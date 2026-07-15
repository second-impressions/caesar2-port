"""Synthetic tests for rule_hints — feed known PS-vs-recomp pairs."""
import sys
sys.path.insert(0, '.')

from c2.commands.rule_hints import (
    detect_rule_4, detect_rule_5, detect_rule_8, detect_rule_9,
    detect_rule_12, detect_rule_14, detect_rule_16, detect_rule_17,
    detect_rule_19, detect_rule_24a, detect_rule_24b, detect_rule_26,
    detect_rule_29, detect_rule_37, detect_rule_40, detect_rule_43,
    detect_rule_44, detect_rule_49, detect_rule_51, detect_rule_53,
    detect_rule_62, detect_rule_72, detect_rule_73,
    detect_byte_reg_swap, detect_reg_identity_swap, detect_add_vs_lea_copy,
    detect_rule_10, detect_rule_20, detect_rule_35, detect_rule_35a,
    detect_rule_49b, detect_rule_98, detect_rule_110,
)
from c2.commands.rule_hints import (
    _find_rule_10_excess, _find_rule_49b_pairs, _find_rule_35_pairs,
    _find_rule_81_swap, detect_rule_81,
    _find_rule_82_pattern, detect_rule_82,
    _find_rule_84_rows, detect_rule_84,
    detect_rule_100, detect_rule_90, _cmp_operand_width,
    detect_rule_4b,
)

def mk(rel_off, raw, asm):
    """Build an InsnT tuple."""
    return (rel_off, len(raw), bytes(raw), asm)

# ── Rule 4 — operand-order swap ──────────────────────────────────────────────
ps_cmp     = mk(0, [0x39, 0xd8],          "cmp eax, ebx")
ps_jmp     = mk(2, [0x7e, 0x05],          "jle 9")
recomp_cmp = mk(0, [0x39, 0xc3],          "cmp ebx, eax")
recomp_jmp = mk(2, [0x7d, 0x05],          "jge 9")
h = detect_rule_4(ps_jmp, recomp_jmp, ps_cmp, recomp_cmp)
assert h is not None and "Rule 4" in h.rule, f"Rule 4 missed: {h}"
print("✓ Rule 4 fires on cmp+jcc swap")

# ── Rule 4b — boundary inclusive/exclusive form (`> N` vs `>= N+1`) ──────────
# PS:  cmp ebx, 0x82 ; jl   (x >= 0x82)
# RC:  cmp ebx, 0x81 ; jle  (x >  0x81)
ps_b_cmp  = mk(0, [0x81, 0xfb, 0x82, 0, 0, 0], "cmp ebx, 0x82")
ps_b_jcc  = mk(6, [0x7c, 0x05],                "jl 0xd")
rc_b_cmp  = mk(0, [0x81, 0xfb, 0x81, 0, 0, 0], "cmp ebx, 0x81")
rc_b_jcc  = mk(6, [0x7e, 0x05],                "jle 0xd")
h = detect_rule_4b(ps_b_cmp, rc_b_cmp, ps_b_jcc, rc_b_jcc)
assert h is not None and h.rule == "Rule 4b", f"Rule 4b missed: {h}"
assert "0x82" in h.summary, f"Rule 4b summary wrong: {h.summary}"
print("✓ Rule 4b fires on off-by-one boundary + jl↔jle")

# Negative: same immediate (a genuine reg/encoding diff) must NOT fire.
assert detect_rule_4b(ps_b_cmp, ps_b_cmp, ps_b_jcc, ps_b_jcc) is None
# Negative: immediates differ by 2 (not a boundary form) must NOT fire.
rc_b_cmp2 = mk(0, [0x81, 0xfb, 0x80, 0, 0, 0], "cmp ebx, 0x80")
assert detect_rule_4b(ps_b_cmp, rc_b_cmp2, ps_b_jcc, rc_b_jcc) is None
# Negative: off-by-one but NOT an inclusive/exclusive Jcc complement
# (jl vs jg = direction flip, that's Rule 4) must NOT fire.
rc_b_jcc_dir = mk(6, [0x7f, 0x05], "jg 0xd")
assert detect_rule_4b(ps_b_cmp, rc_b_cmp, ps_b_jcc, rc_b_jcc_dir) is None
# Negative: different first operand (unrelated cmps) must NOT fire.
rc_b_cmp_op = mk(0, [0x83, 0xf8, 0x81], "cmp eax, 0x81")
assert detect_rule_4b(ps_b_cmp, rc_b_cmp_op, ps_b_jcc, rc_b_jcc) is None
print("✓ Rule 4b rejects same-imm / off-by-two / direction-flip / op-mismatch")

# ── Rule 8 — movsx vs mov+and 0xff ───────────────────────────────────────────
ps_movsx  = mk(0, [0x0f, 0xbe, 0x90, 0x10, 0x00, 0x00, 0x00],
                  "movsx edx, byte ptr [eax + 0x10]")
recomp_mov = mk(0, [0x8a, 0x90, 0x10, 0x00, 0x00, 0x00],
                  "mov dl, byte ptr [eax + 0x10]")
recomp_and = mk(6, [0x81, 0xe2, 0xff, 0x00, 0x00, 0x00],
                  "and edx, 0xff")
h = detect_rule_8(ps_movsx, recomp_mov, None, recomp_and)
assert h is not None and "Rule 8" in h.rule, f"Rule 8 missed: {h}"
print("✓ Rule 8 fires on movsx vs mov+and")

# ── Rule 12 — data-pointer literal vs integer ────────────────────────────────
ps_mov     = mk(0, [0xb8, 0x00, 0x00, 0x00, 0x00], "mov eax, 0")
recomp_mov = mk(0, [0xb8, 0x40, 0xa3, 0x01, 0x00], "mov eax, 0x1a340")
ps_fix     = {0x10001, 0x10002, 0x10003, 0x10004}  # all 4 imm bytes fixed
recomp_fix = set()
h = detect_rule_12(ps_mov, recomp_mov, 0x10000, 0x10000, ps_fix, recomp_fix)
assert h is not None and "Rule 12" in h.rule, f"Rule 12 missed: {h}"
print("✓ Rule 12 fires on fixup vs literal")

# ── Rule 14 — void return mismatch ───────────────────────────────────────────
ps_ret      = mk(0, [0xc3], "ret")
recomp_xor  = mk(0, [0x31, 0xc0], "xor eax, eax")
recomp_ret  = mk(2, [0xc3], "ret")
h = detect_rule_14(None, recomp_xor, None, recomp_ret)
assert h is not None and "Rule 14" in h.rule, f"Rule 14 missed (xor): {h}"
print("✓ Rule 14 fires on `xor eax, eax; ret`")

recomp_mov  = mk(0, [0xb8, 0x01, 0x00, 0x00, 0x00], "mov eax, 1")
h = detect_rule_14(None, recomp_mov, None, recomp_ret)
assert h is not None and "Rule 14" in h.rule, f"Rule 14 missed (mov): {h}"
print("✓ Rule 14 fires on `mov eax, IMM; ret`")

# ── Rule 16 — short-vs-near jmp ──────────────────────────────────────────────
ps_jmp_short = mk(0, [0xeb, 0x96], "jmp 0xffffff9d")
recomp_jmp_n = mk(0, [0xe9, 0x08], "<raw 2b>")    # truncated to 2 bytes
h = detect_rule_16(ps_jmp_short, recomp_jmp_n)
assert h is not None and "Rule 16" in h.rule, f"Rule 16 missed (short PS): {h}"
print("✓ Rule 16 fires on PS short / recomp near (truncated)")

ps_jmp_near = mk(0, [0xe9, 0x08, 0x00, 0x00, 0x00], "jmp 0xd")
recomp_jmp_s = mk(0, [0xeb, 0x08], "jmp 0xa")
h = detect_rule_16(ps_jmp_near, recomp_jmp_s)
assert h is not None and "Rule 16" in h.rule, f"Rule 16 missed (PS near): {h}"
print("✓ Rule 16 fires on PS near / recomp short")

# ── Rule 19 — char vs int spill ──────────────────────────────────────────────
ps_spill_dw = mk(0, [0x89, 0x14, 0x24], "mov dword ptr [esp], edx")
rc_spill_b  = mk(0, [0x88, 0x14, 0x24], "mov byte ptr [esp], dl")
h = detect_rule_19(ps_spill_dw, rc_spill_b)
assert h is not None and "Rule 19" in h.rule, f"Rule 19 missed: {h}"
print("✓ Rule 19 fires on dword vs byte spill")

# ── Rule 9 — `if (cond == 0)` else-first layout ─────────────────────────
ps_test    = mk(0, [0x85, 0xc0],         "test eax, eax")
ps_je      = mk(2, [0x74, 0x05],         "je 9")
recomp_jne = mk(2, [0x75, 0x05],         "jne 9")
h = detect_rule_9(ps_je, recomp_jne, ps_test, ps_test)
assert h is not None and "Rule 9" in h.rule, f"Rule 9 missed: {h}"
print("✓ Rule 9 fires on test+je vs test+jne")

# Rule 9 must NOT fire when preceded by `cmp` (that's Rule 4 territory)
ps_cmp     = mk(0, [0x39, 0xd8], "cmp eax, ebx")
h = detect_rule_9(ps_je, recomp_jne, ps_cmp, ps_cmp)
assert h is None, f"Rule 9 false positive on cmp: {h}"
print("✓ Rule 9 ignores cmp-preceded je/jne")

# Rule 9 must NOT fire when test args differ (e.g. `test eax, ebx`)
ps_test_xy = mk(0, [0x85, 0xd8], "test eax, ebx")
h = detect_rule_9(ps_je, recomp_jne, ps_test_xy, ps_test_xy)
assert h is None, f"Rule 9 false positive on cross-test: {h}"
print("✓ Rule 9 ignores cross-register test")

# Rule 9 must NOT fire when each side tests a different register
# (regalloc artifact, not a source-level inversion).
ps_test_eax = mk(0, [0x85, 0xc0], "test eax, eax")
rc_test_edi = mk(0, [0x85, 0xff], "test edi, edi")
h = detect_rule_9(ps_je, recomp_jne, ps_test_eax, rc_test_edi)
assert h is None, f"Rule 9 false positive on different test regs: {h}"
print("✓ Rule 9 ignores different test registers between sides")

# ── Rule 17 — flag-mask split-RMW ──────────────────────────────────────
ps_mov_dh_dl = mk(0, [0x88, 0xd6],       "mov dh, dl")
recomp_or_dl = mk(0, [0x80, 0xca, 0x01], "or dl, 0x1")
h = detect_rule_17(ps_mov_dh_dl, recomp_or_dl, None, None)
assert h is not None and "Rule 17" in h.rule, f"Rule 17 missed: {h}"
print("✓ Rule 17 fires on mov reg8,reg8 vs or reg8,IMM")

# Rule 17 must NOT fire on same-reg copy (impossible in real codegen)
ps_mov_dl_dl = mk(0, [0x88, 0xd2],       "mov dl, dl")
h = detect_rule_17(ps_mov_dl_dl, recomp_or_dl, None, None)
assert h is None, f"Rule 17 false positive on same-reg copy: {h}"
print("✓ Rule 17 ignores same-register mov")

# Rule 17 fires regardless of which reg recomp's `or` targets - Watcom's
# regalloc picks different physical regs for the split form vs the combined
# form, so requiring same-reg would miss real-world hits.
recomp_or_al = mk(0, [0x0c, 0x01],       "or al, 0x1")
h = detect_rule_17(ps_mov_dh_dl, recomp_or_al, None, None)
assert h is not None and "Rule 17" in h.rule, f"Rule 17 missed cross-reg: {h}"
print("✓ Rule 17 fires regardless of which reg recomp's OR targets")

# Rule 17 must NOT fire when recomp is something else entirely
recomp_mov_al = mk(0, [0xa0, 0x00, 0x00, 0x00, 0x00], "mov al, byte ptr [0]")
h = detect_rule_17(ps_mov_dh_dl, recomp_mov_al, None, None)
assert h is None, f"Rule 17 false positive on non-or recomp: {h}"
print("✓ Rule 17 ignores recomp rows that aren't `or reg8, IMM`")

# ── Rule 5 — signed div by power of 2 ──────────────────────────────
ps_sar_31  = mk(0, [0xc1, 0xfa, 0x1f],   "sar edx, 0x1f")
recomp_test = mk(0, [0x85, 0xc0],        "test eax, eax")
h = detect_rule_5(ps_sar_31, recomp_test)
assert h is not None and "Rule 5" in h.rule, f"Rule 5 missed (PS side): {h}"
assert "PS uses" in h.summary
print("✓ Rule 5 fires on PS sar reg, 31 vs recomp other")

# Reverse direction
h = detect_rule_5(recomp_test, ps_sar_31)
assert h is not None and "recomp uses" in h.summary
print("✓ Rule 5 fires on recomp sar reg, 31 vs PS other")

# Both sides have sar reg, 31 → no diff
h = detect_rule_5(ps_sar_31, ps_sar_31)
assert h is None, f"Rule 5 false positive when both have sar/31: {h}"
print("✓ Rule 5 ignores matched sar/31 on both sides")

# Neither side has sar reg, 31
h = detect_rule_5(recomp_test, recomp_test)
assert h is None, f"Rule 5 false positive when neither has sar/31: {h}"
print("✓ Rule 5 ignores matched non-sar/31 on both sides")

# `sar reg, 5` (different shift, not the idiom marker) → no fire
ps_sar_5 = mk(0, [0xc1, 0xfa, 0x05], "sar edx, 0x5")
h = detect_rule_5(ps_sar_5, recomp_test)
assert h is None, f"Rule 5 false positive on sar reg, 5: {h}"
print("✓ Rule 5 only fires on the literal `sar reg, 31` marker")

