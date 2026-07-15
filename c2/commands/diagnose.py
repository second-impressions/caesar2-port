"""c2 diagnose -- the canonical per-function triage in ONE command.

Fuses the byte-diff verdict, the shape **concordance** verdict, the
regalloc-invariant const-audit, the binir residue class, the layered
shape-distance ({ir,width,spill,seat,bytes,fix_next}), the located
``divergent_lines`` (each divergence anchored to the PS ``-d1`` source
line that produced it), the L4 slice attribution + trace verification,
and the de-invent / add-local source-shape lever -- with a routed
``next`` step.

Run this FIRST on a diffing function to know whether the residue is
shape, a constant bug, or regalloc before drilling in.

FIX-ORDER (work the highest non-zero layer first -- ``fix_next`` names
it): ir (wrong ops/control-flow -- source shape) -> width (wrong local
type, signed/byte) -> spill (frame/live-range) -> seat (register-identity
tie) -> bytes-only residue == pure regalloc/encoding (classify, don't
grind).  ``shape == 0`` means the source shape matches PS.

The structured core is ``diagnose_data()``; the Typer ``diagnose``
command renders it (or ``--json`` dumps it).
"""

from __future__ import annotations

import json
from typing import Annotated, Optional

import typer


# ── data core ────────────────────────────────────────────────────────────
def diagnose_data(
    function: str,
    *,
    file: Optional[str] = None,
    mac: bool = False,
    full: bool = False,
) -> dict:
    """The canonical per-function loop in one call: byte-diff verdict +
    shape concordance + regalloc-invariant constant audit + binir residue
    + layered shape-distance + located divergent lines + the de-invent /
    add-local lever, with a routed next-step.  ``mac`` defaults False (the
    Mac/JVM witness is slow)."""
    # The verify / shape / const-audit projections live in c2.toolapi.
    # Imported lazily so this module loads without pulling the facade.
    from c2.toolapi import verify, shape, const_audit, _const_signal, \
        _divergent_lines

    v = verify(function, file=file, full=full)
    if not v.get("found"):
        return {"name": function, "found": False, "verify": v}
    s = shape(function, mac=mac)
    c = const_audit(function)

    bd = v.get("byte_diff") or 0
    conc = s.get("concordance")
    const_sig = _const_signal(c)
    fh = v.get("frame_hint") or {}
    frame_root = bool(fh.get("is_root")) and bool(fh.get("delta"))
    # is the diff dominated by register-identity swaps? (then a plain-const
    # flag is almost always regalloc register-reuse, not a source bug)
    rh = v.get("rule_hints") or {}
    if isinstance(rh, dict) and sum(rh.values()):
        regswap_frac = (rh.get("Reg swap", 0) + rh.get("Byte-reg swap", 0)) \
            / sum(rh.values())
    else:
        regswap_frac = 0.0

    # route the next step the way the workflow reasons
    sd_layers = (v.get("shape_distance") or {})
    sd_fix_next = sd_layers.get("fix_next")
    # width side-hint: any function carrying a non-trivial width layer
    # (>=2 divergent type-ops) usually closes bytes via a local's TYPE fix
    # -- even when fix_next is ir or frame.  (The old `c2 permute` width
    # enumerator was removed 2026-06; regtrace NAMES the value + form, and
    # `c2 sweep` covers the mechanical reorder space.)  The hint is
    # APPENDED to the primary routing below, not the primary action.
    sd_width = int(sd_layers.get("width") or 0)
    width_side_hint = (
        "  |  also: width N>=2 divergent -- c2 regtrace <fn> names the"
        " value + the jge/movsx/sar form (Rule 151/49); fix the local's"
        " type, then `c2 sweep <fn>` for the mechanical battery."
        if sd_width >= 2 else "")
    if bd == 0:
        nxt = "byte-exact -- run c2 line-compare to confirm shape, then commit"
    elif const_sig == "high":
        nxt = ("fix the const-audit divergence first -- a REAL layer-1 bug "
               "(off-by-one boundary / eq / out-of-order arg), regalloc-invariant")
    elif conc is not None and conc < 0.75:
        nxt = ("LOW concordance -- the recovered SHAPE is wrong; fix shape "
               "before regalloc (c2 mac-decompile)")
    elif frame_root:
        nxt = (f"frame-shift ROOT: PS reserves {fh.get('ps_frame')}b vs RC "
               f"{fh.get('rc_frame')}b ({fh.get('delta'):+d}b) -- fix the stack "
               "frame first; it is usually the root of the regalloc cascade. "
               + (fh.get("fix") or ""))
    elif sd_fix_next == "width":
        # fix_next=width => ir is already 0 (or empty), so the highest non-
        # zero layer is type-signedness/width divergence on locals.  (The
        # old `c2 permute --only width` enumerator was removed 2026-06;
        # regtrace names the value + jge/movsx/sar form, and `c2 sweep`
        # covers the mechanical reorder battery afterwards.)
        nxt = ("width-layer dominant (ir done; types differ) -- "
               "c2 regtrace <fn> names the value + the jge/movsx/sar form "
               "(Rule 151/49); fix that local's type, re-verify, then "
               "`c2 sweep <fn>` for the mechanical battery; the dossier "
               "width rows name the offending locals")
        width_side_hint = ""   # already the primary hint
    elif const_sig == "plain":
        # plain-channel const only: on a shape-correct, reg-swap-heavy
        # function this is usually register-REUSE noise (e.g. `add edx, 4`
        # vs `add edx, ecx`), NOT a wrong literal.  Make the agent confirm.
        nxt = ("a plain-const divergence is flagged but the SHAPE is right"
               + (" and the diff is reg-swap-dominated" if regswap_frac >= 0.5 else "")
               + " -- it is most likely register-reuse noise, not a source bug. "
               "Read c2 decomp-verify -v -f <fn>: if the const is a reused register "
               "it is regalloc (c2 regtrace); only a genuinely wrong literal is a "
               "const fix")
    else:
        rl = v.get("run_ledger") or {}
        bs = v.get("binir_shape") or {}
        if rl.get("verdict") == "regalloc_pure":
            nxt = ("run-ledger: ALL insns match register-blind -- the whole "
                   "diff is register seats / slots / encoding; do NOT "
                   "restructure the source.  c2 regtrace for the lever; "
                   "for a ROVER seat, decomp-verify -v's Rover hint carries "
                   "the fit windows + [lw census] candidates, and "
                   "`c2 spell <fn> <candidate.c>` screens spellings without "
                   "byte compiles (INERT@TREE / INERT@BURN / LIVE)")
        elif rl.get("verdict") == "shape_islands":
            nxt = (f"run-ledger: {rl.get('islands')} statement-shape "
                   f"island(s) ({rl.get('matched')}/{rl.get('ps_total')} "
                   "insns already match register-blind) -- work the islands "
                   f"top-down: c2 ledger {function} shows each with PS asm "
                   "+ our source line + a family tag")
        elif bs.get("lines_divergent") == 0:
            nxt = "IR identical -- pure regalloc residue; c2 regtrace for the lever"
        else:
            nxt = "HIGH concordance, still diffing -- residue is regalloc; c2 regtrace"

    # Pull the layered-verdict slice attribution + the trace-verification
    # note (Score sb/sbi/sbs + MergeIndex mic/mip/mi/mir probes give
    # empirical ground truth about which compile-phase decisions ACTUALLY
    # happened; the note flags MATCH / ENRICH / CONTRADICT against the
    # cascade's slice claim).
    layered = None
    trace_note = None
    trace_activity = None
    try:
        import json as _json
        from pathlib import Path as _Path
        from c2.commands.regalloc_verdict import (
            layered_verdict, trace_verification_note, trace_activity_summary)
        _vp = _Path(".c2-cache/verify.json")
        if _vp.exists():
            _vcache = _json.loads(_vp.read_text())
            _rec = next((x for x in _vcache.get("functions", [])
                         if x.get("name") == function), None)
            if _rec is not None and _rec.get("diff_byte_count", 0) > 0:
                layered = layered_verdict(_rec, name=function, reconcile=True)
                trace_note = trace_verification_note(
                    function, layered.get("steerable", ""))
                trace_activity = trace_activity_summary(function)
    except (ImportError, OSError, KeyError, _json.JSONDecodeError):
        pass

    # local-hints: the de-invent / add-local source-shape lever (most temps
    # were Watcom's, not the source's -- de-inventing is a top byte lever).
    local_hints = None
    if bd > 0:
        try:
            from c2.commands.local_hints import tool_summary as _lh_summary
            _lh = _lh_summary(function)
            if _lh.get("available") and (
                    _lh["deinvent"] or _lh["addlocal"]
                    or _lh["n_real"] or _lh["n_inline"]):
                local_hints = {
                    "deinvent": _lh["deinvent"], "addlocal": _lh["addlocal"],
                    "ps_inline_count": _lh["ps_inline_count"],
                    "n_real": _lh["n_real"], "n_inline": _lh["n_inline"],
                    "n_abstain": _lh["n_abstain"],
                }
        except Exception:  # noqa: BLE001
            local_hints = None
    # surface a secondary width hint when applicable (ir-layer gets
    # fixed first, but width may still close some bytes cheaply).
    if width_side_hint and nxt and "width-layer dominant" not in nxt:
        nxt = nxt + width_side_hint
    # surface the lever in the routed next-step: a de-invent / add-local
    # mismatch is a LAYER-1 source-shape fix (delete the invented caching
    # local / add the named local), to do before grinding regalloc.
    if local_hints and (local_hints["deinvent"] or local_hints["addlocal"]):
        _lever = []
        if local_hints["deinvent"]:
            _lever.append("DE-INVENT " + ", ".join(local_hints["deinvent"])
                          + " (delete the caching local, read the global inline)")
        if local_hints["addlocal"]:
            _lever.append("ADD-LOCAL " + ", ".join(local_hints["addlocal"])
                          + " (introduce `T v = global;`)")
        _msg = ("local-hints source lever (do first): " + "; ".join(_lever)
                + " -- c2 local-hints " + function + " --vs-source")
        # prepend unless a higher-priority layer-1 (const) fix already routed
        nxt = _msg if const_sig != "high" else nxt + "  |  " + _msg

    # W2 witness: win /Od named-local census (root-cause-survey-2026-07-02 §2)
    win_census = None
    try:
        from c2 import win_bytes as _wb
        _cv = _wb.census_func(function)
        if _cv.ok:
            win_census = {"quality": round(_cv.quality, 2), "gate": _cv.gate,
                          "slots_ours": len(_cv.slots_ours),
                          "slots_theirs": len(_cv.slots_theirs),
                          "delta": _cv.delta}
        else:
            win_census = {"gate": "unavailable", "note": _cv.note}
    except Exception:
        pass

    # Rule 158 witness: a Watcom-FOLDED always-true guard (`uchar >= 0 &&`)
    # emits zero PS bytes but still roots a CSE partition; the MSVC /Od
    # CAESAR2.EXE build keeps it literally, so the aligned win diff shows a
    # one-sided zero-compare run.  Ground truth: evolve_land_value.
    win_guard = None
    try:
        from c2 import win_bytes as _wb2
        _gp = _wb2.guard_probe(function)
        if _gp.get("available") and _gp.get("hits"):
            win_guard = _gp
    except Exception:
        pass

    # goto-topology witness: /Od preserves every jump-statement as its own
    # E9 jmp (docs/msvc-od-goto-signal.md), so a funnel-profile mismatch vs
    # our MSVC compile names missing/invented goto/continue/break structure.
    win_goto = None
    try:
        from c2.goto_topology import tool_summary as _gt_summary
        _gv = _gt_summary(function)
        # only surface when it carries signal: available with a non-clean
        # verdict, or PS-side corroboration when the win witness is absent
        if (_gv.get("available") and _gv.get("verdict") != "consistent") \
                or (not _gv.get("available") and _gv.get("ps_evidence")):
            win_goto = _gv
    except Exception:
        pass

    return {
        "name": function, "found": True,
        "byte_diff": bd, "exact": v.get("exact"),
        "win": v.get("win"),            # CAESAR2.EXE second-oracle hint
        "win_census": win_census,       # W2 named-local census verdict
        "win_guard": win_guard,         # Rule 158 folded-guard witness
        "win_goto": win_goto,           # jump-statement topology witness
        "shape_distance": v.get("shape_distance"),
        "divergent_lines": _divergent_lines(v.get("raw") or {}),
        "concordance": conc, "const_clean": c.get("clean"),
        "const_signal": const_sig, "regswap_frac": round(regswap_frac, 2),
        "frame_root": frame_root, "frame_hint": fh or None,
        "layered_verdict": layered,    # slice + steerable + stack
        "trace_note": trace_note,      # GREEN/YELLOW/RED verification
        "trace_activity": trace_activity,  # sb/sbi/sbs/mip/mi counts
        "local_hints": local_hints,    # de-invent / add-local lever
        "next": nxt,
        "verify": v, "shape": s, "const": c,
    }


