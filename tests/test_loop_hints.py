"""Tests for the loop classifier (`c2.commands.loop_hints`)."""

from __future__ import annotations

import pytest

from c2.commands.disasm import disasm_function
from c2.commands.loop_hints import Loop, detect_loops


def _kind_of(fn: str) -> list[str]:
    _, _, lines = disasm_function(fn)
    return [lp.kind for lp in detect_loops(lines)]


# --- Canonical cases (one per kind) -------------------------------------------

def test_for_with_entry_jmp() -> None:
    # `clear_arrow`: classic `for(i=0; i<N; i++)` with init+entry-jmp+step+test
    # all on the for-header line.
    kinds = _kind_of("clear_arrow")
    assert kinds == ["for"]


def test_for_optimized_no_entry_jmp() -> None:
    # `setup_whole_screen_refresh`: `for(i=0; i<0x4b0; ...)` with the entry-jmp
    # elided (init+test trivially true at compile time).  Byte-ambiguous: also
    # matches `do { ...; i++; } while(i < N);`.
    kinds = _kind_of("setup_whole_screen_refresh")
    assert kinds == ["for_or_dowhile_step"]


def test_for_optimized_with_continues() -> None:
    # `clear_region_ferret_map`: deeply nested for-loop with multiple paths
    # back to the top.  Continues are tracked but not counted as separate loops.
    _, _, lines = disasm_function("clear_region_ferret_map")
    loops = detect_loops(lines)
    # Should detect a small number of loops, not one-per-back-edge.
    assert len(loops) <= 6


def test_while_test_at_top() -> None:
    # `get_text_pointer`: `while(word_count > 0)` and `while(*text_pointer < ' ')`
    # -- both test-at-top with unconditional back-edges.
    kinds = _kind_of("get_text_pointer")
    assert all(k == "while" for k in kinds), kinds


def test_while_with_post_increment_in_test() -> None:
    # `get_region_invasion_points`: `while(i++ < 20)` test-at-top with a
    # body-internal CONDITIONAL back-edge.  Detector must recognize the
    # top-test pattern even when the back-edge is conditional.
    kinds = _kind_of("get_region_invasion_points")
    assert "while" in kinds, kinds


# --- Reachability filter (Rule 42 tail-merge / Rule 125 hauled code) ----------

def test_tail_merge_donor_not_a_loop() -> None:
    # `move_figure`: switch-break cases collapse to a shared post-switch tail
    # via backward `jmp` -- looks like a loop but isn't.  Reachability filter
    # must reject these.
    _, _, lines = disasm_function("move_figure")
    loops = detect_loops(lines)
    # Source has no loops (just a switch); detector should find 0.
    assert loops == []


def test_tail_merge_donor_function_skipped() -> None:
    # `clear_unit`: 7-byte tail-merge donor.  Loop body lives in `clear_army`,
    # which is OUTSIDE this function's address range.  Detector finds 0.
    assert _kind_of("clear_unit") == []


# --- Cascade order (high-confidence checks win over weak ones) ---------------

def test_cascade_for_over_dowhile() -> None:
    # `select_a_unit`: real `for(figure_no = 1; figure_no < 0xc9; figure_no++)`.
    # The entry-jmp + step + line agreement must win over the weaker do-while
    # default.
    kinds = _kind_of("select_a_unit")
    assert kinds == ["for"]


def test_cascade_top_test_only_when_no_step() -> None:
    # `select_a_unit`: the loop body starts with a flag-setter + forward
    # conditional, which LOOKS like a top-test pattern.  The cascade must
    # NOT apply the top-test override when a real bottom-step exists.
    kinds = _kind_of("select_a_unit")
    assert kinds == ["for"]


# --- Continues dedup ---------------------------------------------------------

def test_continues_dedup_by_top() -> None:
    # A function with multiple back-edges to the same top should report ONE
    # loop with the `continues` count, not N separate loops.
    _, _, lines = disasm_function("act_about")
    loops = detect_loops(lines)
    # At least one detected loop should have continues > 0.
    assert any(lp.continues > 0 for lp in loops), loops


# --- API ---------------------------------------------------------------------

def test_loop_dataclass_fields() -> None:
    _, _, lines = disasm_function("clear_arrow")
    loops = detect_loops(lines)
    assert len(loops) == 1
    lp = loops[0]
    assert isinstance(lp, Loop)
    assert lp.kind == "for"
    assert lp.top > 0
    assert lp.test is not None and lp.test > lp.top
    assert lp.step is not None and lp.step > lp.top
    assert lp.entry_jmp is not None and lp.entry_jmp < lp.top
    assert lp.back_edge > lp.test
    assert lp.continues == 0
    assert not lp.ambiguous


def test_ambiguous_flag() -> None:
    _, _, lines = disasm_function("setup_whole_screen_refresh")
    loops = detect_loops(lines)
    assert len(loops) == 1
    assert loops[0].ambiguous
    assert loops[0].kind == "for_or_dowhile_step"
