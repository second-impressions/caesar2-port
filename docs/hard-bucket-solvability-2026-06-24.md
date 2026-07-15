# HARD-bucket solvability state — 2026-06-24

After this session's instrumentation (ShellSort sim, edit_sim wrapper,
optimiser-idioms catalogue, Cascade SIM CHECK integration), here's
the per-function solvability classification across the entire HARD
bucket (22 functions, 5682 b stuck).

## Summary

| verdict                  | fns | bytes | %   |
|--------------------------|----:|------:|----:|
| **SOLVABLE_SIM**         |   3 |  1379 | 24% |
| **KNOWN_LAYER5**         |   4 |  1219 | 21% |
| **SOLVABLE_SHELLSORT**   |   5 |   945 | 16% |
| **KNOWN_LAYER1**         |   1 |   770 | 13% |
| **SUB_SOURCE**           |   1 |   469 |  8% |
| **UNREACHABLE**          |   3 |   415 |  7% |
| **CHARACTERIZED**        |   1 |   207 |  3% |
| **OTHER**                |   2 |   140 |  2% |
| **KNOWN_LAYER2**         |   2 |   138 |  2% |

**Recipe-having (SOLVABLE_*, KNOWN_*, CHARACTERIZED): 16 / 22 fns,
4858 / 5682 b = 85 % by bytes.**  Every function in these buckets
has a named mechanism + named lever; what differs is the strength
of the recipe (auto-confirmed via edit_sim vs known-but-uncertified
mechanism class).

## Per-function classification

### SOLVABLE_SIM — edit_sim CONFIRMED a flipping edit (highest confidence)

The Cascade analyzer's "needs SAVINGS change" lever, run through the
edit_sim composed wrapper, reports `pair_check: FLIPPED` for at
least one named source variable.  Agent has a *recipe*: which
variable to bump, by how much, in which direction.  Combine with the
optimiser-idioms catalogue
(`docs/optimiser-folding-idioms-2026-06-24.md`) for the actual C
construct.

| function                    | bytes | file               | SIM CHECK                           |
|-----------------------------|------:|--------------------|-------------------------------------|
| `place_sprite`              |  1008 | pm_map1.c          | add to side (11→15) flips the pair  |
| `build_an_area`             |   274 | map.c              | remove from y (31→0) flips the pair |
| `get_region_over`           |    97 | action.c           | add to ry (40→60) flips the pair    |

### SOLVABLE_SHELLSORT — ShellSort instability with named destabilising temps

The `c2.regalloc.shellsort_sim.diagnose` says `shellsort-instability`
+ names size=1 anonymous byte temps whose source-line attribution
allows targeted restructuring of body byte-stores.  The simulator
predicts the slot order from any input perturbation in microseconds.
Recipe: relocate / merge / remove the body byte-store statements at
the named source lines.

| function                       | bytes | file               | source-line targets             |
|--------------------------------|------:|--------------------|---------------------------------|
| `evolve_water_table`           |   363 | evolver.c          | nt[27]@L475, nt[30]@L500, etc.  |
| `test_zone_for_closest_fire`   |   298 | int_c2.c           | nt[47]@L4411                    |
| `instant_reform`               |   260 | battle.c           | (shellsort+layer-1 mix)         |
| `build_road_from_elastic`      |    19 | map.c              | nt[1]@L954, [3]@L959, [5]@L964  |
| `build_units_figures`          |     5 | battle.c           | nt[9]@L1437, etc.               |

### KNOWN_LAYER5 — loop hoist/reload divergence

The Regalloc analyzer says PS reloads a global inside a loop that RC
hoisted (or vice versa).  Mechanism: an invariant global is reloaded
when a call or pointer store in the loop could alias it.  Recipe:
match the loop's call / aliasing-store structure to PS.
**Limitation**: not auto-confirmed by edit_sim (the simulator covers
ConfList sort, not loop-invariant detection).  Agent has the
mechanism name but must read the diff to identify the specific call
or pointer-store that differs.

| function                | bytes | file               |
|-------------------------|------:|--------------------|
| `place_a_building_roof` |   555 | pm_map1.c          |
| `start_move`            |   360 | battle.c           |
| `control_menus`         |   266 | controls.c         |
| `strip_spaces`          |    38 | lib32.c            |

### KNOWN_LAYER1 — EAX-boundary

