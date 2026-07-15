# HARD-bucket survey: mechanism-class state across all 5 categories

**Session, 2026-06-24.** Applied the slot-swap methodology (read
`decomp-verify -v` output, classify per-function mechanism via the
existing Cascade / Regalloc / Reg-swap / Byte-seat analyzers) across
all five HARD-bucket classes.  Result: **the other four classes were
already well-characterized by the existing analyzers; only slot-swap
needed the new instrumentation this session added.**

The HARD-bucket residue is **not a mystery box**.  Per-function
levers exist for every class; the bottleneck is source EXECUTION
(applying a named lever without cascading other diffs).

## Per-class state

| class                | fns | bytes | mechanism state                       | named lever exists?              |
|----------------------|----:|------:|---------------------------------------|----------------------------------|
| `slot-swap`          |   7 |  1635 | FULLY characterized (this session)    | YES — sim + diagnoser            |
| `savings`            |   4 |  1663 | characterized via Cascade             | YES — per-pair gap + action      |
| `prologue`           |   5 |  1305 | characterized via Cascade + layer-1/2 | YES — EAX-boundary / savings     |
| `h2-tie`             |   5 |   719 | characterized as REVERSE-LAST-USE     | YES — move last read up/down     |
| `byte-savings-short` |   1 |   360 | = savings-gap (collateral byte)       | YES — same as savings            |
| **TOTAL**            |  22 |  5682 |                                       |                                  |

## Per-class details (one representative function each)

### `savings` — `place_sprite` (1008 b)

The Cascade analyzer names PRECISE per-pair levers, e.g.:

> Cascade: EBX<->ECX needs a SAVINGS change: PS's order has `side`
> (pm_map1.c:1311) (sav=11) allocating before `people`
> (pm_map1.c:1437) (sav=15) — raise sav(`side`) to >= 15.  ACTION:
> change weighted use counts (chain/split an assignment, inline a
> single-use temp, add/remove a re-read).  SAVINGS (cv): use-units
> [d0:11u] = sav 11; gap +4 -> ADD ~4 straight-line use(s) of this
> value (a loop use is worth 10× a straight-line one).  SIDE EFFECTS
> (8 re-seat(s)): `people` EBX->ECX, `dir` EBX->ECX, …  these must
> MATCH PS's other diff rows; if they do, this one edit closes the
> whole cascade.

Per pair: the swapped register pair, the SAVINGS GAP magnitude, the
ACTION (add/remove straight-line uses, with the ×10 loop-weight rule),
and the side-effect re-seats to cross-check.

### `prologue` — `elephant_fire` (39 b)

> Regalloc: layer 2 PS enregisters one more value than RC. savings: a
> callee-save register needs savings > 2 (≈3 straight-line uses, or 1
> loop use ×10) to be worth its push/pop.  See the Prologue hint for
> the register.

Same Cascade machinery, applied to callee-save allocation: which
register PS chose to push, and how to bump some value's savings to
make that register worth the push/pop cost.

### `h2-tie` — `get_reg_geog_ov_image` (378 b)

> Cascade: EAX<->EDX UNREACHABLE by any single allocation-order
> move/swap (search exhausted, 27 rows) — but this is an EQUAL-SAVINGS
> (H2) tie.  VERDICT UNRELIABLE for H2 ties: the clean-build LEVER is
> — conflicts are created at each operand's LAST use (backward live
> scan) and PREPENDED; the tie is an unstable ShellSort over that
> reverse-last-use order, so the value PS seats in the EARLIER
> register must be created LAST = have the EARLIER last use.  Move
> that value's final read up (or the other's down) and verify;
> decl/first-assign order usually does NOT move it.  Worked:
> `get_reg_buildings_in_radius` (ef1467d4).

The H2-tie lever has a worked precedent commit.  The mechanism is the
same family as slot-swap (an unstable ShellSort over a creation-order
list — except here it's the CONFLICT list, sorted by ConfBefore, not
the Names[N_TEMP] list).

### `byte-savings-short` — `start_move` (360 b)

