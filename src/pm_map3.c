// D:\C2\CODE\pm_map3.c

#include "c2_data.h"

int elephant_riders[96] = { 16, -10, 15, -9, 15, -10, 16, -10, 15, -9, 15, -9, 18, -7, 17, -7, 17, -7, 18, -7, 17, -7, 17, -7, 16, -6, 16, -6, 15, -7, 16, -6, 15, -6, 15, -7, 11, -4, 11, -5, 11, -5, 12, -3, 12, -4, 12, -5, 7, -5, 7, -5, 7, -6, 7, -5, 7, -5, 7, -6, 5, -7, 6, -7, 6, -7, 5, -7, 6, -7, 6, -7, 6, -9, 7, -9, 7, -9, 6, -9, 7, -9, 7, -9, 12, -10, 12, -10, 12, -10, 12, -10, 12, -10, 12, -10 };


extern void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color);
extern void write_i_sprite(unsigned char *sprite_addr);
extern void write_i_left_sprite(unsigned char *sprite_addr);
extern void write_i_right_sprite(unsigned char *sprite_addr);

// FUNCTION: C2 0x3BB88
// WIN: 0x0041dc80
// Lines 39–49
//
// Top-level battle-map render: clears the per-frame sprite error
// flag, draws the battle-map base and top-half overlays, paints a
// 2x8 grid of small clipping sprites along the top edge at zoom 1,
// decrements the cell-update countdown, and pops the battle-setup
// dialog if the setup phase is still active.
void show_battlemap(void)
{
    int i;

    sprite_error = 0;
    show_battlemap_base();
    show_battlemap_top();
    if (zoom_level == 1) {
        for (i = 0x18; i < 0x164; i += 8)
            show_internal_2x8(0, i, 0);
    }
    if (update_map != 0)
        --update_map;
    if (battle_setup_count > 1)
        show_battle_setup_box();
}

// FUNCTION: C2 0x3BBEB
// WIN: 0x0041dd0b
// Lines 51–169
//
// Paint the BASE (terrain) half of the battle map: top edge
// scanline followed by ((pm_screen_height-2)/2) interior row pairs
// (mid3_line_with_sides_base + mid3_line_no_sides_base) and the
// bottom edge.  Per cell, ptr >= 0x0FFF0000 selects a virtual
// background tile; otherwise battle_map[ptr] carries the kind byte
// and the dirty flags.  When update_map is zero the full diamond is
// drawn; otherwise only refresh_a_square() touches dirty cells.

