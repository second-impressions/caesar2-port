#include <unity/unity.h>

#include "c2_types.h"
#include "c2_port_pause.h"

struct c2inf_rec c2inf;

static int pending_request;
static int toggle_count;

int c2_host_take_pause_request(void)
{
    int request = pending_request;
    pending_request = -1;
    return request;
}

void act_pause(void)
{
    c2inf.paused ^= 1;
    toggle_count++;
}

void setUp(void)
{
    pending_request = -1;
    toggle_count = 0;
}

void tearDown(void)
{
}

static void request(int paused)
{
    pending_request = paused;
    c2_port_apply_pause_request();
}

static void test_unpaused_game_is_paused_then_restored(void)
{
    c2inf.paused = 0;
    request(1);
    TEST_ASSERT_EQUAL_INT(1, c2inf.paused);
    TEST_ASSERT_EQUAL_INT(1, toggle_count);
    request(0);
    TEST_ASSERT_EQUAL_INT(0, c2inf.paused);
    TEST_ASSERT_EQUAL_INT(2, toggle_count);
}

static void test_player_pause_is_preserved(void)
{
    c2inf.paused = 1;
    request(1);
    TEST_ASSERT_EQUAL_INT(1, c2inf.paused);
    TEST_ASSERT_EQUAL_INT(0, toggle_count);
    request(0);
    TEST_ASSERT_EQUAL_INT(1, c2inf.paused);
    TEST_ASSERT_EQUAL_INT(0, toggle_count);
}

static void test_duplicate_pause_and_spurious_restore_are_idempotent(void)
{
    c2inf.paused = 0;
    request(1);
    request(1);
    TEST_ASSERT_EQUAL_INT(1, c2inf.paused);
    TEST_ASSERT_EQUAL_INT(1, toggle_count);
    request(0);
    request(0);
    TEST_ASSERT_EQUAL_INT(0, c2inf.paused);
    TEST_ASSERT_EQUAL_INT(2, toggle_count);
}

static void test_no_request_does_nothing(void)
{
    c2inf.paused = 0;
    c2_port_apply_pause_request();
    TEST_ASSERT_EQUAL_INT(0, c2inf.paused);
    TEST_ASSERT_EQUAL_INT(0, toggle_count);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_unpaused_game_is_paused_then_restored);
    RUN_TEST(test_player_pause_is_preserved);
    RUN_TEST(test_duplicate_pause_and_spurious_restore_are_idempotent);
    RUN_TEST(test_no_request_does_nothing);
    return UNITY_END();
}
