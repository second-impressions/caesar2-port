"""Tests for the dual -d1 run ledger (c2.runledger).

The ledger compares PS-vs-RC instruction streams REGISTER-BLINDLY with
each side segmented by its OWN -d1 line marks (no cross-side attribution
through the byte-diff alignment).  Soundness invariant: identical
canonical streams => zero islands => verdict regalloc_pure.
"""
from __future__ import annotations

from c2.runledger import (
    LedgerInsn, build_ledger, canon_insn, canon_stream, ledger_from_raw,
)


# ---- canonicalization -------------------------------------------------------

def test_canon_register_blind_preserves_width():
    assert canon_insn(0, 2, "mov eax, ebx", frozenset(), b"") == "mov R32, R32"
    assert canon_insn(0, 2, "mov al, bl", frozenset(), b"") == "mov R8, R8"
    assert canon_insn(0, 3, "mov ax, cx", frozenset(), b"") == "mov R16, R16"
    # byte and dword tests must NOT canonicalize to the same string
    assert canon_insn(0, 2, "test al, al", frozenset(), b"") != \
        canon_insn(0, 2, "test eax, eax", frozenset(), b"")


def test_canon_masks_branch_targets():
    assert canon_insn(0, 2, "jle 0x46", frozenset(), b"") == "jle T"
    assert canon_insn(0, 5, "jmp 0x1a9", frozenset(), b"") == "jmp T"
    assert canon_insn(0, 5, "call 0x1234", frozenset(), b"") == "call T"
    # signedness twins stay distinct
    assert canon_insn(0, 2, "jl 0x10", frozenset(), b"") != \
        canon_insn(0, 2, "jb 0x10", frozenset(), b"")


def test_canon_masks_only_fixup_dwords():
    # insn at off 0, size 6: 8b 0d <dword 0x72cb8> = mov ecx,[0x72cb8]
    func = b"\x8b\x0d\xb8\x2c\x07\x00" + b"\x90" * 4
    out = canon_insn(0, 6, "mov ecx, dword ptr [0x72cb8]", {2}, func)
    assert out == "mov R32, dword ptr [G]"
    # a non-fixup immediate is KEPT (consts stay visible)
    assert canon_insn(0, 3, "add eax, 0x50", frozenset(), b"") == \
        "add R32, 0x50"


def test_canon_keeps_esp_displacement():
    # slot layout must stay visible ([esp+4] vs [esp] is a real diff)
    a = canon_insn(0, 4, "mov dword ptr [esp + 4], eax", frozenset(), b"")
    b = canon_insn(0, 3, "mov dword ptr [esp], eax", frozenset(), b"")
    assert a != b


# ---- stream segmentation ----------------------------------------------------

def _mk(insns, marks):
    """Build a canonical stream from [(off, size, text)] + {off: line}."""
    return canon_stream(insns, marks, frozenset(), b"\x90" * 64)


def test_stream_forward_fills_own_marks():
    st = _mk(
        [(0, 2, "mov eax, ebx"), (2, 2, "add eax, ecx"),
         (4, 2, "mov edx, eax")],
        {0: 10, 4: 11},
    )
    assert [i.line for i in st] == [10, 10, 11]


# ---- alignment + islands ----------------------------------------------------

def test_identical_streams_regalloc_pure():
    insns = [(0, 2, "mov eax, ebx"), (2, 2, "test eax, eax"),
             (4, 2, "jg 0x10")]
    ps = _mk(insns, {0: 5})
    rc = _mk(insns, {0: 99})       # different line NUMBERS are fine
    led = build_ledger(ps, rc)
    assert led.verdict == "regalloc_pure"
    assert led.matched == 3 and not led.islands


def test_register_renamed_streams_still_pure():
    ps = _mk([(0, 2, "mov ebx, edx"), (2, 2, "cmp ebx, ecx")], {0: 5})
    rc = _mk([(0, 2, "mov esi, eax"), (2, 2, "cmp esi, edi")], {0: 7})
    led = build_ledger(ps, rc)
    assert led.verdict == "regalloc_pure"


def test_width_divergence_is_an_island():
    ps = _mk([(0, 2, "test al, al"), (2, 2, "je 0x10")], {0: 5})
    rc = _mk([(0, 2, "test eax, eax"), (2, 2, "je 0x10")], {0: 7})
    led = build_ledger(ps, rc)
    assert led.verdict == "shape_islands"
    assert len(led.islands) == 1
    assert led.islands[0].ps_lines == [5]
    assert led.islands[0].rc_lines == [7]


