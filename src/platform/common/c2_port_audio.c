#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ail.h"
#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"
#include "pcsound.h"
#include "xmidi/xmidi.h"

#define C2_SAMPLE_VOICE_COUNT 6
#define C2_AUDIO_VOICE_COUNT 10
#define C2_BEEP_VOICE 6
#define C2_DIGITAL_VOICE_COUNT 8
#define C2_MUSIC_VOICE 8
#define C2_MUSIC_SAMPLE_RATE 44100
#define C2_SEQUENCE_COUNT 2
#define C2_SEQUENCE_BUFFER_FRAMES 2048
#define C2_SEQUENCE_QUEUE_TARGET_MS 100
#define C2_SEQUENCE_DATA_LIMIT PORT_TUNE_BUFFER_SIZE
#define C2_SAMPLE_BUFFER_LIMIT 20000

struct c2_ail_sample {
    const unsigned char *wav;
    size_t wav_size;
    int loop_count;
    int status;
};

/* Music: one Miles OPL3 synthesizer shared by both AIL sequence handles,
 * exactly as one MDI driver served both sequences in the DOS game. The
 * sequencer runs at the XMIDI service rate inside the player and the mixed
 * chip output streams into a single host voice. */
struct c2_ail_sequence {
    struct xmi_sequence *sequence;
    AILTRIGGERCB callback;
    int handle;
};

static struct c2_ail_sample c2_samples[C2_SAMPLE_VOICE_COUNT];
static struct c2_ail_sequence c2_sequences[C2_SEQUENCE_COUNT];
static struct xmi_player *c2_music;
static int c2_next_sample_handle;
static int c2_next_sequence_handle;
static int c2_speech_paused;

void _pos_ret3(void)
{
}

static uint32_t read_u32_le(const unsigned char *bytes)
{
    return (uint32_t)bytes[0] |
           ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) |
           ((uint32_t)bytes[3] << 24);
}

static struct c2_ail_sample *sample_from_handle(int handle)
{
    if (handle < 1 || handle > C2_SAMPLE_VOICE_COUNT) return NULL;
    return &c2_samples[handle - 1];
}

static struct c2_ail_sequence *sequence_from_handle(int handle)
{
    if (handle < 1 || handle > C2_SEQUENCE_COUNT) return NULL;
    return &c2_sequences[handle - 1];
}

static int load_music_bank(struct xmi_player *player)
{
    unsigned char *data;
    size_t data_size;
    int loaded;

    data = c2_port_load_asset("caesar.opl", &data_size);
    if (data == NULL) data = c2_port_load_asset("caesar.ad", &data_size);
    if (data == NULL) return 0;
    loaded = xmi_player_load_bank(player, data, data_size);
    free(data);
    return loaded > 0;
}

static void sequence_trigger(void *user_data, struct xmi_sequence *seq,
                             int channel, int value)
{
    struct c2_ail_sequence *sequence;

    (void)seq;
    sequence = user_data;
    if (sequence != NULL && sequence->callback != NULL) {
        sequence->callback(sequence->handle, channel, value);
    }
}

static int any_sequence_playing(void)
{
    int index;

    for (index = 0; index < C2_SEQUENCE_COUNT; index++) {
        if (c2_sequences[index].sequence != NULL &&
            xmi_sequence_status(c2_sequences[index].sequence) ==
                XMI_SEQ_PLAYING) {
            return 1;
        }
    }
    return 0;
}

/* Keep the host voice fed while music plays; the chip keeps streaming for
 * a moment after the last sequence stops so release tails are not cut. */
static void pump_sequences(void)
{
    static int16_t pcm[C2_SEQUENCE_BUFFER_FRAMES * 2];
    static int tail_chunks;

    if (c2_music == NULL) return;
    if (any_sequence_playing()) tail_chunks = 16;
    else if (tail_chunks == 0) return;
    while (c2_host_audio_voice_queued_ms(C2_MUSIC_VOICE) <
           C2_SEQUENCE_QUEUE_TARGET_MS) {
        xmi_player_render(c2_music, pcm, C2_SEQUENCE_BUFFER_FRAMES);
        if (!c2_host_audio_queue_pcm(C2_MUSIC_VOICE, pcm, sizeof(pcm),
                                     C2_MUSIC_SAMPLE_RATE, 2, 16, 0)) {
            break;
        }
        if (!any_sequence_playing() && --tail_chunks == 0) break;
    }
}

void AIL_shutdown(void)
{
    xmi_player_destroy(c2_music);
    c2_music = NULL;
    memset(c2_sequences, 0, sizeof(c2_sequences));
    c2_next_sequence_handle = 0;
    c2_host_audio_shutdown();
}

int AIL_startup(void)
{
    c2_next_sequence_handle = 0;
    return 1;
}

int AIL_install_DIG_INI(int *dig_handle_out)
{
    int result;

    result = c2_host_audio_init(C2_AUDIO_VOICE_COUNT);
    if (result) {
        c2_next_sample_handle = 0;
        if (dig_handle_out != NULL) *dig_handle_out = 1;
    }
    if (!result) c2inf.samples_on = 0;
    return result ? 0 : 1;
}

