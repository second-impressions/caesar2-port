#include "c2_import.h"

#include <SDL3/SDL.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define C2_IMPORT_PATH_CAPACITY 4096

struct file_reader {
    FILE *file;
};

static void set_error(char *error, size_t capacity, const char *message)
{
    if (error && capacity) snprintf(error, capacity, "%s", message ? message : "import failed");
}

static void report_progress(const struct c2_import_progress *progress,
                            const char *phase, uint64_t completed,
                            uint64_t total, size_t files, size_t total_files)
{
    if (progress != NULL && progress->update != NULL) {
        progress->update(progress->userdata, phase, completed, total,
                         files, total_files);
    }
}

static int file_read_at(void *userdata, uint64_t offset, void *buffer,
                        size_t size, size_t *read_out)
{
    struct file_reader *reader = userdata;
    if (read_out) *read_out = 0;
#if PORT_PLATFORM_WIN32
    if (_fseeki64(reader->file, (__int64)offset, SEEK_SET) != 0) return 0;
#else
    if (fseeko(reader->file, (off_t)offset, SEEK_SET) != 0) return 0;
#endif
    *read_out = fread(buffer, 1, size, reader->file);
    return *read_out == size || feof(reader->file);
}

static int open_file_source(const char *path, struct file_reader *file,
                            struct c2_source_reader *source)
{
    SDL_PathInfo info;
    if (!SDL_GetPathInfo(path, &info) || info.type != SDL_PATHTYPE_FILE) return 0;
    file->file = fopen(path, "rb");
    if (!file->file) return 0;
    source->userdata = file;
    source->size = info.size;
    source->read_at = file_read_at;
    return 1;
}

static int runtime_path(const char *path)
{
    static const char *extensions[] = {
        ".ENG", ".PL8", ".RAW", ".SMK", ".XMI", ".WAV",
        ".256", ".DAT", ".GD8", ".OPL", ".AD"
    };
    const char *dot;
    size_t i;
    if (SDL_strcasecmp(path, "C2PACK.JSN") == 0 ||
        SDL_strcasecmp(path, "C2PACK.IDX") == 0) return 1;
    if (SDL_strncasecmp(path, "OBJECTS/", 8) == 0) return 1;
    dot = strrchr(path, '.');
    if (!dot) return 0;
    for (i = 0; i < sizeof(extensions) / sizeof(extensions[0]); i++) {
        if (SDL_strcasecmp(dot, extensions[i]) == 0) return 1;
    }
    return 0;
}

static int make_parents(const char *path)
{
    char copy[C2_IMPORT_PATH_CAPACITY];
    char *p;
    if (strlen(path) >= sizeof(copy)) return 0;
    strcpy(copy, path);
    for (p = copy + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            if (!SDL_CreateDirectory(copy) && !SDL_GetPathInfo(copy, NULL)) return 0;
            *p = '/';
        }
    }
    return 1;
}

int c2_iso_extract(const struct c2_source_reader *source,
                   const char *destination,
                   const struct c2_import_progress *progress,
                   char *error, size_t error_capacity)
{
    struct c2_iso_catalog catalog;
    uint64_t total_bytes = 0;
    uint64_t completed_bytes = 0;
    size_t total_files = 0;
    size_t completed_files = 0;
    size_t i;
    if (!c2_iso_catalog_open(source, &catalog, error, error_capacity)) return 0;
    for (i = 0; i < catalog.count; i++) {
        if (runtime_path(catalog.entries[i].path)) {
            total_bytes += catalog.entries[i].size;
            total_files++;
        }
    }
    report_progress(progress, "Extracting disc image", 0, total_bytes,
                    0, total_files);
    if (!SDL_CreateDirectory(destination) && !SDL_GetPathInfo(destination, NULL)) {
        c2_iso_catalog_close(&catalog); set_error(error, error_capacity, SDL_GetError()); return 0;
    }
    for (i = 0; i < catalog.count; i++) {
        const struct c2_iso_entry *entry = &catalog.entries[i];
        char output[C2_IMPORT_PATH_CAPACITY];
        unsigned char buffer[65536];
        uint64_t offset = 0;
        FILE *file;
        if (!runtime_path(entry->path)) continue;
        if (snprintf(output, sizeof(output), "%s/%s", destination, entry->path) >= (int)sizeof(output) ||
            !make_parents(output)) {
            c2_iso_catalog_close(&catalog); set_error(error, error_capacity, "ISO output path is too long"); return 0;
        }
        file = fopen(output, "wb");
        if (!file) { c2_iso_catalog_close(&catalog); set_error(error, error_capacity, "could not create ISO output"); return 0; }
        while (offset < entry->size) {
            size_t wanted = sizeof(buffer);
            size_t got = 0;
            if ((uint64_t)wanted > entry->size - offset) wanted = (size_t)(entry->size - offset);
            if (!c2_iso_entry_read(source, entry, offset, buffer, wanted, &got) || got != wanted ||
                fwrite(buffer, 1, got, file) != got) {
                fclose(file); c2_iso_catalog_close(&catalog); set_error(error, error_capacity, "could not extract ISO file"); return 0;
            }
            offset += got;
            completed_bytes += got;
            report_progress(progress, "Extracting disc image",
                            completed_bytes, total_bytes,
                            completed_files, total_files);
        }
        if (fclose(file) != 0) { c2_iso_catalog_close(&catalog); return 0; }
        completed_files++;
        report_progress(progress, "Extracting disc image",
                        completed_bytes, total_bytes,
                        completed_files, total_files);
    }
    c2_iso_catalog_close(&catalog);
    return 1;
}

