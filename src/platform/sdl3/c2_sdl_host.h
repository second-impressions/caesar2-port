#ifndef C2_SDL_HOST_H
#define C2_SDL_HOST_H

#include <SDL3/SDL_events.h>

#include "c2_host.h"

void c2_sdl_host_handle_event(SDL_Event *event);
#if C2_FEAT_DEBUG_OBSERVATION
void c2_sdl_host_set_headless_mouse(int x, int y, unsigned int buttons);
void c2_sdl_host_push_headless_key(enum c2_host_key key);
#endif

#endif /* C2_SDL_HOST_H */
