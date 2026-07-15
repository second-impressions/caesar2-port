#pragma description Caesar II FORUM_X.GD8 (forum department hit-test map)
#pragma endian little
#pragma array_limit 200000

import std.mem;

// ---------------------------------------------------------------------------
// Caesar II FORUM_X.GD8 -- the forum screen's department PICK MAP: a header-less
// 80-column byte grid where each byte is the forum department under that 8x8
// screen cell.  No header.  Retail = 3040 bytes = 80 x 38 rows.
//
// Loaded into scratch_buffer+0x1d4c0 by forum_constant_screen
// (readfile("forum_x.gd8", ..., 0xfa0, 0)) and picked in show_forum_screen:
//   strip = scratch_buffer + mouse_x/8;
//   forum_dept_over = strip[(mouse_y - 0xb0)/8 * 0x50 + 0x1d4c0];
// i.e. cell (col, row) = screen (col*8, 0xb0 + row*8); stride 0x50 = 80 cols.
//
// Verified against retail FORUM_X.GD8 (3040 = 80x38; byte values 0..11) and
// the FORUM_DEPT_* enum (entities.h).
// ---------------------------------------------------------------------------

enum ForumDept : u8 {
    Overview = 0,   // base / empty forum background
    Admin    = 1,   // administration / tax rates
    Career   = 2,   // career / personal cash
    Clerks   = 3,   // clerks / history
    Rome     = 4,   // emperor / Rome
    Advisor  = 5,   // help / advisor
    Army     = 6,   // army / centurion
    Industry = 7,   // industry
    Slaves   = 8,   // plebs / slaves
    Exit     = 9,   // leave forum
    Temple   = 10,  // temple / oracle
    Empire   = 11,  // empire
};

struct Row {
    ForumDept cols[80];   // 80 cells x 8px = 640px wide; col c -> screen x = c*8
};

Row rows[while(!std::mem::eof())] @ 0x00;   // row r -> screen y = 0xb0 + r*8
