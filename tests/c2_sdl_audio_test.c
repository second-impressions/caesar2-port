#include <string.h>

#include <SDL3/SDL.h>
#include <unity/unity.h>

#include "c2_host.h"

static void test_raw_voice_lifetime_and_stop(void)
{
    unsigned char pcm[1000];

    memset(pcm, 128, sizeof(pcm));
    TEST_ASSERT_TRUE(c2_host_audio_init(2));
    TEST_ASSERT_TRUE(c2_host_audio_play_pcm_u8(0, pcm, sizeof(pcm),
                                               1000, 1, 1));
    TEST_ASSERT_TRUE(c2_host_audio_voice_playing(0));
    c2_host_audio_stop_voice(0);
    TEST_ASSERT_FALSE(c2_host_audio_voice_playing(0));
    c2_host_audio_shutdown();
}

static void test_pause_is_per_voice(void)
{
    unsigned char pcm[1000];

    memset(pcm, 128, sizeof(pcm));
    TEST_ASSERT_TRUE(c2_host_audio_init(2));
    TEST_ASSERT_TRUE(c2_host_audio_play_pcm_u8(0, pcm, sizeof(pcm),
                                               1000, 1, 1));
    TEST_ASSERT_TRUE(c2_host_audio_play_pcm_u8(1, pcm, sizeof(pcm),
                                               1000, 1, 1));
    c2_host_audio_pause_voice(0);
    TEST_ASSERT_TRUE(c2_host_audio_voice_playing(0));
    TEST_ASSERT_TRUE(c2_host_audio_voice_playing(1));
    c2_host_audio_resume_voice(0);
    c2_host_audio_stop_voice(0);
    TEST_ASSERT_TRUE(c2_host_audio_voice_playing(1));
    c2_host_audio_shutdown();
}

static void test_wav_is_decoded_by_sdl(void)
{
    static const unsigned char wav[] = {
        'R', 'I', 'F', 'F', 37, 0, 0, 0,
        'W', 'A', 'V', 'E',
        'f', 'm', 't', ' ', 16, 0, 0, 0,
        1, 0, 1, 0, 0xe8, 3, 0, 0,
        0xe8, 3, 0, 0, 1, 0, 8, 0,
        'd', 'a', 't', 'a', 1, 0, 0, 0, 128
    };

    TEST_ASSERT_TRUE(c2_host_audio_init(1));
    TEST_ASSERT_TRUE(c2_host_audio_play_wav(0, wav, sizeof(wav), 1));
    TEST_ASSERT_TRUE(c2_host_audio_voice_playing(0));
    c2_host_audio_shutdown();
}

static void test_pcm_chunks_append_to_one_voice(void)
{
    unsigned char pcm[100];

    memset(pcm, 128, sizeof(pcm));
    TEST_ASSERT_TRUE(c2_host_audio_init(1));
    TEST_ASSERT_TRUE(c2_host_audio_queue_pcm(0, pcm, sizeof(pcm),
                                             1000, 1, 8, 0));
    TEST_ASSERT_TRUE(c2_host_audio_queue_pcm(0, pcm, sizeof(pcm),
                                             1000, 1, 8, 1));
    TEST_ASSERT_GREATER_OR_EQUAL_UINT(100,
        c2_host_audio_voice_queued_ms(0));
    c2_host_audio_set_voice_gain(0, 0.25f);
    TEST_ASSERT_FALSE(c2_host_audio_queue_pcm(0, pcm, sizeof(pcm),
                                              1000, 1, 12, 1));
    TEST_ASSERT_TRUE(c2_host_audio_voice_playing(0));
    c2_host_audio_shutdown();
}

static void test_voice_set_can_grow_after_device_startup(void)
{
    unsigned char pcm[100];

    memset(pcm, 128, sizeof(pcm));
    TEST_ASSERT_TRUE(c2_host_audio_init(8));
    TEST_ASSERT_TRUE(c2_host_audio_init(10));
    TEST_ASSERT_TRUE(c2_host_audio_play_pcm_u8(9, pcm, sizeof(pcm),
                                               1000, 1, 1));
    TEST_ASSERT_TRUE(c2_host_audio_voice_playing(9));
    c2_host_audio_shutdown();
}

int main(void)
{
    SDL_SetHint(SDL_HINT_AUDIO_DRIVER, "dummy");
    UNITY_BEGIN();
    RUN_TEST(test_raw_voice_lifetime_and_stop);
    RUN_TEST(test_pause_is_per_voice);
    RUN_TEST(test_wav_is_decoded_by_sdl);
    RUN_TEST(test_pcm_chunks_append_to_one_voice);
    RUN_TEST(test_voice_set_can_grow_after_device_startup);
    return UNITY_END();
}
