#include <SDL3/SDL.h>

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "c2_host.h"
#include "c2_port_mouse.h"
#include "c2_sdl_host.h"

#define C2_PATH_CAPACITY 4096
#define C2_PALETTE_BYTES (256 * 3)
#define C2_EVENT_QUEUE_CAPACITY 64
#define C2_MOUSE_EDGE_MARGIN 8

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
static struct c2_port_mouse c2_mouse;
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
static int c2_mouse_lock_requested;
static int c2_mouse_relative;
static int c2_mouse_lock_pending;
static int c2_mouse_warp_pending;
#if C2_FEAT_DEBUG_OBSERVATION
static int c2_observation_enabled;
#endif

struct c2_host_user_stream {
    FILE *file;
};

static void sync_mouse_input(void)
{
    c2_input.mouse_x = c2_mouse.x;
    c2_input.mouse_y = c2_mouse.y;
    c2_input.mouse_inside = c2_mouse.inside;
}

static int update_mouse_confinement_rect(void)
{
    SDL_FRect content;
    SDL_Rect barrier;
    int right;
    int bottom;

    if (!SDL_GetRenderLogicalPresentationRect(c2_renderer, &content)) {
        return 0;
    }
    barrier.x = (int)content.x;
    barrier.y = (int)content.y;
    if (barrier.x < content.x) barrier.x++;
    if (barrier.y < content.y) barrier.y++;
    right = (int)(content.x + content.w);
    bottom = (int)(content.y + content.h);
    barrier.w = right - barrier.x;
    barrier.h = bottom - barrier.y;
    if (barrier.w <= 0 || barrier.h <= 0) return 0;
    return SDL_SetWindowMouseRect(c2_window, &barrier);
}

static int enable_mouse_lock(void)
{
    if (!c2_mouse_lock_requested) {
        c2_mouse_lock_pending = 0;
        return 1;
    }

    SDL_ClearError();
    if (update_mouse_confinement_rect() &&
        SDL_SetWindowMouseGrab(c2_window, true)) {
        c2_mouse_relative = 0;
        c2_mouse_lock_pending = 0;
        return 1;
    }

    SDL_SetWindowMouseGrab(c2_window, false);
    SDL_SetWindowMouseRect(c2_window, NULL);
    SDL_ClearError();
    if (SDL_SetWindowRelativeMouseMode(c2_window, true)) {
        c2_mouse_relative = 1;
        c2_mouse_lock_pending = 0;
        return 1;
    }
    c2_mouse_lock_pending = 1;
    return 0;
}

static void apply_pending_mouse_warp(void)
{
    float frame_x;
    float frame_y;
    float window_x;
    float window_y;
    int pending;

    SDL_LockMutex(c2_event_mutex);
    pending = c2_mouse_warp_pending;
    c2_mouse_warp_pending = 0;
    c2_port_mouse_get_frame_position(&c2_mouse, &frame_x, &frame_y);
    SDL_UnlockMutex(c2_event_mutex);

    if (!pending || c2_mouse_relative) return;
    if (!SDL_RenderCoordinatesToWindow(c2_renderer, frame_x, frame_y,
                                       &window_x, &window_y)) {
        return;
    }
    SDL_WarpMouseInWindow(c2_window, window_x, window_y);
}

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

static int compare_filenames(const void *left, const void *right)
{
    const char *const *left_name;
    const char *const *right_name;
    int result;

    left_name = left;
    right_name = right;
    result = SDL_strcasecmp(*left_name, *right_name);
    return result != 0 ? result : strcmp(*left_name, *right_name);
}

