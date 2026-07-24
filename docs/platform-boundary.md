# Legacy/portable platform boundary

## Purpose

Caesar II's recovered source does not have a single historical "platform
file." The DOS boundary is distributed across a small number of functions in
seven C translation units, a banked-refresh implementation, third-party audio
and movie APIs, and thirteen hardware-facing assembly routines. At the same
time, `lib32.c` and the assembly corpus contain a large amount of ordinary
game, formatting, rasterization, compression, and math code.

The port therefore uses a function-level boundary. It does not classify
`lib32.c`, all assembly, or all startup code as disposable platform code.

The intended dependency direction is:

```text
recovered engine code
        |
        | existing Caesar-facing function names
        v
portable compatibility implementations
        |
        | small c2_host_* service interface
        v
SDL, filesystem, audio, and media backends
```

SDL types and functions must not occur above `c2_host_*`. This keeps recovered
files recognizable, makes reconstruction changes easy to cherry-pick, and
allows headless and non-SDL backends to exercise the same engine.

## Implemented boundary

The native port now follows that dependency direction:

- `include/c2_host.h` is the backend-neutral service contract;
- `src/platform/common/c2_port_compat.c` owns same-symbol legacy shims such as
  `readfile`, user-data I/O, `refresh_svga_screen`, and palette publication;
- `src/platform/common/c2_port_input.c` translates host snapshots and input
  events into the legacy mouse and keyboard globals; printable input crosses
  the host interface as Unicode code points and is converted to the CP850
  bytes accepted by the recovered text editor, while navigation keys retain
  their DOS scan codes; recovered `lib32.c` still owns press/release edges,
  cursor state, text editing, timing, raster dispatch, and other engine
  support;
- `src/platform/common/c2_port_mouse.c` owns the backend-neutral bounded
  virtual cursor, active-resolution scaling, windowed edge zone, and
  absolute/relative motion conversion;
- `src/platform/common/c2_port_audio.c` implements the Miles sample surface
  over backend-neutral PCM voices, while `src/platform/sdl3/c2_sdl_audio.c`
  owns the SDL3 playback device, conversion, resampling, and mixing;
- `src/platform/common/c2_port_video.c` implements the recovered Smacker
  surface with libsmacker and delegates only indexed-frame publication and
  PCM queuing to the host;
- `src/platform/common/c2_port_bugfixes.c`,
  `c2_port_save_compat.c`, and `c2_port_text_compat.c` contain portable-only
  compatibility policy; they deliberately do not live beside recovered
  translation units at the `src/` root;
- `src/platform/common/c2_port_timing.c` reproduces the recovered Watcom/DOS
  clock's 18.2 Hz, 50-to-60-ms increments while replacing VGA blank waits and
  CPU-throughput frame timing with separate explicit host deadlines; the three
  historical timing mechanisms are mapped in `docs/timing.md`;
- `src/platform/common/c2_port_app.c` only invokes `c2_engine_main`, traps the
  legacy exit boundary, and performs final cleanup;
- `src/platform/common/c2_port_observation.c` copies selected engine state into
  semantic observations at explicit recovered-code checkpoints; it is a
  one-way, read-only instrumentation bridge compiled only into Debug builds
  and inactive outside observed test runs;
- `src/platform/sdl3/c2_sdl_host.c` implements the host contract; and
- `src/platform/sdl3/c2_sdl_main.c` is only the SDL lifecycle/thread adapter,
  while `c2_sdl_smoke.c` consumes observations and generates ordinary host
  input for end-to-end tests.

Legacy text remains engine-rendered bitmap data. The narrowly scoped,
switchable repair for editor-era smart punctuation is documented in
`docs/text-encoding.md`.

The SDL backend hides the operating-system cursor while its window exists;
the recovered engine remains the sole owner of the visible in-game pointer.
The original `set_mouse_limits`/`mouserange` contract remains authoritative:
the portable host stores its inclusive bounds and scales the fixed renderer
viewport into the active 320x200, 640x400, or 640x480 mouse coordinate space.
`set_mouse` updates the virtual position and schedules an SDL warp when the
backend is using absolute input.

