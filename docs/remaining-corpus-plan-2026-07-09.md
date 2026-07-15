# Plan for the remaining 27-function corpus (2026-07-09)

*Fresh survey + own web research, layered on top of
`docs/matching-decomp-prior-art.md` (2026-07-08 survey),
`docs/root-cause-survey-2026-07-02.md` (three-witness protocol) and the
TODO.md 2026-07-03 plan (which worked: 87 → 27 diffing functions).*

---

## 0. State of the corpus (measured this session)

27 diffing functions.  `c2 shape-census` splits them cleanly:

| class | n | functions |
|---|---|---|
| **SHAPE** (real source-shape islands) | 15 | ★1–2-island pure-ops: `cap_land_value`, `evolve_a_cm_row`, `start_samples`, `top_it`, `setup_enemy_units`, `show_move_highlight`, `trace_back_route_elastic` · mid: `mid3_line_no_sides_base`(3), `stretch_to_3x3_house`(3), `clear_an_area`(5), `mid3_line_with_sides_base`(5), `show_battlemap_base`(6), `action`(8), `set_route_elastic_range`(12) · monster: **`evolve_region` (117 islands: ops 57 · slot 33 · zext 22 · width 5 · incr 3)** |
| **SEATING/CTX** (1 island, regalloc realisation) | 4 | `build_road_from_elastic`, `show_left_overlay`, `show_right_overlay`, `take_census` |
| **PURE-SEATING** (isl 0, ✓IR, register-identity tie) | 8 | `build_city_item`, `check_goods_in_region_warehouses`, `evolve_industrial_activity`, `figure_go_to_target`, `fill_warehouses_with`, `place2_a_building_top`, `place_sprite`, `show_citymap_top` |

Worklist: 25 workable · 1 hard · 1 diagnose · **0 blocked · 0 park**.
Triage (reg-swap reachability) cache is stale.

**Infrastructure hole found:** the **evolver.c Windows TU does not
compile** (`error C2371: 'affected_by_cover1' : redefinition; different
basic types`), so the W2 witness (win-census/win-verify/goto-topology)
is DARK for **6 of the 27**: `evolve_region`, `evolve_a_cm_row`,
`cap_land_value`, `check_goods_in_region_warehouses`,
`evolve_industrial_activity`, `stretch_to_3x3_house`.  This is the same
single-prototype blocker class the 2026-07-02 survey fixed once before
(`check_goods_in_region_warehouses` int→void unlocked 14 functions).
Two other TUs also fail the win build (3 total, per `c2 win-verify`).

---

## 1. What my own research added (beyond the 07-08 prior-art doc)

### 1a. The complete decomp-permuter mutation-pass list → a *concrete* forge gap analysis

