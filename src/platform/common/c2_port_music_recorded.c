/*
 * Recorded music: the Windows 95 version's soundtrack.
 *
 * The DOS game sequences XMIDI scores through an OPL synthesizer. The
 * Windows version (on every CD from August 1996, in C2WIN95/RAW/, and at
 * the root of the 1998 US pressing, which has no XMI at all) streams eight
 * 8-bit 22050 Hz mono recordings of the same music instead, as its
 * winaudio.c and CAESAR2.EXE show:
 *
 *   cityprov.xmi   CITYPRO0..2.RAW   played in turn, each to its end
 *   forum1..3.xmi  FORUM0..2.RAW     one per forum visit, looped
 *   batest2.xmi    BATTLE0.RAW       looped
 *
 * The recovered engine still asks for the XMI names; play_tune() offers
 * each request here first (PORT_FEAT_RECORDED_MUSIC). When the recordings
 * are the chosen source the request is answered by streaming the matching
 * file, with the same two-slot behaviour start_tune() gives sequences: the
 * city tune (slot 0) pauses while a forum or battle tune (slot 1) plays and
 * resumes afterwards. Either source can be chosen when the data has both.
 */
#include <stdio.h>
#include <string.h>

#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"

#if PORT_FEAT_RECORDED_MUSIC

#define C2_RECORDED_SAMPLE_RATE 22050
#define C2_RECORDED_FIRST_VOICE 9      /* slot 0 and 1: voices 9 and 10 */
#define C2_RECORDED_VOICE_COUNT 11
#define C2_RECORDED_CHUNK_BYTES 5512   /* 250 ms */
#define C2_RECORDED_QUEUE_TARGET_MS 500
#define C2_RECORDED_CITY_TUNES 3
#define C2_RECORDED_SLOTS 2

struct c2_recorded_slot {
    char filename[16];   /* the RAW being streamed, "" when idle */
    uint64_t size;
    uint64_t offset;
    int playing;         /* streaming, or paused mid-stream */
    int paused;
    int loop;            /* slot 1 loops; slot 0 moves on to the next tune */
    float gain;          /* current, following the fade */
    float target_gain;
    float gain_step;     /* per pump call while fading */
};

static struct c2_recorded_slot c2_recorded[C2_RECORDED_SLOTS];
static int c2_recorded_city_tune;          /* cityprov_tune of winaudio.c */
/* The DOS music is what this engine was written for, and the only place it
 * can be heard: the Windows recordings exist as ordinary audio files. */
static enum c2_port_music_source c2_recorded_preference = C2_PORT_MUSIC_XMIDI;
static char c2_recorded_last_request[C2_RECORDED_SLOTS][16];
static int c2_recorded_secondary_active;

extern void stop_tune(void);
extern void play_tune(unsigned char *filename, int loop_count);

int c2_port_music_recorded_available(void)
{
    return c2_host_asset_size("citypro0.raw") > 0;
}

int c2_port_music_xmidi_available(void)
{
    return c2_host_asset_size("cityprov.xmi") > 0 &&
           (c2_host_asset_size("caesar.opl") > 0 ||
            c2_host_asset_size("caesar.ad") > 0);
}

enum c2_port_music_source c2_port_music_preference(void)
{
    return c2_recorded_preference;
}

enum c2_port_music_source c2_port_music_source(void)
{
    if (c2_recorded_preference == C2_PORT_MUSIC_RECORDED) {
        return c2_port_music_recorded_available() ? C2_PORT_MUSIC_RECORDED
                                                  : C2_PORT_MUSIC_XMIDI;
    }
    return c2_port_music_xmidi_available() || !c2_port_music_recorded_available()
               ? C2_PORT_MUSIC_XMIDI
               : C2_PORT_MUSIC_RECORDED;
}

const char *c2_port_music_source_name(enum c2_port_music_source source)
{
    return source == C2_PORT_MUSIC_RECORDED ? "windows" : "dos";
}

int c2_port_music_source_parse(const char *name, enum c2_port_music_source *out)
{
    if (name == NULL) return 0;
    /* The stored and typed names are the versions; the older spellings are
     * still read, so a settings file from before this keeps working. */
    if (strcmp(name, "windows") == 0 || strcmp(name, "recorded") == 0) {
        *out = C2_PORT_MUSIC_RECORDED;
        return 1;
    }
    if (strcmp(name, "dos") == 0 || strcmp(name, "xmidi") == 0) {
        *out = C2_PORT_MUSIC_XMIDI;
        return 1;
    }
    return 0;
}

