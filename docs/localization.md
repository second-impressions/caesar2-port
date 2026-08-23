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

The Wasm executable is language-neutral. On first use the page imports a
complete installation or a multi-profile `.c2assets` pack. A pack can store all
observed text/help and speech languages together while storing shared content
only once. The page selects an asset profile before starting the engine; the
active view exposes the chosen data through the same canonical `C2.ENG`,
`HELP.ENG`, and `RAW/*.RAW` names.

`C2_LANGUAGE` remains an optional output/default-profile label for distributor
builds. It is no longer necessary to compile a separate runtime for each
language. Advanced packs may select text and speech independently, while
observed-release profiles keep localized graphics/text/speech coupled by
default.

## Validation

Build-time bundled-data configuration checks for canonical `C2.ENG` and
`HELP.ENG`. Runtime imports and optimized packs perform the same validation
before activation; the recovered startup remains a final guard.

Debug semantic smoke tests exercise the selected complete asset tree through
the recovered menus. The official asset corpus can run the existing province,
city, tutorial, and save/load tests once per language without committing
copyrighted resources.
