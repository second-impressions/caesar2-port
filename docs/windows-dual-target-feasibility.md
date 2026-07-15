# Dual-target decomp: compiling the source tree against CAESAR2.EXE too

> **STATUS — IMPLEMENTED.**  The byte-verify path ships as
> **`c2 win-verify`** (engine `c2/win_bytes.py`, tests `tests/test_win_bytes.py`)
> AND as the unified front door **`c2 decomp-verify --target win`** (a thin
> dispatcher into the same engine + a persistent
> `.c2-cache/win-verify.json` cache, the Win mirror of `verify.json`).  All
> 37 decomp TUs compile under MSVC 4.0
> (`hotkeys`/`sndail` were `#ifdef`-guarded), and a whole-tree run reports
> **372 functions byte-exact vs `CAESAR2.EXE`** in ~4 s (instant on cache).
> The dual census is surfaced in `c2 functions --win`.  Usage is at the bottom
> ("The shipped tool").

**Question (this investigation).**  We attribute the Windows `CAESAR2.EXE`
to **MSVC 4.0 `/Od`** and — unlike the Mac CodeWarrior build — we *have the
compiler* (`localhost/msvc-4.00-wibo`).  Does it make sense to compile the
decomp source tree against the Windows binary as well, to (a) make progress
on the ~131 functions still diffing vs the Watcom `PS.EXE`, and (b) get a
verified Windows decompilation "for free"?  Can `decomp-verify` be adapted
to byte-check both `PS.EXE` (Watcom 10.0a) and `CAESAR2.EXE` (MSVC 4.0)?

**Verdict.**  *Yes to all three, with one nuance.*  The pipeline already
works end-to-end and is reproducible from the committed tree; **369
functions are byte-exact vs `CAESAR2.EXE` today** from the same source (362
of them dual-verified — one source produces *both* shipped binaries
byte-for-byte).  MSVC `/Od` is a **stricter source-shape oracle** than
optimised Watcom: it catches shape errors the Watcom byte oracle is
*blind to* (proven — see `totalXpercent`).  The nuance: `/Od` does no
register allocation, so it cannot adjudicate the *pure-regalloc* residues
that dominate the hardest PS diffs — but for those it instead acts as a
**certificate** ("source shape is correct ⇒ the PS residue is regalloc" —
evidence that documents/deprioritises; only byte-exact finishes).

---

## What already exists (don't rebuild it)

* **The compiler**: `localhost/msvc-4.00-wibo` — VC4.0 `cl.exe` under
  `wibo` (a lightweight PE loader; ~0.1 s/compile, far faster than wine).
  Proven the right toolchain in `docs/windows-builds-fingerprint.md`
  (linker 3.00, debug CRT byte-matched).
* **The byte target**: `data/windows-builds/named/caesar2_A_1044480.exe`
  (build A, 1996-08, the temporally-closest Windows witness to the 1996-04
  `-d1` DOS build).  PE32, image base `0x400000`, `.text` @ VA `0x1000`.
* **The function map**: `data/windows-builds/func-map.json` — 1187
  `ps_name → win_va` rows.  Tier `compile-exact` (315) were byte-verified
  during the map build; `ordinal`/`fuzzy` (the rest) were positioned by
  order/similarity.
* **The decompile oracle**: `c2 win-decompile <fn>` / `c2win.py` (Ghidra,
  named+typed) — already wired, the MSVC analogue of `c2 mac-decompile`.
* **The masking technique**: `scripts/verify_msvc_crt.py` already does
  COFF `.text` + DIR32/REL32 reloc masking + anchored byte-search.

**Not committed but NOT needed**: the old `_msvc_shim/` (DOS intrinsics).
Per project direction the Watcom/DOS specifics belong behind `#ifdef` in
the source, not in a shim.  **35 of 37 TUs already compile under MSVC with
zero changes** (`/Od /Zp1 /I include /FIc2_funcs.h /D__pascal= /D__far=`).
Only two fail, trivially:
* `hotkeys.c` — POSIX `S_IRUSR`/`S_IWUSR` (a `#include`/`#ifdef` guard).
* `sndail.c` — a `timer` identifier collides with a CRT decl (rename/guard).

