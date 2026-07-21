#include <unity/unity.h>
#include <stdint.h>

#include "c2_port.h"

extern int running_delay1(void);
extern char colour_cycle_delay1(int delay_ms);

int time_is;

static uint64_t fake_ticks;
static uint64_t fake_wall_seconds;

uint64_t c2_host_ticks_ms(void)
{
    return fake_ticks;
}

uint64_t c2_host_wall_time_seconds(void)
{
    return fake_wall_seconds;
}

void c2_host_wait_until_ms(uint64_t deadline_ms)
{
    if (fake_ticks < deadline_ms) fake_ticks = deadline_ms;
}

static void test_dos_clock_observation(void)
{
    fake_ticks = 0;
    fake_wall_seconds = 1234;
    c2_port_timing_reset();
    TEST_ASSERT_TRUE(running_delay1() == 999);
    TEST_ASSERT_TRUE(time_is == 1234);
    fake_ticks = 17;
    TEST_ASSERT_TRUE(running_delay1() == 0);
    fake_ticks = 54;
    TEST_ASSERT_TRUE(running_delay1() == 0);
    fake_ticks = 55;
    TEST_ASSERT_TRUE(running_delay1() == 50);
    fake_ticks = 110;
    TEST_ASSERT_TRUE(running_delay1() == 50);
    fake_ticks = 165;
    TEST_ASSERT_TRUE(running_delay1() == 60);
}

static void test_dos_clock_wait(void)
{
    fake_ticks = 0;
    c2_port_timing_reset();
    TEST_ASSERT_TRUE(colour_cycle_delay1(60) == 0);
    TEST_ASSERT_TRUE(c2_port_wait_dos_clock_tick());
    TEST_ASSERT_TRUE(fake_ticks == 55);
    TEST_ASSERT_TRUE(colour_cycle_delay1(60) == 0);
    TEST_ASSERT_TRUE(c2_port_wait_dos_clock_tick());
    TEST_ASSERT_TRUE(fake_ticks == 110);
    TEST_ASSERT_TRUE(colour_cycle_delay1(60) == 1);
}

static void test_frame_deadlines(void)
{
    int i;
    static const uint64_t frame_deadlines[6] = { 16, 33, 50, 66, 83, 100 };

    fake_ticks = 0;
    c2_port_timing_reset();
    for (i = 0; i < 6; i++) {
        c2_port_wait_for_frame();
        TEST_ASSERT_TRUE(fake_ticks == frame_deadlines[i]);
    }
}

static void test_vblank_deadline(void)
{
    fake_ticks = 0;
    c2_port_timing_reset();
    c2_port_wait_vblank();
    TEST_ASSERT_TRUE(fake_ticks == 16);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_dos_clock_observation);
    RUN_TEST(test_dos_clock_wait);
    RUN_TEST(test_frame_deadlines);
    RUN_TEST(test_vblank_deadline);
    return UNITY_END();
}
