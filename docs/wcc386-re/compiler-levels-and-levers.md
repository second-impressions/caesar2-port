# Watcom 10.0a Compiler Levels & Lever Map

**Purpose.** Stop grinding individual functions blind.  This maps the
compiler as a *pipeline of levels*, says at each level **what source-visible
lever exists or is still missing**, and — driven by the **root-cause** of
every diffing function — tells us **where to dig for the levers we lack**.

## The Determinism Principle (read first — it bounds every claim here)

The compiler is a pure function: `bytes = f(source, flags)`.  We have proven
`flags` (PS_CFLAGS), and PS.EXE = `f(PS_source, PS_CFLAGS)`.  Therefore **a
source that reproduces ANY byte sequence in PS.EXE provably exists** — the
Watcom 10.0a output is, by construction, the image of *some* C source under a
compiler we run on demand.

**Consequence:** "no source can produce this" / "not source-reachable" is
**never** a valid conclusion.  The only honest statements are:

* **LEVER KNOWN** — we have a source idiom that reproduces it (a numbered rule).
* **LEVER NOT FOUND** — the preimage exists; we haven't identified the source
  idiom yet.  This is *ignorance*, not impossibility.

A preimage can be hard to find for concrete reasons, none of which make it
impossible:

1. **Unknown source feature** — a type/width/signedness, a macro, a struct
   layout, or an expression shape in the 1995 source we haven't reconstructed
   (e.g. `text_buffer` may have been a typed array, not `char[]`).
2. **Joint/coupled decisions** — the divergence is a *consequence* of another
   choice (a zext idiom claiming EAX forces the index off EAX → materialise),
   so the lever lives at a different level than where the diff *appears*.
3. **Whole-TU / ordering state** — IL conflict order, definition order, and
   neighbouring declarations seed allocator tie-breaks.  (Integer regalloc is
   per-procedure, so a single function's preimage exists from its own source;
   but the source idiom may be non-obvious.)

So every "NO-LEVER" below has been **rewritten as "LEVER NOT FOUND"** with the
best current hypothesis for where the preimage lives.  Do not read any of them
as "impossible" — read them as "unsolved, deprioritised, here's the lead."

The grind is lever-limited, not effort-limited: every remaining diff needs a
source idiom we either have (rule catalogue) or haven't found yet.

---

## The pipeline (from `~/git/open-watcom/owp4v1copy/bld/cg/c/generate.c::Generate`)

```
FRONT-END (cc): parse → expression tree → type/promotion → fold
   │  (emits the CG IL: blocks of instructions over `name`s)
   ▼
cg PreOptimize()            ← generate.c:368
   MakeMovAddrConsts        (data-pointer literals)
   PushPostOps / DeadTemps / InsDead
   MakeFlowGraph → BlockTrim
   CommonSex                (CSE — common subexpression elimination)
   SetOnCondition
   [LOOP_OPTIMIZATION:]
     TransLoops             (loop test placement / rotation)
     LoopInvariant          (LICM — hoist invariants)
     IndVars                (induction-variable substitution)
     ReConstFold
     LoopEnregister
   MulToShiftAdd            (strength reduction: imul → shl/lea chains)
   FindReferences
   ▼
RegAlloc()                  ← the 7-layer model (regalloc-model.md)
   FPRegAlloc, then integer RegAlloc
   ▼
cg PostOptimize()           ← generate.c:436
   DeadInstructions
   BuildIndex / MergeIndex  (ADDRESSING MODES: SIB scale, disp folding)
   LdStAlloc                (stack-temp slot allocation + coalescing)
   Score
   LoopRegInvariant
   Conditions               (condition-code / flag reuse)
   [INS_SCHEDULING:] Schedule   ← OFF for PS (no -or)
   LdStCompress             (load/store coalescing)
   ▼
GenObject()                 ← instruction SELECTION + ENCODING
   386table.c reductions    (SWAPCMP, G_RR2, …; Rule 103)
   ComTail                  (tail-merge: fold identical epilogues; Rule 15/42)
   branch encoding          (short EB / near E9; Rule 16)
   OMF emit
```

---

## Per-level lever status

Legend: **LEVER-RICH** (source reliably steers it) · **NARROW** (lever exists
but applies to a small sub-case) · **LEVER NOT FOUND** (preimage exists —
Determinism Principle — but the source idiom is unidentified / deprioritised;
formerly mislabelled "no-lever").

### L0 — Front-end type & promotion  → **LEVER-RICH**
The single most reliable lever surface.  `char` signedness, declared width,
`(unsigned char)` vs `& 0xff`, `signed char`, narrowing casts.
Rules: **8/23, 49, 49b, 53, 99, 102**.  Fix substrate in `entities.h` /
`_TYPE_OVERRIDES` (Phase 0) — one field-type edit flips many functions.

