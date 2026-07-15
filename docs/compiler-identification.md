# Caesar II — Compiler & Flags Identification

Detailed forensic analysis to pin down the exact Watcom compiler version,
CPU target, and flag set used to compile the game code in `PS.EXE`.

This complements the high-level build environment notes in
`build-environment.md` with evidence from binary analysis and
byte-level compilation experiments.

---

## TL;DR

| Property | Value | Confidence |
|---|---|---|
| Compiler | Watcom C 10.0a | HIGH |
| Compiler binary | `wcc386.exe` (Win32 NT or DOS LX, same backend) | HIGH |
| CPU target | `-4r` (486, register calling convention) | **HIGH** |
| Memory model | `-mf` (flat) | HIGH |
| Debug info | `-d1` (line numbers only) | HIGH |
| Stack checking | `-s` (disabled) | HIGH |
| C standard | C89 (default, no `-za`/`-ze` impact) | HIGH |
| Optimisation | No sub-flags beyond default | MEDIUM |

Confirmed command line (per TU):
```
wcc386 -bt=dos4g -4r -mf -d1 -s <source.c>
```

**Update (2026-04-19):** `-4r` confidence upgraded from MEDIUM to HIGH after
finding a second independent code-gen discriminator: PS.EXE uses
`xor ah,ah; mov [byte_global], ah` (8 bytes) to store literal 0 into a
`char` global, while every Watcom version emits the shorter direct form
`mov byte ptr [m32], 0` (7 bytes) when compiled with `-3r`/`-3s`/`-3`.
The xor-AH-via-register form only appears with CPU target `-4`/`-5`/`-6`
(any of `r`/`s`/none). This pattern occurs throughout PS.EXE and is
impossible to trigger with `-3r`. See §12 below.

---

## 1. LE Header — No WLINK Version Stamp

The binary uses the layered format:
```
MZ stub  →  BW[0] (VMM.EXP)  →  BW[1] (4GWPRO.EXP)  →  MZ stub  →  LE (game)
```

The LE header at file offset `0x37D4C` was parsed against the Open
Watcom source (`bld/wl/c/loadflat.c`, `bld/watcom/h/exeflat.h`).

Key fields:

| Field | Value | Meaning |
|---|---|---|
| `signature` | `0x454C` (`LE`) | Linear Executable |
| `cpu_type` | `0x0002` | 80386 |
| `os_type` | `0x0001` | OS/2 / DOS4GW |
| `version` | `0x00000000` | No `VERSION` directive used in linker script |
| `flags` | `0x00000200` | `OSF_PM_COMPATIBLE` |
| `num_pages` | 138 | |
| `page_size` | 4096 | |
| `eip_object` | 1, offset `0x62D14` | Entry point |
| `esp_object` | 2, offset `0x89420` | Stack |

**Critical finding:** WLINK does **not** embed a version stamp in the LE
header. The guide's claim that `+0x10`/`+0x11` hold "linker major/minor
version" is wrong — those bytes are the low bytes of the `flags` field
(`0x0200`). There is no linker version in the LE format at all; the banner
is only printed to stdout at runtime.

---

## 2. DOS/4GW Professional Version

BW chain at file offsets `0xF474` (VMM.EXP) and `0x1E0C4` (4GWPRO.EXP),
both with GLU/makepm version 10.72.

From the 4GWPRO.EXP segment:
```
DOS/4GW Professional Protected Mode Run-time
Copyright (c) Rational Systems, Inc. 1990-1994
May 19 1994 14:44:26        ← hard lower bound on build date
```

This is DOS/4GW Professional 1.97, bundled with Watcom 10.0.

---

## 3. Embedded CRT Copyright Strings

Two distinct Watcom CRT copyright strings are present in the LE code
section:

| Offset (from LE MZ stub) | String |
|---|---|
| `+0x041D` (inside LE MZ stub itself) | `WATCOM C Run-Time system code is provided on an "as is" basis ... 1988-1993.` |
| `+0xA2F15` (game code, entry point) | `WATCOM C/C++32 Run-Time system. (c) Copyright by WATCOM International Corp. 1988-1994.` |

