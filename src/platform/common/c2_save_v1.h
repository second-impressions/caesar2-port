#ifndef C2_SAVE_V1_H
#define C2_SAVE_V1_H

/*
 * The port's save format: engine-independent core.
 *
 * A save is a FlatBuffer with root `c2.save.Save` (schema: c2_save.fbs,
 * generated accessors in c2_save_gen/) followed by a 4-byte little-endian
 * CRC32 of the buffer. The FlatBuffers verifier bounds-checks the container;
 * `c2_save_validate` bounds-checks the game's own indices; nothing reaches
 * live engine state until both have passed, because everything is decoded
 * into a staging image first and committed by the engine adapter
 * (c2_port_save.c).
 *
 * The original 225,745-byte layout is version 0 and is import-only.
 *
 * This translation unit knows the registry layout and the recovered record
 * sizes, never the engine's globals, so it is unit-tested with synthetic
 * state. docs/save-format.md is the specification.
 */

#include <stddef.h>
#include <stdint.h>

#include "c2_save_compat.h"   /* legacy layout constants, figure/arrow counts */
#include "c2_types.h"

#define C2_SAVE_FORMAT_VERSION 1u
#define C2_SAVE_FILE_IDENTIFIER "C2SV"
#define C2_SAVE_TRAILER_SIZE 4u
#define C2_SAVE_LEGACY_FILE_SIZE 225745u

/* Recovered block and record sizes (bytes). */
#define C2_SAVE_CITY_CELLS      6400u
#define C2_SAVE_CITY_CELL_SIZE  20u
#define C2_SAVE_CITYMAP_SIZE    (C2_SAVE_CITY_CELLS * C2_SAVE_CITY_CELL_SIZE)
#define C2_SAVE_REGIONMP_SIZE   28800u
#define C2_SAVE_BATTLEMP_SIZE   10816u
#define C2_SAVE_CITIZEN_RECORD  58u
#define C2_SAVE_CITIZEN_TARGET  2u   /* wide target index appended to each record in the image */
#define C2_SAVE_CITIZEN_STRIDE  (C2_SAVE_CITIZEN_RECORD + C2_SAVE_CITIZEN_TARGET)
#define C2_SAVE_LEGACY_CITIZENS 201u
#define C2_SAVE_ARMIES_SIZE     4550u   /* 26 x 175 */
#define C2_SAVE_ARMY_RECORD     175u
#define C2_SAVE_ARMYROUT_SIZE   3460u   /* 10 x 346 */
#define C2_SAVE_ROUTE_RECORD    346u
#define C2_SAVE_UNITS_SIZE      3978u   /* 51 x 78 */
#define C2_SAVE_FIGURE_RECORD   80u     /* 88 in the engine record minus 8 pointer bytes */
#define C2_SAVE_ARROW_RECORD    41u     /* 45 minus 4 pointer bytes */
#define C2_SAVE_MESSAGES_SIZE   128u
#define C2_SAVE_FIREZONE_SIZE   100u
#define C2_SAVE_INDUSTRY_SIZE   768u
#define C2_SAVE_SLAVEREQ_SIZE   64u
#define C2_SAVE_HISTORY_SAMPLES 200u
#define C2_SAVE_HISTORY_FIELDS  5u

/* Legacy (version 0) layout the importer needs. */
#define C2_SAVE_LEGACY_STATE_SIZE    221745u
#define C2_SAVE_LEGACY_HISTORY_SIZE  4000u
#define C2_SAVE_LEGACY_FIGURE_RECORD 88u
#define C2_SAVE_LEGACY_ARROW_RECORD  45u
#define C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET 0x0a
#define C2_SAVE_LEGACY_FIGURE_TAIL_OFFSET    0x12
#define C2_SAVE_LEGACY_ARROW_POINTER_OFFSET  0x08
#define C2_SAVE_LEGACY_ARROW_TAIL_OFFSET     0x0c

/*
 * Which registry entries belong to which vector. The engine adapter fills
 * this from its globals; tests fill it from synthetic buffers. Every
 * registry entry whose buffer lies inside one of these blocks is carried by
 * that vector; everything else is a scalar. The three history ring indices
 * are derived state and are neither.
 */
struct c2_save_blocks {
    void *city_map;           /* 128000 */
    void *region_map;         /* 28800 */
    void *battle_map;         /* 10816 */
    void *citizen_list;       /* legacy window: 201 x 58 */
    void *army_list;          /* 4550 */
    void *army_routes;        /* 3460 */
    void *unit_list;          /* 3978 */
    void *figure_list;        /* struct figure_rec[201] */
    void *arrow_list;         /* struct arrow_rec[201] */
    void *message_list;       /* 128 */
    void *fire_zones;         /* 100 */
    void *industry;           /* 768 */
    void *slave_requirements; /* 64 */
    int  *history_end_ptr;
    int  *history_start_ptr;
    int  *history_entries;
};