# ── Rule 24a — spill swap ────────────────────────────────────────────────────
# Mouserange: PS keeps ymin (edx) in edi & spills xmax (ebx) to stack;
# recomp does the opposite at the immediately following diff row.
ps_a   = mk(0x11, [0x89, 0xd7],             "mov edi, edx")
rc_a   = mk(0x11, [0x89, 0x54, 0x24, 0x1c], "mov dword ptr [esp + 0x1c], edx")
ps_b   = mk(0x13, [0x89, 0x5c, 0x24, 0x1c], "mov dword ptr [esp + 0x1c], ebx")
rc_b   = mk(0x13, [0x89, 0xdf],             "mov edi, ebx")
h = detect_rule_24a(ps_a, rc_a, ps_b, rc_b, None, None)
assert h is not None and "Rule 24a" in h.rule, f"Rule 24a missed (next): {h}"
print("✓ Rule 24a fires on spill swap (lookup via next row)")

# Same swap discovered from row B looking at prev:
h = detect_rule_24a(ps_b, rc_b, None, None, ps_a, rc_a)
assert h is not None and "Rule 24a" in h.rule, f"Rule 24a missed (prev): {h}"
print("✓ Rule 24a fires on spill swap (lookup via prev row)")

# Must NOT fire when both sides target the same kind of dest (no swap)
rc_a_reg = mk(0x11, [0x89, 0xd6], "mov esi, edx")
h = detect_rule_24a(ps_a, rc_a_reg, ps_b, rc_b, None, None)
assert h is None, f"Rule 24a false positive (both reg dst): {h}"
print("✓ Rule 24a ignores same-kind dest pair")

# Must NOT fire when source registers differ on current row (regalloc, not swap)
rc_a_other = mk(0x11, [0x89, 0x44, 0x24, 0x1c], "mov dword ptr [esp + 0x1c], eax")
h = detect_rule_24a(ps_a, rc_a_other, ps_b, rc_b, None, None)
assert h is None, f"Rule 24a false positive (src mismatch on cur): {h}"
print("✓ Rule 24a requires same source register on the swap row")

# Must NOT fire when paired row uses the SAME source register as current
ps_b_dup = mk(0x13, [0x89, 0x54, 0x24, 0x1c], "mov dword ptr [esp + 0x1c], edx")
rc_b_dup = mk(0x13, [0x89, 0xd7],             "mov edi, edx")
h = detect_rule_24a(ps_a, rc_a, ps_b_dup, rc_b_dup, None, None)
assert h is None, f"Rule 24a false positive (same src across rows): {h}"
print("✓ Rule 24a requires different source registers between paired rows")

# ── Rule 24b — shift-in-place vs shift-copy ─────────────────────────────────
# lock_region: PS shr eax, 0x10 vs recomp shr ebx, 0x10 (different rows)
ps_shr_eax = mk(0x16, [0xc1, 0xe8, 0x10], "shr eax, 0x10")
rc_movw    = mk(0x16, [0x66, 0x89, 0x5c, 0x24, 0x04],
                       "mov word ptr [esp + 4], bx")
ps_movw    = mk(0x10, [0x66, 0xc7, 0x04, 0x24, 0x00, 0x06],
                       "mov word ptr [esp], 0x600")
rc_shr_ebx = mk(0x10, [0xc1, 0xeb, 0x10], "shr ebx, 0x10")
h = detect_rule_24b(ps_shr_eax, rc_movw, None, None, ps_movw, rc_shr_ebx)
assert h is not None and "Rule 24b" in h.rule, f"Rule 24b missed (PS-side): {h}"
assert "shr eax" in h.summary and "shr ebx" in h.summary, h.summary
print("✓ Rule 24b fires when PS has shr eax, recomp shr ebx (prev row)")

# Symmetric: row where recomp has the shr, PS has it on adjacent row
h = detect_rule_24b(ps_movw, rc_shr_ebx, ps_shr_eax, rc_movw, None, None)
assert h is not None and "Rule 24b" in h.rule, f"Rule 24b missed (recomp-side): {h}"
print("✓ Rule 24b fires when recomp has shr ebx, PS shr eax (next row)")

# Must NOT fire when both sides shift the SAME register (matched, no diff cause)
ps_shr2 = mk(0x10, [0xc1, 0xe8, 0x10], "shr eax, 0x10")
rc_shr2 = mk(0x10, [0xc1, 0xe8, 0x10], "shr eax, 0x10")
h = detect_rule_24b(ps_shr2, rc_shr2, None, None, None, None)
assert h is None, f"Rule 24b false positive on matched shr: {h}"
print("✓ Rule 24b ignores matched-register shifts")

# Must NOT fire when shift counts differ (unrelated shifts)
ps_shr_8  = mk(0x10, [0xc1, 0xe8, 0x08], "shr eax, 0x8")
h = detect_rule_24b(ps_shr_8, rc_movw, None, None, ps_movw, rc_shr_ebx)
assert h is None, f"Rule 24b false positive on different shift counts: {h}"
print("✓ Rule 24b requires matching shift counts between sides")

# Must NOT fire when neither side has any shr in window
h = detect_rule_24b(ps_movw, rc_movw, None, None, None, None)
assert h is None, f"Rule 24b false positive (no shr anywhere): {h}"
print("✓ Rule 24b requires at least one shr in the diff window")

# ── Negative tests — must NOT fire ───────────────────────────────────────────
# Equal instructions
eq = mk(0, [0xb8, 0x00, 0x00, 0x00, 0x00], "mov eax, 0")
assert detect_rule_4(eq, eq, eq, eq) is None
assert detect_rule_5(eq, eq) is None
assert detect_rule_8(eq, eq, eq, eq) is None
assert detect_rule_9(eq, eq, eq, eq) is None
assert detect_rule_12(eq, eq, 0, 0, set(), set()) is None
assert detect_rule_14(eq, eq, eq, eq) is None
assert detect_rule_16(eq, eq) is None
assert detect_rule_17(eq, eq, eq, eq) is None
assert detect_rule_19(eq, eq) is None
assert detect_rule_24a(eq, eq, eq, eq, eq, eq) is None
assert detect_rule_24b(eq, eq, eq, eq, eq, eq) is None
print("✓ All detectors return None on equal pairs")

# Mismatched register destinations for Rule 12 (different reg = different B8+rd)
ps_mov_eax  = mk(0, [0xb8, 0x00, 0x00, 0x00, 0x00], "mov eax, 0")
rc_mov_ebx  = mk(0, [0xbb, 0x40, 0xa3, 0x01, 0x00], "mov ebx, 0x1a340")
assert detect_rule_12(ps_mov_eax, rc_mov_ebx, 0x10000, 0x10000,
                      {0x10001,0x10002,0x10003,0x10004}, set()) is None
print("✓ Rule 12 ignores different destination registers")

# Rule 8 negative — recomp uses movsx too (no mismatch)
recomp_movsx = mk(0, [0x0f, 0xbe, 0x90, 0x10, 0, 0, 0],
                  "movsx edx, byte ptr [eax + 0x10]")
assert detect_rule_8(ps_movsx, recomp_movsx, None, recomp_and) is None
print("✓ Rule 8 doesn't fire when recomp also uses movsx")

# ── Rule 26 — sete-fold of a boolean call argument ───────────────────────
recomp_sete = mk(0, [0x0f, 0x94, 0xc2], "sete dl")
recomp_setne = mk(0, [0x0f, 0x95, 0xc1], "setne cl")
recomp_setl = mk(0, [0x0f, 0x9c, 0xc0], "setl al")

# A. PS row absent (extra recomp row — typical case for explain_forum)
h = detect_rule_26(None, recomp_sete)
assert h is not None and "Rule 26" in h.rule, f"Rule 26 missed (PS=None): {h}"
assert "sete" in h.summary
print("✓ Rule 26 fires when PS row is None and recomp is sete")

# B. PS has a different mnemonic (e.g. mov reg, IMM from the explicit branch)
ps_mov_imm = mk(0, [0xba, 0x01, 0x00, 0x00, 0x00], "mov edx, 1")
h = detect_rule_26(ps_mov_imm, recomp_sete)
assert h is not None and "Rule 26" in h.rule, f"Rule 26 missed (PS=mov): {h}"
print("✓ Rule 26 fires when PS has explicit-branch mov vs recomp sete")

# C. setne also triggers
h = detect_rule_26(None, recomp_setne)
assert h is not None and "setne" in h.summary
print("✓ Rule 26 fires on setne")

# D. setl (any setcc) also triggers
h = detect_rule_26(None, recomp_setl)
assert h is not None and "setl" in h.summary
print("✓ Rule 26 fires on setl (any setcc family)")

# Rule 26 must NOT fire when recomp is not setcc
recomp_mov = mk(0, [0xb8, 0x00, 0x00, 0x00, 0x00], "mov eax, 0")
h = detect_rule_26(None, recomp_mov)
assert h is None, f"Rule 26 false positive on non-setcc recomp: {h}"
print("✓ Rule 26 ignores non-setcc recomp instructions")

# Rule 26 must NOT fire when both sides have the SAME setcc (matched, no diff)
h = detect_rule_26(recomp_sete, recomp_sete)
assert h is None, f"Rule 26 false positive on matched setcc: {h}"
print("✓ Rule 26 ignores matched setcc on both sides")

# Rule 26 STILL fires when PS is a different setcc family (rare but possible —
# means the source picked the wrong comparison direction, still a hint).
h = detect_rule_26(recomp_sete, recomp_setne)
assert h is not None and "setne" in h.summary, h
print("✓ Rule 26 fires when PS and recomp use different setcc families")

# Rule 26 must return None when recomp is None (no row to inspect)
assert detect_rule_26(recomp_sete, None) is None
print("✓ Rule 26 returns None when recomp is None")

# ── Rule 29 — DEC vs LEA for in-place decrement ──────────────────────────────
ps_dec   = mk(0, [0x49],                             "dec ecx")  # placeholder; cap will use 48..4F
ps_dec   = mk(0, [0x48],                             "dec eax")
ps_store = mk(1, [0xa3, 0x00, 0x10, 0x00, 0x00],     "mov [0x1000], eax")
rc_lea   = mk(0, [0x8d, 0x58, 0xff],                 "lea ebx, [eax - 1]")
rc_store = mk(3, [0x89, 0x1d, 0x00, 0x10, 0x00, 0x00], "mov [0x1000], ebx")
h = detect_rule_29(ps_dec, rc_lea, ps_store, rc_store)
assert h is not None and "Rule 29" in h.rule, f"Rule 29 missed: {h}"
print("✓ Rule 29 fires on dec vs lea+store")
# Mirror: recomp has dec, ps has lea
h = detect_rule_29(rc_lea, ps_dec, rc_store, ps_store)
assert h is not None and "Rule 29" in h.rule, f"Rule 29 mirror missed: {h}"
print("✓ Rule 29 fires mirrored")
# No fire when both sides are dec
assert detect_rule_29(ps_dec, ps_dec, ps_store, ps_store) is None
print("✓ Rule 29 ignores matched dec/dec")
# No fire when LEA isn't a -1 form
rc_lea2 = mk(0, [0x8d, 0x58, 0x05], "lea ebx, [eax + 5]")
assert detect_rule_29(ps_dec, rc_lea2, ps_store, rc_store) is None
print("✓ Rule 29 ignores non-(-1) LEA")

# ── Rule 37 — implicit-int return after a call ───────────────────────────────
prev_call  = mk(-5, [0xe8, 0x00, 0x00, 0x00, 0x00], "call 0x5")
ps_test_al = mk(0, [0x84, 0xc0],                    "test al, al")
rc_test_ea = mk(0, [0x85, 0xc0],                    "test eax, eax")
h = detect_rule_37(ps_test_al, rc_test_ea, prev_call, prev_call)
assert h is not None and "Rule 37" in h.rule, f"Rule 37 missed: {h}"
print("✓ Rule 37 fires on test al/al vs test eax/eax after call")
# Mirror
h = detect_rule_37(rc_test_ea, ps_test_al, prev_call, prev_call)
assert h is not None and "Rule 37" in h.rule
print("✓ Rule 37 fires mirrored")
# Must not fire without preceding call
assert detect_rule_37(ps_test_al, rc_test_ea, None, None) is None
print("✓ Rule 37 ignores when no preceding call")
# Must not fire on matched widths
assert detect_rule_37(ps_test_al, ps_test_al, prev_call, prev_call) is None
print("✓ Rule 37 ignores matched widths")
# Different register families don't fire
rc_test_eb = mk(0, [0x85, 0xdb], "test ebx, ebx")
assert detect_rule_37(ps_test_al, rc_test_eb, prev_call, prev_call) is None
print("✓ Rule 37 ignores different register families")

# ── Rule 40 — signed-char sentinel test ──────────────────────────────────────
ps_cmp_al  = mk(0, [0x3c, 0xff],                         "cmp al, 0xff")
rc_cmp_eax = mk(0, [0x83, 0xf8, 0xff],                   "cmp eax, -1")
h = detect_rule_40(ps_cmp_al, rc_cmp_eax, prev_call, prev_call)
assert h is not None and "Rule 40" in h.rule, f"Rule 40 missed: {h}"
print("✓ Rule 40 fires on cmp al,0xff vs cmp eax,-1")
# Mirror
h = detect_rule_40(rc_cmp_eax, ps_cmp_al, prev_call, prev_call)
assert h is not None and "Rule 40" in h.rule
print("✓ Rule 40 fires mirrored")
# Not without call
assert detect_rule_40(ps_cmp_al, rc_cmp_eax, None, None) is None
print("✓ Rule 40 ignores when no preceding call")

