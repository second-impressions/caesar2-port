"""Rule 9 - if-body fall-through layout for `if (x == 0)` / `if (x != 0)`.

## Trigger

Watcom 10.0a always emits the if-body **immediately after the
conditional jump** (so the if-body is the fall-through path) and
the else-body at the forward target.  This holds regardless of
operator (`==`, `!=`, `<`, `>`, etc.) and regardless of relative
branch sizes.

The Jcc opcode is the *inverted* C test operator (because the Jcc
skips the if-body to reach the else):

| C test       | Asm Jcc (skip-body) |
|--------------|---------------------|
| `x == 0`     | `jne forward`       |
| `x != 0`     | `je forward`        |
| `x == N`     | `jne forward`       |
| `x != N`     | `je forward`        |
| `x < N`      | `jge forward`       |
| `x <= N`     | `jg forward`        |
| `x > N`      | `jle forward`       |
| `x >= N`     | `jl forward`        |

This is the same operator-preservation rule as Rule 4, narrowed to
the `==` / `!=` cases.

## Layout matching PS.EXE

When matching PS.EXE byte-for-byte, the Jcc opcode in PS.EXE tells
you which form of the equality test the source used:

  * PS.EXE shows `jne forward`  ->  source had `if (x == 0) { A } else { B }`
  * PS.EXE shows `je  forward`  ->  source had `if (x != 0) { B } else { A }`

`if (is_barb == 0) { A } else { B }` and
`if (is_barb != 0) { B } else { A }` are semantically equivalent
but produce different bytes (different Jcc opcode + the bodies
appear in opposite order in memory).  Pick the form whose Jcc
matches PS.EXE.

## Mechanism

The C front-end emits one IR `OP_CMP_*` per source-level test
(`bld/cg/c/foldins.c:148`).  The block-layout pass keeps the if-body
contiguous with the conditional jump's fall-through, and routes the
else-body to a forward block ending in a join label.  The Jcc
encoding is selected from the optab (Rule 4's `Cmp4` mechanism),
inverting the C test because the Jcc's role is "skip into the else".

## Verified on

  * `create_citizen` (common.c) at sites L67 and elsewhere -
     PS.EXE shows `je forward` for what semantically is "is_barb is
     zero", confirming the source used `if (is_barb != 0) { B }
     else { A }` rather than the more natural `if (is_barb == 0) {
     A } else { B }`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "int x; int dst;\n"
    "void use_a(int v) { (void)v; }\n"
    "void use_b(int v) { (void)v; }\n"
    "void use_c(int v) { (void)v; }\n"
)


_TEMPLATE = """\
extern int x, dst;
extern void use_a(int v);
extern void use_b(int v);
void f(void) {{
    if ({cond}) {{ use_a(1); dst = 11; }}
    else        {{ use_b(2); dst = 22; }}
}}
"""


def _compile(cond, image):
    src = _TEMPLATE.format(cond=cond)
    b = compile_snippet(src, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _first_branch(fn):
    """Return (cmp_or_test, jcc) for the first conditional branch in fn."""
    cmp_ = None
    for i in fn.insns:
        if i.mnemonic in ("cmp", "test"):
            cmp_ = i
        elif i.mnemonic.startswith("j") and i.mnemonic != "jmp" and cmp_ is not None:
            return cmp_, i
    raise AssertionError(f"no branch found:\n{fn.disasm_text()}")


def _body_is_fall_through(fn, jcc):
    """Verify the conditional jump's *target* is later in memory than the
    immediately-next instruction.

    For `if (cond) { A } else { B }` with `jcc forward`, the next
    instruction is the start of the if-body (A).  Calling helper
    use_a() with arg 1 should follow.
    """
    # Find idx of jcc and the following insns
    seq = list(fn.insns)
    idx = next(k for k, i in enumerate(seq) if i is jcc)
    # The instruction after jcc should be `mov eax, 1` (use_a's arg).
    after = seq[idx + 1]
    assert after.mnemonic == "mov" and "eax, 1" in after.op_str, (
        f"expected `mov eax, 1` (use_a arg) after jcc; got `{after.line}`\n"
        f"{fn.disasm_text()}"
    )


# ---- Operator -> Jcc mapping ------------------------------------------

@pytest.mark.parametrize("cond,jcc", [
    ("x == 0",  "jne"),
    ("x != 0",  "je"),
    ("x == 5",  "jne"),
    ("x != 5",  "je"),
    ("x < 5",   "jge"),
    ("x <= 5",  "jg"),
    ("x > 5",   "jle"),
    ("x >= 5",  "jl"),
])
def test_jcc_is_inverted_test(watcom_10_0a, cond, jcc):
    """Each C test operator picks a specific inverted Jcc."""
    fn = _compile(cond, watcom_10_0a)
    _, j = _first_branch(fn)
    assert j.mnemonic == jcc, (
        f"expected `{jcc}` for `{cond}`; got `{j.line}`\n{fn.disasm_text()}"
    )


# ---- Layout: if-body always falls through ------------------------------

@pytest.mark.parametrize("cond", [
    "x == 0", "x != 0", "x == 5", "x != 5",
    "x < 5", "x <= 5", "x > 5", "x >= 5",
])
def test_if_body_falls_through(watcom_10_0a, cond):
    """The if-body (A) immediately follows the Jcc; else-body is at the forward target."""
    fn = _compile(cond, watcom_10_0a)
    _, j = _first_branch(fn)
    _body_is_fall_through(fn, j)


# ---- The two semantically-equivalent forms produce different Jccs ------

def test_eq_zero_and_neq_zero_swap_jcc(watcom_10_0a):
    """`if (x == 0) {A} else {B}` -> `jne`; `if (x != 0) {B} else {A}` -> `je`."""
    eq_form = _compile("x == 0", watcom_10_0a)
    neq_form = _compile("x != 0", watcom_10_0a)
    _, j_eq = _first_branch(eq_form)
    _, j_neq = _first_branch(neq_form)
    assert j_eq.mnemonic == "jne", eq_form.disasm_text()
    assert j_neq.mnemonic == "je",  neq_form.disasm_text()


def test_layout_independent_of_branch_sizes(watcom_10_0a):
    """If-body always falls through, even when else-body is much larger."""
    BIG_ELSE = """\
