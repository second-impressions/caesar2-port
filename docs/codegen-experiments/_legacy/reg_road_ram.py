"""reg_road_ramifications — preamble min/max regalloc tie (x_min<->y_max).

PS puts all 4 min/max locals in callee-saves (x_min=ECX, y_min=EDI,
x_max=EBX, y_max=ESI) and keeps x/y in EAX/EDX as lea sources.  Our
build flips the equal-savings x_min<->y_max tie (x_min=ESI, y_max=ECX).
Sweep preamble forms + decl orders in isolation (fast, cached) to find
the source shape that reproduces PS's tie.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="reg_road_ram",
    ps_function="reg_road_ramifications",
    chk=False,
    prelude="""
struct choice_rec { int a, b; };
extern unsigned char region_map[];
extern int gmn_x, gmn_y, gmn_sptr;
extern char first_choice;
extern struct choice_rec road_data[];
extern int one_reg_wall_ramification(void);
extern void test_regionmap_neighbours_posedge(char mask);
extern int choose_from(struct choice_rec *records, int count);
""",
    extra_defs="""
struct choice_rec { int a, b; };
unsigned char region_map[400000];
int gmn_x, gmn_y, gmn_sptr;
char first_choice;
struct choice_rec road_data[64];
""",
)

BODY = """
    for (gmn_y = y_min; gmn_y <= y_max; gmn_y++) {
        for (gmn_x = x_min; gmn_x <= x_max; gmn_x++) {
            gmn_sptr = (gmn_x + gmn_y * 60) * 8;
            if ((region_map[gmn_sptr + 1] & 0x20) != 0) {
                region_map[gmn_sptr + 3] |= 1;
                if ((region_map[gmn_sptr + 1] & 2) != 0) {
                    if (one_reg_wall_ramification() == 0) {
                        int tt = region_map[gmn_sptr + 1] & 0xf9;
                        region_map[gmn_sptr + 1] = (unsigned char)(tt | 2);
                        return 0;
                    }
                } else {
                    test_regionmap_neighbours_posedge(0xe5);
                    if (choose_from(road_data, 0x10) == 0) {
                        region_map[gmn_sptr + 1] &= 0xdf;
                        return 0;
                    }
                    region_map[gmn_sptr + 0] = first_choice + 0x4e;
                    region_map[gmn_sptr + 3] &= 0xe3;
                    region_map[gmn_sptr + 4] = first_choice - 0x52;
                }
            }
        }
    }
    return 1;
}
"""

PREAMBLES = {
    "ifelse": """int reg_road_ramifications(int x, int y)
{
    int x_min, y_min, x_max, y_max;
    if (x == 0) x_min = 0; else x_min = x - 1;
    if (y == 0) y_min = 0; else y_min = y - 1;
    if (x == 59) x_max = x; else x_max = x + 1;
    if (y == 59) y_max = y; else y_max = y + 1;
""",
    "override": """int reg_road_ramifications(int x, int y)
{
    int x_min, y_min, x_max, y_max;
    x_min = x - 1; if (x == 0) x_min = 0;
    y_min = y - 1; if (y == 0) y_min = 0;
    x_max = x + 1; if (x == 59) x_max = x;
    y_max = y + 1; if (y == 59) y_max = y;
""",
}

# Downstream callee definitions, in map.c source order (after the target).
# Keeping them in the SAME TU after the target reproduces the name-pointer
# allocation context that the regalloc tie-break depends on.
DOWNSTREAM = """
int one_reg_wall_ramification(void) { return gmn_sptr; }
void test_regionmap_neighbours_posedge(char mask) { gmn_x = mask; }
int choose_from(struct choice_rec *records, int count) { return records[count].a; }
"""

for name, pre in PREAMBLES.items():
    exp.add(name, pre + BODY + DOWNSTREAM, note=name)
