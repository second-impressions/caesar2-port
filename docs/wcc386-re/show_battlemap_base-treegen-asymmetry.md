# show_battlemap_base — treegen asymmetry between the two loop edges

*Investigation note for the inverse-compiler-plan treegen slice.  Grounds
the `show_battlemap_base` residue at an actual phase, not "regalloc residue."*

## The residue (recap)

`show_battlemap_base`'s two near-identical loop edges both evaluate

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];

but Watcom emits *different* codegen for the multiply-accumulator on each:

| edge | PS accumulator | RC accumulator |
|---|---|---|
| top (L64)  | EBX           | EBX (matches PS top) |
| bot (L112) | EAX → EDX     | EBX (diverges from PS bot) |

`binir-shape`: `L64 RC has 1x mul_pow2` (RC extra on top); `L123 PS has 1x
mul_pow2` (PS extra on bottom) — *mirrored across the two edges*.  We earlier
proved the index-expression *form* is NOT the lever (2D / cached-row-ptr /
flat-ptr all canonicalise to identical IL; forge depth-3 / 4890 plans found no
shape win).  So the asymmetry is context-driven, not form-driven.

## Extraction inventory (RC forward trace)

`regalloc.file_trace(decomp/src/pm_map3.c)` for `show_battlemap_base`
(`code_size=674`, `has_regalloc=True`).  Per-phase forward substrate captured:

* **treegen** `cgen_events` (217): per-instruction `ge` records
  `{seq, ins, opcode, gen_class, line, result, op0, op1, offset, il_bytes}`.
  70 line-tagged, spanning L54–L145 — covers BOTH edges (top loop 30 instrs,
  bottom loop 27 instrs).  Source-anchored across the divergence region.
* **IRForest** `ir` (15 nodes but 31 statement roots) — the `tn`/`tb`/`tl`
  tree forest (partial: only statement-root trees retained).
* **PreOptimize index-fusion** `mergeindex_events` (389): `mic` 288 candidate
  tests, `mip` 97 predicates, `mi` 4 commits.  The 4 commits touch instrs
  `6c12e8ec` and `6c1287c8`, twice each — i.e. top+bottom edge pairs.
* **RegAlloc**: `confs` 69, `gb` 363 GiveBestReg candidate scores (**340 of
  them `saves==0`** — equal-savings ties; the accumulator seat lives here),
  `nb1`/`nb2` name births with `sort_sav` (ConfBefore tie input),
  `savecalc` 58, `presort`/`postsort` 64, `score_events` 361, `nt_pre`/`nt_post`.

