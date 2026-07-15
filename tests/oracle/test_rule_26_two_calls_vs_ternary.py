"""Rule 26 - Two call statements vs one call with a ternary arg.

## Trigger

When a flag argument to a function depends on a boolean test
(`i == forum_dept_over ? 1 : 0`), the C source can be written
two ways:

  * **Ternary inside the call** (single `call` statement)
    ```c
    forum_explanations(i, i == forum_dept_over ? 1 : 0);
    ```
    -> Watcom emits ``sete dl; and edx, 0xff`` to materialise the
    boolean, then a single ``call``.
  * **Explicit if/else, two calls** (with constant args)
    ```c
    if (i == forum_dept_over) forum_explanations(i, 1);
    else                       forum_explanations(i, 0);
    ```
    -> Watcom emits an explicit `cmp; jne` branch with two arg-
    setup paths (`mov edx, 1` vs `xor edx, edx`), then tail-merges
    the calls into one shared `call` site.

PS.EXE consistently shows the **explicit-branch + tail-merge**
shape at sites like `explain_forum`.  A `sete` in the recomp paired
with a non-`setcc` PS.EXE row at the same diff offset is a
near-certain Rule 26 hit (PS.EXE has only 11 `setcc` instructions
across 37k+ instructions).

## Mechanism

When the front-end sees ``cond ? a : b`` as a sub-expression,
`bld/cc/c/cgen.c` materialises the boolean into a register before
the call, and the back-end picks ``sete + and`` for the 0/1
materialisation under `-4r` (cheap on a 386+).  A single
`OPR_CALL` IR node feeds one `call` site.

When the front-end sees two separate `call` statements, it emits
two distinct `OPR_CALL` IR nodes feeding two call sites with the
same callee but different arg setups.  Rule 15\u2019s `ComTail` then
notices the calls share a common suffix (`call X; ret` or `call X;
inc/cmp/jl loop_top`) and tail-merges them, replacing one with a
`jmp` and folding the arg-setup paths into a join.

The `sete` form has no opportunity for branch-arm-specific
arg-setup; the if/else form gives `ComTail` two distinct setups
to merge.  PS.EXE\u2019s authors wrote the if/else form, and Watcom\u2019s
optimiser finished the job.

## Right C: explicit if/else with two physically distinct calls

```c
for (i = 0; i < 12; i++) {
    if (i == forum_dept_over)
        forum_explanations(i, 1);
    else
        forum_explanations(i, 0);
}
```

Not:

```c
for (i = 0; i < 12; i++) {
    forum_explanations(i, i == forum_dept_over ? 1 : 0);   /* WRONG */
}
```

## Verified on

  * `explain_forum` in gloops.c (commit `c27f398`).
  * Auto-detector `detect_rule_26` in `rule_hints.py` flags any
     diff row where the recomp instruction is `setcc reg8` and PS
     is not.
  * `tests/oracle/test_rule_26_two_calls_vs_ternary.py` - 4 tests:
     ternary form emits `sete`; if/else form has no `setcc`;
     if/else still folds to exactly one `call` instruction (Rule
     15 tail-merge); both forms produce different byte shapes.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "int forum_dept_over;\n"
    "void forum_explanations(int i, int hilite) { (void)i; (void)hilite; }\n"
)


_TERNARY = """\
extern int forum_dept_over;
extern void forum_explanations(int i, int hilite);
void f(void) {
    int i;
    for (i = 0; i < 12; i++) {
        forum_explanations(i, i == forum_dept_over ? 1 : 0);
    }
}
"""

_IF_ELSE = """\
extern int forum_dept_over;
extern void forum_explanations(int i, int hilite);
void f(void) {
    int i;
    for (i = 0; i < 12; i++) {
        if (i == forum_dept_over)
            forum_explanations(i, 1);
        else
            forum_explanations(i, 0);
    }
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, b.output
    return b.function("f")


def _has_setcc(fn):
    return any(i.mnemonic.startswith("set") and len(i.mnemonic) <= 5
               for i in fn.insns)


def test_ternary_emits_sete(watcom_10_0a):
    """Ternary inside the call materialises the boolean via `sete`."""
    fn = _compile(_TERNARY, watcom_10_0a)
    has_sete = any(i.mnemonic == "sete" for i in fn.insns)
    assert has_sete, fn.disasm_text()


def test_if_else_emits_no_setcc(watcom_10_0a):
    """Explicit if/else has no `setcc` instruction \u2014 the branch is materialised
    as a `cmp; jne; mov; jmp; xor` shape."""
    fn = _compile(_IF_ELSE, watcom_10_0a)
    assert not _has_setcc(fn), fn.disasm_text()


def test_if_else_still_one_call_via_tail_merge(watcom_10_0a):
    """The if/else form has *two* source-level `call` statements that
    Rule 15's `ComTail` merges into ONE actual `call` instruction."""
    fn = _compile(_IF_ELSE, watcom_10_0a)
    n_calls = sum(1 for i in fn.insns if i.mnemonic == "call")
    assert n_calls == 1, (
        f"expected 1 tail-merged call; got {n_calls}\n{fn.disasm_text()}"
    )


def test_two_forms_have_different_byte_shapes(watcom_10_0a):
    """Beyond the `setcc` distinction, the overall byte shape differs."""
    ternary = _compile(_TERNARY, watcom_10_0a)
    if_else = _compile(_IF_ELSE, watcom_10_0a)
    a = bytes(0 if (ternary.base + k) in ternary.fixups else x
              for k, x in enumerate(ternary.bytes_))
    b = bytes(0 if (if_else.base + k) in if_else.fixups else x
              for k, x in enumerate(if_else.bytes_))
    assert a != b, (
        f"expected different bytes:\n"
        f"--- TERNARY ---\n{ternary.disasm_text()}\n"
        f"--- IF/ELSE ---\n{if_else.disasm_text()}"
    )
