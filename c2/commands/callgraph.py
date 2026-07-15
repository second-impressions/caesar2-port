r"""callgraph command: PS.EXE direct-call graph + per-callee prototype
consistency check.

Watcom 10.0a's register allocator is **not inter-procedural**.  When
function F calls function G, F's regalloc consults only G's *prototype*
(via :file:`cfeinfo.c` ``InfoLookup``), never G's compiled body.  The
``state->modify`` set (CallZap) for the call to G is computed in
:file:`i86reg.c:82-86` as ``HW_FULL - FEAuxInfo(aux_G, SAVE_REGS)``
where ``aux_G`` comes from either an explicit ``#pragma aux G ...`` or
the language default for the active calling convention.

Practical consequence (verified empirically by reading the OW source
and scanning all 3,842 PS.EXE functions):

  * **Forward dep (F → its callees)**: YES, via prototype info.
    Wrong arg count in our prototype changes CallZap and cascades
    into F's regalloc decisions.
  * **Backward dep (F → its callers)**: NO.  F is compiled in
    isolation; the callers' identity is invisible.
  * **Transitive dep (G's callees affecting F via G)**: NO.  Watcom
    sees only G's prototype, not G's body.

So the high-leverage maintenance task is keeping every *prototype*
(arg count, return type, ``#pragma aux`` if any) consistent with what
PS.EXE source actually declared.  This command surfaces mismatches by
walking the call graph and comparing:

  * Declared sig (from ``decomp/src/*.c``)
  * Body-side inferred sig (what the PS.EXE function's body reads)
  * Caller-side inferred sig (what PS.EXE callers actually set up)

The caller-side analysis is the source of truth for CallZap purposes
because under __watcall, the caller MUST set every reg parm it
intends to pass; the body MAY ignore them.

Usage::

    # Show direct callees of a function with sig consistency
    uv run c2 callgraph battle_stats_panel

    # Show callers (inverse view)
    uv run c2 callgraph battle_stats_panel --callers

    # List all callees with prototype-changing arg-count mismatches
    # that affect a diffing caller (highest leverage to fix)
    uv run c2 callgraph --check

    # JSON output for scripting
    uv run c2 callgraph battle_stats_panel --json

The graph itself is built from PS.EXE direct-``call`` instructions
(via the disasm cache).  Indirect calls (call reg / call [mem]) are
not tracked.  Targets unresolved to a named symbol show as
``@0xXXXXX``.
"""

from __future__ import annotations

import json as _json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

from c2.commands.disasm import disasm_function, _build_ctx
from c2.commands.inferred_sig import (
    InferredSig,
    DeclaredSig,
    CallerEvidence,
    infer_sig,
    infer_sig_from_callers,
    scan_declared_sigs,
    _ARG_REGS,
)


# ── Call graph builder ────────────────────────────────────────────────


_CALLGRAPH_CACHE: dict[
    tuple[str, str], tuple[
        dict[str, list[tuple[int, str]]],  # caller → [(offset, target_name)]
        dict[str, set[str]],                # callee → set(caller_names)
    ]
] = {}


def build_callgraph(
    symbols_json: Path = Path("data/out/symbols.json"),
    exe_path: Path = Path("data/PS.EXE"),
) -> tuple[
    dict[str, list[tuple[int, str]]],
    dict[str, set[str]],
]:
    """Build (callers→[(call_offset, callee_name), ...], callees→{callers}).

    Walks every named code function via :func:`disasm_function` and
    records each ``call`` instruction with its resolved target.

    Targets are resolved as follows:
      * ``DisasmLine.target`` if set (already a symbol name)
      * else parse ``op_str`` as a hex/decimal address and look up
        in the symbol table; falls back to ``@0xXXXXX`` for
        unresolved direct calls
      * indirect calls (``call eax``, ``call [esi+4]``) → skipped

    The result is cached in-process by (symbols_json, exe_path)
    resolved paths.
    """
    key = (str(symbols_json.resolve()), str(exe_path.resolve()))
    if key in _CALLGRAPH_CACHE:
        return _CALLGRAPH_CACHE[key]

    ctx = _build_ctx(symbols_json, exe_path)
    callers_to_calls: dict[str, list[tuple[int, str]]] = {}
    callees_to_callers: dict[str, set[str]] = defaultdict(set)

    for name in sorted(ctx.name_to_addr.keys()):
        try:
            addr, _, lines = disasm_function(
                name, symbols_json=symbols_json, exe_path=exe_path,
            )
        except (KeyError, ValueError, FileNotFoundError):
            continue

        calls: list[tuple[int, str]] = []
        for ln in lines:
            if ln.mnemonic.lower() != "call":
                continue
            tgt = ln.target  # already resolved if a symbol
            if tgt is None:
                m = re.match(r"^(0x[0-9a-fA-F]+|-?\d+)$", ln.op_str.strip())
                if m:
                    raw = int(m.group(1), 0)
                    if raw < 0:
                        raw = (raw + (1 << 32)) & 0xFFFFFFFF
                    tgt = ctx.addr_to_name.get(raw, f"@0x{raw:x}")
                else:
                    # indirect call — call reg / call [mem]
                    continue
            calls.append((ln.address - addr, tgt))
            callees_to_callers[tgt].add(name)
        callers_to_calls[name] = calls

    _CALLGRAPH_CACHE[key] = (callers_to_calls, dict(callees_to_callers))
    return _CALLGRAPH_CACHE[key]


