"""Rule 10 - Staged global RMW vs fused single-expression accumulation.

## Trigger

When PS.EXE shows a chain of memory writes to the same global

    mov   [global], reg              ; first partial
    ...
    add   [global], otherreg         ; subsequent partials touch memory
    ...
    add   [global], otherreg         ; ...

instead of one final store, the source used staged read-modify-write
on the destination:

```c
prosperity_rating  = pop_cap / 60;
prosperity_rating += current_gdp;
prosperity_rating += rolling_profit / 200;
```

The single-expression form

```c
prosperity_rating = pop_cap / 60 + current_gdp + rolling_profit / 200;
```

accumulates the partials in a register (callee-saved EBX or ECX) and
emits a single `mov [global], reg` at the end.

## Mechanism

The same chain of mechanisms as Rule 7 / Rule 7b composed:

  * `CGAssign` (`bld/cg/c/intrface.c:876`) emits one IR sequence per
     ``=`` statement in source order; the optimizer doesn't merge IR
     across statement boundaries.
  * Each `+=` statement matches the `Add4` optab row
     `(M, R, M, EQ_R1) -> G_MR2` (`bld/cg/intel/386/c/386table.c:142`),
     emitting `add [m], reg` (a single 6-byte RMW instruction).
  * `CheckUseful` (`bld/cg/c/insdead.c:269`) keeps every `N_MEMORY`
     store and RMW alive regardless of overwriting.

The fused form reaches the back-end as one IR tree; the back-end
allocates a register for the accumulator and emits register-to-
register adds with one final store, sparing N-1 of the memory
RMW operations.

## Cost

Total delta is moderate (5-byte saving for 3 statements collapsing
to 1 in our test) and comes from competing factors:

  * Each replaced `add [m], reg` (6 bytes) becomes `add reg, reg`
     (2 bytes), saving 4 bytes per RMW.
  * The fused form needs one additional final `mov [m], reg`
     (6 bytes).
  * The fused form may push an extra callee-saved register
     (the accumulator), adding 2 bytes.
  * The Rule 2 EAX-vs-EDX divide setup may shift by 1 byte.

For 3 statements: 2 RMWs eliminated (-8) + 1 final store (+6) +
1 extra reg save (+2) - 1 byte Rule 2 swap = -1?  In practice the
delta is 5 bytes for this test; the exact amount depends on how
many partials are involved and which dividend register Watcom
picks.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "int prosperity_rating;\n"
    "int pop_cap, current_gdp, rolling_profit;\n"
)


_STAGED = """\
extern int prosperity_rating;
extern int pop_cap, current_gdp, rolling_profit;
void f(void) {
    prosperity_rating  = pop_cap / 60;
    prosperity_rating += current_gdp;
    prosperity_rating += rolling_profit / 200;
}
"""


_FUSED = """\
extern int prosperity_rating;
extern int pop_cap, current_gdp, rolling_profit;
void f(void) {
    prosperity_rating = pop_cap / 60 + current_gdp + rolling_profit / 200;
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _writes_to_global(fn, addr_str):
    """Count memory-write ops to the global at offset `addr_str`.

    Includes both `mov [m], reg` and `add [m], reg` (RMW).
    """
    n = 0
    for i in fn.insns:
        if (
            i.mnemonic in ("mov", "add", "sub")
            and i.op_str.startswith(f"dword ptr [{addr_str}]")
            and ", " in i.op_str
            # Exclude memory loads (which would be `mov reg, dword ptr [m]`)
            # — but that's already excluded since we require op1 to start with the addr.
        ):
            n += 1
    return n


def test_staged_form_emits_three_global_writes(watcom_10_0a):
    """Three `+=`-style statements emit three memory-touching writes.

    `prosperity_rating` is at offset 8 in our test.  We see one `mov` and
    two `add` instructions all writing to `[8]`.
    """
    fn = _compile(_STAGED, watcom_10_0a)
    n = _writes_to_global(fn, "8")
    assert n == 3, f"expected 3 writes to [prosperity_rating]; got {n}\n{fn.disasm_text()}"


def test_fused_form_emits_one_global_write(watcom_10_0a):
    """Single fused expression emits exactly one memory write at the end."""
    fn = _compile(_FUSED, watcom_10_0a)
    n = _writes_to_global(fn, "8")
    assert n == 1, f"expected 1 write to [prosperity_rating]; got {n}\n{fn.disasm_text()}"


def test_staged_uses_memory_rmw_add(watcom_10_0a):
    """Staged form uses `add [m], reg` (the G_MR2 form)."""
    fn = _compile(_STAGED, watcom_10_0a)
    add_to_mem = sum(
        1 for i in fn.insns
        if i.mnemonic == "add" and i.op_str.startswith("dword ptr [8],")
    )
    assert add_to_mem == 2, (
        f"expected 2 `add [m], reg` instructions; got {add_to_mem}\n"
        f"{fn.disasm_text()}"
    )


def test_fused_uses_register_only_adds(watcom_10_0a):
    """Fused form accumulates in a register; no `add [m], reg` to the global."""
    fn = _compile(_FUSED, watcom_10_0a)
    add_to_mem = sum(
        1 for i in fn.insns
        if i.mnemonic == "add" and i.op_str.startswith("dword ptr [8],")
    )
    assert add_to_mem == 0, (
        f"fused form should not write directly to memory via add; "
        f"got {add_to_mem}\n{fn.disasm_text()}"
    )
    # And there should be at least one register-to-register add
    add_reg_reg = sum(
        1 for i in fn.insns
        if i.mnemonic == "add" and "dword ptr" not in i.op_str
        and "," in i.op_str
    )
    assert add_reg_reg >= 2, (
        f"expected >= 2 reg-to-reg adds (the accumulator); got {add_reg_reg}\n"
        f"{fn.disasm_text()}"
    )


def test_fused_is_smaller_than_staged(watcom_10_0a):
    """Fused form is a few bytes smaller for our 3-statement test."""
    staged = _compile(_STAGED, watcom_10_0a)
    fused = _compile(_FUSED, watcom_10_0a)
    delta = staged.size() - fused.size()
    assert delta > 0, (
        f"expected fused < staged; got delta={delta}\n"
        f"--- STAGED ({staged.size()}b) ---\n{staged.disasm_text()}\n"
        f"--- FUSED  ({fused.size()}b) ---\n{fused.disasm_text()}"
    )
