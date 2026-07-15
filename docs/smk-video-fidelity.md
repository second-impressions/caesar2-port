# Caesar II Smacker video fidelity: DOS vs Windows vs Mac

The three Caesar II ports (DOS Watcom `PS.EXE`, Windows MSVC `CAESAR2.EXE`,
Mac CodeWarrior PPC) ship the **same set of RAD Smacker (`.SMK`) cinematics**,
but the Windows and Mac ports **re-encoded the marquee videos at higher
resolution and bitrate**.  All are 8-bit-palette SMK2.

## Headline

* **Resolution:** the five big cinematics — `BATTLOST`, `BATTWON`, `LOSEGAME`,
  `PROMOTE`, `WINGAME` — are **500×240 on Windows/Mac** vs **320×152 on DOS**
  (~2.5× the pixels).  The smaller event clips stay 320×152 on all three.
* **Bitrate:** the Windows/Mac cinematics also carry a much higher bitrate
  (e.g. `WINGAME` 962 → 1868 → 2380 kbps for DOS → Win → Mac).  A few 320×152
  clips were re-encoded hotter too (`CONGRAT` 799 → 1679 → 2058, `WARNING`
  934 → 1616, `BATTWON` 886 → 2047).
* **Mac ≥ Windows:** where a clip differs between Win and Mac, **Mac always has
  the higher bitrate** (`BATTLOST`, `CONGRAT`, `LOSEGAME`, `PROMOTE`,
  `WINGAME`).  For the other 8 clips the **Windows and Mac files are
  byte-identical** (`MAC=WIN`) — the ports shared the same re-encode.
* **Intro:** DOS `INTRO` is 640×480 but low-bitrate (206 kbps, 360 frames);
  Windows re-encoded `INTRO` at 640×480/1646 kbps (113 frames); Mac ships a
  **different** clip, `INTRONEW` (640×480, 1980 kbps, 80 frames, dated
  1996-08-18 — later than the rest).
* A handful of 320×152 clips are actually *smaller* on Win/Mac than DOS
  (`ARMYWARN` 867 → 530, `FIRE`/`RIOTERS`/`ROBBERY`/`SICK` ~equal-or-lower) —
  those were simply recompressed, not upgraded.
* Total set size: **DOS 18.0 MB · Windows 28.6 MB · Mac 32.3 MB** (14 files each).

## Full table

`res · frames · size · bitrate` per port.  Bitrate = size × fps / frames
(SMK frame rate field decoded: negative = 100000/(−rate) fps, so −8333 ≈ 12 fps).

| video | DOS | Windows | Mac | identical |
|---|---|---|---|---|
| **ARMYWARN.SMK** | 320×152 · 50f · 0.46MB · 867kbps | 320×152 · 50f · 0.28MB · 530kbps | 320×152 · 50f · 0.28MB · 530kbps | MAC=WIN |
| **BATTLOST.SMK** | 320×152 · 90f · 1.21MB · 1263kbps | 500×240 · 89f · 1.75MB · 1840kbps | 500×240 · 89f · 2.17MB · 2282kbps | — |
| **BATTWON.SMK** | 320×152 · 120f · 1.13MB · 886kbps | 500×240 · 120f · 2.62MB · 2047kbps | 500×240 · 120f · 2.62MB · 2047kbps | MAC=WIN |
| **CONGRAT.SMK** | 320×152 · 126f · 1.07MB · 799kbps | 320×152 · 121f · 2.17MB · 1679kbps | 320×152 · 121f · 2.66MB · 2058kbps | — |
| **FIRE.SMK** | 320×152 · 150f · 1.54MB · 965kbps | 320×152 · 150f · 1.49MB · 933kbps | 320×152 · 150f · 1.49MB · 933kbps | MAC=WIN |
| **INTRO.SMK** | 640×480 · 360f · 0.79MB · 206kbps | 640×480 · 113f · 1.98MB · 1646kbps | — | — |
| **INTRONEW.SMK** | — | — | 640×480 · 80f · 1.69MB · 1980kbps | — |
| **LOSEGAME.SMK** | 320×152 · 193f · 1.59MB · 771kbps | 500×240 · 192f · 2.86MB · 1399kbps | 500×240 · 192f · 3.10MB · 1513kbps | — |
| **MESSAGE.SMK** | 320×152 · 121f · 0.66MB · 604kbps | 320×152 · 121f · 0.88MB · 680kbps | 320×152 · 121f · 0.88MB · 680kbps | MAC=WIN |
| **PROMOTE.SMK** | 320×152 · 120f · 1.54MB · 1200kbps | 500×240 · 120f · 2.38MB · 1862kbps | 500×240 · 120f · 2.83MB · 2209kbps | — |
| **RIOTERS.SMK** | 320×152 · 120f · 1.05MB · 817kbps | 320×152 · 120f · 1.02MB · 797kbps | 320×152 · 120f · 1.02MB · 797kbps | MAC=WIN |
| **ROBBERY.SMK** | 320×152 · 120f · 0.72MB · 566kbps | 320×152 · 120f · 0.70MB · 547kbps | 320×152 · 120f · 0.70MB · 547kbps | MAC=WIN |
| **SICK.SMK** | 320×152 · 120f · 1.22MB · 951kbps | 320×152 · 120f · 1.05MB · 823kbps | 320×152 · 120f · 1.05MB · 823kbps | MAC=WIN |
| **WARNING.SMK** | 320×152 · 56f · 0.56MB · 934kbps | 320×152 · 56f · 0.97MB · 1616kbps | 320×152 · 56f · 0.97MB · 1616kbps | MAC=WIN |
| **WINGAME.SMK** | 320×152 · 437f · 4.49MB · 962kbps | 500×240 · 426f · 8.49MB · 1868kbps | 500×240 · 426f · 10.82MB · 2380kbps | — |

## Where the files come from

| port | source | video path |
|---|---|---|
| DOS | `CDs/Caesar II (Europe) (Rerelease) (1996-04-25)` (`c2 cd unpack`) | `SMK/*.SMK` + `HD/INTRO.SMK` |
| Windows | `CDs/Caesar II (Germany) (Rerelease) (1996-12-18)` (hybrid disc) | `C2WIN95/SMK/*.SMK` |
| Mac | `MAC/caesarii_1_0.zip` → `CaesarII_1_0.toast` (HFS; `hmount`/`hcopy -r`) | `Data/SMK/*.SMK` |

The Mac disc is an Apple-partitioned HFS Toast image; extract the HFS
partition (starts at block 37) and pull the SMK **data forks** with
`hfsutils` (`hcopy -r`).  The Mac files carry Finder type `C2mF` / creator
`C2mA`.

## Viewing them

The delinked Smacker player (`tools/smk-player/`) decodes any of these; it
picks the display mode from the video size (mode 13h for ≤320×200, VESA
640×480 for the 500×240 / 640×480 clips) and letterboxes with black bars.
Videos are staged under `/tmp/smktest/{dos,win,mac}/`:

```
playps.exe win\WINGAME.SMK vga     # 500x240 Windows cinematic, letterboxed in 640x480
playps.exe mac\WINGAME.SMK vga     # 500x240 Mac cinematic (highest bitrate)
playps.exe dos\WINGAME.SMK vga     # 320x152 DOS original
```
