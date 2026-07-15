#!/usr/bin/env python3
"""WATCOM 10.0a wcc386 register-savings cost model, decoded from the binary.

The savings cost tables (`Save` struct, link 0x80468, runtime-filled BSS) are
NOT static constants -- `CostInit` (0x48913) computes them at startup from the
optimisation size% and the target CPU level. Decoded verbatim from wcc386.exe:

  AdjTimeSize (0x59828):
      size = 256 if size% > 100 else size% * 256 // 100      # TOTAL_WEIGHT=256
      time = 256 - size

  SetLoopCost (0x5985c):                                     # LOOP_FACTOR=20
      base = (20 * time) // 256   (clamped to >= 1)
      loop_weight[i] = base ** i  for i in 0..5              # MAX_LOOP=5

  CostInit (0x48913) per-category costs (SetCost fills all 11 type slots with
  one value; index_save = load_cost). Three CPU-level paths ([0x7f908] & 0xf):

      level >= 4 (486/Pentium):
          load = store = (3*size + time)//256
          use = def = push = pop = (size + time)//256
      level == 3 (386):
          load = (4*time + 3*size)//256 ;  store = (2*time + 3*size)//256
          use = def = push = (2*time + size)//256 ; pop = (4*time + size)//256
      level <  3 (8086/186/286):
          load = (17*time + 3*size)//256 ; store = (18*time + 3*size)//256
          use  = (15*time + size)//256   ; def   = (18*time + size)//256
          push = (11*time + size)//256   ; pop   = (8*time  + size)//256
      index_save = load (all paths)

`Weight(value, blk) = value * loop_weight[min(blk.depth, 5)]` and
`CalcSavings` accumulates per-block `save - cost` weighted by `Weight`.

Optimisation flags -> size%:  default (no -ot/-os) = 50 (balanced, time=size=128);
-ot = 0 (time=256); -os = 100 (time=0).  CPU flag -3/-4/-5 -> cpu_level 3/4/5.

VERIFIED against the running compiler (Rung-2 cost dump, tools/patch_trace.py
`cost`/`lwt` records) for every combo below -- formula == observed exactly:
  -3 -ot : load=4 store=2 use=def=push=2 pop=4   base=20
  -4/-5 -ot: all costs 1                          base=20
  -3 -os : load=store=3 use=def=push=pop=1        base=1  (no loop weighting)
  -3     : load=3 store=2 use=def=push=1 pop=2     base=10
  -4     : load=store=2 use=def=push=pop=1         base=10

So caesar2's "use=def=1, load=store=2, W=10" is the **-4 (or -5) default**
(balanced) build -- not -3, which gives load=3.
"""
from __future__ import annotations

TOTAL_WEIGHT = 256
LOOP_FACTOR = 20
MAX_LOOP = 5


def time_size(size_pct: int):
    """AdjTimeSize: percentage -> (time, size) in 0..256 with time+size=256."""
    size = TOTAL_WEIGHT if size_pct > 100 else size_pct * TOTAL_WEIGHT // 100
    return TOTAL_WEIGHT - size, size


def loop_weights(time: int):
    """SetLoopCost: loop_weight[0..MAX_LOOP] = base**i, base=(20*time)//256 (>=1)."""
    base = (LOOP_FACTOR * time) // TOTAL_WEIGHT or 1
    return [base ** i for i in range(MAX_LOOP + 1)]


def costs(size_pct: int = 50, cpu_level: int = 4):
    """Return the per-category Save costs + loop_weight for an opt config."""
    time, size = time_size(size_pct)
    d = lambda x: x // TOTAL_WEIGHT
    if cpu_level >= 4:
        load = store = d(3 * size + time)
        use = deff = push = pop = d(size + time)
    elif cpu_level == 3:
        load = d(4 * time + 3 * size)
        store = d(2 * time + 3 * size)
        use = deff = push = d(2 * time + size)
        pop = d(4 * time + size)
    else:
        load = d(17 * time + 3 * size)
        store = d(18 * time + 3 * size)
        use = d(15 * time + size)
        deff = d(18 * time + size)
        push = d(11 * time + size)
        pop = d(8 * time + size)
    return {
        "time": time, "size": size,
        "index_save": load, "load_cost": load, "store_cost": store,
        "use_save": use, "def_save": deff, "push_cost": push, "pop_cost": pop,
        "loop_weight": loop_weights(time),
    }


def weight(value: int, depth: int, loop_weight) -> int:
    return value * loop_weight[min(depth, MAX_LOOP)]


def from_flags(cpu: int = 4, ot: bool = False, os_: bool = False):
    """Costs for wcc386 flags: cpu in {3,4,5}; ot=-ot, os_=-os, neither=balanced."""
    size_pct = 0 if ot else (100 if os_ else 50)
    return costs(size_pct=size_pct, cpu_level=cpu)


if __name__ == "__main__":
    c = costs(size_pct=50, cpu_level=4)
    print("balanced 486+ (size%=50):")
    for k, v in c.items():
        print(f"  {k:11s} = {v}")
    assert c["use_save"] == c["def_save"] == 1
    assert c["load_cost"] == c["store_cost"] == c["index_save"] == 2
    assert c["loop_weight"] == [1, 10, 100, 1000, 10000, 100000]
    print("matches caesar2 behavioural model (W=10) -- OK")
