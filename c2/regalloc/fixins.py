"""Offline port of the FixInstructions commit rewrite -- the P5 KERNEL
(TODO.md prediction-stack item 6, first increment 2026-07-10).

When GiveBestReg/GiveReqdRegister commits a conflict to a register,
FixInstructions@0x56F64 rewrites every reference of the conflict's
value set inside its ins_range to an N_REGISTER name carrying the
committed hw_reg_set.  This module PREDICTS the post-round IL from the
pre-round walk plus the round's commits, and certifies against the
recorded next-round walk (the v50 per-round ``rr`` snapshots -- image
2026-07-10i).

Why this matters: the masked/P5 residue class (build_city_item,
figure_go_to_target, show_move_highlight island 1,
place2_a_building_top -- the certified 2026-07-10 seat-dominant
survey) needs multi-seat counterfactuals: flipping an EARLY seat
invalidates every later commit window because the rewrites feed the
later windows' CountRegMoves credits and masks.  Replaying those
windows requires exactly this kernel: apply a commit's rewrite,
recompute the next window from the REWRITTEN IL.  Certifying the
kernel against recorded rounds grounds that replay.

Model (v1 -- per-slot class/reg prediction on ins present in BOTH
walks):

  for each committed conflict C (round-0 al row with a reg):
      V = {name} + crm_tree{temp, alt} (the DeAlias ring witness)
      range = [first, last] positions in the pre-round walk
  for each ins in both walks, for each slot (result, op0, op1):
      pre-slot name in V of a commit whose range covers the ins
        -> predict class N_REGISTER, reg = the commit's hw_reg_set
      else -> predict unchanged (class and, when N_REGISTER, reg)

  N_INDEXED slots resolve through the index ptr: when the INDEX name
  is committed, the slot stays N_INDEXED but its idx re-seats -- v1
  checks the slot class only for N_INDEXED (the idx-rewrite check
  needs the round-1 idx tail join, a v2 item).

Certification: ``certify_routine`` compares every predicted slot
against the recorded next-round walk; ``appeared``/``vanished`` ins
(NewIns splits / AxeDeadCode kills between rounds) are counted but not
predicted (v2: the axe model needs the be-graph dataflow, TODO P3).

Corpus certification (2026-07-10, image 2026-07-10i, all 38 TUs):
**152,009/152,010 slots exact (99.9993%)** over 1,231 routines.  The
single miss (lib32.c set_svga_640_480 +0x6c1529f0 op0) is a PROBE
artifact, not a model miss: the walk-0 row's op0_meta reads 0 -- the
trace's ``metaof`` helper guards against implausible pointers by
comparing high bytes against the block ptr, and this name lives in a
different heap segment, so its class is unreadable at walk-0 vintage
(same family as the set_db_sound ge-attribution slip, TODO P7).
"""
from __future__ import annotations

from typing import Optional

N_REGISTER, N_INDEXED = 3, 4


def _walk_ins(walk: dict) -> dict:
    return {r["ins"]: r for b in walk["blocks"] for r in b["ins"]}


def _walk_pos(walk: dict) -> dict:
    pos, n = {}, 0
    for b in walk["blocks"]:
        for r in b["ins"]:
            pos[r["ins"]] = n
            n += 1
    return pos


def _round_commits(rt: dict, rnd: int) -> list:
    """(value_set, first, last, reg_mask) per commit of round ``rnd``.

    Covers BOTH FixInstructions callers: ``rg`` rows (GiveBestReg,
    full al metadata) and ``rq`` rows (GiveReqdRegister parm-reg
    commits -- no name/range on the row; the name joins through the
    cn birth records and the range through the wr first-sighting
    ``_rng`` map).  Value sets extend through the STempOffset alias
    rings (savings.alias_map): FixInstructions DeAliases refs, so a
    ring member's ref rewrites when its master commits."""
    from c2.regalloc.savings import alias_map
    amap = alias_map(rt)
    cn_name = {}
    for c in rt.get("confs") or []:
        if c.get("name"):
            cn_name[c["conf"]] = c["name"]      # last birth wins
    rng = rt.get("_rng") or {}
    out = []
    for a in rt.get("alloc") or []:
        if not a.get("reg_name"):
            continue
        if a.get("source") == "rq":
            if rnd != 0:
                continue                        # parm commits are round 0
            nm = cn_name.get(a["conf"])
            r = rng.get(a["conf"])
            if not nm or not r:
                continue
            v = {int(nm, 16)}
            first, last = r
        else:
            if a.get("round", 0) != rnd:
                continue
            v = {int(a["name"], 16)}
            t = a.get("crm_tree")
            if t:
                v |= {int(t["temp"], 16), int(t["alt"], 16)} - {0}
            first, last = a["first"], a["last"]
        v |= {al for al, m in amap.items() if m in v}
        reg = a.get("reg")
        mask = int(reg, 16) if isinstance(reg, str) else (reg or 0)
        out.append((v, first, last, mask))
    return out


