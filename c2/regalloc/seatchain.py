"""The certified FULL-CHAIN register-seat calculator + counterfactual
flip analysis.

With every layer of the 10.0a allocator now ported and corpus-certified
(2026-07-10/11), a conflict's register seat is DERIVABLE from the trace
substrate instead of merely recorded:

    iv snapshot (one-vintage liveness)          liveness.py   100%
      -> with.regs mask                         neighbours.py 100%
      -> CountRegMoves scores                   replay.crm10a_v2 100%
      -> GiveBestReg pick                       replay.select_register 100%
    (+ conflict/temp sorts + slots              sort/shellsort_sim 100%)

``explain_row`` recomputes a committed conflict's ENTIRE decision from
inputs (mask from the gi walk + graph, scores from the walk + alias
ring, pick from the candidate order + GivenRegisters) and checks each
stage against the recorded truth.  ``certify_chain`` is the identity
gate.  ``flip_analysis`` is the NEW capability: enumerate the minimal
INPUT change that would move the seat to a wanted register --

    masked   -- the wanted reg is excluded: name WHICH recorded ins rows
                put its bits into with.regs (live-range levers), or
                report a TooGreedy veto.
    outscored-- the winner's credits are NAMED per instruction
                (cq ground truth): each crediting ins is a de-CSE /
                reorder / de-name lever.
    tie      -- decided by GivenRegisters-subset then list order:
                the Rule 115/28a order-lever class (or CASE D inert).

This is the seat-class analog of the slot-sim's "ONE fresh temp at
nt[86] flips it" verdicts: named levers, not grinding.

Scope caveats (documented, measured):
* Chain identity uses each presentation's OWN commit-window snapshot;
  cross-commit feedback (earlier picks seeding later masks/credits) is
  real and visible in the inputs -- a flip of an EARLY seat invalidates
  later rows' recorded inputs (the analysis flags rows whose inputs
  contain register-name feedback).
* Rows without the v45+ substrate (own_walk/crm_tree) fall back to
  recorded masks/scores -- still exact, just not counterfactual-capable.
"""
from __future__ import annotations

from typing import Optional

from c2.regalloc.replay import (REG_ENC, crm10a_v2, select_register)
from c2.regalloc import neighbours

REG_NAME_BY_ENC = {v: k for k, v in REG_ENC.items()}


def _mask(row: dict) -> tuple[Optional[int], str]:
    """(with.regs, provenance) -- recomputed when the substrate allows."""
    m = neighbours.with_regs(row)
    if m is not None:
        return m, "recomputed"
    m = row.get("commit_withregs")
    if m is None:
        m = row.get("withregs")
    return m, "recorded"


def _scores(row: dict, cands: list[str]) -> tuple[list[dict], str]:
    out = []
    prov = "recomputed"
    for c in cands:
        enc = REG_ENC.get(c)
        if enc is None:
            continue
        v = crm10a_v2(row, enc)
        if v is None:
            prov = "recorded"
            break
        out.append({"cand": c, "saves": v})
    if prov == "recorded":
        out = row.get("commit_cand_scores") or row.get("cand_scores") or []
    return out, prov


def explain_row(row: dict) -> Optional[dict]:
    """Recompute one committed conflict's full seat decision.  Returns a
    dict with per-stage values + provenance + agreement flags, or None
    for rows that never presented (no candidates)."""
    cands = row.get("commit_tree_cands") or row.get("tree_cands")
    if not cands:
        return None
    mask, mask_prov = _mask(row)
    vetoes = set(row.get("commit_tg_veto") or row.get("tg_veto") or [])
    surviving = []
    for c in cands:
        enc = REG_ENC.get(c)
        if enc is None or c in vetoes:
            continue
        if mask is not None and (enc & mask):
            continue
        surviving.append(c)
    scores, score_prov = _scores(row, surviving)
    given = row.get("commit_given_regs")
    if given is None:
        given = row.get("given_before")
    pick = select_register(scores, given)
    actual = row.get("reg_name")
    # per-candidate credit provenance (cq ground truth)
    credits: dict[str, list] = {}
    last: dict[str, int] = {}
    for e in row.get("crm_events") or []:
        d = e["total"] - last.get(e["cand"], 0)
        last[e["cand"]] = e["total"]
        if d:
            credits.setdefault(e["cand"], []).append(
                {"ins": e["ins"], "credit": d})
    # decision class
    sv = {e["cand"]: e["saves"] for e in scores}
    best = max(sv.values()) if sv else 0
    ties = [c for c in sv if sv[c] == best]
    if not scores:
        klass = "no-candidates"
    elif len(ties) == 1:
        klass = "score"
    elif isinstance(given, int) and any(
            (REG_ENC[c] & given) == REG_ENC[c] for c in ties
            if c in REG_ENC):
        klass = "given-subset-tie"
    else:
        klass = "list-order-tie"
    return {
        "var": row.get("var"), "name": row.get("name"),
        "savings": row.get("savings"),
        "mask": mask, "mask_prov": mask_prov,
        "cands": cands, "vetoes": sorted(vetoes),
        "surviving": surviving,
        "scores": scores, "score_prov": score_prov,
        "credits": credits,
        "given": given, "pick": pick, "actual": actual,
        "agree": pick == actual, "class": klass,
    }


