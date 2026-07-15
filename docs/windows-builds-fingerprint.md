# Caesar II Windows Builds — Compiler & Flag Fingerprint

Companion to the DOS `PS.EXE` decomp (the `-d1` Watcom target) and the
fingerprinted Mac CodeWarrior builds.  The **Windows** side had never been
attributed to a compiler/flags before this pass.  This is the
`../lotr2`-style toolchain-provenance sweep applied to every Windows binary
the game ships.

**TL;DR** — The Win95/Win32s `CAESAR2.EXE` is a **Microsoft Visual C++ 4.0**
(linker 3.00, Developer Studio `C:\develop\MSDEV\Projects\C2Win\`)
**Debug build**: static single-threaded debug CRT (`LIBCD`, i.e. `/MLd`),
**`/Od` (no optimization)**, CodeView/PDB debug info.  *Unlike* the DOS
`PS.EXE` (Watcom 10.0a, `-d1`, optimised), the Windows engine is the
**unoptimised debug config** — the analogue of LOR2's `LORDS2.EXE`, which
was likewise a Debug `LORDS2.pdb` build.  This is **not** the byte target of
this project (that stays the DOS `PS.EXE`), but it is a second, independently
compiled witness of the same source tree, in MSVC's far more legible `/Od`
codegen.

> **Tools.**  Re-run with `python scripts/fingerprint_pe.py <files>`.
> Extract from CDs with `bash scripts/extract_windows_binaries.sh`.
> Structured data: [`data/windows-builds/fingerprint.json`](../data/windows-builds/fingerprint.json),
> provenance in [`data/windows-builds/manifest.tsv`](../data/windows-builds/manifest.tsv),
> the binaries in `data/windows-builds/store/` (sha256-named) with readable
> symlinks in `data/windows-builds/named/`.

## Method

The Windows binaries are PE (32-bit) or NE (16-bit), so the
OMF/Watcom-runtime fingerprinting used for the DOS sibling does not apply.
Instead, for PE:

1. **PE optional-header `MajorLinkerVersion`** pins the MS toolchain.
   Authoritative LINK→VC table (geoffchappell *"Strange Things LINK Knows
   About 80x86 Processors"*, cross-checked against the file versions):
   `2.5x → VC2.0 · 3.00 → VC4.0 · 3.10 → VC4.1 · 4.20 → VC4.2 · 5.00 → VC5.0`.
2. **PE link timestamp** = wall-clock build time (a real date here, not a
   `0` repro stamp).
3. **Debug directory** — `MISC` (names the exe → set by `/DEBUG`), `FPO`
   (frame records), `CODEVIEW NB10` (→ the missing `.pdb` path + rebuild
   `age`, the lineage fingerprint).
4. **CRT linkage** — embedded CRT source names (`dbgheap.c`, `dbgrpt.c`) +
   the `"Microsoft Visual C++ Debug Library"` banner ⇒ static **debug** CRT;
   no `MSVCRT*.dll` import ⇒ statically linked; no MT markers
   (`tidtable.c`, `.tls`, `_beginthread`) ⇒ **single-threaded** (`LIBCD`).
5. **Optimization level from codegen** (capstone): locals/loop counters
   reloaded from memory on every use, index arithmetic recomputed (no CSE),
   full `push ebp;mov ebp,esp` frames everywhere, no incremental-link thunk
   table ⇒ **`/Od`**.  The only frame-pointer-omitting (FPO) functions are
   the 59 hand-asm routines in the linked debug CRT, not game code.

## The game engine — `C2WIN95/HD/CAESAR2.EXE` (3 distinct builds)

All three: **MSVC 4.0** (linker 3.00) · PE32 GUI · 6 sections
(`.text .rdata .data .idata .rsrc .reloc`) · static **debug** CRT (`LIBCD`,
single-threaded = `/MLd`) · **`/Od`** · PDB `C:\develop\MSDEV\Projects\C2Win\Caesar2.pdb`.

| Build | sha256 (16) | size | PE link (UTC) | debug dir | PDB age | First seen / carried on |
|---|---|---:|---|---|---:|---|
| **A** | `caca2babb57d9450` | 1 044 480 | 1996-08-28 22:53 | **stripped** (none) | — | USA 1996-08-29; reused on Europe 1997-09-12 & Italy Covermount |
| **B** (DE) | `f719cdc7a8dcf954` | 1 059 840 | 1996-12-09 19:35 | MISC+FPO+NB10 | **1** | Germany Rerelease 1996-12-18 (+ Alt) |
| **C** | `af6401537c103290` | 1 060 864 | 1997-02-28 20:39 | MISC+FPO+NB10 | **12** | USA 1997-03-10 & 1997-11-12; **= the v1.01 patch engine** |

* **Build A is a Debug-config build with its debug *directory* stripped** —
  it still links the debug CRT (`dbgheap.c`, `"…Debug Library"`, `/Od`
  codegen) but carries no PDB/MISC/FPO/CodeView.  The earliest engine; the
  English release that the late-1997 Europe and Italy pressings re-used
  unchanged.
* **Builds B & C keep the CodeView NB10 reference** to the (never-shipped)
  `Caesar2.pdb`, with rebuild `age` 1 → 12 — the same per-PDB incremental
  link-counter lineage fingerprint seen on LOR2.  B and C share an
  **identical `.text` size (854 528 B) and prologue count (2148)**; they are
  near-adjacent links of the same code (B = German rerelease, C = the v1.01
  zoom-out-crash patch).
* **`C:\develop\MSDEV\Projects\C2Win\`** — Microsoft Developer Studio (VC4.x)
  project tree; the Windows port was its own MSDEV project (`C2Win`),
  separate from the DOS Watcom build.
* **`/Od` proof:** loop counters live in memory and reload every iteration
  (e.g. `movsx eax, word ptr [0x55afc0]` repeated), `index*size` arithmetic
  recomputed rather than cached, `push ebx/esi/edi` saved-but-unused — no
  enregistration, no CSE.  The 59 FPO records are all CRT asm routines.
* **Win32s, not pure Win95:** imports `WING32` (WinG, the early Win95 game
  blit API — *not* DirectDraw) and the **Win32s** sound/video DLLs below, so
  the engine ran under Win32s on Windows 3.1x as well as natively on Win95.

The flag reconstruction for the engine:
`cl /MLd /Od /Zi /D_DEBUG …  /  link /SUBSYSTEM:WINDOWS /INCREMENTAL:NO /DEBUG`
(build A linked without emitting the debug directory).

## Bundled third-party DLLs (in `C2WIN95/HD/`)

| File | sha256 (16) | size | Compiler / linker | Build | Identity |
|---|---|---:|---|---|---|
| `WAIL32.DLL` | `1a9c8bf6fe5e08f8` | 135 680 | **MSVC 4.0** (linker 3.00) | **Release** (`"…Runtime Library"`, no debug dir) | **Miles Sound System v3.50** AIL Win32s driver (`"…usage script generated by MSS V3.50"`) |
| `SMACKW32.DLL` | `1bceeb7d56fdb8f5` | 61 952 | **Watcom C/C++32** (wlink 2.18) | 3rd-party | RAD **Smacker** Win32s video (`"WATCOM C/C++32 Run-Time system"`, `Smacker_for_Win32s`, `BEGTEXT`/`DGROUP` segs) |

Note the Windows port uses **Miles MSS 3.50** for audio, whereas the DOS
`PS.EXE` links **AIL 3.03** (`docs/external-libs/`).  Both audio and video
Windows DLLs are **Win32s** builds (consistent with the engine's Win32s
targeting).  Neither is game code; both are vendor binaries.

## Installer / patch plumbing (not game code)

| File | sha256 (16) | format | Toolchain | What it is |
|---|---|---|---|---|
| `INSTALL/WINUPD.EXE` | `aeb6cb385d125652` | PE32 | **MSVC 2.x** (linker 2.55) | Win32s-setup launcher (`INSTALL\WIN32S\DISK1\MSSETUP.EXE`) |
| `INSTALL/WINUPD16.EXE` (a) | `5c60d07a3f5af962` | NE 16-bit | MS LINK 5.60 | MSSETUP/WinG launcher stub (Europe OEM + 1996-04 only) |
| `INSTALL/WINUPD16.EXE` (b) | `14484a328005abc2` | NE 16-bit | MS LINK 5.60 | MSSETUP/WinG launcher stub (all later pressings) |
| `Patch/C2WINPCH.EXE` | `50d5c95a6d2143ea` | NE wrapper | **PKWARE PKSFX** (1989-1996) | 1999 *"Caesar II Win95 v1.01 Patch"* — a self-extracting ZIP. Inner payload = **build C `CAESAR2.EXE`** (byte-identical) + `NTEXTS.TXT` + readme. Adds no new engine. |

## DOS `PS.EXE` ↔ Windows `CAESAR2.EXE` — same disc, same source tree

The decomp target `data/PS.EXE` (the `-d1` debug build, sha `4a41f68d…`, md5
`23bdf1fd…`) is **not a standalone artifact** — it is the DOS engine that
ships, **byte-identical**, on *every* Win95-rerelease CD, and each of those
discs **also carries a Windows `CAESAR2.EXE`**.  The two engines are built
from the **same source tree** by different toolchains:

| CD | DOS `HD/PS.EXE` | Win `C2WIN95/HD/CAESAR2.EXE` |
|---|---|---|
| USA Rerelease 1996-08-29 | `4a41f68d` (debug `-d1`, 1996-04) | **A** `caca2` 1996-08-28 |
| Europe Rerelease 1997-09-12 | `4a41f68d` | **A** `caca2` |
| Italy Covermount | `4a41f68d` | **A** `caca2` |
| Germany Rerelease 1996-12-18 (+Alt) | `4a41f68d` | **B** `f719` 1996-12-09 (DE) |
| USA Rerelease 1997-03-10 | `4a41f68d` | **C** `af640` 1997-02-28 (v1.01) |
| USA Rerelease 1997-11-12 | `4a41f68d` | **C** `af640` (v1.01) |

(The older DOS-only pressings — Europe original/OEM/1996-04-25, France,
Germany original, USA 1995-10-06 — carry an *earlier* un-symbolled engine
`c95790fa`/`e18875e9` and **no** Windows build.)

**Re the "1.01 patch" question:** the **DOS** engine is *not* the v1.01 patch.
It is the original engine, frozen at the 1996-04 `-d1` build and shipped
unchanged across the whole rerelease line; it **predates** v1.01.  The v1.01
fix (the zoom-out crash) is **Windows-only** — it is Windows build **C**
(1997-02), the engine inside `C2WINPCH.EXE`.  The DOS side was never
re-patched.  So:

* The **temporally-closest Windows witness** to the DOS `-d1` snapshot is
  build **A** (1996-08, ~4 months after the 1996-04 DOS build).
* All three Windows builds share the engine source with the DOS target; A is
  the nearest, C is the later (v1.01) revision of that same source.

Because the Windows engine is the **`/Od`** compilation of this shared
source, it keeps every statement and local explicit — a second, legible
witness of the same code, complementary to the Watcom `-d1` target and the
Mac CodeWarrior decompile.

## Proof: the CRT in `CAESAR2.EXE` *is* Visual C++ 4.0's debug CRT

The version attribution is not just inferred from the linker byte — it is
**byte-proven** against the actual VC4.0 toolchain, the way the DOS side was
proven against Watcom 10.0a.

**Compiler obtained:** [`github.com/itsmattkc/MSVC400`](https://github.com/itsmattkc/MSVC400)
(commit `821e942`, "portable VC++ 4.00 command-line tools") — the x86 sibling
of the locally-archived `msvc-4.20`.  Its `LINK.EXE` self-reports
**`3.00.5270`** and `CL.EXE` **`10.00.5270`** — i.e. Visual C++ 4.0, exactly
the linker version stamped in all three `CAESAR2.EXE` builds.
Provenance hashes (sha256): `LIBCD.LIB 08eff0dd…`, `LIBC.LIB e5f0d0e6…`,
`LINK.EXE 81109c8c…`, `CL.EXE f097e736…`.

**Method** (`scripts/verify_msvc_crt.py`): parse VC4.0's `LIBCD.LIB` (debug)
and `LIBC.LIB` (release) COFF archives, pull each chosen object's `.text` +
relocation table, mask the 4-byte DIR32/REL32 link-patched slots, and search
the binary's `.text` for the masked run.

**Result — identical for builds A, B and C:**

1. **CRT leaf routines match byte-exact** vs VC4.0 `LIBCD`: `chkstk` (47 B),
   `strlen` (119 B), `memset` (88 B), `strcat` (232 B), `memcpy` (334 B,
   12 relocs masked) — each found exactly in the binary's `.text`.
2. **Debug discriminator:** `malloc.obj` and `free.obj` have *different* code
   in debug vs release (LIBCD `malloc` 34 B / `free` 44 B; LIBC 20 B / 24 B).
   The binary matches the **LIBCD (debug)** variant and **not** the LIBC
   (release) variant ⇒ the CRT is the **debug** CRT, `LIBCD.LIB` (single-
   threaded, `/MLd`).  Corroborated by the embedded `"Microsoft Visual C++
   Debug Library"` banner + `dbgheap.c`/`dbgrpt.c` source names.

Reproduce:

```bash
git clone --depth 1 https://github.com/itsmattkc/MSVC400 /tmp/MSVC400
python scripts/verify_msvc_crt.py data/windows-builds/named/caesar2_C_1060864.exe /tmp/MSVC400
```

(The DOS-side analogue — proving `PS.EXE` against Watcom 10.0a's `clib3r` —
uses the locally-held `CDs/WATCOM_C10A.zip`; established in
`../lotr2/docs/binaries.md` and the caesar2 toolchain notes.)

## Cross-reference to the DOS / Mac targets

| Target | Compiler | Optimization | Debug info | Role here |
|---|---|---|---|---|
| **DOS `PS.EXE`** (`data/PS.EXE`) | Watcom C/C++ **10.0a** | optimised (`-mf -4r -s`, OptSize 50) | `-d1` line numbers + 7 092 symbols | **the byte-decomp target** |
| **Win `CAESAR2.EXE`** | **MSVC 4.0** | **`/Od` (none)** | CodeView NB10 → lost `Caesar2.pdb` | secondary witness; unoptimised, legible codegen of the *same source* |
| **Mac (1996 CW Pro 1)** | Metrowerks CodeWarrior | — | full inline name table (~1 293–1 555 names) | source-shape oracle (`c2 mac-decompile`) |

The Windows engine is a **second compilation of the same C source** by a
completely different toolchain.  Because it is `/Od`, its control flow and
variable use map more directly to the source than Watcom's optimised output —
a potential **shape oracle** for ambiguous DOS functions (the MSVC `/Od`
build keeps every statement and local explicit), complementary to the Mac
CodeWarrior decompile.  Its lost `Caesar2.pdb` is the only thing standing
between us and full Windows-side symbols — same dead-end as LOR2's
`Lords2.pdb`.
