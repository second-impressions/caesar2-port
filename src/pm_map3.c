
#include "c2_data.h"

int elephant_riders[96] = { 16, -10, 15, -9, 15, -10, 16, -10, 15, -9, 15, -9, 18, -7, 17, -7, 17, -7, 18, -7, 17, -7, 17, -7, 16, -6, 16, -6, 15, -7, 16, -6, 15, -6, 15, -7, 11, -4, 11, -5, 11, -5, 12, -3, 12, -4, 12, -5, 7, -5, 7, -5, 7, -6, 7, -5, 7, -5, 7, -6, 5, -7, 6, -7, 6, -7, 5, -7, 6, -7, 6, -7, 6, -9, 7, -9, 7, -9, 6, -9, 7, -9, 7, -9, 12, -10, 12, -10, 12, -10, 12, -10, 12, -10, 12, -10 };


extern void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color);
extern void write_i_sprite(unsigned char *sprite_addr);
extern void write_i_left_sprite(unsigned char *sprite_addr);
extern void write_i_right_sprite(unsigned char *sprite_addr);

// Top-level battle-map render: clears the per-frame sprite error flag, draws the battle-map base
// and top-half overlays, paints a 2x8 grid of small clipping sprites along the top edge at zoom 1,
// decrements the cell-update countdown, and pops the battle-setup dialog if the setup phase is.
// FUNCTION: C2 0x3bb88
// FUNCTION: C2WIN 0x0041dc80
void show_battlemap(void)
{
    int i;

    sprite_error = 0;
    show_battlemap_base();
    show_battlemap_top();
    if (zoom_level == 1) {
        for (i = 0x18; i < 0x164; i += 8)
            show_internal_2x8(0, i, 0);
    }
    if (update_map != 0)
        --update_map;
    if (battle_setup_count > 1)
        show_battle_setup_box();
}

// Paint the terrain half of the battle pseudo-map, including clipped edges and virtual background tiles.
// FUNCTION: C2 0x3bbeb
// FUNCTION: C2WIN 0x0041dd0b
void show_battlemap_base(void)
{
    int i;
    int j;
    unsigned char tile;

    sprite_y   = pm_screen_y_start;
    sprite_x   = pm_screen_x_start;
    pm_shown_y = pm_y;
    pm_y_clip  = 0;

    /* top edge */
    for (i = 0, pm_shown_x = pm_x;
         i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (update_map == 0) {
            if (((pm_shown_ptr) >= 0x0FFF0000)) {
                sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                if (sprite_image_no >= 7) place_diamond(2);
                sprite_x += pm_diamond_width;
                continue;
            }
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            if (tile == 0) {
                sprite_x += pm_diamond_width;
                continue;
            }
            if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
            if ((tile & 0xc) != 0) {
                tile &= 0xc;
                if      (tile == 4) sprite_image_no = 0xf;
                else if (tile == 8) sprite_image_no = 0xd;
                else                sprite_image_no = 0xe;
                place_diamond(2);
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                sprite_x += pm_diamond_width;
                continue;
            }
        }
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(2);
            sprite_x += pm_diamond_width;
            continue;
        } else {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
            sprite_image_no += 0x10;
            place_diamond(2);
        }
        sprite_x += pm_diamond_width;
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    /* interior */
    mid3_line_with_sides_base();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        mid3_line_no_sides_base();
        mid3_line_with_sides_base();
    }

    /* bottom edge — same as top with style=1 */
    sprite_x   = pm_screen_x_start;
    for (i = 0, pm_shown_x = pm_x; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (update_map == 0) {
            if (((pm_shown_ptr) >= 0x0FFF0000)) {
                sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                if (sprite_image_no >= 7) place_diamond(1);
                sprite_x += pm_diamond_width;
                continue;
            }
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            if (tile == 0) {
                sprite_x += pm_diamond_width;
                continue;
            }
            if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
            if ((tile & 0xc) != 0) {
                tile &= 0xc;
                if (tile == 4) sprite_image_no = 0xf;
                else if (tile == 8) sprite_image_no = 0xd;
                else sprite_image_no = 0xe;
                place_diamond(1);
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                sprite_x += pm_diamond_width;
                continue;
            }
        }
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(1);
            sprite_x += pm_diamond_width;
            continue;
        } else {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
            sprite_image_no += 0x10;
            place_diamond(1);
        }
        sprite_x += pm_diamond_width;
    }
}

