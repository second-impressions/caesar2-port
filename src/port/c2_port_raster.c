#include "c2_asm_routines.h"
#include "c2_data.h"

int data_ptr;
int font_style;
int sprite_colour;
int sprite_height;
int sprite_start;
int sprite_width;
int x_end;
int x_length;
int x_ofset;
int x_start;
int x_wrap;
int y_end;
int y_length;
int y_start;
unsigned char xclipped;
unsigned char yclipped;

void xclip(int clip_left, int clip_right)
{
    xclipped = 0;
    x_start = 0;
    x_end = sprite_width;

    if (sprite_width <= 0) {
        xclipped = 5;
    } else if (clip_left > sprite_x) {
        if (sprite_x + sprite_width <= clip_left) {
            xclipped = 5;
        } else {
            xclipped = 1;
            x_start = clip_left - sprite_x;
            sprite_start += x_start;
            sprite_x = clip_left;
        }
    } else if (clip_right - sprite_width < sprite_x) {
        if (clip_right <= sprite_x) {
            xclipped = 5;
        } else {
            xclipped = 2;
            x_end = clip_right - sprite_x;
        }
    }

    if (xclipped == 5) {
        x_length = 0;
    } else {
        x_length = x_end - x_start;
    }
    x_ofset = sprite_width - x_length;
    x_wrap = screen_width - x_length;
}

void yclip(int clip_top, int clip_bottom)
{
    yclipped = 0;
    y_start = 0;
    y_end = sprite_height;

    if (sprite_height <= 0) {
        yclipped = 5;
    } else if (clip_top > sprite_y) {
        if (sprite_y + sprite_height <= clip_top) {
            yclipped = 5;
        } else {
            yclipped = 3;
            y_start = clip_top - sprite_y;
            sprite_start += y_start * sprite_width;
            sprite_y = clip_top;
        }
    } else if (clip_bottom - sprite_height < sprite_y) {
        if (clip_bottom <= sprite_y) {
            yclipped = 5;
        } else {
            yclipped = 4;
            y_end = clip_bottom - sprite_y;
        }
    }

    if (yclipped == 5) {
        y_length = 0;
    } else {
        y_length = y_end - y_start;
    }
    if (xclipped == 5) {
        yclipped = 5;
    }
}

void write_image(unsigned char *sprite_data, int image_idx, int x, int y)
{
    data_ptr = image_idx * 16 + 8;
    sprite_width = sprite_data[data_ptr] + (sprite_data[data_ptr + 1] << 8);
    sprite_height = sprite_data[data_ptr + 2] +
                    (sprite_data[data_ptr + 3] << 8);
    sprite_start = sprite_data[data_ptr + 4] +
                   (sprite_data[data_ptr + 5] << 8) +
                   (sprite_data[data_ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;

    xclip(0, screen_width);
    yclip(0, screen_height);
    if (yclipped == 5) {
        return;
    }
    if (xclipped == 1) {
        write_i_left_sprite(sprite_data);
    } else if (xclipped == 2) {
        write_i_right_sprite(sprite_data);
    } else {
        write_i_sprite(sprite_data);
    }
}
