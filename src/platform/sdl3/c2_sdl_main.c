#define SDL_MAIN_USE_CALLBACKS 1
#include <SDL3/SDL.h>
#include <SDL3/SDL_main.h>

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#if PORT_PLATFORM_WASM
#include <emscripten/wasmfs.h>
#endif

#include "c2_host.h"
#include "c2_import.h"
#include "c2_port.h"
#include "c2_port_app.h"
#if PORT_FEAT_DEBUG_CRASH_HANDLER
#include "c2_debug_crash.h"
#endif
#include "c2_sdl_host.h"
#if PORT_FEAT_DEBUG_OBSERVATION
#include "c2_sdl_smoke.h"
#endif

#if PORT_PLATFORM_WASM
extern void c2_browser_show_restart(void);
extern void c2_browser_source_ready(const char *resolved,
                                    const char *original);
#endif

#define C2_HOST_ACTIVE_CALLBACK_RATE "120"
#define C2_HOST_IDLE_CALLBACK_RATE "15"

struct c2_sdl_app {
    SDL_Thread *engine_thread;
#if PORT_PLATFORM_WASM
    SDL_Thread *storage_thread;
    SDL_AtomicInt storage_result;
#endif
    SDL_AtomicInt engine_result;
    struct c2_port_app_config engine_config;
    char *default_user_data_root;
#if PORT_FEAT_DEBUG_OBSERVATION
    struct c2_sdl_smoke smoke;
    int smoke_failed;
#endif
    char asset_source[4096];
    char user_data_root[4096];
    char screenshot_filename[4096];
    char asset_profile[128];
    int headless;
    int mouse_lock;
    int smoke_kind;
    int host_initialized;
    int host_interactive;
};

static struct c2_sdl_app c2_app;

static int parse_arguments(int argc, char *argv[], const char **asset_root,
                           const char **user_data_root,
                           char **default_user_data_root,
                           const char **screenshot_filename,
                           const char **asset_profile,
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
    *asset_profile = getenv("C2_ASSET_PROFILE");

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--headless") == 0) {
            *headless = 1;
        } else if (strcmp(argv[i], "--mouse-lock") == 0) {
            *mouse_lock = 1;
        } else if (strcmp(argv[i], "--no-mouse-lock") == 0) {
            *mouse_lock = 0;
#if PORT_FEAT_DEBUG_OBSERVATION
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
        } else if (strcmp(argv[i],
                          "--campania-transition-smoke-test") == 0) {
            *headless = 1;
            *smoke_kind = C2_SDL_SMOKE_CAMPANIA_TRANSITION;
#endif
        } else if ((strcmp(argv[i], "--asset-root") == 0 ||
                    strcmp(argv[i], "--game-data") == 0) && i + 1 < argc) {
            *asset_root = argv[++i];
        } else if (strcmp(argv[i], "--user-data-dir") == 0 && i + 1 < argc) {
            *user_data_root = argv[++i];
        } else if (strcmp(argv[i], "--asset-profile") == 0 && i + 1 < argc) {
            *asset_profile = argv[++i];
        } else if (strcmp(argv[i], "--screenshot") == 0 && i + 1 < argc) {
            *screenshot_filename = argv[++i];
        } else if (argv[i][0] != '-') {
            *asset_root = argv[i];
        } else {
#if PORT_FEAT_DEBUG_OBSERVATION
            fprintf(stderr,
                    "usage: %s [--headless] [--game-data SOURCE] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--mouse-lock|--no-mouse-lock] "
                    "[--smoke-test|--city-smoke-test|"
                    "--tutorial-smoke-test|--save-load-smoke-test|"
                    "--music-buffer-smoke-test|"
                    "--campania-transition-smoke-test]\n",
                    argv[0]);
#else
            fprintf(stderr,
                    "usage: %s [--headless] [--game-data SOURCE] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--mouse-lock|--no-mouse-lock]\n",
                    argv[0]);
#endif
            return 0;
        }
    }
    if (*user_data_root == NULL) {
#if PORT_PLATFORM_WASM
        *user_data_root = "/persistent/user-data";
#else
        *default_user_data_root =
            SDL_GetPrefPath("second-impressions", "caesar2");
        if (*default_user_data_root == NULL) {
            fprintf(stderr, "could not select a user-data directory: %s\n",
                    SDL_GetError());
            return 0;
        }
        *user_data_root = *default_user_data_root;
#endif
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
    if (result == PORT_APP_SUCCESS) {
        return SDL_APP_SUCCESS;
    }
    if (result == PORT_APP_FAILURE) {
        return SDL_APP_FAILURE;
    }
    return SDL_APP_CONTINUE;
}

