// D:\C2\CODE\pm_map1.c

#include "pm_map1.h"
#include "c2_data.h"

struct byte_delta_rec fire_offs[16] = {
    { 0, 0 },
    { 10, -3 },
    { 21, -2 },
    { 31, 3 },
    { 44, 0 },
    { 34, -5 },
    { 16, 2 },
    { 37, -3 },
    { 28, -8 },
    { 39, -3 },
    { 22, -12 },
    { 18, -6 },
    { 36, -2 },
    { 8, -3 },
    { 37, 1 },
    { 10, 2 }
};

int plague_offs[4] = { -49675264, 52100629, -31981554, -49872368 };

int aquaduct_tops[10] = { 56, 57, 58, 53, 54, 55, 25, 25, 25, 25 };

int aquaduct_tops2[10] = { 53, 54, 55, 56, 57, 58, 25, 25, 25, 25 };

struct int_delta_rec arena_top_data[3][4] = {
    { { 0, 4 },  { 61, -27 }, { 1, -57 },  { -59, -27 } },
    { { 4, 1 },  { 31, -13 }, { 4, -27 },  { -24, -13 } },
    { { 2, 1 },  { 13, -5 },  { 2, -12 },  { -11, -5 } }
};

struct int_delta_rec colos_top_data[3][4] = {
    { { -2, -18 }, { 59, -48 }, { -1, -78 }, { -61, -48 } },
    { { 0, -10 },  { 27, -24 }, { 0, -38 },  { -28, -24 } },
    { { -2, -2 },  { 11, -9 },  { 0, -14 },  { -11, -9 } }
};

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
int city_anim64;
int city_anim128;
int city_anim32;
int city_anim8;
int city_anim16;
int overlay0_empty_mode;
int cmu_count[5];


extern void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color);
extern void write_i_sprite(unsigned char *sprite_addr);
extern void write_i_left_sprite(unsigned char *sprite_addr);
extern void write_i_right_sprite(unsigned char *sprite_addr);

// FUNCTION: C2 0x364F5
// WIN: 0x0045b1e0
// Lines 45–63
//
// Per-frame city-map renderer: advances animation counters, chooses
// overlay empty-mode, invalidates map updates requested by landfill,
// then draws base/sprites/top layers and counts down update_map.
void show_citymap(void)
{
    sprite_error = 0;
    cmu_count[0]++;
    if (cmu_count[0] > 3) {
        cmu_count[0] = 0;
    }

    city_anim128++;
    if (city_anim128 >= 0x80) {
        city_anim128 = 0;
    }
    city_anim64 = city_anim128 >> 1;
    city_anim32 = city_anim128 >> 2;
    city_anim16 = city_anim128 >> 3;
    city_anim8  = city_anim128 >> 4;

    if (ov_map_mode == 0 || ov_map_mode == 1 ||
        ov_map_mode == 4 || ov_map_mode == 8) {
        overlay0_empty_mode = 1;
    } else {
        overlay0_empty_mode = 0;
    }

    if (update_landfill != 0) {
        update_map = 1;
    }
    show_citymap_base();
    if (overlays_on != 1) {
        show_citymap_sprites();
    }
    show_citymap_top();
    if (update_map != 0) {
        update_map--;
    }
}

// FUNCTION: C2 0x365DA
// WIN: 0x0045b314
// Lines 65–149
//
// City-map base layer.  Reads the base tile from the city_cell at
// pm_shown_ptr and dispatches buildings (tile >= 0x78) to
// place_a_building_base; otherwise looks up the rotated base sprite
// via rotated_map and stamps a diamond.  A non-zero show_overlay
// return short-circuits the normal base draw for that cell.
void show_citymap_base(void)
{
    int i;
    int j;

    sprite_y    = pm_screen_y_start;
    sprite_x    = pm_screen_x_start;
    pm_shown_y  = pm_y;
    pm_y_clip   = 0;
    i = 0;
    pm_shown_x  = pm_x;

    /* top edge — style 2 */
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(2);
            sprite_x += pm_diamond_width;
        } else if (show_overlay(2)) {
            /* overlay handled this cell */
        } else if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
            place_a_building_base(2);
        } else {
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
                (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
            sprite_image_no = rotated_map[sprite_image_no].dir[map_direction >> 1];
            sprite_image_no += 0x10;
            place_diamond(2);
            sprite_x += pm_diamond_width;
        }
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits |= 2;
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    /* interior */
    mid_line_with_sides_base();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        mid_line_no_sides_base();
        mid_line_with_sides_base();
    }

    /* bottom edge — style 1 */
    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(1);
            sprite_x += pm_diamond_width;
        } else if (show_overlay(1)) {
            /* overlay handled */
        } else if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
            place_a_building_base(1);
        } else {
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
                (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
            sprite_image_no = rotated_map[sprite_image_no].dir[map_direction >> 1];
            sprite_image_no += 0x10;
            place_diamond(1);
            sprite_x += pm_diamond_width;
        }
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits |= 2;
    }
}

// FUNCTION: C2 0x3689E
// WIN: 0x0045b6bc
// Lines 152–185
//
// City-map sprite layer.  Top edge: place_sprite for each
// non-virtual cell.  Interior: alternating
// sprites_with_sides / sprites_no_sides pair rows.
void show_citymap_sprites(void)
{
    int i;
    int j;

    sprite_y    = pm_screen_y_start;
    sprite_x    = pm_screen_x_start;
    pm_shown_y  = pm_y;
    pm_y_clip   = 0;
    pm_shown_x  = pm_x;

    for (i = 0; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            place_sprite(0);
        sprite_x += pm_diamond_width;
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    sprites_with_sides();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        sprites_no_sides();
        sprites_with_sides();
    }

    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            place_sprite(0);
        sprite_x += pm_diamond_width;
    }
}

// FUNCTION: C2 0x369CA
// WIN: 0x0045b874
// Lines 187–236
//
// City-map top layer: building tops via place_a_building_top and
// road / bridge overhead via top_it.  Status-bar clear when
// zoom_level == 1.  Per cell, are_overlays_on() short-circuits the
// draw; otherwise buildings (tile >= 0x78) get place_a_building_top
// and the overhead flag (edge_bits & 0x80) triggers top_it.
void show_citymap_top(void)
{
    int i;
    int j;
    int k;

    if (zoom_level == 1) for (k = 0x18; k < 0x1bc; k++) show_internal_4point(0, k, 0);

    sprite_y    = pm_screen_y_start;
    sprite_x    = pm_screen_x_start;
    pm_shown_y  = pm_y;
    pm_y_clip   = 0;
    i = 0;
    pm_shown_x  = pm_x;

    /* top edge */
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];

        if (are_overlays_on() != 0) sprite_x += pm_diamond_width;
        else if (((pm_shown_ptr) >= 0x0FFF0000)) sprite_x += pm_diamond_width;
        else {
            if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) place_a_building_top(2);
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x80) != 0) top_it(0);
            sprite_x += pm_diamond_width;
        }
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    /* interior */
    mid_line_with_sides_top();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        mid_line_no_sides_top();
        mid_line_with_sides_top();
    }

    /* one more pre-bottom row */
    sprite_x   = pm_screen_x_start;
    i = 0; pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];

        if (are_overlays_on() != 0) sprite_x += pm_diamond_width;
        else if (((pm_shown_ptr) >= 0x0FFF0000)) sprite_x += pm_diamond_width;
        else {
            if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) place_a_building_top(1);
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x80) != 0) top_it(0);
            sprite_x += pm_diamond_width;
        }
    }
    pm_shown_y++;
    sprite_y += pm_diamond_half_height;
    pm_y_clip = 0;

    bottom_line_with_sides();
    bottom_line_no_sides();
    bottom_line_with_sides();
    bottom_line_no_sides();
}

