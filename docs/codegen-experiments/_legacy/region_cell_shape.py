"""Region map source-shape experiment for put_reg_x1_area.

Tests plausible source forms for Caesar II's 8-byte region-map cells:
raw byte offsets, struct arrays, 2D arrays, array-of-8-byte cells, and cached
pointers.  Compare each to the real PS.EXE put_reg_x1_area.
"""

from c2.commands.cgex import Experiment

PRELUDE = r"""
#define REGION_W 60
#define REGION_CELL_BYTES 8

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

extern int start_x_pos;
extern int start_y_pos;
extern int start_sptr;
extern int cm_sptr;
extern int particles_built;
extern int particles_cleared;
extern unsigned char reg_placing_flags;
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

int start_x_pos;
int start_y_pos;
int start_sptr;
int cm_sptr;
int particles_built;
int particles_cleared;
unsigned char reg_placing_flags;
unsigned char region_map[60 * 60 * 8];
struct region_cell region_cells[60 * 60];
struct region_cell region_2d[60][60];
unsigned char region_3d[60][60][8];
unsigned char region_cell_bytes[60 * 60][8];
"""

exp = Experiment(
    name="region_cell_shape",
    ps_function="put_reg_x1_area",
    prelude=PRELUDE,
    extra_defs=DEFS,
)


def fn_body(setup: str, terrain: str, occupant: str, kind: str, edge: str,
            gfx: str, note_expr: str = "") -> str:
    """Emit the common put_reg_x1_area body for a source-shape trial."""
    return f"""
int put_reg_x1_area(int x, int y, int base_kind, int edge_bits,
                    int color, int strict_flags)
{{
    int off;
    int flags;
    unsigned char old_kind;
{setup}

    start_x_pos = x;
    start_y_pos = y;
{note_expr}    start_sptr = off;
    cm_sptr = off;

    flags = {terrain};
    if (strict_flags == 1) {{
        if ((flags & 0x3f) != 0) return 0;
    }} else {{
        if (flags != 0) return 0;
    }}
    if ({occupant} != 0) return 0;

    old_kind = {kind};
    particles_built++;
    if (old_kind < 0x10) particles_cleared++;
    {edge} |= 1;
    {kind} = (unsigned char)base_kind;
    {terrain} |= (unsigned char)reg_placing_flags;
    {gfx} = (unsigned char)color;
    {edge} &= 0xe3;
    {edge} |= (unsigned char)edge_bits;
    {edge} &= 0xbf;
    {occupant} = 0;
    return 1;
}}
"""


exp.add(
    "byte-array",
    "extern unsigned char region_map[];\n" + fn_body(
        "", "region_map[off + 1]", "region_map[off + 7]",
        "region_map[off]", "region_map[off + 3]", "region_map[off + 4]",
        "    off = (y * 60 + x) * 8;\n",
    ),
    note="raw unsigned char[] with byte offset",
)

exp.add(
    "macro-byte-array",
    r"""
extern unsigned char region_map[];
#define RM_OFF(x, y) (((y) * REGION_W + (x)) * REGION_CELL_BYTES)
#define RM_KIND(p) region_map[(p)]
#define RM_TERRAIN(p) region_map[(p) + 1]
#define RM_EDGE_BITS(p) region_map[(p) + 3]
#define RM_GFX(p) region_map[(p) + 4]
#define RM_OCCUPANT(p) region_map[(p) + 7]
""" + fn_body(
        "", "RM_TERRAIN(off)", "RM_OCCUPANT(off)",
        "RM_KIND(off)", "RM_EDGE_BITS(off)", "RM_GFX(off)",
        "    off = RM_OFF(x, y);\n",
    ),
    note="current RM_* macro spelling",
)

exp.add(
    "struct-array-index",
    "extern struct region_cell region_cells[];\n" + fn_body(
        "    int idx;",
        "region_cells[idx].terrain", "region_cells[idx].occupant",
        "region_cells[idx].kind", "region_cells[idx].edge_bits",
        "region_cells[idx].gfx",
        "    idx = y * 60 + x;\n    off = idx * 8;\n",
    ),
    note="array of structs indexed by cell index",
)

exp.add(
    "struct-array-recompute",
    "extern struct region_cell region_cells[];\n" + fn_body(
        "",
        "region_cells[y * 60 + x].terrain", "region_cells[y * 60 + x].occupant",
        "region_cells[y * 60 + x].kind", "region_cells[y * 60 + x].edge_bits",
        "region_cells[y * 60 + x].gfx",
        "    off = (y * 60 + x) * 8;\n",
    ),
    note="array of structs, no idx local",
)

exp.add(
    "struct-2d",
    "extern struct region_cell region_2d[60][60];\n" + fn_body(
        "",
        "region_2d[y][x].terrain", "region_2d[y][x].occupant",
        "region_2d[y][x].kind", "region_2d[y][x].edge_bits",
        "region_2d[y][x].gfx",
        "    off = (y * 60 + x) * 8;\n",
    ),
    note="2D array of structs, natural source form",
)

exp.add(
    "char-3d",
    "extern unsigned char region_3d[60][60][8];\n" + fn_body(
        "",
        "region_3d[y][x][1]", "region_3d[y][x][7]",
        "region_3d[y][x][0]", "region_3d[y][x][3]", "region_3d[y][x][4]",
        "    off = (y * 60 + x) * 8;\n",
    ),
    note="unsigned char region[y][x][field]",
)

exp.add(
    "cell-bytes-index",
    "extern unsigned char region_cell_bytes[][8];\n" + fn_body(
        "    int idx;",
        "region_cell_bytes[idx][1]", "region_cell_bytes[idx][7]",
        "region_cell_bytes[idx][0]", "region_cell_bytes[idx][3]",
        "region_cell_bytes[idx][4]",
        "    idx = y * 60 + x;\n    off = idx * 8;\n",
    ),
    note="array of 8-byte records, manual field constants",
)

exp.add(
    "byte-offset-inline-cast",
    "extern unsigned char region_map[];\n" + fn_body(
        "",
        "((struct region_cell *)&region_map[off])->terrain",
        "((struct region_cell *)&region_map[off])->occupant",
        "((struct region_cell *)&region_map[off])->kind",
        "((struct region_cell *)&region_map[off])->edge_bits",
        "((struct region_cell *)&region_map[off])->gfx",
        "    off = (y * 60 + x) * 8;\n",
    ),
    note="byte offset but struct lvalues via inline casts",
)

exp.add(
    "byte-offset-pointer",
    "extern unsigned char region_map[];\n" + fn_body(
        "    struct region_cell *rc;",
        "rc->terrain", "rc->occupant", "rc->kind", "rc->edge_bits", "rc->gfx",
        "    off = (y * 60 + x) * 8;\n    rc = (struct region_cell *)&region_map[off];\n",
    ),
    note="cached pointer to byte-offset cell",
)

exp.add(
    "struct-pointer-index",
    "extern struct region_cell region_cells[];\n" + fn_body(
        "    int idx;\n    struct region_cell *rc;",
        "rc->terrain", "rc->occupant", "rc->kind", "rc->edge_bits", "rc->gfx",
        "    idx = y * 60 + x;\n    off = idx * 8;\n    rc = &region_cells[idx];\n",
    ),
    note="cached pointer to struct-array element",
)