def certify_chain(rt: dict) -> dict:
    """Full-chain identity gate for one routine: recomputed pick ==
    committed register for every presentable row."""
    res = {"rows": 0, "agree": 0, "recomputed_full": 0, "misses": []}
    for a in rt.get("alloc") or []:
        if a.get("reg_name") not in REG_ENC:
            continue
        ex = explain_row(a)
        if ex is None:
            continue
        res["rows"] += 1
        if ex["mask_prov"] == "recomputed" and ex["score_prov"] == "recomputed":
            res["recomputed_full"] += 1
        if ex["agree"]:
            res["agree"] += 1
        elif len(res["misses"]) < 6:
            res["misses"].append({"var": ex["var"], "name": ex["name"],
                                  "pick": ex["pick"], "actual": ex["actual"],
                                  "class": ex["class"]})
    return res


def mask_contributors(row: dict, want: str) -> list[dict]:
    """Which recorded walk rows put the wanted register's bits into
    with.regs?  Each is a LIVE-RANGE lever: the named ins where some
    value holding `want` is live across / zapped."""
    enc = REG_ENC.get(want)
    if enc is None:
        return []
    out = []
    for i in row.get("own_walk") or []:
        hit = []
        if i.get("live_regs") is not None and (i["live_regs"] & enc):
            hit.append("live")
        if i.get("zap_reg") and (i["zap_reg"] & enc):
            hit.append("zap")
        if i.get("result_reg") and (i["result_reg"] & enc):
            hit.append("result")
        if hit:
            out.append({"ins": i.get("ins"), "opcode": i["opcode"],
                        "channels": hit})
    return out


def _as_int(x):
    return int(x, 16) if isinstance(x, str) else x


def build_iv_index(rt: dict) -> dict:
    """Routine attribution context for the masked-verdict occupant search:

      ``emit_ord``  ins-ptr -> emission ordinal (il_walks order) -- a total
                    order for comparing conflict live ranges reliably
                    (commit_ins_range endpoints are IL ptrs, NOT ordered).
      ``iv``        ins-ptr -> iv full-IL snapshot row (res_reg/op0_reg) --
                    the FALLBACK fixed-placement (arg/hard-reg) detector when
                    NO allocated conflict overlaps the wanted register.

    (Kept the name ``build_iv_index`` for call-site stability.)
    """
    ivx: dict = {}
    emit_ord: dict = {}
    k = 0
    for wlk in rt.get("il_walks") or []:
        for blk in wlk.get("blocks") or []:
            for ins in blk.get("ins") or []:
                key = _as_int(ins.get("ins"))
                ivx[key] = ins
                emit_ord.setdefault(key, k)
                k += 1
    return {"iv": ivx, "emit_ord": emit_ord, "alloc": rt.get("alloc") or [],
            "presort": rt.get("presort") or []}


