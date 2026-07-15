// D:\C2\CODE\pm_map0.c

#include "c2_data.h"


/* ASM-defined sprite blitters (dia_*.asm); receive (eax = base_ptr,
 * edx = style) and read fixt_data + sprite_start globals.  Forward-
 * declared here because they have no debug info / source file in
 * symbols.json, so the auto-gen header skips them. */

// FUNCTION: C2 0x352AA
// WIN: 0x00484250
// Lines 29–38
//
// BYTE-EXACT.  Three levers, all read off PS's -d1 line numbers + disasm:
//  (1) The cell value is INLINED in the condition (no named `pm_val`
//      local).  PS's line table attributes the load to the condition
//      line (no separate assignment line), so the access is used directly
//      in both tests; Watcom CSEs it into ONE load held in a callee-save
//      (edi) across both compares -- a named local instead gets folded
//      into a scaled-index and lands in eax (scratch) with a setl/and.
//  (2) NESTED ifs (not `&&`): PS's lines L36/L37 are separate (sprite
//      test, then equality test), matching `if (...) if (...)`.
//  (3) UNSIGNED sprite tag (0x0FFF0000U): PS compares the cell unsigned
//      (`jae`), not signed (`jge`) -- Rule 90.
//  (4) NO pm_limits(): PS jmps straight to the shared epilogue in BOTH
//      paths (tail-merge into get_pseudo_map+0x3E0).  The old pm_limits()
//      calls were a decompilation error -- PS never calls it here.
void get_pm_from_actual(int actual)
{
    int row;
    int col;

    x = 0;
    y = 0;
    for (row = 0; row < 0xa1; row++) {
        for (col = 0; col < 0x51; col++) {
            if (!(pseudo_map[row][col] >= 0x0FFF0000U))
                if (actual == pseudo_map[row][col]) {
                    x = row;
                    y = col;
                    return;
                }
        }
    }
}

// FUNCTION: C2 0x35311
// WIN: 0x0048430f
// Lines 44–127
//
// BYTE-EXACT.  Source shape from the Mac PPC oracle + PS -d1 lines; the
// last byte cracked purely by LOCAL-DECLARATION ORDER (no body change).
//
// The 8-arm sprite ring writes `pseudo_map[row][col] = 0x0FFF0000 | k` from
// an if/else-if chain.  Watcom emits the address `base + row*0x144 + col*4`
// in three forms per arm — Form D (row*0x144 in-place in EDX, col scaled *4
// via SIB), Form B (row*0x51 in EAX scaled *4, col*4 explicit in EDX), and
// Form L (Form D built via `lea edx,[ecx+eax]`, +1 byte).  PS's per-arm
// forms are D,B,L,B,B,B,D,B.  The forms come from anonymous per-arm CSE
// temps with no named-local handle, so they cannot be pinned by editing the
// arm statements (all 8 are textually identical).
//
// BUT the form choice is a GiveBestReg tie decided by ConfBefore
// name-pointer order, and Watcom deals FRL name slots to the 12 named
// locals (at declaration) BEFORE the anonymous arm temps — so the
// declaration ORDER of these locals steers the arm temps' tie-break AND the
// six spilled direction-control locals' stack slots.  A cgex-driven search
// over declaration permutations (docs/codegen-experiments/get_pseudo_map_arm0.py)
// found the order below, which reproduces all 8 PS arm forms AND the exact
// spill slots — zero byte diff.  The body (ring + direction setup + the
// three fill loops) is unchanged and matches the Mac oracle exactly; do not
// reorder these declarations.
void get_pseudo_map(int direction)
{
    int col_x2_step;
    int x2_step;
    int start_row;
    int row;
    int start_x2;
    int col_row_step;
    int col_edge;
    int row_step;
    int pr;
    int row_edge;
    int px2;
    int col;

    for (row = 0; row < 0xa1; row++) {
        for (col = 0; col < 0x51; col++) {
            if (row <= 0x50) row_edge = row; else row_edge = 0xa0 - row;
            if (col <= 0x28) col_edge = col; else col_edge = 0x50 - col;
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
            }
        }
    }

    map_direction = direction;
    if (direction == 0) {
        start_row = map_height_reduction * 2 + 1;
        row_step = 1;
        col_row_step = 1;
        start_x2 = 0x50;
        x2_step = -1;
        col_x2_step = 1;
    } else if (direction == 2) {
        start_row = 0x50;
        row_step = 1;
        col_row_step = -1;
        start_x2 = map_width_reduction * 2 + 1;
        x2_step = 1;
        col_x2_step = 1;
    } else if (direction == 4) {
        start_row = (0x50 - map_height_reduction) * 2 - 1;
        row_step = -1;
        col_row_step = -1;
        start_x2 = 0x50;
        x2_step = 1;
        col_x2_step = -1;
    } else if (direction == 6) {
        start_row = 0x50;
        row_step = -1;
        col_row_step = 1;
        start_x2 = (0x50 - map_width_reduction) * 2 - 1;
        x2_step = -1;
        col_x2_step = -1;
    }

    for (row = 0; row < map_actual_height; row++) {
        pr = start_row;
        px2 = start_x2;
        for (col = 0; col < map_actual_width; col++) {
            pseudo_map[pr][px2 / 2] = map_actual_atom * (map_actual_width * row + col);
            pr += col_row_step;
            px2 += col_x2_step;
        }
        start_row += row_step;
        start_x2 += x2_step;
    }

    start_row = map_height_reduction * 2 + 1;
    start_x2 = 0x50;
    for (row = 0; row < 0x50 - map_height_reduction * 2; row++) {
        pr = start_row;
        px2 = start_x2;
        for (col = 0; col < map_actual_width; col++) {
            pr++;
            px2++;
        }
        pseudo_map[pr][px2 / 2] = 0x0FFF0000 | 0x9;
        start_row++;
        start_x2--;
    }
    if (map_mode > 0) {
        pr = start_row;
        px2 = start_x2;
        for (col = 0; col < map_actual_width; col++) {
            pr++;
            px2++;
        }
        pseudo_map[pr][px2 / 2] = 0x0FFF0000 | 0xa;
    }
    pr = start_row;
    px2 = start_x2;
    for (col = 0; col < 0x50 - map_width_reduction * 2; col++) {
        pseudo_map[pr][px2 / 2] = 0x0FFF0000 | 0x8;
        pr++;
        px2++;
    }
}

