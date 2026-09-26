/*
 * The game-data library: one tree sorted by what the files are, shared by
 * the native launcher and the browser page (docs/game-data-library.md).
 *
 * An import is staged (c2_import_stage), sorted into places by one table,
 * and merged file by file: a better copy replaces, an equal or worse one is
 * ignored. A language folder always holds one release and is replaced as a
 * whole. A .c2assets is the library zipped, so it merges the same way.
 */
#include "c2_library.h"

#include <SDL3/SDL.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PATH_CAP C2_LIBRARY_PATH_CAPACITY
#define REL_CAP 192

#define LIBRARY_MARKER "C2ASSETS"
#define LIBRARY_FORMAT "caesar2-assets"
#define LIBRARY_VERSION 1
#define SUMMARY_FORMAT "c2-game-data 1"

enum category {
    CAT_COMMON = 0,
    CAT_UNIT,
    CAT_MUSIC_DOS,
    CAT_MUSIC_WINDOWS,
    CAT_MOVIE
};

/* Quality of a file's origin: the recovered engine is the DOS one, so a
 * DOS tree's copy is the reference. Windows 95 trees remap the palette and
 * re-encode; movie-only sources (the Mac set) sit in between. */
enum tree {
    TREE_WINDOWS = 1,
    TREE_OTHER = 2,
    TREE_DOS = 3
};

struct unit {
    char lang[C2_LIBRARY_TAG_CAPACITY];
    int tree;
    int speech;
    int later;            /* the disc also had the Windows 95 tree: pressed from August 1996 on */
    char version[24];
    int accepted;
};

struct item {
    char src[PATH_CAP];
    char rel[REL_CAP];
    int category;
    int tree;
    int unit;             /* index into the unit list, CAT_UNIT only */
    int aiff;             /* Mac audio: converted to the PC's raw samples */
    uint64_t size;        /* bytes, or samples for AIFF */
};

struct items {
    struct item *v;
    size_t count;
    size_t capacity;
};

struct note {
    char path[REL_CAP + 32];
    int tree;
};

struct manifest {
    struct unit units[C2_LIBRARY_MAX_LANGUAGES];
    int unit_count;
    struct note *notes;
    size_t note_count;
    size_t note_capacity;
};

struct names {
    char **v;
    size_t count;
    size_t capacity;
};

/* ------------------------------------------------------------------ */
/* Tables, from the thirteen PC releases and the 1998 Windows pressing  */

/* The Windows version's soundtrack: byte-identical on every disc. */
static const char *const recordings[] = {
    "CITYPRO0.RAW", "CITYPRO1.RAW", "CITYPRO2.RAW",
    "FORUM0.RAW", "FORUM1.RAW", "FORUM2.RAW", "BATTLE0.RAW", "INTRO.RAW"
};

/* Paths outside speech that differ between releases (the German 1996
 * rerelease and the English 1.2 update change art, samples, the region
 * table and a movie). Each belongs to its release's language folder. */
static const char *const release_files[] = {
    "C2.ENG", "HELP.ENG", "A09.WAV", "FORUM.WAV", "MINING4.WAV",
    "BACKGRND.PL8", "E_PARTS2.PL8", "REGIONS.DAT",
    "PL8/AF2BOWC.PL8", "PL8/AF3BOWC.PL8", "PL8/AFORUM.PL8", "PL8/CA2SPRB.PL8",
    "PL8/EG2SPRA.PL8", "PL8/HN2SWDB.PL8", "PL8/LIBRARY.PL8", "PL8/PA2CAVA2.PL8",
    "PL8/PANTHCOL.PL8", "PL8/RO2SLGC.PL8", "PL8/TCOLMDET.PL8", "PL8/TUT_02A.PL8",
    "PL8/TUT_04B.PL8", "PL8/TUT_12B.PL8", "SMK/RIOTERS.SMK"
};

/* Movies the engine scales into the VGA box (do_vga_smacked_anim); only
 * these gain from a copy with more pixels. The rest are drawn 1:1. */
static const char *const scaled_movies[] = {
    "BATTLOST.SMK", "BATTWON.SMK", "LOSEGAME.SMK", "PROMOTE.SMK", "WINGAME.SMK"
};

/* The Mac CDs keep the Windows version's recordings as AIFF under XMI/,
 * named after the scores they replace. The samples are the PC recordings,
 * signed and a few bytes shorter. */
static const char *const mac_music[][2] = {
    { "PROVINC1.XMI", "CITYPRO1.RAW" }, { "PROVINC2.XMI", "CITYPRO2.RAW" },
    { "PROVINC3.XMI", "CITYPRO0.RAW" }, { "FORUM1.XMI", "FORUM0.RAW" },
    { "FORUM2.XMI", "FORUM1.RAW" }, { "FORUM3.XMI", "FORUM2.RAW" },
    { "BATTLE1.XMI", "BATTLE0.RAW" }, { "INTRO.XMI", "INTRO.RAW" }
};

static const char *const runtime_extensions[] = {
    ".ENG", ".PL8", ".RAW", ".SMK", ".XMI", ".WAV",
    ".256", ".DAT", ".GD8", ".OPL", ".AD"
};

static c2_language_detector language_detector;

