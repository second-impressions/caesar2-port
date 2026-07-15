"""Tiny region_map source-shape experiment: act_select_farm.

act_select_farm is only 39 bytes and currently byte-exact.  It is a good
probe for whether PS source used byte offsets, pointers, or struct indices.
"""

from c2.commands.cgex import Experiment

PRELUDE = r"""
struct region_cell {
    unsigned char kind;
    unsigned char terrain;
    unsigned char place_state;
    unsigned char edge_bits;
    unsigned char gfx;
    unsigned char _pad5;
    unsigned char outside;
    unsigned char occupant;
};
extern int pm_over_cm_ptr;
extern int para1;
extern int get_region_2x2_start(int cm_ptr);
extern struct region_cell *get_region_2x2_ptr(int cm_ptr);
extern int get_region_2x2_idx(int cm_ptr);
"""

DEFS = r"""
struct region_cell {
    unsigned char kind;
    unsigned char terrain;
    unsigned char place_state;
    unsigned char edge_bits;
    unsigned char gfx;
    unsigned char _pad5;
    unsigned char outside;
    unsigned char occupant;
};
unsigned char region_map[60 * 60 * 8];
struct region_cell region_cells[60 * 60];
int pm_over_cm_ptr;
int para1;
int get_region_2x2_start(int cm_ptr) { return cm_ptr; }
struct region_cell *get_region_2x2_ptr(int cm_ptr) { return &region_cells[cm_ptr]; }
int get_region_2x2_idx(int cm_ptr) { return cm_ptr; }
"""

exp = Experiment(
    name="region_act_select_shape",
    ps_function="act_select_farm",
    prelude=PRELUDE,
    extra_defs=DEFS,
)

exp.add(
    "byte-offset-array",
    r"""
extern unsigned char region_map[];
void act_select_farm(void)
{
    int off = get_region_2x2_start(pm_over_cm_ptr);
    region_map[off + 7] &= 0x0f;
    para1 <<= 4;
    region_map[off + 7] |= (unsigned char)para1;
}
""",
    note="byte offset into unsigned char region_map[]",
)

exp.add(
    "macro-byte-offset",
    r"""
extern unsigned char region_map[];
#define RM_OCCUPANT(p) region_map[(p) + 7]
void act_select_farm(void)
{
    int off = get_region_2x2_start(pm_over_cm_ptr);
    RM_OCCUPANT(off) &= 0x0f;
    para1 <<= 4;
    RM_OCCUPANT(off) |= (unsigned char)para1;
}
""",
    note="current RM_OCCUPANT macro spelling",
)

exp.add(
    "inline-cast-byte-offset",
    r"""
extern unsigned char region_map[];
void act_select_farm(void)
{
    int off = get_region_2x2_start(pm_over_cm_ptr);
    ((struct region_cell *)&region_map[off])->occupant &= 0x0f;
    para1 <<= 4;
    ((struct region_cell *)&region_map[off])->occupant |= (unsigned char)para1;
}
""",
    note="byte offset but struct field lvalue via inline cast",
)

exp.add(
    "cached-pointer-returned",
    r"""
void act_select_farm(void)
{
    struct region_cell *rc = get_region_2x2_ptr(pm_over_cm_ptr);
    rc->occupant &= 0x0f;
    para1 <<= 4;
    rc->occupant |= (unsigned char)para1;
}
""",
    note="helper returns a pointer to region cell",
)

exp.add(
    "struct-index-returned",
    r"""
extern struct region_cell region_cells[];
void act_select_farm(void)
{
    int idx = get_region_2x2_idx(pm_over_cm_ptr);
    region_cells[idx].occupant &= 0x0f;
    para1 <<= 4;
    region_cells[idx].occupant |= (unsigned char)para1;
}
""",
    note="helper returns cell index into struct array",
)

exp.add(
    "manual-div-to-index",
    r"""
extern struct region_cell region_cells[];
void act_select_farm(void)
{
    int off = get_region_2x2_start(pm_over_cm_ptr);
    int idx = off / 8;
    region_cells[idx].occupant &= 0x0f;
    para1 <<= 4;
    region_cells[idx].occupant |= (unsigned char)para1;
}
""",
    note="byte offset returned, then converted to struct index",
)
