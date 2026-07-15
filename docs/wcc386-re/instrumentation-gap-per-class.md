# What 10.0a RE / instrumentation each diff class needs (per layer)

For every divergence class we surface, this names **the specific 10.0a compiler
phase that is currently opaque** and **what RE / `patch_trace` probe would make
it transparent** — i.e. would turn the current *educated guess* into *hard
evidence* about the source delta.

Convention (same as `regalloc-trace-image.md`):
* "10.0a addr" = the app-offset in `wcc386.exe`'s relocated image (linear =
  `0x10000000 + offset`).  Known addresses come from the existing dump; "(?)"
  means **needs RE** (find the routine by name in OW v1 → locate the analogue
  in `wcc386` via call-graph / signature / table-pointer watchpoint).
* "Probe" = what to dump from a `patch_trace` hook at that address (the
  `~WV1` record format already used for RegAlloc).
* "Closes the guess" = the specific inferred-inverse the new data unlocks.

What we **already** trace (the baseline, for context — `regalloc-trace-image.md`):

| 10.0a addr | routine                | dumps                          |
|-----------:|------------------------|--------------------------------|
| `0x57b78`  | `GiveBestReg`          | conflict, cand, scores, pick   |
| `0x56f64`  | `FixInstructions`      | the actually-committed reg     |
| `0x57ed8`  | `GiveRegister`         | per-conflict entry             |
| sort/conf  | `SortConflicts`/`ConfList` | presort, postsort, savings |

That covers the **regalloc-tie** slice end-to-end.  Below is what's missing
per diff class.

---

## Already-analyzable classes (NO new RE needed — analysis on existing trace)

| class | what's missing | how to close (existing data) |
|---|---|---|
| **L4:callee-save-tie** (`install_mouse`) | which TWO values compete for the higher-priority callee-save slot | filter alloc rows by `regclass=dword` + recorded reg ∈ {EBX,ESI,EDI,EBP} + equal savings; the divergent pair is the two with PS-vs-RC swapped `reg_name`.  Then the lever is "make the value that should win have the EARLIER last use" — the value's `ins_walk` already names its last-use instruction. |
| **L3:pressure** (citymap_evolution) | which value is the marginal one near the callee-save threshold | already half-done in `pressure_detail`; promote from diagnostic to "name PS's preserved value + its savings gap above the spill margin" using the recorded `savings` field |
| **L4:treegen:use-order** (3 fns) | which expression to commute | for the divergent value, look at its `ins_walk` to find the producing instruction; if it's a commutative op (ADD/MUL/AND/OR/XOR) and the source line of that op has the two operands plainly, the commute candidate is named.  PS's asm at the same offset shows the desired op0; comparing op0_reg PS vs RC names the swap directly. |

These three close **without touching wcc386** — they're analyses we haven't
written yet on data we already capture.

---

## Classes that need NEW 10.0a RE + `patch_trace` probes

**RE STATUS (2026-06-22)**: all four originally-listed items have been
completed.  Two were already done before this audit (ComTail, FindRegister);
two were RE'd in this pass (Score = the real "loop-hoist" mechanism;
MergeIndex + the Rule-109 reframing).  Full RE deliverable lives at
`~/git/ReverseEngineering/watcom10.0a/docs/score-redundant-load-and-mergeindex.md`
(`Score` + `MergeIndex` topology, predicates, probe specs) alongside the
existing `tail-merge.md` (ComTail), `rover-model.md` + `parm-reload-rover.md`
(FindRegister).  Summary:

### L4:loop-hoist  (e.g. `show_regionmap_top` 137 b, `instant_reform` 260 b)

**RE'd — reframing required.**  PreOptimize loop-invariant motion is
**DEAD at PS flags** (per `wcc386_regalloc.py` PreOptimize entry).  The real
mechanism is **`Score`'s redundant-load coalesce failing when an aliasing
event invalidates the scoreboard** between two loads of the same global.

