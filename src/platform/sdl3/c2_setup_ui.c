#include "c2_setup_ui.h"

#if !PORT_PLATFORM_WASM

#include "c2_import.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Public-domain 8x8 glyphs (Daniel Hepper / Marcel Sondaar / IBM VGA). */
#include "font8x8/font8x8_basic.h"

#define UI_WIDTH 480
#define UI_HEIGHT 356
#define UI_SCALE 2
#define UI_MARGIN 16
#define UI_GLYPH 8
#define UI_BUTTON_HEIGHT 22
#define UI_BUTTON_GAP 6
#define UI_BUTTONS_TOP 112
#define UI_MAX_BUTTONS 12
#define UI_MAX_DRIVES 2
#define UI_PATH_CAPACITY 4096

enum setup_state {
    SETUP_MENU = 0,
    SETUP_DIALOG,
    SETUP_IMPORT
};

enum button_kind {
    BUTTON_PLAY = 0,
    BUTTON_LANGUAGE,
    BUTTON_DISPLAY,
    BUTTON_SCALING,
    BUTTON_CHOOSE,
    BUTTON_DRIVE,
    BUTTON_QUIT
};

struct button {
    enum button_kind kind;
    char label[64];
    char hint[32];
    char drive[C2_CDROM_DRIVE_PATH_CAPACITY];
    int enabled;
    SDL_FRect rect;
};

static const char *profile_label(const char *tag);

/* Optical drives come and go (USB readers); poll while the menu is idle. */
#define UI_DRIVE_RESCAN_MS 2000

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
    enum c2_setup_result result;
    int quit_after_import;

    char version[64];
    char source[UI_PATH_CAPACITY];
    char source_kind[64];     /* "Installation folder", "CD-ROM drive /dev/sr0" */
    char detected[128];       /* c2.eng version + release date, once imported */
    char media_note[96];      /* "no music or speech files", when so */
    int startup_check;        /* silent validation of the preselected source */
    char cache_root[UI_PATH_CAPACITY];
    char asset_profile[128];
    char profiles[8][32];     /* from C2PACK.IDX when the data is a pack */
    int profile_count;
    int fullscreen;
    int fractional_scaling;
    char status[256];
    const struct rgb *status_color;
    int source_ready;

    struct button buttons[UI_MAX_BUTTONS];
    int button_count;
    int focus;
    int hover;
    char drives[UI_MAX_DRIVES][C2_CDROM_DRIVE_PATH_CAPACITY];
    int drive_count;
    Uint64 next_drive_scan;

    /* Dialog callback state (written from SDL's dialog thread). */
    int dialog_done;
    char dialog_path[UI_PATH_CAPACITY];

    /* Import worker state (written from the import thread). */
    SDL_Thread *thread;
    int play_after_import;
    char phase[64];
    uint64_t completed_bytes;
    uint64_t total_bytes;
    size_t completed_files;
    size_t total_files;
    int import_done;
    int import_ok;
    char import_error[512];
    char resolved[UI_PATH_CAPACITY];
} ui;

/* ------------------------------------------------------------------ */
/* Layout probe                                                        */

struct child_probe {
    const char *wanted;
    char found[512];
};

static SDL_EnumerationResult SDLCALL probe_child(void *userdata,
                                                 const char *dirname,
                                                 const char *fname)
{
    struct child_probe *probe = userdata;
    (void)dirname;
    if (SDL_strcasecmp(fname, probe->wanted) == 0) {
        snprintf(probe->found, sizeof(probe->found), "%s", fname);
        return SDL_ENUM_SUCCESS;
    }
    return SDL_ENUM_CONTINUE;
}

static int child_path(char *out, size_t capacity, const char *directory,
                      const char *name, SDL_PathType wanted_type)
{
    struct child_probe probe;
    SDL_PathInfo info;
    size_t n = strlen(directory);
    probe.wanted = name;
    probe.found[0] = '\0';
    SDL_EnumerateDirectory(directory, probe_child, &probe);
    if (!probe.found[0]) return 0;
    if (snprintf(out, capacity, "%s%s%s", directory,
                 n && (directory[n - 1] == '/' || directory[n - 1] == '\\') ? "" : "/",
                 probe.found) >= (int)capacity) return 0;
    return SDL_GetPathInfo(out, &info) && info.type == wanted_type;
}

