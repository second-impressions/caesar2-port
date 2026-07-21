#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libsmacker/smacker.h>
#include <unity/unity.h>

static const char *movie_names[] = {
    "INTRO.SMK", "ARMYWARN.SMK", "BATTLOST.SMK", "BATTWON.SMK",
    "CONGRAT.SMK", "FIRE.SMK", "LOSEGAME.SMK", "MESSAGE.SMK",
    "PROMOTE.SMK", "RIOTERS.SMK", "ROBBERY.SMK", "SICK.SMK",
    "WARNING.SMK", "WINGAME.SMK"
};

static FILE *open_movie(const char *root, const char *name)
{
    char path[1024];
    FILE *file;

    snprintf(path, sizeof(path), "%s/%s", root, name);
    file = fopen(path, "rb");
    if (file != NULL) return file;
    snprintf(path, sizeof(path), "%s/smk/%s", root, name);
    file = fopen(path, "rb");
    if (file != NULL) return file;
    snprintf(path, sizeof(path), "%s/SMK/%s", root, name);
    return fopen(path, "rb");
}

static void decode_movie(FILE *file)
{
    smk movie;
    unsigned long expected_frames;
    unsigned long decoded_frames;
    unsigned long width;
    unsigned long height;
    signed char result;

    movie = smk_open_filepointer(file, SMK_MODE_MEMORY);
    TEST_ASSERT_NOT_NULL(movie);
    TEST_ASSERT_EQUAL_INT(0,
        smk_info_all(movie, NULL, &expected_frames, NULL));
    TEST_ASSERT_EQUAL_INT(0,
        smk_info_video(movie, &width, &height, NULL));
    TEST_ASSERT_GREATER_THAN_UINT32(0, width);
    TEST_ASSERT_GREATER_THAN_UINT32(0, height);
    TEST_ASSERT_EQUAL_INT(0, smk_enable_video(movie, 1));
    TEST_ASSERT_EQUAL_INT(0, smk_enable_audio(movie, 0, 1));

    result = smk_first(movie);
    TEST_ASSERT_GREATER_OR_EQUAL_INT(SMK_DONE, result);
    decoded_frames = 1;
    TEST_ASSERT_NOT_NULL(smk_get_video(movie));
    TEST_ASSERT_NOT_NULL(smk_get_palette(movie));
    while (result == SMK_MORE) {
        result = smk_next(movie);
        TEST_ASSERT_GREATER_OR_EQUAL_INT(SMK_DONE, result);
        decoded_frames++;
    }
    TEST_ASSERT_EQUAL_UINT32(expected_frames, decoded_frames);
    TEST_ASSERT_EQUAL_INT(SMK_LAST, result);
    smk_close(movie);
}

static void test_malformed_input_fails_cleanly(void)
{
    unsigned char malformed[16];

    memset(malformed, 0, sizeof(malformed));
    memcpy(malformed, "SMK2", 4);
    TEST_ASSERT_NULL(smk_open_memory(malformed, sizeof(malformed)));
}

static void test_official_movie_corpus(void)
{
    const char *root;
    FILE *file;
    size_t movie_idx;
    int found;

    root = getenv("C2_TEST_DATA_DIR");
    if (root == NULL || *root == 0) TEST_IGNORE_MESSAGE("no Caesar II assets");
    found = 0;
    for (movie_idx = 0;
         movie_idx < sizeof(movie_names) / sizeof(movie_names[0]);
         movie_idx++) {
        file = open_movie(root, movie_names[movie_idx]);
        if (file == NULL) continue;
        found++;
        decode_movie(file);
    }
    TEST_ASSERT_GREATER_THAN_INT(0, found);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_malformed_input_fails_cleanly);
    RUN_TEST(test_official_movie_corpus);
    return UNITY_END();
}
