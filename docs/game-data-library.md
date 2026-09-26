# The game-data library

Every import, on native builds and in the browser, is merged into one
library of game data. The library is a plain directory tree sorted by what
the files are: files common to every release, one folder per language, both
soundtracks, and the best copy of each movie. A `.c2assets` file is that
tree, zipped. Exporting zips the library; importing a `.c2assets` merges it
like any other source. The same C code (`src/platform/sdl3/c2_library.c`)
does all of this in both builds; the native launcher and the web page only
acquire sources and display what the library reports.

This replaces the per-source caches, `asset-source.txt`, the browser's
remembered source and the version-1 `.c2assets` packs, and supersedes the
store and pack sections of `game-data-sources-plan.md` and work items 2 and
3 of `native-data-paths.md`.

## Principles

1. **One implementation.** Reading sources, sorting, merging, the summary,
   removal, export and pack import are C in `c2_import_core`, compiled into
   both targets. The browser shell and the native launcher contain no
   knowledge of the data's layout.
2. **The library is the pack.** The on-disk library and a `.c2assets`
   archive have the same tree. An extracted `.c2assets` is a valid library.
3. **Sorted by meaning, readable.** Any ZIP tool shows the speech of each
   language in its own folder.
4. **Keep the best, drop the rest.** A file is stored when it is the best
   available copy for its place. A better copy replaces it; an equal or
   worse one is ignored. The result does not depend on the order of
   imports: the corpus merged forwards and backwards gives byte-identical
   libraries.
5. **No provenance.** Nothing records where data came from: no paths, file
   names, disc labels or dates. What the library holds is described from
   its contents.
6. **All or nothing.** Remove clears the whole library; export writes the
   whole library.

## Layout

```text
<game-data root>/               native: <user data>/game-data; web: /persistent/game-data
  library/                      the portable part, identical to a .c2assets
    C2ASSETS                    format marker and quality notes
    common/                     files shared by every release
      *.256, *.WAV, *.DAT, ...  base files, as in the DOS HD/ tree
      PL8/                      graphics
    language/<tag>/             one release's text, speech and varying files
      C2.ENG  HELP.ENG
      RAW/*.RAW                 speech
      ...                       that release's versions of the varying files
    music/dos/                  CAESAR.OPL, CAESAR.AD, XMI/*.XMI (1995)
    music/windows/RAW/          CITYPRO0-2, FORUM0-2, BATTLE0, INTRO (1996)
    video/SMK/*.SMK             the best copy of each movie
  local/                        this machine only, never exported
    summary                     what the library holds, for the front ends
    staging/                    an import in progress
```

`<tag>` is the language `C2.ENG` is detected as (`c2_port_text_detect`, the
`X-C2-Detect` lines of `po/`): `en`, `de`, `fr`; `und` when unknown. Names
are the game's DOS names in upper case.

### C2ASSETS

```text
caesar2-assets 1
unit de dos speech later 1.0
unit en dos speech later 1.2
tree other video/SMK/BATTLOST.SMK
tree windows music/windows/RAW/CITYPRO0.RAW
```

- The first line is the format marker. A reader refuses a higher version
  by name ("written by a newer version"); a change to the layout or to the
  sorting tables bumps it, and the new reader migrates older libraries.
- `unit` lines list the language folders a reader may use, with what their
  rank is made of (below). A folder without a line is ignored.
- `tree` lines note files that did not come from a DOS tree (`windows`,
  or `other` for the Mac discs). Everything unlisted is DOS.
- Lines are sorted, so a library's marker does not depend on import order.

These are quality facts, not provenance: nothing says which disc a file
came from.

## Sources

`c2_import_stage` makes any source readable as a directory tree. Folders
are read in place; everything else is extracted into `local/staging`, only
files with a game extension (`.ENG .PL8 .RAW .SMK .XMI .WAV .256 .DAT .GD8
.OPL .AD`) and the `C2ASSETS` marker.

| Source | Read by |
|---|---|
| installation folder, any file inside it, or a folder above it | in place |
| GOG installation | its `game.gog`, the complete original CD |
| `.iso`, `.bin` (MODE1 or MODE2, CUE optional), `.cue` | `c2_iso.c`, `c2_cue.c` |
| `.zip` of an installation, or wrapping an image | `c2_zip.c`, streamed |
| CD-ROM drive (`/dev/sr0`, `D:`) | `c2_cdrom_fs.c` |
| Macintosh CD, Toast image, or the disc in a drive | `c2_iso.c`'s HFS reader |
| `.c2assets`, or a library folder | merged as a library |
| folder of `.SMK` files only | movies |