def test_signedness_island_tagged():
    ps = _mk([(0, 2, "cmp eax, ebx"), (2, 2, "jl 0x10")], {0: 5})
    rc = _mk([(0, 2, "cmp eax, ebx"), (2, 2, "jb 0x10")], {0: 7})
    led = build_ledger(ps, rc)
    assert len(led.islands) == 1
    assert "signedness" in led.islands[0].tags


def test_slot_swap_island_tagged():
    ps = _mk([(0, 4, "mov dword ptr [esp + 4], eax")], {0: 5})
    rc = _mk([(0, 3, "mov dword ptr [esp], eax")], {0: 7})
    led = build_ledger(ps, rc)
    assert len(led.islands) == 1
    assert "slot" in led.islands[0].tags


def test_zext_idiom_island_tagged():
    ps = _mk([(0, 3, "movzx edi, al")], {0: 5})
    rc = _mk([(0, 5, "and eax, 0xff")], {0: 7})
    led = build_ledger(ps, rc)
    assert len(led.islands) == 1
    assert "zext-idiom" in led.islands[0].tags


def test_loop_form_island_tagged():
    # PS: bare jmp (rotated loop entry); RC: inline head test
    ps = _mk([(0, 5, "jmp 0x1a9")], {0: 5})
    rc = _mk([(0, 4, "cmp eax, dword ptr [esp + 8]"), (4, 2, "jle 0x20")],
             {0: 7})
    led = build_ledger(ps, rc)
    assert len(led.islands) == 1
    assert "loop-form" in led.islands[0].tags


def test_run_counting():
    # 3 PS runs; the middle one diverges
    ps = _mk([(0, 2, "mov eax, ebx"),
              (2, 2, "test al, al"),
              (4, 2, "mov edx, ecx")],
             {0: 5, 2: 6, 4: 7})
    rc = _mk([(0, 2, "mov eax, ebx"),
              (2, 2, "test eax, eax"),
              (4, 2, "mov edx, ecx")],
             {0: 7, 2: 8, 4: 9})
    led = build_ledger(ps, rc)
    assert led.ps_runs_total == 3
    assert led.ps_runs_divergent == 1


def test_ledger_from_raw_insnt_shape():
    # InsnT 4-tuples (off, size, raw, text) must be accepted too
    ps = [(0, 2, b"\x89\xd8", "mov eax, ebx")]
    rc = [(0, 2, b"\x89\xf0", "mov eax, esi")]
    led = ledger_from_raw(ps, {0: 5}, frozenset(), b"\x89\xd8",
                          rc, {0: 9}, frozenset(), b"\x89\xf0")
    assert led.verdict == "regalloc_pure"


def test_islands_in_shape_distance_and_formatters():
    from c2.regalloc.seat_recon import (
        shape_distance_from, fmt_shape_layers, fmt_shape_cell)
    # ledger available: islands surfaces in the dict and both formatters
    sd = shape_distance_from({}, {}, {}, byte_diff=100,
                             ir_divergent=5, ir_max=40, islands=12)
    assert sd["islands"] == 12
    assert "(isl 12)" in fmt_shape_layers(sd)
    assert "\u00b7i12" in fmt_shape_cell(sd)
    # regalloc_pure: islands 0 is SHOWN (it is the strong verdict)
    sd0 = shape_distance_from({}, {}, {}, byte_diff=100,
                              ir_divergent=0, ir_max=40, islands=0)
    assert "(isl 0)" in fmt_shape_layers(sd0)
    assert "\u00b7i0" in fmt_shape_cell(sd0)
    # ledger unavailable (binir fallback): islands is None and OMITTED
    sdn = shape_distance_from({}, {}, {}, byte_diff=100,
                              ir_divergent=5, ir_max=40)
    assert sdn["islands"] is None
    assert "isl" not in fmt_shape_layers(sdn)
    assert "\u00b7i" not in fmt_shape_cell(sdn)


def test_json_roundtrip():
    ps = _mk([(0, 2, "test al, al")], {0: 5})
    rc = _mk([(0, 2, "test eax, eax")], {0: 7})
    led = build_ledger(ps, rc)
    d = led.to_json()
    assert d["verdict"] == "shape_islands"
    assert d["islands"][0]["ps"][0]["text"] == "test al, al"
    slim = led.to_json(with_insns=False)
    assert "ps" not in slim["islands"][0]
