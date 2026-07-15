# Caesar II Build Environment

Forensic analysis of the PS.EXE binary to identify the exact compiler,
linker, libraries, and build configuration used to produce the original
Caesar II executable. This information is needed to eventually source
the original toolchain for byte-identical CRT rebuilds.

## Compiler: Watcom C/C++ 10.0

**Confidence: HIGH**

| Evidence | Location | Value |
|----------|----------|-------|
| CRT copyright string | code section @ `0x062D15` | `"WATCOM C/C++32 Run-Time system. (c) Copyright by WATCOM International Corp. 1988-1994. All rights reserved."` |
| DOS/4GW Professional | MZ+BW section @ `0x03168C` | Version **1.97**, built `May 19 1994 14:44:26` |
| Publisher name | copyright string | "WATCOM **International** Corp." (pre-Powersoft acquisition) |

**Reasoning:**
- Copyright `"1988-1994"` pins it to **Watcom 10.0** (released June 1994).
  Watcom 9.5 would say `"1988-1993"`, and Watcom 10.5 would say `"1988-1995"`.
- DOS/4GW Professional 1.97 is from the same 1994 toolchain era.  The Watcom
  10.0a retail CD supplies the ordinary `DOS4GW.EXE`; the separate
  Professional kit and `4GWBIND.EXE` have now been located online.  See
  [`external-libs/online-binary-findings-2026-07-15.md`](external-libs/online-binary-findings-2026-07-15.md).
- "WATCOM International Corp." was renamed to "Powersoft" in 1995 after
  acquisition by Sybase, then "Sybase" for 11.0. The use of the original
  company name confirms pre-1995 toolchain.

**Confirmed: Watcom C/C++ 10.0a** — see
[`docs/compiler-version-confirmation.md`](compiler-version-confirmation.md)
for full methodology and evidence.

**Verification summary (systematic cross-version comparison):**
- All available Watcom releases tested: 9.5, 9.5a, 9.5b, 9.5c, 10.0a, 10.0b,
  10.5, 10.6a, 11.0, 11.0c — both `clib3r.lib` (register) and `clib3s.lib`
  (stack) for each.
- Method: extract `.obj` modules from each lib; mask OMF FIXUPP relocation
  sites (`.obj` side) and LE fixup records (PS.EXE side); compare remaining
  bytes. Parsers: `c2/commands/fixups.py` + `c2/commands/decomp_verify.py`.
- Result: **10.0a scores 22/22 exact function matches**. Next best is 10.5/10.6a
  at 8/22. All 9.x versions score 0/22. `clib3s` scores 0/22 for every version.
- The two apparent non-matches in 10.0a are linker artefacts (WLINK alignment
  padding for `strcpy`; WLINK tail-call rewrite `call`→`jmp` for `_exit`).
  There are zero genuine code differences.
- **10.0b excluded**: the 10.0b Pentium FDIV patch adds 7 `chip*.obj` modules
  to the math libraries; none appear in PS.EXE. The binary uses inline 387
  FPU instructions (`-fpi87`) with no FDIV runtime helper.

**Key files on the disc** (`CDs/WATCOM_C10A.zip` → `WATCOM_C10A.ISO`):
- `watcom/binb/wcc386.exe` — 32-bit C compiler (DOS host)
- `watcom/binnt/wcc386.exe` — 32-bit C compiler (Win32/NT host)
- `watcom/binb/wasm.exe` — assembler (DOS host)
- `watcom/binnt/wasm.exe` — assembler (Win32/NT host)
- `watcom/bin/wlink.exe` — linker (DOS host)
- `watcom/binnt/wlink.exe` — linker (Win32/NT host)
- `watcom/lib386/dos/clib3r.lib` — C runtime (flat model, register convention)
- `watcom/bin/dos4gw.exe` — ordinary DOS/4GW 1.97 runtime (not the
  Professional binder kit)

**Extracting CRT modules:**
```sh
# Extract ISO from zip
mkdir -p data/watcom && cd data/watcom
unzip ../../CDs/WATCOM_C10A.zip && mv c2/WATCOM_C10A.ISO .
# Mount
sudo mount -o loop,ro WATCOM_C10A.ISO /tmp/watcom_mount
# Copy CRT library
cp /tmp/watcom_mount/watcom/lib386/dos/clib3r.lib .
# Extract individual .o modules
mkdir crt_objs && cd crt_objs
wlib ../clib3r.lib :exit    # extracts exit.o
wlib ../clib3r.lib :prtf    # extracts prtf.o
# Disassemble to verify
wdis exit.o                 # shows code + fixups
```


## Game Compiler Flags

**Confidence: HIGH** (confirmed by byte-level function matching; see
`docs/compiler-identification.md` for full methodology)

```
wcc386 -bt=dos4g -4r -mf -d1 -s <source.c>
```

