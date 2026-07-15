# reccmp workflow for the Caesar II reconstruction

This repository pins the Second Impressions Watcom branch of reccmp and wraps
its stock reports with `c2 reccmp`. The integration deliberately keeps project
metadata in Git while keeping copyrighted inputs and generated binaries local.

## Artifact boundary

Tracked:

- `reccmp-project.yml`: target ID, compiler, source roots, and the expected
  SHA-256 of the original executable.
- `reccmp-user.example.yml`: documentation for the machine-local input file.
- `uv.lock`: the exact reccmp revision and Python dependency graph.

Ignored and generated:

- `data/PS.EXE`: the exact original debug build, supplied by the user.
- `reccmp-user.yml`: original-binary discovery, written by `prepare`.
- `build/PS.EXE`: the runnable DOS/4GW-bound reconstruction.
- `build/PS.reccmp.EXE`: the pre-bind linker image used for reccmp analysis.
- `build/PS.reccmp.map`: the matching wlink symbol map.
- `reccmp-build.yml`: build-artifact discovery, written by `rebuild`.

The analysis and runnable executables must remain distinct. Once the complete
non-debug image matches PS, `c2 rebuild` grafts the original Watcom debug
trailer onto the runnable `build/PS.EXE`. That makes the final file runnable
and byte-exact, but its debug addresses no longer independently describe what
the reconstruction compiler and linker emitted. reccmp therefore consumes the
generated-debug pre-bind image and its map.

## Setup and normal use

```bash
uv sync
cp /path/to/PS.EXE data/PS.EXE
uv run c2 reccmp prepare
uv run c2 rebuild
uv run c2 reccmp code
uv run c2 reccmp data
```

`prepare` rejects any input whose SHA-256 differs from the hash in
`reccmp-project.yml`. `rebuild` publishes the analysis pair and refreshes
`reccmp-build.yml` by default; use `--no-reccmp` only when no report will be
run from that build.

The `code` and `data` subcommands pass all additional arguments to reccmp's
stock `asmcmp` and `datacmp` modules. Useful examples:

```bash
uv run c2 reccmp code --no-color
uv run c2 reccmp code --html build/reccmp.html
uv run c2 reccmp code --json build/reccmp.json --json-diet --silent
uv run c2 reccmp code --verbose 13186 --print-rec-addr
uv run c2 reccmp data --no-color
```

Run `uv run c2 reccmp code --help` or `data --help` to see the native reccmp
options. The wrapper checks that all three project files exist before starting
the report.

## What the reports mean

The function report aligns original and reconstructed Watcom symbols using
embedded debug identities, source modules, annotations, and the linker map. It
reports both instruction-normalized similarity and stricter reconstruction
signals added for this project:

- raw bytes and raw-byte ratio;
- normalized instruction identity;
- effective entropy ratio;
- relocation-site and relocation-target identity;
- explicit per-function relocation defects.

The data report compares initialized storage, BSS state, pointer relocation
sites, and relocation targets. Embedded Watcom debug extents take precedence
over public-map gap estimates because a linker map can omit private symbols.

reccmp is the broad, navigable reporting layer; it is not a replacement for
the reconstruction's strict oracle. `c2 decomp-verify` without `--no-strict`
still performs the authentic final link and rejects non-debug code, data,
layout, or loader-relocation differences. The debug trailer is intentionally
outside source-byte matching and is grafted only after the pre-debug image is
exact.

## Expected local noise and diagnosis

Some recovered files contain repeated historical annotations for the same
address. reccmp reports these as dropped duplicate annotations; the compiler
debug and map identities remain the authoritative alignment inputs.

The current pre-bind reference result is 2231 of 2234 functions aligned at
100% accuracy and 1578 data symbols with no issues. The three identity misses
are tracked in `TODO.md`: the known `sound_error_` alias placement and two
same-named private Miles functions whose reconstructed module names lack the
original `.c` suffix. They are deliberately left ambiguous instead of being
paired by an unsupported guess.

If a report appears to inspect the grafted runnable file, delete
`reccmp-build.yml` and rerun `uv run c2 rebuild`. The reconstructed target in
that file should point to `build/PS.reccmp.EXE`, never `build/PS.EXE`.

If setup rejects the original, do not change the tracked hash to accommodate a
different release. Locate the debug build identified in the README instead.
