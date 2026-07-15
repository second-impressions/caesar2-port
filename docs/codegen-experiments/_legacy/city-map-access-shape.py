"""city_map source-shape probe: packed-byte cell spelling.

Question: what C spelling would a 1995 programmer plausibly use for a
20-byte packed city cell, and how does Watcom 10.0a lower it?

Run:
    uv run c2 cgex run city-map-access-shape
    uv run c2 cgex run city-map-access-shape --trial ptr_local_fields

The key distinction is whether the cell base is materialized in a pointer local
(`cell = &city_map[cm_sptr]`) or whether each field access remains a direct
`city_map[cm_sptr + FIELD]` expression (possibly hidden behind a macro).  Direct
forms let Watcom fold `city_map + FIELD` into the memory operand; pointer forms
keep the cell base in a register and change pressure/alias shape.
"""

from c2.commands.cgex import Experiment

PRELUDE = r"""
unsigned char city_map[128000];
int cm_sptr;
int acc;
void usep(unsigned char *p);
int helper(unsigned char *p, int n);
"""

exp = Experiment(
    name="city-map-access-shape",
    prelude=PRELUDE,
    extra_defs="""
void usep(unsigned char *p) { (void)p; }
int helper(unsigned char *p, int n) { (void)p; return n; }
""",
)

exp.add(
    "direct_fields",
    r"""
void g(void) {
    int k;
    k = city_map[cm_sptr];
    acc += city_map[cm_sptr + 9];
    city_map[cm_sptr + 9] = (acc + k) & 0xf;
    city_map[cm_sptr + 3] |= 1;
}
""",
    note="direct byte-offset fields: city_map[cm_sptr+N]",
)

exp.add(
    "macro_fields",
    r"""
#define CM(n) city_map[cm_sptr + (n)]
void g(void) {
    int k;
    k = CM(0);
    acc += CM(9);
    CM(9) = (acc + k) & 0xf;
    CM(3) |= 1;
}
""",
    note="macro spelling expands to direct byte-offset fields",
)

exp.add(
    "ptr_local_fields",
    r"""
void g(void) {
    int k;
    unsigned char *cell;
    cell = &city_map[cm_sptr];
    k = cell[0];
    acc += cell[9];
    cell[9] = (acc + k) & 0xf;
    cell[3] |= 1;
}
""",
    note="cached unsigned char *cell = &city_map[cm_sptr]",
)

exp.add(
    "struct_inline_cast",
    r"""
struct cell { unsigned char f0,f1,f2,f3,f4,f5,f6,f7,f8,f9; };
void g(void) {
    int k;
    k = ((struct cell *)&city_map[cm_sptr])->f0;
    acc += ((struct cell *)&city_map[cm_sptr])->f9;
    ((struct cell *)&city_map[cm_sptr])->f9 = (acc + k) & 0xf;
    ((struct cell *)&city_map[cm_sptr])->f3 |= 1;
}
""",
    note="inline struct cast at each use",
)

exp.add(
    "struct_ptr_local",
    r"""
struct cell { unsigned char f0,f1,f2,f3,f4,f5,f6,f7,f8,f9; };
void g(void) {
    int k;
    struct cell *cell;
    cell = (struct cell *)&city_map[cm_sptr];
    k = cell->f0;
    acc += cell->f9;
    cell->f9 = (acc + k) & 0xf;
    cell->f3 |= 1;
}
""",
    note="cached struct cell *cell",
)

exp.add(
    "struct_array_index",
    r"""
struct cell { unsigned char f0,f1,f2,f3,f4,f5,f6,f7,f8,f9; unsigned char rest[10]; };
struct cell city_cells[6400];
int cell_idx;
void g(void) {
    int k;
    k = city_cells[cell_idx].f0;
    acc += city_cells[cell_idx].f9;
    city_cells[cell_idx].f9 = (acc + k) & 0xf;
    city_cells[cell_idx].f3 |= 1;
}
""",
    note="natural struct-array indexed by cell number (compiler must scale by 20)",
)

exp.add(
    "row_col_expr",
    r"""
void g(int x, int y) {
    int off;
    int k;
    off = (x + y * 80) * 20;
    k = city_map[off];
    acc += city_map[off + 9];
    city_map[off + 9] = (acc + k) & 0xf;
    city_map[off + 3] |= 1;
}
""",
    note="natural x/y -> byte offset local, then direct fields",
)

exp.add(
    "row_col_ptr",
    r"""
void g(int x, int y) {
    int k;
    unsigned char *cell;
    cell = &city_map[(x + y * 80) * 20];
    k = cell[0];
    acc += cell[9];
    cell[9] = (acc + k) & 0xf;
    cell[3] |= 1;
}
""",
    note="natural x/y -> cached cell pointer",
)

exp.add(
    "helper_ptr_needed",
    r"""
void g(void) {
    unsigned char *cell;
    cell = &city_map[cm_sptr];
    acc += helper(cell, 4);
    acc += helper(cell, 2);
    cell[9] = acc & 0xf;
}
""",
    note="pointer is semantically passed to helpers (query/coverage style)",
)

exp.add(
    "helper_direct_addr",
    r"""
void g(void) {
    acc += helper(&city_map[cm_sptr], 4);
    acc += helper(&city_map[cm_sptr], 2);
    city_map[cm_sptr + 9] = acc & 0xf;
}
""",
    note="recompute &city_map[cm_sptr] at each helper call",
)