static int extension_is(const char *path, const char *extension)
{
    const char *dot = strrchr(path, '.');
    return dot && SDL_strcasecmp(dot, extension) == 0;
}

static int join_path(char *output, size_t capacity, const char *left, const char *right)
{
    size_t n = strlen(left);
    int result = snprintf(output, capacity, "%s%s%s", left,
                          n && left[n - 1] == '/' ? "" : "/", right);
    return result >= 0 && (size_t)result < capacity;
}

static uint64_t source_key(const char *path, const SDL_PathInfo *info)
{
    uint64_t hash = 1469598103934665603ULL;
    const unsigned char *p = (const unsigned char *)path;
    while (*p) { hash ^= *p++; hash *= 1099511628211ULL; }
    hash ^= info->size; hash *= 1099511628211ULL;
    hash ^= (uint64_t)info->modify_time; hash *= 1099511628211ULL;
    return hash;
}

static int import_iso_file(const char *path, const char *destination,
                           const struct c2_import_progress *progress,
                           char *error, size_t error_capacity)
{
    struct file_reader file;
    struct c2_source_reader source;
    int ok;
    if (!open_file_source(path, &file, &source)) { set_error(error, error_capacity, "could not open ISO"); return 0; }
    ok = c2_iso_extract(&source, destination, progress, error, error_capacity);
    fclose(file.file);
    return ok;
}

/* A bare BIN carries everything the CUE would tell us: the mode byte of
 * sector 0 selects MODE1/MODE2 and every supported disc is one data track
 * starting at 00:00:00. */
static int import_raw_bin(const char *path, const char *destination,
                          const struct c2_import_progress *progress,
                          char *error, size_t error_capacity)
{
    struct file_reader file;
    struct c2_source_reader raw_source;
    struct c2_source_reader iso_source;
    struct c2_raw_cd_reader adapter;
    unsigned char head[16];
    size_t got = 0;
    enum c2_cd_sector_mode mode;
    int ok;
    if (!open_file_source(path, &file, &raw_source)) { set_error(error, error_capacity, "could not open BIN"); return 0; }
    if (!raw_source.read_at(raw_source.userdata, 0, head, sizeof(head), &got) || got != sizeof(head)) {
        fclose(file.file); set_error(error, error_capacity, "could not read BIN"); return 0;
    }
    mode = head[15] == 2 ? C2_CD_MODE2_2352 : C2_CD_MODE1_2352;
    if (!c2_raw_cd_reader_init(&adapter, &raw_source, mode, error, error_capacity)) { fclose(file.file); return 0; }
    c2_raw_cd_source(&adapter, &iso_source);
    ok = c2_iso_extract(&iso_source, destination, progress, error, error_capacity);
    fclose(file.file);
    return ok;
}

/* ------------------------------------------------------------------ */
/* Classification                                                      */

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

