# User-supplied game data and durable WebAssembly storage

## Scope

The portable build should accept:

- an installed Caesar II directory;
- a ZIP containing an installed directory or optimized asset pack;
- a plain ISO-9660 image; and
- a single-track BIN/CUE image through a MODE1/2352 or MODE2/2352 adapter.

An already-installed GOG copy is an ordinary installation directory. Importing a GOG installer is explicitly out of scope; users can install or unpack it first.

The WebAssembly product must additionally provide:

1. durable local saves and history;
2. clickable save export;
3. durable imported assets, so source selection is normally one-time;
4. a page-owned mechanism to replace/switch the active data source; and
5. an optimized pack format which can contain one or many languages, replaceable speech and video sets, and only the runtime files selected by its manifest.

Measured feasibility and corpus results are in `game-data-feasibility-results.md`.

## Decisions from the feasibility work

- Keep recovered engine file calls unchanged behind `c2_host_asset_read`.
- Migrate the browser from IDBFS to WasmFS OPFS for both assets and mutable data.
- Use reduced libarchive for ZIP only.
- Implement the ISO-9660 reader in-tree over a 2048-byte sector callback.
- Feed BIN/CUE through the already-proven 2352-to-2048-byte MODE1/MODE2 adapter.
- Stage and validate imports transactionally before changing the active generation.
- Store imported objects by content hash so language/media profiles share identical data.
- Expose the importer through a C ABI; its project-owned implementation may be C, Rust, or C++.
- Keep Mac-sized media and future replacements out of the fixed game heap. Integrated WasmFS startup requires a 96 MiB reservation; asset sizes and offsets remain 64-bit throughout.

## Augustus reference model

Research used Augustus commit `974f7e529bdf19059c16f0e3021f7a73b5af3b6b`.

Useful behavior:

- native startup tries explicit/current/executable/saved paths, then a picker;
- selected data is validated by parsing required language files;
- the browser delays `main` until a folder or ZIP has been imported; and
- the same game entry point then runs against a normalized root.

The Caesar II implementation should not copy Augustus literally:

- Augustus is AGPL-3.0;
- it clears old browser data before validating the replacement;
- it places assets and saves in one IDBFS tree;
- it relies heavily on non-standard `webkitdirectory` APIs; and
- its large growable heap makes copying the installation into MEMFS tolerable.

Caesar II retains separate asset/user namespaces, standard picker fallbacks, transactional generations, and a fixed 96 MiB game heap. The original 64 MiB build peaked above its reservation after WasmFS integration; fixed 96 MiB passed while imported data remained outside the heap.

## Runtime architecture

```text
native SDL / browser page
        |
        v
source acquisition
(directory, ZIP, ISO, BIN+CUE, optimized pack)
        |
        v
importer catalog + layout/profile detector
        |
        v
path, quota and archive validation
        |
        v
transactional object import / direct native directory view
        |
        v
active manifest and logical-path index
        |
        v
c2_host_asset_read(logical path, offset, size)
        |
        v
existing recovered readfile/media code
```

The game never receives archive paths, CD drives, browser handles, language directories, or object hashes. It sees the same canonical names as today.

### Importer ABI

Use a narrow ABI with caller-owned buffers and explicit 64-bit values:

```c
struct c2_source_reader {
    void *userdata;
    uint64_t size;
    int (*read_at)(void *userdata, uint64_t offset,
                   void *buffer, size_t size, size_t *read_out);
};

struct c2_import_options;
struct c2_import_report;

int c2_import_probe(const struct c2_source_reader *,
                    struct c2_import_report *);
int c2_import_stage(const struct c2_source_reader *,
                    const struct c2_import_options *,
                    c2_import_progress_fn, void *userdata);
int c2_import_commit(const char *staged_generation);
```

Directory acquisition additionally supplies bounded entry enumeration and entry readers. No allocator, exception, C++ object, Rust object, or browser handle crosses the ABI.

### Active asset view

At startup, build an immutable mapping:

```text
ASCII-folded logical path -> object/source handle + size + hash
```