static FILE *open_file_in_directory(const char *directory,
                                    const char *filename)
{
    char path[C2_PATH_CAPACITY];
    char **entries;
    FILE *file;
    int entry_count;
    int i;

    if (!build_path(path, sizeof(path), directory, filename, 0)) {
        return NULL;
    }
    file = fopen(path, "rb");
    if (file != NULL) {
        return file;
    }
    if (!build_path(path, sizeof(path), directory, filename, 1)) {
        return NULL;
    }
    file = fopen(path, "rb");
    if (file != NULL) {
        return file;
    }

    if (strchr(filename, '/') != NULL || strchr(filename, '\\') != NULL) {
        return NULL;
    }
    entries = SDL_GlobDirectory(directory, filename,
                                SDL_GLOB_CASEINSENSITIVE, &entry_count);
    if (entries == NULL) {
        return NULL;
    }
    qsort(entries, (size_t)entry_count, sizeof(*entries), compare_filenames);
    file = NULL;
    for (i = 0; i < entry_count; i++) {
        if (strchr(entries[i], '/') == NULL &&
            strchr(entries[i], '\\') == NULL &&
            SDL_strcasecmp(entries[i], filename) == 0 &&
            build_path(path, sizeof(path), directory, entries[i], 0)) {
            file = fopen(path, "rb");
            if (file != NULL) {
                break;
            }
        }
    }
    SDL_free(entries);
    return file;
}

static const char *asset_media_directory(const char *filename)
{
    const char *extension;

    extension = strrchr(filename, '.');
    if (extension == NULL) return NULL;
    if (SDL_strcasecmp(extension, ".pl8") == 0) return "pl8";
    if (SDL_strcasecmp(extension, ".raw") == 0) return "raw";
    if (SDL_strcasecmp(extension, ".xmi") == 0) return "xmi";
    if (SDL_strcasecmp(extension, ".smk") == 0) return "smk";
    return NULL;
}

static int resolve_asset_directory(char *path, size_t capacity,
                                   const char *directory)
{
    char **entries;
    SDL_PathInfo info;
    int entry_count;
    int i;

    if (!build_path(path, capacity, c2_asset_root, directory, 0)) {
        return 0;
    }
    if (SDL_GetPathInfo(path, &info) && info.type == SDL_PATHTYPE_DIRECTORY) {
        return 1;
    }
    if (!build_path(path, capacity, c2_asset_root, directory, 1)) {
        return 0;
    }
    if (SDL_GetPathInfo(path, &info) && info.type == SDL_PATHTYPE_DIRECTORY) {
        return 1;
    }

    entries = SDL_GlobDirectory(c2_asset_root, directory,
                                SDL_GLOB_CASEINSENSITIVE, &entry_count);
    if (entries == NULL) {
        return 0;
    }
    qsort(entries, (size_t)entry_count, sizeof(*entries), compare_filenames);
    for (i = 0; i < entry_count; i++) {
        if (strchr(entries[i], '/') == NULL &&
            strchr(entries[i], '\\') == NULL &&
            SDL_strcasecmp(entries[i], directory) == 0 &&
            build_path(path, capacity, c2_asset_root, entries[i], 0) &&
            SDL_GetPathInfo(path, &info) &&
            info.type == SDL_PATHTYPE_DIRECTORY) {
            SDL_free(entries);
            return 1;
        }
    }
    SDL_free(entries);
    return 0;
}

static FILE *open_asset(const char *filename)
{
    char media_path[C2_PATH_CAPACITY];
    const char *media_directory;
    FILE *file;

    if (!is_safe_relative_path(filename)) {
        return NULL;
    }
    file = open_file_in_directory(c2_asset_root, filename);
    if (file != NULL) {
        return file;
    }

    media_directory = asset_media_directory(filename);
    if (media_directory == NULL ||
        !resolve_asset_directory(media_path, sizeof(media_path),
                                 media_directory)) {
        return NULL;
    }
    return open_file_in_directory(media_path, filename);
}

static int resolve_user_path(char *path, size_t capacity,
                             const char *filename, int allow_missing)
{
    char **entries;
    int entry_count;
    int i;

    if (!build_path(path, capacity, c2_user_data_root, filename, 0)) {
        return 0;
    }
    if (SDL_GetPathInfo(path, NULL)) {
        return 1;
    }
    if (strchr(filename, '/') == NULL && strchr(filename, '\\') == NULL) {
        entries = SDL_GlobDirectory(c2_user_data_root, filename,
                                    SDL_GLOB_CASEINSENSITIVE, &entry_count);
        if (entries != NULL) {
            qsort(entries, (size_t)entry_count, sizeof(*entries),
                  compare_filenames);
            for (i = 0; i < entry_count; i++) {
                if (strchr(entries[i], '/') == NULL &&
                    strchr(entries[i], '\\') == NULL &&
                    SDL_strcasecmp(entries[i], filename) == 0 &&
                    build_path(path, capacity, c2_user_data_root,
                               entries[i], 0)) {
                    SDL_free(entries);
                    return 1;
                }
            }
            SDL_free(entries);
        }
    }
    if (!allow_missing) {
        return 0;
    }
    return build_path(path, capacity, c2_user_data_root, filename, 0);
}

