#ifndef C2_SDL_SMOKE_H
#define C2_SDL_SMOKE_H

#include <SDL3/SDL_stdinc.h>

enum c2_sdl_smoke_kind {
    C2_SDL_SMOKE_NONE,
    C2_SDL_SMOKE_PROVINCE_SELECTION,
    C2_SDL_SMOKE_CITY_LOOP,
    C2_SDL_SMOKE_TUTORIAL,
    C2_SDL_SMOKE_SAVE_LOAD,
    C2_SDL_SMOKE_MUSIC_BUFFER,
    C2_SDL_SMOKE_CAMPANIA_TRANSITION,
    C2_SDL_SMOKE_PROVINCE_BUILD,
    C2_SDL_SMOKE_CITY_BUILD
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
    Uint64 confirmation_seen_at;
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
    int file_phase;
    int tutorial_started;
    int tutorial_confirmation_seen;
    int tutorial_pages_seen;
    int last_tutorial_page;
    int saved_province;
    int saved_map_x;
    int saved_map_y;
    int saved_zoom;
    int saved_denarii;
    Uint64 modal_clicked_at;
    Uint64 province_clicked_at;
    int build_denarii;
    int build_selection_x;
    int build_selection_y;
    int build_attempt;
    Uint64 music_started;
    Uint64 music_last_sample;
    Uint64 music_initial_produced_bytes;
    unsigned int music_samples;
    unsigned int music_zero_fill_samples;
    unsigned int music_min_queued_ms;
    unsigned int music_max_queued_ms;
};

void c2_sdl_smoke_init(struct c2_sdl_smoke *smoke,
                       enum c2_sdl_smoke_kind kind, Uint64 now);
enum c2_sdl_smoke_result c2_sdl_smoke_iterate(
    struct c2_sdl_smoke *smoke, Uint64 now);

#endif /* C2_SDL_SMOKE_H */
