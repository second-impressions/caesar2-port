"""Rule 27 - Instruction-pair reorder at function entry.

## Trigger

Two adjacent function-entry `mov reg, reg` instructions (typically
parm-spill copies) appear in OPPOSITE order between PS.EXE and the
recomp:

    PS:                    Recomp:
      push esi               push esi
      mov esi, eax           mov ecx, edx        <- reversed
      mov ecx, edx           mov esi, eax        <- reversed

Same instructions, same registers, just swapped. Produces a 2-byte
diff per pair.

## Mechanism

The order in which Watcom\u2019s register allocator processes virtual
names determines the order of parm-spill `mov` instructions.  When
the C source declares a NAMED LOCAL that aliases a parm (e.g.
`int cap = value;`), the local becomes a separate virtual name.
The allocator processes the local before the parm (or vice versa,
depending on declaration order), changing which `mov reg, src`
gets emitted first.

This is the same regalloc-priority shift that powers Rule 24.
Rule 24a ADDS a named local to force a stack spill; Rule 24c\u2019s
twin (this Rule 27) modulates parm-copy ORDER by adding or
REMOVING the alias.

## Right C: invert the alias decision

Two reciprocal fixes depending on which side has the named local:

```c
/* Form A: named local aliases value */
int f(int value, int factor) {
    int cap;
    cap = value;
    if (cap < 0) cap = 0;
    /* ... uses cap ... */
}

/* Form B: no named local, mutate value directly */
int f(int value, int factor) {
    if (value < 0) value = 0;
    /* ... uses value ... */
}
```

Form A and Form B emit the SAME total instructions but the parm-
spill order at function entry differs.  PS.EXE\u2019s shape tells you
which form to use.

## Detector

`_find_rule_27_pairs` scans the diff rows and recognises two
shapes:

  * **delete + insert**: PS row has `mov X, A` paired with RC=None,
    plus another row within \u00b13 with PS=None and RC=`mov X, A`.
  * **replace + replace**: PS=`mov X, A`, RC=`mov Y, B` at row i,
    plus a mirrored row at j: PS=`mov Y, B`, RC=`mov X, A`.

Limited to `mov` instructions to keep false positives low.

## Verified on

  * `city_pop_limit_10_to_1` (formulae.c) - 2-byte diff at +0x4.
     Removing `int cap = value;` and using `value` directly fixes
     the diff.
  * `tests/oracle/test_rule_27_instruction_pair_reorder.py` -
     5 tests covering both shapes + negative cases.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet
from c2.commands.rule_hints import (
    _find_rule_27_pairs,
    detect_hints,
    histogram,
)


# Reuse the helpers from the integration tests
from tests.oracle.test_rule_hints_integration import (
    _build_diff_rows,
    _to_insn_tuple,
)


_DEFS = "int population;\n"


_FORM_A = """\
extern int population;
int f(int value, int factor) {
    int cap, counter;
    cap = value;
    if (cap < 0) cap = 0;
    if (cap > 100) cap = 100;
    for (counter = 0; counter < 100; counter++) {
        if (counter * 10 * factor >= population) {
            if (cap > counter) cap = counter;
            break;
        }
    }
    return cap;
}
"""

_FORM_B = """\
extern int population;
int f(int value, int factor) {
    int counter;
    if (value < 0) value = 0;
    if (value > 100) value = 100;
    for (counter = 0; counter < 100; counter++) {
        if (counter * 10 * factor >= population) {
            if (value > counter) value = counter;
            break;
        }
    }
    return value;
}
"""


def test_two_forms_swap_parm_spill_order(watcom_10_0a):
    """Form A (named-local alias) and Form B (use parm directly) emit
    the SAME total bytes but with the two parm-copy `mov` instructions
    in OPPOSITE order at function entry.
    """
    fn_a = compile_snippet(
        _FORM_A, extern_defs=_DEFS, image=watcom_10_0a
    ).function("f")
    fn_b = compile_snippet(
        _FORM_B, extern_defs=_DEFS, image=watcom_10_0a
    ).function("f")
    # Same total size
    assert fn_a.size() == fn_b.size(), (
        f"Form A {fn_a.size()}b vs Form B {fn_b.size()}b\n"
        f"--- A ---\n{fn_a.disasm_text()}\n--- B ---\n{fn_b.disasm_text()}"
    )
    # First two `mov` instructions after the prologue should be the
    # same set, in opposite order.
    def _first_two_mov(fn):
        seen_pushes = False
        movs = []
        for i in fn.insns:
            if i.mnemonic == "push":
                seen_pushes = True
                continue
            if not seen_pushes:
                continue
            if i.mnemonic == "mov":
                movs.append(i.line)
                if len(movs) == 2:
                    return movs
            else:
                break
        return movs
    movs_a = _first_two_mov(fn_a)
    movs_b = _first_two_mov(fn_b)
    assert len(movs_a) == 2 and len(movs_b) == 2, (movs_a, movs_b)
    # Same set, opposite order.
    assert sorted(movs_a) == sorted(movs_b), (movs_a, movs_b)
    assert movs_a != movs_b, (
        f"forms produced identical order; expected opposite\n"
        f"A: {movs_a}\nB: {movs_b}"
    )


def test_rule_27_detector_fires_on_swap(watcom_10_0a):
    """Compile both forms and run the detector against their diff."""
    fn_a = compile_snippet(
        _FORM_A, extern_defs=_DEFS, image=watcom_10_0a
    ).function("f")
    fn_b = compile_snippet(
        _FORM_B, extern_defs=_DEFS, image=watcom_10_0a
    ).function("f")
    rows = _build_diff_rows(fn_b, fn_a)   # PS = Form B (matches PS.EXE), RC = Form A
    pairs = _find_rule_27_pairs(rows)
    assert pairs, (
        "expected Rule 27 swap pair\n"
        + "\n".join(
            f"  row {i:2d} diff={d}  PS={ps[3] if ps else '-'!r:<30s}  RC={rc[3] if rc else '-'!r}"
            for i, (ps, rc, d) in enumerate(rows)
        )
    )
    hints = detect_hints(rows, fn_b.base, fn_a.base, fn_b.fixups, fn_a.fixups)
    hist = histogram(hints)
    assert hist.get("Rule 27", 0) >= 2, (
        f"expected at least 2 Rule 27 hits (one per row of the swap pair); "
        f"got histogram={hist}"
    )


def test_rule_27_detector_no_false_positive_on_identical_code(watcom_10_0a):
    """Same code on both sides yields zero diff rows -> zero Rule 27 hits."""
    fn = compile_snippet(
        _FORM_A, extern_defs=_DEFS, image=watcom_10_0a
    ).function("f")
    rows = _build_diff_rows(fn, fn)
    pairs = _find_rule_27_pairs(rows)
    assert pairs == {}, f"expected no swap pairs on identical code; got {pairs}"
    hints = detect_hints(rows, fn.base, fn.base, fn.fixups, fn.fixups)
    hist = histogram(hints)
    assert "Rule 27" not in hist, hist


def test_rule_27_detector_ignores_non_mov_diff_rows(watcom_10_0a):
    """A diff in a `cmp`/`add`/`call` row is not a Rule 27 swap candidate."""
    src_a = """\
