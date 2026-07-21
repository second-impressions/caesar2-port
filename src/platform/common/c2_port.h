#ifndef C2_PORT_H
#define C2_PORT_H

#define C2_SCREEN_WIDTH 640
#define C2_SCREEN_HEIGHT 480
#define C2_SCREEN_PIXELS (C2_SCREEN_WIDTH * C2_SCREEN_HEIGHT)
#define C2_PALETTE_BYTES (256 * 3)
#define C2_DIRECTORY_MAX_ENTRIES 100

int c2_port_compat_init(void);
void c2_port_compat_shutdown(void);
void c2_port_timing_reset(void);
int c2_port_wait_dos_clock_tick(void);
void c2_port_wait_for_frame(void);
void c2_port_wait_vblank(void);
int c2_port_save_screenshot(const char *filename);
int check_user_file_exists(const char *filename);

#endif /* C2_PORT_H */
