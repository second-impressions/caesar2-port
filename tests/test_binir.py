"""Tests for binary-IR reconstruction (c2.binir).

The recovery is intentionally PARTIAL -- only patterns that map unambiguously
to a cg_op shape are emitted.  These tests forge minimal asm sequences to
exercise each recognized pattern in isolation.
"""
from __future__ import annotations

from c2.binir import recover, summarize, RecoveredOp


def _asm(*entries: tuple[int, int, bytes, str]) -> list:
    """Build a list of InsnT tuples from compact (off, size, bytes, asm)."""
    return list(entries)


# ---- R_MOVOP2TEMP shared-divisor idiv pair (Rule 5c FIRED) ----------------

def test_r5c_idiv_pair_two_idivs_same_reg_with_imm_load():
    """Two `idiv R` with NO intervening reload of R, preceded by `mov R, IMM`."""
    insns = _asm(
        (0, 5, b'\xb9\x02\x00\x00\x00', 'mov ecx, 2'),
        (5, 2, b'\x89\xc2',             'mov edx, eax'),
        (7, 3, b'\xc1\xfa\x1f',         'sar edx, 0x1f'),
        (10, 2, b'\xf7\xf9',            'idiv ecx'),
        (12, 2, b'\x89\xd8',            'mov eax, ebx'),
        (14, 2, b'\x89\xda',            'mov edx, ebx'),
        (16, 3, b'\xc1\xfa\x1f',        'sar edx, 0x1f'),
        (19, 2, b'\xf7\xf9',            'idiv ecx'),
    )
    ops = recover(insns)
    r5c = [o for o in ops if o.kind == "r5c_idiv_pair"]
    assert len(r5c) == 1
    assert r5c[0].detail["div_reg"] == "ecx"
    assert r5c[0].detail["divisor_imm"] == 2
    assert "Rule 5c FIRED" in r5c[0].note
    assert r5c[0].offset == 0
    # Length spans from `mov ecx, 2` through the second `idiv ecx` -- the
    # full Rule 5c signature window.
    assert r5c[0].length == 21


def test_r5c_idiv_pair_no_match_when_divisor_reloaded():
    # `mov ecx, 2 ; idiv ecx ; mov ecx, 4 ; idiv ecx` -- different divisor
    # reloaded between idivs.  NOT Rule 5c -- two independent divides.
    insns = _asm(
        (0, 5, b'\xb9\x02\x00\x00\x00', 'mov ecx, 2'),
        (5, 2, b'\xf7\xf9',             'idiv ecx'),
        (7, 5, b'\xb9\x04\x00\x00\x00', 'mov ecx, 4'),
        (12, 2, b'\xf7\xf9',            'idiv ecx'),
    )
    ops = recover(insns)
    assert not any(o.kind == "r5c_idiv_pair" for o in ops)


def test_r5c_idiv_pair_no_match_when_only_one_idiv():
    insns = _asm(
        (0, 5, b'\xb9\x02\x00\x00\x00', 'mov ecx, 2'),
        (5, 2, b'\xf7\xf9',             'idiv ecx'),
    )
    assert not any(o.kind == "r5c_idiv_pair" for o in recover(insns))


def test_r5c_idiv_pair_no_match_with_different_div_regs():
    # `idiv ecx ; idiv edi` -- two divides but different registers, not the
    # shared-divisor Rule 5c signature.
    insns = _asm(
        (0, 2, b'\xf7\xf9', 'idiv ecx'),
        (2, 2, b'\xf7\xff', 'idiv edi'),
    )
    assert not any(o.kind == "r5c_idiv_pair" for o in recover(insns))


# ---- G_POW2DIV (Pow2Div for 2^N, N>=2) -----------------------------------

def test_g_pow2div_idiom_recognised():
    # sar reg,31 ; shl reg,4 ; sbb dst,reg ; sar dst,4 == /16
    insns = _asm(
        (0, 3, b'\xc1\xfa\x1f', 'sar edx, 0x1f'),
        (3, 3, b'\xc1\xe2\x04', 'shl edx, 4'),
        (6, 2, b'\x1b\xc2',     'sbb eax, edx'),
        (8, 3, b'\xc1\xf8\x04', 'sar eax, 4'),
    )
    ops = recover(insns)
    pow2 = [o for o in ops if o.kind == "g_pow2div"]
    assert len(pow2) == 1
    assert pow2[0].detail["shift"] == 4
    assert pow2[0].op == "OP_DIV(*, 2^N)"


def test_g_pow2div_no_match_for_shift_1():
    # shift=1 is the By2Div case (G_DIV2), not Pow2Div.
    insns = _asm(
        (0, 3, b'\xc1\xfa\x1f', 'sar edx, 0x1f'),
        (3, 3, b'\xc1\xe2\x01', 'shl edx, 1'),
        (6, 2, b'\x1b\xc2',     'sbb eax, edx'),
        (8, 3, b'\xc1\xf8\x01', 'sar eax, 1'),
    )
    ops = recover(insns)
    assert not any(o.kind == "g_pow2div" for o in ops)


# ---- G_DIV2 (By2Div for /2 specifically) --------------------------------

def test_g_div2_idiom_recognised():
    # sar reg,31 ; sub dst,reg ; sar dst,1
    insns = _asm(
        (0, 3, b'\xc1\xfa\x1f', 'sar edx, 0x1f'),
        (3, 2, b'\x29\xd0',     'sub eax, edx'),
        (5, 2, b'\xd1\xf8',     'sar eax, 1'),
    )
    ops = recover(insns)
    div2 = [o for o in ops if o.kind == "g_div2"]
    assert len(div2) == 1
    assert div2[0].op == "OP_DIV(*, 2)"
    assert "By2Div" in div2[0].note


# ---- zext byte load (Rule 49 family) ------------------------------------

