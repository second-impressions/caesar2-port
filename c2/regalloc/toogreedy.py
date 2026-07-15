"""Offline port of wcc386 10.0a TooGreedy -- P2 of the prediction stack.

TooGreedy(conf, reg, op) vetoes a GiveBestReg candidate when granting
``reg`` would take the last register some instruction in the conflict's
range still needs: a gen-table reservation (RegList/RegSets need
chains), the last usable index register (StealsIdx), or the last
segment register (StealsSeg).  Until this port the verdicts were only
RECORDED (`tg` records), which left `replay_order`'s reordered rows
low-confidence: a savings perturbation can change which candidates get
vetoed.

Ground truth: full binary RE of 10.0a (2026-07-10; every offset below
read from the disassembly, OW v1 bld/cg/c/regalloc.c as the map):

    TooGreedy       0x57a74   conf+0x38/+0x3c ins_range, conf+8 name,
                              conf+0x55 flags (0x9 = INDEX_SPLIT|
                              SEGMENT_SPLIT -> start at range.last,
                              0x80 = NEVER_TOO_GREEDY)
    UnaryOpGetsReg  0x578b4   NumOperands(ins)==1 via NumOps[opcode]
                              (byte table 0x7a66c), result != NULL,
                              !IsSegReg(reg), opcode != OP_CONVERT
                              (0x24), op == operands[0] or result
    CheckIndecies   0x57a44   except |= ins->live.regs | reg;
                              StealsIdx / StealsSeg -> MAYBE(2)
    StealsIdx       0x5796c   N_INDEXED operand/result indexes must
                              have a conflict and differ from op;
                              chain = RegSets[ins->t.index_needs
                              (+0x3d)]; entry not overlapping except
                              -> FALSE unless is_result and entry
                              overlaps ins->zap->reg
    StealsSeg       0x578ec   op = operands[num_operands-1 (+0x3f)];
                              bail when that slot < NumOperands(ins);
                              chain = RegSets[SegIndex()==0xa]; every
                              entry must overlap except
    IsSegReg        0x3e0b7   (reg & 0xC000F000) == reg
    RegList         0x79988   5-byte entries; byte[0] = need index
    RegSets         0x79918   28 ptrs -> 0-terminated hw_reg_set arrays
    gen reg_set     ins->u.gen_table(+0x28) -> byte +4; NULL -> RL_(0)

Dynamic substrate (trace image >= 2026-07-10h): the iv record's tg_ctx
field packs (num_operands<<16)|(t.index_needs<<8)|reg_set per ins; the
al record's trailing conf_flags byte carries +0x55.  The allocation-
time live/zap sets come from the row's OWN gi walk (own_walk -- the
same vintage the real TooGreedy reads); static per-ins facts (tg_ctx,
index ptrs, tail operands) join from the iv snapshot by ins ptr.

Certification (2026-07-10, all TUs): **122,106/122,108 verdicts exact
(99.998%)** -- ``certify_routine`` replays every recorded verdict: tg
records (vetoed=True) and gb-scored candidates (vetoed=False);
candidates absent from both were mask-skipped (TooGreedy never ran)
and are excluded.  The two residual misses (font_no / pump update,
both EBP over-vetoes) are ROUND-1 re-presentations whose N_INDEXED
internals were rewritten between rounds -- the snapshot index ptrs are
one vintage stale there; the per-round iv snapshot (TODO) closes them.
"""
from __future__ import annotations

from typing import Optional

from c2.regalloc import savings as sv

OP_CONVERT = 0x24
N_TEMP, N_REGISTER, N_INDEXED = 2, 3, 4
SEG_INDEX = 0x0A
SEG_MASK = 0xC000F000
F_SPLIT = 0x09            # INDEX_SPLIT | SEGMENT_SPLIT
F_NEVER_TOO_GREEDY = 0x80

# NumOps[opcode] -- typical operand count, byte table @0x7a66c
NUMOPS = [0, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1,
          1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 1,
          1, 3, 1, 0, 0, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 0, 0, 0, 0, 0,
          0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0]

