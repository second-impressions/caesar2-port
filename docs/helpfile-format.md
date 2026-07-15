# Caesar II `Helpfile` Format (`.ENG` / `.GER` / `.FRE` / `.SPA`)

> ImHex pattern: [`tools/imhex/caesar2_helpfile.hexpat`](../tools/imhex/caesar2_helpfile.hexpat).

## Overview

`HELP.ENG` / `HELP.GER` / `HELP.FRE` / `HELP.SPA` hold the in-game **on-line help /
encyclopedia** shown by the F1 help dialog. Despite the language extensions the format
is identical for every language. It is a **fixed-record database**: a `"Helpfile"` magic,
an array of fixed 58-byte page records, then the help-text bodies.

The active file is selected by `set_language`, which copies the appropriate name into
the `media_file` global.

> This is a **different** format from the `"Textfile"` UI-string files
> (`C2.ENG`, see [`textfile-format.md`](textfile-format.md)). The two just share the
> `.ENG`/`.GER`/… extension.

## Loading

One record (and its text) is read per page by `load_media_entry` (`mmedia.c`):

```c
readfile(media_file, &this_media_entry, 0x3a, this_help_page * 0x3a + 8);  // one 58-byte record
readfile(media_file, format_buffer,     0x7d0, this_media_entry.text_offset); // the page text (≤2000 B)
```

So record `i` is at file offset `8 + i*0x3a`, and its text is at the absolute
`text_offset`. The help dialog (`show_help_page`) then loads the optional left/right
illustration `.PL8` files and the page palette, draws the two sprites flanking the text
column, and word-wraps the body between them.

## File Layout

```
Offset        Size        Description
------        ----        -----------
0x0000        8           Magic: "Helpfile" (no NUL terminator)
0x0008        N × 0x3a    Page record table: N `media_entry` records (58 bytes each)
                            record 0 is the null/sentinel page (text_offset = 0)
text_offset   variable    Text body area: NUL-terminated CP437 help-page strings
```

The record count `N` is not stored; it is `(page[1].text_offset − 8) / 0x3a`, because
the first real page's `text_offset` is also the byte immediately after the record table.
Retail `HELP.ENG` has **2000 records** (`(0x1c528 − 8) / 58`).

## Page Record (`struct media_entry`, 58 bytes)

Field-for-field from `entities.h` / `load_media_entry`:

```
Offset  Size  Type   Field         Description
------  ----  ----   -----         -----------
+0x00   4     u32 LE text_offset   absolute file offset of this page's text (0 = unused)
+0x04   2     u16 LE left_sprite   sprite index within left_file
+0x06   2     u16 LE right_sprite  sprite index within right_file
+0x08   2     u16 LE width         (layout width)
+0x0A   16    char   left_file[16] left illustration .PL8  ("null.pl8" = no image)
+0x1A   16    char   right_file[16] right illustration .PL8 ("null.pl8" = no image)
+0x2A   16    char   voc_file[16]  page audio .VOC          ("null.voc" = no sound)
```

`load_media_entry` sets `media_left_image` / `media_right_image` / `media_voc` by
comparing each filename against `"null.pl8"` / `"null.voc"`. A present `left_file` /
`right_file` is loaded as a `.PL8`, and `left_sprite` / `right_sprite` select which
sprite within it to draw beside the text.

## Text Body Area

Each `text_offset` points to a run of **NUL-terminated CP437 strings**. A page typically
holds a title string followed by the body, e.g. record 1 of retail `HELP.ENG`:

```
"On-Line Help\0Select a category from the list below to view its on-line help ..."
```

`show_help_page` renders `text_pointer` (the title) in `font2`, then word-wraps the
remainder in `font1` between the two illustrations.

## Key Functions (PS.EXE)

| Symbol | File | Description |
|--------|------|-------------|
| `load_media_entry` | `mmedia.c` | Reads one 58-byte `media_entry` + its text into `format_buffer`; sets the asset-present flags |
| `show_help_page` | `mmedia.c` | Renders the F1 help dialog: palette, mosaic frame, optional left/right sprites, word-wrapped body |
| `launch_help` | `action.c` | Entry point; resolves redirects then shows the page |
| `set_language` | `loadsave.c` | Sets `media_file` to `help.eng`/`.ger`/`.fre`/`.spa` by language |

## Note on `load_format_buffer_from_disk`

`load_format_buffer_from_disk` (`lib32.c`) reads a 2-byte **big-endian** value at
`idx*4 + 0x1e` and a string at `value + 0x1c`. That access pattern does **not** match the
`Helpfile` record layout above (which `load_media_entry` reads), and the function has no
decompiled callers. Earlier notes that described it as "the HELP.ENG reader" were
inaccurate — the real reader is `load_media_entry`.