static void update_host_callback_rate(struct c2_sdl_app *app)
{
    int interactive;
    const char *rate;

    interactive = c2_sdl_host_is_interactive();
    if (interactive == app->host_interactive) return;
    rate = interactive ? C2_HOST_ACTIVE_CALLBACK_RATE :
                         C2_HOST_IDLE_CALLBACK_RATE;
    if (!SDL_SetHint(SDL_HINT_MAIN_CALLBACK_RATE, rate)) {
        fprintf(stderr, "warning: could not set SDL callback rate to %s Hz\n",
                rate);
    }
    app->host_interactive = interactive;
}

#if !PORT_PLATFORM_WASM
static int load_saved_asset_source(const char *user_root, char *source, size_t capacity)
{
    char path[4096];
    FILE *file;
    size_t length;
    if (snprintf(path, sizeof(path), "%s/asset-source.txt", user_root) >= (int)sizeof(path)) return 0;
    file = fopen(path, "rb");
    if (!file) return 0;
    if (!fgets(source, (int)capacity, file)) { fclose(file); return 0; }
    fclose(file);
    length = strlen(source);
    while (length && (source[length - 1] == '\n' || source[length - 1] == '\r')) source[--length] = '\0';
    return length != 0;
}

static void save_asset_source(const struct c2_sdl_app *app)
{
    char path[4096];
    FILE *file;
    if (snprintf(path, sizeof(path), "%s/asset-source.txt", app->user_data_root) >= (int)sizeof(path)) return;
    file = fopen(path, "wb");
    if (!file) return;
    fprintf(file, "%s\n", app->asset_source);
    fclose(file);
}
#endif

static int start_runtime(struct c2_sdl_app *app)
{
    char resolved_asset_root[4096];
    char import_error[512];
    struct c2_host_config host_config;
    const char *cache_root;

#if PORT_PLATFORM_WASM
    cache_root = "/persistent";
#else
    cache_root = app->user_data_root;
#endif
    if (!c2_import_path(app->asset_source, cache_root,
                        app->asset_profile[0] ? app->asset_profile : NULL,
                        resolved_asset_root, sizeof(resolved_asset_root),
                        import_error, sizeof(import_error))) {
        fprintf(stderr, "could not import game data '%s': %s\n",
                app->asset_source, import_error);
        return 0;
    }
#if PORT_PLATFORM_WASM
    c2_browser_source_ready(resolved_asset_root, app->asset_source);
#endif
    memset(&host_config, 0, sizeof(host_config));
    host_config.title = "Caesar II";
    host_config.asset_root = resolved_asset_root;
    host_config.user_data_root = app->user_data_root;
    host_config.logical_width = C2_SCREEN_WIDTH;
    host_config.logical_height = C2_SCREEN_HEIGHT;
    host_config.window_scale = 2;
    host_config.headless = app->headless;
    host_config.mouse_lock = app->mouse_lock;
#if PORT_FEAT_DEBUG_OBSERVATION
    host_config.enable_observation = app->smoke_kind != C2_SDL_SMOKE_NONE;
#endif
    if (!c2_host_init(&host_config)) return 0;
    if (c2_host_asset_size("C2.ENG") == 0 ||
        c2_host_asset_size("HELP.ENG") == 0) {
        fprintf(stderr, "selected game data is missing C2.ENG or HELP.ENG\n");
        c2_host_shutdown();
        return 0;
    }
#if !PORT_PLATFORM_WASM
    save_asset_source(app);
#endif
    app->host_initialized = 1;
    update_host_callback_rate(app);
    app->engine_config.screenshot_filename = app->screenshot_filename[0]
        ? app->screenshot_filename : NULL;
#if PORT_FEAT_DEBUG_OBSERVATION
    c2_sdl_smoke_init(&app->smoke, app->smoke_kind, SDL_GetTicks());
#endif
    SDL_SetAtomicInt(&app->engine_result, PORT_APP_CONTINUE);
    app->engine_thread = SDL_CreateThread(engine_main, "caesar2-engine", app);
    if (app->engine_thread == NULL) {
        fprintf(stderr, "could not start the Caesar II engine: %s\n", SDL_GetError());
        return 0;
    }
    return 1;
}

