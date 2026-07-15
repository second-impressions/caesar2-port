"""Can `struct city_cell city_map[6400]` emit the SAME bytes as the
`unsigned char city_map[128000]` byte-array form across every access variety?

Baseline (current/PS form) uses unsigned char[].  Each candidate retypes the
global to struct city_cell[] and spells the access so Watcom still folds
`city_map + field` into a disp32 over the byte-offset cursor register.

Compare trial sizes/disasm pairwise: <X>_bytes (baseline) vs <X>_struct.
"""
from c2.commands.cgex import Experiment

# byte-array prelude vs struct prelude share the same cm_sptr/helpers.
BYTES_DECL = "unsigned char city_map[128000];\n"
STRUCT_DECL = ("struct city_cell { unsigned char base_kind,terrain,road_aqueduct,"
               "edge_bits,extra_edge,activity_a,activity_b,citizen_a,citizen_b,"
               "building,range_flag,fpu_flag,entertainment,education,health,"
               "land_value,fire,security,industrial,business; };\n"
               "struct city_cell city_map[6400];\n")
COMMON = "int cm_sptr; int acc; int helper(unsigned char *p, int n);\n"

exp = Experiment(
    name="city-map-struct-decl",
    extra_defs="int helper(unsigned char *p, int n){(void)p;return n;}\n",
)

# ---- read + RMW current cell ----
exp.add("rmw_bytes", BYTES_DECL+COMMON+r"""
void g(void){
    int k = city_map[cm_sptr];
    acc += city_map[cm_sptr + 9];
    city_map[cm_sptr + 9] = (acc + k) & 0xf;
    city_map[cm_sptr + 3] |= 1;
}
""", note="BASELINE unsigned char[] current-cell rmw")

exp.add("rmw_struct", STRUCT_DECL+COMMON+r"""
void g(void){
    int k = ((struct city_cell *)((unsigned char *)city_map + cm_sptr))->base_kind;
    acc += ((struct city_cell *)((unsigned char *)city_map + cm_sptr))->building;
    ((struct city_cell *)((unsigned char *)city_map + cm_sptr))->building = (acc + k) & 0xf;
    ((struct city_cell *)((unsigned char *)city_map + cm_sptr))->edge_bits |= 1;
}
""", note="struct[] + (uchar*)city_map + cm_sptr cast")

# ---- neighbor cells + variable field offset ----
exp.add("neigh_bytes", BYTES_DECL+COMMON+"int field_off;\n"+r"""
void g(void){
    acc += city_map[cm_sptr + 1600 + 1];
    acc += city_map[cm_sptr - 20];
    acc += city_map[cm_sptr + field_off];
}
""", note="BASELINE neighbor + variable offset")

exp.add("neigh_struct", STRUCT_DECL+COMMON+"int field_off;\n"+r"""
void g(void){
    acc += ((unsigned char *)city_map)[cm_sptr + 1600 + 1];
    acc += ((unsigned char *)city_map)[cm_sptr - 20];
    acc += ((unsigned char *)city_map)[cm_sptr + field_off];
}
""", note="struct[] neighbor/var via (uchar*)city_map[...]")

# ---- &city_map[cm_sptr] helper pointer arg ----
exp.add("arg_bytes", BYTES_DECL+COMMON+r"""
void g(void){ acc += helper(&city_map[cm_sptr], 4); }
""", note="BASELINE &city_map[cm_sptr] arg")

exp.add("arg_struct", STRUCT_DECL+COMMON+r"""
void g(void){ acc += helper((unsigned char *)city_map + cm_sptr, 4); }
""", note="struct[] (uchar*)city_map + cm_sptr arg")

# ---- pointer-cursor walk over struct city_cell[] ----
exp.add("walk_bytes", BYTES_DECL+COMMON+r"""
void g(void){
    int o;
    for (o = 0; o < 1600; o += 20) {
        acc += city_map[o + 9];
        city_map[o + 3] |= 1;
        acc += city_map[o + 1600 + 1];
    }
}
""", note="BASELINE byte cursor with south-neighbor")