The HFS reader handles an Apple partition map or a bare HFS volume: the
master directory block, the catalog B-tree's leaf records and each file's
data fork. `c2_iso_catalog_open` falls back to it when a source has no
ISO-9660 volume, so images, ZIP-wrapped images, BIN files and drives all
read Mac discs. Resource forks and fragmented files are left out.

### Trees

A source is sorted by its trees:

- **DOS**: `HD/` beside `PL8/ RAW/ SMK/ XMI/`, or an installation with
  `C2.ENG` at the top and the media folders inside it.
- **Windows 95**: `C2WIN95/HD/` beside `C2WIN95/PL8 RAW SMK`, or the 1998
  pressing, which has only that tree, at the root. A Windows tree always
  has `C2_START.DAT`; a DOS tree never does.
- **Macintosh**: an install's `Data/HD/` (flat: base and media files
  together) and the disc's `Data/` with `256 PL8 RAW SMK XMI`. Its `C2.ENG`
  says "Macintosh Version"; its speech and music are AIFF.

From a hybrid disc only the DOS tree's files are used, plus the Windows
tree's recordings and movies. A Windows-only disc contributes everything,
ranked below DOS files, so the 1998 pressing plays on its own and is
replaced file by file when a DOS disc arrives.

### Why DOS graphics win

Measured on the 271 graphics files that differ between the two trees of
the same hybrid disc:

- **Fewer colours.** Every Windows 95 palette spends entries 1-9 and
  246-255 on Windows' fixed system colours (index 0 is magenta, the
  transparency key), so the art was re-quantized into what is left: 189
  of the 271 use fewer distinct colours (`CONGRAT.PL8` 186 to 105,
  `WARNING.PL8` 182 to 122, `EMPIRE.PL8` 203 to 178).
- **Water that no longer moves.** Both engines animate water by rotating
  palette ranges: DOS 0x40-0x47 in the city and 0x41-0x43 on the province
  map, Windows (`cycle_map_colours`) 0x40-0x47 and 0x97-0x99 on both. The
  Windows province palette keeps the water colours at 64-71 but its tiles
  use a static copy at 150-157, of which only 151-153 (0x97-0x99) rotate
  there. Nothing else is drawn with the rotated indices, so under the DOS
  engine the province water just stands still. In the city both rotate
  0x40-0x47 and the Windows art behaves as it did in Windows (coarser in
  `HOUSES1.PL8`, whose eight water shades became two).
- **A picture the Windows engine crops.** The start-of-game province
  selection draws `EMPIRE.PL8` into a window and shows only 620x380 of it
  at (11, 45) (`show_initreg_box`, the one `blit_window_area` call); the
  DOS version shows the whole picture with its marble border and the stone
  slabs. The Windows picture has no border, and in the part Windows never
  showed the artists noted the rectangle: "11,45 620x380". Under the DOS
  engine that note and the missing border are visible. `EMPIRE.PL8` is the
  only one of the 32 full-screen pictures drawn differently.

The Windows art still plays; it is the fallback for the 1998 disc, not a
choice.

## Sorting

The first matching row wins:

| File | Goes to |
|---|---|
| `C2.ENG`, `HELP.ENG` | `language/<tag>/` |
| `RAW/` `CITYPRO0-2`, `FORUM0-2`, `BATTLE0`, `INTRO` | `music/windows/RAW/` |
| any other `RAW/*.RAW` (speech) | `language/<tag>/RAW/` |
| `XMI/*.XMI`, `CAESAR.OPL`, `CAESAR.AD` | `music/dos/` |
| a file that varies between releases (below) | `language/<tag>/` |
| `*.SMK`, including the DOS intro kept among the base files | `video/SMK/` |
| `HISTORY.DAT` | not taken: the player's own file |
| anything else | `common/` |

### Files that vary between releases

Measured across the 13 PC releases (and confirmed by the feasibility
corpus): 94 files differ, 71 of them speech. The rest are not simply
localized; the German 1996 rerelease and the English 1.2 update change art,
samples, the region table and a movie:

