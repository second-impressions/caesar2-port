# Compiler-flag survey results (CLEAN run 2026-06-15)

`tools/flag_survey_full.py` (1603 pruned configs x 33 C TUs = 52,899
isolated wcc386 10.0a compiles), analyzed by `tools/flag_survey_analyze.py`
+ the atomic per-flag pass.  (The survey scripts were removed 2026-07 —
the flag question is settled; recover them from git history if needed.) Metric: byte-exact-vs-PS count with
**tail-merge-aware** masked diff (`_dm`: compare min(len), mask fixups
[fixed FIXUPP parser] + rel32 call/jmp disp, NO length-mismatch term).

## Headline
* **Baseline `-bt=dos -mf -4r -s -d1` is the UNIQUE global maximum**
  (1227 byte-exact). No config beats it; ties are inert/ABI-neutral.
* **Every TU's best is baseline EXCEPT int_c2 68->70 under `-en`** (enum
  size) -- but that +2 is the `~pad` jump-table-filler class (fight_barbarian,
  copy_ferret_run_to_citizen), not a real codegen win.
* **6 flip-to-exact fns**: 3 are `~pad` filler artifacts
  (copy_ferret_run_to_citizen, fight_barbarian, try_this_battlemap_square);
  the genuine code-level levers are `screens:show_history_graph` (-oa),
  `landfill:get_water_ov_image` (-oc/-ol), `evolver:update_time` (-j/-o*t).

## History of corrected bugs (why earlier numbers were wrong)
1. rel32 call/jmp displacement not masked -> phantom diffs/flips (fixed).
2. `_dm` added extra=abs(len(PS)-len(RC)) -> tail-merged PS stubs
   mis-scored (evolve_a_building 127 vs true 1); dropped the extra term.
3. `parse_obj_functions` FIXUPP desync (variable-length OMF index fields +
   P-bit) -> phantom fixups that masked real diffs when a layout-shifting
   flag moved a function's .obj offset onto the diff byte (caused the FALSE
   evolve_a_building/-j "flip"). Fixed in c2/parsers/omf.py.
After all three: evolve_a_building is genuinely 1 byte off (tail-merge
doesn't fire) under ALL flags -- NOT closable by any flag.

## Files
| file | what |
|---|---|
| `funcdiffs.jsonl.gz` | RAW: baseline full per-fn diffs + per-config deltas |
| `results.json.gz` | per-config total + per-TU exact + gained/lost |
| `flips.json` | the 6 flip fns -> configs |
| `by_function.json` | 206 residue fns: baseline, min, reduction, flip, hint flags |
| `by_tu.json` | per-TU whole-TU movement |
| `atomic_by_flag.json` | per single-flag global + per-TU stats (clean) |
| `atomic_by_function.json` | per-fn best atomic flag + all reducers |
| `inert-flags.md` | the 22 inert flags dropped + why |

## Per-function source-shape levers (atomic_by_function.json)
`-j`=signed-char field/global (pervasive: check_goods_in_region_warehouses
177->22, action, business_output, init_census, ...); `-oa`=cache global/ptr
in local; `-ol`=loop; `-oc`=call;ret vs tail-jmp; `-ee`=epilogue shape
(unusual: get_city_mood 275->122, figure_update). `-os`/`-3r` dominate by
volume but are global-only (OptSize / 386 scheduling), NOT per-function
actionable. `-zu`==`-oo` are an inert SS!=DS layout artifact (ignore).

## `~pad` class resolved (jump-table alignment filler)
`copy_ferret_run_to_citizen`, `fight_barbarian`, `try_this_battlemap_square`
are **code byte-exact** -- decomp-verify already counts them exact (`~pad`,
"cluster #32 version delta"). Their only diff is the trailing jump-table
**alignment NOP filler**: PS pads with `8d 40 00` (3-byte `lea eax,[eax]`
NOP), the standalone `.obj` with `90` (1-byte NOP), and the table sits at a
different segment offset pre-link (table entries are fixup-masked). Pure
layout artifact, not code. The survey's "flips" on these were `_dm` not
masking the filler; `_dm` now ports decomp-verify's `_trailing_table_pad_only`
(diffs all after the last ret, in a fixup-dense table + <=7-byte pad) so they
read 0. Effective baseline is 1230 (1227 + these 3); the committed
flips.json/tables predate this `_dm` fix and still list the 3 as flips.
