// Shared Caesar II types for the format patterns in tools/imhex/.
// Include with:  #include <caesar2_common.hexpat>
// (ImHex resolves this from the `includes/` folder of a pattern search path,
//  so add tools/imhex/ to ImHex's folders -- see tools/imhex/README.md.)

// --- history.dat ring-buffer row -------------------------------------------
// One per game-year, written by yearly_update().  200 of these = history.dat
// (and the trailing 4000 bytes of every *.SAV).
struct HistoryRow {
    s32 population;       // +0x00
    s32 denarii;          // +0x04
    s32 account_pop_tax;  // +0x08
    s32 account_ind_tax;  // +0x0C
    s32 year;             // +0x10
};

// --- VGA palette entry (.256 files) ----------------------------------------
// 256 of these = a .256 palette.  Channels are 6-bit (0..63); x4 for 8-bit RGB.
struct VgaColor {
    u8 r;
    u8 g;
    u8 b;
} [[color(std::format("{:02X}{:02X}{:02X}", r << 2, g << 2, b << 2))]];

// --- REGIONS.DAT province tile codes ---------------------------------------
// Decoded by load_region_map/put_rm_area into region_cell records.
// Uncovered codes (0x00-0x0f, 0x7c, 0x99-0x9b, 0x9d+) are unused/unknown and
// show as raw numbers.
enum TileCode : u8 {
    Sea              = 0x00 ... 0x17,   // catch-all water (terrain flags 0; 0x10-0x17 common)
    SpecialTerrain40 = 0x18 ... 0x1b,   // terrain flag 0x40
    SpecialTerrain80 = 0x1c ... 0x1f,   // terrain flag 0x80
    Land             = 0x20 ... 0x7b,   // decorative land tile (gfx = code)
    Structure1x1     = 0x7d ... 0x84,
    Structure2x2     = 0x85 ... 0x8c,
    Structure3x3     = 0x8d ... 0x90,
    Structure4x4     = 0x91,
    City             = 0x92,            // 2x2 city
    HutKind2         = 0x93,
    HutKind3         = 0x94,
    HutKind4         = 0x95,
    HutKind5         = 0x96,
    HutKind1         = 0x97,
    Border           = 0x98,            // province border marker
    TradeRoute       = 0x9c,            // trade-route marker
};