In unlocked windowed mode an eight-logical-pixel strip maps to each exact
legacy limit, making edge and corner scrolling selectable without requiring
pixel-perfect placement. Leaving the rendered viewport moves a boundary
coordinate one unit inward, immediately cancelling stale scrolling. With
`--mouse-lock`, SDL mouse grab and a content-area barrier confine native
absolute input. If confinement is unavailable, SDL relative mode feeds deltas
into the same bounded virtual cursor. SDL's Emscripten backend implements that
relative mode with browser Pointer Lock, so the engine-facing contract and
game-drawn cursor do not change for WebAssembly. `--no-mouse-lock` is the
explicit spelling of the default free-pointer policy.

SDL text-input events supply layout- and modifier-aware printable characters;
key-down events are reserved for Escape, Enter, Backspace, Delete, Insert,
Home, End, the arrow keys, F1--F5, and the recovered Alt hotkeys. The common
key mapper reconstructs the DOS scan codes consumed by `sim_mouse`; it covers
Alt+F, Alt+F1, Alt+F3, Alt+D, Alt+X, and Alt+1 through Alt+8. Vertical wheel
events become the existing `+` and `-` engine inputs, keeping zoom policy in
the recovered hotkey handler. The recovered `act_choose_name`,
`new_name_game_loop`, and `edit_format_buffer` path is shared unchanged by the
portable target.

The shipped default name is a fixed-width field containing `Octavian` followed
by sixteen spaces, and the recovered End handler counts that padding. Before
the shared editor is initialized, the portable build trims trailing spaces
under `C2_FIX_PLAYER_NAME_PADDING`. This handles both fresh defaults and old
runtime files without replacing editor behavior. Disabling the same-named
CMake option restores the padded input exactly.

The native target compiles the complete recovered `c2.c` campaign driver and
`lib32.c`. The former replacement bootstrap, port-side raster slice, and copied
text subset were removed once the same-symbol boundary was complete enough to
link the original path.

`tests/test_port_layering.py` enforces that SDL API names do not escape the
backend, recovered files do not call `c2_host_*` directly, portable common
code does not depend back on `c2_sdl_*`, portable-only translation units stay
out of the recovered source root, and the SDL callback does not mutate
representative legacy globals. Extend this test whenever the boundary grows.

The observation contract lives in `include/c2_observation.h`. Recovered code
publishes lifecycle and modal checkpoints from the engine worker. Each record
contains a monotonically increasing sequence, a cumulative reached bitset, and
a small immutable snapshot of relevant game state. The host may copy that
record, but has no API for writing engine state. Test input remains entirely
separate and travels through the normal mouse/key publication path.
The city-flow smoke also observes completed top-menu and drop-down rendering,
including the recovered hit boxes, and opens both File and Options through the
ordinary mouse path. The portable target deliberately selects the DOS
software-menu renderer because, unlike the shipped Windows target, it has no
native platform menu bar.
`C2_DEBUG_BUILD` is supplied by CMake only for the Debug configuration and
selects `C2_FEAT_DEBUG_OBSERVATION`; non-Debug builds omit the adapter sources,
host storage, checkpoint calls, smoke driver, and smoke command-line options.

## Portable assembly interface

Before translating individual assembly bodies, the complete callable ABI is
represented by `include/c2_asm_routines.def`. It contains exactly 87
function slots: one for every callable `PUBLIC` export in the eight recovered
assembly files. `include/c2_asm_routines.h` turns the manifest into engine
declarations. Each entry is explicitly marked `C2_ASM_STUB` or
`C2_ASM_IMPLEMENTED`; `src/asm/c2_asm_stubs.c` supplies only the
remaining hardware-facing bodies. The header is exposed to recovered callers
only for `PLATFORM_PORTABLE`; Watcom retains the recovered call surface and
never parses the portable manifest macros.

