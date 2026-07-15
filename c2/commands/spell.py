"""``c2 spell`` -- the three-stage spelling-difference localizer.

Traces a function TWICE (working-tree TU vs a candidate-spelling file)
under the instrumented 10.0a compiler and reports at which stage the
source distinction DIES -- turning every negative probe result into a
precise, actionable classification instead of "bytes unchanged":

  INERT@TREE   the parser/tree-build canonicalized the spelling away
               (identical tn/tl trees).  No downstream pass can ever see
               it: the spelling family is PROVABLY unreachable -- stop.
  INERT@BURN   trees differ but the LdStAlloc walk (lw) is identical:
               the tree->IL burn (or a pre-LdStAlloc pass) filtered it.
               Other tree spellings of the same idea may still work.
  LIVE         the walk differs; the per-rover-class advance DELTA is
               shown (the number the influence-window fit asks for).
               These are the first candidates worth a byte compile.

Measured calibration (2026-07-09 audit, 109 byte-compiled fold/unfold
candidates on byte-exact functions -- see
docs/codegen-experiments/spell-verdict-audit.py): LIVE predicts a byte
change with 0.93 precision; INERT@BURN predicts byte-neutrality with
0.83 precision.  The walk lens is BLIND to conflict-graph / savings
changes upstream of LdStAlloc, so ~1 in 6 INERT@BURN candidates still
moves bytes (diverged IL births + identical walk was the observed false
negative signature).  Treat INERT@BURN as "deprioritize", NOT "proven
dead"; INERT@TREE remains the only stop verdict.

The candidate view also prints the two layers BETWEEN tree and walk --
block births (bo: GenBlock chain order) and IL births (ni: NewIns
emission order) -- so an inert verdict names the exact stage that
absorbed the spelling: identical IL births = canonicalized AT emission
(deepest inert, stop the family); diverged births + identical walk = a
post-emission pass re-converged it (siblings at the delta lines may
survive).  The construct -> block-birth dictionary (what adds/moves
births: labels +1, &&/||/nested-if identical, loop forms distinct,
byte-RMW naming as the byte-class rover lever) is at watcom10.0a
docs/block-birth-dictionary.md.

Usage:
    c2 spell <fn> <candidate.c>          # candidate = full TU replacement
    c2 spell <fn> <candidate.c> --tree   # show the per-statement tree diff
    c2 spell <fn> --walk-order           # no candidate: print the walk-vs-
                                         # layout block map (the walk-order
                                         # divergence class explorer)
    c2 spell <fn> --suggest              # GENERATE the census's fold/unfold
                                         # candidates (forge de_invent_all +
                                         # cache_field span machinery) PLUS
                                         # the Rule 121 tail-dup/tail-hoist
                                         # structural candidates (shared tail
                                         # <-> per-arm copies; dup-with-CALL =
                                         # the walk-entry lever) and screen
                                         # each one; --lines 410,422 restricts
                                         # to the [lw census] lines the Rover
                                         # hint printed

The analysis engine lives in :mod:`c2.regalloc.lwalk` (shared with the
``Rover:`` hint's per-window census).  Requires the trace image with the
``lw`` probe (watcom10.0a ``scripts/build-trace-image.sh``, >= 2026-07-09).
"""
from __future__ import annotations

import difflib
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.markup import escape

console = Console()


def _trace_routine(func: str, src_text: str) -> dict:
    from c2 import regalloc
    from c2.commands.regtrace_native import _find_function, INCLUDE_DIR
    src_file, start, end, _ = _find_function(func, None)
    files = {"TARGET.C": src_text}
    for h in INCLUDE_DIR.glob("*.h"):
        files[h.name.upper()] = h.read_text(errors="replace")
    td = regalloc.trace_compile(files, main="TARGET.C")
    # Score by lw+fr line hits inside the function's span (with slack
    # for candidate texts whose edits shift lines a little).  The OLD
    # selector used fr-hits alone seeded at -1: a function with NO
    # fr record in its span silently matched the FIRST fr-carrying
    # routine in the TU -- base and candidate then compared the same
    # WRONG routine and emitted a confident false "INERT@TREE --
    # provably unreachable, stop".  Caught by the 2026-07-09 screener
    # audit (docs/codegen-experiments/spell-verdict-audit.py): all 13
    # INERT@TREE verdicts in a 113-candidate byte-compiled corpus were
    # this bug; 10 of them actually moved bytes.
    lo, hi = start - 2, end + 8
    best, bh = None, 0
    for r in td["routines"]:
        hits = sum(1 for x in r.get("lw", [])
                   if x.get("line") and lo <= x["line"] <= hi)
        hits += sum(1 for x in r.get("fr", [])
                    if x.get("line") and lo <= x["line"] <= hi)
        if hits > bh:
            bh, best = hits, r
    if best is None:
        raise typer.Exit(
            f"{func}: no traced routine covers lines {lo}-{hi} "
            "(TU compile error, or the function emits no traced records)")
    return best


