# Native asset onboarding and data paths

## Scope

The browser target has a complete data story: the shell owns source
selection, import progress, switching, and export, and the engine only ever
sees a normalized asset root. The Linux and Windows targets share the same
importer but almost none of that experience. This document fixes the
filesystem schema and the first-run flow for the native targets.

Both native targets already build: `windows-msvc-release` is green in CI,
and `build/port/linux-release/caesar2` runs. The gap is onboarding, not compilation.

## Measured current behavior

`c2_sdl_main.c` resolves a source in this order:

1. `--game-data` / `--asset-root`, a bare positional argument, or
   `C2_ASSET_ROOT`;
2. `asset-source.txt` inside the user-data directory, but only when the
   asset root is still the default `.`;
3. otherwise `.`.

`c2_import_path` then either uses a directory in place or extracts a
ZIP/ISO/CUE — or a physical CD-ROM drive read directly as ISO-9660 sectors —
into `<user-data-dir>/game-data/<16-hex-source-key>/`, guarded by a
`.complete` marker. Drive sources (`/dev/sr0`-style device nodes, or `D:` /
`\\.\D:` optical drives on Windows) are keyed by a fingerprint of the disc's
primary volume descriptor rather than the device path, so different discs in
the same drive cache separately. `SDL_GetPrefPath("second-impressions", "caesar2")`
supplies the user-data directory, which is
`$XDG_DATA_HOME/second-impressions/caesar2/` on Linux and
`%APPDATA%\second-impressions\caesar2\` on Windows. `asset-source.txt` is
written only after the engine successfully starts.

Status: the launcher window described under “First-run window” (option B)
now exists as `src/platform/sdl3/c2_setup_ui.c`, which resolves the second,
third and fourth defects below. The layout/schema items remain open.

Four defects followed from this:

- **Everything is flat in one directory.** Saves, `caesar2.inf`,
  `asset-source.txt` and the extracted disc all sit in the same tree with no
  subdivision, so there is no way to point a backup at just the saves.
- **(fixed) The fallback picker blocked and could only pick folders.** The
  old `choose_installation_folder` ran its own `SDL_Init`/`SDL_Quit` and spun
  on `SDL_WaitConditionTimeout`, and offered `SDL_ShowOpenFolderDialog` only.
  The launcher now drives `SDL_ShowOpenFolderDialog` *and*
  `SDL_ShowOpenFileDialog` (ISO/CUE/ZIP/`.c2assets` filters) asynchronously
  from `SDL_AppIterate`, and lists detected optical drives directly.
- **(fixed) The picker was not gated on headless.**
  `caesar2 --headless --game-data /nonexistent` now prints the reason and
  exits 1; the same applies to `--skip-launcher`, `--prepare-assets` and every
  smoke flag. Only interactive runs open the launcher.
- **(fixed) No native import progress.** The launcher runs `c2_import_path`
  on a worker thread with the `c2_import_progress` callback and renders
  phase, byte and file counts; the engine window is created only afterwards.

## Prior art

| Project | Where assets live | Where user data lives | First run without data |
| --- | --- | --- | --- |
| Augustus / Julius (Caesar III) | in-place install dir; tries explicit arg, cwd, exe dir, then a saved pref path | SDL pref path | SDL folder picker, then validates by parsing `c3.eng` |
| DevilutionX | MPQs next to the exe or in the data dir (`$XDG_DATA_HOME/diasurgical/devilution`, `%APPDATA%\diasurgical\devilution`) | same dir | error message, no picker |
| OpenRCT2 | scans for RCT2 installs; path recorded in config | `~/.config/OpenRCT2`, overridable with `--user-data-path` | prompts for the RCT2 path |
| ScummVM | per-game path recorded in `scummvm.ini` | `$XDG_CONFIG_HOME/scummvm/scummvm.ini` for config, `$XDG_DATA_HOME/scummvm/saves/` for saves | game-add wizard in its own UI |
| isle-portable / isle.pizza | install dir or mounted ISO, resolved by a setup step | config file with an explicit save path | separate setup step |

Four lessons matter here.

Augustus is the closest analogue and the clearest warning. Its issue #1153 is
exactly the failure mode above: when the folder dialog cannot be shown, the
process dies before any window appears and the user sees a silent crash. A
picker that is the only recovery path must never be the thing that fails
silently.

ScummVM splits config from saves and is the only project in the table that
follows the XDG spec properly. Its precedent is that **saves are data, not
config**.

DevilutionX and OpenRCT2 both support the exe-relative layout, because users
run these things from USB sticks, AppImages and portable installs.

Nobody in the table stores extracted disc contents anywhere, because nobody
else extracts discs — they all read an existing installation in place. That
question is ours alone, and the next section answers it.

## Where extracted game data belongs

Extracted disc contents are **primary data, not cache**. The XDG spec scopes
`XDG_CACHE_HOME` to non-essential files that can be regenerated at any time
without loss of function. Our extraction fails that test on the only axis that
matters: the input may be a CD that has been ejected, an ISO the user deleted
after importing, or a mounted image that is long gone. Once the source is
away, the extraction *is* the game. A directory the system may delete at any
moment is the wrong home for it, and any scheme that needs a recorded source
path to recover from eviction is just admitting the data was never cache in
the first place.

So it goes to the data namespace from the start, and there is **no cache
namespace at all**. Nothing the native port currently produces is genuinely
regenerable-on-demand. If that changes later — decoded video frames, rendered
music, upscaled art — those can get a real `XDG_CACHE_HOME` tree at that
point, with eviction that is actually harmless.

This also settles import staging. Staged imports must be renamed into place
atomically once complete, which requires staging to sit on the same filesystem
as the destination. `XDG_CACHE_HOME` can easily be a different mount, or
tmpfs. Staging therefore lives as a sibling of the final generation, inside
the data namespace.

## Proposed schema

Two namespaces: a small config namespace for the port's own preferences, and
a data namespace for everything the user would be upset to lose.

### Linux

```text
$XDG_CONFIG_HOME/caesar2-port/          (default ~/.config/caesar2-port)
    config.ini                  rendering, audio, input, close warning

