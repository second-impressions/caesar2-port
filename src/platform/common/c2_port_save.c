#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_citizen_index.h"
#include "c2_data.h"
#include "c2_host.h"
#include "c2_port_save.h"
#include "c2_save_v1.h"
#include "c2_version.h"

/*
 * Engine adapter: translates between the engine's globals and the save
 * core's staging image, and owns the file I/O. The core (c2_save_v1.c) never
 * touches globals; this file never parses bytes.
 */

#define C2_SAVE_TEMP_SUFFIX ".tmp"

unsigned char c2_figure_secondary_sprite[C2_SAVE_FIGURE_COUNT];

static char last_error[160];

const char *c2_port_save_last_error(void)
{
    return last_error;
}

static void set_error(const char *what, enum c2_save_status status)
{
    snprintf(last_error, sizeof(last_error), "%s: %s", what, c2_save_status_name(status));
}

/* ---- block table from the engine's globals ---------------------------------- */

static void engine_blocks(struct c2_save_blocks *blocks)
{
    memset(blocks, 0, sizeof(*blocks));
    blocks->city_map = city_map;
    blocks->region_map = region_map;
    blocks->battle_map = battle_map;
    blocks->citizen_list = citizen_list;
    blocks->army_list = army_list;
    blocks->army_routes = army_routes;
    blocks->unit_list = unit_list;
    blocks->figure_list = figure_list;
    blocks->arrow_list = arrow_list;
    blocks->message_list = message_list;
    blocks->fire_zones = fire_zones;
    blocks->industry = industry;
    blocks->slave_requirements = slave_requirements;
    blocks->history_end_ptr = &history_end_ptr;
    blocks->history_start_ptr = &history_start_ptr;
    blocks->history_entries = &history_entries;
}

/* Every registry entry that is not one of the blocks above, in order. */
static int is_scalar_entry(const struct save_entry *e, const struct c2_save_blocks *b)
{
    const unsigned char *p = (const unsigned char *)e->buf;
#define IN(base, size) (p >= (const unsigned char *)(base) && p < (const unsigned char *)(base) + (size))
    if (e->buf == b->history_end_ptr || e->buf == b->history_start_ptr || e->buf == b->history_entries) return 0;
    if (IN(b->city_map, C2_SAVE_CITYMAP_SIZE) || IN(b->region_map, C2_SAVE_REGIONMP_SIZE) ||
        IN(b->battle_map, C2_SAVE_BATTLEMP_SIZE) || IN(b->citizen_list, C2_SAVE_LEGACY_CITIZENS * C2_SAVE_CITIZEN_RECORD) ||
        IN(b->army_list, C2_SAVE_ARMIES_SIZE) || IN(b->army_routes, C2_SAVE_ARMYROUT_SIZE) ||
        IN(b->unit_list, C2_SAVE_UNITS_SIZE) || IN(b->figure_list, sizeof(struct figure_rec) * C2_SAVE_FIGURE_COUNT) ||
        IN(b->arrow_list, sizeof(struct arrow_rec) * C2_SAVE_ARROW_COUNT) || IN(b->message_list, C2_SAVE_MESSAGES_SIZE) ||
        IN(b->fire_zones, C2_SAVE_FIREZONE_SIZE) || IN(b->industry, C2_SAVE_INDUSTRY_SIZE) ||
        IN(b->slave_requirements, C2_SAVE_SLAVEREQ_SIZE)) return 0;
#undef IN
    return 1;
}

/* ---- history ring ------------------------------------------------------------- */

static int history_ring[C2_SAVE_HISTORY_SAMPLES * C2_SAVE_HISTORY_FIELDS];

void c2_port_history_reset(void)
{
    memset(history_ring, 0, sizeof(history_ring));
}

void c2_port_history_store(const int *entry, int slot)
{
    if (slot < 0 || slot >= (int)C2_SAVE_HISTORY_SAMPLES) return;
    memcpy(history_ring + (size_t)slot * C2_SAVE_HISTORY_FIELDS, entry, C2_SAVE_HISTORY_FIELDS * sizeof(int));
}

void c2_port_history_copy(int *out)
{
    memcpy(out, history_ring, sizeof(history_ring));
}

