#include "c2_bugfixes.h"

#include <unity/unity.h>

static void test_help_smart_punctuation(void)
{
    char text[] = "city\x92s don\x91t x \x97 y x \x96 y o\x97 C\x92 ";

    c2_fix_help_text(text, sizeof(text));

#if C2_FIX_HELP_SMART_PUNCTUATION
    TEST_ASSERT_TRUE(text[4] == '\'');
    TEST_ASSERT_TRUE(text[10] == '\'');
    TEST_ASSERT_TRUE(text[15] == '-');
    TEST_ASSERT_TRUE(text[21] == '-');
#else
    TEST_ASSERT_TRUE((unsigned char)text[4] == 0x92);
    TEST_ASSERT_TRUE((unsigned char)text[10] == 0x91);
    TEST_ASSERT_TRUE((unsigned char)text[15] == 0x97);
    TEST_ASSERT_TRUE((unsigned char)text[21] == 0x96);
#endif

    /* These byte values are letters in the DOS code pages used by the
     * localized assets and must remain untouched inside words. */
    TEST_ASSERT_TRUE((unsigned char)text[26] == 0x97);
    TEST_ASSERT_TRUE((unsigned char)text[29] == 0x92);
}

static void test_player_name_padding(void)
{
    char padded[26] = "Octavian                ";
    char embedded_space[26] = "Marcus Aurelius   ";
    char empty[5] = "    ";

    c2_fix_player_name_padding(padded, sizeof(padded));
    c2_fix_player_name_padding(embedded_space, sizeof(embedded_space));
    c2_fix_player_name_padding(empty, sizeof(empty));

#if C2_FIX_PLAYER_NAME_PADDING
    TEST_ASSERT_EQUAL_STRING("Octavian", padded);
    TEST_ASSERT_EQUAL_STRING("Marcus Aurelius", embedded_space);
    TEST_ASSERT_EQUAL_STRING("", empty);
#else
    TEST_ASSERT_EQUAL_STRING("Octavian                ", padded);
    TEST_ASSERT_EQUAL_STRING("Marcus Aurelius   ", embedded_space);
    TEST_ASSERT_EQUAL_STRING("    ", empty);
#endif
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_help_smart_punctuation);
    RUN_TEST(test_player_name_padding);
    return UNITY_END();
}
