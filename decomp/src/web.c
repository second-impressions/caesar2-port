// D:\C2\CODE\web.c

#include "web.h"
#include "c2_data.h"

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
struct web_node web[120];
int web_nof_dircs;
int web_node_count;
int web_y;
int web_x;
int web_first_actual_node;
int web_total_length;
int web_out_of_the_walls;
int web_ptr;
int web_start_y;
int web_start_x;
int web_node;
char web_from;
char web_dirc;
char web_directions;

/* web / web_dirc / web_directions: types in c2_data.h */
/* web_from: type char in c2_data.h */

// FUNCTION: C2 0x29A68
// WIN: 0x00450c50
// Lines 41–60
int get_regroad_start_node(int x, int y)
{
    web_start_x = x;
    web_x = x;
    web_start_y = y;
    web_y = y;

    web_ptr = (y * REGION_W + x) * REGION_CELL_BYTES;

    if ((RM_CELL(web_ptr).terrain & 0x25) == 0) return 0;

    web_nof_dircs = get_web_regroad_dircs();
    web[0].kind     = 4;
    web[0].out_of_walls   = 0;
    web[0].x        = web_x;
    web[0].y        = web_y;
    web[0].dirs     = web_directions;
    RM_CELL(web_ptr).edge_bits |= 0x20;
    web_first_actual_node = 0;
    web_node_count = 1;
    web_total_length = 1;
    web_out_of_the_walls = 0;
    return 1;
}

// FUNCTION: C2 0x29B0B
// WIN: 0x00450d3b
// Lines 62–84
//
// Grow the regional-road web from (x, y) by repeatedly picking an
// incomplete node and extending it in one of the four compass
// directions.  Returns 1 if the web closed cleanly, 0 if the node
// table overflowed (>= 120 entries).
int get_regroad_web(int x, int y)
{
    unsigned char dx;

    init_web();
    if (get_regroad_start_node(x, y) == 0) return 0;
    while (get_incomplete_node(0x3c, 8) != 0) {
        web_out_of_the_walls = web[web_node].out_of_walls;
        if (web_node_count >= 0x78) return 0;
        while (run_to_new_regroad_node() != 0) {
            dx = web[web_node].dirs ^ web[web_node].from_dir;
            if      (dx & 1) { web_dirc = 1; web_from = 4; }
            else if (dx & 2) { web_dirc = 2; web_from = 8; }
            else if (dx & 4) { web_dirc = 4; web_from = 1; }
            else if (dx & 8) { web_dirc = 8; web_from = 2; }
            else break;
            web[web_node].from_dir |= web_dirc;
        }
    }
    return 1;
}

// FUNCTION: C2 0x29C0A
// WIN: 0x00450e8c
// Lines 86–129
//
// Step the regional-road walker along web_dirc until it reaches a
// junction (>2 available dirs), where a new web node is appended and
// the current out-of-walls state is copied into web[web_node].out_of_walls.
// Returns 0 for dead ends, loops back to the start node, or the
// 1000-step watchdog.
int run_to_new_regroad_node(void)
{
    int steps;

    steps = 0;
    while (1) {
        steps++;
        if (steps >= 0x3e8) break;
        if      (web_dirc == 1) { web_y--; web_ptr -= 0x1e0; }
        else if (web_dirc == 2) { web_x++; web_ptr += 8;     }
        else if (web_dirc == 4) { web_y++; web_ptr += 0x1e0; }
        else if (web_dirc == 8) { web_x--; web_ptr -= 8;     }

        web_nof_dircs = get_web_regroad_dircs();
        if ((RM_CELL(web_ptr).edge_bits & 0x20) == 0) web_total_length++;
        if (RM_CELL(web_ptr).terrain & 2) web_out_of_the_walls = 1;
        RM_CELL(web_ptr).edge_bits |= 0x20;
        RM_CELL(web_ptr).outside &= 0xbf;
        if (web_out_of_the_walls != 0) RM_CELL(web_ptr).outside |= 0x40;

        if (web_nof_dircs > 2) {
            put_new_node();
            web[web_node].out_of_walls = web_out_of_the_walls;
            return 1;
        }
        if (web_x == web_start_x && web_y == web_start_y) {
            web[0].from_dir |= web_from;
            break;
        }
        if (web_nof_dircs <= 1) break;
        web_directions ^= web_from;
        if      (web_directions & 1) { web_dirc = 1; web_from = 4; }
        else if (web_directions & 2) { web_dirc = 2; web_from = 8; }
        else if (web_directions & 4) { web_dirc = 4; web_from = 1; }
        else if (web_directions & 8) { web_dirc = 8; web_from = 2; }
    }
    return 0;
}

