"""binir-shape hint -- per-source-line semantic-IR comparison between PS and
our compile, for non-byte-equal functions.

PURPOSE.  ``decomp-verify`` already produces a row-by-row asm diff per
function and per-row rule hints (Reg swap, Rule 4, Rule 17b, …).  Those
hints operate at the BYTE-PATTERN level -- they spot register-letter
substitutions, jcc encoding differences, RMW shape mismatches.

What's missing:  *semantic equivalence at the source-line granularity*.
Two asm sequences can differ at every byte yet recover to IDENTICAL
high-level ops (e.g. ``mov ebx, edx; cmp ebx, …`` vs ``mov esi, edx; cmp
esi, …``).  Conversely two asm sequences can MATCH on most bytes yet
recover to DIFFERENT IR shapes on one specific line (e.g. PS used a
PRE_GETS RMW while RC used split load/op/store -- Rule 17b at exactly
that line).

binir already provides the semantic-IR recovery (``c2.binir.recover``).
The audit work proves it correct on the byte-exact corpus.  This hint
applies it to the NON-byte-exact corpus row pairs:

  * Group rows by source line (forward-fill ``row["ln"]`` from the
    first instruction of each statement).
  * For each line, run binir on the PS-side InsnT list AND the RC-side
    InsnT list.
  * Compare ``Counter(o.kind for o in ops)`` between the two.
  * VERDICT:
      - "encoding_noise" : every line's binir shape matches.
        The byte diff is pure regalloc tie-break / encoding-length
        choice -- not a semantic perturbation.  Look at existing
        Reg-swap / encoding hints, NOT at source restructuring.
      - "shape_divergence" : at least one line has divergent shapes.
        Those are the ACTIONABLE lines -- a source-level perturbation
        at those lines should change the compiled IR shape.

This is the "byte-diff-explain" feature requested -- integrated as a
first-class hint alongside Reg-swap / Frame / Sched / etc.

INVARIANT.  When ``verdict == "encoding_noise"`` the existing
register-substitution hints from ``rule_hints`` should be SUFFICIENT;
agents don't need to look for semantic levers.  When ``verdict ==
"shape_divergence"`` the listed lines are the smallest-blast-radius
targets for source-level perturbation.

OUTPUT SHAPE.  ``BinirShapeHint`` carries:

    verdict             -- "encoding_noise" | "shape_divergence" |
                           "no_lines_with_ir" (degenerate)
    lines_compared      -- int, total non-empty source lines compared
    lines_identical     -- int
    lines_divergent     -- int
    divergences         -- list[BinirShapeDivergence]
    note                -- short human-readable summary

Each ``BinirShapeDivergence`` has:

    line                -- source-line number
    ps_shape            -- {kind: count} of binir-recovered ops on PS asm
    rc_shape            -- {kind: count} of binir-recovered ops on RC asm
    only_ps             -- {kind: count} present only on PS side
    only_rc             -- {kind: count} present only on RC side
    summary             -- "PS has 1 pre_gets_mem_const, RC has 1 mov_mem_imm"
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from c2 import binir
from c2.binir import RecoveredOp


@dataclass
class BinirShapeDivergence:
    """One source line where PS and RC have semantically-different IR shapes."""

    line: int
    ps_shape: dict[str, int]
    rc_shape: dict[str, int]
    only_ps: dict[str, int]
    only_rc: dict[str, int]
    summary: str


@dataclass
class BinirShapeHint:
    """Function-level binir-shape analysis result."""

    verdict: str
    lines_compared: int = 0
    lines_identical: int = 0
    lines_divergent: int = 0
    divergences: list[BinirShapeDivergence] = field(default_factory=list)
    note: str = ""


def _group_rows_by_line(rows: list[dict]) -> dict[int, dict[str, list]]:
    """Group rows by source line, forward-filling ln=None rows.

    Returns ``{ln: {"ps": [InsnT, ...], "rc": [InsnT, ...]}}``.

    Rows before the first ``ln`` entry (function prolog) are skipped --
    they're compiler-emitted callee-save pushes that don't correspond
    to a source statement.
    """
    out: dict[int, dict[str, list]] = {}
    cur_ln: Optional[int] = None
    for row in rows:
        ln = row.get("ln")
        if ln is not None:
            cur_ln = ln
        if cur_ln is None:
            continue
        if cur_ln not in out:
            out[cur_ln] = {"ps": [], "rc": []}
        if row.get("o") is not None:
            out[cur_ln]["ps"].append(row["o"])
        if row.get("r") is not None:
            out[cur_ln]["rc"].append(row["r"])
    return out


def _shape_summary(ops: list[RecoveredOp]) -> dict[str, int]:
    """Compact per-kind histogram of recovered ops."""
    return dict(Counter(o.kind for o in ops))


def _format_divergence_summary(only_ps: dict[str, int],
                               only_rc: dict[str, int]) -> str:
    parts = []
    if only_ps:
        ps_str = ", ".join(f"{n}x {k}" for k, n in sorted(only_ps.items()))
        parts.append(f"PS has {ps_str}")
    if only_rc:
        rc_str = ", ".join(f"{n}x {k}" for k, n in sorted(only_rc.items()))
        parts.append(f"RC has {rc_str}")
    return "; ".join(parts) or "shapes differ but no asymmetric kinds"


def detect(rows: list[dict]) -> BinirShapeHint:
    """Run binir on PS-vs-RC per source line; report shape divergences.

    ``rows`` is the output of ``_build_diff_rows`` -- each row has
    ``ln`` (source line, only on first insn of each statement), ``o``
    (PS InsnT or None), ``r`` (RC InsnT or None).

    Catches all binir exceptions so a malformed instruction stream
    can't break the verify pipeline.
    """
    try:
        by_line = _group_rows_by_line(rows)
    except Exception:
        return BinirShapeHint(verdict="no_lines_with_ir",
                              note="row-grouping failed")
    if not by_line:
        return BinirShapeHint(verdict="no_lines_with_ir",
                              note="no source-line entries found "
                                   "(prolog-only diff?)")
    lines_compared = 0
    lines_identical = 0
    lines_divergent = 0
    divergences: list[BinirShapeDivergence] = []
    for ln in sorted(by_line.keys()):
        ps_insns = by_line[ln]["ps"]
        rc_insns = by_line[ln]["rc"]
        # Skip lines where one side has no instructions (insertion/deletion
        # at line boundary -- nothing to compare semantically).
        if not ps_insns or not rc_insns:
            continue
        try:
            ps_ops = binir.recover(ps_insns)
            rc_ops = binir.recover(rc_insns)
        except Exception:
            continue
        # If NEITHER side recovers anything, binir has no signal -- skip.
        if not ps_ops and not rc_ops:
            continue
        lines_compared += 1
        ps_shape = _shape_summary(ps_ops)
        rc_shape = _shape_summary(rc_ops)
        if ps_shape == rc_shape:
            lines_identical += 1
            continue
        # Divergent: identify the asymmetric kinds.
        ps_ctr = Counter(ps_shape)
        rc_ctr = Counter(rc_shape)
        only_ps = dict(ps_ctr - rc_ctr)
        only_rc = dict(rc_ctr - ps_ctr)
        lines_divergent += 1
        divergences.append(BinirShapeDivergence(
            line=ln,
            ps_shape=ps_shape,
            rc_shape=rc_shape,
            only_ps=only_ps,
            only_rc=only_rc,
            summary=_format_divergence_summary(only_ps, only_rc),
        ))
    if lines_compared == 0:
        return BinirShapeHint(
            verdict="no_lines_with_ir",
            lines_compared=0,
            note="no source lines had binir-recoverable IR on either side",
        )
    if lines_divergent == 0:
        return BinirShapeHint(
            verdict="encoding_noise",
            lines_compared=lines_compared,
            lines_identical=lines_identical,
            lines_divergent=0,
            divergences=[],
            note=(f"all {lines_identical}/{lines_compared} compared source "
                  f"lines have IDENTICAL binir-recovered IR -- the byte "
                  f"diff is pure regalloc tie-break / encoding-length noise, "
                  f"NOT a semantic perturbation.  Look at register-substitution "
                  f"or Jcc-encoding hints, not at source restructuring."),
        )
    line_list = ", ".join(str(d.line) for d in divergences[:5])
    if len(divergences) > 5:
        line_list += f", … (+{len(divergences) - 5} more)"
    # Rule 158 co-occurrence: a Watcom-folded always-true guard (e.g.
    # `uchar >= 0 &&`) roots a CSE partition and shows up as BOTH a
    # PS-only zext_byte_load (selector re-zext at the next else-if level)
    # AND a PS zero_test_jcc where RC has branch_flag_jcc (the very-busy
    # hoist landing between an AND-chain and its jcc forces an explicit
    # test).  Ground truth: evolve_land_value.  The authoritative witness
    # is the win /Od oracle: `c2 diagnose <fn>` (win-guard line) or
    # `c2 win-verify -v <fn>`.
    rule157_note = ""
    has_ps_zext = any("zext_byte_load" in d.only_ps for d in divergences)
    has_test_vs_flag = any("zero_test_jcc" in d.only_ps
                           and "branch_flag_jcc" in d.only_rc
                           for d in divergences)
    if has_ps_zext and has_test_vs_flag:
        rule157_note = ("  ⚠ Rule 158 fingerprint: PS-only zext_byte_load "
                        "+ PS zero_test_jcc vs RC branch_flag_jcc — a "
                        "FOLDED always-true guard (`x >= 0 &&`) may be "
                        "rooting a CSE partition in PS.  Check the win /Od "
                        "witness: c2 diagnose <fn> (win-guard) / "
                        "c2 win-verify -v <fn>.")
    return BinirShapeHint(
        verdict="shape_divergence",
        lines_compared=lines_compared,
        lines_identical=lines_identical,
        lines_divergent=lines_divergent,
        divergences=divergences,
        note=(f"{lines_divergent}/{lines_compared} source lines have "
              f"DIVERGENT binir-recovered IR.  Smallest-blast-radius "
              f"source-perturbation targets: line(s) {line_list}.  "
              f"Each divergence below names the asymmetric op kinds; "
              f"map those to the corresponding rule in the rules registry "
              f"(e.g. pre_gets_mem_const vs mov_mem_imm + binary-op -> "
              f"Rule 17b)." + rule157_note),
    )


def to_json(hint: BinirShapeHint) -> Optional[dict]:
    """Serialise to JSON for ``decomp-verify --json``."""
    if hint is None:
        return None
    return {
        "verdict":         hint.verdict,
        "lines_compared":  hint.lines_compared,
        "lines_identical": hint.lines_identical,
        "lines_divergent": hint.lines_divergent,
        "note":            hint.note,
        "divergences": [
            {
                "line":     d.line,
                "ps_shape": d.ps_shape,
                "rc_shape": d.rc_shape,
                "only_ps":  d.only_ps,
                "only_rc":  d.only_rc,
                "summary":  d.summary,
            }
            for d in hint.divergences
        ],
    }
