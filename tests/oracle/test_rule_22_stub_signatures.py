"""Rule 22 - Stub signatures must match real arg widths.

## Trigger

Operational rather than pure codegen.  When a callee is still a
stub, its signature must match the real ABI even when the body is
empty - otherwise the **caller\u2019s call-site bytes differ** from
PS.EXE\u2019s.

Two cases that differ:

  * Callee declared `void X(int p);` and caller passes `0x36`:
    caller emits ``mov eax, 0x36; call X`` (10 bytes total at the
    call site).
  * Callee declared `void X(void);` and caller passes no args:
    caller emits ``call X`` only (5 bytes).

If PS.EXE\u2019s caller shows ``mov eax, 0x36; call X``, the original
declaration was ``void X(int)`` (or compatible).  An auto-generated
``void X(void)`` stub will produce a 5-byte call site - 5 bytes
shorter than PS.EXE.

## Mechanism

The C front-end checks the callee\u2019s prototype during expression
analysis (`bld/cc/c/cgen.c:1530-1532`, `OPR_PARM` case).  If the
prototype declares `(void)`, no `OPR_PARM` IR nodes are emitted
for any actual arguments at the call site (and the source itself
can\u2019t syntactically pass any).  If the prototype declares `(int)`,
each argument generates a `CGAddParm(call, arg, TY_INTEGER)` call
which materialises the arg in the right `__watcall` register
before the call.

The back-end has no visibility into the callee\u2019s actual body when
generating the call-site - it trusts the prototype.  An empty
function body with the right prototype generates the same call
bytes as a full implementation with that prototype.

## Right C: match the real ABI on stubs

```c
void get_movement_image(int img_id) { (void)img_id; }   /* stub */
```

Not:

```c
void get_movement_image(void) {}                        /* WRONG */
```

## Verified on

  * Repeatedly while decompiling the int_c2 state-handler family
     (commit `fe80333`); also bit `confirm`, `alter_slave_reqs`,
     `region_go_to_target`, `sail_to_target`,
     `citizen_maraude_to_target`.
  * `tests/oracle/test_rule_22_stub_signatures.py` - 3 tests:
     `void(int)` stub + `call(0x36)` -> 10-byte call site;
     `void(void)` stub + `call()` -> 5-byte call site;
     even an empty function body with `void(int)` matches a full
     implementation\u2019s call-site bytes.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "void get_movement_image(int img_id) { (void)img_id; }\n"
    "void get_movement_image_void(void) { }\n"
)


_INT_PROTO_PASSES_ARG = """\
extern void get_movement_image(int img_id);
void f(void) {
    get_movement_image(0x36);
}
"""

_VOID_PROTO_NO_ARG = """\
extern void get_movement_image_void(void);
void f(void) {
    get_movement_image_void();
}
"""

_FULL_CALLEE = """\
void get_movement_image(int img_id) {
    (void)img_id;
    /* simulated full implementation */
}
extern int dst;
void f(void) {
    get_movement_image(0x36);
}
"""

_STUB_CALLEE = """\
void get_movement_image(int img_id) {
    (void)img_id;
}
extern int dst;
void f(void) {
    get_movement_image(0x36);
}
"""


def _compile(source, defs, image):
    b = compile_snippet(source, image=image, extern_defs=defs)
    assert b.ok, b.output
    return b.function("f")


def test_int_proto_emits_arg_load_at_call_site(watcom_10_0a):
    """`void X(int);` + `X(0x36);` -> caller emits `mov eax, 0x36`."""
    fn = _compile(_INT_PROTO_PASSES_ARG, _DEFS, watcom_10_0a)
    has_arg_load = any(
        i.mnemonic == "mov" and i.op_str == "eax, 0x36"
        for i in fn.insns
    )
    assert has_arg_load, fn.disasm_text()


def test_void_proto_emits_no_arg_load(watcom_10_0a):
    """`void X(void);` + `X();` -> caller has NO arg-load instruction."""
    fn = _compile(_VOID_PROTO_NO_ARG, _DEFS, watcom_10_0a)
    has_arg_load = any(
        i.mnemonic == "mov"
        and "eax" in i.op_str
        and "[" not in i.op_str
        for i in fn.insns
    )
    assert not has_arg_load, fn.disasm_text()


def test_call_site_size_differs(watcom_10_0a):
    """The two call shapes produce different total function sizes."""
    fn_int = _compile(_INT_PROTO_PASSES_ARG, _DEFS, watcom_10_0a)
    fn_void = _compile(_VOID_PROTO_NO_ARG, _DEFS, watcom_10_0a)
    # int proto adds 5 bytes for `mov eax, 0x36`
    assert fn_int.size() > fn_void.size(), (
        f"expected int-proto call site larger; "
        f"int={fn_int.size()}, void={fn_void.size()}"
    )
