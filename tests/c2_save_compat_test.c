/*
 * Original-layout (version 0) guards: the registry must describe exactly
 * the original state size, and an original file is recognised as such. The
 * translation of that layout into the port's format is tested with
 * synthetic state in c2_port_save_test.c and against a real file by the
 * recovered-engine smoke.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <unity/unity.h>

#include "c2_port_save.h"
#include "c2_save_compat.h"
#include "c2_save_v1.h"

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

static void test_legacy_constants_agree(void)
{
    TEST_ASSERT_EQUAL_UINT(C2_SAVE_FILE_SIZE, C2_SAVE_LEGACY_FILE_SIZE);
    TEST_ASSERT_EQUAL_UINT(C2_SAVE_STATE_SIZE, C2_SAVE_LEGACY_STATE_SIZE);
    TEST_ASSERT_EQUAL_UINT(C2_SAVE_HISTORY_SIZE, C2_SAVE_LEGACY_HISTORY_SIZE);
    TEST_ASSERT_EQUAL_UINT(C2_SAVE_FIGURE_SIZE, C2_SAVE_LEGACY_FIGURE_RECORD);
    TEST_ASSERT_EQUAL_UINT(C2_SAVE_ARROW_SIZE, C2_SAVE_LEGACY_ARROW_RECORD);
    /* the container's pointer-free records are the disk records minus the
     * native pointer bytes */
    TEST_ASSERT_EQUAL_UINT(C2_SAVE_FIGURE_SIZE - 8, C2_SAVE_FIGURE_RECORD);
    TEST_ASSERT_EQUAL_UINT(C2_SAVE_ARROW_SIZE - 4, C2_SAVE_ARROW_RECORD);
}

static void test_original_save_fixture_is_detected_as_legacy(void)
{
    const char *fixture_path;
    FILE *fixture;
    unsigned char *data;
    long file_size;

    fixture_path = getenv("C2_TEST_SAVE_FIXTURE");
    if (fixture_path == NULL || fixture_path[0] == '\0') {
        TEST_IGNORE_MESSAGE("C2_TEST_SAVE_FIXTURE is not configured");
    }
    fixture = fopen(fixture_path, "rb");
    TEST_ASSERT_NOT_NULL(fixture);
    TEST_ASSERT_EQUAL_INT(0, fseek(fixture, 0, SEEK_END));
    file_size = ftell(fixture);
    TEST_ASSERT_EQUAL_INT(C2_SAVE_FILE_SIZE, file_size);
    rewind(fixture);
    data = malloc((size_t)file_size);
    TEST_ASSERT_NOT_NULL(data);
    TEST_ASSERT_EQUAL_size_t((size_t)file_size, fread(data, 1, (size_t)file_size, fixture));
    fclose(fixture);
    TEST_ASSERT_EQUAL_INT(0, c2_save_detect(data, (size_t)file_size));
    free(data);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_full_500_entry_registry_is_valid);
    RUN_TEST(test_legacy_constants_agree);
    RUN_TEST(test_original_save_fixture_is_detected_as_legacy);
    return UNITY_END();
}
