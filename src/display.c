// D:\C2\CODE\display.c

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
/* request_message — struct defined in message.c; layout in entities.h. */


// FUNCTION: C2 0x5A25C
// WIN: 0x0045f920
// Lines 36–41
//
// Read a raw PL8 image file straight into `internal_screen`.
// The image is `screen_width x rows` pixels and skips the first
// 0x18 bytes (the PL8 header).  Beeps on failure.
void show_pl8file(const char *fname, int rows)
{
    if (readfile(fname, internal_screen,
                 screen_width * rows, 0x18) == 0) {
        test_beeps();
        return;
    }
    flush_sb_buffer();
}

// FUNCTION: C2 0x5A28B
// WIN: 0x0045f960
// Lines 43–56
//
// Load a full-screen PL8 image plus its companion palette, push
// to the SVGA buffer and fade in.  Returns 1 on success, 0 if
// either file fails to read.
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

// FUNCTION: C2 0x5A2DD
// WIN: 0x0045f9d6
// Lines 58–68
//
// Read an LBM (Deluxe Paint) image into `scratch_buffer` then
// decode it into `internal_screen` via `convert_lbm_file`.  Used
// by tutorial mode; bails with a printf + exit(100) if the file
// is too large for the scratch buffer.
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

// FUNCTION: C2 0x5A345
// WIN: 0x0045fa67
// Lines 70–77
//
// Read a compressed `.PIC` image into the scratch buffer, run it
// through the evacuate + depress decompression chain, and copy
// the result into `internal_screen` (without touching the
// palette).  Beeps on any stage failure.
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

// FUNCTION: C2 0x5A3BC
// WIN: 0x0045fb16
// Lines 79–87
//
// Like show_picfile but also installs the .PIC file's embedded
// palette via set_palette.
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

// FUNCTION: C2 0x5A43D
// WIN: 0x0045fbd3
// Lines 89–105
//
// Render a `cols × rows` window using the system_panel
// 9-slice sprite atlas (sprites 0..8: TL TM TR / ML MM MR
// / BL BM BR).  Each cell is 16×16 pixels.  The
// `sprite_image_no` math reuses the row's base sprite
// (0/3/6) and adds a 0/+1/+2 column offset; the corner
// case at (col == 0) is handled by skipping the increment.
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

// FUNCTION: C2 0x5A4CF
// WIN: 0x0045fcb7
// Lines 107–117
//
// Fill a `w x h` cell grid (16 px per cell) at (x, y) with the
// blank-interior tile of the system_panel atlas (sprite 4).
// Counterpart to show_a_system_window's 9-slice border.
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


// FUNCTION: C2 0x5A523
// WIN: 0x0045fd38
// Lines 120–124
//
// Composite "framed mosaic" window: outer 1-cell-wide stone
// border (frame) plus the interior tile fill (blank) at
// (x+16, y+16) measured in pixels with a (w-2, h-2) cell
// extent.  Reseeds the stone-random counter so each window
// looks the same on every redraw.
void show_a_mosaic_window(int x, int y, int w, int h)
{
    stone_random_count = 0xa;
    show_a_mosaic_frame(x, y, w, h);
    show_a_mosaic_blank(x + 16, y + 16, w - 2, h - 2);
}

// FUNCTION: C2 0x5A559
// WIN: 0x0045fd86
// Lines 127–146
//
// Draw the 1-cell-thick decorative "stone" border of a w x h window
// at (x, y) using sprites 0..3 for the corners and
// stone_random_data / 2 + {4, 0xc, 0x14, 0x1c} for the top / bottom
// / left / right edges.  Interior cells are skipped.
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

// FUNCTION: C2 0x5A6D5
// WIN: 0x0045ff6a
// Lines 149–162
//
// Render a 1-row decorative "divider" of `w` 16-pixel stone cells at
// (x, y).  The first cell uses sprite 0x4d, the last uses 0x4e, and
// interior cells use a deterministic pick from stone_random_data[]
// halved + 4.  The 4th parameter is preserved by callers but ignored.
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

// FUNCTION: C2 0x5A774
// WIN: 0x0046002d
// Lines 164–175
//
// Render a `cols x rows` interior fill using sprites
// game_panels[0x24..0x63] driven by a precomputed pseudo-
// random walk through stone_random_data[].  The counter
// post-increments and wraps at 0x40, so each redraw of the
// same surface is deterministic given the entry counter
// (callers reseed it via stone_random_count = ... before
// invoking).  Each cell is 16x16 pixels.
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

