"""Selector resolution: turn CLI args into a list of function names.

Selectors accepted:

* Anything that doesn't look like a path (no ``/``, no ``.c``) is
  treated as a **function name** and used as-is.
* Anything ending in ``.c`` or containing a path separator is a
  **file** selector — every diffing (non-byte-exact) function in that
  file is included.  Matches by basename, so ``map.c`` and
  ``decomp/src/map.c`` are equivalent.

Selectors are deduplicated in input order; already-byte-exact functions
are filtered out and reported separately.
"""

from __future__ import annotations

import contextlib
import io
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class WorklistRow:
    name: str
    source_file: Optional[str]
    byte_diff: int
    exact: bool
    tail_merge_donor: Optional[str] = None
    """If the function's only remaining diff is a tail-merge of a donor
    that isn't byte-exact yet, this names the donor.  Else None."""


@dataclass
class Resolution:
    """Outcome of resolving a list of selectors.

    ``targets`` is the deduplicated list of function names to send to
    agents (already filtered to non-byte-exact and tail-merge-blocked).
    ``skipped_exact`` lists names that the user asked for but are
    already done.  ``skipped_blocked`` lists names whose ONLY remaining
    diff is a tail-merge donor that isn't byte-exact yet (those resolve
    automatically once the donor is fixed).  ``unknown`` lists selectors
    that matched nothing.
    """

    targets: list[str] = field(default_factory=list)
    skipped_exact: list[str] = field(default_factory=list)
    skipped_blocked: list[tuple[str, str]] = field(default_factory=list)
    """List of ``(function, blocking_donor_name)`` pairs."""
    unknown: list[str] = field(default_factory=list)


# ── verify.json loader ───────────────────────────────────────────────────


def _load_verify_corpus(
    project_root: Path,
    *,
    no_build: bool = False,
) -> list[WorklistRow]:
    """Return the per-function verify rows from the project's verify cache.

    Uses ``c2.commands.verify_json.get_verify_json`` in-process so the
    cache fast path (and incremental refresh) is honoured.  Run once at
    orchestrator startup; the result is small enough to keep in memory.

    ``no_build=True`` returns the cache even if stale and raises
    :class:`FileNotFoundError` if no cache exists -- useful when the
    caller already knows the named selectors are diffing and wants to
    skip the corpus refresh entirely.
    """
    # Chatter ("Loading PS.EXE…", per-function deltas) is routed to
    # stderr by the verify helpers; silence it so selector resolution
    # stays quiet.
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(project_root)
        from c2.commands.verify_json import get_verify_json
        with contextlib.redirect_stderr(io.StringIO()):
            data = get_verify_json(verbose=False, no_build=no_build)
    finally:
        os.chdir(old_cwd)

    rows: list[WorklistRow] = []
    # First pass: collect bare rows.
    raw_donors: dict[str, Optional[str]] = {}
    for rec in data.get("functions", []):
        diff = int(rec.get("diff_byte_count", 0) or 0)
        tm = rec.get("tail_merge") or {}
        donor = tm.get("donor_name") if isinstance(tm, dict) else None
        raw_donors[rec["name"]] = donor if isinstance(donor, str) else None
        rows.append(WorklistRow(
            name=rec["name"],
            source_file=rec.get("file"),
            byte_diff=diff,
            exact=diff == 0,
            tail_merge_donor=None,    # populated in second pass below
        ))

    # Second pass: tag rows whose only diff is a still-diffing donor.
    #
    # We can't perfectly distinguish "tail-merge-only blocked" from
    # "tail-merge AND other diffs" without per-row classification, so
    # we use the verify cache's ``tail_merge`` block + the diff status
    # of the donor as a proxy.  A row is BLOCKED iff:
    #   1. it has a ``tail_merge.donor_name`` set, AND
    #   2. that donor is itself NOT byte-exact in this same corpus, AND
    #   3. the row's own ``donor_flip`` / ``donor_status`` hint marks
    #      the tail-merge as the residue (heuristic: if the rest of
    #      shape is matched OR the recorded summary called this row a
    #      donor-flip variant, we treat tail-merge as the sole cause).
    #
    # The third clause is intentionally CONSERVATIVE: when in doubt we
    # leave the function in the workable set so the agent can still
    # grind whatever non-tail-merge diff remains.
    exact_by_name = {r.name for r in rows if r.exact}
    for i, rec in enumerate(data.get("functions", [])):
        donor = raw_donors.get(rec["name"])
        if not donor or donor in exact_by_name:
            continue
        # Conservative classifier: shape (if computed) must be all zero
        # AND the row's diff_byte_count must be small relative to the
        # function size — ``donor_flip`` residues are typically the
        # 7-byte epilogue + a handful of cascade bytes.
        shape = rec.get("shape_distance") or {}
        shape_sum = sum(int(shape.get(k, 0) or 0)
                        for k in ("ir", "width", "spill", "seat"))
        diff = rows[i].byte_diff
        size = int(rec.get("size") or 0) or 1
        # "Tail-merge-only" heuristic: shape matched + diff is < 15% of
        # size and < 256 bytes.  Tighter than necessary on purpose.
        if shape_sum == 0 and diff < 256 and diff * 100 < size * 15:
            rows[i] = WorklistRow(
                name=rows[i].name, source_file=rows[i].source_file,
                byte_diff=rows[i].byte_diff, exact=rows[i].exact,
                tail_merge_donor=donor,
            )
    return rows


