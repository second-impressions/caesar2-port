/*
 * Save format core: encode/decode round trip, original-layout import,
 * validation, negative corpus. Synthetic state only; the engine adapter is
 * covered by the recovered-engine smoke.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include <unity/unity.h>
#include <zlib.h>

#include "c2_save_compat.h"
#include "c2_save_v1.h"
#include "c2_save_gen/c2_save_builder.h"

/* Synthetic engine state the registry and blocks point at. */
static unsigned char t_city_map[C2_SAVE_CITYMAP_SIZE];
static unsigned char t_region_map[C2_SAVE_REGIONMP_SIZE];
static unsigned char t_battle_map[C2_SAVE_BATTLEMP_SIZE];
static unsigned char t_citizen_list[C2_SAVE_LEGACY_CITIZENS * C2_SAVE_CITIZEN_RECORD];
static unsigned char t_army_list[C2_SAVE_ARMIES_SIZE];
static unsigned char t_army_routes[C2_SAVE_ARMYROUT_SIZE];
static unsigned char t_unit_list[C2_SAVE_UNITS_SIZE];
static struct figure_rec t_figure_list[C2_SAVE_FIGURE_COUNT];
static struct arrow_rec t_arrow_list[C2_SAVE_ARROW_COUNT];
static unsigned char t_message_list[C2_SAVE_MESSAGES_SIZE];
static unsigned char t_fire_zones[C2_SAVE_FIREZONE_SIZE];
static unsigned char t_industry[C2_SAVE_INDUSTRY_SIZE];
static unsigned char t_slave_requirements[C2_SAVE_SLAVEREQ_SIZE];
static int t_history_end_ptr, t_history_start_ptr, t_history_entries;

/* The legacy layout has 221,745 state bytes; the blocks above account for
 * all but this many, which the registry spreads over small entries. */
#define BLOCK_BYTES \
    (C2_SAVE_CITYMAP_SIZE + C2_SAVE_REGIONMP_SIZE + C2_SAVE_BATTLEMP_SIZE + \
     C2_SAVE_LEGACY_CITIZENS * C2_SAVE_CITIZEN_RECORD + C2_SAVE_ARMIES_SIZE + \
     C2_SAVE_ARMYROUT_SIZE + C2_SAVE_UNITS_SIZE + C2_SAVE_FIGURES_SIZE + \
     C2_SAVE_ARROWS_SIZE + C2_SAVE_MESSAGES_SIZE + C2_SAVE_FIREZONE_SIZE + \
     C2_SAVE_INDUSTRY_SIZE + C2_SAVE_SLAVEREQ_SIZE + 12 + 64)   /* + history indices + the message_list alias */
#define SCALAR_BYTES (C2_SAVE_STATE_SIZE - BLOCK_BYTES)
static unsigned char scalars[SCALAR_BYTES];

static struct save_entry entries[C2_SAVE_REGISTRY_CAPACITY];
static struct c2_save_blocks blocks;

#define POOL_SLOTS 1001u

static void put32(unsigned char *p, int32_t v)
{
    p[0] = (unsigned char)v; p[1] = (unsigned char)(v >> 8);
    p[2] = (unsigned char)(v >> 16); p[3] = (unsigned char)(v >> 24);
}

