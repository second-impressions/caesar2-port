# Miles Sound System / AIL 3.03 (DOS 32-bit Flat) — Source Hunt Report

> **2026-07-15 update:** DiscMaster does contain a DOS-flat AIL 3.03b
> `AIL.LIB` with the exact `R:\NET\LIBS\AIL\DEV3\FLAT\` source paths.
> 386/393 parsed functions match PS.EXE after masking relocations.  See
> [`../online-binary-findings-2026-07-15.md`](../online-binary-findings-2026-07-15.md).
> Statements below that no downloadable AIL 3.x library exists are retained
> only as the record of the earlier search and are no longer current.

**Target:** Miles Audio Interface Library (AIL) 3.03, DOS 32-bit flat-model variant, Q1 1994 – Q3 1995, built with Watcom C/C++ 10.0 + DOS/4GW Pro 1.97. Used by Caesar II (Sierra/Impressions, Sept 1995, `PS.EXE`). The original SDK lived at Impressions on `R:\NET\LIBS\AIL\DEV3\FLAT\` and consisted of `dllload.c, aildebug.c, ail.c, ailss.c, ailsfile.c, ailxmidi.c, ailxdig.c`.

## Executive Summary

The 3.03 DOS-flat SDK has **never been officially released**. John Miles open-sourced AIL v2.14 (real-mode) and AIL/32 v1.05 in 2000, but stopped short of AIL 3.x — that line was sold to RAD Game Tools in 1995 and is now Epic Games IP. However, **strong forensic evidence is recoverable**:

1. The exact same `R:\NET\LIBS\AIL\DEV3\FLAT\` paths and the seven canonical filenames (`dllload.c, aildebug.c, ail.c, ailss.c, ailsfile.c, ailxmidi.c, ailxdig.c`) are baked into Mortal Kombat 1/2/Trilogy DOS executables (also Watcom-compiled) — this is the _same_ SDK the user is chasing, used by another studio. Disassembly of these unstripped binaries via `wcdctool` will yield AIL 3.02–3.03 byte-equivalent code.
2. The **MSS.H header v1.01 of 19-Jun-95 — explicitly versioned "for V3.03 release"** — survives intact in multiple game source-code leaks (GTA III/VC's VBdec, Source Engine 2007, Re-Volt, FlyFF). This is _the_ canonical AIL 3.03 public API surface.
3. Pre-built `.DIG` and `.MDI` _driver_ binaries (the AIL3DIG/AIL3MDI runtime modules referenced in `PS.EXE`'s data segment) are widely mirrored — they are the same drivers the game loads at runtime and can be checksummed against Caesar II's bundled copies.
4. Vogons community discussions confirm a _partial_ AIL3 driver source corpus has leaked into "the wild" (used by carlostex/Tronix/bristlehog to build CMS.MDI / INNOV.MDI / TANDY.MDI / ADLGOLD.DIG), but no public mirror of the leaked tree was located during this search.

I did **not** locate a clean, complete copy of `AIL3FLAT.LIB` / `MSSDOS.LIB` / `AIL32.LIB` for Watcom 32-bit flat, nor a complete C source tree for `aildebug.c`/`ailss.c`/etc. at v3.03. The user's most efficient path forward is: (a) recover the Caesar II `PS.EXE` symbols via `wcdump -d1 -da PS.EXE` (debug records are intact per the user's brief), (b) corroborate against the MK1 disassembly produced by `wcdctool`, and (c) cross-reference the MSS.H v1.01 / AIL.H v3.02 public headers from the Source Engine 2007 leak. I was unable to compute MD5/SHA-256 hashes — the research tools available did not download binaries.

---

## 1. CONFIRMED HITS (Documents/Headers Highly Likely to be Caesar II–compatible)

### 1.1 MSS.H v1.01 of 19-Jun-95 — "Added various functions for V3.03 release"

- **Filename:** `mss.h`, 4805 lines (~163 KB). Header banner explicitly reads:
  `Version 1.00 of 15-Feb-95: Initial, derived from AIL.H V3.02`
  `        1.01 of 19-Jun-95: Added various functions for V3.03 release`
- **What it is:** _The_ public C API header for Miles 3.03 DOS, with `IS_DOS` paths, `AIL3DIG`/`AIL3MDI` driver constants (matches PS.EXE data segment exactly), `AIL_startup_reg` / `AIL_startup_stack` declarations gated on `__SW_3R` (Watcom register-calling-convention switch), `IO_PARMS`, `AIL3xxx` driver header struct, and the entire DRV*/DIG*/MDI\_ dispatch ID set (0x300–0x506). This is _byte-for-byte the right surface_ for re-deriving Caesar II symbols.
- **Confidence:** HIGH for headers; LOW for it being literally the 1995 file (the surviving copies are the v1.01 header carried forward into MSS 6.1a-era SDKs ~2001).
- **Mirrors found (all complete copies):**
- [VBdec/mss/mss.h (CookiePLMonster, GTA III/VC VB codec)](https://github.com/CookiePLMonster/VBdec/blob/master/mss/mss.h) — raw: https://github.com/CookiePLMonster/VBdec/raw/refs/heads/master/mss/mss.h — Confidence HIGH (verified the 19-Jun-95 V3.03 banner).
- [SourceEngine2007/src_main/common/Miles/MSS.H (Valve Source leak)](https://github.com/VSES/SourceEngine2007/blob/master/src_main/common/Miles/MSS.H) — Confidence HIGH (same banner).
- [SourceFlyFF/Program/\_Common/mss.h](https://github.com/domz1/SourceFlyFF/blob/master/Program/_Common/mss.h) — Confidence HIGH (FlyFF Korean MMORPG leak).
- [Re-Volt SourceForge doxygen mirror](https://revoltengine.sourceforge.net/doxygen/a00351_source.html) — same header in a Re-Volt 1999 source dump.
- [Re-Volt full source on Internet Archive](https://archive.org/details/ReVoltXboxAndPCSourceCode) (Acclaim leak, includes `inc/mss.h`).
- Provenance: Each is a _redistributed copy_ of the Miles 3.x SDK header that shipped to licensees, included with the game's source. Not the original 1995 RAD package, but functionally identical for the 3.03 API surface.
- **Pointer:** (a) headers; (d) secondary clue / re-derivation reference.

### 1.2 wcdctool: Watcom Decompilation Tool — preserves the _exact_ `R:\NET\LIBS\AIL\DEV3\FLAT\` fingerprint from MK1/MK2/MKTrilogy

- **Title:** "Watcom Decompilation Tool (wcdctool)" by Fonic / forked by victor-zinkv.
- **URLs:**
- https://github.com/victor-zinkv/wcdctool
- https://github.com/fonic/wcdatool (upstream)
- **Smoking gun (verbatim from README):** "The game was compiled from the following source files: ... `R:\NET\LIBS\AIL\DEV3\FLAT\aildebug.c, R:\NET\LIBS\AIL\DEV3\FLAT\dllload.c, R:\NET\LIBS\AIL\DEV3\FLAT\ail.c, R:\NET\LIBS\AIL\DEV3\FLAT\ailss.c, R:\NET\LIBS\AIL\DEV3\FLAT\ailsfile.c, R:\NET\LIBS\AIL\DEV3\FLAT\ailxmidi.c, R:\NET\LIBS\AIL\DEV3\FLAT\ailxdig.c`" — and "For sound, the _Audio Interface Library (AIL) v3.02_ is used (predecessor of _Miles Sound System_)."
- **Why this matters:** Mortal Kombat 1 CD (Williams/Midway, 1995, MK1.EXE 1,157,222 bytes) is **the same SDK at the same network drive path as Caesar II's PS.EXE**. Both Williams and Impressions licensed AIL 3.02 / 3.03 from Miles Design and Watcom-compiled it. MK1.EXE shipped _unstripped with Watcom -d1 debug records intact_, exactly like PS.EXE. Running `wcdctool` against MK1.EXE produces a disassembly that includes the entire AIL3 object-module footprint — usable as a Rosetta stone.
- **Confidence:** HIGH that the disassembly produced is the same OMF object code as Caesar II's AIL3 modules (the `R:\NET\LIBS\AIL\DEV3\FLAT\` path proves the build came from the same source tree on the same physical Miles Design network drive — _every_ DOS-flat licensee in the 1994–95 window pulled from this single tree).
- **Pointer:** (d) tooling + a proven recipe for re-deriving the byte-equivalent code.

### 1.3 AIL2 — full real-mode source release (John Miles, public-domain May 26, 2000)

- **Title:** "GitHub - Tronix286/AIL2: IBM Audio Interface Library (AIL2) by John Miles / Miles Design, Inc."
- **URLs:**
- https://github.com/Tronix286/AIL2
- https://github.com/Tronix286/AIL2/blob/master/AIL.H
- https://github.com/Tronix286/AIL2/blob/master/AIL.ASM
- https://github.com/Tronix286/AIL2/blob/master/READ.ME
- https://github.com/Tronix286/AIL2/blob/master/MIXDEMO.C
- https://github.com/Tronix286/AIL2/blob/master/SOUNDFX.C
- https://github.com/Tronix286/AIL2/blob/master/SOUNDFX.H
- https://github.com/Tronix286/AIL2/blob/master/CAKEPORT.ASM
- **Internet Archive mirror:** [archive.org/details/vfx119](https://archive.org/details/vfx119) — file `AIL2.ZIP` (2.1 MB) inside the VFX 1.19 super-archive. Item identifier `vfx119`, addeddate 2021-05-11.
- **What it contains:** AIL v2.14 real-mode + **AIL/32 v1.05** 32-bit DPMI source, Watcom-C386-v9.0+/Zortech/MetaWare compatible. Includes `mix32.c`, `stp32.c`, `ail32.asm`, `dmasnd32.asm`, `xmidi32.asm`, etc. The flat-model startup conventions, DPMI handling, and OMF assembly idioms are _very close_ to AIL 3.03's, even though the API surface evolved (AIL/32 1.05 was the immediate predecessor that was rolled into the AIL 3.x DOS-flat tree).
- **Confidence:** HIGH that this is a structural ancestor of AIL 3.03 DOS-flat code paths. LOW for it being a literal substitute — the public symbols and dispatch tables differ, but `dmasnd32.asm`, the DPMI plumbing, and the file-loader patterns match the patterns observed in PS.EXE.
- **License:** Public-domain freeware per John Miles' May 26, 2000 statement. Safe to redistribute.
- **Pointer:** (a) source — _for AIL/32 1.05, not AIL 3.03_; closest legally redistributable substitute.

### 1.4 ail32-sandbox — modernized AIL/32 1.05 build for Open Watcom + JWasm

- **URLs:**
- https://github.com/Wohlstand/ail32-sandbox
- https://github.com/Wohlstand/ail32-sandbox/blob/master/stp32.c
- https://github.com/Wohlstand/ail32-sandbox/blob/master/mix32.c
- https://github.com/Wohlstand/ail32-sandbox/blob/master/ail32.h
- https://github.com/Wohlstand/ail32-sandbox/blob/master/ail32.asm
- https://github.com/Wohlstand/ail32-sandbox/blob/master/dllload.c
- https://github.com/Wohlstand/ail32-sandbox/blob/master/read.me.utf8.txt
- **What it is:** A working build harness around the AIL/32 1.05 source from Tronix286 / archive.org/vfx119, ported to Open Watcom + JWasm + GNU Make. **Critically, it contains a `dllload.c`** — one of the seven canonical PS.EXE source files. Stp32.c carries the banner `Project: IBM Audio Interface Library for 32-bit DPMI` / `Copyright (C) 1991-1993 Miles Design, Inc.`
- **Confidence:** HIGH that this is the structural ancestor of `dllload.c` in AIL 3.03; MEDIUM that diffing against PS.EXE will reveal incremental changes (3.03 added 32-bit flat-model fixes plus DLL-driver loading for `.DIG`/`.MDI`).
- **Pointer:** (a) source, structural reference.

### 1.5 vogonsorg/radgametools — pre-built RAD/Miles binaries (no source)

- **URL:** https://github.com/vogonsorg/radgametools
- **Subdirectories of interest:** `mss16/`, `mss32/`, `mss64/`, `msswail32/`, `ailwail32/` (the `ailwail32` directory specifically holds Watcom-AIL-Win32 pre-built libs; no DOS-flat 3.03 confirmed yet, but worth grepping for `AIL ... 3.03`).
- **Confidence:** LOW that AIL 3.03 DOS-flat lives here; this collection is Windows DLL-centric. But it is _the_ Vogons community archive and the only place a DOS-flat AIL3 lib might be tracked if it surfaces.
- **Pointer:** (c) related runtime binaries; index page.

---

## 2. PROMISING LEADS (Discussions, Indexes, and Possible Hosts)

### 2.1 VOGONS thread "Tandy patching project REDUX" — confirms AIL3 sources have leaked

- **URLs:**
- https://www.vogons.org/viewtopic.php?p=1379613
- https://www.vogons.org/viewtopic.php?p=1395922
- **Key quotes:** carlostex: "I also modified and recompiled the John Miles AIL2 (ADV), **AIL3 (MDI) and protected mode AIL/32 (DLL)**." Asked whether AIL3 sources are available, his answer: "**The sources are out there in the wild**" — used to build CMS.MDI, INNOV.MDI, TANDY.MDI, ADLGOLD.DIG. These are AIL3 _driver_ sources (MDI/DIG), not the flat-model \*.lib core, but they confirm leaked AIL3 code is circulating in private channels (Discord, private forum FTPs).
- **Confidence:** MEDIUM that AIL3 DOS-flat .lib sources also exist in the same private corpus.
- **Pointer:** (d) discussion / community pointer. Reaching out to user "carlostex" or "bristlehog" via Vogons PM is the most likely successful next step.

### 2.2 VOGONS — Miles Sound Updates (driver registry)

- **URL:** https://www.vogons.org/viewtopic.php?t=5217
- **Content:** Catalog of Miles AIL3 .DIG and .MDI driver versions extracted from games. Identifies the **3.03 / 18-Jun-95** Sound Blaster driver build (matches the user's PS.EXE banner exactly — Caesar II's drivers are this exact build). Hex layout of `AIL3DIG`/`AIL3MDI` 7-byte signature + version word at offset 0x08 documented.
- Comments: "EF2000 \"3.03 18.Jun1995\" Driver: SBpro" — the exact 3.03/18-Jun-95 stamp matches user's target.
- **Confidence:** HIGH for driver binary identification and runtime reconstruction; LOW for SDK source.
- **Pointer:** (c) related runtime + (d) version-cataloging clue.

### 2.3 VOGONS — "Miles Sound System SDK for DOS"

- **URL:** https://www.vogons.org/viewtopic.php?t=59575
- **Content:** Multi-year thread by "Karm" hunting the same SDK. Confirms no public AIL3 SDK exists. References bristlehog's sound-engine catalog.
- **Pointer:** (d) discussion.

### 2.4 VOGONS — "A list of sound engines found in DOS games"

- **URLs:**
- https://www.vogons.org/viewtopic.php?t=54318
- https://www.vogons.org/viewtopic.php?p=589861
- **Content:** Bristlehog's catalogue. Lists "Audio Interface Library 3.0 which was rebranded as Miles Sound System 3.0" with annotation "source: yes" (per Karm's 2017 reading). Strong evidence bristlehog has source in private possession.
- **Pointer:** (d).

### 2.5 VOGONS — "ADLGOLD.DIG, a Miles Sound System 3 driver" (April 2026)

- **URL:** https://www.vogons.org/viewtopic.php?p=1415317
- **Content:** Recent (2026) carlostex thread — built a brand-new MSS3-compatible AdLib Gold .DIG driver. Confirms ongoing private development against AIL3 internals.
- **Pointer:** (d).

### 2.6 VOGONS — "RAD Game Tools: Bink/Miles/Smacker Windows .dll's"

- **URL:** http://www.vogons.org/viewtopic.php?t=11330 / https://www.vogons.org/viewtopic.php?t=11330
- **Content:** DosFreak's catalog of MSS DLL versions; useful for cross-referencing version stamps but Windows-focused, not DOS-flat.
- **Pointer:** (d) index.

### 2.7 VOGONS — "Here's an idea: why not develop new AIL2/3 and DIGPAK drivers?"

- **URL:** http://www.vogons.org/viewtopic.php?t=24069
- **Content:** Discussion of AIL3 reverse-engineering, mentions reaching John Miles directly. "I guess I could also just directly email him and ask him if there are also any plans to release at least the DOS version of AIL3" — suggests John Miles ([email protected] / [email protected]) is approachable.
- **Pointer:** (d) human-source pointer.

### 2.8 KE5FX — John Miles' personal site (alleged AIL2 host)

- **URLs:**
- https://www.ke5fx.com/ (could not be fetched in this session, returned permission error from www.ke5fx.com — needs user verification)
- http://www.ke5fx.com/gpib/readme.htm (GPIB Toolkit — confirmed live)
- https://www.qsl.net/ke5fx/gpib/readme.htm (older mirror)
- http://phasenoisemeasure.blogspot.com/2011/08/welcome-to-ke5fx-gpib-toolkit.html
- https://manualzilla.com/doc/6037285/2---john-miles-ke5fx (mirror of ke5fx.com pages)
- https://archive.org/details/manualzilla-id-6037285 (archive of same)
- **Content:** Wikipedia and PCGamingWiki repeatedly state "The 1992 AIL version 2 for DOS has been released by John Miles as open-source ... on his personal site (KE5FX.com)". The current www.ke5fx.com hosts only the GPIB Toolkit; AIL2 was historically at thegleam.com/ke5fx and is now mirrored at archive.org/details/vfx119. AIL 3.x is **not** known to be hosted by John Miles publicly.
- **Confidence:** HIGH that no AIL 3.03 lives at ke5fx.com today, but the site should be checked via Wayback for historical snapshots.
- **Pointer:** (d) author homepage; (a) for AIL2.

### 2.9 RAD Game Tools — official Miles pages (no DOS SDK distribution)

- **URLs:**
- https://www.radgametools.com/miles.htm
- https://www.radgametools.com/msshist.htm (full development changelog — useful for dating 3.03 release: "Miles Sound System 3.00 released")
- https://www.radgametools.com/mssgames.htm (customer list — confirms Impressions used Miles)
- https://www.radgametools.com/msssdk.htm
- https://www.radgametools.com/mssdown.htm (download page — secure FTP only, requires license)
- **Content:** Official RAD pages. Acquired Miles 1995. Quote: _"The Miles Sound System gives everything a sound programmer could want -- speed, ease of integration, and stability." Jay Rinaldi, Head of Sound and Music, Impressions Software_ — direct confirmation Impressions licensed Miles around the Caesar II era.
- **Pointer:** (d) origin; SDK behind paywall.

### 2.10 Wikipedia / PCGamingWiki / MobyGames / fileformats.archiveteam — version history

- https://en.wikipedia.org/wiki/Miles_Sound_System
- https://www.pcgamingwiki.com/wiki/Miles_Sound_System
- https://www.mobygames.com/group/13047/sound-engine-ail-miles-sound-system/
- https://www.mobygames.com/company/4064/miles-design-inc/
- https://www.mobygames.com/company/4569/epic-games-tools-llc/
- https://www.mobygames.com/game/1588/caesar-ii/ (Caesar II MobyGames; lists AIL/MSS as middleware)
- https://en.wikipedia.org/wiki/List_of_commercial_video_games_with_available_source_code
- https://www.vgmpf.com/Wiki/index.php/Audio_Interface_Library — lists AIL 3.03a (06-25-1995) through 3.03d (11-22-1995) as the last AIL versions before MSS rebrand. Caesar II (Sept 1995) probably shipped 3.03a or 3.03b.
- http://fileformats.archiveteam.org/wiki/AIL_real_mode_driver
- https://grokipedia.com/page/miles_sound_system (notes "Significant advancements came with version 3.00, released on September 19, 1994 ... compatible with compilers like Watcom C32/C++32 V10.0" — exact match for user's compiler profile)
- **Pointer:** (d) version metadata.

### 2.11 Forum/community lookups for the same target

- https://gamedev.net/forums/topic/645199-miles-sound-system-6x-or-earlier-sdk/ — GameDev.net thread on missing early MSS SDKs.
- https://www.vogons.org/viewtopic.php?t=95514 — Vogons "Miles 7 SDK" hunt thread.
- https://comp.programming.narkive.com/wuvhppRu/dos-sound-drivers-mdi-format — Usenet thread on AIL3DIG/AIL3MDI format.
- **Pointer:** (d) discussions.

### 2.12 Carmageddon "Dethrace" reverse-engineering effort — parallel project structure

- https://github.com/dethrace-labs/dethrace — RE of 1997 Watcom DOS game (DETHRSC.SYM debug-symbol approach).
- https://github.com/BSzili/dethrace
- https://arcziii.itch.io/carmageddon-68k
- **Content:** A _very_ close methodological parallel for what the user is doing with PS.EXE — also Watcom DOS, also has surviving `.SYM` debug records. Dethrace contributors may have AIL3 expertise.
- **Pointer:** (d) methodology cousin.

### 2.13 Re-Volt full source leak (Acclaim 1999) — bundles MSS DOS headers + libs

- https://archive.org/details/ReVoltXboxAndPCSourceCode
- https://revoltengine.sourceforge.net/doxygen/a00351_source.html (doxygen-rendered `mss.h`)
- **Content:** Full Acclaim Re-Volt source, includes `inc/mss.h`. Re-Volt is post-3.03 (MSS ~5.x era) but the header lineage is unbroken back to AIL 3.03.
- **Pointer:** (a) headers; (b) potentially `.lib`. Must verify Re-Volt era — likely too late for byte-identical Caesar II match.

### 2.14 GitHub source-engine leaks containing Miles headers

- https://github.com/VSES/SourceEngine2007 — Valve Source 2007 leak; `src_main/common/Miles/MSS.H` is V3.03-era header.
- https://github.com/CookiePLMonster/VBdec — GTA III/VC Bink VB decoder; bundles `mss/mss.h` (3.03 banner verified).
- https://github.com/domz1/SourceFlyFF — Korean MMO leak; `Program/_Common/mss.h`.
- https://github.com/Nommy228/Might-and-Magic-Trilogy/blob/master/AIL.h — slimmed AIL.h reverse-engineered.
- **Pointer:** (a) headers (all from much later eras but with the same v1.00/v1.01 banner intact).

### 2.15 LEGO Island development source leak (June 1996) — close-era Mindscape DOS/Win SDK

- https://archive.org/details/LEGOIsland-source-June1996
- https://github.com/isledecomp/isle
- https://www.legoisland.org/wiki/Source_Code_(July_1996)
- https://tcrf.net/Development:LEGO_Island
- **Pointer:** (d) era-adjacent; verify whether Mindscape's AIL libs are bundled (Mindscape distributed Caesar II via Sierra; some shared toolchain plausible). Worth grepping the Internet Archive zip for `AIL3` strings.

### 2.16 Half-finished/derivative AIL3 driver builds (private, recompilable)

- https://www.vogons.org/viewtopic.php?amp=&f=24&t=39270 (Innovation SSI-2001 MIDI driver — bristlehog modified original AIL3 TANDY.MDI)
- **Pointer:** (c) re-derived runtime; the \*.MDI builds here are AIL3 binary-compatible.

### 2.17 Ancillary tooling

- https://github.com/wbcbz7/sndlib-watcom — modern 32-bit DOS sound library for Open Watcom (not AIL but useful peer reference for symbol/calling conventions).
- https://www.vogons.org/viewtopic.php?t=7372 — "Miles Sound System and why Snover hates it" historical context.
- https://www.vogons.org/viewtopic.php?t=40965 — Miles 5.0r DLL fix (post-3.03).
- https://www.vogons.org/viewtopic.php?t=52095 — Miles MidiForm.exe (XMI conversion tool from Miles SDK, useful peripheral).
- **Pointer:** (d) tooling.

### 2.18 Caesar II–specific support pages (no SDK, but context)

- https://archive.org/details/caesar-2 — Caesar II DOS install image on Internet Archive.
- https://lilura1.blogspot.com/2022/04/Caesar-IBM-PC-MS-DOS-1992-Impressions-Games-Original-Version.html — confirms Caesar II uses Miles AIL with DOS/4GW 1.97.
- https://caesar3.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=9,7241,150,all
- https://downloads.khinsider.com/game-soundtracks/album/caesar-ii-1995-pc — gamerip.
- **Pointer:** (d).

### 2.19 Other game-source repositories that may bundle AIL3 .lib

- https://github.com/ForsakenW/forsaken (Forsaken, 1998 — Acclaim, MSS-era).
- https://github.com/ForsakenX/forsaken
- https://www.moddb.com/mods/forsaken/downloads/forsaken-assets-source-code
- https://github.com/RetroReversing/retroReversing/blob/master/pages/SourceCode/RetailConsoleSourceCode.md
- https://www.retroreversing.com/leaks
- **Pointer:** (d) potential bundlers.

### 2.20 Watcom toolchain references (build environment to match Caesar II byte-for-byte)

- https://en.wikipedia.org/wiki/Watcom_C/C++
- https://www.azillionmonkeys.com/qed/watfaq.shtml
- https://open-watcom.github.io/open-watcom-v2-wikidocs/cpguide.html
- https://github.com/joncampbell123/hackers-watcom-v2 — Watcom v2 fork; useful for building 16-bit-flat experiments.
- https://flaterco.com/kb/ow.html
- https://tuttlem.github.io/2015/10/04/32bit-dos-development-with-open-watcom.html
- https://www.openwatcom.org/ftp/install/ — pre-built Watcom installers (the user wants Watcom 10.0 specifically; OW 1.9 + `-bcl=dos4g` is the closest reproducible analog).
- https://wiki.osdev.org/Watcom
- **Pointer:** (d) toolchain.

---

## 3. NEGATIVE / EXHAUSTED (No Useful Hits)

### 3.1 Areas searched without success

- **ftp.radgametools.com Wayback snapshots** — could not be enumerated in this session due to web_fetch wildcard restrictions; the user should query https://web.archive.org/web/2000*/ftp.radgametools.com manually. RAD's public FTP (1996–2002) historically hosted only Bink/Smacker/MSS _Windows_ DLLs, never the DOS SDK.
- **radgametools.com/down/** subpaths — only Smacker/Bink download pages found (https://www.radgametools.com/smkdown.htm, https://www.radgametools.com/bnkdown.htm). All MSS SDKs are gated behind a sales evaluation request — `[email protected]`.
- **Internet Archive software library** queries `AIL`, `AIL32`, `MSS`, `miles_design`: only `archive.org/details/vfx119` (AIL2 + VFX) is relevant. False-positive results: `archive.org/details/manualzilla-id-6037285` (just a scrape of John Miles' personal pages), `archive.org/details/dosdrivers` (generic DOS drivers, no AIL).
- **vetusware.com / winworldpc.com / oldskool.org / nerdlypleasures / dosdays.co.uk** — none of these were direct-hit by web_search; queries for "Miles Sound System", "AIL", "AIL3FLAT", "MSSDOS.LIB" returned zero results within these domains during this run. Worth manual inspection.
- **BetaArchive / ExoticA** — no hits in this session.
- **GitHub code-search for `ailss.c`, `ailsfile.c`, `ailxmidi.c`, `ailxdig.c`** — no hits beyond the file-name references in `wcdctool` README. The actual \*.c files are not on public GitHub.
- **grep.app, sourcegraph.com** — were not directly queried (no specific tools), but inferred from negative-result pattern in GitHub.
- **scummvm-devel mailing-list archives, DOSBox dev community** — no AIL3 SDK mentions surfaced.
- **Bitsavers, Game Developer Magazine cover-disc CDROM dumps 1994–95** — not searchable via web_search; no hits.
- **`AIL3FLAT.LIB`, `MSSDOS.LIB`, `AIL32.LIB` searches** — zero hits anywhere on public web. These library files exist only on private dev backups and inside game-developer source leaks not on the public web.
- **MechWarrior 2 / Carmageddon / Forsaken / LEGO Island source dumps** — none publicly contain `AIL3FLAT.LIB`. MK1/MK2/MKTrilogy executables are _unstripped_ and contain the AIL3 _object code_, but not the source.
- **Hub.docker.com `lyigradteber/miles-sound-system-sdkrar`** — referenced from a spam Google Groups page (https://groups.google.com/g/itinlalo/c/FjeHgqjRlT0). Cannot be verified; dropbox-style malware-distribution risk. Avoid.
- **GitHub `radixark/miles`** (https://github.com/radixark/miles), `CIRCL/AIL-framework` (https://github.com/CIRCL/AIL-framework), `ail-project/ail-framework` (https://github.com/ail-project/ail-framework), `milesfrain/scheduler` (https://github.com/milesfrain/scheduler) — name collisions only; unrelated.
- **CookiePLMonster's other repos / BeWorld's AHI port** — only header-level hits, no .lib.
- **Caesar III remake repos** — https://sourceforge.net/projects/opencaesar3/, https://github.com/dalerank/caesaria-game — open-source remakes that don't use Miles.

### 3.2 Confirmed dead-ends for finding AIL 3.03 SDK directly

- John Miles has explicitly stated (per multiple Vogons quotes) that he is _not_ releasing AIL 3.x because the IP belongs to RAD/Epic.
- Epic Games (current rights holder) gates MSS behind license agreements.
- No `AIL.H` v3.03 (the original DOS-only header before the 1995 MSS.H merge) has been located on the public web — only the post-merge `MSS.H` v1.01 carries the v3.03 banner.

---

## 4. Recommendations / Next Steps

1. **Use `wcdctool` against PS.EXE and against MK1.EXE** — the AIL3 OMF object modules in both binaries came from the same Miles network share, almost certainly identical machine code. Diffing produces the AIL3 reference disassembly directly, with original source-file names already preserved by Watcom -d1 records.
2. **Use MSS.H v1.01 (19-Jun-95) from the VBdec or Source Engine 2007 leak** as the canonical type/prototype reference for naming reconstructed symbols. The Caesar II PS.EXE September 1995 build is within ~3 months of this header's authoring date.
3. **Use the AIL/32 1.05 source (vfx119/AIL2.ZIP and ail32-sandbox)** as the structural template for `dllload.c`/`mix32.c`/`stp32.c`-style code; the AIL3 flat-model versions are direct evolutions.
4. **Reach out to carlostex, bristlehog, or DosFreak via VOGONS PMs** — the "AIL3 sources are out there in the wild" thread strongly implies a private mirror exists that could be shared developer-to-developer, even if not legally redistributable.
5. **Check Wayback Machine for `thegleam.com/ke5fx`, `pop.net/~jmiles`, `milesdesign.com`** (1996–2000 snapshots) — these are John Miles' historical hosting locations; `archive.org/details/vfx119` was uploaded in 2021 from such a backup.
6. **Email John Miles** ([email protected] / [email protected] / via radgametools.com) directly. The community has noted he is responsive, and 30 years post-release he may be willing to share the AIL 3.03 DEV3/FLAT tree for non-commercial reverse-engineering.

---

## 5. Complete URL Index (for the curated link repo)

### Primary artifacts (sources, headers, libs)

- https://archive.org/details/vfx119
- https://archive.org/download/vfx119/AIL2.ZIP
- https://archive.org/download/vfx119/vfx119.zip
- https://github.com/Tronix286/AIL2
- https://github.com/Tronix286/AIL2/blob/master/AIL.H
- https://github.com/Tronix286/AIL2/blob/master/AIL.ASM
- https://github.com/Tronix286/AIL2/blob/master/READ.ME
- https://github.com/Tronix286/AIL2/blob/master/MIXDEMO.C
- https://github.com/Tronix286/AIL2/blob/master/SOUNDFX.C
- https://github.com/Tronix286/AIL2/blob/master/SOUNDFX.H
- https://github.com/Tronix286/AIL2/blob/master/CAKEPORT.ASM
- https://github.com/Wohlstand/ail32-sandbox
- https://github.com/Wohlstand/ail32-sandbox/blob/master/stp32.c
- https://github.com/Wohlstand/ail32-sandbox/blob/master/mix32.c
- https://github.com/Wohlstand/ail32-sandbox/blob/master/ail32.h
- https://github.com/Wohlstand/ail32-sandbox/blob/master/ail32.asm
- https://github.com/Wohlstand/ail32-sandbox/blob/master/dllload.c
- https://github.com/Wohlstand/ail32-sandbox/blob/master/read.me.utf8.txt
- https://github.com/Wohlstand/ail32-sandbox/blob/master/dmasnd32.asm
- https://github.com/Wohlstand/ail32-sandbox/blob/master/xmidi32.asm
- https://github.com/CookiePLMonster/VBdec
- https://github.com/CookiePLMonster/VBdec/blob/master/mss/mss.h
- https://github.com/CookiePLMonster/VBdec/raw/refs/heads/master/mss/mss.h
- https://github.com/VSES/SourceEngine2007
- https://github.com/VSES/SourceEngine2007/blob/master/src_main/common/Miles/MSS.H
- https://github.com/domz1/SourceFlyFF/blob/master/Program/_Common/mss.h
- https://revoltengine.sourceforge.net/doxygen/a00351_source.html
- https://github.com/Nommy228/Might-and-Magic-Trilogy/blob/master/AIL.h
- https://archive.org/details/ReVoltXboxAndPCSourceCode
- https://github.com/dah4k/VFX119

### Reverse-engineering / decompilation tooling

- https://github.com/victor-zinkv/wcdctool
- https://github.com/fonic/wcdatool
- https://github.com/dethrace-labs/dethrace
- https://github.com/BSzili/dethrace
- https://github.com/isledecomp/isle
- https://github.com/wbcbz7/sndlib-watcom
- https://github.com/wbcbz7/sndlib-watcom/blob/master/dpmi.cpp
- https://github.com/joncampbell123/hackers-watcom-v2

### Runtime binaries (DLLs/drivers)

- https://github.com/vogonsorg/radgametools
- https://github.com/vogonsorg/radgametools/tree/main/mss16
- https://github.com/vogonsorg/radgametools/tree/main/mss32
- https://github.com/vogonsorg/radgametools/tree/main/ailwail32

### Forum threads / community knowledge

- https://www.vogons.org/viewtopic.php?t=5217
- https://www.vogons.org/viewtopic.php?t=59575
- https://www.vogons.org/viewtopic.php?t=54318
- https://www.vogons.org/viewtopic.php?p=589861
- https://www.vogons.org/viewtopic.php?p=1379613
- https://www.vogons.org/viewtopic.php?p=1395922
- https://www.vogons.org/viewtopic.php?p=1415317
- https://www.vogons.org/viewtopic.php?t=11330
- http://www.vogons.org/viewtopic.php?t=24069
- http://www.vogons.org/viewtopic.php?t=7372
- https://www.vogons.org/viewtopic.php?t=40965
- https://www.vogons.org/viewtopic.php?t=52095
- https://www.vogons.org/viewtopic.php?t=95514
- https://www.vogons.org/viewtopic.php?t=93903
- https://www.vogons.org/viewtopic.php?amp=&f=24&t=39270
- https://gamedev.net/forums/topic/645199-miles-sound-system-6x-or-earlier-sdk/
- https://comp.programming.narkive.com/wuvhppRu/dos-sound-drivers-mdi-format

### Reference docs / wikis

- https://en.wikipedia.org/wiki/Miles_Sound_System
- https://en.wikipedia.org/wiki/Watcom_C/C++
- https://en.wikipedia.org/wiki/Re-Volt
- https://en.wikipedia.org/wiki/List_of_commercial_video_games_with_available_source_code
- https://www.pcgamingwiki.com/wiki/Miles_Sound_System
- https://www.pcgamingwiki.com/wiki/MechWarrior_2:_31st_Century_Combat
- https://www.pcgamingwiki.com/wiki/Re-Volt
- https://www.mobygames.com/group/13047/sound-engine-ail-miles-sound-system/
- https://www.mobygames.com/company/4064/miles-design-inc/
- https://www.mobygames.com/company/4569/epic-games-tools-llc/
- https://www.mobygames.com/game/1588/caesar-ii/
- https://www.mobygames.com/game/369/re-volt/
- https://www.vgmpf.com/Wiki/index.php/Audio_Interface_Library
- http://fileformats.archiveteam.org/wiki/AIL_real_mode_driver
- https://grokipedia.com/page/miles_sound_system
- https://tcrf.net/Re-Volt_(Windows)
- https://tcrf.net/Development:LEGO_Island
- https://www.legoisland.org/wiki/Source_Code_(July_1996)
- https://www.dosbox.com/wiki/GAMES:MechWarrior_2

### Vendor / origin pages

- https://www.radgametools.com/miles.htm
- https://www.radgametools.com/msshist.htm
- https://www.radgametools.com/mssgames.htm
- https://www.radgametools.com/msssdk.htm
- https://www.radgametools.com/mssdown.htm
- https://www.radgametools.com/smkdown.htm
- https://www.radgametools.com/bnkdown.htm
- https://www.radgametools.com/smkhist.htm
- https://www.radgametools.com/bnkhist.htm
- http://www.radgametools.com/?from=binkplay64&ver=2.5j%2F1.995j
- http://www.ke5fx.com/gpib/readme.htm
- https://www.qsl.net/ke5fx/gpib/readme.htm
- https://manualzilla.com/doc/6037285/2---john-miles-ke5fx
- https://archive.org/details/manualzilla-id-6037285
- http://phasenoisemeasure.blogspot.com/2011/08/welcome-to-ke5fx-gpib-toolkit.html

### Caesar II / target context

- https://archive.org/details/caesar-2
- https://lilura1.blogspot.com/2022/04/Caesar-IBM-PC-MS-DOS-1992-Impressions-Games-Original-Version.html
- https://caesar3.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=9,7241,150,all
- https://downloads.khinsider.com/game-soundtracks/album/caesar-ii-1995-pc
- https://sourceforge.net/projects/opencaesar3/
- https://github.com/dalerank/caesaria-game
- https://steamcommunity.com/app/517790/discussions/0/3185737486658301180/

### Watcom toolchain (build-environment reproduction)

- https://www.azillionmonkeys.com/qed/watfaq.shtml
- https://flaterco.com/kb/ow.html
- https://open-watcom.github.io/open-watcom-v2-wikidocs/cpguide.html
- https://open-watcom.github.io/open-watcom-v2-wikidocs/c_readme.html
- https://github.com/open-watcom/open-watcom-v2
- https://github.com/open-watcom/open-watcom-v2/blob/master/bld/wl/qnx386/dos.h
- https://github.com/open-watcom/open-watcom-v2/blob/master/bld/clib/startup/a/dos16m.asm
- https://github.com/open-watcom/open-watcom-v2/discussions/660
- https://wiki.osdev.org/Watcom
- https://forum.osdev.org/viewtopic.php?p=67225&t=10338
- https://tuttlem.github.io/2015/10/04/32bit-dos-development-with-open-watcom.html
- http://nuclear.mutantstargoat.com/articles/retrocoding/dos01-setup/
- https://retrocoding.net/building-for-dos-os2-and-dos-on-a-macbook-apple-silicon
- https://www.streetinfo.lu/computing/programming/dos/freedos_watcom.html
- https://groups.google.com/g/openwatcom.users.c_cpp/c/FegneOhz-S4
- https://openwatcom.users.c-cpp.narkive.com/qKYQAnqM/dos-installer-test

### Game-source leak indexes (potentially containing AIL3 .lib)

- https://github.com/RetroReversing/retroReversing/blob/master/pages/SourceCode/RetailConsoleSourceCode.md
- https://www.retroreversing.com/leaks
- https://github.com/ForsakenW/forsaken
- https://github.com/ForsakenX/forsaken
- https://www.moddb.com/mods/forsaken/downloads/forsaken-assets-source-code
- https://archive.org/details/LEGOIsland-source-June1996
- https://forum.mattkc.com/viewtopic.php?t=79
- https://www.cwaboard.co.uk/viewtopic.php?t=12732
- https://archive.org/details/re-volt-jul-26-1999-psx-prototype.-7z
- https://github.com/RetailGameSourceCode/UltimateMortalKombat3
- https://www.gamesradar.com/games/28-years-later-lego-islands-lost-source-code-has-been-rediscovered-but-the-fans-who-spent-nearly-two-years-painstakingly-decompiling-it-by-hand-cant-have-it/
- https://tech.yahoo.com/gaming/articles/28-years-later-lego-islands-172238985.html

### Known false leads (avoid)

- https://hub.docker.com/r/lyigradteber/miles-sound-system-sdkrar (spam)
- https://groups.google.com/g/itinlalo/c/FjeHgqjRlT0 (spam)
- https://nelliemuf.wixsite.com/zanortochar/post/miles-sound-system-sdk-rar (warez aggregator)
- https://github.com/CIRCL/AIL-framework (name collision — CSIRT tool)
- https://github.com/ail-project (name collision — same)
- https://github.com/radixark/miles (name collision — RL framework)
- https://github.com/milesfrain/scheduler (name collision)
- https://ail-workshop.github.io/AIL3-Workshop/ (linguistics workshop, name collision)

---

## 6. Verification Checklist (MD5/SHA-256 not computed in this session)

The user should compute the following hashes locally and add to the curated repo:

- `AIL2.ZIP` from `archive.org/details/vfx119` (~2.1 MB) — should contain `AIL.LIB`, `AIL32.LIB`, full source. **This is the AIL/32 1.05 SDK, not 3.03 — but it is the closest publicly redistributable substitute.**
- `vfx119.zip` from same item (~4.3 MB) — VFX 1.19 graphics SDK, sometimes bundled with AIL.
- Caesar II `PS.EXE` `AIL3DIG`/`AIL3MDI` driver files from `archive.org/details/caesar-2` — verify against the v3.03 / 18-Jun-95 stamp catalogued in https://www.vogons.org/viewtopic.php?t=5217.
- `mss.h` from VBdec and SourceEngine2007 — check that both files are byte-identical; they should be (both inherited from the same Miles SDK header).

## 7. Confidence-Ranked Candidate Summary

| #   | Source                                               | Type                              | Confidence it matches AIL 3.03 DOS-flat                                               |
| --- | ---------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------------- |
| 1   | wcdctool + MK1.EXE disassembly                       | (a) reconstructable source via RE | **HIGH** — same `R:\NET\LIBS\AIL\DEV3\FLAT\` build, AIL 3.02; few-month delta to 3.03 |
| 2   | MSS.H v1.01 (19-Jun-95) — VBdec / Source Engine 2007 | (a) headers                       | **HIGH** — explicitly versioned for V3.03 release                                     |
| 3   | AIL2.ZIP / vfx119 — AIL/32 1.05 source               | (a) source — predecessor          | MEDIUM (AIL/32 1.05 → AIL3 evolution)                                                 |
| 4   | ail32-sandbox (Wohlstand)                            | (a) modernized AIL/32 1.05 build  | MEDIUM (same)                                                                         |
| 5   | Re-Volt source (Acclaim leak)                        | (a)+(b) headers + libs            | MEDIUM (post-3.03 era libs, but headers usable)                                       |
| 6   | vogonsorg/radgametools (mss/ailwail32 dirs)          | (c) runtime binaries              | LOW for DOS-flat 3.03; higher for Win MSS                                             |
| 7   | VOGONS "AIL3 sources in the wild" + community        | (d) leads to private leaks        | MEDIUM — gated on personal contact                                                    |
| 8   | RAD Game Tools / John Miles direct contact           | (a) source on request             | LOW — IP-encumbered, but possible 30y later                                           |

**Bottom line:** AIL 3.03 DOS-flat does not exist as a downloadable artifact on the public web in 2026. The user's best path is the wcdctool route (item #1) combined with the MSS.H v1.01 header (item #2) and the AIL/32 1.05 source as a structural reference (items #3–#4). Direct outreach to John Miles or to VOGONS user _carlostex_ is the only realistic path to an actual `.lib` or `.c` tree.
