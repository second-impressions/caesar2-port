#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <adlmidi.h>

#include "ail.h"
#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"
#include "c2_port_miles_bank.h"
#include "pcsound.h"

#define C2_SAMPLE_VOICE_COUNT 6
#define C2_AUDIO_VOICE_COUNT 10
#define C2_BEEP_VOICE 6
#define C2_DIGITAL_VOICE_COUNT 8
#define C2_MUSIC_VOICE_FIRST 8
#define C2_SEQUENCE_COUNT 2
#define C2_SEQUENCE_BUFFER_SAMPLES 4096
#define C2_SEQUENCE_QUEUE_TARGET_MS 100
#define C2_SEQUENCE_DATA_LIMIT C2_TUNE_BUFFER_SIZE
#define C2_CAESAR_BANK 40
#define C2_SAMPLE_BUFFER_LIMIT 20000

struct c2_ail_sample {
    const unsigned char *wav;
    size_t wav_size;
    int loop_count;
    int status;
};

struct c2_ail_sequence {
    struct ADL_MIDIPlayer *player;
    AILTRIGGERCB callback;
    uint64_t fade_started_ms;
    uint64_t fade_ends_ms;
    float fade_started_gain;
    float gain;
    float target_gain;
    int handle;
    int status;
};

static struct c2_ail_sample c2_samples[C2_SAMPLE_VOICE_COUNT];
static struct c2_ail_sequence c2_sequences[C2_SEQUENCE_COUNT];
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

static uint32_t read_u32_be(const unsigned char *bytes)
{
    return ((uint32_t)bytes[0] << 24) |
           ((uint32_t)bytes[1] << 16) |
           ((uint32_t)bytes[2] << 8) |
           (uint32_t)bytes[3];
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

static size_t xmi_size(const unsigned char *bytes)
{
    size_t xdir_size;
    size_t cat_offset;
    size_t cat_size;

    if (bytes == NULL || memcmp(bytes, "FORM", 4) != 0) return 0;
    xdir_size = (size_t)read_u32_be(bytes + 4);
    if (xdir_size > C2_SEQUENCE_DATA_LIMIT - 8) return 0;
    cat_offset = 8 + ((xdir_size + 1) & ~(size_t)1);
    if (cat_offset > C2_SEQUENCE_DATA_LIMIT - 8 ||
        memcmp(bytes + cat_offset, "CAT ", 4) != 0) {
        return 0;
    }
    cat_size = (size_t)read_u32_be(bytes + cat_offset + 4);
    if (cat_size > C2_SEQUENCE_DATA_LIMIT - cat_offset - 8) return 0;
    return cat_offset + 8 + ((cat_size + 1) & ~(size_t)1);
}

static int load_miles_bank(struct ADL_MIDIPlayer *player)
{
    unsigned char *data;
    size_t data_size;
    int result;

    data = c2_port_load_asset("caesar.opl", &data_size);
    if (data == NULL) data = c2_port_load_asset("caesar.ad", &data_size);
    if (data == NULL) return 0;
    result = c2_port_apply_miles_bank(player, data, data_size);
    free(data);
    return result;
}

static void sequence_trigger(void *user_data, unsigned trigger, size_t track)
{
    struct c2_ail_sequence *sequence;

    sequence = user_data;
    if (sequence != NULL && sequence->callback != NULL) {
        sequence->callback(sequence->handle, (int)trigger, (int)track);
    }
}

static void update_sequence_gain(struct c2_ail_sequence *sequence)
{
    uint64_t now;
    float progress;

    if (sequence == NULL || sequence->fade_ends_ms == 0) return;
    now = c2_host_ticks_ms();
    if (now >= sequence->fade_ends_ms) {
        sequence->gain = sequence->target_gain;
        sequence->fade_started_ms = 0;
        sequence->fade_ends_ms = 0;
    } else {
        progress = (float)(now - sequence->fade_started_ms) /
                   (float)(sequence->fade_ends_ms - sequence->fade_started_ms);
        sequence->gain = sequence->fade_started_gain +
                         (sequence->target_gain - sequence->fade_started_gain) *
                         progress;
    }
    c2_host_audio_set_voice_gain(C2_MUSIC_VOICE_FIRST + sequence->handle - 1,
                                 sequence->gain);
}

static void pump_sequences(void)
{
    short pcm[C2_SEQUENCE_BUFFER_SAMPLES];
    struct c2_ail_sequence *sequence;
    int generated;
    int index;
    int voice;

    for (index = 0; index < C2_SEQUENCE_COUNT; index++) {
        sequence = &c2_sequences[index];
        if (sequence->player == NULL || sequence->status != 4) continue;
        voice = C2_MUSIC_VOICE_FIRST + index;
        update_sequence_gain(sequence);
        while (c2_host_audio_voice_queued_ms(voice) <
               C2_SEQUENCE_QUEUE_TARGET_MS) {
            generated = adl_play(sequence->player,
                                 C2_SEQUENCE_BUFFER_SAMPLES, pcm);
            if (generated <= 0) {
                sequence->status = 2;
                break;
            }
            if (!c2_host_audio_queue_pcm(voice, pcm,
                    (size_t)generated * sizeof(*pcm), 44100, 2, 16,
                    adl_atEnd(sequence->player))) {
                sequence->status = 2;
                break;
            }
            if (adl_atEnd(sequence->player)) {
                sequence->status = 2;
                break;
            }
        }
    }
}

void AIL_shutdown(void)
{
    int index;

    for (index = 0; index < C2_SEQUENCE_COUNT; index++) {
        if (c2_sequences[index].player != NULL) {
            adl_close(c2_sequences[index].player);
        }
    }
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
    if (mdi_handle_out != NULL) *mdi_handle_out = 1;
    return 0;
}

int AIL_allocate_sequence_handle(int mdi_handle)
{
    struct c2_ail_sequence *sequence;

    (void)mdi_handle;
    if (c2_next_sequence_handle >= C2_SEQUENCE_COUNT) return 0;
    sequence = &c2_sequences[c2_next_sequence_handle];
    memset(sequence, 0, sizeof(*sequence));
    sequence->player = adl_init(44100);
    if (sequence->player == NULL) {
        fprintf(stderr, "could not initialize libADLMIDI: %s\n",
                adl_errorString());
        return 0;
    }
    if (adl_setBank(sequence->player, C2_CAESAR_BANK) < 0 ||
        adl_setNumChips(sequence->player, 1) < 0 ||
        !load_miles_bank(sequence->player)) {
        fprintf(stderr, "could not configure libADLMIDI: %s\n",
                adl_errorInfo(sequence->player));
        adl_close(sequence->player);
        sequence->player = NULL;
        return 0;
    }
    adl_setVolumeRangeModel(sequence->player, ADLMIDI_VolumeModel_AIL);
    adl_setLoopEnabled(sequence->player, 1);
    c2_next_sequence_handle++;
    sequence->handle = c2_next_sequence_handle;
    sequence->gain = 1.0f;
    sequence->target_gain = 1.0f;
    sequence->status = 2;
    return sequence->handle;
}

int AIL_sequence_status(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL) return 2;
    return sequence->status;
}

