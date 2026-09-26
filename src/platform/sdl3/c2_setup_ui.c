#include "c2_setup_ui.h"
#include "c2_port_text.h"

#if !PORT_PLATFORM_WASM

#include "c2_import.h"
#include "c2_library.h"
#include "c2_sdl_host.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Public-domain 8x8 glyphs (Daniel Hepper / Marcel Sondaar / IBM VGA). */
#include "font8x8/font8x8_basic.h"

/*
 * Three pages in one 480x440 window: the main page (Play, Game data,
 * Settings, Quit), the game-data page (add, choose speech and music,
 * export, remove) and the settings page (text, display). Esc goes back.
 * What the game data holds comes from the shared library
 * (c2_library_describe); nothing here knows how it is laid out.
 */
#define UI_WIDTH 480
#define UI_HEIGHT 440
#define UI_SCALE 2
#define UI_MARGIN 16
#define UI_GLYPH 8
#define UI_BUTTON_HEIGHT 22
#define UI_BUTTON_GAP 6
/* The summary block: four lines from UI_INFO_TOP; the status line has a
 * row of its own below them, then at most eight buttons, then the key
 * reference from UI_LEGEND_TOP. Nothing is drawn over anything. */
#define UI_INFO_TOP 72
#define UI_LINE 12
#define UI_INFO_LINES 4
#define UI_STATUS_TOP (UI_INFO_TOP + UI_INFO_LINES * UI_LINE + 2)
#define UI_BUTTONS_TOP (UI_STATUS_TOP + UI_LINE + 2)
#define UI_MAX_BUTTONS 8
#define UI_LEGEND_TOP (UI_BUTTONS_TOP + UI_MAX_BUTTONS * (UI_BUTTON_HEIGHT + UI_BUTTON_GAP))
#define UI_MAX_DRIVES 2
#define UI_PATH_CAPACITY 4096

/* Optical drives come and go (USB readers); poll while the menu is idle. */
#define UI_DRIVE_RESCAN_MS 2000

enum setup_state {
    SETUP_MENU = 0,
    SETUP_DIALOG,
    SETUP_WORK
};

enum page {
    PAGE_MAIN = 0,
    PAGE_DATA,
    PAGE_SETTINGS
};

enum job {
    JOB_IMPORT = 0,
    JOB_EXPORT,
    JOB_REMOVE
};

enum dialog {
    DIALOG_ADD = 0,
    DIALOG_EXPORT
};

enum button_kind {
    BUTTON_PLAY = 0,
    BUTTON_DATA,
    BUTTON_SETTINGS,
    BUTTON_QUIT,
    BUTTON_BACK,
    BUTTON_DRIVE,
    BUTTON_ADD,
    BUTTON_SPEECH,
    BUTTON_MUSIC,
    BUTTON_EXPORT,
    BUTTON_REMOVE,
    BUTTON_TEXT,
    BUTTON_DISPLAY,
    BUTTON_SCALING
};

struct button {
    enum button_kind kind;
    char label[64];
    char hint[32];
    char drive[C2_CDROM_DRIVE_PATH_CAPACITY];
    int enabled;
    int warning;
    SDL_FRect rect;
};

/* The launcher font is ASCII: fold the po's native name ("Fran\u00e7ais"). */
static const char *language_label(const char *tag, char *out, size_t capacity)
{
    static const struct { const char *utf8; char ascii; } folds[] = {
        { "\xc3\xa7", 'c' }, { "\xc3\xa9", 'e' }, { "\xc3\xa8", 'e' }, { "\xc3\xaa", 'e' },
        { "\xc3\xa0", 'a' }, { "\xc3\xa1", 'a' }, { "\xc3\xa4", 'a' }, { "\xc3\xb6", 'o' },
        { "\xc3\xbc", 'u' }, { "\xc3\xb1", 'n' }, { "\xc3\xad", 'i' }, { "\xc3\xb3", 'o' },
        { "\xc3\xba", 'u' }, { "\xc3\x9f", 's' }
    };
    const char *name = tag;
    size_t used = 0;
    int i;

    for (i = 0; i < c2_port_text_language_count(); i++) {
        const struct c2_port_language *l = c2_port_text_language(i);
        if (strcmp(l->tag, tag) == 0) { name = l->name; break; }
    }
    while (*name && used + 1 < capacity) {
        size_t f;
        int folded = 0;
        for (f = 0; f < sizeof(folds) / sizeof(folds[0]); f++) {
            if (strncmp(name, folds[f].utf8, 2) == 0) {
                out[used++] = folds[f].ascii;
                name += 2;
                folded = 1;
                break;
            }
        }
        if (folded) continue;
        if ((unsigned char)*name >= 0x80) {
            while ((unsigned char)*name >= 0x80) name++;
            out[used++] = '?';
            continue;
        }
        out[used++] = *name++;
    }
    out[used] = '\0';
    return out;
}

struct rgb { Uint8 r, g, b; };

static const struct rgb COLOR_BACKGROUND = { 22, 20, 28 };
static const struct rgb COLOR_RULE = { 70, 60, 48 };
static const struct rgb COLOR_TITLE = { 226, 190, 96 };
static const struct rgb COLOR_TEXT = { 224, 220, 210 };
static const struct rgb COLOR_MUTED = { 140, 134, 124 };
static const struct rgb COLOR_ERROR = { 232, 96, 80 };
static const struct rgb COLOR_OK = { 128, 208, 120 };
static const struct rgb COLOR_BUTTON = { 56, 50, 62 };
static const struct rgb COLOR_BUTTON_HOVER = { 84, 74, 92 };
static const struct rgb COLOR_BUTTON_DISABLED = { 36, 34, 40 };
static const struct rgb COLOR_FOCUS = { 226, 190, 96 };
static const struct rgb COLOR_BAR = { 226, 190, 96 };
static const struct rgb COLOR_BAR_BACK = { 44, 40, 50 };

static struct {
    int open;
    SDL_Window *window;
    SDL_Renderer *renderer;
    SDL_Texture *font;
    SDL_Mutex *mutex;

    enum setup_state state;
    enum page page;
    enum c2_setup_result result;
    int quit_after_work;

    char version[64];
    char game_data_root[UI_PATH_CAPACITY];
    struct c2_library_summary summary;
    char speech[C2_LIBRARY_TAG_CAPACITY];  /* "" = the default pick */
    char text_language[16];   /* compiled-in text; "" follows the game data */
    char music_source[16];    /* "windows" or "dos"; "" = the default */
    int fullscreen;
    int fractional_scaling;
    int confirm_remove;       /* Remove pressed once; Enter again removes */
    char status[256];
    const struct rgb *status_color;

