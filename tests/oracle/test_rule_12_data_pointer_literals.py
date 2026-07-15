"""Rule 12 - Data-pointer literals look like immediate dwords with a fixup mask.

## Trigger

The verifier and oracle both mask **fixup bytes** as `??` in their
diff/disasm output.  When a `mov reg, IMM32` instruction shows all
four immediate bytes masked, the immediate is a *pointer to a data
symbol*, not an integer constant.

| Asm bytes              | Source                              |
|------------------------|-------------------------------------|
| `b8 40 a3 01 00`       | integer literal `0x1A340`           |
| `b8 ?? ?? ?? ??`       | address of a labelled data symbol   |

Both encode as the same 5-byte opcode (`b8` for `mov eax, imm32`),
but the linker emits a fixup record for the symbol-address case.
The fixup records survive into the LE\u2019s fixup table; the verifier\u2019s
fixup parser tags those byte offsets, and the diff renders them as
`??`.

## Mechanism

Whenever the IR references a labelled symbol (data or code), the
back-end emits the placeholder bytes inline and queues an
`F_OFFSET` fixup with the symbol\u2019s label handle.
``OutCodeDisp`` / similar in ``bld/cg/intel/c/x86esc.c:268+`` does
the bookkeeping; the linker walks the fixup queue and patches the
real address at link time.

For our purposes the rule is interpretive:

  * Diff column shows `b8 ?? ?? ?? ??` for `mov reg, IMM32`
     -> the original C source had `(int)&symbol` (or just `symbol`
     for an array), not a literal integer.
  * Diff column shows `b8 40 a3 01 00` (or any literal byte
     pattern) -> the original C source had a literal integer.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "int filename_buf[256];\n"
    "int take(int v) { (void)v; return 0; }\n"
)


_INT_LITERAL = """\
extern int filename_buf[256];
extern int take(int v);
void f(void) {
    take(0x1A340);
}
"""

_POINTER_LITERAL = """\
extern int filename_buf[256];
extern int take(int v);
void f(void) {
    take((int)filename_buf);
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _find_mov_eax_imm(fn):
    """Return the `mov eax, IMM32` instruction (5 bytes, opcode b8)."""
    for i in fn.insns:
        if (
            i.mnemonic == "mov"
            and i.size == 5
            and i.raw[0] == 0xB8
            and i.op_str.startswith("eax,")
        ):
            return i
    raise AssertionError(f"no `mov eax, imm32`:\n{fn.disasm_text()}")


def test_int_literal_has_no_fixups(watcom_10_0a):
    """An integer constant emits literal bytes with no fixup mask."""
    fn = _compile(_INT_LITERAL, watcom_10_0a)
    insn = _find_mov_eax_imm(fn)
    # Opcode b8 followed by 4 literal immediate bytes
    assert insn.fixup_mask == [False, False, False, False, False], (
        f"unexpected fixup mask {insn.fixup_mask} for integer literal:\n"
        f"  {insn.line}\n  bytes={insn.raw.hex()}"
    )
    # And the bytes are 40 a3 01 00 (little-endian 0x1A340)
    assert insn.raw[1:] == b"\x40\xa3\x01\x00", insn.raw.hex()


def test_pointer_literal_has_four_fixup_bytes(watcom_10_0a):
    """An address-of a labelled symbol emits the opcode + 4 fixup bytes."""
    fn = _compile(_POINTER_LITERAL, watcom_10_0a)
    insn = _find_mov_eax_imm(fn)
    # Opcode is real, immediate bytes are all fixup
    assert insn.fixup_mask == [False, True, True, True, True], (
        f"unexpected fixup mask {insn.fixup_mask} for pointer literal:\n"
        f"  {insn.line}"
    )


def test_both_forms_use_same_opcode_byte(watcom_10_0a):
    """`mov eax, imm32` opcode is `b8` in both forms - only the immediate
    bytes' fixup status differs.

    This is why a fully-masked `mov eax, IMM32` is the rule's tell:
    the opcode is identical, only the immediate bytes are different.
    """
    int_lit = _compile(_INT_LITERAL, watcom_10_0a)
    ptr_lit = _compile(_POINTER_LITERAL, watcom_10_0a)
    int_insn = _find_mov_eax_imm(int_lit)
    ptr_insn = _find_mov_eax_imm(ptr_lit)
    assert int_insn.raw[0] == 0xB8 == ptr_insn.raw[0]
    assert int_insn.size == 5 == ptr_insn.size


def test_fixup_mask_distinguishes_pointer_from_integer(watcom_10_0a):
    """The number of fixup bytes is the rule's discriminator.

    integer literal -> 0 fixup bytes in the immediate.
    pointer literal -> 4 fixup bytes in the immediate.
    """
    int_insn = _find_mov_eax_imm(_compile(_INT_LITERAL, watcom_10_0a))
    ptr_insn = _find_mov_eax_imm(_compile(_POINTER_LITERAL, watcom_10_0a))
    int_fixups_in_imm = sum(int_insn.fixup_mask[1:])  # skip opcode byte
    ptr_fixups_in_imm = sum(ptr_insn.fixup_mask[1:])
    assert int_fixups_in_imm == 0, int_insn.fixup_mask
    assert ptr_fixups_in_imm == 4, ptr_insn.fixup_mask
