# try_this_regionmap_square: final 6 bytes = anon index-temp pair
# rotation, tie broken by the ConfBefore NAME-POINTER (allocation
# order).  Extra/dead named locals shift every later temp's heap slot.
# The pre-climb source had dead `other_no` / `route` decls -- probe
# re-adding them (and other dummies) at each decl position.
from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")

anchor = "    int i;\n"
a = src.index(anchor, fn_start)
DUMMIES = {
    "other_no": "    int other_no;\n",
    "route": "    struct army_route_rec *route;\n",
    "both": "    int other_no;\n    struct army_route_rec *route;\n",
    "int_pair": "    int dead_a;\n    int dead_b;\n",
    "uch": "    unsigned char dead_c;\n",
}
for name, txt in DUMMIES.items():
    # after `int i;`
    forge.candidate(f"after_i_{name}", TextEdit(start=a + len(anchor), end=a + len(anchor), replacement=txt))
    # before `int i;`
    forge.candidate(f"before_i_{name}", TextEdit(start=a, end=a, replacement=txt))

# and at the very top of the decl block
top = "    unsigned char terrain;\n"
t = src.index(top, fn_start)
for name, txt in DUMMIES.items():
    forge.candidate(f"top_{name}", TextEdit(start=t, end=t, replacement=txt))
