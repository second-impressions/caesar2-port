#include "c2_bugfixes.h"

#include <unity/unity.h>

extern unsigned char stone_random_data[];

static void test_player_name_padding(void)
{
    char padded[26] = "Octavian                ";
    char embedded_space[26] = "Marcus Aurelius   ";
    char empty[5] = "    ";

    c2_fix_player_name_padding(padded, sizeof(padded));
    c2_fix_player_name_padding(embedded_space, sizeof(embedded_space));
    c2_fix_player_name_padding(empty, sizeof(empty));

#if PORT_FIX_PLAYER_NAME_PADDING
    TEST_ASSERT_EQUAL_STRING("Octavian", padded);
    TEST_ASSERT_EQUAL_STRING("Marcus Aurelius", embedded_space);
    TEST_ASSERT_EQUAL_STRING("", empty);
#else
    TEST_ASSERT_EQUAL_STRING("Octavian                ", padded);
    TEST_ASSERT_EQUAL_STRING("Marcus Aurelius   ", embedded_space);
    TEST_ASSERT_EQUAL_STRING("    ", empty);
#endif
}

static void test_mosaic_random_sentinel(void)
{
#if C2_FIX_MOSAIC_RANDOM_SENTINEL
    TEST_ASSERT_EQUAL_UINT8(1, stone_random_data[64]);
#else
    TEST_PASS();
#endif
}

static void test_envoy_retires_itself(void)
{
    /* A replacement walker handed a different slot never retires itself. */
    TEST_ASSERT_EQUAL_INT(0, c2_fix_envoy_retires_itself(7, 9));
    TEST_ASSERT_EQUAL_INT(0, c2_fix_envoy_retires_itself(0, 9));

#if PORT_FIX_MARKET_ENVOY_SELF_KILL
    /* Recycled slot: the cell's recorded envoy is the new walker itself. */
    TEST_ASSERT_NOT_EQUAL_INT(0, c2_fix_envoy_retires_itself(9, 9));
    TEST_ASSERT_NOT_EQUAL_INT(0, c2_fix_envoy_retires_itself(1, 1));
    /* Slot 0 is never allocated, so this pair cannot occur in the engine;
     * skipping is equivalent to the recovered empty-record check anyway. */
    TEST_ASSERT_NOT_EQUAL_INT(0, c2_fix_envoy_retires_itself(0, 0));
#else
    TEST_ASSERT_EQUAL_INT(0, c2_fix_envoy_retires_itself(9, 9));
#endif
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_player_name_padding);
    RUN_TEST(test_mosaic_random_sentinel);
    RUN_TEST(test_envoy_retires_itself);
    return UNITY_END();
}
