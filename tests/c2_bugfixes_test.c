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

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_player_name_padding);
    RUN_TEST(test_mosaic_random_sentinel);
    return UNITY_END();
}
