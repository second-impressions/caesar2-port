
/* The refresh table stores redraw priorities for a 40×30 grid of 16-pixel tiles. */
#include "refresh.h"
#include "c2_data.h"

struct refresh_bank_row refresh_bank_switch_data[30] = {
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 1, 1, 6, 16 },
    { 0, 1, 0, 0 },
    { 0, 1, 0, 0 },
    { 0, 1, 0, 0 },
    { 0, 1, 0, 0 },
    { 0, 1, 0, 0 },
    { 1, 2, 12, 32 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 1, 3, 3, 8 },
    { 0, 3, 0, 0 },
    { 0, 3, 0, 0 },
    { 0, 3, 0, 0 },
    { 0, 3, 0, 0 },
    { 0, 3, 0, 0 },
    { 1, 4, 9, 24 },
    { 0, 4, 0, 0 },
    { 0, 4, 0, 0 },
    { 0, 4, 0, 0 },
    { 0, 4, 0, 0 }
};

/* Refresh-grid state and precomputed tile offsets. */
struct svga_cell svga_refresh_data[1361];
int ref_y;
int ref_x;
int ref_ptr;
int refresh_count;
char svga_refresh_table[1364];

/* Copies part of a 16×16 tile into the active SVGA bank. */
extern void refresh_16x16_partblock(int screen_off, unsigned short bank_off,
                                    int width);


// Mark every clean screen tile for one redraw.
// FUNCTION: C2 0x28e94
// FUNCTION: C2WIN 0x0043a640
void setup_whole_screen_refresh(void)
{
    int i;
    for (i = 0; i < 0x4b0; i++) {
        if (svga_refresh_table[i] == 0)
            svga_refresh_table[i] = 1;
    }
}

// Mark the refresh tiles covered by the mouse pointer at priority 2.
// FUNCTION: C2 0x28eb2
// FUNCTION: C2WIN 0x0043a68c
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    (*(char (*)[30][40])svga_refresh_table)[ref_y][ref_x] = 2;
    if (ref_x < 39)
        (*(char (*)[30][40])svga_refresh_table)[ref_y][ref_x + 1] = 2;
    if (ref_y < 29)
        (*(char (*)[30][40])svga_refresh_table)[ref_y + 1][ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        (&svga_refresh_table[ref_x])[(ref_y + 1) * 40 + 1] = 2;
}


// Mark a 2×2 cell square in the SVGA refresh table dirty.
// FUNCTION: C2 0x28fb5
// FUNCTION: C2WIN 0x0043a7d2
void refresh_sprite_square(int x, int y)
{
    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    if (ref_ptr < 0x4b0) {
        if (svga_refresh_table[ref_ptr] < 2)
            svga_refresh_table[ref_ptr] = 2;
        if (svga_refresh_table[ref_ptr + 1] < 2)
            svga_refresh_table[ref_ptr + 1] = 2;
        if (svga_refresh_table[ref_ptr + 0x28] < 2)
            svga_refresh_table[ref_ptr + 0x28] = 2;
        if (svga_refresh_table[ref_ptr + 0x29] < 2)
            svga_refresh_table[ref_ptr + 0x29] = 2;
    }
}

// Mark a 4×4 tile square at priority 2, replacing any existing priority.
// FUNCTION: C2 0x29041
// FUNCTION: C2WIN 0x0043a8ad
void refresh_figure_square(int x, int y)
{
    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    if (ref_ptr < 0x4b0) {
        svga_refresh_table[ref_ptr + 0x00] = 2;
        svga_refresh_table[ref_ptr + 0x01] = 2;
        svga_refresh_table[ref_ptr + 0x02] = 2;
        svga_refresh_table[ref_ptr + 0x03] = 2;
        svga_refresh_table[ref_ptr + 0x28] = 2;
        svga_refresh_table[ref_ptr + 0x29] = 2;
        svga_refresh_table[ref_ptr + 0x2a] = 2;
        svga_refresh_table[ref_ptr + 0x2b] = 2;
        svga_refresh_table[ref_ptr + 0x50] = 2;
        svga_refresh_table[ref_ptr + 0x51] = 2;
        svga_refresh_table[ref_ptr + 0x52] = 2;
        svga_refresh_table[ref_ptr + 0x53] = 2;
        svga_refresh_table[ref_ptr + 0x78] = 2;
        svga_refresh_table[ref_ptr + 0x79] = 2;
        svga_refresh_table[ref_ptr + 0x7a] = 2;
        svga_refresh_table[ref_ptr + 0x7b] = 2;
    }
}