Lookups preserve the recovered precedence:

1. base/root assets;
2. only the media group selected by extension (`pl8`, `raw`, `xmi`, `smk`).

Reject duplicate folded keys instead of choosing one nondeterministically. Normalize `\\` to `/`; reject NUL, invalid UTF-8, absolute/drive/UNC names, `.`/`..`, links, devices, and paths outside the source root.

The current `c2_host_asset_read` remains the compatibility operation. Add asset `stat/size` and opaque stream operations so whole-file loaders allocate exactly once and large media need not be repeatedly reopened.

## Browser storage

### OPFS layout

Use one WasmFS OPFS backend created from a storage pthread before SDL or the engine starts:

```text
OPFS root
└── caesar2-v1/
    ├── game-data/
    │   ├── objects/
    │   │   └── sha256-prefix/hash...
    │   ├── manifests/
    │   │   └── generation-id.json
    │   ├── staging/
    │   │   └── import-id/...
    │   └── active.json
    └── user-data/
        ├── *.sav
        ├── history.dat
        ├── caesar2.inf
        └── shot*.png
```

The isolated OPFS probe stored an 80 MiB object plus save/history files across reload and browser restart in Chromium and Firefox without changing its 67,108,864-byte heap. The integrated SDL/game build reserves a fixed 96 MiB because WasmFS startup pushed total game memory slightly above 71 MiB.

Emscripten cannot link the current `idbfs.js` persistence mode together with WasmFS. Remove `SDL_EMSCRIPTEN_PERSISTENT_PATH`, enable `-sWASMFS`, create/mount OPFS from a worker, and pass OPFS-backed roots to the SDL host.

Call `navigator.storage.persist()` after a user gesture and report whether it was granted. OPFS remains browser-managed if denied; the UI must not imply that best-effort storage is guaranteed forever.

### Transactional generations

Do not depend on atomic directory rename; Emscripten's OPFS backend does not currently support all directory moves.

- Write objects and a candidate manifest under a new generation ID.
- Validate every selected profile against those objects.
- Mark the generation complete.
- Replace only the small `active.json` pointer.
- Keep the previous complete generation until activation succeeds.
- Garbage-collect unreachable objects/generations later and only outside gameplay.

Content-addressed objects allow a new import to reuse assets already present. Switching language/video profiles can often replace only `active.json` without copying any media.

## Durable user state and export

Persist the entire user-data namespace, not just one filename. Resume-critical/exportable files are:

- every valid `*.sav`, including `caesar2.sav` and `lastyear.sav`;
- `history.dat`; and
- optionally `caesar2.inf` for preferences/career continuity.

A `.sav` already carries a 4,000-byte history tail, but the game also maintains `history.dat`; export both.

### Write durability

- Close and `fsync`/flush successful save writes before the engine reports completion.
- Serialize host writes and export snapshots with the existing user-data mutex boundary.
- Show a small “saved locally”/storage status outside the game canvas.
- Flush on orderly quit and page visibility changes, but do not rely on `beforeunload` for correctness.

OPFS writes do not need IDBFS `syncfs` copies.

### Browser export UI

The page should always expose a small **Export saves** control. Export can occur from the landing screen or from a toolbar which briefly snapshots the user namespace under a lock.

Current behavior:

- **Export** immediately downloads one store-only `caesar2-user-data.zip`;
- the archive includes all `.sav` files, `history.dat`, and `caesar2.inf`;
- no intermediate list of individual download links or settings checkbox is shown;
- generated Blob URLs are revoked after the download starts; and
- the exported ZIP can be imported directly through the same tab.

Do not fetch JSZip or other code from a CDN. The project-owned ZIP writer and
reader enforce the strict save, history, settings, filename, and decompression
limits on round trip.

## Browser source selection and switching

### Startup state machine

```text
STORAGE_INIT
  -> ACTIVE_SOURCE_CHECK
  -> SOURCE_REQUIRED | READY_TO_PLAY
  -> IMPORTING
  -> VALIDATING
  -> READY_TO_PLAY
  -> ENGINE_RUNNING
  -> ENGINE_STOPPED
```