/* The XMI the engine asks for, as the Windows version's RAW. */
static int recorded_name_for(const char *xmi, int slot, char *out, size_t capacity)
{
    if (slot == 0) {
        snprintf(out, capacity, "citypro%d.raw", c2_recorded_city_tune);
        return 1;
    }
    if (strncmp(xmi, "forum", 5) == 0 && xmi[5] >= '1' && xmi[5] <= '3') {
        snprintf(out, capacity, "forum%c.raw", xmi[5] - 1);
        return 1;
    }
    if (strncmp(xmi, "batest", 6) == 0) {
        snprintf(out, capacity, "battle0.raw");
        return 1;
    }
    return 0;
}

static int voice_of(int slot)
{
    return C2_RECORDED_FIRST_VOICE + slot;
}

static float music_gain(void)
{
    int level = c2inf.tunes_level;
    if (level < 0) level = 0;
    if (level > 100) level = 100;
    return (float)level / 100.0f;
}

static void slot_end(int slot)
{
    struct c2_recorded_slot *s = &c2_recorded[slot];
    if (s->playing) c2_host_audio_stop_voice(voice_of(slot));
    memset(s, 0, sizeof(*s));
}

static void slot_set_gain(int slot, float target, int fade_ms)
{
    struct c2_recorded_slot *s = &c2_recorded[slot];
    s->target_gain = target;
    if (fade_ms <= 0) {
        s->gain = target;
        s->gain_step = 0.0f;
    } else {
        /* The pump runs about every frame; step so the fade takes fade_ms
         * at 50 pumps per second, which is what a one-second fade sounds
         * like in the original. */
        s->gain_step = (target - s->gain) / ((float)fade_ms / 20.0f);
    }
    c2_host_audio_set_voice_gain(voice_of(slot), s->gain);
}

static int slot_start(int slot, const char *filename, int loop)
{
    struct c2_recorded_slot *s = &c2_recorded[slot];
    uint64_t size = c2_host_asset_size(filename);

    slot_end(slot);
    if (size == 0) return 0;
    if (!c2_host_audio_init(C2_RECORDED_VOICE_COUNT)) return 0;
    snprintf(s->filename, sizeof(s->filename), "%s", filename);
    s->size = size;
    s->offset = 0;
    s->playing = 1;
    s->loop = loop;
    s->gain = 0.0f;
    slot_set_gain(slot, music_gain(), 1000);
    c2_port_recorded_music_pump();
    return 1;
}

static void slot_pause(int slot)
{
    struct c2_recorded_slot *s = &c2_recorded[slot];
    if (!s->playing || s->paused) return;
    c2_host_audio_pause_voice(voice_of(slot));
    s->paused = 1;
}

static void slot_resume(int slot)
{
    struct c2_recorded_slot *s = &c2_recorded[slot];
    if (!s->playing || !s->paused) return;
    c2_host_audio_resume_voice(voice_of(slot));
    s->paused = 0;
    slot_set_gain(slot, music_gain(), 0);
}

/* Keep both voices fed; at a file's end loop it or move to the next city
 * tune. Runs from continue_db(), i.e. every engine loop. */
