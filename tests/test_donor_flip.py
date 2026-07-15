"""Unit tests for `_donor_flip_exit_only` (decomp_verify tail-merge filter)."""

from c2.commands.decomp_verify import _donor_flip_exit_only


def test_no_diffs_returns_none():
    body = b"\x53\x52\x51\x56\xc3"          # push ebx/edx/ecx/esi; ret
    assert _donor_flip_exit_only(body, body, []) is None


def test_size_differs_returns_none():
    a = b"\xc3"
    b = b"\xc3\x90"
    assert _donor_flip_exit_only(a, b, [1]) is None


def test_foreign_jmp_vs_inline_epilogue_is_donor_flip():
    # Both versions have the same body bytes for the first 5 instructions
    # (push ebx/edx/ecx/esi; mov edi,eax).  Then:
    #   PS ends with `jmp <far foreign>` (5 bytes).
    #   RC ends with the inline epilogue `pop esi; pop ecx; pop edx;
    #                                     pop ebx; ret` (5 bytes).
    # Both sides are exactly 10 bytes total.
    prefix = b"\x53\x52\x51\x56\x89\xc7"        # push ebx/edx/ecx/esi; mov edi,eax
    # Foreign jmp: target = end+(-0x1000) -> jumps backward outside the
    # function (this 11-byte function is way smaller than 0x1000).
    ps_tail = b"\xe9\x00\xf0\xff\xff"
    rc_tail = b"\x5e\x59\x5a\x5b\xc3"           # pop esi; pop ecx; pop edx; pop ebx; ret
    ps = prefix + ps_tail
    rc = prefix + rc_tail
    diffs = [i for i in range(len(ps)) if ps[i] != rc[i]]
    note = _donor_flip_exit_only(ps, rc, diffs)
    assert note is not None
    assert "donor flip" in note


def test_genuine_body_diff_returns_none():
    # Same prologue, but different intermediate operation -> NOT a donor
    # flip.  (e.g. PS does `xor eax, eax`, RC does `xor edx, edx`.)
    ps = b"\x53\x31\xc0\x5b\xc3"             # push ebx; xor eax,eax; pop ebx; ret
    rc = b"\x53\x31\xd2\x5b\xc3"             # push ebx; xor edx,edx; pop ebx; ret
    diffs = [i for i in range(len(ps)) if ps[i] != rc[i]]
    assert _donor_flip_exit_only(ps, rc, diffs) is None


def test_rule_16_jmp_encoding_only():
    # PS uses a 5-byte near jmp; RC uses a 2-byte short jmp.  Both jump
    # into the function.  Pure Rule 16 encoding cascade (no donor flip).
    # PS: jmp +5 (forward 5 bytes) + 5 nops + ret
    ps = b"\xe9\x05\x00\x00\x00" + b"\x90" * 5 + b"\xc3"   # 11 bytes
    rc = b"\xeb\x02" + b"\x90\x90" + b"\xc3"                 # 5 bytes
    # Different sizes -> reject (donor-flip filter requires matching size).
    assert _donor_flip_exit_only(ps, rc, [0, 1]) is None


def test_donor_to_donor_flip():
    # Same prologue, both end with a different foreign jmp.
    prefix = b"\x53\x52\x51"
    ps = prefix + b"\xe9\x00\xf0\xff\xff"
    rc = prefix + b"\xe9\x00\xe0\xff\xff"
    diffs = [i for i in range(len(ps)) if ps[i] != rc[i]]
    note = _donor_flip_exit_only(ps, rc, diffs)
    assert note is not None and "donor flip" in note


# ── inline epilogue with frame-cleanup prefix ────────────────────────────

def test_inline_epilogue_with_add_esp():
    """Inline epilogue starting with `add esp, N` before the pops counts
    as a valid epilogue.  PS often emits `add esp, 8 ; pop ... ; ret 4`
    where RC tail-merges to a donor that does the same dance."""
    from c2.commands.decomp_verify import _is_inline_epilogue, _epilogue_len
    # add esp, 8  -- 83 c4 08 (3 bytes)
    # pop edi     -- 5f
    # pop esi     -- 5e
    # ret 4       -- c2 04 00
    insns = [
        (0x00, 3, b"\x83\xc4\x08", "add esp, 8"),
        (0x03, 1, b"\x5f",        "pop edi"),
        (0x04, 1, b"\x5e",        "pop esi"),
        (0x05, 3, b"\xc2\x04\x00", "ret 4"),
    ]
    assert _is_inline_epilogue(insns, 0) == 4
    assert _epilogue_len(insns, 0, len(insns)) == 4


def test_inline_epilogue_with_leave():
    """`leave` (C9) also counts as a frame-cleanup prefix."""
    from c2.commands.decomp_verify import _is_inline_epilogue
    insns = [
        (0x00, 1, b"\xc9", "leave"),
        (0x01, 1, b"\x5b", "pop ebx"),
        (0x02, 1, b"\xc3", "ret"),
    ]
    assert _is_inline_epilogue(insns, 0) == 3