# ── Rule 43 — __CHK prologue ─────────────────────────────────────────────────
ps_push_imm  = mk(0, [0x68, 0x10, 0x00, 0x00, 0x00],  "push 0x10")
ps_call_chk  = mk(5, [0xe8, 0x00, 0x00, 0x00, 0x00],  "call __CHK")
rc_push_reg  = mk(0, [0x53],                          "push ebx")
rc_next      = mk(1, [0x56],                          "push esi")
h = detect_rule_43(ps_push_imm, rc_push_reg, ps_call_chk, rc_next, None, None)
assert h is not None and "Rule 43" in h.rule, f"Rule 43 missed: {h}"
print("✓ Rule 43 fires on push imm32+call vs push reg")
# Mirror
h = detect_rule_43(rc_push_reg, ps_push_imm, rc_next, ps_call_chk, None, None)
assert h is not None and "Rule 43" in h.rule
print("✓ Rule 43 fires mirrored")
# Must not fire when next isn't a call
assert detect_rule_43(ps_push_imm, rc_push_reg, rc_next, rc_next, None, None) is None
print("✓ Rule 43 requires next insn = call on CHK side")

# ── Rule 44 — spurious `and eax, 0xff` after byte AND ────────────────────────
from c2.commands.rule_hints import _find_rule_44_excess
prev_and_al = mk(-3, [0x24, 0xe7],                    "and al, 0xe7")
rc_and_zext = mk(0, [0x25, 0xff, 0x00, 0x00, 0x00],   "and eax, 0xff")
next_je     = mk(5, [0x74, 0x05],                     "je 0xc")
# Build a row list where RC has 1 excess `and eax, 0xff`.
rows_excess = [
    (None, prev_and_al, True),     # dummy preceding row
    (None, rc_and_zext, True),     # the spurious zext row
    (None, next_je,     True),     # following Jcc
]
excess_map = _find_rule_44_excess(rows_excess)
assert excess_map == {1: "recomp"}, f"excess detection wrong: {excess_map}"
h = detect_rule_44(1, None, rc_and_zext, excess_map,
                   None, prev_and_al, None, next_je)
assert h is not None and "Rule 44" in h.rule, f"Rule 44 missed: {h}"
print("✓ Rule 44 fires on RC excess `and eax, 0xff` (function-level count)")

# ── Rule 106 — callee `unsigned short` param truncates the caller's arg ─────
from c2.commands.rule_hints import _find_rule_106_excess, detect_rule_106
# PS truncates an int-valued arg to 16-bit before a call; recomp omits it.
ps_add      = mk(0, [0x05, 0xfd, 0x00, 0x00, 0x00], "add eax, 0xfd")
ps_and_ffff = mk(5, [0x25, 0xff, 0xff, 0x00, 0x00], "and eax, 0xffff")
ps_call     = mk(10, [0xe8, 0x00, 0x00, 0x00, 0x00], "call 0x1234")
rows_106 = [
    (ps_add,      None, True),    # PS-only arith
    (ps_and_ffff, None, True),    # PS-only 16-bit truncation
    (ps_call,     None, True),    # the call it precedes
]
ex106 = _find_rule_106_excess(rows_106)
assert ex106 == {1: "PS"}, f"Rule 106 excess detection wrong: {ex106}"
h = detect_rule_106(1, ps_and_ffff, None, ex106)
assert h is not None and "Rule 106" in h.rule, f"Rule 106 missed: {h}"
assert "unsigned short" in h.fix
print("✓ Rule 106 fires on PS-only `and eax, 0xffff` before a call")

# Suppressed when NOT before a call (a generic `& 0xffff`, not a param mask).
rows_106_nocall = [
    (ps_add,      None, True),
    (ps_and_ffff, None, True),
    (mk(10, [0x89, 0xc3], "mov ebx, eax"), None, True),
]
assert _find_rule_106_excess(rows_106_nocall) == {}, \
    "Rule 106 must require a following call"
print("✓ Rule 106 suppressed when no call follows")

# Suppressed when both sides have a matching `and reg, 0xffff` (shift, not bug).
rows_106_bal = [
    (ps_and_ffff, ps_and_ffff, True),
    (ps_call,     ps_call,     True),
]
assert _find_rule_106_excess(rows_106_bal) == {}, \
    "Rule 106 must suppress a balanced pair"
print("✓ Rule 106 suppresses a balanced (PS==RC) pair")

# Must not fire when PS and RC have matched counts (layout-shift artefact).
rows_matched = [
    (rc_and_zext, None,         True),   # PS-only zext (delete)
    (None,        rc_and_zext, True),   # RC-only zext (insert)
]
excess_map = _find_rule_44_excess(rows_matched)
assert excess_map == {}, f"matched should yield empty: {excess_map}"
h = detect_rule_44(0, rc_and_zext, None, excess_map,
                   None, None, None, None)
assert h is None, f"Rule 44 false-positive on matched counts: {h}"
print("✓ Rule 44 suppresses matched PS/RC count (layout shift)")

# Must not fire when next isn't a Jcc reading ZF
rc_next_mov = mk(5, [0x89, 0xc3], "mov ebx, eax")
h = detect_rule_44(1, None, rc_and_zext, {1: "recomp"},
                   None, prev_and_al, None, rc_next_mov)
assert h is None
print("✓ Rule 44 requires next je/jne")

# ── Rule 49 — `& 0xff` vs `(unsigned char)` zext idiom ───────────────────────
ps_mov_dl   = mk(0, [0x8a, 0x15, 0x00, 0x10, 0x00, 0x00], "mov dl, byte ptr [0x1000]")
ps_and_edx  = mk(6, [0x81, 0xe2, 0xff, 0x00, 0x00, 0x00], "and edx, 0xff")
rc_xor_edx  = mk(0, [0x31, 0xd2],                          "xor edx, edx")
rc_mov_dl   = mk(2, [0x8a, 0x15, 0x00, 0x10, 0x00, 0x00], "mov dl, byte ptr [0x1000]")
# Row 1 of the diff: PS=mov dl, RC=xor edx (different insns at same offset)
h = detect_rule_49(ps_mov_dl, rc_xor_edx, ps_and_edx, rc_mov_dl, None, None)
assert h is not None and "Rule 49" in h.rule, f"Rule 49 missed: {h}"
print("✓ Rule 49 fires on `mov rl; and reg, 0xff` vs `xor; mov rl`")
# Mirror (RC has PS's load-then-mask form, PS has xor-then-load)
h = detect_rule_49(rc_xor_edx, ps_mov_dl, rc_mov_dl, ps_and_edx, None, None)
assert h is not None and "Rule 49" in h.rule
print("✓ Rule 49 fires mirrored")

# ── Rule 51 — EAX-shortcut absolute load vs generic byte load ────────────────
ps_mov_eax = mk(0, [0xa1, 0x00, 0x10, 0x00, 0x00],     "mov eax, [0x1000]")
rc_mov_bl  = mk(0, [0x8a, 0x1d, 0x00, 0x10, 0x00, 0x00], "mov bl, byte ptr [0x1000]")
h = detect_rule_51(ps_mov_eax, rc_mov_bl)
assert h is not None and "Rule 51" in h.rule, f"Rule 51 missed: {h}"
print("✓ Rule 51 fires on PS a1 (mov eax,[m]) vs RC 8a (mov bl,[m])")
# Mirror
h = detect_rule_51(rc_mov_bl, ps_mov_eax)
assert h is not None and "Rule 51" in h.rule
print("✓ Rule 51 fires mirrored")
# Must not fire on matched encodings
assert detect_rule_51(ps_mov_eax, ps_mov_eax) is None
print("✓ Rule 51 ignores matched encodings")

# ── Rule 53 — `setne; movzx` boolean materialisation ─────────────────────────
ps_setne  = mk(0, [0x0f, 0x95, 0xc0], "setne al")
rc_other  = mk(0, [0x89, 0xd6],        "mov esi, edx")
h = detect_rule_53(ps_setne, rc_other)
assert h is not None and "Rule 53" in h.rule, f"Rule 53 missed: {h}"
print("✓ Rule 53 fires on PS setne vs RC non-setcc")
# Mirror
h = detect_rule_53(rc_other, ps_setne)
assert h is not None and "Rule 53" in h.rule
print("✓ Rule 53 fires mirrored")
# Must not fire when both setne (matched)
assert detect_rule_53(ps_setne, ps_setne) is None
print("✓ Rule 53 ignores matched setcc")

# ── Rule 62 — `lea reg, [src+src]` vs `mov + add reg, reg` ───────────────────
ps_mov  = mk(0, [0x89, 0xd8], "mov eax, ebx")
ps_add  = mk(2, [0x01, 0xc0], "add eax, eax")
rc_lea  = mk(0, [0x8d, 0x04, 0x1b], "lea eax, [ebx + ebx]")
# Diff appears at the add row (PS has add, RC has lea or next instr)
h = detect_rule_62(ps_add, rc_lea, None, None, ps_mov, None)
assert h is not None and "Rule 62" in h.rule, f"Rule 62 missed: {h}"
print("✓ Rule 62 fires on PS `add reg, reg` vs RC `lea reg, [src+src]`")
# Mirror
h = detect_rule_62(rc_lea, ps_add, None, None, None, ps_mov)
assert h is not None and "Rule 62" in h.rule
print("✓ Rule 62 fires mirrored")
# Must not fire when both sides are LEA
assert detect_rule_62(rc_lea, rc_lea, None, None, None, None) is None
print("✓ Rule 62 ignores matched lea")

# ── Rule 10 — staged global RMW vs fused store ────────────────────────────
# PS has 3 staged `add [global], reg` writes; RC has none.
ps_add1 = mk(0, [0x01, 0x05, 0x00, 0x10, 0x00, 0x00], "add [0x1000], eax")
ps_add2 = mk(6, [0x01, 0x1d, 0x00, 0x10, 0x00, 0x00], "add [0x1000], ebx")
ps_add3 = mk(12,[0x01, 0x0d, 0x00, 0x10, 0x00, 0x00], "add [0x1000], ecx")
rc_mov  = mk(0, [0xa3, 0x00, 0x10, 0x00, 0x00],        "mov [0x1000], eax")
rows10 = [
    (ps_add1, None,   True),   # PS-only add
    (ps_add2, None,   True),   # PS-only add
    (ps_add3, rc_mov, True),   # mismatched (mov on RC)
]
ex10 = _find_rule_10_excess(rows10)
assert set(ex10.keys()) == {0, 1, 2} and all(v=="PS" for v in ex10.values()), ex10
print("✓ Rule 10 excess detection: 3 PS-side staged writes flagged")
h = detect_rule_10(0, ps_add1, None, ex10)
assert h is not None and "Rule 10" in h.rule, f"Rule 10 missed: {h}"
print("✓ Rule 10 fires on PS-side staged add [m], reg")
# Matched counts → no excess (suppression).
rows10b = [(ps_add1, ps_add2, True), (ps_add2, ps_add1, True)]
assert _find_rule_10_excess(rows10b) == {}
print("✓ Rule 10 suppresses matched per-memory counts")
# Single PS write (only 1) → no excess (needs 2+ on one side).
rows10c = [(ps_add1, None, True)]
assert _find_rule_10_excess(rows10c) == {}
print("✓ Rule 10 requires 2+ writes on the excess side")

# ── Rule 35a — `+` vs `|` combine ────────────────────────────────────────
ps_add_eax = mk(0, [0x01, 0xd0], "add eax, edx")
rc_or_eax  = mk(0, [0x09, 0xd0], "or eax, edx")
h = detect_rule_35a(ps_add_eax, rc_or_eax)
assert h is not None and "Rule 35a" in h.rule, f"Rule 35a missed: {h}"
print("✓ Rule 35a fires on PS `add` vs RC `or` with matching operands")
h = detect_rule_35a(rc_or_eax, ps_add_eax)
assert h is not None and "Rule 35a" in h.rule
print("✓ Rule 35a fires mirrored")
# Must not fire when operands differ.
rc_or_ebx = mk(0, [0x09, 0xc3], "or ebx, eax")
assert detect_rule_35a(ps_add_eax, rc_or_ebx) is None
print("✓ Rule 35a requires matching operand pair")
# Must not fire on matched mnemonics.
assert detect_rule_35a(ps_add_eax, ps_add_eax) is None
print("✓ Rule 35a ignores matched add/add")

# ── Rule 49b — asymmetric xor+mov.lo zext pair ─────────────────────────────
rc_xor_eax = mk(0, [0x31, 0xc0],          "xor eax, eax")
rc_mov_al  = mk(2, [0x8a, 0x44, 0x24, 4], "mov al, byte ptr [esp + 4]")
rows49b = [
    (None, rc_xor_eax, True),   # RC-only insertion (xor)
    (None, rc_mov_al,  True),   # RC-only insertion (mov al, [m])
]
p49b = _find_rule_49b_pairs(rows49b)
assert p49b == {0: "recomp"}, f"49b pair detection: {p49b}"
print("✓ Rule 49b detects RC-only `xor eax,eax; mov al,[m]` insertion pair")
h = detect_rule_49b(0, None, rc_xor_eax, p49b)
assert h is not None and "Rule 49b" in h.rule, f"Rule 49b missed: {h}"
print("✓ Rule 49b fires on the xor row of the pair")
# Mirror: PS-only deletion pair.
rows49b_m = [
    (rc_xor_eax, None, True),
    (rc_mov_al,  None, True),
]
assert _find_rule_49b_pairs(rows49b_m) == {0: "PS"}
print("✓ Rule 49b fires mirrored (PS-only deletion pair)")
# Must not fire when both sides have the rows (it's a replace).
rows49b_rep = [
    (rc_xor_eax, rc_xor_eax, True),
    (rc_mov_al,  rc_mov_al,  True),
]
assert _find_rule_49b_pairs(rows49b_rep) == {}
print("✓ Rule 49b ignores matched replace pairs")
# Must not fire when reg families mismatch (xor eax / mov dl).
rc_mov_dl = mk(2, [0x8a, 0x14, 0x24], "mov dl, byte ptr [esp]")
rows49b_mm = [
    (None, rc_xor_eax, True),
    (None, rc_mov_dl,  True),
]
assert _find_rule_49b_pairs(rows49b_mm) == {}
print("✓ Rule 49b requires reg family match between xor and mov.lo")

