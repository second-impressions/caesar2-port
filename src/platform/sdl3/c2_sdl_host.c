#include <SDL3/SDL.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "c2_host.h"
#include "c2_sdl_host.h"

#define C2_PATH_CAPACITY 4096
#define C2_PALETTE_BYTES (256 * 3)
#define C2_EVENT_QUEUE_CAPACITY 64

static SDL_Window *c2_window;
static SDL_Renderer *c2_renderer;
static SDL_Texture *c2_texture;
static SDL_Mutex *c2_frame_mutex;
static SDL_Mutex *c2_event_mutex;
static SDL_Condition *c2_event_condition;
static uint32_t *c2_rgba_frame;
static unsigned char *c2_indexed_frame;
static unsigned char *c2_present_frame;
static unsigned char c2_palette[C2_PALETTE_BYTES];
static unsigned char c2_present_palette[C2_PALETTE_BYTES];
static struct c2_host_event c2_event_queue[C2_EVENT_QUEUE_CAPACITY];
static struct c2_host_input c2_input;
#if C2_FEAT_DEBUG_OBSERVATION
static struct c2_observation c2_observation;
#endif
static char c2_asset_root[C2_PATH_CAPACITY];
static char c2_user_data_root[C2_PATH_CAPACITY];
static int c2_frame_width;
static int c2_frame_height;
static int c2_headless;
static int c2_frame_dirty;
static int c2_event_read;
static int c2_event_count;
static int c2_shutdown;
#if C2_FEAT_DEBUG_OBSERVATION
static int c2_observation_enabled;
#endif

static int copy_root(char *destination, size_t capacity, const char *root)
{
    size_t length;

    length = strlen(root);
    if (length == 0 || length >= capacity) {
        return 0;
    }
    memcpy(destination, root, length + 1);
    return 1;
}

static int is_safe_relative_path(const char *filename)
{
    const char *component;
    const char *cursor;

    if (filename[0] == '\0' || filename[0] == '/' || filename[0] == '\\' ||
        strchr(filename, ':') != NULL) {
        return 0;
    }
    component = filename;
    for (cursor = filename;; cursor++) {
        if (*cursor == '/' || *cursor == '\\' || *cursor == '\0') {
            if (cursor - component == 2 && component[0] == '.' &&
                component[1] == '.') {
                return 0;
            }
            if (*cursor == '\0') {
                break;
            }
            component = cursor + 1;
        }
    }
    return 1;
}

static int build_path(char *path, size_t capacity, const char *root,
                      const char *filename, int uppercase)
{
    size_t root_length;
    size_t i;
    int length;

    if (!is_safe_relative_path(filename)) {
        return 0;
    }
    root_length = strlen(root);
    length = snprintf(path, capacity, "%s%s%s", root,
                      root_length != 0 && root[root_length - 1] == '/'
                          ? "" : "/",
                      filename);
    if (length < 0 || (size_t)length >= capacity) {
        return 0;
    }

    for (i = root_length; path[i] != '\0'; i++) {
        if (path[i] == '\\') {
            path[i] = '/';
        }
        if (uppercase) {
            path[i] = (char)toupper((unsigned char)path[i]);
        }
    }
    return 1;
}

static FILE *open_asset(const char *filename)
{
    char path[C2_PATH_CAPACITY];
    FILE *file;

    if (!build_path(path, sizeof(path), c2_asset_root, filename, 0)) {
        return NULL;
    }
    file = fopen(path, "rb");
    if (file != NULL) {
        return file;
    }
    if (!build_path(path, sizeof(path), c2_asset_root, filename, 1)) {
        return NULL;
    }
    return fopen(path, "rb");
}

static unsigned char expand_vga_channel(unsigned char channel)
{
    return (unsigned char)((channel << 2) | (channel >> 4));
}

static enum c2_host_key translate_key(SDL_Keycode key)
{
    if (key == SDLK_ESCAPE) return C2_HOST_KEY_ESCAPE;
    if (key == SDLK_RETURN) return C2_HOST_KEY_RETURN;
    if (key == SDLK_SPACE) return C2_HOST_KEY_SPACE;
    if (key == SDLK_LEFT) return C2_HOST_KEY_LEFT;
    if (key == SDLK_RIGHT) return C2_HOST_KEY_RIGHT;
    if (key == SDLK_P) return C2_HOST_KEY_P;
    if (key == SDLK_F) return C2_HOST_KEY_F;
    if (key == SDLK_MINUS) return C2_HOST_KEY_MINUS;
    return C2_HOST_KEY_UNKNOWN;
}

