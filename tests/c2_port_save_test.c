#include <stdint.h>
#include <string.h>

#include <SDL3/SDL.h>
#include <unity/unity.h>

#include "c2_host.h"
#include "c2_port_save.h"
#include "c2_save_compat.h"

#define TEST_USER_ROOT "c2-port-save-test-data"
#define ORDINARY_STATE_SIZE \
    (C2_SAVE_STATE_SIZE - C2_SAVE_FIGURES_SIZE - C2_SAVE_ARROWS_SIZE)
#define TRAILING_BLOCK_COUNT 497

static struct save_entry entries[500];
static struct figure_rec figures[C2_SAVE_FIGURE_COUNT];
static struct arrow_rec arrows[C2_SAVE_ARROW_COUNT];
static unsigned char ordinary_state[ORDINARY_STATE_SIZE];
static unsigned char expected_ordinary_state[ORDINARY_STATE_SIZE];
static unsigned char history[C2_SAVE_HISTORY_SIZE];
static unsigned char expected_history[C2_SAVE_HISTORY_SIZE];
static unsigned char expected_figures[C2_SAVE_FIGURES_SIZE];
static unsigned char expected_arrows[C2_SAVE_ARROWS_SIZE];
static unsigned char actual_figures[C2_SAVE_FIGURES_SIZE];
static unsigned char actual_arrows[C2_SAVE_ARROWS_SIZE];
static unsigned char saved_file[C2_SAVE_FILE_SIZE + 1];

static void remove_test_files(void)
{
    SDL_RemovePath(TEST_USER_ROOT "/history.dat");
    SDL_RemovePath(TEST_USER_ROOT "/roundtrip.sav");
    SDL_RemovePath(TEST_USER_ROOT "/truncated.sav");
    SDL_RemovePath(TEST_USER_ROOT "/oversized.sav");
    SDL_RemovePath(TEST_USER_ROOT);
}

static void setup_full_registry(void)
{
    size_t prefix_size;
    size_t i;

    memset(entries, 0, sizeof(entries));
    prefix_size = ORDINARY_STATE_SIZE - TRAILING_BLOCK_COUNT;
    entries[0].buf = ordinary_state;
    entries[0].size = (int)prefix_size;
    entries[1].buf = figures;
    entries[1].size = C2_SAVE_FIGURES_SIZE;
    entries[2].buf = arrows;
    entries[2].size = C2_SAVE_ARROWS_SIZE;
    for (i = 3; i < 500; i++) {
        entries[i].buf = ordinary_state + prefix_size + i - 3;
        entries[i].size = 1;
    }
}

