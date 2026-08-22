# Legacy text encodings and portable repairs

Caesar II renders text with its own bitmap fonts. Text bytes are glyph-table
indices, not characters passed to an operating-system text API. The portable
backend must therefore preserve the original bytes and must not apply a global
CP437, CP850, Windows-1252, or UTF-8 conversion.

The main `C2.ENG` resources also changed alongside the engine. Their offset
table revisions and the guarded runtime compatibility policy are documented in
[text-asset-versions.md](text-asset-versions.md).

## Help smart-punctuation defect

The full English `HELP.ENG` contains four `0x92` bytes in contractions and
possessives. The byte is a right single quotation mark in Windows-1252, but the
game's font table treats it as the DOS `Æ` glyph. The English 1995 demo omits
the affected pages. The later English retail/rerelease help file retains all
four bytes, so the visible `Æ` is a shipped content defect rather than an SDL
rendering error. The DOS retail, Win95 rerelease, and Mac demo font assets all
contain the same `Æ` bitmap in that glyph slot; changing host text encoding
cannot correct it.

The official PC distributions available in the decompilation corpus were also
audited:

- the French help uses DOS accented-letter bytes throughout and contains no
  smart-punctuation candidate;
- the German help uses its DOS accented-letter bytes throughout and contains
  no smart-punctuation candidate;
- the Italian covermount actually carries English help data. Its DOS file has
  four `0x92` apostrophes; its Win95 file has five `0x92` apostrophes and one
  space-delimited `0x97` dash.

`PORT_FIX_HELP_SMART_PUNCTUATION` is enabled by default for the portable target
and disabled by default for retained shipped-target builds. It repairs `0x91`
and `0x92` only between ASCII letters, and `0x96` and `0x97` only between
spaces, while rendering help text. This recognizes the evidenced Windows
editor forms without changing legitimate French `ù`, French `û`, German
umlauts, or any other extended glyph in ordinary game text. Set the CMake
option to `OFF` to restore the shipped rendering in the port.
