# Open-corpus leverage census (2026-06-14)

Current fresh `c2 decomp-verify --json --no-mac-decompile --no-strict` state:

- 1521 compared functions
- 1315 byte-exact
- 206 still diffing
- 0 size-mismatch functions: every open function has matching PS/RC length, so the remaining problem is not function-size/stub-size drift.
- Remaining diff byte mass is about 73.6 KiB.

This pass intentionally did **not** chase the smallest diffs.  The useful signal is where a small number of structural/source-shape mistakes causes a large byte cascade.

## Map-array functions dominate the open residue (2026-06-14)

After retyping `city_map` to `struct city_cell[CITY_W*CITY_H]` (byte-neutral, via
the `CM_*` cell accessors), a census of the 206 still-diffing functions shows:

- **136 functions access `city_map` in code**: 85 are byte-exact, **51 are still
  diffing** -- i.e. ~25% of the entire open corpus fiddles with `city_map`.
- By file (diffing city_map fns): map.c 16, evolver.c 12, pm_map1.c 8,
  int_c2.c 7, landfill.c 5, action.c/screens.c/census.c 1 each.

The retype was byte-neutral, so map access is **not the cause** of the diffs --
but the heavy over-representation is a strong **locator**: the hard remaining
residue lives in the map-sweep / neighbour / elastic-net / evolve / overlay
subsystems (the same families flagged in the motif census).  These functions
share big indexed loops with neighbour reads and runtime-field stamping, which
is exactly the regalloc-pressure-heavy shape that resists byte-equality.  Treat
"touches a map array" as a high-prior bucket when picking targets.

The diffing city_map functions: build_aquaduct/road/wall_from_elastic,
transform_aquaduct/wall_elastic, one_aquaduct/wall_ramification,
road_ramifications, test_elastic_range, get_best_elastic_value,
evolve_a_cm_row, evolve_amenity/fort/forum/industrial/security_activity,
evolve_land_value, evolve_water_table, cap_land_value, business_output,
take_census, push_shell, spread_fire_and_plague_and_unrest, generate_cm_river,
clear_an_area, clear_sized_to_rubble, place_a_building_top/roof, place_sprite,
show_overlay/left/right_overlay, show_city_landfill, show_citymap_top, top_it,
get_education/entertainment/industry/water_ov_image, get_query_info,
get_population_and_industry_count, city_test_for_road, try_this_citymap_square,
citizen_maraude_to_target, s04_map_markets, s10_get_business, test_range_for,
test_range_for_road, test_zone_for_closest_fire, build_city_item,
goto_flag_marker_mode.

### Map-array typed-cell conversion (done: city_map; next: region_map, battle_map)

`city_map` is now `struct city_cell[]` with `CM_CELL(off)` / `CM_N/S/E/W/NE/...`
directional accessors and an anonymous-union `b[]` overlay (named field access
for constants; `((unsigned char *)map)[off + field]` byte-ptr for the runtime-
field flag/range engine).  All byte-neutral (cgex: city-map-*.py).

**DONE 2026-06-14**: all three maps are now typed cell arrays, byte-neutral
(1315 exact throughout):
- `city_map`   -> `struct city_cell[CITY_W*CITY_H]`,   `CM_*` accessors
- `region_map` -> `struct region_cell[REGION_W*REGION_H]`, `RM_*` accessors
- `battle_map` -> `struct battle_cell[BATTLE_W*BATTLE_H]`, `BM_*` accessors

Each cell struct is `union { struct <name>_fields; unsigned char b[sizeof(...)]; }`
with a `typedef ..._size_check` compile-time guard.  Access rules (all proven
byte-identical to the old `unsigned char[]` indexing):
- current/neighbour named field: `CM_CELL(off).field` / `CM_S(off).terrain`
- runtime field index (flag/range engine): `((unsigned char *)map)[off + field]`
  (the `.b[field]` overlay form regressed the loop-heavy stamp functions via a
  `*stride` strength-reduction perturbation -- do NOT use it there)
- byte-pointer helper arg: `CM_CELL(off).b`
- bare pointer arithmetic on the array needs `(unsigned char *)map + off`
  (struct typing would scale by the cell size)

## Main new ranking: bytes per divergent binir line

`binir_shape_hint` says most open byte mass is still real structure, not pure encoding residue:

- `shape_divergence`: 176 functions, about 70.9 KiB
- `encoding_noise`: 28 functions, about 2.3 KiB
- `no_lines_with_ir`: 2 functions, about 0.3 KiB

Therefore rank by:

```text
score = diff_byte_count / binir_shape_hint.lines_divergent
```

This finds large functions where one or two bad source lines are poisoning the rest of the function.  These are much better targets than tiny allocator residue.

