#include <unity/unity.h>

#include <stdio.h>
#include <string.h>

#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"

/* The recorded-music module against a fake host: a game data set as a table
 * of file sizes, and an audio device that only remembers what it was told. */

struct c2inf_rec c2inf;

struct fake_file { const char *name; uint64_t size; };
static struct fake_file *fake_files;
static size_t fake_file_count;

static struct fake_file with_recordings[] = {
    { "citypro0.raw", 30000 }, { "citypro1.raw", 20000 }, { "citypro2.raw", 10000 },
    { "forum0.raw", 8000 }, { "forum1.raw", 8000 }, { "forum2.raw", 8000 },
    { "battle0.raw", 9000 },
    { "cityprov.xmi", 100 }, { "caesar.opl", 100 }
};
static struct fake_file recordings_only[] = {
    { "citypro0.raw", 30000 }, { "citypro1.raw", 20000 }, { "citypro2.raw", 10000 },
    { "forum0.raw", 8000 }, { "forum1.raw", 8000 }, { "forum2.raw", 8000 },
    { "battle0.raw", 9000 }
};
static struct fake_file xmidi_only[] = {
    { "cityprov.xmi", 100 }, { "caesar.opl", 100 }
};

static const struct fake_file *find_file(const char *name)
{
    size_t i;
    for (i = 0; i < fake_file_count; i++) {
        if (strcmp(fake_files[i].name, name) == 0) return &fake_files[i];
    }
    return NULL;
}

uint64_t c2_host_asset_size(const char *filename)
{
    const struct fake_file *f = find_file(filename);
    return f ? f->size : 0;
}

size_t c2_host_asset_read(const char *filename, void *buffer, size_t size, size_t offset)
{
    const struct fake_file *f = find_file(filename);
    if (!f || offset >= f->size) return 0;
    if (size > f->size - offset) size = (size_t)(f->size - offset);
    memset(buffer, 0x80, size);
    return size;
}

/* The audio device: per voice, bytes queued, paused state, gain; each
 * pump call drains the queue so the next call streams more. */
#define VOICES 16
static struct {
    uint64_t queued_bytes;
    unsigned int queued_ms;
    int active;
    int paused;
    int stopped;
    float gain;
} voices[VOICES];
static char last_stream_file[VOICES][16];

int c2_host_audio_init(int voice_count) { (void)voice_count; return 1; }
int c2_host_audio_queue_pcm(int voice, const void *data, size_t size,
                            int sample_rate, int channels, int bit_depth, int final_chunk)
{
    (void)data; (void)final_chunk;
    TEST_ASSERT_EQUAL_INT(22050, sample_rate);
    TEST_ASSERT_EQUAL_INT(1, channels);
    TEST_ASSERT_EQUAL_INT(8, bit_depth);
    voices[voice].queued_bytes += size;
    voices[voice].queued_ms += (unsigned int)(size * 1000 / 22050);
    voices[voice].active = 1;
    return 1;
}
unsigned int c2_host_audio_voice_queued_ms(int voice) { return voices[voice].queued_ms; }
void c2_host_audio_stop_voice(int voice) { voices[voice].active = 0; voices[voice].stopped++; voices[voice].queued_ms = 0; }
void c2_host_audio_pause_voice(int voice) { voices[voice].paused = 1; }
void c2_host_audio_resume_voice(int voice) { voices[voice].paused = 0; }
void c2_host_audio_set_voice_gain(int voice, float gain) { voices[voice].gain = gain; }

/* The engine functions a source change goes through. */
static int stop_tune_calls;
static char play_tune_log[256];
void stop_tune(void) { stop_tune_calls++; }
void play_tune(unsigned char *filename, int loop_count)
{
    char entry[40];
    snprintf(entry, sizeof(entry), "%s/%d ", (const char *)filename, loop_count);
    strncat(play_tune_log, entry, sizeof(play_tune_log) - strlen(play_tune_log) - 1);
    /* As the engine would: offer the request to the recordings. */
    c2_port_recorded_music_play((const char *)filename, loop_count);
}

