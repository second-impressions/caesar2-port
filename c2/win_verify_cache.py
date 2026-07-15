"""Whole-tree cache for the Windows (``CAESAR2.EXE``) byte-verify path.

The structural mirror of ``.c2-cache/verify.json`` (the DOS/Watcom oracle):
a single JSON document at ``.c2-cache/win-verify.json`` recording, per
decompiled function, the MSVC-``/Od``-compile-vs-``CAESAR2.EXE`` verdict so
the sibling commands (``c2 win-verify``, ``c2 decomp-verify --target win``,
``c2 functions``) can read it without recompiling every time.

Per-function schema (the win analogue of the DOS row -- the win path has NO
shape/regalloc layers: ``/Od`` does no register allocation, so the layers
``ir/width/spill/seat`` do not apply; see
``docs/windows-dual-target-feasibility.md``)::

    {
      "name", "tu", "status",        # "exact" | "diff" | "nomap" | "absent"
      "size",                          # compiled .text size (B)
      "byte_diff",                     # raw masked byte diff at located va (ORACLE; 0 => exact)
      "struct_diff",                   # reloc/immediate-normed insn edit distance (WORKABLE)
      "insn_total", "win_va", "confidence", "located_va"
    }

Staleness: per-TU ``decomp/src/<tu>.c`` mtime + a full rebuild when any
``decomp/include/*.h`` changed (mirrors the DOS cache's header-rebuild rule).
Incremental: only the changed TUs are recompiled and their rows merged back.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Optional

from c2 import win_bytes as wb

CACHE_PATH = Path(".c2-cache/win-verify.json")
_REPO = Path(__file__).resolve().parent.parent
SRC_DIR = wb.SRC_DIR
INC_DIR = _REPO / "decomp" / "include"

# Skip the same DU/scratch files the command-path skips.
_SKIP_PREFIX = ("_",)


# ── verdict ↔ row ─────────────────────────────────────────────────────────────
def verdict_to_row(v: "wb.FuncVerdict") -> dict:
    """Win row (cached shape) for one ``FuncVerdict``."""
    return {
        "name": v.name,
        "tu": v.tu,
        "status": v.status,
        "size": int(v.size),
        "byte_diff": int(v.byte_diff),
        "struct_diff": int(v.struct_diff),
        "insn_total": int(v.insn_total),
        "win_va": v.win_va,
        "confidence": v.confidence,
        "located_va": v.located_va,
    }


# ── source-file mtimes (staleness) ────────────────────────────────────────────
def src_mtimes() -> dict[str, float]:
    """mtime map of every ``decomp/src/*.c`` + every ``decomp/include/*.h``.

    Used to decide which TUs are stale vs the cache.  A header change forces
    a full rebuild (every TU depends on the shared headers)."""
    m: dict[str, float] = {}
    for p in sorted(SRC_DIR.glob("*.c")):
        if p.stem.startswith(_SKIP_PREFIX):
            continue
        m[f"src/{p.name}"] = p.stat().st_mtime
    for p in sorted(INC_DIR.glob("*.h")):
        m[f"include/{p.name}"] = p.stat().st_mtime
    return m


def stale_tus(cache: Optional[dict], *, now: Optional[dict[str, float]] = None
              ) -> tuple[set[str], bool]:
    """Which TUs need recompiling, and whether a full rebuild is forced.

    Returns ``(tus, full)``: ``tus`` is the set of changed TU stems; ``full``
    is True when a header changed (or there is no cache, or the cache schema
    is unrecognised) -- caller should re-verify every TU."""
    cur = now or src_mtimes()
    if not cache or "functions" not in cache or "src_mtimes" not in cache:
        return {p.stem for p in SRC_DIR.glob("*.c")
                if not p.stem.startswith(_SKIP_PREFIX)}, True
    stored = cache.get("src_mtimes", {})
    for k, t in cur.items():
        if k.startswith("include/") and stored.get(k, 0) < t:
            return set(), True                       # header changed -> full
    changed = set()
    for k, t in cur.items():
        if k.startswith("src/") and stored.get(k, 0) < t:
            changed.add(Path(k).stem)
    return changed, False


# ── per-TU verify ──────────────────────────────────────────────────────────────
def verify_tu(tu: str, *, win: Optional["wb.WinImage"] = None,
              ctu: Optional["wb.CompiledTU"] = None,
              cb: Optional[Callable[["wb.FuncVerdict"], None]] = None
              ) -> tuple[list[dict], bool, Optional[str]]:
    """Compile + verify every function in one TU.

    Returns ``(rows, failed, error)``: ``rows`` are cache rows; ``failed`` is
    True when the TU did not compile (caller records ``failed_tu``); ``error``
    the first compile error line.  ``ctu`` may be passed to reuse an already-
    compiled TU."""
    win = win or wb.load_win_image()
    ctu = ctu or wb.compile_tu(tu)
    if ctu.errors:
        return [], True, ctu.errors[0]
    rows: list[dict] = []
    for name, _s, _e in ctu.funcs:
        v = wb.verify_func(name, tu, win=win, ctu=ctu)
        rows.append(verdict_to_row(v))
        if cb:
            cb(v)
    return rows, False, None


# ── whole-tree build (full or incremental) ─────────────────────────────────────
def all_tus() -> list[str]:
    """Every decomp src TU that ``win-verify`` compiles, sorted."""
    return sorted(p.stem for p in SRC_DIR.glob("*.c")
                  if not p.stem.startswith(_SKIP_PREFIX))


def _file_summary(rows: list[dict]) -> dict:
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    return {
        "exact": c.get("exact", 0),
        "diff": c.get("diff", 0),
        "nomap": c.get("nomap", 0),
        "absent": c.get("absent", 0),
        "failed_tu": 0,
        "compared": len(rows),
    }


def _summary(rows: list[dict], files: dict[str, dict]) -> dict:
    from collections import Counter
    c = Counter(r["status"] for r in rows)
    return {
        "exact": c.get("exact", 0),
        "diff": c.get("diff", 0),
        "nomap": c.get("nomap", 0),
        "absent": c.get("absent", 0),
        "failed_tu": sum(1 for f in files.values() if f.get("failed_tu")),
        "compared": len(rows),
    }


def _assemble(rows_by_tu: dict[str, list[dict]],
              failed: dict[str, str]) -> dict:
    files = {}
    for tu in all_tus():
        if tu in failed:
            files[tu] = {"exact": 0, "diff": 0, "nomap": 0, "absent": 0,
                         "failed_tu": 1, "compared": 0,
                         "error": failed[tu]}
        else:
            files[tu] = _file_summary(rows_by_tu.get(tu, []))
    all_rows = [r for tu in all_tus() for r in rows_by_tu.get(tu, [])]
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "image": wb.MSVC_IMAGE,
        "src_mtimes": src_mtimes(),
        "summary": _summary(all_rows, files),
        "files": files,
        "functions": all_rows,
    }


def build(tus: Optional[list[str]] = None, *,
          win: Optional["wb.WinImage"] = None,
          cb: Optional[Callable[["wb.FuncVerdict"], None]] = None) -> dict:
    """Verify ``tus`` (default: every TU) fresh; return the full cache dict.

    Does NOT read or merge any existing cache -- a clean full build."""
    tus = tus or all_tus()
    win = win or wb.load_win_image()
    rows_by_tu: dict[str, list[dict]] = {}
    failed: dict[str, str] = {}
    for tu in tus:
        rows, did_fail, err = verify_tu(tu, win=win,
                                        cb=(lambda v: cb(v) if cb else None))
        if did_fail:
            failed[tu] = err or "(unknown error)"
        else:
            rows_by_tu[tu] = rows
    return _assemble(rows_by_tu, failed)


def refresh(*, force: bool = False, win: Optional["wb.WinImage"] = None,
            cb: Optional[Callable[[str], None]] = None
            ) -> tuple[dict, bool]:
    """Refresh the cache incrementally; return ``(cache, refreshed)``.

    ``refreshed`` is True when any TU was recompiled this call (False means
    the cache was already up to date and was returned untouched).  When the
    cache is missing/stale-on-headers/``force``, do a full build."""
    existing = load()
    tus, full = stale_tus(existing) if not force else (all_tus(), True)
    if not full and not tus:
        return existing or {"summary": {}, "files": {}, "functions": []}, False
    win = win or wb.load_win_image()

    rows_by_tu: dict[str, list[dict]] = {}
    failed: dict[str, str] = {}

    if full or not existing:
        targets = all_tus()
        for tu in targets:
            if cb:
                cb(tu)
            rows, did_fail, err = verify_tu(tu, win=win)
            if did_fail:
                failed[tu] = err or "(unknown error)"
            else:
                rows_by_tu[tu] = rows
        cache = _assemble(rows_by_tu, failed)
    else:
        # Incremental: carry forward the non-stale TUs, re-verify the rest.
        by_tu: dict[str, list[dict]] = {}
        for r in existing.get("functions", []):
            by_tu.setdefault(r["tu"], []).append(r)
        failed = {tu: f["error"] for tu, f in existing.get("files", {}).items()
                  if f.get("failed_tu")}
        for tu in all_tus():
            if tu in tus:
                if cb:
                    cb(tu)
                rows, did_fail, err = verify_tu(tu, win=win)
                if did_fail:
                    failed[tu] = err or "(unknown error)"
                else:
                    rows_by_tu[tu] = rows
                    failed.pop(tu, None)
            else:
                rows_by_tu[tu] = by_tu.get(tu, [])
        cache = _assemble(rows_by_tu, failed)

    _write(cache)
    return cache, True


# ── load/save ──────────────────────────────────────────────────────────────────
def load() -> Optional[dict]:
    if not CACHE_PATH.exists():
        return None
    try:
        return json.loads(CACHE_PATH.read_text())
    except Exception:
        return None


def _write(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CACHE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cache, indent=1))
    tmp.replace(CACHE_PATH)


# ── lookups ───────────────────────────────────────────────────────────────────
def func_row(name: str) -> Optional[dict]:
    """Cached row for one function (no rebuild).  None if not in the cache."""
    cache = load()
    if not cache:
        return None
    for r in cache.get("functions", []):
        if r["name"] == name:
            return r
    return None


def func_row_or_verify(name: str, *, win: Optional["wb.WinImage"] = None,
                       ctu: Optional["wb.CompiledTU"] = None) -> dict:
    """Cached row for one function, verifying on a cache miss and writing
    the single row back (mirrors the DOS path's per-function cache-or-build)."""
    row = func_row(name)
    tu = wb.tu_of(name)
    if tu is None:
        return verdict_to_row(
            wb.FuncVerdict(name, "", "absent"))
    # cache hit only counts if the TU's .c mtime matches the stored one.
    cache = load() or {}
    stored = cache.get("src_mtimes", {})
    cur = src_mtimes()
    src_key = f"src/{tu}.c"
    if row is not None and stored.get(src_key, 0) >= cur.get(src_key, 0):
        return row
    # miss/stale: verify this one TU and merge just its rows back.
    win = win or wb.load_win_image()
    ctu = ctu or wb.compile_tu(tu)
    rows, _did_fail, _err = verify_tu(tu, win=win, ctu=ctu)
    # merge into the cache
    fresh = {r["name"]: r for r in rows}
    all_rows = [fresh.get(r["name"], r) if r["tu"] == tu else r
                for r in cache.get("functions", [])]
    for r in rows:
        if not any(x["name"] == r["name"] and x["tu"] == tu
                   for x in cache.get("functions", [])):
            all_rows.append(r)
    fresh_cache = dict(cache)
    fresh_cache["functions"] = all_rows
    fresh_cache["src_mtimes"] = cur
    fresh_cache["files"] = _recompute_files(all_rows, cache.get("files", {}), tu)
    fresh_cache["summary"] = _summary(all_rows, fresh_cache["files"])
    fresh_cache["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _write(fresh_cache)
    return fresh.get(name, verdict_to_row(
        wb.FuncVerdict(name, tu, "absent")))


def _recompute_files(all_rows: list[dict], old_files: dict, tu: str) -> dict:
    """Recompute the per-TU summary for ``tu`` only (preserve others)."""
    files = dict(old_files)
    tu_rows = [r for r in all_rows if r["tu"] == tu]
    files[tu] = _file_summary(tu_rows)
    files[tu]["failed_tu"] = 0
    return files