static void setup_registry(void)
{
    size_t i = 0, used = 0, chunk;

    memset(entries, 0, sizeof(entries));
    /* Mirror the real registry's shape: a few scalars, the blocks, then many
     * small scalars, with the history indices and the doubled t_message_list
     * entry in the middle as the original has them. */
    entries[i].buf = scalars; entries[i].size = 16; i++; used += 16;
    entries[i].buf = t_army_list; entries[i].size = C2_SAVE_ARMIES_SIZE; i++;
    entries[i].buf = t_citizen_list; entries[i].size = (int)sizeof(t_citizen_list); i++;
    entries[i].buf = t_unit_list; entries[i].size = C2_SAVE_UNITS_SIZE; i++;
    entries[i].buf = t_figure_list; entries[i].size = C2_SAVE_FIGURES_SIZE; i++;
    entries[i].buf = t_arrow_list; entries[i].size = C2_SAVE_ARROWS_SIZE; i++;
    entries[i].buf = t_army_routes; entries[i].size = C2_SAVE_ARMYROUT_SIZE; i++;
    entries[i].buf = t_city_map; entries[i].size = C2_SAVE_CITYMAP_SIZE; i++;
    entries[i].buf = t_region_map; entries[i].size = C2_SAVE_REGIONMP_SIZE; i++;
    entries[i].buf = t_fire_zones; entries[i].size = C2_SAVE_FIREZONE_SIZE; i++;
    entries[i].buf = t_slave_requirements; entries[i].size = C2_SAVE_SLAVEREQ_SIZE; i++;
    entries[i].buf = t_message_list; entries[i].size = 64; i++;           /* partial alias, as the original */
    entries[i].buf = t_battle_map; entries[i].size = C2_SAVE_BATTLEMP_SIZE; i++;
    entries[i].buf = &t_history_end_ptr; entries[i].size = 4; i++;
    entries[i].buf = &t_history_start_ptr; entries[i].size = 4; i++;
    entries[i].buf = &t_history_entries; entries[i].size = 4; i++;
    entries[i].buf = t_industry; entries[i].size = C2_SAVE_INDUSTRY_SIZE; i++;
    entries[i].buf = t_message_list; entries[i].size = 128; i++;
    /* remaining scalars in 4-byte entries, then a 1-byte tail */
    while (used < SCALAR_BYTES && i < C2_SAVE_REGISTRY_CAPACITY - 1) {
        chunk = SCALAR_BYTES - used;
        if (chunk > 4) chunk = 4;
        if (i == C2_SAVE_REGISTRY_CAPACITY - 2) chunk = SCALAR_BYTES - used;   /* absorb the rest */
        entries[i].buf = scalars + used; entries[i].size = (int)chunk; i++; used += chunk;
    }
    TEST_ASSERT_EQUAL_size_t(SCALAR_BYTES, used);

    memset(&blocks, 0, sizeof(blocks));
    blocks.city_map = t_city_map; blocks.region_map = t_region_map; blocks.battle_map = t_battle_map;
    blocks.citizen_list = t_citizen_list; blocks.army_list = t_army_list; blocks.army_routes = t_army_routes;
    blocks.unit_list = t_unit_list; blocks.figure_list = t_figure_list; blocks.arrow_list = t_arrow_list;
    blocks.message_list = t_message_list; blocks.fire_zones = t_fire_zones; blocks.industry = t_industry;
    blocks.slave_requirements = t_slave_requirements;
    blocks.history_end_ptr = &t_history_end_ptr; blocks.history_start_ptr = &t_history_start_ptr;
    blocks.history_entries = &t_history_entries;
}

static void fill_pattern(unsigned char *p, size_t n, unsigned seed)
{
    size_t i;
    for (i = 0; i < n; i++) p[i] = (unsigned char)((seed * 31u + i * 7u) & 0xff);
}

/* A plausible image: every block patterned, live walkers on valid cells,
 * markets with envoys, armies with legal cohorts, history samples. */