    struct button buttons[UI_MAX_BUTTONS];
    int button_count;
    int focus;
    int hover;
    char drives[UI_MAX_DRIVES][C2_CDROM_DRIVE_PATH_CAPACITY];
    int drive_count;
    Uint64 next_drive_scan;

    /* Dialog callback state (written from SDL's dialog thread). */
    enum dialog dialog_kind;
    int dialog_done;
    char dialog_path[UI_PATH_CAPACITY];

    /* Worker state (written from the worker thread). */
    SDL_Thread *thread;
    enum job job;
    char job_path[UI_PATH_CAPACITY];
    char phase[64];
    uint64_t completed_bytes;
    uint64_t total_bytes;
    size_t completed_files;
    size_t total_files;
    int work_done;
    int work_ok;
    char work_error[512];
} ui;

/* ------------------------------------------------------------------ */
/* Text rendering                                                      */

static SDL_Texture *build_font(SDL_Renderer *renderer)
{
    SDL_Surface *surface;
    SDL_Texture *texture;
    Uint32 *pixels;
    int glyph;
    int row;
    int column;

    surface = SDL_CreateSurface(128 * UI_GLYPH, UI_GLYPH, SDL_PIXELFORMAT_RGBA32);
    if (surface == NULL) return NULL;
    pixels = surface->pixels;
    for (glyph = 0; glyph < 128; glyph++) {
        for (row = 0; row < UI_GLYPH; row++) {
            unsigned char bits = (unsigned char)font8x8_basic[glyph][row];
            for (column = 0; column < UI_GLYPH; column++) {
                int x = glyph * UI_GLYPH + column;
                int y = row;
                Uint32 value = (bits >> column) & 1u ? 0xffffffffu : 0u;
                pixels[y * (surface->pitch / 4) + x] = value;
            }
        }
    }
    texture = SDL_CreateTextureFromSurface(renderer, surface);
    SDL_DestroySurface(surface);
    if (texture == NULL) return NULL;
    SDL_SetTextureScaleMode(texture, SDL_SCALEMODE_NEAREST);
    SDL_SetTextureBlendMode(texture, SDL_BLENDMODE_BLEND);
    return texture;
}

static int text_width(const char *text, int scale)
{
    return (int)strlen(text) * UI_GLYPH * scale;
}

static void draw_text(int x, int y, int scale, const struct rgb *color,
                      const char *text)
{
    SDL_FRect src;
    SDL_FRect dst;
    SDL_SetTextureColorMod(ui.font, color->r, color->g, color->b);
    src.y = 0;
    src.w = UI_GLYPH;
    src.h = UI_GLYPH;
    dst.y = (float)y;
    dst.w = (float)(UI_GLYPH * scale);
    dst.h = (float)(UI_GLYPH * scale);
    for (; *text; text++, x += UI_GLYPH * scale) {
        unsigned char c = (unsigned char)*text;
        if (c >= 128) c = '?';
        src.x = (float)(c * UI_GLYPH);
        dst.x = (float)x;
        SDL_RenderTexture(ui.renderer, ui.font, &src, &dst);
    }
}

/* Prose is cut on the right; a path keeps its tail, the file name. */
static void fit_text(char *out, size_t capacity, const char *text, int max_chars)
{
    size_t length = strlen(text);
    if ((int)length <= max_chars) {
        snprintf(out, capacity, "%s", text);
        return;
    }
    snprintf(out, capacity, "%.*s...", max_chars - 3, text);
}

static void fit_path(char *out, size_t capacity, const char *path, int max_chars)
{
    size_t length = strlen(path);
    if ((int)length <= max_chars) {
        snprintf(out, capacity, "%s", path);
        return;
    }
    snprintf(out, capacity, "...%s", path + length - (size_t)(max_chars - 3));
}

static void fill_rect(int x, int y, int w, int h, const struct rgb *color)
{
    SDL_FRect rect = { (float)x, (float)y, (float)w, (float)h };
    SDL_SetRenderDrawColor(ui.renderer, color->r, color->g, color->b, 255);
    SDL_RenderFillRect(ui.renderer, &rect);
}

static void outline_rect(int x, int y, int w, int h, const struct rgb *color)
{
    SDL_FRect rect = { (float)x, (float)y, (float)w, (float)h };
    SDL_SetRenderDrawColor(ui.renderer, color->r, color->g, color->b, 255);
    SDL_RenderRect(ui.renderer, &rect);
}

static void format_bytes(char *out, size_t capacity, uint64_t bytes)
{
    if (bytes >= 1024ull * 1024ull * 10ull) {
        snprintf(out, capacity, "%.1f MB", (double)bytes / (1024.0 * 1024.0));
    } else {
        snprintf(out, capacity, "%.0f KB", (double)bytes / 1024.0);
    }
}

/* ------------------------------------------------------------------ */
/* State                                                               */

static void set_status(const char *text, const struct rgb *color)
{
    snprintf(ui.status, sizeof(ui.status), "%s", text ? text : "");
    ui.status_color = color;
}

static void add_button(enum button_kind kind, const char *label,
                       const char *hint, const char *drive, int enabled)
{
    struct button *button;
    if (ui.button_count >= UI_MAX_BUTTONS) return;
    button = &ui.buttons[ui.button_count];
    memset(button, 0, sizeof(*button));
    button->kind = kind;
    snprintf(button->label, sizeof(button->label), "%s", label);
    snprintf(button->hint, sizeof(button->hint), "%s", hint ? hint : "");
    snprintf(button->drive, sizeof(button->drive), "%s", drive ? drive : "");
    button->enabled = enabled;
    button->rect.x = (float)UI_MARGIN;
    button->rect.y = (float)(UI_BUTTONS_TOP +
                             ui.button_count * (UI_BUTTON_HEIGHT + UI_BUTTON_GAP));
    button->rect.w = (float)(UI_WIDTH - 2 * UI_MARGIN);
    button->rect.h = (float)UI_BUTTON_HEIGHT;
    ui.button_count++;
}

/* Only drives that hold a disc are worth a row; one row per drive (the
 * device is listed, its mounted volume is not: c2_cdrom_find_drives). */