// FUNCTION: C2 0x29DDC
// WIN: 0x004510fc
// Lines 131–156
int get_web_regroad_dircs(void)
{
    int count = 0;
    web_directions = 0;
    if (web_y > 0) {
        if (RM_CELL(web_ptr - REGION_ROW).terrain & 0x25) { web_directions = 1; count = 1; }
    }
    if (web_x < 0x3b) {
        if (RM_CELL(web_ptr + REGION_CELL_BYTES).terrain   & 0x25) { web_directions += 2; count++; }
    }
    if (web_y < 0x3b) {
        if (RM_CELL(web_ptr + REGION_ROW).terrain & 0x25) { web_directions += 4; count++; }
    }
    if (web_x > 0) {
        if (RM_CELL(web_ptr - REGION_CELL_BYTES).terrain   & 0x25) { web_directions += 8; count++; }
    }
    return count;
}

// FUNCTION: C2 0x29E8D
// WIN: 0x004511f2
// Lines 160–188
//
// Seed the aqueduct-flow web at (x, y).  Returns 0 if the source
// cell has no aqueduct/structure bits set (cm[+1] & 0xC0 == 0).
// Otherwise initialises web[0] as the source node, marks the cell
// as visited, copies the structure's water-pressure floor from
// cm[+9] into cm[+4], and chooses `web_first_actual_node` = 1 if
// the source cell is itself a water *building* (cm[+1] & 0x80) and
// = 0 otherwise.
int get_aqua_start_node(int x, int y)
{
    web_start_x = x;
    web_x       = x;
    web_start_y = y;
    web_y       = y;
    web_ptr     = (x + y * 80) * 20;  /* Rule 4: keep X-first operand order */
    if ((CM_CELL(web_ptr).terrain & 0xc0) == 0) return 0;
    web_nof_dircs = get_web_aqua_dircs();
    web[0].kind   = 4;
    web[0].x      = web_x;
    web[0].y      = web_y;
    web[0].dirs   = web_directions;
    CM_CELL(web_ptr).edge_bits |= 0x20;
    CM_CELL(web_ptr).range_flag &= 0xfc;
    CM_CELL(web_ptr).extra_edge = CM_CELL(web_ptr).building;
    web_first_actual_node = ((CM_CELL(web_ptr).terrain & 0x80) == 0);
    web_node_count   = 1;
    web_total_length = 1;
    return 1;
}

// FUNCTION: C2 0x29F4E
// WIN: 0x00451323
// Lines 190–215
//
// Grow the aqueduct web from (x, y), then commit the result: each
// committed node gets its building-class mask stamped into
// cm[+0x0A], and three propagation passes flood the surrounding
// cells with diminishing pressure (3 inside walls, 3 across
// terrain, 2 over coverage).  Returns 0 if no start cell is
// reachable, 1 once the web is fully written back.
int get_aqua_web(int x, int y)
{
    unsigned char dx;

    init_web();
    if (get_aqua_start_node(x, y) == 0) return 0;
    while (get_incomplete_node(0x50, 0x14) != 0) {
        while (run_to_new_aqua_node() != 0) {
            dx = web[web_node].dirs ^ web[web_node].from_dir;
            if      (dx & 1) { web_dirc = 1; web_from = 4; }
            else if (dx & 2) { web_dirc = 2; web_from = 8; }
            else if (dx & 4) { web_dirc = 4; web_from = 1; }
            else if (dx & 8) { web_dirc = 8; web_from = 2; }
            else break;
            web[web_node].from_dir |= web_dirc;
        }
    }
    set_first_nodes_values(3);
    push_nodes_values(3, 1);
    push_nodes_values(3, 0);
    push_nodes_values(2, 0);
    return 1;
}

