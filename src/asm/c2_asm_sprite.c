#include "c2_asm_routines.h"

#define C2_LEGACY_SCREEN_WIDTH 640
#define C2_MOUSE_SIZE 24

extern int font_style;
extern unsigned char *internal_screen;
extern int screen_width;
extern int sprite_colour;
extern int sprite_height;
extern int sprite_image_no;
extern int sprite_start;
extern int sprite_width;
extern int sprite_x;
extern int sprite_y;
extern int x_length;
extern int x_ofset;
extern int x_wrap;
extern int y_length;

static unsigned char *sprite_destination(void)
{
    return internal_screen + sprite_y * screen_width + sprite_x;
}

static void draw_transparent(unsigned char *source, int width, int height,
                             int source_wrap, int destination_wrap,
                             int use_source_colour)
{
    unsigned char *destination;
    int row;
    int column;

    destination = sprite_destination();
    for (row = 0; row < height; row++) {
        for (column = 0; column < width; column++) {
            if (*source != 0) {
                if (use_source_colour) {
                    *destination = *source;
                } else {
                    *destination = (unsigned char)sprite_colour;
                }
            }
            source++;
            destination++;
        }
        source += source_wrap;
        destination += destination_wrap;
    }
}

void write_i_font(unsigned char *font)
{
    draw_transparent(font + sprite_start, sprite_width, y_length, 0, x_wrap,
                     font_style == 1);
}

static void write_clipped_font(unsigned char *font)
{
    draw_transparent(font + sprite_start, x_length, y_length, x_ofset, x_wrap,
                     0);
}

void write_i_left_font(unsigned char *font)
{
    write_clipped_font(font);
}

void write_i_right_font(unsigned char *font)
{
    write_clipped_font(font);
}

void place_i_sprite(unsigned char *sprite)
{
    unsigned char *source;
    unsigned char *destination;
    int row;
    int column;

    source = sprite + sprite_start;
    destination = sprite_destination();
    for (row = 0; row < sprite_height; row++) {
        for (column = 0; column < sprite_width; column++) {
            *destination++ = *source++;
        }
        destination += x_wrap;
    }
}

void write_i_sprite(unsigned char *sprite)
{
    draw_transparent(sprite + sprite_start, sprite_width, y_length, 0, x_wrap,
                     1);
}

static void write_clipped_sprite(unsigned char *sprite)
{
    draw_transparent(sprite + sprite_start, x_length, y_length, x_ofset,
                     x_wrap, 1);
}

void write_i_left_sprite(unsigned char *sprite)
{
    write_clipped_sprite(sprite);
}

void write_i_right_sprite(unsigned char *sprite)
{
    write_clipped_sprite(sprite);
}

static unsigned int read_block_offset(unsigned char *sprites, int size)
{
    unsigned char *entry;
    unsigned int offset;

    entry = sprites + sprite_image_no * 16 + 8;
    offset = (unsigned int)entry[4] | (unsigned int)entry[5] << 8;
    if (size == 32) {
        offset |= (unsigned int)entry[6] << 16;
    }
    return offset;
}

static void place_square_block(unsigned char *sprites, int size)
{
    unsigned char *source;
    unsigned char *destination;
    int row;
    int column;

    source = sprites + read_block_offset(sprites, size);
    destination = sprite_destination();
    for (row = 0; row < size; row++) {
        for (column = 0; column < size; column++) {
            *destination++ = *source++;
        }
        destination += C2_LEGACY_SCREEN_WIDTH - size;
    }
}

void place_16x16_block(unsigned char *sprites)
{
    place_square_block(sprites, 16);
}

void place_24x24_block(unsigned char *sprites)
{
    place_square_block(sprites, 24);
}

void place_32x32_block(unsigned char *sprites)
{
    place_square_block(sprites, 32);
}

void pick_up_mouse_background(char *background)
{
    unsigned char *source;
    unsigned char *destination;
    int row;
    int column;

    source = sprite_destination();
    destination = (unsigned char *)background;
    for (row = 0; row < C2_MOUSE_SIZE; row++) {
        for (column = 0; column < C2_MOUSE_SIZE; column++) {
            *destination++ = *source++;
        }
        source += C2_LEGACY_SCREEN_WIDTH - C2_MOUSE_SIZE;
    }
}

void put_down_mouse_background(char *background)
{
    unsigned char *source;
    unsigned char *destination;
    int row;
    int column;

    source = (unsigned char *)background;
    destination = sprite_destination();
    for (row = 0; row < C2_MOUSE_SIZE; row++) {
        for (column = 0; column < C2_MOUSE_SIZE; column++) {
            *destination++ = *source++;
        }
        destination += C2_LEGACY_SCREEN_WIDTH - C2_MOUSE_SIZE;
    }
}
