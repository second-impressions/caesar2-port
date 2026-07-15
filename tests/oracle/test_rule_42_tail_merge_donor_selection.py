"""Rule 42 - Cross-function tail-merge **donor selection** (`ComTail`).

Rule 15 already proves *that* Watcom does cross-function tail-merge
within a TU.  Rule 42 zooms in on the *algorithm* — which function
becomes the donor, which becomes the merged dependent, and what
breaks the chain.

The mechanics, as documented in OW v1 ``bld/cg/c/optcom.c``:

  * Every emitted ``OC_RET`` is added LIFO to a TU-wide ``RetList``
    (``optutil.c::AddRef``: ``_LblRef(instr) = RetList; RetList = instr``).
  * ``OptPush`` walks the instruction stream **backward from
    ``LastIns``**.  Each ``OC_RET`` triggers ``ComTail(RetList, ins)``.
  * ``ComTail`` finds the candidate from ``RetList`` with the longest
    matching backward sequence.  ``FindCommon`` walks ``PrevIns(p1)``
    and ``PrevIns(p2)`` simultaneously, accumulating
    ``c->save += _ObjLen(p1)`` per matching instruction
    (``CommonInstr`` returns true).
  * ``CommonInstr`` for ``OC_RET`` requires equal ``_RetPop``.
  * Gating: ``OptForSize >= 25`` AND ``max.save > 5``
    (= ``OptInsSize(OC_JMP, OC_DEST_NEAR)``).
  * On a hit, the *current* RET is *deleted* and replaced with a
    near-jmp; the candidate keeps its tail intact.  ``DelInstr``
    removes the deleted RET from ``RetList``.

Combined with the LIFO + backward walk, this means the **earliest in
source order with a matching tail always keeps its inline tail** —
that's the canonical donor.  Stub bodies (which compile to a single
mov + ret) break the chain because the matching backward walk
terminates at the mov, leaving ``save <= 1`` byte (well below the
5-byte threshold).

This is the formal explanation behind Phase 2 (the donor-first
tail-merge cascade) of ``docs/decomp-strategy.md``: decompositions of named PS
donors are expected to retroactively unblock byte-exact wins for
their named-PS-donor dependents — but only if the donor body has
the matching prologue/epilogue.

## Verified on

  * ``clear_all_rm`` (1-byte diff at +0x94, expected jmp to
    ``build_wall_from_elastic+0x261``).  Replacing the donor stub
    with a synthetic body that produces the matching 6-pop+ret
    epilogue flipped clear_all_rm to byte-exact (commit 3ebd233).
  * Watcom 10.0a, ``-bt=dos -mf -4r -s``.
"""
from __future__ import annotations

from c2.commands.oracle import compile_snippet


# ───────────────────── building blocks ─────────────────────────────


_DEFS_8 = (
    "int g1, g2, g3, g4, g5, g6, g7, g8;\n"
)
_HDR_8 = (
    "extern int g1, g2, g3, g4, g5, g6, g7, g8;\n"
)


def _heavy_body(seed: int) -> str:
    """Body with a *seed-specific prefix* and a *shared 4-store
    suffix*.  The shared suffix gives ``FindCommon`` a long enough
    backward match (~40 bytes) to clear the 5-byte ``ComTail`` gate.

    Each ``mov [gN], imm`` is 10 bytes (``c7 05 ?? ?? ?? ?? imm32``);
    four of them = 40 bytes plus the ret = 41 bytes ``save`` —
    well above the threshold."""
    return f"""\
    g1 = {seed};
    g2 = {seed + 1};
    g3 = {seed + 2};
    g4 = {seed + 3};
    g5 = 1000;
    g6 = 2000;
    g7 = 3000;
    g8 = 4000;
"""


def _heavy_fn(name: str, seed: int) -> str:
    return f"void {name}(void) {{\n{_heavy_body(seed)}}}\n"


def _stub_fn(name: str, addr: int = 0x10000) -> str:
    """Mimic our project's stub bodies — one global store, then ``ret``.
    The backward walk in ``FindCommon`` will see one OC_MOV (different
    operands per stub) before hitting the ret, so ``save`` caps at 1."""
    return (
        f"extern int __stub_log;\n"
        f"void {name}(void) {{ __stub_log = {addr}; }}\n"
    )