# ── Prototype consistency analysis ────────────────────────────────────


def _proto_callzap(n_reg_args: int, has_return: bool) -> frozenset[str]:
    """CallZap bits assumed by a caller for a function with this
    prototype.  Mirrors i86reg.c::CallZap() for the default __watcall
    aux info: ``parm.used | return_reg`` (with no MODIFY_EXACT).

    For __watcall, the first ``min(n_reg_args, 4)`` regs in
    [EAX, EDX, EBX, ECX] are used as parm registers.  Return reg is
    EAX (for int return).
    """
    z = set(_ARG_REGS[:min(n_reg_args, 4)])
    if has_return:
        z.add("eax")
    return frozenset(z)


def _truth_arg_count(
    name: str,
    body: InferredSig | None = None,
    ev: CallerEvidence | None = None,
) -> tuple[int, str]:
    """Best estimate of a function's reg-arg count.

    Combines body-side (what the function READS) with caller-side
    (what the function's callers SET).  The caller-side wins when
    callers consistently set more regs than the body reads, because
    under __watcall the prototype mandates that callers set every
    intended reg parm — even ones the body ignores.

    Returns ``(count, source_label)`` where source_label is one of
    ``"agree"``, ``"caller-extends"``, ``"body-only"``,
    ``"insufficient"``.
    """
    if body is None:
        try:
            body = infer_sig(name)
        except (KeyError, ValueError, FileNotFoundError):
            return 0, "missing"
    body_n = len(body.arg_regs)

    if ev is None:
        try:
            ev = infer_sig_from_callers(name)
        except (KeyError, ValueError, FileNotFoundError):
            ev = None

    if ev is None or ev.n_call_sites == 0:
        return body_n, "body-only"

    cn, _conf = ev.confirmed_arg_count_prefix_property()
    if cn is None:
        return body_n, "body-only (insufficient callers)"
    if cn > body_n:
        return cn, "caller-extends"
    return body_n, "agree"


# ── Public entry points ───────────────────────────────────────────────


def callees_of(
    name: str,
    *,
    symbols_json: Path = Path("data/out/symbols.json"),
    exe_path: Path = Path("data/PS.EXE"),
) -> list[tuple[int, str]]:
    """All direct callees of ``name`` with their call-site offsets."""
    callers, _ = build_callgraph(symbols_json, exe_path)
    return callers.get(name, [])


def callers_of(
    name: str,
    *,
    symbols_json: Path = Path("data/out/symbols.json"),
    exe_path: Path = Path("data/PS.EXE"),
) -> set[str]:
    """All direct callers of ``name``."""
    _, callees = build_callgraph(symbols_json, exe_path)
    return callees.get(name, set())


