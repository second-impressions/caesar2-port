# Caesar II Decompilation — Agent Guide

The single agent guide for the Caesar II PS.EXE decompilation: hard
rules, the workflow, the command reference, the codegen knowledge base,
and the operational detail.  (It replaced the former two-file split —
`AGENTS.md` + `decomp/AGENTS.md` — in 2026-07; if you find a reference
to `decomp/AGENTS.md`, it means this file.)

Per-command details: `uv run c2 <cmd> --help`.

---

## ⚠️ CRITICAL: THE GHIDRA DB IS REBUILT BY A SCRIPT, NOT HAND-CURATED

The Ghidra project (`./C2`, program `PS.EXE`) is a **disposable,
fully-reconstructable artifact**.  It is gitignored and rebuilt from
scratch by [`scripts/rebuild-ghidra.sh`](scripts/rebuild-ghidra.sh),
which imports PS.EXE with the LE-Style DOS loader + `x86:LE:32:watcom`
language and runs `ghidra_scripts/ImportCaesar2.java` as the post-script.
If the DB is ever missing, stale, or wrong, **just rebuild it** —
nothing in it is hand-edited.

That script applies, and a bare re-analyze would destroy:

- **Debug symbol imports** (~2,234 functions, one per unique debug symbol)
- **Authoritative function boundaries** — every body is normalized to its
  contiguous debug-symbol span `[addr, next_symbol)` (Step 5.5)
- **Line number comments** from debug info (24,568)
- **Program tree organization** (source files grouped by subsystem)
- **Calling convention assignments** (__watcall, etc.)
- **Noreturn function fixes** (Watcom shared-epilogue quirks corrected)

**There is NO "hidden function discovery".**  PS.EXE ships full Watcom
`-d1` debug info that names EVERY function and covers 99.99 % of the code
object, so there are no unlabeled functions to find.  The old heuristic
pass did not discover hidden functions — it *shredded* named ones into
~4,600 spurious `FUN_` fragments (a stub-bodied function's interior looks
"outside any function", so every internal branch target after a RET/JMP
got carved off).  Discovery now runs only over the ~42 bytes NOT claimed
by a debug symbol.  A correct DB has ~2,235 functions and ≤1 `FUN_`, not
7,092.  See `ImportCaesar2.java` Step 4 + Step 5.5.

**Never run bare:** `ghidra-cli analyze --project ./C2` — it re-fragments
the DB.  To fix the DB, run `scripts/rebuild-ghidra.sh` instead.

---

## ⛔ HARD RULES (read before doing ANYTHING)

### 0. READ `docs/observed-source-style.md` BEFORE WRITING ANY C

`docs/observed-source-style.md` is the inferred PS source-style guide,
distilled from the byte-exact corpus.

* **§0 Source forms** — C99 mid-decl + C99 for-init are physically
  rejected by Watcom 10.0a (hard compile errors).  Bare `{ }` scope
  blocks are **corpus-rare, not prohibited**: the simple synthetic
  cases probed in `docs/codegen-experiments/decl-placement.py` are
  byte-equivalent to top-of-function form, but there is at least one
  empirical counter-example (`battle.c::fly_to_target`'s `int ptr;`
  block) where the bare block is load-bearing: flattening `ptr` to the
  function top adds it to the *function-level* ConfBefore name queue,
  which perturbs an UNRELATED value's (`delta_anim`) CountRegMoves
  tie-break (EAX→EDX) — ~30 decl-order / assignment-order /
  embedded-assign / de-invent variants + `regtrace` confirm NO
  top-of-function form reproduces it.  (The block ALSO needs the
  *deferred* form `int ptr; ptr = …;` — init-in-decl `int ptr = …;`
  breaks the bytes even inside the block.)  Default to strict-C89
  top-of-function, one variable per line (the overwhelming corpus
  norm); reach for a bare block when removing it demonstrably breaks
  byte-exact.
* **§1–§9** — codegen-load-bearing source idioms (inline index vs
  cached pointer; if/else-if vs switch; `x + x` vs `x * 2`; etc.) with
  corpus counts.
* **NOT OBSERVED table** + **normalization ledger** — every
  interchangeability experiment that was run and whether it was NOISE
  (free choice) or LOAD-BEARING (matters to the bytes).
* **§10–§12** — family-level patterns (range walkers, de-inventing
  temps, c2.c burn-down).
* **§13** — the gloops.c burn-down patterns, including the
  over-decompiled-mirror corpus signal (5x diffing-vs-exact bias for
  single-assign locals that mirror a global with no aliasing); the
  proven mechanism is a structural rank change in the regalloc queue
  (named local consolidates N inline reads into ONE sav=N+1 FE
  conflict at the top of `ConfBefore`, while inline reads stay as N
  sav=2 anon leaves at the bottom).
  Note: WIN `/Od` decompile is NOT a 1:1 source mirror for locals —
  Ghidra inlines simple `int x = arr[i].field;` — so a missing-in-WIN
  local does NOT prove missing-in-PS.
* **TL;DR** — default writing recipe.

When the style guide conflicts with anything else (this file,
`docs/watcom-codegen-patterns.md`, …), the style guide is the source
of truth.

### 1. You are (almost certainly) NOT alone in this tree

Other agents are usually working on the same tree in parallel.
Nothing in pi enforces single-agent ownership, and the parallel
sessions commit at their own cadence — sometimes between your
baseline read and your final verify.  Stay aware of this and act
accordingly:

* **`git checkout <file>` destroys uncommitted parallel work** without
  warning.  Almost never the right tool for an undo.
* **Stale snapshot reverts can clobber *committed* parallel work
  too.**  If you `cp file /tmp/backup.c` early in your session and
  then `cp /tmp/backup.c file` later, you silently revert any
  *commits* the parallel session landed on that file in between.
  Worked example: `b4fe5e1` silently reverted the parallel session's
  `c37a34a` get_fb_lines firstassign swap because the `/tmp` backup
  pre-dated `c37a34a`; caught later as a 52→50b regression and
  restored in `bc64459`.
* **Prefer small, targeted undo.**  Use the `edit` tool to reverse a
  specific change rather than restoring whole-file snapshots.  When
  you do need a snapshot, take it *immediately before* the edit you
  want to be able to undo, not at session start.
* **Re-check `git log -L` for the region you're committing** before
  every commit if there's any chance a parallel session has been
  touching the same file.  `git diff --stat HEAD~5 -- <file>` is a
  cheap sanity check.
* **Per Hard Rule #2, commit your wins fast.**  The longer your edits
  sit in the working tree, the higher the chance of a stale-snapshot
  collision with a parallel commit.
* **Stage narrowly.**  `git add <specific-file>` (not `git add -A` or
  `git add .`) so unrelated parallel edits in the working tree don't
  get absorbed into your commit.

### 2. Commit clear wins immediately

When a change makes a function **byte-exact** (0 byte diffs = the DONE
oracle), OR drops its layered `shape_distance` toward PS with the
correct source shape, **commit it right away** (`git add` +
`git commit`) with the rule numbers and the postmortem (what was wrong,
what fixed it, why).  Do not batch wins across multiple functions.
Lead with the SHAPE result — concordance / binir delta / the named PS
construct recovered — not a byte number.

### 3. Judge a trial edit by SHAPE + asm, never by the byte count

The per-function **judge metric is the layered `shape_distance`**
(`ir/width/spill/seat` + `fix_next`), surfaced by `decomp-verify -v -f`,
`diagnose`, `dossier`, `regtrace`, `worklist`.  **The byte diff is not
shown per function** (it is the `progress` project-view's corpus figure,
and the 0-byte DONE oracle) — so do not reach for it to decide whether
an edit helped.  For every trial edit:

1. Apply the change.
2. Run `c2 decomp-verify -v -f <fn> --no-strict` (or `c2 dossier <fn>`).
3. **Read the `shape vs PS` line + the diff rows** — compare PS and RC
   asm side by side.  Did `shape_distance` DROP (moved toward PS)?  Did
   a new `movsx`/`cwde` appear (Rule 151)?  Did a `cmp/jne` pair
   appear/vanish (Rule 152)?  Did the prologue push set change?
4. Only THEN decide: keep, adjust, or revert.  An edit that DROPS
   `shape_distance` is PS-faithful even if (unseen) bytes rose; keep it.

Proved: `mouse_follow_cohort` `else if` raised bytes but was the RIGHT
fix — combined with type-width corrections it reached 0.

**Corollary: read the function's own comment FIRST.**  Documented
experiment results ("tried X, regressed, reverted, HERE's why") are
reliable and save you from re-running a known-failed probe (worked
example: evolve_a_cm_row's ternary→if/else was re-tried and re-reverted
in 2026-07 because the session probed before reading the note).  This
does NOT contradict Hard Rule #6 — *evidence* in comments is
trustworthy; *conclusions* ("parked", "floor", "unfixable") are not.

### 4. Read PS `-d1` line numbers FIRST — they ARE the original source shape

**Before writing or modifying ANY function, run `c2 disasm <fn>` and
read the `L<N>` column.**  These are the original Watcom `-d1` line
numbers — the ONLY surviving witness of how PS's `.c` file was
structured.  They tell you:

- **Statement boundaries** — a new `L` = new source statement.
- **Nesting structure** — flat guards: sequential `L` + `jmp epilogue`;
  nested if/else: interleaved `L` blocks.
- **Explicit `else if`** — `cmp reg, K; jne` = `else if (var == K)`
  (Rule 152); bare `else` produces NO compare.
- **Variable types** — `movsx` at a field load = `int` local;
  `mov ax,[field]` + `cwde` = `short` local (Rule 151).
- **Walk order vs source order** — `L610` after `L611` in address
  order = the compiler reordered; source order is the `L` number
  order.

`mouse_follow_cohort` (198b→0b) was solved entirely by reading these
line numbers.

### 5. Use output truncation thoughtfully; keep the diagnostic hints

The verifier (`c2 decomp-verify -v`), `c2 disasm`, `c2 dossier`, and
`c2 regtrace` emit **every hint for a reason**.  It is fine to use
`grep`, `head`, `tail`, or similar filters when they make the work
clearer, faster, or more focused — but **do not filter away the
interesting output**.  If you are still exploring an unfamiliar
function or diagnosis, read the full diagnostic output (or a wide
enough slice) before narrowing.  If the output is genuinely too noisy,
improve the tool so every future session benefits.