Top structural-leverage targets from the fresh corpus:

| function | diff bytes | divergent IR lines | note |
|---|---:|---:|---|
| `place_a_building_top` | 495 | 1/50 | one zext/mul line; also a donor for `top_it` / `place_sprite` |
| `basic_temple_screen` | 439 | 1/17 | one bad line; 16 tail-merge dependents, screens family multiplier |
| `set_route_elastic_range` | 746 | 2/2 | both compared lines are structurally wrong; not allocator-only |
| `show_move_highlight` | 342 | 1/2 | one missing PS branch-jump shape |
| `get_battle_odds` | 325 | 1/17 | one-line structural poison |
| `generate_cm_river` | 315 | 1/22 | mostly identical IR; one branch-shape line |
| `get_pseudo_map` | 847 | 3/32 | only three bad lines cause a large cascade |
| `show_battle_intro_screen` | 531 | 2/15 | small structural nucleus |
| `citymap_evolution` | 770 | 3/71 | only three bad lines; high-value shape target |
| `show_selections` | 510 | 2/20 | likely bad conditional/store expansion |
| `show_left_overlay` | 247 | 1/2 | one RC-only decision-tree line |
| `sf13_autofire_missile` | 220 | 1/10 | one branch/signext line |
| `show_regionmap_top` | 219 | 1/13 | one `cmp_jcc` vs `branch_flag_jcc` line |

Representative divergent source lines identified by `binir_shape_hint`:

- `pm_map1.c:599` (`place_a_building_top`): loop-close line; PS has `mul_pow2 + zext_byte_load`, RC has `zext_and_inplace`.
- `screens.c:1298` (`basic_temple_screen`): `draw_a_box(0x38, 0x164, 0x160, 0x1c, 0x10);`; PS has copy-then-op / pow2 shape, RC emits `mul_const`.
- `map.c:4123-4124` (`set_route_elastic_range`): `gmn_sptr += 8; if (gmn_x < 0x3c) goto x_loop;`; PS has multiply/store shape where RC has compare-only shape.
- `battle.c:424` (`show_move_highlight`): declaration cluster; one branch-jump shape differs.
- `map.c:268` (`generate_cm_river`): blank/source-gap before `if (variant != 0)`; one PS-only branch-jump.
- `pm_map0.c:57-61` (`get_pseudo_map`): direction-control local/slot shape; PS has copy-then-op where RC has pow2 multiply.
- `evolver.c:75-76,236` (`citymap_evolution`): post-dispatch tick/update comments/source lines; PS-only const-store/branch shapes.
- `controls.c:265-266` (`show_selections`): `selection_goods_list[i] = region_sources[province_is].choices[i];`; RC has extra signext/branches/stores.
- `pm_map1.c:1181` (`show_left_overlay`): `data_ptr = sprite_image_no * 16 + 8;`; RC expands a whole decision tree under this line.
- `battle.c:1532` (`sf13_autofire_missile`): `else if (type == 5) ...`; RC has extra signext/branch.
- `pm_map2.c:147` (`show_regionmap_top`): `pm_y_clip = 0;`; PS compare-vs-RC flag-branch shape.

## CallZap / prototype mismatch audit is still promising

`c2 sig-drift --actionable --by-tu` reports no actionable drift, but `c2 callgraph --check` still reports body-only / low-caller-count prototype mismatches that touch open functions.  These are not automatically safe edits; each requires PS disasm + Mac/source-shape confirmation.  They are, however, exactly the kind of horizontal CallZap lever that can move caller regalloc without touching callee bodies.

Map-related and current-open cases:

| callee | declared | inferred truth | open caller(s) / impact |
|---|---|---|---|
| `business_output` | 5 args | 2 args | `evolve_industrial_activity` |
| `evolve_a_building` | 5 args | 3 args | `evolve_a_cm_row` |
| `try_this_regionmap_square` | 3 args + return | 1 arg + return | `try_a_regionmap_square` |
| `try_this_seamap_square` | 3 args + return | 1 arg + return | `try_a_seamap_square` |
| `try_a_citymap_square` | 3 args + return | 1 arg + return | `citizen_go_to_target`, `citizen_maraude_to_target` |
| `check_goods_in_region_warehouses` | returns value | void | `citymap_evolution` |
| `get_regroad_web` | 2 args + return | 1 arg + return | `citymap_evolution` |
| `get_aqua_web` | 2 args + return | 1 arg + return | `one_aquaduct_ramification` |

This should be handled as a focused "map parameter crap" audit: compare caller register setup in PS disasm against the C prototypes, then decide whether the old transcription invented unused params or whether the callgraph inference is fooled by globals / body-only evidence.

