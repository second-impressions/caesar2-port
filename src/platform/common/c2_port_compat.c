#include <string.h>
#include <stdlib.h>

#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"
#include "c2_port_save.h"

static char c2_language_filename[13];
static char c2_media_filename[13];

#define C2_ASSET_SIZE_LIMIT (512u * 1024u * 1024u)

void *c2_port_load_asset(const char *filename, size_t *size_out)
{
    unsigned char *data;
    uint64_t size64;
    size_t size;

    if (filename == NULL || size_out == NULL) return NULL;
    size64 = c2_host_asset_size(filename);
    if (size64 == 0 || size64 > C2_ASSET_SIZE_LIMIT ||
        size64 > (uint64_t)SIZE_MAX) return NULL;
    size = (size_t)size64;
    data = malloc(size);
    if (data == NULL) return NULL;
    if (c2_host_asset_read(filename, data, size, 0) != size) {
        free(data);
        return NULL;
    }
    *size_out = size;
    return data;
}

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
    if (!c2_port_save_registry_valid(savegame_entries, 500,
                                     figure_list, arrow_list)) {
        return 0;
    }
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
    no_of_entries = (int)c2_host_user_file_list(pattern,
                                                (char *)directory,
                                                sizeof(directory[0]),
                                                C2_DIRECTORY_MAX_ENTRIES);
    first_entry = 0;
}

int check_user_file_exists(const char *filename)
{
    return c2_host_user_file_exists(filename);
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
    if (internal_screen == NULL) return 0;
    return c2_host_save_indexed_png(filename,
                                    internal_screen,
                                    C2_SCREEN_WIDTH,
                                    C2_SCREEN_HEIGHT,
                                    C2_SCREEN_WIDTH,
                                    current_palette,
                                    C2_PALETTE_BYTES);
}
