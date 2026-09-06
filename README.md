# Caesar II Port

A source port of Impressions Games' *Caesar II* (1995) for current systems:
Linux, Windows, and the browser. It runs the recovered original engine — the
byte-exact [Caesar II reconstruction](https://github.com/second-impressions/caesar2-reconstruction)
— on SDL3, plays the original music through a faithful reimplementation of
the game's OPL3 driver, and reads the game data from your own copy.

The original game data is required and is never included.

## Playing

**Web:** the hosted build runs in any current browser; it asks for your game
data on first use and keeps it in the browser's storage.

**Native:** run `caesar2`. A small launcher window opens first: pick your game
data once, then *Play*. It remembers the source and your display choices.

### Game data

Any of these works, natively or in the browser — the importer works out what
it is by content:

- the original **CD-ROM** in a drive (natively; the launcher lists the disc
  when one is inserted),
- a **disc image**: `.iso`, `.bin` with or without its `.cue`, also inside a
  `.zip`,
- an **installed game folder** (GOG, or an old DOS/Windows installation —
  pick any file inside it, e.g. `C2.ENG`),
- a `.zip` of such a folder,
- a `.c2assets` pack, which can carry several languages in one file
  (`tools/c2-assets.py build`, see [docs/localization.md](docs/localization.md)).

Note that the original installer copied only part of the game to the hard
disk: an installation folder without `XMI/` and `RAW/` has no music or
speech. The launcher and web page say so; use the disc or its image for
everything.

Disc images and archives are imported once into the user-data directory
(`~/.local/share/second-impressions/caesar2` on Linux) and reused on later
starts; saves, screenshots and settings live there too.

### Display and controls

The game is 640x480. The window opens at the largest whole multiple that
fits your desktop and can be resized freely; with *integer scaling* (the
default) the game is shown at the largest whole multiple that fits the
window, in real pixels, letterboxed until the next multiple fits. With
*fractional scaling* it fills the window. Both toggles are remembered.

| Key | Action |
|---|---|
| **F11** | toggle fullscreen |
| **F10** | toggle integer / fractional scaling |
| **Ctrl+1** … **Ctrl+5** | window at exactly 1x … 5x |
| **Ctrl+0** | window at the largest multiple that fits the screen |
| Mouse wheel | zoom (the game's own `+`/`-`) |
| **Alt+1** … **Alt+8** | screenshot `shot1.png` … `shot8.png` into the user-data directory |

Everything else — hotkeys, mouse behaviour, menus — is the original game's;
see its manual. Maximizing the window also gives the largest scale the
screen holds.

Command line: `caesar2 [SOURCE]` starts with a given game-data source;
`--fullscreen`, `--fractional-scaling`, `--skip-launcher`, `--mouse-lock`
(confine the pointer to the game area), `--user-data-dir PATH`,
`--asset-profile NAME` (language in a multi-profile pack), `--version`.

### Crashes

If the game crashes, it prints a report ending with a request to open an
issue. Please paste the whole report — it already contains the build version,
function names and source lines — and say what you were doing.

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
- [docs/localization.md](docs/localization.md) — languages, speech, packs
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