All 74 CPU-only exports are implemented in ordinary C. They cover memory and
compression, internal-screen primitives, font and sprite blitters, block and
mouse-background copies, callback invocation, map-pointer diamond writers,
and every small, medium, and large diamond image/hat/roof variant. Their
implementations preserve the recovered clipping, transparency, fixed-640
projected-row, variable-stride origin, and byte-oriented unaligned-access
semantics.

Compatibility note: `write_medium_diamond_righthat` contains one asymmetric
literal store inherited from `dia_medi.asm`. In the third post-depth clipped
row, source pair 3 is written at x=62 rather than the geometrically symmetric
x=6. The portable implementation corrects it by default. The centralized
`C2_FIX_MEDIUM_RIGHT_HAT_OFFSET` switch in `include/c2_bugfixes.h` selects the
behavior: `1` uses x=6 and `0` restores the shipped x=62 store. CMake exposes
the same switch as an option, so a compatibility build uses
`-DC2_FIX_MEDIUM_RIGHT_HAT_OFFSET=OFF`.

The large right half-roof has a separate unrolled-row defect in seam mode `2`.
Every other row suppresses source pair 0 at the seam, but row 10 in
`dialargb.asm` omits that check and draws the pair. Suppressing the stray pair
is the portable default. Set `C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR` to `0`,
or use the same-named CMake option with `OFF`, to reproduce the shipped row-10
store.

The recovered graphics-buffer cleanup functions retain dangling pointers, and
some original paths call both map and battle cleanup while `fixt_data` names the
same allocation. Modern allocators reject the resulting repeated free. The
portable build clears every released graphics pointer by default under
`C2_FIX_GFX_BUFFER_DOUBLE_FREE`; set the same-named CMake option to `OFF` to
reproduce shipped cleanup behavior.

`tests/test_diamond_asm_oracle.py` provides the executable semantic oracle for
this family. It builds a statically linked 32-bit Linux fixture with OpenWatcom
and the original recovered assembly, builds the same fixture against the
portable C with renderer bug fixes disabled, and compares complete framebuffer
contents byte-for-byte across parameter cases. The ordinary C test runs with
the corrected defaults, including focused assertions for the corrected
destinations. Extend the shared harness whenever another diamond routine is
translated.

The remaining 13 manifest slots are deliberately unimplemented DOS hardware
operations: direct VGA/VESA writes, bank selection, vertical blank, physical
screen and cursor copies, dirty-tile bank refresh, and RAD palette callbacks.
They are unreachable in the portable build because the corresponding callers
select the framebuffer, timing, cursor, refresh, and movie adapters instead.
They are not outstanding CPU translations.

The DOS diamond modules use the 20-byte Smacker/Miles `sndinit` array as four
unaligned transient dword slots at byte offsets 2, 6, 10, and 14. Each affected
routine writes its own argument there and reads it back only during that call.
Portable translations must replace these assembly register-spill slots with
local variables; renderer state must not remain coupled to the deferred sound
backend.

The translated CPU routines remain a separate `c2_asm_portable` library linked
into the running port. The recovered UI and simulation exercise its sprite
writers and fixed-size block loaders through recovered `display.c` and
`screens.c` call paths.
`tests/test_asm_portable_surface.py` derives the assembly exports from source
and requires exact set equality with the manifest.

The assembly surface must not be confused with the 81 C functions that
directly use a DOS, operating-system, Miles, or Smacker API. Those 81 are an
audit set, not 81 replacement bodies: several contain engine policy or file
format logic that must remain shared and delegate only their host operations.

## Audit method and scale

The boundary inventory was generated with the repository's tree-sitter C AST
support, recursively walking preprocessing nodes as well as ordinary
translation-unit children. A top-level-only AST traversal is incorrect here:
it omits precisely the functions nested under platform guards.

The audited source contains:

