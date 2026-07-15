"""Offline port of wcc386 10.0a NeighboursUse@0x580c0 -- the with.regs
(candidate MASK) channel.

Capture item 2 of the seat-class plan (docs/regalloc-mechanics.md in the
watcom10.0a repo): the conflict's interference mask `with.regs` is what
excludes GiveBestReg candidates; predicting it under a hypothesized IL
change is the missing half of the what-if machinery (scores are handled
by the certified `crm10a_v2`).

Grounded in BOTH the OW v1 source (bld/cg/c/regalloc.c NeighboursUse,
bld/cg/c/liveinfo.c NowAlive/NowDead) and the 10.0a binary disasm; the
inputs are the v45 gi trailing fields (per-ins live.regs / live.out[4] /
live.within / zap->reg / res_meta / op0_meta, REAL block-hopped walk) +
the wr graph fields (the conflict's own id bits).

The no_conflict REGISTER channel only tracks N_REGISTER mov partners
(NowAlive/NowDead first branch); temp partners affect only the bit
channels, which stay recorded (wr) rather than recomputed.

KNOWN GAPS (surfaced as ``None`` returns / census buckets, not silent
errors):

* ``conf->name->v.usage & (NEEDS_MEMORY | USE_ADDRESS)`` (name+0x18 &
  0x88) is RECORDED from image 2026-07-10c (wr trailing field, alloc row
  ``usage``); ``with_regs`` reads it directly (the ``usage_mem``
  parameter is a test override only).
* CheckIndexZap needs the N_INDEXED dst's index->conflict mapping;
  approximated by OR-ing the zap reg when the dst is N_INDEXED (class
  1 -- meta channel).  Exactness measured, not assumed.
"""
from __future__ import annotations

from typing import Optional

OP_MOV = 0x26
OP_BLOCK = 0x4B
OP_CALL = 0x36
OP_CALL_INDIRECT = 0x29

N_INDEXED = 1
N_TEMP = 2
N_REGISTER = 3


def _cls(meta) -> int:
    return (meta or 0) & 0xFF


def with_regs(row: dict, *, usage_mem: bool = False) -> Optional[int]:
    """Recompute conf->with.regs from the row's own gi walk.

    Returns None when the v45 substrate is missing.  ``usage_mem`` is the
    NEEDS_MEMORY|USE_ADDRESS bit of the conflict's name (not yet traced;
    certify both polarities).
    """
    walk = row.get("own_walk")
    graph = row.get("commit_graph") or row.get("graph")
    nm = row.get("name")
    if not walk or graph is None or nm is None:
        return None
    if row.get("usage") is not None:
        usage_mem = bool(row["usage"] & 0x88)
    if not all("live_regs" in i for i in walk):
        return None
    conf_name = int(nm, 16)
    id_within = graph["id_within"]
    id_out = graph["id_out"]
    id_empty = id_within == 0 and not any(id_out)

    def _overlap(ins) -> bool:
        return (any(a & b for a, b in zip(ins["live_out"], id_out))
                or (ins["live_within"] & id_within) != 0
                or id_empty)

    w = 0
    no = 0
    n = len(walk)
    if n < 2:
        return 0
    # OW: ins = range.first; loop { ins = ins->next; process; } until last.
    # The gi walk INCLUDES range.first at index 0 -> process walk[1:].
    for i in range(1, n):
        ins = walk[i]
        op = ins["opcode"]
        last = i == n - 1
        if op != OP_BLOCK:
            res = ins["result"]
            rr = ins["result_reg"]
            res_is_reg = _cls(ins.get("res_meta")) == N_REGISTER
            # NowDead(dst) -- register channel
            if res and res_is_reg:
                no &= ~rr
            if op != OP_MOV:
                if res == conf_name:
                    no = 0
            elif ins["op0"] == conf_name:
                # NowAlive(dst)
                if res and res_is_reg:
                    no |= rr
            elif res == conf_name:
                no = 0
                # NowAlive(definition = op0)
                if ins["op0"] and _cls(ins.get("op0_meta")) == N_REGISTER:
                    no |= ins["op0_reg"]
            # live-range gate: conf live ACROSS this ins?
            if not last:
                nxt = walk[i + 1]
                nxt_overlap = (any(a & b for a, b in
                                   zip(nxt["live_out"], id_out))
                               or (nxt["live_within"] & id_within) != 0)
                if usage_mem or id_empty or nxt_overlap:
                    w |= ins["zap_reg"]
                    if res and res_is_reg:
                        w |= rr
                else:
                    # dead after this ins: CheckIndexZap when it WAS live
                    if (any(a & b for a, b in
                            zip(ins["live_out"], id_out))
                            or (ins["live_within"] & id_within) != 0):
                        if res and _cls(ins.get("res_meta")) == N_INDEXED:
                            w |= ins["zap_reg"]
            else:
                if res and _cls(ins.get("res_meta")) == N_INDEXED:
                    w |= ins["zap_reg"]
        # live-set fold
        if _overlap(ins):
            w |= ins["live_regs"] & ~no & 0xFFFFFFFF
        if op in (OP_CALL, OP_CALL_INDIRECT):
            no = 0
        elif op == OP_BLOCK:
            no = 0
    return w & 0xFFFFFFFF


def certify(rows: list[dict]) -> dict:
    """Compare the port against the recorded wr mask for every row that
    has both.  Returns a census dict."""
    res = {"total": 0, "exact": 0, "exact_mem": 0, "either": 0,
           "no_substrate": 0, "usage_recorded": 0, "misses": []}
    for a in rows:
        rec = a.get("commit_withregs")
        if rec is None:
            continue
        v0 = with_regs(a, usage_mem=False)
        if v0 is None:
            res["no_substrate"] += 1
            continue
        v1 = with_regs(a, usage_mem=True)
        res["total"] += 1
        if a.get("usage") is not None:
            res["usage_recorded"] += 1
        if v0 == rec:
            res["exact"] += 1
        if v1 == rec:
            res["exact_mem"] += 1
        if v0 == rec or v1 == rec:
            res["either"] += 1
        elif len(res["misses"]) < 8:
            res["misses"].append({"var": a.get("var"), "name": a.get("name"),
                                  "rec": hex(rec), "got": hex(v0)})
    return res