int AIL_allocate_sample_handle(int dig_handle)
{
    (void)dig_handle;
    if (c2_next_sample_handle >= C2_SAMPLE_VOICE_COUNT) return 0;
    c2_next_sample_handle++;
    return c2_next_sample_handle;
}

void AIL_init_sample(int handle)
{
    struct c2_ail_sample *sample;

    sample = sample_from_handle(handle);
    if (sample == NULL) return;
    sample->wav = NULL;
    sample->wav_size = 0;
    sample->loop_count = 1;
    sample->status = 2;
}

int AIL_set_sample_file(int handle, void *buffer, int block)
{
    struct c2_ail_sample *sample;
    const unsigned char *bytes;
    size_t size;

    (void)block;
    sample = sample_from_handle(handle);
    bytes = buffer;
    if (sample == NULL || bytes == NULL) return 0;
    if (bytes[0] != 'R' || bytes[1] != 'I' || bytes[2] != 'F' ||
        bytes[3] != 'F' || bytes[8] != 'W' || bytes[9] != 'A' ||
        bytes[10] != 'V' || bytes[11] != 'E') {
        return 0;
    }
    size = (size_t)read_u32_le(bytes + 4) + 8;
    if (size < 12 || size > C2_SAMPLE_BUFFER_LIMIT) return 0;
    sample->wav = bytes;
    sample->wav_size = size;
    return 1;
}

void AIL_set_sample_loop_count(int handle, int loops)
{
    struct c2_ail_sample *sample;

    sample = sample_from_handle(handle);
    if (sample != NULL) sample->loop_count = loops;
}

char *AIL_start_sample(int handle)
{
    struct c2_ail_sample *sample;

    sample = sample_from_handle(handle);
    if (sample == NULL || sample->wav == NULL) return NULL;
    if (!c2_host_audio_play_wav(handle - 1, sample->wav, sample->wav_size,
                                sample->loop_count)) {
        sample->status = 2;
        return NULL;
    }
    sample->status = 4;
    return (char *)sample->wav;
}

int AIL_sample_status(int handle)
{
    struct c2_ail_sample *sample;

    sample = sample_from_handle(handle);
    if (sample == NULL) return 2;
    if (sample->status == 4 &&
        !c2_host_audio_voice_playing(handle - 1)) {
        sample->status = 2;
    }
    return sample->status;
}

void AIL_end_sample(int handle)
{
    struct c2_ail_sample *sample;

    sample = sample_from_handle(handle);
    if (sample == NULL) return;
    c2_host_audio_stop_voice(handle - 1);
    sample->status = 2;
}

void AIL_stop_sample(int handle)
{
    struct c2_ail_sample *sample;

    sample = sample_from_handle(handle);
    if (sample == NULL || sample->status != 4) return;
    c2_host_audio_pause_voice(handle - 1);
    sample->status = 8;
}

void AIL_resume_sample(int handle)
{
    struct c2_ail_sample *sample;

    sample = sample_from_handle(handle);
    if (sample == NULL || sample->status != 8) return;
    c2_host_audio_resume_voice(handle - 1);
    sample->status = 4;
}

void AIL_set_digital_master_volume(int dig_handle, int volume)
{
    int voice;

    (void)dig_handle;
    for (voice = 0; voice < C2_DIGITAL_VOICE_COUNT; voice++) {
        c2_host_audio_set_voice_gain(voice, (float)volume / 127.0f);
    }
}

void AIL_set_sample_type(int handle, int format, int flags)
{
    (void)handle;
    (void)format;
    (void)flags;
}

void AIL_set_sample_playback_rate(int handle, int rate_hz)
{
    (void)handle;
    (void)rate_hz;
}

int AIL_minimum_sample_buffer_size(int dig_handle, int rate_hz, int bits)
{
    (void)dig_handle;
    (void)rate_hz;
    (void)bits;
    return 10000;
}

int AIL_sample_buffer_ready(int handle)
{
    (void)handle;
    return -1;
}

void AIL_load_sample_buffer(int handle, int slot, void *buffer, int size)
{
    (void)handle;
    (void)slot;
    (void)buffer;
    (void)size;
}

void AIL_set_GTL_filename_prefix(char *prefix)
{
    (void)prefix;
}

int AIL_install_MDI_INI(int *mdi_handle_out)
{
    if (!c2_host_audio_init(C2_AUDIO_VOICE_COUNT)) {
        c2inf.tunes_on = 0;
        return 1;
    }
    if (c2_music == NULL) {
        c2_music = xmi_player_create(C2_MUSIC_SAMPLE_RATE);
        if (c2_music == NULL || !load_music_bank(c2_music)) {
            fprintf(stderr, "could not load the Miles OPL bank "
                            "(CAESAR.OPL or CAESAR.AD)\n");
            xmi_player_destroy(c2_music);
            c2_music = NULL;
            c2inf.tunes_on = 0;
            return 1;
        }
    }
    if (mdi_handle_out != NULL) *mdi_handle_out = 1;
    return 0;
}

