# Caesar II Port

Portable continuation of the byte-exact
[Caesar II reconstruction](https://github.com/second-impressions/caesar2-reconstruction).
This repository preserves the reconstruction's Git ancestry but is an
independent project rather than a GitHub fork.

The port keeps recovered engine files in place and puts modern platform code
behind narrow target boundaries.  That makes upstream decompilation advances
straightforward to cherry-pick without preventing deliberate fixes and new
features here.

The durable port design is documented in:

- [`docs/platform-boundary.md`](docs/platform-boundary.md) — the audited
  function, subsystem, and assembly boundary;
- [`docs/engine-scheduling.md`](docs/engine-scheduling.md) — worker-thread,
  frame-publication, input, and browser scheduling;
- [`docs/webassembly.md`](docs/webassembly.md) — browser build, deployment,
  persistence, and Wasm ABI adaptation;
- [`docs/localization.md`](docs/localization.md) — native language labels,
  runtime Web profiles, localized speech, and asset requirements;
- [`docs/game-data-sources-plan.md`](docs/game-data-sources-plan.md) — native
  and browser data import, durable storage, and optimized asset packs;
- [`docs/timing.md`](docs/timing.md) — the three original timing mechanisms and
  their monotonic, vertical-blank, and frame-paced portable counterparts;
- [`docs/media-implementation.md`](docs/media-implementation.md) — the
  SDL3 PCM, Smacker decoding, and branch-aware XMIDI/OPL3 media stack;
- [`docs/legacy-abi.md`](docs/legacy-abi.md) — packing, pointer width,
  signedness, serialization, and compiler semantics; and
- [`docs/recovered-source-delta-audit.md`](docs/recovered-source-delta-audit.md)
  — the justification and enforcement status of every port-only edit to a
  recovered source file.

Source ownership follows the same boundary: recovered engine C remains in
`src/`, CPU-only translations of recovered assembly live in `src/asm/`,
backend-neutral legacy shims live in `src/platform/common/`, and concrete host
backends live in `src/platform/<backend>/`. New backends are selected by the
build rather than threaded through shared code with compiler-specific tests.

## Versioning and hosted Web build

Published builds use `major.minor.patch-build-githash`, beginning at `1.0.0`.
CMake derives the local clean-checkout build number from the commit count and
an eight-character revision; CI supplies the GitHub Actions run number and
revision explicitly. An edited local worktree instead uses the honest,
cache-distinct `1.0.0-YYYYMMDD-HHMMSS` form. The version is available through
`caesar2 --version`, the native window title, browser shell, published
`version.txt`, startup notice, and in-game about box. The latter two replace
the shipped "Version 1.1" and release date from `c2.eng` with a
"Caesar II - Portable" heading and this build's exact version tag.

Every push or merge to `main` runs the single WebAssembly job in
`.github/workflows/ci.yml`; its artifact is then deployed by the dependent
GitHub Pages job without rebuilding. A
same-origin service worker supplies COOP/COEP on static Pages hosting so the
threaded runtime remains cross-origin isolated. The hosted page asks the user
for game data on first use and retains it in OPFS.

## Native Linux port

The native executable now enters the recovered `c2.c` program driver and uses
the original startup, options, province-selection, province-initialization,
simulation, modal, and UI control flow. All recovered engine translation units
needed by the current path, including the full `lib32.c` and `pcsound.c`, are
compiled. The historical Miles and RAD device translation units remain
excluded; narrow common adapters implement their device/codec edge. The port
directory does not contain a second startup state machine, duplicated hitboxes,
or replacement screens.

WAV effects and RAW speech use SDL3 audio streams. `INTRO.SMK`, embedded
message movies, and the VGA-era cinematics are decoded by the pinned Second
Impressions libsmacker fork and run through the recovered playback loops.
Branch-aware XMIDI music is sequenced and synthesized by the pinned Second
Impressions libADLMIDI fork, with the recovered mood and branch policy still
in control. Save-file
enumeration, original-format save/load streams, preferences, history,
autosaves, and screenshots use the portable user-data service described in
[docs/user-data.md](docs/user-data.md).
These are platform capabilities, not alternate game-flow implementations: name entry
uses the recovered editor, and after a province is confirmed the recovered
code initializes it and enters the recovered city game loop.

The recovered startup flow runs on an engine worker. The SDL main thread owns
events and presentation, communicating through the backend-neutral
`c2_host_*` API. The engine thread pumps music into private SDL streams, so
XMIDI triggers and their resulting branch decisions never mutate recovered
state from an audio callback. The WebAssembly target uses this same recovered
engine, SDL callback host, and worker split. Build and deployment instructions
are in [docs/webassembly.md](docs/webassembly.md).

Original game data is required and is never committed.  From the Nix
development shell:

```bash
git submodule update --init
nix develop
cmake --preset linux-debug
cmake --build --preset linux-debug
./build/port/linux-debug/caesar2 --asset-root /path/to/CAESAR2
```

English is the default distribution tag. Pass `-DC2_LANGUAGE=de`, `fr`, or
another two-letter tag at configure time and use the matching complete
localized installation. Language packaging, including localized RAW voices,
is documented in
[docs/localization.md](docs/localization.md).

For an optimized build, use `cmake --preset linux-release` followed by
`cmake --build --preset linux-release`. Its native Unity suite is available as
`ctest --preset linux-release`; Debug-only semantic smoke tests are omitted.

Game data can be selected with a positional source or `--game-data SOURCE`.
`SOURCE` may be an installed directory, a ZIP, an optimized `.c2assets` pack,
a plain ISO, or a CUE beside its BIN. `--asset-root PATH` and `C2_ASSET_ROOT`
remain compatibility aliases for directory sources. Archives/images are
validated and cached beneath the user-data directory; subsequent launches
reuse that cache. `--asset-profile NAME` selects a language/media profile from
a multi-profile asset pack. Writable runtime files use the separate
`--user-data-dir PATH` or `C2_USER_DATA_DIR` namespace. Without an override,
SDL selects and creates the platform-standard application data directory
(`$XDG_DATA_HOME/second-impressions/caesar2` on Linux, with the usual
`~/.local/share` fallback).

A directory source may retain the original DOS CD layout (`HD` plus media
siblings) or a hybrid `C2WIN95` layout; both are detected automatically. Files
are resolved case-insensitively from its top level first, then `.pl8`, `.raw`,
`.xmi`, and `.smk` assets fall back to the matching `pl8/`, `raw/`, `xmi/`,
and `smk/` media directories.

Create a deduplicated multi-language/media pack with the repository tool:

```bash
uv run tools/c2-assets.py build \
  --core /path/to/base-install \
  --text en=/path/to/english --speech en=/path/to/english \
  --text de=/path/to/german  --speech de=/path/to/german \
  --video mac=/path/to/extracted/mac/SMK \
  --output caesar2-all.c2assets
uv run tools/c2-assets.py verify caesar2-all.c2assets
```

`--format iso` emits the same content-addressed pack as an ISO-9660 image.
The Mac `INTRONEW.SMK` is exposed as the engine's logical `INTRO.SMK`.

Synthetic ZIP, ISO, BIN/CUE, layout, and pack tests are part of the ordinary
CTest/Pytest suites and need no copyrighted data. Real corpus tests are opt-in:

```bash
cmake --preset linux-debug \
  -DC2_TEST_GAME_DATA_SOURCES="/path/release.iso;/path/other.cue;/path/install.zip"
cmake --build --preset linux-debug
ctest --preset linux-debug -L game-data-corpus --output-on-failure
```

The option is empty in CI; no original images are downloaded automatically.

Save names retain the recovered 8.3-style UI limit. Lookup and overwrite are
case-insensitive even on case-sensitive hosts. Set the CMake cache path
`C2_TEST_SAVE_FIXTURE` to an original save to include fixture compatibility in
the Unity suite; original game files are never committed.

Mouse interaction, button geometry, modal behavior, and province hit-testing
all come from the recovered engine. The SDL backend only publishes input
snapshots and frames. It translates the recovered F1--F5 shortcuts, Alt+F,
Alt+F1, Alt+F3, Alt+D, Alt+X, and Alt+1--Alt+8 chords to their original DOS
scan codes. Vertical mouse-wheel motion uses the engine's existing `+`/`-`
zoom actions, so keyboard and wheel input retain the same game-side rules.

Windowed play uses an eight-logical-pixel edge zone for the recovered map
scrolling behavior and stops scrolling as soon as the pointer leaves the game
viewport. The pointer is free to leave the window by default. Pass
`--mouse-lock` to confine it to the rendered game area; `--no-mouse-lock`
explicitly selects the default. The lock option uses native confinement where
available and falls back to a relative virtual cursor, which is also the
browser target's Pointer Lock model. Browsers which require a user gesture
retry the request on the next click.

Display-free smoke tests drive input through that same host boundary. They edit
and accept a player name through the recovered name dialog before continuing.
Their
synchronization uses a read-only semantic observation stream rather than
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

The tutorial scenario selects the recovered Tutorial action, advances through
every available page, exits interactive stages through normal input, declines
the final continue prompt, and verifies return to the original menu:

```bash
./build/port/linux-debug/caesar2 --tutorial-smoke-test --asset-root /path/to/CAESAR2
```

The save/load scenario enters a city, saves `c2smoke.sav` through the recovered
filename editor, changes the view, loads through the recovered dialog, and
verifies both restored state and re-entry into the city loop:

```bash
./build/port/linux-debug/caesar2 --save-load-smoke-test --asset-root /path/to/CAESAR2
```

Pass `--screenshot output.png` to write the final headless frame or the current
interactive startup state as a PNG beneath the user-data root. The recovered
screenshot hotkeys likewise write `shot1.png` through `shot8.png`.

To register the semantic smoke tests with CTest, configure with
`-DC2_TEST_DATA_DIR=/path/to/CAESAR2` and run `ctest --preset linux-debug`.
Native C unit tests use Unity, supplied by the Nix development shell, while
CTest remains the suite runner. Pytest covers repository tooling and static
layering checks; the Debug-only smoke drivers cover recovered engine flows.
The `linux-tsan` configure/build/test preset runs the same worker-thread slice
under Clang ThreadSanitizer. The `linux-asan` preset combines AddressSanitizer
and UndefinedBehaviorSanitizer. It disables ASan global instrumentation because
the recovered program has a very large legacy global data segment; heap,
stack, and the live engine path remain instrumented.

Native POSIX Debug builds also install fatal-signal handlers for `SIGSEGV`,
`SIGABRT`, `SIGBUS`, `SIGILL`, and `SIGFPE`. A crash on either the SDL or engine
thread prints the signal, fault address, and native backtrace to standard error,
then re-raises the signal so normal debugger and core-dump behavior is retained.
The handler is absent from release builds. ASan and TSan presets leave it off
so the sanitizer runtimes retain their own signal diagnostics.
Executable frames are printed with load-independent `+0x...` offsets; resolve
one with `addr2line -e build/port/linux-debug/caesar2 -f -C 0xOFFSET`.

The recovered fixed-width default player name contains sixteen trailing
spaces. The portable build trims trailing spaces before entering the recovered
editor so End targets the visible end of the name, including for old
`caesar2.inf` files. Set `PORT_FIX_PLAYER_NAME_PADDING=0`, or configure with
`-DC2_FIX_PLAYER_NAME_PADDING=OFF`, to restore shipped behavior.

## Reconstruction baseline

Clean-room source reconstruction and supporting tools for Caesar II (1995), a
32-bit DOS/4GW game built with Watcom C. The current rebuild is byte-exact
outside generated debug information; the original debug trailer is attached
only after the rebuilt non-debug image has passed the strict comparison.

## Prerequisites

- [Nix](https://nixos.org/) with flakes (the dev shell provides Python and
  uv; enter it with `nix develop`, or `direnv allow` once for automatic
  activation)
- [podman](https://podman.io/) — the Watcom compiler and linker run inside a
  container, not in the shell. The image is public and pulled on first use:
  `ghcr.io/second-impressions/watcom-10.0a-wibo`, built and verified by
  [second-impressions/watcom-compilers](https://github.com/second-impressions/watcom-compilers).
  Set `C2_WATCOM_IMAGE` to point at a different or locally built image.

## ISO Sources

All ISOs held in this repository are sourced from:
https://archive.org/details/20231129_20231129_0828

## Quick Start

```bash
# Enter the dev shell (or let direnv do it: direnv allow)
nix develop

# Install the pinned Python toolchain, including the Watcom-aware reccmp fork
uv sync

# Supply the original PS.EXE (downloads a CD image from archive.org and
# extracts it to original/PS.EXE — see "Getting the original PS.EXE" below
# for manual options), then validate it and configure reccmp
uv run c2 fetch-original
uv run c2 reccmp prepare
# If you also have the closest Windows source witness (build A):
uv run c2 reccmp prepare --windows-original original/CAESAR2.EXE

# Build the runnable game and publish the separate pre-bind analysis image
uv run c2 rebuild

# Whole-image function and initialized-data reports
uv run c2 reccmp code --html build/reccmp.html --json build/reccmp.json
uv run c2 reccmp data
```

The original executables, generated binaries, and machine-local reccmp
configs are intentionally untracked.  The target hash is pinned in
`reccmp-project.yml`; `c2 reccmp prepare` validates the local original
against it.  Compare functions/data against the pre-bind
`build/PS.reccmp.EXE` — never the runnable `build/PS.EXE`, which carries
the original's grafted debug trailer.

Function annotations use the reccmp target ids `C2` (DOS) and `C2WIN`
(Windows build A).  `C2WIN` is an original-binary/source-location target: the
repository does not produce a complete Windows rebuild or PDB, so the normal
code and data reports remain targeted at `C2`.

## CLI Commands

The toolkit is deliberately small — build the binary and verify it:

```
c2 fetch-original                  # Supply original/PS.EXE from archive.org
c2 rebuild                         # Link and bind the runnable reconstruction
c2 reccmp prepare                  # Validate the local original and configure reports
c2 reccmp code                     # Function alignment/accuracy report
c2 reccmp data                     # Initialized-data and relocation report
c2 delink --list                   # Recover third-party OMF objects from PS.EXE
```

(Build metadata — `.c2-cache/symbols.json` — is derived from the original
automatically whenever `rebuild`/`delink` find it missing or stale.)

(The burn-down era's diagnostic tooling — per-function byte oracle, regalloc
trace machinery, game-asset and CD/runtime helpers — was retired once the
reconstruction reached byte-exact; it lives in git history, 2026-07-15.)

## Getting the original PS.EXE

The reconstruction's ground truth is the **debug-symbol build** of `PS.EXE`
(SHA-256
`4a41f68d0c322785d9a174d4728c3095ab5c6e0d24624af2d3ce67540d8eca5c`,
1,304,734 bytes).  It is copyrighted and therefore **not tracked**: every
command that needs it expects it at the git-excluded path **`original/PS.EXE`**,
complains with instructions when it is absent, and refuses to run when the
file does not match the pinned hash (escape hatch:
`C2_ALLOW_ORIGINAL_MISMATCH=1`).  The authoritative hash lives in
`reccmp-project.yml`.

### Automatic (recommended)

```bash
uv run c2 fetch-original                # ~132 MiB download
```

This downloads a CD image from the [Impressions Games PC CD Image
Collection](https://archive.org/details/20231129_20231129_0828) on
archive.org (default: the smallest carrier, the Germany 1996-12-18
rerelease), verifies the zip against its archive.org MD5, converts the
BIN/CUE image on the fly, extracts `HD/PS.EXE` from the ISO9660
filesystem, verifies its SHA-256, and installs it at `original/PS.EXE`.
Nothing but the final 1.3 MB file is kept.  `--cd` picks another release,
`--from-zip` reuses an already-downloaded CD zip.

### Manual

Download any of these CD images from the
[collection](https://archive.org/details/20231129_20231129_0828), extract
`HD/PS.EXE` from the CD filesystem yourself, and place it at
`original/PS.EXE`:

| CD zip in the archive.org item | size | zip MD5 |
|---|---|---|
| [Caesar II (Germany) (Rerelease) (1996-12-18).zip](https://archive.org/download/20231129_20231129_0828/Caesar%20II%20%28Germany%29%20%28Rerelease%29%20%281996-12-18%29.zip) | 132,189,993 | `b9f55ea4d2f6e5aec2e49be96ed6be25` |
| Caesar II (Germany) (Rerelease) (1996-12-18) (Alt).zip | 132,190,010 | `7b758c0f9757039e0751cfeb6062ef8b` |
| Caesar II (USA) (Rerelease) (1997-11-12).zip | 359,348,782 | `9f9ea78b83f67546352915489c4a9e93` |
| Caesar II (USA) (Rerelease) (1996-08-29).zip | 424,795,362 | `5dd30aec3f2cb67f94441ab09180ad0d` |
| Caesar II (USA) (Rerelease) (1997-03-10).zip | 427,346,354 | `b0a5c283dc181460897c8ad31c82f13c` |
| Caesar II (Europe) (Rerelease) (1997-09-12).zip | 427,487,808 | `dfdfc4158f57ae48c5f0a54fee4bd856` |
| Caesar II (Italy) (Covermount).zip | 435,086,930 | `ee4d7d6fd3a980bf92ac6dab1500649e` |

(The other Caesar II releases in the collection — Europe/France/Germany
originals, OEMs, the 1995-10-06 USA rerelease — ship earlier, non-debug
builds of PS.EXE and will be rejected by the hash check.)

## Port source policy

Byte equality is not a requirement in this repository.  The reconstructed DOS
program remains a behavioral and historical reference, but the port may change
recovered code for portability, bug fixes, maintainability, and new features.

Keep inherited files and functions structurally close where that makes future
changes from `caesar2-reconstruction` easy to cherry-pick.  This is a practical
merge policy, not a source freeze: prefer narrow platform interfaces and small
commits, but change engine code directly when the portable design genuinely
benefits.  Port changes are not forwarded back to the byte-exact
reconstruction.

Target differences are expressed through `include/c2_target.h`
(`PLATFORM_DOS`, `PLATFORM_WINDOWS`, and `PORT_PLATFORM`) or through a
named capability—not through raw compiler macros.

## Running the game

`c2 rebuild` produces a self-contained `build/PS.EXE`. Install the game
assets from a CD (copy the CD's `HD/` tree plus the media directories
`xmi/`, `smk/`, `raw/`, `pl8/` into an install directory), drop the rebuilt
`PS.EXE` next to them, and run it in any DOS emulator (e.g. DOSBox-X,
which also offers a GDB remote stub for attaching a debugger to the live
DOS process).  A display-free smoke test that proves DOS/4GW + CRT startup
+ the recovered `main()`:

```bash
podman run --rm -v "$PWD/install/caesar2:/src" \
    ghcr.io/second-impressions/watcom-10.0a-dosemu2 \
    PSREBLD.EXE   # expect the CD-check prompt
```
