"""``c2 binir-audit`` -- corpus-wide structural-soundness audit for the
binir reverse-IR catalog.

THE INVARIANT
=============

For every **byte-exact** function in the decomp corpus, every binir kind
recovered from PS.EXE asm MUST have at least as many structural
counterparts in the forward IR forest (built from the live compile
trace).  In formal terms, for each (function f, binir kind k)::

    count(forward IR nodes in f matching SIGNATURE[k]) >= recover_count(k, f)

WHY: byte-exact means the compiler emitted the SAME asm for our source as
PS did for theirs.  So our forward IR is GROUND TRUTH for what the asm
came from.  If binir recovers N divides but the forward IR only has N-1
TN_BINARY/O_DIV nodes, our binir is hallucinating one -- the reverse
analysis is producing fictitious trees, and any user of ``c2 tree-diff``
will be misled.

The check is intentionally LOOSER than ``shape_from_binir_ops`` ==
``shape_from_node``: binir loses information when going from asm back to
IR (it cannot tell `arr[i]` from a bare memory load; it cannot tell which
jcc inversion the front end applied; etc.).  Instead we declare a
:class:`TreePattern` per binir kind asserting JUST the structural facts
binir DOES recover faithfully.

WHEN ADDING A NEW BINIR KIND
============================

1. Add the asm matcher in :mod:`c2.binir` (kind = ``"my_pattern"``).
2. Add the converter in :mod:`c2.tree_diff` (``_binir_op_to_shape``).
3. Add a :class:`KindSignature` here describing the forward-IR shape
   binir's recovery implies.  Use the LOOSEST signature that still
   asserts something meaningful -- e.g. for `cmp_jcc`, just ``cls=TN_COMPARE``
   (the specific O_CMP_* might be flipped by FlipCond).
4. Run ``uv run c2 binir-audit``.  Zero violations on byte-exact functions
   is the required gate.  Otherwise the pattern is unsound -- fix the
   binir matcher or the signature.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Callable, Iterable, Optional

import typer

from c2 import binir, regalloc
from c2.commands.decomp_verify import _disasm_for_diff, _load_le_code_and_fixups
from c2.ir import (
    CG_OP_NAMES, IRForest, Name, Node,
    N_CONSTANT, N_MEMORY, N_TEMP, N_REGISTER, N_INDEXED,
    O_AND, O_OR, O_XOR, O_PLUS, O_MINUS, O_TIMES, O_DIV, O_MOD,
    O_RSHIFT, O_LSHIFT, O_CONVERT, O_CONVERT_U, O_NEGATE, O_COMPLEMENT,
    TN_LEAF, TN_UNARY, TN_BINARY, TN_COMPARE, TN_ASSIGN, TN_LV_ASSIGN,
    TN_FLOW, TN_PRE_GETS, TN_LV_PRE_GETS, TN_POST_GETS,
    TN_PARM, TN_CALL, TN_COMMA, TN_BIT_LVALUE, TN_BIT_RVALUE, TN_CONS,
    TN_SIDE_EFFECT, TN_CLASS_NAME,
    INS_OP_CALL, INS_OP_CALL_INDIRECT,
)


REPO = Path(__file__).resolve().parents[2]
SRC_DIR = REPO / "decomp" / "src"
INCLUDE_DIR = REPO / "decomp" / "include"
EXE_PATH = REPO / "data" / "PS.EXE"
SYM_PATH = REPO / "data" / "out" / "symbols.json"
VERIFY_CACHE = REPO / ".c2-cache" / "verify.json"


# ── Per-kind structural signatures ───────────────────────────────────────
#
# A signature is a Callable[[Node], bool] that returns True iff the node
# is a forward-IR counterpart to the binir kind.  Predicates are used
# (not TreePattern) so we can express constraints like "right child is a
# constant" or "op is O_DIV OR O_MOD" -- richer than the declarative
# TreePattern can do.
#
# When a kind has no forward-IR counterpart (control flow lives in the
# block graph, not the IR forest), the signature is None and the audit
# skips containment.

@dataclass
class KindSignature:
    """Per-binir-kind forward-IR assertion.

    ``predicate`` is None for kinds with no forward-IR counterpart
    (control-flow / call-lowering -- those live in the block graph, not
    the IR forest).  The audit skips containment for those but still
    counts the recovered ops in the histogram.
    """
    predicate: Optional[Callable[[Node], bool]]
    description: str = ""


def _is_const_leaf(n) -> bool:
    """``tl`` leaf wrapping an N_CONSTANT name (the canonical "constant
    operand" shape -- TN_CONS or TN_LEAF both qualify when name.cls is
    N_CONSTANT)."""
    return (n is not None and n.kind == "tl"
            and n.name is not None and n.name.cls == N_CONSTANT)


def _is_binary_with_const(op_id: int) -> Callable[[Node], bool]:
    """A TN_BINARY of the given op with a constant operand on EITHER side.

    10.0a's IR puts constants on the LEFT for commutative ops (`3 * x` ->
    `TIMES(CONST=3, x)`, not `TIMES(x, CONST=3)`).  For non-commutative
    ops (DIV, MOD, SHIFT) the constant is typically on the right (`x / 2`
    -> `DIV(x, CONST=2)`); but for the audit we accept either side -- the
    binir recovery doesn't care which.
    """
    def pred(n: Node) -> bool:
        if n.kind != "tn" or n.cls != TN_BINARY or n.op != op_id:
            return False
        return (_is_const_leaf(getattr(n, "left", None))
                or _is_const_leaf(getattr(n, "right", None)))
    return pred


def _is_any_binary_with_const(*op_ids: int) -> Callable[[Node], bool]:
    """A TN_BINARY / TN_PRE_GETS / TN_POST_GETS whose op is in ``op_ids``
    and which has a constant operand on EITHER side.

    Captures shape EQUIVALENCES that binir cannot disambiguate from asm
    alone -- the most common being ``shl reg, N`` which can come from:

      * source ``x * 2^N``  -> TN_BINARY/O_TIMES with const
      * source ``x << N``   -> TN_BINARY/O_LSHIFT with const
      * source ``x *= 2^N`` -> TN_PRE_GETS/O_TIMES with const
      * source ``x <<= N``  -> TN_PRE_GETS/O_LSHIFT with const

    All four compile to the SAME asm, so the audit must tolerate any of
    them as a valid forward counterpart.
    """
    ids = set(op_ids)
    def pred(n: Node) -> bool:
        if n.kind != "tn" or n.cls not in (TN_BINARY, TN_PRE_GETS,
                                            TN_LV_PRE_GETS, TN_POST_GETS):
            return False
        if n.op not in ids:
            return False
        return (_is_const_leaf(getattr(n, "left", None))
                or _is_const_leaf(getattr(n, "right", None)))
    return pred


def _is_compare(n: Node) -> bool:
    return n.kind == "tn" and n.cls == TN_COMPARE


def _is_unary(op_id: int) -> Callable[[Node], bool]:
    def pred(n: Node) -> bool:
        return n.kind == "tn" and n.cls == TN_UNARY and n.op == op_id
    return pred


def _is_unary_convert(n: Node) -> bool:
    """O_CONVERT or O_CONVERT_U (both are convert/extend opcodes in 10.0a)."""
    return (n.kind == "tn" and n.cls == TN_UNARY
            and n.op in (O_CONVERT, O_CONVERT_U))


def _is_assign_const_to_mem(n: Node) -> bool:
    """TN_ASSIGN/LV_ASSIGN where LHS is memory-class leaf and the source
    operand is a constant.  10.0a typically uses LHS=left, RHS=right for
    assigns, but accept either side for robustness."""
    if n.kind != "tn" or n.cls not in (TN_ASSIGN, TN_LV_ASSIGN):
        return False
    l = getattr(n, "left", None)
    r = getattr(n, "right", None)
    if l is None or r is None:
        return False
    l_mem = _reaches_name_class(l, N_MEMORY) or _reaches_name_class(l, N_INDEXED)
    r_mem = _reaches_name_class(r, N_MEMORY) or _reaches_name_class(r, N_INDEXED)
    l_const = _is_const_leaf(l)
    r_const = _is_const_leaf(r)
    return (l_mem and r_const) or (r_mem and l_const)


def _is_pre_gets_with_const(op_id: Optional[int]) -> Callable[[Node], bool]:
    """TN_PRE_GETS (or LV_PRE_GETS) with the given op, constant operand on
    EITHER side.  Forward-IR counterpart of
    ``and/or/xor/add/sub <size> ptr [m], IMM``."""
    def pred(n: Node) -> bool:
        if n.kind != "tn":
            return False
        if n.cls in (TN_PRE_GETS, TN_LV_PRE_GETS):
            if op_id is not None and n.op != op_id:
                return False
            return (_is_const_leaf(getattr(n, "left", None))
                    or _is_const_leaf(getattr(n, "right", None)))
        return False
    return pred


def _is_plus_into_memory(n: Node) -> bool:
    """Forward counterpart of binir ``mem_sum_chain``: an addition whose
    result lands in memory.  Two source forms produce the claimed asm:
    ``g = a + b + ...`` (TN_ASSIGN whose RHS subtree contains a
    TN_BINARY/O_PLUS) and ``g += x`` (TN_PRE_GETS with O_PLUS)."""
    if n.kind != "tn":
        return False
    if n.cls in (TN_PRE_GETS, TN_LV_PRE_GETS):
        return n.op == O_PLUS
    if n.cls not in (TN_ASSIGN, TN_LV_ASSIGN):
        return False

    def has_plus(t, depth=0) -> bool:
        if t is None or depth > 6:
            return False
        if getattr(t, "kind", None) == "tn" and t.cls == TN_BINARY                 and t.op == O_PLUS:
            return True
        return (has_plus(getattr(t, "left", None), depth + 1)
                or has_plus(getattr(t, "right", None), depth + 1))

    return has_plus(getattr(n, "left", None)) or has_plus(getattr(n, "right", None))


def _is_call(n: Node) -> bool:
    return n.kind == "tn" and n.cls == TN_CALL


def _reaches_name_class(n: Node, name_cls: int) -> bool:
    """True iff n is a leaf of that name class OR an interior node whose
    descendant leaves include one (used to handle convert/index wrappers
    around a memory access).

    SPECIAL CASE: a ``tl`` of ``cls=TN_LEAF`` with unresolved ``name`` is
    almost ALWAYS a global-memory reference -- 10.0a's front end emits
    globals as a leaf carrying the data-segment offset in the payload
    field WITHOUT calling AllocName (so the leaf has no corresponding
    ``nb`` record).  For the purposes of the audit invariant
    (``forward_count >= reverse_count``), treating these as a potential
    memory match is the SAFE direction (admits a few false positives but
    avoids spurious "binir hallucinated this" reports for the common
    global-store pattern).
    """
    if n is None:
        return False
    if n.kind == "tl":
        if n.name is not None:
            return n.name.cls == name_cls
        # Unresolved leaf -- treat as memory-like for the memory/index
        # classes (the empirically dominant interpretation).
        if n.cls == TN_LEAF and name_cls in (N_MEMORY, N_INDEXED):
            return True
        return False
    # Recurse through tn / tb interior nodes.
    for child in (getattr(n, "left", None), getattr(n, "right", None)):
        if _reaches_name_class(child, name_cls):
            return True
    return False


# Each binir kind -> the forward-IR signature it implies.  These are LOOSE
# (intentionally) -- we assert only what binir recovers faithfully from asm.
KIND_SIGNATURES: dict[str, KindSignature] = {
    "r5c_idiv_pair":      KindSignature(
        # Two consecutive idivs sharing a divisor: forward has BOTH an
        # O_DIV and an O_MOD with the same RHS.  The shared divisor
        # may be EITHER a constant (literal Rule 5c) OR a memory-loaded
        # variable (general CSE on the divisor) -- both produce the same
        # asm signature.  Loose form: "any divide or mod node".
        lambda n: (n.kind == "tn"
                   and n.cls == TN_BINARY
                   and n.op in (O_DIV, O_MOD)),
        "TN_BINARY/{O_DIV,O_MOD} (any RHS -- could be CSE'd variable)"),
    "g_pow2div":          KindSignature(
        # `sar/shl/sbb/sar` idiom for `x / 2^N` (N>=2).  Source could be
        # `x / 2^N` (O_DIV) or `x >> N` for SIGNED x (O_RSHIFT) -- same asm.
        _is_any_binary_with_const(O_DIV, O_RSHIFT),
        "TN_BINARY/{O_DIV,O_RSHIFT} with constant"),
    "g_div2":             KindSignature(
        _is_any_binary_with_const(O_DIV, O_RSHIFT),
        "TN_BINARY/{O_DIV,O_RSHIFT} with constant divisor (=2)"),
    # All mul_* kinds: `shl reg, N` is ambiguous between O_TIMES (x * 2^N),
    # O_LSHIFT (x << N), O_PRE_GETS/O_TIMES (x *= 2^N) and O_PRE_GETS/O_LSHIFT
    # (x <<= N).  Audit accepts ANY of them.
    "mul_pow2":           KindSignature(
        _is_any_binary_with_const(O_TIMES, O_LSHIFT),
        "TN_BINARY/{O_TIMES,O_LSHIFT} with constant"),
    "mul_const_minus_one":KindSignature(
        _is_any_binary_with_const(O_TIMES),
        "TN_BINARY/O_TIMES with constant (compound shl-sub idiom)"),
    "mul_const_plus_one": KindSignature(
        _is_any_binary_with_const(O_TIMES), ""),
    "mul_lea_scaled_self":KindSignature(
        _is_any_binary_with_const(O_TIMES), ""),
    "mul_lea_scaled":     KindSignature(
        _is_any_binary_with_const(O_TIMES), ""),
    # mul_const = OW v1 CheckMul-style strength-reduction CHAIN of length
    # 3+ (one preservation mov + 3+ shl/add/sub on the same target reg).
    # Maps to a SINGLE TN_BINARY O_TIMES with a constant operand in the
    # forward IR -- by construction Factor recovers exactly the OP_MUL's
    # constant rhs.  Source of truth: watcom 10.0a CheckMul@0x61c32 plate.
    "mul_const":          KindSignature(
        _is_any_binary_with_const(O_TIMES),
        "TN_BINARY/O_TIMES with constant (multi-instruction Factor expansion)"),
    "cmp_jcc":            KindSignature(
        _is_compare,
        "TN_COMPARE (specific O_CMP_* may be FlipCond-inverted)"),
    "zero_test_jcc":      KindSignature(
        _is_compare,
        "TN_COMPARE (test reg,reg -> compare against 0)"),
    "zext_byte_load":     KindSignature(
        _is_unary_convert,
        "TN_UNARY/O_CONVERT(_U) -- explicit zero-extend on a byte load"),
    "zext_load_byte":     KindSignature(_is_unary_convert, ""),
    "zext_load_word":     KindSignature(_is_unary_convert, ""),
    "signext_load_byte":  KindSignature(_is_unary_convert, ""),
    "signext_load_word":  KindSignature(_is_unary_convert, ""),
    # NEW patterns in this thread:
    "pre_gets_mem_const": KindSignature(
        # No op constraint -- the cg_op varies by binop, and the
        # OW-v1-style rewrite of `-=` to `+= -K` produces TN_BINARY+TN_ASSIGN
        # instead.  Loose form: any PRE_GETS with constant RHS, OR an
        # ASSIGN-of-BINARY-with-const-RHS where the LHS reaches memory.
        lambda n: (
            _is_pre_gets_with_const(None)(n)
            or _is_assign_of_binary_with_const_rmw(n)
        ),
        "TN_PRE_GETS or rewritten TN_ASSIGN(MEM, BINARY(MEM, CONST))"),
    "mov_mem_imm":        KindSignature(
        _is_assign_const_to_mem,
        "TN_ASSIGN/LV_ASSIGN with constant RHS to memory LHS"),
    "const_store_run_reg": KindSignature(
        _is_assign_const_to_mem,
        "TN_ASSIGN/LV_ASSIGN with constant RHS (run expands to n ASSIGNs; "
        "reg form = Enregister fired, symbol-based destinations)"),
    "const_store_run_imm": KindSignature(
        _is_assign_const_to_mem,
        "TN_ASSIGN/LV_ASSIGN with constant RHS (run expands to n ASSIGNs; "
        "imm form = Enregister skipped, pointer-local destination -- the "
        "Rule 128 observable)"),
    "ptr_base_materialize": KindSignature(None, "address-mode artifact (&arr[i] LA)"),
    "mem_sum_chain":      KindSignature(
        _is_plus_into_memory,
        "TN_ASSIGN with an O_PLUS RHS to memory, or TN_PRE_GETS(O_PLUS) "
        "(`g = a+b+..` / `g += x` -- the claimed asm is identical; "
        "Rule 130 -- split/merged surface forms are CompressIns artifacts)"),
    "call_with_args":     KindSignature(
        _is_call,
        "TN_CALL (at least one TN_PARM child)"),
    # Control flow lives in the block graph, NOT in the IR forest:
    "branch_jmp":         KindSignature(None, "no IR-forest counterpart"),
    "branch_flag_jcc":    KindSignature(None, "no IR-forest counterpart"),
    # Exit-pair constants: return values / merged-call-site args are
    # lowered in BGReturn / call-site emission, not as forest nodes.
    "farptr_ret_const":   KindSignature(None, "no IR-forest counterpart"),
    "regpair_const_exit": KindSignature(None, "no IR-forest counterpart"),
}


def _is_assign_of_binary_with_const_rmw(n: Node) -> bool:
    """``ASSIGN(MEM, BINARY(MEM, CONST))`` -- the rewritten form of
    `X op= K` when the optimiser folded the temp.  Captures `g -= K`
    rewritten to `g = g + (-K)`."""
    if n.kind != "tn" or n.cls not in (TN_ASSIGN, TN_LV_ASSIGN):
        return False
    l = getattr(n, "left", None)
    r = getattr(n, "right", None)
    if l is None or r is None:
        return False
    if not _reaches_name_class(l, N_MEMORY):
        return False
    if r.kind != "tn" or r.cls != TN_BINARY:
        return False
    rl = getattr(r, "left", None)
    rr = getattr(r, "right", None)
    if rl is None or rr is None:
        return False
    # One operand must reach the same memory; the other must be constant.
    rl_is_mem = _reaches_name_class(rl, N_MEMORY)
    rl_is_const = (rl.kind == "tl" and rl.name is not None
                   and rl.name.cls == N_CONSTANT)
    rr_is_mem = _reaches_name_class(rr, N_MEMORY)
    rr_is_const = (rr.kind == "tl" and rr.name is not None
                   and rr.name.cls == N_CONSTANT)
    return (rl_is_mem and rr_is_const) or (rl_is_const and rr_is_mem)


# ── per-function audit ────────────────────────────────────────────────────

@dataclass
class Violation:
    func: str
    file: str
    kind: str
    note: str = ""


@dataclass
class FuncAudit:
    func: str
    file: str
    byte_exact: bool
    n_forward_nodes: int
    n_reverse_ops: int
    by_kind_recovered: dict[str, int] = field(default_factory=dict)
    by_kind_forward_count: dict[str, int] = field(default_factory=dict)
    n_filtered_by_emit_map: int = 0   # binir ops dropped because they fell
                                       # in a no-user-code region (prolog,
                                       # epilog, or compiler-helper call).
    violations: list[Violation] = field(default_factory=list)
    error: Optional[str] = None


def _count_forward(forest: IRForest, predicate: Callable[[Node], bool]) -> int:
    """Count forward-IR nodes matching ``predicate``.  Walks
    ``all_nodes`` (chronological) -- the free-list-pointer-reuse safe view."""
    return sum(1 for n in forest.all_nodes if predicate(n))


def audit_function(name: str, file: str, *, byte_exact: bool,
                   trace: "regalloc.RegallocTrace") -> FuncAudit:
    result = FuncAudit(func=name, file=file, byte_exact=byte_exact,
                       n_forward_nodes=0, n_reverse_ops=0)
    routine = trace.routine_for(name)
    if routine is None or "ir" not in routine:
        result.error = "no IR forest in trace"
        return result
    forest = routine["ir"]
    result.n_forward_nodes = len(forest.all_nodes)

    insns, ps_size = _ps_function_insns(name)
    if insns is None:
        result.error = "not in symbols.json"
        return result
    ops = binir.recover(list(insns))

    # Filter binir ops by the trace's emit map.  The `il` trace records
    # (captured at AdvanceCode entry -- watcom10.0a tools/patch_trace.py)
    # give us, in codegen order, the BYTE LENGTHS of every user instruction
    # that went through the regular GenObjCode emit path.  Calls + branches
    # + ret use a SEPARATE emit path (DoCall/GenJmp/GenReturn) so they are
    # ABSENT from `emit_lengths`.
    #
    # The cumulative-sum offsets stored in routine["emit_offsets"] are
    # therefore COMPRESSED -- they skip over the missing call/branch/ret
    # bytes.  Don't use them directly against the binary's real offsets.
    # Instead we ALIGN here: walk the binary's disassembled instructions in
    # order; each one whose byte-length matches the next expected
    # ``emit_lengths`` entry is a "regular" user instruction at the binary
    # offset where it sits.  Mismatches are calls/branches/ret -- skipped.
    # The resulting `user_real_offsets` set is the AUTHORITATIVE
    # "user-emit map" against PS.EXE's actual offsets.
    emit_lengths = routine.get("emit_lengths", [])
    user_real_offsets: set[int] = set()
    if emit_lengths:
        j = 0
        for ins_off, ins_size, _bytes, _disasm in insns:
            if j >= len(emit_lengths):
                break
            if ins_size == emit_lengths[j]:
                user_real_offsets.add(ins_off)
                j += 1
            # else: instruction didn't match the expected emit_length --
            # it's a call/branch/ret/synthetic that bypassed AdvanceCode,
            # OR codegen reordered.  Skip it (don't add to user_real_offsets,
            # don't advance j -- we'll try the same emit_length on the
            # next binary instruction).  Robustness note: an actual length
            # divergence (binary ≠ our build) could desync the alignment;
            # mitigated by the fact that the audit runs only on
            # byte-exact functions, so binary == trace one-to-one in
            # length.
    first_user_offset = min(user_real_offsets) if user_real_offsets else None
    call_branch_kinds = {"call_with_args", "branch_jmp", "branch_flag_jcc"}

    # PROOF SOURCE for user-call discrimination: the trace's `cgen_events`
    # record EVERY user cg_ins that flows through GenObjCode (which is the
    # universal per-instruction codegen entry).  Calls emitted via the
    # COMPILER-HELPER path (RTCall -> DoCall -- stack-check probe, prolog
    # hooks, segment fixup) DO NOT call GenObjCode and therefore emit NO
    # `ge` record with opcode=OP_CALL.  So the number of USER calls in
    # this routine == count of cgen_events with opcode in {OP_CALL,
    # OP_CALL_INDIRECT}.  binir's call_with_args ops in EXCESS of that
    # count are proven false-positives (helper calls).
    cgen_events = routine.get("cgen_events", [])
    n_user_calls = sum(1 for e in cgen_events
                       if e.get("opcode") in (INS_OP_CALL, INS_OP_CALL_INDIRECT))

    if user_real_offsets:
        kept_ops = []
        user_calls_seen = 0
        for op in ops:
            if op.kind in call_branch_kinds:
                # For call_with_args: only accept up to n_user_calls of them
                # (in trace/offset order).  Excess ops are helper calls --
                # filtered by PROOF (the trace), not by heuristic.
                if op.kind == "call_with_args":
                    if user_calls_seen < n_user_calls:
                        kept_ops.append(op)
                        user_calls_seen += 1
                    else:
                        result.n_filtered_by_emit_map += 1
                    continue
                # For branches (jmp / jcc-after-flag): accept if not before
                # the first user instruction.
                if first_user_offset is not None and op.offset < first_user_offset:
                    result.n_filtered_by_emit_map += 1
                    continue
                kept_ops.append(op)
                continue
            if op.offset in user_real_offsets:
                kept_ops.append(op)
            else:
                result.n_filtered_by_emit_map += 1
        ops = kept_ops
    result.n_reverse_ops = len(ops)

    # Tally recovery per kind (post-filter).
    for op in ops:
        result.by_kind_recovered[op.kind] = (
            result.by_kind_recovered.get(op.kind, 0) + 1)

    # Per-kind forward count + violation check.
    for kind, n_rev in result.by_kind_recovered.items():
        sig = KIND_SIGNATURES.get(kind)
        if sig is None or sig.predicate is None:
            continue
        n_fwd = _count_forward(forest, sig.predicate)
        result.by_kind_forward_count[kind] = n_fwd
        if n_fwd < n_rev:
            result.violations.append(Violation(
                func=name, file=file, kind=kind,
                note=(f"binir recovered {n_rev} but forward IR has only "
                      f"{n_fwd} matching nodes "
                      f"({sig.description})"),
            ))
    return result


# ── PS.EXE byte slicing (cached) ─────────────────────────────────────────
#
# Both PS.EXE (~600 KB + fixup parsing) and symbols.json are loaded ONCE
# and cached -- per-function loading was multiplying the wall-clock by ~1000x.

@lru_cache(maxsize=1)
def _ps_code_and_index() -> tuple[Optional[bytes], list, dict, int]:
    """Returns (code_bytes, code_syms_sorted, by_name_index, virtual_size).
    All None / empty if PS.EXE or symbols.json is missing."""
    if not (EXE_PATH.exists() and SYM_PATH.exists()):
        return None, [], {}, 0
    syms = json.loads(SYM_PATH.read_text())
    code_syms = sorted([s for s in syms.get("symbols", [])
                        if s.get("is_code")],
                       key=lambda s: s["offset"])
    by_name = {s["name"]: i for i, s in enumerate(code_syms)}
    vsize = syms.get("memory_map", {}).get("objects", [{}])[0].get(
        "virtual_size", 0)
    orig_code, _ = _load_le_code_and_fixups(EXE_PATH)
    return orig_code, code_syms, by_name, vsize


@lru_cache(maxsize=4096)
def _ps_function_insns(name: str) -> tuple[Optional[tuple], int]:
    orig_code, code_syms, by_name, vsize = _ps_code_and_index()
    if orig_code is None:
        return None, 0
    idx = (by_name.get(name) or by_name.get(name + "_")
           or by_name.get(name.rstrip("_")))
    if idx is None:
        return None, 0
    target = code_syms[idx]
    if target.get("size"):
        size = target["size"]
    elif idx + 1 < len(code_syms):
        size = code_syms[idx + 1]["offset"] - target["offset"]
    else:
        size = vsize - target["offset"] if vsize else 200
    ps_bytes = orig_code[target["offset"]: target["offset"] + size]
    return tuple(_disasm_for_diff(ps_bytes)), size


# ── corpus driver ────────────────────────────────────────────────────────

def _iter_corpus_status() -> Iterable[tuple[str, str, bool]]:
    if not VERIFY_CACHE.exists():
        raise FileNotFoundError(
            f"{VERIFY_CACHE} not found; run `c2 decomp-verify --json` first")
    doc = json.loads(VERIFY_CACHE.read_text())
    for f in doc.get("functions", []):
        name = f.get("name")
        file = f.get("file") or ""
        if not name:
            continue
        diff = int(f.get("diff_byte_count", 0) or 0)
        yield name, file, diff == 0


def audit_corpus(*, byte_exact_only: bool = True,
                 limit: Optional[int] = None) -> list[FuncAudit]:
    """Audit every (byte-exact) function in the corpus."""
    rt = regalloc.corpus_trace(SRC_DIR, INCLUDE_DIR)
    results: list[FuncAudit] = []
    seen = 0
    for name, file, ok in _iter_corpus_status():
        if byte_exact_only and not ok:
            continue
        if limit is not None and seen >= limit:
            break
        seen += 1
        results.append(audit_function(name, file, byte_exact=ok, trace=rt))
    return results


def summarize_audit(results: list[FuncAudit]) -> dict:
    by_kind_rev: dict[str, int] = {}
    by_kind_fwd: dict[str, int] = {}
    violations: list[Violation] = []
    n_with_recovery = 0
    n_processed = 0
    n_with_errors = 0
    n_filtered_by_emit_map = 0
    for r in results:
        n_processed += 1
        if r.error:
            n_with_errors += 1
            continue
        if r.n_reverse_ops > 0:
            n_with_recovery += 1
        for k, c in r.by_kind_recovered.items():
            by_kind_rev[k] = by_kind_rev.get(k, 0) + c
        for k, c in r.by_kind_forward_count.items():
            by_kind_fwd[k] = by_kind_fwd.get(k, 0) + c
        n_filtered_by_emit_map += r.n_filtered_by_emit_map
        violations.extend(r.violations)
    return {
        "n_processed": n_processed,
        "n_with_errors": n_with_errors,
        "n_with_recovery": n_with_recovery,
        "n_filtered_by_emit_map": n_filtered_by_emit_map,
        "by_kind_recovered": by_kind_rev,
        "by_kind_forward_count": by_kind_fwd,
        "n_violations": len(violations),
        "violations": violations,
    }


# ── CLI ───────────────────────────────────────────────────────────────────

def binir_audit_cmd(
    limit: Annotated[Optional[int], typer.Option(
        "--limit", help="audit only the first N functions")] = None,
    diffs_too: Annotated[bool, typer.Option(
        "--diffs-too",
        help="include non-byte-exact functions")] = False,
    json_out: Annotated[bool, typer.Option(
        "--json", help="emit JSON summary")] = False,
    show_violations: Annotated[int, typer.Option(
        "--show",
        help="how many per-violation lines to print (sample)")] = 20,
):
    """Corpus-wide structural-soundness audit of binir against the byte-
    exact forward IR.  Zero violations is the required gate when adding
    a new binir pattern; non-zero means a recovered shape disagrees with
    what wcc386 actually emits."""
    results = audit_corpus(byte_exact_only=not diffs_too, limit=limit)
    summary = summarize_audit(results)
    if json_out:
        typer.echo(json.dumps({
            "n_processed": summary["n_processed"],
            "n_with_errors": summary["n_with_errors"],
            "n_with_recovery": summary["n_with_recovery"],
            "n_filtered_by_emit_map": summary["n_filtered_by_emit_map"],
            "by_kind_recovered": summary["by_kind_recovered"],
            "by_kind_forward_count": summary["by_kind_forward_count"],
            "n_violations": summary["n_violations"],
            "violations": [v.__dict__ for v in summary["violations"]],
        }, indent=2))
        if summary["n_violations"] > 0:
            raise typer.Exit(1)
        return

    typer.secho("\n=== binir audit ===", fg="green", bold=True)
    typer.echo(f"  processed: {summary['n_processed']}"
               f"  (with-recovery: {summary['n_with_recovery']}, "
               f"errors: {summary['n_with_errors']})")
    typer.echo(f"  filtered by trace emit-map: "
               f"{summary['n_filtered_by_emit_map']}"
               f"  (binir ops at non-user-code offsets;"
               f" prolog/epilog/compiler-helpers)")
    typer.echo(f"  violations: {summary['n_violations']}")
    typer.echo("\n  by binir-kind:")
    for k in sorted(summary["by_kind_recovered"]):
        rev = summary["by_kind_recovered"][k]
        fwd = summary["by_kind_forward_count"].get(k, "-")
        sig = KIND_SIGNATURES.get(k)
        skipped = sig is None or sig.predicate is None
        if skipped:
            typer.echo(f"    SKIP {k:30s}  rev={rev:5d}  fwd=N/A  "
                       f"(no IR-forest counterpart)")
        else:
            ok = "  OK " if isinstance(fwd, int) and fwd >= rev else "WARN"
            typer.echo(f"    {ok} {k:30s}  rev={rev:5d}  fwd={fwd}")

    if summary["violations"]:
        typer.secho(f"\n  sample of {min(show_violations, len(summary['violations']))} "
                    f"violations (of {len(summary['violations'])} total):",
                    fg="red")
        for v in summary["violations"][:show_violations]:
            typer.echo(f"    {v.func}  ({v.file})  kind={v.kind}")
            if v.note:
                typer.echo(f"      {v.note}")
        raise typer.Exit(1)
