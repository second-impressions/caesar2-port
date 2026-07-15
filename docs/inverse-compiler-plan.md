# The Watcom 10.0a matching decompiler — a phase-by-phase plan

*A recompilable, verified decompiler specific to Watcom 10.0a: it lifts PS.EXE
back to C that recompiles to the same bytes.  "Inverting the compiler" and
"decompiling" are the same task; this doc lays it out phase by phase.*

## Premise (why this is possible, and what "inverse" means)

`PS.EXE = f(S*)` where `f` is **Watcom 10.0a** and `S*` is the original C
source.  We *have* `f`: it is the **10.0a `wcc386.exe` binary itself**, which we
**run** (the container build / the `tools/patch_trace.py` instrumentation that
emits `~WV1`) and **decompile** (ghidra of `wcc386`, `watcom10.0a repo docs/wcc386-re/`, the
`~/git/ReverseEngineering/watcom10.0a` repo) **whenever we need its exact
behaviour**.  From that RE we have a **forward-exact** model of its register
allocator (`c2/regalloc/replay.py`: 1228/1228 sort, 19116/19116 selection on the
corpus) and the decoded cost model (`c2/regalloc/costs.py`).  Therefore a source
preimage `S*` **provably exists for every function**.  There is no "unreachable"
residue and no "floor" — only **slices of `f` we have not yet learned to
invert**.

> **Ground truth vs hint.**  The only readable *source* we have is **OW v1**
> (`vendor/open-watcom/`, the 2002 open-source snapshot) — a *cousin* of the
> target, ~7 years newer, whose codegen differs in places.  Use it as a **map
> of the algorithm's structure and names**, never as the spec.  The spec is the
> **10.0a binary**: every forward model below is trusted only after it is
> validated against the 10.0a *trace* (run) or its *decompile* (RE).  Where this
> doc names OW v1 routines (`Generate`, `RegAlloc`, …) they are the *structural
> hint*; the authoritative behaviour is whatever the 10.0a binary actually does.

We do **not** need a true mathematical inverse `f⁻¹`.  `f` is *not injective*
(many sources → the same bytes; every phase below loses information), so a true
inverse does not exist.  What we build instead is a **differential, phase-
localised search**:

1. Compile our current source `S` with a **fully phase-instrumented** Watcom and
   capture every phase's input/output for RC.
2. **Lift** PS's bytes back up the pipeline as far as the later-phase inverses
   allow → PS's reconstructed state at each phase boundary.
3. Find the **earliest phase** where RC's state ≠ PS's reconstructed state (this
   generalises the work-order layer attribution we already ship).
4. At that phase, run its **inverse**: given `(RC input, RC output, PS output,
   forward model fₚ)`, find the minimal **input delta** that makes
   `fₚ(input) == PS output`.
5. Map the input delta back to a **source construct** (the provenance map).
6. Apply, recompile, **verify the bytes** (the only ground truth — `f` is
   non-injective, so we confirm, never trust the prediction blindly).

Two directions matter and they are opposite:

* **Lift backward** (emit⁻¹ → … → frontend⁻¹) to *reconstruct* PS's state.
* **Attribute forward** (frontend → … → emit) to find the *earliest* divergent
  phase — that is the work order (fix the upstream phase first; everything
  downstream is its output).

## This is a decompiler (treat it like one)

Inverting `f` *is* decompilation.  What we are building is a **matching
(recompilable) decompiler specialised to Watcom 10.0a** — the same discipline as
the console-decomp community (`decomp.me`, `m2c`, `asm-differ`,
`decomp-permuter`), not a general decompiler.

Two things distinguish it from a *classic* decompiler (Ghidra / Hex-Rays) and
make it both harder and stronger:

* **Goal = byte-exact recompilation, not plausible behaviour.**  A classic
  decompiler may abstract the compiler away and emit readable,
  behaviourally-equivalent C.  We cannot: our output must recompile (under
  10.0a, fixed flags) to the *same bytes*, so the decompiler must **model
  10.0a's exact codegen idioms** (the ShellSort tie-break, the cost model, the
  2-address op0 reuse, the hoist-alias rule).  That is why it is "highly
  specific to Watcom 10.0a."
