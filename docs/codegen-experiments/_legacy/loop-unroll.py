"""Loop unrolling — when does Watcom 10.0a auto-unroll a small loop?

PS function `test_citymap_neighbours_posedge` (801 b @ 0x6B4F3) contains:

    L2820 (gmn[i] consistency check):
        ... rolled loop over gmn[7] ...

    L2822 (gmn[i+8] = gmn[i]):
        mov al, [gmn]    ; mov [gmn+8], al
        mov al, [gmn+1]  ; mov [gmn+9], al
        ... 8 pairs, fully unrolled ...

    L2825 (gmn_run max-tracking, 16 iters):
        xor eax, eax
        loop_top:
            cmp byte [eax + gmn], 0
            ...
            inc eax
            cmp eax, 16
            jl loop_top
        ← NOT unrolled

So Watcom DOES unroll some loops but not others.  This experiment maps
the trigger conditions.

Hypotheses:
  (a) Trip count ≤ 8 unrolls, ≥ 16 doesn't.
  (b) Single-statement body unrolls; multi-statement doesn't.
  (c) `dst[i] = src[i]` style fully-known indexing unrolls.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="loop-unroll",
    chk=False,
    externs={},
    extra_defs="""
char *city_map;
int gmn_sptr;
int gmn_y;
char gmn[16];
""",
)


# ── trial 1: 8-iter array copy (matches PS L2822 unrolled form) ───
exp.add(
    "copy8",
    """
char src[16];

void f(void)
{
    int i;
    for (i = 0; i < 8; i++)
        src[i + 8] = src[i];
}
""",
    note="8-iter, single-statement, byte-array copy",
)


# ── trial 2: 16-iter same body (does it unroll?) ──────────────────
exp.add(
    "copy16",
    """
char src[24];

void f(void)
{
    int i;
    for (i = 0; i < 16; i++)
        src[i + 8] = src[i];
}
""",
    note="16-iter, single-statement",
)


# ── trial 3: 8-iter with offs[] read pattern ──────────────────────
# PS reads `((char*)city_map)[gmn_sptr + offs[i]] & mask` — does
# Watcom unroll with `offs[i]` as a stack-array dependent read?
exp.add(
    "8iter_indexed_read",
    """
extern char *city_map;
extern int gmn_sptr;
extern char gmn[16];

void f(int mask)
{
    int offs[8];
    int i;
    offs[0] = -1599; offs[1] = -1579; offs[2] = 21;   offs[3] = 1621;
    offs[4] = 1601;  offs[5] = 1581;  offs[6] = -19;  offs[7] = -1619;
    for (i = 0; i < 8; i++)
        gmn[i] = city_map[gmn_sptr + offs[i]] & mask;
}
""",
    note="8-iter with offs[i] indexed read — does it unroll?",
)


# ── trial 4: 8-iter compile-time-const offs[] ─────────────────────
exp.add(
    "8iter_static_const",
    """
extern char *city_map;
extern int gmn_sptr;
extern char gmn[16];

static const int offs[8] = {
    -1599, -1579, 21, 1621, 1601, 1581, -19, -1619,
};

void f(int mask)
{
    int i;
    for (i = 0; i < 8; i++)
        gmn[i] = city_map[gmn_sptr + offs[i]] & mask;
}
""",
    note="static const offs[] — does Watcom propagate + unroll?",
)


# ── trial 5: 8-iter with per-iter conditional (≈ posedge body) ────
exp.add(
    "8iter_with_edge",
    """
extern char *city_map;
extern int gmn_sptr;
extern int gmn_y;
extern char gmn[16];

void f(int mask)
{
    int offs[8];
    int edge[8];
    int i;
    offs[0] = -1599; offs[1] = -1579; offs[2] = 21;   offs[3] = 1621;
    offs[4] = 1601;  offs[5] = 1581;  offs[6] = -19;  offs[7] = -1619;
    edge[0] = (gmn_y == 0);
    edge[1] = (gmn_y == 0);
    edge[2] = 0;
    edge[3] = 0;
    edge[4] = 0;
    edge[5] = 0;
    edge[6] = 0;
    edge[7] = 0;
    for (i = 0; i < 8; i++) {
        if (edge[i]) gmn[i] = 1;
        else gmn[i] = city_map[gmn_sptr + offs[i]] & mask;
    }
}
""",
    note="8-iter with edge[] AND offs[] indexed — closer to posedge",
)
