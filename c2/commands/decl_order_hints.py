"""Rule 115 / declaration-order regalloc-lever hint detector.

When ``decomp-verify`` reports a **layer-3 register-identity swap** (caller-
saved, no prologue change -- the regalloc_explain.py classification), the
underlying mechanism is an equal-savings tie-break in the layer-3 conflict
ordering.  Two source-level levers act on it: Rule 28a (commute the deciding
use) and Rule 115 (swap the two tied locals' declaration order).  See
``watcom10.0a repo docs/wcc386-re/regalloc-model.md`` §3.

This module surfaces Rule-115 candidates: layer-3 Reg-swap functions that
declare two-or-more named ``int`` locals at top scope (so swapping decl pairs
is an applicable lever).  The trigger conditions:

  1. The function has a layer-3 register-identity swap (asm-level signature:
     PS / RC differ in one register identity per row, push set matches, no
     spill/loop divergence -- gated by ``regalloc_explain.RegallocHint``).
  2. The function declares ≥2 ``int``-class locals at top compound scope
     (the candidates to reorder; pycparser AST).
  3. (Refinement) at least one of the swap rows operates on a value that's
     NOT a known named global -- pure register-resident or stack-spilled
     locals are the Rule-115 lever's actual target.

The output names the candidate locals.  When the swap-row source lines
reference a specific subset of those locals, the hint narrows to that
subset (the "probable competing pair").

Asm-level visibility of the tie
-------------------------------

A pure register-identity swap with matching prologues IS, by construction,
an equal-savings tie: different savings would produce a different layout
(different push set / different total assignment), not a rename.  So
"this is a layer-3 equal-savings tie" is **fully detectable from the asm
diff alone**.  What asm cannot reveal without source help is whether the
competing values are named locals (Rule 115 actionable) or compiler temps
(no source handle) -- that's what this module adds via the AST.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

import pycparser.c_ast as c_ast

# Reuse the cached source index from style_check (function name -> AST node).
from c2.commands.style_check import _source_index, _line_of


# ── Int-class type detection ────────────────────────────────────────────────

# Plain-int types that route through ``DoubleRegs`` (32-bit int class).
# ``short`` and ``char`` go through WordRegs / byte-reg classes and don't
# participate in DoubleRegs ties.
_INT_NAMES = {"int", "long", "unsigned"}


def _is_int_class(decl_type: c_ast.Node) -> bool:
    """True if ``decl_type`` is a plain int/long (32-bit, DoubleRegs class).

    Covers ``int x``, ``unsigned int x``, ``long x``, ``int *p`` (pointer is
    also DoubleRegs).  Excludes ``short``, ``char``, arrays, structs, floats.
    """
    if isinstance(decl_type, c_ast.PtrDecl):
        # Pointers are DoubleRegs class regardless of pointee type.
        return True
    if isinstance(decl_type, c_ast.TypeDecl):
        inner = decl_type.type
        if isinstance(inner, c_ast.IdentifierType):
            names = set(inner.names or [])
            # Reject short / char even if combined with signed/unsigned.
            if names & {"short", "char", "float", "double"}:
                return False
            # Plain int / unsigned int / long (signed/unsigned modifiers are
            # also allowed standalone -- they default to int).
            return bool(names & _INT_NAMES) or names <= {"signed", "unsigned"}
    return False


# ── Top-scope local extraction ──────────────────────────────────────────────

@dataclass(frozen=True)
class LocalDecl:
    """A named int-class local declared at the function's top scope."""
    name: str
    line: int          # 1-based line *relative to the function start*
    abs_line: int      # absolute source line (for AST cross-reference)


