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

# Supply the exact original locally, then validate it and configure reccmp
cp /path/to/debug-build/PS.EXE data/PS.EXE
uv run c2 reccmp prepare

# Build the runnable game and publish the separate pre-bind analysis image
uv run c2 rebuild

# Whole-image function and initialized-data reports
uv run c2 reccmp code --html build/reccmp.html --json build/reccmp.json
uv run c2 reccmp data
```

The original executable, generated binaries, and machine-local reccmp configs
are intentionally untracked. See [docs/reccmp-workflow.md](docs/reccmp-workflow.md)
for artifact boundaries, report semantics, and troubleshooting.

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

### Which CD to use

The `data/PS.EXE` this project reconstructs is the **debug-symbol build**
(SHA-256: `4a41f68d0c322785d9a174d4728c3095ab5c6e0d24624af2d3ce67540d8eca5c`).
It ships on the following CD releases:

| Release | CD zip |
|---------|--------|
| Caesar II (Europe) (Rerelease) (1997-09-12) | `CDs/Caesar II (Europe) (Rerelease) (1997-09-12).zip` |
| Caesar II (Germany) (Rerelease) (1996-12-18) | `CDs/Caesar II (Germany) (Rerelease) (1996-12-18).zip` |
| Caesar II (Germany) (Rerelease) (1996-12-18) (Alt) | `CDs/Caesar II (Germany) (Rerelease) (1996-12-18) (Alt).zip` |
| Caesar II (Italy) (Covermount) | `CDs/Caesar II (Italy) (Covermount).zip` |
| Caesar II (USA) (Rerelease) (1996-08-29) | `CDs/Caesar II (USA) (Rerelease) (1996-08-29).zip` |
| Caesar II (USA) (Rerelease) (1997-03-10) | `CDs/Caesar II (USA) (Rerelease) (1997-03-10).zip` |
| Caesar II (USA) (Rerelease) (1997-11-12) | `CDs/Caesar II (USA) (Rerelease) (1997-11-12).zip` |
