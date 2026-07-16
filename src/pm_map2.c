
#include "c2_data.h"


extern int  get_string_width(char *src, unsigned char *font);
extern void put_a_font_string(char *str, int x, int y, unsigned char *font, int color);
extern void font_list(int idx, int word_count, int x, int y, unsigned char *font, int color);
extern void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color);
extern void write_i_sprite(unsigned char *sprite_addr);
extern void write_i_left_sprite(unsigned char *sprite_addr);
extern void write_i_right_sprite(unsigned char *sprite_addr);

/* Assembly sprite-diamond blitters. */

// Repaint the region map: clear sprite_error, set the ambient sprite slot, then redraw base + top
// layers.
// FUNCTION: C2 0x39411
// FUNCTION: C2WIN 0x00445910
void show_regionmap(void)
{
    sprite_error = 0;
    set_this_ambient(1);
    show_regionmap_base();
    show_regionmap_top();
}

// Region-map base layer. Reads the byte-sized region_map cells (tile = base_kind), rotates via
// rotated2_map[tile].dir[map_dir/2] + 0x10, and stamps a diamond.
// FUNCTION: C2 0x39430
// FUNCTION: C2WIN 0x00445939
void show_regionmap_base(void)
{
    int i;
    int j;

    sprite_y    = pm_screen_y_start;
    sprite_x    = pm_screen_x_start;
    pm_shown_y  = pm_y;
    pm_y_clip   = 0;
    i = 0;
    pm_shown_x  = pm_x;

    /* top edge */
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(2);
            sprite_x += pm_diamond_width;
        } else if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
            place2_a_building_base(2);
        } else {
            if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
                (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind;
            sprite_image_no = rotated2_map[sprite_image_no].dir[map_direction >> 1];
            sprite_image_no += 0x10;
            place_diamond(2);
            sprite_x += pm_diamond_width;
        }
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits |= 2;
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    /* interior */
    mid2_line_with_sides_base();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        mid2_line_no_sides_base();
        mid2_line_with_sides_base();
    }

    /* bottom edge — same as top with style=1 */
    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(1);
            sprite_x += pm_diamond_width;
        } else if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
            place2_a_building_base(1);
        } else {
            if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
                (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind;
            sprite_image_no = rotated2_map[sprite_image_no].dir[map_direction >> 1];
            sprite_image_no += 0x10;
            place_diamond(1);
            sprite_x += pm_diamond_width;
        }
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits |= 2;
    }
}

// Region-map top layer (building tops + army sprites). Mirrors show_battlemap_top.
// FUNCTION: C2 0x396c5
// FUNCTION: C2WIN 0x00445cb5
void show_regionmap_top(void)
{
    int i;
    int j;
    int y;

    if (zoom_level == 1) {
        for (y = 0x18; y < 0x1bc; y++)
            show_internal_4point(0, y, 0);
    }

    sprite_y    = pm_screen_y_start;
    sprite_x    = pm_screen_x_start;
    pm_shown_y  = pm_y;
    pm_y_clip   = 0;

    /* top edge */
    for (i = 0, pm_shown_x = pm_x; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
                place2_a_building_top(2);
            } else {
                sprite_x += pm_diamond_width;
            }
            place2_sprite(0);
        }
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    /* interior */
    mid2_line_with_sides_top();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        mid2_line_no_sides_top();
        mid2_line_with_sides_top();
    }

    /* one more no_sides row above the bottom edge */
    sprite_x   = pm_screen_x_start;
    for (i = 0, pm_shown_x = pm_x; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
                place2_a_building_top(1);
            } else {
                sprite_x += pm_diamond_width;
            }
            place2_sprite(0);
        }
    }
    pm_shown_y++;
    sprite_y += pm_diamond_half_height;
    pm_y_clip = 0;

    bottom2_line_with_sides();
    bottom2_line_no_sides();
    bottom2_line_with_sides();
    bottom2_line_no_sides();
}

// Region-map base scanline (no edge clipping). All pm_screen_width cells use the full-diamond
// style.
// FUNCTION: C2 0x398a6
// FUNCTION: C2WIN 0x00445fa4
void mid2_line_no_sides_base(void)
{
    int i;
    int h;
    int dir;
    int t;

    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
        } else if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
            place2_a_building_base(0);
            print2_test_info();
            continue;
        } else {
            if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
                (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            t = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind;
            sprite_image_no = t;
            dir = map_direction >> 1;
            sprite_image_no = rotated2_map[t].dir[dir];
            sprite_image_no += 0x10;
        }
        place_diamond(0);
        sprite_x += pm_diamond_width;
        print2_test_info();
    }
    h = pm_diamond_half_height;
    sprite_y  += h;
    pm_shown_y++;
    pm_y_clip += h;
}

