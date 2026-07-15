# Library filenames to search for

Names you can plug into Google / archive.org / GitHub code-search /
Vogons-PMs / dev-disk grep. Derived from PS.EXE's OMF debug records,
the AIL/32 v1.05 makefile pattern, and RAD's published Win32 SDK naming.

## Miles AIL 3.03 — DOS flat / Watcom register-call

Per `data/out/symbols.json`, PS.EXE has **10 OMF modules** from the AIL3
SDK. The compiled deliverable was either a single bundled `.LIB` or a
loose `.OBJ` set (Miles' v1.05 SDK shipped loose `.OBJ`s, see
`data/external/ail/AIL2-extracted/REL105/RELEASE.105/A32WR.MAK`).

### Most likely .LIB filenames (priority order)

| Filename | Why | Confidence |
|----------|-----|------------|
| `AIL3.LIB` | Matches dir name `AIL\DEV3\FLAT\`; common Miles version-suffix pattern | HIGH |
| `AILFLAT.LIB` | Matches the `FLAT` subdir; differentiates from `AIL3DOS.LIB` (real-mode) and `AIL3WIN.LIB` (Win16) | HIGH |
| `AIL3FLAT.LIB` | Concatenated form | MEDIUM |
| `AIL.LIB` | Carries forward AIL v2.14's `AIL.OBJ` lineage | MEDIUM |
| `AIL32.LIB` | Carries forward AIL/32 v1.05's `AIL32.OBJ` lineage | MEDIUM |
| `AILDOS.LIB` | DOS-only marker | LOW |
| `MSS.LIB` / `MSSDOS.LIB` / `MSSFLAT.LIB` | Possible — Caesar II Sept 1995 is right at the AIL → MSS rename boundary (per RAD `smkhist.htm` the rename was MSS 3.5b, late 1995) | LOW–MEDIUM |

### Alternative: loose .OBJ files (also plausible, matches v1.05 pattern)

Same OMF naming convention as the v1.05 SDK we already have — module
names are just lowercase source filenames:

```
DLLLOAD.OBJ      AILDEBUG.OBJ    AIL.OBJ         AILSS.OBJ
AILSFILE.OBJ     AILXMIDI.OBJ    AILXDIG.OBJ     AILA.OBJ
AILSSA.OBJ       AILSSAB.OBJ?    or similar (10th module unidentified)
```

### Headers to also look for

| Filename | Why |
|----------|-----|
| `MSS.H` | Canonical post-Feb-15-1995 header. **We have v1.01 of 19-Jun-95** at `data/external/ail/mss-v1.01-VBdec.h` |
| `AIL.H` | Pre-MSS-rename name (last AIL.H was V3.02 per the MSS.H banner) |
| `AIL3.H` | Possible interim name |
| `AIL32.H` | Carries forward v1.05 (we have it at `REL105/RELEASE.105/AIL32.H`) |

### Driver runtime files (we already have these in `install/caesar2/`)

These are **loaded at runtime by `dllload.c`**, not linked. They are
DOS-flat `.DLL` files in OS/2 LX format renamed to `.DIG`/`.MDI`:

- `*.DIG` — digital-audio drivers (SB16.DIG, SBPRO.DIG, SBLASTER.DIG, ULTRA.DIG, SNDSCAPE.DIG, PROAUDIO.DIG, ADRV688.DIG, RAP10.DIG, JAMMER.DIG)
- `*.MDI` — MIDI drivers (ADLIB.MDI, ADLIBG.MDI, OPL3.MDI, MT32MPU.MDI, SBLASTER.MDI, SBPRO1.MDI, SBPRO2.MDI, SBAWE32.MDI, PAS.MDI, PASPLUS.MDI, ULTRA.MDI, SNDSCAPE.MDI, TANDY.MDI, PCSPKR.MDI, MPU401.MDI, NULL.MDI)
- `AIL3DIG`/`AIL3MDI` magic at offset 0 confirms AIL 3.x format

### Build path search hint

Anything from a network-share path containing **`R:\NET\LIBS\AIL\DEV3\FLAT\`**
is almost certainly a snapshot of Impressions Games' or Miles Design's
1994-95 dev tree. Grep tarballs / source dumps for that exact substring.

---

## Smacker SDK 2.0 — DOS Watcom flat

PS.EXE has **5 OMF modules** from the Smacker SDK. RAD's Win32 build
uses `SMACKW32.LIB` / `SMACK.H`, so DOS naming likely mirrors that.

### Most likely .LIB filenames (priority order)

| Filename | Why | Confidence |
|----------|-----|------------|
| `SMACK.LIB` | Bare product name; RAD's most generic naming | HIGH |
| `SMACK32.LIB` | 32-bit DOS marker; mirrors `SMACKW32.LIB` (Win32) | HIGH |
| `SMACKW.LIB` | Watcom flavour (parallel to RAD's `SMACKW32.LIB`) | MEDIUM–HIGH |
| `SMACK4G.LIB` | DOS/4GW flavour | MEDIUM |
| `SMACKDOS.LIB` | Explicit DOS marker | MEDIUM |
| `SMK.LIB` / `SMK32.LIB` | Short form | LOW–MEDIUM |
| `SMACKWAT.LIB` | Watcom long form | LOW |

### Alternative: loose .OBJ files

Module-name convention should match the source filenames exactly
(Watcom OMF lower-cases `.cpp` source names):

```
SMACK.OBJ       (the main decoder — no source filename in debug, so
                 was almost certainly shipped pre-compiled as .OBJ)
