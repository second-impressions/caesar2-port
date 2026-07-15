"""Bisect baseline cache for ``c2 dossier``.

Provides per-function HEAD-baseline verify results so ``c2 dossier`` can show
the per-edit delta against HEAD.  The judge metric is the layered SHAPE
DISTANCE (ir/width/spill/seat), NOT the byte count; the byte diff is a
corpus-progress figure only and is not surfaced per function:

  shape:       HEAD ir 21  →  WT ir 18   (-3 divergent lines)     ← judge metric
  first-diff:  HEAD +0xa5  →  WT +0x150  (+0xab prefix gained)

The cache is keyed by (function_name, commit SHA).  Working tree state is NOT
cached -- it's computed fresh on each invocation by the regular verify pipeline.
The baseline (HEAD's state) is computed once per (function, SHA) and reused.

Storage:
  .c2-cache/bisect/<function>.json
    { "<sha>": {"byte_diff": N, "first_diff": "+0xa5",
                "shape": {ir,width,spill,seat}, "ts": ...}, ... }

The build dir per SHA lives under .c2-cache/bisect/builds/<sha>/ and is reused
across cache misses for the same SHA (~60s cold; ~0s cache hit).

Design choices (see chat history 2026-06-25):
  - Stateless from the agent's POV.  No start/stop.  Working tree IS the state.
  - HEAD-relative.  Commits advance the baseline; git diff IS the session log.
  - Baseline cache is regeneratable.  Safe to delete .c2-cache/bisect/.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

_BISECT_DIR = Path(".c2-cache/bisect")
_BISECT_BUILDS_DIR = _BISECT_DIR / "builds"
_BISECT_KEEP_LAST_N_SHAS = 5   # disk cap: ~5 * ~100MB build dirs


# ── git helpers ───────────────────────────────────────────────────────


def current_sha() -> Optional[str]:
    """Return the current HEAD SHA (full 40 chars), or None if not a git repo
    / no HEAD (initial commit before first commit)."""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip() or None


def is_dirty(paths: list[Path]) -> bool:
    """True if any of the given paths differs from HEAD (uncommitted edits).

    Pass ``[decomp/src, decomp/include]`` to detect agent edits.  Untracked
    files are ignored (they wouldn't affect HEAD's build anyway)."""
    if not paths:
        return False
    try:
        r = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"] + [str(p) for p in paths],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    # exit code 1 means there ARE differences; 0 means clean; >1 means error
    return r.returncode == 1


def head_file_paths(rel_dir: Path) -> list[str]:
    """Return list of files in HEAD under the given relative directory."""
    try:
        r = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD", str(rel_dir)],
            capture_output=True, text=True, timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    return [ln for ln in r.stdout.splitlines() if ln]


def show_at_head(rel_path: str) -> Optional[bytes]:
    """Return the bytes of ``rel_path`` at HEAD, or None if not in HEAD."""
    try:
        r = subprocess.run(
            ["git", "show", f"HEAD:{rel_path}"],
            capture_output=True, timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    return r.stdout


def materialize_head(decomp_dir: Path, dest: Path) -> bool:
    """Materialize HEAD's decomp/src and decomp/include into ``dest``.

    Creates ``dest/src/`` and ``dest/include/`` populated from ``git show
    HEAD:<path>`` for every committed file.  Returns True on success.

    Existing dest directory is wiped first (this is a fresh materialization).
    """
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    for sub in ("src", "include"):
        rel_root = decomp_dir / sub
        files = head_file_paths(rel_root)
        if not files:
            continue
        out_sub = dest / sub
        out_sub.mkdir(parents=True, exist_ok=True)
        for rel_path in files:
            blob = show_at_head(rel_path)
            if blob is None:
                continue
            # rel_path is e.g. "decomp/src/evolver.c"; we want
            # "<dest>/src/evolver.c"
            name = Path(rel_path).name
            (out_sub / name).write_bytes(blob)
    return True


# ── per-SHA build dir management ──────────────────────────────────────


def _sha_build_dir(sha: str) -> Path:
    """Persistent build dir for HEAD's source at this SHA."""
    return _BISECT_BUILDS_DIR / sha[:12]


