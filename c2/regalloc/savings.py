"""Offline port of wcc386 10.0a CalcSavings -- the P1 forward model
(TODO.md prediction-stack item 2, started 2026-07-10).

Savings drive THREE allocator decisions from one number (the ConfBefore
sort order, TooGreedy, WorthProlog); until this port they were consumed
as recorded values, so any what-if that added or removed a USE needed a
compile.  This module recomputes a conflict's savings from the ``iv``
IL snapshot (trace v46 ``il_walks``) and certifies against the ``cv``
per-block ground truth and the ``al`` final value.

Certification (2026-07-10, all TUs, trace image >= 2026-07-10g):
**20,432/20,432 rows exact (100.00%), zero misses**; 2,841 rows are
substrate-gapped (see caveats) and report ``None`` rather than a
guess.

The model (OW c/regsave.c + h/savcode.h, i86regsv.c unit tables decoded
in c2.regalloc.costs; W=10 loop weight for the -4r OptSize=50 build):

    savings = clamp0( Sigma_blocks Weight(block_save, depth)
                      - Sigma_blocks Weight(block_cost, depth) )
    Weight(v, blk) = v * 10**min(depth, 5)

Per-instruction units over the conflict's ins_range (al first/last),
value set = {name} + crm_tree {temp, alt} (the DeAlias ring witness):

    operand ref            +use(1); DOUBLED when op0 of a non-condition
                           op (opcode < 0x2e) whose result is N_REGISTER
    result def             +def(1); +use(1) more when op0 is N_REGISTER
    coalesced MOV/CONVERT  +load(2) to COST instead of the def credit,
                           when result/op0 are same-location N_TEMPs

Two 10.0a refinements DISCOVERED by the certification loop (both absent
from the OW v1 reading, both corpus-validated):

  1. **STACK_PARM capture penalty**: the same-location test fires for
     the parm-capture ``MOV var <- parm_temp`` where op0 carries
     temp_flags STACK_PARM (0x20) -- the FE homes the user var at the
     incoming parm slot, so result->t.location == op0->t.location even
     though we cannot see locations.  (16 rows: clear_ferret_map x2/y1,
     control_selection what, draw_* colour, radmalloc size, ...)

  2. **N_INDEXED index refs earn index_save(2) each** (_ReplaceIdxOpnd /
     _ReplaceIdxResult) -- consumed from the iv record's idx tail
     (res/op0/op1_idx = the N_INDEXED name's +0xc index ptr) plus the
     ``xtp`` records for NON-REGISTER TAIL operands (operands[2..N-1]:
     call parms -- ``f(table[t])`` is a hidden index_save ref,
     ``f(show_map_fn)`` a hidden use_save ref; discovered as a 40-row
     +2*W(depth) miss family and the control_menus 12-vs-2 miss).
     ALIAS RINGS (STempOffset members) resolve through the nbo birth
     records' base-ptr edges (``alias_map``) -- _Equal() DeAliases
     every N_TEMP ref, so ring members are refs of the master's
     conflict.  All three substrates are 2026-07-10f/g probe
     extensions; on OLDER traces a legacy heuristic (def-only temps
     with temp_flags INDEXED get one index_save at the def) covers the
     dominant sub-case.

Caveats (rows that return None -- measured, not modeled; corpus gap
census 2026-07-10: pos-miss 2,324 / round>0 789 / unclean 517):

* first/last outside il_walks[0] (round-boundary rewrites) and round>0
  presentations: the snapshot is ONE vintage; later rounds run
  CalcSavings on FixInstructions-rewritten IL.
* Residual alias contexts the nbo base edges do not cover.
* Pre-2026-07-10f/g traces: N_INDEXED refs / alias rings gap their
  rows (no idx tail, no base edges).
* first/last outside il_walks[0] (round > 0 rewrites, snapshot gaps).
* Cross-block memory traffic costs (need_load/need_store flow sets) and
  call reload/store costs for NEEDS_MEMORY|USE_ADDRESS names: not yet
  walked (usage & 0x88 rows certify today because the recorded cv rows
  carry the same block sums; flagged for the flow-set port).
* Block DEPTH is joined from the recorded cv rows (a stable per-block
  property); the pure-forward derivation is the be-graph loop analysis
  (TODO P3 substrate).

``certify_routine`` / ``certify_tu`` are the identity gates;
``savings_for_row`` is the forward calculator.
"""
from __future__ import annotations

