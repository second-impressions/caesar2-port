#ifndef C2_IMPORT_H
#define C2_IMPORT_H

#include <stddef.h>
#include <stdint.h>

typedef int (*c2_source_read_at_fn)(void *userdata, uint64_t offset,
                                    void *buffer, size_t size,
                                    size_t *read_out);

struct c2_source_reader {
    void *userdata;
    uint64_t size;
    c2_source_read_at_fn read_at;
};

struct c2_iso_entry {
    char *path;
    uint64_t offset;
    uint64_t size;
};

struct c2_iso_catalog {
    struct c2_iso_entry *entries;
    size_t count;
    size_t capacity;
    size_t invalid_entries;
};

enum c2_cd_sector_mode {
    C2_CD_MODE1_2352 = 1,
    C2_CD_MODE2_2352 = 2
};

struct c2_raw_cd_reader {
    struct c2_source_reader raw;
    enum c2_cd_sector_mode mode;
};

int c2_iso_catalog_open(const struct c2_source_reader *source,
                        struct c2_iso_catalog *catalog,
                        char *error, size_t error_capacity);
void c2_iso_catalog_close(struct c2_iso_catalog *catalog);
const struct c2_iso_entry *c2_iso_catalog_find(
    const struct c2_iso_catalog *catalog, const char *path);
int c2_iso_entry_read(const struct c2_source_reader *source,
                      const struct c2_iso_entry *entry,
                      uint64_t offset, void *buffer, size_t size,
                      size_t *read_out);

int c2_cue_parse_single_data_track(const char *cue,
                                   char *bin_name, size_t bin_name_capacity,
                                   enum c2_cd_sector_mode *mode,
                                   char *error, size_t error_capacity);
int c2_raw_cd_reader_init(struct c2_raw_cd_reader *reader,
                          const struct c2_source_reader *raw,
                          enum c2_cd_sector_mode mode,
                          char *error, size_t error_capacity);
void c2_raw_cd_source(struct c2_raw_cd_reader *reader,
                      struct c2_source_reader *source);

int c2_zip_extract(const char *zip_path, const char *destination,
                   char *error, size_t error_capacity);
int c2_iso_extract(const struct c2_source_reader *source,
                   const char *destination,
                   char *error, size_t error_capacity);
int c2_import_path(const char *source_path, const char *cache_root,
                   const char *asset_profile,
                   char *asset_root, size_t asset_root_capacity,
                   char *error, size_t error_capacity);
int c2_pack_activate(const char *pack_root, const char *profile,
                     char *active_root, size_t active_root_capacity,
                     char *error, size_t error_capacity);

#endif
