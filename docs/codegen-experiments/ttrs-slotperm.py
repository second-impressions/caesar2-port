# try_this_regionmap_square: the last real divergence is the byte-temp
# SLOT permutation (&2/&0x20/&4/&1 masks + base_kind over [esp+0..0x10]).
# With the masks NAMED (uchar, (int)-cast tests to keep PS's zext-read
# test form), the slots become decl-order-steerable (Rule 115 / ShellSort
# nb2 rank).  Enumerate ALL 120 decl orders of the five byte locals.
from itertools import permutations

from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text

DECLS = {
    "terr_bit_2": "    unsigned char terr_bit_2;",
    "terr_bit_20": "    unsigned char terr_bit_20;",
    "terr_bit_4": "    unsigned char terr_bit_4;",
    "terr_bit_1": "    unsigned char terr_bit_1;",
    "base_kind": "    unsigned char base_kind;",
}
CUR = "\n".join(
    DECLS[v] for v in ["terr_bit_2", "terr_bit_20", "terr_bit_4", "terr_bit_1", "base_kind"]
)
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")
a = src.index(CUR, fn_start)
b = a + len(CUR)

for perm in permutations(DECLS):
    if list(perm) == ["terr_bit_2", "terr_bit_20", "terr_bit_4", "terr_bit_1", "base_kind"]:
        continue  # identity
    txt = "\n".join(DECLS[v] for v in perm)
    forge.candidate("decl_" + "_".join(p.replace("terr_bit_", "b") for p in perm),
                    TextEdit(start=a, end=b, replacement=txt))

# also: the four mask-ASSIGNMENT statement orders (first-assign, Rule 115b)
ASSIGNS = {
    "terr_bit_2": "    terr_bit_2  = terrain & 2;",
    "terr_bit_20": "    terr_bit_20 = terrain & 0x20;",
    "terr_bit_4": "    terr_bit_4  = terrain & 4;",
    "terr_bit_1": "    terr_bit_1  = terrain & 1;",
}
CURA = "\n".join(ASSIGNS[v] for v in ["terr_bit_2", "terr_bit_20", "terr_bit_4", "terr_bit_1"])
aa = src.index(CURA, fn_start)
ab = aa + len(CURA)
for perm in permutations(ASSIGNS):
    if list(perm) == ["terr_bit_2", "terr_bit_20", "terr_bit_4", "terr_bit_1"]:
        continue
    txt = "\n".join(ASSIGNS[v] for v in perm)
    forge.candidate("asg_" + "_".join(p.replace("terr_bit_", "b") for p in perm),
                    TextEdit(start=aa, end=ab, replacement=txt))