| Flag | Confidence | Evidence |
|------|------------|----------|
| `-bt=dos4g` | HIGH | DOS/4GW Professional target |
| `-4r` (486, register calling) | MEDIUM | System req: 486SX 25 MHz minimum; default/`-4r`/`-5r` all produce identical results |
| `-mf` (flat model) | HIGH | 32-bit flat model, `USE32` segments |
| `-d1` (line numbers only) | HIGH | Debug symbols contain function names + line numbers, no type info |
| `-s` (no stack checking) | HIGH | No `__CHK`/`__STK` prolog in game functions (except the `#pragma on(check_stack)` region of lib32.c, see below); byte-match fails without `-s` |

**Exception — lib32.c (module 13): a `#pragma on(check_stack)` mid-file,
not a per-file flag.**

`lib32.c` is the only module that emits stack-overflow checks: 107 calls
to `__CHK`, all in module 13, zero anywhere else in the game. An earlier
revision of this doc concluded "lib32.c was compiled without `-s`". That
is **wrong** — the mechanism and scope are both different. The real story
(verified against PS.EXE):

1. **It is the stack-overflow check, not a large-frame page probe.**
   `__CHK → __STK` computes the projected frame base and compares it
   against `_STACKLOW` (→ `__STKOVERFLOW`) — the exact check that `-s`
   removes. It is *not* a `>4 KB` page-touch: 8–20 byte accessor frames
   (`get_fb_length` pushes `8`, `get_buffer_ofset` pushes `0xc`) call it,
   and `__GRO` (the page-probe helper) has **zero** callers.
2. **It is only the back half of the file.** Of the 158 code functions
   in lib32.c, exactly 107 call `__CHK` and 51 do not. The split is a
   clean source-line threshold with **zero exceptions**: every function
   at PS source line ≥ 1300 is checked, every one below is not.
   - Unchecked front half (L352–L1281): file I/O (`get_directory`,
     `readfile`, `writefile`), SVGA mode setup, palette/fade, screen
     clears/blits — flat, shallow, non-recursive hardware code.
     (`get_directory` has a 44-byte frame yet calls no `__CHK`, so frame
     size is *not* the discriminator.)
   - Checked back half (L1300→EOF, starting at `install_mouse`): the
     mouse callback path, drawing primitives (`Bresenham_decision`,
     `draw_a_line/box/diamond`), font layout + format-buffer machinery,
     delays and key polling — the variable-depth / recursion-prone code
     where a stack blowout during development was a live risk.
3. **It is one translation unit, toggled in source.** The `-d1` line
   numbers run monotonically straight across the boundary
   (`click_handler` L1281 → `install_mouse` L1300 → … → `get_fb_width`
   L1926), and symbols.json attributes both halves to the same debug
   module. That rules out "two objects concatenated". The single clean
   flip at a function boundary inside one TU is the signature of a
   **`#pragma on(check_stack)`** placed at ~line 1300 of lib32.c.

Nobody "enabled" checking for this file: stack checking is the Watcom
*default*, the whole game build adds `-s` to turn it off, and the author
dropped a `#pragma on(check_stack)` partway through lib32.c to keep the
guard on the scary half. Our `decomp/src/lib32.c` reproduces this with a
`#pragma on(check_stack)` between `click_handler` and `install_mouse`;
functions on both sides are byte-exact.

**Optimisation flags:** No individual sub-flags (`-ot`, `-oi`, `-ob`,
etc.) are needed to match tested functions. Adding `-ot` breaks the
match. Refinement against larger functions is needed — see
`docs/compiler-identification.md §9`.

**CPU target detail:** `-3r` (386 timings) was explicitly **rejected** —
it causes the compiler to emit `imul eax,edx,10` instead of the
`shl/add/add` shift-reduce sequence seen in the binary for `i*10`.
The 486SX minimum system requirement supports `-4r`.


## DOS/4GW Professional

**Confidence: HIGH**

| Field | Value | Location |
|-------|-------|----------|
| Product | DOS/4GW Professional | `0x031985` in PS.EXE |
| Version | 1.97 | `0x0316A2` |
| Build date | May 19 1994 14:44:26 | `0x03168C` |
| Copyright | Rational Systems, Inc. 1990-1994 | `0x03165C` |
| MZ stub copyright | Rational Systems, Inc. 1987-1993 | `0x00025C` |

PS.EXE contains three executables chained together:
1. **MZ stub** (62 KB) — small DOS/4G loader
2. **BW section 1**: `VMM.EXP` (60 KB) — DOS4G virtual memory manager
3. **BW section 2**: `4GWPRO.EXP` (95 KB) — DOS/4GW Professional runtime
4. **MZ stub** (11 KB) — LE loader stub
5. **LE executable** — the actual game (code + data)

