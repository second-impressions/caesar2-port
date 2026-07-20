#include "c2_asm_routines.h"

#define C2_LEGACY_SCREEN_WIDTH 640

extern unsigned char *internal_screen;
extern int screen_width;
extern int sprite_start;
extern int sprite_x;
extern int sprite_y;

static unsigned char *diamond_destination(void)
{
    return internal_screen + sprite_y * screen_width + sprite_x;
}

static void copy_bytes(unsigned char *destination, unsigned char *source,
                       int count)
{
    int column;

    for (column = 0; column < count; column++) {
        destination[column] = source[column];
    }
}

static int diamond_level(int row, int height)
{
    if (row < height / 2) {
        return row;
    }
    return height - row - 1;
}

static int include_row(int row, int height, int part)
{
    return (part != 2 || row >= height / 2) &&
           (part != 1 || row < height / 2);
}

static void place_diamond(unsigned char *sprites, int part, int height,
                          int centre)
{
    unsigned char *source;
    unsigned char *destination;
    int row;
    int source_offset;
    int level;
    int left;
    int width;

    source = sprites + sprite_start;
    destination = diamond_destination();
    source_offset = 0;
    for (row = 0; row < height; row++) {
        level = diamond_level(row, height);
        left = centre - level * 2;
        width = level * 4 + 2;
        if (include_row(row, height, part)) {
            copy_bytes(destination + row * C2_LEGACY_SCREEN_WIDTH +
                           left,
                       source + source_offset, width);
        }
        source_offset += width;
    }
}

static void place_diamond_half(unsigned char *sprites, int part, int height,
                               int centre, int keep_right_edge,
                               int select_part)
{
    unsigned char *source;
    unsigned char *destination;
    int row;
    int source_offset;
    int width;
    int source_column;
    int destination_column;
    int level;
    int full_width;
    int left;

    source = sprites + sprite_start;
    destination = diamond_destination();
    source_offset = 0;
    for (row = 0; row < height; row++) {
        level = diamond_level(row, height);
        left = centre - level * 2;
        full_width = level * 4 + 2;
        width = level * 2;
        if (width != 0 && (!select_part || include_row(row, height, part))) {
            source_column = keep_right_edge ? full_width - width : 0;
            destination_column = keep_right_edge ? 0 : left;
            copy_bytes(destination + row * C2_LEGACY_SCREEN_WIDTH +
                           destination_column,
                       source + source_offset + source_column, width);
        }
        source_offset += full_width;
    }
}

void place_i_small_diamond(unsigned char *sprites, int part)
{
    place_diamond(sprites, part, 6, 4);
}

void place_i_small_diamond_lefthalf(unsigned char *sprites, int part)
{
    (void)part;
    place_diamond_half(sprites, part, 6, 4, 1, 0);
}

void place_i_small_diamond_righthalf(unsigned char *sprites, int part)
{
    (void)part;
    place_diamond_half(sprites, part, 6, 4, 0, 0);
}

void place_i_medium_diamond(unsigned char *sprites, int part)
{
    place_diamond(sprites, part, 14, 12);
}

void place_i_medium_diamond_lefthalf(unsigned char *sprites, int part)
{
    place_diamond_half(sprites, part, 14, 12, 1, 1);
}

void place_i_medium_diamond_righthalf(unsigned char *sprites, int part)
{
    place_diamond_half(sprites, part, 14, 12, 0, 1);
}

void place_i_large_diamond(unsigned char *sprites, int part)
{
    place_diamond(sprites, part, 30, 28);
}

void place_i_large_diamond_lefthalf(unsigned char *sprites, int part)
{
    place_diamond_half(sprites, part, 30, 28, 1, 1);
}

void place_i_large_diamond_righthalf(unsigned char *sprites, int part)
{
    place_diamond_half(sprites, part, 30, 28, 0, 1);
}