// FUNCTION: C2 0x36BFE
// WIN: 0x0045bb2b
// Lines 240–265
//
// Sprite-layer scanline (no edge clipping).  Left/right
// one-cell spillovers so figures on columns just outside
// the visible range still get their clipped tails drawn
// into the visible area.
void sprites_no_sides(void)
{
    int i;

    /* left spillover */
    if (pm_x > 0) {
        sprite_x = pm_screen_x_start - pm_diamond_width;
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_x - 1];
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            place_sprite(0);
    }

    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            place_sprite(0);
        sprite_x += pm_diamond_width;
    }

    /* right spillover */
    if (pm_shown_x < 0x50) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x];
        if (!((pm_shown_ptr) >= 0x0FFF0000))
            place_sprite(0);
    }

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x36CFC
// WIN: 0x0045bcb4
// Lines 267–289
//
// Draw one pseudo-map sprite row including the left/right side caps.
// The first tile is drawn as side=1, middle tiles as side=0, and the
// rightmost cap as side=0.  Advances sprite_y, pm_shown_y, and y clip
// by one diamond half-height.
void sprites_with_sides(void)
{
    int i;

    pm_shown_x = pm_x;
    sprite_x = pm_screen_x_start;
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place_sprite(1);
    sprite_x += pm_diamond_half_width;

    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place_sprite(0);
        sprite_x += pm_diamond_width;
    }
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place_sprite(0);
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x36DFB
// WIN: 0x0045be2a
// Lines 293–327
//
// City-map base interior scanline (no edge clipping).
// Mirrors mid2_line_no_sides_base over city_map +
// rotated_map + the >= 0x78 building threshold.
void mid_line_no_sides_base(void)
{
    int i;
    int dir;

    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            if (update_map != 0 || sprite_image_no >= 7) place_diamond(0);
            sprite_x += pm_diamond_width;
            continue;
        } else if (show_overlay(0)) {
            continue;
        } else if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
            place_a_building_base(0);
            continue;
        } else {
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
                (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
            dir = map_direction >> 1;
            sprite_image_no = rotated_map[sprite_image_no].dir[dir];
            sprite_image_no += 0x10;
        }
        place_diamond(0);
        sprite_x += pm_diamond_width;
    }
    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x36F49
// WIN: 0x0045bfd3
// Lines 329–410
//
// City-map base scanline with edge clipping.  Leftmost
// cell uses place_lefthalf_diamond + show_left_overlay;
// rightmost uses place_righthalf_diamond +
// show_right_overlay; middle cells use place_diamond +
// show_overlay.  Buildings on edges call
// place_a_building_base with style 3 (left) or 4 (right).
void mid_line_with_sides_base(void)
{
    int i;
    int dir;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    /* leftmost half-diamond */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (((pm_shown_ptr) >= 0x0FFF0000)) {
        sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
        if (update_map != 0 || sprite_image_no >= 7) place_lefthalf_diamond();
    } else if (show_left_overlay(2)) {
        /* overlay handled this cell */
    } else if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
        place_a_building_base(3);
    } else {
        if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
            (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits &= 0xfe;
            refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
        }
        sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
        dir = map_direction >> 1;
        sprite_image_no = rotated_map[sprite_image_no].dir[dir];
        sprite_image_no += 0x10;
        place_lefthalf_diamond();
    }
    if (!((pm_shown_ptr) >= 0x0FFF0000))
        (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits |= 2;
    sprite_x += pm_diamond_half_width;

    /* middle full diamonds */
    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            if (update_map != 0 || sprite_image_no >= 7) place_diamond(0);
            sprite_x += pm_diamond_width;
            continue;
        } else if (show_overlay(0)) {
            continue;
        } else if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
            place_a_building_base(0);
            continue;
        } else {
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
                (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
            dir = map_direction >> 1;
            sprite_image_no = rotated_map[sprite_image_no].dir[dir];
            sprite_image_no += 0x10;
        }
        place_diamond(0);
        sprite_x += pm_diamond_width;
    }

    /* rightmost half-diamond */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (((pm_shown_ptr) >= 0x0FFF0000)) {
        sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
        if (update_map != 0 || sprite_image_no >= 7) place_righthalf_diamond();
    } else if (show_right_overlay(0)) {
        /* overlay handled this cell */
    } else if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
        place_a_building_base(4);
    } else {
        if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
            (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits &= 0xfe;
            refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
        }
        sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
        dir = map_direction >> 1;
        sprite_image_no = rotated_map[sprite_image_no].dir[dir];
        sprite_image_no += 0x10;
        place_righthalf_diamond();
    }
    if (!((pm_shown_ptr) >= 0x0FFF0000))
        (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits |= 2;
    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x372A9
// WIN: 0x0045c430
// Lines 413–430
//
// City-map top-layer scanline (no edge clipping).  For
// each cell: are_overlays_on bails (just advance sprite_x);
// else for tile >= 0x78 call place_a_building_top(0); if
// (*(struct city_cell *)((unsigned char *)city_map + (ptr))).edge_bits & 0x80 set, call top_it(0).
void mid_line_no_sides_top(void)
{
    int i;
    int next_x;
    int overlays;

    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        overlays = are_overlays_on();
        next_x   = sprite_x + pm_diamond_width;
        if (overlays != 0) {
            sprite_x = next_x;
        } else if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x = next_x;
        } else {
            if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) place_a_building_top(0);
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x80) != 0) top_it(0);
            sprite_x += pm_diamond_width;
            print_test_info();
        }
    }
    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x3738B
// WIN: 0x0045c558
// Lines 433–465
//
// City-map top-layer scanline with edge clipping.  Left
// edge uses style 3 (building) / 1 (top_it); right edge
// uses style 4 / 2.  Middle cells use 0.
void mid_line_with_sides_top(void)
{
    int i;
    int next_x;
    int overlays;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    /* left edge */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (are_overlays_on() == 0) {
        if (!((pm_shown_ptr) >= 0x0FFF0000)) {
            if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) place_a_building_top(3);
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x80) != 0) top_it(1);
        }
    }
    sprite_x += pm_diamond_half_width;

    /* middle */
    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        overlays = are_overlays_on();
        next_x   = sprite_x + pm_diamond_width;
        if (overlays != 0) {
            sprite_x = next_x;
        } else if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x = next_x;
        } else {
            if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) place_a_building_top(0);
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x80) != 0) top_it(0);
            sprite_x += pm_diamond_width;
            print_test_info();
        }
    }

    /* right edge */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (are_overlays_on() == 0) {
        if (!((pm_shown_ptr) >= 0x0FFF0000)) {
            if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) place_a_building_top(4);
            if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x80) != 0) top_it(2);
        }
    }

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x37556
// WIN: 0x0045c7bc
// Lines 473–505
//
// Twin of mid_line_with_sides_top for the bottom edge of the
// displayed slice.  Wrapped in `if (pm_shown_y < 0xA1)` so it
// no-ops past the map bottom and uses place_a_building_roof
// instead of place_a_building_top.  Tail updates only pm_shown_y
// and pm_y_clip (sprite_y advance happens in the caller).
void bottom_line_with_sides(void)
{
    int i;

    if (pm_shown_y >= PM_H) return;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    /* left edge */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) {
        if (are_overlays_on() == 0) {
            if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
                place_a_building_roof(3);
            }
        }
    }
    sprite_x += pm_diamond_half_width;

    /* middle */
    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        }
        else if (are_overlays_on() != 0) sprite_x += pm_diamond_width;
        else if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) place_a_building_roof(0);
        else sprite_x += pm_diamond_width;
    }

    /* right edge */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) {
        if (are_overlays_on() == 0) {
            if ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
                place_a_building_roof(4);
            }
        }
    }

    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x376CF