def _top_scope_int_locals(func: c_ast.FuncDef, func_start: int) -> list[LocalDecl]:
    """Walk ``func.body`` (a Compound) and collect int-class locals declared
    at the top compound scope (NOT inside nested blocks)."""
    out: list[LocalDecl] = []
    body = func.body
    if not isinstance(body, c_ast.Compound) or not body.block_items:
        return out
    for item in body.block_items:
        if not isinstance(item, c_ast.Decl) or not item.name:
            continue
        # Skip storage-class statics (different IL path).
        if item.storage and "static" in item.storage:
            continue
        # Skip function-prototype Decls (those are nested FuncDecls).
        if isinstance(item.type, c_ast.FuncDecl):
            continue
        if not _is_int_class(item.type):
            continue
        line = _line_of(item, func_start) or 0
        abs_line = item.coord.line if item.coord else 0
        out.append(LocalDecl(name=item.name, line=line, abs_line=abs_line))
    return out


# ── Refinement: which locals are referenced near a diff-row source line ─────

def _locals_referenced_at_lines(func: c_ast.FuncDef, local_names: set[str],
                                 abs_lines: set[int]) -> set[str]:
    """Return the subset of ``local_names`` whose ID appears in the function
    AST on any of ``abs_lines`` (absolute source line numbers)."""
    hits: set[str] = set()

    class _RefVisitor(c_ast.NodeVisitor):
        def visit_ID(self, node: c_ast.ID):
            if (node.name in local_names
                    and node.coord
                    and node.coord.line in abs_lines):
                hits.add(node.name)
        # Also catch left-hand side of assignments (an Assignment's lvalue is
        # often a Decl reference -- pycparser models it as ID).

    _RefVisitor().visit(func)
    return hits


# ── Diff-row analysis ───────────────────────────────────────────────────────

_REG_SWAP_RULES = {"Reg swap", "Byte-reg swap", "Rule 28", "Rule 28b"}

# Match registers wrapped in backticks (the actual decomp-verify format),
# e.g. "PS uses `ch`, recomp uses `al`" or "register identity swap
# (`esi`↔`edi`)".  Falls through to bare (R1↔R2) on older outputs.
_BACKTICK_REG_RE = re.compile(r"`([a-d][lh]|[a-d]x|e?[abcd]x|e?[sb]p|e?[sd]i)`")
_BARE_PAIR_RE = re.compile(
    r"\(([a-d][lh]|[a-d]x|e?[abcd]x|e?[sb]p|e?[sd]i)"
    r"\s*[↔↕<>\-]+\s*"
    r"([a-d][lh]|[a-d]x|e?[abcd]x|e?[sb]p|e?[sd]i)\)"
)

# Sub-byte / sub-word -> canonical 32-bit name (so ch/cl/cx -> ecx).
_CANONICAL_REG = {
    "al": "eax", "ah": "eax", "ax": "eax",
    "bl": "ebx", "bh": "ebx", "bx": "ebx",
    "cl": "ecx", "ch": "ecx", "cx": "ecx",
    "dl": "edx", "dh": "edx", "dx": "edx",
    "si": "esi", "di": "edi", "bp": "ebp", "sp": "esp",
}


def _canonical(reg: str) -> str:
    return _CANONICAL_REG.get(reg.lower(), reg.lower())


def _row_hint(row: dict) -> Optional[dict]:
    """Return the row's rule-hint dict, accepting both schemas:
    ``row['hint']`` (single dict, current decomp-verify JSON) or
    ``row['rule_hints']`` (list, legacy / regtrace style)."""
    h = row.get("hint")
    if isinstance(h, dict):
        return h
    hl = row.get("rule_hints") or row.get("hints")
    if isinstance(hl, list):
        for item in hl:
            if isinstance(item, dict):
                return item
    return None


def _is_reg_swap_row(row: dict) -> bool:
    h = _row_hint(row)
    return bool(h and h.get("rule") in _REG_SWAP_RULES)