# ── selector classification ──────────────────────────────────────────────


def _looks_like_file(sel: str) -> bool:
    return sel.endswith(".c") or "/" in sel or "\\" in sel


def _basename_no_ext(p: str) -> str:
    return Path(p).name.removesuffix(".c")


def resolve(
    selectors: Iterable[str],
    project_root: Path,
    *,
    rows: Optional[list[WorklistRow]] = None,
    no_build: bool = False,
) -> Resolution:
    """Turn raw selectors into the orchestrator's target list.

    ``rows`` lets callers inject a pre-loaded verify corpus (e.g. in
    tests).  Otherwise we read ``.c2-cache/verify.json`` via the
    project's in-process cache helper.

    Pass ``no_build=True`` (for ``--dry-run`` etc.) to skip the
    potentially-expensive incremental rebuild when the cache is stale.
    """
    cache_missing = False
    if rows is None:
        try:
            rows = _load_verify_corpus(project_root, no_build=no_build)
        except FileNotFoundError:
            # No cache yet AND we were forbidden to rebuild.  Take every
            # raw function selector at face value (file selectors can't
            # be expanded without the cache, so they'll be flagged as
            # unknown).  The orchestrator will surface real errors when
            # it actually tries to compose.
            rows = []
            cache_missing = True

    by_name = {r.name: r for r in rows}
    by_file: dict[str, list[WorklistRow]] = {}
    for r in rows:
        if r.source_file:
            by_file.setdefault(_basename_no_ext(r.source_file), []).append(r)

    out_targets: list[str] = []
    skipped: list[str] = []
    blocked: list[tuple[str, str]] = []
    unknown: list[str] = []
    seen: set[str] = set()

    def _add(name: str, *, skip_exact: bool = True) -> None:
        if name in seen:
            return
        seen.add(name)
        r = by_name.get(name)
        if r is None:
            unknown.append(name)
            return
        if r.exact and skip_exact:
            skipped.append(name)
            return
        if r.tail_merge_donor:
            # Tail-merge-only-blocked: skip; the agent has no source
            # lever for this and the diff resolves automatically once
            # the donor is fixed (Hard Rule: blocked != workable).
            blocked.append((name, r.tail_merge_donor))
            return
        out_targets.append(name)

    for sel in selectors:
        sel = sel.strip()
        if not sel:
            continue
        if _looks_like_file(sel):
            key = _basename_no_ext(sel)
            matched = by_file.get(key)
            if not matched:
                unknown.append(sel)
                continue
            for r in matched:
                _add(r.name)
        elif cache_missing:
            # Pass-through without exact-filter when no cache exists.
            if sel not in seen:
                seen.add(sel)
                out_targets.append(sel)
        else:
            _add(sel)

    return Resolution(
        targets=out_targets, skipped_exact=skipped,
        skipped_blocked=blocked, unknown=unknown,
    )


# ── quick smoke ──────────────────────────────────────────────────────────


def cli_describe(res: Resolution) -> str:
    """Render a short human summary of a Resolution."""
    parts = [f"Targets: {len(res.targets)}"]
    if res.skipped_exact:
        parts.append(f"skipped (already byte-exact): {len(res.skipped_exact)}")
    if res.skipped_blocked:
        donors = sorted({d for _, d in res.skipped_blocked})
        parts.append(
            f"skipped (tail-merge blocked on "
            f"{len(donors)} donor(s) still diffing): "
            f"{len(res.skipped_blocked)}"
        )
    if res.unknown:
        parts.append(f"unknown: {len(res.unknown)}  → {', '.join(res.unknown[:5])}")
    return "\n".join(parts)
