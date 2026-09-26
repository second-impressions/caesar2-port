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
#include "c2_library.h"
#include "c2_port.h"
#include "c2_port_app.h"
#if PORT_FEAT_DEBUG_CRASH_HANDLER
#include "c2_debug_crash.h"
#endif
#include "c2_sdl_host.h"
#include "c2_setup_ui.h"
#if PORT_PLATFORM_WIN32
#include "c2_win32_console.h"
#endif
#include "c2_port_text.h"
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

/* Settings > Game data > Music; takes effect at once when music plays. */
EMSCRIPTEN_KEEPALIVE void c2_browser_set_music_source(int recorded)
{
#if PORT_FEAT_RECORDED_MUSIC
    /* 1: the 1996 Windows recordings, 0: the 1995 DOS music. */
    c2_port_music_set_preference(recorded ? C2_PORT_MUSIC_RECORDED : C2_PORT_MUSIC_XMIDI);
#else
    (void)recorded;
#endif
}

/* "tag\tname\n" per compiled-in text language, for the page's selector. */
EMSCRIPTEN_KEEPALIVE const char *c2_browser_text_languages(void)
{
    static char list[512];
    size_t used = 0;
    int i;

    for (i = 0; i < c2_port_text_language_count(); i++) {
        const struct c2_port_language *l = c2_port_text_language(i);
        int n = snprintf(list + used, sizeof(list) - used, "%s\t%s\n", l->tag, l->name);
        if (n < 0 || used + (size_t)n >= sizeof(list)) break;
        used += (size_t)n;
    }
    return list;
}

/* The library changed (an import or a migration finished); the page reads
 * /persistent/game-data/local/summary again. */
