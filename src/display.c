
#include <stdio.h>      /* printf */
#include <stdlib.h>     /* exit   */

#include "c2_data.h"
#include "c2_types.h"     /* struct request_message */

extern void place_32x32_block(unsigned char *panels_addr);
extern void place_16x16_block(unsigned char *panel_addr);
extern int  depress(unsigned char *dst, unsigned char *src);
extern void copy(unsigned char *src, unsigned char *dst, int n);
extern int convert_lbm_file(unsigned char *src, unsigned char *dst, char *pal, int length);
extern void place_i_sprite(unsigned char *sprite_addr);  /* sprites.asm */
extern void write_i_sprite(unsigned char *sprite_addr);   /* sprites.asm */
extern void write_i_left_sprite(unsigned char *sprite_addr);
extern void write_i_right_sprite(unsigned char *sprite_addr);


// Load rows of PL8 pixels into the internal screen, skipping the file header.
// FUNCTION: C2 0x5a25c
// FUNCTION: C2WIN 0x0045f920
void show_pl8file(const char *fname, int rows)
{
    if (readfile(fname, internal_screen,
                 screen_width * rows, 0x18) == 0) {
        test_beeps();
        return;
    }
    flush_sb_buffer();
}

// Load a full-screen PL8 image and palette, display it, and fade the palette in.
// FUNCTION: C2 0x5a28b
// FUNCTION: C2WIN 0x0045f960
int display_pl8file(char *pl8_fname, char *pal_fname)
{
    if (readfile(pl8_fname, internal_screen, 0x4b000, 0x18) == 0)
        return 0;
    if (readfile(pal_fname, &temp_palette, 0x300, 0) == 0)
        return 0;
    setup_whole_screen_refresh();
    refresh_svga_screen();
    fade_to_palette(temp_palette);
    return 1;
}

// Load and decode an LBM image into the internal screen.
// FUNCTION: C2 0x5a2dd
// FUNCTION: C2WIN 0x0045f9d6
void show_lbm(const char *fname)
{
    int rc;

    rc = readfile(fname, ((void *)scratch_buffer),
                  scratch_buffer_size, 0);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(scratch_buffer, internal_screen, temp_palette, rc);
    }
    flush_sb_buffer();
}

// Load a compressed PIC image into the internal screen without changing the palette.
// FUNCTION: C2 0x5a345
// FUNCTION: C2WIN 0x0045fa67
void show_picfile(char *fname)
{
    if (readfile(fname, ((void *)scratch_buffer), 0x4e200, 0) == 0) {
        test_beeps();
        return;
    }
    if (evacuate(((scratch_buffer) + 2), internal_screen) > 0x4e200) {
        test_beeps();
        return;
    }
    if (depress(internal_screen, scratch_buffer) > 0x4e200) {
        test_beeps();
        return;
    }
    copy(scratch_buffer + 0x300, internal_screen, screen_size);
    flush_sb_buffer();
}

// Load a compressed PIC image and install its embedded palette.
// FUNCTION: C2 0x5a3bc
// FUNCTION: C2WIN 0x0045fb16
void display_picfile(char *fname)
{
    if (readfile(fname, ((void *)scratch_buffer), 0x4e200, 0) == 0) {
        test_beeps();
        return;
    }
    if (evacuate(((scratch_buffer) + 2), internal_screen) > 0x4e200) {
        test_beeps();
        return;
    }
    if (depress(internal_screen, scratch_buffer) > 0x4e200) {
        test_beeps();
        return;
    }
    copy(scratch_buffer + 0x300, internal_screen, screen_size);
    set_palette(((char *)scratch_buffer));
    flush_sb_buffer();
}

// Draw a tiled system window with corners, edges, and an interior.
// FUNCTION: C2 0x5a43d
// FUNCTION: C2WIN 0x0045fbd3
void show_a_system_window(int x, int y, int cols, int rows)
{
    int row;
    int col;

    for (row = 0; row < rows; row++) {
        for (col = 0; col < cols; col++) {
            if (row == 0)
                sprite_image_no = 0;
            else if (row == rows - 1)
                sprite_image_no = 6;
            else
                sprite_image_no = 3;
            if (col != 0) {
                if (col == cols - 1)
                    sprite_image_no += 2;
                else
                    sprite_image_no++;
            }
            sprite_x = x + col * 16;
            sprite_y = y + row * 16;
            place_16x16_block(system_panel);
        }
    }
}

