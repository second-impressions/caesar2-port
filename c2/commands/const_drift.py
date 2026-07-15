"""const-drift — find wrong literal constants in diffing functions.

The durable wins this corpus still has are *structural / semantic* decompilation
bugs, not the regalloc floor.  The cleanest class is a **wrong literal constant
in a dispatch / threshold ladder**: the recovered source compares a variable
against the wrong immediate, so it byte-diverges for a large cascade even though
the shape looks right.

Proven instance — ``get_census`` (602b -> 119b): the population-warning ladder
had a ``>=100`` check PS never emits, no ``>=40000`` check, and every
``(threshold, warned, message)`` triple shifted by one.

Signature
---------
For each diffing function we compare the **immediate operands of ``cmp`` /
``test`` instructions** in the PS disasm against those in the RC (recompiled)
disasm.  Both are machine code from the same toolchain, so the immediates are
directly comparable — no fragile C-source parsing.  We mask:

  * anything inside ``[..]`` (addresses + spill-slot offsets),
  * values ``>= 0x10000`` (almost always addresses / fixups, never thresholds),
  * the zext masks ``0xff`` / ``0xffff`` (Rule 49 artifacts) and ``0``.

A non-empty **symmetric difference** of the cmp/test immediate multisets is a
wrong-constant bug: a ``get_census``-class structural fix, not regalloc.  We
restrict to ``cmp``/``test`` because comparison constants (thresholds, kind /
enum values, dispatch keys) are where these bugs live and they are almost never
addresses or regalloc artifacts — that filter is what lifts the signal out of
the strength-reduction-shift / leaked-address noise that swamps a naive
all-immediates scan.

Verdict heuristic
-----------------
When every PS-only value ``p`` pairs with an RC-only ``p +/- 1`` (and the offset
is consistent), it is an **off-by-one ladder** — a ``>`` vs ``>=`` / wrong-bound
bug across a whole threshold chain (``business_output``, ``get_new_tribute``).
Otherwise it is a plain **wrong constant** (``get_census``: 40000 vs 100).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import typer

from c2.commands.verify_json import get_verify_json

_CMP_MNEM = {"cmp", "test"}
_MOV_MNEM = {"mov"}
_BRACKET = re.compile(r"\[[^\]]*\]")            # memory operands (addr / spill off)
_NUM = re.compile(r"\b(0x[0-9a-fA-F]+|\d+)\b")
_ZEXT_MASKS = {0x0, 0xff, 0xffff, 0xffffff}     # Rule-49 zext masks + zero
_ADDR_FLOOR = 0x10000                            # >= this is almost always an address


def _imms(asm: str, widen: bool) -> Counter:
    """Source-constant immediates in one instruction's cmp/test (and, with
    ``widen``, ``mov reg, imm``) operands."""
    out: Counter = Counter()
    if not asm:
        return out
    parts = asm.split(None, 1)
    mn = parts[0]
    wanted = _CMP_MNEM | (_MOV_MNEM if widen else set())
    if mn not in wanted:
        return out
    ops = parts[1] if len(parts) > 1 else ""
    no_mem = _BRACKET.sub(" ", ops)              # drop [..] (addresses/offsets)
    for m in _NUM.finditer(no_mem):
        tok = m.group(1)
        v = int(tok, 16) if tok.lower().startswith("0x") else int(tok)
        if v in _ZEXT_MASKS or v >= _ADDR_FLOOR:
            continue
        out[v] += 1
    return out


@dataclass
class Drift:
    name: str
    file: str
    diff_bytes: int
    ps_only: Counter
    rc_only: Counter

    @property
    def score(self) -> int:
        return sum(self.ps_only.values()) + sum(self.rc_only.values())

    def verdict(self) -> str:
        """Off-by-one ladder vs plain wrong-constant.  Pairs PS-only ``p`` with
        an RC-only ``p +/- 1`` even amid strength-reduction noise; a run of
        consistent-sign pairs is a >/>= / wrong-bound ladder bug."""
        ro = Counter(self.rc_only)
        plus = minus = 0
        for p in self.ps_only.elements():
            if ro.get(p + 1, 0) > 0:        # PS K, RC K+1 -> RC bound 1 too high
                ro[p + 1] -= 1; plus += 1
            elif ro.get(p - 1, 0) > 0:      # PS K, RC K-1 -> RC bound 1 too low
                ro[p - 1] -= 1; minus += 1
        pairs = max(plus, minus)
        if pairs >= 2 and (plus == 0 or minus == 0):
            return (f"OFF-BY-ONE ladder: {pairs} threshold(s) RC is "
                    f"{'+1 too high (likely > vs >=)' if plus else '-1 too low'}")
        return "wrong constant(s)"


def _drift(f, widen: bool) -> Drift:
    ps, rc = Counter(), Counter()
    for r in (f.get("rows") or []):
        ps += _imms((r.get("ps") or {}).get("asm", ""), widen)
        rc += _imms((r.get("rc") or {}).get("asm", ""), widen)
    return Drift(f["name"], f.get("file", "?").split("/")[-1],
                 f.get("diff_byte_count", 0), ps - rc, rc - ps)


def _fmt(c: Counter) -> str:
    return ", ".join(hex(k) + (f"x{n}" if n > 1 else "")
                     for k, n in sorted(c.items()))


# ---- decomp-verify -v hint (per-function, from the instruction streams) ----

def detect_hint(ps_insns, rc_insns) -> Optional[Drift]:
    """Const-drift as a verifier hint.  ``ps_insns`` / ``rc_insns`` are the
    aligned instruction streams (``InsnT`` tuples ``(off, size, bytes, asm)``).

    Fires only on a genuine **substitution** -- PS compares against a constant
    our source replaced with a *different* one (both ``ps_only`` and ``rc_only``
    non-empty).  That is the wrong-threshold/dispatch-literal signature
    (get_census, business_output).  One-sided drift (only RC-only, e.g. leaked
    field offsets from a cached pointer -> Rule 73, or a single loop-bound shift)
    is excluded as noise."""
    ps, rc = Counter(), Counter()
    for i in ps_insns:
        ps += _imms(i[3], widen=False)
    for i in rc_insns:
        rc += _imms(i[3], widen=False)
    po, ro = ps - rc, rc - ps
    if not po or not ro:                         # require a substitution
        return None
    return Drift("", "", 0, po, ro)


def render_hint(d: Drift) -> str:
    return (
        f"Const-drift: cmp/test comparison constants differ from PS -- a wrong "
        f"threshold / dispatch literal in the source ({d.verdict()}).  "
        f"PS-only: {_fmt(d.ps_only)}; RC-only: {_fmt(d.rc_only)}.  These are "
        f"the values PS compares against vs the (wrong) ones our source emits; "
        f"read `c2 disasm <fn>` (the L<N> column + cmp immediates) to recover "
        f"the correct ladder and fix the literal.  Realizes byte savings only "
        f"if this is the DOMINANT divergence -- if a Frame/byte-seating diff "
        f"shifts offsets, fix that first (`c2 const-drift` for corpus triage)."
    )


def const_drift(
    func: Optional[str] = typer.Argument(
        None, help="Only this function (default: scan all diffing functions)."),
    widen: bool = typer.Option(
        False, "--widen", help="Also include `mov reg, imm` immediates "
        "(message ids, table sizes), not just cmp/test."),
    min_score: int = typer.Option(
        2, "--min-score", help="Hide functions with fewer than N drifting "
        "immediates (default 2 = at least one PS-only + one RC-only pairing; "
        "set 1 to see single-sided drift too)."),
    rebuild: bool = typer.Option(
        False, "--rebuild", help="Force a fresh build before scanning."),
) -> None:
    """Find diffing functions whose cmp/test comparison constants don't match
    PS — the wrong-threshold / wrong-dispatch-value bugs (get_census class)."""
    doc = get_verify_json(rebuild=rebuild, verbose=True)
    fns = doc["functions"] if "functions" in doc else doc

    targets = []
    for f in fns:
        if not f.get("rows") or f.get("diff_byte_count", 0) == 0:
            continue
        if func and f["name"] != func.rstrip("_"):
            continue
        d = _drift(f, widen)
        if d.score >= min_score:
            targets.append(d)
    targets.sort(key=lambda d: -d.score)

    if not targets:
        typer.echo("No cmp/test constant drift found"
                   + (f" in {func}." if func else " in the diffing corpus."))
        return

    typer.echo(f"const-drift: {len(targets)} function(s) with constant drift "
               f"(cmp/test{' + mov-imm' if widen else ''}, "
               f"score >= {min_score})\n")
    for d in targets:
        typer.echo(f"  [{d.score:3d}] {d.file:13s} {d.name}")
        typer.echo(f"        {d.verdict()}")
        if d.ps_only:
            typer.echo(f"        PS-only : {_fmt(d.ps_only)}")
        if d.rc_only:
            typer.echo(f"        RC-only : {_fmt(d.rc_only)}")
    typer.echo("\nPS-only = constants PS compares against that our source "
               "lacks/mismatches; RC-only = constants our source has that PS "
               "doesn't.  Read `c2 disasm <fn>` (the L<N> line column + the "
               "cmp immediates) to recover the correct ladder, fix the source "
               "literals, re-verify.")