extern void c2_browser_library_changed(void);
/* An export finished and the archive is at `path` in OPFS. */
extern void c2_browser_export_ready(const char *path);
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
    char game_data_root[4096];  /* holds library/ and local/ */
    char asset_root[4096];      /* --asset-root: read in place instead */
    char import_source[4096];   /* --game-data: add this first */
    char export_path[4096];     /* --export-game-data */
    char user_data_root[4096];
    char screenshot_filename[4096];
    char speech[16];            /* speech language wished for; "" = pick */
    char text_language[16];   /* "" = detect from the game data */
    char music_source[16];    /* "recorded" or "xmidi"; "" = the default */
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
                           const char **import_source,
                           const char **export_path,
                           const char **user_data_root,
                           char **default_user_data_root,
                           const char **screenshot_filename,
                           const char **speech,
                           const char **text_language,
                           const char **music_source,
                           int *crash_test,
                           int *headless, int *mouse_lock,
                           int *fractional_scaling, int *smoke_kind,
                           int *prepare_only, int *skip_launcher,
                           int *explicit_source, int *fullscreen)
{
    int i;

    /* C2_ASSET_ROOT and --asset-root read game data in place (tests,
     * development); --game-data and a bare path add it to the library. */
    *asset_root = getenv("C2_ASSET_ROOT");
    if (*asset_root != NULL && **asset_root == '\0') *asset_root = NULL;
    *import_source = NULL;
    *export_path = NULL;
    *explicit_source = *asset_root != NULL;
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
    *speech = NULL;
    *text_language = NULL;
    *music_source = NULL;
    *crash_test = 0;

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
        } else if (strcmp(argv[i], "--province-build-smoke-test") == 0) {
            *headless = 1;
            *smoke_kind = C2_SDL_SMOKE_PROVINCE_BUILD;
        } else if (strcmp(argv[i], "--city-build-smoke-test") == 0) {
            *headless = 1;
            *smoke_kind = C2_SDL_SMOKE_CITY_BUILD;
        } else if (strcmp(argv[i], "--crash-test") == 0) {
            *crash_test = 1;
#endif
        } else if (strcmp(argv[i], "--asset-root") == 0 && i + 1 < argc) {
            *asset_root = argv[++i];
            *explicit_source = 1;
        } else if (strcmp(argv[i], "--game-data") == 0 && i + 1 < argc) {
            *import_source = argv[++i];
            *explicit_source = 1;
        } else if (strcmp(argv[i], "--export-game-data") == 0 && i + 1 < argc) {
            *export_path = argv[++i];
        } else if (strcmp(argv[i], "--user-data-dir") == 0 && i + 1 < argc) {
            *user_data_root = argv[++i];
        } else if (strcmp(argv[i], "--speech") == 0 && i + 1 < argc) {
            *speech = argv[++i];
        } else if (strcmp(argv[i], "--language") == 0 && i + 1 < argc) {
            *text_language = argv[++i];
        } else if (strcmp(argv[i], "--music") == 0 && i + 1 < argc) {
            *music_source = argv[++i];
        } else if (strcmp(argv[i], "--screenshot") == 0 && i + 1 < argc) {
            *screenshot_filename = argv[++i];
        } else if (argv[i][0] != '-') {
            *import_source = argv[i];
            *explicit_source = 1;
        } else {
#if PORT_FEAT_DEBUG_OBSERVATION
            fprintf(stderr,
                    "usage: %s [--headless] [--game-data SOURCE] [--asset-root DIR] "
                    "[--export-game-data FILE] [--speech TAG] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--mouse-lock|--no-mouse-lock] [--prepare-assets] "
                    "[--skip-launcher] [--fullscreen] [--fractional-scaling] "
                    "[--language TAG] [--music dos|windows] "
                    "[--smoke-test|--city-smoke-test|"
                    "--tutorial-smoke-test|--save-load-smoke-test|"
                    "--music-buffer-smoke-test|"
                    "--campania-transition-smoke-test|--province-build-smoke-test|"
                    "--city-build-smoke-test]\n",
                    argv[0]);
#else
            fprintf(stderr,
                    "usage: %s [--headless] [--game-data SOURCE] [--asset-root DIR] "
                    "[--export-game-data FILE] [--speech TAG] "
                    "[--user-data-dir PATH] [--screenshot FILE] "
                    "[--mouse-lock|--no-mouse-lock] [--prepare-assets] "
                    "[--skip-launcher] [--fullscreen] [--fractional-scaling] "
                    "[--language TAG] [--music dos|windows]\n",
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

/* launcher.ini: the choices the launcher offers. Missing keys keep the
 * defaults (windowed, integer scaling, text and speech picked from the
 * game data). */
static void load_display_settings(const char *user_root, int *fullscreen,
                                  int *fractional_scaling,
                                  char *text_language, size_t language_capacity,
                                  char *music_source, size_t music_capacity,
                                  char *speech, size_t speech_capacity)
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
        else if (strncmp(line, "language=", 9) == 0 && text_language) {
            const char *tag = line + 9;
            if (strcmp(tag, "auto") == 0 || strlen(tag) >= language_capacity) tag = "";
            strcpy(text_language, tag);
        } else if (strncmp(line, "music=", 6) == 0 && music_source &&
                   strlen(line + 6) < music_capacity) {
            strcpy(music_source, line + 6);
        } else if (strncmp(line, "speech=", 7) == 0 && speech &&
                   strlen(line + 7) < speech_capacity) {
            strcpy(speech, strcmp(line + 7, "auto") == 0 ? "" : line + 7);
        }
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
    fprintf(file, "fullscreen=%d\nscaling=%s\nlanguage=%s\nmusic=%s\nspeech=%s\n", app->fullscreen ? 1 : 0,
            app->fractional_scaling ? "fractional" : "integer",
            app->text_language[0] ? app->text_language : "auto",
            app->music_source[0] ? app->music_source : "dos",
            app->speech[0] ? app->speech : "auto");
    fclose(file);
}

/*
 * Before the library, the launcher remembered its source in
 * asset-source.txt and kept one extracted copy per source beside it. Those
 * copies are merged into the library; the remembered source only matters
 * when it was a folder read in place, which never had a copy.
 */
static void migrate_legacy_game_data(struct c2_sdl_app *app)
{
    char path[4096];
    char source[4096];
    char error[512];
    FILE *file;
    int migrated = c2_library_migrate(app->game_data_root, NULL, error, sizeof(error));
    if (migrated > 0) printf("moved %d earlier import(s) into the game-data library\n", migrated);
    if (snprintf(path, sizeof(path), "%s/asset-source.txt", app->user_data_root) >= (int)sizeof(path)) return;
    file = fopen(path, "rb");
    if (!file) return;
    source[0] = '\0';
    if (fgets(source, (int)sizeof(source), file)) chomp(source);
    fclose(file);
    if (source[0] && migrated <= 0) {
        SDL_PathInfo info;
        if (SDL_GetPathInfo(source, &info) && info.type == SDL_PATHTYPE_DIRECTORY &&
            !c2_library_import(app->game_data_root, source, NULL, error, sizeof(error))) {
            fprintf(stderr, "could not add the earlier game data '%s': %s\n", source, error);
        }
    }
    SDL_RemovePath(path);
}
#endif

/*
 * Import (--game-data) or export (--export-game-data) without starting the
 * engine: the browser page's way to fill the library, and a command line
 * way on native builds.
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
    char error[512];
    const struct c2_import_progress *progress_ptr = NULL;
    struct c2_library_summary summary;
    int ok = 1;
#if PORT_PLATFORM_WASM
    struct c2_import_progress progress;
    struct c2_browser_progress_state progress_state;
    memset(&progress_state, 0, sizeof(progress_state));
    progress.update = publish_import_progress;
    progress.userdata = &progress_state;
    progress_ptr = &progress;
    /* Caches from before the library: fold them in once. */
    c2_library_migrate(app->game_data_root, progress_ptr, error, sizeof(error));
#endif
    error[0] = '\0';
    if (app->import_source[0]) {
        ok = c2_library_import(app->game_data_root, app->import_source, progress_ptr,
                               error, sizeof(error));
        if (!ok) {
            fprintf(stderr, "could not import game data '%s': %s\n", app->import_source, error);
#if PORT_PLATFORM_WASM
            c2_browser_import_error(error);
#endif
        }
    }
    if (ok && app->export_path[0]) {
        ok = c2_library_export(app->game_data_root, app->export_path, progress_ptr,
                               error, sizeof(error));
        if (!ok) {
            fprintf(stderr, "could not export the game data: %s\n", error);
#if PORT_PLATFORM_WASM
            c2_browser_import_error(error);
#endif
        } else {
            printf("exported game data: %s\n", app->export_path);
#if PORT_PLATFORM_WASM
            c2_browser_export_ready(app->export_path);
#endif
        }
    }
    c2_library_describe(app->game_data_root, &summary);
#if PORT_PLATFORM_WASM
    if (ok) c2_browser_library_changed();
#endif
    if (ok) {
        int i;
        printf("prepared game data: %s%s\n", summary.playable ? "playable" : "incomplete",
               summary.music_windows ? ", Windows music" : "");
        for (i = 0; i < summary.language_count; i++) {
            printf("  %s %s %s\n", summary.languages[i].tag,
                   summary.languages[i].speech ? "speech" : "text", summary.languages[i].version);
        }
    }
    return ok;
}