_SLOTS = (("result", "res_meta", "res_reg"),
          ("op0", "op0_meta", "op0_reg"),
          ("op1", "op1_meta", "op1_reg"))


def certify_routine(rt: dict, rnd: int = 0) -> dict:
    """Predict walk ``rnd+1`` from walk ``rnd`` + round-``rnd`` commits;
    compare per slot.  Returns slot counts + the ins census."""
    res = {"slots": 0, "exact": 0, "misses": [],
           "shared": 0, "appeared": 0, "vanished": 0, "no_sub": False}
    walks = rt.get("il_walks") or []
    if len(walks) < rnd + 2:
        res["no_sub"] = True
        return res
    w0, w1 = _walk_ins(walks[rnd]), _walk_ins(walks[rnd + 1])
    pos = _walk_pos(walks[rnd])
    commits = _round_commits(rt, rnd)
    shared = set(w0) & set(w1)
    res["shared"] = len(shared)
    res["appeared"] = len(set(w1) - set(w0))
    res["vanished"] = len(set(w0) - set(w1))

    def commit_for(name: int, ip: str):
        for v, first, last, mask in commits:
            if name in v and first in pos and last in pos \
                    and pos[first] <= pos[ip] <= pos[last]:
                return mask
        return None

    for ip in shared:
        r0, r1 = w0[ip], w1[ip]
        for slot, meta_k, reg_k in _SLOTS:
            name0 = r0[slot]
            if not name0:
                continue
            cls0, cls1 = r0[meta_k] & 0xFF, r1[meta_k] & 0xFF
            mask = commit_for(name0, ip)
            res["slots"] += 1
            if mask is not None:
                # The rewritten ref carries the WIDTH VIEW of the
                # committed register matching the operand's own type:
                # a dword committed to EAX (0x1000003) is referenced
                # as AL (0x2), AX (0x3) or EAX itself -- all subsets
                # of the commit mask (REG_ENC low bits are shared
                # across views).  Predict: N_REGISTER + a non-empty
                # subset of the commit mask.
                got = r1[reg_k] or 0
                ok = (cls1 == N_REGISTER and got != 0
                      and (got & ~mask) == 0)
            elif cls0 == N_INDEXED:
                # index may re-seat under an INDEX commit; class holds.
                ok = (cls1 == N_INDEXED)
            else:
                ok = (cls1 == cls0
                      and (cls0 != N_REGISTER or r1[reg_k] == r0[reg_k]))
            if ok:
                res["exact"] += 1
            elif len(res["misses"]) < 6:
                res["misses"].append(
                    {"ins": ip, "slot": slot, "name": hex(name0),
                     "pre_cls": cls0, "post_cls": cls1,
                     "pred_reg": mask, "got_reg": r1[reg_k]})
    return res


def certify_tu(td: dict) -> dict:
    tot = {"slots": 0, "exact": 0, "routines": 0, "no_sub": 0,
           "misses": []}
    for fn, rt in (td.get("by_func") or {}).items():
        r = certify_routine(rt)
        if r["no_sub"]:
            tot["no_sub"] += 1
            continue
        tot["routines"] += 1
        tot["slots"] += r["slots"]
        tot["exact"] += r["exact"]
        for m in r["misses"][:2]:
            tot["misses"].append({"fn": fn, **m})
    return tot
