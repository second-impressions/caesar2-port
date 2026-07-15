# Seat-oracle calibration — what actually closes a `fix_next=seat` residue

The forge **seat oracle** (`c2/forge/seat_oracle.py`) routes a
`fix_next=seat` function to a focused lever profile instead of the full
battery.  Its routing was **calibrated against ground truth** by
reverting known seat-closing commits and recording what every
PS.EXE-native signal reported in the *broken* (pre-fix) state.  This
doc is that calibration + the design conclusions.

## Method (reproducible)

For each historical seat-closing commit `C` touching file `F` with the
fix applied to function `fn`:

```bash
git worktree add --detach /tmp/c2-survey HEAD
# symlink the gitignored inputs so the tooling runs
ln -s $REPO/data /tmp/c2-survey/data ; ln -s $REPO/vendor /tmp/c2-survey/vendor
cp -r $REPO/.c2-cache/build /tmp/c2-survey/.c2-cache/build   # link context
# UNDO just the fix on the CURRENT file (keeps current headers -> compiles):
git -C /tmp/c2-survey show C -- decomp/src/F | patch -R -p1 --fuzz=8
uv run c2 decomp-verify decomp/src/F -f fn --json --no-cache   # PS-native signals
```

Reading the whole-file revert fails (header drift); reverse-patching
**just the fix hunk** onto the current tree is what compiles.

## Calibration table (broken state of known seat closers)

| function | fix that worked | `fix_next` | islands | `seat_recon` | **win-census said** |
|---|---|---|---|---|---|
| `do_heavy_ai` | split decl/assign | **ir** (2) | 2 | clean | untrusted (Q.69) |
| `try_this_regionmap_square` | Rule 115 decl-order | **ir** (1) | 1 | clean | **de_invent Δ−5 Q.88** ✗ |
| `convert_lbm_file` | decl-order | **seat** | 0 | clean | untrusted |
| `cap_land_value` | int→char width | **ir** (1) | 1 | clean | untrusted |
| `show_history_graph` | Rule 115 decl-order | **seat** | 0 | clean | untrusted |
| `forum_update_census` | reverse decl-order | **ir** (3) | 3 | ambiguous | **de_invent Δ−1 Q.94** ✗ |

## Findings

1. **Win-census (MSVC `/Od`) is UNRELIABLE as a router.**  Both high-Q
   `de_invent` verdicts were actually closed by **decl-order**, not
   de-invent.  Win/Mac are a different, later source cut compiled by a
   different compiler — a *hint*, never proof of the DOS local set.
   `/Od` also enregisters nothing, so its frame slots overcount vs the
   optimised Watcom PS.EXE actually uses.  ⇒ the oracle logs the
   census as an **informational hint only**; it never routes.

2. **PS.EXE-native signals are the ground truth**, but limited: at
   `-d1` PS.EXE has no local names, and register-resident locals leave
   no trace.  `spill_recon` (PS frame vs ours) was `slot_delta=0,
   equal` on every one of these — it only sees *spilled* values.  The
   de-invent reload census (Rule 129) was silent.  So for a pure-seat
   residue, PS.EXE confirms the frame matches — the residue is a
   register *seat*, and the historical lever was **decl/use-order**.

3. **4/6 historical "seat" fixes present as `fix_next=ir`** (small
   islands 1–3): the fix changed statement shape (split-decl,
   decl-order emits different `-d1` marks / IR), so the ledger scores
   it `ir`, handled by the ordinary shape levers.  Only the
   `islands=0` cases are genuine pure-seat problems.

