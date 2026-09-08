#include <stdlib.h>
#include <string.h>

#include <libsmacker/smacker.h>

#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"

#define C2_MOVIE_AUDIO_VOICE 7

/* Mode 2 plays a movie in the VGA 320x200 screen, which the 640x480 frame
 * shows at 2x horizontally and 2.4x vertically (mode 13h's aspect): every
 * DOS mode-2 movie is 320x152 and lands in a 640x365 box. The Windows 95
 * versions of five of them are 500x240; they are scaled into that same
 * box. */
#define C2_MOVIE_VGA_WIDTH 320u
#define C2_MOVIE_VGA_HEIGHT 152u

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
extern void general_sprite(int sprite_idx, int x, int y);
extern void set_palette(char *palette);
void stop_smacking(void);

static int show_movie_fallback(const char *filename, int left, int top,
                               int mode)
{
    char path[256];
    char *extension;
    unsigned char *pixels;
    unsigned char *palette;
    size_t pixels_size;
    size_t palette_size;

    if (mode != 1 || filename == NULL || strlen(filename) >= sizeof(path)) {
        return 0;
    }
    strcpy(path, filename);
    extension = strrchr(path, '.');
    if (extension == NULL || strlen(extension) != 4) return 0;
    memcpy(extension + 1, "pl8", 4);
    pixels = c2_port_load_asset(path, &pixels_size);
    memcpy(extension + 1, "256", 4);
    palette = c2_port_load_asset(path, &palette_size);
    if (pixels == NULL || palette == NULL || palette_size < 0x300 ||
        pixels_size > 0x186a0) {
        free(pixels);
        free(palette);
        return 0;
    }
    memcpy(scratch_buffer, pixels, pixels_size);
    memcpy(temp_palette, palette, 0x300);
    free(pixels);
    free(palette);
    set_palette((char *)temp_palette);
    general_sprite(0, left, top);
    setup_refresh_area(left, top, 0x14, 0xa, 1);
    refresh_svga_screen();
    return 1;
}

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

/* Fill the box a 320x152 movie occupies in the scaled VGA screen from a
 * frame of any size: each destination pixel takes the source pixel under
 * it (nearest neighbour; the frame is palette-indexed, so no blending). */
static void copy_vga_frame(const unsigned char *pixels, int left, int top)
{
    int box_x = left * C2_SCREEN_WIDTH / 320;
    int box_y = top * C2_SCREEN_HEIGHT / 200;
    int box_w = (left + (int)C2_MOVIE_VGA_WIDTH) * C2_SCREEN_WIDTH / 320 - box_x;
    int box_h = (top + (int)C2_MOVIE_VGA_HEIGHT) * C2_SCREEN_HEIGHT / 200 - box_y;
    int x;
    int y;

    if (c2_movie.width == 0 || c2_movie.height == 0) return;
    for (y = 0; y < box_h; y++) {
        int destination_y = box_y + y;
        unsigned long source_y = (unsigned long)y * c2_movie.height / (unsigned long)box_h;
        const unsigned char *row;
        if (destination_y < 0 || destination_y >= C2_SCREEN_HEIGHT) continue;
        if (source_y >= c2_movie.height) source_y = c2_movie.height - 1;
        row = pixels + source_y * c2_movie.width;
        for (x = 0; x < box_w; x++) {
            int destination_x = box_x + x;
            unsigned long source_x = (unsigned long)x * c2_movie.width / (unsigned long)box_w;
            if (destination_x < 0 || destination_x >= C2_SCREEN_WIDTH) continue;
            if (source_x >= c2_movie.width) source_x = c2_movie.width - 1;
            internal_screen[(size_t)destination_y * C2_SCREEN_WIDTH +
                            (size_t)destination_x] = row[source_x];
        }
    }
}

/* Smacker header: "SMK2", width, height (little-endian 32-bit). */
static unsigned long smk_header_pixels(const unsigned char *header, size_t size)
{
    unsigned long width;
    unsigned long height;

    if (size < 12 || memcmp(header, "SMK2", 4) != 0) return 0;
    width = header[4] | ((unsigned long)header[5] << 8) |
            ((unsigned long)header[6] << 16) | ((unsigned long)header[7] << 24);
    height = header[8] | ((unsigned long)header[9] << 8) |
             ((unsigned long)header[10] << 16) | ((unsigned long)header[11] << 24);
    return width * height;
}

/* The movie file to play: the DOS one, unless the Windows 95 tree has the
 * same movie with more pixels and the mode scales it anyway (mode 2). The
 * same-size Windows re-encodes have fewer colours, so they are not
 * preferred; a movie drawn 1:1 (modes 0 and 1) keeps its DOS size. */
static unsigned char *load_movie_asset(const char *filename, int mode,
                                       size_t *size_out)
{
    unsigned char dos_header[12];
    unsigned char windows_header[12];
    uint64_t windows_size;
    unsigned char *data;
    size_t size;

    if (mode == 2) {
        windows_size = c2_host_asset_windows_size(filename);
        if (windows_size >= 12 && windows_size <= SIZE_MAX &&
            c2_host_asset_read(filename, dos_header, sizeof(dos_header), 0) == sizeof(dos_header) &&
            c2_host_asset_windows_read(filename, windows_header, sizeof(windows_header), 0) == sizeof(windows_header) &&
            smk_header_pixels(windows_header, sizeof(windows_header)) >
                smk_header_pixels(dos_header, sizeof(dos_header))) {
            size = (size_t)windows_size;
            data = malloc(size);
            if (data != NULL &&
                c2_host_asset_windows_read(filename, data, size, 0) == size) {
                *size_out = size;
                return data;
            }
            free(data);
        }
    }
    return c2_port_load_asset(filename, size_out);
}

static void copy_decoded_frame(int left, int top, int mode)
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
    if (filename == NULL) return;
    if (c2inf.anims_on == 0) {
        show_movie_fallback(filename, left, top, mode);
        return;
    }
    c2_movie.asset = load_movie_asset(filename, mode, &asset_size);
    if (c2_movie.asset == NULL) {
        show_movie_fallback(filename, left, top, mode);
        return;
    }
    c2_movie.decoder = smk_open_memory(c2_movie.asset,
                                       (unsigned long)asset_size);
    if (c2_movie.decoder == NULL ||
        smk_info_all(c2_movie.decoder, NULL, &c2_movie.frame_count,
                     &c2_movie.frame_us) < 0 ||
        smk_info_video(c2_movie.decoder, &c2_movie.width,
                       &c2_movie.height, NULL) < 0 ||
        smk_enable_video(c2_movie.decoder, 1) < 0) {
        stop_smacking();
        show_movie_fallback(filename, left, top, mode);
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
    copy_decoded_frame(left, top, mode);
    refresh_svga_screen();
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
    copy_decoded_frame(left, top, mode);
    if (mode == 2) refresh_svga_screen();
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
