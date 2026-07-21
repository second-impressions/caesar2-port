#include <stdio.h>
#include <stdlib.h>

#include <adlmidi.h>
#include <unity/unity.h>

#include "c2_port_miles_bank.h"

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

static unsigned char *read_bank(const char *root, const char *name,
                                size_t *size)
{
    unsigned char *data;
    char path[1024];
    FILE *file;
    long length;

    snprintf(path, sizeof(path), "%s/%s", root, name);
    file = fopen(path, "rb");
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

static void assert_operator(const ADL_Operator *operator,
                            unsigned avekf, unsigned ksl_l,
                            unsigned atdec, unsigned susrel,
                            unsigned waveform)
{
    TEST_ASSERT_EQUAL_HEX8(avekf, operator->avekf_20);
    TEST_ASSERT_EQUAL_HEX8(ksl_l, operator->ksl_l_40);
    TEST_ASSERT_EQUAL_HEX8(atdec, operator->atdec_60);
    TEST_ASSERT_EQUAL_HEX8(susrel, operator->susrel_80);
    TEST_ASSERT_EQUAL_HEX8(waveform, operator->waveform_E0);
}

static void test_official_miles_bank_operator_order(void)
{
    struct ADL_MIDIPlayer *player;
    ADL_BankId id;
    ADL_Bank bank;
    ADL_Instrument instrument;
    unsigned char *data;
    const char *root;
    size_t size;

    root = getenv("C2_TEST_DATA_DIR");
    if (root == NULL || *root == 0) TEST_IGNORE_MESSAGE("no Caesar II assets");
    data = read_bank(root, "CAESAR.OPL", &size);
    player = adl_init(44100);
    TEST_ASSERT_NOT_NULL(player);
    TEST_ASSERT_EQUAL_INT(0, adl_setBank(player, 40));
    TEST_ASSERT_TRUE(c2_port_apply_miles_bank(player, data, size));

    id.percussive = 0;
    id.msb = 0;
    id.lsb = 0;
    TEST_ASSERT_EQUAL_INT(0, adl_getBank(player, &id, 0, &bank));

    TEST_ASSERT_EQUAL_INT(0,
        adl_getInstrument(player, &bank, 0, &instrument));
    TEST_ASSERT_EQUAL_UINT8(ADLMIDI_Ins_4op, instrument.inst_flags);
    TEST_ASSERT_EQUAL_HEX8(0x06, instrument.fb_conn1_C0);
    TEST_ASSERT_EQUAL_HEX8(0x06, instrument.fb_conn2_C0);
    assert_operator(&instrument.operators[0], 0x03, 0x6d, 0xe2, 0xe4, 0x00);
    assert_operator(&instrument.operators[1], 0x06, 0xa4, 0xf3, 0xf4, 0x00);
    assert_operator(&instrument.operators[2], 0x11, 0x02, 0xe1, 0xe5, 0x00);
    assert_operator(&instrument.operators[3], 0x01, 0x53, 0xe1, 0xd4, 0x00);
    TEST_ASSERT_GREATER_THAN_UINT16(0, instrument.delay_on_ms);
    TEST_ASSERT_GREATER_THAN_UINT16(0, instrument.delay_off_ms);

    TEST_ASSERT_EQUAL_INT(0,
        adl_getInstrument(player, &bank, 1, &instrument));
    TEST_ASSERT_EQUAL_UINT8(ADLMIDI_Ins_2op, instrument.inst_flags);
    assert_operator(&instrument.operators[0], 0x13, 0x00, 0xf2, 0xf3, 0x00);
    assert_operator(&instrument.operators[1], 0x41, 0x9d, 0xf2, 0x53, 0x00);

    adl_close(player);
    free(data);
}

static void test_official_ad_fallback_bank(void)
{
    struct ADL_MIDIPlayer *player;
    unsigned char *data;
    const char *root;
    size_t size;

    root = getenv("C2_TEST_DATA_DIR");
    if (root == NULL || *root == 0) TEST_IGNORE_MESSAGE("no Caesar II assets");
    data = read_bank(root, "CAESAR.AD", &size);
    player = adl_init(44100);
    TEST_ASSERT_NOT_NULL(player);
    TEST_ASSERT_EQUAL_INT(0, adl_setBank(player, 40));
    TEST_ASSERT_TRUE(c2_port_apply_miles_bank(player, data, size));
    adl_close(player);
    free(data);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_official_miles_bank_operator_order);
    RUN_TEST(test_official_ad_fallback_bank);
    RUN_TEST(test_official_numbered_branches);
    return UNITY_END();
}
