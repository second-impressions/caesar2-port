"""totalXpercent / totalXpercentX100 — Rule 28b regalloc + tail-merge.

PS pushes BOTH ebx (product) AND ecx (divisor) to enable Rule 15
cross-function tail-merge between totalXpercent and totalXpercentX100.

Recomp pushes only ebx, uses different IMUL form, and emits an
inline divide tail per function.  Net cost: 12 b on
totalXpercentX100 + 24 b on totalXpercent.

Probe which source pattern flips Watcom 10.0a into emitting:
  push ebx; push ecx
  mov ebx, eax
  imul ebx, edx
  mov ecx, <divisor>     ← key signal
  mov eax, ebx
  cdq                    ← or sar edx, 0x1f
  idiv ecx
  pop ecx; pop ebx
  ret
"""

from c2.commands.cgex import Experiment

_PRELUDE = ""
_DEFS = ""

exp = Experiment(
    name="totalXpercent",
    ps_function="totalXpercent",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# ── trial 1: baseline — direct expression ─────────────────────
exp.add(
    "baseline",
    """
int totalXpercent(int a, int b)
{
    return (a * b) / 100;
}
""",
    note="direct (a*b)/100 expression",
)


# ── trial 2: explicit product local ────────────────────────────
exp.add(
    "product-local",
    """
int totalXpercent(int a, int b)
{
    int p = a * b;
    return p / 100;
}
""",
    note="explicit int p = a*b; return p/100",
)


# ── trial 3: divisor-via-local int ─────────────────────────────
exp.add(
    "divisor-local",
    """
int totalXpercent(int a, int b)
{
    int d = 100;
    return (a * b) / d;
}
""",
    note="divisor in local int d",
)


# ── trial 4: both intermediate ─────────────────────────────────
exp.add(
    "both-locals",
    """
int totalXpercent(int a, int b)
{
    int p = a * b;
    int d = 100;
    return p / d;
}
""",
    note="both product and divisor in named locals",
)


# ── trial 5: register hint on product ──────────────────────────
exp.add(
    "register-product",
    """
int totalXpercent(int a, int b)
{
    register int p = a * b;
    return p / 100;
}
""",
    note="register int p — Watcom register hint",
)


# ── trial 6: order-flipped (b first) ───────────────────────────
exp.add(
    "b-first",
    """
int totalXpercent(int a, int b)
{
    return (b * a) / 100;
}
""",
    note="b*a — Rule 4 source-order test",
)


# ── trial 7: cast to long ───────────────────────────────────────
exp.add(
    "long-cast",
    """
int totalXpercent(int a, int b)
{
    return (int)(((long)a * b) / 100);
}
""",
    note="long intermediate to force EDX:EAX product",
)


# ── trial 8: mutate first parameter ────────────────────────────
exp.add(
    "a-times-equals-b",
    """
int totalXpercent(int a, int b)
{
    a *= b;
    return a / 100;
}
""",
    note="parameter mutation: a *= b; return a/100",
)


# ── trial 9: mutate second parameter ───────────────────────────
exp.add(
    "b-times-equals-a",
    """
int totalXpercent(int a, int b)
{
    b *= a;
    return b / 100;
}
""",
    note="parameter mutation: b *= a; return b/100",
)


# ── trial 10: staged product with separate assignment ──────────
exp.add(
    "p-assign-mul",
    """
int totalXpercent(int a, int b)
{
    int p;
    p = a;
    p *= b;
    return p / 100;
}
""",
    note="named p with separate p=a; p*=b sequence",
)


# ── trial 11: staged divisor assigned after product ────────────
exp.add(
    "late-divisor",
    """
int totalXpercent(int a, int b)
{
    int p;
    int d;
    p = a * b;
    d = 100;
    return p / d;
}
""",
    note="force product first, divisor local assigned later",
)


# ── trial 12: volatile divisor local ───────────────────────────
exp.add(
    "volatile-divisor",
    """
int totalXpercent(int a, int b)
{
    int p = a * b;
    volatile int d = 100;
    return p / d;
}
""",
    note="volatile local divisor; does it move divisor out of EBX?",
)