static void build_image(struct c2_save_image *image, uint32_t live_walkers)
{
    uint32_t i;

    TEST_ASSERT_TRUE(c2_save_image_init(image, SCALAR_BYTES, POOL_SLOTS));
    fill_pattern(image->scalars, image->scalars_size, 1);
    fill_pattern(image->city_map, sizeof(image->city_map), 2);
    fill_pattern(image->region_map, sizeof(image->region_map), 3);
    fill_pattern(image->battle_map, sizeof(image->battle_map), 4);
    fill_pattern(image->army_list, sizeof(image->army_list), 5);
    fill_pattern(image->army_routes, sizeof(image->army_routes), 6);
    fill_pattern(image->unit_list, sizeof(image->unit_list), 7);
    fill_pattern(image->figures, sizeof(image->figures), 8);
    fill_pattern(image->arrows, sizeof(image->arrows), 9);
    fill_pattern(image->messages, sizeof(image->messages), 10);
    fill_pattern(image->fire_zones, sizeof(image->fire_zones), 11);
    fill_pattern(image->industry, sizeof(image->industry), 12);
    fill_pattern(image->slave_requirements, sizeof(image->slave_requirements), 13);
    for (i = 0; i < C2_SAVE_FIGURE_COUNT; i++) image->figure_secondary[i] = (i % 3) == 0;

    /* Cells: base_kind pattern, with every 50th cell a market (0xfc) that
     * has an envoy, and the second byte kept below the wall bits. */
    for (i = 0; i < C2_SAVE_CITY_CELLS; i++) {
        unsigned char *cell = image->city_map + i * C2_SAVE_CITY_CELL_SIZE;
        cell[0] = (i % 50 == 0) ? 0xfc : (unsigned char)(0x82 + i % 20);
        image->envoys[i] = (i % 50 == 0) ? (uint16_t)(1 + i % (live_walkers ? live_walkers : 1)) : 0;
    }
    /* Walkers 1..live_walkers exist and stand on distinct valid cells. */
    memset(image->citizens, 0, (size_t)POOL_SLOTS * C2_SAVE_CITIZEN_STRIDE);
    for (i = 1; i <= live_walkers && i < POOL_SLOTS; i++) {
        unsigned char *rec = image->citizens + (size_t)i * C2_SAVE_CITIZEN_STRIDE;
        rec[0] = 1;
        rec[2] = (unsigned char)(1 + i % 7);
        put32(rec + 6, (int32_t)((i * 3) % C2_SAVE_CITY_CELLS) * 20);
        put32(rec + 0x28, (int32_t)((i * 5) % C2_SAVE_CITY_CELLS) * 20);
        rec[C2_SAVE_CITIZEN_RECORD] = (unsigned char)((i + 1) % 256);
        rec[C2_SAVE_CITIZEN_RECORD + 1] = (unsigned char)(((i + 1) / 256) & 0x03);
        rec[0x2e] = (unsigned char)i; rec[0x32] = (unsigned char)(i % 32);
    }
    /* Armies: mark the first three live with legal cohorts. */
    for (i = 0; i < 26; i++) {
        unsigned char *rec = image->army_list + i * C2_SAVE_ARMY_RECORD;
        rec[0] = i < 3; rec[0x28] = (unsigned char)(i % 10);
    }
    for (i = 0; i < 10; i++) put32(image->army_routes + i * C2_SAVE_ROUTE_RECORD + 8, (int32_t)(i % 26));

    image->history_count = 37;
    for (i = 0; i < 37 * C2_SAVE_HISTORY_FIELDS; i++) image->history[i] = (int32_t)(i * 101 - 50);
    TEST_ASSERT_EQUAL_INT(C2_SAVE_OK, c2_save_validate(image, POOL_SLOTS));
}

static void test_round_trip_is_lossless_including_wide_walkers(void)
{
    struct c2_save_image before, after;
    unsigned char *data;
    size_t size;

    build_image(&before, 700);                       /* far beyond the byte ceiling of 254 */
    size = c2_save_encode(&before, "test", &data);
    TEST_ASSERT_TRUE(size > 0);
    TEST_ASSERT_EQUAL_INT(1, c2_save_detect(data, size));

    TEST_ASSERT_TRUE(c2_save_image_init(&after, SCALAR_BYTES, POOL_SLOTS));
    TEST_ASSERT_EQUAL_INT(C2_SAVE_OK, c2_save_decode(data, size, entries, C2_SAVE_REGISTRY_CAPACITY, &blocks, &after));
    TEST_ASSERT_EQUAL_UINT32(C2_SAVE_FORMAT_VERSION, after.format_version);
    TEST_ASSERT_NULL(c2_save_image_diff(&before, &after));
    TEST_ASSERT_EQUAL_UINT(0, after.cleared);
    TEST_ASSERT_EQUAL_UINT(0, after.dropped_citizens);
    /* the wide target of walker 600 survived (it is 601, above a byte) */
    TEST_ASSERT_EQUAL_UINT(601 & 0xff, after.citizens[600 * C2_SAVE_CITIZEN_STRIDE + C2_SAVE_CITIZEN_RECORD]);
    TEST_ASSERT_EQUAL_UINT(601 >> 8, after.citizens[600 * C2_SAVE_CITIZEN_STRIDE + C2_SAVE_CITIZEN_RECORD + 1]);

    free(data);
    c2_save_image_free(&before);
    c2_save_image_free(&after);
}