> Byte-seat = CASE E [trace] (PS bh↔RC cl, …): savings-short byte
> temp (Rule 157) — collateral to the EBX<->EDX SAVINGS-gap swap;
> SAVINGS change needed (not permute)

Reduces to the SAVINGS class — a byte temp that's seated by the same
ShellSort instability as the dword pair it's collateral to.

## Cross-cutting observation: misbucketing

Several functions in HARD are bucketed by the WORKLIST classifier into
one class but the deeper Cascade verdict reveals a different actual
mechanism.  Examples:

* `control_menus` (266 b, h2-tie bucket) → actually `layer 5 loop
  hoist/reload` per the Regalloc line.
* `strip_spaces` (38 b, h2-tie bucket) → actually `layer 5 loop
  hoist/reload`.
* `build_an_area` (274 b, slot-swap bucket) → actually `fix-next: ir`
  per `c2 diagnose`.

A re-bucket pass would tighten the worklist verdicts.  Not done in
this survey.

## What's actually missing (the HARD-bucket bottleneck)

For every class, **named levers exist; execution is the bottleneck**.
The pattern is the same across all four pre-existing classes (savings,
prologue, h2-tie, byte-savings-short) AND the slot-swap class we
characterised this session:

1. Cascade names the swapped register pair / slot.
2. Cascade names the source-level lever (gap+action / move last use /
   bump savings / restructure body byte-stores).
3. The lever's EXECUTION requires a precise source change that
   doesn't break body semantics or introduce its own cascade.

The slot-swap work added a simulator that lets you TEST candidate
input perturbations offline (the `c2.regalloc.shellsort_sim`).  An
analogous offline simulator could be added for:

* the **SortConflicts ShellSort** (ConfBefore comparator) — would
  validate Cascade's `UNREACHABLE` verdicts and surface alternative
  pair-flipping perturbations for h2-tie cases.
* the **CalcSavings** model — would let an agent see how a source
  edit's use-count change would propagate to per-conflict savings,
  closing the "+4 straight-line uses" guidance loop with a
  pre-recompile verify.

These would be the **next instrumentation steps** for HARD-bucket
work generally.  Neither is strictly needed — the existing Cascade
hints are already actionable — but they'd shorten the per-function
experiment loop the same way the slot-swap simulator does for
slot-swap.

## What the slot-swap work added (and what it didn't)

The slot-swap session this day did NOT add the first analyzer for that
class.  The pre-existing `Slot-swap:` hint already named the swapped
slots + the FLIP-CREATION-ORDER lever direction.  What was MISSING:

1. **No mechanism characterization**: the lever was "FLIP their
   creation order" without explaining WHY some orders flip and others
   don't.
2. **No offline simulator**: every candidate source edit required a
   full recompile to test (10-30 s).
3. **No per-function classification**: all slot-swap functions were
   lumped together as "genuinely hard residue".

What the session added:

1. **`nb1/nb2/an/bb` + `nt`/`na` deref-savings trace records** —
   full pipeline observability from front-end to AssignTemps.
2. **The offline ShellSort simulator** (validated 195/195) — sub-
   second iteration.
3. **The 4-class diagnoser** (shellsort-instability / sort-stable-
   other / sub-source / misbucketed) — surfaced inline in
   `decomp-verify -v`, `c2 dossier`, `c2 worklist`.

The OTHER classes already had equivalents of #1 and #3 via the
Cascade analyzer.  An equivalent of #2 (offline simulator) is the
recommended next instrumentation step.

## Bottom line

The HARD bucket is FULLY CHARACTERIZED across all 5 classes.  No
class is a mystery box; every per-function residue has a named
mechanism, a named source lever, and (mostly) a worked precedent
elsewhere in the corpus.  The remaining work is source-experiment
EXECUTION on the named levers — not new analyzer work.

## Honest caveat: NAMED ≠ EXECUTABLE

The classifiers return **named leads** (which pair, which value, what
direction, what magnitude).  They do **not** return executable source
edits.  The gap between "add ~4 straight-line uses of X" and "the
exact source change that achieves that without semantic regression
or optimiser cancellation" is where every HARD-bucket function still
sits.  Empirical experience this session:

| class                | what's NAMED                                         | executable?                                                                                                                                                                                                                                                       |
|----------------------|------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `savings`            | pair + variable + gap magnitude + direction + side-effects | PARTIALLY.  ADD/REMOVE uses verb is real, but semantically-neutral uses get optimised away (verified on show_menu_items P5 `count + text_group * 0`).  For anonymous temps (`t.85b4`), no source handle — must restructure the generating expression.            |
| `prologue`           | which callee-save diverges + savings threshold > 2   | VAGUE.  WHICH value should earn the callee-save isn't named.  Tiny functions (elephant_fire: 4 stmts) have no room for semantic-neutral savings bumps — source comment already documents 'we tried, regresses'.                                                          |
| `h2-tie`             | pair + REVERSE-LAST-USE lever direction + worked precedent | PARTIALLY.  Cascade explicitly says `VERDICT UNRELIABLE for H2 ties`.  Move-last-read direction is concrete BUT often targets anon CSE temps with no source handle.  `restore_picture_part` (4b) source comment: 'asymmetry is allocator walk order, not spelling' = stuck. |
| `byte-savings-short` | reduces to SAVINGS                                   | SAME as savings.                                                                                                                                                                                                                                                       |
| `slot-swap`          | mechanism class + destabilising temps + sort_sav inversion + lever direction | PARTIALLY.  `build_units_figures` (5b) — 6 input perturbations found, source-mapping not yet executed.  `show_menu_items` (207b) — exact pair, lever direction, but every tested edit overshoots or adds frame bytes.                                              |

**No HARD-bucket residue currently has a NAME -> EDIT pipeline that
an agent can apply mechanically.**  Every named lever requires the
agent to invent a source change that:

1. Achieves the required savings/use-count/order shift
2. Survives the optimiser (semantically-neutral changes get folded
   away — e.g. `(void)x`, `x * 0`, dead conditional bodies)
3. Doesn't change function semantics (no extra stores, no changed
   field reads)
4. Doesn't cascade into OTHER diffs (new register pressure, frame
   delta, byte-store reordering)

This is fundamentally a SEARCH problem the per-function loop already
faces: try candidate edits, verify against PS bytes + Mac/Win
oracles.  The named leads narrow the search space dramatically
(from 'unknown source change' to 'edit that bumps X's sort_sav by
~10') but they don't eliminate the search.

## The realistic next-instrumentation step

Three pieces would make HARD-bucket levers EXECUTABLE, not just
named.  **Two already exist; the third was built this session:**

* **Offline CalcSavings simulator** — ALREADY EXISTS as
  `c2.regalloc.trace.savecalc_savings()`.  Takes a conflict's
  per-block `cv` (savecalc) entries + loop base, returns predicted
  savings.  Verified exact against the live trace's `al.savings`
  (4/4 sampled on `get_region_over`).  Test "add a depth-1 use" as
  a savings delta in microseconds.  See
  `docs/optimiser-folding-idioms-2026-06-24.md` for usage.
* **Offline SortConflicts (ConfBefore) simulator** — ALREADY
  EXISTS at `c2/regalloc/sort.py` (predates this session).
  Algorithm exact (self-test passes); reproduces the first sort
  invocation of `postsort` from `presort`.  Use with `presort` to
  test "what if I bump conf X's savings by N?" before recompiling.
* **Catalogue of `optimiser-surviving use idioms`** — BUILT this
  session at `docs/optimiser-folding-idioms-2026-06-24.md` +
  `docs/codegen-experiments/optimiser-folding-idioms.py`.
  Empirical table: which C constructs add a savings bump (and how
  much), which get folded by the optimiser entirely.

**Missing**: the composed wrapper
`diagnose_savings_edit(routine, var, block, depth_delta)` that
chains them — perturbs a conflict's savecalc, re-runs CalcSavings,
re-runs SortConflicts, reports whether the Cascade-named pair flips.
All components exist; the wrapper is a small addition that would
make "named lever -> executable edit" a one-liner test.