/* ---- capture: globals -> image ---------------------------------------------------- */

static void capture_figures(struct c2_save_image *image, const struct figure_rec *figures,
                            const struct arrow_rec *arrows)
{
    size_t i;

    for (i = 0; i < C2_SAVE_FIGURE_COUNT; i++) {
        const unsigned char *rec = (const unsigned char *)&figures[i];
        unsigned char *dst = image->figures + i * C2_SAVE_FIGURE_RECORD;

        memcpy(dst, rec, C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET);
        memcpy(dst + C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET,
               rec + offsetof(struct figure_rec, map_ref),
               C2_SAVE_FIGURE_RECORD - C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET);
        image->figure_secondary[i] = figures[i].sprite_data_ptr != NULL || c2_figure_secondary_sprite[i];
    }
    for (i = 0; i < C2_SAVE_ARROW_COUNT; i++) {
        const unsigned char *rec = (const unsigned char *)&arrows[i];
        unsigned char *dst = image->arrows + i * C2_SAVE_ARROW_RECORD;

        memcpy(dst, rec, C2_SAVE_LEGACY_ARROW_POINTER_OFFSET);
        memcpy(dst + C2_SAVE_LEGACY_ARROW_POINTER_OFFSET,
               rec + offsetof(struct arrow_rec, grid_x),
               C2_SAVE_ARROW_RECORD - C2_SAVE_LEGACY_ARROW_POINTER_OFFSET);
    }
}

static int capture(struct c2_save_image *image, const struct save_entry *entries,
                   size_t entry_count, const struct figure_rec *figures,
                   const struct arrow_rec *arrows)
{
    struct c2_save_blocks blocks;
    size_t i, off = 0;
    uint32_t k;
    int n, start, s;

    engine_blocks(&blocks);
    if (!c2_save_image_init(image, c2_save_scalars_size(entries, entry_count, &blocks), PORT_CITIZEN_SLOTS))
        return 0;

    for (i = 0; i < entry_count; i++) {
        if (entries[i].size == 0) break;
        if (!is_scalar_entry(&entries[i], &blocks)) continue;
        memcpy(image->scalars + off, entries[i].buf, (size_t)entries[i].size);
        off += (size_t)entries[i].size;
    }

    memcpy(image->city_map, city_map, C2_SAVE_CITYMAP_SIZE);
    for (k = 0; k < C2_SAVE_CITY_CELLS; k++) {
        unsigned char kind = image->city_map[k * C2_SAVE_CITY_CELL_SIZE];
        if (kind == 0xfa || kind >= 0xfc)
            image->envoys[k] = (uint16_t)PORT_CELL_ENVOY((int)k * C2_SAVE_CITY_CELL_SIZE);
    }
    memcpy(image->region_map, region_map, C2_SAVE_REGIONMP_SIZE);
    memcpy(image->battle_map, battle_map, C2_SAVE_BATTLEMP_SIZE);

    for (k = 0; k < PORT_CITIZEN_SLOTS; k++) {
        unsigned char *rec = image->citizens + (size_t)k * C2_SAVE_CITIZEN_STRIDE;
        uint16_t target = (uint16_t)PORT_CITIZEN_TARGET(k);

        memcpy(rec, &citizen_list[k], C2_SAVE_CITIZEN_RECORD);
        rec[C2_SAVE_CITIZEN_RECORD] = (unsigned char)target;
        rec[C2_SAVE_CITIZEN_RECORD + 1] = (unsigned char)(target >> 8);
    }

    memcpy(image->army_list, army_list, C2_SAVE_ARMIES_SIZE);
    memcpy(image->army_routes, army_routes, C2_SAVE_ARMYROUT_SIZE);
    memcpy(image->unit_list, unit_list, C2_SAVE_UNITS_SIZE);
    capture_figures(image, figures, arrows);
    memcpy(image->messages, message_list, C2_SAVE_MESSAGES_SIZE);
    memcpy(image->fire_zones, fire_zones, C2_SAVE_FIREZONE_SIZE);
    memcpy(image->industry, industry, C2_SAVE_INDUSTRY_SIZE);
    memcpy(image->slave_requirements, slave_requirements, C2_SAVE_SLAVEREQ_SIZE);

    /* Ring -> chronological. end_ptr is the next write slot. */
    n = history_entries;
    if (n < 0) n = 0;
    if (n > (int)C2_SAVE_HISTORY_SAMPLES) n = (int)C2_SAVE_HISTORY_SAMPLES;
    start = history_end_ptr - n;
    if (start < 0) start += (int)C2_SAVE_HISTORY_SAMPLES;
    for (s = 0; s < n; s++) {
        int slot = (start + s) % (int)C2_SAVE_HISTORY_SAMPLES;
        memcpy(image->history + (size_t)s * C2_SAVE_HISTORY_FIELDS,
               history_ring + (size_t)slot * C2_SAVE_HISTORY_FIELDS,
               C2_SAVE_HISTORY_FIELDS * sizeof(int));
    }
    image->history_count = (uint32_t)n;

    return c2_save_validate(image, PORT_CITIZEN_SLOTS) == C2_SAVE_OK;
}

