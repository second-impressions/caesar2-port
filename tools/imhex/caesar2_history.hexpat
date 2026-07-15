#pragma description Caesar II history.dat - 4,000 bytes (year history graph)
#pragma endian little

#include <caesar2_common.hexpat>     // HistoryRow

// ---------------------------------------------------------------------------
// Caesar II history.dat : a 200-slot circular buffer of per-year economic
// snapshots that drives the in-game history graphs.  One 20-byte row is
// appended each game-year by yearly_update()/save_history() (loadsave.c).
// history_end_ptr is the write cursor (wraps at 200); history_entries
// saturates at 200.  The same 4000-byte blob is the trailing payload of
// every *.SAV file.
//
//   200 rows x 5 ints x 4 bytes = 4,000 bytes (fixed)
//
// HistoryRow is shared with the *.SAV tail (see caesar2_common.hexpat).
// ---------------------------------------------------------------------------

HistoryRow rows[200] @ 0x00;
