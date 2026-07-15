# city_test_for_road x<->y seat tie.  H2 mechanism (confirmed by reading
# dataflo.c AllocBefore + regalloc.c ConfBefore): x/y both have conflicts
# with EQUAL savings=4, so ConfBefore is sort-equal and the id tiebreak
# NEVER fires -- their order is the UNSTABLE ShellSort over the whole
# ConfList (creation = reverse-last-use + prepend).  => a byte-NEUTRAL
# perturbation of an UNRELATED conflict (type/register-class change on
# another local) can drag x ahead of y through the gap-passes WITHOUT
# touching x/y.  forge's type_sweep has a width-guard (6364356f) that may
# gate out a seat-flipping type edit -- probe them directly, read seat.
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.text
fn = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")


def repl(name, old, new):
    a = src.index(old, fn)
    forge.candidate(name, TextEdit(a, a + len(old), new))


# ── type changes on the int locals (register-class perturbation) ──
INT_LOCALS = {
    "i": "    int i;",
    "n_present": "    int n_present;",
    "n_empty": "    int n_empty;",
}
ALTS = ["short", "unsigned short", "unsigned int", "long", "unsigned char", "char"]
for k, decl in INT_LOCALS.items():
    for t in ALTS:
        repl(f"{k}_{t.replace(' ', '')}", decl, f"    {t} {k};")

# ── type changes on the char locals (byte -> dword class) ──
CHAR_LOCALS = {
    "forbidden": "    signed char forbidden;",
    "rand_dir": "    signed char rand_dir;",
}
for k, decl in CHAR_LOCALS.items():
    for t in ["int", "unsigned char", "char", "short", "unsigned int"]:
        repl(f"{k}_{t.replace(' ', '')}", decl, f"    {t} {k};")

# ── slots type width (unsigned char[8][3]) alternatives ──
repl("slots_char", "    unsigned char slots[8][3];", "    char slots[8][3];")
repl("slots_flat24", "    unsigned char slots[8][3];", "    unsigned char slots[24];")

# ── decl-order permutations of the int locals among themselves ──
DECLS = (
    "    int i;\n"
    "    int n_present;\n"
    "    int n_empty;\n"
)
da = src.index(DECLS, fn)
import itertools
for perm in itertools.permutations(["i", "n_present", "n_empty"]):
    if list(perm) == ["i", "n_present", "n_empty"]:
        continue
    new = "".join(f"    int {p};\n" for p in perm)
    forge.candidate("declord_" + "_".join(perm), TextEdit(da, da + len(DECLS), new))

# ── move forbidden/rand_dir among the decls (slot-set perturbation) ──
# put forbidden AFTER the int locals
FULL = (
    "    unsigned char slots[8][3];\n"
    "    signed char forbidden;\n"
    "    signed char rand_dir;\n"
    "    int i;\n"
    "    int n_present;\n"
    "    int n_empty;\n"
)
fa = src.index(FULL, fn)
forge.candidate("chars_last", TextEdit(fa, fa + len(FULL),
    "    unsigned char slots[8][3];\n"
    "    int i;\n"
    "    int n_present;\n"
    "    int n_empty;\n"
    "    signed char forbidden;\n"
    "    signed char rand_dir;\n"))
forge.candidate("chars_first", TextEdit(fa, fa + len(FULL),
    "    signed char forbidden;\n"
    "    signed char rand_dir;\n"
    "    unsigned char slots[8][3];\n"
    "    int i;\n"
    "    int n_present;\n"
    "    int n_empty;\n"))

with forge.session(jobs=12) as s:
    summary = s.run("each", stop_at_exact=True, max_variants=200)

base = summary.baseline
print(f"\nBASELINE  bytes={base.bytes}  layers(ir,isl,w,sp,seat)={base.layers}")
print(f"{'candidate':26s} {'bytes':>6} {'seat':>5}  layers")
print("-" * 70)
for p in sorted(summary.plans, key=lambda p: (p.score.layers[4], p.score.bytes)):
    lay = p.score.layers
    flag = ""
    if lay[4] < base.layers[4]:
        flag = "  <== SEAT FLIP"
    if p.score.bytes == 0:
        flag = "  <== BYTE EXACT"
    print(f"{p.plan.name:26s} {p.score.bytes:>6} {lay[4]:>5}  {lay}{flag}")
