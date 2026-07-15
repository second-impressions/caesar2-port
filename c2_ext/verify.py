"""End-to-end verify: compile ``scratch.c``, byte-compare to one of the
project's byte oracles.

The agent's ``verify`` always compiles the same ``scratch.c``; the
``target`` parameter picks which compile-toolchain + byte oracle pair
to compare against:

* ``target="watcom"`` (default) -- ``wcc386 -bt=dos -mf -4r -s -d1`` against
  the DOS ``PS.EXE``.  Primary byte oracle; the canonical truth.
* ``target="msvc"``           -- ``cl.exe /nologo /c /Od /Zp1`` against the
  Windows ``CAESAR2.EXE`` (MSVC 4.0 ``/Od``, /MLd static-debug CRT).
  Secondary byte oracle; useful as a cross-check when watcom is byte-
  exact but you want a second independent witness.

Output is intentionally compact (per the design's "no prose header"
rule): just the diff rows + the headline ``N/total \u2713|\u2717`` line.
Compile failures surface the raw compiler stderr.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from c2_ext.format.asm import apply_line_numbers
from c2_ext.format.diff import (
    align_and_classify,
    count_real_diffs,
    render_diff,
)
from c2_ext.project import ProjectConfig
from c2_ext.runs import load_meta


@dataclass(frozen=True)
class VerifyResult:
    """One verify invocation."""

    build_ok: bool
    stderr: str
    target_bytes_size: int
    your_bytes_size: int | None      # None on build failure
    byte_diff: int                   # number of real (non-relocation) byte differences
    real_diff_rows: int              # diff rows that disagree
    rendered: list[str]              # output lines for the agent
    exact: bool
    fallthrough_callee: str | None
    donor_name: str | None
    target: str                      # which byte oracle was used
    shape_distance: dict | None = None
    """Layered shape distance (ir/width/spill/seat + fix_next).  Computed
    against the watcom oracle only (msvc encoding differs too much).
    None on build failure or msvc target."""


def verify(
    project: ProjectConfig,
    run_dir: Path,
    *,
    diff: bool = False,
    context: int = 3,
    target: str = "watcom",
) -> VerifyResult:
    """Compile ``run_dir/scratch.c`` and byte-compare against ``target``.

    ``target`` chooses both the compile toolchain AND the byte oracle:
    ``"watcom"`` uses wcc386 + PS.EXE; ``"msvc"`` uses cl.exe + CAESAR2.EXE.
    """
    # Pick the toolchain for this verify run.  We may need a different
    # toolchain than the one the project was originally bound to (the
    # compose step always uses watcom; verify can switch).
    if target != project.active_target:
        project = project.for_target(target)
    tc = project.toolchain()
    meta = load_meta(run_dir)
    fn_name = meta.function

    res = tc.compile_scratch(run_dir, fn_name)
    if not res.ok:
        rendered = ["BUILD FAIL", ""]
        rendered.extend(res.stderr.splitlines())
        return VerifyResult(
            build_ok=False, stderr=res.stderr,
            target_bytes_size=0,
            your_bytes_size=None,
            byte_diff=0, real_diff_rows=0,
            rendered=rendered, exact=False,
            fallthrough_callee=None,
            donor_name=None,
            target=target,
        )

    your_bytes = res.function_bytes

    # Fetch target bytes + fixups + lines fresh from the active oracle.
    info = tc.function_info(fn_name)
    raw_bytes = tc.function_bytes(fn_name)
    raw_fix = tc.function_fixups(fn_name)
    raw_lines = tc.line_numbers(fn_name)
    norm = tc.normalize_target(raw_bytes, info.address, raw_fix, raw_lines)
    target_bytes = norm.bytes_

    # Disassemble both sides at their FULL length (so intra-fn `.L_X`
    # resolution sees the right function bounds).  Truncation is applied
    # to the COMPARE step only.
    target_fix_full = norm.fixup_offsets | norm.extra_reloc_offsets
    target_insns = tc.disassemble(target_bytes, info.address, target_fix_full)
    target_rows = apply_line_numbers(
        target_insns, norm.line_marks,
        donor_first_line=norm.donor_first_line,
        donor_boundary=norm.donor_boundary,
    )

    your_insns = tc.disassemble(your_bytes, info.address, res.fixup_offsets)
    # YOUR-side rows compute their L+N from OUR scratch source's line
    # marks (not the target binary's), so the agent can compare "target
    # emits N insns at L+5 / my source emits M insns at L+5" side-by-side.
    your_rows = apply_line_numbers(
        your_insns, res.line_marks,
        donor_first_line=None,         # no tail-merge donor in scratch
        donor_boundary=None,
        scratch_marks=res.line_marks,  # keep sc:N available too
    )

    # Forward-fall-through normalization: target function ends and
    # falls through into a neighbor; the standalone compile cannot
    # reproduce that and emits its own ``ret``/``call``/etc.
    # afterwards.  Truncate row comparison + byte comparison to the
    # original function size so the trailing standalone emission is
    # ignored.
    if norm.fallthrough_callee is not None:
        cmp_size = norm.raw_dependent_size
        target_cmp = target_bytes[:cmp_size]
        your_cmp = your_bytes[:cmp_size]
        target_rows_cmp = [r for r in target_rows if r.offset < cmp_size]
        your_rows_cmp = [r for r in your_rows if r.offset < cmp_size]
    else:
        target_cmp = target_bytes
        your_cmp = your_bytes
        target_rows_cmp = target_rows
        your_rows_cmp = your_rows

    drows = align_and_classify(target_rows_cmp, your_rows_cmp)

    # The byte counter ignores the union of both fixup masks AND the
    # byte ranges of any row the classifier accepted as equal
    # (e.g. inverse-jcc-pair / cross-fn-elision rows whose bytes
    # legitimately differ).
    accepted_mask: set[int] = set(target_fix_full) | set(res.fixup_offsets)
    for r in drows:
        if r.marker != " ":
            continue
        if r.target is not None:
            for k in range(r.target.size):
                accepted_mask.add(r.target.offset + k)
        if r.yours is not None:
            for k in range(r.yours.size):
                accepted_mask.add(r.yours.offset + k)

    real_byte_diff = _count_real_byte_diffs(
        target_cmp, your_cmp,
        frozenset(accepted_mask), frozenset(),
    )
    real_row_count = count_real_diffs(drows)
    sizes_match = len(target_cmp) == len(your_cmp)
    exact = (real_byte_diff == 0 and real_row_count == 0 and sizes_match)

    headline_lines = render_diff(drows, full=diff, context=context)
    if not headline_lines:
        headline_lines = []

    # Compute the layered shape distance (ir/width/spill/seat + fix_next).
    # Only meaningful against watcom (msvc encoding is too different).
    shape_dict = None
    if target == "watcom" and not exact:
        try:
            shape_dict = _compute_shape_distance(drows, real_byte_diff)
        except Exception:
            shape_dict = None     # never block verify on a metric failure
    elif target == "watcom" and exact:
        shape_dict = {"shape": 0, "ir": 0, "width": 0, "spill": 0, "seat": 0,
                      "ir_total": 0, "width_total": 0, "spill_total": 0,
                      "seat_total": 0, "fix_next": "done"}

    cmp_size = len(target_cmp)
    target_tag = f"[{target}]"
    if exact:
        summary = f"0/{cmp_size} \u2713  {target_tag}"
    else:
        summary = f"{real_byte_diff}/{cmp_size} \u2717  {target_tag}"
        if not sizes_match:
            summary += f" (size: target={len(target_cmp)} yours={len(your_cmp)})"
    if norm.fallthrough_callee:
        summary += f"  [falls through into {norm.fallthrough_callee}]"
    if norm.donor_name:
        summary += f"  [tail-merge donor: {norm.donor_name}]"

    rendered = []
    rendered.append(f"verify ({target})")
    if headline_lines:
        rendered.extend(headline_lines)
        rendered.append("")
    rendered.append(summary)
    if shape_dict is not None:
        rendered.append(_format_shape_line(shape_dict))

    return VerifyResult(
        build_ok=True, stderr=res.stderr,
        target_bytes_size=len(target_bytes),
        your_bytes_size=len(your_bytes),
        byte_diff=real_byte_diff,
        real_diff_rows=real_row_count,
        rendered=rendered,
        exact=exact,
        fallthrough_callee=norm.fallthrough_callee,
        donor_name=norm.donor_name,
        target=target,
        shape_distance=shape_dict,
    )


def _drow_to_shape_dict(r) -> dict:
    """Convert a c2-ext DiffRow into the dict form ``seat_recon`` expects.

    seat_recon's row keys: ``ps``/``rc``  -> {'asm': str},
                            ``off``       -> int,
                            ``ln``        -> int | None.
    Our row's ``line_label`` is like 'L+12' or 'D+0'; the integer line
    number is what seat_recon reads.
    """
    def _ln(lbl: str) -> int | None:
        if not lbl or not lbl.startswith("L+"):
            return None
        try: return int(lbl[2:])
        except ValueError: return None

    def _asm(row) -> str:
        if row is None:
            return ""
        return f"{row.mnemonic} {row.op_str}".strip()

    off = (r.target.offset if r.target is not None
           else (r.yours.offset if r.yours is not None else 0))
    ln = _ln(r.target.line_label if r.target is not None
             else (r.yours.line_label if r.yours is not None else ""))
    return {
        "ps": {"asm": _asm(r.target)} if r.target is not None else None,
        "rc": {"asm": _asm(r.yours)} if r.yours is not None else None,
        "off": off,
        "ln": ln,
    }


def _compute_shape_distance(drows, byte_diff: int) -> dict:
    """Run the project's layered shape-distance computation on our DiffRows."""
    from c2.regalloc.seat_recon import shape_distance as _shape_distance
    dict_rows = [_drow_to_shape_dict(r) for r in drows]
    return _shape_distance(dict_rows, byte_diff=byte_diff)


