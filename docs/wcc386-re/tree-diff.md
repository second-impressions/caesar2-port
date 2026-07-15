# `c2 tree-diff` — forward vs reverse IR tree comparison

End-to-end:

```
PS.EXE asm  --binir.recover-->  RecoveredOp[]  --shape_from_binir_ops-->  TreeShape  ╮
                                                                                       ├── tree_diff
decomp.c   --wcc386 -trace-->   IRForest        --shape_from_ir_forest-->  TreeShape  ╯
```

The **forward** tree is what wcc386 actually built for *our* decomp source
(captured by the instrumented compiler via the `~WV1` `tn/tl/tb/nb/ni`
records — see [`regalloc-trace-image.md`](regalloc-trace-image.md)).

The **reverse** tree is what we can *recover* from PS.EXE's compiled asm
by matching known x86 idioms back to their cg_op tree shapes (see
[`c2/binir.py`](../../c2/binir.py)).

The **diff** reports structural differences (`op_mismatch`,
`children_mismatch`, `only_in_a` for forward-only nodes, `only_in_b` for
reverse-only ones).  `only_in_a` (forward-only) diffs are usually the
most actionable — they show **intermediate constructs PS's source didn't
have** that ours does (extra `s` temp, redundant store, unrolled compute,
etc.).

## Usage

```bash
# basic diff
uv run c2 tree-diff get_region_2x2_start

# disambiguate a duplicated function name
uv run c2 tree-diff market_image --file evolver.c

# dump the full trees (forward + reverse) alongside the diff
uv run c2 tree-diff move_army --raw

# truncate tree depth (default 6)
uv run c2 tree-diff some_big_function --raw --max-depth 4
```

## Output sections

1. **header** — source TU, forward-root count, PS asm size, binir-recovered
   pattern count (a quick sanity-check that both sides have data)
2. **FORWARD** (with `--raw`) — full per-statement tree dump from the trace
3. **REVERSE** (with `--raw`) — per-pattern tree dump from PS asm
4. **DIFFS** — structural differences with kind counts + dotted-index paths

Diff kinds:
- `op_mismatch` — same position, different ops (e.g. forward `ASSIGN`,
  reverse `PRE_GETS` → PS used a different optab row)
- `children_mismatch` — same op, different child counts
- `only_in_a` — node in forward, no counterpart in reverse (forward-only
  intermediate)
- `only_in_b` — node in reverse, no counterpart in forward (binir saw
  something the forward trace didn't expose; usually a binir pattern that
  collapses multiple IR nodes into one tree shape)

## When the diffs are noisy

Today the alignment is purely positional (forward[i] vs reverse[i]).
The reverse side is **partial**: it only covers the asm patterns
`c2.binir` recognises.  Two practical implications:

- **Reverse side has fewer roots than forward** — most statements have no
  binir match yet, so they're "missing" on the reverse side.  This is
  expected; expand the binir catalog to close the gap.
- **Diff alignment is approximate** — when forward and reverse have
  different root counts the index-based pairing aligns *different*
  statements.  Look at the asm offsets in the `--raw` dump to align
  manually.  A smarter alignment (e.g. by source line) is a future
  iteration.

## The actionable workflow

When `c2 decomp-verify -f FUNC -v` shows a non-trivial byte diff:

1. Look at **`regalloc by source line`** — which lines created which
   conflicts.  Spilled values?  Anonymous temps where you didn't expect
   them?
2. Look at **`binary-IR signatures`** — do PS and RC share the same
   pattern histogram?  Divergences here are the signature of a codegen
   choice divergence (Rule 5/5c, Rule 17/17b, etc.).
3. Run `c2 tree-diff FUNC` — get the structural diff.  Focus on
   `only_in_a` diffs: those are the intermediate constructs ours has that
   PS's didn't.
4. Identify the source-level lever (e.g. remove a `s` temp, swap
   declaration order, combine a split RMW).  Apply.
5. Re-verify with `c2 decomp-verify -f FUNC`.  Iterate.

## Extending the reverse side

Adding a new tree shape (so the reverse path can recover it from asm):

1. **Add the asm matcher** in `c2/binir.py` — a `_detect_*` function that
   returns a `RecoveredOp` for a recognised idiom.  Register it in `_PASS2`
   (the greedy walker) or in `recover()`'s first pass for global ones
   (like `r5c_idiv_pair`).
2. **Add the converter case** in
   [`c2/tree_diff.py::_binir_op_to_shape`](../../c2/tree_diff.py) mapping
   the new kind to a `TreeShape`.  Re-use existing `op` strings (e.g.
   `"BINARY:O_AND"`) so the shape compares structurally to the forward
   side's output.
