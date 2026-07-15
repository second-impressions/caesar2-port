# city_test_for_road: 6b x<->y PARAM callee-save seat tie (EDI/EBP),
# regalloc_pure (149/149 register-blind).  The instruction stream is
# pinned, so only instruction-NEUTRAL levers can flip the ConfBefore
# tie: the LOCALS' declaration order (Rule 115 -- name-pointer /
# allocation-order shifts).  Exhaustive 720-perm sweep of the six
# local decls.
from itertools import permutations

from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)")

DECL = {
    "slots": "    unsigned char slots[8][3];",
    "forbidden": "    signed char forbidden;",
    "rand_dir": "    signed char rand_dir;",
    "i": "    int i;",
    "n_present": "    int n_present;",
    "n_empty": "    int n_empty;",
}
ORDER = ["slots", "forbidden", "rand_dir", "i", "n_present", "n_empty"]
CUR = "\n".join(DECL[v] for v in ORDER)
a = src.index(CUR, fn_start)
b = a + len(CUR)

for perm in permutations(ORDER):
    if list(perm) == ORDER:
        continue
    forge.candidate("d_" + "-".join(p[:4] for p in perm),
                    TextEdit(start=a, end=b, replacement="\n".join(DECL[v] for v in perm)))