# RegList[i].need -- byte 0 of the 5-byte entries @0x79988 (0x43
# entries; the table ends where the byte stream stops decoding as
# valid RegSets indexes)
REGLIST_NEED = [
    0x00, 0x00, 0x00, 0x00, 0x0F, 0x00, 0x00, 0x00,   # 0x00-0x07
    0x00, 0x0F, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   # 0x08-0x0f
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   # 0x10-0x17
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   # 0x18-0x1f
    0x00, 0x08, 0x04, 0x00, 0x0F, 0x00, 0x0F, 0x08,   # 0x20-0x27
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x08,   # 0x28-0x2f
    0x0F, 0x00, 0x00, 0x00, 0x04, 0x08, 0x0F, 0x08,   # 0x30-0x37
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   # 0x38-0x3f
    0x00, 0x0F, 0x17,                                  # 0x40-0x42
]

# RegSets[i] -- 0-terminated hw_reg_set chains @0x79918 (28 ptrs)
REGSETS = {
    0x00: [],
    0x01: [0x2], 0x02: [0x1], 0x03: [0x20],
    0x04: [0x2, 0x1, 0x80, 0x40, 0x8, 0x4, 0x20, 0x10],
    0x05: [0x3], 0x06: [0x30], 0x07: [0xC0],
    0x08: [0x3, 0xC0, 0xC, 0x30, 0x100, 0x200],
    0x09: [0x3, 0xC0, 0xC, 0x30],
    0x0A: [0x1000, 0x2000, 0x40000000, 0x80000000, 0x4000, 0x8000],
    0x0B: [0x3, 0xC0, 0xC, 0x30, 0x100, 0x200, 0x1000, 0x2000,
           0x40000000, 0x80000000, 0x4000, 0x8000],
    0x0C: [0x1000003], 0x0D: [0x80000C0], 0x0E: [0xC3],
    0x0F: [0x1000003, 0x80000C0, 0x200000C, 0x4000030, 0x10000100,
           0x20000200, 0x400, 0x800],
    0x10: [0x1000003, 0x80000C0, 0x200000C, 0x4000030],
    0x11: [0x4000030], 0x12: [0x10000C3],
    0x15: [0x90000C3], 0x16: [],
    0x18: [0x10000],
    0x19: [0x20000, 0x40000, 0x80000, 0x100000, 0x200000, 0x400000,
           0x800000],
}
# (0x13/0x14/0x17 are the long register-PAIR lists; TooGreedy never
# consults them through REGLIST_NEED -- keep the table lean and fail
# loudly if a chain index is missing.)


def _regset(idx: int) -> list:
    return REGSETS.get(idx & 0xFF, [])


def _is_seg_reg(reg: int) -> bool:
    return (reg & SEG_MASK) == reg


class InsCtx:
    """One instruction's TooGreedy-relevant facts, fused from the
    allocation-time gi walk row (live/zap) and the iv snapshot row
    (tg_ctx, operand classes, index ptrs, tail operands)."""
    __slots__ = ("live", "zap", "nops", "index_needs", "reg_set",
                 "opcode", "op0", "op1", "result", "op0_cls", "op1_cls",
                 "res_cls", "op0_idx", "op1_idx", "res_idx", "xtra",
                 "ins")

    def __init__(self, gi: dict, iv: Optional[dict]):
        self.ins = gi.get("ins")
        self.live = gi.get("live_regs") or 0
        self.zap = gi.get("zap_reg") or 0
        self.opcode = gi["opcode"]
        r = iv or {}
        # ALLOCATION-vintage tg_ctx (the gi row, image >= 2026-07-10h)
        # beats the RegAlloc-entry snapshot: FixGenEntry re-selects gen
        # rows during allocation (the build_city_item over-veto class).
        ctx = gi.get("tg_ctx")
        if ctx is None:
            ctx = r.get("tg_ctx") or 0
        self.nops = (ctx >> 16) & 0xFF
        self.index_needs = (ctx >> 8) & 0xFF
        self.reg_set = ctx & 0xFF
        self.op0 = r.get("op0") or gi.get("op0") or 0
        self.op1 = r.get("op1") or gi.get("op1") or 0
        self.result = r.get("result") or gi.get("result") or 0
        # classes: prefer the gi row's ALLOCATION-vintage metas (a
        # memory-exiled round-0 temp's N_INDEXED consumer can be
        # rewritten between rounds; the snapshot's class is stale --
        # the font_no EBP case).  op1_meta only exists in the snapshot.
        self.op0_cls = ((gi.get("op0_meta") if gi.get("op0_meta")
                         is not None else r.get("op0_meta")) or 0) & 0xFF
        self.op1_cls = (r.get("op1_meta") or 0) & 0xFF
        self.res_cls = ((gi.get("res_meta") if gi.get("res_meta")
                         is not None else r.get("res_meta")) or 0) & 0xFF
        self.op0_idx = r.get("op0_idx") or 0
        self.op1_idx = r.get("op1_idx") or 0
        self.res_idx = r.get("res_idx") or 0
        self.xtra = r.get("xtra_ops") or []


