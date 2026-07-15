"""Persistence tests for the corpus build-trace cache (update_cache/load_cache).

Regression: routines carry a cyclic IRForest object ("ir"); json.dumps on it
raised TypeError and the silently-caught failure kept the cache stale while
every consumer fell back to per-file container compiles.  update_cache must
strip the forest for the file and rebuild it for the returned/loaded dicts.
"""
import json

from c2 import regalloc as ra


def _parsed_with_forest():
    txt = "\n".join([
        "~WV1 nb aa 1 0 100 7",
        "~WV1 tl bb 3 aa 5 7",
        "~WV1 fb",
        "~WV1 fn",
        "~WV1 fc 0 0 0",
    ])
    from c2.regalloc.trace import parse
    td = parse(txt)
    r = td["routines"][0]
    assert r.get("ir") is not None, "fixture must carry a live IRForest"
    return {"cost_model": {"load_cost": 2}, "loop_base": 10,
            "by_func": {"f": r}}


def test_update_cache_strips_forest_and_rebuilds(tmp_path):
    cache = tmp_path / "regtrace.json"
    data = ra.update_cache(cache, _parsed_with_forest())
    # file written and JSON-valid (would have raised TypeError before the fix)
    on_disk = json.loads(cache.read_text())
    assert on_disk["v"] == ra._CACHE_VERSION
    assert "ir" not in on_disk["by_func"]["f"]
    assert "_ir_records" in on_disk["by_func"]["f"]
    # returned in-memory dict has the forest rebuilt
    assert data["by_func"]["f"].get("ir") is not None


def test_load_cache_rebuilds_forest(tmp_path):
    cache = tmp_path / "regtrace.json"
    ra.update_cache(cache, _parsed_with_forest())
    loaded = ra.load_cache(cache)
    assert loaded is not None
    assert loaded["by_func"]["f"].get("ir") is not None


def test_load_cache_rejects_stale_schema(tmp_path):
    cache = tmp_path / "regtrace.json"
    cache.write_text(json.dumps({"v": 1, "by_func": {}}))
    assert ra.load_cache(cache) is None
