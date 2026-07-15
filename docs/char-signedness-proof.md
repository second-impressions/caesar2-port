# Proof: PS.EXE was built WITHOUT `-j` (Watcom `char` default = unsigned)

**Status: SETTLED.** This is not a fingerprint estimate — it is a direct,
cross-build proof. Do not re-open it.

## The one-line answer

Watcom compiled `PS.EXE` with its **default** plain-`char` type, which is
**unsigned**. The `-j` flag (which would make `char` signed) was **not** used.
`PS_CFLAGS = "-bt=dos -mf -4r -s -d1"` is correct as-is.

## Why it's provable (and why a single binary can't do it)

For any *one* binary, the plain-`char` signedness is a gauge freedom: at a byte
site you can always match the bytes with either a bare `char` (relying on the
default) or an explicit `unsigned char`/`signed char`. So PS.EXE alone cannot
distinguish "bare `char` + no `-j`" from "explicit `unsigned char`".

The lock is that **the same engine source was shipped as three binaries whose
compilers have different `char` defaults**:

| build        | compiler            | default `char` |
|--------------|---------------------|----------------|
| `PS.EXE`     | Watcom (DOS)        | **unsigned** (with `-j` → signed) |
| `CAESAR2.EXE`| MSVC 4.0 (Win32)    | **signed** (with `/J` → unsigned) |
| Mac PPC      | CodeWarrior         | **signed** |

Anchor on a byte whose source type is known *independently of any binary*: a
**string pointer is a bare `char *`** — that's what text is, not a
reconstruction choice.

## The witness: `get_string_width(char *src, ...)`

Reading `*src` (a bare `char`):

```
PS.EXE (Watcom)      mov dl,[ebx];  and edx,0xff;  cmp edx,0x20     ; ZERO-extend  → UNSIGNED
                     mov dl,[edx+0x3ed0]                            ; width_table[c] — UNSIGNED index
Mac (CodeWarrior)    lbz r29,0(r3); extsb r5,r29;   cmpwi r5,0      ; SIGN-extend  → SIGNED
```

Same source token, opposite signedness across two shipped binaries.

> Note: the clean witness is **PS.EXE vs the Mac**. MSVC's default `char` is
> also signed, but its `/Od` spills `*src` to a stack local in this function,
> so CAESAR2.EXE does not show a clean `movsx` here — don't rely on it for
> this particular site. The Mac (`extsb`) is the unambiguous signed side.

## The deduction (both facts, jointly)

Enumerate what the original `src` type could be and check each build:

| original `src`             | PS predicts        | Mac predicts        | matches PS? | matches Mac? |
|----------------------------|--------------------|---------------------|:-----------:|:------------:|
| `unsigned char *`          | unsigned           | unsigned (`lbz`)    | ✓ | ✗ |
| `signed char *`            | signed (`movsx`)   | signed              | ✗ | ✓ |
| bare `char *`, Watcom `-j` | signed (`movsx`)   | signed              | ✗ | ✓ |
| **bare `char *`, no `-j`** | **unsigned (`and 0xff`)** | **signed (`extsb`)** | **✓** | **✓** |

Only the last row satisfies both binaries. Therefore, jointly:

1. The original source uses a **bare `char *`** for strings (original shape), and
2. **Watcom was compiled without `-j`** — a bare char came out *unsigned* in
   PS.EXE; with `-j` it would sign-extend like the Mac.

PS.EXE's `and 0xff` (plus the unsigned `width_table[c]` index) excludes
`signed char *` and `-j`; the Mac's `extsb` excludes `unsigned char *`.

## Corollary for source shape

- Bare `char` is the faithful original type for string pointers (`char *src`),
  NOT `unsigned char *`. Keep it bare.
- Explicit `unsigned char` / `signed char` fields are also faithful where the
  three builds *agree* on signedness (the whole-corpus struct-field scan found
  **0 disagreements** — every comparable byte field is treated identically in
  PS.EXE and CAESAR2.EXE). Those annotations are original, not noise.
- There is no `-j` migration to perform. Adding `-j` would deliberately make the
  DOS build stop matching PS.EXE.

## Reproduce

Cross-build byte-extend scan (x86 capstone for PS.EXE/CAESAR2.EXE, PPC for the
Mac PEF) over the ~1000 functions mapped in all three builds, looking for a byte
that PS zero-extends but Mac/Win sign-extends:

- PS.EXE function bytes: `symbols.json` code ranges + `_load_le_code_and_fixups`.
- CAESAR2.EXE: `c2.win_bytes` (`load_win_image`, `func_bytes`) + `ps_name` map in
  `data/windows-builds/caesar2_symbols.json`.
- Mac: `c2.macref.get('fr').func_bytes(name)`, disassembled with
  capstone PPC (big-endian).

The clean hits are the string readers `get_string_width` and
`get_next_word_length` (bare `char *src`, `movsx`-free in PS.EXE).