// RESIDUE 2026-07-09 late (296bd, ir 3/62, isl 3, seat 1/7,
// register-blind 207/210): the WIN oracle (Hard Rule #7) overturned the
// old shape -- CAESAR2.EXE /Od shows per-arm `sprite_x += w; continue;`
// dups (loop-inc funnels x4), `.dirty &= 0xf0` re-read RMW (not
// `= tile & 0xf0`), and the arm bodies now byte-recover PS's
// mov esi,0xe + top guard EDI + row compute + const-audit clean.
// sprite_default IS real (top else only; bottom else is literal 0xe --
// PS L142 imm store witnesses it; both confirmed by bytes this
// session).  Remaining 3 islands = ONE dword-rover cursor chain:
//   #11 top-terrain guard L90: RC edi / PS ebp (+1 short in walk
//      window T = between top update==0 guard pick and terrain guard;
//      window has 4 advances -- tile0-add, 0xf, 0xd, dispatch-add --
//      PS needs 5), the += then self-fixes (fused add eax, wrap
//      absorbs at the eax-busy #14 pick so #15+ resync; verified by
//      ring sim against the live fr trace);
//   #25/#26 bottom-terrain guard/+=: RC ebp/eax / PS edx/ebx (+2
//      short in the bottom mirror window; bottom has 3 const stores).
// PROBED AND DEAD this session (trace-screened via rover_fit +
// byte-compiled where live): `<`-form guard inversions (Rule 9 pins
// then-arm = fall-through; PS jl layout REQUIRES `>=` -- 546bd),
// literal-0xe top else (hoist does not survive CompressIns: RC imm
// store, 505bd), tile&=0xc (108bd), switch / nested-else / commuted /
// bare-block-temp spellings (all birth-identical, walk-inert),
// goto-in-else at the (tile&0xc)==0 line (moves ONE advance across
// the guard birth but in the -1 direction), while-loop form (PS
// for-increment late-line marks are normal -- byte-exact sibling
// show_citymap_base shows the same), sweep plateau at 296bd.
// The missing +1/+2 advances have no source-visible host in the
// saturated windows; else-arms walk FIRST so the virtual arm's add
// (then-arm, Rule 9-pinned) cannot enter window T.  Class: IL-birth /
// walk-order upstream of LdStAlloc.  Next lever: whatever births an
// extra RISCified dword op inside the windows without changing bytes
// (un-merging the identical add+continue tails would fit the counts
// exactly: top 2->1 merged = +1, bottom 3->1 = +2).
// 2026-07-10 probe: the unmerge lever is DEAD at the source level --
// duplicating the terrain arm's tail add (+continue) AND the commuted
// `sprite_x = pm_diamond_width + sprite_x` variant both screen
// INERT@BURN (births diverge at L140-146, walk identical): a
// post-emission pass re-merges identical tails BEFORE LdStAlloc, so
// no add+continue spelling can enter the walk window.  spell --suggest
// finds zero safe fold/unfold hosts.  Genuinely sub-source pending a
// pass-level insight; this roots the pm_map3 donor chain
// (show_battlemap_base -> mid3_no_sides -> mid3_with_sides).
// 2026-07-10b REFINEMENT (from the mid3_no_sides win, 15cd1284): a
// duplicated tail that INCLUDES the place_diamond CALL survives the
// pre-walk re-merge -- per-arm `place_diamond(2); sprite_x += w;` in
// the top-terrain sub-arms screens LIVE with dword advance +1, the
// EXACT window-T count.  But it is NOT byte-safe here: ComTail
// re-merges the copies into a fresh intra-terrain merge point instead
// of PS's cross-arm goto-top_draw jmp (296->313bd, isl 3->5) -- PS's
// layout witnesses the goto/shared form, so the +1 must be hosted
// WITHOUT creating a new call-tail.  (Contrast mid3_no_sides, where
// PS's layout IS the merged-dup form and the same lever closed the
// 0xf knot.)  Arm-order flip `if (tile == 0)` first = INERT@TREE.
// 2026-07-10c CLOSED (0bd, line-compare 62/62 clean): same-statement
// duplicate constant stores supply the missing RISCify advances
// without changing the emitted stores (top +1, bottom +3).  The last
// anonymous row/index EAX<->EBX seat needed Rule 109's second index
// use: `pseudo_map[y][x] = pseudo_map[y][x]` is DCE'd after allocation
// but gives the scaled index its own conflict.  Keeping that self-store
// in the lookup's comma expression preserves PS's single statement.
// Finally, the one-line if bodies, terrain assignment+goto, and bottom
// refresh+shared-add recover every original -d1 boundary; expanding
// any of them adds an RC-only line mark despite byte-identical code.
// 2026-07-14 CLEANUP (still 0bd, line-compare 62/62): three
// Mac-PPC-asm-witnessed source forms recovered, and the Rule 109
// comma self-store ELIMINATED:
//   * the dispatches mask tile IN PLACE after the terrain test
//     (`tile &= 0xc;` then bare == 4 / == 8 compares) -- CodeWarrior
//     shows `rlwinm r29,r29,0,0x1c,0x1d` on the tile register itself
//     at 0x17c/0x3fc, and PS's single `and al,0xc` (L77/L137) agrees.
//     (The earlier "tile&=0xc = 108bd" probe placed the mask BEFORE
//     the zero test; the Mac order -- test on a temp, THEN mask -- is
//     the byte-neutral form.)
//   * bottom-terrain uses the same RMW `dirty &= 0xf0` as the top
//     (Mac reads+stores through ONE address register at 0x4b4; PS's
//     two-reg split at L160 is the rover picking DL while the address
//     lives in EDX -- codegen, not source).
//   * the bottom lookup is the plain postincrement, same as the top
//     (Mac 0x308 mirrors 0x88); with the witnessed dispatch form the
//     scaled index seats correctly WITHOUT the self-store.
// 2026-07-14b HACK-FREE (0bd, line-compare 62/62 clean): the four
// duplicate const stores are GONE.  The retained source recovery is:
//   * the POSITIVE terrain guard (the mid3 family discovery,
//     7be7ea37/7c2ef6f3): `if ((tile & 0xc) != 0) { dispatch; draw;
//     add; continue; }` with the zero case falling through NATURALLY
//     to the terrain code at loop-body level (no goto/else) -- the
//     early `goto *_terrain` spelling produced the same final CFG but
//     a different pre-optimization block chain, and the dups had been
//     compensating for its missing RISCify advances.  Both edges also
//     take the early `if (tile == 0) { add; continue; }` arm.
// 2026-07-15 SOURCE-FLOW CORRECTION (0bd): the backward jumps at PS
// L92/L152 are compiler tail merges, not backward source gotos.  The
// terrain-virtual arms duplicate the complete `place_diamond(N);`
// + `sprite_x += pm_diamond_width;` + `continue;` tail.  Watcom ComTail
// merges each copy backward into the earlier update-virtual tail,
// producing PS's unusual jumps with entirely forward structured C.
// Duplicating only the call over-merges with the terrain-real arm;
// Forge proved that adding the increment+continue on BOTH edges moves
// ir 7/62 (526bd) to exact.  The Windows /Od build independently has
// these duplicated tails and only the i/j/tile locals; the Mac build
// also materializes the two calls separately.  Consequently the old
// `sprite_default` local was an invented explanation for Watcom's
// loop-invariant `mov esi,0xe`; the original source uses literal 0xe.

