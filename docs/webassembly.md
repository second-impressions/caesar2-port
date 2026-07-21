# WebAssembly port

## Architecture

The browser target is the portable SDL3 target compiled by Emscripten, not a
second game implementation. SDL application callbacks own the browser main
thread, event collection, and presentation. The recovered `c2.c` driver and
all engine/UI control flow run on the same engine worker used by native builds.
Frames, input, audio, movies, timing, assets, and user files cross the existing
`c2_host_*` boundary.

The build deliberately uses pthreads rather than Asyncify or a browser-only
state machine. Two workers are created before the runtime starts, so the
engine and SDL services never have to create a worker from inside a recovered
blocking path. The SDL callback returns to the browser on every iteration;
`requestAnimationFrame` supplies its cadence and no native sleep is performed
on the main thread.

The original C89 program has many calls to `void` functions without visible
cross-translation-unit declarations. Native x86 ABIs tolerate the implicit
`int` return type, but Wasm includes the return type in a function signature
and traps on a mismatch. `include/c2_wasm_implicit_void.h` supplies only those
missing return declarations to the Emscripten compile. Its empty parameter
lists retain C89 argument promotion and the recovered calling shape. This is a
target ABI adapter, not a duplicate engine API.

## Building

Initialize the pinned SDL, libsmacker, and libADLMIDI submodules and enter the
development shell:

```bash
git submodule update --init --recursive
nix develop
```

Package an installed Caesar II asset tree and build the release bundle:

```bash
emcmake cmake --preset wasm-release \
  -DC2_WASM_ASSET_ROOT=/path/to/CAESAR2
cmake --build --preset wasm-release
```

The output directory contains `caesar2.html`, JavaScript, Wasm, and the
generated asset data package. Original game assets remain local build inputs
and are never stored in this repository.

For assertions, semantic observations, and the recovered province-selection
smoke test:

```bash
emcmake cmake --preset wasm-debug \
  -DC2_WASM_ASSET_ROOT=/path/to/CAESAR2
cmake --build --preset wasm-debug
node tools/smoke-wasm.mjs build/port/wasm-debug
```

## Serving and deployment

Threaded Wasm requires a cross-origin-isolated page. The development server
sets `Cross-Origin-Opener-Policy: same-origin` and
`Cross-Origin-Embedder-Policy: require-corp`:

```bash
python3 tools/serve-wasm.py build/port/wasm-release
```

A production host must serve the same headers for the HTML, JavaScript, Wasm,
worker, and asset data files. It should also serve `.wasm` as
`application/wasm`. Opening the HTML directly from disk cannot satisfy this
contract.

The bundle exposes the immutable packaged tree as `/assets`. SDL mounts
IDBFS-backed `/user-data` before `SDL_AppInit`, and `SDL_GetPrefPath` selects
that path for saves, `caesar2.inf`, history, and screenshots. SDL's persistent
path support performs the initial synchronization and automatically flushes
changes, so the recovered synchronous file operations remain on the engine
worker.

The default pointer remains free so windowed play does not unexpectedly trap
the browser cursor. Add `?mouse-lock=1` to request Pointer Lock; when browser
policy requires a user gesture, the backend retries on the next click. Debug
bundles accept `?smoke-test=province` for automated semantic verification.

## Deliberate constraints

- This is currently a threaded Wasm product and therefore requires browser
  support for `SharedArrayBuffer` plus the isolation headers above.
- Original assets are packaged at link time. Streaming or separately hosted
  asset delivery can be added below the same asset service later.
- The native and browser builds share engine, UI, media, save, and SDL host
  implementations. A browser-only replacement screen or control loop would
  violate the platform boundary.
