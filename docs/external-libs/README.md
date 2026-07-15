# External libraries — research, headers, leads

Everything we know about the third-party libraries and extender linked into
PS.EXE.  The Watcom 10.0a compiler/CRT is covered by the separate
`ReverseEngineering/watcom-compilers` reservoir; its CD contains ordinary
DOS/4GW, not the DOS/4GW Professional binder kit.

## Targets

| Library | Version | Source path in PS.EXE | Modules linked |
|---------|---------|------------------------|----------------|
| **Miles AIL** (Audio Interface Library) | 3.03 (DOS flat / Watcom register-call) | `R:\NET\LIBS\AIL\DEV3\FLAT\` | 10 OMF modules, ~63 KB |
| **RAD Smacker SDK** | 2.0 (DOS flat / Watcom) | `C:\DEVEL\PROJECTS\SMACK\20\` | 5 OMF modules, ~25 KB |

Adjacent original libraries have now surfaced publicly: AIL 3.03b and a
genuine Smacker 2.0 DOS/Watcom archive.  Neither is the exact revision linked
into PS.EXE, but most of the Miles routines are exact.  DOS/4GW Professional
1.97's original binder/runtime kit is also online.  See
[`online-binary-findings-2026-07-15.md`](online-binary-findings-2026-07-15.md)
for URLs, hashes, and byte-comparison results.  We do **not need** the vendor
libraries for byte-identical rebuilds because the linked objects have already
been delinked from PS.EXE.

## Layout

```
docs/external-libs/
├── README.md                ← you are here
├── prompts/                 Deep-research prompts (re-runnable)
│   ├── miles-ail-3.03.md
│   └── smacker-sdk-2.0.md
├── reports/                 Deep-research result reports + analysis
│   ├── miles-ail-3.03.md      45 KB — full URL inventory + leads
│   ├── smacker-sdk-2.0.md     45 KB — full URL inventory + leads
│   └── lib-name-hypotheses.md  hypothesised .LIB/.OBJ filenames + verification recipe
└── headers/                 Canonical API surface (small, kept for compile-time reference)
    ├── ail/
    │   ├── mss-v1.01.h           THE V3.03 header (banner: "1.01 of 19-Jun-95")
    │   ├── mssw-win32.h          Miles for Win32 cross-reference
    │   ├── ail32-v1.05.h         Public-domain ancestor (1993)
    │   └── AIL32-v1.05-LICENSE.txt  John Miles' May-2000 PD release
    └── smacker/
        └── smack-v3.2f.h         JA2/MiG leak (md5-identical from both sources)
```

## Provenance, very briefly

- **`mss-v1.01.h`** — extracted from `github.com/CookiePLMonster/VBdec`
  (GTA III/VC Bink VB decoder). Identical copies exist in the leaked
  Source Engine 2007 tree, the Re-Volt source release, and FlyFF.
  Header banner explicitly states *"Added various functions for V3.03
  release"*.
- **`mssw-win32.h`** — from `github.com/gondur/mig_src` (MiG Alley
  source release by the original author). Cross-reference for Win32
  ABI questions.
- **`ail32-v1.05.h`** — from `archive.org/details/vfx119` → AIL2.ZIP →
  REL105.ZIP. **Public domain** per the included
  `AIL32-v1.05-LICENSE.txt` (John Miles, 2000).
- **`smack-v3.2f.h`** — from `github.com/dariusk/ja2` (Jagged Alliance
  2 leaked source). MD5-identical to the copy in `gondur/mig_src`, so
  not an isolated hand-edit.

## What's deliberately **not** kept here

The deep-research process pulled ~30 MB of supplementary material
(public-domain SDK ZIPs, several GitHub repo clones, MK1.EXE as a
Rosetta candidate, decompilation tools). All of that has been removed
to keep the repo lean.

The complete URL inventory is preserved inside the two
[`reports/`](reports/) markdown files — every single link the deep
researcher touched (hits, leads, exhausted dead-ends) is in section 5
of each report. That's the recovery anchor.

To re-acquire any of the bulk artifacts later, see
[`reports/lib-name-hypotheses.md`](reports/lib-name-hypotheses.md) for
the verification recipe and the two report files for the source URLs.
The most valuable items, ranked, are:

1. **Mortal Kombat 1 (CD, 1996)** — `archive.org/details/msdos_Mortal_Kombat_1993` (43 MB ZIP, only `MK/MK1/MK1.EXE` ~1.2 MB matters). Same `R:\NET\LIBS\AIL\DEV3\FLAT\` build path; byte-identical `.DIG` driver binaries to Caesar II. Use as Rosetta stone for AIL3.
2. **AIL/32 v1.05 source** — `archive.org/details/vfx119` → `AIL2.ZIP` (2.1 MB). Public-domain ancestor of AIL 3.x. Contains `dllload.c`, `mix32.c`, `stp32.c`, etc., plus pre-built `WR/AIL32.OBJ` (Watcom register-call OMF).
3. **wcdatool / wcdctool** — `github.com/fonic/wcdatool` and `github.com/victor-zinkv/wcdctool`. The Watcom decompilation tools needed to disassemble MK1.EXE.

## Status

The original deep-research reports are retained as search history, but their
"no public DOS library" conclusions are superseded by the 2026-07-15 binary
findings linked above.