static unsigned int translate_mouse_button(Uint8 button)
{
    if (button == SDL_BUTTON_LEFT) return C2_HOST_MOUSE_LEFT;
    if (button == SDL_BUTTON_RIGHT) return C2_HOST_MOUSE_RIGHT;
    if (button == SDL_BUTTON_MIDDLE) return C2_HOST_MOUSE_MIDDLE;
    return 0;
}

static void queue_event(const struct c2_host_event *event)
{
    int write_index;

    SDL_LockMutex(c2_event_mutex);
    if (c2_event_count == C2_EVENT_QUEUE_CAPACITY) {
        c2_event_read = (c2_event_read + 1) % C2_EVENT_QUEUE_CAPACITY;
        c2_event_count--;
    }
    write_index = (c2_event_read + c2_event_count) % C2_EVENT_QUEUE_CAPACITY;
    c2_event_queue[write_index] = *event;
    c2_event_count++;
    SDL_SignalCondition(c2_event_condition);
    SDL_UnlockMutex(c2_event_mutex);
}

int c2_host_init(const struct c2_host_config *config)
{
    SDL_InitFlags flags;
    size_t pixel_count;

    if (config == NULL || config->logical_width <= 0 ||
        config->logical_height <= 0 || config->window_scale <= 0 ||
        !copy_root(c2_asset_root, sizeof(c2_asset_root), config->asset_root) ||
        !copy_root(c2_user_data_root, sizeof(c2_user_data_root),
                   config->user_data_root)) {
        fprintf(stderr, "invalid Caesar II host configuration\n");
        return 0;
    }

    flags = SDL_INIT_EVENTS;
    if (!config->headless) {
        flags |= SDL_INIT_VIDEO;
    }
    if (!SDL_Init(flags)) {
        fprintf(stderr, "SDL initialization failed: %s\n", SDL_GetError());
        return 0;
    }

    c2_frame_width = config->logical_width;
    c2_frame_height = config->logical_height;
    c2_headless = config->headless;
    c2_frame_dirty = 0;
    c2_event_read = 0;
    c2_event_count = 0;
    c2_shutdown = 0;
#if C2_FEAT_DEBUG_OBSERVATION
    c2_observation_enabled = config->enable_observation;
#endif
    memset(&c2_input, 0, sizeof(c2_input));
#if C2_FEAT_DEBUG_OBSERVATION
    memset(&c2_observation, 0, sizeof(c2_observation));
#endif
    c2_input.focused = 1;
    pixel_count = (size_t)c2_frame_width * (size_t)c2_frame_height;
    c2_indexed_frame = calloc(pixel_count, sizeof(*c2_indexed_frame));
    c2_present_frame = calloc(pixel_count, sizeof(*c2_present_frame));
    c2_rgba_frame = calloc(pixel_count, sizeof(*c2_rgba_frame));
    c2_frame_mutex = SDL_CreateMutex();
    c2_event_mutex = SDL_CreateMutex();
    c2_event_condition = SDL_CreateCondition();
    if (c2_indexed_frame == NULL || c2_present_frame == NULL ||
        c2_rgba_frame == NULL ||
        c2_frame_mutex == NULL || c2_event_mutex == NULL ||
        c2_event_condition == NULL) {
        fprintf(stderr, "could not allocate Caesar II host state: %s\n",
                SDL_GetError());
        c2_host_shutdown();
        return 0;
    }

    if (config->headless) {
        return 1;
    }
    if (!SDL_CreateWindowAndRenderer(config->title,
                                     c2_frame_width * config->window_scale,
                                     c2_frame_height * config->window_scale,
                                     SDL_WINDOW_RESIZABLE,
                                     &c2_window, &c2_renderer)) {
        fprintf(stderr, "SDL window creation failed: %s\n", SDL_GetError());
        c2_host_shutdown();
        return 0;
    }
    if (!SDL_SetRenderLogicalPresentation(c2_renderer,
                                          c2_frame_width,
                                          c2_frame_height,
                                          SDL_LOGICAL_PRESENTATION_LETTERBOX)) {
        fprintf(stderr, "SDL logical presentation failed: %s\n", SDL_GetError());
        c2_host_shutdown();
        return 0;
    }
    c2_texture = SDL_CreateTexture(c2_renderer,
                                   SDL_PIXELFORMAT_XRGB8888,
                                   SDL_TEXTUREACCESS_STREAMING,
                                   c2_frame_width, c2_frame_height);
    if (c2_texture == NULL ||
        !SDL_SetTextureScaleMode(c2_texture, SDL_SCALEMODE_NEAREST)) {
        fprintf(stderr, "SDL texture setup failed: %s\n", SDL_GetError());
        c2_host_shutdown();
        return 0;
    }
    SDL_SetRenderDrawColor(c2_renderer, 0, 0, 0, 255);
    return 1;
}

