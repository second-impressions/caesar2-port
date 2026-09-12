# Changelog

Notable changes, newest first. `tools/release.py prepare` turns the
*Unreleased* section into the next release's notes, so write for players:
what changed for them, not which files moved.

## Unreleased

- The game's limit on walkers out at once is gone from the port. The original
  keeps 200 slots for every tax collector, vigile, market trader and business
  walker in the city, and a large city -- around 200 forums, prefectures,
  markets and businesses -- fills them, after which some markets and
  businesses are never served no matter how many are built. The port now has
  1,000 slots (a build-time setting). Below the old limit the
  game plays exactly as before: the slots only decide when a building is
  refused, never how many walkers it sends.
- Saves use a new file format. It keeps the same `.sav` name, carries a
  version and a checksum, checks every value it reads, and is written in one
  piece so an interrupted save cannot destroy the slot it was replacing. The
  yearly-graph history now travels inside each save instead of a separate
  `history.dat`, so loading a save brings its own graphs with it. Saves from
  the original game and from earlier versions of the port load as before;
  saves written by the port no longer open in the original DOS or Windows
  game. An old `history.dat` in the user-data folder is ignored.
- A market or business that was handed the same walker slot it had just
  freed retired its new walker on the spot and then waited its usual four
  months before trying again. It now keeps that walker. This does not
  change how many walkers a city can have out at once.

## 1.0.3 - 2026-09-09

- Installed GOG copies now provide music, speech and movies automatically:
  the launcher reads the complete original CD from their `game.gog` file
  instead of using only the partial hard-disk installation beside it.

## 1.0.2 - 2026-09-08

- Windows: no console window behind the game. Started from a terminal, the
  program still prints there (`--version`, errors, the crash report's
  location).
- The Windows version's soundtrack plays: every CD from August 1996
  carries it (`C2WIN95/RAW/`), the 1998 US disc has nothing else. It is
  different music, not the DOS score re-recorded — Keith Zizza wrote it in
  1996 for the Windows release, where the 1995 game is Jeremy A. Bell's
  and Jason P. Rinaldi's. Choose in the launcher, in the web page's
  Settings → Game data → Music, or with `--music dos|windows`; the DOS
  music, which follows your city's mood, stays the default. Either place
  says which of the two the game data has.
- The web page's Settings tab "Assets" is "Game data", as the launcher
  and the front page already said.
- The five full-screen movies the Windows version ships at 500x240
  (battle won/lost, promotion, victory, defeat) play from those files
  instead of the 320x152 DOS ones.
- Launcher: the game data's version and release note each get a line of
  their own (no more left-truncated "...rsion 1.02"), and the status line
  no longer draws over the media note.
- Launcher: a disc without music files is told so, instead of "they
  stayed on the CD", which is only true of an installed folder.
- Launcher: accented letters in a localized version line ("Version
  Française") are shown without the accent instead of as "?": C2.ENG is
  CP437, not Latin-1.
- The helmet is the icon everywhere: the game and launcher windows
  (taskbar, Alt-Tab), the Windows executable (with a version block), the
  AppImage, the macOS disk image's volume, and a 256 px icon on Linux
  desktops without SVG support.

## 1.0.1 - 2026-09-07

- Browser version: the text language setting moved from the front page
  into Settings → General.
- The hosted browser version at the site root is now always the latest
  release; the development branch is served at `/main/`.
- Version numbers: a release is plain `1.0.1`; development builds name
  their branch and commit (`main-29c2a676`), pull requests their number
  (`pr23-…`), so a crash report says exactly what was running.

## 1.0.0 - 2026-09-07

- First release of the port: the recovered Caesar II engine on SDL3 for
  Linux (AppImage and Flatpak), Windows, macOS and the browser, with the
  original music through a faithful OPL3 driver, reading your own CD-ROM,
  disc image, installation or archive. The macOS app is not notarized:
  allow it once under System Settings → Privacy & Security.
- A launcher imports the game data once and remembers it, and offers
  fullscreen, integer or fractional scaling and the text language.
- The game's text is built in, in English, German and French, and chosen
  automatically from your game data or by hand; translations are ordinary
  gettext files under `po/`.
- Windowed play at any whole multiple of 640x480, fullscreen with F11,
  screenshots with Alt+1..8, mouse-wheel zoom.
- A crash writes a report with function and source line to the user-data
  directory and the launcher points at it next time.
- Every construction list on the city and province maps opens with a click
  and closes with the next, on every language's layout.

