"""Region map source-shape experiment for clear_reg_basic.

This function is currently byte-exact in the project with RM_* byte-offset
macros.  Test whether plausible struct-shaped source forms remain exact or
regress against PS.EXE.
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
extern char stone_random_data[];
extern char stone_random_count;
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
char stone_random_data[256];
char stone_random_count;
"""

exp = Experiment(
    name="region_clear_basic_shape",
    ps_function="clear_reg_basic",
    prelude=PRELUDE,
    extra_defs=DEFS,
)

exp.add(
    "byte-array",
    r"""
extern unsigned char region_map[];
void clear_reg_basic(int rm_offset)
{
    if (region_map[rm_offset + 1] & 0x40) {
        region_map[rm_offset] = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (region_map[rm_offset + 1] & 0x80) {
        region_map[rm_offset] = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        region_map[rm_offset] = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (region_map[rm_offset + 1] & 1) {
        region_map[rm_offset + 7] = 0;
    }
    region_map[rm_offset + 1] &= 0xd8;
    region_map[rm_offset + 3] &= 2;
    region_map[rm_offset + 5] = 0;
    region_map[rm_offset + 6] = 0;
    region_map[rm_offset + 3] |= 1;
}
""",
    note="current byte-offset shape, macros expanded",
)

exp.add(
    "macro-byte-array",
    r"""
extern unsigned char region_map[];
#define RM_KIND(p) region_map[(p)]
#define RM_TERRAIN(p) region_map[(p) + 1]
#define RM_EDGE_BITS(p) region_map[(p) + 3]
#define RM_OUTSIDE(p) region_map[(p) + 6]
#define RM_OCCUPANT(p) region_map[(p) + 7]
void clear_reg_basic(int rm_offset)
{
    if (RM_TERRAIN(rm_offset) & 0x40) {
        RM_KIND(rm_offset) = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (RM_TERRAIN(rm_offset) & 0x80) {
        RM_KIND(rm_offset) = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        RM_KIND(rm_offset) = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (RM_TERRAIN(rm_offset) & 1) {
        RM_OCCUPANT(rm_offset) = 0;
    }
    RM_TERRAIN(rm_offset) &= 0xd8;
    RM_EDGE_BITS(rm_offset) &= 2;
    RM_KIND(rm_offset + 5) = 0;
    RM_OUTSIDE(rm_offset) = 0;
    RM_EDGE_BITS(rm_offset) |= 1;
}
""",
    note="current checked-in RM_* shape",
)

exp.add(
    "inline-cast",
    r"""
extern unsigned char region_map[];
void clear_reg_basic(int rm_offset)
{
    if (((struct region_cell *)&region_map[rm_offset])->terrain & 0x40) {
        ((struct region_cell *)&region_map[rm_offset])->kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (((struct region_cell *)&region_map[rm_offset])->terrain & 0x80) {
        ((struct region_cell *)&region_map[rm_offset])->kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        ((struct region_cell *)&region_map[rm_offset])->kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (((struct region_cell *)&region_map[rm_offset])->terrain & 1) {
        ((struct region_cell *)&region_map[rm_offset])->occupant = 0;
    }
    ((struct region_cell *)&region_map[rm_offset])->terrain &= 0xd8;
    ((struct region_cell *)&region_map[rm_offset])->edge_bits &= 2;
    ((struct region_cell *)&region_map[rm_offset + 5])->kind = 0;
    ((struct region_cell *)&region_map[rm_offset])->outside = 0;
    ((struct region_cell *)&region_map[rm_offset])->edge_bits |= 1;
}
""",
    note="byte offset but struct field lvalues via casts",
)

exp.add(
    "cached-pointer",
    r"""
extern unsigned char region_map[];
void clear_reg_basic(int rm_offset)
{
    struct region_cell *rc = (struct region_cell *)&region_map[rm_offset];
    if (rc->terrain & 0x40) {
        rc->kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (rc->terrain & 0x80) {
        rc->kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        rc->kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (rc->terrain & 1) {
        rc->occupant = 0;
    }
    rc->terrain &= 0xd8;
    rc->edge_bits &= 2;
    ((struct region_cell *)&region_map[rm_offset + 5])->kind = 0;
    rc->outside = 0;
    rc->edge_bits |= 1;
}
""",
    note="cached pointer to byte-offset cell",
)

exp.add(
    "struct-array-param-index",
    r"""
extern struct region_cell region_cells[];
void clear_reg_basic(int rm_offset)
{
    if (region_cells[rm_offset].terrain & 0x40) {
        region_cells[rm_offset].kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if (region_cells[rm_offset].terrain & 0x80) {
        region_cells[rm_offset].kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        region_cells[rm_offset].kind = (char)(((unsigned char)stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if (region_cells[rm_offset].terrain & 1) {
        region_cells[rm_offset].occupant = 0;
    }
    region_cells[rm_offset].terrain &= 0xd8;
    region_cells[rm_offset].edge_bits &= 2;
    region_cells[rm_offset + 5].kind = 0;
    region_cells[rm_offset].outside = 0;
    region_cells[rm_offset].edge_bits |= 1;
}
""",
    note="treat parameter as struct-array cell index",
)