void c2_host_shutdown(void)
{
    SDL_DestroyCondition(c2_event_condition);
    SDL_DestroyMutex(c2_event_mutex);
    SDL_DestroyMutex(c2_frame_mutex);
    SDL_DestroyTexture(c2_texture);
    SDL_DestroyRenderer(c2_renderer);
    SDL_DestroyWindow(c2_window);
    c2_event_condition = NULL;
    c2_event_mutex = NULL;
    c2_frame_mutex = NULL;
    c2_texture = NULL;
    c2_renderer = NULL;
    c2_window = NULL;

    free(c2_rgba_frame);
    free(c2_present_frame);
    free(c2_indexed_frame);
    c2_rgba_frame = NULL;
    c2_present_frame = NULL;
    c2_indexed_frame = NULL;
    SDL_Quit();
}

uint64_t c2_host_ticks_ms(void)
{
    return SDL_GetTicks();
}

uint64_t c2_host_wall_time_seconds(void)
{
    return (uint64_t)time(NULL);
}

void c2_host_sleep_ms(unsigned int milliseconds)
{
    SDL_Delay(milliseconds);
}

void c2_host_wait_until_ms(uint64_t deadline_ms)
{
    uint64_t now;
    uint64_t remaining;
    Sint32 timeout;

    SDL_LockMutex(c2_event_mutex);
    while (!c2_shutdown) {
        now = SDL_GetTicks();
        if (now >= deadline_ms) break;
        remaining = deadline_ms - now;
        timeout = remaining > INT32_MAX ? INT32_MAX : (Sint32)remaining;
        SDL_WaitConditionTimeout(c2_event_condition, c2_event_mutex, timeout);
    }
    SDL_UnlockMutex(c2_event_mutex);
}

int c2_host_has_capability(enum c2_host_capability capability)
{
    (void)capability;
    return 0;
}

size_t c2_host_asset_read(const char *filename, void *buffer,
                          size_t size, size_t offset)
{
    FILE *file;
    size_t bytes_read;

    file = open_asset(filename);
    if (file == NULL) {
        return 0;
    }
    if (fseek(file, (long)offset, SEEK_SET) != 0) {
        fclose(file);
        return 0;
    }
    bytes_read = fread(buffer, 1, size, file);
    fclose(file);
    return bytes_read;
}

int c2_host_user_file_write(const char *filename, const void *buffer,
                            size_t size)
{
    char path[C2_PATH_CAPACITY];
    FILE *file;
    int ok;

    if (!build_path(path, sizeof(path), c2_user_data_root, filename, 0)) {
        return 0;
    }
    file = fopen(path, "wb");
    if (file == NULL) {
        return 0;
    }
    ok = fwrite(buffer, 1, size, file) == size;
    if (fclose(file) != 0) {
        ok = 0;
    }
    return ok;
}

size_t c2_host_user_file_read(const char *filename, void *buffer,
                              size_t size, size_t offset)
{
    char path[C2_PATH_CAPACITY];
    FILE *file;
    size_t bytes_read;

    if (!build_path(path, sizeof(path), c2_user_data_root, filename, 0)) {
        return 0;
    }
    file = fopen(path, "rb");
    if (file == NULL || fseek(file, (long)offset, SEEK_SET) != 0) {
        if (file != NULL) fclose(file);
        return 0;
    }
    bytes_read = fread(buffer, 1, size, file);
    fclose(file);
    return bytes_read;
}

