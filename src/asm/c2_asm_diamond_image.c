#include "c2_asm_routines.h"
#include "c2_bugfixes.h"

#define C2_LEGACY_SCREEN_WIDTH 640

extern unsigned char *internal_screen;
extern int screen_width;
extern int sprite_hat_start;
extern int sprite_start;
extern int sprite_x;
extern int sprite_y;
extern int y_length;

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

enum hat_part {
    HAT_FULL,
    HAT_KEEP_RIGHT,
    HAT_KEEP_LEFT
};

static void write_hat_pair(unsigned char *destination,
                           unsigned char *source)
{
    if (source[0] != 0) {
        destination[0] = source[0];
    }
    if (source[1] != 0) {
        destination[1] = source[1];
    }
}

static void write_diamond_hat(unsigned char *sprites, int depth,
                              int pair_count, enum hat_part part,
                              int medium_right_quirk)
{
    unsigned char *source;
    unsigned char *base;
    int centre;
    int first_pair;
    int last_pair;
    int destination_pair;
    int row;
    int pair;
    int distance;
    int vertical_offset;

    source = sprites + sprite_hat_start;
    base = diamond_destination();
    centre = pair_count / 2;
    first_pair = 0;
    last_pair = pair_count;
    if (part == HAT_KEEP_RIGHT) {
        first_pair = centre + 1;
    } else if (part == HAT_KEEP_LEFT) {
        last_pair = centre;
    }

    for (row = 0; row < y_length; row++) {
        if (row < depth) {
            base -= screen_width;
        }
        for (pair = first_pair; pair < last_pair; pair++) {
            distance = pair < centre ? centre - pair : pair - centre;
            if (row < depth) {
                vertical_offset = distance;
            } else {
                vertical_offset = distance - (row - depth) - 1;
            }
            if (vertical_offset >= 0) {
                destination_pair = pair;
                if (part == HAT_KEEP_RIGHT) {
                    destination_pair -= centre + 1;
                }
                if (!PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET &&
                    medium_right_quirk && row - depth == 2 && pair == 3) {
                    destination_pair = 31;
                }
                write_hat_pair(base +
                                   vertical_offset * C2_LEGACY_SCREEN_WIDTH +
                                   destination_pair * 2,
                               source + pair * 2);
            }
        }
        source += pair_count * 2;
    }
}

static void write_left_diamond_half_hat(unsigned char *sprites, int depth,
                                        int centre, int edge_seam)
{
    unsigned char *source;
    unsigned char *base;
    int row;
    int pair;
    int vertical_offset;

    source = sprites + sprite_hat_start;
    base = diamond_destination();
    for (row = 0; row < y_length; row++) {
        if (row < depth) {
            base -= screen_width;
        }
        for (pair = 0; pair <= centre; pair++) {
            if (row < depth) {
                vertical_offset = centre - pair;
            } else {
                vertical_offset = centre - pair - (row - depth) - 1;
            }
            if (vertical_offset >= 0 &&
                !(edge_seam == 2 && vertical_offset == 0)) {
                write_hat_pair(base +
                                   vertical_offset * C2_LEGACY_SCREEN_WIDTH +
                                   pair * 2,
                               source + pair * 2);
            }
        }
        source += (centre + 1) * 2;
    }
}

static void write_right_diamond_half_hat(unsigned char *sprites, int depth,
                                         int centre, int edge_seam)
{
    unsigned char *source;
    unsigned char *base;
    int destination_pair_offset;
    int row;
    int pair;
    int vertical_offset;

    source = sprites + sprite_hat_start;
    base = diamond_destination();
    destination_pair_offset = edge_seam == 2 ? -1 : centre;
    for (row = 0; row < y_length; row++) {
        if (row < depth) {
            base -= screen_width;
            if (edge_seam != 2) {
                write_hat_pair(base + centre * 2, source + 2);
            }
        }
        for (pair = 1; pair <= centre; pair++) {
            if (row < depth) {
                vertical_offset = pair;
            } else {
                vertical_offset = pair - (row - depth) - 1;
            }
            if (vertical_offset >= 0) {
                write_hat_pair(base +
                                   vertical_offset * C2_LEGACY_SCREEN_WIDTH +
                                   (destination_pair_offset + pair) * 2,
                               source + pair * 2);
            }
        }
        source += (centre + 1) * 2;
    }
}

void write_small_diamond_hat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 5, HAT_FULL, 0);
}

void write_small_diamond_lefthat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 5, HAT_KEEP_RIGHT, 0);
}

void write_small_diamond_righthat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 5, HAT_KEEP_LEFT, 0);
}

void write_small_diamond_lefthalfhat(unsigned char *sprites, int depth,
                                     int edge_seam)
{
    write_left_diamond_half_hat(sprites, depth, 2, edge_seam);
}

void write_small_diamond_righthalfhat(unsigned char *sprites, int depth,
                                      int edge_seam)
{
    write_right_diamond_half_hat(sprites, depth, 2, edge_seam);
}

void write_medium_diamond_hat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 13, HAT_FULL, 0);
}

void write_medium_diamond_lefthat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 13, HAT_KEEP_RIGHT, 0);
}

void write_medium_diamond_righthat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 13, HAT_KEEP_LEFT, 1);
}

void write_medium_diamond_lefthalfhat(unsigned char *sprites, int depth,
                                      int edge_seam)
{
    write_left_diamond_half_hat(sprites, depth, 6, edge_seam);
}

void write_medium_diamond_righthalfhat(unsigned char *sprites, int depth,
                                       int edge_seam)
{
    write_right_diamond_half_hat(sprites, depth, 6, edge_seam);
}