# ── shared shape-distance formatter ──────────────────────────────────────
def fmt_shape_dist(sd: Optional[dict]) -> Optional[str]:
    """Layered distance-to-PS (fix-order: ir -> width -> spill -> seat).
    ir = wrong ops/control-flow (source shape); width = wrong local type
    (signed/byte); spill = frame/live-range; seat = register-identity tie
    (often sub-source).  Work ``fix_next`` first; shape == 0 => residue is
    pure regalloc/encoding (document the evidence + deprioritise; the
    function stays open until byte-exact).  Bytes are deliberately
    NOT surfaced here -- they are a corpus-progress figure only (see
    ``decomp-verify`` summary), never a per-function judge metric."""
    if not sd:
        return None
    if sd.get("shape") == 0:
        return (f"shape vs PS: MATCHES (ir/width/spill/seat all 0)  "
                f"-- residue is regalloc/encoding")

    def lyr(n: str) -> str:
        v = sd.get(n, 0) or 0
        t = sd.get(n + "_total", 0) or 0
        cell = f"{n} {v}/{t}" if t else f"{n} {v}"
        if n == "ir" and sd.get("islands") is not None:
            cell += f" (isl {sd['islands']})"
        return cell

    layers = " \u00b7 ".join(lyr(n) for n in ("ir", "width", "spill", "seat"))
    return (f"shape vs PS: {layers}  "
            f"-> fix-next: {sd.get('fix_next')}")


