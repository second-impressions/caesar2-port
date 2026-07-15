"""Rule 16 - Short-vs-near jmp encoding cascade.

## Trigger

The target of an unconditional jmp (including tail-merge jmps from
Rule 15) is encoded in one of two ways depending on byte distance:

  * **Short** (`eb disp8`, 2 bytes) when the signed 8-bit
    displacement fits, i.e. forward up to +127, backward down to
    -128 (-127 in practice on x86, see below).
  * **Near**  (`e9 disp32`, 5 bytes) otherwise.

A 1-byte byte-distance change near the threshold flips the
encoding, adding/removing 3 bytes from the function size.  Diffs
of exactly 3 bytes (or chains of 3-byte diffs) at tail-merge sites
are the cascade signature.

## Mechanism

`bld/cg/h/ocentry.h:68-69` defines the x86 short-jmp range:

```c
#define MAX_SHORT_FWD  127
#define MAX_SHORT_BWD  (128 - 2)   /* 126 */
```

`bld/cg/c/optrel.c:74-99` walks instructions forward from the jmp
to its target counting `_ObjLen(instr)`; if the cumulative size
stays under `MAX_SHORT_FWD`, the jmp is shrunk to short.  For
backward jmps the test is `(AskLocation() - lbl->lbl.address) <=
MAX_SHORT_BWD`.

The encoder in `bld/cg/intel/c/x86esc.c:288` checks
`objlen == OptInsSize(OC_JMP, OC_DEST_SHORT)` and emits the short
form via `_OutJShort + OutShortDisp(...)`; otherwise it emits the
near form via `_OutJNear + OutCodeDisp(...)`.

## Cascade implications

When PS.EXE has decompiled neighbours between a wrapper and its
merge target while the recomp still has stubs there, the recomp's
byte distance is shorter and Watcom picks `eb`; PS.EXE's distance
crosses 127 and uses `e9`.  Decompiling the intermediate stubs
re-aligns the distance, both builds emit `e9`, and the diff
collapses.

## Right C: decompile intermediate stubs

If the diff shows a 1-byte (or 3-byte) jmp-encoding mismatch at a
tail-merge site, look at the unfilled stubs between the wrapper
and its merge target.  Decompiling them pushes the byte distance
across the 127-byte threshold and aligns both encodings.

## Verified on

  * `act_tower` (commit `19a77c7`, resolved `b57121f`).
  * `tests/oracle/test_rule_16_jmp_short_vs_near.py` - 5 tests:
     short jmp = 2 bytes, near jmp = 5 bytes, threshold is ~127
     bytes (`MAX_SHORT_BWD` = 126), 3-byte function-size cascade
     at the threshold, encoding bytes (`eb` vs `e9`) match.
  * Watcom 10.0a, `-bt=dos -mf -4r -s`.
"""

from __future__ import annotations

import pytest

from c2.commands.oracle import compile_snippet


_DEFS = "int g[16]; int dst;\n"


def _build_with_filler(filler_count: int) -> str:
    """Two functions sharing a tail, with N filler functions in between.

    `first` and `last` both end with the sequence
    ``dst = g[1]; dst = g[2];`` so they tail-merge backward;
    `last`'s trailing `jmp` lands inside `first`'s body.
    """
    fillers = "\n".join(
        f"void filler_{i}(void) {{ dst = g[{i}] + {i}; }}"
        for i in range(filler_count)
    )
    return (
        "extern int g[16]; extern int dst;\n"
        "void first(void) { dst = g[0]; dst = g[1]; dst = g[2]; }\n"
        + fillers + "\n"
        "void last(void)  { dst = g[3]; dst = g[1]; dst = g[2]; }\n"
    )


def _trailing_jmp_size(b, name="last"):
    fn = b.function(name)
    last_insn = fn.insns[-1]
    assert last_insn.mnemonic == "jmp", fn.disasm_text()
    return last_insn.size, last_insn.raw[0]


def test_close_neighbour_uses_short_jmp(watcom_10_0a):
    """With no filler, last->first jmp is well within ±127 bytes."""
    src = _build_with_filler(0)
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS)
    size, op0 = _trailing_jmp_size(b)
    assert size == 2, f"expected short jmp (eb XX); got {size}b"
    assert op0 == 0xEB, f"expected `eb` opcode; got {op0:#x}"


def test_far_neighbour_uses_near_jmp(watcom_10_0a):
    """With many fillers, last->first crosses the 127-byte threshold."""
    src = _build_with_filler(20)
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS)
    size, op0 = _trailing_jmp_size(b)
    assert size == 5, f"expected near jmp (e9 XX XX XX XX); got {size}b"
    assert op0 == 0xE9, f"expected `e9` opcode; got {op0:#x}"


def test_threshold_at_127_bytes_backward(watcom_10_0a):
    """The cascade triggers exactly when backward displacement crosses
    `MAX_SHORT_BWD` (= 126 in `bld/cg/h/ocentry.h:69`).  In our snippet
    the transition is between 10 and 11 filler functions."""
    sizes = []
    for n in (10, 11):
        src = _build_with_filler(n)
        b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS)
        size, _ = _trailing_jmp_size(b)
        sizes.append(size)
    # 10 fillers: short; 11 fillers: near
    assert sizes == [2, 5], (
        f"expected [short, near] across the threshold; got {sizes}"
    )


def test_function_size_cascades_three_bytes(watcom_10_0a):
    """Crossing the threshold adds exactly 3 bytes to the merged function
    (near jmp is 5 bytes, short jmp is 2 bytes)."""
    src_under = _build_with_filler(10)
    src_over = _build_with_filler(11)
    b_u = compile_snippet(src_under, image=watcom_10_0a, extern_defs=_DEFS)
    b_o = compile_snippet(src_over, image=watcom_10_0a, extern_defs=_DEFS)
    sz_u = b_u.function("last").size()
    sz_o = b_o.function("last").size()
    assert sz_o - sz_u == 3, (
        f"expected +3 byte cascade at threshold; got {sz_o} - {sz_u} = {sz_o - sz_u}"
    )


def test_short_and_near_opcode_bytes(watcom_10_0a):
    """Encoded opcode byte distinguishes short (eb) from near (e9)."""
    short_b = compile_snippet(_build_with_filler(2),
                              image=watcom_10_0a, extern_defs=_DEFS)
    near_b = compile_snippet(_build_with_filler(20),
                             image=watcom_10_0a, extern_defs=_DEFS)
    short_op = short_b.function("last").insns[-1].raw[0]
    near_op = near_b.function("last").insns[-1].raw[0]
    assert short_op == 0xEB
    assert near_op == 0xE9
