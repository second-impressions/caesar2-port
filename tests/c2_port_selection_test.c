#include <unity/unity.h>

#include "c2_port.h"

void setUp(void) {}
void tearDown(void) {}

static void test_stationary_opening_release_is_consumed(void)
{
    c2_port_selection_begin(500, 240);
    TEST_ASSERT_TRUE(c2_port_selection_consume_release(500, 240));
    TEST_ASSERT_FALSE(c2_port_selection_consume_release(500, 240));
}

static void test_pointer_jitter_is_still_a_click(void)
{
    c2_port_selection_begin(500, 240);
    TEST_ASSERT_TRUE(c2_port_selection_consume_release(504, 236));
}

static void test_drag_release_is_not_consumed(void)
{
    c2_port_selection_begin(500, 240);
    TEST_ASSERT_FALSE(c2_port_selection_consume_release(480, 240));
    TEST_ASSERT_FALSE(c2_port_selection_consume_release(500, 240));
}

static void test_end_cancels_pending_release(void)
{
    c2_port_selection_begin(500, 240);
    c2_port_selection_end();
    TEST_ASSERT_FALSE(c2_port_selection_consume_release(500, 240));
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_stationary_opening_release_is_consumed);
    RUN_TEST(test_pointer_jitter_is_still_a_click);
    RUN_TEST(test_drag_release_is_not_consumed);
    RUN_TEST(test_end_cancels_pending_release);
    return UNITY_END();
}