# ── Rule 84 — split-alignment byte-temp cascade ───────────────────────────
# Canonical 3-row alignment from putting_out_fire:
#   row i:    RC-only insert  `xor edx, edx`
#   row i+1:  EQUAL           `mov dl, byte ptr [m]`  (both sides byte-identical)
#   row i+k:  PS-only delete  `and edx, 0xff`
rc_xor_edx = mk(0, [0x31, 0xd2],                          "xor edx, edx")
ps_mov_dl  = mk(0, [0x8a, 0x90, 0x00, 0x10, 0x00, 0x00],  "mov dl, byte ptr [eax + 0x1000]")
rc_mov_dl  = mk(0, [0x8a, 0x90, 0x00, 0x10, 0x00, 0x00],  "mov dl, byte ptr [eax + 0x1000]")
ps_and_edx = mk(0, [0x81, 0xe2, 0xff, 0x00, 0x00, 0x00],  "and edx, 0xff")
rows84 = [
    (None,       rc_xor_edx, True),   # 0: RC-only xor insert
    (ps_mov_dl,  rc_mov_dl,  False),  # 1: equal mov dl, [m]
    (ps_and_edx, None,       True),   # 2: PS-only and delete
]
p84 = _find_rule_84_rows(rows84)
assert p84 == {0: "recomp", 2: "PS"}, f"Rule 84 candidates: {p84}"
print("✓ Rule 84 detects split-alignment xor-insert / mov-equal / and-delete triple")
h = detect_rule_84(0, None, rc_xor_edx, p84)
assert h is not None and "Rule 84" in h.rule
print("✓ Rule 84 fires on the xor-insert row")
h = detect_rule_84(2, ps_and_edx, None, p84)
assert h is not None and "Rule 84" in h.rule
print("✓ Rule 84 fires on the and-delete row")

# Must NOT fire when the equal mov is not adjacent (branch separates the
# cascade halves — false-positive case from get_best_elastic_value).
ps_test_al = mk(0, [0x84, 0xc0],                          "test al, al")
rc_test_eax = mk(0, [0x85, 0xc0],                         "test eax, eax")
ps_je      = mk(0, [0x74, 0x05],                          "je 0x10")
rc_je      = mk(0, [0x74, 0x05],                          "je 0x10")
rows84_branch = [
    (None,       rc_xor_edx, True),   # 0: RC xor insert
    (ps_mov_dl,  rc_mov_dl,  False),  # 1: equal mov
    (ps_test_al, rc_test_eax, True),  # 2: replace test (branch break)
    (ps_je,      rc_je,      False),  # 3: equal jcc
    (ps_and_edx, None,       True),   # 4: PS and delete — NOT adjacent to mov
]
p84b = _find_rule_84_rows(rows84_branch)
# The xor at row 0 is adjacent to the equal mov at row 1 (candidate).
# But the and at row 4 is NOT adjacent to the equal mov at row 1, so no
# PS-side and is collected; without a matching pair, Rule 84 is
# suppressed entirely (forward direction needs both halves).
assert p84b == {}, f"Rule 84 should not fire for branch-separated cascade: {p84b}"
print("✓ Rule 84 suppressed when `and` is separated from the equal `mov` by a test/jcc")

# Must NOT fire for single-instance Rule 49 alignment (xor and mov.lo at
# the same row alignment as a `replace` pair — that's Rule 49, not 84).
rows84_replace = [
    (ps_mov_dl, rc_xor_edx, True),   # 0: replace (PS=mov, RC=xor) — Rule 49 territory
    (ps_and_edx, rc_mov_dl, True),   # 1: replace (PS=and, RC=mov)
]
p84c = _find_rule_84_rows(rows84_replace)
assert p84c == {}, f"Rule 84 should not fire on Rule 49 replace pairs: {p84c}"
print("✓ Rule 84 suppressed for Rule 49 replace-pair alignment")

# ── Rule 20 — scaled-vs-absolute index ─────────────────────────────────────
ps_scaled_load = mk(0, [0x8a, 0x18], "mov bl, byte ptr [eax*4 + 0x4d3c]")
rc_abs_load    = mk(0, [0x8a, 0x1d], "mov bl, byte ptr [0x23b24]")
h = detect_rule_20(ps_scaled_load, rc_abs_load)
assert h is not None and "Rule 20" in h.rule, f"Rule 20 missed: {h}"
print("✓ Rule 20 fires on PS `[reg*K + disp]` vs RC `[abs_disp]`")
h = detect_rule_20(rc_abs_load, ps_scaled_load)
assert h is not None and "Rule 20" in h.rule
print("✓ Rule 20 fires mirrored")
# Must not fire when mnemonics differ.
ps_jmp = mk(0, [0xeb, 0x10], "jmp 0x18")
assert detect_rule_20(ps_jmp, rc_abs_load) is None
print("✓ Rule 20 requires matching mnemonic")
# Must not fire on matched scaled / scaled.
assert detect_rule_20(ps_scaled_load, ps_scaled_load) is None
print("✓ Rule 20 ignores matched scaled")
# Must not fire when neither side is scaled.
ps_reg_load = mk(0, [0x8a, 0x18], "mov bl, byte ptr [eax + 0x10]")
assert detect_rule_20(ps_reg_load, rc_abs_load) is None
print("✓ Rule 20 requires one side scaled and other absolute")

# ── Rule 35 — LE byte-load reorder copy-then-clear pair ────────────────────
rc_mov_edi_edx = mk(0, [0x89, 0xd7], "mov edi, edx")
rc_xor_edx     = mk(2, [0x31, 0xd2], "xor edx, edx")
rows35 = [
    (None, rc_mov_edi_edx, True),
    (None, rc_xor_edx,     True),
]
p35 = _find_rule_35_pairs(rows35)
assert p35 == {0: "recomp"}, f"Rule 35 pair detection: {p35}"
print("✓ Rule 35 detects RC-only mov+xor reorder pair")
h = detect_rule_35(0, None, rc_mov_edi_edx, p35)
assert h is not None and "Rule 35" in h.rule, f"Rule 35 missed: {h}"
print("✓ Rule 35 fires on the mov row of the pair")
# Must not fire when registers don't form the copy-then-clear chain.
rc_xor_ebx = mk(2, [0x31, 0xdb], "xor ebx, ebx")
rows35_mm = [
    (None, rc_mov_edi_edx, True),
    (None, rc_xor_ebx,     True),
]
assert _find_rule_35_pairs(rows35_mm) == {}
print("✓ Rule 35 requires xor's reg to match mov's src")
# Must not fire when dst == src in the mov.
rc_mov_edx_edx = mk(0, [0x89, 0xd2], "mov edx, edx")
rows35_id = [
    (None, rc_mov_edx_edx, True),
    (None, rc_xor_edx,     True),
]
assert _find_rule_35_pairs(rows35_id) == {}
print("✓ Rule 35 requires mov dst != src")

# ── Rule 72 — prefix-inc/dec field vs cached temp RMW ────────────────────
ps_inc  = mk(0x10, [0xfe, 0x05, 0x56, 0x34, 0x12, 0x00],
                    "inc byte ptr [0x123456]")
rc_load = mk(0x10, [0xa0, 0x56, 0x34, 0x12, 0x00],
                    "mov al, byte ptr [0x123456]")
rc_inc  = mk(0x15, [0xfe, 0xc0], "inc al")
h = detect_rule_72(ps_inc, rc_load, None, rc_inc)
assert h is not None and "Rule 72" in h.rule, f"Rule 72 missed: {h}"
print("✓ Rule 72 fires on PS `inc [m]` vs RC `mov reg,[m]` cache load")

# Symmetric: PS cached, RC in-place.
h = detect_rule_72(rc_load, ps_inc, rc_inc, None)
assert h is not None and "Rule 72" in h.rule, f"Rule 72 symmetric missed: {h}"
print("✓ Rule 72 fires symmetrically")

# Must not fire when both sides agree.
h = detect_rule_72(ps_inc, ps_inc, None, None)
assert h is None, f"Rule 72 false positive on matching sides: {h}"
print("✓ Rule 72 doesn't fire on equal rows")

# Must not fire for postfix-style mov-with-reg-dst where the mov stores
# (`mov [m], reg`) instead of loading.
rc_store = mk(0x10, [0xa2, 0x56, 0x34, 0x12, 0x00],
                    "mov byte ptr [0x123456], al")
h = detect_rule_72(ps_inc, rc_store, None, rc_inc)
assert h is None, f"Rule 72 should not fire on mov-store: {h}"
print("✓ Rule 72 distinguishes load from store on the mov side")

# ── Rule 73 — cached pointer vs folded disp32 ──────────────────────────
ps_folded  = mk(0x20, [0x83, 0xba, 0xa4, 0x2f, 0x07, 0x00, 0x00],
                       "cmp dword ptr [edx + 0x72fa4], 0")
rc_cached  = mk(0x20, [0x83, 0x7a, 0x08, 0x00],
                       "cmp dword ptr [edx + 8], 0")
abs_ps, abs_rc = 0x100000, 0x200000
# Mark the last 4 bytes of PS's encoding as fixup-bound (the disp32).
ps_fix_r73 = {abs_ps + 0x20 + 3 + i for i in range(4)}
rc_fix_r73 = set()
h = detect_rule_73(ps_folded, rc_cached, abs_ps, abs_rc, ps_fix_r73, rc_fix_r73)
assert h is not None and "Rule 73" in h.rule, f"Rule 73 missed: {h}"
print("✓ Rule 73 fires on PS-folded vs RC-cached pointer")

# Must not fire when both sides are folded (both have fixups).
rc_folded = mk(0x20, [0x83, 0xba, 0xa4, 0x2f, 0x07, 0x00, 0x00],
                      "cmp dword ptr [edx + 0x72fa4], 0")
rc_fix2 = {abs_rc + 0x20 + 3 + i for i in range(4)}
h = detect_rule_73(ps_folded, rc_folded, abs_ps, abs_rc, ps_fix_r73, rc_fix2)
assert h is None, f"Rule 73 false positive when both folded: {h}"
print("✓ Rule 73 doesn't fire when both sides fold")

# Must not fire when the cached side's offset is itself large (> 0x100).
rc_huge = mk(0x20, [0x83, 0xba, 0x00, 0x10, 0x00, 0x00, 0x00],
                    "cmp dword ptr [edx + 0x1000], 0")
h = detect_rule_73(ps_folded, rc_huge, abs_ps, abs_rc, ps_fix_r73, set())
assert h is None, f"Rule 73 should not fire on huge cached offset: {h}"
print("✓ Rule 73 ignores huge offsets on the non-folded side")

# ── Byte-register identity swap ─────────────────────────────────────
ps_mov_bh = mk(0, [0x88, 0xb8, 0xf7, 0x37, 0x04, 0x00],
                    "mov byte ptr [eax + 0x437f7], bh")
rc_mov_dh = mk(0, [0x88, 0xb0, 0xf7, 0x37, 0x04, 0x00],
                    "mov byte ptr [eax + 0x437f7], dh")
h = detect_byte_reg_swap(ps_mov_bh, rc_mov_dh)
assert h is not None and "Byte-reg swap" in h.rule, f"byte-reg swap missed: {h}"
print("✓ Byte-reg swap fires on mov [m], bh vs mov [m], dh")

# Self-zero xor variant.
ps_xor_bh = mk(0, [0x30, 0xff], "xor bh, bh")
rc_xor_dh = mk(0, [0x30, 0xf6], "xor dh, dh")
h = detect_byte_reg_swap(ps_xor_bh, rc_xor_dh)
assert h is not None and "Byte-reg swap" in h.rule, f"xor variant missed: {h}"
print("✓ Byte-reg swap fires on xor bh,bh vs xor dh,dh")

# Must not fire when memory operand differs.
rc_mov_other = mk(0, [0x88, 0xb0, 0xf8, 0x37, 0x04, 0x00],
                      "mov byte ptr [eax + 0x437f8], dh")
h = detect_byte_reg_swap(ps_mov_bh, rc_mov_other)
assert h is None, f"byte-reg swap false positive on different mem: {h}"
print("✓ Byte-reg swap doesn't fire when memory operand differs")

# Must not fire when both sides use the same register.
h = detect_byte_reg_swap(ps_mov_bh, ps_mov_bh)
assert h is None, f"byte-reg swap false positive on identical: {h}"
print("✓ Byte-reg swap doesn't fire on identical rows")

# Must not fire for 32-bit register swap (that's Rule 28).
ps_mov_esi = mk(0, [0x89, 0xf0], "mov eax, esi")
rc_mov_edi = mk(0, [0x89, 0xf8], "mov eax, edi")
h = detect_byte_reg_swap(ps_mov_esi, rc_mov_edi)
assert h is None, f"byte-reg swap false positive on 32-bit regs: {h}"
print("✓ Byte-reg swap doesn't fire on 32-bit register differences")

# ── General register identity swap ─────────────────────────────────
h = detect_reg_identity_swap(ps_mov_esi, rc_mov_edi)
assert h is not None and "Reg swap" in h.rule, f"reg swap missed: {h}"
print("✓ Reg swap fires on 32-bit register differences")

ps_idx = mk(0, [0x8b, 0x84, 0x9a, 0x84, 0x3d, 0x07, 0x00],
            "mov eax, dword ptr [edx + ebx*4 + 0x73d84]")
rc_idx = mk(0, [0x8b, 0x84, 0x93, 0x2a, 0xf8, 0x02, 0x00],
            "mov eax, dword ptr [ebx + edx*4 + 0x2f82a]")
