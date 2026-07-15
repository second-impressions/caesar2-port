# Map-cell flag bitfields

The map-cell structs (`city_cell`, `region_cell`, `battle_cell` in
`entities.h`) are byte-packed and carry no C bitfields — instead several
`unsigned char` fields are **flag/bitmask fields** whose individual bits the
code sets/tests by hand (`terrain & 0x20`, `fpu_flag & 0x30`, …).  This doc
decodes those bits from the actual masks used across `decomp/src`.

**Method.** Collect every `&` / `|` / `&=` / `|=` / `== mask` site on a field
(grouped by access macro so city/region/battle stay separate), then read the
surrounding logic of the clearest *writers* (placement, evolve, census,
map-gen) to assign each bit a meaning.  Confidence is HIGH where a writer sets
the bit and a reader gates a named behaviour on it.

---

## `city_cell.terrain` (+0x01) — placed-structure / feature bitfield  *(HIGH — DEFINITIVE)*

**Ground truth = the placement actions.**  Each `act_*` build tool sets a
global `placing_flags` that is OR'd straight into `terrain` at placement
(`map.c` `terrain |= placing_flags`), so the bit *is* the structure:

| bit | mask | structure | placement action (`placing_flags`) |
|----:|------|-----------|-------------------------------------|
| 0 | `0x01` | **building** (house, forum, temple, market, baths, hospital, barracks, prefecture, fountain, well, …) | `act_house*/forum/temple/market/…` = `1` |
| 1 | `0x02` | **wall** | `act_wall` = `2` |
| 2 | `0x04` | **tower** (and wall-gate where a wall crosses a road) | `act_tower` = `4` |
| 3 | `0x08` | natural water/river variant (impassable) | map-gen `\|= 8`; not a build tool |
| 4 | `0x10` | river / bridge tile | map-gen `\|= 0x10`; `bridge_count` sums neighbours |
| 5 | `0x20` | **road** | `act_road` = `0x20` |
| 6 | `0x40` | **aqueduct** | `act_aquaduct` = `0x40` |
| 7 | `0x80` | **reservoir** | `act_resevoir` = `0x80` |

Validated on `armenia.sav` (pop 1905, a walled city): 206 building, 51 wall,
13 tower, 178 river, 42 road, 0 aqueduct, **1 reservoir** — a coherent Roman
city.

> **Correction:** an earlier pass (commit bd786ee2) inferred this table from
> the *graphics/ramification* code and got it wrong (called 0x01 "solid",
> 0x02/0x04 "road", 0x20 "structure", 0x40/0x80 "wall").  The `placing_flags`
> assignments in `action.c` + the save-data counts are the corrected source.

**Composite masks (now consistent)**

| mask | bits | meaning |
|------|------|---------|
| `0x18` | 3,4 | natural water / river (the only bits *excluded* from build-occupancy) |
| `0xe7` | 0,1,2,5,6,7 (`~0x18`) | **any man-made structure — illegal to build** (`(t & 0xe7)!=0 → illegal`) |
| `0x8b` | 0,1,3,7 | **citizen cannot stand here**: building+wall+water+reservoir (`create_citizen`) |
| `0x54` | 2,4,6 | blocks a *roman* spawn: tower+river+aqueduct (`create_citizen`) |
| `0x20` | 5 | a *barbarian* spawns only on a road cell (`create_citizen`) |
| `0x06` | 1,2 | wall+tower (wall-graphic connectivity test) |
| `0xc0` | 6,7 | aqueduct+reservoir (water-network presence) |

`create_citizen`, now consistent:
```c
if ((citizen_a==0 || citizen_b==0) && (terrain & 0x8b) == 0) {   // not bldg/wall/water/reservoir
    if (is_barb) { if ((terrain & 0x20) == 0) return 0; }        // barbs spawn on roads
    else         { if ((terrain & 0x54) != 0) return 0; }        // romans avoid tower/river/aqueduct
```

---

## `city_cell.fpu_flag` (+0x0B) — fire / plague / unrest  *(HIGH)*

