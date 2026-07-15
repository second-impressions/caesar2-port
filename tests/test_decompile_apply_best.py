"""Tests for the apply-best shape comparison + sweep helpers.

The orchestrator's auto-apply hook and the ``c2 decompile-apply-best``
CLI both call :func:`c2.decompile.apply_best.compare_shapes` to decide
whether a candidate run is apply-worthy.  These tests pin its
behaviour: byte-exact ALWAYS applies, shape-improvements (lex on the
4-layer vector) apply, ties+lower bytes apply, regressions and
literal ties do not.

Also covers :func:`collect_best_runs` -- the per-function "best of
many runs" selector used by the retroactive sweep CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from c2.decompile.apply_best import (
    BestRun,
    CompareVerdict,
    collect_best_runs,
    compare_shapes,
    is_apply_worthy,
    load_head_index,
)


# ── compare_shapes ───────────────────────────────────────────────────────


def _agent_best(*, byte_diff: int, ir: int, width: int, spill: int, seat: int,
                 ir_total: int = 20, width_total: int = 20,
                 spill_total: int = 10, seat_total: int = 10) -> dict:
    """Synthesise an agent-side best/verify.json payload."""
    return {
        "byte_diff": byte_diff,
        "shape": {
            "ir": [ir, ir_total],
            "width": [width, width_total],
            "spill": [spill, spill_total],
            "seat": [seat, seat_total],
            "fix_next": "none",
        },
        "target": "watcom",
    }


def _head_entry(*, diff: int, ir: int, width: int, spill: int, seat: int) -> dict:
    """Synthesise a HEAD verify.json per-function payload."""
    return {
        "name": "test_fn",
        "diff_byte_count": diff,
        "shape_distance": {
            "ir": ir, "width": width, "spill": spill, "seat": seat,
            "fix_next": "none", "shape": ir + width + spill + seat,
        },
    }


def test_byte_exact_always_applies_even_if_shape_unknown():
    """byte_diff==0 short-circuits every other check."""
    cand = _agent_best(byte_diff=0, ir=0, width=0, spill=0, seat=0)
    assert compare_shapes(candidate_best=cand, head_entry=None) == \
        CompareVerdict.BYTE_EXACT
    assert is_apply_worthy(CompareVerdict.BYTE_EXACT)


def test_ir_layer_drop_is_apply_worthy():
    """A drop in the highest divergent layer (ir) wins regardless of
    what happens below."""
    cand = _agent_best(byte_diff=200, ir=2, width=5, spill=3, seat=8)
    head = _head_entry(diff=200, ir=5, width=0, spill=0, seat=0)
    v = compare_shapes(candidate_best=cand, head_entry=head)
    assert v == CompareVerdict.SHAPE_IMPROVED
    assert is_apply_worthy(v)


def test_lower_layer_drop_wins_when_higher_layers_tied():
    """If ir is tied, a width drop is enough."""
    cand = _agent_best(byte_diff=200, ir=3, width=2, spill=8, seat=8)
    head = _head_entry(diff=200, ir=3, width=4, spill=0, seat=0)
    assert compare_shapes(candidate_best=cand, head_entry=head) == \
        CompareVerdict.SHAPE_IMPROVED


def test_higher_layer_rise_loses_even_with_lower_layer_drop():
    """The lex order is strict: ir+1 NEVER beats a width/spill/seat
    drop -- per Hard Rule #3 (work the highest layer first)."""
    cand = _agent_best(byte_diff=200, ir=4, width=0, spill=0, seat=0)
    head = _head_entry(diff=200, ir=3, width=5, spill=5, seat=5)
    v = compare_shapes(candidate_best=cand, head_entry=head)
    assert v == CompareVerdict.REGRESSED_SHAPE
    assert not is_apply_worthy(v)


def test_byte_drop_at_tied_shape_is_apply_worthy():
    """Shape identical -> byte diff is the tiebreaker (regalloc tie-break rung)."""
    cand = _agent_best(byte_diff=120, ir=2, width=1, spill=0, seat=1)
    head = _head_entry(diff=200, ir=2, width=1, spill=0, seat=1)
    v = compare_shapes(candidate_best=cand, head_entry=head)
    assert v == CompareVerdict.BYTES_IMPROVED_SAME_SHAPE
    assert is_apply_worthy(v)


def test_byte_rise_at_tied_shape_does_not_apply():
    cand = _agent_best(byte_diff=300, ir=2, width=1, spill=0, seat=1)
    head = _head_entry(diff=200, ir=2, width=1, spill=0, seat=1)
    v = compare_shapes(candidate_best=cand, head_entry=head)
    assert v == CompareVerdict.REGRESSED_BYTES
    assert not is_apply_worthy(v)


def test_exact_tie_returns_same():
    cand = _agent_best(byte_diff=200, ir=2, width=1, spill=0, seat=1)
    head = _head_entry(diff=200, ir=2, width=1, spill=0, seat=1)
    assert compare_shapes(candidate_best=cand, head_entry=head) == \
        CompareVerdict.SAME
    assert not is_apply_worthy(CompareVerdict.SAME)