// Region-map base scanline with edge clipping. Leftmost cell uses place_lefthalf_diamond();
// rightmost uses place_righthalf_diamond(); middle (pm_screen_width-2) cells use full
// place_diamond().
// FUNCTION: C2 0x399cc
// FUNCTION: C2WIN 0x0044611a
void mid2_line_with_sides_base(void)
{
    int i;
    int h;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    /* leftmost half-diamond */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (((pm_shown_ptr) >= 0x0FFF0000)) {
        sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
    } else if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
        place2_a_building_base(3);
        goto left_edge_done;
    } else {
        if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
            (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits &= 0xfe;
            refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
        }
        sprite_image_no = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind;
        sprite_image_no = rotated2_map[sprite_image_no].dir[map_direction >> 1];
        sprite_image_no += 0x10;
    }
    place_lefthalf_diamond();
left_edge_done:
    if (!((pm_shown_ptr) >= 0x0FFF0000))
        (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits |= 2;
    sprite_x += pm_diamond_half_width;

    /* middle full diamonds */
    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
        } else if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
            place2_a_building_base(0);
            print2_test_info();
            continue;
        } else {
            if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
                (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind;
            sprite_image_no = rotated2_map[sprite_image_no].dir[map_direction >> 1];
            sprite_image_no += 0x10;
        }
        place_diamond(0);
        sprite_x += pm_diamond_width;
        print2_test_info();
    }

    /* rightmost half-diamond */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (((pm_shown_ptr) >= 0x0FFF0000)) {
        sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
    } else if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
        place2_a_building_base(4);
        goto right_edge_done;
    } else {
        if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
            (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits &= 0xfe;
            refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
        }
        sprite_image_no = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind;
        sprite_image_no = ((unsigned char *)rotated2_map)[(map_direction >> 1) + sprite_image_no * 4];
        sprite_image_no += 0x10;
    }
    place_righthalf_diamond();
right_edge_done:
    if (!((pm_shown_ptr) >= 0x0FFF0000))
        (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits |= 2;

    h = pm_diamond_half_height;
    sprite_y  += h;
    pm_shown_y++;
    pm_y_clip += h;
}

