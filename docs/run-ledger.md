# The dual `-d1` run ledger — statement-level PS-vs-RC comparison

**TL;DR.**  Every per-line diagnostic used to attribute RC instructions to
PS source lines *through the byte-diff alignment* — which drifts at every
length-changing diff, so on big functions the per-line views reported
**phantom divergences** and sent agents chasing constructs that were never
wrong.  The run ledger (`c2/runledger.py`) fixes attribution at the root:
segment **each side by its own `-d1` marks**, canonicalize every
instruction to a **register-blind, width-preserving** form, and align the
two canonical instruction **streams**.  The unmatched stretches
("islands") are exact, local, statement-level divergence reports — at any
function size.  Surfaces: `c2 ledger <fn>` (CLI), the `Run-ledger:` hint
in `decomp-verify -v`, the `ir` layer of `shape_distance`, diagnose's
`divergent source lines`, and the `lines()` tool in the `c2 decompile`
harness.

## Why the old per-line views failed beyond ~400 bytes

`_build_diff_rows` aligns PS and RC instructions by masked byte keys
(difflib).  Rows carry `ln` = the **PS** line — and RC instructions
inherit whatever PS line the alignment happened to pair them with.  On a
byte-exact function that's exact; on a diffing function every
insert/delete run shifts the pairing, so RC ops get attributed to the
wrong PS statement.  `binir-shape`, `diagnose`'s divergent-lines, and the
harness `lines()` v1 all consumed that attribution.

Worked example (`test_elastic_range`, 500 diff bytes): the old view
reported *"L359: RC has 2x branch_jmp, 3x cmp_jcc, 1x mov_mem_imm, 4x
zero_test_jcc, 5x zext_byte_load…"* and rule hints said *"Rule 152 missing
else-if ×10"* — **pure misattribution**.  The dual-marks ledger on the
same function shows the real levers:

* `loop-form` ×6 — PS's loops are **rotated** (`jmp` to a bottom test =
  the Rule 134 `for(;cond;inc)` form); ours are head-tested `while`s.
* `width`/`zext-idiom` ×26 — the `neigh_*` locals are **`char` in PS**
  (`test al,al` before widening; `movzx`/`and 0xff`/clear-first idiom
  mix) where ours are `int`.
* `slot` ×6 — `[esp+4]`↔`[esp]` spill-slot swap (Rule 107, downstream).
* `signedness` (on the sibling `set_route_elastic_range`) — `jl` vs `jb`:
  signed vs unsigned locals.

None of these was visible in the old per-line view; all of them are
named, located (dual line attribution), and family-tagged by the ledger.

## The mechanism

1. **Segment each side by its own marks.**  PS.EXE's `-d1` line table
   (symbols.json `line_numbers`) partitions PS's bytes into line runs;
   our compile's line table (`out.exe` debug dir / the scratch compile's
   marks) partitions RC's bytes.  No cross-side attribution at all.
2. **Canonicalize register-blind, width-preserving.**  Registers →
   `R8`/`R16`/`R32` placeholders (identity blinded, width kept — `test
   al,al` ≠ `test eax,eax` is the char-vs-int witness).  Branch/call
   targets → `T` (layout-positional).  Exactly the linker-fixup'd dwords
   → `G` (read the value at the fixup site, mask that constant only —
   non-fixup immediates stay visible, so consts still diff).  Mnemonics
   kept (`jl` vs `jb` = signedness).  Memory displacements kept
   (`[esp+4]` vs `[esp]` = slot layout).
3. **Align the streams** (difflib on the canonical strings).  Matched =
   same computation, possibly different registers.  Unmatched stretches =
   **islands**, each carrying its own side's exact line attribution +
   cheap family tags (`width`, `zext-idiom`, `signedness`, `loop-form`,
   `slot`, `frame`, `const`, `ops`).

### Invariants (validated)

* **byte-exact ⇒ zero islands** (soundness; checked on the byte-exact
  corpus sample + unit tests).
* **zero islands on a diffing function ⇒ pure regalloc residue.**  The
  whole diff is register seats / spill slots / encoding.  Verdict
  `regalloc_pure` — do NOT restructure the source; `c2 regtrace`.
  (map.c: `transform_wall_elastic` 190 diff bytes, `build_wall_from_elastic`,
  `build_aquaduct_from_elastic`, `build_reg_wall_from_elastic` — all
  routed straight to seat work.)
* **PS marks < RC marks** even on byte-exact functions: the original
  source systematically **packs multiple statements per physical line**
  (the `pack` verdict).  Byte-neutral; a faithfulness witness only.

## Why this is the right "inverse" of the compiler

`bytes = Backend(FE(source))` and the FE is nearly statement-local: each
statement lowers to a tree, trees emit (mostly) contiguous runs, and the
`-d1` marks record the run boundaries **in both binaries**.  Register
allocation is the one *global* pass at PS flags — and the canonical form
blinds exactly its output (seats) while keeping everything the FE and
instruction selection determine (ops, widths, signedness, immediates,
slots).  So the ledger factors the byte-exact problem:

1. **Per-island statement work** (local, small, tagged with the rule
   family) until every instruction matches register-blind;
2. **then** the residue is regalloc by construction — regtrace / the
   seat/slot machinery take over.

This decomposition is what makes >400-byte functions workable: instead of
one 500-byte diff, `test_elastic_range` is 44 islands, each a
one-statement decision, checked independently after each edit.

## Surfaces

| surface | what |
|---|---|
| `c2 ledger <fn>` | full ledger: summary, verdict, every island with real asm, dual line attribution (`PS L<n>` original witness / `map.c:<n>` edit target), our source text, family tags.  `--json`, `--limit`. |
| `c2 decomp-verify -v -f <fn>` | `Run-ledger:` hint — match count, island count, top-10 island one-liners. |
| `c2 decomp-verify --json` / verify.json | `run_ledger` per-function record (islands without insns); **the `ir` layer of `shape_distance` = divergent PS runs (+ RC-only runs) over total PS runs** when the RC line map is available (falls back to the old binir per-line count otherwise).  `shape_distance.islands` carries the island count (None = ledger unavailable). |
| every shape view | the island count rides in `shape_distance` and renders everywhere: `decomp-verify` bulk rows (`ir 19/47  isl 20  …`), `diagnose`/`dossier`/`regtrace` (`ir 19/47 (isl 20)`), `worklist`/`functions` cells (`ir19/47·i20+1→ir` — **`i0` = regalloc_pure at a glance**, don't restructure), the harness `ShapeDistance.islands`. |
| `c2 diagnose <fn>` | `divergent source lines` now island-based (attribution-exact); `run-ledger:` summary line; routed `next` step (`regalloc_pure` → regtrace, `shape_islands` → `c2 ledger`). |
| `c2 decompile` harness | `lines()` tool = the same dual-marks ledger per PS line run (schema: `LineLedgerRow` + `tags`); sandbox `shape_distance` ir layer kept in parity with the project verifier. |

## Reading an island

```
== island 7 [loop-form]  PS L341 | map.c:361
   PS L  341   bc: jmp 0x1a9            <- PS jumps to a bottom test: rotated loop
   RC L  361   b7: mov eax, [esp+8]     <- ours computes the head test inline
   RC L  361   bb: add eax, ebp
   RC L  361   bd: cmp eax, [0x2caaa]
   RC L  361   c3: jle 0x2d7
   map.c:361 | while (gmn_y < y_min + side) {
```

The PS side IS the target shape (here: rewrite as the rotated
`for ( ; cond; inc)` form — Rule 134).  Map tags to rules: `width`/
`zext-idiom` → Rules 49/49b/151 (local's type); `signedness` → signed vs
unsigned local; `loop-form` → Rules 134/93; `slot`/`frame` → Rule 107 /
local-set (work LAST — often downstream of the type fixes); `const` →
const-audit; `ops` → read PS's ops, that is the statement to write.

## Limitations / cautions

* **Islands are not independent proofs** — a type fix usually collapses
  several islands at once (the `neigh_*` char fix removes all the
  zext-idiom islands).  Re-run after each edit; work top-down.
* **Register-blind ≠ semantics-blind**: a same-shape-different-target
  branch matches (`jmp T`).  Block-ORDER divergence shows up as displaced
  islands, not as branch-target diffs.
* The RC side needs `-d1` in the compile (default in `PS_CFLAGS`; the
  ledger degrades to the old binir path without it).
* Tail-merge donor tails are excluded in the harness (`D+N` rows); the
  CLI slices by symbol bounds and may show a small trailing island for a
  donor jmp vs inline epilogue — the `Tail-merge:` verify hint is the
  authority there.
* The `shape_distance.ir` unit changed from "binir-divergent aligned
  lines" to "divergent PS runs" — same fix-order semantics, better
  grounding; whole-corpus numbers shift accordingly on the next
  verify.json refresh.

## Files

| file | what |
|---|---|
| `c2/runledger.py` | the core: canonicalization, stream building, alignment, islands, tags |
| `c2/commands/ledger.py` | `c2 ledger` CLI (`ledger_data()` reusable core) |
| `c2/commands/decomp_verify.py` | `_run_ledger_for` / `_render_run_ledger` / `_recon_bundle_for_json(recomp_line_map=…)` |
| `c2/toolapi.py` | `run_ledger` headline + island-based `_divergent_lines` |
| `c2/commands/diagnose.py` | run-ledger routing + rendering |
| `c2/decompile/_engine/verify.py` | harness `_line_ledger` v2 + shape parity |
| `tests/test_runledger.py` | canonicalization + soundness + tag unit tests |