$XDG_DATA_HOME/caesar2-port/            (default ~/.local/share/caesar2-port)
    user-data/
        *.sav, lastyear.sav
        history.dat
        caesar2.inf
        shot*.png
    game-data/
        <fingerprint>/          extracted ISO/ZIP/CUE contents
        <fingerprint>/.complete
        staging/<import-id>/
        active.json
```

`SDL_GetPrefPath("", "caesar2-port")` returns exactly
`$XDG_DATA_HOME/caesar2-port/`, including the `$HOME/.local/share` fallback,
so the data root needs no hand-rolled path logic. Only the config root is
computed manually from `XDG_CONFIG_HOME` with a `$HOME/.config` fallback.

### Windows

```text
%APPDATA%\caesar2-port\
    config.ini
    user-data\           saves, history.dat, caesar2.inf, screenshots

%LOCALAPPDATA%\caesar2-port\
    game-data\           extracted contents, staging, active.json
```

The Windows split is not a cache distinction, it is the roaming distinction.
`%APPDATA%` roams to every machine the user logs into on a domain; a 600 MB
extracted disc must never do that, while a 225 KB save reasonably can.
`%LOCALAPPDATA%` is ordinary machine-local application data with no eviction
semantics attached, so the "never delete this" property still holds.
`SDL_GetPrefPath("", "caesar2-port")` gives the `%APPDATA%` half.

Linux has no roaming concept, so both halves live under `XDG_DATA_HOME` and
are separated by the `user-data/` and `game-data/` subdirectories instead.
That subdivision is what makes "back up only my saves" a single path on both
platforms.

`SDL_FOLDER_SAVEDGAMES` is deliberately not used. Our saves are opaque
fixed-size blobs that only this port reads, and SDL maps that folder to plain
`$HOME` on Linux.

### This mirrors the browser

The layout is deliberately the same shape as the OPFS tree in
`game-data-sources-plan.md`: a `game-data/` tree holding generations, staging
and an `active.json` pointer, beside a `user-data/` tree holding saves,
history and settings. Same names, same roles, same transactional activation.
One mental model, and the state machine tests can assert the same
expectations against both targets.

`active.json` records which generation is live plus provenance for display:

```json
{
  "schema": 1,
  "generation": "9f2c1a0b44e7d813",
  "importer_schema": 3,
  "profile": "",
  "source": "/home/user/games/caesar2.iso",
  "source_kind": "iso",
  "imported": "2026-08-30T13:18:04Z"
}
```

`source` exists so the setup window can say "Game data: caesar2.iso, imported
30 August 2026" and so an importer-schema bump can offer a one-click
re-import. It is not load-bearing: if the file names a source that no longer
exists, the game still starts, because the generation it points at is present.

### One correction to the original proposal

**Saves belong in the data directory, not the config directory.** XDG scopes
`XDG_CONFIG_HOME` to configuration; ScummVM moved saves out of it
deliberately, and OpenRCT2's single `~/.config/OpenRCT2` tree is a legacy wart
its own PR discussion regretted. Saves are the one irreplaceable thing here,
and dotfile-sync tooling routinely treats `~/.config` as regenerable. With
game data now also in the data namespace, keeping saves there too means the
config namespace holds nothing but a small file of user preferences that can
be recreated from defaults — which is precisely what config means.

### Portable mode

If `caesar2-port.ini` or `portable.txt` sits next to the executable, use
`<exe-dir>/config` and `<exe-dir>/data`. This costs almost nothing and is what
DevilutionX and OpenRCT2 users expect from a zip download or an AppImage.

### Override precedence

`--user-data-dir` and `--config-dir` beat `C2_USER_DATA_DIR` and
`C2_CONFIG_DIR`, which beat portable mode, which beats the platform defaults.
`--user-data-dir` keeps pointing at the `user-data/` namespace specifically,
so existing invocations and tests are unaffected. Add `--game-data-dir` for
the generation tree.

## Startup resolution

Mirror the browser state machine so both targets stay testable against the
same expectations:

```text
RESOLVE -> VALIDATE -> READY -> RUNNING
   |          |
   +-> SETUP <+   (first run, invalid source, or --reconfigure)