/* ---- commit: image -> globals ----------------------------------------------------- */

static void rebuild_occupancy(void)
{
    int i;

#if PORT_FEAT_WIDE_CITIZEN_INDEX
    for (i = 0; i < PORT_CITY_CELLS; i++) { c2_cell_citizen_a[i] = 0; c2_cell_citizen_b[i] = 0; }
#else
    for (i = 0; i < PORT_CITY_CELLS; i++) { PORT_CELL_CITIZEN_A(i * 20) = 0; PORT_CELL_CITIZEN_B(i * 20) = 0; }
#endif
    for (i = 1; i < PORT_CITIZEN_SLOTS; i++) {
        int ref;

        if (citizen_list[i].exists == 0) continue;
        ref = citizen_list[i].map_ref;
        if (PORT_CELL_CITIZEN_A(ref) == 0) PORT_CELL_CITIZEN_A(ref) = (unsigned short)i;
        else if (PORT_CELL_CITIZEN_B(ref) == 0) PORT_CELL_CITIZEN_B(ref) = (unsigned short)i;
        else memset(&citizen_list[i], 0, sizeof(citizen_list[i]));   /* a third walker on one tile cannot exist */
    }
}

static void commit(const struct c2_save_image *image, const struct save_entry *entries,
                   size_t entry_count, struct figure_rec *figures, struct arrow_rec *arrows)
{
    struct c2_save_blocks blocks;
    size_t i, off = 0;
    uint32_t k;

    engine_blocks(&blocks);
    for (i = 0; i < entry_count; i++) {
        if (entries[i].size == 0) break;
        if (!is_scalar_entry(&entries[i], &blocks)) continue;
        memcpy(entries[i].buf, image->scalars + off, (size_t)entries[i].size);
        off += (size_t)entries[i].size;
    }

    memcpy(city_map, image->city_map, C2_SAVE_CITYMAP_SIZE);
#if PORT_FEAT_WIDE_CITIZEN_INDEX
    c2_citizen_index_clear();
#endif
    for (k = 0; k < C2_SAVE_CITY_CELLS; k++)
        PORT_CELL_ENVOY((int)k * C2_SAVE_CITY_CELL_SIZE) = PORT_CITIZEN_CAST(image->envoys[k]);
    memcpy(region_map, image->region_map, C2_SAVE_REGIONMP_SIZE);
    memcpy(battle_map, image->battle_map, C2_SAVE_BATTLEMP_SIZE);

    for (k = 0; k < PORT_CITIZEN_SLOTS; k++) {
        const unsigned char *rec = image->citizens + (size_t)k * C2_SAVE_CITIZEN_STRIDE;

        if (k < image->citizen_count) {
            memcpy(&citizen_list[k], rec, C2_SAVE_CITIZEN_RECORD);
            PORT_CITIZEN_TARGET(k) = PORT_CITIZEN_CAST(rec[C2_SAVE_CITIZEN_RECORD] | (rec[C2_SAVE_CITIZEN_RECORD + 1] << 8));
        } else {
            memset(&citizen_list[k], 0, sizeof(citizen_list[k]));
            PORT_CITIZEN_TARGET(k) = 0;
        }
    }
    rebuild_occupancy();

    memcpy(army_list, image->army_list, C2_SAVE_ARMIES_SIZE);
    memcpy(army_routes, image->army_routes, C2_SAVE_ARMYROUT_SIZE);
    memcpy(unit_list, image->unit_list, C2_SAVE_UNITS_SIZE);
    for (i = 0; i < C2_SAVE_FIGURE_COUNT; i++) {
        unsigned char *rec = (unsigned char *)&figures[i];
        const unsigned char *src = image->figures + i * C2_SAVE_FIGURE_RECORD;

        memcpy(rec, src, C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET);
        figures[i].arrow_data_ptr = NULL;
        figures[i].sprite_data_ptr = NULL;     /* rebuilt from sprite_kind on entering the battle view */
        memcpy(rec + offsetof(struct figure_rec, map_ref), src + C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET,
               C2_SAVE_FIGURE_RECORD - C2_SAVE_LEGACY_FIGURE_POINTER_OFFSET);
        c2_figure_secondary_sprite[i] = image->figure_secondary[i];
    }
    for (i = 0; i < C2_SAVE_ARROW_COUNT; i++) {
        unsigned char *rec = (unsigned char *)&arrows[i];
        const unsigned char *src = image->arrows + i * C2_SAVE_ARROW_RECORD;

        memcpy(rec, src, C2_SAVE_LEGACY_ARROW_POINTER_OFFSET);
        arrows[i].arrow_data_ptr = NULL;
        memcpy(rec + offsetof(struct arrow_rec, grid_x), src + C2_SAVE_LEGACY_ARROW_POINTER_OFFSET,
               C2_SAVE_ARROW_RECORD - C2_SAVE_LEGACY_ARROW_POINTER_OFFSET);
    }
    memcpy(message_list, image->messages, C2_SAVE_MESSAGES_SIZE);
    memcpy(fire_zones, image->fire_zones, C2_SAVE_FIREZONE_SIZE);
    memcpy(industry, image->industry, C2_SAVE_INDUSTRY_SIZE);
    memcpy(slave_requirements, image->slave_requirements, C2_SAVE_SLAVEREQ_SIZE);

    /* Chronological -> ring at slots 0..n-1; the engine reads only end_ptr. */
    c2_port_history_reset();
    memcpy(history_ring, image->history, (size_t)image->history_count * C2_SAVE_HISTORY_FIELDS * sizeof(int));
    history_entries = (int)image->history_count;
    history_end_ptr = (int)(image->history_count % C2_SAVE_HISTORY_SAMPLES);
    history_start_ptr = 0;
}

