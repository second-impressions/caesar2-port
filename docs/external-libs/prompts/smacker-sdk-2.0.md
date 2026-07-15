# Deep-research prompt: Smacker SDK 2.0 (RAD Game Tools, DOS 32-bit, 1994)

Self-contained prompt for a deep-research LLM harness. The harness will
NOT have access to this repo, so all identifying breadcrumbs are inlined
below.

---

```
Goal
----
Locate the original 1994-era "Smacker" video-playback SDK from RAD
Game Tools / Flashpoint Productions, version 2.0 (or closest 2.0x
revision), DOS 32-bit protected-mode build for Watcom C/C++ 10.0
applications under DOS/4GW. I am reverse-engineering Caesar II
(Sierra/Impressions, Sept 1995, PS.EXE) and need this SDK to
reproduce its FMV/cutscene playback path byte-identically.

Deliverable, in priority order
-------------------------------
1. Original Smacker 2.0 SDK source tree — *.c / *.cpp / *.h / *.asm.
2. Pre-built static library + headers for Watcom 32-bit flat:
   typically SMACKW32.LIB / SMACK32.LIB / SMACK.LIB plus SMACK.H,
   and any *.SMK reference clips that shipped with the SDK.
3. Pre-built library only with reverse-engineered headers.
4. Programmer's manual, README, and the standalone "Smacker Tools"
   (compressor / player) from the same era, which often share
   format documentation.

Identifying breadcrumbs from the target binary
----------------------------------------------
- Original build path baked into Watcom -d1 debug records:
  `C:\DEVEL\PROJECTS\SMACK\20\` — i.e. the SDK lived on a local
  drive of an Impressions developer, in a "SMACK\20" subtree
  ("20" = version 2.0 directory naming convention).
- Source filenames preserved in debug info:
    sndail.cpp     -> Smacker→Miles AIL audio glue
    smackinp.cpp   -> Smacker input/decoder front-end
    sndnull.cpp    -> null audio backend
    unsmack.ASM    -> hand-written 386 decompressor inner loop
  These are .cpp files compiled by Watcom (which treats them as C
  with C++ comments). They are a strong fingerprint when grepping
  archives.
- Public symbols visible in the linker map:
    SmackDoFrameToBuffer
    SmackDoFrameToVESA
    SmackTimerSetup
    SmackTimerRead
    SmackAILDigDriver       (this name confirms Miles AIL audio
                             integration, not the later Bink/MSS)
- Object-module footprint: ~25 KB of code across 5 OMF modules in
  the final LE executable.
- Producer: RAD Game Tools, originally Flashpoint Productions
  (Kirkland WA, founded ~1988 by Mitch Soule + Jeff Roberts).
- Era: between the public release of Smacker 1.0 (1994) and the
  appearance of Bink Video (late 1999). The "20" path strongly
  suggests Smacker 2.0; closest acceptable substitutes are 2.01–
  2.05.
- Format constraint: must be the DOS 32-bit protected-mode (Watcom
  flat-model) build, NOT the 16-bit DOS, NOT the Win32/Win16, NOT
  the Mac variants — the OMF object files differ.

Where to search (suggested, not exhaustive)
-------------------------------------------
- RAD Game Tools own historical pages: radgametools.com,
  radgametools.com/smkmain.htm, radgametools.com/down/. Try
  Wayback Machine snapshots of these from 1996-2003. RAD kept
  legacy Smacker downloads online for many years.
- archive.org: search "Smacker SDK", "Smacker 2.0", "RAD Game
  Tools", "smackw32", and check Software Library: MS-DOS.
- vetusware.com, winworldpc.com, exotica.org.uk, betaarchive.com.
- Game Developer Magazine cover-disc CDs (1994-1996), which
  bundled Smacker evaluation versions.
- GitHub / GitLab / SourceForge / grep.app / sourcegraph.com:
  search for "SmackDoFrameToBuffer", "SmackDoFrameToVESA",
  "smackinp.cpp", "unsmack.asm", "sndail.cpp" — leaked source
  trees of mid-90s games sometimes include the Smacker SDK.
  Notable hits historically: leaked Westwood, Origin and Sierra
  source trees.
- Vogons (vogons.org), ScummVM/ResidualVM archives — both
  projects have analysed Smacker formats and may link historical
  SDK snapshots.
- libsmacker / FFmpeg historical mailing lists — they have
  documented Smacker v2 format and occasionally cite primary
  SDK archives.
- 3DRealms / Apogee / Sierra retro source releases on GitHub —
  several included the Smacker SDK in their build trees.

Verification you should perform on any candidate
-------------------------------------------------
- Confirm version string in the binary indicating "Smacker" 2.0x
  (often appears in the .lib's __TEXT segment or in any bundled
  player .exe).
- Confirm the OMF .lib contains modules whose source-file records
  match sndail, smackinp, sndnull, unsmack.
- Confirm flat 32-bit USE32 segments and Watcom register-convention
  __watcall symbols (not 16-bit segmented, not stack convention).
- Provide MD5/SHA-256 of any artifact you find.

Output format
-------------
EVERY URL you visit, cite, or even briefly skim must appear in the
final report. The downstream consumer will incorporate these into
a curated repo of links, so completeness matters more than brevity.
Include direct artifact URLs, index/listing pages, forum threads,
mailing-list posts, blog posts, Wayback snapshots, GitHub repos,
issue trackers, and any page that even hinted at the SDK — even if
it ultimately did not host the bits.

For every candidate source/library/document/clue, return:
  - Title / filename / page title
  - Exact version (string proof if available)
  - Direct, durable URL (archive.org item ID preferred over hot
    links) AND a Wayback Machine snapshot URL when the original
    is at risk of vanishing
  - File size + hash (MD5/SHA-256) if visible
  - One-line provenance note (RAD-official, leak, fan mirror,
    cover-disc rip, etc.)
  - Whether the link points to (a) the actual SDK/lib, (b) docs
    only, (c) a related binary that ships the runtime (e.g. a
    shipping game's SMACKER files), or (d) a secondary clue /
    discussion / index page
  - Confidence: HIGH / MEDIUM / LOW that this is exactly Smacker
    2.0 DOS flat — explain briefly.

Structure the report as three sections:
  1. CONFIRMED HITS — artifacts you are fairly sure match.
  2. PROMISING LEADS — pages that mention Smacker 2.0 / DOS-flat
     Smacker but do not directly host the bits.
  3. NEGATIVE / EXHAUSTED — places you searched that had nothing,
     so the downstream researcher does not duplicate effort.

Do not stop at the first hit. Return at least 5 candidate sources
ranked by confidence, and exhaustively list every URL touched
during the investigation (sections 1, 2, AND 3 must each have URLs
where applicable). Treat this as a link-collection task: a
half-relevant Wayback snapshot is worth recording.

Note: distinguish carefully between the Smacker *SDK* (libs +
headers, what I want) and the Smacker *end-user tools* (compressor
+ player .exes, secondary value).
```
