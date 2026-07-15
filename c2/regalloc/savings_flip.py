"""Grounded savings-edit flip search -- the P1 model's actuator.

For a wanted seat flip (``VAR=REG``, typically a seat_recon PS swap),
enumerate SOURCE-GROUNDED savings edits and replay their full
consequence chain:

    candidate edit (delete THIS ref / add a re-read in THIS block)
      -> new savings            (c2.regalloc.savings, certified P1)
      -> new ConfBefore order   (sort.sort_conflicts, certified)
      -> full pick cascade      (replay.replay_order: masks evolve with
                                 the order, scores recorded/crm10a_v2)
      -> verdict: target seat flipped?  side-effect picks?

This closes the gap the 2026-07 sessions kept hitting on the
seat-dominant parked set (place_sprite, build_city_item, ...): the
Cascade could SAY "lower sav(side) to <= 6 or raise sav(t.25c0) to
>= 8" but nothing enumerated which real refs/blocks realize the delta,
and nothing checked the FULL side-effect cascade of each choice.
``edit_sim.diagnose_savings_edit`` (rank/pair check on hand-postulated
unit deltas) is subsumed for this use case.

Honest limits (flagged per candidate, not hidden):

* TooGreedy verdicts for newly unmasked candidates come from the P2
  port (toogreedy.RoutineTG, certified 122,106/122,108) with
  identity-vintage live/zap inputs -- exact for the dominant
  order-invariant veto inputs (gen chains, index structure),
  approximate where a reorder moves liveness (P5 closes that).
* Deletion candidates assume the ref's removal does not change OTHER
  conflicts' savings (true for a pure re-read fold; false if the edit
  also removes a rival's ref -- byte-compile remains the oracle).
* Round-0 only; multi-round routines replay later rounds in identity
  order (flagged).
"""
from __future__ import annotations

from typing import Optional

from c2.regalloc.replay import (REG_ENC, build_graph, replay_order,
                                replay_rows)
from c2.regalloc.sort import sort_conflicts
from c2.regalloc import savings as sv


def _row_order_for(rows: list[dict], presort: list[dict],
                   perturbed_sav: dict[str, int],
                   transpose: Optional[tuple] = None) -> Optional[list[int]]:
    """Row-index order implied by re-sorting the round-0 presort with
    perturbed savings.

    Rows whose conf node is NOT in the presort snapshot (mid-round
    births on free-list-reused ptrs, later-round presentations) keep
    their IDENTITY-RELATIVE position: each is anchored just after the
    nearest earlier MAPPED row in commit order -- the real allocator
    interleaves them by creation, and identity locality is the best
    order-preserving approximation without modeling ReduceSplit."""
    pre0 = [e for e in presort if e.get("round", 0) == 0]
    if not pre0:
        return None
    if transpose is not None:
        i, j = transpose
        if not (0 <= i < len(pre0) and 0 <= j < len(pre0)):
            return None
        pre0 = list(pre0)
        pre0[i], pre0[j] = pre0[j], pre0[i]
    sim = sort_conflicts(
        [{**e, "savings": perturbed_sav.get(e["node"], e["savings"])}
         for e in pre0])
    rank = {e["node"]: i for i, e in enumerate(sim)}
    # first commit-order occurrence of each node claims the presort slot
    key: dict[int, float] = {}
    claimed: set = set()
    for i, r in enumerate(rows):
        node = r["conf"]
        if (r.get("round", 0) == 0 and node in rank
                and node not in claimed):
            key[i] = float(rank[node])
            claimed.add(node)
    # anchor unmapped rows after their nearest earlier mapped row
    last = -1.0
    eps = 1.0 / (len(rows) + 1)
    bump = 0
    for i in range(len(rows)):
        if i in key:
            last = key[i]
            bump = 0
        else:
            bump += 1
            key[i] = last + eps * bump
    return sorted(range(len(rows)), key=lambda i: key[i])


def _match_row(rows: list[dict], query: str) -> Optional[int]:
    q = query[2:] if query.startswith("t.") else query
    for i, r in enumerate(rows):
        nm = str(r.get("name") or "")
        if r.get("var") == query or nm == query or (
                len(q) >= 3 and nm.endswith(q.lower())):
            return i
    return None


