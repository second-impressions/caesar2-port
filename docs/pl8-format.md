# Caesar II `.PL8` Sprite/Image Format

> ImHex pattern: [`tools/imhex/caesar2_pl8.hexpat`](../tools/imhex/caesar2_pl8.hexpat).
> The 8-byte header + 16-byte descriptor layout below was re-verified against
> the current decompiled accessors (`display.c` `general_sprite` /
> `restore_picture_part`: `idx*16+8`, width@+0, height@+2, 3-byte
> `sprite_start`@+4, default_x@+8) and parses every demo `.PL8` sample.

## Overview

Caesar II uses `.PL8` files as its primary graphics container format. A single `.PL8`
file holds one or more **8-bit palette-indexed sprites** (or a full-screen image) packed
together with a compact header table. The name "PL8" stands for **Palette 8-bit**.

The format is used for everything from full-screen backgrounds and cutscenes to small
UI icons, cursor images, terrain tiles, and building sprites.

---

## Palette

> ImHex pattern: [`tools/imhex/caesar2_256.hexpat`](../tools/imhex/caesar2_256.hexpat)
> (768 bytes = 256 x 6-bit RGB; previews each entry's colour).

`.PL8` files contain **no embedded palette**. The palette is always stored separately,
either in a companion `.256` file (e.g. `CITYFIXT.256`) or in a global palette loaded
at startup. Palette files are 768 bytes: 256 entries × 3 bytes (R, G, B), where each
channel is a **6-bit VGA DAC value (0–63)**.

To convert to 8-bit RGB for modern image viewers, multiply each channel by 4:

```python
r8 = r6 * 4   # or r6 << 2  (gives 0–252)
g8 = g6 * 4
b8 = b6 * 4
```

This is confirmed by [`set_vga_palette`](PS.EXE) writing directly to VGA DAC port
`0x3c9`, which accepts 6-bit values.

---

## File Layout

```
Offset        Size        Description
------        ----        -----------
0x0000        8           File header (see below)
0x0008        N × 16      Sprite descriptor table: N entries of 16 bytes each
0x0008+N×16   variable    Pixel data area: raw 8-bit palette-indexed pixels,
                            packed consecutively (no padding between sprites)
```

The pixel data area begins immediately after the last descriptor entry. Each
descriptor's `sprite_start` field is an absolute byte offset from the start of the
file to that sprite's pixel data.

---

## File Header (8 bytes)

```
Offset  Size  Description
------  ----  -----------
0x00    1     Format version — always 0x02
0x01    1     Zoom level variant: 0x00 = full detail, 0x01 = medium, 0x02 = small
0x02    2     Sprite count N (little-endian uint16)
0x04    2     Tool metadata — group boundary index (see notes below)
0x06    1     Always 0x00 (padding / high byte of a uint16 that is always < 256)
0x07    1     Tool metadata — file ID or set index (see notes below)
```

> **Important:** The game engine **never reads bytes `0x04`–`0x07`** at runtime.
> Confirmed by disassembly: all sprite-access code computes `index * 0x10 + 8` directly
> and never dereferences the file header. These bytes are purely asset-tool metadata.

### Zoom Level Variants

Many sprite sets come in three zoom levels stored as separate files:

| Suffix / Name pattern | Byte `0x01` | Usage |
|-----------------------|-------------|-------|
| `*1*.PL8` / `*T.PL8`  | `0x00`      | Full detail (zoom level 0) |
| `*2*.PL8`             | `0x01`      | Medium detail (zoom level 1) |
| `*3*.PL8`             | `0x02`      | Small detail (zoom level 2) |

Examples: `BUILD1A.PL8` (0x00), `BUILD2A.PL8` (0x01), `BUILD3A.PL8` (0x02).

### Notes on bytes `0x04–0x05` — Group Boundary Index

This field marks the **last sprite index of the first logical group** within the file.
For files with a single homogeneous group it equals `N − 1`. For files with multiple
logical groups (e.g. background panels + overlay buttons, or multiple building types),
it marks the boundary between the first and second group.

Examples:
- `INT_BATL.PL8` (21 sprites, b4-5=9): sprites 0–9 are background panels; sprites
  10–20 are overlay buttons. The game calls `restore_picture_part(buf, 0..3)` for
  the first group only.
- `BUILD1A.PL8` (123 sprites, b4-5=24): sprites 0–24 are the first building type
  (a 5×5 diamond arrangement); sprites 25+ are additional building types.
- `MISC.PL8` (9 sprites, b4-5=0): sprite 0 is the compass rose (standalone); sprites
  1–8 are other UI elements.

The field is inconsistent across zoom-level variants of the same file set, confirming
it is not used at runtime.

### Notes on byte `0x07` — File ID / Set Index

A small value 0–15. Appears to be a **file identifier** assigned by the asset creation
tool, used to distinguish files within a logical set. Values are not consistent across
zoom-level variants of the same set, confirming this is tool metadata only.

Notable groupings observed:
- `0x0F` (15): Full-screen intro/logo images loaded via `display_pl8file`
  (`BACKGRND`, `LOGO1`, `LOGO2`, `TUT_04A`, `SMACKER`, `RAT_FRON`, `E_PARTS`)
- `0x00`: Interface files and city/province fixture sprites
- `0x01`: Event notification screens (`BATTLOST`, `BATTWON`, `FIRE`, `SICK`, etc.)
- `0x08`: Overlay sprites, panel sprites, battle interface

---

## Sprite Descriptor Entry (16 bytes)

Each entry describes one sprite within the file. Entries are indexed 0 to N−1.
Entry `i` is located at file offset `8 + i × 16`.

```
Offset  Size  Type          Description
------  ----  ----          -----------
+0x00   2     uint16 LE     width  — sprite width in pixels
+0x02   2     uint16 LE     height — sprite height in pixels
+0x04   3     uint24 LE     sprite_start — absolute file offset of pixel data
+0x07   1     uint8         padding / unknown (always 0x00)
+0x08   2     uint16 LE     default_x — default screen X position (pixels)
+0x0A   2     uint16 LE     default_y — default screen Y position (pixels)
+0x0C   1     uint8         blitter_type — rendering method (see below)
+0x0D   1     uint8         extra_rows / y_len — body row count for types 2–4
+0x0E   2     —             padding (always 0x0000)
```

`sprite_start` is a 3-byte little-endian value. The maximum addressable offset is
`0xFFFFFF` = 16,777,215 bytes, which is far larger than any known `.PL8` file.

The `default_x` / `default_y` fields give the sprite's default placement on the
640×480 screen. They are used by [`restore_picture_part`](PS.EXE) when blitting
interface background panels. For building sprites these give the composition offset
used to assemble multi-sprite buildings on a shared canvas.

The `blitter_type` byte at `+0x0C` selects the rendering method:

| Value | Name        | Description                                          |
|-------|-------------|------------------------------------------------------|
| 0     | flat        | Row-major pixels, no diamond encoding                |
| 1     | diamond     | Standard diamond tile (terrain)                      |
| 2     | ext-diamond | Diamond base + full-width body rows above            |
| 3     | left-roof   | Diamond base + left-half roof rows above             |
| 4     | right-roof  | Diamond base + right-half roof rows above            |

The `extra_rows` byte at `+0x0D` gives the number of body/roof rows above the
diamond base for types 2, 3, and 4. For types 0 and 1 this byte is always 0.

For flat sprites (type 0) and many UI/background files, all four bytes at `+0x0C`
are `0x00000000`.

---

## Pixel Data

Each sprite's pixel data is a flat array of `width × height` bytes, stored in
row-major order (left-to-right, top-to-bottom). Each byte is an 8-bit index into
the active 256-colour palette.

There is **no compression** and **no row padding** — pixels are packed tightly.

**Exception:** terrain tile sprites in `CITYFIXT`, `PROVFIXT`, and `BATLFIX` files
use a special **diamond-scan encoding** described in the next section.

### Transparency

Palette index `0x00` is conventionally transparent (not blitted) in sprite rendering.
The game's [`place_i_sprite`](PS.EXE) copies pixels unconditionally (no transparency
check), but [`place_i_large_diamond`](PS.EXE) (the diamond/tile blitter) skips zero bytes:

