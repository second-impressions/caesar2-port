# Mutable user data

## Ownership

The portable target has two deliberately disjoint filesystem namespaces:

- `--asset-root` contains read-only installed/CD resources; and
- `--user-data-dir` contains every file created or changed by the game.

Without an override, SDL selects the platform preference directory for
`second-impressions/caesar2`. The engine never falls back from one namespace
to the other. This keeps an installed game tree read-only and gives browser
ports one persistent mount to synchronize.

The mutable files currently supported by the recovered engine are:

| File | Purpose |
| --- | --- |
| `*.sav`, including `lastyear.sav` | manual saves and yearly autosaves |
| `history.dat` | 200 five-value history rows used by the current game |
| `caesar2.inf` | 64-byte preferences and career block |
| `shot1.lbm` through `shot8.lbm` | original screenshot hotkeys |
| a `--screenshot` filename | portable diagnostic PPM output |

`loadmodel` and the streamed speech database remain asset reads. DOS CD-drive
probing is not a user-data operation.

## Host boundary

The shared engine keeps its recovered save ordering, post-load repair, history
ring, dialogs, and screenshot construction. The host boundary provides:

- whole-file and offset reads/writes for small preference/history operations;
- sequential user-file streams for bulk saves and original LBM screenshots;
- existence checks in the mutable namespace; and
- bounded wildcard enumeration for the recovered `char directory[100][13]`
  save picker.

The SDL implementation rejects absolute paths, drive prefixes, and `..` path
components. Flat runtime filenames are resolved case-insensitively so a save
created as `ROME.SAV` can be read or overwritten as `rome.sav` on Linux.
Save-list results are sorted case-insensitively and exposed in DOS-style upper
case for deterministic recovered-UI behavior. Entries which cannot fit the
original 8.3-style 13-byte row are omitted.

The engine worker uses these synchronous operations. A future browser backend
must mount and synchronize its persistent store before starting that worker;
it does not need to make the recovered save code asynchronous.

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
copyrighted game data.

Portable extensions must not be appended silently to this format. If new
state becomes necessary, introduce an explicitly versioned container or
sidecar while continuing to accept the original stream.
