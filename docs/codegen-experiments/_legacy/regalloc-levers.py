"""Regalloc-lever probe — test community-established source-level
levers against Watcom 10.0a to see which actually move codegen.

Background: prior-art survey (OoT, SotN, decomp-permuter, Devilution)
documents a standard list of source-level mutations used to nudge
register allocation in matching decomp.  Many translate to existing
numbered rules in `docs/watcom-codegen-patterns.md`; a handful do
not.  This experiment probes the gaps with synthetic micro-functions.

We don't need a PS reference here — we just compare every trial
against trial `baseline` to see if the mutation alters bytes.  If
yes, it's a real lever; if no, it's a no-op under Watcom 10.0a and
should not be added as a rule.

Gaps under test
---------------
A.  `if (c)` vs `if (c != 0)` — does Watcom emit an extra `test`/`mov`?
B.  Statement separators (`,` vs `;` vs same line) — does whitespace
    affect codegen?  (IDO is sensitive; Watcom may not be.)
C.  Loop-header multi-init `for (i=0, x=4; …)` vs separate init —
    does folding into the prologue change regalloc?
D.  Expression duplication for CSE — when two reads of a global are
    written once vs twice, does the dedup pass change allocator order?
E.  `a = b + c` vs `a = b; a += c` — does splitting bias `a` into a
    callee-save register?
F.  `static` qualifier on an intra-TU helper — does it change call-
    site codegen the way SotN reports for PSP-MIPS?

Run::

    uv run c2 cgex run regalloc-levers
"""

from c2.commands.cgex import Experiment


# We use synthetic functions, not a real PS function, so we compare
# trials against one of our own (`baseline`).
exp = Experiment(
    name="regalloc-levers",
    ps_function=None,
    chk=False,
    extra_defs="""
extern int g_x;
extern int g_y;
extern int g_z;
extern int sink(int);
""",
)


# ───────── Lever A: `if (c)` vs `if (c != 0)` ─────────
exp.add("A_bare", """
int testA(int c, int x, int y) {
    int r;
    if (c) { r = x; } else { r = y; }
    return sink(r);
}
""", note="A: bare `if (c)`")

exp.add("A_nonzero", """
int testA(int c, int x, int y) {
    int r;
    if (c != 0) { r = x; } else { r = y; }
    return sink(r);
}
""", note="A: `if (c != 0)`")


# ───────── Lever B: statement separator (, vs ;) ─────────
exp.add("B_semi", """
int testB(int x, int y) {
    int a;
    int b;
    a = x + 1;
    b = y + 2;
    return sink(a + b);
}
""", note="B: separate `;` statements")

exp.add("B_comma", """
int testB(int x, int y) {
    int a;
    int b;
    a = x + 1, b = y + 2;
    return sink(a + b);
}
""", note="B: `,`-joined")

exp.add("B_sameline", """
int testB(int x, int y) {
    int a;
    int b;
    a = x + 1; b = y + 2;
    return sink(a + b);
}
""", note="B: same-line `;`")


# ───────── Lever C: loop multi-init ─────────
exp.add("C_separate", """
int testC(int n) {
    int i;
    int sum;
    int step;
    sum = 0;
    step = 4;
    for (i = 0; i < n; i++) {
        sum += i * step;
    }
    return sum;
}
""", note="C: separate sum/step init")

exp.add("C_multi", """
int testC(int n) {
    int i;
    int sum;
    int step;
    for (i = 0, sum = 0, step = 4; i < n; i++) {
        sum += i * step;
    }
    return sum;
}
""", note="C: for-header multi-init")


# ───────── Lever D: duplicate-for-CSE ─────────
exp.add("D_temp", """
int testD(int x) {
    int t;
    t = g_x * x;
    return t + t;
}
""", note="D: single temp")

exp.add("D_inline", """
int testD(int x) {
    return (g_x * x) + (g_x * x);
}
""", note="D: duplicated inline; CSE should dedup")


# ───────── Lever E: split arithmetic to bias callee-save ─────────
exp.add("E_fused", """
int testE(int x) {
    int a;
    a = g_x + x;
    sink(0);
    return a + g_y;
}
""", note="E: fused `a = b + c`")

exp.add("E_split", """
int testE(int x) {
    int a;
    a = g_x;
    a += x;
    sink(0);
    return a + g_y;
}
""", note="E: split `a = b; a += c`")


# ───────── Lever F: static vs non-static intra-TU helper ─────────
# Note: this only changes codegen if Watcom inlines static functions
# (it normally doesn't at our cflags), or if the call uses different
# ABI for static.  Both are unlikely; we test anyway.
exp.add("F_nonstatic", """
int helperF(int x, int y) { return x * y + 3; }
int testF(int a) { return helperF(a, a + 1); }
""", note="F: non-static helper")

exp.add("F_static", """
static int helperF(int x, int y) { return x * y + 3; }
int testF(int a) { return helperF(a, a + 1); }
""", note="F: static helper")