static int child_of_type(char *out, size_t capacity, const char *directory,
                         const char *name, SDL_PathType wanted)
{
    struct child_probe probe;
    SDL_PathInfo info;
    probe.wanted = name;
    probe.found[0] = '\0';
    SDL_EnumerateDirectory(directory, probe_child, &probe);
    if (!probe.found[0] || !join_path(out, capacity, directory, probe.found)) return 0;
    return SDL_GetPathInfo(out, &info) && info.type == wanted;
}

static int has_core_files(const char *directory)
{
    char a[C2_IMPORT_PATH_CAPACITY];
    return child_of_type(a, sizeof(a), directory, "C2.ENG", SDL_PATHTYPE_FILE) &&
           child_of_type(a, sizeof(a), directory, "HELP.ENG", SDL_PATHTYPE_FILE);
}

/* 0 = not an installation; 1 = plain (C2.ENG at top); 2 = HD/ or C2WIN95/HD/. */
static int layout_at(const char *directory)
{
    char a[C2_IMPORT_PATH_CAPACITY];
    char b[C2_IMPORT_PATH_CAPACITY];
    if (child_of_type(a, sizeof(a), directory, "HD", SDL_PATHTYPE_DIRECTORY) &&
        has_core_files(a)) return 2;
    if (child_of_type(a, sizeof(a), directory, "C2WIN95", SDL_PATHTYPE_DIRECTORY) &&
        child_of_type(b, sizeof(b), a, "HD", SDL_PATHTYPE_DIRECTORY) &&
        has_core_files(b)) return 2;
    if (has_core_files(directory)) return 1;
    return 0;
}

static int parent_directory(char *path)
{
    char *slash = strrchr(path, '/');
#if PORT_PLATFORM_WIN32
    char *back = strrchr(path, '\\');
    if (back && (!slash || back > slash)) slash = back;
#endif
    if (!slash || slash == path) return 0;
    *slash = '\0';
    return path[0] != '\0';
}

/* Walk from `start` upward looking for an installation root. Picking HD/
 * itself or a file inside it must still land on the directory that holds
 * the media siblings, so a CD-style parent beats a plain match. */
static int resolve_install_root(const char *start, char *root, size_t capacity)
{
    char current[C2_IMPORT_PATH_CAPACITY];
    int level;
    if (strlen(start) >= sizeof(current)) return 0;
    strcpy(current, start);
    for (level = 0; level < 4; level++) {
        int here = layout_at(current);
        if (here == 2) { snprintf(root, capacity, "%s", current); return 1; }
        if (here == 1) {
            char parent[C2_IMPORT_PATH_CAPACITY];
            strcpy(parent, current);
            if (parent_directory(parent) && layout_at(parent) == 2) {
                snprintf(root, capacity, "%s", parent);
            } else {
                snprintf(root, capacity, "%s", current);
            }
            return 1;
        }
        if (!parent_directory(current)) break;
    }
    return 0;
}

static enum c2_source_kind sniff_file(const char *path)
{
    static const unsigned char sync[12] = {
        0x00, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x00
    };
    unsigned char head[16];
    unsigned char pvd[8];
    FILE *file = fopen(path, "rb");
    enum c2_source_kind kind = C2_SOURCE_NONE;
    if (!file) return C2_SOURCE_NONE;
    if (fread(head, 1, sizeof(head), file) == sizeof(head)) {
        if (memcmp(head, "PK\x03\x04", 4) == 0) kind = C2_SOURCE_ZIP;
        else if (memcmp(head, sync, sizeof(sync)) == 0 &&
                 (head[15] == 1 || head[15] == 2)) kind = C2_SOURCE_RAW_BIN;
        else if (
#if PORT_PLATFORM_WIN32
                 _fseeki64(file, (__int64)16 * 2048, SEEK_SET) == 0 &&
#else
                 fseeko(file, (off_t)16 * 2048, SEEK_SET) == 0 &&
#endif
                 fread(pvd, 1, sizeof(pvd), file) == sizeof(pvd) &&
                 memcmp(pvd + 1, "CD001", 5) == 0) kind = C2_SOURCE_ISO;
    }
    fclose(file);
    if (kind == C2_SOURCE_NONE && extension_is(path, ".cue")) kind = C2_SOURCE_CUE;
    return kind;
}