### Map-parameter audit result: do not mechanically delete phantom args

First audit pass (2026-06-14) confirmed that several apparent prototype
mismatches are **load-bearing Watcall register masks/pass-throughs**, not safe
cleanup:

- `get_regroad_web(int x, int y)` and `get_aqua_web(int x, int y)` look like
  `eax`-only bodies to `callgraph --check`, but PS preserves incoming `edx`
  and immediately passes it through to `get_*_start_node(eax, edx)`.  These
  must stay 2-arg.
- `try_a_regionmap_square(dir, 0, 0)` / `try_a_seamap_square(dir, 0, 0)` and
  their `try_this_*` callees look like 1-arg bodies, but removing the two
  phantom args regresses the family hard (`try_this_seamap_square` goes from
  exact to diff, and both `try_a_*` bodies worsen).  The extra regs are shape
  levers, not semantic params.
- `try_a_citymap_square(dir, kind, unused)` likewise needs the unused third
  arg: removing it blows up the two citizen callers and worsens
  `try_a_citymap_square` / `try_this_citymap_square`.
- `check_goods_in_region_warehouses` is PS-void, but changing the C body from
  `int`/`return 0` to `void`/bare `return` worsens the callee and does not help
  `citymap_evolution`.

Conclusion: the prototype lever here is not "delete every unused arg".  The
lever is to identify which extra args are **register pressure shims** and keep
them, while looking for true map-array dialect bugs elsewhere.

### Map-array dialect result: cached `city_map` cell pointers

First source wins (commit `900da46`) came from Rule 63-style removal of cached
`unsigned char *cell = &city_map[cm_sptr]` when the pointer is only a local
field-access convenience:

| function | edit | byte result |
|---|---|---:|
| `take_census` | remove `cell`, spell `city_map[cm_sptr + field]` directly | 1113b -> 1062b |
| `push_shell` | remove `cell`, spell `city_map[cm_sptr + field]` directly | 345b -> 319b |
| `evolve_water_table` | remove `cell`, spell direct `city_map[...]` accesses; pass `&city_map[cm_sptr]` only at the one helper call | 590b -> 587b in final TU context |

Counterexamples from the same pass:

- `check_goods_in_region_warehouses`: replacing `struct region_cell *cell` with
  raw `region_map[cm_sptr + field]` regressed 311b -> 339b.  Keep the struct
  pointer there.
- `get_query_info`: removing `base = &city_map[ptr]` and passing
  `&city_map[ptr]` to each coverage helper regressed 927b -> 968b.  Keep the
  base pointer when it is a repeated helper-call argument.
- `swap_2_figures`: replacing `((struct battle_cell *)&battle_map[...]).figure`
  with raw `battle_map[map_ref + 1]` compiled identically; no byte lever.
- `place_a_building_top`: raw/cast spellings of the `rotated_map` fixed-bank
  load compiled identically; that remaining 495b is not a simple map-array
  raw-vs-struct issue.

Working rule: **inline cached map pointers when they only feed direct field
loads/stores; keep them when they are semantically passed to helper functions or
when the struct pointer itself is part of the desired pressure/alias shape.**

`cgex` follow-up (`docs/codegen-experiments/city-map-access-shape.py`, commit
`f565a27`) answers the likely-source question: this does **not** imply the
original programmer literally hand-wrote `city_map[cm_sptr + 9]` everywhere.
Watcom emits the same direct byte-offset shape for a macro such as
`CM(9) -> city_map[cm_sptr + 9]` and for an inline struct cast.  What matters is
that the expression remains a direct byte-offset expression in the IL; a cached
`unsigned char *cell = &city_map[cm_sptr]` materializes the base pointer and
changes codegen.  A true `struct city_cell city_cells[]` indexed by cell number
emits `cell_idx * 20` scaling and does not match the observed byte-offset style.
So the likely original abstraction was a byte-offset cursor plus field macros,
not necessarily raw readable `city_map[cm_sptr + N]` text.

## Map-array access dialect is a large substrate lever

Open functions that touch `city_map`, `region_map`, or `battle_map`:

- 75 / 206 open functions
- about 27.7 KiB of diff byte mass
- 36 functions / about 13.2 KiB use `struct city_cell`, `struct region_cell`, or `struct battle_cell` casts.

This is too large to treat as per-function noise.  The likely rule family is a **map-array dialect** problem:

- raw byte indexing (`map[off + N]`) vs struct-cast field access (`((struct cell *)&map[off])->field`)
- signedness of byte fields (`movsx` vs `movzx`)
- byte temporary birth vs direct memory expression
- store form (`mov byte ptr [...]` vs read/modify/write, or extra zeroing stores)
- parameterized `off`/`ptr` helpers whose prototypes may have been invented during transcription

