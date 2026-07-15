"""optimiser-folding-idioms -- catalogue of C constructs that DO vs DO NOT
bump a value's regalloc savings under Watcom 10.0a `-bt=dos -mf -4r -s -d1`.

THE PROBLEM (from docs/hard-bucket-survey-2026-06-24.md):
Every HARD-bucket residue class has a named lever of the form
"ADD ~N depth-D uses of value X" or "lower sav(X) by N", but the
ACTION verb hides a search: WHICH C construct bumps savings by the
required amount without (a) getting folded by the optimiser, (b)
changing semantics, (c) cascading into other diffs.

This experiment establishes the empirical baseline: for each idiom,
measure the byte delta + observe whether the use lands in the al/nb1
trace records (= bumped savings) or vanishes (= folded).

Read the table below FIRST, then for any idiom whose contribution is
uncertain re-run with `c2 cgex run optimiser-folding-idioms -t <name>`
and inspect the per-trial asm + trace.

THE BASELINE (`baseline`): a function with a single dword value `x`
loaded from a global, NOT used post-call -- savings should be ~minimal
for x.  Each subsequent trial INSERTS one candidate idiom referencing
x and compares the trace's sav for x against baseline.

THE CATEGORIES:

  FOLDED -- compiler drops the construct entirely; no IL ref to x
    survives, no savings bump.  Useless as a source lever.
  PARTIAL -- generates 1-2 IL refs (small bump); useful for fine
    nudges.
  HEAVY -- generates many IL refs or in-loop expansion (big bump);
    useful for callee-save promotions.

  uv run c2 cgex run optimiser-folding-idioms
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="optimiser-folding-idioms",
    chk=False,
    externs={
        "ext":   "extern int  ext(int x);",
        "ext2":  "extern void ext2(int a, int b);",
    },
)

# --- BASELINE -----------------------------------------------------
# `x` defined, loaded from gx, NOT used post-load -> no spill, no use.
exp.add(
    "baseline",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    ext(0);
    return gy;
}
""",
    note="baseline -- x loaded but never used; al should show x with savings 0",
)

# --- FOLDED IDIOMS (provably dropped) ----------------------------

exp.add(
    "void_cast",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    (void)x;           /* folded: void cast generates no IL */
    ext(0);
    return gy;
}
""",
    note="FOLDED -- `(void)x;` produces no IL ref; same bytes as baseline",
)

exp.add(
    "mul_zero",
    """
int gx, gy;
int f(void) {
    int x, t;
    x = gx;
    t = x * 0;          /* folded: x*0 -> constant 0 */
    ext(t);
    return gy;
}
""",
    note="FOLDED -- x*0 folded to 0 before regalloc; no x reference",
)

exp.add(
    "dead_assignment_via_self",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    gy = gy;            /* tautological self-assign -- may be folded */
    ext(0);
    return gy;
}
""",
    note="FOLDED -- tautological self-assignment; no x reference at all",
)

exp.add(
    "if_dead_body",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    if (x < 0) { gy = gy; }   /* tested but body folded */
    ext(0);
    return gy;
}
""",
    note="PARTIAL -- the test on x survives as cmp+jcc even with empty body",
)

# --- PARTIAL IDIOMS (small savings bump) -------------------------

exp.add(
    "if_guard_return",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    if (x < 0) return -1;     /* test + jcc + return-setup */
    ext(0);
    return gy;
}
""",
    note="PARTIAL/HEAVY -- guard with early return; generates real x reads + jcc + epilogue",
)

exp.add(
    "store_x_to_global",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    gy = x;             /* explicit store -- can't be dropped */
    ext(0);
    return gy;
}
""",
    note="PARTIAL -- store x to global; mov ref to x survives",
)

exp.add(
    "ext_call_with_x",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    ext(x);             /* x passed as call arg */
    return gy;
}
""",
    note="PARTIAL -- x as call arg; one IL ref for the mov to arg reg",
)

exp.add(
    "cmp_x_use_in_branch",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    if (x > 0) gy++;    /* x tested; gy bumped on true */
    ext(0);
    return gy;
}
""",
    note="PARTIAL -- cmp x; jcc; conditional store -- 2-3 IL refs for x",
)

# --- HEAVY IDIOMS (large savings bump, esp. via loop weight) -----

exp.add(
    "in_loop_store",
    """
int gx, gy, gz[10];
int f(void) {
    int x, i;
    x = gx;
    ext(0);
    for (i = 0; i < 10; i++) gz[i] = x;   /* x stored every iter */
    return gy;
}
""",
    note="HEAVY -- in-loop use weighted by W=10; one in-loop ref >> any depth-0 idiom",
)

exp.add(
    "in_loop_guard",
    """
int gx, gy, gz[10];
int f(void) {
    int x, i;
    x = gx;
    ext(0);
    for (i = 0; i < 10; i++) {
        if (gz[i] == x) gy++;   /* x compared every iter */
    }
    return gy;
}
""",
    note="HEAVY -- in-loop cmp + branch; multiple weighted IL refs to x",
)

exp.add(
    "in_loop_arith",
    """
int gx, gy, gz[10];
int f(void) {
    int x, i, s;
    x = gx;
    ext(0);
    s = 0;
    for (i = 0; i < 10; i++) s += gz[i] * x;    /* x in arith every iter */
    return s;
}
""",
    note="HEAVY -- arith with x inside loop; many IL refs at depth-1",
)

# --- SEMANTIC-NEUTRAL SLOT BUMPS (don't change function output) --
# These are EDIT CANDIDATES for the HARD-bucket source levers --
# they bump a specific value's savings without altering the function's
# observable behavior.

exp.add(
    "x_redundant_store",
    """
int gx, gy;
int f(void) {
    int x;
    x = gx;
    gy = x;             /* writes value */
    gy = x;             /* re-write same value -- semantically redundant */
    ext(0);
    return gy;
}
""",
    note="PARTIAL -- repeated store of x -- second store may be DSE'd or kept",
)

exp.add(
    "x_via_volatile_temp",
    """
int gx, gy;
int f(void) {
    int x;
    volatile int t;
    x = gx;
    t = x;              /* volatile prevents DSE */
    ext(0);
    return gy;
}
""",
    note="PARTIAL -- volatile local forces the store; bumps x save by ~1",
)
