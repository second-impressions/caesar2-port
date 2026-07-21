#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <unity/unity.h>

#include "c2_port_save.h"
#include "c2_save_compat.h"

static void test_full_500_entry_registry_is_valid(void)
{
    struct save_entry entries[500];
    struct figure_rec figures[1];
    struct arrow_rec arrows[1];
    unsigned char ordinary_block;
    size_t remaining_size;
    size_t i;

    memset(entries, 0, sizeof(entries));
    for (i = 0; i < 500; i++) {
        entries[i].buf = &ordinary_block;
        entries[i].size = 1;
    }
    entries[10].buf = figures;
    entries[10].size = C2_SAVE_FIGURES_SIZE;
    entries[11].buf = arrows;
    entries[11].size = C2_SAVE_ARROWS_SIZE;
    remaining_size = C2_SAVE_STATE_SIZE - C2_SAVE_FIGURES_SIZE -
                     C2_SAVE_ARROWS_SIZE - 497;
    entries[0].size = (int)remaining_size;

    TEST_ASSERT_TRUE(c2_port_save_registry_valid(entries, 500,
                                                  figures, arrows));
    entries[499].size = 0;
    TEST_ASSERT_FALSE(c2_port_save_registry_valid(entries, 500,
                                                   figures, arrows));
    entries[499].size = 1;
    entries[10].size--;
    TEST_ASSERT_FALSE(c2_port_save_registry_valid(entries, 500,
                                                   figures, arrows));
}

static void test_figure_records_round_trip_without_native_pointers(void)
{
    struct figure_rec *source;
    struct figure_rec *decoded;
    unsigned char *first_encoding;
    unsigned char *second_encoding;
    size_t tail_offset;

    source = calloc(C2_SAVE_FIGURE_COUNT, sizeof(*source));
    decoded = calloc(C2_SAVE_FIGURE_COUNT, sizeof(*decoded));
    first_encoding = malloc(C2_SAVE_FIGURES_SIZE);
    second_encoding = malloc(C2_SAVE_FIGURES_SIZE);
    TEST_ASSERT_NOT_NULL(source);
    TEST_ASSERT_NOT_NULL(decoded);
    TEST_ASSERT_NOT_NULL(first_encoding);
    TEST_ASSERT_NOT_NULL(second_encoding);

    memset(&source[0], 0x5a, sizeof(source[0]));
    source[0].arrow_data_ptr = (unsigned char *)(uintptr_t)0x12345678;
    source[0].sprite_data_ptr = NULL;
    source[1].arrow_data_ptr = NULL;
    source[1].sprite_data_ptr = (unsigned char *)(uintptr_t)0x87654321;

    c2_save_pack_figures(first_encoding, source);
    TEST_ASSERT_EQUAL_UINT8(1, first_encoding[0x0a]);
    TEST_ASSERT_EQUAL_UINT8(0, first_encoding[0x0e]);
    TEST_ASSERT_EQUAL_UINT8(0,
        first_encoding[C2_SAVE_FIGURE_SIZE + 0x0a]);
    TEST_ASSERT_EQUAL_UINT8(1,
        first_encoding[C2_SAVE_FIGURE_SIZE + 0x0e]);

    c2_save_unpack_figures(decoded, first_encoding);
    TEST_ASSERT_EQUAL_PTR((void *)(uintptr_t)1, decoded[0].arrow_data_ptr);
    TEST_ASSERT_NULL(decoded[0].sprite_data_ptr);
    TEST_ASSERT_NULL(decoded[1].arrow_data_ptr);
    TEST_ASSERT_EQUAL_PTR((void *)(uintptr_t)1, decoded[1].sprite_data_ptr);
    TEST_ASSERT_EQUAL_MEMORY(&source[0], &decoded[0], 0x0a);
    tail_offset = offsetof(struct figure_rec, map_ref);
    TEST_ASSERT_EQUAL_MEMORY((unsigned char *)&source[0] + tail_offset,
                             (unsigned char *)&decoded[0] + tail_offset,
                             sizeof(source[0]) - tail_offset);

    c2_save_pack_figures(second_encoding, decoded);
    TEST_ASSERT_EQUAL_MEMORY(first_encoding, second_encoding,
                             C2_SAVE_FIGURES_SIZE);

    free(second_encoding);
    free(first_encoding);
    free(decoded);
    free(source);
}

static void test_arrow_records_round_trip_without_native_pointers(void)
{
    struct arrow_rec *source;
    struct arrow_rec *decoded;
    unsigned char *first_encoding;
    unsigned char *second_encoding;
    size_t tail_offset;

    source = calloc(C2_SAVE_ARROW_COUNT, sizeof(*source));
    decoded = calloc(C2_SAVE_ARROW_COUNT, sizeof(*decoded));
    first_encoding = malloc(C2_SAVE_ARROWS_SIZE);
    second_encoding = malloc(C2_SAVE_ARROWS_SIZE);
    TEST_ASSERT_NOT_NULL(source);
    TEST_ASSERT_NOT_NULL(decoded);
    TEST_ASSERT_NOT_NULL(first_encoding);
    TEST_ASSERT_NOT_NULL(second_encoding);

    memset(&source[0], 0xa5, sizeof(source[0]));
    source[0].arrow_data_ptr = (unsigned char *)(uintptr_t)0x12345678;

    c2_save_pack_arrows(first_encoding, source);
    TEST_ASSERT_EQUAL_UINT8(1, first_encoding[0x08]);
    c2_save_unpack_arrows(decoded, first_encoding);
    TEST_ASSERT_EQUAL_PTR((void *)(uintptr_t)1, decoded[0].arrow_data_ptr);
    TEST_ASSERT_EQUAL_MEMORY(&source[0], &decoded[0], 0x08);
    tail_offset = offsetof(struct arrow_rec, grid_x);
    TEST_ASSERT_EQUAL_MEMORY((unsigned char *)&source[0] + tail_offset,
                             (unsigned char *)&decoded[0] + tail_offset,
                             sizeof(source[0]) - tail_offset);

    c2_save_pack_arrows(second_encoding, decoded);
    TEST_ASSERT_EQUAL_MEMORY(first_encoding, second_encoding,
                             C2_SAVE_ARROWS_SIZE);

    free(second_encoding);
    free(first_encoding);
    free(decoded);
    free(source);
}

