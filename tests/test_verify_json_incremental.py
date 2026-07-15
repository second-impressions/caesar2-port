"""Tests for the incremental verify-cache merge (verify_json)."""
from __future__ import annotations

import json

from c2.commands import verify_json as vj


def _exact(name, file, *, size=10):
    return {"name": name, "address": "0x1", "file": file, "size": size,
            "recomp_size": size, "size_differs": False, "diff_byte_count": 0,
            "exact": True}


def _diff(name, file, *, size=20, diff=5):
    return {"name": name, "address": "0x2", "file": file, "size": size,
            "recomp_size": size, "size_differs": False,
            "diff_byte_count": diff}


def _bucket(*, exact=0, diff=0, byte_diff=0, compared=0,
            efb=0, dfb=0, cfb=0, not_found=0, stub=0):
    return {"exact": exact, "diff": diff, "byte_diff": byte_diff,
            "not_found": not_found, "stub_skipped": stub, "compared": compared,
            "exact_func_bytes": efb, "diff_func_bytes": dfb,
            "compared_func_bytes": cfb}


def _doc(funcs, files):
    return {"summary": vj._recompute_summary(files, funcs),
            "files": files, "functions": funcs}


def test_merge_replaces_changed_keeps_rest():
    old = _doc(
        funcs=[_exact("a", "decomp/src/x.c"),
               _diff("b", "decomp/src/x.c"),
               _exact("c", "decomp/src/y.c")],
        files={"decomp/src/x.c": _bucket(exact=1, diff=1, byte_diff=5,
                                         compared=2, efb=10, dfb=20, cfb=30),
               "decomp/src/y.c": _bucket(exact=1, compared=1, efb=10, cfb=10)},
    )
    # x.c changed: b is now exact, a now diffs, plus a new function d.
    sub = {
        "files": {"decomp/src/x.c": _bucket(exact=2, diff=1, byte_diff=7,
                                            compared=3, efb=20, dfb=20, cfb=40)},
        "functions": [_diff("a", "decomp/src/x.c", diff=7),
                      _exact("b", "decomp/src/x.c"),
                      _exact("d", "decomp/src/x.c")],
    }
    merged = vj._merge_docs(old, sub, {"decomp/src/x.c"})

    names = {f["name"]: f for f in merged["functions"]}
    # y.c untouched
    assert names["c"]["exact"] is True
    # x.c records replaced wholesale
    assert names["a"]["diff_byte_count"] == 7
    assert names["b"].get("exact") is True
    assert "d" in names
    assert len(merged["functions"]) == 4
    # bucket for x.c is the new one; y.c preserved
    assert merged["files"]["decomp/src/x.c"]["exact"] == 2
    assert merged["files"]["decomp/src/y.c"]["exact"] == 1


def test_merge_roundtrip_summary_consistency():
    """Splitting a doc and merging it back reproduces the same summary."""
    funcs = [_exact("a", "decomp/src/x.c"),
             _diff("b", "decomp/src/x.c", diff=5),
             _exact("c", "decomp/src/y.c"),
             _diff("d", "decomp/src/y.c", diff=9)]
    files = {
        "decomp/src/x.c": _bucket(exact=1, diff=1, byte_diff=5, compared=2,
                                  efb=10, dfb=20, cfb=30),
        "decomp/src/y.c": _bucket(exact=1, diff=1, byte_diff=9, compared=2,
                                  efb=10, dfb=20, cfb=30),
    }
    ref = _doc(funcs, files)
    sub = {"files": {"decomp/src/x.c": files["decomp/src/x.c"]},
           "functions": [f for f in funcs if f["file"] == "decomp/src/x.c"]}
    merged = vj._merge_docs(ref, sub, {"decomp/src/x.c"})
    assert merged["summary"] == ref["summary"]


def test_recompute_summary_subbreakdowns():
    funcs = [
        {"name": "p", "file": "f.c", "exact": True, "diff_byte_count": 0,
         "trailing_pad_diff": 2},
        {"name": "q", "file": "f.c", "exact": True, "diff_byte_count": 0,
         "donor_flip_diff": 3},
        {"name": "r", "file": "f.c", "exact": True, "diff_byte_count": 0,
         "rule4_swap_diff": 1},
    ]
    files = {"f.c": _bucket(exact=3, compared=3)}
    s = vj._recompute_summary(files, funcs)
    assert s["trailing_pad"] == 1
    assert s["donor_flip"] == 1
    assert s["rule4_swap"] == 1
    assert s["exact"] == 3


def test_incremental_bails_on_header_change(tmp_path, monkeypatch):
    """A header change must force a full rebuild (return None)."""
    cache = tmp_path / "verify.json"
    cache.write_text(json.dumps(_doc([], {})))
    cache_mtime = cache.stat().st_mtime

    monkeypatch.setattr(vj, "_changed_sources",
                        lambda since: ([tmp_path / "x.c"], [tmp_path / "h.h"]))
    # _run_verify_json must NOT be called when a header changed.
    monkeypatch.setattr(vj, "_run_verify_json",
                        lambda *a, **k: (_ for _ in ()).throw(
                            AssertionError("should not rebuild")))
    assert vj._incremental_update(cache, cache_mtime, verbose=False) is None


def test_incremental_returns_cache_when_nothing_changed(tmp_path, monkeypatch):
    cache = tmp_path / "verify.json"
    doc = _doc([_exact("a", "x.c")], {"x.c": _bucket(exact=1, compared=1)})
    cache.write_text(json.dumps(doc))
    monkeypatch.setattr(vj, "_changed_sources", lambda since: ([], []))
    out = vj._incremental_update(cache, cache.stat().st_mtime, verbose=False)
    assert out == doc


def test_incremental_bails_on_scoped_failure(tmp_path, monkeypatch):
    """A transient scoped-pass failure must not escape -- return None."""
    cache = tmp_path / "verify.json"
    cache.write_text(json.dumps(_doc([], {})))
    import typer

    monkeypatch.setattr(vj, "SRC_DIR", tmp_path)
    # Many TUs so the "most TUs changed" fraction guard does NOT trip;
    # only ONE of them is reported as changed.
    for n in "vwxyz":
        (tmp_path / f"{n}.c").write_text("")
    monkeypatch.setattr(vj, "_changed_sources",
                        lambda since: ([tmp_path / "x.c"], []))

    def _boom(*a, **k):
        raise typer.Exit(1)
    monkeypatch.setattr(vj, "_run_verify_json", _boom)
    assert vj._incremental_update(cache, cache.stat().st_mtime,
                                  verbose=False) is None