int c2_import_classify(const char *path, enum c2_source_kind *kind,
                       char *root, size_t root_capacity,
                       char *error, size_t error_capacity)
{
    SDL_PathInfo info;
    char probe[C2_IMPORT_PATH_CAPACITY];
    *kind = C2_SOURCE_NONE;
    if (root_capacity) root[0] = '\0';
    if (!path || !path[0]) { set_error(error, error_capacity, "no game data selected"); return 0; }
    if (c2_cdrom_is_device_path(path)) {
        *kind = C2_SOURCE_CDROM;
        snprintf(root, root_capacity, "%s", path);
        return 1;
    }
    if (!SDL_GetPathInfo(path, &info)) { set_error(error, error_capacity, "game-data source does not exist"); return 0; }
    if (info.type == SDL_PATHTYPE_DIRECTORY) {
        if (child_of_type(probe, sizeof(probe), path, "C2PACK.IDX", SDL_PATHTYPE_FILE)) {
            *kind = C2_SOURCE_PACK_DIRECTORY;
            snprintf(root, root_capacity, "%s", path);
            return 1;
        }
        if (resolve_install_root(path, root, root_capacity)) {
            *kind = C2_SOURCE_DIRECTORY;
            return 1;
        }
        set_error(error, error_capacity, "no Caesar II installation was found in this folder");
        return 0;
    }
    if (info.type != SDL_PATHTYPE_FILE) { set_error(error, error_capacity, "unsupported game-data source"); return 0; }
    *kind = sniff_file(path);
    if (*kind != C2_SOURCE_NONE) {
        snprintf(root, root_capacity, "%s", path);
        return 1;
    }
    /* Not an archive or image: maybe a file inside an installation. */
    if (strlen(path) < sizeof(probe)) {
        strcpy(probe, path);
        if (parent_directory(probe) && resolve_install_root(probe, root, root_capacity)) {
            *kind = C2_SOURCE_DIRECTORY;
            return 1;
        }
    }
    set_error(error, error_capacity, "not a Caesar II installation, disc image, ZIP or asset pack");
    return 0;
}

const char *c2_source_kind_name(enum c2_source_kind kind)
{
    switch (kind) {
    case C2_SOURCE_DIRECTORY: return "Installation folder";
    case C2_SOURCE_PACK_DIRECTORY: return "Asset pack folder";
    case C2_SOURCE_ZIP: return "ZIP archive";
    case C2_SOURCE_ISO: return "Disc image (ISO)";
    case C2_SOURCE_RAW_BIN: return "Disc image (BIN)";
    case C2_SOURCE_CUE: return "Disc image (CUE/BIN)";
    case C2_SOURCE_CDROM: return "CD-ROM drive";
    default: return "Unknown";
    }
}

static int import_cdrom_device(const char *device_path,
                               const char *destination,
                               const struct c2_import_progress *progress,
                               char *error, size_t error_capacity)
{
    struct c2_cdrom_reader cdrom;
    struct c2_source_reader source;
    int ok;
    if (!c2_cdrom_open(device_path, &cdrom, error, error_capacity)) return 0;
    c2_cdrom_source(&cdrom, &source);
    ok = c2_iso_extract(&source, destination, progress, error, error_capacity);
    c2_cdrom_close(&cdrom);
    return ok;
}

static int import_cue(const char *cue_path, const char *destination,
                      const struct c2_import_progress *progress,
                      char *error, size_t error_capacity)
{
    SDL_PathInfo info;
    char *cue;
    FILE *stream;
    char bin_name[1024];
    char bin_path[C2_IMPORT_PATH_CAPACITY];
    char directory[C2_IMPORT_PATH_CAPACITY];
    char *slash;
    enum c2_cd_sector_mode mode;
    struct file_reader raw_file;
    struct c2_source_reader raw_source;
    struct c2_source_reader iso_source;
    struct c2_raw_cd_reader adapter;
    int ok;

    if (!SDL_GetPathInfo(cue_path, &info) || info.size == 0 || info.size > 65536) {
        set_error(error, error_capacity, "invalid CUE file"); return 0;
    }
    cue = malloc((size_t)info.size + 1);
    stream = fopen(cue_path, "rb");
    if (!cue || !stream || fread(cue, 1, (size_t)info.size, stream) != info.size) {
        free(cue); if (stream) fclose(stream); set_error(error, error_capacity, "could not read CUE"); return 0;
    }
    fclose(stream); cue[info.size] = '\0';
    if (!c2_cue_parse_single_data_track(cue, bin_name, sizeof(bin_name), &mode, error, error_capacity)) { free(cue); return 0; }
    free(cue);
    if (strlen(cue_path) >= sizeof(directory)) return 0;
    strcpy(directory, cue_path);
    slash = strrchr(directory, '/');
#if PORT_PLATFORM_WIN32
    { char *back = strrchr(directory, '\\'); if (back && (!slash || back > slash)) slash = back; }
#endif
    if (slash) *slash = '\0'; else strcpy(directory, ".");
    if (!join_path(bin_path, sizeof(bin_path), directory, bin_name) ||
        !open_file_source(bin_path, &raw_file, &raw_source)) {
        set_error(error, error_capacity, "CUE BIN file was not found"); return 0;
    }
    if (!c2_raw_cd_reader_init(&adapter, &raw_source, mode, error, error_capacity)) { fclose(raw_file.file); return 0; }
    c2_raw_cd_source(&adapter, &iso_source);
    ok = c2_iso_extract(&iso_source, destination, progress, error, error_capacity);
    fclose(raw_file.file);
    return ok;
}

