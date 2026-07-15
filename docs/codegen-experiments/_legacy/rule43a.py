"""Rule 43a — dead `mov reg, ebx` at function entry under #pragma on(check_stack).

PS.EXE function `xor_a_diamond_lhs_top` (88 b @ 0x27BC3) emits this
prologue:

    push 0x18; call __CHK
    push esi; push edi; push ebp; push eax; push edx
    mov esi, ebx        ; ← DEAD: ESI is overwritten 11 insns later
    mov edx, ecx
    mov ebp, [esp + 0x18]
    ...
    lea esi, [ebx + 2]  ; OVERWRITES the earlier mov esi, ebx

Our default oracle build of the same source produces 86 b — same body
without the dead `mov esi, ebx`.  We've theorised the trigger lies in
register allocation (PS chose a callee-save reg `esi` to home the
`width` parameter; the oracle chose to keep it in the arrival reg
`ebx`).  This experiment systematically probes mutations of the C
source, the prelude, and surrounding TU context to find the trigger.

Run with::

    uv run c2 cgex run rule43a
    uv run c2 cgex run rule43a --trial baseline
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="rule43a",
    ps_function="xor_a_diamond_lhs_top",
    chk=True,
    externs={
        "xor_internal_2point":
            "extern void xor_internal_2point(int x, int y, int colour);",
        "xor_internal_3point":
            "extern void xor_internal_3point("
            "int x, int y, int colour, int wid);",
    },
    extra_defs="""
int g_w;
int dummy_sink;
""",
)


# ── trial 1: faithful single-function reconstruction ──────────────
exp.add(
    "baseline",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset;
    int y_offset;
    int loop_max;

    x_offset = 0;
    y_offset = height / 2;
    loop_max = width + 2;
    --y_offset;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="faithful body; matches everywhere except the dead mov",
)


# ── trial 2: explicit local alias ────────────────────────────────
exp.add(
    "alias-width",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int local_width = width;
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = local_width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="explicit alias for width — should home it in a temp",
)


# ── trial 3: width referenced after loop ─────────────────────────
exp.add(
    "width-after-loop",
    """
extern int g_w;
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
    g_w = width;   /* keeps width live past the loop */
}
""",
    note="extending width's live range past the loop",
)


# ── trial 4: width via an unsigned-cast temp ─────────────────────
exp.add(
    "width-unsigned-cast",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    unsigned uw = (unsigned)width;
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = (int)(uw + 2u);

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="forcing a type-conversion node — DoParmDecl emits convert ins",
)


# ── trial 5: register hint ───────────────────────────────────────
exp.add(
    "register-hint",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    register int xo = 0;
    register int yo = height / 2 - 1;
    register int lm = width + 2;

    for ( ; xo < lm / 2; xo += 2, yo--) {
        xor_internal_2point(x + xo, y + yo, color);
    }
}
""",
    note="register qualifier on temps",
)


# ── trial 6: width-passed-as-int-pointer (address taken) ─────────
exp.add(
    "width-addr-taken",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int *pw = &width;
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = *pw + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="address-taken width — forces stack home",
)


# ── trial 7: forced parm aux to esi ──────────────────────────────
exp.add(
    "parm-aux-esi",
    """
#pragma aux xor_a_diamond_lhs_top parm [eax][edx][esi][edi][ebp]
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="parm passed in esi directly — does PS-shape change?",
)


# ── trial 8: many adjacent functions with same shape ─────────────
# Theory: regalloc decisions might depend on global pressure
# accumulated across the TU.  Adding a dozen sister functions
# might shift the heuristic.
exp.add(
    "many-sisters",
    """
void neighbor1(int x, int y, int w, int h, int c) {
    int i; for (i = 0; i < w; i++) xor_internal_2point(x+i, y, c);
}
void neighbor2(int x, int y, int w, int h, int c) {
    int i; for (i = 0; i < h; i++) xor_internal_2point(x, y+i, c);
}
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="extra TU-mates to shift global regalloc state",
)