def test_inline_epilogue_accepts_xor_eax_retval():
    """`xor eax, eax` is a retval-setup prefix (return 0); `sub esp,N`
    and `add eax,N` are NOT epilogue prefixes."""
    from c2.commands.decomp_verify import _is_inline_epilogue
    # xor eax, eax -> retval (return 0); pop ebx; ret -> VALID
    insns_xor = [
        (0x00, 2, b"\x31\xc0", "xor eax, eax"),
        (0x02, 1, b"\x5b", "pop ebx"),
        (0x03, 1, b"\xc3", "ret"),
    ]
    assert _is_inline_epilogue(insns_xor, 0) == 3
    # starting from the pop also works
    assert _is_inline_epilogue(insns_xor, 1) == 2

    # sub esp, 8 (0x83 0xec 0x08) is NOT a cleanup (only ADD is)
    insns_sub = [
        (0x00, 3, b"\x83\xec\x08", "sub esp, 8"),
        (0x03, 1, b"\x5b", "pop ebx"),
        (0x04, 1, b"\xc3", "ret"),
    ]
    assert _is_inline_epilogue(insns_sub, 0) == 0

    # add eax, 8 (0x83 0xc0 0x08) is NOT esp cleanup
    insns_add_eax = [
        (0x00, 3, b"\x83\xc0\x08", "add eax, 8"),
        (0x03, 1, b"\x5b", "pop ebx"),
        (0x04, 1, b"\xc3", "ret"),
    ]
    assert _is_inline_epilogue(insns_add_eax, 0) == 0


def test_inline_epilogue_with_retval():
    """Inline epilogue starting with a return-value setup -- the classic
    `mov eax, RET; pop ...; ret` shape that put_danger_flag uses."""
    from c2.commands.decomp_verify import _is_inline_epilogue, _epilogue_len
    insns = [
        (0x00, 5, b"\xb8\x01\x00\x00\x00", "mov eax, 1"),
        (0x05, 1, b"\x5a", "pop edx"),
        (0x06, 1, b"\xc3", "ret"),
    ]
    assert _is_inline_epilogue(insns, 0) == 3
    assert _epilogue_len(insns, 0, len(insns)) == 3

    # retval + cleanup + pops + ret
    insns2 = [
        (0x00, 5, b"\xb8\x06\x00\x00\x00", "mov eax, 6"),
        (0x05, 3, b"\x83\xc4\x08", "add esp, 8"),
        (0x08, 1, b"\x5f", "pop edi"),
        (0x09, 1, b"\x5e", "pop esi"),
        (0x0a, 1, b"\xc3", "ret"),
    ]
    assert _is_inline_epilogue(insns2, 0) == 5


# ── Rule 4 cmp-swap soft-exact filter ────────────────────────────────────

def test_rule4_cmp_swap_basic():
    """`cmp a, b; jl L` vs `cmp b, a; jg L` is semantically identical and
    is the canonical Rule 4 source-ambiguity (`a < b` vs `b > a`)."""
    from c2.commands.decomp_verify import _rule4_only_diffs
    # cmp ebx, edx  -- 39 d3
    # jl 0x05        -- 7c 01
    # ret           -- c3
    # vs
    # cmp edx, ebx  -- 39 da
    # jg 0x05        -- 7f 01
    # ret           -- c3
    orig = b"\x39\xd3\x7c\x01\x90\xc3"
    recomp = b"\x39\xda\x7f\x01\x90\xc3"
    diffs = [i for i in range(len(orig)) if orig[i] != recomp[i]]
    sites = _rule4_only_diffs(orig, recomp, diffs)
    assert sites == 1


def test_rule4_rejects_partial_swap():
    """If the cmp operands are NOT actually swapped, reject (it's a
    genuine reg/imm diff)."""
    from c2.commands.decomp_verify import _rule4_only_diffs
    # cmp ebx, ecx (not swapped with edx) + complementary jcc
    orig = b"\x39\xcb\x7c\x01\x90\xc3"     # cmp ebx, ecx; jl
    recomp = b"\x39\xda\x7f\x01\x90\xc3"   # cmp edx, ebx; jg
    diffs = [i for i in range(len(orig)) if orig[i] != recomp[i]]
    sites = _rule4_only_diffs(orig, recomp, diffs)
    assert sites is None


def test_rule4_rejects_unrelated_diff():
    """Any diff byte not inside a Rule 4 site disqualifies."""
    from c2.commands.decomp_verify import _rule4_only_diffs
    # Same cmp+jcc swap PLUS an unrelated mov byte diff
    # mov eax, 1  -- b8 01 00 00 00
    # vs
    # mov eax, 2  -- b8 02 00 00 00
    # followed by the swap pair
    orig = b"\xb8\x01\x00\x00\x00\x39\xd3\x7c\x01\xc3"
    recomp = b"\xb8\x02\x00\x00\x00\x39\xda\x7f\x01\xc3"
    diffs = [i for i in range(len(orig)) if orig[i] != recomp[i]]
    sites = _rule4_only_diffs(orig, recomp, diffs)
    assert sites is None