static void test_portable_save_and_load_round_trip(void)
{
    struct c2_host_config config;
    size_t bytes_read;
    size_t mismatch_offset;
    size_t i;

    remove_test_files();
    memset(&config, 0, sizeof(config));
    config.title = "Caesar II save test";
    config.asset_root = ".";
    config.user_data_root = TEST_USER_ROOT;
    config.logical_width = 1;
    config.logical_height = 1;
    config.window_scale = 1;
    config.headless = 1;
    TEST_ASSERT_TRUE(c2_host_init(&config));

    setup_full_registry();
    for (i = 0; i < sizeof(ordinary_state); i++) {
        ordinary_state[i] = (unsigned char)(i * 17 + 3);
    }
    for (i = 0; i < sizeof(history); i++) {
        history[i] = (unsigned char)(i * 7 + 11);
    }
    memset(figures, 0, sizeof(figures));
    memset(arrows, 0, sizeof(arrows));
    figures[0].arrow_data_ptr = (unsigned char *)(uintptr_t)0x12345678;
    figures[0].map_ref = 0x3456;
    arrows[0].arrow_data_ptr = (unsigned char *)(uintptr_t)0x87654321;
    arrows[0].grid_x = 0x34;
    memcpy(expected_ordinary_state, ordinary_state, sizeof(ordinary_state));
    memcpy(expected_history, history, sizeof(history));
    c2_save_pack_figures(expected_figures, figures);
    c2_save_pack_arrows(expected_arrows, arrows);
    TEST_ASSERT_TRUE(c2_host_user_file_write("history.dat", history,
                                             sizeof(history)));

    TEST_ASSERT_TRUE(c2_port_save_game_state("roundtrip.sav", entries, 500,
                                             figures, arrows));
    bytes_read = c2_host_user_file_read("roundtrip.sav", saved_file,
                                        sizeof(saved_file), 0);
    TEST_ASSERT_EQUAL_size_t(C2_SAVE_FILE_SIZE, bytes_read);
    TEST_ASSERT_TRUE(c2_port_save_state_file_matches(
        "roundtrip.sav", entries, 500, figures, arrows, &mismatch_offset));

    ordinary_state[42] ^= 0xff;
    TEST_ASSERT_FALSE(c2_port_save_state_file_matches(
        "roundtrip.sav", entries, 500, figures, arrows, &mismatch_offset));
    TEST_ASSERT_EQUAL_size_t(42, mismatch_offset);
    ordinary_state[42] ^= 0xff;

    saved_file[123] ^= 0xff;
    TEST_ASSERT_TRUE(c2_host_user_file_write("roundtrip.sav", saved_file,
                                             C2_SAVE_FILE_SIZE));
    TEST_ASSERT_FALSE(c2_port_save_state_file_matches(
        "roundtrip.sav", entries, 500, figures, arrows, &mismatch_offset));
    TEST_ASSERT_EQUAL_size_t(123, mismatch_offset);
    saved_file[123] ^= 0xff;
    TEST_ASSERT_TRUE(c2_host_user_file_write("roundtrip.sav", saved_file,
                                             C2_SAVE_FILE_SIZE));

    memset(ordinary_state, 0, sizeof(ordinary_state));
    memset(figures, 0, sizeof(figures));
    memset(arrows, 0, sizeof(arrows));
    memset(history, 0, sizeof(history));
    TEST_ASSERT_TRUE(c2_host_user_file_write("history.dat", history,
                                             sizeof(history)));
    TEST_ASSERT_TRUE(c2_port_load_game_state("roundtrip.sav", entries, 500,
                                             figures, arrows));
    TEST_ASSERT_EQUAL_MEMORY(expected_ordinary_state, ordinary_state,
                             sizeof(ordinary_state));
    c2_save_pack_figures(actual_figures, figures);
    c2_save_pack_arrows(actual_arrows, arrows);
    TEST_ASSERT_EQUAL_MEMORY(expected_figures, actual_figures,
                             sizeof(expected_figures));
    TEST_ASSERT_EQUAL_MEMORY(expected_arrows, actual_arrows,
                             sizeof(expected_arrows));
    TEST_ASSERT_EQUAL_size_t(sizeof(history),
        c2_host_user_file_read("history.dat", history, sizeof(history), 0));
    TEST_ASSERT_EQUAL_MEMORY(expected_history, history, sizeof(history));
    TEST_ASSERT_TRUE(c2_port_save_state_file_matches(
        "roundtrip.sav", entries, 500, figures, arrows, &mismatch_offset));

    history[17] ^= 0xff;
    TEST_ASSERT_TRUE(c2_host_user_file_write("history.dat", history,
                                             sizeof(history)));
    TEST_ASSERT_FALSE(c2_port_save_state_file_matches(
        "roundtrip.sav", entries, 500, figures, arrows, &mismatch_offset));
    TEST_ASSERT_EQUAL_size_t(C2_SAVE_STATE_SIZE + 17, mismatch_offset);
    history[17] ^= 0xff;
    TEST_ASSERT_TRUE(c2_host_user_file_write("history.dat", history,
                                             sizeof(history)));

    TEST_ASSERT_TRUE(c2_host_user_file_write("truncated.sav", saved_file,
                                             C2_SAVE_FILE_SIZE - 1));
    ordinary_state[0] = 0x7b;
    TEST_ASSERT_FALSE(c2_port_load_game_state("truncated.sav", entries, 500,
                                              figures, arrows));
    TEST_ASSERT_EQUAL_HEX8(0x7b, ordinary_state[0]);
    saved_file[C2_SAVE_FILE_SIZE] = 0xa5;
    TEST_ASSERT_TRUE(c2_host_user_file_write("oversized.sav", saved_file,
                                             sizeof(saved_file)));
    TEST_ASSERT_FALSE(c2_port_load_game_state("oversized.sav", entries, 500,
                                              figures, arrows));
    TEST_ASSERT_EQUAL_HEX8(0x7b, ordinary_state[0]);

    c2_host_shutdown();
    remove_test_files();
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_portable_save_and_load_round_trip);
    return UNITY_END();
}
