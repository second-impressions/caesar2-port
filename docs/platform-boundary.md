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
- `src/platform/common/c2_port_audio.c` and `c2_port_video.c` are explicit
  unavailable capability shims until real audio and Smacker backends are
  selected;
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
SDL text-input events supply layout- and modifier-aware printable characters;
key-down events are reserved for Escape, Enter, Backspace, Delete, Insert,
Home, End, and the arrow keys. The recovered `act_choose_name`,
`new_name_game_loop`, and `edit_format_buffer` path is shared unchanged by the
portable target.

The native target compiles the complete recovered `c2.c` campaign driver and
`lib32.c`. The former replacement bootstrap, port-side raster slice, and copied
text subset were removed once the same-symbol boundary was complete enough to
link the original path.

`tests/test_port_layering.py` enforces that SDL API names do not escape the
backend, that portable layers do not depend back on `c2_sdl_*`, and that the
SDL callback does not mutate representative legacy globals. Extend this test
whenever the boundary grows.

The observation contract lives in `include/c2_observation.h`. Recovered code
publishes lifecycle and modal checkpoints from the engine worker. Each record
contains a monotonically increasing sequence, a cumulative reached bitset, and
a small immutable snapshot of relevant game state. The host may copy that
record, but has no API for writing engine state. Test input remains entirely
separate and travels through the normal mouse/key publication path.
`C2_ENABLE_OBSERVATION` is supplied by CMake only for the Debug configuration;
non-Debug builds omit the adapter sources, host storage, checkpoint calls,
smoke driver, and smoke command-line options.

## Portable assembly interface scaffold

Before translating individual assembly bodies, the complete callable ABI is
represented by `include/c2_asm_routines.def`. It contains exactly 87
function slots: one for every callable `PUBLIC` export in the eight recovered
assembly files. `include/c2_asm_routines.h` turns the manifest into engine
declarations. Each entry is explicitly marked `C2_ASM_STUB` or
`C2_ASM_IMPLEMENTED`; `src/asm/c2_asm_stubs.c` supplies only the
remaining empty bodies.

The first implemented batch is `copy`, `compress`, and `depress` in
`src/asm/c2_asm_memory.c`. Their byte-oriented implementation avoids
unaligned typed accesses and is covered by exact encoded-form and round-trip
tests. `copy` preserves the assembly routine's contract: callers provide a
positive byte count in 32-byte units, and the implementation copies whole
32-byte chunks.

The internal-screen point writers, zero-only two-pixel writer, 2/4/6/8-pixel
block placers, and fast rectangle filler are implemented in
`src/asm/c2_asm_internal_raster.c`. These retain the original fixed
640-pixel stride in the block placers and in `show_internal_2x8`; the other
point writers and the fast rectangle filler retain their variable
`screen_width` stride. Tests cover both behaviors directly against framebuffer
rows. The live inventory is therefore 13 implemented and 74 blank routines.

The seven font/sprite blitters, three fixed-size block loaders, and two mouse
background copies are implemented in `src/asm/c2_asm_sprite.c`.
Their source transparency, clipping skips, embedded little-endian sprite-table
offsets, and mixed variable-initial/fixed-640 row addressing have direct tests.
The `char *` mouse-background ABI is retained, while its arbitrary pixel bytes
are accessed through the C-defined `unsigned char` representation view. The
live inventory is therefore 25 implemented and 62 blank routines.

The nine map-pointer diamond writers are implemented in
`src/asm/c2_asm_diamond_ptr.c`. They are rasterizers despite their
historical `ptr` names: each writes a two-byte color word around a large,
medium, or small diamond. The portable geometry preserves the original
top/bottom selection, clipped-side suppression, variable-stride origin, and
fixed 640-pixel row offsets without unaligned typed stores. The live inventory
is therefore 34 implemented and 53 blank routines.

The basic small, medium, and large image-diamond placers are implemented in
`src/asm/c2_asm_diamond_image.c`, including opaque pixels, half
selection, screen-edge source cropping, and the variable-origin/fixed-row
addressing split. The shared kernel follows the recovered 6/14/30-row symmetric
geometry; the small clipped pair retains its assembly-specific ignored `part`
argument. The live inventory is therefore 43 implemented and 44 blank
routines.

`call_address` is implemented as the ordinary no-argument, return-discarding
callback invocation encoded by its assembly trampoline. The live inventory is
therefore 44 implemented and 43 blank routines.