static void scan_drives(void)
{
    char present[UI_MAX_DRIVES * 2][C2_CDROM_DRIVE_PATH_CAPACITY];
    int present_count = c2_cdrom_find_drives(present, UI_MAX_DRIVES * 2);
    int i;
    ui.drive_count = 0;
    for (i = 0; i < present_count && ui.drive_count < UI_MAX_DRIVES; i++) {
        enum c2_source_kind kind;
        char root[UI_PATH_CAPACITY];
        present[i][C2_CDROM_DRIVE_PATH_CAPACITY - 1] = '\0';
        if (!c2_cdrom_drive_has_disc(present[i])) continue;
        /* A mounted volume is offered only when it holds the game. */
        if (!c2_cdrom_is_device_path(present[i]) &&
            !c2_import_classify(present[i], &kind, root, sizeof(root), NULL, 0)) continue;
        memcpy(ui.drives[ui.drive_count++], present[i], C2_CDROM_DRIVE_PATH_CAPACITY);
    }
    ui.next_drive_scan = SDL_GetTicks() + UI_DRIVE_RESCAN_MS;
}

static int music_is_windows(const char *choice)
{
    return strcmp(choice, "windows") == 0 || strcmp(choice, "recorded") == 0;
}

static int speech_count(void)
{
    int i;
    int count = 0;
    for (i = 0; i < ui.summary.language_count; i++) count += ui.summary.languages[i].speech != 0;
    return count;
}

/* The speech that plays: the wish, else the text choice, else the pick. */
static const char *active_speech(void)
{
    return c2_library_pick_speech(&ui.summary, ui.speech[0] ? ui.speech : ui.text_language);
}

static const char *language_name(const char *tag, char *out, size_t capacity)
{
    if (strcmp(tag, "und") == 0) {
        snprintf(out, capacity, "unknown language");
        return out;
    }
    return language_label(tag, out, capacity);
}

static void rebuild_buttons(void)
{
    enum button_kind focused_kind = BUTTON_PLAY;
    char label[64];
    char name[48];
    int i;
    if (ui.focus >= 0 && ui.focus < ui.button_count) {
        focused_kind = ui.buttons[ui.focus].kind;
    }
    ui.button_count = 0;
    switch (ui.page) {
    case PAGE_MAIN:
        add_button(BUTTON_PLAY, "Play", "Enter", NULL, ui.summary.playable);
        add_button(BUTTON_DATA, "Game data...",
                   ui.summary.playable ? "" : "add yours here", NULL, 1);
        add_button(BUTTON_SETTINGS, "Settings...", "", NULL, 1);
        add_button(BUTTON_QUIT, "Quit", "Esc", NULL, 1);
        break;
    case PAGE_DATA:
        for (i = 0; i < ui.drive_count; i++) {
            snprintf(label, sizeof(label), "Add the disc in %.*s",
                     (int)sizeof(label) - 18, ui.drives[i]);
            add_button(BUTTON_DRIVE, label, "", ui.drives[i], 1);
        }
        add_button(BUTTON_ADD, "Add game data...", "or drop it here", NULL, 1);
        if (speech_count() > 1) {
            snprintf(label, sizeof(label), "Speech: %s",
                     language_name(active_speech(), name, sizeof(name)));
            add_button(BUTTON_SPEECH, label, "Enter to change", NULL, 1);
        }
        if (ui.summary.music_dos || ui.summary.music_windows) {
            /* Two soundtracks by two composers, each named after the
             * version it was written for: a choice when the data has both,
             * a statement when it has one. */
            int both = ui.summary.music_dos && ui.summary.music_windows;
            int windows = both ? music_is_windows(ui.music_source) : !ui.summary.music_dos;
            add_button(BUTTON_MUSIC,
                       windows ? "Music: Windows version (1996)" : "Music: DOS version (1995)",
                       both ? "Enter to change" : "", NULL, both);
        }
        add_button(BUTTON_EXPORT, "Export game data...", ".c2assets", NULL, ui.summary.playable);
        add_button(BUTTON_REMOVE,
                   ui.confirm_remove ? "Remove all game data?" : "Remove game data...",
                   ui.confirm_remove ? "Enter to remove" : "", NULL,
                   ui.summary.language_count > 0 || ui.summary.bytes > 0);
        ui.buttons[ui.button_count - 1].warning = ui.confirm_remove;
        add_button(BUTTON_BACK, "Back", "Esc", NULL, 1);
        break;
    case PAGE_SETTINGS:
        if (ui.text_language[0]) {
            snprintf(label, sizeof(label), "Text: %s",
                     language_label(ui.text_language, name, sizeof(name)));
        } else if (ui.summary.language_count) {
            snprintf(label, sizeof(label), "Text: Automatic (%s)",
                     language_name(active_speech(), name, sizeof(name)));
        } else {
            snprintf(label, sizeof(label), "Text: Automatic");
        }
        add_button(BUTTON_TEXT, label, "Enter to change", NULL, 1);
        add_button(BUTTON_DISPLAY, ui.fullscreen ? "Display: Fullscreen" : "Display: Windowed",
                   "F11 to toggle", NULL, 1);
        add_button(BUTTON_SCALING,
                   ui.fractional_scaling ? "Scaling: Fractional" : "Scaling: Integer",
                   "F10 to toggle", NULL, 1);
        add_button(BUTTON_BACK, "Back", "Esc", NULL, 1);
        break;
    }
    ui.focus = -1;
    for (i = 0; i < ui.button_count; i++) {
        if (ui.buttons[i].kind == focused_kind && ui.buttons[i].enabled) {
            ui.focus = i;
            break;
        }
    }
    for (i = 0; ui.focus < 0 && i < ui.button_count; i++) {
        if (ui.buttons[i].enabled) ui.focus = i;
    }
    ui.hover = -1;
}

static void refresh_summary(void)
{
    c2_library_describe(ui.game_data_root, &ui.summary);
    /* A speech wish the data cannot grant is dropped, not kept hidden. */
    if (ui.speech[0] && strcmp(active_speech(), ui.speech) != 0) ui.speech[0] = '\0';
}

static void set_page(enum page page)
{
    ui.page = page;
    ui.confirm_remove = 0;
    ui.focus = -1;
    set_status("", &COLOR_MUTED);
    rebuild_buttons();
}

/* Re-list drives while idle so plugging in a USB reader shows up without a
 * restart. Only rebuilds when the set actually changed, to keep focus. */
static void poll_drives(void)
{
    char before[UI_MAX_DRIVES][C2_CDROM_DRIVE_PATH_CAPACITY];
    int before_count = ui.drive_count;
    if (SDL_GetTicks() < ui.next_drive_scan) return;
    memcpy(before, ui.drives, sizeof(before));
    scan_drives();
    if (before_count != ui.drive_count ||
        memcmp(before, ui.drives, sizeof(before)) != 0) {
        rebuild_buttons();
    }
}

/* ------------------------------------------------------------------ */
/* Work: importing, exporting, removing                                */

