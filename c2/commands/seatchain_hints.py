"""`Seat-chain:` hint -- the certified full-chain flip verdict per
PS<->RC register swap (decomp-verify -v / regtrace --explain consumer).

For every seat_recon swap (value in RC reg R1, PS wants R2), runs
``c2.regalloc.seatchain.flip_analysis`` over the routine's trace and
compresses the verdict to one hint fragment:

    masked     PS's reg is interference-excluded -- live-range lever;
               the contributing walk rows are enumerated in `c2 seats`.
    outscored  the RC winner's CountRegMoves credits are per-instruction
               named (cq) -- de-CSE / de-name / reorder lever.
    tie-order  GivenRegisters/list-order tie -- Rule 115/28a class
               (cross-check the Byte-seat CASE verdict; D = inert).
    vetoed / not-a-candidate -- savings / type-class lever (Rule 151).

Drill-in: `c2 seats <fn>` (full dossier + evidence rows).
"""
from __future__ import annotations

from typing import Optional


def detect(name: str, rows: list[dict]) -> Optional[dict]:
    """Compute flip verdicts for the function's seat swaps.  Returns
    {chain: {rows, agree}, flips: [...]} or None (clean / no trace)."""
    from pathlib import Path
    from c2.regalloc.seat_recon import seat_diff
    import c2.regalloc as regalloc
    from c2.regalloc.replay import REG_ENC
    from c2.regalloc.seatchain import (certify_chain, flip_analysis,
                                       build_iv_index)
    from c2.commands.regtrace import _find_function

    sr = seat_diff(rows)
    swaps = sr.get("swaps") or []
    fd = sr.get("first_divergence")
    if not swaps and not fd:
        return None
    src_file, _, _, _ = _find_function(name, None)
    td = regalloc.file_trace(Path(src_file), Path("decomp/include"))
    rt = (td.get("by_func") or {}).get(name)
    if rt is None:
        return None
    cert = certify_chain(rt)
    ivx = build_iv_index(rt)
    alloc = [a for a in rt.get("alloc") or [] if a.get("reg_name") in REG_ENC]

    pairs = [(sw["rc"], sw["ps"], False) for sw in swaps]
    if not pairs and fd:
        # localized (non-systematic) divergence: the row attribution is
        # APPROXIMATE -- the diverging value may be a rover/scratch seat
        # with no allocator row at all (the Cascade hint is authoritative
        # for that case).
        pairs = [(fd["rc"], fd["ps"], True)]
    flips = []
    seen = set()
    for rc_reg, ps_reg, localized in pairs:
        if (rc_reg, ps_reg) in seen:
            continue
        seen.add((rc_reg, ps_reg))
        cand_rows = [a for a in alloc if a.get("reg_name") == rc_reg]
        if not cand_rows:
            flips.append({"rc": rc_reg, "ps": ps_reg, "verdict": "no-alloc-row",
                          "who": None, "localized": localized,
                          "note": "no allocator commit holds the RC side -- "
                                  "rover/scratch seat (lw machinery), not a "
                                  "chain lever"})
            continue
        # For a LOCALIZED divergence, seat_recon only knows the register
        # FAMILY, so several rows are seated rc_reg; the real diffing seat is
        # the one whose flip yields a concrete lever (named-local baseline
        # blocker / verified composite).  Rank by that; else prefer the
        # named local / highest savings.
        def _rank(a):
            fr = flip_analysis(a, ps_reg, ivx)
            bob = (fr.get("birth_order") or {}).get("blocker") or {}
            lrv = (fr.get("live_range") or {}).get("verdict")
            return ((2 if bob.get("var") else 0)
                    + (1 if lrv == "composite-REACHABLE" else 0), fr)
        if localized:
            ranked = sorted(((_rank(a)[0], -(a.get("savings") or 0), a)
                             for a in cand_rows), key=lambda t: (-t[0], t[1]))
            a = ranked[0][2]
        else:
            cand_rows.sort(key=lambda a: (a.get("var") is None,
                                          -(a.get("savings") or 0)))
            a = cand_rows[0]
        f = flip_analysis(a, ps_reg, ivx)
        occ = f.get("occupants") or []
        pinned = bool(occ) and all(o["pinned"] for o in occ)
        blk = f.get("blocker")
        lr = f.get("live_range") or {}
        verdict = f.get("verdict")
        if verdict == "masked":
            if lr.get("verdict") == "composite-REACHABLE":
                verdict = "masked-composite"
            elif pinned:
                verdict = "masked-pinned"
            elif blk:
                verdict = "masked-blocker"
        flips.append({"rc": rc_reg, "ps": ps_reg,
                      "who": a.get("var") or a.get("name"),
                      "blocker": (blk.get("var") or blk.get("value")) if blk else None,
                      "composite": ({"credit_ins": lr.get("credit", {}).get("ins"),
                                     "winner": lr.get("winner")}
                                    if lr.get("verdict") == "composite-REACHABLE"
                                    else None),
                      "verdict": verdict,
                      "localized": localized,
                      "n_contrib": len(f.get("contributors") or []),
                      "n_credits": len(f.get("winner_credits") or [])})
    if not flips:
        return None
    return {"chain": {"rows": cert["rows"], "agree": cert["agree"]},
            "flips": flips}


_VERDICT_GLOSS = {
    "masked": "live-range lever",
    "masked-pinned": "FIXED ABI/hard-reg PIN on the wanted reg -- no "
                     "overlapping conflict, no reorder frees it (sub-source)",
    "masked-blocker": "an overlapping conflict holds the wanted reg -- "
                      "shorten ITS range / lower savings / reorder (Rule 115)",
    "masked-composite": "VERIFIED composite: shorten the blocker's range AND "
                        "kill the winner's credit (de-CSE/de-name) -> seats it",
    "outscored": "credit lever (per-ins, de-CSE/de-name)",
    "tie-order": "order lever (Rule 115/28a; check Byte-seat CASE)",
    "vetoed": "savings lever (TooGreedy)",
    "not-a-candidate": "type-class lever (Rule 151 first)",
    "no-alloc-row": "rover/scratch (lw machinery)",
    "already": "already PS-seated (stale recon?)",
    "no-presentation": "never presented",
}


def render(hint: dict) -> str:
    ch = hint["chain"]
    parts = []
    for f in hint["flips"]:
        extra = ""
        if f["verdict"] == "masked" and f.get("n_contrib"):
            extra = f" [{f['n_contrib']} mask rows]"
        elif f["verdict"] == "outscored" and f.get("n_credits"):
            extra = f" [{f['n_credits']} named credits]"
        elif f["verdict"] == "masked-composite" and f.get("composite"):
            c = f["composite"]
            extra = (f" [shorten {f.get('blocker') or 'blocker'} + kill "
                     f"{c.get('winner')} credit @{c.get('credit_ins')}]")
        who = f.get("who") or "?"
        loc = (" [LOCALIZED divergence -- row attribution approximate; "
               "if the Cascade says rover/scratch, IT wins]"
               if f.get("localized") else "")
        parts.append(f"{who} {f['rc']}\u2192{f['ps']}: {f['verdict']}"
                     f" ({_VERDICT_GLOSS.get(f['verdict'], '?')}){extra}{loc}")
    return (f"chain {ch['agree']}/{ch['rows']} identity \u00b7 "
            + " \u00b7 ".join(parts)
            + "  \u2014 drill-in: c2 seats")
