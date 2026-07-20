#include <assert.h>
#include <string.h>

#include "c2_asm_routines.h"

#define TEST_WIDTH 640
#define TEST_HEIGHT 40

typedef void (*diamond_placer)(unsigned char *, int);

static unsigned char pixels[(TEST_WIDTH + 1) * TEST_HEIGHT];
static unsigned char expected[(TEST_WIDTH + 1) * TEST_HEIGHT];
unsigned char *internal_screen = pixels;
int screen_width;
int sprite_start;
int sprite_x;
int sprite_y;

static void reset_buffers(void)
{
    memset(pixels, 0xa5, sizeof(pixels));
    memset(expected, 0xa5, sizeof(expected));
}

static int diamond_level(int row, int height)
{
    return row < height / 2 ? row : height - row - 1;
}

static int image_size(int height)
{
    int row;
    int size;

    size = 0;
    for (row = 0; row < height; row++) {
        size += diamond_level(row, height) * 4 + 2;
    }
    return size;
}

static void make_source(unsigned char *sprites, int height)
{
    int index;
    int size;

    size = image_size(height);
    memset(sprites, 0, 1024);
    for (index = 0; index < size; index++) {
        sprites[sprite_start + index] = (unsigned char)(index * 7);
    }
}

static void test_full_parts(diamond_placer place, int height, int centre)
{
    unsigned char sprites[1024];
    int part;
    int row;
    int source_offset;
    int destination_offset;
    int level;
    int left;
    int width;

    make_source(sprites, height);
    for (part = 0; part < 3; part++) {
        reset_buffers();
        place(sprites, part);
        source_offset = sprite_start;
        for (row = 0; row < height; row++) {
            level = diamond_level(row, height);
            left = centre - level * 2;
            width = level * 4 + 2;
            if ((part != 2 || row >= height / 2) &&
                (part != 1 || row < height / 2)) {
                destination_offset = sprite_y * screen_width + sprite_x +
                                     row * TEST_WIDTH + left;
                memcpy(expected + destination_offset, sprites + source_offset,
                       (size_t)width);
            }
            source_offset += width;
        }
        assert(memcmp(pixels, expected, sizeof(pixels)) == 0);
    }
}

static void test_half(diamond_placer place, int height, int centre,
                      int keep_right_edge, int select_part)
{
    unsigned char sprites[1024];
    int part;
    int row;
    int width;
    int source_offset;
    int source_column;
    int destination_column;
    int destination_offset;
    int level;
    int full_width;
    int left;

    make_source(sprites, height);
    for (part = 0; part < (select_part ? 3 : 1); part++) {
        reset_buffers();
        place(sprites, select_part ? part : 99);
        source_offset = sprite_start;
        for (row = 0; row < height; row++) {
            level = diamond_level(row, height);
            full_width = level * 4 + 2;
            width = level * 2;
            left = centre - level * 2;
            if (width != 0 &&
                (!select_part ||
                 ((part != 2 || row >= height / 2) &&
                  (part != 1 || row < height / 2)))) {
                source_column = keep_right_edge ? full_width - width : 0;
                destination_column = keep_right_edge ? 0 : left;
                destination_offset = sprite_y * screen_width + sprite_x +
                                     row * TEST_WIDTH + destination_column;
                memcpy(expected + destination_offset,
                       sprites + source_offset + source_column, (size_t)width);
            }
            source_offset += full_width;
        }
        assert(memcmp(pixels, expected, sizeof(pixels)) == 0);
    }
}

int main(void)
{
    screen_width = TEST_WIDTH + 1;
    sprite_start = 5;
    sprite_x = 3;
    sprite_y = 2;
    test_full_parts(place_i_small_diamond, 6, 4);
    test_half(place_i_small_diamond_lefthalf, 6, 4, 1, 0);
    test_half(place_i_small_diamond_righthalf, 6, 4, 0, 0);
    test_full_parts(place_i_medium_diamond, 14, 12);
    test_half(place_i_medium_diamond_lefthalf, 14, 12, 1, 1);
    test_half(place_i_medium_diamond_righthalf, 14, 12, 0, 1);
    test_full_parts(place_i_large_diamond, 30, 28);
    test_half(place_i_large_diamond_lefthalf, 30, 28, 1, 1);
    test_half(place_i_large_diamond_righthalf, 30, 28, 0, 1);
    return 0;
}
