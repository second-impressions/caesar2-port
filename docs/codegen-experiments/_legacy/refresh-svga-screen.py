"""refresh_svga_screen — SOLVED byte-exact (this probe was the WRONG lever).

This sweep probed cell-pointer / addressing shapes (PS uses `[ecx*8+svga+N]`
scaled-index for every field; do NOT hoist `&svga[idx]` — that part the inline
body already matches).  Addressing was never the lever.

REAL LEVER (decomp/src/refresh.c, byte-exact): declare the two locals `off`
(the pass-2 `eax*5*128` product) and `saved_idx` at FUNCTION scope, not in inner
blocks.  Two same-size-temp allocation roots, both pure scope choices:
  1. SPILL-SLOT order — the three 4-byte spilled temps slot by creation order
     (`SetTempLocation` first->highest [esp+N]; same-size -> `Names[]` order,
     Rule 107).  Block-scoped `off` is created so it slots before the pass-1
     spill -> mirrored `[esp]`/`[esp+4]`, 112 b cascade; function-scope `off`
     slots in source order (saved_idx@8, screen_off@4, off@0) — PS.
  2. PASS-1 EBP tie — `screen_off`/`bank_off` arg loads tie on savings; the
     first-created conflict wins EBP (ConfBefore).  Moving `saved_idx` to
     function scope shifts the whole-function conflict numbering so `bank_off`
     wins EBP (`movzx ebp`) — PS.
See refresh.c's header comment, watcom-codegen-patterns.md Rule 107, and
watcom10.0a `docs/temp-slot-layout.md`.

Lesson: for a spill/slot or equal-savings-tie diff, try a real local at BOTH
function and inner-block scope before concluding "no lever" — the scope changes
temp creation order with zero semantic effect.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
struct svga_cell {
    int            screen_off;
    unsigned short bank_off;
    unsigned short split_off;
};

extern struct svga_cell svga_refresh_data[1200];
extern char             svga_refresh_table[];
extern int              refresh_bank_switch_data[];
extern int              refresh_count;

extern void set_bank(int bank);
extern void refresh_16x16_block(int screen_off, unsigned short bank_off);
extern void refresh_16x16_partblock(int screen_off, unsigned short bank_off,
                                    int width);
"""

_DEFS = """
struct svga_cell {
    int            screen_off;
    unsigned short bank_off;
    unsigned short split_off;
};

struct svga_cell svga_refresh_data[1200];
char             svga_refresh_table[1200];
int              refresh_bank_switch_data[120];
int              refresh_count;

void set_bank(int bank) { (void)bank; }
void refresh_16x16_block(int s, unsigned short b) { (void)s; (void)b; }
void refresh_16x16_partblock(int s, unsigned short b, int w)
    { (void)s; (void)b; (void)w; }
"""

