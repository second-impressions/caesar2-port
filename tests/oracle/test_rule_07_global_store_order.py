"""Rule 7 - Source order of global stores is preserved verbatim.

## Trigger

When a value flows into both a global and a callee-saved register
(for use after a downstream call), the order of those two writes in
the asm follows the C source order:

```c
peace_rating = t / 10;          /* statement 1 */
orig         = peace_rating;    /* statement 2 */
adj = helper(orig, 1);
flag = (orig > adj);            /* orig live across helper -> stashed in EBX */
```

emits

    mov  [peace_rating], eax    ; <-- statement 1
    mov  ebx, eax                ; <-- statement 2 (orig in EBX)
    ...
    call helper

while

```c
orig         = t / 10;
peace_rating = orig;
adj = helper(orig, 1);
flag = (orig > adj);
```

emits

    mov  ebx, eax                ; <-- now first
    mov  [peace_rating], eax    ; <-- now second
    ...
    call helper

The two pairs are equivalent in semantics; PS.EXE picked one specific
order, and matching it is just a matter of writing the C statements
in the same order.

## Mechanism

This is a direct consequence of Rule 3.  The C front-end's
``CGAssign`` (``bld/cg/c/intrface.c:876``) is called for each ``=``
statement in source order; each call appends one IR instruction
whose result is the destination.  No general reordering pass exists
for instructions with side effects, so the two stores remain in
source order through the back-end.

The reason both stores survive (rather than the first being dead-
store-eliminated) is the same as Rule 3: ``CheckUseful`` in
``bld/cg/c/insdead.c:269`` unconditionally marks any instruction
with ``N_MEMORY`` or ``N_REGISTER`` result as useful.  Both the
global store and the EBX-cache stay alive.

## Why this matters

When PS.EXE shows ``mov [g], reg`` before ``mov ebx, reg``, the C
source had the global assignment first.  Vice-versa for the other
order.  Don't try to "tidy" by rearranging - just match PS.EXE.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "int t; int peace_rating; int dst; int flag;\n"
    "int helper(int x, int y) { (void)x; (void)y; return 0; }\n"
)


_GLOBAL_FIRST = """\
extern int t, peace_rating, dst, flag;
extern int helper(int x, int y);
void f(void) {
    int orig, adj;
    peace_rating = t / 10;
    orig = peace_rating;
    adj = helper(orig, 1);
    flag = (orig > adj);
}
"""


_LOCAL_FIRST = """\
extern int t, peace_rating, dst, flag;
extern int helper(int x, int y);
void f(void) {
    int orig, adj;
    orig = t / 10;
    peace_rating = orig;
    adj = helper(orig, 1);
    flag = (orig > adj);
}
"""


def _compile(source, image):
    b = compile_snippet(source, image=image, extern_defs=_DEFS)
    assert b.ok, f"build failed:\n{b.output}"
    return b.function("f")


def _store_and_save_indices(fn, global_offset_str):
    """Find indices of the global-store and the `mov ebx, eax` save.

    Returns (store_idx, save_idx) — both must exist.
    """
    seq = [(i.mnemonic, i.op_str) for i in fn.insns]
    store_idx = next(
        (k for k, (m, ops) in enumerate(seq)
         if m == "mov" and ops.startswith(f"dword ptr [{global_offset_str}]")
         and "eax" in ops.split(",", 1)[1]),
        None,
    )
    save_idx = next(
        (k for k, (m, ops) in enumerate(seq)
         if m == "mov" and ops == "ebx, eax"),
        None,
    )
    assert store_idx is not None, f"no `mov [{global_offset_str}], eax`:\n{fn.disasm_text()}"
    assert save_idx is not None, f"no `mov ebx, eax`:\n{fn.disasm_text()}"
    return store_idx, save_idx


# `peace_rating` is the second extern in the snippet -> at offset 0xc in DGROUP
# (after `t` at 8 ... actually the layout depends on declaration order in defs.c).
# Just look for any `mov dword ptr [...], eax` immediately around the divide.
def _store_save_pair_around_idiv(fn):
    """Return (store_idx, save_idx) for the global-store and EBX-save
    that bracket the idiv result."""
    # idiv is the divide; the result store and EBX save happen right after.
    seq = [(i.mnemonic, i.op_str) for i in fn.insns]
    idiv_idx = next(k for k, (m, ops) in enumerate(seq) if m == "idiv")
    store_idx = None
    save_idx = None
    for k in range(idiv_idx + 1, min(idiv_idx + 5, len(seq))):
        m, ops = seq[k]
        if (m == "mov" and ops.startswith("dword ptr [")
                and ops.endswith(", eax")):
            store_idx = k
        elif m == "mov" and ops == "ebx, eax":
            save_idx = k
    assert store_idx is not None and save_idx is not None, fn.disasm_text()
    return store_idx, save_idx


def test_global_first_emits_store_then_save(watcom_10_0a):
    """`global = expr; local = global;` emits store before EBX-save."""
    fn = _compile(_GLOBAL_FIRST, watcom_10_0a)
    store, save = _store_save_pair_around_idiv(fn)
    assert store < save, (
        f"expected `mov [g], eax` (idx {store}) BEFORE `mov ebx, eax` "
        f"(idx {save}); got:\n{fn.disasm_text()}"
    )


def test_local_first_emits_save_then_store(watcom_10_0a):
    """`local = expr; global = local;` emits EBX-save before store."""
    fn = _compile(_LOCAL_FIRST, watcom_10_0a)
    store, save = _store_save_pair_around_idiv(fn)
    assert save < store, (
        f"expected `mov ebx, eax` (idx {save}) BEFORE `mov [g], eax` "
        f"(idx {store}); got:\n{fn.disasm_text()}"
    )


def test_both_orderings_emit_same_instructions(watcom_10_0a):
    """Both forms emit the same set of instructions, just permuted."""
    a = _compile(_GLOBAL_FIRST, watcom_10_0a)
    b = _compile(_LOCAL_FIRST,  watcom_10_0a)
    a_set = sorted((i.mnemonic, i.op_str) for i in a.insns)
    b_set = sorted((i.mnemonic, i.op_str) for i in b.insns)
    # The two forms differ in the dividend register (Rule 2 EAX-vs-EDX
    # cost-model swap), so insn sets aren't quite equal.  Check the
    # *count* of stores and the EBX-save though.
    a_stores = sum(1 for m, ops in a_set
                    if m == "mov" and "dword ptr [" in ops
                    and ops.endswith(", eax"))
    b_stores = sum(1 for m, ops in b_set
                    if m == "mov" and "dword ptr [" in ops
                    and ops.endswith(", eax"))
    assert a_stores == b_stores, (
        f"global-store count differs: A={a_stores} B={b_stores}\n"
        f"--- A ---\n{a.disasm_text()}\n--- B ---\n{b.disasm_text()}"
    )
    a_saves = sum(1 for m, ops in a_set if m == "mov" and ops == "ebx, eax")
    b_saves = sum(1 for m, ops in b_set if m == "mov" and ops == "ebx, eax")
    assert a_saves == b_saves == 1, (
        f"expected exactly one `mov ebx, eax` per form; "
        f"got A={a_saves}, B={b_saves}"
    )


def test_orderings_have_close_size(watcom_10_0a):
    """The two forms differ only by Rule 2's 1-byte EAX-vs-EDX divide-setup cost."""
    a = _compile(_GLOBAL_FIRST, watcom_10_0a)
    b = _compile(_LOCAL_FIRST,  watcom_10_0a)
    delta = abs(a.size() - b.size())
    assert delta <= 1, (
        f"expected at most 1-byte delta (Rule 2 swap); got {delta}\n"
        f"--- GLOBAL_FIRST ({a.size()}b) ---\n{a.disasm_text()}\n"
        f"--- LOCAL_FIRST ({b.size()}b) ---\n{b.disasm_text()}"
    )