// FUNCTION: C2 0x356F7
// WIN: 0x00484805
// Lines 129–135
void pm_limits(void)
{
    int max;
    if (pm_x < 0) pm_x = 0;
    if (pm_y < 0) pm_y = 0;
    max = 0x50 - pm_screen_width;
    if (max <= pm_x) pm_x = max;
    max = 0xa0 - pm_screen_height;
    if (max <= pm_y) pm_y = max;
}

// FUNCTION: C2 0x3574E
// WIN: 0x0048488c
// Lines 137–206
//
// BYTE-EXACT.  Cracked 513->0 by reconstructing PS's source shape from the
// -d1 disasm + c2 regtrace live-allocator ground truth:
//  (1) map_mode==2 sets x_adj=0, y_adj=0x10 (old source had these SWAPPED
//      — a semantic decompile bug; PS L150 `xor x_adj; mov y_adj,0x10`).
//  (2) rel_y computed BEFORE rel_x (PS L163 mouse_y precedes L164 mouse_x),
//      rel_y in SUM form `- (pm_screen_y_start + pm_diamond_half_height)`.
//  (3) NO abs on rem_x — PS does `rem_x = rel_x % half_width; rem_x /= 2`
//      (signed); the old `if(rem_x<0)rem_x=-rem_x` was spurious.
//  (4) yodd = pm_y_coord & 1 cached once and reused in pm_over_x + the
//      pm_x_edge block (PS keeps it in ECX; recomp had re-read the byte).
//  (5) pm_over_x compute-then-in-place subtract; pm_over_x/pm_over_y in
//      screen_start + coord*scale operand order (Rule 4).
//  (6) natural local-declaration order (the old y_parity-before-tile_y
//      --solve hack became a regression once 1-5 landed).
int get_pm_over_diamond(int force_zero_offset)
{
    int x_adj;
    int y_adj;
    int rel_x;
    int rel_y;
    int tile_x2;
    int rem_x;
    int rem_y;
    int sum_parity;
    int x_parity;
    int y_parity;
    int tile_y;
    int next_x;
    int next_y;
    int yodd;

    if (mouse_x < pm_screen_x_start) return 0;
    if (pm_screen_x_start + pm_screen_width * pm_diamond_width <= mouse_x) return 0;
    if (pm_screen_y_start + pm_diamond_half_height > mouse_y) return 0;
    if (pm_screen_y_start + pm_diamond_half_height + pm_screen_height * pm_diamond_half_height <= mouse_y) return 0;

    if (map_mode == 2) {
        x_adj = 0;
        y_adj = 0x10;
    } else if (force_zero_offset) {
        x_adj = 0;
        y_adj = 0;
    } else if (pointer_mode > 0 && map_mode < 2) {
        x_adj = 8;
        y_adj = 8;
    } else if (pm_build_shape < 1) {
        x_adj = 0;
        y_adj = 0;
    } else if (pm_build_shape < 2) {
        x_adj = 0;
        y_adj = -pm_diamond_half_height;
    } else if (pm_build_shape < 3) {
        x_adj = 0;
        y_adj = -pm_diamond_half_height * 2;
    } else if (pm_build_shape < 4) {
        x_adj = 0;
        y_adj = -pm_diamond_half_height * 3;
    } else if (pm_build_shape < 5) {
        x_adj = pm_diamond_width;
        y_adj = -pm_diamond_half_height * 4;
    } else {
        x_adj = pm_diamond_width;
        y_adj = -pm_diamond_half_height * 5;
    }

    rel_y = mouse_y + y_adj - (pm_screen_y_start + pm_diamond_half_height);
    tile_y = rel_y / pm_diamond_half_height;
    rel_x = mouse_x + x_adj - pm_screen_x_start;
    tile_x2 = rel_x / pm_diamond_half_width;
    sum_parity = (tile_x2 + tile_y) & 1;
    x_parity = tile_x2 & 1;
    y_parity = tile_y & 1;
    rem_x = rel_x % pm_diamond_half_width;
    rem_x /= 2;
    rem_y = rel_y % pm_diamond_half_height;

    pm_y_coord = tile_y;
    pm_x_coord = tile_x2 / 2;
    next_y = tile_y + 1;
    next_x = pm_x_coord + 1;
    if (sum_parity == 0) {
        if (rem_y > rem_x) {
            pm_y_coord = next_y;
        } else if (x_parity != 0 && y_parity != 0) {
            pm_x_coord = next_x;
        }
    } else if (sum_parity == 1) {
        if (rem_y + rem_x >= pm_diamond_half_height - 1) {
            pm_y_coord = next_y;
            if (x_parity != 0 && y_parity == 0) {
                pm_x_coord = next_x;
            }
        }
    }

    yodd = pm_y_coord & 1;
    pm_over_x = pm_screen_x_start + pm_x_coord * pm_diamond_width;
    if (yodd)
        pm_over_x -= pm_diamond_half_width;
    pm_over_y = pm_screen_y_start + pm_y_coord * pm_diamond_half_height;
    pm_over_cm_ptr = pseudo_map[(pm_y_coord + pm_y)][pm_x_coord + pm_x];
    if (pm_over_cm_ptr >= 0x0FFF0000) return 0;

    pm_y_edge = 0;
    pm_x_edge = 0;
    if (pm_y_coord == 0) {
        pm_y_edge = 2;
    } else if (pm_y_coord >= pm_screen_height) {
        pm_y_edge = 1;
    }
    if (yodd) {
        if (pm_x_coord == 0) {
            pm_x_edge = 2;
        } else if (pm_x_coord >= pm_screen_width) {
            pm_x_edge = 1;
        }
    }
    return 1;
}

