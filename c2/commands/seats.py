"""``c2 seats`` -- the certified full-chain register-seat dossier + the
counterfactual flip search (the seat-class analog of the slot-sim).

Per committed conflict, the ENTIRE decision is RECOMPUTED from inputs
(2026-07-11 certification: 6,243/6,243 rows, 100% fully recomputed):

    iv liveness (100%) -> with.regs mask (100%) -> CountRegMoves scores
    (100%, per-ins credit provenance) -> GiveBestReg pick (100%)

For a diffing function, the PS<->RC seat swaps (seat_recon) are joined
against the chain and each divergent seat gets a NAMED verdict from
``flip_analysis``:

    masked     -- PS's register is interference-excluded in RC; the
                  contributing walk rows (live/zap/result channels) are
                  the live-range levers.
    outscored  -- the RC winner's credits are named PER INSTRUCTION
                  (cq ground truth); each is a de-CSE/de-name/reorder
                  lever.
    tie-order  -- GivenRegisters-subset / list-order tie: the Rule
                  115/28a class (check Byte-seat CASE D inertness).
    vetoed / not-a-candidate -- savings / type-class levers.

Use it BEFORE grinding decl orders: the verdict says which lever class
can move the seat at all.
"""
from __future__ import annotations

import json as _json
from pathlib import Path

import typer


