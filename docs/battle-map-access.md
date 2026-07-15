# Battle map access model

This document records the source-shape conclusions for Caesar II's
`battle_map` users.  It is intended as the small proving ground before applying
similar reasoning to `region_map` and `city_map`.

## Layout

`battle_map` is a packed 52 × 52 grid of 4-byte cells:

```c
#define BATTLE_W            52
#define BATTLE_H            52
#define BATTLE_CELL_BYTES    4
#define BATTLE_ROW          (BATTLE_W * BATTLE_CELL_BYTES)    /* 208 */

extern unsigned char battle_map[BATTLE_W * BATTLE_H * BATTLE_CELL_BYTES];

struct battle_cell {
    unsigned char terrain;     /* +0x00 terrain / corpse terrain */
    unsigned char figure;      /* +0x01 occupying figure_no      */
    unsigned char dirty;       /* +0x02 dirty/highlight flags    */
    unsigned char arrow;       /* +0x03 arrow_no / aux layer     */
};
```

The struct is useful documentation, but the primary runtime coordinate stored
in entity records is a **byte offset** into `battle_map`, not a cell index and
not a pointer.

## Ground truth: byte-offset map refs

`remove_figure` is the smallest proof.  PS.EXE emits:

```asm
imul eax, eax, 0x58
mov  edx, [eax + figure_list+0x12]   ; figure_list[n].map_ref
xor  bl, bl
mov  byte ptr [edx + battle_map+0x1], bl
add  eax, figure_list
call clear_figure
```

So the C source shape is:

```c
int ref = figure_list[n].map_ref;
battle_map[ref + 1] = 0;
clear_figure(&figure_list[n]);
```

or the macro equivalent:

```c
BM_FIGURE(ref) = 0;
```

It is **not**:

```c
battle_cells[ref].figure = 0;        /* ref is not a cell index */
figure_list[n].map_ptr->figure = 0;  /* ref is not a pointer    */
```

## Macro/access forms and codegen

Experiments live in:

* `docs/codegen-experiments/battle_remove_figure_shape.py`
* `docs/codegen-experiments/battle_highlight_shape.py`

Run:

```bash
uv run c2 cgex run battle_remove_figure_shape
uv run c2 cgex run battle_highlight_shape
```

### `remove_figure` results

| source shape | size | diff vs PS |
|---|---:|---:|
| `battle_map[ref + 1]` | 32 | 0 |
| `BM_FIGURE(ref)` | 32 | 0 |
| `((struct battle_cell *)&battle_map[ref])->figure` | 32 | 0 |
| cached `struct battle_cell *cell = ...; cell->figure` | 32 | 21 |
| `battle_cells[ref].figure` | 33 | 10 |
| figure stores direct `struct battle_cell *` | 26 | 21 |

### `clear_all_highlights_from_battlemap` results

| source shape | size | diff vs PS |
|---|---:|---:|
| `battle_map[cm_sptr + 2] &= 0xf3` | 84 | 0 |
| `BM_DIRTY(cm_sptr) &= 0xf3` | 84 | 0 |
| `BCELL(cm_sptr).dirty &= 0xf3` | 84 | 0 |
| cached pointer inside loop | 86 | 44 |
| separate struct cell index | 80 | 49 |

## Rules for battle_map decompilation

### 1. Treat map refs as byte offsets

Entity fields such as `figure_list[n].map_ref` are byte offsets into
`battle_map`.

Use:

```c
BM_FIGURE(figure_list[n].map_ref)
BM_DIRTY(cell_off)
BM_ARROW(cell_off)
cell_off += BATTLE_ROW;
cell_off += BATTLE_CELL_BYTES;
```

Do not reinterpret these refs as cell indexes without explicit PS evidence.

### 2. Prefer byte-offset field macros or raw `battle_map[p + field]`

These match PS's dominant addressing mode:

```asm
mov/or/and byte ptr [reg + battle_map + field], ...
```

That is Watcom's global-index form with a byte offset already in `reg`.

### 3. `BCELL(p).field` is acceptable only as a one-shot lvalue

This is codegen-equivalent to `battle_map[p + field]` when used directly:

```c
BCELL(cm_sptr).dirty &= 0xf3;   /* exact in clear_all_highlights */
```

The cast does not survive as runtime code; Watcom folds it back to the same
`[reg + battle_map + field]` access.

### 4. Do not cache `&BCELL(p)` unless PS proves pointer addressing

This source shape changes Watcom's class from global-index to pointer:

```c
struct battle_cell *cell = &BCELL(p);
cell->dirty &= 0xf3;
```

The emitted access becomes pointer-relative (`[eax + field]`) rather than
`[eax + battle_map + field]`, and the tested functions regress.

Existing `pm_map3.c` users with cached `cell = &BCELL(ptr)` should be treated as
suspect until their local disassembly proves PS used pointer-relative access.

### 5. Do not introduce a global `battle_cells[]` struct array

`battle_cells[idx].field` asks Watcom to use a cell index and scale it by 4.
PS's common pattern already stores the byte-scaled offset, so the struct-array
form emits a different address shape.

### 6. Byte fields are unsigned unless disassembly shows `movsx`

The four `battle_cell` bytes are ordinary byte layers.  Use unsigned/`char`
semantics according to observed loads:

* `mov al`/`mov dl` + zeroing/masking/test => unsigned byte layer.
* `movsx byte ptr [...]` => use `signed char` at that specific consumer.

Do not globally make `figure`, `dirty`, or `arrow` signed.

## Transferable pattern for region_map/city_map

The battle-map conclusion matches the tiny region/city probes:

* `figure_list[n].map_ref` → byte offset into `battle_map`
* `army_list[n].map_ref` → byte offset into `region_map`
* `citizen_list[n].map_ref` → byte offset into `city_map`

So the larger maps should be treated as packed byte-addressed map planes first,
with struct definitions serving documentation and occasional one-shot field
lvalues — not as primary `struct cells[]` arrays.
