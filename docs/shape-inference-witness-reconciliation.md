# Shape inference via witness reconciliation (`c2 shape-recon`)

Design spec for a command that fuses the project's three independent
*structural witnesses* into a single **candidate statement skeleton**
for a function, with a per-statement **agreement classification** and a
corpus-wide **agreement metric** that tells us empirically whether the
shape-inference bet is worth pursuing.

Status: **IMPLEMENTED** (`c2 shape-recon`, `c2/commands/shape_recon.py`,
tests in `tests/test_shape_recon.py`).  Phases 1-4 shipped; the RC
correspondence column (§2.3) is a wired-but-unpopulated extension point
(see *Implementation notes* below).  This document is the contract.

### Implementation notes (what shipped vs the spec)

* **Witnesses A + C + B, alignment, confidence, disagreements, human +
  JSON views, and `--corpus`** all shipped as specified.
* **`ps_statement_spine`** is implemented as a clean parallel function in
  `shape_recon.py` (reads `symbols.json` + `le_code.bin` directly) rather
  than factored out of `line_skeleton.py`, to avoid any regression risk to
  the existing `c2 line-skeleton` command.  The two share no code but
  produce the same view of witness A.
* **RC correspondence** (`rc_cues`/`rc_rel`, §2.3) **shipped** (`--rc`,
  default on for a single function).  It builds an RC statement spine from
  a cached/incremental recompile's `-d1` marks (calls resolved via the RC
  `.map`, comparison constants read directly -- RC and PS are the same
  compiler+source, so no RC global resolution is needed) and aligns it to
  the PS spine with the same `_align` engine.  SPLIT (RC over-split a PS
  statement) is emitted conservatively -- only for an anchored PS statement
  owning ≥2 anchored RC statements -- and fires the `boundary`
  disagreement.  The human view gains an **RC line(s)** column, giving the
  three-way PS↔Mac↔RC delta.
  * **Validated** on `scroll` (a known mis-transcription, 16 PS vs 30 RC
    `-d1` lines): the over-split is now visible statement-by-statement.
  * **Recall lift**: adding SPLIT as a conflict raised the byte-exact
    mis-transcription recall vs `line-compare` from **12/41 → 19/41
    (~29%→46%)** while precision held at **19/20 (95%)**.

  **Boundary-divergence axis (precise per-statement line-mark compare).**
  For a byte-exact function PS and RC have the SAME instruction layout
  (`_layout_aligned`: equal boundary offsets — raw bytes differ only at
  fixup/address positions), so each RC `-d1` mark maps PRECISELY onto the
  PS statement whose byte span contains it.  Counting marks per statement
  gives the exact divergence `line-compare` reports globally, but
  localised: **0 marks → MERGE** (PS starts a statement RC combined),
  **1 → 1:1**, **≥2 → SPLIT** (RC over-split).  Diffing functions (offsets
  diverged) fall back to the approximate anchor SPLIT.
  * **Catches the class the Mac witness cannot see** — e.g. `scroll`'s
    residual PS-only mark at `+0x136` (a MERGE) that beat the manual
    dogfood is now flagged automatically.
  * **Honest cross-check separation:** boundary conflicts derive from the
    RC line stream — the SAME source `line-compare` uses — so they overlap
    the oracle BY CONSTRUCTION and are reported as signal **(b)**,
    distinct from the INDEPENDENT Mac signal **(a)**.  Measured on 58
    byte-exact fns: (a) Mac nesting/ir-shape — precision **12/13**, recall
    12/41; (b) RC boundary — recall **41/41** (native + localised, and the
    ONLY boundary detector that works on DIFFING functions, where
    `line-compare`'s exact-only sidecar can't run).  Concordance on the
    byte-exact set correctly falls to **0.48** once boundary divergence is
    detected — the true mis-transcription rate (71% are offenders), which
    the pre-boundary 0.87 was overstating.
  * The build is process-cached (`_ensure_rc_build`) so single-function
    and corpus runs recompile only once.  Corpus uses RC when `--rc`
    (default on); the A/B/C agreement metric is unaffected by RC.