// WIN: 0x0045c9c9
// Lines 507–524
//
// Draw one bottom clipped pseudo-map line when there are no side tiles.
// For each screen column, fetch the pseudo_map city pointer; sentinel
// entries only advance sprite_x, while normal city tiles draw a roof for
// building kinds >= 0x78 when overlays are not active.  Advances the
// shown Y row and bottom clip by one diamond half-height.
void bottom_line_no_sides(void)
{
    int i;
    int next_x;
    int overlays;

    if (pm_shown_y >= PM_H) return;
    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
            continue;
        }
        overlays = are_overlays_on();
        next_x   = sprite_x + pm_diamond_width;
        if (overlays == 0 && (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind >= 0x78) {
            place_a_building_roof(0);
        } else {
            sprite_x = next_x;
        }
    }
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x3779D
// WIN: 0x0045cac7
// Lines 528–580
//
// City-map building-base diamond.  Reads the cell's bank_kind
// (edge_bits & 0x1c) and routes into one of six sprite banks
// (house_data / building_data1..4 / fixt_data) via the rotated_bank*
// lookup tables, then dispatches to place_i_{large,medium,small}_
// diamond[_lefthalf|_righthalf] per zoom_level and the requested
// half-edge style.
void place_a_building_base(int style)
{
    char bank_kind;
    int rot;
    unsigned char *data_base;

    sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).extra_edge;
    bank_kind = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x1c;
    rot = (map_direction >> 1) + sprite_image_no * 4;

    if (bank_kind == 0) {
        data_base = house_data;
        sprite_image_no = rotated_bank0[rot];
    } else if (bank_kind == 4) {
        data_base = building_data1;
        sprite_image_no = rotated_bank1[rot];
    } else if (bank_kind == 8) {
        data_base = building_data2;
        sprite_image_no = rotated_bank2[rot];
    } else if (bank_kind == 0xc) {
        data_base = building_data3;
        sprite_image_no = rotated_bank3[rot];
    } else if (bank_kind == 0x10) {
        data_base = fixt_data;
        sprite_image_no = rotated_map[sprite_image_no - 0x10].dir[map_direction >> 1] + 0x10;
    } else if (bank_kind == 0x14) {
        data_base = building_data4;
        sprite_image_no = rotated_bank4[rot];
    } else {
        return;
    }

    set_city_ambient((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind);
    data_ptr     = sprite_image_no * 16 + 8;
    y_length     = data_base[data_ptr + 0xd];
    sprite_start = data_base[data_ptr + 4]
                 + (data_base[data_ptr + 5] << 8)
                 + (data_base[data_ptr + 6] << 16);
    if (sprite_start > 0x4baf0) {
        sprite_error++;
        return;
    }
    if (sprite_start < 0) {
        sprite_error++;
        return;
    }
    if (y_length > 0xc8) {
        sprite_error++;
        return;
    }
    if (y_length < 0) {
        sprite_error++;
        return;
    }

    if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
        (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits &= 0xfe;
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

// FUNCTION: C2 0x379EB
// WIN: 0x0045cec9
// Lines 585–677
//
// City-map building-top ("hat") diamond.  Same six-bank lookup as
// place_a_building_base (incl. the 0x10 fixt arm reading
// rotated_map[img-0x10] and the 0x14 building_data4 arm); then
// the reused bank_kind char (bank kind, then height class -- one
// local, WIN /Od witness bVar2) gates the write_*_diamond_*hat
// fan-out per style / zoom.  The y_length==0 early-out repeats
// inside each style arm.  Style 4's hc==2 and hc==3 are two separate
// ifs (the righthat call falls through to the hc==3 test); styles 3
// and 0/1 use else-if chains.  The four bounds tests are separate
// ifs whose error bodies share a tail.
//
// LOAD-BEARING: `int dir` must be declared LAST (after data_base).
// The decl order perturbs the regalloc queue enough to flip the
// CountRegMoves coalesce in the 0x10 arm: with dir last, the byte
// load keeps PS's two-IL-value form (shl eax,2; add esi,eax;
// xor eax,eax; mov al,[esi+K]); with dir earlier the index and load
// destination coalesce into eax and Watcom emits the fused
// mov al,[esi+eax*4+K]; and eax,0xff instead (probe-verified: the
// arm spelling itself is NOT the lever -- 10 spellings all fuse).
void place_a_building_top(int style)
{
    char bank_kind;
    unsigned char *data_base;
    int dir;

    sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).extra_edge;
    bank_kind = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x1c; dir = map_direction >> 1;

    if (bank_kind == 0) { data_base = house_data; sprite_image_no = rotated_bank0[sprite_image_no * 4 + dir]; }
    else if (bank_kind == 4) { data_base = building_data1; sprite_image_no = rotated_bank1[sprite_image_no * 4 + dir]; }
    else if (bank_kind == 8) { data_base = building_data2; sprite_image_no = rotated_bank2[sprite_image_no * 4 + dir]; }
    else if (bank_kind == 0xc) { data_base = building_data3; sprite_image_no = rotated_bank3[sprite_image_no * 4 + dir]; }
    else if (bank_kind == 0x10) { data_base = fixt_data; sprite_image_no = rotated_map[sprite_image_no - 0x10].dir[dir] + 0x10; }
    else if (bank_kind == 0x14) {
        data_base = building_data4; sprite_image_no = rotated_bank4[sprite_image_no * 4 + dir]; } else return;

    data_ptr     = sprite_image_no * 16 + 8;
    y_length     = data_base[data_ptr + 0xd];
    bank_kind = data_base[data_ptr + 0xc];
    sprite_start = data_base[data_ptr + 4]
                 + (data_base[data_ptr + 5] << 8)
                 + (data_base[data_ptr + 6] << 16);
    if      (zoom_level == 0) sprite_hat_start = sprite_start + 0x384;
    else if (zoom_level == 1) sprite_hat_start = sprite_start + 0xc4;
    else                       sprite_hat_start = sprite_start + 0x24;

    if (sprite_start > 0x4baf0) { sprite_error++; return; }
    if (sprite_start < 0) { sprite_error++; return; }
    if (y_length > 0xc8) { sprite_error++; return; }
    if (y_length < 0) { sprite_error++; return; }

    if (style == 3) {
        if (y_length == 0) return;
        if (bank_kind == 2) {
            if      (zoom_level == 0) write_large_diamond_lefthat(data_base, pm_y_clip);
            else if (zoom_level == 1) write_medium_diamond_lefthat(data_base, pm_y_clip);
            else                       write_small_diamond_lefthat(data_base, pm_y_clip);
        } else if (bank_kind == 4) {
            if      (zoom_level == 0) write_large_diamond_righthalfhat(data_base, pm_y_clip, 2);
            else if (zoom_level == 1) write_medium_diamond_righthalfhat(data_base, pm_y_clip, 2);
            else                       write_small_diamond_righthalfhat(data_base, pm_y_clip, 2);
        }
    } else if (style == 4) {
        if (y_length == 0) return;
        if (bank_kind == 2) {
            if      (zoom_level == 0) write_large_diamond_righthat(data_base, pm_y_clip);
            else if (zoom_level == 1) write_medium_diamond_righthat(data_base, pm_y_clip);
            else                       write_small_diamond_righthat(data_base, pm_y_clip);
        }
        if (bank_kind == 3) {
            if      (zoom_level == 0) write_large_diamond_lefthalfhat(data_base, pm_y_clip, 2);
            else if (zoom_level == 1) write_medium_diamond_lefthalfhat(data_base, pm_y_clip, 2);
            else                       write_small_diamond_lefthalfhat(data_base, pm_y_clip, 2);
        }
    } else if (style != 2) { if (y_length == 0) return;
        if (bank_kind == 2) {
            if      (zoom_level == 0) write_large_diamond_hat(data_base, pm_y_clip);
            else if (zoom_level == 1) write_medium_diamond_hat(data_base, pm_y_clip);
            else                       write_small_diamond_hat(data_base, pm_y_clip);
        } else if (bank_kind == 3) {
            if      (zoom_level == 0) write_large_diamond_lefthalfhat(data_base, pm_y_clip, 0);
            else if (zoom_level == 1) write_medium_diamond_lefthalfhat(data_base, pm_y_clip, 0);
            else                       write_small_diamond_lefthalfhat(data_base, pm_y_clip, 0);
        } else if (bank_kind == 4) {
            if      (zoom_level == 0) write_large_diamond_righthalfhat(data_base, pm_y_clip, 0);
            else if (zoom_level == 1) write_medium_diamond_righthalfhat(data_base, pm_y_clip, 0);
            else                       write_small_diamond_righthalfhat(data_base, pm_y_clip, 0);
        }
    }
}

// FUNCTION: C2 0x37DC4
// WIN: 0x0045d530
// Lines 680–786
//
// City-map roof slice of a building.  Snapshot sprite_y, do the
// same bank / image / rotation lookup as place_a_building_top, then:
//
//   * Re-stamp sprite_y = pm_screen_y_end - 1 so the roof renders at
//     the bottom of the visible slice.
//   * If edge_bits bit 0 is set: clear it and refresh the bigger
//     square around the building.
//   * Subtract pm_y_clip from y_length and advance sprite_hat_start
//     by pm_y_clip * K(zoom_level, bank_kind), where K tracks the
//     stride of each per-zoom diamond row.
//   * Style fan-out to nine write_*_diamond_*roof blitters keyed on
//     (zoom_level, style, bank_kind).
//
// The bank_kind==0x10 arm assigns `data_base = fixt_data` BEFORE the
// rotated_map lookup (the order is mirrored opposite
// place_a_building_top -- live-set driven).
void place_a_building_roof(int mode)
{
    int rot;
    char bank_kind;
    unsigned char *data_base;
    unsigned char height_class;

    sprite_image_no = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).extra_edge;
    bank_kind = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 0x1c;
    rot       = (map_direction >> 1) + sprite_image_no * 4;

    if (bank_kind == 0) {
        data_base = house_data;
        sprite_image_no = rotated_bank0[rot];
    } else if (bank_kind == 4) {
        data_base = building_data1;
        sprite_image_no = rotated_bank1[rot];
    } else if (bank_kind == 8) {
        data_base = building_data2;
        sprite_image_no = rotated_bank2[rot];
    } else if (bank_kind == 0xc) {
        data_base = building_data3;
        sprite_image_no = rotated_bank3[rot];
    } else if (bank_kind == 0x10) {
        data_base = fixt_data;
        sprite_image_no = (rotated_map[sprite_image_no - 0x10].dir[map_direction >> 1] & 0xff) + 0x10;
    } else if (bank_kind == 0x14) {
        data_base = building_data4;
        sprite_image_no = rotated_bank4[rot];
    } else {
        return;
    }

    data_ptr     = sprite_image_no * 16 + 8;
    y_length     = data_base[data_ptr + 0xd];
    if (y_length <= pm_y_clip) {
        if (mode < 3)
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
        if (((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits & 1) != 0) {
            (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).edge_bits &= 0xfe;
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

        if (mode == 3) {
            if (height_class == 2) {
                if      (zoom_level == 0) write_large_diamond_leftroof(data_base);
                else if (zoom_level == 1) write_medium_diamond_leftroof(data_base);
                else                       write_small_diamond_leftroof(data_base);
            } else if (height_class == 4) {
                if      (zoom_level == 0) write_large_diamond_righthalfroof(data_base, 2);
                else if (zoom_level == 1) write_medium_diamond_righthalfroof(data_base, 2);
                else                       write_small_diamond_righthalfroof(data_base, 2);
            }
        } else if (mode == 4) {
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
    }
}

// FUNCTION: C2 0x3820D
// WIN: 0x0045dc3f
// Lines 809–927
//
// Per-cell overhead sprite renderer.  Triggered when edge_bits bit
// 0x80 is set.  Reads base_kind (tile) and building (anim_arg) from
// the cell and dispatches one of nine cases:
//
//   * tile < 8           - fire flames (animates via city_anim64 /
//                          city_anim16, fire_offs offset table,
//                          set_this_ambient(6), emergency_mood = 10).
//   * tile in 0x82..0xa1 - riot, sprite_image_no = 8 at fixed
//                          per-zoom offsets, emergency_mood = 10.
//   * tile == 0xfa       - jars on building exterior; activity_a & 0xf
//                          picks city_jars_x/y_off, else falls back
//                          to city_type_x/y_off (business & 0xf).
//   * tile == 0xe3       - smoke / steam, image 0x21..0x28.
//   * tile == 0xe7       - arena overhead (arena_top_count >= 6).
//   * tile == 0xe8       - colosseum overhead (colosseum_top_count >= 9).
//   * tile == 0xc0       - aqueduct top via rotated_bank2 + 0x1d.
//   * tile in 0xd5..0xd6 - skill-to-attack lookup, zoom <= 1.
//
// Common epilogue: read sprite_start / width / height from
// tops_data[img*16 + 8] with bounds checks, snapshot sprite_x/y,
// apply img_off_x/y, refresh_sprite[_2w]_square per ambient_mode,
// xclip + yclip, then dispatch to write_i_sprite / write_i_left_sprite
// / write_i_right_sprite (skip entirely when yclipped == 5).
//
// REGALLOC RESIDUE (seat 1/8, ir 0/90 clean): the 0xd5..0xd6 arm's
// zoom_level guard-read (EAX in PS) ties against a compiler-generated
// reload of the just-stored `sprite_image_no - 0x60` result for the
// `> 2` comparison (savings ~5 vs zoom's ~3) -- PS seats zoom=EAX /
// reload=EDX, we seat the opposite.  Exhausted: all 120 decl-order
// permutations of (b,img,zoom,dir,t), zoom named/unnamed/uchar,
// compound `-=`, operand commutes in both rotated_bank2/rotated_map
// lookups, Rule 121 tail-duplication (no size/seat change -- grew
// bytes, ComTail did not re-absorb it, so this isn't the mechanism).
// win-verify is not clean here (145/454 struct) but the divergence is
// concentrated in unrelated CAESAR2.EXE port-drift regions, not this
// arm.  Not source-lever-reachable with current tooling; seat tie only.
//
// RE-AUDIT 2026-07-09 (the certificate above was written while the
// Rover-closeable machinery was TRACE-STARVED by the decomp_verify _rh
// shadowing bug, fixed 1db35afd): closeability now fires and names the
// exact requirement -- a +1 dword rover advance injected after L1031
// `fire_idx = ...`, L1044 `emergency_mood = 0xa;`, or L1139
// `img_off_x -= ...` SELF-HEALS offline.  So the residue IS a rover
// cursor off-by-one, not a pure allocator tie.  Probed 2026-07-09:
// data_ptr/t merge + both split forms (357->498 regress, arena
// reshuffle), fire_idx inline / partial inline (IL-inert, CSE).  The
// four proven +1 idioms don't apply in the window (no loop, no
// checked-global call arg, no dead branch, no shared textual tail).
// Open: a byte-neutral +1 dword op spelling for this window.
// lw-MAP EVIDENCE (2026-07-09, the new ~WV1 lw complete-walk probe):
// both closeability windows contain ZERO kind-flippable dword ops --
// every skipped op is convert/bound/const->REG/all-REG in our compile
// AND PS's asm shows the same reg-only forms (side-compare-from-slot
// falsified: PS cmp edi,1).  So the +1 is an IL-op-BIRTH or block
// WALK-ORDER difference, not an operand-kind flip; next probes: ni
// pairing / bk order diff (watcom10.0a tools/lw_map.py).
// SWEEP DATUM 2026-07-09b (503-variant byte-oracle sweep, 2 passes):
// `(unsigned char)` cast at the d5 rotated_map read scores (shape 1,
// 10bd) vs the mask form's (2, 116bd) -- but the cast form is a FALSE
// improvement: Rule 49b fires (xor-before vs PS's and-after) and the
// d5 fold [ecx+edx*4+K] unfolds to shl/add.  The mask form is
// IR-right; its whole 116bd is ONE dir-seat flip (ECX->EAX, +0x277)
// cascading.  Composed probes (cast x mask per arm, dir-first
// subscript commutes, flat-array spellings, de-invent img) all inert
// or regress -- consistent with the lw-map verdict above (sub-source
// birth/walk-order).  Keep the mask form.
// (c)-LEG CLOSURE 2026-07-09b: spell --walk-order confirms the
// reverse-arm class (else-if arms walk in reverse source order,
// birth ordinals out of walk order, 22 optimizer-born blocks).
// Mechanism argument closes the +1 hunt: a byte-neutral +1 dword
// advance can ONLY come from re-classifying an existing mov+op pair
// via load-folding; the lw census proves zero such candidates in the
// windows, and any manufactured op changes bytes by construction.
// The two remaining data_ptr/t spellings screen LIVE (dword -1, wrong
// sign) and regress at the byte oracle (116->362/367).  Residue is
// sub-source unless a restructure MOVES the advance windows -- the
// open research direction, not a per-function lever.
// 2026-07-10: `kind` hoisted from the tile==0xfa arm to C89
// top-of-function (corpus norm; win-census slot count 11=11 agrees
// kind is a real local).  Layered shape is IDENTICAL to the old
// block form (ir 1/90 isl 1 [sub-vs-lea @ sprite_image_no -= 0x60],
// seat 1/8); the byte count moved 116->357 = the same single-seat
// cascade re-rippling, not a shape change.  Sweep over the flat decl
// space: tile-first ordering is best; the only shape-2 variant was
// commuting sprite_height to `(t[3]<<8) + t[2]`, REJECTED as a false
// improvement (corpus spells X[2] + (X[3]<<8) at 10/10 sites).
// CLOSURE 2026-07-10 (Rule 49b + Rule 115): shape ir1/90, seat1/8 -> all
// zero and BYTE-EXACT.  `c2 forge solve top_it` found the load-bearing
// three-edit composition after 2,057 variants: use the explicit
// `(unsigned char)` conversion at the rotated_map read, swap `tile` with
// `ambient_mode`, and swap `img_off_y` with `dir`.  The cast alone was the
// previously documented 10bd false minimum, while the declaration swaps
// alone did not close the function; together they create the conflicts in
// the order that seats the lookup in EDX, so Watcom emits PS's scaled byte
// load followed by the in-place `and edx,0xff`.  This exact composition
// supersedes the earlier "keep the mask form" conclusion above.
void top_it(int side)
{
    int ambient_mode;
    int dir;
    unsigned char tile;
    int img_off_x;
    unsigned char anim_arg;
    unsigned char b;
    unsigned char kind;
    unsigned char img;
    unsigned char *t;
    int img_off_y;
    int zoom;

    ambient_mode = 0;
    tile        = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
    anim_arg    = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).building;
    img_off_x   = 0;

    if (tile < 8) {
        /* Fire flames */
        sprite_image_no = (anim_arg + city_anim64) & 7;
        img_off_x       = fire_offs[((anim_arg + city_anim16) & 0xf)].dx;
        img_off_y       = fire_offs[((anim_arg + city_anim16) & 0xf)].dy;
        if (zoom_level == 1) {
            img_off_x >>= 1;
            img_off_y >>= 1;
        } else if (zoom_level == 2) {
            img_off_x >>= 2;
            img_off_y >>= 2;
        }
        ambient_mode = 1;
        set_this_ambient(6);
        set_ambient_minimum(6, 0xbe);
        emergency_mood = 0xa;
    } else if (tile >= 0x82 && tile <= 0xa1) {
        /* Riot */
        sprite_image_no = 8;
        img_off_x       = 0x14;
        img_off_y       = -2;
        emergency_mood  = 0xa;
        if (zoom_level == 1) {
            img_off_x = 0xa;
            img_off_y = -1;
        } else if (zoom_level == 2) {
            img_off_x = 5;
            img_off_y = -1;
        }
    } else {
        if (tile == 0xfa) {
            b = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).activity_a & 0xf;
            if (b != 0) {
                /* Jars-with-flowers (b non-zero): look up
                   sub-kind at the parallel byte 0xB cells
                   back in the same row; abort when zero. */
                kind = (*(struct city_cell *)((unsigned char *)city_map + ((pm_shown_ptr) - 0x14))).building & 0xf0;
                kind >>= 4;
                if (kind == 0)
                    return;
                sprite_image_no = kind + 0x18;
                img_off_x       = city_jars_x_off[zoom_level][(map_direction / 2)];
                img_off_y       = city_jars_y_off[zoom_level][(map_direction / 2)];
            } else {
                /* Jars-without-flowers */
                sprite_image_no = ((*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).business & 0xf) + 9;
                img_off_x       = city_type_x_off[zoom_level][(map_direction / 2)];
                img_off_y       = city_type_y_off[zoom_level][(map_direction / 2)];
            }
        } else if (tile == 0xe3) {
            /* Smoke / steam */
            sprite_image_no = ((anim_arg + city_anim64) & 7) + 0x21;
            img_off_x       = 0x1c;
            img_off_y       = -0x1e;
            if (zoom_level == 1) {
                img_off_x = 0xe;
                img_off_y = -0xf;
            } else if (zoom_level == 2) {
                img_off_x = 3;
                img_off_y = -6;
            }
            ambient_mode = 1;
        } else if (tile == 0xe7) {
            if (arena_top_count < 6)
                return;
            sprite_image_no = 0x3b;
            img_off_x       = arena_top_data[zoom_level][(map_direction / 2)].dx;
            img_off_y       = arena_top_data[zoom_level][(map_direction / 2)].dy;
        } else if (tile == 0xe8) {
            if (colosseum_top_count < 9)
                return;
            sprite_image_no = 0x3c;
            img_off_x       = colos_top_data[zoom_level][(map_direction / 2)].dx;
            img_off_y       = colos_top_data[zoom_level][(map_direction / 2)].dy;
        } else { dir = map_direction >> 1; if (tile == 0xc0) {
            /* Aqueduct top */
            img = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).extra_edge;
            sprite_image_no = rotated_bank2[img * 4 + dir] & 0xff;
            sprite_image_no = sprite_image_no + 0x1d;
            img_off_x       = 0;
            img_off_y       = -0x17;
            if (zoom_level == 1)      img_off_y = -0xb;
            else if (zoom_level == 2) img_off_y = -5;
        } else if (tile >= 0xd5 && tile <= 0xd6) {
            zoom = zoom_level;
            if (zoom > 1)
                return;
            img = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).extra_edge;
            sprite_image_no = (unsigned char)rotated_map[img - 0x10].dir[dir];
            sprite_image_no -= 0x60;
            if (sprite_image_no > 2) {
                img_off_x = 0;
            } else if (zoom == 1) {
                img_off_x = 8;
            } else {
                img_off_x = 0x10;
            }
            if (zoom_level == 0) {
                sprite_image_no = aquaduct_tops2[sprite_image_no];
            } else {
                sprite_image_no = aquaduct_tops2[sprite_image_no];
            }
            img_off_y       = 0;
        } else {
            return;
        } }
    }

    if (side == 1)
        img_off_x -= pm_diamond_half_width;

    data_ptr     = sprite_image_no * 16 + 8;
    t = tops_data + data_ptr;
    sprite_start  = (t[5] << 8) + t[4] + (t[6] << 16);
    sprite_width  = t[0] + (t[1] << 8);
    sprite_height = (t[2]) + (t[3] << 8);
    if (sprite_start > 0x4baf0) {
        sprite_error++;
        return;
    }
    if (sprite_start < 0) {
        sprite_error++;
        return;
    }
    if (sprite_width > 0x280) {
        sprite_error++;
        return;
    }
    if (sprite_height > 0x1e0) {
        sprite_error++;
        return;
    }

    old_sprite_x = sprite_x;
    old_sprite_y = sprite_y;
    sprite_x    += img_off_x;
    sprite_y    += img_off_y;

    if (ambient_mode == 1)
        refresh_sprite_square(sprite_x >> 4, sprite_y >> 4);
    else if (ambient_mode == 2)
        refresh_sprite2w_square(sprite_x >> 4, sprite_y >> 4);

    xclip(pm_screen_x_start, 0x1de);
    if (zoom_level == 1)
        yclip(0x18, 0x1d8);
    else
        yclip(0x18, 0x1da);

    if (yclipped != 5) {
        if      (xclipped == 1) write_i_left_sprite(tops_data);
        else if (xclipped == 2) write_i_right_sprite(tops_data);
        else                    write_i_sprite(tops_data);
    }

    sprite_x = old_sprite_x;
    sprite_y = old_sprite_y;
}

