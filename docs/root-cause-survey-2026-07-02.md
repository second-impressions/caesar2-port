# Root-cause survey of the remaining diffing corpus (2026-07-02)

The remaining ~85 diffing functions (32.4 KB diff mass) resist the worklist's
named levers — the user-confirmed state is "flagged workable, actually
non-workable."  This survey re-derives the root causes from the ground truth
(PS `-d1` line records, the wcc386-10.0a trace, and the Mac/Win witness
binaries), names the mechanism per class, and defines the **three-witness
protocol** that turned two "parked" functions into worked lists in one
session.  Companion docs: `docs/wcc386-re/regalloc-model.md` (the allocator
model), `docs/mechanism-survey-2026-06-25.md` (§5b names the source→presort
gap this survey works around), `docs/wcc386-re/instrumentation-gap-per-class.md`
(the probe specs).

---

## TL;DR

1. **The worklist bucket labels mislead on this corpus.**  `shape-152` (19
   fns) and `const` (14 fns) are mostly offset-cascade artifacts (TODO.md
   already documents this for Rule 152); `decl-order` (17 fns) names a lever
   (Rule 115) that prior sessions exhausted.  Do not route by bucket.
2. **The byte mass (~25 KB of 32.4 KB) sits in ~30 "cascade heads"** — big
   map-sweep functions where ONE top-of-function allocator divergence
   (spill-set / callee-save set / frame size / top seat) shifts every
   downstream offset.  The binir `ir N/M` counts on these are contaminated
   by spill loads/stores; the true residue per function is 1–5 statement-form
   or placement divergences.
3. **The generalizable lever is the three-witness protocol** (below): PS
   `-d1` line marks give statement boundaries; the **Windows `/Od` binary
   gives a frame-slot census = the original's named-local set** (plus operand
   order, init constants, per-arm structure); the Mac binary gives reliable
   name↔function mapping and nesting.  Validated this session: the win slot
   census disagrees with our source on **51% of stuck functions vs 21.5% of
   byte-exact ones** — the stuck corpus systematically carries WRONG LOCAL
   SETS, and the census names the missing/invented local per function.
4. **What remains after shape is witness-faithful** is a small set of named
   10.0a mechanisms (§4): CSE-placement/cross-jump extent (needs the
   already-specified `~WV1 sc` Score probe), byte-seat cascades rooted in one
   dword seat, foreign-frame pairs, and anon-temp ties.

---

## 1. Corpus decomposition (evidence)

First-divergence census over the cached diff rows of all 85 (see
`.c2-cache/verify.json` `rows`):

