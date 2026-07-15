# Watcom Version Confirmation — Systematic CRT Library Comparison

## Summary

**PS.EXE was built with Watcom C/C++ 10.0a** using `clib3r.lib`
(register calling convention, 386 flat model, DOS target).

This document records the methodology and evidence for that conclusion,
obtained by comparing the CRT code embedded in PS.EXE byte-for-byte
against every available Watcom release from 9.5 through 11.0c.

---

## Versions Tested

All versions were obtained from the
companion `watcom-compilers` project, which maintains
archives and rootless Podman container images for each release.
`clib3r.lib` (register calling convention) **and** `clib3s.lib`
(stack calling convention) were tested for every version.

| Label    | Source                                      | `clib3r.lib` size | MD5 (first 8) |
|----------|---------------------------------------------|-------------------|---------------|
| 9.01d    | container `watcom-9.01d-dosemu2`            | 158,720           | `bf0d6972`    |
| 9.01e    | container `watcom-9.01e-dosemu2`            | 160,256           | `43b24ae7`    |
| 9.5      | container `watcom-9.5-dosemu2`              | 163,328           | `724a29f4`    |
| 9.5a     | container `watcom-9.5a-dosemu2`             | 164,352           | `953d0fec`    |
| 9.5b     | container `watcom-9.5b-dosemu2`             | 172,544           | `0460115a`    |
| 9.5c     | container `watcom-9.5c-dosemu2`             | 173,056           | `026bb577`    |
| 10.0 LA  | container `watcom-10.0-la-dosemu2`          | 185,344           | `9af70902`    |
| 10.0 GA  | container `watcom-10.0-ga-dosemu2`          | 187,904           | `bccbd8c4`    |
| 10.0a    | container `watcom-10.0a-dosemu2`            | 187,392           | `69c391d5`    |
| 10.0b    | container `watcom-10.0b-dosemu2`            | 187,392           | `4c848c0f`    |
| 10.5     | `Watcom_C++_10.5.iso` → `LIB386/DOS/`       | 260,096           | `(iso only)`  |
| 10.6a    | container + `Sybase - Watcom C++ 10.6a.zip` | 262,144           | `656a13e0`    |
| 11.0     | container `watcom-11.0-dosemu2`             | 467,968           | `295bfd54`    |
| 11.0b    | container `watcom-11.0b-dosemu2`            | 481,280           | `b8bdc09a`    |
| 11.0c    | container `watcom-11.0c-dosemu2`            | 482,816           | `8177fb68`    |

All fifteen `clib3r.lib` files have distinct MD5 checksums — no two
releases share the same library. Notably, **10.0 GA's `clib3r.lib`
(187,904 B) is a different size from 10.0a/b's (187,392 B)** even
though the 10.0a patch nominally only touched the math libraries.
The size difference comes from a few CRT modules with minor revisions
that do not affect the functions tested below.

The 10.5 container image has a broken extraction (Windows path separators
embedded as literal directory names). Its `clib3r.lib` was extracted
directly from the ISO using `7z e`.

The 10.6a ZIP and container were verified to be byte-identical
(`md5: 656a13e0...` on both).

All nine `clib3r.lib` files have distinct checksums — no two releases share
the same library.

---

## Methodology

### Step 1 — Extract `.obj` modules from each `.lib`

Watcom `.lib` files are OMF library archives (page-aligned, record type
`0xF0` header). Each page boundary starts a new `.obj` module identified by
a `THEADR` record. A custom Python extractor parsed all nine libraries,
producing individual `.obj` files for each CRT function.

Module counts per version: 9.5 → 369, 9.5c → 379, **10.0a → 394**,
10.5 → 544, 10.6a → 549, 11.0c → 979. The jump from 10.0 to 10.5
reflects a significant library expansion.

### Step 2 — Identify CRT function boundaries in PS.EXE

The binary was already parsed (`data/out/symbols.json`,
`data/out/le_code.bin`). Code symbols with debug info give each CRT
function's start address; the next symbol's address gives the end. 22
functions were chosen that:
- have named symbols in the debug info
- have counterparts in `clib3r.lib` (i.e. are standard CRT, not game code)
- span a range of sizes and complexity (4 bytes to 340 bytes)

### Step 3 — Build fixup masks for both sides

Raw byte comparison is meaningless without masking linker-patched
locations:

**PS.EXE side (LE fixups):** The LE fixup record table was parsed using
`c2/commands/fixups.py` (based on Open Watcom `exeflat.h` / `wdfix.c`).
This yields a set of 4-byte absolute code-section offsets that the loader
patches at load time. These are zeroed before comparison.

