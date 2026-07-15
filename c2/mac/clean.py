"""AST-based postprocessor for Ghidra Mac PPC decompile output.

Ghidra decompiles PEF binaries faithfully, which means every TOC-indirected
global is rendered as a pointer dereference through an alias::

    int *piVar1;          // pointer-alias declaration
    int *piVar2;
    piVar2 = _water_trouble_rate;   // load TOC slot
    piVar1 = _water_cover;
    get_water_cover();
    if (*piVar1 < 0xb) {            // dereference alias to read global
      *piVar2 = 0;                  // dereference alias to write global
    }

That extra indirection is a PEF-loader artifact, NOT in the original C source.
We collapse it::

    if (water_cover < 0xb) {
      water_trouble_rate = 0;
    }

This module uses pycparser to parse Ghidra's output, walks the AST, and rewrites:
  * `*alias` -> ID(global)
  * bare `alias` -> &global
  * `*_GLOBAL` -> ID(global)
  * `_GLOBAL` -> &global
  * drops the alias declarations and alias-init assignments

Then emits clean C using pycparser's CGenerator.
"""
from __future__ import annotations

import re
import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pycparser.c_ast as ca
from pycparser import c_generator, c_parser


REPO = Path(__file__).resolve().parents[2]
TOC_NAMES_JSON = REPO / ".c2-cache" / "mac" / "toc_names.fr.json"


@lru_cache(maxsize=1)
def known_globals(build: str = "fr") -> frozenset[str]:
    """Return the set of PC global names recovered from PS/Mac correlation."""
    p = REPO / ".c2-cache" / "mac" / f"toc_names.{build}.json"
    if not p.exists():
        return frozenset()
    return frozenset(json.loads(p.read_text()).values())


# Prolog Ghidra always uses + the typedef shims to make its output parseable.
_GHIDRA_PROLOG = """\
typedef int undefined;
typedef int undefined4;
typedef unsigned char byte;
typedef unsigned char undefined1;
typedef unsigned short undefined2;
typedef unsigned int uint;
typedef unsigned int undefined3;
typedef unsigned char uchar;
typedef unsigned short ushort;
typedef unsigned long ulong;
typedef int bool;
typedef int code;
"""

_C_KEYWORDS_NOT_CALLS = frozenset({
    "if", "while", "for", "switch", "return", "sizeof", "do",
    "typedef", "struct", "union", "enum", "case", "default",
    "break", "continue", "goto",
})

_IDENT_CHARS = re.compile(r'\b([A-Za-z_]\w*)\b')


class _PefIndirectionCleaner:
    """Walk a FuncDef AST and collapse PEF TOC pointer aliases.

    Steps per function:
      1. Collect `alias = _GLOBAL;` assignments at the start of the body.
      2. Drop those assignments AND the alias decls (`T *alias;`).
      3. Rewrite all expressions: `*alias` -> ID(global), `alias` -> &global,
         `*_GLOBAL` -> ID(global), `_GLOBAL` -> &global.
    """

    def __init__(self, globals_set: frozenset[str]):
        self.globals = globals_set

    def transform_funcdef(self, fdef: ca.FuncDef) -> None:
        body = fdef.body
        if not isinstance(body, ca.Compound) or body.block_items is None:
            return

        aliases: dict[str, str] = {}
        for item in body.block_items:
            if (isinstance(item, ca.Assignment) and item.op == "="
                    and isinstance(item.lvalue, ca.ID)
                    and isinstance(item.rvalue, ca.ID)
                    and item.rvalue.name.startswith("_")
                    and item.rvalue.name[1:] in self.globals):
                aliases[item.lvalue.name] = item.rvalue.name[1:]

        # 1. drop alias decls + alias-init assignments
        new_items = []
        for item in body.block_items:
            if isinstance(item, ca.Decl) and item.name in aliases:
                continue
            if (isinstance(item, ca.Assignment) and item.op == "="
                    and isinstance(item.lvalue, ca.ID)
                    and item.lvalue.name in aliases):
                continue
            new_items.append(item)
        body.block_items = new_items

        # 2. recurse and rewrite
        body.block_items = [self._rewrite(item, aliases) for item in body.block_items]

    def _rewrite(self, node, aliases):
        if node is None:
            return None
        if isinstance(node, ca.UnaryOp) and node.op == "*" and isinstance(node.expr, ca.ID):
            name = node.expr.name
            if name in aliases:
                return ca.ID(aliases[name], coord=node.coord)
            if name.startswith("_") and name[1:] in self.globals:
                return ca.ID(name[1:], coord=node.coord)
        if isinstance(node, ca.ID):
            if node.name in aliases:
                return ca.UnaryOp(
                    "&", ca.ID(aliases[node.name], coord=node.coord), coord=node.coord
                )
            if node.name.startswith("_") and node.name[1:] in self.globals:
                return ca.UnaryOp(
                    "&", ca.ID(node.name[1:], coord=node.coord), coord=node.coord
                )

        # NOTE: ``node.children()`` yields ONE entry per list element
        # (``block_items[0]``, ``block_items[1]``, ...), all sharing the same
        # ``base`` attribute.  Processing each entry would re-walk the whole
        # list once per element -> O(N^2) per list, compounding across nesting
        # depth into a multi-minute blow-up on deeply-nested functions
        # (cap_land_value: 488s -> <0.1s).  Dedupe ``base`` so each child
        # attribute is rewritten exactly once.
        seen_bases: set[str] = set()
        for attr_name, _child in node.children():
            base = attr_name.split("[", 1)[0]
            if base in seen_bases:
                continue
            seen_bases.add(base)
            current = getattr(node, base, None)
            if current is None:
                continue
            if isinstance(current, list):
                new_list = [self._rewrite(c, aliases) for c in current]
                setattr(node, base, [c for c in new_list if c is not None])
            else:
                new_child = self._rewrite(current, aliases)
                if new_child is not current:
                    setattr(node, base, new_child)
        return node