int c2_setup_source_looks_valid(const char *path)
{
    enum c2_source_kind kind;
    char root[UI_PATH_CAPACITY];
    char a[UI_PATH_CAPACITY];
    if (path == NULL || path[0] == '\0') return 0;
    /* An already-activated cache/pack directory only carries the object
     * map; the classifier looks for installation layouts. */
    if (child_path(a, sizeof(a), path, ".c2-object-map", SDL_PATHTYPE_FILE)) return 1;
    return c2_import_classify(path, &kind, root, sizeof(root), NULL, 0);
}

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

/* Keep the informative tail of a long path visible. */
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

/* Only drives that currently hold a disc are worth a row. */
static void scan_drives(void)
{
    char present[UI_MAX_DRIVES][C2_CDROM_DRIVE_PATH_CAPACITY];
    int present_count = c2_cdrom_find_drives(present, UI_MAX_DRIVES);
    int i;
    ui.drive_count = 0;
    for (i = 0; i < present_count; i++) {
        present[i][C2_CDROM_DRIVE_PATH_CAPACITY - 1] = '\0';
        if (!c2_cdrom_drive_has_disc(present[i])) continue;
        memcpy(ui.drives[ui.drive_count++], present[i],
               C2_CDROM_DRIVE_PATH_CAPACITY);
    }
    ui.next_drive_scan = SDL_GetTicks() + UI_DRIVE_RESCAN_MS;
}

/* The user never has to say what kind of data they have: one chooser
 * accepts a file inside an installation, a disc image, a ZIP or a pack and
 * the importer classifies it; inserted discs are offered automatically. */