The prior-art doc recommended "gap-analyse forge vs decomp-permuter"
(rec #3) but never enumerated the passes.  I pulled
`src/randomizer.py` (34 `RANDOMIZATION_PASSES`).  Split against
`c2 forge levers`:

**Already covered by forge:** `perm_reorder_stmts/decls`
(`stmt_reorder_deep`/`decl_*`), `perm_commutative` (`commute_all`),
`perm_compound_assignment` (`compound_assign_*`), `perm_sameline`
(`line_join`/`line_split`), type randomization
(`type_sweep`/`param_type_sweep`/`cast_sweep`), and *narrower* versions
of `perm_temp_for_expr` (`cache_field`/`cache_literal`: repeated reads
and literals only) and `perm_expand_expr` (`de_invent_all`:
single-assignment locals only).

**Missing and PS-FAITHFUL** (source forms a 1995 dev plausibly wrote —
candidates to PORT into the forge battery):

1. **struct-ref/array form toggle** (`perm_struct_ref`):
   `(a + b)->c` ↔ `a[b].c` ↔ `(*(a + b)).c` (+ paren re-association of
   the subscript).  Companion to style-guide §1 (inline index vs cached
   pointer); forge has NO pointer-vs-index form lever today.
2. **Faithful inequality-boundary rewrite** (`perm_inequalities`):
   `a > K` ↔ `a >= K+1` (op AND literal move together —
   *semantics-preserving*, unlike the existing opt-in `boundary` lever
   which changes semantics).  The SotN wiki independently documents
   that this changes the *register seat*, not just the compare bytes.
3. **Chain-assignment merge/split** (`perm_chain_assignment` /
   `perm_long_chain_assignment`): `x = 0; y = 0;` ↔ `x = y = 0;`.
   AGENTS.md already notes chained assignments are Watcom-visible; no
   lever exists.
4. **`if (x)` ↔ `if (x != 0)` toggle** (`perm_condition`) — forge only
   has `bool_return` for returns.
5. **Constant sign-absorb** (`perm_add_sub`): `a - K` ↔ `a + (-K)`.
6. **Generalized temp-for-expr** (`perm_temp_for_expr`): name ANY
   repeated subexpression, with the assignment placed at any insertion
   point — including a *different basic block* — and optional **reuse
   of an existing dead variable** instead of a fresh decl.  The OoT
   guide singles out "move a temp's assignment across a block boundary"
   and "reuse a variable" as the two levers that do what a fresh temp
   cannot.  Forge's cache_* levers can't move the assignment or reuse.
7. **Partial expand-expr** (`perm_expand_expr`): inline a local for a
   *subrange* of its uses while keeping the variable for the rest
   (de_invent_all is all-or-nothing).

**Missing and NOT PS-faithful — build as a separate forge PROBE MODE,
never land in decomp/src:** `perm_add_mask` (`& 0xff` chains),
`perm_xor_zero`, `perm_mult_zero`, `perm_dummy_comma_expr` (`(0, x)`),
`perm_add_self_assignment` (`x = x;` / `x++; x--;`),
`perm_refer_to_var` (`if (x) {}`), `perm_empty_stmt` / `perm_ins_block`
(`if (1) {}`, `do {} while (0)`, `goto l; l:;`),
`perm_duplicate_assignment` (dup to trigger the dedup/GVN pass),
`perm_var_cond_block` (duplicate a block under `if (v) … else …`),
`perm_pad_var_decl` (unused frame-pad var), `perm_factor_mult/shift`.
The prior hard-bucket survey named "a catalogue of optimiser-surviving
use idioms" as an instrumentation gap — this IS that catalogue, ready
made.  Use: **a reachability oracle for seat ties.**  If *some* no-op
perturbation flips the diverging seat, an IL-order lever exists and a
faithful edit is worth hunting; if the whole probe battery can't move
it, the tie is pinned below source (CASE-D-style evidence, per-function,
mechanical).  Note AGENTS.md records that Watcom folds some of these
(`(void)x`, `x*0`, dead-cond) — expect a subset to be inert; the probe
harness should report which survive 10.0a's optimiser, which is itself
reusable knowledge.

### 1b. The community's agent workflow — permuter as an agent SKILL

New since the earlier survey matured: the matching-decomp community has
converged on exactly our architecture and gone one step further:

* macabeus, *"Can LLMs Really Do Matching Decompilation? I Tested 60
  Functions"* (Medium) — LLMs reach matches on real retro-game corpora;
  validates `c2 decompile`.
* `malvarezcastillo/melee-decomp-agent`, `itsgrimetime/melee-decomp`,
  `decomp-mcp-server`, macabeus' **kappa** VS Code extension (Agent
  Mode: iterate until 100%) — all wire an LLM agent to the
  compile-diff loop, **and expose decomp-permuter as a skill the agent
  invokes when "stuck at 95%+ with only register-allocation diffs"**.
* The kappa/mizuchi history shows plugins that auto-fix AST classes
  between agent turns.