// FUNCTION: C2 0x386F9
// WIN: 0x0045e38c
// Lines 931–1106
//
// City-map sprite layer.  Renders the citizen sprite passes (one per
// occupant in city_map+7 / +8, the draw_citizen_pass body inlined twice
// exactly as PS.EXE does) followed by the optional "mice" overlay sprite
// (flag_mode, city_map+2).  Each pass computes a walking x/y offset from
// the citizen's facing direction and speed_count, applies the diamond
// half-extent + wobble, then clips and blits via write_i_sprite.
//
// 2026-07-11: 5bd -> 2bd (place2_a_building_top's rot-lesson applied:
// composed spelling fixes the earlier sessions had only probed
// separately).  Three witnessed shape recoveries:
//   * mice sprite_width = `(word = mice[dp+0]) + ((word = mice[dp+1])
//     << 8);` with a new `int word;` local -- reproduces PS's L1086
//     byte-for-byte: BOTH loads xor-idiom (Rule 49 named-int-from-
//     uchar defs, NOT anon movzx) + the `mov esi,ecx` copy before the
//     shl (shift of a named value) + `add ecx,esi` accumulator.  The
//     sibling place2_sprite's maskless anon form was the wrong
//     template for THIS statement; _top's 0xd4 word/dummy embedded-
//     assign template was the right one.
//   * citizen_a sprite_start = `(people[5] << 8) + people[4] + ...`
//     (shifted-first, per the +01bd spill-reload accumulator witness);
//     citizen_b = `(people[6] << 16) + (people[4] + (people[5] << 8))`
//     (both adds' accumulators witnessed: inner acc = p5<<8's reg,
//     final acc = p6<<16's reg, NO spill -- the two inlined
//     draw_citizen_pass bodies are spelled DIFFERENTLY in PS; the
//     spill lives in citizen_a only, sub esp,8 = flag_byte + spill).
//   * mice sprite_start kept in the binir-identical grouped form
//     `(m6<<16) + (m4 + (m5<<8))` -- the plain left-assoc spelling is
//     174bd (the sum temp's ECX seat cascades m6 into movzx/ESI);
//     grouped, everything collapses to the ONE remaining tie.
// BYTE-EXACT 2026-07-13 (2bd -> 0; all 130 PS -d1 marks paired).
// POSTMORTEM of the final 2bd: the diff (`add ecx,esi` vs PS
// `add esi,ecx` + the store reg) was NOT a GiveBestReg seat at all --
// every round-0 seat in the statement matches PS (m5s/m6s = ECX,
// m4/inner sum = ESI).  Reading the round-0 IL walk showed the
// sprite_start final ADD has an N_MEMORY result and realizes directly
// as `add op0reg, op1reg; mov mem, op0reg` -- the 2bd was the ADD's
// OPERAND ORDER: RC op0 = m6<<16 (from the grouped source), PS op0 =
// the inner sum (left-assoc source).  Plain left-assoc alone breaks
// the m6 load idiom (movzx anon instead of the xor-idiom named-int
// pair, 174bd cascade); the closer is the COMPOSED form
//   (mice[dp+4] + (mice[dp+5] << 8)) + ((word = mice[dp+6]) << 16);
// left-assoc for op0=inner PLUS the word-embedded def on m6 (same
// device as the sprite_width line) to pin the named-int xor-idiom
// load.  Two prior sessions had probed both halves separately (the
// place2_a_building_top lesson, again).  The earlier 'given-subset
// tie on 6c201d94' attribution was a red herring: that round-1 temp
// is sprite_width's word->shift carrier (seat byte-invisible); the
// seat_recon LOCALIZED caveat was right to warn.
// Fan-out packing: the three write_i_* if/else-if chains carry PS
// -d1 marks on the CALL lines (L1003/L1004 pattern) -> guard and
// call on separate lines.
// Historical (pre-2026-07-11) probe notes: switch(side) impossible
// (PS = jne chain); de-inventing `people` 584bd; decl perms inert;
// win-verify cannot certify (WIN is a later source revision).
//
void place_sprite(int side)
{
    unsigned char flag_byte;
    int mice_kind;
    int dx;
    int dy;
    int dir;
    unsigned char *people;
    int word;

    mice_kind = 0;
    citizen_b = 0;
    citizen_a = 0;
    citizen_a = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).citizen_a;
    citizen_b = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).citizen_b;
    flag_byte = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain;
    if (flag_mode != 0)
        mice_kind = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).road_aqueduct;

    if (citizen_a != 0) {
        dir = citizen_list[citizen_a].world_dir - map_direction;
        if (dir < 0) dir += 8;
        if (zoom_level == 0) {
            dx = walking_x_ofsets_zoom0[dir * 16 + citizen_list[citizen_a].speed_count];
            dy = walking_y_ofsets_zoom0[dir * 16 + citizen_list[citizen_a].speed_count];
        } else if (zoom_level == 1) {
            dx = walking_x_ofsets_zoom1[dir * 16 + citizen_list[citizen_a].speed_count];
            dy = walking_y_ofsets_zoom1[dir * 16 + citizen_list[citizen_a].speed_count];
        } else {
            dx = walking_x_ofsets_zoom2[dir * 16 + citizen_list[citizen_a].speed_count];
            dy = walking_y_ofsets_zoom2[dir * 16 + citizen_list[citizen_a].speed_count];
        }
        if (side == 1) {
            dx -= 2;
        } else if (side == 2) {
            dx += pm_diamond_half_width - 2;
        } else {
            dx += pm_diamond_half_width;
        }
        dy += pm_diamond_half_height;
        if (zoom_level == 0) {
            if (dir <= 3) {
                if ((flag_byte & 0x40) != 0) {
                    citizen_list[citizen_a].wobble_counter = 0x10;
                    dy += 2;
                } else if (citizen_list[citizen_a].wobble_counter != 0) {
                    dy += 2;
                    citizen_list[citizen_a].wobble_counter--;
                } else {
                    dy -= 2;
                }
            } else {
                dy += 6;
            }
        }
        sprite_image_no = citizen_list[citizen_a].image_id;
        data_ptr        = sprite_image_no * 16 + 8;
        people = people_data + data_ptr; sprite_start = (people[5] << 8) + people[4] + (people[6] << 16);
        sprite_width    = people[0] + (people[1] << 8);
        sprite_height   = people[2] + (people[3] << 8);
        if (sprite_start > 0x4baf0) {
            sprite_error++;
            return;
        }
        if (sprite_width <= 0) {
            sprite_error++;
            return;
        }
        if (sprite_width > 0x12c) {
            sprite_error++;
            return;
        }
        if (sprite_height <= 0) {
            sprite_error++;
            return;
        }
        if (sprite_height > 0x12c) {
            sprite_error++;
            return;
        }
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        sprite_x    += dx;
        sprite_y    += dy;
        sprite_x    -= sprite_width >> 1;
        sprite_y    -= sprite_height;
        refresh_sprite_square(sprite_x >> 4, sprite_y >> 4);
        xclip(pm_screen_x_start, 0x1de);
        if (zoom_level == 1) yclip(0x18, 0x1d8);
        else                  yclip(0x18, 0x1da);
        if (yclipped != 5) {
            if (xclipped == 1)
                write_i_left_sprite(people_data);
            else if (xclipped == 2)
                write_i_right_sprite(people_data);
            else
                write_i_sprite(people_data);
        }
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }

    if (citizen_b != 0) {
        dir = citizen_list[citizen_b].world_dir - map_direction;
        if (dir < 0) dir += 8;
        if (zoom_level == 0) {
            dx = walking_x_ofsets_zoom0[dir * 16 + citizen_list[citizen_b].speed_count];
            dy = walking_y_ofsets_zoom0[dir * 16 + citizen_list[citizen_b].speed_count];
        } else if (zoom_level == 1) {
            dx = walking_x_ofsets_zoom1[dir * 16 + citizen_list[citizen_b].speed_count];
            dy = walking_y_ofsets_zoom1[dir * 16 + citizen_list[citizen_b].speed_count];
        } else {
            dx = walking_x_ofsets_zoom2[dir * 16 + citizen_list[citizen_b].speed_count];
            dy = walking_y_ofsets_zoom2[dir * 16 + citizen_list[citizen_b].speed_count];
        }
        if (side == 1) {
            dx -= 2;
        } else if (side == 2) {
            dx += pm_diamond_half_width - 2;
        } else {
            dx += pm_diamond_half_width;
        }
        dy += pm_diamond_half_height;
        if (zoom_level == 0) {
            if (dir <= 3) {
                if ((flag_byte & 0x40) != 0) {
                    citizen_list[citizen_b].wobble_counter = 0x10;
                    dy += 2;
                } else if (citizen_list[citizen_b].wobble_counter != 0) {
                    dy += 2;
                    citizen_list[citizen_b].wobble_counter--;
                } else {
                    dy -= 2;
                }
            } else {
                dy += 6;
            }
        }
        sprite_image_no = citizen_list[citizen_b].image_id;
        data_ptr        = sprite_image_no * 16 + 8;
        people = people_data + data_ptr; sprite_start = (people[6] << 16) + (people[4] + (people[5] << 8));
        sprite_width    = people[0] + (people[1] << 8);
        sprite_height   = people[2] + (people[3] << 8);
        if (sprite_start > 0x4baf0) {
            sprite_error++;
            return;
        }
        if (sprite_width <= 0) {
            sprite_error++;
            return;
        }
        if (sprite_width > 0x12c) {
            sprite_error++;
            return;
        }
        if (sprite_height <= 0) {
            sprite_error++;
            return;
        }
        if (sprite_height > 0x12c) {
            sprite_error++;
            return;
        }
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        sprite_x    += dx;
        sprite_y    += dy;
        sprite_x    -= sprite_width >> 1;
        sprite_y    -= sprite_height;
        refresh_sprite_square(sprite_x >> 4, sprite_y >> 4);
        xclip(pm_screen_x_start, 0x1de);
        if (zoom_level == 1) yclip(0x18, 0x1d8);
        else                  yclip(0x18, 0x1da);
        if (yclipped != 5) {
            if (xclipped == 1)
                write_i_left_sprite(people_data);
            else if (xclipped == 2)
                write_i_right_sprite(people_data);
            else
                write_i_sprite(people_data);
        }
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }

    if (mice_kind == 0)
        return;

    dy = 0;
    if (side == 1)      dx = -2;
    else if (side == 2) dx = pm_diamond_half_width - 2;
    else                dx = pm_diamond_half_width;
    dy += pm_diamond_half_height;

    if (mice_kind == 3) sprite_image_no = zoom_level + 0xe;
    else                 sprite_image_no = zoom_level + 0xb;
    data_ptr        = sprite_image_no * 16 + 8;
    sprite_start    = (mice[data_ptr + 4] + (mice[data_ptr + 5] << 8)) + ((word = mice[data_ptr + 6]) << 16);
    sprite_width    = (word = mice[data_ptr + 0]) + ((word = mice[data_ptr + 1]) << 8);
    sprite_height   = mice[data_ptr + 2] + (mice[data_ptr + 3] << 8);

    old_sprite_x = sprite_x;
    old_sprite_y = sprite_y;
    sprite_x    += dx;
    sprite_y    += dy;
    sprite_y    -= sprite_height;
    refresh_sprite_square(sprite_x >> 4, sprite_y >> 4);
    xclip(pm_screen_x_start, 0x1de);
    if (zoom_level == 1) yclip(0x18, 0x1d8);
    else                  yclip(0x18, 0x1da);
    if (yclipped != 5) {
        if (xclipped == 1)
            write_i_left_sprite(mice);
        else if (xclipped == 2)
            write_i_right_sprite(mice);
        else
            write_i_sprite(mice);
    }
    sprite_x = old_sprite_x;
    sprite_y = old_sprite_y;
}

