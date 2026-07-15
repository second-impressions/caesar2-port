"""Rule 21 - Indexed-array folding only at the deref site.

## Trigger

A byte-array offset expression
``(char *)base + idx * STRIDE + FIELD_OFFSET`` collapses into a
single ``[reg + disp]`` addressing mode **only if the entire
expression is the operand of a single deref** - not if it\u2019s
pinned to a pointer local first.

  * **Direct deref** (folded, fewer bytes):
    ```c
    *(short *)((char *)ambient_list + idx * 70 + 4) = value;
    ```
    -> ``imul eax, eax, 0x46; mov [eax + base+4], dx`` (11 bytes;
    the `base + 4` displacement lives in one 4-byte fixup).
  * **Pinned through a local pointer** (un-folded):
    ```c
    short *row = (short *)((char *)ambient_list + idx * 70 + 4);
    *row = value;
    ```
    -> ``imul eax, eax, 0x46; add eax, base; add eax, 4;
    mov [eax], dx`` (15 bytes; the base and the +4 are
    materialised separately).

The **4-byte difference** comes from the two extra `add`
instructions in the un-folded form.  Watcom\u2019s addressing-mode
synthesis runs at the deref; splitting the address through a
local type-laundering pointer breaks the fold.

## Applies to

Any struct stride that isn\u2019t a power of 2 (8, 16, 32 are folded
as `eax*N`; 70, 175, 58, etc. need the explicit displacement and
benefit from the deref-site fold).  For power-of-2 strides the
back-end can use `[base + eax*scale]` directly without fold.

## Mechanism

The back-end\u2019s addressing-mode synthesiser
(`bld/cg/intel/c/x86esc.c`'s `OutMem*` routines) walks the
operand tree of an `O_PTR` (deref) node, identifying the base
register, an index*scale term, and a constant displacement.  When
the deref is on a complete expression, all three components are
visible at once and the synthesiser folds them into one
addressing mode.

When a local pointer is assigned the partial address first, the
local pointer\u2019s register holds the *fully-computed* address; the
deref on the local sees only ``*reg`` with no displacement, so
the synthesiser has nothing to fold.  The address-computation
side now lives at the assignment site, where each `add` becomes
a separate instruction.

## Right C: deref the full expression

```c
*(short *)((char *)ambient_list + idx * 70 + 4) = some_value;
```

## Wrong C: launder through a local pointer

```c
short *row = (short *)((char *)ambient_list + idx * 70 + 4);
*row = some_value;
```

## Verified on

  * `set_ambient_minimum` (commit `a29fed1`).
  * `tests/oracle/test_rule_21_indexed_array_folding.py` - 4
     tests: direct-deref produces a single store with folded
     `[eax + base+4]`; via-local emits two extra `add`
     instructions; via-local is at least 4 bytes longer; both
     contain the same `imul eax, eax, 70`.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "struct ambient_rec { char data[70]; };\n"
    "struct ambient_rec ambient_list[10];\n"
)


_VIA_LOCAL = """\
struct ambient_rec { char data[70]; };
extern struct ambient_rec ambient_list[10];
void f(int idx, short some_value) {
    short *row = (short *)((char *)ambient_list + idx * 70 + 4);
    *row = some_value;
}
"""

_FOLDED = """\
struct ambient_rec { char data[70]; };
extern struct ambient_rec ambient_list[10];
void f(int idx, short some_value) {
    *(short *)((char *)ambient_list + idx * 70 + 4) = some_value;
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, b.output
    return b.function("f")


def _count_add_imm(fn):
    return sum(
        1
        for i in fn.insns
        if i.mnemonic == "add"
        and "," in i.op_str
        and "[" not in i.op_str
        and "ptr" not in i.op_str.split(",")[1]
    )


def test_folded_form_emits_one_store_no_extra_add(watcom_10_0a):
    """Direct-deref folds base+offset into a single store."""
    fn = _compile(_FOLDED, watcom_10_0a)
    n_add_imm = _count_add_imm(fn)
    assert n_add_imm == 0, (
        f"expected no `add reg, imm` in folded form; got {n_add_imm}\n"
        f"{fn.disasm_text()}"
    )
    # Single word ptr store
    n_word_stores = sum(
        1 for i in fn.insns
        if i.mnemonic == "mov" and i.op_str.startswith("word ptr [")
    )
    assert n_word_stores == 1, fn.disasm_text()


def test_via_local_form_emits_two_extra_adds(watcom_10_0a):
    """Via-local form emits two `add eax, imm` instructions: one for
    the array base (fixup) and one for the +4 field offset."""
    fn = _compile(_VIA_LOCAL, watcom_10_0a)
    n_add_imm = _count_add_imm(fn)
    assert n_add_imm == 2, (
        f"expected 2 `add reg, imm` in via-local form; got {n_add_imm}\n"
        f"{fn.disasm_text()}"
    )


def test_via_local_at_least_four_bytes_longer(watcom_10_0a):
    """Via-local is at least 4 bytes longer than the folded form."""
    folded = _compile(_FOLDED, watcom_10_0a)
    via_local = _compile(_VIA_LOCAL, watcom_10_0a)
    assert via_local.size() >= folded.size() + 4, (
        f"expected via-local at least 4 bytes longer; "
        f"folded={folded.size()}, via_local={via_local.size()}"
    )


def test_both_forms_share_the_imul(watcom_10_0a):
    """Both forms compute idx*70 the same way (`imul eax, eax, 0x46`).
    The byte-difference is purely in how the result is combined with
    the array base and field offset."""
    folded = _compile(_FOLDED, watcom_10_0a)
    via_local = _compile(_VIA_LOCAL, watcom_10_0a)
    for fn in (folded, via_local):
        assert any(
            i.mnemonic == "imul" and i.op_str == "eax, eax, 0x46"
            for i in fn.insns
        ), fn.disasm_text()