void show_battlemap_base(void)
{
    int i;
    int j;
    unsigned char tile;

    sprite_y   = pm_screen_y_start;
    sprite_x   = pm_screen_x_start;
    pm_shown_y = pm_y;
    pm_y_clip  = 0;

    /* top edge */
    for (i = 0, pm_shown_x = pm_x;
         i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (update_map == 0) {
            if (((pm_shown_ptr) >= 0x0FFF0000)) {
                sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                if (sprite_image_no >= 7) place_diamond(2);
                sprite_x += pm_diamond_width;
                continue;
            }
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            if (tile == 0) {
                sprite_x += pm_diamond_width;
                continue;
            }
            if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
            if ((tile & 0xc) != 0) {
                tile &= 0xc;
                if      (tile == 4) sprite_image_no = 0xf;
                else if (tile == 8) sprite_image_no = 0xd;
                else                sprite_image_no = 0xe;
                place_diamond(2);
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                sprite_x += pm_diamond_width;
                continue;
            }
        }
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(2);
            sprite_x += pm_diamond_width;
            continue;
        } else {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
            sprite_image_no += 0x10;
            place_diamond(2);
        }
        sprite_x += pm_diamond_width;
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    /* interior */
    mid3_line_with_sides_base();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        mid3_line_no_sides_base();
        mid3_line_with_sides_base();
    }

    /* bottom edge — same as top with style=1 */
    sprite_x   = pm_screen_x_start;
    for (i = 0, pm_shown_x = pm_x; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (update_map == 0) {
            if (((pm_shown_ptr) >= 0x0FFF0000)) {
                sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                if (sprite_image_no >= 7) place_diamond(1);
                sprite_x += pm_diamond_width;
                continue;
            }
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            if (tile == 0) {
                sprite_x += pm_diamond_width;
                continue;
            }
            if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
            if ((tile & 0xc) != 0) {
                tile &= 0xc;
                if (tile == 4) sprite_image_no = 0xf;
                else if (tile == 8) sprite_image_no = 0xd;
                else sprite_image_no = 0xe;
                place_diamond(1);
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                sprite_x += pm_diamond_width;
                continue;
            }
        }
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(1);
            sprite_x += pm_diamond_width;
            continue;
        } else {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
            sprite_image_no += 0x10;
            place_diamond(1);
        }
        sprite_x += pm_diamond_width;
    }
}

// FUNCTION: C2 0x3BF3C
// WIN: 0x0041e1e0
// Lines 171–214
//
// Top-half (figures, arrows, sprites) twin of
// show_battlemap_base.  Same scanline layout but each cell
// invokes place3_sprite() which draws the figure_a / arrow_a
// stored in battle_map[+1] / [+3].  Top + bottom edges use
// row_kind 0; interior alternates with_sides + no_sides.
void show_battlemap_top(void)
{
    int i;
    int j;

    sprite_y   = pm_screen_y_start;
    sprite_x   = pm_screen_x_start;
    pm_shown_y = pm_y;
    pm_y_clip  = 0;
    pm_shown_x = pm_x;
    for (i = 0; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }
    sprite_y += pm_diamond_half_height;
    pm_shown_y++;

    mid3_line_with_sides_top();
    for (j = 0; j < (pm_screen_height - 2) / 2; j++) {
        mid3_line_no_sides_top();
        mid3_line_with_sides_top();
    }

    /* bottom-edge sprite-only scan (mirror of top) */
    sprite_x   = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }
    pm_shown_y++;
    sprite_y  += pm_diamond_half_height;
    pm_y_clip  = 0;

    bottom3_line_with_sides();
    bottom3_line_no_sides();
}

