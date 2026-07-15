"""Tests for ``c2 const-audit`` -- the constant / off-by-one boundary audit.

The subtle, load-bearing piece is the comparison canonicalisation: a
``cmp K; jcc`` must be reduced to the boundary value at which the branch
flips, so that semantically-identical ``>`` vs ``>=`` source spellings
(which Watcom emits as ``cmp n`` vs ``cmp n±1`` with a flipped Jcc) do NOT
register as a wrong constant.  Only a genuine boundary difference should.
"""
import collections

from c2.commands.const_audit import _extract, constant_audit


def _asm(*parts: bytes) -> bytes:
    return b"".join(parts)


# x86-32 encodings used below:
#   cmp eax, imm32  = 3D imm32
#   cmp edx, imm32  = 81 FA imm32
#   jl  rel8 = 7C rr   jle rel8 = 7E rr   jge rel8 = 7D rr   jg rel8 = 7F rr
#   je  rel8 = 74 rr   jne rel8 = 75 rr
#   mov eax, imm32 = B8 imm32   push imm32 = 68 imm32
#   and eax, imm32 = 25 imm32   shl eax, imm8 = C1 E0 ii
#   imul eax, eax, imm8 = 6B C0 ii
def _cmp_eax(k: int) -> bytes:
    return b"\x3d" + k.to_bytes(4, "little")


def _extract_plain(code: bytes):
    return _extract(code, 0, set())


def test_cmp_jl_boundary_is_k():
    _, b, _ = _extract_plain(_asm(_cmp_eax(0x50), b"\x7c\x00"))  # cmp 0x50; jl
    assert b == collections.Counter({0x50: 1})


def test_cmp_jle_boundary_is_k_plus_1():
    _, b, _ = _extract_plain(_asm(_cmp_eax(0x4f), b"\x7e\x00"))  # cmp 0x4f; jle
    assert b == collections.Counter({0x50: 1})


def test_cmp_jge_boundary_is_k_and_jg_is_k_plus_1():
    _, bge, _ = _extract_plain(_asm(_cmp_eax(0x10), b"\x7d\x00"))  # jge
    _, bg, _ = _extract_plain(_asm(_cmp_eax(0x0f), b"\x7f\x00"))   # jg
    assert bge == collections.Counter({0x10: 1})
    assert bg == collections.Counter({0x10: 1})


def test_equivalent_lt_and_le_do_not_diverge():
    """`x < 0x50` (cmp 0x50; jl) and `x <= 0x4f` (cmp 0x4f; jle) are the
    SAME boundary -- the audit must report CLEAN (no false positive)."""
    ps = _asm(_cmp_eax(0x50), b"\x7c\x00")
    rc = _asm(_cmp_eax(0x4f), b"\x7e\x00")
    res = constant_audit(ps, rc, 0, 0, set(), set())
    assert res["clean"], res


def test_genuine_off_by_one_is_flagged():
    """`x < 0x50` vs `x <= 0x50` differ by one boundary -> flagged."""
    ps = _asm(_cmp_eax(0x50), b"\x7c\x00")   # boundary 0x50
    rc = _asm(_cmp_eax(0x50), b"\x7e\x00")   # boundary 0x51
    res = constant_audit(ps, rc, 0, 0, set(), set())
    assert not res["clean"]
    assert res["cmp_threshold"]["ps_only"] == {0x50: 1}
    assert res["cmp_threshold"]["rc_only"] == {0x51: 1}


def test_eq_channel_separate_from_boundary():
    _, b, e = _extract_plain(_asm(_cmp_eax(0x91), b"\x75\x00"))  # cmp 0x91; jne
    assert b == collections.Counter()
    assert e == collections.Counter({0x91: 1})


def test_zext_mask_is_filtered():
    # and eax, 0xff  -> noise, must not appear as a plain constant
    p, _, _ = _extract_plain(b"\x25\xff\x00\x00\x00")
    assert p == collections.Counter()


def test_shift_count_is_filtered():
    # shl eax, 2  -> strength-reduction codegen, filtered
    p, _, _ = _extract_plain(b"\xc1\xe0\x02")
    assert p == collections.Counter()


def test_plain_constants_kept():
    # mov eax, 0x140 ; push 0x52 ; imul eax, eax, 0x3a
    code = b"\xb8\x40\x01\x00\x00" + b"\x68\x52\x00\x00\x00" + b"\x6b\xc0\x3a"
    p, _, _ = _extract_plain(code)
    assert p == collections.Counter({0x140: 1, 0x52: 1, 0x3a: 1})


