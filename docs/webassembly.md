# WebAssembly port

## Architecture

The browser target is selected by `PLATFORM_WASM` and compiled by Emscripten;
`PLATFORM_PORTABLE` remains the derived family shared with `PLATFORM_LINUX`,
not a target of its own. This is not a second game implementation. SDL
application callbacks own the browser main
thread, event collection, and presentation. The recovered `c2.c` driver and
all engine/UI control flow run on the same engine worker used by native builds.
Frames, input, audio, movies, timing, assets, and user files cross the existing
`c2_host_*` boundary.

The threaded build uses a fixed 64 MiB WebAssembly memory. Growable shared
memory exposes resizable typed-array views to JavaScript; WebGL upload APIs do
not accept those views, which can leave SDL renderer geometry stale and show
pieces of earlier sprites in later frames. The recovered game and its
dynamically loaded graphics fit comfortably in the fixed heap; immutable
packaged assets remain in the preload filesystem rather than being retained
as one heap allocation.

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

Package one installed Caesar II language release and build its release bundle:

```bash
emcmake cmake --preset wasm-release \
  -B build/port/wasm-release-en \
  -DC2_LANGUAGE=en \
  -DC2_WASM_ASSET_ROOT=/path/to/CAESAR2
cmake --build build/port/wasm-release-en
```

The output directory contains `caesar2-en.html`, JavaScript, Wasm, and the
generated English asset data package. Configure `de`, `fr`, and `es` in
separate build directories with their corresponding complete localized asset
trees. This keeps localized text, RAW voices, and movies in separate downloads.
Original game assets remain local build inputs and are never stored in this
repository. See [localization.md](localization.md).

For assertions, semantic observations, and the recovered province-selection
smoke test:

```bash
emcmake cmake --preset wasm-debug \
  -B build/port/wasm-debug-en \
  -DC2_LANGUAGE=en \
  -DC2_WASM_ASSET_ROOT=/path/to/CAESAR2
cmake --build build/port/wasm-debug-en
node tools/smoke-wasm.mjs build/port/wasm-debug-en
node tools/smoke-wasm.mjs build/port/wasm-debug-en city
node tools/smoke-wasm.mjs build/port/wasm-debug-en music
node tools/smoke-wasm.mjs build/port/wasm-debug-en campania firefox
```

## Serving and deployment

Threaded Wasm requires a cross-origin-isolated page. The development server
sets `Cross-Origin-Opener-Policy: same-origin` and
`Cross-Origin-Embedder-Policy: require-corp`:

```bash
python3 tools/serve-wasm.py build/port/wasm-release-en
```

For testing from another machine, use HTTPS so the threaded runtime remains a
secure context. The server accepts an existing certificate and private key:

```bash
python3 tools/serve-wasm.py build/port/wasm-release-en \
  --bind 0.0.0.0 --port 8444 \
  --certfile /path/to/fullchain.pem --keyfile /path/to/key.pem
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

## Pixel-exact presentation

The browser canvas uses a high-pixel-density SDL window and integer logical
presentation. Its CSS size is chosen from `devicePixelRatio`, including browser
zoom, so the 640×480 game image occupies an exact whole-number multiple in the
canvas backing store. Any unavoidable remainder is black letterboxing rather
than fractional resampling. CSS custom properties marked `!important` retain
the chosen display size when Emscripten updates the canvas backing dimensions.

This distinction is load-bearing: a 640×480 CSS rectangle is not necessarily a
640×480 physical render target. Validation covers fractional display densities
as well as ordinary 1× and 2× displays.

The default pointer remains free so windowed play does not unexpectedly trap
the browser cursor. Add `?mouse-lock=1` to request Pointer Lock; when browser
policy requires a user gesture, the backend retries on the next click. Debug
bundles accept `?smoke-test=province` for automated semantic verification.

The browser main thread services input and the published-frame mailbox at
120 Hz, matching the native host's roughly 8 ms service interval. The
recovered engine remains paced independently at 60 Hz; the faster host
callback only reduces the time between a browser pointer event, engine input
publication, and pickup of the next completed cursor-bearing frame.

## Deliberate constraints

- This is currently a threaded Wasm product and therefore requires browser
  support for `SharedArrayBuffer` plus the isolation headers above.
- One complete localized asset tree is packaged at link time. Languages are
  separate artifacts so a browser downloads only its selected text, speech,
  and media.
- The native and browser builds share engine, UI, media, save, and SDL host
  implementations. A browser-only replacement screen or control loop would
  violate the platform boundary.
