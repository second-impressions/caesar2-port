#pragma description Caesar II REGIONS.DAT (province region-map grids)
#pragma endian little
#pragma pattern_limit 5000000
#pragma array_limit 5000000

import std.mem;
#include <caesar2_common.hexpat>     // TileCode

// ---------------------------------------------------------------------------
// Caesar II REGIONS.DAT -- the province region maps.  A flat array of fixed
// 60x60 tile-code grids, one per province, NO header.  Province N is read at
// offset N*0xe10 (= N*3600) by load_region_map (loadsave.c):
//   readfile("regions.dat", scratch_buffer, 0xe10, province*3600);
// then each tile code is expanded into region_cell records by put_rm_area.
//
//   province : 3600 bytes = 60 rows x 60 cols, 1 byte/tile (row-major, [y][x])
//   file     : provinces packed back-to-back (retail = 44 provinces, 158400 B)
//
// Each tile byte is decoded by the shared `TileCode` enum (see
// caesar2_common.hexpat) -- City/Hut/Border/Land/Sea/Structure categories show
// by name; uncovered codes show as raw numbers.
//
// Verified against the retail REGIONS.DAT (158400 B = 44 x 3600) and the
// current load_region_map offset computation (province*3600).
// ---------------------------------------------------------------------------

struct Province {
    TileCode tiles[60][60];   // [row y][col x]
};

Province provinces[while(!std::mem::eof())] @ 0x00;
