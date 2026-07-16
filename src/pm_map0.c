
#include "c2_data.h"


/* Assembly sprite-diamond blitters. */

// Returns pm from actual.
// FUNCTION: C2 0x352aa
// FUNCTION: C2WIN 0x00484250
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

// Returns pseudo map.
// FUNCTION: C2 0x35311
// FUNCTION: C2WIN 0x0048430f
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

// Clamps the pseudo-map viewport to the active map bounds.
// FUNCTION: C2 0x356f7
// FUNCTION: C2WIN 0x00484805
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

// Returns pm over diamond.
// FUNCTION: C2 0x3574e
// FUNCTION: C2WIN 0x0048488c
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

// Rotates the pseudo-map orientation clockwise.
// FUNCTION: C2 0x35a37
// FUNCTION: C2WIN 0x00484cb9
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

// Rotates the pseudo-map orientation anticlockwise.
// FUNCTION: C2 0x35b80
// FUNCTION: C2WIN 0x00484e82
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

// Renders diamond ptr.
// FUNCTION: C2 0x35cc0
// FUNCTION: C2WIN 0x0048504c
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

// Render a 3-row × 3-col isometric "diamond" of pointer arrows centred at (x, y).
// FUNCTION: C2 0x35dc0
// FUNCTION: C2WIN 0x00485206
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

// Copies a 4x4 tile block into the pseudo-map buffer.
// FUNCTION: C2 0x35e3f
// FUNCTION: C2WIN 0x004852e5
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

// Render the cursor / pointer diamond sprite onto the active panorama- map cell (x, y). Panorama
// coordinates are isometric: x walks columns, y walks rows of half-diamonds.
// FUNCTION: C2 0x35f0f
// FUNCTION: C2WIN 0x0048545c
void show_one_ptr(int x, int y)
{
    int cell_y;
    int cell_x;
    int pm_val;

    cell_y = pm_y + y;
    if (cell_y < 0 || cell_y >= 0xa1) return;
    cell_x = pm_x + x;
    if (cell_x < 0 || cell_x >= 0x51) return;

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

// Compute sprite_start = 24-bit little-endian int at ``fixt_data[data_ptr + 4..6]`` where
// ``data_ptr = sprite_image_no * 16 + 8``. Bounds-check (must be in [0, 0x4BAF0]) — out-of-range
// bumps ``sprite_error`` and returns silently.
// FUNCTION: C2 0x36165
// FUNCTION: C2WIN 0x004857da
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

// Draw the left half of a fixture diamond using the blitter for the current zoom level.
// FUNCTION: C2 0x361fd
// FUNCTION: C2WIN 0x0048592d
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

// Draws the right half of a pseudo-map diamond tile.
// FUNCTION: C2 0x36295
// FUNCTION: C2WIN 0x00485a5e
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

// Places overlay.
// FUNCTION: C2 0x3632d
// FUNCTION: C2WIN 0x00485b8f
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

// Places lefthalf overlay.
// FUNCTION: C2 0x363c5
// FUNCTION: C2WIN 0x00485cc6
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

// Places righthalf overlay.
// FUNCTION: C2 0x3645d
// FUNCTION: C2WIN 0x00485df7
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