def _ends_with(fn, *expect):
    """``True`` if the function's last instruction's mnemonic+op matches
    one of ``expect`` (each is ``(mnem, op_substr)``)."""
    if not fn.insns:
        return False
    last = fn.insns[-1]
    return any(last.mnemonic == m and op in last.op_str for m, op in expect)


def _last_jmp_target(fn) -> int:
    """Absolute target address of the function's terminating jmp."""
    last = fn.insns[-1]
    assert last.mnemonic == "jmp", last.line
    after = fn.base + last.rel_off + last.size
    if last.size == 5 and last.raw[0] == 0xE9:
        disp = int.from_bytes(last.raw[1:5], "little", signed=True)
    elif last.size == 2 and last.raw[0] == 0xEB:
        disp = int.from_bytes(last.raw[1:2], "little", signed=True)
    else:
        raise AssertionError(f"unexpected jmp encoding: {last.raw.hex()}")
    return (after + disp) & 0xFFFFFFFF


# ───────────────────── tests ───────────────────────────────────────


def test_donor_is_earliest_in_source_order(watcom_10_0a):
    """When N functions share a tail, the FIRST in source keeps the
    inline tail; all others jmp into it.  This is the OptPush walk-
    backward + LIFO RetList consequence."""
    src = (
        _HDR_8
        + _heavy_fn("a_first", 100)
        + _heavy_fn("b_middle", 200)
        + _heavy_fn("c_last", 300)
    )
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS_8)
    assert b.ok, b.output

    fa = b.function("a_first")
    fb = b.function("b_middle")
    fc = b.function("c_last")

    # First-in-source: full tail, ends in ret
    assert _ends_with(fa, ("ret", "")), fa.disasm_text()
    # Others: terminating jmp
    assert _ends_with(fb, ("jmp", "")), fb.disasm_text()
    assert _ends_with(fc, ("jmp", "")), fc.disasm_text()


def test_jmp_targets_inside_canonical_function(watcom_10_0a):
    """The merged jmp targets a label inside the canonical donor's tail
    region — strictly between donor.base and donor.end."""
    src = (
        _HDR_8
        + _heavy_fn("donor_body", 100)
        + _heavy_fn("dep1", 200)
        + _heavy_fn("dep2", 300)
    )
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS_8)
    assert b.ok, b.output

    donor = b.function("donor_body")
    dep1 = b.function("dep1")
    dep2 = b.function("dep2")

    for dep in (dep1, dep2):
        tgt = _last_jmp_target(dep)
        assert donor.base < tgt < donor.base + donor.size(), (
            f"{dep.name} jmp target {tgt:#x} outside donor "
            f"[{donor.base:#x}..{donor.base + donor.size():#x})\n"
            f"donor:\n{donor.disasm_text()}\n{dep.name}:\n{dep.disasm_text()}"
        )


def test_stub_donor_breaks_the_chain(watcom_10_0a):
    """When the *first*-in-source function is a stub (mov + ret), the
    matching backward walk terminates at the mov and ``save = 1`` —
    below the 5-byte gate.  Subsequent functions cannot merge into
    the stub, so they emit their own inline tails.

    Equivalent to our project's situation when a named PS donor is
    still ``// STUB``: dependent functions can't tail-merge into it.
    """
    src = (
        _HDR_8
        + "extern int __stub_log;\n"
        + _stub_fn("a_stub_first")
        + _heavy_fn("b_real", 200)
        + _heavy_fn("c_real", 300)
    )
    b = compile_snippet(
        src, image=watcom_10_0a,
        extern_defs=_DEFS_8 + "int __stub_log;\n",
    )
    assert b.ok, b.output

    fa = b.function("a_stub_first")
    fb = b.function("b_real")
    fc = b.function("c_real")

    # Stub is unchanged — ends in ret, no donor-jmp.
    assert _ends_with(fa, ("ret", "")), fa.disasm_text()

    # b_real becomes the new canonical (it's earliest-in-source among
    # the *matching*-tail functions).
    assert _ends_with(fb, ("ret", "")), fb.disasm_text()
    # c_real merges into b_real, not into a_stub.
    assert _ends_with(fc, ("jmp", "")), fc.disasm_text()
    tgt = _last_jmp_target(fc)
    assert fb.base < tgt < fb.base + fb.size(), (
        f"c_real jmp target {tgt:#x} not inside b_real "
        f"[{fb.base:#x}..{fb.base + fb.size():#x})"
    )
    # Specifically: the target is NOT inside the stub.
    assert not (fa.base <= tgt < fa.base + fa.size()), (
        f"c_real should not jmp into stub a_stub_first"
    )


