# city_test_for_road: `register` storage-class probes.  The x<->y param
# seat tie is decided by conflict-creation order; `register` hints can
# reroute a name through a different conflict-creation path (usage
# flags / RoughSortTemps walk) without changing the emitted code.
from itertools import combinations

from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")

DECLS = {
    "forbidden": "    signed char forbidden;",
    "rand_dir": "    signed char rand_dir;",
    "i": "    int i;",
    "n_present": "    int n_present;",
    "n_empty": "    int n_empty;",
}
for k, txt in DECLS.items():
    a = src.index(txt, fn_start)
    forge.candidate(f"reg_{k}", TextEdit(start=a, end=a + len(txt),
                                         replacement="    register" + txt[3:]))

# register on params (ANSI allows storage class in param decls)
SIG = "int city_test_for_road(int x, int y, int map_ref, int world_dir)"
a = src.index(SIG, fn_start)
forge.candidate("reg_param_x", TextEdit(start=a, end=a + len(SIG),
    replacement="int city_test_for_road(register int x, int y, int map_ref, int world_dir)"))
forge.candidate("reg_param_y", TextEdit(start=a, end=a + len(SIG),
    replacement="int city_test_for_road(int x, register int y, int map_ref, int world_dir)"))
forge.candidate("reg_param_xy", TextEdit(start=a, end=a + len(SIG),
    replacement="int city_test_for_road(register int x, register int y, int map_ref, int world_dir)"))
forge.candidate("reg_param_wd", TextEdit(start=a, end=a + len(SIG),
    replacement="int city_test_for_road(int x, int y, int map_ref, register int world_dir)"))
