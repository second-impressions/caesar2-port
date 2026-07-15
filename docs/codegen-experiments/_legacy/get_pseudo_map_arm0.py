"""get_pseudo_map — sprite-ring arm address-factoring (Form D vs B vs L).

The ring at the top of get_pseudo_map writes a sprite tile index into
``pseudo_map[row][col]`` from an 8-way if/else-if chain.  Watcom emits
the address ``base + row*0x144 + col*4`` in one of three forms per arm:

  D  row-chain built in-place in EDX, col plain in EAX, [edx + eax*4]
  B  row*0x51 in EAX (scaled *4 via SIB), col*4 explicit in EDX
  L  Form-D result but row-chain built in EAX then `lea edx,[ecx+eax]`
     (18 bytes — one byte longer than D/B, hence the cascade)

PS's per-arm forms (0..7): D, B, L, B, B, B, D, B.

The whole-TU build with the original declaration order picks L for arms
0,1,4 (the +1-byte cascade -> 847 byte diff).  A declaration-order sweep
(named locals are dealt FRL slots before the anonymous arm temps, so
decl order steers the arm temps' ConfBefore tie-break) drives every arm
to PS's form EXCEPT arm0, which sticks on Form B where PS wants D.

This experiment isolates the arm0 chain-temp-vs-col-temp EAX tie so it
can be iterated quickly (cgex builds are cached/sub-second vs ~8 s for a
full-TU verify).  ``--trial <name>`` dumps the disasm + diff-vs-PS.

    uv run c2 cgex run get_pseudo_map_arm0
    uv run c2 cgex run get_pseudo_map_arm0 --trial baseline

SOLVED (2026-06): cgex was the fast oracle here.  A standalone build of
get_pseudo_map reproduces the whole-TU result exactly (Watcom resets its
name arena per routine), so an in-process cgex sweep over the 12!
declaration orderings could be run at ~0.2 s/build.  Findings:

* The `orig` decl order diffs 847 b (whole-TU) / 872 b (standalone): arms
  0,1,4 pick Form L (+1 byte each -> alignment cascade).
* A decl-order sweep drives 7/8 arms to PS's form but plateaus at 10 b
  with arm0 stuck on Form B (`p10`); 500 random orders never beat 10 in
  that basin -- arm0=B and arm0=D are SEPARATE basins.
* arm0=D IS reachable (~4% of random orders) but those break other arms.
* Hill-climbing (single-swap) from an arm0=D / diff-10 seed reached the
  byte-exact order `win` below.

Forms D and B are equal cost (both 17 b, 7 ops); the per-arm choice is a
pure GiveBestReg/ConfBefore tie, and declaration order is the only lever
that reaches it (it deals FRL name slots before the anonymous arm temps).
The winning order is committed in decomp/src/pm_map0.c.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern int  pseudo_map[161][81];
extern int  map_direction;
extern int  map_actual_atom;
extern int  map_actual_height;
extern int  map_actual_width;
extern int  map_height_reduction;
extern int  map_width_reduction;
extern char map_mode;
"""

_DEFS = """
int  pseudo_map[161][81];
int  map_direction;
int  map_actual_atom;
int  map_actual_height;
int  map_actual_width;
int  map_height_reduction;
int  map_width_reduction;
char map_mode;
"""

