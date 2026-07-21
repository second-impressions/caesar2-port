#include <stdlib.h>
#include <string.h>

#include <libsmacker/smacker.h>

#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"

#define C2_MOVIE_AUDIO_VOICE 7

struct c2_movie_state {
    smk decoder;
    unsigned char *asset;
    unsigned long width;
    unsigned long height;
    unsigned long frame_count;
    double frame_us;
    uint64_t next_frame_ms;
    unsigned long audio_rate;
    unsigned char audio_channels;
    unsigned char audio_bit_depth;
    int audio_enabled;
    int last_frame;
};

static struct c2_movie_state c2_movie;

extern void refresh_svga_screen(void);
extern void setup_refresh_area(int screen_x, int screen_y,
                               int width, int height, int refresh_value);
extern void setup_whole_screen_refresh(void);
extern void stop_samples(void);
void stop_smacking(void);

static uint64_t frame_duration_ms(void)
{
    uint64_t duration;

    duration = (uint64_t)(c2_movie.frame_us / 1000.0 + 0.999);
    if (duration == 0) duration = 1;
    return duration;
}

static void copy_normal_frame(const unsigned char *pixels, int left, int top)
{
    unsigned long source_x;
    unsigned long source_y;
    int destination_x;
    int destination_y;

    for (source_y = 0; source_y < c2_movie.height; source_y++) {
        destination_y = top + (int)source_y;
        if (destination_y < 0 || destination_y >= C2_SCREEN_HEIGHT) continue;
        for (source_x = 0; source_x < c2_movie.width; source_x++) {
            destination_x = left + (int)source_x;
            if (destination_x < 0 || destination_x >= C2_SCREEN_WIDTH) continue;
            internal_screen[(size_t)destination_y * C2_SCREEN_WIDTH +
                            (size_t)destination_x] =
                pixels[source_y * c2_movie.width + source_x];
        }
    }
}

static void copy_vga_frame(const unsigned char *pixels, int left, int top)
{
    unsigned long source_x;
    unsigned long source_y;
    int logical_x;
    int logical_y;
    int x_begin;
    int x_end;
    int y_begin;
    int y_end;
    int destination_x;
    int destination_y;

    for (source_y = 0; source_y < c2_movie.height; source_y++) {
        logical_y = top + (int)source_y;
        y_begin = logical_y * C2_SCREEN_HEIGHT / 200;
        y_end = (logical_y + 1) * C2_SCREEN_HEIGHT / 200;
        if (y_begin < 0) y_begin = 0;
        if (y_end > C2_SCREEN_HEIGHT) y_end = C2_SCREEN_HEIGHT;
        for (source_x = 0; source_x < c2_movie.width; source_x++) {
            logical_x = left + (int)source_x;
            x_begin = logical_x * C2_SCREEN_WIDTH / 320;
            x_end = (logical_x + 1) * C2_SCREEN_WIDTH / 320;
            if (x_begin < 0) x_begin = 0;
            if (x_end > C2_SCREEN_WIDTH) x_end = C2_SCREEN_WIDTH;
            for (destination_y = y_begin; destination_y < y_end;
                 destination_y++) {
                for (destination_x = x_begin; destination_x < x_end;
                     destination_x++) {
                    internal_screen[(size_t)destination_y * C2_SCREEN_WIDTH +
                                    (size_t)destination_x] =
                        pixels[source_y * c2_movie.width + source_x];
                }
            }
        }
    }
}

static void publish_decoded_frame(int left, int top, int mode)
{
    const unsigned char *pixels;
    const unsigned char *palette;
    const unsigned char *audio;
    unsigned long audio_size;
    int palette_idx;

    pixels = smk_get_video(c2_movie.decoder);
    palette = smk_get_palette(c2_movie.decoder);
    if (mode == 2) {
        copy_vga_frame(pixels, left, top);
    } else {
        copy_normal_frame(pixels, left, top);
    }
    for (palette_idx = 0; palette_idx < C2_PALETTE_BYTES; palette_idx++) {
        current_palette[palette_idx] = palette[palette_idx] >> 2;
    }

    if (c2_movie.audio_enabled) {
        audio = smk_get_audio(c2_movie.decoder, 0);
        audio_size = smk_get_audio_size(c2_movie.decoder, 0);
        if (audio != NULL && audio_size != 0) {
            c2_host_audio_queue_pcm(C2_MOVIE_AUDIO_VOICE, audio, audio_size,
                                    (int)c2_movie.audio_rate,
                                    c2_movie.audio_channels,
                                    c2_movie.audio_bit_depth,
                                    c2_movie.last_frame);
        }
    }

    if (mode == 1) {
        setup_refresh_area(left, top,
                           ((int)c2_movie.width + 15) / 16,
                           ((int)c2_movie.height + 15) / 16, 1);
    } else {
        setup_whole_screen_refresh();
    }
    refresh_svga_screen();
}