def test_decompiling_stub_donor_unlocks_dependents(watcom_10_0a):
    """The Rule 42 retroactive-unlock claim: replacing a stub donor
    with a real body that has the matching epilogue causes earlier-
    diff'd dependents to flip to the canonical jmp form."""
    # Variant A: donor is a stub. Dependents emit inline tails.
    stub_src = (
        _HDR_8
        + "extern int __stub_log;\n"
        + _stub_fn("donor")
        + _heavy_fn("dep1", 200)
        + _heavy_fn("dep2", 300)
    )
    # Variant B: donor has a matching-shape body. Dependents merge.
    real_src = (
        _HDR_8
        + _heavy_fn("donor", 100)
        + _heavy_fn("dep1", 200)
        + _heavy_fn("dep2", 300)
    )

    b_stub = compile_snippet(
        stub_src, image=watcom_10_0a,
        extern_defs=_DEFS_8 + "int __stub_log;\n",
    )
    b_real = compile_snippet(real_src, image=watcom_10_0a, extern_defs=_DEFS_8)
    assert b_stub.ok and b_real.ok

    # In stub variant: dep1 is canonical (first matching-tail function),
    # dep2 merges into it.
    s_dep1 = b_stub.function("dep1")
    s_dep2 = b_stub.function("dep2")
    assert _ends_with(s_dep1, ("ret", ""))
    assert _ends_with(s_dep2, ("jmp", ""))

    # In real variant: donor is canonical, dep1 AND dep2 merge.
    r_donor = b_real.function("donor")
    r_dep1 = b_real.function("dep1")
    r_dep2 = b_real.function("dep2")
    assert _ends_with(r_donor, ("ret", ""))
    assert _ends_with(r_dep1, ("jmp", ""))
    assert _ends_with(r_dep2, ("jmp", ""))

    # Total bytes should be smaller in the real variant (because
    # dep1 also merged, saving its tail).
    s_total = sum(b_stub.function(n).size() for n in ("dep1", "dep2"))
    r_total = sum(b_real.function(n).size() for n in ("dep1", "dep2"))
    assert r_total < s_total, (
        f"expected real-donor build to merge dep1 too; "
        f"stub-variant total={s_total}, real-variant total={r_total}"
    )


def test_different_retpop_prevents_merge(watcom_10_0a):
    """``CommonInstr`` for OC_RET requires ``_RetPop(old) == _RetPop(add)``.
    A function with stack args (ret N) won't merge with a void function
    (ret 0), even when their pre-pop instructions match exactly."""
    # f_void: void(void) - emits `ret 0`.
    # f_args: takes 5 stack-passed args - emits `ret 0xC` (3 stack args
    #         after first 4 register args, in __watcall: arg5/6/7 stack
    #         = 0xC bytes to clean up if ANY are stack-passed).
    # Both bodies write the same 8 globals.
    src = f"""\
{_HDR_8}
void f_void(void) {{
{_heavy_body(100)}}}

void f_args(int a, int b, int c, int d, int e, int f, int g) {{
{_heavy_body(200)}    (void)a; (void)b; (void)c; (void)d;
    (void)e; (void)f; (void)g;
}}

void f_void2(void) {{
{_heavy_body(300)}}}
"""
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS_8)
    assert b.ok, b.output

    fv1 = b.function("f_void")
    fa = b.function("f_args")
    fv2 = b.function("f_void2")

    # Both void functions can merge: f_void canonical, f_void2 jmps
    assert _ends_with(fv1, ("ret", "")), fv1.disasm_text()
    assert _ends_with(fv2, ("jmp", "")), fv2.disasm_text()
    # But f_args has different RetPop, so it cannot merge into f_void.
    # It keeps its own inline tail.
    assert _ends_with(fa, ("ret", "")), fa.disasm_text()
    # And the f_args tail uses a non-zero ret pop.
    assert "ret" in fa.insns[-1].mnemonic
    assert fa.insns[-1].op_str.strip() != "", (
        f"expected ret with explicit pop count, got: {fa.insns[-1].line}"
    )