// FUNCTION: C2 0x38E80
// WIN: 0x0045ef7d
// Lines 1110–1134
//
// Debug/test overlay for city-map cells.  test_mode1 prints city_map+1
// (negative values shown positive in colour 3, otherwise colour 0x3f),
// while test_mode2 prints city_map+2 with the same sign colouring.
// sprite_x/y are saved around the font_no call because font rendering
// mutates the global sprite cursor.
void print_test_info(void)
{
    int v;
    int colour;

    if (test_mode1 != 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) return;
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        v = (signed char)(*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain;
        if (v < 0) { v = -v; colour = 3; }
        else                colour = 0x3f;
        font_no(v, 0x20, " ",
                sprite_x + 0x14 - pm_diamond_width, sprite_y + 0xa,
                font1, colour);
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    } else if (test_mode2 != 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) return;
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        v = (signed char)(*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).road_aqueduct;
        if (v < 0) { v = -v; colour = 3; }
        else                colour = 0x3f;
        font_no(v, 0x20, " ",
                sprite_x + 0x14 - pm_diamond_width, sprite_y + 0xa,
                font1, colour);
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }
}

// FUNCTION: C2 0x38F5B
// WIN: 0x0045f0f8
// Lines 1138–1179
//
// Per-cell overlay dispatcher.  Returns 0 when no overlay drew the
// cell (caller falls back to the normal draw) and 1 when the overlay
// handled it.
//
// Image selection:
//   * landfill_pool[idx] == 0 (no landfill): only draw when the cell's
//     terrain flags (terrain & 0xe7) are set AND overlay0_empty_mode
//     == 0.  Image is 7 for population cells (base_kind in 0x82..0xa1)
//     and 0 otherwise.
//   * landfill == 0x96 ("flag"): use landfill - 0x76 in ov_map_mode 1;
//     in ov_map_mode 6 only when the tile is outside 0xe5..0xf0; bail
//     in other modes.
//   * other landfill values: image is landfill - 0x76.
//
// After resolution, population cells (0x82..0xa1) shift the image by
// +2 if it's >= 8, otherwise non-population cells advance by 1 when
// terrain & 1 is set ("under construction" marker).  Images < 0x23
// get stamped through place_overlay(style); sprite_x then advances
// by pm_diamond_width.
//
// In the landfill==0 branch base_kind is cached into `tile` so the
// later 0x82..0xa1 range check reuses the same load.  show_overlay,
// show_left_overlay and show_right_overlay share this body modulo
// the routed place_*_overlay call.
int show_overlay(int style)
{
    int idx;
    unsigned char tile;
    unsigned char flag_lsb;
    int tile_in_building_range;

    if (overlays_on != 1)
        return 0;
    idx = pm_shown_ptr / 20;

    if (landfill_pool[idx] == 0) {
        flag_lsb = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain & 0xe7;
        tile = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
        if (flag_lsb == 0)
            return 0;
        if (overlay0_empty_mode != 0)
            return 0;
        if (tile >= 0x82 && tile <= 0xa1)
            sprite_image_no = 7;
        else
            sprite_image_no = 0;
    } else if (landfill_pool[idx] == 0x96) {
        if (ov_map_mode == 1) {
            sprite_image_no = landfill_pool[idx] - 0x76;
        } else {
            if (ov_map_mode != 6) return 0;
            tile = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
            if (tile >= 0xe5 && tile <= 0xf0)
                return 0;
            sprite_image_no = landfill_pool[idx] - 0x76;
        }
    } else {
        sprite_image_no = landfill_pool[idx] - 0x76;
    }

    if (sprite_image_no >= 8) {
        tile                  = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
        flag_lsb              = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain & 1;
        tile_in_building_range = (tile >= 0x82 && tile <= 0xa1);
        if (tile_in_building_range && sprite_image_no >= 8) sprite_image_no += 2;
        else if (flag_lsb) sprite_image_no++;
    }
    if (sprite_image_no < 0x23)
        place_overlay(style);
    sprite_x += pm_diamond_width;
    return 1;
}

