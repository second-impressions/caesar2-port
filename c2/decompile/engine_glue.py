"""Glue between :mod:`c2.decompile._engine` and the orchestrator's typed
workspace/models.

The engine speaks ``Path``-flat run dirs (scratch.c + meta.json side by
side) and untyped dicts; this module:

* Composes into ``Workspace.work_dir`` so scratch.c + the engine's
  meta.json live in the sandbox the agent can see.
* Calls engine.verify and converts its frozen dataclass to a typed
  :class:`c2.decompile.models.VerifyResult`.
* Drives :meth:`Workspace.maybe_save_best`.

This is the only module that imports from ``c2.decompile._engine`` —
keeping the engine boundary thin so the eventual rewrite (or removal of
``c2_ext``-flavoured codepaths) stays local.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from c2.decompile import _engine
from c2.decompile._engine.project import ProjectConfig as EngineProjectConfig
from c2.decompile._engine.runs import compose as _engine_compose
from c2.decompile._engine.runs import ComposeError as EngineComposeError
from c2.decompile._engine.verify import verify as _engine_verify

from c2.decompile.models import (
    BestSnapshot,
    DiffRow,
    FixLayer,
    ShapeDistance,
    Target,
    VerifyResult,
)
from c2.decompile.workspace import RunMeta, Workspace


class ComposeError(RuntimeError):
    """Raised when a workspace cannot be composed for the given function."""


# ── project loading ──────────────────────────────────────────────────────


def load_project(project_root: Path, target: Target) -> EngineProjectConfig:
    """Load the engine's :class:`ProjectConfig` for ``target``."""
    return EngineProjectConfig.load(project_root, target=target.value)


# ── compose ──────────────────────────────────────────────────────────────


def compose_workspace(
    *,
    workspace: Workspace,
    project: EngineProjectConfig,
    function: str,
    target: Target,
    blank: bool = False,
) -> RunMeta:
    """Populate ``workspace.work_dir`` with scratch.c + info.md.

    The engine's compose writes its OWN ``meta.json`` into the work dir
    (used by ``engine.verify``); the orchestrator separately writes its
    own typed ``RunMeta`` into the parent ``run_dir`` for bookkeeping.
    """
    try:
        out_dir = _engine_compose(
            project, function, blank=blank, out_dir=workspace.work_dir
        )
    except EngineComposeError as e:
        raise ComposeError(str(e)) from None
    assert out_dir == workspace.work_dir

    # Mirror selected fields into our typed RunMeta for the orchestrator.
    import json
    raw = json.loads((workspace.work_dir / "meta.json").read_text())
    meta = RunMeta(
        function=raw["function"],
        address_hex=raw["address_hex"],
        target=target,
        target_size=int(raw["target_size"]),
        cflags=list(raw["cflags"]),
        source_file=raw.get("source_file"),
        signature=raw.get("signature"),
        tail_merge_donor=raw.get("tail_merge_donor"),
        body_origin=raw.get("body_origin", "existing"),
        project_root=str(project.root),
        started_at=float(raw["started_at"]),
    )
    workspace.write_meta(meta)
    return meta


# ── verify ───────────────────────────────────────────────────────────────


def _convert_shape(d: Optional[dict]) -> Optional[ShapeDistance]:
    if d is None:
        return None
    # engine schema:  {"ir": <divergent>, "ir_total": ..., "width": ...,
    #                  ..., "fix_next": "ir"|"width"|"spill"|"seat"|"done"}
    fn_raw = (d.get("fix_next") or "none").lower()
    if fn_raw == "done":
        fn = FixLayer.NONE
    else:
        try:
            fn = FixLayer(fn_raw)
        except ValueError:
            fn = FixLayer.NONE
    isl = d.get("islands")
    return ShapeDistance(
        ir=(int(d.get("ir", 0)), int(d.get("ir_total", 0))),
        width=(int(d.get("width", 0)), int(d.get("width_total", 0))),
        spill=(int(d.get("spill", 0)), int(d.get("spill_total", 0))),
        seat=(int(d.get("seat", 0)), int(d.get("seat_total", 0))),
        fix_next=fn,
        islands=int(isl) if isl is not None else None,
    )


