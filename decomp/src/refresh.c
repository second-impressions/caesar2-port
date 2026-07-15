// D:\C2\CODE\refresh.c

/* svga_refresh_table is a 1200-byte (30×40) flag array; each cell
   tracks whether a screen tile needs redrawing.  Override added to
   _TYPE_OVERRIDES so c2_data.h declares it as char[]. */
#include "refresh.h"
#include "c2_data.h"

struct refresh_bank_row refresh_bank_switch_data[30] = {
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 0, 0, 0, 0 },
    { 1, 1, 6, 16 },
    { 0, 1, 0, 0 },
    { 0, 1, 0, 0 },
    { 0, 1, 0, 0 },
    { 0, 1, 0, 0 },
    { 0, 1, 0, 0 },
    { 1, 2, 12, 32 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 0, 2, 0, 0 },
    { 1, 3, 3, 8 },
    { 0, 3, 0, 0 },
    { 0, 3, 0, 0 },
    { 0, 3, 0, 0 },
    { 0, 3, 0, 0 },
    { 0, 3, 0, 0 },
    { 1, 4, 9, 24 },
    { 0, 4, 0, 0 },
    { 0, 4, 0, 0 },
    { 0, 4, 0, 0 },
    { 0, 4, 0, 0 }
};

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
struct svga_cell svga_refresh_data[1361];
int ref_y;
int ref_x;
int ref_ptr;
int refresh_count;
char svga_refresh_table[1364];

/* External assembly entry points used by refresh_svga_screen. */
extern void refresh_16x16_partblock(int screen_off, unsigned short bank_off,
                                    int width);

/* The svga_refresh_table zero-fill loop in setup_svga_refresh_data
 * compiles to `call __STOSB` (eax=dst, edx=val, ecx=n) via Watcom's
 * fill-loop recognition; see mmedia.c for the memset()-is-impossible
 * note. */


// FUNCTION: C2 0x28E94
// WIN: 0x0043a640
// Lines 44–49
void setup_whole_screen_refresh(void)
{
    int i;
    for (i = 0; i < 0x4b0; i++) {
        if (svga_refresh_table[i] == 0)
            svga_refresh_table[i] = 1;
    }
}

// FUNCTION: C2 0x28EB2
// WIN: 0x0043a68c
// Lines 51–65
//
// Mark the cells under the mouse cursor as needing
// refresh.  Two paths:
//
//   * pointer_mode == 6 or 7 (special pointers):
//     defer to setup_refresh_area(mouse_x, mouse_y,
//                                 3, 3, 2)
//     to mark a 3×3 pixel block centred on the cursor.
//
//   * Otherwise convert mouse_x/y to cell coords (÷16,
//     signed) into the globals `ref_x` / `ref_y`, then
//     stamp the up-to-2×2 cluster at (ref_x, ref_y) at
//     priority 2.  Each of the four cells is gated by a
//     bounds check so the cluster shrinks at the right
//     and bottom edges of the 40×30 refresh table.
//
// 5 callers: high-leverage refresh hot-path donor.
//
// NOTE: faithful but ~42 b residue.  PS and recomp share
// the SAME logical structure but Watcom makes two
// cascading regalloc choices that differ:
//
//   * PS picks `ebp` as the 4th callee-save (push ebx,
//     ecx, edx, ebp), recomp picks `edi`.  Rule 28
//     callee-save swap, function-wide tie-breaker.
//   * For the cell-1+cell-2 stores, PS keeps
//     `edx = 40*ref_y` and `eax = ref_x` as separate
//     registers and stores via
//     `[edx + eax + svga + N]` (SIB scale=1).  Recomp
//     merges them into `eax = 40*ref_y + ref_x` and
//     stores via `[eax + svga + N]` (flat).  This costs
//     ~10 b code size.
//   * Cascading jump-distance changes throughout add
//     another ~30 b of one-bit displacement diffs.
//
// 4 source variations + 7 cgex trials all stuck at the
// same 42 b regalloc cascade — likely a function-wide
// register-pressure tie-breaker we don't yet have a
// source-level lever for.  All instruction-level logic
// matches PS exactly; only the register / addressing
// encoding differs.  See
// docs/codegen-experiments/set-mouse-refresh.py for the
// negative-result trial matrix.
/* 2D access to svga_refresh_table is inlined at each callsite
 * (rather than via a local pointer) so Watcom's addrfold treats it
 * as a CL_GLOBAL_INDEX with a scaled row index, producing the SIB-
 * form `mov [edx+eax+disp], bl` store PS.EXE emits.  Storing it in
 * a `char (*)[40]` local converts to CL_POINTER and produces flat
 * `[eax+disp]` stores instead.  See Rule 68. */

