# Changelog

Notable changes, newest first. `tools/release.py prepare` turns the
*Unreleased* section into the next release's notes, so write for players:
what changed for them, not which files moved.

## Unreleased

- Game data is one collection now, and you can add to it: an English and a
  German disc give you both languages' speech to choose from, a 1996 CD adds
  the Windows soundtrack and the larger movies to an older one, and adding a
  disc you already have changes nothing. Where two copies of a file differ,
  the better one is kept: the DOS original over the Windows 95 re-encode,
  a newer release over an older one, the larger version of a movie that is
  shown enlarged anyway.
- The Macintosh CDs can be added (a Toast or ISO image, or the disc in a
  drive). They bring the best-looking versions of four of the full-screen
  movies, and their soundtrack and speech are converted; they need a PC
  copy beside them to play.
- Export writes all your game data as one `.c2assets` file, a plain ZIP, to
  move it to another computer or into the browser; importing it adds it
  back. Remove deletes the game data and keeps saves and settings.
- Launcher: three pages instead of one crowded list: Play, Game data and
  Settings. Nothing overlaps the key reference any more, and a disc in a
  drive that the system has also mounted is listed once.
- Speech can be chosen when the game data has several languages: in the
  launcher, on the web page and with `--speech`. Without a choice it
  follows the text language.
- Earlier imports are moved into the collection on the first start, in the
  launcher and in the browser alike; nothing needs importing again.
- `--game-data` adds its source to the collection; `--asset-root` reads a
  folder in place. `--asset-profile` and version-1 `.c2assets` packs are
  gone, as is the script that built them.

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

