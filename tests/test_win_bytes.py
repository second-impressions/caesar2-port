"""Tests for the CAESAR2.EXE (Windows MSVC) byte-verify engine (c2.win_bytes).

Fast unit tests cover the pure parsing/masking/alignment helpers.  The
container-backed compile+compare path is marked ``slow`` and skipped unless
the MSVC image is present.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest

from c2 import win_bytes as wb


# ── fast unit tests (no container) ────────────────────────────────────────────
def test_masked_find_exact_and_wildcard():
    hay = bytes.fromhex("deadbeef" "55aa" "cafebabe")
    # needle with a wildcard (mask) byte still matches
    needle = bytes.fromhex("55" "00")          # 2nd byte masked
    assert wb.masked_find(hay, needle, {1}) == [4]
    # no anchor / no match
    assert wb.masked_find(hay, bytes.fromhex("1234"), set()) == []


def test_masked_find_relocaware():
    # a DIR32-style 4-byte hole in the middle is wildcarded on both ends
    needle = bytes.fromhex("90" "deadbeef" "90")
    hay = bytes.fromhex("0000" "90" "11223344" "90" "0000")
    assert wb.masked_find(hay, needle, {1, 2, 3, 4}) == [2]


def test_struct_distance_insertion_is_cheap():
    a = ["mov", "add", "ret"]
    b = ["mov", "add", "push", "ret"]          # one inserted insn
    assert wb._struct_distance(a, b) == 1
    assert wb._struct_distance(a, a) == 0


def test_norm_op_wildcards_addresses_and_imms():
    assert wb._norm_op("dword ptr [0x515790], 0xffffffff") == "dword ptr [K], K"
    assert wb._norm_op("ecx, 0x64") == "ecx, K"
    # ebp displacement shape is preserved as K but the bracket stays
    assert "[ebp + K]" in wb._norm_op("eax, dword ptr [ebp + 8]")


def test_win_annotation_override(tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    (src / "demo.c").write_text(
        "// FUNCTION: C2 0x1234\n"
        "// WIN: 0x00deadbe\n"
        "int demo_fn(int a)\n{\n    return a;\n}\n")
    monkeypatch.setattr(wb, "SRC_DIR", src)
    wb.win_annotations.cache_clear()
    assert wb.win_annotations("demo")["demo_fn"] == 0x00DEADBE


def test_func_map_and_image_load():
    fm = wb.load_func_map()
    assert "choose_odd_tune" in fm
    assert fm["choose_odd_tune"].win_va > 0x400000
    img = wb.load_win_image()
    assert img.image_base == 0x400000
    assert img.text_va0 == 0x401000          # .text @ image_base + 0x1000
    assert len(img.text) > 0x80000           # ~841 KB of code


def test_tu_of_finds_definitions():
    assert wb.tu_of("totalXpercent") == "lib32"
    assert wb.tu_of("choose_odd_tune") == "pcsound"
    assert wb.tu_of("definitely_not_a_function_xyz") is None


# ── slow tests (need the MSVC container) ──────────────────────────────────────
def _msvc_available() -> bool:
    if not shutil.which("podman"):
        return False
    try:
        r = subprocess.run(["podman", "image", "exists", wb.MSVC_IMAGE], timeout=20)
        return r.returncode == 0
    except Exception:
        return False


pytestmark_slow = pytest.mark.skipif(
    not _msvc_available(), reason="MSVC 4.0 container not available")


@pytestmark_slow
@pytest.mark.slow
def test_compile_pcsound_yields_functions():
    ctu = wb.compile_tu("pcsound", cache=False)
    assert not ctu.errors
    names = {n for n, _s, _e in ctu.funcs}
    assert {"choose_odd_tune", "get_battle_mood"} <= names


@pytestmark_slow
@pytest.mark.slow
def test_known_compile_exact_functions_match_caesar2():
    # compile-exact tier == byte-exact vs CAESAR2.EXE
    for fn, tu in [("choose_odd_tune", "pcsound"), ("get_battle_mood", "pcsound")]:
        v = wb.verify_func(fn, tu)
        assert v.status == "exact", (fn, v)


@pytestmark_slow
@pytest.mark.slow
def test_totalxpercent_shape_recovery_is_msvc_exact():
    # the committed two-statement shape (d9e1deab) must stay CAESAR2-exact
    assert wb.verify_func("totalXpercent", "lib32").status == "exact"


# ── cache engine (c2.win_verify_cache) -- fast, no container needed ──────────
from c2 import win_verify_cache as wvc


def test_verdict_to_row_shape():
    v = wb.FuncVerdict("demo", "lib32", "diff", 100, 12, 3, 40,
                       0x401000, "annotation", 0x401000)
    row = wvc.verdict_to_row(v)
    assert row == {"name": "demo", "tu": "lib32", "status": "diff",
                   "size": 100, "byte_diff": 12, "struct_diff": 3,
                   "insn_total": 40, "win_va": 0x401000,
                   "confidence": "annotation", "located_va": 0x401000}


def test_stale_tus_no_cache_is_full(tmp_path, monkeypatch):
    # point at an empty src dir -> all_tus empty, but staleness says full
    monkeypatch.setattr(wvc, "SRC_DIR", tmp_path)
    (tmp_path / "_skip.c").write_text("")  # underscore-prefixed is skipped
    tus, full = wvc.stale_tus(None)
    assert full is True
    assert "_skip" not in tus


def test_stale_tus_header_change_forces_full(tmp_path, monkeypatch):
    src = tmp_path / "src"; src.mkdir()
    inc = tmp_path / "include"; inc.mkdir()
    (src / "a.c").write_text(""); (src / "b.c").write_text("")
    (inc / "h.h").write_text("")
    monkeypatch.setattr(wvc, "SRC_DIR", src)
    monkeypatch.setattr(wvc, "INC_DIR", inc)
    base = wvc.src_mtimes()
    # cache fresh for both src + the header
    cache = {"src_mtimes": dict(base), "functions": []}
    tus, full = wvc.stale_tus(cache)
    assert full is False and tus == set()
    # bump the header mtime -> full rebuild
    import os, time
    os.utime(str(inc / "h.h"), (time.time() + 5, time.time() + 5))
    tus, full = wvc.stale_tus(cache)
    assert full is True


def test_stale_tus_incremental_one_tu(tmp_path, monkeypatch):
    src = tmp_path / "src"; src.mkdir()
    (src / "a.c").write_text(""); (src / "b.c").write_text("")
    monkeypatch.setattr(wvc, "SRC_DIR", src)
    inc = tmp_path / "include"; inc.mkdir()
    monkeypatch.setattr(wvc, "INC_DIR", inc)
    base = wvc.src_mtimes()
    cache = {"src_mtimes": dict(base), "functions": []}
    import os, time
    os.utime(str(src / "a.c"), (time.time() + 5, time.time() + 5))
    tus, full = wvc.stale_tus(cache)
    assert full is False and tus == {"a"}


def test_assemble_and_file_summary(tmp_path, monkeypatch):
    # all_tus() picks up SRC_DIR; point at a tiny fake tree.
    src = tmp_path / "src"; src.mkdir()
    inc = tmp_path / "include"; inc.mkdir()
    (src / "one.c").write_text(""); (src / "two.c").write_text("")
    monkeypatch.setattr(wvc, "SRC_DIR", src)
    monkeypatch.setattr(wvc, "INC_DIR", inc)
    rows = {
        "one": [wvc.verdict_to_row(wb.FuncVerdict("f1", "one", "exact", 10)),
                wvc.verdict_to_row(wb.FuncVerdict("f2", "one", "diff", 20,
                                                  5, 2, 8))],
        "two": [wvc.verdict_to_row(wb.FuncVerdict("g1", "two", "nomap", 4))],
    }
    cache = wvc._assemble(rows, {})
    assert cache["summary"]["exact"] == 1
    assert cache["summary"]["diff"] == 1
    assert cache["summary"]["nomap"] == 1
    assert cache["files"]["one"]["exact"] == 1
    assert cache["files"]["one"]["diff"] == 1
    assert cache["files"]["two"]["nomap"] == 1
    assert {r["name"] for r in cache["functions"]} == {"f1", "f2", "g1"}
    # the TU order in `functions` follows all_tus() (sorted)
    assert [r["tu"] for r in cache["functions"]] == ["one", "one", "two"]