// FUNCTION: C2 0x3C0AF
// WIN: 0x0041e3ca
// Lines 218–274
//
// Render one interior base scanline (no edge clipping).  All
// pm_screen_width cells use the full-diamond style.
// Increments pm_shown_y and pm_y_clip at end.
//
// BYTE-EXACT 2026-07-10 (line-compare 31/31 clean).  The closing
// sequence, for the family record:
//  * comma-init `for (i = 0, pm_shown_x = pm_x; ...)` -- PS -d1 packs
//    both inits under one mark (L224).
//  * `tile &= 0xc;` writeback before an UNMASKED equality dispatch --
//    CAESAR2.EXE /Od witnesses the masked writeback + `cmp eax,4/8`
//    with no re-AND; PS L240/L243 concur (single mask, widened reuse).
//  * continue-form update arm -- win-census goto-topology witnessed a
//    loop-inc funnel x4 (four continues), not nested-else fallthrough.
//  * 2026-07-14 cleanup: the dispatch's positive terrain guard is the
//    source construct: `if ((tile & 0xc) != 0) { ... continue; }`, with
//    the zero case naturally falling through to `terrain:`.  The old
//    early `if (...) goto terrain;` spelling produced the same final
//    CFG but a different pre-optimization block chain; two duplicate
//    constant stores had compensated for its missing RISCify advances.
//    The structured guard deletes both stores and is byte-exact with
//    shape 0 and line-compare 31/31 clean.
//  * shared `sprite_x += pm_diamond_width;` hoisted after the terrain
//    if/else (sweep tail_hoist) + direct `pm_diamond_half_height`
//    reads in the tail (sweep de_invent; the mid2 `h` local traded a
//    tail island for a loop-head H2 seat flip -- h is NOT PS source
//    here).  Composed by `c2 sweep` (8 -> 4 -> 0 bd).
//  * `sprite_x += pm_diamond_width; continue;` on ONE line in the
//    sprite arm (PS's jmp is unmarked; a separate `continue;` line
//    left an RC-only -d1 mark at +0x8B).
// the continue/shared layout is byte-load-bearing.
void mid3_line_no_sides_base(void)
{
    int i;
    unsigned char tile;

    sprite_x = pm_screen_x_start;
    for (i = 0, pm_shown_x = pm_x; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (update_map == 0) {
            if (((pm_shown_ptr) >= 0x0FFF0000)) {
                sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                if (sprite_image_no >= 7) place_diamond(0);
                sprite_x += pm_diamond_width; continue;
            }
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            if (tile == 0) {
                sprite_x += pm_diamond_width;
                continue;
            }
            if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
            if ((tile & 0xc) != 0) {
                tile &= 0xc;
                if      (tile == 4) sprite_image_no = 0xf;
                else if (tile == 8) sprite_image_no = 0xd;
                else                sprite_image_no = 0xe;
                place_diamond(0);
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                sprite_x += pm_diamond_width;
                continue;
            }
        }
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(0);
        } else {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
            sprite_image_no += 0x10;
            place_diamond(0);
        }
        sprite_x += pm_diamond_width;
        print3_test_info();
    }
    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x3C244
