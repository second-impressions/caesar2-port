#include <limits.h>
#include <stdint.h>

#include "c2_host.h"
#include "c2_port.h"

extern int time_is;

/*
 * INT 21h/AH=2Ch obtained its hundredths field from the 18.2 Hz BIOS
 * timer. Watcom's ftime() multiplied that field by ten, so its apparent
 * millisecond clock advanced in 50 ms or 60 ms steps.
 */
#define C2_PIT_INPUT_HZ UINT64_C(1193182)
#define C2_PIT_COUNTS_PER_TICK UINT64_C(65536)
#define C2_MILLISECONDS_PER_SECOND UINT64_C(1000)
#define C2_DOS_TICK_DENOMINATOR \
    (C2_PIT_COUNTS_PER_TICK * C2_MILLISECONDS_PER_SECOND)

struct c2_rate_deadline {
    uint64_t deadline_ms;
    unsigned int remainder;
    int initialized;
};

static struct c2_rate_deadline c2_frame_deadline;
static struct c2_rate_deadline c2_vblank_deadline;
static uint64_t c2_dos_clock_origin;
static uint64_t c2_dos_clock_wall_seconds;
static uint64_t c2_elapsed_last;
static int c2_cycle_last1;
static int c2_cycle_last2;
static int c2_timer_start_ms;
static int c2_timer_start_sec;
static int c2_elapsed_initialized;

static uint64_t dos_tick_count(uint64_t now)
{
    uint64_t elapsed;

    elapsed = now - c2_dos_clock_origin;
    return elapsed * C2_PIT_INPUT_HZ / C2_DOS_TICK_DENOMINATOR;
}

static uint64_t dos_elapsed_ms(uint64_t now)
{
    uint64_t ticks;
    uint64_t hundredths;

    ticks = dos_tick_count(now);
    hundredths = ticks * C2_PIT_COUNTS_PER_TICK * UINT64_C(100) /
        C2_PIT_INPUT_HZ;
    return hundredths * UINT64_C(10);
}

static uint64_t dos_clock_ms(void)
{
    return c2_dos_clock_wall_seconds * C2_MILLISECONDS_PER_SECOND +
        dos_elapsed_ms(c2_host_ticks_ms());
}

static void wait_next_60hz(struct c2_rate_deadline *rate)
{
    uint64_t now;

    now = c2_host_ticks_ms();
    if (!rate->initialized || now > rate->deadline_ms + 17) {
        rate->deadline_ms = now;
        rate->remainder = 0;
        rate->initialized = 1;
    }

    rate->deadline_ms += 16;
    rate->remainder += 40;
    if (rate->remainder >= 60) {
        rate->deadline_ms++;
        rate->remainder -= 60;
    }
    c2_host_wait_until_ms(rate->deadline_ms);
}

void c2_port_timing_reset(void)
{
    c2_frame_deadline.deadline_ms = 0;
    c2_frame_deadline.remainder = 0;
    c2_frame_deadline.initialized = 0;
    c2_vblank_deadline.deadline_ms = 0;
    c2_vblank_deadline.remainder = 0;
    c2_vblank_deadline.initialized = 0;
    c2_dos_clock_origin = c2_host_ticks_ms();
    c2_dos_clock_wall_seconds = c2_host_wall_time_seconds();
    c2_elapsed_last = 0;
    c2_cycle_last1 = 0;
    c2_cycle_last2 = 0;
    c2_timer_start_ms = 0;
    c2_timer_start_sec = 0;
    c2_elapsed_initialized = 0;
}

int c2_port_wait_dos_clock_tick(void)
{
    uint64_t next_tick;
    uint64_t elapsed_deadline;
    uint64_t deadline;

    next_tick = dos_tick_count(c2_host_ticks_ms()) + 1;
    elapsed_deadline =
        (next_tick * C2_DOS_TICK_DENOMINATOR + C2_PIT_INPUT_HZ - 1) /
        C2_PIT_INPUT_HZ;
    deadline = c2_dos_clock_origin + elapsed_deadline;
    c2_host_wait_until_ms(deadline);
    return c2_host_ticks_ms() >= deadline;
}

void c2_port_wait_for_frame(void)
{
    wait_next_60hz(&c2_frame_deadline);
}

void c2_port_wait_vblank(void)
{
    wait_next_60hz(&c2_vblank_deadline);
}

int running_delay1(void)
{
    uint64_t now;
    uint64_t elapsed;

    now = dos_clock_ms();
    time_is = (int)(now / C2_MILLISECONDS_PER_SECOND);
    if (!c2_elapsed_initialized) {
        elapsed = 999;
        c2_elapsed_initialized = 1;
    } else {
        elapsed = now - c2_elapsed_last;
        if (elapsed > INT_MAX) elapsed = 999;
    }
    c2_elapsed_last = now;
    return (int)elapsed;
}

int colour_cycle_delay1(int delay_ms)
{
    int now;
    int delta;

    if (delay_ms <= 0) return 1;
    now = (int)(dos_clock_ms() % C2_MILLISECONDS_PER_SECOND);
    if (now > c2_cycle_last1) {
        delta = now - c2_cycle_last1;
    } else if (now < c2_cycle_last1) {
        delta = now + 1000 - c2_cycle_last1;
    } else {
        delta = 0;
    }
    if (delta < delay_ms) return 0;
    c2_cycle_last1 = now;
    return 1;
}

int colour_cycle_delay2(int delay_ms)
{
    int now;
    int delta;

    if (delay_ms <= 0) return 1;
    now = (int)(dos_clock_ms() % C2_MILLISECONDS_PER_SECOND);
    if (now > c2_cycle_last2) {
        delta = now - c2_cycle_last2;
    } else if (now < c2_cycle_last2) {
        delta = now + 1000 - c2_cycle_last2;
    } else {
        delta = 0;
    }
    if (delta < delay_ms) return 0;
    c2_cycle_last2 = now;
    return 1;
}

int timer(int mode)
{
    uint64_t now;
    int now_ms;
    int now_sec;
    int delta;

    now = dos_clock_ms();
    now_ms = (int)(now % C2_MILLISECONDS_PER_SECOND);
    now_sec = (int)(now / C2_MILLISECONDS_PER_SECOND);
    if (mode == 0) {
        c2_timer_start_ms = now_ms;
        c2_timer_start_sec = now_sec;
        return 0;
    }
    if (mode != 1) return 0;
    delta = (now_sec - c2_timer_start_sec) * 1000;
    if (now_ms < c2_timer_start_ms) now_ms += 1000;
    return delta + now_ms - c2_timer_start_ms;
}
