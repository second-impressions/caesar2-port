"""Rule 5 - Signed division by power-of-2 uses the `sar; shl; sbb` idiom.

## Trigger

For signed `int x / 2^N` (N >= 2), Watcom 10.0a emits a branch-free
6-instruction sequence:

    mov  edx, eax        ; copy dividend
    sar  edx, 31         ; edx = 0 or -1 (sign bit broadcast)
    shl  edx, N          ; edx = 0 or -2^N; CF = sign bit of x
    sbb  eax, edx        ; eax += 0 or 2^N - 1; eax += CF (the sign bit)
    sar  eax, N          ; arithmetic right-shift to divide

For signed `x / 2`, the special case in `By2Div` (one fewer step):

    mov  edx, eax
    sar  edx, 31
    sub  eax, edx        ; eax += 0 or 1
    sar  eax, 1

For non-power-of-2 signed divides, Watcom falls back to the full
`idiv` instruction.

For *unsigned* `unsigned u / 2^N`, the front-end's tree-fold rewrites
`u / 2^N` to `u >> N` directly, so the asm is just:

    shr  eax, N

The portable C source `(x < 0 ? x + (2^N - 1) : x) >> N` does **not**
collide with the sar/shl/sbb idiom; it compiles to a 5-instruction
test/branch sequence (`test edx, edx; jge; lea eax, [edx+7]; jmp;
mov eax, edx; sar eax, 3`).  Don't write the portable form when
PS.EXE shows the branch-free idiom.

## Mechanism

`FoldDiv` in `bld/cg/c/treefold.c:947` handles the unsigned case:

    } else if( !HasBigConst( tipe ) && ( left->tipe->attr & TYPE_SIGNED ) == 0 ) {
        if( CFIsU32( rv ) ) {
            log = GetLog2( rite->u.name->c.lo.u.int_value );
            if( log != -1 ) {
                fold = TGBinary( O_RSHIFT, left, IntToType( log, TypeInteger ), tipe );
                BurnTree( rite );
            }
        }
    }

If the dividend type is unsigned and the divisor is a power-of-2
constant, the divide is rewritten as a right shift before reaching
the optab.

For signed types, no early fold happens.  The signed-divide optab
`Div4` at `bld/cg/intel/386/c/386table.c:728` selects between two
power-of-2 generators:

    _OE( _Bin( R, C, R, NONE ), V_OP2TWO,  RG_DBL_DIV, G_DIV2,    FU_IDIV ),
    _OE( _Bin( R, C, R, NONE ), V_OP2POW2, RG_DBL_DIV, G_POW2DIV, FU_IDIV ),

`V_OP2TWO` matches divisor exactly == 2; `V_OP2POW2` matches any
power-of-2.  The first row beats the second so /2 gets the
specialised 4-byte `By2Div` sequence; /4, /8, /16 etc go through
`Pow2Div`'s 6-byte `sar; shl; sbb; sar` chain.

`Pow2Div` is at `bld/cg/intel/386/c/386enc.c:818`:

    LayOpword( 0xe2c1 );    /* shl  edx,n */
    AddByte( log2 );
    LayOpword( 0xc21b );    /* sbb  eax,edx */
    LayOpword( 0xf8c1 );    /* sar  eax,n */
    AddByte( log2 );

`By2Div` is at `bld/cg/intel/386/c/386enc.c:857`:

    LayOpword( 0xc22b );    /* sub  eax,edx */
    LayOpword( 0xf8d1 );    /* sar  eax,1 */

The leading `mov edx, eax; sar edx, 31` setup is emitted earlier as
the standard `RG_DBL_DIV` register-pair load; both Pow2Div and
By2Div assume edx already holds the sign-broadcast.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = "int x; int dst; unsigned int u; unsigned int ud;\n"


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _signed_pow2_div(divisor):
    return f"""\
extern int x, dst;
void f(void) {{ dst = x / {divisor}; }}
"""


def _unsigned_pow2_div(divisor):
    return f"""\
extern unsigned int u, ud;
void f(void) {{ ud = u / {divisor}; }}
"""


def _ternary_bias(divisor):
    bias = divisor - 1
    log2 = divisor.bit_length() - 1
    return f"""\