ps_fix_idx = {0x100000 + 3 + i for i in range(4)}
rc_fix_idx = {0x200000 + 3 + i for i in range(4)}
h = detect_reg_identity_swap(ps_idx, rc_idx, 0x100000, 0x200000, ps_fix_idx, rc_fix_idx)
assert h is not None and "Reg swap" in h.rule, f"reg swap indexed missed: {h}"
print("✓ Reg swap tolerates fixup-masked indexed address differences")

h = detect_reg_identity_swap(ps_mov_bh, rc_mov_dh)
assert h is None, f"Reg swap should defer byte-only rows to Byte-reg swap: {h}"
print("✓ Reg swap defers byte-only rows to Byte-reg swap")

# ── Add in-place vs LEA copy before use ─────────────────────────────
ps_add = mk(0, [0x83, 0xc6, 0x70], "add esi, 0x70")
rc_lea = mk(0, [0x8d, 0x46, 0x70], "lea eax, [esi + 0x70]")
ps_push = mk(3, [0x56], "push esi")
rc_push = mk(3, [0x50], "push eax")
h = detect_add_vs_lea_copy(ps_add, rc_lea, ps_push, rc_push)
assert h is not None and "Add/LEA copy" in h.rule, f"Add/LEA detector missed: {h}"
print("✓ Add/LEA copy fires on add esi vs lea eax,[esi+imm] before push")

h = detect_add_vs_lea_copy(ps_add, rc_lea, None, None)
assert h is not None and "Add/LEA copy" in h.rule, f"Add/LEA detector missed without next rows: {h}"
print("✓ Add/LEA copy fires without next-row confirmation")

# ── Rule 98 — register-arg value born in arg reg vs computed-then-lea ──
# PS computes the value directly in the arg register (ECX = font_list arg4);
# recomp computes in EAX (accumulator) and lea's it into ECX.
r98_ps  = mk(0, [0x83, 0xc1, 0x20], "add ecx, 0x20")
r98_rc  = mk(0, [0x8d, 0x48, 0x20], "lea ecx, [eax + 0x20]")
h = detect_rule_98(r98_ps, r98_rc)
assert h is not None and h.rule == "Rule 98", f"Rule 98 detector missed: {h}"
print("✓ Rule 98 fires on add ecx vs lea ecx,[eax+imm]")

# Must NOT fire on the in-place adjust (lea_src == add_reg) — that's Add/LEA.
assert detect_rule_98(ps_add, rc_lea) is None, "Rule 98 must not claim in-place adjust"
print("✓ Rule 98 defers in-place pointer adjust to Add/LEA copy")

# Must NOT fire when the result register is a callee-save (not an arg reg).
r98_ns_ps = mk(0, [0x83, 0xc6, 0x20], "add esi, 0x20")
r98_ns_rc = mk(0, [0x8d, 0x70, 0x20], "lea esi, [eax + 0x20]")
assert detect_rule_98(r98_ns_ps, r98_ns_rc) is None, "Rule 98 must require an arg register"
print("✓ Rule 98 requires a __watcall arg register as the result")

# Conversely, detect_add_vs_lea_copy must NOT claim the Rule 98 shape.
assert detect_add_vs_lea_copy(r98_ps, r98_rc, None, None) is None, \
    "Add/LEA copy must not claim the src!=dst Rule 98 shape"
print("✓ Add/LEA copy defers src!=dst shape to Rule 98")

# ── Rule 78 — pointer-save-before-deref 5-insn copy ────────────────
from c2.commands.rule_hints import _find_rule_78_copies, detect_rule_78

# PS-side 5 insns of the byte-copy pattern (mirrors font_no L2163+).
r78_ps = [
    mk(0x43, [0x89, 0xc2],          "mov edx, eax"),
    mk(0x45, [0x40],                "inc eax"),
    mk(0x46, [0x8d, 0x2c, 0x1f],    "lea ebp, [edi + ebx]"),
    mk(0x49, [0x8a, 0x12],          "mov dl, byte ptr [edx]"),
    mk(0x4b, [0x88, 0x55, 0x00],    "mov byte ptr [ebp], dl"),
]

# Recomp compact form (3 insns matching just the load/store + inc).
r78_rc = [
    mk(0x3c, [0x8a, 0x28],                          "mov ch, byte ptr [eax]"),
    None,                                            # one of the 5 missing
    mk(0x3e, [0x88, 0x2c, 0x1a],                    "mov byte ptr [edx + ebx], ch"),
    mk(0x41, [0x40],                                "inc eax"),
    None,
]

# Build rows: PS-side has full 5-insn pattern, recomp has different/missing.
r78_rows = [
    (r78_ps[k], r78_rc[k], True)  # all diff rows
    for k in range(5)
]
hits = _find_rule_78_copies(r78_rows)
assert hits == {0, 1, 2, 3, 4}, f"Rule 78 prescan missed: {hits}"
print("✓ Rule 78 prescan finds 5-insn ptr-save-deref pattern on PS")

h = detect_rule_78(0, r78_ps[0], r78_rc[0], hits)
assert h is not None and "Rule 78" in h.rule, f"Rule 78 detector missed: {h}"
print("✓ Rule 78 detector emits hint at row 0")

h = detect_rule_78(2, r78_ps[2], r78_rc[2], hits)
assert h is not None and "Rule 78" in h.rule, f"Rule 78 detector missed at row 2: {h}"
print("✓ Rule 78 detector emits hint at each diff row in the pattern")

# Negative: equal rows (is_diff False) should NOT fire even if PS matches.
r78_eq = [(r78_ps[k], r78_ps[k], False) for k in range(5)]
hits_eq = _find_rule_78_copies(r78_eq)
assert hits_eq == set(), f"Rule 78 false-positive on equal rows: {hits_eq}"
print("✓ Rule 78 prescan skips equal-row patterns")

# Negative: same 5-insn shape on BOTH sides — both match, suppress.
r78_both = [(r78_ps[k], r78_ps[k], True) for k in range(5)]
hits_both = _find_rule_78_copies(r78_both)
assert hits_both == set(), f"Rule 78 false-positive when recomp also matches: {hits_both}"
print("✓ Rule 78 prescan suppresses when recomp has the same pattern")

# Negative: pattern broken — wrong register in step (4) load.
r78_broken = list(r78_ps)
r78_broken[3] = mk(0x49, [0x8a, 0x12], "mov dl, byte ptr [eax]")  # [eax] not [edx]
r78_rows_b = [(r78_broken[k], r78_rc[k], True) for k in range(5)]
hits_b = _find_rule_78_copies(r78_rows_b)
assert hits_b == set(), f"Rule 78 false-positive on broken pattern: {hits_b}"
print("✓ Rule 78 prescan rejects pattern with mismatched load source")

# Negative: regA must have a low-byte register (ESI/EDI/EBP/ESP have none).
r78_esi_save = list(r78_ps)
r78_esi_save[0] = mk(0x43, [0x89, 0xc6], "mov esi, eax")  # esi has no low byte
r78_rows_esi = [(r78_esi_save[k], r78_rc[k], True) for k in range(5)]
hits_esi = _find_rule_78_copies(r78_rows_esi)
assert hits_esi == set(), f"Rule 78 should require low-byte-capable regA: {hits_esi}"
print("✓ Rule 78 prescan requires regA to have a low-byte register")

# ── Rule 81 — byte-copy loop regalloc swap ──────────────────────────────────
# PS shape: load via EAX+disp, store via EDX (out → EDX, i → EAX)
# RC shape: load via EDX+disp, store via EAX (out → EAX, i → EDX)
r81_ps = [
    mk(0x00, [0x89, 0xc2],                                 "mov edx, eax"),
    mk(0x02, [0x31, 0xc0],                                 "xor eax, eax"),
    mk(0x04, [0x8a, 0x98, 0xfc, 0x7c, 0x02, 0x00],         "mov bl, byte ptr [eax + 0x27cfc]"),
    mk(0x0a, [0x84, 0xdb],                                 "test bl, bl"),
    mk(0x0c, [0x74, 0x06],                                 "je 0x14"),
    mk(0x0e, [0x88, 0x1a],                                 "mov byte ptr [edx], bl"),
    mk(0x10, [0x40],                                       "inc eax"),
    mk(0x11, [0x42],                                       "inc edx"),
]
r81_rc = [
    mk(0x00, [0x31, 0xd2],                                 "xor edx, edx"),
    mk(0x02, [0x8a, 0x9a, 0xfc, 0x7c, 0x02, 0x00],         "mov bl, byte ptr [edx + 0x27cfc]"),
    mk(0x08, [0x84, 0xdb],                                 "test bl, bl"),
    mk(0x0a, [0x74, 0x06],                                 "je 0x12"),
    mk(0x0c, [0x88, 0x18],                                 "mov byte ptr [eax], bl"),
    mk(0x0e, [0x42],                                       "inc edx"),
    mk(0x0f, [0x40],                                       "inc eax"),
    None,
]
r81_rows = [
    (r81_ps[k], r81_rc[k], True) for k in range(len(r81_ps))
]
hits = _find_rule_81_swap(r81_rows)
assert hits, f"Rule 81 prescan missed swap pattern: {hits}"
print("✓ Rule 81 prescan finds byte-copy regalloc swap (EAX↔EDX)")

h = detect_rule_81(min(hits), r81_ps[min(hits)], r81_rc[min(hits)], hits)
assert h is not None and "Rule 81" in h.rule, f"Rule 81 detector missed: {h}"
assert "drop the named" in h.fix, f"Rule 81 fix wording missing: {h.fix}"
print("✓ Rule 81 detector emits hint with source-rewrite suggestion")

# Negative: when BOTH sides use the same byte-copy shape (no swap),
# detector must not fire.
r81_no_swap_ps = [
    mk(0x00, [0x31, 0xd2],                                 "xor edx, edx"),
    mk(0x02, [0x8a, 0x9a, 0xfc, 0x7c, 0x02, 0x00],         "mov bl, byte ptr [edx + 0x27cfc]"),
    mk(0x08, [0x88, 0x18],                                 "mov byte ptr [eax], bl"),
]
r81_no_swap_rows = [(r81_no_swap_ps[k], r81_no_swap_ps[k], False)
                    for k in range(len(r81_no_swap_ps))]
hits_eq = _find_rule_81_swap(r81_no_swap_rows)
assert hits_eq == set(), f"Rule 81 false-positive when sides match: {hits_eq}"
print("✓ Rule 81 prescan suppresses when both sides have same shape")

# Negative: PS and RC use the SAME swap direction (no actual swap).
r81_same_dir_rows = [
    (r81_ps[k], r81_ps[k], False) for k in range(len(r81_ps))
]
hits_same = _find_rule_81_swap(r81_same_dir_rows)
assert hits_same == set(), f"Rule 81 false-positive with identical PS shape: {hits_same}"
print("✓ Rule 81 prescan requires base/store register swap symmetry")

# Negative: load without displacement (the *p style) must not fire.
r81_no_disp_ps = [
    mk(0x00, [0x8a, 0x13],                                 "mov dl, byte ptr [ebx]"),
    mk(0x02, [0x88, 0x11],                                 "mov byte ptr [ecx], dl"),
]
r81_no_disp_rc = [
    mk(0x00, [0x8a, 0x11],                                 "mov dl, byte ptr [ecx]"),
    mk(0x02, [0x88, 0x13],                                 "mov byte ptr [ebx], dl"),
]
r81_no_disp_rows = [(r81_no_disp_ps[k], r81_no_disp_rc[k], True)
                    for k in range(len(r81_no_disp_ps))]
hits_nd = _find_rule_81_swap(r81_no_disp_rows)
assert hits_nd == set(), f"Rule 81 should require disp32 in load: {hits_nd}"
print("✓ Rule 81 prescan requires displacement in indexed byte load")

# ── Rule 82 — if-zero-replace pins indexed-load scratch ────────────────────
# PS: scratch=EAX, result=EDX
r82_ps = [
    mk(0x00, [0x0f, 0xbf, 0x05, 0xb4, 0x58, 0x08, 0x00], "movsx eax, word ptr [0x858b4]"),
    mk(0x07, [0x69, 0xc0, 0xaf, 0x00, 0x00, 0x00],         "imul eax, eax, 0xaf"),
    mk(0x0d, [0x8b, 0x90, 0xc0, 0x46, 0x08, 0x00],         "mov edx, dword ptr [eax + 0x846c0]"),
    mk(0x13, [0x85, 0xd2],                                 "test edx, edx"),
    mk(0x15, [0x75, 0x05],                                 "jne 0x1c"),
    mk(0x17, [0xba, 0x08, 0x00, 0x00, 0x00],               "mov edx, 8"),
]
# RC: scratch=EDX, result=EDX (in-place RMW)
r82_rc = [
    mk(0x00, [0x0f, 0xbf, 0x15, 0xb4, 0x58, 0x08, 0x00], "movsx edx, word ptr [0x858b4]"),
    mk(0x07, [0x69, 0xd2, 0xaf, 0x00, 0x00, 0x00],         "imul edx, edx, 0xaf"),
    mk(0x0d, [0x8b, 0x92, 0xc0, 0x46, 0x08, 0x00],         "mov edx, dword ptr [edx + 0x846c0]"),
    mk(0x13, [0x85, 0xd2],                                 "test edx, edx"),
    mk(0x15, [0x75, 0x05],                                 "jne 0x1c"),
    mk(0x17, [0xba, 0x08, 0x00, 0x00, 0x00],               "mov edx, 8"),
]
r82_rows = [(r82_ps[k], r82_rc[k], True) for k in range(len(r82_ps))]
hits = _find_rule_82_pattern(r82_rows)
assert hits, f"Rule 82 prescan missed if-zero-replace pattern: {hits}"
assert 0 in hits or 1 in hits or 2 in hits, \
    f"Rule 82 hint should fire on one of the first 3 rows: {hits}"