// FUNCTION: C2 0x35A37
// WIN: 0x00484cb9
// Lines 208–249
void rotate_pm_clockwise(void)
{
    int nx;
    int ny;

    map_direction += 2;
    if (map_direction > 6) map_direction = 0;
    get_pseudo_map(map_direction);

    if (zoom_level == 0) {
        nx = (pm_y + 0xe) / 2;
        ny = (0x50 - (pm_x + 4)) * 2;
        pm_x = nx - 4;
        pm_y = ny - 0xe;
    } else if (zoom_level == 1) {
        if (map_mode == 2) {
            nx = (pm_y + 0x16) / 2;
            ny = (0x50 - (pm_x + 0xb)) * 2;
            pm_x = nx - 0xb;
            pm_y = ny - 0x16;
        } else {
            nx = (pm_y + 0x1e) / 2;
            ny = (0x50 - (pm_x + 8)) * 2;
            pm_x = nx - 8;
            pm_y = ny - 0x1e;
        }
    } else if (zoom_level == 2) {
        if (map_mode == 2) {
            pm_x = 0xd;
            pm_y = 0x18;
            return;
        }
        nx = (pm_y + 0x46) / 2;
        ny = (0x50 - (pm_x + 0xa)) * 2;
        pm_x = nx - 0x14;
        pm_y = ny - 0x46;
    }
}

