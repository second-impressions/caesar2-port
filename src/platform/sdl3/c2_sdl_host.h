#ifndef C2_SDL_HOST_H
#define C2_SDL_HOST_H

#include <SDL3/SDL_events.h>

void c2_sdl_host_handle_event(SDL_Event *event);
void c2_sdl_host_set_headless_mouse(int x, int y, unsigned int buttons);

#endif /* C2_SDL_HOST_H */
