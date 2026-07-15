# CRT Library Analysis

## Summary

Investigation into using `clib3r.lib` (Watcom C runtime library) for linking
the decompiled binary. **Conclusion: not viable for byte-identical linking.**
The CRT code is instead kept as `.asm` files with original bytes from PS.EXE.

## Available Watcom ISOs

| ISO | Date | clib3r.lib size | clib3r.lib MD5 | Modules |
|-----|------|-----------------|----------------|---------|
| `WATCOM_C10A.zip` (10.0a) | Sep 1994 | 187,392 | `69c391d...` | 394 |
| `Watcom_C++_10.0.iso` (10.0) | Sep 1994 | 187,392 | `69c391d...` | 394 |
| `watcom10la.iso` (prerelease) | Mar 1994 | 185,344 | `9af7090...` | 391 |

**Key finding:** 10.0 and 10.0a have byte-identical `clib3r.lib` (and identical
`watcom/` directories). The 10la prerelease differs: 329 modules identical,
62 modules different, 3 modules missing (`inpd`, `outpd`, `p5prof`).

For the full cross-version comparison (9.5 through 11.0c, both `clib3r` and
`clib3s`) that definitively confirms 10.0a, see
[`docs/compiler-version-confirmation.md`](compiler-version-confirmation.md).

## clib3r.lib Module Code Verification

CRT module code in `clib3r.lib` is **byte-identical** to the original PS.EXE
binary. Verified by comparing extracted module code against corresponding
offsets in `le_code.bin` (e.g., `outpw_`: 11 bytes, perfect match).

## Symbol Resolution Issues

### LPUBDEF (Local Public) Symbols

Two symbols needed by the data segment are defined as **LPUBDEF** (local
public, OMF record type 0xB6/0xB7) in their respective library modules:

| Symbol | Module | Record Type | Description |
|--------|--------|-------------|-------------|
| `__null_FPE_rtn` | crwd386 | LPUBDEF (0xB6) | 1-byte function: just `ret` |
| `_no_support_loaded_` | noefgfmt | LPUBDEF32 (0xB7) | 18 bytes of code |

LPUBDEF symbols are **not visible** for cross-module resolution. This affects
both OW v2 wlink and the original Watcom 10.0 wlink identically.

**Patching attempt:** Changing LPUBDEF→PUBDEF in clib3r.lib (at file offsets
0x012B8E and 0x010641) successfully resolved `__null_FPE_rtn`. However,
`_no_support_loaded_` remained unresolved because its module (`noefgfmt`)
was never pulled in (see below).

### Modules Not Pulled In

11 CRT modules have their **only library exports** satisfied by `data.asm`
(which defines all data segment symbols as PUBLIC). Since the exports are
already provided, the linker never pulls these modules from clib3r.lib:

| Module | Exports (all in data.asm) | Has Code? |
|--------|--------------------------|-----------|
| noefgfmt | `___EFG_printf`, `___EFG_scanf` | Yes (18 bytes) |
| iob | `___ClosedStreams`, `___iob`, `___tmpfnext`, `__fmode` | No |
| istable | `__IsTable` | No |
| environ | `___env_mask`, `_environ` | No |
| stinit | `___OpenStreams` | No |
| argcv386 | `__argc`, `__argv` | No |
| ___argc | `____Argc`, `____Argv` | No |
| amblksiz | `__amblksiz` | No |
| heapmod | `___fheap_clean`, `___nheap_clean` | No |
| minreal | `___minreal` | No |
| umaskval | `___umaskval` | No |

Only `noefgfmt` has code that would be missing from the binary. The other 10
are data-only modules — their data is already in `data.asm`.

### Anonymous Code Symbols

Some fixups in `data.asm` and library `.asm` files reference addresses inside
CRT modules that have **no named symbol**:

| Symbol | Address | Actually In | Description |
|--------|---------|-------------|-------------|
| `_code_06B524` | 0x06B524 | stk386, local label `L$1` | `mov [mem], ss; ret` (init routine) |
| `_code_07606C` | 0x07606C | Gap after `remove_` | Jump table data for ailssa |
| `_code_07626C` | 0x07626C | Gap after `remove_` | Jump table data for ailssa |

These are local labels or data tables embedded in the code segment with no
PUBLIC symbol. They cannot be resolved from clib3r.lib.

### Data Segment Conflicts

`data.asm` contains ALL initialized data (game + CRT + library), defining
3,167 PUBLIC symbols. 66 of these conflict with symbols from clib3r.lib
modules. When clib3r.lib modules are pulled in, their data definitions
generate "redefinition ignored" warnings. This is harmless for data content
but prevents proper module pull-in for data-only exports.

## Original Watcom 10.0 Linker

Tested `bin/wlink.exe` (MZ DOS format, 406KB) via dosemu2 in podman.
**"WATCOM Linker Version 10.0"** — runs successfully.

Results:
- Same undefined symbol issues as OW v2 wlink (LPUBDEF not resolved)
- Additional "relocation offset out of range" errors (likely 16-bit LEDATA
  record limitations when total segment exceeds 64K)
- `OPTION START=` not supported for DOS/4G executables (OW v2 extension)

**Conclusion:** Original wlink 10.0 is MORE restrictive than OW v2 wlink
and produces additional errors. OW v2 wlink is the better choice for linking.

## Decision

Using clib3r.lib for CRT modules is **not viable** for byte-identical output
due to LPUBDEF visibility, module pull-in conflicts, and anonymous symbols.

**Adopted approach:** All code (game + CRT + library) is kept as `.asm` files
with original bytes from PS.EXE. CRT code stays as `.asm` permanently (not a
decompilation target). When decompiling game functions to C, the Watcom CRT
headers from the CD (`watcom/h/*.h`) provide type definitions and prototypes.

## Files

- `CDs/WATCOM_C10A.zip` — Watcom C/C++ 10.0a ISO (git-lfs, 167MB)
- `CDs/watcom10la.iso` — Watcom C/C++ 10.0 prerelease ISO (git-lfs, 47MB)
- `data/watcom/lib386/dos/clib3r.lib` — Extracted from 10.0a (183KB)
- `data/watcom/lib386/dos/clib3r_patched.lib` — LPUBDEF→PUBDEF patched (not used)
