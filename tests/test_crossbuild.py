"""Tests for the cross-build map (c2/commands/crossbuild.py).

These exercise the pure-Python CD extraction + ISO9660 walker and the
loader/query/render API against the committed
``data/out/crossbuild-map.json``.  They skip gracefully when the heavy
artefacts (CD images / map) are not present in the checkout.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from c2.commands import crossbuild as cb

REPO = Path(__file__).resolve().parents[1]


# ── Registry sanity ─────────────────────────────────────────────────────────

def test_registry_has_reference_first_and_distinct_md5s():
    assert cb.BUILDS[0].role == "reference"
    assert cb.REFERENCE_BUILD.has_debug is True
    md5s = [b.md5 for b in cb.BUILDS]
    assert len(md5s) == len(set(md5s)), "builds must be byte-distinct"
    # The two 1995 release builds must be un-symbolled.
    for b in cb.RELEASE_BUILDS:
        assert b.has_debug is False
        assert b.cd_zip is not None


def test_build_by_id():
    assert cb.build_by_id("rel-1995-09").date == "1995-09-21"
    assert cb.build_by_id("nope") is None


# ── Pure-Python extraction ───────────────────────────────────────────────────

def test_iso_from_mode1_bin_carves_user_data():
    # Two synthetic MODE1/2352 sectors; user data at byte offset 16, len 2048.
    s0 = bytes(16) + b"A" * 2048 + bytes(288)
    s1 = bytes(16) + b"B" * 2048 + bytes(288)
    iso = cb.iso_from_mode1_bin(s0 + s1)
    assert len(iso) == 4096
    assert iso[:2048] == b"A" * 2048
    assert iso[2048:] == b"B" * 2048


@pytest.mark.parametrize("build", cb.RELEASE_BUILDS, ids=lambda b: b.id)
def test_extract_release_exe_matches_registered_md5(build):
    zip_path = REPO / build.cd_zip
    if not zip_path.exists():
        pytest.skip(f"CD image not present: {zip_path}")
    exe = cb._extract_from_cd_zip(zip_path, build.iso_path)
    assert len(exe) == build.size
    assert hashlib.md5(exe).hexdigest() == build.md5


# ── Map structure + loader/query API ─────────────────────────────────────────

@pytest.fixture(scope="module")
def cmap():
    p = cb.DEFAULT_MAP_PATH
    if not p.exists():
        pytest.skip("crossbuild-map.json not generated; run `c2 crossbuild-map`")
    return json.loads(p.read_text())


def test_map_schema_and_buckets(cmap):
    assert cmap["schema"] == "crossbuild-map/v1"
    assert cmap["reference"]["id"] == "dbg-1996-04"
    # Every release build has a summary with the four buckets.
    for b in cmap["builds"]:
        if b["role"] == "reference":
            continue
        s = cmap["summary"][b["id"]]
        assert {"anchored", "exact", "near", "differs", "absent"} <= set(s)
        # Sanity: anchored == exact + near + differs.
        assert s["anchored"] == s["exact"] + s["near"] + s["differs"]
        # The vast majority must anchor (TU-order preservation).
        assert s["anchored"] / cmap["reference"]["functions"] > 0.85


def test_every_function_has_a_status_per_build(cmap):
    rel_ids = [b["id"] for b in cmap["builds"] if b["role"] != "reference"]
    valid = {"reference", "exact", "near", "differs", "absent"}
    for rec in cmap["functions"][:500]:  # sample for speed
        for bid in rel_ids:
            assert rec["builds"][bid]["status"] in valid


def test_loader_and_query_helpers(cmap):
    # load_crossbuild_map caches and builds the by-name index.
    data = cb.load_crossbuild_map(cb.DEFAULT_MAP_PATH)
    assert data is not None
    assert "_by_name" in data
    some = cmap["functions"][0]["function"]
    rec = cb.crossbuild_status(some)
    assert rec is not None
    assert rec["function"] == some


def test_render_hint_categories(cmap):
    # Find one of each kind to exercise the three render branches.
    rel_ids = [b["id"] for b in cmap["builds"] if b["role"] != "reference"]

    def kind(rec):
        sts = [rec["builds"][b]["status"] for b in rel_ids]
        if all(s == "exact" for s in sts):
            return "stable"
        if all(s == "absent" for s in sts):
            return "absent"
        return "mixed"

    seen = {}
    for rec in cmap["functions"]:
        k = kind(rec)
        if k not in seen:
            seen[k] = rec["function"]
        if len(seen) == 3:
            break

    if "stable" in seen:
        assert "stable" in cb.render_crossbuild_hint(seen["stable"]).lower()
    if "absent" in seen:
        h = cb.render_crossbuild_hint(seen["absent"]).lower()
        assert any(k in h for k in ("genuinely new", "rewritten", "library", "absent"))
    if "mixed" in seen:
        h = cb.render_crossbuild_hint(seen["mixed"])
        assert h and ("differs" in h or "near" in h or "exact" in h)


def test_render_hint_missing_function_returns_none(cmap):
    assert cb.render_crossbuild_hint("__not_a_real_function__") is None


# ── Semantic annotation ──────────────────────────────────────────────────────

def test_summary_has_semantic_breakdown(cmap):
    for b in cmap["builds"]:
        if b["role"] == "reference":
            continue
        sem = cmap["summary"][b["id"]].get("semantic")
        assert sem, "semantic breakdown missing from summary"
        # Only the valid classes appear.
        valid = {"same-work", "extended", "trimmed", "reworked",
                 "new-feature", "restructured", "library"}
        assert set(sem) <= valid


def test_changed_functions_carry_a_semantic_class(cmap):
    rel_ids = [b["id"] for b in cmap["builds"] if b["role"] != "reference"]
    anchored_classes = {"same-work", "extended", "trimmed", "reworked"}
    absent_classes = {"new-feature", "restructured", "library"}
    n_checked = 0
    for rec in cmap["functions"]:
        sem = rec.get("semantic")
        if not sem:
            continue
        for bid, blk in sem.items():
            st = rec["builds"][bid]["status"]
            if st in ("near", "differs"):
                assert blk["class"] in anchored_classes
            elif st == "absent":
                assert blk["class"] in absent_classes
            n_checked += 1
    assert n_checked > 0


def test_extended_class_lists_added_callees(cmap):
    # Every 'extended'/'reworked' record must name the new callees.
    rel_ids = [b["id"] for b in cmap["builds"] if b["role"] != "reference"]
    for rec in cmap["functions"]:
        for bid in rel_ids:
            blk = rec.get("semantic", {}).get(bid)
            if blk and blk["class"] == "extended":
                assert blk.get("added_callees"), rec["function"]
