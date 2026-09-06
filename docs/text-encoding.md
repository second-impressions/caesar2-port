# Legacy text encodings and portable repairs

Caesar II renders text with its own bitmap fonts. Text bytes are glyph-table
indices, not characters passed to an operating-system text API. The portable
backend must therefore preserve the original bytes and must not apply a global
CP437, CP850, Windows-1252, or UTF-8 conversion.

The text itself is compiled into the port from UTF-8 gettext files and
transcoded to the font's CP437 code points at startup; see
[game-text.md](game-text.md).

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

With the text compiled in, the four apostrophes are corrected in the English
template (`po/c2.pot`) rather than while rendering; the earlier
`PORT_FIX_HELP_SMART_PUNCTUATION` render-time repair is gone.
