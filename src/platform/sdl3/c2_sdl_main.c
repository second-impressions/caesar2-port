#define SDL_MAIN_USE_CALLBACKS 1
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_types.h"
#include "c2_sdl_platform.h"

#define C2_SPLASH_DURATION_MS 2000

enum c2_startup_stage {
    C2_STARTUP_SIERRA,
    C2_STARTUP_IMPRESSIONS,
    C2_STARTUP_MENU,
    C2_STARTUP_SETTINGS
};

struct c2_app_state {
    enum c2_startup_stage stage;
    Uint64 stage_started;
    const char *screenshot_path;
    int headless;
};

extern struct button_rec skill1_buttons[];
extern struct button_rec skill2_buttons[];
extern int display_pl8file(char *pl8_filename, char *palette_filename);
extern void refresh_svga_screen(void);
extern void show_buttons(int x, int y, struct button_rec *button_list, int button_count);
extern void show_skill1_box(void);
extern void show_skill2_box(void);

static struct c2_app_state c2_app;

static int parse_arguments(int argc, char *argv[], const char **data_dir,
                           const char **screenshot_path, int *headless)
{
    int i;

    *data_dir = getenv("C2_DATA_DIR");
    if (*data_dir == NULL || **data_dir == '\0') {
        *data_dir = ".";
    }
    *headless = 0;
    *screenshot_path = NULL;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--headless") == 0) {
            *headless = 1;
        } else if (strcmp(argv[i], "--data-dir") == 0 && i + 1 < argc) {
            i++;
            *data_dir = argv[i];
        } else if (strcmp(argv[i], "--screenshot") == 0 && i + 1 < argc) {
            i++;
            *screenshot_path = argv[i];
        } else {
            fprintf(stderr, "usage: %s [--headless] [--data-dir PATH] [--screenshot PATH]\n",
                    argv[0]);
            return 0;
        }
    }

    return 1;
}

static int show_startup_stage(enum c2_startup_stage stage)
{
    int loaded;

    loaded = 0;
    if (stage == C2_STARTUP_SIERRA) {
        loaded = display_pl8file("logo1.pl8", "logo1.256");
    } else if (stage == C2_STARTUP_IMPRESSIONS) {
        loaded = display_pl8file("logo2.pl8", "logo2.256");
    } else if (stage == C2_STARTUP_MENU) {
        show_skill1_box();
        show_buttons(0x50, 0x50, skill1_buttons, 4);
        refresh_svga_screen();
        loaded = 1;
    } else if (stage == C2_STARTUP_SETTINGS) {
        show_skill2_box();
        show_buttons(0x50, 0x50, skill2_buttons, 6);
        refresh_svga_screen();
        loaded = 1;
    }

    if (loaded) {
        c2_app.stage = stage;
        c2_app.stage_started = SDL_GetTicks();
        if (c2_app.screenshot_path != NULL &&
            !c2_sdl_save_screenshot(c2_app.screenshot_path)) {
            fprintf(stderr, "could not write screenshot to %s\n", c2_app.screenshot_path);
            return 0;
        }
    }
    return loaded;
}

static SDL_AppResult advance_startup(void)
{
    enum c2_startup_stage next_stage;

    if (c2_app.stage >= C2_STARTUP_MENU) {
        return SDL_APP_CONTINUE;
    }
    next_stage = (enum c2_startup_stage)(c2_app.stage + 1);
    if (!show_startup_stage(next_stage)) {
        return SDL_APP_FAILURE;
    }
    return SDL_APP_CONTINUE;
}

static SDL_AppResult redraw_settings(void)
{
    return show_startup_stage(C2_STARTUP_SETTINGS) ? SDL_APP_CONTINUE : SDL_APP_FAILURE;
}

