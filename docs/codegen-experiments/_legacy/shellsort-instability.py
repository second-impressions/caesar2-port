"""shellsort-instability -- Watcom 10.0a's ShellSort (va 0x66689) is NOT
stable; equal-rank temps can end up reordered in the post-sort list.

THE FINDING (verified in the 10.0a binary + trace-validated offline
simulators, see docs/slot-swap-survey-2026-06-25.md and
docs/wcc386-re/regalloc-model.md canon 'The slot-assignment pipeline'):

The alloc sorts are ShellSort, via DoSortList @0x665c4.  DoSortList's
alloc-SUCCESS arm runs ShellSort @0x66689 (the decompile is explicit:
"Normal small conflict lists take the UNSTABLE ShellSort path"); only the
alloc-FAILURE arm falls back to the stable MergeList @0x66566 merge sort.
Normal lists take the unstable arm.  ShellSort's gap>1 bubble passes swap
elements that compare "before" (smaller) across a gap; equal-rank
elements (comparator returns FALSE both ways) are never directly swapped,
BUT a large-gap pass that compares a different-rank neighbour can drag an
element across a same-rank peer that a later smaller-gap pass then leaves
in the dragged position -- so post-sort order of equal-rank elements is
NOT the input order.

The two alloc comparators (decompiled from the binary):
  * SortCmp_flag2_2b @0x55503 (AssignTemps Names[N_TEMP] sort): ALIAS bit
    byte[+0x2b]&0x2 (alias-first) -> n.size [+0x8] (smaller-first) ->
    [+0x24]: if DIFFERENT the comparator returns FALSE both ways
    (sort-equal) -> [+0x10] v.offset DESCENDING (only when +0x24 is equal).
  * AllocBefore @0x5905b (BuildNameConflicts Names[N_TEMP] sort):
    CONST_TEMP bit byte[+0x2b]&0x1 (non-CONST-first) -> has-conflict
    (v.conflict [+0xc]) before no-conflict -> both-conflict: conflict savings
    DESC -> both-no-conflict: [+0x24] DESC.

[+0x24] is a per-temp id = reverse-declaration-rank, assigned by the
front-end at declaration time (nb1 = declaration order; the six byte
locals in evolve_water_table get +0x24 = 7,6,5,4,3,2 in reverse decl
order).  So same-size same-id-class temps almost always have DISTINCT
[+0x24] -> the AssignTemps comparator returns sort-equal for every pair
-> their final slot order is PURELY the ShellSort permutation of the
whole temp list, independent of their decl order.

THIS IS WHY DECL-ORDER IS NOT A SLOT LEVER: a decl reorder moves BOTH the
temp's nb1 position AND its +0x24 rank together (the rank is re-derived
from the new decl order), so the coupled perturbation is what the
non-stable sorts see -- it does not isolate the slot-index of one local.
(Proven, not guessed: 24/24 decl-order permutations of evolve_water_table's
four spilled locals all miss PS's target slot order.)

This experiment demonstrates the instability in isolation: with the stray
byte local absent the same-size dword pair keeps its input order; with it
present the pair's relative position can flip.  (The byte local here is
just a perturbation that changes the list shape; the same flip is also
reachable without any size-mixing -- what matters is any change that alters
which elements a gap-pass compares across.)
  uv run c2 cgex run shellsort-instability

The full offline simulators that reproduce the binary's sort exactly:
  c2/regalloc/shellsort_sim_slots.py  (AssignTemps sort: predict_nt_post;
    + BuildNameConflicts sort: predict_nb2)  -- validated 232/232 nt_post,
    441/456 nb2, 130/130 PS slot-order prediction on the byte-exact corpus.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="shellsort-instability",
    chk=False,
    externs={
        "ext":   "extern int  ext(int x);",
        "ext2":  "extern int  ext2(int a, int b, int c, int d, int e);",
    },
)

# Probe 1: TWO dword locals only -- both spill across the call.  The size
# both dword -- all same size.  A STABLE sort would keep source decl
# order; 10.0a's ShellSort is NOT stable, so the gap-passes can reorder
# equal-rank same-size temps -- the slot order can flip anyway.
exp.add(
    "without_byte_local",
    """
int g_a, g_b;

int f(void)
{
    int aaa;
    int bbb;
    aaa = g_a;
    bbb = g_b;
    ext2(0, 0, 0, 0, 0);   /* zap regs, forces aaa+bbb spill */
    return aaa + bbb;
}
""",
    note="no size=1 temp in nt; ShellSort stable; aaa/bbb keep source decl order in slots",
)

# Probe 2: SAME function but one char local exists.  The size=1 temp
# interleaves with the size=4 in nt; ShellSort's gap-walk hops it past
# the dword pair, perturbing aaa's vs bbb's relative order.
exp.add(
    "with_byte_local",
    """
int g_a, g_b;
char g_c;

int f(void)
{
    int aaa;
    int bbb;
    char ccc;
    aaa = g_a;
    bbb = g_b;
    ccc = g_c;
    g_c = ccc + 1;          /* keeps ccc as a real char temp */
    ext2(0, 0, 0, 0, 0);
    return aaa + bbb;
}
""",
    note="size=1 ccc in nt; ShellSort destabilises the aaa/bbb dword pair",
)
