# Online third-party binary findings (2026-07-15)

This supersedes the older sourcing reports wherever they say that no DOS
OMF library was found.  The original downloads and every distinct comparison
variant are archived under [`ThirdParty/`](../../ThirdParty/README.md) through
Git LFS.  They are proprietary historical binaries; archival inclusion does
not imply a redistribution license.

## Miles AIL 3.03b DOS-flat library

DiscMaster indexes several copies of a 131 KiB `AIL.LIB`.  The oldest
timestamped copy examined is:

- browse page: <https://discmaster.textfiles.com/view/21314/HiperCDROM10.iso/SONS/AIL.LIB>
- direct file: <https://discmaster.textfiles.com/file/21314/HiperCDROM10.iso/SONS/AIL.LIB>
- size: 134,144 bytes
- timestamp: 1995-06-30
- SHA-256: `17d0e4ad10c915062e67921a3c48a5095fdd364bd9cde2f7c45e4871d3a95c3c`
- embedded version: `3.03`
- embedded build path: `R:\NET\LIBS\AIL\DEV3\FLAT\`

The archive contains the same eight core modules as PS.EXE: `aildebug`,
`ailxdig`, `ailsfile`, `ailss`, `ailxmidi`, `ail`, `ailssa`, and `aila`.
The per-module public-function counts also agree exactly.  Comparing parsed
function bodies against the objects delinked from PS.EXE, with OMF relocation
bytes masked, gives 386/393 exact functions.  Three of the seven apparent
non-matches are end-marker spans whose overlapping bytes are identical.  The
four substantive differences are `_AILSSA_merge`, `AILXMIDI_start_`,
`_AIL_API_allocate_sequence_handle`, and `_AIL_API_end_sequence`.

The 1995-06-30 timestamp is the official 3.03a-to-3.03b release date.  The
changed digital mixer and XMIDI routines agree with the fixes described in
the official Miles history for 3.03a and 3.03b.  PS.EXE therefore uses base
3.03 (1995-06-18), while this downloadable library is the immediately
following 3.03b release.  It is an excellent binary/source-layout oracle but
is not a drop-in byte-exact replacement for the four changed routines.

DiscMaster also has three distinct 3.02 libraries.  They are older and less
useful than the 3.03b copy.

## RAD Smacker 2.0 DOS/Watcom library

A game/cover-disc tree contains a real RAD `SMACK.LIB`:

- browse page: <https://discmaster.textfiles.com/view/16093/GOLF_CHLNGR.iso/smack.lib>
- direct file: <https://discmaster.textfiles.com/file/16093/GOLF_CHLNGR.iso/smack.lib>
- size: 49,664 bytes
- timestamp: 1995-04-19
- SHA-256: `06dfc6afb6ee9afa44527281594e9813b6e745fd648eb9ca87b64b2d5decd5e7`
- OMF source prefix: `C:\DEVEL\PROJECTS\SMACK\20\`

The library contains ten members: `snddigp`, `dosext`, `svgablit`, `timer`,
`unsmack`, `rfile`, `palet`, `vesabank`, `smackinp`, and `svga`.  The source
prefix proves that this is the DOS/Watcom Smacker 2.0 tree sought by the old
report.  It is not the exact revision/configuration linked into PS.EXE:
`smackinp` has all 20 corresponding public functions, but only
`SMACKCOLORTRANS`, `SMACKGOTO`, and `SMACKSIMULATE` are byte-exact.  Several
member sizes also differ substantially.  Treat it as an authentic adjacent
Smacker 2.0 release binary, not as a replacement for the delinked PS objects.

DiscMaster has another 82 KiB `SMACK.LIB`, but its source prefix is the later
unversioned `D:\DEVEL\PROJECTS\SMACK\` tree and its member set differs more.

## DOS/4GW Professional 1.97 kit

Roman Garmash's historical DOS extender archive hosts the complete binder and
runtime pair:

- index/documentation: <https://rgmroman.narod.ru/develop.htm>
- archive: <https://rgmroman.narod.ru/4gwpro.zip>
- archive SHA-256: `5f075a5044d17ae9230eab424de7b88fbde8e590f767b957552541678ae0fc07`

Archive contents:

| File | Size | Timestamp |
|---|---:|---|
| `4GWBIND.EXE` | 45,551 | 1994-05-19 12:48 |
| `4GWPRO.EXE` | 242,724 | 1994-05-31 22:00 |

`4GWBIND.EXE` identifies itself as bind utility version 1.3 and accepts the
`-f`, `-q`, and `-v` binding options.  `4GWPRO.EXE` contains three chained BW
modules: `EXPLOAD.EXP` (24,960 bytes), `VMM.EXP` (60,496 bytes), and
`4GWPRO.EXP` (94,688 bytes).  Its runtime strings are exactly the PS.EXE
fingerprint: DOS/4GW Professional 1.97, built May 19 1994 14:44:26.

PS.EXE's bound prefix omits `EXPLOAD.EXP` and contains `VMM.EXP` and
`4GWPRO.EXP` at those exact sizes.  Binding the current unbound rebuild with
this kit established that PS used the default `4GWBIND` invocation with no
option: `-q` and `-f` each introduce a flag byte not present in PS, while
`-v` removes the VMM entirely.  The binder produces the same BW chain offsets
as PS.  The inner LE MZ begins 88 bytes earlier because the current WLINK
output has the already-documented 88-byte-shorter inner stub.

Before that inner stub, the default-bound candidate has only six differences
from PS, and every one is the same `0x7f` (archive) versus `0x77` (PS) byte.
One is in the outer MZ loader and five are in `4GWPRO.EXP`; VMM payload bytes
are exact after the binder rewrites its chain header.  Thus this is the
correct 1.97 kit family, but PS used a six-byte feature-mask microvariant not
present in this surviving archive.  Replacing the prefix splice will require
explaining or declaratively configuring those six masks (or, less cleanly,
applying the six known byte changes) plus reproducing the inner-MZ layout.

The Watcom C/C++ 10.0a CD in
`ReverseEngineering/watcom-compilers` contains the ordinary
`WATCOM/BIN/DOS4GW.EXE`, not this Professional binder kit.
