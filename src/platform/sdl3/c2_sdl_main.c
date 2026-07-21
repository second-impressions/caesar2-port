#define SDL_MAIN_USE_CALLBACKS 1
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_host.h"
#include "c2_port.h"
#include "c2_port_app.h"
#include "c2_sdl_host.h"

struct c2_sdl_app {
    SDL_Thread *engine_thread;
    SDL_AtomicInt engine_result;
    struct c2_port_app_config engine_config;
    Uint64 headless_started;
    int smoke_test;
    int host_initialized;
};

static struct c2_sdl_app c2_app;

static int parse_arguments(int argc, char *argv[], const char **asset_root,
                           const char **user_data_root,
                           const char **screenshot_filename, int *headless,
                           int *smoke_test)
{
    int i;

    *asset_root = getenv("C2_DATA_DIR");
    if (*asset_root == NULL || **asset_root == '\0') {
        *asset_root = ".";
    }
    *user_data_root = getenv("C2_USER_DATA_DIR");
    if (*user_data_root == NULL || **user_data_root == '\0') {
        *user_data_root = ".";
    }
    *headless = 0;
    *smoke_test = 0;
    *screenshot_filename = NULL;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--headless") == 0) {
            *headless = 1;
        } else if (strcmp(argv[i], "--smoke-test") == 0) {
            *headless = 1;
            *smoke_test = 1;
        } else if (strcmp(argv[i], "--data-dir") == 0 && i + 1 < argc) {
            *asset_root = argv[++i];
        } else if (strcmp(argv[i], "--user-data-dir") == 0 && i + 1 < argc) {
            *user_data_root = argv[++i];
        } else if (strcmp(argv[i], "--screenshot") == 0 && i + 1 < argc) {
            *screenshot_filename = argv[++i];
        } else {
            fprintf(stderr,
                    "usage: %s [--headless] [--data-dir PATH] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--smoke-test]\n",
                    argv[0]);
            return 0;
        }
    }
    return 1;
}

static int engine_main(void *data)
{
    struct c2_sdl_app *app;
    enum c2_port_app_result result;

    app = data;
    result = c2_port_app_run(&app->engine_config);
    SDL_SetAtomicInt(&app->engine_result, result);
    return (int)result;
}

static SDL_AppResult to_sdl_result(int result)
{
    if (result == C2_PORT_APP_SUCCESS) {
        return SDL_APP_SUCCESS;
    }
    if (result == C2_PORT_APP_FAILURE) {
        return SDL_APP_FAILURE;
    }
    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppInit(void **appstate, int argc, char *argv[])
{
    const char *asset_root;
    const char *user_data_root;
    const char *screenshot_filename;
    struct c2_host_config host_config;
    int headless;
    int smoke_test;

    *appstate = &c2_app;
    if (!parse_arguments(argc, argv, &asset_root, &user_data_root,
                         &screenshot_filename, &headless, &smoke_test)) {
        return SDL_APP_FAILURE;
    }

    memset(&host_config, 0, sizeof(host_config));
    host_config.title = "Caesar II";
    host_config.asset_root = asset_root;
    host_config.user_data_root = user_data_root;
    host_config.logical_width = C2_SCREEN_WIDTH;
    host_config.logical_height = C2_SCREEN_HEIGHT;
    host_config.window_scale = 2;
    host_config.headless = headless;
    if (!c2_host_init(&host_config)) {
        return SDL_APP_FAILURE;
    }
    c2_app.host_initialized = 1;

    c2_app.engine_config.screenshot_filename = screenshot_filename;
    c2_app.engine_config.headless = headless;
    c2_app.engine_config.smoke_test = smoke_test;
    c2_app.smoke_test = smoke_test;
    c2_app.headless_started = SDL_GetTicks();
    SDL_SetAtomicInt(&c2_app.engine_result, C2_PORT_APP_CONTINUE);
    c2_app.engine_thread = SDL_CreateThread(engine_main, "caesar2-engine", &c2_app);
    if (c2_app.engine_thread == NULL) {
        fprintf(stderr, "could not start the Caesar II engine: %s\n", SDL_GetError());
        return SDL_APP_FAILURE;
    }
    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppEvent(void *appstate, SDL_Event *event)
{
    (void)appstate;
    c2_sdl_host_handle_event(event);
    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppIterate(void *appstate)
{
    struct c2_sdl_app *app;
    int result;

    app = appstate;
    if (app->smoke_test) {
        Uint64 elapsed;
        unsigned int buttons;
        int x;
        int y;

        elapsed = SDL_GetTicks() - app->headless_started;
        buttons = 0;
        x = 10;
        y = 10;
        if (elapsed < 4000) {
            if ((elapsed / 250) % 2 == 0) {
                buttons = C2_HOST_MOUSE_LEFT;
            }
        } else if (elapsed < 6000) {
            x = 410;
            y = 195;
            if ((elapsed / 250) % 2 == 0) {
                buttons = C2_HOST_MOUSE_LEFT;
            }
        } else if (elapsed < 6100) {
            x = 280;
            y = 250;
            buttons = C2_HOST_MOUSE_LEFT;
        } else if (elapsed >= 6500 && elapsed < 6600) {
            x = 280;
            y = 345;
            buttons = C2_HOST_MOUSE_LEFT;
        } else if (elapsed >= 7200 && elapsed < 7300) {
            buttons = C2_HOST_MOUSE_RIGHT;
        }
        c2_sdl_host_set_headless_mouse(x, y, buttons);
        if (elapsed >= 9000) {
            c2_host_request_shutdown();
        }
    }
    result = SDL_GetAtomicInt(&app->engine_result);
    if (result != C2_PORT_APP_CONTINUE) {
        return to_sdl_result(result);
    }
    c2_host_present();
    c2_host_sleep_ms(8);
    return SDL_APP_CONTINUE;
}

void SDL_AppQuit(void *appstate, SDL_AppResult result)
{
    struct c2_sdl_app *app;

    (void)result;
    app = appstate;
    if (app != NULL && app->host_initialized) {
        c2_host_request_shutdown();
    }
    if (app != NULL && app->engine_thread != NULL) {
        SDL_WaitThread(app->engine_thread, NULL);
        app->engine_thread = NULL;
    }
    if (app != NULL && app->host_initialized) {
        c2_host_shutdown();
        app->host_initialized = 0;
    }
}
