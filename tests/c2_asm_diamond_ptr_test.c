#include <assert.h>
#include <string.h>

#include "c2_asm_routines.h"

#define TEST_WIDTH 640
#define TEST_HEIGHT 40

typedef void (*diamond_writer)(int, int);

static unsigned char pixels[(TEST_WIDTH + 1) * TEST_HEIGHT];
static unsigned char expected[(TEST_WIDTH + 1) * TEST_HEIGHT];
unsigned char *internal_screen = pixels;
int lib_para1;
int lib_para2;
int screen_width;

static int diamond_left(int row, int height, int centre)
{
    if (row < height / 2) {
        return centre - row * 2;
    }
    return (row - height / 2) * 2;
}

static void expect_word(int row, int column, int colour)
{
    unsigned int encoded;
    int offset;

    encoded = (unsigned int)colour + ((unsigned int)colour << 8);
    offset = lib_para2 * screen_width + lib_para1 +
             row * TEST_WIDTH + column;
    expected[offset] = (unsigned char)encoded;
    expected[offset + 1] = (unsigned char)(encoded >> 8);
}

static void reset_buffers(void)
{
    memset(pixels, 0x55, sizeof(pixels));
    memset(expected, 0x55, sizeof(expected));
}

static void test_full_writer(diamond_writer write, int height, int centre)
{
    int parts[] = {0, 1, 2};
    int part_index;
    int part;
    int first;
    int last;
    int row;
    int left;
    int right;

    for (part_index = 0; part_index < 3; part_index++) {
        part = parts[part_index];
        reset_buffers();
        write(0x123, part);
        first = part == 2 ? height / 2 : 0;
        last = part == 1 ? height / 2 : height;
        for (row = first; row < last; row++) {
            left = diamond_left(row, height, centre);
            right = centre * 2 - left;
            expect_word(row, left, 0x123);
            if (right != left) {
                expect_word(row, right, 0x123);
            }
        }
        assert(memcmp(pixels, expected, sizeof(pixels)) == 0);
    }
}

static void test_side_writer(diamond_writer write, int height, int centre,
                             int right_edge)
{
    int row;
    int left;
    int column;

    reset_buffers();
    write(15, 0);
    for (row = 1; row < height - 1; row++) {
        left = diamond_left(row, height, centre);
        column = right_edge ? centre * 2 - left : left;
        expect_word(row, column, 15);
    }
    assert(memcmp(pixels, expected, sizeof(pixels)) == 0);

    reset_buffers();
    write(15, 1);
    assert(memcmp(pixels, expected, sizeof(pixels)) == 0);
}

int main(void)
{
    screen_width = TEST_WIDTH + 1;
    lib_para1 = 3;
    lib_para2 = 2;

    test_full_writer(write_i_large_diamond_ptr, 30, 28);
    test_side_writer(write_i_large_diamond_ptr_left, 30, 28, 1);
    test_side_writer(write_i_large_diamond_ptr_right, 30, 28, 0);
    test_full_writer(write_i_medium_diamond_ptr, 14, 12);
    test_side_writer(write_i_medium_diamond_ptr_left, 14, 12, 1);
    test_side_writer(write_i_medium_diamond_ptr_right, 14, 12, 0);
    test_full_writer(write_i_small_diamond_ptr, 6, 4);
    test_side_writer(write_i_small_diamond_ptr_left, 6, 4, 1);
    test_side_writer(write_i_small_diamond_ptr_right, 6, 4, 0);
    return 0;
}
