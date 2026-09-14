# Save format

The port writes its own save format and reads both it and the original one.
This document is the specification and the description of the code that
implements it. The schema, `src/platform/common/c2_save.fbs`, is the
authoritative field reference; this page explains what is in it and why.

## Summary

| | Original (version 0) | Port (version 1) |
| --- | --- | --- |
| Container | positional raw dump of `savegame_entries` | FlatBuffer, root `c2.save.Save`, plus CRC32 trailer |
| Identity | none | file identifier `C2SV` at offset 4; `format_version` field |
| Size | fixed 225,745 bytes | variable (about 220-270 KB) |
| Integrity | none | FlatBuffers verifier for structure, CRC32 for content |
| Field identity | implied by registry order | named fields and vectors |
| Pointers | two per battle figure, one per missile, written as 0/1 markers | none |
| Derived state | stored (tile occupancy, history ring indices) | rebuilt on load |
| Walker index width | 8 bits (pool of 254 at most) | 16 bits |
| Indices on load | used unchecked | bounded; reject or clear per reference |
| Commit | block by block into live state while reading | staging image first, live state only after every check |
| Write | truncate in place | temporary file, then rename |
| `history.dat` | separate ring file, rewritten monthly | folded in; no file |
| Written by | original DOS/Windows executables, and the port before this format | the port only |
| Read by the original executables | yes | no |

The port never writes version 0. A save written by the port cannot be opened
by the 1995 executables; an original save opens in the port as before.

## Why the original layout was replaced

`savegame()` and `loadgame()` (`src/loadsave.c`) walk a 500-entry table of
`{pointer, size}` pairs and copy the bytes in order. Three properties of that
made it a dead end for the port:

- **Positional identity.** Every offset is implied by the table order and the
  block sizes before it. `figure_list` starts at byte 20,202 because that is
  how many bytes precede it. Growing any array shifts every later block, so
  engine limits such as the walker pool could not change.
- **Not memory safe.** Indices are stored raw and used unchecked. An
  `army_rec.cohort_id` from the file indexes the ten-entry `army_routes` and is
  written through (`src/int_c2.c:721`). Battle records store the engine's
  sprite-data pointers; the port's loader read them back as a fabricated
  `(void *)1` that stayed in live state until the battle view happened to
  rebuild it.
- **Not atomic in either direction.** Blocks were copied into live globals
  while reading, so a failure halfway left the engine spliced; the writer
  truncated the target first, so a crash mid-save destroyed the slot.

And the 8-bit walker indices in the 20-byte city cell -- a raw image in the
file -- capped the walker pool at 254, which is the limit behind the
long-standing "markets stop sending traders in a big city" report.

## Architecture

```
 recovered engine (src/*.c)                 portable layer (src/platform/common/)
 ┌──────────────────────────────┐          ┌──────────────────────────────────────┐
 │ loadsave.c  savegame/loadgame│──calls──▶│ c2_port_save.c        engine adapter │
 │ battle.c    sprite rebuild   │          │   capture: globals ──▶ image          │
 │ evolver.c, int_c2.c, map.c,  │          │   commit:  image   ──▶ globals        │
 │ common.c, screens.c ...      │          │   history ring, atomic write          │
 │   PORT_CELL_CITIZEN_A/B(off) │          ├──────────────────────────────────────┤
 │   PORT_CELL_ENVOY(off)       │──reads──▶│ c2_port_citizen_index.c  side tables │
 │   PORT_CITIZEN_TARGET(i)     │          │   uint16 per cell / per citizen       │
 └──────────────────────────────┘          ├──────────────────────────────────────┤
                                           │ c2_save_v1.c            format core  │
                                           │   image ◀──▶ FlatBuffer (+CRC)        │
                                           │   validation, legacy import, diff     │
                                           │   knows no engine globals            │
                                           ├──────────────────────────────────────┤
                                           │ c2_save_gen/   generated accessors   │
                                           │ third_party/flatcc   runtime         │
                                           └──────────────────────────────────────┘
                                                              │
                                                     c2_host_user_file_*
```

Three layers, each testable on its own:

1. **Format core** (`c2_save_v1.c`): pure data. It translates between a
   *staging image* (`struct c2_save_image`: every block in the engine's own
   byte layout plus the wide references) and the FlatBuffer, runs validation,
   and imports the original layout into the same image. It receives the
   registry and a table of block addresses as arguments and never touches
   globals, so `tests/c2_port_save_test.c` exercises it with synthetic state.