#if !PORT_PLATFORM_WASM
struct source_dialog {
    SDL_Mutex *mutex;
    SDL_Condition *condition;
    char path[4096];
    int closed;
};

static void SDLCALL source_dialog_closed(void *userdata,
                                          const char *const *filelist,
                                          int filter)
{
    struct source_dialog *dialog = userdata;
    (void)filter;
    SDL_LockMutex(dialog->mutex);
    if (filelist && filelist[0]) {
        snprintf(dialog->path, sizeof(dialog->path), "%s", filelist[0]);
    }
    dialog->closed = 1;
    SDL_SignalCondition(dialog->condition);
    SDL_UnlockMutex(dialog->mutex);
}

static int choose_installation_folder(char *path, size_t capacity)
{
    struct source_dialog dialog;
    memset(&dialog, 0, sizeof(dialog));
    if (!SDL_Init(SDL_INIT_EVENTS)) return 0;
    dialog.mutex = SDL_CreateMutex();
    dialog.condition = SDL_CreateCondition();
    if (!dialog.mutex || !dialog.condition) goto done;
    SDL_LockMutex(dialog.mutex);
    SDL_ShowOpenFolderDialog(source_dialog_closed, &dialog, NULL, NULL, false);
    while (!dialog.closed) {
        SDL_WaitConditionTimeout(dialog.condition, dialog.mutex, 30);
        SDL_PumpEvents();
    }
    SDL_UnlockMutex(dialog.mutex);
    if (dialog.path[0] && strlen(dialog.path) < capacity) strcpy(path, dialog.path);

done:
    SDL_DestroyCondition(dialog.condition);
    SDL_DestroyMutex(dialog.mutex);
    SDL_Quit();
    return path[0] != '\0';
}
#endif

#if PORT_PLATFORM_WASM
static int storage_main(void *unused)
{
    backend_t backend;
    (void)unused;
    backend = wasmfs_create_opfs_backend();
    if (backend == NULL ||
        (wasmfs_create_directory("/persistent", 0777, backend) != 0 &&
         errno != EEXIST) ||
        (mkdir("/persistent/user-data", 0777) != 0 && errno != EEXIST) ||
        (mkdir("/persistent/game-data", 0777) != 0 && errno != EEXIST) ||
        (mkdir("/persistent/incoming", 0777) != 0 && errno != EEXIST)) {
        SDL_SetAtomicInt(&c2_app.storage_result, -1);
        return -1;
    }
    SDL_SetAtomicInt(&c2_app.storage_result, 1);
    return 0;
}
#endif