def run_verify(
    *,
    workspace: Workspace,
    project: EngineProjectConfig,
    target: Target,
    diff: bool = False,
) -> VerifyResult:
    """Compile workspace.work_dir/scratch.c, byte-compare, save best.

    Concurrent-safe: each Workspace has its own ``work_dir`` and the
    engine's warm-container exec now takes the container name as an
    argument (see :mod:`c2.decompile._engine.toolchains.watcom`), so two
    Workspaces verifying in parallel never share container state.
    """
    res = _engine_verify(
        project, workspace.work_dir,
        diff=diff, target=target.value,
    )

    diff_rows: list[DiffRow] = []
    if diff:
        # Best-effort: the engine returns "rendered" text lines for the
        # human-facing diff view.  Surface them as a single "ours" row
        # so they're still present in the structured result for the
        # agent to read.  Keeping it simple — a full row-by-row
        # conversion would re-walk the alignment, which is expensive.
        for ln in res.rendered:
            diff_rows.append(
                DiffRow(side="changed", offset=0, target_text=ln, ours_text=None)
            )

    notes: list[str] = []
    if target == Target.MSVC:
        notes.append(
            "shape distance is NOT computed on the MSVC target "
            "(encoding differs too much from Watcom for the layered "
            "compare to be meaningful); use target=watcom for the "
            "layered shape judge metric."
        )
        notes.append(
            "L+N source-line columns are not available on this oracle: "
            "CAESAR2.EXE has no recoverable line info, and our MSVC "
            "compile_scratch returns no line_marks either.  Cross-reference "
            "by structure, not by line number."
        )

    # L+N anchors are populated only on Watcom (PS.EXE built -d1 + our
    # wcc386 compile uses -d1).  Reflect that to the agent so they don't
    # try to read line columns that don't exist.
    has_lines = (target == Target.WATCOM and res.build_ok)

    vr = VerifyResult(
        target=target,
        build_ok=res.build_ok,
        stderr=res.stderr,
        byte_diff=res.byte_diff,
        target_size=res.target_bytes_size,
        your_size=res.your_bytes_size,
        exact=res.exact,
        shape=_convert_shape(res.shape_distance),
        diff_rows=diff_rows,
        has_line_numbers=has_lines,
        donor=res.donor_name,
        fallthrough_callee=res.fallthrough_callee,
        is_new_best=False,
        best_so_far=None,
        notes=notes,
    )

    # save-the-best
    became_best = workspace.maybe_save_best(vr)
    vr.is_new_best = became_best
    vr.best_so_far = workspace.read_best()

    # history
    workspace.append_history({
        "type": "verify",
        "target": target.value,
        "build_ok": vr.build_ok,
        "byte_diff": vr.byte_diff,
        "exact": vr.exact,
        "shape": vr.shape.model_dump() if vr.shape else None,
        "is_new_best": vr.is_new_best,
    })
    return vr


def revert_to_best(workspace: Workspace) -> bool:
    """Restore best/scratch.c into work/scratch.c."""
    restored = workspace.revert_to_best()
    workspace.append_history({"type": "revert_to_best", "restored": restored})
    return restored


def run_census(
    *,
    workspace: Workspace,
    project: EngineProjectConfig,
) -> dict:
    """Named-local census: compile scratch.c with MSVC /Od, compare the
    ``[ebp-N]`` frame-slot set against CAESAR2.EXE's copy of the function.

    The W2 witness of ``docs/root-cause-survey-2026-07-02.md``: at /Od every
    named source local owns a distinct frame slot, so the slot-set delta is
    a census of the ORIGINAL's local-variable set vs the scratch's.  Returns
    a plain dict (typed model built in tools.census).
    """
    import difflib

    from c2.decompile._engine.runs import load_meta
    from c2.win_bytes import _slot_census, disasm_norm

    meta = load_meta(workspace.work_dir)
    fn = meta.function

    proj = project if project.active_target == "msvc" else project.for_target("msvc")
    tc = proj.toolchain()
    res = tc.compile_scratch(workspace.work_dir, fn)
    if not res.ok or res.function_bytes is None:
        return {"ok": False, "note": "MSVC compile of scratch.c failed",
                "stderr": res.stderr}
    ours_code = res.function_bytes
    mask = res.fixup_offsets
    try:
        theirs_code = tc.function_bytes(fn)
    except KeyError:
        return {"ok": False, "note": "no CAESAR2.EXE mapping for this function"}
    if not theirs_code:
        return {"ok": False, "note": "empty CAESAR2.EXE byte range (bad mapping)"}

    ours = disasm_norm(ours_code, set(mask))
    theirs = disasm_norm(theirs_code)
    sm = difflib.SequenceMatcher(
        a=[r[2] for r in ours], b=[r[2] for r in theirs], autojunk=False)
    matched = sum(b.size for b in sm.get_matching_blocks())
    quality = matched / max(len(ours), 1)
    gate = ("usable" if quality >= 0.85
            else "caution" if quality >= 0.7 else "mapping-suspect")
    fo, so = _slot_census([r[1] for r in ours])
    ft, st = _slot_census([r[1] for r in theirs])

    def _slots(slots: dict) -> list[dict]:
        return [{"slot": f"ebp-0x{d:x}", "widths": "".join(sorted(r["widths"])),
                 "n_uses": r["n_uses"], "first_use": r["first"]}
                for d, r in sorted(slots.items())]

    out = {
        "ok": True, "quality": round(quality, 3), "gate": gate,
        "frame_ours": fo, "frame_theirs": ft,
        "slots_ours": _slots(so), "slots_theirs": _slots(st),
        "delta": len(st) - len(so),
    }
    workspace.append_history({"type": "census", "quality": out["quality"],
                              "gate": gate, "delta": out["delta"]})
    return out


def run_lines(
    *,
    workspace: Workspace,
    project: EngineProjectConfig,
) -> list[dict] | str:
    """Compile scratch.c (watcom) and return the -d1 line ledger.

    Returns the ledger row dicts, or an error string on build failure.
    Uses the plain engine verify (no best-store side effects beyond the
    ordinary snapshot logic being skipped -- this path does NOT touch
    the best store).
    """
    res = _engine_verify(project, workspace.work_dir, diff=False, target="watcom")
    if not res.build_ok:
        return "build failed: " + (res.stderr.splitlines()[0] if res.stderr else "?")
    if res.line_ledger is None:
        return "no line ledger (exact match, or ledger computation failed)"
    workspace.append_history({"type": "lines",
                              "divergent": sum(1 for r in res.line_ledger
                                               if r["verdict"] != "match")})
    return res.line_ledger
