# Rule 107 slot-order: trace-grounded ground truth (2026-06-25)

**Status: the full slot-assignment pipeline (creation → BuildNameConflicts
sort → AssignTemps sort → SetTempLocation) is modelled, every comparator +
the non-stable ShellSort reproduced offline, and PS's slot order is PREDICTED
on 130/130 byte-exact functions.  The non-stability is the WHOLE mechanism for
same-size slot swaps — not a size-mixing edge case.  Source levers narrow to
temp-set changes (local reuse/scope), NOT decl-order.**

This supersedes the 2026-06-24 draft, which held two now-disproven claims:
that `SortCmp_flag2_2b` is "stable for same-size" and that same-size swaps
arise *only* when size=1 and size=4 temps are interleaved (the "size-mixing"
story).  Both are wrong — see PROOF below.

## The pipeline (verified in the 10.0a binary via pyghidra at `~/git/ReverseEngineering/watcom10.0a`)

```
nb1   (front-end temp creation = DECLARATION order;
       +0x24 = reverse-decl-rank id, assigned at decl time)
  │  BuildNameConflicts sort
  ▼     comparator  AllocBefore @0x5905b
        sort engine  DoSortList @0x665c4 → ShellSort @0x66689  (UNSTABLE;
                     alloc-failure only → MergeList @0x66566 stable)
nb2 == nt_pre   (the AssignTemps input)
  │  AssignTemps sort  (AssignTemps @0x55463)
  ▼     comparator  SortCmp_flag2_2b @0x55503  (OW v1 name TempAllocBefore;
        10.0a's is flag/offset-keyed, NOT size-only)
        sort engine  same DoSortList → ShellSort
nt_post   = AllocNewLocal @0x558d4 walk order
  │  for each NEEDS_MEMORY/!HAS_MEMORY/!ALIAS temp:
  ▼     AllocNewLocal → CalcRange + ReUsableStack (reuse if ranges don't overlap,
        else fresh slot) → SetTempLocation @0x4e6bb
[esp+N] offsets   (SetTempLocation: locals.size += size;
                   t.location = -locals.size - base; first → highest [esp+N])
```

`nb2 == nt_pre` — the BuildNameConflicts sort output IS the AssignTemps
input (no intervening reorder).  So the slot order is two cascaded
non-stable ShellSort passes applied to the declaration-order temp list.

### The two comparators (decompiled from the binary)

`SortCmp_flag2_2b @0x55503` — `before(x,y)` returns 1 iff x sorts before y:
1. **ALIAS bit** `byte[+0x2b] & 0x2` — alias temps sort first;
2. **`n.size`** `[+0x8]` — smaller first;
3. **`[+0x24]`** — if DIFFERENT, the comparator returns FALSE *both* ways
   (sort-equal); if EQUAL, fall through;
4. **`[+0x10]`** (`v.offset`) — DESCENDING (larger first), only when `+0x24`
   is equal.

`AllocBefore @0x5905b` — `before(x,y)`:
1. **CONST_TEMP bit** `byte[+0x2b] & 0x1` — non-CONST sorts before CONST;
2. **has-conflict** (`v.conflict` `[+0xc]`) before no-conflict;
3a. both have conflict → **savings DESC** (`conflict->savings`);
3b. both no-conflict → **`[+0x24]` DESC**.

`[+0x24]` is a per-temp id assigned by the front-end at declaration time —
empirically the **reverse-declaration-rank** (on `evolve_water_table` the
six byte locals get `+0x24` = 7,6,5,4,3,2 in reverse decl order:
tier=7, kind=6, variant=5, counter_sum=4, sprite_count=3, supplied=2).

## Why same-size slot swaps happen (and why it is NOT about size-mixing)

On `evolve_water_table` the 21 size=1 temps all have **distinct `[+0x24]`**
and `+0x10`==0, so step 3 of `SortCmp_flag2_2b` returns sort-equal for *every*
pair.  A STABLE sort would therefore preserve the input order unchanged.  But
`nt_post != nt_pre` — e.g. `supplied` moves `nt[2] → nt_post[1]`.  The
reordering *is* the ShellSort non-stability (gap-passes dragging an element
across a sort-equal peer).  This fires with **no size-mixing required**: the
list can be uniformly same-size and still reorder.  (The old "size-mixing"
story survives only as one way to *trigger* a different list shape; it is not
the mechanism.)

> **2026-07-09 counter-example (evolve_region, commit ad1de9e7): decl-order
> CAN be the slot lever — as a COMPOSED permutation.**  The single-swap
> argument below is correct as far as it goes (one swap moves position +
> `[+0x24]` rank together), but the coupled perturbation is NOT closed
> under composition: a 503-variant byte-oracle sweep (ForgeBuilder LE,
> ~0.1 s/variant) found 9 single decl swaps taking evolve_region 56→6 bd,
> and a second sweep on that baseline found `wkind<->skip` closing it to
> BYTE-EXACT.  evolve_water_table's 24/24 miss was a permutation search of
> the four SPILLED locals only — the winning evolve_region swaps involve
> NON-spilled locals (`t`, `skip`) whose rank shifts re-seed the ShellSort
> for the spilled pair.  Read "decl-order insufficient" claims as
> "insufficient within the probed subset"; the full decl-perm space is
> cheap to sweep and should be exhausted by machine before reaching for
> temp-set surgery.

