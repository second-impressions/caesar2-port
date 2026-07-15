#pragma description Caesar II .PL8 sprite/image (Palette-8bit)
#pragma endian little
#pragma pattern_limit 4000000
#pragma array_limit 2000000

// ---------------------------------------------------------------------------
// Caesar II .PL8 -- the game's primary 8-bit palette-indexed graphics container.
// One file holds N sprites (or a single full-screen image).  No embedded
// palette: colours come from a companion .256 file (see caesar2_256.hexpat).
//
// Verified against the current decompiled accessors (display.c general_sprite /
// restore_picture_part): descriptor at idx*16+8, width@+0, height@+2, 3-byte
// sprite_start@+4, default_x@+8.  Parses every demo .PL8 sample.
//
//   header  : 8 bytes
//   descrs  : N x 16 bytes  (sprite descriptor table)
//   pixels  : raw width*height 8-bit indices at each descriptor's sprite_start
// ---------------------------------------------------------------------------

struct Pl8Header {
    u8  version;          // +0x00 always 0x02
    u8  zoom;             // +0x01 0=full detail, 1=medium, 2=small
    u16 sprite_count;     // +0x02 N
    u16 group_boundary;   // +0x04 asset-tool metadata (NOT read at runtime)
    u8  _pad06;           // +0x06 always 0
    u8  file_id;          // +0x07 asset-tool metadata (NOT read at runtime)
};

struct SpriteDesc {
    u16 width;            // +0x00 px
    u16 height;           // +0x02 px
    u32 sprite_start;     // +0x04 3-byte LE absolute pixel offset (+ always-0 byte @+0x07)
    u16 default_x;        // +0x08 default screen X
    u16 default_y;        // +0x0A default screen Y
    u8  blitter_type;     // +0x0C 0=flat 1=diamond 2=ext-diamond 3=left-roof 4=right-roof
    u8  extra_rows;       // +0x0D body/roof rows above the diamond (types 2-4)
    u16 _pad0E;           // +0x0E always 0
    // Raw 8-bit palette indices, row-major, placed at the absolute offset.
    // NOTE: terrain tiles (CITYFIXT/PROVFIXT/BATLFIX, declared 58x30) use a
    // 900-byte diamond-scan encoding, so pixels[width*height] over-reads for
    // those -- the descriptor table itself is still exact.
    u8  pixels[width * height] @ sprite_start [[comment("raw 8-bit palette indices")]];
};

struct Pl8 {
    Pl8Header  header;
    SpriteDesc sprites[header.sprite_count];
};

Pl8 file @ 0x00;
