#pragma description Caesar II Helpfile (HELP.ENG/.GER/.FRE/.SPA on-line help pages)
#pragma endian little

import std.mem;

// ---------------------------------------------------------------------------
// Caesar II "Helpfile" -- the in-game (F1) on-line help / encyclopedia database.
// Loaded a record at a time by load_media_entry (mmedia.c):
//   readfile(media_file, &this_media_entry, 0x3a, this_help_page*0x3a + 8);
//   readfile(media_file, format_buffer, 0x7d0, this_media_entry.text_offset);
//
//   magic   : 8 bytes  "Helpfile"
//   pages   : N x 58-byte media_entry records (struct media_entry, entities.h):
//             text offset + left/right illustration sprites (.pl8) + a .voc.
//             page 0 is the null/sentinel record (text_offset = 0).
//   text    : NUL-terminated CP437 help-page bodies (each page may hold several
//             NUL-separated strings, e.g. "On-Line Help\0Select a category...").
//
// Verified field-for-field against struct media_entry + load_media_entry, and
// against the retail HELP.ENG (2000 records, "null.pl8"/"null.voc" = no asset).
// ---------------------------------------------------------------------------

struct MediaEntry {           // 0x3a = 58 bytes (struct media_entry)
    u32  text_offset;         // +0x00 absolute file offset of the page text (0 = unused)
    u16  left_sprite;         // +0x04 sprite index within left_file
    u16  right_sprite;        // +0x06 sprite index within right_file
    u16  width;               // +0x08
    char left_file[16];       // +0x0A left illustration .pl8  ("null.pl8" = none)
    char right_file[16];      // +0x1A right illustration .pl8 ("null.pl8" = none)
    char voc_file[16];        // +0x2A page audio .voc          ("null.voc" = none)
};

struct CStr {
    char value[];             // NUL-terminated CP437 string
};

struct Helpfile {
    char magic[8];            // "Helpfile"
    // page[1] is the first real page; its text_offset == the record-table end,
    // so N = (page[1].text_offset - 8) / 58.  page[1] sits at $+58 here ($==8).
    MediaEntry pages[(std::mem::read_unsigned($ + 58, 4, std::mem::Endian::Little) - 8) / 0x3a];
    CStr       text[while(!std::mem::eof())];
};

Helpfile file @ 0x00;