// Fill a rectangular area with the system window's interior tile.
// FUNCTION: C2 0x5a4cf
// FUNCTION: C2WIN 0x0045fcb7
void show_a_system_blank(int x, int y, int w, int h)
{
    int i;
    int j;
    for (i = 0; i < h; i++) {
        for (j = 0; j < w; j++) {
            sprite_image_no = 4;
            sprite_x = x + j * 16;
            sprite_y = y + i * 16;
            place_16x16_block(system_panel);
        }
    }
}


// Draw a deterministic stone mosaic window with a frame and tiled interior.
// FUNCTION: C2 0x5a523
// FUNCTION: C2WIN 0x0045fd38
void show_a_mosaic_window(int x, int y, int w, int h)
{
    stone_random_count = 0xa;
    show_a_mosaic_frame(x, y, w, h);
    show_a_mosaic_blank(x + 16, y + 16, w - 2, h - 2);
}

// Draw the corner and edge tiles of a stone mosaic frame.
// FUNCTION: C2 0x5a559
// FUNCTION: C2WIN 0x0045fd86
void show_a_mosaic_frame(int x, int y, int w, int h)
{
    int row;
    int col;

    for (row = 0; row < h; row++) {
        for (col = 0; col < w; col++) {
            if (stone_random_count++ >= 0x40)
                stone_random_count = 0;

            if (row == 0 && col == 0) {
                sprite_image_no = 0;
            } else if (row == h - 1 && col == 0) {
                sprite_image_no = 3;
            } else if (row == 0 && col == w - 1) {
                sprite_image_no = 1;
            } else if (row == h - 1 && col == w - 1) {
                sprite_image_no = 2;
            } else if (row == 0) {
                sprite_image_no =
                    stone_random_data[stone_random_count] / 2 + 4;
            } else if (row == h - 1) {
                sprite_image_no =
                    stone_random_data[stone_random_count] / 2 + 0xc;
            } else if (col == 0) {
                sprite_image_no =
                    stone_random_data[stone_random_count] / 2 + 0x14;
            } else if (col == w - 1) {
                sprite_image_no =
                    stone_random_data[stone_random_count] / 2 + 0x1c;
            } else {
                continue;
            }
            sprite_x = x + col * 16;
            sprite_y = y + row * 16;
            place_16x16_block(game_panels);
        }
    }
}

// Draw a horizontal stone divider with capped ends.
// FUNCTION: C2 0x5a6d5
// FUNCTION: C2WIN 0x0045ff6a
void mosaic_frame_divider(int x, int y, int w, int unused)
{
    int i;

    (void)unused;
    for (i = 0; i < w; i++) {
        if (stone_random_count++ >= 0x40)
            stone_random_count = 0;
        if (i == 0)
            sprite_image_no = 0x4d;
        else if (i == w - 1)
            sprite_image_no = 0x4e;
        else
            sprite_image_no =
                stone_random_data[stone_random_count] / 2 + 4;
        sprite_x = x + i * 16;
        sprite_y = y;
        place_16x16_block(game_panels);
    }
}

// Fill a mosaic interior with a deterministic sequence of stone tiles.
// FUNCTION: C2 0x5a774
// FUNCTION: C2WIN 0x0046002d
void show_a_mosaic_blank(int x, int y, int cols, int rows)
{
    int row;
    int col;

    for (row = 0; row < rows; row++) {
        for (col = 0; col < cols; col++) {
            if (stone_random_count++ >= 0x40)
                stone_random_count = 0;
            sprite_image_no = stone_random_data[stone_random_count] + 0x24;
            sprite_x = x + col * 16;
            sprite_y = y + row * 16;
            place_16x16_block(game_panels);
        }
    }
}

// Draw one 32-by-32 game-panel sprite at the requested position.
// FUNCTION: C2 0x5a7f7
// FUNCTION: C2WIN 0x004600de
void show_a_32_block(int x, int y, int sprite_no)
{
    sprite_image_no = sprite_no;
    sprite_x        = x;
    sprite_y        = y;
    place_32x32_block(game_panels);
}

// Read a sprite's dimensions from its header in the scratch buffer.
// FUNCTION: C2 0x5a812
// FUNCTION: C2WIN 0x0046010e
void get_general_sprite_sizes(int sprite_index)
{
    unsigned char *p;

    data_ptr = sprite_index * 16 + 8;
    p = (scratch_buffer) + data_ptr;
    sprite_width  = p[0] + (p[1] << 8);
    sprite_height = p[2] + (p[3] << 8);
}