void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    (*(char (*)[30][40])svga_refresh_table)[ref_y][ref_x] = 2;
    if (ref_x < 39)
        (*(char (*)[30][40])svga_refresh_table)[ref_y][ref_x + 1] = 2;
    if (ref_y < 29)
        (*(char (*)[30][40])svga_refresh_table)[ref_y + 1][ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        (&svga_refresh_table[ref_x])[(ref_y + 1) * 40 + 1] = 2;
}



// FUNCTION: C2 0x28FB5
// WIN: 0x0043a7d2
// Lines 67–77
//
// Mark a 2×2 cell square in the SVGA refresh table dirty
// (140 b, L67–77).  The refresh table is a 40×30 grid of
// per-cell refresh-priority bytes; this function bumps the
// priority of cells (x, y), (x+1, y), (x, y+1), (x+1, y+1)
// to 2, but only if they're currently < 2 (don't downgrade
// higher-priority pending refreshes).
//
// Negative `x` and `y` clamp to 0.  Out-of-table refs
// (>= 1200 = 40*30) are skipped entirely.
//
// `ref_ptr` is the global linear cell index used by callers
// (do_the_fight et al) to drive subsequent refresh ops.
//
// 6 callers: high-leverage refresh hot-path donor.
void refresh_sprite_square(int x, int y)
{
    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    if (ref_ptr < 0x4b0) {
        if (svga_refresh_table[ref_ptr] < 2)
            svga_refresh_table[ref_ptr] = 2;
        if (svga_refresh_table[ref_ptr + 1] < 2)
            svga_refresh_table[ref_ptr + 1] = 2;
        if (svga_refresh_table[ref_ptr + 0x28] < 2)
            svga_refresh_table[ref_ptr + 0x28] = 2;
        if (svga_refresh_table[ref_ptr + 0x29] < 2)
            svga_refresh_table[ref_ptr + 0x29] = 2;
    }
}

// FUNCTION: C2 0x29041
// WIN: 0x0043a8ad
// Lines 79–101
//
// Mark a 4×4 cell square in the SVGA refresh table at
// priority 2 (141 b, L79–101).  Like refresh_a_bigger_square
// (and unlike refresh_sprite_square), the stamp is
// unconditional — no < 2 priority check.
//
// Negative x/y clamp to 0; out-of-table refs (>= 1200)
// are skipped entirely.  All 16 cell stores are unrolled
// (4 rows × 4 cells, row stride 40).
//
// 3 callers — refresh-path donor.
void refresh_figure_square(int x, int y)
{
    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    if (ref_ptr < 0x4b0) {
        svga_refresh_table[ref_ptr + 0x00] = 2;
        svga_refresh_table[ref_ptr + 0x01] = 2;
        svga_refresh_table[ref_ptr + 0x02] = 2;
        svga_refresh_table[ref_ptr + 0x03] = 2;
        svga_refresh_table[ref_ptr + 0x28] = 2;
        svga_refresh_table[ref_ptr + 0x29] = 2;
        svga_refresh_table[ref_ptr + 0x2a] = 2;
        svga_refresh_table[ref_ptr + 0x2b] = 2;
        svga_refresh_table[ref_ptr + 0x50] = 2;
        svga_refresh_table[ref_ptr + 0x51] = 2;
        svga_refresh_table[ref_ptr + 0x52] = 2;
        svga_refresh_table[ref_ptr + 0x53] = 2;
        svga_refresh_table[ref_ptr + 0x78] = 2;
        svga_refresh_table[ref_ptr + 0x79] = 2;
        svga_refresh_table[ref_ptr + 0x7a] = 2;
        svga_refresh_table[ref_ptr + 0x7b] = 2;
    }
}

