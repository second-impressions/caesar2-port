"""Infer function signatures from disassembly.

For a `__watcall`-convention function, infer:
  * Number of register parameters (EAX, EDX, EBX, ECX read-before-write).
  * Number of stack parameters (`[esp+N]` reads with N >= 4).
  * Whether the function returns a value (EAX written before some RET).
  * Callee-save register set (PUSH in prologue, POP in epilogue).

Output format::

    inferred sig: int f(eax, edx)        ← reg args, has return
    inferred sig: void f(void)            ← no args, no return
    inferred sig: int f(eax, edx, [esp+8])← reg+stack mix, has return

This is a HEURISTIC — it's accurate for normal Watcom-emitted code
but doesn't handle:
  * Functions that read a callee-save (ESI/EDI/EBP) before saving
    (rare, would imply a non-standard convention).
  * Pseudo-args passed via globals (very common in PS.EXE — caller
    sets a global, callee reads it).  These won't be detected.
  * EAX writes that are dead (e.g., zeroed only as a side-effect).

Usage::

    uv run c2 inferred-sig figure_images
    uv run c2 inferred-sig 0x4FA48
    uv run c2 inferred-sig --all                # scan whole binary
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from c2.commands.disasm import disasm_function, DisasmLine

# Registers and their sub-register aliases.
_REG_ALIASES: dict[str, frozenset[str]] = {
    "eax": frozenset({"eax", "ax", "al", "ah"}),
    "edx": frozenset({"edx", "dx", "dl", "dh"}),
    "ebx": frozenset({"ebx", "bx", "bl", "bh"}),
    "ecx": frozenset({"ecx", "cx", "cl", "ch"}),
    "esi": frozenset({"esi", "si"}),
    "edi": frozenset({"edi", "di"}),
    "ebp": frozenset({"ebp", "bp"}),
}

# Reverse map: any sub-register → its canonical 32-bit form.
_CANONICAL: dict[str, str] = {
    sub: canon for canon, subs in _REG_ALIASES.items() for sub in subs
}

# Order in which __watcall passes register args.
_ARG_REGS = ("eax", "edx", "ebx", "ecx")


@dataclass
class InferredSig:
    name: str
    address: int
    size: int
    arg_regs: list[str] = field(default_factory=list)
    """Register-passed args, in order: e.g. ['eax', 'edx']."""
    stack_args: list[int] = field(default_factory=list)
    """Stack-arg offsets (relative to ESP at entry, after pushes)."""
    has_return: bool = False
    """True if EAX is written before some RET path (likely returns int)."""
    return_size: int = 0
    """1 if AL written; 2 if AX; 4 if EAX; 0 if no return."""
    callee_saves: list[str] = field(default_factory=list)
    """Registers pushed in prologue and popped in epilogue."""
    leaks_call_eax: bool = False
    """True if every RET path has `call X` as its last EAX-touching
    instruction (no explicit EAX write between the call and ret).
    When set, EAX at ret is whatever the trailing call left — usually
    garbage for void callees.  Caller-side "EAX use" evidence is
    UNRELIABLE in this case (callers may be inheriting EAX through
    chains of void-tail-call returns) and should NOT promote the
    function to has_return."""

    def render(self, *, ret_type: str = "int", void_type: str = "void") -> str:
        """Render a C-style signature using the inferred info."""
        ret = ret_type if self.has_return else void_type
        if self.return_size == 1 and self.has_return:
            ret = "char"
        elif self.return_size == 2 and self.has_return:
            ret = "short"
        if not self.arg_regs and not self.stack_args:
            args = "void"
        else:
            parts = list(self.arg_regs)
            for off in self.stack_args:
                parts.append(f"[esp+{off:#x}]")
            args = ", ".join(parts)
        return f"{ret} {self.name}({args})"


# ── Parsing helpers ──────────────────────────────────────────


_REG_OP_RE = re.compile(
    r"\b(e?(?:ax|bx|cx|dx|si|di|bp)|[abcd][hl]|[abcd]x)\b", re.IGNORECASE
)


def _operand_regs(op_str: str) -> list[str]:
    """Return all 32-bit canonical regs referenced anywhere in op_str."""
    out = []
    for m in _REG_OP_RE.finditer(op_str.lower()):
        canon = _CANONICAL.get(m.group(1))
        if canon and canon not in out:
            out.append(canon)
    return out


def _esp_offsets(op_str: str) -> list[int]:
    """Return all `[esp + N]` numeric offsets in op_str."""
    out = []
    for m in re.finditer(
        r"\[\s*esp\s*([+\-]\s*0?x?[0-9a-fA-F]+)?\s*\]", op_str.lower()
    ):
        offset_text = (m.group(1) or "+0").replace(" ", "")
        try:
            out.append(int(offset_text, 0))
        except ValueError:
            pass
    return out


def _classify(line: DisasmLine) -> tuple[set[str], set[str], list[int]]:
    """Return (regs_read, regs_written, stack_reads_at_offset).

    Approximation based on x86 mnemonics.  For most simple ALU ops the
    first operand is read+written, the rest are read.  ``mov`` writes
    its first operand and reads the rest.  Pushes read; pops write.
    """
    mnemonic = line.mnemonic.lower()
    op_str = line.op_str

    # Split ops by top-level commas (we don't worry about nested parens
    # since x86 op_str doesn't have any).
    if op_str.strip():
        ops = [s.strip() for s in op_str.split(",")]
    else:
        ops = []

    read: set[str] = set()
    written: set[str] = set()
    stack_reads: list[int] = []

    if mnemonic in ("mov", "movzx", "movsx", "lea"):
        if ops:
            # First operand is destination (written); subsequent regs in
            # mem operands of the destination are read (e.g., [eax + 4]).
            dst = ops[0]
            dst_regs = _operand_regs(dst)
            if "[" in dst:
                # Memory destination — base/index regs are read, content
                # is written but we model it as stack write only if it's
                # ESP-based.
                read.update(dst_regs)
            elif dst_regs:
                written.add(dst_regs[0])
            for src in ops[1:]:
                read.update(_operand_regs(src))
                stack_reads.extend(_esp_offsets(src))
    elif mnemonic in (
        "add", "sub", "and", "or", "xor", "imul", "shl", "shr", "sar",
        "rol", "ror", "rcl", "rcr", "neg", "not", "inc", "dec",
        "test", "cmp", "adc", "sbb",
    ):
        if mnemonic in ("test", "cmp"):
            # Both operands read.
            for op in ops:
                read.update(_operand_regs(op))
                stack_reads.extend(_esp_offsets(op))
        elif mnemonic == "imul" and len(ops) == 3:
            # 3-operand IMUL: dst = src1 * src2.  Destination is
            # WRITE-ONLY (no read of dst); other two are read.
            dst = ops[0]
            dst_regs = _operand_regs(dst)
            if dst_regs and "[" not in dst:
                written.add(dst_regs[0])
            elif dst_regs:
                read.update(dst_regs)
            for src in ops[1:]:
                read.update(_operand_regs(src))
                stack_reads.extend(_esp_offsets(src))
        elif ops:
            dst = ops[0]
            dst_regs = _operand_regs(dst)
            # First operand is read+written; subsequent are read.
            if "[" in dst:
                read.update(dst_regs)
            else:
                read.update(dst_regs)
                if dst_regs:
                    written.add(dst_regs[0])
            for src in ops[1:]:
                read.update(_operand_regs(src))
                stack_reads.extend(_esp_offsets(src))
            # XOR reg, reg with same operands is a write-only zero.
            if (
                mnemonic == "xor"
                and len(ops) >= 2
                and ops[0].lower() == ops[1].lower()
            ):
                read.discard(_CANONICAL.get(ops[0].lower(), "")) if dst_regs else None
                if dst_regs:
                    read.discard(dst_regs[0])
    elif mnemonic == "push":
        for op in ops:
            read.update(_operand_regs(op))
            stack_reads.extend(_esp_offsets(op))
    elif mnemonic == "pop":
        if ops:
            dst_regs = _operand_regs(ops[0])
            if dst_regs:
                written.add(dst_regs[0])
    elif mnemonic.startswith("set") and len(mnemonic) <= 5:
        # setne/sete/setl/etc. — write the byte register operand.
        # For arg-detection purposes we treat the parent 32-bit
        # register as written (the typical idiom is `setX al; and
        # eax, 0xff` to zero-extend, and we want EAX flagged as
        # written-here so the AND doesn't see EAX as live-in).
        if ops:
            dst_regs = _operand_regs(ops[0])
            if dst_regs:
                written.add(dst_regs[0])
    elif mnemonic in ("idiv", "div", "mul"):
        # IDIV/DIV: reads EDX:EAX and arg, writes both.
        # IMUL (1-op): reads EAX and arg, writes EDX:EAX.
        for op in ops:
            read.update(_operand_regs(op))
        read.add("eax")
        if mnemonic in ("idiv", "div"):
            read.add("edx")
        written.add("eax")
        written.add("edx")
    elif mnemonic in ("cdq", "cwd"):
        read.add("eax")
        written.add("edx")
    elif mnemonic in ("cdqe", "cwde", "cbw"):
        # Sign-extend within the accumulator family.  These do not
        # clobber EDX; marking EDX written hides later DX arg reads
        # (e.g. position_mouse(short x, short y)).
        read.add("eax")
        written.add("eax")
    elif mnemonic in ("call",):
        # Call clobbers caller-saves (eax, edx, ecx) by default __watcall.
        written.add("eax")
        written.add("edx")
        written.add("ecx")
        # We don't know the args without recursing — assume worst case:
        # eax/edx/ebx/ecx are READ as args.  But that would mark every
        # call site as reading all 4, defeating the analysis.  Instead
        # we assume the caller already set up args and simply track
        # post-call clobbers.
    # ret / jmp / branches: nothing to track (no register writes).
    return read, written, stack_reads


# ── Byte-granular register lanes ─────────────────────────────
#
# The plain ``_classify`` view above is 32-bit-granular, which loses the
# fact that `xor ah, ah` clears only the high byte of EAX while a later
# `xor ah, al` still reads AL (an incoming 8-bit parameter).  For
# precise calling-convention inference we track three lanes per
# canonical register:
#
#   LANE_LO  (1) = bits  0..7   (al / bl / ...)
#   LANE_HI  (2) = bits  8..15  (ah / bh / ...)
#   LANE_UP  (4) = bits 16..31  (upper half of e?x)
#
# A 32-bit operand touches all three (mask 7); a 16-bit operand the low
# two (3); an 8-bit low operand just LANE_LO (1); an 8-bit high operand
# just LANE_HI (2).  Memory base/index registers are always full 32-bit
# reads.
LANE_LO, LANE_HI, LANE_UP = 1, 2, 4
LANE_FULL = LANE_LO | LANE_HI | LANE_UP  # 7

_BYTE_LO_REGS = frozenset({"al", "bl", "cl", "dl"})
_BYTE_HI_REGS = frozenset({"ah", "bh", "ch", "dh"})
_WORD_REGS = frozenset({"ax", "bx", "cx", "dx", "si", "di", "bp"})


def _token_lane(tok: str) -> Optional[tuple[str, int]]:
    """Map a single register token to ``(canonical_reg, lane_mask)``."""
    sub = tok.strip().lower()
    canon = _CANONICAL.get(sub)
    if canon is None:
        return None
    if sub in _BYTE_LO_REGS:
        return canon, LANE_LO
    if sub in _BYTE_HI_REGS:
        return canon, LANE_HI
    if sub in _WORD_REGS:
        return canon, LANE_LO | LANE_HI
    return canon, LANE_FULL


def _operand_lane_reads(op: str) -> dict[str, int]:
    """Lane masks for every register mentioned in an operand.

    For a memory operand (`[eax + ebx*4]`) the base/index registers are
    full 32-bit reads; ``_token_lane`` already returns the right mask for
    each token because address registers are always spelled 32-bit.
    """
    out: dict[str, int] = {}
    for m in _REG_OP_RE.finditer(op.lower()):
        lane = _token_lane(m.group(1))
        if lane is not None:
            out[lane[0]] = out.get(lane[0], 0) | lane[1]
    return out


def _merge_lane(d: dict[str, int], reg: str, mask: int) -> None:
    if mask:
        d[reg] = d.get(reg, 0) | mask


def _classify_lanes(
    line: DisasmLine,
) -> tuple[dict[str, int], dict[str, int], list[int]]:
    """Byte-granular ``(reads, writes, stack_reads)`` for one instruction.

    ``reads`` / ``writes`` map a canonical register to the union of lane
    bits it reads / writes.  Mirrors ``_classify``'s operand-role logic
    but at lane granularity so partial writes (`mov al, x`, `xor ah, ah`)
    do not falsely kill the rest of the register.  ``call`` is left to
    the liveness builder, which models the callee's CallZap.
    """
    mnemonic = line.mnemonic.lower()
    op_str = line.op_str
    ops = [s.strip() for s in op_str.split(",")] if op_str.strip() else []
    reads: dict[str, int] = {}
    writes: dict[str, int] = {}
    stack_reads: list[int] = []

    def read_operand(op: str) -> None:
        for reg, mask in _operand_lane_reads(op).items():
            _merge_lane(reads, reg, mask)
        stack_reads.extend(_esp_offsets(op))

    if mnemonic in ("mov", "movzx", "movsx", "lea"):
        if ops:
            dst = ops[0]
            if "[" in dst:
                read_operand(dst)  # memory dst: base/index are reads
            else:
                lane = _token_lane(dst)
                if lane is not None:
                    # movzx/movsx fully define the 32-bit destination
                    # (zero/sign extension); plain mov/lea write only the
                    # destination's own width.
                    wmask = LANE_FULL if mnemonic in ("movzx", "movsx") else lane[1]
                    _merge_lane(writes, lane[0], wmask)
            for src in ops[1:]:
                read_operand(src)
    elif mnemonic in ("test", "cmp"):
        for op in ops:
            read_operand(op)
    elif mnemonic == "imul" and len(ops) == 3:
        dst = ops[0]
        if "[" in dst:
            read_operand(dst)
        else:
            lane = _token_lane(dst)
            if lane is not None:
                _merge_lane(writes, lane[0], LANE_FULL)
        for src in ops[1:]:
            read_operand(src)
    elif mnemonic in (
        "add", "sub", "and", "or", "xor", "imul", "shl", "shr", "sar",
        "rol", "ror", "rcl", "rcr", "neg", "not", "inc", "dec",
        "adc", "sbb",
    ):
        if ops:
            dst = ops[0]
            self_zero = (
                mnemonic == "xor"
                and len(ops) >= 2
                and ops[0].lower() == ops[1].lower()
            )
            # `and reg, imm` is the canonical zero-extend / mask idiom
            # (`mov al, [m]; and eax, 0xff`).  A byte of the destination
            # is only READ where the immediate byte is non-zero; bytes
            # masked to 0 are written, not read, so they must not look
            # live-in.  Handle it lane-precisely.
            and_imm_lanes = None
            if (
                mnemonic == "and"
                and "[" not in dst
                and len(ops) == 2
                and not _operand_lane_reads(ops[1])  # src is an immediate
            ):
                try:
                    imm = int(ops[1].strip(), 0)
                except ValueError:
                    imm = None
                if imm is not None:
                    kept = 0
                    if imm & 0x000000FF:
                        kept |= LANE_LO
                    if imm & 0x0000FF00:
                        kept |= LANE_HI
                    if imm & 0xFFFF0000:
                        kept |= LANE_UP
                    and_imm_lanes = kept
            if "[" in dst:
                read_operand(dst)
            else:
                lane = _token_lane(dst)
                if lane is not None:
                    _merge_lane(writes, lane[0], lane[1])
                    if and_imm_lanes is not None:
                        # Only the kept (non-zero-mask) lanes are read.
                        _merge_lane(reads, lane[0], and_imm_lanes & lane[1])
                    elif not self_zero:
                        _merge_lane(reads, lane[0], lane[1])
            if and_imm_lanes is None:
                for src in ops[1:]:
                    read_operand(src)
            if self_zero and "[" not in dst:
                lane = _token_lane(dst)
                if lane is not None and reads.get(lane[0]):
                    # `xor r, r` is write-only; drop the spurious read.
                    reads[lane[0]] &= ~lane[1]
                    if not reads[lane[0]]:
                        del reads[lane[0]]
    elif mnemonic == "push":
        for op in ops:
            read_operand(op)
    elif mnemonic == "pop":
        if ops:
            lane = _token_lane(ops[0])
            if lane is not None:
                _merge_lane(writes, lane[0], lane[1])
    elif mnemonic.startswith("set") and len(mnemonic) <= 5:
        # setcc writes a byte register; treat as a full define (the idiom
        # `xor eax,eax; setne al` or `setne al; and eax,0xff` always
        # establishes the upper bytes), which keeps EAX from looking
        # live-in here.
        if ops:
            lane = _token_lane(ops[0])
            if lane is not None:
                _merge_lane(writes, lane[0], LANE_FULL)
    elif mnemonic in ("idiv", "div", "mul"):
        for op in ops:
            read_operand(op)
        _merge_lane(reads, "eax", LANE_FULL)
        if mnemonic in ("idiv", "div"):
            _merge_lane(reads, "edx", LANE_FULL)
        _merge_lane(writes, "eax", LANE_FULL)
        _merge_lane(writes, "edx", LANE_FULL)
    elif mnemonic in ("cdq", "cwd"):
        _merge_lane(reads, "eax", LANE_FULL)
        _merge_lane(writes, "edx", LANE_FULL)
    elif mnemonic in ("cdqe", "cwde", "cbw"):
        _merge_lane(reads, "eax", LANE_FULL)
        _merge_lane(writes, "eax", LANE_FULL)
    # call / ret / jmp / jcc: handled by the liveness builder.
    return reads, writes, stack_reads


def _restored_regs(lines: list[DisasmLine], addr: int, sz: int) -> set[str]:
    """Canonical registers the function restores (pops) before returning.

    Includes pops in the function's own body plus those in a (possibly
    multi-hop) tail-merge `jmp` chain into shared epilogues.  Used to tell
    a genuine parameter SPILL (pushed, slot read, NOT restored —
    create_figure) from a callee-save whose saved slot is read as the
    incoming caller value (pushed, slot read, AND restored —
    evolve_security_activity's EDX, a Rule-77-style use).
    """
    restored: set[str] = set()
    for ln in lines:
        if ln.mnemonic.lower() == "pop":
            pr = _operand_regs(ln.op_str)
            if pr:
                restored.add(pr[0])

    def _jmp_target(ln: DisasmLine) -> Optional[int]:
        if isinstance(ln.target, int):
            return ln.target
        op = ln.op_str.strip()
        try:
            return int(op, 16) if op.lower().startswith("0x") else None
        except ValueError:
            return None

    if lines and lines[-1].mnemonic.lower() == "jmp":
        tgt = _jmp_target(lines[-1])
        cur_lo, cur_hi = addr, addr + sz
        for _hop in range(4):
            if tgt is None or (cur_lo <= tgt < cur_hi):
                break
            try:
                a2, s2, donor = disasm_function(f"0x{tgt:X}", size=64)
            except Exception:
                break
            cur_lo, cur_hi, tgt = a2, a2 + s2, None
            for dln in donor:
                dm = dln.mnemonic.lower()
                if dm == "pop":
                    pr = _operand_regs(dln.op_str)
                    if pr:
                        restored.add(pr[0])
                elif dm == "ret":
                    break
                elif dm == "jmp":
                    tgt = _jmp_target(dln)
                    break
    return restored


def _build_cfg_succ(lines: list[DisasmLine]) -> list[list[int]]:
    """Successor index lists for each instruction (intra-function edges)."""
    n = len(lines)
    addr_idx = {ln.address: i for i, ln in enumerate(lines)}
    succ: list[list[int]] = [list() for _ in range(n)]
    for i, ln in enumerate(lines):
        m = ln.mnemonic.lower()
        nxt = [i + 1] if i + 1 < n else []
        if m == "ret":
            succ[i] = []
        elif m == "jmp":
            tgt = _branch_target_addr(ln)
            succ[i] = [addr_idx[tgt]] if (tgt is not None and tgt in addr_idx) else []
        elif m.startswith("j") or m in ("loop", "loope", "loopne"):
            tgt = _branch_target_addr(ln)
            s = list(nxt)
            if tgt is not None and tgt in addr_idx:
                s.append(addr_idx[tgt])
            succ[i] = s
        else:  # includes call (returns to fallthrough)
            succ[i] = nxt
    return succ


def _reachable_indices(lines: list[DisasmLine]) -> set[int]:
    """Instruction indices reachable from entry (index 0).

    Used to ignore trailing code the disassembler over-read past the real
    function end (the size estimate is distance-to-next-symbol, which
    swallows adjacent unnamed functions).
    """
    if not lines:
        return set()
    succ = _build_cfg_succ(lines)
    n = len(lines)
    reach: set[int] = set()
    stack = [0]
    while stack:
        x = stack.pop()
        if x in reach or not (0 <= x < n):
            continue
        reach.add(x)
        stack.extend(succ[x])
    return reach


def _live_in_arg_regs(lines: list[DisasmLine]) -> set[str]:
    """Arg registers (EAX/EDX/EBX/ECX) live-in at the function entry.

    Instruction-level byte-granular liveness over the function's control
    flow graph, computed to a fixpoint.  A register read before being
    (fully) written along some path reachable from entry is a parameter
    — this catches arguments first used inside a loop body (behind a
    backward branch) that the simpler forward walk misses, while
    reachability-from-entry ignores any trailing code the disassembler
    over-read past the real function end.
    """
    n = len(lines)
    if n == 0:
        return set()
    addr_idx = {ln.address: i for i, ln in enumerate(lines)}

    use: list[dict[str, int]] = [dict() for _ in range(n)]
    dfn: list[dict[str, int]] = [dict() for _ in range(n)]
    succ: list[list[int]] = [list() for _ in range(n)]

    for i, ln in enumerate(lines):
        m = ln.mnemonic.lower()
        nxt = [i + 1] if i + 1 < n else []
        if m == "call":
            tgt_name = ln.target or ""
            if "__chk" in tgt_name.lower() or "__stk" in tgt_name.lower():
                # Watcom stack-check stubs preserve every register.
                succ[i] = nxt
                continue
            argc = _declared_call_reg_arg_count(tgt_name)
            u: dict[str, int] = {r: LANE_FULL for r in _ARG_REGS[:argc]}
            # __watcall scratch set: EAX, EDX, ECX (EBX is preserved
            # across calls).  Parameter registers are also clobbered.
            d: dict[str, int] = {"eax": LANE_FULL, "edx": LANE_FULL, "ecx": LANE_FULL}
            for r in _ARG_REGS[:argc]:
                d[r] = LANE_FULL
            use[i] = u
            dfn[i] = d
            succ[i] = nxt
        elif m == "ret":
            succ[i] = []
        elif m == "jmp":
            tgt = _branch_target_addr(ln)
            if tgt is not None and tgt in addr_idx:
                succ[i] = [addr_idx[tgt]]
            else:
                succ[i] = []  # tail-call / external jump == exit
        elif m.startswith("j"):  # conditional branch
            r, w, _ = _classify_lanes(ln)
            use[i] = r
            dfn[i] = w
            tgt = _branch_target_addr(ln)
            s = list(nxt)
            if tgt is not None and tgt in addr_idx:
                s.append(addr_idx[tgt])
            succ[i] = s
        elif m in ("loop", "loope", "loopne"):
            tgt = _branch_target_addr(ln)
            s = list(nxt)
            if tgt is not None and tgt in addr_idx:
                s.append(addr_idx[tgt])
            _merge_lane(dfn[i], "ecx", LANE_FULL)
            _merge_lane(use[i], "ecx", LANE_FULL)
            succ[i] = s
        else:
            r, w, _ = _classify_lanes(ln)
            use[i] = r
            dfn[i] = w
            succ[i] = nxt

    # Reachable instructions from entry (index 0).
    reachable: set[int] = set()
    stack = [0]
    while stack:
        x = stack.pop()
        if x in reachable or not (0 <= x < n):
            continue
        reachable.add(x)
        stack.extend(succ[x])

    live_in: list[dict[str, int]] = [dict() for _ in range(n)]
    live_out: list[dict[str, int]] = [dict() for _ in range(n)]
    order = [i for i in range(n) if i in reachable]
    changed = True
    while changed:
        changed = False
        for i in reversed(order):
            lo: dict[str, int] = {}
            for s in succ[i]:
                if 0 <= s < n:
                    for r, mask in live_in[s].items():
                        lo[r] = lo.get(r, 0) | mask
            li = dict(use[i])
            for r, mask in lo.items():
                rem = mask & ~dfn[i].get(r, 0)
                if rem:
                    li[r] = li.get(r, 0) | rem
            if li != live_in[i] or lo != live_out[i]:
                live_in[i] = li
                live_out[i] = lo
                changed = True

    entry = live_in[0]
    return {r for r in _ARG_REGS if entry.get(r, 0)}


def infer_sig(
    name_or_addr: str,
    *,
    size: Optional[int] = None,
) -> InferredSig:
    """Infer the signature of a function in PS.EXE."""
    addr, sz, lines = disasm_function(name_or_addr, size=size)

    # Resolve symbol name (best effort).
    name = name_or_addr if not name_or_addr.startswith("0x") else f"sub_{addr:X}"

    sig = InferredSig(name=name, address=addr, size=sz)

    # 1) Walk prologue — collect callee-save pushes and stack-frame
    #    allocation until we hit a non-prologue instruction.  Stack
    #    references observed later are relative to this adjusted ESP,
    #    so the first caller-passed stack arg is after locals, saved
    #    regs, and the return address.
    body_start = 0
    local_stack_bytes = 0
    # Argument registers (EAX/EDX/ECX/EBX) pushed in the prologue: under
    # __watcall these are incoming register parameters being spilled to a
    # stack slot (e.g. create_figure: `push eax; push ebx`).  Their
    # presence is asm-level evidence that the function uses the register
    # calling convention, even when the body's register reads sit behind a
    # backward branch the forward-only walk can't reach.
    prologue_arg_spills: set[str] = set()
    for i, ln in enumerate(lines):
        m = ln.mnemonic.lower()
        if m == "push":
            regs = _operand_regs(ln.op_str)
            if regs:
                # Register push: a callee-save (or a Rule 24a spill local).
                # Either way the body analysis below correctly determines
                # whether the register's incoming value is an argument by
                # checking read-before-write, so consume it as prologue.
                sig.callee_saves.append(regs[0])
                if regs[0] in _ARG_REGS:
                    prologue_arg_spills.add(regs[0])
                body_start = i + 1
                continue
            # `push <imm>` / `push <mem>`: a prologue artefact only when it
            # feeds the Watcom stack-check stub (`push N; call __CHK`).
            # Otherwise it is the start of cdecl call-argument setup
            # (`push 0x200; push eax; call open`) and therefore the first
            # body instruction — stop the prologue here so the following
            # `push eax` is analysed as a live-in read of a forwarded
            # parameter rather than being silently consumed.
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if (
                nxt is not None
                and nxt.mnemonic.lower() == "call"
                and "__chk" in (nxt.target or "").lower()
            ):
                body_start = i + 1
                continue
            break
        elif m == "sub" and "esp" in ln.op_str.lower():
            # Stack frame allocation; included in prologue.
            parts = [p.strip() for p in ln.op_str.split(",")]
            if len(parts) >= 2 and parts[0].lower() == "esp":
                try:
                    local_stack_bytes += int(parts[1], 0)
                except ValueError:
                    pass
            body_start = i + 1
        elif m == "call" and "__chk" in (ln.target or "").lower():
            body_start = i + 1
        else:
            break

    # 2) Walk body in CONTROL-FLOW order (not linear).  We follow
    #    unconditional forward `jmp` instructions to their target so
    #    that loop-skip patterns (`mov [m], 1; jmp test; loop: ...`)
    #    don't falsely mark loop registers as arguments.
    #
    #    For conditional branches, we explore the fall-through path
    #    only; this misses branches that lead to early arg reads, but
    #    captures the common pattern where args are saved to callee-
    #    save registers in the entry basic block.
    #
    #    We bail out on backward jumps (we've already processed that
    #    code) and on RET.
    body_lines = lines[body_start:]
    addr_to_idx: dict[int, int] = {ln.address: i for i, ln in enumerate(body_lines)}

    live_in: set[str] = set()
    written_so_far: set[str] = set()
    stack_offsets: set[int] = set()

    visited: set[int] = set()
    idx = 0
    while 0 <= idx < len(body_lines):
        if idx in visited:
            break
        visited.add(idx)
        ln = body_lines[idx]
        m = ln.mnemonic.lower()

        if m == "ret":
            break

        if m == "call":
            # A function can pass one of its own incoming parameters
            # straight through to a callee without first moving it
            # (e.g. show_lbm(fname) immediately calls readfile(fname,
            # ...)).  Calls clobber only the callee's CallZap set under
            # Watcom (parm regs plus return reg), not blindly EDX/ECX.
            target_argc = _declared_call_reg_arg_count(ln.target or "")
            for reg in _ARG_REGS[:target_argc]:
                if reg not in written_so_far and reg not in live_in:
                    live_in.add(reg)
            for reg in _ARG_REGS[:target_argc]:
                written_so_far.add(reg)
            if not _declared_call_returns_void(ln.target or ""):
                written_so_far.add("eax")
            idx += 1
            continue

        # Unconditional JMP — follow forward jumps; bail on backward.
        if m == "jmp":
            tgt = _branch_target_addr(ln)
            if tgt is None:
                break
            tgt_idx = addr_to_idx.get(tgt)
            if tgt_idx is None or tgt_idx <= idx:
                break
            idx = tgt_idx
            continue

        read, written, stack_reads = _classify(ln)

        for r in read:
            if r in _ARG_REGS and r not in written_so_far and r not in live_in:
                live_in.add(r)
        first_stack_arg_off = local_stack_bytes + 4 * len(sig.callee_saves) + 4
        for off in stack_reads:
            if off >= first_stack_arg_off:
                # Normalize back to the caller's entry-ESP-relative
                # argument offset ([esp+4] is the first stack arg).
                stack_offsets.add(off - local_stack_bytes - 4 * len(sig.callee_saves))
        for w in written:
            written_so_far.add(w)

        idx += 1

    # 3) Return-value detection (callee side).  Walk all RET
    #    instructions; for each, scan backward to find the LAST EAX
    #    write that's NOT a `call` clobber.  If between that write
    #    and the RET no instruction READS EAX, the write is
    #    "dead-on-return" → EAX carries the return value.
    #
    #    Calls clobber EAX as a side effect; treating that as a
    #    return-setup gives false positives for `call X; ret` shapes
    #    where the function is genuinely void.  We bail when we see
    #    a `call` and rely on caller-side analysis (combine_with_
    #    callers) for those ambiguous cases.
    has_return = False
    return_size = 0
    # Track whether EVERY exit path ends with a `call X` as the last
    # EAX-touching instruction (no explicit EAX write between).  If so,
    # EAX at ret is unreliable — see InferredSig.leaks_call_eax.
    leaks_call_eax = True  # AND across all exits; stays True only if every exit qualifies
    saw_any_exit = False
    fn_end = addr + sz
    for ret_idx, ln in enumerate(body_lines):
        # Treat both RET and tail-call JMP (jmp to outside-function
        # address) as exit points.  A tail call passes through the
        # callee's return value, so EAX live at the jmp → return.
        is_exit = False
        if ln.mnemonic.lower() == "ret":
            is_exit = True
        elif ln.mnemonic.lower() == "jmp":
            tgt = _branch_target_addr(ln)
            # Only treat as a tail-call if the target resolves to a
            # named function entry (ln.target set).  jmp into the
            # middle of another function (Rule 15 cross-function
            # tail-merge) has target=None and is NOT a tail call —
            # the function flows into someone else's epilogue.
            if (
                tgt is not None
                and ln.target
                and (tgt < addr or tgt >= fn_end)
            ):
                is_exit = True
        if not is_exit:
            continue
        saw_any_exit = True
        this_exit_leaks = False
        # If this exit is a tail-call jmp to a named function, the
        # `mov eax, X` immediately before is setting up the
        # tail-callee's first arg, NOT a return value.  The function
        # inherits whatever the tail-callee returns — so EAX is
        # "leaked" from the tail call's perspective (same as call;
        # ret).  Skip the body's EAX-write scan in this case.
        if ln.mnemonic.lower() == "jmp" and ln.target:
            this_exit_leaks = True
            continue
        for j in range(ret_idx - 1, -1, -1):
            prev = body_lines[j]
            pm = prev.mnemonic.lower()
            if pm == "call":
                # No explicit EAX write was found between this call
                # and the ret — EAX at ret is whatever the call left.
                this_exit_leaks = True
                break
            r, w, _ = _classify(prev)
            # Check WRITE first — a read-modify-write instruction
            # (and eax, 0xff; or eax, X; etc.) writes the final EAX
            # value which is then the return.  If we checked read
            # first we'd bail before recognising the write.
            if "eax" in w:
                has_return = True
                op_str = prev.op_str.lower()
                if pm in ("mov", "movzx", "movsx") and op_str.startswith("al,"):
                    return_size = max(return_size, 1)
                elif pm in ("mov", "movzx", "movsx") and op_str.startswith("ax,"):
                    return_size = max(return_size, 2)
                else:
                    return_size = max(return_size, 4)
                break
            if "eax" in r:
                # Pure read — EAX value flows into a later
                # consumer (e.g. `mov [m], eax`); not a return.
                break
            if pm == "jmp" or pm.startswith("j"):
                break
        if not this_exit_leaks:
            # This exit either wrote EAX explicitly or had no
            # call-before-ret pattern; the function is not a pure
            # call-leak.
            leaks_call_eax = False

    # Argument-register detection (callee side).  Three evidence sources,
    # all derived from the asm so the analysis transfers to any __watcall
    # binary:
    #
    # 1. CFG byte-granular liveness over the BODY (after the prologue): an
    #    arg register read before being written along some path reachable
    #    from the body entry is a parameter.  This catches args first used
    #    inside a loop body that the forward-only walk missed, and byte
    #    granularity catches 8-bit params read via AL while AH is cleared.
    #    Running over the body (not the whole function) keeps callee-save
    #    prologue pushes — which read the register only to save it — from
    #    looking like parameter uses.
    #
    # 2. Prologue classification of pushed arg registers.  A register
    #    pushed in the prologue is either:
    #      * a parameter SPILL — its stack slot is later READ (Rule 24a,
    #        create_figure's `push eax`/`push ebx`) — in which case it is a
    #        genuine incoming argument, or
    #      * a CALLEE-SAVE — its slot is never read, only (eventually)
    #        popped — in which case it is a register the function borrows,
    #        not a parameter.
    #    Under __watcall you never preserve an argument register for the
    #    caller, so "pushed but slot-not-read" cleanly identifies a
    #    callee-save WITHOUT needing to locate the matching pop (which may
    #    live in a multi-hop tail-merge / shared epilogue, or be invisible
    #    when the size estimate over-reads, e.g. dock_the_ship).  We drop
    #    such callee-saves from the liveness candidates, which also rejects
    #    Rule-77 uninitialised-callee-save reads (get_army_name's EBX) and
    #    infeasible-path liveness artefacts on saved registers.
    #
    # The __watcall prefix property then fills any gap: parameters occupy
    # EAX, EDX, EBX, ECX in order, so the highest surviving candidate
    # implies every lower-index register is also a parameter slot.
    body_live_args = _live_in_arg_regs(body_lines)
    restored_args = {r for r in _ARG_REGS if r in _restored_regs(lines, addr, sz)}

    raw_stack_reads: set[int] = set()
    _body_reach = _reachable_indices(body_lines)
    for _bi, _bln in enumerate(body_lines):
        if _bi not in _body_reach:
            continue  # ignore trailing over-read code from adjacent fns
        _, _, _sr = _classify(_bln)
        raw_stack_reads.update(_sr)
    n_pushes = len(sig.callee_saves)
    spilled_args: set[str] = set()
    pushed_arg_regs: set[str] = set()
    for _j, _reg in enumerate(sig.callee_saves):
        if _reg in _ARG_REGS:
            pushed_arg_regs.add(_reg)
            # Slot of the j-th prologue push (push order), relative to the
            # post-prologue ESP: 4*(m-1-j) + local_stack_bytes.  A push is
            # a genuine parameter spill only when its slot is READ and the
            # register is NOT restored: a restored register whose slot is
            # read is a callee-save being read for its incoming value
            # (Rule-77-style), not an argument (evolve_security_activity).
            _slot = 4 * (n_pushes - 1 - _j) + local_stack_bytes
            if _slot in raw_stack_reads and _reg not in restored_args:
                spilled_args.add(_reg)
    # A pushed arg register that is not a parameter spill is a callee-save
    # the function borrows — drop it from the liveness candidates.  This
    # needs no pop evidence (handles dock_the_ship, whose pops live in an
    # over-read / multi-hop epilogue) yet still rejects Rule-77 reads.
    callee_save_args = pushed_arg_regs - spilled_args

    param_args = (body_live_args - callee_save_args) | spilled_args
    if param_args:
        _highest = max(_ARG_REGS.index(r) for r in param_args)
        sig.arg_regs = list(_ARG_REGS[: _highest + 1])
    else:
        sig.arg_regs = []
    _live_arg_regs = sig.arg_regs
    sig.stack_args = sorted(stack_offsets)

    # `ret <imm>` (imm > 0) cleans the caller's stack arguments on return.
    # Under __watcall the four register slots (EAX, EDX, EBX, ECX) are
    # filled before any stack arg is used, so a non-zero `ret` operand is
    # definitive evidence of BOTH a full 4-register arg list AND imm/4
    # stack parameters — even when the body spills them to stack slots and
    # reads them back indirectly (e.g. create_figure: `ret 0xc` => 4 reg
    # args + 3 stack args).  This is control-flow-independent, so scan all
    # lines rather than relying on the body walk reaching the final ret.
    _ret_clean = 0
    for _ln in lines:
        if _ln.mnemonic.lower() == "ret":
            _op = _ln.op_str.strip()
            if _op:
                try:
                    _ret_clean = max(_ret_clean, int(_op, 0))
                except ValueError:
                    pass
    # Trust the watcall interpretation of `ret N` only when the asm shows
    # register-calling evidence: either a live-in arg register read, or an
    # arg register spilled to the stack in the prologue (create_figure).
    # A function that cleans its stack with `ret N` but touches no arg
    # register and spills none (e.g. Smacker's RADMALLOC, which reads its
    # parameter straight from `[esp+4]`) uses a stack-based convention, so
    # we must NOT fabricate four register parameters for it.
    _watcall_evidence = bool(_live_arg_regs) or bool(prologue_arg_spills)
    if _ret_clean > 0 and _watcall_evidence:
        sig.arg_regs = list(_ARG_REGS)
        _n_stack = _ret_clean // 4
        # Represent stack params as synthetic ascending offsets; only the
        # count matters for arg-count comparison.
        sig.stack_args = sorted(set(sig.stack_args) | {0x100 + 4 * k for k in range(_n_stack)})
    sig.has_return = has_return
    sig.return_size = return_size if has_return else 0
    sig.leaks_call_eax = saw_any_exit and leaks_call_eax and not has_return

    return sig


def _branch_target_addr(ln: DisasmLine) -> Optional[int]:
    """Extract the target address of a branch or jmp instruction.

    Returns ``None`` if the operand is indirect or unparseable.
    """
    op = ln.op_str.strip()
    # capstone's op_str is typically a hex literal like '0x1234' or '0x....'
    if op.startswith("0x"):
        try:
            return int(op, 16)
        except ValueError:
            return None
    # Symbolic targets (resolved by disasm tooling) won't have a clean
    # hex form; we'd need ln.target.  For now, return None.
    return None


# ── Caller-side cross-reference analysis ─────────────────────────
#
# A more reliable signal than callee-side analysis alone: look at the
# functions that CALL the target and check how they treat EAX after the
# call.  If any caller does `call f; mov [m], eax` (or any other read
# of EAX before writing it), then `f` returns a value.  Conversely, if
# every caller treats EAX as dead after the call, `f` is void.


import json as _json


@dataclass
class CallerEvidence:
    """What the callers tell us about a function's signature."""
    target: str
    n_call_sites: int
    args_set_before_call: dict[str, int] = field(default_factory=dict)
    """Per-arg-reg, how many call sites set it before the call."""
    eax_used_after_call: int = 0
    """Number of call sites where EAX is read before being written."""
    eax_dead_after_call: int = 0
    """Number of call sites where EAX is dead (overwritten/unused)."""
    caller_names: list[str] = field(default_factory=list)
    """Names of callers (one entry per call site, may repeat)."""

    def confirmed_arg_count(self, threshold: float = 0.8) -> int:
        """Caller-confirmed arg count: longest prefix of [eax,edx,ebx,ecx]
        where each reg is set up by >= ``threshold`` of call sites.

        This is the legacy strict-prefix algorithm.  Prefer
        :meth:`confirmed_arg_count_prefix_property` for new code:
        it exploits the __watcall prefix property to recover args
        that look unset in the visible look-back window (typically
        pass-throughs of the caller's own incoming parm).

        Returns -1 when there is no caller evidence.
        """
        if self.n_call_sites == 0:
            return -1     # "no evidence"
        n = 0
        for reg in ("eax", "edx", "ebx", "ecx"):
            count = self.args_set_before_call.get(reg, 0)
            if count >= self.n_call_sites * threshold:
                n += 1
            else:
                break
        return n

    def confirmed_arg_count_prefix_property(
        self,
        *,
        hi_threshold: float = 0.85,
        sanity_threshold: float = 0.50,
        min_sites: int = 3,
    ) -> tuple[int, str]:
        """Caller-confirmed arg count using the __watcall prefix property.

        Under __watcall, the caller MUST set every reg parm it intends
        to pass.  Therefore if a high-index reg (e.g. ECX) is
        consistently set, every lower-index reg (EAX/EDX/EBX) must
        also be an arg — even if their visible "set" ratio is lower
        (pass-through of the caller's own incoming parm escapes our
        finite look-back window).

        Algorithm:
          1. Find the highest index ``k`` where ratio[k] >=
             ``hi_threshold``.  If none, return ``(0, 'no-args')``.
          2. Validate the prefix: every ratio[0..k-1] must be >=
             ``sanity_threshold``.  If not, fall back to the longest
             well-formed prefix.
          3. Return ``(k + 1, 'confident')``.

        Returns ``(None, 'insufficient')`` when call-site count is
        below ``min_sites`` — caller-side data is too noisy to be
        trusted at small samples; fall back to body-side then.
        """
        if self.n_call_sites < min_sites:
            return None, "insufficient"
        n = self.n_call_sites
        ratios = [
            (self.args_set_before_call.get(r, 0) / n)
            for r in ("eax", "edx", "ebx", "ecx")
        ]
        highest = -1
        for i, ratio in enumerate(ratios):
            if ratio >= hi_threshold:
                highest = i
        if highest < 0:
            return 0, "no-args"
        # Sanity check: all lower-index ratios above sanity threshold
        if all(ratios[j] >= sanity_threshold for j in range(highest)):
            return highest + 1, "confident"
        # Find longest well-formed prefix
        for k in range(highest - 1, -1, -1):
            if ratios[k] >= hi_threshold and all(
                ratios[j] >= sanity_threshold for j in range(k)
            ):
                return k + 1, "prefix-fallback"
        return 0, "sanity-fail"


_CALL_INDEX: dict[str, list[tuple[str, int, list[DisasmLine]]]] | None = None


def _build_call_index(
    symbols_json: Path = Path("data/out/symbols.json"),
    exe_path: Path = Path("data/PS.EXE"),
) -> dict[str, list[tuple[str, int, list[DisasmLine]]]]:
    """Build (target_name → [(caller_name, call_idx, caller_lines), ...]).

    Caches the result at module scope.  Building takes ~30s on a cold
    cache; subsequent calls are instant.
    """
    global _CALL_INDEX
    if _CALL_INDEX is not None:
        return _CALL_INDEX

    # Cross-process cache: the full-image walk (~2300 disasms, ~4s) was
    # rebuilt on EVERY decomp-verify invocation for the Sig hint.  The
    # compact (target -> [(caller, idx)]) map is persisted keyed by the
    # exe's identity; caller LINES are re-disassembled lazily (only the
    # handful of callers actually queried).
    cache = Path(".c2-cache/call_index.json")
    st = Path(exe_path).stat()
    cache_key = f"{st.st_mtime_ns}:{st.st_size}"
    compact: dict[str, list] | None = None
    if cache.exists():
        try:
            data = _json.loads(cache.read_text())
            if data.get("key") == cache_key:
                compact = data["index"]
        except Exception:
            compact = None
    if compact is None:
        sym = _json.loads(Path(symbols_json).read_text())
        code_funcs = sorted(
            (s for s in sym["symbols"] if s.get("is_code")),
            key=lambda s: s["address"],
        )
        compact = {}
        for s in code_funcs:
            try:
                _, _, lines = disasm_function(
                    s["name"], symbols_json=symbols_json, exe_path=exe_path,
                )
            except (KeyError, ValueError, FileNotFoundError):
                continue
            for i, ln in enumerate(lines):
                if ln.target and ln.mnemonic.lower() == "call":
                    compact.setdefault(ln.target, []).append([s["name"], i])
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            tmp = cache.with_suffix(f".tmp{__import__('os').getpid()}")
            tmp.write_text(_json.dumps({"key": cache_key, "index": compact}))
            tmp.replace(cache)
        except Exception:
            pass

    class _LazyIndex(dict):
        """dict that disassembles caller lines on first access."""
        def get(self, target, default=None):
            if dict.__contains__(self, target):
                return dict.__getitem__(self, target)
            sites = compact.get(target)
            if sites is None:
                return default
            out = []
            _dis_cache: dict[str, list] = {}
            for caller, idx in sites:
                if caller not in _dis_cache:
                    try:
                        _, _, lines = disasm_function(
                            caller, symbols_json=symbols_json,
                            exe_path=exe_path)
                    except (KeyError, ValueError, FileNotFoundError):
                        lines = []
                    _dis_cache[caller] = lines
                lines = _dis_cache[caller]
                if idx < len(lines):
                    out.append((caller, idx, lines))
            dict.__setitem__(self, target, out)
            return out

    _CALL_INDEX = _LazyIndex()
    return _CALL_INDEX


def infer_sig_from_callers(
    name: str,
    *,
    look_before: int = 6,
    look_after: int = 4,
) -> CallerEvidence:
    """Aggregate evidence about ``name``'s signature from its callers.

    For each call site:
      * Look at the ~6 instructions BEFORE the call — which arg
        registers were written?  (Crude proxy for "this register was
        set up as a call argument".)
      * Look at the ~4 instructions AFTER the call — is EAX read
        before being written, or is its first usage a write?
    """
    index = _build_call_index()
    sites = index.get(name, [])
    ev = CallerEvidence(target=name, n_call_sites=len(sites))
    if not sites:
        return ev

    arg_set_counts: dict[str, int] = {r: 0 for r in _ARG_REGS}
    for caller, idx, lines in sites:
        # Look BEFORE the call: which arg regs got written within the
        # last `look_before` instructions?
        seen_args: set[str] = set()
        for j in range(idx - 1, max(0, idx - look_before) - 1, -1):
            prev = lines[j]
            pm = prev.mnemonic.lower()
            if pm == "call" or pm.startswith("j") or pm == "ret":
                break
            r, w, _ = _classify(prev)
            for reg in w:
                if reg in _ARG_REGS and reg not in seen_args:
                    seen_args.add(reg)
        for r in seen_args:
            arg_set_counts[r] += 1
        ev.caller_names.append(caller)

        # Look AFTER the call: is EAX read before being written?
        used = False
        for j in range(idx + 1, min(len(lines), idx + 1 + look_after)):
            nxt = lines[j]
            nm = nxt.mnemonic.lower()
            if nm == "ret":
                ev.eax_used_after_call += 1
                used = True
                break
            if nm == "call":
                ev.eax_dead_after_call += 1
                used = True
                break
            r, w, _ = _classify(nxt)
            if "eax" in r:
                ev.eax_used_after_call += 1
                used = True
                break
            if "eax" in w:
                ev.eax_dead_after_call += 1
                used = True
                break
        if not used:
            ev.eax_dead_after_call += 1

    ev.args_set_before_call = arg_set_counts
    return ev


def cli_inferred_sig(
    name: str,
    *,
    size: Optional[int] = None,
) -> str:
    """Print human-readable inferred signature."""
    sig = infer_sig(name, size=size)
    parts = [
        f"=== {sig.name} @ 0x{sig.address:X} ({sig.size} bytes) ===",
        f"  inferred:    {sig.render()}",
        f"  callee-saves: {' '.join(sig.callee_saves) or '(none)'}",
        f"  arg regs:    {' '.join(sig.arg_regs) or '(none)'}",
        f"  has return:  {sig.has_return}"
        + (f"  ({sig.return_size}-byte)" if sig.return_size else ""),
    ]
    if sig.stack_args:
        parts.append(
            f"  stack args:  "
            + ", ".join(f"[esp+{o:#x}]" for o in sig.stack_args)
        )
    return "\n".join(parts)


# ── Compare against currently-declared C signatures ───────────

from pycparser import c_ast

from c2.commands.c_source import (
    classify_source,
    _is_void_return,
    _return_type_str,
    _get_generator,
)


@dataclass
class DeclaredSig:
    """Currently-declared C signature pulled from .c / .h files."""
    name: str
    return_type: str
    arg_types: list[str]      # C type strings, in order; empty for f(void)
    is_stub: bool             # "// STUB:" marker present at the def
    file: str                 # source file path
    line: int                 # line number of definition
    raw: str                  # rendered signature text

    @property
    def returns_void(self) -> bool:
        return self.return_type.strip().lower() in ("void",)

    @property
    def n_args(self) -> int:
        return len(self.arg_types)


def _arg_types_from_funcdecl(func_decl: c_ast.FuncDecl) -> list[str]:
    """Extract argument type strings from a FuncDecl AST node."""
    if func_decl.args is None:
        return []
    gen = _get_generator()
    out = []
    params = func_decl.args.params or []
    # `f(void)` is encoded as a single Typename with type 'void'.
    if (
        len(params) == 1
        and isinstance(params[0], c_ast.Typename)
        and isinstance(params[0].type, c_ast.TypeDecl)
        and isinstance(params[0].type.type, c_ast.IdentifierType)
        and "void" in params[0].type.type.names
    ):
        return []
    for p in params:
        if isinstance(p, c_ast.EllipsisParam):
            out.append("...")
            continue
        # Render the parameter, then strip the trailing identifier.
        if isinstance(p, c_ast.Decl):
            # Render only the type portion by clearing the name.
            p_copy = c_ast.Decl(
                name=None,
                quals=p.quals,
                align=getattr(p, "align", None),
                storage=p.storage,
                funcspec=p.funcspec,
                type=p.type,
                init=None,
                bitsize=None,
            )
            # Strip the deepest identifier from the type tree by walking it.
            type_node = p_copy.type
            while hasattr(type_node, "declname"):
                type_node.declname = None
                if hasattr(type_node, "type"):
                    type_node = type_node.type
                else:
                    break
            try:
                rendered = gen.visit(p_copy).strip().rstrip(";")
            except Exception:
                rendered = "?"
            out.append(rendered)
        elif isinstance(p, c_ast.Typename):
            try:
                rendered = gen.visit(p).strip()
            except Exception:
                rendered = "?"
            out.append(rendered)
        else:
            out.append("?")
    return out


_DECLARED_CALL_ARG_CACHE: dict[str, tuple[int, bool]] | None = None


def _declared_call_reg_arg_count(name: str) -> int:
    """Declared register-arg count for a direct call target.

    Used by body-side inference to spot pass-through parameters at
    calls.  Returns 0 when the target is unknown so we don't invent
    live-ins for library/asm helpers lacking source definitions.
    """
    _ensure_declared_call_cache()
    if _DECLARED_CALL_ARG_CACHE is None:
        return 0
    return _DECLARED_CALL_ARG_CACHE.get(name, (0, False))[0]


def _declared_call_returns_void(name: str) -> bool:
    _ensure_declared_call_cache()
    if _DECLARED_CALL_ARG_CACHE is None:
        return False
    return _DECLARED_CALL_ARG_CACHE.get(name, (0, False))[1]



def _ensure_declared_call_cache() -> None:
    global _DECLARED_CALL_ARG_CACHE
    if _DECLARED_CALL_ARG_CACHE is not None:
        return
    try:
        _DECLARED_CALL_ARG_CACHE = {
            nm: (min(d.n_args, len(_ARG_REGS)), d.returns_void)
            for nm, d in scan_declared_sigs().items()
        }
    except Exception:
        _DECLARED_CALL_ARG_CACHE = {}


def scan_declared_sigs(src_dirs: list[Path] | None = None) -> dict[str, DeclaredSig]:
    """Scan decomp/src/*.c for function definitions via AST parsing.

    Multiple definitions with the same name (shouldn't happen) are
    overwritten by the last one seen.  Header forward decls in
    decomp/include/*.h are NOT scanned (we want the actual definition
    that's compiled, which is in the .c file).
    """
    if src_dirs is None:
        src_dirs = [Path("decomp/src")]
    out: dict[str, DeclaredSig] = {}
    for src_dir in src_dirs:
        for src in sorted(src_dir.glob("*.c")):
            text = src.read_text()
            try:
                decls = classify_source(text, src.name)
            except Exception as e:
                # Skip files that fail to parse (rare).
                continue
            for fn_def in decls.func_defs:
                name = fn_def.decl.name
                func_decl = fn_def.decl.type
                if not isinstance(func_decl, c_ast.FuncDecl):
                    continue
                ret_type = _return_type_str(func_decl)
                if _is_void_return(func_decl):
                    ret_type = "void"
                arg_types = _arg_types_from_funcdecl(func_decl)
                # Detect STUB annotation by inspecting decls.annotations
                # at the function's line range.
                line_no = fn_def.decl.coord.line if fn_def.decl.coord else 0
                ann = decls.annotations.get(line_no)
                is_stub = bool(ann and ann.kind == "STUB")
                # Render full signature.
                gen = _get_generator()
                try:
                    raw = gen.visit(fn_def.decl).strip()
                except Exception:
                    raw = name
                out[name] = DeclaredSig(
                    name=name,
                    return_type=ret_type,
                    arg_types=arg_types,
                    is_stub=is_stub,
                    file=str(src),
                    line=line_no,
                    raw=raw,
                )
    return out


@dataclass
class SigDiff:
    name: str
    declared: DeclaredSig
    inferred: InferredSig
    arg_count_mismatch: bool
    return_mismatch: bool
    caller_evidence: Optional[CallerEvidence] = None

    @property
    def has_diff(self) -> bool:
        return self.arg_count_mismatch or self.return_mismatch

    def render(self, declared_map: "dict[str, DeclaredSig] | None" = None) -> str:
        decl_args = ", ".join(self.declared.arg_types) or "void"
        lines = [
            f"  declared: {self.declared.return_type} "
            f"{self.declared.name}({decl_args})"
            + ("  [STUB]" if self.declared.is_stub else ""),
            f"  inferred: {self.inferred.render()}",
        ]
        if self.arg_count_mismatch:
            inferred_n = len(self.inferred.arg_regs) + len(self.inferred.stack_args)
            extra = ""
            if self.caller_evidence is not None and self.caller_evidence.n_call_sites > 0:
                cc = self.caller_evidence.confirmed_arg_count()
                if cc >= 0:
                    extra = f"  (caller-confirmed={cc})"
            lines.append(
                f"  ! ARG COUNT: declared={self.declared.n_args}, inferred={inferred_n}{extra}"
            )
        if self.return_mismatch:
            lines.append(
                f"  ! RETURN: declared {'void' if self.declared.returns_void else 'non-void'}, "
                f"inferred {'has return' if self.inferred.has_return else 'void'}"
            )
        if self.caller_evidence is not None and self.caller_evidence.n_call_sites > 0:
            ev = self.caller_evidence
            args_set = [f"{r}={n}" for r, n in ev.args_set_before_call.items() if n > 0]
            lines.append(
                f"  callers ({ev.n_call_sites}): "
                f"args set before call: {', '.join(args_set) or '(none)'}; "
                f"EAX after call: {ev.eax_used_after_call} use / "
                f"{ev.eax_dead_after_call} dead"
            )
            # If we have a declared map, surface caller kinds + names so
            # the user can see at a glance which lifted functions are
            # consuming this signature.
            if declared_map is not None and ev.caller_names:
                from collections import Counter
                counts = Counter(ev.caller_names)
                rendered = []
                for cname, n in counts.most_common():
                    cdecl = declared_map.get(cname)
                    if cdecl is None:
                        kind = "?"
                    elif cdecl.is_stub:
                        kind = "STUB"
                    else:
                        kind = "FUNC"
                    suffix = f"×{n}" if n > 1 else ""
                    rendered.append(f"{cname}[{kind}]{suffix}")
                # Group: FUNC callers first (the high-leverage ones).
                func_first = sorted(rendered, key=lambda s: "FUNC" not in s)
                lines.append(f"  caller list: {', '.join(func_first)}")
        return "\n".join(lines)


def compare_sig(
    name: str,
    declared_map: dict[str, DeclaredSig] | None = None,
    *,
    use_caller_evidence: bool = True,
) -> SigDiff:
    """Compare declared vs inferred signature for ``name``.

    With ``use_caller_evidence=True`` (default), the callee-side
    inference is cross-checked against caller-side analysis (xrefs).
    Specifically, the return-value detection switches to the caller-
    side signal when callee-side ends in a `call X; ret` pattern that
    leaves the answer ambiguous.
    """
    if declared_map is None:
        declared_map = scan_declared_sigs()
    if name not in declared_map:
        raise KeyError(f"No declared signature found for {name!r}")
    declared = declared_map[name]
    inferred = infer_sig(name)

    caller_ev: Optional[CallerEvidence] = None
    if use_caller_evidence:
        try:
            caller_ev = infer_sig_from_callers(name)
        except (FileNotFoundError, ValueError):
            caller_ev = None

        if caller_ev is not None and caller_ev.n_call_sites > 0:
            # Use caller evidence to refine return-value detection.
            # We require >= 50% of call sites to USE EAX before treating
            # the function as having a return value.  This filters out
            # noise where one caller happens to read EAX coincidentally.
            n_used = caller_ev.eax_used_after_call
            n_dead = caller_ev.eax_dead_after_call
            n_total = n_used + n_dead
            if n_total > 0:
                # Caller evidence is only authoritative when the
                # callee-side body signal is AMBIGUOUS — i.e. when
                # the body ends with a trailing `call` whose EAX
                # value leaks through to the ret (leaks_call_eax).
                # When the body has an EXPLICIT EAX write before
                # ret (e.g. `xor eax, eax; ret` or `mov eax, [esp];
                # ret`), trust the body — that's a deliberate
                # `return value;` even if no current caller uses it.
                #
                # When leaks_call_eax is True and few callers
                # consume EAX, the trailing call is just clobbering
                # a register — the function is genuinely void.
                if inferred.leaks_call_eax:
                    # Body is ambiguous (`call X; ret` where X may
                    # leak EAX).  Caller "use" evidence is unreliable
                    # because chains of void-tail-call functions
                    # propagate EAX through each other (act_new_game
                    # → click_warning → setup_whole_screen_refresh →
                    # garbage EAX consumed by act_new_game's caller).
                    # When we can't prove a deliberate return, treat
                    # as void.
                    inferred.has_return = False
                    inferred.return_size = 0
                # else: trust the body's has_return as already set
                # by callee-side inference; do NOT demote.

            # Caller-side arg-count refinement: extend (never
            # shrink) the callee-side findings.  Callee-side gives
            # us "args READ by the body" (definitely params).
            # Caller-side gives us "args PASSED by the caller"
            # (definitely params under __watcall, since the ABI
            # requires all arg regs be set before the call).
            #
            # The truth is the union: callee may ignore an arg the
            # caller passes (mosaic_frame_divider passes 4, body
            # overwrites ECX without reading), so the param count
            # in source is the LARGER of the two.
            #
            # We use the prefix-property algorithm (see
            # CallerEvidence.confirmed_arg_count_prefix_property):
            # if a high-index reg crosses the high-confidence
            # threshold, by __watcall's prefix property every
            # lower-index reg must also be a param (even if its
            # visible set ratio looks low due to caller-incoming
            # parm pass-through escaping our look-back window).
            caller_n, _conf = caller_ev.confirmed_arg_count_prefix_property()
            if caller_n is not None and caller_n > len(inferred.arg_regs):
                inferred.arg_regs = list(_ARG_REGS[:caller_n])

    inferred_n_args = len(inferred.arg_regs) + len(inferred.stack_args)
    arg_mismatch = declared.n_args != inferred_n_args
    # return_mismatch: declared void but inferred has return, OR vice versa.
    return_mismatch = declared.returns_void == inferred.has_return

    return SigDiff(
        name=name,
        declared=declared,
        inferred=inferred,
        arg_count_mismatch=arg_mismatch,
        return_mismatch=return_mismatch,
        caller_evidence=caller_ev,
    )


# ── CLI ──────────────────────────────────────────────────────────────

import typer
from typing_extensions import Annotated


def inferred_sig(
    name: Annotated[
        Optional[str],
        typer.Argument(
            help="Function name or address; omit with --all to scan everything",
        ),
    ] = None,
    show_all: Annotated[
        bool,
        typer.Option("--all", help="Scan all defined functions and report mismatches"),
    ] = False,
    only_stubs: Annotated[
        bool,
        typer.Option("--stubs", help="With --all, restrict to STUB functions"),
    ] = False,
    only_lifted: Annotated[
        bool,
        typer.Option(
            "--lifted",
            help="With --all, restrict to FUNCTION (non-stub) definitions — "
                 "these have wrong signatures of their own that affect their callers.",
        ),
    ] = False,
    has_lifted_callers: Annotated[
        bool,
        typer.Option(
            "--has-lifted-callers",
            help="With --all, restrict to functions called by ≥1 lifted (FUNCTION) caller. "
                 "Combine with --stubs to find stubs whose wrong signatures are "
                 "actively consumed by already-decompiled code (Rule-59-style leverage).",
        ),
    ] = False,
    caller_confirmed: Annotated[
        bool,
        typer.Option(
            "--caller-confirmed",
            help="With --all, only show ARG-COUNT mismatches where the caller-confirmed "
                 "arg count (running prefix of regs set by ≥80% of callers) disagrees "
                 "with the declared count. Filters out callee-side false positives from "
                 "local stack spills being misread as caller-passed stack args.",
        ),
    ] = False,
    only_diffs: Annotated[
        bool,
        typer.Option(
            "--diffs/--all-results",
            help="With --all, only show signatures that disagree with declared",
        ),
    ] = True,
    sort_impact: Annotated[
        bool,
        typer.Option(
            "--sort-impact/--no-sort-impact",
            help="With --all, sort by leverage = # of lifted callers (descending). "
                 "Default on so high-impact rows surface first.",
        ),
    ] = True,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON instead of text"),
    ] = False,
) -> None:
    """Infer a function's signature from PS.EXE disassembly.

    Without ``--all``, prints the inferred signature for one function
    plus a comparison to the currently-declared signature in
    decomp/src/.  Use ``--all`` to scan every function and report
    discrepancies.

    Filtering for high-leverage signature fixes (the use-case Rule 59
    surfaced):

    * ``--lifted`` — restrict to FUNCTION-annotated defs.  Wrong sigs
      here are real bugs in already-decompiled code.
    * ``--stubs --has-lifted-callers`` — restrict to STUBS that are
      consumed by already-decompiled code.  Fixing these stub sigs
      propagates correct types to callers and frequently closes byte
      diffs as a side effect.
    """
    if show_all:
        declared = scan_declared_sigs()
        diffs: list[SigDiff] = []
        for fn_name, decl in sorted(declared.items()):
            if only_stubs and not decl.is_stub:
                continue
            if only_lifted and decl.is_stub:
                continue
            try:
                d = compare_sig(fn_name, declared)
            except (KeyError, FileNotFoundError, ValueError):
                continue
            if only_diffs and not d.has_diff:
                continue
            if has_lifted_callers:
                ev = d.caller_evidence
                if ev is None or not ev.caller_names:
                    continue
                lifted_count = sum(
                    1 for c in set(ev.caller_names)
                    if (declared.get(c) is not None and not declared[c].is_stub)
                )
                if lifted_count == 0:
                    continue
            if caller_confirmed:
                ev = d.caller_evidence
                if ev is None or ev.n_call_sites == 0:
                    continue
                cc = ev.confirmed_arg_count()
                # Keep entries where caller evidence DISAGREES with
                # declared (the real-bug case).  Drop arg-count-only
                # mismatches where caller evidence supports declared.
                if d.arg_count_mismatch and cc == d.declared.n_args:
                    if not d.return_mismatch:
                        continue
            diffs.append(d)

        # Compute per-row impact metric (number of distinct lifted callers).
        def _lifted_caller_count(d: SigDiff) -> int:
            ev = d.caller_evidence
            if ev is None:
                return 0
            return sum(
                1 for c in set(ev.caller_names)
                if (declared.get(c) is not None and not declared[c].is_stub)
            )

        if sort_impact:
            diffs.sort(key=lambda d: (-_lifted_caller_count(d), d.name))

        if json_out:
            import json as _j
            from dataclasses import asdict
            payload = []
            for d in diffs:
                row = {
                    "name": d.name,
                    "address": f"0x{d.inferred.address:X}",
                    "size": d.inferred.size,
                    "file": d.declared.file,
                    "line": d.declared.line,
                    "is_stub": d.declared.is_stub,
                    "declared": {
                        "return_type": d.declared.return_type,
                        "arg_types": list(d.declared.arg_types),
                        "raw": d.declared.raw,
                    },
                    "inferred": {
                        "return_type": "int" if d.inferred.has_return else "void",
                        "arg_regs": list(d.inferred.arg_regs),
                        "stack_args": list(d.inferred.stack_args),
                        "has_return": d.inferred.has_return,
                    },
                    "arg_count_mismatch": d.arg_count_mismatch,
                    "return_mismatch": d.return_mismatch,
                    "caller_confirmed_arg_count": (
                        d.caller_evidence.confirmed_arg_count()
                        if d.caller_evidence else -1
                    ),
                    "lifted_caller_count": _lifted_caller_count(d),
                    "callers": (
                        [
                            {
                                "name": cname,
                                "kind": (
                                    "STUB" if (declared.get(cname) and declared[cname].is_stub)
                                    else ("FUNC" if declared.get(cname) else "?")
                                ),
                                "call_count": d.caller_evidence.caller_names.count(cname),
                            }
                            for cname in sorted(set(d.caller_evidence.caller_names))
                        ] if d.caller_evidence else []
                    ),
                }
                payload.append(row)
            typer.echo(_j.dumps(payload, indent=2))
            return

        for d in diffs:
            lc = _lifted_caller_count(d)
            tag = "STUB" if d.declared.is_stub else "FUNC"
            typer.echo(
                f"\n=== {d.name} @ 0x{d.inferred.address:X} "
                f"({d.inferred.size}b) [{d.declared.file}:{d.declared.line}]  "
                f"[{tag}]  lifted-callers={lc}"
            )
            typer.echo(d.render(declared_map=declared))

        # Summary
        n_diff = sum(1 for d in diffs if d.has_diff)
        n_stub = sum(1 for d in diffs if d.declared.is_stub)
        n_func = len(diffs) - n_stub
        n_with_lifted_callers = sum(1 for d in diffs if _lifted_caller_count(d) > 0)
        typer.echo(
            f"\n--- summary: {len(diffs)} reported "
            f"({n_func} FUNC / {n_stub} STUB), "
            f"{n_diff} with mismatches, "
            f"{n_with_lifted_callers} consumed by ≥1 lifted caller ---"
        )
        return

    if not name:
        typer.echo("error: provide a function name or --all", err=True)
        raise typer.Exit(1)

    typer.echo(cli_inferred_sig(name))
    # Also try the comparison.
    try:
        declared = scan_declared_sigs()
        d = compare_sig(name, declared)
    except KeyError:
        return
    typer.echo("")
    typer.echo(d.render(declared_map=declared))
