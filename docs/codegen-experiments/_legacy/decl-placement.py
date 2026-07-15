"""decl-placement — does where a local is declared affect codegen?

Hypothesis: PS source uses strict-C89 top-of-function declarations
everywhere.  The bare `{ }` blocks we see in our decomp source are
codegen cosmetics that compile to the same bytes as the
top-of-function form.

We test candidate source shapes for two scenarios.

SCENARIO 1 — block-scoped int:

  A-top         int x; at function top, assigned where used
  B-block-sep   { int x; x = ...; use(x); }   (bare block, sep-assign)
  C-block-init  { int x = ...; use(x); }      (bare block, init)
  D-c99-mid     int x = ...; use(x);          (C99 mid-decl, no block)

SCENARIO 2 — for-loop counter:

  E-top-for     int i; at function top; for (i=0; ...)
  F-c99-for     for (int i=0; ...)            (C99 for-init)

Equality of (A==B==C) and (E) byte sequences proves the C89
top-of-function form is codegen-equivalent to the bare-block and
in-loop forms our decomp uses.  Watcom 10.0a's behaviour on D / F
tells us whether the original source COULD have used C99 forms.

Run with::

    uv run c2 cgex run decl-placement
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="decl-placement",
    chk=False,
    externs={
        "sink":  "extern void sink(int v);",
        "read_g":"extern int  read_g(void);",
    },
)

# ── A: top-of-function decl (C89, canonical) ───────────────────
exp.add(
    "A-top",
    """
int g_a, g_b;

void f(void)
{
    int x;
    g_a = 1;
    g_b = 2;
    x = read_g();
    if (x == 0) x = 8;
    sink(x);
}
""",
    note="strict C89, decl at function top",
)

# ── B: bare block, decl-then-assign ────────────────────────────
exp.add(
    "B-block-sep",
    """
int g_a, g_b;

void f(void)
{
    g_a = 1;
    g_b = 2;
    {
        int x;
        x = read_g();
        if (x == 0) x = 8;
        sink(x);
    }
}
""",
    note="bare block with separate decl + assignment",
)

# ── C: bare block with initializer ─────────────────────────────
exp.add(
    "C-block-init",
    """
int g_a, g_b;

void f(void)
{
    g_a = 1;
    g_b = 2;
    {
        int x = read_g();
        if (x == 0) x = 8;
        sink(x);
    }
}
""",
    note="bare block, initialized decl",
)

# ── D: C99 mid-decl (no wrapping block) ────────────────────────
exp.add(
    "D-c99-mid",
    """
int g_a, g_b;

void f(void)
{
    g_a = 1;
    g_b = 2;
    int x = read_g();
    if (x == 0) x = 8;
    sink(x);
}
""",
    note="C99 mid-decl — does Watcom 10.0a accept this?",
)

# ── E: for-loop counter at function top (C89) ──────────────────
exp.add(
    "E-top-for",
    """
int g_a, g_b;

void f(void)
{
    int i;
    g_a = 0;
    g_b = read_g();
    for (i = 0; i < 10; i++) {
        sink(i + g_b);
    }
}
""",
    note="strict C89, int i at function top, for (i=0; ...)",
)

# ── F: C99 for-init declaration ────────────────────────────────
exp.add(
    "F-c99-for",
    """
int g_a, g_b;

void f(void)
{
    g_a = 0;
    g_b = read_g();
    for (int i = 0; i < 10; i++) {
        sink(i + g_b);
    }
}
""",
    note="C99 for (int i = 0; ...) — does Watcom 10.0a accept this?",
)
