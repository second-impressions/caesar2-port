# Forge changes that landed in commit `a8b72d8d` (2026-06-27)

The parallel session's commit `a8b72d8d` ("battle.c: setup_enemy_units
-- firstassign reorder ...") accidentally bundled in a substantial
forge improvement alongside its one-byte battle.c edit.  This file
records what actually landed so the changelog is searchable.

## #1 — LE-mode wlink (`c2/forge/build.py`)

`ForgeBuilder` gained a `mode` parameter; default is `"le"`.

* **`mode="le"`** (default).  After `wcc386` compiles the target TU
  into `target.obj`, forge runs `wlink @forge.lnk` against every
  OTHER project .obj (staged at builder warm-up time from
  `.c2-cache/build/`) plus clib3r.lib.  The function's bytes are
  carved from the resulting LE binary, with offsets resolved via the
  linker's .map file.  **byte_diff matches `c2 decomp-verify`
  exactly** -- the OMF-vs-LE fixup-set asymmetry that previously
  inflated counts by 5-15% on large functions is gone.

* **`mode="omf"`** keeps the old fast path: compile-only, carve from
  the pre-link .obj.  ~30% faster per variant (no link step) but
  over-counts byte_diff on large functions.  Use for tight feedback
  loops where relative ranking matters more than absolute counts.

* Requirement: `.c2-cache/build/` must be populated by at least one
  prior `c2 decomp-verify` run.  The builder hard-links the friend
  .objs into the worker's scratch tree (free, no copy cost) and
  writes the linker script once.

* Measured: ~120 ms per variant total (compile + link + carve) on
  warm container, vs ~80 ms in OMF mode -- net ~30 ms / variant cost
  for verifier-exact byte counts.  Verified bytes-match on `action`
  (1481 / 1481), `place2_sprite` (1946 / 1946), `get_query_info`
  (961 / 961), `test_reform_pattern` (10 / 10).

Companion fix in `c2/forge/judge.py`: `score()` now truncates the
RC byte slice to `len(ps.bytes_)` before passing to `_compare_bytes`,
matching the verifier's "audit at PS's func_size" convention.  The
6-byte gap on action (1475 vs 1481) was from inter-function linker
padding the verifier sees but a strict next-symbol-offset carve
misses; the truncate-to-PS fix recovers it.

## #2 — High-impact targeted DSL verbs (`c2/forge/experiment.py`)

Five new DSL methods, each one a one-line targeted hypothesis:

* **`add_else_if(else_line=, condition=)`** -- Rule 152, the largest
  single residue class at corpus scale (59% of remaining diff bytes
  per `decomp/AGENTS.md`).  Converts `else { ... }` ->
  `else if (cond) { ... }`.  Guards against the "already-`else if`"
  case to prevent nonsensical `else if (X) if (Y)` nesting.

* **`de_invent(var_name)`** -- Rule 67 / §10 de-invent lever.  Deletes
  `T name = E;` and inlines `(E)` at every read of `name`.
  Conservative: refuses if the var is reassigned later (would change
  semantics).

* **`cache_global(global_name, type_, *, before_line=, cache_name=)`**
  -- Rule 116 cache-introduction lever.  Inserts `T c_X = X;` at the
  top-of-decl-run (C89-safe placement) and rewrites every downstream
  READ of `X` to `c_X`.  Skips lvalues, struct-field references, and
  function callees.

* **`move_statement(from_line=, to_line=)`** -- non-adjacent statement
  move (use `swap_statements` for neighbour swaps).

* **`split_expr(at_line=, expr_text=, into_var=, type_=)`** -- extract
  a sub-expression into a fresh local, e.g. `f(a, b+c)` ->
  `int t = b+c; f(a, t)`.

## #3 — `SourceIndex` robustness (`c2/forge/source_index.py`)

* **Pointer types** (`int *x`) now correctly preserve the type span
  ("int") and record the `*` count in `DeclInfo.ptr_stars`.

* **Grouped declarations** (`int x, y, z;`) -- each name gets its own
  DeclInfo with a precise `name_range`; `is_grouped=True` flag.

* **Multi-line declarations** -- `full_range` now walks forward to
  the terminating `;`, comment-aware (skips `//` and `/* */` and
  string/char literals so a stray `;` doesn't fool us).

* **Complex declarators** (struct/union/enum-defining decls, function
  pointers) -- explicitly skipped with a recorded warning rather
  than indexed with a wrong span.

* **Binop locator** now also retries with the source's literal parens
  wrapped around either operand, fixing the `(a+b)&c` vs CGenerator's
  `a+b&c` case.

* **Diagnostic surface** -- `SourceIndex.warnings` is a list of
  `(kind, detail)` tuples.  Targeted DSL methods that need a missing
  site raise `KeyError` with a hint to inspect warnings; bulk presets
  emit fewer candidates and warnings explain why.  Eliminates the
  "silent skip → mysterious missing candidate" failure mode.

## Tests

`tests/test_forge.py` grew from 11 to 16 tests covering:
- TextEdit overlap detection
- EditPlan reverse-offset application
- SourceIndex pointer-decl detection
- SourceIndex warning surface
- `cache_global` produces insert + N rewrites
- `add_else_if` rejects already-`else if`
- `move_statement` produces a delete + insert pair

All 16 pass; broader suite is 1116/1119 (3 skipped, no regressions).
