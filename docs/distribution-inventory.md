# Caesar II Cross-Distribution File Inventory

Inventory of **18 distributions** — 13 retail CDs (each carrying a DOS build, and the
later ones a Windows 95 build too), 2 DOS demos, the Mac retail `.toast`, and the Mac
demo — built by extracting every CD image (`bchunk` + `isoinfo`) and Mac disk image
(`hfsutils`) and diffing the file sets.  Goal: the rare / distribution-unique **game**
content worth preserving or remastering.  Bundled non-Caesar content (other Sierra
demos) is listed only so it can be **excluded**.

## Headline — the Mac soundtrack is different (and larger)

| release | `.XMI` (XMIDI) music |
|---|---|
| PC / DOS (all 13 CDs) | `BATEST2`, `CITYPROV`, `FORUM1`, `FORUM2`, `FORUM3` (5) |
| **Mac retail** | `BATTLE1`, `INTRO`, `PROVINC1`, `PROVINC2`, `PROVINC3`, `FORUM1`, `FORUM2`, `FORUM3` (8) |
| Windows 95 build (`C2WIN95/`) | same `.XMI` files as DOS (no separate Windows music) |

The Mac ships **five XMIDI tracks no PC release contains** — `BATTLE1` (a real battle theme
vs the PC's `BATEST2` 'test'), `INTRO` (intro music), and `PROVINC1/2/3` (three province
themes vs the PC's single `CITYPROV`); `PROVINC1` is also on the Mac demo.  Prime
lost-music / remaster candidates.

## Mac retail — game files unique to it (none on any PC CD)

```
  BATLFIX3.256
  BATTLE1.XMI
  BUILD1A.256
  CITYFIX2.256
  CITYFIX3.256
  FORUMBIT.256
  FORUMCIT.256
  ICON1.ICO
  INTRO.XMI
  INTRONEW.SMK
  INT_CITY.256
  INT_PROV.256
  PROVINC2.XMI
  PROVINC3.XMI
  SYSTEM.256
  TUT_00A.256
  TUT_00A.PL8
```
Music `BATTLE1/INTRO/PROVINC2/PROVINC3.XMI`; the alternate intro video `INTRONEW.SMK`;
ten `.256` palettes the PC bundles/embeds differently (`BATLFIX3, BUILD1A, CITYFIX2/3,
FORUMBIT, FORUMCIT, INT_CITY, INT_PROV, SYSTEM, TUT_00A`); `TUT_00A.PL8`; `ICON1.ICO`.
Shared with the **Mac demo** (so Mac-line, not PC): `PROVINC1.XMI`, `FONT0C2.PL8`,
`FORUMCIT.PL8`, `RAT_FRON.256`.

## Windows 95 build of Caesar II (5 rerelease CDs)

The USA 96-08/97-03/97-11, Europe 97-09 and Italy CDs add a real Windows 95 build of
Caesar II under **`C2WIN95/`** (`C2WIN95/HD/CAESAR2.EXE`).  It **reuses the identical PC
data files** — same `.PL8`, `.256`, `C2MODEL.DAT`, etc. as the DOS build (verified: same
basenames in `C2WIN95/HD`).  So the Windows version contributes **no unique game assets**;
it is just a Win32 binary over the same data.

> **Correction (an earlier draft of this doc was wrong):** the `0SONG*.DLL` "music DLLs",
> the `BAT_WIN1/BAT_LOS1/L2INTRO.SMK` videos, `40000.WAV`, `DEMO.DAT`, `ACL*.DAT`, the
> `VxD/FON/32SINST` files etc. are **NOT** Caesar II — they belong to the bundled `DEMO/`
> folder of other games (below).  The Windows Caesar II has no special music format; the
> `0SONG*.DLL` are Sierra's proprietary resource DLLs (custom PE resource types
> 1038/2318/2356, numbered ids) from the **Dr. Brain** demo.

## DOS demos

`MY_MEN1.PL8` is unique to the two DOS demos (demo soldier sprites; retail uses `MY_STDS*`).
Demo binaries `C2DEMO.EXE` / `C2DEMOAR.EXE`.

## Excluded — bundled NON-Caesar content

The rerelease CDs carry a big `DEMO/` tree of **other Sierra game demos** plus Microsoft
redistributables — **none of it Caesar II**, so it is excluded from the analysis above:

| `DEMO/` subdir | game |
|---|---|
| `BRAIN3` (`DRBRAIN.EXE`, `0SONG*.DLL`) | The Lost Mind of Dr. Brain |
| `L2DEMO`, `MOVIE/L2INTRO.SMK` | Lords of the Realm II |
| `ES2DEMO` | EarthSiege 2 |
| `RAMADEMO` | RAMA |
| `TPDEMO`, `TORDEMO` | Torin's Passage |
| `CSTORM` | Missionforce: CyberStorm |
| `UPINBALL` | 3-D Ultra Pinball |
| `AEDEMO`, `STDEMO`, `WINDY` | other Sierra promos |
| `DIRECTX`, `WIN32S`, `VFW`, `WING` | Microsoft runtimes (DirectX, Win32s, Video for Windows, WinG) |

Sierra packed those Windows demos' assets into numbered resource DLLs (`0SONG`=sound bank,
`1TOOLBAR`, `3LOGO`, `5INTRO`, …) loaded via the Win32 resource API — their engine's
convention, irrelevant to Caesar II.

## Method

CD images are MODE1/2352 single-track data discs (no Red Book audio on **any** of the 13).
Converted with `bchunk`, listed with `isoinfo -l`; the Mac `.toast` is a classic-HFS volume
read with `hfsutils` (`hmount`/`hls`).  Matrix keyed on uppercased basename across all 18
distributions.

## Is the Mac release higher quality? No

The Mac port reuses the PC assets verbatim, byte-for-byte in the cases checked:

| asset | Mac vs PC |
|---|---|
| `AARENA.PL8` sprite | **byte-identical** (same 8-bit, 182x132, same pixels) |
| `AFORUM.256` palette | byte-identical (256-colour, 6-bit VGA) |
| `BACKGRND.256` palette | same 768 B / 256-colour depth, different *values* (Mac display-gamma tweak) |
| `A01.RAW` speech | 200,746 vs 200,704 B — same 8-bit raw PCM (not 2x for 16-bit/22 kHz) |

Same 640x480-capped 8-bit graphics, same 256-colour palettes, same low-fi 8-bit
audio.  The Mac's value is **different content, not higher fidelity** -- the extra
XMIDI music, the `INTRONEW.SMK` intro, and gamma-adjusted palettes.