```c
if (unaff_ESI[n] != '\0') {
    *(char *)(dest + offset) = unaff_ESI[n];
}
```

So transparency behaviour depends on which blitter is used.

---

## Diamond-Scan Pixel Encoding (Terrain Tiles)

Terrain tile sprites in `CITYFIXT*.PL8`, `PROVFIXT*.PL8`, and `BATLFIX*.PL8` use a
special **diamond-scan encoding** instead of row-major order.  This is an optimisation
that stores only the pixels inside the diamond shape, skipping the transparent corners.

### Identification

A sprite is diamond-encoded when **all three** conditions hold:
- `width == 58` and `height == 30` (the bounding box of a full-size terrain tile)
- Actual stored byte count == **900** (not 1740 = 58×30)

The descriptor always declares `58×30`, but the stride between consecutive
`sprite_start` offsets is 900 bytes, confirming only 900 bytes are stored per sprite.

### Layout

The diamond has 30 rows (0–29).  Each row stores only the pixels inside the diamond
shape; the transparent corner pixels are not stored at all.

```
Row  0: cols 28–29   ( 2 px)   src bytes   0–  1
Row  1: cols 26–31   ( 6 px)   src bytes   2–  7
Row  2: cols 24–33   (10 px)   src bytes   8– 17
Row  3: cols 22–35   (14 px)   src bytes  18– 31
Row  4: cols 20–37   (18 px)   src bytes  32– 49
Row  5: cols 18–39   (22 px)   src bytes  50– 71
Row  6: cols 16–41   (26 px)   src bytes  72– 97
Row  7: cols 14–43   (30 px)   src bytes  98–127
Row  8: cols 12–45   (34 px)   src bytes 128–161
Row  9: cols 10–47   (38 px)   src bytes 162–199
Row 10: cols  8–49   (42 px)   src bytes 200–241
Row 11: cols  6–51   (46 px)   src bytes 242–287
Row 12: cols  4–53   (50 px)   src bytes 288–337
Row 13: cols  2–55   (54 px)   src bytes 338–391
Row 14: cols  0–57   (58 px)   src bytes 392–449   ← widest row
Row 15: cols  0–57   (58 px)   src bytes 450–507   ← mirror starts
Row 16: cols  2–55   (54 px)   src bytes 508–561
Row 17: cols  4–53   (50 px)   src bytes 562–611
Row 18: cols  6–51   (46 px)   src bytes 612–657
Row 19: cols  8–49   (42 px)   src bytes 658–699
Row 20: cols 10–47   (38 px)   src bytes 700–737
Row 21: cols 12–45   (34 px)   src bytes 738–771
Row 22: cols 14–43   (30 px)   src bytes 772–801
Row 23: cols 16–41   (26 px)   src bytes 802–827
Row 24: cols 18–39   (22 px)   src bytes 828–849
Row 25: cols 20–37   (18 px)   src bytes 850–867
Row 26: cols 22–35   (14 px)   src bytes 868–881
Row 27: cols 24–33   (10 px)   src bytes 882–891
Row 28: cols 26–31   ( 6 px)   src bytes 892–897
Row 29: cols 28–29   ( 2 px)   src bytes 898–899
```