```text
C2.ENG  HELP.ENG  A09.WAV  FORUM.WAV  MINING4.WAV  BACKGRND.PL8  E_PARTS2.PL8
REGIONS.DAT  SMK/RIOTERS.SMK  PL8/AF2BOWC  AF3BOWC  AFORUM  CA2SPRB  EG2SPRA
HN2SWDB  LIBRARY  PA2CAVA2  PANTHCOL  RO2SLGC  TCOLMDET  TUT_02A  TUT_04B  TUT_12B
```

Each goes into its release's language folder, so a language folder always
holds one release's version of all of them.

### The Mac discs

Only what the PC game can use is taken from a Mac disc:

- **Movies**: plain Smacker files. Four of the five scaled movies are the
  best encodes of all (500x240 at a higher bitrate than the Windows 95
  ones). `INTRONEW.SMK` is offered as `INTRO.SMK`; the DOS intro wins.
- **Music**: the Windows version's recordings, stored as AIFF under `XMI/`
  and named after the scores. The samples are the PC recordings, signed and
  a few bytes shorter; they are converted and renamed:

  | Mac | PC |
  |---|---|
  | `PROVINC1.XMI` `PROVINC2.XMI` `PROVINC3.XMI` | `CITYPRO1.RAW` `CITYPRO2.RAW` `CITYPRO0.RAW` |
  | `FORUM1.XMI` `FORUM2.XMI` `FORUM3.XMI` | `FORUM0.RAW` `FORUM1.RAW` `FORUM2.RAW` |
  | `BATTLE1.XMI` `INTRO.XMI` | `BATTLE0.RAW` `INTRO.RAW` |

- **Speech and text**: the AIFF speech, converted, and `C2.ENG`/`HELP.ENG`
  (for the language). Nothing else: a third of the Mac art differs from the
  PC's and the sound effects are `snd ` resources in a resource fork, so a
  Mac disc cannot stand in for a PC installation. Alone it is reported as
  not enough to play.

## Merging

- **A new file** is added. **An identical file** changes nothing.
- **`common/`, `music/dos/`**: a DOS copy beats a Mac copy beats a Windows
  95 copy; between equals, the one present stays.
- **`music/windows/`**: the recordings are the same everywhere; the longer
  file (the untrimmed PC one) wins.
- **Movies**: a scaled movie (`BATTLOST BATTWON LOSEGAME PROMOTE WINGAME`,
  played by `do_vga_smacked_anim`) takes the copy with the most pixels; at
  equal size, and for movies drawn 1:1, the DOS copy wins (the Windows
  re-encodes have fewer colours), then the Mac one; within one origin the
  larger file (higher bitrate).
- **Language folders** are replaced as a whole when the incoming one is not
  worse, compared in this order: with speech over without; DOS over
  Windows 95 over Mac; the higher version line (1.0 < 1.0A < 1.1 < 1.2);
  the later pressing, one that also carries the Windows 95 tree (the German
  original and its 1996 rerelease both say "Version 1.0").

A language folder is replaced by first dropping its line from `C2ASSETS`,
then rewriting the folder, then adding the line back: an interrupted
import leaves a folder no reader uses. Every other file is valid on its
own.

On the web, files are copied rather than renamed into place (`commit_file`):
Firefox keeps a file renamed in OPFS locked for the next page load.

## The runtime

`c2_library_layout` gives the host an ordered list of directories, each with
its base files and `PL8 RAW XMI SMK` media folders:

1. `language/<speech>/`, then English, then the other languages (a folder
   without some varying file falls back to another release's);
2. `common/`, `video/`, `music/dos/`, `music/windows/`.

Base files are looked up in every directory before media. Library names are
upper case and movies, scores and speech are only media there, so each
lookup is one exact open. The speech is the `--speech` wish, else the text
language, else English, else the first language with speech.

The layout reads no file, only lists directories: on the web it runs on the
page's main thread, and Firefox never answers an OPFS read made there. A
language folder counts when it has `C2.ENG`, and has speech when it has
`RAW/`. A library without `common/` is not playable.

`--asset-root DIR` reads a library, or a raw installation or disc tree, in
place (the smoke tests use this). In a raw tree the DOS tree comes first and
the Windows tree's recordings are found behind it.

## What the library reports

After every import, migration and removal, `local/summary`:

```text
c2-game-data 1
playable 1
language de speech dos Version 1.0
language en speech dos Version 1.2
language fr speech dos Version 1.0A
music dos
music windows
movies 13 5
bytes 125897480
```

The native launcher and the web page display this. `movies 13 5` counts the
scaled movies larger than the DOS 320x152 originals.

## Export, import, removal

- **Export** (`c2_library_export`, `--export-game-data FILE`, the
  launcher's *Export game data...*, the web page's *Export*) writes
  `library/` as a deflated ZIP with `C2ASSETS` first. The web page runs it
  like `--prepare-assets` and downloads the file from OPFS.
- **Import** of a `.c2assets` extracts it into staging (ZIP CRCs checked)
  and merges it by the rules above.
- **Remove** deletes `library/` and `local/`. Saves, `caesar2.inf`,
  screenshots and settings sit beside them and are never touched.

## Migration

- **Native**: on start, each old `game-data/<16 hex>/` cache with a
  `.complete` marker is imported and deleted (files are moved, not copied),
  and `asset-source.txt` is deleted; when it named a folder read in place,
  that folder is imported.
- **Browser**: when the old local-storage keys or caches exist, the page
  runs `--prepare-assets` once (with the remembered folder upload, if the
  source was one), which migrates the caches; the keys are removed.

## Measured

The Redump PC corpus (13 releases: Europe, OEM, the 1996 and 1997
rereleases, France, Germany and its two 1996 rereleases, Italy, USA 1995,
1996 and twice 1997), the 1998 US Windows-only disc, GOG's 1.0a
installation (its `game.gog` is the Europe 1.0A disc; it has no XMI), the
community German text patch (two files), and the English and French Mac
discs:

- every source imports, through its file, its extracted tree, the Redump
  ZIP, a loop device and a `scsi_debug` CD-ROM (`/dev/sr0`);
- all of them in one library: English 1.2, German 1996 rerelease, French
  1.0A, both soundtracks, five enhanced movies (four Mac, one Windows 95);
  125.9 MB, exported as a 75.3 MB `.c2assets`;
- forward and reverse import orders give byte-identical libraries; an
  exported library imports back byte-identical;
- the province smoke passes from each PC source and from the export; the
  campania speech smoke passes with each language's speech; the music-buffer
  smoke passes with the Windows soundtrack.

## Tests

- `tests/c2_library_test.c`: sorting of synthetic DOS, hybrid, Windows-only
  and Mac trees, AIFF conversion, the HFS reader on a synthetic partitioned
  image, rank rules, order independence, export round trip, format refusal,
  removal, migration and the runtime layout.
- `tests/c2_import_test.c`: the readers, staging, the mount table (one row
  per drive).
- `C2_TEST_GAME_DATA_SOURCES`: the province smoke from each listed source,
  imported into a fresh library.
- Browser: `tools/smoke-wasm.mjs ... export` checks the export;
  `C2_SMOKE_PROFILE` and `C2_SMOKE_PORT` keep one Firefox profile and
  origin across runs, so a build can be tested opening another build's
  storage (the migration).

A CD-ROM drive can be simulated without hardware:

```bash
sudo modprobe scsi_debug ptype=5 sector_size=2048 dev_size_mb=640
sudo modprobe sg
sudo sg_dd if=disc.iso of=/dev/sgN bs=2048   # N: the scsi_debug CD-ROM
caesar2 --game-data /dev/sr0 --prepare-assets --user-data-dir /tmp/t
```

## Not covered

- A Mac disc on its own: playing it would need the `snd ` resources of
  `C2 Sounds` converted to WAV and the differing art checked against the
  DOS renderer.
- Compressed disk images (`.dmg`, UDIF) and StuffIt archives (the Mac
  demo). Toast, ISO and raw images are read.
- GOG's installer `.exe`: install it (or unpack it with `innoextract`) and
  add the folder.
- Removing one language.
- Converting graphics to PNG. The engine draws 8-bit palette indices from
  the PL8 bytes in many places (`general_sprite`, the terrain blitters,
  the fonts) into buffers sized by a table, several exactly as large as
  the file, so PNG could only be storage behind `readfile()`, rebuilt into
  identical PL8 bytes on load. That would make the art readable and
  editable but fix none of the Windows art's problems, so PL8 stays the
  stored format.
