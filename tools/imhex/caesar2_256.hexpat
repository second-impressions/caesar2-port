#pragma description Caesar II .256 palette (256 x 6-bit VGA RGB)
#pragma endian little

#include <caesar2_common.hexpat>     // VgaColor

// ---------------------------------------------------------------------------
// Caesar II .256 -- a raw VGA palette: 256 entries x 3 bytes (R,G,B), each
// channel a 6-bit VGA DAC value (0..63).  No header.  768 bytes total.
//
// Verified against load_to_temp_palette (readfile(fname, temp_palette, 0x300,
// 0)) and set_vga_palette (outp 0x3c9, r/g/b -- 6-bit DAC writes).  Every demo
// .256 sample is 768 bytes with max channel 63.
//
// VgaColor (caesar2_common.hexpat) previews each entry in its scaled (x4)
// colour in the hex view.
// ---------------------------------------------------------------------------

VgaColor palette[256] @ 0x00;
