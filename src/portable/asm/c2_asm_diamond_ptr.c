#include "c2_asm_routines.h"

#define C2_LEGACY_SCREEN_WIDTH 640

extern unsigned char *internal_screen;
extern int lib_para1;
extern int lib_para2;
extern int screen_width;

static unsigned char *diamond_origin(void)
{
    return internal_screen + lib_para2 * screen_width + lib_para1;
}

static void write_colour_word(unsigned char *destination, int colour)
{
    unsigned short encoded;

    encoded = (unsigned short)((unsigned int)colour +
                               ((unsigned int)colour << 8));
    destination[0] = (unsigned char)encoded;
    destination[1] = (unsigned char)(encoded >> 8);
}

static int diamond_left(int row, int height, int centre)
{
    if (row < height / 2) {
        return centre - row * 2;
    }
    return (row - height / 2) * 2;
}

static void write_diamond_row(unsigned char *origin, int row, int height,
                              int centre, int colour)
{
    int left;
    int right;

    left = diamond_left(row, height, centre);
    right = centre * 2 - left;
    write_colour_word(origin + row * C2_LEGACY_SCREEN_WIDTH + left, colour);
    if (right != left) {
        write_colour_word(origin + row * C2_LEGACY_SCREEN_WIDTH + right,
                          colour);
    }
}

static void write_diamond(int colour, int part, int height, int centre)
{
    unsigned char *origin;
    int row;
    int first;
    int last;

    origin = diamond_origin();
    first = part == 2 ? height / 2 : 0;
    last = part == 1 ? height / 2 : height;
    for (row = first; row < last; row++) {
        write_diamond_row(origin, row, height, centre, colour);
    }
}

static void write_diamond_side(int colour, int y_edge, int height, int centre,
                               int write_right_edge)
{
    unsigned char *origin;
    int row;
    int left;
    int column;

    if (y_edge != 0) {
        return;
    }
    origin = diamond_origin();
    for (row = 1; row < height - 1; row++) {
        left = diamond_left(row, height, centre);
        column = write_right_edge ? centre * 2 - left : left;
        write_colour_word(origin + row * C2_LEGACY_SCREEN_WIDTH + column,
                          colour);
    }
}

void write_i_large_diamond_ptr(int colour, int part)
{
    write_diamond(colour, part, 30, 28);
}

void write_i_large_diamond_ptr_left(int colour, int y_edge)
{
    write_diamond_side(colour, y_edge, 30, 28, 1);
}

void write_i_large_diamond_ptr_right(int colour, int y_edge)
{
    write_diamond_side(colour, y_edge, 30, 28, 0);
}

void write_i_medium_diamond_ptr(int colour, int part)
{
    write_diamond(colour, part, 14, 12);
}

void write_i_medium_diamond_ptr_left(int colour, int y_edge)
{
    write_diamond_side(colour, y_edge, 14, 12, 1);
}

void write_i_medium_diamond_ptr_right(int colour, int y_edge)
{
    write_diamond_side(colour, y_edge, 14, 12, 0);
}

void write_i_small_diamond_ptr(int colour, int part)
{
    write_diamond(colour, part, 6, 4);
}

void write_i_small_diamond_ptr_left(int colour, int y_edge)
{
    write_diamond_side(colour, y_edge, 6, 4, 1);
}

void write_i_small_diamond_ptr_right(int colour, int y_edge)
{
    write_diamond_side(colour, y_edge, 6, 4, 0);
}