from typing import Optional

N_MEMORY, N_TEMP, N_REGISTER, N_INDEXED = 1, 2, 3, 4
OP_CONVERT, OP_MOV, OP_BLOCK = 0x24, 0x26, 0x4B
FIRST_CONDITION = 0x2E
TF_INDEXED, TF_STACK_PARM = 0x08, 0x20

# -4r default-OptSize(50) units (c2.regalloc.costs, trace cost/lwt
# verified): use = def = 1, load = store = 2, index_save = load.
USE = DEF = 1
LOAD = STORE = INDEX = 2
LOOP_W = [10 ** min(d, 5) for d in range(16)]


def snap_index(rt: dict, rnd: int = 0):
    """(blocks, ins-ptr -> (block-idx, ins-idx)) over il_walks[rnd].

    Since trace v50 (image 2026-07-10i) the instrumented compiler
    re-walks the IL at every RegAlloc round loop-back (rr headers), so
    a round-N presentation joins the round-N walk -- the vintage its
    CalcSavings actually consumed (closes the round>0 / pos-miss gap
    classes).  On pre-rr traces (single walk) rnd clamps to walk 0,
    reproducing the historical behavior."""
    walks = rt.get("il_walks") or []
    if not walks:
        return None
    rnd = min(max(rnd, 0), len(walks) - 1)
    blocks = walks[rnd]["blocks"]
    pos = {}
    for bi, b in enumerate(blocks):
        for ii, r in enumerate(b["ins"]):
            pos[r["ins"]] = (bi, ii)
    return blocks, pos


def _row_walk(rt: dict, row: dict) -> int:
    """The il_walks vintage this row's SAVINGS were computed against.

    Savings are computed at conflict CREATION (UpdateLive /
    AddConflictNode) and then REFRESHED by every MoreConflicts run the
    conflict survives (MoreConflicts recomputes savings for still-
    unallocated names against the CURRENT, post-rewrite IL).  RegAlloc
    only calls MoreConflicts on the AssignConflicts==1 path -- the
    edge-2 (MakeLiveInfo+AxeDeadCode) and edge-3 (LiveInfoUpdate)
    loop-backs -- NOT on the edge-1 (verdict!=1) loop-back.  Proven
    empirically on the two witnesses:

      * get_range1 `start`: born round 0, held over an EDGE-1 loop-back
        (no MoreConflicts), presented round 1 with sav=104 = the walk-0
        computation (walk-1 gives 204) -- creation value CARRIED.
      * sf11_fire_missile anon: born round 0, held over an EDGE-3
        loop-back (MoreConflicts ran), presented round 1 with sav=3 =
        the walk-1 computation (walk-0 gives 2) -- REFRESHED.

    So: vintage = the LAST walk in (birth, presentation] whose edge is
    2 or 3 (a MoreConflicts crossing), else the birth walk.  Falls
    back to presentation walk_idx (v50 caches) then the round ordinal
    (pre-v50)."""
    b = row.get("birth_walk_idx")
    p = row.get("walk_idx")
    if b is None or p is None:
        wi = row.get("walk_idx")
        return wi if wi is not None else row.get("round", 0)
    walks = rt.get("il_walks") or []
    v = b
    for w in range(b + 1, min(p, len(walks) - 1) + 1):
        if walks[w].get("edge") in (2, 3):
            v = w
    return v


def _value_set(row: dict, alias_map: dict | None = None) -> set:
    v = {int(row["name"], 16)}
    tree = row.get("crm_tree")
    if tree:
        v |= {int(tree["temp"], 16), int(tree["alt"], 16)} - {0}
    if alias_map:
        # _Equal() DeAliases N_TEMP refs: every ring member whose master
        # is in the set is a ref of this conflict's name.
        v |= {a for a, m in alias_map.items() if m in v}
    return v