void c2_library_set_language_detector(c2_language_detector detector)
{
    language_detector = detector;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                              */

static void set_error(char *error, size_t capacity, const char *message)
{
    if (error && capacity) snprintf(error, capacity, "%s", message);
}

static int in_list(const char *name, const char *const *list, size_t count)
{
    size_t i;
    for (i = 0; i < count; i++) {
        if (SDL_strcasecmp(name, list[i]) == 0) return 1;
    }
    return 0;
}

#define IN_LIST(name, list) in_list((name), (list), sizeof(list) / sizeof((list)[0]))

static int join(char *out, size_t capacity, const char *left, const char *right)
{
    size_t n = strlen(left);
    int result = snprintf(out, capacity, "%s%s%s", left,
                          n && (left[n - 1] == '/' || left[n - 1] == '\\') ? "" : "/",
                          right);
    return result >= 0 && (size_t)result < capacity;
}

static void upper(char *text)
{
    for (; *text; text++) {
        *text = (char)toupper((unsigned char)*text);
        if (*text == '\\') *text = '/';
    }
}

static int has_extension(const char *name, const char *extension)
{
    const char *dot = strrchr(name, '.');
    return dot && SDL_strcasecmp(dot, extension) == 0;
}

static int runtime_file(const char *name)
{
    size_t i;
    const char *dot = strrchr(name, '.');
    if (!dot) return 0;
    for (i = 0; i < sizeof(runtime_extensions) / sizeof(runtime_extensions[0]); i++) {
        if (SDL_strcasecmp(dot, runtime_extensions[i]) == 0) return 1;
    }
    return 0;
}

static int is_directory(const char *path)
{
    SDL_PathInfo info;
    return SDL_GetPathInfo(path, &info) && info.type == SDL_PATHTYPE_DIRECTORY;
}

static int is_file(const char *path)
{
    SDL_PathInfo info;
    return SDL_GetPathInfo(path, &info) && info.type == SDL_PATHTYPE_FILE;
}

static uint64_t file_size(const char *path)
{
    SDL_PathInfo info;
    return SDL_GetPathInfo(path, &info) ? info.size : 0;
}

static SDL_EnumerationResult SDLCALL add_name(void *userdata, const char *dirname,
                                              const char *fname)
{
    struct names *names = userdata;
    (void)dirname;
    if (names->count == names->capacity) {
        size_t capacity = names->capacity ? names->capacity * 2 : 64;
        char **grown = realloc(names->v, capacity * sizeof(*grown));
        if (!grown) return SDL_ENUM_FAILURE;
        names->v = grown;
        names->capacity = capacity;
    }
    names->v[names->count] = SDL_strdup(fname);
    if (!names->v[names->count]) return SDL_ENUM_FAILURE;
    names->count++;
    return SDL_ENUM_CONTINUE;
}

static void free_names(struct names *names)
{
    size_t i;
    for (i = 0; i < names->count; i++) SDL_free(names->v[i]);
    free(names->v);
    memset(names, 0, sizeof(*names));
}

static void list_directory(const char *directory, struct names *names)
{
    memset(names, 0, sizeof(*names));
    SDL_EnumerateDirectory(directory, add_name, names);
}

static int count_entries(const char *directory)
{
    struct names names;
    int count;
    list_directory(directory, &names);
    count = (int)names.count;
    free_names(&names);
    return count;
}

/* The child `name` of `directory` in any letter case. */
static int find_child(char *out, size_t capacity, const char *directory,
                      const char *name, int want_directory)
{
    struct names names;
    size_t i;
    int found = 0;
    if (!directory || !directory[0]) return 0;
    if (join(out, capacity, directory, name) &&
        (want_directory ? is_directory(out) : is_file(out))) return 1;
    list_directory(directory, &names);
    for (i = 0; i < names.count && !found; i++) {
        if (SDL_strcasecmp(names.v[i], name) == 0 &&
            join(out, capacity, directory, names.v[i]) &&
            (want_directory ? is_directory(out) : is_file(out))) found = 1;
    }
    free_names(&names);
    return found;
}

static int make_directories(const char *path)
{
    char copy[PATH_CAP];
    char *p;
    if (strlen(path) >= sizeof(copy)) return 0;
    strcpy(copy, path);
    for (p = copy + 1; *p; p++) {
        if (*p == '/' || *p == '\\') {
            char keep = *p;
            *p = '\0';
            if (!(p > copy && p[-1] == ':') && !is_directory(copy)) SDL_CreateDirectory(copy);
            *p = keep;
        }
    }
    if (!is_directory(copy)) SDL_CreateDirectory(copy);
    return is_directory(copy);
}

static int make_parents(const char *path)
{
    char copy[PATH_CAP];
    char *slash;
    if (strlen(path) >= sizeof(copy)) return 0;
    strcpy(copy, path);
    slash = strrchr(copy, '/');
    {
        char *back = strrchr(copy, '\\');
        if (back && (!slash || back > slash)) slash = back;
    }
    if (!slash) return 1;
    *slash = '\0';
    return make_directories(copy);
}

/* Put a finished temporary file in place. Native renames it; the web
 * copies it, because Firefox keeps a file renamed in OPFS locked for the
 * next page load. */
static int commit_file(const char *temporary, const char *path)
{
#if PORT_PLATFORM_WASM
    int ok = SDL_CopyFile(temporary, path);
    SDL_RemovePath(temporary);
    return ok;
#else
    if (SDL_RenamePath(temporary, path)) return 1;
    SDL_RemovePath(path);
    return SDL_RenamePath(temporary, path);
#endif
}

static int remove_tree(const char *path)
{
    SDL_PathInfo info;
    if (!SDL_GetPathInfo(path, &info)) return 1;
    if (info.type == SDL_PATHTYPE_DIRECTORY) {
        struct names names;
        size_t i;
        list_directory(path, &names);
        for (i = 0; i < names.count; i++) {
            char child[PATH_CAP];
            if (join(child, sizeof(child), path, names.v[i])) remove_tree(child);
        }
        free_names(&names);
    }
    return SDL_RemovePath(path);
}

static int convert_aiff(const char *src, const char *dest);

static int place_file(const char *src, const char *dest, int move, int aiff)
{
    if (!make_parents(dest)) return 0;
    if (is_file(dest)) SDL_RemovePath(dest);
    if (aiff) return convert_aiff(src, dest);
#if !PORT_PLATFORM_WASM
    if (move && SDL_RenamePath(src, dest)) return 1;
#else
    (void)move;   /* see commit_file */
#endif
    return SDL_CopyFile(src, dest);
}

/* The whole of a small file, `limit` bytes at most. */
static unsigned char *read_file(const char *path, size_t limit, size_t *size_out)
{
    uint64_t length;
    length = file_size(path);
    unsigned char *buffer;
    size_t size;
    FILE *file;
    if (length > limit) length = limit;
    file = fopen(path, "rb");
    if (!file) return NULL;
    buffer = malloc((size_t)length + 1);
    if (!buffer) { fclose(file); return NULL; }
    size = length ? fread(buffer, 1, (size_t)length, file) : 0;
    fclose(file);
    buffer[size] = 0;
    *size_out = size;
    return buffer;
}

/* ------------------------------------------------------------------ */
/* AIFF, the Mac audio                                                  */

/* The sample data of a mono 8-bit AIFF: offset and length in the file. */
static int aiff_samples(const char *path, uint64_t *offset, uint64_t *length)
{
    unsigned char header[12];
    unsigned char chunk[18];
    uint64_t position = 12;
    uint64_t size = file_size(path);
    int mono8 = 0;
    FILE *file = fopen(path, "rb");
    if (!file) return 0;
    if (fread(header, 1, sizeof(header), file) != sizeof(header) ||
        memcmp(header, "FORM", 4) != 0 || memcmp(header + 8, "AIFF", 4) != 0) {
        fclose(file);
        return 0;
    }
    while (position + 8 <= size) {
        uint32_t n;
        if (fseek(file, (long)position, SEEK_SET) != 0 ||
            fread(chunk, 1, 8, file) != 8) break;
        n = ((uint32_t)chunk[4] << 24) | ((uint32_t)chunk[5] << 16) |
            ((uint32_t)chunk[6] << 8) | chunk[7];
        if (memcmp(chunk, "COMM", 4) == 0 && n >= 8 && fread(chunk + 8, 1, 8, file) == 8) {
            unsigned channels = (unsigned)(chunk[8] << 8 | chunk[9]);
            unsigned bits = (unsigned)(chunk[14] << 8 | chunk[15]);
            mono8 = channels == 1 && bits == 8;
        } else if (memcmp(chunk, "SSND", 4) == 0 && n >= 8 && fread(chunk + 8, 1, 8, file) == 8) {
            uint32_t skip = ((uint32_t)chunk[8] << 24) | ((uint32_t)chunk[9] << 16) |
                            ((uint32_t)chunk[10] << 8) | chunk[11];
            fclose(file);
            if (!mono8 || skip > n - 8 || position + 8 + n > size) return 0;
            *offset = position + 16 + skip;
            *length = n - 8 - skip;
            return 1;
        }
        position += 8 + (uint64_t)n + (n & 1u);
    }
    fclose(file);
    return 0;
}

static int is_aiff(const char *path)
{
    uint64_t offset;
    uint64_t length;
    return aiff_samples(path, &offset, &length);
}

/* AIFF's signed samples as the headerless unsigned PCM the PC reads. */
static int convert_aiff(const char *src, const char *dest)
{
    uint64_t offset;
    uint64_t length;
    unsigned char buffer[65536];
    FILE *in;
    FILE *out;
    int ok = 1;
    if (!aiff_samples(src, &offset, &length) || !make_parents(dest)) return 0;
    in = fopen(src, "rb");
    out = in ? fopen(dest, "wb") : NULL;
    if (!in || !out || fseek(in, (long)offset, SEEK_SET) != 0) ok = 0;
    while (ok && length > 0) {
        size_t want = length > sizeof(buffer) ? sizeof(buffer) : (size_t)length;
        size_t i;
        if (fread(buffer, 1, want, in) != want) { ok = 0; break; }
        for (i = 0; i < want; i++) buffer[i] ^= 0x80;
        if (fwrite(buffer, 1, want, out) != want) ok = 0;
        length -= want;
    }
    if (in) fclose(in);
    if (out && fclose(out) != 0) ok = 0;
    if (!ok) SDL_RemovePath(dest);
    return ok;
}

/* ------------------------------------------------------------------ */
/* C2.ENG                                                               */

/* Entry `list`, word `word` of the recovered Textfile format: a table of
 * 24-bit offsets at +8, then NUL-separated strings. */
static int eng_string(const unsigned char *buf, size_t size, int list, int word,
                      char *out, size_t capacity)
{
    size_t p;
    size_t e;
    size_t table = (size_t)list * 4 + 8;
    if (size < 16 || memcmp(buf, "Textfile", 8) != 0 || table + 3 > size) return 0;
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
        unsigned char c = buf[e];
        out[e - p] = (char)(c >= ' ' && c < 0x7f ? c : '?');
        e++;
    }
    out[e - p] = '\0';
    return e > p;
}

static const char *detect_language(const unsigned char *buf, size_t size)
{
    char first[32];
    const char *tag = language_detector ? language_detector(buf, size) : NULL;
    if (tag && tag[0]) return tag;
    /* The File menu's title, as the text catalogue's X-C2-Detect lines. */
    if (!eng_string(buf, size, 1, 0, first, sizeof(first))) return "und";
    {
        size_t n = strlen(first);
        while (n && first[n - 1] == ' ') first[--n] = '\0';
    }
    if (strcmp(first, "File") == 0) return "en";
    if (strcmp(first, "Datei") == 0) return "de";
    if (strcmp(first, "Fichier") == 0) return "fr";
    return "und";
}

/* "Caesar II - version 1.0A - 24/09/1995" -> token "1.0A", display
 * "Version 1.0A". */