// Validate and draw an unclipped sprite from the scratch buffer.
// FUNCTION: C2 0x5a858
// FUNCTION: C2WIN 0x00460180
void general_sprite(int idx, int x, int y)
{
    unsigned char *base;
    unsigned char *p;

    data_ptr = idx * 16 + 8;
    sprite_image_no = idx;
    base = (scratch_buffer);
    p = base + data_ptr;
    sprite_width  = p[0] + (p[1] << 8);
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0)      return;
    if (sprite_width > 0x280)   return;
    if (sprite_height <= 0)     return;
    if (sprite_height > 0x1e0)  return;
    sprite_x = x;
    sprite_y = y;
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(base);
}

// Validate, clip, and draw a sprite from the scratch buffer.
// FUNCTION: C2 0x5a915
// FUNCTION: C2WIN 0x004602ce
void write_general_sprite(int idx, int x, int y)
{
    unsigned char *p;

    data_ptr = idx * 16 + 8;
    sprite_image_no = idx;
    p = (scratch_buffer) + data_ptr;
    sprite_width  = p[0] + (p[1] << 8);
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0)      return;
    if (sprite_width > 0x280)   return;
    if (sprite_height <= 0)     return;
    if (sprite_height > 0x1e0)  return;
    sprite_x = x;
    sprite_y = y;
    x_wrap = 0x280 - sprite_width;
    xclip(0, screen_width);
    yclip(0, screen_height);
    if (yclipped == 5) return;
    if (xclipped == 1) {
        write_i_left_sprite(scratch_buffer);
        return;
    }
    if (xclipped == 2) {
        write_i_right_sprite(scratch_buffer);
        return;
    }
    write_i_sprite(scratch_buffer);
}

// Draw a clipped sprite after omitting the requested number of top rows.
// FUNCTION: C2 0x5aa34
// FUNCTION: C2WIN 0x0046049b
void write_general_sprite_with_front_ofset(int idx, int x, int y, int front_offset)
{
    unsigned char *p;

    data_ptr = idx * 16 + 8;
    sprite_image_no = idx;
    p = (scratch_buffer) + data_ptr;
    sprite_width  = p[0] + (p[1] << 8);
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0)      return;
    if (sprite_width > 0x280)   return;
    if (sprite_height <= 0)     return;
    if (sprite_height > 0x1e0)  return;
    sprite_x = x;
    sprite_y = y;
    sprite_y      = y + front_offset;
    sprite_height = sprite_height - front_offset;
    sprite_start += front_offset * sprite_width;
    x_wrap = 0x280 - sprite_width;
    xclip(0, screen_width);
    yclip(0, screen_height);
    if (yclipped == 5) return;
    if (xclipped == 1) {
        write_i_left_sprite(scratch_buffer);
        return;
    }
    if (xclipped == 2) {
        write_i_right_sprite(scratch_buffer);
        return;
    }
    write_i_sprite(scratch_buffer);
}

