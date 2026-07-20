#include "c2_asm_routines.h"

#define C2_LEGACY_SCREEN_WIDTH 640

extern unsigned char *internal_screen;
extern int screen_width;
extern int sprite_height;
extern int sprite_width;

static unsigned char *screen_at(int x, int y)
{
    return internal_screen + y * screen_width + x;
}

void show_internal_point(int x, int y, int colour)
{
    *screen_at(x, y) = (unsigned char)colour;
}

void show_internal_2point(int x, int y, int colour)
{
    unsigned char *destination;

    destination = screen_at(x, y);
    destination[0] = (unsigned char)colour;
    destination[1] = (unsigned char)colour;
}

void show_internal_2x8(int x, int y, int colour)
{
    unsigned char *destination;
    int row;

    destination = screen_at(x, y);
    for (row = 0; row < 8; row++) {
        destination[0] = (unsigned char)colour;
        destination[1] = (unsigned char)colour;
        destination += C2_LEGACY_SCREEN_WIDTH;
    }
}

void show_internal_4point(int x, int y, int colour)
{
    unsigned char *destination;
    int column;

    destination = screen_at(x, y);
    for (column = 0; column < 4; column++) {
        destination[column] = (unsigned char)colour;
    }
}

void xor_internal_2point(int x, int y, int colour)
{
    unsigned char *destination;
    int column;

    destination = screen_at(x, y);
    for (column = 0; column < 2; column++) {
        if (destination[column] == 0) {
            destination[column] = (unsigned char)colour;
        }
    }
}

static void place_block(unsigned char *source, int screen_offset, int size)
{
    int row;
    int column;

    for (row = 0; row < size; row++) {
        for (column = 0; column < size; column++) {
            internal_screen[screen_offset + row * C2_LEGACY_SCREEN_WIDTH + column] =
                source[row * size + column];
        }
    }
}

void place_2x2_block(unsigned char *source, int screen_offset)
{
    place_block(source, screen_offset, 2);
}

void place_4x4_block(unsigned char *source, int screen_offset)
{
    place_block(source, screen_offset, 4);
}

void place_6x6_block(unsigned char *source, int screen_offset)
{
    place_block(source, screen_offset, 6);
}

void place_8x8_block(unsigned char *source, int screen_offset)
{
    place_block(source, screen_offset, 8);
}

void show_fast_rect(int x, int y, int colour)
{
    int row;
    int block;
    int column;

    for (row = 0; row < sprite_height; row++) {
        for (block = 0; block < sprite_width; block++) {
            for (column = 0; column < 16; column++) {
                *screen_at(x + block * 16 + column, y + row) =
                    (unsigned char)colour;
            }
        }
    }
}