int c2_host_user_file_write_at(const char *filename, const void *buffer,
                               size_t size, size_t offset)
{
    char path[C2_PATH_CAPACITY];
    FILE *file;
    int ok;

    if (!build_path(path, sizeof(path), c2_user_data_root, filename, 0)) {
        return 0;
    }
    file = fopen(path, "r+b");
    if (file == NULL) file = fopen(path, "wb");
    if (file == NULL || fseek(file, (long)offset, SEEK_SET) != 0) {
        if (file != NULL) fclose(file);
        return 0;
    }
    ok = fwrite(buffer, 1, size, file) == size;
    if (fclose(file) != 0) ok = 0;
    return ok;
}

int c2_host_publish_indexed_frame(const unsigned char *pixels,
                                  int width, int height, int pitch,
                                  const unsigned char *palette,
                                  size_t palette_size)
{
    int row;

    if (pixels == NULL || palette == NULL || width != c2_frame_width ||
        height != c2_frame_height || pitch < width ||
        palette_size != C2_PALETTE_BYTES) {
        return 0;
    }

    SDL_LockMutex(c2_frame_mutex);
    for (row = 0; row < height; row++) {
        memcpy(c2_indexed_frame + (size_t)row * (size_t)width,
               pixels + (size_t)row * (size_t)pitch,
               (size_t)width);
    }
    memcpy(c2_palette, palette, sizeof(c2_palette));
    c2_frame_dirty = 1;
    SDL_UnlockMutex(c2_frame_mutex);
    return 1;
}

void c2_host_present(void)
{
    size_t pixel_count;
    size_t i;
    int have_frame;

    if (c2_headless || c2_renderer == NULL) {
        return;
    }

    pixel_count = (size_t)c2_frame_width * (size_t)c2_frame_height;
    SDL_LockMutex(c2_frame_mutex);
    have_frame = c2_frame_dirty;
    if (have_frame) {
        memcpy(c2_present_frame, c2_indexed_frame, pixel_count);
        memcpy(c2_present_palette, c2_palette, sizeof(c2_present_palette));
        c2_frame_dirty = 0;
    }
    SDL_UnlockMutex(c2_frame_mutex);

    if (have_frame) {
        for (i = 0; i < pixel_count; i++) {
            unsigned int palette_offset;
            unsigned int red;
            unsigned int green;
            unsigned int blue;

            palette_offset = (unsigned int)c2_present_frame[i] * 3;
            red = expand_vga_channel(c2_present_palette[palette_offset]);
            green = expand_vga_channel(c2_present_palette[palette_offset + 1]);
            blue = expand_vga_channel(c2_present_palette[palette_offset + 2]);
            c2_rgba_frame[i] = (red << 16) | (green << 8) | blue;
        }
        SDL_UpdateTexture(c2_texture, NULL, c2_rgba_frame,
                          c2_frame_width * (int)sizeof(*c2_rgba_frame));
    }

    SDL_RenderClear(c2_renderer);
    SDL_RenderTexture(c2_renderer, c2_texture, NULL, NULL);
    SDL_RenderPresent(c2_renderer);
}

int c2_host_wait_event(struct c2_host_event *event,
                       unsigned int timeout_ms)
{
    int got_event;

    SDL_LockMutex(c2_event_mutex);
    if (c2_event_count == 0 && !c2_shutdown && timeout_ms != 0) {
        SDL_WaitConditionTimeout(c2_event_condition, c2_event_mutex,
                                 (Sint32)timeout_ms);
    }
    got_event = c2_event_count != 0;
    if (got_event) {
        *event = c2_event_queue[c2_event_read];
        c2_event_read = (c2_event_read + 1) % C2_EVENT_QUEUE_CAPACITY;
        c2_event_count--;
    }
    SDL_UnlockMutex(c2_event_mutex);
    return got_event;
}

void c2_host_input_snapshot(struct c2_host_input *input)
{
    SDL_LockMutex(c2_event_mutex);
    *input = c2_input;
    SDL_UnlockMutex(c2_event_mutex);
}

void c2_host_request_shutdown(void)
{
    SDL_LockMutex(c2_event_mutex);
    c2_shutdown = 1;
    c2_input.quit_requested = 1;
    c2_input.generation++;
    SDL_BroadcastCondition(c2_event_condition);
    SDL_UnlockMutex(c2_event_mutex);
}

int c2_host_shutdown_requested(void)
{
    int shutdown;

    SDL_LockMutex(c2_event_mutex);
    shutdown = c2_shutdown;
    SDL_UnlockMutex(c2_event_mutex);
    return shutdown;
}