static void use(struct fake_file *files, size_t count)
{
    fake_files = files;
    fake_file_count = count;
}
#define USE(table) use(table, sizeof(table) / sizeof(table[0]))

static void drain(int voice)
{
    voices[voice].queued_ms = 0;
}

static enum c2_port_music_source initial_preference;

void setUp(void)
{
    memset(voices, 0, sizeof(voices));
    memset(last_stream_file, 0, sizeof(last_stream_file));
    stop_tune_calls = 0;
    play_tune_log[0] = '\0';
    c2inf.tunes_on = 1;
    c2inf.tunes_level = 100;
    c2_port_recorded_music_shutdown();
    c2_port_music_set_preference(C2_PORT_MUSIC_RECORDED);   /* the tests' subject */
    USE(with_recordings);
}

void tearDown(void) {}

/* What the module starts with, before setUp() chooses anything: the 1995
 * DOS music, this port's default. */
static void test_the_default_is_the_dos_music(void)
{
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_XMIDI, initial_preference);
}

static void test_source_follows_preference_and_availability(void)
{
    TEST_ASSERT_TRUE(c2_port_music_recorded_available());
    TEST_ASSERT_TRUE(c2_port_music_xmidi_available());
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_RECORDED, c2_port_music_source());
    c2_port_music_set_preference(C2_PORT_MUSIC_XMIDI);
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_XMIDI, c2_port_music_source());

    USE(recordings_only);
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_RECORDED, c2_port_music_source());
    USE(xmidi_only);
    c2_port_music_set_preference(C2_PORT_MUSIC_RECORDED);
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_XMIDI, c2_port_music_source());
}

static void test_xmidi_preference_leaves_the_request_to_the_engine(void)
{
    c2_port_music_set_preference(C2_PORT_MUSIC_XMIDI);
    TEST_ASSERT_EQUAL_INT(0, c2_port_recorded_music_play("cityprov.xmi", 0));
    TEST_ASSERT_EQUAL_INT(0, voices[9].active);
}

static void test_city_tune_streams_and_moves_on_to_the_next(void)
{
    TEST_ASSERT_EQUAL_INT(1, c2_port_recorded_music_play("cityprov.xmi", 0));
    TEST_ASSERT_TRUE(voices[9].active);
    TEST_ASSERT_TRUE(voices[9].queued_ms >= 500);
    /* Stream the whole of citypro0 (30000 bytes), then citypro1 follows
     * without a stop in between. */
    while (voices[9].queued_bytes < 30000) { drain(9); c2_port_recorded_music_pump(); }
    drain(9); c2_port_recorded_music_pump();
    TEST_ASSERT_TRUE(voices[9].queued_bytes > 30000);
    TEST_ASSERT_EQUAL_INT(0, voices[9].stopped);
    /* ...and after all three, citypro0 again: the round robin. */
    while (voices[9].queued_bytes < 60000 + 5000) { drain(9); c2_port_recorded_music_pump(); }
    TEST_ASSERT_TRUE(voices[9].active);
}

static void test_forum_tune_pauses_the_city_tune_and_loops(void)
{
    c2_port_recorded_music_play("cityprov.xmi", 0);
    TEST_ASSERT_EQUAL_INT(1, c2_port_recorded_music_play("forum2.xmi", 1));
    TEST_ASSERT_TRUE(voices[9].paused);
    TEST_ASSERT_TRUE(voices[10].active);
    /* forum1.raw is 8000 bytes and loops. */
    while (voices[10].queued_bytes < 8000 * 3) { drain(10); c2_port_recorded_music_pump(); }
    TEST_ASSERT_EQUAL_INT(0, voices[10].stopped);
    /* Back to the city: the forum tune ends, the city tune resumes where
     * it was, not from the top. */
    TEST_ASSERT_EQUAL_INT(1, c2_port_recorded_music_play("cityprov.xmi", 0));
    TEST_ASSERT_FALSE(voices[9].paused);
    TEST_ASSERT_FALSE(voices[10].active);
    TEST_ASSERT_EQUAL_INT(1, voices[10].stopped);
}

