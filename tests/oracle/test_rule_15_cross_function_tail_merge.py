"""Rule 15 - Cross-function tail-merge within a TU.

## Trigger

Watcom 10.0a's `ComTail` optimisation merges identical instruction
suffixes across functions **within the same translation unit**.
The first function in source order with a particular tail becomes
the canonical body; subsequent functions with the same tail emit
a `jmp` (short or near) into the canonical function's tail label.

The merge requires:

  * `OptForSize >= 25` (default 50, satisfied by ``-bt=dos -mf -4r -s``)
  * Tail savings > `OptInsSize(OC_JMP, OC_DEST_NEAR)` = 5 bytes
  * Both functions in the same TU (same `.obj` file)

## Mechanism

`ComTail` lives in `bld/cg/c/optcom.c:212+`.  It's invoked from
`bld/cg/c/optins.c:304` whenever an `OC_RET` is added to the
per-CG-pass `RetList`:

```c
case OC_RET:
    ...
    ComTail(RetList, ins);
```

`RetList` is a global in `bld/cg/c/optdata.c:41`, initialised by
`InitQueue()` in `bld/cg/c/optmain.c:210` (called once per TU from
`InitCG()` in `bld/cg/c/generate.c:105`).  This is why merging
spans function boundaries within a TU but **not** across TUs.

`FindCommon` accumulates `c->save += _ObjLen(p1)` for each common
instruction (working backwards from the ret).  `ComTail` then
gates: `if (max.save <= OptInsSize(OC_JMP, OC_DEST_NEAR))
optreturn(false);` (must save more than a near-jmp's worth).

## Verified on

  * `act_house1`/`2`/`3` cluster (action.c) - first function has
     full body, others end in `jmp` into the canonical tail.
  * `tests/oracle/test_rule_15_cross_function_tail_merge.py` -
     6 tests: same-TU merge into the first function; cross-TU
     prevents merge; merged bodies are smaller; merged functions
     end in `jmp` not `ret`; source-order determines canonical;
     reversing source order swaps the canonical function.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = (
    "int placing_type, placing_flags, placing_cost, pm_build_shape;\n"
    "int city_costs[20];\n"
)


def _act_house(n, idx):
    """A small wrapper writing 4 globals; ``n`` distinguishes function name,
    ``idx`` distinguishes the city_costs[] index used."""
    return f"""\
