#include <stddef.h>
#include <string.h>

#include "c2_data.h"
#include "c2_port.h"

#define C2_FONT1_BYTES 9460
#define C2_FONT2_BYTES 28248
#define C2_SYSTEM_PANEL_BYTES 41672
#define C2_TEXT_BUFFER_BYTES 40000
#define C2_MISC_BYTES 3584

unsigned char font1[C2_FONT1_BYTES];
unsigned char font2[C2_FONT2_BYTES];
unsigned char system_panel[C2_SYSTEM_PANEL_BYTES];
char text_buffer[C2_TEXT_BUFFER_BYTES];

unsigned char hold_mouse_replace;
int sprite_image_no;
int sprite_x;
int sprite_y;
int x_is;
struct c2inf_rec c2inf;

extern int readfile(const char *filename, void *buffer, int size, int offset);

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

int c2_port_load_startup_ui(void)
{
    if (readfile("font_c2.pl8", font1, sizeof(font1), 0) == 0) return 0;
    if (readfile("font3c2.pl8", font2, sizeof(font2), 0) == 0) return 0;
    if (readfile("system.pl8", system_panel, sizeof(system_panel), 0) == 0) return 0;
    if (readfile("misc.pl8", misc, C2_MISC_BYTES, 0) == 0) return 0;
    if (readfile("c2.eng", text_buffer, sizeof(text_buffer), 0) == 0) return 0;
    memcpy(c2inf.player_name, "Octavian", sizeof("Octavian"));
    c2inf.skill_level = 0;
    c2inf.peace_mode = 0;
    return 1;
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

void cover_mouse_droppings(void)
{
    hold_mouse_replace = 0;
}

void flush_sb_buffer(void)
{
}

void test_beeps(void)
{
}

void act_tutorial(void)
{
}

void act_preload(void)
{
}

void act_out(void)
{
}

void act_dos(void)
{
}

void act_skill_down(void)
{
}

void act_skill_up(void)
{
}

void act_tog_peace(void)
{
}

void act_choose_name(void)
{
}

void act_back_to_front_panel(void)
{
}