def test_zext_byte_load_idiom_recognised():
    # xor eax, eax ; mov al, [mem]
    insns = _asm(
        (0, 2, b'\x31\xc0', 'xor eax, eax'),
        (2, 6, b'\x8a\x05\x00\x00\x00\x00', 'mov al, byte ptr [0]'),
    )
    ops = recover(insns)
    zext = [o for o in ops if o.kind == "zext_byte_load"]
    assert len(zext) == 1
    assert zext[0].detail["reg"] == "eax"


def test_zext_byte_load_no_match_when_xor_then_imm_mov():
    # xor eax,eax ; mov eax, 5 -- not a byte load idiom.
    insns = _asm(
        (0, 2, b'\x31\xc0', 'xor eax, eax'),
        (2, 5, b'\xb8\x05\x00\x00\x00', 'mov eax, 5'),
    )
    assert not any(o.kind == "zext_byte_load" for o in recover(insns))


def test_zext_clr_reg_register_source():
    # xor eax, eax ; mov al, dl -- rCLRHI_R disjoint form (PS-side
    # AL-squat signature: the byte value lives in DL, not AL).
    insns = _asm(
        (0, 2, b'\x31\xc0', 'xor eax, eax'),
        (2, 2, b'\x88\xd0', 'mov al, dl'),
    )
    ops = recover(insns)
    clr = [o for o in ops if o.kind == "zext_clr_reg"]
    assert len(clr) == 1
    assert clr[0].detail["src"] == "dl"
    assert not any(o.kind == "zext_byte_load" for o in ops)


def test_zext_and_inplace_recognised():
    # and eax, 0xff -- rCLRHI_R overlap form (RC-side AL-squat signature).
    insns = _asm(
        (0, 5, b'\x25\xff\x00\x00\x00', 'and eax, 0xff'),
    )
    ops = recover(insns)
    z = [o for o in ops if o.kind == "zext_and_inplace"]
    assert len(z) == 1
    assert z[0].detail["width"] == 8


def test_zext_and_inplace_ignores_other_masks():
    # and eax, 0xf0 is a real mask, not a zext.
    insns = _asm(
        (0, 3, b'\x83\xe0\xf0', 'and eax, 0xf0'),
    )
    assert not any(o.kind == "zext_and_inplace" for o in recover(insns))


def test_zext_forms_map_to_same_tree_shape():
    # The two rCLRHI_R lowerings are ONE IR op: tree_diff must give them
    # identical shapes so an AL-squat seating divergence is never
    # misreported as an IR-tree difference.
    from c2.tree_diff import shape_from_binir_ops
    a = recover(_asm(
        (0, 2, b'\x31\xc0', 'xor eax, eax'),
        (2, 2, b'\x88\xd0', 'mov al, dl'),
    ))
    b = recover(_asm(
        (0, 5, b'\x25\xff\x00\x00\x00', 'and eax, 0xff'),
    ))
    sa = shape_from_binir_ops(a)
    sb = shape_from_binir_ops(b)
    assert [s.op for s in sa] == [s.op for s in sb]
    assert sa[0].op == "UNARY:O_CONVERT"
    assert [c.op for c in sa[0].children] == [c.op for c in sb[0].children]


# ---- summarize -----------------------------------------------------------

def test_summarize_counts_patterns():
    insns = _asm(
        (0, 2, b'\x31\xc0', 'xor eax, eax'),
        (2, 6, b'\x8a\x05\x00\x00\x00\x00', 'mov al, byte ptr [0]'),
        (8, 3, b'\xc1\xfa\x1f', 'sar edx, 0x1f'),
        (11, 2, b'\x29\xd0',    'sub eax, edx'),
        (13, 2, b'\xd1\xf8',    'sar eax, 1'),
    )
    summary = summarize(recover(insns))
    assert summary == {"zext_byte_load": 1, "g_div2": 1}


# ---- end-to-end: v_mf and v_df comparison --------------------------------

def test_v_mf_recovers_r5c_signature():
    """v_mf (% then /, both pow2=2): Rule 5c FIRED -> single r5c_idiv_pair."""
    insns = _asm(
        (0,  5, b'\xb9\x02\x00\x00\x00', 'mov ecx, 2'),
        (5,  2, b'\x89\xc2',             'mov edx, eax'),
        (7,  3, b'\xc1\xfa\x1f',         'sar edx, 0x1f'),
        (10, 2, b'\xf7\xf9',             'idiv ecx'),
        (12, 6, b'\x89\x15\x00\x00\x00\x00', 'mov [m], edx'),
        (18, 2, b'\x89\xd8',             'mov eax, ebx'),
        (20, 2, b'\x89\xda',             'mov edx, ebx'),
        (22, 3, b'\xc1\xfa\x1f',         'sar edx, 0x1f'),
        (25, 2, b'\xf7\xf9',             'idiv ecx'),
    )
    ops = recover(insns)
    assert summarize(ops) == {"r5c_idiv_pair": 1}


def test_v_df_recovers_g_div2_signature_no_5c():
    """v_df (/ then %, both /2): / -> By2Div, % -> idiv (separate)."""
    insns = _asm(
        (0,  3, b'\xc1\xfa\x1f',         'sar edx, 0x1f'),
        (3,  2, b'\x29\xd0',             'sub eax, edx'),
        (5,  2, b'\xd1\xf8',             'sar eax, 1'),
        (7,  6, b'\xa3\x00\x00\x00\x00\x00', 'mov [m], eax'),
        (13, 5, b'\xb9\x02\x00\x00\x00', 'mov ecx, 2'),
        (18, 2, b'\x89\xd8',             'mov eax, ebx'),
        (20, 2, b'\x89\xda',             'mov edx, ebx'),
        (23, 3, b'\xc1\xfa\x1f',         'sar edx, 0x1f'),
        (26, 2, b'\xf7\xf9',             'idiv ecx'),
    )
    ops = recover(insns)
    summary = summarize(ops)
    assert "g_div2" in summary
    # Only ONE idiv -- no r5c_idiv_pair signature.
    assert "r5c_idiv_pair" not in summary