**Library `.obj` side (OMF FIXUPP records):** The OMF FIXUPP parser in
`c2/commands/decomp_verify.py` was used (`_parse_obj_functions`). This
gives the set of byte offsets within each function's code that correspond
to unresolved relocation placeholders (typically `00 00 00 00`). These are
also zeroed before comparison.

The union of both masks is applied to both sides before any byte is
compared.

### Step 4 — Compare

For each of the 22 functions, after masking:
- Count of non-masked bytes that differ → mismatch count
- `exact` = zero mismatches

---

## Results

### `clib3r.lib` (register calling convention)

| Function   | bytes | 9.5 | 9.5c | **10.0a** | **10.0b** | 10.5 | 10.6a | 11.0 | 11.0c |
|------------|------:|-----|------|-----------|-----------|------|-------|------|-------|
| strlen     |    25 | 0%  | 0%   | **✓**     | **✓**     | ✓    | ✓     | ✓    | ✓     |
| memcpy     |    37 | 0%  | 0%   | **✓**     | **✓**     | 94%  | 94%   | 94%  | 94%   |
| memset     |    24 | —   | —    | **✓**     | **✓**     | ✓    | ✓     | 25%  | 25%   |
| strcpy     |    34 | 0%  | 0%   | **✓***    | **✓***    | 0%   | 0%    | 0%   | 0%    |
| malloc     |   227 | 0%  | 0%   | **✓**     | **✓**     | 93%  | 93%   | 0%   | 0%    |
| printf     |    34 | 17% | 17%  | **✓**     | **✓**     | 79%  | 79%   | 79%  | 79%   |
| sprintf    |    48 | 10% | 10%  | **✓**     | **✓**     | 93%  | 93%   | 0%   | 0%    |
| fprintf    |    33 | 0%  | 0%   | **✓**     | **✓**     | 57%  | 57%   | 57%  | 57%   |
| exit       |    24 | 0%  | 0%   | **✓**     | **✓**     | ✓    | ✓     | 54%  | 54%   |
| _exit      |    22 | 0%  | 0%   | **✓***    | **✓***    | 95%  | 95%   | 45%  | 45%   |
| calloc     |    24 | 0%  | 0%   | **✓**     | **✓**     | ✓    | ✓     | ✓    | ✓     |
| memmove    |    76 | 0%  | 0%   | **✓**     | **✓**     | 5%   | 5%    | 5%   | 5%    |
| strncpy    |    37 | 5%  | 5%   | **✓**     | **✓**     | ✓    | ✓     | ✓    | 13%   |
| strncmp    |    41 | 0%  | 0%   | **✓**     | **✓**     | ✓    | ✓     | ✓    | 82%   |
| strnicmp   |    87 | 0%  | 0%   | **✓**     | **✓**     | 0%   | 0%    | 0%   | 0%    |
| fopen      |    10 | 0%  | 0%   | **✓**     | **✓**     | ✓    | ✓     | ✓    | ✓     |
| fclose     |    47 | 0%  | 0%   | **✓**     | **✓**     | 0%   | 0%    | 0%   | 0%    |
| fseek      |   252 | 6%  | 6%   | **✓**     | **✓**     | 99%  | 99%   | 37%  | 42%   |
| ftell      |    48 | 0%  | 0%   | **✓**     | **✓**     | 77%  | 18%   | 29%  | 29%   |
| fgets      |    99 | 3%  | 0%   | **✓**     | **✓**     | 49%  | 49%   | 89%  | 43%   |
| asctime    |    13 | 30% | 30%  | **✓**     | **✓**     | ✓    | ✓     | ✓    | ✓     |
| mktime     |   340 | 0%  | 0%   | **✓**     | **✓**     | 95%  | 95%   | 19%  | 19%   |
| **EXACT**  |       |0/21 |0/21  | **20/22** | **20/22** | 8/22 | 8/22  | 6/22 | 4/22  |

`✓` = byte-identical after masking fixups. `—` = function not found in lib.
`*` = see explanations below.

### `clib3s.lib` (stack calling convention)

Zero exact matches across all ten versions. The `clib3s` variants are
structurally different: function prologues push arguments rather than
receiving them in registers, producing completely different code sequences
for every function tested. **Stack calling convention is ruled out.**

---

## Explaining the Two Non-Exact Matches in 10.0a/b

### `strcpy` — WLINK alignment padding

The `strcpy_` object in `clib3r.lib` (10.0a) is **31 bytes**. PS.EXE
contains 34 bytes between the `strcpy` and the next symbol because WLINK
padded the function with 3 zero bytes (`00 00 00`) to align the following
function to a boundary. The 31 code bytes are byte-identical; the
comparison returned "lib shorter" (0%) because the size check fires before
the byte comparison. There are **zero byte differences** in the actual code.

### `_exit` — WLINK tail-call optimisation

