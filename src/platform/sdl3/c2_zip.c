#include "c2_import.h"

#include <archive.h>
#include <archive_entry.h>
#include <SDL3/SDL.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define C2_IMPORT_MAX_ENTRIES 8192u
#define C2_IMPORT_MAX_PATH 512u
#define C2_IMPORT_MAX_BYTES (2ULL * 1024ULL * 1024ULL * 1024ULL)

struct zip_item {
    char *archive_path;
    char *logical_path;
    uint64_t size;
};

static void set_error(char *error, size_t capacity, const char *message)
{
    if (error && capacity) snprintf(error, capacity, "%s", message ? message : "archive error");
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

static int safe_path(const char *input, char *output, size_t capacity)
{
    size_t out = 0;
    const char *p = input;
    if (!input || !*input || *input == '/' || *input == '\\' || strchr(input, ':')) return 0;
    while (*p) {
        const char *start;
        size_t length;
        while (*p == '/' || *p == '\\') p++;
        start = p;
        while (*p && *p != '/' && *p != '\\') p++;
        length = (size_t)(p - start);
        if (!length) break;
        if ((length == 1 && start[0] == '.') ||
            (length == 2 && start[0] == '.' && start[1] == '.')) return 0;
        if (out && out + 1 < capacity) output[out++] = '/';
        if (out + length >= capacity) return 0;
        while (length--) {
            unsigned char c = (unsigned char)*start++;
            if (c < 0x20 || c >= 0x7f) return 0;
            output[out++] = (char)c;
        }
    }
    if (!out) return 0;
    output[out] = '\0';
    return 1;
}

static char *copy_string(const char *value)
{
    size_t length = strlen(value) + 1;
    char *copy = malloc(length);
    if (copy) memcpy(copy, value, length);
    return copy;
}

static int same_fold(const char *a, const char *b)
{
    while (*a || *b) {
        unsigned char x = (unsigned char)*a++;
        unsigned char y = (unsigned char)*b++;
        if (x == '\\') x = '/';
        if (y == '\\') y = '/';
        if (toupper(x) != toupper(y)) return 0;
    }
    return 1;
}

static int open_zip(struct archive **out, const char *path, char *error, size_t error_capacity)
{
    struct archive *a = archive_read_new();
    int result;
    if (!a) return 0;
    archive_read_support_filter_none(a);
    archive_read_support_format_zip(a);
    result = archive_read_open_filename(a, path, 1024 * 1024);
    if (result != ARCHIVE_OK) {
        set_error(error, error_capacity, archive_error_string(a));
        archive_read_free(a);
        return 0;
    }
    *out = a;
    return 1;
}

static void free_items(struct zip_item *items, size_t count)
{
    size_t i;
    for (i = 0; i < count; i++) {
        free(items[i].archive_path);
        free(items[i].logical_path);
    }
    free(items);
}

static int make_parents(const char *path)
{
    char copy[C2_IMPORT_MAX_PATH * 2];
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

int c2_zip_extract(const char *zip_path, const char *destination,
                   char *error, size_t error_capacity)
{
    struct archive *a;
    struct archive_entry *entry;
    struct zip_item *items = NULL;
    size_t count = 0;
    size_t capacity = 0;
    uint64_t total = 0;
    char common[C2_IMPORT_MAX_PATH] = {0};
    int common_valid = 1;
    int result;
    size_t i;

    if (!open_zip(&a, zip_path, error, error_capacity)) return 0;
    while ((result = archive_read_next_header(a, &entry)) == ARCHIVE_OK) {
        const char *raw = archive_entry_pathname(entry);
        char normalized[C2_IMPORT_MAX_PATH];
        const char *slash;
        uint64_t size;
        if (archive_entry_filetype(entry) == AE_IFDIR) {
            archive_read_data_skip(a);
            continue;
        }
        if (archive_entry_filetype(entry) != AE_IFREG || !safe_path(raw, normalized, sizeof(normalized))) {
            set_error(error, error_capacity, "ZIP contains an unsafe non-regular entry");
            archive_read_free(a); free_items(items, count); return 0;
        }
        if (!runtime_path(normalized)) {
            archive_read_data_skip(a);
            continue;
        }
        size = (uint64_t)archive_entry_size(entry);
        if (size > C2_IMPORT_MAX_BYTES || total > C2_IMPORT_MAX_BYTES - size || count >= C2_IMPORT_MAX_ENTRIES) {
            set_error(error, error_capacity, "ZIP exceeds import quotas");
            archive_read_free(a); free_items(items, count); return 0;
        }
        total += size;
        if (count == capacity) {
            size_t new_capacity = capacity ? capacity * 2 : 128;
            struct zip_item *grown = realloc(items, new_capacity * sizeof(*grown));
            if (!grown) { archive_read_free(a); free_items(items, count); return 0; }
            items = grown; capacity = new_capacity;
        }
        items[count].archive_path = copy_string(raw);
        items[count].logical_path = copy_string(normalized);
        items[count].size = size;
        if (!items[count].archive_path || !items[count].logical_path) {
            archive_read_free(a); free_items(items, count + 1); return 0;
        }
        slash = strchr(normalized, '/');
        if (!slash) common_valid = 0;
        else if (count == 0) {
            size_t n = (size_t)(slash - normalized);
            memcpy(common, normalized, n); common[n] = '\0';
        } else if (strlen(common) != (size_t)(slash - normalized) ||
                   SDL_strncasecmp(common, normalized, strlen(common)) != 0) {
            common_valid = 0;
        }
        count++;
        archive_read_data_skip(a);
    }
    archive_read_free(a);
    if (result != ARCHIVE_EOF || count == 0) {
        set_error(error, error_capacity, "could not enumerate ZIP"); free_items(items, count); return 0;
    }
    for (i = 0; i < count; i++) {
        const char *logical = items[i].logical_path;
        char *trimmed;
        size_t j;
        if (common_valid) logical = strchr(logical, '/') + 1;
        trimmed = copy_string(logical);
        free(items[i].logical_path);
        items[i].logical_path = trimmed;
        if (!items[i].logical_path || !*items[i].logical_path) {
            set_error(error, error_capacity, "invalid outer ZIP directory"); free_items(items, count); return 0;
        }
        for (j = 0; j < i; j++) {
            if (same_fold(items[j].logical_path, items[i].logical_path)) {
                set_error(error, error_capacity, "ZIP contains case-colliding paths"); free_items(items, count); return 0;
            }
        }
    }

    if (!SDL_CreateDirectory(destination) && !SDL_GetPathInfo(destination, NULL)) {
        set_error(error, error_capacity, SDL_GetError()); free_items(items, count); return 0;
    }
    if (!open_zip(&a, zip_path, error, error_capacity)) { free_items(items, count); return 0; }
    i = 0;
    while ((result = archive_read_next_header(a, &entry)) == ARCHIVE_OK) {
        const char *raw = archive_entry_pathname(entry);
        char output[C2_IMPORT_MAX_PATH * 2];
        FILE *file;
        char buffer[65536];
        la_ssize_t got;
        if (archive_entry_filetype(entry) == AE_IFDIR) { archive_read_data_skip(a); continue; }
        if (i < count && strcmp(raw, items[i].archive_path) != 0) {
            archive_read_data_skip(a);
            continue;
        }
        if (i >= count || strcmp(raw, items[i].archive_path) != 0 ||
            snprintf(output, sizeof(output), "%s/%s", destination, items[i].logical_path) >= (int)sizeof(output) ||
            !make_parents(output)) {
            set_error(error, error_capacity, "ZIP changed or output path is invalid");
            archive_read_free(a); free_items(items, count); return 0;
        }
        file = fopen(output, "wb");
        if (!file) { set_error(error, error_capacity, "could not create imported file"); archive_read_free(a); free_items(items, count); return 0; }
        while ((got = archive_read_data(a, buffer, sizeof(buffer))) > 0) {
            if (fwrite(buffer, 1, (size_t)got, file) != (size_t)got) { fclose(file); archive_read_free(a); free_items(items, count); return 0; }
        }
        if (got < 0 || fclose(file) != 0) { set_error(error, error_capacity, archive_error_string(a)); archive_read_free(a); free_items(items, count); return 0; }
        i++;
    }
    archive_read_free(a);
    free_items(items, count);
    if (result != ARCHIVE_EOF || i != count) { set_error(error, error_capacity, "ZIP extraction ended early"); return 0; }
    return 1;
}