Cleanly nibble/2-bit packed: **`[fire:2][plague:2][unrest:4]`**.

| mask | bits | meaning | evidence |
|------|------|---------|----------|
| `0x0f` | 0-3 | unrest level (0..15) | `unrest = fpu_flag & 0xf`; `(fpu_flag & 0xf0) \| unrest` |
| `0x30` | 4-5 | plague / health (`==0x30` ⇒ plague) | `(fpu_flag & 0x30)==0x30 → plague_pass_count++`; `health = fpu_flag & 0x30` |
| `0xc0` | 6-7 | fire level (0..3) | preserved by `&= 0xc0` (map.c) and `&= 0xcf` (evolver clears only plague) |

---

## `city_cell.edge_bits` (+0x03) — edge / render bits  *(HIGH)*

| bit | mask | meaning | evidence |
|----:|------|---------|----------|
| 0 | `0x01` | on-road / has-citizen / needs-redraw | `create_citizen` + road/wall placement `\|= 1`; `pm_map` `&= 0xfe` per draw |
| 1 | `0x02` | drawn (render-pass) marker | `pm_map` `\|= 2` after consuming bit 0; `landfill & 2` |
| 2-4 | `0x1c` | wall/riverbank graphic **sub-kind** | `bank_kind = edge_bits & 0x1c` (pm_map1); written `&= 0xe3; \|= wall_gfxdat[…].edge_bits` |
| 5 | `0x20` | on water-network / web path | `web.c` `\|= 0x20` |
| 6 | `0x40` | graphic orientation flag | `map.c` `\|= 0x40` / `&= 0xbf` |
| 7 | `0x80` | draw-on-top / tall (wall, tower) | `(edge_bits & 0x80) → top_it()` in `pm_map1`; set for walls/towers |

---

## `region_cell.terrain` (+0x01) — tile-category bits  *(MED — category-encoded)*

Unlike city terrain, these are **tile-category bits** written by `put_rm_area`
from the `regions.dat` tile code (`terrain |= flags`), not independent flags.
`put_rm_area` treats both `0x10` and `0x01` as *placement blockers*
(`if (terrain & 0x10) return; if (terrain & 1) return;`).  Verified against
`armenia.sav`: most cells are `0` (sea), the land/feature cells are dominated
by `0x10` (421), `0x18` (73), `0x08` (56).

| bit | mask | meaning | evidence |
|----:|------|---------|----------|
| 0 | `0x01` | special placement-block: hut/border/city (also the `check_army_list` army-occupiable test) | `load_region_map` passes `flags=1`; `put_rm_area` `& 1 return` |
| 1 | `0x02` | out-of-walls marker | `web.c` `t & 2 → web_out_of_the_walls` |
| 2 | `0x04` | army-passable | `int_c2.c` army move-test `t & 4` |
| 3,4 | `0x18` | decorative land tile (codes 0x20-0x7c) | `load_region_map` `flags=0x18` |
| 4 | `0x10` | occupied / blocks region placement (structures + decor) | `put_rm_area` `& 0x10 return`; structure codes 0x7d-0x91 pass `flags=0x10` |
| 5 | `0x20` | structure present (placed at region level) | `map.c` `\|= 0x20` / `& 0x20 → next_cell` |
| 6 | `0x40` | terrain category (codes 0x18-0x1b) | `load_region_map` `flags=0x40` |
| 7 | `0x80` | terrain category (codes 0x1c-0x1f) | `load_region_map` `flags=0x80` |

Composites seen as readers: `0x25` (b0,2,5) web connectivity; `0x17`
(b0,1,2,4) map-gen strict reject.  The exact decorative-subtype split between
`0x10` and `0x18` is not fully separated.

## `region_cell.edge_bits` (+0x03)  *(HIGH)*

Nailed by the `get_region_query_info` panel in `screens.c` (q_* legend).