- 1,451 reconstructed C functions;
- 81 functions that directly call DOS, OS, Miles AIL, or RAD Smacker APIs;
- 26 DOS-only function bodies already grouped in `lib32.c`;
- 8 assembly files exporting 87 callable routines; and
- 897 C loop nodes in 523 functions, most of which are bounded renderer,
  simulation, map-walking, compression, or formatting loops rather than host
  event loops.

The 81 direct platform/API users are concentrated in `c2.c`, `lib32.c`,
`loadsave.c`, `pcsound.c`, `smacker.c`, `display.c`, and `hotkeys.c`.
`refresh.c` additionally reaches video hardware through assembly calls. This
concentration is the main evidence that selected replacement is viable.

## Build selection

Platform selection describes the program being built, not the compiler used
to build it:

- `PLATFORM_DOS`: the shipped DOS/4GW program;
- `PLATFORM_WINDOWS`: the shipped Windows source witness; and
- `PLATFORM_PORTABLE`: the modern continuation in this repository.

Source must not infer a platform from `__WATCOMC__`, `_MSC_VER`, or another
compiler macro. A different compiler may legitimately target the same
platform, and one compiler may target more than one platform. Compiler
pragmas may remain where they express an ABI, register-clobber contract, or
symbol decoration; they must not choose game behavior or platform services.

Use a named `C2_FEAT_*` macro when the condition describes a verified behavior
difference between releases. Use a `PLATFORM_*` condition for build mechanics
or an actual host facility.

## Inputs excluded from a portable build

The following historical inputs must not be compiled or linked into the
portable executable:

| Historical input | Portable treatment |
|---|---|
| The eight `.asm` files | Same-signature portable C replacements |
| Miles AIL objects/import machinery | Modern audio backend |
| RAD Smacker objects/import machinery | Modern movie backend |
| `sndail.c`, `sndnull.c`, and `smackinp.c` vendor bridge state | Exclude once the portable backends own the corresponding state |
| DOS entry/CD-drive policy | Guarded DOS policy; recovered driver entered by the portable lifecycle adapter |
| VGA, VESA, DPMI, port-I/O, and INT 33h bodies | DOS-only bodies plus portable same-symbol implementations |
| Banked physical-screen refresh | Portable `refresh_svga_screen` body that publishes a framebuffer |

No major recovered engine C translation unit should be excluded wholesale.
In particular, `lib32.c`, `pcsound.c`, `display.c`, and `c2.c` each contain
shared policy or algorithms in addition to their historical platform work.

## Assembly classification

Only thirteen of the 87 callable assembly exports are true DOS video
operations:

- `library.asm`: `cls_256x`, `show_point_256x`, `copy_screen_256x`,
  `convert_and_copy_to_256xscreen`, `copy_to_256xscreen`,
  `copy_from_256xscreen`, `wvbl1`, `set_bank`,
  `copy_to_640_480_screen`, and `copy_mouse_to_screen`;
- `sprites.asm`: `refresh_16x16_block` and
  `refresh_16x16_partblock`; and
- `palet.asm`: `PaletteSet`.

The remaining 74 exports are implementation-language work, not platform
work. They include all diamond rasterizers and pointer calculators, font and
sprite rasterization, block placement, mouse-background save/restore,
compression, decompression, memory copying, internal-screen primitives, and
`call_address`. They should be translated to ordinary C and compiled by the
target compiler for x86-64, ARM64, or Wasm. Hand-written Wasm versions would
create an unnecessary second portability problem.

## Filesystem and asset services

The legacy-facing asset surface is already useful and should keep its current
signatures:

- `readfile`;
- `writefile`;
- `write_to_file`;
- `check_file_exists`;
- `is_file_on_harddrive`; and
- `get_directory`.

`readfile` has 38 direct engine callers. Retaining it keeps path resolution out
of the engine. Its portable implementation must replace `cd_path` and
`main_path` with an asset resolver; it must never emulate the DOS code by
changing the process working directory. The resolver searches a configured
data root case-insensitively and preserves the old install/CD overlay rules
without exposing drives to callers.

