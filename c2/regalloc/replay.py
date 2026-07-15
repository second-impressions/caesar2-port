"""Offline replay of wcc386 10.0a's register allocator from trace records.

CORPUS-CERTIFIED 2026-06-12 over the full build trace:

* ``replay_sort`` -- SortConflicts = the byte-exact ShellSort port
  (c2.regalloc.sort) applied PER RETRY ROUND: **1,228/1,228 routines
  exact**.  The trace's presort (sl) / postsort (sa) streams concatenate
  RegAlloc retry rounds; a node reappearing (same conflict re-presented,
  possibly with recomputed savings) marks a round boundary.
* ``select_register`` -- the GiveBestReg selection rule: **19,116/19,116
  allocations exact** with recorded inputs.  The rule:
      1. argmax CountRegMoves over the surviving candidate list
         (cand_scores order = the bt tree->regs candidate order);
      2. tie -> the FIRST tied candidate that is a hardware subset of
         GivenRegisters at pick time (given_before);
      3. else the first tied candidate (list order).
  NOTE: GivenRegisters DOES participate in the tie-break -- ignoring it
  breaks 7,233 of the 19,116 picks.

What this enables WITHOUT container compiles: re-sorting a tie group
under a hypothesized birth-order change (the Rule 28a/115 lever space)
and replaying the selection cascade to see whether PS's seats fall out.
Scores and masks are RECOMPUTABLE from inputs since 2026-07-11
(crm10a_v2 100%, neighbours.with_regs 100%, liveness.py 100%): the
full chain is forward-calculated per commit-window snapshot
(c2.regalloc.seatchain, identity 6,243/6,243).  Cross-commit feedback
(earlier picks seeding later credits/masks) is visible in the inputs;
a what-if that flips an EARLY seat invalidates later rows' snapshots.
"""
from __future__ import annotations

from typing import Iterable, Optional

from c2.regalloc.sort import conf_before, shell_sort

# Full-size + 16/8-bit hw_reg_set encodings (inverse of trace.REG_NAME --
# byte/word conflicts allocate too and their commits update GivenRegisters
# and every later mask; excluding them was an 8% identity-replay leak).
REG_ENC = {
    "EAX": 0x1000003, "EBX": 0x200000c, "ECX": 0x4000030, "EDX": 0x80000c0,
    "ESI": 0x10000100, "EDI": 0x20000200, "EBP": 0x400, "ESP": 0x800,
    "AX": 0x3, "BX": 0xc, "CX": 0x30, "DX": 0xc0, "SI": 0x100, "DI": 0x200,
    "AL": 0x2, "AH": 0x1, "BH": 0x4, "BL": 0x8, "CH": 0x10, "CL": 0x20,
    "DH": 0x40, "DL": 0x80,
}


def split_rounds(seq: Iterable[dict], key=lambda x: x["node"]) -> list[list[dict]]:
    """Split a concatenated sl/sa stream into RegAlloc retry rounds.
    A reappearing node ptr starts a new round (conflicts are re-presented
    with recomputed savings on ON_HOLD retries)."""
    out: list[list[dict]] = [[]]
    seen: set = set()
    for x in seq:
        k = key(x)
        if k in seen:
            out.append([])
            seen = set()
        seen.add(k)
        out[-1].append(x)
    return out


def replay_sort(presort: list[dict]) -> list[dict]:
    """SortConflicts over the (single-round) ConfList snapshot: returns the
    allocation queue order.  presort entries: {node, savings}."""
    arr = [dict(x) for x in presort]
    shell_sort(arr, lambda a, b: conf_before(a["savings"], b["savings"]))
    return arr


def replay_sort_rounds(presort: list[dict]) -> list[dict]:
    """Round-aware sort replay over the full sl stream."""
    out: list[dict] = []
    for rnd in split_rounds(presort):
        out.extend(replay_sort(rnd))
    return out