// WIN: 0x0041e622
// Lines 277–421
//
// Render one interior base scanline with edge clipping —
// uses place_lefthalf_diamond() for the leftmost column,
// place_righthalf_diamond() for the rightmost, and full
// place_diamond() for the (pm_screen_width-2) middle cells.
//
// BYTE-EXACT 2026-07-11 (638bd -> 0).  The 2026-07-10 walk-order
// diagnosis ("terrain_left must walk BETWEEN the update-left guard and
// its dispatch stores") was closed by ONE structural edit: nest the
// terrain_left body INSIDE the update arm as the ELSE of the
// `(tile & 0xc) != 0` dispatch test (label on the else arm;
// `else goto terrain_left;` on the update_map guard jumps into it --
// same cross-scope goto class as terrain_mid).  Source block-birth
// order then puts the terrain blocks between the guard and the
// dispatch stores; c2 spell screened it LIVE(reorder) -- walk differs
// with ZERO advance delta, exactly the diagnosed signature -- and the
// byte compile landed 0.  The mirrored polarity (terrain in the
// then-arm, dispatch in else) is INERT@BURN: the reverse-arm walk
// rule decides which arm carries the label.  The old ebp push +
// un-merged tail were downstream of this one knot, as predicted.
// -d1 polish: mid sprite-arm and shared update tail pack
// `sprite_x += pm_diamond_width; continue;` on ONE line; terrain_mid
// place_diamond(0) duplicated per arm (byte-neutral, kills the +0x280
// RC-only mark).  line-compare: 75/75 paired, no out-of-order; ONE
// residual RC-only mark at +0x240 (the ComTail jmp from the refresh
// path to the shared tail -- PS leaves it unmarked; tile==0-guard and
// tail-dup respellings both REGRESS bytes, so the mark is inherent to
// the byte-exact shared-tail form, same class as show_left_overlay's
// +0xD1).  Rules 121/125; block-birth dictionary reverse-arm class.
// 2026-07-14 CLEANUP (still 0bd): the three `dirty = tile & 0xf0`
// spellings (unwitnessed -- Mac PPC re-reads the FIELD, not the tile
// local, at 0xcc/0x28c/0x480) were replaced by the plain RMW
// `dirty &= 0xf0`, with the LEFT-half site written as the self-form
// re-read `dirty = dirty & 0xf0` (Mac cannot distinguish self-form
// from &= -- both single-read on PPC -- and the c2 sweep proved ANY
// ONE of the three sites in self-form is byte-exact; the extra
// address/load IL op is the +1 host that seats the first lookup's
// scaled-index temp, replacing the old `= tile &` triple).
// 2026-07-14 cleanup: the middle section uses the same positive
// terrain guard recovered in mid3_line_no_sides_base.  The zero case
// naturally falls through to the terrain draw; the positive body draws
// and continues.  This deletes both duplicate constants and moves the
// no-dup result from 413bd / ir4 to 8bd / ir0 (all 238 instructions
// register-blind-identical).  Forge's whole-function RMW grid then
// located the remaining honest allocator host: the middle update path's
// `dirty = dirty & 0xf0` self-read form.  That single tree spelling seats
// the first lookup's anonymous scaled-index temp in EBX and restores
// byte-exactness; line-compare is clean at all 75 marks.
void mid3_line_with_sides_base(void)
{
    int i;
    unsigned char tile;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    /* leftmost half-diamond — same body as middle but place_lefthalf_diamond */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (update_map == 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            if (sprite_image_no >= 7) place_lefthalf_diamond();
        } else {
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty & 0xf0;
            if (tile != 0) {
                if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
                if ((tile & 0xc) != 0) {
                    tile &= 0xc;
                    if      (tile == 4) sprite_image_no = 0xf;
                    else if (tile == 8) sprite_image_no = 0xd;
                    else                sprite_image_no = 0xe;
                    place_lefthalf_diamond();
                    refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                } else {
terrain_left:
                    if (((pm_shown_ptr) >= 0x0FFF0000)) {
                        sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                        place_lefthalf_diamond();
                    } else {
                        (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
                        sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
                        sprite_image_no += 0x10;
                        place_lefthalf_diamond();
                    }
                }
            }
        }
    } else goto terrain_left;
    sprite_x += pm_diamond_half_width;

    /* middle full diamonds */
    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (update_map == 0) {
            if (((pm_shown_ptr) >= 0x0FFF0000)) {
                sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
                if (sprite_image_no >= 7) place_diamond(0);
                sprite_x += pm_diamond_width; continue;
            }
            tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty & 0xf0;
            if (tile == 0) {
                sprite_x += pm_diamond_width;
                continue;
            }
            if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
            if ((tile & 0xc) != 0) {
                tile &= 0xc;
                if      (tile == 4) sprite_image_no = 0xf;
                else if (tile == 8) sprite_image_no = 0xd;
                else                sprite_image_no = 0xe;
                place_diamond(0);
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
                sprite_x += pm_diamond_width;
                continue;
            }
        }
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            place_diamond(0);
        } else {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
            sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
            sprite_image_no += 0x10;
            place_diamond(0);
        }
        sprite_x += pm_diamond_width;
        print3_test_info();
    }

    /* rightmost half-diamond — same body as middle but place_righthalf_diamond */
    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (update_map == 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
            if (sprite_image_no >= 7) place_righthalf_diamond();
            goto mid_done;
        }
        tile = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty;
        (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
        if (tile == 0) goto mid_done;
        if ((tile & 3) > 1) (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty |= 1;
        if ((tile & 0xc) != 0) {
            tile &= 0xc;
            if      (tile == 4) sprite_image_no = 0xf;
            else if (tile == 8) sprite_image_no = 0xd;
            else                sprite_image_no = 0xe;
            place_righthalf_diamond();
            refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            goto mid_done;
        }
    }
    if (((pm_shown_ptr) >= 0x0FFF0000)) {
        sprite_image_no = ((pm_shown_ptr) - 0x0FFF0000);
        place_righthalf_diamond();
    } else {
        (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).dirty &= 0xf0;
        sprite_image_no = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).terrain;
        sprite_image_no += 0x10;
        place_righthalf_diamond();
    }

mid_done:
    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x3C61E
