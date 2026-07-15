"""Tests for the PS-vs-RC line-stream comparator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from c2.commands.line_compare import (
    SIDECAR_PATH,
    Transition,
    _check_order,
    _pair_by_offset,
    _ps_transitions,
    _rc_transitions,
    compare_function,
)


@pytest.fixture(scope="module")
def sidecar() -> dict:
    if not SIDECAR_PATH.exists():
        pytest.skip("RC line sidecar not present (run `c2 decomp-verify` once)")
    return json.loads(SIDECAR_PATH.read_text())


# --- Direction check (the core smell) ----------------------------------------

def test_both_streams_forward_is_clean() -> None:
    paired = [
        (Transition(0, 100), Transition(0, 200)),
        (Transition(5, 101), Transition(5, 201)),
        (Transition(10, 102), Transition(10, 202)),
    ]
    assert _check_order(paired) == []


def test_both_streams_backward_is_clean() -> None:
    # Both sides going BACKWARD at the same offset is fine -- the compiler
    # reordered the same way on both sides (e.g. Watcom peephole haul-up).
    paired = [
        (Transition(0, 100), Transition(0, 200)),
        (Transition(5, 102), Transition(5, 202)),  # forward
        (Transition(10, 101), Transition(10, 201)),  # both backward
    ]
    assert _check_order(paired) == []


def test_divergent_direction_is_smell() -> None:
    # PS forward, RC backward at the same paired offset -> smell.
    paired = [
        (Transition(0, 100), Transition(0, 200)),
        (Transition(5, 101), Transition(5, 202)),  # PS+, RC+
        (Transition(10, 102), Transition(10, 201)),  # PS+, RC- DIVERGE
    ]
    out = _check_order(paired)
    assert len(out) == 1
    assert out[0][0] == 10


def test_divergent_direction_other_way() -> None:
    # PS backward, RC forward at the same paired offset -> smell
    # (mirror case; tests the asymmetry).
    paired = [
        (Transition(0, 100), Transition(0, 200)),
        (Transition(5, 102), Transition(5, 201)),
        (Transition(10, 101), Transition(10, 202)),  # PS-, RC+ DIVERGE
    ]
    out = _check_order(paired)
    assert len(out) == 1


# --- Offset pairing ----------------------------------------------------------

def test_pair_by_offset_exact_match() -> None:
    ps = [Transition(0, 100), Transition(5, 101), Transition(10, 102)]
    rc = [Transition(0, 200), Transition(5, 201), Transition(10, 202)]
    paired, ps_only, rc_only, misaligned = _pair_by_offset(ps, rc)
    assert len(paired) == 3
    assert ps_only == []
    assert rc_only == []
    assert misaligned == []


def test_pair_by_offset_near_miss() -> None:
    # RC transition shifted by 2 bytes -> within window=4, paired as misaligned.
    ps = [Transition(0, 100), Transition(5, 101)]
    rc = [Transition(0, 200), Transition(7, 201)]
    paired, ps_only, rc_only, misaligned = _pair_by_offset(ps, rc, window=4)
    assert len(paired) == 2
    assert len(misaligned) == 1
    assert misaligned[0] == (5, 7)


def test_pair_by_offset_no_counterpart() -> None:
    # RC has an extra transition with no PS partner within window.
    ps = [Transition(0, 100)]
    rc = [Transition(0, 200), Transition(50, 201)]
    paired, ps_only, rc_only, misaligned = _pair_by_offset(ps, rc, window=4)
    assert len(paired) == 1
    assert ps_only == []
    assert len(rc_only) == 1
    assert rc_only[0].rel_offset == 50


# --- End-to-end on a known clean function ------------------------------------

def test_compare_clean_function(sidecar: dict) -> None:
    # `battle_action`: documented clean candidate -- same transition count
    # at the same byte offsets, no direction divergence.  If the corpus
    # drifts and this stops being clean, swap in another from
    # `c2 line-compare --json | jq '.[] | select(.is_clean)'`.
    if "battle_action" not in sidecar:
        pytest.skip("battle_action not in sidecar (corpus shifted)")
    r = compare_function("battle_action", sidecar["battle_action"]["file"])
    assert r.ps_count > 0
    assert r.rc_count > 0
    assert r.is_clean


# --- End-to-end on the documented OOO outlier --------------------------------

# (formerly tested choose_odd_tune as the OOO outlier; the original source
# order was recovered after the line-compare diagnosis, so the function is
# now clean.  See pcsound.c::choose_odd_tune for the recovered order and the
# explanatory comment.)


# --- PS transitions are sourced from PS.EXE only ----------------------------

def test_ps_transitions_use_ps_disasm() -> None:
    # Sanity: PS transitions come from disasm_function(), which reads data/PS.EXE.
    ps, fn_start = _ps_transitions("clear_arrow")
    assert fn_start == 0x2AFA1
    assert ps  # at least one transition
    # Every transition has a valid rel_offset and a positive PS-source line.
    for t in ps:
        assert t.rel_offset >= 0
        assert t.line > 0
