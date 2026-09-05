#include "c2_import.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define C2_ISO_SECTOR_SIZE 2048u
#define C2_ISO_MAX_DESCRIPTORS 240u
#define C2_ISO_MAX_DEPTH 16u
#define C2_ISO_MAX_ENTRIES 8192u
#define C2_ISO_MAX_DIRECTORY_SIZE (16u * 1024u * 1024u)
#define C2_ISO_MAX_PATH 512u

static uint32_t read_le32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void set_error(char *error, size_t capacity, const char *message)
{
    if (error == NULL || capacity == 0) return;
    snprintf(error, capacity, "%s", message);
}

static int read_exact(const struct c2_source_reader *source, uint64_t offset,
                      void *buffer, size_t size)
{
    size_t done;
    size_t got;

    if (source == NULL || source->read_at == NULL ||
        offset > source->size || size > source->size - offset) {
        return 0;
    }
    done = 0;
    while (done < size) {
        got = 0;
        if (!source->read_at(source->userdata, offset + done,
                             (unsigned char *)buffer + done,
                             size - done, &got) || got == 0) {
            return 0;
        }
        done += got;
    }
    return 1;
}

static int folded_equal(const char *left, const char *right)
{
    while (*left || *right) {
        unsigned char a = (unsigned char)*left++;
        unsigned char b = (unsigned char)*right++;
        if (a == '\\') a = '/';
        if (b == '\\') b = '/';
        if (toupper(a) != toupper(b)) return 0;
    }
    return 1;
}

static int add_entry(struct c2_iso_catalog *catalog, const char *path,
                     uint64_t offset, uint64_t size)
{
    struct c2_iso_entry *grown;
    char *copy;
    size_t capacity;
    size_t i;

    if (catalog->count >= C2_ISO_MAX_ENTRIES) return 0;
    for (i = 0; i < catalog->count; i++) {
        if (folded_equal(catalog->entries[i].path, path)) return 0;
    }
    if (catalog->count == catalog->capacity) {
        capacity = catalog->capacity == 0 ? 128 : catalog->capacity * 2;
        if (capacity > C2_ISO_MAX_ENTRIES) capacity = C2_ISO_MAX_ENTRIES;
        grown = realloc(catalog->entries, capacity * sizeof(*grown));
        if (grown == NULL) return 0;
        catalog->entries = grown;
        catalog->capacity = capacity;
    }
    copy = malloc(strlen(path) + 1);
    if (copy == NULL) return 0;
    strcpy(copy, path);
    catalog->entries[catalog->count].path = copy;
    catalog->entries[catalog->count].offset = offset;
    catalog->entries[catalog->count].size = size;
    catalog->count++;
    return 1;
}

static int canonical_name(char *output, size_t capacity,
                          const unsigned char *name, size_t length)
{
    size_t i;
    size_t out;

    if (length == 0 || capacity == 0) return 0;
    out = 0;
    for (i = 0; i < length; i++) {
        unsigned char c = name[i];
        if (c == ';') break;
        if (c == '/' || c == '\\' || c == 0 || c < 0x20 || c >= 0x7f) {
            return 0;
        }
        if (out + 1 >= capacity) return 0;
        output[out++] = (char)toupper(c);
    }
    while (out > 0 && output[out - 1] == '.') out--;
    if (out == 0) return 0;
    output[out] = '\0';
    return 1;
}

static int walk_directory(const struct c2_source_reader *source,
                          struct c2_iso_catalog *catalog,
                          uint32_t extent, uint32_t length,
                          const char *parent, unsigned int depth,
                          char *error, size_t error_capacity)
{
    unsigned char *data;
    uint64_t byte_offset;
    size_t position;

    if (depth > C2_ISO_MAX_DEPTH || length > C2_ISO_MAX_DIRECTORY_SIZE) {
        set_error(error, error_capacity, "ISO directory exceeds safety limits");
        return 0;
    }
    byte_offset = (uint64_t)extent * C2_ISO_SECTOR_SIZE;
    if (byte_offset > source->size || length > source->size - byte_offset) {
        set_error(error, error_capacity, "ISO directory extent is outside the image");
        return 0;
    }
    data = malloc(length == 0 ? 1 : length);
    if (data == NULL) {
        set_error(error, error_capacity, "out of memory reading ISO directory");
        return 0;
    }
    if (length != 0 && !read_exact(source, byte_offset, data, length)) {
        free(data);
        set_error(error, error_capacity, "could not read ISO directory");
        return 0;
    }

    position = 0;
    while (position < length) {
        const unsigned char *record;
        unsigned int record_length;
        unsigned int name_length;
        uint32_t child_extent;
        uint32_t child_length;
        char component[256];
        char path[C2_ISO_MAX_PATH];
        int path_length;

        record_length = data[position];
        if (record_length == 0) {
            position = ((position / C2_ISO_SECTOR_SIZE) + 1) *
                       C2_ISO_SECTOR_SIZE;
            continue;
        }
        if (record_length < 34 || record_length > length - position) {
            free(data);
            set_error(error, error_capacity, "invalid ISO directory record");
            return 0;
        }
        record = data + position;
        name_length = record[32];
        if (33u + name_length > record_length) {
            free(data);
            set_error(error, error_capacity, "invalid ISO filename record");
            return 0;
        }
        position += record_length;
        if (name_length == 1 && (record[33] == 0 || record[33] == 1)) {
            continue;
        }
        if (!canonical_name(component, sizeof(component), record + 33,
                            name_length)) {
            free(data);
            set_error(error, error_capacity, "unsupported ISO filename");
            return 0;
        }
        path_length = parent[0] == '\0'
            ? snprintf(path, sizeof(path), "%s", component)
            : snprintf(path, sizeof(path), "%s/%s", parent, component);
        if (path_length < 0 || (size_t)path_length >= sizeof(path)) {
            free(data);
            set_error(error, error_capacity, "ISO path is too long");
            return 0;
        }
        child_extent = read_le32(record + 2);
        child_length = read_le32(record + 10);
        byte_offset = (uint64_t)child_extent * C2_ISO_SECTOR_SIZE;
        if (byte_offset > source->size ||
            child_length > source->size - byte_offset) {
            /* Several shipped Caesar II discs retain dangling installer or
             * catalogue records beyond the recorded data track. Keep the
             * filesystem usable but never expose those entries; required
             * game assets are validated after cataloguing. */
            catalog->invalid_entries++;
            continue;
        }
        if ((record[25] & 2) != 0) {
            if (!walk_directory(source, catalog, child_extent, child_length,
                                path, depth + 1, error, error_capacity)) {
                free(data);
                return 0;
            }
        } else if (!add_entry(catalog, path, byte_offset, child_length)) {
            free(data);
            set_error(error, error_capacity, "too many ISO files or out of memory");
            return 0;
        }
    }
    free(data);
    return 1;
}

