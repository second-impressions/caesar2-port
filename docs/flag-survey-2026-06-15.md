# Compiler-flag survey — PS.EXE is a single-toolchain baseline-flag build

**Question (user-driven):** is the ~13% non-byte-exact residue a flag
issue — a flag we got wrong, a flag *combination*/ordering, or *different
flags per TU* (Watcom links per-`.obj`)?

**Verdict: no.** The whole game code was built with the baseline flags
`-bt=dos -mf -4r -s -d1` (unsigned char, OptSize=50), one toolchain, no
per-TU variation. The residue is irreducibly source-shape.

> The one-off `tools/flag_survey*.py` harnesses referenced below were
> removed after the question was settled (2026-07); recover them from git
> history at this doc's vintage if the survey ever needs re-running.
> The banked results live in `data/flag-survey/`.

## Method & a masking bug we had to fix first

`tools/flag_survey.py` (vs-baseline) and `tools/flag_survey_vsps.py`
(vs-PS) compile each TU in isolated podman runs (every `.obj` archived),
parse per-function bytes, diff masked.

**Critical correction:** the first vs-PS harness used compiler-id's
`_diff_bytes`, which masks the fixup table but **not** rel32 call/jmp
*displacements* (link-positional noise — a tail `jmp X` to a function at a
different address). That produced dozens of phantom "wins" (e.g.
`clear_all_cm` "flipped to exact" under `-oc` — but it was 2 bytes of a
`jmp rel32` displacement that decomp-verify already masks). Verified the
compile itself is identical standalone-vs-full-build (0 bytes); only the
**masking** differed. Fixed by adding decomp-verify's
`_rel_call_jmp_disp_mask`. After the fix the standalone baseline exact
counts match the full build (common 54/54, loadsave 27/27, map 102/138…).

## Results (corrected masking)

* **Single-flag sweep (52 flags incl. the "fixed" ones):** free variables
  neutral on all 34 TUs are `-ei`, all `-fp*`, `-om/-on/-op`, `-oz`, `-r`,
  `-zp1`, `-zm/-zg/-zdp`. Everything else (calling conv, `-j`, `-ri`,
  every aggressive `-o`, `-st`, `-zp2/4/8`, `-zc/-zdf/-zu`, `-en/-ee`,
  `-d2/-d3/-d1+`, dropping `-s`) breaks byte-exact TUs.
* **`-o` subset survey (all subsets 1..3 = 833 configs):** 0 configs are
  neutral-on-exact-and-active-on-residue. No config with a "breaking"
  letter is ever neutral on exact (no order-cancellation escape, even
  though `-o` order *is* non-idempotent).
* **vs-PS, binary exact, per-TU best config:** every TU's best is
  BASELINE. **No flag (single, combo, or per-TU) flips any residue
  function to byte-exact.**
* **vs-PS, function-level diff-count:** 115/150 residue functions get
  *closer* to PS under *some* flag, but: (a) the helping flag varies per
  function across 13 mechanisms, (b) reductions are mostly partial
  (`evolve_a_cm_row` 1216→1101), (c) the one clean exact-flip
  (`get_water_ov_image`→0 under `-ol`) is net **−2** on its TU (breaks 3
  to fix 1). So no flag is even a per-TU win.

## What the function-level data IS good for

The flag that most reduces each residue function's diff is a **source-shape
hint** — it names the codegen mechanism our baseline source under-produces
vs PS (catalogued in `docs/function-flag-hints.json`):

| flag | mechanism hint | example residue fns |
|---|---|---|
| `-j`  | a field/var should be **signed char** | `sf14_opertunist_fire`, `start_move` |
| `-oa` | cache a **global/pointer in a local** | `get_industry_ov_image`, `show_regionmap_top` |
| `-ol` | **loop** restructure | `build_wall_from_elastic`, `get_water_ov_image` |
| `-oc` | `call;ret` vs **tail-jmp** | `put_x2_area`, `set_range`, `run_to_new_aqua_node` |
| `-oe` | **inline** expansion | `fly_to_target`, `reg_road_ramifications` |
| `-os/-ot/-or/-ox` | strength-reduction / instr-selection / reorder | the big elastic/evolve walkers |

These are per-function source-shape levers (the regalloc/structural grind),
NOT a toolchain knob.

## Conclusion

Combined with the version sweep (no Watcom 9.01e..11.0c reproduces the
framed mid-epilogue) and the mixed-vintage `.obj` survey (ruled out), the
flag space is exhausted: **single-toolchain, baseline flags, no per-TU
variation.** The residue is source-shape. Reproduce:
`tools/flag_survey_vsps.py {single,o13,o14}` (SURVEY_WORKERS<=6).

## Addendum — exhaustive search (4390 configs, 144,870 compiles)

`tools/flag_survey_full.py` searched the full codegen-flag space with the
corrected masking and a **global total byte-exact** metric across all 33
C TUs (baseline = **1219** exact; verified == the full-build count, so the
standalone harness is faithful):

* single-dimension deviations, all `-o` subsets size 1..4 + **permutations
  of the order-sensitive `{d,s,t,x}` letters** (non-idempotent), pairwise
  cross-dimension combos, and the callconv×char×debug×packing cross-product.

**Result: baseline is the unique global maximum.** No config beats 1219;
the only ties are inert free variables (`-3s/-4s/-5s`, `-ei`, `-r`, `-zp1`,
`-zc/-zm/-zg/-zdp/-zff/-zfp/-zgf/-zgp`). **Every TU's best config is
BASELINE** — no per-TU flag variation.

Only **4** residue functions flip to byte-exact under any flag (all with
heavy corpus losses, so none is a flag PS used):
`copy_ferret_run_to_citizen` & `sa16_army_lurk_round_coast` (the `~pad`
jump-table-filler class), and the two genuine code-level flips
`get_water_ov_image` (`-ol`) and `show_history_graph` (`-oa`).

**The earlier "~50 flips" were a masking bug:** 49/52 were byte-exact at
baseline once rel32 call/jmp displacements are masked (the code was
identical; only the link-resolved displacement bytes shifted with layout
and coincidentally re-matched PS under some flags). See
`docs/flag-full-flips.json` for the 4-function flip catalog and
`/tmp/flag_full_funcdiffs.jsonl` for the full per-function diff stream.

**Toolchain question closed:** PS.EXE's game code is built with
`-bt=dos -mf -4r -s -d1` (unsigned char, OptSize=50), single toolchain,
no per-TU variation. The residue is irreducibly source-shape.