def test_frame_adjust_esp_is_filtered():
    # sub esp, 0x14 ; add esp, 0x14 ; sub esp, 0x118 -> stack-frame size,
    # never a source constant -> must not enter the plain channel.
    code = b"\x83\xec\x14" + b"\x83\xc4\x14" + b"\x81\xec\x18\x01\x00\x00"
    p, _, _ = _extract_plain(code)
    assert p == collections.Counter()


def test_non_esp_add_sub_still_kept():
    # add eax, 0x10 is a real arithmetic constant -- only the ESP dest is
    # the frame-size artifact; non-esp add/sub must still be counted.
    p, _, _ = _extract_plain(b"\x83\xc0\x10")
    assert p == collections.Counter({0x10: 1})


def test_frame_size_delta_is_not_a_wrong_constant():
    """PS and RC with different frame sizes (the allocator spilled a
    different number of locals) must report CLEAN -- the frame size is a
    regalloc artifact, not a divergent constant."""
    ps = b"\x83\xec\x14" + b"\x83\xc4\x14"   # sub/add esp, 0x14
    rc = b"\x83\xec\x18" + b"\x83\xc4\x18"   # sub/add esp, 0x18
    res = constant_audit(ps, rc, 0, 0, set(), set())
    assert res["clean"], res


def test_plain_zero_is_filtered():
    # mov eax, 0 ; mov dword ptr [ebx], 0 -> zero-store / zero-materialization
    # artifact (PS often zeroes via xor / a reused register, no immediate).
    code = b"\xb8\x00\x00\x00\x00" + b"\xc7\x03\x00\x00\x00\x00"
    p, _, _ = _extract_plain(code)
    assert p == collections.Counter()


def test_wrong_zero_still_caught_via_nonzero_side():
    """A genuine wrong-zero (PS `= 5` vs RC `= 0`) is still flagged: the
    zero is dropped but the non-zero literal on the other side surfaces it."""
    ps = b"\xb8\x05\x00\x00\x00"   # mov eax, 5
    rc = b"\xb8\x00\x00\x00\x00"   # mov eax, 0
    res = constant_audit(ps, rc, 0, 0, set(), set())
    assert not res["clean"]
    assert res["plain"]["ps_only"] == {0x5: 1}
    assert res["plain"]["rc_only"] == {}


def test_relocated_immediate_is_masked():
    # mov eax, 0x90abc  with the imm marked as a fixup (relocated address)
    code = b"\xb8\xbc\x0a\x09\x00"   # mov eax, 0x90abc ; imm at byte 1..4
    fix = {1}                         # imm_offset == 1 -> masked
    p, _, _ = _extract(code, 0, fix)
    assert p == collections.Counter()


def test_branch_targets_skipped():
    # jmp rel32 / call rel32 hold link-relative displacements, never consts
    p, b, e = _extract_plain(b"\xe9\x10\x00\x00\x00" + b"\xe8\x20\x00\x00\x00")
    assert p == b == e == collections.Counter()


def test_plain_count_difference_is_noise_suppressed():
    """A value present on BOTH sides with a different COUNT (codegen
    multiplicity, e.g. strength reduction emitting the literal twice) is
    NOT a wrong constant -- the value-set plain channel suppresses it."""
    # PS: mov eax,0x10 ; mov edx,0x10    RC: mov eax,0x10   (PS has 2, RC 1)
    ps = b"\xb8\x10\x00\x00\x00" + b"\xba\x10\x00\x00\x00"
    rc = b"\xb8\x10\x00\x00\x00"
    res = constant_audit(ps, rc, 0, 0, set(), set())
    assert res["clean"], res


def test_plain_value_unique_to_one_side_is_flagged():
    """A literal that exists on one side and is ABSENT on the other is a
    genuine wrong constant -- still caught (no accuracy loss)."""
    ps = b"\x6b\xc0\x3a"          # imul eax, eax, 0x3a   (struct stride)
    rc = b"\x6b\xc0\x4e"          # imul eax, eax, 0x4e   (wrong stride)
    res = constant_audit(ps, rc, 0, 0, set(), set())
    assert not res["clean"]
    assert res["plain"]["ps_only"] == {0x3a: 1}
    assert res["plain"]["rc_only"] == {0x4e: 1}