def birth_order_flip(ctx: dict, row: dict, want: str) -> dict:
    """Birth-order (ConfBefore create-order) ACTUATOR.

    Equal-savings conflicts are ordered by the unstable ShellSort over
    ConfList = reverse creation order (docs/regalloc-tiebreak-findings.md);
    the source lever is last-use motion (a value created last sorts first).
    This replays the FULL pick cascade with the target moved to every
    position in its savings tie group and reports a VERIFIED verdict:

      reorder-REACHABLE  some create-order lands `want` -- the flip + its
                         side-effect re-seats are returned (each must match
                         a PS seat).  Realize via last-use motion (Rule
                         115/28a), NOT a decl swap.
      reorder-INERT      `want` stays masked at EVERY tie-group position:
                         the exclusion is a baseline interference from a
                         HIGHER-savings neighbour (which always allocates
                         first) -- no create-order change can win it; the
                         lever is live-range (shorten that neighbour's
                         range) or savings.  Names the blocker.

    This turns the masked-verdict's "try Rule 115" guess into a checked
    answer (build_city_item nt[60]->ECX: INERT, blocker tgfx_b sav=13).
    """
    from c2.regalloc.replay import build_graph, replay_order
    from c2.regalloc.sort import shell_sort, conf_before
    rows = [a for a in ctx.get("alloc") or [] if a.get("reg_name") in REG_ENC]
    tname = row.get("name")
    ti = next((i for i, a in enumerate(rows) if a.get("name") == tname), None)
    if ti is None:
        return {"verdict": "no-row"}
    graph = build_graph(rows)
    ident = replay_order(rows, list(range(len(rows))), graph)
    ip = {e["idx"]: e["pick"] for e in ident}
    if ip.get(ti) == want:
        return {"verdict": "already"}
    pre0 = [e for e in (ctx.get("presort") or []) if e.get("round", 0) == 0]
    if not pre0:
        return {"verdict": "no-presort"}
    arr = [dict(e) for e in pre0]
    shell_sort(arr, lambda a, b: conf_before(a["savings"], b["savings"]))
    n2r = {a.get("conf"): i for i, a in enumerate(rows)}
    ao = [n2r[e["node"]] for e in arr if e["node"] in n2r]
    seen = set(ao)
    ao += [i for i in range(len(rows)) if i not in seen]
    tsav = row.get("savings") or 0
    tie = [p for p, ri in enumerate(ao) if (rows[ri].get("savings") or 0) == tsav]
    if not tie:
        return {"verdict": "no-tie"}
    # try every position in the tie group (front is the strongest)
    for tp in sorted(set([min(tie)] + tie)):
        o = list(ao)
        o.remove(ti)
        o.insert(tp, ti)
        pk = {e["idx"]: e["pick"] for e in replay_order(rows, o, graph)}
        if pk.get(ti) == want:
            se = [{"row": rows[i].get("var") or rows[i]["name"],
                   "from": ip.get(i), "to": p}
                  for i, p in pk.items() if i != ti and p != ip.get(i)]
            return {"verdict": "reorder-REACHABLE", "tie_group": len(tie),
                    "via": f"target created to tie-position {tp}",
                    "side_effects": se}
    # inert: name the higher-savings baseline blocker seated in `want`
    occ = [o for o in mask_occupants(row, want, ctx)
           if not o.get("pinned") and o.get("blocks_first")]
    blk = occ[0] if occ else None
    return {"verdict": "reorder-INERT", "tie_group": len(tie),
            "blocker": blk,
            "reason": ("`want` stays masked at every tie-group position -- "
                       "a higher-savings neighbour holds it (baseline "
                       "interference, always allocated first); live-range / "
                       "savings lever only, NOT create-order")}


def _range_ord(a: dict, emit_ord: dict):
    cr = a.get("commit_ins_range")
    if not cr:
        return None
    o0 = emit_ord.get(_as_int(cr[0]))
    o1 = emit_ord.get(_as_int(cr[1]))
    if o0 is None or o1 is None:
        return None
    return (min(o0, o1), max(o0, o1))


