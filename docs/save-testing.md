# Save-game round-trip testing

The port tests both halves of a save operation: the bytes that reach durable
storage and the state reconstructed from those bytes. The format itself is
specified in [`docs/save-format.md`](save-format.md).

## Layers

### Format core unit test

`port-save` (`tests/c2_port_save_test.c`) exercises the engine-independent
core with synthetic state: a registry shaped like the real one, blocks the
core classifies by address, and images it builds directly. It verifies:

- a container round trip is lossless, including walker indices above 255;
- a reader with a smaller walker pool keeps the first records, drops the
  rest, and clears every reference to a dropped walker;
- an original-layout file imports into the same image: scalars in registry
  order, stale tile occupancy dropped, envoys lifted out of the cell byte,
  narrow targets widened, pointer markers removed with their one useful bit
  kept, and a wrapped history ring linearised oldest-first;
- importing an original file, saving, and loading yields the imported state;
- truncation, a flipped bit, a forged CRC over a damaged container, a wrong
  identifier, a non-save and a future format version are all refused, each
  with the expected status;
- every reject rule refuses and every clear rule zeroes and counts.

`save-compat` pins the original-layout constants and, when
`C2_TEST_SAVE_FIXTURE` names an original 225,745-byte save, that the file is
detected as version 0. `test_save_schema.py` checks the generated accessors
match the schema when `flatcc` is on the path.

Run them without copyrighted game data:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --target c2-port-save-test c2-save-compat-test
ctest --test-dir build -R '^(port-save|save-compat)$' --output-on-failure
```

### Recovered-engine integration smoke

When original game data is available, `recovered-save-load-smoke` drives the
actual recovered UI and engine. The engine creates a save, then the port
reopens it and compares the live state against the file. The smoke changes
state, loads through the recovered Load window, repeats the comparison, and
finally checks stable gameplay fields after the restarted game loop is
running.

```sh
cmake -S . -B build/save-smoke -DCMAKE_BUILD_TYPE=Debug \
  -DC2_TEST_DATA_DIR=/path/to/caesar2-data
cmake --build build/save-smoke
ctest --test-dir build/save-smoke -R '^recovered-save-load-smoke$' \
  --output-on-failure
```

A successful run prints:

```text
save/load disk and full-state verification restored 'c2smoke.sav'
```

Run it in both walker-index configurations before touching the adapter:
`-DPORT_FEAT_WIDE_CITIZEN_INDEX=OFF` compiles the recovered byte references
and the 200-slot pool.

### Browser/OPFS integration smoke

The same engine smoke can run in Chromium or Firefox. In this form the save
travels through WasmFS and OPFS, so the readback comparison tests the browser
persistence path rather than an in-memory substitute.

```sh
node tools/smoke-wasm.mjs build/port/wasm-debug save chromium /path/to/caesar2.iso
node tools/smoke-wasm.mjs build/port/wasm-debug save firefox /path/to/caesar2.iso
```

The browser test uses a new browser profile and waits for the same
verification message.

## What is compared

The verifier (`c2_port_save_state_file_matches`) no longer compares bytes. It
captures the live engine state into a staging image exactly as a save would,
loads the file into a second image through the normal decode-and-validate
path (whichever layout the file is in), and diffs the two part by part. On a
mismatch it names the first differing part -- `scalars`, `city_map`,
`envoys`, `citizens`, `history`, ... -- rather than a byte offset, since the
file has no fixed offsets.

Both images pass through the same normalisation, so derived state (tile
occupancy, the narrow target byte, the envoy byte on market cells) and
transient render bits that the engine leaves in cells are compared after
the rules the format applies, not raw. The verifier does not advance the
simulation. It therefore detects both an incomplete write and an incomplete
load, and it also detects a translation asymmetry between `capture` and
`commit`, which byte comparison could not.