extern int x;
void f(int p) { x = p + 1; }
"""
    src_b = """\
extern int x;
void f(int p) { x = p + 2; }
"""
    fn_a = compile_snippet(
        src_a, extern_defs="int x;\n", image=watcom_10_0a
    ).function("f")
    fn_b = compile_snippet(
        src_b, extern_defs="int x;\n", image=watcom_10_0a
    ).function("f")
    rows = _build_diff_rows(fn_a, fn_b)
    pairs = _find_rule_27_pairs(rows)
    # The diff is a literal-immediate change in `mov` or `add`, not a swap.
    assert pairs == {}, f"expected no swap pairs; got {pairs}"


def test_rule_27_detector_handles_replace_replace_shape(watcom_10_0a):
    """Synthetic test for shape B (mirrored replace pair) - exercise
    the code path that pairs PS=A,RC=B with PS=B,RC=A on adjacent rows.
    """
    # Build a synthetic rows list with two mirrored rows.
    InsnT = tuple[int, int, bytes, str]
    def mk(asm: str, raw: bytes = b"\x90") -> InsnT:
        return (0, len(raw), raw, asm)

    a = mk("mov esi, eax")
    b = mk("mov ecx, edx")
    rows = [
        (mk("push ebx"), mk("push ebx"), False),
        (a, b, True),    # row 1: replace - PS has a, RC has b
        (b, a, True),    # row 2: replace - mirrored
        (mk("ret"), mk("ret"), False),
    ]
    pairs = _find_rule_27_pairs(rows)
    assert 1 in pairs and 2 in pairs, pairs
    assert pairs[1][0] == 2 and pairs[2][0] == 1
