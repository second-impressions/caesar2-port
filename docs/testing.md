# Testing and diagnostics

## Smoke tests

Display-free smoke tests drive input through the host boundary exactly as a
player would (the game's own polling and hit-testing; no engine code is
skipped). They edit and accept a player name through the recovered name
dialog before continuing. Their synchronization uses a read-only semantic observation stream rather than
framebuffer signatures or fixed delays. The entire observation and smoke-test
surface is compiled only in Debug configurations; release binaries do not
contain it or accept its command-line flags. The fast test stops at the
recovered province selector:

```bash
./build/port/linux-debug/caesar2 --smoke-test --asset-root /path/to/CAESAR2
```

The city-loop scenario selects and confirms a province, observes province
initialization, dismisses recovered message modals, pauses and resumes, pans,
zooms, opens and closes the recovered forum, and then verifies clean worker
shutdown:

```bash
./build/port/linux-debug/caesar2 --city-smoke-test --asset-root /path/to/CAESAR2
```

The build scenarios place things through the real command strip, selection
lists and map clicks. The province build puts down a farm and answers its
warehouse and work-camp questions; the city build opens the health list,
places baths (a 2x2 footprint, which re-evolves the whole city map at once
and used to divide by zero in the port) and checks the city loop survives:

```bash
./build/port/linux-debug/caesar2 --province-build-smoke-test --asset-root /path/to/CAESAR2
./build/port/linux-debug/caesar2 --city-build-smoke-test --asset-root /path/to/CAESAR2
```

The tutorial scenario selects the recovered Tutorial action, advances through
every available page, exits interactive stages through normal input, declines
the final continue prompt, and verifies return to the original menu:

```bash
./build/port/linux-debug/caesar2 --tutorial-smoke-test --asset-root /path/to/CAESAR2
```

The save/load scenario enters a city, saves `c2smoke.sav` through the recovered
filename editor, reads the file back from the host, and compares all 221,745
registered state bytes plus the 4,000-byte history block. It then changes the
view, loads through the recovered dialog, repeats the complete comparison, and
verifies semantic state after re-entry into the city loop. The native,
corruption-injection, and browser/OPFS layers are documented in
[`docs/save-testing.md`](docs/save-testing.md):

```bash
./build/port/linux-debug/caesar2 --save-load-smoke-test --asset-root /path/to/CAESAR2
```

Pass `--screenshot output.png` to write the final headless frame or the current
interactive startup state as a PNG beneath the user-data root. The recovered
screenshot hotkeys likewise write `shot1.png` through `shot8.png`.

## Test suites

To register the semantic smoke tests with CTest, configure with
`-DC2_TEST_DATA_DIR=/path/to/CAESAR2` and run `ctest --preset linux-debug`.
Native C unit tests use Unity, supplied by the Nix development shell, while
CTest remains the suite runner. Pytest covers repository tooling and static
layering checks; the Debug-only smoke drivers cover recovered engine flows.
## Sanitizers

The `linux-tsan` configure/build/test preset runs the same worker-thread slice
under Clang ThreadSanitizer. The `linux-asan` preset combines AddressSanitizer
and UndefinedBehaviorSanitizer with globals instrumented: the recovered code
occasionally reads past one global into its neighbour because the original
linker happened to place them together, and those reads (which crash or
corrupt saves in the port) only show up with redzones between globals. Build
and play the ASan binary when developing; `PORT_ASAN_DISABLE_GLOBALS=ON` is
available if the global redzones ever get in the way. The sanitizer binary
carries its own runtime defaults (`src/platform/posix/c2_posix_sanitizer.c`):
reports are symbolized through `llvm-symbolizer` or, failing that, whatever
`addr2line` is on `PATH`, so a copy on another machine still reports names and
lines, and exit-time leaks inside system libraries (ALSA, PulseAudio, X11,
Wayland, Mesa, GTK…) are suppressed so only the port's own remain.

## Crash reports

Native POSIX builds install fatal-signal handlers for `SIGSEGV`,
`SIGABRT`, `SIGBUS`, `SIGILL`, and `SIGFPE`. A crash on either the SDL or engine
thread prints the build version, the signal, fault address, and native
backtrace to standard error, followed by a request to file the output as an
issue, then re-raises the signal so normal debugger and core-dump behavior is
retained.
ASan and TSan presets leave it off so the sanitizer runtimes retain their own
signal diagnostics. When the build found libbacktrace (`PORT_WITH_LIBBACKTRACE`,
default `AUTO`), each frame is printed with function, source file and line
(`#3 0x... cap_land_value at src/evolver.c:834`), so the log pasted into an
issue is already resolved. Without it the executable's exported symbols still
name engine frames (`caesar2(get_ptr_to_corner+0x38)`), and the report ends
with the `addr2line` command that adds source lines against the crashed
binary.