// FUNCTION: C2 0x35B80
// WIN: 0x00484e82
// Lines 251–292
void rotate_pm_anticlockwise(void)
{
    int nx;
    int ny;

    map_direction -= 2;
    if (map_direction < 0) map_direction = 6;
    get_pseudo_map(map_direction);

    if (zoom_level == 0) {
        nx = (0xa1 - (pm_y + 0xe)) / 2;
        ny = (pm_x + 4) * 2;
        pm_x = nx - 4;
        pm_y = ny - 0xe;
    } else if (zoom_level == 1) {
        if (map_mode == 2) {
            nx = (0xa1 - (pm_y + 0x16)) / 2;
            ny = (pm_x + 0xb) * 2;
            pm_x = nx - 0xb;
            pm_y = ny - 0x16;
        } else {
            nx = (0xa1 - (pm_y + 0x1e)) / 2;
            ny = (pm_x + 8) * 2;
            pm_x = nx - 8;
            pm_y = ny - 0x1e;
        }
    } else if (zoom_level == 2) {
        if (map_mode == 2) {
            pm_x = 0xd;
            pm_y = 0x18;
            return;
        }
        nx = (0xa1 - (pm_y + 0x46)) / 2;
        ny = (pm_x + 0x14) * 2;
        pm_x = nx - 0x14;
        pm_y = ny - 0x46;
    }
}

// FUNCTION: C2 0x35CC0
// WIN: 0x0048504c
// Lines 294–321
void show_diamond_ptr(void)
{
    int parity = (pm_y_coord & 1) != 0;

    if (pm_build_shape == 0) {
        show_one_ptr(pm_x_coord, pm_y_coord);
    } else if (pm_build_shape == 1) {
        show_one_ptr(pm_x_coord, pm_y_coord);
        show_one_ptr(pm_x_coord - parity, pm_y_coord + 1);
        show_one_ptr(pm_x_coord - parity + 1, pm_y_coord + 1);
        show_one_ptr(pm_x_coord, pm_y_coord + 2);
    } else if (pm_build_shape == 2) {
        three_by_three(pm_x_coord, pm_y_coord);
    } else if (pm_build_shape == 3) {
        four_by_four(pm_x_coord, pm_y_coord);
    } else if (pm_build_shape == 4) {
        three_by_three(pm_x_coord, pm_y_coord);
        if (parity) three_by_three(pm_x_coord - 2, pm_y_coord + 3);
        else        three_by_three(pm_x_coord - 1, pm_y_coord + 3);
    } else if (pm_build_shape == 5) {
        four_by_four(pm_x_coord, pm_y_coord);
        four_by_four(pm_x_coord - 2, pm_y_coord + 4);
    }
}