/* ---- file I/O ------------------------------------------------------------------ */

static unsigned char *read_whole(const char *filename, size_t *size)
{
    /* Saves are a few hundred KB; a container is never larger than this. */
    static const size_t limit = 8u * 1024u * 1024u;
    unsigned char *buf = (unsigned char *)malloc(limit + 1);
    size_t n;

    if (buf == NULL) return NULL;
    n = c2_host_user_file_read(filename, buf, limit + 1, 0);
    if (n == 0 || n > limit) { free(buf); return NULL; }
    *size = n;
    return buf;
}

static int load_image(const char *filename, const struct save_entry *entries, size_t entry_count,
                      struct c2_save_image *image)
{
    struct c2_save_blocks blocks;
    unsigned char *data;
    size_t size;
    enum c2_save_status st;

    engine_blocks(&blocks);
    data = read_whole(filename, &size);
    if (data == NULL) { snprintf(last_error, sizeof(last_error), "%s: cannot read", filename); return 0; }
    if (!c2_save_image_init(image, c2_save_scalars_size(entries, entry_count, &blocks), PORT_CITIZEN_SLOTS)) {
        free(data); set_error(filename, C2_SAVE_ERR_MEMORY); return 0;
    }
    switch (c2_save_detect(data, size)) {
    case 1:  st = c2_save_decode(data, size, entries, entry_count, &blocks, image); break;
    case 0:  st = c2_save_import_legacy(data, size, entries, entry_count, &blocks, image); break;
    default: st = C2_SAVE_ERR_FORMAT; break;
    }
    free(data);
    if (st != C2_SAVE_OK) { set_error(filename, st); c2_save_image_free(image); return 0; }
    if (image->dropped_citizens != 0)
        fprintf(stderr, "caesar2: %s holds %u more walkers than this build's pool of %d; they were dropped\n",
                filename, image->dropped_citizens, PORT_CITIZEN_POOL);
    if (image->cleared != 0)
        fprintf(stderr, "caesar2: %s: %u out-of-range references cleared\n", filename, image->cleared);
    last_error[0] = '\0';
    return 1;
}

