#ifndef C2_SETUP_UI_H
#define C2_SETUP_UI_H

/*
 * Native launcher: the native counterpart of the browser page.
 *
 * A small SDL window that shows what the game-data library holds, adds
 * installations, disc images, archives and CD-ROM drives to it with visible
 * progress, exports it as a .c2assets file or removes it, and holds the
 * text, speech, music and display choices. Only after Play does the engine
 * start. It is driven from the SDL app callbacks; nothing here blocks.
 */

#include <SDL3/SDL.h>
#include <stddef.h>

struct c2_setup_config {
    const char *version;          /* shown in the title line */
    const char *game_data_root;   /* holds library/ and local/ */
    const char *pending_source;   /* add this first (command line), may be NULL */
    const char *speech;           /* speech language wished for; "" or NULL = pick */
    const char *text_language;    /* compiled-in text language tag; "" or NULL = detect */
    const char *music_source;     /* "windows", "dos"; "" or NULL = the default */
    const char *error;            /* initial error line, may be NULL */
    int fullscreen;               /* initial display settings */
    int fractional_scaling;
};

enum c2_setup_result {
    C2_SETUP_RUNNING = 0,
    C2_SETUP_PLAY,      /* the library is playable */
    C2_SETUP_QUIT
};

int c2_setup_open(const struct c2_setup_config *config);
void c2_setup_handle_event(const SDL_Event *event);
enum c2_setup_result c2_setup_iterate(void);
const char *c2_setup_selected_speech(void);
const char *c2_setup_selected_text_language(void);
const char *c2_setup_selected_music_source(void);
int c2_setup_selected_fullscreen(void);
int c2_setup_selected_fractional_scaling(void);
void c2_setup_close(void);

#endif
