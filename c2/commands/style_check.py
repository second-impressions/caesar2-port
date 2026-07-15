"""Source-level style check for decomp-verify (AST-based).

Scans a decompiled C function and emits **hints/warnings** (never errors)
about source forms that are either:

  * **not-observed** (``warn``): forms that never appear in the byte-exact
    PS.EXE corpus, so they are almost certainly un-PS-like and should be
    rewritten to the canonical house form.

  * **noise** (``info``): forms proven byte-interchangeable with another
    spelling, so toggling them will NOT move bytes — useful to stop an
    agent from chasing a diff by flipping a codegen-neutral form.

The ``offset-order`` (info) check is a special case: a 2-D cell offset
written row-first (``(y*W + x)*C``, which is what the ``CM_OFF``/``RM_OFF``
macros expand to) is byte-neutral *until* the trailing add lowers to a
``lea``, at which point the row term becomes the wrong base register
(Rule 113).  Reported as ``info`` (preferred form); spelling-independent —
it sees the expanded macro the same as a hand-written row-first offset.

This is purely advisory.  The empirical basis is the normalization sweep
recorded in ``docs/observed-source-style.md``.

Implementation note: this uses the project's **pycparser AST front-end**
(``c2.commands.c_source.parse_c``), NOT regexes.  Regex-based detection was
tried first and produced false positives on pointer-to-array decls, array
initializers, ``extern`` forward-decls, and arithmetic sub-expressions
(``selected - 1 == shown`` is not a yoda).  The AST eliminates all of those.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import pycparser.c_ast as c_ast

from c2.commands.c_source import parse_c


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(REPO_ROOT, "decomp", "src")


@dataclass(frozen=True)
class StyleHint:
    """A single source-style observation."""
    severity: str   # "warn" (not-observed) | "info" (noise)
    category: str   # short label, e.g. "register", "yoda", "c99-decl"
    message: str    # one-line description + canonical form
    line: int       # 1-based line relative to the function start (0 if unknown)
    snippet: str    # short label of the offending construct


# ── Source index: function name -> (file, FuncDef, start_line) ──────────────

@lru_cache(maxsize=1)
def _source_index() -> dict[str, tuple[str, c_ast.FuncDef, int]]:
    index: dict[str, tuple[str, c_ast.FuncDef, int]] = {}
    if not os.path.isdir(SRC_DIR):
        return index
    for fn in sorted(os.listdir(SRC_DIR)):
        if not fn.endswith(".c"):
            continue
        path = os.path.join(SRC_DIR, fn)
        try:
            src = open(path, encoding="utf-8", errors="replace").read()
            ast = parse_c(src, fn)
        except Exception:
            continue
        for node in ast.ext:
            if isinstance(node, c_ast.FuncDef) and node.decl.name:
                start = node.decl.coord.line if node.decl.coord else 0
                index[node.decl.name] = (path, node, start)
    return index


def invalidate_cache() -> None:
    _source_index.cache_clear()


# ── AST visitor ──────────────────────────────────────────────────────────────

def _line_of(node, func_start: int) -> int:
    if getattr(node, "coord", None) is not None and node.coord.line:
        return max(1, node.coord.line - func_start + 1)
    return 0


def _is_const(node) -> bool:
    return isinstance(node, c_ast.Constant)


def _const_is(node, value: str) -> bool:
    return isinstance(node, c_ast.Constant) and node.value.strip() == value


def _const_int(node):
    """Return the integer value of an `int` Constant node, else None."""
    if isinstance(node, c_ast.Constant) and node.type == "int":
        try:
            return int(node.value.rstrip("uUlL"), 0)
        except ValueError:
            return None
    return None


def _strided_mult_const(node):
    """If `node` is `X * CONST` (a multiply by an int literal), return CONST."""
    if isinstance(node, c_ast.BinaryOp) and node.op == "*":
        c = _const_int(node.right)
        if c is not None:
            return c
        c = _const_int(node.left)
        if c is not None:
            return c
    return None


def _contains_ternary(node) -> bool:
    found = []

    class _V(c_ast.NodeVisitor):
        def visit_TernaryOp(self, n):
            found.append(n)
    if node is not None:
        _V().visit(node)
    return bool(found)


class _StyleVisitor(c_ast.NodeVisitor):
    def __init__(self, func_start: int):
        self.func_start = func_start
        self.hits: list[StyleHint] = []

    def _add(self, sev, cat, msg, node, snippet):
        self.hits.append(StyleHint(sev, cat, msg, _line_of(node, self.func_start), snippet))

    # — not-observed (warn) —

    def visit_Decl(self, node):
        if "register" in (node.storage or []):
            self._add("warn", "register",
                      "`register` never appears in the byte-exact corpus "
                      "(Watcom 10.0a no-op); remove it.",
                      node, f"register {node.name or ''}".strip())
        self.generic_visit(node)

    def visit_BinaryOp(self, node):
        if node.op in ("==", "!=") and _is_const(node.left) and not _is_const(node.right):
            self._add("warn", "yoda",
                      "yoda comparison; PS keeps `var == literal` operand "
                      "order (Rule 4). Flip it.",
                      node, f"{node.left.value} {node.op} …")
        # Rule 113 — 2-D cell offset operand order.  `(y*W + x)` (row term on
        # the LEFT) makes Watcom pick `y*W` as the final `lea` base; PS writes
        # the column first, `(x + y*W)`, so `x` is the base.  Spelling-
        # independent: the CM_OFF/RM_OFF macros expand to this same row-first
        # AST, so this fires on them too.  W >= 16 excludes small non-offset
        # multiplies (map widths are 52/60/80/81).
        if node.op == "+":
            lw = _strided_mult_const(node.left)
            rw = _strided_mult_const(node.right)
            if (lw is not None and lw >= 16 and rw is None
                    and not _is_const(node.right)):
                self._add("info", "offset-order",
                          "Rule 113: 2-D cell offset written row-first "
                          "`(y*W + x)`; write column-first `(x + y*W)` so the "
                          "final `lea` base register matches PS. Don't use the "
                          "CM_OFF/RM_OFF/BM_OFF macros (they are row-first) in a "
                          "TU you're matching.",
                          node, "(y*W + x)")
        if node.op == "<<" and _const_is(node.right, "1"):
            self._add("info", "noise-shl1",
                      "`x << 1` is byte-identical to `x * 2` / `2 * x` (all "
                      "`mov;add`) but NOT to `x + x` (`lea`) — Rule 62.",
                      node, "x << 1")
        self.generic_visit(node)

    def visit_TernaryOp(self, node):
        # A plain ternary is the *correct* Rule 82 idiom, so it is NOT flagged.
        # Only NESTED ternaries are un-PS-like (0 in the corpus).
        if _contains_ternary(node.iftrue) or _contains_ternary(node.iffalse) \
                or _contains_ternary(node.cond):
            self._add("warn", "nested-ternary",
                      "nested ternary `?:` never appears in the corpus; "
                      "unfold into if/else.",
                      node, "a ? b ? … : … : …")
        self.generic_visit(node)

    def visit_If(self, node):
        if isinstance(node.cond, c_ast.Assignment):
            self._add("warn", "assign-in-if",
                      "assignment inside an `if` condition is not observed in "
                      "the corpus (assign-in-`while` IS — scanner loops — but "
                      "not in `if`); split the assignment out.",
                      node, "if ((x = …))")
        elif isinstance(node.cond, c_ast.UnaryOp) and node.cond.op == "!":
            self._add("info", "noise-not",
                      "`if (!x)` is codegen-noise — identical to `if (x == 0)`.",
                      node, "if (!x)")
        self.generic_visit(node)

    def visit_While(self, node):
        if _const_is(node.cond, "1"):
            self._add("info", "noise-while1",
                      "`while (1)` is codegen-noise — identical to `for (;;)`.",
                      node, "while (1)")
        self.generic_visit(node)

    # — C99 mixed declarations + scoped blocks (Compound-level) —

    def visit_Compound(self, node):
        items = node.block_items or []
        seen_stmt = False
        # Detect multi-declarator declarations (`int a, b;`): pycparser splits
        # them into separate Decl nodes that share one coord.line.  Policy is
        # one variable per declaration line so declaration order (Rule 115) is
        # an individually-applicable regalloc lever.
        _decl_line_seen: dict[int, object] = {}
        for item in items:
            if isinstance(item, c_ast.Decl):
                ln = getattr(getattr(item, "coord", None), "line", None)
                if ln is not None:
                    if ln in _decl_line_seen:
                        self._add("warn", "multi-decl",
                                  "multiple variables on one declaration line "
                                  "(`T a, b;`); split to one `T name;` per line "
                                  "so declaration order is a per-variable "
                                  "Rule 115 lever (byte-neutral).",
                                  item, f"decl {item.name or ''}".strip())
                    else:
                        _decl_line_seen[ln] = item
        for item in items:
            if isinstance(item, c_ast.Decl):
                if seen_stmt:
                    self._add("warn", "c99-decl",
                              "declaration after a statement (C99 mixed decl); "
                              "the corpus is strict C89 — declare at the top of "
                              "the block.",
                              item, f"decl {item.name or ''}".strip())
            elif isinstance(item, c_ast.Compound):
                # a bare `{ … }` scope block holding declarations
                inner = item.block_items or []
                if any(isinstance(x, c_ast.Decl) for x in inner):
                    self._add("info", "noise-scope",
                              "inner `{ }` scope block is codegen-neutral "
                              "(≡ hoisting the decls to the block top); PS uses "
                              "these too (13 corpus functions). Free choice.",
                              item, "{ int … }")
                seen_stmt = True
            else:
                # labels, pragmas, etc. count as statements for ordering
                if not isinstance(item, c_ast.Label) or not isinstance(
                        getattr(item, "stmt", None), c_ast.Decl):
                    seen_stmt = True
        self.generic_visit(node)


# ── Public API ───────────────────────────────────────────────────────────────

def _detect_on_funcdef(func: c_ast.FuncDef) -> list[StyleHint]:
    start = func.decl.coord.line if func.decl.coord else 1
    v = _StyleVisitor(start)
    v.visit(func)
    # Keep every `warn` (each is a distinct thing to fix), but collapse `info`
    # noise hints to one-per-category so the output isn't spammy when a
    # function has several `if (!x)` / scope blocks.
    out: list[StyleHint] = []
    seen_info: set[str] = set()
    for h in v.hits:
        if h.severity == "info":
            if h.category in seen_info:
                continue
            seen_info.add(h.category)
        out.append(h)
    out.sort(key=lambda h: (h.line, 0 if h.severity == "warn" else 1))
    return out


def detect_style_hints_in_body(body: str) -> list[StyleHint]:
    """Parse a single function definition and run the style check.
    Returns [] if the snippet cannot be parsed."""
    try:
        ast = parse_c(body, "<body>")
    except Exception:
        return []
    funcs = [n for n in ast.ext if isinstance(n, c_ast.FuncDef)]
    if not funcs:
        return []
    return _detect_on_funcdef(funcs[0])


def detect_style_hints(name: str) -> list[StyleHint]:
    """Look a function up by name in decomp/src and run the style check."""
    entry = _source_index().get(name)
    if entry is None:
        return []
    _, func, _ = entry
    return _detect_on_funcdef(func)


def render_style_hints(name: str, *, include_noise: bool = True) -> list[str]:
    """Rich-markup lines for decomp-verify -v output."""
    out = []
    for h in detect_style_hints(name):
        if h.severity == "info" and not include_noise:
            continue
        tag = "[yellow]Style[/]" if h.severity == "warn" else "[dim]Style(noise)[/]"
        out.append(f"  {tag}: L{h.line} {h.message}")
    return out


def style_hints_to_json(name: str) -> list[dict]:
    return [
        {"severity": h.severity, "category": h.category,
         "message": h.message, "line": h.line, "snippet": h.snippet}
        for h in detect_style_hints(name)
    ]