2. **Engine adapter** (`c2_port_save.c`): the only code that knows the
   engine's globals. `capture` fills an image from them; `commit` writes an
   image into them and rebuilds derived state. It owns the in-memory history
   ring and the file I/O, and keeps the entry points `loadsave.c` calls:
   `c2_port_save_game_state`, `c2_port_load_game_state`,
   `c2_port_save_state_file_matches`.
3. **Side tables** (`c2_port_citizen_index.c`, `include/c2_citizen_index.h`):
   the 16-bit walker references the engine reads through macros. See "Wide
   walker indices" below.

The generated accessors and the FlatBuffers runtime sit below all three.

## The file

```
offset 0      FlatBuffer  (root table c2.save.Save, file identifier "C2SV")
offset N-4    uint32 LE   CRC32 (IEEE, as zlib) of bytes [0, N-4)
```

Detection (`c2_save_detect`): `C2SV` at offset 4 is a container; exactly
225,745 bytes without it is an original file; anything else is refused.

### Root table `Save`

| field | type | notes |
| --- | --- | --- |
| `format_version` | `uint` | 1. Readers accept 1..current; the writer always emits current. |
| `engine_version` | `string` | informational |
| `scalars` | `[ubyte]` | every registry entry not carried by a vector below, in registry order, concatenated |
| `city_map` | `[CityCell]` | 6,400 cells, row-major 80 x 80 |
| `region_map` | `[ubyte]` | 3,600 x 8-byte `struct region_cell` |
| `battle_map` | `[ubyte]` | 2,704 x 4-byte `struct battle_cell` |
| `citizens` | `[Citizen]` | pool + 1 entries; slot 0 is the sentinel |
| `armies` | `[ubyte]` | 26 x 175-byte `struct army_rec` |
| `army_routes` | `[ubyte]` | 10 x 346-byte `struct army_route_rec` |
| `units` | `[ubyte]` | 51 x 78-byte `struct unit_rec` |
| `figures` | `[ubyte]` | 201 x 80 bytes: `struct figure_rec` without its two pointers |
| `figure_secondary_sprite` | `[bool]` | 201: whether the figure's secondary sprite is in use |
| `arrows` | `[ubyte]` | 201 x 41 bytes: `struct arrow_rec` without its pointer |
| `messages` | `[ubyte]` | 16 x 8-byte `struct msg_slot` |
| `fire_zones` | `[ubyte]` | 100 |
| `industry` | `[ubyte]` | 16 x 48-byte `struct industry_rec` |
| `slave_requirements` | `[ubyte]` | 8 x 8-byte `struct slave_req` |
| `history` | `[HistorySample]` | up to 200, oldest first |

Required on load: `scalars`, `city_map`, `region_map`, `citizens`, `history`.
Every other vector is optional and zero-filled when absent, which is the
legitimate state outside a battle.

### `CityCell` (struct, 20 bytes in the engine)

The engine's `struct city_cell_fields` (`include/entities.h`) field for field,
with two changes: `citizen_a` and `citizen_b` (who stands on the tile) are not
stored, and `envoy:ushort` carries the market or business's current walker,
which the engine keeps in the `industrial` byte. `industrial` itself is kept
because on wall cells the same byte is a trample counter.

### `Citizen` (struct, 58 bytes in the engine)

`struct citizen_rec` field for field, except: the three byte ranges the engine
never reads (`+0x1C..0x1D`, `+0x25`, `+0x37..0x39`) are not stored, and
`target_kind` (the walker a fighter is chasing, one byte) is stored as
`target:ushort`.

### `HistorySample`

The five values `evolver.c` samples each month -- population, denarii,
population tax, industry tax, year -- oldest first. The engine's ring is a
200-slot array with a next-write index; on load the samples are placed at
slots `0..n-1` and `history_end_ptr = n % 200`, `history_entries = n`,
`history_start_ptr = 0`. Only `history_end_ptr` is ever read by the graph
screens, so this reproduces identical output. `history_start_ptr` and
`history_entries` are write-only in the engine.

### Byte-image vectors

`armies`, `army_routes`, `units`, `region_map`, `battle_map`, `messages`,
`industry`, `slave_requirements` and `scalars` are the engine's records as it
holds them: one-byte packed, little-endian, no padding, no pointers, with
sizes pinned by the `_Static_assert` block in
`src/platform/common/c2_port_save_compat.c`. They are documented per record
in `include/entities.h`. Giving them individual fields is an additive schema
change (a new vector of structs, the byte vector deprecated) and is the
intended next revision; version 1 carries them as images so that no record
had to be transcribed by hand into the schema before a single field of it was
needed.