// Region-map top-layer scanline (no edge clipping). Walks pm_screen_width cells calling
// place2_sprite(0) (or place2_a_building_top(0) when tile > 0x7C).
// FUNCTION: C2 0x39c9f
// FUNCTION: C2WIN 0x004464de
void mid2_line_no_sides_top(void)
{
    int i;

    if (pm_x > 0) {
        sprite_x = pm_screen_x_start - pm_diamond_width;
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_x - 1];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place2_sprite(2);
    }
    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
                place2_a_building_top(0);
            } else {
                sprite_x += pm_diamond_width;
            }
            place2_sprite(0);
        }
    }

    if (pm_shown_x < 80) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place2_sprite(2);
    }

    sprite_y += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Region-map top-layer scanline with edge clipping. Left edge uses place2_sprite(1) (and
// place2_a_building_top(3) when a building); middle cells use 0; right uses 2 (4 for buildings).
// FUNCTION: C2 0x39dd3
// FUNCTION: C2WIN 0x004466a9
void mid2_line_with_sides_top(void)
{
    int i;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    /* left edge */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) {
        if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) place2_a_building_top(3);
        place2_sprite(1);
    }
    sprite_x += pm_diamond_half_width;

    /* middle */
    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
                place2_a_building_top(0);
            } else {
                sprite_x += pm_diamond_width;
            }
            place2_sprite(0);
        }
    }

    /* right edge */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) {
        if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) place2_a_building_top(4);
        place2_sprite(2);
    }

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Twin of mid2_line_with_sides_top for the bottom edge of the displayed slice. Wrapped in `if
// (pm_shown_y < 0xA1)` so it becomes a no-op once we’ve walked past the bottom of the region map.
// FUNCTION: C2 0x39f31
// FUNCTION: C2WIN 0x004468c6
void bottom2_line_with_sides(void)
{
    int i;

    if (pm_shown_y >= PM_H) return;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    /* left edge */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) {
        if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) place2_a_building_roof(3);
        place2_sprite(1);
    }
    sprite_x += pm_diamond_half_width;

    /* middle */
    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
                place2_a_building_roof(0);
            } else {
                sprite_x += pm_diamond_width;
            }
            place2_sprite(0);
        }
    }

    /* right edge */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) {
        if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) place2_a_building_roof(4);
        place2_sprite(2);
    }

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Twin of mid2_line_no_sides_top for the bottom edge. Same off-screen `if (pm_shown_y < 0xA1)`
// guard and place2_a_building_roof substitution as bottom2_line_with_sides.
// FUNCTION: C2 0x3a096
// FUNCTION: C2WIN 0x00446ae3
void bottom2_line_no_sides(void)
{
    int i;

    if (pm_shown_y >= PM_H) return;

    /* left spillover */
    if (pm_x > 0) {
        sprite_x = pm_screen_x_start - pm_diamond_width;
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_x - 1];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place2_sprite(2);
    }

    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            if ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind > 0x7c) {
                place2_a_building_roof(0);
            } else {
                sprite_x += pm_diamond_width;
            }
            place2_sprite(0);
        }
    }

    /* right spillover */
    if (pm_shown_x < 80) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place2_sprite(2);
    }

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Render the base diamond of a building cell on the region map.
// FUNCTION: C2 0x3a1cc
// FUNCTION: C2WIN 0x00446caa
void place2_a_building_base(int style)
{
    char bank_kind;
    char dummy;
    int word;
    int rot;
    unsigned char *data_base;

    sprite_image_no = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).gfx;
    bank_kind = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 0x1c; rot = (map_direction >> 1) + sprite_image_no * 4;

    if (bank_kind == 0) { data_base = house_data; sprite_image_no = rotated2_bank0[rot];
    } else if (bank_kind == 4) { data_base = building_data1; sprite_image_no = rotated2_bank1[rot];
    } else if (bank_kind == 8) { data_base = building_data2; sprite_image_no = rotated2_bank2[rot];
    } else if (bank_kind == 0xc) { data_base = building_data3; sprite_image_no = rotated2_bank3[rot];
    } else if (bank_kind == 0x10) {
        data_base = fixt_data; sprite_image_no = rotated2_map[sprite_image_no - 0x10].dir[map_direction >> 1] + 0x10; } else { return; }

    set_prov_ambient((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind);
    data_ptr     = sprite_image_no * 16 + 8;
    y_length     = data_base[data_ptr + 0xd];
    sprite_start = ((word = data_base[data_ptr + 5]) << 8)
                 + (word = data_base[data_ptr + 4])
                 + ((dummy = data_base[data_ptr + 6]) << 16);
    if (sprite_start > 0x4baf0) { sprite_error++; return; }
    if (sprite_start < 0) { sprite_error++; return; }
    if (y_length > 0xc8) { sprite_error++; return; }
    if (y_length < 0) { sprite_error++; return; }

    if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
        (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits &= 0xfe;
        refresh_a_bigger_square(sprite_x >> 4, (sprite_y - 0x30) >> 4);
    }

    if (style == 3) {
        if      (zoom_level == 0) place_i_large_diamond_lefthalf(data_base, 0);
        else if (zoom_level == 1) place_i_medium_diamond_lefthalf(data_base, 0);
        else                       place_i_small_diamond_lefthalf(data_base, 0);
    } else if (style == 4) {
        if      (zoom_level == 0) place_i_large_diamond_righthalf(data_base, 0);
        else if (zoom_level == 1) place_i_medium_diamond_righthalf(data_base, 0);
        else                       place_i_small_diamond_righthalf(data_base, 0);
    } else {
        if      (zoom_level == 0) place_i_large_diamond(data_base, style);
        else if (zoom_level == 1) place_i_medium_diamond(data_base, style);
        else                       place_i_small_diamond(data_base, style);
        sprite_x += pm_diamond_width;
    }
}