extern int x, dst;
void f(void) {{ dst = (x < 0 ? x + {bias} : x) >> {log2}; }}
"""


# ---- Signed power-of-2 divide ------------------------------------------

@pytest.mark.parametrize("divisor,log2", [(4, 2), (8, 3), (16, 4), (32, 5)])
def test_signed_pow2_div_uses_sar_shl_sbb(watcom_10_0a, divisor, log2):
    """Signed `x / 2^N` (N >= 2) emits sar/shl/sbb/sar (branch-free)."""
    fn = _compile(_signed_pow2_div(divisor), watcom_10_0a)
    text = fn.disasm_text()
    assert fn.has_insn("sar", "edx, 0x1f"), text     # sign broadcast
    assert fn.has_insn("shl", f"edx, {log2}"), text   # shl edx, N
    assert fn.has_insn("sbb", "eax, edx"), text
    assert fn.has_insn("sar", f"eax, {log2}"), text
    # And NO conditional branch (it's branch-free)
    for i in fn.insns:
        assert not (
            i.mnemonic.startswith("j") and i.mnemonic != "jmp"
        ), f"unexpected branch in branch-free idiom:\n{text}"
    # And no idiv
    assert not fn.has_insn("idiv"), text


def test_signed_div_by_2_uses_by2div_special_case(watcom_10_0a):
    """`x / 2` uses the special 4-step By2Div sequence (no `shl edx, 1`)."""
    fn = _compile(_signed_pow2_div(2), watcom_10_0a)
    text = fn.disasm_text()
    assert fn.has_insn("sar", "edx, 0x1f"), text
    assert fn.has_insn("sub", "eax, edx"), text
    assert fn.has_insn("sar", "eax, 1"), text
    # And NO `shl edx, 1` (the By2Div optimization skips it)
    assert not fn.has_insn("shl", "edx"), text
    assert not fn.has_insn("sbb"), text


def test_signed_div_by_3_uses_idiv(watcom_10_0a):
    """Non-power-of-2 signed divides fall back to `idiv`."""
    fn = _compile(_signed_pow2_div(3), watcom_10_0a)
    assert fn.has_insn("idiv"), fn.disasm_text()
    assert not fn.has_insn("sbb"), fn.disasm_text()


# ---- Unsigned power-of-2 divide ----------------------------------------

@pytest.mark.parametrize("divisor,log2", [(2, 1), (4, 2), (8, 3), (16, 4)])
def test_unsigned_pow2_div_uses_shr(watcom_10_0a, divisor, log2):
    """Unsigned `u / 2^N` collapses to a plain `shr reg, N` via tree-fold."""
    fn = _compile(_unsigned_pow2_div(divisor), watcom_10_0a)
    text = fn.disasm_text()
    assert fn.has_insn("shr", f"eax, {log2}") or (
        log2 == 1 and fn.has_insn("shr", "eax, 1")
    ), text
    # No sar (signed shift), no sbb, no idiv
    assert not fn.has_insn("sar"), text
    assert not fn.has_insn("sbb"), text
    assert not fn.has_insn("idiv"), text


# ---- Ternary-bias form vs branch-free idiom ----------------------------

def test_ternary_bias_form_uses_branch_not_idiom(watcom_10_0a):
    """The portable `(x < 0 ? x + 7 : x) >> 3` form emits a branch.

    Don't rewrite signed `/ 8` as the ternary-bias form: PS.EXE used
    the branch-free idiom.
    """
    fn = _compile(_ternary_bias(8), watcom_10_0a)
    text = fn.disasm_text()
    # Has a conditional branch
    has_jcc = any(
        i.mnemonic.startswith("j") and i.mnemonic != "jmp"
        for i in fn.insns
    )
    assert has_jcc, f"expected a conditional branch:\n{text}"
    # Does NOT have the sbb step that distinguishes the idiom
    assert not fn.has_insn("sbb"), text


def test_idiom_is_one_byte_shorter_than_ternary_bias(watcom_10_0a):
    """The branch-free idiom for /8 is 1 byte shorter than the ternary form."""
    idiom = _compile(_signed_pow2_div(8), watcom_10_0a)
    bias = _compile(_ternary_bias(8), watcom_10_0a)
    delta = bias.size() - idiom.size()
    assert delta == 1, (
        f"expected idiom to save 1 byte; got delta={delta}\n"
        f"--- IDIOM ({idiom.size()}b) ---\n{idiom.disasm_text()}\n"
        f"--- BIAS  ({bias.size()}b) ---\n{bias.disasm_text()}"
    )


def test_signed_div2_is_one_step_shorter_than_div4(watcom_10_0a):
    """`x / 2` saves one instruction compared to `x / 4` via By2Div."""
    div2 = _compile(_signed_pow2_div(2), watcom_10_0a)
    div4 = _compile(_signed_pow2_div(4), watcom_10_0a)
    # By2Div: sub+sar (2 insns); Pow2Div: shl+sbb+sar (3 insns)
    # The shl is `c1 e2 N` = 3 bytes => function is 4 bytes longer (3 + 1 for AddByte log2).
    # Actually shl is 3 bytes; the missing instruction in /2 saves 4 bytes
    delta = div4.size() - div2.size()
    assert delta == 4, (
        f"expected /2 to be 4 bytes shorter; got delta={delta}\n"
        f"--- /2 ({div2.size()}b) ---\n{div2.disasm_text()}\n"
        f"--- /4 ({div4.size()}b) ---\n{div4.disasm_text()}"
    )