# ---- Multiplication strength reduction ----------------------------------

def test_mul_pow2_bare_shl():
    """shl reg, N -> multiply by 2^N."""
    insns = _asm((0, 3, b'\xc1\xe6\x03', 'shl esi, 3'))   # esi *= 8
    ops = recover(insns)
    mul = [o for o in ops if o.kind == "mul_pow2"]
    assert len(mul) == 1
    assert mul[0].detail["shift"] == 3
    assert mul[0].detail["factor"] == 8
    assert "OP_MUL" in mul[0].op


def test_mul_const_minus_one_via_mov_shl_sub():
    """get_region_2x2_start's `row * 15` (preparing for * 480):
       mov ebx, eax ; shl ebx, 4 ; sub ebx, eax -> ebx = eax * (16-1) = eax*15.
    """
    insns = _asm(
        (0, 2, b'\x89\xc3', 'mov ebx, eax'),
        (2, 3, b'\xc1\xe3\x04', 'shl ebx, 4'),
        (5, 2, b'\x29\xc3', 'sub ebx, eax'),
    )
    ops = recover(insns)
    mul = [o for o in ops if o.kind == "mul_const_minus_one"]
    assert len(mul) == 1
    assert mul[0].detail["factor"] == 15
    assert mul[0].detail["shift"] == 4
    # The bare `shl ebx, 4` should NOT also emit mul_pow2 -- it's part of
    # the compound idiom.
    assert not any(o.kind == "mul_pow2" for o in ops)


def test_mul_const_plus_one_via_mov_shl_add():
    """mov tmp, src ; shl src, N ; add src, tmp -> src = src_orig * (2^N + 1)."""
    insns = _asm(
        (0, 2, b'\x89\xc3', 'mov ebx, eax'),
        (2, 3, b'\xc1\xe3\x02', 'shl ebx, 2'),
        (5, 2, b'\x01\xc3', 'add ebx, eax'),
    )
    ops = recover(insns)
    mul = [o for o in ops if o.kind == "mul_const_plus_one"]
    assert len(mul) == 1
    assert mul[0].detail["factor"] == 5     # 2^2 + 1 = 5


def test_mul_lea_scaled_self():
    """lea dst, [src + src*K] -> dst = src * (K+1)."""
    insns = _asm(
        (0, 3, b'\x8d\x04\x4d', 'lea eax, [ecx + ecx*2]'),  # = ecx * 3
    )
    ops = recover(insns)
    mul = [o for o in ops if o.kind == "mul_lea_scaled_self"]
    assert len(mul) == 1
    assert mul[0].detail["src"] == "ecx"
    assert mul[0].detail["factor"] == 3


def test_get_region_2x2_start_row_times_480_shape():
    """The actual `row * 480` from get_region_2x2_start:
       row * 480 = row * (16-1) * 32 = (shl row, 4 ; sub row, orig) ; shl row, 5

    SINCE the OW v1 CheckMul source emits THIS WHOLE SEQUENCE as the
    expansion of a single ``ins->operands[1] = AllocIntConst(480)``,
    binir folds it back into ONE ``mul_const`` op (factor=480) -- not
    the old 2-op split.  See watcom10.0a knowledge file CheckMul@0x61c32
    plate for the canonical pattern.
    """
    insns = _asm(
        (0, 2, b'\x89\xc3', 'mov ebx, eax'),    # save row in ebx
        (2, 3, b'\xc1\xe3\x04', 'shl ebx, 4'),  # ebx = row * 16
        (5, 2, b'\x29\xc3', 'sub ebx, eax'),    # ebx = row * 15
        (7, 3, b'\xc1\xe3\x05', 'shl ebx, 5'),  # ebx = row * 15 * 32 = row*480
    )
    ops = recover(insns)
    kinds = [o.kind for o in ops]
    assert kinds == ["mul_const"], kinds
    assert ops[0].detail["factor"] == 480
    assert ops[0].detail["base"] == "eax"
    assert ops[0].detail["result"] == "ebx"
    assert ops[0].detail["chain_insns"] == 3   # shl + sub + shl


def test_mul_const_chain_factor_20_test_for_any_admin():
    """test_for_any_admin's `n * 20` (stride computation) -- canonical 3-op
    chain (shl 2 ; add ; shl 2) preceded by a preservation mov, with an
    UNRELATED ``mov esi, edx`` between the preservation and the chain
    (regalloc-introduced).  The 8-instruction backward budget reaches
    over the unrelated mov to find the preservation."""
    insns = _asm(
        (0, 2, b'\x89\xd1', 'mov ecx, edx'),    # preservation
        (2, 2, b'\x89\xd6', 'mov esi, edx'),    # UNRELATED -- esi for `i^j`
        (4, 3, b'\xc1\xe2\x02', 'shl edx, 2'),  # *4
        (7, 2, b'\x01\xca', 'add edx, ecx'),    # *5
        (9, 3, b'\xc1\xe2\x02', 'shl edx, 2'),  # *20
    )
    ops = recover(insns)
    mc = [o for o in ops if o.kind == "mul_const"]
    assert len(mc) == 1
    assert mc[0].detail["factor"] == 20
    assert mc[0].detail["base"] == "ecx"
    assert mc[0].detail["result"] == "edx"
    assert mc[0].detail["chain_insns"] == 3