// Region-map building-top ("hat") diamond. Same five-bank image / rotation lookup as
// place2_a_building_base over the region's rotated2_bank0..3 tables; bank 0x10 routes through
// fixt_data via rotated2_map.
// FUNCTION: C2 0x3a402
// FUNCTION: C2WIN 0x0044707e
void place2_a_building_top(int style)
{
    unsigned char bank_kind;
    unsigned char *data_base;
    int rot;
    unsigned char tile;
    unsigned char hc;
    int edge_class;
    int x_disp;
    int y_disp;
    int text_w;
    unsigned char label;
    unsigned char army;
    unsigned char kind;
    int x_off;
    int y_off;
    int word;
    int dummy;

    sprite_image_no = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).gfx;

    bank_kind = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 0x1c; rot = (map_direction >> 1) + sprite_image_no * 4;

    if (bank_kind == 0) { data_base = house_data; sprite_image_no = rotated2_bank0[rot] & 0xff; }
    else if (bank_kind == 4) { data_base = building_data1; sprite_image_no = rotated2_bank1[rot] & 0xff; }
    else if (bank_kind == 8) { data_base = building_data2; sprite_image_no = rotated2_bank2[rot] & 0xff; }
    else if (bank_kind == 0xc) { data_base = building_data3; sprite_image_no = (unsigned char)rotated2_bank3[rot]; }
    else if (bank_kind == 0x10) {
        data_base = fixt_data; sprite_image_no = (rotated2_map[sprite_image_no - 0x10].dir[map_direction >> 1] & 0xff) + 0x10; }
    else return;

    data_ptr     = sprite_image_no * 16 + 8;
    y_length     = data_base[data_ptr + 0xd];
    hc           = data_base[data_ptr + 0xc];
    sprite_start = data_base[data_ptr + 4]
                 + (data_base[data_ptr + 5] << 8)
                 + (data_base[data_ptr + 6] << 16);
    if (zoom_level == 0)      sprite_hat_start = sprite_start + 0x384;
    else if (zoom_level == 1) sprite_hat_start = sprite_start + 0xc4;
    else                      sprite_hat_start = sprite_start + 0x24;

    if (sprite_start > 0x4baf0) { sprite_error++; return; }
    if (sprite_start < 0) { sprite_error++; return; }
    if (y_length > 0xc8) { sprite_error++; return; }
    if (y_length < 0) { sprite_error++; return; }

    if (style == 3) {
        if (y_length != 0) {
            if (hc == 2) {
                if      (zoom_level == 0) write_large_diamond_lefthat(data_base, pm_y_clip);
                else if (zoom_level == 1) write_medium_diamond_lefthat(data_base, pm_y_clip);
                else                      write_small_diamond_lefthat(data_base, pm_y_clip);
            } else if (hc == 4) {
                if      (zoom_level == 0) write_large_diamond_righthalfhat(data_base, pm_y_clip, 2);
                else if (zoom_level == 1) write_medium_diamond_righthalfhat(data_base, pm_y_clip, 2);
                else                      write_small_diamond_righthalfhat(data_base, pm_y_clip, 2);
            }
        }
    } else if (style == 4) {
        if (y_length != 0) {
            if (hc == 2) {
                if      (zoom_level == 0) write_large_diamond_righthat(data_base, pm_y_clip);
                else if (zoom_level == 1) write_medium_diamond_righthat(data_base, pm_y_clip);
                else                      write_small_diamond_righthat(data_base, pm_y_clip);
            }
            if (hc == 3) {
                if      (zoom_level == 0) write_large_diamond_lefthalfhat(data_base, pm_y_clip, 2);
                else if (zoom_level == 1) write_medium_diamond_lefthalfhat(data_base, pm_y_clip, 2);
                else                      write_small_diamond_lefthalfhat(data_base, pm_y_clip, 2);
            }
        }
    } else {
        if (style != 2 && y_length != 0) {
            if (hc == 2) {
                if      (zoom_level == 0) write_large_diamond_hat(data_base, pm_y_clip);
                else if (zoom_level == 1) write_medium_diamond_hat(data_base, pm_y_clip);
                else                      write_small_diamond_hat(data_base, pm_y_clip);
            } else if (hc == 3) {
                if      (zoom_level == 0) write_large_diamond_lefthalfhat(data_base, pm_y_clip, 0);
                else if (zoom_level == 1) write_medium_diamond_lefthalfhat(data_base, pm_y_clip, 0);
                else                      write_small_diamond_lefthalfhat(data_base, pm_y_clip, 0);
            } else if (hc == 4) {
                if      (zoom_level == 0) write_large_diamond_righthalfhat(data_base, pm_y_clip, 0);
                else if (zoom_level == 1) write_medium_diamond_righthalfhat(data_base, pm_y_clip, 0);
                else                      write_small_diamond_righthalfhat(data_base, pm_y_clip, 0);
            }
        }
        sprite_x += pm_diamond_width;
    }

    tile = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind;
    if (tile >= 0x98 && tile <= 0x9f) {
        old_sprite_y = sprite_y; old_sprite_x = sprite_x;
        if (tile == 0x98 || tile == 0x9c)      edge_class = 0;
        else if (tile == 0x99 || tile == 0x9d) edge_class = 2;
        else if (tile == 0x9a || tile == 0x9e) edge_class = 4;
        else                                   edge_class = 6;

        label = region_borders[province_is].u.dir[edge_class >> 1];
        if (label != 0) label++;
        get_text_pointer(6, label);
        text_w = get_string_width(text_pointer, font1);

        if (map_direction == 2)      edge_class += 6;
        else if (map_direction == 4) edge_class += 4;
        else if (map_direction == 6) edge_class += 2;
        if (edge_class >= 8) edge_class %= 8;

        if (edge_class == 0)      { x_disp = -8; y_disp = -8; }
        else if (edge_class == 2) { x_disp = 0; y_disp = 0x28; }
        else if (edge_class == 4) { x_disp = -(text_w + 0x3c); y_disp = 0x2c; }
        else                      { x_disp = -(text_w + 0x3c); y_disp = -0xc; }

        font_screen_limit = 1;
        put_a_font_string(text_pointer, sprite_x + x_disp, sprite_y + y_disp, font1, 0x20);
        font_screen_limit = 1;
        sprite_y = old_sprite_y; sprite_x = old_sprite_x;
        font_list(0x1b, 0, sprite_x + x_disp, sprite_y + y_disp - 0x14, font1, 0x20);
        sprite_y = old_sprite_y; sprite_x = old_sprite_x;
    }
    else if (tile == 0xd4) {
        army = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).occupant & 0xf0;
        kind = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).occupant & 0xf;
        army >>= 4;
        if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 0x40) == 0) return;
        sprite_image_no = army + 9;
        x_off = reg_type_x_off[zoom_level][map_direction / 2];
        y_off = reg_type_y_off[zoom_level][map_direction / 2];
        if (style == 1) x_off -= pm_diamond_half_width;

        data_ptr = sprite_image_no * 16 + 8;
        data_base = tops_data + data_ptr; sprite_start = ((word = data_base[5]) << 8)
                     + (word = data_base[4])
                     + ((dummy = data_base[6]) << 16);
        sprite_width = (word = data_base[0]) + ((word = data_base[1]) << 8);
        sprite_height = (data_base[2]) + (data_base[3] << 8);

        if (sprite_start > 0x4baf0) { sprite_error++; return; }
        if (sprite_start < 0)       { sprite_error++; return; }
        if (sprite_width > 0x280)   { sprite_error++; return; }
        if (sprite_height > 0x1e0)  { sprite_error++; return; }

        old_sprite_x = sprite_x; old_sprite_y = sprite_y;
        sprite_x += x_off; sprite_y += y_off;

        xclip(pm_screen_x_start, 0x1de);
        yclip(0x18, 0x1da);
        if (yclipped == 5) goto put_back;
        if      (xclipped == 1) write_i_left_sprite(tops_data);
        else if (xclipped == 2) write_i_right_sprite(tops_data);
        else                    write_i_sprite(tops_data);