static void read_version(const unsigned char *buf, size_t size,
                         char *token, size_t token_capacity,
                         char *display, size_t display_capacity)
{
    char line[96];
    const char *text = line;
    const char *v;
    size_t n = 0;
    if (token_capacity) token[0] = '\0';
    if (display_capacity) display[0] = '\0';
    if (!eng_string(buf, size, 0x0b, 0, line, sizeof(line))) {
        snprintf(token, token_capacity, "0");
        return;
    }
    if (SDL_strncasecmp(text, "Caesar II - ", 12) == 0) text += 12;
    if (display_capacity) {
        const char *cut = strstr(text, " - ");
        size_t length = cut ? (size_t)(cut - text) : strlen(text);
        while (length && text[length - 1] == ' ') length--;
        snprintf(display, display_capacity, "%.*s", (int)length, text);
        if (display[0] == 'v') display[0] = 'V';
    }
    v = SDL_strcasestr(text, "version");
    if (v) {
        v += 7;
        while (*v == ' ') v++;
        while ((isalnum((unsigned char)v[n]) || v[n] == '.') && n + 1 < token_capacity) {
            token[n] = v[n];
            n++;
        }
    }
    while (n && token[n - 1] == '.') n--;
    token[n] = '\0';
    if (!n) snprintf(token, token_capacity, "0");
}

/* 1.0 < 1.0A < 1.1 < 1.2 */
static int compare_versions(const char *a, const char *b)
{
    while (*a || *b) {
        long na = strtol(a, (char **)&a, 10);
        long nb = strtol(b, (char **)&b, 10);
        if (na != nb) return na < nb ? -1 : 1;
        while (isalpha((unsigned char)*a) || isalpha((unsigned char)*b)) {
            char ca = isalpha((unsigned char)*a) ? (char)toupper((unsigned char)*a++) : 0;
            char cb = isalpha((unsigned char)*b) ? (char)toupper((unsigned char)*b++) : 0;
            if (ca != cb) return ca < cb ? -1 : 1;
        }
        if (*a == '.') a++;
        if (*b == '.') b++;
        if (!isdigit((unsigned char)*a) && !isdigit((unsigned char)*b) &&
            !isalpha((unsigned char)*a) && !isalpha((unsigned char)*b)) break;
    }
    return 0;
}

/* ------------------------------------------------------------------ */
/* The C2ASSETS manifest                                                */

static const char *tree_name(int tree)
{
    return tree == TREE_WINDOWS ? "windows" : tree == TREE_OTHER ? "other" : "dos";
}

static int tree_from_name(const char *name)
{
    if (strcmp(name, "windows") == 0) return TREE_WINDOWS;
    if (strcmp(name, "other") == 0) return TREE_OTHER;
    return TREE_DOS;
}

static int valid_tag(const char *tag)
{
    size_t n = strlen(tag);
    size_t i;
    if (n < 2 || n >= C2_LIBRARY_TAG_CAPACITY) return 0;
    for (i = 0; i < n; i++) if (!islower((unsigned char)tag[i])) return 0;
    return 1;
}

static void free_manifest(struct manifest *m)
{
    free(m->notes);
    memset(m, 0, sizeof(*m));
}

static int find_unit(const struct manifest *m, const char *lang)
{
    int i;
    for (i = 0; i < m->unit_count; i++) {
        if (strcmp(m->units[i].lang, lang) == 0) return i;
    }
    return -1;
}

static void drop_unit(struct manifest *m, const char *lang)
{
    int i = find_unit(m, lang);
    if (i < 0) return;
    memmove(&m->units[i], &m->units[i + 1], (size_t)(m->unit_count - i - 1) * sizeof(m->units[0]));
    m->unit_count--;
}

static int note_tree(const struct manifest *m, const char *path)
{
    size_t i;
    for (i = 0; i < m->note_count; i++) {
        if (SDL_strcasecmp(m->notes[i].path, path) == 0) return m->notes[i].tree;
    }
    return TREE_DOS;
}

static int set_note(struct manifest *m, const char *path, int tree)
{
    size_t i;
    for (i = 0; i < m->note_count; i++) {
        if (SDL_strcasecmp(m->notes[i].path, path) == 0) {
            if (tree == TREE_DOS) {
                m->notes[i] = m->notes[--m->note_count];
            } else {
                m->notes[i].tree = tree;
            }
            return 1;
        }
    }
    if (tree == TREE_DOS) return 1;
    if (m->note_count == m->note_capacity) {
        size_t capacity = m->note_capacity ? m->note_capacity * 2 : 64;
        struct note *grown = realloc(m->notes, capacity * sizeof(*grown));
        if (!grown) return 0;
        m->notes = grown;
        m->note_capacity = capacity;
    }
    snprintf(m->notes[m->note_count].path, sizeof(m->notes[0].path), "%s", path);
    m->notes[m->note_count].tree = tree;
    m->note_count++;
    return 1;
}

/* 1 read, 0 absent (an empty manifest), -1 unusable. */
static int load_manifest(const char *library, struct manifest *m,
                         char *error, size_t error_capacity)
{
    char path[PATH_CAP];
    size_t size;
    unsigned char *text;
    char *line;
    char *next;
    int first = 1;
    memset(m, 0, sizeof(*m));
    if (!join(path, sizeof(path), library, LIBRARY_MARKER)) return -1;
    text = read_file(path, 1024 * 1024, &size);
    if (!text) return 0;
    for (line = (char *)text; line && *line; line = next) {
        char word[5][96];
        int fields;
        next = strchr(line, '\n');
        if (next) *next++ = '\0';
        memset(word, 0, sizeof(word));
        fields = sscanf(line, "%95s %95s %95s %95s %95s", word[0], word[1], word[2], word[3], word[4]);
        if (first) {
            int version = 0;
            first = 0;
            if (fields < 2 || strcmp(word[0], LIBRARY_FORMAT) != 0 ||
                sscanf(word[1], "%d", &version) != 1) {
                free(text);
                set_error(error, error_capacity, "not a Caesar II game-data library");
                return -1;
            }
            if (version > LIBRARY_VERSION) {
                free(text);
                snprintf(error, error_capacity,
                         "this game data was written by a newer version (format %d); "
                         "update the game to read it", version);
                return -1;
            }
            continue;
        }
        if (fields >= 4 && strcmp(word[0], "unit") == 0 && valid_tag(word[1]) &&
            m->unit_count < C2_LIBRARY_MAX_LANGUAGES && find_unit(m, word[1]) < 0) {
            struct unit *u = &m->units[m->unit_count++];
            const char *rest = line;
            memset(u, 0, sizeof(*u));
            snprintf(u->lang, sizeof(u->lang), "%s", word[1]);
            u->tree = tree_from_name(word[2]);
            u->speech = strcmp(word[3], "speech") == 0;
            u->later = strcmp(word[4], "later") == 0;
            /* the version is the rest of the line */
            {
                int skip;
                for (skip = 0; skip < 5 && rest; skip++) {
                    rest = strchr(rest, ' ');
                    if (rest) while (*rest == ' ') rest++;
                }
                snprintf(u->version, sizeof(u->version), "%s", rest && *rest ? rest : "0");
            }
        } else if (fields >= 3 && strcmp(word[0], "tree") == 0) {
            const char *rest = strchr(line + 5, ' ');
            if (rest) set_note(m, rest + 1, tree_from_name(word[1]));
        }
    }
    free(text);
    return 1;
}

static int compare_strings(const void *a, const void *b)
{
    return strcmp(*(char *const *)a, *(char *const *)b);
}

static int compare_units(const void *a, const void *b)
{
    return strcmp(((const struct unit *)a)->lang, ((const struct unit *)b)->lang);
}

static int compare_notes(const void *a, const void *b)
{
    return strcmp(((const struct note *)a)->path, ((const struct note *)b)->path);
}

/* Sorted, so a library's marker does not depend on the import order. */
static int save_manifest(const char *library, struct manifest *m)
{
    char path[PATH_CAP];
    char temporary[PATH_CAP];
    FILE *file;
    int i;
    size_t n;
    if (!join(path, sizeof(path), library, LIBRARY_MARKER) ||
        !join(temporary, sizeof(temporary), library, LIBRARY_MARKER ".new")) return 0;
    qsort(m->units, (size_t)m->unit_count, sizeof(m->units[0]), compare_units);
    if (m->note_count) qsort(m->notes, m->note_count, sizeof(m->notes[0]), compare_notes);
    file = fopen(temporary, "wb");
    if (!file) return 0;
    fprintf(file, "%s %d\n", LIBRARY_FORMAT, LIBRARY_VERSION);
    for (i = 0; i < m->unit_count; i++) {
        fprintf(file, "unit %s %s %s %s %s\n", m->units[i].lang, tree_name(m->units[i].tree),
                m->units[i].speech ? "speech" : "text",
                m->units[i].later ? "later" : "first", m->units[i].version);
    }
    for (n = 0; n < m->note_count; n++) {
        fprintf(file, "tree %s %s\n", tree_name(m->notes[n].tree), m->notes[n].path);
    }
    if (fclose(file) != 0) return 0;
    return commit_file(temporary, path);
}

