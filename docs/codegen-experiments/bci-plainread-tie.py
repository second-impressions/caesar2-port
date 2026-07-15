"""build_city_item — flip the sav=12 ConfBefore tie from the PLAIN-read base.

Base state (working tree): the fountain arm is PS-faithful
(`i = 0xdb;` then `fountain_gfx = fountain_gfxdat[0];` — plain read,
fused zext `xor edx,edx; mov dl,[mem]` matching PS L992), and the
0x1c/md==4 arm uses PS's `-d1` statement order `dx = 0; dy = -4;`.

The old `& 0xff` mask spelling created a DL byte temp at that line
whose ONLY queue effect (regtrace-proven, /tmp/regtrace-{mask,plain})
was flipping the sav=12 tie order:
    mask : gfx_a, gfx_b, dx, dy   -> ESI, EDI, EBP, spill  (= PS)
    plain: gfx_a, dx, dy, gfx_b   -> ESI, EDI, EBP, spill  (33 islands)
But the mask kills the fused zext (PS-only `xor edx,edx` vs RC-only
`and edx,0xff`), so byte-exact is unreachable WITH it.  Goal: recover
the mask's tie order without the mask.  A serial 24-perm sweep of the
four tied decls (2026-07-07) found nothing below 759bd — this feeds
the wider pool (cross-decl swaps + per-arm statement order + fountain
variants) at depth 2.
"""
import re
from itertools import permutations

from c2.forge import Forge, TextEdit

forge = Forge("build_city_item", file="action.c")
src = forge.text
fn_start = src.index("void build_city_item(void)")

# ---- 1. full perm sweep of the four tied locals over their slots ----
TIE = ["dx", "dy", "gfx_b", "gfx_a"]
CUR = """    int dx;
    unsigned int i;
    int dy;
    int gfx_b;
    int gfx_b_idx;
    int gfx_a;
"""
a = src.index(CUR, fn_start)
b = a + len(CUR)

def block_for(p):
    return (f"    int {p[0]};\n    unsigned int i;\n    int {p[1]};\n"
            f"    int {p[2]};\n    int gfx_b_idx;\n    int {p[3]};\n")

assert block_for(("dx", "dy", "gfx_b", "gfx_a")) == CUR
for perm in permutations(TIE):
    if list(perm) == TIE:
        continue
    forge.candidate("declperm_" + "-".join(perm),
                    TextEdit(start=a, end=b, replacement=block_for(perm)))

# ---- 2. cross-decl swaps: tied member <-> non-cluster local ----
for x in TIE:
    for y in ["gfx_a_idx", "tgfx_a", "tgfx_b", "fountain_gfx", "i",
              "gfx_b_idx", "ok", "shape", "cover_gfx", "warned"]:
        forge.swap_decls(x, y)

# ---- 3. per-arm statement-order swaps (conflict-creation order) ----
for m in re.finditer(r"gfx_a = (\w+); gfx_b = (\w+);", src):
    line = src[:m.start()].count("\n") + 1
    forge.replace_line(line, f"            gfx_b = {m.group(2)}; gfx_a = {m.group(1)};")
for m in re.finditer(r"gfx_a_idx = (\w+); gfx_b_idx = (\w+);", src):
    line = src[:m.start()].count("\n") + 1
    forge.replace_line(line, f"            gfx_b_idx = {m.group(2)}; gfx_a_idx = {m.group(1)};")
for m in re.finditer(r"dx = (-?\w+); dy = (-?\w+);", src):
    line = src[:m.start()].count("\n") + 1
    forge.replace_line(line, f"            dy = {m.group(2)}; dx = {m.group(1)};")

# ---- 4. fountain-arm variants ----
fl = src.index("fountain_gfx = fountain_gfxdat[0];", fn_start)
fline = src[:fl].count("\n") + 1
forge.replace_line(fline, "        fountain_gfx = fountain_gfxdat[0] & 0xff;")
# swap i = 0xdb; <-> fountain read (back to fountain-first)
forge.swap_statements(line_a=fline - 1, line_b=fline)