extern int x, dst;
extern void use_a(int v);
extern void use_b(int v);
extern void use_c(int v);
void f(void) {
    if (x == 0) { use_a(99); }
    else {
        use_a(1); dst = 11;
        use_b(2); dst = 22;
        use_c(3); dst = 33;
    }
}
"""
    b = compile_snippet(BIG_ELSE, extern_defs=_DEFS, image=watcom_10_0a)
    assert b.ok, b.output
    fn = b.function("f")
    _, j = _first_branch(fn)
    assert j.mnemonic == "jne", fn.disasm_text()
    # Check that the if-body (use_a(99)) follows the jcc
    seq = list(fn.insns)
    idx = next(k for k, i in enumerate(seq) if i is j)
    after = seq[idx + 1]
    assert after.mnemonic == "mov" and "0x63" in after.op_str, (
        f"expected `mov eax, 0x63` (use_a(99)) after jne; got `{after.line}`\n"
        f"{fn.disasm_text()}"
    )


# ---- The negation table extends to ALL six relational ops --------------
#
# Per `bld/cg/c/revcond.c:42-49` (FlipBranch[]), identical in OW v1.0.0
# and OW v2 master, the negation table is:
#
#     EQUAL          <-> NOT_EQUAL
#     LESS           <-> GREATER_EQUAL
#     LESS_EQUAL     <-> GREATER
#
# (plus BIT_TEST_TRUE <-> BIT_TEST_FALSE, irrelevant to plain `if`).
#
# `bld/cg/c/encode.c:DoCondJump` calls `FlipCond(cond)` when the true
# target is the next block (i.e. the if-body falls through).  For C
# source `if (cond) IFBODY; else ELSEBODY;` with IFBODY laid out next,
# the emitted Jcc is therefore the negation of the source operator.
#
# Consequence: writing `if (a OP b) X(); else Y();` and
# `if (a NEG_OP b) Y(); else X();` produces semantically identical
# code; the bytes differ only in the Jcc opcode (per FlipBranch).
# Pick the form whose Jcc matches PS.EXE.


_NEG_TEMPLATE_A = """\
extern int x, y;
extern void X(void);
extern void Y(void);
void f(int p) {{ x = p; if (p {op} y) X(); else Y(); }}
"""

_NEG_TEMPLATE_B = """\
extern int x, y;
extern void X(void);
extern void Y(void);
void f(int p) {{ x = p; if (p {op} y) Y(); else X(); }}
"""

_NEG_DEFS = "int x, y; void X(void){} void Y(void){}\n"


@pytest.mark.parametrize("op_a,op_b,jcc_a,jcc_b", [
    ("==", "!=", "jne", "je"),
    ("<",  ">=", "jge", "jl"),
    ("<=", ">",  "jg",  "jle"),
])
def test_flipbranch_negation_pairs(
    watcom_10_0a, op_a, op_b, jcc_a, jcc_b,
):
    """Each `FlipBranch[]` pair `(op_a, op_b)` produces complementary
    Jccs, with the ELSE branch swapped to keep semantics equivalent.

    Per the encode.c:DoCondJump mechanism, the Jcc emitted is
    `FlipBranch[op]` because IFBODY falls through.  We verify this
    holds for all three non-bit-test relational pairs.
    """
    src_a = _NEG_TEMPLATE_A.format(op=op_a)
    src_b = _NEG_TEMPLATE_B.format(op=op_b)
    fn_a = compile_snippet(
        src_a, extern_defs=_NEG_DEFS, image=watcom_10_0a
    ).function("f")
    fn_b = compile_snippet(
        src_b, extern_defs=_NEG_DEFS, image=watcom_10_0a
    ).function("f")
    _, j_a = _first_branch(fn_a)
    _, j_b = _first_branch(fn_b)
    assert j_a.mnemonic == jcc_a, (
        f"`{op_a}` form should emit {jcc_a}, got {j_a.mnemonic}\n"
        f"{fn_a.disasm_text()}"
    )
    assert j_b.mnemonic == jcc_b, (
        f"`{op_b}` form should emit {jcc_b}, got {j_b.mnemonic}\n"
        f"{fn_b.disasm_text()}"
    )


@pytest.mark.parametrize("op_a,op_b", [
    ("==", "!="),
    ("<",  ">="),
    ("<=", ">"),
])
def test_flipbranch_pair_same_function_size(watcom_10_0a, op_a, op_b):
    """The two semantically-equivalent forms have the SAME total byte size
    (only the Jcc opcode differs)."""
    src_a = _NEG_TEMPLATE_A.format(op=op_a)
    src_b = _NEG_TEMPLATE_B.format(op=op_b)
    fn_a = compile_snippet(
        src_a, extern_defs=_NEG_DEFS, image=watcom_10_0a
    ).function("f")
    fn_b = compile_snippet(
        src_b, extern_defs=_NEG_DEFS, image=watcom_10_0a
    ).function("f")
    assert fn_a.size() == fn_b.size(), (
        f"`{op_a}` ({fn_a.size()}b) vs `{op_b}` ({fn_b.size()}b)\n"
        f"--- {op_a} ---\n{fn_a.disasm_text()}\n"
        f"--- {op_b} ---\n{fn_b.disasm_text()}"
    )