print("✓ Rule 82 prescan finds movsx+imul+load + test/jne/mov-imm pattern")

h = detect_rule_82(min(hits), r82_ps[min(hits)], r82_rc[min(hits)], hits)
assert h is not None and "Rule 82" in h.rule, f"Rule 82 detector missed: {h}"
assert "ternary" in h.fix, f"Rule 82 fix wording missing 'ternary': {h.fix}"
print("✓ Rule 82 detector emits ternary-rewrite hint")

# Negative: PS and RC both use scratch != result (no merge — already
# byte-exact form).  Detector must NOT fire.
r82_neither = [
    (r82_ps[k], r82_ps[k], False) for k in range(len(r82_ps))
]
assert _find_rule_82_pattern(r82_neither) == set(), \
    "Rule 82 false-positive when both sides byte-exact"
print("✓ Rule 82 prescan suppresses when both sides match PS shape")

# Negative: both sides use scratch == result (no swap signal).
r82_both_merge = [(r82_rc[k], r82_rc[k], False) for k in range(len(r82_rc))]
assert _find_rule_82_pattern(r82_both_merge) == set(), \
    "Rule 82 false-positive when both sides use in-place RMW"
print("✓ Rule 82 prescan suppresses when both sides merge scratch/result")

# Negative: no if-zero-replace tail (load present but no test/jne/mov-imm).
r82_no_check = [
    (r82_ps[0], r82_rc[0], True),
    (r82_ps[1], r82_rc[1], True),
    (r82_ps[2], r82_rc[2], True),
    # No test/jne/mov-imm follow-up — pattern incomplete.
    (mk(0x13, [0x90], "nop"), mk(0x13, [0x90], "nop"), False),
]
assert _find_rule_82_pattern(r82_no_check) == set(), \
    "Rule 82 false-positive when no if-zero-replace tail"
print("✓ Rule 82 prescan requires test/jne/mov-imm if-zero tail")

# Negative: different result registers between PS and RC (would be a
# call-arg position diff, not a scratch-merge).
r82_diff_result_ps = list(r82_ps)
r82_diff_result_rc = list(r82_rc)
r82_diff_result_rc[2] = mk(0x0d, [0x8b, 0x9a, 0xc0, 0x46, 0x08, 0x00],
                            "mov ebx, dword ptr [edx + 0x846c0]")
r82_diff_result_rc[3] = mk(0x13, [0x85, 0xdb], "test ebx, ebx")
r82_diff_result_rc[5] = mk(0x17, [0xbb, 0x08, 0x00, 0x00, 0x00],
                            "mov ebx, 8")
r82_diff_rows = [
    (r82_diff_result_ps[k], r82_diff_result_rc[k], True)
    for k in range(len(r82_diff_result_ps))
]
assert _find_rule_82_pattern(r82_diff_rows) == set(), \
    "Rule 82 false-positive when PS/RC result regs differ"
print("✓ Rule 82 prescan requires matching result register on both sides")

# ── Rule 91 — compound op= (in-place RMW) vs expanded load-op-store ────────
from c2.commands.rule_hints import detect_rule_91

# True positive: PS in-place `xor byte [eax+disp], 1`; RC load-op-store to the
# SAME indexed address.
r91_ps_rmw  = mk(0, [0x80, 0xb0, 0x0d, 0x80, 0x04, 0x00, 0x01],
                 "xor byte ptr [eax + 0x4380d], 1")
r91_rc_load = mk(0, [0x8a, 0x90, 0x57, 0xf0, 0x02, 0x00],
                 "mov dl, byte ptr [eax + 0x2f057]")
r91_rc_op   = mk(6, [0x80, 0xf2, 0x01], "xor dl, 1")
r91_rc_st   = mk(9, [0x88, 0x90, 0x57, 0xf0, 0x02, 0x00],
                 "mov byte ptr [eax + 0x2f057], dl")
h = detect_rule_91(r91_ps_rmw, r91_rc_load, None, None, r91_rc_op, r91_rc_st)
assert h is not None and h.rule == "Rule 91", f"Rule 91 missed: {h}"
print("✓ Rule 91 fires on indexed in-place RMW vs complete load-op-store")

# Negative: stack-slot RMW (`[esp+4]`) is NOT an indexed lvalue — must not fire.
r91_stack_rmw = mk(0, [0x80, 0x44, 0x24, 0x04, 0x03], "add byte ptr [esp + 4], 3")
assert detect_rule_91(r91_stack_rmw, r91_rc_load, None, None,
                      r91_rc_op, r91_rc_st) is None, \
    "Rule 91 false-positive on a stack-slot RMW"
print("✓ Rule 91 ignores stack-slot (non-indexed) RMW")

# Negative: load and store address differ — coincidental, not a self-modify.
r91_rc_st_other = mk(9, [0x88, 0x90, 0x00, 0x10, 0x00, 0x00],
                     "mov byte ptr [eax + 0x1000], dl")
assert detect_rule_91(r91_ps_rmw, r91_rc_load, None, None,
                      r91_rc_op, r91_rc_st_other) is None, \
    "Rule 91 false-positive when load/store addresses differ"
print("✓ Rule 91 requires load-addr == store-addr (real self-modify)")

# Negative: incomplete sequence (no store) — must not fire.
assert detect_rule_91(r91_ps_rmw, r91_rc_load, None, None,
                      r91_rc_op, None) is None, \
    "Rule 91 false-positive on incomplete load-op-store"
print("✓ Rule 91 requires the complete load-op-store sequence")

# ── Rule 96 — SIB scale fold (`idx*4`) vs pre-scale (`shl`+plain index) ───
from c2.commands.rule_hints import detect_rule_96

# PS folds X*4 into the SIB byte; recomp pre-scaled X with `shl edx, 2` and
# emits a plain `[edx + eax + disp]` with no scale.
r96_ps   = mk(0, [0x8a, 0x84, 0x82, 0x44, 0x7b, 0x00, 0x00],
                 "mov al, byte ptr [edx + eax*4 + 0x7b44]")
r96_rc   = mk(0, [0x8a, 0x84, 0x02, 0x82, 0x91, 0x00, 0x00],
                 "mov al, byte ptr [edx + eax + 0x9182]")
r96_shl  = mk(0, [0xc1, 0xe2, 0x02], "shl edx, 2")
h = detect_rule_96(r96_ps, r96_rc, r96_shl, None)
assert h is not None and h.rule == "Rule 96", f"Rule 96 missed: {h}"
print("✓ Rule 96 fires on SIB-scale-vs-shl with a preceding shl")

# No preceding shl → must not fire (it's not a pre-scale, just a coincidence).
assert detect_rule_96(r96_ps, r96_rc, None, None) is None, \
    "Rule 96 false-positive without a preceding shl"
print("✓ Rule 96 requires the pre-scaling `shl` on the recomp side")

# Recomp also scaled → not a pre-scale divergence, must not fire.
r96_rc_scaled = mk(0, [0x8a, 0x84, 0x82, 0x82, 0x91, 0x00, 0x00],
                   "mov al, byte ptr [edx + eax*4 + 0x9182]")
assert detect_rule_96(r96_ps, r96_rc_scaled, r96_shl, None) is None, \
    "Rule 96 false-positive when recomp also uses the SIB scale"
print("✓ Rule 96 only fires when recomp dropped the scale")

# ── Rule 99 — narrow (16-bit) vs 32-bit zero-extend of a byte/short value ────
from c2.commands.rule_hints import detect_rule_99

# PS: xor ah, ah  (16-bit zext);  recomp: and eax, 0xff  (32-bit)
r99_ps = mk(0, [0x30, 0xe4], "xor ah, ah")
r99_rc = mk(0, [0x25, 0xff, 0x00, 0x00, 0x00], "and eax, 0xff")
h = detect_rule_99(r99_ps, r99_rc)
assert h is not None and h.rule == "Rule 99", f"Rule 99 missed: {h}"
print("✓ Rule 99 fires on xor ah,ah (PS) vs and eax,0xff (recomp)")

# ch variant (getlen), and-mask form
r99_ps_ch = mk(0, [0x30, 0xed], "xor ch, ch")
r99_rc_ecx = mk(0, [0x25, 0xff, 0x00, 0x00, 0x00], "and ecx, 0xff")
assert detect_rule_99(r99_ps_ch, r99_rc_ecx) is not None, "Rule 99 missed ch and-mask"
print("✓ Rule 99 fires on the ch/high-byte and-mask variant")

# full-register-xor form: PS xor ch,ch vs recomp xor ecx,ecx (corresponding reg)
r99_rc_xor = mk(0, [0x31, 0xc9], "xor ecx, ecx")
assert detect_rule_99(r99_ps_ch, r99_rc_xor) is not None, "Rule 99 missed full-xor form"
print("✓ Rule 99 fires on xor ch,ch (PS) vs xor ecx,ecx (recomp)")

# Negative: full-xor of a NON-corresponding register must not fire.
r99_rc_xor_eax = mk(0, [0x31, 0xc0], "xor eax, eax")
assert detect_rule_99(r99_ps_ch, r99_rc_xor_eax) is None, \
    "Rule 99 false-positive: ch should map to ecx, not eax"
print("✓ Rule 99 full-xor requires the corresponding 32-bit register")

# Negative: a plain `xor eax, eax` (full clear) is NOT a high-byte self-xor.
r99_full = mk(0, [0x31, 0xc0], "xor eax, eax")
assert detect_rule_99(r99_full, r99_rc) is None, \
    "Rule 99 false-positive on a full-register xor"
print("✓ Rule 99 ignores full-register xor")

# Negative: and with a non-0xff mask must not fire.
r99_rc_other = mk(0, [0x25, 0x00, 0xff, 0x00, 0x00], "and eax, 0xff00")
assert detect_rule_99(r99_ps, r99_rc_other) is None, \
    "Rule 99 false-positive on a non-0xff mask"
print("✓ Rule 99 requires the 0xff byte mask")

# ── Rule 100 — live-range-shortening lever (literal vs reused register) ──────
# PS re-materializes the literal 0xe0 into eax; recomp reuses esi (a still-live
# cached local) into the same dest.
r100_ps = mk(0, [0xb8, 0xe0, 0x00, 0x00, 0x00], "mov eax, 0xe0")
r100_rc = mk(0, [0x89, 0xf0],                   "mov eax, esi")
h = detect_rule_100(r100_ps, r100_rc, None, None, 0, 0, set(), set())
assert h is not None and h.rule == "Rule 100", f"Rule 100 missed: {h}"
print("✓ Rule 100 fires on PS literal vs recomp reused register (same dest)")

# Negative: PS immediate is a RELOCATED pointer literal (all imm bytes in the
# fixup set) — that's Rule 12 territory, not Rule 100.
r100_ps_fix = mk(0, [0xb8, 0x34, 0x22, 0x03, 0x00], "mov eax, 0x32234")
ps_fixups = {1, 2, 3, 4}  # imm32 bytes relocated
assert detect_rule_100(r100_ps_fix, r100_rc, None, None, 0, 0, ps_fixups, set()) is None, \
    "Rule 100 false-positive on a relocated pointer literal"
print("✓ Rule 100 ignores relocated pointer literals (defers to Rule 12)")

# Negative: both sides are `mov reg, imm` (different constants) — not Rule 100.
r100_rc_imm = mk(0, [0xb8, 0x14, 0x00, 0x00, 0x00], "mov eax, 0x14")
assert detect_rule_100(r100_ps, r100_rc_imm, None, None, 0, 0, set(), set()) is None, \
    "Rule 100 false-positive when recomp source is an immediate"
print("✓ Rule 100 requires recomp source to be a register, not an immediate")

# Negative: destination registers differ — not a same-dest substitution.
r100_rc_other_dst = mk(0, [0x89, 0xf3], "mov ebx, esi")
assert detect_rule_100(r100_ps, r100_rc_other_dst, None, None, 0, 0, set(), set()) is None, \
    "Rule 100 false-positive when destination registers differ"
print("✓ Rule 100 requires matching destination register")

# Negative: PS combines the literal into a following arith op on the same reg
# (`mov eax, 0x50; sub eax, esi` == `0x50 - esi`) - operand-order regalloc, not
# a complete-value literal substitution.
r100_ps_kv   = mk(0, [0xb8, 0x50, 0x00, 0x00, 0x00], "mov eax, 0x50")
r100_ps_sub  = mk(5, [0x29, 0xf0],                   "sub eax, esi")
assert detect_rule_100(r100_ps_kv, r100_rc, r100_ps_sub, None, 0, 0, set(), set()) is None, \
    "Rule 100 false-positive on a `K - v` arithmetic operand"
print("✓ Rule 100 excludes the `K - v` subtraction operand-order case")

# ── Rule 90 — jcc signedness + cmp width (enum vs unsigned-int discriminator) ─
# PS: byte compare + unsigned jump  (cmp al,0x1e ; jb)  ← byte-packed enum
# RC: signed jump (recomp widened to signed int)        (cmp eax,0x1e ; jl)
r90_ps_cmp_b = mk(0, [0x3c, 0x1e],             "cmp al, 0x1e")
r90_ps_jb    = mk(2, [0x72, 0x05],             "jb 9")
r90_rc_cmp_d = mk(0, [0x3d, 0x1e, 0, 0, 0],    "cmp eax, 0x1e")
r90_rc_jl    = mk(5, [0x7c, 0x05],             "jl 9")
h = detect_rule_90(r90_ps_jb, r90_rc_jl, r90_ps_cmp_b, r90_rc_cmp_d)
assert h is not None and "Rule 90" in h.rule, f"Rule 90 byte missed: {h}"
assert "BYTE" in h.summary and "enum" in h.fix, f"Rule 90 width wrong: {h}"
print("✓ Rule 90 byte+unsigned → enum / unsigned char")

