# LZHUF reference sources (`src/pump.c`)

Caesar II's `pump.c` is **Okumura / Yoshizaki LZHUF** — the LZSS + adaptive-Huffman
codec that is also LHA's "lh1" scheme (Haruyasu Yoshizaki, 1988; LZSS from
Haruhiko Okumura's LZARI; English translation by Kenji Rikitake).  Impressions
copied it into their packing module and:

* **de-structured it** — the canonical struct members became file-scope
  globals (`son`, `getbuf`, `getlen`, `match_length`, `match_position`,
  `lson`/`rson`/`dad`/`prnt`/`freq`, `text_buf`, …);
* **pointer-ized the tables** — `int lson[N+1]` → `short *lson`, etc.;
* **stripped the file I/O** — `getc()`/`putc()` became reads/writes of the
  in-memory `pmp_inbuff` / `pmp_outbuff` buffers (`pmp_iptr`/`pmp_optr`);
* kept Okumura's original constants: **N = 4096, F = 60, THRESHOLD = 2**.

## THE discovery — 16-bit `int` → 32-bit `short`

LZHUF was written for **16-bit-`int` MSDOS compilers** (Turbo/Borland C —
the original `#include <alloc.h>`).  The justsolve wiki even warns it
*"will not work correctly if compiled by a modern C compiler … differs
depending on the compiler's in-memory format."*

So every 16-bit DOS `int` is a **`short`** in the 32-bit Watcom port, and
the codec's bit buffer is a 16-bit `unsigned`.  Matching these types is what
flips the functions byte-exact:

| LZHUF source type (16-bit DOS) | Caesar II / 32-bit Watcom | why |
|---|---|---|
| `unsigned getbuf` | **`unsigned short getbuf`** | 16-bit refill ⇒ `xor ch,ch` shift-count zero-extend, `and eax,0xffff` reads |
| `unsigned putbuf` | **`unsigned short putbuf`** | same |
| `int GetBit(); int i;` | **`short GetBit(void); short i;`** | 16-bit return ⇒ `setl al; xor ah,ah` (not `and eax,0xff`) |
| `int GetByte(); unsigned i;` | `int GetByte(void); unsigned short i;` | |
| `void InsertNode(int r)` | **`void InsertNode(short r)`** | `r` is a 16-bit window index ⇒ the entry `cwde` |
| `int lson[N+1]` … | `short *lson` … | 16-bit table cells, `mov ax,[..]` not `movsx`/4-byte |
| `unsigned freq[T+1]` | `unsigned short *freq` | sentinel `freq[T]=0xffff` must stay unsigned |
| `short DecodeChar(); USHORT c;` | `short DecodeChar(void); unsigned short c;` | 16-bit `c += GetBit(); c = son[c]` eager-wraps in 16-bit |

This single insight (plus the `getbuf`/`freq` type overrides in
`c2/commands/c_source.py` / `entities.h`) made GetBit, GetByte, InsertNode,
DeleteNode, StartHuff, reconst, update, DecodeChar and DecodePosition all
byte-exact — including residues previously documented as "hard, no source
lever" (the DecodeChar eager-wrap).

## Files here

* **`LZHUF-amiga.c`** — *the* matching shape.  An Amiga (`__regargs`,
  register-calling, like Watcom's `__watcall`) port that is **already
  de-structured, pointer-ized and `short`-typed** exactly like PS:
  `unsigned char *text_buf; short match_position, match_length, *lson,
  *rson, *dad; USHORT getbuf; short GetBit(); void __regargs
  InsertNode(short r); short DecodeChar();`.  Read this for the per-function
  source shape.
  Source: `https://www.amiga-stuff.com/source/archivers/LZHUF.C`
  (retrieved via the Wayback Machine; the live site was 502 at capture time).

* **`LZHUF-original.c`** — Okumura/Yoshizaki/Rikitake canonical original
  (file-scope globals, `int` arrays — i.e. 16-bit DOS ints).  Read this for
  the authoritative *algorithm*.
  Source: `https://github.com/e-n-f/lzss/blob/master/LZHUF.C`

## Provenance / where this was found

* justsolve.archiveteam.org/wiki/LZHUF — catalogue of LZHUF variants; led to
  both the original (textfiles `okumura.zip` / `LZHSRC10.ZIP` lineage) and
  the de-structured Amiga port.
* ham-radio-software/lzhuf (JNOS fork) — a *modernized* struct version
  (`struct lzhufstruct`, `N=2048`, 32-bit `unsigned getbuf`).  Useful to
  confirm the algorithm, but its types do **not** match PS — it had been
  ported to 32-bit ints, which is the opposite of what we needed.

The big remaining diffs (`Putcode`, `pump`, `evacuate`) are the
Caesar-specific buffer-I/O wrappers, not pure LZHUF.
