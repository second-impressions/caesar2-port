#include <stdio.h>
#include <string.h>

#include <SDL3/SDL.h>
#include <unity/unity.h>

#include "c2_host.h"
#include "c2_sdl_host.h"

#define TEST_ASSET_ROOT "c2-asset-files-test-data"
#define TEST_USER_ROOT "c2-user-files-test-data"

static void remove_test_assets(void)
{
    SDL_RemovePath(TEST_ASSET_ROOT "/Shared.PL8");
    SDL_RemovePath(TEST_ASSET_ROOT "/Root.CaSe");
    SDL_RemovePath(TEST_ASSET_ROOT "/pl8/shared.pl8");
    SDL_RemovePath(TEST_ASSET_ROOT "/pl8/Tutorial.Pl8");
    SDL_RemovePath(TEST_ASSET_ROOT "/pl8/hidden.dat");
    SDL_RemovePath(TEST_ASSET_ROOT "/RaW/Voice.RAW");
    SDL_RemovePath(TEST_ASSET_ROOT "/XMI/Tune.Xmi");
    SDL_RemovePath(TEST_ASSET_ROOT "/sMk/Intro.SMK");
    SDL_RemovePath(TEST_ASSET_ROOT "/pl8");
    SDL_RemovePath(TEST_ASSET_ROOT "/RaW");
    SDL_RemovePath(TEST_ASSET_ROOT "/XMI");
    SDL_RemovePath(TEST_ASSET_ROOT "/sMk");
    SDL_RemovePath(TEST_ASSET_ROOT);
}

static void remove_test_files(void)
{
    SDL_RemovePath(TEST_USER_ROOT "/Alpha.SAV");
    SDL_RemovePath(TEST_USER_ROOT "/beta.sAv");
    SDL_RemovePath(TEST_USER_ROOT "/notes.txt");
    SDL_RemovePath(TEST_USER_ROOT "/screen.png");
    SDL_RemovePath(TEST_USER_ROOT);
}

static void write_test_asset(const char *filename, char value)
{
    FILE *file;

    file = fopen(filename, "wb");
    TEST_ASSERT_NOT_NULL(file);
    TEST_ASSERT_EQUAL_size_t(1, fwrite(&value, 1, 1, file));
    TEST_ASSERT_EQUAL_INT(0, fclose(file));
}

static void test_assets_use_install_then_cd_media_lookup(void)
{
    struct c2_host_config config;
    unsigned char byte;

    remove_test_assets();
    TEST_ASSERT_TRUE(SDL_CreateDirectory(TEST_ASSET_ROOT "/pl8"));
    TEST_ASSERT_TRUE(SDL_CreateDirectory(TEST_ASSET_ROOT "/RaW"));
    TEST_ASSERT_TRUE(SDL_CreateDirectory(TEST_ASSET_ROOT "/XMI"));
    TEST_ASSERT_TRUE(SDL_CreateDirectory(TEST_ASSET_ROOT "/sMk"));
    write_test_asset(TEST_ASSET_ROOT "/Shared.PL8", 'R');
    write_test_asset(TEST_ASSET_ROOT "/Root.CaSe", 'C');
    write_test_asset(TEST_ASSET_ROOT "/pl8/shared.pl8", 'M');
    write_test_asset(TEST_ASSET_ROOT "/pl8/Tutorial.Pl8", 'P');
    write_test_asset(TEST_ASSET_ROOT "/pl8/hidden.dat", 'H');
    write_test_asset(TEST_ASSET_ROOT "/RaW/Voice.RAW", 'W');
    write_test_asset(TEST_ASSET_ROOT "/XMI/Tune.Xmi", 'X');
    write_test_asset(TEST_ASSET_ROOT "/sMk/Intro.SMK", 'S');

    memset(&config, 0, sizeof(config));
    config.title = "Caesar II asset lookup test";
    config.asset_root = TEST_ASSET_ROOT;
    config.user_data_root = TEST_USER_ROOT;
    config.logical_width = 1;
    config.logical_height = 1;
    config.window_scale = 1;
    config.headless = 1;
    TEST_ASSERT_TRUE(c2_host_init(&config));

    TEST_ASSERT_EQUAL_size_t(1,
        c2_host_asset_read("shared.pl8", &byte, 1, 0));
    TEST_ASSERT_EQUAL_UINT8('R', byte);
    TEST_ASSERT_EQUAL_size_t(1,
        c2_host_asset_read("root.case", &byte, 1, 0));
    TEST_ASSERT_EQUAL_UINT8('C', byte);
    TEST_ASSERT_EQUAL_size_t(1,
        c2_host_asset_read("tutorial.pl8", &byte, 1, 0));
    TEST_ASSERT_EQUAL_UINT8('P', byte);
    TEST_ASSERT_EQUAL_size_t(1,
        c2_host_asset_read("voice.raw", &byte, 1, 0));
    TEST_ASSERT_EQUAL_UINT8('W', byte);
    TEST_ASSERT_EQUAL_size_t(1,
        c2_host_asset_read("tune.xmi", &byte, 1, 0));
    TEST_ASSERT_EQUAL_UINT8('X', byte);
    TEST_ASSERT_EQUAL_size_t(1,
        c2_host_asset_read("intro.smk", &byte, 1, 0));
    TEST_ASSERT_EQUAL_UINT8('S', byte);
    TEST_ASSERT_EQUAL_size_t(0,
        c2_host_asset_read("hidden.dat", &byte, 1, 0));
    TEST_ASSERT_EQUAL_size_t(0,
        c2_host_asset_read("../Shared.PL8", &byte, 1, 0));

    c2_host_shutdown();
    remove_test_assets();
    remove_test_files();
}