// FUNCTION: C2 0x290CE
// WIN: 0x0043a9c0
// Lines 103–120
//
// Mark a 5×5 cell square in the SVGA refresh table at
// priority 2.  Bigger version of refresh_figure_square.
//
// Negative x/y clamp to 0; out-of-table refs (>= 1200)
// short-circuit the rest of the loop.  Five rows of five
// cells each, row stride 40.  Note that `ref_ptr` is
// reloaded from memory each iteration: the per-iteration
// `ref_ptr += 40` mutates the global, and the next iter's
// bound check + base-pointer reads back through it.
//
// Single caller — refresh.c.
void refresh_figure2_square(int x, int y)
{
    int i;

    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    for (i = 0; i < 5; i++) {
        if (ref_ptr >= 0x4b0) return;
        svga_refresh_table[ref_ptr + 0] = 2;
        svga_refresh_table[ref_ptr + 1] = 2;
        svga_refresh_table[ref_ptr + 2] = 2;
        svga_refresh_table[ref_ptr + 3] = 2;
        svga_refresh_table[ref_ptr + 4] = 2;
        ref_ptr += 40;
    }
}

// FUNCTION: C2 0x29131
// WIN: 0x0043aa77
// Lines 122–140
//
// Mark a 6×6 cell square in the SVGA refresh table at
// priority 2.  Same loop shape as refresh_figure2_square,
// just one more cell per row and one more row.
void refresh_figure3_square(int x, int y)
{
    int i;

    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    for (i = 0; i < 6; i++) {
        if (ref_ptr >= 0x4b0) return;
        svga_refresh_table[ref_ptr + 0] = 2;
        svga_refresh_table[ref_ptr + 1] = 2;
        svga_refresh_table[ref_ptr + 2] = 2;
        svga_refresh_table[ref_ptr + 3] = 2;
        svga_refresh_table[ref_ptr + 4] = 2;
        svga_refresh_table[ref_ptr + 5] = 2;
        ref_ptr += 40;
    }
}

// FUNCTION: C2 0x2919A
// WIN: 0x0043ab3a
// Lines 142–156
//
// Mark a 4×2 cell rectangle in the SVGA refresh table at
// priority 2 (only over cells whose current priority is
// < 2).  Wider cousin of refresh_sprite_square (2×2) for
// double-wide sprites.
//
// Negative x/y clamp to 0.  Out-of-table refs (>= 1200)
// short-circuit the whole stamp.  All 8 cell stores are
// unrolled, with PS reloading `ref_ptr` from memory before
// each store after the first because the global is typed
// `int` (Watcom can't keep it in a register across the
// per-cell stores).
void refresh_sprite2w_square(int x, int y)
{
    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    if (ref_ptr < 0x4b0) {
        if (svga_refresh_table[ref_ptr + 0x00] < 2)
            svga_refresh_table[ref_ptr + 0x00] = 2;
        if (svga_refresh_table[ref_ptr + 0x01] < 2)
            svga_refresh_table[ref_ptr + 0x01] = 2;
        if (svga_refresh_table[ref_ptr + 0x02] < 2)
            svga_refresh_table[ref_ptr + 0x02] = 2;
        if (svga_refresh_table[ref_ptr + 0x03] < 2)
            svga_refresh_table[ref_ptr + 0x03] = 2;
        if (svga_refresh_table[ref_ptr + 0x28] < 2)
            svga_refresh_table[ref_ptr + 0x28] = 2;
        if (svga_refresh_table[ref_ptr + 0x29] < 2)
            svga_refresh_table[ref_ptr + 0x29] = 2;
        if (svga_refresh_table[ref_ptr + 0x2a] < 2)
            svga_refresh_table[ref_ptr + 0x2a] = 2;
        if (svga_refresh_table[ref_ptr + 0x2b] < 2)
            svga_refresh_table[ref_ptr + 0x2b] = 2;
    }
}