/* Stream a wrapped disc image straight out of the ZIP: no staging copy. */
static int import_zipped_iso(const char *zip_path, const char *entry,
                             const char *destination,
                             const struct c2_import_progress *progress,
                             char *error, size_t error_capacity)
{
    struct c2_zip_stream stream;
    struct c2_source_reader source;
    int ok;
    if (!c2_zip_stream_open(&stream, zip_path, entry, error, error_capacity)) return 0;
    c2_zip_stream_source(&stream, &source);
    ok = c2_iso_extract(&source, destination, progress, error, error_capacity);
    c2_zip_stream_close(&stream);
    return ok;
}

static int import_zipped_cue(const char *zip_path, const char *cue_entry,
                             const char *destination,
                             const struct c2_import_progress *progress,
                             char *error, size_t error_capacity)
{
    char cue[65536 + 1];
    char bin_name[1024];
    char bin_entry[C2_IMPORT_PATH_CAPACITY];
    size_t cue_size;
    const char *slash;
    enum c2_cd_sector_mode mode;
    struct c2_zip_stream stream;
    struct c2_source_reader raw_source;
    struct c2_source_reader iso_source;
    struct c2_raw_cd_reader adapter;
    int ok;

    if (!c2_zip_read_entry(zip_path, cue_entry, cue, sizeof(cue) - 1, &cue_size,
                           error, error_capacity)) return 0;
    cue[cue_size] = '\0';
    if (!c2_cue_parse_single_data_track(cue, bin_name, sizeof(bin_name), &mode,
                                        error, error_capacity)) return 0;
    /* The CUE names its BIN relative to itself; keep the ZIP directory. */
    slash = strrchr(cue_entry, '/');
    { const char *back = strrchr(cue_entry, '\\'); if (back && (!slash || back > slash)) slash = back; }
    if (slash) {
        int n = snprintf(bin_entry, sizeof(bin_entry), "%.*s/%s",
                         (int)(slash - cue_entry), cue_entry, bin_name);
        if (n < 0 || (size_t)n >= sizeof(bin_entry)) return 0;
    } else {
        snprintf(bin_entry, sizeof(bin_entry), "%s", bin_name);
    }
    if (!c2_zip_stream_open(&stream, zip_path, bin_entry, error, error_capacity)) {
        set_error(error, error_capacity, "CUE BIN file was not found in the ZIP");
        return 0;
    }
    c2_zip_stream_source(&stream, &raw_source);
    if (!c2_raw_cd_reader_init(&adapter, &raw_source, mode, error, error_capacity)) {
        c2_zip_stream_close(&stream);
        return 0;
    }
    c2_raw_cd_source(&adapter, &iso_source);
    ok = c2_iso_extract(&iso_source, destination, progress, error, error_capacity);
    c2_zip_stream_close(&stream);
    return ok;
}

