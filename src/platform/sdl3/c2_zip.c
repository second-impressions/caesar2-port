/*
 * ZIP reader for the game-data importer: central directory, stored and
 * Deflate entries, ZIP64 sizes. Everything the importer needs to read a
 * zipped installation or a zipped disc image, over zlib alone.
 */
#include "c2_import.h"

#include <SDL3/SDL.h>
#include <zlib.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define C2_IMPORT_MAX_ENTRIES 8192u
#define C2_IMPORT_MAX_PATH 512u
#define C2_IMPORT_MAX_BYTES (2ULL * 1024ULL * 1024ULL * 1024ULL)

/* The central directory of a game-data ZIP is a few hundred KiB at most. */
#define C2_ZIP_MAX_CENTRAL_DIRECTORY (64u * 1024u * 1024u)
#define C2_ZIP_MAX_ENTRIES 65536u
#define C2_ZIP_SCRATCH 65536u

#define ZIP_LOCAL_HEADER 0x04034b50u
#define ZIP_CENTRAL_HEADER 0x02014b50u
#define ZIP_END_RECORD 0x06054b50u
#define ZIP_END_RECORD64 0x06064b50u
#define ZIP_END_LOCATOR64 0x07064b50u
#define ZIP_METHOD_STORED 0
#define ZIP_METHOD_DEFLATE 8
#define ZIP_FLAG_ENCRYPTED 0x0001u

struct zip_entry {
    char *name;
    uint64_t compressed_size;
    uint64_t size;
    uint64_t local_offset;
    uint32_t crc;
    unsigned method;
    unsigned flags;
    int directory;
};

struct zip_archive {
    FILE *file;
    struct zip_entry *entries;
    size_t count;
};

/* One open entry: file position, inflater, progress through the data. */
struct zip_cursor {
    struct zip_archive *archive;
    const struct zip_entry *entry;
    uint64_t data_offset;
    uint64_t compressed_position;
    z_stream inflater;
    int inflating;
    unsigned char *input;
};

static void set_error(char *error, size_t capacity, const char *message)
{
    if (error && capacity) snprintf(error, capacity, "%s", message ? message : "archive error");
}

static void report_progress(const struct c2_import_progress *progress,
                            uint64_t completed, uint64_t total,
                            size_t files, size_t total_files)
{
    if (progress != NULL && progress->update != NULL) {
        progress->update(progress->userdata, "Extracting asset archive",
                         completed, total, files, total_files);
    }
}

static int seek_to(FILE *file, uint64_t offset)
{
#if PORT_PLATFORM_WIN32
    return _fseeki64(file, (__int64)offset, SEEK_SET) == 0;
#else
    return fseeko(file, (off_t)offset, SEEK_SET) == 0;
#endif
}

static uint64_t file_size(FILE *file)
{
#if PORT_PLATFORM_WIN32
    if (_fseeki64(file, 0, SEEK_END) != 0) return 0;
    return (uint64_t)_ftelli64(file);
#else
    if (fseeko(file, 0, SEEK_END) != 0) return 0;
    return (uint64_t)ftello(file);
#endif
}