// FUNCTION: C2 0x2A05A
// WIN: 0x0045147a
// Lines 217–253
//
// Step the aqueduct walker one cell at a time along web_dirc until
// it hits a water-using building (cm[+1] & 0x80) — put_new_node()
// and return 1 — or runs out of directions / loops back to the
// start cell / trips the 1000-iter watchdog (return 0).
int run_to_new_aqua_node(void)
{
    int           steps;
    unsigned char dx;

    steps = 0;
    while (1) {
        steps++;
        if (steps >= 0x3e8) break;
        if      (web_dirc == 1) { web_y--; web_ptr -= 0x640; }
        else if (web_dirc == 2) { web_x++; web_ptr += 0x14;  }
        else if (web_dirc == 4) { web_y++; web_ptr += 0x640; }
        else if (web_dirc == 8) { web_x--; web_ptr -= 0x14;  }
        web_nof_dircs = get_web_aqua_dircs();
        if ((CM_CELL(web_ptr).edge_bits & 0x20) == 0) web_total_length++;
        CM_CELL(web_ptr).edge_bits   |= 0x21;
        CM_CELL(web_ptr).range_flag &= 0xfc;
        CM_CELL(web_ptr).extra_edge    = CM_CELL(web_ptr).building;
        if (CM_CELL(web_ptr).terrain & 0x80) {
            put_new_node();
            return 1;
        }
        if (web_x == web_start_x && web_y == web_start_y) {
            web[0].from_dir |= web_from;
            break;
        }
        if (web_nof_dircs <= 1) break;
        web_directions ^= web_from;
        if      (web_directions & 1) { web_dirc = 1; web_from = 4; }
        else if (web_directions & 2) { web_dirc = 2; web_from = 8; }
        else if (web_directions & 4) { web_dirc = 4; web_from = 1; }
        else if (web_directions & 8) { web_dirc = 8; web_from = 2; }
    }
    return 0;
}

// FUNCTION: C2 0x2A1F3
// WIN: 0x004516cb
// Lines 255–268
/* The 4 neighbour cells of the current `web_ptr` cell: row stride is
 * sizeof(struct city_cell) * 80 = 0x640, column stride is
 * sizeof(struct city_cell) = 0x14.  Each access reads the +1 byte
 * (terrain field) of one neighbour.  We use a struct-of-bytes cast
 * so Watcom folds `city_map_base + (cell_offset * 20 + terrain_off)`
 * into a single displacement.  The PS code path is
 *     mov edx, [web_ptr]
 *     mov dl,  [edx + city_map - 0x63F]
 * which matches the (struct city_cell *)((char *)city_map + web_ptr)
 * + .terrain pattern below. */
int get_web_aqua_dircs(void)
{
    int count = 0;
    web_directions = 0;
    if (web_y > 0) {
        if (CM_CELL((web_ptr - 80 * CITY_CELL_BYTES)).terrain & 0xC0) {
            web_directions = 1; count = 1;
        }
    }
    if (web_x < 0x4f) {
        if (CM_CELL((web_ptr + 1 * CITY_CELL_BYTES)).terrain & 0xC0) {
            web_directions += 2; count++;
        }
    }
    if (web_y < 0x4f) {
        if (CM_CELL((web_ptr + 80 * CITY_CELL_BYTES)).terrain & 0xC0) {
            web_directions += 4; count++;
        }
    }
    if (web_x > 0) {
        if (CM_CELL((web_ptr - 1 * CITY_CELL_BYTES)).terrain & 0xC0) {
            web_directions += 8; count++;
        }
    }
    return count;
}

// FUNCTION: C2 0x2A2A4
// WIN: 0x004517c1
// Lines 270–281
int test_next_to_river(void)
{
    if (web_y > 0) {
        if (CM_CELL((web_ptr - 80 * CITY_CELL_BYTES)).terrain & 0x18) return 1;
    }
    if (web_x < 0x4f) {
        if (CM_CELL((web_ptr + 1 * CITY_CELL_BYTES)).terrain & 0x18) return 1;
    }
    if (web_y < 0x4f) {
        if (CM_CELL((web_ptr + 80 * CITY_CELL_BYTES)).terrain & 0x18) return 1;
    }
    if (web_x > 0) {
        if (CM_CELL((web_ptr - 1 * CITY_CELL_BYTES)).terrain & 0x18) return 1;
    }
    return 0;
}

// FUNCTION: C2 0x2A321
// WIN: 0x00451887
// Lines 285–294
void init_web(void)
{
    int i;
    for (i = 0; i < 120; i++) {
        web[i].kind = web[i].out_of_walls = web[i]._unused_writeonly02[0] = web[i]._unused_writeonly02[1] = 0;
        web[i].dirs = web[i].from_dir = 0;
        web[i].x    = web[i].y        = 0;
    }
}