def _format_shape_line(sd: dict) -> str:
    """Format the shape distance for the rendered output."""
    if sd.get("shape", 0) == 0 and sd.get("fix_next") == "done":
        return ("shape: MATCHES (ir/width/spill/seat all 0)  "
                "-- residue is regalloc/encoding")

    def lyr(n: str) -> str:
        v = sd.get(n, 0) or 0
        t = sd.get(n + "_total", 0) or 0
        return f"{n} {v}/{t}" if t else f"{n} {v}"

    layers = " \u00b7 ".join(lyr(n) for n in ("ir", "width", "spill", "seat"))
    fn = sd.get("fix_next")
    return f"shape: {layers}  \u2192 fix-next: {fn}"


# ── best-version checkpoint ────────────────────────────────────
#
# Every successful watcom verify is compared against the previous best for
# this run; if the new state is better, ``scratch.c`` is snapshotted into
# ``scratch.best.c`` along with a ``scratch.best.json`` carrying the
# winning metrics.  The ``revert_to_best`` command restores the snapshot
# back into ``scratch.c``.
#
# Ordering is by the project's Hard Rule #3 judge metric: the layered
# shape distance comes FIRST, byte count is the tie-breaker.  An edit
# that drops shape but raises bytes still wins -- it's PS-faithful.