SNDAIL.OBJ      from sndail.cpp
SMACKINP.OBJ    from smackinp.cpp
SNDNULL.OBJ     from sndnull.cpp
UNSMACK.OBJ     from unsmack.ASM
```

### Headers to also look for

| Filename | Why |
|----------|-----|
| `SMACK.H` | Canonical (we have v3.2f at `data/external/smacker/SMACK-{ja2,mig}.h`) |
| `RAD.H` | RAD common header (we have it at `data/external/smacker/edgeforce-radtools/include/rad.h`) |
| `SMACK20.H` | Possible version-specific |

### Build path search hint

Anything from **`C:\DEVEL\PROJECTS\SMACK\20\`** is RAD's own 1994 dev
tree for Smacker 2.0. Grep tarballs for that exact substring.

The path's `SMACK\20\` directory is significant: it corresponds to
**v2.0**. RAD's directory layout convention (per Vogons reverse
engineering) was `\SMACK\<MAJOR><MINOR>\` so:
- `\SMACK\10\` would be v1.0
- `\SMACK\20\` is v2.0 ← what Caesar II linked against
- `\SMACK\21\` would be v2.1, etc.

If a candidate archive has `\SMACK\20\` paths anywhere in its files or
manifest, that's the **exact** SDK version we want.

---

## Combined search snippets

```bash
# Filename grep against any candidate archive
find . -iname "AIL3*.LIB" -o -iname "AILFLAT.LIB" -o -iname "AIL.LIB" \
       -o -iname "AIL32.LIB" -o -iname "AILDOS.LIB" -o -iname "MSSDOS.LIB" \
       -o -iname "MSSFLAT.LIB" -o -iname "MSS.LIB"

find . -iname "SMACK.LIB" -o -iname "SMACK32.LIB" -o -iname "SMACKW.LIB" \
       -o -iname "SMACK4G.LIB" -o -iname "SMACKDOS.LIB" -o -iname "SMK*.LIB"

# OMF module-name grep (works inside any .LIB or .OBJ)
strings candidate.lib | grep -iE "^(ail|ailss|ailxmidi|ailxdig|aildebug|dllload|aila|ailssa)\.(c|asm)$"
strings candidate.lib | grep -iE "^(smack|sndail|smackinp|sndnull|unsmack)\.(c|cpp|asm)$"

# Build-path grep against any tarball/zip stream
unzip -p candidate.zip | grep -aE "R:.NET.LIBS.AIL.DEV3.FLAT|C:.DEVEL.PROJECTS.SMACK.20"

# Google / DuckDuckGo — exact-phrase queries that should surface mirrors
"AIL3.LIB" OR "AILFLAT.LIB" OR "AIL3FLAT.LIB" filetype:zip
"SMACK.LIB" "watcom" OR "dos4g" OR "flat"
"\AIL\DEV3\FLAT" OR "DEV3\FLAT" -site:github.com  # source-leak fingerprint
"PROJECTS\SMACK\20" OR "SMACK\20\sndail"          # source-leak fingerprint

# Wayback Machine search — RAD's old SDK download page
https://web.archive.org/web/1997*/radgametools.com/smkdown.htm
https://web.archive.org/web/1998*/radgametools.com/down/

# GitHub code-search (run multiple variants, GitHub's UI rate-limits)
"AIL3.LIB" path:Makefile
"AILFLAT" path:wlink
"SMACK.LIB" path:Makefile
"link with smack" extension:txt
```

## What "found it" looks like

A genuine hit will satisfy **all** of:

1. **OMF magic** (`80 09 00` … THEADR record at file offset 0). Run:
   `head -c 16 candidate.lib | xxd`
2. **USE32 / FLAT segment names** — `_TEXT`, `_DATA`, `FLAT`, `CODE`,
   `DATA` (NOT 16-bit segmented `_TEXT16`). Run:
   `strings candidate.lib | head -20`
3. **`__watcall` register-convention public symbols** — undecorated
   names, NOT the stdcall `_SmackOpen@12` form. Run:
   `wlib -q candidate.lib | head` (Open Watcom)
4. **At least one of the canonical source filenames** in the THEADR
   records: `dllload.c, aildebug.c, ail.c, ailss.c, ailsfile.c,
   ailxmidi.c, ailxdig.c, aila.asm, ailssa.asm` for AIL — or
   `sndail.cpp, smackinp.cpp, sndnull.cpp, unsmack.asm` plus the main
   Smacker decoder for Smacker.
5. **Version stamp** — for AIL look for the literal string `"3.03"` in
   the data section of the .lib's `AIL_API_VERSION` member; for Smacker
   look for `"2.0"` near the `SMACKVERSION` define.
6. **Date around target** — File stamp Q4-94 to Q4-95 for AIL 3.03; Q1
   to Q4-94 for Smacker 2.0.

If a candidate satisfies (1)+(2)+(4), that's already extremely strong;
add (5) and you're done.
