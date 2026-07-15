"""``c2 tree-diff <func>`` -- compare the FORWARD IR tree (from the
instrumented compile trace of our decomp source) against the REVERSED IR
tree (recovered from PS.EXE asm via :mod:`c2.binir`).

End-to-end pipeline::

    PS.EXE asm  --binir.recover-->  RecoveredOp[]  --to_tree-->  TreeShape  ──┐
                                                                                ├── tree_diff
    decomp.c   --wcc386 trace-->   IRForest         --to_tree-->  TreeShape  ──┘

Structural differences between the two trees identify what intermediate
constructs (temps, extra stores, etc.) PS`s source had that ours doesn`t
(or vice versa).  See :mod:`c2.tree_diff` for the tree representation and
the diff machinery; this command wires it up to the existing trace +
disasm pipelines.

Usage::

    uv run c2 tree-diff get_region_2x2_start
    uv run c2 tree-diff market_image --file evolver.c
    uv run c2 tree-diff move_army --raw      # show full tree dumps too

The output has three sections:

  * **FORWARD** (from trace) -- our build`s actual IR forest, one tree per
    statement root.  This is ground truth for what wcc386 made of OUR
    source.
  * **REVERSE** (from PS asm) -- what binir could recover from PS.EXE`s
    bytes, expressed as a tree.  Currently PARTIAL -- binir`s pattern
    catalog bounds the coverage; unrecognised offsets simply don`t emit a
    node, so the reverse forest is usually smaller.  As binir grows the
    gap closes.
  * **DIFFS** -- structural differences (op_mismatch, children_mismatch,
    only_in_a, only_in_b) with dotted-index paths.

The ``only_in_a`` (forward-only) diffs are usually the most actionable:
they show intermediate constructs (like a Rule 17b `s` temp ASSIGN chain)
that PS`s source didn`t have, so removing them moves toward byte-exact.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

from c2 import binir, regalloc
from c2.commands.decomp_verify import _disasm_for_diff
from c2.tree_diff import (
    Difference,
    TreeShape,
    diff_function,
    shape_from_binir_ops,
    shape_from_ir_forest,
    tree_diff,
)


REPO = Path(__file__).resolve().parents[2]
SRC_DIR = REPO / "decomp" / "src"
INCLUDE_DIR = REPO / "decomp" / "include"


def _get_ir_forest_for(name: str, file: str | None):
    """Run the instrumented compiler over the TU containing ``name`` and
    return ``(routine_dict, src_file_path)``.

    Mirrors c2.commands.regtrace._container_rows but only fetches the
    routine + IR forest.  Returns (None, src_path) when the trace doesn`t
    have a matching routine (rare; usually means the function is
    inlined-only or the name didn`t match)."""
    from c2.commands.regtrace import _find_function
    src_file, start, end, _preamble = _find_function(name, file)
    files = {"TARGET.C": src_file.read_text(errors="replace")}
    for h in INCLUDE_DIR.glob("*.h"):
        files[h.name.upper()] = h.read_text(errors="replace")
    td = regalloc.trace_compile(files, main="TARGET.C")
    routine = td["by_func"].get(name) or td["by_func"].get(name.rstrip("_"))
    return routine, src_file


def _get_ps_recovered_ops(name: str):
    """Slice the function`s bytes out of PS.EXE`s LE code segment, disassemble,
    and run binir.  Returns ``(insns, recovered_ops, ps_size)`` or
    ``(None, [], 0)`` when no symbol named ``name`` exists in symbols.json
    (note: even non-exported functions are listed there since they come from
    Watcom`s ``-d1`` line-number debug info, not from the export table)."""
    from c2.commands.decomp_verify import _load_le_code_and_fixups
    exe_path = REPO / "data" / "PS.EXE"
    sym_path = REPO / "data" / "out" / "symbols.json"
    if not exe_path.exists() or not sym_path.exists():
        return None, [], 0
    syms = json.loads(sym_path.read_text())
    code_syms = sorted(
        [s for s in syms.get("symbols", []) if s.get("is_code")],
        key=lambda s: s["offset"],
    )
    # Find the target by name; size = distance to the next code symbol when
    # not explicitly recorded.
    by_name = {s["name"]: i for i, s in enumerate(code_syms)}
    idx = by_name.get(name) or by_name.get(name + "_") or by_name.get(name.rstrip("_"))
    if idx is None:
        return None, [], 0
    target = code_syms[idx]
    if "size" in target and target["size"]:
        size = target["size"]
    elif idx + 1 < len(code_syms):
        size = code_syms[idx + 1]["offset"] - target["offset"]
    else:
        vsize = syms.get("memory_map", {}).get("objects", [{}])[0].get(
            "virtual_size", target["offset"] + 200)
        size = vsize - target["offset"]
    orig_code, _orig_fix = _load_le_code_and_fixups(exe_path)
    ps_bytes = orig_code[target["offset"]: target["offset"] + size]
    insns = _disasm_for_diff(ps_bytes)
    ops = binir.recover(insns)
    return insns, ops, size


def _render_tree_dump(label: str, trees: list[TreeShape], *, max_depth: int = 6
                     ) -> list[str]:
    out = [f"=== {label} ({len(trees)} root{'s' if len(trees) != 1 else ''}) ==="]
    if not trees:
        out.append("  (no roots recovered)")
        return out
    for i, t in enumerate(trees):
        out.append(f"--- {label.lower()}[{i}] ---")
        out.append(_truncated_dump(t, max_depth=max_depth))
    return out


def _truncated_dump(tree: TreeShape, *, max_depth: int, depth: int = 0
                    ) -> str:
    pad = "  " * depth
    head = f"{pad}{tree.op}"
    if tree.detail:
        keys = sorted(k for k in tree.detail if k not in ("offset",))
        if keys:
            head += "  " + " ".join(f"{k}={tree.detail[k]}" for k in keys)
    if depth >= max_depth and tree.children:
        return head + f"  (+{len(tree.children)} child subtrees)"
    parts = [head]
    for c in tree.children:
        parts.append(_truncated_dump(c, max_depth=max_depth, depth=depth + 1))
    return "\n".join(parts)


def _render_diffs(diffs: list[Difference]) -> list[str]:
    if not diffs:
        return ["=== DIFFS ===", "  (none -- forward and reverse trees match)"]
    out = [f"=== DIFFS ({len(diffs)} difference{'s' if len(diffs) != 1 else ''}) ==="]
    # Group by kind for readability.
    from collections import Counter
    counts = Counter(d.kind for d in diffs)
    out.append("  by kind: "
               + ", ".join(f"{k}={c}" for k, c in sorted(counts.items())))
    for d in diffs:
        fwd = d.a if d.a is not None else "-"
        rev = d.b if d.b is not None else "-"
        out.append(f"  [{d.kind}] {d.path}: forward={fwd!r}  reverse={rev!r}"
                   + (f"  ({d.note})" if d.note else ""))
    return out


def tree_diff_cmd(
    name: Annotated[str, typer.Argument(help="function name to diff")],
    file: Annotated[Optional[str], typer.Option(
        "--file", help="source filename hint (disambiguates duplicates)")] = None,
    raw: Annotated[bool, typer.Option(
        "--raw", help="dump the full forward+reverse tree forests too "
                      "(default: just the diff)")] = False,
    max_depth: Annotated[int, typer.Option(
        "--max-depth", help="truncate tree printing at this depth")] = 6,
):
    """Compare the forward IR tree (from the trace) against the reverse
    IR tree (from PS.EXE asm).

    Use this to identify SOURCE-LEVEL intermediates (like the Rule 17b
    ``s`` temp) that exist in your decomp but didn`t in PS`s source -- they
    show up as `only_in_a` (forward-only) diffs.
    """
    try:
        routine, src_file = _get_ir_forest_for(name, file)
    except Exception as exc:
        typer.secho(f"trace for {name}: {exc}", fg="red", err=True)
        raise typer.Exit(2)
    if routine is None or "ir" not in routine:
        typer.secho(f"{name}: no IR forest in trace (function not compiled "
                    f"or not in {file or 'auto-detected TU'})", fg="red", err=True)
        raise typer.Exit(2)
    forest = routine["ir"]

    insns, recovered_ops, ps_size = _get_ps_recovered_ops(name)
    if insns is None:
        typer.secho(f"{name}: not exported by PS.EXE -- reverse side is empty",
                    fg="yellow", err=True)
    typer.secho(f"\n=== c2 tree-diff: {name} ===", fg="green", bold=True)
    typer.secho(f"  source TU: {src_file.relative_to(REPO)}", fg="cyan")
    typer.secho(f"  forward roots: {len(forest.roots)}", fg="cyan")
    typer.secho(f"  PS asm size: {ps_size or 'n/a'} b, binir recovered: "
                f"{len(recovered_ops)} pattern{'s' if len(recovered_ops) != 1 else ''}",
                fg="cyan")

    result = diff_function(forest, recovered_ops)
    if raw:
        for line in _render_tree_dump("FORWARD (trace)", result["forward"],
                                       max_depth=max_depth):
            typer.echo(line)
        for line in _render_tree_dump("REVERSE (PS asm)", result["reverse"],
                                       max_depth=max_depth):
            typer.echo(line)
    for line in _render_diffs(result["diffs"]):
        typer.echo(line)
