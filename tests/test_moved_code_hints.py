"""Tests for the Rule 125 moved-code signature detector
(c2/commands/moved_code_hints.py).

These run against the real data/out/symbols.json + PS.EXE, like the
other hint-detector suites: the ground truth is the binary itself, and
the worked cases below are byte-verified (helping / act_help_icons
went byte-exact by following the hint).
"""

from __future__ import annotations

import pytest

from c2.commands.moved_code_hints import (
    detect,
    render,
    render_moved_code_hint,
    scan_all,
    to_json,
)


def test_helping_is_hauled():
    """helping's head was hauled to 0x32409 by CallRet+StraightenCode;
    its true source position is after act_about (lines 1684-1697)."""
    h = detect("helping")
    assert h is not None
    assert h.kind == "hauled"
    assert h.after_fn == "act_about"
    assert h.before_fn == "act_rewind_help"
    assert h.tail_line is not None and h.tail_line >= 1693
    assert h.kind == "hauled"
    # neighbourhood at the symbol position leaves no room for the body
    assert h.room < h.est_lines or h.room <= 3


def test_fade_to_palette_is_tail_consumed():
    """fade_to_palette jmps BACKWARD into go_16m_palette's line-covered
    BODY (L1045, mid-code, not an orphan region) — a normal Rule 42
    donor merge that consumed the line records.  Its source position is
    fine."""
    h = detect("fade_to_palette")
    assert h is not None
    assert h.kind == "tail-consumed"


def test_clear_unit_is_hauled_down():
    """clear_unit's 7-byte symbol range at 0x2AFBC is the hauled-DOWN
    head (remove_unit's tail call); the orphan body at 0x2AF82
    (L234/L235, preceded by clear_army's ret) pins the source position
    right after clear_army.  Byte-verified: reordering made clear_army,
    clear_unit, remove_unit, clear_unit_list all exact."""
    h = detect("clear_unit")
    assert h is not None
    assert h.kind == "hauled"
    assert h.after_fn == "clear_army"
    assert h.before_fn == "clear_figure"


def test_set_palette_is_relocated():
    """set_palette ends in ret (no trailing jmp to follow)."""
    h = detect("set_palette")
    assert h is not None
    assert h.kind == "relocated"


def test_normal_function_not_flagged():
    """A function with ordinary line records must not fire."""
    assert detect("move_army") is None
    assert detect("act_about") is None


def test_asm_functions_not_flagged():
    """.asm modules have no .c line neighbourhood — never flagged."""
    assert detect("_DC_16") is None


def test_scan_all_is_small_and_c_only():
    hints = scan_all()
    names = {h.name for h in hints}
    assert "helping" in names
    assert "fade_to_palette" in names
    # every flagged function is from a C TU
    assert all(h.file.endswith(".c") for h in hints)
    # the signature is rare — guard against detector regressions that
    # would flood it (corpus currently has 5)
    assert len(hints) < 20


def test_render_and_json():
    h = detect("helping")
    txt = render(h)
    assert "Rule 125" in txt and "act_about" in txt
    assert render_moved_code_hint("helping") == txt
    j = to_json(h)
    assert j["kind"] == "hauled"
    assert j["define_after"] == "act_about"
    assert to_json(None) is None


def test_func_order_exempts_moved_code():
    """helping is defined after act_about in decomp source (correct per
    Rule 125) — func-order must not report it as an inversion."""
    from c2.commands.func_order import _moved_code_names, _violations

    exempt = _moved_code_names()
    assert "helping" in exempt
    addr_of = {"act_help_game": 0x22404, "helping": 0x22409,
               "act_about": 0x22473, "act_rewind_help": 0x224F1}
    src_order = ["act_help_game", "act_about", "helping", "act_rewind_help"]
    assert _violations(addr_of, src_order, exempt={"helping"}) == []
    # without the exemption it WOULD be flagged (sanity)
    assert len(_violations(addr_of, src_order, exempt=set())) == 1
