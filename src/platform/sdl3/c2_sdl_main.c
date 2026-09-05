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
#include "c2_setup_ui.h"
#include "c2_version.h"
#if PORT_FEAT_DEBUG_OBSERVATION
#include "c2_sdl_smoke.h"
#endif

#if PORT_PLATFORM_WASM
#include <emscripten.h>
extern void c2_browser_show_restart(void);
/*
 * Browser chrome pauses the game while its own dialogs are in front of it.
 * The request only crosses the host boundary here; the engine applies it with
 * its own pause action.
 */
EMSCRIPTEN_KEEPALIVE void c2_browser_set_pause(int paused)
{
    c2_host_request_pause(paused);
}

EMSCRIPTEN_KEEPALIVE void c2_browser_set_fractional_scaling(int enabled)
{
    c2_host_set_fractional_scaling(enabled);
}

EMSCRIPTEN_KEEPALIVE void c2_browser_set_canvas_size(int width, int height)
{
    c2_host_set_canvas_size(width, height);
}

extern void c2_browser_source_ready(const char *resolved,
                                    const char *original);
extern void c2_browser_import_progress(const char *phase,
                                       unsigned int completed_kib,
                                       unsigned int total_kib,
                                       int completed_files,
                                       int total_files);
extern void c2_browser_import_error(const char *message);
#endif

#define C2_HOST_ACTIVE_CALLBACK_RATE "120"
#define C2_HOST_IDLE_CALLBACK_RATE "15"

struct c2_sdl_app {
    SDL_Thread *engine_thread;
#if PORT_PLATFORM_WASM
    SDL_Thread *storage_thread;
    SDL_Thread *prepare_thread;
    SDL_AtomicInt storage_result;
    SDL_AtomicInt prepare_result;
    int pointer_watch_installed;
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
    int fractional_scaling;
    int fullscreen;
    int smoke_kind;
    int prepare_only;
    int skip_launcher;
    int launcher_active;
    int host_initialized;
    int host_interactive;
    char last_error[512];
};

static struct c2_sdl_app c2_app;

#if PORT_PLATFORM_WASM
static int is_pointer_event(Uint32 type)
{
    return type == SDL_EVENT_MOUSE_MOTION ||
           type == SDL_EVENT_MOUSE_BUTTON_DOWN ||
           type == SDL_EVENT_MOUSE_BUTTON_UP ||
           type == SDL_EVENT_MOUSE_WHEEL;
}

/*
 * SDL event watches run when an event is added, before SDL_AppEvent drains the
 * queue. Browser pointer input therefore reaches the shared host snapshot as
 * it is pushed instead of waiting for the next fixed-rate main callback.
 */
static bool SDLCALL push_pointer_event(void *userdata, SDL_Event *event)
{
    (void)userdata;
    if (is_pointer_event(event->type)) c2_sdl_host_handle_event(event);
    return true;
}
#endif