# PS: dword compare + unsigned jump → unsigned int (NOT enum)
r90_ps_cmp_d = mk(0, [0x3d, 0x1e, 0, 0, 0],    "cmp eax, 0x1e")
h = detect_rule_90(r90_ps_jb, r90_rc_jl, r90_ps_cmp_d, r90_rc_cmp_d)
assert h is not None and "DWORD" in h.summary and "unsigned int" in h.fix, \
    f"Rule 90 dword wrong: {h}"
print("✓ Rule 90 dword+unsigned → unsigned int (not enum)")

# Both sides signed (the landfill.c case) → NO hint (source already correct)
h = detect_rule_90(r90_rc_jl, r90_rc_jl, r90_ps_cmp_d, r90_rc_cmp_d)
assert h is None, f"Rule 90 false-positive when both signed: {h}"
print("✓ Rule 90 silent when both sides signed (no enum opportunity)")

# width helper unit checks
assert _cmp_operand_width(mk(0, [], "cmp al, 0x1e")) == "byte"
assert _cmp_operand_width(mk(0, [], "cmp byte ptr [eax], 1")) == "byte"
assert _cmp_operand_width(mk(0, [], "cmp eax, 0x1e")) == "dword"
assert _cmp_operand_width(mk(0, [], "cmp dx, 3")) == "word"
assert _cmp_operand_width(mk(0, [], "mov eax, 1")) is None
print("✓ _cmp_operand_width classifies byte/word/dword")

print("\nAll synthetic tests pass.")


# ── Rule 109 — scaled-index load fused into the result register ──────────────
from c2.commands.rule_hints import detect_rule_109


def test_rule_109_fires_on_split_vs_merged_load():
    # PS keeps index in a scratch (eax), recomp merges it into the dst (edx).
    ps = mk(0, [0x8b, 0x90, 0, 0, 0, 0], "mov edx, dword ptr [eax + 0x80962]")
    rc = mk(0, [0x8b, 0x92, 0, 0, 0, 0], "mov edx, dword ptr [edx + 0xf956]")
    h = detect_rule_109(ps, rc)
    assert h is not None and h.rule == "Rule 109"


def test_rule_109_movsx_variant():
    ps = mk(0, [0x0f, 0xbf], "movsx edx, byte ptr [eax + 0x437da]")
    rc = mk(0, [0x0f, 0xbf], "movsx edx, byte ptr [edx + 0x2f024]")
    assert detect_rule_109(ps, rc) is not None


def test_rule_109_no_fire_when_dest_differs():
    # ordinary reg-identity swap, not an index fusion
    ps = mk(0, [], "mov edx, dword ptr [eax + 4]")
    rc = mk(0, [], "mov ecx, dword ptr [ecx + 4]")
    assert detect_rule_109(ps, rc) is None


def test_rule_109_no_fire_when_both_merged():
    ps = mk(0, [], "mov edx, dword ptr [edx + 4]")
    rc = mk(0, [], "mov edx, dword ptr [edx + 4]")
    assert detect_rule_109(ps, rc) is None


def test_rule_109_no_fire_when_both_split():
    # PS base != dst AND recomp base != dst -> plain base swap, not a fusion
    ps = mk(0, [], "mov edx, dword ptr [eax + 4]")
    rc = mk(0, [], "mov edx, dword ptr [ebx + 4]")
    assert detect_rule_109(ps, rc) is None


# ── Rule 110 — const-store FORM mismatch (immediate <-> register) ─────────────

def test_rule_110_ps_register_recomp_immediate():
    # PS caches the literal 1 in a register (>=2 refs); recomp uses it once
    # (immediate store).  Form mismatch -> ref-count lever.
    prev_ps = mk(0, [0xb2, 0x01], "mov dl, 1")
    ps      = mk(2, [0x88, 0x15, 0, 0, 0, 0], "mov byte ptr [0x87c4d], dl")
    rc      = mk(2, [0xc6, 0x05, 0, 0, 0, 0, 0x01], "mov byte ptr [0x45eb7], 1")
    h = detect_rule_110(ps, rc, prev_ps, None)
    assert h is not None and h.rule == "Rule 110", f"missed: {h}"


def test_rule_110_recomp_register_ps_immediate():
    # symmetric: recomp caches (register), PS immediate
    prev_rc = mk(0, [0xba, 0x05, 0, 0, 0], "mov edx, 5")
    ps      = mk(2, [0xc7, 0x05, 0, 0, 0, 0, 5, 0, 0, 0], "mov dword ptr [0x10], 5")
    rc      = mk(2, [0x89, 0x15, 0, 0, 0, 0], "mov dword ptr [0x20], edx")
    h = detect_rule_110(ps, rc, None, prev_rc)
    assert h is not None and h.rule == "Rule 110"


def test_rule_110_zero_xor_materialised():
    # PS register-form for 0 (xor bl,bl), recomp immediate byte 0
    prev_ps = mk(0, [0x30, 0xdb], "xor bl, bl")
    ps      = mk(2, [0x88, 0x1d, 0, 0, 0, 0], "mov byte ptr [0x3ccbd], bl")
    rc      = mk(2, [0xc6, 0x05, 0, 0, 0, 0, 0], "mov byte ptr [0x2f7b7], 0")
    h = detect_rule_110(ps, rc, prev_ps, None)
    assert h is not None and h.rule == "Rule 110"


def test_rule_110_no_fire_both_register():
    # both register-form, different reg -> regalloc (Byte-reg swap), NOT Rule 110
    prev_ps = mk(0, [0x30, 0xdb], "xor bl, bl")
    prev_rc = mk(0, [0x30, 0xf6], "xor dh, dh")
    ps = mk(2, [0x88, 0x1d, 0, 0, 0, 0], "mov byte ptr [0x846b8], bl")
    rc = mk(2, [0x88, 0x35, 0, 0, 0, 0], "mov byte ptr [0x46600], dh")
    assert detect_rule_110(ps, rc, prev_ps, prev_rc) is None


def test_rule_110_no_fire_both_immediate():
    ps = mk(0, [], "mov byte ptr [0x10], 5")
    rc = mk(0, [], "mov byte ptr [0x20], 5")
    assert detect_rule_110(ps, rc, None, None) is None


def test_rule_110_no_fire_register_not_const():
    # recomp register store but reg is NOT a materialised const (computed value)
    prev_rc = mk(0, [], "add edx, ecx")
    ps = mk(2, [], "mov dword ptr [0x10], 5")
    rc = mk(2, [], "mov dword ptr [0x20], edx")
    assert detect_rule_110(ps, rc, None, prev_rc) is None


def test_rule_110_no_fire_width_differs():
    prev_ps = mk(0, [], "mov dl, 1")
    ps = mk(2, [], "mov byte ptr [0x10], dl")
    rc = mk(2, [], "mov dword ptr [0x20], 1")
    assert detect_rule_110(ps, rc, prev_ps, None) is None


print("✓ Rule 110 const-store form-mismatch detector")


# ── Rules 139/140 (c2.c burn-down, 2026-06-13) ────────────────────────────

def _i139(off, asm, size=2):
    return (off, size, b"\x90" * size, asm)


class TestRule139DeadArgStaging:
    def test_fires_on_free_sample_buffer_shape(self):
        from c2.commands.rule_hints import detect_rule_139
        h = detect_rule_139(
            _i139(0x3dc, "mov eax, 0xa", 5), None,
            _i139(0x3e1, "call 0x357a", 5), _i139(0x3dc, "call 0x350a", 5),
            _i139(0x3d7, "call 0x3593", 5), _i139(0x3d7, "call 0x3593", 5))
        assert h is not None and h.rule == "Rule 139"
        assert "0xa" in h.summary

    def test_suppressed_when_whole_staging_block_differs(self):
        # evolve_industrial_activity false-positive class: previous row
        # is also PS-only -> different call signature, not a dead arg.
        from c2.commands.rule_hints import detect_rule_139
        h = detect_rule_139(
            _i139(0xdb, "mov eax, 2", 5), None,
            _i139(0xe0, "call 0xb1d", 5), _i139(0xe0, "call 0xb1d", 5),
            _i139(0xd7, "mov dl, byte ptr [esp + 0x14]", 4), None)
        assert h is None

    def test_requires_shared_call_next(self):
        from c2.commands.rule_hints import detect_rule_139
        h = detect_rule_139(
            _i139(0x10, "mov eax, 0x5", 5), None,
            _i139(0x15, "mov ebx, 1", 5), _i139(0x10, "mov ebx, 1", 5),
            None, None)
        assert h is None


class TestRule140LoopPrologueHoist:
    def _rows(self, ps_target, rc_target):
        eq = lambda off, asm, size: (
            _i139(off, asm, size), _i139(off, asm, size), False)
        return [
            eq(0x346, "xor ebp, ebp", 2),
            eq(0x348, "mov dword ptr [0x34754], ebp", 6),
            eq(0x34e, "cmp byte ptr [0x3ccac], 0", 7),
            (_i139(0x393, f"je {ps_target:#x}"),
             _i139(0x393, f"je {rc_target:#x}"), True),
        ]

    def test_fires_on_main_turbo_shape(self):
        from c2.commands.rule_hints import _find_rule_140_rows
        out = _find_rule_140_rows(self._rows(0x34e, 0x346))
        assert 3 in out and out[3].rule == "Rule 140"
        assert "AFTER 2 store" in out[3].summary

    def test_no_fire_when_targets_match_direction_and_gap_zero(self):
        from c2.commands.rule_hints import _find_rule_140_rows
        assert _find_rule_140_rows(self._rows(0x346, 0x346)) == {}

    def test_no_fire_when_window_has_non_store(self):
        from c2.commands.rule_hints import _find_rule_140_rows
        rows = self._rows(0x34e, 0x346)
        call = _i139(0x346, "call 0x100", 2)
        rows[0] = (call, call, False)
        assert _find_rule_140_rows(rows) == {}


# ── Rules 141-147 (bbarian.c burn-down, 2026-06-12) ────────────────────────
#
# These detectors decode the RAW BYTES via c2.commands.insn_ast (capstone
# detail), so every test instruction below carries its genuine encoding.

def _enc(off, raw_hex, asm=""):
    raw = bytes.fromhex(raw_hex)
    return (off, len(raw), raw, asm)


class TestRule141LiveArgVsZero:
    def _rows(self, with_xor=True, call_equal=True):
        rows = []
        if with_xor:
            # RC-only: xor edx, edx
            rows.append((None, _enc(0x17, "31d2", "xor edx, edx"), True))
        # equal staging: mov ecx, 1 / xor ebx, ebx / mov eax, 3
        for off, hexs, asm in [(0x19, "b901000000", "mov ecx, 1"),
                               (0x1e, "31db", "xor ebx, ebx"),
                               (0x20, "b803000000", "mov eax, 3")]:
            i = _enc(off, hexs, asm)
            rows.append((i, i, False))
        call = _enc(0x25, "e8b7050000", "call 0x5e1")
        rows.append((call, call, False) if call_equal else (call, None, True))
        return rows

    def test_fires_on_war_trouble_shape(self):
        from c2.commands.rule_hints import _find_rule_141_rows
        out = _find_rule_141_rows(self._rows())
        assert 0 in out and out[0].rule == "Rule 141"
        assert "edx" in out[0].summary and "LIVE" in out[0].summary

    def test_ps_side_direction(self):
        from c2.commands.rule_hints import _find_rule_141_rows
        rows = self._rows()
        ps_xor = _enc(0x17, "31d2", "xor edx, edx")
        rows[0] = (ps_xor, None, True)
        out = _find_rule_141_rows(rows)
        assert 0 in out and "PS zeroes" in out[0].summary

    def test_no_fire_without_shared_call(self):
        from c2.commands.rule_hints import _find_rule_141_rows
        assert _find_rule_141_rows(self._rows(call_equal=False)) == {}

    def test_no_fire_on_eax(self):
        # xor eax, eax is return-value/arg-1 setup; excluded by design.
        from c2.commands.rule_hints import _find_rule_141_rows
        rows = self._rows()
        rows[0] = (None, _enc(0x17, "31c0", "xor eax, eax"), True)
        assert _find_rule_141_rows(rows) == {}


class TestRule142ReturnStagingViaEdx:
    def test_fires_on_revolt_trouble_shape(self):
        from c2.commands.rule_hints import detect_rule_142
        h = detect_rule_142(
            _enc(0x15c, "ba01000000", "mov edx, 1"),
            _enc(0x15c, "b801000000", "mov eax, 1"),
            _enc(0x161, "89d0", "mov eax, edx"),
            _enc(0x161, "5d", "pop ebp"))
        assert h is not None and h.rule == "Rule 142"
        assert "&&" in h.fix

    def test_requires_same_constant(self):
        from c2.commands.rule_hints import detect_rule_142
        h = detect_rule_142(
            _enc(0x15c, "ba01000000", "mov edx, 1"),
            _enc(0x15c, "b802000000", "mov eax, 2"),
            _enc(0x161, "89d0", "mov eax, edx"),
            _enc(0x161, "5d", "pop ebp"))
        assert h is None

    def test_requires_staging_copy_next(self):
        from c2.commands.rule_hints import detect_rule_142
        h = detect_rule_142(
            _enc(0x15c, "ba01000000", "mov edx, 1"),
            _enc(0x15c, "b801000000", "mov eax, 1"),
            _enc(0x161, "5d", "pop ebp"),
            _enc(0x161, "5d", "pop ebp"))
        assert h is None


