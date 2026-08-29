# Save-game round-trip testing

The port tests both halves of a save operation: the bytes that reach durable
storage and the state reconstructed from those bytes.

## Layers

### Canonical serializer unit test

`port-save` builds a complete 500-entry synthetic save registry, including the
portable figure and arrow pointer conversions and the separate 4,000-byte
history block. It verifies:

- the file has the exact 225,745-byte Caesar II save size;
- every ordinary state byte reaches its canonical file offset;
- figures and arrows use their original pointer-free disk layouts;
- history data occupies the final 4,000 bytes;
- loading reconstructs every registered byte and history byte;
- altered live state, altered save bytes, altered history, truncation, and
  trailing bytes are all detected.

Run it without copyrighted game data:

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --target c2-port-save-test
ctest --test-dir build -R '^port-save$' --output-on-failure
```

### Recovered-engine integration smoke

When original game data is available, `recovered-save-load-smoke` drives the
actual recovered UI and engine. The engine creates a save, then the port
reopens it and compares the complete canonical live registry and `history.dat`
against the file. The smoke changes state, loads through the recovered Load
window, repeats the full comparison, and finally checks stable gameplay fields
after the restarted game loop is running.

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

### Browser/OPFS integration smoke

The same engine smoke can run in Chromium or Firefox. In this form the save and
history file travel through WasmFS and OPFS, so the readback comparison tests
the browser persistence path rather than an in-memory substitute.

Build a Debug Wasm tree with test assets, serve it through the smoke harness,
and select the `save` test:

```sh
node tools/smoke-wasm.mjs build/wasm-debug save chromium
node tools/smoke-wasm.mjs build/wasm-debug save firefox
```

The browser test uses a new browser profile and waits for the same full-state
verification message. A console message or a visually successful load is not
sufficient to pass.

## What is compared

The readback verifier canonicalizes all entries in `savegame_entries` until its
terminator. This covers 221,745 bytes of game state. It then appends and checks
the 4,000-byte history block. Comparison is byte-for-byte and reports the first
mismatching file offset. The semantic smoke additionally tracks the province,
map position, zoom level, treasury, and other stable resumed-loop state.

The verifier does not advance the simulation or normalize values before the
comparison. Therefore it detects both incomplete writes and incomplete loads.
