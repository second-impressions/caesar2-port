# Caesar II `REGIONS.DAT` Format

> ImHex pattern: [`tools/imhex/caesar2_regions.hexpat`](../tools/imhex/caesar2_regions.hexpat).

## Overview

`REGIONS.DAT` holds the **province region maps** — the 60×60 terrain grid for each
playable province (the map you see at the province/region level). It is the simplest
Caesar II data file: a **flat array of fixed-size tile-code grids with no header**.

## Layout

```
Offset            Size      Description
------            ----      -----------
province * 0xe10  0xe10     One province grid: 60 rows × 60 cols, 1 byte per tile
                            (3600 bytes, row-major [y][x])
```

- Each province occupies exactly **3600 bytes** (`0xe10` = 60 × 60).
- Provinces are packed back-to-back; there is **no file header** and no per-province
  header.
- Retail `REGIONS.DAT` is **158,400 bytes = 44 provinces × 3600**.

## Loading

`load_region_map(province)` (`loadsave.c`) computes the byte offset as `province * 3600`
(via the shift chain `((province*8 − province)*32 + province)*16`) and reads one grid:

```c
readfile("regions.dat", scratch_buffer, 0xe10, province * 3600);
```

It then walks the grid `y = 0..59`, `x = 0..59` and expands each 1-byte **tile code**
into a `region_cell` record via `put_rm_area`, which sets the cell's `base_kind`, `gfx`,
and `terrain` category bits.

## Tile Codes

The byte at `[y][x]` is a tile code interpreted by `load_region_map`:

| Code range | Meaning | region_cell.terrain flags |
|------------|---------|----------------------------|
| `0x00`–`0x17` | sea / water (`load_region_map` catch-all `else`; `0x10`-`0x17` common) | `0` |
| `0x18`–`0x1b` | special terrain | `0x40` |
| `0x1c`–`0x1f` | special terrain | `0x80` |
| `0x20`–`0x7b` | land / decorative terrain tile (gfx = code) | `0x18` |
| `0x7d`–`0x84` | structure, 1×1 | `0x10` |
| `0x85`–`0x8c` | structure, 2×2 | `0x10` |
| `0x8d`–`0x90` | structure, 3×3 | `0x10` |
| `0x91` | structure, 4×4 | `0x10` |
| `0x92` | city (2×2) | `0x01` |
| `0x93`–`0x97` | huts (kinds 2,3,4,5,1) | `0x01` |
| `0x98` / `0x9c` | province border / trade-route marker | — |

See [`cell-bitfields.md`](cell-bitfields.md) for the `region_cell.terrain` bits these
codes produce. The structure codes (`0x7d`+) place multi-cell items whose size grows with
the code group; `put_rm_area` stamps the whole footprint.

## Verification

- Retail `REGIONS.DAT` size = 158,400 = 44 × 3600 (exact multiple). ✓
- Province 0 decodes to a coherent coastal province (sea tiles, a band of land, a city
  tile `0x92`, and hut tiles), matching the `load_region_map` code ranges. ✓
- Offset formula reduces to `province * 3600` exactly from the current decompiled shift
  chain. ✓

## Related Runtime Structures

The in-memory result of decoding one province is `region_map` — a 60×60 array of 8-byte
`region_cell` records (see `entities.h` and the `RegionCell` pattern in
[`caesar2_savegame.hexpat`](../tools/imhex/caesar2_savegame.hexpat)). `REGIONS.DAT` is the
*source* tile codes; `region_map` is the *expanded* runtime grid (and what a `.SAV` stores).