**Note:** DOS/4GW Professional was the commercial version bundled with
Watcom C/C++. The free `DOS4GW.EXE` was a stripped-down redistributable.
The Professional version in the binary is the full development runtime,
suggesting the game shipped with the Watcom-bundled extender.


## Miles Sound System (AIL)

**Confidence: HIGH** (for version), **MEDIUM** (for exact SDK revision)

| Field | Value | Location |
|-------|-------|----------|
| Library | AIL/32 (Audio Interface Library) | function names throughout |
| Version | 3.03 | data section @ `0x001188` |
| Modules | AIL3DIG (digital), AIL3MDI (MIDI) | data section @ `0x002130`, `0x002138` |
| Sub-modules | AILSS, AILSFILE, AILXMIDI, AILXDIG | function name prefixes in code |
| Build path | `R:\NET\LIBS\AIL\DEV3\FLAT\` | debug info @ `0x1247CE` |
| Source files | `dllload.c`, `aildebug.c`, `ail.c`, `ailss.c`, `ailsfile.c`, `ailxmidi.c`, `ailxdig.c` | debug info paths |
| Driver refs | `SB16.DIG`, `SBPRO.DIG`, `SBLASTER.DIG` | strings @ `0x0F2C24` |

AIL 3.03 is the DOS flat-model (32-bit protected mode) version of the
Miles Sound System, designed for use with DOS extenders like DOS/4GW.

**Build path analysis:** `R:\NET\LIBS\AIL\DEV3\FLAT\` suggests the Miles
SDK was on a network drive (`R:\NET\LIBS\`) in the Impressions Games
development environment. `DEV3\FLAT` indicates the DOS flat-model variant
of the AIL version 3 development kit.

**What to look for:**
- Miles Sound System SDK version 3 / AIL/32 version 3.03
- Produced by Miles Design, Inc. (later RAD Game Tools)
- 1994-era SDK for DOS/4GW flat-model applications
- Would contain `AIL32.LIB` or similar for Watcom C/C++ 32-bit

**Uncertainty:**
- The exact SDK patch level is unknown. Miles 3.03 could have had
  sub-revisions (3.03a, etc.) that aren't reflected in the version string.
- The binary contains 10 Miles object modules totaling ~63 KB (12.4% of code).


## Smacker SDK (RAD Game Tools)

**Confidence: MEDIUM**

| Field | Value | Location |
|-------|-------|----------|
| Library | Smacker (video playback) | function names and strings |
| Version | 2.0x (SDK path: `SMACK\20\`) | debug info paths |
| Build path | `C:\DEVEL\PROJECTS\SMACK\20\` | debug info @ `0x124805` |
| Source files | `sndail.cpp`, `smackinp.cpp`, `sndnull.cpp` | debug info paths |
| ASM source | `unsmack.ASM` | debug info @ `0x12511B` |
| Key functions | `SmackDoFrameToBuffer`, `SmackDoFrameToVESA`, `SmackTimerSetup`, `SmackTimerRead`, `SmackAILDigDriver` | symbol table |

The Smacker SDK was produced by RAD Game Tools (originally Flashpoint
Productions). The `\SMACK\20\` path strongly suggests version 2.0.

**Build path analysis:** `C:\DEVEL\PROJECTS\SMACK\20\` — unlike the Miles
SDK (on a network drive), Smacker was on a local drive, suggesting it was
perhaps a newer or separately obtained SDK. The `.cpp` extensions indicate
the Smacker glue code was C++ (compiled as C by Watcom).

**What to look for:**
- Smacker SDK version 2.0 for DOS (32-bit protected mode / Watcom)
- Produced by RAD Game Tools / Flashpoint Productions
- 1994-era video playback SDK
- Would contain Smacker library (`.lib`) for Watcom C/C++ 32-bit

**Uncertainty:**
- Path `\20\` could mean version 2.0 or just a directory naming convention.
  The version is inferred, not confirmed by a version string.
- Smacker was later bundled with Bink as "RAD Video Tools" — the standalone
  Smacker SDK is harder to find.
- The binary contains 5 Smacker modules totaling ~25 KB (4.9% of code).


## CRT Library Composition

110 CRT modules in the binary, categorized by origin:

| Category | Count | Notes |
|----------|-------|-------|
| C-source (compiler output) | 94 | Functions like `exit`, `printf`, `malloc`, etc. |
| ASM-source (hand-written) | 7 | `cmp386`, `crwd386`, `drive386`, `error386`, `intxa386`, `stk386`, `__stos` |
| Not found in Open Watcom | 9 | `cstrt386_part0/1`, `delay386`, `find386`, `inirt386`, `memalloc`, `_preamble`, `sbrk386`, `set386` |

The "not found" modules are either renamed, platform-specific variants, or
assembled from macro-heavy sources that expanded differently in Watcom 10.0
vs the Open Watcom initial import.

**Comparison with Open Watcom v2 source (initial Sybase import ≈ Watcom 11.0c):**

| ASM Module | Byte comparison | Notes |
|------------|----------------|-------|
| `__stos.asm` | 161 bytes, 2 diffs (1.2%) | Only reg-reg encoding direction |
| `cmp386.asm` | 159 bytes, 29 diffs (18.2%) | Only reg-reg encoding direction (heavy reg-reg code) |
| `intxa386.asm` | 983 bytes, 929 diffs (94.5%) | **Source was substantially rewritten** between v10 and v11 |

The ASM modules that differ only in reg-reg encoding confirm the **source
code is identical** between Watcom 10.0 and the Open Watcom initial import
for most modules. The encoding difference is because the original was
assembled with MASM/TASM (which uses the `r/m, r` opcode form for reg-reg),
while WASM consistently uses the `r, r/m` form.

`intxa386.asm` (the INT dispatcher) was reorganized between versions and
cannot be rebuilt from Open Watcom source.

**C-source modules cannot be rebuilt with Open Watcom v2** — the code
generator produces different output from Watcom 10.0. Example: `__CMain`
in the binary calls `stackavail_` before `alloca`, while the OW 11.0c
source calls `alloca()` directly. The function body structure differs.


## Game Build Environment

**Confidence: HIGH** (paths), **MEDIUM** (build system details)

| Field | Value |
|-------|-------|
| Game source path | `D:\C2\CODE\` |
| Miles SDK path | `R:\NET\LIBS\AIL\DEV3\FLAT\` (network drive) |
| Smacker SDK path | `C:\DEVEL\PROJECTS\SMACK\20\` (local drive) |
| Module name | `c2_x` (from LE resident name table) |
| Target | DOS/4GW Professional, 32-bit flat model |

Source files identified from debug info (in link order):
```
D:\C2\CODE\c2.c          D:\C2\CODE\pcsound.c
D:\C2\CODE\speech.c      D:\C2\CODE\smacker.c
D:\C2\CODE\lib32.c       D:\C2\CODE\hotkeys.c
D:\C2\CODE\refresh.c     D:\C2\CODE\web.c
D:\C2\CODE\common.c      D:\C2\CODE\data.c
D:\C2\CODE\rot_data.c    D:\C2\CODE\c2_vars.c
D:\C2\CODE\controls.c    D:\C2\CODE\contrdat.c
D:\C2\CODE\action.c      D:\C2\CODE\pm_map0.c
D:\C2\CODE\pm_map1.c     D:\C2\CODE\pm_map2.c
D:\C2\CODE\pm_map3.c     D:\C2\CODE\gloops.c
D:\C2\CODE\landfill.c    D:\C2\CODE\evolver.c
D:\C2\CODE\census.c      D:\C2\CODE\int_c2.c
D:\C2\CODE\battle.c      D:\C2\CODE\bbarian.c
D:\C2\CODE\formulae.c    D:\C2\CODE\empire.c
D:\C2\CODE\mmedia.c      D:\C2\CODE\message.c
D:\C2\CODE\titles.c      D:\C2\CODE\display.c
D:\C2\CODE\screens.c     D:\C2\CODE\map.c
D:\C2\CODE\pump.c        D:\C2\CODE\loadsave.c
D:\C2\CODE\debug.c
```

7 additional C2 game modules are hand-written assembly (no source path
in debug info): `library.asm`, `sprites.asm`, `dia_ptrs.asm`,
`dialarga.asm`, `dialargb.asm`, `dia_medi.asm`, `dia_smal.asm`.


## Summary: What You Need

To replace the extracted CRT stubs with buildable source:

| Component | Product | Version | Confidence | Impact |
|-----------|---------|---------|------------|--------|
| **Compiler** | Watcom C/C++ | 10.0 (or 10.0a) | HIGH | Required for C CRT modules (94 files, ~18 KB) |
| **Assembler** | Watcom WASM (from same package) | 10.0 | HIGH | Required for ASM CRT modules (7 files, ~3 KB). May use MASM-compatible encoding. |
| **Miles SDK** | Miles Sound System / AIL/32 | 3.03 | HIGH | 10 modules, ~63 KB. Would need exact SDK to rebuild. |
| **Smacker SDK** | Smacker / RAD Game Tools | 2.0x | MEDIUM | 5 modules, ~25 KB. Would need exact SDK to rebuild. |

The **CRT is the most actionable target** (4.1% of code, 110 modules).
With the original Watcom 10.0 `CLIB3R.LIB`, you could extract each .obj
module and verify byte-for-byte. If matched, the corresponding C/ASM
source from the library could replace our extracted stubs.

Miles and Smacker are less actionable — these are proprietary SDKs that
would be harder to source, and they aren't decompilation targets anyway.