def select_register(cand_scores: list[dict],
                    given_before: Optional[int]) -> Optional[str]:
    """The corpus-certified GiveBestReg selection rule (see module doc).
    cand_scores: [{cand, saves}] in the bt candidate order."""
    if not cand_scores:
        return None
    sv = {e["cand"]: e["saves"] for e in cand_scores}
    cands = [e["cand"] for e in cand_scores]
    best = max(sv.values())
    ties = [c for c in cands if sv[c] == best]
    if len(ties) > 1 and isinstance(given_before, int):
        for c in ties:
            e = REG_ENC.get(c)
            if e is not None and (e & given_before) == e:
                return c
    return ties[0]


def validate_routine(routine: dict) -> dict:
    """Replay both halves for one routine vs ground truth.  Returns
    {sort_ok, sort_rounds, picks_total, picks_ok, pick_misses}."""
    res = {"sort_ok": None, "sort_rounds": 0,
           "picks_total": 0, "picks_ok": 0, "pick_misses": []}
    pres = routine.get("presort") or []
    sa = routine.get("postsort") or []
    if pres and sa:
        pred = [x["node"] for x in replay_sort_rounds(pres)]
        want = [x["node"] for x in sa]
        res["sort_ok"] = pred == want
        res["sort_rounds"] = len(split_rounds(pres))
    for a in routine.get("alloc") or []:
        pick = a.get("reg_name")
        scores = a.get("cand_scores") or []
        if not pick or pick not in REG_ENC or not scores:
            continue
        if pick not in {e["cand"] for e in scores}:
            continue
        res["picks_total"] += 1
        pred = select_register(scores, a.get("given_before"))
        if pred == pick:
            res["picks_ok"] += 1
        else:
            res["pick_misses"].append(
                {"var": a.get("var") or a.get("name"), "pred": pred,
                 "actual": pick, "savings": a.get("savings")})
    return res


# --------------------------------------------------------------------------
# Conflict graph + full pick-cascade replay (trace image >= 2026-06-12: the
# wr record's trailing with.out/within + full own-id fields).
#
# Graph semantics (grounded in 10.0a NeighboursUse@0x580c0): an EARLIER-
# committed conflict's with.out_of_block contains the id bits of every
# LATER, still-unallocated conflict it live-overlaps (allocated neighbors
# leave the live bitsets when FixInstructions rewrites them to N_REGISTER,
# so the edge must be read from the earlier node's snapshot).  The
# within_block channel uses a per-block 32-bit pool and is NOT comparable
# across blocks; we use the out channel only.  Corpus census 2026-06-12:
# 10,557 out-edges, 94.5% put the earlier pick into the later mask; the
# exceptions are MOV-coalesce pairs (no_conflict masking -- structural,
# order-independent) and are LEARNED from the identity run per pair.
# --------------------------------------------------------------------------

OP_MOV = 0x26
# hw_reg_set encoding -> register width (for the 0x3dfdb size-class flag).
REG_WIDTH = {enc: (4 if n in ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI",
                              "EBP", "ESP") else
                   2 if n in ("AX", "BX", "CX", "DX", "SI", "DI") else 1)
             for n, enc in {
                 "EAX": 0x1000003, "EBX": 0x200000c, "ECX": 0x4000030,
                 "EDX": 0x80000c0, "ESI": 0x10000100, "EDI": 0x20000200,
                 "EBP": 0x400, "ESP": 0x800, "AX": 0x3, "BX": 0xc,
                 "CX": 0x30, "DX": 0xc0, "SI": 0x100, "DI": 0x200,
                 "AL": 0x2, "AH": 0x1, "BH": 0x4, "BL": 0x8, "CH": 0x10,
                 "CL": 0x20, "DH": 0x40, "DL": 0x80}.items()}
# 10.0a CountRegMoves@0x57728 half-credit op1 extension list (the op0/result
# channel applies to ANY 2-address op).  Credits: MOV=4, half=2 (dword).
CRM_COMM = {0x1, 0x2, 0x5, 0x9, 0xa, 0xb}


