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


/* ------------------------------------------------------------------ */
/* HFS: the Macintosh CDs                                              */
/*
 * The Mac release ships on HFS volumes behind an Apple partition map
 * (Toast images, the CD itself). Only what cataloguing needs is read: the
 * master directory block, the catalog B-tree's leaf records, and each
 * file's data fork, which on these mastered discs is one contiguous run.
 * Resource forks and fragmented files are left out.
 */

#define C2_HFS_MAX_CATALOG (32u * 1024u * 1024u)
#define C2_HFS_MAX_DIRECTORIES 4096u

static uint16_t be16(const unsigned char *p) { return (uint16_t)((p[0] << 8) | p[1]); }
static uint32_t be32(const unsigned char *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}

struct hfs_volume {
    uint64_t start;          /* byte offset of the HFS volume */
    uint64_t end;
    uint32_t block_size;
    uint64_t first_block;    /* byte offset of allocation block 0 */
    unsigned char mdb[512];
};

static int hfs_mdb_at(const struct c2_source_reader *source, uint64_t start,
                      struct hfs_volume *volume)
{
    if (!read_exact(source, start + 1024, volume->mdb, sizeof(volume->mdb)) ||
        volume->mdb[0] != 'B' || volume->mdb[1] != 'D') return 0;
    volume->start = start;
    volume->block_size = be32(volume->mdb + 20);
    if (volume->block_size == 0 || volume->block_size % 512 != 0) return 0;
    volume->first_block = start + (uint64_t)be16(volume->mdb + 28) * 512u;
    volume->end = volume->first_block +
                  (uint64_t)be16(volume->mdb + 18) * volume->block_size + 1024u;
    return 1;
}

/* The HFS partition of an Apple partition map, or a bare HFS volume. */
static int hfs_locate(const struct c2_source_reader *source, struct hfs_volume *volume)
{
    unsigned char block[512];
    uint32_t entries;
    uint32_t i;
    if (!read_exact(source, 0, block, sizeof(block))) return 0;
    if (block[0] == 'E' && block[1] == 'R') {
        if (!read_exact(source, 512, block, sizeof(block)) || block[0] != 'P' || block[1] != 'M') return 0;
        entries = be32(block + 4);
        if (entries > 64) entries = 64;
        for (i = 1; i <= entries; i++) {
            if (!read_exact(source, (uint64_t)i * 512u, block, sizeof(block)) ||
                block[0] != 'P' || block[1] != 'M') break;
            if (memcmp(block + 48, "Apple_HFS", 10) == 0 &&
                hfs_mdb_at(source, (uint64_t)be32(block + 8) * 512u, volume)) {
                uint64_t partition_end = (uint64_t)(be32(block + 8) + be32(block + 12)) * 512u;
                if (partition_end > volume->end) volume->end = partition_end;
                return 1;
            }
        }
        return 0;
    }
    return hfs_mdb_at(source, 0, volume);
}

int c2_hfs_probe(const struct c2_source_reader *source, uint64_t *volume_end)
{
    struct hfs_volume volume;
    if (!hfs_locate(source, &volume)) return 0;
    if (volume_end) *volume_end = volume.end;
    return 1;
}

struct hfs_directory {
    uint32_t id;
    uint32_t parent;
    char name[64];
};

/* ASCII for a MacRoman name; control characters (the "Icon\r" files)
 * mean the entry is not ours. */
static int hfs_name(char *out, size_t capacity, const unsigned char *name, size_t length)
{
    size_t i;
    if (length == 0 || length + 1 > capacity) return 0;
    for (i = 0; i < length; i++) {
        unsigned char c = name[i];
        if (c < 0x20 || c == 0x7f) return 0;
        out[i] = (char)(c == '/' || c == '\\' || c >= 0x80 ? '_' : toupper(c));
    }
    out[length] = '\0';
    return 1;
}

static int hfs_path(char *out, size_t capacity, const struct hfs_directory *dirs,
                    size_t count, uint32_t parent, const char *leaf)
{
    const char *parts[C2_ISO_MAX_DEPTH];
    size_t depth = 0;
    size_t used = 0;
    while (parent > 2 && depth < C2_ISO_MAX_DEPTH) {
        size_t i;
        for (i = 0; i < count && dirs[i].id != parent; i++) {}
        if (i == count) return 0;
        parts[depth++] = dirs[i].name;
        parent = dirs[i].parent;
    }
    if (parent > 2) return 0;
    out[0] = '\0';
    while (depth > 0) {
        int n = snprintf(out + used, capacity - used, "%s/", parts[--depth]);
        if (n < 0 || (size_t)n >= capacity - used) return 0;
        used += (size_t)n;
    }
    return snprintf(out + used, capacity - used, "%s", leaf) < (int)(capacity - used);
}

struct hfs_file {
    uint32_t parent;
    char name[64];
    uint64_t offset;
    uint64_t size;
};