`scalars` has a stronger caveat: its layout is that of the *writing build's*
registry. A reader whose registry contributes a different byte count refuses
the file (`C2_SAVE_ERR_REGISTRY`). That is deliberate for version 1 -- the
registry has not changed since the original -- and is the first thing a
version 2 should replace with named fields.

## Versioning

One number, `format_version`, monotonic. The reader accepts every version from
1 up to the one it was built with and refuses newer ones. The writer always
emits the current version, so there is no forward-compatibility burden;
loading an older version means applying that version's defaults, which
FlatBuffers does per field. Fields are only ever added (with defaults) or
deprecated, never renumbered or retyped.

The original layout is pseudo-version 0: read by `c2_save_import_legacy`
through the same image, validation and commit path as a container, never
written.

## Loading

1. Read the whole file (`c2_host_user_file_read`).
2. Detect the layout.
3. Container: check the CRC32 trailer; run the FlatBuffers verifier
   (`c2_save_Save_verify_as_root_with_identifier`), which bounds-checks every
   offset before any accessor is used; check `format_version`; copy each vector
   into the staging image, refusing wrong lengths. Original: walk the registry
   over the 221,745 state bytes into the same image, widening the byte
   references, lifting envoys out of the cell bytes, dropping the pointer
   markers and keeping the one bit they carried, and linearising the history
   ring from the 4,000-byte tail.
4. Validate (`c2_save_validate`), see below.
5. Commit: copy the image into the globals, set every figure and arrow pointer
   to `NULL`, store the wide references in the side tables, rebuild tile
   occupancy from the citizen records (a third walker on one tile cannot
   exist and is removed), fill the history ring.

Nothing in step 5 runs unless steps 3 and 4 succeeded, so a bad file leaves
the running game untouched. `c2_port_save_last_error()` names the reason.

### Validation

Every reference in the image has a declared domain. `reject` fails the load;
`clear` zeroes the reference, counts it, and continues.

| reference | rule | policy |
| --- | --- | --- |
| `CityCell.envoy` | 0, or below the pool size; only on market/business cells | clear |
| `Citizen.map_ref` (live walker) | below 128,000 and a multiple of 20 | reject |
| `Citizen.target_ref` | 0, or as `map_ref` | clear |
| `Citizen.target` | 0, or below the pool size | clear |
| citizen slot 0 | must be empty | reject |
| `army_rec.cohort_id` (live army) | 0..9: it indexes `army_routes[10]` and is written through | reject |
| `army_route_rec.target_army` | low word 0..25 | clear |
| history sample count | at most 200 | reject |
| `citizens` beyond the compiled pool | dropped, counted, logged | clamp |

Derived bytes are normalised in the same pass: cell bytes +7/+8 (occupancy)
and, on market/business cells, +0x12 (envoy) are zeroed, as is the narrow
`target_kind` byte of every citizen record. Validation runs on decoded and on
captured images alike, so the debug verifier compares like for like.

## Saving

`capture` builds an image from the globals, validation normalises it,
`c2_save_encode` builds the FlatBuffer and appends the CRC. The bytes go to
`<name>.tmp` and are renamed over the target (`c2_host_user_file_rename`); if
the host cannot rename, the temporary file is removed and the target is
written in place as before.

## Wide walker indices

The recovered engine keeps every walker index in a byte: `city_cell.citizen_a`
and `citizen_b` (who stands on the tile), `city_cell.industrial` on market and
business cells (the walker it last sent out), and `citizen_rec.target_kind`
(the walker a fighter is chasing). The 20-byte cell is addressed by raw byte
offset throughout the engine and is a raw image in the original file, so none
of these can grow in place. With `create_citizen` refusing when the 200-slot
pool is full, a city with more walker-producing buildings than that has
buildings that never get served -- and the byte fields cap any raise at 254.

`PORT_FEAT_WIDE_CITIZEN_INDEX` (on for the portable target) moves the three
references into `unsigned short` side tables (`c2_cell_citizen_a`,
`c2_cell_citizen_b`, `c2_cell_envoy`, `c2_citizen_target`) and sets the pool to
`PORT_CITIZEN_POOL`, a CMake cache value defaulting to 1000. Every recovered
access goes through four macros in `include/c2_citizen_index.h`:

