#include <SDL3/SDL.h>

#include <ctype.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_sdl_platform.h"

#define C2_SCREEN_WIDTH 640
#define C2_SCREEN_HEIGHT 480
#define C2_SCREEN_PIXELS (C2_SCREEN_WIDTH * C2_SCREEN_HEIGHT)
#define C2_PALETTE_BYTES (256 * 3)
#define C2_PATH_CAPACITY 4096

unsigned char current_palette[C2_PALETTE_BYTES];
char temp_palette[C2_PALETTE_BYTES];
unsigned char *internal_screen;
int screen_width = C2_SCREEN_WIDTH;
int screen_height = C2_SCREEN_HEIGHT;
int screen_size = C2_SCREEN_PIXELS;

static SDL_Window *c2_window;
static SDL_Renderer *c2_renderer;
static SDL_Texture *c2_texture;
static uint32_t *c2_rgba_screen;
static char c2_data_dir[C2_PATH_CAPACITY];
static int c2_headless;
static int c2_frame_dirty;

static int build_asset_path(char *path, size_t capacity, const char *filename, int uppercase)
{
    size_t root_length;
    size_t i;
    int length;

    root_length = strlen(c2_data_dir);
    length = snprintf(path, capacity, "%s%s%s", c2_data_dir,
                      root_length != 0 && c2_data_dir[root_length - 1] == '/' ? "" : "/",
                      filename);
    if (length < 0 || (size_t)length >= capacity) {
        return 0;
    }

    if (uppercase) {
        for (i = root_length; path[i] != '\0'; i++) {
            path[i] = (char)toupper((unsigned char)path[i]);
        }
    }

    return 1;
}

static FILE *open_asset(const char *filename)
{
    char path[C2_PATH_CAPACITY];
    FILE *file;

    if (!build_asset_path(path, sizeof(path), filename, 0)) {
        return NULL;
    }
    file = fopen(path, "rb");
    if (file != NULL) {
        return file;
    }

    if (!build_asset_path(path, sizeof(path), filename, 1)) {
        return NULL;
    }
    return fopen(path, "rb");
}

static unsigned char expand_vga_channel(unsigned char channel)
{
    return (unsigned char)((channel << 2) | (channel >> 4));
}

static void update_texture(void)
{
    int i;

    if (!c2_frame_dirty || c2_headless) {
        return;
    }

    for (i = 0; i < C2_SCREEN_PIXELS; i++) {
        unsigned int palette_offset;
        unsigned int red;
        unsigned int green;
        unsigned int blue;

        palette_offset = (unsigned int)internal_screen[i] * 3;
        red = expand_vga_channel(current_palette[palette_offset]);
        green = expand_vga_channel(current_palette[palette_offset + 1]);
        blue = expand_vga_channel(current_palette[palette_offset + 2]);
        c2_rgba_screen[i] = (red << 16) | (green << 8) | blue;
    }

    SDL_UpdateTexture(c2_texture, NULL, c2_rgba_screen,
                      C2_SCREEN_WIDTH * (int)sizeof(*c2_rgba_screen));
    c2_frame_dirty = 0;
}

int c2_sdl_platform_init(const char *data_dir, int headless)
{
    size_t data_dir_length;

    data_dir_length = strlen(data_dir);
    if (data_dir_length == 0 || data_dir_length >= sizeof(c2_data_dir)) {
        fprintf(stderr, "invalid Caesar II data directory\n");
        return 0;
    }
    memcpy(c2_data_dir, data_dir, data_dir_length + 1);

    internal_screen = calloc(C2_SCREEN_PIXELS, sizeof(*internal_screen));
    c2_rgba_screen = calloc(C2_SCREEN_PIXELS, sizeof(*c2_rgba_screen));
    if (internal_screen == NULL || c2_rgba_screen == NULL) {
        fprintf(stderr, "could not allocate the Caesar II framebuffer\n");
        c2_sdl_platform_shutdown();
        return 0;
    }

    c2_headless = headless;
    c2_frame_dirty = 1;
    if (headless) {
        return 1;
    }

    if (!SDL_Init(SDL_INIT_VIDEO)) {
        fprintf(stderr, "SDL video initialization failed: %s\n", SDL_GetError());
        c2_sdl_platform_shutdown();
        return 0;
    }
    if (!SDL_CreateWindowAndRenderer("Caesar II", 1280, 960,
                                     SDL_WINDOW_RESIZABLE,
                                     &c2_window, &c2_renderer)) {
        fprintf(stderr, "SDL window creation failed: %s\n", SDL_GetError());
        c2_sdl_platform_shutdown();
        return 0;
    }
    if (!SDL_SetRenderLogicalPresentation(c2_renderer,
                                          C2_SCREEN_WIDTH,
                                          C2_SCREEN_HEIGHT,
                                          SDL_LOGICAL_PRESENTATION_LETTERBOX)) {
        fprintf(stderr, "SDL logical presentation failed: %s\n", SDL_GetError());
        c2_sdl_platform_shutdown();
        return 0;
    }

    c2_texture = SDL_CreateTexture(c2_renderer,
                                   SDL_PIXELFORMAT_XRGB8888,
                                   SDL_TEXTUREACCESS_STREAMING,
                                   C2_SCREEN_WIDTH,
                                   C2_SCREEN_HEIGHT);
    if (c2_texture == NULL) {
        fprintf(stderr, "SDL texture creation failed: %s\n", SDL_GetError());
        c2_sdl_platform_shutdown();
        return 0;
    }
    if (!SDL_SetTextureScaleMode(c2_texture, SDL_SCALEMODE_NEAREST)) {
        fprintf(stderr, "SDL texture scaling setup failed: %s\n", SDL_GetError());
        c2_sdl_platform_shutdown();
        return 0;
    }

    SDL_SetRenderDrawColor(c2_renderer, 0, 0, 0, 255);
    return 1;
}

void c2_sdl_platform_shutdown(void)
{
    SDL_DestroyTexture(c2_texture);
    SDL_DestroyRenderer(c2_renderer);
    SDL_DestroyWindow(c2_window);
    c2_texture = NULL;
    c2_renderer = NULL;
    c2_window = NULL;

    free(c2_rgba_screen);
    free(internal_screen);
    c2_rgba_screen = NULL;
    internal_screen = NULL;

    SDL_Quit();
}

void c2_sdl_platform_present(void)
{
    if (c2_headless || c2_renderer == NULL) {
        return;
    }

    update_texture();
    SDL_RenderClear(c2_renderer);
    SDL_RenderTexture(c2_renderer, c2_texture, NULL, NULL);
    SDL_RenderPresent(c2_renderer);
}

uint64_t c2_sdl_title_hash(void)
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

int readfile(const char *filename, void *buffer, int size, int offset)
{
    FILE *file;
    size_t bytes_read;

    file = open_asset(filename);
    if (file == NULL) {
        return 0;
    }
    if (fseek(file, offset, SEEK_SET) != 0) {
        fclose(file);
        return 0;
    }

    bytes_read = fread(buffer, 1, (size_t)size, file);
    fclose(file);
    return (int)bytes_read;
}

void refresh_svga_screen(void)
{
    c2_frame_dirty = 1;
    c2_sdl_platform_present();
}

void fade_to_palette(char *palette)
{
    memcpy(current_palette, palette, C2_PALETTE_BYTES);
    current_palette[0] = 0;
    current_palette[1] = 0;
    current_palette[2] = 0;
    c2_frame_dirty = 1;
    c2_sdl_platform_present();
}