### L1 — Front-end expression tree shape  → **LEVER-RICH / NARROW**
Operand order is preserved literally (Rule 4); `x+x` vs `x<<1` (Rule 62);
boolean materialisation (Rule 53); prototype visibility / implicit-int
(Rule 37) feeds CallZap.  Decl/statement order seeds the IL conflict order
(→ regalloc tie-break, Rules 28a/100).
**LEVER NOT FOUND corner:** register-vs-register `cmp` operand order tracks
register priority (Rule 103) — FE order and reg choice move together, so simple
operand reorder can't split them.  A preimage exists; not yet found.

### L2 — CSE (`CommonSex`)  → **NARROW**
Decides whether two equal subexpressions share one computation.  Lever:
make them *not equal* (narrowing cast inside one, Rule 102) to force re-emit;
or factor a shared temp to force CSE.  Few rules here — **under-explored**.

### L3 — Loop opts (`TransLoops`/`LoopInvariant`/`IndVars`)  → **LEVER-RICH**
Loop test placement (`goto outer_test`, do/while — Rules 71, 93), IV
substitution + LICM (Rule 33), parallel-counter init/step order (Rule 79),
invariant reload structure (Rule 50).  Active at default opt; **never `-ol`/`-oa`**.

### L4 — Strength reduction (`MulToShiftAdd`)  → **NARROW**
`imul` vs `shl/lea/add` chains, cost-gated by `OptForSize=50`.  Source lever:
the multiply-constant shape; mostly flag-determined, little source control.

### L5 — Register allocation  → **NARROW (the hard residue)**
The 7-layer model (`regalloc-model.md`).  Levers: type→class (L0), use-order
(Rule 28a/100 — decl/statement reorder), savings (extra/fewer uses), move-elim.
**LEVER NOT FOUND corner (large):** equal-savings `(R,R)` ties resolved by the
unstable savings ShellSort seeded by ConfList order — `entering_new_square`,
proven not source-steerable (Rule 103 §IR-lever hunt).  Second worked example:
`basic_temple_screen` (432 b, the tail-merge DONOR for ~2330 b of dependents).
Its head-multiply accumulator (`skill*80` in EDX vs EAX) is a *symptom*; the
root is a sav=50 tie between the loop locals `r` (rating) and `icon_x`, which PS
resolves `r`→ECX / `icon_x`→spill and RC resolves the opposite way (same 4
spilled values, same frame — only *which* one spills differs).  At `r`'s def
ECX is free in PS but masked in RC by an `icon_x` sub-temp — a conflict-graph /
scheduling difference below the source layer.  Seven source levers all regress
(decl reorder, use-order, range-shorten, statement-swap, named temp, etc. — see
the `basic_temple_screen` header comment in `decomp/src/screens.c` for the
measured deltas).  Cracking it needs the conflict-graph *input* difference
(IR-scheduling / ConfList seed), not a C reorder.

### L6 — Addressing-mode / index build (`BuildIndex`/`MergeIndex`)  → **NARROW (non-power-of-2 strides only) — validated**
`global+field` folded to disp32 vs cached row-pointer.  Rules **63, 73, 101**.
**Validated limit:** the lever exists ONLY for **non-power-of-2 strides**
(0x15a, 20, 1600, …), where x86 SIB can't scale so Watcom must materialise the
index — making cache-vs-inline a real choice.  For **power-of-2 scales**
(`idx*2/4/8`) addrfold *always* uses a SIB scale `[idx*N+disp]`; PS's
materialised form is NOT source-reachable (every `idx*4` C form reduces to the
scale).  **CORRECTION:** `get_buffer_ofset` (×4) is NOT a no-lever case — its
materialised index is a *consequence* of the Rule 49 clear-first zext idiom
claiming EAX (`xor eax,eax; mov al,[edx+disp]`), which forces the index off EAX
into EDX.  The lever lives at L0 (the zext idiom) coupled to the accumulator
register choice, not L6 addrfold; the preimage exists, not yet triggered.