The HTML page owns this state. Do not start the SDL engine thread until OPFS is mounted and an active manifest validates.

### Input mechanisms

Support, in order:

1. `showDirectoryPicker()` with persisted handle/permission recheck;
2. `<input webkitdirectory multiple>` fallback;
3. file input/drag-drop for ZIP, ISO, BIN, and CUE; and
4. optimized `.c2assets` packs.

For BIN/CUE, require both files in one selection/drop unless a browser directory handle supplies them. Parse one data track only and reject unsupported multisession/audio layouts explicitly.

### Page controls

When no source exists:

- **Choose installation folder**
- **Choose ZIP / ISO / BIN+CUE / asset pack**

When a valid source exists:

- **Play**
- **Change game data**
- **Choose language / speech / video profile** when available
- **Export saves**
- **Delete cached game data**
- **Delete saves/settings** as a separate, strongly confirmed action

Changing data while the engine runs requests a clean shutdown and returns to the page. Never hot-swap an active view beneath running game code. Import and validate the replacement while retaining the previous generation; activate it and reload only after success.

## Native source selection

Accept both a positional source and an explicit option:

```text
caesar2 [SOURCE]
caesar2 --game-data SOURCE
caesar2 --asset-root DIRECTORY   # compatibility alias
```

Try:

1. explicit source;
2. saved active source/cache;
3. current and executable directories if valid; and
4. SDL3 folder/file dialogs.

Native installation directories can run in place through an indexed read-only view. ZIP/ISO/BIN inputs import into a preference-directory cache keyed by source fingerprint and importer schema. The native and browser importers use the same parser, layout detector, manifest, and validation tests.

SDL dialogs are asynchronous. Drive them through the SDL callback state machine instead of blocking `SDL_AppInit`.

## Input formats

### Installation directory

Enumerate recursively to bounded depth without changing process working directory. Find layout candidates by content, not directory name. Persist the native path or browser handle only after validation.

### ZIP

Use the measured reduced libarchive 3.8.2 configuration with zlib and ZIP reader support only. Static linked cost was about 146 KB Wasm / 62 KB gzip. It streamed a real 211.7 MB ZIP-wrapped BIN/CUE in under one second under Node/Wasm with the fixed heap.

Flatten one outer directory only if every meaningful entry shares it. Reject unsupported/encrypted methods, traversal, links, collisions, CRC failures, excessive ratios, and quota overruns.

### ISO-9660

Implement a project-owned read-only parser over:

```c
read_sector(userdata, uint64_t sector, unsigned char out[2048])
```

Required initial subset:

- primary volume and root record discovery;
- bounded recursive directory records;
- multi-sector regular files;
- 64-bit checked source offsets;
- ISO `;1` suffix removal;
- ASCII case folding; and
- extent/file bounds against the source size.

Add Joliet only when a supported corpus requires it. The importer does not need Rock Ridge permissions, writing, boot records, devices, or general mount semantics.

Libarchive parsed only 7 of 13 real converted images cleanly, so it remains the ZIP backend rather than the ISO oracle.

### BIN/CUE

Parse the CUE conservatively and expose its selected data track as logical ISO sectors:

- MODE1/2352: payload offset 16;
- MODE2/2352 Form 1: payload offset 24; and
- payload length 2048.

Validate the sync pattern, mode byte, complete sector count, CUE filename association, and track/index bounds. All 13 local full releases use this single-track shape (11 MODE1, two MODE2).

### Mac media

Direct HFS/Toast import is not required initially. The pack builder accepts extracted Mac media directories.

Mac Smackers are first-class replacements, not edge cases:

- DOS set: 18.0 MB;
- Win95 set: 28.6 MB;
- Mac set: 32.3 MB.

Mac's largest files exceed Win95 sizes, and `INTRONEW.SMK` replaces the intro. The manifest maps logical `INTRO.SMK` to that blob. Never encode DOS/Win95 size ceilings into the pack or runtime reader.

## Layout profiles

Observed profiles:

1. **Normalized installation**
   - base: selected directory
   - media: `pl8`, `raw`, `smk`, `xmi`

2. **DOS CD**
   - base: `HD`
   - media: sibling `PL8`, `RAW`, `SMK`, `XMI`

3. **Hybrid Win95 CD**
   - base: `C2WIN95/HD`
   - media: `C2WIN95/PL8`, `RAW`, `SMK`
   - music: disc-root `XMI`
   - required portable bank fallback: disc-root `HD/CAESAR.OPL` or `CAESAR.AD`

4. **Selected C2WIN95 directory**
   - same children as profile 3
   - bounded parent/sibling lookup for XMI and portable music bank

5. **One outer archive directory**
   - strip it, then apply profiles 1–4

Demo trees are incomplete and must not pass a full-install validator merely because ENG files exist.

## Optimized asset pack

### Goals

- contain only selected runtime files;
- carry one language or every available language;
- deduplicate identical data;
- permit independently selectable text/help, speech, graphics, music, and video profiles;
- accept DOS, Win95, Mac, and custom higher-quality media;
- be buildable as ZIP or ISO; and
- remain usable by native and browser importers.

### Container layout

Use an ISO-9660-friendly abstract layout so ZIP and ISO contain the same files:

```text
C2PACK.JSN
OBJECTS/
    00000001.BIN
    00000002.BIN
    ...
```

Short numeric object names avoid requiring Joliet. `C2PACK.JSN` records each object's SHA-256 and 64-bit size, so IDs are container-local and content identity remains stable.

Manifest sections:

```text
schema/version
objects: id -> sha256, size
components:
  core/<profile>
  text/<language-release>
  speech/<language-release>
  graphics/<release>
  effects/<release>
  music/<release>
  video/dos | video/win95 | video/mac | video/custom
profiles: named compatible component selections
defaults
logical aliases
source/provenance labels
```

Each component maps canonical logical paths to object IDs. `video/mac` can map `INTRO.SMK` to the `INTRONEW.SMK` object.

### Multi-language behavior

An all-language pack stores shared objects once and contains multiple text/help and speech components. The page selects a profile before game startup. The active logical view then exposes the selected files under canonical engine names:

```text
C2.ENG
HELP.ENG
RAW/*.RAW
```

The Wasm executable no longer needs one build per language. `C2_LANGUAGE` becomes an optional default-profile/package label rather than a compile-time asset partition.

Default profiles should couple text/help, localized graphics, and speech from one observed release. Advanced UI may allow deliberate cross-language mixing, but it must show provenance and validation warnings rather than assume all 94 observed variant files are interchangeable.

Measured deduplication across all 13 DOS release profiles:

- one representative runtime set: 56.9 MB uncompressed;
- all observed DOS variants content-addressed: 89.1 MB uncompressed;
- 537 of 631 runtime paths are byte-stable; and
- only 94 paths vary.

This makes an all-language bundle practical. Adding all DOS/Win95/Mac video sets increases media size, but content addressing still stores byte-identical Win95/Mac clips once.

### Pack builder

Provide a native CLI, later compiled for a browser worker:

```text
c2-assets inspect SOURCE...
c2-assets build --core SOURCE \
  --text en=SOURCE --speech en=SOURCE \
  --text de=SOURCE --speech de=SOURCE \
  --video mac=/path/to/extracted/mac/smk \
  --output caesar2-all.c2assets
c2-assets verify caesar2-all.c2assets
```

Outputs:

- `.c2assets` (deflated ZIP) by default;
- ordinary `.zip` alias if desired; and
- optional ISO using the same manifest/object tree.

The safe first pack includes the conservative 631 runtime paths plus one supported OPL/AD bank. Do not prune to the 387 literal or 102 smoke-traced files; dynamic tables and unvisited gameplay paths make those lower bounds.

## Validation and security

Treat every source and pack as hostile:

- 64-bit checked arithmetic and bounded chunk buffers;
- input, output, object, entry-count, depth, path-length, and compression-ratio quotas;
- cancellation and progress;
- CRC/hash verification;
- no links, devices, sparse surprises, encryption, traversal, or duplicate canonical paths;
- output only to importer-owned staging/object directories; and
- fuzz the exact ZIP, ISO, CUE, path, manifest, and profile-selection code.