def test_mul_const_chain_factor_1000_hospital_coverage():
    """hospital_coverage's `x * 1000` -- 5-op chain (shl 5 ; sub ; shl 2 ;
    add ; shl 3): 32-1=31 ; *4=124 ; +1=125 ; *8=1000.  Anchored on the
    leading preservation mov."""
    insns = _asm(
        (0, 2, b'\x89\xd8', 'mov eax, ebx'),       # mov #2 surviving (seed)
        (2, 3, b'\xc1\xe0\x05', 'shl eax, 5'),     # *32
        (5, 2, b'\x29\xd8', 'sub eax, ebx'),       # *31
        (7, 3, b'\xc1\xe0\x02', 'shl eax, 2'),     # *124
        (10, 2, b'\x01\xd8', 'add eax, ebx'),      # *125
        (12, 3, b'\xc1\xe0\x03', 'shl eax, 3'),    # *1000
    )
    ops = recover(insns)
    mc = [o for o in ops if o.kind == "mul_const"]
    assert len(mc) == 1
    assert mc[0].detail["factor"] == 1000
    assert mc[0].detail["base"] == "ebx"
    assert mc[0].detail["result"] == "eax"
    assert mc[0].detail["chain_insns"] == 5


# ---- cmp / test + jcc ---------------------------------------------------

def test_cmp_imm_jcc_recognised():
    insns = _asm(
        (0, 6, b'\x81\xfd\xd4\x00\x00\x00', 'cmp ebp, 0xd4'),
        (6, 2, b'\x75\x06', 'jne 0xe'),
    )
    ops = recover(insns)
    cj = [o for o in ops if o.kind == "cmp_jcc"]
    assert len(cj) == 1
    assert cj[0].detail["imm"] == 0xd4
    assert cj[0].detail["jcc"] == "jne"
    assert "O_CMP_NOT_EQUAL" in cj[0].op


def test_zero_test_jcc_recognised():
    insns = _asm(
        (0, 2, b'\x85\xc0', 'test eax, eax'),
        (2, 2, b'\x74\x06', 'je 0xa'),
    )
    ops = recover(insns)
    cj = [o for o in ops if o.kind == "zero_test_jcc"]
    assert len(cj) == 1
    assert cj[0].detail["reg"] == "eax"
    assert "O_CMP_EQUAL" in cj[0].op


def test_cmp_without_jcc_is_not_a_match():
    """cmp alone (no following jcc) is just a comparison; might be used
    for a setcc or other purpose -- don't claim cmp_jcc."""
    insns = _asm(
        (0, 6, b'\x81\xfd\xd4\x00\x00\x00', 'cmp ebp, 0xd4'),
        (6, 2, b'\x90\x90', 'nop ; nop'),
    )
    ops = recover(insns)
    assert not any(o.kind == "cmp_jcc" for o in ops)


# ---- signed/unsigned extension loads -------------------------------------

def test_movzx_byte_load():
    insns = _asm(
        (0, 7, b'\x0f\xb6\x05\x00\x00\x00\x00', 'movzx eax, byte ptr [0]'),
    )
    ops = recover(insns)
    z = [o for o in ops if o.kind == "zext_load_byte"]
    assert len(z) == 1
    assert z[0].detail["signed"] is False
    assert z[0].detail["size"] == "byte"


def test_movsx_word_load():
    insns = _asm(
        (0, 7, b'\x0f\xbf\x05\x00\x00\x00\x00', 'movsx eax, word ptr [0]'),
    )
    ops = recover(insns)
    z = [o for o in ops if o.kind == "signext_load_word"]
    assert len(z) == 1
    assert z[0].detail["signed"] is True


# ---- listing renderer ----------------------------------------------------

def test_render_listing_mixes_patterns_and_passthrough():
    """Combines recognised idioms with un-matched insns into a single
    pseudo-listing -- the IR-level view of a function."""
    insns = _asm(
        (0, 3, b'\xc1\xfa\x1f', 'sar edx, 0x1f'),    # part of g_div2
        (3, 2, b'\x29\xd0',     'sub eax, edx'),
        (5, 2, b'\xd1\xf8',     'sar eax, 1'),
        (7, 6, b'\xa3\x00\x00\x00\x00\x00', 'mov dword ptr [0], eax'),  # passthrough
    )
    from c2.binir import render_listing
    lines = render_listing(insns)
    # 4 insns -> 1 recognised op (g_div2) + 1 passthrough (mov) = 2 lines.
    assert len(lines) == 2
    assert "g_div2" in lines[0]
    assert "mov dword ptr" in lines[1]


# ---- pre_gets_mem_const (direct-memory-RMW with constant) ---------------

def test_pre_gets_and_byte_mem_imm():
    """`and byte ptr [m], 0xfc` -- the Rule 17b smoking gun."""
    insns = _asm(
        (0, 7, b'\x80\x25\x00\x00\x00\x00\xfc',
         'and byte ptr [0], 0xfc'),
    )
    ops = recover(insns)
    pg = [o for o in ops if o.kind == "pre_gets_mem_const"]
    assert len(pg) == 1
    assert pg[0].detail["binop"] == "and"
    assert pg[0].detail["cg_op"] == "O_AND"
    assert pg[0].detail["size"] == "byte"
    assert pg[0].detail["imm"] == 0xfc
    assert "Rule 17b" in pg[0].note


def test_pre_gets_or_dword_mem_imm():
    insns = _asm(
        (0, 7, b'\x81\x0d\x00\x00\x00\x00\x00\x01\x00\x00',
         'or dword ptr [0], 0x100'),
    )
    ops = recover(insns)
    pg = [o for o in ops if o.kind == "pre_gets_mem_const"]
    assert len(pg) == 1
    assert pg[0].detail["cg_op"] == "O_OR"
    assert pg[0].detail["size"] == "dword"
    assert pg[0].detail["imm"] == 0x100


def test_pre_gets_add_sub_xor_recognised():
    """The full alu family lands in pre_gets_mem_const."""
    for mn, cg in [("add", "O_PLUS"), ("sub", "O_MINUS"), ("xor", "O_XOR")]:
        insns = _asm((0, 7, b'\x00' * 7, f'{mn} byte ptr [0x1234], 0x10'))
        ops = recover(insns)
        pg = [o for o in ops if o.kind == "pre_gets_mem_const"]
        assert len(pg) == 1, f"{mn} not recognised"
        assert pg[0].detail["cg_op"] == cg