static int parse_arguments(int argc, char *argv[], const char **asset_root,
                           const char **user_data_root,
                           char **default_user_data_root,
                           const char **screenshot_filename,
                           const char **asset_profile,
                           int *headless, int *mouse_lock,
                           int *fractional_scaling, int *smoke_kind,
                           int *prepare_only, int *skip_launcher,
                           int *explicit_source, int *fullscreen)
{
    int i;

    *asset_root = getenv("C2_ASSET_ROOT");
    *explicit_source = *asset_root != NULL && **asset_root != '\0';
    if (!*explicit_source) {
        *asset_root = ".";
    }
    *skip_launcher = 0;
    *user_data_root = getenv("C2_USER_DATA_DIR");
    if (*user_data_root == NULL || **user_data_root == '\0') {
        *user_data_root = NULL;
    }
    *default_user_data_root = NULL;
    *headless = 0;
    *mouse_lock = 0;
    *fractional_scaling = -1; /* -1: use the saved launcher setting */
    *fullscreen = -1;
    *smoke_kind = 0;
    *prepare_only = 0;
    *screenshot_filename = NULL;
    *asset_profile = getenv("C2_ASSET_PROFILE");

    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--headless") == 0) {
            *headless = 1;
        } else if (strcmp(argv[i], "--mouse-lock") == 0) {
            *mouse_lock = 1;
        } else if (strcmp(argv[i], "--no-mouse-lock") == 0) {
            *mouse_lock = 0;
        } else if (strcmp(argv[i], "--prepare-assets") == 0) {
            *prepare_only = 1;
        } else if (strcmp(argv[i], "--skip-launcher") == 0) {
            *skip_launcher = 1;
        } else if (strcmp(argv[i], "--fractional-scaling") == 0) {
            *fractional_scaling = 1;
        } else if (strcmp(argv[i], "--fullscreen") == 0) {
            *fullscreen = 1;
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
            *explicit_source = 1;
        } else if (strcmp(argv[i], "--user-data-dir") == 0 && i + 1 < argc) {
            *user_data_root = argv[++i];
        } else if (strcmp(argv[i], "--asset-profile") == 0 && i + 1 < argc) {
            *asset_profile = argv[++i];
        } else if (strcmp(argv[i], "--screenshot") == 0 && i + 1 < argc) {
            *screenshot_filename = argv[++i];
        } else if (argv[i][0] != '-') {
            *asset_root = argv[i];
            *explicit_source = 1;
        } else {
#if PORT_FEAT_DEBUG_OBSERVATION
            fprintf(stderr,
                    "usage: %s [--headless] [--game-data SOURCE] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--mouse-lock|--no-mouse-lock] [--prepare-assets] "
                    "[--skip-launcher] [--fullscreen] [--fractional-scaling] "
                    "[--smoke-test|--city-smoke-test|"
                    "--tutorial-smoke-test|--save-load-smoke-test|"
                    "--music-buffer-smoke-test|"
                    "--campania-transition-smoke-test]\n",
                    argv[0]);
#else
            fprintf(stderr,
                    "usage: %s [--headless] [--game-data SOURCE] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--mouse-lock|--no-mouse-lock] [--prepare-assets] "
                    "[--skip-launcher] [--fullscreen] [--fractional-scaling]\n",
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
static void chomp(char *text)
{
    size_t length = strlen(text);
    while (length && (text[length - 1] == '\n' || text[length - 1] == '\r')) text[--length] = '\0';
}

/* asset-source.txt: line 1 the source, optional line 2 the pack profile. */
static int load_saved_asset_source(const char *user_root, char *source, size_t capacity,
                                   char *profile, size_t profile_capacity)
{
    char path[4096];
    FILE *file;
    if (snprintf(path, sizeof(path), "%s/asset-source.txt", user_root) >= (int)sizeof(path)) return 0;
    file = fopen(path, "rb");
    if (!file) return 0;
    if (!fgets(source, (int)capacity, file)) { fclose(file); return 0; }
    chomp(source);
    if (profile && profile_capacity && !profile[0]) {
        if (fgets(profile, (int)profile_capacity, file)) chomp(profile);
        else profile[0] = '\0';
    }
    fclose(file);
    return source[0] != '\0';
}

/* launcher.ini: the display choices the launcher offers. Missing keys keep
 * the defaults (windowed, integer scaling). */
static void load_display_settings(const char *user_root, int *fullscreen,
                                  int *fractional_scaling)
{
    char path[4096];
    char line[256];
    FILE *file;
    if (snprintf(path, sizeof(path), "%s/launcher.ini", user_root) >= (int)sizeof(path)) return;
    file = fopen(path, "rb");
    if (!file) return;
    while (fgets(line, sizeof(line), file)) {
        chomp(line);
        if (strcmp(line, "fullscreen=1") == 0) *fullscreen = 1;
        else if (strcmp(line, "fullscreen=0") == 0) *fullscreen = 0;
        else if (strcmp(line, "scaling=fractional") == 0) *fractional_scaling = 1;
        else if (strcmp(line, "scaling=integer") == 0) *fractional_scaling = 0;
    }
    fclose(file);
}

static void save_display_settings(const struct c2_sdl_app *app)
{
    char path[4096];
    FILE *file;
    if (snprintf(path, sizeof(path), "%s/launcher.ini", app->user_data_root) >= (int)sizeof(path)) return;
    SDL_CreateDirectory(app->user_data_root);
    file = fopen(path, "wb");
    if (!file) return;
    fprintf(file, "fullscreen=%d\nscaling=%s\n", app->fullscreen ? 1 : 0,
            app->fractional_scaling ? "fractional" : "integer");
    fclose(file);
}

static void save_asset_source(const struct c2_sdl_app *app)
{
    char path[4096];
    FILE *file;
    if (snprintf(path, sizeof(path), "%s/asset-source.txt", app->user_data_root) >= (int)sizeof(path)) return;
    file = fopen(path, "wb");
    if (!file) return;
    fprintf(file, "%s\n%s\n", app->asset_source, app->asset_profile);
    fclose(file);
}
#endif

/*
 * Import and cache the selected game data without starting the engine so the
 * shell can validate an upload and return to its main window.
 */
#if PORT_PLATFORM_WASM
struct c2_browser_progress_state {
    uint64_t last_bytes;
    size_t last_files;
    int reported;
};

static void publish_import_progress(void *userdata, const char *phase,
                                    uint64_t completed, uint64_t total,
                                    size_t completed_files,
                                    size_t total_files)
{
    struct c2_browser_progress_state *state = userdata;
    if (state->reported && completed < total &&
        completed_files == state->last_files &&
        completed - state->last_bytes < 1024 * 1024) {
        return;
    }
    state->last_bytes = completed;
    state->last_files = completed_files;
    state->reported = 1;
    c2_browser_import_progress(
        phase,
        (unsigned int)(completed / 1024),
        (unsigned int)((total + 1023) / 1024),
        (int)completed_files, (int)total_files);
}
#endif

static int prepare_assets(struct c2_sdl_app *app)
{
    char resolved_asset_root[4096];
    char import_error[512];
    const char *cache_root;
    const struct c2_import_progress *progress_ptr = NULL;
#if PORT_PLATFORM_WASM
    struct c2_import_progress progress;
    struct c2_browser_progress_state progress_state;
    memset(&progress_state, 0, sizeof(progress_state));
    progress.update = publish_import_progress;
    progress.userdata = &progress_state;
    progress_ptr = &progress;
#endif

#if PORT_PLATFORM_WASM
    cache_root = "/persistent";
#else
    cache_root = app->user_data_root;
#endif
    if (!c2_import_path(app->asset_source, cache_root,
                        app->asset_profile[0] ? app->asset_profile : NULL,
                        progress_ptr,
                        resolved_asset_root, sizeof(resolved_asset_root),
                        import_error, sizeof(import_error))) {
        fprintf(stderr, "could not import game data '%s': %s\n",
                app->asset_source, import_error);
#if PORT_PLATFORM_WASM
        c2_browser_import_error(import_error);
#endif
        return 0;
    }
#if PORT_PLATFORM_WASM
    c2_browser_source_ready(resolved_asset_root, app->asset_source);
#endif
    printf("prepared game data: %s\n", resolved_asset_root);
    return 1;
}

static int start_runtime(struct c2_sdl_app *app)
{
    char resolved_asset_root[4096];
    char import_error[512];
    struct c2_host_config host_config;
    char title[160];
    const char *cache_root;

#if PORT_PLATFORM_WASM
    cache_root = "/persistent";
#else
    cache_root = app->user_data_root;
#endif
    app->last_error[0] = '\0';
    if (!c2_import_path(app->asset_source, cache_root,
                        app->asset_profile[0] ? app->asset_profile : NULL,
                        NULL,
                        resolved_asset_root, sizeof(resolved_asset_root),
                        import_error, sizeof(import_error))) {
        fprintf(stderr, "could not import game data '%s': %s\n",
                app->asset_source, import_error);
        snprintf(app->last_error, sizeof(app->last_error), "%s", import_error);
#if PORT_PLATFORM_WASM
        c2_browser_import_error(import_error);
#endif
        return 0;
    }
#if PORT_PLATFORM_WASM
    c2_browser_source_ready(resolved_asset_root, app->asset_source);
#endif
    memset(&host_config, 0, sizeof(host_config));
    snprintf(title, sizeof(title), "Caesar II %s", C2_VERSION_STRING);
    host_config.title = title;
    host_config.asset_root = resolved_asset_root;
    host_config.user_data_root = app->user_data_root;
    host_config.logical_width = C2_SCREEN_WIDTH;
    host_config.logical_height = C2_SCREEN_HEIGHT;
    host_config.window_scale = 2;
    host_config.headless = app->headless;
    host_config.mouse_lock = app->mouse_lock;
    host_config.fractional_scaling = app->fractional_scaling > 0;
    host_config.fullscreen = app->fullscreen > 0;
#if PORT_FEAT_DEBUG_OBSERVATION
    host_config.enable_observation = app->smoke_kind != C2_SDL_SMOKE_NONE;
#endif
    if (!c2_host_init(&host_config)) {
        snprintf(app->last_error, sizeof(app->last_error),
                 "could not initialize the display: %s", SDL_GetError());
        return 0;
    }
    if (c2_host_asset_size("C2.ENG") == 0 ||
        c2_host_asset_size("HELP.ENG") == 0) {
        fprintf(stderr, "selected game data is missing C2.ENG or HELP.ENG\n");
        snprintf(app->last_error, sizeof(app->last_error),
                 "selected game data is missing C2.ENG or HELP.ENG");
        c2_host_shutdown();
        return 0;
    }
#if !PORT_PLATFORM_WASM
    save_asset_source(app);
#endif
    app->host_initialized = 1;
#if PORT_PLATFORM_WASM
    if (!SDL_AddEventWatch(push_pointer_event, app)) {
        fprintf(stderr, "warning: could not install push pointer input: %s\n",
                SDL_GetError());
    } else {
        app->pointer_watch_installed = 1;
    }
#endif
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
        snprintf(app->last_error, sizeof(app->last_error),
                 "could not start the engine: %s", SDL_GetError());
        return 0;
    }
    return 1;
}

#if !PORT_PLATFORM_WASM
/*
 * The launcher is the native counterpart of the browser landing page. It owns
 * source selection, import progress, and error retry; the engine only starts
 * once it reports C2_SETUP_PLAY.
 */
static int open_launcher(struct c2_sdl_app *app, const char *error)
{
    struct c2_setup_config config;
    memset(&config, 0, sizeof(config));
    config.version = C2_VERSION_STRING;
    config.source = app->asset_source;
    config.cache_root = app->user_data_root;
    config.asset_profile = app->asset_profile[0] ? app->asset_profile : NULL;
    config.error = error;
    config.fullscreen = app->fullscreen > 0;
    config.fractional_scaling = app->fractional_scaling > 0;
    if (!c2_setup_open(&config)) return 0;
    app->launcher_active = 1;
    return 1;
}

static void print_source_hint(void)
{
    fprintf(stderr,
            "Start with --game-data pointing at an installed Caesar II folder, "
            "a ZIP/ISO/CUE image, an asset pack, or a CD-ROM drive.\n");
}
#endif

#if PORT_PLATFORM_WASM
static int prepare_main(void *userdata)
{
    struct c2_sdl_app *app = userdata;
    int ok = prepare_assets(app);
    SDL_SetAtomicInt(&app->prepare_result, ok ? 1 : -1);
    return ok ? 0 : -1;
}

static SDL_Thread *create_prepare_thread(struct c2_sdl_app *app)
{
    SDL_PropertiesID props = SDL_CreateProperties();
    SDL_Thread *thread;

    if (props == 0) return NULL;
    SDL_SetPointerProperty(props,
        SDL_PROP_THREAD_CREATE_ENTRY_FUNCTION_POINTER, (void *)prepare_main);
    SDL_SetStringProperty(props,
        SDL_PROP_THREAD_CREATE_NAME_STRING, "caesar2-import");
    SDL_SetPointerProperty(props,
        SDL_PROP_THREAD_CREATE_USERDATA_POINTER, app);
    /* ISO/CUE extraction nests a 64 KiB copy buffer below path/catalog state;
     * Emscripten's small default pthread stack is not sufficient. */
    SDL_SetNumberProperty(props,
        SDL_PROP_THREAD_CREATE_STACKSIZE_NUMBER, 1024 * 1024);
    thread = SDL_CreateThreadWithProperties(props);
    SDL_DestroyProperties(props);
    return thread;
}

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
    int fractional_scaling;
    int fullscreen;
    int smoke_kind;
    int prepare_only;
    int skip_launcher;
    int explicit_source;
    int saved_source = 0;

    *appstate = &c2_app;
    {
        int i;
        for (i = 1; i < argc; i++) {
            if (strcmp(argv[i], "--version") == 0) {
                printf("Caesar II %s\n", C2_VERSION_STRING);
                return SDL_APP_SUCCESS;
            }
        }
    }
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
                         &headless, &mouse_lock, &fractional_scaling,
                         &smoke_kind, &prepare_only, &skip_launcher,
                         &explicit_source, &fullscreen)) {
        return SDL_APP_FAILURE;
    }

    snprintf(c2_app.user_data_root, sizeof(c2_app.user_data_root), "%s", user_data_root);
    if (asset_profile && *asset_profile) {
        snprintf(c2_app.asset_profile, sizeof(c2_app.asset_profile), "%s", asset_profile);
    } else {
        c2_app.asset_profile[0] = '\0';
    }