def _best_files(run_dir: Path) -> tuple[Path, Path]:
    """Paths of the best-version snapshot files."""
    return run_dir / "scratch.best.c", run_dir / "scratch.best.json"


def _verify_score(vr: "VerifyResult") -> tuple[int, int, int]:
    """Return a sortable tuple: (shape_total, byte_diff, build_fail_penalty).

    Lower is better.  ``shape_total`` is the SUM of ir+width+spill+seat;
    on missing shape data (msvc / build failure) it falls back to a large
    sentinel so any computed shape wins.  Build failures get a HUGE
    penalty so they never beat a successful verify.
    """
    if not vr.build_ok:
        return (10**9, 10**9, 1)
    sd = vr.shape_distance
    if sd is None:
        # msvc verify (or any target that doesn't compute shape) -- use
        # bytes-only ordering, but rank below any watcom result by
        # adding a large shape penalty so msvc never overwrites a
        # watcom best.
        return (10**8, vr.byte_diff, 0)
    shape_total = int(sd.get("shape", 10**6))
    return (shape_total, vr.byte_diff, 0)


def _fmt_metric(vr: "VerifyResult") -> str:
    """Short human-readable metric for the checkpoint manifest."""
    if not vr.build_ok:
        return "build-fail"
    sd = vr.shape_distance
    bytes_str = f"{vr.byte_diff}/{vr.target_bytes_size}"
    if sd is None:
        return bytes_str
    return (f"{bytes_str}  shape ir {sd.get('ir',0)} "
            f"width {sd.get('width',0)} "
            f"spill {sd.get('spill',0)} "
            f"seat {sd.get('seat',0)}")


