#include <unity/unity.h>
#include <string.h>

#include "c2_asm_routines.h"
#include "c2_bugfixes.h"

#define TEST_WIDTH 640
#define TEST_HEIGHT 40

typedef void (*diamond_placer)(unsigned char *, int);
typedef void (*half_hat_writer)(unsigned char *, int, int);
typedef void (*half_roof_writer)(unsigned char *, int);

static unsigned char pixels[(TEST_WIDTH + 1) * TEST_HEIGHT];
static unsigned char expected[(TEST_WIDTH + 1) * TEST_HEIGHT];
unsigned char *internal_screen = pixels;
int screen_width;
int sprite_hat_start;
int sprite_start;
int sprite_x;
int sprite_y;
int y_length;

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
        TEST_ASSERT_TRUE(memcmp(pixels, expected, sizeof(pixels)) == 0);
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
        TEST_ASSERT_TRUE(memcmp(pixels, expected, sizeof(pixels)) == 0);
    }
}

enum test_hat_part {
    TEST_HAT_FULL,
    TEST_HAT_KEEP_RIGHT,
    TEST_HAT_KEEP_LEFT
};

static void test_hat(diamond_placer write, int pair_count,
                     enum test_hat_part part, int medium_right_quirk)
{
    unsigned char sprites[1024];
    int depth;
    int centre;
    int first_pair;
    int last_pair;
    int destination_pair;
    int row;
    int pair;
    int distance;
    int vertical_offset;
    int base_offset;
    int destination_offset;
    int source_offset;

    centre = pair_count / 2;
    first_pair = part == TEST_HAT_KEEP_RIGHT ? centre + 1 : 0;
    last_pair = part == TEST_HAT_KEEP_LEFT ? centre : pair_count;
    sprite_hat_start = 7;
    y_length = 4;
    memset(sprites, 0, sizeof(sprites));
    for (source_offset = 0; source_offset < y_length * pair_count * 2;
         source_offset++) {
        sprites[sprite_hat_start + source_offset] =
            source_offset % 5 == 0 ? 0 : (unsigned char)(source_offset + 1);
    }

    for (depth = 0; depth < 3; depth++) {
        reset_buffers();
        write(sprites, depth);
        base_offset = sprite_y * screen_width + sprite_x;
        for (row = 0; row < y_length; row++) {
            if (row < depth) {
                base_offset -= screen_width;
            }
            for (pair = first_pair; pair < last_pair; pair++) {
                distance = pair < centre ? centre - pair : pair - centre;
                vertical_offset = row < depth ? distance :
                    distance - (row - depth) - 1;
                if (vertical_offset >= 0) {
                    destination_pair = pair;
                    if (part == TEST_HAT_KEEP_RIGHT) {
                        destination_pair -= centre + 1;
                    }
                    if (!PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET &&
                        medium_right_quirk && row - depth == 2 && pair == 3) {
                        destination_pair = 31;
                    }
                    destination_offset = base_offset +
                        vertical_offset * TEST_WIDTH + destination_pair * 2;
                    source_offset = sprite_hat_start +
                        (row * pair_count + pair) * 2;
                    if (sprites[source_offset] != 0) {
                        expected[destination_offset] = sprites[source_offset];
                    }
                    if (sprites[source_offset + 1] != 0) {
                        expected[destination_offset + 1] =
                            sprites[source_offset + 1];
                    }
                }
            }
        }
        TEST_ASSERT_TRUE(memcmp(pixels, expected, sizeof(pixels)) == 0);
    }
}

static void test_medium_right_hat_offset(void)
{
    unsigned char sprites[1024];
    int base_offset;
    int source_offset;

    memset(sprites, 0, sizeof(sprites));
    sprite_hat_start = 0;
    y_length = 3;
    source_offset = (2 * 13 + 3) * 2;
    sprites[source_offset] = 0x71;
    sprites[source_offset + 1] = 0x72;
    reset_buffers();

    write_medium_diamond_righthat(sprites, 0);

    base_offset = sprite_y * screen_width + sprite_x;
#if PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET
    TEST_ASSERT_TRUE(pixels[base_offset + 6] == 0x71);
    TEST_ASSERT_TRUE(pixels[base_offset + 7] == 0x72);
    TEST_ASSERT_TRUE(pixels[base_offset + 62] == 0xa5);
    TEST_ASSERT_TRUE(pixels[base_offset + 63] == 0xa5);
#else
    TEST_ASSERT_TRUE(pixels[base_offset + 6] == 0xa5);
    TEST_ASSERT_TRUE(pixels[base_offset + 7] == 0xa5);
    TEST_ASSERT_TRUE(pixels[base_offset + 62] == 0x71);
    TEST_ASSERT_TRUE(pixels[base_offset + 63] == 0x72);
#endif
}

