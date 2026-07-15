#pragma description Caesar II Textfile (.ENG/.GER/.FRE/.SPA localised UI strings)
#pragma endian little

import std.mem;

// ---------------------------------------------------------------------------
// Caesar II "Textfile" -- the localised UI-string container (C2.ENG/GER/FRE/SPA;
// same format for every language).  Loaded whole into text_buffer (40000 B).
//
//   magic   : 8 bytes  "Textfile" (no NUL)
//   offsets : N x u32 LE absolute file offsets (a string-group table).
//             entry[0] = 0 (sentinel); entry[1] = first string = table end, so
//             N = (entry[1] - 8) / 4.  (Only 3 bytes are used per entry; the 4th
//             is always 0 -- get_buffer_ofset reads it as a 3-byte LE value.)
//   strings : packed NUL-terminated CP437 strings; each offset points to a
//             group (one or more strings, navigated by counting NULs).
//
// Verified against the current decomp (lib32.c get_buffer_ofset reads
// text_buffer[8 + i*4] as 3-byte LE; c2.c readfile("c2.eng", text_buffer,
// 0x9c40=40000, 0)).
// ---------------------------------------------------------------------------

struct CStr {
    char value[];                 // NUL-terminated CP437 string
};

struct Textfile {
    char magic[8];                // "Textfile"
    // entry[1] sits at $+4 here ($ == 8 after magic) and equals the table end:
    u32  offsets[(std::mem::read_unsigned($ + 4, 4, std::mem::Endian::Little) - 8) / 4];
    CStr strings[while(!std::mem::eof())];
};

Textfile file @ 0x00;