SDL_AppResult SDL_AppInit(void **appstate, int argc, char *argv[])
{
    const char *asset_root;
    const char *user_data_root;
    const char *screenshot_filename;
    const char *asset_profile;
    int headless;
    int mouse_lock;
    int smoke_kind;

    *appstate = &c2_app;
    /*
     * Keep input and the frame mailbox responsive while the user is
     * interacting. This rate is reduced after host initialization when the
     * window is not active.
     */
    SDL_SetHint(SDL_HINT_MAIN_CALLBACK_RATE, C2_HOST_ACTIVE_CALLBACK_RATE);
    c2_app.host_interactive = -1;
#if PORT_FEAT_DEBUG_CRASH_HANDLER
    if (!c2_debug_install_crash_handlers()) {
        fprintf(stderr, "warning: could not install debug crash handlers\n");
    }
#endif
    if (!parse_arguments(argc, argv, &asset_root, &user_data_root,
                         &c2_app.default_user_data_root,
                         &screenshot_filename, &asset_profile,
                         &headless, &mouse_lock,
                         &smoke_kind)) {
        return SDL_APP_FAILURE;
    }

    snprintf(c2_app.user_data_root, sizeof(c2_app.user_data_root), "%s", user_data_root);
#if !PORT_PLATFORM_WASM
    if (strcmp(asset_root, ".") == 0 &&
        load_saved_asset_source(user_data_root, c2_app.asset_source,
                                sizeof(c2_app.asset_source))) {
        asset_root = c2_app.asset_source;
    }
#endif
    if (asset_root != c2_app.asset_source) {
        snprintf(c2_app.asset_source, sizeof(c2_app.asset_source), "%s", asset_root);
    }
    if (screenshot_filename) {
        snprintf(c2_app.screenshot_filename, sizeof(c2_app.screenshot_filename), "%s", screenshot_filename);
    } else {
        c2_app.screenshot_filename[0] = '\0';
    }
    if (asset_profile && *asset_profile) {
        snprintf(c2_app.asset_profile, sizeof(c2_app.asset_profile), "%s", asset_profile);
    } else {
        c2_app.asset_profile[0] = '\0';
    }
    c2_app.headless = headless;
    c2_app.mouse_lock = mouse_lock;
    c2_app.smoke_kind = smoke_kind;
#if PORT_PLATFORM_WASM
    SDL_SetAtomicInt(&c2_app.storage_result, 0);
    c2_app.storage_thread = SDL_CreateThread(storage_main, "caesar2-storage", NULL);
    if (c2_app.storage_thread == NULL) return SDL_APP_FAILURE;
    return SDL_APP_CONTINUE;
#else
    if (!start_runtime(&c2_app)) {
        fprintf(stderr, "Select an installed Caesar II folder, or restart with --game-data ZIP/ISO/CUE.\n");
        c2_app.asset_source[0] = '\0';
        if (!choose_installation_folder(c2_app.asset_source,
                                        sizeof(c2_app.asset_source)) ||
            !start_runtime(&c2_app)) {
            SDL_free(c2_app.default_user_data_root);
            c2_app.default_user_data_root = NULL;
            return SDL_APP_FAILURE;
        }
    }
    return SDL_APP_CONTINUE;
#endif
}

SDL_AppResult SDL_AppEvent(void *appstate, SDL_Event *event)
{
    struct c2_sdl_app *app;

    app = appstate;
    if (!app->host_initialized) return SDL_APP_CONTINUE;
    c2_sdl_host_handle_event(event);
    update_host_callback_rate(app);
    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppIterate(void *appstate)
{
    struct c2_sdl_app *app;
    int result;

    app = appstate;
#if PORT_PLATFORM_WASM
    if (!app->host_initialized) {
        int storage_result = SDL_GetAtomicInt(&app->storage_result);
        if (storage_result == 0) return SDL_APP_CONTINUE;
        if (app->storage_thread != NULL) {
            SDL_WaitThread(app->storage_thread, NULL);
            app->storage_thread = NULL;
        }
        if (storage_result < 0 || !start_runtime(app)) return SDL_APP_FAILURE;
        return SDL_APP_CONTINUE;
    }
#endif
#if PORT_FEAT_DEBUG_OBSERVATION
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
    if (result != PORT_APP_CONTINUE) {
#if PORT_FEAT_DEBUG_OBSERVATION
        if (app->smoke_failed) return SDL_APP_FAILURE;
#endif
#if PORT_PLATFORM_WASM
        if (to_sdl_result(result) == SDL_APP_SUCCESS) {
            c2_browser_show_restart();
        }
#endif
        return to_sdl_result(result);
    }
    c2_host_present();
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
#if PORT_PLATFORM_WASM
    if (app != NULL && app->storage_thread != NULL) {
        SDL_WaitThread(app->storage_thread, NULL);
        app->storage_thread = NULL;
    }
#endif
    if (app != NULL && app->host_initialized) {
        c2_host_shutdown();
        app->host_initialized = 0;
    }
    if (app != NULL) {
        SDL_free(app->default_user_data_root);
        app->default_user_data_root = NULL;
    }
}
