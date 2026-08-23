# Mutable user data

## Ownership

The portable target has two deliberately disjoint filesystem namespaces:

- `--asset-root` contains read-only installed/CD resources; and
- `--user-data-dir` contains every file created or changed by the game.

Without an override, SDL selects the platform preference directory for
`second-impressions/caesar2`. On WebAssembly, a storage pthread mounts WasmFS
OPFS and selects `/persistent/user-data`; imported assets use the separate
`/persistent/game-data` namespace. The engine never falls back from one
namespace to the other. This keeps an installed game tree read-only and gives the
browser one persistent mount to synchronize.

The mutable files currently supported by the recovered engine are:

| File | Purpose |
| --- | --- |
| `*.sav`, including `lastyear.sav` | manual saves and yearly autosaves |
| `history.dat` | 200 five-value history rows used by the current game |
| `caesar2.inf` | 64-byte preferences and career block |
| `shot1.png` through `shot8.png` | portable screenshot hotkeys |
| a `--screenshot` filename | portable diagnostic PNG output |

`loadmodel` and the streamed speech database remain asset reads. DOS CD-drive
probing is not a user-data operation.

## Host boundary

The shared engine keeps its recovered save ordering, post-load repair, history
ring, and dialogs. The host boundary provides:

- whole-file and offset reads/writes for preferences, history, and complete
  validated save streams;
- lossless PNG encoding from the read-only indexed frame and VGA palette;
- existence checks in the mutable namespace; and
- bounded wildcard enumeration for the recovered `char directory[100][13]`
  save picker.

The SDL implementation rejects absolute paths, drive prefixes, and `..` path
components. Flat runtime filenames are resolved case-insensitively so a save
created as `ROME.SAV` can be read or overwritten as `rome.sav` on Linux.
Save-list results are sorted case-insensitively and exposed in DOS-style upper
case for deterministic recovered-UI behavior. Entries which cannot fit the
original 8.3-style 13-byte row are omitted.

Portable screenshot encoding is implemented by the SDL backend and requires
SDL 3.4 or newer. The recovered DOS and Windows targets retain their original
LBM writer and `shotN.lbm` names; only the portable feature branch uses PNG.

The engine worker uses these synchronous operations. In the browser, OPFS is
mounted before SDL host initialization. Successful writes are flushed before
the save operation completes; the recovered save code does not become
asynchronous. The page exposes all `*.sav` plus `history.dat` as downloads and
can produce a local store-only ZIP; `caesar2.inf` is an optional settings/career
export.

Portable save serialization is owned by `src/platform/common`. The recovered
registry contains exactly 500 live entries rather than a shorter list followed
by a zero sentinel; the portable validator accepts either representation only
when its blocks total the original 221,745-byte state payload. Loading first
reads and validates the complete 225,745-byte file and writes its history
sidecar before applying any state blocks, so a truncated or oversized file
cannot leave the running engine partially deserialized. The recovered DOS and
Windows file-descriptor implementations remain unchanged.

## Save compatibility

The original save is a fixed 225,745-byte stream: 221,745 bytes of registered
state blocks followed by the 4,000-byte history file. The portable target
retains that ordering and size.

Watcom used one-byte packing for engine records. Portable engine structures
therefore use scoped one-byte packing, with compile-time checks on every
structured record present in the save registry. Most registered blocks can
then be transferred unchanged.

`figure_rec` and `arrow_rec` are the exceptions. Their runtime forms contain
native pointers so they can safely run on 64-bit hosts, while the file format
has 32-bit process-local image-pointer slots. `c2_save_compat` packs and
unpacks those two arrays explicitly. Pointer values are not durable game
state: each non-null pointer is written as the little-endian marker `1`, read
as a temporary non-null marker, and rebound to the graphics loaded for the
current battle before use. Every other byte remains unchanged.

Unity tests cover the native-pointer conversion, normalized byte-for-byte
round trips, host stream behavior, case-insensitive overwrite, and save-list
enumeration. The optional `C2_TEST_SAVE_FIXTURE` CMake path enables the same
round-trip check against an original 225,745-byte save without committing
copyrighted game data. A Debug-only semantic smoke test additionally drives
the recovered filename editor, save action, state mutation, load action, and
city-loop re-entry through ordinary host input. It checks the file through the
user-data service and verifies that the loaded province and view state match
the state observed at save completion.

Portable extensions must not be appended silently to this format. If new
state becomes necessary, introduce an explicitly versioned container or
sidecar while continuing to accept the original stream.