def _build_prolog_for(text: str, globals_set: frozenset[str]) -> str:
    """Build minimal forward decls needed for pycparser to accept the body.

    For every `_GLOBAL` and bare global reference, declare an int variable
    and an `int *_GLOBAL`.  For every function-call identifier seen, declare a
    permissive prototype (`int F();`) so call expressions parse.
    """
    referenced_globals = {
        m for m in _IDENT_CHARS.findall(text) if m in globals_set
    }
    referenced_aliases = {
        m[1:] for m in _IDENT_CHARS.findall(text)
        if m.startswith("_") and m[1:] in globals_set
    }
    referenced = referenced_globals | referenced_aliases

    # Find call identifiers `NAME(`
    called = set(re.findall(r"\b([A-Za-z_]\w*)\s*\(", text))
    called -= _C_KEYWORDS_NOT_CALLS

    lines = [_GHIDRA_PROLOG.rstrip()]
    for g in sorted(referenced):
        lines.append(f"int {g};")
        lines.append(f"int *_{g};")
    for c in sorted(called):
        if c in referenced:
            continue
        # Skip if it's defined in this same text (Ghidra outputs one func at a time
        # so this only catches recursion -- still benign)
        lines.append(f"int {c}();")
    return "\n".join(lines) + "\n"


def clean_decompile(raw_text: str, globals_set: Optional[frozenset[str]] = None
                    ) -> tuple[Optional[str], Optional[str]]:
    """Parse Ghidra decompile output, collapse PEF indirection, regenerate C.

    Returns ``(cleaned_text, None)`` on success or ``(None, error_message)`` on
    parse failure.  Falls back to the raw text if AST manipulation fails.
    """
    if globals_set is None:
        globals_set = known_globals()

    # 1. Strip Ghidra warnings and the `.debug::` namespace prefix
    text = re.sub(r"/\*.*?\*/", "", raw_text, flags=re.DOTALL)
    text = re.sub(r"\.debug::", "", text)

    prolog = _build_prolog_for(text, globals_set)
    try:
        ast = c_parser.CParser().parse(prolog + text, filename="ghidra.c")
    except Exception as e:
        return None, f"parse error: {e}"

    cleaner = _PefIndirectionCleaner(globals_set)
    for ext in ast.ext:
        if isinstance(ext, ca.FuncDef):
            cleaner.transform_funcdef(ext)

    gen = c_generator.CGenerator()
    parts = [gen.visit(ext) for ext in ast.ext if isinstance(ext, ca.FuncDef)]
    return "\n\n".join(parts), None


def clean_decompile_ast(raw_text: str,
                        globals_set: Optional[frozenset[str]] = None):
    """Like :func:`clean_decompile`, but return the cleaned pycparser
    ``FuncDef`` AST node instead of regenerated text.

    Returns ``(funcdef, None)`` on success or ``(None, error_message)`` on
    parse failure.  Used by ``c2 shape-recon`` (witness B) to read the
    Mac control-flow nesting / types / per-statement anchors structurally
    rather than from text.
    """
    if globals_set is None:
        globals_set = known_globals()

    text = re.sub(r"/\*.*?\*/", "", raw_text, flags=re.DOTALL)
    text = re.sub(r"\.debug::", "", text)

    prolog = _build_prolog_for(text, globals_set)
    try:
        ast = c_parser.CParser().parse(prolog + text, filename="ghidra.c")
    except Exception as e:
        return None, f"parse error: {e}"

    cleaner = _PefIndirectionCleaner(globals_set)
    fdef = None
    for ext in ast.ext:
        if isinstance(ext, ca.FuncDef):
            cleaner.transform_funcdef(ext)
            if fdef is None:
                fdef = ext
    if fdef is None:
        return None, "no FuncDef in decompile output"
    return fdef, None