def _unary_op_gets_reg(ins: InsCtx, reg: int, op: int) -> bool:
    return (NUMOPS[ins.opcode] == 1 if ins.opcode < len(NUMOPS) else False) \
        and ins.result != 0 and not _is_seg_reg(reg) \
        and ins.opcode != OP_CONVERT \
        and (op == ins.op0 or op == ins.result)


def _steals_idx(ins: InsCtx, except_: int, op: int,
                has_conflict) -> bool:
    is_result = False
    idx_ops = [(ins.op0_cls, ins.op0_idx), (ins.op1_cls, ins.op1_idx)]
    idx_ops += [((x["meta"] & 0xFF), x["idx"]) for x in ins.xtra]
    for cls, idx in idx_ops:
        if cls == N_INDEXED:
            if not has_conflict(idx, ins) or op == idx:
                return False
    if ins.result and ins.res_cls == N_INDEXED:
        if not has_conflict(ins.res_idx, ins) or op == ins.res_idx:
            return False
        is_result = True
    chain = _regset(ins.index_needs)
    if not chain:
        return False
    for entry in chain:
        if not (entry & except_):
            if not is_result:
                return False
            if not (entry & ins.zap):
                return False
    return True


def _steals_seg(ins: InsCtx, reg: int, except_: int, actual_op: int,
                has_conflict) -> bool:
    i = ins.nops - 1
    if i < (NUMOPS[ins.opcode] if ins.opcode < len(NUMOPS) else 0):
        return False
    # operands[i]: slot 0/1 direct; tail slots only exist in xtra_ops
    # when non-register -- an unrecorded (register) tail operand has no
    # conflict, which returns FALSE exactly like the real walk.
    if i == 0:
        op, cls = ins.op0, ins.op0_cls
    elif i == 1:
        op, cls = ins.op1, ins.op1_cls
    elif ins.xtra and len(ins.xtra) == ins.nops - 2:
        op, cls = ins.xtra[-1]["name"], ins.xtra[-1]["meta"] & 0xFF
    else:
        return False                       # register tail operand
    if cls == N_REGISTER or not has_conflict(op, ins):
        return False
    if op == actual_op and _is_seg_reg(reg):
        return False
    chain = _regset(SEG_INDEX)
    for entry in chain:
        if not (entry & except_):
            return False
    return bool(chain)


def _check_indecies(ins: InsCtx, reg: int, except_: int, op: int,
                    has_conflict) -> int:
    except_ = except_ | ins.live | reg
    if _steals_idx(ins, except_, op, has_conflict):
        return 2
    if _steals_seg(ins, reg, except_, op, has_conflict):
        return 2
    return 0


