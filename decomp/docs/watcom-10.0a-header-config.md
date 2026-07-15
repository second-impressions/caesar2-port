# Watcom 10.0a header configuration macros

This note records the compiler switches and predefined macros that affect the
Watcom 10.0a C headers we compile Caesar II with.  It is based on two sources:

* **Runtime headers from the toolchain container**:
  `localhost/watcom-10.0a-dosemu2:/opt/watcom/h`
* **Open Watcom 1.x frontend source**:
  `/tmp/ow1/bld/cc/c/coptions.c`, `/tmp/ow1/bld/cc/c/cmodel.c`,
  `/tmp/ow1/bld/cc/c/watcom.c`

To refresh the header copy used for local greps:

```bash
rm -rf /tmp/watcom10a_h && mkdir -p /tmp/watcom10a_h
podman run --rm --entrypoint /bin/sh \
  -v /tmp/watcom10a_h:/out localhost/watcom-10.0a-dosemu2 \
  -lc 'cp -a /opt/watcom/h /out/h; cp -a /opt/watcom/novh /out/novh'
```

## Big picture

The frontend has three relevant macro paths:

1. **Target / machine predefines** — `SetTargSystem()` in `coptions.c`.
   These are inserted with `PreDefine_Macro(...)` and can be blocked by
   `-u<name>` / undef handling.
2. **Switch macros** — `MacroDefs()` in `coptions.c`.  These are mostly
   `__SW_*` names corresponding to command-line switches (`__SW_OI`,
   `__SW_4`, `__SW_MF`, etc.).
3. **Misc frontend/header controls** — `MiscMacroDefs()` in `cmodel.c`.
   This is where the most header-visible toggles are defined:
   `__INLINE_FUNCTIONS__`, `NO_EXT_KEYS`, `__CHAR_SIGNED__`, `__RENT__`,
   extension keyword aliases, and `__WATCOMC__=<version>`.

For PS.EXE's current verifier flags (`-bt=dos -mf -4r -s`), the important
facts are:

* target is DOS/386 flat model;
* extensions are enabled by default (`NO_EXT_KEYS` is **not** defined);
* global inline intrinsics are disabled (`__INLINE_FUNCTIONS__` is **not**
  defined unless `-oi`/`-ox` is used);
* `char` is unsigned by default (`__CHAR_SIGNED__` is **not** defined unless
  `-j` is used);
* register calling convention is enabled by `-4r`, so `__SW_3R` is defined;
* stack checks are disabled by `-s`, so `__SW_S` is defined.

## Target / machine predefines

Source: `coptions.c:SetTargSystem()`.

For the 386 compiler (`wcc386`):

| Macro | Source condition | Notes |
|---|---|---|
| `M_I386` | `_CPU == 386` | Machine family. |
| `__386__` | `_CPU == 386` | Used heavily by headers (`conio.h`, `i86.h`, `stdio.h`, `string.h`, etc.). |
| `__X86__` | `_CPU == 386` | Generic x86 marker. |
| `_X86_` | `_CPU == 386` | Windows-style x86 marker. |
| `_STDCALL_SUPPORTED` | `_CPU == 386` | Enables stdcall support macros. |
| `__WATCOM_INT64__` | always | Watcom 10 supports 64-bit integer type. |
| `_INTEGRAL_MAX_BITS=64` | always | MS-compatible integral width macro. |
| `__WATCOMC__=<version>` | `cmodel.c:MiscMacroDefs()` via `CompilerID` from `watcom.c` | Version macro. |

Target-system predefines from `-bt=<target>`:

| Target | Macro(s) | Notes |
|---|---|---|
| `-bt=dos` | `MSDOS`, `_DOS`, `__DOS__` | Current PS.EXE target. |
| `-bt=nt` | `_WIN32`, `__NT__` | Not relevant for PS. |
| `-bt=linux` / `qnx` | `__UNIX__`, `__LINUX__` / `__QNX__` | Not relevant for PS. |
| `-bt=windows` on 386 | `__WINDOWS_386__`, `__WINDOWS__` | Also changes default FPU mode and segment assumptions. Not PS. |
| `-bt=netware` | `__NETWARE_386__` (+ `__NETWARE__` for netware5) | Not PS. |

The target name is also emitted generically as `__<TARGET>__`, so DOS gives
`__DOS__`.

## Memory model and CPU/FPU switch macros

Sources: `coptions.c:SetGenSwitches()`, `MacroDefs()`, `Define_Memory_Model()`.

### Memory model