// Top-half (figures, arrows, sprites) twin of show_battlemap_base. Same scanline layout but each
// cell invokes place3_sprite() which draws the figure_a / arrow_a stored in battle_map[+1] / [+3].
// FUNCTION: C2 0x3bf3c
// FUNCTION: C2WIN 0x0041e1e0
void show_battlemap_top(void)
{
    int i;
    int j;

    sprite_y   = pm_screen_y_start;
    sprite_x   = pm_screen_x_start;
    pm_shown_y = pm_y;
    pm_y_clip  = 0;
    pm_shown_x = pm_x;
    for (i = 0; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    mid3_line_with_sides_top();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        mid3_line_no_sides_top();
        mid3_line_with_sides_top();
    }

    /* bottom-edge sprite-only scan (mirror of top) */
    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }
    pm_shown_y++;
    sprite_y  += pm_diamond_half_height;
    pm_y_clip  = 0;

    bottom3_line_with_sides();
    bottom3_line_no_sides();
}

// Render one interior base scanline (no edge clipping). All pm_screen_width cells use the
// full-diamond style.
// FUNCTION: C2 0x3c0af
// FUNCTION: C2WIN 0x0041e3ca
void mid3_line_no_sides_base(void)
{
    int i;
    unsigned char tile;

    sprite_x = pm_screen_x_start;
    for (i = 0, pm_shown_x = pm_x; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (update_map == 0) {
            if (((pm_shown_ptr) >= 0x0FFF0000)) {
                sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                if (sprite_image_no >= 7) place_diamond(0);
                sprite_x += pm_diamond_width; continue;
            }
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            if (tile == 0) {
                sprite_x += pm_diamond_width;
                continue;
            }
            if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
            if ((tile & 0xc) != 0) {
                tile &= 0xc;
                if      (tile == 4) sprite_image_no = 0xf;
                else if (tile == 8) sprite_image_no = 0xd;
                else                sprite_image_no = 0xe;
                place_diamond(0);
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                sprite_x += pm_diamond_width;
                continue;
            }
        }
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(0);
        } else {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
            sprite_image_no += 0x10;
            place_diamond(0);
        }
        sprite_x += pm_diamond_width;
        print3_test_info();
    }
    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Render one interior base scanline with edge clipping — uses place_lefthalf_diamond() for the
// leftmost column, place_righthalf_diamond() for the rightmost, and full place_diamond() for the
// (pm_screen_width-2) middle cells.
// FUNCTION: C2 0x3c244
// FUNCTION: C2WIN 0x0041e622
void mid3_line_with_sides_base(void)
{
    int i;
    unsigned char tile;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    /* leftmost half-diamond — same body as middle but place_lefthalf_diamond */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (update_map == 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            if (sprite_image_no >= 7) place_lefthalf_diamond();
        } else {
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty & 0xf0;
            if (tile != 0) {
                if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
                if ((tile & 0xc) != 0) {
                    tile &= 0xc;
                    if      (tile == 4) sprite_image_no = 0xf;
                    else if (tile == 8) sprite_image_no = 0xd;
                    else                sprite_image_no = 0xe;
                    place_lefthalf_diamond();
                    refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                } else {
terrain_left:
                    if (((pm_shown_ptr) >= 0x0FFF0000)) {
                        sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                        place_lefthalf_diamond();
                    } else {
                        (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
                        sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
                        sprite_image_no += 0x10;
                        place_lefthalf_diamond();
                    }
                }
            }
        }
    } else goto terrain_left;
    sprite_x += pm_diamond_half_width;

    /* middle full diamonds */
    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (update_map == 0) {
            if (((pm_shown_ptr) >= 0x0FFF0000)) {
                sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                if (sprite_image_no >= 7) place_diamond(0);
                sprite_x += pm_diamond_width; continue;
            }
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty & 0xf0;
            if (tile == 0) {
                sprite_x += pm_diamond_width;
                continue;
            }
            if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
            if ((tile & 0xc) != 0) {
                tile &= 0xc;
                if      (tile == 4) sprite_image_no = 0xf;
                else if (tile == 8) sprite_image_no = 0xd;
                else                sprite_image_no = 0xe;
                place_diamond(0);
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                sprite_x += pm_diamond_width;
                continue;
            }
        }
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(0);
        } else {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
            sprite_image_no += 0x10;
            place_diamond(0);
        }
        sprite_x += pm_diamond_width;
        print3_test_info();
    }

    /* rightmost half-diamond — same body as middle but place_righthalf_diamond */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (update_map == 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            if (sprite_image_no >= 7) place_righthalf_diamond();
            goto mid_done;
        }
        tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
        (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
        if (tile == 0) goto mid_done;
        if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
        if ((tile & 0xc) != 0) {
            tile &= 0xc;
            if      (tile == 4) sprite_image_no = 0xf;
            else if (tile == 8) sprite_image_no = 0xd;
            else                sprite_image_no = 0xe;
            place_righthalf_diamond();
            refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            goto mid_done;
        }
    }
    if (((pm_shown_ptr) >= 0x0FFF0000)) {
        sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
        place_righthalf_diamond();
    } else {
        (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
        sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
        sprite_image_no += 0x10;
        place_righthalf_diamond();
    }

mid_done:
    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Top-half mid scanline, no edge half-cells. Three render passes (leading/main/trailing
// half-cells, styles 2/0/2).
// FUNCTION: C2 0x3c61e
// FUNCTION: C2WIN 0x0041ebe0
void mid3_line_no_sides_top(void)
{
    int i;

    if (pm_x > 0) {
        sprite_x = pm_screen_x_start - pm_diamond_width;
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_x - 1];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);
    }
    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }

    if (pm_shown_x < 80) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);
    }

    sprite_y += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Top-half mid scanline, full edge cells. Three render passes: leading full cell (style=1), main