* **Phase**: `PostOptimize` → `Score` (`0x54df1`), per-block visitor
  `0x54b63`, scan + dispatch `FUN_00069ee7`.
* **Opcode-dispatch addresses** (the exact CMP byte sites for probing):
  `0x69ff1` CALL (`0x29`), `0x69feb` bound-op (`0x36`), `0x6a06d` MOV (`0x26`),
  `0x6a0ab` PARM_DEF (`0x28`), `0x69f37`/`0x69f8a` LABEL (`0x4b`).
* **Invalidation helpers**: `0x000649c8` (caller-save wipe), `0x0006e53e` /
  `0x0006e4dd` (per-register clear), `FUN_00069df5` (aliasing-store handler).
* **Coalesce action**: `FUN_0005a0aa` `ReplaceLoad`.
* **Probe**: `~WV1 sc <ins:hex> <opcode:hex> {coalesce|invalidate|miss}
  <reason> <name:hex>` — hook `0x5a0aa` (coalesce) + `0x649c8` /
  `0x6e4dd` (the two invalidate sites).
* **Closes the guess**: a single coalesce/invalidate stream per block tells
  us **exactly which ins** in PS's loop invalidated the scoreboard that RC
  didn't (or vice versa).  Inferred inverse: "add/remove a call to X (or a
  `*p = ...` store) between these two loads".

### L4:rover-scratch  (e.g. `timer`, many "Reg swap" tail rows)

**Done — preexisting.**
* **Phase**: `PostOptimize` → `LdStAlloc` (`0x62d95`) → `LoadStoreIns`
  (`0x62af3`) → `FindRegister` (`0x62a29`, found-return `0x62aaf`).
* **Probe (already shipping)**: `~WV1 fr <ins> <type_class> <except>
  <opcode> <op0>` — every scratch pick by the rover.
* **Closes the guess**: the trace already names every rover advance and
  exactly which value/opcode it fired on.  Used by
  `caesar2/c2/regalloc/rover_*.py` and `docs/parm-reload-rover.md`.

### L4:treegen:index-fusion  (Rule 109, e.g. `find_enemy` — known-hard)

**RE'd — reframing required.**  Two distinct mechanisms turned out to share
the "fusion" word:

* **`MergeIndex` (newly RE'd, `0x000626b3`)** — PostOptimize per-block sweep
  that fuses two N_INDEXED memory operands into one addressing mode.
  Candidate test at `0x00062676` (needs class `\x03` + size 4); predicate at
  `FUN_0006c5b2` (only fires for **opcode `0x0d` LEA-like or `0x01` ADD**;
  early-outs on scale > 3 / `FirstReg` conflict / class-1 operand / mode
  mismatch).  Probe: `~WV1 mi <ins> <opcode> {fused|rejected} <clause>`
  with `clause ∈ {not-candidate, scale-overflow, reg-conflict, class-1,
  mode-mismatch, no-match}`.
* **`find_enemy`'s Rule 109 is NOT MergeIndex** (the find_enemy site has the
  wrong opcode).  It is the **`CountRegMoves` MOV-credit coalesce** (already
  traced at `0x57728` via `cand_scores`): when `arr[i].field` is the only
  use of `i` and TreeGen lowers it to one IL value, the load's destination
  IS the index, and CountRegMoves coalesces both MOVs into the same register.
* **Open**: the **upstream TreeGen IL-shape choice** — whether `arr[i].field`
  lowers to (a) two IL values (PS, no coalesce) vs (b) one IL value (RC,
  coalesce).  We see the effect in `cand_scores` but not the choice.  This is
  a separate TREEGEN RE task (not blocking the main inverse, see Open Work
  below).

### L4:tail-merge / ComTail  (e.g. `show_battle_outtro_screen`, `evolve_a_building`)

**Done — preexisting.**
* **Phase**: emit; `OptPush` `0x4c798` (OC_RET handler) calls `ComTail`
  (`0x679ce`) via the `RetList` head at `0x80348`.  Predicate: longest
  common suffix > 5 bytes AND `OptForSize >= 25`.  Helpers: `FindCommon`
  (`0x67974`), `JustMoveLabel` (`0x6775a`), `OptInsSize` (`0x67720`).
