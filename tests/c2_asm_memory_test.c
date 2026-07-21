#include <unity/unity.h>
#include <string.h>

#include "c2_asm_routines.h"

static int callback_count;

static void count_callback(void)
{
    callback_count++;
}

static void test_call_address(void)
{
    callback_count = 0;
    call_address(count_callback);
    TEST_ASSERT_TRUE(callback_count == 1);
}

static void test_copy(void)
{
    unsigned char source[64];
    unsigned char destination[64] = { 0 };
    int i;

    for (i = 0; i < 64; i++) {
        source[i] = (unsigned char)(i * 3 + 1);
    }
    copy(source, destination, 64);
    TEST_ASSERT_TRUE(memcmp(source, destination, sizeof(source)) == 0);
}

static void test_repeated_run(void)
{
    unsigned char source[] = { 'A', 'A', 'A', 'A', 'A' };
    unsigned char packed[32] = { 0 };
    unsigned char unpacked[sizeof(source)] = { 0 };
    unsigned char expected[] = {
        11, 0, 0, 0, 5, 0, 0, 0, 4, 0, 'A'
    };

    TEST_ASSERT_TRUE(compress(source, packed, sizeof(source)) == sizeof(expected));
    TEST_ASSERT_TRUE(memcmp(packed, expected, sizeof(expected)) == 0);
    TEST_ASSERT_TRUE(depress(unpacked, packed) == sizeof(source));
    TEST_ASSERT_TRUE(memcmp(unpacked, source, sizeof(source)) == 0);
}

static void test_literal_run(void)
{
    unsigned char source[] = { 1, 2, 3, 4 };
    unsigned char packed[32] = { 0 };
    unsigned char unpacked[sizeof(source)] = { 0 };
    unsigned char expected[] = {
        14, 0, 0, 0, 4, 0, 0, 0, 3, 0x80, 1, 2, 3, 4
    };

    TEST_ASSERT_TRUE(compress(source, packed, sizeof(source)) == sizeof(expected));
    TEST_ASSERT_TRUE(memcmp(packed, expected, sizeof(expected)) == 0);
    TEST_ASSERT_TRUE(depress(unpacked, packed) == sizeof(source));
    TEST_ASSERT_TRUE(memcmp(unpacked, source, sizeof(source)) == 0);
}

static void test_mixed_round_trip(void)
{
    unsigned char source[] = {
        1, 2, 3, 4, 7, 7, 7, 7, 9, 10, 11, 12, 12, 12
    };
    unsigned char packed[64] = { 0 };
    unsigned char unpacked[sizeof(source)] = { 0 };

    TEST_ASSERT_TRUE(compress(source, packed, sizeof(source)) > 8);
    TEST_ASSERT_TRUE(depress(unpacked, packed) == sizeof(source));
    TEST_ASSERT_TRUE(memcmp(unpacked, source, sizeof(source)) == 0);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_call_address);
    RUN_TEST(test_copy);
    RUN_TEST(test_repeated_run);
    RUN_TEST(test_literal_run);
    RUN_TEST(test_mixed_round_trip);
    return UNITY_END();
}
