"""Tests for c2.regalloc.seat_recon — the value-aligned PS<->RC seat diff
(gap #1) and the type/width diff (gap #3).

The rows use the json shape ({'off','ln','ps':{'asm':…},'rc':{'asm':…}}).
Soundness invariant: byte-exact (PS asm == RC asm) ⇒ no swap, no width diff.
"""
from c2.regalloc import seat_recon as sr


def _row(off, ps, rc, ln=None):
    r = {"off": off, "ln": ln}
    if ps is not None:
        r["ps"] = {"asm": ps}
    if rc is not None:
        r["rc"] = {"asm": rc}
    return r


# ── seat diff (gap #1) ──────────────────────────────────────────────────────
def test_identical_rows_are_clean():
    rows = [_row(0, "mov eax, ebx", "mov eax, ebx"),
            _row(2, "add ecx, edx", "add ecx, edx")]
    out = sr.seat_diff(rows)
    assert out["verdict"] == "clean"
    assert out["swaps"] == []


def test_systematic_swap_detected_and_named_by_family():
    # ESI (PS) consistently <-> ECX (RC) across several rows = a seat swap
    rows = [_row(i, f"mov edx, esi", f"mov edx, ecx") for i in range(4)]
    out = sr.seat_diff(rows)
    assert out["verdict"] == "swap"
    sw = out["swaps"][0]
    assert {sw["rc"], sw["ps"]} == {"ECX", "ESI"}
    assert sw["support"] >= 2


def test_one_off_divergence_is_clean_with_first_divergence():
    rows = [_row(i, "mov eax, ebx", "mov eax, ebx") for i in range(6)]
    rows.append(_row(99, "mov eax, dword ptr [0x10]",
                     "mov ebx, dword ptr [0x20]"))  # lone EAX<->EBX
    out = sr.seat_diff(rows)
    assert out["verdict"] == "clean"          # not systematic
    assert out["first_divergence"] is not None
    assert {out["first_divergence"]["rc"],
            out["first_divergence"]["ps"]} == {"EAX", "EBX"}


def test_mem_address_operands_ignored():
    # different masked globals must NOT register as a divergence
    rows = [_row(0, "mov eax, dword ptr [0x72dc4]",
                 "mov eax, dword ptr [0x2c731]")]
    out = sr.seat_diff(rows)
    assert out["verdict"] == "clean"


# ── type/width diff (gap #3) ────────────────────────────────────────────────
def test_byte_exact_has_no_width_diff():
    rows = [_row(0, "cmp cl, al", "cmp cl, al"),
            _row(2, "jge 0x10", "jge 0x10"),
            _row(4, "movzx esi, al", "movzx esi, al")]
    assert sr.type_width_diff(rows)["count"] == 0


def test_signedness_branch_multiset_delta():
    # PS uses jge (signed), RC uses jae (unsigned) for the same comparison
    rows = [_row(0, "cmp cl, al", "cmp cl, dl"),
            _row(2, "jge 0x10", "jae 0x10", ln=967)]
    out = sr.type_width_diff(rows)
    assert out["count"] >= 1
    jcc = [s for s in out["signedness"] if s["family"] == "jcc"][0]
    assert jcc["delta"] == 1          # PS has one more signed branch
    assert jcc["examples"] and jcc["examples"][0]["ln"] == 967


def test_extension_signedness():
    rows = [_row(0, "movsx eax, bl", "movzx eax, bl")]
    out = sr.type_width_diff(rows)
    ext = [s for s in out["signedness"] if s["family"] == "ext"][0]
    assert ext["delta"] == 1


def test_same_family_byte_vs_dword_width():
    # value a: PS tests it as a byte (al), we as a dword (eax) — same family A
    rows = [_row(0, "test al, al", "test eax, eax", ln=836)]
    out = sr.type_width_diff(rows)
    assert len(out["width"]) == 1
    assert out["width"][0]["ps_width"] == 1
    assert out["width"][0]["rc_width"] == 4


def test_cross_family_width_is_not_flagged():
    # PS al vs RC ebp = a register swap, NOT a width bug
    rows = [_row(0, "test al, al", "test ebp, ebp")]
    assert sr.type_width_diff(rows)["width"] == []


def test_capstone_desync_row_not_flagged_as_width():
    # a misaligned pair (different operand SHAPES) must not register as width
    # even when one operand coincidentally shares a register family.
    rows = [_row(0, "add ah, al", "add dword ptr [eax], eax")]
    assert sr.type_width_diff(rows)["count"] == 0


