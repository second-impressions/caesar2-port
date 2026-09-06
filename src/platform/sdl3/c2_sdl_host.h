#ifndef C2_SDL_HOST_H
#define C2_SDL_HOST_H

#include <SDL3/SDL_events.h>

#include "c2_host.h"

void c2_sdl_host_handle_event(SDL_Event *event);
int c2_sdl_host_is_interactive(void);
/* Largest integer scale, at most `preferred`, at which a width x height
 * window still fits the primary display's usable area (never below 1). */
int c2_sdl_host_window_scale(int width, int height, int preferred);
#if PORT_FEAT_DEBUG_OBSERVATION
void c2_sdl_host_set_headless_mouse(int x, int y, unsigned int buttons);
void c2_sdl_host_set_headless_arrow_keys(unsigned int arrow_keys);
void c2_sdl_host_push_headless_key(enum c2_host_key key);
void c2_sdl_host_push_headless_text(uint32_t codepoint);
#endif

#endif /* C2_SDL_HOST_H */