| class | evidence at first diff | examples (PS diff bytes) |
|---|---|---|
| **spill-set / frame divergence** | PS spills where RC holds, or vice versa; `sub esp, K` differs | evolve_region (1857: PS stores `[esp+0x10]` we hold), evolve_a_cm_row (1356: PS holds EBP where we spill), build_city_item (1503: frame 0x18 vs 0x14), top_it (799), set_route_elastic_range (688) |
| **callee-save set divergence** | ± `push ebp`/`push esi` in prologue | place2_a_building_top (1216), mid3_line_with_sides_base (645), sf14_opertunist_fire (1556) |
| **top-of-queue seat swap** | first divergent instruction is a register identity | place2_sprite (1890: `xor ebp,ebp` vs `xor edi,edi`), battle_auto_resolve (1200: ebx vs edx), take_census (1004: byte-widen idiom + seat) |
| **statement-form residues** (1–5 lines) | binir names PS constructs at specific `-d1` lines | evolve_land_value (L750/L766), evolve_water_table (5 lines, each named), show_battlemap_base |
| **foreign-frame pairs (Rule 125)** | PS's symbol range contains blocks running under another function's frame | sf14_opertunist_fire ⇄ elephant_fire (inbound branch at +0x1ec; PS pushes 3, the shared region runs under elephant_fire's 5-push frame), evolve_security_activity |
| **IR-identical seat/slot ties** (20 fns, ✓IR) | `binir all N/N identical`; localized 1-seat diff per regtrace | region_go_to_target (40: ONE dword seat EBX↔EDX drives 25 byte-reg swap rows), place_sprite (7), elastic family |

Key discipline: **an early first-diff offset (≤ ~0x100) in a >300 b diff
means a single allocator root, not N shape bugs.**  Fix/diagnose the root
(regtrace names it); ignore the downstream rows.

## 2. The three-witness protocol (the "new lever")

For each function, three independent witnesses of the original source exist
beyond PS bytes.  Use them **in this order**:

### W1 — PS `-d1` line marks (statement structure; always available)

* One mark per source line; a construct with no mark is **compiler-emitted**
  (hoisted CSE, spill reload, cross-jump) — never chase it with a source
  statement.
* Mark COUNT per region discriminates `x = e; if (x)` (2 marks) from
  `if (e)` (1 mark).  Worked: evolve_land_value L750 — PS has ONE mark over
  load+mask+zext+test ⇒ the mask test is inline; our two-line local form was
  wrong (commit 07b923c2, recovered `zext_and_inplace`).
* `c2 line-compare` / the `stmt-map` SPLIT lines in `-v` also reveal PS's
  multi-statement lines.

### W2 — the Windows `/Od` binary (locals census; the strongest new signal)

MSVC 4.0 `/Od` gives **every named source local a distinct `[ebp-N]` frame
slot**, evaluates args in source operand order, and preserves per-arm
statement structure.  Extraction: compile the TU via `c2.win_bytes.compile_tu`,
disassemble both sides, collect `[ebp-N]` displacements + widths + use sites.

* **Mapping-quality gate is mandatory** (the win func-map is fuzzy):
  `matched_instructions / total` under difflib alignment.  Q ≥ ~0.85 ⇒ census
  trustworthy; Q ≤ ~0.6 ⇒ mapping/drift suspect (dock_the_ship 0.15 = wrong
  window).  Baseline: on PS-byte-exact functions the slot-count census
  matches 78.5%; on the stuck set only 49% — the gap IS the signal.
* What it witnesses: the named-local SET (invented/missing locals — the §13
  over-decompiled-mirror class made per-function and nameable), local TYPES
  (slot width; `xor eax,eax; mov al` = unsigned, `movsx` = signed),
  **source operand order** (`mov eax,[row]; add eax,[evolve_row]` ⇒
  `row + evolve_row`), init constants (`get_pseudo_map`: three const locals
  0xa0/0xa1/0x28 our source lacks), per-slot use profile (a 2-use dword slot
  = single-assign temp).
* Caveats: **port drift is real** (region_go_to_target: win adds `speed = 0`
  on the else path and moves the `flags & 1` test after the store — the PS
  asm contradicts both).  Treat W2 as a *candidate generator*; W1 + the PS
  asm adjudicate.  Ghidra's win-decompile view forward-propagates locals —
  read the **asm**, not the decompile, for the census.
* Watcom-invisible facts are still worth landing (byte-neutral,
  witness-faithful source): operand order, split variables whose live ranges
  Watcom merges anyway (commits 8f616473, bkind split).

### W3 — the Mac PPC binary (names + nesting)

Symbol names are authoritative (use to sanity-check win mappings and
function identity); local lists in the Ghidra decompile are PPC/TOC
artifacts — do NOT read them as a census.

### Worked end-to-end examples (this session)

| fn | witness finding | result |
|---|---|---|
| evolve_land_value | W1: ONE mark at L750 ⇒ inline mask test | `zext_and_inplace` recovered; residue reduced to Score-placement (commit 07b923c2) |
| evolve_land_value | W2: `[ebp-0x1c]` distinct from flags' `[ebp-0x30]` | `bkind` split from `flags` (witness-faithful, Watcom-neutral) |
| evolve_water_table | W2: extra 2-use dword slot holding `kind - 0xda` | named int temp ⇒ **ir 7/29 → 5/29, width → 0/16**; the "24/24 decl perms failed, parked" slot-swap case reopened (the perms could never change the TEMP SET) |
| region_go_to_target | W2: one local vs our two; PS asm shows the byte-seat root | census correct about the local count; the 40 b residue is the EBX↔EDX seat (25 byte-reg rows are collateral of it) |

## 3. Why the old levers failed (the honest mechanics)

* Rule 28a/115/decl-order act **inside equal-savings tie groups of named
  locals** — 9.6% of tie population (mechanism survey §4).  The stuck
  functions' ties are anon-temp-dominated; the named-local knobs are simply
  not connected to the diverging decision.
* `c2 permute`/forge enumerate INTER-statement edits over the *existing*
  local set.  A missing/invented named local changes the conflict/temp SET —
  outside every permutation's reach (evolve_water_table's 24/24 miss is now
  explained).