static void rebuild_buttons(void)
{
    enum button_kind focused_kind = BUTTON_PLAY;
    int i;
    if (ui.focus >= 0 && ui.focus < ui.button_count) {
        focused_kind = ui.buttons[ui.focus].kind;
    }
    ui.button_count = 0;
    add_button(BUTTON_PLAY, "Play", "Enter", NULL, ui.source_ready);
    if (ui.profile_count > 1) {
        char label[64];
        snprintf(label, sizeof(label), "Language: %s", profile_label(ui.asset_profile));
        add_button(BUTTON_LANGUAGE, label, "Enter to change", NULL, 1);
    }
    add_button(BUTTON_DISPLAY,
               ui.fullscreen ? "Display: Fullscreen" : "Display: Windowed",
               "F11 in game", NULL, 1);
    add_button(BUTTON_SCALING,
               ui.fractional_scaling ? "Scaling: Fractional (fills the window)"
                                     : "Scaling: Integer (square pixels)",
               "", NULL, 1);
    add_button(BUTTON_CHOOSE, ui.source_ready ? "Replace game data..."
                                              : "Choose game data...",
               "", NULL, 1);
    for (i = 0; i < ui.drive_count; i++) {
        char label[64];
        snprintf(label, sizeof(label), "Use the disc in %.*s",
                 C2_CDROM_DRIVE_PATH_CAPACITY - 1, ui.drives[i]);
        add_button(BUTTON_DRIVE, label, "", ui.drives[i], 1);
    }
    add_button(BUTTON_QUIT, "Quit", "Esc", NULL, 1);
    ui.focus = -1;
    for (i = 0; i < ui.button_count; i++) {
        if (ui.buttons[i].kind == focused_kind && ui.buttons[i].enabled) {
            ui.focus = i;
            break;
        }
    }
    if (ui.focus < 0) ui.focus = ui.source_ready ? 0 : 1;
    ui.hover = -1;
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
/* Source description                                                  */

static int extension_is(const char *path, const char *extension)
{
    const char *dot = strrchr(path, '.');
    return dot && SDL_strcasecmp(dot, extension) == 0;
}

static void describe_source_kind(void)
{
    char probe[UI_PATH_CAPACITY];
    char root[UI_PATH_CAPACITY];
    enum c2_source_kind kind;
    ui.source_kind[0] = '\0';
    if (!ui.source[0]) return;
    if (child_path(probe, sizeof(probe), ui.source, ".c2-object-map", SDL_PATHTYPE_FILE)) {
        snprintf(ui.source_kind, sizeof(ui.source_kind), "Asset pack");
        return;
    }
    if (!c2_import_classify(ui.source, &kind, root, sizeof(root), NULL, 0)) {
        snprintf(ui.source_kind, sizeof(ui.source_kind), "Unrecognized game data");
        return;
    }
    switch (kind) {
    case C2_SOURCE_CDROM:
        snprintf(ui.source_kind, sizeof(ui.source_kind), "CD-ROM drive %.40s", ui.source);
        break;
    case C2_SOURCE_ZIP: {
        enum c2_zip_content content = C2_ZIP_EMPTY;
        char entry[512];
        c2_zip_probe(ui.source, &content, entry, sizeof(entry), NULL, 0);
        snprintf(ui.source_kind, sizeof(ui.source_kind), "%s",
                 content == C2_ZIP_CUE_IMAGE ? "ZIP archive (CUE/BIN disc dump)"
               : content == C2_ZIP_ISO_IMAGE ? "ZIP archive (ISO disc dump)"
               : extension_is(ui.source, ".c2assets") ? "Asset pack"
               : "ZIP archive (installation)");
        break;
    }
    case C2_SOURCE_DIRECTORY:
        if (child_path(probe, sizeof(probe), root, "C2WIN95", SDL_PATHTYPE_DIRECTORY)) {
            snprintf(ui.source_kind, sizeof(ui.source_kind), "Installation folder (DOS + Win95 CD)");
        } else if (child_path(probe, sizeof(probe), root, "HD", SDL_PATHTYPE_DIRECTORY)) {
            snprintf(ui.source_kind, sizeof(ui.source_kind), "Installation folder (CD layout)");
        } else {
            snprintf(ui.source_kind, sizeof(ui.source_kind), "Installation folder");
        }
        break;
    default:
        snprintf(ui.source_kind, sizeof(ui.source_kind), "%s", c2_source_kind_name(kind));
        break;
    }
}

/* Locate C2.ENG under an activated root: plain, DOS CD, hybrid, or the
 * object map an asset pack activation writes. */
static int find_c2_eng(const char *root, char *out, size_t capacity)
{
    char a[UI_PATH_CAPACITY];
    char b[UI_PATH_CAPACITY];
    FILE *map;
    char line[1024];
    if (child_path(out, capacity, root, "C2.ENG", SDL_PATHTYPE_FILE)) return 1;
    if (child_path(a, sizeof(a), root, "HD", SDL_PATHTYPE_DIRECTORY) &&
        child_path(out, capacity, a, "C2.ENG", SDL_PATHTYPE_FILE)) return 1;
    if (child_path(a, sizeof(a), root, "C2WIN95", SDL_PATHTYPE_DIRECTORY) &&
        child_path(b, sizeof(b), a, "HD", SDL_PATHTYPE_DIRECTORY) &&
        child_path(out, capacity, b, "C2.ENG", SDL_PATHTYPE_FILE)) return 1;
    if (!child_path(a, sizeof(a), root, ".c2-object-map", SDL_PATHTYPE_FILE)) return 0;
    map = fopen(a, "rb");
    if (!map) return 0;
    while (fgets(line, sizeof(line), map)) {
        char *tab = strchr(line, '\t');
        char *end;
        if (!tab) continue;
        *tab++ = '\0';
        end = strpbrk(tab, "\r\n");
        if (end) *end = '\0';
        if (SDL_strcasecmp(line, "C2.ENG") == 0) {
            fclose(map);
            return snprintf(out, capacity, "%s/%s", root, tab) < (int)capacity;
        }
    }
    fclose(map);
    return 0;
}

/* The launcher font is ASCII-only; strip accents from the Latin-1 text the
 * localized C2.ENG files carry rather than show '?'. */
static char fold_latin1(unsigned char c)
{
    static const char table[64] =
        "AAAAAAACEEEEIIIIDNOOOOOxOUUUUYTsaaaaaaaceeeeiiiidnooooo/ouuuuyty";
    if (c >= ' ' && c < 0x7f) return (char)c;
    if (c >= 0xc0) return table[c - 0xc0];
    return '?';
}

/* Entry `list`, word `word` of the recovered Textfile format: a table of
 * 24-bit offsets at +8, then NUL-separated strings; mirrors font_list(). */
static int eng_string(const unsigned char *buf, size_t size, int list,
                      int word, char *out, size_t capacity)
{
    size_t p;
    size_t e;
    size_t table = (size_t)list * 4 + 8;
    if (size < 8 || memcmp(buf, "Textfile", 8) != 0 || table + 3 > size) return 0;
    p = (size_t)buf[table] | ((size_t)buf[table + 1] << 8) | ((size_t)buf[table + 2] << 16);
    if (p == 0 || p >= size) return 0;
    while (word > 0) {
        if (p >= size) return 0;
        if (buf[p] == 0 && (buf[p - 1] >= ' ' || buf[p - 1] == 0)) word--;
        p++;
    }
    while (p < size && buf[p] < ' ') p++;
    e = p;
    while (e < size && buf[e] != 0 && e - p + 1 < capacity) {
        out[e - p] = fold_latin1(buf[e]);
        e++;
    }
    out[e - p] = '\0';
    return e > p;
}

/* A pack activation resolves to <pack>/ACTIVE-<profile>; list the pack's
 * profiles so a language row can be offered. Non-pack data has none. */
static void detect_profiles(const char *root)
{
    char pack[UI_PATH_CAPACITY];
    char index[UI_PATH_CAPACITY];
    FILE *file;
    char line[1024];
    ui.profile_count = 0;
    if (strlen(root) >= sizeof(pack)) return;
    strcpy(pack, root);
    if (!child_path(index, sizeof(index), pack, "C2PACK.IDX", SDL_PATHTYPE_FILE)) {
        char *slash = strrchr(pack, '/');
        if (!slash) return;
        *slash = '\0';
        if (!child_path(index, sizeof(index), pack, "C2PACK.IDX", SDL_PATHTYPE_FILE)) return;
    }
    file = fopen(index, "rb");
    if (!file) return;
    while (fgets(line, sizeof(line), file) &&
           ui.profile_count < (int)(sizeof(ui.profiles) / sizeof(ui.profiles[0]))) {
        char *name;
        char *end;
        if (strncmp(line, "PROFILE\t", 8) != 0) continue;
        name = line + 8;
        end = strpbrk(name, "\t\r\n");
        if (end) *end = '\0';
        if (!*name) continue;
        snprintf(ui.profiles[ui.profile_count++], sizeof(ui.profiles[0]), "%s", name);
    }
    fclose(file);
    if (ui.profile_count && !ui.asset_profile[0]) {
        /* The activation picked the pack default; mirror it so the row
         * shows what is actually active. */
        const char *active = strrchr(root, '-');
        if (active && active[1]) {
            snprintf(ui.asset_profile, sizeof(ui.asset_profile), "%s", active + 1);
        }
    }
}

static const char *profile_label(const char *tag)
{
    static const struct { const char *tag; const char *label; } names[] = {
        { "en", "English" }, { "de", "Deutsch" }, { "fr", "Francais" },
        { "it", "Italiano" }, { "es", "Espanol" }, { "nl", "Nederlands" },
        { "pl", "Polski" }
    };
    size_t i;
    for (i = 0; i < sizeof(names) / sizeof(names[0]); i++) {
        if (SDL_strcasecmp(names[i].tag, tag) == 0) return names[i].label;
    }
    return tag;
}

static void detect_version(const char *root)
{
    char path[UI_PATH_CAPACITY];
    unsigned char *buf;
    size_t size;
    FILE *file;
    char version[64];
    char date[64];
    snprintf(ui.detected, sizeof(ui.detected), "version unknown");
    if (!find_c2_eng(root, path, sizeof(path))) return;
    file = fopen(path, "rb");
    if (!file) return;
    buf = malloc(65536);
    if (!buf) { fclose(file); return; }
    size = fread(buf, 1, 65536, file);
    fclose(file);
    if (eng_string(buf, size, 0x0b, 0, version, sizeof(version))) {
        if (eng_string(buf, size, 0x0b, 1, date, sizeof(date))) {
            snprintf(ui.detected, sizeof(ui.detected), "%.60s, %.60s",
                     version, date);
        } else {
            snprintf(ui.detected, sizeof(ui.detected), "%s", version);
        }
    }
    free(buf);
}

/* Any file with the extension directly in dir or in its sub-directory. */
static int has_media(const char *root, const char *subdir, const char *pattern)
{
    char dir[UI_PATH_CAPACITY];
    char **entries;
    int count;
    int found;
    int pass;

    for (pass = 0; pass < 2; pass++) {
        if (pass == 0) {
            snprintf(dir, sizeof(dir), "%s", root);
        } else if (!child_path(dir, sizeof(dir), root, subdir, SDL_PATHTYPE_DIRECTORY)) {
            break;
        }
        entries = SDL_GlobDirectory(dir, pattern, SDL_GLOB_CASEINSENSITIVE, &count);
        found = entries != NULL && count > 0;
        SDL_free(entries);
        if (found) return 1;
    }
    return 0;
}

/* The original installer copied only the HD tree; XMI music and RAW speech
 * stayed on the CD. Say so instead of leaving the silence unexplained. */
static void detect_media(const char *root)
{
    char map[UI_PATH_CAPACITY];
    int music;
    int speech;

    ui.media_note[0] = '\0';
    if (child_path(map, sizeof(map), root, ".c2-object-map", SDL_PATHTYPE_FILE) ||
        child_path(map, sizeof(map), root, "C2PACK.IDX", SDL_PATHTYPE_FILE)) {
        return; /* packs and object-mapped caches carry what they list */
    }
    music = has_media(root, "XMI", "*.xmi");
    speech = has_media(root, "RAW", "*.raw");
    if (music && speech) return;
    snprintf(ui.media_note, sizeof(ui.media_note), "No %s files: they stayed on the CD",
             !music && !speech ? "music or speech" : !music ? "music" : "speech");
}

static void refresh_source(void)
{
    ui.source_ready = c2_setup_source_looks_valid(ui.source);
    ui.detected[0] = '\0';
    ui.media_note[0] = '\0';
    ui.profile_count = 0;
    describe_source_kind();
    if (ui.source[0] && !ui.source_ready) {
        set_status("No Caesar II game data was found at this location.",
                   &COLOR_ERROR);
    }
}

/* ------------------------------------------------------------------ */
/* Import worker                                                       */

static void import_progress(void *userdata, const char *phase,
                            uint64_t completed, uint64_t total,
                            size_t completed_files, size_t total_files)
{
    (void)userdata;
    SDL_LockMutex(ui.mutex);
    snprintf(ui.phase, sizeof(ui.phase), "%s", phase ? phase : "Importing");
    ui.completed_bytes = completed;
    ui.total_bytes = total;
    ui.completed_files = completed_files;
    ui.total_files = total_files;
    SDL_UnlockMutex(ui.mutex);
}

static int import_main(void *userdata)
{
    struct c2_import_progress progress;
    char resolved[UI_PATH_CAPACITY];
    char error[512];
    int ok;
    (void)userdata;
    progress.update = import_progress;
    progress.userdata = NULL;
    error[0] = '\0';
    ok = c2_import_path(ui.source, ui.cache_root,
                        ui.asset_profile[0] ? ui.asset_profile : NULL,
                        &progress, resolved, sizeof(resolved),
                        error, sizeof(error));
    if (ok && !c2_setup_source_looks_valid(resolved)) {
        ok = 0;
        snprintf(error, sizeof(error),
                 "the imported data does not contain C2.ENG and HELP.ENG");
    }
    SDL_LockMutex(ui.mutex);
    ui.import_ok = ok;
    snprintf(ui.resolved, sizeof(ui.resolved), "%s", ok ? resolved : "");
    snprintf(ui.import_error, sizeof(ui.import_error), "%s", error);
    ui.import_done = 1;
    SDL_UnlockMutex(ui.mutex);
    return 0;
}

static void start_import(int play_after)
{
    SDL_LockMutex(ui.mutex);
    ui.import_done = 0;
    ui.import_ok = 0;
    ui.import_error[0] = '\0';
    ui.resolved[0] = '\0';
    snprintf(ui.phase, sizeof(ui.phase), "Checking game data");
    ui.completed_bytes = ui.total_bytes = 0;
    ui.completed_files = ui.total_files = 0;
    SDL_UnlockMutex(ui.mutex);
    ui.play_after_import = play_after;
    ui.state = SETUP_IMPORT;
    set_status("", &COLOR_MUTED);
    ui.thread = SDL_CreateThread(import_main, "caesar2-import", NULL);
    if (ui.thread == NULL) {
        ui.state = SETUP_MENU;
        set_status("Could not start the import thread.", &COLOR_ERROR);
    }
}

static void finish_import(void)
{
    int ok;
    char error[512];
    SDL_WaitThread(ui.thread, NULL);
    ui.thread = NULL;
    SDL_LockMutex(ui.mutex);
    ok = ui.import_ok;
    snprintf(error, sizeof(error), "%s", ui.import_error);
    SDL_UnlockMutex(ui.mutex);
    ui.state = SETUP_MENU;
    if (ui.quit_after_import) {
        ui.result = C2_SETUP_QUIT;
        return;
    }
    if (ok) {
        ui.source_ready = 1;
        if (ui.play_after_import) {
            ui.result = C2_SETUP_PLAY;
            return;
        }
        detect_version(ui.resolved);
        detect_media(ui.resolved);
        detect_profiles(ui.resolved);
        if (ui.startup_check) {
            ui.startup_check = 0;
        } else {
            set_status("Game data is ready. Press Play to start.", &COLOR_OK);
        }
        ui.focus = 0;
    } else {
        ui.startup_check = 0;
        char message[256];
        snprintf(message, sizeof(message), "Import failed: %.230s", error);
        set_status(message, &COLOR_ERROR);
        ui.source_ready = c2_setup_source_looks_valid(ui.source);
    }
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

static void open_dialog(void)
{
    /* One dialog for everything. A file inside an installation (C2.ENG,
     * CAESAR2.EXE, ...) selects that installation. */
    static const SDL_DialogFileFilter filters[] = {
        { "Caesar II game data (C2.ENG, ISO, BIN, CUE, ZIP, C2ASSETS)",
          "eng;exe;iso;bin;cue;img;zip;c2assets" },
        { "All files", "*" }
    };
    SDL_LockMutex(ui.mutex);
    ui.dialog_done = 0;
    ui.dialog_path[0] = '\0';
    SDL_UnlockMutex(ui.mutex);
    ui.state = SETUP_DIALOG;
    set_status("", &COLOR_MUTED);
    SDL_ShowOpenFileDialog(dialog_closed, NULL, ui.window, filters, 2, NULL,
                           false);
}

/* A picked/dropped path becomes the source; installation files collapse
 * to their root so the remembered source is the folder itself. */
static void select_path(const char *path)
{
    enum c2_source_kind kind;
    char root[UI_PATH_CAPACITY];
    char error[256];
    if (!c2_import_classify(path, &kind, root, sizeof(root), error, sizeof(error))) {
        snprintf(ui.source, sizeof(ui.source), "%s", path);
        ui.source_ready = 0;
        ui.detected[0] = '\0';
        describe_source_kind();
        set_status(error, &COLOR_ERROR);
        rebuild_buttons();
        return;
    }
    snprintf(ui.source, sizeof(ui.source), "%s",
             kind == C2_SOURCE_DIRECTORY ? root : path);
    refresh_source();
    start_import(0);
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
    select_path(path);
}

/* ------------------------------------------------------------------ */
/* Input                                                               */

static void activate(int index)
{
    struct button *button;
    if (index < 0 || index >= ui.button_count) return;
    button = &ui.buttons[index];
    if (!button->enabled || ui.state != SETUP_MENU) return;
    switch (button->kind) {
    case BUTTON_PLAY:
        start_import(1);
        break;
    case BUTTON_DISPLAY:
        ui.fullscreen = !ui.fullscreen;
        rebuild_buttons();
        break;
    case BUTTON_SCALING:
        ui.fractional_scaling = !ui.fractional_scaling;
        rebuild_buttons();
        break;
    case BUTTON_CHOOSE:
        open_dialog();
        break;
    case BUTTON_LANGUAGE: {
        int i;
        int current = -1;
        for (i = 0; i < ui.profile_count; i++) {
            if (SDL_strcasecmp(ui.profiles[i], ui.asset_profile) == 0) current = i;
        }
        snprintf(ui.asset_profile, sizeof(ui.asset_profile), "%s",
                 ui.profiles[(current + 1) % ui.profile_count]);
        ui.startup_check = 1; /* quiet re-activation */
        start_import(0);
        break;
    }
    case BUTTON_DRIVE:
        snprintf(ui.source, sizeof(ui.source), "%s", button->drive);
        ui.source_ready = 1;
        start_import(0);
        break;
    case BUTTON_QUIT:
        ui.result = C2_SETUP_QUIT;
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
    if (ui.state == SETUP_IMPORT) {
        ui.quit_after_import = 1;
    } else {
        ui.result = C2_SETUP_QUIT;
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
        if (ui.state == SETUP_MENU && event->drop.data) select_path(event->drop.data);
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
            request_quit();
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

static void render_menu(void)
{
    int i;
    for (i = 0; i < ui.button_count; i++) {
        const struct button *button = &ui.buttons[i];
        const struct rgb *fill = !button->enabled ? &COLOR_BUTTON_DISABLED
                               : i == ui.hover ? &COLOR_BUTTON_HOVER
                               : &COLOR_BUTTON;
        const struct rgb *text = button->enabled ? &COLOR_TEXT : &COLOR_MUTED;
        int x = (int)button->rect.x;
        int y = (int)button->rect.y;
        int w = (int)button->rect.w;
        int h = (int)button->rect.h;
        fill_rect(x, y, w, h, fill);
        if (i == ui.focus && ui.state == SETUP_MENU) {
            outline_rect(x, y, w, h, &COLOR_FOCUS);
        }
        draw_text(x + 10, y + (h - UI_GLYPH) / 2, 1, text, button->label);
        if (button->hint[0]) {
            draw_text(x + w - 10 - text_width(button->hint, 1),
                      y + (h - UI_GLYPH) / 2, 1, &COLOR_MUTED, button->hint);
        }
    }
    if (ui.state == SETUP_DIALOG) {
        draw_text(UI_MARGIN, UI_HEIGHT - 44, 1, &COLOR_MUTED,
                  "Waiting for the file dialog...");
    }
}

static void render_import(void)
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
        /* Indeterminate: directory/pack sources have nothing to copy. */
        int sweep = (int)((SDL_GetTicks() / 8) % (Uint64)(bar_w + 60)) - 60;
        int x0 = sweep < 0 ? bar_x : bar_x + sweep;
        int x1 = bar_x + sweep + 60;
        if (x1 > bar_x + bar_w) x1 = bar_x + bar_w;
        if (x1 > x0) fill_rect(x0, bar_y, x1 - x0, bar_h, &COLOR_BAR);
        snprintf(line, sizeof(line), "Please wait...");
    }
    outline_rect(bar_x, bar_y, bar_w, bar_h, &COLOR_RULE);
    draw_text(UI_MARGIN, bar_y + bar_h + 12, 1, &COLOR_MUTED, line);
    if (ui.quit_after_import) {
        draw_text(UI_MARGIN, bar_y + bar_h + 36, 1, &COLOR_ERROR,
                  "Quitting once the import has finished.");
    } else {
        draw_text(UI_MARGIN, bar_y + bar_h + 36, 1, &COLOR_MUTED,
                  "The import runs once; later starts reuse the cached copy.");
    }
}

static void render(void)
{
    char line[160];
    char shown[128];
    const int max_chars = (UI_WIDTH - 2 * UI_MARGIN) / UI_GLYPH;

    SDL_SetRenderDrawColor(ui.renderer, COLOR_BACKGROUND.r, COLOR_BACKGROUND.g,
                           COLOR_BACKGROUND.b, 255);
    SDL_RenderClear(ui.renderer);

    draw_text(UI_MARGIN, 14, 2, &COLOR_TITLE, "CAESAR II");
    snprintf(line, sizeof(line), "Second Impressions port %s", ui.version);
    draw_text(UI_MARGIN, 36, 1, &COLOR_MUTED, line);
    fill_rect(UI_MARGIN, 52, UI_WIDTH - 2 * UI_MARGIN, 1, &COLOR_RULE);

    draw_text(UI_MARGIN, 60, 1, &COLOR_MUTED, "Game data");
    if (ui.source[0]) {
        fit_path(shown, sizeof(shown), ui.source_kind, max_chars);
        draw_text(UI_MARGIN, 72, 1, &COLOR_TEXT, shown);
        if (ui.detected[0]) {
            fit_path(shown, sizeof(shown), ui.detected, max_chars);
            draw_text(UI_MARGIN, 84, 1, &COLOR_TEXT, shown);
            if (ui.media_note[0]) {
                fit_path(shown, sizeof(shown), ui.media_note, max_chars);
                draw_text(UI_MARGIN, 96, 1, &COLOR_ERROR, shown);
            }
        } else if (ui.source_ready) {
            draw_text(UI_MARGIN, 84, 1, &COLOR_MUTED,
                      ui.state == SETUP_IMPORT ? "Checking..." : "Not imported yet");
        }
    } else {
        draw_text(UI_MARGIN, 72, 1, &COLOR_MUTED,
                  "None selected. Choose a folder, image, or disc below.");
    }
    if (ui.status[0]) {
        fit_path(shown, sizeof(shown), ui.status, max_chars);
        draw_text(UI_MARGIN, 98, 1, ui.status_color, shown);
    }

    if (ui.state == SETUP_IMPORT) {
        render_import();
    } else {
        render_menu();
    }

    draw_text(UI_MARGIN, UI_HEIGHT - 40, 1, &COLOR_MUTED,
              "Installed folder, ISO/BIN disc image, ZIP or .c2assets");
    draw_text(UI_MARGIN, UI_HEIGHT - 28, 1, &COLOR_MUTED,
              "pack - pick a file inside it, or drop it on this window.");
    draw_text(UI_MARGIN, UI_HEIGHT - 16, 1, &COLOR_MUTED,
              "Arrows/Tab move, Enter selects, Esc quits.");
    SDL_RenderPresent(ui.renderer);
}

/* ------------------------------------------------------------------ */
/* Lifecycle                                                           */

int c2_setup_open(const struct c2_setup_config *config)
{
    char title[128];
    SDL_Mutex *mutex;
    if (ui.open) return 1;
    /* The mutex outlives close(): a native file dialog that is still open
     * when the launcher is torn down may deliver its callback later, and it
     * must find valid state to write into. */
    mutex = ui.mutex;
    memset(&ui, 0, sizeof(ui));
    ui.mutex = mutex ? mutex : SDL_CreateMutex();
    ui.focus = -1;
    ui.hover = -1;
    snprintf(ui.version, sizeof(ui.version), "%s",
             config->version ? config->version : "");
    snprintf(ui.source, sizeof(ui.source), "%s",
             config->source ? config->source : "");
    snprintf(ui.cache_root, sizeof(ui.cache_root), "%s",
             config->cache_root ? config->cache_root : ".");
    snprintf(ui.asset_profile, sizeof(ui.asset_profile), "%s",
             config->asset_profile ? config->asset_profile : "");
    ui.fullscreen = config->fullscreen != 0;
    ui.fractional_scaling = config->fractional_scaling != 0;

    if (!SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS)) {
        fprintf(stderr, "launcher: SDL video initialization failed: %s\n",
                SDL_GetError());
        return 0;
    }
    snprintf(title, sizeof(title), "Caesar II %s", ui.version);
    if (!SDL_CreateWindowAndRenderer(title, UI_WIDTH * UI_SCALE,
                                     UI_HEIGHT * UI_SCALE,
                                     SDL_WINDOW_RESIZABLE,
                                     &ui.window, &ui.renderer)) {
        fprintf(stderr, "launcher: window creation failed: %s\n",
                SDL_GetError());
        SDL_QuitSubSystem(SDL_INIT_VIDEO | SDL_INIT_EVENTS);
        return 0;
    }
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
    scan_drives();
    refresh_source();
    rebuild_buttons();
    if (config->error && config->error[0]) {
        SDL_PathInfo info;
        set_status(config->error, &COLOR_ERROR);
        if (SDL_GetPathInfo(ui.source, &info) &&
            info.type == SDL_PATHTYPE_DIRECTORY) {
            detect_version(ui.source);
            detect_media(ui.source);
        }
    } else if (ui.source_ready) {
        /* Validate the remembered/preselected source right away so the
         * version line is populated; instant on a cache hit. */
        ui.startup_check = 1;
        start_import(0);
    }
    render();
    return 1;
}

enum c2_setup_result c2_setup_iterate(void)
{
    if (!ui.open) return C2_SETUP_QUIT;
    if (ui.state == SETUP_IMPORT) {
        int done;
        SDL_LockMutex(ui.mutex);
        done = ui.import_done;
        SDL_UnlockMutex(ui.mutex);
        if (done) finish_import();
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
    return ui.result;
}

const char *c2_setup_selected_source(void)
{
    return ui.source;
}

const char *c2_setup_selected_profile(void)
{
    return ui.asset_profile;
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
const char *c2_setup_selected_source(void) { return ""; }
const char *c2_setup_selected_profile(void) { return ""; }
int c2_setup_selected_fullscreen(void) { return 0; }
int c2_setup_selected_fractional_scaling(void) { return 0; }
void c2_setup_close(void) {}
int c2_setup_source_looks_valid(const char *path) { (void)path; return 0; }

#endif