Aggregate opcode deltas across the 206 open functions confirm this is not just register allocation:

- `movsx` deltas: 47 functions
- `movzx` deltas: 35 functions
- `store_mov` deltas: 99 functions
- `and`/`xor` zeroing deltas: about 100 functions

High-impact map-array users:

- `place2_sprite`, `place3_sprite`, `place_sprite`
- `place*_building_*`, `top_it`
- `build_road_from_elastic`, `test_elastic_range`, `test_rm_elastic_range`, `set_route_elastic_range`, `trace_back_route_elastic`
- `one_wall_ramification`, `one_aquaduct_ramification`, `road_ramifications`
- `show_*_overlay`, `show_*_landfill`, `get_*_ov_image`
- `get_query_info`, `business_output`, `evolve_*`

## Donor-first still has multiplier value

Diffing donors with currently blocked dependents:

| donor | donor diff | deps | blocked bytes | notable diffing dependents |
|---|---:|---:|---:|---|
| `basic_temple_screen` | 439 | 16 | 15723 | `forum_industry_screen`, `show_people_query_panel`, `get_query_info`, `show_battle_outtro_screen` |
| `evolve_land_value` | 990 | 14 | 10663 | `citymap_evolution`, `evolve_water_table`, `evolve_amenity_cover`, `cap_land_value`, `evolve_forum_activity`, `evolve_fort_activity` |
| `get_wf_dirc` | 307 | 14 | 9378 | `show_move_highlight`, `setup_roman_units`, `setup_enemy_units`, `sf14_opertunist_fire` |
| `build_wall_from_elastic` | 406 | 14 | 6565 | `generate_cm_river`, `build_road_from_elastic`, `transform_wall_elastic`, `build_aquaduct_from_elastic`, `destroy_reg_atom` |
| `mid2_line_with_sides_base` | 51 | 4 | 6353 | `place2_a_building_base`, `place2_a_building_top`, `place2_a_building_roof`, `place2_sprite` |
| `place_a_building_top` | 495 | 4 | 4641 | `top_it`, `place_sprite` |
| `show_battlemap_base` | 511 | 2 | 2539 | `mid3_line_no_sides_base`, `place3_sprite` |

Donor implication: do not begin by grinding `place2_sprite` or `place3_sprite`.  First attack the PM-map donor/body dialect (`mid2_line_with_sides_base`, `show_battlemap_base`, `place_a_building_top`) and the map-array/prototype substrate.

## Source motif families still open

Largest open name/source motifs:

| motif | functions | bytes |
|---|---:|---:|
| place/sprite/building display | 8 | 8464 |
| evolve family | 10 | 7058 |
| query/screen/panel | 10 | 6225 |
| elastic family | 14 | 5955 |
| figure/target/battle AI | 15 | 4160 |
| overlay/landfill | 12 | 2705 |
| `try_*_square` family | 6 | 2060 |
| census family | 3 | 1943 |
| ramification family | 5 | 1379 |
| sound family | 4 | 259 |

## Burn-down triage (2026-06-14): where the 206 actually live

Thorough pass with `c2 triage` + per-fn `c2 dossier` verdicts. The remaining
corpus splits cleanly, and **there is no low-hanging fruit left** -- every
category needs either WCC allocator modelling or a multi-hour reconstruction:

1. **Allocator register-ties** (small byte diff, IR-multiset IDENTICAL): the
   diff is *which* callee-saved reg each var/param lands in (CountRegMoves
   savings + GivenRegisters tiebreak). NOT source-steerable cleanly. Examples:
   `city_test_for_road` (7b, param x/y reg tie), `build_units_figures` (5b).
   These are the "small diffs are a lie" cases.
2. **Pervasive allocator reorder** (large byte diff, IR IDENTICAL, big line-mark
   mismatch): whole-function register assignment differs. `get_city_mood` (65%,
   author already parked as layout), `generate_cm_river` (58%).
3. **Savings cascades** (`c2 triage savings`): the tool names the exact pair +
   direction (e.g. `get_city_mood` old_mood sav=19 vs r sav=15; `clear_a_reg_area`
   kind=1200 vs y=662). Source-steerable in principle, but flipping CountRegMoves
   needs precise use-pattern surgery, multi-minute build cycles, and most fns
   have multiple/INCONCLUSIVE cascades. Low yield per attempt.
4. **Semantic / structural divergence** (IR-multiset DIFFERS = real source bug):
   the only genuinely source-fixable class, but large/risky. `place_a_building_top`
   (mul_pow2 PS5/RC4), `clear_sized_to_rubble` (zext_byte_load PS16/RC8 -- RC
   caches a field PS re-reads), `evolve_*` family (all blocked on the shared
   `*1600`/frame cascade, first-diff +0x4..+0x8), `show_selections` (already
   rewritten, still 80%).
