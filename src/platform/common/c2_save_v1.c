#include <stdlib.h>
#include <string.h>

#include <zlib.h>

#include "c2_save_v1.h"
#include "c2_save_gen/c2_save_builder.h"
#include "c2_save_gen/c2_save_reader.h"
#include "c2_save_gen/c2_save_verifier.h"

#undef ns
#define ns(x) FLATBUFFERS_WRAP_NAMESPACE(c2_save, x)

/* ---- small helpers -------------------------------------------------------- */

static uint16_t get_u16(const unsigned char *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t get_u32(const unsigned char *p) { return (uint32_t)get_u16(p) | ((uint32_t)get_u16(p + 2) << 16); }
static int32_t  get_i32(const unsigned char *p) { return (int32_t)get_u32(p); }
static int16_t  get_i16(const unsigned char *p) { return (int16_t)get_u16(p); }
static void put_u16(unsigned char *p, uint16_t v) { p[0] = (unsigned char)v; p[1] = (unsigned char)(v >> 8); }
static void put_u32(unsigned char *p, uint32_t v) { put_u16(p, (uint16_t)v); put_u16(p + 2, (uint16_t)(v >> 16)); }
static void put_i32(unsigned char *p, int32_t v) { put_u32(p, (uint32_t)v); }
static void put_i16(unsigned char *p, int16_t v) { put_u16(p, (uint16_t)v); }

static uint32_t trailer_crc(const unsigned char *data, size_t size)
{
    return (uint32_t)crc32(crc32(0L, Z_NULL, 0), data, (uInt)size);
}

const char *c2_save_status_name(enum c2_save_status status)
{
    switch (status) {
    case C2_SAVE_OK: return "ok";
    case C2_SAVE_ERR_ARGS: return "bad arguments";
    case C2_SAVE_ERR_MEMORY: return "out of memory";
    case C2_SAVE_ERR_FORMAT: return "not a Caesar II save";
    case C2_SAVE_ERR_CRC: return "checksum mismatch";
    case C2_SAVE_ERR_VERIFY: return "damaged save container";
    case C2_SAVE_ERR_VERSION: return "written by a newer version";
    case C2_SAVE_ERR_SHAPE: return "a block has the wrong size";
    case C2_SAVE_ERR_MISSING: return "required block missing";
    case C2_SAVE_ERR_REGISTRY: return "state layout differs from this build";
    case C2_SAVE_ERR_VALIDATION: return "state failed validation";
    }
    return "unknown";
}

/* ---- registry classification ---------------------------------------------- */

enum block_kind {
    BLK_SCALAR = 0, BLK_SKIP,
    BLK_CITYMAP, BLK_REGIONMP, BLK_BATTLEMP, BLK_CITIZENS, BLK_ARMIES,
    BLK_ARMYROUT, BLK_UNITS, BLK_FIGURES, BLK_ARROWS, BLK_MESSAGES,
    BLK_FIREZONE, BLK_INDUSTRY, BLK_SLAVEREQ
};

static int inside(const void *p, const void *block, size_t size)
{
    const unsigned char *a = (const unsigned char *)p;
    const unsigned char *b = (const unsigned char *)block;

    return block != NULL && a >= b && a < b + size;
}

static enum block_kind classify(const struct save_entry *entry,
                                const struct c2_save_blocks *blocks)
{
    const void *p = entry->buf;

    if (p == blocks->history_end_ptr || p == blocks->history_start_ptr ||
        p == blocks->history_entries) return BLK_SKIP;
    if (inside(p, blocks->city_map, C2_SAVE_CITYMAP_SIZE)) return BLK_CITYMAP;
    if (inside(p, blocks->region_map, C2_SAVE_REGIONMP_SIZE)) return BLK_REGIONMP;
    if (inside(p, blocks->battle_map, C2_SAVE_BATTLEMP_SIZE)) return BLK_BATTLEMP;
    if (inside(p, blocks->citizen_list, C2_SAVE_LEGACY_CITIZENS * C2_SAVE_CITIZEN_RECORD)) return BLK_CITIZENS;
    if (inside(p, blocks->army_list, C2_SAVE_ARMIES_SIZE)) return BLK_ARMIES;
    if (inside(p, blocks->army_routes, C2_SAVE_ARMYROUT_SIZE)) return BLK_ARMYROUT;
    if (inside(p, blocks->unit_list, C2_SAVE_UNITS_SIZE)) return BLK_UNITS;
    if (inside(p, blocks->figure_list, sizeof(struct figure_rec) * C2_SAVE_FIGURE_COUNT)) return BLK_FIGURES;
    if (inside(p, blocks->arrow_list, sizeof(struct arrow_rec) * C2_SAVE_ARROW_COUNT)) return BLK_ARROWS;
    if (inside(p, blocks->message_list, C2_SAVE_MESSAGES_SIZE)) return BLK_MESSAGES;
    if (inside(p, blocks->fire_zones, C2_SAVE_FIREZONE_SIZE)) return BLK_FIREZONE;
    if (inside(p, blocks->industry, C2_SAVE_INDUSTRY_SIZE)) return BLK_INDUSTRY;
    if (inside(p, blocks->slave_requirements, C2_SAVE_SLAVEREQ_SIZE)) return BLK_SLAVEREQ;
    return BLK_SCALAR;
}

size_t c2_save_scalars_size(const struct save_entry *entries,
                            size_t entry_count,
                            const struct c2_save_blocks *blocks)
{
    size_t i, total = 0;

    for (i = 0; i < entry_count; i++) {
        if (entries[i].size == 0) break;
        if (classify(&entries[i], blocks) == BLK_SCALAR) total += (size_t)entries[i].size;
    }
    return total;
}

/* ---- image ----------------------------------------------------------------- */

int c2_save_image_init(struct c2_save_image *image, size_t scalars_size,
                       uint32_t citizen_slots)
{
    memset(image, 0, sizeof(*image));
    image->scalars = (unsigned char *)calloc(scalars_size ? scalars_size : 1, 1);
    image->citizens = (unsigned char *)calloc((size_t)citizen_slots * C2_SAVE_CITIZEN_STRIDE + 1, 1);
    if (image->scalars == NULL || image->citizens == NULL) {
        c2_save_image_free(image);
        return 0;
    }
    image->scalars_size = scalars_size;
    image->citizen_count = citizen_slots;
    return 1;
}

void c2_save_image_free(struct c2_save_image *image)
{
    free(image->scalars);
    free(image->citizens);
    image->scalars = NULL;
    image->citizens = NULL;
    image->scalars_size = 0;
    image->citizen_count = 0;
}

/* ---- validation -------------------------------------------------------------- */

static int is_market_or_business(unsigned char base_kind)
{
    return base_kind == 0xfa || base_kind >= 0xfc;
}

static int valid_cell_ref(int32_t ref)
{
    return ref >= 0 && ref < (int32_t)C2_SAVE_CITYMAP_SIZE &&
           (ref % (int32_t)C2_SAVE_CITY_CELL_SIZE) == 0;
}

enum c2_save_status c2_save_validate(struct c2_save_image *image,
                                     uint32_t citizen_slots)
{
    uint32_t i;

    for (i = 0; i < C2_SAVE_CITY_CELLS; i++) {
        unsigned char *cell = image->city_map + i * C2_SAVE_CITY_CELL_SIZE;

        /* Who stands here is derived from the citizen records. */
        cell[7] = 0;
        cell[8] = 0;
        if (is_market_or_business(cell[0])) {
            cell[0x12] = 0;   /* the envoy lives in the wide field */
            if (image->envoys[i] >= citizen_slots) { image->envoys[i] = 0; image->cleared++; }
        } else if (image->envoys[i] != 0) {
            image->envoys[i] = 0; image->cleared++;
        }
    }

    for (i = 0; i < image->citizen_count; i++) {
        unsigned char *rec = image->citizens + (size_t)i * C2_SAVE_CITIZEN_STRIDE;
        uint16_t target;

        if (rec[0] == 0) { memset(rec, 0, C2_SAVE_CITIZEN_STRIDE); continue; }
        if (i == 0) return C2_SAVE_ERR_VALIDATION;               /* sentinel slot must be empty */
        if (!valid_cell_ref(get_i32(rec + 6))) return C2_SAVE_ERR_VALIDATION;
        if (!valid_cell_ref(get_i32(rec + 0x28))) { put_i32(rec + 0x28, 0); image->cleared++; }
        target = get_u16(rec + C2_SAVE_CITIZEN_RECORD);
        if (target >= citizen_slots) { put_u16(rec + C2_SAVE_CITIZEN_RECORD, 0); image->cleared++; }
        rec[0x2c] = 0;   /* narrow target byte is derived from the wide field */
    }

    for (i = 0; i < C2_SAVE_ARMIES_SIZE / C2_SAVE_ARMY_RECORD; i++) {
        const unsigned char *rec = image->army_list + i * C2_SAVE_ARMY_RECORD;
        signed char cohort = (signed char)rec[0x28];

        if (rec[0] != 0 && (cohort < 0 || cohort >= (signed char)(C2_SAVE_ARMYROUT_SIZE / C2_SAVE_ROUTE_RECORD)))
            return C2_SAVE_ERR_VALIDATION;    /* indexes army_routes[10] and is written through */
    }
    for (i = 0; i < C2_SAVE_ARMYROUT_SIZE / C2_SAVE_ROUTE_RECORD; i++) {
        unsigned char *rec = image->army_routes + i * C2_SAVE_ROUTE_RECORD;

        if ((get_u32(rec + 8) & 0xffffu) > 25u) { put_u32(rec + 8, 0); image->cleared++; }
    }

    if (image->history_count > C2_SAVE_HISTORY_SAMPLES) return C2_SAVE_ERR_VALIDATION;
    return C2_SAVE_OK;
}

/* ---- citizen record <-> schema struct ----------------------------------------- */

static void citizen_to_fb(ns(Citizen_t) *c, const unsigned char *rec)
{
    c->exists = rec[0x00]; c->xp = (int8_t)rec[0x01]; c->type = (int8_t)rec[0x02];
    c->world_dir = (int8_t)rec[0x03]; c->x = (int8_t)rec[0x04]; c->y = (int8_t)rec[0x05];
    c->map_ref = get_i32(rec + 0x06);
    c->pixel_x = rec[0x0a]; c->pixel_y = rec[0x0b];
    c->dest_x = (int8_t)rec[0x0c]; c->dest_y = (int8_t)rec[0x0d];
    c->saved_state_idx = rec[0x0e]; c->wait_count = (int8_t)rec[0x0f]; c->state_idx = (int8_t)rec[0x10];
    c->wf_active = rec[0x11]; c->wf_step = (int8_t)rec[0x12]; c->wf_length = (int8_t)rec[0x13];
    memcpy(c->wf_steps, rec + 0x14, 8);
    c->speed = (int8_t)rec[0x1e]; c->speed_count = (int8_t)rec[0x1f]; c->speed_phase = (int8_t)rec[0x20];
    c->flag_bits = (int8_t)rec[0x21]; c->action_kind = rec[0x22]; c->is_barbarian = rec[0x23];
    c->state_timer = (int8_t)rec[0x24];
    c->market_demand_a = (int8_t)rec[0x26]; c->market_demand_b = (int8_t)rec[0x27];
    c->target_ref = get_i32(rec + 0x28);
    c->target = get_u16(rec + C2_SAVE_CITIZEN_RECORD);
    c->target_count = rec[0x2d];
    c->evolve_timer = get_i16(rec + 0x2e); c->target_marker = get_i16(rec + 0x30);
    c->name_id = rec[0x32]; c->state = rec[0x33];
    c->image_id = get_i16(rec + 0x34); c->wobble_counter = rec[0x36];
}

static void citizen_from_fb(unsigned char *rec, const ns(Citizen_t) *c)
{
    memset(rec, 0, C2_SAVE_CITIZEN_STRIDE);
    rec[0x00] = c->exists; rec[0x01] = (unsigned char)c->xp; rec[0x02] = (unsigned char)c->type;
    rec[0x03] = (unsigned char)c->world_dir; rec[0x04] = (unsigned char)c->x; rec[0x05] = (unsigned char)c->y;
    put_i32(rec + 0x06, c->map_ref);
    rec[0x0a] = c->pixel_x; rec[0x0b] = c->pixel_y;
    rec[0x0c] = (unsigned char)c->dest_x; rec[0x0d] = (unsigned char)c->dest_y;
    rec[0x0e] = c->saved_state_idx; rec[0x0f] = (unsigned char)c->wait_count; rec[0x10] = (unsigned char)c->state_idx;
    rec[0x11] = c->wf_active; rec[0x12] = (unsigned char)c->wf_step; rec[0x13] = (unsigned char)c->wf_length;
    memcpy(rec + 0x14, c->wf_steps, 8);
    rec[0x1e] = (unsigned char)c->speed; rec[0x1f] = (unsigned char)c->speed_count; rec[0x20] = (unsigned char)c->speed_phase;
    rec[0x21] = (unsigned char)c->flag_bits; rec[0x22] = c->action_kind; rec[0x23] = c->is_barbarian;
    rec[0x24] = (unsigned char)c->state_timer;
    rec[0x26] = (unsigned char)c->market_demand_a; rec[0x27] = (unsigned char)c->market_demand_b;
    put_i32(rec + 0x28, c->target_ref);
    put_u16(rec + C2_SAVE_CITIZEN_RECORD, c->target);
    rec[0x2d] = c->target_count;
    put_i16(rec + 0x2e, c->evolve_timer); put_i16(rec + 0x30, c->target_marker);
    rec[0x32] = c->name_id; rec[0x33] = c->state;
    put_i16(rec + 0x34, c->image_id); rec[0x36] = c->wobble_counter;
}

static void cell_to_fb(ns(CityCell_t) *c, const unsigned char *b, uint16_t envoy)
{
    c->base_kind = b[0]; c->terrain = b[1]; c->road_aqueduct = b[2]; c->edge_bits = b[3];
    c->extra_edge = b[4]; c->activity_a = b[5]; c->activity_b = b[6];
    c->building = b[9]; c->range_flag = b[10]; c->fpu_flag = b[11]; c->entertainment = b[12];
    c->education = b[13]; c->health = b[14]; c->land_value = b[15]; c->fire = b[16];
    c->security = b[17]; c->industrial = b[18]; c->business = b[19];
    c->envoy = envoy;
}

static void cell_from_fb(unsigned char *b, uint16_t *envoy, const ns(CityCell_t) *c)
{
    b[0] = c->base_kind; b[1] = c->terrain; b[2] = c->road_aqueduct; b[3] = c->edge_bits;
    b[4] = c->extra_edge; b[5] = c->activity_a; b[6] = c->activity_b; b[7] = 0; b[8] = 0;
    b[9] = c->building; b[10] = c->range_flag; b[11] = c->fpu_flag; b[12] = c->entertainment;
    b[13] = c->education; b[14] = c->health; b[15] = c->land_value; b[16] = c->fire;
    b[17] = c->security; b[18] = c->industrial; b[19] = c->business;
    *envoy = c->envoy;
}

/* ---- encode --------------------------------------------------------------- */

size_t c2_save_encode(const struct c2_save_image *image,
                      const char *engine_version, unsigned char **out)
{
    flatcc_builder_t builder;
    ns(CityCell_t) *cells;
    ns(Citizen_t) *cits;
    ns(HistorySample_t) *samples;
    flatbuffers_bool_t *flags;
    unsigned char *buf, *file;
    size_t size, i;

    if (image == NULL || out == NULL || image->history_count > C2_SAVE_HISTORY_SAMPLES) return 0;
    *out = NULL;

    flatcc_builder_init(&builder);
    if (ns(Save_start_as_root)(&builder)) goto fail;
    ns(Save_format_version_add)(&builder, C2_SAVE_FORMAT_VERSION);
    if (engine_version != NULL) ns(Save_engine_version_create_str)(&builder, engine_version);
    ns(Save_scalars_create)(&builder, image->scalars, image->scalars_size);

    if (ns(Save_city_map_start)(&builder)) goto fail;
    cells = ns(CityCell_vec_extend)(&builder, C2_SAVE_CITY_CELLS);
    if (cells == NULL) goto fail;
    for (i = 0; i < C2_SAVE_CITY_CELLS; i++)
        cell_to_fb(&cells[i], image->city_map + i * C2_SAVE_CITY_CELL_SIZE, image->envoys[i]);
    ns(Save_city_map_end)(&builder);

    ns(Save_region_map_create)(&builder, image->region_map, C2_SAVE_REGIONMP_SIZE);
    ns(Save_battle_map_create)(&builder, image->battle_map, C2_SAVE_BATTLEMP_SIZE);

    if (ns(Save_citizens_start)(&builder)) goto fail;
    cits = ns(Citizen_vec_extend)(&builder, image->citizen_count);
    if (cits == NULL) goto fail;
    for (i = 0; i < image->citizen_count; i++)
        citizen_to_fb(&cits[i], image->citizens + i * C2_SAVE_CITIZEN_STRIDE);
    ns(Save_citizens_end)(&builder);

    ns(Save_armies_create)(&builder, image->army_list, C2_SAVE_ARMIES_SIZE);
    ns(Save_army_routes_create)(&builder, image->army_routes, C2_SAVE_ARMYROUT_SIZE);
    ns(Save_units_create)(&builder, image->unit_list, C2_SAVE_UNITS_SIZE);
    ns(Save_figures_create)(&builder, image->figures, sizeof(image->figures));
    if (ns(Save_figure_secondary_sprite_start)(&builder)) goto fail;
    flags = flatbuffers_bool_vec_extend(&builder, C2_SAVE_FIGURE_COUNT);
    if (flags == NULL) goto fail;
    for (i = 0; i < C2_SAVE_FIGURE_COUNT; i++) flags[i] = image->figure_secondary[i] != 0;
    ns(Save_figure_secondary_sprite_end)(&builder);
    ns(Save_arrows_create)(&builder, image->arrows, sizeof(image->arrows));
    ns(Save_messages_create)(&builder, image->messages, C2_SAVE_MESSAGES_SIZE);
    ns(Save_fire_zones_create)(&builder, image->fire_zones, C2_SAVE_FIREZONE_SIZE);
    ns(Save_industry_create)(&builder, image->industry, C2_SAVE_INDUSTRY_SIZE);
    ns(Save_slave_requirements_create)(&builder, image->slave_requirements, C2_SAVE_SLAVEREQ_SIZE);

    if (ns(Save_history_start)(&builder)) goto fail;
    samples = ns(HistorySample_vec_extend)(&builder, image->history_count);
    if (samples == NULL && image->history_count != 0) goto fail;
    for (i = 0; i < image->history_count; i++) {
        const int32_t *s = image->history + i * C2_SAVE_HISTORY_FIELDS;
        samples[i].population = s[0]; samples[i].denarii = s[1]; samples[i].pop_tax = s[2];
        samples[i].ind_tax = s[3]; samples[i].year = s[4];
    }
    ns(Save_history_end)(&builder);

    ns(Save_end_as_root)(&builder);
    buf = (unsigned char *)flatcc_builder_finalize_aligned_buffer(&builder, &size);
    flatcc_builder_clear(&builder);
    if (buf == NULL) return 0;

    file = (unsigned char *)malloc(size + C2_SAVE_TRAILER_SIZE);
    if (file == NULL) { flatcc_builder_aligned_free(buf); return 0; }
    memcpy(file, buf, size);
    put_u32(file + size, trailer_crc(buf, size));
    flatcc_builder_aligned_free(buf);
    *out = file;
    return size + C2_SAVE_TRAILER_SIZE;

fail:
    flatcc_builder_clear(&builder);
    return 0;
}

/* ---- decode --------------------------------------------------------------- */

int c2_save_detect(const unsigned char *data, size_t size)
{
    if (data == NULL) return -1;
    if (size >= 8 + C2_SAVE_TRAILER_SIZE && memcmp(data + 4, C2_SAVE_FILE_IDENTIFIER, 4) == 0) return 1;
    if (size == C2_SAVE_LEGACY_FILE_SIZE) return 0;
    return -1;
}

static int take(flatbuffers_uint8_vec_t v, void *dst, size_t expected, int *present)
{
    if (v == NULL) { *present = 0; return 1; }
    if (flatbuffers_uint8_vec_len(v) != expected) return 0;
    memcpy(dst, v, expected);
    *present = 1;
    return 1;
}

enum c2_save_status c2_save_decode(const unsigned char *data, size_t size,
                                   const struct save_entry *entries,
                                   size_t entry_count,
                                   const struct c2_save_blocks *blocks,
                                   struct c2_save_image *image)
{
    size_t body;
    ns(Save_table_t) save;
    flatbuffers_uint8_vec_t bytes;
    ns(CityCell_vec_t) cells;
    ns(Citizen_vec_t) cits;
    ns(HistorySample_vec_t) samples;
    flatbuffers_bool_vec_t flags;
    size_t i, n;
    int present;

    if (data == NULL || image == NULL || entries == NULL || blocks == NULL) return C2_SAVE_ERR_ARGS;
    if (c2_save_detect(data, size) != 1) return C2_SAVE_ERR_FORMAT;
    body = size - C2_SAVE_TRAILER_SIZE;
    if (get_u32(data + body) != trailer_crc(data, body)) return C2_SAVE_ERR_CRC;
    if (ns(Save_verify_as_root_with_identifier)(data, body, C2_SAVE_FILE_IDENTIFIER) != 0) return C2_SAVE_ERR_VERIFY;

    save = ns(Save_as_root_with_identifier)(data, C2_SAVE_FILE_IDENTIFIER);
    if (save == NULL) return C2_SAVE_ERR_VERIFY;
    image->format_version = ns(Save_format_version_get)(save);
    if (image->format_version == 0 || image->format_version > C2_SAVE_FORMAT_VERSION) return C2_SAVE_ERR_VERSION;

    bytes = ns(Save_scalars_get)(save);
    if (bytes == NULL) return C2_SAVE_ERR_MISSING;
    if (flatbuffers_uint8_vec_len(bytes) != c2_save_scalars_size(entries, entry_count, blocks) ||
        flatbuffers_uint8_vec_len(bytes) != image->scalars_size) return C2_SAVE_ERR_REGISTRY;
    memcpy(image->scalars, bytes, image->scalars_size);

    cells = ns(Save_city_map_get)(save);
    if (cells == NULL) return C2_SAVE_ERR_MISSING;
    if (ns(CityCell_vec_len)(cells) != C2_SAVE_CITY_CELLS) return C2_SAVE_ERR_SHAPE;
    for (i = 0; i < C2_SAVE_CITY_CELLS; i++)
        cell_from_fb(image->city_map + i * C2_SAVE_CITY_CELL_SIZE, &image->envoys[i], ns(CityCell_vec_at)(cells, i));

    if (!take(ns(Save_region_map_get)(save), image->region_map, C2_SAVE_REGIONMP_SIZE, &present)) return C2_SAVE_ERR_SHAPE;
    if (!present) return C2_SAVE_ERR_MISSING;
    if (!take(ns(Save_battle_map_get)(save), image->battle_map, C2_SAVE_BATTLEMP_SIZE, &present)) return C2_SAVE_ERR_SHAPE;

    cits = ns(Save_citizens_get)(save);
    if (cits == NULL) return C2_SAVE_ERR_MISSING;
    n = ns(Citizen_vec_len)(cits);
    if (n == 0) return C2_SAVE_ERR_SHAPE;
    memset(image->citizens, 0, (size_t)image->citizen_count * C2_SAVE_CITIZEN_STRIDE);
    for (i = 0; i < n; i++) {
        if (i < image->citizen_count)
            citizen_from_fb(image->citizens + i * C2_SAVE_CITIZEN_STRIDE, ns(Citizen_vec_at)(cits, i));
        else if (ns(Citizen_vec_at)(cits, i)->exists != 0)
            image->dropped_citizens++;
    }

    if (!take(ns(Save_armies_get)(save), image->army_list, C2_SAVE_ARMIES_SIZE, &present)) return C2_SAVE_ERR_SHAPE;
    if (!take(ns(Save_army_routes_get)(save), image->army_routes, C2_SAVE_ARMYROUT_SIZE, &present)) return C2_SAVE_ERR_SHAPE;
    if (!take(ns(Save_units_get)(save), image->unit_list, C2_SAVE_UNITS_SIZE, &present)) return C2_SAVE_ERR_SHAPE;
    if (!take(ns(Save_figures_get)(save), image->figures, sizeof(image->figures), &present)) return C2_SAVE_ERR_SHAPE;
    flags = ns(Save_figure_secondary_sprite_get)(save);
    memset(image->figure_secondary, 0, sizeof(image->figure_secondary));
    if (flags != NULL) {
        if (flatbuffers_bool_vec_len(flags) != C2_SAVE_FIGURE_COUNT) return C2_SAVE_ERR_SHAPE;
        for (i = 0; i < C2_SAVE_FIGURE_COUNT; i++) image->figure_secondary[i] = flatbuffers_bool_vec_at(flags, i) != 0;
    }
    if (!take(ns(Save_arrows_get)(save), image->arrows, sizeof(image->arrows), &present)) return C2_SAVE_ERR_SHAPE;
    if (!take(ns(Save_messages_get)(save), image->messages, C2_SAVE_MESSAGES_SIZE, &present)) return C2_SAVE_ERR_SHAPE;
    if (!take(ns(Save_fire_zones_get)(save), image->fire_zones, C2_SAVE_FIREZONE_SIZE, &present)) return C2_SAVE_ERR_SHAPE;
    if (!take(ns(Save_industry_get)(save), image->industry, C2_SAVE_INDUSTRY_SIZE, &present)) return C2_SAVE_ERR_SHAPE;
    if (!take(ns(Save_slave_requirements_get)(save), image->slave_requirements, C2_SAVE_SLAVEREQ_SIZE, &present)) return C2_SAVE_ERR_SHAPE;

    samples = ns(Save_history_get)(save);
    if (samples == NULL) return C2_SAVE_ERR_MISSING;
    n = ns(HistorySample_vec_len)(samples);
    if (n > C2_SAVE_HISTORY_SAMPLES) return C2_SAVE_ERR_SHAPE;
    for (i = 0; i < n; i++) {
        const ns(HistorySample_t) *s = ns(HistorySample_vec_at)(samples, i);
        int32_t *d = image->history + i * C2_SAVE_HISTORY_FIELDS;
        d[0] = s->population; d[1] = s->denarii; d[2] = s->pop_tax; d[3] = s->ind_tax; d[4] = s->year;
    }
    image->history_count = (uint32_t)n;

    return c2_save_validate(image, image->citizen_count);
}

/* ---- legacy import (version 0) ------------------------------------------------ */

static void figure_from_legacy(unsigned char *dst, unsigned char *secondary, const unsigned char *src)
{
    /* [0, 0x0a) fields; [0x0a, 0x12) two pointer markers; [0x12, 0x58) tail. */
    memcpy(dst, src, C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET);
    memcpy(dst + C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET,
           src + C2_SAVE_LEGACY_FIGURE_TAIL_OFFSET,
           C2_SAVE_LEGACY_FIGURE_RECORD - C2_SAVE_LEGACY_FIGURE_TAIL_OFFSET);
    *secondary = (src[0x0e] | src[0x0f] | src[0x10] | src[0x11]) != 0;
}

static void arrow_from_legacy(unsigned char *dst, const unsigned char *src)
{
    memcpy(dst, src, C2_SAVE_LEGACY_ARROW_POINTER_OFFSET);
    memcpy(dst + C2_SAVE_LEGACY_ARROW_POINTER_OFFSET,
           src + C2_SAVE_LEGACY_ARROW_TAIL_OFFSET,
           C2_SAVE_LEGACY_ARROW_RECORD - C2_SAVE_LEGACY_ARROW_TAIL_OFFSET);
}

#define REL(e, base) ((size_t)((const unsigned char *)(e)->buf - (const unsigned char *)(base)))

enum c2_save_status c2_save_import_legacy(const unsigned char *data, size_t size,
                                          const struct save_entry *entries,
                                          size_t entry_count,
                                          const struct c2_save_blocks *blocks,
                                          struct c2_save_image *image)
{
    size_t i, in = 0, scalar_off = 0;
    int end_ptr = 0, entries_n = 0;
    uint32_t k;

    if (data == NULL || image == NULL || entries == NULL || blocks == NULL) return C2_SAVE_ERR_ARGS;
    if (size != C2_SAVE_LEGACY_FILE_SIZE) return C2_SAVE_ERR_FORMAT;
    if (image->scalars_size != c2_save_scalars_size(entries, entry_count, blocks)) return C2_SAVE_ERR_REGISTRY;
    if (image->citizen_count < C2_SAVE_LEGACY_CITIZENS) return C2_SAVE_ERR_ARGS;

    image->format_version = 0;
    memset(image->envoys, 0, sizeof(image->envoys));
    memset(image->figure_secondary, 0, sizeof(image->figure_secondary));
    memset(image->citizens, 0, (size_t)image->citizen_count * C2_SAVE_CITIZEN_STRIDE);

    for (i = 0; i < entry_count; i++) {
        const struct save_entry *e = &entries[i];
        size_t sz, n;

        if (e->size == 0) break;
        sz = (size_t)e->size;
        if (in + sz > C2_SAVE_LEGACY_STATE_SIZE) return C2_SAVE_ERR_REGISTRY;
        switch (classify(e, blocks)) {
        case BLK_SCALAR:
            memcpy(image->scalars + scalar_off, data + in, sz); scalar_off += sz; break;
        case BLK_SKIP:
            if (e->buf == blocks->history_end_ptr) end_ptr = get_i32(data + in);
            else if (e->buf == blocks->history_entries) entries_n = get_i32(data + in);
            break;
        case BLK_CITYMAP:  memcpy(image->city_map + REL(e, blocks->city_map), data + in, sz); break;
        case BLK_REGIONMP: memcpy(image->region_map + REL(e, blocks->region_map), data + in, sz); break;
        case BLK_BATTLEMP: memcpy(image->battle_map + REL(e, blocks->battle_map), data + in, sz); break;
        case BLK_CITIZENS:
            n = sz / C2_SAVE_CITIZEN_RECORD;
            for (k = 0; k < n && k < image->citizen_count; k++) {
                unsigned char *dst = image->citizens + (size_t)k * C2_SAVE_CITIZEN_STRIDE;
                const unsigned char *src = data + in + (size_t)k * C2_SAVE_CITIZEN_RECORD;

                memcpy(dst, src, C2_SAVE_CITIZEN_RECORD);
                put_u16(dst + C2_SAVE_CITIZEN_RECORD, src[0x2c]);
            }
            break;
        case BLK_ARMIES:   memcpy(image->army_list + REL(e, blocks->army_list), data + in, sz); break;
        case BLK_ARMYROUT: memcpy(image->army_routes + REL(e, blocks->army_routes), data + in, sz); break;
        case BLK_UNITS:    memcpy(image->unit_list + REL(e, blocks->unit_list), data + in, sz); break;
        case BLK_FIGURES:
            if (sz != C2_SAVE_FIGURE_COUNT * C2_SAVE_LEGACY_FIGURE_RECORD) return C2_SAVE_ERR_REGISTRY;
            for (k = 0; k < C2_SAVE_FIGURE_COUNT; k++)
                figure_from_legacy(image->figures + k * C2_SAVE_FIGURE_RECORD, &image->figure_secondary[k],
                                   data + in + k * C2_SAVE_LEGACY_FIGURE_RECORD);
            break;
        case BLK_ARROWS:
            if (sz != C2_SAVE_ARROW_COUNT * C2_SAVE_LEGACY_ARROW_RECORD) return C2_SAVE_ERR_REGISTRY;
            for (k = 0; k < C2_SAVE_ARROW_COUNT; k++)
                arrow_from_legacy(image->arrows + k * C2_SAVE_ARROW_RECORD, data + in + k * C2_SAVE_LEGACY_ARROW_RECORD);
            break;
        case BLK_MESSAGES:
            if (REL(e, blocks->message_list) + sz <= C2_SAVE_MESSAGES_SIZE)
                memcpy(image->messages + REL(e, blocks->message_list), data + in, sz);
            break;
        case BLK_FIREZONE: memcpy(image->fire_zones + REL(e, blocks->fire_zones), data + in, sz); break;
        case BLK_INDUSTRY: memcpy(image->industry + REL(e, blocks->industry), data + in, sz); break;
        case BLK_SLAVEREQ: memcpy(image->slave_requirements + REL(e, blocks->slave_requirements), data + in, sz); break;
        }
        in += sz;
    }
    if (in != C2_SAVE_LEGACY_STATE_SIZE || scalar_off != image->scalars_size) return C2_SAVE_ERR_REGISTRY;

    /* Envoys lived in cell byte +0x12 of market and business cells. */
    for (k = 0; k < C2_SAVE_CITY_CELLS; k++) {
        const unsigned char *cell = image->city_map + k * C2_SAVE_CITY_CELL_SIZE;
        if (is_market_or_business(cell[0])) image->envoys[k] = cell[0x12];
    }

    /* History: a 200-slot ring whose end_ptr is the next write slot.
     * Linearise oldest-first; start_ptr is write-only in the engine. */
    {
        const unsigned char *ring = data + C2_SAVE_LEGACY_STATE_SIZE;
        int n = entries_n, start, s;

        if (n < 0) n = 0;
        if (n > (int)C2_SAVE_HISTORY_SAMPLES) n = (int)C2_SAVE_HISTORY_SAMPLES;
        if (end_ptr < 0 || end_ptr >= (int)C2_SAVE_HISTORY_SAMPLES) end_ptr = 0;
        start = end_ptr - n;
        if (start < 0) start += (int)C2_SAVE_HISTORY_SAMPLES;
        for (s = 0; s < n; s++) {
            int slot = (start + s) % (int)C2_SAVE_HISTORY_SAMPLES;
            for (k = 0; k < C2_SAVE_HISTORY_FIELDS; k++)
                image->history[(size_t)s * C2_SAVE_HISTORY_FIELDS + k] =
                    get_i32(ring + ((size_t)slot * C2_SAVE_HISTORY_FIELDS + k) * 4);
        }
        image->history_count = (uint32_t)n;
    }

    return c2_save_validate(image, image->citizen_count);
}

/* ---- diff ------------------------------------------------------------------- */

const char *c2_save_image_diff(const struct c2_save_image *a,
                               const struct c2_save_image *b)
{
    uint32_t n;

    if (a->scalars_size != b->scalars_size || memcmp(a->scalars, b->scalars, a->scalars_size)) return "scalars";
    if (memcmp(a->city_map, b->city_map, sizeof(a->city_map))) return "city_map";
    if (memcmp(a->envoys, b->envoys, sizeof(a->envoys))) return "envoys";
    if (memcmp(a->region_map, b->region_map, sizeof(a->region_map))) return "region_map";
    if (memcmp(a->battle_map, b->battle_map, sizeof(a->battle_map))) return "battle_map";
    n = a->citizen_count < b->citizen_count ? a->citizen_count : b->citizen_count;
    if (memcmp(a->citizens, b->citizens, (size_t)n * C2_SAVE_CITIZEN_STRIDE)) return "citizens";
    if (memcmp(a->army_list, b->army_list, sizeof(a->army_list))) return "armies";
    if (memcmp(a->army_routes, b->army_routes, sizeof(a->army_routes))) return "army_routes";
    if (memcmp(a->unit_list, b->unit_list, sizeof(a->unit_list))) return "units";
    if (memcmp(a->figures, b->figures, sizeof(a->figures))) return "figures";
    if (memcmp(a->figure_secondary, b->figure_secondary, sizeof(a->figure_secondary))) return "figure_secondary_sprite";
    if (memcmp(a->arrows, b->arrows, sizeof(a->arrows))) return "arrows";
    if (memcmp(a->messages, b->messages, sizeof(a->messages))) return "messages";
    if (memcmp(a->fire_zones, b->fire_zones, sizeof(a->fire_zones))) return "fire_zones";
    if (memcmp(a->industry, b->industry, sizeof(a->industry))) return "industry";
    if (memcmp(a->slave_requirements, b->slave_requirements, sizeof(a->slave_requirements))) return "slave_requirements";
    if (a->history_count != b->history_count ||
        memcmp(a->history, b->history, (size_t)a->history_count * C2_SAVE_HISTORY_FIELDS * 4)) return "history";
    return NULL;
}