void write_large_diamond_hat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 29, HAT_FULL, 0);
}

void write_large_diamond_lefthat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 29, HAT_KEEP_RIGHT, 0);
}

void write_large_diamond_righthat(unsigned char *sprites, int depth)
{
    write_diamond_hat(sprites, depth, 29, HAT_KEEP_LEFT, 0);
}

void write_large_diamond_lefthalfhat(unsigned char *sprites, int depth,
                                     int edge_seam)
{
    write_left_diamond_half_hat(sprites, depth, 14, edge_seam);
}

void write_large_diamond_righthalfhat(unsigned char *sprites, int depth,
                                      int edge_seam)
{
    write_right_diamond_half_hat(sprites, depth, 14, edge_seam);
}

static void write_diamond_roof(unsigned char *sprites, int pair_count,
                               enum hat_part part)
{
    unsigned char *source;
    unsigned char *base;
    int centre;
    int first_pair;
    int last_pair;
    int destination_pair;
    int row;
    int pair;
    int distance;

    source = sprites + sprite_hat_start;
    base = diamond_destination();
    centre = pair_count / 2;
    first_pair = 0;
    last_pair = pair_count;
    if (part == HAT_KEEP_RIGHT) {
        first_pair = centre + 1;
    } else if (part == HAT_KEEP_LEFT) {
        last_pair = centre;
    }

    for (row = 0; row < y_length; row++) {
        for (pair = first_pair; pair < last_pair; pair++) {
            distance = pair < centre ? centre - pair : pair - centre;
            if (distance <= row) {
                destination_pair = pair;
                if (part == HAT_KEEP_RIGHT) {
                    destination_pair -= centre + 1;
                }
                write_hat_pair(base + distance * C2_LEGACY_SCREEN_WIDTH +
                                   destination_pair * 2,
                               source + pair * 2);
            }
        }
        source += pair_count * 2;
        base -= screen_width;
    }
}

static void write_left_diamond_half_roof(unsigned char *sprites, int centre,
                                         int edge_seam)
{
    unsigned char *source;
    unsigned char *base;
    int row;
    int pair;
    int vertical_offset;

    source = sprites + sprite_hat_start;
    base = diamond_destination();
    for (row = 0; row < y_length; row++) {
        for (pair = 0; pair <= centre; pair++) {
            vertical_offset = centre - pair;
            if (vertical_offset <= row &&
                !(edge_seam == 2 && vertical_offset == 0)) {
                write_hat_pair(base +
                                   vertical_offset * C2_LEGACY_SCREEN_WIDTH +
                                   pair * 2,
                               source + pair * 2);
            }
        }
        source += (centre + 1) * 2;
        base -= screen_width;
    }
}

static void write_right_diamond_half_roof(unsigned char *sprites, int centre,
                                          int edge_seam)
{
    unsigned char *source;
    unsigned char *base;
    int destination_pair_offset;
    int first_pair;
    int last_pair;
    int row;
    int pair;

    source = sprites + sprite_hat_start;
    base = diamond_destination();
    destination_pair_offset = edge_seam == 2 ? -1 : centre;
    for (row = 0; row < y_length; row++) {
        if (row == 0) {
            if (edge_seam != 2) {
                write_hat_pair(base + destination_pair_offset * 2,
                               source + centre * 2);
            }
        } else {
            first_pair = edge_seam == 2 ? 1 : 0;
            last_pair = row < centre ? row : centre;
            if (!PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR &&
                centre == 14 && edge_seam == 2 && row == 10) {
                write_hat_pair(base + destination_pair_offset * 2, source);
            }
            for (pair = first_pair; pair <= last_pair; pair++) {
                write_hat_pair(base + pair * C2_LEGACY_SCREEN_WIDTH +
                                   (destination_pair_offset + pair) * 2,
                               source + pair * 2);
            }
        }
        source += (centre + 1) * 2;
        base -= screen_width;
    }
}

void write_small_diamond_roof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 5, HAT_FULL);
}

void write_small_diamond_leftroof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 5, HAT_KEEP_RIGHT);
}

void write_small_diamond_rightroof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 5, HAT_KEEP_LEFT);
}

void write_small_diamond_righthalfroof(unsigned char *sprites, int edge_seam)
{
    write_right_diamond_half_roof(sprites, 2, edge_seam);
}

void write_small_diamond_lefthalfroof(unsigned char *sprites, int edge_seam)
{
    write_left_diamond_half_roof(sprites, 2, edge_seam);
}

void write_medium_diamond_roof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 13, HAT_FULL);
}

void write_medium_diamond_leftroof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 13, HAT_KEEP_RIGHT);
}

void write_medium_diamond_rightroof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 13, HAT_KEEP_LEFT);
}

void write_medium_diamond_righthalfroof(unsigned char *sprites, int edge_seam)
{
    write_right_diamond_half_roof(sprites, 6, edge_seam);
}

void write_medium_diamond_lefthalfroof(unsigned char *sprites, int edge_seam)
{
    write_left_diamond_half_roof(sprites, 6, edge_seam);
}

void write_large_diamond_roof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 29, HAT_FULL);
}

void write_large_diamond_leftroof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 29, HAT_KEEP_RIGHT);
}

void write_large_diamond_rightroof(unsigned char *sprites)
{
    write_diamond_roof(sprites, 29, HAT_KEEP_LEFT);
}

void write_large_diamond_righthalfroof(unsigned char *sprites, int edge_seam)
{
    write_right_diamond_half_roof(sprites, 14, edge_seam);
}

void write_large_diamond_lefthalfroof(unsigned char *sprites, int edge_seam)
{
    write_left_diamond_half_roof(sprites, 14, edge_seam);
}
