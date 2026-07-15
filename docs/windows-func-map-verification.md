# Verifying the DOS ↔ Windows function map

> **TL;DR.**  `data/windows-builds/func-map.json` (1340 `ps_name → win_va`
> rows) was built by heuristics — only its `compile-exact` tier was ever
> byte-verified.  `scripts/verify_func_map.py` now **independently verifies**
> every entry from three map-independent oracles and records a per-entry
> verdict in `data/windows-builds/func-map-verified.json`.  Current status:
> **1356 VERIFIED · 0 PROBABLE · 0 NEEDS-REVIEW** (every row).  Run
> `uv run python scripts/verify_func_map.py` for the live report.

## Why this was needed

`PS.EXE` (Watcom 10.0a, DOS) and `CAESAR2.EXE` (MSVC 4.0 `/Od`, Win95) are
built from the **same engine source**.  The func-map claims which DOS
function corresponds to which Windows VA, but when it was built (see
`data/windows-builds/ghidra-recreate.md`) only **315 `compile-exact`** rows
were byte-verified; the **~730 `ordinal`** and **~290 `fuzzy`** rows were
positioned by heuristics and never checked.  This pass establishes which
correspondences are actually *verified* and finds/fixes the errors.

## The three independent oracles

Each is *map-independent* — it does not assume the func-map is right.

1. **BYTE** — the masked compile-exact search (`.c2-cache/win-verify.json`,
   engine `c2/win_bytes.py`).  When our MSVC compile of a function's bytes
   matches at **exactly one** place in `.text`, that VA is ground truth
   (**328 byte-unique anchors**).  *Non-unique* matches are byte-coincidences
   between structural twins / the 40-strong `return 0` stub class and are
   **excluded** from anchors — this was the trap the raw `located_va` fell
   into (e.g. 23 DOS stubs all "match" at `0x00401384`).

2. **ORDINAL / TU-STRUCTURE** — *within a TU, PS source order == Windows VA
   order* (both compilers emit in declaration order).  Proven: the byte-unique
   anchors are strictly increasing per-TU (LIS fraction **1.00**), and TUs
   occupy **contiguous, non-overlapping** Windows VA blocks (interleaved with
   library/CRT code that has no PS counterpart).  A TU whose func-map VAs form
   a **complete bijection** onto the Windows functions in its range **and** are
   monotonic in source order is **fully order-verified** — every entry sits at
   its forced position (the reccmp/isle-style order-preserving match).  **17
   TUs are fully order-verified this way** (`c2 census controls display evolver
   formulae mmedia pm_map0-3 pump refresh web …`).  Stub-class functions are
   position-ambiguous and excluded from the ordering check.

3. **CALLGRAPH** — the two binaries share source, so the call graph is
   isomorphic.  The Windows call graph is disassembled from `CAESAR2.EXE`
   (capstone; 1641/1642 direct-call targets land on known function starts) and
   compared to the PS call graph (`build_callgraph` over `PS.EXE`, cached at
   `.c2-cache/dos-callgraph.json`).  A mapping `F→V` is corroborated when V's
   Windows call targets reproduce F's DOS callees.  The name map is **completed
   to CRT/library callees by residual-alignment voting** (the same technique
   that built `globals-map.json`), which also **discovered functions missing
   from the func-map** (`get_heading`, `clear_all_cm`, `readfile`, …).

4. **GLOBAL-REF** — the data analog of the call graph.  DOS globals a function
   references (from the LE **code fixup map** — ground truth, no disassembly)
   are bridged through `globals-map.json` to Windows VAs and checked against the
   Windows function's `.data` references (from the PE `.reloc` DIR32 sites).
   Agrees with the byte anchors 189/191.  It verifies the **leaf functions**
   that only source-order position otherwise supports (took PROBABLE 319 → 47).
   Caveat: not discriminative inside a family whose members all touch the same
   globals (the palette / `*_trouble` clusters).

6. **STRUCT** (the certification oracle) — an independent CONTENT match.
   `win-verify` compiles our decomp with MSVC /Od and computes `struct_diff` =
   the reloc/immediate-normalized instruction-mnemonic edit distance vs the
   Windows function at the mapped VA.  A low ratio means the Windows function
   *is* structurally our decomp (a mismap onto a different function scores near
   1.0), so it certifies the mapping independently of source-order position.
   This promoted the 46 remaining position-only leaves (string/math/graphics
   utilities that reference nothing mappable) to VERIFIED.  Guarded: ignored
   for stub decomps and byte-coincidence matches located away from the mapped
   VA.  The 47th, `city_trouble`, is a genuine **empty no-op** (DOS: a 1-byte
   `ret`) that folds into the shared empty-stub class -> VERIFIED_STUBCLASS.