The **1988-1993** string comes from the WLINK-generated 16-bit MZ stub
wrapper (linker-generated, not game code). The **1988-1994** string is
the 32-bit CRT startup (`_cstart_`) linked into the game binary itself.

`1988-1994` copyright pins the CRT to **Watcom 10.0** (released 1994).
Watcom 9.x shipped `1988-1993`; Watcom 10.5+ shipped `1988-1995`.

The entry point structure matches `cstrt386.asm` from the Watcom CRT:
```
0x72D14:  eb 76   jmp short around    ; skip 0x76 bytes of embedded data
0x72D16:  "WATCOM C/C++32 Run-Time system ... 1988-1994 ..."
0x72D8C:  fb      sti                 ; 'around:' — actual startup code
```

---

## 4. Debug Info Version

Parsed via `c2/parsers/debug.py`:

| Field | Value |
|---|---|
| `exe_major_ver` | 3 |
| `exe_minor_ver` | 0 |
| `obj_major_ver` | 1 |
| `obj_minor_ver` | 0 |
| Languages | `['C']` |
| Symbol count | 3857 |
| Module count | 178 |

All 3857 game code symbols show calling convention `__watcall` (Watcom
register calling convention), confirming `-3r` or `-4r` throughout.

---

## 5. Stack Checking

`__STK` is present at virtual address `0x0007B53F`. This is the Watcom
stack overflow checker.

However, inspecting game TUs individually: the simple leaf functions in
`formulae.c` produce no `call __STK` even with stack checking enabled —
they're too small. The presence of `__STK` in the binary comes from
larger functions in `lib32.c` (module 13), which has 107 `__CHK` calls.

Byte-matching experiments (see §7) confirmed that game code was compiled
with **`-s`** (stack checking disabled). Without `-s`, the compiler
inserts a 10-byte `__STK` call prolog even in small functions, which
does not appear in any of the tested game functions.

---

## 6. Compiler Version Verification

The ISO `CDs/WATCOM_C10A.zip` → `WATCOM_C10A.ISO` (dated 1994-09-01)
was extracted. It contains **Watcom C/C++ 10.0a**:

```
WATCOM C32 Optimizing Compiler  Version 10.0a
Copyright by WATCOM International Corp. 1984, 1994. All rights reserved.
```

The BINNT (Win32) `wcc386.exe` (7704 bytes) is a stub that loads the
actual compiler from `BINB/WCC386.EXE` (541 KB, DOS LX format). Both
produce identical code — same backend.

