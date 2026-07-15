"""Rule 7b - Split `+=1` from the add to get `inc reg` + load/add/store.

## Trigger

When PS.EXE shows the four-instruction read-modify-write

    inc   reg                   ; +1 of a local
    mov   r2, [global]          ; load destination
    add   r2, reg               ; fold in the increment
    mov   [global], r2          ; store

the source had two assignment statements:

```c
growth_amt++;                   /* emits inc reg */
slaves += growth_amt;           /* emits mov r2,[m]; add r2,reg; mov [m],r2 */
```

The fused single-expression form

```c
slaves = slaves + growth_amt + 1;
```

emits the three-instruction sequence

    add   reg, [global]         ; absorbs the load
    inc   reg                   ; +1 (or `add reg, 2` etc)
    mov   [global], reg

and saves 4 bytes total: the explicit load is folded into the add
(`G_RM2` form `add reg, [m]`, 6 bytes) instead of being a separate
`mov reg, [m]` (6 bytes) plus a register `add reg, reg` (2 bytes).
The split form additionally has to preserve the callee-saved
register it picks for the load destination (`push ebx; pop ebx` at
the prologue/epilogue), adding 2 bytes - net +4 over the fused form.

## Mechanism

Watcom emits each ``=`` statement as its own IR sequence via
``CGAssign`` (`bld/cg/c/intrface.c:876`).  The optimizer doesn't
merge IR across statement boundaries, so the load+add can't pick up
the just-incremented value as a free side input.

The fused single-expression form reaches the back-end as one IR
tree; the optab `Add4` at `bld/cg/intel/386/c/386table.c:141`
matches `(R, M, R, EQ_R1)` -> `G_RM2`, emitting the compact
`add reg, [m]` form.  The split form's second statement is
`(M, R, M, EQ_R1)` (line 142) -> `G_MR2`, emitting `add [m], reg` -
*but* the actual chain has to go through a register first because
the intermediate result is also reused by the next statement
(`slaves -= mortality_amt`), so the compiler routes through EBX.

## Why this matters

This is the inverse of Rule 7: there, two statements *match* PS.EXE
and one expression doesn't.  Here, **one** expression matches the
compact PS.EXE form and two statements don't.  Read PS.EXE:

  * `inc reg; mov r2,[m]; add r2,reg; mov [m],r2` -> two C statements.
  * `add reg,[m]; inc reg; mov [m],reg`           -> one C expression.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "int slaves; int growth_amt; int mortality_amt;\n"
    "int reader(void) { return 0; }\n"
)


_SPLIT = """\
extern int slaves, growth_amt, mortality_amt;
extern int reader(void);
void f(void) {
    int gx = reader();
    int mort = reader();
    gx++;
    slaves += gx;
    slaves -= mort;
}
"""


_FUSED = """\
extern int slaves, growth_amt, mortality_amt;
extern int reader(void);
void f(void) {
    int gx = reader();
    int mort = reader();
    slaves = slaves + gx + 1;
    slaves -= mort;
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def test_split_form_emits_inc_then_load_add_store(watcom_10_0a):
    """`gx++; slaves += gx;` emits inc, separate load, add reg/reg, store."""
    fn = _compile(_SPLIT, watcom_10_0a)
    assert fn.has_insn("inc"), fn.disasm_text()
    # Separate load: `mov rX, [imm32]` reading slaves
    assert any(
        i.mnemonic == "mov"
        and i.op_str.startswith(("ebx, dword ptr", "ecx, dword ptr",
                                  "eax, dword ptr", "edx, dword ptr"))
        for i in fn.insns
    ), f"expected separate load:\n{fn.disasm_text()}"
    # Register-to-register add (no memory operand)
    assert any(
        i.mnemonic == "add"
        and "dword ptr" not in i.op_str
        and i.op_str.count(",") == 1
        for i in fn.insns
    ), f"expected `add r, r`:\n{fn.disasm_text()}"
    # And NOT `add reg, [memory]`
    assert not any(
        i.mnemonic == "add" and "dword ptr" in i.op_str
        for i in fn.insns
    ), f"split form should not use memory-operand add:\n{fn.disasm_text()}"


def test_fused_form_emits_add_with_memory_operand(watcom_10_0a):
    """`slaves + gx + 1` emits `add reg, [slaves]` + `inc reg` + store."""
    fn = _compile(_FUSED, watcom_10_0a)
    assert any(
        i.mnemonic == "add" and "dword ptr" in i.op_str
        for i in fn.insns
    ), f"expected `add reg, [m]`:\n{fn.disasm_text()}"
    assert fn.has_insn("inc"), fn.disasm_text()


def test_fused_is_four_bytes_shorter(watcom_10_0a):
    """Fused single-expression saves 4 bytes vs the split form."""
    split = _compile(_SPLIT, watcom_10_0a)
    fused = _compile(_FUSED, watcom_10_0a)
    delta = split.size() - fused.size()
    assert delta == 4, (
        f"expected fused to save 4 bytes; got {delta}\n"
        f"--- SPLIT ({split.size()}b) ---\n{split.disasm_text()}\n"
        f"--- FUSED ({fused.size()}b) ---\n{fused.disasm_text()}"
    )


def test_split_form_saves_callee_saved_register(watcom_10_0a):
    """The split form pushes EBX (because it's used as a temp); fused doesn't."""
    split = _compile(_SPLIT, watcom_10_0a)
    fused = _compile(_FUSED, watcom_10_0a)
    assert split.has_insn("push", "ebx"), split.disasm_text()
    assert not fused.has_insn("push", "ebx"), fused.disasm_text()
