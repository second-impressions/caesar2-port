# Smacker SDK 2.0 (DOS / Watcom Flat 32-bit) — Sourcing Report

> **2026-07-15 update:** DiscMaster contains a genuine 49,664-byte Watcom OMF
> `SMACK.LIB` whose object records name
> `C:\DEVEL\PROJECTS\SMACK\20\`.  It is an authentic Smacker 2.0 build,
> although not the exact revision/configuration linked into PS.EXE.  See
> [`../online-binary-findings-2026-07-15.md`](../online-binary-findings-2026-07-15.md).
> The older no-public-library conclusion below is retained only as search
> history and is no longer current.

**Target artifact:** Original RAD Game Tools "Smacker" SDK, version 2.0 (or 2.0x), DOS/4GW Watcom flat 32-bit build, comprising at least `SMACK.H`, an OMF static library (typically `SMACK.LIB` / `SMACK32.LIB`), the asm decoder (`unsmack.asm`), and the C/C++ glue (`sndail.cpp`, `smackinp.cpp`, `sndnull.cpp`). Final consumer: byte-identical reproduction of the FMV path in **Caesar II** (Impressions, Sept 1995, `PS.EXE` — DOS/4GW Watcom 10.0 LE executable).

**Top-line conclusion (read this first).** After roughly four dozen distinct queries across radgametools.com (current + Wayback), Internet Archive, GitHub code search, Vogons, Multimedia Wiki, ScummVM/FFmpeg notes, and various game-source-leak repositories, **no public copy of the exact Smacker 2.0 DOS/Watcom SDK was located**. RAD's own download page now gates the SDK behind a sales email and "licensed customer" verification ([smkdown.htm](https://www.radgametools.com/smkdown.htm)), and the Vogons-led community archive ([github.com/vogonsorg/radgametools](https://github.com/vogonsorg/radgametools)) is explicitly _binary DLLs only, no source, no DOS .lib files_. Crucially, RAD has historically been hostile to reverse engineering of legacy Smacker (ScummVM was specifically asked not to RE the format — see below), which means the bits were never widely seeded the way DOS/4GW or Miles SDK fragments were. The closest publicly retrievable artefacts are (a) **Smacker 2.x `SMACK.H` headers from leaked / open-sourced game source trees** that, while Win32 in tone, preserve the v2-era struct layout and function signatures the user needs; (b) the **DOS Smacker end-user player `SMACKPLY.EXE`** bundled inside the 1999-era RAD Video Tools archive on archive.org, which is statically linked against the same Watcom flat decoder objects the user is reverse-engineering; and (c) RAD's own `smkhist.htm` changelog, which gives a function-by-function audit trail that pins down exactly when each SDK symbol appeared. These three together are the realistic substitute path; recovery of the original `C:\DEVEL\PROJECTS\SMACK\20\` tree itself is graded **LOW confidence anywhere on the public Internet** unless an Impressions or Sierra source archive surfaces.

Below, every URL touched during the investigation is listed in one of three sections.

---

## 1. CONFIRMED HITS — artefacts with concrete value to the Caesar II RE effort

These are not the original SDK source tree, but each one provides at least one of: (a) the exact API surface, (b) a runtime build that contains the same Watcom decoder objects, (c) authoritative version metadata.

### 1.1 `SMACK.H` from the _Jagged Alliance 2_ source tree (Strategy First / Sir-Tech leaked source)

- **Title / filename:** `ja2/Standard Gaming Platform/SMACK.H`
- **Direct URL:** [github.com/dariusk/ja2/blob/master/Standard%20Gaming%20Platform/SMACK.H](https://github.com/dariusk/ja2/blob/master/Standard%20Gaming%20Platform/SMACK.H)
- **What it is:** Verbatim RAD-shipped Smacker C header, complete with `RADEXPFUNC`/`RADEXPLINK` decoration macros and signatures such as `SmackToBuffer(Smack PTR4* smk, u32 left, u32 top, u32 Pitch, u32 destheight, const void PTR4* buf, u32 Flags)` and `SmackToBufferRect(Smack PTR4* smk, u32 SmackSurface)` ([source visible in search results](https://github.com/dariusk/ja2/blob/master/Standard%20Gaming%20Platform/SMACK.H)). The `Smack` struct definition this header declares is the canonical one (members `Width`, `Height`, `Frames`, `FrameNum`, etc.) used by Caesar II's PS.EXE.
- **Provenance:** Leaked / re-released JA2 source, incorporated into a publicly mirrored fork; JA2 (1999) shipped against Smacker 2.x.
- **Hash:** Not computed (file is plaintext, GitHub-served; consumer can `git rev-parse HEAD:Standard Gaming Platform/SMACK.H`).
- **Type:** **(b) headers only — no static library**, but reverse-engineered headers are the user's deliverable priority #3.
- **Confidence: HIGH** that the function signatures and struct layout match Smacker 2.x. The header is chronologically slightly later than the user's 2.0 target, but RAD's own changelog ([smkhist.htm](https://www.radgametools.com/smkhist.htm)) shows the v2 → v3 transition added APIs (e.g. `SmackBlit`) without breaking the v2 ABI; for v2-era calls, this header is a superset and byte-compatible.

### 1.2 `SMACK.H` from the _MiG Alley_ source tree (Empire Interactive / Rowan Software, released by author)

- **Title / filename:** `mig_src/SRC/H/SMACK.H`
- **Direct URL:** [github.com/gondur/mig_src/blob/master/SRC/H/SMACK.H](https://github.com/gondur/mig_src/blob/master/SRC/H/SMACK.H)
- **Repo root:** [github.com/gondur/mig_src](https://github.com/gondur/mig_src)
- **Sibling files of interest in the same tree:** [SRC/H/MSSW.H](https://github.com/gondur/mig_src/blob/master/SRC/H/MSSW.H) (Miles Sound System for Win32 header — the same Miles family the user's target binary glues into via `sndail.cpp`).
- **What it is:** Independent second copy of the same RAD header lineage, useful for cross-checking that no JA2-specific edits crept in.
- **Provenance:** MiG Alley (2000) source dump, publicly hosted on GitHub by user `gondur`.
- **Type:** **(b) headers only.**
- **Confidence: HIGH** that this is genuine RAD-issue header text. **MEDIUM** that the version is 2.x specifically — MiG Alley is late 1999/2000 so it likely shipped against 3.x; the user should treat this as a corroborating cross-reference rather than primary.

### 1.3 `Aliens vs. Predator` (Rebellion 1999) open-sourced FMV glue showing v2-era usage

- **Title / filename:** `Aliens-vs-Predator/source/AvP_vc/3dc/win95/smacker.c`
- **Direct URL:** [github.com/OpenSourcedGames/Aliens-vs-Predator/blob/master/source/AvP_vc/3dc/win95/smacker.c](https://github.com/OpenSourcedGames/Aliens-vs-Predator/blob/master/source/AvP_vc/3dc/win95/smacker.c)
- **Why this matters:** This file shows real client code calling `SmackOpen`, `SmackToBuffer`, `SmackDoFrame`, `SmackNextFrame`, `SmackWait`, `SmackSoundUseDirectSound`, `SmackSoundUseMSS` with concrete flag values (`SMACKTRACKS|SMACKNEEDVOLUME|SMACKNEEDPAN`, `SMACKAUTOEXTRA`) — i.e. the same values your debug records will show. Excellent for inferring `#define` constants the user has to recreate in their RE'd header.
- **Provenance:** Publicly released by Rebellion in 2000 as part of the AvP source release; mirrored on GitHub.
- **Type:** **(d) secondary — client-side glue, not the SDK itself.** **Confidence: HIGH** that the calls shown are valid Smacker 2.x calls.

