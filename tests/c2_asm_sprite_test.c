#include <assert.h>
#include <string.h>

#include "c2_asm_routines.h"

#define TEST_WIDTH 640
#define TEST_HEIGHT 64

static unsigned char pixels[(TEST_WIDTH + 1) * TEST_HEIGHT];
int font_style;
unsigned char *internal_screen = pixels;
int screen_width = TEST_WIDTH;
int sprite_colour;
int sprite_height;
int sprite_image_no;
int sprite_start;
int sprite_width;
int sprite_x;
int sprite_y;
int x_length;
int x_ofset;
int x_wrap;
int y_length;

static void clear_pixels(unsigned char value)
{
    memset(pixels, value, sizeof(pixels));
}

static void set_position_and_size(int x, int y, int width, int height)
{
    sprite_x = x;
    sprite_y = y;
    sprite_width = width;
    sprite_height = height;
    x_wrap = screen_width - width;
}

static void test_fonts(void)
{
    unsigned char font[] = {99, 99, 1, 0, 2, 3, 0, 4, 0, 5};
    static const unsigned char coloured[] = {12, 7, 12, 12, 7, 12, 7, 12};
    static const unsigned char styled[] = {1, 7, 2, 3, 7, 4, 7, 5};

    sprite_start = 2;
    sprite_colour = 12;
    y_length = 2;
    set_position_and_size(3, 2, 4, 2);
    clear_pixels(7);
    font_style = 0;
    write_i_font(font);
    assert(memcmp(pixels + 2 * TEST_WIDTH + 3, coloured, 4) == 0);
    assert(memcmp(pixels + 3 * TEST_WIDTH + 3, coloured + 4, 4) == 0);

    clear_pixels(7);
    font_style = 1;
    write_i_font(font);
    assert(memcmp(pixels + 2 * TEST_WIDTH + 3, styled, 4) == 0);
    assert(memcmp(pixels + 3 * TEST_WIDTH + 3, styled + 4, 4) == 0);
}

static void test_one_clipped_font(void (*write_font)(unsigned char *))
{
    unsigned char font[] = {99, 1, 0, 8, 8, 2, 3, 8, 8};

    sprite_start = 1;
    sprite_colour = 10;
    x_length = 2;
    x_ofset = 2;
    y_length = 2;
    sprite_x = 6;
    sprite_y = 4;
    x_wrap = screen_width - x_length;
    clear_pixels(5);
    write_font(font);
    assert(pixels[4 * TEST_WIDTH + 6] == 10);
    assert(pixels[4 * TEST_WIDTH + 7] == 5);
    assert(pixels[5 * TEST_WIDTH + 6] == 10);
    assert(pixels[5 * TEST_WIDTH + 7] == 10);
}

static void test_sprite_writers(void)
{
    unsigned char sprite[] = {99, 99, 1, 0, 2, 3, 0, 4, 0, 5};
    static const unsigned char opaque[] = {1, 0, 2, 3, 0, 4, 0, 5};
    static const unsigned char transparent[] = {1, 6, 2, 3, 6, 4, 6, 5};

    sprite_start = 2;
    y_length = 2;
    set_position_and_size(8, 2, 4, 2);
    clear_pixels(6);
    place_i_sprite(sprite);
    assert(memcmp(pixels + 2 * TEST_WIDTH + 8, opaque, 4) == 0);
    assert(memcmp(pixels + 3 * TEST_WIDTH + 8, opaque + 4, 4) == 0);

    clear_pixels(6);
    write_i_sprite(sprite);
    assert(memcmp(pixels + 2 * TEST_WIDTH + 8, transparent, 4) == 0);
    assert(memcmp(pixels + 3 * TEST_WIDTH + 8, transparent + 4, 4) == 0);
}

static void test_one_clipped_sprite(void (*write_sprite)(unsigned char *))
{
    unsigned char sprite[] = {99, 1, 0, 8, 8, 2, 3, 8, 8};

    sprite_start = 1;
    x_length = 2;
    x_ofset = 2;
    y_length = 2;
    sprite_x = 10;
    sprite_y = 4;
    x_wrap = screen_width - x_length;
    clear_pixels(5);
    write_sprite(sprite);
    assert(pixels[4 * TEST_WIDTH + 10] == 1);
    assert(pixels[4 * TEST_WIDTH + 11] == 5);
    assert(pixels[5 * TEST_WIDTH + 10] == 2);
    assert(pixels[5 * TEST_WIDTH + 11] == 3);
}

static void test_one_square_block(void (*place)(unsigned char *), int size,
                                  unsigned int offset)
{
    unsigned char sprites[2048];
    unsigned char *entry;
    int row;
    int column;

    memset(sprites, 0, sizeof(sprites));
    sprite_image_no = 1;
    entry = sprites + sprite_image_no * 16 + 8;
    entry[4] = (unsigned char)offset;
    entry[5] = (unsigned char)(offset >> 8);
    entry[6] = (unsigned char)(offset >> 16);
    for (row = 0; row < size; row++) {
        for (column = 0; column < size; column++) {
            sprites[offset + row * size + column] =
                (unsigned char)(row + column + 1);
        }
    }

    screen_width = TEST_WIDTH + 1;
    sprite_x = 4;
    sprite_y = 1;
    clear_pixels(0);
    place(sprites);
    for (row = 0; row < size; row++) {
        assert(memcmp(pixels + screen_width + sprite_x + row * TEST_WIDTH,
                      sprites + offset + row * size, (size_t)size) == 0);
    }
    screen_width = TEST_WIDTH;
}

static void test_square_blocks(void)
{
    test_one_square_block(place_16x16_block, 16, 0x100);
    test_one_square_block(place_24x24_block, 24, 0x200);
    test_one_square_block(place_32x32_block, 32, 0x300);
}

static void test_mouse_background(void)
{
    char background[24 * 24];
    int row;
    int column;

    screen_width = TEST_WIDTH + 1;
    sprite_x = 5;
    sprite_y = 2;
    clear_pixels(0);
    for (row = 0; row < 24; row++) {
        for (column = 0; column < 24; column++) {
            pixels[sprite_y * screen_width + sprite_x + row * TEST_WIDTH +
                   column] = (unsigned char)(row + column + 128);
        }
    }
    pick_up_mouse_background(background);
    clear_pixels(0);
    put_down_mouse_background(background);
    for (row = 0; row < 24; row++) {
        for (column = 0; column < 24; column++) {
            assert(pixels[sprite_y * screen_width + sprite_x +
                          row * TEST_WIDTH + column] ==
                   (unsigned char)(row + column + 128));
        }
    }
    screen_width = TEST_WIDTH;
}

int main(void)
{
    test_fonts();
    test_one_clipped_font(write_i_left_font);
    test_one_clipped_font(write_i_right_font);
    test_sprite_writers();
    test_one_clipped_sprite(write_i_left_sprite);
    test_one_clipped_sprite(write_i_right_sprite);
    test_square_blocks();
    test_mouse_background();
    return 0;
}
