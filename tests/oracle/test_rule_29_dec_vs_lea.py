"""Rule 29 - DEC vs LEA for in-place global decrement.

## Trigger

The two C forms produce different byte sequences for the same
"decrement-and-store" semantics:

```c
/* Form A: direct global decrement */
if (g != 0) g--;

/* Form B: load into a named local, decrement, store back */
int x = g;
if (x != 0) {
    x--;
    g = x;
}
```

* **Form A** uses `lea reg2, [reg1 - 1]` to compute the new value
  in a fresh register, then stores it.
* **Form B** uses `dec reg` to update the register in place.

PS.EXE\u2019s `check_for_promotion::refused_promotion--` (line 89-90)
matches Form B\u2019s shape (`dec ecx; mov [m], ecx`), so the recomp
should write the local-and-store form to byte-match.

## Mechanism

Watcom decides between LEA and DEC based on whether the
just-decremented value is still needed.  When the global is
modified directly via `--`, the value-pool tracker keeps the
register holding the *old* value reserved (in case downstream
code uses it) and emits LEA into a different register.  Naming
a local changes the value-pool\u2019s analysis: the tracker can
prove the old value is dead after the decrement and emits an
in-place `dec`.

## Caveat

Applying Rule 29 in isolation often cascades through the function
because the 4-byte saving shifts every relative jmp/jcc
displacement downstream.  When PS\u2019s epilogue is tail-merged
with the next function (Rule 15), the recomp must end with the
same `jmp <abs>` byte sequence; an inline `pop \u2026 pop \u2026 ret`
epilogue ruins the match even though it is locally correct.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


def _has_lea_minus_one(insns):
    """Does the function contain a `lea reg, [reg-1]` instruction?"""
    for ins in insns:
        if ins.mnemonic == "lea" and "- 1" in ins.op_str:
            return True
    return False


def _has_dec_reg(insns):
    """Does the function contain a `dec <reg>` (single-operand reg form)?"""
    for ins in insns:
        if ins.mnemonic == "dec" and "[" not in ins.op_str:
            return True
    return False


# ── Form A: direct global decrement → LEA ────────────────────────────────────


def test_form_a_direct_global_dec_emits_lea(watcom_10_0a):
    """Direct `g--;` inside an if-test emits `lea reg2, [reg1 - 1]`."""
    src = """\
extern int refused_promotion;
void f(void) {
    if (refused_promotion != 0) {
        refused_promotion--;
    }
}
"""
    fn = compile_snippet(
        src, extern_defs="int refused_promotion;\n"
    ).function("f")
    assert _has_lea_minus_one(fn.insns), (
        "Form A should emit `lea reg, [reg-1]`; got:\n"
        + "\n".join(f"  {i.mnemonic} {i.op_str}" for i in fn.insns)
    )
    assert not _has_dec_reg(fn.insns)


def test_form_a_predec_also_emits_lea(watcom_10_0a):
    """`--g;` (pre-decrement) behaves the same as `g--;`."""
    src = """\
extern int refused_promotion;
void f(void) {
    if (refused_promotion != 0) {
        --refused_promotion;
    }
}
"""
    fn = compile_snippet(
        src, extern_defs="int refused_promotion;\n"
    ).function("f")
    assert _has_lea_minus_one(fn.insns)


def test_form_a_subassign_also_emits_lea(watcom_10_0a):
    """`g -= 1;` produces the same LEA shape."""
    src = """\
extern int refused_promotion;
void f(void) {
    if (refused_promotion != 0) {
        refused_promotion -= 1;
    }
}
"""
    fn = compile_snippet(
        src, extern_defs="int refused_promotion;\n"
    ).function("f")
    assert _has_lea_minus_one(fn.insns)


# ── Form B: load-into-local, decrement, store → DEC ──────────────────────────


def test_form_b_local_dec_emits_dec(watcom_10_0a):
    """Loading into a named local, decrementing the local, and writing
    the local back triggers in-place `dec reg`."""
    src = """\
extern int refused_promotion;
void f(void) {
    int rp = refused_promotion;
    if (rp != 0) {
        rp--;
        refused_promotion = rp;
    }
}
"""
    fn = compile_snippet(
        src, extern_defs="int refused_promotion;\n"
    ).function("f")
    assert _has_dec_reg(fn.insns), (
        "Form B should emit `dec <reg>`; got:\n"
        + "\n".join(f"  {i.mnemonic} {i.op_str}" for i in fn.insns)
    )
    assert not _has_lea_minus_one(fn.insns)


def test_form_b_inline_assign_in_test_emits_dec(watcom_10_0a):
    """Combining the load into the if-test still emits DEC."""
    src = """\
extern int refused_promotion;
void f(void) {
    int rp;
    if ((rp = refused_promotion) != 0) {
        rp--;
        refused_promotion = rp;
    }
}
"""
    fn = compile_snippet(
        src, extern_defs="int refused_promotion;\n"
    ).function("f")
    assert _has_dec_reg(fn.insns)


def test_form_b_unsigned_local_emits_dec(watcom_10_0a):
    """Signed-ness of the local doesn\u2019t matter; the load+dec+store
    pattern is what triggers DEC."""
    src = """\
extern int refused_promotion;
void f(void) {
    unsigned int rp = (unsigned int)refused_promotion;
    if (rp != 0) {
        rp--;
        refused_promotion = (int)rp;
    }
}
"""
    fn = compile_snippet(
        src, extern_defs="int refused_promotion;\n"
    ).function("f")
    assert _has_dec_reg(fn.insns)


# ── Comparison: byte size ─────────────────────────────────────────────────────


def test_form_b_is_smaller_than_form_a(watcom_10_0a):
    """Form B saves ~4 bytes per call site by avoiding the LEA reg."""
    DEFS = "int refused_promotion;\n"

    form_a = """\
extern int refused_promotion;
void f(void) { if (refused_promotion != 0) refused_promotion--; }
"""
    form_b = """\
extern int refused_promotion;
void f(void) {
    int rp = refused_promotion;
    if (rp != 0) { rp--; refused_promotion = rp; }
}
"""
    a = compile_snippet(form_a, extern_defs=DEFS).function("f")
    b = compile_snippet(form_b, extern_defs=DEFS).function("f")
    assert b.size() < a.size(), (
        f"expected Form B ({b.size()}b) < Form A ({a.size()}b)"
    )