def flip_search(rt: dict, target: str, want: str,
                max_candidates: int = 400, depth: int = 1,
                max_pairs: int = 20000) -> dict:
    """Enumerate grounded savings edits over every round-0 conflict;
    replay each through the full sort+pick cascade; return the ranked
    flips.  ``depth=2`` composes PAIRS of single edits (different
    conflicts), movers-first: singles whose replay moved ANY pick are
    paired before inert ones, capped at ``max_pairs`` replays -- the
    callee-save seat class (a value lands EBP only when six seats are
    taken/masked) is typically multi-edit."""
    want = want.upper()
    rows = replay_rows(rt.get("alloc") or [])
    if not rows:
        return {"error": "no replayable rows"}
    ti = _match_row(rows, target)
    if ti is None:
        return {"error": f"target {target!r} not in replayable rows"}
    graph = build_graph(rows)
    from c2.regalloc.toogreedy import RoutineTG
    tg = RoutineTG(rt)
    snap = sv.snap_index(rt)
    amap = sv.alias_map(rt) if snap else {}
    dmap = sv._depth_map(rt)
    presort = rt.get("presort") or []

    # identity replay (sanity + side-effect baseline)
    ident = replay_order(rows, list(range(len(rows))), graph, tg=tg)
    ident_picks = {e["idx"]: e["pick"] for e in ident}
    base_ok = ident_picks.get(ti) == rows[ti].get("reg_name")

    # ---- candidate edits, grounded in the ref ledger ----------------
    cands = []
    for ri, row in enumerate(rows):
        if row.get("round", 0) != 0 or snap is None:
            continue
        led = sv.ref_ledger(rt, row, snap, amap)
        blocks = sv.calc_blocks(row, snap, amap)
        sav0 = row["savings"]
        label = row.get("var") or row["name"]
        if led:
            saves = [e for e in led if e["side"] == "save"]
            for e in saves:
                cands.append({
                    "row": ri, "conf": row["conf"], "label": label,
                    "kind": f"DELETE {e['kind']} ref",
                    "detail": (f"ins {e['ins']} blk {e['blk']} "
                               f"(d{e['depth']}, -{e['weighted']})"),
                    "sav": max(sav0 - e["weighted"], 0)})
            # multi-ref deletions on the SAME conflict (subset sums up
            # to 3 refs): a 'needs a SAVINGS change' gap often exceeds
            # any single ref's weight (check_goods sx: -279 = three
            # depth-2 uses).  The replay only sees the resulting sav,
            # so dedupe by sum; the witness names one realizing set.
            import itertools as _it
            seen_sums = {e["weighted"] for e in saves}
            for k in (2, 3):
                if len(saves) < k:
                    break
                for combo in _it.combinations(range(len(saves)), k):
                    w = sum(saves[i]["weighted"] for i in combo)
                    if w in seen_sums:
                        continue
                    seen_sums.add(w)
                    ws = "+".join(str(saves[i]["weighted"])
                                  for i in combo)
                    ins_l = ",".join(str(saves[i]["ins"])
                                     for i in combo)
                    cands.append({
                        "row": ri, "conf": row["conf"], "label": label,
                        "kind": f"DELETE {k} refs",
                        "detail": f"ins {ins_l} (-{ws})",
                        "sav": max(sav0 - w, 0)})
        if blocks:
            seen_blk = set()
            for blk, _s, _c in blocks:
                if blk in seen_blk:
                    continue
                seen_blk.add(blk)
                d = dmap.get(blk, 0)
                w = sv.LOOP_W[d]
                cands.append({
                    "row": ri, "conf": row["conf"], "label": label,
                    "kind": "ADD re-read",
                    "detail": f"blk {blk} (d{d}, +{w})",
                    "sav": sav0 + w})
    # de-dup identical (conf, sav) outcomes -- the replay only sees the
    # savings value, so equal outcomes share a verdict; keep the first
    # detail of each and note the multiplicity.
    uniq: dict[tuple, dict] = {}
    for c in cands:
        k = (c["conf"], c["sav"])
        if k in uniq:
            uniq[k]["alt"] = uniq[k].get("alt", 0) + 1
        else:
            uniq[k] = c
    cands = list(uniq.values())[:max_candidates]

    # ---- third family: CREDIT KILLS (the `outscored` seat class) ----
    # A [score]-decided seat holds because CountRegMoves credits a
    # specific instruction (cq ground truth).  A de-CSE / de-name /
    # reorder edit at that ins deletes the credit; the replay side is a
    # cand_scores perturbation on that row (score - credit).  Kept as a
    # separate candidate list: they do not change savings/sort order,
    # so alone they only re-deal THAT row's pick -- their power is in
    # depth-2 compositions with savings edits.
    def _row_credits(row):
        out, last = {}, {}
        for e in row.get("crm_events") or []:
            d = e["total"] - last.get(e["cand"], 0)
            last[e["cand"]] = e["total"]
            if d:
                out.setdefault(e["cand"], []).append(
                    {"ins": e["ins"], "credit": d})
        return out

    score_cands = []
    for ri, row in enumerate(rows):
        if row.get("round", 0) != 0:
            continue
        for cand, evs in _row_credits(row).items():
            for e in evs:
                score_cands.append({
                    "row": ri, "conf": row["conf"],
                    "label": row.get("var") or row["name"],
                    "kind": "KILL credit",
                    "detail": (f"{cand} credit {e['credit']} at ins "
                               f"{e['ins']} (de-CSE/de-name/reorder)"),
                    "score_edit": (ri, cand, -e["credit"])})

    # ---- fourth family: PRESORT TRANSPOSITIONS (tie-order / H2) ------
    # An equal-savings tie re-deals on conflict-CREATION order (the
    # unstable ShellSort); the source lever is LAST-USE motion (the
    # value that should sort first must be created last = have the
    # earlier last use).  Model: transpose the target's presort entry
    # with each equal-savings peer.  Realization is the H2 lever, NOT a
    # decl swap (decl order rarely moves creation order).
    order_cands = []
    pre0 = [e for e in presort if e.get("round", 0) == 0]
    tgt_node = rows[ti]["conf"]
    tgt_pi = next((k for k, e in enumerate(pre0)
                   if e["node"] == tgt_node), None)
    if tgt_pi is not None:
        tsav = pre0[tgt_pi]["savings"]
        for k, e in enumerate(pre0):
            if k != tgt_pi and e["savings"] == tsav:
                order_cands.append({
                    "row": ti, "conf": tgt_node,
                    "label": rows[ti].get("var") or rows[ti]["name"],
                    "kind": "REORDER tie (H2 last-use motion)",
                    "detail": (f"transpose presort #{tgt_pi}<->#{k} "
                               f"(peer {e['node']}, sav {tsav}) -- move "
                               f"the winner's final read EARLIER (it is "
                               f"then created last and sorts first)"),
                    "transpose": (tgt_pi, k)})

    # ---- replay ------------------------------------------------------
    hits, checked = [], 0
    movers = []          # single edits that moved at least one pick

    def _apply_score_edits(edits: list):
        """rows copy with each edit's cand_scores perturbation.  graph/
        withregs are untouched, so the identity graph stays valid."""
        se = [c["score_edit"] for c in edits if c.get("score_edit")]
        if not se:
            return rows
        rows2 = list(rows)
        for ri, cand, delta in se:
            a = dict(rows2[ri])
            for key in ("cand_scores", "commit_cand_scores"):
                cs = a.get(key)
                if cs:
                    a[key] = [dict(e) for e in cs]
                    for e in a[key]:
                        if e["cand"] == cand:
                            e["saves"] = max(e["saves"] + delta, 0)
            rows2[ri] = a
        return rows2

    def _try(edits: list, perturbed: dict) -> Optional[bool]:
        """Replay one perturbation; record a hit; return whether ANY
        pick moved (the movers signal).  None = unmappable order."""
        nonlocal checked
        tr = next((c["transpose"] for c in edits
                   if c.get("transpose")), None)
        order = _row_order_for(rows, presort, perturbed, transpose=tr)
        if order is None:
            return None
        checked += 1
        res = replay_order(_apply_score_edits(edits), order, graph, tg=tg)
        picks = {e["idx"]: e["pick"] for e in res}
        moved = any(p != ident_picks.get(i) for i, p in picks.items())
        if picks.get(ti) != want:
            return moved
        conf_flags = {e["idx"]: e.get("confident", True) for e in res}
        side = [{"row": i,
                 "label": rows[i].get("var") or rows[i]["name"],
                 "from": ident_picks.get(i), "to": p}
                for i, p in picks.items()
                if i != ti and p != ident_picks.get(i)]
        base = dict(edits[0])
        if len(edits) > 1:
            base["kind"] = " + ".join(e["kind"] for e in edits)
            base["detail"] = " | ".join(
                f"{e['label']}: {e['detail']}" for e in edits)
            base["sav"] = "/".join(str(e.get("sav", "-")) for e in edits)
        hits.append({**base, "edits": len(edits), "side_effects": side,
                     "confident": conf_flags.get(ti, True)
                     and all(conf_flags.get(s["row"], True)
                             for s in side)})
        return moved

    def _perturb(edits: list) -> dict:
        return {c["conf"]: c["sav"] for c in edits if "sav" in c}

    for c in cands:
        if c["sav"] == rows[c["row"]]["savings"]:
            continue
        moved = _try([c], _perturb([c]))
        if moved:
            movers.append(c)
    for c in score_cands:
        moved = _try([c], {})
        if moved:
            movers.append(c)
    for c in order_cands:
        moved = _try([c], {})
        if moved:
            movers.append(c)

    if depth >= 2 and not hits:
        # movers-first pairing across BOTH families; inert x inert
        # savings pairs cannot flip anything (each half leaves every
        # pick identical and the perturbations are independent unless
        # the PAIR reorders a 3-way tie -- rare enough to accept).
        all_cands = cands + score_cands + order_cands
        pool = movers if movers else all_cands
        pairs = 0
        for c1 in pool:
            for c2 in all_cands:
                if c1["conf"] == c2["conf"] and \
                        c1.get("score_edit") == c2.get("score_edit"):
                    continue
                if pairs >= max_pairs:
                    break
                pairs += 1
                _try([c1, c2], _perturb([c1, c2]))
            if pairs >= max_pairs or hits:
                break

    hits.sort(key=lambda h: (h.get("edits", 1),
                             len(h["side_effects"]), not h["confident"]))
    return {"target": target, "want": want, "row": ti,
            "identity_ok": base_ok, "candidates": len(cands),
            "replayed": checked, "movers": len(movers), "hits": hits}
