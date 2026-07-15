"""Offline port of wcc386 10.0a FlowConflicts -- the within-block backward
liveness scan (capture item 3, layer 3a).

Grounded in OW v1 bld/cg/c/liveinfo.c ``FlowConflicts`` + the 10.0a
opcode numbering (OW opcodes.h enum, corroborated by the CountRegMoves
comm table {1,2,5,9,a,b} = ADD, EXT_ADD, MUL, AND, OR, XOR):

    per block, walking instructions BACKWARD from the block-end live set
    (the block struct's own pseudo-ins live fields = the ``bs`` row --
    the sentinel keeps the RAW alive set, real rows get |unalterable):
      1. alive.regs &= ~ins->zap->reg
      2. result:  N_REGISTER -> NowDead (clear its reg);
                  N_INDEXED  -> the INDEX name goes NowAlive (verbatim
                  OW FlowConflicts) -- REGS-NEUTRAL pre-allocation: the
                  index is a temp, and NowAlive on a temp only touches
                  the bit channels.  (Early versions of this port
                  poisoned every indexed row -- 5,945/10,388 rows -- and
                  scored 1.5%; the fix took it to the certified figure
                  in the module tail.)
      3. operands -> NowAlive (N_REGISTER -> set its reg; N_INDEXED ->
         regs-neutral as above), EXCEPT the x-op-x idiom: SUB/XOR/MOD/
         DIV with operands[0]==operands[1] of class N_REGISTER skips
         ALL operands (the result is value-independent: xor eax,eax).
      4. ins->head.live.regs = alive.regs | CurrProc->state.unalterable

    ``unalterable`` is not traced; it is recovered per routine as the
    AND over every recorded INS live_regs (bs sentinel rows excluded --
    the sentinel store skips the |unalterable).

    Register-name resolution: the per-routine gi regmap first, then the
    TU-GLOBAL map (the AllocRegName cache is per-compile; register-name
    ptrs are stable across routines) -- only a name unresolved by BOTH
    poisons the remaining (earlier) rows of its block.

This is the REGS channel only -- the channel that feeds
``neighbours.with_regs``'s live-set fold and every seat question.  The
bit channels (out_of_block/within_block) additionally need per-name
conflict-id assignment (FindConflictNode + AssignBit) -- layer 3b,
together with the global dataflow over the ``be`` flow graph.

Substrate: trace cache v46 ``il_walks`` (the bs/be/iv MakeConflicts
snapshot) + the per-routine register-name map learned from gi walks
(c2.regalloc.realization.routine_regmap).
"""
from __future__ import annotations

from c2.regalloc.realization import routine_regmap

N_MEMORY = 1
N_REGISTER = 3
# hw_reg_set dword: low word = 8/16-bit reg bits, high word = 32-bit regs
# PLUS the x87 stack: bits 16..23 (0x00ff0000) are ST0..ST7.  Their
# liveness varies with FP-stack depth and has no N_REGISTER-name
# representation in the IL rows -- a separate channel, irrelevant to the
# GP seat machinery (GiveBestReg candidates are DoubleRegs/WordRegs/
# byte regs).  The port models and certifies the GP channel only.
FPU_BITS = 0x00FF0000
GP_MASK = 0xFFFFFFFF & ~FPU_BITS
N_INDEXED = 4          # binary-proven in FlowConflicts@0x5a259:
                       # `cmp byte[name+4],4` -> index name at +0xc
OP_BLOCK = 0x4B
# OW opcodes.h enum order at 10.0a numbering (OP_NOP=0):
XOPX_SKIP = {0x3, 0xB, 0x8, 0x7}     # OP_SUB, OP_XOR, OP_MOD, OP_DIV


def _cls(meta: int) -> int:
    return meta & 0xFF


def routine_unalterable(rt: dict) -> int:
    """CurrProc->state.unalterable, recovered as the AND over every
    recorded INS live_regs in the routine's first IL snapshot (bs
    sentinel rows are excluded: FlowConflicts' sentinel store keeps the
    raw alive set -- observed 0 -- without the |unalterable)."""
    acc = 0xFFFFFFFF
    for w in (rt.get("il_walks") or [])[:1]:
        for b in w["blocks"]:
            for i in b["ins"]:
                acc &= i["live_regs"]
    return (acc & GP_MASK) if acc != 0xFFFFFFFF else 0