def check_proto_consistency(
    declared_map: dict[str, DeclaredSig] | None = None,
    *,
    require_diffing_caller: bool = False,
    diffing_fns: set[str] | None = None,
) -> list[dict]:
    """List all callees whose declared prototype mismatches PS.EXE
    evidence in a way that would change CallZap (cascading regalloc
    drift into the callers).

    Each result row is a dict with keys:

      * ``name``          — callee name
      * ``declared_args`` — total args (reg + stack) declared in source
      * ``declared_reg``  — clamped to 4 (the reg-arg count Watcom sees)
      * ``truth_args``    — caller-confirmed + body-extended estimate
      * ``source``        — provenance label (agree/caller-extends/...)
      * ``n_callers``     — direct caller count
      * ``diff_callers``  — caller subset currently diffing (if known)
      * ``ratios``        — per-reg caller set-ratio dict

    Sorted by len(diff_callers) descending then by n_callers descending.
    """
    if declared_map is None:
        declared_map = scan_declared_sigs()
    callers_map, callees_map = build_callgraph()

    rows: list[dict] = []
    for callee, decl in declared_map.items():
        # Quick eligibility: only consider functions actually called.
        if callee not in callees_map:
            continue

        try:
            body = infer_sig(callee)
        except (KeyError, ValueError, FileNotFoundError):
            continue
        try:
            ev = infer_sig_from_callers(callee)
        except (KeyError, ValueError, FileNotFoundError):
            ev = None

        truth_n, source = _truth_arg_count(callee, body, ev)
        decl_reg = min(decl.n_args, 4)

        # We only care about mismatches that change CallZap.
        decl_zap = _proto_callzap(decl_reg, not decl.returns_void)
        truth_zap = _proto_callzap(truth_n, body.has_return)
        if decl_zap == truth_zap:
            continue

        ratios = {}
        if ev and ev.n_call_sites > 0:
            for r in _ARG_REGS:
                ratios[r] = ev.args_set_before_call.get(r, 0) / ev.n_call_sites

        direct_callers = callees_map[callee]
        diff_subset = (
            direct_callers & diffing_fns if diffing_fns else set()
        )

        if require_diffing_caller and not diff_subset:
            continue

        rows.append({
            "name": callee,
            "declared_args": decl.n_args,
            "declared_reg": decl_reg,
            "declared_returns": not decl.returns_void,
            "truth_args": truth_n,
            "truth_returns": body.has_return,
            "source": source,
            "n_callers": len(direct_callers),
            "diff_callers": sorted(diff_subset),
            "n_call_sites": ev.n_call_sites if ev else 0,
            "ratios": ratios,
        })

    rows.sort(key=lambda r: (-len(r["diff_callers"]), -r["n_callers"]))
    return rows


def _load_diffing_fns() -> set[str]:
    """Load the diffing-function set from the sibling-status cache,
    falling back to empty if no cache is present."""
    cache = Path(".c2-cache/sibling-status.json")
    if not cache.exists():
        return set()
    try:
        data = _json.loads(cache.read_text())
        return set(data.get("diffing", []))
    except (OSError, ValueError, KeyError):
        return set()


# ── CLI ───────────────────────────────────────────────────────────────


