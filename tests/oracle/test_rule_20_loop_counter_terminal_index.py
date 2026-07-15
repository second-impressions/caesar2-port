"""Rule 20 - Loop-counter terminal value as the final index.

## Trigger

After a counted ``for`` loop, the loop counter holds the terminal
value (the value that failed the loop condition).  When the C
source uses that variable as an array index right after the loop,
Watcom keeps the counter live and re-uses the indexed addressing
mode it built inside the loop:

```c
int i;
for (i = 0; i < 7; i++) {
    slave_requirements[i].current = 0;     // [eax*8]
}
slave_requirements[i].current = pool;      // STILL [eax*8] (i = 7)
```

emits ``mov [eax*8], reg`` for the post-loop store - same
addressing mode as inside the loop.

If the C source uses a literal index instead:

```c
slave_requirements[7].current = pool;
```

Watcom emits ``mov [0x38], reg`` (absolute displacement 7*8 = 0x38),
**different bytes** even though semantically identical.

The PS.EXE diagnostic: a post-loop array store using an
indexed-by-register addressing mode means the source used the
loop counter (`i`) as the index.

## Mechanism

Watcom\u2019s induction-variable analysis (`bld/cg/c/loopopts.c`,
specifically the `IndVarList` data structures from line 91) tracks
the loop counter as an induction variable.  When the post-loop
code references the same variable, the back-end keeps the
register-resident counter live (same name, same allocation), so
its register holds the terminal value.

The address-folding pass in `bld/cg/intel/c/x86esc.c` then sees
the post-loop expression `array_base + i * elem_size + field_off`
where `i` is in EAX, and folds it into the same `[eax*8 + disp]`
shape that the loop body used.  Using a literal `7` instead loses
the IV link; the constant ``7 * 8 + field_off`` is computed at
compile time and emitted as an absolute displacement.

## Right C: use the loop counter post-loop

```c
for (i = 0; i < 7; i++) { ... }
slave_requirements[i].current = pool;   // matches PS.EXE
```

## Wrong C: literal index

```c
slave_requirements[7].current = pool;   // emits absolute disp,
                                        // won't match PS.EXE
```

## Verified on

  * `adjust_slave_usage` (commit `ff2cf77`).
  * `tests/oracle/test_rule_20_loop_counter_terminal_index.py` -
     4 tests: loop-counter form emits indexed addressing for the
     final store; literal form emits absolute displacement; both
     forms produce different bytes; loop-counter form keeps the
     counter register alive past the loop.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "struct slot { int current; int target; };\n"
    "struct slot slave_requirements[8];\n"
    "int pool;\n"
)


_CONST_IDX = """\
struct slot { int current; int target; };
extern struct slot slave_requirements[8];
extern int pool;
void f(void) {
    int i;
    for (i = 0; i < 7; i++) {
        slave_requirements[i].current = 0;
    }
    slave_requirements[7].current = pool;
}
"""

_LOOP_IDX = """\
struct slot { int current; int target; };
extern struct slot slave_requirements[8];
extern int pool;
void f(void) {
    int i;
    for (i = 0; i < 7; i++) {
        slave_requirements[i].current = 0;
    }
    slave_requirements[i].current = pool;
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, b.output
    return b.function("f")


def _has_indexed_store(fn, scale=8):
    """True if any `mov [reg*scale + ...]` (indexed addressing) appears
    after at least one `cmp ... jl` (i.e. after the loop)."""
    seen_loop_jcc = False
    for i in fn.insns:
        if i.mnemonic == "jl":
            seen_loop_jcc = True
            continue
        if (
            seen_loop_jcc
            and i.mnemonic == "mov"
            and i.op_str.startswith("dword ptr [")
            and f"*{scale}" in i.op_str
        ):
            return True
    return False


def _has_absolute_store_at(fn, displacement):
    """True if `mov dword ptr [<displacement>], reg` appears in fn."""
    target = f"dword ptr [{displacement:#x}]"
    return any(
        i.mnemonic == "mov" and i.op_str.startswith(f"{target},")
        for i in fn.insns
    )


def test_loop_counter_form_uses_indexed_store(watcom_10_0a):
    """`slave_requirements[i].current = pool;` after a counted loop emits
    `mov [eax*8], reg` for the post-loop store."""
    fn = _compile(_LOOP_IDX, watcom_10_0a)
    assert _has_indexed_store(fn, scale=8), (
        f"expected indexed store [eax*8] post-loop:\n{fn.disasm_text()}"
    )


def test_literal_index_form_uses_absolute_store(watcom_10_0a):
    """`slave_requirements[7].current = pool;` emits absolute displacement
    `mov [0x38], reg`."""
    fn = _compile(_CONST_IDX, watcom_10_0a)
    assert _has_absolute_store_at(fn, 0x38), (
        f"expected absolute store [0x38]:\n{fn.disasm_text()}"
    )


def test_two_forms_produce_different_bytes(watcom_10_0a):
    """The two forms compile to different bytes despite being semantically
    equivalent at the source level."""
    fn_const = _compile(_CONST_IDX, watcom_10_0a)
    fn_loop = _compile(_LOOP_IDX, watcom_10_0a)
    # Mask fixups for fair comparison
    a = bytes(0 if (fn_const.base + k) in fn_const.fixups else x
              for k, x in enumerate(fn_const.bytes_))
    b = bytes(0 if (fn_loop.base + k) in fn_loop.fixups else x
              for k, x in enumerate(fn_loop.bytes_))
    assert a != b, (
        f"expected different bytes:\n"
        f"--- CONST ---\n{fn_const.disasm_text()}\n"
        f"--- LOOP ---\n{fn_loop.disasm_text()}"
    )


def test_loop_counter_form_keeps_counter_alive_past_loop(watcom_10_0a):
    """Reusing the counter past the loop forces the back-end to allocate
    a separate register for the post-loop value.  Function size grows by
    a few bytes vs the literal form (extra push/pop for the new
    register)."""
    fn_const = _compile(_CONST_IDX, watcom_10_0a)
    fn_loop = _compile(_LOOP_IDX, watcom_10_0a)
    assert fn_loop.size() > fn_const.size(), (
        f"expected loop-counter form larger; "
        f"const={fn_const.size()}, loop={fn_loop.size()}"
    )
