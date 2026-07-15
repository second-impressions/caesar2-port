"""Prologue-divergence detector for ``decomp-verify``.

When PS.EXE and the recompiled binary disagree on which registers a
function pushes in its prologue, the root cause is almost always one
of a small set of well-understood source-level patterns:

* **PS preserves EAX** — PS source carried a `#pragma aux NAME modify
  [edx ebx ecx]` (or similar) that *omits* EAX from the modify set,
  forcing the callee to save the caller's EAX value.  Rare (≤ 5
  functions in PS.EXE) but very high-leverage when it fires.

* **PS preserves a segment register** — PS source had `__loadds`
  (`LOAD_DS_ON_ENTRY` aux class) or an explicit `#pragma aux ... [ds]`
  in the save set.  Even rarer; the only known case in C2 is
  `click_handler`.

* **PS has one extra GP callee-save** (typically EBP, EDI, or ESI)
  vs recomp — the function's source carried one more named local
  (or used a wider type), giving Watcom another live-across-call
  value to enregister.  Fix: add or widen a local.

* **Recomp has one extra GP callee-save** vs PS — recomp's source
  unnecessarily enregisters something PS source kept in a scratch
  register.  Fix: simplify a local out, inline an expression, or
  narrow a type.

* **Many regs differ** — structural divergence (different loop
  shape, different number of live values).  Detector flags but
  doesn't try to prescribe a fix.

The detector is **conservative**: it only fires when the prologue
**actually differs** between PS and recomp.  Functions that already
byte-match the prologue produce no hint, even if their prologue
shape is unusual.

Wired into ``decomp_verify._render_compact`` and
``_render_diff`` next to the existing callee-saves summary; also
surfaces under ``functions[].pragma_hints`` in ``--json`` output.

See `docs/watcom-codegen-patterns.md` Rule 70 for the underlying
mechanism (`MustSaveRegs` / `SaveRegs` in OW v1.0's
`bld/cg/intel/c/i86reg.c` and the `GetSaveInfo`/`PragRegList`
parsing of `modify` clauses in `bld/cc/c/cprag86.c`).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.markup import escape as _esc


# Set of registers that Watcom 10.0a under `-4r` __watcall can include
# in a function's callee-save set.  Capstone formats these in
# lower-case op_str; we match against that.
_GP_REGS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}
_SEG_REGS = {"ds", "es", "fs", "gs"}

# Regex used by _has_stack_slot_access to spot Rule 24a stack-spill
# patterns: `[esp]` or `[esp + N]` in an operand string.  Catches
# both reads (`mov reg, [esp]`) and writes (`mov [esp], reg`).
import re as _re
_STACK_SLOT_RE = _re.compile(r"\[\s*esp(\s*[+\-]\s*0x[0-9a-fA-F]+)?\s*\]")


@dataclass(frozen=True)
class PragmaHint:
    """A single prologue-divergence hint for a function.

    ``category`` is a short tag suitable for grouping in --json
    output and the ``progress`` histograms; ``severity`` drives
    color rendering in -v mode; ``summary`` is the one-line human-
    readable description; ``suggestion`` is the actionable next step
    (may be empty for "many regs differ" cases the detector can't
    pin down).
    """
    category: str
    severity: str           # "high" | "medium" | "low"
    summary: str
    suggestion: str
    ps_pushes: tuple[str, ...]
    rc_pushes: tuple[str, ...]
    ps_only: tuple[str, ...]
    rc_only: tuple[str, ...]

    def render(self) -> str:
        """Format for one-line display in `decomp-verify -v` output."""
        return f"{self.summary}.  {self.suggestion}" if self.suggestion else self.summary


# ── Categorisation logic ───────────────────────────────────────────────────


def _has_stack_slot_access(insns: list) -> bool:
    """Scan ``insns`` for any operand referencing ``[esp]`` or
    ``[esp + N]`` — the canonical Rule 24a stack-spill signature.

    A function that legitimately callee-saves a register never
    reads back from that stack slot; a function using ``push eax``
    as a stack-allocation idiom always does (it spills a local
    through it).
    """
    if not insns:
        return False
    for i in insns:
        asm = i[3] if len(i) >= 4 else ""
        if not asm:
            continue
        # Skip prologue / epilogue stack manipulation — only body
        # `[esp+N]` accesses count as spill signature.
        if asm.startswith(("push ", "pop ")):
            continue
        if _STACK_SLOT_RE.search(asm):
            return True
    return False


def _classify(
    ps: tuple[str, ...], rc: tuple[str, ...],
    ps_insns: Optional[list] = None,
    rc_insns: Optional[list] = None,
) -> Optional[PragmaHint]:
    """Return a PragmaHint if PS and recomp prologues differ in a way
    the detector recognises; otherwise None.

    Prologues that match exactly produce no hint.  Prologues that
    only differ in ordering (e.g. PS pushes ``ebx, ecx`` and recomp
    pushes ``ecx, ebx``) also produce no hint — Watcom's prologue
    emitter is deterministic for a given used-set, so ordering
    divergence is also a real signal, but a separate one.

    ``ps_insns`` / ``rc_insns`` are optional; supplying them lets
    the detector look beyond the prologue to disambiguate categories
    that look identical from prologue-pushes alone (specifically
    ``ps_eax_preserved`` vs ``ps_stack_spill``).
    """
    if ps == rc:
        return None

    ps_set = set(ps)
    rc_set = set(rc)
    ps_only = ps_set - rc_set
    rc_only = rc_set - ps_set

    # Ordering-only divergence (same set, different order).  Rare
    # but does happen — Watcom's prologue emitter sorts by `state.used`
    # in conflict-creation order, which can flip when source layout
    # changes.  We surface it as a low-severity hint.
    if not ps_only and not rc_only:
        return PragmaHint(
            category="prologue_order",
            severity="low",
            summary=f"Prologue push ORDER differs: PS={list(ps)} RC={list(rc)}",
            suggestion=(
                "Same callee-save set but different push order — usually "
                "harmless register-creation-order noise from a small source "
                "layout change."
            ),
            ps_pushes=ps, rc_pushes=rc, ps_only=(), rc_only=(),
        )

    # PS pushes EAX in the prologue.  Two distinct sub-cases:
    #
    #   (a) **True EAX preservation** — callee-save EAX, restored at
    #       end via `pop eax`.  Source needs `#pragma aux NAME
    #       modify exact [edx ebx ecx]` so EAX stays in the save set.
    #       Rare: Watcom by default removes EAX from MustSaveRegs as
    #       it's the param/return reg.
    #
    #   (b) **Stack-spill via EAX (Rule 24a)** — push eax is a
    #       4-byte stack-slot allocation.  The body reads/writes
    #       `[esp]` (or `[esp+N]`) and the epilogue uses `add esp,
    #       N` rather than `pop eax`.  No pragma fixes this; the
    #       lever is a named local that Watcom decides to spill.
    #
    # We disambiguate by checking the function body for `[esp]`
    # accesses (stack-spill signature) before suggesting a pragma.
    if "eax" in ps_only:
        spill = _has_stack_slot_access(ps_insns)
        if spill:
            return PragmaHint(
                category="ps_stack_spill",
                severity="medium",
                summary="PS uses `push eax` as a 4-byte stack-slot local (Rule 24a)",
                suggestion=(
                    "PS source has a named local that Watcom decided to spill "
                    "to the stack rather than enregister.  The `push eax` is "
                    "stack-allocation, not EAX preservation — no `#pragma aux "
                    "modify` fixes this.  Try adding a named local in the C "
                    "source that Watcom is likely to spill (a pointer that "
                    "survives across many sub-expressions, or a value live "
                    "across a call).  See `docs/watcom-codegen-patterns.md` "
                    "Rule 24a (spill-via-local) for the lever."
                ),
                ps_pushes=ps, rc_pushes=rc,
                ps_only=tuple(sorted(ps_only)), rc_only=tuple(sorted(rc_only)),
            )
        return PragmaHint(
            category="ps_eax_preserved",
            severity="high",
            summary="PS preserves EAX across the function (callee-save EAX)",
            suggestion=(
                "Add `#pragma aux <name> modify exact [edx ebx ecx];` "
                "(omitting eax from the modify list, with `exact` to keep "
                "EAX in `save` even though it's the param/return reg). "
                "PS source had a pragma that forces EAX preservation, "
                "typically because the caller relies on EAX surviving "
                "the call (e.g. a long-lived loop variable)."
            ),
            ps_pushes=ps, rc_pushes=rc,
            ps_only=tuple(sorted(ps_only)), rc_only=tuple(sorted(rc_only)),
        )

    # PS preserves a segment reg.  Either `__loadds` (LOAD_DS_ON_ENTRY
    # aux flag) when DS is involved, or a custom segreg-preserve pragma.
    ps_segs = ps_only & _SEG_REGS
    if ps_segs:
        if "ds" in ps_segs and len(ps_segs) == 1:
            return PragmaHint(
                category="ps_loadds",
                severity="high",
                summary="PS preserves DS at function entry",
                suggestion=(
                    "Add `#pragma aux <name> __loadds;` (LOAD_DS_ON_ENTRY "
                    "aux flag) — PS source declared this function as needing "
                    "DS reloaded on every call, typically because it's an "
                    "interrupt handler / callback registered with a non-flat "
                    "library (e.g. AIL).  Watcom emits `push ds; mov ds, "
                    "DGROUP; ...; pop ds` around the body."
                ),
                ps_pushes=ps, rc_pushes=rc,
                ps_only=tuple(sorted(ps_only)), rc_only=tuple(sorted(rc_only)),
            )
        return PragmaHint(
            category="ps_seg_preserved",
            severity="high",
            summary=f"PS preserves segment register(s): {sorted(ps_segs)}",
            suggestion=(
                "Add a `#pragma aux <name>` with the appropriate save set "
                "(usually `modify exact [eax edx ecx ebx]`-style that "
                f"*omits* {sorted(ps_segs)} from the modify list) — typically "
                "needed for callbacks registered with DOS/DPMI services."
            ),
            ps_pushes=ps, rc_pushes=rc,
            ps_only=tuple(sorted(ps_only)), rc_only=tuple(sorted(rc_only)),
        )

    # PS has exactly one extra GP callee-save (and recomp matches on
    # all others) — most often EDI/ESI/EBP, indicating PS source had
    # an extra named local or a wider type.
    if len(ps_only) == 1 and not rc_only:
        extra = next(iter(ps_only))
        return PragmaHint(
            category="ps_extra_callee_save",
            severity="medium",
            summary=f"PS uses an extra callee-save register: {extra}",
            suggestion=(
                f"PS enregisters one more long-lived value than recomp.  "
                f"DIAGNOSE FIRST (Rule 89): extra-callee-save is heterogeneous. "
                f"Read the PS body and check what `{extra}` holds: "
                f"(a) a value live ACROSS a call/idiv -> EAX-boundary: reshape "
                f"the C so the value's range spans the clobber (read a global "
                f"into a named local BEFORE a call and use it AFTER; widen a "
                f"`char` flag to `int`); "
                f"(b) a byte reg materialising a const for a store (`xor bl,bl; "
                f"mov [m],bl`) -> Rule 110: the store FORM is deterministic, so "
                f"this is a regalloc which-register divergence (match PS's "
                f"allocation, Rule 108/use-order), NOT a store-form lever; "
                f"(c) a value PS put in a different reg -> FIRST-USE order "
                f"(Rule 28a): reorder which competing value is used first. "
                f"There is NO push-economics or `register`-keyword lever."
            ),
            ps_pushes=ps, rc_pushes=rc,
            ps_only=tuple(sorted(ps_only)), rc_only=tuple(sorted(rc_only)),
        )

    # Recomp has exactly one extra GP callee-save (and PS matches on
    # all others) — recomp enregisters one more value than PS, usually
    # because a source-level local introduces a value PS source kept
    # as a memory expression.
    if len(rc_only) == 1 and not ps_only:
        extra = next(iter(rc_only))
        return PragmaHint(
            category="rc_extra_callee_save",
            severity="medium",
            summary=f"Recomp uses an extra callee-save register: {extra}",
            suggestion=(
                f"Recomp enregisters one more long-lived value than PS.  "
                f"DIAGNOSE FIRST (Rule 89): check what `{extra}` holds in OUR "
                f"body vs PS. "
                f"(a) a value WE keep live across a call/idiv that PS didn't "
                f"-> EAX-boundary: stop crossing the clobber -- inline the value "
                f"at its use sites (Rule 1/63/73) or move the use BEFORE the "
                f"call so its range no longer spans it; "
                f"(b) a value we put in a different reg than PS -> FIRST-USE "
                f"order (Rule 28a): reorder which competing value is used first "
                f"(commute an operand, move a statement). "
                f"The `register` keyword and push-economics do NOTHING (proven)."
            ),
            ps_pushes=ps, rc_pushes=rc,
            ps_only=tuple(sorted(ps_only)), rc_only=tuple(sorted(rc_only)),
        )

    # Symmetric one-for-one swap (PS uses ESI where recomp uses EDI,
    # etc.) — Rule 28a territory, but we surface the prologue half of
    # it as well so it shows up in the per-function header.
    if len(ps_only) == 1 and len(rc_only) == 1:
        a = next(iter(ps_only))
        b = next(iter(rc_only))
        # The edi<->ebp flavour has a known C-source lever (Rule 87): a
        # spurious `else return;` on an unreachable dispatch branch adds a
        # control-flow edge that flips the allocator from edi to ebp.
        if {a, b} == {"edi", "ebp"}:
            suggestion = (
                f"PS uses {a}, RC uses {b}.  edi<->ebp swaps usually have a "
                f"C-source lever — reduce register pressure on the "
                f"long-lived value so the allocator picks edi over ebp:\n"
                f"  (1) Rule 1/63: remove a cached local that is read "
                f"multiple times (e.g. `int mx = mouse_x;` used 3x) and "
                f"inline the reads — the cache's live range is what bumps "
                f"the held value into ebp.\n"
                f"  (2) Rule 87: drop a spurious `else return;` (or other "
                f"dead branch) on an UNREACHABLE dispatch case that is "
                f"already excluded by earlier guards — PS lets that path "
                f"fall through with an uninitialised local.\n"
                f"After either, if the push set matches, the residual is "
                f"usually a tail-merge (Rule 42) anchor-direction issue. "
                f"See `docs/watcom-codegen-patterns.md` Rules 1, 87, 42 "
                f"(Rule 28a if neither lever applies)."
            )
        else:
            suggestion = (
                f"Rule 28a pure register swap.  The {a}/{b} assignment follows "
                f"FIRST-USE order: reorder which competing value is used first "
                f"(commute an operand, move a statement) — worked example "
                f"change_citizen_targs.  See `docs/wcc386-re/regalloc-model.md` "
                f"and Rule 28a.  Not reorderable when the values are CSE-hoisted "
                f"globals in fixed algorithmic order."
            )
        return PragmaHint(
            category="callee_save_swap",
            severity="medium",
            summary=f"Callee-save SWAP: PS uses {a} where RC uses {b}",
            suggestion=suggestion,
            ps_pushes=ps, rc_pushes=rc,
            ps_only=tuple(sorted(ps_only)), rc_only=tuple(sorted(rc_only)),
        )

    # Many-reg divergence (≥ 2 on at least one side) — structural
    # difference.  Surface but don't prescribe.
    side = "PS" if len(ps_only) > len(rc_only) else "RC"
    return PragmaHint(
        category="structural_divergence",
        severity="low",
        summary=(
            f"Prologue diverges by {len(ps_only)}+{len(rc_only)} regs "
            f"(PS-only={sorted(ps_only)}, RC-only={sorted(rc_only)})"
        ),
        suggestion=(
            f"{side} has substantially more enregistered values — the "
            f"function's control flow / live-value count differs from PS.  "
            f"Re-read the PS disasm and verify the C source matches PS's "
            f"branch structure (no merged loops, no hoisted constants, no "
            f"extra `else`/`continue` paths).  Single-reg fixes won't close "
            f"this kind of gap."
        ),
        ps_pushes=ps, rc_pushes=rc,
        ps_only=tuple(sorted(ps_only)), rc_only=tuple(sorted(rc_only)),
    )


# ── Public API ─────────────────────────────────────────────────────────────


def detect_prologue_pushes(insns: list) -> tuple[str, ...]:
    """Extract the ordered list of register pushes from a function's
    prologue.

    Mirrors `decomp_verify._detect_callee_saves` but returns the raw
    push set (without filtering to a fixed "callee-save" allowlist),
    so the detector can also flag exotic pushes like ``eax`` and
    segment registers that `_detect_callee_saves` would clip off.

    The optional `push <imm>; call __CHK` stack-probe prefix is
    skipped: `push 8; call __CHK` etc. don't count as callee-saves.
    """
    if not insns:
        return ()

    # Capstone tuple shape used by decomp_verify is (addr, size, raw, asm).
    def asm(i):
        return i[3] if len(i) >= 4 else ""

    start = 0
    if len(insns) >= 2:
        a0 = asm(insns[0])
        a1 = asm(insns[1])
        if a0.startswith("push "):
            op = a0.split(None, 1)[1]
            if op and (op[0].isdigit() or op.startswith("0x") or op.startswith("-")):
                if a1.startswith("call "):
                    start = 2

    out: list[str] = []
    for i in range(start, len(insns)):
        a = asm(insns[i])
        if not a.startswith("push "):
            break
        op = a.split(None, 1)[1].strip()
        if not op:
            break
        # Stop at `push <imm>` (e.g. push 0x10 inside the body).
        if op[0].isdigit() or op.startswith("0x") or op.startswith("-"):
            break
        if op in _GP_REGS or op in _SEG_REGS:
            out.append(op)
        else:
            # Unknown push operand (memory, far ptr, etc.) — stop the prologue.
            break
    return tuple(out)


def detect_pragma_hint(
    ps_insns: list,
    rc_insns: list,
) -> Optional[PragmaHint]:
    """Top-level entry point used by `decomp_verify`.

    Compares the PS and recomp prologue push sets and returns a hint
    when they diverge.  Returns None when prologues match exactly.

    ``ps_insns`` / ``rc_insns`` are the capstone-decoded instruction
    lists already produced by ``_disasm_for_diff`` in decomp_verify;
    the detector inspects the prologue *and* the body, since some
    high-severity categories (``ps_eax_preserved`` vs the easily
    confused ``ps_stack_spill``) need a body-scan to disambiguate.
    """
    ps = detect_prologue_pushes(ps_insns)
    rc = detect_prologue_pushes(rc_insns)
    return _classify(ps, rc, ps_insns=ps_insns, rc_insns=rc_insns)


def render_hint_lines(hint: PragmaHint) -> list[str]:
    """Format a hint as one or two terminal-friendly lines.

    Returns one line for severity=low (just the summary), two for
    medium/high (summary + indented suggestion).  Callers wrap with
    Rich markup as appropriate.
    """
    lines = [hint.summary]
    if hint.suggestion:
        # Suggestion can be long; just emit it as a single soft-wrapped
        # block.  Rendering layer is free to truncate.
        lines.append(f"    → {hint.suggestion}")
    return lines


def hint_to_json(hint: PragmaHint) -> dict:
    """Serialise a PragmaHint to a JSON-compatible dict for
    ``decomp-verify --json`` output."""
    return {
        "category":   hint.category,
        "severity":   hint.severity,
        "summary":    hint.summary,
        "suggestion": hint.suggestion,
        "ps_pushes":  list(hint.ps_pushes),
        "rc_pushes":  list(hint.rc_pushes),
        "ps_only":    list(hint.ps_only),
        "rc_only":    list(hint.rc_only),
    }


# ── CLI command ────────────────────────────────────────────────────────────

# Display order for severity — high first so the most actionable hits
# rise to the top of the table.
_SEV_RANK = {"high": 0, "medium": 1, "low": 2}

# Category labels for the table header (kept short for a 12-column fit).
_CAT_LABEL = {
    "ps_eax_preserved":     "PS-eax",
    "ps_stack_spill":       "spill",
    "ps_loadds":            "loadds",
    "ps_seg_preserved":     "PS-seg",
    "ps_extra_callee_save": "PS+1",
    "rc_extra_callee_save": "RC+1",
    "callee_save_swap":     "swap",
    "prologue_order":       "order",
    "structural_divergence":"struct",
}


def _gather_hits(
    *,
    no_cache: bool,
    strict: bool,
) -> tuple[list[dict], dict]:
    """Run ``c2 decomp-verify --json`` and return ``(hits, summary)``.

    Spawns a subprocess so the underlying decomp-verify invocation
    is exactly the same as what the user would run by hand — keeps
    cache behaviour, warning filtering and exit-code semantics
    identical to the CLI.

    ``hits`` is the subset of ``functions[]`` that have a non-null
    ``pragma_hint``, each enriched with the hint fields flattened
    onto the function record for easy filtering/printing.
    """
    args = ["uv", "run", "c2", "decomp-verify", "--json"]
    if not strict:
        args.append("--no-strict")
    if no_cache:
        args.append("--no-cache")
    res = subprocess.run(args, capture_output=True, text=True, check=False)
    if not res.stdout.strip():
        # Build failed or no output — surface the stderr for debugging.
        typer.echo(res.stderr, err=True)
        raise typer.Exit(res.returncode or 1)
    try:
        data = json.loads(res.stdout)
    except json.JSONDecodeError as e:
        typer.echo(f"failed to parse decomp-verify --json output: {e}", err=True)
        typer.echo(res.stderr, err=True)
        raise typer.Exit(1) from e

    hits: list[dict] = []
    for f in data.get("functions", []):
        h = f.get("pragma_hint")
        if not h:
            continue
        hits.append({
            "name":     f["name"],
            "file":     f.get("file", ""),
            "address":  f.get("address", ""),
            "size":     f.get("size", 0),
            "diff":     f.get("diff_byte_count", 0),
            "category": h["category"],
            "severity": h["severity"],
            "summary":  h["summary"],
            "suggestion": h["suggestion"],
            "ps_pushes": h["ps_pushes"],
            "rc_pushes": h["rc_pushes"],
            "ps_only":   h["ps_only"],
            "rc_only":   h["rc_only"],
        })
    return hits, data.get("summary", {})


def _render_table(
    hits: list[dict],
    *,
    show_suggestion: bool,
    show_pushes: bool,
) -> None:
    """Render a Rich table of pragma hints.

    The default table is compact (sev, cat, diff, size, function,
    file) so it fits in a normal 100-column terminal.  ``--show-pushes``
    adds the PS/RC push columns; ``--show-suggestion`` adds the full
    suggestion text.  The summary is omitted from the table proper
    because the category label encodes the same info — use
    ``--show-suggestion`` when you want the prose explanation.
    """
    from rich.console import Console
    from rich.table import Table

    table = Table(show_header=True, header_style="bold", expand=False)
    table.add_column("sev", style="bold", width=4)
    table.add_column("category", width=8)
    table.add_column("diff", justify="right", width=6)
    table.add_column("size", justify="right", width=6)
    table.add_column("function", no_wrap=True)
    table.add_column("file", no_wrap=True)
    if show_pushes:
        table.add_column("PS pushes", overflow="ellipsis", max_width=22)
        table.add_column("RC pushes", overflow="ellipsis", max_width=22)
    if show_suggestion:
        table.add_column("suggestion", overflow="fold")

    sev_colors = {"high": "red", "medium": "yellow", "low": "dim"}

    for h in hits:
        sev_label = f"[{sev_colors[h['severity']]}]{h['severity'][0].upper()}[/]"
        cat_label = _CAT_LABEL.get(h["category"], h["category"])
        # `_esc` escapes [..] sequences in user-supplied strings so Rich
        # doesn't try to parse them as markup tags.  Function names,
        # file paths and the suggestion can all carry brackets (e.g.
        # `#pragma aux ... modify [edx ebx ecx]`).
        row = [
            sev_label,
            cat_label,
            str(h["diff"]),
            str(h["size"]),
            _esc(h["name"]),
            _esc(Path(h["file"]).name),
        ]
        if show_pushes:
            row.append(",".join(h["ps_pushes"]) or "—")
            row.append(",".join(h["rc_pushes"]) or "—")
        if show_suggestion:
            row.append(_esc(h["suggestion"]))
        table.add_row(*row)

    console = Console(color_system=None)
    console.print(table)

    # Footer: bucket counts by category + total diff bytes.
    from collections import Counter
    cats = Counter(h["category"] for h in hits)
    sev_counts = Counter(h["severity"] for h in hits)
    total_diff = sum(h["diff"] for h in hits)
    parts = [f"{n}x {_CAT_LABEL.get(c, c)}" for c, n in cats.most_common()]
    sev_parts = [f"{n} {s}" for s, n in sorted(sev_counts.items(), key=lambda kv: _SEV_RANK.get(kv[0], 99))]
    console.print(
        f"  [dim]{len(hits)} functions  ({', '.join(sev_parts)})  "
        f"· {total_diff:,} diff bytes attributed  · {', '.join(parts)}[/]"
    )


def pragma_hints(
    severity: Annotated[
        Optional[str],
        typer.Option("--severity",
                     help="Filter by severity: high, medium, low."),
    ] = None,
    category: Annotated[
        Optional[str],
        typer.Option("--category",
                     help="Filter by category (e.g. ps_eax_preserved, "
                          "ps_loadds, ps_extra_callee_save, "
                          "rc_extra_callee_save, callee_save_swap, "
                          "structural_divergence, prologue_order)."),
    ] = None,
    file_filter: Annotated[
        Optional[str],
        typer.Option("--file",
                     help="Restrict to functions whose source file path "
                          "contains this substring (e.g. 'lib32')."),
    ] = None,
    name_filter: Annotated[
        Optional[str],
        typer.Option("--name",
                     help="Restrict to functions whose name contains "
                          "this substring."),
    ] = None,
    min_diff: Annotated[
        int,
        typer.Option("--min-diff",
                     help="Only show functions with at least N diff bytes."),
    ] = 0,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n",
                     help="Show top N rows (sorted by severity then diff). "
                          "Use 0 for all."),
    ] = 25,
    sort: Annotated[
        str,
        typer.Option("--sort",
                     help="Sort key: 'diff' (desc), 'size' (asc), "
                          "'severity' (high→low), 'name' (asc)."),
    ] = "severity",
    show_suggestion: Annotated[
        bool,
        typer.Option("--show-suggestion",
                     help="Include the full suggestion text in the table "
                          "(wide output)."),
    ] = False,
    show_pushes: Annotated[
        bool,
        typer.Option("--show-pushes/--no-show-pushes",
                     help="Include PS-pushes and RC-pushes columns."),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a text table."),
    ] = False,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache",
                     help="Force a fresh decomp-verify build (skip "
                          ".c2-cache/build/)."),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict/--no-strict",
                     help="Strict mode for decomp-verify (default: "
                          "--no-strict)."),
    ] = False,
) -> None:
    """Triage prologue divergences between PS.EXE and the recompiled
    binary by suggesting pragma directives or source-level fixes.

    Output table is sorted by severity (high→low) then diff bytes,
    so the highest-leverage actionable hits rise to the top.  Use
    ``--severity high`` for the rare-but-clear pragma cases
    (``modify [...]``, ``__loadds``) and ``--severity medium`` for
    the larger "extra/missing callee-save" pool where source-level
    levers (type widening, named local) usually close the gap.

    Examples::

        # Top 25 hits, sorted by severity then leverage.
        uv run c2 pragma-hints

        # High-severity only (modify-pragma / loadds candidates).
        uv run c2 pragma-hints --severity high

        # All `int building`-style "PS has an extra callee-save" candidates.
        uv run c2 pragma-hints --category ps_extra_callee_save

        # Just one source file.
        uv run c2 pragma-hints --file lib32

        # Full JSON for downstream tooling.
        uv run c2 pragma-hints --json --limit 0

    See ``docs/watcom-codegen-patterns.md`` Rule 70 for the
    underlying mechanism and worked example (`push_node_value`).
    """
    hits, summary = _gather_hits(no_cache=no_cache, strict=strict)

    # Apply filters.
    if severity:
        sev = severity.lower()
        if sev not in _SEV_RANK:
            typer.echo(f"unknown severity {severity!r}", err=True)
            raise typer.Exit(2)
        hits = [h for h in hits if h["severity"] == sev]
    if category:
        hits = [h for h in hits if h["category"] == category]
    if file_filter:
        hits = [h for h in hits if file_filter in h["file"]]
    if name_filter:
        hits = [h for h in hits if name_filter in h["name"]]
    if min_diff > 0:
        hits = [h for h in hits if h["diff"] >= min_diff]

    # Sort.
    if sort == "diff":
        hits.sort(key=lambda h: -h["diff"])
    elif sort == "size":
        hits.sort(key=lambda h: h["size"])
    elif sort == "name":
        hits.sort(key=lambda h: h["name"])
    else:  # severity (default)
        hits.sort(key=lambda h: (_SEV_RANK.get(h["severity"], 99), -h["diff"]))

    # Limit.
    if limit > 0:
        hits = hits[:limit]

    if as_json:
        typer.echo(json.dumps({"hits": hits, "verify_summary": summary},
                              indent=2))
        return

    if not hits:
        typer.echo("no pragma-hint divergences match the filters", err=True)
        return

    _render_table(
        hits,
        show_suggestion=show_suggestion,
        show_pushes=show_pushes,
    )