**`decomp-verify -v` defaults to a focused view**: a *windowed* diff
disasm (long byte-identical runs collapse to `… N unchanged row(s)
elided …`) with the lower-signal blocks trimmed.  Everything stripped
is one flag away: `--full-hints` (or `C2_FULL_HINTS=1`) restores the
complete diagnostics — reach for it when a diff spans a wide region or
you need the full `-d1` line walk (Hard Rule #4).

**Never pipe a foreground `c2 forge solve` through
`head`/`tail`/`grep`** — the user watches its live stream; the full
record persists in `.c2-cache/forge-runs/` (`c2 forge report` /
`c2 forge diff`).

### 6. Comments above functions are UNRELIABLE — ignore residue/parked/floor claims

Comments like `/* PROBE: allocator-residue, parked */`, `/* reached
the floor */`, or `/* Rule 111 spill, unfixable */` were written by
previous sessions that **did not have the tools or knowledge you have
now** (worked example: top_it's 2026-07-07 "not source-lever-reachable"
certificate was overturned two days later when the trace-starved
closeability machinery came back online and named three heal sites).
Every function labeled "parked" or "floor" is a candidate for closure
with the current tooling.

**Treat stale CONCLUSIONS as null and void** — but per Hard Rule #3's
corollary, documented *experiment evidence* (what was tried, what it
did) is valuable; read it before probing.

**Nothing ends work on a still-diffing function except byte-exact.**
A well-evidenced regalloc-residue analysis — IR-identical to PS,
**win-checked** (Hard Rule #7), traced via `regtrace --explain` /
`binir-shape` / the rover machinery — is how you *document* a hard
function, not how you finish it.  It earns three things: (1) the next
session skips the searched space; (2) the function drops in priority;
(3) the divergence class becomes a research target.  It does NOT earn
"done".  There is no "unreachable" — only "no lever *found yet*"
(worked example: `try_this_regionmap_square`'s framed mid-function
epilogue, documented as unreproducible, fell out byte-exact from a
`goto`-placement change).  Stale residue comments may be deleted on
sight when you touch that function.

### 7. Use `c2 mac-decompile <fn>` / `c2 win-decompile <fn>` for the source shape

The Mac PPC build was compiled from the **SAME source** by CodeWarrior;
its Ghidra decompile shows the source *shape* (nesting, types, control
flow) independently of Watcom's codegen.  The Windows `CAESAR2.EXE`
build (MSVC 4.0 `/Od` of the same engine source, CRT byte-proven) is a
second source oracle — x86 AND unoptimized, often the most legible of
the three — **and a second BYTE oracle** (`c2 win-verify` /
`c2 decomp-verify --target win`).  Full detail in the command
reference (`c2 win-decompile`, `c2 win-verify`, `c2 win-census`).

**On a seat/spill/width-dominant (✓IR) diff, run `c2 win-verify -v <fn>`
FIRST — before regtrace, before forge.**  binir IR-identity is measured
against the WATCOM compile, which canonicalizes away exactly the source
defects that own most "pure regalloc" residues: invented temps with
byte-identical realizations, write-only locals, precomputed bounds PS
never had, guard nesting Watcom tail-merges.  MSVC `/Od` keeps ALL of
these visible.  Proven 2026-07-04 on the map.c elastic family: five ✓IR
"regalloc residue" functions went byte-exact by fixing the win-visible
shape — the seat flips came for free (fd93151a, 49893918, fd83ebd9,
23a831cb).  Only a win-clean (or win-classified fragile-codegen)
function is a certified regalloc residue — and certification
documents/deprioritises, it does not finish (Hard Rule #6).

Caveats: MSVC 4.x codegen is *fragile-but-deterministic* — a stable
win-diff is either (a) a real shape defect the Watcom oracle is blind
to (fixable) or (b) a reproducible codegen-realization difference that
resists every source rewrite (classify, don't grind); discriminate by
editing and watching BOTH oracles.  Where the oracles conflict on
Watcom-visible details (operand order, chained assignments), the DOS
byte oracle wins.  The Mac decompile is not inlined in `decomp-verify`
by default (JVM ~25 s); `c2 mac-decompile <fn>` / `--mac-decompile`.

### 8. Byte-exact is NECESSARY but NOT SUFFICIENT — run `c2 line-compare <fn>` after every win

Watcom's optimiser can produce identical bytes from different source
shapes (statement reordering for register reuse, expression factoring,
scope rearrangement).  **After every fresh byte-exact win, run
`c2 line-compare <fn>` BEFORE the commit.**  It compares PS's `-d1`
line stream against RC's and surfaces:

1. **DIRECTION DIVERGENCE** — at the same byte offset, PS goes backward
   in source-line order while RC goes forward (or vice versa).  Both
   sides backward together is FINE; only opposite directions is the
   smell — the recovered source has its statements in a different
   order than PS.
2. **OFFSET MISMATCH** — line marks land on different instructions
   (e.g. `int a; int b;` on one line vs two).  Weaker smell.

Worked example — `choose_odd_tune`: bytes matched as
`odd_battle_tune = 1; tune_branch += 1;` but PS's marks ran backward;
PS source had the statements in the opposite order (Watcom reordered
them to reuse `ebx = 1`).  The macro hypothesis was tested and
disproved (`docs/codegen-experiments/d1-macro-lines.py`); statement
reordering for register reuse is the proven mechanism.

Whole-corpus mode: `c2 line-compare --offenders`.  The richer
companion is **`c2 shape-recon <fn>`** — the same per-statement check
localised to the exact statement, fused with the Mac witness, and it
works on non-byte-exact functions too (see the command reference).

---

## ⭐ THE WORKFLOW

### Session start

**Run [`c2 worklist`](c2/commands/worklist.py)** — the live dispatcher.
One fused verdict per diffing function — **WORKABLE** (named lever +
the command to run), **HARD**, **BLOCKED** (tail-merge donor not exact
yet), **PARK** (no lever the classifiers can name — lowest priority,
*not* a proven floor), **DIAGNOSE** (the new-rule frontier) — ranked by
shape-distance (`fix_next` layer: ir > width > spill > seat).  Pick a
target, then drop into the per-function loop below.

Worklist knobs: `c2 worklist <fn>` = one function's verdict with ALL
its independent levers (dominant + `ALSO:` list — fix each);
`--file <name>` scopes to TUs (exact basename, repeatable/comma-lists,
`-`/`!` prefix excludes); `--status park|workable|hard|diagnose|blocked`;
`--per-file 1` / `--per-bucket 3` / `--shuffle [--seed N]` for variety;
`--json`.  It auto-refreshes `verify.json` incrementally when stale
(`--no-refresh` for the instant view; caveat: a cross-TU tail-merge
dependent whose donor lives in a changed file can stay stale until the
next full rebuild).  The `triage` reachability axis is refreshed on
demand with `c2 triage --rebuild`.  [`TODO.md`](TODO.md) and the
`docs/remaining-corpus-plan-*.md` files are the narrative companions.

**The toolchain is proven settled** — `PS_CFLAGS = -bt=dos -mf -4r -s
-d1`, default `OptSize=50`, unsigned `char` (no `-j`; cross-build
proven, `docs/char-signedness-proof.md`).  Every remaining diff is
source-shape, not a flag/version gap; do not chase flags.

### The per-function loop

0. **Orient**: `c2 worklist <fn>` (the verdict + lever order), then
   **`c2 disasm <fn>`** (the `L<N>` `-d1` line read, Hard Rule #4),
   the three decompile oracles — `ghidra-cli decompile <fn>` (PS.EXE
   target), **`c2 mac-decompile <fn>`** (CodeWarrior shape),
   **`c2 win-decompile <fn>`** (MSVC `/Od`, most legible) — and
   **`c2 sibling <fn>`** (nearest byte-exact template; the
   highest-leverage win-starter for a new or wrong-shape function).
   For the deepest single look: **`c2 dossier <fn>`** — the focused
   first-divergence view (re-run after each edit; bisect mode).
1. **Triage**: **`c2 diagnose <fn>`** — concordance + const-audit +
   binir residue + run-ledger, with a routed `next`.  Act in order:
   * **const NOT clean** → fix the wrong literal / off-by-one boundary /
     out-of-order arg FIRST (layer-1, regalloc-invariant).
   * **LOW concordance** (< ~0.75) → the recovered SHAPE is wrong → fix
     the structure first (`c2 mac-decompile` shows it); regalloc is
     wasted effort until it matches.
   * **HIGH concordance + still diffing** → shape is right; residue is
     regalloc/codegen → step 4.
2. **Write/fix the C body** per `docs/observed-source-style.md`
   (Hard Rule #0).
3. **Verify every edit**: `c2 decomp-verify -v -f <fn>` — read the
   `shape vs PS` line + diff rows (Hard Rules #3/#5).  Check Rule 151
   (movsx/cwde width) and Rule 152 (missing else-if) FIRST — they cause
   rover cascades that look like regalloc but aren't.
4. **Regalloc residue**: `c2 win-verify -v <fn>` first (Hard Rule #7),
   then **`c2 seats <fn>`** (the certified full-chain flip verdict — it
   names the lever CLASS and, for a `masked` seat, runs the ACTUATOR
   STACK to a VERIFIED composite: names the blocker to shorten + the
   credit ins to break — `masked-blocker` / `masked-pinned` /
   `masked-composite`; `--want VAR=REG` pins a specific seat) and
   **`c2 regtrace <fn> --explain`** (the allocator ground
   truth + PS↔RC seat diff, now carrying the same chain verdicts).
   For a savings-order / tie-order verdict, **`c2 savings <fn>
   --flip VAR=REG`** searches the grounded single-edit space through
   the FULL sort+pick replay and names the ref-level lever (+ its
   side-effect re-seats, which must match PS); `--var X` prints the
   per-ref ledger behind any savings figure.  For a ROVER / walk-order / chain-structure seat:
   the `Rover:` hint in `decomp-verify -v` carries the confirmed
   inject / fit windows + `[lw census: ...]` candidates; **`c2 spell`**
   is the front door — `--suggest` GENERATES the fold/unfold candidates
   and screens them, `<candidate.c>` screens hand-written variants
   across the full tree→births→walk ladder, `--fusion`/`--walk-order`/
   `--chain` are the diagnosis views (see the command reference).
   `c2 forge solve <fn>` is the remaining automatic actuator (see the
   command reference for when it can and cannot help).
5. **When byte-exact**: `c2 line-compare <fn>` (Hard Rule #8) before
   commit; fix any out-of-order / split-merge divergence and re-verify.
6. **Commit immediately** with the rule number(s) (Hard Rule #2).

**Big function (> ~400 b) still diffing in shape?**  Do NOT read the
whole diff — work it island by island: `c2 ledger <fn>` → take the
first island (skip `slot`/`frame` tags until the type/shape islands
are gone) → ONE statement-level edit at the island's source line →
verify → re-run the ledger.  A type fix typically collapses many
islands at once.

**Drive a whole file to byte-exact**: `c2 functions <file>` lists its
functions by status (byte-exact ✓ / diffing sorted by shape_distance /
STUB / MISSING); loop the per-function steps over the diffing ones.

### The dependency DAG (order of work across the corpus)

Two cross-function dependencies, pointing opposite ways:

1. **Prototype (CallZap):** a caller's regalloc depends on each
   callee's declared *prototype* (arg count + return-void), **not** its
   body — you can drive a caller byte-exact while its callees are still
   stubs.  Per-TU visibility.
2. **Tail-merge:** a dependent's body can't go byte-exact until its
   **donor's body** is byte-exact.

* **Phase 0 — type substrate**: globals + struct-field types (signed
  vs unsigned `char` → `movsx`/`movzx`, widths, pointer-ness).  Fix in
  `entities.h` / `_TYPE_OVERRIDES`; one edit flips many functions.
* **Phase 1 — prototypes everywhere**: `c2 inferred-sig --all --stubs`
  → `c2 sig-drift --actionable --by-tu` → `c2 callgraph --check`.
  Cheap, horizontal, multiplicative.
* **Phase 2 — bodies donor-first**: `c2 stubs --donors`.  **Never start
  a tail-merge dependent before its donor is byte-exact** (skip it —
  `decomp-verify -v` prints the donor).
* **Phase 3 — per-function source-shape**: the loop above.  Discovery
  layer for finding targets: `c2 decomp-verify --shape-divergence`
  (whole-surface `-d1` trajectory map), `c2 residue-cluster` (residue
  families; `--novel`), `c2 negative-corpus` (un-PS shapes with lift),
  `c2 sibling --survey` (structural partition).

Guard every horizontal batch with `c2 baseline save` / `check`.

### The judge metric: layered `shape_distance`

Every per-function command surfaces `shape_distance`: a byte-INDEPENDENT
distance-to-PS decomposed by residue layer.  Read the per-layer `N/T`
(N divergent of T comparable) + `fix_next`:

    shape vs PS: ir 14/59 (isl 12) · width 4/31 · spill 6/9 · seat 2/8  → fix-next: ir

`(isl 12)` is the run-ledger ISLAND count — the ir layer's fine-grained
unit (one island = one local statement-shape divergence; **`isl 0` =
regalloc_pure**: every insn matches register-blind, do NOT restructure —
`c2 ledger <fn>` is the drill-in).  The layers, in strict **FIX-ORDER**
(work the highest non-zero one first — `fix_next` names it):

1. **`ir`** — wrong OPS / control-flow: the recovered SOURCE SHAPE is
   wrong.  Fix the C shape first; everything below is downstream.
2. **`width`** — type/signedness divergence.  Fix the local's type
   (`c2 regtrace` names the value + the `jge`/`movsx`/`sar` form).
3. **`spill`** — frame / live-range divergence.  Add/de-invent named
   locals to match PS's live-set.
4. **`seat`** — register-identity tie (often sub-source; the hardest,
   least reliably source-fixable layer).

When **`shape == 0`** the residue is a pure regalloc tie-break /
encoding — document the evidence and spend your session where levers
are named, but the function stays OPEN: only 0 bytes closes it.
Prioritise across the corpus by `fix_next` (a width pass over the
width-dominant functions, etc.).  The divergence is LOCATED to source
lines — `c2 diagnose`'s `divergent_lines` and `c2 dossier`'s
first-divergence pane collapse the fix from "somewhere in the function"
to "edit these lines".

---

## The goal: byte-exact, approached through PS-faithful shape

**The goal is a PS-faithful decompilation: the source shape, types,
constants, field offsets, and logic match what PS's `.c` actually
contained.**  Byte-exactness conflates (a) *the source is right* —
what we actually care about — with (b) *the optimiser's tie-breaks
landed identically* (rover picks on compiler temps, spill tie-breaks,
donor flips — often below the source level).  The primary signal is
(a): concordance, binir IR-identity, the Mac/Win oracles, the absence
of wrong-shape constructs.  Byte-exactness is kept as three things,
all load-bearing:

1. **the verifier** — the one check that needs no external ground
   truth (PS.EXE *is* the spec; there is no behavioural test suite).
2. **the residue classifier** — `binir-shape: all N/N identical`
   proves a remaining diff is pure regalloc, not shape.
3. **the bug-oracle** — a byte divergence is the trail to a real bug
   you can't see any other way.  Worked example:
   `show_people_query_panel` had concordance 1.00 yet the byte diff
   exposed `draw_a_box` rendering on the wrong Y and `draw_a_dias` off
   by 0x1a — real behavioural bugs, invisible to every shape metric.
   **Never dismiss a byte diff without reading the asm.**

**The finish line is byte-exact.  Full stop.**  A residue analysis
documents; it never finishes (Hard Rule #6).  The correct shape can
score worse on raw bytes (`show_people_query_panel`: binir 15/62 →
4/62 while bytes went 806 → 891 — keep the shape fix, then work the
next layer).  Wrong-shape bodies (a `void` dropping a real return, a
`sete` where PS branched) are open targets, never waypoints to bank —
do not revert a PS-faithful body to a wrong-but-smaller form.

---

## Command reference

Most commands take a function or file argument and accept `--json`.
This is the per-command reference; the workflow above says *when* to
use each.

### `c2 worklist` — the session entrypoint / dispatcher

See "Session start" above for the full description and knobs.

### `c2 diagnose <fn>` — the one-call triage (run FIRST on any diffing function)

Fuses the shape **concordance** verdict, the regalloc-invariant
**const-audit**, the **binir residue class**, the **run-ledger** (its
`divergent source lines` + `run-ledger:` sections), the **L4 slice
attribution** (from `c2 regalloc-verdict`'s layered model), the
**win-census** line, and the **trace verification** of the slice
against the live compile-phase trace (Score `sb`/`sbi`/`sbs` +
MergeIndex `mic`/`mip`/`mi`/`mir1..6` probes), tagged MATCH / ENRICH /
CONTRADICT / CONFIRMS-NOT.  `tie-reorder-pinned` marks functions where
the cascade said REACHABLE but the named pair has NO source handle —
**do not grind decl reorders on these** (for single-letter-named pairs
confidence is LOW; confirm against `regtrace`'s seat diff).
Concordance triage: HIGH + still diffing = shape right, residue is
regalloc (do NOT restructure); LOW = fix the shape first.

### `c2 dossier <fn>` — the focused first-divergence view (bisect mode)

One screen: PS asm + RC asm + RC source + Mac/Win oracle aligned to the
FIRST PS↔RC divergence, plus the delta vs git HEAD (`diff:` /
`first-diff:` / `shape:` rows — first-diff moving forward + shape
dropping are the two PS-faithfulness signals).  Re-run after each edit;
the working tree IS the state, commits are the bisect checkpoints.
Donor-blocked functions are flagged and re-routed.  Baseline cached per
(function, HEAD-SHA) in `.c2-cache/bisect/`; ~0.3 s clean-WT, ~5-10 s
dirty.  `--full` = the all-streams firehose (archeology mode).

### `c2 disasm <fn>` — PS.EXE asm with `L<N>` line numbers

The canonical disassembly with resolved symbols, fixups, and the `-d1`
line column (Hard Rule #4).

### `c2 decomp-verify` — the BYTE oracle (+ the asm diff)

The definition of "done" (0 bytes = byte-exact).  `-v -f <fn>` shows
the windowed PS-vs-RC asm diff + every hint header (table below).
Whole-file / corpus modes and `--json` for tooling; `--cflags` for flag
audits; `--target win` dispatches to the Windows byte oracle;
`--shape-divergence` is the whole-surface `-d1` trajectory map
(reccmp-based, ~0.5 s, reliable for byte-exact functions, approximate
for diffing ones).

```bash
uv run c2 decomp-verify decomp/src/formulae.c                      # whole file
uv run c2 decomp-verify decomp/src/formulae.c -f act_review_in_10 -v
uv run c2 decomp-verify --json --no-strict                         # corpus, one build
```

Default strict mode also runs the authentic final runnable link (the same
pipeline as `c2 rebuild`) and fails on non-debug code/data/layout differences,
including loader-fixup **target identity**.  This catches references to the
wrong global or string even when the instruction bytes at the fixup site are
otherwise identical.  `--no-strict` retains the historical fast per-function
oracle and does not build `build/PS.EXE`.  Strict mode attributes code-fixup
target defects to their containing functions in the initial per-TU listing;
`-v` expands each row with the PS and rebuild target names.

Output marks: `(silent)` exact · `~` exact with non-code artefact ·
`✗` genuine diff.  In `-v`: `+XXXX` byte offset, `LNNNN` PS line, `??`
fixup byte (masked), `[xx]` differing byte.

**Build cache**: the historical "rarely goes stale" bug was
root-caused and FIXED (2026-07-09): wmake runs inside dosemu, which
presents mtimes truncated to absolute 2-second DOS FAT buckets, and
wmake treats equal-as-up-to-date — an edit + re-verify landing in the
same bucket as the previous `.obj` silently skipped the recompile.
Staging (`_write_if_changed`) now bumps every changed file past its
`.obj`'s bucket (headers/makefile past ALL objs).  A dosemu-side fix is
impossible (the DOS INT 21h time format stores seconds/2 — finer
resolution is unrepresentable).  If a wrong diff count ever recurs:
`--no-cache` for that file to confirm, `rm .c2-cache/build/<file>.obj`
to fix (cold full rebuild is ~7-10 min).  **`c2 cache status`**
inventories every persistent cache with its keying + staleness
indicators; `c2 cache gc` prunes the trace store; `c2 cache clear
<name>` clears selectively (with cost warnings).

**Flag audit recipe**: run corpus-wide `--json` twice (baseline vs
`--cflags "<NEW FLAGS>"`) and diff the per-function dicts — ~30 s
total, vs ~10 min file-by-file.

### `c2 rebuild` / `c2 delink` / `c2 run` — the functional rebuild toolchain

Build the RUNNABLE game: `c2 rebuild` → `build/PS.EXE` (the authentic
1995 link: 44 FILE objs + `LIBRARY ail.lib, smack.lib, clib3r.lib`,
DOS/4GW-bound; no auto-stubbing — undefined externs are hard errors =
the recovery worklist), with an automatic per-symbol byte comparison
against `data/PS.EXE` (buckets game / c2-asm / av-delink / crt / data +
the layout-order metric).  `c2 delink` recovers the third-party OMF
objects and the reconstructed vendor archives from PS.EXE;
`c2 cd install … --full` + `c2 run` (default `--recompiled`,
`--original` for the shipped exe) launches the game.  Full usage,
output interpretation, and regression signatures: “The functional
rebuild toolchain” under Operational detail; mechanism docs in
`docs/delinking.md`.

### `c2 shape-recon <fn>` — the SHAPE lens (statement-level witnesses)

Fuses the PS `-d1` statement spine, binir IR per statement, and the
structurally-aligned Mac decompile into one statement skeleton, and
aligns your CURRENT source to flag `boundary` SPLIT/MERGE (the Hard
Rule #8 mis-transcription class, localised per statement — works on
*diffing* functions, where `line-compare` can't).  `--no-mac`/`--no-rc`
for a fast look; `--corpus` ranks targets; `--corpus --exact` is the
byte-exact self-check.  Its concordance verdict is what `c2 diagnose`
surfaces.  Design: `docs/shape-inference-witness-reconciliation.md`.

### `c2 mac-decompile <fn>` / `c2 mac-fn <fn>` — Mac source-shape oracle

Near-source C (or raw PPC disasm) from the Mac build — same source,
different compiler.  SLOW on first use (JVM ~25 s).

### `c2 win-decompile <fn>` — Windows source-shape oracle (the most legible)

Near-source C from `CAESAR2.EXE` (MSVC 4.0 `/Od` of the same engine
source; CRT byte-proven, `docs/windows-builds-fingerprint.md`).
Parameters named + typed, globals named (1079 mapped), every statement
explicit.  SLOW on first use (~60 s; disk-cached after).  The DB is
reproducible from the binary + committed files via `c2win.py`
(`data/windows-builds/ghidra-recreate.md`).

### `c2 win-verify <fn>` / `c2 decomp-verify --target win` — the Windows BYTE oracle

Builds the same source with MSVC 4.0 `/Od` and byte-compares against
`CAESAR2.EXE`; cache `.c2-cache/win-verify.json` (incremental).  Two
figures: `byte_diff` (oracle) and `struct_diff` (slot-shuffle-
insensitive, the workable figure).  `-v` shows the aligned asm.  Use
per Hard Rule #7: certify PS regalloc residues, read invented-locals /
decl-order / operand-order off the `/Od` frame.  `c2 functions <file>
--win` adds the dual census per TU (the PS-exact-but-win-diff list is
the shape-recovery worklist).  Caveats in Hard Rule #7.  Engine
`c2/win_bytes.py`; `docs/windows-dual-target-feasibility.md`.

### `c2 win-census <fn>` — the named-local census (W2 witness)

Compares our MSVC build's `[ebp-N]` slot set against `CAESAR2.EXE`'s,
gated by mapping quality Q (act on `usable`, Q ≥ 0.85).  `Δ > 0` = the
original declared MORE locals (the unmatched slot's width/uses identify
the expression to NAME — worked: `evolve_water_table` ir 7→5 after
24/24 decl permutations had failed; **permutations can never change the
temp SET; the census can**).  `Δ < 0` = our source INVENTED locals
(§13); inline them.  `Δ = 0` = set matches; check widths.  `--corpus`
ranks by |Δ|.  Port drift is real: every Δ is a CANDIDATE, adjudicated
by PS asm + `-d1` marks.

### `c2 regtrace <fn> --explain` — live allocator ground truth

Traces the REAL 10.0a allocator (instrumented compiler; see "The
instrumented compiler" below) and correlates it with the diff, naming
the exact lever (type-width / register-identity swap / outside
regalloc) + the value-aligned PS↔RC SEAT DIFF (which named VALUE sits
in a different register, and whether the tie is steerable).

The `--explain` seat diff now carries a per-swap **chain verdict**
(the certified seatchain flip analysis — same engine as `c2 seats`).

The conflict table's `CRM` column and the `our <reg> holds:` correlation
read the trace's RECORDED `reg_name` + `cand_scores` (ce/cq ground
truth), NOT the legacy `ins_walk` re-derivation (fixed 2026-07-13,
`_gb_pick_scores`).  The old model mis-scored move-elimination picks
(e.g. an arg-N value coalesced into arg-N's register), contradicting the
recorded seat AND the certified chain, and fed the correlation a wrong
value→reg map; the `greedy` column is the naive first-free candidate and
the `*` marks a genuine move-elimination/tie-break where the actual pick
differs from it.

HARD-bucket context: `docs/hard-bucket-survey-2026-06-24.md` catalogues
the five HARD classes; leads are **NAMED ≠ EXECUTABLE**.  The trace
also carries slot-allocation ground truth for the Rule 107 slot-swap
class (`nt_pre`/`nt_post`, `nb1`/`nb2`, `an`+`st`; validated 195/195 —
`docs/slot-swap-survey-2026-06-24.md`), diagnosed by the **ShellSort
sim** (`c2.regalloc.shellsort_sim`) into four classes surfaced in
`decomp-verify -v` / `dossier` / `worklist`: `shellsort-instability`
(simulator names the destabilising temps), `sort-stable-other`
(upstream of AssignTemps; open frontier), `sub-source`, `misbucketed`.
Slot-swap technique: read PS's slot order off `c2 disasm` `[esp+N]`
displacements, RC's off the trace, apply the named lever (hoist
inner-block local / swap decl lines / simulator-guided restructure).

### `c2 seats <fn>` — the certified full-chain seat dossier + flip search

The seat-class analog of the slot-sim (2026-07-11).  Every committed
conflict's register decision is RECOMPUTED from inputs — iv liveness
(`c2.regalloc.liveness`, 100%) → with.regs mask (`neighbours`, 100%) →
CountRegMoves scores with per-instruction credit provenance
(`crm10a_v2`, 100%) → GiveBestReg pick (100%); full-chain identity
6,243/6,243 on the certification sample.  For each PS↔RC seat swap
(seat_recon, or `--want VAR=REG`) it names the LEVER CLASS
authoritatively: `masked` (live-range lever, contributing walk rows
enumerated), `outscored` (the winner's credits named per ins —
de-CSE/de-name/reorder), `tie-order` (Rule 115/28a; cross-check
Byte-seat CASE D inertness), `vetoed` (savings), `not-a-candidate`
(type class → Rule 151 first).  Run it BEFORE grinding decl orders.
Surfaced compactly as the `Seat-chain:` hint in `decomp-verify -v` and
as per-swap chain verdicts in `c2 regtrace --explain`.
(2026-07-10: full-corpus certified — liveness 70k/70k, masks/scores/
picks 23,3k/23,3k, zero misses; the standing regression gate is
`docs/codegen-experiments/corpus-chain-certification.py`.)

**The masked-seat ACTUATOR STACK (2026-07-13)** — a `masked` verdict no
longer just says "live-range lever"; it NAMES the occupant and runs three
composable counterfactual replays to a VERIFIED lever verdict:

* **occupant attribution** (`mask_occupants`) — the `live_regs` with.regs
  substrate is a bare register bitmask with NO value identity, so it
  cannot say WHICH value holds the wanted reg.  This joins the ALLOCATED
  conflicts seated in `want` whose committed live range OVERLAPS the
  target's (by emission ordinal, **recycling-proof** — wcc386 recycles
  name ptrs via AllocFrl, so the iv-snapshot name-ptr method
  mis-attributes a coalesced self-move as a "pinned arg").  `commit_ins_
  range` is a convex HULL, so if two conflicts are both seated in `want`
  their true ranges are disjoint → the wide-hull one is a false positive;
  the genuine competitor is the equal-rank, tightly-overlapping one.
  Classes: **blocker** (higher-savings overlapper), **tie** (equal-rank
  ConfBefore competitor), **pinned** (held in EXACTLY `want` = an ABI/
  hard-reg fixed placement, no overlapping conflict).
* **birth-order actuator** (`birth_order_flip`) — equal-savings ties are
  resolved by the unstable ShellSort over ConfList = reverse creation
  order (`sort.py`).  It moves the target to EVERY position in its
  savings tie group and replays the pick cascade: `reorder-REACHABLE`
  (a create-order lands `want` → last-use motion, Rule 115/28a) vs
  `reorder-INERT` (`want` stays masked at every position → a
  higher-savings neighbour holds it at baseline, always allocated first;
  NO reorder wins).
* **live-range actuator** (`live_range_flip`, the P5 counterfactual) —
  clears `want` from the target's baseline mask (blocker's range
  shortened so it no longer covers this value), recomputes crm10a_v2
  scores for the newly-unmasked candidate, and replays: `lr-REACHABLE`
  (shorten the blocker → seats it), `lr+credit` (freed but still
  OUTSCORED by a credit), or `lr-INERT`.
* **credit actuator** (`credit_flip`) — models the de-CSE/de-name edit:
  perturbs the winner's cand_scores by its per-ins CountRegMoves credit
  (the crediting ins named from the `cq` provenance) ON TOP of the
  live-range graph, replays.  Composing live-range + credit yields
  **`composite-REACHABLE`** — shorten the blocker AND kill the winner's
  credit at ins X → seats `want`, verified end-to-end, both halves named.

All auto-run inside `flip_analysis` (chained masked → birth-order →
live-range → credit) and surfaced: `c2 seats <fn>` (no `--want`)
auto-picks the localized first-divergence's best-guess row (named-local
baseline blocker fingerprint); `--want VAR=REG` pins it; `--json`
carries the full `birth_order`/`live_range` chain per flip.  Corpus (0
errors): 1,155 `composite-REACHABLE`, 987 `lr-REACHABLE`, and 81
birth-order-REACHABLE seats are now nameable levers that the old
"live-range lever" blanket verdict misrouted.  These are MODELS — the
named lever + ins are a hypothesis to byte-verify, not a proven close
(a fully-packed allocation may have no byte-neutral realization of the
named composite).

### `c2 savings <fn>` — the CalcSavings forward model: dossier, per-ref ledger, grounded flip search

The P1 prediction-stack surface (2026-07-10; engine
`c2/regalloc/savings.py`, certified **20,432/20,432 exact, zero
misses** against the recorded `cv`/`al` ground truth on the
2026-07-10g trace image).  Savings drive THREE allocator decisions
(the ConfBefore sort order, TooGreedy, WorthProlog); this makes them
DERIVED from the IL instead of merely recorded:

* **`c2 savings <fn>`** — per conflict, recorded vs forward-computed
  savings.  A `!!` MISMATCH is a new mechanism — report it, don't
  shrug; `GAP` rows are substrate-vintage (round>0 / snapshot
  pos-miss), not model errors.
* **`c2 savings <fn> --var X`** — the per-REF ledger: every unit of
  X's savings named to (block, depth, ins, ref kind, weighted units).
  Turns a Cascade "needs a SAVINGS change / REMOVE ~2 uses" verdict
  into a named lever list (worked: place_sprite's `side` sav=8 =
  parm-capture def 2u + SIX depth-0 compare uses).
* **`c2 savings <fn> --flip VAR=REG [--depth 2]`** — the ACTUATOR
  (`c2/regalloc/savings_flip.py`): enumerates source-grounded edits
  in THREE families — savings (delete THIS ledger ref / add a
  re-read in THIS block), and **credit kills** (a `[score]`-decided
  seat holds via a CountRegMoves credit at a NAMED ins; the
  de-CSE/de-name edit there is modeled as a cand_scores
  perturbation) — and replays each through the certified chain (P1
  savings → ConfBefore ShellSort → `replay_order`'s full pick
  cascade with order-evolving masks, **modeled P2 TooGreedy verdicts**
  for newly unmasked candidates, and a **WorthProlog gate** on
  counterfactual callee-save picks), reporting flips WITH their
  side-effect re-seats — every side effect must match a PS seat for
  the edit to be right.  `--depth 2` composes pairs (movers-first,
  capped).  Worked to closure same-day: show_left/right_overlay
  177bd → 0 each (b2e2a8ad) from the named +1-use lever.  Honest
  negative: "NO grounded savings edit" = the lever is outside the
  order/credit classes — usually the **masked** (live-range) family.
  That family IS now modeled by the `c2 seats` actuator stack
  (2026-07-13: birth_order_flip / live_range_flip / credit_flip — see
  its command entry); route a "NO grounded savings edit" masked seat
  there for the named blocker + composite lever.  Caveats: identity-vintage live/zap under
  reorder (P5's job); deletion candidates assume the ref's removal is
  savings-local; the byte compile stays the oracle.

### `c2 spell <fn> [candidate.c]` — trace-level spelling screener + generator (no byte compile)

**THE tool for any rover / walk-order / IL-birth / chain-structure
residue** — the consumer of the trace's walk + birth records
(`lw`/`lc`/`lcx`/`cw`/`bo`/`ni`; engine `c2/regalloc/lwalk.py`).  Four
modes:

* **`c2 spell <fn> <candidate.c>`** — the STAGED spelling localizer:
  traces the working-tree TU and the candidate TU and reports where the
  source distinction DIES, across the full ladder **tree → block births
  (bo) → IL births (ni) → walk (lw)** — `INERT@TREE` (parser
  canonicalized it away; the family is PROVABLY unreachable, stop),
  `INERT@BURN` refined by the birth lines (identical IL births =
  canonicalized AT emission, deepest inert; diverged births + identical
  walk = a post-emission pass re-converged it — siblings at the printed
  delta lines may survive), or `LIVE` (walk differs + the per-class
  advance DELTA; byte-compile these first).  **Measured calibration**
  (2026-07-09 audit, 109 byte-compiled fold/unfold candidates on
  byte-exact functions —
  `docs/codegen-experiments/spell-verdict-audit.py`): LIVE→byte-change
  precision 0.93; INERT@BURN→neutral precision 0.83 — the walk lens is
  blind to conflict-graph/savings changes upstream of LdStAlloc
  (false-negative signature: diverged IL births + identical walk), so
  INERT@BURN means DEPRIORITIZE, not proven dead.  The audit also
  caught + fixed a routine-matching bug that had made every observed
  INERT@TREE verdict false (10/13 moved bytes); post-fix INERT@TREE is
  again the only stop verdict.
* **`c2 spell <fn> --suggest [--lines 410,422] [--no-screen]`** —
  GENERATE the census's fold (de-invent) / unfold (cache-field)
  candidates PLUS the Rule 121 structural tail-dup / tail-hoist
  candidates (shared tail ↔ per-arm copies, both directions,
  control-flow-neutral by construction; the dup-with-CALL variants are
  the rover walk-entry lever, tagged `call` vs `stmt-only`) as real TU
  files (forge's hazard-checked span machinery) and screen each one;
  files land in `.c2-cache/spell-cands/<fn>/` for direct byte
  compiles.  Paste the Rover hint's `[lw census]` lines into `--lines`
  for a targeted run.
* **`c2 spell <fn> --fusion`** — the fr→lc/lcx map (every RISCified
  pair resolved to fused or a NAMED rejection) plus the **compress
  attempts × chain block** (`cw`): each attempt's pair-scan kinds —
  `pk/nk = 3` recognized MOV half, `0x1NN` = ins opcode NN between the
  halves, `0x14b` = BLOCK HEADER (chain-separated even when the final
  layout is byte-adjacent — the kept-split lens).
* **`c2 spell <fn> --chain`** — the chain-placement report: blocks in
  chain order with call/Rule-125 tags, plus every conflict's ACTUAL
  CountRegMoves scan (`own_walk` ground truth) checked for op54 rows
  with physical registers — each is an EAX credit source via the
  crm10a_v2 NULL==NULL quirk (calls AND far-returns; only SCORED
  candidates are affected — a mask-skipped EAX never sees the credit,
  so read this WITH `c2 seats`' mask rows).  Root-cause lens for
  `outscored`-verdict seats whose credit ins is a call/return
  (discovered on start_samples — see its pcsound.c ledger).
* **`c2 spell <fn> --seat-flip VAR=REG`** — the P6c counterfactual: 're-seat
  conflict VAR to REG' replayed through the certified rover (except-bit
  attribution 12,106/12,119 corpus-certified, gate #9b), reporting the
  ROVER PICKS that change.  Screens which allocator flip lands a wanted
  scratch pick BEFORE hunting its source lever (`c2 seats`/`c2 savings
  --flip` name the lever for the flip itself).  Engine:
  `c2.regalloc.rover.seat_flip_walk`; the byte compile stays the oracle.
* **`c2 spell <fn> --walk-order`** — the walk-vs-layout block map with
  **birth ordinals** (else-if arms are walked in REVERSE source order;
  `<<< moved` rows + out-of-order births = optimizer restructure;
  opt-born merge blocks flagged) **and the `mfg#` chain vintage**
  (≥ 2026-07-13 image): the post-MakeFlowGraph chain position per
  block + a haul-attribution summary (blocks moved by MakeFlowGraph's
  DFS/RPO relink / ReturnsToBottom vs a LATER pass).  br ptrs are
  LdStAlloc-stable where bo ptrs are not (big functions rebuild the
  block set after birth — `birth#opt` everywhere on action).

Before designing a STRUCTURAL variant, consult the **construct →
block-birth dictionary** (watcom10.0a `docs/block-birth-dictionary.md`):
labels add a walk-invisible birth; `&&`/`||`/nested-if are
birth-identical; loop forms have distinct signatures; byte-class rover
advances come from byte const stores + byte RMW (the naming/inlining
lever).  The same engine feeds the `Rover:` hint's `[lw census: ...]`
line (see the hint table).  Requires the trace image (auto-invalidated
caches via image-ID keying).

### `c2 sweep <fn>` — iterated forge-preset byte-oracle sweep

Greedy coordinate descent over the mechanical lever space: generates
the full forge preset battery (~200-700 variants: decl swaps/perms,
statement reorders, commutes, RMW forms, de-invent/cache, if-inverts,
line splits, Rule 121 tail-dup/tail-hoist), byte-compiles EVERY variant on the ForgeBuilder LE fast
path (~0.1 s each), judges shape-first (Hard Rule #3), takes the
winner as the new baseline and repeats (default 3 passes).  COMPOSED
edits that single-pass hand-probing never reaches are exactly what
closed `evolve_region` (two decl swaps, 56→6→0 — ad1de9e7) after the
class had been written off.  Never touches the tree: the winner lands
in `.c2-cache/sweep/<fn>/best.c` + a printed diff (re-derive on fresh
disk before applying; a parallel session may have moved the file).
Use AFTER the shape is right (seat/slot/rover residues, `worklist`
decl-order/tie levers); NOT for ir-dominant wrong shapes.  Caveat: a
shape drop can be a FALSE improvement when Rule 49b/151 contradicts it
(top_it's cast-vs-mask trade) — read the `-v` hints on the applied
result before committing.

### `c2 ledger <fn>` — the dual `-d1` run ledger (statement-level islands)

THE tool for a big still-diffing function.  Segments PS by ITS `-d1`
marks and RC by OURS (attribution-exact at any size), aligns the
register-blind streams, and prints each divergence island with PS asm
(the target shape), our source line (the edit target) and a family tag
(`width`/`zext-idiom` → Rules 49/151; `signedness`; `loop-form` →
Rule 134/93; `slot`/`frame` → Rule 107, work LAST; `const`; `ops`).
`regalloc_pure` = zero islands → `c2 regtrace`, never restructure.
Feeds the `ir` layer of `shape_distance`.  `docs/run-ledger.md`.

### `c2 loops <fn>` — loop classifier from PS.EXE bytes

Classifies every back-edge (`for` / `while` / `do_while` / `infinite` /
`loop_insn` / byte-ambiguous).  99.06% kind agreement on the byte-exact
corpus.  Also the `Loops:` header in `decomp-verify -v`.

### `c2 line-compare <fn>` — PS-vs-RC line-stream comparator

Hard Rule #8.  Run after every byte-exact win; `--offenders` for the
corpus scan.

### `c2 sibling` — nearest byte-exact template + structural twin

Two lenses over one cached corpus (`.c2-cache/sibling-corpus.pkl`;
warm queries sub-second):

* **Shingle (default)** — fuzzy whole-body ASM match: a verified
  C-source TEMPLATE for a diffing/un-decompiled function.  `--status
  any` widens past byte-exact; `--submatch` shows which insn ranges
  align; `--all --min-score 0.30` corpus-wide.
* **Structural (`--structure` / `--survey`)** — matches the prologue
  signature (callee-save pushes, frame size, arg count) + opening
  instruction shapes.  A *diagnosis*: no byte-exact twin with your
  frame = the source reserves the wrong stack; an unrelated cross-family
  twin = your shape is right, the residue is downstream regalloc.
  `c2 sibling --survey` partitions the whole diff corpus (start on the
  A cohort = wrong stack frame).

`docs/structure-twin-survey-2026-06-17.md`; library entry points in
`c2.commands.sibling`.

### `c2 xrefs <symbol> [--field 0xN]` — who calls / reads / writes

### `c2 stubs [--donors]` — Phase 1/2 target pickers

Ranks STUBs by caller count, or by tail-merge dependents (`--donors`,
typically 2-15× multiplier).

### `c2 inferred-sig <fn> [--all --stubs]` / `c2 callgraph --check` / `c2 sig-drift`

Prototype tooling (Phase 1): infer the real `__watcall` signature from
PS asm; scan project-wide prototype mismatches that change CallZap;
find per-TU declaration drift.

### `c2 baseline save|check baselines/<name>.json` — corpus snapshot

Before any large refactor: `save`.  After: `check` (non-zero exit on
regressions).

### `c2 forge` — the automatic source-shape solver

`solve` / `report` / `diff` / `exp` / `levers`.  `c2 forge solve <fn>`
beam-searches with the win-mirror lever battery (tree-sitter spans,
DecisionMatrix judge over the same layered `shape_distance`,
stop-at-exact; search tree persisted to `.c2-cache/forge-runs/`).
Validated by re-deriving setup_roman_units' byte-exact autonomously.
**Honest limits** (2026-07): on the residual corpus forge solves have
been NEUTRAL — the remaining residues are intra-statement,
sub-source, or trace-level (rover/IL-birth) where inter-statement
reordering cannot reach; a neutral solve is itself information
(classified residue; check `report` for pareto near-misses).  Prefer
the trace-first workflow (`Rover:` census, `c2 spell`) for rover-class
residues; forge remains useful for new/wrong-shape functions and the
`boundary` lever (const-audit's off-by-one candidates; semantic-
changing, opt-in).  Do NOT forge a Byte-seat CASE D (Rule 133 inert
byte tie — provably dead lever).  `c2 forge exp --new <slug>` scaffolds
authored experiments (`docs/codegen-experiments/<slug>.py`; legacy
archive at `_legacy/`).  Never filter a live solve (Hard Rule #5).

### `c2 decompile` — parallel subagent runs

Spawns N pydantic-ai subagents, one per function, each driving the full
per-function loop in a sandboxed working directory with typed tools
(`read`/`write`/`edit`/`verify`/`revert_to_best`/`disasm`/`decompile`/
`info`/`nearest`/`fetch`/`lookup`/`regtrace`/`census`/`lines`/`search`
plus the trace-level spelling suite — **`spell`** (screen the current
edit against the best snapshot across the tree→births→walk ladder, no
byte compile), **`suggest`** (generate + screen fold/unfold candidates
into `cands/`), **`fusion`** and **`walk_order`** (rover fuse fates +
chain-structure diagnosis)) and a typed `FinishReport` verdict.

```
c2 decompile SELECTOR [SELECTOR …]     # function name(s) or file(s)
  --batch N | --model M | --max-turns N | --time-budget S
  --apply/--no-apply (default ON) | --trace (100% local OTel)
  --dry-run | --jsonl
```

Credentials: `.env` (see `.env.example`).  Caveats: each subagent
verifies `scratch.c` as a STANDALONE TU (re-run `c2 decomp-verify -f`
after a win to confirm it generalises); tail-merge-BLOCKED functions
are filtered out; tracing is hardened local-only
(`c2/decompile/tracing.py`).

### `c2 tempbirths <fn>` — the attributed Names[N_TEMP] table (Rule 107 drill-in)

The slot chain is fully modeled and corpus-validated (births 1137/1137,
nb1→nb2 1137/1137, nt sort 1224/1224, an order 138/138 —
`c2/regalloc/shellsort_sim_slots.py::validate_routine_chain`):
source → AllocName births (PREPEND; TempId@0x7f8f0 == loc24) →
BuildNameConflicts sort → AssignTemps sort → `[esp+N]`.  `tempbirths`
prints every nt entry with var/size/usage/FE-line and the CREATING PASS
(`nbc`/`nbo` probe attribution), so a slot-swap lever search names the
source construct to move instead of grinding decls.  The `Slot-swap:`
hint runs the flip search (adjacent swaps + insert windows + removals)
automatically.  Requires the ≥ 2026-07-10 trace image.

### `c2 dispatch-hints` / `c2 frame-hints` / `c2 pragma-hints` / `c2 const-audit` / `c2 const-drift` / `c2 residue-cluster` / `c2 negative-corpus` / …

Single-purpose triagers; all surface as headers in `decomp-verify -v`.
`c2 <cmd> --help`.

---

## Key hint lines in `decomp-verify -v` output

| Header | Meaning |
|---|---|
| `Rule hints:` | per-row pattern matches (Rules 4–155).  Check Rule 151/152 first. |
| `Regalloc:` | model layer (0–6) + lever, or "outside the model." |
| `Rover:` | RISCify rover divergence.  Often a DOWNSTREAM SYMPTOM — check Rules 151/152 first.  Carries, in order of strength: the trace-CONFIRMED single inject (self-heals); the **`Rover-fit (influence-window solver)`** block — divergent picks decoupled into influence-independent groups (composed masked-advance maps; beware partial absorption: a +1 can die where a +2 survives) with each group's minimal ±op requirement and its **`[lw census: ...]`** candidate map (foldable loads by line / RISCified −1 ops / kind-flip-free → IL-birth/walk-order class); and the refined advance model (see "The RISCify rover" below). |
| `Rover-closeable:` / `Rover-blocked:` | offline closeability verdict, CompressIns-aware; closeable sites carry a per-gap `[lw census]` line.  A blocked verdict carries the `[br: N hauled by MakeFlowGraph …]` chain-provenance (≥ 2026-07-13 image) — drill-in `c2 spell <fn> --walk-order` (the `mfg#` vintage column). |
| `Tail-merge:` | donor + epilogue chain; the `-v` diff splices the borrowed epilogue back onto both sides under a `── merged epilogue tail ──` banner. |
| `Frame:` | prologue `sub esp` delta (PS vs RC stack frame). |
| `Rule 151:` | `int` vs `short` local (movsx/cwde mismatch).  Fires bidirectionally. |
| `Rule 152:` | explicit `else if (var == K)` vs bare `else`.  PS-only `cmp reg, K; jcc` delete pair.  (Historically the dominant class — 59% of remaining diff bytes in mid-2026; largely burned down since.) |
| `Sibling:` | top-3 byte-exact siblings ≥ 30% containment — `c2 sibling <fn>`. |
| `Byte-seat:` | one verdict per `Byte-reg swap` row, proven against the 10.0a binary (`GiveBestReg` tie-break VA 0x57ca1).  CASE **A** = collateral to a 32-bit `Reg swap` (reorderable — Rule 28a/115/123); **A2** = occupancy-pinned anon byte tie (Rule 161 — every swap byte conflict is anonymous; seat = first non-excluded byte reg in list order, exclusions from overlapping anon byte ranges; reorders provably futile, temp-SET levers only, `spell --suggest` empty ⇒ certified); **B** = AL-squat masking (Rule 126 — int-widen); **C** = rover-seated CSE (Rule 127 — de-name); **D** = inert byte tie (Rule 133 — list-order seats it; reordering is provably futile — deprioritize, but a missing-rule frontier, not a proven floor). |
| `Loops:` | loop classification per back-edge. |
| `Cross-build:` | per-build status (exact in rel-1995-10 / rel-1995-09 etc.). |
| `binir-shape:` | IR-level match/mismatch.  "all IDENTICAL IR" = pure regalloc/encoding noise. |
| `Neg-corpus:` | size-controlled un-PS-like source shapes (anti-rule joins). |
| `Spill-class:` | Rule 111 spill-vs-hold differential. |
| `Moved-code:` | Rule 125 hauled bodies (define-position ≠ symbol-address order). |
| `Rule 116:` | reload-vs-hold marker (delete the named local, inline the global). |
| `Rule 117:` | prologue frame-size delta. |
| `De-invent (Rule 129 / §10):` / `Add an intermediate:` | caching-mismatch, both directions, AST-named.  **De-invent**: PS re-reads global `G` N× (BlockByBlock — no cross-block CSE) but the source caches it in local `v` → delete `v` (`edit_format_buffer` 207→0).  **Add**: source reads `G` directly many times but PS caches it in a callee-save → introduce `T v = G;`.  Surfaced in both `decomp-verify -v` and `shape-recon`. |
| `Invented temp:` | §10 de-invent, register-walk variant: an RC-only intra-pair copy duplicating a value already live — delete the `temp = x;` copy (`clear_sized_to_rubble` 416→0). |
| `Const-drift:` | the `cmp`/`test` comparison constants differ from PS — a wrong threshold / dispatch literal (get_census 602→119). |
| `Const-audit:` | regalloc-INVARIANT wrong-constant / off-by-one boundary check (multiset compare across cmp-boundary / eq / plain channels; CLEAN on all byte-exact functions; localizes each divergent literal to its offset + `-d1` line).  Standalone: `c2 const-audit <fn>` / `--corpus`. |
| `Arg-swap:` | out-of-order parameter — a constant lands in a DIFFERENT `__watcall` arg register.  A definite semantic bug, regalloc-invariant, HIGHEST-priority source lever.  Part of const-audit. |
| `Slot-swap:` | Rule 107 same-size spill-slot swap + the ShellSort sim verdict (see `c2 regtrace`).  Since 2026-07-10 the sim's FLIP SEARCH runs live against the PS slot order derived from the diff: it prints the single-adjacent input swaps, the single-INSERT windows (one fresh sz1/sz4 temp at nt[j] flips to PS's order) and single REMOVALS -- each with the temp's BIRTH attribution (SAllocUserTemp = named local; FlowOut = bool-valued expr; CondConstStores2Bool = if/else const stores differing by 1; BGNewTemp = tree burn; CallParmTemp; ReduceSplit).  Drill-in: `c2 tempbirths <fn>`. |
| `Seat-chain:` | the CERTIFIED full-chain flip verdict per PS↔RC seat swap (masks+scores+pick recomputed from inputs).  Verdict = the lever class: masked / outscored / tie-order / vetoed / not-a-candidate.  A `masked` seat is refined by the actuator stack (2026-07-13, see `c2 seats`): **`masked-blocker`** (a higher-savings overlapper holds the reg — shorten ITS range), **`masked-pinned`** (an ABI/hard-reg fixed placement — no reorder frees it, sub-source), **`masked-composite`** (VERIFIED: shorten the blocker AND kill the winner's credit at the named ins → seats it).  Authoritative over the savings-tie heuristics; drill-in `c2 seats <fn>`.  LOCALIZED divergences: the row picker ranks by named-local baseline blocker to land the real diffing seat; the Cascade's rover/scratch verdict still wins where it fires. |
| `Branch-target audit:` | fires on a function whose masked compare is EXACT but whose masked rel-branch displacement fields resolve to DIFFERENT symbols/offsets (wrong callee, or a different ComTail merge point that includes/excludes whole call statements — the `act_set_patrol_stop` spurious-`save_undo_info` class).  Counted as ✗ diff; sites list resolved PS→/RC→ targets.  End-to-end twin: `c2 rebuild`'s `strict` line (whole code object, loader fixups masked, rel branches visible). |
| `Parm-reload:` | a checked global passed as a call arg → Watcom reloads it for the push (an extra rover advance).  Lever: cache through a temp AFTER the guard (proven: link_to_smacker) — but verify against bytes; heavy-use temps regress (setup_enemy_units 324→1190). |

---

## The knowledge base

### Codegen pattern catalogue

**`docs/watcom-codegen-patterns.md`** — the running catalogue of every
Watcom 10.0a quirk learned by matching PS.EXE byte-for-byte (155+
numbered rules).  Each rule documents the asm pattern, what to write in
C, what the obvious form emits instead, and the discovery commit.  When
you discover a new pattern, **add it and bump the rule counter**, then
reference the rule number in the commit message.

### The 7-layer register-allocation model (read this for ANY register diff)

The 10.0a allocator is fully reverse-engineered and proven —
**`docs/wcc386-re/regalloc-model.md`** is canonical.  The layers:

0. **TYPE** → register class (`int`/ptr = `DoubleRegs
   EAX,EDX,EBX,ECX,ESI,EDI,EBP`; `short` = WordRegs; `char` = byte regs).
1. **EAX-boundary** — a value lives in EAX **iff** its range never
   crosses a `call`/`mul`/`div`.
2. **SAVINGS** — `savings = Σ(uses·1+defs·1)·W^depth − Σ(spills·2)·W^depth`,
   **W=10** per loop nesting level; a callee-save reg is worth it once
   savings > 2 (≈3 straight-line uses, or 1 loop use = 10).
3. **TIE-BREAK on equal savings** — deterministic.  Lever 1 (Rule 28a):
   commute / move a use.  Lever 2 (Rule 115): swap the tied locals'
   decl lines (direction NOT monotonic).  `register`/`auto` keywords
   are inert; only declaration *order* moves bytes.
4. **OVERRIDES** — hard constraints (var shift→ECX, `idiv`→EAX:EDX) +
   move-elim (arg-N values placed in arg-N's reg).
5. **LOOPS** — invariant globals hoist unless a call or aliasing store
   in the loop could modify them.  **Never use `-oa`.**
6. **CAPACITY** — 7 GP regs; 6 across a call; beyond that, spill.

`decomp-verify -v`'s `Regalloc:` header classifies each divergence into
a layer + lever — or says the diff is OUTSIDE the regalloc model
(instruction-selection / tail-merge / branch-encoding; don't chase
registers).

### The RISCify rover (memory-op-heavy diffs)

A large diff class where the IR is identical and `Regalloc:` says the
layout matches — yet bytes differ — is the **RISCify rover**: a
scratch-register picker (`FindRegister`) running post-RegAlloc over the
IL ops that LdStAlloc RISCifies.  Diagnostic priority when `Rover:`
fires: (1) Rule 151 type width, (2) Rule 152 missing else-if, (3) the
`-d1` line read + Mac oracle, (4) only then the rover lever.

**What advances the cursor** (lw-probe-refined, 2026-07-09): a
SPLIT-OUT memory operand (a cmp/test/arith op reading memory directly —
Enregister splits it into rover-load + reg-op) or a const store to
memory.  Plain `mov reg,[mem]` loads NEVER advance, nor do reg-only
ops, converts, or calls.  Therefore the **±1 lever is load-folding**:
rewrite `x = g; … x OP k` so the consumer reads `g` INLINE (+1
advance); the −1 lever is the reverse (name the temp).  **Measured
calibration** (2026-07-09 gauge inventory, 532 byte-compiled
candidates on the exact corpus —
`docs/codegen-experiments/rover-gauge-inventory.py`): the fold's own
site compiles identically only ~35% of the time — BYTE-SCREEN every
candidate (~0.1 s via the sweep harness); downstream-only rotators
exist in every advance class AND as zero-delta walk reorders, so the
window-lever menu is broader than in-window foldable loads.  For
the **byte class** (8-wide rotation), advances come from byte const
stores and byte RMW on memory (byte COMPARES widen to dword — no
advance); the byte ±1 lever is RMW naming/inlining (`t=g;t+=1;g=t` ↔
`g+=1`).  The
`Rover:` hint enumerates candidates per window (`[lw census: ...]`);
`c2 spell` screens spellings without byte compiles; a **kind-flip-free**
census routes the function to the IL-birth / walk-order class (walked
else-if arms are in REVERSE source order — `c2 spell --walk-order`).
The **fusion map** (`c2 spell --fusion`) resolves each RISCified pair
to fused or a named `lcx` reject — `lcx0` (pair separated) is the
fingerprint behind byte-level "hoists" like the pm_map3 `mov ebp,0xf`
family; `--fusion` also prints each compress attempt's pair-scan
context (`cw` × chain block — the chain-separation lens).  The
compress (LdStCompress) runs ONCE, LAST in PostOptimize (gates:
OptForSize ≤ 50, cpu ≥ 4).  **Duplicated-tail (Rule 121) refinement
(2026-07-10)**: a statement-only tail dup (`add; continue;` per arm) is
re-merged BEFORE the walk (spell INERT@BURN — the advance never lands);
include the arm's CALL in the dup and it SURVIVES to the walk (spell
LIVE with the exact delta).  Byte-safety follows PS's witnessed layout:
merged-dup form (jmp carries its own `-d1` mark) → lever closes
(mid3_line_no_sides_base, 15cd1284); cross-arm goto/shared-tail (jmp
unmarked) → ComTail builds a NEW merge point and regresses
(show_battlemap_base).  Full detail: Rule 121's refinement section.
For structural (block-level) levers,
consult the **construct → block-birth dictionary** (watcom10.0a
`docs/block-birth-dictionary.md`): labels add a walk-invisible birth;
`&&`/`||`/nested-if are birth-identical; loop forms have distinct
signatures.  Full mechanism: the watcom10.0a repo's
`docs/rover-model.md`.

### The instrumented compiler (the `~WV1` trace)

`c2 regtrace`, `c2 spell`, the ShellSort/slot machinery, and the
Rover/lw hints are all fed by an instrumented wcc386 10.0a (the
`watcom-10.0a-wibo-trace` image), built by the sibling repo
`~/git/ReverseEngineering/watcom10.0a`:

* **Probes** live in `tools/patch_trace.py` (the single re-applyable
  source of truth; every hook documents its VA, register state, and RE
  evidence).  Rebuild: `scripts/build-trace-image.sh` (includes a
  byte-identity gate — the traced compiler produces identical .obj).
* **The rover is forward-calculated too** (2026-07-13): the fr
  record's except-mask components (`zap`/`live`/`resreg`; `except ==
  zap|live|resreg` certified 12,119/12,119) + the `br`/`bre` post-
  MakeFlowGraph chain+edge snapshot feed `c2/regalloc/rover.py` —
  FindRegister picks certified **12,025/12,025** corpus-wide (gate #9);
  `counterfactual_walk()`/`seat_flip_walk()` replay the cursor under
  hypothetical re-seatings (gate #9b), and **`predict_chain()`
  reproduces MakeFlowGraph offline** (DFS/RPO + interval reorder +
  ReturnsToBottom; gate #9c, **1,450/1,450 chains**) — walk-order
  levers are searchable without a compile: perturb edges/blocks,
  re-run, read the new walk.
* **The full seat chain is forward-calculated** (2026-07-11): the
  `ce`/`cq` probes (CountRegMoves entry + per-contribution credits),
  the `bs`/`be`/`iv` full-IL liveness snapshot (RegAlloc 0x584b9,
  one-vintage, with the flow graph), and the extended `gi`/`wr`
  records feed certified offline ports — `liveness.py` (FlowConflicts,
  100%), `neighbours.py` (with.regs, 100%), `replay.crm10a_v2`
  (scores, 100%), `seatchain.py` (identity 6,243/6,243).  Consumers:
  `c2 seats`, the `Seat-chain:` hint, regtrace's chain verdicts.  The
  same `replay.replay_order` (masks evolve with allocation order) powers
  the `seatchain.py` masked-seat ACTUATOR stack — `birth_order_flip`
  (create-order tie), `live_range_flip` (interference counterfactual via
  the `iv` snapshot's per-ins res_reg/emission-ordinal ranges), and
  `credit_flip` (de-CSE/de-name via the `cq` credit provenance) — which
  chain to the VERIFIED composite lever (see `c2 seats`).
* **Analyses** live HERE in c2 (`c2/regalloc/trace.py` parses the
  records; `c2/regalloc/lwalk.py` is the walk library) — if a session
  needs an analysis it cannot reach through c2, extend c2, don't grow
  a standalone script there (`watcom10.0a tools/README.md` documents
  the division).
* Record schema: `patch_trace.py`'s module docstring.  Mechanism docs:
  the watcom repo's `docs/` (rover-model, regalloc-mechanics,
  score-redundant-load-and-mergeindex, …).  **Cache discipline**: the
  trace disk cache is keyed by content + flags + headers +
  `_CACHE_VERSION` + the **trace image ID** (auto-read from podman,
  2026-07-09) — a rebuilt image auto-invalidates all cached traces, so
  adding probes needs NO manual bump; bump `_CACHE_VERSION` only for
  PARSER-side schema changes (new fields extracted from existing
  records).  `c2 cache status` / `gc` / `clear` manage all persistent
  caches (the trace store grows to tens of GB apparent; entries carry a
  stamp so gc prunes orphaned key-spaces precisely).

### Auto-solvers: almost never; hand-edit from the diagnostics

The broad auto-solvers (`c2 solve`, `regtrace --solve`, `decl-swap`,
`rover-solve`, `permute`, `cgex`) were REMOVED (2026-06): they almost
never closed a diff.  The working method is: read `decomp-verify -v` +
`regtrace`'s named seat diff + the rule catalogue, hand-edit, verify
each change.  `c2 forge` survives (see its command entry for honest
limits); `c2 spell` screens rover-class spellings.

### Compiler flags (proven settled — do not chase)

The canonical flag set lives in `decomp_verify.PS_CFLAGS`:

```
-bt=dos -mf -4r -s -d1      (Watcom 10.0a, default OptSize=50, unsigned char)
```

Every command imports this constant; do **not** hardcode a flag string.
Each token is proven by an unconfounded fingerprint:

| Flag | Meaning | Unconfounded proof |
|---|---|---|
| `-bt=dos` | DOS/4GW LE target | binary format |
| `-mf` | flat memory model | flat 32-bit pointers, single code/data objects |
| `-4r` | 486 register calling (`__watcall`) | `xor ah,ah; mov [m],ah` literal-zero byte store (8-byte form, `-4/-5/-6` only) |
| `-s` | no stack-overflow checks | no `__STK` probe prologues |
| `-d1` | line-number debug info | `symbols.json` `has_lines=true`, `has_locals=false`; `-d1` does NOT change code bytes |
| default `OptSize=50` | no `-os`/`-ot` | strength-reduction ratio `shl/(shl+imul)=0.59` matches 50; ComTail active at 50 |
| default unsigned `char` | no `-j` | **cross-build proven**: a bare-`char` string read is zero-extended in PS.EXE but sign-extended on Mac/Win — only Watcom's unsigned default fits both (`docs/char-signedness-proof.md`) |
| inline 387 | `-fpi87` is the `-4r` default | 4769 `D8`-`DF` bytes; `-fp*` flags byte-identical |

Historical sub-flag audits (all NOT used: `-oa` +230 diffs, `-oe` +39,
`-oi` regresses 7 lib32 fns with zero improvements, `-or` +210; `-ol`
possibly-used but net-neutral; no `-d2` — it forces `-od`): full tables
in git history of this file and `decomp/docs/watcom-10.0a-flags.md`
(the canonical wcc386/wlink flag reference for the ACTUAL 10.0a
container — do not trust modern Open Watcom v2 docs).  Re-dump flag
lists: `yes "" | podman run --rm -i watcom-10.0a-dosemu2 wcc386`.

### Watcom internals — Open Watcom source + the 10.0a binary

For *how an algorithm works* (codegen, tail-merge, regalloc,
scheduling, encoding, CRT, linker), read the vendored Open Watcom
source at `vendor/open-watcom/` (gitignored; `bld/...` citations
resolve there; searchable via semble).  **It is a HINT, not ground
truth** — the 2002 snapshot is ~7 years newer than 10.0a and the
codegen changed.  Ground truth for 10.0a is established only by
reverse-engineering the binary (`docs/wcc386-re/` + the watcom10.0a
repo) and by experiments.  Where they diverge, 10.0a wins.

Key OW regalloc files (names/shape only): `bld/cg/c/regalloc.c`
(`RegAlloc`, `GiveBestReg`, `SortConflicts`, `ConfBefore`,
`CountRegMoves`, `TooGreedy`, `WorthProlog`, `FixInstructions`),
`bld/cg/c/regsave.c` (`CalcSavings`; W=10, use=def=1, load=store=2,
prolog cost 2), `bld/cg/c/regtree.c`, `bld/cg/c/sortlist.c`.  For
32-bit ints the governing list is `DoubleRegs = EAX, EDX, EBX, ECX,
ESI, EDI, EBP` (table at va 0x821A8, confirmed behaviourally).

### Header layers: `c2_data.h`, `c2_types.h`, `c2_funcs.h`

`uv run c2 gen-header` regenerates the generated headers from
`data/out/symbols.json` + the `.c` definitions:

1. **`decomp/include/c2_data.h`** — externs for all non-static data
   symbols (~1451), with `_TYPE_OVERRIDES` for known structs/arrays.
   The only generated header normal `.c` files should include.
2. **`decomp/include/c2_funcs.h`** — canonical function prototypes for
   tooling; **must not be included broadly** (prototype visibility
   changes Watcom call-site codegen; PS source had no global registry).

Hand-written: **`decomp/include/c2_types.h`** (wrapper around
`entities.h` for shared structs + map/cell macros).  (`caesar2.h`,
`c2macro.h`, `c2rt.h` were retired.)  **Never patch generated headers
by hand** — fix `_TYPE_OVERRIDES` in `c2/commands/c_source.py` and
re-run `gen-header`.

### What PS.EXE source almost certainly looked like

Watcom debug info inlines `#include`d content, so headers are inferred
from indirect evidence.  **FOR a shared types header** (`globals.h`):
`army_rec`/`city_cell`/etc. referenced in 30+ files; AIL/Smacker
shipped headers; hundreds of `.foo` field-access sites need the struct
visible.  **AGAINST per-module function-decl headers**: Rule 37
(implicit-int `test eax,eax` after `char`-returning calls) is
everywhere — many cross-TU calls had NO prototype; `&font1`-style args
only compile without one; per-file externs match 1990s practice.

Most likely structure: `globals.h` + `ail.h` + `smacker.h` + per-file
`extern` decls, no central function registry.  Mapping to our repo:
`c2_types.h`/`entities.h` ≈ `globals.h` ✅; `c2_data.h` centralizes
what PS scattered ✅ functionally equivalent; `c2_funcs.h` = tooling
only ⚠; per-file externs = authentic ✅.

**Implication**: per-file `extern` decls are NOT a smell.  When fixing
W113/W1071 warnings, use case-by-case judgment: a real type bug → fix
the source; `&font1` matching PS asm → add the callee to
`_IMPLICIT_INT_FUNCTIONS`; a stub with a bogus canonical sig → keep the
per-file extern; an `int` global passed as `char *` → cast at the use
site; buttons arrays → `_TYPE_OVERRIDES`.

Per-file externs are legitimate for: self-references (call before
definition in the same TU), stub overrides, `#pragma aux` callees.
The verifier-driven check: strip the decl, run `c2 decomp-verify
decomp/src/<file> --no-strict`; if exact count drops, restore it.

---

## Special Caesar II context

### Watcom compiler specifics

- **Calling convention**: `__watcall` — eax, edx, ebx, ecx for the
  first 4 int params; remaining on stack right-to-left.
- **Name mangling**: already demangled in `symbols.json`.
- **Stack checking**: `__CHK`/`__STK` with special fixups.
- **Debug info**: `-d1` (line numbers only).
- **Static-data symbols (61)**: all file-scope statics.  Function-local
  statics are private internal labels at `-d1` — invisible to
  `symbols.json`, showing as `data_XXX` gaps in Ghidra.

### Code organization

- **Code section**: ~2,234 named functions, base `0x10000`.
- **Data section**: base `0x90000`.
- **Format**: Linear Executable (LE-Style DOS).
- **Only decompile `D:\C2\CODE\` files** — skip `R:\NET\LIBS\` (AIL)
  and Watcom CRT.

### Third-party libraries

- **Miles Sound System (AIL)** and **RAD Smacker**: linked from RAD;
  not byte-compared.  Headers: `decomp/include/ail.h` / `smacker.h`.
- **Watcom CRT (`clib3r.lib`)**: linked from the toolchain image.
  Probe list: `decomp/lib/clib3r-symbols.txt`.

### Big-picture data layout

- **`city_map`** (128 KB) — 80×80 grid of 20-byte cells
  (`struct city_cell` in `decomp/include/entities.h`); indexed by
  `cm_ptr = y * 80 + x`; referenced by 211 functions.
- **`region_map`** (28.8 KB), **`pseudo_map`** (52 KB),
  **`battle_map`** (10.8 KB).
- **`figure_list` / `citizen_list` / `army_list` / `unit_rec` /
  `arrow_rec` / `web_node` / `industry_rec` / `mercs_class` /
  `province_industry`** — documented in `entities.h`.

### Cross-build family

Three byte-distinct DOS `PS.EXE` builds, same toolchain:

| build id | date | size | `-d1` debug |
|---|---|---|---|
| `dbg-1996-04` | 1996-04-01 | 1,304,734 | **yes** (this is `data/PS.EXE`) |
| `rel-1995-10` | 1995-10-04 | 1,040,111 | no |
| `rel-1995-09` | 1995-09-21 | 1,039,599 | no |

Names transfer to the 1995 builds via TU-order anchoring
(`c2 crossbuild-map`); `decomp-verify -v`'s `Cross-build:` header
reports per-build status.

---

## Operational detail

### Stub generation & module emission

`c2/commands/c_source.py`: `classify_source()` (parse `// FUNCTION:` /
`// STUB:` annotations), `generate_stubs()`, `emit_module_c()`,
`StubFn`/`ExternVar`.

### Hand-written ASM modules (`c2 decomp`)

`c2 decomp --force data/out/symbols.json --exe data/PS.EXE` regenerates
ONLY the eight hand-written asm modules (`library.asm`, `sprites.asm`,
`dia_ptrs.asm`, `dialarga.asm`, `dialargb.asm`, `dia_medi.asm`,
`dia_smal.asm`, `palet.asm`) — Capstone-decoded WASM mnemonics,
automatic de-relocation (labels `<funcname>L<N>`).  All eight link into
the verify build, so every PUBLIC asm function is byte-compared on
every run.  (`palet.asm` was MASM/TASM-assembled originally — opposite
reg-reg direction bits — so its three affected instructions carry
byte-exact `db` fallbacks.)  CRT comes from `clib3r.lib`; AIL/Smacker
are not assembled by us; the generator never touches existing `.c`
files.

### The functional rebuild toolchain (`c2 rebuild` / `c2 delink` / `c2 run`)

The verify build (`c2 decomp-verify`) answers "are the bytes right?";
this toolchain answers "**does the recovered game actually build and
run?**".  Full background: `docs/delinking.md`.

**`c2 rebuild`** — produces a runnable, self-contained
**`build/PS.EXE`** (gitignored; `data/PS.EXE` is never written).  It
emits **the authentic 1995 link shape** and lets the stock toolchain do
the rest — no CRT extraction, no synthetic ordering, no post-link
patching:

```
SYSTEM dos4g                          ← stock wlink 10.0a directive file
LIBRARY ail.lib, smack.lib, clib3r.lib
FILE <PS's -d1 modules 0..45, in order>   (44 objects)
```

* FILE objects = the recovered game TUs + the eight asm modules + the
  delinked `dllload.obj`/`sndail.obj` (loose SDK glue, exactly as in
  1995).  `ail.lib`/`smack.lib` are reconstructed from the split delink
  on every build (member-stale checked); `palet.obj` is packed into
  `smack.lib` (it was an SDK library member).  wlink's own resolution
  regenerates PS's entire CRT/AV module interleaving — the layout
  metric proves it (0 cross-module order breaks).  The result is made
  self-contained by prepending PS.EXE's OWN byte-exact DOS/4GW
  Professional 1.97 stub (`data/PS.EXE[:0x37d4c]`) to the linked `LE` —
  binding is a pure prefix swap, so this reproduces the shipped stub
  byte-for-byte with no vendored `4GWBIND`/`4GWPRO` blob or dosemu step.
  The DOS/4GW extender is Tenberry third-party code we never decompile,
  the same category as the CRT/AIL/Smacker blobs the rebuild reuses.
* **No auto-stubbing.**  An unresolved extern is a hard link error and
  the printed undefined-symbol list IS the recovery worklist (that
  policy is what surfaced `c2_vars.c` and the `smacks` movie-table
  bug).  The verifier's stubs.c machinery is decomp-verify-only.
* Work dir `.c2-cache/rebuild/` (independent of the verifier's shared
  build cache; safe next to parallel verify sessions).  Incremental:
  ~1 s warm, minutes cold.  Sources are staged VERBATIM — no stub
  stripping.
* Options: `-cv` (list diffing/unmatched symbols), `--no-compare`,
  `--no-bind` (stop at the LE `psle.exe`), `--stack`, `-o <path>`.

**Reading the auto-comparison** (runs after every build; the same
fixup+rel32 masking as the byte oracle, applied to the final link):

```
game       1415/1435 exact, 17 diff …   ← must equal decomp-verify's diff set
c2-asm     87/87 exact                  ← anything less: asm module regression
av-delink  517/517 exact                ← anything less: DELINKER bug (delink is verbatim)
crt        195/195 exact                ← anything less: link-input/toolchain drift
layout     0 cross-module break(s); 1 within ← module order fidelity (the 1 = a 1-byte
                                               empty-fn ret fold in pcsound, sub-source)
data       341/341 named initialized symbols exact
```

Regression signatures: `N unmatched` = a symbol lost its rebuild
address (resolution machinery, not necessarily missing bytes — statics
resolve via map name → module/cluster anchoring → pointer chase);
`name(uninitialized)` in data = a PS-initialized global became zeroed
BSS (the `smacks` bug class — recover the initializer); `~tail` =
span-overreach noise after a `ret` (only worth chasing if new).  A new
game diff that decomp-verify does NOT show means the rebuild staging
diverged from the verify staging — investigate immediately.

**`c2 delink`** — recovers relocatable OMF objects from PS.EXE
(byte-preserving; docs/delinking.md for the mechanism):

```
c2 delink --group av --split --libs -o decomp/lib/av --verify
   # 15 per-module objs + reconstructed ail.lib/smack.lib (gitignored)
c2 delink --group av -o /tmp/av.obj --verify        # merged single obj
c2 delink --list                                    # groups
```

Key delinker facts (each was a measured fix — don't regress them):
alias dedupe (two `-d1` names on one body must not duplicate bytes);
data PUBDEFs + the `_sndinit` allowlist; per-module `_TEXT` alignment
inferred from PS's pad bytes; the RAD asm modules' own code segments
declared in `_SEGMENT_CANON` order by every RAD object.  `--verify`
(verbatim byte check vs PS.EXE) should accompany any delinker change,
and `c2 rebuild`'s av-delink/layout buckets are the end-to-end gate.

**Install & run:**

```
c2 cd install "CDs/extracted/Caesar II (Europe) …" --full   # once → install/caesar2
c2 run                  # DOSBox-X, RECOMPILED game (auto-runs c2 rebuild,
                        #   stages install/caesar2/PSREBLD.EXE; shipped PS.EXE untouched)
c2 run --original       # the shipped PS.EXE via c2.bat
c2 run --no-gdb         # don't wait for a debugger
```

Headless smoke test (no display; proves DOS/4GW + CRT startup + the
recovered `main()` reach the CD prompt):

```
podman run --rm -v "$PWD/install/caesar2:/src" \
    localhost/watcom-10.0a-dosemu2 PSREBLD.EXE   # expect the CD-check prompt
```

**AV runtime test** — `tools/smk-player/build.sh` links the
reconstructed `ail.lib`/`smack.lib` like a 1995 licensee program and
decodes real `.SMK` cinematics with AIL sound (see its README).  Run it
after delinker changes; garbage frames = a wrong relocation.

The shared-globals substrate lives in `decomp/src/c2_vars.c` (the
original's pure variables TU, 773 BSS definitions in PS layout order)
plus per-TU variable blocks; `datainit.c` carries the recovered
initializers of PS's `data.c` (and, until split back out, `rot_data.c`
+ `contrdat.c`).  Byte-space map snapshot:
`docs/rebuild-byte-space-2026-07-10.png`.

### Refactor scans (`semgrep`)

`uv run semgrep --config c2/semgrep-rules/ decomp/src/` for
**discovery only** — semgrep's `autofix:` has a paren-range bug; locate
sites with semgrep, apply with a tiny paren-balanced Python rewriter.
(The `setuptools<81` pin in `pyproject.toml` is for semgrep's
`pkg_resources` dependency.)

### Reading PS.EXE bytes / data / line numbers (low-level)

The canonical command is `c2 disasm <name>`.  Library helpers:
`c2.commands.disasm.disasm_function(name)` → `(addr, size, lines)`;
`c2.commands.decomp_verify._load_le_code_and_fixups(exe)`;
`c2.commands.fixups.parse_le_fixups(...)`.  Data-segment reads: seek
`objects[1].file_offset_int + (vaddr - 0x90000)` in `data/PS.EXE`.
`symbols.json` → `line_numbers` maps code offsets to source lines.

### Project setup

- **Ghidra project**: `./C2`, program `PS.EXE`; rebuilt by
  `scripts/rebuild-ghidra.sh`; bridge auto-starts on first command.
- **Debug data**: `data/out/symbols.json`.
- **Import script**: `ghidra_scripts/ImportCaesar2.java`.

### Semantic code search (semble)

The user-wide `pi-semble` extension registers `semble_search` (+
`semble_find_related`): fast semantic + lexical search across the C
decompilation, the c2 toolkit, the docs, AND the vendored Open Watcom
source (`vendor/open-watcom/`, searchable despite being gitignored).
**Prefer `semble_search` over grep/glob+read for any "where is… / how
does…" question**; narrow with `path`, fall back to exact grep only
for every-literal-occurrence needs.  Scope: `.gitignore` +
`.sembleignore`.

### Ghidra-cli

Routine work uses the `c2` commands; ghidra-cli is rarely needed —
prefer `c2 disasm` / `c2 xrefs` / `c2 decomp-verify`.  Full reference:
`.pi/skills/ghidra-cli/SKILL.md`.  Bridge:
`ghidra-cli status|restart|ping --project ./Caesar2`.
**Never** `ghidra-cli analyze` (see the CRITICAL warning at the top).
