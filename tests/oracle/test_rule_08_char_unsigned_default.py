"""Rule 8 - Plain ``char`` defaults to unsigned on Watcom 10.0a.

## Trigger

Plain ``char`` (no explicit ``signed``/``unsigned`` qualifier)
behaves as ``unsigned char``:

  * Reading a ``char`` field/global widens via zero-extend
    (``xor reg, reg; mov rl, [m]``).
  * Reading a ``signed char`` field/global widens via sign-extend
    (``movsx reg, byte ptr [m]``).
  * Reading an ``unsigned char`` is identical to plain ``char``.

If the diff shows ``movsx`` where the recomp emits ``xor + mov``,
the original field/global was declared ``signed char`` (explicit).

## Parameter spilling

Watcom\u2019s register convention passes the first 1-byte parm in the
8-bit half of EAX (AL) and the second in DL.  When the function
takes the address of the parm or stores it across calls, the parm
must be spilled to the stack:

| Param type | Spill instruction      | Reload                    |
|------------|------------------------|---------------------------|
| ``char``           | ``mov [esp+N], al``  | ``xor eax,eax; mov al,[esp+N]`` |
| ``unsigned char``  | same as ``char``     | same                            |
| ``signed char``    | ``mov [esp+N], al``  | ``movsx eax, byte ptr [esp+N]`` |
| ``int``            | ``push eax`` or ``mov dword ptr [esp+N], edx`` | ``mov eax, [esp+N]``     |

If PS.EXE shows ``mov dword ptr [esp+N], edx`` for a parm spill,
the parm was declared ``int``, not ``char`` / ``signed char``.
Promote ``char X`` parms to ``int X`` when the diff shows that
shape.

## Mechanism

`SetPlainCharType(TYP_UCHAR)` in `bld/cc/c/ctype.c:131` is the
default initialisation (called from `BaseTypesInit`).  The ``-j``
flag flips it via `SetSignedChar()` (`bld/cc/c/ctype.c:218`),
which calls `SetPlainCharType(TYP_CHAR)`.

Character constants are typed by `bld/cc/c/cscan.c:1439-1450`:
without ``-j`` they\u2019re ``TYP_UCHAR``; with ``-j`` they\u2019re ``TYP_CHAR``
(narrowed from 0\u2026255 to -128\u2026127 if needed).

PS.EXE was compiled **without** ``-j``: applying ``-j`` globally
regresses the byte-match score.  When a specific field truly is
``signed char``, declare it explicitly per-field.

## Caveat

The rule is **per-field / per-parameter**.  A blanket
``char -> signed char`` sweep regresses the score in functions
that use ``char`` fields the natural unsigned way.  Apply only
where the diff visibly shows ``movsx`` mismatch.

## Verified on

  * `get_nearest_enemy_to_track` (dropped ``(char)`` casts on
     ``.type``).
  * `get_army_name_from_fort_ref` (struct ``army_rec.name`` ->
     ``signed char``; dropped ``(int)(char)`` cast).
  * `create_arrow` (struct ``arrow_rec.grid_x`` /
     ``.grid_y`` -> ``signed char``; dropped ``(char)`` casts;
     param ``char arrow_type`` -> ``int``).
  * `create_unit` (3 char params promoted to int).
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


def _read_global(qual):
    """Build a snippet that reads a global of the given char qualifier."""
    src = f"""\
extern {qual} char G;
extern int result;
void f(void) {{ result = G; }}
"""
    defs = f"{qual} char G; int result;\n"
    return src, defs


def _spill_param(arg_type):
    src = f"""\
extern void take_addr(void *p);
int f({arg_type} x) {{
    take_addr(&x);
    return x;
}}
"""
    defs = "void take_addr(void *p) { (void)p; }\n"
    return src, defs


def _multi_spill(a_type, b_type):
    src = f"""\
