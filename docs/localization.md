# Language builds

## What is localized where

The game's text — `C2.ENG` and the help in `HELP.ENG` — is compiled into the
port in every language it knows and chosen at startup; see
[game-text.md](game-text.md). The rest of a localized release stays with the
game data:

| Component | Where it comes from |
| --- | --- |
| Text (menus, panels, messages, help) | compiled in (`po/`), selected by `--language`, the launcher, or detection |
| Speech (`RAW/*.RAW`) | the game data |
| Illustrations and movies (`PL8`, `SMK`) | the game data |

The evidenced PC releases are English (every disc the corpus calls Europe,
USA or Italy — the Italian covermount is English), German (1995 and the 1996
rerelease) and French (1995). The German 1996 rerelease shows that speech is
load-bearing: 71 of its 73 RAW files differ from the English installation,
and `RIOTERS.SMK` differs too.

Neither `.ENG` extension is a language declaration: localized installations
replace both files' contents under the same names. The recovered
`set_language` also knows `HELP.GER`, `HELP.FRE` and `HELP.SPA`, but no
examined distribution is installed that way. The port answers all of those
names from the compiled-in text.

## Native builds

The executable is identical for every language; `C2_LANGUAGE` only labels a
distribution artifact and the web page's bundled-data description:

```bash
cmake --preset linux-release -B build/port/linux-release-de -DC2_LANGUAGE=de
```

Keeping language out of engine control flow keeps saves portable across
distributions.

## Packs

A `.c2assets` pack (`tools/c2-assets.py build`) can carry several languages
of speech in one deduplicated container; a *profile* selects one. With text
compiled in, a profile decides only the speech (and, for the detection
default, which `C2.ENG` the text language is read from). The launcher's
*Speech* row and `--asset-profile` choose it.

## Validation

Build-time bundled-data configuration checks for canonical `C2.ENG` and
`HELP.ENG`. Runtime imports and packs perform the same validation before
activation; the recovered startup remains a final guard. The debug smoke
tests run against any language's game data, and `--language` runs them
against any bundled text.