def callgraph(
    name: Annotated[
        Optional[str],
        typer.Argument(
            help="Function name (omit with --check to scan all "
                 "callees for prototype mismatches).",
        ),
    ] = None,
    callers: Annotated[
        bool,
        typer.Option(
            "--callers/--callees",
            help="Show direct callers of NAME (default: callees).",
        ),
    ] = False,
    check: Annotated[
        bool,
        typer.Option(
            "--check",
            help="Scan ALL callees in the project for declared-vs-"
                 "evidence prototype mismatches that change CallZap.",
        ),
    ] = False,
    diffing_only: Annotated[
        bool,
        typer.Option(
            "--diffing-only/--all",
            help="With --check, restrict to callees with ≥1 currently "
                 "diffing caller (highest leverage).",
        ),
    ] = True,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Cap rows in --check output."),
    ] = 30,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit JSON instead of a table."),
    ] = False,
) -> None:
    """PS.EXE call-graph viewer + prototype consistency checker.

    Three modes:

    1. ``c2 callgraph <fn>``           — list callees with sig info
    2. ``c2 callgraph <fn> --callers`` — list callers
    3. ``c2 callgraph --check``        — scan all callees for sig drift
    """
    console = Console(color_system=None)

    if check:
        if name is not None:
            console.print(
                "[yellow]warning:[/yellow] NAME is ignored with --check"
            )
        diffs = _load_diffing_fns() if diffing_only else None
        rows = check_proto_consistency(
            require_diffing_caller=diffing_only,
            diffing_fns=diffs,
        )
        if json_out:
            print(_json.dumps(rows, indent=2))
            return
        if not rows:
            console.print("[green]no prototype mismatches that change CallZap[/green]")
            return
        t = Table(title=f"Prototype mismatches affecting CallZap ({len(rows)} total)")
        t.add_column("diff", justify="right", style="red")
        t.add_column("callers", justify="right")
        t.add_column("callee", style="cyan")
        t.add_column("declared")
        t.add_column("truth")
        t.add_column("source")
        t.add_column("ratios (ax/dx/bx/cx)")
        for r in rows[:limit]:
            dec_s = f"{r['declared_args']}arg{'+r' if r['declared_returns'] else ''}"
            tru_s = f"{r['truth_args']}arg{'+r' if r['truth_returns'] else ''}"
            rs = r["ratios"]
            ratio_s = " ".join(
                f"{int(rs.get(rr, 0) * 100):>3}%" for rr in _ARG_REGS
            ) if rs else "(no callers)"
            t.add_row(
                str(len(r["diff_callers"])),
                str(r["n_callers"]),
                r["name"],
                dec_s,
                tru_s,
                r["source"],
                ratio_s,
            )
        console.print(t)
        if len(rows) > limit:
            console.print(
                f"  ... {len(rows) - limit} more (use --limit / --json)"
            )
        return

    if name is None:
        raise typer.BadParameter(
            "Provide a function name or use --check"
        )

    # Single-function mode.
    declared = scan_declared_sigs()
    if callers:
        cset = callers_of(name)
        if json_out:
            print(_json.dumps({"name": name, "callers": sorted(cset)}, indent=2))
            return
        if not cset:
            console.print(f"[yellow]{name}[/yellow]: no direct callers found")
            return
        t = Table(title=f"Direct callers of {name} ({len(cset)} total)")
        t.add_column("caller", style="cyan")
        t.add_column("declared sig")
        t.add_column("call sites", justify="right")
        # Site count per caller
        site_counts = Counter(
            c
            for c, calls in build_callgraph()[0].items()
            for off, tgt in calls if tgt == name
            if c in cset  # NB: c is in cset by construction
        )
        for c in sorted(cset):
            d = declared.get(c)
            sig = (
                f"{d.n_args}arg{'+r' if not d.returns_void else ''}"
                if d else "(undeclared)"
            )
            t.add_row(c, sig, str(site_counts.get(c, 0)))
        console.print(t)
        return

    # Callees mode (default).
    calls = callees_of(name)
    if not calls:
        console.print(f"[yellow]{name}[/yellow]: no direct callees found")
        return
    callee_counts = Counter(t for _, t in calls)

    out_rows = []
    for callee, cnt in callee_counts.most_common():
        try:
            body = infer_sig(callee)
        except (KeyError, ValueError, FileNotFoundError):
            body = None
        try:
            ev = infer_sig_from_callers(callee)
        except (KeyError, ValueError, FileNotFoundError):
            ev = None
        truth_n, source = (
            _truth_arg_count(callee, body, ev) if body else (0, "missing")
        )
        decl = declared.get(callee)
        decl_n = decl.n_args if decl else None
        decl_reg = min(decl_n, 4) if decl_n is not None else None
        match = "—"
        if decl_reg is not None and body is not None:
            match = "✓" if truth_n == decl_reg else "✗"
        out_rows.append({
            "callee": callee,
            "count": cnt,
            "body_args": len(body.arg_regs) if body else None,
            "truth_args": truth_n if body else None,
            "declared_args": decl_n,
            "declared_reg": decl_reg,
            "source": source,
            "match": match,
        })

    if json_out:
        print(_json.dumps({"caller": name, "callees": out_rows}, indent=2))
        return

    t = Table(
        title=f"Direct callees of {name} "
              f"({len(callee_counts)} distinct, {sum(callee_counts.values())} sites)"
    )
    t.add_column("sites", justify="right")
    t.add_column("callee", style="cyan")
    t.add_column("body", justify="right")
    t.add_column("truth", justify="right")
    t.add_column("decl_reg", justify="right")
    t.add_column("decl_tot", justify="right")
    t.add_column("match")
    t.add_column("source")
    for r in out_rows:
        t.add_row(
            str(r["count"]),
            r["callee"],
            "?" if r["body_args"] is None else str(r["body_args"]),
            "?" if r["truth_args"] is None else str(r["truth_args"]),
            "?" if r["declared_reg"] is None else str(r["declared_reg"]),
            "?" if r["declared_args"] is None else str(r["declared_args"]),
            r["match"],
            r["source"],
        )
    console.print(t)