class TestRule143MemoryRmwChain:
    def _rows(self):
        # do_land_trade shape: PS copy chain vs RC fused in-place.
        return [
            (_enc(0x99, "88f3", "mov bl, dh"),
             _enc(0x99, "08f2", "or dl, dh"), True),
            (_enc(0x9b, "08d3", "or bl, dl"),
             _enc(0x9b, "80e29f", "and dl, 0x9f"), True),
            (_enc(0x9d, "88df", "mov bh, bl"),
             _enc(0x9e, "8890d0860400", "mov byte ptr [eax + 0x486d0], dl"),
             True),
            (_enc(0x9f, "80e79f", "and bh, 0x9f"), None, True),
            (_enc(0xa2, "88b8bb960400", "mov byte ptr [eax + 0x496bb], bh"),
             None, True),
        ]

    def test_fires_on_do_land_trade_shape(self):
        from c2.commands.rule_hints import _find_rule_143_rows
        out = _find_rule_143_rows(self._rows())
        assert out, "expected at least one Rule 143 row"
        h = next(iter(out.values()))
        assert h.rule == "Rule 143" and "compound RMW" in h.fix

    def test_no_fire_without_final_store(self):
        from c2.commands.rule_hints import _find_rule_143_rows
        rows = self._rows()[:2] + [
            (_enc(0x9d, "c3", "ret"), _enc(0x9e, "c3", "ret"), False)]
        assert _find_rule_143_rows(rows) == {}

    def test_no_fire_when_rc_row_not_fused_alu(self):
        from c2.commands.rule_hints import _find_rule_143_rows
        rows = self._rows()
        # RC row aligned with the first PS copy is a call: not the shape.
        rows[0] = (rows[0][0], _enc(0x99, "e800010000", "call 0x19e"), True)
        rows[1] = (rows[1][0], None, True)
        rows[2] = (rows[2][0], None, True)
        assert _find_rule_143_rows(rows) == {}


class TestRule144WhileIPlusPlus:
    def _rows(self, with_back_jump=True, diff=True):
        rows = [
            # loop head: mov eax, ecx / inc ecx / cmp eax, 0x14 / jge fwd
            (_enc(0x08, "89c8", "mov eax, ecx"),
             _enc(0x08, "89c8", "mov eax, ecx"), diff),
            (_enc(0x0a, "41", "inc ecx"),
             _enc(0x0a, "41", "inc ecx"), False),
            (_enc(0x0b, "83f814", "cmp eax, 0x14"),
             _enc(0x0b, "83f814", "cmp eax, 0x14"), False),
        ]
        if with_back_jump:
            # jne 0x8 (backward, from 0x50: 75 b6 -> 0x52 - 0x4a = 0x8)
            j = _enc(0x50, "75b6", "jne 0x8")
            rows.append((j, j, False))
        return rows

    def test_fires_on_invasion_points_shape(self):
        from c2.commands.rule_hints import _find_rule_144_rows
        out = _find_rule_144_rows(self._rows())
        assert 0 in out and out[0].rule == "Rule 144"
        assert "while (i++ < 0x14)" in out[0].fix

    def test_no_fire_without_back_edge(self):
        from c2.commands.rule_hints import _find_rule_144_rows
        assert _find_rule_144_rows(self._rows(with_back_jump=False)) == {}

    def test_no_fire_when_all_rows_equal(self):
        from c2.commands.rule_hints import _find_rule_144_rows
        assert _find_rule_144_rows(self._rows(diff=False)) == {}


class TestRule145SignedRemVsMask:
    def _rows(self):
        return [
            (_enc(0x28, "bb08000000", "mov ebx, 8"),
             _enc(0x28, "89d0", "mov eax, edx"), True),
            (_enc(0x2d, "89d0", "mov eax, edx"),
             _enc(0x2a, "83e207", "and edx, 7"), True),
            (_enc(0x2f, "c1fa1f", "sar edx, 0x1f"), None, True),
            (_enc(0x32, "f7fb", "idiv ebx"), None, True),
        ]

    def test_fires_on_invades_city_shape(self):
        from c2.commands.rule_hints import _find_rule_145_rows
        out = _find_rule_145_rows(self._rows())
        assert 3 in out and out[3].rule == "Rule 145"
        assert "% 8" in out[3].fix

    def test_no_fire_when_mask_mismatches_divisor(self):
        from c2.commands.rule_hints import _find_rule_145_rows
        rows = self._rows()
        rows[1] = (rows[1][0], _enc(0x2a, "83e20f", "and edx, 0xf"), True)
        assert _find_rule_145_rows(rows) == {}

    def test_no_fire_on_non_power_of_two(self):
        from c2.commands.rule_hints import _find_rule_145_rows
        rows = self._rows()
        rows[0] = (_enc(0x28, "bb07000000", "mov ebx, 7"), rows[0][1], True)
        assert _find_rule_145_rows(rows) == {}


class TestRule146DeinventCseCalleeSave:
    def _rows(self, n_cmps=2):
        rows = [
            # def: mov ebx, [eax+disp] vs mov eax, [eax+disp]
            (_enc(0x0e, "8b9842470800", "mov ebx, [eax + 0x84742]"),
             _enc(0x0e, "8b8026c60400", "mov eax, [eax + 0x4c626]"), True),
        ]
        cmps = [("81fb20030000", "3d20030000", "0x320"),
                ("81fb58020000", "3d58020000", "0x258"),
                ("81fb90010000", "3d90010000", "0x190")][:n_cmps]
        off = 0x14
        for ps_hex, rc_hex, imm in cmps:
            rows.append((_enc(off, ps_hex, f"cmp ebx, {imm}"),
                         _enc(off, rc_hex, f"cmp eax, {imm}"), True))
            off += 7
        return rows

    def test_fires_on_invades_city_shape(self):
        from c2.commands.rule_hints import _find_rule_146_rows
        out = _find_rule_146_rows(self._rows())
        assert 0 in out and out[0].rule == "Rule 146"
        assert "de-invent" in out[0].fix

    def test_requires_two_compares(self):
        from c2.commands.rule_hints import _find_rule_146_rows
        assert _find_rule_146_rows(self._rows(n_cmps=1)) == {}

    def test_requires_matching_immediates(self):
        from c2.commands.rule_hints import _find_rule_146_rows
        rows = self._rows()
        rows[1] = (rows[1][0],
                   _enc(0x14, "3d21030000", "cmp eax, 0x321"), True)
        assert _find_rule_146_rows(rows) == {}


class TestRule147ElementWidthStride:
    # Misaligned rows (insert/delete), as the diff aligner actually
    # produces them: PS's scaled dword load and RC's unscaled byte load
    # land on DIFFERENT rows, paired only through the shared index reg.
    def _rows(self, rc_hex="8a9ac5be0000", rc_asm="mov bl, byte ptr [edx + 0xbec5]"):
        return [
            (_enc(0x79, "8b149567570000", "mov edx, [edx*4 + 0x5767]"),
             None, True),
            (_enc(0x80, "c1e203", "shl edx, 3"), None, True),
            (None, _enc(0x79, rc_hex, rc_asm), True),
        ]

    def test_fires_on_troop_numbers_shape(self):
        from c2.commands.rule_hints import _find_rule_147_rows
        out = _find_rule_147_rows(self._rows())
        assert 0 in out and out[0].rule == "Rule 147"
        assert "entities.h" in out[0].fix
        assert "PS reads a 4-byte" in out[0].summary

    def test_fires_reversed_sides(self):
        from c2.commands.rule_hints import _find_rule_147_rows
        rows = [(rc, ps, d) for ps, rc, d in self._rows()]
        out = _find_rule_147_rows(rows)
        assert out and "RC reads a 4-byte" in next(iter(out.values())).summary

    def test_no_fire_when_index_regs_differ(self):
        # RC reads through ECX while PS scales EDX: not the same value.
        from c2.commands.rule_hints import _find_rule_147_rows
        out = _find_rule_147_rows(self._rows(
            rc_hex="8a99c5be0000", rc_asm="mov bl, byte ptr [ecx + 0xbec5]"))
        assert out == {}

    def test_no_fire_same_width(self):
        from c2.commands.rule_hints import _find_rule_147_rows
        rows = [
            (_enc(0x79, "8b149567570000", "mov edx, [edx*4 + 0x5767]"),
             _enc(0x79, "8b148d67570000", "mov edx, [ecx*4 + 0x5767]"),
             True),
        ]
        assert _find_rule_147_rows(rows) == {}


# ── Rule 150 (gloops.c main_game_loop, 2026-06-13) ───────────────────────

class TestRule150GotoLabelVsReturn:
    """Multi-site jcc/jmp where PS target = epilogue, RC target = mid-fn label."""

    def _rows(self):
        # Simulate: 3 sites all jcc'ing to the same offsets, PS to epilogue,
        # RC to a mid-function label.  Epilogue is pop ebp; pop edi; pop esi;
        # pop edx; pop ecx; pop ebx; ret = 6 pops + ret.
        eq = lambda off, asm, hexs="90": (
            _enc(off, hexs, asm), _enc(off, hexs, asm), False)
        # Three je instructions at +0x50, +0x59, +0x62 -- both sides emit `je`
        # but with different targets.  PS targets 0x100 (epilogue).
        # RC targets 0x80 (mid-function, NOT an epilogue).
        # `je 0x100` from +0x50 with next-insn=+0x56 -> disp = 0x100 - 0x56 = 0xaa.
        # `je 0x80` from +0x50 with next-insn=+0x56 -> disp = 0x80 - 0x56 = 0x2a.
        # Both fit in disp32 (0F 84 + le-dword disp).
        def je_at(off, target):
            disp = target - (off + 6)
            return _enc(off, "0f84" + disp.to_bytes(4, "little").hex(),
                        f"je {target:#x}")

        rows = []
        rows.append((je_at(0x50, 0x100), je_at(0x50, 0x80), True))
        rows.append((je_at(0x59, 0x100), je_at(0x59, 0x80), True))
        rows.append((je_at(0x62, 0x100), je_at(0x62, 0x80), True))
        # mid-function content at offset 0x80 onwards: a `mov` instruction
        # (NOT an epilogue) -- common reachable code.  RC's jump target.
        eq_mid = (_enc(0x80, "89c8", "mov eax, ecx"),
                  _enc(0x80, "89c8", "mov eax, ecx"), False)
        rows.append(eq_mid)
        # Epilogue at offset 0x100 onwards: 6 pops + ret.  PS's jump target.
        for off, hexs, asm in [
            (0x100, "5d", "pop ebp"),
            (0x101, "5f", "pop edi"),
            (0x102, "5e", "pop esi"),
            (0x103, "5a", "pop edx"),
            (0x104, "59", "pop ecx"),
            (0x105, "5b", "pop ebx"),
            (0x106, "c3", "ret"),
        ]:
            rows.append((_enc(off, hexs, asm), _enc(off, hexs, asm), False))
        return rows

    def test_fires_on_main_game_loop_shape(self):
        from c2.commands.rule_hints import _find_rule_150_rows
        out = _find_rule_150_rows(self._rows())
        # All three je rows (indices 0, 1, 2) should fire.
        assert set(out.keys()) == {0, 1, 2}
        for i in (0, 1, 2):
            assert out[i].rule == "Rule 150"
            assert "0x100" in out[i].summary
            assert "3 sites converge" in out[i].summary
            assert "return;" in out[i].fix

    def test_no_fire_on_single_site(self):
        from c2.commands.rule_hints import _find_rule_150_rows
        rows = self._rows()
        # Keep only the first je; remove rows 1 and 2.
        rows = [rows[0]] + rows[3:]
        # Lone matches are likely Rule 92 / 95, not Rule 150.
        assert _find_rule_150_rows(rows) == {}

    def test_no_fire_when_gap_too_small(self):
        from c2.commands.rule_hints import _find_rule_150_rows
        # Move RC's target close to PS's target (gap < 20 b).
        eq = lambda off, asm, hexs="90": (
            _enc(off, hexs, asm), _enc(off, hexs, asm), False)
        def je_at(off, target):
            disp = target - (off + 6)
            return _enc(off, "0f84" + disp.to_bytes(4, "little").hex(),
                        f"je {target:#x}")
        rows = []
        for off in (0x50, 0x59, 0x62):
            rows.append((je_at(off, 0x100), je_at(off, 0xf0), True))  # gap=16
        for off, hexs, asm in [
            (0xf0, "89c8", "mov eax, ecx"),
            (0x100, "5d", "pop ebp"),
            (0x101, "5f", "pop edi"),
            (0x102, "5e", "pop esi"),
            (0x103, "5a", "pop edx"),
            (0x104, "59", "pop ecx"),
            (0x105, "5b", "pop ebx"),
            (0x106, "c3", "ret"),
        ]:
            rows.append((_enc(off, hexs, asm), _enc(off, hexs, asm), False))
        assert _find_rule_150_rows(rows) == {}

    def test_no_fire_when_rc_target_also_epilogue(self):
        # If BOTH sides target an epilogue (just different epilogues), it's
        # not the goto-vs-return pattern -- that's a layout cascade.
        from c2.commands.rule_hints import _find_rule_150_rows
        def je_at(off, target):
            disp = target - (off + 6)
            return _enc(off, "0f84" + disp.to_bytes(4, "little").hex(),
                        f"je {target:#x}")
        rows = []
        for off in (0x50, 0x59, 0x62):
            rows.append((je_at(off, 0x100), je_at(off, 0x80), True))
        # Add an epilogue at 0x80 too (so RC target is also epilogue).
        for off, hexs, asm in [
            (0x80, "5d", "pop ebp"),
            (0x81, "5f", "pop edi"),
            (0x82, "5e", "pop esi"),
            (0x83, "c3", "ret"),
            (0x100, "5d", "pop ebp"),
            (0x101, "5f", "pop edi"),
            (0x102, "5e", "pop esi"),
            (0x103, "5a", "pop edx"),
            (0x104, "59", "pop ecx"),
            (0x105, "5b", "pop ebx"),
            (0x106, "c3", "ret"),
        ]:
            rows.append((_enc(off, hexs, asm), _enc(off, hexs, asm), False))
        assert _find_rule_150_rows(rows) == {}