// FUNCTION: C2 0x35DC0
// WIN: 0x00485206
// Lines 323–338
//
// Render a 3-row × 3-col isometric "diamond" of pointer
// arrows centred at (x, y).  Layout:
//
//                       (x, y)
//          (x-parity, y+1)  (x-parity+1, y+1)
//   (x-1, y+2)  (x, y+2)  (x+1, y+2)
//          (x-parity, y+3)  (x-parity+1, y+3)
//                       (x, y+4)
//
// where parity = (y & 1) — the half-cell stagger that
// keeps odd rows aligned with their even neighbours in the
// isometric tile grid.  9 cells total via show_one_ptr.
void three_by_three(int x, int y)
{
    int parity = (y & 1) != 0;

    show_one_ptr(x, y);
    show_one_ptr(x - parity, y + 1);
    show_one_ptr(x - parity + 1, y + 1);
    show_one_ptr(x - 1, y + 2);
    show_one_ptr(x, y + 2);
    show_one_ptr(x + 1, y + 2);
    show_one_ptr(x - parity, y + 3);
    show_one_ptr(x - parity + 1, y + 3);
    show_one_ptr(x, y + 4);
}

// FUNCTION: C2 0x35E3F
// WIN: 0x004852e5
// Lines 340–362
void four_by_four(int x, int y)
{
    int parity = (y & 1) != 0;

    show_one_ptr(x, y);
    show_one_ptr(x - parity, y + 1);
    show_one_ptr(x - parity + 1, y + 1);
    show_one_ptr(x - 1, y + 2);
    show_one_ptr(x, y + 2);
    show_one_ptr(x + 1, y + 2);
    show_one_ptr(x - parity - 1, y + 3);
    show_one_ptr(x - parity, y + 3);
    show_one_ptr(x - parity + 1, y + 3);
    show_one_ptr(x - parity + 2, y + 3);
    show_one_ptr(x - 1, y + 4);
    show_one_ptr(x, y + 4);
    show_one_ptr(x + 1, y + 4);
    show_one_ptr(x - parity, y + 5);
    show_one_ptr(x - parity + 1, y + 5);
    show_one_ptr(x, y + 6);
}

// FUNCTION: C2 0x35F0F
// WIN: 0x0048545c
// Lines 365–415
//
// Render the cursor / pointer diamond sprite onto the active panorama-
// map cell (x, y).  Panorama coordinates are isometric: x walks columns,
// y walks rows of half-diamonds.  Steps:
//
//   1. Reject the cell if (pm_x + x, pm_y + y) is outside the visible
//      [0..81)×[0..161) window.
//   2. Look up `pseudo_map[(pm_y+y)][(pm_x+x)]`; reject if the high-
//      bits indicate "empty" (>= 0xFFF0000).
//   3. OR a "dirty" flag (bit 0) into the corresponding city_map (or
//      region_map, when map_mode==1) cell.
//   4. Compute screen-space anchor in (lib_para1, lib_para2) =
//        (pm_screen_x_start + x*pm_diamond_width [- half on odd rows],
//         pm_screen_y_start + y*pm_diamond_half_height).
//   5. Determine pm_x_edge / pm_y_edge (0 = interior, 1 = right/bottom
//      clip, 2 = left/top clip) by comparing x,y to the screen edges.
//   6. Dispatch by zoom_level (0 large / 1 medium / 2 small) and the
//      edge flags to one of 9 `write_i_*_diamond_ptr*` painters.
void show_one_ptr(int x, int y)
{
    int cell_y;
    int cell_x;
    int pm_val;

    cell_y = pm_y + y;
    if (cell_y < 0 || cell_y >= 0xa1) return;
    cell_x = pm_x + x;
    if (cell_x < 0 || cell_x >= 0x51) return;

    /* pseudo_map stride is 81 cells; expressing the indexing as
       (row*81)*4 + col*4 keeps Watcom from fusing the two terms
       before scaling — PS emits 'shl esi,2' + '[esi+eax*4+base]'. */
    pm_val = pseudo_map[cell_y][cell_x];
    if (pm_val >= 0x0FFF0000) return;

    if (map_mode == 0) {
        CM_CELL(pm_val).edge_bits |= 1;
    } else if (map_mode == 1) {
        RM_CELL(pm_val).edge_bits |= 1;
    }

    lib_para1 = pm_screen_x_start + pm_diamond_width * x;
    if (y & 1) lib_para1 -= pm_diamond_half_width;
    lib_para2 = pm_screen_y_start + pm_diamond_half_height * y;

    pm_y_edge = 0;
    pm_x_edge = 0;
    if (y == 0) {
        pm_y_edge = 2;
    } else if (y < 0) {
        return;
    } else if (y == pm_screen_height) {
        pm_y_edge = 1;
    } else if (y > pm_screen_height) {
        return;
    }

    if (x < 0) return;
    if (y & 1) {
        if (x == 0) {
            pm_x_edge = 2;
        } else if (x == pm_screen_width) {
            pm_x_edge = 1;
        } else if (x > pm_screen_width) {
            return;
        }
    } else if (x >= pm_screen_width) {
        return;
    }

    if (zoom_level == 0) {
        if (pm_x_edge == 0)      write_i_large_diamond_ptr(15, pm_y_edge);
        else if (pm_x_edge == 2) write_i_large_diamond_ptr_left(15, pm_y_edge);
        else if (pm_x_edge == 1) write_i_large_diamond_ptr_right(15, pm_y_edge);
    } else if (zoom_level == 1) {
        if (pm_x_edge == 0)      write_i_medium_diamond_ptr(15, pm_y_edge);
        else if (pm_x_edge == 2) write_i_medium_diamond_ptr_left(15, pm_y_edge);
        else if (pm_x_edge == 1) write_i_medium_diamond_ptr_right(15, pm_y_edge);
    } else if (zoom_level == 2) {
        if (pm_x_edge == 0)      write_i_small_diamond_ptr(15, pm_y_edge);
        else if (pm_x_edge == 2) write_i_small_diamond_ptr_left(15, pm_y_edge);
        else if (pm_x_edge == 1) write_i_small_diamond_ptr_right(15, pm_y_edge);
    }
}

