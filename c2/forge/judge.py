"""Score a candidate function (variant bytes) against a PS reference.

Produces both judges the agent loop cares about (Hard Rules #3 / #8):

  * **bytes** -- the DONE oracle (0 = byte-exact).  Computed with the
    same fixup + rel32 masking the verifier uses, so the number matches
    ``c2 decomp-verify`` exactly.
  * **shape_distance** -- the per-function judge metric (layered
    ir/width/spill/seat + ``fix_next``).  An edit that DROPS this is
    PS-faithful even if bytes rose.

A single :func:`score` call runs the disasm → diff-row → recon-bundle
pipeline once; both judges fall out together.  ~5–10 ms per variant on
typical PS functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from c2.forge.ps_ref import PSRef


@dataclass
class Score:
    """One variant's judges against PS."""

    ok: bool
    bytes: int                         # byte-diff (masked); -1 on build fail
    size: int                          # variant size
    size_delta: int                    # variant - PS size
    shape: dict[str, Any] = field(default_factory=dict)
    # ↑ {ir, width, spill, seat, shape, bytes, total, fix_next, islands,
    #    ir_total, width_total, spill_total, seat_total}
    error: str = ""
    ledger: dict[str, Any] | None = None
    seat_recon: dict[str, Any] | None = None
    # ↑ the run-ledger JSON (islands with ps_lines/rc_lines/tags, no
    #   insns) -- populated only when score() is called with
    #   want_ledger=True (the baseline; used for island-first plan
    #   ORDERING, never for filtering).

    @property
    def shape_total(self) -> int:
        """The byte-INDEPENDENT distance-to-PS (ir+width+spill+seat).  Use
        as the primary judge per Hard Rule #3."""
        return int(self.shape.get("shape", 0))

    @property
    def islands(self) -> int | None:
        """Run-ledger island count (the ir layer's fine-grained unit;
        0 = regalloc_pure).  None when the ledger was unavailable."""
        v = self.shape.get("islands")
        return int(v) if v is not None else None

    @property
    def layers(self) -> tuple[int, int, int, int, int]:
        """The FIX-ORDER layer vector ``(ir, islands, width, spill, seat)``.

        This is the honest per-function judge (AGENTS.md): compare
        LEXICOGRAPHICALLY -- an ir-layer drop is a win even when a
        downstream layer or the byte count rises.  The mixed-unit
        ``shape_total`` aggregate MASKED two real construct recoveries
        on show_battlemap_base (2026-06-30: decl_hoist ir 6->5 scored
        aggregate +3 and was buried); rank by this vector instead.

        ``islands`` sits between ir and width: the run-ledger island
        count is the ir layer's finer-grained unit, so a variant that
        collapses an island WITHIN a still-divergent run is recognised
        as progress (the ir run-count alone would tie).  When the
        ledger is unavailable (islands=None) the slot mirrors ir --
        identical information, so the comparison degrades exactly to
        the old vector and can never fabricate a win.
        """
        s = self.shape
        ir = int(s.get("ir", 0))
        isl = s.get("islands")
        return (ir, int(isl) if isl is not None else ir,
                int(s.get("width", 0)),
                int(s.get("spill", 0)), int(s.get("seat", 0)))

    @property
    def fix_next(self) -> str:
        return str(self.shape.get("fix_next", "?"))