void AIL_end_sequence(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->player == NULL) return;
    c2_host_audio_stop_voice(C2_MUSIC_VOICE_FIRST + handle - 1);
    adl_positionRewind(sequence->player);
    sequence->status = 2;
}

void AIL_stop_sequence(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->status != 4) return;
    c2_host_audio_stop_voice(C2_MUSIC_VOICE_FIRST + handle - 1);
    sequence->status = 8;
}

void AIL_set_sequence_volume(int handle, int volume, int milliseconds)
{
    struct c2_ail_sequence *sequence;
    uint64_t now;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL) return;
    if (volume < 0) volume = 0;
    if (volume > 127) volume = 127;
    update_sequence_gain(sequence);
    sequence->target_gain = (float)volume / 127.0f;
    if (milliseconds <= 0) {
        sequence->gain = sequence->target_gain;
        sequence->fade_started_ms = 0;
        sequence->fade_ends_ms = 0;
        c2_host_audio_set_voice_gain(C2_MUSIC_VOICE_FIRST + handle - 1,
                                     sequence->gain);
        return;
    }
    now = c2_host_ticks_ms();
    sequence->fade_started_gain = sequence->gain;
    sequence->fade_started_ms = now;
    sequence->fade_ends_ms = now + (uint64_t)milliseconds;
}
int AIL_init_sequence(int handle, void *bytes, int sequence_num)
{
    struct c2_ail_sequence *sequence;
    size_t size;

    (void)sequence_num;
    sequence = sequence_from_handle(handle);
    size = xmi_size(bytes);
    if (sequence == NULL || sequence->player == NULL || size == 0) return 0;
    c2_host_audio_stop_voice(C2_MUSIC_VOICE_FIRST + handle - 1);
    if (adl_openData(sequence->player, bytes, (unsigned long)size) < 0) return 0;
    adl_setTriggerHandler(sequence->player, sequence_trigger, sequence);
    sequence->status = 2;
    return 1;
}

char *AIL_start_sequence(int handle)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->player == NULL) return NULL;
    sequence->status = 4;
    pump_sequences();
    return (char *)sequence;
}

char *AIL_resume_sequence(int handle)
{
    return AIL_start_sequence(handle);
}

AILTRIGGERCB AIL_register_trigger_callback(int handle, AILTRIGGERCB callback)
{
    struct c2_ail_sequence *sequence;
    AILTRIGGERCB previous;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL) return NULL;
    previous = sequence->callback;
    sequence->callback = callback;
    if (sequence->player != NULL) {
        adl_setTriggerHandler(sequence->player, sequence_trigger, sequence);
    }
    return previous;
}
void AIL_branch_index(int handle, int marker)
{
    struct c2_ail_sequence *sequence;

    sequence = sequence_from_handle(handle);
    if (sequence == NULL || sequence->player == NULL || marker < 0) return;
    adl_jumpToBranch(sequence->player, (unsigned)marker);
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