def test_pre_gets_mem_const_rejects_register_destinations():
    """`and eax, 0xfc` is NOT direct-memory-RMW (different tree shape)."""
    insns = _asm((0, 5, b'\x83\xe0\xfc', 'and eax, 0xfc'))
    ops = recover(insns)
    assert not any(o.kind == "pre_gets_mem_const" for o in ops)


# ---- mov_mem_imm (ASSIGN(LEAF:MEMORY, LEAF:CONSTANT)) -------------------

def test_mov_mem_imm_dword():
    insns = _asm(
        (0, 10, b'\xc7\x05\x00\x00\x00\x00\x42\x00\x00\x00',
         'mov dword ptr [0], 0x42'),
    )
    ops = recover(insns)
    mm = [o for o in ops if o.kind == "mov_mem_imm"]
    assert len(mm) == 1
    assert mm[0].detail["size"] == "dword"
    assert mm[0].detail["imm"] == 0x42


def test_mov_mem_imm_byte():
    insns = _asm(
        (0, 7, b'\xc6\x05\x00\x00\x00\x00\x00',
         'mov byte ptr [0], 0'),
    )
    ops = recover(insns)
    mm = [o for o in ops if o.kind == "mov_mem_imm"]
    assert len(mm) == 1
    assert mm[0].detail["size"] == "byte"
    assert mm[0].detail["imm"] == 0


def test_mov_mem_imm_rejects_register_destination():
    """`mov eax, 5` is NOT a memory store (different tree shape)."""
    insns = _asm((0, 5, b'\xb8\x05\x00\x00\x00', 'mov eax, 5'))
    ops = recover(insns)
    assert not any(o.kind == "mov_mem_imm" for o in ops)


def test_mov_mem_imm_rejects_register_to_memory():
    """`mov [m], eax` is a store but NOT a constant store (no IMM)."""
    insns = _asm(
        (0, 6, b'\x89\x05\x00\x00\x00\x00', 'mov dword ptr [0], eax'),
    )
    ops = recover(insns)
    assert not any(o.kind == "mov_mem_imm" for o in ops)


# ---- call_with_args -----------------------------------------------------

def test_call_with_args_two_args_with_cleanup():
    """`push arg2 ; push arg1 ; call FN ; add esp, 8`."""
    insns = _asm(
        (0, 5, b'\x68\x02\x00\x00\x00', 'push 2'),
        (5, 5, b'\x68\x01\x00\x00\x00', 'push 1'),
        (10, 5, b'\xe8\x00\x00\x00\x00', 'call 0xf'),
        (15, 3, b'\x83\xc4\x08', 'add esp, 8'),
    )
    ops = recover(insns)
    cw = [o for o in ops if o.kind == "call_with_args"]
    assert len(cw) == 1
    assert cw[0].detail["argc"] == 2
    assert cw[0].detail["cleanup"] == 8
    assert cw[0].offset == 0
    assert cw[0].length == 18


def test_call_with_args_no_cleanup_still_matches():
    """callee-cleanup or no-cleanup: still recover the call-with-args.
    Compiler-helper filtering (stack-check at function entry, register-save
    + unrelated call in __watcall code) is the JOB OF THE AUDIT'S TRACE-
    OFFSET MAP, NOT this matcher.  binir stays structural."""
    insns = _asm(
        (0, 5, b'\x68\x01\x00\x00\x00', 'push 1'),
        (5, 5, b'\xe8\x00\x00\x00\x00', 'call 0xa'),
    )
    ops = recover(insns)
    cw = [o for o in ops if o.kind == "call_with_args"]
    assert len(cw) == 1
    assert cw[0].detail["cleanup"] is None


def test_call_with_args_rejects_segment_register_push():
    """`push ds; call FN` is the __far prologue, never a user-call arg."""
    insns = _asm(
        (0, 1, b'\x1e', 'push ds'),
        (1, 5, b'\xe8\x00\x00\x00\x00', 'call 0x6'),
    )
    ops = recover(insns)
    assert not any(o.kind == "call_with_args" for o in ops)


def test_call_with_no_args_is_not_recovered():
    """Bare `call FN` without preceding pushes is just asm passthrough."""
    insns = _asm(
        (0, 5, b'\xe8\x00\x00\x00\x00', 'call 0x5'),
    )
    ops = recover(insns)
    assert not any(o.kind == "call_with_args" for o in ops)


def test_call_with_args_only_consumes_contiguous_pushes():
    """Non-push instructions between pushes break the contiguous run."""
    insns = _asm(
        (0, 5, b'\x68\x02\x00\x00\x00', 'push 2'),
        (5, 2, b'\x89\xc1', 'mov ecx, eax'),     # breaks contiguity
        (7, 5, b'\x68\x01\x00\x00\x00', 'push 1'),
        (12, 5, b'\xe8\x00\x00\x00\x00', 'call 0x11'),
    )
    ops = recover(insns)
    cw = [o for o in ops if o.kind == "call_with_args"]
    # Only the contiguous push immediately before the call is the arg.
    assert len(cw) == 1
    assert cw[0].detail["argc"] == 1


# ---- branch_simple ------------------------------------------------------

def test_branch_jmp_recovered():
    insns = _asm(
        (0, 5, b'\xe9\x10\x00\x00\x00', 'jmp 0x15'),
    )
    ops = recover(insns)
    br = [o for o in ops if o.kind == "branch_jmp"]
    assert len(br) == 1
    assert "GOTO" in br[0].op


def test_branch_flag_jcc_after_dec():
    """`dec ecx ; jnz loop` -- flag set by dec, jcc uses ZF."""
    insns = _asm(
        (0, 1, b'\x49', 'dec ecx'),
        (1, 2, b'\x75\xfd', 'jnz 0'),
    )
    ops = recover(insns)
    br = [o for o in ops if o.kind == "branch_flag_jcc"]
    assert len(br) == 1
    assert "O_CMP_NOT_EQUAL" in br[0].op


