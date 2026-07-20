#include <assert.h>
#include <string.h>

#include "c2_asm_routines.h"

#define TEST_WIDTH 640
#define TEST_HEIGHT 16

static unsigned char pixels[TEST_WIDTH * TEST_HEIGHT];
unsigned char *internal_screen = pixels;
int screen_width = TEST_WIDTH;
int sprite_height;
int sprite_width;

static void clear_pixels(void)
{
    memset(pixels, 0, sizeof(pixels));
}

static void test_point_writers(void)
{
    static const unsigned char four_nines[] = {9, 9, 9, 9};
    int row;

    clear_pixels();
    show_internal_point(3, 2, 7);
    show_internal_2point(5, 2, 8);
    show_internal_4point(8, 2, 9);
    show_internal_2x8(20, 1, 10);
    assert(pixels[2 * TEST_WIDTH + 3] == 7);
    assert(pixels[2 * TEST_WIDTH + 5] == 8);
    assert(pixels[2 * TEST_WIDTH + 6] == 8);
    assert(memcmp(pixels + 2 * TEST_WIDTH + 8, four_nines,
                  sizeof(four_nines)) == 0);
    for (row = 1; row < 9; row++) {
        assert(pixels[row * TEST_WIDTH + 20] == 10);
        assert(pixels[row * TEST_WIDTH + 21] == 10);
    }
}

static void test_2x8_legacy_row_stride(void)
{
    int row;

    clear_pixels();
    screen_width = TEST_WIDTH + 1;
    show_internal_2x8(3, 1, 14);
    for (row = 0; row < 8; row++) {
        assert(pixels[TEST_WIDTH + 1 + 3 + row * TEST_WIDTH] == 14);
        assert(pixels[TEST_WIDTH + 1 + 4 + row * TEST_WIDTH] == 14);
    }
    screen_width = TEST_WIDTH;
}

static void test_zero_only_writer(void)
{
    clear_pixels();
    pixels[4 * TEST_WIDTH + 2] = 3;
    xor_internal_2point(2, 4, 12);
    assert(pixels[4 * TEST_WIDTH + 2] == 3);
    assert(pixels[4 * TEST_WIDTH + 3] == 12);
}

static void test_one_block(void (*place)(unsigned char *, int), int size)
{
    unsigned char source[64];
    int row;
    int column;

    for (row = 0; row < size; row++) {
        for (column = 0; column < size; column++) {
            source[row * size + column] =
                (unsigned char)(row * size + column + 1);
        }
    }
    clear_pixels();
    place(source, TEST_WIDTH + 4);
    for (row = 0; row < size; row++) {
        assert(memcmp(pixels + (row + 1) * TEST_WIDTH + 4,
                      source + row * size, (size_t)size) == 0);
    }
}

static void test_blocks(void)
{
    test_one_block(place_2x2_block, 2);
    test_one_block(place_4x4_block, 4);
    test_one_block(place_6x6_block, 6);
    test_one_block(place_8x8_block, 8);
}

static void test_fast_rect(void)
{
    int row;
    int column;

    clear_pixels();
    sprite_width = 2;
    sprite_height = 3;
    show_fast_rect(7, 5, 0x2a);
    for (row = 5; row < 8; row++) {
        for (column = 7; column < 39; column++) {
            assert(pixels[row * TEST_WIDTH + column] == 0x2a);
        }
        assert(pixels[row * TEST_WIDTH + 6] == 0);
        assert(pixels[row * TEST_WIDTH + 39] == 0);
    }
}

int main(void)
{
    test_point_writers();
    test_2x8_legacy_row_stride();
    test_zero_only_writer();
    test_blocks();
    test_fast_rect();
    return 0;
}
