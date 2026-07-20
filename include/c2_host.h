#ifndef C2_HOST_H
#define C2_HOST_H

#include <stddef.h>
#include <stdint.h>

enum c2_host_capability {
    C2_HOST_CAPABILITY_MUSIC,
    C2_HOST_CAPABILITY_VIDEO
};

enum c2_host_event_type {
    C2_HOST_EVENT_NONE,
    C2_HOST_EVENT_QUIT,
    C2_HOST_EVENT_KEY_DOWN,
    C2_HOST_EVENT_MOUSE_BUTTON_DOWN
};

enum c2_host_key {
    C2_HOST_KEY_UNKNOWN,
    C2_HOST_KEY_ESCAPE,
    C2_HOST_KEY_RETURN,
    C2_HOST_KEY_SPACE,
    C2_HOST_KEY_LEFT,
    C2_HOST_KEY_RIGHT,
    C2_HOST_KEY_P
};

struct c2_host_config {
    const char *title;
    const char *asset_root;
    const char *user_data_root;
    int logical_width;
    int logical_height;
    int window_scale;
    int headless;
};

struct c2_host_event {
    enum c2_host_event_type type;
    enum c2_host_key key;
    int mouse_x;
    int mouse_y;
    unsigned int mouse_button;
};

struct c2_host_input {
    int mouse_x;
    int mouse_y;
    unsigned int mouse_buttons;
    int wheel_x;
    int wheel_y;
    int focused;
    int quit_requested;
    uint64_t generation;
};

int c2_host_init(const struct c2_host_config *config);
void c2_host_shutdown(void);

uint64_t c2_host_ticks_ms(void);
void c2_host_sleep_ms(unsigned int milliseconds);
int c2_host_has_capability(enum c2_host_capability capability);

size_t c2_host_asset_read(const char *filename, void *buffer,
                          size_t size, size_t offset);
int c2_host_user_file_write(const char *filename, const void *buffer,
                            size_t size);

int c2_host_publish_indexed_frame(const unsigned char *pixels,
                                  int width, int height, int pitch,
                                  const unsigned char *palette,
                                  size_t palette_size);
void c2_host_present(void);

int c2_host_wait_event(struct c2_host_event *event,
                       unsigned int timeout_ms);
void c2_host_input_snapshot(struct c2_host_input *input);
void c2_host_request_shutdown(void);
int c2_host_shutdown_requested(void);

#endif /* C2_HOST_H */