static void work_progress(void *userdata, const char *phase,
                          uint64_t completed, uint64_t total,
                          size_t completed_files, size_t total_files)
{
    (void)userdata;
    SDL_LockMutex(ui.mutex);
    snprintf(ui.phase, sizeof(ui.phase), "%s", phase ? phase : "Working");
    ui.completed_bytes = completed;
    ui.total_bytes = total;
    ui.completed_files = completed_files;
    ui.total_files = total_files;
    SDL_UnlockMutex(ui.mutex);
}

static int work_main(void *userdata)
{
    struct c2_import_progress progress;
    char error[512];
    int ok = 0;
    (void)userdata;
    progress.update = work_progress;
    progress.userdata = NULL;
    error[0] = '\0';
    switch (ui.job) {
    case JOB_IMPORT:
        ok = c2_library_import(ui.game_data_root, ui.job_path, &progress, error, sizeof(error));
        break;
    case JOB_EXPORT:
        ok = c2_library_export(ui.game_data_root, ui.job_path, &progress, error, sizeof(error));
        break;
    case JOB_REMOVE:
        ok = c2_library_remove(ui.game_data_root);
        if (!ok) snprintf(error, sizeof(error), "some files could not be deleted");
        break;
    }
    SDL_LockMutex(ui.mutex);
    ui.work_ok = ok;
    snprintf(ui.work_error, sizeof(ui.work_error), "%s", error);
    ui.work_done = 1;
    SDL_UnlockMutex(ui.mutex);
    return 0;
}

static void start_work(enum job job, const char *path, const char *phase)
{
    SDL_LockMutex(ui.mutex);
    ui.work_done = 0;
    ui.work_ok = 0;
    ui.work_error[0] = '\0';
    snprintf(ui.phase, sizeof(ui.phase), "%s", phase);
    ui.completed_bytes = ui.total_bytes = 0;
    ui.completed_files = ui.total_files = 0;
    SDL_UnlockMutex(ui.mutex);
    ui.job = job;
    snprintf(ui.job_path, sizeof(ui.job_path), "%s", path ? path : "");
    ui.state = SETUP_WORK;
    ui.confirm_remove = 0;
    set_status("", &COLOR_MUTED);
    ui.thread = SDL_CreateThread(work_main, "caesar2-game-data", NULL);
    if (ui.thread == NULL) {
        ui.state = SETUP_MENU;
        set_status("Could not start the worker thread.", &COLOR_ERROR);
    }
}

static void add_source(const char *path)
{
    start_work(JOB_IMPORT, path, "Reading the game data");
}

static void finish_work(void)
{
    int ok;
    char error[512];
    char message[400];
    int before = ui.summary.language_count;
    int was_playable = ui.summary.playable;
    SDL_WaitThread(ui.thread, NULL);
    ui.thread = NULL;
    SDL_LockMutex(ui.mutex);
    ok = ui.work_ok;
    snprintf(error, sizeof(error), "%s", ui.work_error);
    SDL_UnlockMutex(ui.mutex);
    ui.state = SETUP_MENU;
    if (ui.quit_after_work) {
        ui.result = C2_SETUP_QUIT;
        return;
    }
    refresh_summary();
    switch (ui.job) {
    case JOB_IMPORT:
        if (!ok) {
            snprintf(message, sizeof(message), "Could not add that: %.300s", error);
            set_status(message, &COLOR_ERROR);
        } else if (!ui.summary.playable) {
            set_status("Added, but this is not enough to play: add a PC installation or disc.",
                       &COLOR_ERROR);
        } else {
            set_status(ui.summary.language_count > before ? "Added. Press Play to start."
                                                          : "Added what was new or better.",
                       &COLOR_OK);
        }
        break;
    case JOB_EXPORT:
        if (ok) {
            snprintf(message, sizeof(message), "Exported to %s", ui.job_path);
            set_status(message, &COLOR_OK);
        } else {
            snprintf(message, sizeof(message), "Export failed: %.300s", error);
            set_status(message, &COLOR_ERROR);
        }
        break;
    case JOB_REMOVE:
        set_status(ok ? "Game data removed. Saves and settings were kept."
                      : "Some game data could not be removed.",
                   ok ? &COLOR_OK : &COLOR_ERROR);
        break;
    }
    /* Just became playable: Enter starts the game. */
    if (ui.summary.playable && !was_playable && ui.page == PAGE_MAIN) ui.focus = -1;
    rebuild_buttons();
}

/* ------------------------------------------------------------------ */
/* Dialogs                                                             */

static void SDLCALL dialog_closed(void *userdata,
                                  const char *const *filelist, int filter)
{
    (void)userdata;
    (void)filter;
    SDL_LockMutex(ui.mutex);
    ui.dialog_path[0] = '\0';
    if (filelist != NULL && filelist[0] != NULL) {
        snprintf(ui.dialog_path, sizeof(ui.dialog_path), "%s", filelist[0]);
    }
    ui.dialog_done = 1;
    SDL_UnlockMutex(ui.mutex);
}

static void open_dialog(enum dialog kind)
{
    /* One dialog for everything. A file inside an installation (C2.ENG,
     * CAESAR2.EXE, ...) adds that installation. */
    static const SDL_DialogFileFilter add_filters[] = {
        { "Caesar II game data (C2.ENG, ISO, BIN, CUE, Toast, ZIP, C2ASSETS)",
          "eng;exe;iso;bin;cue;img;toast;cdr;zip;c2assets" },
        { "All files", "*" }
    };
    static const SDL_DialogFileFilter export_filters[] = {
        { "Caesar II game data", "c2assets" }
    };
    SDL_LockMutex(ui.mutex);
    ui.dialog_done = 0;
    ui.dialog_path[0] = '\0';
    SDL_UnlockMutex(ui.mutex);
    ui.dialog_kind = kind;
    ui.state = SETUP_DIALOG;
    set_status("", &COLOR_MUTED);
    if (kind == DIALOG_EXPORT) {
        SDL_ShowSaveFileDialog(dialog_closed, NULL, ui.window, export_filters, 1,
                               "caesar2.c2assets");
    } else {
        SDL_ShowOpenFileDialog(dialog_closed, NULL, ui.window, add_filters, 2, NULL, false);
    }
}

static void finish_dialog(void)
{
    char path[UI_PATH_CAPACITY];
    SDL_LockMutex(ui.mutex);
    snprintf(path, sizeof(path), "%s", ui.dialog_path);
    SDL_UnlockMutex(ui.mutex);
    ui.state = SETUP_MENU;
    if (path[0] == '\0') {
        rebuild_buttons();
        return;
    }
    if (ui.dialog_kind == DIALOG_EXPORT) {
        size_t n = strlen(path);
        if (n < 9 || SDL_strcasecmp(path + n - 9, ".c2assets") != 0) {
            if (n + 9 < sizeof(path)) strcat(path, ".c2assets");
        }
        start_work(JOB_EXPORT, path, "Writing the game-data archive");
    } else {
        add_source(path);
    }
}