| Switch | Macro(s) | Header/codegen impact |
|---|---|---|
| `-mf` | `__SW_MF`, `__FLAT__` | Current PS.EXE flat 386 model. Also sets flat model internals and cheap pointers. |
| `-ms` | `__SW_MS`, `_M_386SM`; for non-flat small model also `M_I86SM`, `__SMALL__` | 16-bit/small-model header branches. Not PS. |
| `-mm` | `__SW_MM`, `_M_386MM`, `M_I86MM`, `__MEDIUM__` | Not PS. |
| `-mc` | `__SW_MC`, `_M_386CM`, `M_I86CM`, `__COMPACT__` | Not PS. |
| `-ml` | `__SW_ML`, `_M_386LM`, `M_I86LM`, `__LARGE__` | Not PS. |
| `-mh` | `__SW_MH`, `_M_386HM`, `M_I86HM`, `__HUGE__` | Mostly 16-bit huge-model behavior. Not PS. |

Headers use these mainly for pointer size, `NULL`, `__va_list`, and far/near
variants. Under `-mf` + `__386__`, most `NULL` branches resolve to `0`.

### CPU level

| Switch | Macro(s) |
|---|---|
| `-3` / `-3r` / `-3s` | `__SW_3`, `_M_IX86=300` |
| `-4` / `-4r` / `-4s` | `__SW_4`, `_M_IX86=400` |
| `-5` / `-5r` / `-5s` | `__SW_5`, `_M_IX86=500` |
| `-6` / `-6r` / `-6s` | `__SW_6`, `_M_IX86=600` |

For PS.EXE we use `-4r`, so `__SW_4` and `_M_IX86=400` are expected.  The
`r`/`s` suffix also controls calling convention macros below.

### 386 register vs stack calling convention

| Switch | Macro | Notes |
|---|---|---|
| `-3r`, `-4r`, `-5r`, `-6r` | `__SW_3R` | Register calling convention (`__watcall` shape). Current PS setting. |
| `-3s`, `-4s`, `-5s`, `-6s` or no register convention | `__SW_3S` | Stack calling convention. Not PS. |

The macro name is historical: even with `-4r`, the convention macro is
`__SW_3R`; CPU level is separately represented by `__SW_4`.

### FPU mode

| Switch | Macro(s) | Notes |
|---|---|---|
| `-fpi` | `__SW_FPI`, `__FPI__` | Emulated floating point. |
| `-fpi87` | `__SW_FPI87`, `__FPI__` | Inline 80x87. |
| `-fpc` | `__SW_FPC` | Floating calls, disables `__SW_OP`. |
| `-fp2`, `-fp3`, `-fp5`, `-fp6` | `__SW_FP2`, `__SW_FP3`, `__SW_FP5`, `__SW_FP6` | FPU level. Default 386 compiler path chooses 387 level if not overridden. |
| `-op` | `__SW_OP` | Force floats to memory. |

Mostly relevant for float-heavy functions and math headers.

## Header-control switches

These directly explain the configurable macros observed in `/opt/watcom/h`.