/* ------------------------------------------------------------------ */
/* Sorting a source into places                                         */

static int add_item_aiff(struct items *items, const char *src, const char *rel,
                         int category, int tree, int unit, int aiff);

static int add_item(struct items *items, const char *src, const char *rel,
                    int category, int tree, int unit)
{
    return add_item_aiff(items, src, rel, category, tree, unit, 0);
}

static int add_item_aiff(struct items *items, const char *src, const char *rel,
                         int category, int tree, int unit, int aiff)
{
    struct item *it;
    if (items->count == items->capacity) {
        size_t capacity = items->capacity ? items->capacity * 2 : 256;
        struct item *grown = realloc(items->v, capacity * sizeof(*grown));
        if (!grown) return 0;
        items->v = grown;
        items->capacity = capacity;
    }
    it = &items->v[items->count];
    if (strlen(src) >= sizeof(it->src) || strlen(rel) >= sizeof(it->rel)) return 1;
    strcpy(it->src, src);
    strcpy(it->rel, rel);
    upper(it->rel);
    it->category = category;
    it->tree = tree;
    it->unit = unit;
    it->aiff = aiff;
    it->size = file_size(src);
    if (aiff) {
        uint64_t offset;
        if (!aiff_samples(src, &offset, &it->size)) return 1;
    }
    items->count++;
    return 1;
}

static int is_recording(const char *rel)
{
    return SDL_strncasecmp(rel, "RAW/", 4) == 0 && IN_LIST(rel + 4, recordings);
}

/* Where one file of a game tree goes. `unit` < 0: the tree contributes no
 * language folder (the Windows side of a hybrid disc). */
static int sort_file(struct items *items, const char *src, const char *rel_in,
                     int tree, int unit)
{
    char rel[REL_CAP];
    const char *name;
    if (strlen(rel_in) >= sizeof(rel)) return 1;
    strcpy(rel, rel_in);
    upper(rel);
    name = strrchr(rel, '/');
    name = name ? name + 1 : rel;
    if (!runtime_file(name)) return 1;
    /* The player's own files, where an installation kept them. */
    if (strcmp(name, "HISTORY.DAT") == 0) return 1;
    if (strchr(rel, '/') == NULL && has_extension(name, ".smk")) {
        /* The DOS intro sits among the base files. */
        char movie[REL_CAP];
        snprintf(movie, sizeof(movie), "SMK/%s", name);
        strcpy(rel, movie);
    }
    if (strchr(rel, '/') == NULL && has_extension(name, ".xmi")) {
        char music[REL_CAP];
        snprintf(music, sizeof(music), "XMI/%s", name);
        strcpy(rel, music);
    }
    if (is_recording(rel)) return add_item(items, src, rel, CAT_MUSIC_WINDOWS, tree, -1);
    if (unit < 0) {
        /* Only the recordings and the movies of a second tree matter. */
        if (strncmp(rel, "SMK/", 4) == 0 && !IN_LIST(rel, release_files)) {
            return add_item(items, src, rel, CAT_MOVIE, tree, -1);
        }
        return 1;
    }
    if (strcmp(rel, "C2.ENG") == 0 || strcmp(rel, "HELP.ENG") == 0 ||
        strncmp(rel, "RAW/", 4) == 0 || IN_LIST(rel, release_files)) {
        return add_item(items, src, rel, CAT_UNIT, tree, unit);
    }
    if (strncmp(rel, "XMI/", 4) == 0 || strcmp(rel, "CAESAR.OPL") == 0 ||
        strcmp(rel, "CAESAR.AD") == 0) {
        return add_item(items, src, rel, CAT_MUSIC_DOS, tree, -1);
    }
    if (strncmp(rel, "SMK/", 4) == 0) return add_item(items, src, rel, CAT_MOVIE, tree, -1);
    return add_item(items, src, rel, CAT_COMMON, tree, -1);
}

static int sort_directory(struct items *items, const char *directory,
                          const char *prefix, int tree, int unit)
{
    struct names names;
    size_t i;
    int ok = 1;
    if (!directory || !directory[0] || !is_directory(directory)) return 1;
    list_directory(directory, &names);
    for (i = 0; i < names.count && ok; i++) {
        char src[PATH_CAP];
        char rel[REL_CAP];
        if (!join(src, sizeof(src), directory, names.v[i]) || !is_file(src)) continue;
        snprintf(rel, sizeof(rel), "%s%s", prefix, names.v[i]);
        ok = sort_file(items, src, rel, tree, unit);
    }
    free_names(&names);
    return ok;
}

/* A Macintosh tree: its C2.ENG says so ("Caesar II - Macintosh Version
 * 1.0"), and its speech and music are AIFF. */
static int mac_base(const char *base)
{
    char path[PATH_CAP];
    char line[96];
    unsigned char *text;
    size_t size = 0;
    int mac = 0;
    if (!find_child(path, sizeof(path), base, "C2.ENG", 0) ||
        !(text = read_file(path, 1024 * 1024, &size))) return 0;
    if (eng_string(text, size, 0x0b, 0, line, sizeof(line))) mac = SDL_strcasestr(line, "Macintosh") != NULL;
    free(text);
    return mac;
}

struct game_tree {
    int present;
    int tree;
    char base[PATH_CAP];
    char media[PATH_CAP];
};

/* The DOS and Windows 95 trees in a disc, installation or extracted image.
 * The Windows tree always has C2_START.DAT, a DOS tree never does. */
static void find_trees(const char *root, struct game_tree *dos, struct game_tree *windows)
{
    char hd[PATH_CAP];
    char win[PATH_CAP];
    char win_hd[PATH_CAP];
    char probe[PATH_CAP];
    const char *bases[3] = { NULL, NULL, NULL };
    const char *medias[3] = { NULL, NULL, NULL };
    int i;
    memset(dos, 0, sizeof(*dos));
    memset(windows, 0, sizeof(*windows));
    if (find_child(hd, sizeof(hd), root, "HD", 1)) { bases[0] = hd; medias[0] = root; }
    if (find_child(win, sizeof(win), root, "C2WIN95", 1) &&
        find_child(win_hd, sizeof(win_hd), win, "HD", 1)) { bases[1] = win_hd; medias[1] = win; }
    bases[2] = root; medias[2] = root;
    for (i = 0; i < 3; i++) {
        struct game_tree *slot;
        if (!bases[i] || !find_child(probe, sizeof(probe), bases[i], "C2.ENG", 0)) continue;
        if (mac_base(bases[i])) continue;
        slot = find_child(probe, sizeof(probe), bases[i], "C2_START.DAT", 0) ? windows : dos;
        if (slot->present) continue;
        slot->present = 1;
        slot->tree = slot == windows ? TREE_WINDOWS : TREE_DOS;
        snprintf(slot->base, sizeof(slot->base), "%s", bases[i]);
        snprintf(slot->media, sizeof(slot->media), "%s", medias[i]);
    }
}

static int sort_tree(struct items *items, const struct game_tree *tree, int unit)
{
    static const char *const media[] = { "PL8", "RAW", "SMK", "XMI" };
    size_t i;
    if (!sort_directory(items, tree->base, "", tree->tree, unit)) return 0;
    for (i = 0; i < sizeof(media) / sizeof(media[0]); i++) {
        char directory[PATH_CAP];
        char prefix[8];
        if (!find_child(directory, sizeof(directory), tree->media, media[i], 1)) continue;
        snprintf(prefix, sizeof(prefix), "%s/", media[i]);
        if (!sort_directory(items, directory, prefix, tree->tree, unit)) return 0;
    }
    return 1;
}

/* A folder of movies only: its .SMK files, directly or in SMK/. The Mac
 * release names its intro INTRONEW.SMK. */