// WIN: 0x0041ebe0
// Lines 428–457
//
// Top-half mid scanline, no edge half-cells.  Three render
// passes (leading/main/trailing half-cells, styles 2/0/2).
void mid3_line_no_sides_top(void)
{
    int i;

    if (pm_x > 0) {
        sprite_x = pm_screen_x_start - pm_diamond_width;
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_x - 1];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);
    }
    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }

    if (pm_shown_x < 80) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);
    }

    sprite_y += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x3C733
// WIN: 0x0041ed78
// Lines 459–491
//
// Top-half mid scanline, full edge cells.  Three render
// passes: leading full cell (style=1), main row of
// pm_screen_width - 1 cells (style=0), trailing full cell
// (style=2).
void mid3_line_with_sides_top(void)
{
    int i;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(1);
    sprite_x += pm_diamond_half_width;

    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x3C846
// WIN: 0x0041ef08
// Lines 495–528
//
// Bottom-edge with-sides scanline.  Three render passes:
//   1. Leading full cell at (pm_x, pm_shown_y), style=1.
//   2. Main row of pm_screen_width - 1 full cells, style=0.
//   3. Trailing full cell, style=2.
// Advances sprite_y / pm_shown_y / pm_y_clip by half-height
// after the row.
void bottom3_line_with_sides(void)
{
    int i;

    if (pm_shown_y >= PM_H) return;

    pm_shown_x = pm_x;
    sprite_x   = pm_screen_x_start;

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(1);
    sprite_x += pm_diamond_half_width;

    for (i = 0; i < pm_screen_width - 1; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }

    pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
    if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);

    sprite_y  += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x3C960
// WIN: 0x0041f098
// Lines 530–562
//
// Bottom-edge no-sides scanline.  Three render passes:
//   1. Leading half-cell at (pm_x - 1, pm_shown_y), style=2,
//      only when pm_x > 0.
//   2. Main row of pm_screen_width full cells, style=0.
//   3. Trailing half-cell at (pm_shown_x, pm_shown_y),
//      style=2, only when pm_shown_x < 80.
// Advances sprite_y / pm_shown_y / pm_y_clip by half-height
// after the row.
void bottom3_line_no_sides(void)
{
    int i;

    if (pm_shown_y >= PM_H) return;

    if (pm_x > 0) {
        sprite_x = pm_screen_x_start - pm_diamond_width;
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_x - 1];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);
    }
    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (((pm_shown_ptr) >= 0x0FFF0000)) {
            sprite_x += pm_diamond_width;
        } else {
            sprite_x += pm_diamond_width;
            place3_sprite(0);
        }
    }

    if (pm_shown_x < 80) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x];
        if (!((pm_shown_ptr) >= 0x0FFF0000)) place3_sprite(2);
    }

    sprite_y += pm_diamond_half_height;
    pm_shown_y++;
    pm_y_clip += pm_diamond_half_height;
}

