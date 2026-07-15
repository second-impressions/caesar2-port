"""Realization rule (capture item 4): `inc` vs `lea` (in-place vs fresh)
for IL ADD, decided at ENCODING time by FINAL REGISTER IDENTITY.

Corpus gate 2026-07-10 (pcsound+map+battle, byte-exact functions only,
IL opcode 1 events whose emitted first byte is 0x40-0x47 inc r32 or 0x8d
lea):

* register-level rule ``in-place  <=>  final(result reg) == final(op reg)``:
  **50/51 = 98.0%** with the per-routine register-name map learned from
  gi walks (one attribution anomaly: set_db_sound +0x57 maps EAX/EDX ge
  operands to an emitted `inc ecx` -- a post-ge rewrite or ge-offset
  attribution slip; documented, not modeled away).
* IL-NAME identity is only a 93.9% proxy: two IL names can coalesce into
  one register (`inc ecx` from result != op0) and one memory-homed name
  can realize as `lea eax,[edx+1]` via two DIFFERENT rover picks
  (result==op0 pointer-equal!).  15/66 events had a memory-homed side:
  those are ROVER-realized -- the pick is the lw/FindRegister machinery's
  domain (`c2 spell`, c2.regalloc.lwalk), not the allocator's.

Consequence for the start_samples class: `lea ebx,[eax+1]` vs `inc eax`
is DOWNSTREAM of seats -- PS's form proves the `x+1` value's final
register differs from the source value's, i.e. the allocator (or rover)
gave them different homes.  Fix the seat; the realization follows.
"""
from __future__ import annotations


def routine_regmap(rt: dict) -> dict:
    """Learn the canonical register-name ptr -> hw_reg_set map from the
    routine's own gi walks (per-routine: name slabs are free-list reused
    across routines, so a global map is poisoned)."""
    regmap: dict = {}
    for a in rt.get("alloc") or []:
        for i in a.get("own_walk") or []:
            for p, r in ((i["result"], i["result_reg"]),
                         (i["op0"], i["op0_reg"]),
                         (i["op1"], i["op1_reg"])):
                if p and r:
                    regmap[p] = r
    return regmap


def add_form(rt: dict, ev: dict) -> str:
    """Predict the realization of an IL ADD cgen event: 'inplace' (inc /
    add-in-place), 'fresh' (lea / mov+op), or 'rover' (memory-homed side;
    the scratch picker decides -- consult the lw records)."""
    regmap = routine_regmap(rt)
    r1 = regmap.get(ev.get("result"))
    r0 = regmap.get(ev.get("op0"))
    if r1 is None or r0 is None:
        return "rover"
    return "inplace" if r1 == r0 else "fresh"