Mapping to us: `c2 decompile` subagents currently have
verify/ledger/census tools but **cannot invoke `c2 forge solve`**.
Adding a budgeted `forge()` tool to the harness (routed only when the
agent's own verify shows `fix_next: seat` or a stuck plateau) copies
the community's proven division of labour: agent does shape, search
does the last-mile seat.

### 1c. Compiler-pinning, corroborated — and our stronger variant

Devilution (reccmp #108): instruction-perfect still ≠ byte-perfect
because MSVC's internal sort is unstable; they got binary-perfect only
by **hacking the compiler to hardcode the sort**.  Our seat cluster is
the same wall.  But unlike them we already *have* an instrumented
10.0a (`~WV1` trace probes, `patch_trace.py`, the replay model at
100% on the corpus) — so we can run the **observing** version instead
of the blind one: read the tie's actual `ConfBefore`/creation order
from the trace, compute the *minimal input-order delta* that would
yield PS's seat (the inverse-compiler plan's step 4), and only then
search for a faithful source edit that produces that delta.  The one
specified-but-never-built probe (`~WV1 sc` Score probe, hooks
0x5a0aa/0x649c8/0x6e4dd) still blocks the CSE-placement class.

---

## 2. The plan

### Phase 0 — infrastructure unlocks (hours, do first)

1. **Fix the evolver.c win TU** (`affected_by_cover1` C2371 prototype
   conflict; likely one line in `c2_funcs.h` or a per-file extern, same
   as the 07-02 fix).  Unlocks W2 (win-census + win-verify + goto
   topology) for 6 of the 27 — including the monster `evolve_region`.
   Then fix the other 2 failing win TUs (`c2 win-verify` names them).
2. **`c2 triage --rebuild`** (the reachability axis is stale; the
   worklist says so).
3. Re-run `c2 win-verify` and `c2 win-census --corpus` so every
   remaining function has a current W2 verdict.

### Phase 1 — SHAPE burn-down (15 fns; the biggest tractable mass)

Standard ledger loop (`c2 ledger` → one island → verify → repeat),
donor-first, judged by `shape_distance`:

1. **★ the seven 1–2-island pure-ops fns** first (`cap_land_value`,
   `evolve_a_cm_row`, `start_samples`, `top_it`, `setup_enemy_units`,
   `show_move_highlight`, `trace_back_route_elastic`).  Each is one or
   two statement-form edits; several have residue-evidence comments
   from recent sessions — per Hard Rule #6 re-derive, don't trust.
2. **pm_map3.c cluster donor-first**: `show_battlemap_base` (file
   donor, 6 isl) → `mid3_line_no_sides_base` → `mid3_line_with_sides_base`.
   TODO.md documents the twin-loop anon-temp tie cluster here; the new
   probe mode (1a) is the designed tool for exactly this named residue.
3. `clear_an_area`, `stretch_to_3x3_house` (W2-unlocked by Phase 0),
   `set_route_elastic_range`, `action` (8 isl, 1771b — ledger
   island-by-island, first-diff-root discipline).
4. **`evolve_region` — the monster (117 isl)**, after Phase 0 gives it
   a win witness:
   * **type pass first**: 22 zext-idiom + 5 width tags = a handful of
     local `char`/`int` fixes collapse dozens of islands at once
     (proven pattern, TODO 07-03).
   * then ops islands via ledger; `slot:33` strictly last (downstream).
   * `c2 win-census evolve_region` for the named-local set before any
     decl grinding — its 33 slot islands smell like a wrong local SET,
     the class permutations can never fix.
   * candidate for a big-budget `c2 decompile` agent after the type
     pass.

### Phase 2 — port the missing faithful levers into forge (parallel with Phase 1)

From §1a: struct-ref form toggle, faithful boundary rewrite,
chain-assignment merge/split, `if(x)`↔`if(x!=0)`, const sign-absorb,
generalized temp-for-expr (block-crossing placement + var reuse),
partial expand-expr.  Each is a tree-sitter site preset + evidence doc,
same shape as the existing battery.  Then **build probe mode** (the
non-faithful battery behind a `--probe` flag that never writes to
decomp/src, reporting seat-flip reachability + which idioms survive the
optimiser).

### Phase 3 — the seat endgame (8 pure-seating + 4 seating-ctx)

Per function, in order:

1. **`c2 win-verify -v <fn>`** — certify or refute the shape (Hard Rule
   #7 order).  A win-diff = a Watcom-invisible shape defect; fix it and
   the seat often falls out (5x proven on the elastic family).
2. **`c2 regtrace <fn> --explain`** → named pair; **`c2 forge solve`**
   with the Phase-2-extended battery (the new levers are precisely the
   inter-statement forms the old battery lacked).
3. **Probe-mode reachability test**: no probe flips the seat ⇒ pinned
   below source; write the evidence, deprioritise per Hard Rule #6.
4. **For proven-reachable-but-unfound**: the trace-guided inverse step
   (§1c) — read the tie's input order from the `~WV1` trace, compute
   the required birth-order delta, hunt a faithful source edit for that
   delta.  Wire the **`~WV1 sc` Score probe** when a CSE-placement
   residue (evolve_land_value-class) is the blocker.

### Phase 4 — fidelity hygiene (background, cheap)

* Continue the **goto-topology pass on byte-exact functions** —
  `missing-goto` on a PS-exact fn is real shape drift the byte oracle
  can't see; fixes stay PS-exact.
* `c2 line-compare --offenders` + `c2 shape-recon --corpus --exact`
  sweeps after each batch of fresh exacts.
* Work the `c2 functions --win` PS-exact-but-win-diff list as the
  shape-recovery worklist (the second oracle's blind-spot coverage).

### Ordering rationale

* Phase 0 first because `evolve_region` alone carries ~117 of the
  corpus's islands and currently has NO W2 witness; one prototype fix
  lights up a quarter of the remaining corpus.
* Shape before seat because seat residues are frequently *downstream*
  of invisible shape defects (the elastic-family proof), and because
  every shape fix cascades into the tie groups.
* Probe mode before grinding the true ties, because it converts
  "we tried N levers and failed" into a mechanical
  reachable/pinned verdict per function — the difference between
  documented residue (Hard Rule #6) and wasted sessions.

### Success criteria

* Phase 0: 3 win TUs compile; win coverage 27/27.
* Phase 1: SHAPE class 15 → ≤ 3 (evolve_region may outlive the rest).
* Phase 2: ≥ 7 new faithful levers + probe mode in `c2 forge levers`.
* Phase 3: every remaining seat fn either byte-exact or carrying a
  probe-mode PINNED certificate + trace evidence (open per Hard Rule
  #6, deprioritised with proof instead of fatigue).

---

## Post-plan addendum: the `_rh` shadowing audit (2026-07-09, later session)

`decomp_verify.py`'s reassign-hint block (landed `042577c0`, 2026-06-18)
shadowed `_rh` (the regalloc-trace handle), silently starving THREE
trace-gated hint engines on every diffing function for three weeks:
`rover_hints.detect` (degraded to naive shift text), `parm_reload`
(dead), `closeability` (dead).  Fixed in `1db35afd`.  **Every residue
note / exhaustion certificate written 2026-06-18..07-09 that cites those
verdicts is suspect.**  Full 26-function re-sweep results:

| fn | fresh verdict | acted |
|---|---|---|
| top_it | Rover-closeable NEW: +1 dword self-heals after L1031/L1044/L1139 — **overturns the 07-07 "not source-lever-reachable" certificate** | 5 spellings probed (2 regress, 3 IL-inert); note updated |
| mid3_line_no_sides_base | Rover-closeable NEW: +2 after L393 | mid2 shared-tail terrain arm RE-LANDED (`f9ae7685`); prologue defect gone |
| mid3_line_with_sides_base | (ledger) RC-only word-reload + RMW spelling | cast + `\|1` fixed (`46cea315`) |
| take_census | Rover-closeable NEW: −3 after L447 (complements the two-mod fit) | — |
| setup_enemy_units | Parm-reload NEW + Cascade sim-CONFIRMED savings lever (bat_size_front 85→165) | parm-reload temp tried: 324→1190 regress (10 uses = real named value); savings lever needs ±8 loop uses, no faithful spelling |
| show_battlemap_base | Rover-fit: no single-mod (window fr#0..#23) | pressure lever landed earlier (`7c170f64`) |
| trace_back_route_elastic | Rover-fit: no single-mod, window fr#2..#3 | map.c dirty (parallel session), skipped |
| evolve_region / action / evolve_a_cm_row | Rover-blocked (honest negatives, now trustworthy) | — |
| build_city_item | trace-confirmed single inject on its anchor subset; full fit needs a PAIR (+2 head / +1 tail) | note corrected (`f8ec52db`) |
| others (start_samples, show_move_highlight, place2_a_building_top, fill_warehouses_with, check_goods…, figure_go_to_target, evolve_industrial_activity, place_sprite, cap_land_value, clear_an_area, set_route_elastic_range) | no trace-gated hint fires — these non-findings are now REAL (machinery ran with the trace) | — |

**Family mystery (pm_map3 battle-map scanliners)**: PS stores every
0xf/0xd/0xe dispatch const as an immediate; our compile hoists
`mov ebp,0xf` (Rule 110-L) whenever a register frees.  Whatever pinned
PS's allocator registers across these loops (not a visible local; win
Δ=0) is ONE lever that would close show_battlemap_base +
mid3_line_no/with_sides together.  Candidates: 10.0a hoist gating vs
the OW snapshot, or IL-order effect on WorthProlog — a wcc386-RE
question, not a source-spelling one.

---

## Second addendum: the `lw` complete-walk probe (2026-07-09, evening)

New instrumentation in the watcom10.0a repo (`9969cac`): the `~WV1 lw`
probe hooks LdStAlloc's per-instruction call site (`0x62de4` →
LoadStoreIns), recording EVERY visited op with opcode/line/type_class +
operand/result KINDS.  The `fr` stream is its RISCified subset; pairing
by ins ptr gives, per rover inject window, the complete +1/−1 candidate
map with WHY each op was skipped (Enregister's gates, from the 0x62939
decompile).  c2-side: `trace.py` parses `routine["lw"]` (`1bcfc92c`);
analyzer: `watcom10.0a tools/lw_map.py <fn> --window LO HI`.

**Model correction (was wrong in the hint text, now fixed)**: plain
`mov reg,[mem]` loads NEVER advance the rover — Enregister only
RISCifies (a) const-source movs storing to memory and (b) scan-class
ops (cmp/test/arith ≥0x2a) reading memory, by splitting the operand
into rover-load + reg-op.  Therefore the byte-neutral ±1 lever is
**load-folding**: `x = g; … x OP k` (pre-loaded, no advance) vs
`g OP k` inline (split → +1 advance, identical bytes when the rover
lands on the same register).  The −1 is the reverse (name the temp).
This is §10/§13 de-invent/add-intermediate with an exact mechanical
model and an ENUMERATOR.

First classifications:
* **top_it**: both closeability windows are kind-flip-free in BOTH
  compiles (PS `cmp edi,1` falsified the spilled-param idea in
  seconds).  The +1 there is an IL-op-birth or block-walk-order
  difference — a NEW divergence class; next probes: `ni` pairing /
  `bk` order diff.
* **take_census**: the window HAS foldable dword loads (L410 evolve_row,
  L414/L422 cm_sptr region) — the +1 lever hunt there is now a directed
  fold/unfold search over named lines instead of blind spellings.

Remaining instrumentation ideas (not yet built): `dn` GiveBestReg
denial-reason probe (the pm_map3 0xf-hoist capacity question), `ni`
birth-diff pairing across candidate spellings, `bk` walk-order
comparator vs PS block layout.

### Probe trio landed (same evening, watcom repo `1952cd3`)

All three "remaining instrumentation ideas" are now built and validated:

* **`dn`** (GiveRegister denial events): c2 parses `routine["dn"]`;
  validated 5/5 vs evolve_a_cm_row's known spills.  The pm_map3
  0xf-hoist question is now askable concretely: the const temp's `bt`
  tree candidates vs the with.regs/except union say what would deny it.
* **`lw_diff.py`**: 1-second line-blind walk differ — spelling probes
  for the ±N-advance hunts no longer need byte compiles to screen
  (first take_census fold candidate: proven walk-identical instantly).
* **`walk_order.py`**: walk-vs-layout map.  Structural discovery:
  **else-if chain arms are walked in REVERSE source order** while the
  layout stays source-order — top_it's dispatch walks last-arm-first.
  This is the mechanism space for the walk-order divergence class
  (Rule 122's substrate) and explains why the fire arm's advances sit
  where they do in the cursor stream.

Workflow for the ±N functions from here: `lw_map.py --window` for the
candidate map → hypothesize folds/de-folds/arm-moves → screen each with
`lw_diff.py` (1 s) → byte-compile only walk-improving candidates.

### lcx rejection probes + the fusion answer (same night, watcom `e568f3e`)

`lcx0..lcx5` complete the LdStCompress picture: every RISCified ins now
resolves to fused (`lc`) or a named reject.  pm_map3's last hop
answered: the 0xf store's EBP pair rejects **lcx0 = halves SEPARATED**
between LdStAlloc and LdStCompress — the byte-level "hoist" IS the
separated load half.  Both lcx0 rejects in the function are EBP picks
(EBX picks reject lcx3): the separator treats EBP specially.  Remaining
unknown in that chain: which pass separates (Score scan vs FlushAhead
OptPull — `fq` brackets it), though the caesar2-side lever is
unchanged (cursor +2 in window re-picks the store).

### Honest under-instrumentation map (what more would still help)

| stage | current probes | gap | payoff if instrumented |
|---|---|---|---|
| treegen tree→IL burn | tn/tb/tl (TREES with lines!), ni (ptr+nops+line), ge/il (codegen ctx + bytes) | the BURN decisions between tree and ins (fold/CSE/canonicalize) | a tree-diff tool over tn/tl needs NO new probe and localizes where a spelling dies (tree level vs burn); instrumenting the burn itself is the last mile |
| block-list construction | bk (walk markers only) | WHY arms walk in reverse; what reorders the list | top_it's walk-order class; hook block-birth (AddBlock family) |
| pair separator | fq (OptPull bracket), sb/sbi/sbs | which pass moves RISCify halves apart; why EBP-specific | closes the pm_map3 causal chain fully (suspects: Score scan, FlushAhead) |
| LdStCompress | lc + lcx0..5 (NEW) | none — complete | done |
| GiveRegister/GiveBestReg | al/rg/bt/gb/tg/wp + dn (NEW) | none material — complete | done |
| rover/LdStAlloc | fr/frx + lw (NEW) | none — complete | done |

### Consolidation: analyses moved into the global toolkit (caesar2 `4244c545`, watcom `43f7d27`)

The standalone watcom-repo prototypes are superseded; the canonical,
maintained homes are:

* `c2/regalloc/lwalk.py` — the lw/lc/lcx analysis library (window census,
  3-stage spelling compare, walk-vs-layout, fusion map), fully documented
  with the Enregister gate model inline.
* **`c2 spell`** — the new command (spelling localizer / `--fusion` /
  `--walk-order`).
* The **`Rover:` hint** now auto-appends `[lw census: ...]` per fit
  window (threaded via RegallocHint.lw, the same path as fr — no extra
  trace cost).
* Watcom repo: `tools/README.md` records the division of responsibility
  (probes there — `patch_trace.py` + `build-trace-image.sh` are the
  re-applyable source of truth; analyses here) and every superseded
  script carries a banner.

Separator finding folded in: Score's ReplaceLoad is the pair separator
(`sb` hits on exactly the lcx0 instructions) — surfaced as the lcx0
meaning string in `c2 spell --fusion`.