put_back: sprite_x = old_sprite_x; sprite_y = old_sprite_y;
    }
}

// Region-map roof slice of a building. Snapshot sprite_y, do the same five-bank image lookup as
// place2_a_building_base, then: * Early-out when y_length <= pm_y_clip (entire roof above the
// visible slice): middle styles bump sprite_x by pm_diamond_width, edge styles just exit.
// FUNCTION: C2 0x3ab26
// FUNCTION: C2WIN 0x00447bf3
void place2_a_building_roof(int style)
{
    int rot;
    unsigned char bank_kind;
    unsigned char *data_base;
    unsigned char height_class;

    old_sprite_y = sprite_y;
    sprite_image_no = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).gfx;
    bank_kind = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 0x1c;
    rot = (map_direction >> 1) + sprite_image_no * 4;

    if (bank_kind == 0) {
        data_base = house_data;
        sprite_image_no = rotated2_bank0[rot];
    } else if (bank_kind == 4) {
        data_base = building_data1;
        sprite_image_no = rotated2_bank1[rot];
    } else if (bank_kind == 8) {
        data_base = building_data2;
        sprite_image_no = rotated2_bank2[rot];
    } else if (bank_kind == 0xc) {
        data_base = building_data3;
        sprite_image_no = rotated2_bank3[rot];
    } else if (bank_kind == 0x10) {
        data_base = fixt_data;
        sprite_image_no = (rotated2_map[sprite_image_no - 0x10].dir[map_direction >> 1] & 0xff) + 0x10;
    } else {
        return;
    }

    data_ptr     = sprite_image_no * 16 + 8;
    y_length     = data_base[data_ptr + 0xd];
    if (y_length <= pm_y_clip) {
        if (style < 3)
            sprite_x += pm_diamond_width;
        return;
    }

    height_class = data_base[data_ptr + 0xc];
    sprite_start = data_base[data_ptr + 4]
                 + (data_base[data_ptr + 5] << 8)
                 + (data_base[data_ptr + 6] << 16);
    if      (zoom_level == 0) sprite_hat_start = sprite_start + 0x384;
    else if (zoom_level == 1) sprite_hat_start = sprite_start + 0xc4;
    else                       sprite_hat_start = sprite_start + 0x24;

    if (sprite_start > 0x4baf0) {
        sprite_error++;
    } else if (sprite_start < 0) {
        sprite_error++;
    } else if (y_length > 0xc8) {
        sprite_error++;
    } else if (y_length < 0) {
        sprite_error++;
    } else {
        sprite_y = pm_screen_y_end - 1;
        if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
            (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits &= 0xfe;
            refresh_a_bigger_square(sprite_x >> 4, (sprite_y - 0x30) >> 4);
        }
        y_length -= pm_y_clip;

        if (zoom_level == 0) {
            if (height_class == 2) sprite_hat_start += pm_y_clip * 0x3a;
            else                   sprite_hat_start += pm_y_clip * 30;
        } else if (zoom_level == 1) {
            if (height_class == 2) sprite_hat_start += pm_y_clip * 0x1a;
            else                   sprite_hat_start += pm_y_clip * 14;
        } else {
            if (height_class == 2) sprite_hat_start += pm_y_clip * 10;
            else                   sprite_hat_start += pm_y_clip * 6;
        }

        if (style == 3) {
            if (height_class == 2) {
                if      (zoom_level == 0) write_large_diamond_leftroof(data_base);
                else if (zoom_level == 1) write_medium_diamond_leftroof(data_base);
                else                       write_small_diamond_leftroof(data_base);
            } else if (height_class == 4) {
                if      (zoom_level == 0) write_large_diamond_righthalfroof(data_base, 2);
                else if (zoom_level == 1) write_medium_diamond_righthalfroof(data_base, 2);
                else                       write_small_diamond_righthalfroof(data_base, 2);
            }
        } else if (style == 4) {
            if (height_class == 2) {
                if      (zoom_level == 0) write_large_diamond_rightroof(data_base);
                else if (zoom_level == 1) write_medium_diamond_rightroof(data_base);
                else                       write_small_diamond_rightroof(data_base);
            }
            if (height_class == 3) {
                if      (zoom_level == 0) write_large_diamond_lefthalfroof(data_base, 2);
                else if (zoom_level == 1) write_medium_diamond_lefthalfroof(data_base, 2);
                else                       write_small_diamond_lefthalfroof(data_base, 2);
            }
        } else {
            if (height_class == 2) {
                if      (zoom_level == 0) write_large_diamond_roof(data_base);
                else if (zoom_level == 1) write_medium_diamond_roof(data_base);
                else                       write_small_diamond_roof(data_base);
            } else if (height_class == 3) {
                if      (zoom_level == 0) write_large_diamond_lefthalfroof(data_base, 0);
                else if (zoom_level == 1) write_medium_diamond_lefthalfroof(data_base, 0);
                else                       write_small_diamond_lefthalfroof(data_base, 0);
            } else if (height_class == 4) {
                if      (zoom_level == 0) write_large_diamond_righthalfroof(data_base, 0);
                else if (zoom_level == 1) write_medium_diamond_righthalfroof(data_base, 0);
                else                       write_small_diamond_righthalfroof(data_base, 0);
            }
            sprite_x += pm_diamond_width;
        }
        sprite_y = old_sprite_y;
    }
}

