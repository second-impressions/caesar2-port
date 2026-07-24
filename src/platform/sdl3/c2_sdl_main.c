#define SDL_MAIN_USE_CALLBACKS 1
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_host.h"
#include "c2_port.h"
#include "c2_port_app.h"
#if C2_FEAT_DEBUG_CRASH_HANDLER
#include "c2_debug_crash.h"
#endif
#include "c2_sdl_host.h"
#if C2_FEAT_DEBUG_OBSERVATION
#include "c2_sdl_smoke.h"
#endif

struct c2_sdl_app {
    SDL_Thread *engine_thread;
    SDL_AtomicInt engine_result;
    struct c2_port_app_config engine_config;
    char *default_user_data_root;
#if C2_FEAT_DEBUG_OBSERVATION
    struct c2_sdl_smoke smoke;
    int smoke_failed;
#endif
    int host_initialized;
};

static struct c2_sdl_app c2_app;

static int parse_arguments(int argc, char *argv[], const char **asset_root,
                           const char **user_data_root,
                           char **default_user_data_root,
                           const char **screenshot_filename,
                           int *headless, int *mouse_lock, int *smoke_kind)
{
    int i;

    *asset_root = getenv("C2_ASSET_ROOT");
    if (*asset_root == NULL || **asset_root == '\0') {
        *asset_root = ".";
    }
    *user_data_root = getenv("C2_USER_DATA_DIR");
    if (*user_data_root == NULL || **user_data_root == '\0') {
        *user_data_root = NULL;
    }
    *default_user_data_root = NULL;
    *headless = 0;
    *mouse_lock = 0;
    *smoke_kind = 0;
    *screenshot_filename = NULL;

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--headless") == 0) {
            *headless = 1;
        } else if (strcmp(argv[i], "--mouse-lock") == 0) {
            *mouse_lock = 1;
        } else if (strcmp(argv[i], "--no-mouse-lock") == 0) {
            *mouse_lock = 0;
#if C2_FEAT_DEBUG_OBSERVATION
        } else if (strcmp(argv[i], "--smoke-test") == 0) {
            *headless = 1;
            *smoke_kind = C2_SDL_SMOKE_PROVINCE_SELECTION;
        } else if (strcmp(argv[i], "--city-smoke-test") == 0) {
            *headless = 1;
            *smoke_kind = C2_SDL_SMOKE_CITY_LOOP;
        } else if (strcmp(argv[i], "--tutorial-smoke-test") == 0) {
            *headless = 1;
            *smoke_kind = C2_SDL_SMOKE_TUTORIAL;
        } else if (strcmp(argv[i], "--save-load-smoke-test") == 0) {
            *headless = 1;
            *smoke_kind = C2_SDL_SMOKE_SAVE_LOAD;
        } else if (strcmp(argv[i], "--music-buffer-smoke-test") == 0) {
            *headless = 1;
            *smoke_kind = C2_SDL_SMOKE_MUSIC_BUFFER;
#endif
        } else if (strcmp(argv[i], "--asset-root") == 0 && i + 1 < argc) {
            *asset_root = argv[++i];
        } else if (strcmp(argv[i], "--user-data-dir") == 0 && i + 1 < argc) {
            *user_data_root = argv[++i];
        } else if (strcmp(argv[i], "--screenshot") == 0 && i + 1 < argc) {
            *screenshot_filename = argv[++i];
        } else {
#if C2_FEAT_DEBUG_OBSERVATION
            fprintf(stderr,
                    "usage: %s [--headless] [--asset-root PATH] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--mouse-lock|--no-mouse-lock] "
                    "[--smoke-test|--city-smoke-test|"
                    "--tutorial-smoke-test|--save-load-smoke-test|"
                    "--music-buffer-smoke-test]\n",
                    argv[0]);
#else
            fprintf(stderr,
                    "usage: %s [--headless] [--asset-root PATH] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--mouse-lock|--no-mouse-lock]\n",
                    argv[0]);
#endif
            return 0;
        }
    }
    if (*user_data_root == NULL) {
        *default_user_data_root =
            SDL_GetPrefPath("second-impressions", "caesar2");
        if (*default_user_data_root == NULL) {
            fprintf(stderr, "could not select a user-data directory: %s\n",
                    SDL_GetError());
            return 0;
        }
        *user_data_root = *default_user_data_root;
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
    int mouse_lock;
    int smoke_kind;

    *appstate = &c2_app;
#if C2_FEAT_DEBUG_CRASH_HANDLER
    if (!c2_debug_install_crash_handlers()) {
        fprintf(stderr, "warning: could not install debug crash handlers\n");
    }
#endif
    if (!parse_arguments(argc, argv, &asset_root, &user_data_root,
                         &c2_app.default_user_data_root,
                         &screenshot_filename, &headless, &mouse_lock,
                         &smoke_kind)) {
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
    host_config.mouse_lock = mouse_lock;
#if C2_FEAT_DEBUG_OBSERVATION
    host_config.enable_observation = smoke_kind != C2_SDL_SMOKE_NONE;
#endif
    if (!c2_host_init(&host_config)) {
        SDL_free(c2_app.default_user_data_root);
        c2_app.default_user_data_root = NULL;
        return SDL_APP_FAILURE;
    }
    c2_app.host_initialized = 1;

    c2_app.engine_config.screenshot_filename = screenshot_filename;
#if C2_FEAT_DEBUG_OBSERVATION
    c2_sdl_smoke_init(&c2_app.smoke, smoke_kind, SDL_GetTicks());
#else
    (void)smoke_kind;
#endif
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
#if C2_FEAT_DEBUG_OBSERVATION
    if (app->smoke.kind != C2_SDL_SMOKE_NONE) {
        enum c2_sdl_smoke_result smoke_result;

        smoke_result = c2_sdl_smoke_iterate(&app->smoke, SDL_GetTicks());
        if (smoke_result != C2_SDL_SMOKE_RUNNING) {
            app->smoke_failed = smoke_result == C2_SDL_SMOKE_FAILURE;
            app->smoke.kind = C2_SDL_SMOKE_NONE;
            c2_host_request_shutdown();
        }
    }
#endif
    result = SDL_GetAtomicInt(&app->engine_result);
    if (result != C2_PORT_APP_CONTINUE) {
#if C2_FEAT_DEBUG_OBSERVATION
        if (app->smoke_failed) return SDL_APP_FAILURE;
#endif
        return to_sdl_result(result);
    }
    c2_host_present();
#if !PLATFORM_WASM
    c2_host_sleep_ms(8);
#endif
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
    if (app != NULL) {
        SDL_free(app->default_user_data_root);
        app->default_user_data_root = NULL;
    }
}
