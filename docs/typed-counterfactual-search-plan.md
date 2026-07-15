# Plan: typed counterfactual auto-search (the second half of tooling gap #9)

**Status:** deferred / not started.  The *distance-metric core* of gap #9 is
DONE and shipped (see below); this doc captures the remaining **auto-search**
half so we can pick it up later with eyes open.

## Where gap #9 stands

Gap #9 was "a hypothesis-driven counterfactual loop with attribution."  It
split into two parts:

* **DONE \u2014 the distance metric** (`c2/regalloc/seat_recon.py:shape_distance_from`
  + the located divergent source lines).  Every per-function tool now surfaces
  `shape_distance = {ir, width, spill, seat, shape, bytes, fix_next}` (a
  byte-INDEPENDENT, layered distance-to-PS) and `divergent_lines` (each
  divergence anchored to the exact PS `-d1` source line + what diverged).
  This is the enabler for everything below.
* **DEFERRED \u2014 the auto-search** (this doc): given a typed hypothesis, apply
  the minimal source transform, recompile, and report whether the IL moved
  TOWARD PS (via the distance metric) and which divergent lines closed.

## What the auto-search would do

1. **Derive typed hypotheses** from the already-located diagnostics:
   * `width` \u2014 "make local `X` signed `char`" / "make `X` `char`" (from the
     width diff + its divergent line).
   * `spill` \u2014 "keep value `Y` named/live" / "de-invent temp `Z`" (from the
     spill diff direction).
   * `seat` \u2014 "swap decls of `A`,`B`" / "move `A`'s last use up" (from the
     ConfBefore tie named by `regtrace`).
   * `ir` \u2014 control-flow / expression restructure (from the binir per-line
     divergence).  Hardest to mechanise.
2. **Apply the minimal source transform** with typed mutators (a small,
   audited set; NOT blind permute).
3. **Recompile** via the existing permute/verify container harness.
4. **Attribute** \u2014 report the per-layer `shape_distance` BEFORE\u2192AFTER and which
   `divergent_lines` closed, e.g. "moved toward PS (shape 27\u219221, width
   4\u21920); bytes 592\u2192636 (rose, but PS-faithful: keep it)".

## Benefits

* Turns the manual read\u2192edit\u2192reread loop into a guided, **attributed** search.
* The **attribution** is the real prize: it proves an edit is PS-faithful
  (shape dropped) even when the byte count rose \u2014 currently judged only by
  hand-reading asm (Hard Rule #3).
* The located divergent lines + typed mutators make the search **small and
  targeted**, not a blind reorder sweep.
* Could **batch-apply** the clean classes (width signedness / byte types)
  across the width-dominant corpus.
* Even a no-close run is useful: it **classifies the residue** (proves a tie
  is pinned, a type fix doesn't trigger, etc.) fast.

## Risks

1. **Typed fixes do not compose mechanically** (the cap_land_value lesson).
   The obvious transform often does NOT trigger PS's exact codegen: a plain
   `unsigned char rank_sum` did not produce byte arithmetic; `cl`'s `jge`
   needed `land_value` (a *shared struct field*) to be signed.  The mutator
   may need shared-type edits or expression restructuring it cannot find.
2. **Attribution \u2260 closure.**  Many edits move `shape` toward PS without
   closing `bytes`.  Useful direction signal; not a one-click solver.
3. **Shared-type blast radius.**  A width fix to a struct field changes MANY
   functions; the harness must verify the WHOLE corpus didn't regress (a
   `baseline check`), not just the target.
4. **ir-layer transforms** (control-flow restructure) are the hardest to
   mechanise safely and the highest value \u2014 a C control-flow mutator is a big
   build; better left to the agent guided by the located lines.
5. **Compile cost** \u2014 each variant is a ~10\u201330 s container compile.  A
   targeted search (a handful of typed hypotheses) is fine; a broad one is
   slow.  (Mitigated by the small, located search space.)

## Projected success rate (closer vs attributor)

As a **closer** (fully byte-exact):

| class | est. close-or-provably-toward-PS | note |
|---|---|---|
| `width` (signedness / byte), function-local | ~40\u201360% | cleanest; lower (~20%) when the trigger needs a shared field or expr restructure |
| `spill` (add/de-invent named locals) | ~20\u201340% | the exact live-set is hard to derive; often moves shape without closing |
| `seat` (tie reorder) | ~10\u201320% | many ties are provably PINNED (`control_buttons` permute 0/63); search mostly PROVES pinned-ness |
| `ir` (control-flow) | low | poor automation feasibility; agent-guided instead |

Overall as a **closer**: modest \u2014 maybe **15\u201330%** of the width/spill-dominant
diffing functions.  As an **attributor / triage accelerator**: high value
(objective direction signal + fast pinned-residue classification).

## Recommended phasing

* **Phase A (low risk, high value): the attribution harness only.**  Given a
  hand-applied edit (or a single typed hypothesis), recompile and report the
  `shape_distance` delta per layer + which `divergent_lines` closed.  No
  auto-mutation \u2014 the agent applies the edit.  This gives the "did my edit
  move toward PS?" signal objectively, cheaply, safely.  (Essentially a
  `regtrace --baseline/--vs` over the shape distance.)
* **Phase B (medium): typed mutators for the CLEAN classes** \u2014 width
  signedness / byte type for FUNCTION-LOCAL locals only, with whole-corpus
  regression verification.  Small, targeted, audited mutator set.
* **Phase C (high effort, uncertain): spill / seat / ir mutators.**  Defer
  unless A/B prove the loop's value.

## The metric is the enabler

The shipped `shape_distance` + located `divergent_lines` is the foundation:
it makes the search **targeted** (typed hypotheses from named layers/lines)
and **attributable** (before/after per-layer delta).  Without it the
auto-search was blind permute; with it, even a no-close run yields a
classified residue.  Start at **Phase A** when we return \u2014 it is the
cheapest slice and delivers most of the practical value (objective
"PS-faithful?" verdict) without the mutator risk.
