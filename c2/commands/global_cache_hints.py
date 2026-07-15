"""Precise "global cached in a local pointer" detector (AST-based).

The single strongest source-shape predictor of a byte diff in this project is
caching the **address of an element of a global array** in a local pointer and
then accessing it as a fixed row alias::

    struct svga_cell *cell = &svga_refresh_data[idx];   /* anti-pattern  */
    ... cell->screen_off ... cell->bank_off ...

PS source instead re-indexes the global at every field touch and lets Watcom
fold ``global + idx*stride + field`` into a disp32 indexed operand::

    ... svga_refresh_data[idx].screen_off ... svga_refresh_data[idx].bank_off ...

This module fires **only** on that exact anti-pattern and is empirically
clean: across the 1180-function byte-exact corpus it has **0 false
positives**, while flagging **49 / 341** diffing functions (raw enrichment
≈ 85×; size-controlled lift ≈ 1.6×).  The full survey is recorded in
``docs/observed-source-style.md`` § 1.

Two mechanical conditions must both hold for the hint to fire:

  1. A local **pointer** is assigned the address of an *indexed* element of a
     global *array* — ``p = &G[i]`` / ``p = &G[i].field`` / ``p = G + i`` —
     where ``G`` is declared as an array in the project headers (resolved from
     ``decomp/include/*.h``; type, not name heuristics).

  2. That pointer is **never advanced** in the function (no ``p++`` / ``++p`` /
     ``p += k`` / ``p = p ± k``).  A pointer that *is* advanced is a genuine
     moving cursor (``*p++`` walk), which the byte-exact corpus DOES use
     (e.g. ``load_to_text_buffer``'s ``dst = &text_buffer[off]`` then ``dst++``)
     and is therefore NOT the anti-pattern.

Copying the *value* of a global that is itself a pointer (``p = text_pointer``)
is also never flagged — that is a base-cursor copy, not an array-element
address.

Purely advisory.  Built on the project's pycparser AST front-end
(``c2.commands.c_source.parse_c``), NOT regexes.
"""

from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import pycparser.c_ast as c_ast

from c2.commands.c_source import parse_c

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DIR = os.path.join(REPO_ROOT, "decomp", "src")
INCLUDE_DIR = os.path.join(REPO_ROOT, "decomp", "include")


# ── Global type classification (array / pointer / scalar) ────────────────────

