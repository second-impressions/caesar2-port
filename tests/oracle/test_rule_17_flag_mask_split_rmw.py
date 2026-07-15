"""Rule 17 - Flag-mask split-RMW emits an extra register copy.

## Trigger

When a flag byte is updated by clearing some bits and setting
others, the C source can be written two ways:

  * **Combined**: a single statement
    ``x = (x & MASK) | BITS;``
  * **Split**: two statements
    ``x &= MASK; x |= BITS;``

The two forms produce **different bytes**.  PS.EXE's pattern for
the SPLIT form contains an **extra register-copy** between the
AND and the OR:

```
mov  rl1, [x]
and  rl1, MASK
mov  rl2, rl1   ; <-- extra copy to a SECOND register
or   rl2, BITS
mov  [x], rl2
```

versus the COMBINED form's tighter 4-instruction sequence:

```
mov  rl, [x]
and  rl, MASK
or   rl, BITS
mov  [x], rl
```

The extra `mov rl2, rl1` is the rule's diagnostic - if PS.EXE
shows that copy at a flag-update site, the source had two separate
statements, not the combined expression.

## Two sub-shapes (struct field vs plain global)

  * **Struct field / array element**: SPLIT emits exactly the
    doc's 5-instruction sequence with one memory write at the end.
    The compiler keeps both intermediate values in callee-saved
    BL/BH halves of EBX.
  * **Plain global byte**: SPLIT also emits **two memory writes**
    (one per source statement, by Rule 3), so the full sequence is
    6 instructions.  The "copy to second register" is still
    present.

In both shapes the COMBINED form folds to 4 instructions with one
register and one memory write.

## Mechanism

`bld/cc/c/cgen.c:1357-1369` handles `OPR_AND_EQUAL` and `OPR_OR_EQUAL`
by calling `CGPreGets(CGOperator[opr], lvalue, rvalue, ...)`.
`CGPreGets` -> `TGPreGets` -> `DoTGPreGets` (`bld/cg/c/tree.c:1102`)
builds a `TN_PRE_GETS` tree node per source statement.

Two consecutive `TN_PRE_GETS` nodes feed two distinct IR
statements.  Rule 3's `CheckUseful` keeps the per-statement
`N_MEMORY` writes alive.  Inside each statement, the back-end
allocates a destination register that's distinct from the source
register so the SOURCE remains observable post-statement (the
compiler treats the post-AND value as potentially live for the
next reference); on a single combined expression no such boundary
exists, so the back-end folds AND/OR into one register.

## Right C: write what PS.EXE shows

If the diff shows the 5-instruction pattern with the
`mov rl2, rl1` copy, write two statements:

```c
army_list[army_no].flags &= 0xFC;
army_list[army_no].flags |= 1;
```

If the diff shows the 4-instruction tight form, write the
combined expression:

```c
army_list[army_no].flags = (army_list[army_no].flags & 0xFC) | 1;
```

## Verified on

  * `sa01_wait` in `int_c2.c` (commit `c73dee1`).
  * `tests/oracle/test_rule_17_flag_mask_split_rmw.py` - 4 tests:
     struct-field SPLIT shows 5-insn pattern with extra register
     copy; struct-field COMBINED shows 4-insn pattern without copy;
     plain-global SPLIT also has the extra copy plus two memory
     writes (Rule 3); COMBINED form is byte-shorter than SPLIT in
     both shapes.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_FIELD_DEFS = (
    "struct rec { char name[8]; unsigned char flags; };\n"
    "struct rec army_list[10];\n"
    "int army_no;\n"
)


_FIELD_COMBINED = """\
struct rec { char name[8]; unsigned char flags; };
extern struct rec army_list[10];
extern int army_no;
void f(void) {
    army_list[army_no].flags = (army_list[army_no].flags & 0xFC) | 1;
}
"""

_FIELD_SPLIT = """\
struct rec { char name[8]; unsigned char flags; };
extern struct rec army_list[10];
extern int army_no;
void f(void) {
    army_list[army_no].flags &= 0xFC;
    army_list[army_no].flags |= 1;
}
"""


_GLOBAL_DEFS = "unsigned char flags;\n"


_GLOBAL_COMBINED = """\
extern unsigned char flags;
void f(void) { flags = (flags & 0xFC) | 1; }
"""

_GLOBAL_SPLIT = """\
extern unsigned char flags;
void f(void) { flags &= 0xFC; flags |= 1; }
"""


def _compile(source, defs, image):
    b = compile_snippet(source, image=image, extern_defs=defs)
    assert b.ok, b.output
    return b.function("f")


def _count_byte_mem_writes(fn):
    """Count `mov byte ptr [...], <reg>` instructions (the per-statement
    Rule-3 memory writes)."""
    return sum(
        1
        for i in fn.insns
        if i.mnemonic == "mov"
        and i.op_str.startswith("byte ptr [")
        and not i.op_str.endswith(", 0")
    )


def _has_intra_rmw_register_copy(fn):
    """True when the function contains a ``mov rXX, rYY`` (8-bit reg
    only, no memory) sandwiched between AND and OR.

    This is the Rule 17 diagnostic: an extra register copy used to keep
    the post-AND value alive while the post-OR value lives in a different
    register.
    """
    seen_and = False
    for i in fn.insns:
        if i.mnemonic == "and":
            seen_and = True
            continue
        if seen_and and i.mnemonic == "or":
            return False  # no copy between and/or - combined form
        if (
            seen_and
            and i.mnemonic == "mov"
            and "byte ptr" not in i.op_str
            and "dword ptr" not in i.op_str
            and "[" not in i.op_str
        ):
            # 8-bit reg-to-reg between and/or
            return True
    return False


def test_field_split_emits_extra_register_copy(watcom_10_0a):
    """SPLIT form on a struct field shows the 5-insn pattern with the copy."""
    fn = _compile(_FIELD_SPLIT, _FIELD_DEFS, watcom_10_0a)
    assert _has_intra_rmw_register_copy(fn), (
        f"expected mov rl, rl between and/or:\n{fn.disasm_text()}"
    )


def test_field_combined_no_register_copy(watcom_10_0a):
    """COMBINED form on a struct field has no copy between AND and OR."""
    fn = _compile(_FIELD_COMBINED, _FIELD_DEFS, watcom_10_0a)
    assert not _has_intra_rmw_register_copy(fn), (
        f"expected NO copy between and/or:\n{fn.disasm_text()}"
    )


def test_global_split_has_two_memory_writes(watcom_10_0a):
    """SPLIT on a plain global emits TWO `mov byte ptr [g], reg` writes
    (Rule 3 cooperating with Rule 17)."""
    fn = _compile(_GLOBAL_SPLIT, _GLOBAL_DEFS, watcom_10_0a)
    n = _count_byte_mem_writes(fn)
    assert n == 2, (
        f"expected 2 byte memory writes (one per source statement); got {n}\n"
        f"{fn.disasm_text()}"
    )
    # And the extra register-copy is still there
    assert _has_intra_rmw_register_copy(fn), fn.disasm_text()


def test_combined_strictly_shorter_than_split(watcom_10_0a):
    """COMBINED is strictly smaller than SPLIT in both struct-field and
    plain-global cases."""
    f_combined = _compile(_FIELD_COMBINED, _FIELD_DEFS, watcom_10_0a)
    f_split = _compile(_FIELD_SPLIT, _FIELD_DEFS, watcom_10_0a)
    g_combined = _compile(_GLOBAL_COMBINED, _GLOBAL_DEFS, watcom_10_0a)
    g_split = _compile(_GLOBAL_SPLIT, _GLOBAL_DEFS, watcom_10_0a)
    assert f_combined.size() < f_split.size(), (
        f"struct-field: combined={f_combined.size()} split={f_split.size()}"
    )
    assert g_combined.size() < g_split.size(), (
        f"global: combined={g_combined.size()} split={g_split.size()}"
    )
