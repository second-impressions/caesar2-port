# ComTail cascade analysis — the donor-first leverage is (mostly) a mirage

**TL;DR.** Watcom's cross-function tail-merge (`ComTail`, Rule 42) builds
a real dependency graph: ~490 PS.EXE functions end in a `jmp` into a
*donor* whose epilogue they share.  It is tempting to think "fix the
donor → its dependents cascade byte-exact."  **Empirically that cascade
is almost entirely a confound.**  Across the whole corpus only **2**
dependents are genuinely *tail-merge-blocked*; the other ~370 have their
own independent **body** diffs that a donor fix does not touch.  Do not
build effort around the donor-first cascade — it does not bottleneck the
non-byte-exact count.

This document records the validation so future sessions don't re-derive
it.  The tooling that operationalises it is `c2 tail-merge` (the `#tb`
column and `--blocked` view).

## The mechanism (why a cascade *could* exist)

`bld/cg/c/optcom.c::ComTail(list, ins)`:

* `list` = the label's `refs` chain (every jump to a shared label);
  `ins` = the jmp currently being processed.
* `FindCommon` walks **backwards** from each candidate `try` and from
  `ins`, accumulating the shared instruction suffix (`CommonInstr`: same
  class + reclen + bytes).  The `try` with the **maximum** common tail
  becomes `first` (strict `>`, so the *first* max wins ties).
* `ins`'s tail is deleted and replaced with a `jmp` to a new label at
  `first`'s tail.  So **`first` keeps the tail inline (canonical)** and
  `ins` jumps to it.
* Gates: `OptForSize >= 25` **and** `max.save > OptInsSize(OC_JMP,
  near)` (= 5 bytes).

**Key property: ComTail is deterministic given identical IL.**  Same
instruction streams + same `refs`-chain order ⇒ same canonical choice.
Therefore a PS↔RC tail-merge byte-diff is *downstream of* a body/IL diff
in some cluster member (or a refs-chain ordering difference) — it is
**not** an independent "merge direction" knob you can turn from C source.
`c2 func-order` already guarantees the per-TU emission order matches PS,
which removes the ordering degree of freedom in the common case.

## The validation (donor-exact ↔ dependent-exact is confounded)

Scan every code function for a terminal tail-merge jmp
(`scan_tail_merge_donor`), cross-reference each dependent's byte-diff
status (`decomp-verify --json`):

| donor status | dependents | dependent byte-exact |
|---|---:|---:|
| donor **exact** | 211 | **193 (91.5 %)** |
| donor **diffs** | 158 | 52 (32.9 %) |

The 91.5 % looks like strong donor-first causation.  It is not.  Locate
*where* each blocked dependent's diff bytes fall:

* A dependent is **tail-blocked** only if its *entire* diff is in the
  shared tail it merges away (PS emits `jmp donor`, RC kept the epilogue
  inline) — i.e. all diff offsets in the last ~12 bytes.
* Result over the whole corpus: **2** tail-blocked dependents.  Every
  other "blocked" dependent has large **body** diffs (e.g.
  `build_road_from_elastic`: 780 body-diff offsets vs 4 tail;
  `goto_flag_marker_mode`: 15 body, 0 tail).

So the correlation is **shared regional difficulty**: a donor in hard
code (heavy regalloc, byte-packing) sits among dependents in the same
hard code; both diff for independent reasons.  Fixing the donor reduces
each dependent by at most the 3-4 shared-tail bytes — it does **not**
flip them byte-exact.

## The 2 genuine cases

```
dependent          Δ   donor                       donorΔ
put_danger_flag    1   one_reg_wall_ramification   152
show_this_tribune  2   basic_temple_screen         439
```

For these the dependent's only divergence is the merge itself (PS `jmp`
vs RC inline).  To flip them you must make the **donor's shared tail**
(not its whole body) byte-exact so ComTail re-merges.  Both donors are
large (152 b / 439 b) but only their *tail* matters — a focused tail fix
may suffice even with a diffing donor body.