@lru_cache(maxsize=1)
def _global_types() -> dict[str, str]:
    """Map global symbol name -> 'array' | 'pointer' | 'scalar', parsed from
    the project headers.  Array-ness is what gates the anti-pattern: only the
    address of an element of an *array* global folds to a disp32 indexed
    operand in PS codegen."""
    types: dict[str, str] = {}
    for hf in sorted(glob.glob(os.path.join(INCLUDE_DIR, "*.h"))):
        try:
            txt = open(hf, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        # strip comments so they don't pollute the decl scan
        txt = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
        txt = re.sub(r"//[^\n]*", "", txt)
        for m in re.finditer(r"extern\s+([^;{}]+?)\s*;", txt):
            decl = m.group(1).strip()
            if "(" in decl:  # function declaration
                continue
            nm = re.search(r"([A-Za-z_]\w*)\s*(\[[^\]]*\])*\s*$", decl)
            if not nm:
                continue
            name = nm.group(1)
            if name in ("void", "int", "char", "short", "long",
                        "unsigned", "signed", "struct", "union", "enum"):
                continue
            tail = decl.split(name, 1)[-1]
            if re.search(re.escape(name) + r"\s*\[", decl) or "[" in tail:
                t = "array"
            elif "*" in decl:
                t = "pointer"
            else:
                t = "scalar"
            # first declaration wins, but prefer a definite array classification
            if name not in types or t == "array":
                types[name] = t
    return types


def invalidate_cache() -> None:
    _global_types.cache_clear()
    _source_index.cache_clear()


# ── Hit dataclass ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GlobalCacheHint:
    var: str        # the local pointer name
    global_: str    # the global array it caches an element address of
    line: int       # 1-based line relative to the function start (0 if unknown)
    snippet: str    # e.g. "cell = &svga_refresh_data[idx]"


# ── Init/assignment classifier ───────────────────────────────────────────────

def _array_id_root(node) -> Optional[str]:
    """If node (after unwrapping casts) is a bare global identifier that is an
    array, return its name."""
    while isinstance(node, c_ast.Cast):
        node = node.expr
    if isinstance(node, c_ast.ID) and _global_types().get(node.name) == "array":
        return node.name
    return None


def _anti_global(node) -> Optional[str]:
    """Return the global array name iff ``node`` is the address of an *indexed*
    element of a global array (the anti-pattern shape).  Returns None for bare
    ``p = global_array`` / ``p = global_pointer`` cursor copies."""
    while isinstance(node, c_ast.Cast):
        node = node.expr

    # &G[i] / &G[i].field  — must contain at least one ArrayRef
    if isinstance(node, c_ast.UnaryOp) and node.op == "&":
        inner = node.expr
        has_index = False
        root = inner
        while isinstance(root, (c_ast.ArrayRef, c_ast.StructRef)):
            if isinstance(root, c_ast.ArrayRef):
                has_index = True
            root = root.name
        if has_index and isinstance(root, c_ast.ID) \
                and _global_types().get(root.name) == "array":
            return root.name
        return None

    # G + i  /  G - i  (pointer arithmetic on the array base -> indexed address)
    if isinstance(node, c_ast.BinaryOp) and node.op in ("+", "-"):
        for side in (node.left, node.right):
            g = _array_id_root(side)
            if g:
                return g
    return None


# ── Visitor ──────────────────────────────────────────────────────────────────

def _line_of(node, func_start: int) -> int:
    if getattr(node, "coord", None) is not None and node.coord.line:
        return max(1, node.coord.line - func_start + 1)
    return 0


class _AdvancedPtrCollector(c_ast.NodeVisitor):
    """Collect the names of pointer locals that are ever advanced
    (p++/++p/p+=k/p=p±k) — i.e. genuine moving cursors, not row aliases."""

    def __init__(self):
        self.advanced: set[str] = set()

    def visit_UnaryOp(self, n):
        if n.op in ("p++", "p--", "++", "--") and isinstance(n.expr, c_ast.ID):
            self.advanced.add(n.expr.name)
        self.generic_visit(n)

    def visit_Assignment(self, a):
        if isinstance(a.lvalue, c_ast.ID):
            nm = a.lvalue.name
            if a.op in ("+=", "-="):
                self.advanced.add(nm)
            elif a.op == "=" and isinstance(a.rvalue, c_ast.BinaryOp) \
                    and a.rvalue.op in ("+", "-"):
                for s in (a.rvalue.left, a.rvalue.right):
                    if isinstance(s, c_ast.ID) and s.name == nm:
                        self.advanced.add(nm)
        self.generic_visit(a)


def _detect_on_funcdef(func: c_ast.FuncDef) -> list[GlobalCacheHint]:
    start = func.decl.coord.line if func.decl.coord else 1

    # pass 1: which local pointers exist, and which are advanced
    ptr_locals: set[str] = set()

    class _Decls(c_ast.NodeVisitor):
        def visit_Decl(self, d):
            if isinstance(d.type, c_ast.PtrDecl) and d.name:
                ptr_locals.add(d.name)
            self.generic_visit(d)

    _Decls().visit(func)
    adv = _AdvancedPtrCollector()
    adv.visit(func)
    advanced = adv.advanced

    hits: list[GlobalCacheHint] = []

    class _Scan(c_ast.NodeVisitor):
        def visit_Decl(self, d):
            if isinstance(d.type, c_ast.PtrDecl) and d.init is not None \
                    and d.name in ptr_locals and d.name not in advanced:
                g = _anti_global(d.init)
                if g:
                    hits.append(GlobalCacheHint(
                        d.name, g, _line_of(d, start), f"{d.name} = &{g}[…]"))
            self.generic_visit(d)

        def visit_Assignment(self, a):
            if a.op == "=" and isinstance(a.lvalue, c_ast.ID) \
                    and a.lvalue.name in ptr_locals \
                    and a.lvalue.name not in advanced:
                g = _anti_global(a.rvalue)
                if g:
                    hits.append(GlobalCacheHint(
                        a.lvalue.name, g, _line_of(a, start),
                        f"{a.lvalue.name} = &{g}[…]"))
            self.generic_visit(a)

    _Scan().visit(func)

    # de-duplicate (var, global) pairs, keep earliest line
    best: dict[tuple[str, str], GlobalCacheHint] = {}
    for h in hits:
        key = (h.var, h.global_)
        if key not in best or h.line < best[key].line:
            best[key] = h
    return sorted(best.values(), key=lambda h: (h.line, h.var))


# ── Source index ─────────────────────────────────────────────────────────────

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


# ── Public API ───────────────────────────────────────────────────────────────

def detect_global_cache_hints(name: str) -> list[GlobalCacheHint]:
    """Look a function up by name in decomp/src and run the detector."""
    entry = _source_index().get(name)
    if entry is None:
        return []
    _, func, _ = entry
    return _detect_on_funcdef(func)


def detect_in_body(body: str) -> list[GlobalCacheHint]:
    """Run the detector on a single function-definition snippet."""
    try:
        ast = parse_c(body, "<body>")
    except Exception:
        return []
    funcs = [n for n in ast.ext if isinstance(n, c_ast.FuncDef)]
    if not funcs:
        return []
    return _detect_on_funcdef(funcs[0])


def render_global_cache_hints(name: str) -> list[str]:
    """Rich-markup lines for decomp-verify -v output (one per cached global)."""
    out = []
    for h in detect_global_cache_hints(name):
        out.append(
            f"  [yellow]Global-cache[/]: L{h.line} `{h.var}` caches "
            f"`&{h.global_}[…]` — index `{h.global_}[…]` inline at every "
            f"field touch instead (don't alias a global array element; "
            f"Rules 63/73, observed-source-style §1)."
        )
    return out


def global_cache_hints_to_json(name: str) -> list[dict]:
    return [
        {"var": h.var, "global": h.global_, "line": h.line, "snippet": h.snippet}
        for h in detect_global_cache_hints(name)
    ]


def scan_all() -> dict[str, list[GlobalCacheHint]]:
    """Project-wide scan: every function that caches a global array element."""
    out: dict[str, list[GlobalCacheHint]] = {}
    for fname, (_, func, _) in _source_index().items():
        hits = _detect_on_funcdef(func)
        if hits:
            out[fname] = hits
    return out


# ── CLI ──────────────────────────────────────────────────────────────────────

import typer


def global_cache_hints(
    name: Optional[str] = typer.Argument(
        None, help="Function to inspect (omit with --all for a project scan)."),
    all_: bool = typer.Option(
        False, "--all", help="Project-wide list of every carrier function."),
    json_out: bool = typer.Option(False, "--json", help="JSON output."),
):
    """Flag locals that cache the address of a global array element.

    With NAME: show hits for one function.  With --all: project-wide list of
    every function that uses the anti-pattern (the strongest byte-diff
    predictor in the corpus; see ``docs/observed-source-style.md`` § 1).
    """
    import json as _json

    from rich.console import Console
    from rich.table import Table

    console = Console(color_system=None)

    if name and not all_:
        hits = detect_global_cache_hints(name)
        if json_out:
            typer.echo(_json.dumps(global_cache_hints_to_json(name), indent=2))
            return
        if not hits:
            console.print(f"[green]{name}[/]: no global-array-element cache "
                          f"(this anti-pattern not present).")
            return
        console.print(f"[yellow]{name}[/] caches {len(hits)} global array "
                      f"element(s) in local pointer(s):")
        for h in hits:
            console.print(f"  L{h.line}  `{h.var} = &{h.global_}[…]`  "
                          f"→ inline `{h.global_}[idx].field` at each touch.")
        return

    # project-wide
    found = scan_all()
    if json_out:
        typer.echo(_json.dumps(
            {fn: [h.__dict__ for h in hs] for fn, hs in found.items()},
            indent=2, default=lambda o: o.__dict__))
        return

    tbl = Table(title="Locals caching a global array element (anti-pattern)")
    tbl.add_column("function", style="cyan")
    tbl.add_column("globals")
    tbl.add_column("n", justify="right")
    for fn in sorted(found):
        hs = found[fn]
        globs = sorted({h.global_ for h in hs})
        tbl.add_row(fn, ", ".join(globs[:4]), str(len(hs)))
    console.print(tbl)
    console.print(f"\n[dim]{len(found)} function(s).  Each is a candidate to "
                  f"inline its global array indexing (Rules 63/73, "
                  f"observed-source-style §1).[/]")