* **We have a verification oracle.**  A classic decompiler has no way to check
  itself.  We have `f` (run it) + `decomp-verify` (byte-compare), so every
  decompiled function is **verified**, not merely plausible.  This is
  *verified / matching decompilation*.

The project's existing pieces already ARE the stages of this decompiler — name
them as such:

| decompiler stage (inverse of …) | our component |
|---|---|
| disassembly (emit⁻¹) | `c2 disasm`, the byte/asm alignment |
| lift to IR | `c2/binir.py` (the recovered IR-tree per row) |
| codegen-idiom model (treegen/regalloc) | `c2/regalloc/*` (forward-exact), the rule catalogue |
| control-flow / structuring (frontend⁻¹) | `shape-recon`, the `-d1` line stream, `line-compare` |
| type recovery | `entities.h` types, `_TYPE_OVERRIDES`, const-audit |
| source-shape oracles | Mac decompile + PS-Ghidra decompile (both in `dossier`) |
| the multi-view IDE | `c2 dossier` |
| stage-fault attribution | `regalloc-verdict` slice tags (which stage is lossy here) |
| validation | `decomp-verify` (recompile + masked byte diff) |
| (assisted) permuter | `c2 permute` — use sparingly; lifting > search |

So "treat it like a decompiler" means: the **phase inverses below are the
decompiler's lifting stages**; each gets a **corpus-validated accuracy** (as the
regalloc model already has, 19116/19116); the 133 diffing functions are the
decompiler's **failing test cases**, each attributed to the stage that is still
lossy; and we **improve the worst stage first** (currently treegen).  We *lift*,
we do not *search* — the verifier confirms each lift, which is what keeps us out
of the auto-solver trap.

## The forward pipeline (per routine)

The phase *structure* below is read from OW v1's `bld/cg/c/generate.c::Generate`
(the **hint**); the authoritative per-phase behaviour is the 10.0a binary's, as
traced/decompiled.  10.0a's phase set is close but not guaranteed identical —
confirm any load-bearing detail against the 10.0a trace/RE, not OW v1.

```
   C source
     │  frontend + treegen   (parse → IL; expression trees; 2-address
     │                        lowering; addressing-mode / scaled-index
     │                        selection; FindRegister scratch seats)
     ▼
   IL (CG instruction list)
     │  PreOptimize           (CSE, copy-prop, dead-code, loop-invariant
     │                        code motion / hoisting)
     ▼
   optimised IL
     │  MakeConflicts         (conflict graph + CalcSavings)
     │  RegAlloc              (SortConflicts = unstable ShellSort by savings;
     │                        GiveBestReg = CountRegMoves argmax +
     │                        GivenRegisters tiebreak; spill; prologue push set)
     ▼
   register-assigned IL
     │  PostOptimize          (peephole, post-alloc cleanup)
     │  Schedule              (instruction scheduling — limited on 10.0a)
     ▼
   ordered machine instructions
     │  emit                  (encoding; branch-displacement sizing;
     │                        ComTail cross-function tail merge; alignment)
     ▼
   PS.EXE bytes
```

## Per-phase inversion table

Legend for **state**: ✅ have · ◑ partial · ⛔ missing.

### 1. emit  (encoding / branch sizing / ComTail)
* **Forward**: instructions → bytes.  Near-bijective except ComTail (a tail is
  replaced by a `jmp` into an adjacent donor) and branch-size selection.
* **Inverting means**: bytes → the instruction stream + which tails were merged.
* **Info input required**: the disassembly (have), the `-d1` line marks (have),
  function adjacency + donor table for ComTail (have, `tail_merge`).
* **State**: ✅ disasm/alignment; ◑ ComTail (we *detect* the jmp-vs-inline diff,
  `evolve_a_building`/`show_directory`; we do not yet *drive* tail formation).
* **Source lever**: make the two functions' tails bit-identical + rely on
  adjacency; otherwise this is a linker/codegen determinism to match.

### 2. Schedule  (instruction ordering)
* **Forward**: reorders independent instructions (10.0a does little).
* **Inverting means**: PS's instruction order → its pre-schedule order.
* **Info input required**: the dependency DAG of the window (derivable from the
  instructions); PS's order (from bytes).
* **State**: ◑ mostly identity; a few `sched_hint` cases.
* **Source lever**: usually none (post-source); matched by fixing the upstream IR.