```

`RESOLVE` tries, in order:

1. `--game-data` / positional / `C2_ASSET_ROOT`;
2. the generation named by `active.json`, if its `importer_schema` still
   matches the build;
3. the executable directory, then the current directory, but only if either
   contains a valid layout — this is the Augustus convenience path and it
   makes "unzip next to the game files" work;
4. `SETUP`.

Step 2 is a directory existence check, not a source re-import. A recorded
source that has vanished is irrelevant to startup.

`VALIDATE` keeps the current check — `C2.ENG` and `HELP.ENG` must resolve and
be non-empty — and must run before `active.json` is replaced, so a bad
selection never displaces a working generation.

`SETUP` is entered only when a video driver is available and `--headless`,
`--prepare-assets` and every smoke flag are absent. In those modes an
unresolved source prints the reason and exits non-zero. This is the hang fix,
and it should get a regression test alongside the existing target guards.

## First-run window

Three candidate designs.

**A. Native dialogs only.** What Augustus does, and roughly what we do now.
Cheapest. But there is no place to explain what the game wants, no progress
bar for a multi-minute extraction, no way to show why a selection was
rejected, and if the dialog backend is missing the user gets nothing at all.

**B. A small SDL setup window with an embedded font, using native dialogs for
the actual picking.** The window is ours, so it can explain the requirement,
offer both "Choose installation folder" and "Choose disc image or archive"
with proper filters (`*.iso *.bin *.cue *.zip *.c2assets`), render importer
progress, and show a rejection reason inline with a retry button. It needs a
compiled-in bitmap font, because the game's own font is an asset we do not
have yet — perhaps 4 KB of glyph data for ASCII at one size.

**C. A real toolkit dialog (Qt/GTK/WinUI).** Rejected. It drags a large
dependency into a project whose entire native surface is SDL, and it would
need per-platform work for no user-visible gain over B.

**Implemented: B.** `c2_setup_ui.c` is a 480×360 logical-resolution SDL window
with the public-domain `font8x8` glyphs (`third_party/font8x8`), shown on
every interactive start like the browser landing page. It owns source display,
folder/file dialogs, drive buttons from `c2_cdrom_find_drives`, a worker-thread
import with progress, and inline error retry; `start_runtime` failures return
to it with `last_error` instead of exiting. It was the only option that could
surface import progress, and progress is not optional once a user points us
at a 600 MB image. The dialogs
themselves stay native via `SDL_ShowOpenFileDialog` and
`SDL_ShowOpenFolderDialog`, driven asynchronously from `SDL_AppIterate` — the
current blocking wait with its private `SDL_Init`/`SDL_Quit` pair goes away.
The same window later serves `--reconfigure` for switching data sources, which
is the native equivalent of the shell's "Change game data".

Fallback chain if the window cannot be created: try the native dialog alone,
then print the instructions we print today and exit non-zero. Never exit
silently.

## Work items

1. Split the path resolver into config and data roots with the override
   precedence above; introduce the `user-data/` and `game-data/` subdivision.
2. Move the extraction target to `game-data/<fingerprint>/`, keeping the
   fingerprint keying and `.complete` marker, with staging as a sibling so
   activation is a same-filesystem rename.
3. Replace `asset-source.txt` with `game-data/active.json`, written only after
   validation.
4. Add a one-time migration from `$XDG_DATA_HOME/second-impressions/caesar2/`
   and `%APPDATA%\second-impressions\caesar2\` into the new layout, leaving a
   marker so it does not run twice. Existing saves must survive. On Windows
   the `game-data` half crosses from `%APPDATA%` to `%LOCALAPPDATA%`, so that
   one is a copy-then-delete, not a rename.
5. ~~Gate `SETUP` on interactive mode; exit non-zero otherwise~~ (done; a
   target guard test is still worth adding).
6. ~~Implement the setup window with the embedded font, async dialogs,
   progress, and error retry.~~ (done: `c2_setup_ui.c`)
7. ~~Wire `c2_import_progress` on native.~~ (done, inside the launcher)
8. Add `--game-data-dir`. `--reconfigure` is unnecessary while the launcher
   is shown on every interactive start; revisit if a “skip straight to the
   game” default is ever adopted.
9. Tests: fresh-run resolution matrix, generation missing but recorded,
   importer-schema bump, migration from the old layout on both platforms,
   headless refusal, and portable mode.

Items 1–5 are mechanical and unblock a usable command-line experience on both
platforms. Item 6 is the only one with real UI design in it.

## Open questions

- Should the setup window offer "copy the installation into game-data" for
  in-place installation directories too? It doubles disk use for that case,
  but it makes every source behave identically afterwards and removes the
  "user moved their GOG folder" failure mode.
- Do we want Steam/GOG auto-detection at `RESOLVE` step 3, the way OpenRCT2
  scans for RCT2? A nice touch, but registry and path guesswork on both
  platforms.
- Flatpak and Snap confine these paths differently. Worth deciding before the
  schema is published, since changing it afterwards means another migration.
- Old generations are currently never collected. With data-namespace storage
  this is now a disk-usage question rather than a cache question, so the setup
  window probably needs a "remove unused game data" action.
