#include "c2_asm_routines.h"

#define C2_LEGACY_SCREEN_WIDTH 640
#define C2_SMALL_DIAMOND_HEIGHT 6

extern unsigned char *internal_screen;
extern int screen_width;
extern int sprite_start;
extern int sprite_x;
extern int sprite_y;

static const int small_left[C2_SMALL_DIAMOND_HEIGHT] = {4, 2, 0, 0, 2, 4};
static const int small_width[C2_SMALL_DIAMOND_HEIGHT] = {2, 6, 10, 10, 6, 2};
static const int small_half_width[C2_SMALL_DIAMOND_HEIGHT] = {0, 2, 4, 4, 2, 0};

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

void place_i_small_diamond(unsigned char *sprites, int part)
{
    unsigned char *source;
    unsigned char *destination;
    int row;
    int source_offset;

    source = sprites + sprite_start;
    destination = diamond_destination();
    source_offset = 0;
    for (row = 0; row < C2_SMALL_DIAMOND_HEIGHT; row++) {
        if ((part != 2 || row >= C2_SMALL_DIAMOND_HEIGHT / 2) &&
            (part != 1 || row < C2_SMALL_DIAMOND_HEIGHT / 2)) {
            copy_bytes(destination + row * C2_LEGACY_SCREEN_WIDTH +
                           small_left[row],
                       source + source_offset, small_width[row]);
        }
        source_offset += small_width[row];
    }
}

static void place_i_small_diamond_half(unsigned char *sprites,
                                       int keep_right_edge)
{
    unsigned char *source;
    unsigned char *destination;
    int row;
    int source_offset;
    int width;
    int source_column;
    int destination_column;

    source = sprites + sprite_start;
    destination = diamond_destination();
    source_offset = 0;
    for (row = 0; row < C2_SMALL_DIAMOND_HEIGHT; row++) {
        width = small_half_width[row];
        if (width != 0) {
            source_column = keep_right_edge ? small_width[row] - width : 0;
            destination_column = keep_right_edge ? 0 : small_left[row];
            copy_bytes(destination + row * C2_LEGACY_SCREEN_WIDTH +
                           destination_column,
                       source + source_offset + source_column, width);
        }
        source_offset += small_width[row];
    }
}

void place_i_small_diamond_lefthalf(unsigned char *sprites, int part)
{
    (void)part;
    place_i_small_diamond_half(sprites, 1);
}

void place_i_small_diamond_righthalf(unsigned char *sprites, int part)
{
    (void)part;
    place_i_small_diamond_half(sprites, 0);
}