3. **Update `c2/tree_diff.py::_ir_op_name`** if the forward path's
   `c2.ir.Node` needs a new mapping (rare — most ops already have an
   `_CG_OP_NAMES` entry).
4. **Write a unit test** in `tests/test_tree_diff.py` asserting
   `shape_from_binir_ops([new_op])` produces the expected `TreeShape`.
5. **Write an end-to-end test** in `tests/test_binir.py` (or a new one)
   that disassembles a small forged asm sequence, runs binir, runs
   `shape_from_binir_ops`, and compares against the forward tree (built
   via `shape_from_ir_forest` on a parsed `.c` source compiled with the
   trace image).  When they match the shape is round-trip-proven.

## Adding a new SOURCE-pattern detector (Rule N)

When a new RE finding identifies a source-level lever that maps to a
specific IR-tree shape:

1. Subclass `c2.commands.rule_pattern_scan.SourcePatternDetector`
2. Decorate with `@register`
3. Implement `find_in_funcdef(funcdef, fn_name)` — yield
   `Candidate(rule_id, func, file, line, description, detail)`
4. Optional: implement `predict_ir(candidate)` to return one or more
   `TreePattern`s — the base class will verify them against the trace IR
   forest for any candidate's function

Example skeleton:

```python
from c2.commands.rule_pattern_scan import (
    Candidate, SourcePatternDetector, TreePattern, register,
)
from c2.ir import TN_ASSIGN, TN_BINARY

@register
class RuleNDetector(SourcePatternDetector):
    rule_id = "N"
    title = "One-line description of the source-level pattern"

    def find_in_funcdef(self, funcdef, fn_name):
        # walk the AST, yield Candidate(...) for each match
        ...

    def predict_ir(self, candidate):
        # what tree shape(s) the compiler should produce for this pattern
        return [TreePattern(cls=TN_ASSIGN, right=TreePattern(cls=TN_BINARY, op=9))]
```

Once registered, the new rule is automatically picked up by:

- `c2.commands.rule_pattern_scan.scan_corpus()` — corpus-wide AST scan
- `c2.commands.rule_pattern_scan.verify_corpus_predictions(trace)` — IR
  cross-check against an actual compile trace
- `tests/test_rule_pattern_scan.py` patterns (add a guard test asserting
  zero candidates if the rule's hint is "remove this construct")

## Files / API surface (for further work)

| File | What's there |
|------|-------------|
| `c2/binir.py` | `recover(insns)`, `summarize(ops)`, `render_listing(insns)` — asm-pattern catalog + listing |
| `c2/ir.py` | `IRForest`, `Node`, `Name`, `build_forest(records)` — forward IR forest from `~WV1` records |
| `c2/tree_diff.py` | `TreeShape`, `shape_from_ir_forest`, `shape_from_binir_ops`, `tree_diff`, `trees_match`, `diff_function` |
| `c2/commands/tree_diff_cmd.py` | The `c2 tree-diff` CLI |
| `c2/commands/rule_pattern_scan.py` | `SourcePatternDetector`, `Candidate`, `TreePattern`, `register`, `scan_corpus`, `verify_corpus_predictions` |
| `c2/commands/rules_registry.py` | `RuleVerdict` registry (the human-readable rule index) |
| `tests/test_tree_diff.py` | 14 unit tests covering tree shapes + diff |
| `tests/test_binir.py` | binir pattern unit tests |
| `tests/test_rule_pattern_scan.py` | source-pattern AST detector + corpus guard tests |

## Cross-references

- [`regalloc-trace-image.md`](regalloc-trace-image.md) — the
  instrumented compiler image that produces the `~WV1` trace
- [`regalloc-model.md`](regalloc-model.md) — model of layers 0–6 of
  divergence (per-line view, regalloc decisions, rule hints)
- [`wcc386-10.0a-regalloc-symbols.md`](wcc386-10.0a-regalloc-symbols.md) —
  the RE'd 10.0a-binary VAs and their OW v1 source cites
- `knowledge/wcc386_regalloc.py` (in the watcom10.0a repo) — the
  authoritative VA + struct-offset table that drives Ghidra annotation

## Future: line-cue-paired tree matching

Forward IR nodes carry source lines (tn/ni records); reverse (binir) ops
can be tagged with PS lines from the debug-info line map.  Pairing
subtrees by RELATIVE line offset (L+N within the function) would let
`tree-diff` report *per-statement* structural deltas — "forward has an
extra ASSIGN chain at L+12 that PS's L+12 lacks" — instead of
whole-function set differences.  The `line-shape` decomp-verify hint
(statement-boundary positions) is the coarse version of this; the
fine-grained pairing is the natural next step.  PS line GAPS (delta > 1
between consecutive cues) additionally mark blank/comment lines in the
ORIGINAL source — useful for source-layout reconstruction even on
byte-exact functions.
