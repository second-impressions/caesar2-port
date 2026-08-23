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
                   char *error, size_t error_capacity)
{
    struct c2_iso_catalog catalog;
    size_t i;
    if (!c2_iso_catalog_open(source, &catalog, error, error_capacity)) return 0;
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
        }
        if (fclose(file) != 0) { c2_iso_catalog_close(&catalog); return 0; }
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
                           char *error, size_t error_capacity)
{
    struct file_reader file;
    struct c2_source_reader source;
    int ok;
    if (!open_file_source(path, &file, &source)) { set_error(error, error_capacity, "could not open ISO"); return 0; }
    ok = c2_iso_extract(&source, destination, error, error_capacity);
    fclose(file.file);
    return ok;
}

static int import_cue(const char *cue_path, const char *destination,
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
    ok = c2_iso_extract(&iso_source, destination, error, error_capacity);
    fclose(raw_file.file);
    return ok;
}

int c2_import_path(const char *source_path, const char *cache_root,
                   const char *asset_profile,
                   char *asset_root, size_t asset_root_capacity,
                   char *error, size_t error_capacity)
{
    SDL_PathInfo info;
    char game_data_root[C2_IMPORT_PATH_CAPACITY];
    char destination[C2_IMPORT_PATH_CAPACITY];
    char marker[C2_IMPORT_PATH_CAPACITY];
    char key[32];
    FILE *done;
    int ok;

    if (!SDL_GetPathInfo(source_path, &info)) { set_error(error, error_capacity, "game-data source does not exist"); return 0; }
    if (info.type == SDL_PATHTYPE_DIRECTORY) {
        char index_path[C2_IMPORT_PATH_CAPACITY];
        if (join_path(index_path, sizeof(index_path), source_path, "C2PACK.IDX") &&
            SDL_GetPathInfo(index_path, NULL)) {
            return c2_pack_activate(source_path, asset_profile,
                                    asset_root, asset_root_capacity,
                                    error, error_capacity);
        }
        if (strlen(source_path) >= asset_root_capacity) return 0;
        strcpy(asset_root, source_path);
        return 1;
    }
    snprintf(key, sizeof(key), "%016llx", (unsigned long long)source_key(source_path, &info));
    if (!join_path(game_data_root, sizeof(game_data_root), cache_root, "game-data") ||
        !join_path(destination, sizeof(destination), game_data_root, key) ||
        !join_path(marker, sizeof(marker), destination, ".complete")) return 0;
    if (SDL_GetPathInfo(marker, NULL)) goto activate;
    if (!make_parents(marker) || (!SDL_CreateDirectory(destination) && !SDL_GetPathInfo(destination, NULL))) {
        set_error(error, error_capacity, "could not create game-data cache"); return 0;
    }
    if (extension_is(source_path, ".zip") || extension_is(source_path, ".c2assets"))
        ok = c2_zip_extract(source_path, destination, error, error_capacity);
    else if (extension_is(source_path, ".iso"))
        ok = import_iso_file(source_path, destination, error, error_capacity);
    else if (extension_is(source_path, ".cue"))
        ok = import_cue(source_path, destination, error, error_capacity);
    else {
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