void c2_port_recorded_music_pump(void)
{
    static unsigned char chunk[C2_RECORDED_CHUNK_BYTES];
    int slot;

    for (slot = 0; slot < C2_RECORDED_SLOTS; slot++) {
        struct c2_recorded_slot *s = &c2_recorded[slot];
        if (!s->playing || s->paused) continue;
        if (s->gain_step != 0.0f) {
            s->gain += s->gain_step;
            if ((s->gain_step > 0.0f && s->gain >= s->target_gain) ||
                (s->gain_step < 0.0f && s->gain <= s->target_gain)) {
                s->gain = s->target_gain;
                s->gain_step = 0.0f;
            }
            c2_host_audio_set_voice_gain(voice_of(slot), s->gain);
        }
        while (c2_host_audio_voice_queued_ms(voice_of(slot)) < C2_RECORDED_QUEUE_TARGET_MS) {
            size_t wanted = sizeof(chunk);
            size_t got;
            if (s->offset >= s->size) {
                if (s->loop) {
                    s->offset = 0;
                } else if (slot == 0) {
                    /* play_next_tune: the next city tune, round robin. */
                    char next[16];
                    c2_recorded_city_tune = (c2_recorded_city_tune + 1) % C2_RECORDED_CITY_TUNES;
                    snprintf(next, sizeof(next), "citypro%d.raw", c2_recorded_city_tune);
                    s->size = c2_host_asset_size(next);
                    if (s->size == 0) { slot_end(slot); break; }
                    snprintf(s->filename, sizeof(s->filename), "%s", next);
                    s->offset = 0;
                } else {
                    slot_end(slot);
                    break;
                }
            }
            if ((uint64_t)wanted > s->size - s->offset) wanted = (size_t)(s->size - s->offset);
            got = c2_host_asset_read(s->filename, chunk, wanted, (size_t)s->offset);
            if (got == 0) { slot_end(slot); break; }
            if (!c2_host_audio_queue_pcm(voice_of(slot), chunk, got,
                                         C2_RECORDED_SAMPLE_RATE, 1, 8, 0)) {
                slot_end(slot);
                break;
            }
            s->offset += got;
        }
    }
}

/* play_tune(): the engine wants an XMI started in slot loop_count (0: the
 * city tune, 1: forum or battle). 1 = answered here. */
int c2_port_recorded_music_play(const char *filename, int loop_count)
{
    int slot = loop_count == 0 ? 0 : 1;
    char raw[16];

    snprintf(c2_recorded_last_request[slot], sizeof(c2_recorded_last_request[slot]),
             "%s", filename);
    if (slot == 1) c2_recorded_secondary_active = 1;
    else c2_recorded_secondary_active = 0;
    if (c2_port_music_source() != C2_PORT_MUSIC_RECORDED) return 0;
    if (!recorded_name_for(filename, slot, raw, sizeof(raw))) return 0;

    if (slot == 0) {
        slot_end(1);
        if (c2_recorded[0].playing) {
            slot_resume(0);
            return 1;
        }
        return slot_start(0, raw, 0);
    }
    slot_pause(0);
    return slot_start(1, raw, 1);
}

/* stop_tune(): pause the city tune and end the secondary; stop_tune0():
 * pause the city tune only. */
void c2_port_recorded_music_stop(int end_secondary)
{
    slot_pause(0);
    if (end_secondary) {
        slot_end(1);
        c2_recorded_secondary_active = 0;
    }
}

/* AIL_set_sequence_volume() for handle 1 + slot: the music volume slider
 * and the engine's own fades. */
void c2_port_recorded_music_set_volume(int slot, int volume, int fade_ms)
{
    float gain;
    if (slot < 0 || slot >= C2_RECORDED_SLOTS || !c2_recorded[slot].playing) return;
    if (volume < 0) volume = 0;
    if (volume > 127) volume = 127;
    gain = (float)volume / 127.0f;
    slot_set_gain(slot, gain, fade_ms);
}

/* A change of source while music plays: silence the old system and ask the
 * engine for the same tune again, which the new system answers. */
void c2_port_music_set_preference(enum c2_port_music_source preference)
{
    enum c2_port_music_source before = c2_port_music_source();
    int secondary = c2_recorded_secondary_active;
    char city[16];
    char other[16];

    c2_recorded_preference = preference;
    if (c2_port_music_source() == before) return;
    if (c2inf.tunes_on == 0) return;
    snprintf(city, sizeof(city), "%s", c2_recorded_last_request[0]);
    snprintf(other, sizeof(other), "%s", c2_recorded_last_request[1]);
    if (city[0] == '\0' && other[0] == '\0') return;
    stop_tune();              /* pauses the XMI city tune, ends its secondary */
    slot_end(0);
    slot_end(1);
    if (city[0]) play_tune((unsigned char *)city, 0);
    if (secondary && other[0]) play_tune((unsigned char *)other, 1);
}

void c2_port_recorded_music_shutdown(void)
{
    slot_end(0);
    slot_end(1);
    c2_recorded_city_tune = 0;
    c2_recorded_secondary_active = 0;
    memset(c2_recorded_last_request, 0, sizeof(c2_recorded_last_request));
}

#endif /* PORT_FEAT_RECORDED_MUSIC */