| Switch / condition | Macro defined | Source | Header effect |
|---|---|---|---|
| `-oi` | `__INLINE_FUNCTIONS__`, `__SW_OI` | `Set_OI()`, `MiscMacroDefs()`, `MacroDefs()` | Enables header `#pragma intrinsic(...)` blocks. Very codegen-significant. |
| `-ox` | `__INLINE_FUNCTIONS__`, `__SW_OI`, plus optimization bundle | `Set_OX()` | Also sets loop/scheduling/branch opts and math inline. Not PS. |
| `-za` / `-zA` | `NO_EXT_KEYS`; also unique functions | `Set_ZA()`, `SetStrictANSI()`, `MiscMacroDefs()` | Disables Watcom extension declarations/macros. Not PS. |
| default (no `-za`) | extension keyword aliases, no `NO_EXT_KEYS` | `Define_Extensions()` | Defines `near`, `far`, `cdecl`, `_cdecl`, `_interrupt`, `_based`, `_asm`, etc. |
| `-ze` | no macro itself; re-enables extensions | `Set_ZE()` | Opposite of `-za` if both appear. |
| `-j` | `__CHAR_SIGNED__`, `__SW_J` | `SetCharType()`, `MiscMacroDefs()`, `MacroDefs()` | Makes plain `char` signed. PS evidence says **not global**. |
| `-re` | `__RENT__` | `Set_RE()`, `MiscMacroDefs()` | Reentrant code marker. Not current PS. |
| `-ei` | `__SW_EI` | `Set_EI()`, `MacroDefs()` | Force enum size to int. |
| `-em` | no `__SW_EI` | `Set_EM()` | Restore minimal enum sizing. |
| `-ou` | `__SW_OU` | `Set_OU()`, `MacroDefs()` | Unique function addresses. |
| `-en` | `__SW_EN` | `Set_EN()`, `MacroDefs()` | Emit names. |
| `-s` | `__SW_S` | `Set_S()`, `MacroDefs()` | Stack checks disabled. Current verifier setting. |
| `-zu` | `__SW_ZU` | `Set_ZU()`, `MacroDefs()` | Floating stack segment / stack assumptions; headers use in varargs/process paths. |
| `-zc` | `__SW_ZC` | `Set_ZC()`, `MacroDefs()` | Strings in code segment / const-in-code. |
| `-zk0`, `-zk1`, `-zk2`, `-zk3`, `-zkl` | `__SW_ZK` | `Set_ZK*()`, `MacroDefs()` | Non-Unicode / DBCS mode. Default `use_unicode=1`, so `__SW_ZK` absent unless a `-zk*` switch is used. |
| `-bm` | `__SW_BM`, `_MT` | `Set_BM()`, `MacroDefs()` | Multithread lib model; affects `stdio.h` `getc`/`putc` macros. Not PS. |
| `-bd` | `__SW_BD` | `Set_BD()`, `MacroDefs()` | DLL resident code; affects `stdio.h` `getc`/`putc` macros. Not PS. |
| `-br` | `__SW_BR`, `_DLL` | `Set_BR()`, `MacroDefs()` | DLL runtime. Not PS. |
| `-bc`, `-bg`, `-bw` | `__SW_BC`, `__SW_BG`, `__SW_BW` | `MacroDefs()` | Target/application model markers. |
| `-nd=<name>` | `__SW_ND` | `SetDataSegName()`, `MacroDefs()` | Changes `stdio.h` `__iob` near declaration. Not PS. |
| `-zp=<n>` | no `__SW_*` macro | `SetPackAmount()` | Changes default struct packing. Header `#pragma pack(1)` often overrides local structs. |
| `-d+` | no direct header macro | `SetExtendedDefines()` | Allows extended macro definitions on command line. |
| `-dNAME[=VALUE]` | user macro | `DefineMacro()` | User-defined macros. |
| `-uNAME` / `-u` | undefines / suppresses predefined macros | `AddUndefName()`, `PreDefine_Macro()` | Can remove predefines before headers see them. |
| `-fi=<file>` | no macro | `Set_FI()` | Force-includes a header before the source. Could introduce project macros. |

## Optimization switch macros

Source: `coptions.c:Optimization_Options`, `MacroDefs()`.

These mostly tell headers / user code what optimization switches are active;
most do not alter CRT header declarations directly, except `-oi` and `-om`.

| Switch | Macro |
|---|---|
| `-oa` | `__SW_OA` |
| `-oc` | `__SW_OC` |
| `-od` | `__SW_OD` |
| `-of` | `__SW_OF` |
| `-oh` | `__SW_OH` |
| `-oi` | `__SW_OI` and `__INLINE_FUNCTIONS__` |
| `-ok` | `__SW_OK` |
| `-ol` / `-ol+` | `__SW_OL` |
| `-om` | `__SW_OM`; sets math-inline target switch |
| `-on` | `__SW_ON` |
| `-op` | `__SW_OP` |
| `-or` | `__SW_OR` |
| `-ou` | `__SW_OU` |
| `-ox` | `__SW_OI`, `__SW_OL`, `__SW_OR`, plus branch prediction and `-om` bundle |

PS.EXE evidence so far: global `-oi`, `-or`, `-oa`, `-os`, `-ot`, and `-d2`
are not part of the build.  `-ol` remains a possible per-file or global open
question, but it is not header-driven except for the `__SW_OL` marker.

## What the container headers actually do with these macros

The most important header observations from `/opt/watcom/h`:

### `__INLINE_FUNCTIONS__`

Gates `#pragma intrinsic(...)` blocks.

| Header | Intrinsics enabled |
|---|---|
| `conio.h` | `inp`, `inpw`, `outp`, `outpw`, and on 386 also `inpd`, `outpd` |
| `string.h` | `memchr`, `memcmp`, `memcpy`, `strcat`, `strcpy`, `strlen`, `strchr`; extensions such as `_fmemcpy`, `_fstrcmp`, etc. when `NO_EXT_KEYS` is absent. On `__386__`, `memset` and `strcmp` are **not** in this block. |
| `stdlib.h` | `abs`, `div`, `labs`, and on 386 `ldiv`; also rotations `_rotl`, `_rotr`, `_lrotl`, `_lrotr` |
| `i86.h` | `_disable`, `_enable` |
| `bios.h` / `bios98.h` | BIOS helper intrinsics / pragmas |