**Gap flagged:** loop-hoist aliasing events (`sbs`/`sbi`, the
PreOptimize-loop-hoist substrate) are NOT present for this function (`oh`=0).
Either no qualifying hoists or the capture isn't enabled here — to investigate
for the PreOptimize inverse (#8).

## THE FINDING — the divergence is in RC treegen, not (only) regalloc

Comparing RC's `cgen_events` for the multiply region of the two edges:

```
TOP edge (identical expr):
  L67  op=3   res=..9888  op0=..2588  op1=..4912     # ONE multiply instr

BOT edge (identical expr):
  L114 op=53  res=0       op0=..9888  op1=..4912     # EXTRA op53 (no result)
  L115 op=3   res=..9888  op0=..9888  op1=..4912     # + 2-address form (op0==res)
```

**RC itself emits asymmetric treegen for the two identical expressions.** The
bottom edge has an *extra* `op53` and a *2-address reshape* (`op0 == res`)
that the top edge does not.  This is precisely the `treegen:index-fusion` /
`treegen:use-order` residue class the inverse-compiler-plan names as the
largest un-built inverse — and which it explicitly says "looks like a register
swap" because treegen feeds `CountRegMoves`, which feeds the RegAlloc tie-break
(the 340 `saves==0` ties).  The accumulator seat-flip is the *visible
symptom*; the *cause* is one phase up, in treegen.

Crucially this contradicts the earlier (wrong) classification "pure regalloc
residue / no source lever."  The earliest divergent phase is **treegen**, and
the R-side substrate (`cgen_events` + `nb1` births + `gb` scores) is already
captured so we can investigate it without first building the PS-side lifter.

## What this re-prioritises

1. The PS-side treegen lifter (inverse-compiler-plan info-input B / todo #5) is
   still needed to confirm *which* treegen shape (top's single multiply, or
   bot's op53+2-address) is PS-faithful — i.e. which side RC has to mimic.  But
   it is no longer on the critical path of ATTRIBUTION: RC is asymmetric in
   its own trace, source-context-driven (the j-loop tail leaves different
   `GivenRegisters` than the prologue does at the bottom-loop entry).  This is
   a `treegen:use-order` lever candidate (operand/operand-order / temp pinning
   / the bottom-edge setup-statement order), reachable from the forward model.
2. The earlier forge `-7b swap_stmts(L109,L110)` lived in exactly this region
   (bottom-edge setup: `i = 0; pm_shown_x = pm_x;`) — it moved bytes
   collaterally because reordering the setup perturbs the entry
   `GivenRegisters`.  That makes it a *candidate lever site* once we know which
   shape is PS-faithful, not a dead end.
3. The `mi` index-fusion commits on `6c12e8ec` / `6c1287c8` (twice each =
   top+bot) are the prime PreOptimize suspect for the asymmetry — worth
   diffing top-vs-bot fusion decisions next (RC-only, cheap).

## Open next steps

* Diff the top-vs-bot `mergeindex` (`mic`/`mip`/`mi`/`mir`) event streams for
  the two `ins` values — confirm whether index-fusion made a different
  decision on the bottom edge (PreOptimize-level cause) vs the treegen
  `ge` shape (treegen-level cause).
* Build the `treegen:use-order` inverse: given the bottom edge's
  op53+2-address shape, find the minimal source edit (operand order / temp
  pin / setup-reorder) that makes it match the top edge's single-multiply
  shape — then verify by recompile + masked byte diff.  This is the first
  concrete application of the treegen inverse the inverse-compiler-plan
  scopes.
* The PS-side lifter (#5) confirms which shape to target.

## Update — opcode decode verified against 10.0a binary (not OW v1)

The CG instruction opcodes were decoded using c2's `CG_INS_OPCODE_NAMES`
table (c2/ir.py), which values are **verified against the 10.0a binary**:
`OP_MOV=0x26` confirmed at address `0x580dc` (`cmp byte[ins+0x22],0x26`);
the `CRM_COMM={1,2,5,9,a,b}` commutative half-credit set confirmed at
`CountRegMoves@0x57728` (see ~/git/ReverseEngineering/watcom10.0a/
knowledge/wcc386_regalloc.py).  So this is the 10.0a spec, not OW-v1
(cousin ~7yr newer) interpretation:

  op=1   OP_ADD               op=3   OP_SUB
  op=5   OP_MUL               op=9   OP_AND
  op=38  OP_MOV               op=48  OP_CMP_EQUAL
  op=49  OP_CMP_NOT_EQUAL     op=53  OP_CMP_GREATER_EQUAL

## Genuine treegen-shape difference (verified opcodes)

Comparing RC's `cgen_events` for the textually-IDENTICAL `pm_shown_ptr =
pseudo_map[y][x++]` + `>= 0x0FFF0000` region on each edge:

  TOP (L64–L68):  MOV, CMP_EQUAL, MOV, SUB, CMP_GREATER_EQUAL
  BOT (L112–L116):MOV, CMP_EQUAL, CMP_GREATER_EQUAL*, SUB, CMP_GREATER_EQUAL
                                                       ^^^ EXTRA duplicate flag-set

The bottom edge emits **two** `OP_CMP_GREATER_EQUAL` instructions (L114
+ L116) for what is the single `if (pm_shown_ptr >= 0x0FFF0000)` test;
the top edge emits **one**.  Both source blocks are verbatim identical
(L64–L69 == L112–L117).  This is a source-independent treegen
materialisation difference inside RC, driven by the different
`GivenRegisters` / live-set context the interior `for(j…)` tail leaves
at the bottom-loop entry vs the prologue at the top-loop entry.

(The `pm_shown_y*324` multiply itself is the *same* shape on both edges
in RC — the asymmetry is in the immediately-following compare
materialisation, which is the L135 binir divergence `PS zero_test_jcc
vs RC branch_flag_jcc` showing up at treegen already.)

## MergeIndex index-fusion — EXONERATED (symmetric)

The two edge-paired fused instrs (`6c12e8ec`, `6c1287c8`) each received
the **identical** fusion pattern: 2 `mi` commits, 3 `mic` candidate
tests, 0 `mip`/`mir` predicate clauses.  MergeIndex made symmetric
decisions on both edges — so index-fusion is not the cause.  The
asymmetry is treegen-shape, not PreOptimize-index-fusion.

## Attribution locked

Earliest divergent phase = **treegen** (materialisation of the
`>= 0x0FFF0000` test).  Downstream cascade: the duplicated flag-set
changes `CountRegMoves` rewards → tips the 340 `saves==0` GiveBestReg
ties → flips the bottom-edge accumulator seat off EBX → the visible L64
mul_pow2 + L123 mul_pow2 mirrored asymmetry + L140/L141 mem_imm
collateral.  Per inverse-compiler-plan: "a treegen difference looks
like a register swap because treegen feeds CountRegMoves."

This is the concrete first case for the treegen inverse (todo #7):
find the minimal source edit (operand commute / temp pin / setup-statement
order at the bottom-loop entry) that makes the bottom edge materialise
ONE compare like the top, then verify by recompile + masked byte-diff.
PS-side treegen lifter (#5) confirms which single-compare form is
PS-faithful before driving the edit.

## Correction — the treegen-stage dup compare is collapsed before emit (Hard Rule #3)

Re-reading the FINAL asm (emit⁻¹, the solved phase) of the >= 0x0FFF0000
region on both edges:

  PS TOP (L67):  mov edi, [pm_shown_ptr];  cmp edi, 0xfff0000; jl ...
                 (value reloaded into EDI; test on EDI)
  PS BOT (L127/129): cmp eax, 0xfff0000; jl ...; sub eax, 0xfff0000
                 (value stays in EAX; test on EAX)
  RC BOT (final): cmp eax, 0xfff0000; jl ...; sub eax, 0xfff0000; cmp eax, 7
                 (ONE compare — matches PS bot)

So the bottom edge's TWO OP_CMP_GREATER_EQUAL at the treegen cgen_events
stage are a treegen-INTERMEDIATE that PostOptimize collapses to ONE
compare before emit.  The final-asm compare count is symmetric (one per
edge) on both PS and RC.  Hard Rule #3/#4 applies: judge by the asm, the
treegen-stage intermediate was misleading as a "duplicate" claim.

## Where this leaves the attribution (honest)

* The TREEGEN-stage IL IS asymmetric on the bottom edge (two CMP_GE
  per cgen_events), even though it collapses before emit.  That asymmetry
  perturbs CountRegMoves at the treegen level, which feeds the 340
  saves==0 RegAlloc ties, which IS downstream-visible (the accumulator
  seat flip EBX<->EAX).  So treegen is still the earliest divergent
  phase -- the mechanism holds -- but its PROOF is not "two compares in
  final asm" (false), it's "the treegen IL perturbs CountRegMoves
  differently per edge, tipping the equal-savings regalloc tie."

* The genuine FINAL-asm asymmetry between PS-top and PS-bot is purely
  a register seat: PS holds pm_shown_ptr in EDI on the top edge (re-
  loaded from the global after the index store) and in EAX on the bot
  edge (the load result reused).  That seat difference is the original
  symptom; the cause is the entry-context (GivenRegisters) difference
  at each loop's head -- exactly the open-treegen-inverse question.

## Next concrete step

The treegen inverse (#7) needs to answer: what source edit makes RC's
bottom edge's treegen IL land in the SAME CountRegMoves landscape as
the top edge (collapsing the treegen-stage dup), so the equal-savings
regalloc tie resolves to EBX like the top edge does?  Candidates named
by the inverse-compiler-plan for treegen:use-order: operand commute,
temp pin/split, index-expression reshape (already disproved as form-
swap), statement-order at the loop entry.  The earlier -7b
swap_stmts(L109,L110) lives exactly at the bot-edge setup -- revisit it
under the treegen-IL lens (cgen_events before/after the edit) rather
than the byte-count lens.

## Experiment — setup-statement order is NOT the treegen lever (decisive negative)

Tested whether flipping the bottom-loop-entry setup order (the earlier
-7b `swap_stmts(L109,L110)`: `i=0; pm_shown_x=pm_x` -> `pm_shown_x=pm_x; i=0`)
perturbs the treegen IL.  Applied to a scratch copy, re-traced, compared
bot-edge cgen_events.

RESULT: bot-edge treegen IL is byte-identical before/after the swap:
  MOV, CMP_EQUAL, CMP_GREATER_EQUAL, SUB, CMP_GREATER_EQUAL  (unchanged)
The duplicate CMP_GREATER_EQUAL at the treegen stage is STABLE across
setup-order perturbation.  CountRegMoves ties barely moved
(saves==0: 340 -> 341 of 363 -> 364).

CONCLUSION: the bottom-loop-entry SETUP-STATEMENT order is NOT the
treegen lever.  The -7b byte win was a downstream cascaded regalloc
effect (as the byte-lens reading earlier suspected), not a treegen-IL
change.  The treegen asymmetry is inherent to the loop BODY, not the
loop's entry setup.

## Where the genuine lever must live

The treegen-stage dup-CMP_GE is stable; what differs PS-top vs PS-bot
in the FINAL asm is the register-SEAT for pm_shown_ptr across the
`>= 0x0FFF0000` test:

  PS TOP: load eax -> [pm_shown_ptr]; ... mov edi,[pm_shown_ptr]; cmp edi,...
          (value RELOADED into EDI)
  PS BOT: load eax -> [pm_shown_ptr]; ... cmp eax,...  (value REUSED in EAX)

This is a live-range / persistence choice: does the load result stay
live in EAX through to the compare, or is EAX killed and the global
reloaded into a fresh register?  That choice is exactly what the
treegen inverse (#7) + PS-side lifter (#5) are needed to drive:
which source construct makes Watcom reuse vs reload.  Natural
candidates (per inverse-compiler-plan treegen levers):
  * an operand/temp pinning the load result earlier (forces reload)
  * the else-branch's `sprite_default = 0xe` occupying esi (present in
    TOP, dead by BOT) - may be why top reloads into a different reg
          than the bot reuses
  * an explicit cached local for pm_shown_ptr forcing a stable seat

Neither the index-form swap (dead) nor the setup-order swap (dead)
reaches it.  The next concrete move is to drive a treegen-lever (cache
pm_shown_ptr into a local at the bot edge, OR pinning across the
`if(update_map==0)` guard) through the cgen_events before/after lens
to see if it collapses the treegen-stage dup / changes the seat --
extending the treegen inverse (#7) as the first applied case.

## Session result 2026-06-30 (evening): ir 6/36 -> 4/35, mirror fully characterized

Three asm-verified recoveries committed (1242c402, then L160 fix, then
4af54dcf):

1. `unsigned char tile;` HOISTED to top-of-function (was declared inside
   the else blocks twice).  Fixes L135: both edges' tile tests are now
   byte-identical `test al,al` (same seat as PS).  Also the corpus/
   sibling norm (mid3_* declare tile at top).
2. Bottom terrain mask written NON-COMPOUND (`dirty = dirty & 0xf0`)
   where the top edge keeps compound `&=`.  Fixes L160: RC now emits
   PS's load/mask/store form.  Per-edge source asymmetry, same family
   as sprite_default(top)/literal-0xe(bottom).
3. The flat-index "fix" for L64 was a BINIR ARTIFACT (its asm had lea/
   scale-only addressing PS doesn't have; binir's tree normalisation
   scored it as matching).  Reverted to 2D.  binir has a blind spot at
   this construct family; judge it by asm.

## What remains (458bd, binir L64/L123/L140/L141) — THE MIRROR

RC's two edge multiplies are byte-for-byte PS's two edges SWAPPED:

  PS top  = acc-dest, scratch EBX, x in EDX, load [ebx+edx*4]
  PS bot  = y-dest,  scratch EAX->EDX, x in EBX, load [edx+ebx*4]
  RC top  = PS bot's exact realization (same registers!)
  RC bot  = PS top's exact realization (same registers!)

One allocation-order phase flip between two equal-savings realizations.
The constant-caching L140/141 (RC-only `mov edi,0xf / mov esi,0xd`
hoisted before the bottom loop) and the eax<->ebp pm_shown_ptr rename
ride the same phase.

Source levers EMPIRICALLY ELIMINATED for the mirror: index-expression
forms incl. byte-offset arithmetic (front end folds/canonicalises; and
the one binir "win" was an artifact), decl order + stmt order +
firstassign (87 forge plans in the NEW context; 4890 in the old), loop
form for->while (worse, ir 9/38), setup-statement order (treegen IL
byte-identical), cached-row-pointer, non-2D scale encodings.

## Open hypothesis for the mirror (new-rule territory)

The equal-savings tie order is decided by ConfBefore name-pointer
comparison; name pointers come from the compiler's heap, whose state
depends on the ENTIRE earlier TU compile (headers, statics, preceding
functions).  A preceding function can be byte-exact yet allocate a
different NUMBER of internal name structs than PS's original source did
-- shifting the heap phase and flipping later pointer-compared ties.
This is the §13 "over-decompiled mirror" corpus signal at TU scope.

Test: perturb the PRECEDING wrapper (show_battlemap, byte-exact) or the
TU prologue with byte-neutral source variations that change internal
name-allocation counts; watch whether the base function's mirror flips.
If it does, this is a NEW RULE with corpus-wide reach (the ~80 hard
functions likely include more phase-flip mirrors).