### 3. RegAlloc  (conflicts, savings, ShellSort, GiveBestReg, spill, frame)
* **Forward**: optimised IL → registers + spills + prologue push set.
* **Inverting means**: PS's registers (read from asm) → the conflict order /
  savings / capacity decision that produced them.  Split into sub-levers:
  * **tie** (equal-savings ShellSort order): birth-order reorder — **already
    invertible offline & exact** (`inverse_search`; cascade verdict).
  * **savings**: the marginal value's weighted use-count (cost model).
  * **capacity / spill**: the simultaneously-live count.
* **Info input required**: RC's full alloc trace (✅ `regtrace`/`file_trace`);
  PS's per-value register + live ranges, reconstructed from the asm (◑); the
  forward model (✅ exact); the cost model (✅).
* **State**: ✅ forward exact; ✅ tie inverse; ◑ savings/capacity inverse
  (diagnostic only); ⛔ independent PS-side savings reconstruction.
* **Source lever**: statement/birth order (tie); use-count / live-range
  (savings); pressure (capacity).

### 4. treegen  (expression trees, 2-address, addressing modes, FindRegister)
* **Forward**: IL operations → per-instruction trees, operand order (op0 reuse),
  scaled-index fusion, scratch-reg seats.  Drives `CountRegMoves`, which drives
  RegAlloc tie-breaks — so a treegen difference *looks like* a register swap.
* **Inverting means**: PS's instruction selection (addressing forms, operand
  order, where a load fused vs stayed scratch) → PS's expression-tree shape.
* **Info input required**: PS's instruction patterns (✅ from asm — a scaled-index
  `[edx+eax*4+k]` vs a separate `mov;mul` reveals the tree); RC's per-instruction
  tree (◑ `ins_walk`); the forward treegen model (◑ — 2-address op0 reuse,
  commutative set, Rule 109 fusion modelled in `regsolve`/`replay`).
* **State**: ◑ forward partial; ◑ inverse partial (commute / use-order named, not
  driven).  **This is the largest un-built inverse** — it owns the most L4
  "out-of-tie" divergences (`treegen:use-order`, `treegen:index-fusion`,
  `treegen:savings`).
* **Source lever**: commute operands (op0 choice), split/merge sub-expressions,
  reshape an index expression, inline/pin a single-use temp.

### 5. PreOptimize  (CSE, copy-prop, dead-code, loop-invariant hoisting)
* **Forward**: IL → optimised IL.  **Information-losing** (CSE collapses,
  hoisting moves a load out of a loop, dead-code deletes).
* **Inverting means**: from "PS hoisted / did NOT hoist" infer the *property* of
  PS's input that drove the optimiser's decision.  Example (proven on
  `show_regionmap_top`): an invariant global is **reloaded inside the loop** iff
  a call or a possibly-aliasing pointer store sits in the loop; PS reloads ⇒ PS's
  loop had that aliasing site, RC's did not.
* **Info input required**: the optimiser's **decision models** (the alias test
  for hoisting; the CSE availability test) — *this is the key missing
  information*.  Ground truth = **10.0a RE** (decompile the hoist/alias code in
  `wcc386`); OW v1's `bld/cg` is the map for where it lives and roughly how it
  works.  Plus RC's pre/post-optimise IL (⛔ not yet dumped) and the loop/alias
  structure of both sides.
* **State**: ◑ a few decision rules known (hoist-alias); ⛔ pre/post-optimise IL
  capture; ⛔ general CSE/dead-code inverse.
* **Source lever**: add/remove the aliasing call/store; change a common
  sub-expression's reuse; change loop nesting of a reference.

### 6. frontend + statement mapping  (C → IL)
* **Forward**: source statements → IL ops, with `-d1` line marks.
* **Inverting means**: IL + line marks → source statement shape (this is
  `shape-recon` / the decompile).
* **Info input required**: the binir IR (✅), the `-d1` line stream (✅), the Mac
  and PS-Ghidra shape oracles (✅, now both in the dossier).
* **State**: ✅/◑ — the L1/L2 substrate+shape layers; well-served already.
* **Source lever**: the statement/expression rewrite itself (direct).

## The cross-cutting information inputs we must build