* **`--corpus`** defaults to Mac ON (the meaningful agreement number);
  `--no-mac` gives the fast A+C floor.  Diffing functions come from the
  cached `decomp-verify --json` (`diff_byte_count > 0`), same source as
  `residue-cluster`/`negative-corpus`.

The phased plan below maps every piece onto existing code.

---

## 0. Why this, and why now

The remaining ~206 diffing functions are dominated by **whole-function
source-shape** problems (statement order, temp introduction, expression
factoring, type widths), not scattered idiom mistakes — see
`docs/open-corpus-levers-2026-06-14.md`.  Closing them by blind
mutation search does not work (the permuter ceiling; AGENTS.md Phase 3).

The lever we have that general decompilation does **not** is *two extra
structural witnesses of the lost original source*:

| # | Witness | What it pins | Axis | Produced by |
|---|---------|--------------|------|-------------|
| **A** | PS `-d1` line table | statement **boundaries** + **source order** (Hard Rule #4) | asm-offset | `c2 line-skeleton` (`line_skeleton.py`), `symbols.json["line_numbers"]` |
| **B** | Mac CodeWarrior decompile | control-flow **nesting** + variable **types** + per-stmt expressions, *independent of Watcom codegen* | PPC (no shared offsets) | `c2 mac-decompile` (`mac/clean.py` → pycparser AST) |
| **C** | binir IR reconstruction | per-statement **IR shape** (the byte-exact spec) | asm-offset | `c2.binir.recover` |

Academic decompilation (DREAM, Phoenix, SAILR) must *reconstruct*
control-flow structure from a bare CFG.  We mostly get it **for free**
from A+B and only need to reconcile the two.  Our actual hard problem —
statement-level shape — is exactly what A (order) and C (IR spec) and B
(nesting/types) jointly constrain.

The `dossier` already fuses all of these into a **human-reading pane**.
What is missing, and what this command adds:

1. A **normalized, ordered statement-skeleton data structure** with
   per-statement multi-witness attributes (not a rendered pane).
2. **Cross-witness alignment of the Mac AST (axis B) onto the PS
   statement spine (axis A/C)** — the genuinely new, hard piece.  A and
   C share the asm-offset axis and are already alignable via the
   `stmt-map` machinery; B lives on a separate axis and must be aligned
   *structurally*.
3. A **per-statement agreement classification** + **confidence**.
4. A **corpus-wide agreement metric** — the empirical payoff test: how
   often do the three witnesses actually agree?  If agreement is high,
   the skeleton is a reliable search seed / LLM prompt; if it is low,
   the bet does not pay and we learn that cheaply.
5. **JSON output** consumable by a downstream search seeder or LLM
   proposer (the Mizuchi-style "propose shape → verify bytes" loop).

---

## 1. The data model

The output is a `ShapeSkeleton`: an ordered list of `Statement`s, where
the **spine is the PS `-d1` statement stream** (witness A) because PS
line marks are ground truth for *boundaries* and *order*.  Each
statement carries the other witnesses' contributions and an agreement
verdict.

```python
@dataclass
class Statement:
    idx: int                      # position in PS source order (0-based)
    ps_line: int                  # PS -d1 source line (absolute, original file)
    ps_line_rel: str              # "L+10" (function-relative, dossier style)
    byte_span: tuple[int, int]    # (rel_off, rel_off+len) in the PS function
    multi_stmt: bool              # several marks on the same source line
    backward: bool                # line went backward (reorder/loop/shared-tail)

    # Witness A — PS line-skeleton summary (calls/global r-w/compares/arcs)
    a_summary: list[str]          # ["call get_water_cover", "->water_trouble_rate", ...]

    # Witness C — binir IR shape over byte_span
    c_ir: ShapeNode | None        # structural op tree (binir.recover → tree_diff shape)
    c_ops: dict[str, int]         # structural-op multiset (BINARY:O_LSHIFT×2, ...)

    # Witness B — aligned Mac AST node (may be None where alignment fails)
    b_node: MacStmt | None        # control construct + types + expr signature
    b_nesting: list[str]          # enclosing constructs ["if", "for"] (from B)
    b_types: dict[str, str]       # local/var name -> C type (signed/unsigned width)
    b_align_conf: float           # 0..1 alignment confidence for THIS stmt

    # RC correspondence (our current decomp) — from stmt-map
    rc_cues: list[str]            # ["L+12", "L+13"]  ([] = RC packs onto prev line)
    rc_rel: str                   # "1:1" | "SPLIT" | "MERGE" | "MISSING"
    rc_diff: bool                 # this statement currently diffs

    # Verdict
    witnesses: int                # how many of {A,B,C} corroborate (1..3)
    confidence: str               # "high" | "medium" | "low"
    disagreements: list[Disagreement]
```

```python
@dataclass
class Disagreement:
    axis: str        # "order" | "nesting" | "type" | "ir-shape" | "boundary" | "missing"
    detail: str      # human description
    witness_lo: str  # which witness disagrees with the spine, e.g. "B"
```

```python
@dataclass
class ShapeSkeleton:
    func: str
    file: str
    statements: list[Statement]
    n_high: int; n_medium: int; n_low: int
    mac_aligned: int; mac_total: int       # alignment coverage
    agreement_score: float                 # fused 0..1 (see §3.4)
```

The **spine choice matters**: PS order is authoritative (Hard Rule #4),
so the skeleton always lists statements in PS `-d1` order.  Witness B's
job is to *annotate* each spine statement with nesting/types/expr shape,
not to reorder it.  Where B implies a different order than A, that is a
recorded `Disagreement(axis="order")`, not a reordering of the spine.

---

## 2. Per-witness extraction (all reuse existing code)

### 2.1 Witness A — PS statement spine

Reuse `line_skeleton.py` almost verbatim.  It already yields, per PS
line mark: `{file:line, rel_offset, n_bytes, instruction-summary,
gap, multi-stmt/backward flags}`.  Factor its body into a reusable
`ps_statement_spine(name) -> list[SpineEntry]` (the CLI keeps calling
it; the new command calls the same function).  This gives the spine
list, `byte_span`, `a_summary`, `multi_stmt`, `backward`.

### 2.2 Witness C — binir IR per statement

For each spine entry, run `binir.recover(insns_in_span)` then
`tree_diff.shape_from_binir_ops(...)` to get `c_ir` and the structural
multiset `c_ops`.  This is exactly what `stmt_map.build` already does
per diverging segment (`rev = shape_from_binir_ops(binir.recover(
s.ps_insns))`) — lift that into a helper so both callers share it.

A and C are both on the **asm-offset axis**, so segmenting the function
at PS line-mark offsets aligns them with zero ambiguity.

### 2.3 RC correspondence

Reuse `stmt_map.build(...)` directly: it already produces the PS↔RC
segment correspondence (`1:1` / `SPLIT` / `MERGE` / RC-continues-prev)
and the forward(trace)/reverse(binir) IR asymmetry per diverging
statement.  Map each `StmtSeg` back onto the spine by its `ps_cue`
(`"L+N"`), filling `rc_cues`, `rc_rel`, `rc_diff`.

### 2.4 Witness B — Mac AST

`mac/clean.py::clean_decompile` already parses the Mac decompile into a
**pycparser AST** with PEF indirection collapsed.  Add a thin accessor
that returns the cleaned **AST** (not just regenerated text) for the
target FuncDef, then lower it to a `MacStmt` tree:

```python
@dataclass
class MacStmt:
    construct: str        # "if" | "else-if" | "for" | "while" | "do" | "switch"
                          #   | "assign" | "call" | "return" | "compound"
    children: list["MacStmt"]
    # structural signature used for alignment (compiler-independent anchors):
    calls: list[str]      # callee names referenced in this stmt
    globals: list[str]    # global names referenced (read/written)
    consts: list[int]     # integer literals
    cmp_consts: list[int] # constants appearing in a comparison
    types: dict[str, str] # declared local types in scope
    coord_line: int       # Mac source line (for stable ordering only)
```

The MacStmt tree gives `b_nesting` (the enclosing-construct path) and
`b_types`.  Its `calls`/`globals`/`consts`/`cmp_consts` are the
**cross-compiler anchors** — they reference the *same symbols and
literals* in both builds, so they survive the Watcom↔CodeWarrior
codegen gap and are what alignment keys on.

---

## 3. The alignment engine (the new, load-bearing piece)

Goal: assign each spine statement (axis A/C) the Mac statement (axis B)
that came from the **same original source statement**, despite no shared
offset/line axis.

### 3.1 Anchor signatures

For each **spine** statement, derive an anchor signature from witnesses
A+C (which read the *PS asm*):

* `calls`   — callee names (from `a_summary` `"call NAME"` + binir `CALL`).
* `globals` — global names read/written (from `a_summary` `->g` / `<-g`).
* `cmp_consts` — comparison immediates (from binir `OP_CMP_*(reg, IMM)`
  and `line-skeleton`'s `cmp` summary).
* `consts`  — other integer literals visible in the span.

For each **Mac** statement, the same fields come straight from the AST.
These four fields are **compiler-independent**: a call to `get_water_cover`,
a write to `water_trouble_rate`, a `cmp ..., 0xb`, are identical tokens
on both sides.

### 3.2 Sequence alignment

Run a **monotonic sequence alignment** (Needleman–Wunsch / global
alignment) between the spine list and the flattened Mac statement list,
with a similarity score per pair:

```
sim(spine_i, mac_j) =
      3.0 * jaccard(calls)        # calls are the strongest anchor
    + 2.0 * jaccard(globals)
    + 2.0 * jaccard(cmp_consts)   # branch constants are very discriminative
    + 1.0 * jaccard(consts)
    + 0.5 * construct_compat(c_ops_i, mac_j.construct)   # IR↔construct prior
```

`construct_compat` is a small prior: a spine statement whose binir shows
`OP_CMP_* + COND_BRANCH` is compatible with a Mac `if/else-if/for/while`;
a `CALL`-only span with a Mac `call`/`assign`; an `ASSIGN`/`PRE_GETS`
span with a Mac `assign`.  This breaks ties when anchors are sparse.

Monotonicity is enforced because **both sides are in source order** (PS
by Hard Rule #4; Mac by its own statement order, which is the original
order modulo CodeWarrior's far weaker reordering).  Gaps on either side
are allowed (penalised) and become `Disagreement(axis="missing")` or
`axis="boundary"`.

`b_align_conf` for a matched pair = its normalised `sim` against the
best alternative (margin); low margin → low confidence → flagged.

### 3.3 Why monotonic alignment and not tree matching

Tree edit distance is tempting (both sides have nesting) but B's nesting
is the thing we want to *transfer*, not assume.  A *linear* anchor
alignment keeps the PS spine authoritative for order while letting B
contribute nesting/types where anchors make the match trustworthy.  The
nesting from B is attached post-alignment (`b_nesting`), and any place
where B's nesting contradicts the spine's flat-guard vs nested structure
(readable from the PS branch-arc pattern in `a_summary`: forward
`jmp epilogue` runs = flat guards; interleaved arcs = nested) becomes a
`Disagreement(axis="nesting")`.

### 3.4 Confidence + agreement score

Per statement:

* `witnesses` = 1 (PS spine only) + (B aligned with `b_align_conf ≥ τ`)
  + (C produced a non-trivial IR shape).
* `confidence`:
  * **high** — all three present, no disagreements, `b_align_conf` high.
  * **medium** — A+C agree and B aligned but with a recorded
    nesting/type disagreement, OR B missing but A+C strong.
  * **low** — B unaligned *and* C trivial (PS spine is the only witness),
    or multiple disagreements.

Function-level `agreement_score` = mean over statements of a 0..1 value
(high=1.0, medium=0.5, low=0.0), weighted by `byte_span` length (big
statements matter more).  This is the number that, aggregated over the
corpus, decides the bet.

---

## 4. Output

### 4.1 Human view (`c2 shape-recon <fn>`)

One block per PS statement, in source order, e.g.:

```
# place2_a_building_base  pm_map2.c:568..639   33 statements   agreement 0.71
#   conf  L#     bytes   A: PS line-summary           B: Mac construct/types     C: binir shape        RC
  HIGH  L+0   +0x07 14b  ->bank_kind  <-build_data   assign bank_kind=...         ASSIGN,zext_byte      L+7  1:1
  HIGH  L+8   +0x1a 27b  cmp bl,0x1c; jne            if (style & 0x1c)            CMP_NE,COND_BRANCH    L+8  SPLIT  ⚠nesting
  MED   L+9   +0x39 17b  <-pm_diamond_..; al<-tab    x = table[idx]   (uchar)     zext_byte_load        L+11 1:1
  ...
  LOW   L+21  +0xe5 11b  esi=byte<<8                 (no Mac match)               copy_then_op          L+33 1:1   ⚠B-missing
  ...
# disagreements: 1 nesting (L+8), 3 boundary (SPLIT), 2 B-missing
# witness coverage: A 33/33, B 27/33 aligned, C 30/33 non-trivial
```

The `⚠` flags are the **search frontier**: statements where the
witnesses disagree are exactly where a human (or the localized search of
the companion spec) should focus, and the rest is high-confidence
skeleton that can be written down directly.

### 4.2 JSON view (`--json`)

Emits the full `ShapeSkeleton` (§1) for downstream consumers: the
localized expression-search seeder, or an LLM "propose the C shape"
prompt (the Mizuchi pattern).  This is the machine contract; keep it
stable.

### 4.3 Corpus mode (`c2 shape-recon --corpus`)

Runs over all diffing functions (from the cached `decomp-verify --json`
blob, same source as `residue-cluster`/`negative-corpus`) and prints:

* distribution of `agreement_score` (histogram),
* Mac alignment coverage (what fraction of statements B reaches),
* a ranked list: functions with **high agreement but still diffing** =
  the best targets (skeleton trustworthy → the residue is a small set of
  flagged statements), vs **low agreement** = where the witnesses can't
  help and a different lever is needed.

This ranked list is the immediate, standalone payoff even before any
search is built: it tells you *which* open functions are
shape-recoverable today.

---

## 5. Phased implementation plan

Each phase is independently useful and testable.

* **Phase 1 — A+C spine (no Mac).**  Factor `ps_statement_spine` out of
  `line_skeleton.py`; lift the binir-per-segment helper out of
  `stmt_map.build`; emit the skeleton with witnesses {A,C} + RC
  correspondence.  Ship the human + JSON views.  *Deliverable:* a
  statement skeleton + RC delta that is strictly richer than `stmt-map`,
  with zero new inference.  Validate on a handful of byte-exact
  functions (the skeleton must reproduce their known structure).

* **Phase 2 — Mac AST lowering.**  Add the cleaned-AST accessor to
  `mac/clean.py`; build the `MacStmt` lowering + anchor extraction.
  Render B as an *un-aligned* side column first (sanity).

* **Phase 3 — Alignment engine.**  Implement §3 (anchor sim + monotonic
  alignment + confidence).  Add the `Disagreement` classification.
  *Validation:* on **byte-exact** functions, the alignment should land
  high-confidence with few disagreements — they are byte-exact, so the
  recovered source shape is (near) correct, giving a labelled set to
  tune `τ` and the `sim` weights against.

* **Phase 4 — Corpus metric.**  Add `--corpus`; produce the agreement
  distribution + ranked targets.  **This is the go/no-go measurement**
  for the whole shape-inference direction.

* **Phase 5 (separate spec) — consume the skeleton.**  Feed the JSON to
  the localized expression search and/or an LLM proposer.  Out of scope
  here.

### Reuse map

| Need | Existing code |
|------|---------------|
| PS spine, line summaries, gaps | `c2/commands/line_skeleton.py` |
| PS↔RC segment correspondence | `c2/commands/stmt_map.py::build` |
| binir per-span IR + structural multiset | `c2/binir.py`, `c2/tree_diff.py` |
| Mac cleaned AST | `c2/mac/clean.py::clean_decompile` (+ new AST accessor) |
| Mac function lookup / availability | `c2/macref.py`, `c2/commands/mac_decompile.py` |
| Offset-aligned stream building | `c2/commands/dossier.py` (per-side walkers) |
| Corpus source (diffing fn list) | cached `decomp-verify --json` (as in `residue-cluster`) |

---

## 6. Validation & honesty

* **Self-check on byte-exact functions (`c2 shape-recon --corpus
  --exact`).**  Run the tool over functions whose recovered source
  already produces byte-identical code, and cross-validate against the
  independent `line-compare` offender signal.

  **Measured (58 byte-exact functions, 2026-06-16):**
  * shape-CONFLICT rate (nesting/ir-shape) = **8 % of statements**;
    coverage-gap rate (`missing`) = 18 %.
  * 13/58 functions carry ≥1 shape conflict.
  * **Of those 13 conflict-flagged functions, 12 are ALSO
    `line-compare` offenders** (~92 % precision against an independent
    detector).  i.e. shape-recon's disagreements on byte-exact functions
    are overwhelmingly NOT false positives — they catch source that is
    byte-equal but **mis-transcribed** (Watcom emits identical bytes from
    a different source shape, Hard Rule #8).  The lone `line-compare`-clean
    case is the genuine false-positive bucket to debug.
  * shape-recon catches 12/41 `line-compare` offenders — lower recall
    (many offenders are statement-splits with no Mac conflict), but it
    ADDS what line-compare lacks: the Mac witness and **statement-level
    localization + the shape the statement should have**.

  **Key calibration lesson (now baked into the score):** separate
  **coverage** (`missing` — benign witness sparsity; many tiny `action.c`
  handlers aren't in the Mac build) from **concordance/conflict**
  (`nesting`/`ir-shape`/`boundary` — the real mis-transcription signal).
  The function score is now reported as two numbers:
  * **coverage** = byte-weighted fraction of statements with ≥2 witnesses
    (PS spine + Mac and/or binir) — how much we can judge.
  * **concordance** = among those informative statements, the fraction
    with NO shape conflict — the CORRECTNESS signal.  (`agreement_score`
    is kept as an alias for concordance.)

  This fixes the old `agreement_score`, which conflated the two and
  ranked byte-exact (correct) functions *below* diffing ones.  Measured:
  byte-exact concordance **mean 0.87 / median 1.00** (high, as correct
  source should be) vs the old agreement 0.40.  The discriminating cell
  is **low concordance + high coverage** = witnesses present but
  disagree = likely wrong recovered shape (e.g. `general_reform` 0.40 @
  93% cov); **high concordance + diffing** = shape is right, the residue
  is a layer below (regalloc), e.g. `place2` 1.00.

  This also makes shape-recon a **triage tool for the `line-compare`
  offender backlog**: it points at WHICH statements diverge and shows the
  Mac shape they should take.

* **Where it will be weak (state up front):**
  * **Mac alignment is approximate.**  Functions with few calls/globals/
    branch-constants (pure arithmetic kernels) have sparse anchors →
    low `b_align_conf` → B contributes little.  That is correctly
    reported as low confidence, not silently guessed.  An
    **expression-shape** similarity term (`_canon_ps_ops` ↔ `_mac_ops`:
    a canonical op vocabulary mapping binir IR ops to Mac AST operators)
    lets such statements align by the shape of their computation
    (shift+add, divide, cast).  Measured lift is **marginal (~+1 pt Mac
    alignment coverage)**, because the real ceiling is elsewhere:
  * **Mac availability is the dominant coverage cap.**  Only ~53 % of
    functions exist in the Mac build at all (many tiny `action.c`
    handlers are absent), and statements where binir *also* recovers no
    IR (pure register shuffles, `lea`s) are reachable by neither anchors
    nor expression-shape.  Mac alignment coverage therefore plateaus at
    ~50–58 %; the remainder is a data limitation, not a tunable one.
    Concordance/precision are unaffected by the expr-shape term
    (byte-exact concordance 0.87, conflict precision 19/20 held).
  * **CodeWarrior is a different compiler.**  Its decompile can fold/
    split expressions differently from the original; B is a *nesting +
    type* witness first, an *expression* witness second.  We weight it
    accordingly (`construct_compat` is only 0.5).
  * **Statement ordering inside big regalloc-pressure loops** (the
    deepest residue) is exactly where PS `backward` line marks and
    Watcom reordering live.  The skeleton *flags* these (`backward`,
    nesting disagreements) but does not resolve the reorder — that needs
    the offline regalloc model (companion spec).  shape-recon's job is
    to *localize* the hard statements, not to crack them.

* **The metric is the point.**  Even if shape-recon never directly
  closes a function, the §4.3 corpus number answers the strategic
  question — *is the lost source shape recoverable from the witnesses we
  have?* — with data instead of intuition.  A high number greenlights
  the LLM/search consumer; a low number redirects effort to the
  regalloc-model bet.

---

## 7. Relationship to prior art

* **Matching-decompilation scene** (decomp.me, m2c, decomp-permuter,
  Mizuchi): shape-recon is the *witness-fusion front half* of a
  Mizuchi-style loop — it produces the structured prompt/seed that an
  LLM or m2c-like proposer turns into candidate C, verified by recompile
  (`decomp-verify`).  decomp-permuter's manual `PERM_GENERAL` macros are
  the per-statement equivalence classes the §4.2 frontier statements
  feed into.
* **SAILR (USENIX '24), compiler-aware structuring:** validates the
  posture — we exploit Watcom-specific structure rather than producing
  goto-free generic output.  Its de-optimization transforms are relevant
  only at the §3.3 nesting-disagreement points.
* **Debug-line-table literature** (LLVM `is_stmt`, Tice's optimized-code
  debugging): explains the PS `-d1` `backward`/`multi-stmt` marks as
  optimizer statement reordering/merging — i.e. *why* witness A is a
  faithful but optimizer-perturbed order signal, which is what the
  `backward` flag records.
* **Type recovery** (TIE, Retypd): witness B's `b_types` is a
  second-compiler shortcut to the same signed/unsigned-width inference
  these systems do from dataflow.

---

## TL;DR

Build `c2 shape-recon <fn>`: spine = PS `-d1` statements (order ground
truth), annotate each with binir IR (the byte-exact spec) and the
**structurally-aligned** Mac AST (nesting + types), classify per-statement
agreement, and emit a human view + JSON seed + a **corpus agreement
metric**.  It reuses `line_skeleton` (A), `binir`/`tree_diff` (C),
`stmt_map` (RC), and `mac/clean` (B); the one new component is the
anchor-based monotonic alignment of the Mac AST onto the PS spine
(§3).  The corpus metric (§4.3) is the cheap go/no-go measurement for the
entire shape-inference direction.