exp = Experiment(
    name="refresh-svga-screen",
    ps_function="refresh_svga_screen",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# ── trial 1: current source (cell ptr in both loops) ────────────
exp.add(
    "cell-both",
    """
void refresh_svga_screen(void)
{
    struct svga_cell *cell;
    int row, col, idx;
    int eax;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row * 4] != 0) {
            int saved_idx = idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row * 4 + 1] - 1);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    cell = &svga_refresh_data[idx];
                    refresh_16x16_partblock(cell->screen_off,
                                            cell->bank_off, eax);
                }
            }
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row * 4 + 1]);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    cell = &svga_refresh_data[idx];
                    refresh_16x16_partblock(cell->screen_off + eax * 5 * 128,
                                            cell->split_off, 16 - eax);
                }
            }
        } else {
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    eax = refresh_bank_switch_data[row * 4 + 1];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    set_bank(eax);
                    refresh_16x16_block(svga_refresh_data[idx].screen_off,
                                        svga_refresh_data[idx].bank_off);
                }
            }
        }
    }
}
""",
    note="cell ptr in split-row loops, inline in non-split loop",
)


# ── trial 2: no cell ptr anywhere (all inline) ──────────────────
exp.add(
    "no-cell",
    """
void refresh_svga_screen(void)
{
    int row, col, idx;
    int eax;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row * 4] != 0) {
            int saved_idx = idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row * 4 + 1] - 1);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    refresh_16x16_partblock(
                        svga_refresh_data[idx].screen_off,
                        svga_refresh_data[idx].bank_off, eax);
                }
            }
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row * 4 + 1]);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    refresh_16x16_partblock(
                        svga_refresh_data[idx].screen_off + eax * 5 * 128,
                        svga_refresh_data[idx].split_off, 16 - eax);
                }
            }
        } else {
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    eax = refresh_bank_switch_data[row * 4 + 1];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    set_bank(eax);
                    refresh_16x16_block(
                        svga_refresh_data[idx].screen_off,
                        svga_refresh_data[idx].bank_off);
                }
            }
        }
    }
}
""",
    note="all access via svga_refresh_data[idx].field (no local ptr)",
)


# ── trial 3: int[] type with manual cell offsets ────────────────
exp.add(
    "int-array",
    """
extern int  svga_refresh_data_int[];
#define SVGA_INT  ((int *)svga_refresh_data)

void refresh_svga_screen(void)
{
    int *cell;
    int row, col, idx;
    int eax;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row * 4] != 0) {
            int saved_idx = idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row * 4 + 1] - 1);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    cell = &SVGA_INT[idx * 2];
                    refresh_16x16_partblock(cell[0],
                                            ((unsigned short *)cell)[2], eax);
                }
            }
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row * 4 + 1]);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    cell = &SVGA_INT[idx * 2];
                    refresh_16x16_partblock(cell[0] + eax * 5 * 128,
                                            ((unsigned short *)cell)[3],
                                            16 - eax);
                }
            }
        } else {
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    eax = refresh_bank_switch_data[row * 4 + 1];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    set_bank(eax);
                    refresh_16x16_block(SVGA_INT[idx * 2],
                                        ((unsigned short *)&SVGA_INT[idx*2])[2]);
                }
            }
        }
    }
}
""",
    note="int[] with manual offsets (((ushort *)cell)[N])",
)


# ── trial 4: extract bank_off + screen_off into temps before call ─
exp.add(
    "named-temps",
    """
void refresh_svga_screen(void)
{
    int row, col, idx;
    int eax;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row * 4] != 0) {
            int saved_idx = idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    int sc, bk;
                    set_bank(refresh_bank_switch_data[row * 4 + 1] - 1);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    sc = svga_refresh_data[idx].screen_off;
                    bk = svga_refresh_data[idx].bank_off;
                    refresh_16x16_partblock(sc, bk, eax);
                }
            }
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    int sc, sp;
                    set_bank(refresh_bank_switch_data[row * 4 + 1]);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    sc = svga_refresh_data[idx].screen_off;
                    sp = svga_refresh_data[idx].split_off;
                    refresh_16x16_partblock(sc + eax * 5 * 128, sp, 16 - eax);
                }
            }
        } else {
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    eax = refresh_bank_switch_data[row * 4 + 1];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    set_bank(eax);
                    refresh_16x16_block(svga_refresh_data[idx].screen_off,
                                        svga_refresh_data[idx].bank_off);
                }
            }
        }
    }
}
""",
    note="named temps (sc, bk, sp) for fields read before call",
)


# ── trial 5: idx*8 cast to char* base, byte-offset accesses ─────
exp.add(
    "char-base",
    """
void refresh_svga_screen(void)
{
    int row, col, idx;
    int eax;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row * 4] != 0) {
            int saved_idx = idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row * 4 + 1] - 1);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    refresh_16x16_partblock(
                        *(int *)((char *)svga_refresh_data + idx * 8),
                        *(unsigned short *)((char *)svga_refresh_data + idx * 8 + 4),
                        eax);
                }
            }
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row * 4 + 1]);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    refresh_16x16_partblock(
                        *(int *)((char *)svga_refresh_data + idx * 8) + eax * 5 * 128,
                        *(unsigned short *)((char *)svga_refresh_data + idx * 8 + 6),
                        16 - eax);
                }
            }
        } else {
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    eax = refresh_bank_switch_data[row * 4 + 1];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    set_bank(eax);
                    refresh_16x16_block(
                        *(int *)((char *)svga_refresh_data + idx * 8),
                        *(unsigned short *)((char *)svga_refresh_data + idx * 8 + 4));
                }
            }
        }
    }
}
""",
    note="char* base + manual byte offsets",
)


# ── trial 6: one field cached, the other inline ─────────────────
exp.add(
    "single-cache",
    """
void refresh_svga_screen(void)
{
    int row, col, idx;
    int eax;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row * 4] != 0) {
            int saved_idx = idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    int sc;
                    set_bank(refresh_bank_switch_data[row * 4 + 1] - 1);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    sc = svga_refresh_data[idx].screen_off;
                    refresh_16x16_partblock(sc,
                                            svga_refresh_data[idx].bank_off,
                                            eax);
                }
            }
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    int sc;
                    set_bank(refresh_bank_switch_data[row * 4 + 1]);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    sc = svga_refresh_data[idx].screen_off;
                    refresh_16x16_partblock(sc + eax * 5 * 128,
                                            svga_refresh_data[idx].split_off,
                                            16 - eax);
                }
            }
        } else {
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    int sc;
                    eax = refresh_bank_switch_data[row * 4 + 1];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    set_bank(eax);
                    sc = svga_refresh_data[idx].screen_off;
                    refresh_16x16_block(sc,
                                        svga_refresh_data[idx].bank_off);
                }
            }
        }
    }
}
""",
    note="screen_off cached in local; bank_off/split_off inline",
)


# ── trial 7: bank cached, screen inline ─────────────────────────
exp.add(
    "bank-cache",
    """
void refresh_svga_screen(void)
{
    int row, col, idx;
    int eax;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row * 4] != 0) {
            int saved_idx = idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    unsigned short bk;
                    set_bank(refresh_bank_switch_data[row * 4 + 1] - 1);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    bk = svga_refresh_data[idx].bank_off;
                    refresh_16x16_partblock(svga_refresh_data[idx].screen_off,
                                            bk, eax);
                }
            }
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    unsigned short sp;
                    set_bank(refresh_bank_switch_data[row * 4 + 1]);
                    eax = refresh_bank_switch_data[row * 4 + 2];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    if (col < refresh_bank_switch_data[row * 4 + 3])
                        eax++;
                    sp = svga_refresh_data[idx].split_off;
                    refresh_16x16_partblock(
                        svga_refresh_data[idx].screen_off + eax * 5 * 128,
                        sp, 16 - eax);
                }
            }
        } else {
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    unsigned short bk;
                    eax = refresh_bank_switch_data[row * 4 + 1];
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    set_bank(eax);
                    bk = svga_refresh_data[idx].bank_off;
                    refresh_16x16_block(svga_refresh_data[idx].screen_off,
                                        bk);
                }
            }
        }
    }
}
""",
    note="bank_off/split_off cached; screen_off inline",
)