static void set_expected_pair(int destination_offset,
                              unsigned char *source)
{
    if (source[0] != 0) {
        expected[destination_offset] = source[0];
    }
    if (source[1] != 0) {
        expected[destination_offset + 1] = source[1];
    }
}

static void make_half_source(unsigned char *sprites, int pair_count,
                             int rows)
{
    int source_offset;

    memset(sprites, 0, 1024);
    for (source_offset = 0; source_offset < rows * pair_count * 2;
         source_offset++) {
        sprites[sprite_hat_start + source_offset] =
            source_offset % 7 == 0 ? 0 :
            (unsigned char)(source_offset * 13 + 5);
    }
}

static void test_half_hat(half_hat_writer write, int centre, int keep_left)
{
    unsigned char sprites[1024];
    int edge_seam;
    int depth;
    int pair_count;
    int destination_pair_offset;
    int destination_offset;
    int source_offset;
    int base_offset;
    int vertical_offset;
    int row;
    int pair;

    pair_count = centre + 1;
    sprite_hat_start = 7;
    y_length = 8;
    make_half_source(sprites, pair_count, y_length);
    for (edge_seam = 0; edge_seam <= 2; edge_seam += 2) {
        for (depth = 0; depth <= 5; depth += depth == 0 ? 2 : 3) {
            reset_buffers();
            write(sprites, depth, edge_seam);
            base_offset = sprite_y * screen_width + sprite_x;
            destination_pair_offset = edge_seam == 2 ? -1 : centre;
            for (row = 0; row < y_length; row++) {
                source_offset = sprite_hat_start + row * pair_count * 2;
                if (row < depth) {
                    base_offset -= screen_width;
                }
                if (!keep_left && row < depth && edge_seam != 2) {
                    set_expected_pair(base_offset + centre * 2,
                                      sprites + source_offset + 2);
                }
                for (pair = keep_left ? 0 : 1; pair <= centre; pair++) {
                    if (row < depth) {
                        vertical_offset = keep_left ? centre - pair : pair;
                    } else {
                        vertical_offset = keep_left ?
                            centre - pair - (row - depth) - 1 :
                            pair - (row - depth) - 1;
                    }
                    if (vertical_offset < 0 ||
                        (keep_left && edge_seam == 2 &&
                         vertical_offset == 0)) {
                        continue;
                    }
                    destination_offset = base_offset +
                        vertical_offset * TEST_WIDTH +
                        (keep_left ? pair :
                         destination_pair_offset + pair) * 2;
                    set_expected_pair(destination_offset,
                                      sprites + source_offset + pair * 2);
                }
            }
            TEST_ASSERT_TRUE(memcmp(pixels, expected, sizeof(pixels)) == 0);
        }
    }
}

static void test_half_roof(half_roof_writer write, int centre, int keep_left)
{
    unsigned char sprites[1024];
    int edge_seam;
    int pair_count;
    int first_pair;
    int last_pair;
    int destination_pair_offset;
    int destination_offset;
    int source_offset;
    int base_offset;
    int vertical_offset;
    int row;
    int pair;

    pair_count = centre + 1;
    sprite_hat_start = 7;
    y_length = 16;
    make_half_source(sprites, pair_count, y_length + 1);
    for (edge_seam = 0; edge_seam <= 2; edge_seam += 2) {
        reset_buffers();
        write(sprites, edge_seam);
        base_offset = sprite_y * screen_width + sprite_x;
        destination_pair_offset = edge_seam == 2 ? -1 : centre;
        for (row = 0; row < y_length; row++) {
            source_offset = sprite_hat_start + row * pair_count * 2;
            if (keep_left) {
                for (pair = 0; pair <= centre; pair++) {
                    vertical_offset = centre - pair;
                    if (vertical_offset <= row &&
                        !(edge_seam == 2 && vertical_offset == 0)) {
                        destination_offset = base_offset +
                            vertical_offset * TEST_WIDTH + pair * 2;
                        set_expected_pair(destination_offset,
                                          sprites + source_offset + pair * 2);
                    }
                }
            } else if (row == 0) {
                if (edge_seam != 2) {
                    set_expected_pair(base_offset +
                                          destination_pair_offset * 2,
                                      sprites + source_offset + centre * 2);
                }
            } else {
                first_pair = edge_seam == 2 ? 1 : 0;
                last_pair = row < centre ? row : centre;
                if (!PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR &&
                    centre == 14 && edge_seam == 2 && row == 10) {
                    set_expected_pair(base_offset +
                                          destination_pair_offset * 2,
                                      sprites + source_offset);
                }
                for (pair = first_pair; pair <= last_pair; pair++) {
                    destination_offset = base_offset + pair * TEST_WIDTH +
                        (destination_pair_offset + pair) * 2;
                    set_expected_pair(destination_offset,
                                      sprites + source_offset + pair * 2);
                }
            }
            base_offset -= screen_width;
        }
        TEST_ASSERT_TRUE(memcmp(pixels, expected, sizeof(pixels)) == 0);
    }
}

