"""Multi-way dispatch hint: `switch` (jump table) vs if/else-if chain.

Empirical basis (byte-exact corpus, 2026-06):

  * Every byte-exact function whose SOURCE uses a `switch` (>=3 cases)
    compiles to a PS jump table (`jmp [reg*4 + table]`) -- 5/5, no
    exceptions.
  * Every byte-exact function whose source uses an if/else-if chain
    compiles WITHOUT a jump table (71/71).
  * No byte-exact function has a jump table without a source `switch`.

So `switch` <=> jump table is a clean bidirectional equivalence in this
codebase.  A diffing function that violates it is mis-shaped:

  * source `switch` but PS has no jump table  -> PS used an if/else-if
    chain (the cases ComTail-merge, or carry compound bodies); rewrite the
    `switch` as an explicit if/else-if chain in PS's branch order
    (Rule 95).  This was `rebuild_figures_image_data` (260b -> 0).
  * PS jump table but source has no `switch`  -> use a `switch`.

This module surfaces that mismatch as a `decomp-verify -v` header hint and
in `--json` (`functions[].dispatch_hint`).  See Rule 95 in
docs/watcom-codegen-patterns.md.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Optional

import typer
from pycparser import c_ast

# A switch jump table is an INDIRECT jmp through a table:
#   jmp [reg*4 + table]        (scale applied in the operand), or
#   jmp cs:[reg + table]       (index pre-scaled by a `shl reg,2` earlier).
# Both reference the table base as a displacement, so either a *N scale OR a
# hex displacement inside the brackets marks it.  (Plain `jmp [reg]` with no
# displacement is a bare function-pointer indirect jump, not a table.)
_JT_SCALE = re.compile(r"\*[48]\b")
_JT_DISP = re.compile(r"\[[^\]]*\+\s*0x[0-9a-f]+\]")


def ps_has_jump_table(insns) -> bool:
    """True if the PS disasm contains a `jmp` through an indexed table.

    ``insns`` is the decomp-verify ``InsnT`` list: tuples whose 4th element
    is the ``"mnemonic op_str"`` text.  A `call [...]` is a function-pointer
    table, NOT a switch, so we only match `jmp`.  Catches both inline-scaled
    (`jmp [eax*4+t]`) and pre-scaled (`shl ebp,2; jmp [ebp+t]`) tables.
    """
    for t in insns:
        text = t[3] if len(t) > 3 else ""
        if not text.startswith("jmp") or "[" not in text:
            continue
        if _JT_SCALE.search(text) or _JT_DISP.search(text):
            return True
    return False


@dataclass
class SwitchInfo:
    cases: int
    fall: int


class _SwitchVisitor(c_ast.NodeVisitor):
    def __init__(self) -> None:
        self.switches: list[tuple[int, int]] = []

    def visit_Switch(self, node: c_ast.Switch) -> None:
        items = getattr(node.stmt, "block_items", None) or []
        cases = fall = 0
        for it in items:
            if isinstance(it, c_ast.Case):
                cases += 1
                stmts = it.stmts or []
                if not stmts or not isinstance(
                    stmts[-1],
                    (c_ast.Break, c_ast.Return, c_ast.Goto, c_ast.Continue),
                ):
                    fall += 1
        self.switches.append((cases, fall))
        self.generic_visit(node)


@lru_cache(maxsize=1)
def _switch_index(src_dir: str = "decomp/src") -> dict[str, SwitchInfo]:
    """{func_name: SwitchInfo} for every function whose source contains a
    `switch` with >=3 cases.  Parsed once (AST, via classify_source)."""
    from c2.commands.c_source import classify_source

    out: dict[str, SwitchInfo] = {}
    for cf in sorted(Path(src_dir).glob("*.c")):
        try:
            fd = classify_source(cf.read_text(), cf.name)
        except Exception:
            continue
        for f in fd.func_defs:
            v = _SwitchVisitor()
            v.visit(f)
            big = [(c, fl) for c, fl in v.switches if c >= 3]
            if big:
                out[f.decl.name] = SwitchInfo(
                    cases=max(c for c, _ in big),
                    fall=sum(fl for _, fl in big),
                )
    return out


def detect_dispatch_mismatch(name: str | None, orig_insns) -> str | None:
    """Return a one-line hint when the source dispatch construct disagrees
    with PS's (switch<=>jump-table), else None."""
    if not name:
        return None
    jt = ps_has_jump_table(orig_insns)
    sw = _switch_index().get(name)
    if sw is not None and not jt:
        fall = f", {sw.fall} fall-through" if sw.fall else ""
        return (
            f"source uses switch ({sw.cases} cases{fall}) but PS has NO jump "
            f"table — PS compiled an if/else-if chain. Rewrite the switch as "
            f"explicit if/else-if in PS's branch order (Rule 95); read "
            f"`c2 disasm {name}` for the cmp sequence."
        )
    if jt and sw is None:
        return (
            f"PS uses a jump table but the source has no switch — use a "
            f"`switch` to reproduce the jump-table dispatch (Rule 95)."
        )
    return None