/* ------------------------------------------------------------------ */
/* Input                                                               */

static void cycle_speech(void)
{
    const char *current = active_speech();
    int i;
    int start = -1;
    for (i = 0; i < ui.summary.language_count; i++) {
        if (strcmp(ui.summary.languages[i].tag, current) == 0) start = i;
    }
    for (i = 1; i <= ui.summary.language_count; i++) {
        const struct c2_library_language *l =
            &ui.summary.languages[(start + i) % ui.summary.language_count];
        if (l->speech) {
            snprintf(ui.speech, sizeof(ui.speech), "%s", l->tag);
            break;
        }
    }
}

static void activate(int index)
{
    struct button *button;
    if (index < 0 || index >= ui.button_count) return;
    button = &ui.buttons[index];
    if (!button->enabled || ui.state != SETUP_MENU) return;
    if (button->kind != BUTTON_REMOVE) ui.confirm_remove = 0;
    switch (button->kind) {
    case BUTTON_PLAY:
        ui.result = C2_SETUP_PLAY;
        break;
    case BUTTON_DATA:
        set_page(PAGE_DATA);
        break;
    case BUTTON_SETTINGS:
        set_page(PAGE_SETTINGS);
        break;
    case BUTTON_BACK:
        set_page(PAGE_MAIN);
        break;
    case BUTTON_QUIT:
        ui.result = C2_SETUP_QUIT;
        break;
    case BUTTON_DRIVE:
        add_source(button->drive);
        break;
    case BUTTON_ADD:
        open_dialog(DIALOG_ADD);
        break;
    case BUTTON_EXPORT:
        open_dialog(DIALOG_EXPORT);
        break;
    case BUTTON_REMOVE:
        if (!ui.confirm_remove) {
            ui.confirm_remove = 1;
            set_status("Saves and settings are kept. Press Enter again to remove.", &COLOR_ERROR);
            rebuild_buttons();
        } else {
            start_work(JOB_REMOVE, NULL, "Removing game data");
        }
        break;
    case BUTTON_SPEECH:
        cycle_speech();
        rebuild_buttons();
        break;
    case BUTTON_MUSIC:
        snprintf(ui.music_source, sizeof(ui.music_source), "%s",
                 music_is_windows(ui.music_source) ? "dos" : "windows");
        rebuild_buttons();
        break;
    case BUTTON_TEXT: {
        /* Automatic, then each compiled-in language, then Automatic again. */
        int i;
        int current = -1;
        int count = c2_port_text_language_count();
        for (i = 0; i < count; i++) {
            if (strcmp(c2_port_text_language(i)->tag, ui.text_language) == 0) current = i;
        }
        if (current + 1 < count) {
            snprintf(ui.text_language, sizeof(ui.text_language), "%s",
                     c2_port_text_language(current + 1)->tag);
        } else {
            ui.text_language[0] = '\0';
        }
        rebuild_buttons();
        break;
    }
    case BUTTON_DISPLAY:
        ui.fullscreen = !ui.fullscreen;
        rebuild_buttons();
        break;
    case BUTTON_SCALING:
        ui.fractional_scaling = !ui.fractional_scaling;
        rebuild_buttons();
        break;
    }
}

static void move_focus(int direction)
{
    int i;
    int index = ui.focus;
    for (i = 0; i < ui.button_count; i++) {
        index = (index + direction + ui.button_count) % ui.button_count;
        if (ui.buttons[index].enabled) {
            if (ui.confirm_remove && ui.buttons[index].kind != BUTTON_REMOVE) {
                ui.confirm_remove = 0;
                set_status("", &COLOR_MUTED);
                ui.focus = index;
                rebuild_buttons();
                return;
            }
            ui.focus = index;
            return;
        }
    }
}

static int button_at(float x, float y)
{
    int i;
    for (i = 0; i < ui.button_count; i++) {
        const SDL_FRect *r = &ui.buttons[i].rect;
        if (x >= r->x && x < r->x + r->w && y >= r->y && y < r->y + r->h) {
            return i;
        }
    }
    return -1;
}

static void request_quit(void)
{
    if (ui.state == SETUP_WORK) {
        ui.quit_after_work = 1;
    } else {
        ui.result = C2_SETUP_QUIT;
    }
}

static void go_back(void)
{
    if (ui.confirm_remove) {
        ui.confirm_remove = 0;
        set_status("", &COLOR_MUTED);
        rebuild_buttons();
    } else if (ui.page != PAGE_MAIN) {
        set_page(PAGE_MAIN);
    } else {
        request_quit();
    }
}

void c2_setup_handle_event(const SDL_Event *event)
{
    SDL_Event converted;
    if (!ui.open) return;
    switch (event->type) {
    case SDL_EVENT_QUIT:
    case SDL_EVENT_WINDOW_CLOSE_REQUESTED:
        request_quit();
        break;
    case SDL_EVENT_DROP_FILE:
        if (ui.state == SETUP_MENU && event->drop.data) add_source(event->drop.data);
        break;
    case SDL_EVENT_KEY_DOWN:
        if (ui.state != SETUP_MENU) break;
        switch (event->key.key) {
        case SDLK_UP:
            move_focus(-1);
            break;
        case SDLK_DOWN:
            move_focus(1);
            break;
        case SDLK_TAB:
            move_focus((event->key.mod & SDL_KMOD_SHIFT) ? -1 : 1);
            break;
        case SDLK_RETURN:
        case SDLK_KP_ENTER:
        case SDLK_SPACE:
            activate(ui.focus);
            break;
        case SDLK_ESCAPE:
        case SDLK_BACKSPACE:
            go_back();
            break;
        case SDLK_F11:
            ui.fullscreen = !ui.fullscreen;
            rebuild_buttons();
            break;
        case SDLK_F10:
            ui.fractional_scaling = !ui.fractional_scaling;
            rebuild_buttons();
            break;
        default:
            break;
        }
        break;
    case SDL_EVENT_MOUSE_MOTION:
        converted = *event;
        SDL_ConvertEventToRenderCoordinates(ui.renderer, &converted);
        ui.hover = button_at(converted.motion.x, converted.motion.y);
        if (ui.hover >= 0 && ui.buttons[ui.hover].enabled) ui.focus = ui.hover;
        break;
    case SDL_EVENT_MOUSE_BUTTON_DOWN:
        if (event->button.button != SDL_BUTTON_LEFT) break;
        converted = *event;
        SDL_ConvertEventToRenderCoordinates(ui.renderer, &converted);
        activate(button_at(converted.button.x, converted.button.y));
        break;
    default:
        break;
    }
}

