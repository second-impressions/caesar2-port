# try_this_regionmap_square: inline masks -> L1847 temp ROTATION right,
# slots wrong (3-cycle); all-named -> slots right (decl-order), rotation
# wrong (6b).  Enumerate MIXED subsets: name k of the 4 masks (uchar +
# (int)-cast tests), inline the rest, x decl-orders of named+base_kind.
from itertools import combinations, permutations

from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")
fn_end = src.index("int try_a_seamap_square(", fn_start)
body = src[fn_start:fn_end]

MASKS = ["terr_bit_2", "terr_bit_20", "terr_bit_4", "terr_bit_1"]
EXPR = {"terr_bit_2": "terrain & 2", "terr_bit_20": "terrain & 0x20",
        "terr_bit_4": "terrain & 4", "terr_bit_1": "terrain & 1"}
DECL = {m: f"    unsigned char {m};" for m in MASKS}
DECL["base_kind"] = "    unsigned char base_kind;"
ASG = {"terr_bit_2": "    terr_bit_2  = terrain & 2;",
       "terr_bit_20": "    terr_bit_20 = terrain & 0x20;",
       "terr_bit_4": "    terr_bit_4  = terrain & 4;",
       "terr_bit_1": "    terr_bit_1  = terrain & 1;"}

CUR_DECLS = ("    unsigned char terr_bit_2;\n"
             "    unsigned char terr_bit_4;\n"
             "    unsigned char terr_bit_1;\n"
             "    unsigned char terr_bit_20;\n"
             "    unsigned char base_kind;")
CUR_ASGS = ("    terr_bit_2  = terrain & 2;\n"
            "    terr_bit_20 = terrain & 0x20;\n"
            "    terr_bit_4  = terrain & 4;\n"
            "    terr_bit_1  = terrain & 1;\n")
assert CUR_DECLS in body and CUR_ASGS in body


def make_body(named, decl_order):
    b = body
    # decls: permuted named decls (+ base_kind), drop unnamed
    b = b.replace(CUR_DECLS, "\n".join(DECL[v] for v in decl_order))
    # assignments: keep source order of the named ones only
    keep = [ASG[m] for m in MASKS if m in named]
    b = b.replace(CUR_ASGS, ("\n".join(keep) + "\n") if keep else "")
    # tests: named keep (int) cast; unnamed -> inline expr
    for m in MASKS:
        if m not in named:
            b = b.replace(f"(int){m}", f"{EXPR[m]}")
    return b


seen = 0
for k in range(0, 5):
    for named in combinations(MASKS, k):
        for decl_order in permutations(list(named) + ["base_kind"]):
            nb = make_body(named, list(decl_order))
            if nb == body:
                continue
            name = "N" + ("-".join(m.replace("terr_bit_", "b") for m in named) or "none") \
                   + "_D" + "-".join(v.replace("terr_bit_", "b") for v in decl_order)
            forge.candidate(name, TextEdit(start=fn_start, end=fn_end, replacement=nb))
            seen += 1
print(f"{seen} variants")