static int disk_pointer_is_nonzero(const unsigned char *pointer_bytes)
{
    return (pointer_bytes[0] | pointer_bytes[1] |
            pointer_bytes[2] | pointer_bytes[3]) != 0;
}

static void normalize_disk_pointer(unsigned char *pointer_bytes)
{
    pointer_bytes[0] = disk_pointer_is_nonzero(pointer_bytes) ? 1 : 0;
    pointer_bytes[1] = 0;
    pointer_bytes[2] = 0;
    pointer_bytes[3] = 0;
}

static void test_original_save_fixture_records(void)
{
    const char *fixture_path;
    FILE *fixture;
    struct figure_rec *figures;
    struct arrow_rec *arrows;
    unsigned char *disk_figures;
    unsigned char *disk_arrows;
    unsigned char *expected_figures;
    unsigned char *expected_arrows;
    long file_size;
    size_t i;

    fixture_path = getenv("C2_TEST_SAVE_FIXTURE");
    if (fixture_path == NULL || fixture_path[0] == '\0') {
        TEST_IGNORE_MESSAGE("C2_TEST_SAVE_FIXTURE is not configured");
    }
    fixture = fopen(fixture_path, "rb");
    TEST_ASSERT_NOT_NULL(fixture);
    TEST_ASSERT_EQUAL_INT(0, fseek(fixture, 0, SEEK_END));
    file_size = ftell(fixture);
    TEST_ASSERT_EQUAL_INT(C2_SAVE_FILE_SIZE, file_size);
    TEST_ASSERT_EQUAL_INT(0, fseek(fixture, C2_SAVE_FIGURES_OFFSET, SEEK_SET));

    figures = calloc(C2_SAVE_FIGURE_COUNT, sizeof(*figures));
    arrows = calloc(C2_SAVE_ARROW_COUNT, sizeof(*arrows));
    disk_figures = malloc(C2_SAVE_FIGURES_SIZE);
    disk_arrows = malloc(C2_SAVE_ARROWS_SIZE);
    expected_figures = malloc(C2_SAVE_FIGURES_SIZE);
    expected_arrows = malloc(C2_SAVE_ARROWS_SIZE);
    TEST_ASSERT_NOT_NULL(figures);
    TEST_ASSERT_NOT_NULL(arrows);
    TEST_ASSERT_NOT_NULL(disk_figures);
    TEST_ASSERT_NOT_NULL(disk_arrows);
    TEST_ASSERT_NOT_NULL(expected_figures);
    TEST_ASSERT_NOT_NULL(expected_arrows);
    TEST_ASSERT_EQUAL_size_t(C2_SAVE_FIGURES_SIZE,
        fread(expected_figures, 1, C2_SAVE_FIGURES_SIZE, fixture));
    TEST_ASSERT_EQUAL_size_t(C2_SAVE_ARROWS_SIZE,
        fread(expected_arrows, 1, C2_SAVE_ARROWS_SIZE, fixture));
    fclose(fixture);

    c2_save_unpack_figures(figures, expected_figures);
    c2_save_unpack_arrows(arrows, expected_arrows);
    c2_save_pack_figures(disk_figures, figures);
    c2_save_pack_arrows(disk_arrows, arrows);
    for (i = 0; i < C2_SAVE_FIGURE_COUNT; i++) {
        normalize_disk_pointer(expected_figures +
                               i * C2_SAVE_FIGURE_SIZE + 0x0a);
        normalize_disk_pointer(expected_figures +
                               i * C2_SAVE_FIGURE_SIZE + 0x0e);
    }
    for (i = 0; i < C2_SAVE_ARROW_COUNT; i++) {
        normalize_disk_pointer(expected_arrows +
                               i * C2_SAVE_ARROW_SIZE + 0x08);
    }
    TEST_ASSERT_EQUAL_MEMORY(expected_figures, disk_figures,
                             C2_SAVE_FIGURES_SIZE);
    TEST_ASSERT_EQUAL_MEMORY(expected_arrows, disk_arrows,
                             C2_SAVE_ARROWS_SIZE);

    free(expected_arrows);
    free(expected_figures);
    free(disk_arrows);
    free(disk_figures);
    free(arrows);
    free(figures);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_full_500_entry_registry_is_valid);
    RUN_TEST(test_figure_records_round_trip_without_native_pointers);
    RUN_TEST(test_arrow_records_round_trip_without_native_pointers);
    RUN_TEST(test_original_save_fixture_records);
    return UNITY_END();
}