#if C2_FEAT_DEBUG_OBSERVATION
void c2_host_publish_observation(const struct c2_observation *observation)
{
    if (!c2_observation_enabled) return;
    SDL_LockMutex(c2_event_mutex);
    c2_observation.sequence++;
    if (observation->point > C2_OBSERVATION_NONE &&
        observation->point < 64) {
        c2_observation.reached |= UINT64_C(1) << observation->point;
    }
    c2_observation.point = observation->point;
    c2_observation.detail = observation->detail;
    c2_observation.province = observation->province;
    c2_observation.map_mode = observation->map_mode;
    c2_observation.zoom_level = observation->zoom_level;
    c2_observation.paused = observation->paused;
    c2_observation.peace_mode = observation->peace_mode;
    c2_observation.in_forum = observation->in_forum;
    c2_observation.map_x = observation->map_x;
    c2_observation.map_y = observation->map_y;
    SDL_UnlockMutex(c2_event_mutex);
}

void c2_host_observation_snapshot(struct c2_observation *observation)
{
    SDL_LockMutex(c2_event_mutex);
    *observation = c2_observation;
    SDL_UnlockMutex(c2_event_mutex);
}
#endif

#if C2_FEAT_DEBUG_OBSERVATION
void c2_sdl_host_set_headless_mouse(int x, int y, unsigned int buttons)
{
    SDL_LockMutex(c2_event_mutex);
    c2_input.mouse_x = x;
    c2_input.mouse_y = y;
    c2_input.mouse_buttons = buttons;
    c2_input.generation++;
    SDL_UnlockMutex(c2_event_mutex);
}

void c2_sdl_host_push_headless_key(enum c2_host_key key)
{
    struct c2_host_event event;

    memset(&event, 0, sizeof(event));
    event.type = C2_HOST_EVENT_KEY_DOWN;
    event.key = key;
    queue_event(&event);
}
#endif

void c2_sdl_host_handle_event(SDL_Event *event)
{
    struct c2_host_event host_event;
    int publish;

    memset(&host_event, 0, sizeof(host_event));
    publish = 0;
    if (c2_renderer != NULL) {
        SDL_ConvertEventToRenderCoordinates(c2_renderer, event);
    }

    SDL_LockMutex(c2_event_mutex);
    if (event->type == SDL_EVENT_QUIT) {
        c2_input.quit_requested = 1;
        c2_input.generation++;
        host_event.type = C2_HOST_EVENT_QUIT;
        publish = 1;
    } else if (event->type == SDL_EVENT_WINDOW_FOCUS_GAINED) {
        c2_input.focused = 1;
        c2_input.generation++;
    } else if (event->type == SDL_EVENT_WINDOW_FOCUS_LOST) {
        c2_input.focused = 0;
        c2_input.generation++;
    } else if (event->type == SDL_EVENT_MOUSE_MOTION) {
        c2_input.mouse_x = (int)event->motion.x;
        c2_input.mouse_y = (int)event->motion.y;
        c2_input.generation++;
    } else if (event->type == SDL_EVENT_MOUSE_BUTTON_DOWN ||
               event->type == SDL_EVENT_MOUSE_BUTTON_UP) {
        unsigned int mask;

        c2_input.mouse_x = (int)event->button.x;
        c2_input.mouse_y = (int)event->button.y;
        mask = translate_mouse_button(event->button.button);
        if (event->type == SDL_EVENT_MOUSE_BUTTON_DOWN) {
            c2_input.mouse_buttons |= mask;
            host_event.type = C2_HOST_EVENT_MOUSE_BUTTON_DOWN;
            host_event.mouse_x = c2_input.mouse_x;
            host_event.mouse_y = c2_input.mouse_y;
            host_event.mouse_button = mask;
            publish = 1;
        } else {
            c2_input.mouse_buttons &= ~mask;
        }
        c2_input.generation++;
    } else if (event->type == SDL_EVENT_MOUSE_WHEEL) {
        c2_input.wheel_x += (int)event->wheel.x;
        c2_input.wheel_y += (int)event->wheel.y;
        c2_input.generation++;
    } else if (event->type == SDL_EVENT_KEY_DOWN && !event->key.repeat) {
        host_event.type = C2_HOST_EVENT_KEY_DOWN;
        host_event.key = translate_key(event->key.key);
        c2_input.generation++;
        publish = 1;
    }
    SDL_UnlockMutex(c2_event_mutex);

    if (publish) {
        queue_event(&host_event);
    }
}
