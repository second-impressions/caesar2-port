# Changelog

Notable changes, newest first. `tools/release.py prepare` turns the
*Unreleased* section into the next release's notes, so write for players:
what changed for them, not which files moved.

## Unreleased

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