// Mark a 5×5 tile square at priority 2.
// FUNCTION: C2 0x290ce
// FUNCTION: C2WIN 0x0043a9c0
void refresh_figure2_square(int x, int y)
{
    int i;

    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    for (i = 0; i < 5; i++) {
        if (ref_ptr >= 0x4b0) return;
        svga_refresh_table[ref_ptr + 0] = 2;
        svga_refresh_table[ref_ptr + 1] = 2;
        svga_refresh_table[ref_ptr + 2] = 2;
        svga_refresh_table[ref_ptr + 3] = 2;
        svga_refresh_table[ref_ptr + 4] = 2;
        ref_ptr += 40;
    }
}

// Mark a 6×6 tile square at priority 2.
// FUNCTION: C2 0x29131
// FUNCTION: C2WIN 0x0043aa77
void refresh_figure3_square(int x, int y)
{
    int i;

    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    for (i = 0; i < 6; i++) {
        if (ref_ptr >= 0x4b0) return;
        svga_refresh_table[ref_ptr + 0] = 2;
        svga_refresh_table[ref_ptr + 1] = 2;
        svga_refresh_table[ref_ptr + 2] = 2;
        svga_refresh_table[ref_ptr + 3] = 2;
        svga_refresh_table[ref_ptr + 4] = 2;
        svga_refresh_table[ref_ptr + 5] = 2;
        ref_ptr += 40;
    }
}

// Raise a 4×2 tile rectangle to at least priority 2.
// FUNCTION: C2 0x2919a
// FUNCTION: C2WIN 0x0043ab3a
void refresh_sprite2w_square(int x, int y)
{
    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    if (ref_ptr < 0x4b0) {
        if (svga_refresh_table[ref_ptr + 0x00] < 2)
            svga_refresh_table[ref_ptr + 0x00] = 2;
        if (svga_refresh_table[ref_ptr + 0x01] < 2)
            svga_refresh_table[ref_ptr + 0x01] = 2;
        if (svga_refresh_table[ref_ptr + 0x02] < 2)
            svga_refresh_table[ref_ptr + 0x02] = 2;
        if (svga_refresh_table[ref_ptr + 0x03] < 2)
            svga_refresh_table[ref_ptr + 0x03] = 2;
        if (svga_refresh_table[ref_ptr + 0x28] < 2)
            svga_refresh_table[ref_ptr + 0x28] = 2;
        if (svga_refresh_table[ref_ptr + 0x29] < 2)
            svga_refresh_table[ref_ptr + 0x29] = 2;
        if (svga_refresh_table[ref_ptr + 0x2a] < 2)
            svga_refresh_table[ref_ptr + 0x2a] = 2;
        if (svga_refresh_table[ref_ptr + 0x2b] < 2)
            svga_refresh_table[ref_ptr + 0x2b] = 2;
    }
}