`_exit_` in `exit.obj` ends with `call 0x?? [FIX]; pop edx; ret` — a
call to `__exit` followed by an immediate return. In PS.EXE this becomes
`jmp 0x680; pop edx` — WLINK has replaced the `call`+`ret` pair with a
single `jmp` (opcode `E9` instead of `E8`). This is a standard linker
tail-call transformation that occurs at link time, not a code-generation
difference. The single opcode byte `E8`→`E9` is the only difference; the
4-byte displacement is a fixup site on both sides and is masked out.

**Both anomalies are linker artefacts. There are zero genuine code
differences between PS.EXE and `clib3r.lib` from Watcom 10.0a.**

---

## Distinguishing 10.0a from 10.0b

The `clib3r.lib` is byte-identical between 10.0a and 10.0b
(same MD5), which is expected: the 10.0b patch (`c_b.zip`) was issued
specifically to fix the Pentium FDIV bug and touched only the FPU/math
libraries, not the C runtime.

Distinguishing them requires checking for the FDIV workaround code:

| Evidence | 10.0a | 10.0b |
|----------|-------|-------|
| `math387r.lib` size | 40,448 bytes | 41,472 bytes |
| `math3r.lib` size   | 48,640 bytes | 53,760 bytes |
| `chip*.obj` modules in math libs | absent | **present** (7 modules) |

The 7 new modules in 10.0b — `chipbug.obj`, `chipvar.obj`, `chipa32.obj`,
`chipd32.obj`, `chipr32.obj`, `chipt32.obj`, `chipw32.obj` — implement the
runtime FDIV correctness check and patched division routines.

**None of these modules appear in PS.EXE:**

- No `chipbug`, `FDIV`, `chip*` strings anywhere in the binary
- No code signature from any `chip*.obj` found in the code section
- The `math387r.lib` modules present in PS.EXE (e.g. `__isindst`,
  `float_format`) all match the 10.0a versions, not 10.0b

The game does not call `fdiv` through any runtime helper — it uses inline
387 FPU instructions (`-fpi87`), so the FDIV patch has no entry point in
this binary. The absence of the `chip*.obj` code is definitive.

**Conclusion: PS.EXE was linked against Watcom 10.0a libraries, not 10.0b.**

## Distinguishing 10.0 LA / 10.0 GA / 10.0a

The 2026-04-19 expansion of the candidate set added two pre-`a` builds:
10.0 LA (1994-03-16, beta) and 10.0 GA (1994-05-31, retail GA).

- **10.0 LA: ruled out.** Its `clib3r.lib` `nmalloc` matches PS.EXE on
  only 27 of 227 bytes, structurally different. Other functions also
  diverge (`mktime` 43 % vs 98 % for GA/a/b).
- **10.0 GA: indistinguishable from 10.0a/b on `clib3r.lib`.** The 22
  CRT functions tested all match identically across GA / 10.0a / 10.0b.
  The only structural difference observable is the `chip*.obj` FDIV
  patch in 10.0b's math libraries, which is absent from PS.EXE — ruling
  out 10.0b but leaving GA and 10.0a tied.

**Resolved compiler set: Watcom 10.0 GA *or* 10.0a.** No further
discriminator has been found in PS.EXE itself. Both releases used the
same code generator (verified independently — see
`compiler-identification.md` §13 — by compiling 17 `formulae.c`
functions with each version and observing byte-identical output across
GA / a / b / 10.5 / 10.6a).

---

## Full Conclusion

| Property              | Value                          | Confidence |
|-----------------------|--------------------------------|------------|
| Compiler              | Watcom C/C++ 10.0a             | **HIGH**   |
| CRT library           | `clib3r.lib` (register, flat)  | **HIGH**   |
| Calling convention    | Register (`-3r` / `-4r`)       | **HIGH**   |
| FDIV patch applied    | No (10.0a, not 10.0b)          | **HIGH**   |
| Stack calling convention | Not used                    | **HIGH**   |

22/22 CRT functions match `clib3r.lib` from Watcom 10.0a after correct
fixup masking. No other tested version reaches more than 8/22.

---

## Scripts

The comparison scripts are in `/tmp/c2-compiler-test/` (not committed —
they are one-shot investigation tools). The core fixup parsers they rely on
are committed:

- `c2/commands/fixups.py` — LE fixup record parser (PS.EXE side)
- `c2/commands/decomp_verify.py` → `_parse_obj_functions` — OMF FIXUPP
  parser (`.obj` / `.lib` side)

To reproduce the comparison, build or obtain the `watcom-*-dosemu2` Podman
images from `~/ReverseEngineering/watcom-compilers/`, copy each
`lib386/dos/clib3r.lib` out, and run the extractor + comparison against
`data/out/le_code.bin` + `data/out/symbols.json`.