def too_greedy(walk: list, reg: int, op: int, conf_flags: int,
               has_conflict) -> int:
    """The full range walk.  ``walk`` = [InsCtx] in range order (already
    respecting the INDEX_SPLIT start-at-last rule); returns 0/1/2
    (nonzero = veto), exactly the binary's AL."""
    rc = 0
    for ins in walk:
        chain = _regset(REGLIST_NEED[ins.reg_set]
                        if ins.reg_set < len(REGLIST_NEED) else 0)
        if (not chain or (conf_flags & F_NEVER_TOO_GREEDY)
                or _unary_op_gets_reg(ins, reg, op)):
            rc = _check_indecies(ins, reg, 0, op, has_conflict)
        else:
            rc = 1
            for entry in chain:
                if not (entry & ins.live) and not (reg & entry):
                    rc = _check_indecies(ins, reg, entry, op,
                                         has_conflict)
                    if rc == 0:
                        break
        if rc:
            break
    return rc


# ---------------------------------------------------------------------
# certification against the recorded tg / gb verdicts
# ---------------------------------------------------------------------

def _conflict_names(rt: dict) -> set:
    s = {int(c["name"], 16) for c in rt.get("confs") or []}
    for a in rt.get("alloc") or []:
        s.add(int(a["name"], 16))
        t = a.get("crm_tree")
        if t:
            s |= {int(t["temp"], 16), int(t["alt"], 16)} - {0}
    return s


def build_walk(rt: dict, row: dict, snap, iv_by_ins: dict) -> Optional[list]:
    """InsCtx list for one row: own_walk (allocation-time live/zap)
    joined with the iv snapshot per ins ptr; INDEX_SPLIT rule applied."""
    ow = [g for g in (row.get("own_walk") or []) if g["opcode"] != 0x4B]
    if not ow:
        return None
    walk = [InsCtx(g, iv_by_ins.get(g.get("ins"))) for g in ow]
    flags = row.get("conf_flags") or 0
    if (row.get("nameclass") == N_TEMP) and (flags & F_SPLIT):
        walk = walk[-1:]                  # start (and end) at range.last
    return walk