def _fmt_num(n) -> str:
    return f"{n:.2f}" if isinstance(n, (int, float)) else str(n)


# ── renderer ─────────────────────────────────────────────────────────────
def _render(r: dict) -> None:
    if r.get("found") is False:
        typer.secho(f"{r['name']}: not a compared FUNCTION (stub or unknown).",
                    fg="yellow")
        return
    from c2.regalloc.seat_recon import fmt_shape_layers as _flyr
    sd = r.get("shape_distance") or {}
    sh = (f", shape {_flyr(sd)} → fix-next {sd.get('fix_next','?')}"
          if sd else "")
    head = (f"{r['name']} -- "
            + ("byte-exact \u2713" if r.get("exact")
               else (f"diff, shape {sd.get('shape','?')}" if sd else "diff"))
            + f", concordance {_fmt_num(r.get('concordance'))}{sh}"
            + (", const clean" if r.get("const_clean") else ", const NOT clean"))
    typer.secho(head, bold=True)

    c = r.get("const")
    if c and not c.get("clean"):
        for ch, d in (c.get("channels") or {}).items():
            ob = (f"  off-by-one: {','.join(d['off_by_one'])}"
                  if d.get("off_by_one") else "")
            typer.echo(f"const-audit {ch}: PS-only={json.dumps(d.get('ps_only'))} "
                       f"RC-only={json.dumps(d.get('rc_only'))}{ob}")
        if c.get("arg_swap"):
            typer.echo(f"const-audit arg-swap: {json.dumps(c['arg_swap'])}")

    fh = r.get("frame_hint")
    if fh and fh.get("delta"):
        typer.echo(f"frame: PS {fh.get('ps_frame')}b vs RC {fh.get('rc_frame')}b "
                   f"({'+' if fh.get('delta', 0) >= 0 else ''}{fh.get('delta')}b"
                   f"{', ROOT' if fh.get('is_root') else ''}) "
                   f"{fh.get('direction') or ''}")

    sdl = fmt_shape_dist(r.get("shape_distance")
                         or (r.get("verify") or {}).get("shape_distance"))
    if sdl:
        typer.echo(sdl)

    dl = r.get("divergent_lines")
    if dl:
        typer.echo("divergent source lines (fix is HERE -- c2 dossier focuses on "
                   "the first divergence with PS asm + RC asm + Mac/Win oracle "
                   "in one pane; this list shows all of them by source order):")
        for e in dl[:12]:
            issues = "  \u00b7  ".join(f"[{i['layer']}] {i['detail']}"
                                       for i in e["issues"])
            lbl = "RC-only" if e["line"] < 0 else f"L{e['line']}"
            typer.echo(f"  {lbl}  {issues}")
        if len(dl) > 12:
            typer.echo(f"  ... (+{len(dl) - 12} more lines)")

    rl = (r.get("verify") or {}).get("run_ledger")
    if rl:
        typer.echo(f"run-ledger: {rl.get('verdict')} -- "
                   f"{rl.get('matched')}/{rl.get('ps_total')} insns match "
                   f"register-blind, {rl.get('islands')} island(s) over "
                   f"{rl.get('ps_runs_divergent')}/{rl.get('ps_runs_total')} "
                   f"PS line-runs (detail: c2 ledger <fn>)")
    bs = (r.get("verify") or {}).get("binir_shape")
    if bs and not rl:
        typer.echo(f"binir-shape: {bs.get('lines_identical')}/"
                   f"{bs.get('lines_compared')} identical, "
                   f"{bs.get('lines_divergent')} divergent")

    rh = (r.get("verify") or {}).get("rule_hints")
    if rh:
        if isinstance(rh, dict):
            hints = ", ".join(f"{k}\u00d7{v}" for k, v in rh.items())
        elif isinstance(rh, list):
            hints = ", ".join(rh)
        else:
            hints = str(rh)
        if hints:
            typer.echo(f"rule hints: {hints}")

    lv = r.get("layered_verdict")
    if lv and lv.get("steerable"):
        typer.echo(f"slice: L{lv.get('layer')} {lv['steerable']}  "
                   f"-- {lv.get('lever') or ''}")
    if r.get("trace_note"):
        typer.echo(f"trace: {r['trace_note']}")
    ta = r.get("trace_activity")
    if ta and (ta.get("sbi") or ta.get("sbs") or ta.get("mi_attempts")
               or ta.get("mir_inner")):
        typer.echo(f"trace-counts: sb={ta.get('sb')} sbi={ta.get('sbi')} "
                   f"sbs={ta.get('sbs')}  \u00b7  "
                   f"mic-attempts={ta.get('mi_attempts')} "
                   f"mi-fused={ta.get('mi_active')} mir-inner={ta.get('mir_inner')}")

    lh = r.get("local_hints")
    if lh:
        if lh.get("deinvent"):
            typer.echo("local-hints DE-INVENT (delete the caching local, read "
                       f"inline): {', '.join(lh['deinvent'])}")
        if lh.get("addlocal"):
            typer.echo("local-hints ADD-LOCAL (introduce `T v = global;`): "
                       f"{', '.join(lh['addlocal'])}")
        if not lh.get("deinvent") and not lh.get("addlocal"):
            typer.echo(f"local-hints: {lh.get('n_real')} REAL / "
                       f"{lh.get('n_inline')} INLINE / {lh.get('n_abstain')} "
                       "abstain (agrees with source)")

    win = r.get("win")
    if win and win.get("available"):
        typer.echo(f"win: CAESAR2.EXE {win.get('win_va')} ({win.get('confidence')}) "
                   "-- c2 win-verify / c2 win-decompile available")

    wc = r.get("win_census")
    if wc:
        if wc.get("gate") == "unavailable":
            typer.echo(f"win-census: unavailable ({wc.get('note')})")
        else:
            d = wc["delta"]
            verdict = ("local set MATCHES the /Od witness" if d == 0 else
                       (f"original has {d} MORE named local(s) -- NAME them "
                        "(c2 win-census -v shows the slot profiles)" if d > 0 else
                        f"our source has {-d} EXTRA local(s) -- §13 invented-"
                        "local candidates (c2 win-census -v)"))
            trust = "" if wc["gate"] == "usable" else f"  ⚠ {wc['gate']} mapping -- verify before acting"
            typer.echo(f"win-census: Q={wc['quality']:.2f} slots "
                       f"{wc['slots_ours']}/{wc['slots_theirs']} Δ={d:+d} -- {verdict}{trust}")

    wgu = r.get("win_guard")
    if wgu:
        for h in wgu.get("hits", []):
            run = "; ".join(h["insns"])
            ctx = "; ".join(h.get("after") or [])
            if h["side"] == "theirs":
                typer.echo(
                    "win-guard: Rule 158 — CAESAR2-only zero-compare guard "
                    f"[{run}] before [{ctx}] — the original source has an "
                    "always-true guard (e.g. `x >= 0 &&`) that Watcom FOLDS "
                    "to zero bytes but which ROOTS a CSE partition (changes "
                    "hoist/zext/tail-merge shape).  ADD the guard to the "
                    "matching condition.")
            else:
                typer.echo(
                    "win-guard: Rule 158 (inverse) — our source has a "
                    f"zero-compare guard [{run}] the original LACKS — "
                    "REMOVE it.")

    wg = r.get("win_goto")
    if wg:
        if wg.get("available"):
            src = wg.get("src") or {}
            trust = ("" if wg.get("gate") == "usable"
                     else f"  ⚠ {wg.get('gate')} mapping")
            verdict = {
                "missing-goto": "original has jump-stmt structure we LACK "
                                "(goto/continue/break)",
                "extra-goto": "our source has jump-stmt structure the "
                              "original LACKS",
                "mixed": "jump-stmt topology diverges both ways",
            }.get(wg.get("verdict"), wg.get("verdict"))
            typer.echo(
                f"win-goto: {wg.get('verdict').upper()} — {verdict}; "
                f"WIN funnels {wg.get('win_funnels')} vs ours "
                f"{wg.get('our_funnels')}, jmps {wg.get('win_jmps')}/"
                f"{wg.get('our_jmps')} (src gotos {src.get('gotos')}, labels "
                f"{src.get('labels')}){trust} — c2 win-census "
                + r["name"])
        if wg.get("ps_evidence"):
            evs = ", ".join(f"+{e['offset']:#x}×{e['indeg']}"
                            for e in wg["ps_evidence"][:6])
            typer.echo(f"ps-goto: {len(wg['ps_evidence'])} detached multi-pred "
                       f"block(s) in PS.EXE ({evs}) — non-structured control "
                       "flow the Watcom side can't fake")

    typer.echo(f"-> next: {r.get('next')}")


# ── typer command ────────────────────────────────────────────────────────
def diagnose(
    function: Annotated[str, typer.Argument(help="Function to triage.")],
    file: Annotated[
        Optional[str],
        typer.Option("--file", help="Source file to disambiguate."),
    ] = None,
    mac: Annotated[
        bool,
        typer.Option("--mac/--no-mac",
                     help="Include the Mac witness (slower, JVM)."),
    ] = False,
    full: Annotated[
        bool,
        typer.Option("--full-hints/--no-full-hints",
                     help="Full hints in the raw verify record."),
    ] = False,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Per-function triage: byte diff + concordance + const-audit + binir
    residue + layered shape-distance + located divergent lines + the
    de-invent/add-local lever, with a routed next step.  Run FIRST on a
    diffing function."""
    data = diagnose_data(function, file=file, mac=mac, full=full)
    if as_json:
        typer.echo(json.dumps(data, default=str, indent=2))
        return
    _render(data)
