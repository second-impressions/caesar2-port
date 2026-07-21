# Legacy timing and portable scheduling

## Scope

The DOS game does not have one master frame clock. It combines three distinct
timing mechanisms, and preserving their distinction matters: simulation speed
is elapsed-time based, some explicit delays are synchronized to VGA vertical
blank, while ordinary rendering and a few bounded polling loops depend on how
quickly the contemporary CPU and video hardware complete their work.

The portable build replaces only the hardware- and throughput-dependent parts.
It does not convert the recovered game loops into a fixed-timestep engine.

## 1. Wall-clock elapsed time

`lib32.c::running_delay1` calls Watcom `ftime`, forms an apparent millisecond
timestamp, returns the difference from its preceding invocation, and also
copies the seconds part to `time_is`. The engine stores the returned value in
`button_time_flag`.

Those apparent milliseconds were not a high-resolution clock. The DOS Watcom
runtime obtains the time through `INT 21h`, function `2Ch`, and multiplies its
hundredths field by ten. That field is derived from the PC timer interrupt:
1,193,182 input counts divided by 65,536, or about 18.2065 Hz. Consequently
`ftime` normally repeats the same value and then jumps by 50 or 60 ms. Open
Watcom's own [`delay.c`](https://github.com/open-watcom/open-watcom-v2/blob/master/bld/clib/process/c/delay.c)
documents both the 5/100-to-6/100-second resolution and a 50-to-60-ms minimum
delay. [DOSBox Staging's DOS time service](https://github.com/dosbox-staging/dosbox-staging/blob/main/src/dos/dos.cpp)
independently shows the conversion from BIOS/PIT ticks to the returned
hundredths field.

The important consumers are:

- `game_speed`, which accumulates milliseconds and advances the city simulation
  when `(100 - game_speed) / 10 * 50 + 50` milliseconds have elapsed;
- `scroll_speed`, which uses the same accumulator pattern for map scrolling;
- modal and button loops, which use a nonzero elapsed value to advance button
  repeat state;
- palette animation gates of 60 ms and 150 ms; and
- message expiry, which compares the `time_is` seconds value.

This means the simulation was already real-time based. A portable frame cap
must not replace those accumulators with a frame count.

The DOS implementation uses wall time and 32-bit arithmetic. That permits
clock adjustments and timestamp wrap to appear as a 999 ms result. The
portable implementation in `src/platform/common/c2_port_timing.c` anchors an
emulated DOS clock to host monotonic time, using the original PIT rate and
centisecond truncation. `running_delay1` therefore returns zero between DOS
ticks and 50 or 60 when the modeled tick advances. Absolute wall-clock seconds
are sampled at reset to maintain `time_is`; subsequent elapsed time remains
monotonic. The first elapsed read returns 999, retaining the observed original
first-call behavior without depending on the current epoch's low 32 bits.

`colour_cycle_delay1`, `colour_cycle_delay2`, and the recovered `timer` helper
read the same modeled DOS clock in portable builds. The colour gates preserve
the recovered millisecond-within-the-second rollover arithmetic and remain
independent; calling one does not advance another.

## 2. Vertical-blank synchronization

The two recovered vertical-blank primitives have the same hardware shape:

1. poll VGA status port `0x3da` until the current blanking interval ends;
2. poll until the next blanking interval begins; and
3. return at that boundary.

`wvbl1` is the assembly form and has no direct game caller in PS.EXE. `wvbl2`
is the C form. It is used by `do_delay`, which waits for 25 vertical blanks per
argument unit, and by the VGA Smacker transition. The duration therefore
followed the active display refresh rate rather than a fixed millisecond
constant. At the normal 60 Hz 640x480 VGA cadence, one blank is about 16.67 ms
and one `do_delay(1)` is about 417 ms.

Portable `wvbl2` delegates to `c2_port_wait_vblank`. It maintains its own
drift-corrected 60 Hz deadline, independent of ordinary frame publication.
Integer millisecond deadlines follow the repeating 16, 17, 17 ms pattern, so
six waits total exactly 100 ms. Falling more than one period behind resets the
deadline instead of issuing a burst of catch-up iterations.

The 60 Hz value is an explicit port policy. The original code contains no
literal refresh rate; it follows the configured VGA mode. Sixty hertz matches
the normal 640x480 VGA mode used by the game and gives the explicit wait
functions their intended order of magnitude.

## 3. Throughput-bound loops and frame cadence

Two original behaviors are not genuinely clocked.

First, `refresh_svga_screen` copies dirty 16x16 blocks through banked VESA
memory and returns. It contains no vertical-blank wait and no wall-clock gate.
Consequently the ordinary UI frame rate emerged from CPU speed, the number of
dirty blocks, bank switching, and video-memory bandwidth. Some controls count
rendered iterations for their repeat ramp, so running that loop hundreds of
times per second changes interaction even though simulation steps still use
elapsed milliseconds.

The portable `refresh_svga_screen` publishes the indexed framebuffer and then
calls `c2_port_wait_for_frame`. This is a separate drift-corrected 60 Hz
deadline. It gives modal controls and cursor animation a stable cadence while
leaving `game_speed` driven by real elapsed milliseconds. If rendering exceeds
the budget, the scheduler drops the missed deadline and resumes from the
current time; it never runs fast frames to catch up.

Second, a few recovered waits combine the DOS clock with a fixed polling
ceiling. The startup palette fade asks for a 5 ms interval but abandons the
wait after 20,000 calls to `running_delay1`. Five milliseconds is below the
clock's 50-to-60-ms resolution: on DOS, the loop normally ends when the next
clock tick produces a 50- or 60-ms delta. It does not produce one palette step
every 5 ms. The 20,000-poll bound is a CPU-era failsafe, not the intended
duration.

Using a modern high-resolution `ftime` exposed both incompatibilities at once:
20,000 vDSO calls completed before 5 ms, so the bound won and each whole logo
lasted only about 51-to-52 ms. Waiting for literal 5 ms steps improved that to
about 0.67 seconds, but was still not the DOS behavior.

In portable builds, the recovered palette stepping and click-to-skip logic are
unchanged. When the recovered loop still needs time, it waits until the next
modeled DOS clock edge and samples `running_delay1` again. There is no
logo-specific duration constant. A live file-open trace now measures 6.97
seconds for the first complete logo interval and 7.05 seconds for the second,
including each fade in, fade out, file access, and frame publication.

`click_delay` and `clicked_delay` are another CPU-counted family: 1,000 warmup
mouse polls followed by 8,000 polls per argument unit. PS.EXE has no direct
caller for either function, so they are currently dormant and do not define a
portable gameplay cadence. They must be converted to an explicit deadline if a
future recovered or new call path makes them live; their iteration counts must
not be treated as milliseconds.

The recovered save dialog has a similar but live construct: after the
synchronous save has completely closed both files, it executes 1,000
`just_idle_game_loop` iterations to keep “Saving Game -- PLEASE WAIT” visible.
On the original hardware this was a CPU/video-throughput cosmetic hold, not
part of the file operation and not a duration expressed in time. Applying the
portable 60 Hz frame policy to it would manufacture a roughly 16.7-second
delay. Loading has the same construct with 200 frames after the complete read,
which would become about 3.3 seconds. `C2_FEAT_POST_FILE_BUSY_WAIT` retains both
loops for the shipped targets and removes them from the portable target. Each
message is presented once before synchronous I/O and the dialog continues as
soon as that operation finishes.

## Host boundary and shutdown

The common timing adapter depends only on `c2_host_ticks_ms`,
`c2_host_wall_time_seconds`, and `c2_host_wait_until_ms`. The SDL backend
implements the monotonic source with `SDL_GetTicks` and implements deadline
waits on the existing input/shutdown condition variable. Input may wake the
condition, but the wait resumes until its deadline; shutdown terminates it
immediately. SDL names and objects do not enter recovered engine files.

`tests/c2_port_timing_test.c` uses a fake host clock to verify the DOS sequence
of repeated values followed by 50/50/60-ms deltas, a colour gate spanning two
DOS ticks, the 60 Hz deadline sequence, and the independent vertical-blank
schedule. End-to-end smoke tests exercise the same timing adapter through the
recovered startup, modal, and city loops.

## Calibration rule

Do not tune simulation speed by changing the 60 Hz frame policy. If calendar,
citizen, or economy progression is wrong, inspect `running_delay1`,
`button_time_flag`, and the `game_speed` accumulator in milliseconds. Change
the frame policy only for frame-counted behavior such as button repeat, cursor
animation, or presentation smoothness, and compare those behaviors against the
original separately.