def crm10a_v2(row: dict, enc: int) -> Optional[int]:
    """Recompute CountRegMoves from the row's OWN gi walk + the ce/cq
    ground truth fields (trace image >= 2026-07-10b, cache v45).  Full
    port of CountRegMoves@0x57728:

    * VALUE SET = {tree->temp, tree->alt} (``crm_tree`` -- the alias ring;
      the v1 model only matched the conflict's own name).
    * credits = tree->size (full, MOV) / size>>1 (half, non-MOV) -- v1
      hardcoded 4/2.
    * walk = ``own_walk`` (per-presentation gi burst, REAL block hops).
    * MOV extension rule @0x57884: a MOV result that is an N_REGISTER
      whose hw_reg_set INTERSECTS the candidate earns half credit even
      when neither side is in the value set.
    * 0x57670 predicate path (v45 meta fields): when the reg-name
      equality fails, a MOV partner that is an N_TEMP with temp_flags&8
      still earns FULL credit, gated by the 0x3dfdb flag (`candidate is
      a member of the temp's size-class register list` -- modeled as a
      width match, exact for the 1/2/4-byte classes).

    Returns None when the row lacks the v45 substrate.
    """
    tree = row.get("crm_tree")
    walk = row.get("own_walk")
    if not tree or not walk:
        return None
    V = {int(tree["temp"], 16), int(tree["alt"], 16)} - {0}
    full = tree["size"] or 4
    half = full >> 1
    flag = REG_WIDTH.get(enc, 4) == min(full, 4)   # 0x3dfdb size-class flag

    def _pred(meta: Optional[int]) -> bool:        # 0x57670
        return bool(flag and meta is not None
                    and (meta & 0xFF) == 2 and (meta >> 8) & 8)

    cnt = 0
    for ins in walk:
        op, res, rr = ins["opcode"], ins["result"], ins["result_reg"]
        o0, o0r = ins["op0"], ins["op0_reg"]
        o1, o1r = ins["op1"], ins["op1_reg"]
        if op == 0x4B:
            continue                      # block sentinel row
        if op == OP_MOV:
            if o0 in V and (rr == enc or _pred(ins.get("res_meta"))):
                cnt += full
            elif res in V and (o0r == enc or _pred(ins.get("op0_meta"))):
                cnt += full
            elif rr and (rr & enc):       # 0x57884 N_REGISTER overlap
                cnt += half
        else:
            # Faithful port of the non-MOV branch (0x577b5..0x57832):
            # ebx=op0 participates for EVERY op (the 0x576fc comm table
            # only gates op1 LOADING), and the {temp, alt} comparisons are
            # RAW POINTER equality INCLUDING NULL==NULL -- with alt==0, an
            # un-loaded op1 (0) "equals" alt, so ANY non-MOV whose result
            # is the candidate's register name earns half credit; likewise
            # a result-less op (res==0) "equals" alt on the other side.
            temp = int(tree["temp"], 16)
            alt = int(tree["alt"], 16)
            b = o0
            d = o1 if op in CRM_COMM else 0
            if rr == enc:                     # result == AllocRegName(cand)
                if b == temp or b == alt or d == temp or d == alt:
                    cnt += half
            elif res == temp or res == alt:
                if (b and o0r == enc) or (d and o1r == enc):
                    cnt += half
    return cnt


def crm_selfcheck(row: dict) -> bool:
    """True when the offline model reproduces every recorded candidate
    score for this row (crm10a_v2, CERTIFIED 32,192/32,192 = 100.000%).
    None-substrate rows (should not exist on current traces -- image-ID
    keying auto-invalidates) fail the check loudly."""
    for e in row.get("cand_scores") or []:
        enc = REG_ENC.get(e["cand"])
        if enc is None:
            continue
        if crm10a_v2(row, enc) != e["saves"]:
            return False
    return True


def out_edge(g_early: dict, g_late: dict) -> bool:
    """Earlier-committed node's with.out vs later node's own id.out."""
    return any(a & b for a, b in zip(g_early["with_out"], g_late["id_out"]))