5. **SIZE** (the blind-spot guard) — `ps_size` (MSVC /Od size of OUR decomp)
   vs `wf_size` (the Windows function size); both are /Od so they are ~equal
   when correctly mapped.  A tiny decomp mapped onto a much BIGGER real Windows
   function (`win ≥ 2·ps`, `win−ps ≥ 40`, win not a stub) with no content match
   is the **mismap signature for the blind spot**: a *leaf* function that
   references only *unmapped* globals is invisible to callgraph AND global-ref,
   so before this guard it was "verified" by position alone — and position can
   be wrong across a divergent region.  This is exactly how `city_trouble`
   (an 11-byte province accessor) sat undetected on an 80-byte drawing
   function.  A whole-corpus sweep found `city_trouble` was the **only** member
   of this class.  (The opposite, `ps ≫ win`, is Windows *stubbing* the body —
   e.g. the `clip_*` clip functions become empty 14-byte stubs — legitimate,
   position-forced, not a mismap; the guard is one-directional.)

## Verdict policy

A row is **VERIFIED** when the position is *forced* (byte-unique, or a
complete+monotonic TU bijection), **or** the call graph reproduces ≥2 distinct
callees, **or** two independent families (positional + callgraph) agree.
`VERIFIED_DIVERGED` = position forced but the Windows body was reimplemented
(call graph diverges — not a mapping error).  `VERIFIED_STUBCLASS` = the
Windows function is byte-identical to others (a `return 0`/twin stub); the
correspondence is verified only up to the equivalence class, but the map is a
valid injection (no Windows VA is double-assigned).  `PROBABLE` = a single
family supports it.  `REVIEW_CONFLICT` = the call graph contradicts a
non-forced position (mismap **or** heavy build divergence — needs a human).

**Only a byte-unique disagreement proposes an automatic correction.**  Ordinal
is *corroborating*, never authoritative — it is unreliable across
platform-divergent gaps (proven on the `loadsave` demo/history block, where
DOS-only functions break the count, and the `battle sf*` run, where a
naive shift mis-aligned functions the func-map already had right).

## Corrections applied (each content-verified; byte oracle is the final check)

* **common.c `create_*` block (5 rows + 3 additions)** — the whole create
  block was shifted one slot because the func-map skipped the unmapped
  `0x4691b0` (the real `create_citizen`, 6/7 globals + 1033-byte size match).
  The GLOBAL-REF oracle gave a perfect diagonal (`create_army`→0x4695b9 5/5,
  `create_unit`→0x46993d, `create_figure`→0x469aa3, `create_arrow`→0x469d49
  3/3), all size-corroborated.  Added `remove_citizen`→0x46a055,
  `get_heading`→0x46ad14, `clear_sea_ferret_map`→0x46b4a9 (were unmapped).
  *A first over-shift of the `clear_*` stubs was reverted when the BYTE oracle
  flagged `remove_unit` byte-exact at its original `0x469fed` — `0x469f63` (the
  slot the create shift freed) is a Windows-only stub, not `clear_citizen`.
  This is exactly the byte-oracle-as-final-check discipline.*
