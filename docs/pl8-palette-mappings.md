# PL8 to Palette (.256) Mappings

This document maps each `.PL8` file to its correct companion `.256` palette file, as determined by reverse engineering the game executable (`PS.EXE`) using Ghidra.

## Summary

The game uses **explicit palette loading** for most files, with context-based palette selection for sprite sets used during gameplay.

## Methodology

Analysis was performed by:
1. Searching for all `.256` and `.PL8` string references in `PS.EXE`
2. Decompiling functions that load these files
3. Tracing the call patterns to identify which palette is loaded with which PL8 file

## Palette Files Found in PS.EXE

The following `.256` palette files are explicitly referenced in the game code:

1. `cityfixt.256` - City fixture palette (loaded at startup)
2. `provfixt.256` - Province fixture palette (loaded at startup)
3. `batlfix2.256` - Battle fixture palette
4. `logo1.256` - Impressions logo palette
5. `logo2.256` - Sierra logo palette
6. `empire.256` - Empire map palette
7. `forum.256` - Forum screen palette
8. `backgrnd.256` - Main menu background palette
9. `rat_back.256` - Temple/rat screen background palette
10. `tut_01a.256` - Tutorial palette (pattern: `tut_XXa.256` for each tutorial page)
11. `xxxxxxxx.256` - Generic placeholder pattern (8 characters)

## Explicit PL8 → Palette Mappings

### Startup Graphics (loaded by `load_start_graphics` @ 0x00010e98)

These files are loaded at game startup and use the **city palette** (`cityfixt.256`):

| PL8 File | Palette | Notes |
|----------|---------|-------|
| `landfill.pl8` | `cityfixt.256` | Terrain/landfill tiles |
| `font_c2.pl8` | `cityfixt.256` | Small font glyphs |
| `font3c2.pl8` | `cityfixt.256` | Large font glyphs |
| `mouse.pl8` | `cityfixt.256` | Cursor sprites |
| `system.pl8` | `cityfixt.256` | System/UI panel sprites |
| `panels.pl8` | `cityfixt.256` | Game panel sprites |
| `smacker.pl8` | `cityfixt.256` | Smacker logo sprite |
| `misc.pl8` | `cityfixt.256` | Miscellaneous UI sprites |
| `int_city.pl8` | `cityfixt.256` | City map interface panels (header only at startup) |

The **province palette** (`provfixt.256`) is also loaded at startup for:

| PL8 File | Palette | Notes |
|----------|---------|-------|
| `int_prov.pl8` | `provfixt.256` | Province map interface panels (header only at startup) |
| `int_batl.pl8` | `provfixt.256` | Battle map interface panels (header only at startup) |

### Logo Screens (loaded by `lead_in_logos` @ 0x0005a1fb)

| PL8 File | Palette | Function |
|----------|---------|----------|
| `logo1.pl8` | `logo1.256` | Impressions logo |
| `logo2.pl8` | `logo2.256` | Sierra logo |

### Full-Screen Backgrounds

| PL8 File | Palette | Function | Address |
|----------|---------|----------|---------|
| `backgrnd.pl8` | `backgrnd.256` | Main menu background | `background_screen` @ 0x0005daa3 |
| `forum.pl8` | `forum.256` | Forum/senate screen | `forum_constant_screen` @ 0x0005da60 |
| `empire.pl8` | `empire.256` | Empire map background | `show_initreg_box` @ 0x0005cb64 |

### Battle Screen (loaded by `battle_screen` @ 0x0005b3f0)

| PL8 File | Palette | Notes |
|----------|---------|-------|
| `int_batl.pl8` | `batlfix2.256` | Battle interface panels |

### Temple/Forum Screens (loaded by `forum_temple_screen` @ 0x0005f094)

| PL8 File | Palette | Notes |
|----------|---------|-------|
| `rat_back.pl8` | `rat_back.256` | Temple background (rat screen) |
| `forumbit.pl8` | `forum.256` | Forum UI elements (loaded after rat_back) |

### Tutorial Screens (loaded by `do_a_tutorial_page` @ 0x00058a40)

Tutorial files follow a pattern where each tutorial page has its own palette:

| PL8 File Pattern | Palette Pattern | Notes |
|------------------|-----------------|-------|
| `tut_01a.pl8` | `tut_01a.256` | Tutorial page 1 |
| `tut_02a.pl8` | `tut_02a.256` | Tutorial page 2 |
| `tut_XXa.pl8` | `tut_XXa.256` | Pattern continues for all tutorial pages |

The code dynamically constructs the filename based on `tutorial_page` index.

## Sprite Sets (Buildings, Houses, etc.)

The following sprite sets are referenced in the code but **do NOT have explicit palette loads** in the functions analyzed. These likely use the **currently active palette** from the game context:

### City Context (uses `cityfixt.256`)

| PL8 Files | Expected Palette | Notes |
|-----------|------------------|-------|
| `build1a.pl8`, `build2a.pl8`, `build3a.pl8` | `cityfixt.256` | Buildings set A (3 zoom levels) |
| `build1b.pl8`, `build2b.pl8`, `build3b.pl8` | `cityfixt.256` | Buildings set B |
| `build1c.pl8`, `build2c.pl8`, `build3c.pl8` | `cityfixt.256` | Buildings set C |
| `build1d.pl8`, `build2d.pl8`, `build3d.pl8` | `cityfixt.256` | Buildings set D |
| `build1f.pl8`, `build2f.pl8`, `build3f.pl8` | `cityfixt.256` | Buildings set F |
| `cityfixt.pl8`, `cityfix2.pl8`, `cityfix3.pl8` | `cityfixt.256` | City fixture sprites (3 zoom levels) |
| `houses1.pl8`, `houses2.pl8`, `houses3.pl8` | `cityfixt.256` | House sprites |
| `citytop1.pl8`, `citytop2.pl8`, `citytop3.pl8` | `cityfixt.256` | City top-layer sprites |
| `ltlmen1b.pl8`, `ltlmen2b.pl8`, `ltlmen3b.pl8` | `cityfixt.256` | Little men (soldiers) in city |
| `overlay1.pl8`, `overlay2.pl8`, `overlay3.pl8` | `cityfixt.256` | Map overlay sprites |