def _swap_register_pair(diff_rows: list[dict]) -> Optional[tuple[str, str]]:
    """Extract the canonical (PS_reg, RC_reg) pair from any Reg-swap row's
    hint metadata.  Returns the **canonical 32-bit names** (`eax`, `ebx`, ...)
    so byte-reg swaps (`ch`/`al`) and word-reg swaps surface uniformly.
    Returns the first pair seen (they're typically all the same swap)."""
    for row in diff_rows:
        h = _row_hint(row)
        if not h or h.get("rule") not in _REG_SWAP_RULES:
            continue
        # Structured fields first.
        pair = h.get("regs") or h.get("pair")
        if pair and len(pair) == 2:
            return (_canonical(str(pair[0])), _canonical(str(pair[1])))
        # Backtick form: "... `ch`, recomp uses `al`" or "(`esi`↔`edi`)".
        for field_ in ("summary", "message", "detail", "fix"):
            text = h.get(field_) or ""
            regs = _BACKTICK_REG_RE.findall(text)
            if len(regs) >= 2:
                return (_canonical(regs[0]), _canonical(regs[1]))
            m = _BARE_PAIR_RE.search(text.lower())
            if m:
                return (_canonical(m.group(1)), _canonical(m.group(2)))
    return None


# ── Public hint ─────────────────────────────────────────────────────────────

@dataclass
class DeclOrderHint:
    """A Rule 115 candidate hint."""
    # Detection signal.
    swap_regs: tuple[str, str]               # asm-level swap pair (lower-case)
    layer3_reg_swap: bool                    # gating regalloc_explain layer
    # Source-side handles.
    locals: list[LocalDecl]                  # all top-scope int locals
    candidate_pair: Optional[tuple[str, str]] = None  # refined competing pair (if ≥2 inferred)
    # Provenance.
    swap_row_count: int = 0
    # Severity / status.
    actionable: bool = True

    @property
    def local_names(self) -> list[str]:
        return [l.name for l in self.locals]


def detect(name: str, regalloc_layer: Optional[int],
           diff_rows: list[dict]) -> Optional[DeclOrderHint]:
    """Detect a Rule 115 candidate for function ``name``.

    Returns None when any precondition fails:
      * regalloc layer is not 3,
      * no Reg-swap diff rows,
      * source for the function isn't indexed,
      * fewer than 2 int-class top-scope locals.

    Otherwise returns a hint naming the candidate locals (and, if possible,
    a refined "probable competing pair" inferred from which locals are
    referenced on the swap rows' source lines).
    """
    if regalloc_layer != 3:
        return None
    swap_rows = [r for r in diff_rows if _is_reg_swap_row(r)]
    if not swap_rows:
        return None
    swap_regs = _swap_register_pair(swap_rows)
    if swap_regs is None:
        return None

    idx = _source_index()
    if name not in idx:
        return None
    _, func, func_start = idx[name]

    locals_ = _top_scope_int_locals(func, func_start)
    if len(locals_) < 2:
        return None

    # Refine: which locals are referenced near the swap-row source lines?
    # ``replace`` rows often have ``ln=None`` (only ``equal`` rows carry the
    # original source line), so we widen each swap row to a small window
    # bounded by the nearest preceding and following ``equal`` rows that DO
    # have line numbers.  The local-name AST scan then sees any local
    # mentioned inside that window, which is enough to identify the
    # competing pair without needing per-row line attribution.
    local_names = {l.name for l in locals_}
    swap_windows: set[int] = set()
    for i, r in enumerate(diff_rows):
        if r is not swap_rows[0] and r not in swap_rows:
            continue
        # Each swap row's own ln if present.
        rel = r.get("ln") or r.get("line")
        if isinstance(rel, int) and rel > 0:
            swap_windows.add(func_start + rel - 1)
            continue
        # Walk outwards to the nearest equal rows with ln set.
        for j in range(i - 1, max(-1, i - 6), -1):
            ln = diff_rows[j].get("ln") if 0 <= j < len(diff_rows) else None
            if isinstance(ln, int) and ln > 0:
                swap_windows.add(func_start + ln - 1)
                break
        for j in range(i + 1, min(len(diff_rows), i + 6)):
            ln = diff_rows[j].get("ln")
            if isinstance(ln, int) and ln > 0:
                swap_windows.add(func_start + ln - 1)
                break
    # Widen each anchor by +/- 1 line (typical diff-hunk span around a row).
    widened = {ln + d for ln in swap_windows for d in (-1, 0, 1)}
    refined = (_locals_referenced_at_lines(func, local_names, widened)
               if widened else set())
    pair: Optional[tuple[str, str]] = None
    if len(locals_) == 2:
        # Unambiguous: only one pair possible.
        pair = (locals_[0].name, locals_[1].name)
    elif len(refined) == 2:
        # AST refinement isolated exactly two competing locals.
        ref_locals = sorted(
            (l for l in locals_ if l.name in refined),
            key=lambda l: l.line,
        )
        pair = (ref_locals[0].name, ref_locals[1].name)
    elif len(refined) > 2:
        # Multiple AST-referenced candidates -- present the two whose decl
        # lines are closest together (tied locals tend to be declared near
        # each other since they correlate with use position).
        ref_locals = sorted(
            (l for l in locals_ if l.name in refined),
            key=lambda l: l.line,
        )
        best = min(
            zip(ref_locals[:-1], ref_locals[1:]),
            key=lambda ab: ab[1].line - ab[0].line,
        )
        pair = (best[0].name, best[1].name)

    return DeclOrderHint(
        swap_regs=swap_regs,
        layer3_reg_swap=True,
        locals=locals_,
        candidate_pair=pair,
        swap_row_count=len(swap_rows),
        actionable=True,
    )


