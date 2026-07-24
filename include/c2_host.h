#ifndef C2_HOST_H
#define C2_HOST_H

#include <stddef.h>
#include <stdint.h>

#include "c2_target.h"

#if C2_FEAT_DEBUG_OBSERVATION
#include "c2_observation.h"
#endif

enum c2_host_capability {
    C2_HOST_CAPABILITY_MUSIC,
    C2_HOST_CAPABILITY_VIDEO
};

enum c2_host_event_type {
    C2_HOST_EVENT_NONE,
    C2_HOST_EVENT_QUIT,
    C2_HOST_EVENT_KEY_DOWN,
    C2_HOST_EVENT_TEXT_INPUT,
    C2_HOST_EVENT_MOUSE_BUTTON_DOWN,
    C2_HOST_EVENT_MOUSE_WHEEL
};

enum c2_host_key {
    C2_HOST_KEY_UNKNOWN,
    C2_HOST_KEY_ESCAPE,
    C2_HOST_KEY_RETURN,
    C2_HOST_KEY_BACKSPACE,
    C2_HOST_KEY_DELETE,
    C2_HOST_KEY_INSERT,
    C2_HOST_KEY_HOME,
    C2_HOST_KEY_END,
    C2_HOST_KEY_LEFT,
    C2_HOST_KEY_RIGHT,
    C2_HOST_KEY_UP,
    C2_HOST_KEY_DOWN,
    C2_HOST_KEY_F1,
    C2_HOST_KEY_F2,
    C2_HOST_KEY_F3,
    C2_HOST_KEY_F4,
    C2_HOST_KEY_F5,
    C2_HOST_KEY_D,
    C2_HOST_KEY_F,
    C2_HOST_KEY_X,
    C2_HOST_KEY_1,
    C2_HOST_KEY_2,
    C2_HOST_KEY_3,
    C2_HOST_KEY_4,
    C2_HOST_KEY_5,
    C2_HOST_KEY_6,
    C2_HOST_KEY_7,
    C2_HOST_KEY_8
};

enum c2_host_key_modifier {
    C2_HOST_KEY_MODIFIER_ALT = 1u << 0
};

enum c2_host_mouse_button {
    C2_HOST_MOUSE_LEFT = 1u << 0,
    C2_HOST_MOUSE_RIGHT = 1u << 1,
    C2_HOST_MOUSE_MIDDLE = 1u << 2
};

struct c2_host_config {
    const char *title;
    const char *asset_root;
    const char *user_data_root;
    int logical_width;
    int logical_height;
    int window_scale;
    int headless;
    int mouse_lock;
#if C2_FEAT_DEBUG_OBSERVATION
    int enable_observation;
#endif
};

struct c2_host_event {
    enum c2_host_event_type type;
    enum c2_host_key key;
    unsigned int key_modifiers;
    uint32_t codepoint;
    int mouse_x;
    int mouse_y;
    unsigned int mouse_button;
    int wheel_y;
};

struct c2_host_input {
    int mouse_x;
    int mouse_y;
    unsigned int mouse_buttons;
    int wheel_x;
    int wheel_y;
    int mouse_inside;
    int focused;
    int quit_requested;
    uint64_t generation;
};

enum c2_host_user_stream_mode {
    C2_HOST_USER_STREAM_READ,
    C2_HOST_USER_STREAM_WRITE
};

struct c2_host_user_stream;

int c2_host_init(const struct c2_host_config *config);
void c2_host_shutdown(void);

uint64_t c2_host_ticks_ms(void);
uint64_t c2_host_wall_time_seconds(void);
void c2_host_sleep_ms(unsigned int milliseconds);
void c2_host_wait_until_ms(uint64_t deadline_ms);
int c2_host_has_capability(enum c2_host_capability capability);

int c2_host_audio_init(int voice_count);
void c2_host_audio_shutdown(void);
int c2_host_audio_play_wav(int voice, const void *data, size_t size,
                           int loop_count);
int c2_host_audio_play_pcm_u8(int voice, const void *data, size_t size,
                              int sample_rate, int channels,
                              int loop_count);
int c2_host_audio_queue_pcm(int voice, const void *data, size_t size,
                            int sample_rate, int channels, int bit_depth,
                            int final_chunk);
int c2_host_audio_voice_playing(int voice);
unsigned int c2_host_audio_voice_queued_ms(int voice);
void c2_host_audio_stop_voice(int voice);
void c2_host_audio_pause_voice(int voice);
void c2_host_audio_resume_voice(int voice);
void c2_host_audio_set_voice_gain(int voice, float gain);
void c2_host_audio_set_master_gain(float gain);

size_t c2_host_asset_read(const char *filename, void *buffer,
                          size_t size, size_t offset);
size_t c2_host_user_file_read(const char *filename, void *buffer,
                              size_t size, size_t offset);
int c2_host_user_file_write(const char *filename, const void *buffer,
                            size_t size);
int c2_host_user_file_write_at(const char *filename, const void *buffer,
                               size_t size, size_t offset);
int c2_host_user_file_exists(const char *filename);
size_t c2_host_user_file_list(const char *pattern, char *names,
                              size_t name_capacity, size_t max_names);
struct c2_host_user_stream *c2_host_user_stream_open(
    const char *filename, enum c2_host_user_stream_mode mode);
size_t c2_host_user_stream_read(struct c2_host_user_stream *stream,
                                void *buffer, size_t size);
size_t c2_host_user_stream_write(struct c2_host_user_stream *stream,
                                 const void *buffer, size_t size);
int c2_host_user_stream_close(struct c2_host_user_stream *stream);

int c2_host_save_indexed_png(const char *filename,
                             const unsigned char *pixels,
                             int width, int height, int pitch,
                             const unsigned char *palette,
                             size_t palette_size);

int c2_host_publish_indexed_frame(const unsigned char *pixels,
                                  int width, int height, int pitch,
                                  const unsigned char *palette,
                                  size_t palette_size);
void c2_host_present(void);

int c2_host_wait_event(struct c2_host_event *event,
                       unsigned int timeout_ms);
void c2_host_input_snapshot(struct c2_host_input *input);
void c2_host_input_poll(struct c2_host_input *input);
void c2_host_set_mouse_position(int x, int y);
void c2_host_set_mouse_bounds(int min_x, int min_y, int max_x, int max_y);
void c2_host_request_shutdown(void);
int c2_host_shutdown_requested(void);

#if C2_FEAT_DEBUG_OBSERVATION
struct c2_host_audio_observation {
    uint64_t produced_bytes;
    uint64_t underflow_bytes;
    unsigned int queued_bytes;
    unsigned int queued_ms;
    unsigned int estimated_queued_ms;
    unsigned int queue_calls;
    unsigned int device_requests;
    unsigned int underflows;
    int active;
};

void c2_host_publish_observation(const struct c2_observation *observation);
void c2_host_observation_snapshot(struct c2_observation *observation);
int c2_host_audio_observation_snapshot(
    int voice, struct c2_host_audio_observation *observation);
#endif

#endif /* C2_HOST_H */