def score(
    ps: PSRef,
    rc_bytes: bytes,
    rc_fixups: set[int] | frozenset[int],
    rc_line_marks: tuple[tuple[int, int], ...] = (),
    want_ledger: bool = False,
) -> Score:
    """Score variant bytes against the PS reference.

    Args:
        ps: cached PS reference (see :mod:`c2.forge.ps_ref`).
        rc_bytes: variant function bytes (already carved from .obj).
        rc_fixups: variant's fixup byte set, relative to the function
            start (the same offset basis ``ps.fixups`` uses).
        rc_line_marks: the variant's -d1 LINNUM marks ``((rel_off,
            line), ...)`` from the .obj.  When present (the normal
            case -- PS_CFLAGS carries -d1) the ir layer comes from the
            DUAL-MARKS run ledger (attribution-exact; islands in the
            shape dict); without them it degrades to the byte-diff-
            aligned binir count (drift-prone -- the pre-2026-07 judge
            that scored correct rotation/type fixes as regressions).
        want_ledger: also attach the run-ledger JSON (islands with
            line attribution, no insns) to ``Score.ledger`` -- used
            for the BASELINE only, to island-order the plan stream.

    Returns:
        :class:`Score` with both judges + the layered shape breakdown.
        Never raises -- a build / disasm failure is reported via
        ``ok=False`` + ``error``.
    """
    # Delegate to the verifier's existing builders so the masking,
    # capstone alignment, and binir-IR detector are exactly the same as
    # what ``c2 decomp-verify`` shows -- no parallel implementation to
    # drift out of sync.  CRITICAL: the byte count MUST come from
    # ``_compare_bytes`` (per-offset byte-equality), NOT from
    # ``_build_diff_rows``'s LCS-aligned token diff.  The latter
    # collapses per-instruction mismatches into a single "replace" row
    # and under-counts by ~5x vs the verifier's ground truth.
    try:
        from c2.commands.decomp_verify import (
            _compare_bytes,
            _recon_bundle_for_json,
        )
    except Exception as exc:                # noqa: BLE001
        return Score(ok=False, bytes=-1, size=len(rc_bytes), size_delta=0,
                     error=f"verifier import failed: {exc}")
    try:
        # Mirror the verifier exactly: compare exactly len(PS) bytes.
        # The verifier slices RC by PS's func_size and counts per-offset
        # mismatches over that range (with fixup + rel32 masking).
        # When the LE-mode carve returns MORE than len(PS) bytes (the
        # builder grabs a 64 KB slab so inter-function linker padding
        # is recoverable), we truncate here; when it returns LESS
        # (e.g. the function is at the end of _TEXT), the per-offset
        # loop simply stops at min(len, len), matching the verifier's
        # behaviour on a short tail.
        ps_len = len(ps.bytes_)
        rc_compare = rc_bytes[:ps_len] if len(rc_bytes) > ps_len else rc_bytes
        byte_diff = len(_compare_bytes(
            ps.bytes_, rc_compare, 0, 0,
            set(ps.fixups), set(rc_fixups),
        ))
    except Exception as exc:                # noqa: BLE001
        return Score(ok=False, bytes=-1, size=len(rc_bytes),
                     size_delta=len(rc_bytes) - len(ps.bytes_),
                     error=f"byte compare failed: {exc}")

    # CRITICAL: the recon must see the FUNCTION-length slice, exactly
    # like decomp-verify does.  Passing the raw carve slab (up to 64 KB)
    # made _build_diff_rows disassemble far past the function end,
    # polluting every recon layer with garbage rows (width read ~858 on
    # a 17-slot function) and DILUTING real divergences -- the reason
    # forge scored the decl_hoist and RMW-form construct recoveries
    # flat while decomp-verify saw them (2026-06-30).
    # PS marks: the FULL -d1 stream when available (the ledger needs
    # every mark; the deduped map stays for older PSRef pickles).
    ps_marks = dict(getattr(ps, "line_marks_full", ()) or ()) \
        or dict(ps.line_map)
    rc_marks = dict(rc_line_marks or ())
    bundle = _recon_bundle_for_json(
        ps.bytes_, 0,
        rc_compare, 0,
        set(ps.fixups), set(rc_fixups),
        ps_marks,
        byte_diff=byte_diff,
        recomp_line_map=rc_marks or None,
    )
    return Score(
        ok=True,
        bytes=byte_diff,
        size=len(rc_bytes),
        size_delta=len(rc_bytes) - len(ps.bytes_),
        shape=bundle.get("shape_distance") or {},
        ledger=(bundle.get("run_ledger") if want_ledger else None),
        seat_recon=bundle.get("seat_recon"),
    )


# (the LCS-row byte counter that previously lived here under-counted by
# ~5x vs ``c2 decomp-verify``'s headline metric -- replaced by a direct
# ``_compare_bytes`` call above)