def test_branch_simple_skips_cmp_jcc_compound():
    """A jcc preceded by cmp must NOT be matched by branch_simple
    (cmp_jcc already owns the compound)."""
    insns = _asm(
        (0, 3, b'\x83\xf8\x05', 'cmp eax, 5'),
        (3, 2, b'\x74\x06', 'je 0xb'),
    )
    ops = recover(insns)
    assert not any(o.kind in {"branch_jmp", "branch_flag_jcc"} for o in ops)
    # And cmp_jcc DID claim it.
    assert any(o.kind == "cmp_jcc" for o in ops)


def test_branch_simple_skips_after_reg_reg_cmp():
    """`cmp eax, ebx ; jne tgt` -- cmp_jcc can't match (no immediate);
    branch_simple still skips (a real compare, just not yet supported)."""
    insns = _asm(
        (0, 2, b'\x39\xd8', 'cmp eax, ebx'),
        (2, 2, b'\x75\x06', 'jne 0xa'),
    )
    ops = recover(insns)
    assert not any(o.kind in {"branch_jmp", "branch_flag_jcc"} for o in ops)


def test_render_listing_handles_overlapping_patterns():
    """Make sure the renderer respects the offset-coverage of a recognised
    op (skips ALL insns within its span).  With the post-folder behaviour
    the whole 4-ins ``row * 480`` sequence is ONE ``mul_const`` op, so the
    renderer emits a single condensed line."""
    insns = _asm(
        (0, 2, b'\x89\xc3', 'mov ebx, eax'),
        (2, 3, b'\xc1\xe3\x04', 'shl ebx, 4'),
        (5, 2, b'\x29\xc3', 'sub ebx, eax'),
        (7, 3, b'\xc1\xe3\x05', 'shl ebx, 5'),
    )
    from c2.binir import render_listing
    lines = render_listing(insns)
    assert len(lines) == 1
    assert "mul_const" in lines[0]
    assert "480" in lines[0]


def test_zext_copy_and():
    # Rule 127 PS-side signature: mov al,<byte reg>; and eax,0xff
    insns = [
        (0, 2, b"\x88\xe8", "mov al, ch"),
        (2, 5, b"\x25\xff\x00\x00\x00", "and eax, 0xff"),
    ]
    ops = recover(insns)
    assert [o.kind for o in ops] == ["zext_copy_and"]
    assert ops[0].detail["src"] == "ch"
    assert ops[0].op == "OP_CONVERT_U8_U32(copy)"


def test_zext_copy_and_not_al_source():
    # mov al, al never happens; mov al from MEMORY must NOT match -- that is
    # a plain byte load (and-inplace then claims the and).
    insns = [
        (0, 5, b"\xa0\x00\x00\x00\x00", "mov al, byte ptr [0x100]"),
        (5, 5, b"\x25\xff\x00\x00\x00", "and eax, 0xff"),
    ]
    ops = recover(insns)
    assert "zext_copy_and" not in [o.kind for o in ops]


def test_const_store_run_reg_form():
    insns = [
        (0, 2, b"\x31\xd2", "xor edx, edx"),
        (2, 6, b"\x90" * 6, "mov dword ptr [eax + 0x8473e], edx"),
        (8, 6, b"\x90" * 6, "mov dword ptr [eax + 0x8472e], edx"),
        (14, 6, b"\x90" * 6, "mov dword ptr [eax + 0x8473a], edx"),
    ]
    ops = recover(insns)
    assert [o.kind for o in ops] == ["const_store_run_reg"]
    assert ops[0].detail == {"form": "reg", "n": 3, "value": 0, "reg": "edx"}


def test_const_store_run_imm_form_and_materialize():
    insns = [
        (0, 3, b"\xc1\xe0\x02", "shl eax, 2"),
        (3, 5, b"\x05\x00\x00\x00\x00", "add eax, 0"),       # fixup base
        (8, 10, b"\x90" * 10, "mov dword ptr [eax + 0x76], 0"),
        (18, 10, b"\x90" * 10, "mov dword ptr [eax + 0x7a], 0"),
    ]
    kinds = [o.kind for o in recover(insns)]
    assert "ptr_base_materialize" in kinds
    assert "const_store_run_imm" in kinds


def test_const_store_run_not_single_store():
    # one store stays mov_mem_imm (no run)
    insns = [
        (0, 10, b"\x90" * 10, "mov dword ptr [eax + 0x76], 0"),
        (10, 2, b"\x31\xc0", "xor eax, eax"),
        (12, 1, b"\xc3", "ret"),
    ]
    kinds = [o.kind for o in recover(insns)]
    assert "const_store_run_imm" not in kinds
    assert "mov_mem_imm" in kinds


def test_const_store_run_reg_does_not_steal_zext():
    # xor eax,eax ; mov al,[mem] must stay zext_byte_load
    insns = [
        (0, 2, b"\x31\xc0", "xor eax, eax"),
        (2, 5, b"\xa0\x00\x00\x00\x00", "mov al, byte ptr [0x100]"),
    ]
    kinds = [o.kind for o in recover(insns)]
    assert kinds == ["zext_byte_load"]


def _sum_insns():
    # g = a+b+c+d+e under -4r: merged b,c; acc-swap d; last-term e split
    return [
        (0, 5, b"\x90" * 5, "mov eax, dword ptr [0x100]"),
        (5, 6, b"\x90" * 6, "add eax, dword ptr [0x104]"),
        (11, 6, b"\x90" * 6, "add eax, dword ptr [0x108]"),
        (17, 6, b"\x90" * 6, "mov edx, dword ptr [0x10c]"),
        (23, 2, b"\x90" * 2, "add edx, eax"),                 # acc swap
        (25, 6, b"\x90" * 6, "mov eax, dword ptr [0x110]"),
        (31, 2, b"\x90" * 2, "add edx, eax"),                 # last term
        (33, 6, b"\x90" * 6, "mov dword ptr [0x114], edx"),
    ]