Additional versions tested (from <https://github.com/decompme/compilers>):

| Version | Source |
|---|---|
| wcc10.5, wcc10.5a | decompme tarball |
| wcc10.6 | decompme tarball |
| wcc11.0 | decompme tarball |

**Update (2026-04-19):** A complete archive of containerised Watcom
distributions is now available at
the companion `watcom-compilers` project, covering 9.01d, 9.01e, 9.5
GA, 9.5a, 9.5b, 9.5c, 10.0 LA (1994-03-16, pre-GA), 10.0 GA (1994-05-31,
pre-patch), 10.0a, 10.0b, 10.5, 10.6a, 11.0, 11.0b, and 11.0c. For 9.5
and 11.x the same compiler is also available as a Win32-native binary
(`binnt/wcc386.exe`) executed under wine, plus 9.5 under HX DOS
Extender. **All host variants of the same compiler version (DOS-extender,
NT-native, HX) produce byte-identical .obj output**, confirming the
host-binary taxonomy claim that they share the same backend.

---

## 7. Function Byte Matching — `city_pop_limit_10_to_1`

Methodology: compile candidate C source with `wine wcc386.exe`, extract
function bytes from OMF `.obj` using FIXUPP records to mask relocations,
compare against PS.EXE.

### Target bytes (67 bytes, 1 relocation)

```
53 51 56                   ; push EBX, ECX, ESI
89 c6                      ; mov ESI, EAX         (value → ESI)
89 d1                      ; mov ECX, EDX         (factor → ECX)
85 c0                      ; test EAX, EAX
7d 02                      ; jge +2
31 c6                      ; xor ESI, EAX         (value = 0)
83 fe 64                   ; cmp ESI, 100
7e 05                      ; jle +5
be 64 00 00 00             ; mov ESI, 100
31 d2                      ; xor EDX, EDX         (i = 0)
8b 1d [reloc×4]            ; mov EBX, [population]
89 d0                      ; mov EAX, EDX         (eax = i)
c1 e0 02                   ; shl EAX, 2           (eax = i*4)
01 d0                      ; add EAX, EDX         (eax = i*5)
01 c0                      ; add EAX, EAX         (eax = i*10)
0f af c1                   ; imul EAX, ECX        (eax = i*10*factor)
39 d8                      ; cmp EAX, EBX
7c 08                      ; jl +8
39 d6                      ; cmp ESI, EDX
7e 0a                      ; jle +10
89 d6                      ; mov ESI, EDX         (value = i)
eb 06                      ; jmp +6
42                         ; inc EDX
83 fa 64                   ; cmp EDX, 100
7c e2                      ; jl -30
89 f0                      ; mov EAX, ESI
5e 59 5b                   ; pop ESI, ECX, EBX
c3                         ; ret
```

### Key observations

1. **Shift-add for ×10** (`shl eax,2` / `add eax,edx` / `add eax,eax`
   instead of `imul eax,edx,10`) — this is the critical discriminator.
   With `-3r`, all tested versions emit `imul imm8`; with the default
   CPU target or `-4r`/`-5r`, the 10.0a compiler uses shift-add.

2. **Register allocation**: EBX/ECX/ESI saved; value→ESI, factor→ECX,
   population→EBX, loop counter→EDX. This specific allocation is
   produced only when the source contains a local copy of `factor`
   (a `dummy = factor` assignment), which forces ECX for factor and
   leaves EBX for population.

3. **`xor ESI, EAX`** zero trick — compiler uses XOR because ESI and EAX
   held the same value at that point, producing `xor esi, eax` instead
   of `xor esi, esi`.

### Best source match found

```c
int city_pop_limit_10_to_1(int value, int factor) {
    int i, pop, x, dummy;
    dummy = factor;              /* local copy → forces ECX for factor */
    if (value < 0) value = 0;
    if (value > 100) value = 100;
    pop = population;
    for (i = 0; i < 100; i++) {
        x = i; x <<= 2; x += i; x <<= 1;   /* i * 10 via shifts */
        if (x * dummy >= pop) { if (value > i) value = i; break; }
    }
    return value;
}
```

Compiled with: `wcc386 -bt=dos4g -mf -d1 -s`

### Match results

| Compiler | Flags | Diffs | Notes |
|---|---|---|---|
| wcc10.0a | `-bt=dos4g -mf -d1 -s` | **4** | Only instruction ordering |
| wcc10.0a | `-bt=dos4g -4r -mf -d1 -s` | **4** | Same |
| wcc10.5 | `-bt=dos4g -mf -d1 -s` | **4** | Same |
| wcc10.6 | `-bt=dos4g -mf -d1 -s` | **4** | Same |
| wcc11.0 | `-bt=dos4g -mf -d1 -s` | **49** | Completely different codegen |

The 4 remaining diffs are **instruction order only** — `xor EDX,EDX` and
`mov EBX,[population]` are emitted in opposite order:

```
; Target:                     ; Generated (10.0a):
xor  edx, edx                 mov  ebx, [population]
mov  ebx, [population]        xor  edx, edx
```

Both orderings are semantically identical (instructions are independent).
This is a deterministic scheduler choice baked into the 10.0a code
generator that we could not override through any C source variation,
flag combination, or language standard (C89, C with extensions,
C++ via `wpp386`). It is likely resolved by the **base Watcom 10.0**
binary (pre-patch), which we do not have.

For practical purposes, **63/67 bytes match exactly** after relocation
masking; the remaining 4 bytes are a pure scheduling artefact with no
semantic difference.

---

## 8. CPU Target Flag

The `-3r` flag (386 instruction timings) causes the compiler to emit
`imul eax, edx, 10` for `i * 10`, because on the 386 the `IMUL` with
small immediate is considered cheap (early-out multiplier).

The default CPU target (and `-4r`/`-5r`) causes the compiler to emit
the shift-add sequence (`shl/add/add`) for `i * 10`. On 486/Pentium,
`IMUL` is fast and strength reduction to shifts is not preferred, but the
10.0a code generator happens to produce shifts as the default for this
exact expression shape.

The Caesar II minimum system requirement (DOS version) is
**Intel 486SX 25 MHz**, consistent with `-4r`. The Windows version
requires 486DX2 66 MHz.

**Conclusion:** `-4r` is the most likely CPU target flag, but `-mf -d1 -s`
without any CPU flag also produces identical results for every tested
function. The ambiguity cannot be resolved from the game code alone.

---

## 9. Optimisation Flags

No individual optimisation sub-flags (`-ot`, `-oi`, `-ob`, `-ok`, etc.)
were needed to match `city_pop_limit_10_to_1`. Adding `-ot` in particular
**breaks** the match (produces 69-byte code with a different loop
structure).

The matched functions from `formulae.c` (trivial leaf functions) are not
strong discriminators for optimisation flags. Larger functions with loops,
FP, and complex control flow (e.g. `adjust_culture_criteria_`,
`get_morale_and_readiness_`) should be used for further flag refinement.

Optimisation flags tested and ruled out for `city_pop_limit_10_to_1`:
`-ot`, `-oi`, `-ob`, `-ok`, `-ol`, `-or`, `-oa`, `-ox`, `-os`.

---

## 10. Rejected Hypotheses

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Compiled with `-3r` (386 target) | **Rejected** for game code | Produces `imul imm8` instead of shift-add for `×10` |
| Compiled with Watcom 10.5+ | **Rejected** as primary | 11.0 gives d=49; 10.5/10.6 give same d=4 as 10.0a but 10.0a matches the CRT copyright |
| Compiled with C++ (`wpp386`) | **Rejected** | C++ codegen gives d=35+ |
| Stack checking enabled (default) | **Rejected** for game TUs | Would add 10-byte `__STK` call prolog; absent in game functions |
| WLINK version in LE header bytes `+0x10`/`+0x11` | **Rejected** | Those bytes are `flags` field (`0x0200` = `OSF_PM_COMPATIBLE`) |

---

## 12. Code-Gen Discriminator: `-3r` vs `-4r`/`-5r`/`-6`

Isolated test:
```c
char decision;
void f(void) { decision = 0; }
```

| Flag         | Bytes for `decision = 0` | Form |
|--------------|--------------------------|------|
| `-3r`/`-3s`/`-3` | `c6 05 [m32] 00`     (7 b) | `mov byte ptr [m32], 0` |
| `-4r`/`-4s`/`-4` | `30 e4 88 25 [m32]`  (8 b) | `xor ah,ah; mov [m32], ah` |
| `-5r`/`-5s`/`-5` | `30 e4 88 25 [m32]`  (8 b) | same |
| `-6` (11.x only) | `30 e4 88 25 [m32]`  (8 b) | same |

The form is invariant across every Watcom version 9.5 through 11.0c.
It is not affected by `-os`/`-ot`/`-oi`/`-ol`/`-oa`/`-ob`/`-ok`/`-or`/`-ox`/`-d?`,
nor by C standard, structure-pack, or runtime-library flags.

PS.EXE consistently emits the 8-byte `xor ah,ah` form, e.g. at
`act_review_in_10` (0x55AD9) and `act_review_in_25` (0x55AF6).
The sibling function `act_take_promotion` (0x55AC7) stores `1` (not `0`)
to the same byte global and uses the direct 7-byte form, ruling out
any hypothesis that the function context (e.g. fall-through, prior AH
load) is responsible — the trigger is the literal `0` operand only.

Switching the verifier from `-3r` to `-4r` reduces the aggregate diff
byte count on `formulae.c` (17 functions) from 829 to 720 and adds
two more byte-identical functions. `-4r` beats `-5r` by a further 14
bytes — consistent with Caesar II's box requirement of "486SX 25 MHz".

## 13. Cross-Version Code-Gen Sweep with `-4r`

Total byte-diff against PS.EXE on the 17 currently-decompiled
`formulae.c` functions, after fixup masking, by compiler version:

| Version group | Total diff bytes |
|---|---|
| 9.5 GA (1993-05) / 9.5 NT-native / 9.5 HX | 886 |
| **9.5a / 9.5b / 9.5c / 10.0 LA**   | **831** (joint lowest)  |
| 10.0 GA / 10.0a / 10.0b / 10.5 / 10.6a | 841 |
| 11.0 GA | 906 |
| 11.0b / 11.0c | 902 |

Observations:
- 9.5a, 9.5b, 9.5c are byte-identical on every function tested — the
  three patch revisions did not touch the code generator.
- 10.0 LA is byte-identical to 9.5a/b/c on this sample but its CRT
  library differs structurally on `malloc` (see
  `compiler-version-confirmation.md`), ruling it out as the build
  compiler.
**Update (2026-04-20):** full-file sweep across all 109 decompiled
functions in `formulae.c` / `common.c` / `message.c` / `debug.c` now
shows:

| Compiler | Exact | Total diff bytes |
|----------|------:|-----------------:|
| 10.0 LA  | 36    | 16 168 |
| 10.0 GA  | 37    | 15 836 |
| **10.0a**  | **50**    | **14 005** |
| **10.0b**  | **50**    | **14 005** |
| 10.5     | 37    | 15 885 |
| 11.0     | 14    | 17 005 |

10.0a and 10.0b score **byte-identical** across every function tested.
This is consistent with the documented release-note difference
(10.0b = 10.0a + Pentium FDIV floating-point workaround only, per the
companion `watcom-compilers` project's `docs/RESEARCH.md`): no
change to the integer back-end.

**Decision (2026-04-20):** PS.EXE contains **no floating-point code**.
A linear sweep of the 0x7D000-byte code section with capstone found
only three putative FPU instructions out of 149 699 disassembled
opcodes, all of which are obvious linear-sweep false positives (bogus
displacements into unmapped addresses, bytes mid-jump-table):

```
@ 0x03a611: fbld tbyte ptr [esi - 0x590efffd]   ; garbage disp
@ 0x041a5b: fistp word ptr [edx]                ; df 1a = data byte + next insn
@ 0x06f5a8: fdivr st(5), st(0)                  ; dc f5 = data mid-table
```

Since the only documented 10.0a → 10.0b code-gen difference is the
Pentium FDIV workaround, and Caesar II emits no FPU instructions at
all, **the two versions are provably indistinguishable for this
binary**. We canonicalise on 10.0a; 10.0b is an accepted equivalent.
No further work is needed to disambiguate them.

### Release-date sanity check

| Release | Date | Plausible for C2 (shipped 1995-09-29)? |
|---------|------|----------------------------------------|
| 10.0 GA | 1994-05-31 | yes (but ruled out: 37 exact vs 50) |
| 10.0a   | 1994-09-01 | **yes** — best fit |
| 10.0b   | 1995-01-11 | **yes** — equally good (integer-identical to 10.0a) |
| 10.5    | 1995-07-11 | yes (but ruled out: 37 exact) |
| 10.6    | 1996       | post-dates C2 |

Additional circumstantial evidence: the embedded CRT banner in
PS.EXE reads **"WATCOM International Corp. 1988-1994"**, which
matches both 10.0a's and 10.0b's `clib3r.lib` exactly. (10.5 bumped
this to 1988-1995, so 10.5 is independently ruled out here too.)
Dates from the companion `watcom-compilers` project's
`docs/RESEARCH.md`.

- 10.0 GA, 10.0a, 10.0b, 10.5, and 10.6a all produce byte-identical
  code on the entire 17-function sample. The code generator was
  effectively frozen across this 18-month window. Distinguishing
  between them requires CRT-library evidence, where 10.0 GA / 10.0a /
  10.0b are also indistinguishable; only the math libraries (FDIV
  patch, see §9 of `compiler-version-confirmation.md`) rule out 10.0b.
- The remaining 9.5a/10.0LA-vs-10.0a 10-byte gap is concentrated in a
  single function (`adjust_peace_criteria`); the CRT evidence for 10.0a
  is much stronger and overrides this signal.
- 11.x is clearly worse, eliminating it as a candidate.

## 14. Status: flag space settled

The flag and per-TU questions this document originally raised are now
closed by the exhaustive flag survey
(`docs/flag-survey-2026-06-15.md`, 52,899 isolated wcc386 10.0a compiles):

1. **Optimisation flags** — the baseline `-bt=dos -mf -4r -s -d1`
   (unsigned `char`, OptSize=50) is the *unique global maximum* across
   the full codegen-flag space; no flag or combination beats it.

2. **Per-TU flag variation** — none. Every TU (including `lib32.c`) is
   built with the same baseline; the decomp build uses a single
   `PS_CFLAGS`. The remaining byte residue is irreducibly source-shape,
   not a flag or version gap.

3. **Base Watcom 10.0 vs 10.0a** — both 10.0 LA and 10.0 GA were tested;
   the CRT byte-comparison pins the build to 10.0a (see
   `compiler-version-confirmation.md`). The `city_pop_limit_10_to_1`
   instruction-ordering case that once looked like an irreducible 2-byte
   scheduler quirk is **now byte-exact** — it was a source-shape lever,
   not a compiler quirk.

---

## Appendix: Tools Used

- `c2/parsers/exe.py` — parses the layered BW/LE format of PS.EXE
- `c2/parsers/debug.py` — parses Watcom debug info (symbols, modules)
- `wine` (11.0) — runs the Win32 stub `wcc386.exe` on Linux
- `wcc386.exe` (10.0a) — from `CDs/WATCOM_C10A.zip` → `WATCOM_C10A.ISO`
- `wcc386.exe` (10.5/10.5a/10.6/11.0) — from <https://github.com/decompme/compilers>
- Python OMF parser (ad-hoc) — extracts function bytes + FIXUPP reloc masks

## Appendix: Reproducing the Compiler Setup

```bash
# Extract 10.0a compiler from the ISO
7z x CDs/WATCOM_C10A.zip  # extracts WATCOM_C10A.ISO
7z x WATCOM_C10A.ISO WATCOM/BINNT/WCC386.EXE WATCOM/BINB/WCC386.EXE \
                     WATCOM/BINNT/WPP386.EXE WATCOM/BINB/WPP386.EXE \
                     WATCOM/H/               \
     -o/tmp/watcom/wcc10.0a

# Run compiler via wine
export WINEDEBUG=-all
SRC_WIN=$(winepath -w source.c)
OBJ_WIN=$(winepath -w source.obj)
wine /tmp/watcom/wcc10.0a/WATCOM/BINNT/WCC386.EXE \
     $SRC_WIN -bt=dos4g -4r -mf -d1 -s -fo=$OBJ_WIN

# Alternative: download decompme containers
wget https://github.com/OmniBlade/decomp.me/releases/download/wcc10.5/wcc10.5.tar.gz
tar xzf wcc10.5.tar.gz
wine wcc10.5/binnt/wcc386.exe $SRC_WIN -bt=dos4g -4r -mf -d1 -s -fo=$OBJ_WIN
```