5. **Tail-merge donor chain**: `c2 tail-merge --blocked` finds exactly ONE
   genuinely blocked dependent -- `evolve_a_building` (1b), whose `jmp` lands in
   a shared tail at 0x42ebd that it and `devolve_a_building` both jump up into.
   The donor's layout shifts 1 byte upstream (Rule-16 near/short cascade): the
   known "turtles up to wrong donor" family, not independently fixable.

**Verdict:** quick source wins are exhausted. The two real levers are (a) finish
the WCC `CountRegMoves`/`GivenRegisters` model so the predictor can compute the
exact source nudge for the allocator classes (watcom10.0a side -- the
GivenRegisters tiebreak is already confirmed in the binary), and (b) commit to
the IR-multiset-DIFFERS structural reconstructions one at a time (highest-value:
the `evolve_*` frame cascade, which would unblock ~5 functions at once).

### evolve_fort_activity deep-dive (2026-06-14): structural levers found, but allocator-gated

Worked this end-to-end with `c2 dossier` (regalloc section) + RC-vs-PS disasm.
Found THREE genuine, PS-confirmed source levers -- each correct in isolation:

1. **`new_cit` base-caching**: PS computes `created_citizen_no*0x3a` ONCE into a
   base reg and reuses it for all 7 `citizen_list[created_citizen_no].FIELD`
   writes; our source re-indexed each time (9 temps crammed into EAX per the
   dossier regalloc section). Caching `new_cit = &citizen_list[created_citizen_no];`
   (the variable was ALREADY declared, unused!) drops EAX crowding 9->7 and makes
   `new_cit` a named sav=1500 conflict like PS.
2. **`if (counter == 0)` inversion**: PS lays out the big `counter==0` block as
   the fall-through and puts `new_counter = counter-1` at the BOTTOM (reached by
   `jne`). Inverting our `if (counter != 0){dec}else{big}` to
   `if (counter == 0){big}else{dec}` makes RC's block order match (`jne` to a
   bottom dec block).
3. **`unsigned char counter`**: PS handles the cooldown as a byte (`dec al`,
   `mov byte [esp+N]`); our `int` forced `and eax,0xff` zext.

**But all three RAISE the raw byte count** (255 -> 260/270/281), because they each
shorten RC while PS is *longer* -- and PS is longer precisely because it SPILLS
`row`/`col` to the stack and keeps the `rows` param in EDI. RC does the opposite
(`rows` sav=12 -> spilled; `col` sav=710 -> ESI; `row` -> EBP). That spill
inversion is the dominant residue and is NOT source-reachable: `col`'s
inner-loop frequency intrinsically gives it sav=710, which outranks the param
`rows` (used once, sav=12) -- no source edit closes a 12-vs-710 savings gap, and
the triage's `EBP<->EDX` pair (the `row` spill/liveness) is flagged UNREACHABLE.

**Lesson:** even with perfect block layout + types, an `evolve_*` function can't
reach byte-exact while the allocator keeps the loop counters in registers and
PS spills them. This is squarely lever (b)->(a): the structural levers above are
NECESSARY but not SUFFICIENT; the spill decision needs the WCC
`CountRegMoves`/spill model. The three levers are recorded here so a future pass
(once the allocator side can confirm the spill) can apply them as the
structural half of a full fix.

### Byte-exact-sibling probe (2026-06-14): the spill class has NO working template

Follow-up: found the byte-exact siblings with the same `(int rows)` + cm_sptr
double-loop shape -- `evolve_security_cover` and `evolve_water_supply_baths_industry`.
They reveal the structural template (for-header cursor `col++, cm_sptr += 20`;
`unsigned char kind`; `continue` not `goto next`; if/else-if). Applied ALL of it
to `evolve_fort_activity` plus the lazy-`enemy` scheduling fix -- each change
VERIFIED in the RC asm to match PS's structure exactly (loop form, the
created-base-then-lazy-enemy-base order, etc.). Every one was byte-neutral or a
regression, because the byte-exact siblings **do not spill** (simple bodies =
zero stack frame, everything in registers), so they cannot show the spill idiom.

Then searched the WHOLE byte-exact corpus for ANY function with this shape that
*does* spill (stack frame > 0 + double-loop cursor + inner calls): **zero hits.**
Every spilling complex-body map-sweep (the entire evolve family + take_census,
spread_fire_and_plague, etc.) is in the DIFF set. So the `rows`-vs-counter spill
is a **systematic, class-wide divergence with no byte-exact precedent anywhere
in the corpus** -- it is NOT a per-function source quirk and cannot be grinded
away with source structure. It needs the WCC `CountRegMoves`/spill-decision
model (lever B). Upside: that model would unlock the whole class at once
(~10-20 functions), not one at a time.