def replay_rows(alloc: list[dict]) -> list[dict]:
    """The replayable subset of a routine's alloc rows, in identity commit
    order.  NOTE: conflict node POINTERS are free-list-reused within a
    routine (a conf id can appear twice) -- all graph/replay APIs key by
    ROW INDEX into this list, never by conf.

    Rows prefer the per-presentation ``commit_*`` fields (trace cache
    >= v27): each row's wr/bt/gb sweep scoped to ITS OWN birth..commit
    window, instead of the legacy first-sighting-per-conf join that
    leaked stale masks into free-list re-owners (the 247-function
    identity-gate leak, closed 2026-06-13 at 1227/1227)."""
    out = []
    for a in alloc:
        if a.get("reg_name") not in REG_ENC:
            continue
        if a.get("commit_withregs") is not None or any(
                a.get("commit_" + k) is not None
                for k in ("graph", "cand_scores", "tree_cands", "tg_veto")):
            a = dict(a)
            for k in ("withregs", "graph", "cand_scores", "tree_cands",
                      "tg_veto", "ins_range"):
                v = a.get("commit_" + k)
                if v is not None:
                    a[k] = v
        if a.get("graph"):
            out.append(a)
    return out


def build_graph(rows: list[dict]) -> list[dict]:
    """From the identity run, derive per-row (indexed like `rows`): neighbor
    row-index set (undirected, via the earlier node's with.out snapshot),
    per-pair coalesce exceptions (edge present but pick NOT in mask =>
    no_conflict), and the baseline mask (recorded withregs minus earlier-
    neighbor contributions)."""
    out = []
    for i, b in enumerate(rows):
        nb, exc, contrib = set(), set(), 0
        for j, a in enumerate(rows):
            if j == i:
                continue
            ge, gl = (a, b) if j < i else (b, a)
            if not out_edge(ge["graph"], gl["graph"]):
                continue
            nb.add(j)
            if j < i:                       # a committed first in identity
                enc = REG_ENC[a["reg_name"]]
                if (enc & b["withregs"]) == enc:
                    contrib |= enc
                else:
                    exc.add(j)              # MOV-coalesce exception
        out.append({"neighbors": nb, "excepted": exc,
                    "baseline": b["withregs"] & ~contrib})
    return out


