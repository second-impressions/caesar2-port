#include "c2_text_compat.h"

#include <unity/unity.h>
#include <string.h>

char text_buffer[C2_TEXT_BUFFER_CAPACITY];

static void write_u32_le(char *destination, unsigned int value)
{
    destination[0] = (char)value;
    destination[1] = (char)(value >> 8);
    destination[2] = (char)(value >> 16);
    destination[3] = (char)(value >> 24);
}

static void build_text_group(int group_index, int string_count)
{
    const unsigned int first_offset = 0x254;
    unsigned int end_offset;
    int i;

    memset(text_buffer, 0, sizeof(text_buffer));
    memcpy(text_buffer, "Textfile", 8);
    for (i = 0; i < 147; i++) {
        unsigned int offset;

        if (i == 0)
            offset = 0;
        else if (i <= group_index)
            offset = first_offset;
        else
            offset = first_offset + (unsigned int)string_count * 2;
        write_u32_le(text_buffer + 8 + i * 4, offset);
    }

    for (i = 0; i < string_count; i++) {
        text_buffer[first_offset + (unsigned int)i * 2] = 'x';
        text_buffer[first_offset + (unsigned int)i * 2 + 1] = 0;
    }

    end_offset = first_offset + (unsigned int)string_count * 2;
    TEST_ASSERT_TRUE(end_offset < sizeof(text_buffer));
}

static void test_new_game_cancel_capability(void)
{
    build_text_group(0x2b, 18);
    TEST_ASSERT_TRUE(c2_text_group_string_count_in_buffer(
               text_buffer, sizeof(text_buffer), 0x2b) == 18);
    TEST_ASSERT_TRUE(!c2_text_group_has_string(0x2b, 18));
    TEST_ASSERT_TRUE(!c2_text_has_new_game_cancel());

    build_text_group(0x2b, 19);
    TEST_ASSERT_TRUE(c2_text_group_string_count_in_buffer(
               text_buffer, sizeof(text_buffer), 0x2b) == 19);
    TEST_ASSERT_TRUE(c2_text_group_has_string(0x2b, 18));
    TEST_ASSERT_TRUE(c2_text_has_new_game_cancel());
}

static void test_late_region_quote_capability(void)
{
    build_text_group(0x45, 29);
    TEST_ASSERT_TRUE(!c2_text_group_has_string(0x45, 29));
    TEST_ASSERT_TRUE(!c2_text_group_has_string(0x45, 30));
    TEST_ASSERT_TRUE(!c2_text_has_late_region_quotes());

    build_text_group(0x45, 30);
    TEST_ASSERT_TRUE(c2_text_group_has_string(0x45, 29));
    TEST_ASSERT_TRUE(!c2_text_has_late_region_quotes());

    build_text_group(0x45, 31);
    TEST_ASSERT_TRUE(c2_text_group_has_string(0x45, 29));
    TEST_ASSERT_TRUE(c2_text_group_has_string(0x45, 30));
    TEST_ASSERT_TRUE(c2_text_has_late_region_quotes());
}

static void test_invalid_text_buffer(void)
{
    build_text_group(0x2b, 18);
    text_buffer[0] = 0;
    TEST_ASSERT_TRUE(c2_text_group_string_count_in_buffer(
               text_buffer, sizeof(text_buffer), 0x2b) == -1);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_new_game_cancel_capability);
    RUN_TEST(test_late_region_quote_capability);
    RUN_TEST(test_invalid_text_buffer);
    return UNITY_END();
}