exp.add("walk_ptr", STRUCT_DECL+COMMON+r"""
void g(void){
    struct city_cell *p;
    for (p = city_map; p < city_map + 80; p++) {
        acc += p->building;
        p->edge_bits |= 1;
        acc += p[80].terrain;
    }
}
""", note="struct city_cell *p walk: p++, p[80].field neighbor")

# ---- macro form over struct city_cell[] vs unsigned char[] baseline ----
MACROS = (
    "#define CITY_ROW 1600\n#define CITY_CELL_BYTES 20\n"
    "#define CM_PTR(off) ((unsigned char *)city_map + (off))\n"
    "#define CM_CELL(off) (*(struct city_cell *)CM_PTR(off))\n"
    "#define CM_FIELD(off,f) (CM_PTR(off)[(f)])\n"
    "#define CM_N (-CITY_ROW)\n#define CM_S (CITY_ROW)\n"
    "#define CM_W (-CITY_CELL_BYTES)\n#define CM_E (CITY_CELL_BYTES)\n"
)

exp.add("macro_baseline", BYTES_DECL+COMMON+"int field_off;\n"+r"""
void g(void){
    int k = city_map[cm_sptr];
    acc += city_map[cm_sptr + 9];
    city_map[cm_sptr + 9] = (acc + k) & 0xf;
    city_map[cm_sptr + 3] |= 1;
    acc += city_map[cm_sptr + 1600 + 1];      /* S terrain   */
    acc += city_map[cm_sptr + 1620 + 1];      /* SE terrain  */
    acc += city_map[cm_sptr + field_off];     /* runtime fld */
    acc += helper(&city_map[cm_sptr], 4);
}
""", note="BASELINE unsigned char[] mixed accesses")

exp.add("macro_form", STRUCT_DECL+COMMON+"int field_off;\n"+MACROS+r"""
void g(void){
    int k = CM_CELL(cm_sptr).base_kind;
    acc += CM_CELL(cm_sptr).building;
    CM_CELL(cm_sptr).building = (acc + k) & 0xf;
    CM_CELL(cm_sptr).edge_bits |= 1;
    acc += CM_CELL(cm_sptr + CM_S).terrain;
    acc += CM_CELL(cm_sptr + CM_S + CM_E).terrain;
    acc += CM_FIELD(cm_sptr, field_off);
    acc += helper(CM_PTR(cm_sptr), 4);
}
""", note="MACRO form over struct city_cell[]")

# ---- directional cell macros (no manual + in call sites) ----
DIRMAC = (
    "#define CITY_ROW 1600\n#define CITY_CELL_BYTES 20\n"
    "#define CM_CELL(off) (*(struct city_cell *)((unsigned char *)city_map + (off)))\n"
    "#define CM_N(off)  CM_CELL((off) - CITY_ROW)\n"
    "#define CM_S(off)  CM_CELL((off) + CITY_ROW)\n"
    "#define CM_E(off)  CM_CELL((off) + CITY_CELL_BYTES)\n"
    "#define CM_W(off)  CM_CELL((off) - CITY_CELL_BYTES)\n"
    "#define CM_SE(off) CM_CELL((off) + CITY_ROW + CITY_CELL_BYTES)\n"
    "#define CM_PTR(off) ((unsigned char *)city_map + (off))\n"
    "#define CM_FIELD(off,f) (CM_PTR(off)[(f)])\n"
)

exp.add("dir_form", STRUCT_DECL+COMMON+"int field_off;\n"+DIRMAC+r"""
void g(void){
    int k = CM_CELL(cm_sptr).base_kind;
    acc += CM_CELL(cm_sptr).building;
    CM_CELL(cm_sptr).building = (acc + k) & 0xf;
    CM_CELL(cm_sptr).edge_bits |= 1;
    acc += CM_S(cm_sptr).terrain;
    acc += CM_SE(cm_sptr).terrain;
    acc += CM_FIELD(cm_sptr, field_off);
    acc += helper(CM_PTR(cm_sptr), 4);
}
""", note="directional cell macros CM_S/CM_SE(off).field")