def _evict_old_sha_dirs() -> None:
    """Keep only the N most recently used per-SHA build dirs."""
    if not _BISECT_BUILDS_DIR.exists():
        return
    dirs = sorted(
        (d for d in _BISECT_BUILDS_DIR.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime, reverse=True,
    )
    for d in dirs[_BISECT_KEEP_LAST_N_SHAS:]:
        shutil.rmtree(d, ignore_errors=True)


def _build_head_baseline(sha: str, decomp_dir: Path) -> Optional[Path]:
    """Build HEAD's source for the given SHA into a persistent per-SHA dir.

    Returns the build work dir (containing ``out.exe`` + ``out.map``) on
    success, None on build failure.

    Reuses an existing per-SHA build dir if its config matches and the
    cached out.exe is present.  This makes the second bisect call for the
    same SHA ~0s.
    """
    from c2.commands.decomp_verify import (
        _build_all_impl, PS_CFLAGS, _DEFAULT_IMAGE,
    )
    work_dir = _sha_build_dir(sha)
    # Always re-materialize source from HEAD (cheap, ~50 files; ensures
    # consistency if the build dir somehow drifted).
    src_root = work_dir / "_src"
    materialize_head(decomp_dir, src_root)

    # We need to point _build_all_impl at a persistent build dir.  The
    # easiest way: monkey-patch _BUILD_DIR ... but that's process-global.
    # Instead, run _build_all_impl with use_cache=True after temporarily
    # redirecting the build dir via the same env path the module uses.
    # _build_all_impl doesn't take a work-dir arg, so we override by
    # patching _BUILD_DIR for the call.
    from c2.commands import decomp_verify as _dv
    saved = _dv._BUILD_DIR
    _dv._BUILD_DIR = work_dir
    try:
        ok, _out, work = _build_all_impl(
            src_root / "src", src_root / "include",
            _DEFAULT_IMAGE, PS_CFLAGS, use_cache=True, timings=False,
        )
    finally:
        _dv._BUILD_DIR = saved
    if not ok:
        return None
    return work


# ── per-function baseline verify ──────────────────────────────────────


def _verify_function_at(name: str, out_exe: Path, out_map: Path,
                        symbols_json: Path) -> Optional[dict]:
    """Run the per-function verify against the given out.exe/out.map and
    return the slim baseline record.

    Returns ``{byte_diff, first_diff, shape: {ir,width,spill,seat,shape},
    prologue_pushes, prologue_sub}`` or None if the function isn't found.
    """
    from c2.commands.dossier import _ps_func_records, _rc_func_records
    from c2.commands.decomp_verify import (
        _compare_bytes, _load_le_code_and_fixups,
    )
    from c2.parsers.exe import parse_exe
    from c2.commands.fixups import parse_le_fixups

    ps = _ps_func_records(symbols_json, name)
    if ps is None:
        return None
    ps_start, ps_end, _mod, _file, _recs, ps_code = ps

    rc = _rc_func_records(out_exe, out_map, name)
    if rc is None:
        # Function not present in this baseline build (e.g. stub-only).
        return None
    rc_start, rc_end, _rc_file, _rc_recs, rc_code = rc

    # PS fixups
    _, _bw, le_ps = parse_exe(Path("data/PS.EXE"))
    ps_fm, _ = parse_le_fixups(
        Path("data/PS.EXE"), le_ps.le_offset, le_ps.page_size,
        le_ps.num_pages, le_ps.objects[0].num_pages,
        le_ps.objects[1].num_pages,
    )
    ps_fix: set[int] = set()
    for off in ps_fm:
        for k in range(4):
            ps_fix.add(off + k)
    # RC code + fixups from this build's out.exe (the FULL code image:
    # the verifier-identical recomp slice below may extend past the RC
    # function's own end when RC is smaller than PS)
    rc_full, rc_fix = _load_le_code_and_fixups(out_exe)

    func_size = len(ps_code)
    # VERIFIER-IDENTICAL slices: `recomp` is PS-SIZED (byte-diff
    # semantics unchanged even when the sizes differ) and the AUDIT
    # slice is bounded by the RC function's own end (the run ledger /
    # const audits must not leak the next function's bytes).  This
    # mirrors decomp_verify's per-function loop exactly.
    recomp_ps_sized = rc_full[rc_start: rc_start + func_size]
    # audit slice = min(PS size, RC extent) -- the verifier's
    # _rc_func_size clamps to the PS size as an upper bound.
    recomp_audit = rc_code[:func_size]

    n = min(len(ps_code), len(recomp_ps_sized))
    diffs = _compare_bytes(
        ps_code[:n], recomp_ps_sized[:n], ps_start, rc_start,
        ps_fix, rc_fix,
    )
    bdiff = len(diffs)
    if len(ps_code) != len(recomp_ps_sized):
        bdiff += abs(len(ps_code) - len(recomp_ps_sized))
    first_diff = diffs[0] if diffs else None

    # Shape distance -- THE SHARED IMPLEMENTATION (identical code path
    # to `c2 decomp-verify` and the c2-decompile engine):
    # _recon_bundle_for_json with the dual-marks run ledger feeding the
    # ir layer (attribution-exact).  The old bisect-local computation
    # used the byte-diff-aligned binir count, which drifts past the
    # first length-changing diff and could report ir IMPROVING while
    # the verifier's ir worsened (the 2026-07-09 contradiction report).
    sd = None
    try:
        from c2.commands.decomp_verify import _recon_bundle_for_json
        from c2.commands.oracle import _load_oracle_line_lookup
        lm = {r["offset"]: r["line"] for r in _recs}
        try:
            rc_lm = _load_oracle_line_lookup(out_exe)
        except Exception:
            rc_lm = {r["offset"]: r["line"] for r in _rc_recs}
        sd = _recon_bundle_for_json(
            ps_code, ps_start, recomp_ps_sized, rc_start,
            ps_fix, rc_fix, lm, bdiff,
            recomp_line_map=rc_lm or None,
            recomp_audit=recomp_audit,
        )["shape_distance"]
    except Exception:  # noqa: BLE001
        pass

    return {
        "byte_diff": bdiff,
        "first_diff": first_diff,
        "shape": sd,
        "ps_size": ps_end - ps_start,
        "rc_size": rc_end - rc_start,
    }


# ── public cache API ──────────────────────────────────────────────────


def _cache_path(name: str) -> Path:
    _BISECT_DIR.mkdir(parents=True, exist_ok=True)
    return _BISECT_DIR / f"{name}.json"


#: Bump when the SHAPE computation feeding the cached baselines changes.
#: v3 (2026-07-09; v2 was a mid-fix dev state): dossier's ir layer switched from the byte-diff-aligned
#: binir count (approximate on drifting diffs -- reported ir IMPROVING
#: while decomp-verify's ledger-based ir worsened) to the shared
#: _recon_bundle_for_json ledger path, the same implementation
#: decomp-verify and the c2-decompile engine use.  Old-version caches are
#: dropped wholesale (mixed-method HEAD-vs-WT deltas would be garbage).
_CACHE_VERSION = 3


def load_cache(name: str) -> dict:
    p = _cache_path(name)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}
    if data.get("_v") != _CACHE_VERSION:
        return {}
    return {k: v for k, v in data.items() if k != "_v"}