/* ------------------------------------------------------------------ */
/* Rendering                                                           */

/* What the game data holds, one fact per line, as c2_library reports it. */
static int summary_lines(char lines[UI_INFO_LINES][96], const struct rgb *colors[UI_INFO_LINES])
{
    int n = 0;
    int i;
    char names[80];
    size_t used = 0;
    const struct c2_library_summary *s = &ui.summary;

    if (s->language_count == 0) {
        snprintf(lines[n], 96, "None yet. Add an installed folder, a disc image");
        colors[n++] = &COLOR_MUTED;
        snprintf(lines[n], 96, "(ISO, BIN/CUE, Mac Toast), a ZIP or .c2assets,");
        colors[n++] = &COLOR_MUTED;
        snprintf(lines[n], 96, "or insert the CD. Drop any of them on this window.");
        colors[n++] = &COLOR_MUTED;
        return n;
    }
    names[0] = '\0';
    for (i = 0; i < s->language_count; i++) {
        char name[48];
        if (!s->languages[i].speech) continue;
        language_name(s->languages[i].tag, name, sizeof(name));
        used += (size_t)snprintf(names + used, sizeof(names) - used, "%s%s",
                                 used ? ", " : "", name);
        if (used >= sizeof(names)) break;
    }
    snprintf(lines[n], 96, "Speech: %s", names[0] ? names : "none");
    colors[n++] = names[0] ? &COLOR_TEXT : &COLOR_ERROR;
    snprintf(lines[n], 96, "Music: %s",
             s->music_dos && s->music_windows ? "DOS (1995) and Windows (1996)"
             : s->music_dos ? "DOS (1995)"
             : s->music_windows ? "Windows (1996)" : "none");
    colors[n++] = s->music_dos || s->music_windows ? &COLOR_TEXT : &COLOR_ERROR;
    if (s->movies_enhanced) {
        snprintf(lines[n], 96, "Movies: %d, %d of them larger than the originals",
                 s->movies, s->movies_enhanced);
    } else {
        snprintf(lines[n], 96, "Movies: %d", s->movies);
    }
    colors[n++] = s->movies ? &COLOR_TEXT : &COLOR_ERROR;
    if (!s->playable) {
        snprintf(lines[n], 96, "Not enough to play: add a PC installation or disc.");
        colors[n++] = &COLOR_ERROR;
    } else if (ui.page == PAGE_DATA) {
        char size[32];
        const char *speech = active_speech();
        char version[64] = "";
        for (i = 0; i < s->language_count; i++) {
            if (strcmp(s->languages[i].tag, speech) == 0) {
                snprintf(version, sizeof(version), "%s", s->languages[i].version);
            }
        }
        format_bytes(size, sizeof(size), s->bytes);
        snprintf(lines[n], 96, "%s%s%s on disk", version, version[0] ? ", " : "", size);
        colors[n++] = &COLOR_MUTED;
    }
    return n;
}

static void render_menu(void)
{
    int i;
    for (i = 0; i < ui.button_count; i++) {
        const struct button *button = &ui.buttons[i];
        const struct rgb *fill = !button->enabled ? &COLOR_BUTTON_DISABLED
                               : i == ui.hover ? &COLOR_BUTTON_HOVER
                               : &COLOR_BUTTON;
        const struct rgb *text = !button->enabled ? &COLOR_MUTED
                               : button->warning ? &COLOR_ERROR : &COLOR_TEXT;
        int x = (int)button->rect.x;
        int y = (int)button->rect.y;
        int w = (int)button->rect.w;
        int h = (int)button->rect.h;
        fill_rect(x, y, w, h, fill);
        if (i == ui.focus && ui.state == SETUP_MENU) {
            outline_rect(x, y, w, h, button->warning ? &COLOR_ERROR : &COLOR_FOCUS);
        }
        draw_text(x + 10, y + (h - UI_GLYPH) / 2, 1, text, button->label);
        if (button->hint[0]) {
            draw_text(x + w - 10 - text_width(button->hint, 1),
                      y + (h - UI_GLYPH) / 2, 1, &COLOR_MUTED, button->hint);
        }
    }
}

static void draw_key_table(int x, int y, int key_width, const char *heading,
                           const char *const (*rows)[2], size_t count)
{
    size_t i;
    draw_text(x, y, 1, &COLOR_MUTED, heading);
    for (i = 0; i < count; i++) {
        draw_text(x, y + 14 + (int)i * 12, 1, &COLOR_TEXT, rows[i][0]);
        draw_text(x + key_width * UI_GLYPH, y + 14 + (int)i * 12, 1, &COLOR_MUTED, rows[i][1]);
    }
}

/*
 * Key tables under a rule: what the game answers to (on the main and
 * settings pages), and how this window is driven. Keys in text colour,
 * meanings muted.
 */
static void render_key_reference(void)
{
    static const char *const game_keys[][2] = {
        { "F11",       "Fullscreen" },
        { "F10",       "Scaling mode" },
        { "Ctrl+1..5", "Window size 1x..5x" },
        { "Ctrl+0",    "Largest that fits" },
    };
    static const char *const main_keys[][2] = {
        { "Arrows, Tab", "Move" },
        { "Enter",       "Select" },
        { "Esc",         "Quit" },
    };
    static const char *const page_keys[][2] = {
        { "Arrows, Tab", "Move" },
        { "Enter",       "Select" },
        { "Esc",         "Back" },
    };
    const int top = UI_LEGEND_TOP + 4;
    const int right = UI_WIDTH / 2 + 24;

    fill_rect(UI_MARGIN, top, UI_WIDTH - 2 * UI_MARGIN, 1, &COLOR_RULE);
    if (ui.page == PAGE_DATA) {
        draw_key_table(UI_MARGIN, top + 8, 13, "This window", page_keys,
                       sizeof(page_keys) / sizeof(page_keys[0]));
        draw_text(right, top + 8, 1, &COLOR_MUTED, "Drop a folder, image,");
        draw_text(right, top + 22, 1, &COLOR_MUTED, "ZIP or .c2assets on");
        draw_text(right, top + 34, 1, &COLOR_MUTED, "this window to add it.");
        return;
    }
    draw_key_table(UI_MARGIN, top + 8, 11, "In game", game_keys,
                   sizeof(game_keys) / sizeof(game_keys[0]));
    if (ui.page == PAGE_MAIN) {
        draw_key_table(right, top + 8, 13, "This window", main_keys,
                       sizeof(main_keys) / sizeof(main_keys[0]));
    } else {
        draw_key_table(right, top + 8, 13, "This window", page_keys,
                       sizeof(page_keys) / sizeof(page_keys[0]));
    }
}

