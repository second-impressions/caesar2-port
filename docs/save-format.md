# Save format

This document specifies the port's own save format and the rules for reading
the original one. It is a design document: nothing in `src/` implements it yet.

## Why replace the original layout

`savegame()` and `loadgame()` (`src/loadsave.c`) write and read a positional
raw dump driven by one table, `savegame_entries`, of `{void *buf, int size}`
pairs. The resulting file has no identity and no structure:

| Property | Original layout |
| --- | --- |
| Identity | none: no magic, no version, no checksum |
| Size | fixed 225,745 bytes (`C2_SAVE_STATE_SIZE` 221,745 plus 4,000 history) |
| Field identity | positional only; offsets are implied by table order |
| Layout | raw struct images, guarded by `_Static_assert` in `src/platform/common/c2_port_save_compat.c` |
| Pointers | three sprite-data fields, written as a 0/1 marker |
| History | separate `history.dat`, rewritten live every month |
| Atomicity | none; the write truncates the target in place |
| Validation | none; any byte pattern of the right length is accepted |

Three consequences matter in practice.

**Positional identity blocks engine changes.** `C2_SAVE_FIGURES_OFFSET` is
20,202 because everything before `figure_list` happens to occupy that many
bytes. Growing any array shifts every later block, so engine-side limits such
as the 200-slot citizen pool cannot be changed without breaking the format.

**The file is not memory safe.** Indices are stored raw and used unchecked.
`army_rec.cohort_id` is a `signed char` (`include/entities.h:388`) used directly
as an index into the ten-entry `army_routes` and written through
(`army_routes[...].chase_row = 0`, `src/int_c2.c:721`), so a corrupt file yields
an out-of-bounds write.

**Loading is not atomic in either direction.** `c2_port_load_game_state`
(`src/platform/common/c2_port_save.c:136-149`) copies blocks into live globals
as it iterates, so a failure halfway leaves the engine spliced; and
`c2_host_user_file_write` truncates the target, so a crash mid-save destroys the
slot being overwritten.

## Scope

- The port writes **one** format. There is no legacy writer and no hybrid
  output. Files written by the port cannot be opened by the original
  executables; this is accepted.
- The original layout stays **readable forever**, as a one-way importer.
- The shipped DOS and Windows targets keep their recovered `savegame()` and
  `loadgame()` verbatim. Everything here applies to `PORT_PLATFORM` builds.
- **No new player-visible features.** The format carries the state the original
  carries, plus the history data that was a side file. No metadata for the load
  dialog, no thumbnails, no compression, no autosave slots.
- The format describes **game state**, not engine memory. Both directions
  translate; nothing is a memory image.

## Principles

1. **Semantic, not positional.** Chunks are addressed by id, records by
   declared field, never by implied offset.
2. **No pointers.** Ever, in any chunk.
3. **No derived state.** Anything the engine can rebuild is rebuilt, not
   stored.
4. **Every index is bounded on read.** Decoding an index validates it against
   its declared domain; the decoder is the validator.
5. **Nothing reaches live globals until the whole file validates.**
6. **Little-endian, fixed widths.** All supported targets are little-endian;
   the build asserts it rather than pretending to be portable.

## Container

```
Header - 32 bytes
  0x00  magic           char[8]   "CAESAR2S"
  0x08  format_version  u32       single monotonic number, 1 for the first release
  0x0C  header_size     u16       32
  0x0E  chunk_count     u16
  0x10  total_size      u64       must equal the real file size
  0x18  engine_version  char[8]   informational only
  0x20  header_crc32    u32       over bytes 0x00-0x1B

Chunk - 20-byte header, payload padded to an 8-byte boundary
  0x00  id              char[8]
  0x08  payload_size    u32
  0x0C  record_count    u32       entity chunks; 0 for singleton chunks
  0x10  crc32           u32       over the payload
  0x14  payload
```

Chunks are order-independent. A duplicate id is a load failure. An unknown id
is skipped with a warning. A missing required chunk is a load failure.

### Versioning

One number, monotonic. Readers accept version 0 (the original layout, by
sniffing) through the current version. The writer always emits the current
version. Because the port never writes an older version, there is no
forward-compatibility burden: the only compatibility data needed is a table of
defaults to apply when loading a version older than the current one.

## Chunks

### Entity chunks

Each begins with `{u32 record_count, u16 record_size, u16 reserved}` and then
the records, each encoded field by field. The reader clamps `record_count` to
the compiled array bound, so an engine-side array change is a data change
rather than a format change.

| id | records (version 1) | source |
| --- | --- | --- |
| `CITIZENS` | 201 | `citizen_list` |
| `ARMIES  ` | 26 | `army_list` |
| `ARMYROUT` | 10 | `army_routes` |
| `UNITS   ` | 51 | `unit_list` |
| `FIGURES ` | 201 | `figure_list` |
| `ARROWS  ` | 201 | `arrow_list` |
| `MESSAGES` | 16 | `message_list` |