The overlay lookup order is the asset-root top level first, followed by the
original extension-selected CD media directory: `pl8/` for `.pl8`, `raw/` for
`.raw`, `xmi/` for `.xmi`, and `smk/` for `.smk`. Both directory and file names
are matched case-insensitively. Root assets take precedence when both locations
contain the same name, matching `readfile`'s original hard-drive-first lookup.
Other extensions remain root-only; the resolver must not search unrelated
media directories heuristically.

Mutable storage is a separate namespace from assets. Save games,
`caesar2.inf`, `history.dat`, and screenshots use a writable user-data root.
The Emscripten SDL backend mounts and synchronizes IDBFS-backed `/user-data`
before the engine starts, after which the legacy worker continues to perform
synchronous file operations.

The native host separates `asset_root` and `user_data_root`. `readfile` uses
the asset service, while save-game enumeration, bulk `savegame` / `loadgame`
streams, preferences, history data, autosaves, and screenshots use the
user-file service. The completed contract and save-layout treatment are
documented in [user-data.md](user-data.md).

The command-line names expose that ownership directly. `--asset-root` (or
`C2_ASSET_ROOT`) selects the immutable installed/CD asset tree.
`--user-data-dir` (or `C2_USER_DATA_DIR`) overrides the mutable runtime tree.
When it is not overridden, the SDL backend uses its platform preference path:
the XDG application-data location on Linux and the corresponding standard
per-user location on Windows and macOS. Save games, `caesar2.inf`,
`history.dat`, and screenshots all belong to this mutable namespace; asset
fallback into it is forbidden.

Resource-version compatibility is not a filesystem responsibility. The host
returns the selected asset unchanged. Engine/UI revisions that require
different string indices or control counts are selected from the read-only
`Textfile` structure behind `C2_FEAT_TEXT_ASSET_COMPAT`; see
[text-asset-versions.md](text-asset-versions.md). The original recovered path
must remain present when that feature is disabled.

These functions mix serialization or game fixups with raw file descriptors:

- `savegame` and `loadgame`;
- `save_inf` and `load_inf`;
- `loadmodel`;
- `setup_history_data`, `save_history`, and `get_history_in_buffer`; and
- `capture_shot`.

Their game behavior remains shared. Narrow portable guards replace only their
open/read/write/seek/close operations with the complete-file platform service.
The two native-pointer-bearing entity arrays are converted by an engine-side
save codec; save ordering and post-load behavior are not duplicated in the
platform layer.

The complete portable save stream is assembled and validated in
`src/platform/common/c2_port_save.c`. Engine call sites only delegate across
that boundary and honor its success result. The platform implementation
accepts the recovered registry's full 500-entry form, validates the exact
legacy payload size, and reads a complete file before changing live state.
DOS and Windows continue through the recovered descriptor/file operations.

For screenshots, the shared engine passes the current indexed framebuffer and
VGA palette read-only across the host boundary. The SDL backend encodes PNG
under the user-data root. Shipped targets retain the recovered LBM writer;
portable code neither mutates the live palette nor reconstructs image formats
inside the engine.

`test_cd_drive` is different: DOS drive validation is its entire purpose, so
the portable target should provide a complete body that validates or selects
the configured asset root.

## Video and palette services

The reference renderer remains the 640x480 indexed `internal_screen` plus its
palette. Keep shared:

- all rendering into `internal_screen`;
- dirty-tile marking and viewport calculations;
- palette animation state;
- sprite, font, diamond, line, box, UI, and map rendering; and
- `refresh_zoom_mode` and `refresh_battle_zoom_mode`.