static int start_runtime(struct c2_sdl_app *app)
{
    struct c2_host_config host_config;
    char title[160];
    const char *speech;

    app->last_error[0] = '\0';
    /* The speech wished for; failing that the chosen text language, so a
     * German text choice brings German voices when the data has them. */
    speech = app->speech[0] ? app->speech : app->text_language;
    memset(&host_config, 0, sizeof(host_config));
    snprintf(title, sizeof(title), "Caesar II %s", C2_VERSION_STRING);
    host_config.title = title;
    host_config.asset_root = app->asset_root[0] ? app->asset_root : app->game_data_root;
    host_config.speech = speech;
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
/*
 * A crash report newer than the launcher's last start (launcher.ini is
 * rewritten on every Play) is from the last run; say so, with its path,
 * since a player who started from a desktop icon saw nothing else.
 */
#if PORT_FEAT_DEBUG_CRASH_HANDLER
static const char *last_crash_report(struct c2_sdl_app *app)
{
    static char notice[4096 + 96];
    char ini[4096];
    char path[4096];
    SDL_PathInfo ini_info;
    SDL_PathInfo report_info;
    SDL_Time since = 0;
    char **entries;
    int count;
    int i;
    int best = -1;
    SDL_Time best_time = 0;

    if (snprintf(ini, sizeof(ini), "%s/launcher.ini", app->user_data_root) < (int)sizeof(ini) &&
        SDL_GetPathInfo(ini, &ini_info)) {
        since = ini_info.modify_time;
    }
    entries = SDL_GlobDirectory(app->user_data_root, C2_CRASH_REPORT_PREFIX "*" C2_CRASH_REPORT_SUFFIX,
                                0, &count);
    if (entries == NULL) return NULL;
    for (i = 0; i < count; i++) {
        if (snprintf(path, sizeof(path), "%s/%s", app->user_data_root, entries[i]) >= (int)sizeof(path)) continue;
        if (!SDL_GetPathInfo(path, &report_info) || report_info.type != SDL_PATHTYPE_FILE) continue;
        if (report_info.size == 0 || report_info.modify_time <= since) continue;
        if (best < 0 || report_info.modify_time > best_time) {
            best = i;
            best_time = report_info.modify_time;
        }
    }
    if (best >= 0) {
        snprintf(notice, sizeof(notice), "The last run crashed. Report: %s/%s",
                 app->user_data_root, entries[best]);
    }
    SDL_free(entries);
    return best >= 0 ? notice : NULL;
}
#endif

static int open_launcher(struct c2_sdl_app *app, const char *error)
{
    struct c2_setup_config config;
    memset(&config, 0, sizeof(config));
#if PORT_FEAT_DEBUG_CRASH_HANDLER
    if (error == NULL) error = last_crash_report(app);
#endif
    config.version = C2_VERSION_STRING;
    config.game_data_root = app->game_data_root;
    config.pending_source = app->import_source[0] ? app->import_source : NULL;
    config.speech = app->speech;
    config.text_language = app->text_language;
    config.music_source = app->music_source;
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
            "Add game data with --game-data: an installed Caesar II folder, a "
            "disc image (ISO, BIN/CUE, Mac Toast), a ZIP, a .c2assets file, or a "
            "CD-ROM drive.\n");
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
    const char *import_source;
    const char *export_path;
    const char *user_data_root;
    const char *screenshot_filename;
    const char *speech;
    const char *text_language;
    const char *music_source;
    int crash_test;
    int headless;
    int mouse_lock;
    int fractional_scaling;
    int fullscreen;
    int smoke_kind;
    int prepare_only;
    int skip_launcher;
    int explicit_source;

#if PORT_PLATFORM_WIN32
    /* Before the first printf: this executable is windowed, so what it
     * prints to is the console that started it, if there is one. */
    c2_win32_attach_parent_console();
#endif
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
    if (!parse_arguments(argc, argv, &asset_root, &import_source, &export_path,
                         &user_data_root,
                         &c2_app.default_user_data_root,
                         &screenshot_filename, &speech,
                         &text_language, &music_source, &crash_test,
                         &headless, &mouse_lock, &fractional_scaling,
                         &smoke_kind, &prepare_only, &skip_launcher,
                         &explicit_source, &fullscreen)) {
        return SDL_APP_FAILURE;
    }

    snprintf(c2_app.user_data_root, sizeof(c2_app.user_data_root), "%s", user_data_root);
#if PORT_PLATFORM_WASM
    snprintf(c2_app.game_data_root, sizeof(c2_app.game_data_root), "/persistent/game-data");
#else
    snprintf(c2_app.game_data_root, sizeof(c2_app.game_data_root), "%s/game-data", user_data_root);
#endif
    snprintf(c2_app.asset_root, sizeof(c2_app.asset_root), "%s", asset_root ? asset_root : "");
    snprintf(c2_app.import_source, sizeof(c2_app.import_source), "%s", import_source ? import_source : "");
    snprintf(c2_app.export_path, sizeof(c2_app.export_path), "%s", export_path ? export_path : "");
    if (export_path) prepare_only = 1;
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
        load_display_settings(user_data_root, &saved_fullscreen, &saved_fractional,
                              c2_app.text_language, sizeof(c2_app.text_language),
                              c2_app.music_source, sizeof(c2_app.music_source),
                              c2_app.speech, sizeof(c2_app.speech));
        if (fullscreen < 0) fullscreen = saved_fullscreen;
        if (fractional_scaling < 0) fractional_scaling = saved_fractional;
    }