### Why decl-order is NOT a slot lever (single swaps of the spilled pair)

A decl reorder moves **both** the temp's `nb1` position **and** its `[+0x24]`
rank together (the rank is re-derived from the new decl order at decl time),
so the sorts see a coupled perturbation, not an isolated reposition of one
local.  *Proven, not guessed*: all 24 decl-order permutations of
`evolve_water_table`'s four spilled locals were recompiled and simulated —
none produces PS's target slot order.

The real levers are **temp-set changes** (local reuse merges / scope moves /
statement reorder), which change *which* temps and *how many* exist — that
renumbers the `[+0x24]` ranks of the survivors, which the non-stable sorts
then resolve into a different slot order.  The Mac oracle (same source, same
spill pattern) shows PS reused byte locals where our RC over-decomposed.

## Instrumentation (`tools/patch_trace.py` in the sister repo, `.obj`-byte-identical gate)

`~WV1` records per routine (parsed by `c2/regalloc/trace.py`, cache v41+):

* **`nb1`** / **`nb2`** — `Names[N_TEMP]` walked before/after the
  BuildNameConflicts `SortList` @0x59137.  Fields per node: `name` ptr,
  `conf` (`v.conflict` [+0xc]), `size` [+0x8], `usage` (low byte NEEDS_MEMORY/
  HAS_MEMORY/…), `flags` dword [+0x28..0x2b], `loc24` [+0x24], `off10` [+0x10],
  `sort_sav` (deref `name.conflict->savings`, the value AllocBefore saw).
* **`nt`** / **`na`** — same walk around the AssignTemps `SortList` @0x55498.
  Same fields (incl. `off10`/`loc24`, the `SortCmp_flag2_2b` tie-breaks).
* **`an`** — AllocNewLocal @0x558d4 entry hook; one record per spill candidate.
  Pair with the next `st` (SetTempLocation) — present ⇒ fresh slot, absent ⇒
  ReUsableStack-coalesced.  The `an` sequence IS the slot-commit order; `st`
  is the fresh-slot subset that grows the frame.
* **`bb`** — `DAT_0007f914` (BlockByBlock).  When 1, BuildNameConflicts'
  savings sort is SKIPPED (nb1/nb2 empty); slot order then depends on
  per-block name-list mutations, not a global savings sort.

## Validation

Offline simulators in `c2/regalloc/shellsort_sim_slots.py` (decompiled from
the binary):

| gate | result |
|---|---|
| `predict_nb2(nb1)` reproduces the real `nb2` | **441/456** routines (the 15 misses are block-by-block / alias-heavy edge cases the `bb` probe flags) |
| `predict_nt_post(nt_pre)` reproduces the real `nt_post` | **232/232** |
| `predict_slot_ptrs(nt_pre)` predicts the PS `[esp+N]` slot order on the byte-exact corpus | **130/130** (RC==PS, so the `an` order IS PS's) |

The 130/130 gate is the load-bearing one: it proves the simulator *predicts
PS*, not merely reproduces RC.  So any candidate source edit's `nt_pre`
(recompiled) can be pre-validated against PS's target offline.

Caveat: removing/merging a local renumbers *all* temps' `[+0x24]` globally,
including the ~47 unnamed temps in a typical function; those renumbered
ranks cannot be predicted from source.  So an edit's effect still requires
one recompile to fetch its `nb1`/`nt_pre` — but the simulator then confirms
in milliseconds whether that `nb1` → the target order, before any commit.

## The actionable technique (every slot-swap diff)

1. **`c2 regtrace <fn>`** — the parsed `an` list (`r["an"]`) is the ground-truth
   slot-commit order; `r["nt_pre"]`/`r["nt_post"]` give the sort input/output.
2. **Read PS's slot order from the asm** (`c2 disasm <fn>`: follow `[esp+N]`
   displacements at each spill store/reload).
3. **Per the swap class (see below)**:
   * **temp-set divergence** (PS reused a local our RC split — confirm via the
     Mac/Win oracle): reconstruct PS's local set; each candidate recompile's
     `nb1` is pre-validated by `predict_nb2` → `predict_nt_post` offline.
   * **a swap attributable to differing sort-time *savings***: read `sort_sav`
     on the `nb1`/`nb2` records; AllocBefore keys on it for both-have-conflict
     pairs.  PS's source must have produced different savings — change a
     use-count (see `show_menu_items` below).
   * **a same-line register PARAM swap**: still open.  `swap params in the
     signature` is a SEMANTIC regression (Mac PPC + Win MSVC both reject it).
     The trace lets you compile any candidate edit and SEE whether it shifts
     the `an` order toward PS.

## Per-function status (the stuck slot-swap cases)