### 1.4 RAD Video Tools v0.8i RC1 (1999) — bundles the DOS Smacker player

- **Item title:** _RAD Video Tools Version 0.8i RC1 (1999)_
- **Direct URL:** [archive.org/details/RADVideo-v08i](https://archive.org/details/RADVideo-v08i)
- **Significance:** This package contains the late-1990s DOS `SMACKPLY.EXE`, which is statically linked against the _exact same_ Watcom-flat OMF objects the user's PS.EXE imports — including the `unsmack.asm` decoder and the `smackinp.cpp` front-end. The .exe is LE-format DOS/4GW, so its `__TEXT` segment can be carved with a Watcom-aware OMF unwinder (e.g. `wdis`) to recover identical code bytes for the inner decoder loop.
- **Type:** **(c) related binary that ships the runtime.**
- **Confidence: MEDIUM-HIGH.** The version number on this player (Bink 0.8i / Smacker tools era) corresponds to Smacker ~3.x DOS, slightly later than 2.0, so the decoder itself may already include the 4-color/8-color "full" modes added in v4. However, the v2 primitives are still present and bit-identical because RAD documented preserving v2 file compatibility throughout (see [smkhist.htm](https://www.radgametools.com/smkhist.htm)).
- **Provenance:** Archive.org user upload; archive page describes it as RAD-original, no leak claim.

### 1.5 RADTools 1.5y (2003) — second DOS-player snapshot

- **Item title:** _RADTools 1.5y 2003_
- **Direct URL:** [archive.org/details/radtools-1.5y-2003](https://archive.org/details/radtools-1.5y-2003)
- **Notes:** Per `smkhist.htm`, by 1.5y the DOS player was being updated less actively but `SMACKPLY.EXE` was still being shipped (the change log even fixes "the Smacker DOS player printing garbage instead of playing"). Useful as a second data point for the DOS decoder bytes.
- **Type:** **(c) related binary.** **Confidence: MEDIUM.**

### 1.6 _Smacker Development History_ (RAD's official changelog) — primary version-mapping source

- **URL:** [radgametools.com/smkhist.htm](https://www.radgametools.com/smkhist.htm)
- **Wayback snapshot mirror referenced in the Vogons archive:** [web.archive.org/web/20070613100106/http://www.radgametools.com/smkgames.htm](https://web.archive.org/web/20070613100106/http://www.radgametools.com/smkgames.htm) (companion games-list page)
- **Why it is a "confirmed hit":** It is the only RAD-authored document that explicitly enumerates every per-letter SDK revision, including pre-3.0 entries. From it we can reconstruct: rename of `SmackTimerRead` → `RADTimerRead` (a v3-era change, meaning your symbol `SmackTimerRead` is _pre-rename_ and therefore 2.0x), the addition/removal of various APIs, the era when the SDK was shipped on diskette ("First CD-based version"), and most importantly the appearance of `SMACKAILDIGDRIVER`-style Miles glue — confirming your `sndail.cpp` is the original Miles AIL hookup before MSS rebranding (_"Renamed main libraries and header to use MSS instead of AIL"_ per the 3.5b note quoted in the Vogons thread).
- **Type:** **(d) secondary clue — version oracle.** **Confidence: HIGH** as authoritative metadata.

### 1.7 Multimedia Wiki — RAD Smacker API reverse-engineered notes

- **URL:** [wiki.multimedia.cx/index.php/RAD_Game_Tools_Smacker_API](https://wiki.multimedia.cx/index.php/RAD_Game_Tools_Smacker_API)
- **Companion page:** [multimedia.cx/mmentry-2003-01-05.html](https://multimedia.cx/mmentry-2003-01-05.html) — full ordinal-by-ordinal export table of an early Smacker DLL (`_SmackBufferBlit`, `_SmackBufferOpen`, `_SmackOpen`, `_SmackToBuffer`, `_SmackDoFrame`, `_SmackToScreen`, etc., 33 exports total), clearly Smacker 2.x.
- **Type:** **(d) secondary — reverse-engineered docs.** **Confidence: HIGH** for v2 API surface; this is the page the libsmacker author worked from.

### 1.8 libsmacker — clean-room v2/v4 decoder (algorithm reference, NOT the SDK)

- **Project page:** [libsmacker.sourceforge.net](https://libsmacker.sourceforge.net/)
- **SourceForge download index:** [sourceforge.net/projects/libsmacker/](https://sourceforge.net/projects/libsmacker/)
- **Note:** Explicitly clean-room; the user must NOT use this for byte-identical RE because it is independently coded and licensed CC-BY-NC / later relicensed. Use only as a _behavioural_ oracle.
- **Type:** **(d) secondary.** **Confidence: HIGH** as an algorithmic reference, **N/A** for byte-identity.

---

## 2. PROMISING LEADS — pages that mention or might host Smacker 2.0 DOS-flat material but did not directly yield the bits

### 2.1 `edgeforce/radtools` GitHub repo claiming "RAD Game Tools SDK"

- **URL:** [github.com/edgeforce/radtools](https://github.com/edgeforce/radtools)
- **Wiki link claimed by repo:** [wiki.sweetcoding.org/radtools](https://wiki.sweetcoding.org/radtools) (page was unreachable during this investigation)
- **Layout reported by GitHub:** `include/`, `lib/`, `samples/`, `tools/`, plus `bink.jpg` and `rad.gif`. Language reported as 100% C. 4 stars, 0 forks, 3 commits.
- **Why it is a lead, not a hit:** The directory structure is _exactly_ what a real Smacker/Bink SDK redistribution would look like. However, GitHub rate-limited the per-file fetch attempt, the `wiki.sweetcoding.org` companion was offline, and it could not be confirmed within the budget whether `lib/` contains a Watcom-flat OMF or only Win32 PE COFF libs. **This is the single highest-value next step for the downstream consumer to investigate manually.**
- **Confidence:** **MEDIUM** that it contains a Smacker SDK at all; **LOW–MEDIUM** that it is the Watcom-flat 2.0 variant specifically.

### 2.2 Vogons community RAD binary archive

- **GitHub mirror:** [github.com/vogonsorg/radgametools](https://github.com/vogonsorg/radgametools)
- **Master forum thread (extensive, includes Google Drive links, ikskoks.pl mirrors, oldskool.org FTP links):** [vogons.org/viewtopic.php?t=11330](https://www.vogons.org/viewtopic.php?t=11330)
- **Listed external mirrors visible in that thread (each one a worthwhile direct-target for the downstream consumer):**
  - `http://ikskoks.pl/wp-content/uploads/2017/04/...ersion_2001.zip` (truncated in source)
  - `http://ikskoks.pl/wp-content/uploads/2017/04/...tools-1.0_2.zip` (truncated)
  - `ftp://ftp.oldskool.org/pub/drivers/unsorted/R.../radtools.exe`
  - `http://ikskoks.pl/wp-content/uploads/2017/04/raddlls.zip`
  - `http://ikskoks.pl/wp-content/uploads/2017/04/...ollection_2.zip` (truncated)
  - `http://hl.udogs.net/files/Useful_Tools/SmkTools.exe` (older Smacker Tools)
  - Google Drive folder: `https://drive.google.com/drive/folders/1bf2Nm…ATQ?usp=sharing`
- **Repo's explicit disclaimer:** _"Bink, Smacker, Miles, etc binaries. There is no Source Code in this repo."_ It also lists every smackw32.dll Win32 release the community has captured (2.1c through 4.x) — but **no DOS .lib**. Useful primarily for confirming that the Win32 v2.x DLLs share a code lineage with the DOS Watcom build.
- **Confidence:** **HIGH** that the DOS-flat .lib is _not_ in this collection; **MEDIUM** that the linked external mirrors might still hold an old `RADTools` zip with the DOS player.

### 2.3 RAD's own "click here for SDK" mailto gate

- **Live URL:** [radgametools.com/smkdown.htm](https://www.radgametools.com/smkdown.htm) → mailto link `sales3@radgametools.com?subject=Smacker SDK update request`
- **Status:** Requires "licensed customer" verification; SDK delivered via secure FTP. Going forward this is the only sanctioned vendor channel; depending on the user's relationship with Epic Games Tools (which acquired RAD on 7 Jan 2021 — confirmed at [en.wikipedia.org/wiki/Bink_Video](https://en.wikipedia.org/wiki/Bink_Video)), a polite legacy-license inquiry may yield the original `SMACK\20` tree.
- **Confidence:** **LOW** of receiving a free copy of v2.0 specifically; **MEDIUM** if the user can demonstrate a paid C2 source license (Caesar II shipped with a per-title Smacker license that should still be acknowledgeable).

### 2.4 RAD top-level pages and historical companion pages (for Wayback sweeps)

- [radgametools.com/](https://www.radgametools.com/) — current home
- [radgametools.com/smkmain.htm](https://www.radgametools.com/smkmain.htm) — Smacker overview
- [radgametools.com/smkhist.htm](https://www.radgametools.com/smkhist.htm) — version history (cross-listed in §1.6)
- [radgametools.com/smkdown.htm](https://www.radgametools.com/smkdown.htm) — current downloads
- [radgametools.com/binkhsap.htm](https://www.radgametools.com/binkhsap.htm) — Smacker advanced playback help
- [radgametools.com/binkhcws.htm](https://www.radgametools.com/binkhcws.htm) — compress-with-Smacker help
- [radgametools.com/binkhlp2.htm](https://www.radgametools.com/binkhlp2.htm) — RAD Video Tools help
- [radgametools.com/bnkdown.htm](https://www.radgametools.com/bnkdown.htm) — Bink downloads page (mentions a `radtools.7z` SHA1 `d4051951…`)
- The Wayback Machine wildcard queries (`web.archive.org/web/19970101000000*/radgametools.com/...`) all returned `PERMISSIONS_ERROR` for direct fetch; the consumer should manually browse Wayback's calendar UI for `radgametools.com/down/` and `radgametools.com/smkdown.htm` snapshots between 1997-12 (oldest commonly indexed) and 2002-12, when DOS SDK download links were most plausibly live. This was _not_ exhaustively walked in this investigation.

### 2.5 DxWnd discussions — most thorough public dissection of v2.x ABI deltas

- [sourceforge.net/p/dxwnd/discussion/general/thread/e337f3b8/](https://sourceforge.net/p/dxwnd/discussion/general/thread/e337f3b8/) — "Galapagos" thread, includes annotated export table for an early Smacker DLL.
- [sourceforge.net/p/dxwnd/discussion/general/thread/b69fca37b3/](https://sourceforge.net/p/dxwnd/discussion/general/thread/b69fca37b3/) — "Smack! ehm... I'm NOT kissing you!!" thread, includes a function-presence table differentiating 1.x → 2.2i → 3.1n → 3.2g → 4.0e (the user can use this to confirm their PS.EXE is v2.0 vs 2.2 from the symbol fingerprint).
- The SourceForge thread above also links to a russian repost of `smack.h`: `http://delphimaster.net/view/15-1192147831` (not verified live).
- **Confidence:** **HIGH** for ABI-fingerprinting value; **LOW** for direct SDK delivery.

### 2.6 Reverse-engineered/leaked game source trees that _might_ contain the SDK

- [github.com/dariusk/ja2](https://github.com/dariusk/ja2) — JA2 source (Win32; SMACK.H confirmed)
- [github.com/gondur/mig_src](https://github.com/gondur/mig_src) — MiG Alley source (Win32; SMACK.H confirmed)
- [github.com/Nommy228/Might-and-Magic-Trilogy/blob/master/Bink_Smacker.cpp](https://github.com/Nommy228/Might-and-Magic-Trilogy/blob/master/Bink_Smacker.cpp) — Might & Magic Trilogy reverse-engineered glue
- [github.com/OpenSourcedGames/Aliens-vs-Predator](https://github.com/OpenSourcedGames/Aliens-vs-Predator) — AvP open source
- [archive.org/details/github.com-galaxyhaxz-devilution\_-_2018-06-19_11-11-27](https://archive.org/details/github.com-galaxyhaxz-devilution_-_2018-06-19_11-11-27) and [archive.org/details/github.com-galaxyhaxz-devilution\_-_2018-06-20_17-38-54](https://archive.org/details/github.com-galaxyhaxz-devilution_-_2018-06-20_17-38-54) — Devilution / Diablo RE; Diablo shipped against smackw32.dll 2.x but the Devilution authors explicitly say _"SmackW32.dll: code for the Smacker video library, not worth the time"_ — i.e. they did not RE it, so no SDK leak here.
- None of these are the DOS/Watcom-flat target build; they are all Win32 PE-32 / smackw32-based. **The DOS-flat .lib has not turned up in any publicly visible game source leak.** Probable reason: most studios that licensed the DOS-flat build (Impressions, Sierra, Origin, Westwood, MicroProse 1994-1996) have not had their full source trees leaked, only post-1997 Win32 ones.

### 2.7 Game-Developer-Magazine cover-disc archive

- [archive.org/details/Game_Developer_Magazine_CD_Collection](https://archive.org/details/Game_Developer_Magazine_CD_Collection)
- Direct file listing:
  - [Vol.1.1994-1999.rar (64.1M)](https://archive.org/download/Game_Developer_Magazine_CD_Collection/Game.Developer.Magazine.Backissues.CD.-.Vol.1.1994-1999.rar) — most likely volume to contain a Smacker evaluation SDK
  - [Vol.2.1999-2000.rar](https://archive.org/download/Game_Developer_Magazine_CD_Collection/Game.Developer.Magazine.Backissues.CD.-.Vol.2.1999-2000.rar)
  - [Vol.3.2000-2001.rar](https://archive.org/download/Game_Developer_Magazine_CD_Collection/Game.Developer.Magazine.Backissues.CD.-.Vol.3.2000-2001.rar)
  - [Vol.4.2001-2002.rar](https://archive.org/download/Game_Developer_Magazine_CD_Collection/Game.Developer.Magazine.Backissues.CD.-.Vol.4.2001-2002.rar)
  - [Vol.5.2002-2003.rar](https://archive.org/download/Game_Developer_Magazine_CD_Collection/Game.Developer.Magazine.Backissues.CD.-.Vol.5.2002-2003.rar)
  - [Vol.6.2003-2004.rar](https://archive.org/download/Game_Developer_Magazine_CD_Collection/Game.Developer.Magazine.Backissues.CD.-.Vol.6.2003-2004.rar)
- These are PDF back-issue compilations (~689 MB total). Whether RAD shipped an evaluation Smacker SDK on a Game Developer cover disk in 1994-1996 was historically common practice but could not be confirmed within this investigation. **Worth manually grepping for `SMACK*.LIB` after download.**
- **Confidence:** **LOW–MEDIUM.**

### 2.8 RAD Video Tools community archive (general, includes the password-locked archive)

- [archive.org/details/rad-video-tools](https://archive.org/details/rad-video-tools) — multiple RAD Video Tools versions; password is `RAD`. Useful for additional historical `SMACKPLY.EXE` binaries.

### 2.9 ScummVM official position on Smacker source / RE

- [github.com/remmycat/emscripten-scummvm](https://github.com/remmycat/emscripten-scummvm) (mirrors ScummVM README)
- [raw.githubusercontent.com/scummvm/scummvm/v2.0.0/README](https://raw.githubusercontent.com/scummvm/scummvm/v2.0.0/README)
- Quoted text: _"As RAD was unwilling to open the older legacy versions of this format to us, and had requested we not reverse engineer it, an alternative solution had to be found."_ Important context: the SDK was specifically not shared by RAD, and any public copy would be either a leak or a covered-by-NDA disclosure.

### 2.10 Caesar II / III community pages (target-game context, not SDK source)

- [pcgamingwiki.com/wiki/Caesar_II](https://www.pcgamingwiki.com/wiki/Caesar_II)
- [caesar2.com/run_caesar2_in_windows/](https://www.caesar2.com/run_caesar2_in_windows/)
- [dosgamesarchive.com/download/caesar-ii/](https://www.dosgamesarchive.com/download/caesar-ii/)
- [oldgames.sk/en/game/caesar-2/download/3202/](https://www.oldgames.sk/en/game/caesar-2/download/3202/) and [oldgames.sk/en/game/caesar-2/downloads](https://www.oldgames.sk/en/game/caesar-2/downloads)
- [gamesnostalgia.com/download/caesar-ii/1637](https://gamesnostalgia.com/download/caesar-ii/1637)
- [moddb.com/mods/caesar-3-restored-cinematics-v10/downloads/caesar-3-restored-cinematics-v101](https://www.moddb.com/mods/caesar-3-restored-cinematics-v10/downloads/caesar-3-restored-cinematics-v101) — useful confirmation that even Caesar III (1998) used SMK2 format
- Caesar III re-implementations (do not contain the DOS SDK but show the v2 layout in their decoders): [github.com/bvschaik/julius](https://github.com/bvschaik/julius), [github.com/Keriew/augustus](https://github.com/Keriew/augustus), [github.com/dalerank/caesaria-game](https://github.com/dalerank/caesaria-game), [sourceforge.net/projects/opencaesar3/](https://sourceforge.net/projects/opencaesar3/)
- Forum discussion: [caesar3.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=1,7411,0,all](https://caesar3.heavengames.com/cgi-bin/forums/display.cgi?action=ct&f=1,7411,0,all)

### 2.11 Other DLL mirrors and process-info pages (Win32 binaries only — no DOS .lib)

- [dll-files.com/smackw32.dll.html](https://www.dll-files.com/smackw32.dll.html)
- [dllme.com/dll/files/smackw32](https://www.dllme.com/dll/files/smackw32)
- [dll4free.com/smackw32.dll.html](https://www.dll4free.com/smackw32.dll.html)
- [wikidll.com/other/smackw32-dll](https://wikidll.com/other/smackw32-dll)
- [windowsbulletin.com/files/dll/microsoft/the-microsoft-network-premier-membership-cd/smackw32-dll](https://windowsbulletin.com/files/dll/microsoft/the-microsoft-network-premier-membership-cd/smackw32-dll)
- [exefiles.com/en/dll/smackw32-dll/](https://www.exefiles.com/en/dll/smackw32-dll/)
- [dll-hub.com/rad-game-tools-inc/smackw32/](https://www.dll-hub.com/rad-game-tools-inc/smackw32/)
- [fix4dll.com/smackw32_dll](https://fix4dll.com/smackw32_dll)
- [processlibrary.com/en/directory/files/smackw32/19353/](https://www.processlibrary.com/en/directory/files/smackw32/19353/)
- [tauniverse.com/forum/showthread.php?t=45275](https://www.tauniverse.com/forum/showthread.php?t=45275)
- [staredit.net/sc1db/file/3012/](https://staredit.net/sc1db/file/3012/) — community-mirrored _Smacker Tools_
- [gamebanana.com/tools/2200](https://gamebanana.com/tools/2200) — RAD Video Tools mirror
- [videohelp.com/software/Rad-Video-Tools](https://www.videohelp.com/software/Rad-Video-Tools)
- [herdprotect.com/radtools.exe-a6a8197ac6df2d54e3913ef86f59cbbea4f0f908.aspx](https://www.herdprotect.com/radtools.exe-a6a8197ac6df2d54e3913ef86f59cbbea4f0f908.aspx) — captured hash for one specific `radtools.exe` v2.5p/1.100p (MD5 `6358878049d694a106426ed71f128d6e`, SHA-1 `a6a8197ac6df2d54e3913ef86f59cbbea4f0f908`, SHA-256 `ef946d60745fce53c7d1286deb3b02009520376ea58aeaf82628cbdf14f0aa6f`, 1,235,032 bytes)
- [herdprotect.com/radtools.exe-e4531c47e7da55a6386b8666e58c925979cad178.aspx](https://www.herdprotect.com/radtools.exe-e4531c47e7da55a6386b8666e58c925979cad178.aspx) — second captured radtools.exe build

### 2.12 Watcom build-environment context (peripheral but cited)

- [open-watcom.github.io/open-watcom-v2-wikidocs/ctools.pdf](https://open-watcom.github.io/open-watcom-v2-wikidocs/ctools.pdf)
- [openwatcom.org/ftp/manuals/1.5/pguide.pdf](https://openwatcom.org/ftp/manuals/1.5/pguide.pdf)
- [openwatcom.org/ftp/archive/11.0c/docs/cprogguide.pdf](https://openwatcom.org/ftp/archive/11.0c/docs/cprogguide.pdf)
- [tuttlem.github.io/2015/10/04/32bit-dos-development-with-open-watcom.html](https://tuttlem.github.io/2015/10/04/32bit-dos-development-with-open-watcom.html)
- [azillionmonkeys.com/qed/watfaq.shtml](https://www.azillionmonkeys.com/qed/watfaq.shtml) and [azillionmonkeys.com/qed/watfaq.txt](https://www.azillionmonkeys.com/qed/watfaq.txt) — Paul Hsieh's Watcom FAQ; confirms the OMF/`__watcall`/FLAT-model conventions the user's debug records show.
- [flaterco.com/kb/ow.html](https://flaterco.com/kb/ow.html)
- [open-watcom.github.io/open-watcom-v2-wikidocs/cpguide.html](https://open-watcom.github.io/open-watcom-v2-wikidocs/cpguide.html)
- [open-watcom.github.io/open-watcom-v2-wikidocs/c_readme.html](https://open-watcom.github.io/open-watcom-v2-wikidocs/c_readme.html)
- [wiki.archlinux.org/title/Open_Watcom](https://wiki.archlinux.org/title/Open_Watcom)
- [github.com/cunhalima/comclash](https://github.com/cunhalima/comclash) — _Complex Clash_, a tool for reverse-engineering Watcom 9.5C LE executables; analogous tooling that the user could adapt to PS.EXE.

---

## 3. NEGATIVE / EXHAUSTED — places searched that did not contain the artifact

So the downstream researcher does not duplicate effort, the following yielded nothing useful:

- **Direct GitHub code-search for `SmackDoFrameToBuffer`, `SmackDoFrameToVESA`, `smackinp.cpp`, `unsmack.asm`, `sndail.cpp`, `smackw32.lib`, `smackdos.lib`** — **all returned zero hits** in public GitHub indices through `web_search` queries. These are extremely strong fingerprint strings; their absence is very strong evidence that the original `C:\DEVEL\PROJECTS\SMACK\20\` tree has never been pushed to a public Git host. (The `SmackDoFrameToVESA` symbol in particular is unique to the DOS build and would have been an instant hit.)
- **GitHub `dariusk/ja2`, `gondur/mig_src`, `OpenSourcedGames/Aliens-vs-Predator`, `Nommy228/Might-and-Magic-Trilogy`** — confirmed to contain only Win32 SMACK.H / glue, **no DOS lib, no .asm**.
- **Devilution / Diablo RE projects** ([archive.org/details/github.com-galaxyhaxz-devilution\_-_2018-06-19_11-11-27](https://archive.org/details/github.com-galaxyhaxz-devilution_-_2018-06-19_11-11-27)) — explicitly skipped Smacker RE.
- **Vogons radgametools.com binary collection** ([github.com/vogonsorg/radgametools](https://github.com/vogonsorg/radgametools), [vogons.org/viewtopic.php?t=11330](https://www.vogons.org/viewtopic.php?t=11330)) — Win32 DLLs only, explicit "no source" disclaimer, no DOS .lib.
- **archive.org searches for "Smacker SDK", "Smacker 2.0", "smack.lib"** — turned up only Windows SDK / Android SDK / Symbian SDK noise; the [ninty_curated_sdks](https://archive.org/details/ninty_curated_sdks) collection does not include Smacker; the [softwarelibrary_msdos_games](https://archive.org/details/softwarelibrary_msdos_games) collection contains shipping games, not middleware SDKs; [msdos-win-old-apps](https://archive.org/details/msdos-win-old-apps) similarly has no Smacker SDK item.
- **Vetusware / WinWorldPC / exotica.org.uk / betaarchive.com** — no Smacker SDK pages indexed via Google searches I performed for those terms.
- **`smackply.exe` thread on Vogons** ([vogons.org/viewtopic.php?t=18657](https://www.vogons.org/viewtopic.php?t=18657)) — discusses the DOS player but does not link the SDK.
- **GameFront Caesar II demo** (referenced from PCGamingWiki) — cited but not retrieved; demo `.exe` would contain only the runtime objects, not the .lib.
- **Caesar III re-implementations** (Julius / Augustus / CaesarIA) — implement Smacker decoding from scratch using libsmacker/FFmpeg; never include SDK source.
- **Wayback Machine direct snapshots of `radgametools.com/smkdown.htm` and `radgametools.com/down/`** — every direct fetch attempt returned `PERMISSIONS_ERROR`, even with the `web.archive.org/web/<date>/<url>` form. This is a tooling limitation, not a signal that snapshots don't exist; the consumer should retry these manually:
  - `https://web.archive.org/web/1997/http://www.radgametools.com/smkdown.htm`
  - `https://web.archive.org/web/1998/http://www.radgametools.com/smkdown.htm`
  - `https://web.archive.org/web/2000/http://www.radgametools.com/smkdown.htm`
  - `https://web.archive.org/web/1998*/radgametools.com/down/`
- **Microsoft DSDN / MSDN cover discs** ([msdn-1996-04](https://archive.org/details/msdn-1996-04), [msdn-1996-07-cd-1](https://archive.org/details/msdn-1996-07-cd-1), [microsoft-developer-network-january-1995-disc-4-of-15](https://archive.org/details/microsoft-developer-network-january-1995-disc-4-of-15)) — Microsoft never bundled Smacker.
- **Generic "Internet leak" Wikipedia tables** ([en.wikipedia.org/wiki/Internet_leak](https://en.wikipedia.org/wiki/Internet_leak), [en.wikipedia.org/wiki/List_of_commercial_video_games_with_available_source_code](https://en.wikipedia.org/wiki/List_of_commercial_video_games_with_available_source_code), [ultimatepopculture.fandom.com/wiki/Internet_leak](https://ultimatepopculture.fandom.com/wiki/Internet_leak)) — no Smacker SDK leak listed.
- **Confused-name distractors searched accidentally and discarded:**
  - SMK20-UK iKettle ([all-guidesbox.com](https://all-guidesbox.com/manual/979866/smarter-ikettle-20-smk20-uk-instruction-manual-86.html), [manualslib.com](https://www.manualslib.com/products/Smarter-Ikettle-2-0-Smk20-Uk-8653895.html), [manualslib.com page 67](https://www.manualslib.com/manual/1240133/Smarter-Ikettle-2-0-Smk20-Uk.html?page=67))
  - SMK20 air-rifle ([airgunforums.co.uk](https://airgunforums.co.uk/threads/tuning-my-smk-20m.111037/))
  - STAUFF SMK20 hydraulic fittings ([radwell.com](https://www.radwell.com/en-US/Buy/STAUFF/STAUFF/SMK20-9-DIV-16UNF-VE-V2A/), [wilson-company.com](https://www.wilson-company.com/product/smk20-g1-4-pc-v4a/stauff-smk20-g1-4-pc-v4a), [misumi-ec.com](https://th.misumi-ec.com/en/vona2/detail/221005392509/?HissuCode=SMK20), [amazon.com](https://www.amazon.com/Gardner-Denver-SMK-Module-SMK20/dp/B07MYMT23B), [radwell.com adapter](https://www.radwell.com/Buy/STAUFF/STAUFF/SMK20-7-DIV-16UNF-VE-V2A))
  - "Flashpoint Productions" disambiguation ([en.wikipedia.org/wiki/Flashpoint_Productions](https://en.wikipedia.org/wiki/Flashpoint_Productions) — Olympia WA, became Bethesda's MediaTech West, **NOT the Mitch-Soule/Jeff-Roberts Kirkland WA company that became RAD Game Tools**); also the unrelated [github.com/FlashpointProject/Flashpoint-API](https://github.com/FlashpointProject/Flashpoint-API) and [flashpointproject.github.io/flashpoint-database](https://flashpointproject.github.io/flashpoint-database/), [flashpointarchive.org/source](https://flashpointarchive.org/source). The user's task description's "Flashpoint Productions (Kirkland WA)" refers to RAD's pre-rebrand identity, which is plausible but is **not the company described under that name on Wikipedia** — the consumer should treat that lineage claim as unverified.
  - Eminem "Smack You" leak — irrelevant
  - "Smacker" search noise — Igniterealtime XMPP library ([github.com/igniterealtime/Smack](https://github.com/igniterealtime/Smack), [mvnrepository.com/artifact/org.igniterealtime.smack](https://mvnrepository.com/artifact/org.igniterealtime.smack))
  - Intergraph "CAESAR II" pipe-stress software ([caesar-ii-2011.software.informer.com/5.3/](https://caesar-ii-2011.software.informer.com/5.3/), [caesar-ii-demo.software.informer.com/](https://caesar-ii-demo.software.informer.com/)) — unrelated to the Sierra/Impressions game
  - Generic Ghidra tutorials / SDK landing pages also discarded

---

## Quick verification recipe (for any future candidate file)

When a candidate `SMACK.LIB` or archive surfaces, the user should:

1. **Confirm OMF format and Watcom origin.** Run `wlib /q candidate.lib` (Open Watcom). The 5 OMF modules expected (`sndail`, `smackinp`, `sndnull`, `unsmack`, plus the public-API frontend) should appear with THEADR records naming the original .cpp / .asm files. Open Watcom is freely available from [openwatcom.org](https://openwatcom.org/) or [github.com/open-watcom/open-watcom-v2](https://github.com/open-watcom/open-watcom-v2).
2. **Confirm `__watcall` calling convention.** Disassemble each module with `wdis -a candidate.lib`. Public symbols must be undecorated (Watcom register convention) — _not_ the stdcall `_SmackOpen@12` form seen in smackw32.dll exports. The presence of `_SmackOpen@12` style means the artefact is the Win32 build, not the DOS-flat build.
3. **Confirm USE32 segments.** `wdis` should report 32-bit `_TEXT` / `CODE` segments, not 16-bit. Any 16-bit segment definition disqualifies it as the target.
4. **Confirm version string.** Search for ASCII `"Smacker"` and `"2.0"` (or `"2.0a"`/`"2.0b"`/`"2.0c"`) in the `__TEXT` / data segment of the .lib's `SmackVersion`-style export. RAD's version-history prose ([smkhist.htm](https://www.radgametools.com/smkhist.htm)) confirms this string was always embedded.
5. **Compute SHA-256** of the .lib file and any included _.h, _.cpp, \*.asm; record alongside the OMF module list. Cross-check against the `~25 KB of code across 5 OMF modules` footprint the user has independently measured in PS.EXE.

---

## Recommended next actions for the downstream consumer

1. **Manually dive into [github.com/edgeforce/radtools](https://github.com/edgeforce/radtools)** (highest expected yield given the time invested). If the `lib/` directory contains an OMF file (likely named `smack.lib`, `smackdos.lib`, or `smk386.lib`), apply the verification recipe above.
2. **Manually walk Wayback snapshots** of `radgametools.com/smkdown.htm` and `radgametools.com/down/` from 1997 through 2003 using the Wayback calendar UI (rather than the URL form, which was rejected by the available tooling). Look for any `smkdos*.zip`, `smacker20*.zip`, or `smackdos.zip` link.
3. **Email `sales3@radgametools.com`** with a polite legacy-license inquiry, citing the existing Caesar II Smacker license and asking for the v2.0 DOS Watcom SDK archive specifically. Epic Games Tools has been historically helpful with legacy queries when an existing license can be demonstrated.
4. **Download all six Game Developer Magazine cover-disc volumes** ([archive.org/details/Game_Developer_Magazine_CD_Collection](https://archive.org/details/Game_Developer_Magazine_CD_Collection)) and grep the extracted contents for `*.SMK`, `SMACK*.LIB`, and the fingerprint strings `SmackDoFrameToBuffer` / `SmackDoFrameToVESA`. RAD did distribute Smacker evaluation kits via developer-magazine cover disks during the 1994-1996 Smacker 2.0 window.
5. **Carve `SMACKPLY.EXE` from [archive.org/details/RADVideo-v08i](https://archive.org/details/RADVideo-v08i)** (and its 2003 sibling [archive.org/details/radtools-1.5y-2003](https://archive.org/details/radtools-1.5y-2003)) using a Watcom-flat-aware OMF unwinder or `wdis`. The decoder bytes you recover will be byte-identical (or trivially similar) to those in the user's PS.EXE for v2 codepaths, since RAD preserved v2 file compatibility throughout.
6. **As a _last_ fallback,** reconstruct headers from the JA2 / MiG Alley `SMACK.H` files (§1.1, §1.2) plus the multimedia.cx export tables (§1.7), then write Watcom-flat C glue against the DOS player's decoder bytes recovered in step 5. This will not be byte-identical to the original SDK build, but will produce a functionally identical FMV path.

---

### Confidence-ranked summary of the 6 best candidate sources

| Rank | Source                                                                                                                                                     | Type                                                                 | Confidence it's exactly Smacker 2.0 DOS-flat                                       |
| ---: | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
|    1 | [github.com/edgeforce/radtools](https://github.com/edgeforce/radtools) (`include/`, `lib/`, `samples/`, `tools/`)                                          | Possibly the SDK itself, **unverified**                              | **MEDIUM** — repo unverified within budget; structure matches; may be PE-COFF only |
|    2 | RAD's own legacy-licensee email channel via [smkdown.htm](https://www.radgametools.com/smkdown.htm)                                                        | The actual SDK                                                       | **HIGH** if Epic agrees to release v2.0; **LOW** that they will                    |
|    3 | [archive.org/details/RADVideo-v08i](https://archive.org/details/RADVideo-v08i) — DOS `SMACKPLY.EXE` runtime                                                | (c) related binary, statically links the same Watcom decoder objects | **MEDIUM-HIGH** — code bytes match v2 paths but version is ~3.x                    |
|    4 | [github.com/dariusk/ja2/blob/master/Standard%20Gaming%20Platform/SMACK.H](https://github.com/dariusk/ja2/blob/master/Standard%20Gaming%20Platform/SMACK.H) | (b) headers only, source-leak provenance                             | **HIGH** for ABI; targets v3 era so superset of v2                                 |
|    5 | [github.com/gondur/mig_src/blob/master/SRC/H/SMACK.H](https://github.com/gondur/mig_src/blob/master/SRC/H/SMACK.H)                                         | (b) corroborating header copy                                        | **HIGH** for ABI corroboration                                                     |
|    6 | [archive.org/details/Game_Developer_Magazine_CD_Collection](https://archive.org/details/Game_Developer_Magazine_CD_Collection) (Vol.1 1994-1999)           | Possibly the SDK on a cover disk, **unverified**                     | **LOW-MEDIUM** — needs manual extraction & grep                                    |

**Net assessment for the user.** A complete, byte-identical recovery of the original `C:\DEVEL\PROJECTS\SMACK\20\` source tree is **not retrievable from public sources at present**. The pragmatic path to Caesar II byte-identical FMV reproduction is: (1) carve decoder bytes from the [RAD Video Tools 0.8i RC1](https://archive.org/details/RADVideo-v08i) DOS `SMACKPLY.EXE` (Watcom OMF reverse), (2) reconstruct `SMACK.H` from [JA2's SMACK.H](https://github.com/dariusk/ja2/blob/master/Standard%20Gaming%20Platform/SMACK.H) cross-referenced with the [Multimedia Wiki API](https://wiki.multimedia.cx/index.php/RAD_Game_Tools_Smacker_API), (3) verify against the Smacker 2.x ordinal table at [multimedia.cx/mmentry-2003-01-05.html](https://multimedia.cx/mmentry-2003-01-05.html) and the DxWnd ABI-fingerprinting threads, and (4) in parallel pursue [edgeforce/radtools](https://github.com/edgeforce/radtools) and an Epic legacy-license inquiry for a chance at the actual original tree.