def mask_occupants(row: dict, want: str, ctx: dict) -> list[dict]:
    """Name WHICH value occupies the wanted register across the conflict's
    live range -- the piece `mask_contributors` (bare `live_regs` bitmask,
    no value identity) cannot recover.

    The RELIABLE signal is the set of ALLOCATED conflicts seated in `want`
    whose committed live range OVERLAPS the target's (compared by emission
    ordinal).  The higher-savings overlapper is allocated FIRST and is the
    actual blocker; because it is an ordinary conflict (usually a named
    local), the lever is real: shorten its range / lower its savings /
    reorder (Rule 115) -- NOT "sub-source".

    Only when NO allocated conflict overlaps do we fall back to the iv
    snapshot's res_reg to detect a genuine FIXED placement (an ABI call-arg
    / hard-reg pin held in exactly `want`), which no reorder can free.

    (History: a first cut attributed the occupant via the iv snapshot's
    per-ins name ptrs -- but wcc386 RECYCLES name ptrs (AllocFrl), so a
    coalesced self-move `mov ECX<-ECX` was mis-read as a "pinned arg"
    constant when the real blocker was the sav=13 named local `tgfx_b`
    overlapping nt[60] in build_city_item.  Conflict-range overlap is
    recycling-proof.)
    """
    enc = REG_ENC.get(want)
    if enc is None or not ctx:
        return []
    emit_ord = ctx.get("emit_ord") or {}
    alloc = ctx.get("alloc") or []
    tr = _range_ord(row, emit_ord)
    out = []
    if tr is not None:
        sav0 = row.get("savings") or 0
        # more than one conflict seated in `want` => their TRUE live ranges
        # are disjoint (they cannot co-occupy a register), so a wide hull
        # that merely spans the target is a FALSE positive -- the genuine
        # competitor is the one whose range tightly brackets the target
        # (and, for a swap, is EQUAL rank: the ConfBefore create-order tie).
        # Rank: equal-rank first, then tightest range span.
        for a in alloc:
            if a is row or a.get("reg_name") != want:
                continue
            r = _range_ord(a, emit_ord)
            if r and not (r[1] < tr[0] or r[0] > tr[1]):
                sav = a.get("savings") or 0
                out.append({"value": a.get("name"), "var": a.get("var"),
                            "savings": sav, "range": r,
                            "span": r[1] - r[0],
                            "tie": sav == sav0,
                            "blocks_first": sav > sav0,
                            "pinned": False})
        # equal-rank tie competitors first (the Rule 115 lever), then the
        # tightest-range overlapper; wide-hull higher-savings ones sink.
        out.sort(key=lambda o: (not o["tie"], o["span"]))
    if out:
        return out
    # fallback: no allocated conflict overlaps -> genuine fixed placement
    ivx = ctx.get("iv") or {}
    seen = set()
    for i in row.get("own_walk") or []:
        iv = ivx.get(_as_int(i.get("ins")))
        if not iv:
            continue
        for chan, rk in (("result", "res_reg"), ("op0", "op0_reg")):
            reg = iv.get(rk)
            if reg == enc:                       # held in EXACTLY want = pin
                key = (iv.get("ins"), iv.get(chan))
                if key in seen:
                    continue
                seen.add(key)
                out.append({"value": iv.get(chan), "var": None,
                            "savings": None, "ins": iv.get("ins"),
                            "pinned": True})
    return out


