# Stub / mistranslation census

Functions whose RC body has **substantially fewer branch ops** than PS — i.e.
the source was stubbed or only partially transcribed, not merely allocator
residue.  Detector: for each diff function, recover binir for PS and RC code
and count the "branchy" op kinds (`cmp_jcc`, `zero_test_jcc`, `branch_jmp`,
`branch_flag_jcc`, `loop_rotation_*`, `backjump_shared_call`).  A large
`PSbr - RCbr` delta means RC is missing control flow → a stub.

Regenerate with the kernel snippet in this session's notes (build once via
`_build_all`, then `_binir_for_code` on PS/RC code per `c2 dossier` helpers).

## Workflow for each

1. `c2 dossier <fn> --no-mac` → read IR-multiset + prologue.
2. `c2 mac-decompile <fn>` → the CodeWarrior body is the structural oracle
   (control flow + constants reliable; **pointer-arithmetic offsets are NOT** —
   the decompiler mis-types `&global` and reports e.g. `+0x36` for a `+0x32`
   field).
3. `c2 disasm <fn>` → PS Ghidra has the **authoritative field offsets**
   (`citizen_list+0x2`, etc.) and operand order (watcall: eax=arg0, edx=arg1).
   Use PS to nail every field/const/operand.
4. Rewrite, verify, commit.

## Done this session

- **business_output** (was PS65/RC1, 4-line stub) → full supply/growth
  computation reconstructed. Commit `evolver: business_output real body`.
- **show_people_query_panel** (was PS57/RC16, only type==1 handled) → full
  type 1-7 word_health dispatch + `font_format_split`. Commit `screens:
  show_people_query_panel reconstruct word_health type dispatch`.
- **evolve_region** (was PS100/RC50, ~50% transcribed) → full warehouse/mine
  dispatch. Fixed skip-flag offset bug (occupant&3 at +7, not edge_bits&3),
  added 0x97/0xd3 + four missing warehouse ranges (0xdc-0xeb), removed bogus
  0xc0-0xcf case. All 18 calls + kind-compares now present. Residue is now
  pure allocator frame-spill cascade (PS frame 0x2c vs RC 0x24); the body
  bytes mostly align (diff barely moved despite +800 bytes of code). Commit
  `evolver: evolve_region reconstruct full warehouse/mine dispatch`.

  Reusable facts for the sibling evolve_* / place3_sprite reconstructions:
  - region_cell: base_kind +0, edge_bits +3, gfx +4, outside +6, occupant +7
  - warehouse goods nibble = occupant>>4; fill-state = (occupant&0x1c)>>2;
    trader-kind = occupant&0x60 → {west,east,south,north}_trader_brings
  - province goods fallback: region_sources[province_is].choices[3|6]
  - industry delivered accumulator: industry[g].supply_pipeline[1] (+0x20)
  - tier base: `kind - 0xNN` for warehouses, `gfx - 0xNN` for mine/farm.
  - Mac control flow + constants reliable; Mac field offsets WRONG (verify
    every one against `c2 disasm`).
- **place_sprite** — inlined `draw_citizen_pass` twice (PS inlines it; RC
  called it). Commit `pm_map1: inline draw_citizen_pass`.
- **put_reg_x2_area** — inlined `put_reg_sized_area` helper (PS has body
  inline). Commit `map: inline put_reg_sized_area`.
- **bd** → EXACT (asymmetric step_error branch).
- **put_rm_area** — `region_map[off]` not `region_map[cm_sptr]` (off was
  computed but dead-code-eliminated).

## Remaining candidates (delta = PSbranches - RCbranches, post-fixes)

| delta | PS/RC | size | function | notes |
|------:|------:|-----:|----------|-------|
| 50 | 100/50 | 2292 | `evolve_region` | big; likely several sub-blocks stubbed |
| 44 | 69/25 | 2134 | `place3_sprite` | **big.** needs `place3_sprite_figure` + `place3_sprite_arrow` inlined (don't exist as fns; partial/wrong inline present). figure pass missing sprite-data load + 3-way refresh_figure dispatch + multi-part sub-figure loop (fight_state==2, figure+0x4a). figure_rec: sprite_anim +2, sprite_dir +3, fight_state +4, direction +6, arrow_data_ptr +0xA, sprite_data_ptr +0xE, wf_step_x +0x22 (anim sub-frame, table index = dir*8 + wf_step_x). stride 0x58. |
| 19 | 93/74 | 1820 | `evolve_a_cm_row` | **half-transcribed** (RC 187 vs Mac 358 lines). City-cell evolution dispatch over many kind ranges (housing 0x82-0xa1, 0xa2-0xa5..0xb9, 0xc0, 0xd7-0xe2). Same field-offset playbook as evolve_region. |
| 16 | 48/32 | 1631 | `battle_auto_resolve` | partial |
|  9 | 36/27 | 1452 | `get_query_info` | partial |
|  9 | 21/12 | 753 | `evolve_industrial_activity` | calls business_output |
|  8 | 43/35 | 761 | `test_rm_elastic_range` | |
|  8 | 42/34 | 761 | `test_elastic_range` | |
|  8 | 9/1 | 265 | `exit_game` | **NOT a stub** — PS symbol range over-extends past `jmp exit` into an unnamed following function (video-reset/init). Boundary artifact, skip. |
|  7 | 51/44 | 1107 | `try_this_regionmap_square` | documented allocator residue PROBE |
|  7 | 35/28 | 629 | `clear_an_area` | |
|  5 | 38/33 | 1575 | `setup_enemy_units` | |
|  5 | 19/14 | 624 | `evolve_security_activity` | |
|  4 | 27/23 | 842 | `evolve_amenity_cover` | |
|  4 | 26/22 | 488 | `test_fire_zones` | |
|  4 | 24/20 | 499 | `get_population_and_industry_count` | |
|  4 | 20/16 | 420 | `figure_update` | |
|  4 | 20/16 | 315 | `reg_road_ramifications` | |
|  4 | 19/15 | 438 | `check_goods_in_region_warehouses` | |
|  4 | 6/2 | 321 | `stop_system` | small; check |

`show_people_query_panel` still shows delta 4 because the reconstructed tail
is structurally complete but a couple of compares differ at the allocator
level (frame off by 4 bytes); not a stub anymore.