static uint16_t le16(const unsigned char *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t le32(const unsigned char *p) { return (uint32_t)le16(p) | ((uint32_t)le16(p + 2) << 16); }
static uint64_t le64(const unsigned char *p) { return (uint64_t)le32(p) | ((uint64_t)le32(p + 4) << 32); }

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

/* ---- central directory --------------------------------------------- */

static void close_archive(struct zip_archive *archive)
{
    size_t i;
    if (!archive) return;
    if (archive->file) fclose(archive->file);
    for (i = 0; i < archive->count; i++) free(archive->entries[i].name);
    free(archive->entries);
    free(archive);
}

/* Locate the end-of-central-directory record in the file's tail, then the
 * ZIP64 record when the classic one saturates. Returns the directory's
 * offset, size and entry count. */
static int locate_directory(FILE *file, uint64_t size, uint64_t *offset,
                            uint64_t *length, uint64_t *count)
{
    unsigned char tail[65536 + 22];
    size_t tail_size = size < sizeof(tail) ? (size_t)size : sizeof(tail);
    uint64_t tail_offset = size - tail_size;
    size_t i;

    if (size < 22 || !seek_to(file, tail_offset) ||
        fread(tail, 1, tail_size, file) != tail_size) return 0;
    for (i = tail_size - 22; ; i--) {
        if (le32(tail + i) == ZIP_END_RECORD && i + 22 + le16(tail + i + 20) <= tail_size) {
            uint64_t record = tail_offset + i;
            *count = le16(tail + i + 10);
            *length = le32(tail + i + 12);
            *offset = le32(tail + i + 16);
            if (*count == 0xffff || *length == 0xffffffffu || *offset == 0xffffffffu) {
                unsigned char locator[20];
                unsigned char record64[56];
                if (record < 20 || !seek_to(file, record - 20) ||
                    fread(locator, 1, 20, file) != 20 ||
                    le32(locator) != ZIP_END_LOCATOR64 ||
                    !seek_to(file, le64(locator + 8)) ||
                    fread(record64, 1, 56, file) != 56 ||
                    le32(record64) != ZIP_END_RECORD64) return 0;
                *count = le64(record64 + 32);
                *length = le64(record64 + 40);
                *offset = le64(record64 + 48);
            }
            return 1;
        }
        if (i == 0) break;
    }
    return 0;
}

/* ZIP64 extra field: only the fields that saturated are present, in order. */
static void apply_zip64(struct zip_entry *entry, const unsigned char *extra, size_t length)
{
    while (length >= 4) {
        unsigned id = le16(extra);
        size_t field = le16(extra + 2);
        if (field > length - 4) return;
        if (id == 0x0001) {
            const unsigned char *p = extra + 4;
            size_t left = field;
            if (entry->size == 0xffffffffu && left >= 8) { entry->size = le64(p); p += 8; left -= 8; }
            if (entry->compressed_size == 0xffffffffu && left >= 8) { entry->compressed_size = le64(p); p += 8; left -= 8; }
            if (entry->local_offset == 0xffffffffu && left >= 8) { entry->local_offset = le64(p); }
            return;
        }
        extra += 4 + field;
        length -= 4 + field;
    }
}

static struct zip_archive *open_archive(const char *path, char *error, size_t error_capacity)
{
    struct zip_archive *archive = calloc(1, sizeof(*archive));
    unsigned char *directory = NULL;
    uint64_t offset, length, count, size;
    size_t pos = 0;
    size_t i;

    if (!archive) return NULL;
    archive->file = fopen(path, "rb");
    if (!archive->file) { set_error(error, error_capacity, "could not open ZIP"); goto fail; }
    size = file_size(archive->file);
    if (!locate_directory(archive->file, size, &offset, &length, &count)) {
        set_error(error, error_capacity, "not a ZIP archive (no central directory)"); goto fail;
    }
    if (length > C2_ZIP_MAX_CENTRAL_DIRECTORY || count > C2_ZIP_MAX_ENTRIES || offset > size - length) {
        set_error(error, error_capacity, "ZIP central directory is too large"); goto fail;
    }
    directory = malloc((size_t)length + 1);
    archive->entries = calloc((size_t)count + 1, sizeof(*archive->entries));
    if (!directory || !archive->entries) goto fail;
    if (!seek_to(archive->file, offset) ||
        fread(directory, 1, (size_t)length, archive->file) != (size_t)length) {
        set_error(error, error_capacity, "could not read ZIP central directory"); goto fail;
    }
    for (i = 0; i < count; i++) {
        struct zip_entry *entry = &archive->entries[i];
        const unsigned char *h = directory + pos;
        size_t name_length, extra_length, comment_length;
        if (pos + 46 > length || le32(h) != ZIP_CENTRAL_HEADER) {
            set_error(error, error_capacity, "ZIP central directory is corrupt"); goto fail;
        }
        name_length = le16(h + 28);
        extra_length = le16(h + 30);
        comment_length = le16(h + 32);
        if (pos + 46 + name_length + extra_length + comment_length > length) {
            set_error(error, error_capacity, "ZIP central directory is corrupt"); goto fail;
        }
        entry->flags = le16(h + 8);
        entry->method = le16(h + 10);
        entry->crc = le32(h + 16);
        entry->compressed_size = le32(h + 20);
        entry->size = le32(h + 24);
        entry->local_offset = le32(h + 42);
        entry->name = malloc(name_length + 1);
        if (!entry->name) goto fail;
        memcpy(entry->name, h + 46, name_length);
        entry->name[name_length] = '\0';
        apply_zip64(entry, h + 46 + name_length, extra_length);
        entry->directory = (name_length > 0 && entry->name[name_length - 1] == '/') ||
                           (le32(h + 38) & 0x10u) != 0;
        archive->count++;
        pos += 46 + name_length + extra_length + comment_length;
    }
    free(directory);
    return archive;
fail:
    free(directory);
    close_archive(archive);
    return NULL;
}

static const struct zip_entry *find_entry(const struct zip_archive *archive, const char *name)
{
    size_t i;
    for (i = 0; i < archive->count; i++) {
        if (!archive->entries[i].directory && same_fold(archive->entries[i].name, name)) {
            return &archive->entries[i];
        }
    }
    return NULL;
}

/* ---- entry data ------------------------------------------------------ */

static void close_cursor(struct zip_cursor *cursor)
{
    if (cursor->inflating) inflateEnd(&cursor->inflater);
    cursor->inflating = 0;
    free(cursor->input);
    cursor->input = NULL;
}

static const char *cursor_open(struct zip_cursor *cursor, struct zip_archive *archive,
                               const struct zip_entry *entry)
{
    unsigned char local[30];
    memset(cursor, 0, sizeof(*cursor));
    cursor->archive = archive;
    cursor->entry = entry;
    if (entry->flags & ZIP_FLAG_ENCRYPTED) return "encrypted ZIP entries are not supported";
    if (entry->method != ZIP_METHOD_STORED && entry->method != ZIP_METHOD_DEFLATE) {
        return "ZIP entry uses an unsupported compression method";
    }
    if (!seek_to(archive->file, entry->local_offset) ||
        fread(local, 1, 30, archive->file) != 30 || le32(local) != ZIP_LOCAL_HEADER) {
        return "ZIP local header is corrupt";
    }
    cursor->data_offset = entry->local_offset + 30 + le16(local + 26) + le16(local + 28);
    if (entry->method == ZIP_METHOD_DEFLATE) {
        cursor->input = malloc(C2_ZIP_SCRATCH);
        if (!cursor->input) return "out of memory";
        if (inflateInit2(&cursor->inflater, -MAX_WBITS) != Z_OK) return "could not initialize inflate";
        cursor->inflating = 1;
    }
    return NULL;
}

/* Rewind to the start of the entry data without re-parsing anything. */
static int cursor_rewind(struct zip_cursor *cursor)
{
    cursor->compressed_position = 0;
    if (cursor->inflating) {
        cursor->inflater.avail_in = 0; /* drop buffered input; reset keeps it */
        return inflateReset(&cursor->inflater) == Z_OK;
    }
    return 1;
}

/* Read `size` bytes of entry data starting at `position` (stored) or
 * continuing the inflate stream (deflate). Returns bytes produced. */
static size_t cursor_read(struct zip_cursor *cursor, uint64_t position, void *buffer, size_t size)
{
    struct zip_archive *archive = cursor->archive;
    const struct zip_entry *entry = cursor->entry;
    if (position >= entry->size) return 0;
    if (size > entry->size - position) size = (size_t)(entry->size - position);
    if (!cursor->inflating) {
        if (!seek_to(archive->file, cursor->data_offset + position)) return 0;
        return fread(buffer, 1, size, archive->file);
    }
    cursor->inflater.next_out = buffer;
    cursor->inflater.avail_out = (uInt)size;
    while (cursor->inflater.avail_out > 0) {
        int result;
        if (cursor->inflater.avail_in == 0) {
            uint64_t left = entry->compressed_size - cursor->compressed_position;
            size_t wanted = left > C2_ZIP_SCRATCH ? C2_ZIP_SCRATCH : (size_t)left;
            if (wanted == 0) break;
            if (!seek_to(archive->file, cursor->data_offset + cursor->compressed_position)) break;
            wanted = fread(cursor->input, 1, wanted, archive->file);
            if (wanted == 0) break;
            cursor->compressed_position += wanted;
            cursor->inflater.next_in = cursor->input;
            cursor->inflater.avail_in = (uInt)wanted;
        }
        result = inflate(&cursor->inflater, Z_NO_FLUSH);
        if (result == Z_STREAM_END) break;
        if (result != Z_OK) break;
    }
    return size - cursor->inflater.avail_out;
}

/* ---- public API -------------------------------------------------------- */

static int disc_image_kind(const char *normalized)
{
    const char *dot = strrchr(normalized, '.');
    if (!dot) return 0;
    if (SDL_strcasecmp(dot, ".cue") == 0) return C2_ZIP_CUE_IMAGE;
    if (SDL_strcasecmp(dot, ".iso") == 0) return C2_ZIP_ISO_IMAGE;
    return 0;
}

int c2_zip_probe(const char *zip_path, enum c2_zip_content *content,
                 char *entry, size_t entry_capacity,
                 char *error, size_t error_capacity)
{
    struct zip_archive *archive;
    char cue[C2_IMPORT_MAX_PATH] = {0};
    char iso[C2_IMPORT_MAX_PATH] = {0};
    size_t i;

    *content = C2_ZIP_EMPTY;
    if (entry_capacity) entry[0] = '\0';
    archive = open_archive(zip_path, error, error_capacity);
    if (!archive) return 0;
    for (i = 0; i < archive->count; i++) {
        const struct zip_entry *item = &archive->entries[i];
        char normalized[C2_IMPORT_MAX_PATH];
        if (item->directory || !safe_path(item->name, normalized, sizeof(normalized))) continue;
        if (runtime_path(normalized)) {
            *content = C2_ZIP_RUNTIME_FILES;
            close_archive(archive);
            return 1;
        }
        switch (disc_image_kind(normalized)) {
        case C2_ZIP_CUE_IMAGE:
            if (!cue[0]) snprintf(cue, sizeof(cue), "%s", item->name);
            break;
        case C2_ZIP_ISO_IMAGE:
            if (!iso[0]) snprintf(iso, sizeof(iso), "%s", item->name);
            break;
        default:
            break;
        }
    }
    close_archive(archive);
    if (cue[0]) {
        *content = C2_ZIP_CUE_IMAGE;
        snprintf(entry, entry_capacity, "%s", cue);
    } else if (iso[0]) {
        *content = C2_ZIP_ISO_IMAGE;
        snprintf(entry, entry_capacity, "%s", iso);
    }
    return 1;
}

int c2_zip_read_entry(const char *zip_path, const char *entry,
                      void *buffer, size_t capacity, size_t *size_out,
                      char *error, size_t error_capacity)
{
    struct zip_archive *archive;
    const struct zip_entry *item;
    struct zip_cursor cursor;
    const char *problem;
    size_t done = 0;
    uint64_t size;
    uint32_t crc;

    *size_out = 0;
    archive = open_archive(zip_path, error, error_capacity);
    if (!archive) return 0;
    item = find_entry(archive, entry);
    if (!item) {
        set_error(error, error_capacity, "ZIP entry was not found");
        close_archive(archive); return 0;
    }
    if (item->size > capacity) {
        set_error(error, error_capacity, "ZIP entry is too large");
        close_archive(archive); return 0;
    }
    problem = cursor_open(&cursor, archive, item);
    if (problem) {
        set_error(error, error_capacity, problem);
        close_cursor(&cursor); close_archive(archive); return 0;
    }
    size = item->size;
    crc = item->crc;
    while (done < size) {
        size_t got = cursor_read(&cursor, done, (unsigned char *)buffer + done, (size_t)size - done);
        if (got == 0) break;
        done += got;
    }
    close_cursor(&cursor);
    close_archive(archive);
    if (done != size || crc32(crc32(0L, Z_NULL, 0), buffer, (uInt)done) != crc) {
        set_error(error, error_capacity, "could not read ZIP entry");
        return 0;
    }
    *size_out = done;
    return 1;
}

/* Streaming: stored entries seek freely; Deflate entries decompress forward
 * and rewind the inflater for a backward read. */
struct zip_stream_state {
    struct zip_archive *archive;
    struct zip_cursor cursor;
};

static int stream_read_at(void *userdata, uint64_t offset, void *buffer,
                          size_t size, size_t *read_out)
{
    struct c2_zip_stream *stream = userdata;
    struct zip_stream_state *state = stream->state;
    size_t done = 0;

    if (read_out) *read_out = 0;
    if (offset > stream->size) return 0;
    if (size > stream->size - offset) size = (size_t)(stream->size - offset);
    if (!state->cursor.inflating) {
        done = cursor_read(&state->cursor, offset, buffer, size);
        stream->position = offset + done;
        if (read_out) *read_out = done;
        return done == size;
    }
    if (offset < stream->position) {
        if (!cursor_rewind(&state->cursor)) return 0;
        stream->position = 0;
        stream->rewinds++;
    }
    while (stream->position < offset) {
        uint64_t gap = offset - stream->position;
        size_t wanted = gap > C2_ZIP_SCRATCH ? C2_ZIP_SCRATCH : (size_t)gap;
        size_t got = cursor_read(&state->cursor, stream->position, stream->scratch, wanted);
        if (got == 0) return 0;
        stream->position += got;
    }
    while (done < size) {
        size_t got = cursor_read(&state->cursor, stream->position,
                                 (unsigned char *)buffer + done, size - done);
        if (got == 0) break;
        done += got;
        stream->position += got;
    }
    if (read_out) *read_out = done;
    return done == size;
}

int c2_zip_stream_open(struct c2_zip_stream *stream, const char *zip_path,
                       const char *entry, char *error, size_t error_capacity)
{
    struct zip_stream_state *state;
    const struct zip_entry *item;
    const char *problem;

    memset(stream, 0, sizeof(*stream));
    state = calloc(1, sizeof(*state));
    stream->state = state;
    stream->scratch = malloc(C2_ZIP_SCRATCH);
    if (!state || !stream->scratch) {
        c2_zip_stream_close(stream);
        set_error(error, error_capacity, "out of memory");
        return 0;
    }
    state->archive = open_archive(zip_path, error, error_capacity);
    if (!state->archive) { c2_zip_stream_close(stream); return 0; }
    item = find_entry(state->archive, entry);
    if (!item) {
        c2_zip_stream_close(stream);
        set_error(error, error_capacity, "ZIP entry was not found");
        return 0;
    }
    problem = cursor_open(&state->cursor, state->archive, item);
    if (problem) {
        c2_zip_stream_close(stream);
        set_error(error, error_capacity, problem);
        return 0;
    }
    stream->size = item->size;
    return 1;
}

void c2_zip_stream_source(struct c2_zip_stream *stream,
                          struct c2_source_reader *source)
{
    source->userdata = stream;
    source->size = stream->size;
    source->read_at = stream_read_at;
}

void c2_zip_stream_close(struct c2_zip_stream *stream)
{
    struct zip_stream_state *state = stream->state;
    if (state) {
        close_cursor(&state->cursor);
        close_archive(state->archive);
        free(state);
    }
    free(stream->scratch);
    memset(stream, 0, sizeof(*stream));
}

struct zip_item {
    const struct zip_entry *entry;
    char *logical_path;
};

static void free_items(struct zip_item *items, size_t count)
{
    size_t i;
    for (i = 0; i < count; i++) free(items[i].logical_path);
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
                   const struct c2_import_progress *progress,
                   char *error, size_t error_capacity)
{
    struct zip_archive *archive;
    struct zip_item *items = NULL;
    size_t count = 0;
    size_t capacity = 0;
    uint64_t total = 0;
    char common[C2_IMPORT_MAX_PATH] = {0};
    int common_valid = 1;
    int saw_disc_image = 0;
    size_t i;
    uint64_t completed = 0;
    unsigned char *buffer = NULL;

    archive = open_archive(zip_path, error, error_capacity);
    if (!archive) return 0;
    for (i = 0; i < archive->count; i++) {
        const struct zip_entry *entry = &archive->entries[i];
        char normalized[C2_IMPORT_MAX_PATH];
        const char *slash;
        if (entry->directory) continue;
        if (!safe_path(entry->name, normalized, sizeof(normalized))) {
            set_error(error, error_capacity, "ZIP contains an unsafe non-regular entry");
            goto fail;
        }
        if (!runtime_path(normalized)) {
            const char *dot = strrchr(normalized, '.');
            if (dot && (SDL_strcasecmp(dot, ".bin") == 0 ||
                        SDL_strcasecmp(dot, ".cue") == 0 ||
                        SDL_strcasecmp(dot, ".iso") == 0)) {
                saw_disc_image = 1;
            }
            continue;
        }
        if (entry->size > C2_IMPORT_MAX_BYTES || total > C2_IMPORT_MAX_BYTES - entry->size ||
            count >= C2_IMPORT_MAX_ENTRIES) {
            set_error(error, error_capacity, "ZIP exceeds import quotas");
            goto fail;
        }
        total += entry->size;
        if (count == capacity) {
            size_t new_capacity = capacity ? capacity * 2 : 128;
            struct zip_item *grown = realloc(items, new_capacity * sizeof(*grown));
            if (!grown) goto fail;
            items = grown; capacity = new_capacity;
        }
        items[count].entry = entry;
        items[count].logical_path = copy_string(normalized);
        if (!items[count].logical_path) goto fail;
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
    }
    if (count == 0) {
        set_error(error, error_capacity, saw_disc_image
                  ? "ZIP wraps a disc image; unzip it and select the ISO or CUE"
                  : "ZIP contains no Caesar II game files");
        goto fail;
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
            set_error(error, error_capacity, "invalid outer ZIP directory"); goto fail;
        }
        for (j = 0; j < i; j++) {
            if (same_fold(items[j].logical_path, items[i].logical_path)) {
                set_error(error, error_capacity, "ZIP contains case-colliding paths"); goto fail;
            }
        }
    }

    report_progress(progress, 0, total, 0, count);
    if (!SDL_CreateDirectory(destination) && !SDL_GetPathInfo(destination, NULL)) {
        set_error(error, error_capacity, SDL_GetError()); goto fail;
    }
    buffer = malloc(C2_ZIP_SCRATCH);
    if (!buffer) goto fail;
    for (i = 0; i < count; i++) {
        const struct zip_entry *entry = items[i].entry;
        struct zip_cursor cursor;
        char output[C2_IMPORT_MAX_PATH * 2];
        FILE *file;
        const char *problem;
        uint64_t done = 0;
        uint32_t crc = crc32(0L, Z_NULL, 0);
        if (snprintf(output, sizeof(output), "%s/%s", destination, items[i].logical_path) >= (int)sizeof(output) ||
            !make_parents(output)) {
            set_error(error, error_capacity, "output path is invalid"); goto fail;
        }
        problem = cursor_open(&cursor, archive, entry);
        if (problem) { set_error(error, error_capacity, problem); close_cursor(&cursor); goto fail; }
        file = fopen(output, "wb");
        if (!file) {
            set_error(error, error_capacity, "could not create imported file");
            close_cursor(&cursor); goto fail;
        }
        while (done < entry->size) {
            size_t got = cursor_read(&cursor, done, buffer, C2_ZIP_SCRATCH);
            if (got == 0) break;
            if (fwrite(buffer, 1, got, file) != got) {
                set_error(error, error_capacity, "could not write imported file");
                fclose(file); close_cursor(&cursor); goto fail;
            }
            crc = crc32(crc, buffer, (uInt)got);
            done += got;
            completed += got;
            report_progress(progress, completed, total, i, count);
        }
        close_cursor(&cursor);
        if (fclose(file) != 0 || done != entry->size || crc != entry->crc) {
            set_error(error, error_capacity, "ZIP entry is corrupt");
            goto fail;
        }
        report_progress(progress, completed, total, i + 1, count);
    }
    free(buffer);
    free_items(items, count);
    close_archive(archive);
    return 1;
fail:
    free(buffer);
    free_items(items, count);
    close_archive(archive);
    return 0;
}
