# Engine scheduling and host-thread design

## Decision

Run the recovered game flow on a dedicated engine worker thread. Keep window
events, rendering, and application lifecycle on the host/main thread. Preserve
the legacy C call stack and blocking modal structure, but make its frame and
wait boundaries cooperate with the host through explicit queues, snapshots,
and condition waits.

This is preferable to an immediate state-machine rewrite. The source has good
frame chokepoints, but callers retain nested modal call stacks. A chokepoint is
an excellent place to wait; it is not by itself a continuation that can return
to the browser and later resume the middle of an arbitrary C function.

## Loop topology

The AST audit found 897 loop nodes in 523 functions. Most are bounded engine
algorithms. Approximately 52 function-level paths contain interactive,
timer-driven, or movie-driven waits.

Ordinary UI and simulation frames are strongly centralized:

- `gloop_start` has 36 direct callers;
- `gloop_end` has 28 direct callers;
- `floop_end` has 8 direct callers;
- `just_idle_game_loop` has 10 direct callers;
- `main_game_loop` is called by the campaign and tutorial flows;
- `battle_game_loop` has one battle driver caller; and
- `refresh_svga_screen` has 51 direct callers.

`main_game_loop` and `battle_game_loop` each perform one frame and return.
Most modal loops call a helper that reaches `gloop_end`, `floop_end`, or
`just_idle_game_loop` once per iteration.

The important paths that bypass the ordinary terminators are finite:

- `select_filename`, which has an inline frame pump;
- `fade_to_palette`;
- `do_vga_smacked_anim` and `do_svga_smacked_anim`;
- the initial movie wait in `start_smacking`;
- `wait_click`, `wait_key`, and `clear_mouse`;
- `click_delay`, `clicked_delay`, and `do_delay`; and
- `act_show_ov_legend`, which directly polls `read_mouse`.

These exceptions need explicit wait integration. They do not justify
threading arbitrary SDL calls through the entire engine.

## Thread ownership

The host/main thread owns:

- SDL initialization and shutdown;
- window and renderer objects;
- event polling and browser lifecycle callbacks;
- texture updates and presentation;
- publication of input state; and
- dispatch of host-only requests.

The engine worker owns:

- recovered startup and campaign control flow;
- simulation and modal functions;
- all mutation of ordinary game globals;
- software rendering into an engine-owned framebuffer;
- synchronous reads through the asset/storage services; and
- calls to the legacy compatibility API.

The host must not inspect or mutate arbitrary legacy globals. Doing so would
turn the whole data segment into an undocumented shared-memory API. Every
cross-thread value is instead copied through a defined boundary.

This split is active in the Linux port. SDL callbacks enqueue neutral events
and present frames on the main thread. A named `caesar2-engine` worker enters
the recovered `c2_engine_main` driver and owns startup, campaign, simulation,
modal flow, and ordinary legacy-global mutation. The SDL lifecycle adapter
never selects screens or calls engine actions.

## Boundary data

### Frame publication

Use at least two indexed framebuffers. The engine draws into its current
buffer. At `refresh_svga_screen`, it publishes a completed buffer together
with:

- a palette snapshot or palette generation number;
- dirty-region metadata when useful;
- logical dimensions and pitch; and
- a monotonically increasing frame number.

Ownership transfers atomically or under a short mutex. The main thread never
uploads from a buffer the worker is modifying.

The current implementation uses a latest-frame mailbox rather than a
free-buffer queue. Publication copies the engine-owned `internal_screen` and
palette into a host-owned indexed buffer under a short mutex. Presentation
copies that mailbox into a main-thread snapshot, releases the mutex, and only
then expands the palette and uploads the texture. Intermediate frames may be
dropped, but neither side ever touches a buffer owned by the other. This
copying strategy is deliberately simpler at 640x480 and keeps the legacy
renderer on its stable framebuffer; replace it with an ownership queue only
if profiling shows the copy to matter.

The mailbox publication itself does not wait for presentation. After
publication, portable `refresh_svga_screen` waits on a drift-corrected 60 Hz
engine deadline. The wait lives in the host timing boundary, where shutdown can
wake it. It replaces the historical throughput cost of banked video copies and
naturally throttles modal loops that already publish every iteration. Missed
deadlines are dropped rather than replayed as catch-up frames. This frame policy
does not drive simulation; recovered millisecond accumulators remain the
simulation clock. See `docs/timing.md` for the original timing mechanisms and
their portable mapping.

### Input publication

Mouse position, wheel state, focus, quit state, and the current button state
form a mutex-protected snapshot. Button-state transitions additionally use a
bounded sample queue. The portable `read_mouse` consumes queued press/release
samples before falling back to the current snapshot, so a complete browser
click between two legacy polls is not lost. Text and key transitions use a
separate bounded event queue. `get_key` dequeues and translates those events
into the legacy key representation.
Engine-thread `set_mouse` and `mouserange` calls update the same protected
virtual cursor; any required native pointer warp is deferred to the SDL main
thread. Absolute desktop events and relative Pointer-Lock events therefore
share one ordered engine-facing position without crossing SDL's main-thread
boundary.

Input remains responsive even when no new frame is ready because the main
thread never waits for the worker. A condition signal wakes explicit engine
input waits.

The neutral-event queue and mouse-transition queue each hold 64 records and
drop the oldest record on overflow so host callbacks can never block behind
the engine. Mouse state, focus, wheel motion, quit state, and a generation
counter remain available as a mutex-protected snapshot. Portable `read_mouse`
feeds the transition queue and then that snapshot into the recovered
`get_mouse` press/release state machine throughout the game.
`--smoke-test` generates input in the SDL test adapter only; it does not
introduce a second game controller.

