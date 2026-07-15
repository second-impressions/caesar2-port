# Allocator-only source spellings — cleanup inventory

**Status:** cleanup complete + historical audit (2026-07-14).

The source-witnessed S2/S5 defects, two overlay initialization defects, and
all eleven S1 allocator spellings have been removed while retaining DOS
byte-exactness.  This document is now the historical audit and mechanism
record; it is no longer a worklist.  The live scanner reports zero S1 sites.

The campaign originally ran beside the strict whole-code ComTail audit.  Both
are now closed: the strict code object is byte-exact, and no allocator-only
source spelling remains.

The important distinction is:

- a **scanner hit** is only suspicious syntax;
- a **confirmed allocator spelling** is contradicted by an independent source
  build or by PS's statement spine;
- a **source-shaped replacement** has positive evidence for the form that
  should replace it.

The previous version blurred those categories and incorrectly described live
locals in `get_region_query_info` as invented/write-only.

---

## Origin

Commit `3a084b6e` (`action: remove allocator-only source hacks`) kept
`build_city_item` byte-exact while deleting chained foreign carriers,
assignment-in-call/condition carriers, a dead constant carrier, a comma
self-identity, and two unused `action` locals.  The replacement was ordinary
semantic source plus Watcom-load-bearing declaration order.  Related source
cleanups are `6d4560b5`, `3673eca6`, `fd7344e2`, `ccda9c01`, `04e418ea`,
`d1c7dc7f`, and `5c796366`.

This audit asks where the same recovery is still needed.  Hard Rules #0, #3,
#4, #6, #7, and #8 apply: match source shape, judge trials by shape and asm,
and do not treat an old “kept verbatim” conclusion as source evidence.

---

## Evidence used

The scanner was rerun against the current `decomp/src` tree:

```bash
uv run python docs/codegen-experiments/allocator-hack-corpus-scan.py
```

It now reports 0 S1 sites, 0 S2 sites, 1 S3 site, 0 S4 sites, 2 S5 hits (both
third-party padding stubs), and 0 S6 hits.

Every curated function was then checked with:

```bash
uv run c2 shape-recon FUNCTION
uv run c2 win-verify -v FUNCTION
uv run c2 mac-fn FUNCTION
```

`shape-recon` supplies the PS `-d1` statement spine and current-source
correspondence.  `win-verify -v` supplies the original MSVC `/Od` instruction
stream beside the current source compiled the same way.  `mac-fn` supplies raw
CodeWarrior PPC instructions.  Conclusions below use those fused/raw binary
witnesses, not standalone Ghidra prose.

The integrated Mac column is not available for every traceback-named PPC
function because the decompile-symbol coverage is smaller than `mac-fn`'s
authoritative CodeWarrior traceback index.  Raw `mac-fn` output was available
for every function below except `barbarians_drop_by_city`, which is absent from
both indexed Mac builds.  Commit `80d7ff05` fixed a separate `shape-recon`
ingestion bug (`bool` missing from the Mac-cleaner prologue), restoring 20/22
aligned Mac statements for each overlay twin.

---

## Pattern taxonomy

| Tag | Suspicious recovered-source pattern | `build_city_item` / `action` example |
|-----|--------------------------------------|--------------------------------------|
| **A** | self-assignment or duplicated assignment used only as an extra allocator reference | `(city_costs[cover_gfx] = city_costs[cover_gfx], cover_gfx)` |
| **B** | chained assignment through an unrelated carrier | `tgfx_a = warned = forum_gfxdat[i * 4 - 0x2b8]` |
| **C** | unrelated assignment embedded in a call argument | `put_x3_area(over_x + dx, (tgfx_a = over_y + dy), ...)` |
| **D** | call result assigned in a condition although the local is otherwise unused | `if ((ok = put_x3_area(...)) != 0)` |
| **E** | literal written to a dead local only to pass that local | `shape = 0; put_message(0x65, 0, shape);` |
| **F** | unused local retained with a `(void)local` expression | `int route_idx; ... (void)route_idx;` |

Patterns A–F have no remaining **confirmed first-party allocator-hack**
candidate; the scanner's sole pattern-C-shaped hit is the legitimate
`get_linked_page` form classified below.

---

## Resolved allocator-only spellings

### S1 — duplicated-store / comma self-reference (pattern A)

These were not merely “odd-looking C.”  The Mac and Windows binaries showed
one semantic store per dispatch arm, while the recovered DOS source contained
two; the Mac lookup also disproved the `pseudo_map` comma self-store.  The
replacement campaign recovered the real structural levers:

| File | Function(s) | Deleted spelling | Recovered source fact |
|------|-------------|------------------|-----------------------|
| `pm_map1.c` | `show_left_overlay`, `show_right_overlay` | duplicated landfill assignment | PS's real `ov_image` local computes the subtraction once and supplies two natural stores (`aa0e5e41`) |
| `pm_map3.c` | `mid3_line_no_sides_base` | duplicated `0xf` / `0xd` stores | positive terrain guard; the zero case falls through naturally (`7be7ea37`, `71e0ce76`) |
| `pm_map3.c` | `mid3_line_with_sides_base` | duplicated `0xf` / `0xd` stores | same positive guard plus the middle-path `dirty = dirty & 0xf0` tree that honestly seats the first lookup (`7c2ef6f3`, `9be405fb`) |
| `pm_map3.c` | `show_battlemap_base` | four duplicate constants and the earlier comma self-store | positive guards on both edges plus PS's cross-arm `goto top_draw` / `goto bottom_draw`, which pins the correct two-instruction ComTail merge (`62d1b304`) |

All affected functions are byte-exact and their full PS/RC line streams are
clean.  The transitive Score-chain output added in `49fd342e` records why the
old duplicates had acted as RISCify/LdStAlloc compensators without treating
those compensators as source evidence.

---

## Completed source-witnessed cleanups

| Commit | Function(s) | Recovered defect and evidence |
|--------|-------------|-------------------------------|
| `7615b75a` | `get_nearest_reg_building` | Replaced the comma-separated zeros with the PS-shaped `best_x = best_y = 0` chain.  Windows emits the original zero-and-copy sequence, Mac independently has `li`/`mr`, and the DOS function remains exact. |
| `407f2b12` | `get_region_query_info` | Restored the PS L3074 quotient local and reused it for both coordinates; removed the redundant `map_x`/`map_y` casts.  Windows structural diff dropped 13→10 and the Mac binary independently reuses one quotient. |
| `c31dcd37` | `try_a_seamap_square` | Removed the dead `target` local/cast.  The Windows frame now matches the original 8-byte frame, Mac carries only the real result, and DOS remains exact. |
| `cb936b87`, `9bccc250` | `barbarian_invades_city` | Removed the indexed self-assignment and recovered the PS/Windows/Mac postincrement attempt loop, terrain local, and failure funnel.  The PS message statement is no longer split and DOS remains exact. |
| `f114d2d8` | `barbarians_drop_by_city` | Replaced the self-store with the witnessed attempt-loop/terrain/failure-funnel shape.  Windows regains its original four-slot frame and DOS remains exact. |
| `9593dc6a`, `4ea1eb3d` | `show_left_overlay`, `show_right_overlay` | Initialized `tile_in_building_range` to zero as in the Windows entry sequence.  Watcom removes the dead-before-write value, both DOS functions remain exact, and all 26 PS line transitions pair.  Their formerly separate S1 assignments were later closed by `aa0e5e41`. |

---

## Source-witnessed / legitimate scanner hits

### `get_linked_page` assignment-in-call

`mmedia.c:617`:

```c
mouse_in_area(help_page_hot_spots[i].x3, y_top += 0x12, x_w, 0x12)
```

This is legitimate semantic compact C, not an allocator-only foreign carrier.
`shape-recon` maps the call to one PS statement; the Mac binary performs
`addi y_top,y_top,0x12` immediately before the call, and Windows performs the
same in-place add before pushing the argument.  Style guide §11 records this
exact family idiom.

### Other exclusions

- S6 dead constant-carrier locals: **0 hits**.
- The 22 `(void)param` sites are genuine unused ABI parameters.
- `smackinp.c`'s two non-parameter `(void)` hits are third-party padding stubs.
- For-loop comma clauses and ordinary multi-zero chains are idiomatic and are
  deliberately excluded by the scanner.

---

## Priority order

Complete.  There are no remaining candidates to dispatch from this document.

---

## Workflow retained for future audits

1. Run `c2 disasm FUNCTION` and read the full PS `-d1` statement walk first.
2. Run `c2 shape-recon FUNCTION` and inspect the PS↔RC statement boundary at
   the candidate site.
3. Read raw independent binary evidence with `c2 win-verify -v FUNCTION` and
   `c2 mac-fn FUNCTION` (when present).
4. Replace only the allocator spelling with the witnessed semantic form;
   adjust C89 top-of-function declaration order if required.
5. Run `c2 decomp-verify -v -f FUNCTION --no-strict` and judge the shape line
   plus asm, not a byte count in isolation.  The function must remain
   byte-exact before it can be committed as a cleanup.
6. Run `c2 line-compare FUNCTION`; preserve/fix the original statement
   direction and offsets.
7. Commit each function separately with the recovered construct and the
   Windows/Mac/PS evidence in the postmortem.

If a witnessed semantic cleanup cannot yet preserve DOS exactness, retain the
function as open and document the failed source-shaped trials.  Do not restore
or add a claim that the allocator spelling was “verbatim original source.”