int AIL_allocate_sequence_handle(int mdi_handle)
{
    struct c2_ail_sequence *sequence;

    (void)mdi_handle;
    if (c2_music == NULL || c2_next_sequence_handle >= C2_SEQUENCE_COUNT) {
        return 0;
    }
    sequence = &c2_sequences[c2_next_sequence_handle];
    memset(sequence, 0, sizeof(*sequence));
    sequence->sequence = xmi_sequence_create(xmi_player_driver(c2_music));
    if (sequence->sequence == NULL) return 0;
    c2_next_sequence_handle++;
    sequence->handle = c2_next_sequence_handle;
    return sequence->handle;
}

int AIL_sequence_status(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->sequence == NULL) return 2;
    return xmi_sequence_status(sequence->sequence);
}

void AIL_end_sequence(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->sequence == NULL) return;
    xmi_sequence_end(sequence->sequence);
}

void AIL_stop_sequence(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->sequence == NULL) return;
    xmi_sequence_stop(sequence->sequence);
}

void AIL_set_sequence_volume(int handle, int volume, int milliseconds)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->sequence == NULL) return;
    xmi_sequence_set_volume(sequence->sequence, volume, milliseconds);
}

int AIL_init_sequence(int handle, void *bytes, int sequence_num)
{
    struct c2_ail_sequence *sequence;
    size_t size;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->sequence == NULL) return 0;
    size = xmi_image_size(bytes, C2_SEQUENCE_DATA_LIMIT);
    if (size == 0) return 0;
    if (!xmi_sequence_init(sequence->sequence, bytes, size, sequence_num)) {
        return 0;
    }
    xmi_sequence_set_trigger_callback(sequence->sequence, sequence_trigger,
                                      sequence);
    return 1;
}

char *AIL_start_sequence(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->sequence == NULL) return NULL;
    xmi_sequence_start(sequence->sequence);
    pump_sequences();
    return (char *)sequence;
}

char *AIL_resume_sequence(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->sequence == NULL) return NULL;
    xmi_sequence_resume(sequence->sequence);
    pump_sequences();
    return (char *)sequence;
}

AILTRIGGERCB AIL_register_trigger_callback(int handle, AILTRIGGERCB callback)
{
    struct c2_ail_sequence *sequence;
    AILTRIGGERCB previous;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL) return NULL;
    previous = sequence->callback;
    sequence->callback = callback;
    return previous;
}

void AIL_branch_index(int handle, int marker)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->sequence == NULL || marker < 0) return;
    xmi_sequence_branch(sequence->sequence, (unsigned)marker);
}

void set_db_sound(char *filename)
{
    void *data;
    size_t size;

    if (c2inf.samples_on == 0 || c2inf.speech_on == 0 ||
        samples_running == 0 || db_playing != 0 || filename == NULL ||
        *filename == 0) {
        return;
    }
    data = c2_port_load_asset(filename, &size);
    if (data == NULL) return;
    if (c2_host_audio_play_pcm_u8(5, data, size, 22050, 1, 1)) {
        db_file = filename;
        db_playing = 1;
        c2_speech_paused = 0;
    }
    free(data);
}

void continue_db(void)
{
    pump_sequences();
    if (db_playing != 0 && !c2_speech_paused &&
        !c2_host_audio_voice_playing(5)) {
        db_playing = 0;
    }
}

void stop_db(void)
{
    if (db_playing == 0) return;
    c2_host_audio_stop_voice(5);
    db_playing = 0;
    c2_speech_paused = 0;
}

int pause_db(void)
{
    if (db_playing == 0) return 0;
    if (c2_speech_paused) {
        c2_host_audio_resume_voice(5);
        c2_speech_paused = 0;
    } else {
        c2_host_audio_pause_voice(5);
        c2_speech_paused = 1;
    }
    return 1;
}

static void play_beep(int frequency, int duration_ms)
{
    unsigned char *pcm;
    size_t sample_count;
    size_t i;

    if (c2inf.samples_on == 0 || samples_running == 0) return;
    sample_count = (size_t)22050 * (size_t)duration_ms / 1000;
    pcm = malloc(sample_count);
    if (pcm == NULL) return;
    for (i = 0; i < sample_count; i++) {
        pcm[i] = ((i * (size_t)frequency * 2 / 22050) & 1) ? 176 : 80;
    }
    c2_host_audio_play_pcm_u8(C2_BEEP_VOICE, pcm, sample_count,
                              22050, 1, 1);
    free(pcm);
    c2_host_sleep_ms((unsigned int)duration_ms);
}

void high_beep(void) { play_beep(880, 50); }
void low_beep(void) { play_beep(220, 50); }
void vhigh_beep(void) { play_beep(1720, 150); }