def alias_map(rt: dict) -> dict:
    """alias name -> ring MASTER, from the nbo birth base edges (trace
    image >= 2026-07-10g).  STempOffset inserts each new alias into the
    base's circular ring; following recorded base edges transitively
    reaches the flag-free master DeAlias would return."""
    base = {}
    for r in rt.get("nb") or []:
        if r.get("pass_kind") == "nbo" and r.get("alias_base"):
            base[int(r["name"], 16)] = int(r["alias_base"], 16)
    out = {}
    for a in base:
        m, hops = a, 0
        while m in base and hops < 64:
            m, hops = base[m], hops + 1
        out[a] = m
    return out


def calc_blocks(row: dict, snap, amap: dict | None = None) -> Optional[list]:
    """Per-block (blk_ptr, save, cost) raw unit sums for one conflict
    (pre-Weight -- the cv record's own vintage).  None = substrate gap."""
    blocks, pos = snap
    first, last = row["first"], row["last"]
    if first not in pos or last not in pos:
        return None
    (b0, i0), (b1, i1) = pos[first], pos[last]
    name = int(row["name"], 16)
    V = _value_set(row, amap)

    def _span(bi):
        b = blocks[bi]
        lo = i0 if bi == b0 else 0
        hi = i1 if bi == b1 else len(b["ins"]) - 1
        return b, b["ins"][lo:hi + 1]

    # idx substrate (image >= 2026-07-10f/g): real N_INDEXED index ptrs
    # + non-register tail operands.
    have_idx = any(r.get("res_idx") is not None
                   for bi in range(b0, b1 + 1) for r in _span(bi)[1])
    has_op_use = any(r["op0"] in V or r["op1"] in V
                     for bi in range(b0, b1 + 1) for r in _span(bi)[1])
    out = []
    for bi in range(b0, b1 + 1):
        b, span = _span(bi)
        bs = bc = 0
        for r in span:
            if r["opcode"] == OP_BLOCK:
                continue
            res_is_reg = r["result"] and (r["res_meta"] & 0xFF) == N_REGISTER
            for i, op, _meta, idx in (
                    (1, r["op1"], r["op1_meta"], r.get("op1_idx")),
                    (0, r["op0"], r["op0_meta"], r.get("op0_idx"))):
                if op and op in V:
                    bs += USE
                    if (i == 0 and r["opcode"] < FIRST_CONDITION
                            and res_is_reg):
                        bs += USE            # savcode _ReplaceOpnd doubling
                elif idx and idx in V:
                    bs += INDEX              # _ReplaceIdxOpnd
            for xo in (r.get("xtra_ops") or ()):
                if xo["name"] in V:
                    bs += USE                # tail direct ref (call parm
                                             # f(show_map_fn); i > 0, no
                                             # doubling)
                elif xo["idx"] and xo["idx"] in V:
                    bs += INDEX              # _ReplaceIdxOpnd, tail operand
                                             # (call parm f(table[t]))
            if r["result"] and r["result"] in V:
                if (r["opcode"] in (OP_MOV, OP_CONVERT)
                        and (r["res_meta"] & 0xFF) == N_TEMP
                        and (r["op0_meta"] & 0xFF) == N_TEMP
                        and (r["op0"] in V
                             or (r["op0_meta"] >> 8) & TF_STACK_PARM)):
                    bc += LOAD               # coalesced-move penalty
                else:
                    bs += DEF
                    if r["op0"] and (r["op0_meta"] & 0xFF) == N_REGISTER:
                        bs += USE
                    if (not have_idx
                            and (r["res_meta"] >> 8) & TF_INDEXED
                            and r["result"] == name and not has_op_use):
                        bs += INDEX          # legacy-substrate heuristic
            elif r.get("res_idx") and r["res_idx"] in V:
                bs += INDEX                  # _ReplaceIdxResult
        out.append((b["blk"], bs, bc))
    return out


def _clean(row: dict, snap, nbo: set, amap: dict | None = None) -> bool:
    """Substrate gate: False when the range contains an N_INDEXED ref
    whose index ptr is unrecorded (pre-2026-07-10f traces) or an
    UNMAPPED STempOffset alias temp (pre-2026-07-10g traces) -- rows
    where the iv substrate cannot support the walk."""
    blocks, pos = snap
    if row["first"] not in pos or row["last"] not in pos:
        return False
    (b0, i0), (b1, i1) = pos[row["first"]], pos[row["last"]]
    V = _value_set(row, amap)
    if amap:
        nbo = nbo - {format(a, "x") for a in amap}
    for bi in range(b0, b1 + 1):
        b = blocks[bi]
        lo = i0 if bi == b0 else 0
        hi = i1 if bi == b1 else len(b["ins"]) - 1
        for r in b["ins"][lo:hi + 1]:
            have_idx = r.get("res_idx") is not None
            for op, meta in ((r["op0"], r["op0_meta"]),
                             (r["op1"], r["op1_meta"]),
                             (r["result"], r["res_meta"])):
                if op and (meta & 0xFF) == N_INDEXED and not have_idx:
                    return False
                if op and format(op, "x") in nbo and op not in V:
                    return False
    return True


