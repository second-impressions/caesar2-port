"""Unit tests for c2.bisect (the dossier bisect-baseline cache + delta block).

These tests exercise the renderer formatting and cache I/O.  They do NOT
build the project (that's an integration concern); the per-SHA build
path is covered manually in the dossier integration when the cache
misses.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from c2 import bisect as bs


# ── delta block ──────────────────────────────────────────────────────


def test_delta_clean_wt():
    lines = bs.format_delta_block(
        "foo", "deadbeef12345678", baseline=None, current=None, dirty=False)
    assert len(lines) == 1
    assert "clean working tree" in lines[0]
    assert "deadbeef" in lines[0]


def test_delta_dirty_progress():
    base = {"byte_diff": 580, "first_diff": 0x5,
            "shape": {"ir": 21, "width": 0, "spill": 4, "seat": 1}}
    cur = {"byte_diff": 543, "first_diff": 0x150,
           "shape": {"ir": 18, "width": 0, "spill": 4, "seat": 1}}
    lines = bs.format_delta_block("foo", "deadbeef", base, cur, dirty=True)
    text = "\n".join(lines)
    assert "+uncommitted edits" in text
    # shape-first: the judge metric is surfaced, the byte count is not.
    assert "ir 21" in text and "ir 18" in text
    assert "580b" not in text and "543b" not in text
    assert "-3 divergent line(s)" in text           # shape progress
    assert "judge metric" in text                     # shape is the judge
    assert "+0x14b prefix gained" in text


def test_delta_dirty_regression():
    base = {"byte_diff": 580, "first_diff": 0x150,
            "shape": {"ir": 18, "width": 0, "spill": 4, "seat": 1}}
    cur = {"byte_diff": 620, "first_diff": 0x10,
           "shape": {"ir": 25, "width": 0, "spill": 4, "seat": 1}}
    lines = bs.format_delta_block("foo", "deadbeef", base, cur, dirty=True)
    text = "\n".join(lines)
    # shape worsened (ir 18 -> 25): the per-function judge went the wrong way.
    assert "+7 divergent line(s)" in text
    assert "ir 18" in text and "ir 25" in text
    assert "regressed" in text or "-" in text


def test_delta_dirty_all_clean_now():
    """Edit drove the function to byte-exact: WT first_diff is None."""
    base = {"byte_diff": 580, "first_diff": 0x5,
            "shape": {"ir": 21, "width": 0, "spill": 4, "seat": 1}}
    cur = {"byte_diff": 0, "first_diff": None,
           "shape": {"ir": 0, "width": 0, "spill": 0, "seat": 0}}
    lines = bs.format_delta_block("foo", "deadbeef", base, cur, dirty=True)
    text = "\n".join(lines)
    # byte count is not surfaced; the shape row shows the converging-to-0
    # judge metric, and first-diff reports ALL CLEAN.
    assert "580b" not in text
    assert "ir 21" in text and "ir 0" in text
    assert "ALL CLEAN" in text


def test_delta_no_baseline():
    """HEAD has no version of this fn (new function)."""
    cur = {"byte_diff": 100, "first_diff": 0x20,
           "shape": {"ir": 5, "width": 0, "spill": 0, "seat": 1}}
    lines = bs.format_delta_block(
        "foo", "deadbeef", baseline=None, current=cur, dirty=True)
    text = "\n".join(lines)
    assert "baseline unavailable" in text


def test_delta_absent_baseline():
    """Cached sentinel: baseline build couldn't locate this fn."""
    base = {"absent": True, "byte_diff": None, "first_diff": None, "shape": None}
    cur = {"byte_diff": 100, "first_diff": 0x20,
           "shape": {"ir": 5, "width": 0, "spill": 0, "seat": 1}}
    lines = bs.format_delta_block("foo", "deadbeef", base, cur, dirty=True)
    text = "\n".join(lines)
    assert "baseline unavailable" in text


# ── cache I/O ────────────────────────────────────────────────────────


def test_cache_roundtrip(tmp_path, monkeypatch):
    """Cache reads/writes are tolerant and atomic."""
    monkeypatch.setattr(bs, "_BISECT_DIR", tmp_path / "bisect")
    # empty cache
    assert bs.load_cache("foo") == {}
    bs.save_cache("foo", {"abcdef": {"byte_diff": 100, "first_diff": 5,
                                     "shape": None, "ts": 1}})
    loaded = bs.load_cache("foo")
    assert "abcdef" in loaded
    assert loaded["abcdef"]["byte_diff"] == 100


def test_cache_corrupt_returns_empty(tmp_path, monkeypatch):
    """A malformed cache file is treated as empty (no exception)."""
    monkeypatch.setattr(bs, "_BISECT_DIR", tmp_path / "bisect")
    (tmp_path / "bisect").mkdir()
    (tmp_path / "bisect" / "foo.json").write_text("{ not valid json")
    assert bs.load_cache("foo") == {}


# ── helper formatters ────────────────────────────────────────────────


def test_fmt_offset():
    assert bs._fmt_offset(None) == "—"
    assert bs._fmt_offset(0) == "+0x0"
    assert bs._fmt_offset(0x150) == "+0x150"
    # passthrough for pre-formatted strings
    assert bs._fmt_offset("+0xa5") == "+0xa5"


def test_fmt_shape_compact():
    assert bs._fmt_shape_compact(None) == "—"
    s = bs._fmt_shape_compact(
        {"ir": 21, "width": 2, "spill": 0, "seat": 1})
    assert "ir 21" in s
    assert "width 2" in s
    assert "seat 1" in s


# ── git helpers (smoke; needs a git checkout) ─────────────────────────


def test_current_sha_is_hexstring_or_none():
    sha = bs.current_sha()
    # in CI / dev box this is the project repo; could be None if not a repo
    if sha is not None:
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)


def test_is_dirty_empty_paths():
    assert bs.is_dirty([]) is False
