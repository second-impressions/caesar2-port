"""Shared helper: get the full ``decomp-verify --json`` document, cached.

Several analysis commands (``negative-corpus``, ``residue-cluster``, …) need
the complete per-function verify record — diff byte counts AND the structured
``rows`` / ``rule_hints`` / ``tail_merge`` / ``pragma_hint`` payload that only
the JSON mode emits.  Running the verifier is ~10-30 s, so this module:

  1. caches the document at ``.c2-cache/verify.json``,
  2. reuses the cache if it is newer than every ``decomp/src/*.c`` and
     ``decomp/include/*.h`` (the same staleness rule the sibling status
     cache uses), and
  3. otherwise regenerates it in-process via ``decomp_verify`` (so no
     subprocess / shell quoting), writing it back.

It deliberately does NOT depend on the older per-command snapshots
(``sibling-status.json`` only carries byte counts, not rows).  Callers that
just need ``{name: byte_diff}`` can still use the lighter sibling cache; this
one is for the full record.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
from typing import Optional

CACHE_PATH = Path(".c2-cache/verify.json")
SRC_DIR = Path("decomp/src")
INCLUDE_DIR = Path("decomp/include")


def _newest_src_mtime() -> float:
    """Newest mtime across decomp/src/*.c and decomp/include/*.h."""
    newest = 0.0
    for d, pat in ((SRC_DIR, "*.c"), (INCLUDE_DIR, "*.h")):
        if not d.exists():
            continue
        for f in d.glob(pat):
            try:
                m = f.stat().st_mtime
            except OSError:
                continue
            newest = max(newest, m)
    return newest


def _run_verify_json(c_files: Optional[list[Path]] = None) -> dict:
    """Run ``decomp-verify --json --no-strict`` in-process; return the doc.

    ``c_files`` scopes the per-function compare/render to those source
    files only (the build itself is always the full incremental wmake, so
    the recompiled bytes are correct for every function).  ``None`` = the
    full corpus.
    """
    from c2.commands.decomp_verify import decomp_verify
    import typer

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            decomp_verify(
                c_files=c_files,
                symbols_json=Path("data/out/symbols.json"),
                exe_path=Path("data/PS.EXE"),
                decomp_dir=Path("decomp"),
                json_out=True,
                strict=False,
                strict_warnings=False,
            )
        except typer.Exit as exc:
            if exc.exit_code not in (0, None):
                raise
    return json.loads(buf.getvalue())


def _safe_mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


def _changed_sources(since: float) -> tuple[list[Path], list[Path]]:
    """``(changed_c, changed_h)`` with mtime strictly newer than ``since``.

    Mirrors :func:`_newest_src_mtime`'s scope (``decomp/src/*.c`` +
    ``decomp/include/*.h``) so the staleness check and the incremental
    refresh always agree on *what* counts as a change.
    """
    cc = ([f for f in SRC_DIR.glob("*.c") if _safe_mtime(f) > since]
          if SRC_DIR.exists() else [])
    hh = ([f for f in INCLUDE_DIR.glob("*.h") if _safe_mtime(f) > since]
          if INCLUDE_DIR.exists() else [])
    return cc, hh


# Top-level ``summary`` count/byte fields that are exactly the sum of the
# per-file ``files`` buckets (so a merged doc can recompute them cleanly).
_SUMMARY_BUCKET_KEYS = (
    "exact", "diff", "byte_diff", "not_found", "stub_skipped", "compared",
    "exact_func_bytes", "diff_func_bytes", "compared_func_bytes",
)


def _recompute_summary(files: dict, funcs: list[dict]) -> dict:
    """Rebuild the ``summary`` block from merged ``files`` + ``functions``.

    The count/byte fields are the sum of the per-file buckets; the
    exact-with-note sub-breakdowns (donor-flip / Rule 4 / trailing-pad)
    are counted off the per-function records (they aren't tracked per
    bucket).
    """
    s = {k: sum(b.get(k, 0) for b in files.values())
         for k in _SUMMARY_BUCKET_KEYS}
    s["donor_flip"] = sum(1 for f in funcs if f.get("donor_flip_diff"))
    s["rule4_swap"] = sum(1 for f in funcs if f.get("rule4_swap_diff"))
    s["trailing_pad"] = sum(1 for f in funcs if f.get("trailing_pad_diff"))
    return s


def _merge_docs(old: dict, sub: dict, changed_rel: set[str]) -> dict:
    """Merge a scoped verify ``sub`` (only ``changed_rel`` files) into the
    cached full ``old`` document.  Records for the changed files are
    REPLACED wholesale; every other function/file is carried over."""
    funcs = [f for f in old.get("functions", [])
             if f.get("file") not in changed_rel]
    funcs.extend(f for f in sub.get("functions", [])
                 if f.get("file") in changed_rel)
    files = dict(old.get("files", {}))
    sub_files = sub.get("files", {})
    for rel in changed_rel:
        if rel in sub_files:
            files[rel] = sub_files[rel]
    return {"summary": _recompute_summary(files, funcs),
            "files": files, "functions": funcs}


# When (nearly) this fraction of TUs changed, a scoped pass costs about as
# much as the full one (the build is shared either way) -- so just rebuild.
_INCREMENTAL_MAX_FRACTION = 0.6


def _foreign_tail_merge_donors_changed(
    old: dict, changed_rel: set[str],
) -> bool:
    """Return True if a CHANGED file hosts a tail-merge donor that has
    dependents in an UNCHANGED file.

    A donor body edit rewrites the shared epilogue tail Watcom factored
    into every dependent that ``jmp``s into it -- including dependents in
    other TUs that the scoped re-verify does not recompile.  Their cached
    records would go stale (byte-diff / exact flag no longer reflect the
    rebuilt bytes), so the caller must bail to a full rebuild rather than
    merge a half-fresh doc.  Pure cache inspection -- no rebuild, no I/O
    beyond the already-loaded ``old``.
    """
    funcs = old.get("functions", [])
    if not funcs:
        return False
    # name -> file, to resolve which file a named donor lives in.
    file_by_name = {}
    for f in funcs:
        nm = f.get("name")
        fl = f.get("file")
        if nm and fl:
            file_by_name.setdefault(nm, fl)
    # donor_name -> set of dependent files (only non-empty payloads).
    donor_to_dep_files: dict[str, set[str]] = {}
    for f in funcs:
        tm = f.get("tail_merge")
        if not isinstance(tm, dict):
            continue
        donor = tm.get("donor_name")
        dep_file = f.get("file")
        if not donor or not dep_file:
            continue
        donor_to_dep_files.setdefault(donor, set()).add(dep_file)
    if not donor_to_dep_files:
        return False
    # A changed file is "foreign-donor-coupled" if it contains a donor
    # function that has ANY dependent in a file NOT also being re-verified.
    for donor, dep_files in donor_to_dep_files.items():
        donor_file = file_by_name.get(donor)
        if donor_file is None or donor_file not in changed_rel:
            continue
        if any(dep_file not in changed_rel for dep_file in dep_files):
            return True
    return False


def _incremental_update(
    cache_path: Path, cache_mtime: float, verbose: bool,
) -> Optional[dict]:
    """Try to refresh a STALE verify cache by re-verifying ONLY the changed
    ``.c`` files and merging their records into the cached document.

    Returns the merged doc (and writes it back to ``cache_path`` with a
    fresh mtime, so the next read is instant) on success, or ``None`` to
    tell the caller to fall back to a full rebuild.  Bails to full when:

      * the cache is missing/corrupt or not the expected shape,
      * a header changed (a header can affect every TU),
      * (nearly) every TU changed (scoped == full),
      * the scoped output's file keys don't line up with the changed set.

    KNOWN LIMITATION: a *cross-TU tail-merge* coupling -- where an
    unchanged function tail-merges into a donor that lives in a CHANGED
    file -- can leave that dependent's record stale until the next full
    rebuild (``c2 decomp-verify --json``, a header touch, or a
    ``rebuild=True`` caller).  This is the same staleness tradeoff the
    triage cache already makes, in exchange for a ~3x faster refresh.
    """
    try:
        old = json.loads(cache_path.read_text())
    except (OSError, ValueError):
        return None
    if not (isinstance(old, dict) and "functions" in old and "files" in old):
        return None

    changed_c, changed_h = _changed_sources(cache_mtime)
    if changed_h:
        return None  # header -> may touch every TU -> full rebuild
    if not changed_c:
        return old   # mtime newer but no tracked source changed -> cache OK

    n_total_c = sum(1 for _ in SRC_DIR.glob("*.c")) if SRC_DIR.exists() else 0
    if n_total_c and len(changed_c) >= max(1, int(n_total_c
                                                  * _INCREMENTAL_MAX_FRACTION)):
        return None  # too many TUs changed -> a full pass is cheaper

    if verbose:
        import typer
        names = sorted(p.name for p in changed_c)
        shown = ", ".join(names[:6]) + (
            f" (+{len(names) - 6} more)" if len(names) > 6 else "")
        typer.echo(
            f"verify-json: incremental refresh of {len(changed_c)} changed "
            f"file(s) [{shown}] (scoped re-verify + merge into cache)…",
            err=True,
        )

    changed_rel = {str(p) for p in changed_c}
    # Cross-TU tail-merge guard.  A donor function whose body changed
    # rewrites the "shared tail" Watcom factored into every dependent
    # that jmps into it -- INCLUDING dependents in other, unchanged TUs.
    # The scoped re-verify only recompiles the changed files, so those
    # foreign dependents' records would stay stale (typically surfacing
    # as a phantom exact-count swing once a full rebuild eventually
    # catches up).  Bail to a full rebuild instead; correctness over the
    # ~3x speedup here.  See the staleness model docstring above.
    if _foreign_tail_merge_donors_changed(old, changed_rel):
        if verbose:
            import typer
            typer.echo(
                "verify-json: changed file(s) host tail-merge donors "
                "with cross-TU dependents -- bailing to full rebuild "
                "(scoped merge would leave foreign dependents stale).",
                err=True,
            )
        return None

    try:
        sub = _run_verify_json(c_files=list(changed_c))
    except BaseException:
        # A scoped re-verify can fail transiently -- most often a parallel
        # session saving one of the changed files mid-build (the build's
        # own "source changed DURING the build" guard aborts with a
        # typer.Exit).  Don't let that escape the fast path: bail to the
        # normal full-rebuild path, exactly as if incremental were off.
        return None
    # The scoped pass must report every changed file under the same key the
    # records use; if the path format differs, bail rather than risk a
    # half-merged doc.
    if not changed_rel.issubset(set(sub.get("files", {}))):
        return None

    merged = _merge_docs(old, sub, changed_rel)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(f".tmp{os.getpid()}")
        tmp.write_text(json.dumps(merged))
        tmp.replace(cache_path)
    except OSError:
        pass
    return merged


def get_verify_json(
    *,
    rebuild: bool = False,
    from_path: Optional[Path] = None,
    cache_path: Path = CACHE_PATH,
    verbose: bool = False,
    no_build: bool = False,
    incremental: bool = True,
) -> dict:
    """Return the full verify document.

    Priority:
      1. ``from_path`` — load a caller-supplied JSON blob verbatim.
      2. cached ``cache_path`` if fresh (newer than all sources) and not
         ``rebuild``.
      3. if the cache is STALE but only some ``.c`` files changed (and
         ``incremental``), re-verify JUST those files and merge them into
         the cache — a ~3x faster refresh than a full pass (the build is
         the same incremental wmake; only the per-function compare/hints
         are scoped).  See :func:`_incremental_update` for the bail-out
         conditions and the cross-TU tail-merge caveat.
      4. otherwise regenerate the full document in-process and cache it.

    ``no_build``: never regenerate — return the cache even if slightly
    stale, or raise ``FileNotFoundError`` if there is none.  Used by the
    decomp-verify -v hint path so a hint can never trigger a 30 s rebuild
    (or recurse) inside the verifier itself.

    ``incremental``: enable the scoped-merge fast path (step 3); set
    ``False`` to force a full rebuild whenever the cache is stale.
    """
    if from_path is not None:
        return json.loads(Path(from_path).read_text())

    if no_build:
        if cache_path.exists():
            return json.loads(cache_path.read_text())
        raise FileNotFoundError(cache_path)

    if not rebuild and cache_path.exists():
        try:
            cache_mtime = cache_path.stat().st_mtime
            if cache_mtime >= _newest_src_mtime():
                return json.loads(cache_path.read_text())
            if incremental:
                doc = _incremental_update(cache_path, cache_mtime, verbose)
                if doc is not None:
                    return doc
        except (OSError, ValueError):
            pass

    if verbose:
        import typer
        typer.echo(
            "verify-json: regenerating via decomp-verify --json "
            "(~10-30 s; cached afterwards)…",
            err=True,
        )
    doc = _run_verify_json()
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(doc))
    except OSError:
        pass
    return doc