static void test_battle_tune_and_stops(void)
{
    c2_port_recorded_music_play("cityprov.xmi", 0);
    c2_port_recorded_music_play("batest2.xmi", 1);
    TEST_ASSERT_TRUE(voices[10].active);
    c2_port_recorded_music_stop(0);          /* stop_tune0: city paused */
    TEST_ASSERT_TRUE(voices[9].paused);
    TEST_ASSERT_TRUE(voices[10].active);
    c2_port_recorded_music_stop(1);          /* stop_tune: secondary ended */
    TEST_ASSERT_FALSE(voices[10].active);
}

static void test_volume_reaches_the_slot(void)
{
    c2_port_recorded_music_play("cityprov.xmi", 0);
    c2_port_recorded_music_set_volume(0, 64, 0);
    TEST_ASSERT_FLOAT_WITHIN(0.01f, 64.0f / 127.0f, voices[9].gain);
    c2_port_recorded_music_set_volume(1, 64, 0);   /* idle slot: nothing */
    TEST_ASSERT_EQUAL_FLOAT(0.0f, voices[10].gain);
}

static void test_changing_the_source_replays_the_current_tunes(void)
{
    c2_port_recorded_music_play("cityprov.xmi", 0);
    c2_port_recorded_music_play("forum1.xmi", 1);
    c2_port_music_set_preference(C2_PORT_MUSIC_XMIDI);
    /* The engine was told to stop, then asked for both tunes again, which
     * now go to the synthesizer: the recordings fall silent. */
    TEST_ASSERT_EQUAL_INT(1, stop_tune_calls);
    TEST_ASSERT_EQUAL_STRING("cityprov.xmi/0 forum1.xmi/1 ", play_tune_log);
    TEST_ASSERT_FALSE(voices[9].active);
    TEST_ASSERT_FALSE(voices[10].active);
    /* And back. */
    c2_port_music_set_preference(C2_PORT_MUSIC_RECORDED);
    TEST_ASSERT_EQUAL_INT(2, stop_tune_calls);
    TEST_ASSERT_TRUE(voices[9].active);
    TEST_ASSERT_TRUE(voices[10].active);
    /* Same preference again: nothing happens. */
    c2_port_music_set_preference(C2_PORT_MUSIC_RECORDED);
    TEST_ASSERT_EQUAL_INT(2, stop_tune_calls);
}

static void test_names(void)
{
    enum c2_port_music_source source;
    TEST_ASSERT_TRUE(c2_port_music_source_parse("windows", &source));
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_RECORDED, source);
    TEST_ASSERT_TRUE(c2_port_music_source_parse("dos", &source));
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_XMIDI, source);
    /* The spellings of the first release still parse. */
    TEST_ASSERT_TRUE(c2_port_music_source_parse("recorded", &source));
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_RECORDED, source);
    TEST_ASSERT_TRUE(c2_port_music_source_parse("xmidi", &source));
    TEST_ASSERT_EQUAL_INT(C2_PORT_MUSIC_XMIDI, source);
    TEST_ASSERT_FALSE(c2_port_music_source_parse("midi", &source));
    TEST_ASSERT_FALSE(c2_port_music_source_parse(NULL, &source));
    TEST_ASSERT_EQUAL_STRING("windows", c2_port_music_source_name(C2_PORT_MUSIC_RECORDED));
    TEST_ASSERT_EQUAL_STRING("dos", c2_port_music_source_name(C2_PORT_MUSIC_XMIDI));
}

int main(void)
{
    initial_preference = c2_port_music_preference();
    UNITY_BEGIN();
    RUN_TEST(test_the_default_is_the_dos_music);
    RUN_TEST(test_source_follows_preference_and_availability);
    RUN_TEST(test_xmidi_preference_leaves_the_request_to_the_engine);
    RUN_TEST(test_city_tune_streams_and_moves_on_to_the_next);
    RUN_TEST(test_forum_tune_pauses_the_city_tune_and_loops);
    RUN_TEST(test_battle_tune_and_stops);
    RUN_TEST(test_volume_reaches_the_slot);
    RUN_TEST(test_changing_the_source_replays_the_current_tunes);
    RUN_TEST(test_names);
    return UNITY_END();
}
