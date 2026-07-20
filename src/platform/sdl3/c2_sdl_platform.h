#ifndef C2_SDL_PLATFORM_H
#define C2_SDL_PLATFORM_H

#include <stdint.h>

int c2_sdl_platform_init(const char *data_dir, int headless);
void c2_sdl_platform_shutdown(void);
void c2_sdl_platform_present(void);
uint64_t c2_sdl_title_hash(void);

#endif /* C2_SDL_PLATFORM_H */
