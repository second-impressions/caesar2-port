"""Rule 155 hint: a throwaway boolean-expression call arg spills where a
reassign-to-constant would not.

Surfaces the lever proven in
``docs/codegen-experiments/reassign-to-constant.py`` and documented as
Rule 155 in ``docs/watcom-codegen-patterns.md``: a call argument of the
form ``(c != K) + N`` (or ``c ? N1 : N2``, ``(c == K) + base``, ``!c``)
materialises a boolean temp that is a *new live value* crossing any
preceding calls.  At the register-pressure spill threshold that temp is
the 7th cross-call value and spills (``sub esp, 4``).  Reassigning ``c``
to the constant first -- ``if (c == K) c = N1; else c = N2; call(..., c)``
-- lets ``c``'s original die at the compare; the constant result reuses
``c``'s own register and no extra cross-call value exists.

Distinct from Rule 26: BOTH forms fold to the identical ``setcc``, so
Rule 26's detector (``detect_rule_26``) stays silent.  The spill delta
is the only observable symptom -- which is why this is easy to miss.

This detector is AST + spill-gate:

1. **AST** (pycparser ``FuncDef``): find a ``FuncCall`` argument that is
   a *setcc-foldable boolean expression on a local* ``c`` -- a ``TernaryOp``
   with a constant-ish arms, or a ``BinaryOp`` whose root op is a
   comparison (``!=``, ``==``, ``<``, ...) optionally wrapped in ``+``/
   ``-``/arithmetic.  ``c`` must be a scalar local assigned earlier in
   the function (so its original is live across the call).

2. **Spill gate** (the reliable half): RC's prologue frame is BIGGER
   than PS's at EQUAL push count -- the ``Rule 116 / pressure-spill``
   class from the ``Frame:`` header.  This is the symptom that
   distinguishes Rule 155 (a real spill) from a byte-neutral throwaway
   (no pressure).  Without the gate the hint would fire on every
   ``c ? a : b`` call arg, almost all of them byte-neutral.

The ground-truth positive is ``forum_industry_screen`` pre-fix (RC
spills 7 vs PS 6, ``sub esp, 0x1c`` vs ``0x18``, equal 6 pushes); the
byte-exact corpus is the negative set (detector must stay silent).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pycparser import c_ast

# Comparison root operators whose result is a 0/1 boolean Watcom folds to
# `setcc`.  A throwaway arg rooted at one of these (optionally wrapped in
# arithmetic) is the Rule 155 shape.
_CMP_OPS = {"==", "!=", "<", "<=", ">", ">="}


@dataclass
class ReassignHint:
    local: str           # the local `c` whose boolean is thrown away
    line: int            # source line of the throwaway call arg
    call: str            # the callee name (for the message)
    arms: tuple          # the constant arms, if a ternary ((N1, N2))
    ps_frame: int
    rc_frame: int
    slot_delta: int      # (rc_frame - ps_frame) // 4


def _is_int_literal(node) -> bool:
    if isinstance(node, c_ast.Constant):
        try:
            int(node.value.rstrip("uUlL"), 0)
            return True
        except ValueError:
            return False
    return False


def _ternary_arms(node) -> Optional[tuple]:
    """If ``node`` is `cond ? A : B` with A, B integer-literal-ish, return
    (A, B) as source strings; else None.  We accept casts/IDs-to-const too
    but keep it conservative -- the message just illustrates the reassign."""
    if not isinstance(node, c_ast.TernaryOp):
        return None
    a, b = node.iftrue, node.iffalse
    # strip casts
    for _ in range(4):
        if isinstance(a, c_ast.Cast): a = a.expr
        else: break
    for _ in range(4):
        if isinstance(b, c_ast.Cast): b = b.expr
        else: break
    def _txt(n):
        if isinstance(n, c_ast.Constant): return n.value
        if isinstance(n, c_ast.ID): return n.name
        return None
    ta, tb = _txt(a), _txt(b)
    if ta is None or tb is None:
        return None
    return (ta, tb)


def _bool_expr_local(node) -> Optional[str]:
    """If ``node`` is a setcc-foldable boolean expression rooted at a
    comparison whose primary operand is a bare local ID, return that
    local's name; else None.

    Accepts:  `c != K`, `c == K`, `K == c`, `(c != K) + N`, `c ? .. : ..`,
    `!c`.  The root must be a comparison (or a ternary whose cond is);
    arithmetic wrappers (`+`/`-`/`*`/casts) are peeled.  The comparison
    operand we keep must be a bare ``c_ast.ID`` (a local), not a
    field/array read -- those are not the Rule 155 shape (the boolean
    temp there is cheap / already materialised).
    """
    seen = 0
    cur = node
    # peel arithmetic/cast wrappers down to the comparison or ternary
    while seen < 16:
        seen += 1
        if isinstance(cur, c_ast.Cast):
            cur = cur.expr
        elif isinstance(cur, c_ast.UnaryOp) and cur.op == "!":
            # `!c` -> boolean of the bare operand
            inner = cur.expr
            if isinstance(inner, c_ast.ID):
                return inner.name
            return None
        elif isinstance(cur, c_ast.BinaryOp) and cur.op in ("+", "-"):
            # `(cmp) + N` -- descend into the side that is the comparison.
            # Only the comparison side carries the boolean; the other is
            # an arithmetic offset.
            for side in (cur.left, cur.right):
                if isinstance(side, c_ast.BinaryOp) and side.op in _CMP_OPS:
                    cur = side
                    break
            else:
                return None
        elif isinstance(cur, c_ast.TernaryOp):
            cond = cur.cond
            # `c ? A : B` -- cond may be a bare ID (truthiness) or a
            # comparison.  A bare-ID cond roots at that local directly.
            if isinstance(cond, c_ast.ID):
                return cond.name
            cur = cond
        elif isinstance(cur, c_ast.BinaryOp) and cur.op in _CMP_OPS:
            break
        else:
            return None
    # cur is a comparison; one operand must be a bare local ID
    if not (isinstance(cur, c_ast.BinaryOp) and cur.op in _CMP_OPS):
        return None
    for side in (cur.left, cur.right):
        if isinstance(side, c_ast.ID):
            return side.name
    return None


class _CallArgScan(c_ast.NodeVisitor):
    """Find the first FuncCall argument that is a Rule-155 throwaway on a
    local, and record the set of scalar locals assigned in the function."""

    def __init__(self) -> None:
        self.locals: set[str] = set()
        # name -> first assignment line (decl init or `=` assignment)
        self.assigned: dict[str, int] = {}
        self.hit: Optional[ReassignHint] = None
        # ordered list of (line, callee) for every FuncCall seen so far, so we
        # can check that a candidate local's original is live across at least
        # one PRECEDING call (the spill trigger -- the boolean temp crosses it)
        self._calls: list[tuple[int, str]] = []

    def _line(self, node) -> int:
        c = getattr(node, "coord", None)
        return (getattr(c, "line", 0) or 0) if c else 0

    def visit_Decl(self, node) -> None:
        if node.name:
            self.locals.add(node.name)
            if getattr(node, "init", None) is not None:
                self.assigned.setdefault(node.name, self._line(node))
        self.generic_visit(node)

    def visit_Assignment(self, node) -> None:
        if node.op == "=" and isinstance(node.lvalue, c_ast.ID):
            self.assigned.setdefault(node.lvalue.name, self._line(node))
        self.generic_visit(node)

    def visit_FuncCall(self, node) -> None:
        callee = node.name.name if isinstance(node.name, c_ast.ID) else ""
        call_line = self._line(node)
        # record this call BEFORE scanning its args, so a *nested* call in the
        # throwaway arg (rare) is still counted as preceding for later calls
        if call_line:
            self._calls.append((call_line, callee))
        if self.hit is None and node.args:
            for arg in node.args.exprs or []:
                local = _bool_expr_local(arg)
                if local is None or local not in self.locals:
                    continue
                al = self.assigned.get(local)
                if al is None or al >= call_line:
                    continue
                # the lever requires the local's original be live across at
                # least one call BETWEEN its assignment and this throwaway --
                # that intervening call is what the boolean temp spills across
                intervening = [(cl, ce) for (cl, ce) in self._calls if al < cl < call_line]
                if not intervening:
                    continue
                arms = _ternary_arms(arg) or ()
                self.hit = ReassignHint(
                    local=local, line=call_line, call=callee, arms=arms,
                    ps_frame=0, rc_frame=0, slot_delta=0)
                break
        self.generic_visit(node)


def _frame_spill_delta(orig_insns, recomp_insns) -> Optional[tuple[int, int, int, int, int]]:
    """Return ``(ps_frame, rc_frame, ps_pushes, rc_pushes, slot_delta)`` when
    RC's prologue frame is strictly bigger than PS's AND push counts are
    equal (the Rule 116 / pressure-spill class -- a genuine spill, not a
    WorthProlog callee-save swap).  Else None.

    Lazy import so the hint module stays cheap when frames match.
    """
    try:
        from c2.commands.frame_hints import (
            detect_frame_alloc, count_prologue_pushes)
    except Exception:
        return None
    ps_frame = detect_frame_alloc(orig_insns)
    rc_frame = detect_frame_alloc(recomp_insns)
    if ps_frame is None or rc_frame is None or rc_frame <= ps_frame:
        return None
    ps_push = count_prologue_pushes(orig_insns)
    rc_push = count_prologue_pushes(recomp_insns)
    if ps_push != rc_push:
        return None
    return (ps_frame, rc_frame, ps_push, rc_push, (rc_frame - ps_frame) // 4)


def detect(func_ast, ps_insns, rc_insns) -> Optional[ReassignHint]:
    """Return a ``ReassignHint`` iff (a) the source AST has a throwaway
    boolean-expression call arg on an assigned scalar local, and (b) RC
    spills at least one slot PS does not at equal push count.  None
    otherwise (including on byte-exact functions, where the frames match
    and the gate fails)."""
    spill = _frame_spill_delta(ps_insns, rc_insns)
    if spill is None:
        return None
    ps_frame, rc_frame, ps_push, rc_push, slot_delta = spill
    if func_ast is None:
        return None
    scan = _CallArgScan()
    try:
        scan.visit(func_ast.body)
    except Exception:
        return None
    if scan.hit is None:
        return None
    h = scan.hit
    h.ps_frame = ps_frame
    h.rc_frame = rc_frame
    h.slot_delta = slot_delta
    return h


def render(h: ReassignHint) -> str:
    arms = ""
    if h.arms:
        arms = (f"  The arg is a ternary -- reassign "
                f"`if (c==K) c={h.arms[0]}; else c={h.arms[1]};` then pass `c`.")
    return (
        f"Reassign-to-constant (Rule 155): the call to `{h.call}` at line "
        f"{h.line} passes a throwaway boolean expression on the local "
        f"`{h.local}` (e.g. `({h.local} != K) + N` or `{h.local} ? A : B`).  "
        f"That materialises a boolean temp that is a new live value crossing "
        f"the preceding calls; at the pressure threshold it spills (RC frame "
        f"{h.rc_frame:#x} vs PS {h.ps_frame:#x}, +{h.slot_delta} slot at "
        f"equal push count).  PS reassigns `{h.local}` to the constant "
        f"first -- `if ({h.local} == K) {h.local} = N1; else {h.local} = N2; "
        f"{h.call}(..., {h.local})` -- so `{h.local}`'s original dies at the "
        f"compare and the constant reuses its register (no spill).  Both "
        f"forms fold to the same `setcc`, so Rule 26 stays silent; the spill "
        f"delta is the only symptom.  Proof: "
        f"docs/codegen-experiments/reassign-to-constant.py.{arms}")
