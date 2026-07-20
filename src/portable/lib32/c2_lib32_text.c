#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include "c2_data.h"

#define C2_FONT1_BYTES 9460
#define C2_FONT2_BYTES 28248
#define C2_SYSTEM_PANEL_BYTES 41672
#define C2_TEXT_BUFFER_BYTES 40000
#define C2_GAME_PANELS_BYTES 23441
#define C2_FORMAT_BUFFER_BYTES 2000

unsigned char font1[C2_FONT1_BYTES];
unsigned char font2[C2_FONT2_BYTES];
unsigned char system_panel[C2_SYSTEM_PANEL_BYTES];
unsigned char game_panels[C2_GAME_PANELS_BYTES];
char text_buffer[C2_TEXT_BUFFER_BYTES];
char format_buffer[C2_FORMAT_BUFFER_BYTES];
char *text_pointer;
char *media_file = "help.eng";
struct media_entry this_media_entry;
unsigned char allow_padding;
int char_count;
int font_screen_limit;
int insert_place;

unsigned char hold_mouse_replace;
int sprite_image_no;
int sprite_x;
int sprite_y;
int x_is;
struct c2inf_rec c2inf;

static unsigned int read_u16(const unsigned char *bytes)
{
    return (unsigned int)bytes[0] | ((unsigned int)bytes[1] << 8);
}

static unsigned int read_u24(const unsigned char *bytes)
{
    return read_u16(bytes) | ((unsigned int)bytes[2] << 16);
}

static int get_text_offset(int entry_idx)
{
    int table_offset;

    table_offset = entry_idx * 4;
    return (unsigned char)text_buffer[table_offset + 8] |
           ((unsigned char)text_buffer[table_offset + 9] << 8) |
           ((unsigned char)text_buffer[table_offset + 10] << 16);
}

static const char *get_text(int entry_idx, int word_count)
{
    const char *text;

    text = text_buffer + get_text_offset(entry_idx);
    while (word_count > 0) {
        if (*text == '\0' && (text[-1] >= ' ' || text[-1] == '\0')) {
            word_count--;
        }
        text++;
    }
    while ((unsigned char)*text < ' ') {
        text++;
    }
    return text;
}

static int draw_glyph(unsigned char *font, unsigned char character, int x, int y, int color)
{
    const unsigned char *descriptor;
    const unsigned char *pixels;
    int glyph;
    int width;
    int height;
    int row;
    int column;

    glyph = letter_table[character];
    if (glyph == 0) {
        return 4;
    }
    descriptor = font + (glyph - 1) * 16 + 8;
    width = (int)read_u16(descriptor);
    height = (int)read_u16(descriptor + 2);
    pixels = font + read_u24(descriptor + 4);
    y += descriptor[13];

    for (row = 0; row < height; row++) {
        int destination_y;

        destination_y = y + row;
        if (destination_y < 0 || destination_y >= screen_height) {
            continue;
        }
        for (column = 0; column < width; column++) {
            int destination_x;
            unsigned char pixel;

            destination_x = x + column;
            pixel = pixels[row * width + column];
            if (pixel != 0 && destination_x >= 0 && destination_x < screen_width) {
                internal_screen[destination_y * screen_width + destination_x] =
                    color != 0 ? (unsigned char)color : pixel;
            }
        }
    }

    return width + 1;
}

static void draw_text(const unsigned char *text, int x, int y,
                      unsigned char *font, int color)
{
    x_is = x;
    while (*text != '\0') {
        unsigned char character;

        character = *text++;
        if (character == '_') {
            character = ' ';
        }
        if (character >= ' ') {
            x_is += draw_glyph(font, (unsigned char)(character - ' '), x_is, y, color);
        }
    }
    x_is += 4;
}

void font_list(int entry_idx, int word_count, int x, int y, unsigned char *font, int color)
{
    const unsigned char *text;

    text = (const unsigned char *)get_text(entry_idx, word_count);
    draw_text(text, x, y, font, color);
}

void put_a_font_string(char *text, int x, int y, unsigned char *font, int color)
{
    draw_text((unsigned char *)text, x, y, font, color);
}

int get_string_width(char *text, unsigned char *font)
{
    int width;

    width = 0;
    while (*text != '\0') {
        unsigned char character;
        int glyph;

        character = (unsigned char)*text++;
        if (character == ' ') {
            width += 4;
        } else if (character >= ' ') {
            glyph = letter_table[character - ' '];
            if (glyph != 0) {
                width += (int)read_u16(font + (glyph - 1) * 16 + 8) + 1;
            }
        }
    }
    return width;
}

int my_strcmp(char *first, char *second, int count)
{
    int i;

    for (i = 0; i < count; i++) {
        if (second[i] != first[i]) return i + 1;
    }
    return 0;
}

int get_number_from_text(char *text)
{
    int value;

    value = 0;
    while (*text >= '0' && *text <= '9') {
        value = value * 10 + (*text - '0');
        text++;
    }
    return value;
}

static int get_letter_width(int letter, unsigned char *font)
{
    int glyph;

    if (letter == ' ') return 4;
    glyph = letter_table[(unsigned char)letter - ' '];
    if (glyph == 0) return 0;
    return (int)read_u16(font + (glyph - 1) * 16 + 8) + 1;
}

int get_next_word_length(char *text, unsigned char *font)
{
    int width;
    int started;
    int i;
    unsigned char character;

    char_count = 0;
    width = 0;
    started = 0;
    for (i = 0; i < 0x7cf; i++) {
        character = (unsigned char)*text++;
        if (character == 0) break;
        if (character == ' ') {
            if (started) break;
            width += 4;
        } else if (character == '$') {
            if (started) break;
        } else if (character >= ' ') {
            width += get_letter_width(character, font);
            started = 1;
        }
        char_count++;
    }
    return width;
}

int one_letter(unsigned char *font, unsigned char letter)
{
    int y;

    y = sprite_y;
    if (font == font1 &&
        ((letter >= 'a' && letter <= 'm') ||
         (letter >= 's' && letter <= 'w') ||
         (letter >= 0x80 && letter <= 0x84))) {
        y--;
    }
    return draw_glyph(font, letter, sprite_x, y, sprite_colour);
}

void font_centre(int entry_idx, int word_count, int x, int y,
                 int width, unsigned char *font, int color)
{
    const char *text;
    int offset;

    text = get_text(entry_idx, word_count);
    offset = (width - get_string_width((char *)text, font)) / 2;
    if (offset < 0) offset = 0;
    draw_text((const unsigned char *)text, x + offset, y, font, color);
}

void font_no(int value, char pad_char, char *suffix, int x,
             int y, unsigned char *font, int color)
{
    char number[32];

    if (pad_char == ' ') {
        snprintf(number, sizeof(number), "%d%s", value, suffix);
    } else {
        snprintf(number, sizeof(number), "%010d%s", value, suffix);
    }
    draw_text((const unsigned char *)number, x, y, font, color);
}

void draw_a_box(int x, int y, int width, int height, int color)
{
    int i;

    for (i = 0; i < width; i++) {
        internal_screen[y * screen_width + x + i] = (unsigned char)color;
        internal_screen[(y + height - 1) * screen_width + x + i] = (unsigned char)color;
    }
    for (i = 0; i < height; i++) {
        internal_screen[(y + i) * screen_width + x] = (unsigned char)color;
        internal_screen[(y + i) * screen_width + x + width - 1] = (unsigned char)color;
    }
}

void flush_sb_buffer(void)
{
    sb_cm_undo_flushed = 1;
    sb_rm_undo_flushed = 1;
}
