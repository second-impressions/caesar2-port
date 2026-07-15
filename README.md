# Caesar II Reconstruction

Clean-room source reconstruction and supporting tools for Caesar II (1995), a
32-bit DOS/4GW game built with Watcom C. The current rebuild is byte-exact
outside generated debug information; the original debug trailer is attached
only after the rebuilt non-debug image has passed the strict comparison.

## Prerequisites

- [devenv](https://devenv.sh/) (provides Python, uv, Open Watcom, Wine, DOSBox-X, etc.)

## ISO Sources

All ISOs held in this repository are sourced from:
https://archive.org/details/20231129_20231129_0828

## Quick Start

```bash
# Enter the devenv shell
devenv shell

# Install the pinned Python toolchain, including the Watcom-aware reccmp fork
uv sync

# Supply the original PS.EXE (downloads a CD image from archive.org and
# extracts it — see "Getting the original PS.EXE" below for manual options),
# then validate it and configure reccmp
uv run c2 fetch-original
uv run c2 reccmp prepare

# Build the runnable game and publish the separate pre-bind analysis image
uv run c2 rebuild

# Whole-image function and initialized-data reports
uv run c2 reccmp code --html build/reccmp.html --json build/reccmp.json
uv run c2 reccmp data
```

The original executable, generated binaries, and machine-local reccmp
configs are intentionally untracked.  The target hash is pinned in
`reccmp-project.yml`; `c2 reccmp prepare` validates the local original
against it.  Compare functions/data against the pre-bind
`build/PS.reccmp.EXE` — never the runnable `build/PS.EXE`, which carries
the original's grafted debug trailer.

## CLI Commands

The toolkit is deliberately small — build the binary and verify it:

```
c2 export data/PS.EXE              # Parse EXE, write data/out/symbols.json
c2 export data/PS.EXE --symbols    # Also print full symbol listing
c2 delink --list                   # Recover third-party OMF objects from PS.EXE
c2 rebuild                         # Link and bind the runnable reconstruction
c2 reccmp prepare                  # Validate the local original and configure reports
c2 reccmp code                     # Function alignment/accuracy report
c2 reccmp data                     # Initialized-data and relocation report
```

(The burn-down era's diagnostic tooling — per-function byte oracle, regalloc
trace machinery, game-asset and CD/runtime helpers — was retired once the
reconstruction reached byte-exact; it lives in git history, 2026-07-15.)

## Getting the original PS.EXE

The reconstruction's ground truth is the **debug-symbol build** of `PS.EXE`
(SHA-256
`4a41f68d0c322785d9a174d4728c3095ab5c6e0d24624af2d3ce67540d8eca5c`,
1,304,734 bytes).  It is copyrighted and therefore **not tracked**: every
command that needs it expects it at the git-excluded path **`data/PS.EXE`**,
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
filesystem, verifies its SHA-256, and installs it at `data/PS.EXE`.
Nothing but the final 1.3 MB file is kept.  `--cd` picks another release,
`--from-zip` reuses an already-downloaded CD zip.

### Manual

Download any of these CD images from the
[collection](https://archive.org/details/20231129_20231129_0828), extract
`HD/PS.EXE` from the CD filesystem yourself, and place it at
`data/PS.EXE`:

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

## Running the game

`c2 rebuild` produces a self-contained `build/PS.EXE`. Install the game
assets from a CD (copy the CD's `HD/` tree plus the media directories
`xmi/`, `smk/`, `raw/`, `pl8/` into an install directory), drop the rebuilt
`PS.EXE` next to them, and run it in DOSBox-X. A display-free smoke test
that proves DOS/4GW + CRT startup + the recovered `main()`:

```bash
podman run --rm -v "$PWD/install/caesar2:/src" \
    localhost/watcom-10.0a-dosemu2 PSREBLD.EXE   # expect the CD-check prompt
```

DOSBox-X has a built-in GDB remote stub (`gdbserver` machine option) for
attaching a debugger to the live DOS process.