Validation layers:

1. catalog/path safety;
2. manifest/hash integrity for optimized packs;
3. parsed `C2.ENG` and `HELP.ENG`;
4. conservative core component completeness;
5. optional speech/video/help capabilities;
6. profile compatibility warnings; and
7. Debug semantic smokes against each supported corpus/profile.

## Delivery phases

### Phase 0 — completed feasibility work

- reduced native/Wasm libarchive benchmark;
- real 13-disc corpus inventory;
- real ZIP and ISO compatibility runs;
- Chromium/Firefox OPFS reload tests with 80 MiB data and fixed heap;
- save/history persistence proof; and
- Win95 high-quality media smoke tests.

### Phase 1 — implemented: OPFS user data and export

- migrate browser persistence from IDBFS to WasmFS OPFS;
- mount `/game-data` and `/user-data` before SDL host init;
- preserve all `*.sav`, `history.dat`, and `caesar2.inf`;
- add storage status and persistence request;
- add individual and ZIP save downloads; and
- add browser restart regression tests.

**Gate:** saves survive page reload and browser restart in Chromium and Firefox, exports match source bytes, and the game heap remains fixed.

### Phase 2 — implemented: source manager and native/browser directories

- add importer ABI and canonical catalog;
- add startup state machine and page/native pickers;
- implement layout profiles and validation;
- index direct native directories;
- copy browser folders transactionally into content-addressed OPFS objects; and
- implement Change/Delete Game Data separately from save deletion.

**Gate:** all currently supported native smokes pass from normalized, DOS-CD, and hybrid Win95 layouts; invalid imports retain the previous generation.

### Phase 3 — implemented: ZIP

- integrate reduced libarchive ZIP reader;
- add source quotas, path/collision validation, and outer-directory normalization;
- import normal installation ZIPs and ZIP-wrapped BIN/CUE; and
- test fixed-heap browser imports at real corpus sizes.

### Phase 4 — implemented: ISO and BIN/CUE

- implement and fuzz the in-tree ISO reader;
- implement CUE and MODE1/MODE2 sector adapters;
- test plain ISO directly as well as all 13 converted local discs; and
- add native/browser `.iso`, `.bin`, and `.cue` UX.

**Gate:** all 13 releases produce the same canonical catalogs as the established Python tooling.

### Phase 5 — implemented baseline: optimized multi-profile packs

- implement `C2PACK.JSN` and content-addressed objects;
- generate the conservative runtime manifest from corpus/static analysis;
- add all-language text/speech profiles;
- add DOS, Win95, Mac, and custom video components;
- add runtime profile selector and aliases;
- emit ZIP and ISO forms; and
- retain build-time prepackaging as a distributor option.

**Gate:** one pack can switch languages and video sets without reimporting shared assets, and every profile passes its relevant semantic smokes.

### Phase 6 — evidence-driven pruning

Use asset-open telemetry across complete campaign/battle/event coverage to refine optional groups. Never remove files based only on startup or source-literal traces.

## Tests

- generated safe/malicious ZIP, ISO, BIN/CUE, and pack fixtures;
- all 13 opt-in local CD images;
- localized text/speech profile matrix;
- DOS, Win95, and Mac video profile decoding/playback;
- native direct-directory and cache invalidation;
- OPFS creation, reload, browser restart, persistence denial, quota failure, cancellation, and rollback;
- save/history/settings byte-exact export;
- source switching without save loss;
- manifest/object deduplication and garbage collection; and
- fuzz targets for every untrusted parser and canonicalization boundary.

## Final recommendation

Proceed with implementation in this order:

1. OPFS migration and save export;
2. source manager and directory import;
3. libarchive ZIP;
4. in-tree ISO plus BIN/CUE;
5. multi-language/multi-media optimized packs.

The measurements show this is feasible without changing recovered game logic, without growing the game heap, and without requiring users to reselect their source on every visit.