def maybe_checkpoint_best(run_dir: Path, vr: VerifyResult) -> bool:
    """If ``vr`` is the best result seen for this run, snapshot scratch.c.

    Returns True if a new snapshot was written.  Skips silently on msvc
    (we only checkpoint watcom-faithful versions -- msvc shape isn't
    computed) and on build failures.
    """
    if not vr.build_ok or vr.target != "watcom":
        return False
    best_c, best_json = _best_files(run_dir)
    scratch = run_dir / "scratch.c"
    if not scratch.exists():
        return False

    cur_score = _verify_score(vr)
    if best_json.exists():
        try:
            prev = json.loads(best_json.read_text())
            prev_score = tuple(prev.get("score", (10**9, 10**9, 1)))
        except Exception:
            prev_score = (10**9, 10**9, 1)
        if cur_score >= prev_score:
            return False

    shutil.copyfile(scratch, best_c)
    best_json.write_text(json.dumps({
        "score": list(cur_score),
        "byte_diff": vr.byte_diff,
        "target_bytes": vr.target_bytes_size,
        "your_bytes": vr.your_bytes_size,
        "target": vr.target,
        "exact": vr.exact,
        "shape_distance": vr.shape_distance,
        "metric": _fmt_metric(vr),
    }, indent=2) + "\n")
    return True


def read_best_manifest(run_dir: Path) -> dict | None:
    """Return the best-version manifest, or None if no checkpoint exists."""
    _, best_json = _best_files(run_dir)
    if not best_json.exists():
        return None
    try:
        return json.loads(best_json.read_text())
    except Exception:
        return None


def revert_to_best(run_dir: Path) -> dict:
    """Restore ``scratch.best.c`` to ``scratch.c``.

    Returns a dict describing what was restored.  Raises ``FileNotFoundError``
    if no checkpoint exists.
    """
    best_c, best_json = _best_files(run_dir)
    scratch = run_dir / "scratch.c"
    if not best_c.exists() or not best_json.exists():
        raise FileNotFoundError(
            "no checkpoint to revert to -- run verify() at least once "
            "with a watcom-compilable scratch.c first"
        )
    manifest = json.loads(best_json.read_text())
    shutil.copyfile(best_c, scratch)
    return {
        "reverted": True,
        "metric": manifest.get("metric", "?"),
        "shape_distance": manifest.get("shape_distance"),
        "byte_diff": manifest.get("byte_diff"),
        "exact": manifest.get("exact", False),
    }


def _count_real_byte_diffs(
    target: bytes, yours: bytes,
    target_fix: frozenset[int], your_fix: frozenset[int],
) -> int:
    """Byte-level diff count, masking out the union of both fixup sets."""
    mask = target_fix | your_fix
    n = max(len(target), len(yours))
    diff = 0
    for i in range(n):
        if i in mask:
            continue
        a = target[i] if i < len(target) else None
        b = yours[i] if i < len(yours) else None
        if a != b:
            diff += 1
    return diff