Reproduce: `c2 tail-merge --blocked`.

## Practical guidance

* Trust the **`#tb`** column in `c2 tail-merge`, not `#dep` / `ΣΔ` /
  `ROI` (those count all dependents and are confounded).
* Do **not** invest in a "ComTail canonical-selection controller" to
  flip merge direction — the determinism result means there is nothing
  to flip from C beyond fixing the underlying body/IL diff (which is the
  per-function regalloc work you'd do anyway).
* The remaining ~340 non-byte-exact functions are **irreducibly
  per-function** regalloc/body diffs, not a tail-merge dependency forest.
  There is no structural shortcut to close them en masse.

## Methodology / tooling

* `scan_tail_merge_donor` (`c2/commands/tail_merge.py`) — the per-function
  terminal-jmp detector.
* `_is_tail_blocked` + the `#tb` column / `--blocked` view
  (`c2/commands/tail_merge_rank.py`) — the body-vs-tail classifier that
  operationalises this finding.
* Source of truth for the algorithm: `bld/cg/c/optcom.c` (`ComTail`,
  `FindCommon`, `CommonInstr`, `ComCode`, `TraceCommon`).

## Addendum 2026-06-15 — the "framed mid-epilogue" sub-class is a *block-layout* wall, not a ComTail knob

The `~donor` functions whose only divergence is epilogue **position** (PS
puts the framed `add esp,K; pop…; ret N` epilogue mid-function with the
`count<=0`-style guard jumping to it; our build funnels it to the end and
the dependents `jmp` to a different donor) are **not** ComTail
merge-direction cases.  Worked example: `devolve_a_building` (donor) /
`evolve_a_building` (1-byte dependent, `jmp devolve+0x11` vs inline).

**Correction (2026-06-15, binary-confirmed):** the OW-v1 cg source
(`object.c::SortBlocks` with the `BestFollower`/`Predictor`/
`BRANCH_PREDICTION` machinery) is a **later** version — it does NOT
match wcc 10.0a.  Verified directly in the 10.0a `wcc386.exe` Ghidra DB
(`~/git/ReverseEngineering/watcom10.0a`, functions `SortBlocks@0x5c4e3`,
`GenBlockCode@0x5c2d7`, `CloneCode@0x67204`):

* **10.0a has NO block-reordering / branch-prediction pass at all.**
  `SortBlocks@0x5c4e3` is a plain stable **bubble sort by gen_id**
  (`block+0x54`).  Block layout == gen_id (front-end block-creation)
  order, period.  (The earlier "BRANCH_PREDICTION gate" framing was
  wrong — that gate only exists in the newer OW-v1 source.)
* `GenBlockCode@0x5c2d7` (OW `GenObject`'s per-block emit body) walks
  the block list in layout order and, on `block->class & RETURN`,
  emits `GenEpilog()` **inline at that block's gen_id position**.  So a
  source-position `return;` becomes an epilogue at its gen_id slot
  (the 10.0a FE emits a real epilogue+ret per return; owp4v1 lowers
  return as `Jump(end-label)`).
* The framed-vs-frameless split is the **epilogue clone/funnel size
  gate**, not reordering.  `CloneCode@0x67204` clones a `≤region`
  epilogue over a jmp-to-it iff `region ≤ jmp_objlen` (scaled by
  `(100-OptSize)/25` only when OptSize<50) OR the jmp is non-short-able.
  An 8-byte framed epilogue (`add esp,N; pop x2; ret N`):
  - OptSize=50 (our flags): budget = jmp objlen (5/6) < 8 → **never
    clones, funnels to END** regardless of arm size.
  - OptSize<50 + a *far* (non-short-able) jmp: budget scales to 10..20
    → clones → MID.
  - OptSize<50 + a *short-able* jmp (small arm): END.

Reproduced with minimal probes (`watcom10.0a/probes/framed-epilogue/`):
FR2 (4b frameless) = MID; FR3 (8b framed, small arm) = END at OptSize
{50,100,0}; FR4 (8b framed, large arm) = END@50 / MID@`-ot`.  And the
source-reachability dead-ends still hold (guard reorder, `goto done`,
if/else-if all canonicalise to the same IL at gen-order end).

**Conclusion:** the framed mid-epilogue class is fixed 10.0a layout
behaviour at OptSize=50 — every framed epilogue funnels to the END.
PS's framed *small-arm* mid epilogues (e.g. `devolve_a_building`) are
NOT reproducible by any known mechanism at OptSize=50: not block
reorder (none exists), not CloneCode (needs OptSize<50 + a far jmp,
which devolve lacks), not the FE 5-byte inline budget (8>5).  The
residual Rule 135 open question is now precisely bounded; do not grind
these from C source.

**Correction (2026-07-07, `e27e4717`, evolver.c) — the bound above only
holds for a SINGLE function acting alone; a cross-function mechanism
does reproduce it.** All three "not reproducible" mechanisms surveyed
above (block reorder, CloneCode, FE inline budget) are *intra-function*.
They miss `ComTail`'s own machinery operating *across* the function
boundary this document exists to analyse: when a **dependent** function
is compiled immediately after the donor (this file's emission order)
and is itself written **arms-first with its own shared call + `return;`
as the function's LAST statements**, the front end's last-statement
special case emits *that dependent's* epilogue inline right after its
own call. That gives `ComTail`/`TransformJumps` (`optcom.c`) a second
epilogue copy to work with: `ComTail(RetList)` finds a common suffix
between the donor's own (end-anchored) epilogue and the dependent's new
inline one; `JustMoveLabel` fails (the call falls through into the
label); `AddNewJump` replaces the donor's tail with a `jmp` into the
dependent's; the retry lands on that jmp, `Untangle` aliases the dead
end-of-func label away, `ComCode`/`ComTail` then finds the *real* common
tail (the shared call block) between the donor's jmp and the
dependent's return-jmp (same label after aliasing); `JustMoveLabel`
fails again, so `TransformJumps` physically **moves the dependent's
trailing epilogue block up** to sit right after the dependent's own
return-jmp — landing exactly at the donor's early-return site. This is
the "framed mid-epilogue" shape PS shows, reproduced byte-exact on
`evolve_a_building` (23b, `jmp devolve_a_building+0x11`) together with
`devolve_a_building` (154b, mid-epilogue at +0x5b) — full mechanism
replay in the `e27e4717` commit message. **The donor cannot fix
itself: the lever lives in the DEPENDENT's source shape**, not the
donor's — don't grind the donor alone; check what's emitted directly
after it in file order.

Gating requirement, from the same investigation: the dependent's
shared epilogue **tail** must be long enough to clear `ComTail`'s
`max.save > OptInsSize(OC_JMP, near)` (5-byte) admission gate. Checked
against `action.c`'s own (still open) Rule 135 residue: its file-order
neighbour `flag_mode_action` shares only a 2-byte common suffix
(`pop ebx; ret`) with `action`'s 5-callee-save epilogue — below the
gate — so `TransformJumps` never fires there, and no other corpus
function supplies a matching donor tail immediately after `action`.
Confirmed structurally blocked, not a source-lever miss.

Corpus census (2026-07-07): of the 12 members `rules_registry.py`'s
Rule 135 entry lists as "affected framed" cases, 11 are *already*
byte-exact (resolved independently, via the goto idiom, in prior
sessions) and the 12th (`figure_go_to_target`) no longer carries a
mid-epilogue-position residue at all — its remaining 12-byte diff is a
plain byte-seat CASE A tie, unrelated to Rule 135. **There are
currently zero live Rule-135 targets with a reachable dependent** —
the cross-function lever is proven and generalizable, but the corpus
has no pending case to apply it to right now.

## Addendum 2026-07-12 — action's Rule 135 CLOSED: the dependent's *merged-away tail* can hide a missing call (the act_query class)

The 2026-07-07 gating paragraph above ("no other corpus function
supplies a matching donor tail immediately after `action`") checked
only file-order **adjacency**.  Wrong frame: the OptPush dance works
from ANY later same-TU dependent whose ret is processed while the
donor's tail entries are queue-resident.

**The scan that found it** (do this FIRST for any mid-epilogue
residue): enumerate PS jmp/jcc targets landing INSIDE the donor.
For `action`: `this_region+0xc5`, `act_query+0xf`,
`act_query_do_help+0xfd` → `action+0x4a`, and `act_query`'s tail jmp
→ **`action+0x45`** — one instruction EARLIER than the epilogue.  A
merge target before the pops means the dependent's ComTail consumed
MORE than the epilogue — here `call clear_mouse` (save=11).  Our
recovered `act_query` did NOT end with `clear_mouse();` — **a real
missing call, and the byte oracle could not see it**: tail-merge
splicing + cross-function rel32 masking kept act_query "byte-exact"
while its merged-away tail silently lacked a semantic call.

With the call restored (bbcb03ec), the machinery (all from the OW
source, verified against the fw/op/cc/ctm/em trace streams):

1. act_query's OC_RET → `ComTail(RetList, ret)` splices save=6 into
   action's END epilogue (`ct` commit) → act_query tail becomes
   `[call clear_mouse][LABEL aq_end][jmp action_end]`.
2. OptPush retry (`InsDelete` loop) lands on the new jmp → `Untangle(
   PrevIns)` → UnTangle2 "jump to jump" `Redirect` aliases `aq_end`
   away (its early-return jcc re-points to action's end label).
3. `ComCode`→`ComTail(refs)` re-runs: `FindCommon` now walks past the
   call — 10-byte common tail `[call clear_mouse][jmp]` with action's
   TURBO return-jmp (labels are walk-transparent only on the
   CANDIDATE side; OC_INFO linenums on both).  `JustMoveLabel` fails
   (fall-in) → **`TransformJumps` swaps action's `[label+pops+ret]`
   block up to the turbo site (+0x4a) and the turbo jmp down to the
   end** (→ PS's `+0xb1b jmp 0x4a`), Untangle deletes it as
   jmp-to-next.  `je/jne/jmp 0x4a` all reproduce.

Load-bearing set (each ablation-verified 2026-07-12, commit 46da97e1):
act_query ends `pointer_mode = saved_pm; clear_mouse();`; action's
turbo arm keeps the two-return form (855e92c3) — the single-return
spelling leaves the arm-merge label before the return-jmp and
FindCommon stops at 5; NO zoom-arm store duplication (kills the dance
AND is Mac/Win counter-witnessed).

**Corpus scan for the class** (jmp32 into another function landing on
a `call` byte): 38 hits; spot-checks (clear_battle_gfx_buffers,
vhigh_beep, helping, act_tunes_level, floop_end) all have the
consumed calls present in the recovered source — act_query was the
outlier.  Detection recipe for future sessions: a dependent whose PS
merge target sits BEFORE the donor's pops must have its recovered
tail end with the consumed instruction(s); the byte oracle will not
flag it.

Correction to the framing of 4476fcb3 (the ctm "re-canonicalization
sweep" story): the two save=5 ctm sweeps after the end-label define
are **inert reads** — no ct/jm commit fires (5 is not > OptInsSize);
they never re-pointed anything.  The forward-funnel was simply the
FE's gen-order layout, and the fix was never intra-action.  The
`fw`/`op`/`cc`/`ctm`/`em` streams already carry per-candidate saves,
refs-chain order, and caller identity (stream adjacency) — the
"re-add ct/ctc probes" plan is obsolete.