// FUNCTION: C2 0x3CA7F
// WIN: 0x0041f231
// Lines 771–948
//
// Composite figure-and-arrow sprite renderer for one battle-map
// cell.  Reads figure_a from battle_map[+1] and arrow_a from
// battle_map[+3] of the current pm_shown_ptr.  For each non-zero
// slot:
//
//   * Compute the screen offset (xo, yo) by indexing
//     fig_walking_x/y_ofsets_z1/z2 with (facing_dir - map_direction)
//     mod 8 (z1 / z2 split is by zoom_level).  Apply the per-row
//     style offset for full / left / right slot.
//   * Read the 24-bit sprite_start, sprite_width, sprite_height and
//     sprite_x/y_off bytes from the figure's animation frame table;
//     sprite_start > 0x4baf0 marks an empty slot (bumps
//     sprite_error and bails).
//   * Apply zoom-2 x/y adjustments for special figure types
//     (figure_list[+0x4] == 2), refresh the figure square, xclip /
//     yclip and dispatch via write_i_*_sprite.
//   * For elephant-class figures (fight_state == 2) draw a 2-step
//     archer-rider loop after the body.
//   * Arrow pass walks the arrow chain via arrow_list[+0x21]
//     repeating the same pipeline on the arrow frame table.
void place3_sprite(int style)
{
    int xi;
    int yi;
    int dir;
    int xo;
    int yo;
    unsigned char *hdr;
    unsigned char *sd;
    int rider;
    int eleph;
    int xr;
    int yr;
    int z;

    figure_a = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).figure;
    arrow_a  = (*(struct battle_cell *)((unsigned char *)battle_map + ((pm_shown_ptr)))).arrow;

    if (figure_a != 0) {
        dir = figure_list[figure_a].direction - map_direction;
        if (dir < 0) dir += 8;
        if (zoom_level == 1) {
            xo = fig_walking_x_ofsets_z1[dir * 8 + figure_list[figure_a].wf_step_x];
            yo = fig_walking_y_ofsets_z1[dir * 8 + figure_list[figure_a].wf_step_x];
        } else {
            xo = fig_walking_x_ofsets_z2[dir * 8 + figure_list[figure_a].wf_step_x];
            yo = fig_walking_y_ofsets_z2[dir * 8 + figure_list[figure_a].wf_step_x];
        }
        if      (style == 1) xo -= 2;
        else if (style == 2) xo += pm_diamond_half_width;
        else                 xo += pm_diamond_half_width - pm_diamond_width;
        yo += pm_diamond_half_height;
        xi = xo; yi = yo;

        if (figure_list[figure_a].sprite_dir != 0) sd = figure_list[figure_a].sprite_data_ptr;
        else sd = figure_list[figure_a].arrow_data_ptr;
        sprite_image_no = figure_list[figure_a].sprite_anim;
        data_ptr        = sprite_image_no * 0x10 + 8;
        hdr             = sd + data_ptr; sprite_start = hdr[4] + (hdr[5] << 8) + (hdr[6] << 16);
        sprite_width    = hdr[0] + (hdr[1] << 8);
        sprite_height   = hdr[2] + (hdr[3] << 8);
        if (sprite_start > 0x4baf0) { sprite_error++; return; }
        if (sprite_width <= 0)      { sprite_error++; return; }
        if (sprite_width > 0x12c)   { sprite_error++; return; }
        if (sprite_height <= 0)     { sprite_error++; return; }
        if (sprite_height > 0x12c)  { sprite_error++; return; }
        sprite_x_off = (signed char)hdr[0xe];
        sprite_y_off = (signed char)hdr[0xd];
        xo = xo - sprite_x_off;
        yo = yo - sprite_y_off;
        old_sprite_x = sprite_x; old_sprite_y = sprite_y;
        sprite_x += xo;
        sprite_y += yo;
        if (figure_list[figure_a].fight_state == 2) {
            if (zoom_level == 1) { sprite_x -= 0x18; sprite_y -= 0x40; }
            else                 { sprite_x -= 0xc;  sprite_y -= 0x20; }
            refresh_figure3_square((sprite_x - 4) >> 4, sprite_y >> 4);
        } else if (figure_list[figure_a].fight_state != 0) {
            if (zoom_level == 1) { sprite_x -= 0x14; sprite_y -= 0x2a; }
            else                 { sprite_x -= 0xa;  sprite_y -= 0x14; }
            refresh_figure2_square((sprite_x - 4) >> 4, sprite_y >> 4);
        } else {
            if (zoom_level == 1) { sprite_x -= 0xa;  sprite_y -= 0x20; }
            else                 { sprite_x -= 4;    sprite_y -= 0x10; }
            refresh_figure_square((sprite_x - 0x14) >> 4, sprite_y >> 4);
        }
        xclip(pm_screen_x_start, 0x280);
        yclip(0x18, 0x168);
        if (yclipped != 5) {
            if      (xclipped == 1) write_i_left_sprite(sd);
            else if (xclipped == 2) write_i_right_sprite(sd);
            else                    write_i_sprite(sd);
        }
        sprite_x = old_sprite_x; sprite_y = old_sprite_y;

        if (figure_list[figure_a].fight_state == 2) {
            for (rider = 1; rider >= 0; rider--) {
                if (rider == 1) sprite_image_no = figure_list[figure_a].archer_image_a;
                else sprite_image_no = figure_list[figure_a].archer_image_b;
                data_ptr      = sprite_image_no * 0x10 + 8;
                hdr           = sd + data_ptr; sprite_start = hdr[4] + (hdr[5] << 8) + (hdr[6] << 16);
                sprite_width  = hdr[0] + (hdr[1] << 8);
                sprite_height = hdr[2] + (hdr[3] << 8);
                if (sprite_start > 0x4baf0) { sprite_error++; return; }
                if (sprite_width <= 0)      { sprite_error++; return; }
                if (sprite_width > 0x12c)   { sprite_error++; return; }
                if (sprite_height <= 0)     { sprite_error++; return; }
                if (sprite_height > 0x12c)  { sprite_error++; return; }
                sprite_x_off = (signed char)hdr[0xe];
                sprite_y_off = (signed char)hdr[0xd];
                xo = xi - sprite_x_off;
                yo = yi - sprite_y_off;
                old_sprite_x = sprite_x; old_sprite_y = sprite_y;
                sprite_x += xo;
                sprite_y += yo;
                sprite_x -= 0x18;
                sprite_y -= 0x40;
                eleph = figure_list[figure_a].sprite_anim; sprite_x += elephant_riders[eleph * 2];
                sprite_y += elephant_riders[eleph * 2 + 1];
                sprite_x += rider * 6;
                sprite_y -= rider * 6;
                if (rider <= 0) sprite_height -= 8;
                refresh_figure_square((sprite_x - 4) >> 4, sprite_y >> 4);
                xclip(pm_screen_x_start, 0x280);
                yclip(0x18, 0x168);
                if (yclipped != 5) {
                    if      (xclipped == 1) write_i_left_sprite(sd);
                    else if (xclipped == 2) write_i_right_sprite(sd);
                    else                    write_i_sprite(sd);
                }
                sprite_x = old_sprite_x; sprite_y = old_sprite_y;
            }
        }
    }

    if (arrow_a != 0) {
        do {
            dir = (unsigned char)arrow_list[arrow_a].heading - map_direction;
            if (dir < 0) dir += 8;
            xr = arrow_list[arrow_a].start_x % 7; yr = arrow_list[arrow_a].start_y % 7;
            if (zoom_level == 1) {
                z = map_direction / 2; xo = arrow_xr_x_ofset[xr + 7 * z];
                xo += arrow_yr_x_ofset[yr + 7 * z];
                yo = arrow_xr_y_ofset[xr + 7 * z];
                yo += arrow_yr_y_ofset[yr + 7 * z];
            }
            if      (style == 1) xo -= 2;
            else if (style == 2) xo += pm_diamond_half_width;
            else                 xo += pm_diamond_half_width - pm_diamond_width;
            yo += pm_diamond_half_height;

            sd = arrow_list[arrow_a].arrow_data_ptr;
            if (sd == 0) return;
            sprite_image_no = arrow_list[arrow_a].sprite_anim;
            data_ptr        = sprite_image_no * 0x10 + 8;
            hdr             = sd + data_ptr; sprite_start = hdr[4] + (hdr[5] << 8) + (hdr[6] << 16);
            sprite_width    = (hdr[0]) + (hdr[1] << 8);
            sprite_height   = hdr[2] + (hdr[3] << 8);
            if (sprite_start > 0x4baf0) { sprite_error++; return; }
            if (sprite_width <= 0)      { sprite_error++; return; }
            if (sprite_width > 0x12c)   { sprite_error++; return; }
            if (sprite_height <= 0)     { sprite_error++; return; }
            if (sprite_height > 0x12c)  { sprite_error++; return; }
            old_sprite_x = sprite_x; old_sprite_y = sprite_y;
            sprite_x += xo;
            sprite_y += yo;
            sprite_x -= sprite_width >> 1;
            sprite_y -= sprite_height;
            sprite_y -= (unsigned char)arrow_list[arrow_a].anim_count / 2 + 0x20;
            refresh_figure_square((sprite_x - 4) >> 4, sprite_y >> 4);
            xclip(pm_screen_x_start, 0x280);
            yclip(0x18, 0x168);
            if (yclipped != 5) {
                if      (xclipped == 1) write_i_left_sprite(sd);
                else if (xclipped == 2) write_i_right_sprite(sd);
                else                    write_i_sprite(sd);
            }
            sprite_x = old_sprite_x; sprite_y = old_sprite_y;
            arrow_a = (unsigned char)arrow_list[arrow_a].flight_done;
        } while (arrow_a != 0);
    }
}