def live_range_flip(ctx: dict, row: dict, want: str) -> dict:
    """Live-range (interference) ACTUATOR -- the P5 counterfactual.

    A masked seat whose `want` is held by a HIGHER-savings overlapping
    conflict can only be freed by shortening THAT conflict's range (it
    always allocates first; no reorder wins -- see birth_order_flip).  This
    replays the counterfactual "the blocker(s) no longer cover this value"
    by clearing `want` from the target's baseline mask, recomputes scores
    (crm10a_v2) for the newly-unmasked candidate, and reports what actually
    happens:

      lr-REACHABLE  the target picks `want` -> shortening the blocker's
                    range closes it (name the blocker; byte-verify).
      lr+credit     `want` is freed but the target is still OUTSCORED by
                    another candidate (a CountRegMoves credit) -- a
                    COMPOSITE: shorten the blocker AND kill the winner's
                    credit (de-CSE/de-name) or mask the winner.  Names both.
      lr-INERT      another `want`-holder remains, or `want` is not even a
                    tree candidate (type class).

    build_city_item nt[60]->ECX: freeing ECX (shorten tgfx_b) is NOT enough
    -- EBX still outscores ECX 4 vs 2 via the education-base copy credit;
    the actuator reports the lr+credit composite instead of a false
    'shorten tgfx_b' close.
    """
    from c2.regalloc.replay import build_graph, replay_order, crm10a_v2
    import copy as _copy
    enc = REG_ENC.get(want)
    if enc is None:
        return {"verdict": "no-reg"}
    occ = [o for o in mask_occupants(row, want, ctx) if not o.get("pinned")]
    blockers = [o for o in occ if o.get("blocks_first")]
    rows = [a for a in ctx.get("alloc") or [] if a.get("reg_name") in REG_ENC]
    tname = row.get("name")
    ti = next((i for i, a in enumerate(rows) if a.get("name") == tname), None)
    if ti is None:
        return {"verdict": "no-row"}
    if want not in (row.get("tree_cands") or []):
        return {"verdict": "lr-INERT", "reason":
                f"{want} is not a tree candidate (register-class/width "
                f"lever, not live-range)"}
    graph = build_graph(rows)
    ident = {e["idx"]: e["pick"] for e in
             replay_order(rows, list(range(len(rows))), graph)}
    if ident.get(ti) == want:
        return {"verdict": "already"}
    # counterfactual: clear `want` from the target's baseline (blocker(s)
    # shortened so they no longer cover this value).
    g2 = _copy.deepcopy(graph)
    g2[ti]["baseline"] &= ~enc
    pk = {e["idx"]: e["pick"] for e in
          replay_order(rows, list(range(len(rows))), g2)}
    if pk.get(ti) == want:
        return {"verdict": "lr-REACHABLE", "blockers": blockers,
                "reason": ("shortening the higher-savings blocker's range so "
                           "it no longer covers this value frees "
                           f"{want}; byte-verify")}
    # freed but not taken: outscored?  compare want's score to the winner's.
    winner = pk.get(ti)
    want_s = crm10a_v2(rows[ti], enc) or 0
    win_s = crm10a_v2(rows[ti], REG_ENC.get(winner, 0)) or 0 if winner else 0
    if winner and win_s > want_s:
        # COMPOSE with the credit actuator: model killing the winner's
        # CountRegMoves credit (the de-CSE/de-name edit at its crediting
        # ins) ON TOP of the freed baseline, and re-replay.  If `want`
        # then seats, the composite is VERIFIED and both halves are named.
        cred = credit_flip(ctx, rows[ti], want, winner, g2)
        base = {"blockers": blockers, "winner": winner,
                "want_score": want_s, "win_score": win_s,
                "credit": cred}
        if cred.get("seats"):
            return {"verdict": "composite-REACHABLE", **base,
                    "reason": (f"VERIFIED composite: shorten the blocker "
                               f"(frees {want}) AND kill {winner}'s credit "
                               f"at {cred['ins']} (de-CSE/de-name) -> seats "
                               f"{want}.  Byte-verify both halves.")}
        return {"verdict": "lr+credit", **base,
                "reason": (f"freeing {want} (shorten the blocker) is NOT "
                           f"enough -- {winner} still outscores {want} "
                           f"{win_s} vs {want_s}; killing {winner}'s credit "
                           f"alone does not seat it either (deeper residue)")}
    return {"verdict": "lr-INERT", "blockers": blockers,
            "reason": (f"freeing {want} does not seat it here (another "
                       f"holder remains, or a list-order tie) -- picks "
                       f"{winner}")}


def credit_flip(ctx: dict, row: dict, want: str, winner: str,
                base_graph=None) -> dict:
    """Credit (de-CSE / de-name) ACTUATOR.

    A `[score]`-decided seat holds because the winner earns a CountRegMoves
    credit at a NAMED instruction (a MOV/2-op where the value coalesces).
    The source lever is de-CSE / de-name at that ins (break the coalesce so
    the credit vanishes).  This models each such credit removal (perturb the
    winner's cand_scores by the credit weight) -- optionally ON TOP of a
    live-range counterfactual graph (`base_graph`, e.g. `want` already
    freed) -- and replays the certified pick cascade.

    Returns ``seats`` (True if `want` seats after the kill) with the named
    ``ins`` / ``credit`` so the source construct can be located.  Composes
    with live_range_flip to VERIFY a shorten-blocker + kill-credit composite
    (build_city_item nt[60]->ECX: free ECX + kill EBX's +4 at 6c190ef8).
    """
    from c2.regalloc.replay import build_graph, replay_order
    rows = [a for a in ctx.get("alloc") or [] if a.get("reg_name") in REG_ENC]
    tname = row.get("name")
    ti = next((i for i, a in enumerate(rows) if a.get("name") == tname), None)
    if ti is None:
        return {"seats": False, "reason": "no-row"}
    ex = explain_row(row)
    credits = (ex or {}).get("credits", {}).get(winner, []) if ex else []
    if not credits:
        return {"seats": False, "reason": f"no named {winner} credit"}
    graph = base_graph if base_graph is not None else build_graph(rows)
    total = sum(c.get("credit", 0) for c in credits)
    rows2 = list(rows)
    a2 = dict(rows2[ti])
    for key in ("cand_scores", "commit_cand_scores"):
        cs = a2.get(key)
        if cs:
            a2[key] = [dict(e) for e in cs]
            for e in a2[key]:
                if e["cand"] == winner:
                    e["saves"] = max(e["saves"] - total, 0)
    rows2[ti] = a2
    pk = {e["idx"]: e["pick"]
          for e in replay_order(rows2, list(range(len(rows2))), graph)}
    ins0 = credits[0].get("ins")
    return {"seats": pk.get(ti) == want, "ins": ins0, "credit": total,
            "n_credit_ins": len(credits), "pick": pk.get(ti)}