```c
PORT_CELL_CITIZEN_A(off)   PORT_CELL_CITIZEN_B(off)
PORT_CELL_ENVOY(off)       PORT_CITIZEN_TARGET(i)
PORT_CITIZEN_CAST(x)       /* the byte narrowing the recovered code applied */
PORT_CITIZEN_SLOTS         /* pool + 1; the six loop bounds and the array */
```

With the feature off they expand to the original cell and record bytes and to
`(unsigned char)`, so the retained DOS and Windows builds keep their exact
text. Two narrow holders outside the cell are widened under the same flag:
`city_test_for_road`'s `road_list` (a `char` array that would fold index 256
to "nobody here") and the query panel's occupant list, which gets a wide twin
so the forty per-unit data headers declaring the byte array stay untouched.

A larger pool adds no walkers: each building dispatches on the same schedule
and each walker lives as long as before, so below saturation the game is
identical to the original. The pool only decides when dispatch *fails*. The
number is a cap, not a driver. Each forum, prefecture, barracks, market and
business holds between one and three walkers at a time (dispatch interval
against walker lifetime), so demand is a small multiple of the number of
such buildings; 1000 leaves that far below the cap on an 80 x 80 map and is a
CMake cache value that can be raised to 65,534.

Persistence follows from the format: `Citizen.target` and `CityCell.envoy`
are 16-bit, the `citizens` vector has as many entries as the writing build's
pool, and a reader with a smaller pool keeps the first entries and drops the
rest, clearing any reference to a dropped walker. Occupancy is not stored at
all; `commit` rebuilds it.

## History

`history.dat` no longer exists on the portable target. The 200-sample ring
lives in memory (`c2_port_history_*` in the adapter), `save_history()` writes
into it, `get_history_in_buffer()` reads from it, and it travels inside the
save. It is per-city state -- `new_province()` resets it -- so this also
removes the original's side effect that two instances sharing one file
interleaved their rings. The DOS and Windows targets keep the original file
I/O unchanged. An old `history.dat` in the user-data directory is ignored.

## Not carried over

Artifacts of the original table rather than of game state, which the
translation simply does not reproduce:

| original | what it was | now |
| --- | --- | --- |
| `{ &zoom_level, 1 }` written twice | the same byte twice | inside `scalars`, still twice, harmless |
| `{ message_list, 64 }` and `{ message_list, 128 }` | a partial alias of the same 16 slots | `messages`, once |
| `(char *)&c2inf + 52`, `+ 53` | `skill_level`, `peace_mode` | inside `scalars` (named fields are version 2 work) |
| `restore_window_positions`, `savegame_version = 999` | Windows-build window geometry | not stored |

## Tooling

- `tools/regen-save-schema.sh` regenerates `src/platform/common/c2_save_gen/`
  from the schema with the `flatcc` compiler. Run it inside `nix develop`:
  `flake.nix` pins `flatcc` to the latest release independently of the
  nixpkgs lock, the bundled runtime is that same version, and the generated
  text differs between versions. `tests/test_save_schema.py` checks the three
  agree, and compares against a `flatcc` on the path only when it is that
  version. Bump all three together.
- The FlatBuffers runtime is bundled under `third_party/flatcc/` (see
  `third_party/README.md` for why); the compiler is a development tool only.
- `flatcc --json` can print or parse a save's FlatBuffer body for inspection
  once the 4-byte trailer is stripped.

## Testing

`tests/c2_port_save_test.c` (core, synthetic state): lossless round trip with
700 walkers; a 201-slot reader dropping the tail and clearing references to
it; import of an original-layout file with stale occupancy, envoy bytes,
pointer markers and a wrapped history ring; import-save-load idempotence; a
negative corpus (truncation, a flipped bit, a forged CRC over a damaged
container, wrong identifier, not a save, a future version); and every
reject/clear rule. `tests/c2_save_compat_test.c` pins the original-layout
constants and, with `C2_TEST_SAVE_FIXTURE`, that an original file is detected
as such.

`recovered-save-load-smoke` drives the actual engine: it saves through the
recovered dialog, reloads, and compares the live state against the file
semantically (`c2_port_save_state_file_matches`, which captures the live
state, loads the file into a second image, and diffs the two). It passes with
`PORT_FEAT_WIDE_CITIZEN_INDEX` on and off. See `docs/save-testing.md`.
