"""Partial IR reconstruction from x86 binary output.

The compiler trace gives us our build's IR forest directly; PS.EXE only gives
us asm.  This module reverse-maps recurrent x86 patterns to the cg_op tree
ops that produced them, so PS.EXE's "missing" IR can be partially recovered
and compared against our build's IR forest -- the differences pinpoint what
SOURCE STRUCTURE PS had that ours doesn't.

Recovered IR is PARTIAL: only patterns that map UNAMBIGUOUSLY to a cg_op
shape are emitted.  Unmatched instructions are PASSED THROUGH (via
:func:`recover_listing`) so consumers see the COMPLETE function flow at IR
level, not just isolated patterns.

Pattern catalog (current):

    R_MOVOP2TEMP shared-divisor idiv pair (Rule 5c FIRED):
        ``mov R, IMM ; <body> ; idiv R ; <body without `mov R, ...`> ; idiv R``
      -> ``OP_DIV(*, R) ; OP_MOD(*, R)`` -- both using SAME R for divisor.

    G_POW2DIV (signed pow2 divide, N>=2):
        ``sar reg, 0x1f ; shl reg, N ; sbb dst, reg ; sar dst, N``
      -> ``OP_DIV(*, 2^N)`` via V_OP2POW2.

    G_DIV2 (signed /2):
        ``sar reg, 0x1f ; sub dst, reg ; sar dst, 1``
      -> ``OP_DIV(*, 2)`` via V_OP2TWO.

    Multiplication strength reduction (very common in array index
    calculations -- get_region_2x2_start's `row * 480` is one example):

      shl reg, N
        -> ``OP_MUL(reg, 2^N)`` (cheapest small multiply form)

      mov reg2, reg ; shl reg, N ; sub reg, reg2  (or add)
        -> ``OP_MUL(reg2, 2^N - 1)`` (or +1)
           Saves 1 byte vs `lea`, used for mul by 3/5/7/9/15/31/...

      lea dst, [src + src * N]   (N in 1,2,4,8)
        -> ``OP_MUL(src, N+1)`` (1+1=2, 2+1=3, 4+1=5, 8+1=9)

      lea dst, [src * N]   (N in 2,4,8)
        -> ``OP_MUL(src, N)``

    Comparison + conditional branch:
      cmp reg, IMM ; j<cond> tgt   -> ``OP_CMP_<cond>(reg, IMM)``
      test reg, reg ; j<cond> tgt  -> ``OP_CMP_<cond>(reg, 0)`` (zero test)
      test reg.lo, reg.lo ; j<cond> tgt -> byte zero test

    Sign / zero extension load:
      movzx reg, byte ptr [m]  -> ``OP_CONVERT_U8_U32(load_byte(m))``
      movzx reg, word ptr [m]  -> ``OP_CONVERT_U16_U32(load_word(m))``
      movsx reg, byte ptr [m]  -> ``OP_CONVERT_S8_S32(load_byte(m))``
      movsx reg, word ptr [m]  -> ``OP_CONVERT_S16_S32(load_word(m))``
      xor reg,reg ; mov reg.lo,[m] -> ``OP_CONVERT_U8_U32`` (Rule 49 zext idiom)

    Memory addressing:
      lea dst, [base + idx * scale + disp]
        -> ``OP_ADDR(base + idx * scale + disp)`` (address calculation)

    Direct memory RMW with constant (Rule 17b signature):
      and/or/xor/add/sub <size> ptr [m], IMM
        -> ``PRE_GETS:O_<binop>(load([m]), IMM)``
           The smoking gun for Rule 17b: the compiler chose the in-place
           RMW optab row instead of split load/op/store.  Source: `X op= IMM`.

    Store constant to memory:
      mov <size> ptr [m], IMM
        -> ``ASSIGN(load([m]), IMM)``
           The most-common "missing" pattern; covers `*p = K` and field
           initialisers.

    Stack call (push args + call [+ esp cleanup]):
      push arg1 ; ... ; push argN ; call FN [; add esp, 4*N]
        -> ``CALL(FN, argc=N)`` (`__cdecl`-style or varargs)

    Branches not part of cmp+jcc:
      jmp imm32                    -> ``GOTO(target)``
      j<cond> imm32 (after flag op) -> ``COND_BRANCH(cond, target)``

The output of :func:`recover` is a list of :class:`RecoveredOp` records, one
per recognised pattern (with the asm offsets it spans).  :func:`recover_listing`
returns the same with passthrough instructions interleaved at their
original offsets, giving a complete IR-level pseudo-listing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


InsnT = tuple[int, int, bytes, str]   # (offset, size, raw, mnemonic+op_str)


@dataclass
class RecoveredOp:
    """One pattern-matched IR signature in the asm."""
    kind: str
    offset: int
    length: int
    detail: dict = field(default_factory=dict)
    op: Optional[str] = None
    note: str = ""


# ── low-level helpers ─────────────────────────────────────────────────────

def _mnem(i: InsnT) -> str:
    return i[3].split(None, 1)[0]


def _opstr(i: InsnT) -> str:
    parts = i[3].split(None, 1)
    return parts[1] if len(parts) > 1 else ""


def _ops(i: InsnT) -> list[str]:
    """Split operand string at commas, stripping whitespace."""
    s = _opstr(i)
    return [t.strip() for t in s.split(",")] if s else []


def _imm(s: str) -> Optional[int]:
    """Parse an immediate operand; returns None if not a number."""
    try:
        return int(s, 0)
    except (ValueError, TypeError):
        return None


# 32-bit reg -> low 8 / low 16 names; used by zext/sign-ext idiom detectors.
_LOW8 = {"eax": "al", "ebx": "bl", "ecx": "cl", "edx": "dl"}
_LOW16 = {"eax": "ax", "ebx": "bx", "ecx": "cx", "edx": "dx",
          "esi": "si", "edi": "di", "ebp": "bp", "esp": "sp"}

_REG32 = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"}


def _is_sar_signbit(i: InsnT) -> bool:
    """sar reg, 31 (the sign-extension prefix to divide-by-pow2 idioms or
    cdq-equivalent before an idiv)."""
    if _mnem(i) != "sar":
        return False
    ops = _ops(i)
    return len(ops) == 2 and ops[1].lower() in {"0x1f", "31"}


def _is_idiv(i: InsnT) -> bool:
    return _mnem(i) in {"idiv", "div"}


def _is_mov_imm(i: InsnT) -> Optional[tuple[str, int]]:
    """mov reg, imm32  ->  (dst, imm)"""
    if _mnem(i) != "mov":
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    val = _imm(ops[1])
    return (ops[0], val) if val is not None else None


def _is_xor_self(i: InsnT) -> Optional[str]:
    if _mnem(i) != "xor":
        return None
    ops = _ops(i)
    return ops[0] if len(ops) == 2 and ops[0] == ops[1] else None


def _is_mov_low(i: InsnT, dst32: str) -> Optional[str]:
    """`mov dst32.lo8, src` (zext-idiom companion); returns the src operand
    when matched."""
    if _mnem(i) != "mov":
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    low = _LOW8.get(dst32.lower())
    if low is None:
        return None
    dst = ops[0].lower()
    # capstone may render as bare "al" or "byte ptr al"; we accept either.
    if dst == low or dst.endswith(" " + low) or dst == "byte ptr " + low:
        return ops[1]
    return None


def _is_movzx_or_movsx_load(i: InsnT) -> Optional[tuple[str, str, str, str]]:
    """movzx/movsx reg, <byte|word> ptr [...]   ->  (mnem, dst, size, mem)"""
    mn = _mnem(i)
    if mn not in {"movzx", "movsx"}:
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    src = ops[1]
    low = src.lower()
    if low.startswith("byte ptr "):
        size = "byte"
        mem = src[len("byte ptr "):]
    elif low.startswith("word ptr "):
        size = "word"
        mem = src[len("word ptr "):]
    else:
        return None
    if "[" not in mem:
        return None
    return (mn, ops[0], size, mem)


def _is_cmp_imm(i: InsnT) -> Optional[tuple[str, int]]:
    """cmp reg, imm  ->  (reg, imm)."""
    if _mnem(i) != "cmp":
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    val = _imm(ops[1])
    return (ops[0], val) if val is not None else None


def _is_test_self(i: InsnT) -> Optional[str]:
    """test reg, reg (zero test)."""
    if _mnem(i) != "test":
        return None
    ops = _ops(i)
    return ops[0] if len(ops) == 2 and ops[0] == ops[1] else None


_JCC = {"jz", "je", "jnz", "jne", "jg", "jge", "jl", "jle",
        "ja", "jae", "jb", "jbe", "js", "jns", "jo", "jno", "jp", "jnp",
        "jcxz", "jecxz"}


def _is_jcc(i: InsnT) -> bool:
    return _mnem(i) in _JCC


def _condcode_to_op(jcc: str) -> str:
    """Map a jcc mnemonic to the cg_op-style comparison name.

    Names align with ``c2.ir.O_CMP_*`` (10.0a-empirical), so the TreeShape
    converter can produce ``COMPARE:O_CMP_EQUAL`` etc. that round-trips
    against the forward-side ``shape_from_node`` naming.
    """
    return {
        "jz":  "O_CMP_EQUAL",       "je":  "O_CMP_EQUAL",
        "jnz": "O_CMP_NOT_EQUAL",   "jne": "O_CMP_NOT_EQUAL",
        "jg":  "O_CMP_GREATER",     "jge": "O_CMP_GREATER_EQUAL",
        "jl":  "O_CMP_LESS",        "jle": "O_CMP_LESS_EQUAL",
        # Unsigned variants don't have a separate cg_op (10.0a uses signed
        # OP_CMP_* + a signed/unsigned type tag in the tipe field); use the
        # same signed name and rely on tipe to disambiguate.  These are
        # functionally equivalent for the binir audit (both fire TN_COMPARE).
        "ja":  "O_CMP_GREATER",     "jae": "O_CMP_GREATER_EQUAL",
        "jb":  "O_CMP_LESS",        "jbe": "O_CMP_LESS_EQUAL",
        # Sign / parity / overflow conditions -- no cg_op counterpart.
        "js":  "O_CMP_SIGN",        "jns": "O_CMP_NSIGN",
        "jo":  "O_CMP_OVF",         "jno": "O_CMP_NOVF",
        "jp":  "O_CMP_PE",          "jnp": "O_CMP_PO",
        "jcxz": "O_CMP_EQZ_CX",     "jecxz": "O_CMP_EQZ_ECX",
    }.get(jcc, "O_CMP_?")


def _is_shl_imm(i: InsnT) -> Optional[tuple[str, int]]:
    """shl reg, IMM  ->  (reg, shift_amount)."""
    if _mnem(i) != "shl":
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    val = _imm(ops[1])
    return (ops[0], val) if val is not None else None


def _is_mov_reg_reg(i: InsnT) -> Optional[tuple[str, str]]:
    """mov dst, src where both are bare registers."""
    if _mnem(i) != "mov":
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    dst, src = ops
    if dst.lower() in _REG32 and src.lower() in _REG32:
        return (dst, src)
    return None


def _is_sub_or_add_reg_reg(i: InsnT) -> Optional[tuple[str, str, str]]:
    """sub/add dst, src where both are bare registers; returns (op, dst, src)."""
    mn = _mnem(i)
    if mn not in {"sub", "add"}:
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    dst, src = ops
    if dst.lower() in _REG32 and src.lower() in _REG32:
        return (mn, dst, src)
    return None


def _is_lea(i: InsnT) -> Optional[tuple[str, str]]:
    """lea dst, [...]  ->  (dst, addr_expr)."""
    if _mnem(i) != "lea":
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    addr = ops[1]
    if not addr.startswith("[") or not addr.endswith("]"):
        return None
    return (ops[0], addr[1:-1].strip())


# mnemonic -> cg_op name used in the recovered op string.  Used by the
# PRE_GETS-style memory-RMW detector AND by ASSIGN(reg, IMM)-equivalent
# patterns that materialise into the same cg_op family.
_ALU_MEM_OP_NAMES = {
    "and": "O_AND",  "or":  "O_OR",   "xor": "O_XOR",
    "add": "O_PLUS", "sub": "O_MINUS",
}


def _strip_size_prefix(s: str) -> tuple[Optional[str], str]:
    """Strip a `byte|word|dword|qword ptr ` prefix; returns (size, rest)."""
    low = s.lower()
    for size in ("byte", "word", "dword", "qword"):
        pre = size + " ptr "
        if low.startswith(pre):
            return size, s[len(pre):]
    return None, s


def _is_alu_mem_imm(i: InsnT) -> Optional[tuple[str, str, str, int]]:
    """`<op> <size> ptr [mem], IMM` for op in {and, or, xor, add, sub}.

    Returns (mnemonic, size, mem_expr, imm).  Specifically REJECTS register
    destinations -- those are NOT direct-memory-RMW (different cg_op tree
    shape: an ASSIGN-with-binop, not a PRE_GETS).
    """
    mn = _mnem(i)
    if mn not in _ALU_MEM_OP_NAMES:
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    dst, src = ops
    size, dst_rest = _strip_size_prefix(dst)
    # No size prefix?  Capstone never elides the size when the dst is
    # memory and the src is an imm whose size is ambiguous -- so absent
    # prefix means dst is almost certainly a register.  Bail out.
    if size is None:
        return None
    if not (dst_rest.startswith("[") and dst_rest.endswith("]")):
        return None
    mem = dst_rest[1:-1].strip()
    imm = _imm(src)
    if imm is None:
        return None
    return (mn, size, mem, imm)


def _is_mov_mem_imm(i: InsnT) -> Optional[tuple[str, str, int]]:
    """`mov <size> ptr [mem], IMM`  ->  (size, mem_expr, imm).

    The companion ASSIGN(LEAF:MEMORY, LEAF:CONSTANT) signature.  As with
    _is_alu_mem_imm, requires an explicit size prefix on the destination
    so we never confuse a register destination for memory.
    """
    if _mnem(i) != "mov":
        return None
    ops = _ops(i)
    if len(ops) != 2:
        return None
    dst, src = ops
    size, dst_rest = _strip_size_prefix(dst)
    if size is None:
        return None
    if not (dst_rest.startswith("[") and dst_rest.endswith("]")):
        return None
    mem = dst_rest[1:-1].strip()
    imm = _imm(src)
    if imm is None:
        return None
    return (size, mem, imm)


# ─── call-with-args & branch helpers ──────────────────────────────────────

# Pushes that are NOT user-call arguments: segment-register pushes
# (`push ds`, `push cs`, ...) are part of __far call helpers; flag-register
# pushes (`pushfd`/`pushf`) belong to interrupt or critical-section
# setups; control-register pushes are kernel-level.
_NON_ARG_PUSH_OPERANDS = {
    "ds", "es", "cs", "ss", "fs", "gs",
    "eflags", "flags",
}


def _is_push(i: InsnT) -> Optional[str]:
    """`push <operand>` where the operand is plausibly a user-call argument.

    Returns the operand string for IMMEDIATE / GP-register / memory pushes;
    returns None for segment-register or flag-register pushes (which belong
    to __far prologue helpers, interrupt frames, etc., NOT to user-level
    argument setup -- treating them as args produces spurious
    ``call_with_args`` recoveries on functions with no source-level calls).
    """
    if _mnem(i) != "push":
        return None
    ops = _ops(i)
    if len(ops) != 1:
        return None
    operand = ops[0]
    if operand.lower() in _NON_ARG_PUSH_OPERANDS:
        return None
    return operand


def _is_call(i: InsnT) -> Optional[str]:
    """`call <tgt>` (any form: imm, reg, mem)."""
    if _mnem(i) != "call":
        return None
    ops = _ops(i)
    return ops[0] if len(ops) == 1 else None


def _is_add_esp(i: InsnT) -> Optional[int]:
    """`add esp, IMM` (the stdcall-style argument cleanup)."""
    if _mnem(i) != "add":
        return None
    ops = _ops(i)
    if len(ops) != 2 or ops[0].lower() != "esp":
        return None
    return _imm(ops[1])


def _is_branch(i: InsnT) -> Optional[tuple[str, str]]:
    """jmp/j<cond> -> (mnem, target).  Excludes cmp+jcc compound (which is
    handled by the cmp_jcc detector with a 2-ins window)."""
    mn = _mnem(i)
    if mn != "jmp" and mn not in _JCC:
        return None
    ops = _ops(i)
    if len(ops) != 1:
        return None
    return (mn, ops[0])


# ── pattern detectors ────────────────────────────────────────────────────

def _parse_target_off(tgt: str) -> Optional[int]:
    """Parse the operand of a branch (`0x12ab`, `0x12ab`, decimal) into a
    function-relative offset.  Returns None on a non-numeric target."""
    s = tgt.strip()
    try:
        if s.lower().startswith("0x"):
            return int(s, 16)
        if all(c in "-0123456789abcdefABCDEF" for c in s):
            return int(s, 16)
    except (ValueError, IndexError):
        return None
    return None


def _detect_loop_rotation_markers(
        insns: list[InsnT]) -> list[RecoveredOp]:
    """Identify Watcom's rotated-loop layout (OW v1 cstmt2.c `for`-clause
    lowering): an unconditional `jmp <forward>` at the loop entry that
    targets a CMP/TEST + Jcc-back at the loop bottom.

    A rotated loop emits THREE landmarks:

      ENTRY:   `jmp <test_off>`  near the top of the function, where
                <test_off> sits FAR DOWN in the function body.
      TEST:    `cmp|test ...` followed by `jcc <body_off>` where
                <body_off> is strictly between ENTRY's offset and the
                TEST's offset (a backward jcc into the body).
      BACK:    the Jcc itself (the rotated loop's only back-edge).

    PS uses this layout for `for ( ; cond; cnt++) { ... }` (empty init
    clause with cond+inc).  RC uses head-tested layout for the
    equivalent `while (cond) { ...; cnt++; }`.  See OW v1
    bld/cc/c/cstmt2.c::ForStmt+EndForStmt vs case T_WHILE end -- the
    FOR's `AddStmt(inc_var)` between body and back-jump is the
    trigger.  Oracle:
    docs/codegen-experiments/loop_rotation_for_vs_while.py.

    Asymmetric presence of `loop_rotation_entry` (PS side only) means
    the source uses `while(... ; cnt++)` and a `for(; ... ; cnt++)`
    rewrite triggers the layout.  CAVEAT: the rewrite also changes
    the inc form from in-place `inc [global]` to cached load-inc-
    store on the same allocator state -- pair with a Rule 72 check.
    """
    out: list[RecoveredOp] = []
    if not insns:
        return out
    fn_end = insns[-1][0] + insns[-1][1]
    # Pre-index instructions by start offset for fast target lookup.
    off_to_idx = {ins[0]: k for k, ins in enumerate(insns)}
    for i, ins in enumerate(insns):
        if _mnem(ins) != "jmp":
            continue
        ops = _ops(ins)
        if len(ops) != 1:
            continue
        tgt_off = _parse_target_off(ops[0])
        if tgt_off is None:
            continue
        src_off = ins[0]
        # forward jmp, target inside the function body, not the trivial
        # "jmp into the next byte" peephole edge case
        if tgt_off <= src_off + ins[1]:
            continue
        if tgt_off >= fn_end:
            continue
        tgt_idx = off_to_idx.get(tgt_off)
        if tgt_idx is None:
            continue
        # The test block can be (cmp|test) on the very target row OR a
        # short load + cmp; allow a 1-2 ins window before the cmp/test.
        cmp_idx = None
        for k in range(0, 3):
            if tgt_idx + k >= len(insns):
                break
            mk = _mnem(insns[tgt_idx + k])
            if mk in ("cmp", "test"):
                cmp_idx = tgt_idx + k
                break
        if cmp_idx is None:
            continue
        # The next instruction after the cmp must be a Jcc whose target
        # is BETWEEN src_off and tgt_off (back-jcc into the body).
        if cmp_idx + 1 >= len(insns):
            continue
        nxt = insns[cmp_idx + 1]
        if _mnem(nxt) not in _JCC:
            continue
        n_ops = _ops(nxt)
        if len(n_ops) != 1:
            continue
        back_off = _parse_target_off(n_ops[0])
        if back_off is None:
            continue
        if not (src_off < back_off < tgt_off):
            continue
        # Emit the three markers in offset order.
        out.append(RecoveredOp(
            kind="loop_rotation_entry",
            offset=src_off, length=ins[1],
            detail={"target": tgt_off, "back": back_off},
            op=f"LOOP_ROT_ENTRY(jmp 0x{tgt_off:x})",
            note=(f"rotated-loop entry: `jmp 0x{tgt_off:x}` skips body to "
                  f"the bottom-tested compare.  Source pattern: "
                  f"`for ( ; cond; cnt++) {{ body }}` (empty init clause "
                  f"with separate inc).  An asymmetric PS-only sighting "
                  f"means our source uses `while (cond) {{...; cnt++;}}` "
                  f"-- rewrite as the for-clause form.  Oracle: "
                  f"docs/codegen-experiments/loop_rotation_for_vs_while.py"),
        ))
        # cmp_idx through cmp_idx+1 form the test+back compound; mark
        # them as the rotated-loop tail.  Use cmp's offset and span the
        # jcc end so the marker covers both.
        cmp_ins = insns[cmp_idx]
        out.append(RecoveredOp(
            kind="loop_rotation_test_back",
            offset=cmp_ins[0],
            length=nxt[0] + nxt[1] - cmp_ins[0],
            detail={"entry": src_off, "body_target": back_off},
            op=f"LOOP_ROT_TEST(cmp; jcc 0x{back_off:x})",
            note=(f"rotated-loop tail: bottom-tested cmp+jcc with back-"
                  f"edge to 0x{back_off:x}.  Pairs with a "
                  f"`loop_rotation_entry` at 0x{src_off:x}."),
        ))
    return out


def _detect_goto_shared_call_markers(
        insns: list[InsnT]) -> list[RecoveredOp]:
    """Identify the goto-to-shared-call layout (Rule 135, devolve_a_building):
    a `ret` that is NOT the function's last instruction, with LATER code
    back-jumping to a target BEFORE the ret -- the arms-below-the-ret shape.

    Markers:

      MID_EPILOGUE:  the mid-function ret (with its epilogue run scanned
                     backward: `pop`s, `add esp, N`).  detail["framed"]
                     records whether the epilogue exceeds CloneCode's
                     5-byte budget (add esp / ret N present) -- framed
                     mid-epilogues are NOT reproducible at OptForSize=50
                     (the position residue is the ~donor class); frameless
                     ones reproduce exactly (19 byte-exact corpus members).
      BACKJUMP_ARM:  each later `jmp` whose target precedes the ret AND
                     whose target region runs into a `call` before the
                     ret -- a `goto do_call;` arm.

    Source recipe (PS-only sighting): put a label on the shared call
    statement inside the FIRST arm, `return;` after the call, and
    `goto <label>;` from every other arm.  The early return also fixes
    the register-seat cascade (the call leaves the cond-chain's linear
    span).  Worked: devolve_a_building 127b -> body exact.
    """
    out: list[RecoveredOp] = []
    if len(insns) < 6:
        return out
    fn_end = insns[-1][0] + insns[-1][1]
    rets = [k for k, ins in enumerate(insns)
            if _mnem(ins).startswith("ret") and k < len(insns) - 2]
    for k in rets:
        ret_ins = insns[k]
        ret_off = ret_ins[0]
        # later back-jumps over the ret
        arms = []
        shared_kinds = set()
        for j in range(k + 1, len(insns)):
            ins = insns[j]
            if _mnem(ins) != "jmp":
                continue
            ops = _ops(ins)
            if len(ops) != 1:
                continue
            tgt = _parse_target_off(ops[0])
            if tgt is None or tgt >= ret_off:
                continue
            # classify the shared region [tgt..ret): a call cluster
            # (goto do_call idiom), a retval setup (goto fail / shared
            # `return CONST`), or a bare tail.
            region = [x for x in insns if tgt <= x[0] < ret_off]
            if any(_mnem(x) == "call" for x in region):
                shared_kinds.add("call")
            elif any(_mnem(x) in ("mov", "xor") and (
                     x[3].startswith("mov eax") or x[3].startswith("mov al")
                     or x[3].startswith("xor eax")) for x in region):
                shared_kinds.add("retval")
            else:
                shared_kinds.add("tail")
            arms.append((j, tgt))
        if not arms:
            continue
        shared = ("call" if "call" in shared_kinds
                  else "retval" if "retval" in shared_kinds else "tail")
        # classify the epilogue run feeding the ret (scan backward)
        epi_start = k
        framed = ret_ins[3].split(None, 1)[1:] != []   # `ret N` form
        while epi_start > 0:
            m = _mnem(insns[epi_start - 1])
            o = insns[epi_start - 1][3]
            if m == "pop":
                epi_start -= 1
            elif m == "add" and "esp" in o:
                framed = True
                epi_start -= 1
            else:
                break
        epi_len = ret_ins[0] + ret_ins[1] - insns[epi_start][0]
        if epi_len > 5:
            framed = True
        recipe = {
            "call": ("the goto-to-shared-call layout (Rule 135): label the "
                     "shared call statement inside the FIRST arm, `return;` "
                     "after it, `goto <label>;` from the other arms "
                     "(worked: devolve_a_building 127b -> body exact)."),
            "retval": ("the `goto fail` shared-return idiom (house style "
                       "5b / Rule 92): the arms `goto` a shared "
                       "`return CONST` inside an earlier arm -- do NOT "
                       "duplicate `return CONST` per guard."),
            "tail": ("a goto into a shared tail before the mid-ret "
                     "(Rule 135 family)."),
        }[shared]
        out.append(RecoveredOp(
            kind="mid_func_epilogue",
            offset=insns[epi_start][0], length=epi_len,
            detail={"framed": framed, "arms": len(arms),
                    "ret_off": ret_off, "shared": shared},
            op=f"MID_EPILOGUE(ret@0x{ret_off:x}, {len(arms)} arm(s))",
            note=("mid-function epilogue+ret with later arms back-jumping "
                  "past it -- " + recipe
                  + ("  FRAMED epilogue (> 5 bytes): the POSITION itself "
                     "is not reproducible at OptForSize=50 (CloneCode "
                     "budget) -- expect the body to verify exact with a "
                     "~donor epilogue-position residue."
                     if framed else
                     "  Frameless epilogue (<= 5 bytes): fully "
                     "reproducible; CloneCode inlines it per return.")),
        ))
        for j, tgt in arms:
            ins = insns[j]
            out.append(RecoveredOp(
                kind="backjump_shared_call",
                offset=ins[0], length=ins[1],
                detail={"target": tgt, "ret_off": ret_off},
                op=f"GOTO_SHARED_CALL(jmp 0x{tgt:x})",
                note=(f"back-jump into the shared region at "
                      f"0x{tgt:x} (before the mid-ret at 0x{ret_off:x}) "
                      f"-- a `goto` arm of the Rule 135/92 shared-tail "
                      f"idiom."),
            ))
    return out


def _detect_r5c_idiv_pair(insns: list[InsnT]) -> list[RecoveredOp]:
    """Two consecutive `idiv R` with NO reload of R between them.  PS
    materialised the divisor once and reused it -- Rule 5c FIRED."""
    out: list[RecoveredOp] = []
    idiv_sites = [(k, _opstr(ins).strip().lower())
                  for k, ins in enumerate(insns) if _is_idiv(ins)]
    for a in range(len(idiv_sites) - 1):
        k1, r1 = idiv_sites[a]
        k2, r2 = idiv_sites[a + 1]
        if r1 != r2:
            continue
        # Scan between k1 and k2 for any reload of r1.
        reloaded = False
        for kk in range(k1 + 1, k2):
            if _mnem(insns[kk]) == "mov":
                ops = _ops(insns[kk])
                if ops and ops[0].lower() == r1:
                    reloaded = True
                    break
        if reloaded:
            continue
        # Find the most-recent `mov r1, IMM` before k1.
        imm = None
        imm_idx = None
        for kk in range(k1 - 1, -1, -1):
            mi = _is_mov_imm(insns[kk])
            if mi is None:
                # If we see r1 redefined by non-imm before reaching the
                # mov, we stop -- the divisor came from elsewhere.
                ops = _ops(insns[kk])
                if ops and ops[0].lower() == r1 and _mnem(insns[kk]) == "mov":
                    break
                continue
            if mi[0].lower() == r1:
                imm, imm_idx = mi[1], kk
                break
        start_idx = imm_idx if imm_idx is not None else k1
        start_off = insns[start_idx][0]
        end_off = insns[k2][0] + insns[k2][1]
        out.append(RecoveredOp(
            kind="r5c_idiv_pair",
            offset=start_off,
            length=end_off - start_off,
            detail={"div_reg": r1, "divisor_imm": imm, "ops": ["MOD", "DIV"]},
            op="OP_MOD/OP_DIV(shared)",
            note=(f"two consecutive `idiv {r1}` with NO reload between them "
                  f"=> Rule 5c FIRED: PS materialised the divisor "
                  f"({imm if imm is not None else 'imm?'}) once and reused "
                  f"it for both `%` and `/`.  Source should keep `/N` and "
                  f"`%N` with the SAME literal; do NOT switch to `>>`."),
        ))
    return out


def _detect_g_pow2div(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """sar reg,31 ; shl reg,N ; sbb dst,reg ; sar dst,N  (N >= 2)."""
    if i + 3 >= len(insns):
        return None
    if not (_is_sar_signbit(insns[i])
            and _mnem(insns[i + 1]) == "shl"
            and _mnem(insns[i + 2]) == "sbb"
            and _mnem(insns[i + 3]) == "sar"):
        return None
    shl_ops = _ops(insns[i + 1])
    if len(shl_ops) != 2:
        return None
    shift = _imm(shl_ops[1])
    if shift is None or shift < 2:
        return None
    sbb_ops = _ops(insns[i + 2])
    if len(sbb_ops) != 2:
        return None
    dst = sbb_ops[0]
    return RecoveredOp(
        kind="g_pow2div",
        offset=insns[i][0],
        length=insns[i + 3][0] + insns[i + 3][1] - insns[i][0],
        detail={"shift": shift, "dst": dst},
        op="OP_DIV(*, 2^N)",
        note=(f"Pow2Div idiom (V_OP2POW2 -> G_POW2DIV): divide-by-{1 << shift} "
              f"strength-reduced.  Source wrote `x / {1 << shift}`."),
    )


def _detect_g_div2(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """sar reg,31 ; sub dst,reg ; sar dst,1."""
    if i + 2 >= len(insns):
        return None
    if not (_is_sar_signbit(insns[i])
            and _mnem(insns[i + 1]) == "sub"
            and _mnem(insns[i + 2]) == "sar"):
        return None
    sar2 = _ops(insns[i + 2])
    if len(sar2) != 2 or sar2[1].lower() not in {"1", "0x1"}:
        return None
    return RecoveredOp(
        kind="g_div2",
        offset=insns[i][0],
        length=insns[i + 2][0] + insns[i + 2][1] - insns[i][0],
        detail={"dst": sar2[0]},
        op="OP_DIV(*, 2)",
        note=("By2Div idiom (V_OP2TWO -> G_DIV2): divide-by-2 "
              "strength-reduced.  Source wrote `x / 2`."),
    )


def _detect_zext_byte_load(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """xor reg,reg ; mov reg.lo, [mem]  (Rule 49 zext byte fetch)."""
    if i + 1 >= len(insns):
        return None
    xreg = _is_xor_self(insns[i])
    if xreg is None or xreg.lower() not in _LOW8:
        return None
    src = _is_mov_low(insns[i + 1], xreg)
    if src is None:
        return None
    src_is_reg = src.lower() in _LOW8.values() or src.lower() in _LOW8
    return RecoveredOp(
        kind="zext_clr_reg" if src_is_reg else "zext_byte_load",
        offset=insns[i][0],
        length=insns[i + 1][0] + insns[i + 1][1] - insns[i][0],
        detail={"reg": xreg, "src": src},
        op="OP_CONVERT_U8_U32(load)",
        note=("xor+mov-low byte zext from a REGISTER (rCLRHI_R disjoint "
              "form): the byte value lives in a NON-A register -- the "
              "AL-squat family's PS-side signature when paired with an "
              "RC-side zext_and_inplace (watcom10.0a docs/"
              "al-squat-family.md)." if src_is_reg else
              "xor+mov-low byte zext idiom: source treats the byte as "
              "`unsigned char` (Rule 49 family)."),
    )


def _detect_zext_copy_and(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """``mov al, <byte reg != al>`` ; ``and eax, 0xff`` -- the re-extend of a
    ROVER-SEATED byte CSE temp into EAX for a call argument (Rule 127,
    battle_action).  PS-side presence vs an RC-side direct AL seat (no mov)
    means PS's source wrote the byte expression TWICE (the optimizer commons
    the loads into a temp that FindRegister rover-seats), while RC named it
    in a local (allocator conflict -> AL) -- write the expression twice."""
    if i + 1 >= len(insns):
        return None
    ins = insns[i]
    if _mnem(ins) != "mov":
        return None
    ops = _ops(ins)
    if len(ops) != 2 or ops[0].lower() != "al":
        return None
    src = ops[1].lower()
    if src == "al" or src not in {"ah", "bl", "bh", "cl", "ch", "dl", "dh"}:
        return None
    nxt = insns[i + 1]
    if _mnem(nxt) != "and":
        return None
    nops = _ops(nxt)
    if len(nops) != 2 or nops[0].lower() != "eax" or nops[1].lower() not in {"0xff", "255"}:
        return None
    return RecoveredOp(
        kind="zext_copy_and",
        offset=ins[0],
        length=nxt[0] + nxt[1] - ins[0],
        detail={"src": src},
        op="OP_CONVERT_U8_U32(copy)",
        note=("mov-al-from-byte-reg + and-0xff re-extend: the byte value is "
              "NOT allocator-AL-seated.  Two known mechanisms: (a) a "
              "ROVER-SEATED CSE temp -- Rule 127, replace the named byte "
              "local with the expression written twice (battle_action "
              "316b->exact); (b) a named byte local re-extended into an "
              "allocator-EAX funnel temp (get_reg_geog family) -- check the "
              "GB line for an EAX conflict with MOV credit before applying "
              "(a)."),
    )


def _detect_zext_and_inplace(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """``and r32, 0xff`` / ``and r32, 0xffff`` -- the rCLRHI_R IN-PLACE
    zero-extend (byte/word value already seated in the register's own low
    part, typically AL/AX).  Same IR op (OP_CONVERT) as zext_byte_load /
    zext_clr_reg -- tree_diff maps all three to the same shape.  An
    RC-side zext_and_inplace vs a PS-side zext_clr_reg on the same line
    is the AL-squat seating divergence, NOT an IR difference."""
    ins = insns[i]
    if _mnem(ins) != "and":
        return None
    ops = _ops(ins)
    if len(ops) != 2 or ops[0].lower() not in _LOW8:
        return None
    imm = ops[1].lower()
    if imm not in {"0xff", "255", "0xffff", "65535"}:
        return None
    wide = imm in {"0xffff", "65535"}
    return RecoveredOp(
        kind="zext_and_inplace",
        offset=ins[0],
        length=ins[1],
        detail={"reg": ops[0], "width": 16 if wide else 8},
        op=f"OP_CONVERT_U{16 if wide else 8}_U32(inplace)",
        note=("and-imm in-place zero-extend (rCLRHI_R overlap form): the "
              "byte/word value is seated in this register's own low part "
              "(AL-squat RC-side signature when PS shows zext_clr_reg)."),
    )


def _ins_writes(ins: InsnT, reg: str) -> bool:
    """Conservative: does ``ins`` plausibly modify ``reg``?

    Used to bound the backward search for a strength-reduction preamble:
    if any instruction between the preamble and the chain CLOBBERS the
    `orig` register, the preamble is invalidated.  We treat any
    instruction whose first operand is ``reg`` (case-insensitive 32-bit
    name) AND whose mnemonic is in a known write-set as a write.
    """
    mn = _mnem(ins)
    if mn not in {"mov", "add", "sub", "xor", "and", "or", "shl", "shr",
                  "sar", "neg", "not", "inc", "dec", "lea", "movzx",
                  "movsx", "imul", "mul", "div", "idiv", "pop", "xchg",
                  "cmovcc"}:
        return False
    ops = _ops(ins)
    if not ops:
        return False
    return ops[0].lower() == reg.lower()


def _detect_mul_chain_extended(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """Recognise OW v1 CheckMul-style strength-reduction chains of ANY length.

    Source of truth: watcom 10.0a binary ``CheckMul@0x61c32`` (RE'd in
    watcom10.0a knowledge/wcc386_regalloc.py).  Per the OW v1
    ``bld/cg/c/multiply.c CheckMul``, every recognised OP_MUL with a
    profitable constant rhs is rewritten into:

        MOV  rA, rB                     # MakeMove(operands[0]=rB, orig=rA)
        [chain on rB, with rA as the consistent add/sub source]:
            SHL  rB, k                  # Ops[j]=DO_SHL  k   -> mul *= 2^k
            ADD  rB, rA                 # Ops[j]=DO_ADD      -> mul += 1
            SUB  rB, rA                 # Ops[j]=DO_SUB      -> mul -= 1
            MOV  rB, rA                 # Ops[j]=DO_XFR      -> orig = temp
        [NEG  rB]                       # only when rhs<0 was passed

    The leading MOV preserves operands[0] (the original) into ``rA``;
    after this preamble, ``rB`` IS the chain target (because OW's
    ``MakeMove(orig=rA, temp=rB)`` is regalloc-eliminated when ``temp``
    landed in the same hw_reg as ``operands[0]``).

    Anchoring: we anchor on the CHAIN, not the preamble, because regalloc
    can interleave UNRELATED moves between the preservation mov and the
    chain (e.g. `mov esi, edx` between `mov ecx, edx` and `shl edx, 2`).
    The anchor instruction must be a chain op (shl/add/sub) that uses a
    consistent (rA, rB).  Then we look forward to extend the chain, and
    BACKWARD to verify a preceding `mov rA, rB` whose `rA` has NOT been
    clobbered by intervening instructions.

    Reverse simulation: start ``multiplier = 1`` (since the loop entry
    state is ``rB == rA * 1`` -- the temp was just seeded from orig).
    Walk the chain; each op transforms multiplier as above.  ``DO_XFR``
    (``mov rB, rA``) corresponds to ``orig = temp`` in OW source -- so
    subsequent ADD/SUB use the CURRENT temp value (we set multiplier=1
    AND set a flag that future +/- delta is relative to the prior
    multiplier).  Since strength reduction is usually 2 or 3 ops, full
    XFR-aware simulation is rare; the simple "multiplier += {1, -1, 2^k}"
    rule below captures the common cases.

    Yields ONE ``mul_const`` op covering the chain (NOT the preamble --
    the preamble bytes may be far away and are claimed by their own
    pattern).  Must run BEFORE ``_detect_mul_strength`` so the 3-ins
    compound (mul_strength) and bare-shl (mul_pow2) detectors don't
    fire inside the chain.
    """
    n = len(insns)
    if i + 1 >= n:
        return None
    # Anchor: either a leading preservation mov, or the first shl/add/sub
    # of the chain.  Determine candidate (rA, rB) and the chain-start
    # index ``chain_start``.
    cur = insns[i]
    rA = rB = None
    chain_start = i
    preamble_offset = None
    preamble_length = 0
    mv0 = _is_mov_reg_reg(cur)
    sh = _is_shl_imm(cur)
    aop = _is_sub_or_add_reg_reg(cur)
    if mv0 is not None and i + 1 < n:
        # Possible preservation mov.  The chain starts at i+1; determine
        # rA/rB from the FIRST chain op.
        mv_dst, mv_src = mv0
        if mv_dst.lower() == mv_src.lower():
            return None
        nxt = insns[i + 1]
        nxt_sh = _is_shl_imm(nxt)
        nxt_aop = _is_sub_or_add_reg_reg(nxt)
        # Chain target must be one of the mov's registers.
        if nxt_sh is not None and nxt_sh[0].lower() in (mv_dst.lower(), mv_src.lower()):
            rB = nxt_sh[0]
            rA = mv_src if rB.lower() == mv_dst.lower() else mv_dst
        elif nxt_aop is not None:
            op_mn, dst, src = nxt_aop
            if dst.lower() in (mv_dst.lower(), mv_src.lower()) and src.lower() in (mv_dst.lower(), mv_src.lower()):
                rB = dst
                rA = src
        else:
            return None
        if rA is None or rB is None or rA.lower() == rB.lower():
            return None
        preamble_offset = cur[0]
        preamble_length = cur[1]
        chain_start = i + 1
    elif sh is not None:
        rB = sh[0]
    elif aop is not None:
        op_mn, dst, src = aop
        rB = dst
        rA = src
        if dst.lower() == src.lower():
            return None
    else:
        return None
    if rB not in _REG32:
        return None
    if rA is not None and rA not in _REG32:
        return None

    # Walk forward to extend the chain.  Track ops on rB; use add/sub src
    # to lock-in rA on the first add/sub we see.
    multiplier = 1
    chain_end = chain_start    # exclusive
    n_arith = 0
    n_shl = 0
    n_xfr = 0
    j = chain_start
    while j < n:
        ins = insns[j]
        sh2 = _is_shl_imm(ins)
        if sh2 is not None and sh2[0].lower() == rB.lower():
            multiplier *= (1 << sh2[1])
            chain_end = j + 1
            n_shl += 1
            n_arith += 1
            j += 1
            continue
        aop2 = _is_sub_or_add_reg_reg(ins)
        if (aop2 is not None
                and aop2[1].lower() == rB.lower()):
            # Lock-in rA on first add/sub if not already known.
            if rA is None:
                rA = aop2[2]
                if rA.lower() == rB.lower():
                    return None
            elif aop2[2].lower() != rA.lower():
                break
            multiplier += 1 if aop2[0] == "add" else -1
            chain_end = j + 1
            n_arith += 1
            j += 1
            continue
        mvx = _is_mov_reg_reg(ins)
        if (mvx is not None
                and mvx[0].lower() == rB.lower()
                and rA is not None
                and mvx[1].lower() == rA.lower()):
            # DO_XFR -- mov temp, orig => orig was promoted; future
            # +/- becomes relative to the just-promoted value.  For
            # the common 2-3 op chains in practice this rarely fires;
            # we keep the simple "reset multiplier=1" semantics so the
            # detector at least lands on the right offset.
            multiplier = 1
            chain_end = j + 1
            n_xfr += 1
            j += 1
            continue
        break
    chain_len = chain_end - chain_start
    # Need a non-trivial chain (3+ arith ops) AND a confirmed `rA`.
    if rA is None:
        return None
    if n_arith < 3:
        return None
    # If we anchored on a leading mov, the preamble is already confirmed.
    if preamble_offset is not None:
        found_preamble = True
    else:
        found_preamble = False
    # Backward scan for the OW v1 CheckMul preamble.  Per multiply.c, two
    # MakeMove instructions are emitted in sequence:
    #   (1) ``MakeMove(operands[0], orig)``   ->  mov orig_reg, op0_reg
    #   (2) ``MakeMove(orig,        temp)``   ->  mov temp_reg, orig_reg
    # Regalloc may collapse one or both of these.  Either single mov that
    # survives is a `mov X, Y` where ``{X, Y} == {rA, rB}`` (i.e. either
    # mov direction is valid -- they are the SAME register swap pair).
    # That covers both observed in-the-wild orientations:
    #   * ``mov rA, rB``  (preservation; mov #1 survived, mov #2 eliminated
    #                     because temp_reg coincided with op0_reg = rB)
    #   * ``mov rB, rA``  (seeding; mov #2 survived as `mov temp_reg=rB,
    #                     orig_reg=rA`, mov #1 eliminated because orig_reg
    #                     coincided with op0_reg = rA)
    # Allow up to 8 intervening instructions, none of which may clobber
    # either rA OR rB.
    BACK_BUDGET = 8
    if not found_preamble:
      for k in range(chain_start - 1, max(-1, chain_start - 1 - BACK_BUDGET), -1):
        ins = insns[k]
        mv = _is_mov_reg_reg(ins)
        if mv is not None:
            x, y = mv[0].lower(), mv[1].lower()
            if {x, y} == {rA.lower(), rB.lower()}:
                found_preamble = True
                # Extend the recovered-op offset window to cover the
                # preamble (so the existing 3-ins `mul_strength` detector
                # doesn't fire at the preamble byte after our op claims
                # the chain bytes).
                preamble_offset = ins[0]
                preamble_length = ins[1]
                break
        # Any other write to rA or rB invalidates the preamble.
        if _ins_writes(ins, rA) or _ins_writes(ins, rB):
            break
    if not found_preamble:
        return None
    # Optional trailing NEG rB (single-operand) -- the OW source's neg-flag tail.
    negated = False
    if chain_end < n:
        ins = insns[chain_end]
        if _mnem(ins) == "neg":
            ops = _ops(ins)
            if len(ops) == 1 and ops[0].lower() == rB.lower():
                negated = True
                chain_end += 1
                multiplier = -multiplier
    # Span: from preamble (if adjacent) to chain end; the greedy recover
    # loop uses ``offset`` + ``length`` to skip past matched bytes.
    if preamble_offset is not None:
        start_off = preamble_offset
    else:
        start_off = insns[chain_start][0]
    end_off = insns[chain_end - 1][0] + insns[chain_end - 1][1]
    detail = {
        "result": rB, "base": rA,
        "factor": multiplier,
        "chain_insns": chain_len,
        "n_shl": n_shl,
        "n_xfr": n_xfr,
        "negated": negated,
    }
    return RecoveredOp(
        kind="mul_const",
        offset=start_off,
        length=end_off - start_off,
        detail=detail,
        op=f"OP_MUL({rB}, {multiplier})",
        note=(f"strength-reduced multiply: {rB} = {rA}_orig * {multiplier} "
              f"via {chain_len}-instruction shl/add/sub chain "
              f"(OW v1 CheckMul/Factor expansion of Ops[]@0x806e4 in "
              f"watcom 10.0a binary)."),
    )


def _detect_mul_strength(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """Recognise mul-by-constant strength reductions:

       1) mov tmp, reg ; shl reg, N ; sub reg, tmp     -> reg = reg_orig * (2^N - 1)
       2) mov tmp, reg ; shl reg, N ; add reg, tmp     -> reg = reg_orig * (2^N + 1)
       3) shl reg, N                                   -> reg *= 2^N  (only when the
                                                          next ins is NOT one of (1)/(2))
       4) lea dst, [src + src * K]    K in {1,2,4,8}   -> dst = src * (K+1)
       5) lea dst, [src * K]          K in {2,4,8}     -> dst = src * K
    """
    n = len(insns)
    # (4) and (5) -- lea-based, single-instruction.
    lea = _is_lea(insns[i])
    if lea is not None:
        dst, expr = lea
        # Normalise spaces for matching.
        e = expr.replace(" ", "").lower()
        # `src + src*K`
        import re as _re
        m = _re.fullmatch(r"([a-z]{2,3})\+\1\*([1248])", e)
        if m:
            src = m.group(1)
            k = int(m.group(2))
            return RecoveredOp(
                kind="mul_lea_scaled_self",
                offset=insns[i][0], length=insns[i][1],
                detail={"dst": dst, "src": src, "factor": k + 1},
                op=f"OP_MUL({src}, {k + 1})",
                note=(f"strength-reduced multiply by {k + 1} via "
                      f"`lea {dst}, [{src} + {src}*{k}]`."),
            )
        m = _re.fullmatch(r"([a-z]{2,3})\*([248])", e)
        if m:
            src = m.group(1)
            k = int(m.group(2))
            return RecoveredOp(
                kind="mul_lea_scaled",
                offset=insns[i][0], length=insns[i][1],
                detail={"dst": dst, "src": src, "factor": k},
                op=f"OP_MUL({src}, {k})",
                note=(f"strength-reduced multiply by {k} via "
                      f"`lea {dst}, [{src}*{k}]`."),
            )
    # (1) and (2) -- the mov+shl+sub|add pattern.  Two equivalent register
    # orderings produce the same factor -- both must be recognised:
    #
    #   Pattern A: ``mov copy, orig ; shl copy, N ; (sub|add) copy, orig``
    #              -> copy = orig * (2^N ∓ 1).  Result in COPY register.
    #
    #   Pattern B: ``mov copy, orig ; shl orig, N ; (sub|add) orig, copy``
    #              -> orig = orig * (2^N ∓ 1).  Result in ORIG register.
    #
    # Both are 7 bytes; the choice depends on regalloc.  PS frequently
    # picks Pattern B (shift the live reg, save the copy elsewhere) when
    # other code already saved into the copy register.
    if i + 2 < n:
        mv = _is_mov_reg_reg(insns[i])
        sh = _is_shl_imm(insns[i + 1])
        aop = _is_sub_or_add_reg_reg(insns[i + 2])
        if mv is not None and sh is not None and aop is not None:
            mv_dst, mv_src = mv
            sh_reg, sh_amt = sh
            op_mn, su_dst, su_src = aop
            if sh_amt >= 1 and mv_dst.lower() != mv_src.lower():
                # Pattern A: shift the copy, sub the original.
                if (sh_reg.lower() == mv_dst.lower()
                        and su_dst.lower() == mv_dst.lower()
                        and su_src.lower() == mv_src.lower()):
                    return _mk_mul_compound(
                        insns, i, op_mn, sh_amt,
                        result=mv_dst, orig=mv_src,
                        pattern="A: shl copy ; sub copy, orig")
                # Pattern B: shift the original, sub the copy.
                if (sh_reg.lower() == mv_src.lower()
                        and su_dst.lower() == mv_src.lower()
                        and su_src.lower() == mv_dst.lower()):
                    return _mk_mul_compound(
                        insns, i, op_mn, sh_amt,
                        result=mv_src, orig=mv_src,
                        pattern="B: shl orig ; sub orig, copy")
    # (3) -- bare shl with imm.  Only emit if NOT part of the (1)/(2) compound.
    sh = _is_shl_imm(insns[i])
    if sh is not None and sh[1] >= 1:
        reg, amt = sh
        # Look back ONE ins for the matching mov, look forward ONE for the
        # matching sub/add (in both Pattern A and B orderings).
        is_part_of_compound = False
        if i > 0 and i + 1 < n:
            mv = _is_mov_reg_reg(insns[i - 1])
            aop = _is_sub_or_add_reg_reg(insns[i + 1])
            if mv is not None and aop is not None:
                mv_dst, mv_src = mv
                op_mn, su_dst, su_src = aop
                # Pattern A: shl operates on mv_dst (the copy).
                if (reg.lower() == mv_dst.lower()
                        and su_dst.lower() == mv_dst.lower()
                        and su_src.lower() == mv_src.lower()):
                    is_part_of_compound = True
                # Pattern B: shl operates on mv_src (the original).
                elif (reg.lower() == mv_src.lower()
                        and su_dst.lower() == mv_src.lower()
                        and su_src.lower() == mv_dst.lower()):
                    is_part_of_compound = True
        if is_part_of_compound:
            return None
        return RecoveredOp(
            kind="mul_pow2",
            offset=insns[i][0], length=insns[i][1],
            detail={"reg": reg, "shift": amt, "factor": 1 << amt},
            op=f"OP_MUL({reg}, {1 << amt})",
            note=(f"multiply by {1 << amt} via `shl {reg}, {amt}` "
                  f"(pow2 multiply)."),
        )
    return None


def _mk_mul_compound(insns: list[InsnT], i: int, op_mn: str, sh_amt: int,
                    *, result: str, orig: str, pattern: str) -> RecoveredOp:
    """Build a RecoveredOp for the mov+shl+(sub|add) compound multiply."""
    factor = (1 << sh_amt) + (-1 if op_mn == "sub" else +1)
    end_off = insns[i + 2][0] + insns[i + 2][1]
    return RecoveredOp(
        kind=("mul_const_minus_one" if op_mn == "sub"
              else "mul_const_plus_one"),
        offset=insns[i][0],
        length=end_off - insns[i][0],
        detail={"dst": result, "src": orig, "shift": sh_amt,
                "op": op_mn, "factor": factor, "pattern": pattern},
        op=f"OP_MUL({orig}, {factor})",
        note=(f"strength-reduced multiply by {factor} (pattern {pattern}): "
              f"3-ins compound, result in {result}."),
    )


def _detect_cmp_jcc(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """cmp reg, IMM ; jcc tgt   or   test reg, reg ; jcc tgt."""
    if i + 1 >= len(insns):
        return None
    nxt = insns[i + 1]
    if not _is_jcc(nxt):
        return None
    cmpi = _is_cmp_imm(insns[i])
    if cmpi is not None:
        reg, imm = cmpi
        return RecoveredOp(
            kind="cmp_jcc",
            offset=insns[i][0],
            length=nxt[0] + nxt[1] - insns[i][0],
            detail={"reg": reg, "imm": imm, "jcc": _mnem(nxt),
                    "tgt": _opstr(nxt)},
            op=f"OP_{_condcode_to_op(_mnem(nxt))}({reg}, {imm})",
            note=(f"comparison + conditional branch: source wrote "
                  f"`if ({reg} <cond> {imm}) ...`."),
        )
    zreg = _is_test_self(insns[i])
    if zreg is not None:
        return RecoveredOp(
            kind="zero_test_jcc",
            offset=insns[i][0],
            length=nxt[0] + nxt[1] - insns[i][0],
            detail={"reg": zreg, "jcc": _mnem(nxt), "tgt": _opstr(nxt)},
            op=f"OP_{_condcode_to_op(_mnem(nxt))}({zreg}, 0)",
            note=(f"zero-test + conditional branch: source wrote "
                  f"`if ({zreg}) ...` or `if (!{zreg}) ...`."),
        )
    return None


def _detect_pre_gets_mem_const(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """`<binop> <size> ptr [mem], IMM` -- direct-memory-RMW with constant.

    Maps to a ``PRE_GETS:O_<NAME>`` tree shape -- this is the smoking gun
    for Rule 17b (the optab row that READS, MODIFIES, and WRITES memory
    in one instruction, with no intermediate temp).  Source-side: the
    user wrote ``X op= MASK;`` and the compiler chose the in-place RMW
    optab row instead of split load/op/store.
    """
    m = _is_alu_mem_imm(insns[i])
    if m is None:
        return None
    mn, size, mem, imm = m
    cg = _ALU_MEM_OP_NAMES[mn]
    return RecoveredOp(
        kind="pre_gets_mem_const",
        offset=insns[i][0],
        length=insns[i][1],
        detail={"binop": mn, "cg_op": cg, "size": size,
                "mem": mem, "imm": imm},
        op=f"PRE_GETS:{cg}([{mem}], {imm:#x})",
        note=(f"direct-memory-RMW with constant: source wrote "
              f"`*[{mem}] {mn}= {imm:#x};` (or equivalent) and the "
              f"compiler chose the in-place {mn}-with-{size}-mem optab "
              f"row -- Rule 17b territory."),
    )


def _detect_mem_sum_chain(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """An n-term memory sum assigned to memory: ``g = a + b + ... + z``.

    Rule 130 (LdStAlloc/LdStCompress, grounded in 10.0a CompressIns
    @0x62e16 == owp4v1 i86ldstr.c): every term is RISCified post-alloc and
    merged BACK only when the partner mov is adjacent and the guards pass.
    Three deterministic surface forms for the SAME IR (probe sum.c):

      merged term:    ``add acc, [mem]``
      acc-swap split: ``mov r2, [mem]`` ; ``add r2, acc``   (acc := r2)
      last-term split:``mov r2, [mem]`` ; ``add acc, r2``
                      (the FINAL addend always splits: the result store
                      engages CompressIns' presult path and
                      ``*popnd != *presult`` aborts the merge)

    ended by ``mov [dst], acc``.  All decode to ONE statement:
    ASSIGN(dst, O_PLUS chain over n memory leaves) -- a one-line source
    expression, NOT a ``+=`` chain (those show RMW ``add [g],r`` forms).
    """
    regs32 = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}

    def _mem_src(op: str) -> bool:
        op = op.strip()
        if op.startswith(("dword ptr [", "word ptr [", "byte ptr [")):
            return True
        return op.startswith("[") and op.endswith("]")

    ins = insns[i]
    if _mnem(ins) != "mov":
        return None
    ops = _ops(ins)
    if len(ops) != 2 or ops[0].lower() not in regs32 or not _mem_src(ops[1]):
        return None
    acc = ops[0].lower()
    n_terms = 1
    j = i + 1
    while j < len(insns):
        t = insns[j]
        m, o = _mnem(t), _ops(t)
        if m == "add" and len(o) == 2 and o[0].lower() == acc and _mem_src(o[1]):
            n_terms += 1
            j += 1
            continue
        if (m == "mov" and len(o) == 2 and o[0].lower() in regs32
                and o[0].lower() != acc and _mem_src(o[1])
                and j + 1 < len(insns)):
            r2 = o[0].lower()
            m2, o2 = _mnem(insns[j + 1]), _ops(insns[j + 1])
            if m2 == "add" and len(o2) == 2:
                a, b = o2[0].lower(), o2[1].lower()
                if a == r2 and b == acc:        # acc-swap split
                    acc = r2
                    n_terms += 1
                    j += 2
                    continue
                if a == acc and b == r2:        # last-term split
                    n_terms += 1
                    j += 2
                    continue
        break
    if n_terms < 2 or j >= len(insns):
        return None
    end = insns[j]
    eo = _ops(end)
    if (_mnem(end) != "mov" or len(eo) != 2
            or not eo[0].strip().endswith("]") or eo[1].lower() != acc):
        return None
    return RecoveredOp(
        kind="mem_sum_chain",
        offset=ins[0],
        length=end[0] + end[1] - ins[0],
        detail={"n": n_terms, "acc": acc},
        op=f"ASSIGN(MEM, O_PLUS\u00d7{n_terms - 1})",
        note=(f"{n_terms}-term memory sum stored to memory: ONE source "
              f"statement `g = m1 + ... + m{n_terms};` (Rule 130).  The "
              "split mov+add term(s) are CompressIns declines (last addend "
              "always; acc-swaps), NOT separate statements; a `+=` chain "
              "would show RMW `add [g],reg` stores instead.  Same shape on "
              "the other side but different term count = different "
              "expression grouping; RMW forms on the other side = it used "
              "`+=` statements."),
    )


_CTO_ALU = {"add": "O_PLUS", "sub": "O_MINUS", "and": "O_AND", "or": "O_OR",
            "xor": "O_XOR", "shl": "O_LSHIFT", "sar": "O_RSHIFT",
            "shr": "O_RSHIFT", "imul": "O_TIMES"}


def _detect_copy_then_op(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """Value-preserving copy before a two-address ALU op (Rule 132).

    ``mov rT, rS`` ; ``<alu> rT, X``   (rT != rS, both registers)

    decodes to the SAME single statement as the in-place form
    ``<alu> rS, X`` -- the copy is NOT a source statement.  wcc386 always
    reduces ``dst = a <op> b`` via a result temp (OW v1 split.c
    rMOVOP1RES / rUSEREGISTER); the prefix ``mov`` SURVIVES register
    allocation iff the left operand's value is STILL LIVE past the
    statement (oracle: docs/codegen-experiments/copy_then_op_liveness.py
    -- even a bare ``return a;`` keeps it).  A side that shows the copy
    has a LATER USE of the left value in its source; a side that does
    the op in-place consumed it.  This is a liveness lever, not
    restructuring noise.
    """
    regs32 = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}
    ins = insns[i]
    if _mnem(ins) != "mov" or i + 1 >= len(insns):
        return None
    ops = _ops(ins)
    if (len(ops) != 2 or ops[0].lower() not in regs32
            or ops[1].lower() not in regs32
            or ops[0].lower() == ops[1].lower()):
        return None
    rt, rs = ops[0].lower(), ops[1].lower()
    nxt = insns[i + 1]
    mn = _mnem(nxt)
    if mn not in _CTO_ALU:
        return None
    no = _ops(nxt)
    if len(no) != 2 or no[0].lower() != rt:
        return None
    x = no[1].strip()
    if x.lower() == rt:
        return None
    if mn in ("sar", "shr") and x.lower() in ("0x1f", "31"):
        return None     # sign/zero-extend idiom (cdq replacement), not a stmt
    cg = _CTO_ALU[mn]
    return RecoveredOp(
        kind="copy_then_op",
        offset=ins[0],
        length=nxt[0] + nxt[1] - ins[0],
        detail={"dst": rt, "src": rs, "binop": mn, "rhs": x},
        op=f"ASSIGN({rt}, {cg}({rs}, {x}))",
        note=(f"copy-then-{mn}: ONE statement `t = {rs} {mn} {x}` with the "
              f"value in {rs} KEPT LIVE past it (Rule 132): this side's "
              f"source READS that value again later (second use / return / "
              f"cached var).  An in-place `{mn} {rs}, {x}` on the other "
              f"side means the other source CONSUMED it.  Find/remove the "
              f"later use -- do not restructure this statement."),
    )


def _detect_const_store_run(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """A RUN of >=2 constant stores of the SAME value, in either lowering:

    reg form:   ``xor r,r`` (or ``mov r, IMM``) ; ``mov [m1], r`` ; ``mov [m2], r`` ...
    imm form:   ``mov <size> [m1], K`` ; ``mov <size> [m2], K`` ...

    The FORM is the Rule 128 observable (ptr-local vs direct indexing):
    Watcom RISCifies const->mem stores ONLY when the destination is
    N_INDEXED with a symbol base or plain N_MEMORY (i86ldstr.c Enregister;
    `if (result->i.base == NULL) break;`).  A pointer-local access
    (`p->f = K`) has base==NULL -> stays imm form; direct `arr[i].f = K`
    folds the array base into the displacement -> reg form with one
    shared register for the whole run.  A PS reg-run vs RC imm-run on the
    same line = replace the pointer local with direct indexing (and vice
    versa).  Probe: docs/codegen-experiments/ptr_local_vs_direct_indexing.py."""
    ins = insns[i]
    regs32 = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}
    # --- reg form: xor r,r / mov r,imm then >=2 stores of r
    src_reg = _is_xor_self(ins)
    value = 0 if src_reg else None
    if src_reg is None and _mnem(ins) == "mov":
        ops = _ops(ins)
        if len(ops) == 2 and ops[0].lower() in regs32:
            try:
                value = int(ops[1], 0)
                src_reg = ops[0].lower()
            except ValueError:
                pass
    if src_reg is not None and src_reg.lower() in regs32:
        src_reg = src_reg.lower()
        n = 0
        j = i + 1
        last = ins
        while j < len(insns):
            t = _ops(insns[j])
            if (_mnem(insns[j]) == "mov" and len(t) == 2
                    and t[1].lower() == src_reg
                    and "[" in t[0]):
                n += 1
                last = insns[j]
                j += 1
                continue
            break
        if n >= 2:
            return RecoveredOp(
                kind="const_store_run_reg",
                offset=ins[0],
                length=last[0] + last[1] - ins[0],
                detail={"form": "reg", "n": n, "value": value,
                        "reg": src_reg},
                op=f"ASSIGN(MEM, {value:#x})*{n}" if value is not None
                   else f"ASSIGN(MEM, ?)*{n}",
                note=(f"{n} stores of one constant through register "
                      f"{src_reg} (Enregister REG form): the destinations "
                      "are symbol-based (direct indexing / globals).  If "
                      "the other side shows the IMM form on this line, "
                      "Rule 128: IT uses a pointer local -- switch form."),
            )
    # --- imm form: >=2 size-prefixed imm stores of the same value
    m0 = _is_mov_mem_imm(ins)
    if m0 is None:
        return None
    size0, _mem0, imm0 = m0
    n = 1
    j = i + 1
    last = ins
    while j < len(insns):
        m = _is_mov_mem_imm(insns[j])
        if m is None or m[2] != imm0:
            break
        n += 1
        last = insns[j]
        j += 1
    if n < 2:
        return None
    return RecoveredOp(
        kind="const_store_run_imm",
        offset=ins[0],
        length=last[0] + last[1] - ins[0],
        detail={"form": "imm", "n": n, "value": imm0},
        op=f"ASSIGN(MEM, {imm0:#x})*{n}",
        note=(f"{n} immediate-form stores of {imm0:#x} (Enregister "
              "SKIPPED -- destination has no symbol base): the access is "
              "through a POINTER LOCAL (`p->f = K`).  If the other side "
              "shows the REG form (xor/mov reg + reg stores) on this "
              "line, Rule 128: replace `struct X *p = &arr[i]; p->f=K;` "
              "with direct `arr[i].f = K;` statements."),
    )


def _detect_ptr_base_materialize(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """The `&arr[i]` pointer-local materialization (Rule 128 companion):

    shape 1:  ``mov r32, IMM`` ; (<=1 filler) ; ``add r32, r32``
    shape 2:  ``add r32, IMM``  directly after index arithmetic
              (imul/shl/sub/add) on the same register.

    In a relocatable .obj the IMM prints as 0 (fixup); in PS it is the
    linked array base.  Presence on ONE side only = that side hoists
    `&arr[i]` into a pointer local; the other folds the base into each
    access displacement (direct indexing)."""
    ins = insns[i]
    if _mnem(ins) != "mov" and _mnem(ins) != "add":
        return None
    ops = _ops(ins)
    regs32 = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}
    if len(ops) != 2 or ops[0].lower() not in regs32:
        return None
    try:
        imm = int(ops[1], 0)
    except ValueError:
        return None
    if imm != 0 and imm < 0x10000:
        return None
    r = ops[0].lower()
    if _mnem(ins) == "mov":
        # shape 1: mov r, base ; [filler] ; add r, idxreg
        for j in (i + 1, i + 2):
            if j >= len(insns):
                break
            t = _ops(insns[j])
            if (_mnem(insns[j]) == "add" and len(t) == 2
                    and t[0].lower() == r and t[1].lower() in regs32):
                return RecoveredOp(
                    kind="ptr_base_materialize",
                    offset=ins[0],
                    length=insns[j][0] + insns[j][1] - ins[0],
                    detail={"reg": r, "shape": "mov+add"},
                    op="LA(&arr[i])",
                    note=("array base materialized into a register "
                          "(`mov r,ARR; add r,idx`): a POINTER LOCAL "
                          "holds &arr[i].  If the other side indexes "
                          "with the base folded into displacements "
                          "(fixup per access), Rule 128 applies."),
                )
        return None
    # shape 2: add r, base after index arithmetic on r
    if i == 0:
        return None
    prev = insns[i - 1]
    if _mnem(prev) not in {"imul", "shl", "sub", "add", "lea"}:
        return None
    pops = _ops(prev)
    if not pops or pops[0].lower() != r:
        return None
    return RecoveredOp(
        kind="ptr_base_materialize",
        offset=ins[0],
        length=ins[1],
        detail={"reg": r, "shape": "add-base"},
        op="LA(&arr[i])",
        note=("array base added onto the scaled index (`add r, ARR` "
              "after index math): a POINTER LOCAL holds &arr[i] "
              "(Rule 128; see const_store_run form note)."),
    )


def _detect_mov_mem_imm(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """`mov <size> ptr [mem], IMM` -- store a constant to memory.

    Maps to ``ASSIGN(LEAF:MEMORY, LEAF:CONSTANT)`` -- the most common
    "missing" pattern on the reverse side.  Adding this collapses many
    `only_in_a` chatter diffs that would otherwise dominate tree-diff
    output on functions that just initialise fields.
    """
    m = _is_mov_mem_imm(insns[i])
    if m is None:
        return None
    size, mem, imm = m
    return RecoveredOp(
        kind="mov_mem_imm",
        offset=insns[i][0],
        length=insns[i][1],
        detail={"size": size, "mem": mem, "imm": imm},
        op=f"ASSIGN([{mem}], {imm:#x})",
        note=(f"store constant {imm:#x} to {size} ptr [{mem}]: source "
              f"wrote `*[{mem}] = {imm:#x};` (direct memory assignment "
              f"of a constant)."),
    )


def _detect_call_with_args(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """Stack-call sequence: `push arg ; ... ; call tgt [; add esp, N]`.

    Recognises the C-style call ABI (stack-passed args, optional cleanup).
    Watcom defaults to __watcall (register passing), so a push-arg
    sequence followed by a call is the SIGNATURE of a __cdecl-converted
    function or a printf-style varargs.  Maps to a CALL tree with PARM
    children (one per pushed argument).

    Filtering compiler-emitted helper calls (stack-check probe at function
    entry, register-save-then-unrelated-call sequences in __watcall code)
    is the JOB OF THE PARSER / AUDIT VIA THE TRACE OFFSET MAP, NOT this
    matcher.  binir stays structural; the trace tells us which offsets
    are user-IR vs synthetic.  See c2.commands.binir_audit for the
    offset-driven filter.

    The matcher ITSELF rejects only:
      * zero-push calls (no preceding pushes -- nothing to recover)
      * pushes that aren't plausible arguments (segment registers, etc. --
        see :func:`_is_push`).  These are NEVER user-code idioms, regardless
        of the function context.
    """
    n = len(insns)
    if i >= n:
        return None
    cur = insns[i]
    if _is_call(cur) is None:
        return None
    pushes: list[tuple[int, str]] = []
    j = i - 1
    while j >= 0:
        p = _is_push(insns[j])
        if p is None:
            break
        pushes.append((j, p))
        j -= 1
    if not pushes:
        return None
    pushes.reverse()
    start_idx = pushes[0][0]
    end_idx = i
    cleanup_imm: Optional[int] = None
    if i + 1 < n:
        amt = _is_add_esp(insns[i + 1])
        if amt is not None and amt == 4 * len(pushes):
            cleanup_imm = amt
            end_idx = i + 1
    target = _is_call(cur)
    end_off = insns[end_idx][0] + insns[end_idx][1]
    return RecoveredOp(
        kind="call_with_args",
        offset=insns[start_idx][0],
        length=end_off - insns[start_idx][0],
        detail={"target": target, "argc": len(pushes),
                "args": [p[1] for p in pushes],
                "cleanup": cleanup_imm},
        op=f"CALL({target}, argc={len(pushes)})",
        note=(f"{len(pushes)}-arg stack call to {target}"
              + (f" (cleanup: add esp, {cleanup_imm})"
                 if cleanup_imm is not None else "")
              + ".  Source-side: `__cdecl`-style call or varargs."),
    )


def _detect_branch_simple(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """Bare branch (`jmp tgt` or `j<cond> tgt`) that is NOT part of a
    cmp+jcc compound.  The cmp_jcc detector handles the compound case
    with higher priority; this catches:

      * unconditional `jmp imm32` (loop edges, goto, switch tail)
      * `j<cond>` after a flag-setting arithmetic op (add/sub/sar/dec/...)
        that didn't emit an explicit `cmp` -- a frequent shape after
        loop counter dec.

    Maps to a synthetic ``BRANCH:<mnem>`` tree shape; the diff aligns
    on the branch position rather than treating it as raw asm.
    """
    cur = insns[i]
    br = _is_branch(cur)
    if br is None:
        return None
    mn, tgt = br
    # If a jcc is immediately preceded by cmp or test, the cmp_jcc detector
    # owns the compound when the cmp operand is an immediate (or test is a
    # self-test).  If neither matched, the comparison is "real" (cmp reg/reg,
    # test reg1/reg2) but still NOT a bare flag-set + branch -- pass through
    # rather than mislabelling.
    if mn in _JCC and i > 0:
        prev_mn = _mnem(insns[i - 1])
        if prev_mn in {"cmp", "test"}:
            return None
    detail = {"mnem": mn, "target": tgt}
    if mn == "jmp":
        return RecoveredOp(
            kind="branch_jmp",
            offset=cur[0], length=cur[1],
            detail=detail,
            op=f"GOTO({tgt})",
            note=(f"unconditional branch to {tgt}: source `goto`, "
                  f"loop back-edge, or switch tail."),
        )
    return RecoveredOp(
        kind="branch_flag_jcc",
        offset=cur[0], length=cur[1],
        detail=detail,
        op=f"COND_BRANCH({_condcode_to_op(mn)}, {tgt})",
        note=(f"`{mn} {tgt}` after a flag-setting op (no explicit cmp): "
              f"the preceding arithmetic op set the flags, source likely "
              f"`if (--ctr) ...` or `if (X - Y) ...` pattern."),
    )


_EXIT_MNEMS = {"ret", "jmp", "pop", "leave"}


def _detect_farptr_ret_const(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """Far-pointer return constant (Rule 85): the EDX:EAX pair loaded with
    immediates right before an exit.

      xor edx, edx | mov edx, SEG
      mov eax, OFF
      <ret | jmp epilogue | pop ...>

    Decodes the EXACT source expression: ``return (char __far *)OFF;``
    when SEG == 0, else ``return (char __far *)MK_FP(SEG, OFF);``
    (<i86.h>) -- oracle-proven on Watcom 10.0a (pcsound start_sequences:
    only MK_FP(1,2) produces `mov edx,1; mov eax,2`).  The seg write can
    be VALUE-POOL ELIDED when a preceding `test reg,reg` proved the
    register zero (start_samples' `return 2` after `int s = ...;
    if (s == 0)`) -- that variant shows as a bare mov_eax_imm and is NOT
    detected here.  PS pushes/pops EDX in far*-returning functions
    anyway (10.0a quirk; callers discard the seg half), so do NOT use
    the push set to rule far* out.  See Rule 85 in
    docs/watcom-codegen-patterns.md.
    """
    if i + 1 >= len(insns):
        return None
    a, b = insns[i], insns[i + 1]
    seg: Optional[int] = None
    if _mnem(a) == "xor":
        ops = _ops(a)
        if len(ops) == 2 and ops[0] == "edx" and ops[1] == "edx":
            seg = 0
    elif _mnem(a) == "mov":
        ops = _ops(a)
        if len(ops) == 2 and ops[0] == "edx":
            seg = _imm(ops[1])
    if seg is None:
        return None
    if _mnem(b) != "mov":
        return None
    ops_b = _ops(b)
    if len(ops_b) != 2 or ops_b[0] != "eax":
        return None
    off = _imm(ops_b[1])
    if off is None:
        return None
    # Segments are 16-bit and error-code far-ptr constants are small;
    # this also kills the watcall tail-call false positive
    # (`mov edx,<global>; mov eax,<arg>; jmp callee`).
    if seg > 0xFFFF or off > 0xFFFF:
        return None
    # Require an exit-shaped next instruction so plain arg-setup
    # (xor edx,edx before a call) never fires.
    if i + 2 < len(insns) and _mnem(insns[i + 2]) not in _EXIT_MNEMS:
        return None
    # Classify by what follows.  Local pops ending in `ret` = certainly a
    # far-ptr RETURN.  A `jmp` is ambiguous WITHIN the function: corpus
    # census (2026-06-10, 65 sites in PS.EXE) splits 5 returns (the
    # pcsound Rule 85 family, jmp → epilogue-stub chain ending in pops+
    # ret) vs 58 ARG-PAIR merges (jmp → a SHARED CALL TAIL: ComTail
    # merged identical call sites; the pair is the callee's (eax,edx)
    # watcall args -- get_census/get_new_tribute/show_* UI panels).
    # decomp-verify resolves the jmp through symbols and upgrades the
    # verdict (tail_merge.classify_regpair_exit).
    j = i + 2
    while j < len(insns) and _mnem(insns[j]) == "pop":
        j += 1
    follower = _mnem(insns[j]) if j < len(insns) else "ret"
    jmp_target = None
    if follower == "jmp":
        jmp_target = _imm(_ops(insns[j])[0]) if _ops(insns[j]) else None
    src = (f"return (char __far *){off:#x};" if seg == 0 else
           f"return (char __far *)MK_FP({seg:#x}, {off:#x});  /* <i86.h> */")
    if follower == "ret":
        return RecoveredOp(
            kind="farptr_ret_const",
            offset=a[0],
            length=(b[0] + b[1]) - a[0],
            detail={"seg": seg, "off": off},
            op=f"RETURN_FARPTR(MK_FP({seg:#x}, {off:#x}))",
            note=(f"Rule 85 far-ptr return constant -- source is literally "
                  f"`{src}`  (function returns char __far *; needs a "
                  f"prototype before any caller or E1062)."),
        )
    return RecoveredOp(
        kind="regpair_const_exit",
        offset=a[0],
        length=(b[0] + b[1]) - a[0],
        detail={"seg": seg, "off": off, "jmp_target": jmp_target},
        op=f"REGPAIR_EXIT(edx={seg:#x}, eax={off:#x})",
        note=(f"EDX:EAX constant pair at an exit jmp -- EITHER a Rule 85 "
              f"far-ptr return through an epilogue-stub chain (source: "
              f"`{src}`) OR (eax,edx) watcall ARGS into a ComTail-merged "
              f"SHARED CALL TAIL (identical call sites factored out; RC "
              f"needs the same call shape at every merged site).  Follow "
              f"the jmp: pops+ret = return; call = args."),
    )


def _detect_signzext_load(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """movzx/movsx reg, byte|word ptr [mem]."""
    m = _is_movzx_or_movsx_load(insns[i])
    if m is None:
        return None
    mn, dst, size, mem = m
    signed = mn == "movsx"
    op_name = ("OP_CONVERT_S" if signed else "OP_CONVERT_U") + (
        "8_S32" if size == "byte" and signed else
        "16_S32" if size == "word" and signed else
        "8_U32" if size == "byte" else "16_U32")
    return RecoveredOp(
        kind=("signext_load_" + size) if signed
              else ("zext_load_" + size),
        offset=insns[i][0],
        length=insns[i][1],
        detail={"dst": dst, "size": size, "src": mem, "signed": signed},
        op=op_name + f"(load([{mem}]))",
        note=(f"{'signed' if signed else 'unsigned'} {size}-load + extend "
              f"to 32-bit: source treats `[{mem}]` as "
              f"`{'signed' if signed else 'unsigned'} {size}`."),
    )


# ── top-level recovery ───────────────────────────────────────────────────

_PASS2: list = [
    _detect_g_pow2div,           # 4-ins window
    _detect_mul_chain_extended,  # variable window: mov + N×{shl|add|sub|xfr}[+neg]
    _detect_mul_strength,        # 1-3 ins (lea, shl, or mov+shl+sub)
    _detect_g_div2,           # 3-ins window
    _detect_zext_byte_load,   # 2-ins window (also emits zext_clr_reg)
    _detect_farptr_ret_const, # 2-ins window (must run BEFORE mov_mem_imm/branch)
    _detect_cmp_jcc,          # 2-ins window  (must run BEFORE branch_simple)
    _detect_zext_copy_and,    # 2-ins window (must run BEFORE zext_and_inplace)
    _detect_zext_and_inplace, # 1-ins (and r32, 0xff/0xffff)
    _detect_call_with_args,   # variable window: pushes...+call[+add esp]
    _detect_mem_sum_chain,       # variable window (mov r,[m] + add chain + store)
    _detect_copy_then_op,        # 2-ins window (mov rT,rS + alu rT,X; Rule 132)
    _detect_const_store_run,     # variable window (BEFORE mov_mem_imm; claims runs)
    _detect_ptr_base_materialize,  # 1-3 ins (mov+add / add-base)
    _detect_pre_gets_mem_const,  # 1-ins (size-prefixed memory dst only)
    _detect_mov_mem_imm,         # 1-ins (size-prefixed memory dst only)
    _detect_signzext_load,    # 1-ins
    _detect_branch_simple,    # 1-ins (bare jmp/jcc; cmp_jcc claims compounds)
]


def recover(insns: list[InsnT]) -> list[RecoveredOp]:
    """Reverse-engineer recognised patterns from a function's asm.

    Returns a list of :class:`RecoveredOp` in asm order.  Patterns are
    non-overlapping (greedy from low offset; longer windows tried first).
    """
    n = len(insns)
    out: list[RecoveredOp] = []
    # Pass 1: locate idiv pairs (spans dozens of insns, can't be greedy).
    out.extend(_detect_r5c_idiv_pair(insns))
    # Pass 1b: function-level loop-rotation markers (non-overlapping with
    # local-pattern detectors -- the entry is a bare `jmp` and the test
    # is a `cmp+jcc` compound that cmp_jcc would also claim; we let
    # cmp_jcc claim those bytes in PASS2 and add rotation markers as
    # SEPARATE entries here so the kind tally surfaces the rotation
    # without disturbing the byte coverage map).
    rotation_markers = _detect_loop_rotation_markers(insns)
    rotation_markers.extend(_detect_goto_shared_call_markers(insns))
    claimed = [(o.offset, o.offset + o.length) for o in out]
    # Pass 2: greedy sequential patterns (must not overlap pass-1 claims).
    i = 0
    while i < n:
        ofs = insns[i][0]
        owner = next((c for c in claimed if c[0] <= ofs < c[1]), None)
        if owner is not None:
            while i < n and insns[i][0] < owner[1]:
                i += 1
            continue
        matched = None
        for det in _PASS2:
            r = det(i, insns)
            if r is not None:
                matched = r
                break
        if matched is not None:
            out.append(matched)
            # Advance past the match (count insns covered by length).
            ofs_end = matched.offset + matched.length
            while i < n and insns[i][0] < ofs_end:
                i += 1
        else:
            i += 1
    # Add rotation markers AFTER pass 2 so they don't suppress local
    # patterns (cmp_jcc, branch_jmp).  They are tagged as 'tags' --
    # multiple ops can occupy the same offset.
    out.extend(rotation_markers)
    out.sort(key=lambda r: (r.offset, r.length))
    return out


def summarize(ops: list[RecoveredOp]) -> dict[str, int]:
    import collections
    return dict(collections.Counter(o.kind for o in ops))


# ── readable pseudo-listing ──────────────────────────────────────────────

def render_listing(insns: list[InsnT],
                   ops: Optional[list[RecoveredOp]] = None,
                   *, prefix: str = "  ") -> list[str]:
    """Render a complete IR-pseudo-listing for ``insns``, interleaving
    recovered ops with passthrough instructions.  Recognised patterns are
    shown as a single condensed line; unmatched instructions render as
    plain asm with a `?` prefix.

    Output is suited for direct printing alongside the asm diff.
    """
    if ops is None:
        ops = recover(insns)
    ops = sorted(ops, key=lambda r: r.offset)
    # Build offset->op for quick covered-range checks.
    covered: dict[int, RecoveredOp] = {}
    cover_ends: list[int] = []
    for op in ops:
        covered[op.offset] = op
        cover_ends.append(op.offset + op.length)

    def _covered_by(off: int) -> Optional[RecoveredOp]:
        for op in ops:
            if op.offset <= off < op.offset + op.length:
                return op
        return None

    lines: list[str] = []
    skip_until: int = -1
    for ins in insns:
        off = ins[0]
        if off < skip_until:
            continue
        op = covered.get(off)
        if op is not None:
            lines.append(
                f"{prefix}+{op.offset:#06x}  ![{op.kind:20s}] {op.op or '-':<28} "
                f"-- {op.note.splitlines()[0] if op.note else ''}")
            skip_until = op.offset + op.length
            continue
        if _covered_by(off) is not None:
            continue
        lines.append(f"{prefix}+{off:#06x}  {ins[3]}")
    return lines
