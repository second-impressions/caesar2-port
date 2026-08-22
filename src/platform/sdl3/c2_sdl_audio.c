#include <SDL3/SDL.h>

#include <limits.h>
#include <stdlib.h>

#include "c2_host.h"

static SDL_AudioDeviceID c2_audio_device;
struct c2_audio_voice {
    SDL_AudioStream *stream;
    SDL_AudioSpec source_spec;
    Uint64 deadline_ms;
    Uint64 pause_started_ms;
    float gain;
    int paused;
#if PORT_FEAT_DEBUG_OBSERVATION
    SDL_AtomicU32 produced_bytes;
    SDL_AtomicU32 underflow_bytes;
    SDL_AtomicU32 queue_calls;
    SDL_AtomicU32 device_requests;
    SDL_AtomicU32 underflows;
#endif
};

static struct c2_audio_voice *c2_audio_voices;
static int c2_audio_voice_count;
static float c2_audio_master_gain = 1.0f;

#if PORT_FEAT_DEBUG_OBSERVATION && !PORT_PLATFORM_WASM
static void SDLCALL observe_audio_request(void *userdata,
                                          SDL_AudioStream *stream,
                                          int additional_amount,
                                          int total_amount)
{
    struct c2_audio_voice *voice;
    int voice_index;

    (void)stream;
    (void)total_amount;
    voice_index = (int)(uintptr_t)userdata - 1;
    if (voice_index < 0 || voice_index >= c2_audio_voice_count) return;
    voice = &c2_audio_voices[voice_index];
    SDL_AddAtomicU32(&voice->device_requests, 1);
    if (additional_amount > 0) {
        SDL_AddAtomicU32(&voice->underflows, 1);
        SDL_AddAtomicU32(&voice->underflow_bytes, additional_amount);
    }
}
#endif

static int valid_voice(int voice)
{
    return voice >= 0 && voice < c2_audio_voice_count;
}

static void destroy_voice(int voice)
{
    if (!valid_voice(voice) || c2_audio_voices[voice].stream == NULL) return;
    SDL_DestroyAudioStream(c2_audio_voices[voice].stream);
    c2_audio_voices[voice].stream = NULL;
    SDL_zero(c2_audio_voices[voice].source_spec);
    c2_audio_voices[voice].deadline_ms = 0;
    c2_audio_voices[voice].pause_started_ms = 0;
    c2_audio_voices[voice].paused = 0;
}

static int same_spec(const SDL_AudioSpec *left, const SDL_AudioSpec *right)
{
    return left->format == right->format &&
           left->channels == right->channels &&
           left->freq == right->freq;
}

static int queue_pcm(int voice, const SDL_AudioSpec *spec,
                     const void *data, size_t size, int loop_count,
                     int replace, int flush)
{
    SDL_AudioStream *stream;
    Uint64 byte_rate;
    Uint64 duration_ms;
    Uint64 now;
    Uint64 start_ms;
    int loop;
#if PORT_FEAT_DEBUG_OBSERVATION
    int new_stream;
#endif

    if (!valid_voice(voice) || data == NULL || size == 0 ||
        size > INT_MAX) {
        return 0;
    }
    if (loop_count < 1) loop_count = 1;

    if (replace) destroy_voice(voice);
    stream = c2_audio_voices[voice].stream;
#if PORT_FEAT_DEBUG_OBSERVATION
    new_stream = stream == NULL;
#endif
    if (stream == NULL) {
        stream = SDL_CreateAudioStream(spec, NULL);
        if (stream == NULL ||
            !SDL_BindAudioStream(c2_audio_device, stream) ||
            !SDL_SetAudioStreamGain(stream, c2_audio_master_gain *
                                            c2_audio_voices[voice].gain)) {
            SDL_DestroyAudioStream(stream);
            return 0;
        }
        c2_audio_voices[voice].stream = stream;
        c2_audio_voices[voice].source_spec = *spec;
    } else if (!same_spec(&c2_audio_voices[voice].source_spec, spec)) {
        return 0;
    }
    for (loop = 0; loop < loop_count; loop++) {
        if (!SDL_PutAudioStreamData(stream, data, (int)size)) {
            destroy_voice(voice);
            return 0;
        }
#if PORT_FEAT_DEBUG_OBSERVATION
        SDL_AddAtomicU32(&c2_audio_voices[voice].produced_bytes, (int)size);
#endif
    }
#if PORT_FEAT_DEBUG_OBSERVATION
    SDL_AddAtomicU32(&c2_audio_voices[voice].queue_calls, 1);
#if !PORT_PLATFORM_WASM
    if (new_stream &&
        !SDL_SetAudioStreamGetCallback(
            stream, observe_audio_request,
            (void *)(uintptr_t)(voice + 1))) {
        destroy_voice(voice);
        return 0;
    }
#else
    (void)new_stream;
#endif
#endif
    if (flush && !SDL_FlushAudioStream(stream)) {
        destroy_voice(voice);
        return 0;
    }
    byte_rate = (Uint64)SDL_AUDIO_BYTESIZE(spec->format) *
                (Uint64)spec->channels * (Uint64)spec->freq;
    duration_ms = ((Uint64)size * (Uint64)loop_count * 1000 +
                   byte_rate - 1) / byte_rate;
    now = SDL_GetTicks();
    start_ms = c2_audio_voices[voice].deadline_ms;
    if (start_ms < now) start_ms = now;
    c2_audio_voices[voice].deadline_ms = start_ms + duration_ms;
    return 1;
}