def _depth_map(rt: dict) -> dict:
    """blk ptr -> loop depth, folded over every recorded cv row (depth
    is a stable per-block property; conf-ptr free-list reuse does not
    poison it)."""
    depth = {}
    for rows in (rt.get("savecalc") or {}).values():
        for w in rows:
            depth[w["blk"]] = w["depth"]
    return depth


def _nbo_names(rt: dict) -> set:
    return {r["name"] for r in (rt.get("nb") or [])
            if r.get("pass_kind") == "nbo"}


def savings_for_row(rt: dict, row: dict, snap=None,
                    depth: dict | None = None,
                    amap: dict | None = None) -> Optional[int]:
    """Forward-computed final savings for one alloc row (None on a
    substrate gap).  When ``snap`` is not supplied, the row's own
    presentation-time WALK INDEX selects the vintage (v50 per-round
    snapshots; stream-order join -- round ordinals can desync from
    walk ordinals when a trip presents zero conflicts)."""
    if row.get("birth_walk_idx", 0) >= 1:
        # In-routine-born conflict (MoreConflicts/split machinery):
        # measured 0/146 exact under every walk vintage -- the refs
        # are created by the NEXT round's FixInstructions, invisible
        # to any recorded walk.  The P5 rewrite port's class; gap it
        # (None, not a guess) until modeled.
        return None
    snap = snap or snap_index(rt, _row_walk(rt, row))
    if snap is None:
        return None
    if row["first"] == row["last"]:
        return 0                     # single-ins early-out
    amap = alias_map(rt) if amap is None else amap
    if not _clean(row, snap, _nbo_names(rt), amap):
        return None
    got = calc_blocks(row, snap, amap)
    if got is None:
        return None
    depth = depth if depth is not None else _depth_map(rt)
    if any(b not in depth for b, _, _ in got):
        return None
    sv = sum(s * LOOP_W[depth[b]] for b, s, _ in got) \
        - sum(c * LOOP_W[depth[b]] for b, _, c in got)
    return max(sv, 0)