### Spill lever now PREDICTABLE as a hint (2026-06-14, `c2 regtrace --explain`)

Closed the predictability gap: the explain table's MEMORY-exile rows now print a
**spill-chain** line naming which value holds each candidate register and the
cheapest displaceable holder -- the concrete source lever. Example
(`evolve_fort_activity`, also `take_census`, `evolve_amenity_cover` -- whole
class identical):

```
  16  rows  1163  12  MEMORY(masked: all candidates masked)
      spilled because: EAX=(temp)(1500) EDX=enemy(700) ESI=col(710)
        EDI=enemy_idx(400) EBP=row(231)
      LEVER: all callee-saved holders out-rank sav=12; free a reg by spilling
        the cheapest callee-saved holder row(231) -- lower its savings /
        shorten its live range
```

**Verified real**: the holder map was checked against the COMPILED RC binary
for `evolve_fort_activity` (`row`->EBP, `col`->ESI, `enemy_idx`->EDI, `rows`
spilled to `[esp]`) -- exact match. Then tested across the corpus, which surfaced
and fixed a bug (an earlier draft told a value that already OUT-RANKED a holder
to "raise its savings", which is nonsense). The hint now distinguishes three
real, callee-saved-aware cases:

  1. **below all holders** (e.g. `rows` sav=12): the lowest cross-call competitor;
     it spills because >4 cross-call values fight for 4 callee-saved regs. Lever:
     shorten the cheapest holder's call-spanning range so it becomes a memory
     temp, dropping the count below the reg budget.
  2. **a free callee-saved reg that is scratch-clobbered** (e.g. `business_output`,
     EBX unheld yet spilled): the reg is occupied by short-lived scratch across
     the call(s). Lever: cut the cross-call scratch (CSE/reorder).
  3. **out-ranks a holder yet spilled** (e.g. `get_query_info` dy, `patrol_count`):
     NOT a rank problem -- its candidates were all masked at its def. Lever:
     shorten/split THIS value's own (call-crossing) live range.

Model: `build_holder_map` + `spill_chain_hint` in `c2/commands/regtrace.py`,
unit-tested in `tests/test_spill_chain.py` (4 cases). For any spilled value the
hint now names the exact competitors and the correct, case-specific lever -- the
spill is no longer a black box.

### Causal validation (2026-06-14): the lever provably flips the allocation

The hint isn't just descriptive -- its lever was confirmed CAUSALLY by
controlled experiment on `evolve_fort_activity` (baseline 255b, `rows` spilled):

