# Extending `binir` and `tree-diff` — a tactical guide

This is the **playbook for adding a new tree-shape pattern** end-to-end.
Use it when a new RE finding (a new x86 idiom mapped to a specific cg_op
tree shape) needs to land in the triangulation tooling.

## The pieces

```
        ┌─────────────────────┐         ┌──────────────────────┐
PS.EXE  │ c2.binir.recover    │  ops    │ c2.tree_diff.        │  reverse TreeShape
asm  ─► │ (asm patterns)      ├────────►│ shape_from_binir_ops ├──────────────────────┐
        └─────────────────────┘         └──────────────────────┘                       │
                                                                                        ├── c2.tree_diff
                                                                                        │   .tree_diff
        ┌─────────────────────┐         ┌──────────────────────┐                       │
~WV1    │ c2.regalloc.trace   │  IRForest│ c2.tree_diff.        │  forward TreeShape   │
trace ► │ .parse              ├────────►│ shape_from_ir_forest ├──────────────────────┘
        └─────────────────────┘         └──────────────────────┘
```

Adding a new construct touches up to 3 files:
1. `c2/binir.py` — the new asm-pattern matcher
2. `c2/tree_diff.py` — the converter from the binir kind to a `TreeShape`
3. `c2/commands/rule_pattern_scan.py` — the source-level `Rule` detector
   (if there's a corresponding source-shape lever)

## Step 1: add the asm-pattern matcher (`c2/binir.py`)

A pattern detector is a function `_detect_NAME(i, insns) -> RecoveredOp | None`.
It returns a `RecoveredOp` for a recognised idiom or `None` to keep walking.

```python
def _detect_my_new_idiom(i: int, insns: list[InsnT]) -> Optional[RecoveredOp]:
    """ASM pattern: <describe the bytes you're matching>.
    
    Maps to: <cg_op tree shape this PS source idiom produces>.
    """
    # Window check (have enough instructions left)
    if i + N >= len(insns):
        return None
    # Pattern matching with the existing helpers:
    #   _mnem(insns[i]) == "mov" etc.
    #   _ops(insns[i]) -> ["dst", "src", ...]
    #   _imm(s) -> int or None
    #   _is_idiv(...), _is_mov_imm(...), _is_xor_self(...), etc.
    #
    # Example: match `mov reg, imm; lea dst, [reg + reg*2]`
    mv = _is_mov_imm(insns[i])
    if mv is None: return None
    # ... continue matching ...
    
    return RecoveredOp(
        kind="my_new_idiom",           # short id used in summarize() output
        offset=insns[i][0],
        length=insns[i + 2][0] + insns[i + 2][1] - insns[i][0],
        detail={"reg": mv[0], "value": mv[1], ...},
        op="OP_<CG_OP_NAME>(<args>)",  # human-readable
        note="<source-level implication or compiler-mechanism explanation>",
    )
```

Register it in `_PASS2` (the greedy sequential walker) at the right
priority order.  **Longer / more-specific windows go FIRST** — the walker
takes the first match and advances past it.

If your pattern is **global** (spans the whole function, can't be
greedy-matched at one offset — like `r5c_idiv_pair`), call your detector
explicitly in `recover()` outside the `_PASS2` loop instead.

**Tests**: add to `tests/test_binir.py`.  Both:
- positive: a small forged InsnT list that should produce the new op
- negative: similar shapes that should NOT match (different reg, etc.)

## Step 2: add the tree converter (`c2/tree_diff.py`)

In `_binir_op_to_shape`, add a case for the new `kind`:

```python
if kind == "my_new_idiom":
    return TreeShape(
        op="BINARY:O_<CG_OP>",        # use existing _CG_OP_NAMES
        children=[
            TreeShape(op="LEAF:?", origin="reverse"),
            TreeShape(op="LEAF:CONSTANT",
                      detail={"value": op.detail["value"]},
                      origin="reverse"),
        ],
        detail={"offset": op.offset, **op.detail},
        origin="reverse",
    )
```

**Naming convention** (so forward and reverse TreeShapes compare):
- Interior nodes: `"BINARY:O_<NAME>"`, `"UNARY:O_<NAME>"`, `"ASSIGN"`,
  `"COMPARE:<CMP_OP>"`, `"PRE_GETS"`, `"SIDE_EFFECT"`, etc.
- Leaves: `"LEAF:<NAME_CLASS>"` (e.g. `"LEAF:MEMORY"`, `"LEAF:CONSTANT"`,
  `"LEAF:TEMP"`, `"LEAF:REGISTER"`), or `"LEAF:?"` when the underlying
  name class can't be inferred from asm alone.

**The forward side** (`_ir_op_name` in the same file) already produces
strings in this format from `c2.ir.Node` — use the same opcode names so
diffs are clean.

If you need a new `cg_op` name not in `_CG_OP_NAMES`, add it.  See
`bld/cg/h/cgdefs.h` in `owp4v1copy` for the canonical enum.

**Tests**: add to `tests/test_tree_diff.py`.  Most useful:
- `test_shape_from_binir_<kind>` — a single forged `RecoveredOp` → expected
  `TreeShape`.
- A round-trip test: forge a small `.c`, compile with the trace image,
  get the forward `TreeShape`, also build the reverse `TreeShape` from
  the recompiled bytes via binir, assert `trees_match(fwd, rev)`.

## Step 3 (optional): add the source-level rule detector

If the new construct comes with a source-shape lever (`use Y not X to get
this codegen`), register a `SourcePatternDetector` for it:

```python
# in c2/commands/rule_pattern_scan.py

@register
class RuleNDetector(SourcePatternDetector):
    rule_id = "N"
    title = "..."

    def find_in_funcdef(self, funcdef, fn_name):
        # walk the AST with pycparser.c_ast.NodeVisitor; yield Candidate(...)
        ...

    def predict_ir(self, candidate):
        # what tree shape(s) the compiler should produce for this pattern
        return [TreePattern(cls=TN_BINARY, op=O_<...>, ...)]
```

Also add a `RuleVerdict` entry in `c2/commands/rules_registry.py` so the
rule appears in `decomp-verify -v` output with the actionable hint + the
OW v1 / 10.0a binary mechanism cites.

If the rule's hint is "remove this construct" (like Rule 17b), add a
corpus-wide guard test in `tests/test_rule_pattern_scan.py`:

```python
def test_rule_N_pattern_stays_gone_corpus_wide():
    cands = scan_corpus(rule_ids=["N"]).get("N", [])
    if cands:
        pytest.fail(f"{len(cands)} candidates: " + ...)
```

## Quick reference: existing patterns and their tree shapes

| binir kind | TreeShape `op` | cg_op | source lever |
|---|---|---|---|
| `r5c_idiv_pair` | `SIDE_EFFECT` wrapping `BINARY:O_MOD` + `BINARY:O_DIV` | OP_MOD + OP_DIV | Rule 5c — keep `/N` `%N` of SAME literal in source order |
| `g_pow2div` | `BINARY:O_DIV` with const `2^N` | OP_DIV | Rule 5 — write `x / 2^N` |
| `g_div2` | `BINARY:O_DIV` with const `2` | OP_DIV | Rule 5 — write `x / 2` |
| `zext_byte_load` | `UNARY:O_CONVERT` over `LEAF:MEMORY` | OP_CONVERT | Rule 49 — `unsigned char` byte fetch |
| `zext_load_byte` etc. | `UNARY:O_CONVERT` over `LEAF:MEMORY` | OP_CONVERT | explicit movzx/movsx |
| `mul_pow2` | `BINARY:O_TIMES` with const `2^N` | OP_TIMES | `x * 2^N` direct |
| `mul_const_minus_one` | `BINARY:O_TIMES` with const `(2^N - 1)` | OP_TIMES | `x * 15`, `x * 31`, ... |
| `mul_const_plus_one` | `BINARY:O_TIMES` with const `(2^N + 1)` | OP_TIMES | `x * 3`, `x * 5`, `x * 9` |
| `mul_lea_scaled_self` | `BINARY:O_TIMES` with const `(K+1)` | OP_TIMES | lea form, K in {1,2,4,8} |
| `mul_lea_scaled` | `BINARY:O_TIMES` with const `K` | OP_TIMES | lea form, K in {2,4,8} |
| `cmp_jcc` | `COMPARE:CMP_<cond>` | OP_CMP_* | `if (var <cond> CONST)` |
| `zero_test_jcc` | `COMPARE:CMP_<cond>` | OP_CMP_* | `if (var)` / `if (!var)` |

## Priority candidates to add next (high-value)

These are common idioms not yet covered.  Each is a 1-2 hour task:

1. **`pre_gets_and_mem_const`** — `and byte ptr [m], imm` (in-place AND with
   constant on memory).  Maps to `PRE_GETS:O_AND` in TreeShape.  Source
   shape: `X &= MASK;`.  Without this, the forward side shows `PRE_GETS`
   but the reverse side has nothing — diff is just `only_in_a` chatter.
2. **`pre_gets_or_mem_const`** — same for OR.
3. **`mov_mem_imm`** — `mov dword ptr [m], IMM` (store constant to memory).
   Maps to `ASSIGN(LEAF:MEMORY, LEAF:CONSTANT)`.  Extremely common; would
   collapse many `only_in_a` diffs.
4. **`call_with_args`** — `push args; call FN; add esp, N` sequence.  Maps
   to `CALL` interior with `PARM` children.  Lets `tree-diff` align calls
   between PS and RC.
5. **`branch_simple`** — `jmp imm32` / `je`/`jne` etc. without a preceding
   `cmp` (an unconditional branch or a branch after an arithmetic flag set).

For each: write the asm matcher in binir + the converter in tree_diff +
tests on both sides.  See the existing `mul_*` family for the template.

## Round-trip verification (the GOAL)

Once binir's catalog is rich enough, this should work for at least a
handful of byte-exact functions:

```python
from c2 import binir, regalloc
from c2.commands.decomp_verify import _disasm_for_diff
from c2.tree_diff import shape_from_binir_ops, shape_from_ir_forest, trees_match

# Forward: compile + capture trace
td = regalloc.trace_compile({"f.c": SOURCE}, main="f.c")
forest = td["by_func"]["my_func"]["ir"]
forward = shape_from_ir_forest(forest)

# Reverse: same binary, disassemble + recover
ops = binir.recover(_disasm_for_diff(BYTES))
reverse = shape_from_binir_ops(ops)

assert all(trees_match(f, r) for f, r in zip(forward, reverse))
```

When this passes for a byte-exact function, the reverse path has full
coverage for that function's IR shapes.  When it fails for a NON-byte-
exact function, the diff *is* the source-shape lever to investigate.