def save_cache(name: str, data: dict) -> None:
    p = _cache_path(name)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({**data, "_v": _CACHE_VERSION}, indent=2))
    tmp.replace(p)


def get_baseline(name: str, sha: Optional[str] = None,
                 decomp_dir: Optional[Path] = None,
                 symbols_json: Optional[Path] = None,
                 force: bool = False) -> Optional[dict]:
    """Return the baseline verify result for ``name`` at SHA (default HEAD).

    Computed lazily on cache miss: materializes HEAD's source, builds it
    (~60s cold, ~0s warm per SHA), verifies the target function, caches the
    slim result.  Returns None if SHA can't be determined, the build
    failed, or the function isn't in HEAD's source.
    """
    if sha is None:
        sha = current_sha()
    if sha is None:
        return None
    cache = load_cache(name)
    if not force and sha in cache:
        return cache[sha]
    if decomp_dir is None:
        decomp_dir = Path("decomp")
    if symbols_json is None:
        symbols_json = Path("data/out/symbols.json")

    work = _build_head_baseline(sha, decomp_dir)
    if work is None:
        return None
    out_exe = work / "out.exe"
    out_map = work / "out.map"
    if not (out_exe.exists() and out_map.exists()):
        return None
    record = _verify_function_at(name, out_exe, out_map, symbols_json)
    if record is None:
        # Function not in this baseline; cache a sentinel so we don't rebuild.
        record = {"absent": True, "byte_diff": None,
                  "first_diff": None, "shape": None,
                  "ps_size": None, "rc_size": None}
    record["ts"] = int(time.time())
    cache[sha] = record
    save_cache(name, cache)
    _evict_old_sha_dirs()
    return record