/*
 * Staging image: everything a save holds, in the engine's own byte layouts
 * (so the adapter commits with memcpy) plus the wide references that the
 * engine keeps in side tables.
 */
struct c2_save_image {
    unsigned char *scalars;
    size_t scalars_size;

    unsigned char city_map[C2_SAVE_CITYMAP_SIZE];   /* cell bytes +7, +8 zero; +0x12 zero on market/business cells */
    uint16_t envoys[C2_SAVE_CITY_CELLS];
    unsigned char region_map[C2_SAVE_REGIONMP_SIZE];
    unsigned char battle_map[C2_SAVE_BATTLEMP_SIZE];

    unsigned char *citizens;      /* citizen_count x C2_SAVE_CITIZEN_STRIDE; record byte +0x2c zero, wide target at +58 */
    uint32_t citizen_count;       /* slots including slot 0 */

    unsigned char army_list[C2_SAVE_ARMIES_SIZE];
    unsigned char army_routes[C2_SAVE_ARMYROUT_SIZE];
    unsigned char unit_list[C2_SAVE_UNITS_SIZE];
    unsigned char figures[C2_SAVE_FIGURE_COUNT * C2_SAVE_FIGURE_RECORD];
    unsigned char figure_secondary[C2_SAVE_FIGURE_COUNT];
    unsigned char arrows[C2_SAVE_ARROW_COUNT * C2_SAVE_ARROW_RECORD];
    unsigned char messages[C2_SAVE_MESSAGES_SIZE];
    unsigned char fire_zones[C2_SAVE_FIREZONE_SIZE];
    unsigned char industry[C2_SAVE_INDUSTRY_SIZE];
    unsigned char slave_requirements[C2_SAVE_SLAVEREQ_SIZE];

    int32_t history[C2_SAVE_HISTORY_SAMPLES * C2_SAVE_HISTORY_FIELDS]; /* oldest first */
    uint32_t history_count;

    uint32_t format_version;      /* 0 for an imported legacy file */
    unsigned int cleared;         /* soft references zeroed by validation */
    unsigned int dropped_citizens;/* live records beyond the compiled pool */
};

enum c2_save_status {
    C2_SAVE_OK = 0,
    C2_SAVE_ERR_ARGS,
    C2_SAVE_ERR_MEMORY,
    C2_SAVE_ERR_FORMAT,      /* not a save in any known layout */
    C2_SAVE_ERR_CRC,         /* trailer checksum mismatch */
    C2_SAVE_ERR_VERIFY,      /* FlatBuffers verifier refused the buffer */
    C2_SAVE_ERR_VERSION,     /* written by a newer version */
    C2_SAVE_ERR_SHAPE,       /* a vector has the wrong length for its record */
    C2_SAVE_ERR_MISSING,     /* required vector absent */
    C2_SAVE_ERR_REGISTRY,    /* scalars do not match this build's registry */
    C2_SAVE_ERR_VALIDATION   /* a reject-policy reference is out of range */
};

const char *c2_save_status_name(enum c2_save_status status);

int  c2_save_image_init(struct c2_save_image *image, size_t scalars_size,
                        uint32_t citizen_slots);
void c2_save_image_free(struct c2_save_image *image);

size_t c2_save_scalars_size(const struct save_entry *entries,
                            size_t entry_count,
                            const struct c2_save_blocks *blocks);

/* Encode an image. *out is malloc'd, owned by the caller; returns size or 0. */
size_t c2_save_encode(const struct c2_save_image *image,
                      const char *engine_version, unsigned char **out);

/* Decode a container into an image sized by c2_save_image_init. */
enum c2_save_status c2_save_decode(const unsigned char *data, size_t size,
                                   const struct save_entry *entries,
                                   size_t entry_count,
                                   const struct c2_save_blocks *blocks,
                                   struct c2_save_image *image);

/* Import the original layout (version 0). */
enum c2_save_status c2_save_import_legacy(const unsigned char *data, size_t size,
                                          const struct save_entry *entries,
                                          size_t entry_count,
                                          const struct c2_save_blocks *blocks,
                                          struct c2_save_image *image);

/* Sniff: 1 = container, 0 = legacy layout, -1 = neither. */
int c2_save_detect(const unsigned char *data, size_t size);

/* Domain validation and normalisation; decode and import run it, and the
 * adapter runs it on a captured image so two images compare like for like. */
enum c2_save_status c2_save_validate(struct c2_save_image *image,
                                     uint32_t citizen_slots);

/* Semantic comparison: name of the first differing part, or NULL if equal. */
const char *c2_save_image_diff(const struct c2_save_image *a,
                               const struct c2_save_image *b);

#endif /* C2_SAVE_V1_H */
