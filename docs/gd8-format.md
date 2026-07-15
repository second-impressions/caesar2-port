# Caesar II `.GD8` Format (`FORUM_X.GD8` — forum pick map)

> ImHex pattern: [`tools/imhex/caesar2_gd8.hexpat`](../tools/imhex/caesar2_gd8.hexpat).

## Overview

`FORUM_X.GD8` is the **department hit-test / pick map** for the forum screen. It is a
header-less 2-D byte grid: one byte per **8×8 screen cell**, holding the forum
**department id** under that cell. The game uses it to decide which department the mouse
is hovering over (so the matching panel highlights / activates on click).

The only `.GD8` file is `FORUM_X.GD8`; the name means "geometry data, 8-bit".

## Layout

```
Offset       Size   Description
------       ----   -----------
row * 0x50   0x50   One row: 80 bytes, one forum-department id per 8x8 cell
```

- **80 columns** (`0x50`), one byte each → 80 × 8 = 640 px wide.
- **No header**; rows are packed back-to-back.
- Retail `FORUM_X.GD8` is **3040 bytes = 80 × 38 rows** (38 × 8 = 304 px tall).

## Loading & Picking

`forum_constant_screen` reads the file into `scratch_buffer + 0x1d4c0`:

```c
readfile("forum_x.gd8", scratch_buffer + 0x1d4c0, 0xfa0, 0);  // 0xfa0=4000 cap; file is 3040
```

`show_forum_screen` picks the department under the cursor:

```c
strip = scratch_buffer + mouse_x / 8;
forum_dept_over = strip[(mouse_y - 0xb0) / 8 * 0x50 + 0x1d4c0];
```

So a grid cell maps to the screen as:

```
cell (col, row)  ⟷  screen (col*8, 0xb0 + row*8)
col = mouse_x / 8                (0..79)
row = (mouse_y - 0xb0) / 8       (grid starts at screen y = 0xb0 = 176)
```

The grid therefore covers the forum area from screen `y = 176` down. Above `y = 0xb0` the
view is the overview; at/below `y = 0x198` the bottom forum menu is used instead
(`over_forum_menu`).

## Cell Values (`FORUM_DEPT_*`, `entities.h`)

| Value | Department |
|------:|-----------|
| 0 | Overview (background / empty) |
| 1 | Admin (tax rates) |
| 2 | Career (personal cash) |
| 3 | Clerks (history) |
| 4 | Rome (emperor) |
| 5 | Advisor (help) |
| 6 | Army (centurion) |
| 7 | Industry |
| 8 | Slaves (plebs) |
| 9 | Exit (leave forum) |
| 10 | Temple (oracle) |
| 11 | Empire |

`12` (`FORUM_DEPT_END`) is one-past-the-last and does not appear as a cell value.

## Verification

- Retail `FORUM_X.GD8` size = 3040 = 80 × 38 (exact). ✓
- All cell bytes are in `0..11`; value `0` (background) dominates (≈1934 cells), with the
  ten department regions filling the rest. ✓
- The pick formula reduces from the current `show_forum_screen` decompile exactly. ✓