def _fmt_row(row: tuple) -> str:
    ln, op, tc, rk, o0, o1, risc = row
    return (f"L{ln:<5} op={op:#04x} tc={tc:#x} res={rk:x} "
            f"op0={o0:x} op1={o1:x} {'RISC' if risc else 'skip'}")


class _ShimForge:
    """Minimal duck-type of :class:`c2.forge.experiment.Forge` for the
    span-generating presets: they only touch ``.text``, ``.function`` and
    ``.candidate(tag, *edits)``."""

    def __init__(self, text: str, function: str):
        self.text = text
        self.function = function
        self.collected: list[tuple[str, tuple]] = []

    def candidate(self, tag: str, *edits) -> None:
        self.collected.append((tag, edits))


def _suggest(function: str, base_text: str, lines: Optional[str],
             screen: bool) -> None:
    """The census -> concrete-rewrite generator: materialize the fold
    (de-invent: +1 rover advance -- the consumer reads the global/field
    INLINE, Enregister splits it), unfold (cache-field: -1 -- the
    repeated read gets NAMED, the split disappears) and Rule 121
    tail-dup / tail-hoist (shared tail <-> per-arm copies; the
    dup-with-CALL variants are the walk-entry lever, 15cd1284)
    candidates as real TU files, then trace-screen each (INERT@TREE /
    INERT@BURN / LIVE).

    The generation machinery is forge's proven span presets
    (``de_invent_candidates`` + ``preset_cache_field`` +
    ``preset_tail_dup`` + ``preset_tail_hoist``: single-write /
    side-effect-free / hazard-checked), driven through a shim so no
    forge run state is created.  ``lines`` (comma-separated) restricts
    to candidates whose edits touch those source lines -- paste the
    ``[lw census: ...]`` lines from the Rover hint for a targeted run."""
    from c2.forge.presets import (de_invent_candidates, preset_cache_field,
                                  preset_tail_dup, preset_tail_hoist)
    from c2.regalloc import lwalk

    want = ({int(x) for x in lines.replace(" ", "").split(",") if x}
            if lines else None)

    shim = _ShimForge(base_text, function)
    n_fold = de_invent_candidates(shim)
    n_unfold = preset_cache_field(shim)
    n_dup = preset_tail_dup(shim)
    n_hoist = preset_tail_hoist(shim)
    if not shim.collected:
        console.print("[yellow]no safe fold/unfold/tail-dup candidates in "
                      "this function[/] (single-write / hazard analysis "
                      "rejected everything -- the residue is likely "
                      "walk-order or sub-source)")
        return

    line_starts = [0]
    for i, ch in enumerate(base_text):
        if ch == "\n":
            line_starts.append(i + 1)

    def _lineno(off: int) -> int:
        import bisect
        return bisect.bisect_right(line_starts, off)

    outdir = Path(".c2-cache") / "spell-cands" / function
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("*.c"):
        old.unlink()

    console.print(f"[bold]{function}[/]: {n_fold} fold (de-invent) + "
                  f"{n_unfold} unfold (cache-field) + "
                  f"{n_dup} tail-dup + {n_hoist} tail-hoist (Rule 121) "
                  "candidate(s)"
                  + (f", restricted to lines {sorted(want)}" if want else ""))

    base_routine = _trace_routine(function, base_text) if screen else None

    kept = 0
    for idx, (tag, edits) in enumerate(shim.collected):
        touched = sorted({_lineno(e.start) for e in edits})
        if want and not (want & set(touched)):
            continue
        kept += 1
        # reverse-offset apply (same discipline as EditPlan.apply)
        buf = base_text
        for e in sorted(edits, key=lambda e: (-e.start, -e.end)):
            buf = buf[:e.start] + e.replacement + buf[e.end:]
        safe_tag = tag.replace("(", "-").replace(")", "").replace(",", "_")
        path = outdir / f"{idx:02d}-{safe_tag}.c"
        path.write_text(buf)

        loc = ",".join(f"L{t}" for t in touched[:4])
        if not screen:
            console.print(f"  {tag:<36} {loc:<20} -> {path}",
                          highlight=False)
            continue
        try:
            cand_routine = _trace_routine(function, buf)
            v = lwalk.spelling_compare(base_routine, cand_routine)
            verdict = v.headline()
        except Exception as exc:            # compile error etc.
            verdict = f"ERROR ({exc})"
        colour = ("green" if verdict.startswith("LIVE")
                  else "red" if verdict.startswith("ERROR") else "dim")
        console.print(f"  {tag:<36} {loc:<20} [{colour}]{escape(verdict)}[/]"
                      f"  {path.name}", highlight=False)
    if not kept:
        console.print("[yellow]no candidate touches the requested lines[/] "
                      "-- the census line may be a USE site whose write is "
                      "elsewhere; rerun without --lines to see all")
    elif screen:
        console.print("\n  [dim]LIVE candidates are worth a byte compile: "
                      "copy the file over the TU (or hand-apply the edit) "
                      "and run c2 decomp-verify -v -f " + function + "; "
                      "INERT@BURN is deprioritize, not proven dead "
                      "(measured ~1/6 false-negative, see module doc)[/]")


