# Caesar II

**Caesar II (1995) on your computer today** — no DOSBox, no virtual machine,
no emulator. This is the original game's own code, recovered instruction by
instruction from the 1995 executable and made to build and run on Linux,
Windows, macOS and in a browser.

You bring your own copy of the game; this project never distributes it.

[![The city map](docs/screenshots/city.png)](docs/screenshots/city.png)

| | |
|---|---|
| [![The province map](docs/screenshots/province.png)](docs/screenshots/province.png) | [![The browser version](docs/screenshots/web.png)](docs/screenshots/web.png) |
| The province map | The same game in a browser |

## Play it in three steps

1. **Get the game.** Caesar II is sold on
  [GOG](https://www.gog.com/en/game/caesar_ii) for a few euros, DRM-free. An
  original CD, a disc image or an old installation works just as well.
2. **Get the port.** Either open
  [the browser version](https://second-impressions.github.io/caesar2-port/) —
  nothing to install — or download for your system from the
  [releases page](https://github.com/second-impressions/caesar2-port/releases):
  `.AppImage` or `.flatpak` for Linux, `.zip` for Windows (unzip anywhere, run
  `caesar2.exe`), `.dmg` for macOS.
3. **Point it at your copy and press Play.** A small launcher opens first; drop
  in your disc, image or game folder. It is imported once and remembered.

![The launcher](docs/screenshots/launcher.png)

## What you get

- **The real game.** The recovered engine, bugs and balance included — not a
  remake and not an emulator. Your original save files load.
- **A native program.** A resizable window, fullscreen, sharp integer scaling,
  screenshots, and no configuration files to edit.
- **In a browser too**, on the same code: your game data stays on your machine,
  in the browser's own storage.
- **English, German and French text**, chosen in the launcher; the game data
  supplies speech and pictures. Translations are ordinary gettext files under
  `po/` — see [docs/game-text.md](docs/game-text.md) to add one.
- **Both soundtracks.** The 1995 DOS music, played through a faithful
  reimplementation of the Sound Blaster's OPL3 chip and branching with your
  city's mood, or — from the CDs that carry it — the recorded 1996 Windows
  soundtrack.

## Where your copy can come from

Anything below works, natively or in the browser; the importer works out what
it is by looking inside:

- an **installed game folder** — GOG's, or an old DOS/Windows installation
  (pick any file inside it, e.g. `C2.ENG`),
- the original **CD-ROM** in a drive (the launcher lists the disc when one is
  inserted),
- a **disc image**: `.iso`, `.bin` with or without its `.cue`, also inside a
  `.zip`,
- a `.zip` of an installed folder,
- a `.c2assets` pack, which can carry several languages of speech in one file
  (`tools/c2-assets.py build`, see [docs/localization.md](docs/localization.md)).

Disc images and archives are imported once and reused on later starts; saves,
screenshots and settings live in the same place:

| | |
|---|---|
| Linux | `~/.local/share/second-impressions/caesar2` |
| Linux, Flatpak | `~/.var/app/io.github.second_impressions.caesar2/data/second-impressions/caesar2` |
| Windows | `%APPDATA%\second-impressions\caesar2` |
| macOS | `~/Library/Application Support/second-impressions/caesar2` |
| Browser | the browser's own storage for the page |

The original installer copied only part of the game to the hard disk, so an
installation folder without `XMI/` and `RAW/` has no music or speech. The
launcher and the web page say so when they see it; use the disc or an image of
it for everything.

## Keys and options

Everything in the game itself is the original's — hotkeys, mouse, menus; see
its manual. The port adds only these:

| Key | Action |
|---|---|
| **F11** | fullscreen |
| **F10** | integer / fractional scaling |
| **Ctrl+1** … **Ctrl+5** | window at exactly 1x … 5x |
| **Ctrl+0** | window at the largest multiple that fits the screen |
| Mouse wheel | zoom (the game's own `+`/`-`) |
| **Alt+1** … **Alt+8** | screenshot `shot1.png` … `shot8.png` into the user-data directory |

The game is 640x480. The window opens at the largest whole multiple that fits
your desktop and can be resized freely; integer scaling (the default) keeps
square pixels and letterboxes until the next multiple fits, fractional scaling
fills the window. Both are remembered.

Command line: `caesar2 [SOURCE]` starts with a given game-data source;
`--fullscreen`, `--fractional-scaling`, `--skip-launcher`, `--mouse-lock`
(confine the pointer to the game area), `--user-data-dir PATH`, `--language
TAG` (`en`, `de`, `fr`), `--music dos|windows`, `--asset-profile NAME` (speech
in a multi-profile pack), `--version`.

## Something wrong?

Open an [issue](https://github.com/second-impressions/caesar2-port/issues/new/choose);
the form asks for the few things that make a report usable.

## How this works, and the rest of the family

The engine is not reimplemented: it is the original, recovered as C source in
the byte-exact
[Caesar II reconstruction](https://github.com/second-impressions/caesar2-reconstruction),
whose build reproduces the 1995 executable byte for byte. This repository
continues that source onto SDL3: the DOS and Windows APIs the game called are
replaced one function at a time, the game's own logic is left alone, and every
deliberate difference is a named flag in `include/c2_target.h`.

The music, the movies and the file formats are handled by code written for
this port (an XMIDI sequencer and OPL3 synthesizer, Smacker video, the
importer), described under [docs/](docs/).

## Building

```bash
nix develop            # or install the dependencies below yourself
cmake --preset linux-release
cmake --build --preset linux-release
./build/port/linux-release/caesar2
```

Every library comes from the build host; CMake locates them, nothing is
fetched or bundled, and there are no git submodules, so a release tarball
builds as-is:

| Library | Needed for | Required |
|---|---|---|
| SDL3 ≥ 3.4 | window, input, audio, filesystem | yes |
| zlib | Deflate in the ZIP importer | yes |
| libbacktrace | source lines in crash reports (`-DPORT_WITH_LIBBACKTRACE=AUTO\|ON\|OFF`) | no |
| Unity | the C test suite (`BUILD_TESTING`) | tests only |

Two decoders that no distribution packages are carried as plain files with
their provenance in [third_party/README.md](third_party/README.md):
libsmacker (Smacker video) and Nuked OPL3 (the FM chip). Packagers should
declare them as bundled.

`cmake --install` lays out the binary, desktop entry, AppStream metainfo,
icon and licenses under the usual `GNUInstallDirs` (`DESTDIR` honoured):

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DPORT_WITH_LIBBACKTRACE=ON
cmake --build build
DESTDIR=/tmp/stage cmake --install build --prefix /usr
```

Other targets: the `windows-msvc-*` presets take their libraries from the
vcpkg manifest (`vcpkg.json`), and the web build is described in
[docs/webassembly.md](docs/webassembly.md). Every configuration, release
included, carries debug information. Published builds are versioned
`major.minor.patch-build-githash` (`caesar2 --version`).

## Developing

Recovered engine C stays in `src/`, CPU-only translations of recovered
assembly in `src/asm/`, backend-neutral shims in `src/platform/common/`, and
host backends in `src/platform/<backend>/`. Target differences go through
`include/c2_target.h` (`PORT_PLATFORM`, `PORT_FIX_*`, `PORT_FEAT_*`), never
raw compiler macros; the original's behaviour, bugs included, is the default
and every deviation is a named, documented flag.

- [docs/testing.md](docs/testing.md) — smoke tests that play the game
  through the real input path, the sanitizer presets, crash reports
- [docs/platform-boundary.md](docs/platform-boundary.md) — the audited
  function, subsystem and assembly boundary
- [docs/engine-scheduling.md](docs/engine-scheduling.md) — worker thread,
  frame publication, input and browser scheduling
- [docs/timing.md](docs/timing.md) — the original timing mechanisms and
  their portable counterparts
- [docs/media-implementation.md](docs/media-implementation.md) — PCM,
  Smacker and the XMIDI/OPL3 music stack
- [docs/game-data-sources-plan.md](docs/game-data-sources-plan.md),
  [docs/native-data-paths.md](docs/native-data-paths.md),
  [docs/user-data.md](docs/user-data.md) — data import, caching, user files
- [docs/game-text.md](docs/game-text.md) — the compiled-in text and its
  gettext files; [docs/localization.md](docs/localization.md) — speech and
  packs
- [docs/releasing.md](docs/releasing.md) — how a release is cut and what it
  contains
- [docs/legacy-abi.md](docs/legacy-abi.md),
  [docs/recovered-source-delta-audit.md](docs/recovered-source-delta-audit.md)
  — compiler semantics the recovered code relies on, and every port edit to a
  recovered file
- [docs/reconstruction-tooling.md](docs/reconstruction-tooling.md) — the
  byte-exact DOS reconstruction tooling still carried here

Byte equality is not a requirement in this repository, but keep inherited
files structurally close to the reconstruction so its advances stay easy to
cherry-pick; changes are not forwarded back.

## License

Except for third-party components carrying their own notices, this project is
licensed under the [GNU Affero General Public License, version 3 or later](LICENSE)
(`AGPL-3.0-or-later`). It is distributed without warranty.

This license declaration applies to contributions that project contributors
are entitled to license. It does not grant rights to original Caesar II game
assets or other third-party material. Game assets are not distributed by this
project and must be supplied by users from copies they are authorized to use.
Third-party components retain the licenses recorded in their own license and
notice files.
