"""Battle-map source-shape experiment: remove_figure.

remove_figure is 32 bytes and currently byte-exact.  It proves how a
figure_list struct field references battle_map.
"""

from c2.commands.cgex import Experiment

PRELUDE = r"""
struct battle_cell {
    unsigned char terrain;
    unsigned char figure;
    unsigned char dirty;
    unsigned char arrow;
};
struct figure_rec {
    char _pad0[0x12];
    int map_ref;
    char _pad16[0x58 - 0x16];
};
struct figure_rec_ptr {
    char _pad0[0x12];
    struct battle_cell *map_ptr;
    char _pad16[0x58 - 0x16];
};
extern unsigned char battle_map[];
extern struct battle_cell battle_cells[];
extern struct figure_rec figure_list[];
extern struct figure_rec_ptr figure_ptr_list[];
extern void clear_figure(struct figure_rec *f);
extern void clear_figure_ptr(struct figure_rec_ptr *f);
"""

DEFS = PRELUDE.replace("extern ", "") + r"""
unsigned char battle_map[52 * 52 * 4];
struct battle_cell battle_cells[52 * 52];
struct figure_rec figure_list[256];
struct figure_rec_ptr figure_ptr_list[256];
void clear_figure(struct figure_rec *f) { }
void clear_figure_ptr(struct figure_rec_ptr *f) { }
"""

exp = Experiment(
    name="battle_remove_figure_shape",
    ps_function="remove_figure",
    prelude=PRELUDE,
    extra_defs=DEFS,
)

exp.add(
    "byte-offset-array",
    r"""
void remove_figure(int n)
{
    char zero = 0;
    int ref = figure_list[n].map_ref;
    battle_map[ref + 1] = zero;
    clear_figure(&figure_list[n]);
}
""",
    note="typed figure_list; map_ref byte offset into unsigned char battle_map[]",
)

exp.add(
    "macro-byte-offset",
    r"""
#define BM_FIGURE(p) battle_map[(p) + 1]
void remove_figure(int n)
{
    char zero = 0;
    int ref = figure_list[n].map_ref;
    BM_FIGURE(ref) = zero;
    clear_figure(&figure_list[n]);
}
""",
    note="checked-in BM_FIGURE source shape",
)

exp.add(
    "inline-cast-byte-offset",
    r"""
void remove_figure(int n)
{
    char zero = 0;
    int ref = figure_list[n].map_ref;
    ((struct battle_cell *)&battle_map[ref])->figure = zero;
    clear_figure(&figure_list[n]);
}
""",
    note="byte offset with struct field lvalue via inline cast",
)

exp.add(
    "cached-cell-pointer",
    r"""
void remove_figure(int n)
{
    char zero = 0;
    int ref = figure_list[n].map_ref;
    struct battle_cell *cell = (struct battle_cell *)&battle_map[ref];
    cell->figure = zero;
    clear_figure(&figure_list[n]);
}
""",
    note="cached pointer to selected battle cell",
)

exp.add(
    "struct-index",
    r"""
void remove_figure(int n)
{
    char zero = 0;
    int ref = figure_list[n].map_ref;
    battle_cells[ref].figure = zero;
    clear_figure(&figure_list[n]);
}
""",
    note="map_ref interpreted as struct-cell index",
)

exp.add(
    "pointer-field",
    r"""
void remove_figure(int n)
{
    char zero = 0;
    struct battle_cell *cell = figure_ptr_list[n].map_ptr;
    cell->figure = zero;
    clear_figure_ptr(&figure_ptr_list[n]);
}
""",
    note="figure stores direct battle_cell pointer",
)