## The byte-compare works end-to-end (PoC built this session)

Per function: compile the TU → parse the COFF symbol table for the
function's `.text` range → mask its DIR32/REL32 reloc slots → extract the
same-length window at `win_va` in `CAESAR2.EXE` → compare (the masked
search relocates the function map-independently, so a hit *is* byte-exact).
This is the exact analogue of the `PS.EXE` path (`_extract_le_code` +
LE-fixup + rel-call masking).  Worked example `pcsound.c`: **15/23 functions
byte-exact vs `CAESAR2.EXE`**, the 8 misses genuine (no exact match anywhere
in `.text`, i.e. not mismapping).

Full tree (35 compilable TUs, 1417 functions):

| MSVC vs CAESAR2.EXE | count | meaning |
|---|---:|---|
| **byte-exact** | **369** | a verified Windows decomp, *free* |
| — also PS-exact | 362 | **dual-verified**: one source → both binaries |
| diff | 808 | shape/port/slot divergence (see below) |
| no win mapping | 240 | not in `func-map.json` yet |

## The value for the ~131 still-diffing functions

`/Od` reproduces **source structure** faithfully (statements, types,
constants, field offsets, arg order, control flow) and optimises *nothing*
(no enregistration, no CSE, no scheduling, no canonicalisation).  So:

1. **It catches optimizer-canonicalised SHAPE errors the Watcom byte
   oracle cannot see.**  *Proven.*  `totalXpercent` was byte-exact vs
   `PS.EXE` written `a *= b; return a/100;`.  Watcom collapses that and the
   two-statement `a *= b; a = a/100; return a;` to identical PS bytes — the
   byte oracle can't choose.  MSVC `/Od` keeps the assign+reload explicit:
   the two-statement form is byte-exact vs `CAESAR2.EXE` (43 B), the
   one-statement form is not (37 B).  → recovered the true shape, committed
   in `d9e1deab` (stays PS-exact, now also CAESAR2-exact).  This is a *new*
   capability: neither the Watcom bytes nor the Mac/Ghidra decompile
   surfaced it.

2. **The `/Od` stack frame is a near-direct readout of the source's local
   declarations** — count *and* order — the single hardest thing to recover
   from *optimised* Watcom output (where locals are enregistered and
   invisible).  Worked example `find_enemy` (diffing vs PS): MSVC-of-our-
   source vs `CAESAR2.EXE` is ~90 % structurally identical (same control
   flow, same `0x50`/`0x4f` bounds) and the diffs are pure shape signal —
   our frame `sub esp,0x24` (9 locals) vs the win build's `0x1c`, a
   different slot order, and one `cy+r` vs `r+cy` operand swap.  That is a
   de-invent / declaration-order / expression-order worklist, read straight
   off the `/Od` disasm.

3. **For pure-regalloc residues it is a certificate, not a lever.**  `/Od`
   does no regalloc, so it can't adjudicate seat/decl-order/savings ties
   (22 of the 131 diffs are `seat`-layer).  But MSVC-exact there would
   *certify* the source shape is correct ⇒ the PS residue is regalloc
   (documents/deprioritises the function; per AGENTS.md, only byte-exact
   finishes it).

Today **0 of the 131 diffing functions are MSVC-exact** — they diverge
under MSVC too.  That is the expected state (a function still diffing vs PS
usually has *some* unrecovered shape, which `/Od` also reflects) and is
exactly why the `/Od` view is useful: it shows the shape gap legibly.  As
shape fixes land, functions cross into MSVC-exact and the residue becomes
classifiable.

### Important caveat — CAESAR2.EXE is a temporally-distant *port*