# ── spill / frame diff (gap #4) ─────────────────────────────────────────────
def test_spill_byte_exact_has_no_frame_delta():
    rows = [_row(0, "sub esp, 0x10", "sub esp, 0x10"),
            _row(4, "mov byte ptr [esp + 8], al", "mov byte ptr [esp + 8], al")]
    out = sr.spill_diff(rows)
    assert out["ps_frame"] == out["rc_frame"] == 16
    assert out["slot_delta"] == 0 and out["direction"] == "equal"


# ── composite shape distance (gap #5 core) ───────────────────────────
def test_shape_distance_zero_when_clean():
    out = sr.shape_distance_from({"swaps": [], "first_divergence": None},
                                 {"count": 0},
                                 {"ps_frame": 8, "rc_frame": 8,
                                  "slot_delta": 0}, byte_diff=0)
    assert out["shape"] == 0 and out["total"] == 0


def test_shape_distance_decomposes_and_excludes_bytes():
    out = sr.shape_distance_from(
        {"swaps": [{"rc": "ESI", "ps": "ECX"}], "first_divergence": None,
         "map": {"A": "A", "B": "B", "C": "ESI"}},
        {"count": 4, "total": 27},
        {"ps_frame": 32, "rc_frame": 8, "slot_delta": 6,
         "ps_slots": 9, "rc_slots": 3},
        byte_diff=592, ir_divergent=14, ir_max=62)
    assert out["shape"] == 25 and out["total"] == 617
    # goal-post denominators (the shape-dependent upper bound per layer)
    assert out["ir_total"] == 62 and out["width_total"] == 27
    assert out["spill_total"] == 9 and out["seat_total"] == 3


def test_fmt_shape_layers_shows_goalposts():
    out = sr.shape_distance_from(
        {"swaps": [], "map": {"A": "A", "B": "B"}}, {"count": 0, "total": 5},
        {"ps_frame": 8, "rc_frame": 8, "slot_delta": 0,
         "ps_slots": 2, "rc_slots": 2},
        ir_divergent=3, ir_max=20)
    assert sr.fmt_shape_layers(out) == "ir 3/20 · width 0/5 · spill 0/2 · seat 0/2"


def test_shape_distance_fix_next_is_highest_nonzero_layer():
    # ir 0, width 0, spill 0, seat 1 -> fix_next seat
    assert sr.shape_distance_from(
        {"swaps": [{"rc": "A", "ps": "B"}]}, {"count": 0},
        {"ps_frame": 8, "rc_frame": 8, "slot_delta": 0})["fix_next"] == "seat"
    # all shape layers 0 but bytes>0 -> pure regalloc residue
    assert sr.shape_distance_from(
        {"swaps": []}, {"count": 0},
        {"ps_frame": 8, "rc_frame": 8, "slot_delta": 0},
        byte_diff=12)["fix_next"] == "regalloc"
    # width present beats seat (fix-order ir>width>spill>seat)
    assert sr.shape_distance_from(
        {"swaps": [{"rc": "A", "ps": "B"}]}, {"count": 3},
        {"ps_frame": 8, "rc_frame": 8, "slot_delta": 0})["fix_next"] == "width"


def test_shape_distance_localized_seat_counts_one():
    out = sr.shape_distance_from(
        {"swaps": [], "first_divergence": {"off": 0}},
        {"count": 0}, {"ps_frame": 8, "rc_frame": 8, "slot_delta": 0})
    assert out["seat"] == 1 and out["shape"] == 1


def test_spill_ps_spills_more_with_byte_slots():
    rows = [
        _row(0, "sub esp, 0x20", "sub esp, 8"),
        _row(4, "mov byte ptr [esp + 0x10], al", "mov esi, eax"),
        _row(8, "mov byte ptr [esp + 0x14], bl", "mov edi, ebx"),
        _row(12, "mov dword ptr [esp + 0xc], edx", "mov dword ptr [esp], edx"),
    ]
    out = sr.spill_diff(rows)
    assert out["ps_frame"] == 32 and out["rc_frame"] == 8
    assert out["ps_byte_slots"] == 2 and out["rc_byte_slots"] == 0
    assert out["slot_delta"] > 0 and out["direction"] == "ps_spills_more"