static void render_work(void)
{
    char phase[64];
    char line[128];
    char done[32];
    char total[32];
    uint64_t completed_bytes;
    uint64_t total_bytes;
    size_t completed_files;
    size_t total_files;
    int bar_x = UI_MARGIN;
    int bar_y = UI_BUTTONS_TOP + 40;
    int bar_w = UI_WIDTH - 2 * UI_MARGIN;
    int bar_h = 14;
    int filled;

    SDL_LockMutex(ui.mutex);
    snprintf(phase, sizeof(phase), "%s", ui.phase);
    completed_bytes = ui.completed_bytes;
    total_bytes = ui.total_bytes;
    completed_files = ui.completed_files;
    total_files = ui.total_files;
    SDL_UnlockMutex(ui.mutex);

    draw_text(UI_MARGIN, UI_BUTTONS_TOP + 12, 1, &COLOR_TEXT, phase);
    fill_rect(bar_x, bar_y, bar_w, bar_h, &COLOR_BAR_BACK);
    if (total_bytes > 0) {
        filled = (int)((double)bar_w * (double)completed_bytes / (double)total_bytes);
        if (filled > bar_w) filled = bar_w;
        fill_rect(bar_x, bar_y, filled, bar_h, &COLOR_BAR);
        format_bytes(done, sizeof(done), completed_bytes);
        format_bytes(total, sizeof(total), total_bytes);
        snprintf(line, sizeof(line), "%s / %s   %u / %u files",
                 done, total, (unsigned)completed_files, (unsigned)total_files);
    } else {
        /* Indeterminate: cataloguing, or removing. */
        int sweep = (int)((SDL_GetTicks() / 8) % (Uint64)(bar_w + 60)) - 60;
        int x0 = sweep < 0 ? bar_x : bar_x + sweep;
        int x1 = bar_x + sweep + 60;
        if (x1 > bar_x + bar_w) x1 = bar_x + bar_w;
        if (x1 > x0) fill_rect(x0, bar_y, x1 - x0, bar_h, &COLOR_BAR);
        snprintf(line, sizeof(line), "Please wait...");
    }
    outline_rect(bar_x, bar_y, bar_w, bar_h, &COLOR_RULE);
    draw_text(UI_MARGIN, bar_y + bar_h + 12, 1, &COLOR_MUTED, line);
    if (ui.quit_after_work) {
        draw_text(UI_MARGIN, bar_y + bar_h + 36, 1, &COLOR_ERROR,
                  "Quitting once this has finished.");
    } else if (ui.job == JOB_IMPORT) {
        draw_text(UI_MARGIN, bar_y + bar_h + 36, 1, &COLOR_MUTED,
                  "Only what is new or better is kept.");
    }
}

static void render(void)
{
    char line[160];
    char shown[128];
    char lines[UI_INFO_LINES][96];
    const struct rgb *colors[UI_INFO_LINES];
    const int max_chars = (UI_WIDTH - 2 * UI_MARGIN) / UI_GLYPH;
    int count;
    int i;

    SDL_SetRenderDrawColor(ui.renderer, COLOR_BACKGROUND.r, COLOR_BACKGROUND.g,
                           COLOR_BACKGROUND.b, 255);
    SDL_RenderClear(ui.renderer);

    draw_text(UI_MARGIN, 14, 2, &COLOR_TITLE, "CAESAR II");
    snprintf(line, sizeof(line), "Second Impressions port %s", ui.version);
    draw_text(UI_MARGIN, 36, 1, &COLOR_MUTED, line);
    fill_rect(UI_MARGIN, 52, UI_WIDTH - 2 * UI_MARGIN, 1, &COLOR_RULE);

    draw_text(UI_MARGIN, UI_INFO_TOP - UI_LINE, 1, &COLOR_MUTED,
              ui.page == PAGE_SETTINGS ? "Settings" : "Game data");
    if (ui.page != PAGE_SETTINGS) {
        count = summary_lines(lines, colors);
        for (i = 0; i < count; i++) {
            fit_text(shown, sizeof(shown), lines[i], max_chars);
            draw_text(UI_MARGIN, UI_INFO_TOP + i * UI_LINE, 1, colors[i], shown);
        }
    } else {
        draw_text(UI_MARGIN, UI_INFO_TOP, 1, &COLOR_MUTED,
                  "Text is built in; speech and pictures come from");
        draw_text(UI_MARGIN, UI_INFO_TOP + UI_LINE, 1, &COLOR_MUTED,
                  "the game data. Automatic follows the speech.");
    }
    if (ui.status[0]) {
        /* The status may end in a path (an export, a crash report): keep
         * its tail. */
        fit_path(shown, sizeof(shown), ui.status, max_chars);
        draw_text(UI_MARGIN, UI_STATUS_TOP, 1, ui.status_color, shown);
    }

    if (ui.state == SETUP_WORK) {
        render_work();
    } else {
        render_menu();
        if (ui.state == SETUP_DIALOG) {
            draw_text(UI_MARGIN, UI_STATUS_TOP, 1, &COLOR_MUTED,
                      "Waiting for the file dialog...");
        }
        render_key_reference();
    }
    SDL_RenderPresent(ui.renderer);
}

/* ------------------------------------------------------------------ */
/* Lifecycle                                                           */

static void fit_window(int logical_width, int logical_height, int preferred,
                       int *width, int *height)
{
    SDL_Rect usable;
    SDL_DisplayID display = SDL_GetPrimaryDisplay();
    float scale = (float)preferred;
    if (display != 0 && SDL_GetDisplayUsableBounds(display, &usable)) {
        float fit_x = (float)(usable.w - 16) / (float)logical_width;
        float fit_y = (float)(usable.h - 48) / (float)logical_height;
        if (fit_x < scale) scale = fit_x;
        if (fit_y < scale) scale = fit_y;
        if (scale < 1.0f) scale = 1.0f;
    }
    *width = (int)((float)logical_width * scale);
    *height = (int)((float)logical_height * scale);
}