int c2_port_save_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            const struct figure_rec *figures,
                            const struct arrow_rec *arrows)
{
    struct c2_save_image *image;
    unsigned char *data;
    size_t size;
    char temp[64];
    int ok;

    if (entry_count != C2_SAVE_REGISTRY_CAPACITY ||
        !c2_port_save_registry_valid(entries, entry_count, figures, arrows)) return 0;
    /* The image is a few hundred KB: never on the stack (the Wasm worker's
     * is small). */
    image = (struct c2_save_image *)malloc(sizeof(*image));
    if (image == NULL) { set_error(filename, C2_SAVE_ERR_MEMORY); return 0; }
    if (!capture(image, entries, entry_count, figures, arrows)) {
        c2_save_image_free(image); free(image); set_error(filename, C2_SAVE_ERR_VALIDATION); return 0;
    }
    size = c2_save_encode(image, C2_VERSION_STRING, &data);
    c2_save_image_free(image);
    free(image);
    if (size == 0) { set_error(filename, C2_SAVE_ERR_MEMORY); return 0; }

    /* Write beside the target, then rename over it, so a crash mid-write
     * cannot destroy the slot being overwritten. Hosts without rename fall
     * back to writing in place. */
    if (snprintf(temp, sizeof(temp), "%s%s", filename, C2_SAVE_TEMP_SUFFIX) >= (int)sizeof(temp)) {
        free(data); return 0;
    }
    ok = c2_host_user_file_write(temp, data, size) && c2_host_user_file_rename(temp, filename);
    if (!ok) {
        c2_host_user_file_remove(temp);
        ok = c2_host_user_file_write(filename, data, size);
    }
    free(data);
    if (!ok) snprintf(last_error, sizeof(last_error), "%s: cannot write", filename);
    else last_error[0] = '\0';
    return ok;
}

int c2_port_load_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            struct figure_rec *figures,
                            struct arrow_rec *arrows)
{
    struct c2_save_image *image;

    if (entry_count != C2_SAVE_REGISTRY_CAPACITY ||
        !c2_port_save_registry_valid(entries, entry_count, figures, arrows)) return 0;
    image = (struct c2_save_image *)malloc(sizeof(*image));
    if (image == NULL) { set_error(filename, C2_SAVE_ERR_MEMORY); return 0; }
    if (!load_image(filename, entries, entry_count, image)) { free(image); return 0; }
    commit(image, entries, entry_count, figures, arrows);
    c2_save_image_free(image);
    free(image);
    return 1;
}

int c2_port_save_state_file_matches(
    const char *filename, const struct save_entry *entries,
    size_t entry_count, const struct figure_rec *figures,
    const struct arrow_rec *arrows, const char **mismatch_part)
{
    struct c2_save_image *live, *file;
    const char *diff = "(unreadable)";

    if (mismatch_part != NULL) *mismatch_part = NULL;
    if (filename == NULL || entry_count != C2_SAVE_REGISTRY_CAPACITY ||
        !c2_port_save_registry_valid(entries, entry_count, figures, arrows)) return 0;
    live = (struct c2_save_image *)malloc(sizeof(*live));
    file = (struct c2_save_image *)malloc(sizeof(*file));
    if (live == NULL || file == NULL) { free(live); free(file); return 0; }
    if (capture(live, entries, entry_count, figures, arrows) &&
        load_image(filename, entries, entry_count, file)) {
        diff = c2_save_image_diff(live, file);
        c2_save_image_free(file);
    }
    c2_save_image_free(live);
    free(live);
    free(file);
    if (mismatch_part != NULL) *mismatch_part = diff;
    return diff == NULL;
}