def flip_analysis(row: dict, want: str, ivx: Optional[dict] = None) -> dict:
    """Name the minimal input change that seats this conflict in `want`.
    Verdict classes: already / masked / vetoed / outscored / tie-order /
    not-a-candidate.

    Pass `ivx` (build_iv_index) to attribute a `masked` verdict to the
    value occupying the wanted register (pinned vs shortenable)."""
    ex = explain_row(row)
    if ex is None:
        return {"verdict": "no-presentation"}
    if ex["actual"] == want:
        return {"verdict": "already", "explain": ex}
    enc = REG_ENC.get(want)
    out: dict = {"explain": ex, "want": want}
    if want not in (ex["cands"] or []):
        out["verdict"] = "not-a-candidate"
        out["note"] = ("the wanted register is not in the reg tree's "
                       "candidate list -- type-class/width lever, not a "
                       "seat lever (check Rule 151 first)")
        return out
    if want in ex["vetoes"]:
        out["verdict"] = "vetoed"
        out["note"] = "TooGreedy vetoed the wanted register (savings lever)"
        return out
    if ex["mask"] is not None and enc is not None and (enc & ex["mask"]):
        out["verdict"] = "masked"
        out["contributors"] = mask_contributors(row, want)
        occ = mask_occupants(row, want, ivx) if ivx else []
        out["occupants"] = occ
        real = [o for o in occ if not o["pinned"]]
        if real and real[0]["tie"]:
            # equal-rank competitor => the ConfBefore create-order tie MIGHT
            # be the lever.  Don't guess -- run the birth-order actuator
            # (full pick-cascade replay over every tie-group position) and
            # report the VERIFIED verdict.
            bo = birth_order_flip(ivx, row, want)
            out["birth_order"] = bo
            top = real[0]
            who = (f"local `{top['var']}`" if top.get("var")
                   else f"temp {top['value']}")
            if bo.get("verdict") == "reorder-REACHABLE":
                se = bo.get("side_effects") or []
                out["note"] = (
                    f"{want} is an equal-rank tie with {who}; birth-order "
                    f"actuator: REACHABLE via {bo['via']} "
                    f"({len(se)} side-seat(s) -- each must match PS).  "
                    f"Realize by LAST-USE motion (Rule 115/28a): make this "
                    f"value's final read later so it is created last.")
            elif bo.get("verdict") == "reorder-INERT":
                b = bo.get("blocker")
                bwho = ((f"local `{b['var']}`" if b.get("var")
                         else f"temp {b['value']}") + f" (sav={b['savings']})"
                        if b else "a higher-savings neighbour")
                # reorder can't win -> the blocker is a higher-savings
                # baseline interference.  Chain the live-range actuator to
                # check whether shortening it actually seats `want`, or a
                # residual credit lever remains (composite).
                lr = live_range_flip(ivx, row, want)
                out["live_range"] = lr
                v = lr.get("verdict")
                head = (f"{want} is an equal-rank tie with {who}, but "
                        f"birth-order is INERT ({bwho} holds {want} at "
                        f"baseline).")
                if v == "composite-REACHABLE":
                    cr = lr.get("credit") or {}
                    out["note"] = (
                        f"{head}  VERIFIED COMPOSITE lever: (1) shorten "
                        f"{bwho}'s range so it stops covering this value "
                        f"(frees {want}), AND (2) kill {lr['winner']}'s "
                        f"CountRegMoves credit at ins {cr.get('ins')} "
                        f"(de-CSE/de-name the coalesced copy).  Both -> "
                        f"seats {want}; byte-verify each half.")
                elif v == "lr+credit":
                    out["note"] = (
                        f"{head}  Live-range actuator: shortening {bwho} "
                        f"frees {want} but it is still OUTSCORED by "
                        f"{lr['winner']} ({lr['win_score']} vs "
                        f"{lr['want_score']}), and killing that credit alone "
                        f"does not seat it -- deeper residue.")
                elif v == "lr-REACHABLE":
                    out["note"] = (
                        f"{head}  Live-range actuator: shortening {bwho}'s "
                        f"range SEATS {want} (byte-verify).")
                else:
                    out["note"] = (
                        f"{head}  Live-range actuator: "
                        f"{lr.get('reason', 'shorten the blocker')}.")
            else:
                out["note"] = (
                    f"{want} is an equal-rank tie with {who}; birth-order "
                    f"actuator inconclusive ({bo.get('verdict')}).")
        elif real:
            # the blocker is an ordinary overlapping conflict (higher-savings
            # = allocated first).  Named locals are Rule 115 / live-range
            # levers -- shorten the blocker's range so it stops covering this
            # value, or reorder so this value allocates first.
            top = real[0]
            who = (f"local `{top['var']}`" if top.get("var")
                   else f"temp {top['value']}")
            out["blocker"] = top
            if top["blocks_first"]:
                # blocker outranks by savings -> this value can NEVER be
                # allocated first (SortConflicts is savings-desc).  Run the
                # live-range actuator to check whether shortening the
                # blocker actually frees+seats `want`, or whether a residual
                # credit/list-order lever remains (composite).
                lr = live_range_flip(ivx, row, want) if ivx else {}
                out["live_range"] = lr
                v = lr.get("verdict")
                if v == "lr-REACHABLE":
                    out["note"] = (
                        f"{want} held by {who} (sav={top['savings']}, "
                        f"allocated first).  Live-range actuator: shortening "
                        f"{who}'s range so it no longer covers this value "
                        f"SEATS {want} (byte-verify).")
                elif v == "composite-REACHABLE":
                    cr = lr.get("credit") or {}
                    out["note"] = (
                        f"{want} held by {who} (sav={top['savings']}).  "
                        f"VERIFIED COMPOSITE lever: (1) shorten {who}'s range "
                        f"(frees {want}) AND (2) kill {lr['winner']}'s credit "
                        f"at ins {cr.get('ins')} (de-CSE/de-name).  Both -> "
                        f"seats {want}; byte-verify each half.")
                elif v == "lr+credit":
                    out["note"] = (
                        f"{want} held by {who} (sav={top['savings']}).  "
                        f"Live-range actuator: shortening {who} frees {want} "
                        f"but {lr['winner']} still outscores it "
                        f"({lr['win_score']} vs {lr['want_score']}) and the "
                        f"credit kill alone does not seat it -- deeper residue.")
                else:
                    out["note"] = (
                        f"{want} held by {who} (sav={top['savings']} > "
                        f"sav={ex.get('savings', 0)}, allocated first).  "
                        f"Live-range actuator: {lr.get('reason', 'shorten the blocker')}.")
            else:
                out["note"] = (
                    f"{want} is held by {who} (sav={top['savings']}, EQUAL "
                    f"rank), whose range overlaps this value.  LEVER: the "
                    f"ConfBefore tie -- reorder so this value is created first "
                    f"(Rule 115/28a), or shorten {who}'s range.")
        elif occ:
            out["note"] = (
                f"{want} is held in EXACTLY {want} by a FIXED placement "
                f"(ABI call-arg / hard-reg pin, no overlapping conflict) -- "
                f"no reorder frees it; the lever is the pin's materialization, "
                f"usually sub-source.")
        else:
            out["note"] = ("the wanted register is interference-masked; each "
                           "contributor row is a live-range lever (shrink the "
                           "value holding it / move the crossing).  "
                           "[pass routine ctx for occupant attribution]")
        return out
    sv = {e["cand"]: e["saves"] for e in ex["scores"]}
    if want in sv and sv[want] < max(sv.values()):
        winner = ex["pick"]
        out["verdict"] = "outscored"
        out["winner"] = winner
        out["winner_credits"] = ex["credits"].get(winner, [])
        out["note"] = ("the winner's CountRegMoves credits are named per "
                       "instruction -- each is a de-CSE / de-name / "
                       "reorder lever (kill the credit, the tie re-deals)")
        return out
    out["verdict"] = "tie-order"
    out["note"] = ("equal scores: decided by GivenRegisters-subset then "
                   "candidate list order -- the Rule 115/28a order-lever "
                   "class; check the Byte-seat CASE verdict before "
                   "grinding (CASE D is provably inert)")
    return out
