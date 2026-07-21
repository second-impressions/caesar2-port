#include <stdio.h>
#include <stdlib.h>

#include <adlmidi.h>
#include <unity/unity.h>

static FILE *open_xmi(const char *root, const char *name)
{
    char path[1024];
    FILE *file;

    snprintf(path, sizeof(path), "%s/%s", root, name);
    file = fopen(path, "rb");
    if (file != NULL) return file;
    snprintf(path, sizeof(path), "%s/xmi/%s", root, name);
    file = fopen(path, "rb");
    if (file != NULL) return file;
    snprintf(path, sizeof(path), "%s/XMI/%s", root, name);
    return fopen(path, "rb");
}

static unsigned char *read_xmi(const char *root, const char *name,
                               size_t *size)
{
    unsigned char *data;
    FILE *file;
    long length;

    file = open_xmi(root, name);
    TEST_ASSERT_NOT_NULL(file);
    TEST_ASSERT_EQUAL_INT(0, fseek(file, 0, SEEK_END));
    length = ftell(file);
    TEST_ASSERT_GREATER_THAN_INT(0, length);
    TEST_ASSERT_EQUAL_INT(0, fseek(file, 0, SEEK_SET));
    data = malloc((size_t)length);
    TEST_ASSERT_NOT_NULL(data);
    TEST_ASSERT_EQUAL_size_t((size_t)length,
                             fread(data, 1, (size_t)length, file));
    fclose(file);
    *size = (size_t)length;
    return data;
}

static int city_branch_expected(unsigned branch)
{
    return branch <= 6 ||
           (branch >= 10 && branch <= 16) ||
           (branch >= 20 && branch <= 26) ||
           (branch >= 30 && branch <= 36) ||
           (branch >= 40 && branch <= 53);
}

static void check_branches(const char *root, const char *name,
                           int (*expected)(unsigned), unsigned count)
{
    struct ADL_MIDIPlayer *player;
    unsigned char *data;
    unsigned branch;
    unsigned found;
    size_t size;

    data = read_xmi(root, name, &size);
    player = adl_init(44100);
    TEST_ASSERT_NOT_NULL(player);
    TEST_ASSERT_EQUAL_INT(0,
        adl_openData(player, data, (unsigned long)size));
    found = 0;
    for (branch = 0; branch < 256; branch++) {
        if (expected(branch)) {
            TEST_ASSERT_EQUAL_INT(0, adl_jumpToBranch(player, branch));
            found++;
        } else {
            TEST_ASSERT_LESS_THAN_INT(0, adl_jumpToBranch(player, branch));
        }
    }
    TEST_ASSERT_EQUAL_UINT(count, found);
    adl_close(player);
    free(data);
}

static int battle_branch_expected(unsigned branch)
{
    return branch <= 53;
}

static void test_official_numbered_branches(void)
{
    const char *root;

    root = getenv("C2_TEST_DATA_DIR");
    if (root == NULL || *root == 0) TEST_IGNORE_MESSAGE("no Caesar II assets");
    check_branches(root, "CITYPROV.XMI", city_branch_expected, 42);
    check_branches(root, "BATEST2.XMI", battle_branch_expected, 54);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_official_numbered_branches);
    return UNITY_END();
}