def ref_ledger(rt: dict, row: dict, snap=None,
               amap: dict | None = None) -> Optional[list]:
    """Per-REF attribution for one conflict: every unit of its savings
    named to (block, ins, kind, side, units).  THE actionable view for
    a Cascade 'needs a SAVINGS change' verdict: each `save`-side row is
    a candidate DELETION lever (drop sav by its weighted units), each
    absent re-read a candidate ADDITION lever.  None on substrate gap.
    When ``snap`` is not supplied, the row's presentation-time walk
    index selects the vintage."""
    snap = snap or snap_index(rt, _row_walk(rt, row))
    if snap is None:
        return None
    amap = alias_map(rt) if amap is None else amap
    if not _clean(row, snap, _nbo_names(rt), amap):
        return None
    blocks, pos = snap
    if row["first"] not in pos or row["last"] not in pos:
        return None
    (b0, i0), (b1, i1) = pos[row["first"]], pos[row["last"]]
    name = int(row["name"], 16)
    V = _value_set(row, amap)
    depth = _depth_map(rt)
    has_op_use = False
    for bi in range(b0, b1 + 1):
        b = blocks[bi]
        lo = i0 if bi == b0 else 0
        hi = i1 if bi == b1 else len(b["ins"]) - 1
        for r in b["ins"][lo:hi + 1]:
            if r["op0"] in V or r["op1"] in V:
                has_op_use = True
    out = []
    for bi in range(b0, b1 + 1):
        b = blocks[bi]
        d = depth.get(b["blk"], 0)
        lo = i0 if bi == b0 else 0
        hi = i1 if bi == b1 else len(b["ins"]) - 1
        for r in b["ins"][lo:hi + 1]:
            if r["opcode"] == OP_BLOCK:
                continue

            def _ev(kind, side, units, r=r, b=b, d=d):
                out.append({"blk": b["blk"], "depth": d, "ins": r["ins"],
                            "opcode": r["opcode"], "kind": kind,
                            "side": side, "units": units,
                            "weighted": units * LOOP_W[d]})
            res_is_reg = (r["result"]
                          and (r["res_meta"] & 0xFF) == N_REGISTER)
            for i, op, _m, idx in (
                    (1, r["op1"], r["op1_meta"], r.get("op1_idx")),
                    (0, r["op0"], r["op0_meta"], r.get("op0_idx"))):
                if op and op in V:
                    dbl = (i == 0 and r["opcode"] < FIRST_CONDITION
                           and res_is_reg)
                    _ev("use" + ("+dbl" if dbl else ""), "save",
                        USE * (2 if dbl else 1))
                elif idx and idx in V:
                    _ev("index", "save", INDEX)
            for xo in (r.get("xtra_ops") or ()):
                if xo["name"] in V:
                    _ev("use(parm)", "save", USE)
                elif xo["idx"] and xo["idx"] in V:
                    _ev("index(parm)", "save", INDEX)
            if r["result"] and r["result"] in V:
                if (r["opcode"] in (OP_MOV, OP_CONVERT)
                        and (r["res_meta"] & 0xFF) == N_TEMP
                        and (r["op0_meta"] & 0xFF) == N_TEMP
                        and (r["op0"] in V
                             or (r["op0_meta"] >> 8) & TF_STACK_PARM)):
                    _ev("coalesced-def", "cost", LOAD)
                else:
                    units = DEF
                    kind = "def"
                    if r["op0"] and (r["op0_meta"] & 0xFF) == N_REGISTER:
                        units += USE
                        kind = "def+reg-use"
                    have_idx = r.get("res_idx") is not None
                    if (not have_idx and (r["res_meta"] >> 8) & TF_INDEXED
                            and r["result"] == name and not has_op_use):
                        units += INDEX
                        kind += "+index(legacy)"
                    _ev(kind, "save", units)
            elif r.get("res_idx") and r["res_idx"] in V:
                _ev("index(store)", "save", INDEX)
    return out


def certify_routine(rt: dict) -> dict:
    """Identity gate: forward savings == recorded al savings for every
    row the substrate supports.  Since v50 this includes round>0 rows,
    each joined to its OWN round's walk (rr per-round snapshots); on
    pre-rr traces round>0 rows clamp to walk 0 and mostly gap, exactly
    as before."""
    res = {"rows": 0, "exact": 0, "gapped": 0, "misses": [],
           "rows_r1": 0, "exact_r1": 0}
    if snap_index(rt) is None:
        return res
    snaps = {}
    depth = _depth_map(rt)
    amap = alias_map(rt)
    for a in rt.get("alloc") or []:
        rnd = a.get("round", 0)
        wi = _row_walk(rt, a)
        if wi not in snaps:
            snaps[wi] = snap_index(rt, wi)
        fin = savings_for_row(rt, a, snaps[wi], depth, amap)
        if fin is None:
            res["gapped"] += 1
            continue
        res["rows"] += 1
        if rnd > 0:
            res["rows_r1"] += 1
        if fin == a["savings"]:
            res["exact"] += 1
            if rnd > 0:
                res["exact_r1"] += 1
        elif len(res["misses"]) < 6:
            res["misses"].append({"var": a.get("var"), "name": a["name"],
                                  "round": rnd,
                                  "recorded": a["savings"], "got": fin})
    return res


def certify_tu(td: dict) -> dict:
    tot = {"rows": 0, "exact": 0, "gapped": 0, "misses": [],
           "rows_r1": 0, "exact_r1": 0}
    for fn, rt in (td.get("by_func") or {}).items():
        r = certify_routine(rt)
        tot["rows"] += r["rows"]
        tot["exact"] += r["exact"]
        tot["gapped"] += r["gapped"]
        tot["rows_r1"] += r.get("rows_r1", 0)
        tot["exact_r1"] += r.get("exact_r1", 0)
        for m in r["misses"][:2]:
            tot["misses"].append({"fn": fn, **m})
    return tot
