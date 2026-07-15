# Reference headers

These are the canonical API surfaces for AIL 3.03 and Smacker 2.x as
they shipped to Watcom-DOS licensees. The files themselves are not kept
in this repo (re-acquire them from the per-file provenance below); this
doc records their content purely as
**compile-time references** for any future decomp pass that needs to:

- Look up the exact prototype of an AIL or Smacker function
- Resolve calling-convention questions (`AILCALL`, `__SW_3R`, `RADEXPLINK`, etc.)
- Identify struct layouts (`Smack`, `MSS_TIMER`, etc.)
- Cross-check that a hand-rolled prototype in `decomp/include/{ail,smacker}.h` is correct

They are **not** included in the build. The decomp build links against
the byte-blob `.asm` files in `decomp/lib/{miles,smacker}/` and uses the
hand-rolled, narrowed prototypes in `decomp/include/{ail,smacker}.h`.

## Files

### `ail/mss-v1.01.h` — primary AIL 3.03 reference (4805 lines)

The Miles SDK header as it stood at the V3.03 release. Banner:

```
//##  MSS.H: Miles Sound System main header file
//##  Version 1.00 of 15-Feb-95: Initial, derived from AIL.H V3.02
//##          1.01 of 19-Jun-95: Added various functions for V3.03 release
```

Use this as the authoritative source for any `AIL_*` prototype the
PS.EXE decomp code calls. Key sections:

- `~line 213-330` — `AILCALL` / `AILCALLBACK` macro definitions (per platform)
- `~line 2898-2995` — the `__SW_3R` register/stack-call dispatch (only `AIL_startup` varies; all other entry points are cdecl/AILCALL)
- Function declarations are grouped by subsystem: `Sample`, `Sequence`, `Timer`, `MSSDS` (DirectSound), `MSSWS` (WaveOut), `MSSDOS` (DOS-only block).

For PS.EXE we want the `IS_DOS` block specifically. Watcom auto-defines
`__DOS__` which sets `IS_DOS` per the `#ifdef __DOS__` guard near the
top of the file.

### `ail/mssw-win32.h` — Win32 cross-reference

From the MiG Alley source release. Useful only for cross-checking that
a function signature didn't change between DOS and Win32 builds (it
almost always didn't — the DOS-vs-Win32 differences are isolated
under `#ifdef IS_DOS` blocks in the canonical `mss-v1.01.h`).

### `ail/ail32-v1.05.h` — public-domain ancestor (1993)

The original AIL/32 v1.05 header from John Miles' May-2000 PD release.
Useful for understanding what survived from v1.05 → v3.03. The struct
shapes and most function names are recognisable.

License is in `AIL32-v1.05-LICENSE.txt` (the original `READ.ME` file
from the public-domain release).

### `smacker/smack-v3.2f.h` — Smacker 2.x-superset reference (~530 lines)

Header from Jagged Alliance 2's leaked source tree. MD5-identical to
the same file in MiG Alley's source release, so it's not a one-off
hand-edit. Banner reads `#define SMACKVERSION "3.2f"` — chronologically
later than the 2.0 build linked into PS.EXE, but RAD documented
preserving the v2 ABI through the entire 2.x → 3.x line, so this
header is a strict superset of what we need. All v2 entry points are
present; v3-only additions are easy to spot from the changelog at
`radgametools.com/smkhist.htm`.

Key types: struct `Smack` (member layout matches what PS.EXE expects),
`SMACKTRACKS`/`SMACKNEEDPAN`/`SMACKAUTOEXTRA` flag constants, function
signatures for `SmackOpen` / `SmackToBuffer` / `SmackDoFrame` /
`SmackNextFrame` / `SmackWait` / `SmackSoundUseMSS` /
`SmackSoundUseDirectSound`.

## How to use these from a decomp session

1. When you encounter an `AIL_*` or `Smack*` call site in PS.EXE that
   isn't already in `decomp/include/ail.h` or `decomp/include/smacker.h`,
   look up its prototype here.
2. Watch for the `AILCALL` / `RADEXPLINK` macro on each declaration —
   that determines the calling convention. For DOS-Watcom register
   targets: `AILCALL` expands to `cdecl`, and `__SW_3R`-gated
   `_reg`/`_stack` aliases pick between Watcom register call and stack
   call (only `AIL_startup` actually has both; everything else is plain
   cdecl).
3. Add the narrowed prototype to `decomp/include/{ail,smacker}.h` with
   the appropriate `#pragma aux NAME "*" parm caller [] modify [...]`
   so Watcom emits the right symbol name and stack-cleanup behaviour.
4. Do **not** `#include` these reference headers from `decomp/src/*.c`
   directly. They drag in too much (~5000 lines of Win32/DirectSound
   declarations we don't want). Always go through the narrowed
   `decomp/include/` shim.