// Region-map army renderer. Reads the cell's army index from occupant and dispatches up to four
// sprite passes: 1.
// FUNCTION: C2 0x3af6b
// FUNCTION: C2WIN 0x004482d9
void place2_sprite(int style)
{
    int extra_event;
    int dy;
    int dx;
    int dir;
    unsigned char *people;
    unsigned char fl;
    int y;

    army_a = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).occupant;
    extra_event = 0;
    if (flag_mode != 0)
        extra_event = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).place_state;

    if (army_a != 0) {
        if (army_a < 0) return;
        if (army_a >= 0x1a) return;
        if (army_list[army_a].exists == 0) return;
        if (army_list[army_a].exists == 3) return;
        if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).terrain & 1) != 0) return;

        if      (army_list[army_a].type <= 1) set_this_ambient(9);
        else if (army_list[army_a].type <= 4) set_this_ambient(8);
        else if (army_list[army_a].type == 5) set_this_ambient(0xa);

        dir = army_list[army_a].world_dir - map_direction;
        if (dir < 0) dir += 8;

        if (zoom_level == 0) {
            dx = walking_x_ofsets_zoom0[dir * 16 + army_list[army_a].target_kind];
            dy = walking_y_ofsets_zoom0[dir * 16 + army_list[army_a].target_kind];
        } else if (zoom_level == 1) {
            dx = walking_x_ofsets_zoom1[dir * 16 + army_list[army_a].target_kind];
            dy = walking_y_ofsets_zoom1[dir * 16 + army_list[army_a].target_kind];
        } else {
            dx = walking_x_ofsets_zoom2[dir * 16 + army_list[army_a].target_kind];
            dy = walking_y_ofsets_zoom2[dir * 16 + army_list[army_a].target_kind];
        }

        if (style == 1) {
            dx -= 2;
        } else if (style == 2) {
            dx += pm_diamond_half_width - 2;
        } else {
            dx += pm_diamond_half_width - 2 - pm_diamond_width;
        }

        if      (zoom_level == 0) dy += 0x18;
        else if (zoom_level == 1) dy += 8;
        else                       dy += 2;

        /* --- Pass 1: main body --- */
        sprite_image_no = army_list[army_a].sprite_image;
        data_ptr        = sprite_image_no * 16 + 8;
        people          = people_data + data_ptr; sprite_start = people[4] + (people[5] << 8) + (people[6] << 16);
        sprite_width    = (people[0]) + (people[1] << 8);
        sprite_height   = people[2] + (people[3] << 8);
        if (sprite_start > 0x4baf0) { sprite_error++; return; }
        if (sprite_width <= 0)      { sprite_error++; return; }
        if (sprite_width > 0x12c)   { sprite_error++; return; }
        if (sprite_height <= 0)     { sprite_error++; return; }
        if (sprite_height > 0x12c)  { sprite_error++; return; }

        /* --- Read sprite2 header (optional) --- */
        if (army_list[army_a].sprite_anim != 0) {
            sprite2_image_no = army_list[army_a].sprite_anim;
            data_ptr         = sprite2_image_no * 16 + 8;
            people           = people_data + data_ptr; sprite2_start = (people[6] << 16) + ((people[4]) + (people[5] << 8));
            sprite2_height   = (people[2]) + (people[3] << 8);
        } else {
            sprite2_height = 0;
        }

        /* --- Read sprite3 header (optional) --- */
        if (army_list[army_a].sprite_dir != 0) {
            sprite3_image_no = army_list[army_a].sprite_dir;
            data_ptr         = sprite3_image_no * 16 + 8;
            people           = people_data + data_ptr; sprite3_start = people[4] + (people[5] << 8) + (people[6] << 16);
            sprite3_height   = people[2] + (people[3] << 8);
        } else {
            sprite3_height = 0;
        }

        /* --- Snapshot + centre + draw body --- */
        old_sprite_x = sprite_x; old_sprite_y = sprite_y;
        sprite_x    += dx; sprite_y += dy;
        sprite_x    -= sprite_width >> 1;
        sprite_y    -= sprite_height + sprite2_height + sprite3_height;
        sprite_base_x = sprite_x;
        sprite_base_y = sprite_y;
        refresh_region_sprite_square(sprite_x >> 4, sprite_y >> 4);
        xclip(pm_screen_x_start, 0x1de);
        if (zoom_level == 1) yclip(0x18, 0x1d8);
        else                  yclip(0x18, 0x1da);
        if (yclipped == 5) goto after_body;
        if      (xclipped == 1) write_i_left_sprite(people_data);
        else if (xclipped == 2) write_i_right_sprite(people_data);
        else                    write_i_sprite(people_data);
