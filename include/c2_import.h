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

typedef void (*c2_import_progress_fn)(void *userdata, const char *phase,
                                      uint64_t completed_bytes,
                                      uint64_t total_bytes,
                                      size_t completed_files,
                                      size_t total_files);

struct c2_import_progress {
    c2_import_progress_fn update;
    void *userdata;
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

/* A physical CD-ROM drive exposed as logical 2048-byte ISO sectors.
 * win32_handle carries the Windows volume HANDLE; fd carries the POSIX
 * device descriptor.  size and fingerprint come from the disc's primary
 * volume descriptor. */
struct c2_cdrom_reader {
    void *win32_handle;
    int fd;
    uint64_t size;
    uint64_t fingerprint;
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

#define C2_CDROM_DRIVE_PATH_CAPACITY 32

int c2_cdrom_is_device_path(const char *path);
/* Fill paths[0..max) with candidate optical drive device paths present on
 * this machine ("/dev/sr0", "D:", ...) and return how many were found.
 * Presence of a drive does not imply a readable disc is inserted. */
int c2_cdrom_find_drives(char paths[][C2_CDROM_DRIVE_PATH_CAPACITY], int max);
/* Cheap media check for polling; does not spin the drive up where the OS
 * offers a status query. */
int c2_cdrom_drive_has_disc(const char *path);
int c2_cdrom_open(const char *path, struct c2_cdrom_reader *reader,
                  char *error, size_t error_capacity);
void c2_cdrom_source(struct c2_cdrom_reader *reader,
                     struct c2_source_reader *source);
void c2_cdrom_close(struct c2_cdrom_reader *reader);

int c2_zip_extract(const char *zip_path, const char *destination,
                   const struct c2_import_progress *progress,
                   char *error, size_t error_capacity);

/* What a ZIP can be imported as. Runtime files win over wrapped images. */
enum c2_zip_content {
    C2_ZIP_EMPTY = 0,
    C2_ZIP_RUNTIME_FILES,
    C2_ZIP_ISO_IMAGE,   /* entry names the .iso */
    C2_ZIP_CUE_IMAGE    /* entry names the .cue; its BIN sits beside it */
};

int c2_zip_probe(const char *zip_path, enum c2_zip_content *content,
                 char *entry, size_t entry_capacity,
                 char *error, size_t error_capacity);
int c2_zip_read_entry(const char *zip_path, const char *entry,
                      void *buffer, size_t capacity, size_t *size_out,
                      char *error, size_t error_capacity);

/* A c2_source_reader over one ZIP entry without extracting it. Deflate is
 * sequential, so forward reads decompress-and-skip and a backward read
 * reopens the entry; ISO extraction is ordered by extent to keep rewinds
 * rare. Entry names match case-insensitively with either slash. */
struct c2_zip_stream {
    void *archive;
    char *zip_path;
    char *entry;
    unsigned char *scratch;
    uint64_t size;
    uint64_t position;
    unsigned rewinds;
};

int c2_zip_stream_open(struct c2_zip_stream *stream, const char *zip_path,
                       const char *entry, char *error, size_t error_capacity);
void c2_zip_stream_source(struct c2_zip_stream *stream,
                          struct c2_source_reader *source);
void c2_zip_stream_close(struct c2_zip_stream *stream);
int c2_iso_extract(const struct c2_source_reader *source,
                   const char *destination,
                   const struct c2_import_progress *progress,
                   char *error, size_t error_capacity);
/* How a user-supplied path will be imported. Classification looks at
 * content (ZIP/ISO/raw-sector signatures), not just extensions, and a file
 * inside an installation resolves to that installation's root. */
enum c2_source_kind {
    C2_SOURCE_NONE = 0,
    C2_SOURCE_DIRECTORY,      /* installation folder, used in place */
    C2_SOURCE_PACK_DIRECTORY, /* unpacked .c2assets (C2PACK.IDX) */
    C2_SOURCE_ZIP,            /* installation ZIP, .c2assets, or wrapped image */
    C2_SOURCE_ISO,            /* 2048-byte-sector image */
    C2_SOURCE_RAW_BIN,        /* 2352-byte-sector image; CUE not required */
    C2_SOURCE_CUE,            /* cue sheet beside its BIN */
    C2_SOURCE_CDROM           /* physical drive */
};

/* root receives the path the importer will actually use: the resolved
 * installation root for directory-like sources, otherwise path itself. */
int c2_import_classify(const char *path, enum c2_source_kind *kind,
                       char *root, size_t root_capacity,
                       char *error, size_t error_capacity);
const char *c2_source_kind_name(enum c2_source_kind kind);

int c2_import_path(const char *source_path, const char *cache_root,
                   const char *asset_profile,
                   const struct c2_import_progress *progress,
                   char *asset_root, size_t asset_root_capacity,
                   char *error, size_t error_capacity);
int c2_pack_activate(const char *pack_root, const char *profile,
                     char *active_root, size_t active_root_capacity,
                     char *error, size_t error_capacity);

#endif