The nine full and screen-edge left/right diamond-hat writers share a proven
two-pixel-pair projection kernel. It preserves transparent pixels, `y_length`,
the variable-stride upward origin walk, fixed-640 projected rows, and the
post-depth outer-pair clipping encoded by the unrolled assembly. The live
inventory is therefore 53 implemented and 34 blank routines.

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

The nine full and screen-edge left/right roof writers use the corresponding
upward-growing V projection: source row `r` draws pairs at most `r` steps from
the center while the origin walks upward with `screen_width`. Their portable
kernel is covered by the compiled assembly oracle. The live inventory is
therefore 62 implemented and 25 blank routines.

The six half-width hat writers and six half-width roof writers complete the
CPU-only diamond family. Their source rows contain 3, 7, or 15 two-byte pairs;
the `edge_seam` argument is the recovered `0`/`2` choice that retains or
suppresses the joining pair at a viewport edge. The right-half encoding has an
unused leading hat pair and a special first roof row, both preserved by the
shared portable kernels and verified against compiled assembly. The live
inventory is therefore 74 implemented and 13 blank routines. The remaining
13 routines are all hardware-facing video, refresh, cursor, or palette paths.

The DOS diamond modules use the 20-byte Smacker/Miles `sndinit` array as four
unaligned transient dword slots at byte offsets 2, 6, 10, and 14. Each affected
routine writes its own argument there and reads it back only during that call.
Portable translations must replace these assembly register-spill slots with
local variables; renderer state must not remain coupled to the deferred sound
backend.

The translated CPU routines remain a separate `c2_asm_portable` library, now
linked into the running port. The recovered UI and simulation exercise its
sprite writers and fixed-size block loaders through recovered `display.c` and
`screens.c` call paths. The thirteen hardware-facing slots remain empty and
unreachable from the portable framebuffer publication path.
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

Mutable storage is a separate namespace from assets. Save games,
`caesar2.inf`, `history.dat`, and screenshots use a writable user-data root.
The browser backend may mount persistent storage asynchronously before the
engine starts, after which the legacy worker may continue to perform
synchronous file operations.

The native host already separates `asset_root` and `user_data_root`.
`readfile` uses the asset service, while preferences, history data, and
diagnostic screenshots use the user-file service. Save-game enumeration and
the bulk `savegame` / `loadgame` streams still need to move behind that same
boundary.

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

Keep their game behavior shared. Replace their open/read/write/seek/close
operations with a small stream interface or narrowly guarded calls. Complete
function duplication would duplicate save-format and post-load behavior.

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

`do_vga_smacked_anim` and `do_svga_smacked_anim` warrant complete portable
bodies. Their game-visible filename and skip behavior remains, while VGA mode
switching and graphics-buffer destruction do not.

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
state.

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

A no-op replacement is not acceptable: it turns these paths into CPU-burning
spins. They must wait on a condition, timer, or engine-thread scheduling
primitive.

## Audio services

Keep music mood and ambient policy in the engine:

- `get_city_mood`, `get_battle_mood`, `get_old_mood`;
- `choose_odd_tune` and `sooth_mood`;
- ambient event selection and delay logic; and
- the city, province, and battle ambient tables.

Replace Miles driver startup, voice allocation, sample status, speech
streaming, sequence control, and handle management behind the existing public
sound API. `continue_db` remains callable even if a modern streaming backend
does not require per-frame service.

XMI music is not merely file playback. Miles invokes `mood_modfication` at a
sequence marker; the engine calculates a new mood and requests a numbered
branch. The portable music service therefore needs marker callbacks and a
branch operation in addition to open, play, volume, and stop.

Music is intentionally unavailable in the current port. The host reports
that fact through `C2_HOST_CAPABILITY_MUSIC`; callers must skip optional music
rather than link a placeholder decoder or pretend playback succeeded.

## Movie services

Retain `start_smacking`, `continue_smacking`, `stop_smacking`, and
`are_smacking` as the engine-facing API, with complete portable bodies. This
surface covers both full-screen cinematics and movies embedded in message
dialogs. Prefer decoding into the indexed framebuffer and palette model so
movie playback does not impose a second renderer on the engine.

Video is intentionally unavailable in the current port and reported as
such through `C2_HOST_CAPABILITY_VIDEO`. Startup therefore omits `INTRO.SMK`.
The capability is the temporary boundary; a decoder API should be designed
when a concrete media library and the embedded-message movie path are brought
up together.

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
