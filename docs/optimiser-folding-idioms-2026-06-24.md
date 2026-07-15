# Optimiser-surviving idioms — savings-bump catalogue

**Empirical catalogue** of C constructs and their measured impact on a
named value's regalloc savings under Watcom 10.0a
`-bt=dos -mf -4r -s -d1` (the PS.EXE flag set).  Reproducible via
`uv run c2 cgex run optimiser-folding-idioms`.

## Why this exists

Every HARD-bucket residue class (`savings`, `prologue`, `h2-tie`,
`byte-savings-short`, `slot-swap` — see
`docs/hard-bucket-survey-2026-06-24.md`) has a Cascade analyzer that
names a precise lever of the form:

> raise sav(X) to >= 15 → ADD ~4 straight-line uses (each +1, in-loop ×10)

But the action verb hides a search: WHICH C construct adds the
required number of uses without (a) getting folded by the optimiser,
(b) changing function semantics, (c) cascading into other diffs.
This catalogue removes the search for (a): a known-survival idiom
with a measured savings contribution.

## Empirical measurements

All measurements from `c2 cgex run optimiser-folding-idioms`
(`docs/codegen-experiments/optimiser-folding-idioms.py`).  Baseline:
`int x; x = gx; ext(0); return gy;` — x loaded but not used post-call;
x's al-record savings is `None` (never spilled).

| idiom | code bytes | x savings | category | use this when... |
|---|---:|---:|---|---|
| baseline (no use of x post-load) | 7 | — | — | (reference) |
| `(void)x;` | 7 | — | **FOLDED** | never — folded entirely |
| `t = x * 0` | 7 | — | **FOLDED** | never — folded to constant |
| `gy = gy;` (self-assign) | 7 | — | **FOLDED** | never — folded entirely |
| `if (x < 0) { gy = gy; }` (empty body) | 7 | — | **FOLDED** | never — even the `cmp/jcc` gets dropped when the body is empty |
| `gy = x;` (store to global) | 17 | **+2** | PARTIAL | need a small bump (+2) without control flow |
| `if (x < 0) return -1;` | 19 | **+2** | PARTIAL | need +2 and a guard fits the function semantically |
| `if (x > 0) gy++;` (conditional store) | 20 | **+2** | PARTIAL | need +2 with semi-meaningful condition |
| `ext(x);` (call arg) | 10 | **+3** | PARTIAL | need +3 — cheapest by-bytes; needs an existing call site |
| `gy = x; gy = x;` (repeat store) | 17 | **+3** | PARTIAL | need +3; DSE keeps both refs in IL even if 2nd store is dropped |
| `volatile int t; t = x;` | 21 | **+2** | PARTIAL | need +2 with no observable side effect; volatile defeats DSE |
| `for(i=0;i<10;i++) gz[i] = x;` (in-loop store) | 28 | **+11** | **HEAVY** | need a callee-save promotion (savings > 2 with × loop-weight 10) |
| `for(i=0;i<10;i++) if (gz[i] == x) gy++;` | 34 | **+11** | **HEAVY** | same — in-loop guard |
| `for(i=0;i<10;i++) s += gz[i] * x;` | 35 | **+11** | **HEAVY** | same — in-loop arith |

## How to use this catalogue

When a Cascade hint says **"raise sav(X) by N"**:

* **N < 2 (need +1)**: there is currently no measured idiom that
  cleanly produces a single-savings bump in isolation.  Smallest
  observed +2 idiom is `gy = x;` or a guard `if (x < 0) return;`.
  An exact +1 bump may require shifting a use that already exists
  rather than adding a new one.
* **N = 2..5**: use a PARTIAL idiom.  Cheapest in code bytes:
  `ext(x);` (+3, +3 bytes) if an existing call exists you can pass
  x to.  Next: `gy = x;` (+2, +10 bytes).
* **N >= 10**: use a HEAVY idiom.  In-loop store / guard / arith
  each give +11.  An existing loop in the function is the natural
  place to land it.
* **N is depth-0 of an in-loop value already**: nothing more to
  add; that's the natural max for in-loop uses.

When a Cascade hint says **"lower sav(X) by N"**:

* **REMOVE one of x's depth-0 uses** by caching into a hoisted
  local or by inlining: `int xc = x; ...use xc...` shifts x's
  savings to `xc`.  (worked on show_menu_items P10: y → yl
  caching dropped y's sort_sav from 13 → 4).
* **MOVE one of x's in-loop uses out of the loop** (depth-1 use
  worth ×10 → outside contributes +1).  This is the biggest
  per-edit savings drop available.

## Watcom 10.0a savings model (the math, recap)

Per `vendor/open-watcom/bld/cg/c/dataflo.c::AddTempSave` and
`bld/cg/c/regsave.c::CalcSavings`:

```
W = 10  (loop weight per nesting depth)
savings = Σ(uses + defs)·W^depth  −  Σ(spills·2)·W^depth
```

