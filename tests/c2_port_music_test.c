#include <unity/unity.h>

#include "c2_port.h"

void setUp(void) {}
void tearDown(void) {}

static void test_paused_branches_stay_in_mood(void)
{
    int count;

    for (count = 1; count <= 20; count++) {
        int branch = c2_port_paused_music_branch(0x14, 7, -1, count);
        TEST_ASSERT_GREATER_OR_EQUAL_INT(0x14, branch);
        TEST_ASSERT_LESS_OR_EQUAL_INT(0x1a, branch);
    }
}

static void test_paused_branch_does_not_repeat_current_phrase(void)
{
    int count;
    int branch = 0;

    for (count = 1; count <= 50; count++) {
        int next = c2_port_paused_music_branch(0, 7, branch, count);
        TEST_ASSERT_NOT_EQUAL(branch, next);
        branch = next;
    }
}

static void test_every_phrase_is_reached(void)
{
    unsigned int seen = 0;
    int count;

    for (count = 1; count <= 7; count++) {
        int branch = c2_port_paused_music_branch(0, 7, -1, count);
        seen |= 1u << branch;
    }
    TEST_ASSERT_EQUAL_HEX32(0x7f, seen);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_paused_branches_stay_in_mood);
    RUN_TEST(test_paused_branch_does_not_repeat_current_phrase);
    RUN_TEST(test_every_phrase_is_reached);
    return UNITY_END();
}
