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
  frame-publication, input, and browser scheduling; and
- [`docs/legacy-abi.md`](docs/legacy-abi.md) — packing, pointer width,
  signedness, serialization, and compiler semantics.

## Native Linux bootstrap

The native bootstrap presents both original publisher splashes and then enters
the recovered `Caesar II - Game Options` and `New Game Options` screens through
SDL3. It deliberately links recovered display, screen, control, and data
translation units, so this is a vertical engine-to-platform slice rather than
a replacement UI. The splashes advance after two seconds or on input. Escape
exits from the front screen and returns from the detailed game-options screen.

The original `INTRO.SMK` between the publisher splashes and front screen is
currently skipped. Loading games, tutorials, name entry, and starting the
simulation remain to be connected.

The recovered startup flow runs on an engine worker. The SDL main thread owns
events and presentation, communicating through the backend-neutral
`c2_host_*` API. Music and video are explicit unavailable host capabilities in
this milestone; no placeholder media libraries or false-success stubs are
linked.

Original game data is required and is never committed.  From the Nix
development shell:

```bash
nix develop
cmake --preset linux-debug
cmake --build --preset linux-debug
./build/port/linux-debug/caesar2 --data-dir /path/to/CAESAR2
```

Writable files use a separate user-data root, selected with
`--user-data-dir PATH` or `C2_USER_DATA_DIR` (default: the current directory).

The game-options screen supports Start New Game by mouse or Enter/Space. In the
detailed options, Left/Right changes difficulty, `P` toggles peaceful campaign
mode, and the Back row returns to the front screen. The visible Start This Game
action is the next unconnected startup boundary.

A display-free smoke test loads the same PL8, font, text, and palette files and
reports deterministic framebuffer hashes for the complete sequence:

```bash
./build/port/linux-debug/caesar2 --headless --data-dir /path/to/CAESAR2
```

Pass `--screenshot output.ppm` to write the final headless frame or the current
interactive startup state as a portable pixmap beneath the user-data root.

To register that smoke test with CTest, configure with
`-DC2_TEST_DATA_DIR=/path/to/CAESAR2` and run `ctest --preset linux-debug`.
The `linux-tsan` configure/build/test preset runs the same worker-thread slice
under Clang ThreadSanitizer.

## Reconstruction baseline

Clean-room source reconstruction and supporting tools for Caesar II (1995), a
32-bit DOS/4GW game built with Watcom C. The current rebuild is byte-exact
outside generated debug information; the original debug trailer is attached
only after the rebuilt non-debug image has passed the strict comparison.

## Prerequisites

- [Nix](https://nixos.org/) with flakes (the dev shell provides Python and
  uv; enter it with `nix develop`, or `direnv allow` once for automatic
  activation)
- [podman](https://podman.io/) with the `watcom-10.0a-wibo` toolchain image
  (the Watcom compiler/linker run inside it, not in the shell)

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
(`PLATFORM_DOS`, `PLATFORM_WINDOWS`, and `PLATFORM_PORTABLE`) or through a
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
    localhost/watcom-10.0a-dosemu2 PSREBLD.EXE   # expect the CD-check prompt
```