# ── Rendering ────────────────────────────────────────────────────────────────

def render(hint: DeclOrderHint) -> str:
    """One-line ``Rule 115:`` summary suitable for decomp-verify -v."""
    a, b = hint.swap_regs
    n = len(hint.locals)
    # SHAPE-CONSTRAINT caveat: Rule 115 (decl-swap) is IR-neutral ONLY for
    # named NON-PARAM locals.  A __watcall PARAMETER's register is ABI-fixed
    # (first 4 int args in eax/edx/ebx/ecx), so its decl order can't move --
    # only use-order (Rule 28a), which reorders statements and often breaks
    # the IR -> sub-source (proven: city_test_for_road's x/y tie).  This hint
    # lists BODY locals; if the actual tied value is a param it is NOT here.
    _param_caveat = (" CAVEAT: if the tied value is a __watcall PARAMETER "
                     "(not in this local list), decl-order is ABI-FIXED -- "
                     "Rule 115 does NOT apply; use-order only, often "
                     "sub-source (verify with decomp-verify).")
    if hint.candidate_pair:
        pa, pb = hint.candidate_pair
        return (
            f"layer-3 {a.upper()}↔{b.upper()} tie ({hint.swap_row_count} row(s)); "
            f"probable competing pair `{pa}`/`{pb}` "
            f"(of {n} top-scope int local{'' if n == 1 else 's'}). "
            f"Rule 115 lever: swap their declaration order and verify. "
            f"Rule 28a lever first if you can commute / reorder a use."
            + _param_caveat
        )
    names = ", ".join(f"`{l.name}`" for l in hint.locals[:6])
    if n > 6:
        names += f", … (+{n - 6})"
    return (
        f"layer-3 {a.upper()}↔{b.upper()} tie ({hint.swap_row_count} row(s)); "
        f"{n} top-scope int locals: {names}. "
        f"Rule 115 lever: try swapping pairs of decl order (direction non-monotonic). "
        f"Rule 28a lever first if a use is reorderable."
        + _param_caveat
    )


def to_json(hint: DeclOrderHint) -> dict:
    """Serialise for ``--json`` output (``functions[].decl_order_hint``)."""
    return {
        "swap_regs": list(hint.swap_regs),
        "layer3_reg_swap": hint.layer3_reg_swap,
        "swap_row_count": hint.swap_row_count,
        "candidate_pair": list(hint.candidate_pair) if hint.candidate_pair else None,
        "locals": [
            {"name": l.name, "line": l.line, "abs_line": l.abs_line}
            for l in hint.locals
        ],
        "actionable": hint.actionable,
    }