// FUNCTION: C2 0x2928E
// WIN: 0x0043ac9d
// Lines 158–175
//
// Mark a 5×6 cell rectangle in the SVGA refresh table at
// priority 2 (only over cells whose current priority is
// < 2).  Used by region/empire-map refresh paths where
// each region-sprite occupies more screen cells than a
// regular city sprite.
//
// Negative x/y clamp to 0.  Out-of-table refs (>= 1200)
// short-circuit the rest of the loop.  Inner row is
// unrolled (5 cells); outer loop runs 6 rows.
void refresh_region_sprite_square(int x, int y)
{
    int i;

    if (y < 0) y = 0;
    if (x < 0) x = 0;
    ref_ptr = x + y * 40;
    if (ref_ptr >= 0x4b0) return;
    for (i = 0; i < 6; i++) {
        if (svga_refresh_table[ref_ptr + 0] < 2)
            svga_refresh_table[ref_ptr + 0] = 2;
        if (svga_refresh_table[ref_ptr + 1] < 2)
            svga_refresh_table[ref_ptr + 1] = 2;
        if (svga_refresh_table[ref_ptr + 2] < 2)
            svga_refresh_table[ref_ptr + 2] = 2;
        if (svga_refresh_table[ref_ptr + 3] < 2)
            svga_refresh_table[ref_ptr + 3] = 2;
        if (svga_refresh_table[ref_ptr + 4] < 2)
            svga_refresh_table[ref_ptr + 4] = 2;
        ref_ptr += 0x28;
        if (ref_ptr >= 0x4b0) return;
    }
}

// FUNCTION: C2 0x29361
// WIN: 0x0043add7
// Lines 178–196
void refresh_a_square(int x, int y, char val)
{
    ref_ptr = x + y * 0x28;
    svga_refresh_table[ref_ptr + 0x00] = val;
    svga_refresh_table[ref_ptr + 0x01] = val;
    svga_refresh_table[ref_ptr + 0x02] = val;
    svga_refresh_table[ref_ptr + 0x03] = val;
    svga_refresh_table[ref_ptr + 0x04] = val;
    svga_refresh_table[ref_ptr + 0x28] = val;
    svga_refresh_table[ref_ptr + 0x29] = val;
    svga_refresh_table[ref_ptr + 0x2a] = val;
    svga_refresh_table[ref_ptr + 0x2b] = val;
    svga_refresh_table[ref_ptr + 0x2c] = val;
    svga_refresh_table[ref_ptr + 0x50] = val;
    svga_refresh_table[ref_ptr + 0x51] = val;
    svga_refresh_table[ref_ptr + 0x52] = val;
    svga_refresh_table[ref_ptr + 0x53] = val;
    svga_refresh_table[ref_ptr + 0x54] = val;
}

// FUNCTION: C2 0x293D2
// WIN: 0x0043aed4
// Lines 198–216
//
// Mark a 5-cell-wide vertical strip in the SVGA refresh
// table at priority 2 (134 b, L198–216).  Unlike
// refresh_sprite_square, this version unconditionally
// stamps 2 (no "don't downgrade" check).
//
// Strip height depends on initial y:
//   y < -32  → 3 rows, y forced to 0
//   y < -16  → 4 rows, y forced to 0
//   y <   0  → 5 rows, y forced to 0
//   y >=  0  → 6 rows, y unchanged
//
// Each row paints 5 contiguous cells (offsets +0..+4)
// then advances ref_ptr by 40 (one row).  Stops early
// if ref_ptr >= 1200 mid-loop.
//
// 4 callers — high-leverage refresh-path donor.
void refresh_a_bigger_square(int x, int y)
{
    int rows;
    int i;

    rows = 6;
    if (y < -0x20) {
        y = 0;
        rows = 3;
    } else if (y < -0x10) {
        y = 0;
        rows = 4;
    } else if (y < 0) {
        y = 0;
        rows = 5;
    }
    ref_ptr = x + y * 40;
    for (i = 0; i < rows; ++i) {
        if (ref_ptr >= 0x4b0) return;
        svga_refresh_table[ref_ptr + 0] = 2;
        svga_refresh_table[ref_ptr + 1] = 2;
        svga_refresh_table[ref_ptr + 2] = 2;
        svga_refresh_table[ref_ptr + 3] = 2;
        svga_refresh_table[ref_ptr + 4] = 2;
        ref_ptr += 0x28;
    }
}