// row of pm_screen_width - 1 cells (style=0), trailing full cell (style=2).
// FUNCTION: C2 0x3c733
// FUNCTION: C2WIN 0x0041ed78
void mid3_line_with_sides_top(void)
{
    int i;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(1);
    sprite_x += pm_diamond_half_width;

    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Bottom-edge with-sides scanline. Three render passes: 1.
// FUNCTION: C2 0x3c846
// FUNCTION: C2WIN 0x0041ef08
void bottom3_line_with_sides(void)
{
    int i;

    if (pm_shown_y >= PM_H) return;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(1);
    sprite_x += pm_diamond_half_width;

    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Bottom-edge no-sides scanline. Three render passes: 1.
// FUNCTION: C2 0x3c960
// FUNCTION: C2WIN 0x0041f098
void bottom3_line_no_sides(void)
{
    int i;

    if (pm_shown_y >= PM_H) return;

    if (pm_x > 0) {
        sprite_x = pm_screen_x_start - pm_diamond_width;
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_x - 1];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);
    }
    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }

    if (pm_shown_x < 80) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);
    }

    sprite_y += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// Composite figure-and-arrow sprite renderer for one battle-map cell. Reads figure_a from
// battle_map[+1] and arrow_a from battle_map[+3] of the current pm_shown_ptr.
// FUNCTION: C2 0x3ca7f
// FUNCTION: C2WIN 0x0041f231
void place3_sprite(int style)
{
    int xi;
    int yi;
    int dir;
    int xo;
    int yo;
    unsigned char *hdr;
    unsigned char *sd;
    int rider;
    int eleph;
    int xr;
    int yr;
    int z;

    figure_a = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).figure;
    arrow_a  = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).arrow;

    if (figure_a != 0) {
        dir = figure_list[figure_a].direction - map_direction;
        if (dir < 0) dir += 8;
        if (zoom_level == 1) {
            xo = fig_walking_x_ofsets_z1[dir * 8 + figure_list[figure_a].wf_step_x];
            yo = fig_walking_y_ofsets_z1[dir * 8 + figure_list[figure_a].wf_step_x];
        } else {
            xo = fig_walking_x_ofsets_z2[dir * 8 + figure_list[figure_a].wf_step_x];
            yo = fig_walking_y_ofsets_z2[dir * 8 + figure_list[figure_a].wf_step_x];
        }
        if      (style == 1) xo -= 2;
        else if (style == 2) xo += pm_diamond_half_width;
        else                 xo += pm_diamond_half_width - pm_diamond_width;
        yo += pm_diamond_half_height;
        xi = xo; yi = yo;

        if (figure_list[figure_a].sprite_dir != 0) sd = figure_list[figure_a].sprite_data_ptr;
        else sd = figure_list[figure_a].arrow_data_ptr;
        sprite_image_no = figure_list[figure_a].sprite_anim;
        data_ptr        = sprite_image_no * 0x10 + 8;
        hdr             = sd + data_ptr; sprite_start = hdr[4] + (hdr[5] << 8) + (hdr[6] << 16);
        sprite_width    = hdr[0] + (hdr[1] << 8);
        sprite_height   = hdr[2] + (hdr[3] << 8);
        if (sprite_start > 0x4baf0) { sprite_error++; return; }
        if (sprite_width <= 0)      { sprite_error++; return; }
        if (sprite_width > 0x12c)   { sprite_error++; return; }
        if (sprite_height <= 0)     { sprite_error++; return; }
        if (sprite_height > 0x12c)  { sprite_error++; return; }
        sprite_x_off = (signed char)hdr[0xe];
        sprite_y_off = (signed char)hdr[0xd];
        xo = xo - sprite_x_off;
        yo = yo - sprite_y_off;
        old_sprite_x = sprite_x; old_sprite_y = sprite_y;
        sprite_x += xo;
        sprite_y += yo;
        if (figure_list[figure_a].fight_state == 2) {
            if (zoom_level == 1) { sprite_x -= 0x18; sprite_y -= 0x40; }
            else                 { sprite_x -= 0xc;  sprite_y -= 0x20; }
            refresh_figure3_square((sprite_x - 4) >> 4, sprite_y >> 4);
        } else if (figure_list[figure_a].fight_state != 0) {
            if (zoom_level == 1) { sprite_x -= 0x14; sprite_y -= 0x2a; }
            else                 { sprite_x -= 0xa;  sprite_y -= 0x14; }
            refresh_figure2_square((sprite_x - 4) >> 4, sprite_y >> 4);
        } else {
            if (zoom_level == 1) { sprite_x -= 0xa;  sprite_y -= 0x20; }
            else                 { sprite_x -= 4;    sprite_y -= 0x10; }
            refresh_figure_square((sprite_x - 0x14) >> 4, sprite_y >> 4);
        }
        xclip(pm_screen_x_start, 0x280);
        yclip(0x18, 0x168);
        if (yclipped != 5) {
            if      (xclipped == 1) write_i_left_sprite(sd);
            else if (xclipped == 2) write_i_right_sprite(sd);
            else                    write_i_sprite(sd);
        }
        sprite_x = old_sprite_x; sprite_y = old_sprite_y;

        if (figure_list[figure_a].fight_state == 2) {
            for (rider = 1; rider >= 0; rider--) {
                if (rider == 1) sprite_image_no = figure_list[figure_a].archer_image_a;
                else sprite_image_no = figure_list[figure_a].archer_image_b;
                data_ptr      = sprite_image_no * 0x10 + 8;
                hdr           = sd + data_ptr; sprite_start = hdr[4] + (hdr[5] << 8) + (hdr[6] << 16);
                sprite_width  = hdr[0] + (hdr[1] << 8);
                sprite_height = hdr[2] + (hdr[3] << 8);
                if (sprite_start > 0x4baf0) { sprite_error++; return; }
                if (sprite_width <= 0)      { sprite_error++; return; }
                if (sprite_width > 0x12c)   { sprite_error++; return; }
                if (sprite_height <= 0)     { sprite_error++; return; }
                if (sprite_height > 0x12c)  { sprite_error++; return; }
                sprite_x_off = (signed char)hdr[0xe];
                sprite_y_off = (signed char)hdr[0xd];
                xo = xi - sprite_x_off;
                yo = yi - sprite_y_off;
                old_sprite_x = sprite_x; old_sprite_y = sprite_y;
                sprite_x += xo;
                sprite_y += yo;
                sprite_x -= 0x18;
                sprite_y -= 0x40;
                eleph = figure_list[figure_a].sprite_anim; sprite_x += elephant_riders[eleph * 2];
                sprite_y += elephant_riders[eleph * 2 + 1];
                sprite_x += rider * 6;
                sprite_y -= rider * 6;
                if (rider <= 0) sprite_height -= 8;
                refresh_figure_square((sprite_x - 4) >> 4, sprite_y >> 4);
                xclip(pm_screen_x_start, 0x280);
                yclip(0x18, 0x168);
                if (yclipped != 5) {
                    if      (xclipped == 1) write_i_left_sprite(sd);
                    else if (xclipped == 2) write_i_right_sprite(sd);
                    else                    write_i_sprite(sd);
                }
                sprite_x = old_sprite_x; sprite_y = old_sprite_y;
            }
        }
    }

    if (arrow_a != 0) {
        do {
            dir = (unsigned char)arrow_list[arrow_a].heading - map_direction;
            if (dir < 0) dir += 8;
            xr = arrow_list[arrow_a].start_x % 7; yr = arrow_list[arrow_a].start_y % 7;
            if (zoom_level == 1) {
                z = map_direction / 2; xo = arrow_xr_x_ofset[xr + 7 * z];
                xo += arrow_yr_x_ofset[yr + 7 * z];
                yo = arrow_xr_y_ofset[xr + 7 * z];
                yo += arrow_yr_y_ofset[yr + 7 * z];
            }
            if      (style == 1) xo -= 2;
            else if (style == 2) xo += pm_diamond_half_width;
            else                 xo += pm_diamond_half_width - pm_diamond_width;
            yo += pm_diamond_half_height;

            sd = arrow_list[arrow_a].arrow_data_ptr;
            if (sd == 0) return;
            sprite_image_no = arrow_list[arrow_a].sprite_anim;
            data_ptr        = sprite_image_no * 0x10 + 8;
            hdr             = sd + data_ptr; sprite_start = hdr[4] + (hdr[5] << 8) + (hdr[6] << 16);
            sprite_width    = (hdr[0]) + (hdr[1] << 8);
            sprite_height   = hdr[2] + (hdr[3] << 8);
            if (sprite_start > 0x4baf0) { sprite_error++; return; }
            if (sprite_width <= 0)      { sprite_error++; return; }
            if (sprite_width > 0x12c)   { sprite_error++; return; }
            if (sprite_height <= 0)     { sprite_error++; return; }
            if (sprite_height > 0x12c)  { sprite_error++; return; }
            old_sprite_x = sprite_x; old_sprite_y = sprite_y;
            sprite_x += xo;
            sprite_y += yo;
            sprite_x -= sprite_width >> 1;
            sprite_y -= sprite_height;
            sprite_y -= (unsigned char)arrow_list[arrow_a].anim_count / 2 + 0x20;
            refresh_figure_square((sprite_x - 4) >> 4, sprite_y >> 4);
            xclip(pm_screen_x_start, 0x280);
            yclip(0x18, 0x168);
            if (yclipped != 5) {
                if      (xclipped == 1) write_i_left_sprite(sd);
                else if (xclipped == 2) write_i_right_sprite(sd);
                else                    write_i_sprite(sd);
            }
            sprite_x = old_sprite_x; sprite_y = old_sprite_y;
            arrow_a = (unsigned char)arrow_list[arrow_a].flight_done;
        } while (arrow_a != 0);
    }
}

// Battle-map debug overlay. test_mode1 prints the state_idx of the figure stored in battle_map+1
// (or zero for an empty cell); test_mode2 prints signed battle_map+3.
// FUNCTION: C2 0x3d2d5
// FUNCTION: C2WIN 0x0041fe23
void print3_test_info(void)
{
    int v;
    int fig;

    if (test_mode1 != 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) return;
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        fig = ((unsigned char *)battle_map)[(pm_shown_ptr) + 1];
        if (fig != 0) v = figure_list[fig].state_idx;
        else v = 0;
        font_no(v, 0x20, " ",
                sprite_x + 0x14 - pm_diamond_width, sprite_y + 0xa,
                font1, 0x3f);
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    } else if (test_mode2 != 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) return;
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        v = (signed char)((unsigned char *)battle_map)[(pm_shown_ptr) + 3];
        font_no(v, 0x20, " ",
                sprite_x + 0x14 - pm_diamond_width, sprite_y + 0xa,
                font1, 0x3f);
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }
}
