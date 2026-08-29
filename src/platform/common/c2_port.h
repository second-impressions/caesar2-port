#ifndef PORT_H
#define PORT_H

#include <stddef.h>

#include "c2_target.h"

#define C2_SCREEN_WIDTH 640
#define C2_SCREEN_HEIGHT 480
#define C2_SCREEN_PIXELS (C2_SCREEN_WIDTH * C2_SCREEN_HEIGHT)
#define C2_PALETTE_BYTES (256 * 3)
#define C2_DIRECTORY_MAX_ENTRIES 100

enum c2_port_scroll_key {
    PORT_SCROLL_LEFT = 1u << 0,
    PORT_SCROLL_RIGHT = 1u << 1,
    PORT_SCROLL_UP = 1u << 2,
    PORT_SCROLL_DOWN = 1u << 3
};

int c2_port_compat_init(void);
void c2_port_compat_shutdown(void);
void c2_port_timing_reset(void);
int c2_port_wait_dos_clock_tick(void);
void c2_port_wait_for_frame(void);
void c2_port_wait_vblank(void);
int c2_port_save_screenshot(const char *filename);
int check_user_file_exists(const char *filename);
void *c2_port_load_asset(const char *filename, size_t *size_out);
unsigned int c2_port_scroll_keys(void);
#if PORT_FIX_PAUSED_MUSIC_VARIETY
int c2_port_paused_music_branch(int base, int count,
                                int current_branch, int branch_count);
#endif
#if PORT_FEAT_STICKY_REGION_DROPDOWNS
void c2_port_region_selection_begin(int mouse_x, int mouse_y);
void c2_port_region_selection_end(void);
int c2_port_region_selection_consume_release(int mouse_x, int mouse_y);
#endif
void mouserange(int xmin, int ymin, int xmax, int ymax);

#endif /* PORT_H */
