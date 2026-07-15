# Caesar II Reconstruction

Clean-room source reconstruction and supporting tools for Caesar II (1995), a
32-bit DOS/4GW game built with Watcom C. The current rebuild is byte-exact
outside generated debug information; the original debug trailer is attached
only after the rebuilt non-debug image has passed the strict comparison.

## Prerequisites

- [devenv](https://devenv.sh/) (provides Python, uv, Java, Open Watcom, Wine, DOSBox-X, etc.)
- [Ghidra](https://ghidra-sre.org/) with the ghidra-lx-loader extension installed

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

# Build (or rebuild) the Ghidra project headlessly, reproducibly:
scripts/rebuild-ghidra.sh          # imports PS.EXE + runs ImportCaesar2.java
# ...or in the Ghidra GUI: import with the LE loader, run
# ghidra_scripts/ImportCaesar2.java
```

The Ghidra DB is a disposable, fully-reconstructable artifact (gitignored).
`scripts/rebuild-ghidra.sh` is the single source of truth for how it is
built; re-run it any time the DB is missing or stale.

The original executable, generated binaries, and machine-local reccmp configs
are intentionally untracked. See [docs/reccmp-workflow.md](docs/reccmp-workflow.md)
for artifact boundaries, report semantics, and troubleshooting.

## CLI Commands

```
c2 export data/PS.EXE              # Parse EXE, write data/out/symbols.json
c2 rebuild                         # Link and bind the runnable reconstruction
c2 reccmp prepare                  # Validate the local original and configure reports
c2 reccmp code                     # Function alignment/accuracy report
c2 reccmp data                     # Initialized-data and relocation report
c2 export data/PS.EXE --symbols    # Also print full symbol listing
c2 run                             # Launch game in DOSBox-X with GDB stub (port 1234)
c2 run --no-gdb                    # Launch without GDB stub
c2 run --cd path/to/cd-root        # Launch with CD mounted as D: (minimal install)
c2 cd unpack CDs/<name>.zip        # Unpack CD zip → extracted directory
c2 cd install <cd-root>            # Minimal install (HD/ tree only, CD needed at runtime)
c2 cd install --full <cd-root>     # Full install (copies all assets, no CD needed)
c2 cd hash CDs/extracted/<name>/   # Compute SHA256 hashes for a CD directory
c2 cd compare                      # Compare EXE versions across CD releases
c2 cd compare --file "HD/PS.EXE"   # Compare a specific file
```

## Static Analysis Workflow

1. **Extract symbols**: `c2 export data/PS.EXE`
   - Parses the DOS/4GW LE executable structure
   - Extracts Watcom Debug Info 3.0 (symbols, line numbers, modules)
   - Writes `data/out/symbols.json` for Ghidra import

2. **Import into Ghidra** (headless, reproducible):
   - `scripts/rebuild-ghidra.sh` — imports `data/PS.EXE` with the LE-Style
     DOS loader + `x86:LE:32:watcom` language and runs
     `ghidra_scripts/ImportCaesar2.java` as the post-script
   - The script reads `data/out/symbols.json` and `config/program_tree.jsonc`
   - GUI equivalent: import with the LX Loader, then run the script manually

3. **Customize Program Tree**:
   - Edit `config/program_tree.jsonc` to adjust subsystem groupings
   - Re-run `ImportCaesar2.java` to apply changes

## Runtime Debugging with Ghidra + DOSBox-X

DOSBox-X has a built-in GDB remote stub.  `c2 run` enables it by default on
port 1234, allowing Ghidra's debugger to attach to the live DOS process.

### Which CD to use

The `data/PS.EXE` in this repository is the **debug-symbol build**
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

### Setup: full install (no CD required at runtime)

```bash
# 1. Unpack a CD that contains the debug-symbol PS.EXE
c2 cd unpack "CDs/Caesar II (USA) (Rerelease) (1996-08-29).zip"

# 2. Full install — copies HD/ tree + all CD media assets (xmi/, smk/, raw/, pl8/)
c2 cd install --full "CDs/extracted/Caesar II (USA) (Rerelease) (1996-08-29)"

# 3. Launch with GDB stub (enabled by default, port 1234)
c2 run
```

### Setup: minimal install (CD mounted at runtime)

```bash
# 1. Unpack a CD
c2 cd unpack "CDs/Caesar II (USA) (Rerelease) (1996-08-29).zip"

# 2. Minimal install — HD/ tree only
c2 cd install "CDs/extracted/Caesar II (USA) (Rerelease) (1996-08-29)"

# 3. Launch with CD mounted as D: and GDB stub on port 1234
c2 run --cd "CDs/extracted/Caesar II (USA) (Rerelease) (1996-08-29)"
```

### Connecting Ghidra to the live process

1. In Ghidra open the project containing `PS.EXE`
2. Go to **Debugger → Connect → Remote GDB**
3. Set **host** = `localhost`, **port** = `1234`
4. Click **Connect** — DOSBox-X will resume execution
5. Set breakpoints, inspect memory, and step through code as normal

> **Tip**: Use `--no-gdb` if you just want to play the game without the
> debugger pausing at startup:
> ```bash
> c2 run --no-gdb
> ```

## CD Management

```bash
# Unpack a CD image
c2 cd unpack "CDs/Caesar II (Germany) (Rerelease) (1996-12-18).zip"

# Compute hashes for comparison
c2 cd hash CDs/extracted/

# Compare EXE versions across all CDs
c2 cd compare
c2 cd compare --file "HD/PS.EXE"
```
