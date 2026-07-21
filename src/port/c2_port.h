#ifndef C2_PORT_H
#define C2_PORT_H

#include <stdint.h>

#define C2_SCREEN_WIDTH 640
#define C2_SCREEN_HEIGHT 480
#define C2_SCREEN_PIXELS (C2_SCREEN_WIDTH * C2_SCREEN_HEIGHT)
#define C2_PALETTE_BYTES (256 * 3)

int c2_port_compat_init(void);
void c2_port_compat_shutdown(void);
int c2_port_save_screenshot(const char *filename);
uint64_t c2_port_frame_hash(void);

#endif /* C2_PORT_H */