void start_smacking(char *filename, int left, int top, int mode)
{
    size_t asset_size;
    unsigned char track_mask;
    unsigned char channels[7];
    unsigned char bit_depth[7];
    unsigned long audio_rate[7];
    signed char first_result;

    stop_smacking();
    if (filename == NULL || c2inf.anims_on == 0) return;
    c2_movie.asset = c2_port_load_asset(filename, &asset_size);
    if (c2_movie.asset == NULL) return;
    c2_movie.decoder = smk_open_memory(c2_movie.asset,
                                       (unsigned long)asset_size);
    if (c2_movie.decoder == NULL ||
        smk_info_all(c2_movie.decoder, NULL, &c2_movie.frame_count,
                     &c2_movie.frame_us) < 0 ||
        smk_info_video(c2_movie.decoder, &c2_movie.width,
                       &c2_movie.height, NULL) < 0 ||
        smk_enable_video(c2_movie.decoder, 1) < 0) {
        stop_smacking();
        return;
    }

    memset(channels, 0, sizeof(channels));
    memset(bit_depth, 0, sizeof(bit_depth));
    memset(audio_rate, 0, sizeof(audio_rate));
    track_mask = 0;
    c2_movie.audio_enabled = 0;
    if (smk_info_audio(c2_movie.decoder, &track_mask, channels,
                       bit_depth, audio_rate) >= 0 &&
        (track_mask & SMK_AUDIO_TRACK_0) != 0 &&
        c2inf.samples_on != 0 &&
        c2_host_audio_init(C2_MOVIE_AUDIO_VOICE + 1)) {
        c2_movie.audio_channels = channels[0];
        c2_movie.audio_bit_depth = bit_depth[0];
        c2_movie.audio_rate = audio_rate[0];
        c2_movie.audio_enabled =
            smk_enable_audio(c2_movie.decoder, 0, 1) >= 0;
    }

    stop_samples();
    first_result = smk_first(c2_movie.decoder);
    if (first_result < 0 || first_result == SMK_DONE) {
        stop_smacking();
        return;
    }
    c2_movie.last_frame = first_result == SMK_LAST;
    publish_decoded_frame(left, top, mode);
    c2_movie.next_frame_ms = c2_host_ticks_ms() + frame_duration_ms();
}

int continue_smacking(int left, int top, int mode)
{
    signed char next_result;

    if (c2_movie.decoder == NULL) return 0;
    if (c2_host_ticks_ms() < c2_movie.next_frame_ms) {
        c2_port_wait_for_frame();
        return 0;
    }
    if (c2_movie.last_frame) {
        stop_smacking();
        return 1;
    }

    next_result = smk_next(c2_movie.decoder);
    if (next_result < 0 || next_result == SMK_DONE) {
        stop_smacking();
        return 1;
    }
    c2_movie.last_frame = next_result == SMK_LAST;
    publish_decoded_frame(left, top, mode);
    c2_movie.next_frame_ms += frame_duration_ms();
    return 1;
}

void stop_smacking(void)
{
    if (c2_movie.decoder != NULL) smk_close(c2_movie.decoder);
    free(c2_movie.asset);
    c2_host_audio_stop_voice(C2_MOVIE_AUDIO_VOICE);
    memset(&c2_movie, 0, sizeof(c2_movie));
}

int are_smacking(void)
{
    return c2_movie.decoder != NULL;
}

void wvbl2(void)
{
    c2_port_wait_vblank();
}

void set_vga_256x(void)
{
}

void unset_vga_256x(void)
{
}
