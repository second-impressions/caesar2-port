"""ferret_heading — param register swap (PS y->EAX/x->EBX vs RC x->EAX/y->EDX).

PS @ 0x2CDCD, 142 bytes.

PS prologue:
    push ebx
    push edi
    mov  ebx, eax            ; ebx = x  (param1)
    mov  eax, edx            ; eax = y  (param2)
    mov  edx, [ferret_targ_x]
    cmp  ebx, edx            ; x vs targ_x
    ...
    mov  edi, [ferret_targ_y]
    cmp  eax, edi            ; y vs targ_y

RC keeps x in EAX, y in EDX (arrival regs) and never moves them.

So PS moves the *more-used* value (y, 3 cmp uses) into EAX and the
less-used (x, 1 cmp) into callee-save EBX.  Goal: find the source shape
that reproduces that.

Run::

    uv run c2 cgex run ferret_heading
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
extern int ferret_targ_x;
extern int ferret_targ_y;
"""

_DEFS = _PRELUDE + """
int ferret_targ_x;
int ferret_targ_y;
"""

exp = Experiment(
    name="ferret_heading",
    ps_function="ferret_heading",
    chk=False,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# ── baseline — current source shape ─────────────────────────────────────
exp.add("baseline", """
unsigned char ferret_heading(int x, int y)
{
    if (x > ferret_targ_x) {
        if (y > ferret_targ_y) return 7;
        if (y == ferret_targ_y) return 6;
        if (y < ferret_targ_y) return 5;
    } else if (x == ferret_targ_x) {
        if (y > ferret_targ_y) return 0;
        if (y != ferret_targ_y && y < ferret_targ_y) return 4;
    } else if (x < ferret_targ_x) {
        if (y > ferret_targ_y) return 1;
        if (y == ferret_targ_y) return 2;
        if (y < ferret_targ_y) return 3;
    }
    return 8;
}
""", note="baseline (current source)")


# ── B: cache targ_x/targ_y into locals first ────────────────────────────
exp.add("B_cache_targs", """
unsigned char ferret_heading(int x, int y)
{
    int tx = ferret_targ_x;
    int ty = ferret_targ_y;
    if (x > tx) {
        if (y > ty) return 7;
        if (y == ty) return 6;
        if (y < ty) return 5;
    } else if (x == tx) {
        if (y > ty) return 0;
        if (y != ty && y < ty) return 4;
    } else if (x < tx) {
        if (y > ty) return 1;
        if (y == ty) return 2;
        if (y < ty) return 3;
    }
    return 8;
}
""", note="cache both targs in locals")


# ── C: cache only targ_y ────────────────────────────────────────────────
exp.add("C_cache_ty", """
unsigned char ferret_heading(int x, int y)
{
    int ty = ferret_targ_y;
    if (x > ferret_targ_x) {
        if (y > ty) return 7;
        if (y == ty) return 6;
        if (y < ty) return 5;
    } else if (x == ferret_targ_x) {
        if (y > ty) return 0;
        if (y != ty && y < ty) return 4;
    } else if (x < ferret_targ_x) {
        if (y > ty) return 1;
        if (y == ty) return 2;
        if (y < ty) return 3;
    }
    return 8;
}
""", note="cache only targ_y")


# ── D: compare reversed operand order (targ first) ──────────────────────
exp.add("D_targ_first", """
unsigned char ferret_heading(int x, int y)
{
    if (ferret_targ_x < x) {
        if (ferret_targ_y < y) return 7;
        if (ferret_targ_y == y) return 6;
        if (ferret_targ_y > y) return 5;
    } else if (ferret_targ_x == x) {
        if (ferret_targ_y < y) return 0;
        if (ferret_targ_y != y && ferret_targ_y > y) return 4;
    } else if (ferret_targ_x > x) {
        if (ferret_targ_y < y) return 1;
        if (ferret_targ_y == y) return 2;
        if (ferret_targ_y > y) return 3;
    }
    return 8;
}
""", note="targ on left of compares")


# ── F: cache only targ_x ────────────────────────────────────────────────
exp.add("F_cache_tx", """
unsigned char ferret_heading(int x, int y)
{
    int tx = ferret_targ_x;
    if (x > tx) {
        if (y > ferret_targ_y) return 7;
        if (y == ferret_targ_y) return 6;
        if (y < ferret_targ_y) return 5;
    } else if (x == tx) {
        if (y > ferret_targ_y) return 0;
        if (y != ferret_targ_y && y < ferret_targ_y) return 4;
    } else if (x < tx) {
        if (y > ferret_targ_y) return 1;
        if (y == ferret_targ_y) return 2;
        if (y < ferret_targ_y) return 3;
    }
    return 8;
}
""", note="cache only targ_x")


# ── G: cache targ_x, reload targ_y into a reused local per branch ────
exp.add("G_tx_cache_ty_local", """
unsigned char ferret_heading(int x, int y)
{
    int tx = ferret_targ_x;
    int ty;
    if (x > tx) {
        ty = ferret_targ_y;
        if (y > ty) return 7;
        if (y == ty) return 6;
        if (y < ty) return 5;
    } else if (x == tx) {
        ty = ferret_targ_y;
        if (y > ty) return 0;
        if (y != ty && y < ty) return 4;
    } else if (x < tx) {
        ty = ferret_targ_y;
        if (y > ty) return 1;
        if (y == ty) return 2;
        if (y < ty) return 3;
    }
    return 8;
}
""", note="cache targ_x, ty reloaded into reused local per branch")


# ── H: cache targ_x in local declared AFTER (decl-order) ────────────
exp.add("H_tx_ty_both_local", """
unsigned char ferret_heading(int x, int y)
{
    int ty;
    int tx = ferret_targ_x;
    if (x > tx) {
        ty = ferret_targ_y;
        if (y > ty) return 7;
        if (y == ty) return 6;
        if (y < ty) return 5;
    } else if (x == tx) {
        ty = ferret_targ_y;
        if (y > ty) return 0;
        if (y != ty && y < ty) return 4;
    } else if (x < tx) {
        ty = ferret_targ_y;
        if (y > ty) return 1;
        if (y == ty) return 2;
        if (y < ty) return 3;
    }
    return 8;
}
""", note="ty declared first, tx cached")


# ── I: get_heading-style single-return with `heading` var, no cache ──
exp.add("I_heading_var", """
unsigned char ferret_heading(int x, int y)
{
    unsigned char heading;
    if (x > ferret_targ_x) {
        if (y > ferret_targ_y) heading = 7;
        else if (y == ferret_targ_y) heading = 6;
        else if (y < ferret_targ_y) heading = 5;
    } else if (x == ferret_targ_x) {
        if (y > ferret_targ_y) heading = 0;
        else if (y < ferret_targ_y) heading = 4;
    } else if (x < ferret_targ_x) {
        if (y > ferret_targ_y) heading = 1;
        else if (y == ferret_targ_y) heading = 2;
        else if (y < ferret_targ_y) heading = 3;
    } else {
        heading = 8;
    }
    return heading;
}
""", note="get_heading-style single return, no cache")


# ── J: cache tx and keep it live to end (occupy EDX through branches) ─
exp.add("J_tx_kept_live", """
unsigned char ferret_heading(int x, int y)
{
    int tx = ferret_targ_x;
    unsigned char heading;
    if (x > tx) {
        if (y > ferret_targ_y) return 7;
        if (y == ferret_targ_y) return 6;
        if (y < ferret_targ_y) return 5;
    } else if (x == tx) {
        if (y > ferret_targ_y) return 0;
        if (y != ferret_targ_y && y < ferret_targ_y) return 4;
    } else if (x < tx) {
        if (y > ferret_targ_y) return 1;
        if (y == ferret_targ_y) return 2;
        if (y < ferret_targ_y) return 3;
    }
    heading = (unsigned char)tx;
    return heading == heading ? 8 : (unsigned char)tx;
}
""", note="tx kept live via trailing use (probe)")


# ── E: reference y before x (compute a dummy y use first) ────────────────
exp.add("E_y_first", """
unsigned char ferret_heading(int x, int y)
{
    if (y > ferret_targ_y) {
        if (x > ferret_targ_x) return 7;
        if (x == ferret_targ_x) return 0;
        if (x < ferret_targ_x) return 1;
    }
    if (x > ferret_targ_x) {
        if (y == ferret_targ_y) return 6;
        if (y < ferret_targ_y) return 5;
    } else if (x == ferret_targ_x) {
        if (y < ferret_targ_y) return 4;
    } else if (x < ferret_targ_x) {
        if (y == ferret_targ_y) return 2;
        if (y < ferret_targ_y) return 3;
    }
    return 8;
}
""", note="restructured y-first (NOT semantically identical, probe only)")
