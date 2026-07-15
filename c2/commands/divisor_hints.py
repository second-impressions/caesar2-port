"""Rule 5 / 5b / 5c divisor strength-reduction predictor.

Walks the per-routine IR forest (built by :mod:`c2.regalloc.trace` from the
instrumented compiler's ``tn`` / ``tl`` / ``nb`` records) to classify each
``O_DIV`` (and ``O_MOD``) node by what the wcc386 back end will emit:

  * **literal_pow2**  -- right operand is a ``TN_CONS`` (constant leaf);
                         likely takes the Pow2Div / By2Div strength-reduction
                         path (Rule 5).  Bytes saved over ``idiv``.
  * **literal_other** -- right is a constant but probably not a power of 2
                         (we can't see the literal value reliably from the
                         trace; this is a "trust the asm" fallback).
  * **shared_temp_5c** -- right is a ``TN_LEAF`` wrapping a name, AND there's
                         an ``O_MOD`` in the same routine whose right is the
                         SAME leaf payload (i.e. CSE shared the divisor temp
                         across ``/`` and ``%``).  This is the Rule 5c
                         residual: the divisor is no longer a literal at
                         codegen time, so V_OP2TWO/V_OP2POW2 fail and BOTH
                         operators go to ``idiv``.  Source code can NOT fix
                         this without changing semantics.
  * **var_divisor**   -- right is a memory / register / non-shared temp;
                         normal ``idiv`` emission (no strength reduction).

The classification uses ONLY the IR forest -- no asm inspection needed -- so
it surfaces predictively (before the byte-diff exists), and explains a
diff after the fact when one does.  Pairs with decomp-verify.

Output hint shape:
    DivisorHint(func, divides=[DivClass(line, kind, rule, note), ...])

Rules registry mapping (see c2.commands.rules_registry):
    literal_pow2  -> Rule 5  ("PS shows sar;shl;sbb;sar idiom -> use `/2^N`")
    shared_temp_5c -> Rule 5c ("`%` next to `/` of SAME value -> keep `/`,
                                don't switch to `>>`; CSE locks in idiv")
    var_divisor   -> (no actionable rule; informational only)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from c2 import regalloc
from c2.ir import (
    IRForest, Node,
    TN_BINARY, TN_CONS, TN_LEAF,
    N_TEMP, N_MEMORY, N_REGISTER, N_INDEXED, N_CONSTANT,
)

# Tree opcode values (10.0a verified -- O_DIV=7 confirmed via probe.c's
# `gA/2` tn record; from OW v1 cgdefs.h enum, position-confirmed).
O_DIV    = 7
O_MOD    = 8
O_RSHIFT = 12
O_LSHIFT = 13


# ---- model ----------------------------------------------------------------

@dataclass
class DivClass:
    """Classification of one O_DIV or O_MOD tree node."""
    line: int                  # source line of the divide
    op: str                    # "/" or "%"
    kind: str                  # see module docstring
    rule: str | None           # rule id ("5", "5c", ...) or None
    note: str                  # human-readable explanation
    div_ptr: int               # in-compiler ptr of the O_DIV/O_MOD tn (for debug)
    rhs_ptr: int               # in-compiler ptr of the right operand leaf
    rhs_cls: int               # right.cls (TN_CONS=0x12 / TN_LEAF=0)
    rhs_payload: int           # right.payload (name ptr or constant)


@dataclass
class DivisorHint:
    """All divides + modulos in a function, classified."""
    func: str
    divides: list[DivClass] = field(default_factory=list)

    def has_actionable(self) -> bool:
        return any(d.rule for d in self.divides)

    def by_rule(self, rule: str) -> list[DivClass]:
        return [d for d in self.divides if d.rule == rule]


# ---- classifier -----------------------------------------------------------

def _is_literal_const_leaf(n: Node | None) -> bool:
    """True when the operand leaf is a TN_CONS-class wrapper.  In 10.0a a
    TGLeaf wrapping an ``N_CONSTANT`` name morphs the leaf class to
    ``TN_CONS`` (= 0x12) -- the value is a compile-time literal."""
    return n is not None and n.kind == "tl" and n.cls == TN_CONS


def _wrapped_name_class(n: Node | None) -> int | None:
    """When ``n`` is a TGLeaf wrapping a Name, return that Name's ``cls``.
    Returns ``None`` if the leaf isn't name-wrapping or the name isn't
    resolved (the trace didn't see its ``nb`` event)."""
    if n is None or n.kind != "tl" or n.name is None:
        return None
    return n.name.cls


def _classify_one(div_node: Node, mod_rhs_payloads: set[int]) -> DivClass:
    """Classify a single O_DIV or O_MOD node.

    ``mod_rhs_payloads`` is the set of ``.payload`` values seen as the right
    operand of any ``O_MOD`` in the same routine -- the CSE-sharing lookup
    set.  For a TN_CONS leaf, the payload IS the in-compiler pointer to the
    constant-class name (a unique value per literal constant per
    compilation); two leaves pointing at the same constant name => the same
    literal.  For a TN_LEAF wrapping a temp / memory / register name, the
    payload is the name pointer; sharing => CSE.
    """
    op_name = {O_DIV: "/", O_MOD: "%"}.get(div_node.op, f"op{div_node.op}")
    right = div_node.right

    rhs_ptr     = right.ptr if right is not None else 0
    rhs_cls     = right.cls if right is not None else -1
    rhs_payload = right.payload if right is not None and right.kind == "tl" else 0
    line        = div_node.line if div_node.line is not None else 0

    if right is None:
        return DivClass(line=line, op=op_name, kind="missing_rhs",
                        rule=None, note="right operand not in trace",
                        div_ptr=div_node.ptr, rhs_ptr=0, rhs_cls=-1,
                        rhs_payload=0)

    # ---- Rule 5c shared-divisor detection ----
    #
    # Rule 5c only fires when the compiler CSEs the divisor into a temp
    # before codegen.  Two SIGNAL strengths we can detect from the IR:
    #
    #   1. STRONG (shared_temp_5c):  the IR ALREADY shows the divisor as a
    #      TN_LEAF wrapping an N_TEMP name, shared between `/` and `%`.
    #      Front-end already coalesced -> codegen sees a temp, not a literal
    #      -> V_OP2TWO/V_OP2POW2 fail -> BOTH go to idiv.  Rule 5c FIRES.
    #
    #   2. WEAK (paired_const_div_mod):  `/N` and `%N` reference the SAME
    #      constant-class name but each via its OWN TN_CONS leaf.  Rule 5c
    #      COULD fire post-CSE -- depends on the optimizer / pressure.  In
    #      practice (probe.c verification 2026-06: rule5c probe shows
    #      Pow2Div + separate idiv on the `%`), this signature usually does
    #      NOT trigger Rule 5c in the back end; we surface it as INFO so a
    #      human can sanity-check the asm.
    if div_node.op == O_DIV and right.kind == "tl" \
            and right.payload in mod_rhs_payloads:
        nc = _wrapped_name_class(right)
        if nc == N_TEMP:
            return DivClass(line=line, op=op_name, kind="shared_temp_5c",
                            rule="5c",
                            note=("Rule 5c: divisor CSE'd into a temp "
                                  "across `/` and `%`; both emit idiv. "
                                  "KEEP `/2^N` -- the shared temp defeats "
                                  "strength reduction"),
                            div_ptr=div_node.ptr, rhs_ptr=rhs_ptr,
                            rhs_cls=rhs_cls, rhs_payload=rhs_payload)
        if _is_literal_const_leaf(right):
            return DivClass(line=line, op=op_name, kind="paired_const_div_mod",
                            rule=None,
                            note=("`/` and `%` of the SAME constant in this "
                                  "routine -- Rule 5c CAN fire if the "
                                  "optimizer CSEs the constant into a temp "
                                  "(rare; check the asm for two idivs)"),
                            div_ptr=div_node.ptr, rhs_ptr=rhs_ptr,
                            rhs_cls=rhs_cls, rhs_payload=rhs_payload)

    # ---- non-shared classification ----

    # Literal constant -- Pow2Div/By2Div if power of 2.
    if _is_literal_const_leaf(right):
        return DivClass(line=line, op=op_name, kind="literal_const",
                        rule="5" if div_node.op == O_DIV else None,
                        note=("literal constant divisor -- "
                              "Pow2Div/By2Div applies if pow2 "
                              "(check asm for sar/shl/sbb)"),
                        div_ptr=div_node.ptr, rhs_ptr=rhs_ptr,
                        rhs_cls=rhs_cls, rhs_payload=rhs_payload)

    name_cls = _wrapped_name_class(right)
    if name_cls == N_TEMP:
        return DivClass(line=line, op=op_name, kind="temp_divisor",
                        rule=None,
                        note="temp divisor -- emits idiv (no strength reduction)",
                        div_ptr=div_node.ptr, rhs_ptr=rhs_ptr,
                        rhs_cls=rhs_cls, rhs_payload=rhs_payload)
    if name_cls in (N_MEMORY, N_INDEXED):
        return DivClass(line=line, op=op_name, kind="memory_divisor",
                        rule=None, note="memory divisor -- emits idiv",
                        div_ptr=div_node.ptr, rhs_ptr=rhs_ptr,
                        rhs_cls=rhs_cls, rhs_payload=rhs_payload)
    if name_cls == N_REGISTER:
        return DivClass(line=line, op=op_name, kind="reg_divisor",
                        rule=None, note="register divisor -- emits idiv",
                        div_ptr=div_node.ptr, rhs_ptr=rhs_ptr,
                        rhs_cls=rhs_cls, rhs_payload=rhs_payload)

    return DivClass(line=line, op=op_name, kind="var_divisor",
                    rule=None,
                    note=f"variable divisor (right={right.cls_name}) -- emits idiv",
                    div_ptr=div_node.ptr, rhs_ptr=rhs_ptr,
                    rhs_cls=rhs_cls, rhs_payload=rhs_payload)


def classify_routine(ir: IRForest, routine: dict | None = None) -> list[DivClass]:
    """Classify every O_DIV and O_MOD node in a routine's IR forest.

    When ``routine`` is given, additionally cross-reference the regalloc
    trace to detect the actual Rule 5c OUTCOME (fired vs missed) for any
    paired-const div/mod case.  Without routine data we can only flag the
    candidate signature.

    Iterates ``ir.all_nodes`` (the chronological list of every tn ever
    emitted) -- the ``ir.nodes`` dict overwrites on ptr reuse, so it'd hide
    intermediate divides whose ptr is later reclaimed for a different node.
    """
    # First pass: collect the right-operand PAYLOADs of all O_MOD nodes;
    # the payload is the in-compiler ptr the leaf wraps (a constant-class
    # name for literals, a temp/memory/register name otherwise).  Two leaves
    # with the same payload point at the SAME underlying name == CSE
    # candidate (Rule 5c).
    mod_rhs_payloads: set[int] = set()
    mod_lines: set[int] = set()
    div_lines: set[int] = set()
    for n in ir.all_nodes:
        if n.kind != "tn":
            continue
        if n.op == O_MOD and n.right is not None and n.right.kind == "tl":
            mod_rhs_payloads.add(n.right.payload)
            mod_lines.add(n.line if n.line is not None else 0)
        elif n.op == O_DIV:
            div_lines.add(n.line if n.line is not None else 0)

    out: list[DivClass] = []
    for n in ir.all_nodes:
        if n.kind != "tn":
            continue
        if n.op not in (O_DIV, O_MOD):
            continue
        cls = _classify_one(n, mod_rhs_payloads)
        # The regalloc trace records every conflict's CREATION line but not
        # whether the temp is REUSED for both ops post-codegen -- the Rule
        # 5/5c choice happens in the optab matcher AFTER regalloc.  So a
        # trace-based verdict on FIRED vs MISSED isn't possible from the
        # alloc records alone.  We surface a precise pointer to BOTH lines
        # so the user can read the per-source-line regalloc view (rendered
        # above the divisor hint) and the asm diff side-by-side to confirm.
        if routine is not None and cls.kind == "paired_const_div_mod":
            mod_line = next((m for m in sorted(mod_lines)
                             if m and m != cls.line), None)
            if mod_line is not None:
                cls.note = (f"`/` and `%` of the SAME constant -- check the "
                            f"per-line regalloc view at L{mod_line} and "
                            f"L{cls.line}: if PS shows TWO idivs sharing a "
                            f"register, Rule 5c FIRED (keep `/N`); if PS "
                            f"shows one idiv + a strength-reduction idiom, "
                            f"Rule 5c MISSED (consider `>>` if non-negative).")
        out.append(cls)
    out.sort(key=lambda d: (d.line, d.div_ptr))
    return out


# ---- public detect ------------------------------------------------------

REPO = Path(__file__).resolve().parents[2]
_SRC = REPO / "decomp" / "src"
_INC = REPO / "decomp" / "include"


@lru_cache(maxsize=4096)
def _file_trace(func: str, file: str | None) -> dict | None:
    """Same fallback the regalloc/rover hints use: trace the function's
    .c file standalone when no build trace is active."""
    try:
        from c2.commands.regtrace import _find_function
        sf, *_ = _find_function(func, file)
        return regalloc.file_trace(sf, _INC)
    except Exception:
        return None


def _lookup_routine(func: str, file: str | None) -> dict | None:
    """Find the routine record for ``func`` in either a build-wide trace or
    a standalone file trace.  Returns the routine dict (with ``ir`` attached
    by the parser) or None."""
    # Build-wide trace (decomp-verify hot path) -- skipped here; the routine
    # is resolved by the caller and ``ir`` is present.  This helper is for
    # the standalone path.
    td = _file_trace(func, file)
    if not td:
        return None
    # Locate the routine.  Try line-range attribution like regalloc_hints.
    try:
        from c2.commands.regalloc_hints import _routine_by_line_range
        return _routine_by_line_range(td.get("routines", []), func, file)
    except Exception:
        return None


def detect(func: str, *, file: str | None = None,
           routine: dict | None = None) -> DivisorHint | None:
    """Return a DivisorHint for ``func`` if its IR forest contains any
    ``/`` or ``%`` to classify; otherwise ``None``.

    ``routine`` can be passed directly (when the caller already has the
    parsed routine in hand -- the decomp-verify hot path) to avoid the
    file-trace fallback.
    """
    r = routine if routine is not None else _lookup_routine(func, file)
    if r is None:
        return None
    ir = r.get("ir")
    if ir is None or not ir.nodes:
        return None
    # Pass the routine to classify_routine so it can cross-reference
    # the regalloc trace and decide Rule 5c FIRED vs MISSED for paired
    # div/mod cases.
    divides = classify_routine(ir, routine=r)
    if not divides:
        return None
    return DivisorHint(func=func, divides=divides)


def render_lines(h: DivisorHint, *, max_items: int = 6) -> list[str]:
    """Render the hint as a short list of lines for decomp-verify output."""
    if not h.divides:
        return []
    head_bits = []
    for rule in ("5", "5c"):
        cnt = len(h.by_rule(rule))
        if cnt:
            head_bits.append(f"Rule {rule}: {cnt}")
    info = sum(1 for d in h.divides if d.rule is None)
    if info:
        head_bits.append(f"info: {info}")
    lines = [f"divisors: " + ", ".join(head_bits)] if head_bits else []
    # One per actionable divide first (so they aren't truncated by max_items).
    shown: list[DivClass] = (
        [d for d in h.divides if d.rule]
        + [d for d in h.divides if d.rule is None]
    )
    for d in shown[:max_items]:
        tag = f"Rule {d.rule}" if d.rule else "info"
        lines.append(f"  L{d.line} `{d.op}` [{d.kind}] {tag}: {d.note}")
    if len(shown) > max_items:
        lines.append(f"  ... and {len(shown) - max_items} more")
    return lines
