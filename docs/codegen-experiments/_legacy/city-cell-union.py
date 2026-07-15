"""struct city_cell with an anonymous-union byte overlay: keeps NAMED field
access for constant fields AND struct-style INDEXED access for runtime fields,
with no raw cast / manual offset at call sites.  Watcom 10.0a accepts the
anonymous struct-in-union, and every form is byte-identical to the raw
unsigned char[] baseline.

    struct city_cell {
        union {
            struct { unsigned char base_kind, terrain, ... business; };
            unsigned char b[20];
        };
    };

    CM_S(off).terrain        named, constant field   (neighbour)
    CM_S(off).b[field_off]    indexed, RUNTIME field  (flag/range engine)
    CM_CELL(off).b           byte pointer arg (.b decays) -> &city_map[off]
"""
from c2.commands.cgex import Experiment

CELL = (
    "struct city_cell { union { struct { unsigned char base_kind,terrain,"
    "road_aqueduct,edge_bits,extra_edge,activity_a,activity_b,citizen_a,"
    "citizen_b,building,range_flag,fpu_flag,entertainment,education,health,"
    "land_value,fire,security,industrial,business; }; unsigned char b[20]; }; };\n"
    "struct city_cell city_map[6400];\n"
)
COMMON = ("int cm_sptr,acc,field_off,value; int helper(unsigned char *p,int n);\n"
          "#define CITY_ROW 1600\n#define CITY_CELL_BYTES 20\n"
          "#define CM_CELL(off) (*(struct city_cell *)((unsigned char *)city_map + (off)))\n"
          "#define CM_S(off) CM_CELL((off) + CITY_ROW)\n")
BYTES = "unsigned char city_map[128000];\nint cm_sptr,acc,field_off,value; int helper(unsigned char *p,int n);\n"

exp = Experiment(name="city-cell-union",
                 extra_defs="int helper(unsigned char *p,int n){(void)p;return n;}\n")

exp.add("union_form", CELL+COMMON+r"""
void g(void){
    CM_CELL(cm_sptr).terrain = 5;            /* named constant field */
    CM_S(cm_sptr).b[field_off] = value;      /* indexed runtime field */
    acc += helper(CM_CELL(cm_sptr).b, 4);    /* byte-ptr arg via .b */
}
""", note="union overlay: named + indexed + .b ptr")

exp.add("bytes_ref", BYTES+r"""
void g(void){
    city_map[cm_sptr + 1] = 5;
    city_map[cm_sptr + 1600 + field_off] = value;
    acc += helper(&city_map[cm_sptr], 4);
}
""", note="baseline unsigned char[]")
