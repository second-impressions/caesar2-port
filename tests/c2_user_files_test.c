#include <string.h>

#include <SDL3/SDL.h>
#include <unity/unity.h>

#include "c2_host.h"

#define TEST_USER_ROOT "c2-user-files-test-data"

static void remove_test_files(void)
{
    SDL_RemovePath(TEST_USER_ROOT "/Alpha.SAV");
    SDL_RemovePath(TEST_USER_ROOT "/beta.sAv");
    SDL_RemovePath(TEST_USER_ROOT "/notes.txt");
    SDL_RemovePath(TEST_USER_ROOT);
}

static void test_user_streams_and_dos_style_directory_listing(void)
{
    struct c2_host_config config;
    struct c2_host_user_stream *stream;
    char names[100][13];
    char buffer[8];
    size_t count;

    remove_test_files();
    memset(&config, 0, sizeof(config));
    config.title = "Caesar II filesystem test";
    config.asset_root = ".";
    config.user_data_root = TEST_USER_ROOT;
    config.logical_width = 1;
    config.logical_height = 1;
    config.window_scale = 1;
    config.headless = 1;
    TEST_ASSERT_TRUE(c2_host_init(&config));

    stream = c2_host_user_stream_open("Alpha.SAV",
                                      C2_HOST_USER_STREAM_WRITE);
    TEST_ASSERT_NOT_NULL(stream);
    TEST_ASSERT_EQUAL_size_t(3,
        c2_host_user_stream_write(stream, "abc", 3));
    TEST_ASSERT_EQUAL_size_t(3,
        c2_host_user_stream_write(stream, "def", 3));
    TEST_ASSERT_TRUE(c2_host_user_stream_close(stream));
    TEST_ASSERT_TRUE(c2_host_user_file_write("beta.sAv", "B", 1));
    TEST_ASSERT_TRUE(c2_host_user_file_write("notes.txt", "N", 1));

    TEST_ASSERT_TRUE(c2_host_user_file_exists("alpha.sav"));
    stream = c2_host_user_stream_open("ALPHA.SAV",
                                      C2_HOST_USER_STREAM_READ);
    TEST_ASSERT_NOT_NULL(stream);
    memset(buffer, 0, sizeof(buffer));
    TEST_ASSERT_EQUAL_size_t(6,
        c2_host_user_stream_read(stream, buffer, 6));
    TEST_ASSERT_EQUAL_STRING("abcdef", buffer);
    TEST_ASSERT_TRUE(c2_host_user_stream_close(stream));

    memset(names, 0, sizeof(names));
    count = c2_host_user_file_list("*.sav", (char *)names,
                                   sizeof(names[0]), 100);
    TEST_ASSERT_EQUAL_size_t(2, count);
    TEST_ASSERT_EQUAL_STRING("ALPHA.SAV", names[0]);
    TEST_ASSERT_EQUAL_STRING("BETA.SAV", names[1]);

    TEST_ASSERT_TRUE(c2_host_user_file_write("BETA.SAV", "new", 3));
    memset(buffer, 0, sizeof(buffer));
    TEST_ASSERT_EQUAL_size_t(3,
        c2_host_user_file_read("beta.sav", buffer, sizeof(buffer), 0));
    TEST_ASSERT_EQUAL_STRING("new", buffer);
    TEST_ASSERT_NULL(c2_host_user_stream_open("../bad.sav",
                                              C2_HOST_USER_STREAM_WRITE));

    c2_host_shutdown();
    remove_test_files();
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_user_streams_and_dos_style_directory_listing);
    return UNITY_END();
}