static void test_smaller_pool_drops_the_tail_and_reports_it(void)
{
    struct c2_save_image big, small;
    unsigned char *data;
    size_t size;

    build_image(&big, 700);
    size = c2_save_encode(&big, NULL, &data);
    TEST_ASSERT_TRUE(size > 0);
    TEST_ASSERT_TRUE(c2_save_image_init(&small, SCALAR_BYTES, 201));
    TEST_ASSERT_EQUAL_INT(C2_SAVE_OK, c2_save_decode(data, size, entries, C2_SAVE_REGISTRY_CAPACITY, &blocks, &small));
    TEST_ASSERT_EQUAL_UINT(500, small.dropped_citizens);
    /* references to dropped walkers were cleared, not left dangling */
    TEST_ASSERT_TRUE(small.cleared > 0);
    free(data);
    c2_save_image_free(&big);
    c2_save_image_free(&small);
}

/* Build a legacy 225,745-byte file from the synthetic globals. */
static unsigned char *build_legacy(size_t *size)
{
    unsigned char *file = (unsigned char *)calloc(C2_SAVE_FILE_SIZE, 1);
    size_t i, off = 0;
    int slot;

    fill_pattern(scalars, sizeof(scalars), 21);
    fill_pattern(t_city_map, sizeof(t_city_map), 22);
    fill_pattern(t_region_map, sizeof(t_region_map), 23);
    fill_pattern(t_battle_map, sizeof(t_battle_map), 24);
    fill_pattern(t_army_list, sizeof(t_army_list), 25);
    fill_pattern(t_army_routes, sizeof(t_army_routes), 26);
    fill_pattern(t_unit_list, sizeof(t_unit_list), 27);
    fill_pattern(t_message_list, sizeof(t_message_list), 28);
    fill_pattern(t_fire_zones, sizeof(t_fire_zones), 29);
    fill_pattern(t_industry, sizeof(t_industry), 30);
    fill_pattern(t_slave_requirements, sizeof(t_slave_requirements), 31);
    memset(t_citizen_list, 0, sizeof(t_citizen_list));
    for (i = 1; i < 150; i++) {
        unsigned char *rec = t_citizen_list + i * C2_SAVE_CITIZEN_RECORD;
        rec[0] = 1; put32(rec + 6, (int32_t)(i * 40)); put32(rec + 0x28, 0); rec[0x2c] = (unsigned char)(i + 1);
    }
    for (i = 0; i < C2_SAVE_CITY_CELLS; i++) {
        t_city_map[i * 20] = (i % 50 == 0) ? 0xfa : 0x10;
        t_city_map[i * 20 + 7] = 9; t_city_map[i * 20 + 8] = 9;         /* stale occupancy the import must drop */
        t_city_map[i * 20 + 0x12] = (i % 50 == 0) ? (unsigned char)(1 + i % 100) : 0x55;
    }
    for (i = 0; i < 26; i++) { t_army_list[i * C2_SAVE_ARMY_RECORD] = i < 2; t_army_list[i * C2_SAVE_ARMY_RECORD + 0x28] = 3; }
    for (i = 0; i < 10; i++) put32(t_army_routes + i * C2_SAVE_ROUTE_RECORD + 8, 4);
    /* legacy figure/arrow disk records: pointer markers 0/1 at their offsets */
    memset(t_figure_list, 0, sizeof(t_figure_list));
    memset(t_arrow_list, 0, sizeof(t_arrow_list));
    t_history_entries = 12; t_history_end_ptr = 5; t_history_start_ptr = 0;   /* wrapped ring */

    for (i = 0; i < C2_SAVE_REGISTRY_CAPACITY && entries[i].size != 0; i++) {
        const struct save_entry *e = &entries[i];
        if (e->buf == t_figure_list) {
            size_t k;
            for (k = 0; k < C2_SAVE_FIGURE_COUNT; k++) {
                unsigned char *d = file + off + k * C2_SAVE_FIGURE_SIZE;
                fill_pattern(d, C2_SAVE_FIGURE_SIZE, (unsigned)(40 + k));
                d[0x0a] = 1; d[0x0b] = d[0x0c] = d[0x0d] = 0;
                d[0x0e] = (k % 4 == 0); d[0x0f] = d[0x10] = d[0x11] = 0;
            }
        } else if (e->buf == t_arrow_list) {
            size_t k;
            for (k = 0; k < C2_SAVE_ARROW_COUNT; k++) {
                unsigned char *d = file + off + k * C2_SAVE_ARROW_SIZE;
                fill_pattern(d, C2_SAVE_ARROW_SIZE, (unsigned)(60 + k));
                d[8] = 1; d[9] = d[10] = d[11] = 0;
            }
        } else {
            memcpy(file + off, e->buf, (size_t)e->size);
        }
        off += (size_t)e->size;
    }
    TEST_ASSERT_EQUAL_size_t(C2_SAVE_STATE_SIZE, off);
    /* ring: 200 slots x 5 ints; samples for the last 12 months ending at slot 4 */
    for (slot = 0; slot < 200; slot++) {
        int k;
        for (k = 0; k < 5; k++) put32(file + off + (size_t)(slot * 5 + k) * 4, slot * 10 + k);
    }
    *size = C2_SAVE_FILE_SIZE;
    return file;
}