// FUNCTION: C2 0x36165
// WIN: 0x004857da
// Lines 418–429
//
// Compute sprite_start = 24-bit little-endian int at
// ``fixt_data[data_ptr + 4..6]`` where ``data_ptr =
// sprite_image_no * 16 + 8``.  Bounds-check (must be in
// [0, 0x4BAF0]) — out-of-range bumps ``sprite_error`` and
// returns silently.  Then dispatch to one of three
// ASM-defined sprite blitters (``place_i_*_diamond``)
// according to ``zoom_level`` (0=large / 1=medium / else=
// small).  ``style`` is forwarded to whichever blitter runs;
// every caller passes 0.
//
// All 22 callers do ``xor eax, eax`` before the call, so
// ``style`` is always 0 in practice.  We keep the parameter
// because PS preserves it (saves into edx in the prologue and
// each blitter receives it as edx).
void place_diamond(int style)
{
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = *(fixt_data + data_ptr + 4)
                 + (*(fixt_data + data_ptr + 5) << 8)
                 + (*(fixt_data + data_ptr + 6) << 16);

    if (sprite_start > 0x4baf0) {
        sprite_error++;
        return;
    }
    if (sprite_start < 0) {
        sprite_error++;
        return;
    }
    if (zoom_level == 0) {
        place_i_large_diamond(fixt_data, style);
        return;
    }
    if (zoom_level == 1) {
        place_i_medium_diamond(fixt_data, style);
        return;
    }
    place_i_small_diamond(fixt_data, style);
}

// FUNCTION: C2 0x361FD
// WIN: 0x0048592d
// Lines 431–442
//
// Left-half variant of `place_diamond` (152 b, L431–442).
// Same structure: compute sprite_start as 24-bit LE int at
// fixt_data[data_ptr+4..6], bounds-check, then dispatch to
// the matching `place_i_*_diamond_lefthalf` blitter by
// zoom_level.  See `place_diamond` for full prose.
//
// Byte-exact.  The 24-bit LE read MUST be written in explicit
// pointer form `*(fixt_data + data_ptr + N)` (Rule 96), not the
// array-subscript form `fixt_data[data_ptr + N]`.  The subscript
// form lets Watcom keep `data_ptr` live in a register (it just
// stored it to the global), emitting a `mov edx, eax` copy; the
// pointer form forces a reload of `data_ptr` from the global and
// the PS-matching indexed `[edx+eax+N]` addressing.  Bisected via
// docs/codegen-experiments/place-lefthalf.py.
//
// 4 callers — pm_map0 donor.
void place_lefthalf_diamond(void)
{
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = *(fixt_data + data_ptr + 4)
                 + (*(fixt_data + data_ptr + 5) << 8)
                 + (*(fixt_data + data_ptr + 6) << 16);

    if (sprite_start > 0x4baf0) {
        sprite_error++;
        return;
    }
    if (sprite_start < 0) {
        sprite_error++;
        return;
    }
    if (zoom_level == 0) {
        place_i_large_diamond_lefthalf(fixt_data, 0);
        return;
    }
    if (zoom_level == 1) {
        place_i_medium_diamond_lefthalf(fixt_data, 0);
        return;
    }
    place_i_small_diamond_lefthalf(fixt_data, 0);
}

