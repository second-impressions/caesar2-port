# Structure-twin survey of the diff corpus — 2026-06-17

**Question.** Take every function still in the diff corpus and check
whether it is structurally similar to a **byte-exact** function — *not*
in a sibling/family sense, but by three asm-visible structural features:

1. **stack space reserved** — the prologue `sub esp, N` frame size;
2. **arguments it takes** — declared param count from `decomp/src`;
3. **opening code** — the first `K=10` instructions after the prologue,
   normalised to a `mnemonic(operand-shape…)` sequence (addresses,
   register identities and constants abstracted away, so an unrelated
   function with the same *shape* matches).

The goal is to infer *what is wrong* with each diffing function from how
it matches (or fails to match) the byte-exact corpus.

**Method / where it's built.** Merged into the **`c2 sibling`** tool as a
second similarity lens over its cached corpus: the structural prologue
signature (pushes, frame, argc, opening shape) is computed for *every*
function during the sibling corpus build, reusing sibling's own
instruction normalization for the opening shape. Exact/diff status,
`rule_hints`, `frame_hint`, and the first-divergence offset are read from
the **decomp-verify** cache (`.c2-cache/verify.json`) to enrich the
partition. `shape-recon` was *not* used corpus-wide — it is per-function
and pulls the Mac/JVM witness; the three features here are pure PS-asm,
so this stays a sub-second scan off the warm corpus. Reproduce with:

```
uv run c2 sibling --survey                          # the partition below
uv run c2 sibling <fn> --structure [--cross-family] # twins of one function
uv run c2 sibling --structure --all                 # per-diff best twin
```

Library entry points: `c2.commands.sibling.find_structure_twins` /
`structure_survey`.

Corpus at survey time: **182 diffing**, **1339 byte-exact** (1521 compared).

---

## Headline numbers

| signal | count |
|---|---|
| diffing functions | **182** |
| have an exact prolog-twin *anywhere* (same pushes+frame+argc) | 130 |
| have a **cross-family** exact prolog-twin (different `.c` file) | 127 |
| have **no** exact prolog-twin (unique signature) | **52** |
| `Reg`/`Byte-reg swap` residue present (register-identity tie) | **155 / 182** |
| tail-merge dependents (blocked until donor byte-exact) | 77 |

Two facts dominate everything below:

* **Register-identity ties are nearly universal** — 155/182 carry a
  `Reg swap` / `Byte-reg swap` hint, in *every* divergence class. The
  remaining diff corpus is overwhelmingly a register-allocation residue
  problem, not a source-shape problem.
* **A unique prolog signature is a structural smoking gun.** 52 diffing
  functions have a (pushes, frame, argc) triple that **no** byte-exact
  function shares; 34 of those are unique purely because of their
  **frame size**, and 22 of *those* have `ps_frame != rc_frame` — i.e.
  we provably reserve the **wrong amount of stack**.

---

## Where does each diffing function first diverge, relative to its prologue?

Mapping the first non-equal verify row to the prologue boundary:

| first divergence | count |
|---|---|
| **inside the prologue** | 57 |
| at the first body instruction | 31 |
| body +1..3 | 29 |
| body +4..9 | 12 |
| body +10 or deeper | 53 |

57/182 never get past the prologue — the prologue itself is wrong. The
other 125 have a byte-identical prologue and diverge in the body.

---

## Diagnostic partition (mutually exclusive, in priority order)

| class | n | meaning | inference |
|---|---|---|---|
| **A — FRAME wrong-stack-size** | 39 | `frame_hint` set: `ps_frame != rc_frame` | **Structural defect.** Stack-local layout differs: extra/missing/wrong-width local, or different outgoing-arg space (Rule 107). Localised by a single scalar, not per-row noise. |
| **B — prolog encoding / push-set** | 20 | diverges in prologue, frame size equal | Callee-save **set/order differs** (extra/missing push, or a swap). 19/20 already carry a `pragma_hint`. WorthProlog tie / Rule 89 — the number of enregistered values differs. |
| **C — instr-select at 1st statement** | 29 | clean prologue, diverges at body insn 0 | Instruction selection on the very first statement (Reg swap 26/29, Rule 16 19/29). |
| **D — early-body residue (+1..9)** | 41 | clean prologue + opening | Downstream regalloc residue (Reg swap 33/41). |
| **E — deep-body residue (+10+)** | 53 | clean prologue + clean opening | Pure late-body register allocation (Reg swap 38/53). |

`Reg swap` is the top hint in **all five** classes (34/39, 13/20, 26/29,
33/41, 38/53).

### Class A — the wrong-stack-size cohort (22 with a frame delta)

These are the highest-value structural targets: the survey *proves* the
frame is wrong (no exact function reserves this much with this push-set,
**and** `frame_hint` shows the delta). Direction: 23 `ps_bigger`
(PS reserved more — we under-spilled / inlined a local PS kept on the
stack) vs 16 `rc_bigger` (we reserve more — extra/wider local, or we
failed to enregister) across all 39 class-A functions.

