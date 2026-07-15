"""Rule 14 - Bare ``ret`` (no EAX preload) means the function returns ``void``.

## Trigger

In ``__watcall``, an integer return value is left in EAX.  Watcom
materialises that value with an explicit instruction immediately
before the ``ret``:

  * ``return 0;``       -> ``xor eax, eax; ret``  (3 bytes, +2 over bare ret)
  * ``return 1;``       -> ``mov eax, 1; ret``    (6 bytes, +5 over bare ret)
  * ``return EXPR;``    -> ``<eval EXPR into eax>; ret``

A ``void`` return emits **no EAX-setting instruction**:

  * ``return;`` (in a void function)  -> bare ``ret``
  * implicit fallthrough               -> bare ``ret``

If PS.EXE shows a bare ``ret`` (or ``pop ...; ret``) at the end of
a function with no preceding ``mov eax``/``xor eax, eax``, the
function was declared ``void``.  Even when call sites appear to
consume the return (``if (foo()) ...``), the value being read is
whatever incidental register state was left over (often a flag
read inside the function); the C source still declared ``void``.

## Mechanism

`bld/cc/c/cgen.c:287-296` selects between two `CGReturn` invocations:

```c
if (node->u2.sym_handle == SYM_NULL) {
    dtype = CGenType(CurFunc->sym_type->object);
    CGReturn(NULL, dtype);                 /* void return */
} else {
    SymGet(&sym, node->u2.sym_handle);
    dtype = CGenType(sym.sym_type);
    name = CGTempName(sym.u1.return_var, dtype);
    name = CGUnary(O_POINTS, name, dtype);
    CGReturn(name, ReturnType(dtype));     /* value return */
}
```

`CGReturn(NULL, ...)` in `bld/cg/c/intrface.c:674` skips the
`TGReturn(name, ...)` call that would otherwise generate the
EAX-load IR.  `BGReturn(NULL, ...)` then emits the bare `ret`.

The ``return EXPR;`` path always generates a value-into-EAX IR
node, even for ``return 0;``: the back-end recognises the constant
0 and lowers it to ``xor eax, eax`` (2 bytes) instead of
``mov eax, 0`` (5 bytes) via standard peephole.

## Right C

```c
void show_pl8file(char *name) {
    if (!readfile_chk(name)) { beep(); return; }
    flush();
}
```

## Wrong C

```c
int show_pl8file(char *name) {           /* WRONG: PS shows bare `ret` */
    if (!readfile_chk(name)) { beep(); return 0; }
    flush();
    return 1;
}
```

## Verified on

  * `show_pl8file`, `display_pl8file`, `show_picfile`,
     `display_picfile` in `display.c` (commit `a36a942`).
  * `tests/oracle/test_rule_14_void_return.py` - 5 tests:
     ``return 0;`` emits ``xor eax, eax``; ``return 1;`` emits
     ``mov eax, 1``; ``return;`` (void fn) emits no EAX-set;
     fallthrough on a void fn emits no EAX-set; an int->void
     conversion drops the EAX-set bytes.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "void beep(void) {}\n"
    "void flush(void) {}\n"
    "int readfile_chk(char *name) { (void)name; return 0; }\n"
)


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b


def _has(fn, mnem, op_substr):
    return any(i.mnemonic == mnem and op_substr in i.op_str for i in fn.insns)


def test_return_zero_emits_xor_eax_eax(watcom_10_0a):
    """``int f() { return 0; }`` materialises EAX via ``xor eax, eax``."""
    src = """\
int f(void) { return 0; }
"""
    fn = _compile(src, watcom_10_0a).function("f")
    assert _has(fn, "xor", "eax, eax"), fn.disasm_text()
    assert any(i.mnemonic == "ret" for i in fn.insns), fn.disasm_text()


def test_return_one_emits_mov_eax_1(watcom_10_0a):
    """``int f() { return 1; }`` materialises EAX via ``mov eax, 1``."""
    src = """\
int f(void) { return 1; }
"""
    fn = _compile(src, watcom_10_0a).function("f")
    assert _has(fn, "mov", "eax, 1"), fn.disasm_text()


def test_void_explicit_return_no_eax_set(watcom_10_0a):
    """``void f() { return; }`` emits a bare ``ret`` with no EAX set."""
    src = """\
extern void beep(void);
void f(void) { beep(); return; }
"""
    fn = _compile(src, watcom_10_0a).function("f")
    # No xor/mov targeting eax should appear (only the call to beep)
    assert not _has(fn, "xor", "eax, eax"), fn.disasm_text()
    assert not _has(fn, "mov", "eax,"), fn.disasm_text()
    assert any(i.mnemonic in ("ret", "jmp") for i in fn.insns), fn.disasm_text()


def test_void_fallthrough_no_eax_set(watcom_10_0a):
    """A void function with implicit fallthrough also emits no EAX set."""
    src = """\
extern void beep(void);
void f(void) { beep(); }
"""
    fn = _compile(src, watcom_10_0a).function("f")
    assert not _has(fn, "xor", "eax, eax"), fn.disasm_text()
    assert not _has(fn, "mov", "eax,"), fn.disasm_text()


def test_int_to_void_conversion_drops_eax_set_bytes(watcom_10_0a):
    """Switching from int->void on the same body removes the EAX-load
    instructions, leaving the recomp's bytes shorter and matching what
    PS.EXE shows when the original function was declared void."""

    INT_BODY = """\
extern void beep(void);
extern void flush(void);
extern int readfile_chk(char *name);
int f(char *name) {
    if (!readfile_chk(name)) { beep(); return 0; }
    flush();
    return 1;
}
"""
    VOID_BODY = """\
extern void beep(void);
extern void flush(void);
extern int readfile_chk(char *name);
void f(char *name) {
    if (!readfile_chk(name)) { beep(); return; }
    flush();
}
"""
    int_fn = _compile(INT_BODY, watcom_10_0a).function("f")
    void_fn = _compile(VOID_BODY, watcom_10_0a).function("f")

    # int form has both `xor eax, eax` and `mov eax, 1`
    assert _has(int_fn, "xor", "eax, eax"), int_fn.disasm_text()
    assert _has(int_fn, "mov", "eax, 1"), int_fn.disasm_text()
    # void form has neither
    assert not _has(void_fn, "xor", "eax, eax"), void_fn.disasm_text()
    assert not _has(void_fn, "mov", "eax,"), void_fn.disasm_text()
    # And the void form is strictly smaller
    assert void_fn.size() < int_fn.size(), (
        f"expected void < int; got void={void_fn.size()} int={int_fn.size()}"
    )
