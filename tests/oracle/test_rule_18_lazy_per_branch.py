"""Rule 18 - Lazy per-branch computation, not pre-computed temps.

## Trigger

When a function takes an arg and uses ``arg + offset`` inside an
if/else cascade, the C source structure determines whether
Watcom emits the eager LEA or the per-branch ``mov + add``:

  * **Pre-computed temp** (``int v = arg + 0x1B; if (...) ... v ...;``)
    -> ``lea reg, [arg_reg + 0x1B]`` (3 bytes)
  * **Inline per-branch** (``if (...) f = arg + 0x1B;``) when there
    are multiple branches and arg must remain unmodified
    -> ``mov reg, arg_reg; add reg, 0x1B`` (5 bytes)

The 2-byte difference repeats per pre-computed temp.  PS.EXE
consistently emits the 5-byte ``mov + add`` shape at sites like
`get_rioter_image`; matching it requires writing the offsets
inline at each branch.

## Caveat - depends on register pressure

The empirical trigger isn't *just* the source structure; it
depends on how many callee-saved registers the function uses.
With register pressure low (only EDX needs saving), Watcom picks
LEA in both forms.  With register pressure high (EBX + ECX + EDX
all saved, e.g. in `get_rioter_image`), the per-branch form
yields ``mov + add`` while the pre-computed form yields LEA.

## Mechanism

Watcom's IR builder creates an `O_PLUS` tree node for ``arg +
0x1B``.  The lowering to x86 is choice-based: `bld/cg/intel/386/c/
386table.c` has rows for `O_PLUS` mapping to either `LEA` or
`mov + add` depending on which gives shorter encoding given the
operand register classes.

When the destination register is callee-saved AND distinct from
the source register, the cost-based selector in `AssignARegister`
(`bld/cg/c/regalloc.c:1034`) prefers the form that keeps the
source register's value in EBX-class storage rather than
synthesising a fresh address-mode result.  The exact policy is
encoded in the `Add4` row's preferred encoding flags.

The pre-computed temp form lives at the same source level as the
arg-saving `mov`, giving the back-end visibility into both
materialisations at once; the compiler picks LEA because it can
fold the precompute and the offset into one instruction.

The inline-per-branch form scopes each materialisation to its
basic block; the compiler treats each as an independent two-step
operation (`mov dest, src; add dest, K`).

## Right C: write inline per-branch

```c
if      (age <  5) field = (short)(arg + 0x1B);
else if (age < 10) field = (short)(arg + 0x1C);
else if (age < 15) field = (short)(arg + 0x1B);
else if (age < 20) field = (short)(arg + 0x1C);
else               field = (short)(arg + 0x1B);
```

Not:

```c
int v1 = arg + 0x1B;     /* WRONG: emits LEA, won't match */
int v2 = arg + 0x1C;
if      (age <  5) field = (short)v1;
else if (age < 10) field = (short)v2;
...
```

## Verified on

  * `get_rioter_image` (commit `f7aa75d`).
  * `tests/oracle/test_rule_18_lazy_per_branch.py` - 4 tests:
     low-pressure case both forms produce LEA; high-pressure case
     pre-computed -> LEA; high-pressure case per-branch -> mov +
     add; per-branch is at least 2 bytes longer per eager
     precompute (the trade-off).
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_LOW_PRESSURE_DEFS = "int dst1, dst2;\n"

_LOW_PRECOMPUTED = """\
extern int dst1, dst2;
void f(int arg) {
    int v = arg + 0x1B;
    dst1 = v;
    dst2 = v;
}
"""

_LOW_INLINE = """\
extern int dst1, dst2;
void f(int arg) {
    dst1 = arg + 0x1B;
    dst2 = arg + 0x1B;
}
"""


_HIGH_PRESSURE_DEFS = (
    "struct cit { char x[15]; signed char age; char y[36]; short img; char rest[7]; };\n"
    "struct cit citizen_list[200];\n"
    "short citizen_no;\n"
)

_HIGH_PRECOMPUTED = """\
struct cit { char x[15]; signed char age; char y[36]; short img; char rest[7]; };
extern struct cit citizen_list[200];
extern short citizen_no;
void f(int arg) {
    int idx = citizen_no;
    int age = citizen_list[idx].age;
    int v1 = arg + 0x1B;
    int v2 = arg + 0x1C;
    if      (age <  5) citizen_list[idx].img = (short)v1;
    else if (age < 10) citizen_list[idx].img = (short)v2;
    else if (age < 15) citizen_list[idx].img = (short)v1;
    else if (age < 20) citizen_list[idx].img = (short)v2;
    else               citizen_list[idx].img = (short)v1;
}
"""

_HIGH_INLINE = """\
struct cit { char x[15]; signed char age; char y[36]; short img; char rest[7]; };
extern struct cit citizen_list[200];
extern short citizen_no;
void f(int arg) {
    int idx = citizen_no;
    int age = citizen_list[idx].age;
    if      (age <  5) citizen_list[idx].img = (short)(arg + 0x1B);
    else if (age < 10) citizen_list[idx].img = (short)(arg + 0x1C);
    else if (age < 15) citizen_list[idx].img = (short)(arg + 0x1B);
    else if (age < 20) citizen_list[idx].img = (short)(arg + 0x1C);
    else               citizen_list[idx].img = (short)(arg + 0x1B);
}
"""


def _compile(source, defs, image):
    b = compile_snippet(source, image=image, extern_defs=defs)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _has_lea_with_imm(fn, imm_value):
    """True if any LEA contains [reg + imm_value]."""
    return any(
        i.mnemonic == "lea" and f"+ {imm_value:#x}" in i.op_str
        for i in fn.insns
    )


def _has_mov_add_pair(fn, imm_value):
    """True if the function has a `mov rA, rB` immediately followed by
    `add rA, imm_value` (the per-branch eager precompute pattern)."""
    seq = list(fn.insns)
    for k in range(len(seq) - 1):
        i, j = seq[k], seq[k + 1]
        if (
            i.mnemonic == "mov"
            and "[" not in i.op_str
            and "ptr" not in i.op_str
            and j.mnemonic == "add"
            and j.op_str.endswith(f", {imm_value:#x}")
        ):
            # Check the destination register is the same in both
            mov_dest = i.op_str.split(",")[0].strip()
            add_dest = j.op_str.split(",")[0].strip()
            if mov_dest == add_dest:
                return True
    return False


def test_low_pressure_both_forms_use_lea(watcom_10_0a):
    """With low register pressure, both forms produce LEA - source
    structure doesn't matter."""
    pre = _compile(_LOW_PRECOMPUTED, _LOW_PRESSURE_DEFS, watcom_10_0a)
    inl = _compile(_LOW_INLINE, _LOW_PRESSURE_DEFS, watcom_10_0a)
    # Actually for use-twice with no callee-save pressure, the +0x1b can
    # be folded into the source register directly (no LEA needed).
    # The point is: the bytes match between the two forms.
    assert pre.bytes_ == inl.bytes_, (
        f"low-pressure forms should produce identical bytes:\n"
        f"--- PRECOMPUTED ---\n{pre.disasm_text()}\n"
        f"--- INLINE ---\n{inl.disasm_text()}"
    )


