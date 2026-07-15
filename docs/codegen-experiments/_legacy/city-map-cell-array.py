"""Does typing city_map as struct city_cell[] (cell-indexed) match the
byte-offset cursor form PS uses?

PS walks the map with a BYTE offset cursor (cm_sptr += 20 per col, += 1600 per
row) and accesses ((struct city_cell *)&city_map[cm_sptr])->field, folding
city_map+field into a disp32 over the cursor register.

If we retype city_map to `struct city_cell city_map[6400]` and index by CELL
number (i++, city_map[i].field), the compiler must scale i*20.  This experiment
checks whether Watcom strength-reduces the cell-indexed loop to the same
byte-pointer walk, or whether it diverges.
"""
from c2.commands.cgex import Experiment

CELL = "struct city_cell { unsigned char f[20]; };"

exp = Experiment(name="city-map-cell-array")

# byte-offset cursor over unsigned char[] (current/PS form)
exp.add("byte_offset_loop", r"""
unsigned char city_map[128000];
int acc;
void g(void){
    int o;
    for (o = 0; o < 1600; o += 20) {
        acc += city_map[o + 9];
        city_map[o + 3] |= 1;
    }
}
""", note="unsigned char[] + byte cursor o+=20 (PS form)")

# cell-indexed over struct city_cell[] (target form)
exp.add("cell_index_loop", r"""
struct city_cell { unsigned char f[20]; };
struct city_cell city_map[6400];
int acc;
void g(void){
    int i;
    for (i = 0; i < 80; i++) {
        acc += city_map[i].f[9];
        city_map[i].f[3] |= 1;
    }
}
""", note="struct city_cell[] + cell index i++ (target form)")

# struct[] but still byte cursor via char* cast (typed array, byte access)
exp.add("struct_array_byte_cursor", r"""
struct city_cell { unsigned char f[20]; };
struct city_cell city_map[6400];
int acc;
void g(void){
    int o;
    for (o = 0; o < 1600; o += 20) {
        acc += ((struct city_cell *)((unsigned char *)city_map + o))->f[9];
        ((struct city_cell *)((unsigned char *)city_map + o))->f[3] |= 1;
    }
}
""", note="struct city_cell[] but byte cursor via char* cast")
