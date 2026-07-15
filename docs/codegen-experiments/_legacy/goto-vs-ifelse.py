"""goto-vs-ifelse — source-form distinguisher for goto-tail vs if/else.

GROUND-TRUTH SYNTHESIS for the goto-to-ifelse detector.  PS.EXE corpus
contains both forms but for many cases (body_A == 0) they produce
byte-identical output, so the corpus alone can't tell us when source
form is observable from bytes.  This experiment synthesizes a small
controlled corpus where we KNOW the source form and measure the byte
signature.

Forms tested:
  A_goto_no_body:      if (X) goto L; rest; L: ...
  A_ifelse_no_body:    if (!X) { rest; } L: ...                (equivalent to A_goto_no_body)

  B_goto_short_body:   if (X) { stmt_A; goto L; } rest; L: ... (body_A=1)
  B_ifelse_short_body: if (!X) { rest; } else { stmt_A; } L: ... (body_A=1, swapped)

  C_goto_med_body:     if (X) { stmt_A1; stmt_A2; goto L; } rest; L: ...
  C_ifelse_med_body:   if (!X) { rest; } else { stmt_A1; stmt_A2; } L: ...

For each pair, the experiment dumps the byte diff between the goto
form and the ifelse form, showing whether they collapse to identical
bytes (no source-form distinguishable from bytes) or differ (source
form distinguishable).

Hypothesis (per the OW v1 source analysis in bld/cg/c/encode.c
DoCondJump + FlipCond):
  * body_A == 0   →  goto and ifelse produce IDENTICAL bytes (FlipCond
                     collapses the two block layouts since dest_true ==
                     dest_next in both cases).
  * body_A >= 1   →  goto puts body_A at fall-through (right after jcc),
                     ifelse puts body_B at fall-through.  Different
                     block layouts ⇒ DIFFERENT bytes.

Run::

    uv run c2 cgex run goto-vs-ifelse                  # summary table
    uv run c2 cgex run goto-vs-ifelse --trial B_goto_short_body  # disasm
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
extern int sink(int);
extern int side_a(int);
extern int side_b(int);
extern int side_c(int);
extern int common_arg;
extern int global_state;
"""

_DEFS = """
int common_arg;
int global_state;
int sink(int x) { (void)x; return 0; }
int side_a(int x) { (void)x; return 0; }
int side_b(int x) { (void)x; return 0; }
int side_c(int x) { (void)x; return 0; }
"""


exp = Experiment(
    name="goto-vs-ifelse",
    chk=False,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# ── A: body_A = 0 (no body before the goto) ─────────────────────────
# Forms collapse to identical bytes when body_A is empty.
exp.add("A_goto_no_body", """
void g(int x)
{
    if (x) goto L;
    side_a(1);
    side_b(2);
    side_c(3);
L:
    sink(global_state);
}
""", note="if (X) goto L; rest; L:  -- empty body_A")

exp.add("A_ifelse_no_body", """
void g(int x)
{
    if (!x) {
        side_a(1);
        side_b(2);
        side_c(3);
    }
    sink(global_state);
}
""", note="if (!X) { rest; }  -- no goto, no label")


# ── B: body_A = 1 statement ─────────────────────────────────────────
# Forms should produce DIFFERENT bytes since block layout differs.
exp.add("B_goto_short_body", """
void g(int x)
{
    if (x) {
        global_state = 1;
        goto L;
    }
    side_a(1);
    side_b(2);
    side_c(3);
L:
    sink(global_state);
}
""", note="if (X) { stmt_A; goto L; } rest; L:  -- body_A=1")

exp.add("B_ifelse_short_body", """
void g(int x)
{
    if (!x) {
        side_a(1);
        side_b(2);
        side_c(3);
    } else {
        global_state = 1;
    }
    sink(global_state);
}
""", note="if (!X) { rest; } else { stmt_A; }  -- body_A=1, swapped to else")


# ── C: body_A = 2 statements (the do_a_tutorial_page-like case) ────
exp.add("C_goto_med_body", """
void g(int x)
{
    if (x) {
        global_state = 1;
        common_arg = 2;
        goto L;
    }
    side_a(1);
    side_b(2);
    side_c(3);
    side_a(4);
    side_b(5);
L:
    sink(global_state);
}
""", note="if (X) { stmt; stmt; goto L; } rest; L:")

exp.add("C_ifelse_med_body", """
void g(int x)
{
    if (!x) {
        side_a(1);
        side_b(2);
        side_c(3);
        side_a(4);
        side_b(5);
    } else {
        global_state = 1;
        common_arg = 2;
    }
    sink(global_state);
}
""", note="if (!X) { rest; } else { stmt; stmt; }")