static void test_legacy_import_translates_and_normalises(void)
{
    struct c2_save_image image;
    unsigned char *file;
    size_t size;
    int s;

    file = build_legacy(&size);
    TEST_ASSERT_EQUAL_INT(0, c2_save_detect(file, size));
    TEST_ASSERT_TRUE(c2_save_image_init(&image, SCALAR_BYTES, POOL_SLOTS));
    TEST_ASSERT_EQUAL_INT(C2_SAVE_OK, c2_save_import_legacy(file, size, entries, C2_SAVE_REGISTRY_CAPACITY, &blocks, &image));
    TEST_ASSERT_EQUAL_UINT32(0, image.format_version);

    /* scalars in registry order, blocks intact */
    TEST_ASSERT_EQUAL_MEMORY(scalars, image.scalars, SCALAR_BYTES);
    TEST_ASSERT_EQUAL_MEMORY(t_region_map, image.region_map, sizeof(t_region_map));
    TEST_ASSERT_EQUAL_MEMORY(t_industry, image.industry, sizeof(t_industry));
    TEST_ASSERT_EQUAL_MEMORY(t_message_list, image.messages, sizeof(t_message_list));

    /* derived occupancy dropped; envoy lifted out of the cell byte */
    TEST_ASSERT_EQUAL_UINT8(0, image.city_map[7]);
    TEST_ASSERT_EQUAL_UINT8(0, image.city_map[8]);
    TEST_ASSERT_EQUAL_UINT8(0, image.city_map[0x12]);            /* cell 0 is a business */
    TEST_ASSERT_EQUAL_UINT16(1, image.envoys[0]);
    TEST_ASSERT_EQUAL_UINT8(0x55, image.city_map[20 + 0x12]);    /* cell 1 is not: byte kept */
    TEST_ASSERT_EQUAL_UINT16(0, image.envoys[1]);

    /* narrow target widened */
    TEST_ASSERT_EQUAL_UINT(43, image.citizens[42 * C2_SAVE_CITIZEN_STRIDE + C2_SAVE_CITIZEN_RECORD]);
    TEST_ASSERT_EQUAL_UINT(0, image.citizens[42 * C2_SAVE_CITIZEN_STRIDE + 0x2c]);

    /* pointer markers gone, the one bit kept */
    TEST_ASSERT_EQUAL_UINT8(1, image.figure_secondary[0]);
    TEST_ASSERT_EQUAL_UINT8(0, image.figure_secondary[1]);
    TEST_ASSERT_EQUAL_UINT8(1, image.figure_secondary[4]);

    /* history linearised oldest-first across the wrap: slots 193..199,0..4 */
    TEST_ASSERT_EQUAL_UINT32(12, image.history_count);
    for (s = 0; s < 12; s++) {
        int slot = (193 + s) % 200;
        TEST_ASSERT_EQUAL_INT32(slot * 10, image.history[s * 5]);
        TEST_ASSERT_EQUAL_INT32(slot * 10 + 4, image.history[s * 5 + 4]);
    }

    free(file);
    c2_save_image_free(&image);
}