# ── trial 9: two consecutive uses of width ───────────────────────
# DoParmDecl emits the param-init copy regardless; the question is
# whether IsDeadIns elides it.  If `width` is used in two separate
# expressions, the optimizer might keep the temp home.
exp.add(
    "width-two-reads",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;
    int half = width / 2;     /* second read of width */

    for ( ; x_offset < loop_max / 2 && x_offset < half * 2;
          x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="two reads of width — temp may stay live longer",
)


# ── trial 10: with -d2 debug flag ────────────────────────────────
exp.add(
    "debug-d2",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    cflags="-bt=dos -mf -4r -s -d2",
    note="full symbolic debug — keeps locals visible",
)


# ── trial 11: with -ol (loop-opt) ────────────────────────────────
exp.add(
    "ol-loopopt",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    cflags="-bt=dos -mf -4r -s -ol",
    note="loop optimisation enabled",
)


# ── trial 12: with -d1 (line-numbers only) ───────────────────────
exp.add(
    "debug-d1",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    cflags="-bt=dos -mf -4r -s -d1",
    note="line-numbers debug only",
)


# ── trial 13: width inline in for-condition (no hoist) ───────────
# Theory: with `width + 2` *inside* the for-condition, Watcom may
# decide to keep `width` live across the call (since each iteration
# re-reads it), allocating it to a callee-save reg.
exp.add(
    "width-inline-cond",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;

    for ( ; x_offset < (width + 2) / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="width inlined in for-condition; should stay live across call",
)


# ── trial 14: width-via-pointer-arg, all reads through *p ────────
exp.add(
    "width-pointer-arg",
    """
void xor_a_diamond_lhs_top(int x, int y, int *pw, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = *pw + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="parameter is now an int* (forces a memory load for width)",
)


# ── trial 15: width used inside loop body, after the call ────────
exp.add(
    "width-after-call",
    """
extern int dummy_sink;
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
        dummy_sink = width;   /* keeps width alive across the call */
    }
}
""",
    note="width consumed inside loop after the call",
)


# ── trial 16: width passed *to* the inner call ───────────────────
# If width is one of the call args, the regalloc must keep it in
# a stable home until the call site.
exp.add(
    "width-as-call-arg",
    """
extern void xor_internal_3point(int x, int y, int color, int wid);
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_3point(x + x_offset, y + y_offset, color, width);
    }
}
""",
    note="width passed as call arg every iteration",
)


# ── trial 17: width still live through a tail statement ─────────
exp.add(
    "width-tail-use",
    """
extern int dummy_sink;
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
    dummy_sink = width;
}
""",
    note="width used after loop (single tail use)",
)


# ── trial 18: param mutation (width += 2) ─────────────────────────
# DoParmDecl might emit the copy for params that get *modified*.
exp.add(
    "param-mutation",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    width += 2;

    for ( ; x_offset < width / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="width is mutated in-place (param assignment)",
)


# ── trial 19: 5-arg with width mutated AND used by call ─────────
exp.add(
    "param-mutation-and-call-arg",
    """
extern void xor_internal_3point(int x, int y, int color, int wid);
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    width += 2;
    for ( ; x_offset < width / 2; x_offset += 2, y_offset--) {
        xor_internal_3point(x + x_offset, y + y_offset, color, width);
    }
}
""",
    note="width mutated AND passed to call",
)


# ── trial 20: assigned-to local (forces convert ins) ─────────────
exp.add(
    "assign-then-add",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width;
    loop_max += 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="loop_max = width then += 2 (split assignment)",
)


# ── trial 21a: param-mutation, lea ordering — `+= 2` before --yo ──
# PS emits lea esi, [ebx+2] *before* lea edi, [eax-1].  Try
# rearranging the source to put the width-mutation as the LAST
# pre-loop statement.
exp.add(
    "param-mutation-width-last",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2;
    --y_offset;
    width += 2;

    for ( ; x_offset < width / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="reorder so `width += 2` is the last pre-loop statement",
)

exp.add(
    "param-mutation-yo-last",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset;
    width += 2;
    y_offset = height / 2 - 1;

    for ( ; x_offset < width / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="`width += 2` first, then y_offset",
)

exp.add(
    "param-mutation-yo-decr",
    """
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2;
    width += 2;
    --y_offset;

    for ( ; x_offset < width / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="height/2 then width+=2 then --yo",
)


# ── trial 22: short-instead-of-int (force convert at parm) ───────
exp.add(
    "width-short",
    """
void xor_a_diamond_lhs_top(int x, int y, short width, int height, int color)
{
    int x_offset = 0;
    int y_offset = height / 2 - 1;
    int loop_max = width + 2;

    for ( ; x_offset < loop_max / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}
""",
    note="width is short — forces movsx convert in DoParmDecl",
)
