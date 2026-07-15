"""build_city_item — endgame: 62bd, ir0/isl0, pure seats.

Two residues: (a) the placing_type==1 body ptr temp (PS EDX / RC EAX,
GB list-order all-scores-0 — an arena-order artifact) and (b) the
gfx_a/gfx_b/dx sav=12 tie rotation (PS: dx→ESI, gfx_b→EDI, gfx_a→EBP;
RC: gfx_b→ESI, gfx_a→EDI, dx→EBP).  Both moved under decl/arena
shuffles before (gfx_b<->cover_gfx swap was worth -601b).  Sweep the
whole pairwise decl-swap space + tie perms + ptr-local naming at the
==1 arm, depth 2.
"""
from itertools import combinations, permutations

from c2.forge import Forge, TextEdit

forge = Forge("build_city_item", file="action.c")
src = forge.text
fn_start = src.index("void build_city_item(void)")

NAMES = ["gfx_a_idx", "tgfx_a", "tgfx_b", "fountain_gfx", "dx", "i",
         "dy", "cover_gfx", "gfx_b_idx", "gfx_a", "ok", "shape",
         "gfx_b", "warned"]
for a, b in combinations(NAMES, 2):
    forge.swap_decls(a, b)

# tie-cluster full perms over the four slots (dx@slotA, dy@slotB,
# gfx_a@slotC, gfx_b@slotD in current decl block)
CUR = """    int dx;
    unsigned int i;
    int dy;
    unsigned int cover_gfx;
    int gfx_b_idx;
    int gfx_a;
    int ok;
    int shape;
    int gfx_b;
"""
a0 = src.index(CUR, fn_start)
b0 = a0 + len(CUR)

def block_for(p):
    return (f"    int {p[0]};\n    unsigned int i;\n    int {p[1]};\n"
            f"    unsigned int cover_gfx;\n    int gfx_b_idx;\n"
            f"    int {p[2]};\n    int ok;\n    int shape;\n    int {p[3]};\n")

assert block_for(("dx", "dy", "gfx_a", "gfx_b")) == CUR
for perm in permutations(["dx", "dy", "gfx_a", "gfx_b"]):
    if list(perm) == ["dx", "dy", "gfx_a", "gfx_b"]:
        continue
    forge.candidate("tieperm_" + "-".join(perm),
                    TextEdit(start=a0, end=b0, replacement=block_for(perm)))