Important Caesar II check: compiling `check_for_Trident` with
`-d__INLINE_FUNCTIONS__` changed the function from a 2-byte residue to a
128-byte residue because `inp/outp` inlined.  Therefore PS.EXE did **not** use
`__INLINE_FUNCTIONS__` globally, even though local `#pragma intrinsic(...)`
may still appear in original source around specific routines.

### `NO_EXT_KEYS`

Disables Watcom extension declarations and macros in many ANSI-ish headers:
`assert.h`, `bios.h`, `ctype.h`, `float.h`, `io.h`, `math.h`, `stddef.h`,
`stdio.h`, `stdlib.h`, `string.h`, `time.h`.

Because extensions are enabled by default in the frontend, PS-style builds
should normally have these declarations visible unless the original build used
`-za` / strict ANSI for a file.  Current evidence says not global.

### `__SW_BD` / `__SW_BM`

`stdio.h` uses these to force:

```c
#define getc(fp)    fgetc(fp)
#define putc(c,fp)  fputc(c,fp)
```

Without them, `getc` / `putc` are inline buffer macros.  This matters for any
stdio-heavy function.  Caesar II game code mostly uses DOS `open/read/write`,
so this is probably low priority.

### `__SW_ND`

`stdio.h` declares `__iob` differently:

```c
#ifdef __SW_ND
extern FILE __iob[];
#else
extern FILE __near __iob[];
#endif
```

Only relevant if using `stdin` / `stdout` / `stderr` macros or `FILE *` CRT I/O.

### `__NO_MATH_OPS`

This one is unusual: it is **not** defined by a normal compiler switch in the
frontend sweep.  `math.h` says defining it stops the compiler from recognizing
math functions as intrinsic operators and otherwise emits:

```c
#pragma intrinsic(log,cos,sin,tan,sqrt,fabs,pow,atan2,fmod)
#pragma intrinsic(acos,asin,atan,cosh,exp,log10,sinh,tanh)
```

So math functions can become intrinsic from simply including `math.h`, unless
`__NO_MATH_OPS` is supplied manually.  This is separate from `-oi`.

### `__CHAR_SIGNED__`

Used by `limits.h` to choose `CHAR_MIN` / `CHAR_MAX`.  The compiler's plain
`char` signedness is controlled by `-j`; the macro is just the header-visible
reflection of that choice.

## Current expected macro set for verifier flags

For `-bt=dos -mf -4r -s`, expect at least:

```c
#define M_I386
#define __386__
#define __X86__
#define _X86_
#define _STDCALL_SUPPORTED
#define __WATCOM_INT64__
#define _INTEGRAL_MAX_BITS 64
#define __WATCOMC__ <10.0a version value>
#define MSDOS
#define _DOS
#define __DOS__
#define __SW_MF
#define __FLAT__
#define __SW_4
#define _M_IX86 400
#define __SW_3R
#define __SW_S
#define __SW_FP3        /* default 387 level unless overridden */
```

Also expect segment/default macros such as `__SW_ZFP` / `__SW_ZGF` /
`__SW_ZDP` depending on the frontend's peg-segment defaults after `-mf`.
These are mostly diagnostic for headers; they have not yet explained Caesar II
byte residues.

Do **not** expect globally:

```c
#define __INLINE_FUNCTIONS__
#define __SW_OI
#define NO_EXT_KEYS
#define __CHAR_SIGNED__
#define __SW_J
#define __SW_BM
#define __SW_BD
#define _MT
#define _DLL
```

## Reverse-engineering implications

* Do not add global `-oi` or `-d__INLINE_FUNCTIONS__`: container headers prove
  it changes `conio.h`/`string.h` intrinsic behavior, and direct verification
  regresses known PS-matching code.
* If a function uses `inp/outp` and PS shows helper calls, `__INLINE_FUNCTIONS__`
  was not visible there.
* If a function uses `strcpy`/`strlen`/`memcpy` and PS shows inline-ish code,
  investigate a **local** `#pragma intrinsic(...)` before changing global flags.
* If stdio `getc`/`putc` appears, check whether the PS shape is the macro body
  or the `fgetc`/`fputc` call path (`__SW_BD`/`__SW_BM`).
* Plain `char` remains unsigned unless the source explicitly says `signed char`
  or a per-file build used `-j` (unlikely globally; many PS patterns rely on
  unsigned default char).
* Original project headers may still be the larger missing macro source.  CRT
  header config explains intrinsics/prototypes, but not game-specific idioms
  such as map/cell indexing macros.
