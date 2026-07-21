#ifndef C2_SDL_SMOKE_H
#define C2_SDL_SMOKE_H

#include <SDL3/SDL_stdinc.h>

enum c2_sdl_smoke_kind {
    C2_SDL_SMOKE_NONE,
    C2_SDL_SMOKE_PROVINCE_SELECTION,
    C2_SDL_SMOKE_CITY_LOOP
};

enum c2_sdl_smoke_result {
    C2_SDL_SMOKE_RUNNING,
    C2_SDL_SMOKE_SUCCESS,
    C2_SDL_SMOKE_FAILURE
};

struct c2_sdl_smoke {
    enum c2_sdl_smoke_kind kind;
    Uint64 started;
    Uint64 last_input;
    Uint64 city_quiet_since;
    Uint64 release_mouse_at;
    int phase;
    int scan_offset;
    int confirmation_clicked;
    int mouse_down;
    int mouse_x;
    int mouse_y;
    int initial_map_x;
    int initial_zoom;
    int name_phase;
    int name_failed;
};

void c2_sdl_smoke_init(struct c2_sdl_smoke *smoke,
                       enum c2_sdl_smoke_kind kind, Uint64 now);
enum c2_sdl_smoke_result c2_sdl_smoke_iterate(
    struct c2_sdl_smoke *smoke, Uint64 now);

#endif /* C2_SDL_SMOKE_H */