### Grid chunks

| id | cells | source |
| --- | --- | --- |
| `CITYMAP ` | 6,400 | `city_map`, 20 fields per cell |
| `REGIONMP` | 3,600 | `region_map`, 8 bytes per cell |
| `BATTLEMP` | 2,704 | `battle_map`, 4 bytes per cell |

### Singleton chunks

| id | contents |
| --- | --- |
| `GAMEINFO` | province, calendar, difficulty (`skill_level`), `peace_mode`, player name, rank, salary, tribute state |
| `CITYSTAT` | treasury, tax rates, employment rate, population, census accumulators, account and estimate ledgers, slave state, structure counters |
| `INDUSTRY` | province industry and warehouse records |
| `HISTORY ` | see below |

Required in version 1: `GAMEINFO`, `CITYSTAT`, `CITYMAP `, `REGIONMP`,
`CITIZENS`, `HISTORY `. The battle chunks and `MESSAGES` are optional; absent
means zeroed, which is the normal state outside a battle.

### Field enumeration

Field lists are derived mechanically from `include/entities.h`, whose records
are already fully annotated with offsets, signedness and meaning. The
`_Static_assert` block in `src/platform/common/c2_port_save_compat.c` is the
checklist of record types that must be covered:

```
citizen_rec 58   army_rec 175   unit_rec 78    army_route_rec 346
city_cell 20     region_cell 8  battle_cell 4  msg_slot 8
industry_rec 48  province_industry 16          slave_req 8
figure_rec / arrow_rec (88 / 45 on disk in the original layout)
```

Enumerating them is Phase 1 work and is deliberately not reproduced here; the
binding rule is that every field named in `entities.h` is either encoded
explicitly, or listed in "derived state" below with the function that rebuilds
it.

## History

`history.dat` becomes part of the save. It is per-city state, not a profile:
`new_province()` resets it through `setup_history_data()` (`src/c2.c:588`), and
the engine samples five values monthly (`src/evolver.c:335-340`):

```c
history_entry[0] = population;
history_entry[1] = denarii;
history_entry[2] = account_pop_tax;
history_entry[3] = account_ind_tax;
history_entry[4] = year;
```

200 samples at one per month is roughly 16.7 years, about one province. The
graph screens consume them (`src/screens.c:1979`, `2100`, `2147`).

Payload:

```
u32 sample_count
sample_count x { i32 population, i32 denarii, i32 pop_tax, i32 ind_tax, i32 year }   oldest first
```

No ring indices are stored. `history_start_ptr` and `history_entries` are
write-only in the engine - nothing reads them - and the graphs use only
`history_end_ptr`, walking backwards from it. On load the samples are written to
slots `0..count-1` and the engine state is set to `history_end_ptr = count % 200`,
`history_entries = min(count, 200)`, `history_start_ptr = 0`, which reproduces
identical graph output.

On the port target the ring lives in memory: `setup_history_data()`,
`save_history()` and `get_history_in_buffer()` operate on an array, which also
removes a per-month file write (a real saving on OPFS). The DOS and Windows
targets keep their file I/O unchanged. The shared `history.dat` currently has
the side effect that two concurrent instances interleave into one ring and that
a crash leaves the file describing a city you are no longer in; folding it in
removes both.

## Derived state, deliberately not stored

| State | Rebuilt by |
| --- | --- |
| `figure_rec.arrow_data_ptr`, `figure_rec.sprite_data_ptr`, `arrow_rec.arrow_data_ptr` | `rebuild_figures_image_data()` (`src/battle.c:1163`) from `sprite_kind` |
| `city_cell.citizen_a`, `city_cell.citizen_b` | `check_citizen_list()` (`src/common.c:422-452`) from the citizen records |
| `history_start_ptr`, `history_entries`, `history_end_ptr` | from `sample_count` on load |
| Window geometry, `savegame_version`, `restore_window_positions` | Windows-build UI artifacts (`src/loadsave.c:893-919`), not game state |

The three pointer fields are the only pointers in any saved structure. They
carry exactly one bit of information beyond `sprite_kind`: whether the secondary
sprite is in use, which the rebuild tests as `sprite_data_ptr != 0`. The format
stores that as an explicit `u8 secondary_sprite_active` per figure record.

On load both pointer fields are set to `NULL`. The original pack/unpack pair
writes a 0/1 marker and materialises `(void *)(uintptr_t)1`
(`src/platform/common/c2_port_save_compat.c:74`) - a fabricated, non-dereferenceable
pointer installed into live state that survives until the battle view runs the
rebuild, which is conditional (`src/action.c:4184`). `NULL` fails fast where the
sentinel corrupts silently.

Candidate for a later version, pending a resume test that proves the engine
recomputes them: normalising the transient render bits (`edge_bits` draw
markers, `range_flag` scratch markers) to zero. `docs/save-testing.md` already
notes that the original file carries whatever the last drawn frame left in them.

## Reference validation

