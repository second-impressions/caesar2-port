"""Rule 13 - Per-branch vs hoisted shared call: source structure matters.

## Trigger

When multiple if/else branches each end with the same function
call (different args per branch), the C source can be written two
ways:

1. **Per-branch** - each branch contains its own ``call`` statement:
   ```c
   if      (cond == 0) readfile(&a, dst, 0x1000, 0);
   else if (cond == 1) readfile(&b, dst, 0x2000, 0);
   else                readfile(&c, dst, 0x4000, 0);
   ```
2. **Hoisted** - the call is lifted past the if-tree, with each
   branch storing into shared locals first:
   ```c
   int *fname; int sz;
   if      (cond == 0) { fname = &a; sz = 0x1000; }
   else if (cond == 1) { fname = &b; sz = 0x2000; }
   else                { fname = &c; sz = 0x4000; }
   readfile(fname, dst, sz, 0);
   ```

Both forms tail-merge into a single ``call; ret`` epilogue (Rule
15's `ComTail` mechanism, applied intra-function).  The two forms
produce **different bytes** in two distinct ways:

  * **When some args are constant across branches** (like
    `dst` and `0` above): the hoisted form is **smaller** because
    each branch only loads the *varying* args; the constant args
    are loaded once before the call.  PS.EXE would show only the
    varying args being loaded per branch.
  * **When all args differ per branch**: both forms produce the
    **same total size**, but the per-branch arg-load order in each
    branch is **right-to-left** (matching the call's argument
    evaluation), while the hoisted form's order matches the
    source's local-variable assignment order.

## Mechanism

`ComTail` in `bld/cg/c/optcom.c:212` is invoked from
`bld/cg/c/optins.c:309` whenever an `OC_RET` instruction is added
to the per-function `RetList`.  It walks the list looking for the
longest common suffix between the new ret-block and any earlier
ret-block; if savings exceed `OptInsSize(OC_JMP, OC_DEST_NEAR)` (5
bytes) and `OptForSize >= 25` (default 50), it emits a join label
and rewrites the duplicated suffix as a `jmp_near` to that label.

Args are pushed during AST walk (`bld/cc/c/cgen.c:1530`,
`OPR_PARM` case).  The order in which arg-load `mov` instructions
appear in the final asm follows the per-branch arg evaluation,
which is right-to-left under `__watcall`.  The hoisted form
breaks that link - the local-variable assignments are arranged in
source order, then materialised before the call.

## Matching PS.EXE

Look at the per-branch suffixes in PS.EXE:

  * If each branch loads **only the varying args** before
     ``jmp tail``, the source was hoisted; common args are loaded
     once at the join.
  * If each branch loads **all N args** (including ones identical
     across branches), the source was per-branch.

The doc's previous mechanism note ("the hoisted form forces extra
spills, ... pay for an unconditional join block") was incorrect.
Both forms tail-merge cleanly; the byte difference is in *which
args appear in which block*, not in extra spills or epilogue
overhead.

## Verified on

  * `swap_circus_gfx` (c2.c): 6 readfile() call sites, each
     branch loads ``edx=building_data4; xor ecx,ecx; mov ebx,sz;
     mov eax,&fname_blob`` and jumps to a single
     ``call readfile; pop pop pop; ret`` epilogue at L448
     (commit 767c8ba).  Each branch sets the common args
     (``building_data4``, ``0``) - confirming the source used
     per-branch calls.
  * `tests/oracle/test_rule_13_call_hoist_vs_per_branch.py` - 4
     tests covering: with-common-args (hoisted smaller), all-args-
     differ (both same size), shared-tail merge for both forms,
     per-branch sets constants in each branch.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "int zoom_level;\n"
    "int a, b, c;\n"
    "int dst[10];\n"
    "int readfile(int *fname, int *buf, int sz, int mode) "
    "{ (void)fname; (void)buf; (void)sz; (void)mode; return 0; }\n"
)


_PER_BRANCH_COMMON = """\
extern int zoom_level;
extern int a, b, c;
extern int dst[10];
extern int readfile(int *fname, int *buf, int sz, int mode);
void f(void) {
    if      (zoom_level == 0) readfile(&a, dst, 0x1000, 0);
    else if (zoom_level == 1) readfile(&b, dst, 0x2000, 0);
    else                      readfile(&c, dst, 0x4000, 0);
}
"""

_HOISTED_COMMON = """\
extern int zoom_level;
extern int a, b, c;
extern int dst[10];
extern int readfile(int *fname, int *buf, int sz, int mode);
void f(void) {
    int *fname; int sz;
    if      (zoom_level == 0) { fname = &a; sz = 0x1000; }
    else if (zoom_level == 1) { fname = &b; sz = 0x2000; }
    else                      { fname = &c; sz = 0x4000; }
    readfile(fname, dst, sz, 0);
}
"""

_PER_BRANCH_ALL_DIFF = """\
extern int zoom_level;
extern int a, b, c;
extern int dst[10];
extern int readfile(int *fname, int *buf, int sz, int mode);
void f(void) {
    if      (zoom_level == 0) readfile(&a, &dst[0], 0x1000, 11);
    else if (zoom_level == 1) readfile(&b, &dst[3], 0x2000, 22);
    else                      readfile(&c, &dst[6], 0x4000, 33);
}
"""

_HOISTED_ALL_DIFF = """\
extern int zoom_level;
extern int a, b, c;
extern int dst[10];
extern int readfile(int *fname, int *buf, int sz, int mode);
void f(void) {
    int *fname; int *buf; int sz; int mode;
    if      (zoom_level == 0) { fname = &a; buf = &dst[0]; sz = 0x1000; mode = 11; }
    else if (zoom_level == 1) { fname = &b; buf = &dst[3]; sz = 0x2000; mode = 22; }
    else                      { fname = &c; buf = &dst[6]; sz = 0x4000; mode = 33; }
    readfile(fname, buf, sz, mode);
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _count(fn, mnemonic, op_substr=""):
    return sum(1 for i in fn.insns
               if i.mnemonic == mnemonic and op_substr in i.op_str)


def test_hoisted_smaller_when_args_share_constants(watcom_10_0a):
    """When `dst` and `0` are common across branches, hoisting saves bytes."""
    pb = _compile(_PER_BRANCH_COMMON, watcom_10_0a)
    hh = _compile(_HOISTED_COMMON, watcom_10_0a)
    assert hh.size() < pb.size(), (
        f"expected hoisted < per-branch when args share constants;\n"
        f"per-branch={pb.size()}b hoisted={hh.size()}b"
    )


def test_both_forms_same_size_when_all_args_differ(watcom_10_0a):
    """Without common args, both forms compile to the same total size."""
    pb = _compile(_PER_BRANCH_ALL_DIFF, watcom_10_0a)
    hh = _compile(_HOISTED_ALL_DIFF, watcom_10_0a)
    assert pb.size() == hh.size(), (
        f"expected same size; per-branch={pb.size()}b hoisted={hh.size()}b"
    )


def test_both_forms_share_one_call_via_tail_merge(watcom_10_0a):
    """Both forms tail-merge into a single `call readfile`."""
    for src in (_PER_BRANCH_COMMON, _HOISTED_COMMON,
                _PER_BRANCH_ALL_DIFF, _HOISTED_ALL_DIFF):
        fn = _compile(src, watcom_10_0a)
        n_calls = _count(fn, "call")
        assert n_calls == 1, (
            f"expected exactly 1 `call` (tail-merged); got {n_calls}\n"
            f"{fn.disasm_text()}"
        )


def test_per_branch_loads_constant_args_in_each_branch(watcom_10_0a):
    """Per-branch form loads the common ``building_data4``-equivalent
    (here: address of `dst`) and the constant `0` (mode arg) in EVERY
    branch.

    PS.EXE's `swap_circus_gfx` shows this exact pattern: each of the
    six call sites loads ``edx = building_data4; xor ecx, ecx;`` even
    though those args are identical for all six.  This is the rule's
    diagnostic - if PS.EXE shows constant args being set per branch,
    the source was per-branch (not hoisted).
    """
    fn = _compile(_PER_BRANCH_COMMON, watcom_10_0a)
    # Three branches each set xor ecx, ecx (the `0` mode arg)
    n_xor_ecx = sum(1 for i in fn.insns
                    if i.mnemonic == "xor" and i.op_str == "ecx, ecx")
    # Three `mov edx, &dst` (5-byte b8/ba opcode + 4 fixup bytes for the
    # symbol address; capstone renders the masked immediate as 0).
    n_mov_edx_addr = sum(1 for i in fn.insns
                         if i.mnemonic == "mov"
                         and i.size == 5
                         and i.raw[0] == 0xBA  # mov edx, imm32
                         and sum(i.fixup_mask[1:]) == 4)
    assert n_xor_ecx == 3, (
        f"expected 3 `xor ecx, ecx` (one per branch); got {n_xor_ecx}\n"
        f"{fn.disasm_text()}"
    )
    assert n_mov_edx_addr == 3, (
        f"expected 3 `mov edx, &dst` (one per branch); got {n_mov_edx_addr}\n"
        f"{fn.disasm_text()}"
    )


def test_hoisted_loads_constant_args_once(watcom_10_0a):
    """Hoisted form loads the constant args (`dst`, `0`) once before the call."""
    fn = _compile(_HOISTED_COMMON, watcom_10_0a)
    n_xor_ecx = sum(1 for i in fn.insns
                    if i.mnemonic == "xor" and i.op_str == "ecx, ecx")
    # Should be exactly one xor ecx, ecx (in the join block)
    assert n_xor_ecx == 1, (
        f"expected 1 `xor ecx, ecx` in join block; got {n_xor_ecx}\n"
        f"{fn.disasm_text()}"
    )
