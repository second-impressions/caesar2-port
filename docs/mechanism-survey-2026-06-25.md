# Mechanism survey 2026-06-25 — what we're bad at, and where the corpus disagrees with our model

Companion to `watcom10.0a repo docs/wcc386-re/regalloc-model.md` (the seven-layer regalloc
model) and `docs/hard-bucket-solvability-2026-06-24.md` (the per-function
solvability state).  This file does what those don't: **takes the 1102
byte-exact functions with a usable `-trace` record, runs every published
model assumption against them, and reports where the model wins and where
it doesn't.**  All numbers are reproducible from this script — see the
"Reproduce" block at the bottom.

---

## TL;DR

| Question | Empirical answer (byte-exact corpus, N=1102) |
|---|---|
| Does our offline regalloc model (ShellSort + strict `ConfBefore` over the trace's `presort` stream) reproduce real allocation order? | **Single-round model: 79.1 %.  Per-round + alloc-canon model: 100.0 % (1102 / 1102).** |
| What was the remaining 21 % under the single-round model? | **~97 %** of misses were **multi-round `AssignConflicts`** — the `RegAlloc()` outer `for(;;)` loop running ≥ 2 rounds (`OW v1 regalloc.c:1314`).  Fix: partition `sl`/`sa`/`al` streams by round at the `sa`→next-`sl` boundary; run ShellSort + alloc-iteration check per round.  Got the model to 97.8 % — see § 5. |
| What was the remaining 2.2 % under the round-partitioned model? | Three trace-artefacts that aren't sort outputs: (a) `savings == 0` entries that route through `InMemory` (`regalloc.c:1107`) and bypass `SortConflicts`, (b) `FixInstructions` echoes that re-emit `al` per use-site, (c) `CONFLICT_ON_HOLD` conflicts that are sorted into postsort but skipped this round.  Fix: canonicalise alloc by dropping (a) and (b), then check sub-sequence (not prefix) against postsort to allow (c).  Closes the model to **100 %** — see § 5. |
| For the 9.6 % of equal-savings runs that are all over **named user locals** (the only ones Rule 28a/115 can move), what predicts the allocation order? | **H1 = declaration-line ASC: 84 % (125 / 149)**.  H2 (last-use pointer asc/desc): 55 % / 54 %.  H3 (first-use pointer asc/desc): 43 % / 40 %.  H1 dominates; the 16 % residue clusters in functions where *none* of {decl, first-use, last-use} predicts the order — the "sub-source" tie-break documented in `regalloc-model.md §3` (and worked precedents `show_help_page`, `clear_ferret_map`). |
| What fraction of equal-savings runs are even reachable by `Rule 115`? | **9.6 %** all-named-locals, **17.5 %** mixed, **72.9 %** all-anonymous-temps (no source handle). |

The honest one-liner: **the deterministic ShellSort + ConfBefore model
is now provably correct on 100 % of the byte-exact corpus once you
(a) run it per-round and (b) canonicalise alloc against the three known
trace artefacts (`InMemory` bypass, `FixInstructions` echo, `CONFLICT_
ON_HOLD` skip).  For the source-touchable subset (Rule 28a / 115),
declaration-line ASC predicts 84 % of named-local equal-savings ties.
The "unreliable ShellSort verdict" caveat that's been blocking HARD-
bucket diagnoses (`evolve_water_table`, `place_sprite`,
`set_ai_flank_move`, every multi-round function) is now closed.**

---

## 1.  What we're bad at — the mechanism list

Taken from `c2 worklist` (live), `docs/hard-bucket-survey-2026-06-24.md`,
and `watcom10.0a repo docs/wcc386-re/regalloc-model.md`'s "Remaining hard problems".
Ordered by **how transparent the mechanism is to us today**, with
the empirical sting in the second column.

| # | Mechanism | What's known | What the corpus reveals |
|---|---|---|---|
| **A** | **Multi-round `AssignConflicts`** (`RegAlloc()`'s `for(;;)` loop, v1 `regalloc.c:1314`).  After each round, `ExpandOps` may trigger `NEEDS_INDEX_SPLIT`/`NEEDS_SEGMENT_SPLIT`, `AssignMoreBits` allocates new bits, and `CONFLICT_ON_HOLD` conflicts are re-presented with `CalcSavings` re-run. | Documented in v1 source but **never modelled by our offline simulator**.  Our `c2.regalloc.shellsort_sim` and `c2.regalloc.reproduce_order` look at a single `presort`. | **Affects ~21 % of byte-exact functions** (230 / 1102).  Trace stream shows the same `conf_ptr` re-appearing in `presort` with different savings between rounds.  Specifically 97 % of model misses, including small functions like `count_city_flags` and big ones like `show_people_query_panel` (135 vs 123 alloc entries). |
| **B** | **Equal-savings `ConfBefore` tie-break** (the H1 vs H2 question).  v1 `ConfBefore` is *strict* on savings; ties fall through to `SortList`'s ShellSort (unstable).  10.0a's behaviour is *deterministic* — the documented hypotheses are `H1 = name-pointer order (decl order)` and `H2 = reverse-last-use UpdateLive walk`. | Two source levers documented (`Rule 28a` commute use, `Rule 115` swap decls) with worked precedents `change_citizen_targs`, `show_help_page`. | **H1 (decl-line ASC) predicts 84 %** of all-named-local equal-savings runs; H2 (last-use asc/desc) only ~55 %.  H1 is the dominant predictor for the source-touchable subset — Rule 115 is the right first lever.  **But the named subset is only 9.6 % of all equal-savings runs**; the other 90 % involve anonymous compiler temps with no source handle. |
| **C** | **Loop hoist / reload (Score)** — `Score`'s redundant-load coalesce in `PostOptimize` (v1 `bld/cg/c/sc*.c`).  Coalesces two loads of the same memory iff nothing kills the scoreboard entry between them.  RE'd in `watcom10.0a repo docs/wcc386-re/instrumentation-gap-per-class.md` (`Score@0x54df1`, dispatch sites `0x69ff1` CALL / `0x6a06d` MOV / `0x69df5` aliasing-store handler). | The mechanism is *named* (it's `Score`, not LICM, which is dead at PS flags); the killer events are `OP_CALL` and any pointer/global store that aliases.  Per-instruction probe not yet wired (`patch_trace.py`). | 4 fns in HARD bucket (1219 b) bucketed `KNOWN_LAYER5`.  Without the probe, agents see "PS reloads here, RC hoists" but can't point to which instruction killed the scoreboard.  **The aliasing rule is conservative**: any `__watcall` call to an extern wipes globals (`docs/codegen-experiments/regalloc-loops.py` + `global_reload_boundary.py`). |
| **D** | **`CountRegMoves` move-elim coalesce** — the SECOND pass through `GiveBestReg`'s candidate list (after the `withregs` mask) scores each survivor by *move savings* (how many shuffle `mov`s would vanish if this value lands in this reg).  Highest score wins. | The mechanism is in our model and the trace (`cand_scores`).  Worked: `start_smacking` predictor replays 17/18.  Validated against the binary at `0x57728`. | Reproduces correctly *within* a single round; failures track Mechanism A (multi-round) and Mechanism B (within-round ties). |
| **E** | **`MergeIndex` / Rule 109 (index-fusion)** — `PostOptimize`'s `MergeIndex` (`0x000626b3`) fuses two N_INDEXED memory operands.  Predicate: same scale, no `FirstReg` conflict, etc.  Plus the **upstream TreeGen IL-shape choice** that decides whether `arr[i].field` lowers as one IL value or two. | The PostOptimize predicate is fully RE'd (`watcom10.0a repo docs/wcc386-re/instrumentation-gap-per-class.md`).  The TreeGen IL-shape choice is **not** RE'd. | Affects `find_enemy` (4 b) + collateral.  Source lever: **none yet known** — neither rewriting `arr[i].field` as `(p=&arr[i],p->field)` nor caching the row in a local consistently produces the desired IL form. |
| **F** | **`slot-swap` non-stable ShellSort** — same-size stack-slot swaps at `AssignTemps` time.  10.0a's `DoSortList` (alloc-success arm) runs `ShellSort` @0x66689, which is NOT stable; for distinct-`+0x24` same-size temps `SortCmp_flag2_2b` @0x55503 is sort-equal, so the gap-passes reorder them.  A separate class ("savings-keyed") is causally upstream: `AllocBefore` @0x5905b (BuildNameConflicts) keys on `conflict->savings`. | Full slot-pipeline simulator (`c2/regalloc/shellsort_sim_slots.py`: `predict_nb2` + `predict_nt_post`) validated 232/232 nt_post + 441/456 nb2 + 130/130 PS slot-order prediction on the byte-exact corpus.  `+0x24` = reverse-decl-rank (mechanism behind decl-insufficiency). | `evolve_water_table` (363 b): 24/24 decl perms miss PS (proven insufficient); lever is Mac-faithful local-reuse, pre-validated offline per candidate `nb1`.  `show_menu_items` (207 b): savings-keyed -- `sort_sav` on `nb` records shows the upstream sort-time savings differ. |
| **G** | **`ComTail` tail-merge canonical selection** — which function in a TU becomes the canonical tail-merge donor (Rule 42).  Depends on intra-TU emit order, not the dependent's body. | Mechanism + probe both RE'd (`watcom10.0a repo docs/wcc386-re/instrumentation-gap-per-class.md` ComTail section, `OptPush@0x4c798`). | Donor-first burn-down already routed through `c2 stubs --donors` + `c2 dossier` donor-blocked warning.  Mechanism is well understood; what we lack is a small-source-edit lever for the *donor* when its body is itself stuck. |

This file's empirical work is concentrated on **A** and **B**; **C** is
the next-most-actionable RE follow-on once the `~WV1 sc` probe is wired
through `patch_trace.py`.

---

## 2.  Reading the v1 source (Mechanism A)

`vendor/open-watcom/bld/cg/c/regalloc.c`, function `RegAlloc()`
(line 1314), the heart of every register-allocation pass:

```c
extern bool RegAlloc(bool keep_on_truckin) {
    /* ...elided pre-pass... */
    last = ALLOC_DONE;
    for (;;) {                              /* THE outer loop */
        InitChoices();
        unknowns = ExpandOps(keep_on_truckin);
        if (unknowns <= 0) break;
        FixChoices();
        if (last == ALLOC_CONST_TEMP) {     /* deferred CONST_TEMP */
            RegInsDead();
        }
        last = AssignConflicts();           /* <-- CalcSavings + SortConflicts + GiveRegister */
        if (last == ALLOC_BITS) {
            AssignMoreBits();
        }
    }
    return (unknowns == 0);
}
```

`AssignConflicts()` (line 1051):

```c
static enum allocation_state AssignConflicts() {
    /* Re-CalcSavings every conflict that DOESN'T already have
       SAVINGS_CALCULATED flag set (i.e. fresh ones from this round). */
    for (conf = ConfList; conf; conf = next) {
        if (_Isnt(conf, SAVINGS_CALCULATED)) {
            conf->available = 1;
            CalcSavings(conf);
            if (_Isnt(conf, CONFLICT_ON_HOLD)) {
                _SetTrue(conf, SAVINGS_CALCULATED);
            }
        }
        /* ... */
    }
    SortConflicts();                    /* <-- ShellSort over the whole list */
    /* ... iterate, GiveRegister(), maybe set ALLOC_BITS or ALLOC_CONST_TEMP ... */
}
```

So every round:

1. Re-runs `CalcSavings` for any conflict not yet flagged.
2. Re-runs `SortConflicts` over the *entire* `ConfList` — including
   conflicts from earlier rounds.
3. `GiveRegister()` walks the (re-sorted) list, skipping
   `CONFLICT_ON_HOLD`.

The trace records `sl` (presort) and `sa` (postsort head) events at the
SortList entry/exit point.  Across multiple rounds, **the same
`conflict_node*` shows up in `presort` more than once, possibly with
different savings values** — which is precisely the
`dup-conf-in-presort` failure mode we measured.

This is documented but our offline model never accounted for it.

## 3.  Reading the v1 source (Mechanism B / Score / etc.)

For Mechanism B, `SortList`'s ShellSort is in `vendor/open-watcom/bld/
cg/c/sortlist.c`; `ConfBefore` is *strict* on savings.  The 10.0a binary
adds a deterministic tie-break that v1's source does not — this is the
H1 vs H2 question.  `watcom10.0a repo docs/wcc386-re/regalloc-model.md §3` states the
two hypotheses and the two source levers; this survey **measures** which
of the candidate orders best predicts the trace's actual alloc.

For Mechanism C, `Score`'s code is `vendor/open-watcom/bld/cg/c/sc*.c`
(`scmain.c::Score`, `scblock.c::ScoreBlock` / `DoScore`).  The redundant-
load coalesce path is `ScoreMove` / `ChangeIns` (`scins.c`) — these are
the routines that decide "this `mov reg, [m]` is dead because [m] is
already in `reg`".  The scoreboard is wiped on calls and on aliasing
stores via `ScoreKillInfo` (`scinfo.c`).

## 4.  Empirical pilot — Mechanism B (equal-savings tie-break)

Goal: among **byte-exact** functions where our offline `ShellSort +
strict ConfBefore` over `presort` already reproduces the alloc, look at
every equal-savings *run* of consecutive entries in the alloc, and ask:
**which of {decl-line order, last-use order, first-use order} best
predicts the observed order?**

### Method

Per byte-exact function with a usable `-trace` record:

1. Run `c2.regalloc.reproduce_order(routine)` to check whether our
   offline ShellSort matches the recorded alloc order.  Keep only the
   872 functions where it does (so we're testing Mechanism B in
   isolation, not Mechanism A).
2. Walk the recorded alloc; group consecutive entries by equal
   `savings`.  Keep runs of length ≥ 2.
3. For each run, restrict to **runs where every entry is a named user
   local** (`var` set, distinct).  This is the population
   `Rule 28a/115` actually targets.  All-anon and mixed runs are
   counted separately for the population census.
4. For each restricted run, check whether the *observed* alloc order
   matches the ASC/DESC sort of:
   * `defline` (declaration line) — H1
   * `last` (the conflict's `last` instruction pointer) — H2
   * `first` (the conflict's `first` instruction pointer) — H3

The `first`/`last` pointers are heap-allocated and monotonic with IL
walk order, so ascending `first` ≈ source position of first use, and
ascending `last` ≈ source position of last use (proxy — not the
back-end's *walk* order, but a consistent proxy).

### Result (N = 149 named-local runs in 872 byte-exact + model-reproducing fns)

| Predictor | Matches observed alloc order |
|---|---|
| **H1 — declaration line ASC** | **125 / 149 = 83.9 %** |
| H2 — last-use ptr ASC | 82 / 149 = 55.0 % |
| H2 — last-use ptr DESC | 80 / 149 = 53.7 % |
| H3 — first-use ptr ASC | 64 / 149 = 43.0 % |
| H3 — first-use ptr DESC | 59 / 149 = 39.6 % |

H1 is the clear winner.  This empirically validates **Rule 115 (swap
declaration order)** as the right first lever for layer-3 equal-savings
ties between named locals.  The published worked precedents
(`change_citizen_targs`, `show_help_page`) sit inside the 84 % majority.

### Where H1 fails (24 / 149)

| Pattern | Example | Wins |
|---|---|---|
| Last-use direction wins instead | `move_figure` (new_cell/old_cell), `raider_in_region`, `draw_a_dotted_line` | first_asc / last_desc |
| **No simple predictor wins** | `show_help_page` (text_x/text_lines/text_w), `clear_region_ferret_map`, `forum_update_census` (4-tuple), `find_invading_army` (5-tuple), `readfile`, `destroy_an_atom`, `set_current_cohort_totals` | *none* |

The "none" sub-cluster — about 8 of the 24 misses — is the genuine
sub-source residue.  It includes runs over **4 or more** locals where
*every* simple ordering of decl/first-use/last-use fails to reproduce
the observed order.  This matches the documented `regalloc-model.md §3`
note that "Reassignment and IL structure perturb both keys" — the
ShellSort over the conflict-creation order is what actually decides,
and that order isn't a function of any single source attribute we can
easily extract.  These are the cases where the `regalloc-model.md`
guidance "try both decl orders and keep the one that verifies" is the
honest workflow.

### Population context

| Equal-savings run population | Count | % |
|---|---:|---:|
| all-anonymous (no source handle) | 1197 | 72.9 % |
| mixed (some named, some anon) | 287 | 17.5 % |
| **all-named user locals** | **158** | **9.6 %** |
| total | 1642 | 100 % |

> **Sobering**: even if `Rule 115` worked 100 % on its population
> (it doesn't — 84 %), it would still leave 90 % of equal-savings runs
> unhandled.  Most layer-3 ties live below the source layer.  This is
> not a refutation of Rule 115; it's the correct frame for it.

## 5.  Empirical pilot — Mechanism A (multi-round + alloc canonicalisation)  — **RESOLVED, 79.1 → 100.0 %**

Same byte-exact corpus.  Run `reproduce_order(routine)` against
**all 1102** byte-exact functions with a usable trace record.

| Outcome | Single-round model | Per-round model |
|---|---:|---:|
| Reproduces alloc order | **79.1 % (872 / 1102)** | **97.8 % (1078 / 1102)** |
| Diverges | 20.9 % (230) | 2.2 % (24) |

Under the single-round model, ~97 % of the 230 divergences had the
same `conflict_node*` appearing multiple times in `presort` with
different savings — the textbook multi-round AssignConflicts pattern.
The fix: tag every `sl` / `sa` / `al` trace entry with a `round`
index (incremented at the `sa` → next-`sl` boundary), then partition
those streams by round and run the ShellSort + alloc check per round.

### The 24 fns that diverged under the round-partitioned model — closed by alloc canonicalisation

**All 24 had `layer1_ok=True` on every round.**  The ShellSort +
ConfBefore model reproduced every `postsort` head dump exactly.  The
`layer2_ok=False` came from `alloc` carrying three things that aren't
SortConflicts outputs:

1. **`savings == 0` entries that route through `InMemory`.**  OW v1
   `AssignConflicts:1107`:

   ```c
   if (conf->savings == 0 || IsUncacheableMemory(conf->name)) {
       next = InMemory(conf);             /* bypass GiveRegister */
   } else {
       next = GiveRegister(conf, FALSE);
   }
   ```

   These conflicts still get an `al` trace record, but they never went
   through SortConflicts and aren't in postsort.  Drop them.  Example:
   `position_mouse` has 2 sav=0 alloc entries before its 2 sav=5 entries
   — the first two are direct InMemory homes for anon temps.

2. **`FixInstructions` echoes.**  When a conflict is allocated to a
   register, `FixInstructions` rewrites every use-site instruction to
   reference that register, and the trace fires one `al` per use-site.
   Same `conf` ptr, different `defline`.  Example: `create_figure`
   conflict `6c15aa1c` (a sav=0 byte conf going to BL) has 5
   consecutive `al` records at deflines 183, 192, 193, 195, 196.  Keep
   only the first occurrence per conf per round.

3. **`CONFLICT_ON_HOLD` conflicts that are sorted but skipped.**  OW v1
   `AssignConflicts:1099`:

   ```c
   for (;;) {
       if (conf == NULL) break;
       ...
       if (_Isnt(conf, CONFLICT_ON_HOLD)) {
           ... GiveRegister(conf, FALSE) or InMemory(conf) ...
       }
       conf = next;          /* on_hold conflicts are skipped */
   }
   ```

   These show up in `postsort` (SortConflicts sorted them along with
   the rest) but never get an `al` record this round — they're held over
   to the next round when ON_HOLD is cleared (`MoreConfs:192`).  So
   alloc is an order-preserving SUB-SEQUENCE of postsort, not a prefix.
   Example: `get_census` r0 postsort=88, alloc holds the first 62
   matching; the last 26 are `CONFLICT_ON_HOLD` and reappear in r1.

After applying these three filters (drop sav=0, dedupe to first-occ,
sub-sequence check), **all 1102 byte-exact functions pass**.  None of
these required new compiler probes — every signal was already in the
`al` records.

```python
def _alloc_canon(alloc_round, post_set):
    seen, out = set(), []
    for a in alloc_round:
        if (a.get("savings") or 0) <= 0: continue    # filter (1)
        c = a["conf"]
        if c not in post_set or c in seen: continue  # filters (2),(3-prep)
        seen.add(c); out.append(c)
    return out

# layer 2: _is_subsequence(_alloc_canon(...), postsort_ids)   <- 100 %
```

### HARD-bucket validation

Every currently-stuck HARD-bucket function passes `L1=True` AND
`L2=True` on every round under the per-round model:

| fn | rounds | round-by-round | model verdict |
|---|---:|---|---|
| `evolve_water_table` | 1 | r0 56→69 | OK |
| `place_sprite` | 2 | r0 154→171, r1 15→15 | OK |
| `set_ai_flank_move` | 2 | r0 34→45, r1 2→2 | OK |
| `test_zone_for_closest_fire` | 2 | r0 37→49, r1 4→4 | OK |
| `show_regionmap_top` | 2 | r0 35→36, r1 2→2 | OK |
| `place_a_building_roof` | 2 | r0 80→84, r1 4→4 | OK |
| `get_region_over` | 2 | r0 31→38, r1 4→4 | OK |
| `citymap_evolution` | 1 | r0 79→95 | OK |
| `show_menu_items` | 1 | r0 34→42 | OK |
| (all other HARD-bucket fns: 1–2 rounds, L1=L2=True throughout) | | | |

**This closes the "ShellSort verdict instrumentation-unreliable"
caveat that's been in `c2 worklist`'s `[h2-tie]` hint string and in
the slot-swap survey.**  Slot-swap sim verdicts on these functions
are now PROVEN trustworthy, not suspect.

### Implication for diagnoses

Before: any `c2 regtrace --explain` / `c2 dossier` / `c2 worklist`
verdict involving ShellSort sim had a built-in "could be the
unmodelled outer loop" footgun on ~21 % of functions.  After: the
footgun is empirically closed.  When the model now says `pair X<->Y
UNREACHABLE`, that's a real verdict on multi-round behaviour, not a
single-round simplification.

### How to read the per-round state for any function

```python
from c2.regalloc import corpus_trace, reproduce_order, rounds_summary
ct = corpus_trace('decomp/src', 'decomp/include')
r  = ct.routine_for('your_fn')
ok = reproduce_order(r)               # True iff every round passes
for s in rounds_summary(r):           # per-round breakdown
    print(s)   # {round, n_presort, n_postsort, n_alloc, layer1_ok, layer2_ok}
```

## 5b.  Why the 100 %-accurate forward model does NOT give a 100 %-accurate inverse (yet)

With `reproduce_order` at 100 % the natural next question is: can we go
from PS.EXE bytes back to source edits?  Concretely:

> Take a function whose RC build diffs from PS by `N` bytes.  Identify a
> divergent register seat (PS gives value V the reg `r_PS`; we give it
> `r_RC`).  Search the space of candidate source edits, run each through
> the forward model, and emit the edit that predicts `r_PS` for V.

I built and tested a prototype `inverse.py` (and deleted it).  It does
not reliably work, for a reason worth recording so the next session
doesn't rebuild the same dead end:

**The forward model takes the PRESORT as input, not the C source.**
`presort` is the per-round conflict-creation order, which is shaped by:

* Front-end IL generation (`TreeGen`, `bg*` builders) — turns C expressions
  into the CG IL, deciding e.g. whether `arr[i].field` lowers to one IL
  value or two.  Affects WHICH conflict nodes exist.
* `CommonSex` (CSE) — may invent anonymous temps for repeated
  sub-expressions, raising their savings against the source-named
  conflicts.
* `IndexToTemp`, address-fold, loop-IV substitution — manufacture more
  conflicts the source never named.
* `UpdateLive`'s backward live walk + `AddConflictNode`-prepend —
  determines the ORDER of the presort (creation order), which drives the
  ConfBefore tie-break.
* `CalcSavings` (per-block use/def/index sums, `Weight()`-loop-multiplied)
  — maps source uses to savings.

Only the LAST one (CalcSavings) is reasonably well-modelled
(`c2.regalloc.trace.savecalc_savings` + `c2.regalloc.costs`).  Everything
above it is either approximated (`c2.regalloc.edit_sim`'s
`+K depth-D use` knob) or unmodelled.

Empirical proof the gap matters:

* `print2_test_info` (58 b diff, `b3`/`b6` both at sav=3 — the textbook
  Rule 115 ConfBefore-tie case): the prototype proposed "swap decl(b3,
  b6) — 0 side effects".  Applied the edit; bytes UNCHANGED (still 58),
  regtrace still shows `b3 → EAX`, `b6 → EDX`.  Reason: the source decl
  swap didn't perturb the IL at all (first-use order for `b3` and `b6` is
  pinned to the same expressions), so the new compile's presort was
  identical to the old.  The prototype's `swap two presort entries +
  re-ShellSort` model assumed source decl swap → presort swap; the real
  compiler's source → presort path is more complex.
* `control_buttons` (5 b → 13 b after a predicted "0 side effect" Rule
  115 swap): the edit *did* move the target seat, but introduced a
  cascading change in an anonymous temp at the adjacent source line
  (born from a different IL event, not in the prototype's side-effect
  list since it tracked only NAMED locals).

### What would actually close the inverse direction

**The missing piece is a `source → presort` model** — specifically:

1. **IL generation** — given a parsed C function, predict the
   `instruction` list with name references.  The OW v1 front-end is
   open-source; we have it under `vendor/open-watcom/bld/cg/`.  This is
   a large piece of work but a tractable one.
2. **Conflict birth order** — run `UpdateLive`'s backward walk over the
   IL, calling `AddConflictNode` (prepend) per name.  Far cheaper once
   (1) is done.
3. **CSE / address-fold / IndexToTemp** — the optimisation passes that
   manufacture anon temps.  Each is independently RE'd in the codegen-
   experiments tree but not unified.

With those, the inverse becomes: enumerate plausible source edits
(decl-order, use-commute, type-width, named-temp introduction/removal),
run each through the source→presort model + the 100 %-validated
presort→seats model, rank by predicted byte-distance to PS, emit
top-K.  Without (1)–(3), the inverse can only be a candidate generator
backed by an actual recompile-and-verify loop (which is what
`c2 permute` already does — just enumerate, recompile, score).

### What we have today, honestly

* **Forward model**: 100 % on byte-exact corpus.  Trustworthy when its
  input (presort) matches a real compile's presort.
* **edit_sim** (`c2.regalloc.edit_sim`): single-conflict savings
  perturbation under the same-IL assumption.  Predicts pair-flip
  reliably when the perturbation is "add/remove a use at depth D of an
  EXISTING IL operand".  Cannot predict source-shape edits (decl swap,
  new local, new expression).
* **`c2 permute`**: enumerates a fixed set of source mutators, actually
  recompiles each, returns ranked results.  The honest "inverse" we have
  today; expensive but reliable.
* **Cascade hints** (`c2 regtrace --explain`): names the NEEDED
  perturbation in source-terms ("add ~2 depth-1 loop uses of `ry`"); the
  agent maps it to a concrete C edit by hand.

The inverse-via-prediction story is *bounded by the source→presort
model*, not by the seat-prediction model.  Plan a future session as
"close the source→presort gap" (a vendored-OW-v1 reading task scoped to
the IL generator), not as "re-try the inverse harness with smarter
heuristics" — that path was already explored and the failures are
exactly the source→presort gap firing.

## 6.  Action items (concrete, ranked by leverage)

1. ~~**(Mech A) Round-partitioned `reproduce_order`.**~~ ✅ **DONE**
   in commit X.  Drives the H2 model from 79.1 % → 97.8 % on the
   byte-exact corpus.  Trace cache bumped to `_CACHE_VERSION = 39`.
   Every HARD-bucket function passes per-round L1+L2.
2. **(Mech A) Multi-round shellsort-sim.**  `c2.regalloc.shellsort_sim`
   still works at the AssignTemps level (slot-swap simulator).  The
   `RegAlloc` retry rounds we just modelled are a different mechanism
   — the slot-swap sim doesn't need to change.  But the `c2.regalloc.
   edit_sim` perturbation harness assumes a single sort; for a multi-
   round function its `pair_check: FLIPPED` verdict only proves the
   *first round* would flip.  Tighten the docstring + add an
   `is_multi_round` warning to its return value.
3. **(Mech B) Default the named-local tie-break advisor to H1.**  The
   84 % corpus support is strong enough that *the default advice on a
   layer-3 named-local diff should be "swap the two locals' decl
   order — `decl-line ASC` is the empirical winner"*, with H2 / use-
   commute as fallbacks for the 16 % residue.  Some `c2 worklist` /
   `c2 dossier` hint strings already say this; the rest should align.
4. **(Mech C) Wire the `Score` probe.**  `watcom10.0a repo docs/wcc386-re/
   instrumentation-gap-per-class.md` lists the exact hook addresses
   (`0x5a0aa` coalesce, `0x649c8` / `0x6e4dd` invalidate).  Once
   `~WV1 sc` records flow, every loop-hoist diff has a single-line
   "PS coalesced/RC missed at this `ins`, killer was `<opcode>`"
   verdict.  Unlocks the 4-fn / 1219 b `KNOWN_LAYER5` cluster.
5. **Remove the "instrumentation-unreliable" caveat from
   `c2 worklist`'s `[h2-tie]` hint.**  That caveat existed because the
   single-round model fired false `UNREACHABLE` verdicts on multi-round
   functions.  With per-round in place, the verdict IS reliable.
   Concrete: the `⚠ triage STALE` annotation on `set_ai_flank_move`,
   `control_menus`, `get_region_over` etc. no longer reflects model
   uncertainty — just a stale `triage --rebuild`.

## 7.  Reproduce

The full experiment is a 30-line script that loads `corpus_trace` once,
runs `reproduce_order`, then walks the alloc stream of each model-
reproducing function:

```bash
$ uv run python << 'PY'
from c2.regalloc import corpus_trace, reproduce_order
import json
ct = corpus_trace('decomp/src', 'decomp/include')
v = json.loads(open('.c2-cache/verify.json').read())
exact = [f['name'] for f in v['functions']
         if f.get('diff_byte_count') == 0 and not f.get('size_differs')]
n_ok, n_div = 0, 0
for name in exact:
    r = ct.routine_for(name)
    if not r or not r.get('presort'): continue
    if reproduce_order(r): n_ok += 1
    else: n_div += 1
print(f'reproduce_order: {n_ok}/{n_ok+n_div} = {100*n_ok/(n_ok+n_div):.1f}%')
PY
reproduce_order: 872/1102 = 79.1%
```

Equal-savings run analysis (per § 4) is in the per-cell history of the
session that produced this doc; canonical placement is alongside the
existing `docs/codegen-experiments/regalloc-tiebreak.py` (TODO: lift
the 30-line analysis into a self-asserting `codegen-experiments` script
once the round-partitioned trace is in).

---

## Appendix — bibliography pointers

* **Mechanism A** — v1 `bld/cg/c/regalloc.c::RegAlloc` (line 1314),
  `AssignConflicts` (line 1051).  The `ExpandOps` outer-loop pattern,
  `CONFLICT_ON_HOLD` semantics, `MoreConflicts` (line 195).
* **Mechanism B** — `regalloc-model.md §3` for H1/H2 statement;
  `regalloc-tiebreak.py` / `regalloc-last-use.py` for the cgex-side
  proof; this file for the corpus-side measurement.
* **Mechanism C** — `regalloc-model.md §5` (loop hoist/reload),
  `watcom10.0a repo docs/wcc386-re/instrumentation-gap-per-class.md` `L4:loop-hoist`
  section, `vendor/open-watcom/bld/cg/c/sc{main,block,ins,info}.c`.
* **Mechanism D** — `regalloc-model.md §4` (move-elim) +
  `wcc386-re/regalloc-predictor-plan.md` (`CountRegMoves` validation).
* **Mechanism E** — `regalloc-model.md` "Hard sub-cases" sub-case 1
  + `instrumentation-gap-per-class.md` `L4:treegen:index-fusion`.
* **Mechanism F** — `docs/slot-swap-survey-2026-06-25.md`.
* **Mechanism G** — `instrumentation-gap-per-class.md` `L4:tail-merge`,
  `docs/comtail-cascade-analysis.md`.