static int sort_movies(struct items *items, const char *root)
{
    const char *where[2];
    char smk[PATH_CAP];
    int d;
    where[0] = root;
    where[1] = find_child(smk, sizeof(smk), root, "SMK", 1) ? smk : NULL;
    for (d = 0; d < 2; d++) {
        struct names names;
        size_t i;
        if (!where[d]) continue;
        list_directory(where[d], &names);
        for (i = 0; i < names.count; i++) {
            char src[PATH_CAP];
            char rel[REL_CAP];
            if (!has_extension(names.v[i], ".smk") ||
                !join(src, sizeof(src), where[d], names.v[i]) || !is_file(src)) continue;
            snprintf(rel, sizeof(rel), "SMK/%s",
                     SDL_strcasecmp(names.v[i], "INTRONEW.SMK") == 0 ? "INTRO.SMK" : names.v[i]);
            if (!add_item(items, src, rel, CAT_MOVIE, TREE_OTHER, -1)) {
                free_names(&names);
                return 0;
            }
        }
        free_names(&names);
    }
    return 1;
}

/* A PC installation a few folders below the one chosen. */
static int find_nested_trees(const char *root, int depth,
                             struct game_tree *dos, struct game_tree *windows)
{
    struct names names;
    size_t i;
    int found = 0;
    if (depth <= 0) return 0;
    list_directory(root, &names);
    for (i = 0; i < names.count && !found; i++) {
        char child[PATH_CAP];
        if (!join(child, sizeof(child), root, names.v[i]) || !is_directory(child)) continue;
        find_trees(child, dos, windows);
        found = dos->present || windows->present || find_nested_trees(child, depth - 1, dos, windows);
    }
    free_names(&names);
    return found;
}

struct mac_tree {
    char base[PATH_CAP];      /* an install's Data/HD: the largest one */
    char media[PATH_CAP];     /* the disc's Data: 256, PL8, RAW, SMK, XMI */
    int base_files;
};

static void search_mac(const char *directory, int depth, struct mac_tree *mac)
{
    struct names names;
    size_t i;
    list_directory(directory, &names);
    for (i = 0; i < names.count; i++) {
        char child[PATH_CAP];
        char probe[PATH_CAP];
        if (!join(child, sizeof(child), directory, names.v[i]) || !is_directory(child)) continue;
        if (SDL_strcasecmp(names.v[i], "HD") == 0 && mac_base(child)) {
            int files = count_entries(child);
            if (files > mac->base_files) {
                snprintf(mac->base, sizeof(mac->base), "%s", child);
                mac->base_files = files;
            }
        } else if (SDL_strcasecmp(names.v[i], "Data") == 0 && !mac->media[0] &&
                   (find_child(probe, sizeof(probe), child, "SMK", 1) ||
                    find_child(probe, sizeof(probe), child, "XMI", 1) ||
                    find_child(probe, sizeof(probe), child, "RAW", 1))) {
            snprintf(mac->media, sizeof(mac->media), "%s", child);
        }
        if (depth > 0) search_mac(child, depth - 1, mac);
    }
    free_names(&names);
}

static const char *mac_music_name(const char *name)
{
    size_t i;
    for (i = 0; i < sizeof(mac_music) / sizeof(mac_music[0]); i++) {
        if (SDL_strcasecmp(name, mac_music[i][0]) == 0) return mac_music[i][1];
    }
    return NULL;
}

/* One file of a Mac tree. `in_pl8` marks the disc's PL8 folder; the
 * install's flat HD mixes base and media files. */
static int sort_mac_file(struct items *items, const char *src, const char *file_name,
                         int in_pl8, int unit)
{
    char name[REL_CAP];
    char rel[REL_CAP + 8];
    if (strlen(file_name) + 8 >= sizeof(name)) return 1;
    strcpy(name, file_name);
    upper(name);
    if (!runtime_file(name)) return 1;
    if (has_extension(name, ".xmi")) {
        const char *recording = mac_music_name(name);
        if (is_aiff(src)) {
            if (!recording) return 1;
            snprintf(rel, sizeof(rel), "RAW/%s", recording);
            return add_item_aiff(items, src, rel, CAT_MUSIC_WINDOWS, TREE_OTHER, -1, 1);
        }
        snprintf(rel, sizeof(rel), "XMI/%s", name);
        return add_item(items, src, rel, CAT_MUSIC_DOS, TREE_OTHER, -1);
    }
    if (has_extension(name, ".raw")) {
        if (unit < 0) return 1;
        snprintf(rel, sizeof(rel), "RAW/%s", name);
        return add_item_aiff(items, src, rel, CAT_UNIT, TREE_OTHER, unit, is_aiff(src));
    }
    if (has_extension(name, ".smk")) {
        snprintf(rel, sizeof(rel), "SMK/%s", strcmp(name, "INTRONEW.SMK") == 0 ? "INTRO.SMK" : name);
        if (IN_LIST(rel, release_files) && unit >= 0) {
            return add_item(items, src, rel, CAT_UNIT, TREE_OTHER, unit);
        }
        return add_item(items, src, rel, CAT_MOVIE, TREE_OTHER, -1);
    }
    /* The rest of a Mac tree is not taken: a third of its art differs from
     * the PC's and it has no sound-effect files, so it cannot stand in for
     * a PC installation. Its text identifies the language of its speech. */
    (void)in_pl8;
    if (unit >= 0 && (strcmp(name, "C2.ENG") == 0 || strcmp(name, "HELP.ENG") == 0)) {
        return add_item(items, src, name, CAT_UNIT, TREE_OTHER, unit);
    }
    return 1;
}

static int sort_mac_directory(struct items *items, const char *directory, int in_pl8, int unit)
{
    struct names names;
    size_t i;
    int ok = 1;
    if (!directory || !directory[0]) return 1;
    list_directory(directory, &names);
    for (i = 0; i < names.count && ok; i++) {
        char src[PATH_CAP];
        if (!join(src, sizeof(src), directory, names.v[i]) || !is_file(src)) continue;
        ok = sort_mac_file(items, src, names.v[i], in_pl8, unit);
    }
    free_names(&names);
    return ok;
}

static int sort_mac(const struct mac_tree *mac, struct items *items,
                    struct unit *units, int *unit_count)
{
    static const char *const media[] = { "256", "PL8", "RAW", "SMK", "XMI" };
    int unit = -1;
    size_t i;
    if (mac->base[0]) {
        char c2eng[PATH_CAP];
        unsigned char *text;
        size_t size = 0;
        if (find_child(c2eng, sizeof(c2eng), mac->base, "C2.ENG", 0) &&
            (text = read_file(c2eng, 1024 * 1024, &size))) {
            struct unit *u = &units[0];
            memset(u, 0, sizeof(*u));
            snprintf(u->lang, sizeof(u->lang), "%s", detect_language(text, size));
            if (!valid_tag(u->lang)) snprintf(u->lang, sizeof(u->lang), "und");
            u->tree = TREE_OTHER;
            read_version(text, size, u->version, sizeof(u->version), NULL, 0);
            free(text);
            *unit_count = 1;
            unit = 0;
        }
        if (!sort_mac_directory(items, mac->base, 0, unit)) return 0;
    }
    for (i = 0; mac->media[0] && i < sizeof(media) / sizeof(media[0]); i++) {
        char directory[PATH_CAP];
        if (find_child(directory, sizeof(directory), mac->media, media[i], 1) &&
            !sort_mac_directory(items, directory, strcmp(media[i], "PL8") == 0, unit)) return 0;
    }
    for (i = 0; unit >= 0 && i < items->count; i++) {
        if (items->v[i].category == CAT_UNIT && strncmp(items->v[i].rel, "RAW/", 4) == 0) {
            units[0].speech = 1;
            break;
        }
    }
    return 1;
}