#endif
    if (fullscreen < 0) fullscreen = 0;
    if (fractional_scaling < 0) fractional_scaling = 0;
    c2_app.fractional_scaling = fractional_scaling;
    c2_app.fullscreen = fullscreen;
#if PORT_FEAT_DEBUG_CRASH_HANDLER
    c2_debug_set_crash_report_directory(c2_app.user_data_root);
#endif
    if (crash_test) {
        /* Debug builds only: prove the report reaches the user-data directory. */
        volatile int *nowhere = NULL;
        fprintf(stderr, "crash test: faulting on purpose\n");
        *nowhere = 1;
    }
    if (text_language) {
        if (!c2_port_text_select(text_language)) {
            int i;
            fprintf(stderr, "unknown --language '%s'; compiled in:", text_language);
            for (i = 0; i < c2_port_text_language_count(); i++)
                fprintf(stderr, " %s", c2_port_text_language(i)->tag);
            fprintf(stderr, "\n");
            return SDL_APP_FAILURE;
        }
        snprintf(c2_app.text_language, sizeof(c2_app.text_language), "%s", text_language);
    } else if (c2_app.text_language[0] && !c2_port_text_select(c2_app.text_language)) {
        c2_app.text_language[0] = '\0';  /* a language no longer compiled in */
    }