def spell(
    function: Annotated[str, typer.Argument(help="function name")],
    candidate: Annotated[Optional[Path], typer.Argument(
        help="candidate .c file (full TU replacement); omit with "
             "--walk-order")] = None,
    baseline: Annotated[Optional[Path], typer.Option(
        "--baseline", help="baseline TU (default: the on-disk file)")] = None,
    tree: Annotated[bool, typer.Option(
        "--tree", help="show the per-statement tree diff")] = False,
    walk_order: Annotated[bool, typer.Option(
        "--walk-order", help="print the walk-vs-layout block map instead "
        "of a spelling compare")] = False,
    fusion: Annotated[bool, typer.Option(
        "--fusion", help="print the fr->lc/lcx fusion map (which RISCified "
        "pairs fused vs a named rejection)")] = False,
    chain: Annotated[bool, typer.Option(
        "--chain", help="print the chain-placement report: blocks in walk "
        "order with call/Rule-125 tags + every conflict's range mapped to "
        "the calls it spans (ABI-fixed EAX credit sources)")] = False,
    suggest: Annotated[bool, typer.Option(
        "--suggest", help="generate fold (de-invent) / unfold (cache-field) "
        "+ Rule 121 tail-dup/tail-hoist candidate TUs from the census "
        "machinery and screen each")] = False,
    lines: Annotated[Optional[str], typer.Option(
        "--lines", help="comma-separated source lines to restrict --suggest "
        "to (the [lw census] lines from the Rover hint)")] = None,
    screen: Annotated[bool, typer.Option(
        "--screen/--no-screen", help="--suggest: trace-screen each "
        "generated candidate (default on; off = just write the files)")] = True,
    seat_flip: Annotated[Optional[str], typer.Option(
        "--seat-flip", help="VAR=REG: counterfactual re-seat of a "
        "committed conflict; reports the ROVER PICKS that change "
        "(c2.regalloc.rover.seat_flip_walk, P6c -- the certified "
        "except-component substrate).  The byte compile stays the "
        "oracle; use this to screen which allocator flip lands a "
        "wanted scratch pick before hunting its source lever.")] = None,
) -> None:
    """Three-stage spelling localizer / walk-order map (docs in module)."""
    from c2.commands.regtrace_native import _find_function
    from c2.regalloc import lwalk

    src_file, _, _, _ = _find_function(function, None)
    base_text = (baseline or src_file).read_text(errors="replace")

    if suggest:
        _suggest(function, base_text, lines, screen)
        return

    base = _trace_routine(function, base_text)

    if seat_flip:
        from c2.regalloc import rover as _rover
        var, _, reg = seat_flip.partition("=")
        res = _rover.seat_flip_walk(base, var.strip(), reg.strip())
        if res is None:
            console.print(f"[red]no committed conflict named '{var}' (or "
                          "unknown register) -- `c2 regtrace` lists the "
                          "named conflicts[/]")
            raise typer.Exit(1)
        console.print(
            f"[bold]{function}[/]: counterfactual re-seat "
            f"{res['var'] or res['conf']} {res['old_reg']} -> {res['new_reg']}"
            f"  (rows touched {len(res['rows_touched'])}, "
            f"ambiguous {len(res['ambiguous'])})")
        if not res["changes"]:
            console.print("  [dim]no rover pick changes -- the flip is "
                          "rover-neutral (its byte effect, if any, is "
                          "main-allocator only)[/]")
        for i, line, old, new in res["changes"]:
            ln = f"L{line}" if line else "L?"
            console.print(f"  fr#{i:<3} {ln:<6} pick {old} -> {new}",
                          highlight=False)
        if res["ambiguous"]:
            console.print(f"  [yellow]ambiguous rows (old seat also owed "
                          f"to another source; kept + new added): "
                          f"{res['ambiguous'][:8]}[/]")
        return

    if not base.get("lw"):
        console.print("[red]no lw records -- rebuild the trace image "
                      "(watcom10.0a scripts/build-trace-image.sh)[/]")
        raise typer.Exit(1)

    if walk_order or fusion or chain:
        if chain:
            _chain_report(function, base)
        if walk_order:
            console.print(f"[bold]{function}[/]: walk-vs-layout block map "
                          "(moved rows = walk-order divergence candidates)")
            rows = lwalk.walk_vs_layout(base)
            for row in rows:
                adv = " ".join(f"{k}:{v}" for k, v in sorted(row["adv"].items()))
                moved = "   [yellow]<<< moved[/]" if row["moved"] else ""
                lo, hi = row["lines"]
                span = f"L{lo}" if lo == hi else f"L{lo}..L{hi}"
                birth = (f" birth#{row['birth']}"
                         if row.get("birth") is not None else "")
                mfg = (f" mfg#{row['post_mfg']}"
                       if row.get("post_mfg") is not None else "")
                ret = " [dim]RET[/]" if row.get("ret") else ""
                console.print(
                    f"  walk#{row['walk']:<3} blk={row['blk']:<4} "
                    f"{span:<16} adv[{adv}]  layout#{row['layout']}"
                    f"{birth}{mfg}{ret}{moved}",
                    highlight=False)
            births = [r.get("birth") for r in rows
                      if isinstance(r.get("birth"), int)]
            if births and births != sorted(births):
                console.print(
                    "  [yellow]birth ordinals run out of walk order[/] -- "
                    "the optimizer RESTRUCTURED the chain after the tree "
                    "burn (reverse-arm class); diff two spellings' birth "
                    "streams with `c2 spell <fn> <cand.c>` to see whether "
                    "a candidate reaches the generation order at all",
                    highlight=False)
            opt_born = sum(1 for r in rows if r.get("birth") == "opt")
            if opt_born:
                console.print(f"  [dim]{opt_born} walked block(s) are "
                              "optimizer-born (blktrim merge products; no "
                              "bo record)[/]", highlight=False)
            # chain-vintage attribution (>= 2026-07-13 image, the br probe):
            # WHICH stage moved each block -- birth -> post-MFG (the
            # pre-conflicts optimizer / MakeFlowGraph DFS/RPO relink /
            # ReturnsToBottom) vs post-MFG -> walk (a later pass).
            from c2.regalloc import rover as _rover
            vin = _rover.chain_vintages(base)
            if vin:
                hauled = [v for v in vin if v["hauled_mfg"]]
                late = [v for v in vin if v["moved_after_mfg"]]
                if hauled:
                    names = ", ".join(
                        f"blk@{v['blk'][-4:]}{' (RET->bottom)' if v['ret'] else ''}"
                        for v in hauled[:6])
                    console.print(
                        f"  [yellow]{len(hauled)} block(s) hauled by "
                        f"MakeFlowGraph[/] (DFS/RPO relink / "
                        f"ReturnsToBottom): {names}", highlight=False)
                if late:
                    console.print(
                        f"  [yellow]{len(late)} block(s) moved AFTER "
                        f"MakeFlowGraph[/] (post-MFG chain != LdStAlloc "
                        f"walk -- a later pass): "
                        + ", ".join(f"blk@{v['blk'][-4:]}" for v in late[:6]),
                        highlight=False)
                if not hauled and not late:
                    console.print("  [dim]chain vintages agree: birth == "
                                  "post-MFG == walk order (no haul)[/]",
                                  highlight=False)
        if fusion:
            console.print(f"[bold]{function}[/]: fr -> fusion map")
            console.print("  [dim]split (fr) at PostOptimize HEAD; the "
                          "fuse decision runs ONCE at PostOptimize END "
                          "(the `cd` compress driver), after Score & co "
                          "perturb adjacency[/]", highlight=False)
            for e in lwalk.fusion_map(base):
                extra = ("" if e["state"] in ("fused",)
                         else f"  ({lwalk.LCX_MEANING.get(e['state'], '')})")
                console.print(
                    f"  fr#{e['fr_idx']:<3} L{e['line']}  {e['state']}{extra}",
                    highlight=False)
            ctx = lwalk.compress_context(base)
            if ctx:
                console.print("\n  [bold]compress attempts (cw \u00d7 chain "
                              "block)[/] -- prev/nextkind 3 = recognized "
                              "MOV half; 0x1NN = ins opcode NN between the "
                              "halves (0x14b = BLOCK HEADER: chain-"
                              "separated)")
                for c in ctx:
                    console.print(
                        f"  ins={c['ins']} blk={c['blk']} op={c['opcode']:#x}"
                        f" pk={c['prevkind']:#x} nk={c['nextkind']:#x}"
                        f"  {c['outcome']}", highlight=False)
            chains = lwalk.score_coalesce_chains(base)
            if chains:
                console.print("\n  [bold]Score coalesce chains for lcx0[/] "
                              "-- sb.into names the earlier instruction "
                              "that consumed each split half")
                for chain in chains:
                    head = (f"fr#{chain['fr_idx']} L{chain['line']} "
                            f"ins={chain['ins']}")
                    console.print(f"  {head}", highlight=False)
                    for node in chain['nodes']:
                        if node['into_line']:
                            where = (f"L{node['into_line']} blk="
                                     f"{node['into_blk']} op="
                                     f"{node['into_opcode']:#x}")
                        elif node['into_blk'] is not None:
                            where = (f"unmarked blk={node['into_blk']} op="
                                     f"{node['into_opcode']:#x}")
                        else:
                            where = "optimizer/deleted intermediate"
                        console.print(
                            f"    {node['ins']} --sb(op="
                            f"{node['opcode']:#x})--> {node['into']}  "
                            f"({where})", highlight=False)
        return

    if candidate is None:
        console.print("[red]need a candidate .c (or --walk-order/--fusion/"
                      "--chain)[/]")
        raise typer.Exit(1)

    cand = _trace_routine(function, candidate.read_text(errors="replace"))
    v = lwalk.spelling_compare(base, cand)

    console.print(f"[bold]verdict:[/] {escape(v.headline())}")
    console.print(f"  advances baseline:  {v.adv_base}")
    console.print(f"  advances candidate: {v.adv_cand}")

    bc = lwalk.birth_compare(base, cand)
    if bc["base_sig"] or bc["cand_sig"]:
        console.print(f"  block births:       {bc['verdict'].lower()} "
                      f"(base {len(bc['base_sig'])} / cand "
                      f"{len(bc['cand_sig'])}"
                      + (f", first delta at birth#{bc['delta'][0]}"
                         if bc["delta"] else "") + ")")
    ib = lwalk.il_birth_compare(base, cand)
    if ib["n_base"] or ib["n_cand"]:
        console.print(f"  IL births (ni):     {ib['verdict'].lower()} "
                      f"(base {ib['n_base']} / cand {ib['n_cand']}"
                      + (", delta lines " + ",".join(
                          f"L{l}" for l in ib["delta_lines"][:6])
                         if ib["delta_lines"] else "") + ")")
    if v.walk_same and (bc["verdict"] == "DIVERGED"
                        or ib["verdict"] == "DIVERGED"):
        console.print(
            "  [dim]births diverged but the walk is identical -- a"
            " post-emission pass re-converged it (a stronger INERT than"
            " tree-level; sibling spellings at the SAME birth-delta lines"
            " may survive)[/]", highlight=False)
    elif v.walk_same and ib["verdict"] == "IDENTICAL" \
            and not v.tree_same:
        console.print(
            "  [dim]trees differ but IL births are already identical --"
            " the canonicalization happened AT tree->IL emission (the"
            " deepest inert; stop this spelling family)[/]",
            highlight=False)

    if tree and v.trees_base is not None and v.tree_same is False:
        console.print("\n[bold]tree diff (per statement)[/]")
        sm = difflib.SequenceMatcher(a=v.trees_base, b=v.trees_cand)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                continue
            for s in v.trees_base[i1:i2]:
                console.print("[red]- " + escape(s.replace("\n", "\n- ")) + "[/]",
                              highlight=False)
            for s in (v.trees_cand or [])[j1:j2]:
                console.print("[green]+ " + escape(s.replace("\n", "\n+ ")) + "[/]",
                              highlight=False)

    if not v.walk_same:
        console.print("\n[bold]walk diff[/] (line-blind)")
        sig = lambda r: (r[1], r[2], r[3], r[4], r[5])
        sm = difflib.SequenceMatcher(a=[sig(r) for r in v.walk_rows_base],
                                     b=[sig(r) for r in v.walk_rows_cand])
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for di in range(i2 - i1):
                    x = v.walk_rows_base[i1 + di]
                    y = v.walk_rows_cand[j1 + di]
                    if x[6] != y[6]:
                        console.print(
                            f"~ FLIP  {_fmt_row(x)}  ->  "
                            f"{'RISC' if y[6] else 'skip'}", highlight=False)
                continue
            for r in v.walk_rows_base[i1:i2]:
                console.print(f"[red]- {_fmt_row(r)}[/]", highlight=False)
            for r in v.walk_rows_cand[j1:j2]:
                console.print(f"[green]+ {_fmt_row(r)}[/]", highlight=False)