def test_mem_sum_chain_five_terms():
    ops = recover(_sum_insns())
    chains = [o for o in ops if o.kind == "mem_sum_chain"]
    assert len(chains) == 1
    assert chains[0].detail["n"] == 5
    assert chains[0].offset == 0 and chains[0].length == 39


def test_mem_sum_chain_tree_shape():
    from c2.tree_diff import shape_from_binir_ops
    ops = [o for o in recover(_sum_insns()) if o.kind == "mem_sum_chain"]
    sh = shape_from_binir_ops(ops)
    assert len(sh) == 1 and sh[0].op == "ASSIGN"
    # nested O_PLUS chain depth = n-1 = 4
    depth = 0
    node = sh[0].children[1]
    while node.op == "BINARY:O_PLUS":
        depth += 1
        node = node.children[0]
    assert depth == 4


def test_mem_sum_chain_requires_store():
    insns = _sum_insns()[:-1]   # no final store
    assert "mem_sum_chain" not in [o.kind for o in recover(insns)]


def test_mem_sum_chain_not_rmw_chain():
    # `g = a+b; g += c;` RMW form must NOT be claimed as one chain
    insns = [
        (0, 5, b"\x90" * 5, "mov eax, dword ptr [0x100]"),
        (5, 6, b"\x90" * 6, "mov edx, dword ptr [0x104]"),
        (11, 2, b"\x90" * 2, "add eax, edx"),
        (13, 6, b"\x90" * 6, "mov dword ptr [0x114], eax"),
        (19, 6, b"\x90" * 6, "mov eax, dword ptr [0x108]"),
        (25, 6, b"\x90" * 6, "add dword ptr [0x114], eax"),
    ]
    chains = [o for o in recover(insns) if o.kind == "mem_sum_chain"]
    assert len(chains) == 1 and chains[0].detail["n"] == 2


# ── copy_then_op (Rule 132) ─────────────────────────────────────────────

def test_copy_then_op_basic():
    from c2.binir import recover
    insns = [
        (0, 2, b"\x90" * 2, "mov ecx, eax"),
        (2, 2, b"\x90" * 2, "sub ecx, ebx"),
        (4, 6, b"\x90" * 6, "mov dword ptr [0x43054], ecx"),
    ]
    ops = [o for o in recover(insns) if o.kind == "copy_then_op"]
    assert len(ops) == 1
    d = ops[0].detail
    assert (d["dst"], d["src"], d["binop"]) == ("ecx", "eax", "sub")


def test_copy_then_op_rejects_same_reg_and_mem():
    from c2.binir import recover
    # mov from memory is a load (mem_sum territory), not a copy
    insns = [
        (0, 5, b"\x90" * 5, "mov ecx, dword ptr [0x100]"),
        (5, 2, b"\x90" * 2, "sub ecx, ebx"),
    ]
    assert "copy_then_op" not in [o.kind for o in recover(insns)]
    # alu dst must be the copy target
    insns2 = [
        (0, 2, b"\x90" * 2, "mov ecx, eax"),
        (2, 2, b"\x90" * 2, "sub eax, ebx"),
    ]
    assert "copy_then_op" not in [o.kind for o in recover(insns2)]


# ── loop_rotation_entry / loop_rotation_test_back (Rule 134) ─────────────

def test_loop_rotation_markers_basic():
    """`jmp <forward>` to a `cmp + jcc <back>` at the function bottom
    -- the rotated layout PS emits for `for(;cond;cnt++)`."""
    from c2.binir import recover
    # 0x00: init (xor eax, eax)
    # 0x02: jmp 0x10  <- entry
    # 0x07: body (mov [g], eax + add)
    # 0x10: cmp eax, 0x3c  <- test
    # 0x13: jl 0x07  <- back jcc to body
    insns = [
        (0x00, 2, b"\x90" * 2, "xor eax, eax"),
        (0x02, 5, b"\x90" * 5, "jmp 0x10"),
        (0x07, 6, b"\x90" * 6, "mov dword ptr [0x1234], eax"),
        (0x0d, 3, b"\x90" * 3, "add eax, 1"),
        (0x10, 3, b"\x90" * 3, "cmp eax, 0x3c"),
        (0x13, 2, b"\x90" * 2, "jl 0x07"),
    ]
    ops = recover(insns)
    entries = [o for o in ops if o.kind == "loop_rotation_entry"]
    tests = [o for o in ops if o.kind == "loop_rotation_test_back"]
    assert len(entries) == 1, [o.kind for o in ops]
    assert len(tests) == 1
    assert entries[0].offset == 0x02
    assert entries[0].detail["target"] == 0x10
    assert entries[0].detail["back"] == 0x07
    assert tests[0].offset == 0x10
    assert tests[0].detail["entry"] == 0x02
    assert tests[0].detail["body_target"] == 0x07


def test_loop_rotation_rejects_backward_jmp():
    """Head-tested loops have a BACKWARD `jmp top` at the body bottom.
    They must NOT be tagged as rotated."""
    from c2.binir import recover
    # head-tested: cmp at top, jmp at bottom (backward)
    insns = [
        (0x00, 3, b"\x90" * 3, "cmp eax, 0x3c"),
        (0x03, 2, b"\x90" * 2, "jge 0x10"),
        (0x05, 6, b"\x90" * 6, "mov dword ptr [0x1234], eax"),
        (0x0b, 3, b"\x90" * 3, "add eax, 1"),
        (0x0e, 2, b"\x90" * 2, "jmp 0x00"),
        (0x10, 1, b"\xc3", "ret"),
    ]
    ops = recover(insns)
    assert "loop_rotation_entry" not in [o.kind for o in ops]


