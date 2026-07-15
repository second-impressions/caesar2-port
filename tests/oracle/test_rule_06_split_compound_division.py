"""Rule 6 - Split compound division into two assignment statements.

## Trigger

Compound chained divides like ``estimate = a / 12 / 100`` come out as
*one* intermediate-store-free instruction stream:

    mov  ebx, 12
    mov  eax, [a]
    mov  edx, eax
    sar  edx, 31
    idiv ebx              ; first divide; result in EAX
    mov  edx, eax
    mov  ebx, 100
    sar  edx, 31
    idiv ebx              ; second divide; result in EAX
    mov  [estimate], eax  ; only ONE store

PS.EXE shows the **two-store** variant for several tax / economic
formulas:

    mov  edx, [a]
    mov  ebx, 12
    mov  eax, edx
    sar  edx, 31
    idiv ebx
    mov  [estimate], eax  ; <- intermediate store
    mov  ebx, 100
    mov  edx, eax
    sar  edx, 31
    idiv ebx
    mov  [estimate], eax  ; <- final store

That two-store shape comes from writing the divide in two assignment
statements:

    estimate = projected / 12;       /* store 1 */
    estimate /= 100;                 /* store 2 */

This is **Rule 3 applied to chained divides** - the operator on the
second statement doesn't matter, only the count of assignment
statements to the global.  See Rule 3 for the underlying
`N_MEMORY` dead-store-elimination policy
(`bld/cg/c/insdead.c:269`).

## Cost

The two-statement form is +6 bytes per chained divide compared to
the single-expression form: each extra `mov [imm32], reg` is 6
bytes including the 4-byte fixup.

## Why this matters

PS.EXE`s tax-estimate functions (`collect_taxes_estimate`,
`collect_industry_taxes_estimate`, etc.) use the same shape every
time: two visible stores per chained divide.  When a diff shows
the intermediate store, the C source had two assignment statements,
not a single expression.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = "int projected; int estimate;\n"

_SINGLE_EXPRESSION = """\
extern int projected, estimate;
void f(void) { estimate = (projected / 12) / 100; }
"""

_TWO_STATEMENTS_COMPOUND = """\
extern int projected, estimate;
void f(void) {
    estimate = projected / 12;
    estimate /= 100;
}
"""

_TWO_STATEMENTS_PLAIN = """\
extern int projected, estimate;
void f(void) {
    estimate = projected / 12;
    estimate = estimate / 100;
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _count_stores_to_estimate(fn):
    """Count `mov dword ptr [0], reg` (the `estimate` global at offset 0)."""
    n = 0
    for i in fn.insns:
        if (
            i.mnemonic == "mov"
            and i.op_str.startswith("dword ptr [0]")
            and ", " in i.op_str
        ):
            n += 1
    return n


def test_single_expression_emits_one_store(watcom_10_0a):
    """``(projected / 12) / 100`` chains divides in registers; one store."""
    fn = _compile(_SINGLE_EXPRESSION, watcom_10_0a)
    assert _count_stores_to_estimate(fn) == 1, fn.disasm_text()
    # Two idivs (the chain), only one of them is followed by a store
    idivs = [k for k, i in enumerate(fn.insns) if i.mnemonic == "idiv"]
    assert len(idivs) == 2, fn.disasm_text()


def test_two_statements_compound_emits_two_stores(watcom_10_0a):
    """``estimate = projected/12; estimate /= 100;`` emits TWO stores."""
    fn = _compile(_TWO_STATEMENTS_COMPOUND, watcom_10_0a)
    assert _count_stores_to_estimate(fn) == 2, fn.disasm_text()


def test_two_statements_plain_emits_two_stores(watcom_10_0a):
    """``estimate = projected/12; estimate = estimate/100;`` also emits TWO stores.

    Confirms the operator on the second statement doesn't matter.
    """
    fn = _compile(_TWO_STATEMENTS_PLAIN, watcom_10_0a)
    assert _count_stores_to_estimate(fn) == 2, fn.disasm_text()


def test_two_statement_forms_are_byte_identical(watcom_10_0a):
    """``= /= ;`` and ``= = / ;`` produce byte-identical output."""
    a = _compile(_TWO_STATEMENTS_COMPOUND, watcom_10_0a)
    b = _compile(_TWO_STATEMENTS_PLAIN, watcom_10_0a)
    assert a.size() == b.size(), (
        f"size mismatch: compound={a.size()} plain={b.size()}"
    )
    a_masked = bytes(0 if (a.base + k) in a.fixups else x
                     for k, x in enumerate(a.bytes_))
    b_masked = bytes(0 if (b.base + k) in b.fixups else x
                     for k, x in enumerate(b.bytes_))
    assert a_masked == b_masked, (
        f"bytes differ:\n--- COMPOUND ---\n{a.disasm_text()}\n"
        f"--- PLAIN ---\n{b.disasm_text()}"
    )


def test_split_form_is_six_bytes_longer(watcom_10_0a):
    """Splitting into two statements costs exactly +6 bytes (one extra `mov [imm32], reg`)."""
    one = _compile(_SINGLE_EXPRESSION, watcom_10_0a)
    two = _compile(_TWO_STATEMENTS_COMPOUND, watcom_10_0a)
    delta = two.size() - one.size()
    assert delta == 6, (
        f"expected +6 bytes; got {delta}\n"
        f"--- ONE ({one.size()}b) ---\n{one.disasm_text()}\n"
        f"--- TWO ({two.size()}b) ---\n{two.disasm_text()}"
    )