// FUNCTION: C2 0x2A368
// WIN: 0x00451938
// Lines 296–314
//
// Add (web_x, web_y) to the active web.  If an existing slot already
// holds those coordinates, just OR `web_from` into its from_dir mask
// and return.  Otherwise append a fresh `kind=4` (initial) node at
// the tail and bump web_node_count.
void put_new_node(void)
{
    /* PS initializes web_node, then loops with web_x/web_y read directly.
     * Watcom CSE caches the two globals into callee-save registers, but the
     * CSE-derived temps land at a different LIFO position in the conflict
     * list than hand-coded locals would (`int x = web_x` etc.) — and the
     * Rule 65 equal-savings tie-break ends up swapping ESI/EBX assignment
     * for web_x vs web_node_count.  Keeping the reads inline lets PS-shaped
     * regalloc emerge (Rule 67).  See docs/watcom-codegen-patterns.md. */
    for (web_node = 0; web_node < web_node_count; web_node++) {
        if (web[web_node].kind == 0) break;
        if (web[web_node].x == web_x) {
            if (web[web_node].y == web_y) {
                web[web_node].from_dir |= web_from;
                return;
            }
        }
    }

    /* Source order (Mac-confirmed): web_node_count++ FIRST, from_dir +=
     * LAST.  Watcom schedules the `inc [web_node_count]` down to the
     * function tail (no register dependency) but its per-instruction
     * line_num travels with it, so PS's -d1 tags it L307 -- BEFORE the
     * kind=4 line -- even though it emits last.  c2 line-compare clean. */
    web_node_count++;
    web[web_node].kind = 4;
    web[web_node].x    = web_x;
    web[web_node].y    = web_y;
    web[web_node].dirs = web_directions;
    web[web_node].from_dir += web_from;
}

// FUNCTION: C2 0x2A418
// WIN: 0x00451a53
// Lines 317–336
//
// Find the first web node (0..web_node_count-1) whose `dirs` mask
// still has unexplored bits (dirs != from_dir).  On hit, populate
// web_x / web_y from the node, compute web_ptr from (web_y, web_x)
// using the caller-supplied row stride and per-cell stride, and pick
// the next direction bit to extend.  Returns 1 on hit, 0 if no node
// is incomplete.
int get_incomplete_node(int row_stride, int cell_stride)
{
    unsigned char dx;

    for (web_node = 0; web_node < web_node_count; web_node++) {
        if (web[web_node].dirs == web[web_node].from_dir) continue;
        web_x = web[web_node].x;
        web_y = web[web_node].y;
        web_ptr = (row_stride * web_y + web_x) * cell_stride;
        dx = web[web_node].dirs ^ web[web_node].from_dir;
        if      (dx & 1) { web_dirc = 1; web_from = 4; }
        else if (dx & 2) { web_dirc = 2; web_from = 8; }
        else if (dx & 4) { web_dirc = 4; web_from = 1; }
        else if (dx & 8) { web_dirc = 8; web_from = 2; }
        web[web_node].from_dir |= web_dirc;
        return 1;
    }
    return 0;
}

// FUNCTION: C2 0x2A51F
// WIN: 0x00451bb9
// Lines 338–352
//
// Commit every initial web node from web_first_actual_node up to
// web_node_count.  For nodes next to a river, OR `mask` into the
// city-map byte at +0x0A, mark the web node kind as committed (5),
// and bump the city-map byte at +0x04 by 3.
void set_first_nodes_values(int mask)
{
    char mask_byte;
    char kind;

    mask_byte = mask;
    for (web_node = web_first_actual_node, kind = 5; web_node < web_node_count; web_node++) {
        web_x = web[web_node].x;
        web_y = web[web_node].y;
        web_ptr = (web_y * CITY_W + web_x) * CITY_CELL_BYTES;
        if (test_next_to_river()) {
            CM_CELL(web_ptr).range_flag |= mask_byte;
            web[web_node].kind = kind;
            CM_CELL(web_ptr).extra_edge += 3;
        }
    }
}