// FUNCTION: C2 0x29458
// WIN: 0x0043afc4
// Lines 218–233
//
// Mark a 14×12 cell rectangle in the SVGA refresh table
// at priority 2, but only over cells whose current
// priority is < 2 (so a higher-priority refresh isn't
// downgraded).
//
// Negative x/y don't just clamp — they also shrink the
// stamp:
//   * x < 0 → x = 0, width = 8 (was 14)
//   * y < 0 → y = 0, height = 8 (was 12)
// (Empirically: covers a 14×12 region centred on a 3×3
// `refresh_a_bigger_square` site, but only when both
// coords are non-negative; otherwise truncate to the
// in-range portion.)
//
// Bail entirely the moment any cell index would exceed
// the 1200-byte table.
//
// Single caller — refresh.c.
void refresh_big_action_square(int x, int y)
{
    int w;
    int h;
    int i;
    int j;

    h = 12;
    w = 14;
    if (x < 0) {
        x = 0;
        w = 8;
    }
    if (y < 0) {
        y = 0;
        h = 8;
    }
    ref_ptr = x + y * 40;
    for (i = 0; i < h; i++, ref_ptr += 40) {
        for (j = 0; j < w; j++) {
            int idx = ref_ptr + j;
            if (idx >= 0x4b0) return;
            if (svga_refresh_table[idx] < 2) {
                svga_refresh_table[idx] = 2;
            }
        }
    }
}

// FUNCTION: C2 0x294D0
// WIN: 0x0043b0aa
// Lines 235–242
void setup_map_screen_refresh(void)
{
    /* Rule 27 (three places): the parm-init order at function entry
     * and both loop-tail update orders are determined by C statement
     * order.  Putting all increments in the for-update lists matches
     * PS’s `inc <counter>; <other update>` sequence. */
    int j = 1;
    int idx = 0x28;
    int i;
    for (; j < 0x1e; j++, idx += 0xa) {
        for (i = 0; i < 0x1e; i++, idx++) {
            if (svga_refresh_table[idx] == 0)
                svga_refresh_table[idx] = 1;
        }
    }
}

// FUNCTION: C2 0x29506
// WIN: 0x0043b11f
// Lines 244–249
void setup_map_screen_long_refresh(int fill)
{
    /* Rule 27 (twice): see setup_map_screen_refresh for the lever. */
    int j = 1;
    int idx = 0x28;
    int i;
    for (; j < 0x1e; j++, idx += 0xa) {
        for (i = 0; i < 0x1e; i++) {
            svga_refresh_table[idx] = fill;
            idx++;
        }
    }
}

// FUNCTION: C2 0x29533
// WIN: 0x0043b183
// Lines 251–257
void setup_battle_screen_refresh(void)
{
    int i;
    int j;
    int idx = 0x28;
    for (j = 1; j < 0x17; j++) {
        for (i = 0; i < 0x28; i++) {
            svga_refresh_table[idx] = 1;
            idx++;
        }
    }
}

// FUNCTION: C2 0x2955B
// WIN: 0x0043b1e1
// Lines 259–272
//
// Mark a rectangular region of the 40×30 SVGA refresh grid as
// dirty.  The grid quantizes screen pixels by 16 (so a 640×480
// screen has a 40×30 cell grid).  Args are pixel coordinates and
// dimensions; the function clamps negative origins, divides by
// 16 to get cell coordinates, then walks the cell rectangle and
// stamps `value` into svga_refresh_table[].
//
// `value` is passed as a stack argument (5th); PS reads it as
// 32-bit (`mov ecx, [esp+0x10]`) and writes via cl, so a `char`
// at the call site widens to int and PS emits `ret 4` to clean
// up the stack arg.
//
// Globals updated: ref_ptr, ref_x, ref_y track the current cell.
void setup_refresh_area(int x, int y, int w, int h, int value)
{
    if (x < 0) x = 0;
    if (y < 0) y = 0;
    x /= 16;
    y /= 16;

    ref_ptr = x + y * 40;

    for (ref_y = y; ref_y < y + h; ref_y++) {
        if (ref_ptr >= 0x4b0) break;
        for (ref_x = x; ref_x < x + w; ref_x++) {
            svga_refresh_table[ref_ptr] = value;
            ref_ptr++;
        }
        ref_ptr += 40 - w;
    }
}

