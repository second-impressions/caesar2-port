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

from c2.decompile._engine.format.asm import apply_line_numbers
from c2.decompile._engine.format.diff import (
    align_and_classify,
    count_real_diffs,
    render_diff,
)
from c2.decompile._engine.project import ProjectConfig
from c2.decompile._engine.runs import load_meta


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
    line_ledger: list[dict] | None = None
    """Per-source-line -d1 ledger (watcom only): one entry per PS line
    mark region with instruction counts on both sides, the scratch.c
    lines whose marks fall in the region, and the binir op delta.  The
    primary line-by-line witness for the agent's ``lines()`` tool."""


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

    # ---- Standalone-also-tail-merged detection.
    #
    # ``normalize_target`` ALWAYS splices the donor's shared tail onto
    # PS's bytes, because historically the bundler's scratch.c held
    # only the target function -- wcc386 couldn't tail-merge in that
    # universe and emitted an inline epilogue.  With the new
    # include-split compose path the donor IS present in the standalone
    # TU, so wcc386 tail-merges too -- emitting a ``jmp donor+N``
    # exactly like the real-project build.  Splicing PS in that case
    # creates an artificial inline-epilogue that the standalone
    # rightly does not produce.
    #
    # Detect the case (boundary is a known jmp offset, ``your_bytes``
    # at that boundary starts with the ``e9`` ``jmp rel32`` opcode)
    # and SKIP the splice -- compare PS's raw jmp-form against the
    # standalone's jmp-form, masking the jmp's 4 displacement bytes on
    # both sides (linker-resolved, so unequal even when bodies match).
    # Decide whether to keep PS's normalize_target splice (which
    # appends the donor's shared tail onto PS's bytes) or roll back to
    # PS's raw bytes.  The splice was correct under the LEGACY bundler
    # (scratch.c carried only the target function -- wcc386 could not
    # tail-merge in that universe, so it always emitted an inline
    # epilogue and PS-spliced matched standalone-inline).  Under the
    # include-split compose the standalone has the full TU, and three
    # outcomes are possible:
    #
    #   (a) Standalone ALSO tail-merged: ``your_bytes`` at the
    #       boundary starts with 0xE9 (5b jmp rel32) or 0xEB (2b
    #       jmp short rel8).  Compare jmp-form vs jmp-form; mask the
    #       disp bytes (linker-resolved per-build).
    #   (b) Standalone's body is SHORTER than the boundary (e.g.
    #       diffing function whose source emits fewer instructions
    #       than PS) -- there's no jmp to compare against.  Compare
    #       raw PS body vs raw standalone body.
    #   (c) Standalone matched PS exactly UP TO the boundary but did
    #       NOT tail-merge (rare; the donor was reachable but
    #       wcc386's tail-merge cost model declined).  Same as (b):
    #       compare un-spliced.
    #
    # In all three cases the right move is the same -- DROP the
    # splice.  The splice is correct ONLY when standalone has no
    # donor and emitted the inline epilogue (the legacy-bundler
    # universe, which the include-split has eliminated).  We default
    # to un-splicing whenever a donor was detected, then add the
    # standalone jmp's disp bytes to the fixup mask if (a) applies.
    extra_jmp_mask: frozenset[int] = frozenset()
    if norm.donor_boundary is not None:
        # Detect (a): standalone also tail-merged.
        jmp_disp_len = 0
        if norm.donor_boundary < len(your_bytes):
            op = your_bytes[norm.donor_boundary]
            if op == 0xE9 and norm.donor_boundary + 5 <= len(your_bytes):
                jmp_disp_len = 4
            elif op == 0xEB and norm.donor_boundary + 2 <= len(your_bytes):
                jmp_disp_len = 1
        if jmp_disp_len:
            extra_jmp_mask = frozenset(
                range(norm.donor_boundary + 1, norm.donor_boundary + 1 + jmp_disp_len)
            )
        # Roll back to raw PS bytes regardless -- the donor's appended
        # tail does NOT belong on PS's side in the include-split world.
        target_bytes = raw_bytes
        from c2.decompile._engine.toolchains.base import NormalizedTarget
        norm = NormalizedTarget(
            bytes_=raw_bytes,
            fixup_offsets=raw_fix,
            line_marks=raw_lines,
            extra_reloc_offsets=norm.extra_reloc_offsets,
            donor_name=norm.donor_name,
            donor_boundary=norm.donor_boundary,
            donor_first_line=None,
            donor_tail_size=0,
            fallthrough_callee=norm.fallthrough_callee,
            fallthrough_added_bytes=norm.fallthrough_added_bytes,
            raw_dependent_size=norm.raw_dependent_size,
        )

    # Disassemble both sides at their FULL length (so intra-fn `.L_X`
    # resolution sees the right function bounds).  Truncation is applied
    # to the COMPARE step only.
    target_fix_full = norm.fixup_offsets | norm.extra_reloc_offsets | extra_jmp_mask
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

    # The classifier compares rows by raw bytes at relocation sites
    # (modrm/sib carry the register identity; only the fixup-positioned
    # disp bytes are masked).  This matches the project verifier's strict
    # byte compare and prevents the standalone verify from silently
    # accepting register-swaps or addressing-mode changes as ``equal``
    # (which used to hide IR divergence -- ``get_region_over`` reported
    # ``ir 0/0`` from the agent while the real-TU verifier saw
    # ``ir 5/11``; same bytes, different masking).
    drows = align_and_classify(
        target_rows_cmp, your_rows_cmp,
        target_fix=frozenset(target_fix_full),
        yours_fix=frozenset(res.fixup_offsets),
    )

    # The byte counter uses PER-SIDE fixup masking to match the project
    # verifier (``c2.commands.decomp_verify._compare_bytes``):
    #
    #   * LE-fixup positions: PER-SIDE replace with 0 then compare.
    #     A position that is a fixup on ONLY ONE side is genuinely
    #     different (a linker-resolved address byte on one side vs.
    #     an arbitrary literal on the other) and MUST count as a diff;
    #     only positions that are fixups on BOTH sides naturally
    #     compare 0 == 0 and are exempt.
    #   * Intra-instruction call/jmp/Jcc rel-disp positions: UNION-SKIP
    #     (positions that are rel-disp on EITHER side are exempt --
    #     they're link-positional, never a real-code difference).
    #
    # Previously this used union masking for fixups too, which under-
    # counted by ~120 bytes on functions like ``clear_an_area`` (project:
    # 465 / agent: 345), making the standalone harness look like it was
    # producing different codegen than the real-TU build.  The codegen
    # is identical -- the byte counter just disagreed.
    #
    # ``target_fix_full`` carries the PS-side LE-fixup positions PLUS
    # the rel-disp positions PS contributes.  ``res.fixup_offsets``
    # carries the standalone OBJ's LE-fixup positions.  ``extra_jmp_mask``
    # is the standalone's tail-merge jmp disp -- a STANDALONE-side rel-
    # disp position (NOT a PS-side fixup), hence it goes into the YOUR
    # mask not the TARGET mask.
    target_byte_fix = frozenset(target_fix_full)
    your_byte_fix = frozenset(res.fixup_offsets) | frozenset(extra_jmp_mask)
    real_byte_diff = _count_real_byte_diffs(
        target_cmp, your_cmp,
        target_byte_fix, your_byte_fix,
    )
    real_row_count = count_real_diffs(drows)
    sizes_match = len(target_cmp) == len(your_cmp)
    exact = (real_byte_diff == 0 and real_row_count == 0 and sizes_match)

    # Exact-with-note exemptions -- MIRROR the project verifier
    # (c2 decomp-verify) so the sandbox oracle agrees with it.  When the
    # only residual byte diffs are a tail-merge donor flip, a Rule 4
    # cmp-swap, or trailing jump-table filler, PS and the recomp are
    # body-equivalent; the project verifier counts them exact.  Without
    # this the sandbox over-counts on ~7 byte-exact functions
    # (draw_a_dias, swap_2_figures, entering_new_square, ...).
    exempt_note: str | None = None
    if (not exact) and sizes_match and real_byte_diff > 0:
        try:
            from c2.commands.decomp_verify import (
                _compare_bytes, _donor_flip_exit_only,
                _rule4_only_diffs, _trailing_table_pad_only,
            )
            tfix0 = set(target_byte_fix)
            yfix0 = set(your_byte_fix)
            # function-local offsets (0): the masks are already local.
            diffs0 = _compare_bytes(target_cmp, your_cmp, 0, 0, tfix0, yfix0)
            if diffs0:
                if _trailing_table_pad_only(target_cmp, your_cmp,
                                            diffs0, 0, tfix0):
                    exempt_note = "trailing jump-table filler"
                elif _rule4_only_diffs(target_cmp, your_cmp,
                                       diffs0) is not None:
                    exempt_note = "Rule 4 cmp-swap (a<b vs b>a)"
                else:
                    dn = _donor_flip_exit_only(
                        target_cmp, your_cmp, diffs0,
                        orig_off=0, recomp_off=0,
                        orig_fix=tfix0, recomp_fix=yfix0)
                    if dn is not None:
                        exempt_note = f"tail-merge donor flip ({dn})"
        except Exception:
            exempt_note = None      # never block verify on the exemption probe
        if exempt_note is not None:
            exact = True
            real_byte_diff = 0

    headline_lines = render_diff(drows, full=diff, context=context)
    if not headline_lines:
        headline_lines = []

    # Compute the layered shape distance (ir/width/spill/seat + fix_next).
    # Only meaningful against watcom (msvc encoding is too different).
    shape_dict = None
    line_ledger = None
    if target == "watcom" and not exact:
        try:
            shape_dict = _compute_shape_distance(
                drows, real_byte_diff,
                target_bytes=target_cmp, your_bytes=your_cmp,
                target_fix=target_byte_fix, your_fix=your_byte_fix,
                ps_line_map=dict(norm.line_marks or ()),
                rc_line_map=dict(res.line_marks or ()),
            )
        except Exception:
            shape_dict = None     # never block verify on a metric failure
        try:
            line_ledger = _line_ledger(
                target_rows_cmp, your_rows_cmp, target_cmp, your_cmp,
                target_byte_fix, your_byte_fix)
        except Exception:
            line_ledger = None    # never block verify on a metric failure
    elif target == "watcom" and exact:
        shape_dict = {"shape": 0, "ir": 0, "width": 0, "spill": 0, "seat": 0,
                      "ir_total": 0, "width_total": 0, "spill_total": 0,
                      "seat_total": 0, "fix_next": "done", "islands": 0}

    cmp_size = len(target_cmp)
    target_tag = f"[{target}]"
    if exact:
        summary = f"0/{cmp_size} \u2713  {target_tag}"
        if exempt_note is not None:
            summary += f"  [~exact: {exempt_note}]"
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
        line_ledger=line_ledger,
    )


