"""Battle-map source-shape experiment: clear_all_highlights_from_battlemap.

This exact 84-byte grid scan tests whether direct byte-offset access, inline
struct casts, cached pointers, or struct indices match PS.EXE's loop shape.
"""

from c2.commands.cgex import Experiment

PRELUDE = r"""
struct battle_cell {
    unsigned char terrain;
    unsigned char figure;
    unsigned char dirty;
    unsigned char arrow;
};
extern int gmn_y;
extern int gmn_x;
extern int cm_sptr;
extern unsigned char battle_map[];
extern struct battle_cell battle_cells[];
"""

DEFS = r"""
struct battle_cell {
    unsigned char terrain;
    unsigned char figure;
    unsigned char dirty;
    unsigned char arrow;
};
int gmn_y;
int gmn_x;
int cm_sptr;
unsigned char battle_map[52 * 52 * 4];
struct battle_cell battle_cells[52 * 52];
"""

exp = Experiment(
    name="battle_highlight_shape",
    ps_function="clear_all_highlights_from_battlemap",
    prelude=PRELUDE,
    extra_defs=DEFS,
)

exp.add(
    "byte-offset-array",
    r"""
void clear_all_highlights_from_battlemap(void)
{
    gmn_y   = 0;
    cm_sptr = 0;
    goto outer_test;
outer_loop:
    gmn_x = 0;
    do {
        battle_map[cm_sptr + 2] &= 0xf3;
        gmn_x++;
        cm_sptr += 4;
    } while (gmn_x < 0x34);
    gmn_y++;
outer_test:
    if (gmn_y < 0x34) goto outer_loop;
}
""",
    note="byte offset into unsigned char battle_map[]",
)

exp.add(
    "macro-bm-dirty",
    r"""
#define BM_DIRTY(p) battle_map[(p) + 2]
void clear_all_highlights_from_battlemap(void)
{
    gmn_y   = 0;
    cm_sptr = 0;
    goto outer_test;
outer_loop:
    gmn_x = 0;
    do {
        BM_DIRTY(cm_sptr) &= 0xf3;
        gmn_x++;
        cm_sptr += 4;
    } while (gmn_x < 0x34);
    gmn_y++;
outer_test:
    if (gmn_y < 0x34) goto outer_loop;
}
""",
    note="BM_DIRTY macro spelling",
)

exp.add(
    "inline-bcell",
    r"""
#define BCELL(p) (*(struct battle_cell *)&battle_map[(p)])
void clear_all_highlights_from_battlemap(void)
{
    gmn_y   = 0;
    cm_sptr = 0;
    goto outer_test;
outer_loop:
    gmn_x = 0;
    do {
        BCELL(cm_sptr).dirty &= 0xf3;
        gmn_x++;
        cm_sptr += 4;
    } while (gmn_x < 0x34);
    gmn_y++;
outer_test:
    if (gmn_y < 0x34) goto outer_loop;
}
""",
    note="checked-in BCELL inline-cast field access",
)

exp.add(
    "cached-pointer",
    r"""
void clear_all_highlights_from_battlemap(void)
{
    gmn_y   = 0;
    cm_sptr = 0;
    goto outer_test;
outer_loop:
    gmn_x = 0;
    do {
        struct battle_cell *cell = (struct battle_cell *)&battle_map[cm_sptr];
        cell->dirty &= 0xf3;
        gmn_x++;
        cm_sptr += 4;
    } while (gmn_x < 0x34);
    gmn_y++;
outer_test:
    if (gmn_y < 0x34) goto outer_loop;
}
""",
    note="cached pointer inside loop",
)

exp.add(
    "struct-index",
    r"""
void clear_all_highlights_from_battlemap(void)
{
    int idx;
    gmn_y = 0;
    idx = 0;
    cm_sptr = 0;
    goto outer_test;
outer_loop:
    gmn_x = 0;
    do {
        battle_cells[idx].dirty &= 0xf3;
        gmn_x++;
        idx++;
        cm_sptr += 4;
    } while (gmn_x < 0x34);
    gmn_y++;
outer_test:
    if (gmn_y < 0x34) goto outer_loop;
}
""",
    note="separate struct cell index plus legacy cm_sptr side effect",
)