def test_loop_rotation_rejects_back_jcc_outside_body():
    """When the bottom jcc's target is BEFORE the rotation entry, the
    rotation contract is violated -- skip."""
    from c2.binir import recover
    insns = [
        (0x00, 3, b"\x90" * 3, "mov eax, 0"),
        (0x03, 5, b"\x90" * 5, "jmp 0x10"),
        (0x08, 6, b"\x90" * 6, "mov dword ptr [0x1234], eax"),
        (0x0e, 2, b"\x90" * 2, "jmp 0x08"),
        (0x10, 3, b"\x90" * 3, "cmp eax, 0x3c"),
        (0x13, 2, b"\x90" * 2, "jl 0x00"),    # target BEFORE entry -- bad
    ]
    ops = recover(insns)
    assert "loop_rotation_entry" not in [o.kind for o in ops]


# ── mid_func_epilogue / backjump_shared_call (Rule 135) ──────────────────

def _devolve_like():
    """Miniature of PS devolve_a_building's layout: cond chain, arm1 with
    the shared call, FRAMED mid epilogue, arms below back-jumping."""
    return [
        (0x00, 3, b"\x90" * 3, "cmp eax, 0xdb"),
        (0x03, 2, b"\x90" * 2, "jne 0x14"),
        (0x05, 2, b"\x90" * 2, "mov dl, al"),        # arm1
        (0x07, 5, b"\x90" * 5, "call 0x100"),         # shared call
        (0x0c, 3, b"\x90" * 3, "add esp, 4"),         # framed epilogue
        (0x0f, 1, b"\x90" * 1, "pop edi"),
        (0x10, 1, b"\x90" * 1, "pop esi"),
        (0x11, 3, b"\x90" * 3, "ret 4"),              # MID ret
        (0x14, 3, b"\x90" * 3, "cmp eax, 0xdf"),      # chain below
        (0x17, 2, b"\x90" * 2, "jne 0x1d"),
        (0x19, 2, b"\x90" * 2, "mov dl, al"),
        (0x1b, 2, b"\x90" * 2, "jmp 0x05"),           # goto do_call arm
        (0x1d, 2, b"\x90" * 2, "mov dl, cl"),
        (0x1f, 2, b"\x90" * 2, "jmp 0x05"),           # goto do_call arm
    ]


def test_mid_func_epilogue_framed():
    from c2.binir import recover
    ops = recover(_devolve_like())
    epis = [o for o in ops if o.kind == "mid_func_epilogue"]
    arms = [o for o in ops if o.kind == "backjump_shared_call"]
    assert len(epis) == 1, [o.kind for o in ops]
    assert epis[0].detail["framed"] is True
    assert epis[0].detail["arms"] == 2
    assert epis[0].offset == 0x0c          # epilogue start (add esp,4)
    assert len(arms) == 2
    assert {a.detail["target"] for a in arms} == {0x05}
    assert "Rule 135" in epis[0].note and "FRAMED" in epis[0].note


def test_mid_func_epilogue_frameless():
    from c2.binir import recover
    insns = [
        (0x00, 3, b"\x90" * 3, "cmp eax, 1"),
        (0x03, 2, b"\x90" * 2, "jne 0x0d"),
        (0x05, 5, b"\x90" * 5, "call 0x100"),
        (0x0a, 1, b"\x90" * 1, "pop edx"),
        (0x0b, 1, b"\x90" * 1, "pop ebx"),
        (0x0c, 1, b"\x90" * 1, "ret"),                # frameless mid ret
        (0x0d, 5, b"\x90" * 5, "mov eax, 6"),
        (0x12, 2, b"\x90" * 2, "jmp 0x05"),           # back into the call
    ]
    from c2.binir import recover
    ops = recover(insns)
    epis = [o for o in ops if o.kind == "mid_func_epilogue"]
    assert len(epis) == 1
    assert epis[0].detail["framed"] is False
    assert "Frameless" in epis[0].note


def test_mid_func_epilogue_negative_no_call():
    """Back-jump past a ret but with NO call in the target region: a loop
    tail or other construct -- must NOT fire."""
    from c2.binir import recover
    insns = [
        (0x00, 2, b"\x90" * 2, "xor eax, eax"),
        (0x02, 3, b"\x90" * 3, "add eax, 1"),
        (0x05, 1, b"\x90" * 1, "ret"),
        (0x06, 5, b"\x90" * 5, "mov eax, 6"),
        (0x0b, 2, b"\x90" * 2, "jmp 0x02"),
    ]
    ops = recover(insns)
    assert not [o for o in ops if o.kind == "mid_func_epilogue"]


def test_mid_func_epilogue_negative_last_ret():
    """A normal function (ret last) must not fire."""
    from c2.binir import recover
    insns = [
        (0x00, 5, b"\x90" * 5, "call 0x100"),
        (0x05, 1, b"\x90" * 1, "pop ebx"),
        (0x06, 1, b"\x90" * 1, "ret"),
    ]
    ops = recover(insns)
    assert not [o for o in ops if o.kind == "mid_func_epilogue"]


def test_mid_func_epilogue_retval_form():
    """get_region_invasion_points shape: arms goto a shared `return 1`."""
    from c2.binir import recover
    insns = [
        (0x00, 3, b"\x90" * 3, "cmp eax, 1"),
        (0x03, 2, b"\x90" * 2, "jne 0x10"),
        (0x05, 5, b"\x90" * 5, "mov eax, 1"),     # shared return 1
        (0x0a, 1, b"\x90" * 1, "pop edi"),
        (0x0b, 1, b"\x90" * 1, "pop esi"),
        (0x0c, 1, b"\x90" * 1, "ret"),
        (0x10, 5, b"\x90" * 5, "mov edx, 2"),
        (0x15, 2, b"\x90" * 2, "jmp 0x05"),       # goto the return-1 tail
        (0x17, 2, b"\x90" * 2, "xor eax, eax"),
        (0x19, 1, b"\x90" * 1, "ret"),
    ]
    ops = recover(insns)
    epis = [o for o in ops if o.kind == "mid_func_epilogue"]
    assert len(epis) == 1
    assert epis[0].detail["shared"] == "retval"
    assert "goto fail" in epis[0].note
