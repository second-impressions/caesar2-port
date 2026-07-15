# Caesar II ImHex patterns

ImHex pattern-language descriptions of Caesar II's **own** file formats, each
verified against the current decompiled loaders (and, where available, real
sample files).  Third-party formats (Miles AIL audio `.wav/.voc/.xmi/.dig`,
RAD Smacker `.smk`, raw audio `.raw`) are out of scope.

| pattern | describes | size |
|---|---|---|
| `caesar2_savegame.hexpat` | a `*.SAV` save game | **225,745 bytes** (fixed) |
| `caesar2_history.hexpat`  | `history.dat` (also the trailing 4000 b of every save) | **4,000 bytes** (fixed) |
| `caesar2_pl8.hexpat`      | `.PL8` sprite/image container | variable |
| `caesar2_256.hexpat`      | `.256` VGA palette | 768 bytes |
| `caesar2_textfile.hexpat` | `Textfile` UI strings (`C2.ENG/GER/FRE/SPA`) | variable |
| `caesar2_helpfile.hexpat` | `Helpfile` on-line help (`HELP.ENG/...`) | variable |
| `caesar2_regions.hexpat`  | `REGIONS.DAT` province tile grids | N x 3600 |
| `caesar2_inf.hexpat`      | `CAESAR2.INF` options block | 64 bytes |
| `caesar2_gd8.hexpat`      | `FORUM_X.GD8` forum dept pick map | N x 80 |
| `caesar2_lbm.hexpat`      | `.LBM` screenshots (standard IFF `PBM `) | variable |
| `caesar2_model.hexpat`    | `C2MODEL.DAT` game-balance tuning tables | 4,360 bytes |
| `includes/caesar2_common.hexpat` | shared types (`VgaColor`, `TileCode`) | (include) |

The prose format specs the patterns were derived from (`pl8-format.md`,
`textfile-format.md`, `helpfile-format.md`, `regions-dat-format.md`,
`inf-format.md`, `cell-bitfields.md`, …) were retired with the rest of the
burn-down docs; find them in git history (≤ 2026-07-15) under `docs/`.

> **`C2MODEL.DAT`** *does* ship on the CD (4,360 bytes = the `model_entries` tuning
> tables) and is patterned above — but the game never loads it (`loadmodel` has zero
> callers; `"c2model.dat"` is absent from the binary), and 11 of its blocks differ from
> the baked-in EXE defaults.  (Spec: `docs/model-dat-format.md` in git history.)

## Not patterned (considered, but no real format)

- **`cd.dat`** — a CD-presence **sentinel**: the game only `open()`s it and checks the
  result (`c2.c` — missing ⇒ error 4); its content is never read. No format.

## Shared includes

`includes/caesar2_common.hexpat` holds types used by more than one pattern
(`HistoryRow`, `VgaColor`, the `TileCode` enum).  ImHex resolves
`#include <caesar2_common.hexpat>` from the `includes/` sub-folder of a
**pattern search path**, so add `tools/imhex/` to ImHex's folders once
(Settings -> Folders, or `Extras -> Folders`).  `caesar2_savegame`,
`caesar2_history`, `caesar2_256` and `caesar2_regions` use it; the rest are
self-contained.

## Format in one paragraph

`savegame()` dumps the 500-entry `savegame_entries[]` table verbatim — each
entry is an in-memory global written `size` bytes wide, in table order — for
221,745 bytes of state, then appends the 4,000-byte `history.dat` ring buffer
(200 rows × 5 ints: population, denarii, pop-tax, ind-tax, year). `loadgame()`
is the exact inverse. There is no header, magic, version or checksum.

Every record struct is **fully expanded** from `include/entities.h`
with each field named — there is no `rest[]` catch-all.

The structs are **byte-packed** (Watcom `pack(1)`): multi-byte fields sit at
non-naturally-aligned offsets (e.g. `army_rec.home_ref`, an `int`, at +0xA3),
so the compiler inserts **no alignment padding**.  That means a gap is never
padding — it is a real source-declared field that simply turned out to be
unused.  Such **dead/vestigial fields are kept as named fields** (their
`entities.h` names, e.g. `_unk1F`, `_reserved50`, `_unk08`) tagged
`[[color("707070"), comment("dead field ...")]]` — *not* `padding[N]`, which in
ImHex means structural/alignment padding and would mislabel them.  ImHex has
no dedicated dead-field marker; named-field-plus-attributes is the idiomatic
way (official patterns likewise use a plain `reserved` field for such bytes).
The "dead" status is *proven*: a whole-binary disassembly scan for
`arrow_rec`/`province_industry`/`mercs_class`, and the two-build Mac
cross-check for `figure`/`citizen`/`unit`/`army_rec` (see
`docs/mac-deadfield-crosscheck.md` in git history).

One faithful quirk is modelled explicitly: the `province_industries` symbol is
only 8 records (128 B), but its save entry is `{ province_industries, 256 }`,
so the block over-reads 128 B into the adjacent `industry[]` (which the next
entry then re-saves — the same double-store as the duplicated `message_list`).
The pattern shows `ProvinceIndustry[8]` followed by a labelled
`_industry_overshoot[128]`.

## Validation

`validate_savegame.py <file-or-dir>` parses saves directly from the recovered
offsets and checks internal consistency. It was run against 41 real save files
pulled off the web (the `CAESAR2PROVINCES` pack of 40 starter provinces +
a `CHEATER.SAV`):

* **41 / 41** were exactly 225,745 bytes.
* every recovered scalar offset decoded to a plausible value (year as a signed
  BC/AD int, tax rates 0–100, the two denarii mirrors `denarii` /
  `this_years_denarii` agreeing on fresh saves);
* the big-array strides are correct (clean `exists`-byte counts; `armenia.sav`
  has 10 citizens clustered in one map district);
* `armenia.sav` (a populated mid-game city) decoded a 13-row history ring of
  **consecutive years 303–315** with monotonic population growth ending at
  **1905 — exactly equal to the live `population` field**, and a last history
  year (315) equal to the live `year` field. Two independent regions of the
  file agree to the byte.

The published hex cheats line up too: offset `0x329EC` = `denarii`,
`0x35FCC` = `this_years_denarii` (see `src/loadsave.c`).