def test_save_threshold_is_strictly_above_near_jmp_size(watcom_10_0a):
    """``ComTail`` gates with ``max.save > OptInsSize(OC_JMP, OC_DEST_NEAR)``
    which is 5 bytes for x86 near jmp.  Functions with exactly 5 bytes
    of common backward tail are at the boundary — depending on the
    exact reclen accounting they may not merge.

    Use a tiny body (single global store) to keep the prologue/
    epilogue short.  Verify that with NO common body — only the bare
    ``ret`` (1 byte) — no merge fires.  This confirms the gate is
    actually consulted (otherwise everything with two ret-only
    functions would merge to junk)."""
    src = """\
extern int g1, g2;
void tiny1(void) { g1 = 1; }
void tiny2(void) { g2 = 2; }
"""
    defs = "int g1, g2;\n"
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=defs)
    assert b.ok, b.output

    f1 = b.function("tiny1")
    f2 = b.function("tiny2")
    # Both end in ret — neither merges.  save=1 (just the ret) < 5.
    assert _ends_with(f1, ("ret", "")), f1.disasm_text()
    assert _ends_with(f2, ("ret", "")), f2.disasm_text()


def test_merged_tail_is_within_donors_epilogue(watcom_10_0a):
    """Concrete cross-check on the new-label insertion point.

    ``ComTail`` does ``AddNewLabel(PrevIns(max.start_com), align)`` —
    inserts a label *just before* the first matching instruction in
    the canonical body.  Therefore the merged-jmp target should land
    at the boundary between the donor's last non-shared instruction
    and the start of its shared tail.

    Empirically: for our 8-global heavy body, the donor ends with
    ``mov [g8], ...; pop ebx; ret`` (or similar callee-save dance).
    The shared tail is the pop sequence + ret.  Confirm dep's jmp
    targets that exact shared region (not the function start, not
    past the ret).
    """
    src = (
        _HDR_8
        + _heavy_fn("donor", 100)
        + _heavy_fn("dep", 200)
    )
    b = compile_snippet(src, image=watcom_10_0a, extern_defs=_DEFS_8)
    assert b.ok, b.output

    donor = b.function("donor")
    dep = b.function("dep")
    tgt = _last_jmp_target(dep)

    # Target falls strictly within donor (not its start).
    rel = tgt - donor.base
    assert 0 < rel < donor.size(), (
        f"jmp rel={rel} not inside donor (size={donor.size()})"
    )

    # Specifically: target lands at the start of an instruction
    # in the donor's disassembly.
    assert any(i.rel_off == rel for i in donor.insns), (
        f"jmp target rel={rel} doesn't align with any donor instruction\n"
        f"donor offsets: {[i.rel_off for i in donor.insns]}\n"
        f"donor:\n{donor.disasm_text()}"
    )

    # And the target instruction is in the donor's *tail* —
    # specifically, after at least the first instruction of the
    # body (i.e. not just past the prologue, but inside the
    # epilogue/shared-tail region).
    target_insn = next(i for i in donor.insns if i.rel_off == rel)
    # The shared tail necessarily contains the final ``ret`` of donor.
    # So target must be at or before donor's final ret in instruction
    # order, and after at least one body instruction.
    final_ret_off = donor.insns[-1].rel_off
    assert rel <= final_ret_off, (
        f"jmp target rel={rel} past donor's final ret @ {final_ret_off}"
    )
