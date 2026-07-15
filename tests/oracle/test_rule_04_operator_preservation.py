"""Rule 4 - Watcom preserves `<` / `<=` / `>` / `>=` literally.

## Trigger

Watcom 10.0a does not normalise relational operators.  The C source
operator picks the immediate and the Jcc opcode byte-for-byte:

| C source     | Compare immediate | Branch (skip-body) |
|--------------|-------------------|--------------------|
| `x < 26`     | `cmp r, 0x1a`     | `jge skip`         |
| `x <= 25`    | `cmp r, 0x19`     | `jg  skip`         |
| `x > 25`     | `cmp r, 0x19`     | `jle skip`         |
| `x >= 26`    | `cmp r, 0x1a`     | `jl  skip`         |
| `x == 25`    | `cmp r, 0x19`     | `jne skip`         |
| `x != 25`    | `cmp r, 0x19`     | `je  skip`         |

`x <= 25` and `x < 26` are semantically equal but produce different
bytes; pick the form that matches PS.EXE.

## Sub-pattern: `cmp reg, 0` -> `test reg, reg`

For a *register-resident* operand compared against literal `0`,
Watcom collapses `cmp reg, 0` (4 bytes) to `test reg, reg` (2 bytes):

| C source  | Setup       | Asm                  | Bytes |
|-----------|-------------|----------------------|-------|
| `x > 0`   | reg in EAX  | `test eax, eax; jle` | 4     |
| `x >= 1`  | reg in EAX  | `cmp eax, 1; jl`     | 5     |
| `x <= 0`  | reg in EAX  | `test eax, eax; jg`  | 4     |
| `x < 1`   | reg in EAX  | `cmp eax, 1; jge`    | 5     |
| `x == 0`  | reg in EAX  | `test eax, eax; jne` | 4     |
| `x != 0`  | reg in EAX  | `test eax, eax; je`  | 4     |
| `x < 0`   | reg in EAX  | `test eax, eax; jge` | 4     |
| `x >= 0`  | reg in EAX  | `test eax, eax; jl`  | 4     |
| `x > -1`  | reg in EAX  | `cmp eax, -1; jle`   | 5     |
| `x <= -1` | reg in EAX  | `cmp eax, -1; jg`    | 5     |

The transform fires whenever the *literal numeric 0* appears in the
source operand position - including `x < 0` / `x >= 0`.  `x <= -1`
is semantically `x < 0` but does not get the `test` form because the
source literal is `-1`, not `0`.

The transform does **not** fire when op1 is a memory operand:
`cmp dword ptr [g], 0` stays as a 7-byte memory compare; converting
to `test mem, mem` would be longer.

## Mechanism

The front-end emits six distinct compare opcodes - `OP_CMP_EQUAL`,
`OP_CMP_NOT_EQUAL`, `OP_CMP_LESS`, `OP_CMP_LESS_EQUAL`,
`OP_CMP_GREATER`, `OP_CMP_GREATER_EQUAL` - visible at
`bld/cg/c/foldins.c:148`.  Each maps directly to a Jcc encoding
without any operator normalisation pass.

The cmp-vs-test selection is in the 32-bit compare optab `Cmp4` at
`bld/cg/intel/386/c/386table.c:1037`:

    _OE( _SidCC( R, C ), V_OP2ZERO, RG_DBL, G_TEST, FU_ALUX ),  // R,0 -> test
    _OE( _SidCC( R, R ), V_NO,      RG_DBL, G_RR2,  FU_ALUX ),
    _OE( _SidCC( R, M ), V_NO,      RG_DBL, G_RM2,  FU_ALUX ),
    _OE( _SidCC( R, C ), V_AC_BETTER, RG_DBL_ACC, G_AC, FU_ALUX ),
    _OE( _SidCC( R, C ), V_NO,      RG_DBL, G_RC,   FU_ALUX ),  // R,non-0 cmp
    _OE( _SidCC( M, C ), V_NO,      RG_,    G_MC,   FU_ALUX ),  // M,C cmp - no V_OP2ZERO

The `V_OP2ZERO` verifier (in `bld/cg/c/optab.c`) requires op2 to be
the integer constant 0.  It fires only on the `R, C` row, so memory
operands always go through `G_MC`.  The `R, R` and `R, M` rows have
no zero-shortcut because there's no shorter encoding to switch to.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_MEMORY_TEMPLATE = """\
extern int x, y;
extern void use(int);
void f(void) {{
    if ({cond}) {{
        use(1);
        y = 42;
    }}
    y = 0;
}}
"""

_REG_TEMPLATE = """\
extern int y;
extern int reader(void);
extern void use(int);
void f(void) {{
    int x = reader();
    if ({cond}) {{
        use(1);
        y = 42;
    }}
    y = 0;
}}
"""

_DEFS = (
    "int x; int y;\n"
    "int reader(void) { return 0; }\n"
    "void use(int v) { (void)v; }\n"
)


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _first_branch_pair(fn):
    """Return (cmp_or_test_insn, jcc_insn) for the first comparison/branch."""
    cmp_or_test = None
    for i in fn.insns:
        if i.mnemonic in ("cmp", "test"):
            cmp_or_test = i
        elif i.mnemonic.startswith("j") and cmp_or_test is not None:
            return cmp_or_test, i
    raise AssertionError(f"no cmp/test+jXX in:\n{fn.disasm_text()}")


def _imm_in(op_str: str, imm: int) -> bool:
    """Capstone formats positive imm <= 9 in decimal, larger in hex; negatives in decimal."""
    candidates = [f", {imm}"]
    if imm >= 0:
        candidates.append(f", {imm:#x}")
    return any(c in op_str for c in candidates)


# ---- Operator preservation (memory operand) -----------------------------

@pytest.mark.parametrize("cond,imm,jcc", [
    ("x < 26",   0x1a, "jge"),
    ("x <= 25",  0x19, "jg"),
    ("x > 25",   0x19, "jle"),
    ("x >= 26",  0x1a, "jl"),
    ("x == 25",  0x19, "jne"),
    ("x != 25",  0x19, "je"),
])
def test_operator_preserved_on_memory_operand(watcom_10_0a, cond, imm, jcc):
    """Each operator preserves its immediate and dictates the inverted Jcc.

    `x <= 25` and `x < 26` are semantically equal but emit different
    bytes - the source operator wins.
    """
    fn = _compile(_MEMORY_TEMPLATE.format(cond=cond), watcom_10_0a)
    cmp_ins, j_ins = _first_branch_pair(fn)
    assert cmp_ins.mnemonic == "cmp", fn.disasm_text()
    assert _imm_in(cmp_ins.op_str, imm), (
        f"expected immediate {imm:#x} for `{cond}`; got `{cmp_ins.line}`\n"
        f"{fn.disasm_text()}"
    )
    assert j_ins.mnemonic == jcc, (
        f"expected `{jcc}` for `{cond}`; got `{j_ins.line}`\n{fn.disasm_text()}"
    )


# ---- Operator preservation (register operand) ---------------------------

@pytest.mark.parametrize("cond,imm,jcc", [
    ("x < 26",   0x1a, "jge"),
    ("x <= 25",  0x19, "jg"),
    ("x > 25",   0x19, "jle"),
    ("x >= 26",  0x1a, "jl"),
])
def test_operator_preserved_on_register_operand(watcom_10_0a, cond, imm, jcc):
    """Same as the memory case but with a local-in-register operand."""
    fn = _compile(_REG_TEMPLATE.format(cond=cond), watcom_10_0a)
    cmp_ins, j_ins = _first_branch_pair(fn)
    assert cmp_ins.mnemonic == "cmp", fn.disasm_text()
    assert _imm_in(cmp_ins.op_str, imm), (
        f"expected immediate {imm:#x} for `{cond}`; got `{cmp_ins.line}`\n"
        f"{fn.disasm_text()}"
    )
    assert j_ins.mnemonic == jcc, (
        f"expected `{jcc}` for `{cond}`; got `{j_ins.line}`\n{fn.disasm_text()}"
    )


# ---- Sub-pattern: cmp reg, 0 -> test reg, reg ---------------------------

@pytest.mark.parametrize("cond,jcc", [
    ("x > 0",   "jle"),
    ("x <= 0",  "jg"),
    ("x == 0",  "jne"),
    ("x != 0",  "je"),
    ("x < 0",   "jge"),
    ("x >= 0",  "jl"),
])
def test_zero_compare_register_uses_test(watcom_10_0a, cond, jcc):
    """Direct comparison against literal 0 in a register collapses to `test`."""
    fn = _compile(_REG_TEMPLATE.format(cond=cond), watcom_10_0a)
    cmp_ins, j_ins = _first_branch_pair(fn)
    assert cmp_ins.mnemonic == "test", (
        f"expected `test` for `{cond}`; got `{cmp_ins.line}`\n{fn.disasm_text()}"
    )
    assert "eax, eax" in cmp_ins.op_str, (
        f"expected `test eax, eax`; got `{cmp_ins.line}`\n{fn.disasm_text()}"
    )
    assert j_ins.mnemonic == jcc, (
        f"expected `{jcc}` for `{cond}`; got `{j_ins.line}`\n{fn.disasm_text()}"
    )


@pytest.mark.parametrize("cond,imm", [
    ("x >= 1",  1),    # off-by-one of `x > 0`
    ("x < 1",   1),    # off-by-one of `x <= 0`
    ("x > -1",  -1),   # off-by-one of `x >= 0`
    ("x <= -1", -1),   # off-by-one of `x < 0`
])
def test_off_by_one_keeps_cmp(watcom_10_0a, cond, imm):
    """Semantically equivalent off-by-one forms do NOT trigger the test transform.

    The literal numeric 0 must appear in the source operand position;
    `x >= 1` (which is semantically `x > 0`) is encoded as `cmp eax, 1`
    not `test eax, eax`.
    """
    fn = _compile(_REG_TEMPLATE.format(cond=cond), watcom_10_0a)
    cmp_ins, _ = _first_branch_pair(fn)
    assert cmp_ins.mnemonic == "cmp", (
        f"expected `cmp` for `{cond}`; got `{cmp_ins.line}`\n{fn.disasm_text()}"
    )
    # capstone formats small positive ints decimal, larger ones hex; check both.
    candidates = (
        [f", {imm}", f", {imm:#x}"] if imm >= 0
        else [f", {imm}"]      # negatives are always decimal
    )
    assert any(c in cmp_ins.op_str for c in candidates), (
        f"expected immediate {imm} for `{cond}`; got `{cmp_ins.line}`"
    )


def test_zero_compare_memory_keeps_cmp(watcom_10_0a):
    """`cmp [g], 0` on memory does NOT collapse to a `test` form.

    The optab routes `M, C` to `G_MC` regardless of constant value -
    no shorter encoding exists for a memory `test`.
    """
    fn = _compile(_MEMORY_TEMPLATE.format(cond="x > 0"), watcom_10_0a)
    cmp_ins, _ = _first_branch_pair(fn)
    assert cmp_ins.mnemonic == "cmp", fn.disasm_text()
    assert "dword ptr" in cmp_ins.op_str, fn.disasm_text()
    assert ", 0" in cmp_ins.op_str, fn.disasm_text()


def test_test_is_one_byte_shorter_than_cmp(watcom_10_0a):
    """`test eax, eax` (2 bytes) saves 3 bytes vs `cmp eax, 0` (5 bytes)."""
    test_form = _compile(_REG_TEMPLATE.format(cond="x > 0"),  watcom_10_0a)
    cmp_form  = _compile(_REG_TEMPLATE.format(cond="x >= 1"), watcom_10_0a)
    delta = test_form.size() - cmp_form.size()
    # `test eax,eax`(2) vs `cmp eax,1`(3) - 1-byte saving for the compare,
    # no change to the Jcc length.  Net function size shrinks by 1 byte.
    assert delta == -1, (
        f"expected test-form 1 byte shorter; got delta={delta}\n"
        f"--- TEST ({test_form.size()}b) ---\n{test_form.disasm_text()}\n"
        f"--- CMP  ({cmp_form.size()}b) ---\n{cmp_form.disasm_text()}"
    )