4. **The genuine pure-seat closers were fixed by DECL-ORDER (Rule
   115).**  `convert_lbm_file`'s real fix (`swap_decls(chunk_search,
   a)`) is exactly what a decl-order profile restricted to its
   competing values `[a,b,k,src]` generates.

## Design conclusions (implemented)

* **Route named-competing seat cases to the decl-order reorder
  profile** (Rule 115/28a + width), *not* a register-class flip.  The
  presence of NAMED values in the diverging registers (or inverse-search
  tie movers) is itself the routing signal — inverse-search's clean
  `tie` detection is too strict to confirm most real closers.
* **`decl_swap_all` runs UNRESTRICTED** in the reorder profile: the
  decl-order *mover* need not be a diverging value (`convert_lbm_file`
  closed via `swap_decls(i,b)`, and `i` is not a competing value).
  Only O(n²), so the pool stays small; the expensive levers
  (`decl_perm`, `stmt`/`commute`, `type`) stay focused on the competing
  set.
* **Anonymous-only seat ties → skip** (certified sub-source residue):
  the diverging registers hold only compiler temps, no source handle.
* **Census / bridge (type-flip) is NOT auto-routed** — demoted after the
  survey.  `preset_seat(prune_reorder=True)` and `preset_localset`
  remain in the palette for manual `--presets` experiments.

## Validation

Recalibrated forge re-closed `convert_lbm_file` (broken state) to
**byte-exact in round 1 / 4 s** via `swap_decls(i,b)` — the decl-order
lever.  Before recalibration the oracle routed it to `bridge`
(type-flip) and would never close.

## Broader survey — what closes a byte-exact flip BEYOND correct shape

A second survey (15 commits, 12 usable) across every "last-mile" lever
(de-invent, decl-order, use-order/commute, width-flip, split-decl,
slot-swap, RMW-fuse) recorded the broken-state signal per lever:

| function | lever | fix_next | islands | spill_dir | seat_recon |
|---|---|---|---|---|---|
| `find_enemy` | **de-invent** | seat | 0 | equal | ambiguous |
| `start_move` | **commute** | seat | 0 | equal | clean |
| `city_test_for_road` | **width int→schar** | seat | 0 | equal | ambiguous |
| `get_ptr_to_corner` | de-invent | ir | 4 | equal | ambiguous |
| `update_units_morale` | de-invent | ir | 5 | equal | clean |
| `mid3_line_no_sides_base` | de-invent | ir | 3 | equal | ambiguous |
| `test_zone_for_closest_fire` | slot-swap | ir | 2 | equal | clean |
| `show_battle_landfill` | decl-order | ir | 8 | equal | **swap** |
| `battle_auto_resolve` | split-decl | ir | 23 | **rc_spills_more** | ambiguous |
| `dock_the_ship_in_good_port` | RMW-fuse | ir | 11 | **ps_spills_more** | clean |

Findings:

1. **The seat layer is lever-AMBIGUOUS.**  `find_enemy` (de-invent),
   `start_move` (commute) and `city_test_for_road` (width) are
   shape-IDENTICAL — `fix_next=seat, islands=0, seat=1` — yet were closed
   by three *different* levers.  The shape signal cannot pick the lever.
   ⇒ the seat profile must offer EVERY seat lever (decl-order + use-order
   + commute + width + de-invent) and let byte-verify decide.  This is
   why single-lever routing leaves holdouts.

2. **The de-invent reload hint (Rule 129) has ~0 recall here** — it fired
   on NONE of the four de-invent closers; they were found via the win
   witness (which §Findings above shows is unreliable).  There is no
   dependable PS.EXE-native "this local is invented" signal today; the
   only safe route is to OFFER `de_invent_all` and let the byte oracle
   confirm.  (`de_invent_all` was added to the seat profile as a result.)

3. **Most "beyond-shape" fixes present as `fix_next=ir` (islands 2–8)**,
   not pure seat — the lever changes statement shape, so the ordinary
   shape levers (driven by the ir islands) already cover them.  Only
   `islands=0` is a genuine pure-seat problem, and even those are
   lever-ambiguous (finding 1).

4. **`spill_dir != equal` is a real discriminator** for the split-decl /
   RMW / spill-class levers (`battle_auto_resolve` rc_spills_more,
   `dock` ps_spills_more) — the `spill` layer, worked before seat.

5. **Multi-lever combos are common and defeat single-lever search:**
   `find_enemy` = de-invent + line-packing; `battle_auto_resolve` =
   split-decl + decl-order; `get_query_info` = commute + decl-order.
   `de_invent_split(xx)+de_invent_split(yy)` compiles but stays neutral
   until the guards are ALSO packed onto one `-d1` line.  These are the
   residual frontier the pairs/triples escalation must reach.

## Honest limits

The recalibrated oracle correctly and quickly triages the current
`fix_next=seat` corpus (skip the anon sub-source residues in seconds;
route the named ones to decl-order), but the remaining stuck functions
(`figure_go_to_target`, `check_goods_in_region_warehouses`,
`place2_a_building_top`, `build_city_item`) do **not** close on a single
decl-order/type edit — they are the residual multi-edit / sub-source
frontier (`build_city_item` has a documented 3278-plan decl-order
failure, `cc04e9fd`).  The oracle is *correct and validated*, not a
universal solver.