// FUNCTION: C2 0x3D2D5
// WIN: 0x0041fe23
// Lines 952–976
//
// Battle-map debug overlay.  test_mode1 prints the state_idx of the
// figure stored in battle_map+1 (or zero for an empty cell); test_mode2
// prints signed battle_map+3.  Restores sprite_x/y after font_no.
void print3_test_info(void)
{
    int v;
    int fig;

    if (test_mode1 != 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) return;
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        fig = ((unsigned char *)battle_map)[(pm_shown_ptr) + 1];
        if (fig != 0) v = figure_list[fig].state_idx;
        else v = 0;
        font_no(v, 0x20, " ",
                sprite_x + 0x14 - pm_diamond_width, sprite_y + 0xa,
                font1, 0x3f);
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    } else if (test_mode2 != 0) {
        if (((pm_shown_ptr) >= 0x0FFF0000)) return;
        old_sprite_x = sprite_x;
        old_sprite_y = sprite_y;
        v = (signed char)((unsigned char *)battle_map)[(pm_shown_ptr) + 3];
        font_no(v, 0x20, " ",
                sprite_x + 0x14 - pm_diamond_width, sprite_y + 0xa,
                font1, 0x3f);
        sprite_x = old_sprite_x;
        sprite_y = old_sprite_y;
    }
}