// FUNCTION: C2 0x36295
// WIN: 0x00485a5e
// Lines 444–455
//
// Right-half variant of `place_diamond` (152 b, L444–455).
// Same shape as place_lefthalf_diamond / place_diamond,
// dispatching to the `_righthalf` blitter family.
//
// Byte-exact via the Rule 96 pointer form (see
// place_lefthalf_diamond's comment +
// docs/codegen-experiments/place-lefthalf.py).
//
// 4 callers — pm_map0 donor.
void place_righthalf_diamond(void)
{
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = *(fixt_data + data_ptr + 4)
                 + (*(fixt_data + data_ptr + 5) << 8)
                 + (*(fixt_data + data_ptr + 6) << 16);

    if (sprite_start > 0x4baf0) {
        sprite_error++;
        return;
    }
    if (sprite_start < 0) {
        sprite_error++;
        return;
    }
    if (zoom_level == 0) {
        place_i_large_diamond_righthalf(fixt_data, 0);
        return;
    }
    if (zoom_level == 1) {
        place_i_medium_diamond_righthalf(fixt_data, 0);
        return;
    }
    place_i_small_diamond_righthalf(fixt_data, 0);
}

// FUNCTION: C2 0x3632D
// WIN: 0x00485b8f
// Lines 457–466
void place_overlay(int style)
{
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = *(people_data + data_ptr + 4)
                 + (*(people_data + data_ptr + 5) << 8)
                 + (*(people_data + data_ptr + 6) << 16);

    if (sprite_start > 0x4baf0) {
        sprite_error++;
        return;
    }
    if (sprite_start < 0) {
        sprite_error++;
        return;
    }
    if (zoom_level == 0) {
        place_i_large_diamond(people_data, style);
        return;
    }
    if (zoom_level == 1) {
        place_i_medium_diamond(people_data, style);
        return;
    }
    place_i_small_diamond(people_data, style);
}

// FUNCTION: C2 0x363C5
// WIN: 0x00485cc6
// Lines 468–477
void place_lefthalf_overlay(int style)
{
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = *(people_data + data_ptr + 4)
                 + (*(people_data + data_ptr + 5) << 8)
                 + (*(people_data + data_ptr + 6) << 16);

    if (sprite_start > 0x4baf0) {
        sprite_error++;
        return;
    }
    if (sprite_start < 0) {
        sprite_error++;
        return;
    }
    if (zoom_level == 0) {
        place_i_large_diamond_lefthalf(people_data, 0);
        return;
    }
    if (zoom_level == 1) {
        place_i_medium_diamond_lefthalf(people_data, 0);
        return;
    }
    place_i_small_diamond_lefthalf(people_data, 0);
}

// FUNCTION: C2 0x3645D
// WIN: 0x00485df7
// Lines 479–488
void place_righthalf_overlay(int style)
{
    data_ptr = sprite_image_no * 16 + 8;
    sprite_start = *(people_data + data_ptr + 4)
                 + (*(people_data + data_ptr + 5) << 8)
                 + (*(people_data + data_ptr + 6) << 16);

    if (sprite_start > 0x4baf0) {
        sprite_error++;
        return;
    }
    if (sprite_start < 0) {
        sprite_error++;
        return;
    }
    if (zoom_level == 0) {
        place_i_large_diamond_righthalf(people_data, 0);
        return;
    }
    if (zoom_level == 1) {
        place_i_medium_diamond_righthalf(people_data, 0);
        return;
    }
    place_i_small_diamond_righthalf(people_data, 0);
}