Per-conflict savings are accumulated in two passes:

1. **AddTempSave** (called in BuildNameConflicts): `conf->savings +=
   Weight(1, blk)` per IL operand referencing the conflict.  This
   is the SORT-TIME savings — what `AllocBefore` reads at the
   BuildNameConflicts SortList.  Captured in the trace as
   `nb1.sort_sav` / `nb2.sort_sav`.
2. **CalcSavings** (called in AssignConflicts, BEFORE
   GiveBestReg): full per-instruction recompute with save / cost
   units.  This is the FINAL savings.  Captured in the trace as
   `al.savings`.

The two diverge when AddTempSave's per-operand count differs from
CalcSavings' per-instruction count — e.g. for show_menu_items'
`text_group` (sort_sav=12, al_sav=24, ~2x).  This divergence is
why some HARD residue is so hard: an agent can be looking at the
`al` savings but the SORT decision was made on the (lower)
`sort_sav` value.

## Open: per-idiom savings under the sort-time model

The numbers in the table are `al.savings` (post-CalcSavings).
The SORT-TIME savings (`sort_sav` via the `nb1/nb2` deref) are
typically LOWER, sometimes by a factor of 2x.  For accurate
HARD-bucket leverage, repeat the cgex with each idiom inside a
BuildNameConflicts-fired routine and read `sort_sav` instead.
Not done here; the al-record numbers are a starting point.

## Reproducing

```sh
uv run c2 cgex run optimiser-folding-idioms
uv run c2 cgex run optimiser-folding-idioms -t in_loop_store   # asm dump
```

To add a new idiom: edit
`docs/codegen-experiments/optimiser-folding-idioms.py`, add an
`exp.add(...)` entry, re-run.

## Offline simulators (BOTH ALREADY EXIST)

The hard-bucket survey listed two as "realistic next instrumentation
steps".  Both predate this session and are working:

### CalcSavings simulator — `c2.regalloc.trace.savecalc_savings`

Feed it a conflict's `cv` (savecalc) entries + the loop base; returns
the predicted savings.  Verified exact against the live trace's `al`
savings (4/4 sampled on `get_region_over` reproduce exactly):

```python
from c2 import regalloc
from c2.regalloc.trace import savecalc_savings

td = regalloc.file_trace(Path("decomp/src/action.c"), Path("decomp/include"))
r = td["by_func"]["get_region_over"]
base = td.get("loop_base", 10)
for a in r.get("alloc", []):
    if a.get("var") == "ry":
        cv = r["savecalc"][a["conf"]]
        # Current savings
        sim = savecalc_savings(cv, base)
        # "What if I add a depth-1 use?"
        cv_plus = cv + [{"blk": 0, "save": 1, "cost": 0, "depth": 1}]
        sim_plus = savecalc_savings(cv_plus, base)
        print(f"ry sav now={sim}, after +1 depth-1 use={sim_plus}")
```

This lets an agent test "add ~2 depth-1 loop uses of `ry`" as a
savings-delta in microseconds, without recompiling.

### SortConflicts / ConfBefore simulator — `c2.regalloc.sort`

The h2-tie analog of the slot-swap ShellSort sim, already at
`c2/regalloc/sort.py`.  Algorithm exact (self-test passes); when fed a
realistic routine's `presort` it reproduces a subset of `postsort`
(the FIRST sort).  The full sort sequence diverges over RegAlloc retry
rounds (multiple sort invocations rebuild ConfList) but a single sort
is byte-exact.

```python
from c2.regalloc.sort import sort_conflicts

# Take presort (ConfList pre-sort, in list order from the `sl` stream)
# and predict the postsort = the order GiveRegister iterates
sorted_items = sort_conflicts(r["presort"],
                              savings_of=lambda c: c["savings"])
```

Use this to validate Cascade's `UNREACHABLE` verdicts for h2-tie
cases and to test "what if I bump conf X's savings by N?" as an
input-perturbation search.

### Cost model — `c2.regalloc.costs`

The full W/depth weighting model, decoded from `wcc386.exe` and
verified against the running compiler's `cost`/`lwt` records.  Use
when building a custom predictor:

```python
from c2.regalloc.costs import costs, loop_weights, weight
```

## Composing them (the missing wrapper)

The one piece NOT yet built: a `diagnose_savings_edit(routine, var,
block, depth_delta)` helper that:

1. Looks up `var`'s conflict in the routine.
2. Adds a synthetic save/use unit at the given depth.
3. Re-runs `savecalc_savings` for the perturbed conflict.
4. Re-runs `sort_conflicts` for the full ConfList with the perturbed
   savings.
5. Reports: does the perturbation flip the order of the named
   register-pair from the Cascade verdict?

This composed wrapper would let any agent test a candidate source
edit in microseconds and check the predicted register-flip BEFORE
recompiling.  All the pieces (savecalc_savings + sort_conflicts +
the trace data) are in place; the wrapper is a small future addition.