static int import_zip(const char *zip_path, const char *destination,
                      const struct c2_import_progress *progress,
                      char *error, size_t error_capacity)
{
    enum c2_zip_content content;
    char entry[512];
    if (!c2_zip_probe(zip_path, &content, entry, sizeof(entry), error, error_capacity)) return 0;
    switch (content) {
    case C2_ZIP_RUNTIME_FILES:
        return c2_zip_extract(zip_path, destination, progress, error, error_capacity);
    case C2_ZIP_ISO_IMAGE:
        return import_zipped_iso(zip_path, entry, destination, progress, error, error_capacity);
    case C2_ZIP_CUE_IMAGE:
        return import_zipped_cue(zip_path, entry, destination, progress, error, error_capacity);
    default:
        set_error(error, error_capacity, "ZIP contains no Caesar II game files");
        return 0;
    }
}

int c2_import_path(const char *source_path, const char *cache_root,
                   const char *asset_profile,
                   const struct c2_import_progress *progress,
                   char *asset_root, size_t asset_root_capacity,
                   char *error, size_t error_capacity)
{
    SDL_PathInfo info;
    char game_data_root[C2_IMPORT_PATH_CAPACITY];
    char destination[C2_IMPORT_PATH_CAPACITY];
    char marker[C2_IMPORT_PATH_CAPACITY];
    char key[32];
    char root[C2_IMPORT_PATH_CAPACITY];
    enum c2_source_kind kind;
    FILE *done;
    int ok;

    if (!c2_import_classify(source_path, &kind, root, sizeof(root), error, error_capacity)) return 0;
    switch (kind) {
    case C2_SOURCE_PACK_DIRECTORY:
        return c2_pack_activate(root, asset_profile, asset_root, asset_root_capacity,
                                error, error_capacity);
    case C2_SOURCE_DIRECTORY:
        if (strlen(root) >= asset_root_capacity) return 0;
        strcpy(asset_root, root);
        return 1;
    case C2_SOURCE_CDROM: {
        /* Key the cache by the disc's primary volume descriptor: the
         * device path is identical for every disc in the drive and the
         * device node reports no useful size or modify time. */
        struct c2_cdrom_reader cdrom;
        if (!c2_cdrom_open(source_path, &cdrom, error, error_capacity)) return 0;
        snprintf(key, sizeof(key), "%016llx",
                 (unsigned long long)cdrom.fingerprint);
        c2_cdrom_close(&cdrom);
        break;
    }
    default:
        if (!SDL_GetPathInfo(source_path, &info)) { set_error(error, error_capacity, "game-data source does not exist"); return 0; }
        snprintf(key, sizeof(key), "%016llx", (unsigned long long)source_key(source_path, &info));
        break;
    }
    if (!join_path(game_data_root, sizeof(game_data_root), cache_root, "game-data") ||
        !join_path(destination, sizeof(destination), game_data_root, key) ||
        !join_path(marker, sizeof(marker), destination, ".complete")) return 0;
    if (SDL_GetPathInfo(marker, NULL)) goto activate;
    if (!make_parents(marker) || (!SDL_CreateDirectory(destination) && !SDL_GetPathInfo(destination, NULL))) {
        set_error(error, error_capacity, "could not create game-data cache"); return 0;
    }
    switch (kind) {
    case C2_SOURCE_CDROM:
        ok = import_cdrom_device(source_path, destination, progress, error, error_capacity); break;
    case C2_SOURCE_ZIP:
        ok = import_zip(source_path, destination, progress, error, error_capacity); break;
    case C2_SOURCE_ISO:
        ok = import_iso_file(source_path, destination, progress, error, error_capacity); break;
    case C2_SOURCE_RAW_BIN:
        ok = import_raw_bin(source_path, destination, progress, error, error_capacity); break;
    case C2_SOURCE_CUE:
        ok = import_cue(source_path, destination, progress, error, error_capacity); break;
    default:
        set_error(error, error_capacity, "unsupported game-data source type"); return 0;
    }
    if (!ok) return 0;
    done = fopen(marker, "wb");
    if (!done) return 0;
    if (fclose(done) != 0) return 0;

activate:
    {
        char index_path[C2_IMPORT_PATH_CAPACITY];
        if (join_path(index_path, sizeof(index_path), destination, "C2PACK.IDX") &&
            SDL_GetPathInfo(index_path, NULL)) {
            return c2_pack_activate(destination, asset_profile,
                                    asset_root, asset_root_capacity,
                                    error, error_capacity);
        }
    }
    if (strlen(destination) >= asset_root_capacity) return 0;
    strcpy(asset_root, destination);
    return 1;
}