// Raise a 5×6 tile rectangle to at least priority 2.
// FUNCTION: C2 0x2928e
// FUNCTION: C2WIN 0x0043ac9d
void refresh_region_sprite_square(int x, int y)
{
    int i;

    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    if (ref_ptr >= 0x4b0) return;
    for (i = 0; i < 6; i++) {
        if (svga_refresh_table[ref_ptr + 0] < 2)
            svga_refresh_table[ref_ptr + 0] = 2;
        if (svga_refresh_table[ref_ptr + 1] < 2)
            svga_refresh_table[ref_ptr + 1] = 2;
        if (svga_refresh_table[ref_ptr + 2] < 2)
            svga_refresh_table[ref_ptr + 2] = 2;
        if (svga_refresh_table[ref_ptr + 3] < 2)
            svga_refresh_table[ref_ptr + 3] = 2;
        if (svga_refresh_table[ref_ptr + 4] < 2)
            svga_refresh_table[ref_ptr + 4] = 2;
        ref_ptr += 0x28;
        if (ref_ptr >= 0x4b0) return;
    }
}

// Marks one map square for redraw at the requested refresh priority.
// FUNCTION: C2 0x29361
// FUNCTION: C2WIN 0x0043add7
void refresh_a_square(int x, int y, char val)
{
    ref_ptr = x + y * 0x28;
    svga_refresh_table[ref_ptr + 0x00] = val;
    svga_refresh_table[ref_ptr + 0x01] = val;
    svga_refresh_table[ref_ptr + 0x02] = val;
    svga_refresh_table[ref_ptr + 0x03] = val;
    svga_refresh_table[ref_ptr + 0x04] = val;
    svga_refresh_table[ref_ptr + 0x28] = val;
    svga_refresh_table[ref_ptr + 0x29] = val;
    svga_refresh_table[ref_ptr + 0x2a] = val;
    svga_refresh_table[ref_ptr + 0x2b] = val;
    svga_refresh_table[ref_ptr + 0x2c] = val;
    svga_refresh_table[ref_ptr + 0x50] = val;
    svga_refresh_table[ref_ptr + 0x51] = val;
    svga_refresh_table[ref_ptr + 0x52] = val;
    svga_refresh_table[ref_ptr + 0x53] = val;
    svga_refresh_table[ref_ptr + 0x54] = val;
}

// Mark a five-tile-wide footprint at priority 2, clipping rows above the screen.
// FUNCTION: C2 0x293d2
// FUNCTION: C2WIN 0x0043aed4
void refresh_a_bigger_square(int x, int y)
{
    int rows;
    int i;

    rows = 6;
    if (y < -0x20) {
        y = 0;
        rows = 3;
    } else if (y < -0x10) {
        y = 0;
        rows = 4;
    } else if (y < 0) {
        y = 0;
        rows = 5;
    }
    ref_ptr = x + y * 40;
    for (i = 0; i < rows; ++i) {
        if (ref_ptr >= 0x4b0) return;
        svga_refresh_table[ref_ptr + 0] = 2;
        svga_refresh_table[ref_ptr + 1] = 2;
        svga_refresh_table[ref_ptr + 2] = 2;
        svga_refresh_table[ref_ptr + 3] = 2;
        svga_refresh_table[ref_ptr + 4] = 2;
        ref_ptr += 0x28;
    }
}

// Raise a 14×12 tile rectangle to priority 2, clipping at the top and left edges.
// FUNCTION: C2 0x29458
// FUNCTION: C2WIN 0x0043afc4
void refresh_big_action_square(int x, int y)
{
    int w;
    int h;
    int i;
    int j;

    h = 12;
    w = 14;
    if (x < 0) {
        x = 0;
        w = 8;
    }
    if (y < 0) {
        y = 0;
        h = 8;
    }
    ref_ptr = x + y * 40;
    for (i = 0; i < h; i++, ref_ptr += 40) {
        for (j = 0; j < w; j++) {
            int idx = ref_ptr + j;
            if (idx >= 0x4b0) return;
            if (svga_refresh_table[idx] < 2) {
                svga_refresh_table[idx] = 2;
            }
        }
    }
}

