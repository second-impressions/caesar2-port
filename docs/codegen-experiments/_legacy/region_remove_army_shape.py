"""Tiny mixed-struct/region source-shape experiment: remove_army.

remove_army is 35 bytes and currently byte-exact.  It mixes a real typed
army_rec access with a region_map occupant write, making it a good probe for
whether army.map_ref is a byte offset, a struct index, or a pointer.
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

struct army_rec {
    char _pad0[8];
    int map_ref;
    char _pad12[0xaf - 12];
};

struct army_rec_ptr {
    char _pad0[8];
    struct region_cell *map_ptr;
    char _pad12[0xaf - 12];
};

extern unsigned char region_map[];
extern struct region_cell region_cells[];
extern struct army_rec army_list[];
extern struct army_rec_ptr army_ptr_list[];
extern void clear_army(struct army_rec *a);
extern void clear_army_ptr(struct army_rec_ptr *a);
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

struct army_rec {
    char _pad0[8];
    int map_ref;
    char _pad12[0xaf - 12];
};

struct army_rec_ptr {
    char _pad0[8];
    struct region_cell *map_ptr;
    char _pad12[0xaf - 12];
};

unsigned char region_map[60 * 60 * 8];
struct region_cell region_cells[60 * 60];
struct army_rec army_list[100];
struct army_rec_ptr army_ptr_list[100];
void clear_army(struct army_rec *a) { }
void clear_army_ptr(struct army_rec_ptr *a) { }
"""

exp = Experiment(
    name="region_remove_army_shape",
    ps_function="remove_army",
    prelude=PRELUDE,
    extra_defs=DEFS,
)

exp.add(
    "byte-offset-array",
    r"""
void remove_army(int n)
{
    char zero = 0;
    int ref = army_list[n].map_ref;
    region_map[ref + 7] = zero;
    clear_army(&army_list[n]);
}
""",
    note="typed army_list, map_ref is byte offset into unsigned char region_map[]",
)

exp.add(
    "macro-byte-offset",
    r"""
#define RM_OCCUPANT(p) region_map[(p) + 7]
void remove_army(int n)
{
    char zero = 0;
    int ref = army_list[n].map_ref;
    RM_OCCUPANT(ref) = zero;
    clear_army(&army_list[n]);
}
""",
    note="checked-in source shape",
)

exp.add(
    "inline-cast-byte-offset",
    r"""
void remove_army(int n)
{
    char zero = 0;
    int ref = army_list[n].map_ref;
    ((struct region_cell *)&region_map[ref])->occupant = zero;
    clear_army(&army_list[n]);
}
""",
    note="byte offset, field lvalue via inline cast",
)

exp.add(
    "cached-region-pointer",
    r"""
void remove_army(int n)
{
    char zero = 0;
    int ref = army_list[n].map_ref;
    struct region_cell *rc = (struct region_cell *)&region_map[ref];
    rc->occupant = zero;
    clear_army(&army_list[n]);
}
""",
    note="map_ref byte offset, then cached region_cell pointer",
)

exp.add(
    "struct-index",
    r"""
void remove_army(int n)
{
    char zero = 0;
    int ref = army_list[n].map_ref;
    region_cells[ref].occupant = zero;
    clear_army(&army_list[n]);
}
""",
    note="map_ref interpreted as struct-cell index",
)

exp.add(
    "map-ref-pointer-field",
    r"""
void remove_army(int n)
{
    char zero = 0;
    struct region_cell *rc = army_ptr_list[n].map_ptr;
    rc->occupant = zero;
    clear_army_ptr(&army_ptr_list[n]);
}
""",
    note="army stores direct pointer to region cell",
)

exp.add(
    "no-zero-local",
    r"""
void remove_army(int n)
{
    int ref = army_list[n].map_ref;
    region_map[ref + 7] = 0;
    clear_army(&army_list[n]);
}
""",
    note="same byte-offset source without explicit zero local",
)
