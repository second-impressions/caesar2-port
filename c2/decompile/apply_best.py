"""Apply best-body splices: byte-exact AND clear shape improvements.

The orchestrator's original behaviour was "only auto-apply byte-exact
wins".  This module extends that to also auto-apply CLEAR SHAPE
IMPROVEMENTS -- candidate bodies whose layered shape vector
``(ir, width, spill, seat)`` is strictly less (lex) than HEAD's.  Per
Hard Rule #3, an edit that drops shape_distance is PS-faithful even
if the byte count rose; we materialise that ranking objectively here.

Two entry points:

* :func:`apply_if_improves` -- called from the orchestrator's
  ``_postprocess`` at the end of each run.  Compares the agent's
  best snapshot against HEAD's ``.c2-cache/verify.json`` and applies
  iff the candidate strictly improves the shape vector (or is a
  byte-exact win).

* :func:`sweep_best_runs` -- retroactive: scans ``.c2-runs/`` for the
  best historical run of each still-diffing function and applies any
  improvement.  Powers the ``c2 decompile apply-best`` CLI.

Both share the same comparison primitive (:func:`compare_shapes`) and
the same atomic splice via :mod:`c2.decompile._engine.apply` -- the
function-span splice that preserves comments, sibling functions, and
formatting in the TU.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator, Optional

from c2.decompile._engine.apply import ApplyError
from c2.decompile._engine.apply import apply as _apply_engine
from c2.decompile.workspace import Workspace


# ── shape vector + comparison ────────────────────────────────────────────


# A shape vector is the four-tuple ``(ir, width, spill, seat)`` of
# DIVERGENT counts (lower = closer to PS).  Lex comparison matches the
# project's fix-order priority: an ir-layer drop beats any width/spill/
# seat drop, a width drop beats any spill/seat drop, etc.
ShapeVec = tuple[int, int, int, int]


def _vec_from_agent_best(best_verify: dict) -> Optional[ShapeVec]:
    """Extract the shape vector from an agent run's ``best/verify.json``
    (the orchestrator's BestSnapshot format).  Returns ``None`` if the
    snapshot has no shape (build-failure / msvc-target snapshots).

    Schema (see :class:`c2.decompile.models.ShapeDistance`):
        ``{"ir": [div,total], "width": [...], "spill": [...], "seat": [...]}``
    """
    sh = best_verify.get("shape")
    if not sh:
        return None
    try:
        return (sh["ir"][0], sh["width"][0], sh["spill"][0], sh["seat"][0])
    except (KeyError, IndexError, TypeError):
        return None


def _vec_from_head(head_entry: dict) -> Optional[ShapeVec]:
    """Extract the shape vector from ``.c2-cache/verify.json``'s
    per-function entry (flat scalar form).

    Schema (see ``c2/decomp_verify/verifier.py`` -- ``shape_distance``
    field on each row):
        ``{"ir": int, "width": int, "spill": int, "seat": int, ...}``
    """
    sd = head_entry.get("shape_distance")
    if not sd:
        return None
    try:
        return (int(sd["ir"]), int(sd["width"]), int(sd["spill"]), int(sd["seat"]))
    except (KeyError, TypeError, ValueError):
        return None


class CompareVerdict(str, Enum):
    """Why ``compare_shapes`` says yes/no.  Surfaced in history.jsonl
    + the apply-best CLI summary."""

    BYTE_EXACT = "byte_exact"                   # bytes==0, apply unconditionally
    SHAPE_IMPROVED = "shape_improved"            # lex(candidate) < lex(head)
    BYTES_IMPROVED_SAME_SHAPE = "bytes_improved_same_shape"  # tied shape, lower bytes
    SAME = "same"                                # exact tie
    REGRESSED_SHAPE = "regressed_shape"          # lex(candidate) > lex(head)
    REGRESSED_BYTES = "regressed_bytes"          # tied shape, higher bytes
    NO_HEAD_DATA = "no_head_data"                # function missing from HEAD's verify.json
    NO_CANDIDATE_DATA = "no_candidate_data"      # best/verify.json missing/no shape


def compare_shapes(
    *,
    candidate_best: dict,
    head_entry: Optional[dict],
) -> CompareVerdict:
    """Decide whether ``candidate_best`` improves on ``head_entry``.

    Returns a :class:`CompareVerdict` ranked so callers can filter:
    "apply iff verdict in {BYTE_EXACT, SHAPE_IMPROVED, BYTES_IMPROVED_SAME_SHAPE}".

    The order is strict-lexicographic on the shape vector
    ``(ir, width, spill, seat)``, with byte_diff as the tiebreaker.
    Equal shape + equal bytes = SAME (no apply, no benefit).
    """
    cand_bytes = int(candidate_best.get("byte_diff", -1))
    if cand_bytes == 0:
        return CompareVerdict.BYTE_EXACT

    cand_vec = _vec_from_agent_best(candidate_best)
    if cand_vec is None:
        return CompareVerdict.NO_CANDIDATE_DATA
    if head_entry is None:
        return CompareVerdict.NO_HEAD_DATA

    head_vec = _vec_from_head(head_entry)
    if head_vec is None:
        return CompareVerdict.NO_HEAD_DATA
    head_bytes = int(head_entry.get("diff_byte_count", -1))

    if cand_vec < head_vec:
        return CompareVerdict.SHAPE_IMPROVED
    if cand_vec > head_vec:
        return CompareVerdict.REGRESSED_SHAPE

    # Shape tied -- defer to bytes.  This is the rung where the byte
    # diff IS meaningful (shape is identical, so the byte gap reflects
    # only regalloc tie-breaks; lower IS better in this strict tied
    # case).  Strictly lower bytes only; equal = SAME.
    if 0 <= cand_bytes < head_bytes:
        return CompareVerdict.BYTES_IMPROVED_SAME_SHAPE
    if cand_bytes > head_bytes >= 0:
        return CompareVerdict.REGRESSED_BYTES
    return CompareVerdict.SAME


def is_apply_worthy(verdict: CompareVerdict) -> bool:
    """The set of verdicts that justify materialising the apply."""
    return verdict in {
        CompareVerdict.BYTE_EXACT,
        CompareVerdict.SHAPE_IMPROVED,
        CompareVerdict.BYTES_IMPROVED_SAME_SHAPE,
    }


# ── helpers: load HEAD's verify.json + iterate runs ──────────────────────


def load_head_index(project_root: Path) -> dict[str, dict]:
    """Index ``.c2-cache/verify.json``'s ``functions`` array by name.

    Returns ``{}`` (empty dict) if the cache is missing -- callers
    treat that as "no HEAD data for any function" and skip shape
    comparison (byte-exact wins still apply).
    """
    cache = project_root / ".c2-cache" / "verify.json"
    if not cache.is_file():
        return {}
    try:
        data = json.loads(cache.read_text())
    except json.JSONDecodeError:
        return {}
    return {f["name"]: f for f in data.get("functions", []) if "name" in f}


# ── apply: orchestrator post-run hook ────────────────────────────────────


@dataclass(frozen=True)
class ApplyDecision:
    """Returned by :func:`apply_if_improves` for the orchestrator's
    history.jsonl trail."""

    function: str
    verdict: CompareVerdict
    applied: bool
    candidate_vec: Optional[ShapeVec]
    head_vec: Optional[ShapeVec]
    candidate_bytes: Optional[int]
    head_bytes: Optional[int]
    error: Optional[str] = None


def apply_if_improves(
    *,
    ws: Workspace,
    project,
    project_root: Path,
    function: str,
    head_index: Optional[dict[str, dict]] = None,
) -> ApplyDecision:
    """Apply the agent's best body iff it byte-exacts OR strictly
    improves HEAD's shape vector (or bytes within the same shape).

    Copies ``best/scratch.c`` over ``work/scratch.c`` first so the
    splice always uses the BEST snapshot, never whatever the agent
    happened to leave at the end of its run (per Hard Rule #3 -- the
    project's recorded best, not the most-recent-edit).
    """
    if head_index is None:
        head_index = load_head_index(project_root)
    head_entry = head_index.get(function)

    best_verify_path = ws.best_dir / "verify.json"
    best_scratch_path = ws.best_dir / "scratch.c"
    if not best_verify_path.is_file() or not best_scratch_path.is_file():
        return ApplyDecision(
            function=function,
            verdict=CompareVerdict.NO_CANDIDATE_DATA,
            applied=False,
            candidate_vec=None,
            head_vec=_vec_from_head(head_entry) if head_entry else None,
            candidate_bytes=None,
            head_bytes=int(head_entry.get("diff_byte_count", -1)) if head_entry else None,
            error="no best snapshot for this run",
        )

    candidate_best = json.loads(best_verify_path.read_text())
    verdict = compare_shapes(candidate_best=candidate_best, head_entry=head_entry)
    cand_vec = _vec_from_agent_best(candidate_best)
    head_vec = _vec_from_head(head_entry) if head_entry else None
    cand_bytes = int(candidate_best.get("byte_diff", -1))
    head_bytes = int(head_entry.get("diff_byte_count", -1)) if head_entry else None

    if not is_apply_worthy(verdict):
        ws.append_history({
            "type": "apply_skipped",
            "verdict": verdict.value,
            "candidate_vec": list(cand_vec) if cand_vec else None,
            "head_vec": list(head_vec) if head_vec else None,
            "candidate_bytes": cand_bytes,
            "head_bytes": head_bytes,
        })
        return ApplyDecision(
            function=function, verdict=verdict, applied=False,
            candidate_vec=cand_vec, head_vec=head_vec,
            candidate_bytes=cand_bytes, head_bytes=head_bytes,
        )

    # Ensure work/scratch.c holds the BEST snapshot before splicing --
    # the agent may have wandered after its is_new_best transition.
    try:
        shutil.copy(best_scratch_path, ws.work_dir / "scratch.c")
        result = _apply_engine(project, ws.work_dir, dry_run=False)
        ws.append_history({
            "type": "applied",
            "verdict": verdict.value,
            "src_file": result.tu_path,
            "bytes_before": result.bytes_before,
            "bytes_after": result.bytes_after,
            "candidate_vec": list(cand_vec) if cand_vec else None,
            "head_vec": list(head_vec) if head_vec else None,
            "candidate_bytes": cand_bytes,
            "head_bytes": head_bytes,
        })
        return ApplyDecision(
            function=function, verdict=verdict, applied=True,
            candidate_vec=cand_vec, head_vec=head_vec,
            candidate_bytes=cand_bytes, head_bytes=head_bytes,
        )
    except (ApplyError, OSError) as e:
        ws.append_history({"type": "apply_failed", "error": str(e),
                           "verdict": verdict.value})
        return ApplyDecision(
            function=function, verdict=verdict, applied=False,
            candidate_vec=cand_vec, head_vec=head_vec,
            candidate_bytes=cand_bytes, head_bytes=head_bytes,
            error=str(e),
        )


# ── retroactive sweep: c2 decompile apply-best ───────────────────────────


def iter_run_dirs(runs_root: Path) -> Iterator[Path]:
    """Every immediate subdir of ``.c2-runs/`` that LOOKS like an agent
    run (has a ``best/`` + ``work/`` + ``meta.json``).  Sorted by
    mtime descending so the most recent runs come first."""
    if not runs_root.is_dir():
        return
    candidates = []
    for p in runs_root.iterdir():
        if not p.is_dir():
            continue
        if not (p / "best").is_dir() or not (p / "work").is_dir():
            continue
        candidates.append(p)
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    yield from candidates


def _run_function_name(run_dir: Path) -> Optional[str]:
    """Read the function name out of ``<run>/work/meta.json``."""
    meta_path = run_dir / "work" / "meta.json"
    if not meta_path.is_file():
        return None
    try:
        return json.loads(meta_path.read_text()).get("function")
    except json.JSONDecodeError:
        return None


@dataclass(frozen=True)
class BestRun:
    """The single best historical run for a given function.

    "Best" = lowest layered shape vector, tiebreaker = lowest byte_diff,
    tiebreaker = most-recent mtime (favour newer attempts on a true tie).
    """

    function: str
    run_dir: Path
    shape_vec: ShapeVec
    byte_diff: int
    mtime: float


def collect_best_runs(runs_root: Path) -> dict[str, BestRun]:
    """Walk every run dir and return one :class:`BestRun` per function
    (the best historical candidate, by the project's layered ranking)."""
    by_fn: dict[str, BestRun] = {}
    for run_dir in iter_run_dirs(runs_root):
        fn = _run_function_name(run_dir)
        if fn is None:
            continue
        best_verify_path = run_dir / "best" / "verify.json"
        best_scratch_path = run_dir / "best" / "scratch.c"
        if not best_verify_path.is_file() or not best_scratch_path.is_file():
            continue
        try:
            data = json.loads(best_verify_path.read_text())
        except json.JSONDecodeError:
            continue
        vec = _vec_from_agent_best(data)
        if vec is None:
            continue
        bd = int(data.get("byte_diff", -1))
        mt = run_dir.stat().st_mtime
        candidate = BestRun(function=fn, run_dir=run_dir,
                            shape_vec=vec, byte_diff=bd, mtime=mt)
        prior = by_fn.get(fn)
        if prior is None:
            by_fn[fn] = candidate
            continue
        # Lex on (shape_vec, byte_diff, -mtime).
        cur_key = (prior.shape_vec, prior.byte_diff, -prior.mtime)
        new_key = (candidate.shape_vec, candidate.byte_diff, -candidate.mtime)
        if new_key < cur_key:
            by_fn[fn] = candidate
    return by_fn


@dataclass(frozen=True)
class SweepResult:
    function: str
    run_dir: Path
    verdict: CompareVerdict
    applied: bool
    candidate_vec: ShapeVec
    head_vec: Optional[ShapeVec]
    candidate_bytes: int
    head_bytes: Optional[int]
    error: Optional[str] = None


def sweep_apply_best(
    *,
    project,
    project_root: Path,
    runs_root: Path,
    only_functions: Optional[set[str]] = None,
    dry_run: bool = False,
) -> list[SweepResult]:
    """Apply the BEST historical body for each still-improvable function.

    Skips functions that are already byte-exact at HEAD.  For each
    candidate that strictly improves HEAD's shape (or matches shape
    with strictly fewer bytes -- the regalloc tie-break case), the
    splice is materialised via the same engine path used by
    :func:`apply_if_improves`.

    ``only_functions`` -- limit the sweep to this set (names).
    ``dry_run`` -- compute the decisions but do NOT write any TU.
    """
    head_index = load_head_index(project_root)
    best_runs = collect_best_runs(runs_root)
    results: list[SweepResult] = []

    for fn, run in best_runs.items():
        if only_functions is not None and fn not in only_functions:
            continue
        head_entry = head_index.get(fn)
        # Skip functions HEAD already has byte-exact -- nothing to gain.
        if head_entry is not None and head_entry.get("diff_byte_count", 1) == 0:
            continue

        candidate_best = json.loads((run.run_dir / "best" / "verify.json").read_text())
        verdict = compare_shapes(candidate_best=candidate_best, head_entry=head_entry)
        head_vec = _vec_from_head(head_entry) if head_entry else None
        head_bytes = int(head_entry.get("diff_byte_count", -1)) if head_entry else None

        if not is_apply_worthy(verdict):
            results.append(SweepResult(
                function=fn, run_dir=run.run_dir, verdict=verdict,
                applied=False, candidate_vec=run.shape_vec, head_vec=head_vec,
                candidate_bytes=run.byte_diff, head_bytes=head_bytes,
            ))
            continue

        if dry_run:
            results.append(SweepResult(
                function=fn, run_dir=run.run_dir, verdict=verdict,
                applied=False, candidate_vec=run.shape_vec, head_vec=head_vec,
                candidate_bytes=run.byte_diff, head_bytes=head_bytes,
            ))
            continue

        # Materialise: copy best -> work, splice, mark history.
        try:
            shutil.copy(run.run_dir / "best" / "scratch.c",
                        run.run_dir / "work" / "scratch.c")
            _apply_engine(project, run.run_dir / "work", dry_run=False)
            results.append(SweepResult(
                function=fn, run_dir=run.run_dir, verdict=verdict,
                applied=True, candidate_vec=run.shape_vec, head_vec=head_vec,
                candidate_bytes=run.byte_diff, head_bytes=head_bytes,
            ))
        except (ApplyError, OSError) as e:
            results.append(SweepResult(
                function=fn, run_dir=run.run_dir, verdict=verdict,
                applied=False, candidate_vec=run.shape_vec, head_vec=head_vec,
                candidate_bytes=run.byte_diff, head_bytes=head_bytes,
                error=str(e),
            ))

    return results