| change | effect on `rows` | bytes |
|---|---|---|
| baseline | MEMORY (spilled) | 255 |
| `volatile int col` (force col -> memory temp) | **MEMORY -> EBP (register)** | **224** |
| `volatile int col` + `volatile int row` | **-> EDI** (PS's *exact* reg) | 273* |
| `unsigned char col` | col sav 710->310, col spills *naturally* | 264 |

Forcing a loop counter out of the callee-saved pool flips `rows` into a register
exactly as the hint predicts -- and into PS's exact register (EDI) when both
counters leave, confirming the holder/displacement model end-to-end. (`volatile`
is a probe, not a faithful fix -- it forces *every* access to memory, heavier
than PS's spill-and-reload-to-scratch, hence the 273 with both.) `unsigned char
col` lowers col's savings and spills it *naturally* (no volatile), and the hint
then correctly re-points to the next layer: "ESI is unheld but scratch-clobbered
across the call(s) -- cut cross-call scratch." So the hint both predicts the
spill AND guides the lever search step-by-step, each step verified against the
rebuilt binary.

**Status:** hint = REAL (facts match binary, lever causally proven, guides
step-by-step). A fully byte-faithful fix for `evolve_fort_activity` needs PS's
complete allocation reproduced (col+row as int memory temps, `rows`->EDI,
`enemy_idx`->ESI, no scratch in the freed regs) -- multi-layered allocator-model
work -- but it is no longer a black box: every layer is now named and
predictable, and clearing them is monotonic (255 -> 224 with the first lever).

### From "hint" to "DO THIS" -- and the honest limit (2026-06-14)

Pushed the predictor to emit a literal mechanical edit for the one case that
has one: an equal-savings register tie now prints
`DO THIS: swap the declaration lines of X (lnA) and Y (lnB) [Rule 115]; else
commute the deciding use [Rule 28a]`.

Then TESTED it and it was over-confident: `get_nearest_reg_building` (4b) flagged
a `best_x<->best_y` swap, but applying it regressed 4->8b -- the swap was a
DOWNSTREAM artifact of a type-width diff, not the cause. So the gate was
tightened: a decl-swap is asserted as `DO THIS` ONLY for a **clean swap-only
divergence** (no type-width/truncation rows AND no other semantic/encoding
replace rows); otherwise it is demoted to `CANDIDATE (... fix the non-swap rows
first)`.

**Corpus scan result: 0 of 206 diffing functions have a clean swap-only diff.**
Every register swap is accompanied by type-width/semantic/encoding divergence,
so the decl-swap "do this" would be wrong for ALL of them -- the gate correctly
never fires it. The honest takeaway: **a register-swap source edit is never the
sole lever in this corpus**; it is always downstream of a width/semantic diff.
The predictor now says exactly that and redirects to the real (non-swap) lever.
The genuinely mechanical "do this" remaining is the **type-width** class
(declared width / zero-extension, Rule 8/23/49); the spill and semantic classes
are named-and-predictable but need the source-shape / allocator-model work,
not a one-line mechanical edit. Tooling: `_do_this` + gate in
`c2/commands/regtrace_explain.py`, tests in `tests/test_regtrace_explain.py`.

## Recommended next queue

1. Run the map-parameter / CallZap audit for `try_this_*`, `try_a_*`, `get_aqua_web`, `get_regroad_web`, `business_output`, `evolve_a_building`.
2. Work one-line structural targets with donor leverage: `place_a_building_top`, `basic_temple_screen`, `generate_cm_river`, `citymap_evolution`, `get_pseudo_map`.
3. Define and test a map-array dialect rule: raw byte indexing vs struct field casts, signed/unsigned byte loads, direct field stores vs temporary/RMW forms.
4. Only then return to large bodies like `place3_sprite`, `place2_sprite`, `evolve_a_cm_row`, `set_route_elastic_range`.

The actionable shift is: **rank by large byte residue caused by few divergent binir lines, then intersect with donor leverage and map/prototype substrate**, rather than grinding small byte diffs.

## Map-access form is settled -- it is NOT the residue (2026-06-14)

A one-off PS-vs-source map-access cross-check was run over the whole open
corpus (the throwaway decoder/differ has since been removed -- it produced no
byte wins, see verdict below).

**Key finding: map-access *form* is NOT the dominant residue.** Across all 51
open city_map functions only **2** had a real form mismatch; the other 49
already use the correct access form and diff purely on allocator/frame/codegen
residue.

The 2 mismatches found:

- **`push_shell`** (evolver.c) — FIXED (commit after 34ee4ca). The `dir == 1`
  branch read `CM_NW(cm_sptr).fpu_flag` + `CM_N(cm_sptr).citizen_a`; PS reads
  `CM_N(cm_sptr).terrain & 0x1e` + `CM_N(cm_sptr).security` (all four dir
  branches read neighbour `terrain`+`security`). Byte-neutral on the corpus
  because push_shell's diff is an early frame/tail-merge cascade that saturates
  the byte count, but it removes a genuine transcription bug.

- **`evolve_industrial_activity`** (evolver.c, 753b) — OPEN, concrete
  reconstruction lead. The `edge_bits` form mismatch is the symptom of a
  **missing entire `kind == 0xfa` branch**. PS dispatches base_kind into two
  paths sharing the activity_a/activity_b writeback tail (0x41ddd):
    - `kind in [0xfc,0xff]` (path A, 0x41b80): `market_image()`, no edge_bits,
      `put_out_a(2, ...)`, patrons wrap at 4, citizen `+0xE = 4`, first test is
      on `cooldown` (activity_b&0xf) not `active`.
    - `kind == 0xfa` (path B, 0x41cb3): `CM_CELL(cm_sptr).edge_bits |= 1`
      (unconditional, before the activity_a test), `business_output(...)`, then
      `put_out_a(6, ...)`, patrons wrap at 9, citizen `+0xE = 0xa`.
  The current source is a single hybrid path. Needs a careful two-branch
  rewrite (different call targets, put_out_a type arg 2 vs 6, wrap 4 vs 9) with
  per-edit byte verification.

Conclusion: for the remaining city_map functions, stop looking for access-form
bugs (they're correct) and attack the allocator/frame/structural residue
directly (binir shape divergence, donor leverage, missing branches like the
`evolve_industrial_activity` 0xfa path above).

### region_map (38 open) + battle_map (16 open): all forms correct

Same cross-check over the other two arrays found **zero real access-form bugs**.
Every apparent mismatch was a harness false positive caused by the
**cached-pointer** access idiom, which the PS-vs-source differ can't decode but
which is byte-correct:

- `trace_back_route_elastic` / `set_route_elastic_range` (map.c):
  `cm = &RM_CELL(gmn_sptr).base_kind; ... cm[2]/cm[-0x1de]/cm[0xa]...` — 8-way
  place_state neighbour scan via a cached byte pointer (route-finding inner
  loop; the cache is load-bearing for register pressure).
- `check_goods_in_region_warehouses` (evolver.c):
  `cell = (struct region_cell *)RM_CELL(cm_sptr).b; cell->occupant` — cached
  struct pointer.
- `place3_sprite` (pm_map3.c):
  `cell = &(*(struct battle_cell *)&((unsigned char*)battle_map)[pm_shown_ptr]);
  cell->figure/->arrow` — cached struct pointer.
- `get_fig_missile_image` (battle.c): touches no map at all; the "src-only
  dirty" was a slicer span-collision with the next function.

**Corpus-wide verdict:** across all 105 open map-touching functions the only
real map-access discrepancies are `push_shell` (fixed) and
`evolve_industrial_activity` (structural 0xfa branch). Map-array *form* is
settled; the open residue is allocator / frame / structural everywhere else.

### How rigorous is that verdict? (harness caveats)

The `region`/`battle` "all false positives" conclusion was first reached by
manual reading, then *proven* by a hardened triage differ.  Honest caveats:

- The first pass's "0 violations on 145 byte-exact" checked only ONE direction
  (PS-form in source).  A bidirectional check (also source-form in PS) is the
  real gate; the one-directional pass over-claimed.
- **0 of 145** byte-exact map functions use the cached-pointer idiom
  (`cm = &XM_CELL(off).f; cm[N]` / `(struct cell*)XM_CELL(off).b; p->f`), so the
  byte-exact corpus never exercised it.  All 4 cached-pointer functions are in
  the diff set; teaching the differ that idiom and running it BOTH ways gives
  `trace_back_route_elastic`, `set_route_elastic_range`,
  `check_goods_in_region_warehouses`, `place3_sprite` = 0 missing AND 0
  src-only -- i.e. exact equivalences, confirmed not bugs.
- The PS-side decoder had inherent blind spots: two-register operands carry the
  field in a register ("runtime field", unnamed), and base-folded-into-register
  accesses (`[reg]`, no displacement) are invisible.  These surface as src-only
  on a bidirectional check (e.g. `set_4_neighbours`' runtime `field_off`) and
  are NOT bugs.  (The decoder/dossier section/test were removed afterward --
  they found no byte wins.)
- The triage slicer is regex-based and can merge functions it cannot bound
  (`set_4_neighbours` sliced as a 139-line blob of ~6 functions); cross-check
  any flag with `c2 disasm` + direct source grep before trusting it.

### Manual audit of the 4 decoder-blind functions (DONE, all clean)

The decoder cannot see accesses whose map base is folded into a register
(`[reg]`, no displacement).  4 diff functions tripped this; hand-audited via
`c2 disasm` + source:

- `evolve_a_cm_row` (1820b): cached `cell = CM_CELL(city_ptr).b + col*20; cell[N]`.
  PS byte-field displacements `{0,3,5,0xa,0xb,0xd,0xf}` == source cell[] set
  exactly (no extra/missing fields).  Map access correct; the 81% diff is the
  evolve-family frame/allocator cascade (RC frame +0x1c).
- `citizen_maraude_to_target` / `region_go_to_target` / `sail_to_target`: do NOT
  dereference any map locally -- they only pass `(unsigned char *)<map>` as an
  argument to pathfinding callees (city/region/region respectively, all
  correct).  Nothing map-related to get wrong; diff is allocator/pathfinding.

### `evolve_industrial_activity` (the one real map bug): blocked, not a byte win

The missing `kind == 0xfa` branch is real, but reconstructing it will NOT make
the function byte-exact: it first diverges at **+0x5** (frame/`*1600` setup),
~350 bytes before the 0xfa branch site (+0x16a).  The whole evolve family
(`evolve_forum_activity` 359b, `evolve_fort_activity` 255b,
`evolve_amenity_cover` 572b, `evolve_security_activity` 484b, this one 551b) is
stuck on the SAME early cascade (first diffs +0x4..+0x8), driven by frame size +
the kind-check codegen.  Byte-equality needs BOTH a faithful 2-branch rewrite
(path A: `market_image` + `put_out_a(2)`, patrons wrap 4, saved_state 4; path B:
`edge_bits|=1` + `business_output` + `put_out_a(6)`, patrons wrap 9,
saved_state 0xa; shared activity_a/activity_b writeback tail) AND alignment of
the evolve-family frame cascade. Treat the evolve family as a single
frame-lever target, not individual map fixes.
