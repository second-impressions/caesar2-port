"""Rule 11 - Pre-increment + cache pattern for loop sentinels.

## Trigger

When a loop body initialises ``best_val`` from ``cur_val`` and the
post-search check is "did the inner search find anything better?",
PS.EXE uses the **pre-incremented primary** as both the sentinel and
the tie-detection comparand:

```c
cur_val++;                  /* pre-increment */
best_val = cur_val;
inner_search(&best_val);    /* may shrink best_val */
if (best_val == cur_val) return 0;
cur_val = best_val;
```

The fused alternative

```c
best_val = cur_val + 1;
inner_search(&best_val);
if (best_val == cur_val + 1) return 0;
cur_val = best_val;
```

is semantically equivalent (when ``cur_val`` isn't read elsewhere)
but produces longer asm because:

  * The comparison ``best_val == cur_val + 1`` recomputes
     ``cur_val + 1`` at compare time (extra `mov`, `inc`, and 32-bit
     zero-extends because ``cur_val`` and ``best_val`` are ``char``).
  * The pre-increment form's comparison is a plain 8-bit
     ``cmp dl, ah`` (cur_val and best_val both in 8-bit halves).

## Mechanism

Same chain as Rules 7 / 7b / 10: each ``=`` statement is its own IR
sequence (`CGAssign` at `bld/cg/c/intrface.c:876`); no merging
across statement boundaries.  ``cur_val++`` materialises ``cur_val``
in a register at its incremented value; the next statement's
``best_val = cur_val`` and the later ``best_val == cur_val`` reuse
that already-resident value.

The fused ``cur_val + 1`` produces a temp expression each time it
appears.  At the comparison site it has to be recomputed because
the original ``cur_val`` is preserved (no statement explicitly
incremented it).  C's integer promotion rules force the comparison
to int width when one side is an int expression
(``cur_val + 1`` -> int), so the comparison gains 32-bit
zero-extension steps.

## Why this matters

When PS.EXE shows a small loop with `inc reg; mov [stack], reg;
... cmp reg, [stack]; je no_improvement`, the source had the
pre-increment + cache form.  This is a common shape for path-
finding / search loops in Caesar II's AI code (``trace_back_ferret``,
etc.).
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "char inner_search(char *bv) { return *bv; }\n"
)


_PRE_INC = """\
extern char inner_search(char *bv);
int f(int n) {
    char cur_val = 0;
    char best_val;
    while (n--) {
        cur_val++;
        best_val = cur_val;
        inner_search(&best_val);
        if (best_val == cur_val) return 0;
        cur_val = best_val;
    }
    return 1;
}
"""


_FUSED = """\
extern char inner_search(char *bv);
int f(int n) {
    char cur_val = 0;
    char best_val;
    while (n--) {
        best_val = cur_val + 1;
        inner_search(&best_val);
        if (best_val == cur_val + 1) return 0;
        cur_val = best_val;
    }
    return 1;
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def test_pre_increment_form_uses_8bit_cmp(watcom_10_0a):
    """The PS-matching form keeps the comparison at 8-bit width."""
    fn = _compile(_PRE_INC, watcom_10_0a)
    # Look for `cmp <byte_reg>, <byte_reg>`
    has_8bit_cmp = any(
        i.mnemonic == "cmp"
        and any(r in i.op_str for r in ("al", "bl", "cl", "dl",
                                          "ah", "bh", "ch", "dh"))
        and "dword ptr" not in i.op_str
        for i in fn.insns
    )
    assert has_8bit_cmp, f"expected 8-bit cmp:\n{fn.disasm_text()}"
    # And NO `cmp <32bit_reg>, <32bit_reg>` for the tie-detection
    # (there may be one for the loop counter `n--` but the bv comparison stays 8-bit)


def test_fused_form_recomputes_via_32bit_cmp(watcom_10_0a):
    """The fused form recomputes `cur_val + 1` and compares at 32-bit width.

    C promotes ``cur_val + 1`` to int, forcing 32-bit zero-extension
    of the char operands and a 32-bit cmp.
    """
    fn = _compile(_FUSED, watcom_10_0a)
    # Has 32-bit cmp on the tie-detection
    has_32bit_cmp = any(
        i.mnemonic == "cmp"
        and i.op_str.count(",") == 1
        and all(r not in i.op_str for r in ("al", "bl", "cl", "dl",
                                             "ah", "bh", "ch", "dh",
                                             "byte ptr"))
        and "dword ptr" not in i.op_str   # exclude memory comparison
        for i in fn.insns
    )
    assert has_32bit_cmp, f"expected 32-bit reg-reg cmp:\n{fn.disasm_text()}"
    # Has at least two zero-extends (one per side of the cmp)
    xor_count = sum(
        1 for i in fn.insns
        if i.mnemonic == "xor" and i.op_str in (
            "eax, eax", "ebx, ebx", "ecx, ecx", "edx, edx",
        )
    )
    assert xor_count >= 2, (
        f"expected >= 2 zero-extends in fused form; got {xor_count}\n"
        f"{fn.disasm_text()}"
    )


def test_pre_increment_is_shorter_than_fused(watcom_10_0a):
    """The pre-increment form saves a few bytes vs the fused form."""
    pre = _compile(_PRE_INC, watcom_10_0a)
    fused = _compile(_FUSED, watcom_10_0a)
    delta = fused.size() - pre.size()
    assert delta >= 4, (
        f"expected pre-increment to save >= 4 bytes; got {delta}\n"
        f"--- PRE-INC ({pre.size()}b) ---\n{pre.disasm_text()}\n"
        f"--- FUSED   ({fused.size()}b) ---\n{fused.disasm_text()}"
    )


def test_pre_increment_emits_one_inc(watcom_10_0a):
    """Pre-increment form has exactly one `inc` for the cur_val update.

    The fused form also has one `inc` (for `cur_val + 1`) but it's
    used as a temp - the same source `cur_val` is *not* modified.
    """
    fn = _compile(_PRE_INC, watcom_10_0a)
    inc_count = sum(1 for i in fn.insns if i.mnemonic == "inc")
    # The loop counter `n--` is `dec`, not `inc`.  Only the `cur_val++`
    # contributes an `inc`.
    assert inc_count == 1, f"expected 1 `inc`; got {inc_count}\n{fn.disasm_text()}"