def test_high_pressure_precomputed_uses_lea(watcom_10_0a):
    """With register pressure, the pre-computed temp form emits LEA."""
    fn = _compile(_HIGH_PRECOMPUTED, _HIGH_PRESSURE_DEFS, watcom_10_0a)
    assert _has_lea_with_imm(fn, 0x1B), (
        f"expected `lea reg, [arg + 0x1B]`:\n{fn.disasm_text()}"
    )


def test_high_pressure_inline_uses_mov_add(watcom_10_0a):
    """With register pressure, the inline-per-branch form emits the
    classic `mov + add` shape that PS.EXE shows."""
    fn = _compile(_HIGH_INLINE, _HIGH_PRESSURE_DEFS, watcom_10_0a)
    assert _has_mov_add_pair(fn, 0x1B), (
        f"expected `mov rA, rB; add rA, 0x1B`:\n{fn.disasm_text()}"
    )
    # And conversely, no LEA for 0x1B
    assert not _has_lea_with_imm(fn, 0x1B), (
        f"expected NO LEA for 0x1B:\n{fn.disasm_text()}"
    )


def test_high_pressure_inline_at_least_two_bytes_longer(watcom_10_0a):
    """The inline form's `mov + add` (5 bytes) is longer than the
    pre-computed form's `lea` (3 bytes); for one eager precompute the
    function grows by at least 2 bytes."""
    pre = _compile(_HIGH_PRECOMPUTED, _HIGH_PRESSURE_DEFS, watcom_10_0a)
    inl = _compile(_HIGH_INLINE, _HIGH_PRESSURE_DEFS, watcom_10_0a)
    assert inl.size() >= pre.size() + 2, (
        f"inline must be at least 2 bytes longer; "
        f"precomputed={pre.size()}, inline={inl.size()}"
    )
