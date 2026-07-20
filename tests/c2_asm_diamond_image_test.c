#include <assert.h>
#include <string.h>

#include "c2_asm_routines.h"

#define TEST_WIDTH 640
#define TEST_HEIGHT 12

typedef void (*diamond_placer)(unsigned char *, int);

static const int row_left[] = {4, 2, 0, 0, 2, 4};
static const int row_width[] = {2, 6, 10, 10, 6, 2};
static const int half_width[] = {0, 2, 4, 4, 2, 0};
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

static void make_source(unsigned char *sprites)
{
    int index;

    memset(sprites, 0, 64);
    for (index = 0; index < 36; index++) {
        sprites[sprite_start + index] = (unsigned char)(index * 7);
    }
}

static void test_full_parts(void)
{
    unsigned char sprites[64];
    int part;
    int row;
    int source_offset;
    int destination_offset;

    make_source(sprites);
    for (part = 0; part < 3; part++) {
        reset_buffers();
        place_i_small_diamond(sprites, part);
        source_offset = sprite_start;
        for (row = 0; row < 6; row++) {
            if ((part != 2 || row >= 3) && (part != 1 || row < 3)) {
                destination_offset = sprite_y * screen_width + sprite_x +
                                     row * TEST_WIDTH + row_left[row];
                memcpy(expected + destination_offset, sprites + source_offset,
                       (size_t)row_width[row]);
            }
            source_offset += row_width[row];
        }
        assert(memcmp(pixels, expected, sizeof(pixels)) == 0);
    }
}

static void test_half(diamond_placer place, int keep_right_edge)
{
    unsigned char sprites[64];
    int row;
    int width;
    int source_offset;
    int source_column;
    int destination_column;
    int destination_offset;

    make_source(sprites);
    reset_buffers();
    place(sprites, 99);
    source_offset = sprite_start;
    for (row = 0; row < 6; row++) {
        width = half_width[row];
        if (width != 0) {
            source_column = keep_right_edge ? row_width[row] - width : 0;
            destination_column = keep_right_edge ? 0 : row_left[row];
            destination_offset = sprite_y * screen_width + sprite_x +
                                 row * TEST_WIDTH + destination_column;
            memcpy(expected + destination_offset,
                   sprites + source_offset + source_column, (size_t)width);
        }
        source_offset += row_width[row];
    }
    assert(memcmp(pixels, expected, sizeof(pixels)) == 0);
}

int main(void)
{
    screen_width = TEST_WIDTH + 1;
    sprite_start = 5;
    sprite_x = 3;
    sprite_y = 2;
    test_full_parts();
    test_half(place_i_small_diamond_lefthalf, 1);
    test_half(place_i_small_diamond_righthalf, 0);
    return 0;
}
