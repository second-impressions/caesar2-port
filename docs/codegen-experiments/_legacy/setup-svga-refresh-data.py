"""setup_svga_refresh_data — Watcom recompute pattern.

PS computes `py * 640 + px` TWICE in the inner loop (once via
shifts for `cell[0]`, once via IMUL for the modulo store).
Recomp computes it once via shifts and reuses.  Probe what
source pattern triggers the recompute.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern int  refresh_bank_switch_data[];
extern int  svga_refresh_data[];
extern char svga_refresh_table[];
"""

_DEFS = """
int  refresh_bank_switch_data[120];
int  svga_refresh_data[2400];
char svga_refresh_table[1200];
"""

exp = Experiment(
    name="setup-svga-refresh-data",
    ps_function="setup_svga_refresh_data",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
    externs={
        "__STOSB": (
            'extern void __STOSB(void *dst, int val, unsigned n);\n'
            '#pragma aux __STOSB "*" parm caller [eax] [edx] [ecx] modify [];'
        ),
    },
)


# ── trial 1: baseline (current source) ─────────────────────────
exp.add(
    "baseline",
    """
void setup_svga_refresh_data(void)
{
    int *bank_row;
    int *cell;
    int  py, px, idx;

    __STOSB(svga_refresh_table, 0, 0x4b0);

    idx = 0;
    for (py = 0; py < 0x1e0; py += 0x10) {
        for (px = 0; px < 0x280; px += 0x10) {
            cell = &svga_refresh_data[idx * 2];
            cell[0] = py * 5 * 128 + px;
            ((unsigned short *)cell)[2] =
                (unsigned short)((py * 0x280 + px) % 0x10000);
            ((unsigned short *)cell)[3] = 0;

            bank_row = &refresh_bank_switch_data[(py / 16) * 4];
            if (bank_row[0] != 0) {
                int split_col = bank_row[3];
                if (px >= split_col * 16) {
                    ((unsigned short *)cell)[3] =
                        (unsigned short)(px - split_col * 16);
                } else {
                    ((unsigned short *)cell)[3] =
                        (unsigned short)((40 - split_col) * 16 + px);
                }
            }
            idx++;
        }
    }
}
""",
    note="current source structure",
)


# ── trial 2: indexed access (no cell pointer) ──────────────────
exp.add(
    "no-cell",
    """
void setup_svga_refresh_data(void)
{
    int *bank_row;
    int  py, px, idx;

    __STOSB(svga_refresh_table, 0, 0x4b0);

    idx = 0;
    for (py = 0; py < 0x1e0; py += 0x10) {
        for (px = 0; px < 0x280; px += 0x10) {
            svga_refresh_data[idx * 2] = py * 5 * 128 + px;
            ((unsigned short *)&svga_refresh_data[idx * 2])[2] =
                (unsigned short)((py * 0x280 + px) % 0x10000);
            ((unsigned short *)&svga_refresh_data[idx * 2])[3] = 0;

            bank_row = &refresh_bank_switch_data[(py / 16) * 4];
            if (bank_row[0] != 0) {
                int split_col = bank_row[3];
                if (px >= split_col * 16) {
                    ((unsigned short *)&svga_refresh_data[idx * 2])[3] =
                        (unsigned short)(px - split_col * 16);
                } else {
                    ((unsigned short *)&svga_refresh_data[idx * 2])[3] =
                        (unsigned short)((40 - split_col) * 16 + px);
                }
            }
            idx++;
        }
    }
}
""",
    note="no cell pointer, recompute &svga[idx*2] each access",
)


# ── trial 3: explicit byte offset ──────────────────────────────
exp.add(
    "byte-offset",
    """
void setup_svga_refresh_data(void)
{
    int *bank_row;
    char *cell;
    int  py, px, idx;

    __STOSB(svga_refresh_table, 0, 0x4b0);

    idx = 0;
    for (py = 0; py < 0x1e0; py += 0x10) {
        for (px = 0; px < 0x280; px += 0x10) {
            cell = (char *)&svga_refresh_data[idx * 2];
            *(int *)(cell + 0)            = py * 5 * 128 + px;
            *(unsigned short *)(cell + 4) =
                (unsigned short)((py * 0x280 + px) % 0x10000);
            *(unsigned short *)(cell + 6) = 0;

            bank_row = &refresh_bank_switch_data[(py / 16) * 4];
            if (bank_row[0] != 0) {
                int split_col = bank_row[3];
                if (px >= split_col * 16) {
                    *(unsigned short *)(cell + 6) =
                        (unsigned short)(px - split_col * 16);
                } else {
                    *(unsigned short *)(cell + 6) =
                        (unsigned short)((40 - split_col) * 16 + px);
                }
            }
            idx++;
        }
    }
}
""",
    note="char* cell with byte offsets (cell+0/+4/+6)",
)


# ── trial 4: skip cell pointer, use idx directly with offsets ──
exp.add(
    "explicit-shifts",
    """
void setup_svga_refresh_data(void)
{
    int *bank_row;
    char *cell;
    int  py, px, idx;

    __STOSB(svga_refresh_table, 0, 0x4b0);

    idx = 0;
    for (py = 0; py < 0x1e0; py += 0x10) {
        for (px = 0; px < 0x280; px += 0x10) {
            int screen_off1 = py * 5 * 128 + px;     /* shift form */
            int screen_off2 = py * 0x280   + px;     /* imul form  */
            cell = (char *)&svga_refresh_data[idx * 2];
            *(int *)(cell + 0)            = screen_off1;
            *(unsigned short *)(cell + 4) =
                (unsigned short)(screen_off2 % 0x10000);
            *(unsigned short *)(cell + 6) = 0;

            bank_row = &refresh_bank_switch_data[(py / 16) * 4];
            if (bank_row[0] != 0) {
                int split_col = bank_row[3];
                if (px >= split_col * 16) {
                    *(unsigned short *)(cell + 6) =
                        (unsigned short)(px - split_col * 16);
                } else {
                    *(unsigned short *)(cell + 6) =
                        (unsigned short)((40 - split_col) * 16 + px);
                }
            }
            idx++;
        }
    }
}
""",
    note="two named locals for the two compute forms",
)
