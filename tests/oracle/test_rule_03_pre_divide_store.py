"""Rule 3 - "Pre-divide store": two assignment statements to a global.

## Trigger

When PS.EXE shows *two* `mov [global], reg` stores spanning a divide
(or any other compute), the original C had two distinct assignment
statements:

```c
current_gdp = sum;          // pre-divide store
current_gdp /= 4;           // post-divide store
```

The single-statement form `current_gdp = sum / 4;` emits only one
store - the post-divide one - because there's only one assignment
in the C source.

The compound `/=` is **not** required.  Watcom emits the same two
stores for any of:

  * `current_gdp = sum; current_gdp /= 4;`
  * `current_gdp = sum; current_gdp = sum / 4;`
  * `current_gdp = sum; current_gdp = current_gdp / 4;`

What matters is that the C source has two separate assignment
statements to the same global.

## Mechanism

`CheckUseful` in `bld/cg/c/insdead.c:269` unconditionally marks any
instruction whose result is `N_MEMORY` (i.e. a global) as useful:

```c
if( res != NULL ) {
    if( res->n.class == N_MEMORY || res->n.class == N_REGISTER ) {
        change |= MarkOpsUseful( ins );
        return( change );
    }
    ...
}
```

Compare to `N_TEMP` (named locals) which are only marked useful if
some downstream instruction has already marked them `VISITED` (i.e.
something reads the temp).  Globals never get the dead-store
treatment regardless of whether a later write overwrites them
before any read.

This is conservative dead-store elimination - Watcom doesn't try
to prove that no aliased pointer reads the global between the two
stores, so it preserves both.

## Why this matters

Whenever PS.EXE shows the pattern

```
mov [global], reg          ; pre-compute store
... compute ...            ; (reg still in flight)
mov [global], result       ; post-compute store
```

split the C into the two assignment statements PS.EXE clearly had.
This is a common shape in functions that compute and clamp:

```c
current_gdp = sum;
current_gdp = sum / 4;
if (current_gdp > 60) current_gdp = 60;   // third store from the clamp
```

PS.EXE's `adjust_proserity_criteria` at 0x557AF emits exactly this
three-store pattern.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_GLOBALS = """\
extern int current_gdp;
extern int average_pop_tax_denariis, average_pop_tax_asses;
"""

_SINGLE_STATEMENT = _GLOBALS + """\
void f(void) {
    int sum = average_pop_tax_denariis * 100 + average_pop_tax_asses;
    current_gdp = sum / 4;
}
"""

_TWO_STATEMENTS_COMPOUND = _GLOBALS + """\
void f(void) {
    int sum = average_pop_tax_denariis * 100 + average_pop_tax_asses;
    current_gdp = sum;
    current_gdp /= 4;
}
"""

_TWO_STATEMENTS_PLAIN = _GLOBALS + """\
void f(void) {
    int sum = average_pop_tax_denariis * 100 + average_pop_tax_asses;
    current_gdp = sum;
    current_gdp = sum / 4;
}
"""

_DEFS = "int current_gdp; int average_pop_tax_denariis, average_pop_tax_asses;\n"


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _count_stores_to_first_global(fn):
    """Count `mov dword ptr [imm], reg` instructions whose target is the
    primary global (offset 4 in our test, which is current_gdp)."""
    n = 0
    for i in fn.insns:
        if (
            i.mnemonic == "mov"
            and i.op_str.startswith("dword ptr [4]")
            and "," in i.op_str
        ):
            n += 1
    return n


def test_single_statement_emits_one_store(watcom_10_0a):
    """`current_gdp = sum / 4;` produces exactly ONE store to current_gdp."""
    fn = _compile(_SINGLE_STATEMENT, watcom_10_0a)
    assert _count_stores_to_first_global(fn) == 1, fn.disasm_text()


def test_two_statements_compound_emits_two_stores(watcom_10_0a):
    """`current_gdp = sum; current_gdp /= 4;` produces TWO stores."""
    fn = _compile(_TWO_STATEMENTS_COMPOUND, watcom_10_0a)
    assert _count_stores_to_first_global(fn) == 2, fn.disasm_text()


def test_two_statements_plain_emits_two_stores(watcom_10_0a):
    """`current_gdp = sum; current_gdp = sum / 4;` also produces TWO stores.

    The compound `/=` is not required - what matters is two distinct
    assignment statements.
    """
    fn = _compile(_TWO_STATEMENTS_PLAIN, watcom_10_0a)
    assert _count_stores_to_first_global(fn) == 2, fn.disasm_text()


def test_two_statement_forms_emit_identical_bytes(watcom_10_0a):
    """`= sum; /= 4;` and `= sum; = sum/4;` are byte-identical.

    Confirms the rule is purely about the count of assignment
    statements, not the operator on the second one.
    """
    a = _compile(_TWO_STATEMENTS_COMPOUND, watcom_10_0a)
    b = _compile(_TWO_STATEMENTS_PLAIN, watcom_10_0a)
    # Compare with fixup bytes masked (link addresses differ; codegen shouldn't).
    assert a.size() == b.size(), (
        f"size mismatch: compound={a.size()} plain={b.size()}\n"
        f"--- COMPOUND ---\n{a.disasm_text()}\n--- PLAIN ---\n{b.disasm_text()}"
    )
    a_bytes = bytes(0 if m else b for m, b in zip(
        [(a.base + k) in a.fixups for k in range(a.size())], a.bytes_,
    ))
    b_bytes = bytes(0 if m else b for m, b in zip(
        [(b.base + k) in b.fixups for k in range(b.size())], b.bytes_,
    ))
    assert a_bytes == b_bytes, (
        f"bytes differ:\n--- COMPOUND ---\n{a.disasm_text()}\n"
        f"--- PLAIN ---\n{b.disasm_text()}"
    )


def test_two_statement_form_is_six_bytes_longer_than_single(watcom_10_0a):
    """The extra `mov [global], reg` is 6 bytes (a3/89 + 4 fixup bytes + reg)."""
    one = _compile(_SINGLE_STATEMENT, watcom_10_0a)
    two = _compile(_TWO_STATEMENTS_COMPOUND, watcom_10_0a)
    delta = two.size() - one.size()
    assert delta == 6, (
        f"expected +6 bytes for the extra store; got {delta}\n"
        f"--- ONE ({one.size()}b) ---\n{one.disasm_text()}\n"
        f"--- TWO ({two.size()}b) ---\n{two.disasm_text()}"
    )