// FUNCTION: C2 0x2960D
// WIN: 0x0043b2c9
// Lines 274–292
//
// Pre-compute the per-cell SVGA refresh tables.  For
// each of the 1200 (40×30) screen tiles, fills:
//
//   svga_refresh_data[idx].screen_off = pixel offset in
//       the linear video buffer (esi*640 + ecx, where
//       esi/ecx are pixel coords).
//
//   svga_refresh_data[idx].bank_off = the same offset
//       modulo 0x10000 (offset within the current bank).
//
//   svga_refresh_data[idx].split_off = 0 by default; for
//       cells in rows that cross a bank boundary, the
//       offset within the *other* bank.
//
// Also memsets `svga_refresh_table` to zero (the dirty-
// flag grid).  Single caller — part of SVGA mode
// initialisation.
void setup_svga_refresh_data(void)
{
    /* Source-shape levers (BYTE-EXACT):
     *   - py = 0 BEFORE idx = 0 : emits the prologue `xor esi`(py)
     *     before `xor edi`(idx), matching PS's zero-init order
     *     (Rule 79 Lever-A corollary: binding pinned by use-order,
     *     only the xor EMISSION order tracks source assignment order).
     *   - outer `for ( ; py < 0x1e0; py += 0x10)` (empty init) : the
     *     rotated/bottom-tested outer loop (Rule 71); a plain
     *     while/for(py=0;...) would NOT rotate.
     *   - idx++ in the for-increment + (unsigned short) cast INSIDE the
     *     `% modbase` (Rule 102): the cast narrows the dividend so Watcom
     *     does NOT CSE py*0x280+px with screen_off (== py*640+px) and
     *     re-emits the imul + ushort-truncate before the idiv, as PS does.
     *   - `modbase` (a written-once local, not a literal) keeps the
     *     0x10000 divisor hoisted into EBP across the loop (Rule 102 companion). */
    int py;
    int px;
    int idx;
    int modbase;
    int i;

    for (i = 0; i < 0x4b0; i++)
        svga_refresh_table[i] = 0;

    py = 0;
    idx = 0;
    modbase = 0x10000;
    for ( ; py < 0x1e0; py += 0x10) {
    for (px = 0; px < 0x280; px += 0x10, idx++) {
        svga_refresh_data[idx].screen_off = py * 5 * 128 + px;
        svga_refresh_data[idx].bank_off   = (unsigned short)(py * 0x280 + px) % modbase;
        svga_refresh_data[idx].split_off  = 0;

        if (refresh_bank_switch_data[py / 16].split != 0) {
            int split_col = refresh_bank_switch_data[py / 16].split_col;
            if (px >= split_col * 16) {
                svga_refresh_data[idx].split_off = (unsigned short)(px - split_col * 16);
            } else {
                svga_refresh_data[idx].split_off = (unsigned short)((40 - split_col) * 16 + px);
            }
        }
    }
    }
}

// FUNCTION: C2 0x296E5
// WIN: 0x0043b412
// Lines 296–337
//
// Reconfigure pseudo-map (PM) viewport globals for the
// city screen at the given zoom level.
//
//   * level == 0: 8×30 cells, 60×30 diamonds, scroll 1
//   * level == 1: 17×64 cells, 28×14 diamonds, scroll 2
//   * level == 2: 40×150 cells, 12×6 diamonds, scroll 4
//   * other:      no per-level set, only x/y_end recomp
//
// `zoom_level` is stashed (single byte cast).  Always
// finishes by recomputing pm_screen_{x,y}_end from the
// updated width/height × diamond half-step values.
//
// 7 callers — city-zoom path donor.
void refresh_zoom_mode(int level)
{
    zoom_level = level;
    if (zoom_level == 0) {
        scroll_amount = 1;
        pm_screen_width = 8;
        pm_screen_height = 0x1e;
        pm_screen_x_start = 0;
        pm_screen_y_start = 9;
        pm_diamond_width = 0x3c;
        pm_diamond_height = 0x1e;
        pm_diamond_half_width = 0x1e;
        pm_diamond_half_height = 0xf;
    } else if ((level & 0xff) == 1) {
        scroll_amount = 2;
        pm_screen_width = 0x11;
        pm_screen_height = 0x40;
        pm_screen_x_start = 4;
        pm_screen_y_start = 0x11;
        pm_diamond_width = 0x1c;
        pm_diamond_height = 0xe;
        pm_diamond_half_width = 0xe;
        pm_diamond_half_height = 7;
    } else if ((level & 0xff) == 2) {
        scroll_amount = 4;
        pm_screen_width = 0x28;
        pm_screen_height = 0x96;
        pm_screen_x_start = 0;
        pm_screen_y_start = 0x15;
        pm_diamond_width = 0xc;
        pm_diamond_height = 6;
        pm_diamond_half_width = 6;
        pm_diamond_half_height = 3;
    }
    pm_screen_x_end = pm_screen_x_start + pm_screen_width * pm_diamond_width;
    pm_screen_y_end = pm_screen_y_start
                      + (pm_screen_height + 1) * pm_diamond_half_height;
}