**Total: 450 (top half) + 450 (bottom half) = 900 bytes.**

### Formula

```
top half    (row 0–14):  width = 4*row + 2,          col_start = 28 - 2*row
bottom half (row 15–29): width = 4*(29 - row) + 2,   col_start = 2*(row - 15)
```

### Source

Derived from disassembly of `place_i_large_diamond` at `0x00015ac6` in `PS.EXE`.
The function reads source bytes sequentially and scatters them to specific screen
column offsets, confirming the diamond-scan storage order.

### Decoding (Python)

```python
DIAMOND_WIDTH, DIAMOND_HEIGHT, DIAMOND_BYTES = 58, 30, 900

def decode_diamond(pixels: bytes) -> bytes:
    """900-byte diamond-scan → 1740-byte 58×30 row-major (transparent corners = 0)."""
    assert len(pixels) == DIAMOND_BYTES
    out = bytearray(DIAMOND_WIDTH * DIAMOND_HEIGHT)
    src = 0
    for row in range(DIAMOND_HEIGHT):
        if row < DIAMOND_HEIGHT // 2:
            width = 4 * row + 2
            col_start = 28 - 2 * row
        else:
            width = 4 * (DIAMOND_HEIGHT - 1 - row) + 2
            col_start = 2 * (row - DIAMOND_HEIGHT // 2)
        dst = row * DIAMOND_WIDTH + col_start
        out[dst : dst + width] = pixels[src : src + width]
        src += width
    return bytes(out)
```