| function | bytes | class | status |
|---|---:|---|---|
| `evolve_water_table` | 363 | temp-set divergence (Mac reused locals) | `predict_slot_ptrs` narrows the target to ONE relative nt_pre order; 24/24 decl perms miss it (proven; decl is insufficient). Lever = Mac-faithful local-reuse merges; each candidate recompile's `nb1` pre-validated offline. |
| `build_units_figures` | 5 | same-line PARAM slot swap | same-line-PARAM lever not isolated; trace + sim let candidates be pre-validated. |
| `show_menu_items` | 207 | savings-keyed (sort-time savings differ from later `al` savings) | `sort_sav` on `nb` records shows `y(13) > text_group(12)` at sort time → y first; PS source must have had `text_group` savings ≥ y's. Lever = change a use-count. |
| `test_zone_for_closest_fire` | 298 | mostly size=4, 2 size=1 | PARTIAL — covered by the same ShellSort-non-stability class. |
| `build_road_from_elastic` / `build_reg_road_from_elastic` | 19/469 | named subset interleaved with anon coalesced temps | Lever = reorder the named subset's creation; pre-validate offline. |
| `build_an_area` | 274 | misbucketed | `c2 diagnose: fix-next ir` — not a slot-swap at all. |

## Files

* This document: `docs/slot-swap-survey-2026-06-25.md` (supersedes the 2026-06-24 draft).
* Simulators: `c2/regalloc/shellsort_sim_slots.py`
  (`predict_nb2`, `predict_nt_post`, `predict_slot_ptrs`) — canonical; the
  older `c2/regalloc/shellsort_sim.py` predates the BuildNameConflicts half
  and is kept only as a historical harness.
* Instrumentation: `~/git/ReverseEngineering/watcom10.0a/tools/patch_trace.py`.
* Parser: `c2/regalloc/trace.py` (`nb1`/`nb2`/`nt_pre`/`nt_post`/`an` per
  routine, cache v41).
* Canon: `docs/wcc386-re/regalloc-model.md` § "The slot-assignment pipeline"
  + Rule 107 in `docs/watcom-codegen-patterns.md`.
* 10.0a binary sites: `AssignTemps@0x55463`, `SortCmp_flag2_2b@0x55503`,
  `AllocBefore@0x5905b`, `DoSortList@0x665c4`, `ShellSort@0x66689`,
  `MergeList@0x66566`, `BuildList@0x66532`, `AllocNewLocal@0x558d4`,
  `ReUsableStack@0x5561e`, `SetTempLocation@0x4e6bb`, `BuildNameConflicts@0x590ab`.

## 2026-07-10 addendum — the chain is CLOSED and corpus-validated

The full slot pipeline is now modeled end-to-end (see
`c2/regalloc/shellsort_sim_slots.py`, esp. `validate_routine_chain`) and
validated at 100 % on the byte-exact corpus:

| stage | model | validation |
|---|---|---|
| source → temp births | `nb` trace records (AllocName@0x39ab7 exit + caller; SAllocTemp/STempOffset entry probes `nbc`/`nbo` give the CREATING PASS) | — |
| births → Names[N_TEMP] | PREPEND + FreeName-unlink: `reversed(surviving births)` | 1137/1137 |
| Names → nt_pre | BuildNameConflicts ShellSort, `AllocBefore@0x5905b` | 1137/1137 (per ROUND — the parser concatenates multi-round nb1/nb2 events; `segment_sort_events` splits them.  The historical "30 failures" were ALL this artifact) |
| nt_pre → nt_post | AssignTemps ShellSort, `SortCmp_flag2_2b@0x55503` | 1224/1224 |
| nt_post → [esp+N] | AllocNewLocal walk (`an` records) | 138/138 |

Ground truths (binary-verified, in the watcom10.0a knowledge DB):
`TempId@0x7f8f0` == the `+0x24` "loc24" (monotone creation ordinal; aliases
share it → SortCmp's "+0x24 equal → +0x10 DESC" orders ALIASES, distinct
temps are sort-equal).  Identified birth passes: `BGNewTemp@0x443a8` (tree
burn), `FlowOut@0x443d4` (bool materialisation → the sz4+sz1 anon pairs),
`CondConstStores2Bool@0x5e7ed` (diamond const-stores-differ-by-1 → the U1
byte temps that interleave Names[N_TEMP] and destabilise the size sort),
`BurnCopyToTemp@0x4ada9`, `BGGlobalTemp@0x443ca`.

Consequence for the open Rule 107 residues (set_route_elastic_range,
build_road_from_elastic, trace_back_route_elastic): the "anon-temp
birth-order arm" is no longer a black box — every flip-window temp now
carries (line, pass-caller) attribution in `routine['nb']`.  The next
lever search is: which SOURCE construct feeds the attributed pass
(FlowOut ↔ bool expressions; CondConstStores2Bool ↔ if/else constant
stores differing by 1; BGNewTemp ↔ specific burn helpers), then move THAT
construct.  BGNewTemp births still hide the outermost helper one hop up —
if needed, the next probe is push_caller on BGNewTemp itself.
