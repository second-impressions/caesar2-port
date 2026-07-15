"""``c2 sweep`` -- iterated forge-preset byte-oracle sweep for one function.

Greedy coordinate descent over the mechanical source-lever space:

  1. Generate the full forge preset battery for the CURRENT source
     (decl swaps/perms, statement reorders, commutes, RMW forms,
     de-invent/cache, if-inversions, line splits -- ~200-700 variants).
  2. Byte-compile every variant with the ForgeBuilder LE fast path
     (~0.1 s/variant, verifier byte parity) and judge by the layered
     shape distance FIRST, byte count second (Hard Rule #3).
  3. Take the best variant as the new baseline and repeat (default 3
     passes) -- COMPOSED edits that no single-pass probe reaches are
     exactly what closed evolve_region (ad1de9e7: two decl swaps,
     56->6->0 bd) after hand-probing had written the class off.

The sweep NEVER touches the working tree: the winning variant is
written to ``.c2-cache/sweep/<fn>/best.c`` and the winning edit chain
is printed as a unified diff for hand application (re-derive on fresh
disk if a parallel session may have moved the file -- Hard Rule #1).

When to use:
  * seat/slot/rover residues where `worklist` names decl-order or
    tie-group levers -- the sweep exhausts the WHOLE permutation space
    the hints can only sample;
  * after any hand shape-fix, as a cheap "is there a mechanical
    residue-closer?" pass;
  * NOT for ir-dominant wrong-shape functions (fix the shape first --
    the battery only reorders/respells what is already there).

Results (2026-07-09): evolve_region 56->0 (BYTE-EXACT), top_it 116->10
(rejected -- Rule 49b idiom trade, see the function comment),
set_route_elastic_range ir 17->9, mid3_line_with_sides_base 641->405.
"""
from __future__ import annotations

import difflib
import hashlib
import os
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

console = Console()

# The temp-set / order / form levers.  ir-shape presets (loop_form,
# guard_const, ...) are excluded: they change semantics-adjacent
# structure and belong to forge's judged search, not a blind sweep.
SWEEP_PRESETS = [
    "tie_group", "decl_swap_all", "decl_perm", "decl_init_split",
    "decl_hoist", "stmt_reorder_deep", "stmt_swap_adjacent",
    "commute_all", "relorder_all", "shift1", "bytemask",
    "compound_assign_expand", "compound_assign_contract",
    "incdec_toggle", "de_invent_all", "cache_literal", "cache_field",
    "ternary_split", "if_fission", "if_invert", "rmw_split",
    "line_split",
    # Rule 121 (2026-07-10): shared-tail <-> per-arm-dup, both directions.
    # Control-flow-neutral by construction; the dup-with-call variants are
    # the rover walk-entry lever (mid3_line_no_sides_base 15cd1284).
    "tail_dup", "tail_hoist",
]


def _apply_edits(text: str, edits) -> str:
    buf = text
    for e in sorted(edits, key=lambda e: (-e.start, -e.end)):
        buf = buf[: e.start] + e.replacement + buf[e.end :]
    return buf


def _battery(text: str, fn: str) -> list[tuple[str, tuple]]:
    from c2.commands.spell import _ShimForge
    from c2.forge.presets import PRESETS

    out: list[tuple[str, tuple]] = []
    for pname in SWEEP_PRESETS:
        preset = PRESETS.get(pname)
        if preset is None:
            continue
        shim = _ShimForge(text, fn)
        try:
            preset(shim)
        except Exception:  # noqa: BLE001 -- presets are best-effort feeders
            continue
        for tag, edits in shim.collected:
            out.append((f"{pname}:{tag}", edits))
    return out


def _score_tuple(sc) -> tuple:
    if not sc.ok:
        return (10**9, 10**9)
    shape = sc.shape.get("shape", 10**6) if sc.shape else 10**6
    return (shape, sc.bytes)


