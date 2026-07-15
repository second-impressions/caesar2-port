# `c2 forge` — the automatic per-function source-shape solver

**Authoritative user guide**: `.pi/skills/forge/SKILL.md` (loaded
automatically by pi when you're doing forge work).

This doc is the high-level **design notes + architecture overview**.

## What forge is for

`c2 forge solve <fn>` is the automated version of the per-function
workflow loop: it beam-searches the function's source with the full
lever battery (every lever a mirror of a named byte-exact win), judges
each variant with the verifier's own layered `shape_distance`, keeps
what moves toward PS, and records the entire search tree so every
branch's diff is reconstructable afterwards without recompiling.

Validation (2026-07-05): given `setup_roman_units` reverted to its
pre-win shape (ir 24, 605 diff bytes), `c2 forge solve` re-derived the
full human solution — type widths, decl order, 4× condition inversion,
4× if-fission — reaching **byte-exact in 8 rounds / ~4 minutes** on a
warm pool.

## Design invariants (load-bearing)

1. **Text-preserving edits.**  Every lever produces `TextEdit`s (char
   ranges + replacement strings) directly against the raw source.  No
   generator round-trip anywhere — comments, indentation, brace style,
   the project's `observed-source-style.md` conventions all survive.
2. **tree-sitter spans, no regex.**  Site discovery AND byte-span
   extraction run on the tree-sitter-c AST of the RAW file
   (`c2/forge/cspan.py`).  pycparser is gone from forge: it parses a
   preprocessed shadow (columns drift on commented lines, no node end
   positions), which is what forced the old generation of levers into
   fragile regex scans.  The parse buffer is an ASCII shadow (1 byte
   per char) so tree-sitter's byte offsets ARE char offsets into the
   real text.
3. **Levers mirror real wins.**  Each preset docstring cites the
   byte-exact commit(s) it was distilled from.  When a hand session
   closes a function with a transform forge lacks, the transform
   becomes a lever (that is how `if_invert`, `if_fission`,
   `guard_const`, `rmw_split`, `cache_field`, `bool_return`,
   `cast_drop`, `decl_perm`, `line_split`/`line_join` got here).
   Two levers are deliberate hypothesis SWEEPS rather than win
   mirrors: `type_sweep` (every native-integer local x every other
   native integer type — width/sign-AGNOSTIC, because a wrong declared
   type is one of the commonest shape defects and a byte-neutral
   register-class flip is a proven seat perturbation) and `cast_sweep`
   (explicit `(T)` casts on variables, computation results and
   comparison operands — the lever that can surface a wrong GLOBAL /
   struct-field type, which no local-decl sweep can reach).
4. **Verifier-accurate scoring, no parallel implementation.**  Byte
   count via the verifier's `_compare_bytes`; the layer vector via
   `_recon_bundle_for_json`; the ir layer via the dual-marks run
   ledger.  The numbers forge prints are the numbers `decomp-verify`
   prints.
5. **Fast cycles.**  Each worker owns one container whose MAIN
   process is a persistent ``/bin/sh`` on a pipe (``podman run -i
   --rm``): compiles are pipe writes + sentinel reads, never fresh
   ``podman exec`` calls (the exec path cost 220-1700 ms/variant
   under parallel load; the wcc386 compile itself is 46-88 ms).
   Measured: ~90 ms/variant end-to-end single-worker, ~58 variants/s
   sustained on 12 workers.  One shared pool across all beam rounds;
   the variant caps (25k) are runaway brakes, ``--budget`` (wall
   seconds) is the honest cost knob.  Container lifetime is tied to
   the pipe: parent death (any signal) => EOF => sh exits => ``--rm``
   removes it -- no orphan containers by construction; stuck
   compilers are killed by an in-container ``timeout`` (rc=124)
   without losing the shell.
6. **Nothing evaporates.**  Every scored permutation (edits + judges)
   and every climb tree node is persisted under
   `.c2-cache/forge-runs/<fn>/<ts>-<kind>/`; diffs are reconstructed
   offline from `baseline.c` + stored edits.

## The judge: DecisionMatrix

`c2/forge/matrix.py`.  Primary acceptance is the FIX-ORDER layer
vector `(ir, islands, width, spill, seat)` compared lexicographically
with bytes as the tie-break — the honest judge per AGENTS.md.  The
`lex+weighted` policy (solve's default) adds a composite fallback for
byte-plateaus, under hard guards: **ir/islands may never regress**,
and a `type(...)` edit may never regress width (the 2026-07-03
metric-gaming defence).  `pareto()` surfaces the mutually-incomparable
trade-offs — "the different wins".

**The bridge tier** (`bridge_accepts` / `bridge_rank_key`) is a third,
looser acceptance used ONLY to widen the SEARCH.  Both guards above
mean lex and weighted can never climb OUT of a wall-locked local
minimum — one where every deep-residue (seat/spill/width) reduction
costs a shallow (ir/islands/bytes) regression first.  `bridge_accepts`
accepts exactly that trade — a BOUNDED shallow regression
(`ir_budget` / `isl_budget`; bytes unbounded) that BUYS a strict gain
in a layer DEEPER than the shallowest regressed one ("pay shallow, buy
deep") — and `bridge_rank_key` ranks bridges to clear the deepest
residue first (seat, then spill, width) so the beam lands in the
lowest-deep-residue (ideally seat=0) launch basin.  Motivating case:
`city_test_for_road`'s 6-byte seat tie, whose only seat=0 basins are a
register-class type flip costing ir+islands+hundreds of bytes.  It
never changes what is KEPT (see the climb section).

## The search: beam climb

`c2/forge/experiment.py::climb`.  Rounds of full-battery singles over
up to `--beam` DISTINCT states (family-diverse selection, so round 1
already branches into alternative trees instead of following only the
best step).  Singles are NEVER truncated (the cap is floored at the
battery size) -- every lever is reliably tried at every state.  On
stall the escalation runs RANKED pairs: the state's own singles
results seed the pair space (failed singles excluded, no single
re-run), enumerated best-first by summed singles rank with a
coverage sweep guaranteeing every ok single appears in a few pairs
-- so a capped pass explores the most promising slice of a 100k+
pair space instead of a lexicographic prefix.  When pairs ALSO stall,
RANKED TRIPLES fire: the top ok pairs of the pairs pass, each
extended with ranked ok singles, walked anti-diagonally (pair_rank +
single_rank) -- the tier that catches three simultaneously-needed
edits invisible to singles and pairs alike (blind C(574,3) would be
31M plans; seeded it is a best-first 25k).  Then one weighted plateau
step.  Finally, when the whole lex ladder WALL-LOCKS (no lex
single/pair/triple), the round admits **basin-hop BRIDGES**
(`--bridge`, on by default): a bounded ir/islands/bytes regression
that buys a deeper seat/spill/width gain, ranked deepest-residue-first,
capped by `--max-bridges` / `--bridge-ir` / `--bridge-isl`.  Two
guarantees make the basin actually explorable:

* **admission** — on a stalled round the best-ranked bridge is ALWAYS
  taken (extending the beam by one when the weighted byte-chasers
  filled it, additionally filling any empty slots).  It never
  displaces a normal branch, and a normal branch can never starve it.
* **the full ladder** — the pairs/triples escalation rotates over the
  states not yet escalated, BASIN STATES FIRST.  A basin state is
  lex-worse than the main lane by construction and the beam is
  replaced by children every round, so without this priority it would
  die after one singles pass — never seeing the pair/triple tiers a
  basin descent needs (the whole point of paying the bridge toll).
  Displaced un-escalated states park in a LADDER QUEUE and stay
  escalation-eligible.
* **signature dedup + reservoir** — a bridge `(plan, layers, bytes)`
  signature is admitted once per run (byte-neutral variant states
  re-offer the same hop with a fresh fingerprint forever — the
  2026-07-06 cycle burned all 8 hops on 4 repetitions of 2 plans),
  and every discovered bridge lives in a persistent reservoir, so
  when a basin dead-ends the search falls back to the next-ranked hop
  even though its parent state left the beam long ago.
* **hold-the-gain** — children of a basin lineage may not regress the
  deep layers the bridge bought (a `lex` step giving the seat back is
  just walking back over the bridge); byte-exact bypasses the hold.

The ir/isl budgets default to ADAPTIVE values scaled by function size
(`max(12, ir_total//6)` / `max(16, ir_total//4)`) — a register-class
flip in a 2 kB function legitimately moves far more islands than in a
60-byte one.  Deep-gain candidates BEYOND the budget are never silently
dropped: the climb WARNS live (plan name + the `--bridge-ir/--bridge-isl`
values that would admit them) and lists them in the report + runstore
(`bridge_overbudget`), as does exhausting `--max-bridges`.  Stop at
byte-exact / no-improver / round cap / `--budget`.  Only a LEX
improvement (or byte-exact) is kept at the end — weighted AND bridge
steps are bridges, never destinations, so a basin-hop that leads
nowhere is explored then restored.  A single shared warm pool serves
every round.

## Module map

```
c2/forge/__init__.py     lazy public API: Forge, TextEdit, DecisionMatrix, RunStore, ...
c2/forge/cspan.py        tree-sitter span index (FnSpan): the ONLY C parser in forge
c2/forge/edits.py        TextEdit / Candidate / EditPlan + overlap rules + apply
c2/forge/presets.py      the lever battery (site discovery on FnSpan; win-mirror levers)
c2/forge/experiment.py   Forge (targeted DSL + cartesian run) + climb (beam search)
c2/forge/matrix.py       DecisionMatrix (lex / lex+weighted) + pareto_front
c2/forge/runstore.py     persistent run artifacts + offline diff reconstruction
c2/forge/judge.py        score() -- bytes + layered shape via the verifier's own code
c2/forge/build.py        ForgeBuilder -- warm container + wcc386 single-TU compile
c2/forge/pool.py         ForgePool -- N worker subprocesses, JSON-lines RPC
c2/forge/worker.py       worker subprocess entry
c2/forge/ps_ref.py       PS bytes / fixups / -d1 line-map loader (lru-cached)
c2/forge/objcarve.py     OMF .obj -> function bytes + fixup mask
c2/commands/forge.py     CLI: solve / report / diff / exp / levers
```

## CLI reference

```
c2 forge solve [FN|FILE.c ...]   # THE default: beam-search, keep wins, record tree
c2 forge report [RUN]            # list runs / inspect one (tree, winners, pareto)
c2 forge diff RUN ITEM [--step]  # reconstruct any permutation's diff offline
c2 forge exp [SLUG]              # authored experiment files (targeted probes)
c2 forge levers                  # the lever catalogue (docstring-derived)
```

`solve` with no arguments runs the whole non-blocked diffing worklist.
After a win: `c2 decomp-verify -f <fn>`, `c2 line-compare <fn>`, commit
(Hard Rules #2/#8).

## What forge is NOT

* Not an analysis tool — use `c2 diagnose`, `c2 dossier`,
  `c2 decomp-verify -v`.
* Not a binary patcher — use `ghidra-cli`.
* Not an AST-mutation framework — levers emit minimal TEXT patches;
  if the targeted DSL doesn't cover a case, write a `Candidate` with
  hand-built `TextEdit`s.