Decoding bounds every index. `reject` fails the load; `clear` zeroes the
reference, logs, and continues.

| Reference | Rule | Policy |
| --- | --- | --- |
| `city_cell.industrial` (market or business envoy) | 0, or 1..citizen count; only on cells whose `base_kind` is 0xFA or 0xFC-0xFF, because on wall cells the same byte is a trample counter (`src/int_c2.c:1743`) | clear |
| `citizen_rec.target_kind` | 0, or 1..citizen count | clear |
| `citizen_rec.map_ref`, `citizen_rec.target_ref` | below 128,000 and a multiple of 20 | reject |
| `army_rec.cohort_id` | 0..route count - 1 | reject |
| `army_route_rec.target_army` | 0, or 1..army count | clear |
| `unit_rec.owner`, `figure_rec.owner` | within the owner enum | reject |
| `msg_slot.param` when it holds a cell reference | as `map_ref` above | clear |
| `fire_zones`, `top_lv_spot`, `pm_x`, `pm_y` | within grid bounds | reject |
| any `record_count` | at most the compiled array bound | clamp, log |

CRC32 catches accidental corruption; this table catches hostile files and files
produced by older engine defects. Neither substitutes for the other.

## Pipelines

### Load

1. Verify `header_crc32`, `magic`, `format_version`, `total_size` against the
   real file size.
2. Walk the chunk table; verify each `crc32`; reject duplicate ids.
3. Decode field by field into a **staging state image**, bounding every index
   as it is read.
4. Run the reference checks; apply `clear` policies; abort on `reject` with
   live state untouched.
5. Commit the staging image into the live globals.
6. Rebuild derived state: `NULL` sprite pointers, the history ring,
   `check_citizen_list()`.

### Save

Translate live state into records, encode into a buffer, write `name.tmp`,
flush, rename over the target. Atomic rename needs one host addition
(`c2_host_user_file_rename`); `include/c2_host.h` currently exposes read,
write, write-at, exists and list only.

### Legacy import (version 0)

Detected by a file of exactly 225,745 bytes with no magic at offset 0. The
existing positional reader decodes into the same staging image: the 221,745
byte state by the current table, the 4,000-byte tail as history samples, and
`secondary_sprite_active` synthesised from the old 0/1 pointer markers. It then
uses the same validation, commit and derivation path.

This importer is the only code that still knows about raw struct images,
`sizeof(void *)` and the original's positional offsets, so the existing
`_Static_assert` wall stays, scoped to it.

### Registry quirks are not carried over

The original table contains artifacts of being a positional dump rather than a
description of state. Under translation they simply disappear:

| Quirk | What it is | New format |
| --- | --- | --- |
| `{ &zoom_level, 1 }` twice (`src/loadsave.c:101-102`) | the same byte written twice | `zoom_level`, once |
| `{ message_list, 64 }` (`:271`) and `{ message_list, 128 }` (`:482`) | `message_list` is `struct msg_slot[16]` = 128 bytes (`src/c2_vars.c:34`); the 64-byte entry is a partial alias the 128-byte entry overwrites on load | the 16 message slots, once |
| `(char *)&c2inf + 52` (`:116`), `+ 53` (`:513`) | offsets 0x34 and 0x35 of `c2inf_rec`: `skill_level` and `peace_mode` (`include/entities.h:237-239`) | named fields in `GAMEINFO` |

## Testing

- **Round trip**: synthetic full state, save, load, compare every field of
  every record semantically.
- **Legacy conformance**: import `.sav` fixtures produced by `original/PS.EXE`
  and assert the expected state image. This validates the legacy path against
  the original rather than against our own encoder, which is stronger than the
  current byte-exact self-comparison.
- **Idempotence**: import legacy, save version 1, load it, and require the
  state to match the imported state. Catches asymmetric translation.
- **Negative corpus**: truncation, bad header CRC, bad chunk CRC, duplicate
  chunk, version above the current one, `record_count` beyond the compiled
  bound, `cohort_id` out of range, misaligned `map_ref`. Each must fail with
  live state provably untouched, asserted with a sentinel pattern in the
  globals.
- **Fuzzing**: loading is a single entry point over a byte buffer, so it is a
  natural libFuzzer target. Memory safety is a goal of this format, so this is
  part of the deliverable, not an extra.
- `docs/save-testing.md` needs rewriting: its "what is compared" contract
  describes byte-exact comparison against a repacked legacy image, and its
  history assumptions no longer hold on the port target. The
  `recovered-save-load-smoke` test and the Chromium and Firefox OPFS smokes
  assert on that message and must follow.

## Phases

1. Schema and codecs, staging image, container reader and writer, legacy
   importer rewired to the staging image. The port's legacy writer is deleted.
2. History in memory, `HISTORY ` chunk, `history.dat` retired on the port
   target.
3. Pointer elimination and omission of `city_cell.citizen_a`/`citizen_b`, with
   `check_citizen_list()` on load.
4. Atomic write and `c2_host_user_file_rename`.