static void queue_event(const struct c2_host_event *event);

static unsigned char expand_vga_channel(unsigned char channel)
{
    return (unsigned char)((channel << 2) | (channel >> 4));
}

static enum c2_host_key translate_key(SDL_Keycode key)
{
    if (key == SDLK_ESCAPE) return C2_HOST_KEY_ESCAPE;
    if (key == SDLK_RETURN || key == SDLK_KP_ENTER) return C2_HOST_KEY_RETURN;
    if (key == SDLK_BACKSPACE) return C2_HOST_KEY_BACKSPACE;
    if (key == SDLK_DELETE) return C2_HOST_KEY_DELETE;
    if (key == SDLK_INSERT) return C2_HOST_KEY_INSERT;
    if (key == SDLK_HOME) return C2_HOST_KEY_HOME;
    if (key == SDLK_END) return C2_HOST_KEY_END;
    if (key == SDLK_LEFT) return C2_HOST_KEY_LEFT;
    if (key == SDLK_RIGHT) return C2_HOST_KEY_RIGHT;
    if (key == SDLK_UP) return C2_HOST_KEY_UP;
    if (key == SDLK_DOWN) return C2_HOST_KEY_DOWN;
    if (key == SDLK_F1) return C2_HOST_KEY_F1;
    if (key == SDLK_F2) return C2_HOST_KEY_F2;
    if (key == SDLK_F3) return C2_HOST_KEY_F3;
    if (key == SDLK_F4) return C2_HOST_KEY_F4;
    if (key == SDLK_F5) return C2_HOST_KEY_F5;
    if (key == SDLK_D) return C2_HOST_KEY_D;
    if (key == SDLK_F) return C2_HOST_KEY_F;
    if (key == SDLK_X) return C2_HOST_KEY_X;
    if (key == SDLK_1) return C2_HOST_KEY_1;
    if (key == SDLK_2) return C2_HOST_KEY_2;
    if (key == SDLK_3) return C2_HOST_KEY_3;
    if (key == SDLK_4) return C2_HOST_KEY_4;
    if (key == SDLK_5) return C2_HOST_KEY_5;
    if (key == SDLK_6) return C2_HOST_KEY_6;
    if (key == SDLK_7) return C2_HOST_KEY_7;
    if (key == SDLK_8) return C2_HOST_KEY_8;
    return C2_HOST_KEY_UNKNOWN;
}

static const char *decode_utf8(const char *text, uint32_t *codepoint)
{
    const unsigned char *bytes;
    uint32_t value;
    int continuation_count;
    int i;

    bytes = (const unsigned char *)text;
    if (bytes[0] < 0x80) {
        *codepoint = bytes[0];
        return text + 1;
    }
    if (bytes[0] >= 0xc2 && bytes[0] <= 0xdf) {
        value = bytes[0] & 0x1f;
        continuation_count = 1;
    } else if (bytes[0] >= 0xe0 && bytes[0] <= 0xef) {
        value = bytes[0] & 0x0f;
        continuation_count = 2;
    } else if (bytes[0] >= 0xf0 && bytes[0] <= 0xf4) {
        value = bytes[0] & 0x07;
        continuation_count = 3;
    } else {
        *codepoint = 0xfffd;
        return text + 1;
    }
    for (i = 1; i <= continuation_count; i++) {
        if ((bytes[i] & 0xc0) != 0x80) {
            *codepoint = 0xfffd;
            return text + 1;
        }
        value = (value << 6) | (bytes[i] & 0x3f);
    }
    if ((continuation_count == 2 && value < 0x800) ||
        (continuation_count == 3 && value < 0x10000) ||
        (value >= 0xd800 && value <= 0xdfff) || value > 0x10ffff) {
        *codepoint = 0xfffd;
        return text + 1;
    }
    *codepoint = value;
    return text + continuation_count + 1;
}