# ── current verify (light wrapper for the bisect view) ────────────────


def get_current(name: str, decomp_dir: Optional[Path] = None,
                symbols_json: Optional[Path] = None) -> Optional[dict]:
    """Return the working-tree verify result for ``name`` -- same shape as
    ``get_baseline`` but always fresh (uses the normal build cache so
    incremental builds are ~5s for one changed .c file)."""
    from c2.commands.decomp_verify import (
        _build_all, PS_CFLAGS, _DEFAULT_IMAGE,
    )
    if decomp_dir is None:
        decomp_dir = Path("decomp")
    if symbols_json is None:
        symbols_json = Path("data/out/symbols.json")
    src_dir = decomp_dir / "src"
    inc_dir = decomp_dir / "include"
    ok, _out, _work, out_exe, out_map = _build_all(
        src_dir, inc_dir, _DEFAULT_IMAGE, PS_CFLAGS, use_cache=True,
    )
    if not ok:
        return None
    return _verify_function_at(name, out_exe, out_map, symbols_json)


# ── delta rendering helpers ───────────────────────────────────────────


def _fmt_offset(off) -> str:
    if off is None:
        return "—"
    if isinstance(off, str):
        return off
    return f"+{int(off):#x}"


def _fmt_shape_compact(sd: Optional[dict]) -> str:
    if not sd:
        return "—"
    ir = sd.get("ir", 0)
    width = sd.get("width", 0)
    spill = sd.get("spill", 0)
    seat = sd.get("seat", 0)
    return f"ir {ir} · width {width} · spill {spill} · seat {seat}"


def format_delta_block(name: str, sha: Optional[str],
                       baseline: Optional[dict], current: Optional[dict],
                       dirty: bool) -> list[str]:
    """Return the lines of the bisect delta block (suitable for typer.echo).

    Two modes:
      - clean WT (no uncommitted edits): "clean vs HEAD" one-liner
      - dirty WT: three-row delta table (diff / first-diff / shape)
    """
    lines: list[str] = []
    short = sha[:8] if sha else "—"
    if not dirty:
        lines.append(f"   HEAD {short}   (clean working tree)")
        return lines
    if baseline is None or baseline.get("absent"):
        lines.append(
            f"   HEAD {short}   +uncommitted edits   "
            f"(baseline unavailable: HEAD has no version of this fn)")
        return lines
    if current is None:
        lines.append(f"   HEAD {short}   +uncommitted edits   "
                     "(current verify failed)")
        return lines

    b_fd = baseline.get("first_diff")
    c_fd = current.get("first_diff")
    if b_fd is not None and c_fd is not None:
        try:
            b_off = int(b_fd) if not isinstance(b_fd, str) else int(b_fd, 0)
            c_off = int(c_fd) if not isinstance(c_fd, str) else int(c_fd, 0)
            fd_delta = c_off - b_off
            if fd_delta == 0:
                fd_note = "unchanged"
            elif fd_delta > 0:
                fd_note = f"+{fd_delta:#x} prefix gained"
            else:
                fd_note = f"{fd_delta:#x} regressed"
        except (TypeError, ValueError):
            fd_note = ""
    elif c_fd is None and b_fd is not None:
        fd_note = "ALL CLEAN now!"
    elif c_fd is not None and b_fd is None:
        fd_note = "NEW divergence"
    else:
        fd_note = "—"

    sh_b = baseline.get("shape") or {}
    sh_c = current.get("shape") or {}
    ir_b, ir_c = sh_b.get("ir", 0), sh_c.get("ir", 0)
    ir_delta = ir_c - ir_b
    if ir_delta == 0:
        sh_note = "unchanged"
    elif ir_delta < 0:
        sh_note = f"{ir_delta:+d} divergent line(s)"
    else:
        sh_note = f"{ir_delta:+d} divergent line(s)"

    lines.append(f"   HEAD {short}   +uncommitted edits")
    lines.append(f"     shape:       HEAD {_fmt_shape_compact(sh_b)}  →  "
                 f"WT {_fmt_shape_compact(sh_c)}   ({sh_note})     ← judge metric")
    lines.append(f"     first-diff:  HEAD {_fmt_offset(b_fd)}  →  "
                 f"WT {_fmt_offset(c_fd)}   ({fd_note})")
    return lines
