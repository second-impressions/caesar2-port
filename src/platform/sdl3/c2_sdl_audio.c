#include <SDL3/SDL.h>

#include <limits.h>
#include <stdlib.h>

#include "c2_host.h"

static SDL_AudioDeviceID c2_audio_device;
struct c2_audio_voice {
    SDL_AudioStream *stream;
    Uint64 deadline_ms;
    Uint64 pause_started_ms;
    int paused;
};

static struct c2_audio_voice *c2_audio_voices;
static int c2_audio_voice_count;
static float c2_audio_master_gain = 1.0f;

static int valid_voice(int voice)
{
    return voice >= 0 && voice < c2_audio_voice_count;
}

static void destroy_voice(int voice)
{
    if (!valid_voice(voice) || c2_audio_voices[voice].stream == NULL) return;
    SDL_DestroyAudioStream(c2_audio_voices[voice].stream);
    c2_audio_voices[voice].stream = NULL;
    c2_audio_voices[voice].deadline_ms = 0;
    c2_audio_voices[voice].pause_started_ms = 0;
    c2_audio_voices[voice].paused = 0;
}

static int play_pcm(int voice, const SDL_AudioSpec *spec,
                    const void *data, size_t size, int loop_count)
{
    SDL_AudioStream *stream;
    Uint64 byte_rate;
    Uint64 duration_ms;
    int loop;

    if (!valid_voice(voice) || data == NULL || size == 0 ||
        size > INT_MAX) {
        return 0;
    }
    if (loop_count < 1) loop_count = 1;

    destroy_voice(voice);
    stream = SDL_CreateAudioStream(spec, NULL);
    if (stream == NULL ||
        !SDL_BindAudioStream(c2_audio_device, stream) ||
        !SDL_SetAudioStreamGain(stream, c2_audio_master_gain)) {
        SDL_DestroyAudioStream(stream);
        return 0;
    }
    for (loop = 0; loop < loop_count; loop++) {
        if (!SDL_PutAudioStreamData(stream, data, (int)size)) {
            SDL_DestroyAudioStream(stream);
            return 0;
        }
    }
    if (!SDL_FlushAudioStream(stream)) {
        SDL_DestroyAudioStream(stream);
        return 0;
    }
    byte_rate = (Uint64)SDL_AUDIO_BYTESIZE(spec->format) *
                (Uint64)spec->channels * (Uint64)spec->freq;
    duration_ms = ((Uint64)size * (Uint64)loop_count * 1000 +
                   byte_rate - 1) / byte_rate;
    c2_audio_voices[voice].stream = stream;
    c2_audio_voices[voice].deadline_ms = SDL_GetTicks() + duration_ms;
    return 1;
}

int c2_host_audio_init(int voice_count)
{
    if (c2_audio_device != 0) return 1;
    if (voice_count <= 0 || !SDL_InitSubSystem(SDL_INIT_AUDIO)) return 0;

    c2_audio_device = SDL_OpenAudioDevice(SDL_AUDIO_DEVICE_DEFAULT_PLAYBACK,
                                          NULL);
    if (c2_audio_device == 0) {
        SDL_QuitSubSystem(SDL_INIT_AUDIO);
        return 0;
    }
    c2_audio_voices = calloc((size_t)voice_count,
                             sizeof(*c2_audio_voices));
    if (c2_audio_voices == NULL) {
        SDL_CloseAudioDevice(c2_audio_device);
        c2_audio_device = 0;
        SDL_QuitSubSystem(SDL_INIT_AUDIO);
        return 0;
    }
    c2_audio_voice_count = voice_count;
    if (!SDL_ResumeAudioDevice(c2_audio_device)) {
        c2_host_audio_shutdown();
        return 0;
    }
    return 1;
}

void c2_host_audio_shutdown(void)
{
    int voice;

    for (voice = 0; voice < c2_audio_voice_count; voice++) {
        destroy_voice(voice);
    }
    free(c2_audio_voices);
    c2_audio_voices = NULL;
    c2_audio_voice_count = 0;
    if (c2_audio_device != 0) SDL_CloseAudioDevice(c2_audio_device);
    c2_audio_device = 0;
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
}

int c2_host_audio_play_wav(int voice, const void *data, size_t size,
                           int loop_count)
{
    SDL_AudioSpec spec;
    SDL_IOStream *io;
    Uint8 *pcm;
    Uint32 pcm_size;
    int result;

    if (data == NULL || size == 0) return 0;
    io = SDL_IOFromConstMem(data, size);
    if (io == NULL || !SDL_LoadWAV_IO(io, true, &spec, &pcm, &pcm_size)) {
        return 0;
    }
    result = play_pcm(voice, &spec, pcm, pcm_size, loop_count);
    SDL_free(pcm);
    return result;
}

int c2_host_audio_play_pcm_u8(int voice, const void *data, size_t size,
                              int sample_rate, int channels,
                              int loop_count)
{
    SDL_AudioSpec spec;

    if (sample_rate <= 0 || channels <= 0) return 0;
    spec.format = SDL_AUDIO_U8;
    spec.channels = channels;
    spec.freq = sample_rate;
    return play_pcm(voice, &spec, data, size, loop_count);
}

int c2_host_audio_voice_playing(int voice)
{
    if (!valid_voice(voice) || c2_audio_voices[voice].stream == NULL) return 0;
    if (c2_audio_voices[voice].paused ||
        SDL_GetTicks() < c2_audio_voices[voice].deadline_ms) {
        return 1;
    }
    destroy_voice(voice);
    return 0;
}

void c2_host_audio_stop_voice(int voice)
{
    destroy_voice(voice);
}

void c2_host_audio_pause_voice(int voice)
{
    if (valid_voice(voice) && c2_audio_voices[voice].stream != NULL &&
        !c2_audio_voices[voice].paused) {
        SDL_UnbindAudioStream(c2_audio_voices[voice].stream);
        c2_audio_voices[voice].pause_started_ms = SDL_GetTicks();
        c2_audio_voices[voice].paused = 1;
    }
}

void c2_host_audio_resume_voice(int voice)
{
    Uint64 paused_ms;

    if (valid_voice(voice) && c2_audio_voices[voice].stream != NULL &&
        c2_audio_voices[voice].paused) {
        paused_ms = SDL_GetTicks() -
                    c2_audio_voices[voice].pause_started_ms;
        if (SDL_BindAudioStream(c2_audio_device,
                                c2_audio_voices[voice].stream)) {
            c2_audio_voices[voice].deadline_ms += paused_ms;
            c2_audio_voices[voice].pause_started_ms = 0;
            c2_audio_voices[voice].paused = 0;
        }
    }
}

void c2_host_audio_set_master_gain(float gain)
{
    int voice;

    if (gain < 0.0f) gain = 0.0f;
    c2_audio_master_gain = gain;
    for (voice = 0; voice < c2_audio_voice_count; voice++) {
        if (c2_audio_voices[voice].stream != NULL) {
            SDL_SetAudioStreamGain(c2_audio_voices[voice].stream, gain);
        }
    }
}