---

## Known File Inventory

### Full-screen images (640×480, 1 sprite)

These files contain a single 640×480 sprite. [`display_pl8file`](PS.EXE) reads them
by seeking to offset `0x18` (= 8 header + 16 entry bytes) and reading `0x4B000`
(307,200 = 640×480) bytes directly into the screen buffer.

| File | Description | Companion palette |
|------|-------------|-------------------|
| `BACKGRND.PL8` | Main menu background | loaded separately |
| `EMPIRE.PL8` | Empire map background | loaded separately |
| `FORUM.PL8` | Forum/senate screen | loaded separately |
| `LOGO1.PL8` | Impressions logo | loaded separately |
| `LOGO2.PL8` | Sierra logo | loaded separately |
| `TUT_04A.PL8` | Tutorial screen | loaded separately |
| `BATTLOST.PL8` | Battle lost screen (320×152) | loaded separately |
| `BATTWON.PL8` | Battle won screen (320×152) | loaded separately |
| `CONGRAT.PL8` | Congratulations screen | loaded separately |
| `ARMYWARN.PL8` | Army warning screen | loaded separately |
| `MESSAGE.PL8` | Message screen | loaded separately |
| `FIRE.PL8` | Fire event screen | loaded separately |
| `RIOTERS.PL8` | Rioters event screen | loaded separately |
| `ROBBERY.PL8` | Robbery event screen | loaded separately |
| `SICK.PL8` | Sickness event screen | loaded separately |
| `WARNING.PL8` | Warning screen | loaded separately |

### Interface panels (multi-sprite, loaded at startup)

These are loaded in full by [`city_map_screen`](PS.EXE),
[`region_map_screen`](PS.EXE), and [`battle_screen`](PS.EXE) into `scratch_buffer`,
then individual sprites are blitted by [`restore_picture_part`](PS.EXE).

| File | Sprites | Description |
|------|---------|-------------|
| `INT_CITY.PL8` | 28 | City map interface panels |
| `INT_PROV.PL8` | 28 | Province/region map interface panels |
| `INT_BATL.PL8` | 21 | Battle map interface panels |

The game also pre-loads the first `0x1C8` = 456 bytes of each file at startup into
`int_city_header`, `int_region_header`, and `int_battle_header` globals via
[`load_start_graphics`](PS.EXE). For `INT_CITY.PL8` and `INT_PROV.PL8` (28 sprites)
this covers exactly `8 + 28×16 = 456` bytes. For `INT_BATL.PL8` (21 sprites,
`8 + 21×16 = 344` bytes) the read overshoots into pixel data, but the game only
accesses entries 0–20 by index so the extra bytes are harmless.

### Sprite sets (multi-sprite, zoom variants)