static void test_indexed_screenshot_is_saved_as_png(void)
{
    struct c2_host_config config;
    SDL_Surface *screenshot;
    unsigned char pixels[4] = { 0, 1, 1, 0 };
    unsigned char palette[256 * 3];
    unsigned char signature[8];
    Uint8 red;
    Uint8 green;
    Uint8 blue;
    Uint8 alpha;

    remove_test_files();
    memset(&config, 0, sizeof(config));
    config.title = "Caesar II screenshot test";
    config.asset_root = ".";
    config.user_data_root = TEST_USER_ROOT;
    config.logical_width = 1;
    config.logical_height = 1;
    config.window_scale = 1;
    config.headless = 1;
    TEST_ASSERT_TRUE(c2_host_init(&config));

    memset(palette, 0, sizeof(palette));
    palette[3] = 63;
    palette[5] = 31;
    TEST_ASSERT_TRUE(c2_host_save_indexed_png("screen.png", pixels,
                                             2, 2, 2,
                                             palette, sizeof(palette)));
    TEST_ASSERT_EQUAL_size_t(sizeof(signature),
        c2_host_user_file_read("screen.png", signature,
                               sizeof(signature), 0));
    TEST_ASSERT_EQUAL_UINT8_ARRAY(
        ((const unsigned char []) { 0x89, 'P', 'N', 'G', 0x0d, 0x0a, 0x1a, 0x0a }),
        signature, sizeof(signature));

    screenshot = SDL_LoadPNG(TEST_USER_ROOT "/screen.png");
    TEST_ASSERT_NOT_NULL(screenshot);
    TEST_ASSERT_EQUAL_INT(2, screenshot->w);
    TEST_ASSERT_EQUAL_INT(2, screenshot->h);
    TEST_ASSERT_TRUE(SDL_ReadSurfacePixel(screenshot, 1, 0,
                                          &red, &green, &blue, &alpha));
    TEST_ASSERT_EQUAL_UINT8(255, red);
    TEST_ASSERT_EQUAL_UINT8(0, green);
    TEST_ASSERT_EQUAL_UINT8(125, blue);
    TEST_ASSERT_EQUAL_UINT8(255, alpha);
    SDL_DestroySurface(screenshot);

    c2_host_shutdown();
    remove_test_files();
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

static void test_mouse_edges_survive_between_engine_polls(void)
{
    struct c2_host_config config;
    struct c2_host_input input;
    SDL_Event event;

    remove_test_files();
    memset(&config, 0, sizeof(config));
    config.title = "Caesar II input transition test";
    config.asset_root = ".";
    config.user_data_root = TEST_USER_ROOT;
    config.logical_width = 640;
    config.logical_height = 480;
    config.window_scale = 1;
    config.headless = 1;
    TEST_ASSERT_TRUE(c2_host_init(&config));

    memset(&event, 0, sizeof(event));
    event.type = SDL_EVENT_MOUSE_BUTTON_DOWN;
    event.button.button = SDL_BUTTON_LEFT;
    event.button.x = 320.0f;
    event.button.y = 240.0f;
    c2_sdl_host_handle_event(&event);
    event.type = SDL_EVENT_MOUSE_BUTTON_UP;
    c2_sdl_host_handle_event(&event);

    c2_host_input_snapshot(&input);
    TEST_ASSERT_EQUAL_UINT(0, input.mouse_buttons);
    c2_host_input_poll(&input);
    TEST_ASSERT_EQUAL_UINT(C2_HOST_MOUSE_LEFT, input.mouse_buttons);
    c2_host_input_poll(&input);
    TEST_ASSERT_EQUAL_UINT(0, input.mouse_buttons);

    c2_host_shutdown();
    remove_test_files();
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_assets_use_install_then_cd_media_lookup);
    RUN_TEST(test_user_streams_and_dos_style_directory_listing);
    RUN_TEST(test_indexed_screenshot_is_saved_as_png);
    RUN_TEST(test_mouse_edges_survive_between_engine_polls);
    return UNITY_END();
}