void act_house{n}(void) {{
    placing_type = {n + 9};
    placing_flags = 1;
    placing_cost = city_costs[{idx}];
    pm_build_shape = 0;
}}
"""


_HEADER = (
    "extern int placing_type, placing_flags, placing_cost, pm_build_shape;\n"
    "extern int city_costs[20];\n"
)


def _ends_with_jmp(fn):
    return fn.insns and fn.insns[-1].mnemonic == "jmp"


def _ends_with_ret(fn):
    return fn.insns and fn.insns[-1].mnemonic == "ret"


def test_same_tu_merges_three_into_one_canonical(watcom_10_0a):
    """In one TU, the first function in source order becomes canonical."""
    src = _HEADER + _act_house(1, 8) + _act_house(2, 9) + _act_house(3, 10)
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS)
    assert b.ok, b.output

    h1 = b.function("act_house1")
    h2 = b.function("act_house2")
    h3 = b.function("act_house3")

    # First in source order has the full body, ends in `ret`
    assert _ends_with_ret(h1), h1.disasm_text()
    # Subsequent functions are merged, end in `jmp` into h1's tail
    assert _ends_with_jmp(h2), h2.disasm_text()
    assert _ends_with_jmp(h3), h3.disasm_text()

    # Canonical body is strictly larger than the merged ones
    assert h1.size() > h2.size() and h1.size() > h3.size()
    # Merged sizes are equal (each lops off the same shared tail)
    assert h2.size() == h3.size()


def test_cross_tu_does_not_merge(watcom_10_0a):
    """Three TUs each containing one function: no tail-merge possible."""
    sources = {
        f"H{n}.C": _HEADER + _act_house(n, idx)
        for n, idx in [(1, 8), (2, 9), (3, 10)]
    }
    b = compile_snippet(sources, image=watcom_10_0a, extern_defs=_DEFS)
    assert b.ok, b.output

    h1 = b.function("act_house1")
    h2 = b.function("act_house2")
    h3 = b.function("act_house3")

    # All three have full bodies (end in ret)
    for h in (h1, h2, h3):
        assert _ends_with_ret(h), h.disasm_text()

    # All three the same size (full body each)
    assert h1.size() == h2.size() == h3.size()


def test_same_tu_smaller_total_than_cross_tu(watcom_10_0a):
    """Same-TU build is strictly smaller than cross-TU due to merging."""
    in_tu = _HEADER + _act_house(1, 8) + _act_house(2, 9) + _act_house(3, 10)
    b_in = compile_snippet(in_tu, image=watcom_10_0a, extern_defs=_DEFS)

    sources = {
        f"H{n}.C": _HEADER + _act_house(n, idx)
        for n, idx in [(1, 8), (2, 9), (3, 10)]
    }
    b_x = compile_snippet(sources, image=watcom_10_0a, extern_defs=_DEFS)

    in_total = sum(b_in.function(f"act_house{n}").size() for n in (1, 2, 3))
    x_total  = sum(b_x.function(f"act_house{n}").size() for n in (1, 2, 3))
    assert in_total < x_total, (
        f"expected same-TU total < cross-TU total; "
        f"got same={in_total}, cross={x_total}"
    )


def test_source_order_determines_canonical(watcom_10_0a):
    """Reversing source order makes the LAST-in-original-order function canonical."""
    forward = _HEADER + _act_house(1, 8) + _act_house(2, 9) + _act_house(3, 10)
    reverse = _HEADER + _act_house(3, 10) + _act_house(2, 9) + _act_house(1, 8)

    b_fwd = compile_snippet(forward, image=watcom_10_0a, extern_defs=_DEFS)
    b_rev = compile_snippet(reverse, image=watcom_10_0a, extern_defs=_DEFS)

    # Forward: act_house1 is canonical
    assert _ends_with_ret(b_fwd.function("act_house1"))
    assert _ends_with_jmp(b_fwd.function("act_house2"))
    assert _ends_with_jmp(b_fwd.function("act_house3"))

    # Reverse: act_house3 is canonical (it's first in source order now)
    assert _ends_with_ret(b_rev.function("act_house3"))
    assert _ends_with_jmp(b_rev.function("act_house2"))
    assert _ends_with_jmp(b_rev.function("act_house1"))


def _jmp_target_abs(fn, insn):
    """Compute the absolute target address of a near/short jmp."""
    assert insn.mnemonic == "jmp"
    after = fn.base + insn.rel_off + insn.size
    if insn.size == 5 and insn.raw[0] == 0xE9:
        disp = int.from_bytes(insn.raw[1:5], "little", signed=True)
    elif insn.size == 2 and insn.raw[0] == 0xEB:
        disp = int.from_bytes(insn.raw[1:2], "little", signed=True)
    else:
        raise AssertionError(f"unexpected jmp encoding: {insn.raw.hex()}")
    return (after + disp) & 0xFFFFFFFF


def test_merged_jmp_targets_canonical_tail(watcom_10_0a):
    """The `jmp` at the end of a merged function targets a label inside
    the canonical function's body (after its start, before its end)."""
    src = _HEADER + _act_house(1, 8) + _act_house(2, 9) + _act_house(3, 10)
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS)

    h1 = b.function("act_house1")
    h2 = b.function("act_house2")

    last = h2.insns[-1]
    target = _jmp_target_abs(h2, last)
    assert h1.base <= target < h1.base + h1.size(), (
        f"jmp target {target:x} not inside h1 "
        f"[{h1.base:x}..{h1.base+h1.size():x})\n"
        f"h2:\n{h2.disasm_text()}\nh1:\n{h1.disasm_text()}"
    )
    # And the target is past h1's start (it's a TAIL merge, not a function call)
    assert target > h1.base, f"jmp targets h1's start, not its tail"


def test_short_tail_below_threshold_does_not_merge(watcom_10_0a):
    """Two functions sharing only a tiny tail (<= near-jmp size = 5 bytes)
    are NOT tail-merged - the savings gating filters them out."""
    # Each function: just `mov [g], imm; ret` - 7 bytes for mov + 1 for ret = 8 bytes
    # Shared tail is just the `ret` (1 byte). Savings = 1, jmp_near = 5, no merge.
    src = """\
extern int g1, g2;
void f1(void) { g1 = 1; }
void f2(void) { g2 = 2; }
"""
    defs = "int g1, g2;\n"
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=defs)
    assert b.ok, b.output

    f1 = b.function("f1")
    f2 = b.function("f2")
    # Both have full bodies ending in ret (no merge)
    assert _ends_with_ret(f1), f1.disasm_text()
    assert _ends_with_ret(f2), f2.disasm_text()
