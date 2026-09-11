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

static void test_dispatch_phase_rotation_is_a_permutation(void)
{
    int year;

    /* Whatever the month, the four phases each own exactly four of the
     * sixteen clock ticks, so no phase is skipped or runs twice. */
    for (year = -400; year <= 400; year += 7) {
        int month;

        for (month = 0; month < 12; month++) {
            unsigned int rotation = c2_fix_dispatch_rotation(year, month);
            int seen[4] = {0, 0, 0, 0};
            int slot;

            for (slot = 0; slot < 16; slot++) {
                int phase = c2_fix_dispatch_phase(slot, rotation);

                TEST_ASSERT_TRUE(phase >= 0 && phase < 4);
                seen[phase]++;
            }
            TEST_ASSERT_EQUAL_INT(4, seen[0]);
            TEST_ASSERT_EQUAL_INT(4, seen[1]);
            TEST_ASSERT_EQUAL_INT(4, seen[2]);
            TEST_ASSERT_EQUAL_INT(4, seen[3]);
        }
    }
}

static void test_dispatch_column_rotation_is_a_permutation(void)
{
    int year;

    /* Every map column is visited exactly once per row band. */
    for (year = -400; year <= 400; year += 7) {
        int month;

        for (month = 0; month < 12; month++) {
            unsigned int rotation = c2_fix_dispatch_rotation(year, month);
            int seen[80];
            int i;

            for (i = 0; i < 80; i++) seen[i] = 0;
            for (i = 0; i < 80; i++) {
                int column = c2_fix_dispatch_column(i, rotation);

                TEST_ASSERT_TRUE(column >= 0 && column < 80);
                seen[column]++;
            }
            for (i = 0; i < 80; i++) TEST_ASSERT_EQUAL_INT(1, seen[i]);
        }
    }
}

static void test_dispatch_order_matches_the_recovered_sweep(void)
{
    int i;

    /* Rotation zero is the recovered order: phase = tick / 4, and the row
     * band is swept from column zero upward. */
    for (i = 0; i < 16; i++) {
        TEST_ASSERT_EQUAL_INT(i / 4, c2_fix_dispatch_phase(i, 0u));
    }
    for (i = 0; i < 80; i++) {
        TEST_ASSERT_EQUAL_INT(i, c2_fix_dispatch_column(i, 0u));
    }

#if PORT_FIX_WALKER_DISPATCH_FAIRNESS
    /* A later month moves both orders. */
    TEST_ASSERT_NOT_EQUAL_UINT(0u, c2_fix_dispatch_rotation(1, 1));
    TEST_ASSERT_NOT_EQUAL_INT(0, c2_fix_dispatch_phase(0, 1u));
    TEST_ASSERT_NOT_EQUAL_INT(0, c2_fix_dispatch_column(0, 1u));
#else
    /* With the fix off the recovered order holds for every calendar date. */
    TEST_ASSERT_EQUAL_UINT(0u, c2_fix_dispatch_rotation(1, 1));
    TEST_ASSERT_EQUAL_INT(0, c2_fix_dispatch_phase(0, 1u));
    TEST_ASSERT_EQUAL_INT(0, c2_fix_dispatch_column(0, 1u));
#endif
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_player_name_padding);
    RUN_TEST(test_mosaic_random_sentinel);
    RUN_TEST(test_dispatch_phase_rotation_is_a_permutation);
    RUN_TEST(test_dispatch_column_rotation_is_a_permutation);
    RUN_TEST(test_dispatch_order_matches_the_recovered_sweep);
    return UNITY_END();
}
