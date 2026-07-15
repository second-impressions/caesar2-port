"""Find AST-level source patterns that cache array row pointers.

Watcom 10.0a often emits different code for

    p = &array[i]; p->field ...

than for repeated explicit indexing

    array[i].field ...

or byte-offset macros.  In PS.EXE many hot entity-list functions keep the
index expression live and fold the global base + field into each memory
operand instead of materializing a row pointer in a callee-save register.
This command lists likely candidates for that source-level refactor.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import typer
from pycparser import c_ast, c_generator

from c2.commands.c_source import parse_c


ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "decomp" / "src"

INTERESTING_ARRAYS = {
    "figure_list",
    "arrow_list",
    "unit_list",
    "army_list",
    "citizen_list",
    "city_map",
    "battle_map",
    "region_map",
    "pseudo_map",
}

_GEN = c_generator.CGenerator()


@dataclass
class Hit:
    file: Path
    line: int
    function: str
    var: str
    array: str
    expr: str
    uses: int
    kind: str
    sites: int = 1


def _expr_text(node: c_ast.Node | None) -> str:
    if node is None:
        return ""
    try:
        return _GEN.visit(node)
    except Exception:
        return type(node).__name__


def _strip_casts(node: c_ast.Node) -> c_ast.Node:
    while isinstance(node, c_ast.Cast):
        node = node.expr
    return node


def _id_name(node: c_ast.Node) -> str | None:
    node = _strip_casts(node)
    if isinstance(node, c_ast.ID):
        return node.name
    return None


def _contains_mul_const(node: c_ast.Node) -> bool:
    """Heuristic for row-address arithmetic: i * stride, stride * i."""
    node = _strip_casts(node)
    if isinstance(node, c_ast.BinaryOp) and node.op == "*":
        return isinstance(_strip_casts(node.left), c_ast.Constant) or isinstance(_strip_casts(node.right), c_ast.Constant)
    for _name, child in node.children():
        if _contains_mul_const(child):
            return True
    return False


def _match_cached_row_expr(node: c_ast.Node, arrays: set[str]) -> tuple[str, str, str] | None:
    """Return (array, index/expression, kind) for cached-row expressions.

    Recognised AST shapes:
      * &array[index]
      * ((char *)array) + (index * stride)
      * (index * stride) + ((char *)array)
    """
    node = _strip_casts(node)

    if isinstance(node, c_ast.UnaryOp) and node.op == "&":
        target = _strip_casts(node.expr)
        if isinstance(target, c_ast.ArrayRef):
            arr = _id_name(target.name)
            if arr and (not arrays or arr in arrays):
                return arr, _expr_text(target.subscript), "addr-of-index"

    if isinstance(node, c_ast.BinaryOp) and node.op == "+":
        left_arr = _id_name(node.left)
        right_arr = _id_name(node.right)
        if left_arr and (not arrays or left_arr in arrays) and _contains_mul_const(node.right):
            return left_arr, _expr_text(node.right), "offset-add"
        if right_arr and (not arrays or right_arr in arrays) and _contains_mul_const(node.left):
            return right_arr, _expr_text(node.left), "offset-add"

    return None


class _IDUseCounter(c_ast.NodeVisitor):
    def __init__(self, name: str) -> None:
        self.name = name
        self.count = 0

    def visit_ID(self, node: c_ast.ID) -> None:  # noqa: N802 - pycparser API
        if node.name == self.name:
            self.count += 1


class _FunctionScanner(c_ast.NodeVisitor):
    def __init__(self, path: Path, arrays: set[str], min_uses: int) -> None:
        self.path = path
        self.arrays = arrays
        self.min_uses = min_uses
        self.function = "?"
        self.body: c_ast.Compound | None = None
        self.hits: list[Hit] = []

    def visit_FuncDef(self, node: c_ast.FuncDef) -> None:  # noqa: N802
        old_func, old_body = self.function, self.body
        self.function = node.decl.name
        self.body = node.body
        self.visit(node.body)
        self.function, self.body = old_func, old_body

    def visit_Decl(self, node: c_ast.Decl) -> None:  # noqa: N802
        if node.init is not None and node.name:
            self._maybe_add(node.name, node.init, node.coord.line if node.coord else 0, "decl")
        # Keep walking initializer for nested declarations / IDs.
        self.generic_visit(node)

    def visit_Assignment(self, node: c_ast.Assignment) -> None:  # noqa: N802
        if isinstance(node.lvalue, c_ast.ID):
            self._maybe_add(node.lvalue.name, node.rvalue, node.coord.line if node.coord else 0, "assign")
        self.generic_visit(node)

    def _maybe_add(self, var: str, expr: c_ast.Node, line: int, prefix: str) -> None:
        if self.body is None:
            return
        m = _match_cached_row_expr(expr, self.arrays)
        if not m:
            return
        arr, idx_expr, kind = m
        counter = _IDUseCounter(var)
        counter.visit(self.body)
        # The declaration/assignment itself contributes one ID occurrence for
        # assignment lvalues but not declarations; treat both uniformly by using
        # post-candidate references as a rough priority metric.
        uses = max(counter.count - 1, 0)
        if uses < self.min_uses:
            return
        self.hits.append(Hit(
            file=self.path,
            line=line,
            function=self.function,
            var=var,
            array=arr,
            expr=idx_expr,
            uses=uses,
            kind=f"{prefix}:{kind}",
        ))


def _scan_file(path: Path, arrays: set[str], min_uses: int) -> list[Hit]:
    try:
        ast = parse_c(path.read_text(errors="replace"), filename=str(path))
    except Exception as e:
        typer.echo(f"warning: failed to parse {path}: {e}", err=True)
        return []
    scanner = _FunctionScanner(path, arrays, min_uses)
    scanner.visit(ast)
    return scanner.hits


def row_caches(
    path: Path = typer.Argument(SRC_DIR, help="Source file or directory to scan"),
    array: list[str] | None = typer.Option(None, "--array", "-a", help="Restrict to array/global name; repeatable"),
    all_arrays: bool = typer.Option(False, "--all", help="Do not restrict to known entity/map arrays"),
    min_uses: int = typer.Option(2, "--min-uses", help="Minimum uses of cached pointer inside function"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum rows to show"),
) -> None:
    """List candidate cached-row-pointer refactors using the C AST."""
    arrays = set(array or [])
    if not arrays and not all_arrays:
        arrays = set(INTERESTING_ARRAYS)

    path = path.resolve()
    files = [path] if path.is_file() else sorted(path.glob("*.c"))
    hits: list[Hit] = []
    for f in files:
        hits.extend(_scan_file(f, arrays, min_uses))

    # Collapse repeated row-pointer reassignments inside one function.  Those
    # are still an important signal, so retain a `sites` count, but one row per
    # function-local cache is much more useful for triage.
    merged: dict[tuple[Path, str, str, str, str], Hit] = {}
    for h in hits:
        key = (h.file, h.function, h.var, h.array, h.expr)
        prev = merged.get(key)
        if prev is None:
            merged[key] = h
        else:
            prev.sites += 1
            prev.uses = max(prev.uses, h.uses)
            prev.line = min(prev.line, h.line)
            if h.kind not in prev.kind:
                prev.kind += "," + h.kind
    hits = list(merged.values())
    hits.sort(key=lambda h: (-h.uses, -h.sites, h.file.name, h.line))

    print(f"{'uses':>4} {'sites':>5}  {'file:line':24} {'function':32} {'array':14} {'var':8} kind  expr")
    print("-" * 128)
    for h in hits[:limit]:
        loc = f"{h.file.relative_to(ROOT)}:{h.line}"
        print(f"{h.uses:4d} {h.sites:5d}  {loc:24} {h.function:32} {h.array:14} {h.var:8} {h.kind:16} {h.expr}")
    if len(hits) > limit:
        print(f"... {len(hits) - limit} more")