static void test_import_then_save_then_load_is_idempotent(void)
{
    struct c2_save_image imported, reloaded;
    unsigned char *file, *data;
    size_t size, n;

    file = build_legacy(&size);
    TEST_ASSERT_TRUE(c2_save_image_init(&imported, SCALAR_BYTES, POOL_SLOTS));
    TEST_ASSERT_EQUAL_INT(C2_SAVE_OK, c2_save_import_legacy(file, size, entries, C2_SAVE_REGISTRY_CAPACITY, &blocks, &imported));
    n = c2_save_encode(&imported, "x", &data);
    TEST_ASSERT_TRUE(n > 0);
    TEST_ASSERT_TRUE(c2_save_image_init(&reloaded, SCALAR_BYTES, POOL_SLOTS));
    TEST_ASSERT_EQUAL_INT(C2_SAVE_OK, c2_save_decode(data, n, entries, C2_SAVE_REGISTRY_CAPACITY, &blocks, &reloaded));
    TEST_ASSERT_NULL(c2_save_image_diff(&imported, &reloaded));
    free(file); free(data);
    c2_save_image_free(&imported); c2_save_image_free(&reloaded);
}

static void expect_decode(const unsigned char *data, size_t size, enum c2_save_status expected)
{
    struct c2_save_image image;

    TEST_ASSERT_TRUE(c2_save_image_init(&image, SCALAR_BYTES, POOL_SLOTS));
    TEST_ASSERT_EQUAL_INT(expected, c2_save_decode(data, size, entries, C2_SAVE_REGISTRY_CAPACITY, &blocks, &image));
    c2_save_image_free(&image);
}

static void test_negative_corpus(void)
{
    struct c2_save_image image;
    unsigned char *data, *copy;
    size_t size;

    build_image(&image, 50);
    size = c2_save_encode(&image, NULL, &data);
    TEST_ASSERT_TRUE(size > 0);
    copy = (unsigned char *)malloc(size);

    /* truncation: header is fine, buffer is not */
    expect_decode(data, size - 100, C2_SAVE_ERR_CRC);
    /* a flipped bit deep inside a grid */
    memcpy(copy, data, size); copy[size / 2] ^= 0x40;
    expect_decode(copy, size, C2_SAVE_ERR_CRC);
    /* trailer says ok but the container is damaged: forge the CRC */
    memcpy(copy, data, size); copy[8] ^= 0xff;                    /* root offset area */
    {
        /* recompute the trailer so only the verifier can catch it */
        unsigned long c = crc32(crc32(0L, Z_NULL, 0), copy, (uInt)(size - 4));
        copy[size - 4] = (unsigned char)c; copy[size - 3] = (unsigned char)(c >> 8);
        copy[size - 2] = (unsigned char)(c >> 16); copy[size - 1] = (unsigned char)(c >> 24);
    }
    expect_decode(copy, size, C2_SAVE_ERR_VERIFY);
    /* wrong identifier */
    memcpy(copy, data, size); copy[4] = 'X';
    expect_decode(copy, size, C2_SAVE_ERR_FORMAT);
    /* not a save at all */
    expect_decode((const unsigned char *)"hello", 5, C2_SAVE_ERR_FORMAT);
    TEST_ASSERT_EQUAL_INT(-1, c2_save_detect((const unsigned char *)"hello", 5));

    free(copy); free(data);
    c2_save_image_free(&image);
}