def _line_ledger(target_rows, your_rows, target_bytes, your_bytes,
                 target_fix, your_fix) -> list[dict]:
    """Per-source-line ``-d1`` ledger from the DUAL-MARKS run ledger.

    THE primary line-by-line witness (the binir op histogram is the
    secondary lens).  Attribution is EXACT at any function size: each
    side is segmented by its OWN -d1 marks (PS.EXE's debug directory /
    the scratch compile's line table) and the REGISTER-BLIND canonical
    instruction streams are aligned (``c2.runledger``).  The old
    implementation attributed RC instructions to PS lines through the
    byte-diff alignment, which drifts past the first length-changing
    diff -- producing phantom per-line divergences on big functions.

    One entry per PS line RUN, in PS emission order:

    * ``ps_line``  -- the PS ``L+N`` relative line of the run.
    * ``rc_lines`` -- the ABSOLUTE scratch.c line numbers of the RC
      instructions ALIGNED to this run (matched register-blind, or
      islanded against it) -- the lines to edit.
    * ``ps_insns`` / ``rc_insns`` -- instruction counts per side.
    * ``ps_only_ops`` / ``rc_only_ops`` -- binir constructs on the
      divergent (island) part only.
    * ``tags``     -- island family tags (width / zext-idiom /
      signedness / loop-form / slot / frame / const / ops).
    * ``verdict``  -- ps_only | rc_only | form | pack | match.
    * ``order_flip`` -- statement-order divergence smell (Hard Rule #8).

    Donor (tail-merge ``D+N``) rows are excluded -- they are the
    donor's statements, not this function's.
    """
    from collections import Counter

    from c2 import binir as _binir
    from c2.runledger import build_ledger, canon_stream

    def _rel(lbl: str) -> int | None:
        if lbl.startswith("L+"):
            try:
                return int(lbl[2:])
            except ValueError:
                return None
        return None

    ps_rows = [r for r in target_rows if not r.is_donor]
    rc_rows = list(your_rows)
    ps_insns = [(r.offset, r.size, r.raw,
                 f"{r.mnemonic} {r.op_str}".strip()) for r in ps_rows]
    rc_insns = [(r.offset, r.size, r.raw,
                 f"{r.mnemonic} {r.op_str}".strip()) for r in rc_rows]
    ps_marks = {r.offset: _rel(r.line_label) for r in ps_rows
                if _rel(r.line_label) is not None}
    rc_marks = {r.offset: r.scratch_line for r in rc_rows
                if r.scratch_line is not None}
    if not ps_marks or not rc_marks:
        return []
    ps_stream = canon_stream(ps_insns, ps_marks, set(target_fix or ()),
                             target_bytes)
    rc_stream = canon_stream(rc_insns, rc_marks, set(your_fix or ()),
                             your_bytes)
    led = build_ledger(ps_stream, rc_stream)
    pair_rc_by_ps = dict(led.matched_pairs)

    def _ops(idxs, insns) -> Counter:
        part = [insns[k] for k in idxs]
        if not part:
            return Counter()
        try:
            return Counter(o.kind for o in _binir.recover(part))
        except Exception:
            return Counter()

    # PS line runs (contiguous stretches of one forward-filled line value)
    runs: list[list] = []
    for k, ins in enumerate(ps_stream):
        if runs and runs[-1][0] == ins.line:
            runs[-1][2] = k
        else:
            runs.append([ins.line, k, k])

    out: list[dict] = []
    prev_ps: int | None = None
    prev_rc: int | None = None
    emitted_rc_only: set[int] = set()
    for line, lo, hi in runs:
        if line is None:
            continue                    # prologue before the first mark
        isls = [isl for isl in led.islands
                if isl.ps_span[0] <= hi + 1 and isl.ps_span[1] > lo
                and isl.ps_span[1] > isl.ps_span[0]]
        rc_idx: list[int] = sorted(
            [pair_rc_by_ps[k] for k in range(lo, hi + 1)
             if k in pair_rc_by_ps]
            + [j for isl in isls for j in range(*isl.rc_span)])
        rc_lines: list[int] = []
        for j in rc_idx:
            sl = rc_stream[j].line
            if sl is not None and (not rc_lines or rc_lines[-1] != sl):
                rc_lines.append(sl)
        island_ps = [k for isl in isls for k in range(*isl.ps_span)
                     if lo <= k <= hi]
        island_rc = [j for isl in isls for j in range(*isl.rc_span)]
        only_ps_ops = dict(_ops(island_ps, ps_insns))
        only_rc_ops = dict(_ops(island_rc, rc_insns))
        tags = sorted({t for isl in isls for t in isl.tags})
        ps_n = hi - lo + 1
        rc_n = len(rc_idx)
        if not isls:
            verdict = "pack" if len(rc_lines) > 1 else "match"
        elif island_ps and not island_rc:
            verdict = "ps_only"
        elif island_rc and not island_ps:
            verdict = "rc_only"
        else:
            verdict = "form"
        rc_first = rc_lines[0] if rc_lines else None
        order_flip = False
        if (prev_ps is not None and prev_rc is not None
                and rc_first is not None):
            ps_dir = line - prev_ps
            rc_dir = rc_first - prev_rc
            order_flip = (ps_dir < 0 <= rc_dir) or (rc_dir < 0 <= ps_dir)
        prev_ps = line
        if rc_first is not None:
            prev_rc = rc_first
        out.append({
            "ps_line": line, "rc_lines": rc_lines,
            "ps_insns": ps_n, "rc_insns": rc_n,
            "ps_only_ops": only_ps_ops, "rc_only_ops": only_rc_ops,
            "ps_head": ps_stream[lo].text,
            "rc_head": rc_stream[rc_idx[0]].text if rc_idx else "",
            "verdict": verdict, "order_flip": order_flip,
            "tags": tags,
        })
        for isl in isls:
            emitted_rc_only.update(range(*isl.rc_span))

    # Pure-insert (rc_only) islands not attached to any PS run: our
    # source adds statements PS lacks.  Emit one row per island so the
    # agent sees the scratch lines to remove/inline.
    for isl in led.islands:
        if isl.kind != "rc_only":
            continue
        idxs = [j for j in range(*isl.rc_span) if j not in emitted_rc_only]
        if not idxs:
            continue
        rc_lines = []
        for j in idxs:
            sl = rc_stream[j].line
            if sl is not None and (not rc_lines or rc_lines[-1] != sl):
                rc_lines.append(sl)
        anchor = None
        k = isl.ps_span[0] - 1
        if 0 <= k < len(ps_stream):
            anchor = ps_stream[k].line
        out.append({
            "ps_line": anchor if anchor is not None else -1,
            "rc_lines": rc_lines,
            "ps_insns": 0, "rc_insns": len(idxs),
            "ps_only_ops": {}, "rc_only_ops": dict(_ops(idxs, rc_insns)),
            "ps_head": "",
            "rc_head": rc_stream[idxs[0]].text,
            "verdict": "rc_only", "order_flip": False,
            "tags": isl.tags,
        })
    return out