int c2_setup_open(const struct c2_setup_config *config)
{
    char title[128];
    int width;
    int height;
    SDL_Mutex *mutex;
    const char *page;
    if (ui.open) return 1;
    /* The mutex outlives close(): a native file dialog that is still open
     * when the launcher is torn down may deliver its callback later, and it
     * must find valid state to write into. */
    mutex = ui.mutex;
    memset(&ui, 0, sizeof(ui));
    ui.mutex = mutex ? mutex : SDL_CreateMutex();
    ui.focus = -1;
    ui.hover = -1;
    snprintf(ui.version, sizeof(ui.version), "%s", config->version ? config->version : "");
    snprintf(ui.game_data_root, sizeof(ui.game_data_root), "%s",
             config->game_data_root ? config->game_data_root : "game-data");
    snprintf(ui.speech, sizeof(ui.speech), "%s", config->speech ? config->speech : "");
    snprintf(ui.text_language, sizeof(ui.text_language), "%s",
             config->text_language ? config->text_language : "");
    snprintf(ui.music_source, sizeof(ui.music_source), "%s",
             config->music_source ? config->music_source : "");
    ui.fullscreen = config->fullscreen != 0;
    ui.fractional_scaling = config->fractional_scaling != 0;

    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) {
        fprintf(stderr, "launcher: SDL video initialization failed: %s\n", SDL_GetError());
        return 0;
    }
    snprintf(title, sizeof(title), "Caesar II %s", ui.version);
    /* The launcher letterboxes, so it can shrink to whatever fits a small
     * logical desktop (a HiDPI laptop at 200%) without integer steps. */
    fit_window(UI_WIDTH, UI_HEIGHT, UI_SCALE, &width, &height);
    if (!SDL_CreateWindowAndRenderer(title, width, height,
                                     SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY,
                                     &ui.window, &ui.renderer)) {
        fprintf(stderr, "launcher: window creation failed: %s\n", SDL_GetError());
        SDL_QuitSubSystem(SDL_INIT_VIDEO | SDL_INIT_EVENTS);
        return 0;
    }
    c2_sdl_set_window_icon(ui.window);
    SDL_SetRenderLogicalPresentation(ui.renderer, UI_WIDTH, UI_HEIGHT,
                                     SDL_LOGICAL_PRESENTATION_LETTERBOX);
    ui.font = build_font(ui.renderer);
    if (ui.font == NULL || ui.mutex == NULL) {
        fprintf(stderr, "launcher: setup failed: %s\n", SDL_GetError());
        SDL_DestroyTexture(ui.font);
        SDL_DestroyRenderer(ui.renderer);
        SDL_DestroyWindow(ui.window);
        SDL_QuitSubSystem(SDL_INIT_VIDEO | SDL_INIT_EVENTS);
        ui.font = NULL;
        ui.renderer = NULL;
        ui.window = NULL;
        return 0;
    }
    SDL_SetHint(SDL_HINT_MAIN_CALLBACK_RATE, "60");
    ui.open = 1;
    ui.state = SETUP_MENU;
    ui.result = C2_SETUP_RUNNING;
    ui.status_color = &COLOR_MUTED;
    /* C2_SETUP_PAGE=data|settings opens on that page (screenshots). */
    page = SDL_getenv("C2_SETUP_PAGE");
    ui.page = page && strcmp(page, "data") == 0 ? PAGE_DATA
            : page && strcmp(page, "settings") == 0 ? PAGE_SETTINGS : PAGE_MAIN;
    scan_drives();
    refresh_summary();
    rebuild_buttons();
    if (config->error && config->error[0]) {
        set_status(config->error, &COLOR_ERROR);
    }
    if (config->pending_source && config->pending_source[0]) {
        add_source(config->pending_source);
    }
    render();
    return 1;
}

/* C2_SETUP_SCREENSHOT=<file> saves the launcher's first idle frame as a PNG
 * and quits: how the layout is looked at without a desktop (with
 * SDL_VIDEODRIVER=dummy), and what tests/screenshots of the launcher use. */
static void capture_frame_if_asked(void)
{
    const char *filename = SDL_getenv("C2_SETUP_SCREENSHOT");
    SDL_Surface *frame;
    if (filename == NULL || filename[0] == '\0') return;
    frame = SDL_RenderReadPixels(ui.renderer, NULL);
    if (frame != NULL) {
        if (!SDL_SavePNG(frame, filename)) {
            SDL_Log("could not write %s: %s", filename, SDL_GetError());
        }
        SDL_DestroySurface(frame);
    }
    ui.result = C2_SETUP_QUIT;
}

enum c2_setup_result c2_setup_iterate(void)
{
    if (!ui.open) return C2_SETUP_QUIT;
    if (ui.state == SETUP_WORK) {
        int done;
        SDL_LockMutex(ui.mutex);
        done = ui.work_done;
        SDL_UnlockMutex(ui.mutex);
        if (done) finish_work();
    } else if (ui.state == SETUP_DIALOG) {
        int done;
        SDL_LockMutex(ui.mutex);
        done = ui.dialog_done;
        SDL_UnlockMutex(ui.mutex);
        if (done) finish_dialog();
    } else {
        poll_drives();
    }
    if (ui.result == C2_SETUP_RUNNING) render();
    if (ui.result == C2_SETUP_RUNNING && ui.state == SETUP_MENU) {
        capture_frame_if_asked();
    }
    return ui.result;
}

const char *c2_setup_selected_speech(void)
{
    return ui.speech;
}

const char *c2_setup_selected_text_language(void)
{
    return ui.text_language;
}

const char *c2_setup_selected_music_source(void)
{
    return ui.music_source;
}

int c2_setup_selected_fullscreen(void)
{
    return ui.fullscreen;
}

int c2_setup_selected_fractional_scaling(void)
{
    return ui.fractional_scaling;
}

void c2_setup_close(void)
{
    if (!ui.open) return;
    if (ui.thread != NULL) {
        SDL_WaitThread(ui.thread, NULL);
        ui.thread = NULL;
    }
    SDL_DestroyTexture(ui.font);
    SDL_DestroyRenderer(ui.renderer);
    SDL_DestroyWindow(ui.window);
    ui.font = NULL;
    ui.renderer = NULL;
    ui.window = NULL;
    ui.open = 0;
    /* The video subsystem stays up on purpose: the host's SDL_Init only
     * bumps the reference and SDL_Quit at exit tears everything down.
     * Re-initialising video in between would reload libdecor on Wayland,
     * whose GTK plugin then complains that GTK was already initialised
     * ("gtk_disable_setlocale() must be called before gtk_init()"). */
}

#else /* PORT_PLATFORM_WASM */

int c2_setup_open(const struct c2_setup_config *config) { (void)config; return 0; }
void c2_setup_handle_event(const SDL_Event *event) { (void)event; }
enum c2_setup_result c2_setup_iterate(void) { return C2_SETUP_QUIT; }
const char *c2_setup_selected_speech(void) { return ""; }
const char *c2_setup_selected_text_language(void) { return ""; }
const char *c2_setup_selected_music_source(void) { return ""; }
int c2_setup_selected_fullscreen(void) { return 0; }
int c2_setup_selected_fractional_scaling(void) { return 0; }
void c2_setup_close(void) {}

#endif