// Mark clean tiles in the 30×29 map viewport for one redraw.
// FUNCTION: C2 0x294d0
// FUNCTION: C2WIN 0x0043b0aa
void setup_map_screen_refresh(void)
{
    int j = 1;
    int idx = 0x28;
    int i;
    for (; j < 0x1e; j++, idx += 0xa) {
        for (i = 0; i < 0x1e; i++, idx++) {
            if (svga_refresh_table[idx] == 0)
                svga_refresh_table[idx] = 1;
        }
    }
}

// Fill the 30×29 map viewport with the requested refresh priority.
// FUNCTION: C2 0x29506
// FUNCTION: C2WIN 0x0043b11f
void setup_map_screen_long_refresh(int fill)
{
    int j = 1;
    int idx = 0x28;
    int i;
    for (; j < 0x1e; j++, idx += 0xa) {
        for (i = 0; i < 0x1e; i++) {
            svga_refresh_table[idx] = fill;
            idx++;
        }
    }
}

// Mark refresh-grid rows 1 through 22 for one battle-screen redraw.
// FUNCTION: C2 0x29533
// FUNCTION: C2WIN 0x0043b183
void setup_battle_screen_refresh(void)
{
    int i;
    int j;
    int idx = 0x28;
    for (j = 1; j < 0x17; j++) {
        for (i = 0; i < 0x28; i++) {
            svga_refresh_table[idx] = 1;
            idx++;
        }
    }
}

// Fill a tile rectangle whose origin is given in screen pixels.
// FUNCTION: C2 0x2955b
// FUNCTION: C2WIN 0x0043b1e1
void setup_refresh_area(int x, int y, int w, int h, int value)
{
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    x /= 16;
    y /= 16;

    ref_ptr = x + y * 40;

    for (ref_y = y; ref_y < y + h; ref_y++) {
        if (ref_ptr >= 0x4b0) break;
        for (ref_x = x; ref_x < x + w; ref_x++) {
            svga_refresh_table[ref_ptr] = value;
            ref_ptr++;
        }
        ref_ptr += 40 - w;
    }
}

// Precompute screen offsets and bank-switch metadata for all 40×30 refresh tiles.
// FUNCTION: C2 0x2960d
// FUNCTION: C2WIN 0x0043b2c9
void setup_svga_refresh_data(void)
{
    int py;
    int px;
    int idx;
    int modbase;
    int i;

    for (i = 0; i < 0x4b0; i++)
        svga_refresh_table[i] = 0;

    py = 0;
    idx = 0;
    modbase = 0x10000;
    for ( ; py < 0x1e0; py += 0x10) {
    for (px = 0; px < 0x280; px += 0x10, idx++) {
        svga_refresh_data[idx].screen_off = py * 5 * 128 + px;
        svga_refresh_data[idx].bank_off   = (unsigned short)(py * 0x280 + px) % modbase;
        svga_refresh_data[idx].split_off  = 0;

        if (refresh_bank_switch_data[py / 16].split != 0) {
            int split_col = refresh_bank_switch_data[py / 16].split_col;
            if (px >= split_col * 16) {
                svga_refresh_data[idx].split_off = (unsigned short)(px - split_col * 16);
            } else {
                svga_refresh_data[idx].split_off = (unsigned short)((40 - split_col) * 16 + px);
            }
        }
    }
    }
}

