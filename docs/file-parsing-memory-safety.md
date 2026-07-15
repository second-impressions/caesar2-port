# File-parsing memory-safety findings

An audit of the recovered data-file loaders and decoders for memory-safety
bugs.  Because the decompilation is byte-faithful to the shipped `PS.EXE`,
every bug documented here is present **verbatim in the original game** — it
is not a transcription artefact.

The recurring pattern is classic mid-90s DOS code: **the loaders trust
size / offset / dimension fields that come from the file itself, and the
decoders have no bound on the destination buffer.**  None of these are a
concern with the shipped, well-formed data files; each one is triggerable
by a corrupt or maliciously crafted data file (a modded/CD-swapped
`.lbm` / `.pic` / `.pl8`, or a hand-edited `resource.cfg`).

The relevant buffer sizes:

| Buffer | Size | Where |
|---|---|---|
| `internal_screen` | `screen_size` (0x4B000 = 307,200 for 640×480) `malloc` | `lib32.c:4611` |
| `scratch_buffer` | `scratch_buffer_size = 0x27100` = **159,488** `malloc` | `c2.c:141`, `lib32.c:4659` |
| `format_buffer` | fixed 0x7D0 = 2000 | `c2_data.h:390` |

---

## HIGH — decoder output overflows

### 1. `convert_lbm_file` — unbounded RLE write into `internal_screen`

`decomp/src/lib32.c:662` (byte-exact to PS, run-ledger 161/161 → definitely
in the original).

The `.lbm` BODY chunk is PackBits-RLE-decoded into `dst` (= `internal_screen`,
307,200 bytes):

```c
if (c > length) return 8;          /* bounds the INPUT only */
for (i = 0; i < c; ++i) {
    tag = *p++;
    if (tag > 0x80) {
        run = *p++;
        for (k = 0; k < 0x100 - tag + 1; k++) *dst++ = run;  /* up to 128 bytes out */
        ++i;
    } else {
        for (k = 0; k < tag + 1; k++) *dst++ = *p++;
        i += tag + 1;
    }
}
```

The only guard, `if (c > length)`, limits how much *input* is consumed.
There is **no check that `dst` stays inside `internal_screen`.**  A run token
`0x81 XX` costs 2 input bytes but emits 128 output bytes — a ~64×
amplification — so a crafted `.lbm` decompresses far past the 307,200-byte
destination.  Reached via `show_lbm()` (tutorial mode).

### 2. `evacuate` — LZHUF output bounded only by a file-supplied length

`decomp/src/pump.c:836`.

```c
my_strcpy((char *)(src + 4), (char *)&hdr, 4);   /* uncompressed length from file bytes 4..7 */
textsize = hdr;
...
for (count = 0; count < textsize; ) {
    ...
    pmp_outbuff[pmp_optr++] = c;   /* writes into internal_screen, no output cap */
}
```

The decode loop runs until `count == textsize`, where `textsize` is the
**claimed uncompressed size taken straight from the `.PIC` header.**  Nothing
checks it against the destination.  The caller *does* test
`if (evacuate(...) > 0x4e200)` — but that is evaluated **after** `evacuate`
returns, i.e. after the overflow has already happened.  A `.PIC` header
claiming a huge size overflows `internal_screen`.

---

## MEDIUM/HIGH — raw reads larger than the buffer

### 3. `show_picfile` / `display_picfile` read 0x4E200 into a 0x27100 buffer

`decomp/src/display.c:93,117`.

```c
readfile(fname, ((void *)scratch_buffer), 0x4e200, 0)   /* asks for 320,000 bytes */
```

`scratch_buffer` is `malloc(scratch_buffer_size)` with
`scratch_buffer_size = 0x27100` = **159,488 bytes** (`c2.c:141`,
`lib32.c:4659`).  `readfile` passes that size to `read(fd, buf, 0x4e200)`, so
any `.PIC` on disk larger than ~156 KB overflows the heap buffer *before* any
decompression.  Notably the sibling `show_lbm()` does this correctly — it
reads `scratch_buffer_size` and bails with an error if the file is too big —
which makes the `.PIC` path's hardcoded `0x4e200` look like a genuine
oversight rather than an intended invariant.

### 4. `.pl8` sprite loads use a file-controlled read size

`decomp/src/display.c:506,530,556` (`draw_city_map_part`,
`draw_region_map_part`, `draw_battle_part`).

```c
sprite_width  = int_city_header[n * 8 + 4];   /* header loaded from int_city.pl8 */
sprite_height = int_city_header[n * 8 + 5];
readfile("int_city.pl8", scratch_buffer, sprite_width * sprite_height, offset);
```

`int_city_header` is filled directly from the file:
`readfile("int_city.pl8", int_city_header, 0x1c8, 0)` (`c2.c:780`).  So
`sprite_width` and `sprite_height` are attacker-controlled `unsigned short`s,
and their product is used unvalidated as the read length into the
159,488-byte `scratch_buffer`.  Large dimensions overflow it; the product is
also computed in `int`, so `width * height` can integer-overflow / truncate
as well.

---

## LOW — read overruns / trust issues

- **`read_config`** (`decomp/src/lib32.c:~614`): reads 1000 bytes, scans for
  `"resaud"`, then `p += 7; return *p;`.  A match near the end of the window
  makes both the 6-byte `my_strcmp` and the `+7` deref read several bytes past
  the 1000-byte region.  Driven by `resource.cfg`.
- **`convert_lbm_file` chunk scans**: `chunk_search = length` while scanning
  forward from an already-advanced `p` can walk past the file data (still
  inside the large scratch allocation, so an info-read rather than a crash),
  and the CMAP copy blindly reads 0x300 bytes / BODY reads without verifying
  the chunk is actually that long.
- **`load_format_buffer_from_disk` / `load_media_entry`**
  (`decomp/src/lib32.c:2921`, `decomp/src/mmedia.c:108`): the read *offset*
  (`word_value + 0x1c` / `this_media_entry.text_offset`) is taken from the
  file, so a crafted file can point the fixed-size `format_buffer` (0x7D0)
  read at an arbitrary file region.  The read *size* is fixed, so no
  overflow, but it is an unvalidated seek.

---

## What is safe

The save/load path (`loadgame` / `savegame` in `decomp/src/loadsave.c`) is
**safe**: it reads into blocks whose sizes are the game's own in-memory
registered sizes (`savegame_entries[i].size`), not values from the file, and
the `history.dat` payload is a fixed 0xFA0 bytes.  The real defects are all in
the **graphics / media decoders** (`.lbm`, `.pic`, `.pl8`), where file-supplied
sizes, offsets, and sprite dimensions flow unchecked into fixed heap buffers
and into RLE / LZHUF decoders with no destination bound.
