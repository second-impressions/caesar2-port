"""Evaluation-order / instruction-scheduling hint (the "eval-order hoist").

Empirical + RE basis (watcom10.0a knowledge/wcc386_regalloc.py SOURCE_LEVERS,
caesar2 copy_ferret_run_to_citizen/_army, 2026-06):

For a compound assignment ``a[idx] OP= <expr>`` where ``<expr>`` is a
non-trivial sub-expression (e.g. ``step << 4``), wcc386 picks an order for
computing the RHS value vs the LHS *address*.  PS sometimes computes the RHS
FIRST (``shl bl,4`` then ``movsx;imul`` for the address); the recompiled
``a[idx] += step<<4`` computes the address first then the shift.  That pure
scheduling divergence re-aligns the whole tail and costs bytes with NO
register/savings change (the savcode.h savings are identical either way).

The lever (proven byte-mover): hoist the RHS into a named temp so the
rhs-first schedule is forced --

    char hi = step << 4;        /* RHS computed first, like PS */
    a[idx] += hi;

copy_ferret_run_to_citizen 23->12b, copy_ferret_run_to_army 24->10b.

Detection combines two independent signals so it does NOT false-fire:
  (1) DISASM: within the diffing region PS and recomp contain the SAME
      value-ALU op (a shift/mul on a data register) but in SWAPPED order
      relative to an address-compute block (``movsx`` / ``lea`` / ``imul``)
      -- i.e. one side does VALUE before ADDR, the other ADDR before VALUE.
  (2) SOURCE (AST): the function has a compound assignment / read-modify-
      write ``a[idx] OP= <BinaryOp>`` whose RHS is a non-trivial expression
      and whose LHS index is non-trivial -- the hoistable site.

Surfaced as a ``decomp-verify -v`` header hint and in ``--json``
(``functions[].sched_hint``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pycparser import c_ast

# Value-ALU ops: a shift or 3-operand multiply on a *data* register produces a
# computed value (the RHS of a compound assign), NOT an address.  These are the
# ops that PS may schedule ahead of the address recompute.
_VALUE_OP = re.compile(r"^(shl|shr|sal|sar|imul)\b")
# Address-compute ops: sign/zero-extend a (word) index, scale it, or lea a base.
_ADDR_OP = re.compile(r"^(movsx|movzx|lea)\b")
# A 3-operand imul is address scaling ONLY when it is `imul r, r, <stride>`
# feeding a `[...]` operand; a 2-operand value `imul` (or `shl`) is the RHS.
_IMUL3 = re.compile(r"^imul\s+\w+,\s*\w+,")
# An indexed-memory read-modify-write: the actual `a[idx] OP= ...` codegen
# (`add byte ptr [reg+reg+disp], reg`).  Requiring one in the diff ties the
# scheduling signal to a real RMW, not an unrelated shift elsewhere.
_MEM_RMW = re.compile(r"^(add|sub|or|and|xor)\s+(byte|word|dword)\s+ptr\s+\[[^\]]*\+[^\]]*\]")


def _mnem(asm: str) -> str:
    return asm.split(None, 1)[0] if asm else ""


def _is_value_op(asm: str) -> bool:
    # `imul r, r, imm` is address-stride scaling, not a value op.
    if _IMUL3.match(asm):
        return False
    return bool(_VALUE_OP.match(asm))


def _is_addr_op(asm: str) -> bool:
    return bool(_ADDR_OP.match(asm)) or bool(_IMUL3.match(asm))


def _first_idx(asms: list[str], pred) -> int:
    for i, a in enumerate(asms):
        if pred(a):
            return i
    return -1


@dataclass
class SchedHint:
    """An eval-order scheduling swap between PS and recomp."""
    value_mnem: str                       # the value-ALU op that moved (e.g. "shl")
    ps_value_before_addr: bool            # PS order: value op precedes addr compute
    sites: list[tuple[int, str]] = field(default_factory=list)  # (src_line, lhs) hoist sites

    @property
    def has_site(self) -> bool:
        return bool(self.sites)


# ── source side: hoistable `a[idx] OP= <expr>` sites ───────────────────────────

_COMPOUND_OPS = {"+=", "-=", "|=", "&=", "^=", "<<=", ">>=", "*="}


# Map a disasm value-op mnemonic to the C RHS operators that produce it, so a
# detected `shl` only matches a `<<`/`*` RHS (not an unrelated cast/divide).
_OP_FOR_MNEM = {
    "shl": {"<<", "*"}, "sal": {"<<", "*"}, "imul": {"*"},
    "sar": {">>", "/"}, "shr": {">>", "/"},
}


def _rhs_operators(expr: c_ast.Node) -> set[str]:
    """All binary operators appearing in an expression."""
    ops: set[str] = set()

    class V(c_ast.NodeVisitor):
        def visit_BinaryOp(self, n):  # noqa: N802
            ops.add(n.op)
            self.generic_visit(n)

    V().visit(expr)
    return ops


class _RMWVisitor(c_ast.NodeVisitor):
    """Collect read-modify-write sites whose value side is a non-trivial expr
    and whose lvalue is a subscript/deref with a non-trivial index.

    Each site is (line, lhs_str, rhs_operators) so detect() can match the
    disasm value-op to the source RHS operator."""

    def __init__(self) -> None:
        self.sites: list[tuple[int, str, frozenset]] = []

    def _lhs_is_indexed(self, node: c_ast.Node) -> bool:
        # a[idx], p->f[idx], *(p+idx) ... we want an ArrayRef with a non-const
        # subscript (the address needs a runtime compute that can be scheduled).
        n = node
        while isinstance(n, c_ast.StructRef):
            n = n.name
        if isinstance(n, c_ast.ArrayRef):
            sub = n.subscript
            return not isinstance(sub, c_ast.Constant)
        if isinstance(n, c_ast.UnaryOp) and n.op == "*":
            return True
        return False

    @staticmethod
    def _rhs_nontrivial(expr: c_ast.Node) -> bool:
        # The RHS must carry an operator whose result is a fresh value worth
        # hoisting (shift/mul/add of something), not a bare id/constant.
        return isinstance(expr, (c_ast.BinaryOp, c_ast.UnaryOp, c_ast.Cast))

    def visit_Assignment(self, node: c_ast.Assignment) -> None:
        line = node.coord.line if node.coord else 0
        if node.op in _COMPOUND_OPS:
            if self._lhs_is_indexed(node.lvalue) and self._rhs_nontrivial(node.rvalue):
                ops = _rhs_operators(node.rvalue)
                # the compound op itself contributes the implicit '+='-style add;
                # what matters for scheduling is the RHS sub-expression operators
                self.sites.append((line, _lhs_str(node.lvalue), frozenset(ops)))
        elif node.op == "=":
            # plain `a[idx] = a[idx] OP x` (the un-fused RMW form)
            rv = node.rvalue
            if (self._lhs_is_indexed(node.lvalue)
                    and isinstance(rv, c_ast.BinaryOp)
                    and _refs_same(rv, node.lvalue)):
                self.sites.append((line, _lhs_str(node.lvalue), frozenset(_rhs_operators(rv))))
        self.generic_visit(node)


def _lhs_str(node: c_ast.Node) -> str:
    try:
        from pycparser import c_generator
        return c_generator.CGenerator().visit(node)
    except Exception:
        return "a[idx]"


def _refs_same(expr: c_ast.Node, lvalue: c_ast.Node) -> bool:
    target = _lhs_str(lvalue)
    found = [False]

    class V(c_ast.NodeVisitor):
        def visit_ArrayRef(self, n):  # noqa: N802
            if _lhs_str(n) == target:
                found[0] = True
            self.generic_visit(n)

    V().visit(expr)
    return found[0]


@lru_cache(maxsize=1)
def _rmw_index(src_dir: str = "decomp/src") -> dict[str, list[tuple[int, str, frozenset]]]:
    """{func_name: [(line, lhs, rhs_ops), ...]} for every function with a
    hoistable indexed read-modify-write whose value side is non-trivial."""
    from c2.commands.c_source import classify_source

    out: dict[str, list[tuple[int, str, frozenset]]] = {}
    for cf in sorted(Path(src_dir).glob("*.c")):
        try:
            fd = classify_source(cf.read_text(), cf.name)
        except Exception:
            continue
        for f in fd.func_defs:
            v = _RMWVisitor()
            v.visit(f)
            if v.sites:
                out[f.decl.name] = v.sites
    return out


# ── disasm side: value/addr order swap ────────────────────────────────────────

def _order_swap(pairs: list[tuple[str, str]]) -> Optional[tuple[str, bool]]:
    """Detect a LOCAL transposition: a value-ALU op that sits at one row index
    in the PS column and a DIFFERENT row index in the recomp column, with an
    address-compute op in the rows between (the op moved across the address
    recompute).  ``pairs`` is the aligned ``(ps_asm, rc_asm)`` per row, equal
    rows included (the address anchors are usually equal rows).

    Returns (value_mnem, ps_value_before_addr).
    """
    ps = [a for a, _ in pairs]
    rc = [b for _, b in pairs]
    for mnem in ("shl", "shr", "sal", "sar", "imul"):
        ps_at = [i for i, a in enumerate(ps) if _is_value_op(a) and _mnem(a) == mnem]
        rc_at = [i for i, b in enumerate(rc) if _is_value_op(b) and _mnem(b) == mnem]
        if not ps_at or not rc_at:
            continue
        pi, ri = ps_at[0], rc_at[0]
        if pi == ri:
            continue
        lo, hi = sorted((pi, ri))
        # an address-compute op must sit between the two positions on EITHER
        # column (that is the thing the value op was scheduled across)
        between = any(_is_addr_op(ps[k]) or _is_addr_op(rc[k])
                      for k in range(lo + 1, hi))
        if not between:
            continue
        return mnem, pi < ri
    return None


def detect(name: Optional[str], orig_insns: list, recomp_insns: list,
           rows: Optional[list[dict]] = None) -> Optional[SchedHint]:
    """Detect an eval-order scheduling swap.  Requires BOTH the disasm
    order-swap signature AND a hoistable source RMW site to fire."""
    if not name or rows is None:
        return None
    # Aligned (ps_asm, rc_asm) per row, equal rows included -- the address
    # anchors that the value op moves across are usually byte-equal rows.
    pairs: list[tuple[str, str]] = []
    for row in rows:
        o = row.get("o")
        r = row.get("r")
        pairs.append((o[3] if o else "", r[3] if r else ""))
    swap = _order_swap(pairs)
    if swap is None:
        return None
    # Precision gate: the diff must contain an indexed-memory RMW (the actual
    # `a[idx] OP= ...` codegen) -- otherwise the value-op swap is some other
    # shift and the source RMW site is an unrelated coincidence.
    if not any(_MEM_RMW.match(a) or _MEM_RMW.match(b) for a, b in pairs):
        return None
    value_mnem, ps_before = swap
    all_sites = _rmw_index().get(name, [])
    # Keep only RMW sites whose RHS operator can produce the detected value-op
    # (a `shl` swap must pair with a `<<`/`*` RHS, not a cast or divide).
    want = _OP_FOR_MNEM.get(value_mnem, set())
    sites = [(ln, lhs) for ln, lhs, ops in all_sites if ops & want]
    if not sites:
        return None
    return SchedHint(value_mnem=value_mnem, ps_value_before_addr=ps_before,
                     sites=sites)


def render(h: SchedHint) -> str:
    site = ""
    if h.sites:
        ln, lhs = h.sites[0]
        more = f" (+{len(h.sites)-1} more)" if len(h.sites) > 1 else ""
        site = f"  Hoist the RHS at line {ln} (`{lhs} OP= <expr>`){more}: "
    order = ("PS computes the RHS value (`%s`) BEFORE the address; recomp does the "
             "address first" % h.value_mnem) if h.ps_value_before_addr else (
             "PS computes the address before the RHS (`%s`); recomp does the RHS first"
             % h.value_mnem)
    return (
        f"eval-order scheduling swap -- {order}.{site}"
        "write `T tmp = <expr>; a[idx] OP= tmp;` so wcc386 emits the RHS first "
        "(matches PS's schedule).  Pure scheduling: no register/savings change. "
        "copy_ferret_run twins -25b.  watcom10.0a knowledge SOURCE_LEVERS "
        "(EVAL-ORDER HOIST)."
    )


def render_line(h: SchedHint) -> str:
    return f"  [yellow]Schedule[/]: {render(h)}"


def to_json(h: Optional[SchedHint]) -> Optional[dict]:
    if h is None:
        return None
    return {
        "value_mnem": h.value_mnem,
        "ps_value_before_addr": h.ps_value_before_addr,
        "sites": [{"line": ln, "lhs": lhs} for ln, lhs in h.sites],
    }