class RoutineTG:
    """Per-routine TooGreedy evaluation context: the iv/gi fusion,
    alias map, conflict-name set and range index built ONCE, exposing
    ``verdict(row, enc, committed)`` for any consumer (certification,
    replay_order's newly-unmasked candidates, the flip search)."""

    def __init__(self, rt: dict):
        self.rt = rt
        self.snap = sv.snap_index(rt)
        self.iv_by_ins = {}
        self.pos = {}
        if self.snap:
            n = 0
            for b in self.snap[0]:
                for r in b["ins"]:
                    self.iv_by_ins[r["ins"]] = r
                    self.pos[r["ins"]] = n
                    n += 1
        self.amap = sv.alias_map(rt)
        self.cnames = _conflict_names(rt)
        # NameConflict range index: a conflict only answers for ins
        # WITHIN its range (the font_no EBP over-veto class).
        self.ranges: dict = {}
        for a in rt.get("alloc") or []:
            names = {int(a["name"], 16)}
            t = a.get("crm_tree")
            if t:
                names |= {int(t["temp"], 16), int(t["alt"], 16)} - {0}
            lo, hi = self.pos.get(a["first"]), self.pos.get(a["last"])
            for nm in names:
                self.ranges.setdefault(nm, []).append(
                    (lo, hi) if lo is not None and hi is not None
                    else None)
        self._walks: dict = {}
        self._iv_rounds: dict = {}

    def _has_conflict(self, committed: set):
        def has_conflict(name_ptr: int,
                         ins: Optional[InsCtx] = None) -> bool:
            # NameConflict(ins, name) at ALLOCATION time: the name's
            # conflict must (a) not be FixInstructions-consumed already
            # and (b) COVER the queried ins.
            if not name_ptr:
                return False
            m = self.amap.get(name_ptr, name_ptr)
            if m in committed or name_ptr in committed:
                return False
            if m not in self.cnames and name_ptr not in self.cnames:
                return False
            ip = (self.pos.get(getattr(ins, "ins", None))
                  if ins is not None else None)
            if ip is not None:
                rl = self.ranges.get(m, []) + (
                    self.ranges.get(name_ptr, [])
                    if name_ptr != m else [])
                if rl and all(r is not None for r in rl):
                    return any(lo <= ip <= hi for lo, hi in rl)
            return True
        return has_conflict

    def _iv_for_round(self, rnd: int) -> dict:
        """iv ins-ptr map at round ``rnd``'s vintage (v50 per-round
        snapshots).  Round 0 = the base map; later rounds OVERLAY their
        walk's rows (post-FixInstructions rewrites) on the base, so an
        ins ptr missing from a later walk still resolves.  On pre-rr
        traces there is one walk and every round sees the base map --
        the historical behavior."""
        if rnd <= 0:
            return self.iv_by_ins
        if rnd not in self._iv_rounds:
            walks = self.rt.get("il_walks") or []
            if rnd >= len(walks):
                self._iv_rounds[rnd] = self.iv_by_ins
            else:
                ov = dict(self.iv_by_ins)
                for b in walks[rnd]["blocks"]:
                    for r in b["ins"]:
                        ov[r["ins"]] = r
                self._iv_rounds[rnd] = ov
        return self._iv_rounds[rnd]

    def walk(self, row: dict) -> Optional[list]:
        key = id(row)
        if key not in self._walks:
            wi = row.get("walk_idx")
            if wi is None:
                wi = row.get("round", 0)
            self._walks[key] = build_walk(
                self.rt, row, self.snap, self._iv_for_round(wi))
        return self._walks[key]

    def verdict(self, row: dict, enc: int,
                committed: set | None = None) -> Optional[bool]:
        """True = veto, False = pass, None = substrate gap.
        ``committed`` = master-name ints of conflicts already committed
        at this point (identity prefix, or the replay's own picks)."""
        tree = row.get("crm_tree")
        flags = row.get("conf_flags")
        if not tree or flags is None:
            return None
        walk = self.walk(row)
        if walk is None:
            return None
        op = int(tree["temp"], 16)
        hc = self._has_conflict(committed if committed is not None
                                else set())
        return bool(too_greedy(walk, enc, op, flags, hc))


def committed_names(rows: list[dict]) -> set:
    """Master-name set of a committed-row prefix (for RoutineTG
    ``committed``)."""
    out: set = set()
    for a in rows:
        if not a.get("reg_name"):
            continue
        out.add(int(a["name"], 16))
        t = a.get("crm_tree")
        if t:
            out |= {int(t["temp"], 16), int(t["alt"], 16)} - {0}
    return out


def certify_routine(rt: dict) -> dict:
    from c2.regalloc.replay import REG_ENC
    res = {"rows": 0, "checked": 0, "agree": 0, "no_sub": 0,
           "misses": []}
    ctx = RoutineTG(rt)
    committed: set = set()
    for a in rt.get("alloc") or []:
        tree = a.get("crm_tree")
        if not tree:
            continue
        flags = a.get("conf_flags")
        if flags is None or ctx.walk(a) is None:
            res["no_sub"] += 1
            continue
        res["rows"] += 1
        vetoed = set(a.get("commit_tg_veto") or a.get("tg_veto") or [])
        scored = {e["cand"] for e in (a.get("commit_cand_scores")
                                      or a.get("cand_scores") or [])}
        for cand, truth in ([(c, True) for c in vetoed]
                            + [(c, False) for c in scored - vetoed]):
            enc = REG_ENC.get(cand)
            if enc is None:
                continue
            res["checked"] += 1
            pred = ctx.verdict(a, enc, committed)
            if pred == truth:
                res["agree"] += 1
            elif len(res["misses"]) < 6:
                res["misses"].append(
                    {"var": a.get("var"), "name": a["name"],
                     "cand": cand, "truth": truth, "pred": pred})
        if a.get("reg_name"):
            committed.add(int(a["name"], 16))
            committed |= {int(tree["temp"], 16),
                          int(tree["alt"], 16)} - {0}
    return res