def replay_order(rows: list[dict], order: list[int],
                 graph: list[dict] | None = None,
                 tg=None) -> list[dict]:
    """Replay the full pick cascade under a hypothetical allocation ORDER
    (row indices into `rows` = replay_rows(alloc)).  Masks evolve as
    baseline | earlier-neighbor picks (coalesce-excepted pairs contribute
    nothing, both directions); GivenRegisters accumulates picks; scores are
    RECORDED where available and recomputed (crm10a_v2, certified exact)
    for newly unmasked candidates, with a confidence flag.

    ``tg`` (optional) = a ``toogreedy.RoutineTG`` context: newly
    unmasked candidates get a MODELED TooGreedy verdict (P2 port,
    certified 122,106/122,108) instead of being silently assumed
    un-vetoed; a modeled verdict keeps the row confident.  Caveat: the
    port's live/zap inputs are identity-vintage -- under a reorder they
    approximate (the P5 feedback engine is the exact fix).

    Returns [{idx, conf, var, pick, identity, confident}] in `order`."""
    if graph is None:
        graph = build_graph(rows)
    tg_committed: set = set()
    # seed GivenRegisters from the first row's recorded entry state (captures
    # rq parm-reg commits that precede the GiveBestReg stream)
    given = 0
    if order:
        gb = rows[order[0]].get("given_before")
        if isinstance(gb, int):
            given = gb
    picks: dict[int, str] = {}
    out = []
    for idx in order:
        a = rows[idx]
        g = graph[idx]
        mask = g["baseline"]
        for n in g["neighbors"]:
            if n in picks and n not in g["excepted"]:
                mask |= REG_ENC[picks[n]]
        rec_scores = {e["cand"]: e["saves"] for e in a.get("cand_scores") or []}
        veto = set(a.get("tg_veto") or [])   # TooGreedy verdicts (identity)
        tree = a.get("tree_cands") or list(rec_scores)
        cands, confident = [], True
        for cand in tree:
            enc = REG_ENC.get(cand)
            if enc is None or (enc & mask) or cand in veto:
                continue
            if cand in rec_scores:
                cands.append({"cand": cand, "saves": rec_scores[cand]})
            elif not (enc & a["withregs"]):
                # unscored AND unmasked at identity AND unvetoed: GiveBestReg
                # skipped it via the conflict's own EXCEPT set (with.regs/
                # except, no tg record) -- an order-INDEPENDENT exclusion.
                # Modeling it closed the find_enemy-class identity leak.
                continue
            else:
                # newly unmasked candidate: TooGreedy verdict from the
                # P2 port when available (identity-vintage inputs);
                # without it, assume un-vetoed and drop confidence.
                if tg is not None:
                    tv = tg.verdict(a, enc, tg_committed)
                    if tv is True:
                        continue                  # modeled veto
                    if tv is None:
                        confident = False
                else:
                    confident = False
                v = crm10a_v2(a, REG_ENC[cand])
                if v is None:
                    confident = False
                    v = 0
                cands.append({"cand": cand, "saves": v})
                if not crm_selfcheck(a):
                    confident = False
        pick = select_register(cands, given)
        # WorthProlog gate (OW regalloc.c; 10.0a wp records: cost 0 for
        # the EAX family / given-covered picks, else 2 = push+pop at the
        # -4 cost model; accept iff savings > cost).  Applied ONLY to
        # COUNTERFACTUAL picks -- identity picks carry a recorded
        # ok=True, and the replay's `given` evolution is approximate,
        # so gating them could break the certified identity gate.
        if (pick is not None and pick != a.get("reg_name")
                and pick not in ("EAX", "AX", "AL", "AH")):
            _enc = REG_ENC[pick]
            if (_enc & given) != _enc and (a.get("savings") or 0) <= 2:
                pick = None                       # not worth the prologue
        if pick is None:
            pick, confident = "MEM", False
        else:
            given |= REG_ENC[pick]
            picks[idx] = pick
            tg_committed.add(int(a["name"], 16))
            _t = a.get("crm_tree")
            if _t:
                tg_committed |= {int(_t["temp"], 16),
                                 int(_t["alt"], 16)} - {0}
        out.append({"idx": idx, "conf": a["conf"],
                    "var": a.get("var") or a.get("name"),
                    "pick": pick, "identity": a["reg_name"],
                    "confident": confident})
    return out


def inverse_search(rows: list[dict], want: dict[int, str],
                   graph: list[dict] | None = None,
                   focus: set[int] | None = None,
                   budget: int | None = None) -> tuple[list[dict], bool]:
    """Enumerate single-row moves and pair swaps of the allocation order;
    return ``(hits, exhausted)`` where hits are the orders whose full
    cascade reproduces `want` -- ONLY the row indices present in `want`
    are constrained (a PARTIAL map allows downstream re-seats; pass a
    complete map for strict matching).  Each hit carries
    ``side_effects``: [(idx, identity_reg, new_reg)] for unconstrained
    rows whose pick changed -- verify those against PS's diff rows
    before acting.

    ``focus``: only consider orders that MOVE one of these rows (the
    meaningful lever space for a target pair) -- O(n*|focus|) orders
    instead of O(n^2).  ``budget``: max replays; when exceeded the search
    stops and ``exhausted`` is False -- callers MUST then report
    INCONCLUSIVE, never UNREACHABLE (the STOP verdict requires an
    exhausted search).

    Each hit: {kind: 'move'|'swap', i, j, tie: bool} where `tie` means the
    two rows share savings (reachable by a pure birth reorder, Rule
    28a/115); tie=False means the order requires a SAVINGS change (source
    shape lever, not decl order)."""
    import itertools
    if graph is None:
        graph = build_graph(rows)
    n = len(rows)
    cands = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if focus is not None and i not in focus and j not in focus:
                continue
            o = list(range(n))
            o.insert(j, o.pop(i))
            cands.append(("move", i, j, o))
    for i, j in itertools.combinations(range(n), 2):
        if focus is not None and i not in focus and j not in focus:
            continue
        o = list(range(n))
        o[i], o[j] = o[j], o[i]
        cands.append(("swap", i, j, o))
    identity = {k: r["reg_name"] for k, r in enumerate(rows)}
    hits = []
    exhausted = True
    for k, (kind, i, j, order) in enumerate(cands):
        if budget is not None and k >= budget:
            exhausted = False
            break
        res = {x["idx"]: x["pick"] for x in replay_order(rows, order, graph)}
        if all(res.get(ix) == rg for ix, rg in want.items()):
            side = [(ix, identity[ix], res[ix]) for ix in res
                    if ix not in want and res[ix] != identity[ix]]
            hits.append({"kind": kind, "i": i, "j": j,
                         "tie": rows[i].get("savings") == rows[j].get("savings"),
                         "side_effects": side})
    return hits, exhausted