static int sort_source(const char *root, struct items *items,
                       struct unit *units, int *unit_count,
                       char *error, size_t error_capacity)
{
    struct game_tree dos;
    struct game_tree windows;
    const struct game_tree *primary;
    char c2eng[PATH_CAP];
    unsigned char *text;
    size_t size = 0;
    size_t i;
    struct unit *u;

    *unit_count = 0;
    find_trees(root, &dos, &windows);
    if (!dos.present && !windows.present) {
        struct mac_tree mac;
        memset(&mac, 0, sizeof(mac));
        search_mac(root, 4, &mac);
        if (mac.base[0] || mac.media[0]) {
            if (!sort_mac(&mac, items, units, unit_count)) return 0;
            if (items->count == 0) {
                set_error(error, error_capacity, "no Caesar II game data was found there");
                return 0;
            }
            return 1;
        }
        find_nested_trees(root, 3, &dos, &windows);
    }
    if (!dos.present && !windows.present) {
        if (!sort_movies(items, root)) return 0;
        if (items->count == 0) {
            set_error(error, error_capacity, "no Caesar II game data was found there");
            return 0;
        }
        return 1;
    }
    primary = dos.present ? &dos : &windows;
    if (!find_child(c2eng, sizeof(c2eng), primary->base, "C2.ENG", 0) ||
        !(text = read_file(c2eng, 1024 * 1024, &size))) {
        set_error(error, error_capacity, "could not read C2.ENG");
        return 0;
    }
    u = &units[0];
    memset(u, 0, sizeof(*u));
    snprintf(u->lang, sizeof(u->lang), "%s", detect_language(text, size));
    if (!valid_tag(u->lang)) snprintf(u->lang, sizeof(u->lang), "und");
    u->tree = primary->tree;
    read_version(text, size, u->version, sizeof(u->version), NULL, 0);
    free(text);
    *unit_count = 1;
    if (!sort_tree(items, primary, 0)) return 0;
    /* The disc-root XMI of a CD layout sits beside HD/, as media; an
     * installation keeps xmi/ inside its folder. Both are the media parent. */
    if (dos.present && windows.present && !sort_tree(items, &windows, -1)) return 0;
    u->later = dos.present && windows.present;
    for (i = 0; i < items->count; i++) {
        if (items->v[i].category == CAT_UNIT && strncmp(items->v[i].rel, "RAW/", 4) == 0) {
            u->speech = 1;
            break;
        }
    }
    return 1;
}

/* A library, or an unzipped .c2assets: its own manifest says where each
 * file came from. */
static int sort_library(const char *root, struct items *items,
                        struct unit *units, int *unit_count,
                        char *error, size_t error_capacity)
{
    struct manifest m;
    char **found;
    int count = 0;
    int i;
    if (load_manifest(root, &m, error, error_capacity) <= 0) {
        if (error && !error[0]) set_error(error, error_capacity, "the game-data library is unreadable");
        free_manifest(&m);
        return 0;
    }
    *unit_count = m.unit_count;
    memcpy(units, m.units, sizeof(m.units[0]) * (size_t)m.unit_count);
    found = SDL_GlobDirectory(root, NULL, 0, &count);
    for (i = 0; found && i < count; i++) {
        char rel[REL_CAP + 32];
        char src[PATH_CAP];
        char *c;
        int category = -1;
        int unit = -1;
        const char *inner = NULL;
        if (strlen(found[i]) >= sizeof(rel)) continue;
        strcpy(rel, found[i]);
        for (c = rel; *c; c++) if (*c == '\\') *c = '/';
        if (!join(src, sizeof(src), root, found[i]) || !is_file(src)) continue;
        if (SDL_strncasecmp(rel, "common/", 7) == 0) { category = CAT_COMMON; inner = rel + 7; }
        else if (SDL_strncasecmp(rel, "music/dos/", 10) == 0) { category = CAT_MUSIC_DOS; inner = rel + 10; }
        else if (SDL_strncasecmp(rel, "music/windows/", 14) == 0) { category = CAT_MUSIC_WINDOWS; inner = rel + 14; }
        else if (SDL_strncasecmp(rel, "video/", 6) == 0) { category = CAT_MOVIE; inner = rel + 6; }
        else if (SDL_strncasecmp(rel, "language/", 9) == 0) {
            char tag[C2_LIBRARY_TAG_CAPACITY];
            const char *slash = strchr(rel + 9, '/');
            if (slash && (size_t)(slash - (rel + 9)) < sizeof(tag)) {
                snprintf(tag, sizeof(tag), "%.*s", (int)(slash - (rel + 9)), rel + 9);
                unit = find_unit(&m, tag);
                if (unit >= 0) { category = CAT_UNIT; inner = slash + 1; }
            }
        }
        if (category < 0 || !inner[0]) continue;
        if (!add_item(items, src, inner,
                      category, category == CAT_UNIT ? m.units[unit].tree : note_tree(&m, rel),
                      unit)) {
            SDL_free(found);
            free_manifest(&m);
            return 0;
        }
    }
    SDL_free(found);
    free_manifest(&m);
    return 1;
}

/* ------------------------------------------------------------------ */
/* Merging                                                              */

static const char *category_directory(int category)
{
    switch (category) {
    case CAT_MUSIC_DOS: return "music/dos";
    case CAT_MUSIC_WINDOWS: return "music/windows";
    case CAT_MOVIE: return "video";
    default: return "common";
    }
}

static unsigned long movie_pixels(const char *path)
{
    unsigned char header[12];
    size_t got;
    FILE *file = fopen(path, "rb");
    if (!file) return 0;
    got = fread(header, 1, sizeof(header), file);
    fclose(file);
    if (got != sizeof(header) || memcmp(header, "SMK", 3) != 0) return 0;
    return (unsigned long)(header[4] | (header[5] << 8) | (header[6] << 16)) *
           (unsigned long)(header[8] | (header[9] << 8) | (header[10] << 16));
}

/* A scaled movie takes the copy with the most pixels; otherwise, and at
 * equal size, the DOS copy (the Windows re-encodes have fewer colours),
 * then the Mac one; within one origin the higher bitrate. */
static int movie_better(const char *rel, const char *incoming, int incoming_tree,
                        const char *existing, int existing_tree)
{
    const char *name = strrchr(rel, '/');
    int scaled = IN_LIST(name ? name + 1 : rel, scaled_movies);
    if (scaled) {
        unsigned long a = movie_pixels(incoming);
        unsigned long b = movie_pixels(existing);
        if (a != b) return a > b;
    }
    if (incoming_tree != existing_tree) return incoming_tree > existing_tree;
    return file_size(incoming) > file_size(existing);
}

/* complete (with speech) first, then from a DOS tree, then the higher
 * version, then the later pressing (the German original and its 1996
 * rerelease both say "Version 1.0"); an equal one replaces. */
/* A Mac language folder holds only text and speech; a Windows 95 one has
 * all of a release's files, if with fewer colours. */
static int unit_rank(int tree)
{
    return tree == TREE_DOS ? 3 : tree == TREE_WINDOWS ? 2 : 1;
}

static int unit_not_worse(const struct unit *incoming, const struct unit *existing)
{
    int v;
    if (incoming->speech != existing->speech) return incoming->speech > existing->speech;
    if (incoming->tree != existing->tree) return unit_rank(incoming->tree) > unit_rank(existing->tree);
    v = compare_versions(incoming->version, existing->version);
    if (v != 0) return v > 0;
    if (incoming->later != existing->later) return incoming->later > existing->later;
    return 1;
}

struct merge_progress {
    const struct c2_import_progress *progress;
    uint64_t total;
    uint64_t done;
    size_t files;
    size_t total_files;
};

static void step(struct merge_progress *p, uint64_t bytes)
{
    p->done += bytes;
    p->files++;
    if (p->progress && p->progress->update) {
        p->progress->update(p->progress->userdata, "Adding to your game data",
                            p->done, p->total, p->files, p->total_files);
    }
}

static int merge(const char *library, struct items *items,
                 struct unit *units, int unit_count, int move,
                 const struct c2_import_progress *progress,
                 char *error, size_t error_capacity)
{
    struct manifest m;
    struct merge_progress mp;
    size_t i;
    int u;
    int changed = 0;

    if (load_manifest(library, &m, error, error_capacity) < 0) return 0;
    memset(&mp, 0, sizeof(mp));
    mp.progress = progress;
    mp.total_files = items->count;
    for (i = 0; i < items->count; i++) mp.total += items->v[i].size;

    for (u = 0; u < unit_count; u++) {
        int existing = find_unit(&m, units[u].lang);
        char directory[PATH_CAP];
        units[u].accepted = 0;
        if (existing >= 0 && !unit_not_worse(&units[u], &m.units[existing])) continue;
        /* Forget the old folder before touching it: a folder without a
         * manifest line is never read. */
        drop_unit(&m, units[u].lang);
        if (!save_manifest(library, &m)) goto write_failed;
        snprintf(directory, sizeof(directory), "%s/language/%s", library, units[u].lang);
        remove_tree(directory);
        if (!make_directories(directory)) goto write_failed;
        units[u].accepted = 1;
        changed = 1;
    }

    for (i = 0; i < items->count; i++) {
        const struct item *it = &items->v[i];
        char dest[PATH_CAP];
        char key[REL_CAP + 32];
        int write = 0;
        if (it->category == CAT_UNIT) {
            if (it->unit < 0 || it->unit >= unit_count || !units[it->unit].accepted) {
                step(&mp, it->size);
                continue;
            }
            snprintf(dest, sizeof(dest), "%s/language/%s/%s", library,
                     units[it->unit].lang, it->rel);
            if (!place_file(it->src, dest, move, it->aiff)) goto write_failed;
            step(&mp, it->size);
            continue;
        }
        snprintf(key, sizeof(key), "%s/%s", category_directory(it->category), it->rel);
        if (!join(dest, sizeof(dest), library, key)) continue;
        if (!is_file(dest)) {
            write = 1;
        } else if (it->category == CAT_MOVIE) {
            write = movie_better(it->rel, it->src, it->tree, dest, note_tree(&m, key));
        } else if (it->category == CAT_COMMON || it->category == CAT_MUSIC_DOS) {
            write = it->tree > note_tree(&m, key);
        } else if (it->category == CAT_MUSIC_WINDOWS) {
            /* The same recordings everywhere; the Mac copies lose a few
             * bytes at the end, so the longer one is the whole piece. */
            write = it->size > file_size(dest);
        }
        if (write) {
            if (!place_file(it->src, dest, move, it->aiff) || !set_note(&m, key, it->tree)) goto write_failed;
            changed = 1;
        }
        step(&mp, it->size);
    }

    for (u = 0; u < unit_count; u++) {
        if (!units[u].accepted || m.unit_count >= C2_LIBRARY_MAX_LANGUAGES) continue;
        m.units[m.unit_count++] = units[u];
    }
    if (!save_manifest(library, &m)) goto write_failed;
    (void)changed;
    free_manifest(&m);
    return 1;

write_failed:
    free_manifest(&m);
    set_error(error, error_capacity, "could not write the game data (is the disk full?)");
    return 0;
}