def sweep(
    function: Annotated[str, typer.Argument(help="function name")],
    file: Annotated[Optional[str], typer.Option(
        "--file", help="TU basename (default: located via the AST index)")] = None,
    passes: Annotated[int, typer.Option(
        "--passes", help="max greedy passes (each re-generates the battery "
        "on the previous winner)")] = 3,
    top: Annotated[int, typer.Option(
        "--top", help="leaderboard rows to print per pass")] = 8,
) -> None:
    """Iterated forge-preset byte-oracle sweep (module doc for the method)."""
    from c2.commands.regtrace import _find_function
    from c2.forge import judge, ps_ref
    from c2.forge.build import ForgeBuilder

    src_file, _, _, _ = _find_function(function, file)
    base_text = src_file.read_text(errors="replace")
    tu = os.path.basename(str(src_file))

    ps = ps_ref.load(function)
    builder = ForgeBuilder(source_root=src_file.resolve().parents[1])
    try:
        builder.warm()
        br = builder.compile_one(file=tu, function=function,
                                 source_text=base_text, timeout=120)
        sc = judge.score(ps, br.code, br.fixups, br.line_marks)
        best_score, best_text = _score_tuple(sc), base_text
        console.print(f"[bold]{function}[/] ({tu})  baseline: "
                      f"shape {best_score[0]} · {best_score[1]} bd")
        if best_score == (0, 0):
            console.print("[green]already byte-exact -- nothing to sweep[/]")
            return

        chain: list[str] = []
        for p in range(1, passes + 1):
            cands = _battery(best_text, function)
            seen: set[str] = set()
            rows: list[tuple[tuple, str, str]] = []
            t0 = time.time()
            for tag, edits in cands:
                try:
                    txt = _apply_edits(best_text, edits)
                except Exception:  # noqa: BLE001
                    continue
                h = hashlib.sha1(txt.encode()).hexdigest()
                if h in seen:
                    continue
                seen.add(h)
                try:
                    br = builder.compile_one(file=tu, function=function,
                                             source_text=txt, timeout=90)
                    s = judge.score(ps, br.code, br.fixups, br.line_marks)
                except Exception:  # noqa: BLE001
                    continue
                rows.append((_score_tuple(s), tag, txt))
            rows.sort(key=lambda r: r[0])
            console.print(f"\n[bold]pass {p}[/]: {len(seen)} variants in "
                          f"{time.time() - t0:.0f}s")
            for s, tag, _ in rows[:top]:
                mark = "[green]" if s < best_score else "[dim]"
                console.print(f"  {mark}shape {s[0]:>3} · {s[1]:>5} bd  "
                              f"{tag}[/]", highlight=False)
            if not rows or rows[0][0] >= best_score:
                console.print("  [dim]no improvement -- battery exhausted[/]")
                break
            best_score, tag, best_text = rows[0][0], rows[0][1], rows[0][2]
            chain.append(tag)
            if best_score == (0, 0):
                break
    finally:
        builder.shutdown()

    if not chain:
        console.print("\n[yellow]sweep neutral[/] -- the mechanical lever "
                      "space is exhausted; the residue needs a hand shape "
                      "fix (c2 diagnose / dossier) or is sub-source.")
        return

    outdir = Path(".c2-cache") / "sweep" / function
    outdir.mkdir(parents=True, exist_ok=True)
    best_path = outdir / "best.c"
    best_path.write_text(best_text)
    exact = " [bold green]BYTE-EXACT[/]" if best_score == (0, 0) else ""
    console.print(f"\n[bold]winner[/]: shape {best_score[0]} · "
                  f"{best_score[1]} bd{exact}  via " + " → ".join(chain))
    console.print(f"  full TU: {best_path}")
    console.print("  [bold]edit chain as diff[/] (re-derive on FRESH disk "
                  "before applying -- Hard Rule #1):")
    for ln in difflib.unified_diff(
            base_text.splitlines(), best_text.splitlines(),
            lineterm="", n=2):
        if ln.startswith(("---", "+++")):
            continue
        colour = ("green" if ln.startswith("+")
                  else "red" if ln.startswith("-") else "dim")
        console.print(f"  [{colour}]{ln}[/]", highlight=False)
    if best_score != (0, 0):
        console.print("\n  [dim]verify the winner is PS-faithful before "
                      "applying: a shape drop can be a false improvement "
                      "when Rule 49b/151 contradicts it (worked example: "
                      "top_it's cast-vs-mask trade) -- read the -v hints on "
                      "the applied result.[/]")