SDL_AppResult SDL_AppInit(void **appstate, int argc, char *argv[])
{
    const char *data_dir;
    const char *screenshot_path;
    int headless;

    *appstate = &c2_app;
    if (!parse_arguments(argc, argv, &data_dir, &screenshot_path, &headless)) {
        return SDL_APP_FAILURE;
    }
    if (!c2_sdl_platform_init(data_dir, headless)) {
        return SDL_APP_FAILURE;
    }
    if (!c2_sdl_load_startup_ui()) {
        fprintf(stderr, "could not load the Caesar II interface assets from %s\n", data_dir);
        return SDL_APP_FAILURE;
    }

    c2_app.headless = headless;
    c2_app.screenshot_path = screenshot_path;
    if (!show_startup_stage(C2_STARTUP_SIERRA)) {
        fprintf(stderr, "could not load the Caesar II startup assets from %s\n", data_dir);
        return SDL_APP_FAILURE;
    }
    printf("sierra framebuffer fnv1a64=%016" PRIx64 "\n", c2_sdl_title_hash());

    if (headless) {
        if (advance_startup() == SDL_APP_FAILURE) {
            return SDL_APP_FAILURE;
        }
        printf("impressions framebuffer fnv1a64=%016" PRIx64 "\n", c2_sdl_title_hash());
        if (advance_startup() == SDL_APP_FAILURE) {
            return SDL_APP_FAILURE;
        }
        printf("startup menu framebuffer fnv1a64=%016" PRIx64 "\n", c2_sdl_title_hash());
        if (!show_startup_stage(C2_STARTUP_SETTINGS)) {
            return SDL_APP_FAILURE;
        }
        printf("game settings framebuffer fnv1a64=%016" PRIx64 "\n", c2_sdl_title_hash());
        return SDL_APP_SUCCESS;
    }

    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppEvent(void *appstate, SDL_Event *event)
{
    struct c2_app_state *state;

    state = appstate;

    if (event->type == SDL_EVENT_QUIT) {
        return SDL_APP_SUCCESS;
    }
    if (event->type == SDL_EVENT_KEY_DOWN && event->key.key == SDLK_ESCAPE) {
        if (state->stage == C2_STARTUP_SETTINGS) {
            return show_startup_stage(C2_STARTUP_MENU) ? SDL_APP_CONTINUE : SDL_APP_FAILURE;
        }
        return SDL_APP_SUCCESS;
    }
    if (state->stage < C2_STARTUP_MENU &&
        (event->type == SDL_EVENT_KEY_DOWN || event->type == SDL_EVENT_MOUSE_BUTTON_DOWN)) {
        return advance_startup();
    }
    if (state->stage == C2_STARTUP_MENU && event->type == SDL_EVENT_KEY_DOWN &&
        (event->key.key == SDLK_RETURN || event->key.key == SDLK_SPACE)) {
        return show_startup_stage(C2_STARTUP_SETTINGS) ? SDL_APP_CONTINUE : SDL_APP_FAILURE;
    }
    if (state->stage == C2_STARTUP_MENU && event->type == SDL_EVENT_MOUSE_BUTTON_DOWN) {
        if (!c2_sdl_event_to_game(event)) {
            return SDL_APP_FAILURE;
        }
        if (event->button.x >= 130 && event->button.x < 440) {
            if (event->button.y >= 170 && event->button.y < 218) {
                return show_startup_stage(C2_STARTUP_SETTINGS) ? SDL_APP_CONTINUE : SDL_APP_FAILURE;
            }
            if (event->button.y >= 314 && event->button.y < 362) {
                return SDL_APP_SUCCESS;
            }
        }
    }
    if (state->stage == C2_STARTUP_SETTINGS && event->type == SDL_EVENT_KEY_DOWN) {
        if (event->key.key == SDLK_LEFT && c2inf.skill_level > 0) {
            c2inf.skill_level--;
            return redraw_settings();
        }
        if (event->key.key == SDLK_RIGHT && c2inf.skill_level < 4) {
            c2inf.skill_level++;
            return redraw_settings();
        }
        if (event->key.key == SDLK_P) {
            c2inf.peace_mode ^= 1;
            return redraw_settings();
        }
    }
    if (state->stage == C2_STARTUP_SETTINGS && event->type == SDL_EVENT_MOUSE_BUTTON_DOWN) {
        if (!c2_sdl_event_to_game(event)) {
            return SDL_APP_FAILURE;
        }
        if (event->button.y >= 145 && event->button.y < 195) {
            if (event->button.x >= 260 && event->button.x < 300 && c2inf.skill_level > 0) {
                c2inf.skill_level--;
                return redraw_settings();
            }
            if (event->button.x >= 300 && event->button.x < 340 && c2inf.skill_level < 4) {
                c2inf.skill_level++;
                return redraw_settings();
            }
        }
        if (event->button.x >= 130 && event->button.x < 440 &&
            event->button.y >= 220 && event->button.y < 275) {
            c2inf.peace_mode ^= 1;
            return redraw_settings();
        }
        if (event->button.x >= 130 && event->button.x < 440 &&
            event->button.y >= 370 && event->button.y < 425) {
            return show_startup_stage(C2_STARTUP_MENU) ? SDL_APP_CONTINUE : SDL_APP_FAILURE;
        }
    }

    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppIterate(void *appstate)
{
    struct c2_app_state *state;

    state = appstate;
    if (state->stage < C2_STARTUP_MENU &&
        SDL_GetTicks() - state->stage_started >= C2_SPLASH_DURATION_MS) {
        if (advance_startup() == SDL_APP_FAILURE) {
            return SDL_APP_FAILURE;
        }
    }

    c2_sdl_platform_present();
    SDL_Delay(16);
    return SDL_APP_CONTINUE;
}

void SDL_AppQuit(void *appstate, SDL_AppResult result)
{
    (void)appstate;
    (void)result;
    c2_sdl_platform_shutdown();
}