Provide complete portable implementations for VGA/VESA setup, bank selection,
physical copies, and `refresh_svga_screen`. The portable `refresh_svga_screen`
retains the dirty-table and refresh-counter semantics, then publishes the
indexed framebuffer and palette rather than copying through VESA banks.
`setup_svga_refresh_data` only precomputes banked-VESA copy metadata and is not
used by portable framebuffer publication.

Keep `cycle_colours`, `pulse_red`, `set_palette`, and the interpolation logic
in `fade_to_palette`. Replace `set_vga_palette` and
`set_vga_palette_range` with palette publication. `fade_to_palette` is a
mixed function because it also waits and polls input; its portable path needs
an explicit timed engine yield.

`do_svga_smacked_anim` now uses the recovered body on every target.
`do_vga_smacked_anim` has a narrow portable branch that retains the recovered
filename, input, skip, and cleanup loop while omitting VGA mode changes and
banked-buffer destruction. Its 320x200 logical canvas is scaled into the
640x480 indexed framebuffer at the adapter boundary.

## Input services

Provide same-signature portable implementations of `init_mouse`,
`read_mouse`, `set_mouse`, `mouserange`, `set_mouse_limits`, and `get_key`.
The INT 33h callback, DPMI lock, and installed-mouse callback buffer remain
DOS-only.

Keep `get_mouse` and `sim_mouse` logically on the engine side. They implement
replay input, movement, button edges, and legacy global state rather than host
event collection. The full recovered `lib32.c` now supplies both functions;
`src/platform/common/c2_port_input.c` supplies only the same-symbol hardware
edge (`init_mouse`, `read_mouse`, `set_mouse`, `mouserange`, and `get_key`).
The host publishes a normalized input snapshot and a keyboard event queue. SDL
event handlers must not directly mutate `c2inf`, menu decisions, or control
state. SDL key/modifier and wheel events are normalized at this boundary, then
the common mapper emits the ASCII or DOS scan-code pairs already consumed by
the recovered `sim_mouse`. Unit coverage enumerates every scan-code branch in
that handler, including F1--F5, all supported Alt chords, and both wheel
directions.

Mouse confinement is policy, not engine control flow. The recovered
`scroll()` continues to react only to the exact bounds supplied by
`mouserange`; the common cursor adapter maps a host edge zone or relative
motion onto those bounds. Native grab and browser Pointer Lock remain backend
mechanisms selected below `c2_host.h`.

## Timing and waits

`running_delay1`, `colour_cycle_delay1`, `colour_cycle_delay2`, and `timer`
retain their legacy interfaces and read the common timing adapter's modeled
Watcom/DOS clock. The adapter advances from a monotonic host source but exposes
the original 18.2 Hz, 50-to-60-ms increments to recovered code.

The following busy waits require portable bodies or narrow portable branches:

- `wvbl2` and `do_delay`;
- `click_delay` and `clicked_delay`;
- `wait_click`, `wait_key`, and `clear_mouse`;
- the inner wait in `fade_to_palette`; and
- movie frame waits.

The post-save 1,000-frame and post-load 200-frame cosmetic holds are handled by
a narrow feature branch. Portable builds omit them because the file operation
is already complete and pacing those iterations at 60 Hz would create
artificial 16.7-second and 3.3-second delays.

A no-op replacement is not acceptable: it turns these paths into CPU-burning
spins. They must wait on a condition, timer, or engine-thread scheduling
primitive.

## Audio services

The concrete dependency choices, XMIDI branching requirement, implementation
order, and compatibility tests are recorded in
[`media-implementation.md`](media-implementation.md).

Keep music mood and ambient policy in the engine:

- `get_city_mood`, `get_battle_mood`, `get_old_mood`;
- `choose_odd_tune` and `sooth_mood`;
- ambient event selection and delay logic; and
- the city, province, and battle ambient tables.

Replace Miles driver startup, voice allocation, sample status, speech
streaming, sequence control, and handle management behind the existing public
sound API. `continue_db` remains callable even if a modern streaming backend
does not require per-frame service.