def certify_block(blk: dict, regmap: dict, unalt: int,
                  fallback: dict | None = None) -> dict:
    """Replay the backward scan over one snapshot block; compare each
    predicted live_regs with the recorded one.  Returns counts.  Only a
    register name resolvable by NEITHER map poisons the remaining
    (earlier) rows; N_INDEXED is regs-neutral (see module doc)."""
    out = {"rows": 0, "exact": 0, "skipped_unres": 0, "misses": []}
    fallback = fallback or {}

    def _enc(ptr):
        v = regmap.get(ptr)
        return v if v is not None else fallback.get(ptr)

    direct = blk["ins"] and blk["ins"][0].get("res_reg") is not None
    # PARM-DEF promotion (observational, certified): between an op-0x2c
    # parm-register def and its capture MOV, the recorded liveness holds
    # the FULL parm register even when the IL use is a sub-register name
    # (char parm captured via the AL/DL/... name).  Promote a subset-use
    # to the parent's full set when the parent was 0x2c-defined in this
    # block.  (40/16,572 rows before this rule; every one an entry-block
    # parm capture.)
    parm_defs = [r["res_reg"] for r in blk["ins"]
                 if direct and r["opcode"] == 0x2C and r.get("res_reg")]

    def _promote(enc: int) -> int:
        for full in parm_defs:
            if enc and enc != full and (enc & full) == enc:
                return full
        return enc

    # SEED from the LAST REAL INS's recorded live, not the bs sentinel:
    # FlowConflicts@0x5a259 initializes alive from the sentinel's stored
    # live (= the block's live-OUT, written by the inter-block pass), but
    # by MakeConflicts-snapshot time the sentinel reads 0 (reset after
    # the last run) while the per-ins values are relative to the stale
    # nonzero live-out.  rec(last) IS the exact backward state above the
    # last ins (post-kill), so seeding there verifies every earlier row
    # and only the last row itself goes unchecked (counted as `seeded`).
    if not blk["ins"]:
        return out
    alive = blk["ins"][-1]["live_regs"] & GP_MASK & ~unalt
    out["seeded"] = 1
    poisoned = False
    for r in reversed(blk["ins"][:-1]):
        # 1. zap kill
        alive &= ~r["zap_reg"] & 0xFFFFFFFF
        # 2. result: N_REGISTER kill; N_INDEXED -> index NowAlive
        #    (regs-neutral); anything else -> bit channels only
        res, rm = r["result"], _cls(r["res_meta"])
        if res and rm == N_REGISTER:
            enc = r["res_reg"] if direct else _enc(res)
            if enc is None:
                poisoned = True
            else:
                alive &= ~enc & 0xFFFFFFFF
        elif res and rm == N_INDEXED and direct and r.get("res_reg"):
            # N_INDEXED result: the INDEX goes NowAlive (v48 res_reg
            # resolves through the indexed name -- an N_REGISTER index,
            # e.g. the lea-edi side of a struct-copy MOV)
            alive |= r["res_reg"]
        # 3. operands NowAlive (with the x-op-x skip; OW skips ALL
        #    operands there -- including the 2..N tail)
        skip_ops = (r["opcode"] in XOPX_SKIP and r["op0"] == r["op1"]
                    and r["op0"] and _cls(r["op1_meta"]) == N_REGISTER)
        if not skip_ops and r["opcode"] != OP_BLOCK:
            for op, meta, dr in ((r["op0"], r["op0_meta"], r.get("op0_reg")),
                                 (r["op1"], r["op1_meta"], r.get("op1_reg"))):
                c = _cls(meta)
                if op and c == N_REGISTER:
                    enc = dr if direct else _enc(op)
                    if enc is None:
                        poisoned = True
                    else:
                        alive |= _promote(enc)
                elif op and c == N_INDEXED and direct and dr:
                    alive |= dr                 # index NowAlive (N_REGISTER idx)
            if direct and r.get("xtra_regs"):
                alive |= r["xtra_regs"]         # operands[2..N-1] (CALL parms)
        # 4. compare the stored value
        if poisoned:
            out["skipped_unres"] += 1
            continue
        out["rows"] += 1
        pred = (alive | unalt) & GP_MASK
        if pred == (r["live_regs"] & GP_MASK):
            out["exact"] += 1
        elif len(out["misses"]) < 4:
            out["misses"].append({"ins": r["ins"], "op": r["opcode"],
                                  "pred": hex(pred),
                                  "rec": hex(r["live_regs"] & GP_MASK)})
    return out


def tu_regmap(td_by_func: dict) -> dict:
    """TU-global register-name ptr -> hw_reg_set map (fallback for names
    the routine's own gi walks never sighted; the AllocRegName cache is
    per-compile, so canonical register-name ptrs are stable TU-wide)."""
    m: dict = {}
    for rt in td_by_func.values():
        m.update(routine_regmap(rt))
    return m


def certify_routine(rt: dict, fallback: dict | None = None) -> dict:
    """Run certify_block over the routine's first IL snapshot."""
    tot = {"rows": 0, "exact": 0, "skipped_unres": 0, "blocks": 0,
           "seeded": 0, "misses": []}
    walks = rt.get("il_walks") or []
    if not walks:
        return tot
    regmap = routine_regmap(rt)
    unalt = routine_unalterable(rt)
    for b in walks[0]["blocks"]:
        if not b["ins"]:
            continue
        tot["blocks"] += 1
        r = certify_block(b, regmap, unalt, fallback)
        for k in ("rows", "exact", "skipped_unres"):
            tot[k] += r[k]
        tot["seeded"] += r.get("seeded", 0)
        tot["misses"].extend(r["misses"][:2])
    return tot