def seats(
    function: str = typer.Argument(..., help="function name"),
    file: str = typer.Option(None, "--file", help="TU basename"),
    want: str = typer.Option(None, "--want",
                             help="flip query 'VAR=REG' or 'REG1=REG2' "
                                  "(default: seat_recon's PS swaps)"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Full-chain seat dossier + PS-seat flip verdicts."""
    import c2.regalloc as regalloc
    from c2.regalloc.replay import REG_ENC
    from c2.regalloc.seatchain import (certify_chain, explain_row,
                                       flip_analysis, build_iv_index)
    from c2.commands.regtrace import _find_function

    cfile, _, _, _ = _find_function(function, file)
    td = regalloc.file_trace(Path(cfile), Path("decomp/include"))
    rt = (td.get("by_func") or {}).get(function)
    if rt is None:
        typer.echo(f"{function} not in {cfile}'s trace")
        raise typer.Exit(1)
    # iv full-IL snapshot index: names the value occupying a masked wanted
    # register (pinned ABI/move-elim vs shortenable live range).
    ivx = build_iv_index(rt)

    rows = [a for a in rt.get("alloc") or [] if a.get("reg_name") in REG_ENC]
    cert = certify_chain(rt)
    explains = [(a, explain_row(a)) for a in rows]

    # -- flip targets: --want override, else seat_recon swaps ------------
    targets: list[tuple[dict, str, str]] = []   # (row, why, want_reg)
    if want and "=" in want:
        lhs, reg = want.split("=", 1)
        lhs = lhs.strip()
        reg = reg.strip().upper()
        # accept: a named local (`var`), a register name (REG1=REG2), the
        # full anon-temp id (`6c168804`), or the short `t.8804` / bare-hex
        # suffix form other tools print.
        suffix = lhs[2:] if lhs.startswith("t.") else lhs
        for a, ex in explains:
            if ex is None:
                continue
            name = str(a.get("name") or "")
            if (a.get("var") == lhs or a.get("reg_name") == lhs.upper()
                    or name == lhs
                    or (len(suffix) >= 3 and name.endswith(suffix.lower()))):
                targets.append((a, f"--want {lhs}", reg))
        if not targets:
            typer.echo(f"  (--want: no chain row matched {lhs!r}; rows are "
                       f"named locals or anon ids like 6c168804 / t.8804)")
    else:
        vpath = Path(".c2-cache/verify.json")
        if vpath.exists():
            v = _json.loads(vpath.read_text())
            rec = next((e for e in v.get("functions", [])
                        if e.get("name") == function), None)
            sr = (rec or {}).get("seat_recon") or {}
            for sw in sr.get("swaps") or []:
                for a, ex in explains:
                    if ex and a.get("reg_name") == sw["rc"]:
                        targets.append(
                            (a, f"seat_recon {sw['rc']}<->{sw['ps']} "
                                f"(conf {sw.get('confidence')})", sw["ps"]))
            # No clean swap, but a LOCALIZED first-divergence: auto-surface
            # the composite lever for the diffing seat.  seat_recon localizes
            # at register-FAMILY granularity (no conflict id), so several
            # RC-seated rows flip-analyze as masked; the REAL divergence is
            # distinguished by a concrete (named-local / composite-REACHABLE)
            # blocker.  Rank those first and cap, labelling as candidates.
            fd = sr.get("first_divergence")
            if not targets and fd and fd.get("rc") and fd.get("ps"):
                from c2.regalloc.seatchain import flip_analysis as _fa
                cands_fd = []
                for a, ex in explains:
                    if not ex or a.get("reg_name") != fd["rc"]:
                        continue
                    r = _fa(a, fd["ps"], ivx)
                    if r.get("verdict") != "masked":
                        continue
                    blk = r.get("blocker") or {}
                    bob = (r.get("birth_order") or {}).get("blocker") or {}
                    lrv = (r.get("live_range") or {}).get("verdict")
                    # rank: a NAMED-local baseline blocker (birth-order) is
                    # the fingerprint of the real divergence; byte-exact rows
                    # get anonymous blockers.  Verified composite next.
                    score = ((2 if bob.get("var") else 0)
                             + (1 if lrv == "composite-REACHABLE" else 0))
                    if r.get("occupants") or blk:
                        cands_fd.append((score, a))
                cands_fd.sort(key=lambda t: -t[0])
                for _s, a in cands_fd[:1]:
                    targets.append(
                        (a, f"localized first-divergence @L{fd.get('ln')} "
                            f"{fd['rc']}<->{fd['ps']} (best-guess row -- "
                            f"--want <conf>={fd['ps']} to pin)", fd["ps"]))

    flips = [{"row_var": a.get("var"), "row_name": a.get("name"),
              "why": why, **flip_analysis(a, wreg, ivx)}
             for a, why, wreg in targets]

    if json_out:
        out = {"function": function, "chain": cert,
               "rows": [ex for _, ex in explains if ex], "flips": flips}
        typer.echo(_json.dumps(out, indent=1, default=str))
        return

    typer.echo(f"{function}: full-chain identity "
               f"{cert['agree']}/{cert['rows']} "
               f"(fully recomputed {cert['recomputed_full']})")
    for a, ex in explains:
        if ex is None:
            continue
        sv = " ".join(f"{e['cand']}:{e['saves']}" for e in ex["scores"])
        cr = sum(len(v) for v in ex["credits"].values())
        typer.echo(f"  {ex['var'] or ex['name']:>14} sav={ex['savings']} "
                   f"-> {ex['actual']}  [{ex['class']}] "
                   f"mask={ex['mask']:#x}({'calc' if ex['mask_prov'] == 'recomputed' else 'rec'}) "
                   f"scores[{sv}] credits:{cr}"
                   f"{'' if ex['agree'] else '  !! chain-miss'}")
    if not flips:
        typer.echo("  (no seat-swap targets: seat_recon clean or no "
                   "verify.json entry; use --want VAR=REG)")
    for f in flips:
        typer.echo(f"  FLIP {f['row_var'] or f['row_name']} -> {f.get('want')}"
                   f"  [{f['why']}]  verdict: {f['verdict']}")
        if f.get("note"):
            typer.echo(f"       {f['note']}")
        for o in (f.get("occupants") or [])[:4]:
            if o["pinned"]:
                typer.echo(f"       occupant<- FIXED placement in {f.get('want')} "
                           f"(hard-reg/ABI pin) at ins {o.get('ins')}")
            else:
                who = f"local `{o['var']}`" if o.get("var") else f"temp {o['value']}"
                typer.echo(f"       occupant<- {who} sav={o['savings']} in "
                           f"{f.get('want')} (range {o['range']}"
                           f"{', allocated first' if o['blocks_first'] else ''})")
        for c in (f.get("contributors") or [])[:6]:
            typer.echo(f"       mask<- ins {c['ins']} op {c['opcode']:#x} "
                       f"({'+'.join(c['channels'])})")
        for c in (f.get("winner_credits") or [])[:6]:
            typer.echo(f"       credit<- ins {c['ins']} +{c['credit']}")
