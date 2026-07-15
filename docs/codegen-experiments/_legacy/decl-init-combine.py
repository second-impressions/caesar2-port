"""decl-init-combine -- do these three source levers change codegen?

Hard regalloc residue is hypothesised to come from:
  1. declaration ORDER of locals                      (Rule 115 -- known)
  2. ORDER of first assignment                        (Rule 28a/use-order)
  3. combining declaration + first assignment into ONE statement
     (`int x = E;`) vs keeping them separate (`int x; ... x = E;`)
     -- UNVERIFIED: is the syntactic combine load-bearing on its own,
     i.e. at the SAME statement position, or only via where it forces
     the first assignment to land?

Contention setup: two int locals x, y, each first-assigned from a CALL
(read_g) and both live across the next call -> both must occupy a
callee-save register; which one gets which depends on the regalloc
tie-break, so any lever that flips the tie flips the bytes.

Pairs to read off the table:
  * sep_xy  vs  comb_xy   -> #3 at the SAME position (read order x,y;
                             only syntax differs).  EQUAL => #3 is purely
                             syntactic; DIFFERENT => #3 is load-bearing.
  * sep_xy  vs  sep_yx    -> #2 first-assignment ORDER (x-first vs y-first).
  * sep_xy  vs  sep_declyx-> #1 declaration ORDER (decl x,y vs y,x).

Run:  uv run c2 cgex run decl-init-combine

RESULT (verified 2026-06-16, byte-level diff of the trials)
-----------------------------------------------------------
* **#2 (first-assignment ORDER) is THE lever** -- load-bearing in every
  context: straight-line (33b vs 27b), inside a loop (same size, the
  mov/call order swaps), and most dramatically with first-assignment
  INSIDE branch arms (48b vs 40b).
* **#3 (combine `int x = E;`) is byte-IDENTICAL** to the separate form
  `int x; ... x = E;` at the SAME position, in all three contexts.  It is
  purely syntactic -- NOT an independent lever.  Its apparent effect is
  entirely a #2 effect: combining merely PINS the first assignment to the
  decl position/order, a state the separate form can also reach.  =>
  redundant as a permuter axis.
* **#1 (decl order alone)** with the same assignment order is byte-neutral
  in these 2-local scenarios; it only bites in a genuine Rule 115
  savings-tie (handled by `c2 decl-swap`).

Conclusion for the permuter: center on **first-assignment ORDER** (move
each local's first assignment earlier/later in the statement stream,
respecting data deps + call boundaries); keep decl-order (Rule 115) as a
secondary axis; drop the combine form (byte-neutral / subsumed by #2).
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="decl-init-combine",
    chk=False,
    externs={
        "read_g": "extern int read_g(void);",
        "sink":   "extern void sink(int v);",
    },
)

_PRE = "extern int read_g(void);\nextern void sink(int v);\n\n"

# ── separate, decl order x,y, first-assign order x,y ───────────
exp.add("sep_xy", _PRE + """
void f(void)
{
    int x;
    int y;
    x = read_g();
    y = read_g();
    sink(x);
    sink(y);
}
""", note="separate decl/assign; decl x,y; assign x,y")

# ── #3: combine decl+init, SAME read order (x,y) ───────────────
exp.add("comb_xy", _PRE + """
void f(void)
{
    int x = read_g();
    int y = read_g();
    sink(x);
    sink(y);
}
""", note="combined int x=...; int y=...; (same position as sep_xy)")

# ── #2: separate, first-assignment order y,x ───────────────────
exp.add("sep_yx", _PRE + """
void f(void)
{
    int x;
    int y;
    y = read_g();
    x = read_g();
    sink(x);
    sink(y);
}
""", note="separate; decl x,y; assign y,x (first-assign order)")

# ── #2 combined counterpart: combine with read order y,x ───────
exp.add("comb_yx", _PRE + """
void f(void)
{
    int y = read_g();
    int x = read_g();
    sink(x);
    sink(y);
}
""", note="combined, read order y,x")

# ── #1: separate, DECL order y,x, assign order x,y ─────────────
exp.add("sep_declyx", _PRE + """
void f(void)
{
    int y;
    int x;
    x = read_g();
    y = read_g();
    sink(x);
    sink(y);
}
""", note="separate; decl y,x; assign x,y (decl order only)")

# ══ LOOP family: x,y live across a loop, used INSIDE (loop savings) ══
exp.add("loop_sep_xy", _PRE + """
void f(void)
{
    int x;
    int y;
    int i;
    x = read_g();
    y = read_g();
    for (i = 0; i < 10; i = i + 1) {
        sink(x);
        sink(y);
    }
}
""", note="LOOP: separate; assign x,y")

exp.add("loop_sep_yx", _PRE + """
void f(void)
{
    int x;
    int y;
    int i;
    y = read_g();
    x = read_g();
    for (i = 0; i < 10; i = i + 1) {
        sink(x);
        sink(y);
    }
}
""", note="LOOP: separate; assign y,x (#2 first-assign order)")

exp.add("loop_comb_xy", _PRE + """
void f(void)
{
    int i;
    int x = read_g();
    int y = read_g();
    for (i = 0; i < 10; i = i + 1) {
        sink(x);
        sink(y);
    }
}
""", note="LOOP: combined x,y (#3 vs loop_sep_xy)")

exp.add("loop_declyx", _PRE + """
void f(void)
{
    int y;
    int x;
    int i;
    x = read_g();
    y = read_g();
    for (i = 0; i < 10; i = i + 1) {
        sink(x);
        sink(y);
    }
}
""", note="LOOP: separate; decl y,x (#1 decl order)")

# ══ BRANCH family: asymmetric conditional use ══
exp.add("br_sep_xy", _PRE + """
void f(void)
{
    int x;
    int y;
    x = read_g();
    y = read_g();
    if (read_g()) {
        sink(x);
    }
    sink(y);
}
""", note="BRANCH: separate; assign x,y")

exp.add("br_sep_yx", _PRE + """
void f(void)
{
    int x;
    int y;
    y = read_g();
    x = read_g();
    if (read_g()) {
        sink(x);
    }
    sink(y);
}
""", note="BRANCH: separate; assign y,x (#2 first-assign order)")

exp.add("br_comb_xy", _PRE + """
void f(void)
{
    int x = read_g();
    int y = read_g();
    if (read_g()) {
        sink(x);
    }
    sink(y);
}
""", note="BRANCH: combined x,y (#3 vs br_sep_xy)")

# ══ first-assignment INSIDE branches (the conditional-init shape) ══
exp.add("br_inside_xy", _PRE + """
void f(void)
{
    int x;
    int y;
    if (read_g()) {
        x = read_g();
        y = read_g();
    } else {
        x = 0;
        y = 0;
    }
    sink(x);
    sink(y);
}
""", note="BRANCH: first-assign inside both arms; x,y")

exp.add("br_inside_yx", _PRE + """
void f(void)
{
    int x;
    int y;
    if (read_g()) {
        y = read_g();
        x = read_g();
    } else {
        y = 0;
        x = 0;
    }
    sink(x);
    sink(y);
}
""", note="BRANCH: first-assign inside arms; y,x (#2 inside a branch)")