// FUNCTION: C2 0x29833
// WIN: 0x0043b5b2
// Lines 339–368
//
// Reconfigure pseudo-map (PM) viewport globals for the
// battle screen at the given zoom level.
//
//   * level == 1: 23×48 cell screen, 28×14 diamonds
//   * level == 2: 53×112 cell screen, 12×6 diamonds
//   * other:      no per-level set, only x/y_end recomp
//
// `zoom_level` is stashed (single byte cast).  Always
// finishes by recomputing pm_screen_{x,y}_end from the
// updated width/height × diamond half-step values.
//
// 3 callers — battle-zoom path.
void refresh_battle_zoom_mode(int level)
{
    zoom_level = level;
    if ((level & 0xff) == 1) {
        scroll_amount = 2;
        pm_screen_width = 0x17;
        pm_screen_height = 0x30;
        pm_screen_x_start = 0;
        pm_screen_y_start = 0x11;
        pm_diamond_width = 0x1c;
        pm_diamond_height = 0xe;
        pm_diamond_half_width = 0xe;
        pm_diamond_half_height = 7;
    } else if ((level & 0xff) == 2) {
        scroll_amount = 4;
        pm_screen_width = 0x35;
        pm_screen_height = 0x70;
        pm_screen_x_start = 6;
        pm_screen_y_start = 0x15;
        pm_diamond_width = 0xc;
        pm_diamond_height = 6;
        pm_diamond_half_width = 6;
        pm_diamond_half_height = 3;
    }
    pm_screen_x_end = pm_screen_x_start + pm_screen_width * pm_diamond_width;
    pm_screen_y_end = pm_screen_y_start
                      + (pm_screen_height + 1) * pm_diamond_half_height;
}