| Base name | Sprites | Description |
|-----------|---------|-------------|
| `BUILD1A/2A/3A.PL8` | 123 | Buildings set A (3 zoom levels) |
| `BUILD1B/2B/3B.PL8` | 115 | Buildings set B |
| `BUILD1C/2C/3C.PL8` | 71  | Buildings set C |
| `BUILD1D/2D/3D.PL8` | 100 | Buildings set D |
| `BUILD1F/2F/3F.PL8` | 100 | Buildings set F |
| `CITYFIXT/2/3.PL8`  | 140 | City fixture sprites |
| `PROVFIXT/2/3.PL8`  | 140 | Province fixture sprites |
| `BATLFIX2/3.PL8`    | 64  | Battle fixture sprites |
| `HOUSES1/2/3.PL8`   | 106 | House sprites |
| `MOUNTNS1/2/3.PL8`  | 92  | Mountain sprites |
| `LTLMEN1B/2B/3B.PL8`| 220 | Little men (soldiers) |
| `PRVBLD1A/2A/3A.PL8`| 88  | Province buildings A |
| `PRVBLD1B/2B/3B.PL8`| 112 | Province buildings B |
| `MY_STDS/2/3.PL8`   | 119 | Military standards |
| `OVERLAY1/2/3.PL8`  | 35  | Map overlay sprites |
| `CITYTOP1/2/3.PL8`  | 59  | City top-layer sprites |

### Always-loaded graphics (loaded at startup by `load_start_graphics`)

| File | Size (bytes) | Sprites | Description |
|------|-------------|---------|-------------|
| `LANDFILL.PL8` | 5,440 | 214 | Terrain/landfill tiles (2×2 px each) |
| `FONT_C2.PL8`  | 9,460 | 108 | Small font glyphs |
| `FONT3C2.PL8`  | 28,247 | 106 | Large font glyphs |
| `MOUSE.PL8`    | 8,312 | 22  | Cursor sprites |
| `SYSTEM.PL8`   | 38,984 | 64  | System/UI panel sprites |
| `PANELS.PL8`   | 23,441 | 79  | Game panel sprites |
| `SMACKER.PL8`  | 5,344 | 1   | Smacker logo sprite |
| `MISC.PL8`     | 3,584 | 9   | Miscellaneous UI sprites |

---

## Converting to PNG

To convert a `.PL8` file to PNG (or any modern format):

1. Read the 8-byte file header; extract `sprite_count` from bytes `0x02–0x03` (LE uint16).
2. Read `sprite_count` × 16-byte descriptor entries starting at offset `0x08`.
3. For each sprite entry `i`:
   - `width`  = LE uint16 at entry offset `+0x00`
   - `height` = LE uint16 at entry offset `+0x02`
   - `start`  = LE uint24 at entry offset `+0x04` (3 bytes)
   - Seek to `start` in the file; read `width × height` bytes as raw pixel indices.
4. Load the companion palette file (768 bytes = 256 × RGB triplets, 6-bit VGA values).
   Scale each channel: `r8 = r6 * 4`, `g8 = g6 * 4`, `b8 = b6 * 4`.
5. Map each pixel index through the palette to produce a 24-bit RGB image.
6. Save as PNG/BMP/etc.

### Python sketch

```python
import struct
from pathlib import Path
from PIL import Image

def load_palette(pal_path: Path) -> list[tuple[int, int, int]]:
    """Load a 768-byte VGA palette file; scale 6-bit → 8-bit."""
    data = pal_path.read_bytes()
    assert len(data) == 768
    return [(data[i*3]*4, data[i*3+1]*4, data[i*3+2]*4) for i in range(256)]

def load_pl8(pl8_path: Path, palette: list[tuple[int,int,int]]) -> list[Image.Image]:
    """Decode all sprites from a .PL8 file; return list of PIL Images."""
    data = pl8_path.read_bytes()
    version, zoom, count, last_idx, unk = struct.unpack_from('<BBHHH', data, 0)
    images = []
    for i in range(count):
        off = 8 + i * 16
        w, h = struct.unpack_from('<HH', data, off)
        start = struct.unpack_from('<I', data, off + 4)[0] & 0xFFFFFF  # 3-byte LE
        pixels = data[start : start + w * h]
        img = Image.new('RGB', (w, h))
        img.putdata([palette[p] for p in pixels])
        images.append(img)
    return images
```