def test_no_head_data_returns_no_head_data():
    cand = _agent_best(byte_diff=200, ir=2, width=1, spill=0, seat=1)
    v = compare_shapes(candidate_best=cand, head_entry=None)
    # Non-byte-exact + no HEAD reference -> cannot prove improvement
    # -> do NOT apply (safer than guessing).
    assert v == CompareVerdict.NO_HEAD_DATA
    assert not is_apply_worthy(v)


def test_no_candidate_shape_returns_no_candidate_data():
    cand = {"byte_diff": 200, "target": "watcom"}  # no "shape"
    head = _head_entry(diff=200, ir=2, width=1, spill=0, seat=1)
    assert compare_shapes(candidate_best=cand, head_entry=head) == \
        CompareVerdict.NO_CANDIDATE_DATA


# ── collect_best_runs ────────────────────────────────────────────────────


def _make_run(runs_root: Path, fn: str, *, slug: str,
              shape: tuple[int, int, int, int], byte_diff: int) -> Path:
    """Build a minimal agent-run dir on disk: best/verify.json,
    best/scratch.c, work/meta.json, work/scratch.c.  Returns the run
    dir."""
    rd = runs_root / f"{slug}"
    (rd / "best").mkdir(parents=True)
    (rd / "work").mkdir()
    (rd / "best" / "verify.json").write_text(json.dumps({
        "byte_diff": byte_diff,
        "shape": {
            "ir": [shape[0], 20], "width": [shape[1], 20],
            "spill": [shape[2], 10], "seat": [shape[3], 10],
            "fix_next": "none",
        },
        "target": "watcom",
    }))
    (rd / "best" / "scratch.c").write_text(f"// best for {fn}\n")
    (rd / "work" / "meta.json").write_text(json.dumps({
        "function": fn, "source_file": "test.c",
    }))
    (rd / "work" / "scratch.c").write_text(f"// work for {fn}\n")
    return rd


def test_collect_best_runs_picks_lowest_shape_vec(tmp_path):
    """When the same function has several runs, the BEST (lex-lowest
    shape vector) wins."""
    runs = tmp_path / "runs"
    runs.mkdir()
    _make_run(runs, "foo", slug="foo-1", shape=(5, 0, 0, 0), byte_diff=200)
    rd_win = _make_run(runs, "foo", slug="foo-2", shape=(2, 5, 5, 5), byte_diff=400)
    _make_run(runs, "foo", slug="foo-3", shape=(5, 0, 0, 1), byte_diff=200)

    bests = collect_best_runs(runs)
    assert set(bests) == {"foo"}
    assert bests["foo"].run_dir == rd_win
    assert bests["foo"].shape_vec == (2, 5, 5, 5)


def test_collect_best_runs_tiebreaks_on_bytes(tmp_path):
    """Tied shape -> lower byte_diff wins."""
    runs = tmp_path / "runs"
    runs.mkdir()
    _make_run(runs, "bar", slug="bar-a", shape=(3, 2, 1, 0), byte_diff=300)
    rd_win = _make_run(runs, "bar", slug="bar-b", shape=(3, 2, 1, 0), byte_diff=150)
    _make_run(runs, "bar", slug="bar-c", shape=(3, 2, 1, 0), byte_diff=500)

    bests = collect_best_runs(runs)
    assert bests["bar"].run_dir == rd_win
    assert bests["bar"].byte_diff == 150


def test_collect_best_runs_ignores_malformed_dirs(tmp_path):
    """Dirs without best/ or work/ are silently skipped."""
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "noisy-1").mkdir()                # no best/ or work/
    (runs / "noisy-2" / "best").mkdir(parents=True)  # no work/
    _make_run(runs, "good", slug="good-1", shape=(1, 0, 0, 0), byte_diff=50)

    bests = collect_best_runs(runs)
    assert set(bests) == {"good"}


# ── load_head_index ──────────────────────────────────────────────────────


def test_load_head_index_missing_cache_returns_empty(tmp_path):
    """Empty dict for a project with no .c2-cache/verify.json -- the
    sweep then skips shape comparison (byte-exact wins still work)."""
    assert load_head_index(tmp_path) == {}


def test_load_head_index_indexes_by_name(tmp_path):
    cache = tmp_path / ".c2-cache"
    cache.mkdir()
    cache_file = cache / "verify.json"
    cache_file.write_text(json.dumps({
        "summary": {"exact": 2, "diff": 1, "compared": 3},
        "files": [],
        "functions": [
            {"name": "alpha", "diff_byte_count": 0,
             "shape_distance": {"ir": 0, "width": 0, "spill": 0, "seat": 0}},
            {"name": "beta",  "diff_byte_count": 12,
             "shape_distance": {"ir": 1, "width": 0, "spill": 0, "seat": 0}},
        ],
    }))
    idx = load_head_index(tmp_path)
    assert set(idx) == {"alpha", "beta"}
    assert idx["beta"]["diff_byte_count"] == 12