/* ------------------------------------------------------------------ */
/* Describing                                                           */

int c2_library_path(char *out, size_t capacity, const char *game_data_root)
{
    return join(out, capacity, game_data_root, "library");
}

static int count_files(const char *directory, const char *extension)
{
    struct names names;
    size_t i;
    int count = 0;
    if (!is_directory(directory)) return 0;
    list_directory(directory, &names);
    for (i = 0; i < names.count; i++) {
        if (!extension || has_extension(names.v[i], extension)) count++;
    }
    free_names(&names);
    return count;
}

static void describe_library(const char *library, struct c2_library_summary *s)
{
    struct manifest m;
    char path[PATH_CAP];
    char probe[PATH_CAP];
    int i;
    memset(s, 0, sizeof(*s));
    if (load_manifest(library, &m, NULL, 0) <= 0) {
        free_manifest(&m);
        return;
    }
    for (i = 0; i < m.unit_count && s->language_count < C2_LIBRARY_MAX_LANGUAGES; i++) {
        struct c2_library_language *l = &s->languages[s->language_count];
        unsigned char *text;
        size_t size = 0;
        char token[24];
        snprintf(path, sizeof(path), "%s/language/%s", library, m.units[i].lang);
        if (!find_child(probe, sizeof(probe), path, "C2.ENG", 0)) continue;
        memset(l, 0, sizeof(*l));
        snprintf(l->tag, sizeof(l->tag), "%s", m.units[i].lang);
        l->windows = m.units[i].tree == TREE_WINDOWS;
        l->mac = m.units[i].tree == TREE_OTHER;
        snprintf(probe, sizeof(probe), "%s/RAW", path);
        l->speech = count_files(probe, ".raw") > 0;
        text = read_file(path[0] ? (snprintf(probe, sizeof(probe), "%s/C2.ENG", path), probe) : probe,
                         1024 * 1024, &size);
        if (text) {
            read_version(text, size, token, sizeof(token), l->version, sizeof(l->version));
            free(text);
        }
        snprintf(probe, sizeof(probe), "%s/HELP.ENG", path);
        if (is_file(probe)) s->playable = 1;
        s->language_count++;
    }
    snprintf(path, sizeof(path), "%s/common", library);
    if (count_files(path, NULL) < 50) s->playable = 0;
    snprintf(path, sizeof(path), "%s/music/dos", library);
    s->music_dos = (find_child(probe, sizeof(probe), path, "CAESAR.OPL", 0) ||
                    find_child(probe, sizeof(probe), path, "CAESAR.AD", 0)) &&
                   (snprintf(path, sizeof(path), "%s/music/dos/XMI", library),
                    count_files(path, ".xmi") > 0);
    snprintf(path, sizeof(path), "%s/music/windows/RAW", library);
    s->music_windows = find_child(probe, sizeof(probe), path, "CITYPRO0.RAW", 0);
    snprintf(path, sizeof(path), "%s/video/SMK", library);
    s->movies = count_files(path, ".smk");
    for (i = 0; i < (int)(sizeof(scaled_movies) / sizeof(scaled_movies[0])); i++) {
        /* Larger than the DOS 320x152. */
        snprintf(probe, sizeof(probe), "%s/video/SMK/%s", library, scaled_movies[i]);
        if (movie_pixels(probe) > 320ul * 152ul) s->movies_enhanced++;
    }
    {
        char **found;
        int count = 0;
        int f;
        found = SDL_GlobDirectory(library, NULL, 0, &count);
        for (f = 0; found && f < count; f++) {
            if (join(path, sizeof(path), library, found[f])) s->bytes += file_size(path);
        }
        SDL_free(found);
    }
    free_manifest(&m);
}

static void write_summary(const char *game_data_root, const struct c2_library_summary *s)
{
    char local[PATH_CAP];
    char path[PATH_CAP];
    char temporary[PATH_CAP];
    FILE *file;
    int i;
    if (!join(local, sizeof(local), game_data_root, "local") || !make_directories(local) ||
        !join(path, sizeof(path), local, "summary") ||
        !join(temporary, sizeof(temporary), local, "summary.new")) return;
    file = fopen(temporary, "wb");
    if (!file) return;
    fprintf(file, "%s\nplayable %d\n", SUMMARY_FORMAT, s->playable);
    for (i = 0; i < s->language_count; i++) {
        fprintf(file, "language %s %s %s %s\n", s->languages[i].tag,
                s->languages[i].speech ? "speech" : "text",
                s->languages[i].windows ? "windows" : s->languages[i].mac ? "mac" : "dos",
                s->languages[i].version[0] ? s->languages[i].version : "-");
    }
    if (s->music_dos) fprintf(file, "music dos\n");
    if (s->music_windows) fprintf(file, "music windows\n");
    fprintf(file, "movies %d %d\n", s->movies, s->movies_enhanced);
    fprintf(file, "bytes %llu\n", (unsigned long long)s->bytes);
    if (fclose(file) != 0) return;
    commit_file(temporary, path);
}

int c2_library_describe(const char *game_data_root, struct c2_library_summary *summary)
{
    char library[PATH_CAP];
    memset(summary, 0, sizeof(*summary));
    if (!c2_library_path(library, sizeof(library), game_data_root)) return 0;
    describe_library(library, summary);
    write_summary(game_data_root, summary);
    return 1;
}

const char *c2_library_pick_speech(const struct c2_library_summary *s, const char *wanted)
{
    int i;
    if (wanted && wanted[0]) {
        for (i = 0; i < s->language_count; i++) {
            if (strcmp(s->languages[i].tag, wanted) == 0 && s->languages[i].speech) return s->languages[i].tag;
        }
    }
    for (i = 0; i < s->language_count; i++) {
        if (strcmp(s->languages[i].tag, "en") == 0 && s->languages[i].speech) return s->languages[i].tag;
    }
    for (i = 0; i < s->language_count; i++) {
        if (s->languages[i].speech) return s->languages[i].tag;
    }
    if (wanted && wanted[0]) {
        for (i = 0; i < s->language_count; i++) {
            if (strcmp(s->languages[i].tag, wanted) == 0) return s->languages[i].tag;
        }
    }
    return s->language_count ? s->languages[0].tag : "";
}

/* ------------------------------------------------------------------ */
/* The runtime's view                                                   */

static int add_root(struct c2_asset_layout *layout, const char *base, const char *media)
{
    struct c2_asset_root *r;
    if (layout->count >= C2_LIBRARY_MAX_ROOTS || !is_directory(base)) return 1;
    r = &layout->roots[layout->count];
    memset(r, 0, sizeof(*r));
    if (strlen(base) >= sizeof(r->base) || strlen(media) >= sizeof(r->media)) return 0;
    strcpy(r->base, base);
    strcpy(r->media, media);
    layout->count++;
    return 1;
}

static int add_library_root(struct c2_asset_layout *layout, const char *library, const char *rel)
{
    char path[PATH_CAP];
    int before = layout->count;
    if (!join(path, sizeof(path), library, rel)) return 0;
    if (!add_root(layout, path, path)) return 0;
    if (layout->count > before) layout->roots[before].library = 1;
    return 1;
}