// FUNCTION: C2 0x390C3
// WIN: 0x0045f34e
// Lines 1181–1221
//
// Left-edge half-diamond overlay.  Same image-selection
// logic as show_overlay; routes through
// place_lefthalf_overlay and does NOT advance sprite_x
// (the caller bumps it by pm_diamond_half_width after
// returning).
//
// BYTE-EXACT (twin: show_right_overlay, same shape).  2026-07-14: the
// comma-dup allocator hack is GONE -- PS's true source shape was
// recovered from its own asm: the subtraction is computed ONCE into a
// named local BEFORE the 0x96 test (PS L1198: xor ecx,ecx; mov cl,dl;
// lea edx,[ecx-0x76]; cmp ecx,0x96 -- widen + sub + compare in one
// line's run), and the b!=0x96 / mode==1 paths both store that local
// (two source stores, ComTail-merged into the single L1209
// `mov [sprite_image_no],edx`; the jne/je branch straight to it).
// That gives the sub temp its sav=3 (def + 2 uses) honestly -- the
// exact +1 use-unit the `c2 savings --flip` cascade demanded (the old
// comma dup simulated it).  The mode-6 arm recomputes fresh from the
// array (PS L1205 reload witnessed).  Decl order (tile, b, idx, ...)
// is the Rule 115 lever; the original (idx, b, tile) order = 191bd.
// ONE RC-only -d1 mark remains at +0xD1 (the merged store's second
// source line; placement-invariant, same class as mid3's +0x240).
//
int show_left_overlay(int style)
{
    unsigned char tile;
    unsigned char b;
    int idx;
    unsigned char flag_lsb;
    int tile_in_building_range = 0;
    int ov_image;

    if (overlays_on != 1) return 0;
    idx = pm_shown_ptr / 20;
    if ((b = landfill_pool[idx]) == 0) {
        flag_lsb = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain & 0xe7;
        tile = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
        if (flag_lsb == 0)
            return 0;
        if (overlay0_empty_mode != 0)
            return 0;
        if (tile >= 0x82 && tile <= 0xa1) sprite_image_no = 7;
        else sprite_image_no = 0;
    } else {
        ov_image = b - 0x76; if (b == 0x96) {
            if (ov_map_mode == 1) sprite_image_no = ov_image;
            else if (ov_map_mode == 6) {
                tile = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
                if (tile >= 0xe5 && tile <= 0xf0)
                    return 0;
                sprite_image_no = landfill_pool[idx] - 0x76;
            } else {
                return 0;
            }
        } else {
            sprite_image_no = ov_image;
        }
    }

    if (sprite_image_no >= 8) {
        tile                  = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
        flag_lsb              = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain & 1;
        tile_in_building_range = (tile >= 0x82 && tile <= 0xa1);
        if (tile_in_building_range && sprite_image_no >= 8) sprite_image_no += 2;
        else if (flag_lsb) sprite_image_no++;
    }
    if (sprite_image_no < 0x23) place_lefthalf_overlay(style);
    return 1;
}

