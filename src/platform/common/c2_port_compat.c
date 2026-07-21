#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"

static unsigned char expand_vga_channel(unsigned char channel)
{
    return (unsigned char)((channel << 2) | (channel >> 4));
}

static char c2_language_filename[13];
static char c2_media_filename[13];

static void publish_frame(void)
{
    c2_host_publish_indexed_frame(internal_screen,
                                  C2_SCREEN_WIDTH,
                                  C2_SCREEN_HEIGHT,
                                  C2_SCREEN_WIDTH,
                                  current_palette,
                                  C2_PALETTE_BYTES);
}

int c2_port_compat_init(void)
{
    lang_file = c2_language_filename;
    media_file = c2_media_filename;
    return 1;
}

void c2_port_compat_shutdown(void)
{
}

int readfile(const char *filename, void *buffer, int size, int offset)
{
    if (size < 0 || offset < 0) {
        return 0;
    }
    return (int)c2_host_asset_read(filename, buffer,
                                   (size_t)size, (size_t)offset);
}

int check_file_exists(char *filename)
{
    unsigned char byte;

    return c2_host_asset_read(filename, &byte, 1, 0) != 0;
}

void get_directory(char *pattern)
{
    (void)pattern;
    no_of_entries = 0;
    first_entry = 0;
}

int is_file_on_harddrive(char *filename)
{
    return check_file_exists(filename);
}

int writefile(const char *filename, char *buffer, int size)
{
    if (size < 0) return 0;
    return c2_host_user_file_write(filename, buffer, (size_t)size) ? size : 0;
}

int read_userfile(const char *filename, void *buffer, int size, int offset)
{
    if (size < 0 || offset < 0) return 0;
    return (int)c2_host_user_file_read(filename, buffer,
                                      (size_t)size, (size_t)offset);
}

int write_to_file(char *filename, char *buffer, int size, int offset)
{
    if (size < 0 || offset < 0) return 0;
    return c2_host_user_file_write_at(filename, buffer,
                                      (size_t)size, (size_t)offset)
        ? size : 0;
}

char read_config(char *filename, char *buffer)
{
    (void)filename;
    (void)buffer;
    return 0;
}

int set_svga_640_480(int mode)
{
    (void)mode;
    return 0;
}

void set_vga_palette(char *palette)
{
    memcpy(current_palette, palette, C2_PALETTE_BYTES);
    publish_frame();
}

void set_vga_palette_range(char *palette, int start, int end)
{
    size_t offset;
    size_t size;

    if (start < 0 || end < start || end >= 256) return;
    offset = (size_t)start * 3;
    size = (size_t)(end - start + 1) * 3;
    memcpy(current_palette + offset, palette, size);
    publish_frame();
}

void clear_all_screens(void)
{
}

void refresh_svga_screen(void)
{
    int tile_idx;

    for (tile_idx = 0; tile_idx < 1200; tile_idx++) {
        if (svga_refresh_table[tile_idx] != 0) {
            refresh_count++;
            svga_refresh_table[tile_idx]--;
        }
    }
    publish_frame();
    c2_port_wait_for_frame();
}

int c2_port_save_screenshot(const char *filename)
{
    unsigned char *ppm;
    size_t header_size;
    size_t ppm_size;
    int header_length;
    int i;

    if (internal_screen == NULL) return 0;
    header_length = snprintf(NULL, 0, "P6\n%d %d\n255\n",
                             C2_SCREEN_WIDTH, C2_SCREEN_HEIGHT);
    if (header_length < 0) {
        return 0;
    }
    header_size = (size_t)header_length;
    ppm_size = header_size + C2_SCREEN_PIXELS * 3;
    ppm = malloc(ppm_size);
    if (ppm == NULL) {
        return 0;
    }
    snprintf((char *)ppm, header_size + 1, "P6\n%d %d\n255\n",
             C2_SCREEN_WIDTH, C2_SCREEN_HEIGHT);

    for (i = 0; i < C2_SCREEN_PIXELS; i++) {
        unsigned int palette_offset;
        size_t pixel_offset;

        palette_offset = (unsigned int)internal_screen[i] * 3;
        pixel_offset = header_size + (size_t)i * 3;
        ppm[pixel_offset] = expand_vga_channel(current_palette[palette_offset]);
        ppm[pixel_offset + 1] = expand_vga_channel(current_palette[palette_offset + 1]);
        ppm[pixel_offset + 2] = expand_vga_channel(current_palette[palette_offset + 2]);
    }

    i = c2_host_user_file_write(filename, ppm, ppm_size);
    free(ppm);
    return i;
}