// FUNCTION: C2 0x5A7F7
// WIN: 0x004600de
// Lines 178–183
//
// Place a single 32x32 sprite from the game_panels atlas at
// (x, y) -- a thin wrapper that just stamps the three sprite
// globals before dispatching to place_32x32_block.
void show_a_32_block(int x, int y, int sprite_no)
{
    sprite_image_no = sprite_no;
    sprite_x        = x;
    sprite_y        = y;
    place_32x32_block(game_panels);
}

// FUNCTION: C2 0x5A812
// WIN: 0x0046010e
// Lines 186–191
//
// Read width/height from the 16-byte sprite header in
// `scratch_buffer`.  The header for sprite `n` lives at offset
// n*16 + 8; bytes [0..1] are the little-endian 16-bit width,
// bytes [2..3] the height.
void get_general_sprite_sizes(int sprite_index)
{
    unsigned char *p;

    data_ptr = sprite_index * 16 + 8;
    p = (scratch_buffer) + data_ptr;
    sprite_width  = p[0] + (p[1] << 8);
    sprite_height = p[2] + (p[3] << 8);
}

// FUNCTION: C2 0x5A858
// WIN: 0x00460180
// Lines 193–211
//
// Generic sprite drawer: parse the 16-byte header at
// scratch_buffer + idx*16 + 8 (width / height / start / x / y),
// validate width/height bounds, set up the global sprite state, and
// dispatch to place_i_sprite.
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

// FUNCTION: C2 0x5A915
// WIN: 0x004602ce
// Lines 213–236
//
// Like general_sprite, but additionally clips against the screen
// rectangle and dispatches to the matching write_i_*_sprite variant
// based on the clip outcome.
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

// FUNCTION: C2 0x5AA34
// WIN: 0x0046049b
// Lines 238–266
//
// Like write_general_sprite, but skips the top `front_offset` rows of
// the sprite (sprite_y += front_offset, sprite_height -= front_offset,
// sprite_start advanced by front_offset * sprite_width) before clipping
// and dispatch.
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

// FUNCTION: C2 0x5AB70
// WIN: 0x0046068e
// Lines 268–285
//
// Restore a previously-saved background sprite back into
// `sprite_addr`'s buffer.  Like general_sprite but takes the
// sprite-table base address as a parameter and reads (x, y)
// from header bytes [8..11] instead of from caller args.
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

// FUNCTION: C2 0x5AC44
// WIN: 0x004607fb
// Lines 287–303
//
// Load and place one rectangular city-screen component.  Header entries
// are 8 shorts each in int_city_header; entries >=4 are shifted right by
// 0xee pixels before drawing.  Sibling of draw_region_map_part /
// draw_battle_part.
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

// FUNCTION: C2 0x5ACF9
// WIN: 0x004608f1
// Lines 306–319
//
// Region-map screen sibling of draw_city_map_part.
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

// FUNCTION: C2 0x5AD8D
// WIN: 0x004609e7
// Lines 324–340
//
// Load and place one rectangular battle-screen component.  Header
// entries are 8 shorts each in int_battle_header; entries >=4 are
// shifted down by 0xc8 pixels before drawing.
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

// FUNCTION: C2 0x5AE3E
// WIN: 0x00460add
// Lines 342–367
//
// Blink the text-entry caret.  Increments request_message[1] every
// frame as a 0..0x10 phase counter; while the high half of the cycle
// is active and a font/letter has been laid down, draw either the
// thick "insert" caret (5 rectangles forming an I-bar) or the thin
// "overwrite" caret (one horizontal underline rectangle).
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

// FUNCTION: C2 0x5AF5D
// WIN: 0x00460c28
// Lines 369–427
//
// Switch to VGA mode 0x13, play a Smacker animation centred at (0x18,
// 0x18), and restore the SVGA 640x480 game mode afterwards.  The
// playback loop polls the mouse and bails out on either button.
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

// FUNCTION: C2 0x5B0A0
// WIN: 0x00460db5
// Lines 429–468
//
// Stay in SVGA mode and play a Smacker animation centred at (0, 0)
// with the c2inf.anims_on flag forced on for the duration; restored
// at exit.  Mouse pre-clicks (rather than full clicks) terminate.
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