> **Note:** For full-screen images (640×480, 1 sprite), `display_pl8file` in `PS.EXE`
> reads the pixel data directly at offset `0x18` without parsing the descriptor table.
> The sketch above is equivalent and more general.

---

## Lossy Re-encoding

Converting a `.PL8` to PNG and back produces a **visually identical** but not necessarily
**binary-identical** `.PL8` file.  The composed PNG canvas is a single flat image; when
sprites have overlapping bounding boxes (common in `BUILD*.PL8` files), the composition
is last-writer-wins at each pixel.  Re-encoding from the canvas recovers each sprite's
region independently, so pixels at overlap positions may differ from the original.

This only affects transparent (index 0) pixels at overlap boundaries.  The rendered
image is pixel-identical in all tested cases (82/82 files pass
`compose(decompose(compose(orig))) == compose(orig)`).

---

## Key Functions (PS.EXE)

All addresses are Ghidra virtual addresses.

| Symbol | Address | Description |
|--------|---------|-------------|
| `display_pl8file` | `0x0005a28b` | Load a full-screen `.PL8` + companion palette; fade in |
| `show_pl8file` | `0x0005a261` | Load a partial `.PL8` strip into the screen buffer |
| `restore_picture_part` | `0x0005ab70` | Blit one sprite from a loaded `.PL8` buffer by index |
| `general_sprite` | `0x0005a858` | Blit one sprite from `scratch_buffer` at a given screen position |
| `place_i_sprite` | — | Low-level pixel blitter (no transparency) |
| `load_start_graphics` | — | Loads all always-resident `.PL8` files at startup |
| `city_map_screen` | `0x0005b181` | Loads `INT_CITY.PL8` and blits 4 background parts |
| `region_map_screen` | `0x0005b2ca` | Loads `INT_PROV.PL8` and blits 4 background parts |
| `battle_screen` | `0x0005b3cb` | Loads `INT_BATL.PL8` and blits 4 background parts |
| `set_vga_palette` | — | Writes 256-entry palette to VGA DAC port `0x3c9` (6-bit values) |
| `set_palette` | — | Copies palette to `current_palette` global then calls `set_vga_palette` |

---

## File Layout Summary

```
Byte 0x00:  0x02                    ← format version (always 0x02)
Byte 0x01:  0x00 / 0x01 / 0x02     ← zoom level (0=full, 1=medium, 2=small)
Bytes 0x02–0x03: N (LE uint16)      ← sprite count
Bytes 0x04–0x05: (LE uint16)        ← tool metadata: group boundary index [NOT read at runtime]
Byte  0x06: 0x00                    ← always zero (padding)
Byte  0x07: 0–15                    ← tool metadata: file ID / set index [NOT read at runtime]

For each sprite i (0 ≤ i < N):
  Bytes 0x08 + i×16 + 0x00: width  (LE uint16)
  Bytes 0x08 + i×16 + 0x02: height (LE uint16)
  Bytes 0x08 + i×16 + 0x04: sprite_start (LE uint24, 3 bytes)
  Bytes 0x08 + i×16 + 0x07: 0x00 (padding)
  Bytes 0x08 + i×16 + 0x08: default_x (LE uint16)
  Bytes 0x08 + i×16 + 0x0A: default_y (LE uint16)
  Bytes 0x08 + i×16 + 0x0C: blitter_type (uint8), extra_rows (uint8), 0x0000 (padding)

Pixel data area (starts at 0x08 + N×16):
  For each sprite i: width[i] × height[i] bytes of 8-bit palette indices
  Sprites are packed consecutively; sprite_start[i] gives the absolute offset.
```
