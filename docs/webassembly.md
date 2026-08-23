# WebAssembly port

## Architecture

The browser target is selected by `PORT_PLATFORM_WASM` and compiled by Emscripten;
`PORT_PLATFORM` remains the derived family shared with `PORT_PLATFORM_LINUX`,
not a target of its own. This is not a second game implementation. SDL
application callbacks own the browser main
thread, event collection, and presentation. The recovered `c2.c` driver and
all engine/UI control flow run on the same engine worker used by native builds.
Frames, input, audio, movies, timing, assets, and user files cross the existing
`c2_host_*` boundary.

The threaded build uses a fixed 96 MiB WebAssembly memory. The recovered game
fit in 64 MiB; integrated WasmFS startup peaks slightly above 71 MiB, so OPFS
uses a larger fixed reservation without enabling growable shared memory. Growable shared
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

Build a release runtime without bundled copyrighted data:

```bash
emcmake cmake --preset wasm-release -B build/port/wasm-release
cmake --build build/port/wasm-release
```

On first visit the page accepts an installation folder, ZIP, optimized
`.c2assets` pack, ISO, or BIN/CUE pair. It imports and validates data into
OPFS before starting the game. `C2_WASM_ASSET_ROOT` remains available for
self-hosted/demo bundles; the page offers **Use bundled game data** for those
builds. A multi-profile `.c2assets` pack can carry all text/speech languages
and DOS, Win95, Mac, or custom video sets in one deduplicated container.

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
node tools/smoke-wasm.mjs build/port/wasm-debug-en contextmenu firefox
node tools/smoke-wasm.mjs build/port/wasm-debug-en canvas firefox
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

A production host should serve the same isolation headers for the HTML,
JavaScript, Wasm, worker, and asset files, and serve `.wasm` as
`application/wasm`. GitHub Pages cannot configure COOP/COEP directly, so the
published build registers `coi-serviceworker.js`; the first visit reloads once
under that worker and subsequent responses are cross-origin isolated. Opening
the HTML directly from disk cannot satisfy this contract.

A storage pthread mounts one WasmFS OPFS backend before SDL host startup.
Imported assets/cache live below `/persistent/game-data`; mutable files live
below `/persistent/user-data`. Saves, `history.dat`, `caesar2.inf`, and
screenshots survive reload without mirroring assets into the Wasm heap. The
page can export individual saves/history/settings or a local store-only ZIP,
and game-data deletion is deliberately separate from save deletion.

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
The document suppresses the browser context menu at capture time so right
click remains an ordinary game input in Firefox as well as Chromium.

The browser main thread services input and the published-frame mailbox at
120 Hz while the canvas has focus and contains the physical pointer, matching
the native host's interactive cadence. It reduces SDL's runtime-changeable
callback-rate hint to 15 Hz after the pointer leaves or focus is lost, then
restores 120 Hz on re-entry. The recovered engine remains paced independently
at 60 Hz; this changes only event pumping and presentation latency, not game
time.

The canvas remains programmatically focusable for keyboard input, but browser
selection, dragging, tap highlighting, and the default focus outline are
disabled. Focus therefore stays functional without drawing a browser-owned
border over the game.

The recovered quit paths still end the game exactly as they do on DOS. Once
SDL reports a clean engine shutdown, the browser shell replaces the stopped
canvas with a Restart button. Restarting reloads the page to create a fresh
Emscripten runtime; the persistent `/user-data` mount retains saves and
settings across that reload. Runtime failures remain visible as errors rather
than being presented as an ordinary game exit.

## Deliberate constraints

- This is currently a threaded Wasm product and therefore requires browser
  support for `SharedArrayBuffer` plus the isolation headers above.
- Original data is user-supplied at runtime unless a distributor deliberately
  configures `C2_WASM_ASSET_ROOT`. Multi-profile packs select language, speech,
  and video before startup without rebuilding the Wasm executable.
- The native and browser builds share engine, UI, media, save, and SDL host
  implementations. A browser-only replacement screen or control loop would
  violate the platform boundary.
