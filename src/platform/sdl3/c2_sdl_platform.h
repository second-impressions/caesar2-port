#ifndef C2_SDL_PLATFORM_H
#define C2_SDL_PLATFORM_H

#include <SDL3/SDL_events.h>

#include <stdint.h>

int c2_sdl_platform_init(const char *data_dir, int headless);
int c2_sdl_load_startup_ui(void);
void c2_sdl_platform_shutdown(void);
void c2_sdl_platform_present(void);
int c2_sdl_event_to_game(SDL_Event *event);
int c2_sdl_save_screenshot(const char *path);
uint64_t c2_sdl_title_hash(void);

#endif /* C2_SDL_PLATFORM_H */