// Restore a saved screen region using the position stored in its sprite header.
// FUNCTION: C2 0x5ab70
// FUNCTION: C2WIN 0x0046068e
void restore_picture_part(unsigned char *sprite_addr, int sprite_idx)
{
    data_ptr = sprite_idx * 16 + 8;
    sprite_width  = sprite_addr[data_ptr] + (sprite_addr[data_ptr + 1] << 8);
    sprite_height = sprite_addr[data_ptr + 2] + (sprite_addr[data_ptr + 3] << 8);
    sprite_start  = sprite_addr[data_ptr + 4] + (sprite_addr[data_ptr + 5] << 8) + (sprite_addr[data_ptr + 6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    sprite_x = sprite_addr[data_ptr + 8] + (sprite_addr[data_ptr + 9] << 8);
    sprite_y = sprite_addr[data_ptr + 10] + (sprite_addr[data_ptr + 11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}

// Load and draw one rectangular component of the city interface.
// FUNCTION: C2 0x5ac44
// FUNCTION: C2WIN 0x004607fb
void draw_city_map_part(int n)
{
    int offset;

    offset = int_city_header[n * 8 + 6];
    offset += (int_city_header[n * 8 + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = int_city_header[n * 8 + 4];
    sprite_height = int_city_header[n * 8 + 5];
    sprite_x      = int_city_header[n * 8 + 8];
    if (n >= 4) {
        sprite_x += 0xee;
    }
    sprite_y      = int_city_header[n * 8 + 9];
    readfile("int_city.pl8", ((void *)scratch_buffer), sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}

// Load and draw one rectangular component of the region interface.
// FUNCTION: C2 0x5acf9
// FUNCTION: C2WIN 0x004608f1
void draw_region_map_part(int n)
{
    int offset;

    offset = int_region_header[n * 8 + 6];
    offset += (int_region_header[n * 8 + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = int_region_header[n * 8 + 4];
    sprite_height = int_region_header[n * 8 + 5];
    sprite_x      = int_region_header[n * 8 + 8];
    if (n >= 4) {
        sprite_x += 0xee;
    }
    sprite_y      = int_region_header[n * 8 + 9];
    readfile("int_prov.pl8", ((void *)scratch_buffer), sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}

// Load and draw one rectangular component of the battle interface.
// FUNCTION: C2 0x5ad8d
// FUNCTION: C2WIN 0x004609e7
void draw_battle_part(int n)
{
    int saved_n = n;
    int offset;

    n *= 8;
    offset = int_battle_header[n + 6];
    offset += (int_battle_header[n + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = int_battle_header[n + 4];
    sprite_height = int_battle_header[n + 5];
    sprite_x      = int_battle_header[n + 8];
    sprite_y      = int_battle_header[n + 9];
    if (saved_n >= 4) sprite_y += 0xc8;
    readfile("int_batl.pl8", ((void *)scratch_buffer), sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}

// Blink either the insertion bar or underline caret at the text cursor.
// FUNCTION: C2 0x5ae3e
// FUNCTION: C2WIN 0x00460add
void show_cursor(unsigned char *font)
{
    int width;

    request_message.caret_count++;
    if (request_message.caret_count > 0x10) request_message.caret_count = 0;
    if (cursor_y == 0) return;
    width = get_letter_width((signed char)format_buffer[this_letter], font);
    if (request_message.caret_count <= 8) return;
    if (insert_cursor != 0) {
        draw_a_rect(cursor_x - 2, cursor_y - 2, 1, 0xf, 3);
        draw_a_rect(cursor_x - 4, cursor_y - 3, 2, 1, 3);
        draw_a_rect(cursor_x - 4, cursor_y + 0xe, 2, 1, 3);
        draw_a_rect(cursor_x - 1, cursor_y - 3, 2, 1, 3);
        draw_a_rect(cursor_x - 1, cursor_y + 0xe, 2, 1, 3);
    } else {
        draw_a_rect(cursor_x - 1, cursor_y + 0xe, width + 2, 2, 3);
    }
}

// Play a mouse-skippable Smacker animation in VGA mode, then restore the SVGA game display.
// FUNCTION: C2 0x5af5d
// FUNCTION: C2WIN 0x00460c28
void do_vga_smacked_anim(char *fname)
{
    if (check_file_exists(fname) == 0) return;
    black_out();
    wvbl2();
    clear_a_screen();
    clear_all_screens();
    setup_whole_screen_refresh();
    refresh_svga_screen();
    set_bank(0);
    screen_mode = 1;
    set_vga_mode(0x13);
    screen_width  = 0x140;
    screen_height = 0xc8;
    screen_size   = 0xfa00;
    clear_map_gfx_buffers();
    clear_battle_gfx_buffers();
    start_smacking(fname, 0, 0x18, 2);
    if (are_smacking()) {
        out2 = 0;
        out1 = 0;
        while (out1 != 1) {
            hold_hot_keys = 1;
            get_mouse();
            continue_smacking(0, 0x18, 2);
            if (mouse_right_click) {
                out1 = 1;
                out2 = 1;
            }
            if (mouse_left_click) {
                out1 = 1;
                out2 = 1;
            }
            if (!are_smacking()) out1 = 1;
        }
        stop_smacking();
    }
    black_out();
    clear_all_screens();
    screen_mode = 2;
    set_svga_640_480(0);
    clear_a_screen();
    set_mouse_limits();
    init_map_gfx_buffers();
    init_battle_gfx_buffers();
}

// Play a mouse-skippable Smacker animation in SVGA mode and restore the graphics buffers.
// FUNCTION: C2 0x5b0a0
// FUNCTION: C2WIN 0x00460db5
void do_svga_smacked_anim(char *fname)
{
    int saved_anims_on;

    saved_anims_on = c2inf.anims_on;
    c2inf.anims_on = 1;
    clear_map_gfx_buffers();
    clear_battle_gfx_buffers();
    start_smacking(fname, 0, 0, 0);
    out2 = 0;
    out1 = 0;
    while (out1 != 1) {
        hold_hot_keys = 1;
        get_mouse();
        if (continue_smacking(0, 0, 0)) refresh_svga_screen();
        if (mouse_right_preclick) {
            out1 = 1;
            out2 = 1;
        }
        if (mouse_left_preclick) {
            out1 = 1;
            out2 = 1;
        }
        if (!are_smacking()) out1 = 1;
    }
    stop_smacking();
    black_out();
    clear_all_screens();
    clear_a_screen();
    c2inf.anims_on = saved_anims_on;
    init_map_gfx_buffers();
    init_battle_gfx_buffers();
}