static int hfs_catalog_open(const struct c2_source_reader *source,
                            const struct hfs_volume *volume,
                            struct c2_iso_catalog *catalog,
                            char *error, size_t error_capacity)
{
    unsigned char *tree = NULL;
    struct hfs_directory *dirs = NULL;
    struct hfs_file *files = NULL;
    size_t dir_count = 0;
    size_t file_count = 0;
    size_t file_capacity = 0;
    uint32_t tree_size = be32(volume->mdb + 146);
    uint64_t covered = 0;
    uint64_t done = 0;
    uint32_t node_size;
    uint32_t node;
    uint32_t visited = 0;
    int e;
    int ok = 0;
    size_t f;

    if (tree_size == 0 || tree_size > C2_HFS_MAX_CATALOG) {
        set_error(error, error_capacity, "HFS catalog exceeds safety limits");
        return 0;
    }
    tree = malloc(tree_size);
    dirs = calloc(C2_HFS_MAX_DIRECTORIES, sizeof(*dirs));
    if (!tree || !dirs) goto out_of_memory;
    for (e = 0; e < 3 && done < tree_size; e++) {
        uint64_t start = be16(volume->mdb + 150 + 4 * e);
        uint64_t count = be16(volume->mdb + 152 + 4 * e);
        uint64_t bytes = count * volume->block_size;
        if (bytes > tree_size - done) bytes = tree_size - done;
        if (count && !read_exact(source, volume->first_block + start * volume->block_size,
                                 tree + done, (size_t)bytes)) {
            set_error(error, error_capacity, "could not read the HFS catalog");
            goto done;
        }
        done += bytes;
        covered += count * volume->block_size;
    }
    if (covered < tree_size) {
        set_error(error, error_capacity, "fragmented HFS catalogs are not supported");
        goto done;
    }
    node_size = be16(tree + 14 + 18);
    if (node_size < 512 || node_size > 32768 || tree_size % node_size != 0) {
        set_error(error, error_capacity, "invalid HFS catalog");
        goto done;
    }
    for (node = be32(tree + 14 + 10); node != 0; node = be32(tree + (size_t)node * node_size)) {
        const unsigned char *nd;
        uint16_t records;
        uint16_t r;
        if ((uint64_t)(node + 1) * node_size > tree_size || ++visited > tree_size / node_size) {
            set_error(error, error_capacity, "invalid HFS catalog");
            goto done;
        }
        nd = tree + (size_t)node * node_size;
        if ((signed char)nd[8] != -1) break;
        records = be16(nd + 10);
        for (r = 0; r < records; r++) {
            uint32_t o = be16(nd + node_size - 2u * (r + 1u));
            uint32_t d;
            uint32_t parent;
            if (o + 7 > node_size || o + 7u + nd[o + 6] > node_size) continue;
            parent = be32(nd + o + 2);
            d = o + 1u + nd[o];
            d += d & 1u;
            if (d + 102 > node_size) continue;
            if (nd[d] == 1 && dir_count < C2_HFS_MAX_DIRECTORIES) {
                struct hfs_directory *dir = &dirs[dir_count];
                dir->id = be32(nd + d + 6);
                dir->parent = parent;
                if (!hfs_name(dir->name, sizeof(dir->name), nd + o + 7, nd[o + 6])) {
                    snprintf(dir->name, sizeof(dir->name), "_");
                }
                dir_count++;
            } else if (nd[d] == 2) {
                struct hfs_file file;
                uint32_t length = be32(nd + d + 26);
                uint32_t start = be16(nd + d + 74);
                uint32_t blocks = 0;
                uint32_t next = start;
                int x;
                file.parent = parent;
                if (length == 0 || !hfs_name(file.name, sizeof(file.name), nd + o + 7, nd[o + 6])) continue;
                for (x = 0; x < 3; x++) {
                    uint32_t s = be16(nd + d + 74 + 4 * x);
                    uint32_t c = be16(nd + d + 76 + 4 * x);
                    if (!c) break;
                    if (s != next) { blocks = 0; break; }
                    blocks += c;
                    next = s + c;
                }
                if ((uint64_t)blocks * volume->block_size < length) {
                    catalog->invalid_entries++;
                    continue;
                }
                file.offset = volume->first_block + (uint64_t)start * volume->block_size;
                file.size = length;
                if (file.offset > source->size || file.size > source->size - file.offset) {
                    catalog->invalid_entries++;
                    continue;
                }
                if (file_count == file_capacity) {
                    size_t capacity = file_capacity ? file_capacity * 2 : 256;
                    struct hfs_file *grown;
                    if (capacity > C2_ISO_MAX_ENTRIES) {
                        set_error(error, error_capacity, "too many files on the HFS volume");
                        goto done;
                    }
                    grown = realloc(files, capacity * sizeof(*grown));
                    if (!grown) goto out_of_memory;
                    files = grown;
                    file_capacity = capacity;
                }
                files[file_count++] = file;
            }
        }
    }
    for (f = 0; f < file_count; f++) {
        char path[C2_ISO_MAX_PATH];
        if (!hfs_path(path, sizeof(path), dirs, dir_count, files[f].parent, files[f].name) ||
            !add_entry(catalog, path, files[f].offset, files[f].size)) {
            catalog->invalid_entries++;
        }
    }
    qsort(catalog->entries, catalog->count, sizeof(*catalog->entries), compare_extent);
    ok = 1;
    goto done;
out_of_memory:
    set_error(error, error_capacity, "out of memory reading the HFS catalog");
done:
    free(files);
    free(dirs);
    free(tree);
    if (!ok) c2_iso_catalog_close(catalog);
    return ok;
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
        source->size < 4u * C2_ISO_SECTOR_SIZE) {
        set_error(error, error_capacity, "source is too small for a disc image");
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
        struct hfs_volume volume;
        if (hfs_locate(source, &volume)) {
            return hfs_catalog_open(source, &volume, catalog, error, error_capacity);
        }
        set_error(error, error_capacity, "not an ISO-9660 or Macintosh (HFS) disc");
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