### Province Context (uses `provfixt.256`)

| PL8 Files | Expected Palette | Notes |
|-----------|------------------|-------|
| `provfixt.pl8`, `provfix2.pl8`, `provfix3.pl8` | `provfixt.256` | Province fixture sprites |
| `mountns1.pl8`, `mountns2.pl8`, `mountns3.pl8` | `provfixt.256` | Mountain sprites |
| `prvbld1a.pl8`, `prvbld2a.pl8`, `prvbld3a.pl8` | `provfixt.256` | Province buildings A |
| `prvbld1b.pl8`, `prvbld2b.pl8`, `prvbld3b.pl8` | `provfixt.256` | Province buildings B |
| `my_stds.pl8`, `my_stds2.pl8`, `my_stds3.pl8` | `provfixt.256` | Military standards |

### Battle Context (uses `batlfix2.256`)

| PL8 Files | Expected Palette | Notes |
|-----------|------------------|-------|
| `batlfix2.pl8`, `batlfix3.pl8` | `batlfix2.256` | Battle fixture sprites |

**Note:** There is no `batlfix1.pl8` or `batlfixt.pl8` - battle mode only has zoom levels 2 and 3.

## Event/Message Screens

The following event screens are referenced in the code but their palette loading was not found in the analyzed functions. They likely use context-specific palettes or have same-name `.256` files:

| PL8 File | Expected Palette | Notes |
|----------|---------|-------|
| `battlost.pl8` | `battlost.256` (if exists) | Battle lost screen |
| `battwon.pl8` | `battwon.256` (if exists) | Battle won screen |
| `congrat.pl8` | `congrat.256` (if exists) | Congratulations screen |
| `armywarn.pl8` | `armywarn.256` (if exists) | Army warning screen |
| `message.pl8` | `message.256` (if exists) | Message screen |
| `fire.pl8` | `fire.256` (if exists) | Fire event screen |
| `rioters.pl8` | `rioters.256` (if exists) | Rioters event screen |
| `robbery.pl8` | `robbery.256` (if exists) | Robbery event screen |
| `sick.pl8` | `sick.256` (if exists) | Sickness event screen |
| `warning.pl8` | `warning.256` (if exists) | Warning screen |

## Key Findings

1. **The current fallback to `CITYFIXT.256` is WRONG for many files:**
   - Logo screens need their own palettes (`logo1.256`, `logo2.256`)
   - Forum screen needs `forum.256`
   - Background screen needs `backgrnd.256`
   - Empire map needs `empire.256`
   - Battle interface needs `batlfix2.256`
   - Province sprites need `provfixt.256`
   - Tutorial pages need `tut_XXa.256`
   - Temple screen needs `rat_back.256`

2. **Context-based palette usage:**
   - City gameplay uses `cityfixt.256` (loaded at startup)
   - Province gameplay uses `provfixt.256` (loaded at startup)
   - Battle gameplay uses `batlfix2.256` (loaded when entering battle)

3. **Sprite sets inherit the active palette:**
   - Building sprites (`BUILD*.PL8`) use the city palette
   - Province buildings use the province palette
   - These files do NOT have explicit palette loads in the code

4. **Same-name convention works for:**
   - Logo screens (`logo1.pl8` → `logo1.256`)
   - Tutorial screens (`tut_01a.pl8` → `tut_01a.256`)
   - Likely event screens (not confirmed in code analysis)

## Recommendations for Code Updates

The palette resolution logic in `c2/commands/pl8.py` (lines 425-446) should be updated to:

1. **First priority:** Check for explicit `--palette` option
2. **Second priority:** Check for same-name `.256` file (e.g., `BUILD1A.256` for `BUILD1A.PL8`)
3. **Third priority:** Use context-based mapping:
   - Files starting with `BUILD`, `HOUSES`, `CITYTOP`, `CITYFIX`, `LTLMEN`, `OVERLAY` → `CITYFIXT.256`
   - Files starting with `PROV`, `MOUNTNS`, `MY_STDS` → `PROVFIXT.256`
   - Files starting with `BATLFIX` → `BATLFIX2.256`
   - Files starting with `INT_CITY` → `CITYFIXT.256`
   - Files starting with `INT_PROV`, `INT_BATL` → `PROVFIXT.256`
   - Startup graphics (`LANDFILL`, `FONT`, `MOUSE`, `SYSTEM`, `PANELS`, `SMACKER`, `MISC`) → `CITYFIXT.256`
4. **Last resort:** Error message (do not blindly default to `CITYFIXT.256`)

## References

- `PS.EXE` analyzed with Ghidra
- Key functions:
  - `load_start_graphics` @ 0x00010e98
  - `lead_in_logos` @ 0x0005a1fb
  - `battle_screen` @ 0x0005b3f0
  - `forum_constant_screen` @ 0x0005da60
  - `background_screen` @ 0x0005daa3
  - `show_initreg_box` @ 0x0005cb64
  - `forum_temple_screen` @ 0x0005f094
  - `do_a_tutorial_page` @ 0x00058a40
