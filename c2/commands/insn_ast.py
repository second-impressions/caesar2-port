"""Structured instruction operands for rule-hint detectors.

The diff rows that ``decomp_verify`` hands to ``rule_hints.detect_hints``
carry the raw instruction bytes (``InsnT = (rel_addr, size, raw, asm_text)``).
Historically detectors parsed the rendered ``asm_text`` with regexes; this
module instead re-decodes the RAW BYTES with capstone ``detail=True`` and
exposes the operands structurally — the instruction's AST:

  * ``Op(kind="reg", reg="edx", size=4)``
  * ``Op(kind="imm", imm=0x14, size=4)``
  * ``Op(kind="mem", base="eax", index="edx", scale=8, disp=0x496b4, size=1)``

No text parsing, no regex: register identity, operand width, SIB scale,
displacement and immediates all come from capstone's decoder, which is the
same decoder that produced the bytes' rendering in the first place.

Decoding is memoised on ``(raw, rel_addr)`` so repeated detector passes over
the same row list are free.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import capstone
from capstone import x86

# Capstone instruction tuple shape used by decomp_verify._render_diff:
#   (rel_addr, size, raw_bytes, "mnemonic op_str")
InsnT = tuple[int, int, bytes, str]


@dataclass(frozen=True)
class Op:
    kind: str            # "reg" | "imm" | "mem"
    reg: str = ""        # kind == "reg"
    imm: int = 0         # kind == "imm"
    base: str = ""       # kind == "mem"
    index: str = ""      # kind == "mem"
    scale: int = 1       # kind == "mem"
    disp: int = 0        # kind == "mem"
    size: int = 0        # operand width in BYTES (1/2/4)

    @property
    def is_reg(self) -> bool:
        return self.kind == "reg"

    @property
    def is_imm(self) -> bool:
        return self.kind == "imm"

    @property
    def is_mem(self) -> bool:
        return self.kind == "mem"


@dataclass(frozen=True)
class Insn:
    mnemonic: str
    ops: tuple[Op, ...]
    addr: int            # rel offset within the compared function
    size: int

    def op(self, i: int) -> Op | None:
        return self.ops[i] if i < len(self.ops) else None


_md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_md.detail = True


@lru_cache(maxsize=65536)
def _decode_raw(raw: bytes, addr: int) -> Insn | None:
    try:
        ci = next(_md.disasm(raw, addr))
    except StopIteration:
        return None
    ops: list[Op] = []
    for o in ci.operands:
        if o.type == x86.X86_OP_REG:
            ops.append(Op("reg", reg=ci.reg_name(o.reg), size=o.size))
        elif o.type == x86.X86_OP_IMM:
            ops.append(Op("imm", imm=o.imm, size=o.size))
        elif o.type == x86.X86_OP_MEM:
            ops.append(Op(
                "mem",
                base=ci.reg_name(o.mem.base) if o.mem.base else "",
                index=ci.reg_name(o.mem.index) if o.mem.index else "",
                scale=o.mem.scale,
                disp=o.mem.disp,
                size=o.size,
            ))
    return Insn(ci.mnemonic, tuple(ops), addr, ci.size)


def decode(insn: InsnT | None) -> Insn | None:
    """Decode one verifier row tuple into a structured ``Insn`` (or None)."""
    if insn is None:
        return None
    rel, _size, raw, _asm = insn
    return _decode_raw(bytes(raw), rel)


# Register-class predicates (identity from capstone names, not text). --------

GPR32 = frozenset({"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp"})
BYTE_REGS = frozenset({"al", "ah", "bl", "bh", "cl", "ch", "dl", "dh"})
CALLEE_SAVE32 = frozenset({"ebx", "esi", "edi", "ebp"})
# __watcall args 2..4 (EAX excluded: it is also the return register, so a
# one-sided `xor eax, eax` is usually return-value setup, not arg staging).
WATCALL_ARG_REGS_2_4 = frozenset({"edx", "ebx", "ecx"})


def is_reg_self_xor(insn: Insn | None) -> str | None:
    """``xor r, r`` -> the register name, else None."""
    if insn is None or insn.mnemonic != "xor" or len(insn.ops) != 2:
        return None
    a, b = insn.ops
    if a.is_reg and b.is_reg and a.reg == b.reg:
        return a.reg
    return None


def is_mov_reg_reg(insn: Insn | None, width: int | None = None
                   ) -> tuple[str, str] | None:
    """``mov rDST, rSRC`` -> (dst, src), optionally filtered by width."""
    if insn is None or insn.mnemonic != "mov" or len(insn.ops) != 2:
        return None
    a, b = insn.ops
    if not (a.is_reg and b.is_reg):
        return None
    if width is not None and (a.size != width or b.size != width):
        return None
    return a.reg, b.reg


def is_mov_reg_imm(insn: Insn | None) -> tuple[str, int] | None:
    """``mov r, IMM`` -> (reg, imm)."""
    if insn is None or insn.mnemonic != "mov" or len(insn.ops) != 2:
        return None
    a, b = insn.ops
    if a.is_reg and b.is_imm:
        return a.reg, b.imm
    return None


def is_mov_reg_mem(insn: Insn | None) -> tuple[str, Op] | None:
    """``mov r, [mem]`` -> (reg, mem-op)."""
    if insn is None or insn.mnemonic != "mov" or len(insn.ops) != 2:
        return None
    a, b = insn.ops
    if a.is_reg and b.is_mem:
        return a.reg, b
    return None


def is_mov_mem_reg(insn: Insn | None) -> tuple[Op, str] | None:
    """``mov [mem], r`` -> (mem-op, reg)."""
    if insn is None or insn.mnemonic != "mov" or len(insn.ops) != 2:
        return None
    a, b = insn.ops
    if a.is_mem and b.is_reg:
        return a, b.reg
    return None


def is_cmp_reg_imm(insn: Insn | None) -> tuple[str, int] | None:
    """``cmp r, IMM`` -> (reg, imm)."""
    if insn is None or insn.mnemonic != "cmp" or len(insn.ops) != 2:
        return None
    a, b = insn.ops
    if a.is_reg and b.is_imm:
        return a.reg, b.imm
    return None


def jump_target(insn: Insn | None) -> int | None:
    """Absolute (function-relative) target of a jmp/jcc, else None."""
    if insn is None or len(insn.ops) != 1:
        return None
    if insn.mnemonic != "jmp" and not insn.mnemonic.startswith("j"):
        return None
    o = insn.ops[0]
    return o.imm if o.is_imm else None
