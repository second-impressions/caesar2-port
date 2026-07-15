#pragma description Caesar II .LBM screenshot (standard EA IFF "PBM ")
#pragma endian big
#pragma array_limit 2000000

import std.mem;

// ---------------------------------------------------------------------------
// Caesar II .LBM is NOT a custom format -- it is a standard EA IFF-85 "PBM "
// (DeluxePaint chunky 8-bit LBM).  Full spec:
//   * EA IFF 85: https://wiki.amigaos.net/wiki/ILBM_IFF_Interleaved_Bitmap
//   * LBM/PBM:   https://moddingwiki.shikadi.net/wiki/LBM_Format
//
// This pattern is a generic big-endian IFF chunk reader (FORM + BMHD/CMAP/BODY)
// since ImHex ships none.  C2 specifics (write_lbm, from LBM_HEADER1/2 in
// datainit.c, verified): formType "PBM ", BMHD 640x480, 8 planes,
// compression = 0 (uncompressed), CMAP = 256x3 8-bit RGB (0x300 bytes),
// BODY = raw 640*480 = 0x4b000 bytes.  Written by capture_shot (shotN.lbm) and
// read back by convert_lbm_file / show_lbm (tutorial .lbm).
// ---------------------------------------------------------------------------

struct BMHD {              // bitmap header (see IFF spec)
    u16 width;
    u16 height;
    s16 x_origin;
    s16 y_origin;
    u8  num_planes;        // C2: 8
    u8  masking;
    u8  compression;       // C2: 0 (none)  -- NB: NOT 1 (the datainit comment mislabels xAspect)
    u8  pad1;
    u16 transparent_color;
    u8  x_aspect;
    u8  y_aspect;
    u16 page_width;
    u16 page_height;
};

struct Chunk {
    char id[4];            // "BMHD" / "CMAP" / "BODY" / ...
    u32  size;             // chunk data size (big-endian)
    if (id == "BMHD")      BMHD bmhd;
    else if (id == "CMAP") u8 palette[size];   // C2: 256x3 8-bit RGB
    else                   u8 data[size];       // BODY: raw 8-bit pixels (C2 uncompressed)
    if (size % 2 == 1)     padding[1];          // IFF chunks pad to an even boundary
};

struct IFF {
    char form[4];          // "FORM"
    u32  size;             // size of everything after this field
    char form_type[4];     // "PBM " (C2) or "ILBM"
    Chunk chunks[while(!std::mem::eof())];
};

IFF file @ 0x00;