def batched_inverse_search(
    rows: list[dict], wants: list[dict[int, str]],
    graph: list[dict] | None = None,
    focus: set[int] | None = None,
) -> list[list[dict]]:
    """Batched inverse search: enumerate the move + swap order space
    ONCE and check ALL candidate `wants` against each order's full
    cascade.  Returns ``[hits_for_want_0, hits_for_want_1, ...]`` where
    each hits list has the same shape as :func:`inverse_search`'s hits
    (kind/i/j/tie/side_effects).

    Big win for the seat-residue predictor when many candidates need
    checking against the same allocation order space (e.g. per-swap
    candidate enumeration on a 120-row routine with 44 chosen=EBX
    candidates: ``inverse_search`` runs 44 \u00d7 9009 replays = ~400k, this
    runs 9009 replays once + 44 \u00d7 9009 dict checks = ~40x faster).
    """
    import itertools
    if graph is None:
        graph = build_graph(rows)
    n = len(rows)
    cands_o: list[tuple[str, int, int, list[int]]] = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            if focus is not None and i not in focus and j not in focus:
                continue
            o = list(range(n))
            o.insert(j, o.pop(i))
            cands_o.append(("move", i, j, o))
    for i, j in itertools.combinations(range(n), 2):
        if focus is not None and i not in focus and j not in focus:
            continue
        o = list(range(n))
        o[i], o[j] = o[j], o[i]
        cands_o.append(("swap", i, j, o))
    identity = {k: r["reg_name"] for k, r in enumerate(rows)}
    hits_by_want: list[list[dict]] = [[] for _ in wants]
    for kind, i, j, order in cands_o:
        res = {x["idx"]: x["pick"] for x in replay_order(rows, order, graph)}
        tie = rows[i].get("savings") == rows[j].get("savings")
        for wi, want in enumerate(wants):
            if all(res.get(ix) == rg for ix, rg in want.items()):
                side = [(ix, identity[ix], res[ix]) for ix in res
                        if ix not in want and res[ix] != identity[ix]]
                hits_by_want[wi].append({"kind": kind, "i": i, "j": j,
                                          "tie": tie,
                                          "side_effects": side})
    return hits_by_want


def whatif_swap(presort: list[dict], i: int, j: int) -> list[dict]:
    """Lever query: swap two entries' positions in the (single-round)
    ConfList snapshot -- the IL effect of a birth-order change (decl
    swap / statement reorder) on two conflicts -- and return the new
    allocation queue.  Compare against replay_sort(presort) to see which
    queue slots move; equal-savings entries between the two positions
    may cascade (the unstable ShellSort)."""
    arr = [dict(x) for x in presort]
    arr[i], arr[j] = arr[j], arr[i]
    return replay_sort(arr)