extern void take_two(void *p, void *q);
void f({a_type} a, {b_type} b) {{
    take_two(&a, &b);
}}
"""
    defs = "void take_two(void *p, void *q) { (void)p; (void)q; }\n"
    return src, defs


def _compile(source, defs, image):
    b = compile_snippet(source, image=image, extern_defs=defs)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


# ---- Read of a char global widens via zero-extend ----------------------

def test_plain_char_global_uses_zero_extend(watcom_10_0a):
    """Reading ``char G`` emits ``xor + mov`` (zero-extend, unsigned)."""
    src, defs = _read_global("")
    fn = _compile(src, defs, watcom_10_0a)
    assert fn.has_insn("xor", "eax, eax"), fn.disasm_text()
    assert fn.has_insn("mov", "al, byte ptr"), fn.disasm_text()
    assert not fn.has_insn("movsx"), fn.disasm_text()


def test_unsigned_char_global_matches_plain_char(watcom_10_0a):
    """``unsigned char`` is byte-identical to plain ``char`` (default).

    Confirms plain ``char`` is unsigned on Watcom 10.0a without ``-j``.
    """
    src1, defs1 = _read_global("")
    src2, defs2 = _read_global("unsigned")
    a = _compile(src1, defs1, watcom_10_0a)
    b = _compile(src2, defs2, watcom_10_0a)
    a_masked = bytes(0 if (a.base + k) in a.fixups else x
                     for k, x in enumerate(a.bytes_))
    b_masked = bytes(0 if (b.base + k) in b.fixups else x
                     for k, x in enumerate(b.bytes_))
    assert a_masked == b_masked, (
        f"plain char and unsigned char should be identical:\n"
        f"--- PLAIN ---\n{a.disasm_text()}\n"
        f"--- UNSIGNED ---\n{b.disasm_text()}"
    )


def test_signed_char_global_uses_movsx(watcom_10_0a):
    """Reading ``signed char G`` emits ``movsx`` (sign-extend)."""
    src, defs = _read_global("signed")
    fn = _compile(src, defs, watcom_10_0a)
    assert fn.has_insn("movsx", "byte ptr"), fn.disasm_text()
    assert not fn.has_insn("xor", "eax, eax"), fn.disasm_text()


# ---- Parameter spill: char vs int ---------------------------------------

def test_char_param_spills_byte(watcom_10_0a):
    """``char`` param spill emits ``mov byte ptr [esp], al``."""
    src, defs = _spill_param("char")
    fn = _compile(src, defs, watcom_10_0a)
    assert any(
        i.mnemonic == "mov"
        and i.op_str.startswith("byte ptr [esp")
        and ", al" in i.op_str
        for i in fn.insns
    ), fn.disasm_text()


def test_int_param_spills_dword_or_uses_push(watcom_10_0a):
    """``int`` param spill is either ``push eax`` (single param) or
    ``mov dword ptr [esp], edx`` (multi-param)."""
    # Single param case: push eax
    src, defs = _spill_param("int")
    fn = _compile(src, defs, watcom_10_0a)
    assert fn.has_insn("push", "eax"), fn.disasm_text()
    # No byte spill
    assert not any(
        i.mnemonic == "mov" and i.op_str.startswith("byte ptr [esp")
        for i in fn.insns
    ), fn.disasm_text()


def test_int_int_two_param_spill_uses_dword_pushes(watcom_10_0a):
    """Two ``int`` params spill via ``push eax; push edx``."""
    src, defs = _multi_spill("int", "int")
    fn = _compile(src, defs, watcom_10_0a)
    push_eax = sum(1 for i in fn.insns if i.mnemonic == "push" and i.op_str == "eax")
    push_edx = sum(1 for i in fn.insns if i.mnemonic == "push" and i.op_str == "edx")
    assert push_eax == 1 and push_edx == 1, fn.disasm_text()


def test_char_int_two_param_spill_distinguishes_widths(watcom_10_0a):
    """Mixed ``char, int`` param spill emits one byte spill and one dword spill.

    This is the tell that the rule documents: when PS.EXE shows
    ``mov dword ptr [esp+N], edx`` it's an ``int`` parm.
    """
    src, defs = _multi_spill("char", "int")
    fn = _compile(src, defs, watcom_10_0a)
    byte_spill = any(
        i.mnemonic == "mov"
        and i.op_str.startswith("byte ptr [esp")
        and ", al" in i.op_str
        for i in fn.insns
    )
    dword_spill = any(
        i.mnemonic == "mov"
        and i.op_str.startswith("dword ptr [esp")
        and ", edx" in i.op_str
        for i in fn.insns
    )
    assert byte_spill, f"expected `mov byte ptr [esp+N], al`:\n{fn.disasm_text()}"
    assert dword_spill, f"expected `mov dword ptr [esp+N], edx`:\n{fn.disasm_text()}"


# ---- Reload after spill ------------------------------------------------

def test_signed_char_reload_uses_movsx(watcom_10_0a):
    """Spilled ``signed char`` reload emits ``movsx``, not zero-extend."""
    src, defs = _spill_param("signed char")
    fn = _compile(src, defs, watcom_10_0a)
    assert any(
        i.mnemonic == "movsx" and "byte ptr [esp" in i.op_str
        for i in fn.insns
    ), fn.disasm_text()


def test_plain_char_reload_uses_zero_extend(watcom_10_0a):
    """Spilled plain ``char`` reload emits ``xor + mov al`` (no movsx)."""
    src, defs = _spill_param("char")
    fn = _compile(src, defs, watcom_10_0a)
    assert fn.has_insn("xor", "eax, eax"), fn.disasm_text()
    assert any(
        i.mnemonic == "mov"
        and i.op_str.startswith("al, byte ptr [esp")
        for i in fn.insns
    ), fn.disasm_text()
    assert not fn.has_insn("movsx"), fn.disasm_text()