| bit | mask | meaning | evidence |
|----:|------|---------|----------|
| 0 | `0x01` | has-army / has-citizen | `common.c` create-army/citizen `\|= 1` |
| 1 | `0x02` | overlay / processed | `landfill`/`pm_map2` `& 2`, `\|= 2` |
| 5 | `0x20` | road | `q_road = edge_bits & 0x20`; `web.c` `\|= 0x20` |
| 6 | `0x40` | had-goods | `q_had_goods = edge_bits & 0x40` |
| 7 | `0x80` | placement marker | `action.c` `\|= 0x80` |

## `region_cell.outside` (+0x06)  *(HIGH)* — single flag

Only bit 6 is ever used: **`0x40` = outside-of-walls** (`q_outside`; `web.c`
sets/clears it). The other bits are unused.

## `region_cell.occupant` (+0x07) — context-dependent packed byte  *(HIGH, overloaded)*

The byte's meaning depends on the cell's `base_kind` (union-like); the same
bits are reused per cell type.  Documented interpretations:

| view | mask | meaning | evidence |
|------|------|---------|----------|
| warehouse | `0x0f` | warehouse fill level | `q_wh_level = occupant & 0xf` |
| warehouse | `0xf0`>>4 | stored goods kind | `q_goods = (occupant & 0xf0)>>4` |
| multi-cell bldg (`base_kind>=0xd5`) / coast | `0x03` | corner offset (dx=c%2, dy=c/2) / coast dir | `screens.c`, `landfill.c` |
| evolve decay | `0x1c`>>2 | demolition/decay countdown | `evolver.c` `v=(occ&0x1c)>>2; … occ=(occ&0xe3)\|(v<<2)` |
| evolve decay | `0x80` | within workcamp radius | `evolver.c` `occ &= 0x7f` / `\|= 0x80` |
| army on cell | whole byte | army index | `common.c` `occupant = army_no` |

## Per-record flag bytes  *(HIGH)*

* **`citizen_rec.flag_bits`** (+0x21): `0x01` = on-road / pathfind-ok / active
  (every walk handler early-returns on `(flag_bits & 1)==0`); `0x02` = transient
  (set/cleared `&= 0xfd` in one handler).
* **`army_rec.flags`** (+0x25): `0x01` = active/moving (set on army creation,
  gated `(flags & 1)==0 → return`; `flags &= 0xfc; flags \|= 1` reinit);
  `0x02` = a state bit (`flags &= ~2`); `0x08` = sailing / sea-voyage
  (`flags \|= 8` in sea-trade, gated with `sail_to_target`).

## Not bitfields (recorded so nobody re-checks)

* **`region_cell.place_state`** (+0x02): flood-fill **state/distance** — `0`
  unset, `0xff` blocked/wall, else a step value (`r+1`, `+= 2`). Integer.
* **`city_cell.road_aqueduct`** (+0x02): wall/aqueduct **chain length** counter
  (`count = road_aqueduct; if (terrain&0x80) count++`; `0xff` sentinel). Integer.
* **`base_kind`** (city & region, +0x00): a **tile/building category enum**
  (whole-byte compares: `==0x92`, `<0x1a`, `>=0xd5`, …); a few sites OR a high
  flag on top, but it is not a flag byte.
* **`battle_cell`** (4 bytes): `terrain` holds a small value (`rand & 0x1f` =
  terrain/corpse id), `figure` = occupying figure index, `arrow` = arrow index,
  `dirty` = redraw flag — whole-byte values/indices, not bitfields.
* **`city_cell.extra_edge`** (+0x04): a secondary **sprite/graphic index**
  (assigned whole tile numbers from `house_gfxdat`/`wall_gfxdat`, read as
  `sprite_count`) — a value, not a bitfield.
* **`city_cell.gfx`-class overlay bytes** (`activity_a/b`, `entertainment`,
  `education`, `health`, `land_value`, `fire`, `security`, `industrial`,
  `business`): 0..N magnitude levels, not flag bytes.

Remaining soft spots (not blocking): city `terrain` bit6-vs-bit7 wall/aqueduct
split; city `edge_bits` `0x1c`+`0x20`/`0x40` direction sub-field; region
`terrain` bits 3/6 graphics-variant exact meaning.
