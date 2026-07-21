#include <assert.h>
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

int main(void)
{
    int i;
    static const uint64_t frame_deadlines[6] = { 16, 33, 50, 66, 83, 100 };

    fake_ticks = 0;
    fake_wall_seconds = 1234;
    c2_port_timing_reset();
    assert(running_delay1() == 999);
    assert(time_is == 1234);
    fake_ticks = 17;
    assert(running_delay1() == 0);
    fake_ticks = 54;
    assert(running_delay1() == 0);
    fake_ticks = 55;
    assert(running_delay1() == 50);
    fake_ticks = 110;
    assert(running_delay1() == 50);
    fake_ticks = 165;
    assert(running_delay1() == 60);

    fake_ticks = 0;
    c2_port_timing_reset();
    assert(colour_cycle_delay1(60) == 0);
    assert(c2_port_wait_dos_clock_tick());
    assert(fake_ticks == 55);
    assert(colour_cycle_delay1(60) == 0);
    assert(c2_port_wait_dos_clock_tick());
    assert(fake_ticks == 110);
    assert(colour_cycle_delay1(60) == 1);

    fake_ticks = 0;
    c2_port_timing_reset();
    for (i = 0; i < 6; i++) {
        c2_port_wait_for_frame();
        assert(fake_ticks == frame_deadlines[i]);
    }

    fake_ticks = 0;
    c2_port_timing_reset();
    c2_port_wait_vblank();
    assert(fake_ticks == 16);

    return 0;
}