static void queue_text_input(const char *text)
{
    struct c2_host_event event;
    const char *cursor;

    cursor = text;
    while (*cursor != '\0') {
        memset(&event, 0, sizeof(event));
        event.type = C2_HOST_EVENT_TEXT_INPUT;
        cursor = decode_utf8(cursor, &event.codepoint);
        queue_event(&event);
    }
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
    SDL_WindowFlags window_flags;
    SDL_RendererLogicalPresentation presentation;
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
    if (!SDL_CreateDirectory(c2_user_data_root)) {
        fprintf(stderr, "could not create user-data directory '%s': %s\n",
                c2_user_data_root, SDL_GetError());
        c2_host_shutdown();
        return 0;
    }

    c2_frame_width = config->logical_width;
    c2_frame_height = config->logical_height;
    c2_headless = config->headless;
    c2_mouse_lock_requested = config->mouse_lock;
    c2_mouse_relative = 0;
    c2_mouse_lock_pending = 0;
    c2_mouse_warp_pending = 0;
    c2_frame_dirty = 0;
    c2_event_read = 0;
    c2_event_count = 0;
    c2_shutdown = 0;
#if C2_FEAT_DEBUG_OBSERVATION
    c2_observation_enabled = config->enable_observation;
#endif
    memset(&c2_input, 0, sizeof(c2_input));
    if (!c2_port_mouse_init(&c2_mouse, c2_frame_width, c2_frame_height,
                            C2_MOUSE_EDGE_MARGIN)) {
        fprintf(stderr, "invalid Caesar II mouse configuration\n");
        c2_host_shutdown();
        return 0;
    }
#if C2_FEAT_DEBUG_OBSERVATION
    memset(&c2_observation, 0, sizeof(c2_observation));
#endif
    c2_input.focused = 1;
    sync_mouse_input();
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
    window_flags = SDL_WINDOW_RESIZABLE;
    presentation = SDL_LOGICAL_PRESENTATION_LETTERBOX;
#if C2_FEAT_BROWSER_RUNTIME
    window_flags |= SDL_WINDOW_HIGH_PIXEL_DENSITY;
    presentation = SDL_LOGICAL_PRESENTATION_INTEGER_SCALE;
#endif
    if (!SDL_CreateWindowAndRenderer(config->title,
                                     c2_frame_width * config->window_scale,
                                     c2_frame_height * config->window_scale,
                                     window_flags,
                                     &c2_window, &c2_renderer)) {
        fprintf(stderr, "SDL window creation failed: %s\n", SDL_GetError());
        c2_host_shutdown();
        return 0;
    }
    if (!SDL_HideCursor()) {
        fprintf(stderr, "could not hide the host cursor: %s\n", SDL_GetError());
        c2_host_shutdown();
        return 0;
    }
    if (!SDL_StartTextInput(c2_window)) {
        fprintf(stderr, "could not start text input: %s\n", SDL_GetError());
        c2_host_shutdown();
        return 0;
    }
    if (!SDL_SetRenderLogicalPresentation(c2_renderer,
                                          c2_frame_width,
                                          c2_frame_height,
                                          presentation)) {
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
    if (!enable_mouse_lock()) {
        fprintf(stderr,
                "mouse lock is waiting for a pointer click: %s\n",
                SDL_GetError());
    }
    return 1;
}

void c2_host_shutdown(void)
{
    c2_host_audio_shutdown();
    if (c2_window != NULL) {
        if (c2_mouse_relative) {
            SDL_SetWindowRelativeMouseMode(c2_window, false);
        }
        SDL_SetWindowMouseGrab(c2_window, false);
        SDL_SetWindowMouseRect(c2_window, NULL);
        SDL_StopTextInput(c2_window);
        SDL_ShowCursor();
    }
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
    c2_mouse_lock_requested = 0;
    c2_mouse_relative = 0;
    c2_mouse_lock_pending = 0;
    c2_mouse_warp_pending = 0;

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
    return capability == C2_HOST_CAPABILITY_MUSIC ||
           capability == C2_HOST_CAPABILITY_VIDEO;
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

    if (!resolve_user_path(path, sizeof(path), filename, 1)) {
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

    if (!resolve_user_path(path, sizeof(path), filename, 0)) {
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

    if (!resolve_user_path(path, sizeof(path), filename, 1)) {
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

int c2_host_user_file_exists(const char *filename)
{
    char path[C2_PATH_CAPACITY];
    SDL_PathInfo info;

    return resolve_user_path(path, sizeof(path), filename, 0) &&
           SDL_GetPathInfo(path, &info) && info.type == SDL_PATHTYPE_FILE;
}

size_t c2_host_user_file_list(const char *pattern, char *names,
                              size_t name_capacity, size_t max_names)
{
    char path[C2_PATH_CAPACITY];
    char **entries;
    SDL_PathInfo info;
    size_t result_count;
    size_t length;
    size_t j;
    int entry_count;
    int i;

    if (names == NULL || name_capacity == 0 || max_names == 0 ||
        !is_safe_relative_path(pattern) || strchr(pattern, '/') != NULL ||
        strchr(pattern, '\\') != NULL) {
        return 0;
    }
    entries = SDL_GlobDirectory(c2_user_data_root, pattern,
                                SDL_GLOB_CASEINSENSITIVE, &entry_count);
    if (entries == NULL) {
        return 0;
    }
    qsort(entries, (size_t)entry_count, sizeof(*entries), compare_filenames);
    result_count = 0;
    for (i = 0; i < entry_count && result_count < max_names; i++) {
        length = strlen(entries[i]);
        if (length == 0 || length >= name_capacity ||
            strchr(entries[i], '/') != NULL ||
            strchr(entries[i], '\\') != NULL ||
            (result_count != 0 &&
             SDL_strcasecmp(names + (result_count - 1) * name_capacity,
                            entries[i]) == 0) ||
            !build_path(path, sizeof(path), c2_user_data_root,
                        entries[i], 0) ||
            !SDL_GetPathInfo(path, &info) || info.type != SDL_PATHTYPE_FILE) {
            continue;
        }
        for (j = 0; j < length; j++) {
            names[result_count * name_capacity + j] =
                (char)toupper((unsigned char)entries[i][j]);
        }
        names[result_count * name_capacity + length] = '\0';
        result_count++;
    }
    SDL_free(entries);
    return result_count;
}

struct c2_host_user_stream *c2_host_user_stream_open(
    const char *filename, enum c2_host_user_stream_mode mode)
{
    char path[C2_PATH_CAPACITY];
    struct c2_host_user_stream *stream;
    int allow_missing;

    if (mode != C2_HOST_USER_STREAM_READ &&
        mode != C2_HOST_USER_STREAM_WRITE) {
        return NULL;
    }
    allow_missing = mode == C2_HOST_USER_STREAM_WRITE;
    if (!resolve_user_path(path, sizeof(path), filename, allow_missing)) {
        return NULL;
    }
    stream = malloc(sizeof(*stream));
    if (stream == NULL) {
        return NULL;
    }
    stream->file = fopen(path, mode == C2_HOST_USER_STREAM_READ ? "rb" : "wb");
    if (stream->file == NULL) {
        free(stream);
        return NULL;
    }
    return stream;
}

size_t c2_host_user_stream_read(struct c2_host_user_stream *stream,
                                void *buffer, size_t size)
{
    if (stream == NULL || stream->file == NULL) {
        return 0;
    }
    return fread(buffer, 1, size, stream->file);
}

size_t c2_host_user_stream_write(struct c2_host_user_stream *stream,
                                 const void *buffer, size_t size)
{
    if (stream == NULL || stream->file == NULL) {
        return 0;
    }
    return fwrite(buffer, 1, size, stream->file);
}

int c2_host_user_stream_close(struct c2_host_user_stream *stream)
{
    int ok;

    if (stream == NULL) {
        return 0;
    }
    ok = stream->file != NULL && fclose(stream->file) == 0;
    free(stream);
    return ok;
}

int c2_host_save_indexed_png(const char *filename,
                             const unsigned char *pixels,
                             int width, int height, int pitch,
                             const unsigned char *palette,
                             size_t palette_size)
{
    char path[C2_PATH_CAPACITY];
    SDL_Surface *surface;
    SDL_Palette *surface_palette;
    SDL_Color colors[256];
    int row;
    int i;
    int ok;

    if (pixels == NULL || palette == NULL || width <= 0 || height <= 0 ||
        pitch < width || palette_size != C2_PALETTE_BYTES ||
        !resolve_user_path(path, sizeof(path), filename, 1)) {
        return 0;
    }
    surface = SDL_CreateSurface(width, height, SDL_PIXELFORMAT_INDEX8);
    if (surface == NULL) {
        return 0;
    }
    surface_palette = SDL_CreateSurfacePalette(surface);
    if (surface_palette == NULL) {
        SDL_DestroySurface(surface);
        return 0;
    }
    for (i = 0; i < 256; i++) {
        colors[i].r = expand_vga_channel(palette[i * 3]);
        colors[i].g = expand_vga_channel(palette[i * 3 + 1]);
        colors[i].b = expand_vga_channel(palette[i * 3 + 2]);
        colors[i].a = 255;
    }
    if (!SDL_SetPaletteColors(surface_palette, colors, 0, 256) ||
        !SDL_LockSurface(surface)) {
        SDL_DestroySurface(surface);
        return 0;
    }
    for (row = 0; row < height; row++) {
        memcpy((unsigned char *)surface->pixels +
                   (size_t)row * (size_t)surface->pitch,
               pixels + (size_t)row * (size_t)pitch,
               (size_t)width);
    }
    SDL_UnlockSurface(surface);
    ok = SDL_SavePNG(surface, path);
    SDL_DestroySurface(surface);
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

    apply_pending_mouse_warp();

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

void c2_host_set_mouse_position(int x, int y)
{
    SDL_LockMutex(c2_event_mutex);
    c2_port_mouse_set_position(&c2_mouse, x, y);
    sync_mouse_input();
    c2_mouse_warp_pending = !c2_headless;
    c2_input.generation++;
    SDL_UnlockMutex(c2_event_mutex);
}

void c2_host_set_mouse_bounds(int min_x, int min_y, int max_x, int max_y)
{
    SDL_LockMutex(c2_event_mutex);
    if (c2_port_mouse_set_bounds(&c2_mouse,
                                 min_x, min_y, max_x, max_y)) {
        sync_mouse_input();
        c2_mouse_warp_pending = !c2_headless;
        c2_input.generation++;
    }
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
    c2_observation.tutorial_mode = observation->tutorial_mode;
    c2_observation.in_forum = observation->in_forum;
    c2_observation.map_x = observation->map_x;
    c2_observation.map_y = observation->map_y;
    c2_observation.sequences_running = observation->sequences_running;
    c2_observation.tune_branch = observation->tune_branch;
    c2_observation.tune_branch_count = observation->tune_branch_count;
    c2_observation.menu_count = observation->menu_count;
    c2_observation.active_menu = observation->active_menu;
    c2_observation.menu_item_group = observation->menu_item_group;
    c2_observation.menu_item_count = observation->menu_item_count;
    c2_observation.active_menu_item = observation->active_menu_item;
    memcpy(c2_observation.menu_x1, observation->menu_x1,
           sizeof(c2_observation.menu_x1));
    memcpy(c2_observation.menu_x2, observation->menu_x2,
           sizeof(c2_observation.menu_x2));
    memcpy(c2_observation.player_name, observation->player_name,
           sizeof(c2_observation.player_name));
    memcpy(c2_observation.filename, observation->filename,
           sizeof(c2_observation.filename));
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
    c2_port_mouse_set_position(&c2_mouse, x, y);
    sync_mouse_input();
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

void c2_sdl_host_push_headless_text(uint32_t codepoint)
{
    struct c2_host_event event;

    memset(&event, 0, sizeof(event));
    event.type = C2_HOST_EVENT_TEXT_INPUT;
    event.codepoint = codepoint;
    queue_event(&event);
}
#endif

void c2_sdl_host_handle_event(SDL_Event *event)
{
    struct c2_host_event host_event;
    int publish;
    int refresh_mouse_rect;
    int retry_mouse_lock;

    memset(&host_event, 0, sizeof(host_event));
    publish = 0;
    refresh_mouse_rect = 0;
    retry_mouse_lock = 0;
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
        c2_input.mouse_buttons = 0;
        c2_port_mouse_leave(&c2_mouse);
        sync_mouse_input();
        c2_input.generation++;
    } else if (event->type == SDL_EVENT_WINDOW_MOUSE_LEAVE) {
        c2_port_mouse_leave(&c2_mouse);
        sync_mouse_input();
        c2_input.generation++;
    } else if ((event->type == SDL_EVENT_WINDOW_RESIZED ||
                event->type == SDL_EVENT_WINDOW_PIXEL_SIZE_CHANGED) &&
               c2_mouse_lock_requested && !c2_mouse_relative) {
        refresh_mouse_rect = 1;
    } else if (event->type == SDL_EVENT_MOUSE_MOTION) {
        if (c2_mouse_relative) {
            c2_port_mouse_add_relative(&c2_mouse,
                                       event->motion.xrel,
                                       event->motion.yrel);
        } else {
            c2_port_mouse_set_absolute(&c2_mouse,
                                       event->motion.x,
                                       event->motion.y);
        }
        sync_mouse_input();
        c2_input.generation++;
    } else if (event->type == SDL_EVENT_MOUSE_BUTTON_DOWN ||
               event->type == SDL_EVENT_MOUSE_BUTTON_UP) {
        unsigned int mask;

        if (!c2_mouse_relative) {
            c2_port_mouse_set_absolute(&c2_mouse,
                                       event->button.x,
                                       event->button.y);
            sync_mouse_input();
        }
        mask = translate_mouse_button(event->button.button);
        if (event->type == SDL_EVENT_MOUSE_BUTTON_DOWN &&
            c2_mouse.inside && mask != 0) {
            c2_input.mouse_buttons |= mask;
            host_event.type = C2_HOST_EVENT_MOUSE_BUTTON_DOWN;
            host_event.mouse_x = c2_input.mouse_x;
            host_event.mouse_y = c2_input.mouse_y;
            host_event.mouse_button = mask;
            publish = 1;
            retry_mouse_lock = c2_mouse_lock_pending;
        } else if (event->type == SDL_EVENT_MOUSE_BUTTON_UP) {
            c2_input.mouse_buttons &= ~mask;
        }
        c2_input.generation++;
    } else if (event->type == SDL_EVENT_MOUSE_WHEEL) {
        int wheel_x;
        int wheel_y;

        wheel_x = event->wheel.integer_x;
        wheel_y = event->wheel.integer_y;
        if (wheel_x == 0 && event->wheel.x != 0.0f) {
            wheel_x = event->wheel.x > 0.0f ? 1 : -1;
        }
        if (wheel_y == 0 && event->wheel.y != 0.0f) {
            wheel_y = event->wheel.y > 0.0f ? 1 : -1;
        }
        if (event->wheel.direction == SDL_MOUSEWHEEL_FLIPPED) {
            wheel_x = -wheel_x;
            wheel_y = -wheel_y;
        }
        if (c2_mouse.inside) {
            c2_input.wheel_x += wheel_x;
            c2_input.wheel_y += wheel_y;
        }
        c2_input.generation++;
        if (c2_mouse.inside && wheel_y != 0) {
            host_event.type = C2_HOST_EVENT_MOUSE_WHEEL;
            host_event.wheel_y = wheel_y;
            publish = 1;
        }
    } else if (event->type == SDL_EVENT_KEY_DOWN && !event->key.repeat) {
        host_event.type = C2_HOST_EVENT_KEY_DOWN;
        host_event.key = translate_key(event->key.key);
        if ((event->key.mod & SDL_KMOD_ALT) != 0) {
            host_event.key_modifiers |= C2_HOST_KEY_MODIFIER_ALT;
        }
        c2_input.generation++;
        publish = host_event.key != C2_HOST_KEY_UNKNOWN;
    } else if (event->type == SDL_EVENT_TEXT_INPUT) {
        c2_input.generation++;
    }
    SDL_UnlockMutex(c2_event_mutex);

    if (retry_mouse_lock && !enable_mouse_lock()) {
        fprintf(stderr, "could not lock the mouse: %s\n", SDL_GetError());
    }
    if (refresh_mouse_rect && !update_mouse_confinement_rect()) {
        fprintf(stderr,
                "warning: could not update mouse confinement: %s\n",
                SDL_GetError());
    }
    if (event->type == SDL_EVENT_TEXT_INPUT) {
        queue_text_input(event->text.text);
    } else if (publish) {
        queue_event(&host_event);
    }
}