# ── CLI command (`c2 dispatch-hints`) ──────────────────────────────────
#
# Single-purpose triager for the switch<=>jump-table lever (Rule 95).
# Reads the persisted ``dispatch_hint`` string from
# ``.c2-cache/verify.json`` (computed by ``detect_dispatch_mismatch`` in
# the verifier), the same line that surfaces in ``decomp-verify -v``.


def dispatch_hints(
    name: Annotated[Optional[str], typer.Argument(
        help="function name (omit with --corpus)")] = None,
    corpus: Annotated[bool, typer.Option(
        "--corpus", help="list every diffing function whose source dispatch "
        "construct disagrees with PS (switch<=>jump-table)")] = False,
    as_json: Annotated[bool, typer.Option(
        "--json", help="emit the dispatch_hint record(s) as JSON")] = False,
) -> None:
    """Multi-way dispatch mismatch: `switch` (jump table) vs if/else-if chain.

    Flags functions whose source uses a `switch` where PS compiled an
    if/else-if chain (no jump table), or vice versa (Rule 95).  Surfaces
    the same ``functions[].dispatch_hint`` the verifier persists.
    """
    from c2.commands.verify_json import get_verify_json
    try:
        doc = get_verify_json()
    except FileNotFoundError:
        typer.secho("no .c2-cache/verify.json -- run `c2 decomp-verify "
                    "--json` once", fg="red", err=True)
        raise typer.Exit(1)
    funcs = doc.get("functions", [])
    from c2.regalloc.seat_recon import fmt_shape_cell as _sc

    if not corpus:
        if not name:
            typer.secho("[!] provide a function name or --corpus", fg="red",
                        err=True)
            raise typer.Exit(2)
        fn = next((f for f in funcs if f["name"] == name), None)
        if fn is None:
            typer.secho(f"[!] {name}: not in the verify set (byte-exact, "
                        "unknown, or cache stale)", fg="yellow")
            raise typer.Exit(1)
        dh = fn.get("dispatch_hint")
        if not dh:
            if as_json:
                typer.echo("null")
            else:
                typer.secho(f"  ✓  {name}: dispatch construct matches PS "
                            "(switch<=>jump-table agree)", fg="green")
            return
        if as_json:
            typer.echo(json.dumps({"name": name, "dispatch_hint": dh},
                                  indent=2))
            return
        typer.echo(f"  ✗  {name}  [{_sc(fn.get('shape_distance'))}]", fg="yellow")
        typer.echo(f"      {dh}")
        return

    # corpus mode
    rows = [f for f in funcs
            if f.get("diff_byte_count", 0) > 0 and f.get("dispatch_hint")]
    _RANK = {"ir": 0, "width": 1, "spill": 2, "seat": 3}
    rows.sort(key=lambda f: (_RANK.get((f.get("shape_distance") or {}).get("fix_next"), 9),
                             -int((f.get("shape_distance") or {}).get("total", 0))))
    if as_json:
        typer.echo(json.dumps(
            [{"name": f["name"],
              "shape_cell": _sc(f.get("shape_distance")),
              "dispatch_hint": f["dispatch_hint"]} for f in rows], indent=2))
        return
    typer.secho(f"\n# dispatch-hints: {len(rows)} diffing function(s) with a "
                "switch<=>jump-table mismatch (Rule 95)\n", fg="cyan",
                bold=True)
    for f in rows:
        typer.secho(f"  ✗  {f['name']}  [{_sc(f.get('shape_distance'))}]", fg="yellow")
        typer.echo(f"      {f['dispatch_hint']}")
