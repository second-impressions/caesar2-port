"""Rule 25 - Byte-offset cast vs cell-index access for typed arrays.

## Trigger

When `city_map` is declared `struct city_cell city_map[6400]`
(20-byte cells) and a caller already holds the **byte offset**
(`ref = (y * 80 + x) * 20`), Watcom 10.0a generates different
code depending on how the field is expressed in C:

| C expression                                                    | x86 codegen                                                   |
|-----------------------------------------------------------------|---------------------------------------------------------------|
| `((struct city_cell *)((char *)city_map + ref))->terrain`       | `mov al, byte ptr [eax + city_map + 1]` (6 bytes)             |
| `city_map[cell].terrain` (`cell` = `ref / 20`)                  | `mov al, byte ptr [eax*4 + city_map + 1]` after `shl/add` mul (7 bytes inside, plus 5 bytes setup) |

PS.EXE consistently uses the byte-offset cast form; cell-index
access forces the back-end to compute `cell * 20` via shift+add
(non-power-of-2 stride), bloating the function by ~10 bytes.

## Mechanism

Same machinery as Rule 21: the addressing-mode synthesiser in
`bld/cg/intel/c/x86esc.c` folds a constant displacement into a
`[reg + disp]` mode when the byte offset is already register-
resident.

The cast `((struct city_cell *)((char *)city_map + ref))->terrain`
gives the back-end an `O_PTR(O_PLUS(BASE, REF))` tree at the
deref node.  `BASE` is a labelled symbol (folded into the fixup
displacement); `REF` is in EAX.  The constant field offset (`+ 1`
for `.terrain`) folds in too, giving one `mov [eax + base+1]`.

`city_map[cell].terrain` gives `O_PTR(O_PLUS(O_TIMES(cell, 20),
BASE), 1)`.  Without `-ol+` (loop strength reduction), the
back-end emits the multiplication as
``mov edx, eax; shl eax, 2; add eax, edx; mov al, [eax*4 + base + 1]``
(distributes 20 = 4 * 5 across the SIB scale and a shift+add).

## Right C: byte-offset cast

```c
terrain = ((struct city_cell *)((char *)city_map + ref))->terrain;
((struct city_cell *)((char *)city_map + ref))->citizen_a = 0;
```

When both `cell` and `ref` are needed in the function:

```c
int cell = y * 80 + x;
int ref  = cell * 20;
terrain = city_map[cell].terrain;          /* CSE folds into ref */
citizen_list[n].map_ref = ref;
```

Watcom recognises `cell * 20` and `ref` as the same value,
keeps it in one register, and emits the `[reg + base + N]` form.

## Why not `-ol+` (loop strength reduction)?

`-ol+` would turn cell-index loops into byte-stride pointers
matching PS.EXE.  But it also REGRESSES many other byte-exact
functions (~28 across the project).  PS.EXE was not compiled
with `-ol+`; the unrolled clear loops in PS were authored by
hand using the cast pattern.

## Verified on

  * `check_citizen_list`, `clear_all_cm` and other
     `city_map`-heavy functions.
  * `tests/oracle/test_rule_25_byte_offset_vs_cell_index.py` -
     4 tests: byte-offset cast emits a single 6-byte indexed
     load; cell-index emits the same load wrapped in shift+add
     stride multiplication; byte-offset is at least 8 bytes
     shorter; cell-index uses SIB scaling (`*4`) in the indexed
     mode, byte-offset uses plain `[eax + disp]`.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "struct city_cell { unsigned char a; unsigned char terrain; unsigned char b[18]; };\n"
    "struct city_cell city_map[6400];\n"
)


_BYTE_OFFSET = """\
struct city_cell { unsigned char a; unsigned char terrain; unsigned char b[18]; };
extern struct city_cell city_map[6400];
int f(int ref) {
    return ((struct city_cell *)((char *)city_map + ref))->terrain;
}
"""

_CELL_INDEX = """\
struct city_cell { unsigned char a; unsigned char terrain; unsigned char b[18]; };
extern struct city_cell city_map[6400];
int f(int cell) {
    return city_map[cell].terrain;
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, b.output
    return b.function("f")


def _has_indexed_byte_load_no_sib(fn):
    """True if the function has `mov al, byte ptr [eax + ...]` (no SIB)."""
    return any(
        i.mnemonic == "mov"
        and i.op_str.startswith("al, byte ptr [")
        and "*" not in i.op_str
        for i in fn.insns
    )


def _has_indexed_byte_load_with_sib(fn, scale=4):
    return any(
        i.mnemonic == "mov"
        and i.op_str.startswith("al, byte ptr [")
        and f"*{scale}" in i.op_str
        for i in fn.insns
    )


def _count_shifts_or_mul(fn):
    return sum(
        1 for i in fn.insns if i.mnemonic in ("shl", "shr", "imul", "add")
        and not i.op_str.startswith("esp")
        and not i.op_str.startswith("eax, 0xff")  # exclude the zero-extend
    )


def test_byte_offset_uses_plain_indexed_load(watcom_10_0a):
    """Byte-offset cast emits `mov al, byte ptr [eax + ...]` with no SIB."""
    fn = _compile(_BYTE_OFFSET, watcom_10_0a)
    assert _has_indexed_byte_load_no_sib(fn), fn.disasm_text()
    # And no SIB scaling
    assert not _has_indexed_byte_load_with_sib(fn, scale=4), fn.disasm_text()


def test_cell_index_uses_sib_scaling(watcom_10_0a):
    """Cell-index access emits `mov al, byte ptr [eax*4 + ...]` (SIB)."""
    fn = _compile(_CELL_INDEX, watcom_10_0a)
    assert _has_indexed_byte_load_with_sib(fn, scale=4), fn.disasm_text()


def test_byte_offset_at_least_eight_bytes_shorter(watcom_10_0a):
    """Byte-offset form is much smaller than cell-index for 20-byte
    stride (non-power-of-2)."""
    bo = _compile(_BYTE_OFFSET, watcom_10_0a)
    ci = _compile(_CELL_INDEX, watcom_10_0a)
    assert ci.size() >= bo.size() + 8, (
        f"expected cell-index >= byte-offset + 8; "
        f"byte_offset={bo.size()}, cell_index={ci.size()}"
    )


def test_cell_index_emits_stride_multiplication(watcom_10_0a):
    """Cell-index form emits at least one ``shl`` (the *4 part of the
    20 = 4 * 5 strength-reduction).  Byte-offset form has none."""
    bo = _compile(_BYTE_OFFSET, watcom_10_0a)
    ci = _compile(_CELL_INDEX, watcom_10_0a)
    n_shl_bo = sum(1 for i in bo.insns if i.mnemonic == "shl")
    n_shl_ci = sum(1 for i in ci.insns if i.mnemonic == "shl")
    assert n_shl_bo == 0, bo.disasm_text()
    assert n_shl_ci >= 1, ci.disasm_text()