Most per-phase inverses need the **same four kinds of information**; building
these once unlocks several phases:

**A. A fully phase-instrumented Watcom** — dump every phase's I/O for RC, not
just RegAlloc.  This means **patching more of the 10.0a `wcc386` binary**: we
already instrument RegAlloc (`tools/patch_trace.py` patches 10.0a → `~WV1` →
`file_trace`: conflicts, savings, ShellSort queue, `ins_walk`).  Extending it to
dump **PreOptimize pre/post IL**, the **treegen trees** per instruction, the
**FindRegister scratch decisions**, and the **Schedule** order is itself an **RE
task on the 10.0a binary** (locate each phase's entry/structures in `wcc386`;
OW v1 is the map for *where* to look).  *This is the single highest-leverage
build* — it turns "we guess PS's intermediate state" into "we have RC's exactly,
at every boundary."

**B. PS-state lifters** (`emit⁻¹ … optimise⁻¹`) — reconstruct PS's state at each
boundary from the binary.  `emit⁻¹` = disasm (have).  `regalloc⁻¹` = infer PS's
per-value register + live range + savings from the asm (partial — `binir` gives
the ops, add live-range recovery + cost-model savings).  `treegen⁻¹` = read PS's
addressing/operand forms (partial).  `optimise⁻¹` = the hardest: infer the input
*property* from the optimiser's observed decision, using the decision model from
(D).

**C. Forward models `fₚ`** per phase — to *search* input deltas without a
compile.  Each is derived from OW v1 (structure) but **validated against the
10.0a trace/decompile** before it is trusted (the regalloc model's "corpus-
certified" status is exactly this validation).  Have: RegAlloc (exact), cost
model (exact).  Partial: treegen (2-address/commute/fusion in
`regsolve`/`replay`).  Missing: the PreOptimize decision models (hoist-alias is
the first to formalise), Schedule.

**D. Provenance maps** (phase input → source construct) — to make a delta
*actionable*.  We have `defline` per conflict; we need the IL-value → sub-
expression map (align the IL/`ins_walk` to the source AST) so "move this temp's
birth" or "this load fused" becomes a concrete edit on a concrete line.

**E. The verify loop** — compile + masked byte-compare (✅, `decomp-verify`).
Because `f` is non-injective, every predicted delta is **confirmed by a
recompile**, never trusted alone.  This is what keeps the whole thing honest and
keeps us out of the auto-solver trap.

## How the pieces compose (the realisable tool, not a solver)

The deliverable is **not** a closed-loop auto-solver (those oversell).  It is an
honest **attribution + inverse-lever pointer**, surfaced in the dossier map:

```
for a diffing function:
  attribute  → earliest divergent phase  (the work-order layer, now generalised
                                           to all 6 phases, not just regalloc)
  lift       → PS's reconstructed state at that boundary
  invert     → fₚ⁻¹ names the minimal INPUT delta to match PS
  provenance → the delta as a concrete source edit on a concrete line
  (human/agent applies it; verify confirms)
```

Each phase's inverse is added independently; the attribution already routes a
divergence to the right one (`regalloc-verdict` slice tags:
`optimize:loop-hoist`, `regalloc:capacity`, `treegen:use-order`,
`treegen:index-fusion`, `treegen:savings`, `rover:scratch-seat`).

## Build priority

1. **treegen forward+inverse** — owns the largest pool of currently
   "out-of-tie" L4 divergences (use-order / index-fusion / savings).  Needs (A)
   the treegen-tree dump + (C) the forward treegen model hardened + (D) the
   IL→source map.  Highest immediate byte coverage.
2. **PreOptimize decision models** — start with the **loop-hoist alias test**
   (one rule, already half-known, closes the `optimize:loop-hoist` class), then
   CSE availability.  Needs (A) pre/post-optimise IL + (C) the decision model.
3. **RegAlloc savings/capacity inverse** — promote the current *diagnostic*
   (marginal value + savings gap) to a provenance-mapped lever.  Needs (B) PS-
   side savings reconstruction.
4. **emit/ComTail driving** — turn tail-merge *detection* into a precondition
   check (tail identity + adjacency).  Small pool, well-bounded.

Phase (A) — extending the trace harness to dump every phase's I/O — is the
substrate that accelerates 1–3 and should be built first within each.
