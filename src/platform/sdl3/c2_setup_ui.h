#ifndef C2_SETUP_UI_H
#define C2_SETUP_UI_H

/*
 * Native launcher / game-data setup window.
 *
 * The native equivalent of the browser shell's landing page: a small SDL
 * window that shows the active game-data source, lets the user pick an
 * installation folder, a disc image/archive, or a physical CD-ROM drive,
 * imports it with visible progress, and only then hands over to the engine.
 * It is driven from the SDL app callbacks; nothing here blocks.
 */

#include <SDL3/SDL.h>
#include <stddef.h>

struct c2_setup_config {
    const char *version;        /* shown in the title line */
    const char *source;         /* current source, may be "" */
    const char *cache_root;     /* user-data directory for imports */
    const char *asset_profile;  /* may be NULL */
    const char *error;          /* initial error line, may be NULL */
    int fullscreen;             /* initial display settings */
    int fractional_scaling;
};

enum c2_setup_result {
    C2_SETUP_RUNNING = 0,
    C2_SETUP_PLAY,      /* c2_setup_selected_source() is ready to run */
    C2_SETUP_QUIT
};

int c2_setup_open(const struct c2_setup_config *config);
void c2_setup_handle_event(const SDL_Event *event);
enum c2_setup_result c2_setup_iterate(void);
const char *c2_setup_selected_source(void);
const char *c2_setup_selected_profile(void);
int c2_setup_selected_fullscreen(void);
int c2_setup_selected_fractional_scaling(void);
void c2_setup_close(void);

/* Cheap layout probe used to decide whether Play can be offered before any
 * import runs: directory sources must expose C2.ENG in one of the known
 * layouts; file and device sources only need to exist. */
int c2_setup_source_looks_valid(const char *path);

#endif