#if PORT_FEAT_RECORDED_MUSIC
    {
        enum c2_port_music_source source;
        if (music_source) {
            if (!c2_port_music_source_parse(music_source, &source)) {
                fprintf(stderr, "unknown --music '%s'; dos or windows\n", music_source);
                return SDL_APP_FAILURE;
            }
            snprintf(c2_app.music_source, sizeof(c2_app.music_source), "%s", music_source);
        }
        if (c2_port_music_source_parse(c2_app.music_source, &source)) {
            c2_port_music_set_preference(source);
        } else {
            c2_app.music_source[0] = '\0';
        }
    }
#endif
    if (speech) snprintf(c2_app.speech, sizeof(c2_app.speech), "%s", speech);
    /* The library names language folders with the text catalogue's tags. */
    c2_library_set_language_detector(c2_port_text_detect);
    c2_app.smoke_kind = smoke_kind;
    c2_app.prepare_only = prepare_only;
    c2_app.skip_launcher = skip_launcher;
    c2_app.launcher_active = 0;
    c2_app.last_error[0] = '\0';
    (void)explicit_source;
#if PORT_PLATFORM_WASM
    SDL_SetAtomicInt(&c2_app.storage_result, 0);
    SDL_SetAtomicInt(&c2_app.prepare_result, 0);
    c2_app.storage_thread = SDL_CreateThread(storage_main, "caesar2-storage", NULL);
    if (c2_app.storage_thread == NULL) return SDL_APP_FAILURE;
    return SDL_APP_CONTINUE;
#else
    migrate_legacy_game_data(&c2_app);
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
        if ((c2_app.import_source[0] && !prepare_assets(&c2_app)) ||
            !start_runtime(&c2_app)) {
            print_source_hint();
            SDL_free(c2_app.default_user_data_root);
            c2_app.default_user_data_root = NULL;
            return SDL_APP_FAILURE;
        }
        return SDL_APP_CONTINUE;
    }
    /* Interactive: show the launcher first; it adds --game-data itself,
     * with progress. */
    if (!open_launcher(&c2_app, NULL)) {
        /* No usable display for the launcher; fall back to a direct start so
         * a scripted --game-data invocation still works. */
        if ((c2_app.import_source[0] && !prepare_assets(&c2_app)) ||
            !start_runtime(&c2_app)) {
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
#if !PORT_PLATFORM_WASM
    /* Display toggles never reach the game and are remembered like the
     * launcher's choices; the browser shell owns both on its own chrome. */
    if (event->type == SDL_EVENT_KEY_DOWN && !event->key.repeat) {
        if (event->key.key == SDLK_F11) {
            app->fullscreen = !c2_host_is_fullscreen();
            c2_host_set_fullscreen(app->fullscreen);
            save_display_settings(app);
            return SDL_APP_CONTINUE;
        }
        if (event->key.key == SDLK_F10) {
            app->fractional_scaling = !c2_host_is_fractional_scaling();
            c2_host_set_fractional_scaling(app->fractional_scaling);
            save_display_settings(app);
            return SDL_APP_CONTINUE;
        }
    }
#endif
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
        app->import_source[0] = '\0';  /* the launcher added it */
        snprintf(app->speech, sizeof(app->speech), "%s", c2_setup_selected_speech());
        app->fullscreen = c2_setup_selected_fullscreen();
        app->fractional_scaling = c2_setup_selected_fractional_scaling();
        snprintf(app->text_language, sizeof(app->text_language), "%s",
                 c2_setup_selected_text_language());
        c2_port_text_select(app->text_language[0] ? app->text_language : NULL);
#if PORT_FEAT_RECORDED_MUSIC
        {
            enum c2_port_music_source source;
            snprintf(app->music_source, sizeof(app->music_source), "%s",
                     c2_setup_selected_music_source());
            if (c2_port_music_source_parse(app->music_source, &source)) {
                c2_port_music_set_preference(source);
            }
        }
#endif
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