static void test_validation_rejects_and_clears(void)
{
    struct c2_save_image image;

    build_image(&image, 20);
    /* reject: a live army whose cohort indexes past the ten routes */
    image.army_list[0x28] = 100;
    TEST_ASSERT_EQUAL_INT(C2_SAVE_ERR_VALIDATION, c2_save_validate(&image, POOL_SLOTS));
    image.army_list[0x28] = 3;
    /* reject: a live walker standing off the map */
    put32(image.citizens + 5 * C2_SAVE_CITIZEN_STRIDE + 6, 128000);
    TEST_ASSERT_EQUAL_INT(C2_SAVE_ERR_VALIDATION, c2_save_validate(&image, POOL_SLOTS));
    put32(image.citizens + 5 * C2_SAVE_CITIZEN_STRIDE + 6, 40);
    /* reject: slot 0 occupied */
    image.citizens[0] = 1;
    TEST_ASSERT_EQUAL_INT(C2_SAVE_ERR_VALIDATION, c2_save_validate(&image, POOL_SLOTS));
    image.citizens[0] = 0;
    /* clear: misaligned action target, chase target beyond the pool, envoy beyond the pool */
    put32(image.citizens + 5 * C2_SAVE_CITIZEN_STRIDE + 0x28, 41);
    image.citizens[6 * C2_SAVE_CITIZEN_STRIDE + C2_SAVE_CITIZEN_RECORD + 1] = 0xff;
    image.envoys[0] = 5000;
    image.cleared = 0;
    TEST_ASSERT_EQUAL_INT(C2_SAVE_OK, c2_save_validate(&image, POOL_SLOTS));
    TEST_ASSERT_EQUAL_UINT(3, image.cleared);
    TEST_ASSERT_EQUAL_UINT16(0, image.envoys[0]);
    c2_save_image_free(&image);
}

static void test_newer_version_is_refused(void)
{
    /* Build a minimal root claiming a future version straight from the
     * generated builder, as a newer writer would. */
    flatcc_builder_t b;
    unsigned char *buf, *file;
    size_t size;
    unsigned long c;

    flatcc_builder_init(&b);
    c2_save_Save_start_as_root(&b);
    c2_save_Save_format_version_add(&b, C2_SAVE_FORMAT_VERSION + 1);
    c2_save_Save_end_as_root(&b);
    buf = (unsigned char *)flatcc_builder_finalize_aligned_buffer(&b, &size);
    flatcc_builder_clear(&b);
    TEST_ASSERT_NOT_NULL(buf);
    file = (unsigned char *)malloc(size + 4);
    memcpy(file, buf, size);
    c = crc32(crc32(0L, Z_NULL, 0), buf, (uInt)size);
    file[size] = (unsigned char)c; file[size + 1] = (unsigned char)(c >> 8);
    file[size + 2] = (unsigned char)(c >> 16); file[size + 3] = (unsigned char)(c >> 24);
    expect_decode(file, size + 4, C2_SAVE_ERR_VERSION);
    flatcc_builder_aligned_free(buf);
    free(file);
}

int main(void)
{
    UNITY_BEGIN();
    setup_registry();
    RUN_TEST(test_round_trip_is_lossless_including_wide_walkers);
    RUN_TEST(test_smaller_pool_drops_the_tail_and_reports_it);
    RUN_TEST(test_legacy_import_translates_and_normalises);
    RUN_TEST(test_import_then_save_then_load_is_idempotent);
    RUN_TEST(test_negative_corpus);
    RUN_TEST(test_validation_rejects_and_clears);
    RUN_TEST(test_newer_version_is_refused);
    return UNITY_END();
}