static void configure_diamond_test(void)
{
    screen_width = TEST_WIDTH + 1;
    sprite_start = 5;
    sprite_x = 3;
    sprite_y = 2;
}

static void test_image_diamonds(void)
{
    configure_diamond_test();
    test_full_parts(place_i_small_diamond, 6, 4);
    test_half(place_i_small_diamond_lefthalf, 6, 4, 1, 0);
    test_half(place_i_small_diamond_righthalf, 6, 4, 0, 0);
    test_full_parts(place_i_medium_diamond, 14, 12);
    test_half(place_i_medium_diamond_lefthalf, 14, 12, 1, 1);
    test_half(place_i_medium_diamond_righthalf, 14, 12, 0, 1);
    test_full_parts(place_i_large_diamond, 30, 28);
    test_half(place_i_large_diamond_lefthalf, 30, 28, 1, 1);
    test_half(place_i_large_diamond_righthalf, 30, 28, 0, 1);
}

static void test_projected_hats(void)
{
    configure_diamond_test();
    sprite_y = 10;
    test_hat(write_small_diamond_hat, 5, TEST_HAT_FULL, 0);
    test_hat(write_small_diamond_lefthat, 5, TEST_HAT_KEEP_RIGHT, 0);
    test_hat(write_small_diamond_righthat, 5, TEST_HAT_KEEP_LEFT, 0);
    test_hat(write_medium_diamond_hat, 13, TEST_HAT_FULL, 0);
    test_hat(write_medium_diamond_lefthat, 13, TEST_HAT_KEEP_RIGHT, 0);
    test_hat(write_medium_diamond_righthat, 13, TEST_HAT_KEEP_LEFT, 1);
    test_hat(write_large_diamond_hat, 29, TEST_HAT_FULL, 0);
    test_hat(write_large_diamond_lefthat, 29, TEST_HAT_KEEP_RIGHT, 0);
    test_hat(write_large_diamond_righthat, 29, TEST_HAT_KEEP_LEFT, 0);
    test_medium_right_hat_offset();
}

static void test_half_hats(void)
{
    configure_diamond_test();
    sprite_y = 10;
    test_half_hat(write_small_diamond_lefthalfhat, 2, 1);
    test_half_hat(write_small_diamond_righthalfhat, 2, 0);
    test_half_hat(write_medium_diamond_lefthalfhat, 6, 1);
    test_half_hat(write_medium_diamond_righthalfhat, 6, 0);
    test_half_hat(write_large_diamond_lefthalfhat, 14, 1);
    test_half_hat(write_large_diamond_righthalfhat, 14, 0);
}

static void test_half_roofs(void)
{
    configure_diamond_test();
    sprite_y = 20;
    test_half_roof(write_small_diamond_lefthalfroof, 2, 1);
    test_half_roof(write_small_diamond_righthalfroof, 2, 0);
    test_half_roof(write_medium_diamond_lefthalfroof, 6, 1);
    test_half_roof(write_medium_diamond_righthalfroof, 6, 0);
    test_half_roof(write_large_diamond_lefthalfroof, 14, 1);
    test_half_roof(write_large_diamond_righthalfroof, 14, 0);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_image_diamonds);
    RUN_TEST(test_projected_hats);
    RUN_TEST(test_half_hats);
    RUN_TEST(test_half_roofs);
    return UNITY_END();
}