PS enregisters one more value across a call than RC.  Recipe: move
the value's use before the call to free it to EAX, or shorten its
live range so it doesn't cross the call.

| function             | bytes | file               |
|----------------------|------:|--------------------|
| `citymap_evolution`  |   770 | evolver.c          |

### KNOWN_LAYER2 — callee-save savings

PS enregisters one more value than RC.  Recipe: bump the value's
savings above 2 (≈3 straight-line uses, or 1 loop use ×10) to make
it worth its push/pop.  Same mechanism as the savings cascade but
for prologue.

| function                     | bytes | file               |
|------------------------------|------:|--------------------|
| `get_entertainment_ov_image` |    99 | landfill.c         |
| `elephant_fire`              |    39 | battle.c           |

### CHARACTERIZED — sort-stable-other, lever direction known

`show_menu_items` (207b) — the diagnoser names the exact pair to flip
(text_group before y), the sort_sav split (12 vs 13), and the lever
direction (bump text_group's sort_sav above y's).  Empirical
perturbations tested and documented in
`docs/slot-swap-survey-2026-06-25.md`.  No zero-byte source-faithful
lever isolated yet, but the mechanism is fully exposed and every
candidate edit can be tested via the simulator.

### SUB_SOURCE — anonymous compiler temps, no source handle

| function                       | bytes | file               | note                         |
|--------------------------------|------:|--------------------|------------------------------|
| `build_reg_road_from_elastic`  |   469 | map.c              | anon CSE temp dominates slot |

### UNREACHABLE — non-allocator mechanism

Cascade analyzer reports `UNREACHABLE by any single allocation-order
move/swap` AND the pair involves compiler temps with no source
handle.  Likely rover / treegen / instruction-selection mechanism
beyond the allocator's reach.

| function                | bytes | file               |
|-------------------------|------:|--------------------|
| `get_reg_geog_ov_image` |   378 | landfill.c         |
| `test_for_same_fig_to`  |    33 | battle.c           |
| `restore_picture_part`  |     4 | display.c          |

### OTHER — not yet sub-classified

| function                     | bytes | file               |
|------------------------------|------:|--------------------|
| `show_regionmap_top`         |   137 | pm_map2.c          |
| `show_battle_outtro_screen`  |     3 | screens.c          |

Both involve anonymous temps + tie-breaks; likely SUB_SOURCE in
practice but the audit script's heuristic didn't classify them
that way.

## What "SOLVABLE" means (and what it doesn't)

* **SOLVABLE_SIM** — the offline simulator confirmed a specific source
  edit would close the named pair-swap.  Highest confidence.  Agent
  edits the named variable as suggested + recompiles + verifies.
* **SOLVABLE_SHELLSORT** — the simulator names destabilising body
  byte-stores; agent restructures those source statements + recompiles.
  No edit_sim confirmation (slot-swap is at AssignTemps, not
  AssignConflicts) but the simulator is direct.
* **KNOWN_LAYER1/2/5** — the layer's mechanism is named (EAX-boundary,
  callee-save savings, loop hoist); agent has a known-good lever
  template, no per-function auto-confirmation.
* **CHARACTERIZED** — mechanism + lever direction known, no candidate
  edit found that doesn't introduce other regressions yet (open
  frontier; tractable but not "solvable on first try").
* **SUB_SOURCE / UNREACHABLE** — mechanism is identified but no source
  handle exists to flip the diff.  Park as residue.

## How to use this list

1. Pick the highest-bytes SOLVABLE_SIM entry: `place_sprite` (1008 b).
2. Run `c2 decomp-verify decomp/src/pm_map1.c -f place_sprite -v` to
   see the Cascade verdict + SIM CHECK CONFIRMATION.
3. Consult `docs/optimiser-folding-idioms-2026-06-24.md` for the C
   construct that achieves the suggested savings delta.
4. Apply the edit, recompile, verify.  Cross-check against Mac PPC
   + Windows MSVC oracles per the standard workflow.

For SOLVABLE_SHELLSORT: run
`uv run python scripts/probe-same-line-param-slot-swap.py` as a
template (the build_units_figures probe) and adapt to your target.

For KNOWN_LAYER5 / KNOWN_LAYER1: read the Regalloc layer line in
`decomp-verify -v` for the mechanism; restructure source per the
layer's lever.

For UNREACHABLE / SUB_SOURCE: classify as residue and document with
a `c2 dossier <fn>` PARK comment.