def test_cmp_boundary_keeps_count_for_offby_one_pairing():
    """The off-by-one needs the count-aware multiset: two checks at one
    boundary where one shifts must still surface PS 0x51 / RC 0x50."""
    # PS: cmp 0x50; jl   (bnd 0x50)  +  cmp 0x50; jle  (bnd 0x51)
    ps = b"\x3d\x50\x00\x00\x00\x7c\x00" + b"\x3d\x50\x00\x00\x00\x7e\x00"
    # RC: cmp 0x50; jl   +  cmp 0x50; jl   (both 0x50 -- the jle shifted)
    rc = b"\x3d\x50\x00\x00\x00\x7c\x00" + b"\x3d\x50\x00\x00\x00\x7c\x00"
    res = constant_audit(ps, rc, 0, 0, set(), set())
    assert not res["clean"]
    assert res["cmp_threshold"]["ps_only"] == {0x51: 1}
    assert res["cmp_threshold"]["rc_only"] == {0x50: 1}


def test_cmp_zero_equals_test_idiom_dropped_from_eq():
    """`cmp reg, 0; je` == `test reg, reg; je`; the `cmp 0` form must not
    register as an equality constant (it is codegen idiom, not a const)."""
    _, _, e = _extract(b"\x3d\x00\x00\x00\x00\x74\x00", 0, set())  # cmp 0; je
    assert e == collections.Counter()


# ── out-of-order parameter (swapped constant arg) detector ──────────────────
from c2.commands.const_audit import argswap_audit, _call_arg_consts


def _mov(reg_op: int, k: int) -> bytes:
    return bytes([reg_op]) + (k & 0xFFFFFFFF).to_bytes(4, "little")


_MOV_EAX, _MOV_ECX, _MOV_EDX, _MOV_EBX = 0xB8, 0xB9, 0xBA, 0xBB
# call rel32 with disp 0x100 -> from a call at offset 10, target = 10+5+0x100
_CALL = b"\xe8" + (0x100).to_bytes(4, "little")
_O2N = {0x10F: "F"}


def test_argswap_detects_swapped_constants():
    """PS F(0x10, 0x20) vs RC F(0x20, 0x10) -- both constants land in the
    opposite arg register; both flagged."""
    ps = _mov(_MOV_EAX, 0x10) + _mov(_MOV_EDX, 0x20) + _CALL
    rc = _mov(_MOV_EAX, 0x20) + _mov(_MOV_EDX, 0x10) + _CALL
    sw = argswap_audit(ps, rc, 0, 0, set(), set(), _O2N, _O2N)
    pairs = {(s["const"], s["ps_slot"], s["rc_slot"]) for s in sw}
    assert (0x10, 0, 1) in pairs   # 0x10: PS arg0 -> RC arg1
    assert (0x20, 1, 0) in pairs   # 0x20: PS arg1 -> RC arg0


def test_argswap_catches_const_swapped_with_variable():
    """Only ONE arg is a constant; the other is a variable.  The const's
    slot still moves -> caught.  Each arg is staged in its own register
    (as real codegen does)."""
    mem_eax = b"\x8b\x05\x00\x00\x00\x00"          # mov eax, [0]  (variable)
    mem_edx = b"\x8b\x15\x00\x00\x00\x00"          # mov edx, [0]  (variable)
    # PS: F(var, 0x20) -> eax=var, edx=0x20    RC: F(0x20, var) -> eax=0x20, edx=var
    ps = mem_eax + _mov(_MOV_EDX, 0x20) + _CALL     # call at offset 11
    rc = _mov(_MOV_EAX, 0x20) + mem_edx + _CALL     # call at offset 11
    o2n = {0x110: "F"}                              # 11 + 5 + 0x100
    sw = argswap_audit(ps, rc, 0, 0, set(), set(), o2n, o2n)
    assert any(s["const"] == 0x20 and s["ps_slot"] == 1 and s["rc_slot"] == 0
               for s in sw)


def test_argswap_no_false_positive_on_matching_args():
    ps = _mov(_MOV_EAX, 0x10) + _mov(_MOV_EDX, 0x20) + _CALL
    assert argswap_audit(ps, ps, 0, 0, set(), set(), _O2N, _O2N) == []


def test_argswap_skips_ambiguous_duplicate_value():
    """A value in multiple arg slots (e.g. a dimension passed to two params)
    is ambiguous and must NOT produce a false swap."""
    # PS: eax=0xa0, edx=0xa0   RC: eax=0xa0, ecx=0xa0  (0xa0 in 2 slots both)
    ps = _mov(_MOV_EAX, 0xA0) + _mov(_MOV_EDX, 0xA0) + _CALL
    rc = _mov(_MOV_EAX, 0xA0) + _mov(_MOV_ECX, 0xA0) + _CALL
    assert argswap_audit(ps, rc, 0, 0, set(), set(), _O2N, _O2N) == []