// FUNCTION: C2 0x2992D
// WIN: 0x0043b6cd
// Lines 373–423
//
// Per-frame SVGA bulk-refresh sweep.  Walks the 40×30
// `svga_refresh_table` priority grid; for every dirty
// cell, dispatches to `refresh_16x16_block` (or two
// `refresh_16x16_partblock` calls when the row crosses
// an SVGA bank boundary).
//
//   `refresh_bank_switch_data[row]` is a 16-byte struct
//   indexed by the 30 row IDs.  Field [0] is the split
//   flag; when zero the row is fully inside one bank.
//   When non-zero, fields [1] (split bank), [2] (col_a)
//   and [3] (split_col) describe where in the row the
//   bank boundary falls.
//
//   `svga_refresh_data[idx]` is an 8-byte struct indexed
//   by linear cell id (row*40 + col).  Layout: int
//   screen_off, ushort bank_off, ushort split_off (set
//   only for cells in split-bank rows).
//
// Tail-jumps into `setup_svga_refresh_data`'s epilogue
// at 0x296de (Rule 15 cross-function tail-merge).
// 41 callers — highest-leverage refresh donor.
//
// BYTE-EXACT.  The body indexes `svga_refresh_data[idx].field` inline
// (PS-faithful; PS recomputes `row<<4`/`idx*8` at every access — do NOT cache a
// row pointer or a cell pointer, both diverge).  Two allocation roots had to be
// matched, BOTH fixed by declaring the locals at FUNCTION scope (not in inner
// blocks).  This is a pure scope choice — `off` and `saved_idx` are real locals
// with real uses; function scope just changes which Watcom allocation phase
// processes them, with no effect on semantics or on any other instruction.
//
// 1. SPILL-SLOT ORDER (`off` at function scope).  The split rows pass
//    `svga_refresh_data[idx].screen_off + eax*5*128`.  PS spills the `eax*5*128`
//    PRODUCT to a distinct stack slot (so `ReUsableStack`, temps.c, does not
//    coalesce it with the pass-1 spill -> the 3-slot `sub esp,0xc` frame).  The
//    three same-size (4 B) spilled temps get slots from `SetTempLocation`
//    (i86temps.c: each call bumps `locals.size`, so the FIRST allocated gets
//    the HIGHEST [esp+N]); same-size order falls to creation/`Names[]` order
//    (Rule 107 / watcom-codegen-patterns.md).  A *block-scoped* `int off` is
//    created so that it slots BEFORE the earlier inline pass-1 spill, mirroring
//    PS's slots ([esp]<->[esp+4]) and cascading every jump displacement.
//    Declaring `off` at FUNCTION scope changes its creation order so the slots
//    fall in source order: saved_idx@8, screen_off@4, off@0 — exactly PS.
//    (Inline `off` -> 2-slot coalesced frame, 167 b; block-scope `off` ->
//    3-slot but mirrored slots, 112 b.)
//
// 2. PASS-1 EBP TIE (`saved_idx` at function scope).  In pass 1 PS keeps
//    `bank_off` (arg2) in ebp (`movzx ebp`) and spills `screen_off` (arg1); the
//    two arg-load temps tie on savings, so the winner is the first-created
//    conflict (ConfBefore name-pointer order).  Inline, our build creates
//    screen_off first -> it wins ebp (wrong), forcing the `xor;mov` zext of the
//    spilled bank_off.  Moving `saved_idx` to function scope shifts the
//    whole-function conflict numbering by exactly the amount that flips the tie
//    so bank_off wins ebp — matching PS.  (Do NOT instead add a throwaway
//    `int bk = bank` cache: it also flips the tie but is a forbidden
//    dummy-conflict hack; the scope move is the faithful lever.)
//
// MEMORY IS NOT INVOLVED (exhaustively ruled out): refresh.c is a small TU,
// compiled in ordinary mode; the 3-slot frame is reachable without memory
// pressure.  `_MemLow`/BlockByBlock is unreachable in this toolchain anyway
// (qemu `-m 2` and `WCGMEMORY`=64K leave codegen byte-identical; the W32RUN
// extender reports a fixed 4 MB) — see watcom-codegen-patterns.md.
void refresh_svga_screen(void)
{
    int row;
    int col;
    int idx;
    int part_rows;
    int bank;
    int off;
    int saved_idx;

    idx = 0;
    for (row = 0; row < 30; row++) {
        if (refresh_bank_switch_data[row].split != 0) {
            saved_idx = idx;
            /* First pass: lower bank, left half of split rows */
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row].bank - 1);
                    part_rows = refresh_bank_switch_data[row].part_rows;
                    if (col < refresh_bank_switch_data[row].split_col)
                        part_rows++;
                    refresh_16x16_partblock(
                        svga_refresh_data[idx].screen_off,
                        svga_refresh_data[idx].bank_off,
                        part_rows);
                }
            }
            /* Second pass: upper bank, right half of split rows */
            idx = saved_idx;
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    set_bank(refresh_bank_switch_data[row].bank);
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    part_rows = refresh_bank_switch_data[row].part_rows;
                    if (col < refresh_bank_switch_data[row].split_col)
                        part_rows++;
                    off = part_rows * 5 * 128;
                    refresh_16x16_partblock(
                        svga_refresh_data[idx].screen_off + off,
                        svga_refresh_data[idx].split_off,
                        16 - part_rows);
                }
            }
        } else {
            /* Non-split rows: simple block refresh */
            for (col = 0; col < 40; col++, idx++) {
                if (svga_refresh_table[idx] != 0) {
                    refresh_count++;
                    svga_refresh_table[idx]--;
                    bank = refresh_bank_switch_data[row].bank;
                    set_bank(bank);
                    refresh_16x16_block(
                        svga_refresh_data[idx].screen_off,
                        svga_refresh_data[idx].bank_off);
                }
            }
        }
    }
}