exp = Experiment(
    name="get_pseudo_map_arm0",
    ps_function="get_pseudo_map",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


def _body(decls: str, ring: str | None = None) -> str:
    RING = ring or """
            if (col_edge < 4 && row_edge < 8) {
                pseudo_map[row][col] = 0x0FFF0000;
            } else if (col_edge < 8 && row_edge < 0x10) {
                pseudo_map[row][col] = 0x0FFF0000 | 1;
            } else if (col_edge < 0xc && row_edge < 0x18) {
                pseudo_map[row][col] = 0x0FFF0000 | 2;
            } else if (col_edge < 0x10 && row_edge < 0x20) {
                pseudo_map[row][col] = 0x0FFF0000 | 3;
            } else if (col_edge < 0x13 && row_edge < 0x28) {
                pseudo_map[row][col] = 0x0FFF0000 | 4;
            } else if (col_edge < 0x1c && row_edge < 0x14) {
                pseudo_map[row][col] = 0x0FFF0000 | 5;
            } else if (col_edge < 8 && row_edge < 0x3c) {
                pseudo_map[row][col] = 0x0FFF0000 | 6;
            } else {
                pseudo_map[row][col] = 0x0FFF0000 | 7;
            }"""
    return f"""
void get_pseudo_map(int direction)
{{
{decls}

    for (row = 0; row < 0xa1; row++) {{
        for (col = 0; col < 0x51; col++) {{
            if (row <= 0x50) row_edge = row; else row_edge = 0xa0 - row;
            if (col <= 0x28) col_edge = col; else col_edge = 0x50 - col;
{RING}
        }}
    }}

    map_direction = direction;
    if (direction == 0) {{
        start_row = map_height_reduction * 2 + 1;
        row_step = 1;
        col_row_step = 1;
        start_x2 = 0x50;
        x2_step = -1;
        col_x2_step = 1;
    }} else if (direction == 2) {{
        start_row = 0x50;
        row_step = 1;
        col_row_step = -1;
        start_x2 = map_width_reduction * 2 + 1;
        x2_step = 1;
        col_x2_step = 1;
    }} else if (direction == 4) {{
        start_row = (0x50 - map_height_reduction) * 2 - 1;
        row_step = -1;
        col_row_step = -1;
        start_x2 = 0x50;
        x2_step = 1;
        col_x2_step = -1;
    }} else if (direction == 6) {{
        start_row = 0x50;
        row_step = -1;
        col_row_step = 1;
        start_x2 = (0x50 - map_width_reduction) * 2 - 1;
        x2_step = -1;
        col_x2_step = -1;
    }}

    for (row = 0; row < map_actual_height; row++) {{
        pr = start_row;
        px2 = start_x2;
        for (col = 0; col < map_actual_width; col++) {{
            pseudo_map[pr][px2 / 2] = map_actual_atom * (map_actual_width * row + col);
            pr += col_row_step;
            px2 += col_x2_step;
        }}
        start_row += row_step;
        start_x2 += x2_step;
    }}

    start_row = map_height_reduction * 2 + 1;
    start_x2 = 0x50;
    for (row = 0; row < 0x50 - map_height_reduction * 2; row++) {{
        pr = start_row;
        px2 = start_x2;
        for (col = 0; col < map_actual_width; col++) {{
            pr++;
            px2++;
        }}
        pseudo_map[pr][px2 / 2] = 0x0FFF0000 | 0x9;
        start_row++;
        start_x2--;
    }}
    if (map_mode > 0) {{
        pr = start_row;
        px2 = start_x2;
        for (col = 0; col < map_actual_width; col++) {{
            pr++;
            px2++;
        }}
        pseudo_map[pr][px2 / 2] = 0x0FFF0000 | 0xa;
    }}
    pr = start_row;
    px2 = start_x2;
    for (col = 0; col < 0x50 - map_width_reduction * 2; col++) {{
        pseudo_map[pr][px2 / 2] = 0x0FFF0000 | 0x8;
        pr++;
        px2++;
    }}
}}
"""


def _decls(order: list[str]) -> str:
    return "\n".join(f"    int {n};" for n in order)


# original declaration order (whole-TU baseline: 847 b)
_ORIG = ["row", "col", "col_edge", "row_edge", "start_row", "x2_step",
         "start_x2", "row_step", "col_row_step", "col_x2_step", "pr", "px2"]

# P10: decl-order sweep result — every arm matches PS except arm0 (10 b)
_P10 = ["start_row", "row", "start_x2", "px2", "row_step", "col",
        "col_edge", "pr", "col_x2_step", "x2_step", "row_edge", "col_row_step"]

# WIN: byte-exact decl order (arm0=D + all spill slots correct) -- committed
_WIN = ["col_x2_step", "x2_step", "start_row", "row", "start_x2",
        "col_row_step", "col_edge", "row_step", "pr", "row_edge", "px2", "col"]

exp.add("orig", _body(_decls(_ORIG)), note="original decl order (whole-TU: 847 b)")
exp.add("p10", _body(_decls(_P10)), note="decl sweep: only arm0 wrong (10 b)")
exp.add("win", _body(_decls(_WIN)), note="byte-exact decl order (committed)")

# ── arm0 levers (all on the P10 decl order) ──────────────────────────────────
_P10s = _decls(_P10)

# edge as assign-then-conditional-override
exp.add("p10_edge_override", _body(_P10s, ring=None).replace(
    "            if (row <= 0x50) row_edge = row; else row_edge = 0xa0 - row;\n"
    "            if (col <= 0x28) col_edge = col; else col_edge = 0x50 - col;",
    "            row_edge = row;\n            if (row > 0x50) row_edge = 0xa0 - row;\n"
    "            col_edge = col;\n            if (col > 0x28) col_edge = 0x50 - col;"),
    note="edges: assign-then-override")

# edge ternary
exp.add("p10_edge_tern", _body(_P10s).replace(
    "            if (row <= 0x50) row_edge = row; else row_edge = 0xa0 - row;\n"
    "            if (col <= 0x28) col_edge = col; else col_edge = 0x50 - col;",
    "            row_edge = (row <= 0x50) ? row : 0xa0 - row;\n"
    "            col_edge = (col <= 0x28) ? col : 0x50 - col;"),
    note="edges: ternary")

# edges computed col first
exp.add("p10_edge_colfirst", _body(_P10s).replace(
    "            if (row <= 0x50) row_edge = row; else row_edge = 0xa0 - row;\n"
    "            if (col <= 0x28) col_edge = col; else col_edge = 0x50 - col;",
    "            if (col <= 0x28) col_edge = col; else col_edge = 0x50 - col;\n"
    "            if (row <= 0x50) row_edge = row; else row_edge = 0xa0 - row;"),
    note="edges: col before row")

# all arms condition row first (row_edge < K2 && col_edge < K)
def _ring_rowfirst():
    pairs=[(4,8,0),(8,0x10,1),(0xc,0x18,2),(0x10,0x20,3),(0x13,0x28,4),
           (0x1c,0x14,5),(8,0x3c,6)]
    lines=[]
    for i,(c,r,k) in enumerate(pairs):
        kw="if" if i==0 else "} else if"
        val="0x0FFF0000" if k==0 else f"0x0FFF0000 | {k}"
        lines.append(f"            {kw} (row_edge < {hex(r)} && col_edge < {hex(c)}) {{\n                pseudo_map[row][col] = {val};")
    lines.append("            } else {\n                pseudo_map[row][col] = 0x0FFF0000 | 7;\n            }")
    return "\n".join(lines)
exp.add("p10_cond_rowfirst", _body(_P10s, ring=_ring_rowfirst()),
        note="arm conditions: row_edge first")
