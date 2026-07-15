# Frame-lever census (2026-06-10)

PS-side corpus sweep with the new machine levers (`c2/commands/
frame_hints.py`, binir `farptr_ret_const`/`regpair_const_exit`,
`tail_merge.trace_epilogue_chain` / `classify_regpair_exit`).  Rerun
recipe: disassemble every code symbol from symbols.json, apply the
detectors (see the sweep cell in this commit's session; ~30 s).

## EDX:EAX constant pairs at exits — 65 sites

* **5 genuine far-ptr returns** (resolved `RETURN`: jmp chain → pops+ret):
  `start_samples` (0,4)(0,1), `start_sequences` (0,1) **(1,2)=MK_FP(1,2)**,
  `start_sound` (0,3) — the pcsound Rule 85 family, all already
  note-documented.
* **58 arg-pair merges** (resolved `ARGS`: jmp → shared CALL tail).
  ComTail factored out byte-identical call sequences; the pair is the
  callee's (eax,edx) watcall args.  Families: `get_census` (6 sites,
  codes 106–111), `get_new_tribute` (12 sites, 122–146),
  `show_ov_legend_panel`, `act_*` menu handlers, `*_game_loop`,
  `show_*`/`forum_*` UI panels, `this_region_box`, `update_tribune_flag`,
  `clear_sized_to_rubble`, `place_9_legend_blocks`, `show_estimate`,
  `battle_stats_panel`, `random_event`, `show_emperor_message`,
  `start_tune` (its 2 sites feed an `add esp,4` cleanup tail).
  **Lever**: the RC source must produce IDENTICAL call shapes at every
  merged site (same args-in-registers form) or the factoring cannot
  reproduce — check these before chasing per-site byte diffs in any of
  the listed functions.

## Foreign-frame writes — 304 functions

* **249 custom-convention/asm** (unsaved callee-save writes from
  offset ~0, empty push set): the `write_*_diamond_*` compiled-sprite
  blitter family (~230), Smacker (`_Smack*`), AIL asm (`_AIL_API_*`,
  `_AILA_*`, `_AILSSA_*`), CRT internals (`__prtf`, `__brk`, `__qread`,
  `formstring`, `malloc`, `__int386x`), and the mouse/INT-handler group
  (`install_mouse`, `get_mouse`, `show_mouse`, `get_mouse_droppings`,
  `timer`, `exit_game`, `stop_system`, `go_16m_palette`,
  `edit_format_buffer`, `one_letter`, `xclip`, `yclip`, `do_32_count`).
  These are NOT C reconstruction targets in the normal sense (pragma
  aux / hand asm / generated code).
* **Genuine hosted-block candidates** (wcc-style head, LATE unsaved
  writes — Rule 125 queue motion):
  | function | saved | foreign writes |
  |---|---|---|
  | `sf14_opertunist_fire` | ebx,ecx,edx | esi@+0x301, edi@+0x6e3 |
  | `run_anti_ferret` | ebx,ecx,edx,edi | esi@+0x15c |
  | `copy_ferret_run_to_citizen` | ebx,ecx,edx | esi@+0x8e |
  | `try_this_battlemap_square` | ebx,edx | esi@+0xb7 |

  **`copy_ferret_run_to_citizen` is byte-exact** — proof that hosted
  blocks DO reproduce when the family/queue compiles in order (Rule 15
  "decompile the whole family in order").  So the foreign-frame hint
  means "fix the queue", not "impossible".

## Epilogue chains

`battle_action` → `scroll+0x154`, restores `edi esi edx ecx ebx`;
RC missing `ecx` (PS holds the Rule 110/126 byte temps CL/CH there).
pcsound funnel: `0x118df` (pop ebp) → `0x13181` (pop edi esi edx ecx
ebx; ret) — chains HOP; `0x118da` (`mov eax,1`) is a shared
multi-function constant-return site (jumped to by 0x225f/0x2274).