```
evolve_a_cm_row              ps=20 rc=48  +28  rc_bigger
setup_enemy_units            ps=64 rc=40  -24  ps_bigger
cap_land_value               ps=32 rc=8   -24  ps_bigger
place3_sprite                ps=20 rc=0   -20  ps_bigger
evolve_forum_activity        ps=20 rc=8   -12  ps_bigger
evolve_industrial_activity   ps=20 rc=8   -12  ps_bigger
set_route_elastic_range      ps=28 rc=40  +12  rc_bigger
build_city_item              ps=24 rc=16   -8  ps_bigger
battle_auto_resolve          ps=20 rc=12   -8  ps_bigger
evolve_region                ps=44 rc=36   -8  ps_bigger
clear_a_reg_area             ps=16 rc=24   +8  rc_bigger
put_rm_area                  ps=16 rc=8    -8  ps_bigger
get_closest_trading_post     ps=16 rc=24   +8  rc_bigger
get_fire_target              ps=28 rc=24   -4  ps_bigger
show_menus                   ps=24 rc=20   -4  ps_bigger
mid_slider_var               ps=12 rc=16   +4  rc_bigger
evolve_security_activity     ps=20 rc=16   -4  ps_bigger
try_this_regionmap_square    ps=20 rc=16   -4  ps_bigger
dock_the_ship_in_good_port   ps=8  rc=4    -4  ps_bigger
test_zone_for_closest_fire   ps=32 rc=36   +4  rc_bigger
trace_back_route_elastic     ps=24 rc=28   +4  rc_bigger
forum_industry_screen        ps=24 rc=28   +4  rc_bigger
```

### Class B — prologue push-set divergence (sample)

The first diff is literally a push being inserted/deleted/swapped:

```
elephant_fire               pragma=structural_divergence   PS push ebx  / RC —
get_entertainment_ov_image  pragma=ps_extra_callee_save     PS push ecx  / RC —
get_industry_ov_image       pragma=rc_extra_callee_save     RC push ebx  / PS —
install_mouse               pragma=callee_save_swap         PS push esi  / RC push edi
show_regionmap_top          pragma=callee_save_swap         PS push ebp  / RC push edi
```

---

## The non-sibling structural twins (the part the request asked for)

127/182 diffing functions have an exact prolog-twin in a **different
source file** — an *unrelated* function that reserves the same stack,
takes the same args, and (for the deep ones) opens with the same
instruction shapes byte-for-byte. When the agreement runs ≥4 opening
instructions, that unrelated exact function is a *proof* that the
recovered prologue + opening shape is generic-Watcom-correct, so the
defect must be downstream:

```
place_a_building_roof   (pm_map1) ~~ place2_a_building_base (pm_map2)  10 insns  cls C
print2_test_info        (pm_map2) ~~ print3_test_info       (pm_map3)  10 insns  cls D
mid3_line_with_sides... (pm_map3) ~~ mid_line_with_sides... (pm_map1)  10 insns  cls C
control_buttons         (controls)~~ show_a_mosaic_frame    (display)   6 insns  cls E
show_cohort_landfill    (landfill)~~ get_allowed_selections (controls)   6 insns  cls E
show_battlemap_base     (pm_map3) ~~ mid2_line_with_sides   (pm_map2)   5 insns  cls E
get_fig_walk_image      (battle)  ~~ sa10_army_demobed      (int_c2)    4 insns  cls D
get_fig_missile_image   (battle)  ~~ sa10_army_demobed      (int_c2)    4 insns  cls D
do_heavy_ai             (battle)  ~~ adjust_culture_criteria(formulae)  4 insns  cls D
figure_go_to_target     (battle)  ~~ act_set_return_home    (action)    4 insns  cls E
grey_a_screen           (lib32)   ~~ clip_zoom_level1       (screens)   4 insns  cls D
place2_a_building_roof  (pm_map2) ~~ trace_forward_ferret   (common)    4 insns  cls C
```

These are squarely the `c2 permute --depth 2` / `c2 decl-swap` lane
(register-identity ties on an otherwise code-aligned function) per
`decomp/AGENTS.md` — the source shape is already right.

---

## What the survey says is wrong with the diff corpus

Sorting the 182 into actionable inference buckets:

1. **~22 (up to 39) have a genuinely wrong stack frame** (class A). The
   structural signature *localises the bug to the stack layout itself*,
   independent of per-row diff noise. Work these with `frame_hint` /
   Rule 107 — an extra/missing/wrong-width named local, or over- vs
   under-enregistration. Highest structural leverage.

2. **~20 have a wrong callee-save set** (class B). The body asked the
   allocator to keep a different number of long-lived values in
   registers, so the prologue push-set diverged. WorthProlog / Rule 89;
   `pragma_hint` already names the sub-case for 19 of them.

3. **~123 have a byte-correct prologue and diverge in the body**
   (classes C/D/E), and **155/182 of the whole corpus carry a
   register-identity-tie hint**. For the 127 with a cross-family exact
   twin (and especially the 12 deep ones above), the recovered SHAPE is
   proven correct — the residue is register allocation, not source. This
   is the `permute`/`decl-swap` lane, not a structural rewrite.

4. **52 have a unique prolog signature** — the ones that resemble *no*
   exact function. 26 of those are also class A: a unique frame size is
   the single most reliable "this function is structurally wrong"
   detector the survey produces. The other 26 are unique on push-set or
   argc and spread across B–E.

**Bottom line.** Structural-twin matching cleanly splits the remaining
diff corpus into a small *structural* tail (~40–60 functions whose
prologue/frame is wrong — chase the stack layout) and a large
*regalloc-residue* body (~120+ functions whose shape an unrelated
byte-exact function already reproduces — chase the register-identity
tie). "Has no exact prolog-twin" + "frame_hint set" is the highest-yield
filter for the structural tail.

---

*Reproducible: `c2 sibling --survey` (the structural lens of the sibling
tool; rebuilds from the cached corpus + `.c2-cache/verify.json`, no
Watcom build).*