after_body:

        /* --- Pass 2: sprite2 stacked above body --- */
        if (army_list[army_a].sprite_anim != 0) {
            sprite_x        = sprite_base_x;
            sprite_y        = sprite_base_y;
            sprite_y       += sprite_height;
            sprite_base_y   = sprite_y;
            sprite_image_no = sprite2_image_no; sprite_start = sprite2_start; sprite_height = sprite2_height;
            if (sprite_start > 0x4baf0) { sprite_error++; return; }
            if (sprite_height <= 0)     { sprite_error++; return; }
            if (sprite_height > 0x12c)  { sprite_error++; return; }
            xclip(pm_screen_x_start, 0x1de);
            if (zoom_level == 1) yclip(0x18, 0x1d8);
            else                  yclip(0x18, 0x1da);
            if (yclipped == 5) goto after_sprite2;
            if      (xclipped == 1) write_i_left_sprite(people_data);
            else if (xclipped == 2) write_i_right_sprite(people_data);
            else                    write_i_sprite(people_data);
after_sprite2:

            if      (zoom_level == 0) army_list[army_a].map_x = sprite_x + 8;
            else if (zoom_level == 1) army_list[army_a].map_x = sprite_x + 4;
            else                       army_list[army_a].map_x = sprite_x;
            army_list[army_a].map_y = sprite_y;
        }

        /* --- Pass 3: sprite3 stacked above sprite2 --- */
        if (army_list[army_a].sprite_dir != 0) {
            sprite_x        = sprite_base_x;
            sprite_y        = sprite_base_y;
            sprite_y       += sprite_height;
            sprite_image_no = sprite3_image_no; sprite_start = sprite3_start; sprite_height = sprite3_height;
            if (sprite_start > 0x4baf0) { sprite_error++; return; }
            if (sprite_height <= 0)     { sprite_error++; return; }
            if (sprite_height > 0x12c)  { sprite_error++; return; }
            xclip(pm_screen_x_start, 0x1de);
            if (zoom_level == 1) yclip(0x18, 0x1d8);
            else                  yclip(0x18, 0x1da);
            if (army_list[army_a].morale_timer != 0) goto after_sprite3;
            if (yclipped == 5) goto after_sprite3;
            if      (xclipped == 1) write_i_left_sprite(people_data);
            else if (xclipped == 2) write_i_right_sprite(people_data);
            else                    write_i_sprite(people_data);
after_sprite3:
            if      (zoom_level == 0) army_list[army_a].map_x = sprite_x + 8;
            else if (zoom_level == 1) army_list[army_a].map_x = sprite_x + 4;
            else                       army_list[army_a].map_x = sprite_x;
            army_list[army_a].map_y = sprite_y;
        }

        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }

    fl  = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 0xc0;
    if (((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).base_kind) == 0xd4)
        fl = 0;
    if (fl != 0) {
        dy = 0;
        if (style == 1) {
            dx = -2;
        } else {
            dx = pm_diamond_half_width - 2;
            if (style != 2)
                dx -= pm_diamond_width;
        }
        dy += pm_diamond_half_height;

        if ((fl & 0x80) != 0) {
            sprite_image_no = 6;
            sprite_width    = 0x10;
            sprite_height   = 0x1c;
        } else if ((fl & 0x40) != 0) {
            sprite_image_no = 8;
            sprite_width    = 7;
            sprite_height   = 7;
        }
        data_ptr     = sprite_image_no * 16 + 8;
        sprite_start = (mice[data_ptr + 5] << 8) + (mice[data_ptr + 4]) + (mice[data_ptr + 6] << 16);
        if (sprite_start > 0x4baf0) { sprite_error++; return; }
        if (sprite_start < 0)       { sprite_error++; return; }
        old_sprite_x = sprite_x; old_sprite_y = sprite_y;
        sprite_x    += dx; sprite_y += dy; y = sprite_y - sprite_height;
        if      (zoom_level == 0) { sprite_x -= sprite_width >> 1; sprite_y = y; }
        else if (zoom_level == 1) { sprite_x -= sprite_width >> 2; sprite_y = y; }
        else                      { sprite_x -= sprite_width >> 3; sprite_y = y; }
        refresh_sprite_square(sprite_x >> 4, sprite_y >> 4);
        xclip(pm_screen_x_start, 0x1de);
        if (zoom_level == 1) yclip(0x18, 0x1d8);
        else                  yclip(0x18, 0x1da);
        if (yclipped == 5) goto restore_overlay;
        if      (xclipped == 1) write_i_left_sprite(mice);
        else if (xclipped == 2) write_i_right_sprite(mice);
        else                    write_i_sprite(mice);
restore_overlay:
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }

    if (extra_event != 0) {
        dy = 0;
        if (style == 1) {
            dx = -2;
        } else {
            dx = pm_diamond_half_width - 2;
            if (style != 2)
                dx -= pm_diamond_width;
        }
        dy += pm_diamond_half_height;

        if (extra_event == 3)
            sprite_image_no = zoom_level + 0xe;
        else
            sprite_image_no = zoom_level + 0xb;
        data_ptr      = sprite_image_no * 16 + 8;
        sprite_start  = mice[data_ptr + 4] + (mice[data_ptr + 5] << 8) + (mice[data_ptr + 6] << 16);
        sprite_width  = (mice[data_ptr + 0]) + (mice[data_ptr + 1] << 8);
        sprite_height = (mice[data_ptr + 2]) + (mice[data_ptr + 3] << 8);
        if (sprite_start > 0x4baf0) { sprite_error++; return; }
        if (sprite_width <= 0)      { sprite_error++; return; }
        if (sprite_width > 0x12c)   { sprite_error++; return; }
        if (sprite_height <= 0)     { sprite_error++; return; }
        if (sprite_height > 0x12c)  { sprite_error++; return; }
        old_sprite_x = sprite_x; old_sprite_y = sprite_y;
        sprite_x    += dx;
        sprite_y    += dy;
        sprite_y    -= sprite_height;
        refresh_sprite_square(sprite_x >> 4, sprite_y >> 4);
        xclip(pm_screen_x_start, 0x1de);
        if (zoom_level == 1) yclip(0x18, 0x1d8);
        else                  yclip(0x18, 0x1da);
        if (yclipped == 5) goto restore_event;
        if      (xclipped == 1)
            write_i_left_sprite(mice);
        else if (xclipped == 2)
            write_i_right_sprite(mice);
        else                    write_i_sprite(mice);
restore_event:
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }
}

// Region-map debug overlay. test_mode1 compresses two region flags into a tiny status value (bit
// 0x40 from +6 and bit 0x20 from +3), while test_mode2 prints signed region_map+2.
// FUNCTION: C2 0x3ba9d
// FUNCTION: C2WIN 0x00449419
void print2_test_info(void)
{
    int v;
    int b3;

    if (test_mode1 != 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) return;
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        v = ((*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).outside &= 0x40);
        b3 = (*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).edge_bits & 0x20;
        if (v != 0 && b3 != 0) v = 1;
        else if (b3 != 0) v = 2;
        else v = 0;
        font_no(v, 0x20, " ",
                sprite_x + 0x14 - pm_diamond_width, sprite_y + 0xa,
                font1, 0x20);
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    } else if (test_mode2 != 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) return;
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        v = (signed char)(*(struct region_cell *)((unsigned char *)region_map + (pm_shown_ptr))).place_state;
        font_no(v, 0x20, " ",
                sprite_x + 0x14 - pm_diamond_width, sprite_y + 0xa,
                font1, 0x20);
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }
}
