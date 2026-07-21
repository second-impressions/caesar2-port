# Language builds

## Distribution model

Caesar II is distributed as one complete build per language. A language build
contains one executable or WebAssembly runtime plus one complete official
localized asset tree. The browser never downloads text, speech, or movies for
languages other than the selected build.

The currently evidenced PC language distributions are:

| Tag | Language | Main text | Help | Speech |
| --- | --- | --- | --- | --- |
| `en` | English | `C2.ENG` | `HELP.ENG` | English `raw/*.RAW` |
| `de` | German | localized `C2.ENG` | localized `HELP.ENG` | German `raw/*.RAW` |
| `fr` | French | localized `C2.ENG` | localized `HELP.ENG` | French release assets |

Neither extension is a language declaration. The recovered startup opens the
installed `C2.ENG` and defaults help to `HELP.ENG`; official localized
installations replace both files' contents while retaining those canonical
installed filenames. The recovered `set_language` function also knows
`HELP.GER`, `HELP.FRE`, and `HELP.SPA`, but those names are not how the examined
standalone German distribution is installed and must not drive modern
distribution selection.

Each build must use a complete installation from the corresponding release.
That includes localized `raw/` speech and any language-specific graphics or
Smacker movies, not merely the two text resources. Asset files are preserved
byte-for-byte and retain Caesar II's bitmap-font encoding.

The German 1996-12-18 rerelease confirms that this is load-bearing: 71 of its
73 RAW files differ from the examined English/European installation. Twelve
of the thirteen message Smacker files are identical, while `RIOTERS.SMK`
differs. The distribution boundary therefore remains the complete release
rather than a guessed list of text and voice filenames.

## Native builds

`C2_LANGUAGE` labels the distribution artifact:

```bash
cmake --preset linux-release \
  -B build/port/linux-release-de \
  -DC2_LANGUAGE=de
cmake --build build/port/linux-release-de
./build/port/linux-release-de/caesar2 \
  --asset-root /path/to/german/CAESAR2
```

The native executable remains identical across tags; localization belongs to
the selected complete asset tree. Keeping language out of engine control flow
also keeps saves portable across distributions. Packaging systems may use the
tag to name archives or installers.

## WebAssembly builds

Configure each language in its own build directory with its matching asset
root:

```bash
emcmake cmake --preset wasm-release \
  -B build/port/wasm-release-de \
  -DC2_LANGUAGE=de \
  -DC2_WASM_ASSET_ROOT=/path/to/german/CAESAR2
cmake --build build/port/wasm-release-de
```

This emits `caesar2-de.html`, `caesar2-de.js`, `caesar2-de.wasm`, and
`caesar2-de.data`. The `.data` file contains only that installation. English,
French, and Spanish use separate build directories and correspondingly tagged
output names. A deployment can publish all four directories, but a player
visits one language entry point and downloads only its package.

The language tag names the output files, while every runtime still follows the
same recovered canonical asset names. A page therefore has no runtime language
switch that could select German behavior while serving English data.
`tools/serve-wasm.py` automatically serves a directory containing one tagged
build; `--entry` selects one explicitly if several outputs are placed together.

## Validation

WebAssembly configuration checks for canonical `C2.ENG` and `HELP.ENG` before
packaging. The recovered startup retains its own required-file validation.

Debug semantic smoke tests exercise the selected complete asset tree through
the recovered menus. The official asset corpus can run the existing province,
city, tutorial, and save/load tests once per language without committing
copyrighted resources.