def test_argswap_masks_relocated_address_arg():
    """An arg whose immediate is a relocated address (fixup) is not a
    comparable constant -- it must be skipped."""
    ps = _mov(_MOV_EAX, 0x90100) + _mov(_MOV_EDX, 0x20) + _CALL
    # fixup marks the eax imm bytes (offset 1..4) -> eax not tracked as const
    sw = argswap_audit(ps, ps, 0, 0, {1, 2, 3, 4}, {1, 2, 3, 4}, _O2N, _O2N)
    assert sw == []


def test_argswap_skips_when_call_sequence_diverges():
    """If PS and RC call DIFFERENT callee sequences (a shape divergence added
    or moved a call), per-position pairing is unreliable -> report nothing,
    so a mis-paired comparison can't invent a false swap."""
    # PS: F(0x10) ; G()      RC: F(0x10) ; H() ; G()   (H inserted)
    F = _CALL                                  # call at offset 5 -> target 0x10a
    ps = _mov(_MOV_EAX, 0x10) + F + b"\xe8" + (0x200).to_bytes(4, "little")
    rc = (_mov(_MOV_EAX, 0x10) + F
          + b"\xe8" + (0x300).to_bytes(4, "little")
          + b"\xe8" + (0x200).to_bytes(4, "little"))
    o2n = {0x10A: "F", 0xF + 0x200: "G", 0x14 + 0x300: "H",
           0x19 + 0x200: "G"}
    # sequences differ (PS=[F,G], RC=[F,H,G]) -> guard returns []
    assert argswap_audit(ps, rc, 0, 0, set(), set(), o2n, o2n) == []


def test_argswap_invalidates_const_staged_into_lower_slot():
    """A constant in ebx that is READ to stage a lower arg (mov edx, ebx) is
    a source register, not a dedicated arg2 -- the regalloc-leftover FP where
    a variable holding a constant lives in an arg reg across a call.  No const
    arg should be attributed to that call."""
    code = _mov(_MOV_EBX, 0x50) + b"\x89\xda" + _CALL   # mov ebx,0x50; mov edx,ebx
    o2n = {0xC + 0x100: "F"}                             # call at 7 -> 7+5+0x100
    assert _call_arg_consts(code, 0, set(), o2n) == [("F", {})]


def test_const_audit_does_not_overrun_smaller_rc_function():
    """Regression: when RC's function body is SMALLER than PS's, the audit
    must NOT read constants from the next RC function.  Previously this
    surfaced phantom equality literals (e.g. `cmp edi, 0x1e/0x1f ; jne`
    from a neighbour function) as RC-only divergences in functions like
    `build_city_item`.  The caller is responsible for sizing the RC slice;
    here we model the bug by passing a deliberately-oversized RC slice and
    confirming that, when the slice is bounded correctly, the audit is
    clean."""
    # PS: simple `mov eax, 5` body, no compares.
    ps = _mov(_MOV_EAX, 5)
    # RC: same body, followed by NEIGHBOUR function bytes containing
    # `cmp edi, 0x1e ; jne 0` and `cmp edi, 0x1f ; jne 0`.  When the RC
    # slice overruns into this neighbour code, those equality constants
    # leak as RC-only divergences -- the false positive class observed in
    # the corpus.
    neighbour = (b"\x81\xff\x1e\x00\x00\x00" + b"\x75\x00"
                 + b"\x81\xff\x1f\x00\x00\x00" + b"\x75\x00")
    rc_overrun = _mov(_MOV_EAX, 5) + neighbour
    bad = constant_audit(ps, rc_overrun, 0, 0, set(), set())
    assert not bad["clean"], (
        "smoke-test: an oversized RC slice MUST surface phantom equality "
        "literals -- if this assertion ever fails, the audit's own "
        "slicing logic changed and the regression below no longer proves "
        "the caller-side fix")
    assert bad.get("eq", {}).get("rc_only") == {0x1e: 1, 0x1f: 1}
    # When the caller slices RC to its OWN function length (here = len(ps)),
    # the audit must report CLEAN -- no phantom constants leak through.
    rc_bounded = rc_overrun[:len(ps)]
    good = constant_audit(ps, rc_bounded, 0, 0, set(), set())
    assert good["clean"], good
