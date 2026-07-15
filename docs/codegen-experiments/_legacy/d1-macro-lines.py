"""d1-macro-lines -- does Watcom 10.0a's `-d1` tag macro-expanded code
with the macro's DEFINITION line or its USE line?

Triggered by `c2 line-compare choose_odd_tune`: PS emits a backward
line transition (L544 -> L543) at the same byte offset where our
recomp emits a forward one (L884 -> L885).  Theory: PS source had a
`#define` for the trailing `tune_branch += 1` statement, defined
EARLIER in the file than the call site, and Watcom's debug-info
emitter tagged the expanded code with the DEFINITION line.

We test three source forms that should produce IDENTICAL bytes for
the body, and inspect the `-d1` line records of each:

  A-inline             -- the statement written inline (our current
                          recomp shape)
  B-macro-def-earlier  -- a #define for the statement, defined ABOVE
                          the function (definition line BEFORE the
                          call site, like PS's L543 vs L544)
  C-macro-def-later    -- a #define for the statement, defined BELOW
                          the function (definition line AFTER all the
                          uses) -- pure control, to see if Watcom
                          would emit a FORWARD jump for the expansion

If the theory is correct:

  * A's line records walk forward through the body.
  * B emits the macro-expanded body with the line of the #define
    (earlier source line), producing a BACKWARD line transition at
    the same byte offset where the use site emits a forward
    transition.
  * C similarly emits the macro-expanded body with the #define line
    (which is LATER than the call site).

The experiment dumps the recompiled binary's debug info (via the
oracle's `_load_oracle_line_lookup`) and prints the line stream per
trial.

Run with::

    uv run c2 cgex run d1-macro-lines
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="d1-macro-lines",
    chk=False,
    externs={
        "odd_battle_tune": "extern int odd_battle_tune;",
        "tune_branch":     "extern int tune_branch;",
        "rand128":         "extern int rand128;",
    },
    extra_defs="""
int odd_battle_tune;
int tune_branch;
int rand128;
""",
    cflags="-bt=dos -mf -4r -s -d1",
)


# ── A: statement inlined (our current recomp form) ─────────────────
exp.add(
    "A-inline",
    """
void choose_odd_tune(int x)
{
    if (odd_battle_tune) {
        tune_branch = x + (rand128 & 6);
        odd_battle_tune = 0;
    } else {
        odd_battle_tune = 1;
        tune_branch += 1;
    }
}
""",
    note="statement inlined; baseline (our current source shape)",
)


# ── B: #define BEFORE the function (PS theory) ─────────────────────
exp.add(
    "B-macro-def-earlier",
    """
#define BUMP_BRANCH    tune_branch += 1
void choose_odd_tune(int x)
{
    if (odd_battle_tune) {
        tune_branch = x + (rand128 & 6);
        odd_battle_tune = 0;
    } else {
        odd_battle_tune = 1;
        BUMP_BRANCH;
    }
}
""",
    note="#define BEFORE the function (matches PS source theory)",
)


# ── C: #define AFTER the function (control / inverse) ──────────────
exp.add(
    "C-macro-def-later",
    """
void choose_odd_tune(int x)
{
    if (odd_battle_tune) {
        tune_branch = x + (rand128 & 6);
        odd_battle_tune = 0;
    } else {
        odd_battle_tune = 1;
        BUMP_BRANCH;
    }
}

#define BUMP_BRANCH    tune_branch += 1
""",
    note="#define AFTER the function (use site precedes definition)",
)
