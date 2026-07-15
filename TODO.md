# TODO — live remaining work

Updated 2026-07-14 (evening pass).  This file is intentionally a short list
of unfinished work.  Completed campaigns and stale corpus snapshots belong in
git history and the dated documents under `docs/`, not here.

The live function dispatcher remains `c2 worklist`; do not trust a count in a
document over the current tools.

## Current verified state

- `c2 worklist --no-refresh`: **0 diffing functions**.
- `c2 decomp-verify --json --no-strict`: **1522/1522 exact** — and this now
  includes the **branch-target audit** (dc83bf15): every masked rel-branch
  displacement is resolved symbolically on both sides, so a call/jump to the
  wrong symbol or a different ComTail merge point can no longer hide behind
  the rel32 mask.  Zero false positives corpus-wide.
- Final-link comparison (`c2 rebuild`, every line exact):
  - game C 1435/1435 · c2-asm 87/87 · av-delink 517/517 · crt 195/195;
  - initialized data 341/341; LE sizes all exact;
  - **placement**: code starts 2233/2234 exact + 1 `~alias`
    (`sound_error_` — label-only, byte at PS position correct); data
    placement 1538/1538 named exact, 58 statics via delink/anchor
    (module-aware dup-name pairing; the old false AIL `_dig` report is
    fixed);
  - **strict whole-code-object: 0 differing bytes / 508368** with only
    loader fixups masked and every relative branch displacement visible.

## Closed 2026-07-14 (this pass — see git for postmortems)

1. **Strict code stream (was 15 bytes / 9 ComTail sites) → 0.**  Every site
   encoded a real source fact the masked oracle hid:
   - `act_set_patrol_stop`: spurious `save_undo_info()` call deleted;
   - `war_trouble`: int contract (return 0/1), the raider/horde family
     `if (a && b) { … return 1; } return 0;` shape, and the definition moved
     to after `horde_trouble` (WIN address order + the L165-192 `-d1` gap
     prove it; Watcom hauls the body to region_trouble's fall-through and
     strips its line marks — our compile reproduces this, line-compare
     clean).  The `uprise.wav` const-order hack died with it;
   - `do_a_tutorial_page`: the missing-pl8 skip path falls through to the
     challenge wrap-up (it never returned early);
   - `show_fx_box`: autosave-on glyph is the constant 3, not `p1`;
   - `show_exit_box`: missing `hold_mouse_replace = 1;`;
   - `clear_sized_to_rubble`: out-of-range kinds return early (sound +
     refresh are in-range-only) + PS's one-line-per-kind `-d1` layout.
2. **Verifier/reporting** (old §1.1/§4): `c2 rebuild` strict metric +
   placement metrics; `decomp-verify` branch-target audit; AGENTS.md hint
   table updated.
3. **Allocator spellings** (old §2): **ALL 11 S1 sites CLOSED — the
   corpus is free of every duplicated-store / self-store spelling**:
   - `show_left_overlay` / `show_right_overlay`: PS's true `ov_image`
     named local recovered from its own asm (sub computed once before the
     0x96 test; two natural stores ComTail-merged);
   - `mid3_line_no_sides_base` / `mid3_line_with_sides_base`: the
     POSITIVE terrain guard recovered (`if ((tile & 0xc) != 0) { draw;
     continue; }`, zero case falls through naturally) — the old early
     `goto terrain` produced the same final CFG but a different
     pre-optimization block chain; plus the middle-path
     `dirty = dirty & 0xf0` self-form seating the lookup temp
     (7be7ea37, 71e0ce76, 7c2ef6f3, 9be405fb);
   - `show_battlemap_base`: the same positive guard in both edges + PS's
     cross-arm `goto top_draw`/`goto bottom_draw` into the
     update-virtual's call, pinning PS's 2-insn ComTail merge (both
     arms' stores land in EAX here, so a structured call copy lets
     ComTail over-merge a 3-insn tail with the terrain-REAL arm).  Also
     earlier: the Rule 109 comma self-store and the `= tile & 0xf0`
     triple deleted (Mac-PPC-witnessed forms).
   Every function byte-exact with line-compare clean.
4. **Score-chain tooling** (49fd342e): `c2 spell` now follows `sb.into`
   edges transitively from each lcx0 site with line/block provenance —
   the lever that made the pm_map3 search actionable.

## 1. (closed) — no open allocator spellings remain

The former §1 (duplicate const stores) is fully resolved; see the closed
list above and the function comments in `pm_map3.c` / `pm_map1.c` for the
mechanism postmortems (positive terrain guard, cross-arm goto merge
pinning, Score-coalesce `lcx0` history).

## 2. Header provenance, not data placement

Unchanged: corroborate original header filenames / include graph and the 35
non-data lib32 slots only if an external source artifact appears.  Do not
sacrifice exact BSS placement for an unsupported filename guess.

## 3. Optional inverse-compiler research

- make CalcSavings/TooGreedy lookup round-aware; close the two remaining
  TooGreedy certification misses;
- derive block live-OUT dataflow instead of consuming recorded `bs` values;
- model conflict-graph id-bit channels, not only `with.regs`;
- finish the sequential feedback driver (hypothetical early seat through
  FixInstructions, recompute later masks/credits);
- classify the 13 open rover-attribution rows and the minor parm-promotion /
  realization-gate anomalies.

## Explicitly out of scope for the current binary pass

- byte-exact Watcom debug section;
- original source file/path strings and file naming;
- the `sound_error_` public/debug alias location while debug metadata
  remains excluded (now reported distinctly as `~alias` by the placement
  metric).
