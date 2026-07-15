# Deep-research prompt: Miles Sound System / AIL 3.03 (DOS flat, 1994)

Self-contained prompt for a deep-research LLM harness. The harness will
NOT have access to this repo, so all identifying breadcrumbs are inlined
below.

---

```
Goal
----
Locate the original 1994-era "Miles Sound System" / "Audio Interface
Library" (AIL) version 3.03, DOS 32-bit flat-model variant, intended
to be linked against Watcom C/C++ 10.0 applications running under a
DOS extender (DOS/4GW Pro 1.97). I am reverse-engineering Caesar II
(Sierra/Impressions, Sept 1995, PS.EXE) and need this library to
reproduce the audio code path byte-identically.

Deliverable, in priority order
-------------------------------
1. Original Miles Sound System SDK 3.03 (or closest-revision) source
   tree — *.c / *.h / *.asm.
2. Pre-built static library + headers for Watcom 32-bit flat:
   typically named AIL32.LIB / AIL3FLAT.LIB / MSSDOS.LIB plus
   MSS.H / AIL.H, and the *.DIG / *.MDI driver binaries.
3. Pre-built library only, with reverse-engineered headers.
4. Manuals, programmer's guides, README, and any redistributable
   archives that contain just the runtime drivers.

Identifying breadcrumbs from the target binary
----------------------------------------------
- Version string in data segment: literal ASCII "3.03" with the
  Miles banner, followed by sub-module names "AIL3DIG" and "AIL3MDI"
  (digital + MIDI dispatchers loaded as DLLs).
- Sub-module prefixes seen in linker symbols: AILSS, AILSFILE,
  AILXMIDI, AILXDIG. The first four characters "AIL3" or "AILS"
  appear in dozens of public symbols.
- Original build path baked into Watcom -d1 debug records:
  `R:\NET\LIBS\AIL\DEV3\FLAT\` — i.e. the SDK lived on a network
  drive at Impressions Games, in a "DEV3\FLAT" subtree (DEV3 = AIL
  v3 development kit, FLAT = 32-bit flat-model build).
- Source filenames preserved in debug info:
    dllload.c, aildebug.c, ail.c, ailss.c, ailsfile.c,
    ailxmidi.c, ailxdig.c
  These are the canonical file names of the Miles 3.x DOS SDK and
  are a strong fingerprint when grepping archives.
- Driver filenames referenced in data: SB16.DIG, SBPRO.DIG,
  SBLASTER.DIG (Sound Blaster family) — implies the SDK shipped
  the standard ".DIG" digital-audio drivers and ".MDI" MIDI drivers.
- Object-module footprint: ~63 KB of code across 10 OMF modules
  in the final LE executable.
- Producer: Miles Design, Inc. (founded by John Miles, Tucson AZ;
  later absorbed into RAD Game Tools, ~1995).

Era / version constraints
-------------------------
- AIL 3.03 specifically. Not 2.x (real-mode), not 3.04+ (post-1995),
  not the later "MSS" rebranding. Closest acceptable substitutes:
  AIL 3.02 or 3.03a if 3.03 cannot be found.
- DOS 32-bit flat / DOS/4GW target. Reject 16-bit real-mode builds
  and Win32/Mac variants — they are different object files.
- Build date should fall in the window roughly Q1 1994 – Q3 1995.

Where to search (suggested, not exhaustive)
-------------------------------------------
- archive.org: search for "Miles Sound System", "AIL", "AIL32",
  "AIL3FLAT", "miles_design", and check the Wayback Machine for
  ftp.radgametools.com (RAD's old download server) snapshots
  1996-2002.
- RAD Game Tools' own historical pages: radgametools.com,
  radgametools.com/down/, and any "legacy" / "miles" subpaths.
- Old DOS game development archives: vetusware.com, winworldpc.com,
  oldskool.org, nerdlypleasures, dosdays.co.uk.
- BetaArchive, ExoticA, archive.org/details/CD-ROM_..., and
  "abandonware SDK" collections.
- GitHub / GitLab / SourceForge: search for filenames listed above
  ("aildebug.c", "ailsfile.c", "ailxmidi.c") — leaked source trees
  from later games occasionally include these. Try also code-search
  on grep.app and sourcegraph.com.
- Vogons forum (vogons.org), DOSBox community, scummvm-devel
  archives — developers there have catalogued AIL revisions and
  sometimes mirror SDK snapshots.
- Bitsavers, CD-ROM dumps of Game Developer Magazine cover discs
  from 1994-95, which occasionally bundled Miles eval kits.
- Internet Archive's "Software Library: MS-DOS" with queries like
  AIL, AIL32, MSS, miles_design.

Verification you should perform on any candidate
-------------------------------------------------
- Confirm version string "AIL ... 3.03" inside the .lib or driver
  binaries.
- Confirm the OMF .lib contains modules whose source-file records
  match dllload, aildebug, ail, ailss, ailsfile, ailxmidi, ailxdig.
- Confirm flat-model 32-bit (not 16-bit segmented). Easiest test:
  COFF/OMF with USE32 segments and __watcall / register-convention
  symbols.
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
  - One-line provenance note (who hosted it, what year it was
    uploaded, whether it is the official redistributable, a leak,
    a fan mirror, a cover-disc rip, etc.)
  - Whether the link points to (a) the actual SDK/lib, (b) docs
    only, (c) a related binary that ships the runtime, or (d) a
    secondary clue / discussion / index page
  - Confidence: HIGH / MEDIUM / LOW that this is exactly Miles AIL
    3.03 DOS flat — explain briefly.

Structure the report as three sections:
  1. CONFIRMED HITS — artifacts you are fairly sure match.
  2. PROMISING LEADS — pages that mention AIL 3.03 / DOS-flat AIL
     but do not directly host the bits.
  3. NEGATIVE / EXHAUSTED — places you searched that had nothing,
     so the downstream researcher does not duplicate effort.

Do not stop at the first hit. Return at least 5 candidate sources
ranked by confidence, and exhaustively list every URL touched
during the investigation (sections 1, 2, AND 3 must each have URLs
where applicable). Treat this as a link-collection task: a
half-relevant Wayback snapshot is worth recording.
```