// FUNCTION: C2 0x3921D
// WIN: 0x0045f599
// Lines 1223–1263
//
// Right-edge half-diamond overlay.  Same image-selection
// logic; routes through place_righthalf_overlay.
// BYTE-EXACT; the ov_image named-local shape and Rule 115 decl order
// mirror show_left_overlay (see its comment for the full recovery
// postmortem -- the comma-dup hack is gone in both twins).
//
int show_right_overlay(int style)
{
    unsigned char tile;
    unsigned char b;
    int idx;
    unsigned char flag_lsb;
    int tile_in_building_range = 0;
    int ov_image;

    if (overlays_on != 1) return 0;
    idx = pm_shown_ptr / 20;
    if ((b = landfill_pool[idx]) == 0) {
        flag_lsb = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain & 0xe7;
        tile = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
        if (flag_lsb == 0)
            return 0;
        if (overlay0_empty_mode != 0)
            return 0;
        if (tile >= 0x82 && tile <= 0xa1) sprite_image_no = 7;
        else sprite_image_no = 0;
    } else {
        ov_image = b - 0x76; if (b == 0x96) {
            if (ov_map_mode == 1) sprite_image_no = ov_image;
            else if (ov_map_mode == 6) {
                tile = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
                if (tile >= 0xe5 && tile <= 0xf0)
                    return 0;
                sprite_image_no = landfill_pool[idx] - 0x76;
            } else {
                return 0;
            }
        } else {
            sprite_image_no = ov_image;
        }
    }

    if (sprite_image_no >= 8) {
        tile                  = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
        flag_lsb              = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain & 1;
        tile_in_building_range = (tile >= 0x82 && tile <= 0xa1);
        if (tile_in_building_range && sprite_image_no >= 8) sprite_image_no += 2;
        else if (flag_lsb) sprite_image_no++;
    }
    if (sprite_image_no < 0x23) place_righthalf_overlay(style);
    return 1;
}

// FUNCTION: C2 0x39377
// WIN: 0x0045f7e4
// Lines 1265–1291
//
// Predicate used by the top / sprite passes: returns 1 when the cell
// at pm_shown_ptr is currently covered by an overlay sprite (so the
// caller should skip the normal draw).  Returns 0 when overlays are
// off, the cell is a virtual sentinel, or the landfill-pool entry
// resolves to a no-overlay state for this ov_map_mode.  Mirrors the
// gating in show_overlay's image-selection chain.
int are_overlays_on(void)
{
    unsigned char x, b;
    if (overlays_on != 1) return 0;
    if (((pm_shown_ptr) >= 0x0FFF0000)) return 0;
    if ((unsigned char)landfill_pool[pm_shown_ptr / 20] == 0) {
        x = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).terrain & 0xe7;
        if (x == 0) return 0;
        if (overlay0_empty_mode != 0) return 0;
        return 1;
    }

    if ((unsigned char)landfill_pool[pm_shown_ptr / 20] != 0x96) return 1;
    if (ov_map_mode == 1) return 1;
    if (ov_map_mode != 6) return 0;
    b = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).base_kind;
    if (b < 0xe5) return 1; if (b <= 0xf0) return 0;
    return 1;
}