Build A is 1996-08, the DOS `-d1` build is 1996-04, and the Windows engine
was its own MSDEV project (`C2Win`).  So **not every MSVC divergence is a
recovery error** — some are genuine source differences between the DOS and
Windows codebases (e.g. the `find_enemy` `r+cy` operand order is ambiguous;
Watcom can't confirm it either way).  Treat MSVC-exact as strong positive
evidence, and MSVC-diff as a *lead to read*, not a verdict.  The Windows
side is a witness, never the byte spec (that stays `PS.EXE`).

### Methodological note — raw byte-diff vs MSVC is noisy

In `/Od`, shuffling one local changes every `[ebp-N]` displacement byte, so
raw byte-diff massively overstates divergence (`find_enemy`: 238/464 bytes,
but ~90 % same shape).  A dual-target verifier should score at the
**structure level** (mnemonic + reloc-/displacement-normalised operands)
and/or mask ebp-relative displacement bytes, *in addition to* the raw byte
oracle — otherwise the slot-shuffle noise drowns the real signal.

### MSVC 4.x codegen is fragile-but-DETERMINISTIC (not "random")

A question that bears directly on how to read a `win-verify` diff: is the
MSVC 4.0 `/Od` codegen run-to-run reproducible, or genuinely nondeterministic?
The sibling decompilation project, [LEGO Island](https://github.com/isledecomp/isle)
(MSVC 4.20 — same `C2.EXE` backend family), names a "compiler randomness /
entropy" phenomenon: *"changes to the code base, for instance in a header,
can pseudo-randomly affect the code generation of functions in compilation
units that include this header, even if the changes are completely
unrelated to those functions ... roughly affects ~5% of all decompiled
functions. We are currently unaware of the exact nature of this
phenomenon."*  They treat it as an unsolved obstacle to 100% matching.

**This is a mislabel.  The phenomenon is *fragile-but-deterministic*
codegen, not nondeterminism** — and it is empirically testable.

* **The decomp community framing** (decomp.wiki) classifies old compilers
  (MWCC, IDO, MSVC 4.x) as *fragile*: *"a series of 10,000 logically
  equivalent ways of writing the same thing may compile 10,000 different
  ways even with the same optimization level"*, *contrasted* with robust
  modern compilers (Clang) that *"are much better at discarding information
  that is irrelevant."*  isle's own example gives the answer away: the trigger
  is *adding an unused inline/enum **in a header*** — which **changes the
  preprocessed translation unit**.  The codegen is fragile to the **full
  preprocessed TU content** (the compiler iterates pointer-keyed pools /
  carries register-allocator state across the TU; a perturbation upstream
  propagates downstream — the general mechanism behind both true
  nondeterminism and fragile-but-deterministic codegen; see LLVM's
  pointer-ordering analyzer [D50488](https://reviews.llvm.org/D50488)).
  Same preprocessed TU in → same `.obj` out.
* **Empirical test on OUR toolchain** (MSVC 4.0 `/Od`, `c2 win-verify`):
  compiling the same TU twice with the per-process memo cache bypassed
  yields **byte-identical `.text`**::

      evolver  run 1: sha256=640918a972d7ff29    run 2: sha256=640918a972d7ff29  # identical
      pcsound  run 1: sha256=48979a55922ebd80    run 2: sha256=48979a55922ebd80  # identical

  And the win-verify **diff itself** is stable across recompiles::

      evolve_water_supply_baths_industry  run 1: struct_diff=19  run 2: struct_diff=19  # identical

  **MSVC 4.0 `/Od` is run-to-run byte-deterministic.**

* **What it means for `win-verify` diffs:**
  1. A win-diff is **stable and therefore meaningful** — it is not noise
     that might vanish on a recompile.  It reflects a real, reproducible
     difference between *our* preprocessed TU and the *original
     `CAESAR2.EXE`* build's preprocessed TU.
  2. But **meaningful ≠ a recovery error.**  The diff is reproducibly *our
     codegen realization* vs *their codegen realization* of the same source
     — and fragile-but-deterministic codegen means two compiles of the same
     source can diverge if their surrounding TUs differ (the isle symptom).
     Proven on this corpus: rewriting `evolve_water_supply_baths_industry`'s
     field accesses through a cached struct pointer made the diff *worse on
     both oracles* (struct 19→22, and it broke PS-exactness) — i.e. a source
     rewrite pushed further from *both* realizations, not toward either.
     That is *stronger* evidence the diff is NOT a source defect.
  3. A win-diff is therefore **either** (a) a real shape defect the Watcom
     byte oracle is blind to (`evolve_a_house`'s invented temp — fixable,
     committed `b0104717`), **or** (b) a reproducible codegen-realization
     difference (`evolve_amenity_cover`'s `jge`/`jle` operand-order flip,
     `evolve_water_supply`'s global-fold) — **not fixable by source, and not
     to be chased**.  The two cases are discriminated empirically: try the
     source rewrite the diff suggests and watch *both* oracles — if the
     Watcom oracle breaks or both rise, it's (b).

This sharpens the "MSVC-diff is a lead, not a verdict" caveat from a hunch
into a tested property: a `win-verify` diff is a stable signal that *either*
names a real source-shape defect *or* reflects a reproducible but
source-invariant codegen choice — and only the experiment (edit + re-verify
both oracles) tells which.

## The shipped tool — `c2 win-verify` / `c2 decomp-verify --target win`

```
c2 win-verify                    # whole-tree summary (372 exact / 867 diff / …)
c2 decomp-verify --target win    # same thing via the unified front door
c2 win-verify totalXpercent      # one function's verdict
c2 win-verify -v find_enemy      # + the aligned MSVC-vs-CAESAR2 asm diff
c2 win-verify --file pcsound.c   # every decompiled function in a TU
c2 win-verify --diffing          # the not-yet-exact functions, ranked by struct_diff
c2 win-verify --json             # {summary, files, functions} on stdout
c2 win-verify --no-cache         # force a fresh MSVC build
c2 functions lib32 --win         # PS-vs-CAESAR2 dual census for a TU
```

Results are cached at `.c2-cache/win-verify.json` (whole-tree, incremental
on changed TUs, full rebuild when a header changes) — the Win mirror of
`verify.json`; both `win-verify` and `decomp-verify --target win` read/write
the same cache.

Each function reports two figures (mirroring the oracle/shape split on the
DOS side): **byte_diff** (the oracle; 0 ⇒ byte-exact vs CAESAR2.EXE) and
**struct_diff** (a difflib instruction-edit distance over reloc-/immediate-
normalised mnemonics — the *workable* figure, insensitive to /Od stack-slot
shuffle).  The `-v` view colours **structural** divergence (`≠`, real shape)
distinctly from **slot/immediate noise** (`·`, the /Od slot shuffle).
Exactness is decided by a **map-independent masked search** across `.text`
(DIR32/REL32 wildcarded), so a stale `func-map` entry never yields a false
diff — a masked hit anywhere *is* a byte-exact certificate.

**Command.**  `c2 win-verify <fn>` is the byte-oracle sibling of
`c2 decomp-verify` / `c2 win-decompile`; **`c2 decomp-verify --target win`
** is the unified front door (same engine + cache, rendered like the
Watcom summary); `--json` returns structured `{summary, files, functions}`
(or one fn record with `diff_rows`) and `-v` the aligned MSVC-vs-CAESAR2 asm.

**Design note (revised).**  The two targets are now combined behind one
front door: **`c2 decomp-verify --target watcom|win`** (default `watcom`).
Earlier this note argued for keeping a separate `win-verify` command rather
than a `--target win` flag, because `decomp_verify.py` is ~6 100 lines of
Watcom-specific build/hint machinery the Windows path shares almost none
of.  That argument still holds for *the body*: the `--target win` path does
NOT fork the Watcom body -- it is a ~30-line dispatcher at the top of
`decomp_verify()` that calls into the clean `c2/win_bytes.py` engine +
`c2/win_verify_cache.py` cache.  The standalone `c2 win-verify` command stays
as a convenience alias that delegates to the same `run()`.  The two are the
symmetric pair below -- SAME cache + engine, two entry points.

## Architecture — the two symmetric paths

The two paths are structurally symmetric:

| stage | DOS (today) | Windows (proposed) |
|---|---|---|
| build | Watcom `wmake` in `watcom-10.0a-wibo-trace` → `out.exe` (LE) | MSVC `cl /Od /Zp1 …` in `msvc-4.00-wibo` → per-TU COFF `.obj` |
| locate | `symbols.json` addr + `// FUNCTION: C2 0xADDR` | `func-map.json` win_va + a new `// WIN: 0xADDR` annotation |
| extract | `_extract_le_code` + LE fixups | COFF `.text` slice (this PoC) |
| mask | LE fixups + rel-call/jmp disp | DIR32/REL32 relocs (+ optional ebp-disp for shape view) |
| compare | `_compare_bytes` | identical logic |

Status of the concrete pieces:

1. ✅ **`#ifdef` the DOS specifics in place** — `hotkeys.c` (`S_IRUSR`/
   `S_IWUSR` fallback) and `sndail.c` (the `timer` data/function clash)
   guarded under `__WATCOMC__`; **37/37 TUs now compile under MSVC**, the
   Watcom/PS build byte-unaffected (`744b6032`).
2. ✅ **The byte-verify engine + command** — `c2/win_bytes.py` +
   `c2 win-verify` (`b1a8c1e6`): per-TU MSVC compile, COFF extract,
   DIR32/REL32 mask, map-independent locate, byte+struct diff.
3. ✅ **`// WIN: 0xADDR` annotation support** — `win_verify` reads a
   `// WIN:` comment above a definition and lets it *override*
   `func-map.json` (the user's proposal).  Deliberately **not bulk-seeded**:
   `func-map.json` already provides every location, so annotations are kept
   for the cases that need correcting/adding (the 203 no-map functions and
   the `ordinal`/`fuzzy` mismaps) rather than as ~1 200 lines of churn.
   Seeding can be done later as a deliberate pass.
4. ✅ **Persistent cache + `--json` + `--target win` front door** —
   `.c2-cache/win-verify.json` mirrors `verify.json` (whole-tree,
   incremental on changed TUs, full rebuild when a header changes;
   `c2/win_verify_cache.py`).  `c2 win-verify --json` emits
   `{summary,files,functions}` (or one-fn record with `diff_rows`).  The
   unified front door `c2 decomp-verify --target win` dispatches into the
   same engine + cache, rendering the decomp-verify-style summary/per-fn
   diff view (no regalloc layers — `/Od` does no register allocation).
5. ✅ **Dual census in `c2 functions`** — `c2 functions <file> --win`
   loads the Win cache and reports PS-exact-**and**-CAESAR2-exact per TU,
   so the gap list (PS-exact but MSVC-diff) is the shape-recovery worklist
   directly.  `c2 win-verify --diffing` / `c2 decomp-verify --target win
   --diffing` give the full ranked diff list anytime.

## The recurring payoff & limits

* Run the win oracle over the PS-exact corpus to surface
  "byte-exact-but-wrong-shape" cases like `totalXpercent` (shape recovery
  the Watcom oracle can't do), and over the still-diffing corpus to read
  invented-locals / decl-order / operand-order straight off the `/Od` frame
  (`find_enemy` pattern) via `c2 win-verify -v <fn>`.
* **Don't expect**: a turnkey closer for the seat-layer regalloc residues
  (`/Od` has no opinion there) or byte-exactness on heavily port-diverged
  functions.  Also, for small `ordinal`-mapped functions a
  "1 byte / 0 struct" diff usually means the map points at a structural
  *twin* (e.g. a `return g ? 1 : 0` sibling) — the map-independent masked
  search correctly withholds the "exact" verdict; trust `struct_diff` plus
  the `-v` view, not the raw byte count alone.  And per the determinism
  section above, a stable win-diff that resists every source rewrite (both
  oracles stay flat or rise) is a reproducible codegen-realization
  difference — classify it (b), don't grind it: MSVC 4.x is
  fragile-but-deterministic, so the diff won't churn away on a recompile.

---

*Built this session:* `c2 win-verify` (engine `c2/win_bytes.py`, command
`c2/commands/win_verify.py`, tests `tests/test_win_bytes.py`) — validated on
`pcsound.c` (18/26 mapped exact) and the full tree (**408 exact**, 0 TU
build-fails, ~4 s).  The two `#ifdef` guards: `744b6032`.  First shape-
recovery win driven by the `/Od` witness: `d9e1deab` (`totalXpercent`).
See also `docs/windows-builds-fingerprint.md` (compiler proof) and
`data/windows-builds/ghidra-recreate.md` (the func-map build).