* **Probe (already shipping)**: `~WV1 rl <count>` — RetList length at each
  `OptPush` OC_RET call.
* **Closes the guess**: the probe + the predicate addresses let us tell
  *which clause* RC failed for each missed merge.  See
  `~/git/ReverseEngineering/watcom10.0a/docs/tail-merge.md`.

### L2:shape  (op-asymmetry — when binir names "Rule 17b" etc. but the source
mapping isn't clear)

* **Phase**: frontend IL generation.  C statements like `a += k` can lower
  to `pre_gets_mem_const` (a `[mem] op= imm` IL op) OR to `mov reg, [mem];
  binary-op reg, imm; mov [mem], reg` depending on type, address-of usage,
  surrounding context.  The choice drives the rule registry classification.
* **OW v1 hint**: the `BG*` builders in `bld/cg/c/bg*.c` and the IL `Gen*`
  call sites in the frontend.
* **10.0a addr**: **(?)** — needs RE per-rule on demand (not a single
  routine; this is the breadth of the IL generator).  Cheaper path: build a
  rules registry that PAIRS source-shape variants against their emitted IL
  ops (we already have `c2 cgex` — extend it).
* **Probe**: for each `Gen*` call, dump `(source_line, op_kind, operands,
  type_class)`.  Heavy — instrument only the ops the rule registry covers.
* **Closes the guess**: per binir-named rule (e.g. "Rule 17b
  `pre_gets_mem_const` vs `mov_mem_imm + binary-op`"), the probe would
  certify *which source variant* produces each IL form.  Inferred inverse:
  pick the source form whose recorded IL matches PS's.

---

## Implementation work (now that RE is done)

| rank | item | effort | functions unlocked |
|---:|---|---|---:|
| 1 | Write the 3 **already-analyzable** analyses (callee-save-tie pair, marginal-pressure value, treegen:use-order expression) | analysis only, no RE | ~9 functions across L3/L4 |
| 2 | Implement the **Score `~WV1 sc`** probe in `patch_trace.py` (hook the 3 named sites) + the caesar2 consumer that pairs PS-vs-RC coalesce/invalidate streams | small — reuse the existing trampoline pattern | loop-hoist class + collateral on L1/L2 stacks |
| 3 | Implement the **MergeIndex `~WV1 mi`** probe (hook the 5 early-outs in the predicate) + caesar2 consumer | small | the *general* index-fusion class |
| 4 | Extend the L2 rules registry with paired source/IL fixtures (`c2 cgex`) | iterative, per-rule | many L2 cases |

## Open work (separate RE task, not blocking)

* **TreeGen IL-shape probe** — the upstream choice that drives `find_enemy`'s
  Rule 109 coalesce.  Not a single routine: TreeGen breadth.  Best handled
  via paired-fixture compares (per IL-shape rule) using the `cgex` registry
  + targeted `~WV1` probes at the specific `Gen*` site for each rule.  See
  the score/mergeindex doc "Rule 109 caveat" for why this is a measurement
  question rather than a single predicate.

All four originally-listed RE items are **complete**.  Implementation begins
with item 1 (zero RE), then items 2–3 (wire the new probes through
`patch_trace.py` and consume in caesar2's regalloc-verdict).

---

## What this changes

Today we're guessing at the source delta for the **rover-scratch**,
**loop-hoist**, **ComTail**, and **index-fusion** classes — and *each guess
has a cost*: a wrong source edit can regress bytes (as `find_enemy`'s comment
records).  The four RE/probe tasks above replace each guess with a
ground-truth pointer at *the exact phase decision that diverged*.  After
them, every L4 diff has either:

* a **hard-evidence** lever from existing+new traces (no permutation,
  no recompile gamble), or
* a documented "the predicate is X, RC failed clause Y" — an *honest*
  guidance even when no source lever exists (rare).
