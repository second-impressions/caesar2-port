#ifndef C2_LIBRARY_H
#define C2_LIBRARY_H

/*
 * The game-data library (docs/game-data-library.md).
 *
 * Every import, native or in the browser, is merged into one directory
 * tree under <game-data root>/library, sorted by what the files are:
 *
 *   C2ASSETS                  format marker and quality notes
 *   common/                   identical in every release
 *   language/<tag>/           one release's text, speech and localized files
 *   music/dos/, music/windows/
 *   video/SMK/                the best copy of each movie
 *
 * A .c2assets file is that tree in a ZIP. <game-data root>/local holds
 * what never leaves the machine: staging and the summary the front ends
 * display.
 */

#include <stddef.h>
#include <stdint.h>

#include "c2_import.h"

#define C2_LIBRARY_PATH_CAPACITY 1024
#define C2_LIBRARY_MAX_ROOTS 16
#define C2_LIBRARY_MAX_LANGUAGES 8
#define C2_LIBRARY_TAG_CAPACITY 16

/* One directory the runtime searches: base files in `base`, media files in
 * `media`/PL8, RAW, SMK, XMI. A library root has base == media. */
struct c2_asset_root {
    char base[C2_LIBRARY_PATH_CAPACITY];
    char media[C2_LIBRARY_PATH_CAPACITY];
    int library;    /* upper-case names; movies, scores and speech only as media */
};

struct c2_asset_layout {
    struct c2_asset_root roots[C2_LIBRARY_MAX_ROOTS];
    int count;
    char speech[C2_LIBRARY_TAG_CAPACITY]; /* the language folder in front, "" for raw data */
};

struct c2_library_language {
    char tag[C2_LIBRARY_TAG_CAPACITY];
    int speech;             /* has the speech files */
    int windows;            /* taken from a Windows 95 tree */
    int mac;                /* text and speech from a Macintosh disc only */
    char version[64];       /* "Version 1.2", from its C2.ENG */
};

struct c2_library_summary {
    int playable;
    int language_count;
    struct c2_library_language languages[C2_LIBRARY_MAX_LANGUAGES];
    int music_dos;          /* the 1995 scores and a synthesizer bank */
    int music_windows;      /* the 1996 recordings */
    int movies;             /* movies present */
    int movies_enhanced;    /* of those, larger than the DOS originals */
    uint64_t bytes;         /* size of library/ */
};

/* C2.ENG -> language tag ("en", "de", ...), or NULL when unknown. The
 * runtime passes its text catalogue's detector; without one a built-in
 * table covering the shipped releases is used. */
typedef const char *(*c2_language_detector)(const unsigned char *c2eng, size_t size);
void c2_library_set_language_detector(c2_language_detector detector);

/* Merge a source (installation, GOG folder, disc image, BIN/CUE, ZIP,
 * .c2assets, CD-ROM drive, folder of movies) into the library. */
int c2_library_import(const char *game_data_root, const char *source,
                      const struct c2_import_progress *progress,
                      char *error, size_t error_capacity);

/* Import each cache the importer used to keep (<root>/<16 hex>/ with a
 * .complete marker) and delete it. Returns how many were migrated, or -1. */
int c2_library_migrate(const char *game_data_root,
                       const struct c2_import_progress *progress,
                       char *error, size_t error_capacity);

/* Delete library/ and local/. Nothing else under the root is touched. */
int c2_library_remove(const char *game_data_root);

/* Write library/ as a .c2assets ZIP, C2ASSETS first. */
int c2_library_export(const char *game_data_root, const char *zip_path,
                      const struct c2_import_progress *progress,
                      char *error, size_t error_capacity);

/* Read what the library holds. Also rewrites local/summary. */
int c2_library_describe(const char *game_data_root,
                        struct c2_library_summary *summary);

/* The speech language that plays for a wish ("" = no wish): the wish when
 * the library has its speech, else English, else the first with speech,
 * else the wish or the first language at all. */
const char *c2_library_pick_speech(const struct c2_library_summary *summary,
                                   const char *wanted);

/* Directories the runtime reads, for either a library (or a folder that
 * contains one) or a raw installation or disc tree read in place. */
int c2_library_layout(const char *root, const char *speech,
                      struct c2_asset_layout *layout,
                      char *error, size_t error_capacity);

/* <game_data_root>/library */
int c2_library_path(char *out, size_t capacity, const char *game_data_root);

#endif