* The forward regalloc model is 100% but takes the presort as input;
  **source→presort is the gap** (§5b).  The win census closes the *conflict
  membership* part of that gap from the witness side; birth ORDER remains
  unmodelled (and is what the remaining seat ties hang on).

## 4. Remaining 10.0a mechanisms per class, and what closes each

| mechanism | 10.0a location | closes with |
|---|---|---|
| **CSE hoist placement + cross-jump extent** (evolve_land_value L750/L766; KNOWN_LAYER5 four) | `Score`@0x54df1 / `CommonSex` cost gate; cross-jump in emit | wire the **`~WV1 sc` probe** (spec complete in instrumentation-gap-per-class.md, hooks 0x5a0aa/0x649c8/0x6e4dd, never implemented). Until then these lines are classified, not workable |
| **byte-seat cascade from one dword seat** | `GiveBestReg` withregs gate @0x57c50 + ByteRegs list order | fix the ROOT dword seat (regtrace names it); never grind the byte rows |
| **marginal spill / callee-save divergence** (cascade heads) | ordinary `CalcSavings` ranking; membership/savings of the conflict list | W2 census first (wrong local set moves the spill boundary); then savings arithmetic per regalloc-model §2 |
| **foreign-frame pairs** | ComTail/emit-order block sharing | solve the PAIR jointly (sf14+elephant_fire); function-local edits provably cannot reach parity (Rule 125) |
| **anon-temp equal-savings ties, IR-identical** | ShellSort over creation order (UpdateLive backward walk) | honest sub-source residue once W1/W2 confirm the source; document the evidence + deprioritise (only byte-exact finishes) |

## 5. Infrastructure actions (ranked by unlocked functions)

1. **DONE this session — evolver.c win oracle**: `c2_funcs.h`
   `check_goods_in_region_warehouses` int→void (MSVC C2371 killed the whole
   TU).  14 stuck evolver.c functions now have W2.  **battle.c likely has a
   similar single blocker — fix it next** (11 stuck fns, incl. sf14,
   setup_roman_units, figure_go_to_target).
2. **Package the census as `c2 win-census <fn>`**: slot set + widths + use
   profiles + mapping-quality Q, diffed against our MSVC build; surface in
   `diagnose`/`dossier`.  (The analysis in this survey was done ad hoc via
   `c2.win_bytes`; ~100 lines.)
3. **Wire the `~WV1 sc` Score probe** (watcom10.0a repo `patch_trace.py`) —
   converts the CSE-placement class from "classified" to "workable."
4. **Win mapping refresh**: reject/flag mappings with Q < 0.7 (13 of 57
   currently); re-anchor via call-graph fingerprints.
5. **Worklist re-routing**: add a `cascade-head` verdict (early first-diff +
   large mass ⇒ route to regtrace root, suppress shape-152/const noise), and
   a `win-census` lever column.

## 6. Session recipe for the stuck corpus (for agent sessions)

1. `c2 regtrace <fn>` → read the **first divergent seat / localized verdict**
   (not the byte count, not the bucket).
2. **W2 census** (mapping-quality-gated): local-set delta?  Fix
   invented/missing locals FIRST — they move spill boundaries and tie groups
   wholesale.
3. **W1 line marks** at each binir-divergent line: 1-vs-2 marks decides
   inline-vs-local; unmarked code is compiler-placed — do not write source
   for it.
4. Only then the classic catalogue (Rule 44/49/151/152 forms) per divergent
   line; judge every edit by `shape_distance` layers.
5. If shape is witness-faithful and the residue is Score-placement /
   anon-tie: classify, cite this doc, stop grinding.