def _chain_report(function: str, base: dict) -> None:
    """The chain-placement report (--chain).

    Root-cause lens for [score]-credit seat verdicts: a CALL inside a
    conflict's chain-order range is an ABI-FIXED EAX credit -- no
    savings/order/decl lever can remove it; the lever is the range /
    the return block's CHAIN placement (Rule 125 chain vs layout).
    Discovered on start_samples (see the pcsound.c ledger + watcom10.0a
    notes/start-samples-p5p6.md)."""
    from c2.regalloc import lwalk
    rep = lwalk.chain_placement(base)
    console.print(f"[bold]{function}[/]: chain-placement report "
                  "(blocks in WALK/chain order)")
    for b in rep["blocks"]:
        lines = sorted(b["lines"])
        span = (f"L{lines[0]}" if len(lines) == 1
                else f"L{lines[0]}..L{lines[-1]}" if lines else "-")
        tags = []
        if b["calls"]:
            tags.append(f"[cyan]{b['calls']} call(s)[/]")
        if b.get("moved_late"):
            tags.append("[yellow]chained-late (Rule 125: earlier source "
                        "line than a preceding chain block)[/]")
        console.print(f"  blk={b['blk']:<4} {span:<14} {' '.join(tags)}",
                      highlight=False)
    console.print("\n  [bold]conflict ranges vs calls[/] (a call inside "
                  "the span = ABI-fixed EAX credit at that ins)")
    for c in rep["conflicts"]:
        nm = c["name"] or c["conf"]
        p0, p1 = c["span"]
        span = f"walk[{p0}..{p1}]" if p0 is not None else "walk[?]"
        if c["calls_in_range"]:
            calls = ", ".join(
                f"L{x['line']} blk={x['blk']}" for x in c["calls_in_range"])
            console.print(
                f"  {nm:<10} sav={c['savings']:<4} -> {c['reg'] or '?':<4} "
                f"{span:<16} [red]SPANS CALL(s): {calls}[/]",
                highlight=False)
        elif not c["span_known"]:
            console.print(
                f"  {nm:<10} sav={c['savings']:<4} -> {c['reg'] or '?':<4} "
                f"{span:<16} [dim]range endpoint outside the lw walk "
                "(inserted ins) -- span unknown[/]", highlight=False)
        else:
            console.print(
                f"  {nm:<10} sav={c['savings']:<4} -> {c['reg'] or '?':<4} "
                f"{span:<16} clean", highlight=False)
    console.print(
        "\n  [dim]lever note: SPANS-CALL on a value PS seats in EDX/EBX "
        "means the fail/return block is chained past a call the value "
        "does not otherwise reach -- the source lever is block-count/"
        "placement (e.g. an extra tail block pulls return blocks "
        "earlier), not savings or decl order.[/]")