Smoke-test synchronization is semantic rather than visual. Explicit
engine-thread checkpoints publish an immutable `c2_observation` snapshot into
the host boundary. The SDL test adapter can only read the latest snapshot and
the cumulative reached bitset; it cannot mutate recovered globals. This lets
tests wait for skill selection, province selection and confirmation, province
initialization, city frames, messages, and the forum without framebuffer
signatures or timing the renderer. The observation code is compiled only in
Debug configurations and publication is enabled only for observed test runs.

### Audio and movies

Audio commands carry immutable filenames or decoded buffers, volumes, loop
counts, and stop/pause operations. The engine receives state changes and music
marker notifications through a return queue or atomic service state. Movie
frames use the same ownership rule as ordinary frame publication.

The backend may perform decoding on its own workers, but those workers are an
implementation detail. They do not acquire access to legacy game state.

### Filesystem

Asset and save APIs remain synchronous on the engine worker. Native hosts
perform normal blocking I/O there. The Emscripten build packages assets at
`/assets`; SDL completes its IDBFS synchronization for `/user-data` before
calling `SDL_AppInit`, and only then starts the engine worker.

## Wait semantics

Frame-presenting loops synchronize through portable `refresh_svga_screen`.
Non-presenting waits use explicit primitives:

- wait for input-generation change in `wait_click`, `wait_key`, and
  `clear_mouse`;
- timed wait in palette fades and legacy delay functions;
- movie-frame deadline/event wait instead of spinning on `SmackWait`; and
- shutdown-aware waits everywhere so closing the window cannot strand the
  worker.

The implemented palette wait preserves what the recovered 5 ms comparison
meant against Watcom's coarse DOS clock: advance at the next 18.2 Hz clock
edge. It removes the 20,000-poll CPU-speed ceiling without interpreting the
comparison as a literal high-resolution 5 ms delay. The implemented
vertical-blank substitute uses an independent 60 Hz deadline. Both use the
same shutdown-aware host condition as frame pacing; neither turns the cheap
mouse poll into a blocking operation.

`read_mouse` itself must remain a cheap poll. Making every call block would
stall animation when the pointer is stationary. Blocking belongs in the
functions whose semantics are actually to wait.

## Native and browser execution

Native SDL could technically run the legacy loop on the main thread and poll
events from inside compatibility shims. That would preserve responsiveness,
but it creates a different architecture from the browser and makes later
main-thread-only services harder to reason about.

The implemented shared design keeps SDL callbacks on the main thread and the
legacy loop on the engine worker for Linux and threaded Wasm, with the same
structure intended for native Windows and macOS.
The browser build consequently requires pthread support and deployment with
the cross-origin isolation headers needed for `SharedArrayBuffer`. Threaded
and non-threaded Wasm artifacts should be treated as separate build products.

The main thread does not synchronously wait for the worker during normal
execution. It returns from every application callback and drains published
frames and requests on later iterations. Native and browser targets request a
120 Hz SDL callback while the window is focused and the physical pointer is
inside the game surface, keeping input publication and mailbox pickup close
to an 8 ms cadence. SDL permits the callback-rate hint to change at runtime;
the host reduces it to 15 Hz when either condition is false and restores
120 Hz on the corresponding focus/pointer event. An engine-requested virtual
cursor warp does not count as the physical pointer re-entering the surface.
This host-service rate does not alter the engine worker's independent 60 Hz
frame deadline or the browser compositor's display refresh rate.

## Alternatives

### Asyncify

Asyncify can suspend a single-threaded Wasm call stack at a host wait and
resume it later. It is a viable fallback or diagnostic build because it
preserves modal source shape, but it increases code size and makes suspension
an Emscripten-specific property of otherwise ordinary functions. It is not the
primary architecture.

### State-machine conversion

A true callback-driven, non-threaded, non-Asyncify build must convert the
campaign driver and every reachable modal/wait function into resumable state.
The roughly 52 wait paths make that possible but invasive. Such a conversion
may be worthwhile later for latency or platform reach, after the worker-thread
port provides a behavioral reference and tests.

### Main-thread legacy loop

Running the legacy loop on the main thread is acceptable for a headless test
or a narrowly scoped native bring-up. It is not the cross-platform production
design because SDL presentation is main-thread-bound and browser callbacks
must return.

## Shutdown and failure

Shutdown is a state transition, not an arbitrary `exit()` call:

1. the main thread publishes a shutdown request and wakes all engine waits;
2. the engine leaves modal/campaign flow through the portable exit path;
3. audio, movies, and storage flush on their owning side;
4. the worker joins; and
5. the main thread destroys SDL resources.

Fatal engine errors publish a structured failure containing a message and
status. The main thread displays or logs it and follows the same shutdown
sequence.

On native POSIX Debug builds, faults that cannot use that orderly path are
covered by process-wide fatal-signal handlers installed before the engine
thread starts. They emit the current thread's native backtrace and re-raise the
signal. This diagnostic implementation is compiled out of non-Debug builds.

## Verification

Scheduling work should add:

- a headless deterministic worker runner;
- additional semantic observations where new blocking boundaries require
  deterministic tests;
- scripted input playback through the host input queue;
- tests that close the application while blocked in every exceptional wait;
- ThreadSanitizer coverage for native debug builds; and
- counters asserting that the host never presents a buffer owned by the
  engine.