#if !PORT_PLATFORM_WASM
    if (!explicit_source &&
        load_saved_asset_source(user_data_root, c2_app.asset_source,
                                sizeof(c2_app.asset_source),
                                c2_app.asset_profile, sizeof(c2_app.asset_profile))) {
        asset_root = c2_app.asset_source;
        saved_source = 1;
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
    c2_app.headless = headless;
    c2_app.mouse_lock = mouse_lock;
#if !PORT_PLATFORM_WASM
    {
        int saved_fullscreen = 0;
        int saved_fractional = 0;
        load_display_settings(user_data_root, &saved_fullscreen, &saved_fractional);
        if (fullscreen < 0) fullscreen = saved_fullscreen;
        if (fractional_scaling < 0) fractional_scaling = saved_fractional;
    }
#endif
    if (fullscreen < 0) fullscreen = 0;
    if (fractional_scaling < 0) fractional_scaling = 0;
    c2_app.fractional_scaling = fractional_scaling;
    c2_app.fullscreen = fullscreen;
    c2_app.smoke_kind = smoke_kind;
    c2_app.prepare_only = prepare_only;
    c2_app.skip_launcher = skip_launcher;
    c2_app.launcher_active = 0;
    c2_app.last_error[0] = '\0';
    (void)explicit_source;
    (void)saved_source;
#if PORT_PLATFORM_WASM
    SDL_SetAtomicInt(&c2_app.storage_result, 0);
    SDL_SetAtomicInt(&c2_app.prepare_result, 0);
    c2_app.storage_thread = SDL_CreateThread(storage_main, "caesar2-storage", NULL);
    if (c2_app.storage_thread == NULL) return SDL_APP_FAILURE;
    return SDL_APP_CONTINUE;
#else
    if (c2_app.prepare_only) {
        SDL_AppResult prepared = prepare_assets(&c2_app)
            ? SDL_APP_SUCCESS : SDL_APP_FAILURE;
        SDL_free(c2_app.default_user_data_root);
        c2_app.default_user_data_root = NULL;
        return prepared;
    }
    if (c2_app.headless || c2_app.skip_launcher) {
        /* Non-interactive runs must never open a dialog: fail fast with a
         * non-zero exit so CI and smoke runs cannot hang. */
        if (!start_runtime(&c2_app)) {
            print_source_hint();
            SDL_free(c2_app.default_user_data_root);
            c2_app.default_user_data_root = NULL;
            return SDL_APP_FAILURE;
        }
        return SDL_APP_CONTINUE;
    }
    /* Interactive: show the launcher first. The implicit "." default only
     * counts as a source when the working directory really holds the game,
     * so first-run users see "none selected" instead of a cryptic error. */
    if (!explicit_source && !saved_source &&
        !c2_setup_source_looks_valid(c2_app.asset_source)) {
        c2_app.asset_source[0] = '\0';
    }
    if (!open_launcher(&c2_app, NULL)) {
        /* No usable display for the launcher; fall back to a direct start so
         * a scripted --game-data invocation still works. */
        if (!start_runtime(&c2_app)) {
            print_source_hint();
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
#if !PORT_PLATFORM_WASM
    if (app->launcher_active) {
        c2_setup_handle_event(event);
        return SDL_APP_CONTINUE;
    }
#endif
    if (!app->host_initialized) return SDL_APP_CONTINUE;
#if PORT_PLATFORM_WASM
    if (app->pointer_watch_installed && is_pointer_event(event->type)) {
        update_host_callback_rate(app);
        return SDL_APP_CONTINUE; /* already delivered synchronously by watch */
    }
#endif
    c2_sdl_host_handle_event(event);
    update_host_callback_rate(app);
    return SDL_APP_CONTINUE;
}

SDL_AppResult SDL_AppIterate(void *appstate)
{
    struct c2_sdl_app *app;
    int result;

    app = appstate;
#if !PORT_PLATFORM_WASM
    if (app->launcher_active) {
        enum c2_setup_result setup = c2_setup_iterate();
        if (setup == C2_SETUP_RUNNING) return SDL_APP_CONTINUE;
        snprintf(app->asset_source, sizeof(app->asset_source), "%s",
                 c2_setup_selected_source());
        snprintf(app->asset_profile, sizeof(app->asset_profile), "%s",
                 c2_setup_selected_profile());
        app->fullscreen = c2_setup_selected_fullscreen();
        app->fractional_scaling = c2_setup_selected_fractional_scaling();
        c2_setup_close();
        if (setup == C2_SETUP_PLAY) save_display_settings(app);
        app->launcher_active = 0;
        if (setup == C2_SETUP_QUIT) return SDL_APP_SUCCESS;
        SDL_SetHint(SDL_HINT_MAIN_CALLBACK_RATE, C2_HOST_ACTIVE_CALLBACK_RATE);
        app->host_interactive = -1;
        if (start_runtime(app)) return SDL_APP_CONTINUE;
        /* Return to the launcher with the reason instead of dying. */
        if (!open_launcher(app, app->last_error[0] ? app->last_error
                                                  : "could not start the game")) {
            return SDL_APP_FAILURE;
        }
        return SDL_APP_CONTINUE;
    }
#endif
#if PORT_PLATFORM_WASM
    if (!app->host_initialized) {
        int storage_result = SDL_GetAtomicInt(&app->storage_result);
        if (storage_result == 0) return SDL_APP_CONTINUE;
        if (app->storage_thread != NULL) {
            SDL_WaitThread(app->storage_thread, NULL);
            app->storage_thread = NULL;
        }
        if (storage_result < 0) return SDL_APP_FAILURE;
        if (app->prepare_only) {
            int prepare_result = SDL_GetAtomicInt(&app->prepare_result);
            if (prepare_result == 0) {
                if (app->prepare_thread == NULL) {
                    app->prepare_thread = create_prepare_thread(app);
                    if (app->prepare_thread == NULL) return SDL_APP_FAILURE;
                }
                return SDL_APP_CONTINUE;
            }
            if (app->prepare_thread != NULL) {
                SDL_WaitThread(app->prepare_thread, NULL);
                app->prepare_thread = NULL;
            }
            return prepare_result > 0 ? SDL_APP_SUCCESS : SDL_APP_FAILURE;
        }
        if (!start_runtime(app)) return SDL_APP_FAILURE;
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
#if !PORT_PLATFORM_WASM
    if (app != NULL && app->launcher_active) {
        c2_setup_close();
        app->launcher_active = 0;
    }
#endif
#if PORT_PLATFORM_WASM
    if (app != NULL && app->pointer_watch_installed) {
        SDL_RemoveEventWatch(push_pointer_event, app);
        app->pointer_watch_installed = 0;
    }
#endif
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
    if (app != NULL && app->prepare_thread != NULL) {
        SDL_WaitThread(app->prepare_thread, NULL);
        app->prepare_thread = NULL;
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