// FUNCTION: C2 0x2A5B0
// WIN: 0x00451c83
// Lines 354–400
//
// For every active web node with class `mask`, fan out into the four
// compass directions and call push_node_value() on each unexplored
// neighbour.  When `flag` is non-zero the scan is restricted to
// committed nodes (kind == 5) and the propagated mask is unchanged;
// when `flag` is zero every node is processed and the mask is
// decremented by one for the recursive call.
//
// Faithful body — ~308 b regalloc residue.  PS keeps `mask` in BL
// and uses byte-compares directly against memory operands; recomp
// hoists the zext-mask into EBP and adds a 4-byte stack slot for
// the per-bit ternary spill.  Same control flow / call pattern.
void push_nodes_values(char mask, int flag)
{
    unsigned char dirs;
    int  x;
    int  y;
    int  cm_ptr;

    for (web_node = web_first_actual_node; web_node < web_node_count; web_node++) {
        if (flag != 0) {
            if ((unsigned char)web[web_node].kind != 5) continue;
        }
        dirs = web[web_node].dirs;
        x = web[web_node].x;
        y = web[web_node].y;
        cm_ptr = (x + y * CITY_W) * CITY_CELL_BYTES;
        if ((char)(CM_CELL(cm_ptr).range_flag & 3) != mask) continue;
        if (dirs & 1) {
            web_dirc = 1; web_from = 4;
            web_x = x; web_y = y; web_ptr = cm_ptr;
            if (flag == 0) push_node_value((char)(mask - 1));
            else           push_node_value(mask);
        }
        if (dirs & 2) {
            web_dirc = 2; web_from = 8;
            web_x = x; web_y = y; web_ptr = cm_ptr;
            if (flag == 0) push_node_value((char)(mask - 1));
            else           push_node_value(mask);
        }
        if (dirs & 4) {
            web_dirc = 4; web_from = 1;
            web_x = x; web_y = y; web_ptr = cm_ptr;
            if (flag == 0) push_node_value((char)(mask - 1));
            else           push_node_value(mask);
        }
        if (dirs & 8) {
            web_dirc = 8; web_from = 2;
            web_x = x; web_y = y; web_ptr = cm_ptr;
            if (flag == 0) push_node_value((char)(mask - 1));
            else           push_node_value(mask);
        }
    }
}

// FUNCTION: C2 0x2A74D
// WIN: 0x00451ebf
// Lines 402–438
//
// Walk the city map outward from the current node, OR-ing `mask`
// into city_map[+0x0A] and accumulating water-pressure / building
// adjustments at city_map[+0x04] for each cell, until the run hits
// a tile whose existing pressure already ≥ `mask`, the directions
// queue empties, or the watchdog (1000 iters) trips.
//
// `int building` (not `unsigned char`) is required: PS enregisters
// `building` as int in ESI via the `mov ch, [..]; and ch, 0x80;
// movzx esi, ch` pattern.  With `unsigned char` building's byte
// temp stays in CL and ESI is never claimed, which flips the
// callee-save set + cascades through the pressure/ECX allocation.
// The `else if` on the `(cm&2)==0` block matches PS's `jmp` after
// the `mask==3 ? cm[+4]+=2` branch (without `else if`, mask==3 would
// incorrectly add +3 instead of +2).
void push_node_value(char mask)
{
    int steps;
    unsigned char pressure;
    int building;

    steps = 0;
    while (1) {
        steps++;
        if (steps >= 0x3e8) return;
        if      (web_dirc == 1) { web_y--; web_ptr -= 0x640; }
        else if (web_dirc == 2) { web_x++; web_ptr += 0x14;  }
        else if (web_dirc == 4) { web_y++; web_ptr += 0x640; }
        else if (web_dirc == 8) { web_x--; web_ptr -= 0x14;  }
        web_nof_dircs = get_web_aqua_dircs();
        pressure = CM_CELL(web_ptr).range_flag & 3;
        building = CM_CELL(web_ptr).terrain & 0x80;

        if (building) {
            if ((char)pressure >= mask) return;
            CM_CELL(web_ptr).range_flag |= mask;
            if (mask == 3) CM_CELL(web_ptr).extra_edge += 3;
            if (mask == 2) CM_CELL(web_ptr).extra_edge += 2;
            if (mask == 1) CM_CELL(web_ptr).extra_edge += 1;
            return;
        }
        if ((char)pressure >= mask) return;
        CM_CELL(web_ptr).range_flag |= mask;
        if ((CM_CELL(web_ptr).terrain & 2) == 0) {
            if (mask == 3) CM_CELL(web_ptr).extra_edge += 2;
            else if (mask >= 1) CM_CELL(web_ptr).extra_edge++;
        }
        web_directions ^= web_from;
        if      (web_directions & 1) { web_dirc = 1; web_from = 4; }
        else if (web_directions & 2) { web_dirc = 2; web_from = 8; }
        else if (web_directions & 4) { web_dirc = 4; web_from = 1; }
        else if (web_directions & 8) { web_dirc = 8; web_from = 2; }
        else return;
    }
}