Digital samples and speech are implemented. The portable target compiles the
recovered `pcsound.c`, preserving its six-voice rotation, dedicated feedback
and speech voices, sample cache, ambient tables, delay policy, and mood code.
The common Miles adapter maps those handles onto SDL-independent PCM
operations. SDL3 supplies one stream per voice, WAV decoding, conversion,
resampling, gain, and device mixing; a seventh private voice reproduces the
PC-speaker feedback tones without stealing a recovered sample handle. RAW
speech is loaded through the asset service as unsigned 8-bit mono PCM at
22,050 Hz. Pausing speech unbinds only that stream, rather than pausing the
shared SDL device and every effect with it.

XMI music is not merely file playback. Miles invokes `mood_modfication` at a
sequence marker; the engine calculates a new mood and requests a numbered
branch. The common adapter implements that recovered Miles surface with the
pinned Second Impressions libADLMIDI fork. It owns the two private sequencer
handles, loads shipped Miles timbres, pumps synthesized PCM from `continue_db`,
and translates `AIL_branch_index` into the fork's bounded numbered jump. SDL3
owns only the device streams, queued-duration observation, and gain.

The SDL3 host reports `C2_HOST_CAPABILITY_MUSIC` only now that this complete
path is functional. Trigger callbacks run synchronously in the engine pump, so
`mood_modfication` and all recovered state remain confined to the engine
thread. Other backends must continue to report the capability unavailable
until they implement equivalent sequencing, synthesis, and callback behavior.

## Movie services

Decoder selection and the indexed-frame/audio integration plan are recorded in
[`media-implementation.md`](media-implementation.md).

Retain `start_smacking`, `continue_smacking`, `stop_smacking`, and
`are_smacking` as the engine-facing API, with complete portable bodies. This
surface covers both full-screen cinematics and movies embedded in message
dialogs. Prefer decoding into the indexed framebuffer and palette model so
movie playback does not impose a second renderer on the engine.

Video is available through the Second Impressions libsmacker fork and reported
through `C2_HOST_CAPABILITY_VIDEO`. The common adapter owns the private decoder
handle, frame deadline, asset buffer, palette conversion, indexed-frame copy,
and dedicated movie-audio voice. Startup therefore runs the recovered
`INTRO.SMK` loop, while message dialogs continue to call the same embedded
movie API they used under DOS. The SDL backend remains unaware of Smacker and
only receives indexed frames and PCM chunks through the existing host
interfaces.

For buffered embedded and SVGA movies, advancing the decoder only updates
`internal_screen` and dirty metadata. The recovered caller remains responsible
for the one frame publication after overlays and the software cursor have been
drawn. Only the legacy direct-VGA mode publishes from the adapter itself.

## Startup, shutdown, and errors

The DOS `main` combines process bootstrap, CD policy, resource initialization,
and the persistent campaign loop. A portable application entry owns SDL and
starts the engine; the campaign flow remains legacy code on the engine worker.
Similarly, `start_system` and `stop_system` should retain shared allocation and
game initialization while delegating video, input, audio, and process work.

Fatal resource errors should call a host-neutral `c2_fatal` service rather
than invoking display teardown and `exit` from arbitrary engine functions.

## Source-selection policy

Use these forms in preference order:

1. A fully platform-specific function gets a guarded historical body and a
   same-symbol portable implementation in a separate compatibility file.
2. A mixed function with one or two platform operations stays shared and
   guards or delegates only those operations.
3. A function whose control flow is structurally different on the portable
   target gets a complete target-selected body.
4. A verified game behavior difference gets a named `C2_FEAT_*` switch rather
   than a platform or compiler test.

Recovered files stay at their inherited paths. CPU-only translations of the
recovered assembly belong in `src/asm/`. Backend-neutral compatibility code
belongs in `src/platform/common/`, while backend-specific code belongs below
`src/platform/<backend>/`. Select those backend sources in the build graph;
do not accumulate backend compiler tests inside shared engine functions.