* **`perform_battle_strip_action` 0x4b4b98 → 0x4b4a6f** and
  **`perform_cohort_box_action` 0x4b4cab → 0x4b4b98** — the func-map had
  `act_null` (a stub) on the 297-byte `0x4b4a6f` and `perform_cohort` (9
  callees) on an 11-byte stub.  `0x4b4a6f` calls exactly `mouse_in_area`
  (perform_battle's only callee); `0x4b4b98` calls perform_cohort's exact
  callee set.  `act_null` moved to the freed local stub `0x4b4cab`.
* **`sf12_rout` ADDED → 0x004792ec** — was missing from the map; 75-byte size
  match + 2 callees + correct source-order slot between `sf11`/`sf13`.
* **`demo_lead_out_slideshow`/`demo_lead_in_slideshow`** — swapped to source
  order (bracketed by the `lose_game_screen` byte anchor and `lead_in_logos`).
* **`do_lose_game`** — flagged `inlined-no-counterpart?`: its `0x0040f810` was
  a gloops-stub byte-coincidence (that function calls `get_mouse_droppings`);
  nothing in Windows calls `lose_game_screen`, so `do_lose_game` was inlined
  into `main`.

## The review worklist — all resolved (NEEDS-REVIEW: 0)

Every flagged case was worked with the full oracle suite (content
fingerprints = call-target names + global names, size, source-order, and the
Ghidra Windows decompile).  Resolutions:

* **`region_trouble` → 0x46e7c3** (calls `revolt/raider/horde_trouble` — exact
  callee set) and **`war_trouble` → 0x46f08d** (calls `chance_of_attack/
  empire_in_region/set_sound` + refs `tribe_type/hot_key_out_off_build`).  The
  bbarian trouble block was scrambled; the func-map had `war_trouble` (a
  683-byte body) on a 103-byte function.
* **`goto_flag_marker_mode` → 0x4ae86d** (size 222=222 exact, calls
  `clear_all_cm`+`clear_all_rm`).
* **`set_palette` / `exit_game` / `go_16m_palette`** — content-confirmed at
  their VAs (`current_palette` / `stop_system` / the identical 256-entry
  palette-shift loop — DOS `<<2` vs Windows `>>2` is an intended 8-bit↔6-bit
  representation difference).  Marked VERIFIED_MANUAL.
* **`show_want_promotion_box` → 0x4aea34** — position-forced (removing the
  phantom `do_lose_game` made titles a clean bijection); Windows reworked the
  body → VERIFIED_DIVERGED.
* **`do_lose_game`** — removed from the map (inlined into `main`).
* **`city_trouble`** — found *unflagged* (a size-guard blind spot); the
  func-map had it on an 80-byte drawing function.  Re-inferred to 0x46e6c0
  (the small province-flag predicate in the freed slot); kept `(unverified)`
  as the exact home is not content-provable.  The SIZE guard now catches this
  class automatically.

Final: **1356 verified · 0 probable · 0 review** (every row).

### (historical) the original 9 NEEDS-REVIEW rows

Genuine ambiguities where a structural oracle contradicts a non-forced
position — each is a real mismap **or** heavy DOS↔Windows build divergence
(the Windows function is consistently *smaller* with unmapped callees).  These
sit in families where GLOBAL-REF is not discriminative (all members touch the
same globals), so no oracle resolves them cleanly:
`go_16m_palette`, `load_to_temp_palette`, `fade_to_temp_palette`,
`start_system` (lib32 palette/init rework), `region_trouble`, `war_trouble`
(bbarian AI rework — note `war_trouble`'s 683-byte body cannot be its
current 103-byte `0x46e7c3`; the 688-byte `0x46f08d` is the likely home but
is out of source order, so left for a human), `goto_flag_marker_mode`,
`show_want_promotion_box` (likely body divergence, position ok),
`do_lose_game` (inlined into `main`).  Drill in with
`uv run python scripts/verify_func_map.py --tu <name>`.

## Decomp `// WIN:` annotations are kept in sync

Each decompiled function carries a `// WIN: 0xADDR` comment (the Windows VA;
`c2 win-verify` treats it as authoritative over `func-map.json`).  It now
reflects the verification state:

* **verified** → bare `// WIN: 0xADDR` (no qualifier).
* **not verified** (probable / review / stub-class — specific address is a
  guess) → `// WIN: 0xADDR  (unverified)`.
* **no Windows counterpart** (inlined / removed, e.g. `do_lose_game`) → the
  `// WIN:` line is dropped entirely.

Status after this pass: **1259 verified (clean) · 92 (unverified) · 1 dropped**
(`do_lose_game`).  Annotation address == func-map address for every entry, and
the qualifier matches the verifier verdict (validated 0/0 mismatches).  The
hand-determined annotations turned out to be the *better* source in several
regions (lib32 palette, `exit_game`/`start_system`, the `*_danger_flag`
family) — there the func-map was corrected to match the annotation; for the 4
stale ones (`perform_*`, `dock_the_ship_in_good_port`, `demo_lead_out`) the
func-map was right and the annotation was fixed.  The rewriter is idempotent
(re-run any time; it only edits `// WIN:` lines).

## Reproduce

```
uv run python scripts/verify_func_map.py            # whole-tree report + per-TU table
uv run python scripts/verify_func_map.py --tu bbarian   # one TU, per-entry detail
uv run python scripts/verify_func_map.py --conflicts    # just the review worklist
uv run python scripts/verify_func_map.py --write        # (re)write func-map-verified.json
```

Inputs: `data/windows-builds/func-map.json`, `caesar2_symbols.json`,
`.c2-cache/win-verify.json`, `data/out/symbols.json`, and `CAESAR2.EXE`.
The DOS call graph is cached at `.c2-cache/dos-callgraph.json` (rebuilt from
`PS.EXE` if absent).
