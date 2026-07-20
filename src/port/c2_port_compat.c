#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_host.h"
#include "c2_port.h"

unsigned char current_palette[C2_PALETTE_BYTES];
char temp_palette[C2_PALETTE_BYTES];
unsigned char *internal_screen;
int screen_width = C2_SCREEN_WIDTH;
int screen_height = C2_SCREEN_HEIGHT;
int screen_size = C2_SCREEN_PIXELS;

static unsigned char expand_vga_channel(unsigned char channel)
{
    return (unsigned char)((channel << 2) | (channel >> 4));
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
    internal_screen = calloc(C2_SCREEN_PIXELS, sizeof(*internal_screen));
    if (internal_screen == NULL) {
        fprintf(stderr, "could not allocate the Caesar II framebuffer\n");
        return 0;
    }
    memset(current_palette, 0, sizeof(current_palette));
    memset(temp_palette, 0, sizeof(temp_palette));
    publish_frame();
    return 1;
}

void c2_port_compat_shutdown(void)
{
    free(internal_screen);
    internal_screen = NULL;
}

int readfile(const char *filename, void *buffer, int size, int offset)
{
    if (size < 0 || offset < 0) {
        return 0;
    }
    return (int)c2_host_asset_read(filename, buffer,
                                   (size_t)size, (size_t)offset);
}

void refresh_svga_screen(void)
{
    publish_frame();
}

void fade_to_palette(char *palette)
{
    memcpy(current_palette, palette, C2_PALETTE_BYTES);
    current_palette[0] = 0;
    current_palette[1] = 0;
    current_palette[2] = 0;
    publish_frame();
}

void set_palette(char *palette)
{
    fade_to_palette(palette);
}

void black_out(void)
{
    memset(current_palette, 0, C2_PALETTE_BYTES);
    publish_frame();
}

int c2_port_save_screenshot(const char *filename)
{
    unsigned char *ppm;
    size_t header_size;
    size_t ppm_size;
    int header_length;
    int i;

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

uint64_t c2_port_frame_hash(void)
{
    uint64_t hash;
    int i;

    hash = UINT64_C(14695981039346656037);
    for (i = 0; i < C2_SCREEN_PIXELS; i++) {
        hash ^= internal_screen[i];
        hash *= UINT64_C(1099511628211);
    }
    for (i = 0; i < C2_PALETTE_BYTES; i++) {
        hash ^= current_palette[i];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}