def _drow_to_shape_dict(r) -> dict:
    """Convert a c2-ext DiffRow into the dict form the project shape
    detectors expect.

    ``seat_recon`` / ``type_width_diff`` / ``spill_diff`` read
    ``ps``/``rc`` -> ``{'asm': str}``; ``binir_shape_hints.detect``
    reads ``o``/``r`` -> ``InsnT`` (``(offset, size, raw_bytes,
    asm_text)``).  Provide BOTH so IR + width + spill + seat layers
    all compute -- earlier versions only populated ``ps``/``rc`` and
    the IR layer silently skipped (``lines_compared == 0`` ->
    ``ir 0/0`` for every function, hiding all IR divergence from the
    agent's metric, which the user surfaced as a bug).

    Our row's ``line_label`` is like 'L+12' or 'D+0'; the integer line
    number is what the detectors read.
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

    def _insnt(row) -> tuple | None:
        if row is None:
            return None
        return (row.offset, row.size, row.raw, _asm(row))

    off = (r.target.offset if r.target is not None
           else (r.yours.offset if r.yours is not None else 0))
    ln = _ln(r.target.line_label if r.target is not None
             else (r.yours.line_label if r.yours is not None else ""))
    return {
        "ps": {"asm": _asm(r.target)} if r.target is not None else None,
        "rc": {"asm": _asm(r.yours)} if r.yours is not None else None,
        "o":  _insnt(r.target),
        "r":  _insnt(r.yours),
        "off": off,
        "ln": ln,
    }


def _compute_shape_distance(
    drows, byte_diff: int,
    *,
    target_bytes: bytes | None = None,
    your_bytes: bytes | None = None,
    target_fix: frozenset[int] | None = None,
    your_fix: frozenset[int] | None = None,
    ps_line_map: dict[int, int] | None = None,
    rc_line_map: dict[int, int] | None = None,
) -> dict:
    """Layered shape distance -- IDENTICAL to the project verifier.

    When the function-local bytes/fixups/PS-line-map are supplied, this
    runs the EXACT SAME code path as ``c2 decomp-verify``
    (``_recon_bundle_for_json`` -> ``_build_diff_rows`` ->
    ``binir_shape_hints.detect``), so the sandbox's ir/width/spill/seat
    numbers match the real verifier byte-for-byte.

    Why this matters: the sandbox's own ``align_and_classify`` pairs PS
    and RC instructions differently than ``_build_diff_rows`` (which
    aligns on MASKED byte keys via difflib, so a register-seat or
    Jcc-encoding difference stays "equal" and does NOT shift the line
    grouping).  The old path grouped mis-paired instructions per source
    line, so binir compared different statements and reported PHANTOM ir
    divergence (e.g. grey_a_screen ir6 where the real verifier sees ir0),
    sending agents to invent source structure on already-correct code.

    Falls back to the legacy DiffRow path only if the exact inputs are
    unavailable (should not happen on the normal watcom verify path).

    NOTE: unequal PS/RC sizes are FINE for the exact path -- the project
    verifier itself compares differently-sized functions through the
    same ``_build_diff_rows`` machinery.  The old ``len == len`` gate
    silently dropped every size-mismatched (i.e. most shape-diverging)
    function to the legacy path, which has NO run-ledger: the sandbox
    then reported binir-based ir and ``islands=None`` -- the "decompile
    tool doesn't report islands" bug (2026-07-03).
    """
    if target_bytes is not None and your_bytes is not None:
        try:
            from c2.commands.decomp_verify import _recon_bundle_for_json
            bundle = _recon_bundle_for_json(
                target_bytes, 0, your_bytes, 0,
                set(target_fix or ()), set(your_fix or ()),
                dict(ps_line_map or {}), byte_diff,
                recomp_line_map=dict(rc_line_map or {}) or None,
            )
            sd = bundle.get("shape_distance")
            if sd is not None:
                return sd
        except Exception:
            pass  # fall back to the legacy path below
    from c2.regalloc.seat_recon import shape_distance as _shape_distance
    dict_rows = [_drow_to_shape_dict(r) for r in drows]
    return _shape_distance(dict_rows, byte_diff=byte_diff)


def _format_shape_line(sd: dict) -> str:
    """Format the shape distance for the rendered output.  ``isl K`` after
    the ir layer = the run-ledger island count (the ir layer's
    fine-grained unit; 0 = regalloc_pure -- every insn matches
    register-blind, stop restructuring)."""
    if sd.get("shape", 0) == 0 and sd.get("fix_next") == "done":
        return ("shape: MATCHES (ir/width/spill/seat all 0)  "
                "-- residue is regalloc/encoding")

    def lyr(n: str) -> str:
        v = sd.get(n, 0) or 0
        t = sd.get(n + "_total", 0) or 0
        cell = f"{n} {v}/{t}" if t else f"{n} {v}"
        if n == "ir" and sd.get("islands") is not None:
            cell += f" (isl {sd['islands']})"
        return cell

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
    """Byte-level diff count mirroring ``decomp_verify._compare_bytes``.

    Two masking layers, exactly as the project verifier does it:

    1. **Intra-instruction relative call/jmp/Jcc displacement**:
       UNION-SKIP -- positions that are within a ``call``/``jmp``/``Jcc``
       displacement on EITHER side are exempt (link-positional noise,
       not real codegen).  Computed PER-SIDE on the actual bytes
       (project's ``_rel_call_jmp_disp_mask``); the union is then
       skipped.

    2. **LE-fixup table positions**: PER-SIDE replace-with-0 then
       compare.  A position that is a fixup on ONLY ONE side counts as
       a real diff (linker-resolved address on one side vs. an arbitrary
       literal on the other); only BOTH-side fixups naturally compare
       0 == 0 and are exempt.

    Previously this used UNION masking for fixups too, which under-
    counted by ~120 bytes on functions like ``clear_an_area``
    (project: 465 / agent: 345), making the standalone harness look
    like it was producing different codegen than the real-TU build.
    The codegen is identical -- the byte counter just disagreed.

    A position past the shorter side's end is treated as ``None``,
    which is never equal to a real byte and never equal to a
    fixup-masked 0, so size differences contribute to the diff like
    the project verifier reports.
    """
    # Layer 1: per-side rel-disp masks, then UNION-skip.
    from c2.commands.decomp_verify import _rel_call_jmp_disp_mask
    rel_target = _rel_call_jmp_disp_mask(target)
    rel_yours = _rel_call_jmp_disp_mask(yours)
    rel_skip = rel_target | rel_yours

    n = max(len(target), len(yours))
    diff = 0
    for i in range(n):
        if i in rel_skip:
            continue
        if i < len(target):
            a: int | None = 0 if i in target_fix else target[i]
        else:
            a = None
        if i < len(yours):
            b: int | None = 0 if i in your_fix else yours[i]
        else:
            b = None
        if a != b:
            diff += 1
    return diff