int c2_library_layout(const char *root, const char *speech,
                      struct c2_asset_layout *layout,
                      char *error, size_t error_capacity)
{
    char library[PATH_CAP];
    char probe[PATH_CAP];
    memset(layout, 0, sizeof(*layout));
    if (!root || !root[0]) {
        set_error(error, error_capacity, "no game data");
        return 0;
    }
    if (find_child(probe, sizeof(probe), root, LIBRARY_MARKER, 0)) {
        snprintf(library, sizeof(library), "%s", root);
    } else if (!(join(library, sizeof(library), root, "library") &&
                 find_child(probe, sizeof(probe), library, LIBRARY_MARKER, 0))) {
        library[0] = '\0';
    }
    if (library[0]) {
        /* No file is read here, only listed: on the web this runs on the
         * page's main thread, and Firefox never answers a read of OPFS
         * made there. A language folder counts when it has C2.ENG; it has
         * speech when it has RAW/. */
        struct c2_library_summary summary;
        struct names names;
        char languages[PATH_CAP];
        char probe[PATH_CAP];
        const char *chosen;
        int i;
        size_t n;
        char unit[64];
        if (!join(probe, sizeof(probe), library, "common") || !is_directory(probe)) {
            set_error(error, error_capacity,
                      "the game data is incomplete; add a PC installation or disc");
            return 0;
        }
        memset(&summary, 0, sizeof(summary));
        if (!join(languages, sizeof(languages), library, "language")) return 0;
        list_directory(languages, &names);
        qsort(names.v, names.count, sizeof(names.v[0]), compare_strings);
        for (n = 0; n < names.count && summary.language_count < C2_LIBRARY_MAX_LANGUAGES; n++) {
            char folder[PATH_CAP];
            struct c2_library_language *l = &summary.languages[summary.language_count];
            if (!valid_tag(names.v[n]) || !join(folder, sizeof(folder), languages, names.v[n]) ||
                !join(probe, sizeof(probe), folder, "C2.ENG") || !is_file(probe)) continue;
            snprintf(l->tag, sizeof(l->tag), "%s", names.v[n]);
            l->speech = join(probe, sizeof(probe), folder, "RAW") && is_directory(probe);
            summary.language_count++;
        }
        free_names(&names);
        if (summary.language_count == 0) {
            set_error(error, error_capacity, "no game data has been added yet");
            return 0;
        }
        chosen = c2_library_pick_speech(&summary, speech);
        snprintf(layout->speech, sizeof(layout->speech), "%s", chosen);
        snprintf(unit, sizeof(unit), "language/%s", chosen);
        if (!add_library_root(layout, library, unit)) return 0;
        /* Files a text-only folder lacks come from another language. */
        for (i = 0; i < summary.language_count; i++) {
            if (strcmp(summary.languages[i].tag, chosen) == 0) continue;
            if (strcmp(summary.languages[i].tag, "en") != 0) continue;
            snprintf(unit, sizeof(unit), "language/%s", summary.languages[i].tag);
            if (!add_library_root(layout, library, unit)) return 0;
        }
        for (i = 0; i < summary.language_count; i++) {
            if (strcmp(summary.languages[i].tag, chosen) == 0 ||
                strcmp(summary.languages[i].tag, "en") == 0) continue;
            snprintf(unit, sizeof(unit), "language/%s", summary.languages[i].tag);
            if (!add_library_root(layout, library, unit)) return 0;
        }
        return add_library_root(layout, library, "common") &&
               add_library_root(layout, library, "video") &&
               add_library_root(layout, library, "music/dos") &&
               add_library_root(layout, library, "music/windows");
    }
    {
        /* A raw tree read in place (--asset-root): DOS first, the Windows
         * tree behind it for the recordings. */
        struct game_tree dos;
        struct game_tree windows;
        find_trees(root, &dos, &windows);
        if (!dos.present && !windows.present) {
            /* A plain folder; whether it holds the game is checked when the
             * runtime reads C2.ENG and HELP.ENG. */
            if (!is_directory(root)) {
                set_error(error, error_capacity, "no Caesar II game data was found there");
                return 0;
            }
            return add_root(layout, root, root);
        }
        if (dos.present && !add_root(layout, dos.base, dos.media)) return 0;
        if (windows.present && !add_root(layout, windows.base, windows.media)) return 0;
        return 1;
    }
}

/* ------------------------------------------------------------------ */
/* Import, migration, removal, export                                   */

/* `consume`: the source is deleted afterwards, so its files may be moved. */
static int import_one(const char *game_data_root, const char *source,
                      const struct c2_import_progress *progress, int consume,
                      char *error, size_t error_capacity)
{
    char library[PATH_CAP];
    char local[PATH_CAP];
    char staging[PATH_CAP];
    char root[PATH_CAP];
    char probe[PATH_CAP];
    struct items items;
    struct unit units[C2_LIBRARY_MAX_LANGUAGES];
    int unit_count = 0;
    int in_place = 0;
    int ok;

    memset(&items, 0, sizeof(items));
    if (!c2_library_path(library, sizeof(library), game_data_root) ||
        !join(local, sizeof(local), game_data_root, "local") ||
        !join(staging, sizeof(staging), local, "staging") ||
        !make_directories(library) || !make_directories(local)) {
        set_error(error, error_capacity, "could not create the game-data folder");
        return 0;
    }
    if (strcmp(source, library) == 0) {
        set_error(error, error_capacity, "that is the game data already in use");
        return 0;
    }
    remove_tree(staging);
    if (!c2_import_stage(source, staging, progress, root, sizeof(root), &in_place,
                         error, error_capacity)) {
        remove_tree(staging);
        return 0;
    }
    if (find_child(probe, sizeof(probe), root, LIBRARY_MARKER, 0)) {
        ok = sort_library(root, &items, units, &unit_count, error, error_capacity);
    } else {
        ok = sort_source(root, &items, units, &unit_count, error, error_capacity);
    }
    if (ok) {
        ok = merge(library, &items, units, unit_count, !in_place || consume, progress,
                   error, error_capacity);
    }
    free(items.v);
    remove_tree(staging);
    return ok;
}

int c2_library_import(const char *game_data_root, const char *source,
                      const struct c2_import_progress *progress,
                      char *error, size_t error_capacity)
{
    struct c2_library_summary summary;
    int ok;
    if (error && error_capacity) error[0] = '\0';
    ok = import_one(game_data_root, source, progress, 0, error, error_capacity);
    c2_library_describe(game_data_root, &summary);
    return ok;
}

static int hex_key(const char *name)
{
    size_t i;
    if (strlen(name) != 16) return 0;
    for (i = 0; i < 16; i++) if (!isxdigit((unsigned char)name[i])) return 0;
    return 1;
}

int c2_library_migrate(const char *game_data_root,
                       const struct c2_import_progress *progress,
                       char *error, size_t error_capacity)
{
    struct names names;
    size_t i;
    int migrated = 0;
    if (!is_directory(game_data_root)) return 0;
    list_directory(game_data_root, &names);
    for (i = 0; i < names.count; i++) {
        char old[PATH_CAP];
        char marker[PATH_CAP];
        char ignored[256];
        if (!hex_key(names.v[i]) || !join(old, sizeof(old), game_data_root, names.v[i]) ||
            !join(marker, sizeof(marker), old, ".complete")) continue;
        /* An unfinished or unreadable old cache has nothing to give. */
        if (is_file(marker) && import_one(game_data_root, old, progress, 1, ignored, sizeof(ignored))) {
            migrated++;
        }
        remove_tree(old);
    }
    free_names(&names);
    if (migrated) {
        struct c2_library_summary summary;
        c2_library_describe(game_data_root, &summary);
    }
    (void)error;
    (void)error_capacity;
    return migrated;
}

int c2_library_remove(const char *game_data_root)
{
    char path[PATH_CAP];
    int ok = 1;
    if (c2_library_path(path, sizeof(path), game_data_root)) ok = remove_tree(path) && ok;
    if (join(path, sizeof(path), game_data_root, "local")) ok = remove_tree(path) && ok;
    return ok;
}

int c2_library_export(const char *game_data_root, const char *zip_path,
                      const struct c2_import_progress *progress,
                      char *error, size_t error_capacity)
{
    char library[PATH_CAP];
    struct c2_library_summary summary;
    if (!c2_library_path(library, sizeof(library), game_data_root)) return 0;
    describe_library(library, &summary);
    if (!summary.playable) {
        set_error(error, error_capacity, "there is no game data to export");
        return 0;
    }
    return c2_zip_write_tree(library, zip_path, LIBRARY_MARKER, progress, error, error_capacity);
}