static int compare_extent(const void *left, const void *right)
{
    const struct c2_iso_entry *a = left;
    const struct c2_iso_entry *b = right;
    if (a->offset != b->offset) return a->offset < b->offset ? -1 : 1;
    return strcmp(a->path, b->path);
}

int c2_iso_catalog_open(const struct c2_source_reader *source,
                        struct c2_iso_catalog *catalog,
                        char *error, size_t error_capacity)
{
    unsigned char sector[C2_ISO_SECTOR_SIZE];
    unsigned int index;
    const unsigned char *root;
    uint32_t extent;
    uint32_t length;
    int found;

    if (catalog == NULL) return 0;
    memset(catalog, 0, sizeof(*catalog));
    if (source == NULL || source->read_at == NULL ||
        source->size < 17u * C2_ISO_SECTOR_SIZE) {
        set_error(error, error_capacity, "source is too small for ISO-9660");
        return 0;
    }
    found = 0;
    for (index = 16; index < 16 + C2_ISO_MAX_DESCRIPTORS; index++) {
        if (!read_exact(source, (uint64_t)index * C2_ISO_SECTOR_SIZE,
                        sector, sizeof(sector))) {
            break;
        }
        if (memcmp(sector + 1, "CD001", 5) != 0 || sector[6] != 1) {
            continue;
        }
        if (sector[0] == 1) {
            found = 1;
            break;
        }
        if (sector[0] == 255) break;
    }
    if (!found) {
        set_error(error, error_capacity, "ISO-9660 primary volume descriptor not found");
        return 0;
    }
    root = sector + 156;
    if (root[0] < 34 || root[32] != 1 || root[33] != 0 ||
        (root[25] & 2) == 0) {
        set_error(error, error_capacity, "invalid ISO-9660 root directory");
        return 0;
    }
    extent = read_le32(root + 2);
    length = read_le32(root + 10);
    if (!walk_directory(source, catalog, extent, length, "", 0,
                        error, error_capacity)) {
        c2_iso_catalog_close(catalog);
        return 0;
    }
    /* Extent order makes extraction a single forward sweep, which is what
     * optical drives and sequential (deflated) sources want. */
    qsort(catalog->entries, catalog->count, sizeof(*catalog->entries),
          compare_extent);
    return 1;
}

void c2_iso_catalog_close(struct c2_iso_catalog *catalog)
{
    size_t i;
    if (catalog == NULL) return;
    for (i = 0; i < catalog->count; i++) free(catalog->entries[i].path);
    free(catalog->entries);
    memset(catalog, 0, sizeof(*catalog));
}

static int path_compare(const char *left, const char *right)
{
    unsigned char a;
    unsigned char b;
    do {
        a = (unsigned char)*left++;
        b = (unsigned char)*right++;
        if (a == '\\') a = '/';
        if (b == '\\') b = '/';
        a = (unsigned char)toupper(a);
        b = (unsigned char)toupper(b);
        if (a != b) return (int)a - (int)b;
    } while (a != 0);
    return 0;
}

const struct c2_iso_entry *c2_iso_catalog_find(
    const struct c2_iso_catalog *catalog, const char *path)
{
    size_t i;
    if (catalog == NULL || path == NULL) return NULL;
    while (*path == '/' || *path == '\\') path++;
    for (i = 0; i < catalog->count; i++) {
        if (path_compare(catalog->entries[i].path, path) == 0) {
            return &catalog->entries[i];
        }
    }
    return NULL;
}

int c2_iso_entry_read(const struct c2_source_reader *source,
                      const struct c2_iso_entry *entry,
                      uint64_t offset, void *buffer, size_t size,
                      size_t *read_out)
{
    size_t wanted;
    if (read_out != NULL) *read_out = 0;
    if (source == NULL || entry == NULL || buffer == NULL ||
        offset > entry->size) return 0;
    wanted = size;
    if ((uint64_t)wanted > entry->size - offset) {
        wanted = (size_t)(entry->size - offset);
    }
    if (wanted == 0) return 1;
    if (!read_exact(source, entry->offset + offset, buffer, wanted)) return 0;
    if (read_out != NULL) *read_out = wanted;
    return 1;
}