int c2_host_audio_init(int voice_count)
{
    struct c2_audio_voice *voices;
    int voice;

    if (voice_count <= 0) return 0;
    if (c2_audio_device != 0) {
        if (voice_count <= c2_audio_voice_count) return 1;
        voices = realloc(c2_audio_voices,
                         (size_t)voice_count * sizeof(*voices));
        if (voices == NULL) return 0;
        c2_audio_voices = voices;
        SDL_memset(c2_audio_voices + c2_audio_voice_count, 0,
                   (size_t)(voice_count - c2_audio_voice_count) *
                       sizeof(*c2_audio_voices));
        for (voice = c2_audio_voice_count; voice < voice_count; voice++) {
            c2_audio_voices[voice].gain = 1.0f;
        }
        c2_audio_voice_count = voice_count;
        return 1;
    }
    if (!SDL_InitSubSystem(SDL_INIT_AUDIO)) return 0;

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
    for (voice = 0; voice < voice_count; voice++) {
        c2_audio_voices[voice].gain = 1.0f;
    }
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
    result = queue_pcm(voice, &spec, pcm, pcm_size, loop_count, 1, 1);
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
    return queue_pcm(voice, &spec, data, size, loop_count, 1, 1);
}

int c2_host_audio_queue_pcm(int voice, const void *data, size_t size,
                            int sample_rate, int channels, int bit_depth,
                            int final_chunk)
{
    SDL_AudioSpec spec;

    if (sample_rate <= 0 || channels <= 0) return 0;
    if (bit_depth == 8) {
        spec.format = SDL_AUDIO_U8;
    } else if (bit_depth == 16) {
        spec.format = SDL_AUDIO_S16LE;
    } else {
        return 0;
    }
    spec.channels = channels;
    spec.freq = sample_rate;
    return queue_pcm(voice, &spec, data, size, 1, 0, final_chunk);
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

unsigned int c2_host_audio_voice_queued_ms(int voice)
{
    struct c2_audio_voice *audio_voice;
    Uint64 byte_rate;
    Uint64 queued_ms;
    int queued;

    if (!valid_voice(voice) || c2_audio_voices[voice].stream == NULL) return 0;
    audio_voice = &c2_audio_voices[voice];
    queued = SDL_GetAudioStreamQueued(audio_voice->stream);
    if (queued <= 0) return 0;
    byte_rate =
        (Uint64)SDL_AUDIO_BYTESIZE(audio_voice->source_spec.format) *
        (Uint64)audio_voice->source_spec.channels *
        (Uint64)audio_voice->source_spec.freq;
    if (byte_rate == 0) return 0;
    queued_ms = ((Uint64)queued * 1000) / byte_rate;
    if (queued_ms > UINT_MAX) return UINT_MAX;
    return (unsigned int)queued_ms;
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

void c2_host_audio_set_voice_gain(int voice, float gain)
{
    if (!valid_voice(voice)) return;
    if (gain < 0.0f) gain = 0.0f;
    c2_audio_voices[voice].gain = gain;
    if (c2_audio_voices[voice].stream != NULL) {
        SDL_SetAudioStreamGain(c2_audio_voices[voice].stream,
                               gain * c2_audio_master_gain);
    }
}

void c2_host_audio_set_master_gain(float gain)
{
    int voice;

    if (gain < 0.0f) gain = 0.0f;
    c2_audio_master_gain = gain;
    for (voice = 0; voice < c2_audio_voice_count; voice++) {
        if (c2_audio_voices[voice].stream != NULL) {
            SDL_SetAudioStreamGain(c2_audio_voices[voice].stream,
                                   gain * c2_audio_voices[voice].gain);
        }
    }
}

#if PORT_FEAT_DEBUG_OBSERVATION
int c2_host_audio_observation_snapshot(
    int voice, struct c2_host_audio_observation *observation)
{
    struct c2_audio_voice *audio_voice;
    Uint64 byte_rate;
    Uint64 deadline;
    Uint64 now;
    int queued;

    if (!valid_voice(voice) || observation == NULL) return 0;
    SDL_memset(observation, 0, sizeof(*observation));
    audio_voice = &c2_audio_voices[voice];
    observation->produced_bytes =
        (uint64_t)SDL_GetAtomicU32(
            &audio_voice->produced_bytes);
    observation->underflow_bytes =
        (uint64_t)SDL_GetAtomicU32(
            &audio_voice->underflow_bytes);
    observation->queue_calls =
        (unsigned int)SDL_GetAtomicU32(&audio_voice->queue_calls);
    observation->device_requests =
        (unsigned int)SDL_GetAtomicU32(&audio_voice->device_requests);
    observation->underflows =
        (unsigned int)SDL_GetAtomicU32(&audio_voice->underflows);
    now = SDL_GetTicks();
    deadline = audio_voice->deadline_ms;
    if (deadline > now) {
        if (deadline - now > UINT_MAX) {
            observation->estimated_queued_ms = UINT_MAX;
        } else {
            observation->estimated_queued_ms =
                (unsigned int)(deadline - now);
        }
    }
    if (audio_voice->stream == NULL) return 1;

    observation->active = 1;
    queued = SDL_GetAudioStreamQueued(audio_voice->stream);
    if (queued < 0) return 0;
    observation->queued_bytes = (unsigned int)queued;
    byte_rate =
        (Uint64)SDL_AUDIO_BYTESIZE(audio_voice->source_spec.format) *
        (Uint64)audio_voice->source_spec.channels *
        (Uint64)audio_voice->source_spec.freq;
    if (byte_rate != 0) {
        observation->queued_ms =
            (unsigned int)(((Uint64)queued * 1000) / byte_rate);
    }
    return 1;
}
#endif
