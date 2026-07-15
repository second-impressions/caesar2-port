"""Rule 119 / byte-pump workhorse rotation regalloc-lever hint.

When a function builds a multi-byte composite (24-bit / 16-bit / packed)
into a NAMED accumulator via compound assignments on byte-zext loads,
two semantically-identical source forms produce DIFFERENT regalloc
allocations.  This module surfaces the source-level lever.

The mechanism
-------------

OW v1 ``regalloc.c::CountRegMoves`` (see also watcom10.0a repo docs/wcc386-re/regalloc-model.md
§4) scores each (conflict, candidate register) pair by walking the IR and
counting:

  * **MOV bonus** (``count += tree->size``, typically +4 for 32-bit): a
    MOV between the conflict's value and the candidate register
    eliminates an instruction if the value lives in that register.
  * **Commutative-RMW bonus** (``count += half``, typically +2): for
    ``OP_ADD``, ``OP_EXT_ADD``, ``OP_MUL``, ``OP_AND``, ``OP_OR``,
    ``OP_XOR`` only (NOT LSHIFT, NOT SUB), a single-instruction RMW
    is possible if the value is in the candidate reg.

``CalcSavings`` picks each conflict's max-CRM register; ``SortConflicts``
orders by descending savings; ``GiveBestReg`` assigns each conflict in
order, with the first to ask claiming its preferred reg.

So the value with the MOST CRM-eligible ops wins its preferred register
(often EAX -- the return register, AND the natural byte-load destination
since AL is the cheapest byte target).

The lever
---------

If a function has:

    r = (uchar)mem[i + N0];        // r gets byte load (MOV +4 to r)
    r <<= 16;                       // LSHIFT -- no bonus
    r += (uchar)mem[i + N1] << 8;   // byte load goes to anon temp,
                                    //   r gets ADD commutative bonus
    r += (uchar)mem[i + N2];        // ditto
    return r;                       // r → EAX (final MOV +4)

then **r** accrues all the bonuses (~9 savings, CRM(EAX)=+2 from return
MOV) and claims EAX.  Byte loads scatter to scratch temps (BL/DL/etc).
This produces register-letter divergences from PS, which routes byte
loads through a single scratch register.

Rewriting to route byte loads through a SCRATCH named local ``t``:

    int r, t;
    t  = (uchar)mem[i + N0];       // MOV +4 to t in EAX
    t <<= 16;                       // LSHIFT -- still no bonus
    r  = t;                          // MOV between r and t
    t  = (uchar)mem[i + N1];       // MOV +4 to t in EAX (2nd byte load)
    t <<= 8;
    r += t;
    t  = (uchar)mem[i + N2];       // MOV +4 to t in EAX (3rd byte load)
    r += t;
    return r;                       // MOV +4 to r in EAX

Now **t** has 3 byte-load MOV bonuses (+12 CRM(EAX) before scaling),
becoming the highest-savings conflict, claiming EAX.  r drops to lower
savings (only the return-MOV +4) and claims the next callee-save EBX.
This matches PS's allocation bit-for-bit on the canonical case
(``get_buffer_ofset`` -- the discovery case, 28→0 byte diff).

Detector signature
------------------

The hint fires when ALL of:

  1. The function has ≥2 compound assignments (``<<=``, ``+=``, ``|=``)
     to the same named local ``r``.
  2. ``r`` is also assigned a byte-zext value at least once (cast to
     ``char``/``unsigned char``, or ``& 0xff`` form).
  3. The function ends with ``return r`` (r IS the returned value).
  4. NO dedicated named byte-scratch local ``t`` exists -- i.e., no
     local that is assigned a byte-zext value MORE THAN ONCE.

When fired, the hint names ``r`` (the workhorse accumulator) and
suggests adding a scratch ``t``.

Asm-level visibility
---------------------

This is a Reg-swap / shape-mixed diff (layer-3 or layer-4 in
``regalloc_explain``'s classification).  ``regalloc-explain`` will
typically say "no register-class divergence" -- the divergence is
**within** the DoubleRegs class, an op-count tie-break that asm alone
can't surface.  The byte-pump pattern is the SOURCE-side signature
that makes this specific tie-break actionable.

Cross-reference
---------------

* Worked example: ``docs/codegen-experiments/get_buffer_ofset.py``.
* Doc: ``docs/watcom-codegen-patterns.md`` Rule 119.
* OW v1 source: ``bld/cg/c/regalloc.c::CountRegMoves`` lines 457+.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pycparser.c_ast as c_ast

from c2.commands.style_check import _source_index


# ── AST walkers ─────────────────────────────────────────────────────────


class _ReturnScanner(c_ast.NodeVisitor):
    """Collect the names returned by ``return <ID>;`` statements."""

    def __init__(self) -> None:
        self.returned_names: set[str] = set()

    def visit_Return(self, node: c_ast.Return) -> None:
        expr = node.expr
        if isinstance(expr, c_ast.ID):
            self.returned_names.add(expr.name)
        self.generic_visit(node)


def _is_byte_zext_rvalue(rv: c_ast.Node) -> bool:
    """True if ``rv`` is a byte-zext expression: ``(unsigned char)X`` cast,
    or ``X & 0xff`` form, or a direct ``unsigned char``-typed indexed load."""
    if isinstance(rv, c_ast.Cast):
        t = rv.to_type.type
        if isinstance(t, c_ast.TypeDecl) and isinstance(t.type, c_ast.IdentifierType):
            names = t.type.names or []
            if "char" in names:
                return True
    if isinstance(rv, c_ast.BinaryOp) and rv.op == "&":
        for side in (rv.left, rv.right):
            if isinstance(side, c_ast.Constant) and side.value in ("0xff", "255", "0xFF"):
                return True
    return False


class _BytePumpScanner(c_ast.NodeVisitor):
    """Collect per-local compound-op counts and byte-zext-assign counts."""

    def __init__(self) -> None:
        self.compound_count: dict[str, int] = {}
        self.byte_zext_assign_count: dict[str, int] = {}

    def visit_Assignment(self, node: c_ast.Assignment) -> None:
        if isinstance(node.lvalue, c_ast.ID):
            name = node.lvalue.name
            if node.op in ("<<=", "+=", "|=", "&=", "^="):
                self.compound_count[name] = self.compound_count.get(name, 0) + 1
            elif node.op == "=" and _is_byte_zext_rvalue(node.rvalue):
                self.byte_zext_assign_count[name] = self.byte_zext_assign_count.get(name, 0) + 1
        self.generic_visit(node)


# ── Public hint result ─────────────────────────────────────────────────


@dataclass
class BytePumpHint:
    """Rule 116 fire result.

    Attributes
    ----------
    accumulator:
        The named local that's the workhorse -- the candidate to
        DEMOTE from the EAX claim.
    compound_op_count:
        Number of ``<<= / += / |=`` operations on ``accumulator``.
    byte_zext_assign_count:
        Number of times ``accumulator`` is assigned a byte-zext value
        (the "byte-pump" loads).
    returned:
        Whether ``accumulator`` is the value returned (``return r;``).
    existing_byte_scratch:
        Name of an existing byte-scratch local (if any -- a local that
        receives 2+ byte-zext assigns).  Empty if the lever is fully
        unapplied.
    """

    function: str
    accumulator: str
    compound_op_count: int
    byte_zext_assign_count: int
    returned: bool
    existing_byte_scratch: Optional[str] = None


# ── Detector ────────────────────────────────────────────────────────────


def detect(name: str) -> Optional[BytePumpHint]:
    """Return a ``BytePumpHint`` if ``name`` matches the byte-pump pattern.

    Conditions: see module docstring.
    """
    idx = _source_index()
    if name not in idx:
        return None
    _fp, fn_node, _line = idx[name]

    sc = _BytePumpScanner()
    sc.visit(fn_node)
    rs = _ReturnScanner()
    rs.visit(fn_node)

    # Identify candidate accumulator: a local with >=2 compound ops AND
    # 1 byte-zext direct assign (the "first byte" initializer pattern).
    # Locals with 2+ byte-zext assigns are SCRATCHES, not accumulators --
    # they already play the role we'd suggest introducing.
    candidates = []
    for nm, count in sc.compound_count.items():
        bz = sc.byte_zext_assign_count.get(nm, 0)
        if count >= 2 and bz == 1:
            candidates.append((nm, count, bz))

    if not candidates:
        return None
    # Prefer returned accumulators (the lever's target -- demote from EAX).
    candidates.sort(
        key=lambda c: (c[0] in rs.returned_names, c[1] + c[2]),
        reverse=True,
    )
    acc, comp, bz = candidates[0]

    # Look for an EXISTING byte scratch: a local with 2+ byte-zext assigns
    # that ISN'T the accumulator itself.
    existing_scratch: Optional[str] = None
    for nm, bz_count in sc.byte_zext_assign_count.items():
        if nm == acc:
            continue
        if bz_count >= 2:
            existing_scratch = nm
            break

    return BytePumpHint(
        function=name,
        accumulator=acc,
        compound_op_count=comp,
        byte_zext_assign_count=bz,
        returned=(acc in rs.returned_names),
        existing_byte_scratch=existing_scratch,
    )


# ── Rendering ──────────────────────────────────────────────────────────


def render(hint: BytePumpHint) -> str:
    """One-line text rendering for the ``-v`` decomp-verify output."""
    accum = hint.accumulator
    parts = [
        f"accumulator '{accum}' has {hint.compound_op_count} compound op(s) "
        f"and {hint.byte_zext_assign_count} byte-zext assign(s)",
    ]
    if hint.returned:
        parts.append("returned (claims EAX from return-MOV)")
    if hint.existing_byte_scratch is None:
        parts.append(
            f"no byte-scratch local -- introduce `int t` and route byte "
            f"loads + shifts through t, leaving '{accum}' with only `r += t` "
            f"adds (workhorse rotation)"
        )
    else:
        parts.append(
            f"byte-scratch '{hint.existing_byte_scratch}' exists but "
            f"'{accum}' still bears compound ops -- move shifts onto "
            f"'{hint.existing_byte_scratch}'"
        )
    return "; ".join(parts)


def to_json(hint: BytePumpHint) -> dict:
    """JSON serialisation for ``--json`` mode."""
    return {
        "rule": "119",
        "name": "byte_pump_workhorse",
        "function": hint.function,
        "accumulator": hint.accumulator,
        "compound_op_count": hint.compound_op_count,
        "byte_zext_assign_count": hint.byte_zext_assign_count,
        "returned": hint.returned,
        "existing_byte_scratch": hint.existing_byte_scratch,
    }