### L7 — Stack-temp allocation (`LdStAlloc`/`AssignOtherLocals`/`ReUsableStack`)  → **LEVER NOT FOUND**
Whether two non-overlapping spill temps get distinct slots (frame size
`sub esp,N`) or coalesce.  `refresh_svga_screen` proved not source-steerable.
**Re-examine for a lever** (it's a high-volume root cause — see below).

### L8 — Prologue / callee-save (`WorthProlog`, `intel/c/i86regsv.c`)  → **LEVER NOT FOUND**
Which callee-saves get pushed (`push ebx/ecx/...`).  `WorthProlog` keeps a
chosen callee-save iff `savings >= push+pop (~2)`, but that only gates
callee-save-**vs-spill** — it is *not* what the observed push-set diffs are.
Validated negative (Rule 105): `forum_update_census`'s extra `ebp` push is
`GiveBestReg` putting a non-call-crossing value in EBP where RC (optimally)
uses caller-save EAX — a register-*choice*, not a threshold crossing;
`perform_region_strip_action` is a spill *cascade*.  The savings threshold is a
useful **diagnostic** (savings < ~2 can't hold a callee-save) but there is **no
push-economics / savings-nudge lever**.  Act only if the extra save maps to a
real L1/L5 lever (EAX-boundary call-crossing, or first-use order).

### L9 — Instruction selection / encoding (`GenObject`, `386table.c`)  → **LEVER NOT FOUND mostly**
Operand-shape reductions (Rule 103), branch short/near encoding (Rule 16 —
layout cascade), `ret` vs tail-merge `jmp`.

### L10 — Tail-merge (`ComTail`)  → **LEVER = source order**
A later function folds its identical epilogue into an earlier function's tail.
Lever: function *definition order* (donor before dependent — Rule 15/42).
Body must match first; otherwise the merge is a layout artefact.

---

## Where the diffs actually come from (ROOT-CAUSE, not cascade)

Classifying the **first divergence** of all 367 diffing functions (everything
after is cascade) by the phase that produced it:

| root-cause level | functions | lever status |
|---|---:|---|
| L5/L7 regalloc reg-identity (incl. `sub esp` frame size) | 103 | NARROW + lever-not-found |
| L2/L7/L10 CSE / spill / tail-merge (instr-count differs) | 105 | MIXED |
| L9 branch-encoding / control-shape | 52 | lever-not-found |
| **L0 type-width (zext/sext)** | **48** | **LEVER-RICH** |
| L8 prologue / callee-save push-set | 43 | lever-not-found (Rule 105) |
| **L6 addressing-mode (index build)** | **10** | **NARROW, dig** |
| other | 9 | mixed |

### Reading this map
* The **lever-rich** levels (L0 type-width 48, L3 loops, L6 non-pow2 addressing)
  are the *known-closable* classes — work these first; the source idiom is
  identified.
* The **bulk** (L5 ties, L7 stack coalescing, L8 prologue, L9 encoding/layout,
  L10 tail-merge-as-cascade) is currently **LEVER NOT FOUND** — that's *why* the
  `--solve` sweep found only 4/370 mechanical wins.  **Per the Determinism
  Principle these are NOT impossible** — a source preimage exists for every one;
  we simply haven't identified the idiom (often because the lever is coupled to
  another level, like get_buffer_ofset's index materialisation living at L0 not
  L6, or needs whole-TU ordering control).  Deprioritised, not closed-off.

## Where to dig for NEW levers (ranked by volume × plausibility)

1. **L0 type-width (48 fns) + L3 loops — the remaining lever-rich work.**
   These are the genuinely closable classes; grind them per-function with
   `decomp-verify` rule-hints.  (L6 addressing is leverable only for
   non-power-of-2 strides — validated, Rule 73 "Hard limit"; power-of-2 scales
   coupled to the L0 zext idiom (Rule 49) — see the L6 CORRECTION — not an
   addrfold law; lever not yet found.  L8 push-set lever not found — Rule 105.
   Deprioritised, not impossible.)
2. **L7 stack-temp coalescing (subset of 103).** `ReUsableStack` coalesces by
   size + non-overlapping instruction-ID range.  Is the ID range (hence
   coalescing) perturbable by statement order?  `refresh_svga_screen` said no
   for one case — test the general claim with `cgex`.
3. **L6 addressing-mode (10 fns, only 3 rules).** Most clearly leverable and
   most under-developed.  `BuildIndex`/`MergeIndex`: when does `idx*scale` fold
   to SIB vs materialise?  Testbed: `get_buffer_ofset`.  Likely yields 1–2 new
   numbered rules quickly.
4. **L2 CSE (under-explored).** Only Rule 102.  The instr-count "insert/delete"
   root causes (105) are partly failed/extra CSE — a CSE-control lever
   (force/defeat sharing via expression identity) could address several.

## Method for a lever hunt
Use `c2 cgex` (isolated single-TU codegen experiments) on the named testbed
function: enumerate source variants, byte-compare each to PS, and when one hits
0 (or isolates the trigger), capture it as a numbered rule in
`watcom-codegen-patterns.md`.  Gate every claim on `decomp-verify` —
a matched rule-hint is **not** proof the lever closes the *gating* diff
(see Rule 103 and the type-width false-positive lesson:
`regtrace --explain` flags values that *exist*, not values that *diff*).
