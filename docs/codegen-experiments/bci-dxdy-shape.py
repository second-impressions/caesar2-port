"""build_city_item — flip the dx/dy reg-vs-spill chirality + the shape spill.

PS map (from the ledger/slot survey): gfx_a=EBP, gfx_b=EDI,
gfx_a_idx=[esp+0xc], gfx_b_idx=[esp+0x10], dx=ESI, dy=[esp+0x14],
shape=[esp+4]  (frame 0x18, 6 slots).
RC map: gfx_a=EDI, gfx_b=ESI, gfx_a_idx=[esp+0xc], gfx_b_idx=[esp+4],
dx=[esp+0x10], dy=EBP, shape=reg  (frame 0x14, 5 slots).

Two coupled flips: (a) dx wins the register / dy spills (equal-savings
reverse-last-use tie); (b) shape gets evicted to memory.  Singles and
pairs were exhausted by `forge climb`; this experiment feeds a focused
candidate pool (decl swaps among the cluster + per-arm statement swaps
+ dx/dy assignment-order swaps) and runs depth 3.
"""
from c2.forge import Forge

forge = Forge("build_city_item", file="action.c")

# decl-order swaps inside the tied cluster (Rule 115)
for a, b in [("dx", "dy"), ("shape", "gfx_b"), ("shape", "gfx_a"),
             ("shape", "i"), ("gfx_a_idx", "gfx_b_idx"),
             ("dy", "gfx_b_idx"), ("dx", "gfx_a_idx"), ("ok", "gfx_a_idx"),
             ("shape", "ok")]:
    try:
        forge.swap_decls(a, b)
    except KeyError:
        pass

# per-arm 'dx = K; dy = K;' -> 'dy = K; dx = K;' order swaps
# (moves the last-use / conflict-creation rank)
import re
src = open("decomp/src/action.c").read()
for m in re.finditer(r"dx = (-?\w+); dy = (-?\w+);", src):
    line = src[:m.start()].count("\n") + 1
    forge.replace_line(line, f"            dy = {m.group(2)}; dx = {m.group(1)};")

# 'gfx_a_idx = K; gfx_b_idx = K;' order swaps
for m in re.finditer(r"gfx_a_idx = (\w+); gfx_b_idx = (\w+);", src):
    line = src[:m.start()].count("\n") + 1
    forge.replace_line(line, f"            gfx_b_idx = {m.group(2)}; gfx_a_idx = {m.group(1)};")

# 'gfx_a = K; gfx_b = K;' order swaps
for m in re.finditer(r"gfx_a = (\w+); gfx_b = (\w+);", src):
    line = src[:m.start()].count("\n") + 1
    forge.replace_line(line, f"            gfx_b = {m.group(2)}; gfx_a = {m.group(1)};")