// Reconfigure pseudo-map (PM) viewport globals for the city screen at the given zoom level.
// FUNCTION: C2 0x296e5
// FUNCTION: C2WIN 0x0043b412
void refresh_zoom_mode(int level)
{
    zoom_level = level;
    if (zoom_level == 0) {
        scroll_amount = 1;
        pm_screen_width = 8;
        pm_screen_height = 0x1e;
        pm_screen_x_start = 0;
        pm_screen_y_start = 9;
        pm_diamond_width = 0x3c;
        pm_diamond_height = 0x1e;
        pm_diamond_half_width = 0x1e;
        pm_diamond_half_height = 0xf;
    } else if ((level & 0xff) == 1) {
        scroll_amount = 2;
        pm_screen_width = 0x11;
        pm_screen_height = 0x40;
        pm_screen_x_start = 4;
        pm_screen_y_start = 0x11;
        pm_diamond_width = 0x1c;
        pm_diamond_height = 0xe;
        pm_diamond_half_width = 0xe;
        pm_diamond_half_height = 7;
    } else if ((level & 0xff) == 2) {
        scroll_amount = 4;
        pm_screen_width = 0x28;
        pm_screen_height = 0x96;
        pm_screen_x_start = 0;
        pm_screen_y_start = 0x15;
        pm_diamond_width = 0xc;
        pm_diamond_height = 6;
        pm_diamond_half_width = 6;
        pm_diamond_half_height = 3;
    }
    pm_screen_x_end = pm_screen_x_start + pm_screen_width * pm_diamond_width;
    pm_screen_y_end = pm_screen_y_start
                      + (pm_screen_height + 1) * pm_diamond_half_height;
}

// Reconfigure pseudo-map (PM) viewport globals for the battle screen at the given zoom level.
// FUNCTION: C2 0x29833
// FUNCTION: C2WIN 0x0043b5b2
void refresh_battle_zoom_mode(int level)
{
    zoom_level = level;
    if ((level & 0xff) == 1) {
        scroll_amount = 2;
        pm_screen_width = 0x17;
        pm_screen_height = 0x30;
        pm_screen_x_start = 0;
        pm_screen_y_start = 0x11;
        pm_diamond_width = 0x1c;
        pm_diamond_height = 0xe;
        pm_diamond_half_width = 0xe;
        pm_diamond_half_height = 7;
    } else if ((level & 0xff) == 2) {
        scroll_amount = 4;
        pm_screen_width = 0x35;
        pm_screen_height = 0x70;
        pm_screen_x_start = 6;
        pm_screen_y_start = 0x15;
        pm_diamond_width = 0xc;
        pm_diamond_height = 6;
        pm_diamond_half_width = 6;
        pm_diamond_half_height = 3;
    }
    pm_screen_x_end = pm_screen_x_start + pm_screen_width * pm_diamond_width;
    pm_screen_y_end = pm_screen_y_start
                      + (pm_screen_height + 1) * pm_diamond_half_height;
}

// Redraw dirty tiles, splitting copies that cross an SVGA bank boundary.
// FUNCTION: C2 0x2992d
// FUNCTION: C2WIN 0x0043b6cd
void refresh_svga_screen(void)
{
    int row;
    int col;
    int idx;
    int part_rows;
    int bank;
    int off;
    int saved_idx;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row].split != 0) {
            saved_idx = idx;
            /* Copy each tile's portion held in the preceding bank. */
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row].bank - 1);
                    part_rows = refresh_bank_switch_data[row].part_rows;
                    if (col < refresh_bank_switch_data[row].split_col)
                        part_rows++;
                    refresh_16x16_partblock(
                        svga_refresh_data[idx].screen_off,
                        svga_refresh_data[idx].bank_off,
                        part_rows);
                }
            }
            /* Copy each tile's remaining portion from the selected bank. */
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row].bank);
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    part_rows = refresh_bank_switch_data[row].part_rows;
                    if (col < refresh_bank_switch_data[row].split_col)
                        part_rows++;
                    off = part_rows * 5 * 128;
                    refresh_16x16_partblock(
                        svga_refresh_data[idx].screen_off + off,
                        svga_refresh_data[idx].split_off,
                        16 - part_rows);
                }
            }
        } else {
            /* Rows contained in one bank can be copied as full tiles. */
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    bank = refresh_bank_switch_data[row].bank;
                    set_bank(bank);
                    refresh_16x16_block(
                        svga_refresh_data[idx].screen_off,
                        svga_refresh_data[idx].bank_off);
                }
            }
        }
    }
}
