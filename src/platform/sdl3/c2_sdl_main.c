#define SDL_MAIN_USE_CALLBACKS 1
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_sdl_platform.h"

extern int display_pl8file(char *pl8_filename, char *palette_filename);

static int parse_arguments(int argc, char *argv[], const char **data_dir, int *headless)
{
    int i;

    *data_dir = getenv("C2_DATA_DIR");
    if (*data_dir == NULL || **data_dir == '\0') {
        *data_dir = ".";
    }
    *headless = 0;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--headless") == 0) {
            *headless = 1;
        } else if (strcmp(argv[i], "--data-dir") == 0 && i + 1 < argc) {
            i++;
            *data_dir = argv[i];
        } else {
            fprintf(stderr, "usage: %s [--headless] [--data-dir PATH]\n", argv[0]);
            return 0;
        }
    }

    return 1;
}

SDL_AppResult SDL_AppInit(void **appstate, int argc, char *argv[])
{
    const char *data_dir;
    int headless;

    *appstate = NULL;
    if (!parse_arguments(argc, argv, &data_dir, &headless)) {
        return SDL_APP_FAILURE;
    }
    if (!c2_sdl_platform_init(data_dir, headless)) {
        return SDL_APP_FAILURE;
    }

    if (!display_pl8file("logo1.pl8", "logo1.256")) {
        fprintf(stderr, "could not load the Caesar II title assets from %s\n", data_dir);
        return SDL_APP_FAILURE;
    }

    printf("title framebuffer fnv1a64=%016" PRIx64 "\n", c2_sdl_title_hash());
    if (headless) {
        return SDL_APP_SUCCESS;
    }

    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppEvent(void *appstate, SDL_Event *event)
{
    (void)appstate;

    if (event->type == SDL_EVENT_QUIT) {
        return SDL_APP_SUCCESS;
    }
    if (event->type == SDL_EVENT_KEY_DOWN && event->key.key == SDLK_ESCAPE) {
        return SDL_APP_SUCCESS;
    }

    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppIterate(void *appstate)
{
    (void)appstate;
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
