// D:\C2\CODE\battle.c

#include "battle.h"
#include "c2_data.h"

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
int bat_ai_trig_count;
int bat_attack_rate;
int bat_order;
int first_rear;
int bat_no_selected;
int bat_which;
int y_bit;
int first_front;
int which_unit;
int bat_no_of_units;
int x_bit;
int bat_attacker_clock;
int bat_odds;
int bat_spacing;
int first_back;
int xright_front;
int bat_control;
int bat_size;
int yfront;
int bat_hi;
int xleft_front;
int ypos;
int xright_rear;
int bat_morale;
int xleft_back;
int bat_side;
int xpos;
int xleft_rear;
int bat_no;
int bat_width;
int yrear;
int xright_back;
int yback;

/* ---------------------------------------------------------------------
 * Implicit-int callees made VISIBLE (NOT the original PS source shape).
 *
 * PS's .c did not declare these helpers: the calls below were K&R
 * implicit-int, so wcc386 assumed `int f()`.  Declaring them `extern
 * int f()` here is BYTE-NEUTRAL -- identical codegen to the implicit
 * declaration the compiler already synthesised -- and exists only to
 * surface the real cross-TU contract.  The real definitions return a
 * narrower type (noted per line); the caller intentionally reads EAX
 * as int, exactly as PS.EXE does.  Do NOT "correct" these to the real
 * return type -- a typed (char / enum) decl CHANGES the bytes.
 * ------------------------------------------------------------------- */
extern int get_heading();  /* really heading_t (enum, int-wide) -- common.c */

void elephant_fire(void);
// FUNCTION: C2 0x4AFD7
// WIN: 0x00472bc0
// Lines 273–329
//
// Top-level battle entry point.  When `continuing` is 0 saves the
// player's map context, switches to the battle pseudo-map
// (map_mode=2, zoom_level=1), and runs the full
// load-graphics / get-pseudo-map / generate-battle-map /
// setup-battle / figure-intelligence / battle_screen / ambients
// pipeline.  Plays "batest2.xmi" and enters the main loop: each
// tick pumps battle_game_loop, watches both sides' men and morale,
// and once either drops to zero ticks battle_over_count to 0x32 (~50
// ticks of victory/defeat animation) before forcing battle_state =
// 4.  On exit (unless battle_state == 0xA) restores the saved map
// context and stops the tune.

void do_fight_battle(int continuing)
{
    update_icon         = 0;
    pointer_mode        = 0;
    reg_placing_type    = 0;
    reg_placing_flags   = 0;
    placing_type        = 0;
    placing_flags       = 0;
    battle_state        = 0;
    nomansland_ptr      = 0x1380;
    battle_turbo        = 0;
    c2inf.paused        = 1;
    redraw_icons        = 1;

    if (continuing == 0) {
        return_map_mode   = map_mode;
        return_zoom_level = zoom_level;
        if (map_mode == 0) {
            city_pm_x       = pm_x;
            city_pm_y       = pm_y;
            city_direction  = map_direction;
        } else {
            region_pm_x     = pm_x;
            region_pm_y     = pm_y;
            region_direction = map_direction;
        }
        zoom_level    = 1;
        map_direction = 0;
        pm_x          = 0x1c;
        pm_y          = 0x38;
        map_mode      = 2;
        load_battle_graphics(1);
        refresh_battle_zoom_mode(zoom_level);
        get_pseudo_map(map_direction);
        generate_battle_map();
        setup_battle();
        figure_intelligence();
        battle_screen(1);
        init_battle_ambients();
    }

    play_tune("batest2.xmi", 1);

    while (battle_state < 4) {
        battle_game_loop();
        if (battle_state == 0xa) break;

        if (our_battle_men <= 0) {
            battle_state = 2;
            tune_mood    = 0x12;
            battle_over_count++;
        }
        if (their_battle_men <= 0) {
            battle_state = 2;
            tune_mood    = 0x11;
            battle_over_count++;
        }
        if (our_battle_morale <= 0) {
            battle_state = 2;
            tune_mood    = 0x12;
            battle_over_count++;
        }
        if (their_battle_morale <= 0) {
            battle_state = 2;
            tune_mood    = 0x11;
            battle_over_count++;
        }
        if (battle_over_count > 0x32)
            battle_state = 4;
        if (battle_over_count == 1) {
            if (tune_mood == 0x11) play_speech(3);
            else                   play_speech(4);
        }
    }

    pointer_mode                  = 0;
    c2inf.paused                   = 0;

    if (battle_state != 0xa) {
        zoom_level = return_zoom_level;
        map_mode   = return_map_mode;
        if (map_mode == 0) {
            pm_x          = city_pm_x;
            pm_y          = city_pm_y;
            map_direction = city_direction;
        } else {
            pm_x          = region_pm_x;
            pm_y          = region_pm_y;
            map_direction = region_direction;
        }
        get_pseudo_map(map_direction);
        stop_tune();
    }
}

// FUNCTION: C2 0x4B267
// WIN: 0x00472f8c
// Lines 333–349
//
// Select / toggle every figure that belongs to the same
// unit as `fig_idx` (135 b, L333–349).
//
//   1. If figure[fig_idx].owner == 0 (player) call
//      deselect_all_figures, else deselect_enemy_figures.
//      This wipes the prior selection state.
//   2. unit_ref = figure[fig_idx].unit_ref (byte +0x2B,
//      zero-extended into int).
//   3. Walk figure_list[1..200] and for each figure whose
//      .unit_ref matches:
//        * battle_stats_type = 0.
//        * Skip if state_idx == 2 (already sleeping/dead).
//        * If mode == 0, toggle .selected.
//          else,        force .selected = 1.
void select_a_unit(int fig_idx, int mode)
{
    int unit_ref;

    if (figure_list[fig_idx].owner == 0) {
        deselect_all_figures();
    } else {
        deselect_enemy_figures();
    }
    unit_ref = figure_list[fig_idx].unit_ref;
    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].unit_ref == unit_ref) {
            battle_stats_type = 0;
            if (figure_list[figure_no].state_idx != 2) {
                if (mode == 0) {
                    figure_list[figure_no].selected ^= 1;
                } else {
                    figure_list[figure_no].selected = 1;
                }
            }
        }
    }
}

// FUNCTION: C2 0x4B2EE
// WIN: 0x004730ae
// Lines 351–354
//
// Clear the .selected flag on every figure in figure_list[1..200].
void deselect_all_figures(void)
{
    for (figure_no = 1; figure_no < 201; figure_no++) {
        figure_list[figure_no].selected = 0;
    }
}

// FUNCTION: C2 0x4B31C
// WIN: 0x004730fc
// Lines 356–360
//
// Walk the figure_list and clear the .selected flag on every
// enemy unit (owner == 0).  Used by the battle UI when
// switching selection modes so a leftover marquee can't keep
// enemies highlighted.
void deselect_enemy_figures(void)
{
    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].owner == 0) {
            figure_list[figure_no].selected = 0;
        }
    }
}

// FUNCTION: C2 0x4B352
// WIN: 0x00473169
// Lines 362–367
//
// Mark every populated, owned figure as selected.  Companion
// to deselect_enemy_figures — enemies (owner == 0) and empty
// slots (kind == 0) are skipped.
void select_all_figures(void)
{
    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists != 0
         && figure_list[figure_no].owner != 0) {
            figure_list[figure_no].selected = 1;
        }
    }
}

// FUNCTION: C2 0x4B38F
// WIN: 0x004731f5
// Lines 369–398
//
// Drag-rectangle selection on the battle map.  The player has held
// the mouse over (battle_drag_start_x/y) -> (act_start_x/y); this
// walks every battlemap cell inside that axis-aligned rectangle
// (battle_map is a stride-4 0x34-wide grid).  For each cell:
//   * if .+1 (figure_no_in_cell) is non-zero, call select_a_unit
//     with mode = 1 to add that figure's unit to the current
//     selection;
//   * otherwise stamp the lower nibble of .+2 to 0xe (selection
//     highlight marker) while preserving bits 4..7.
void select_drag_figures(void)
{
    int x0;
    int x1;
    int y0;
    int y1;
    int row_stride;
    int x;
    int y;
    int cell_off;
    int width;
    unsigned char unit_no;

    x0 = battle_drag_start_x;
    x1 = act_start_x;
    y0 = battle_drag_start_y;
    y1 = act_start_y;

    if (x1 < x0) {
        int t = x0; x0 = x1; x1 = t;
    }
    if (y0 > y1) {
        int t = y0; y0 = y1; y1 = t;
    }

    cell_off = (y0 * 0x34 + x0) * 4;
    width = x1 - x0 + 1;
    row_stride = (0x34 - width) * 4;

    for (y = y0; y <= y1; y++, cell_off += row_stride) {
        for (x = x0; x <= x1; x++, cell_off += 4) {
            unit_no = ((unsigned char *)battle_map)[(cell_off) + 1];
            if (unit_no != 0) {
                select_a_unit(unit_no, 1);
            }
            else {
                ((unsigned char *)battle_map)[(cell_off) + 2] |= 2;
                ((unsigned char *)battle_map)[(cell_off) + 2] &= 0xf3;
                ((unsigned char *)battle_map)[(cell_off) + 2] |= 0xc;
            }
        }
    }
}

// FUNCTION: C2 0x4B438
// WIN: 0x00473345
// Lines 400–443
//
// Two-pass redraw of the moving-unit highlight on the battle map,
// called from battle_action while the mouse is being dragged.
// Pass 1 walks every selected non-commander figure, re-anchors
// its parent unit by (hlite_off_x, hlite_off_y), and bails out if
// the destination falls off the grid or onto an occupied enemy
// cell.  Pass 2 then stamps the destination's dirty bits: 0x0C
// for an empty target, 0x08 for a foreign occupant, leaving the
// preserved bits 0xF3 for a same-side cell.  Return value is
// undefined (the asm exits via the shared 6-pop epilogue
// without setting EAX): the source is `int` with bare `return;` at
// every exit.  W107 is therefore expected.
//
// BYTE-EXACT 2026-07-12.  The Windows /Od witness exposed `row` and
// `col` as invented locals, both state-12 tests as explicit continue
// guards, and `u_idx` as the one index shared by both passes.  Making
// the battle coordinate and selection fields unsigned then exposed
// the remaining source lever: each pass-1 bound and address uses the
// same prev-first x/y expression.  Pass 2 keeps prev-first x but uses
// offset-first y.  A coupled 5,184-pair expression screen found the
// family; consistently commuting x and y closed the final 315b rover
// cascade to zero.  The one-line guards and map-bit arms reproduce
// PS's 33/33 `-d1` statement stream exactly.  All declarations remain
// at function scope.
int show_move_highlight(void)
{
  int ptr;
  int u_idx;

  if (pm_over == 0)
    return;
  get_highlight_position();
  if (hlite_squares == 0)
    return;
  for (figure_no = 1; figure_no < 0xc9; ++figure_no)
  {
    if ((figure_list[figure_no].exists != 0) && (figure_list[figure_no].selected != 0))
    {
      u_idx = figure_list[figure_no].unit_ref;
      if (unit_list[u_idx].first_figure == figure_no)
      {
        unit_list[u_idx].prev_x = unit_list[u_idx].x + hlite_off_x;
        unit_list[u_idx].prev_y = unit_list[u_idx].y + hlite_off_y;
      }
      if (figure_list[figure_no].state_idx == 0xc)
        continue;
      if (unit_list[u_idx].prev_x + figure_list[figure_no].offset_x >= 0x34) { hlite_squares = 0; return; }
      if (unit_list[u_idx].prev_x + figure_list[figure_no].offset_x < 0) { hlite_squares = 0; return; }
      if (unit_list[u_idx].prev_y + figure_list[figure_no].offset_y >= 0x34) { hlite_squares = 0; return; }
      if (unit_list[u_idx].prev_y + figure_list[figure_no].offset_y < 0) { hlite_squares = 0; return; }
      ptr = ((unit_list[u_idx].prev_x + figure_list[figure_no].offset_x) + (unit_list[u_idx].prev_y + figure_list[figure_no].offset_y) * 0x34) * 4;
      if (ptr >= nomansland_ptr) { hlite_squares = 0; return; }
      figure_a = ((unsigned char *) battle_map)[ptr + 1];
      if (figure_a != 0)
      {
        if ((figure_list[figure_a].owner != 0) && (figure_list[figure_a].selected == 0)) { hlite_squares = 0; return; }
      }
    }
  }

  for (figure_no = 1; figure_no < 0xc9; ++figure_no)
  {
    if ((figure_list[figure_no].exists != 0) && (figure_list[figure_no].selected != 0))
    {
      if (figure_list[figure_no].state_idx == 0xc)
        continue;
      u_idx = figure_list[figure_no].unit_ref;
      ptr = ((unit_list[u_idx].prev_x + figure_list[figure_no].offset_x) + (figure_list[figure_no].offset_y + unit_list[u_idx].prev_y) * 0x34) << 2;
      figure_a = ((unsigned char *) battle_map)[ptr + 1];
      ((unsigned char *) battle_map)[ptr + 2] |= 0x02;
      ((unsigned char *) battle_map)[ptr + 2] &= 0xf3;
      if ((figure_a != 0) && (figure_list[figure_no].owner != figure_list[figure_a].owner)) { ((unsigned char *) battle_map)[ptr + 2] |= 0x08; }
      else { ((unsigned char *) battle_map)[ptr + 2] |= 0x0c; }
    }
  }

  return;
}







// FUNCTION: C2 0x4B69F
// WIN: 0x0047388d
// Lines 445–480
//
// While the mouse is held down inside the battle-map (pm_over != 0)
// and we have at least one aim-eligible figure selected, paint an
// 11x11 (10-cell radius) cell-mask rectangle around (act_start_x,
// act_start_y).
void show_aim_highlight(void)
{
    int eligible;
    int x0;
    int x1;
    int y0;
    int y1;
    int x;
    int y;
    int cell_off;
    int row_skip;

    if (pm_over == 0) return;

    figure_no = 1; eligible = 0;
    for (; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists != 0 && figure_list[figure_no].selected != 0) {
            temp_unit = figure_list[figure_no].unit_ref;
            if (unit_list[temp_unit].target_lock == 0) {
                if (unit_list[temp_unit].unit_sub_kind != 0) eligible++;
            }
        }
    }
    if (eligible == 0) return;

    x0 = act_start_x - 5; hlite_left = x0;
    y0 = act_start_y - 5; hlite_top  = y0;
    x1 = act_start_x + 5;
    y1 = act_start_y + 5;

    if (x0 < 0)    x0 = 0;
    if (x1 >= 0x34) x1 = 0x33;
    if (y0 < 0)    y0 = 0;
    if (y1 >= 0x34) y1 = 0x33;

    cell_off = (y0 * 0x34 + x0) * 4;
    row_skip = (0x34 - (x1 - x0 + 1)) * 4;

    y = y0;
    for (; y <= y1; y++, cell_off += row_skip) {
        x = x0;
        for (; x <= x1; x++, cell_off += 4) {
            ((unsigned char *)battle_map)[(cell_off) + 2] &= 0xf1;
            ((unsigned char *)battle_map)[(cell_off) + 2] |= 0xe;
        }
    }
}

// FUNCTION: C2 0x4B7B2
// WIN: 0x00473acd
// Lines 482–555
//
// Commit the highlighted move previewed by show_move_highlight.
// First scans the selected figures: bails if nothing is
// highlighted, if the parent unit can't move, or if none of the
// figures have morale left.  Then prompts via confirm(); on
// decision == 0 also bails.  Out of battle (battle_state == 0):
// teleport each selected figure into its formation slot via
// get_fig_in_unit_position, refresh its battle_map footprint, and
// repaint.  Mid-battle: set figure state 8 (moving) or 0xF (charge,
// when the unit's morale is broken), then assign the new target
// anchor + slot offsets so figure_go_to_target walks them there.
void start_move(void)
{
    int flag;
    int new_ptr;
    int u_idx;
    flag = 0;
    if (hlite_squares == 0) {
        pointer_mode = 0;
        redraw_icons = 1;
    } else {
        /* Pass 1: locate a movable selected figure. */
        for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
            if (figure_list[figure_no].exists != 0
                && figure_list[figure_no].selected != 0) {
                u_idx = figure_list[figure_no].unit_ref;
                if (unit_list[u_idx].type == 0) {
                    deselect_all_figures();
                    return;
                }
                if (unit_list[u_idx].target_lock != 0) {
                    flag = 1;
                    break;
                }
            }
        }
        if (flag) {
            confirm(4, 0xa0, 0xa0);
            if (decision == 0)
                return;
        }

        /* Pass 3: clear battle_map under selected figs (battle_state == 0). */
        for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
            if (figure_list[figure_no].exists != 0
                && figure_list[figure_no].selected != 0
                && battle_state == 0) {
                ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 1] = 0;
            }
        }

        /* Pass 4: re-anchor + apply state to each selected fig. */
        for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
            if (figure_list[figure_no].exists != 0
                && figure_list[figure_no].selected != 0) {
                u_idx = figure_list[figure_no].unit_ref;
                figure_list[figure_no].selected = 0;
                if (figure_list[figure_no].state_idx != 0xc) {
                    if (battle_state == 0) {
                        pointer_mode = 0;
                        update_map   = 1;
                        get_fig_in_unit_position(unit_list[u_idx].formation_mode, figure_list[figure_no].unit_type, figure_no);
                        figure_list[figure_no].grid_x = (char)(unit_list[u_idx].prev_x + x_bit);
                        figure_list[figure_no].grid_y = (char)(unit_list[u_idx].prev_y + y_bit);
                        figure_list[figure_no].offset_x = x_bit;
                        figure_list[figure_no].offset_y = y_bit;
                        figure_list[figure_no].map_ref =
                            (figure_list[figure_no].grid_x +
                             figure_list[figure_no].grid_y * 0x34) * 4;
                        ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 1] = figure_no;
                    } else if (unit_list[u_idx].target_lock != 0) {
                        pointer_mode = 0;
                        figure_list[figure_no].state_idx = 8;
                        get_fig_in_unit_position(unit_list[u_idx].formation_mode, figure_list[figure_no].unit_type, figure_no);
                        figure_list[figure_no].prev_grid_x = (unit_list[u_idx].prev_x + x_bit);
                        figure_list[figure_no].prev_grid_y = (unit_list[u_idx].prev_y + y_bit);
                        figure_list[figure_no].offset_x    = x_bit;
                        figure_list[figure_no].offset_y    = y_bit;
                    } else {
                        pointer_mode = 0;
                        figure_list[figure_no].state_idx = 0xf;
                        figure_list[figure_no].is_visible &= 0xfd;
                        get_fig_in_unit_position(unit_list[u_idx].formation_mode, figure_list[figure_no].unit_type, figure_no);
                        figure_list[figure_no].prev_grid_x = (unit_list[u_idx].prev_x + x_bit);
                        figure_list[figure_no].prev_grid_y = (unit_list[u_idx].prev_y + y_bit);
                        figure_list[figure_no].offset_x    = x_bit;
                        figure_list[figure_no].offset_y    = y_bit;
                    }
                }
            }
        }
    }
    return;
}

// FUNCTION: C2 0x4BA40
// WIN: 0x0047410c
// Lines 557–581
//
// Activate "aim" mode for every selected figure.  Walks the figure_no
// 1..0xc8 range and for each living, currently-selected figure:
//   * clamps its selected flag back to 0
//   * if its parent unit's type is zero, bails by deselecting all
//     figures and returning (caller stops the aim flow)
//   * if the figure's state_idx is already 0xc (some aim/move terminal
//     state), or its unit's combat field at +0xE is non-zero, or the
//     unit isn't aim-eligible (byte +0x39 == 0), skips it
//   * otherwise stashes (hlite_left, hlite_top) into the unit's aim
//     target slot (+0x3a, +0x3b), sets state_idx = 0xb (aim state),
//     and snapshots the figure's grid_(x,y) into prev_grid_(x,y).
//
// If no figure was promoted, pointer_mode is cleared and redraw_icons
// latched so the cursor UI reverts.
void start_aim(void)
{
    int  hit_count;
    int  unit_idx;

    hit_count    = 0;
    pointer_mode = 0;

    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists != 0
            && figure_list[figure_no].selected != 0) {
            unit_idx = figure_list[figure_no].unit_ref;
            if (unit_list[unit_idx].type == 0) {
                deselect_all_figures();
                return;
            }
            figure_list[figure_no].selected = 0;
            if (figure_list[figure_no].state_idx != 0xc
                && unit_list[unit_idx].target_lock == 0
                && unit_list[unit_idx].unit_sub_kind != 0)
            {
                unit_list[unit_idx].attack_marker_x = hlite_left;
                unit_list[unit_idx].attack_marker_y = hlite_top;
                figure_list[figure_no].state_idx = 0xb;
                figure_list[figure_no].prev_grid_x = figure_list[figure_no].grid_x;
                figure_list[figure_no].prev_grid_y = figure_list[figure_no].grid_y;
                hit_count++;
            }
        }
    }

    if (hit_count == 0) {
        pointer_mode = 0;
        redraw_icons = 1;
    }
}

// FUNCTION: C2 0x4BB23
// WIN: 0x00474311
// Lines 583–608
//
// Compute the highlight bounding box and centre offset of the
// selected figures.  Used by show_move_highlight before drawing
// the drag-marker frame.  Walks figure_list 1..0xC8, skipping
// non-existing / unselected / dying figures, and tracks the
// (min/max) of grid_x and grid_y over the rest along with the
// total count.  The bbox centre, the drag-anchor delta from
// (act_start_x, act_start_y), and the battle_map cell offset
// (stride 0x34 cells × 4 bytes per cell = 208) are then derived
// into the corresponding `hlite_*` globals.
void get_highlight_position(void)
{
    hlite_centre_x = 0;
    hlite_centre_y = 0;
    hlite_off_x    = 0;
    hlite_off_y    = 0;
    hlite_off_ptr  = 0;
    hlite_squares  = 0;
    hlite_left     = 0x34;
    hlite_right    = 0;
    hlite_top      = 0x34;
    hlite_bottom   = 0;

    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists == 0)    continue;
        if (figure_list[figure_no].selected == 0)  continue;
        if (figure_list[figure_no].state_idx == 0x0c) continue;

        if (figure_list[figure_no].grid_x < hlite_left)
            hlite_left = figure_list[figure_no].grid_x;
        if (hlite_right < figure_list[figure_no].grid_x)
            hlite_right = figure_list[figure_no].grid_x;

        if (figure_list[figure_no].grid_y < hlite_top)
            hlite_top = figure_list[figure_no].grid_y;
        if (hlite_bottom < figure_list[figure_no].grid_y)
            hlite_bottom = figure_list[figure_no].grid_y;

        hlite_squares++;
    }

    hlite_centre_x = (hlite_right  - hlite_left) / 2 + hlite_left;
    hlite_centre_y = (hlite_bottom - hlite_top)  / 2 + hlite_top;

    hlite_off_x    = act_start_x - hlite_centre_x;
    hlite_off_y    = act_start_y - hlite_centre_y;

    hlite_off_ptr  = hlite_off_x * 4;
    hlite_off_ptr += hlite_off_y * 208;
}

// FUNCTION: C2 0x4BCBF
// WIN: 0x00474593
// Lines 612–617
//
// Walk every cell in the 52x52 battle_map grid and clear the highlight bits
// (0x0C) in `dirty`.
void clear_all_highlights_from_battlemap(void)
{
    /* Walk every cell in the 52×52 battle_map grid and
       clear the highlight bits (0x0C) in ((unsigned char *)battle_map)[+2].
       Each cell is 4 bytes; cm_sptr is the running byte
       offset into battle_map. */
    gmn_y   = 0;
    cm_sptr = 0;
    for ( ; gmn_y < 0x34; gmn_y++) {
        gmn_x = 0;
        do {
            (*(struct battle_cell *)((unsigned char *)battle_map + ((cm_sptr)))).dirty &= 0xf3;
            gmn_x++;
            cm_sptr += 4;
        } while (gmn_x < 0x34);
    }
}

// FUNCTION: C2 0x4BD13
// WIN: 0x00474618
// Lines 619–640
//
// Build a fresh open-battle map: clear battle_map layers 1 and 3,
// scatter a random low-5-bit terrain index into every cell
// (battle_map[y*0x34+x] = rand128 & 0x1f), then stamp the standard
// 52x52 battle-map dimensions and the (0xa0 x 0xa0) compass overlay
// origin, and finally drive get_pseudo_map(map_direction).
void generate_battle_map(void)
{
    clear_all_bm(1);
    clear_all_bm(3);

    gmn_y   = 0;
    cm_sptr = 0;
    for ( ; gmn_y < 0x34; gmn_y++) {
        gmn_x = 0;
        do {
            random();
            (*(struct battle_cell *)((unsigned char *)battle_map + ((cm_sptr)))).terrain = rand128 & 0x1f;
            gmn_x++;
            cm_sptr += 4;
        } while (gmn_x < 0x34);
    }

    map_actual_width      = 0x34;
    map_actual_height     = 0x34;
    map_actual_atom       = 4;
    map_width_reduction   = 0xe;
    map_height_reduction  = 0xe;
    com_x                 = 0x1e0;
    com_y                 = 0x30;
    com_w                 = 0xa0;
    com_h                 = 0xa0;

    get_pseudo_map(map_direction);
}

// FUNCTION: C2 0x4BDE3
// WIN: 0x00474716
// Lines 644–695
//
// Initialise battle state for the combatants named in
// our_battle_army / their_battle_army.  Picks battle_scale (0/1/2/4/8
// = how many men each sprite represents) from the combined troop
// total via thresholds 900 / 1800 / 3600 / 7200, then zeros the
// rout / retreat / AI counters and seeds bat_ai_trig_count.
// get_battle_odds() fills the morale tables, and the per-side stance
// flips to 1 (outmatched) when the opposing side outnumbers it by
// more than 4/3.  Finally clears the unit / figure / arrow lists,
// builds both sides via setup_roman_units + setup_enemy_units, and
// snapshots the starting men counts for later morale-decay refs.
void setup_battle(void)
{
    int our_men;
    int their_men;
    int total;

    total = army_list[our_battle_army].total_troops
          + army_list[their_battle_army].total_troops;

    battle_scale = 0;
    if (total >= 0x1c20) battle_scale = 8;
    else if (total >= 0xe10) battle_scale = 4;
    else if (total >= 0x708) battle_scale = 2;
    else if (total >= 0x384) battle_scale = 1;

    their_battle_routs            = 0;
    our_battle_routs              = 0;
    bat_attacker_clock            = 0;
    battle_ai_count               = 0;
    battle_npc_retreat_count      = 0;
    battle_over_count             = 0;
    bat_enemy_left_flank_unit     = 0;
    bat_enemy_right_flank_unit    = 0;
    bat_enemy_first_fan_unit      = 0;
    bat_enemy_second_fan_unit     = 0;
    bat_ai_trig_count             = 12;

    get_battle_odds();

    /* re-read after odds tables ran */
    our_men   = army_list[our_battle_army].total_troops;
    their_men = army_list[their_battle_army].total_troops;

    their_battle_stance = 0;
    our_battle_stance   = 0;
    if (our_men   > (their_men + their_men / 3)) their_battle_stance = 1;
    if (their_men > (our_men   + our_men   / 3)) our_battle_stance   = 1;

    bat_no_selected = 0;
    retreat_flag    = 0;

    clear_unit_list();
    clear_figure_list();
    clear_arrow_list();
    setup_roman_units();
    setup_enemy_units();
    get_units_status();

    our_battle_start_men   = our_battle_men;
    their_battle_start_men = their_battle_men;
    which_unit             = 0;
}

// FUNCTION: C2 0x4BF69
// WIN: 0x0047491f
// Lines 697–711
//
// Snapshot troop counts from the two participating armies into the
// battle globals used by the setup UI and battle resolution code.
void get_battle_men(void)
{
    our_battle_men      = army_list[our_battle_army].total_troops;
    their_battle_men    = army_list[their_battle_army].total_troops;
    our_battle_specials = army_list[our_battle_army].num_specials;
    our_battle_horse    = army_list[our_battle_army].num_horse;
    our_battle_regs     = army_list[our_battle_army].num_regulars;
    our_battle_irregs   = army_list[our_battle_army].num_irregulars;
    our_battle_auxs     = army_list[our_battle_army].num_auxillaries;
    their_battle_specials = army_list[their_battle_army].num_specials;
    their_battle_horse    = army_list[their_battle_army].num_horse;
    their_battle_regs     = army_list[their_battle_army].num_regulars;
    their_battle_irregs   = army_list[their_battle_army].num_irregulars;
    their_battle_auxs     = army_list[their_battle_army].num_auxillaries;
}

// FUNCTION: C2 0x4C016
// WIN: 0x00474a86
// Lines 713–760
//
// Set up the Roman side of the battle (called once from
// setup_battle).  Resets the bat_* globals (which=0, spacing=1,
// side=-1, control=1), then runs find_attack_spot or
// find_defensive_spot per our_battle_stance.  Four sequential
// stages place heavy infantry, light infantry, archers and
// mercenary cavalry: each draws its per-kind man count from
// army_list[our_battle_army] and calls build_units_figures
// repeatedly with the matching figureN_data sprite block until
// the count is spent.  Each call places at most `bat_size` men
// (0x3C..0x3C0 depending on battle_scale).
void setup_roman_units(void)
{
    int count_light;
    int count_heavy;
    int count_archers;
    int count_mercs;
    int bat_size;
    int made;

    bat_which   = 0;
    bat_spacing = 1;
    bat_side    = -1;
    bat_control = 1;

    if (our_battle_stance != 0)
        find_attack_spot();
    else
        find_defensive_spot();

    count_heavy   = army_list[our_battle_army].num_regulars;
    count_light   = army_list[our_battle_army].num_irregulars;
    count_archers = army_list[our_battle_army].num_auxillaries;
    count_mercs   = army_list[our_battle_army].num_specials;

    if (battle_scale == 4)
        bat_size = 0x3c0;
    else if (battle_scale == 3)
        bat_size = 0x1e0;
    else if (battle_scale == 2)
        bat_size = 0xf0;
    else if (battle_scale == 1)
        bat_size = 0x78;
    else
        bat_size = 0x3c;

    made = 0;

    /* Stage 1: heavy infantry */
    while (bat_size / 12 <= count_heavy) {
        if (bat_size <= count_heavy)
            build_units_figures(made++, 1, 3, 0, 0, our_battle_stance,
                army_list[our_battle_army].morale, bat_size, 2, 1,
                figure1_data, 0, 1);
        else
            build_units_figures(made++, 1, 3, 0, 0, our_battle_stance,
                army_list[our_battle_army].morale, count_heavy, 2, 1,
                figure1_data, 0, 1);
        if (bat_size <= count_heavy)
            count_heavy -= bat_size;
        else
            count_heavy = 0;
    }

    /* Stage 2: light infantry */
    while (count_light >= bat_size / 12) {
        if (count_light >= bat_size)
            build_units_figures(made++, 2, 2, 0, 1, our_battle_stance,
                army_list[our_battle_army].morale, bat_size, 2, 1,
                figure2_data, 0, 2);
        else
            build_units_figures(made++, 2, 2, 0, 1, our_battle_stance,
                army_list[our_battle_army].morale, count_light, 2, 1,
                figure2_data, 0, 2);
        if (count_light >= bat_size)
            count_light -= bat_size;
        else
            count_light = 0;
    }

    /* Stage 3: archers */
    while (bat_size / 12 <= count_archers) {
        if (bat_size <= count_archers)
            build_units_figures(made++, 3, 2, 1, 2, our_battle_stance,
                army_list[our_battle_army].morale, bat_size, 2, 1,
                figure3_data, 0, 3);
        else
            build_units_figures(made++, 3, 2, 1, 2, our_battle_stance,
                army_list[our_battle_army].morale, count_archers, 2, 1,
                figure3_data, 0, 3);
        if (bat_size <= count_archers)
            count_archers -= bat_size;
        else
            count_archers = 0;
    }

    /* Stage 4: mercenary cavalry */
    while (bat_size / 12 <= count_mercs) {
        if (bat_size <= count_mercs)
            build_units_figures(made++, mercs_type, mercs_speed, mercs_missile,
                4, our_battle_stance, army_list[our_battle_army].morale,
                bat_size, 2, 1, figure7_data, figure8_data, 7);
        else
            build_units_figures(made++, mercs_type, mercs_speed, mercs_missile,
                4, our_battle_stance, army_list[our_battle_army].morale,
                count_mercs, 2, 1, figure7_data, figure8_data, 7);
        if (bat_size <= count_mercs)
            count_mercs -= bat_size;
        else
            count_mercs = 0;
    }
}

// FUNCTION: C2 0x4C399
// WIN: 0x00474f9f
// Lines 762–852
//
// Set up the barbarian/enemy side of the battle (called once from
// setup_battle after setup_roman_units).  Reads the per-tribe
// formation hints from tribe_battle_setup[bat_tribe]: front/middle/
// rear unit kinds, a mercenary-cavalry kind, plus a sprite-block
// selector per rank (fig4/5/6 depending on hint).  Picks bat_size
// from a per-battle_scale table (down to 0x50/0x64/0x1E/0xA at the
// smallest scale).  Forces the flank / fan unit flags from
// tribe_ai_data when its enable bits are zero.  Resets the bat_*
// globals (which=0, spacing=3, side=1, control=0), runs
// find_attack_spot / find_defensive_spot per their_battle_stance,
// then drains the five army_list cohort counts through
// build_units_figures — stages 1-3 are central formations, stage 4
// mercenary cavalry (kind 0xF), stage 5 archers (kind 4).
//
// BYTE-EXACT 2026-07-10 (Rule 115 / Windows W2 witness): MSVC /Od
// exposed the five-count zero-assignment chain and the paired flank/fan
// assignment chains that Watcom optimizes out or coalesces.  The dead zero
// stores still perturb Watcom's ConfBefore queue; with them present, three
// top-level declaration swaps restore the original queue and eliminate the
// entire made++ rover cascade.  The former 324-byte scratch-seat residue was
// therefore downstream of a missing first-assignment shape, not irreducible.
// The recovered same-line statement groups also make line-compare 55/55 clean.
void setup_enemy_units(void)
{
    int tbs_rear_figure;
    int bat_size_merc;
    int tbs_middle_figure;
    int rear_quirk;
    int tbs_flank_quirk;
    int count_heavy_rear;
    int tbs_middle_kind;
    int bat_size_arch;
    int tbs_front_kind;
    int front_quirk;
    int bat_size_front;
    int tbs_rear_kind;
    int count_heavy_middle;
    int count_heavy_front;
    int count_archers;
    int tbs_front_quirk;
    int count_mercs;
    int bat_size_middle;
    unsigned char *fig_a;
    int made;

    count_heavy_front = count_heavy_middle = count_heavy_rear = count_archers = count_mercs = 0;
    count_heavy_front  = army_list[their_battle_army].num_regulars;
    count_heavy_middle = army_list[their_battle_army].num_irregulars;
    count_heavy_rear   = army_list[their_battle_army].num_auxillaries;
    count_mercs        = army_list[their_battle_army].num_horse;
    count_archers      = army_list[their_battle_army].num_specials;

    if (battle_scale == 4) { bat_size_front = 0x500; bat_size_middle = 0x640; bat_size_merc = 0x1e0; bat_size_arch = 0xa0; }
    else if (battle_scale == 3) { bat_size_front = 0x280; bat_size_middle = 0x320; bat_size_merc = 0xf0; bat_size_arch = 0x50; }
    else if (battle_scale == 2) { bat_size_front = 0x140; bat_size_middle = 0x190; bat_size_merc = 0x78; bat_size_arch = 0x28; }
    else if (battle_scale == 1) { bat_size_front = 0xa0; bat_size_middle = 0xc8; bat_size_merc = 0x3c; bat_size_arch = 0x14; }
    else { bat_size_front = 0x50; bat_size_middle = 0x64; bat_size_merc = 0x1e; bat_size_arch = 0xa; }

    bat_tribe = army_list[their_battle_army].tribe_id;
    tbs_front_quirk  = tribe_battle_setup[bat_tribe].u.raw[0];
    tbs_middle_figure = tribe_battle_setup[bat_tribe].u.raw[1];
    tbs_rear_figure   = tribe_battle_setup[bat_tribe].u.raw[2];
    tbs_flank_quirk   = tribe_battle_setup[bat_tribe].u.raw[3];
    tbs_front_kind    = tribe_battle_setup[bat_tribe].u.raw[4];
    tbs_middle_kind   = tribe_battle_setup[bat_tribe].u.raw[5];
    tbs_rear_kind     = tribe_battle_setup[bat_tribe].u.raw[6];

    if (tribe_ai_data[bat_tribe].no_flanks == 0) {
        bat_enemy_left_flank_unit = bat_enemy_right_flank_unit = 1;
    }
    if (tribe_ai_data[bat_tribe].no_fans == 0) {
        bat_enemy_first_fan_unit = bat_enemy_second_fan_unit = 1;
    }

    bat_which = 0; bat_spacing = 3; bat_side = 1; bat_control = 0;

    if (their_battle_stance != 0) find_attack_spot();
    else find_defensive_spot();

    front_quirk = (tbs_front_quirk == 0xd);
    rear_quirk  = (tbs_flank_quirk >= 9);
    made = 0;

    /* ---- Stage 1: front rank ---- */
    while (bat_size_front / 10 <= count_heavy_front) {
        if (tbs_front_kind == 2) fig_a = figure5_data;
        else if (tbs_front_kind == 3) fig_a = figure6_data;
        else fig_a = figure4_data;
        if (bat_size_front <= count_heavy_front) build_units_figures(made++, tbs_middle_figure, 3, 0, 0, their_battle_stance, army_list[their_battle_army].morale, bat_size_front, 2, 1, fig_a, 0, tbs_front_kind + 3);
        else build_units_figures(made++, tbs_middle_figure, 3, 0, 0, their_battle_stance, army_list[their_battle_army].morale, count_heavy_front, 2, 1, fig_a, 0, tbs_front_kind + 3);
        if (bat_size_front <= count_heavy_front) count_heavy_front -= bat_size_front; else count_heavy_front = 0;
    }

    /* ---- Stage 2: middle rank ---- */
    while (bat_size_middle / 10 <= count_heavy_middle) {
        if (tbs_middle_kind == 2) fig_a = figure5_data;
        else if (tbs_middle_kind == 3) fig_a = figure6_data;
        else fig_a = figure4_data;
        if (bat_size_middle <= count_heavy_middle) build_units_figures(made++, tbs_rear_figure, 2, 0, 1, their_battle_stance, army_list[their_battle_army].morale, bat_size_middle, 2, 1, fig_a, 0, tbs_middle_kind + 3);
        else build_units_figures(made++, tbs_rear_figure, 2, 0, 1, their_battle_stance, army_list[their_battle_army].morale, count_heavy_middle, 2, 1, fig_a, 0, tbs_middle_kind + 3);
        if (bat_size_middle <= count_heavy_middle) count_heavy_middle -= bat_size_middle; else count_heavy_middle = 0;
    }

    /* ---- Stage 3: rear rank ---- */
    while (bat_size_middle / 10 <= count_heavy_rear) {
        if (tbs_rear_kind == 2) fig_a = figure5_data;
        else if (tbs_rear_kind == 3) fig_a = figure6_data;
        else fig_a = figure4_data;
        if (bat_size_middle <= count_heavy_rear) build_units_figures(made++, tbs_flank_quirk, 2, rear_quirk, 2, their_battle_stance, army_list[their_battle_army].morale, bat_size_middle, 2, 1, fig_a, 0, tbs_rear_kind + 3);
        else build_units_figures(made++, tbs_flank_quirk, 2, rear_quirk, 2, their_battle_stance, army_list[their_battle_army].morale, count_heavy_rear, 2, 1, fig_a, 0, tbs_rear_kind + 3);
        if (bat_size_middle <= count_heavy_rear) count_heavy_rear -= bat_size_middle; else count_heavy_rear = 0;
    }

    /* ---- Stage 4: mercenary cavalry ---- */
    while (bat_size_merc / 10 <= count_mercs) {
        if (count_mercs >= bat_size_merc) build_units_figures(made++, tbs_front_quirk, 0, front_quirk, 3, their_battle_stance, army_list[their_battle_army].morale, bat_size_merc, 1, 1, figure4_data, figure5_data, 4);
        else build_units_figures(made++, tbs_front_quirk, 0, front_quirk, 3, their_battle_stance, army_list[their_battle_army].morale, count_mercs, 1, 1, figure4_data, figure5_data, 4);
        if (count_mercs >= bat_size_merc) count_mercs -= bat_size_merc; else count_mercs = 0;
    }

    /* ---- Stage 5: archers ---- */
    while (bat_size_arch / 5 <= count_archers) {
        if (count_archers >= bat_size_arch) build_units_figures(made++, 0xf, 2, 0, 4, their_battle_stance, army_list[their_battle_army].morale, bat_size_arch, 1, 2, figure4_data, 0, 4);
        else build_units_figures(made++, 0xf, 2, 0, 4, their_battle_stance, army_list[their_battle_army].morale, 5, 1, 2, figure4_data, 0, 4);
        if (count_archers >= bat_size_arch) count_archers -= bat_size_arch; else count_archers = 0;
    }
}

// FUNCTION: C2 0x4C9C0
// WIN: 0x00475835
// Lines 854–882
//
// Re-tally per-rank HP totals into each side's army_list
// record.  The five 32-bit buckets at army_list[+0x76, +0x7A,
// +0x7E, +0x82, +0x86] hold cumulative HP (figure_rec[+0x33])
// split by rank (figure_rec.figure_rank, +0x47):
//
//      rank 4 → army[+0x86]    (leaders / centurions — the
//                                gating value for the global
//                                count of "centuries left")
//      rank 3 → army[+0x76]
//      rank 2 → army[+0x7A]
//      rank 1 → army[+0x7E]
//      rank 0 → army[+0x82]
//
// Side selection: figure_rec.owner (fig[+1]) != 0 routes to
// our_battle_army; zero routes to their_battle_army.
//
// After accumulation, army[+0x8A] is the grand total
// (sum of the five buckets); this is the men-count read by
// setup_battle's battle_scale picker.
void get_battle_centuries_left(void)
{

    army_list[our_battle_army].num_specials = 0; army_list[our_battle_army].num_horse = 0; army_list[our_battle_army].num_regulars = 0; army_list[our_battle_army].num_irregulars = 0; army_list[our_battle_army].num_auxillaries = 0;
    army_list[their_battle_army].num_specials = 0; army_list[their_battle_army].num_horse = 0; army_list[their_battle_army].num_regulars = 0; army_list[their_battle_army].num_irregulars = 0; army_list[their_battle_army].num_auxillaries = 0;

    for (temp_figure = 1; temp_figure < 0xc9; temp_figure++) {
        if (figure_list[temp_figure].exists == 0) continue;

        if (figure_list[temp_figure].owner != 0) {

            if (figure_list[temp_figure].figure_rank == 4)      army_list[our_battle_army].num_specials    += figure_list[temp_figure].stampede_flag;
            else if (figure_list[temp_figure].figure_rank == 3) army_list[our_battle_army].num_horse       += figure_list[temp_figure].stampede_flag;
            else if (figure_list[temp_figure].figure_rank == 0) army_list[our_battle_army].num_regulars    += figure_list[temp_figure].stampede_flag;
            else if (figure_list[temp_figure].figure_rank == 1) army_list[our_battle_army].num_irregulars  += figure_list[temp_figure].stampede_flag;
            else if (figure_list[temp_figure].figure_rank == 2) army_list[our_battle_army].num_auxillaries += figure_list[temp_figure].stampede_flag;
        }
        else {

            if (figure_list[temp_figure].figure_rank == 4)      army_list[their_battle_army].num_specials    += figure_list[temp_figure].stampede_flag;
            else if (figure_list[temp_figure].figure_rank == 3) army_list[their_battle_army].num_horse       += figure_list[temp_figure].stampede_flag;
            else if (figure_list[temp_figure].figure_rank == 0) army_list[their_battle_army].num_regulars    += figure_list[temp_figure].stampede_flag;
            else if (figure_list[temp_figure].figure_rank == 1) army_list[their_battle_army].num_irregulars  += figure_list[temp_figure].stampede_flag;
            else if (figure_list[temp_figure].figure_rank == 2) army_list[their_battle_army].num_auxillaries += figure_list[temp_figure].stampede_flag;
        }
    }

    army_list[our_battle_army].total_troops = army_list[our_battle_army].num_auxillaries + army_list[our_battle_army].num_irregulars + army_list[our_battle_army].num_regulars + army_list[our_battle_army].num_horse + army_list[our_battle_army].num_specials;
    army_list[their_battle_army].total_troops = army_list[their_battle_army].num_auxillaries + army_list[their_battle_army].num_irregulars + army_list[their_battle_army].num_regulars + army_list[their_battle_army].num_horse + army_list[their_battle_army].num_specials;
}

// FUNCTION: C2 0x4CBD9
// WIN: 0x00475e2d
// Lines 884–904
//
// Compute the battle-odds rating into bat_odds (+5 = we vastly
// outnumber them, 0 = roughly equal, -5 = they vastly outnumber us)
// from their_battle_men and our_battle_men, then — unless
// tune_mood_hold is set — fold that into tune_mood (1..5).
void get_battle_odds(void)
{
    if      (their_battle_men * 4 < our_battle_men)                      bat_odds =  5;
    else if (their_battle_men * 3 < our_battle_men)                      bat_odds =  4;
    else if (their_battle_men * 2 < our_battle_men)                      bat_odds =  3;
    else if (their_battle_men + their_battle_men / 2 < our_battle_men)   bat_odds =  2;
    else if (their_battle_men + their_battle_men / 4 < our_battle_men)   bat_odds =  1;
    else if (our_battle_men   * 4 < their_battle_men)                    bat_odds = -5;
    else if (our_battle_men   * 3 < their_battle_men)                    bat_odds = -4;
    else if (our_battle_men   * 2 < their_battle_men)                    bat_odds = -3;
    else if (our_battle_men   + our_battle_men   / 2 < their_battle_men) bat_odds = -2;
    else if (our_battle_men   + our_battle_men   / 4 < their_battle_men) bat_odds = -1;
    else                                                                 bat_odds =  0;

    if (tune_mood_hold != 0) return;

    if      (bat_odds >=  4) tune_mood = 5;
    else if (bat_odds >=  2) tune_mood = 4;
    else if (bat_odds <= -4) tune_mood = 3;
    else if (bat_odds <= -2) tune_mood = 2;
    else                     tune_mood = 1;
}

// FUNCTION: C2 0x4CD76
// WIN: 0x0047605c
// Lines 909–998
//
// Place one unit's worth of figures on the battle map.  Called
// from setup_roman_units (4 stages) and setup_enemy_units
// (5 stages); both pre-compute the men chunk and slot context.
//
// Seeds the RNG, derives bat_size from target_men / a
// battle_scale divisor (5..0x50), shrinks the column count down
// when there are too few men to fill the requested grid, picks a
// start point via get_start_points, and creates the unit via
// create_unit().  Morale is then derived from the player byte
// (×10 + 0x32) and biased ± bat_odds*5 by bat_control, clamped
// to [0x19, 0x64].  Subsequent stores stamp every per-unit
// constant (sub-kind, formation width, stance slot, anim seed
// per figure, weapon/armour fields, missile range, AI period)
// and drop each figure onto its formation slot via
// get_fig_in_unit_position.
void build_units_figures(int made, int kind, int sub_kind, int sub_kind2,
                         int slot, int stance, int player, int target_men,
                         int cols, int row_count, unsigned char *fig_a,
                         unsigned char *fig_b, int stage_slot)
{
    signed char extra;
    int i;

    random();

    if      (battle_scale == 4) bat_size = target_men / 0x50;
    else if (battle_scale == 3) bat_size = target_men / 0x28;
    else if (battle_scale == 2) bat_size = target_men / 0x14;
    else if (battle_scale == 1) bat_size = target_men / 0xa;
    else                        bat_size = target_men / 5;

    if (bat_size < 0xf && cols == 4) cols = 3;
    if (bat_size < 0xa && cols == 3) cols = 2;
    if (bat_size < 5   && cols == 2) cols = 1;

    bat_width = bat_size / cols * row_count;

    get_start_points(made);
    create_unit(kind, x, y, bat_control);

    unit_list[created_unit_no].morale_a = player * 10 + 0x32;
    extra = sub_kind;
    unit_list[created_unit_no].unit_sub_kind = sub_kind2;
    unit_list[created_unit_no].stage_slot = stance; extra = bat_odds * 5;
    if (bat_control != 0) unit_list[created_unit_no].morale_a += extra;
    else unit_list[created_unit_no].morale_a -= extra;
    if (unit_list[created_unit_no].morale_a >= 0x64) unit_list[created_unit_no].morale_a = 0x64;
    if (unit_list[created_unit_no].morale_a < 0x19) unit_list[created_unit_no].morale_a = 0x19;
    unit_list[created_unit_no].morale_b = unit_list[created_unit_no].morale_a;
    unit_list[created_unit_no].formation_width = bat_width;
    unit_list[created_unit_no].formation_cols = cols;
    unit_list[created_unit_no]._init32 = 1;
    unit_list[created_unit_no].formation_mode = 0;
    unit_list[created_unit_no].heading = bat_side;
    unit_list[created_unit_no].start_men = target_men; unit_list[created_unit_no].current_men = target_men;
    if (bat_control != 0) unit_list[created_unit_no].ai_period = 0;
    else {
        unit_list[created_unit_no].ai_period = bat_ai_trig_count;
        bat_ai_trig_count += (rand128 & 7) + 6;
    }
    unit_list[created_unit_no].ai_tick = 0;
    unit_list[created_unit_no].unit_rank = slot;

    /* Enemy flank/fan dispatch (only when bat_control == 0 and slot == 1). */
    if (bat_control == 0 && slot == 1) {
        if (bat_enemy_left_flank_unit == 0 && x <= 0x1a) {
            unit_list[created_unit_no].flank_pending = 1; bat_enemy_left_flank_unit = slot;
        }
        if (bat_enemy_right_flank_unit == 0 && x > 0x1a) {
            unit_list[created_unit_no].flank_pending = 2; bat_enemy_right_flank_unit = 1;
        }
        if (unit_list[created_unit_no].flank_pending == 0) {
            if (bat_enemy_first_fan_unit == 0) {
                unit_list[created_unit_no].flank_pending = 4; bat_enemy_first_fan_unit = 1;
            } else if (bat_enemy_second_fan_unit == 0) {
                unit_list[created_unit_no].flank_pending = 3; bat_enemy_second_fan_unit = 1;
            }
        }
    }

    /* Figure loop: esi runs 0..bat_size-1. */
    for (i = 0; i < bat_size; i++) {
        random();
        x_bit = get_x_spacing(row_count, cols, i);
        y_bit = get_y_spacing(row_count, cols, i, bat_side);

        if (create_figure(kind, x, x_bit, y, y_bit, bat_control,
                          created_unit_no) == 0)
            break;

        figure_list[created_figure_no].state_idx     = 6;
        figure_list[created_figure_no].unit_position = bat_side;
        figure_list[created_figure_no].figure_rank   = slot;
        figure_list[created_figure_no].unit_grid_x   = row_count;
        figure_list[created_figure_no].unit_grid_y   = cols;
        figure_list[created_figure_no].fight_swing_active = sub_kind2;

        if (bat_control == 0) figure_list[created_figure_no].morale = tribe_ai_data[bat_tribe].aggression;
        if (figure_list[created_figure_no].figure_rank == 1) figure_list[created_figure_no].morale = figure_list[created_figure_no].morale / 2;
        if (figure_list[created_figure_no].figure_rank == 2) figure_list[created_figure_no].morale = 0;

        figure_list[created_figure_no].stampede_kind = sub_kind;
        figure_list[created_figure_no].is_defending = 1;
        figure_list[created_figure_no].shield_class = 0;

        if      (battle_scale == 0) figure_list[created_figure_no].stampede_flag = 5;
        else if (battle_scale == 1) figure_list[created_figure_no].stampede_flag = 0xa;
        else if (battle_scale == 2) figure_list[created_figure_no].stampede_flag = 0x14;
        else if (battle_scale == 3) figure_list[created_figure_no].stampede_flag = 0x28;
        else if (battle_scale == 4) figure_list[created_figure_no].stampede_flag = 0x50;

        figure_list[created_figure_no].arrow_data_ptr = fig_a;
        figure_list[created_figure_no].sprite_data_ptr = fig_b;
        figure_list[created_figure_no].sprite_kind = stage_slot;

        if (fig_b != 0) figure_list[created_figure_no].fight_state = 1;
        else if (kind == 0xf) figure_list[created_figure_no].fight_state = 2;
        figure_list[created_figure_no].missile_timer = rand128 & 0x1f;

        if (i == 0) unit_list[created_unit_no].first_figure = created_figure_no;
        unit_list[created_unit_no].fig_count++;
    }

    unit_list[created_unit_no].last_figure = created_figure_no;
}

// FUNCTION: C2 0x4D272
// WIN: 0x004769af
// Lines 1001–1037
//
// Re-point every live figure's and arrow's sprite-data
// pointers (figure_rec[+0x0A] primary, [+0x0E] secondary;
// arrow_rec[+0x08]) at the currently-loaded figureN_data
// globals.  Called whenever the zoom level or active map
// changes (act_zoom_level1, act_correct_map) so the sprite
// indirection tables match the freshly-paged sprite resources.
//
// Per-figure: skip if exists==0; switch on type at [+0x26]:
//   1–3, 5–6 → single-sheet types, only [+0x0A] re-pointed
//   4         → [+0x0A]=figure4_data; if [+0x0E] non-null
//               also → figure5_data
//   7         → [+0x0A]=figure7_data; if [+0x0E] non-null
//               also → figure8_data
//
// Per-arrow (45-byte stride, idx*45): skip if exists==0
// (offset +0x23); switch on type at +0x1B; map types 1–8
// onto figureN_data → arrow_rec[+0x08].
void rebuild_figures_image_data(void)
{
    unsigned char *fig;
    unsigned char *arr;
    int type;

    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists == 0) continue;
        type = figure_list[figure_no].sprite_kind;
        if (type == 7) {
            figure_list[figure_no].arrow_data_ptr = figure7_data;
            if (figure_list[figure_no].sprite_data_ptr != 0)
                figure_list[figure_no].sprite_data_ptr = figure8_data;
        } else if (type == 1) {
            figure_list[figure_no].arrow_data_ptr = figure1_data;
        } else if (type == 2) {
            figure_list[figure_no].arrow_data_ptr = figure2_data;
        } else if (type == 3) {
            figure_list[figure_no].arrow_data_ptr = figure3_data;
        } else if (type == 4) {
            figure_list[figure_no].arrow_data_ptr = figure4_data;
            if (figure_list[figure_no].sprite_data_ptr != 0)
                figure_list[figure_no].sprite_data_ptr = figure5_data;
        } else if (type == 5) {
            figure_list[figure_no].arrow_data_ptr = figure5_data;
        } else if (type == 6) {
            figure_list[figure_no].arrow_data_ptr = figure6_data;
        }
    }

    for (arrow_no = 1; arrow_no < 0xc9; arrow_no++) {
        if (arrow_list[arrow_no].exists == 0) continue;
        type = arrow_list[arrow_no].sprite_kind;
        if (type == 1) arrow_list[arrow_no].arrow_data_ptr = figure1_data;
        else if (type == 2) arrow_list[arrow_no].arrow_data_ptr = figure2_data;
        else if (type == 3) arrow_list[arrow_no].arrow_data_ptr = figure3_data;
        else if (type == 4) arrow_list[arrow_no].arrow_data_ptr = figure4_data;
        else if (type == 5) arrow_list[arrow_no].arrow_data_ptr = figure5_data;
        else if (type == 6) arrow_list[arrow_no].arrow_data_ptr = figure6_data;
        else if (type == 7) arrow_list[arrow_no].arrow_data_ptr = figure7_data;
        else if (type == 8) arrow_list[arrow_no].arrow_data_ptr = figure8_data;
    }
}

// FUNCTION: C2 0x4D404
// WIN: 0x00476d34
// Lines 1041–1047
//
// Initialise the three Roman formation lanes for an attack order.
// Each lane starts unused (first_* = 1) and centred at x=0x1a;
// the y lanes depend on bat_side.  Note: in the bat_side == -1 arm
// yback is written twice (0xe then 0xa), leaving yrear untouched —
// an original-game bug, preserved here.
void find_attack_spot(void)
{
    first_rear = 1;
    first_back = 1;
    first_front = 1;
    xright_rear = 0x1a;
    xleft_rear = 0x1a;
    xright_back = 0x1a;
    xleft_back = 0x1a;
    xright_front = 0x1a;
    xleft_front = 0x1a;
    if (bat_side == -1) {
        yfront = 0x12;
        yback = 0xe;
        yback = 0xa;
    } else {
        yfront = 0x22;
        yback = 0x26;
        yrear = 0x2a;
    }
}

// FUNCTION: C2 0x4D491
// WIN: 0x00476de7
// Lines 1049–1055
//
// Defensive formation initialiser: same x/first reset as attack,
// but y lanes are set one band deeper/shallower depending on side.
void find_defensive_spot(void)
{
    first_rear = 1;
    first_back = 1;
    first_front = 1;
    xright_rear = 0x1a;
    xleft_rear = 0x1a;
    xright_back = 0x1a;
    xleft_back = 0x1a;
    xright_front = 0x1a;
    xleft_front = 0x1a;
    if (bat_side == -1) {
        yfront = 0xe;
        yback = 0xa;
        yrear = 6;
    } else {
        yfront = 0x26;
        yback = 0x2a;
        yrear = 0x2e;
    }
}

// FUNCTION: C2 0x4D51E
// WIN: 0x00476e9a
// Lines 1057–1103
//
// Pick the next (x, y) deployment slot for a unit being
// placed on the battle map.  Reads the per-unit row/anchor
// hint from attack_pos_data[idx]:
//   xpos: 0 = left, 1 = right (which edge to grow from)
//   ypos: 0 = front row, 1 = back row, 2 = rear row
//
// On the first placement into a row (first_{front,back,rear}
// still set), seed x = xleft_<row>, y = y<row> and grow
// xright_<row> rightward.  Subsequent placements:
//   * xpos == 1:   x = xright_<row>; grow xright_<row>
//   * xpos == 0:   xleft_<row> -= step; x = xleft_<row>
// where step = bat_width + bat_spacing.
//
// If the chosen edge would overflow the field (xright +
// width >= 0x34 with xpos == 1, or xleft - step < 0 with
// xpos == 0), the orientation is flipped.
void get_start_points(int idx)
{
    xpos = attack_pos_data[idx].xpos;
    ypos = attack_pos_data[idx].ypos;

    if (ypos == 0 && first_front != 0) {
        first_front = 0;
        x = xleft_front;
        y = yfront;
        xright_front += bat_width + bat_spacing;
        return;
    }
    if (ypos == 1 && first_back != 0) {
        first_back = 0;
        x = xleft_back;
        y = yback;
        xright_back += bat_width + bat_spacing;
        return;
    }
    if (ypos == 2 && first_rear != 0) {
        first_rear = 0;
        x = xleft_rear;
        y = yrear;
        xright_rear += bat_width + bat_spacing;
        return;
    }

    if (ypos == 0) {
        y = yfront;
        if (xpos == 1 && xright_front + bat_width >= 0x34) xpos = 0;
        else if (xpos == 0 && xleft_front - bat_width - bat_spacing < 0) xpos = 1;
        if (xpos == 1) {
            x = xright_front;
            xright_front += bat_width + bat_spacing;
        } else {
            x = xleft_front - bat_width - bat_spacing;
            xleft_front = x;
        }
    } else if (ypos == 1) {
        y = yback;
        if (xpos == 1 && xright_back + bat_width >= 0x34) xpos = 0;
        else if (xpos == 0 && xleft_back - bat_width - bat_spacing < 0) xpos = 1;
        if (xpos == 1) {
            x = xright_back;
            xright_back += bat_width + bat_spacing;
        } else {
            x = xleft_back - bat_width - bat_spacing;
            xleft_back = x;
        }
    } else { /* ypos == 2 */
        y = yrear;
        if (xpos == 1 && xright_rear + bat_width >= 0x34) xpos = 0;
        else if (xpos == 0 && xleft_rear - bat_width - bat_spacing < 0) xpos = 1;
        if (xpos == 1) {
            x = xright_rear;
            xright_rear += bat_width + bat_spacing;
        } else {
            x = xleft_rear - bat_width - bat_spacing;
            xleft_rear = x;
        }
    }
}

// FUNCTION: C2 0x4D7D3
// WIN: 0x004771f6  (unverified)
// Lines 1105–1111
//
// Battle-grid x-spacing helper: given the troop count `p1`,
// the troop-rank order `p2`, and the figure index `p3`,
// return the x-offset of figure `p3` within its rank.
//
// Returns `(p3 / divisor) * p1` where divisor depends on p2:
//
//   p2 <= 1  → divisor = 1 (single rank — each figure has
//                            its own column)
//   p2 == 2  → divisor = 2 (two-deep rows)
//   p2 == 3  → divisor = 3
//   p2 >= 4  → divisor = 4 (four-deep rows max)
//
// Sister of get_y_spacing; used by build_units_figures and
// get_fig_in_unit_position.
int get_x_spacing(int p1, int p2, int p3)
{
    if (p2 <= 1)
        return p3 * p1;
    if (p2 <= 2)
        return (p3 / 2) * p1;
    if (p2 <= 3)
        return (p3 / 3) * p1;
    return (p3 / 4) * p1;
}

// FUNCTION: C2 0x4D821
// WIN: 0x0047726b  (unverified)
// Lines 1113–1119
//
// Battle-grid spacing helper: given the troop count `p1`,
// the troop-rank order `p2`, the figure index `p3`, and the
// per-formation tier multiplier `p4`, return the y-offset
// of figure `p3` within its rank.
//
// The figure-spacing pattern is `(p3 % divisor) * p1 * p4`,
// where divisor is set by `p2`:
//
//   p2 <= 1  → 0           (single-rank — no spacing needed)
//   p2 == 2  → divisor = 2 (two ranks)
//   p2 == 3  → divisor = 3 (three ranks)
//   p2 >= 4  → divisor = 4 (four ranks max)
//
// Used by build_units_figures and get_fig_in_unit_position.
int get_y_spacing(int p1, int p2, int p3, int p4)
{
    int divisor;
    int q;

    if (p2 <= 1)
        return p3 ^ p3;   /* zero via xor-self */
    if (p2 <= 2)
        divisor = 2;
    else if (p2 <= 3)
        divisor = 3;
    else
        divisor = 4;
    q = p3 % divisor;
    q *= p1;
    q *= p4;
    return q;
}

// FUNCTION: C2 0x4D861
// WIN: 0x004772f2
// Lines 1123–1146
//
// Per-tick map-refresh pass over every figure in figure_list.
// Counts the live figures into no_of_figures, then for each
// stamps its battle_map footprint via set_figure_map_refresh so
// subsequent renderers know which cells changed.  Each call
// paints the cell the figure sits on at footprint size 3 (priests)
// or 2 (everyone else), plus a diagonal trailing-motion stamp
// keyed off map_direction (±size on each axis for the four even
// directions, skipped otherwise).  Selected figures also flip
// their cell's dirty bit so the highlight overlay repaints, with
// a special pointer_mode == 2 path that propagates a parent-unit
// deselect back down to the figure.
void figure_update(void)
{
    int e;
    int d;

    no_of_figures = 0;

    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists != 0) {
            no_of_figures++;
            if (figure_list[figure_no].sprite_type == 0xf) {
                e = 3;
                d = 3;
            } else if (figure_list[figure_no].fight_state != 0) {
                e = 2;
                d = 2;
            } else {
                e = 2;
                d = 2;
            }
            set_figure_map_refresh(figure_list[figure_no].grid_x,
                                   figure_list[figure_no].grid_y,
                                   0, 0, e, 0);

            if (map_direction == 0)
                set_figure_map_refresh(figure_list[figure_no].grid_x,
                                       figure_list[figure_no].grid_y,
                                       -d, -d, d, 1);
            else if (map_direction == 2)
                set_figure_map_refresh(figure_list[figure_no].grid_x,
                                       figure_list[figure_no].grid_y,
                                        d, -d, d, 1);
            else if (map_direction == 4)
                set_figure_map_refresh(figure_list[figure_no].grid_x,
                                       figure_list[figure_no].grid_y,
                                        d,  d, d, 1);
            else if (map_direction == 6)
                set_figure_map_refresh(figure_list[figure_no].grid_x,
                                       figure_list[figure_no].grid_y,
                                       -d,  d, d, 1);

            if (figure_list[figure_no].selected != 0) {
                temp_unit = (short)figure_list[figure_no].unit_ref;
                if (pointer_mode == 2 && unit_list[temp_unit].unit_sub_kind == 0) {
                    figure_list[figure_no].selected = 0;
                } else {
                    ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 2] |= 4;
                }
            }
        }
    }
}

// FUNCTION: C2 0x4DA05
// WIN: 0x0047763d
// Lines 1148–1159
//
// Per-tick arrow cleanup pass: for every live arrow (arrow_no 1..0xc8
// with exists != 0), clear the +3 byte of its map_ref'd battle_map
// cell ("arrow occupancy" flag) and queue a 3x3 figure-map refresh
// around the arrow's last grid_(x,y).  The +/- 2 deltas passed to
// set_figure_map_refresh select the rectangle's two diagonal corners;
// their signs depend on which view orientation map_direction encodes
// (0/2/4/6 = N/E/S/W).  Other orientations (or arrows already cleared)
// just advance to the next slot.
void arrow_update(void)
{
    for (arrow_no = 1; arrow_no < 0xc9; arrow_no++) {
        if (arrow_list[arrow_no].exists != 0) {
            ((unsigned char *)battle_map)[(arrow_list[arrow_no].map_ref) + 3] = 0;
            if (map_direction == 0)
                set_figure_map_refresh(arrow_list[arrow_no].grid_x,
                                       arrow_list[arrow_no].grid_y,
                                       -2, -2, 2, 1);
            else if (map_direction == 2)
                set_figure_map_refresh(arrow_list[arrow_no].grid_x,
                                       arrow_list[arrow_no].grid_y,
                                        2, -2, 2, 1);
            else if (map_direction == 4)
                set_figure_map_refresh(arrow_list[arrow_no].grid_x,
                                       arrow_list[arrow_no].grid_y,
                                        2,  2, 2, 1);
            else if (map_direction == 6)
                set_figure_map_refresh(arrow_list[arrow_no].grid_x,
                                       arrow_list[arrow_no].grid_y,
                                       -2,  2, 2, 1);
        }
    }
}

// FUNCTION: C2 0x4DAE8
// WIN: 0x004777c2
// Lines 1161–1171
//
// Per-tick figure update loop (118 b, L1161–1171).
// Walks figure_list[1..200], for each populated entry:
//
//   1. Decrement field +0x4E (a per-figure tick counter)
//      unless it's already 0.
//   2. Read .sprite_type.  If 0 < sprite_type < 18 it's a
//      valid figure-class index — dispatch via the
//      `figure_intelligences[]` function-pointer table.
//      Otherwise (<= 0 or >= 18), remove_figure.
//
// Mirrors `figure_update`'s walk; this one runs the AI
// state machine while figure_update advances animation.
void figure_intelligence(void)
{
    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists != 0) {
            if (figure_list[figure_no].engaged_count != 0) {
                figure_list[figure_no].engaged_count--;
            }
            if (figure_list[figure_no].sprite_type <= 0
             || figure_list[figure_no].sprite_type >= 0x12) {
                remove_figure(figure_no);
            } else {
                figure_intelligences[figure_list[figure_no].sprite_type]();
            }
        }
    }
}

// FUNCTION: C2 0x4DB5E
// WIN: 0x004778bf
// Lines 1173–1176
//
// Refresh the still-frame sprite for every populated figure.
// Same loop shape as select_all_figures / deselect_enemy_figures.
void figure_images(void)
{
    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists != 0) {
            get_fig_still_image();
        }
    }
}

// FUNCTION: C2 0x4DB8F
// WIN: 0x0047791a  (unverified)
// Lines 1177–1177
//
// Battle-frame slot 00: no-op.  Some battle frame handlers
// are explicitly empty placeholders.
void f00_null(void)
{
}

// FUNCTION: C2 0x4DB90
// WIN: 0x00477925
// Lines 1180–1180
//
// Per-figure-type init: sets the figure's `anim_kind` /
// `sub_state` pair and immediately tail-calls the current
// state handler in `figure_states[]`.  Every f0?_* / f1?_*
// variant follows this shape, differing only in the two
// byte constants.
void f01_regular(void)
{
    figure_list[figure_no].anim_kind = 0xf;
    figure_list[figure_no].sub_state = 3;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DBAA
// WIN: 0x0047797c
// Lines 1185–1185
//
// Irregular-troop figure-state init (anim_kind = 0xa, sub_state = 2).
void f02_irregular(void)
{
    figure_list[figure_no].anim_kind = 0xa;
    figure_list[figure_no].sub_state = 2;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DBC4
// WIN: 0x004779d3  (unverified)
// Lines 1190–1190
//
// Auxiliary-troop figure-state init (anim_kind = 4, sub_state = 1).
// f09_barb_javalin, f10_barb_sling and f17_barb_knife share this
// body verbatim and are defined below at their own numeric slots.
void f03_auxillary(void)
{
    figure_list[figure_no].anim_kind = 4;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DBEA
//
// Empty state-handler slot in `figure_states[]` (state_idx 0).
void sf00_null(void)
{
}

// FUNCTION: C2 0x4DBEB
// WIN: 0x00477a2a
// Lines 1195–1195
//
// Same shape as f01_regular — only the anim_kind / sub_state
// constants differ.
void f05_barb_sword(void)
{
    figure_list[figure_no].anim_kind = 0xe;
    figure_list[figure_no].sub_state = 3;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DBFE
// WIN: 0x00477a81
// Lines 1200–1200
//
// Barbarian-spear figure-state init (anim_kind = 0xc, sub_state = 2).
void f06_barb_spear(void)
{
    figure_list[figure_no].anim_kind = 0xc;
    figure_list[figure_no].sub_state = 2;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DC11
// WIN: 0x00477ad8
// Lines 1205–1205
//
// Barbarian-axe figure-state init (anim_kind = 0x10, sub_state = 1).
void f07_barb_axe(void)
{
    figure_list[figure_no].anim_kind = 0x10;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DC24
// WIN: 0x00477b2f
// Lines 1210–1210
//
// Barbarian-pike figure-state init (anim_kind = 0xa, sub_state = 5).
void f08_barb_pike(void)
{
    figure_list[figure_no].anim_kind = 0xa;
    figure_list[figure_no].sub_state = 5;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DBC4
// WIN: 0x004779d3  (unverified)
//
// Barbarian-javelin figure-state init.  Body identical to f03_auxillary.
void f09_barb_javalin(void)
{
    figure_list[figure_no].anim_kind = 4;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DBC4
// WIN: 0x004779d3  (unverified)
//
// Barbarian-sling figure-state init.  Body identical to f03_auxillary.
void f10_barb_sling(void)
{
    figure_list[figure_no].anim_kind = 4;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DC3E
// WIN: 0x00477c34
// Lines 1225–1225
//
// Heavy barbarian-cavalry figure-state init (anim_kind = 0x10, sub_state = 5).
void f11_barb_horse_heavy(void)
{
    figure_list[figure_no].anim_kind = 0x10;
    figure_list[figure_no].sub_state = 5;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DC51
// WIN: 0x00477c8b  (unverified)
// Lines 1230–1230
//
// Light barbarian-cavalry figure-state init (anim_kind = 0xe,
// sub_state = 4).  f13_barb_horse_archer and f14_barb_camel share
// this body verbatim and are defined below at their own numeric slots.
void f12_barb_horse_light(void)
{
    figure_list[figure_no].anim_kind = 0xe;
    figure_list[figure_no].sub_state = 4;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DC51
// WIN: 0x00477ce2  (unverified)
//
// Mounted-archer figure-state init.  Body identical to f12_barb_horse_light.
void f13_barb_horse_archer(void)
{
    figure_list[figure_no].anim_kind = 0xe;
    figure_list[figure_no].sub_state = 4;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DC51
// WIN: 0x00477d39
//
// Camel-rider figure-state init.  Body identical to f12_barb_horse_light.
void f14_barb_camel(void)
{
    figure_list[figure_no].anim_kind = 0xe;
    figure_list[figure_no].sub_state = 4;
    figure_states[figure_list[figure_no].state_idx]();
}


// FUNCTION: C2 0x4DC6E
// WIN: 0x00477d90
// Lines 1247–1250
//
// Same shape as f01_regular et al — sets anim_kind/sub_state
// then tail-calls figure_states[state_idx].
void f15_barb_elephant(void)
{
    figure_list[figure_no].anim_kind = 0x14;
    figure_list[figure_no].sub_state = 6;
    figure_states[figure_list[figure_no].state_idx]();
    elephant_fire();
}

// FUNCTION: C2 0x4DCCA
// WIN: 0x00477dec
// Lines 1254–1254
//
// Same shape as f17_barb_knife.
void f16_barb_bow(void)
{
    figure_list[figure_no].anim_kind = 5;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DBC4
// WIN: 0x004779d3  (unverified)
//
// Barbarian-knife figure-state init.  Body identical to f03_auxillary.
void f17_barb_knife(void)
{
    figure_list[figure_no].anim_kind = 4;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// FUNCTION: C2 0x4DCE0
// WIN: 0x00477ea5
// Lines 1267–1278
//
// Hold an idle (state-1) figure on its current frame.
// While cnt4 (the animation gate) is still ticking, just
// freeze the sprite via get_fig_still_image.  Once the
// gate clears, count down fl[+0x1B] and — when it hits 0
// — transition the figure back to its previous state by
// copying fl[+0x1A] (the saved “return” state) into
// fl[+0x1C], reset the per-tick counters, and set bit 0
// of fl[+0x24] (“has finished wait”).
void sf01_wait(void)
{
    get_fig_still_image();
    if (cnt4 != 0) return;
    if (--figure_list[figure_no].wait_counter > 0) return;

    figure_list[figure_no].wait_counter = 5;
    figure_list[figure_no].wf_step_y    = 0;
    figure_list[figure_no].wf_step_x    = 0;
    figure_list[figure_no].is_routing   = 0;
    figure_list[figure_no].state_idx    = figure_list[figure_no].next_state_idx;
    figure_list[figure_no].is_visible  &= 0xfc;
    figure_list[figure_no].is_visible  |= 1;
}

// FUNCTION: C2 0x4DD4A
// WIN: 0x00477fe7
// Lines 1280–1307
//
// Death state (state == 2).
//
// Elephants (kind 0xF) get stampede handling: stamp
// fl[+0x44]/+0x33 = 1 and re-aim toward an entry in the
// 8-pair `elephant_stampede` table (chosen via figure_no
// & 7), then sf12_rout() takes over the movement.  Once
// rout finishes one tick, run set_battle_death_fx on
// entry to dying and bump fl[+0x28]; once it exceeds
// 0x40 reset it to rand8 doubled.
//
// Non-elephants: trigger one set_battle_death_fx on the
// first tick (when fl[+0x28] is still 0), then advance
// the death sprite stepper via get_fig_death_image and
// bump fl[+0x28] toward 0x1E.  At the cap, paint a corpse
// byte over the underlying battle_map cell at fl[+0x12]
// (low-nibble clamping to keep the corpse art in the
// right palette band) and call remove_figure(figure_no).
void sf02_death(void)
{
    int kind;
    signed char cnt;
    unsigned char cell;
    unsigned char one = 1;
    int cellv;

    kind = figure_list[figure_no].sprite_type;
    if (kind == 0xf) {
        int idx;
        figure_list[figure_no].stampede_kind = one;
        figure_list[figure_no].stampede_flag = one;
        idx = figure_no & 7;
        figure_list[figure_no].prev_grid_x = elephant_stampede[idx].dx;
        figure_list[figure_no].prev_grid_y = elephant_stampede[idx].dy;
        sf12_rout();
        if (figure_list[figure_no].death_timer <= 0) {
            set_battle_death_fx(figure_list[figure_no].sprite_type);
        }
        ++figure_list[figure_no].death_timer;
        if (figure_list[figure_no].death_timer > 0x40)
            figure_list[figure_no].death_timer =
                ((unsigned char)rand8 + (unsigned char)rand8);
        return;
    }

    if (figure_list[figure_no].death_timer <= 0)
        set_battle_death_fx(kind);

    get_fig_death_image();
    ++figure_list[figure_no].death_timer;
    if (figure_list[figure_no].death_timer <= 0x1e)
        return;

    figure_list[figure_no].death_timer = 0x1e;
    cell  = (*(struct battle_cell *)((unsigned char *)battle_map + ((figure_list[figure_no].map_ref)))).terrain;
    cellv = cell;
    if (cellv < 0x28) {
        if (cellv >= 0x24) {
            cell = cell + 4;
        } else if (cellv >= 0x20) {
            cell = cell + 4;
        } else {
            cell = (unsigned char)((cell & 3) + 0x24);
        }
    }
    (*(struct battle_cell *)((unsigned char *)battle_map + ((figure_list[figure_no].map_ref)))).terrain = cell;
    remove_figure(figure_no);
}

// FUNCTION: C2 0x4DE81
// WIN: 0x00478269
// Lines 1309–1319
//
// Move state (state_idx 3): step the figure toward its current target; on arrival
// drop the routing flag and return to defend state 6.
void sf03_move(void)
{
    int moved;

    figure_list[figure_no].is_routing = 1;
    get_fig_walk_image();
    moved = figure_go_to_target();
    if (moved == 0)
        return;
    if ((figure_list[figure_no].is_visible & 2) == 0)
        return;
    figure_list[figure_no].is_visible &= 0xfd;
    figure_list[figure_no].state_idx = 6;
}

// FUNCTION: C2 0x4DECB
// WIN: 0x00478307
// Lines 1321–1331
//
// Move-and-reform state (state_idx 15): step the figure toward its current target;
// once it arrives, call reform() on its parent unit with the saved formation.
void sf15_move_and_reform(void)
{
    int moved;
    int unit_ref;
    int formation;

    figure_list[figure_no].is_routing = 1;
    get_fig_walk_image();
    moved = figure_go_to_target();
    if (moved == 0)
        return;
    if ((figure_list[figure_no].is_visible & 2) == 0)
        return;
    figure_list[figure_no].is_visible &= 0xfd;
    formation = figure_list[figure_no].shield_class;
    unit_ref  = figure_list[figure_no].unit_ref;
    reform(unit_ref, formation, 1);
}

// FUNCTION: C2 0x4DF2D
// WIN: 0x004783ca
// Lines 1333–1342
//
// Fight state (state_idx 4): if the opponent is still alive and also fighting us,
// resolve one tick of melee; otherwise fall back to look-for-fight (state 9).
void sf04_fight(void)
{
    int cond;

    figure_list[figure_no].is_routing = 0;
    get_fig_fight_image();
    enemy_figure = (short)figure_list[figure_no].opponent;
    if (figure_list[figure_list[figure_no].opponent].exists == 0) {
        figure_list[figure_no].state_idx = 9;
        return;
    }
    if (figure_list[enemy_figure].state_idx != 4) {
        figure_list[figure_no].state_idx = 9;
        return;
    }
    do_the_fight();
    cond = (figure_list[figure_no].is_visible == 0);
    if (cond)
        figure_go_to_target();
}

// FUNCTION: C2 0x4DFB7
//
// Empty state-handler slot for the "mop-up" battle state.
void sf05_mop_up(void)
{
}

// FUNCTION: C2 0x4DFB8
// WIN: 0x004784c6
// Lines 1345–1376
//
// Defend state (state == 6).  Hold position; harass any enemy in
// firing range.  If the parent unit isn't marching, just
// refresh the missile sprite and return.  Otherwise every half
// fire period acquires a fresh missile target via
// find_nearest_target(5), latches it into missile_target and
// re-aims the heading.  When the fire timer crosses the full
// period, fires an arrow (create_arrow + the standard image/
// fx/range setup) at whichever target is still alive.
void sf06_defend(void)
{
    int half;

    get_fig_still_image();
    temp_unit = (short)figure_list[figure_no].unit_ref;

    if (unit_list[figure_list[figure_no].unit_ref].unit_sub_kind != 0) {
        figure_list[figure_no].missile_max = 0x20;
        half     = figure_list[figure_no].missile_max / 2;
        figure_list[figure_no].missile_timer++;
        if (figure_list[figure_no].missile_timer == half) {
            if (find_nearest_target(5)) {
                figure_list[figure_no].missile_target = enemy_figure;
                figure_list[figure_no].direction = (char)get_heading(
                    figure_list[figure_no].grid_x,
                    figure_list[figure_no].grid_y,
                    figure_list[enemy_figure].grid_x,
                    figure_list[enemy_figure].grid_y,
                    figure_list[figure_no].direction);
            } else {
                figure_list[figure_no].missile_target = 0;
                figure_list[figure_no].missile_timer = 4;
            }
        }

        if (figure_list[figure_no].missile_timer > figure_list[figure_no].missile_max) {
            figure_list[figure_no].missile_timer = 0;
            enemy_figure = (short)figure_list[figure_no].missile_target;
            if (figure_list[enemy_figure].exists != 0) {
                create_arrow(
                    figure_list[figure_no].arrow_data_ptr,
                    figure_list[figure_no].owner,
                    figure_list[figure_no].grid_x,
                    figure_list[figure_no].grid_y,
                    figure_list[enemy_figure].grid_x,
                    figure_list[enemy_figure].grid_y);
                arrow_list[created_arrow_no].weapon_kind = figure_list[figure_no].sprite_type;
                get_arrow_base_image();
                set_missile_fire_fx(arrow_list[created_arrow_no].weapon_kind);
                set_missile_fire_range(arrow_list[created_arrow_no].weapon_kind);
            }
        }

        if (figure_list[figure_no].missile_target != 0)
            get_fig_missile_image();
    }
}

// FUNCTION: C2 0x4E1BF
// WIN: 0x00478820
// Lines 1378–1390
//
// Reform state (state_idx 7): walk the figure toward its formation slot; on arrival
// switch to defend state 6 with .is_defending set, snapping its facing to anim_state.
void sf07_reform(void)
{
    int moved;

    figure_list[figure_no].is_routing = 1;
    get_fig_walk_image();
    moved = figure_go_to_target();
    if (moved == 0)
        return;
    if ((figure_list[figure_no].is_visible & 2) == 0)
        return;
    figure_list[figure_no].is_visible   &= 0xfd;
    figure_list[figure_no].state_idx     = 6;
    figure_list[figure_no].is_defending  = 1;
    figure_list[figure_no].direction     = figure_list[figure_no].anim_state;
}

// FUNCTION: C2 0x4E21C
// WIN: 0x00478901
// Lines 1392–1414
//
// Withdraw state (state_idx 8): step the figure backward to its target tile; on
// arrival drop into defend state 6 and reset morale (halved for rank-1, zeroed for
// rank-2) based on the tribe's base morale.
void sf08_withdraw(void)
{
    int moved;
    int unit_idx;
    int slot;
    int m;

    figure_list[figure_no].is_routing   = 1;
    figure_list[figure_no].is_defending = 0;
    get_fig_walk_image();
    moved = figure_go_to_target();
    if (moved == 0)
        return;
    if ((figure_list[figure_no].is_visible & 2) == 0)
        return;

    unit_idx = figure_list[figure_no].unit_ref;
    if (unit_list[unit_idx].combat_order == 8)
        unit_list[unit_idx].combat_order = 6;

    figure_list[figure_no].is_visible &= 0xfd;
    figure_list[figure_no].state_idx    = 6;
    figure_list[figure_no].is_defending = 1;
    figure_list[figure_no].morale =
        tribe_ai_data[bat_tribe].aggression;

    slot = figure_list[figure_no].figure_rank;
    if (slot == 1) {
        m = figure_list[figure_no].morale;
        figure_list[figure_no].morale = (m / 2);
    }
    if (figure_list[figure_no].figure_rank == 2)
        figure_list[figure_no].morale = 0;
    figure_list[figure_no].direction = figure_list[figure_no].anim_state;
}

// FUNCTION: C2 0x4E31D
// WIN: 0x00478afc
// Lines 1416–1441
//
// Look-for-fight state (state_idx 9): if defending, scan the eight neighbour cells
// via `nearest_formation_enemy` and engage the first hostile found; otherwise drop
// into the hunt-for-fight state (0xa).
void sf09_look_for_fight(void)
{
    int dir;

    get_fig_still_image();
    if (figure_list[figure_no].is_defending == 0) {
        figure_list[figure_no].state_idx = 0xa;
        return;
    }

    dir = nearest_formation_enemy();
    if (dir >= 8)
        return;

    figure_list[figure_no].state_idx       = 4;
    figure_list[figure_no].fight_direction = dir;
    figure_list[figure_no].opponent        = enemy_figure;
    figure_list[figure_no].fight_role      = 1;
    set_attack_count(figure_no);

    if (figure_list[enemy_figure].state_idx == 4)
        return;
    figure_list[enemy_figure].state_idx       = 4;
    figure_list[enemy_figure].fight_direction = ((dir + 4) % 8);
    figure_list[enemy_figure].opponent        = figure_no;
    figure_list[enemy_figure].fight_role      = 2;
    set_defense_shield(enemy_figure);
}

// FUNCTION: C2 0x4E3DF
//
// Empty state-handler slot for the "berserk" battle state.
void sf16_beserk(void)
{
}

// FUNCTION: C2 0x4E3E0
// WIN: 0x00478c7b
// Lines 1449–1468
//
// Hunt-for-fight state (state_idx 10): pick a fresh missile_target (the previous one
// if still alive, otherwise the nearest enemy), then walk toward it via
// figure_go_to_target.
void sf10_hunt_for_fight(void)
{
    short latched;

    figure_list[figure_no].is_routing   = 1;
    figure_list[figure_no].wf_searching = 0;
    figure_list[figure_no].is_defending = 0;
    enemy_figure = figure_list[figure_no].missile_target;

    if ((figure_list[figure_no].is_visible & 1) != 0) {
        latched = enemy_figure;
        if (latched != 0) {
            if (figure_list[latched].exists != 0)
                goto have_target;
        }
        if (find_nearest_enemy() != 0)
            goto tail;
        figure_list[figure_no].state_idx = 6;
        goto tail;
    have_target:
        figure_list[figure_no].prev_grid_x = figure_list[enemy_figure].grid_x;
        figure_list[figure_no].prev_grid_y = figure_list[enemy_figure].grid_y;
    }

tail:
    if (figure_list[enemy_figure].state_idx == 2) {
        figure_list[figure_no].missile_target = 0;
    }
    if (figure_list[enemy_figure].state_idx == 0xc) {
        figure_list[figure_no].missile_target = 0;
    }
    get_fig_walk_image();
    figure_go_to_target();
}

// FUNCTION: C2 0x4E4CC
// WIN: 0x00479337
// Lines 1470–1508
//
// Fire-missile state (state == 11).  While the figure hasn't
// reached its firing stand yet (is_visible bit 1 clear), keep
// walking via figure_go_to_target.  Once standing, freeze the
// sprite and tick the fire counter; on overflow try to acquire
// a target via get_fire_target first and find_nearest_target(5)
// as fallback.  On a hit latch enemy_figure, re-aim heading,
// fire (create_arrow + image/fx/range setup keyed off the
// figure's sprite_type); on a miss clear the target and let
// the next tick retry.
void sf11_fire_missile(void)
{
    if ((figure_list[figure_no].is_visible & 1) == 0) {
        get_fig_walk_image();
        figure_go_to_target();
        return;
    }

    get_fig_still_image();
    figure_list[figure_no].missile_max = 0x20;
    figure_list[figure_no].missile_timer++;
    if (figure_list[figure_no].missile_timer
        <= figure_list[figure_no].missile_max)
        goto tail;

    if (get_fire_target(figure_no) != 0) {
        figure_list[figure_no].missile_target = enemy_figure;
        figure_list[figure_no].missile_timer = 0;

        figure_list[figure_no].direction = (char)get_heading(
            figure_list[figure_no].grid_x,
            figure_list[figure_no].grid_y,
            figure_list[enemy_figure].grid_x,
            figure_list[enemy_figure].grid_y,
            figure_list[figure_no].direction);
        create_arrow(figure_list[figure_no].arrow_data_ptr,
                     figure_list[figure_no].owner,
                     figure_list[figure_no].grid_x,
                     figure_list[figure_no].grid_y,
                     figure_list[enemy_figure].grid_x,
                     figure_list[enemy_figure].grid_y);
        arrow_list[created_arrow_no].weapon_kind = figure_list[figure_no].sprite_type;
        get_arrow_base_image();
        set_missile_fire_fx(arrow_list[created_arrow_no].weapon_kind);
        set_missile_fire_range(arrow_list[created_arrow_no].weapon_kind);
    } else if (find_nearest_target(5) != 0) {
        figure_list[figure_no].missile_target = enemy_figure;
        figure_list[figure_no].missile_timer = 0;

        figure_list[figure_no].direction = (char)get_heading(
            figure_list[figure_no].grid_x,
            figure_list[figure_no].grid_y,
            figure_list[enemy_figure].grid_x,
            figure_list[enemy_figure].grid_y,
            figure_list[figure_no].direction);
        create_arrow(figure_list[figure_no].arrow_data_ptr,
                     figure_list[figure_no].owner,
                     figure_list[figure_no].grid_x,
                     figure_list[figure_no].grid_y,
                     figure_list[enemy_figure].grid_x,
                     figure_list[enemy_figure].grid_y);
        arrow_list[created_arrow_no].weapon_kind = figure_list[figure_no].sprite_type;
        get_arrow_base_image();
        set_missile_fire_fx(arrow_list[created_arrow_no].weapon_kind);
        set_missile_fire_range(arrow_list[created_arrow_no].weapon_kind);
    } else {
        figure_list[figure_no].missile_timer = 0xa;
        figure_list[figure_no].missile_target = 0;
    }

tail:
    if (figure_list[figure_no].missile_target != 0)
        get_fig_missile_image();
}

// FUNCTION: C2 0x4E6B4
// Lines 1510–1515
//
// Routing state handler: mark the figure as routing, update its
// walk image, advance toward the (panic) target, and despawn it
// once it reaches the map edge.
void sf12_rout(void)
{
    figure_list[figure_no].is_routing = 1;
    get_fig_walk_image();
    figure_go_to_target();
    if (fig_at_edge != 0) {
        remove_figure(figure_no);
    }
}

// FUNCTION: C2 0x4E6E4
// WIN: 0x004795f0
// Lines 1518–1545
//
// Auto-fire missile state (state == 13).  Same two-phase
// structure as sf11_fire_missile but the acquisition
// path skips get_fire_target entirely: every fl[+0x38]
// ticks (= 0x20) call find_nearest_target(5).  On hit
// re-aim + fire (create_arrow + the standard
// missile-art / fx / range sequence); on miss just clear
// fl[+0x29].
void sf13_autofire_missile(void)
{
    if ((figure_list[figure_no].is_visible & 1) == 0) {
        get_fig_walk_image();
        figure_go_to_target();
        return;
    }

    get_fig_still_image();
    figure_list[figure_no].missile_max = 0x20;
    figure_list[figure_no].missile_timer++;
    if (figure_list[figure_no].missile_timer
        <= figure_list[figure_no].missile_max)
        goto tail;

    figure_list[figure_no].missile_timer = 0;
    if (find_nearest_target(5) != 0) {
        figure_list[figure_no].missile_target = enemy_figure;

        figure_list[figure_no].direction = (char)get_heading(
            figure_list[figure_no].grid_x,
            figure_list[figure_no].grid_y,
            figure_list[enemy_figure].grid_x,
            figure_list[enemy_figure].grid_y,
            figure_list[figure_no].direction);
        create_arrow(figure_list[figure_no].arrow_data_ptr,
                     figure_list[figure_no].owner,
                     figure_list[figure_no].grid_x,
                     figure_list[figure_no].grid_y,
                     figure_list[enemy_figure].grid_x,
                     figure_list[enemy_figure].grid_y);
        arrow_list[created_arrow_no].weapon_kind = figure_list[figure_no].sprite_type;
        get_arrow_base_image();
        set_missile_fire_fx(arrow_list[created_arrow_no].weapon_kind);
        set_missile_fire_range(arrow_list[created_arrow_no].weapon_kind);
    } else {
        figure_list[figure_no].missile_target = 0;
    }

tail:
    if (figure_list[figure_no].missile_target != 0)
        get_fig_missile_image();
}

// FUNCTION: C2 0x4E895
// WIN: 0x0047995d
// Lines 1547–1581
//
// Opportunist-fire state (state == 14): walk toward the firing
// stand; once standing, every 0x30 ticks scan for a target in
// range 0xF via find_nearest_target.  On a hit, re-aim heading
// and fire a standard missile (create_arrow + image/fx/range);
// on a miss, crouch one row closer if not yet at the front.
//
// Phase B (the shared opportunist-AI tick) lives in
// elephant_fire, defined right below (Rule 125).
void sf14_opertunist_fire(void)
{
    if ((figure_list[figure_no].is_visible & 1) == 0) {
        get_fig_walk_image();
        figure_go_to_target();
        return;
    }

    /* ---- Phase A: opportunist range 0xF ---- */
    get_fig_still_image();
    figure_list[figure_no].missile_max = 0x30;
    figure_list[figure_no].missile_timer += 1;
    if (figure_list[figure_no].missile_timer > figure_list[figure_no].missile_max) {
        figure_list[figure_no].missile_timer = 0;
        if (find_nearest_target(0xf)) {
            figure_list[figure_no].missile_target = enemy_figure;
            figure_list[figure_no].direction = get_heading(figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                                        figure_list[enemy_figure].grid_x, figure_list[enemy_figure].grid_y,
                                        figure_list[figure_no].direction);
            create_arrow(figure_list[figure_no].arrow_data_ptr, figure_list[figure_no].owner,
                         figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                         figure_list[enemy_figure].grid_x, figure_list[enemy_figure].grid_y);
            arrow_list[created_arrow_no].weapon_kind = figure_list[figure_no].sprite_type;
            get_arrow_base_image();
            set_missile_fire_fx(arrow_list[created_arrow_no].weapon_kind);
            set_missile_fire_range(arrow_list[created_arrow_no].weapon_kind);
        } else if (figure_list[figure_no].grid_y > 0xa) {
            figure_list[figure_no].missile_target = 0;
            figure_list[figure_no].prev_grid_y = figure_list[figure_no].grid_y - 2; figure_list[figure_no].prev_grid_x = figure_list[figure_no].grid_x;
            figure_list[figure_no].is_routing = 1;
            figure_go_to_target();
        } else figure_list[figure_no].missile_target = 0;
    }

    if (figure_list[figure_no].missile_target != 0) get_fig_missile_image();
}

// FUNCTION: C2 0x4DC94
// Lines 1583–1664
//
// Elephant special: when the elephant archer figure is dead
// (state 2) park both sprite slots on the static front frame;
// otherwise run the shared opportunist-AI tick at 0xB and 0x15
// step intervals: each scans range 0x1E for an enemy figure and
// caches its index + heading into the two archer slots.  At
// archer_tick_a > 0x14 / archer_tick_b > 0x1E fires the cached
// target with a long-fuse arrow (anim_count 0x3C, anim_delta
// from the distance band 0xA / 6 / 3 / 1), then recomputes the
// two archer sprite images from the rotated archer_heading_*.
//
// Rule 125: DEFINED here, after sf14_opertunist_fire, exactly as
// in PS source (block lines 1597–1664 carry battle.c marks inside
// sf14's symbol span).  f15_barb_elephant tail-calls it, so
// CallRet + StraightenCode haul the head (through the first
// unconditional jmp, 54 bytes) up to f15's fall-through site at
// 0x4DC94 — the symbol travels with the label; the else branch
// stays here (the hauled jne targets 0x4EA81).
void elephant_fire(void)
{
    int dist;

    if (figure_list[figure_no].state_idx == 2) {
        figure_list[figure_no].archer_image_a = elephant_archer_images[0];
        figure_list[figure_no].archer_image_b = elephant_archer_images[0];
    } else {
        figure_list[figure_no].archer_tick_a++;
        figure_list[figure_no].archer_tick_b++;
        if (figure_list[figure_no].archer_tick_a == 0xb) {
            if (find_nearest_target(0x1e)) {
                target_unit_debar = figure_list[enemy_figure].unit_ref;
                if (our_battle_units <= 1) target_unit_debar = 0;
                figure_list[figure_no].archer_target_a = enemy_figure;
                figure_list[figure_no].archer_heading_a = get_heading(figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                                                   figure_list[enemy_figure].grid_x, figure_list[enemy_figure].grid_y,
                                                   figure_list[figure_no].direction);
            } else figure_list[figure_no].archer_tick_a = 0;
        }

        if (figure_list[figure_no].archer_tick_b == 0x15) {
            if (find_nearest_target(0x1e)) {
                target_unit_debar = figure_list[enemy_figure].unit_ref;
                if (our_battle_units <= 1) target_unit_debar = 0;
                figure_list[figure_no].archer_target_b = enemy_figure;
                figure_list[figure_no].archer_heading_b = get_heading(figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                                                   figure_list[enemy_figure].grid_x, figure_list[enemy_figure].grid_y,
                                                   figure_list[figure_no].direction);
            } else figure_list[figure_no].archer_tick_b = 0xa;
        }

        if (figure_list[figure_no].archer_tick_a > 0x14) {
            enemy_figure = figure_list[figure_no].archer_target_a;
            create_arrow(figure_list[figure_no].arrow_data_ptr, figure_list[figure_no].owner,
                         figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                         figure_list[enemy_figure].grid_x, figure_list[enemy_figure].grid_y);
            dist = get_longest_distance(figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                                        figure_list[enemy_figure].grid_x, figure_list[enemy_figure].grid_y);
            arrow_list[created_arrow_no].weapon_kind = figure_list[figure_no].sprite_type;
            get_arrow_base_image();
            arrow_list[created_arrow_no].anim_count = 0x3c;
            set_missile_fire_fx(arrow_list[created_arrow_no].weapon_kind);
            set_missile_fire_range(arrow_list[created_arrow_no].weapon_kind);
            if      (dist <= 2) arrow_list[created_arrow_no].anim_delta = 0xa;
            else if (dist <= 4) arrow_list[created_arrow_no].anim_delta = 6;
            else if (dist <= 8) arrow_list[created_arrow_no].anim_delta = 3;
            else                arrow_list[created_arrow_no].anim_delta = 1;
            figure_list[figure_no].archer_tick_a = rand128 & 3;
        }

        if (figure_list[figure_no].archer_tick_b > 0x1e) {
            enemy_figure = figure_list[figure_no].archer_target_b;
            create_arrow(figure_list[figure_no].arrow_data_ptr, figure_list[figure_no].owner,
                         figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                         figure_list[enemy_figure].grid_x, figure_list[enemy_figure].grid_y);
            dist = get_longest_distance(figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                                        figure_list[enemy_figure].grid_x, figure_list[enemy_figure].grid_y);
            arrow_list[created_arrow_no].weapon_kind = figure_list[figure_no].sprite_type;
            set_missile_fire_fx(arrow_list[created_arrow_no].weapon_kind);
            get_arrow_base_image();
            arrow_list[created_arrow_no].anim_count = 0x3c;
            set_missile_fire_range(arrow_list[created_arrow_no].weapon_kind);
            if      (dist <= 2) arrow_list[created_arrow_no].anim_delta = 0xa;
            else if (dist <= 4) arrow_list[created_arrow_no].anim_delta = 6;
            else if (dist <= 8) arrow_list[created_arrow_no].anim_delta = 3;
            else                arrow_list[created_arrow_no].anim_delta = 1;
            figure_list[figure_no].archer_tick_b = 0xa;
        }

        /* Sprite slot 1: elephant_archer_images indexed by
           archer_tick_a, rotated by map_direction (one full
           += statement per direction; Watcom cross-jumps the
           identical tails into the shared %8*4 join). */
        figure_list[figure_no].archer_image_a = elephant_archer_images[figure_list[figure_no].archer_tick_a];
        if      (map_direction == 0) figure_list[figure_no].archer_image_a += ((figure_list[figure_no].archer_heading_a % 8) * 4);
        else if (map_direction == 2) figure_list[figure_no].archer_image_a += (((figure_list[figure_no].archer_heading_a + 6) % 8) * 4);
        else if (map_direction == 4) figure_list[figure_no].archer_image_a += (((figure_list[figure_no].archer_heading_a + 4) % 8) * 4);
        else if (map_direction == 6) figure_list[figure_no].archer_image_a += (((figure_list[figure_no].archer_heading_a + 2) % 8) * 4);

        /* Sprite slot 2: elephant_archer_images[0] when archer_tick_b
           < 0xA, otherwise the tick-10 elephant frame.  Same rotation. */
        if (figure_list[figure_no].archer_tick_b < 0xa) figure_list[figure_no].archer_image_b = elephant_archer_images[0];
        else figure_list[figure_no].archer_image_b = elephant_archer_images[figure_list[figure_no].archer_tick_b - 10];

        if      (map_direction == 0) figure_list[figure_no].archer_image_b += ((figure_list[figure_no].archer_heading_b % 8) * 4);
        else if (map_direction == 2) figure_list[figure_no].archer_image_b += (((figure_list[figure_no].archer_heading_b + 6) % 8) * 4);
        else if (map_direction == 4) figure_list[figure_no].archer_image_b += (((figure_list[figure_no].archer_heading_b + 4) % 8) * 4);
        else if (map_direction == 6) figure_list[figure_no].archer_image_b += (((figure_list[figure_no].archer_heading_b + 2) % 8) * 4);
    }
}

// FUNCTION: C2 0x4F096
// WIN: 0x0047a4ba
// Lines 1666–1677
//
// Set the base sprite type for the newly-created arrow tracked by
// created_arrow_no, indexed by the firing figure's sprite_type
// (figure_list+0x5).  Bow/javelin classes 3/9/10/16/17 use sprite
// base 0xaa, ballista bolts (13) use 0x28, onager rocks (15) use 0x50,
// everything else clears it to 0.  Also forwards the firer's owner
// (figure_list+0x26) into arrow_list+0x1b.
void get_arrow_base_image(void)
{
    int kind = figure_list[figure_no].sprite_type;

    if (kind == 3) {
        arrow_list[created_arrow_no].sprite_base = 0xaa;
    } else if (kind == 9) {
        arrow_list[created_arrow_no].sprite_base = 0xaa;
    } else if (kind == 10) {
        arrow_list[created_arrow_no].sprite_base = 0xaa;
    } else if (kind == 13) {
        arrow_list[created_arrow_no].sprite_base = 0x28;
    } else if (kind == 15) {
        arrow_list[created_arrow_no].sprite_base = 0x50;
    } else if (kind == 16) {
        arrow_list[created_arrow_no].sprite_base = 0xaa;
    } else if (kind == 17) {
        arrow_list[created_arrow_no].sprite_base = 0xaa;
    } else {
        arrow_list[created_arrow_no].sprite_base = 0;
    }
    arrow_list[created_arrow_no].sprite_kind =
        figure_list[figure_no].sprite_kind;
}

// FUNCTION: C2 0x4F174
// WIN: 0x0047a67f
// Lines 1679–1697
//
// Per-tick AI for active arrows (arrow_no 1..0xc8).  Each existing
// arrow (arrow.+0x23 != 0) clears its wait counter (+0x21), flies
// one step toward its target via fly_to_target(), advances its
// per-frame anim counter (anim_count -= anim_decay if > 0), then
// recomputes the current sprite index from the heading byte
// (+0x27) plus a map_direction-dependent rotation (0 -> +1, 2 -> +7,
// 4 -> +5, 6 -> +3) clamped to [0,7] mod 8, and stores it at +0x1A
// (= +0x1C base + rotation index).
void arrow_intelligence(void)
{
    int idx;

    for (arrow_no = 1; arrow_no < 0xc9; arrow_no++) {
        if (arrow_list[arrow_no].exists != 0) {
            arrow_list[arrow_no].flight_done = 0;
            fly_to_target();

            if (arrow_list[arrow_no].anim_count != 0) arrow_list[arrow_no].anim_count -= arrow_list[arrow_no].anim_delta;

            idx = (unsigned char)arrow_list[arrow_no].heading;
            if (map_direction == 0) idx += 1;
            if (map_direction == 2) idx += 7;
            if (map_direction == 4) idx += 5;
            if (map_direction == 6) idx += 3;
            if (idx >= 8) idx = idx % 8;

            arrow_list[arrow_no].sprite_anim =
                (arrow_list[arrow_no].sprite_base + idx);
        }
    }
}

// FUNCTION: C2 0x4F27D
// WIN: 0x0047a7db
// Lines 1700–1717
//
// Sweep figure_list[1..200].  For each existing+selected figure that
// belongs to a unit, either deselect the lot (if its owner is the
// player, .owner==0) or attempt a reform: outside battle, run
// test_reform_pattern + instant_reform on its unit_ref; in battle,
// delegate to reform() with formation=0.
void general_reform(int p1)
{
    /* Per-unit dedup: skip figures whose unit_ref matches the previous
       iteration so consecutive figures from the same unit don't re-trigger
       the reform.  Initial value 0 acts as "no unit yet". */
    int prev_unit = 0;

    for (figure_no = 1; figure_no < 201; figure_no++) {
        if (figure_list[figure_no].selected != 0
            && figure_list[figure_no].exists != 0
            && (unsigned char)figure_list[figure_no].unit_ref != prev_unit) {
            if (figure_list[figure_no].owner == 0) {
                deselect_all_figures();
                return;
            }
            if (battle_state == 0) {
                if (test_reform_pattern(figure_list[figure_no].unit_ref, p1) != 0) {
                    instant_reform(figure_list[figure_no].unit_ref, p1);
                }
            } else {
                reform(figure_list[figure_no].unit_ref, p1, 0);
            }
            prev_unit = (unsigned char)figure_list[figure_no].unit_ref;
        }
    }
}

// FUNCTION: C2 0x4F33D
// WIN: 0x0047a94b
// Lines 1719–1746
//
// Re-form the figures of `unit_ref` into formation mode `mode`.
// Stores mode in unit+0x36, then walks the unit's figure range.  For
// normal modes, get_fig_in_unit_position publishes x_bit/y_bit offsets
// which are added to the unit origin and copied into the figure's
// previous-grid / per-figure offset fields.  `force` marks figures for
// state 7; mode 3 instead sends them berserk/state 10.  Routed figures
// (state 12) are also brought back to state 7.  Defending is cleared.
void reform(int unit_ref, int mode, int force)
{
  int unit_x;
  int pos;
  int unit_y;
  unit_list[unit_ref].formation_mode = mode;
  pos = 0;
  unit_x = unit_list[unit_ref].x;
  unit_y = unit_list[unit_ref].y;
  for (temp_figure = unit_list[unit_ref].first_figure; temp_figure <= unit_list[unit_ref].last_figure; temp_figure++)
  {
    if (figure_list[temp_figure].exists != 0)
    {
      if (mode != 3)
      {
        get_fig_in_unit_position(mode, pos, temp_figure);
        figure_list[temp_figure].prev_grid_x = unit_x + ((char) x_bit);
        figure_list[temp_figure].prev_grid_y = unit_y + ((char) y_bit);
        figure_list[temp_figure].offset_x = x_bit;
        figure_list[temp_figure].offset_y = y_bit;
        figure_list[temp_figure].shield_class = mode;
        if (force != 0)
          figure_list[temp_figure].state_idx = 7;
        if (figure_list[temp_figure].state_idx == 0xc)
          figure_list[temp_figure].state_idx = 7;
      }
      else
      {
        figure_list[temp_figure].state_idx = 0xa;
      }
      figure_list[temp_figure].is_defending = 0;
      pos++;
    }
  }

}


// FUNCTION: C2 0x4F44D
// WIN: 0x0047ab55
// Lines 1748–1781
//
// Re-snap every figure in unit `unit_no` into a fresh formation
// of kind `formation`.  formation == 3 is the "disband" no-op
// shortcut that only stores the formation byte and returns.
// Otherwise a two-pass walk: pass 1 zeros the unit's prior
// battle_map footprint so the previous figure-id markers don't
// leak into the new layout; pass 2 places each living figure
// at its formation slot via get_fig_in_unit_position (which
// writes x_bit/y_bit), adds those offsets to the unit's anchor,
// stamps the new map_ref + battle_map[map_ref], and resets
// state to 6 (idle in formation) with combat flags cleared.
// The slot counter only increments on living figures, so gaps
// collapse to contiguous slots.
void instant_reform(int unit_no, int formation)
{
    int base_y;
  int base_x;
  int pos;
  unit_list[unit_no].formation_mode = formation;
  if (formation == 3)
    return;
  pos = 0;
  base_x = unit_list[unit_no].x;
  base_y = unit_list[unit_no].y;
  for (temp_figure = unit_list[unit_no].first_figure; temp_figure <= unit_list[unit_no].last_figure; temp_figure++)
  {
    if (figure_list[temp_figure].exists != 0)
    {
      ((unsigned char *) battle_map)[figure_list[temp_figure].map_ref + 1] = 0;
    }
  }

  for (temp_figure = unit_list[unit_no].first_figure; temp_figure <= unit_list[unit_no].last_figure; temp_figure++)
  {
    if (figure_list[temp_figure].exists != 0)
    {
      get_fig_in_unit_position(formation, pos, temp_figure);
      update_map = 1;
      figure_list[temp_figure].grid_x = base_x + ((char) x_bit);
      figure_list[temp_figure].grid_y = base_y + ((char) y_bit);
      figure_list[temp_figure].map_ref = (figure_list[temp_figure].grid_x + (figure_list[temp_figure].grid_y * 0x34)) * 4;
      ((unsigned char *) battle_map)[figure_list[temp_figure].map_ref + 1] = temp_figure;
      figure_list[temp_figure].offset_x = x_bit;
      figure_list[temp_figure].offset_y = y_bit;
      figure_list[temp_figure].shield_class = formation;
      figure_list[temp_figure].is_defending = 1;
      figure_list[temp_figure].state_idx = 6;
      figure_list[temp_figure].wf_step_y = 0;
      figure_list[temp_figure].wf_step_x = 0;
      figure_list[temp_figure].is_routing = 0;
      figure_list[temp_figure].is_visible &= 0xfc;
      figure_list[temp_figure].is_visible |= 1;
      pos++;
    }
  }

}




// FUNCTION: C2 0x4F5E0
// WIN: 0x0047aeb4
// Lines 1784–1807
//
// Test whether a unit can reform at (x_bit, y_bit) heading direction
// `dir`.  For each figure slot 0..figure_count-1 of the unit, walk
// the corresponding formation cell (get_fig_in_unit_position fills
// in the position via x_bit/y_bit) and:
//
//   * fail if the cell lies past nomansland_ptr (off-map / outside
//     the legal battle area),
//   * succeed when the cell is empty,
//   * succeed when the figure currently in the cell is from the same
//     army (figure_list[].+0x2B = army_no).
//
// As a fast-path: dir 3 (RESET / stay-put) always succeeds.
int test_reform_pattern(int unit_ref, int dir)
{
  int pos;
  int unit_x;
    int unit_y;
  int cell_off;
  int occ;
  if (dir == 3)
    return 1;
  pos = 0;
  unit_x = unit_list[unit_ref].x;
  unit_y = unit_list[unit_ref].y;
  for (temp_figure = unit_list[unit_ref].first_figure; temp_figure <= unit_list[unit_ref].last_figure; temp_figure++)
  {
    if (figure_list[temp_figure].exists != 0)
    {
      get_fig_in_unit_position(dir, pos, temp_figure);
      cell_off = (unit_x + x_bit) * BATTLE_CELL_BYTES;
      cell_off += (unit_y + y_bit) * BATTLE_ROW;
      occ = ((unsigned char *) battle_map)[cell_off + 1];
      pos++;
      if (cell_off >= nomansland_ptr)
        return 0;
      if (occ != 0)
      {
        if ((figure_list[occ].unit_ref) != (figure_list[temp_figure].unit_ref))
        {
          return 0;
        }
      }
    }
  }

  return 1;
}



// FUNCTION: C2 0x4F6C1
// WIN: 0x0047b036
// Lines 1810–1831
//
// Compute (x_bit, y_bit) globals for figure `fig_idx` under
// formation `mode`.  Reads the figure's anchor_x / anchor_y /
// unit_position fields, then dispatches:
//   0 → (x_bit, y_bit) = (get_x_spacing, get_y_spacing)
//   1 → same with the axes swapped
//   2 → mode 0 with anchor_y + 1 (back-rank stagger)
//   anything else → (0, 0)
// The unit_position field is forwarded into get_y_spacing as
// the per-figure scaling factor.
void get_fig_in_unit_position(int mode, int p2, int fig_idx)
{
    int fp;
    int fx;
    int fy;

    fx = figure_list[fig_idx].unit_grid_x;
    fy = figure_list[fig_idx].unit_grid_y;
    fp = figure_list[fig_idx].unit_position;

    if (mode == 0) {
        x_bit = get_x_spacing(fx, fy, p2);
        y_bit = get_y_spacing(fx, fy, p2, fp);
    } else if (mode == 1) {
        y_bit = get_x_spacing(fx, fy, p2);
        x_bit = get_y_spacing(fx, fy, p2, fp);
    } else if (mode == 2) {
        x_bit = get_x_spacing(fx, fy + 1, p2);
        y_bit = get_y_spacing(fx, fy + 1, p2, fp);
    } else {
        y_bit = 0;
        x_bit = 0;
    }
}

// FUNCTION: C2 0x4F74E
// WIN: 0x0047b16d
// Lines 1833–1890
//
// Pick the sprite-frame for figure_no while it is in a fight
// state.  fight_state == 2 (stopped) delegates to
// get_fig_still_image and returns.  Otherwise per-state pacing
// picks (cnt_step, delay_short, delay_long): (9, 0, 0) when
// walking-while-engaged, (20, 10, 16) when post-swing.  The
// figure's direction is rotated by one step on every swing-cycle
// and folded against the camera-rotation table (map_direction
// 0/2/4/6 → +0/+6/+4/+2), then multiplied by cnt_step to land
// at the base of the animation sheet.  Combat sub-state then
// selects which step pattern advances anim_counter (cap 8 or 12)
// and what delay (0, short, short+3, or long) is added to the
// base before writing the final sprite_anim byte.
void get_fig_fight_image(void)
{
    int dir;
    int cnt_step;
    int delay_long;
    int delay_short;
    int dir_step;
    int tick;

    dir = figure_list[figure_no].fight_direction;
    if (figure_list[figure_no].fight_state == 2) {
        get_fig_still_image();
        return;
    }
    if (figure_list[figure_no].fight_state != 0) {
        cnt_step = 9;
        delay_long = 0;
        delay_short = 0;
        figure_list[figure_no].sprite_dir = 1;
    } else {
        cnt_step = 20;
        delay_long = 16;
        delay_short = 10;
    }
    if (figure_list[figure_no].fight_state != 0) {
        dir = (dir + 2) % 8;
    }
    if (map_direction == 0) {
        dir_step = (dir % 8) * cnt_step;
    } else if (map_direction == 2) {
        dir_step = ((dir + 6) % 8) * cnt_step;
    } else if (map_direction == 4) {
        dir_step = ((dir + 4) % 8) * cnt_step;
    } else if (map_direction == 6) {
        dir_step = ((dir + 2) % 8) * cnt_step;
    }
    if (figure_list[figure_no].fight_role == 1) {
        if (figure_list[figure_no].fight_state != 0) {
            figure_list[figure_no].anim_counter++;
            if (figure_list[figure_no].anim_counter >= 12)
                figure_list[figure_no].anim_counter = 0;
            dir_step += ((unsigned char)figure_list[figure_no].anim_counter) >> 1;
        } else if (figure_list[figure_no].fight_swing_active != 0) {
            dir_step += delay_short + 3;
            figure_list[figure_no].anim_counter++;
            if (figure_list[figure_no].anim_counter >= 8)
                figure_list[figure_no].anim_counter = 0;
            tick = ((unsigned char)figure_list[figure_no].anim_counter) >> 1;
            if (tick == 3)
                tick = 1;
            dir_step += tick;
        } else {
            dir_step += delay_short;
            figure_list[figure_no].anim_counter++;
            if (figure_list[figure_no].anim_counter >= 12)
                figure_list[figure_no].anim_counter = 0;
            dir_step += ((unsigned char)figure_list[figure_no].anim_counter) >> 1;
        }
    } else {
        if (figure_list[figure_no].fight_state != 0) {
            figure_list[figure_no].anim_counter++;
            if (figure_list[figure_no].anim_counter >= 12)
                figure_list[figure_no].anim_counter = 0;
            dir_step += ((unsigned char)figure_list[figure_no].anim_counter) >> 1;
        } else {
            dir_step += delay_long;
            figure_list[figure_no].anim_counter++;
            if (figure_list[figure_no].anim_counter >= 8)
                figure_list[figure_no].anim_counter = 0;
            dir_step += ((unsigned char)figure_list[figure_no].anim_counter) >> 1;
        }
    }
    figure_list[figure_no].sprite_anim = dir_step;
}



// FUNCTION: C2 0x4F902
// WIN: 0x0047b600
// Lines 1892–1911
//
// Walk-pose sprite frame picker for figure_no.  Mirrors
// get_fig_still_image's base-step + map-direction-relative rotation,
// then adds the figure's running animation counter (>>1) and advances
// that counter (different cycle length per fight_state).
void get_fig_walk_image(void)
{
    int base;
    int sprite_val;

    figure_list[figure_no].sprite_dir = 0;
    if (figure_list[figure_no].fight_state == 2) {
        base = 6;
    } else if (figure_list[figure_no].fight_state != 0) {
        base = 5;
    } else {
        base = 0x14;
    }
    /* map_direction is always 0/2/4/6 in practice; the unmatched
       default leaves sprite_val undefined but never executes. */
    if (map_direction == 0)      sprite_val = (figure_list[figure_no].direction % 8) * base;
    else if (map_direction == 2) sprite_val = ((figure_list[figure_no].direction + 6) % 8) * base;
    else if (map_direction == 4) sprite_val = ((figure_list[figure_no].direction + 4) % 8) * base;
    else if (map_direction == 6) sprite_val = ((figure_list[figure_no].direction + 2) % 8) * base;
    sprite_val += (unsigned char)figure_list[figure_no].anim_counter >> 1;
    if (figure_list[figure_no].fight_state == 2) {
        figure_list[figure_no].anim_counter++;
        if (figure_list[figure_no].anim_counter >= 0xc)
            figure_list[figure_no].anim_counter = 0;
    } else if (figure_list[figure_no].fight_state != 0) {
        figure_list[figure_no].anim_counter++;
        if (figure_list[figure_no].anim_counter >= 0xa)
            figure_list[figure_no].anim_counter = 0;
    } else {
        figure_list[figure_no].anim_counter++;
        if (figure_list[figure_no].anim_counter >= 0x14)
            figure_list[figure_no].anim_counter = 0;
    }
    figure_list[figure_no].sprite_anim = sprite_val;
}

// FUNCTION: C2 0x4FA48
// WIN: 0x0047b8e5
// Lines 1913–1930
//
// Pick the still-image sprite frame for figure_no.  Selects a
// per-state base step (6 for still-state 2, 5 for non-zero active
// states, 0x14 for idle state 0); if idle and the figure is
// defending with shield_class==2, delegates to the tortoise-shape
// pose-picker instead.  Computes the direction-adjusted frame from
// (.direction + map_direction-relative offset) mod 8 multiplied by
// the base step, then stashes it as sprite_anim.  sprite_dir is
// cleared at entry.
void get_fig_still_image(void)
{
    int base;
    int anim;

    figure_list[figure_no].sprite_dir = 0;
    if (figure_list[figure_no].fight_state == 2) {
        base = 6;
    } else if (figure_list[figure_no].fight_state != 0) {
        base = 5;
    } else {
        if (figure_list[figure_no].is_defending != 0
            && figure_list[figure_no].shield_class == 2) {
            get_fig_tortoise_image();
            return;
        }
        base = 0x14;
    }
    /* map_direction is always 0/2/4/6 in practice; the unmatched
       default leaves anim undefined but never executes. */
    if (map_direction == 0)      anim = (figure_list[figure_no].direction % 8) * base;
    else if (map_direction == 2) anim = ((figure_list[figure_no].direction + 6) % 8) * base;
    else if (map_direction == 4) anim = ((figure_list[figure_no].direction + 4) % 8) * base;
    else if (map_direction == 6) anim = ((figure_list[figure_no].direction + 2) % 8) * base;
    figure_list[figure_no].sprite_anim = anim;
}

// FUNCTION: C2 0x4FB34
// WIN: 0x0047bac7
// Lines 1932–1949
//
// Pick the facing for a tortoise figure (the locked-shield Roman
// formation): prefer to face the same-army figure that's one step
// E (4), N (2), S (6), or W (0); fall back to E (4) when no
// neighbour matches.  The chosen facing is written to figure.+0x6,
// then the per-map-rotation image offset is computed from the
// facing (offset by map_direction's contribution) and stored at
// figure.+0x2 as ((facing+rot) % 8) * 20 + 0x10.
void get_fig_tortoise_image(void)
{
    int img;

    if (test_for_same_fig_to(4) == 0) {
        figure_list[figure_no].direction = 4;
    } else {
        if (test_for_same_fig_to(2) == 0)
            figure_list[figure_no].direction = 2;
        else {
            if (test_for_same_fig_to(6) == 0)
                figure_list[figure_no].direction = 6;
            else {
                if (test_for_same_fig_to(0) == 0)
                    figure_list[figure_no].direction = 0;
                else
                    figure_list[figure_no].direction = 4;
            }
        }
    }

    /* map_direction is always 0/2/4/6 in practice; the +0x10 is applied
       at the join. */
    if (map_direction == 0)      img = (figure_list[figure_no].direction % 8) * 20;
    else if (map_direction == 2) img = ((figure_list[figure_no].direction + 6) % 8) * 20;
    else if (map_direction == 4) img = ((figure_list[figure_no].direction + 4) % 8) * 20;
    else if (map_direction == 6) img = ((figure_list[figure_no].direction + 2) % 8) * 20;
    img = img + 0x10;
    figure_list[figure_no].sprite_anim = img;
}

// FUNCTION: C2 0x4FC4E
// WIN: 0x0047bcbd
// Lines 1951–1977
//
// Direction-checked neighbour test on the battle map.  Returns 1 if
// the neighbour cell in `dirc` (0/2/4/6) holds a figure that shares
// figure_no's unit_ref, 0 otherwise.  Each direction is gated on
// the firer's row (grid_y at +0x9) staying inside the half-map
// boundary 0x33 (or strictly positive for the back two dirs).  The
// peek offsets are raw battle-map-relative byte offsets:
//   dirc 4 → +0xd1  (south-forward)
//   dirc 2 → +0x05  (east neighbour)
//   dirc 6 → -0xCF  (rear-right neighbour, into region_map tail)
//   dirc 0 → -0x19B (far-rear)
int test_for_same_fig_to(int dirc)
{
    int other_idx;

    if (dirc == 4) {
        if (figure_list[figure_no].grid_y >= 0x33) return 0;
        other_idx = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + BATTLE_ROW + 1];
    } else if (dirc == 2) {
        if (figure_list[figure_no].grid_y >= 0x33) return 0;
        other_idx = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 5];
    } else if (dirc == 6) {
        if (figure_list[figure_no].grid_y <= 0) return 0;
        other_idx = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref - 3];
    } else if (dirc == 0) {
        if (figure_list[figure_no].grid_y <= 0) return 0;
        other_idx = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref - 0xcf];
    }
    if (other_idx == 0) return 0;
    if (figure_list[other_idx].unit_ref != figure_list[figure_no].unit_ref)
        return 0;
    return 1;
}

// FUNCTION: C2 0x4FD25
// WIN: 0x0047be76
// Lines 1979–1988
//
// Pick the sprite frame for a dying figure (figure_no).  If the
// figure's fight_state is 2 ("still"), delegate to
// get_fig_still_image; otherwise compute the death-animation
// frame from death_timer (capped at 7) and stash it in
// .sprite_anim, with .sprite_dir bumped to 1 if the figure has
// a non-zero fight_state (so it draws as the "dying" pose),
// otherwise the alternate "corpse" pose.
void get_fig_death_image(void)
{
    int frame;

    if (figure_list[figure_no].fight_state == 2) {
        get_fig_still_image();
        return;
    }
    frame = figure_list[figure_no].death_timer >> 1;
    if (frame > 7) frame = 7;
    if (figure_list[figure_no].fight_state != 0) {
        figure_list[figure_no].sprite_anim = (frame + 0x48);
        figure_list[figure_no].sprite_dir  = 1;
    } else {
        figure_list[figure_no].sprite_anim = (frame + 0xa0);
    }
}

// FUNCTION: C2 0x4FD87
// WIN: 0x0047bf53
// Lines 1990–2010
//
// Missile-attack frame picker for figure_no.  Non-zero fight_state
// uses the short 9-frame stride and sprite_dir=1; idle uses the
// normal 20-frame stride.  The base direction is rotated by
// map_direction, scaled by the stride, then an equipment-specific
// firing-frame table (sling/bow/horsebow) is indexed by the figure's
// missile timer at +0x40 (clamped to 0x20).
// Sets figure_list[figure_no].sprite_anim as a side effect.
void get_fig_missile_image(void)
{
    int dir_base;
    int stride;
    int idx;

    figure_list[figure_no].sprite_dir = 0;
    if (figure_list[figure_no].fight_state != 0) {
        stride = 9;
        figure_list[figure_no].sprite_dir = 1;
    } else {
        stride = 0x14;
    }

    if (map_direction == 0)
        dir_base = (figure_list[figure_no].direction % 8) * stride;
    else if (map_direction == 2)
        dir_base = ((figure_list[figure_no].direction + 6) % 8) * stride;
    else if (map_direction == 4)
        dir_base = ((figure_list[figure_no].direction + 4) % 8) * stride;
    else if (map_direction == 6)
        dir_base = ((figure_list[figure_no].direction + 2) % 8) * stride;

    idx = figure_list[figure_no].missile_timer;
    if (0x20 < idx)
        idx = 0x20;

    if (figure_list[figure_no].sprite_type == 10)
        dir_base += sling_images[idx];
    else if (figure_list[figure_no].sprite_type == 3)
        dir_base += sling_images[idx];
    else if (figure_list[figure_no].fight_state != 0)
        dir_base += horsebow_images[idx];
    else
        dir_base += bow_images[idx];
    figure_list[figure_no].sprite_anim = dir_base;
}

// FUNCTION: C2 0x4FEA9
// WIN: 0x0047c1a2  (unverified)
// Lines 2012–2030
//
// Mark a rectangle of battle_map cells dirty by ORing bit
// 1 into each cell's +0x02 byte (121 b, L2012–2030).
//
// battle_map is 52×52 (0x34×0x34) cells, 4 bytes each
// (`battle_cell_size` 4).  The rectangle is computed from
// 6 args: an anchor (cx=a+c, cy=b+d), a margin `e` in
// each direction, and an extra extent `f` in the +x/+y
// direction:
//
//   x0 = clamp(a + c - e,         0, 51)
//   x1 = clamp(a + c + e + f,     0, 51)
//   y0 = clamp(b + d - e,         0, 51)
//   y1 = clamp(b + d + e + f,     0, 51)
//
// Then for each (row, col) in [y0..y1] × [x0..x1] inclusive,
// `((char*)battle_map)[(row*52 + col)*4 + 2] |= 2`.
//
// Used by figure_update + arrow_update to flag cells
// touched by figures/arrows for the next battle-map
// refresh pass.
void set_figure_map_refresh(int a, int b, int c, int d,
                            int e, int f)
{
    int x0;
    int x1;
    int y0;
    int y1;
    int row;
    int col;
    int byte_off;
    int row_stride;

    x0 = a + c - e;
    y0 = b + d - e;
    x1 = (a + c + f) + e;
    y1 = (b + d + f) + e;

    if (x0 < 0) x0 = 0;
    if (x1 >= 0x34) x1 = 0x33;
    if (y0 < 0) y0 = 0;
    if (y1 >= 0x34) y1 = 0x33;

    byte_off = (y0 * 0x34 + x0) * 4;
    row_stride = (0x34 - ((x1 - x0) + 1)) * 4;
    for (row = y0; row <= y1; ++row, byte_off += row_stride) {
        for (col = x0; col <= x1; ++col, byte_off += 4) {
            ((unsigned char *)battle_map)[(byte_off) + 2] |= 2;
        }
    }
}

// FUNCTION: C2 0x4FF22
// WIN: 0x0047c2b4
// Lines 2032–2039
//
// Stamp arrow_list[created_arrow_no].fire_range and
// .fire_speed from the missile-weapon kind `n` (174 b,
// L2032–2039).  Five tiers:
//
//   n <= 3       → range=60, speed=50    (basic ranged)
//   n <= 9       → range=30, speed=120   (heavy / short)
//   n == 10      → range=60, speed=50    (same as basic)
//   n <= 16      → range=40, speed=100   (medium tier)
//   n == 17      → range=70, speed=30    (siege/long)
//   n >  17      → no-op
void set_missile_fire_range(int n)
{
    if (n <= 3) {
        arrow_list[created_arrow_no].fire_range = 60;
        arrow_list[created_arrow_no].fire_speed = 50;
    } else if (n <= 9) {
        arrow_list[created_arrow_no].fire_range = 30;
        arrow_list[created_arrow_no].fire_speed = 120;
    } else if (n <= 10) {
        arrow_list[created_arrow_no].fire_range = 60;
        arrow_list[created_arrow_no].fire_speed = 50;
    } else if (n <= 16) {
        arrow_list[created_arrow_no].fire_range = 40;
        arrow_list[created_arrow_no].fire_speed = 100;
    } else if (n <= 17) {
        arrow_list[created_arrow_no].fire_range = 70;
        arrow_list[created_arrow_no].fire_speed = 30;
    }
}

// FUNCTION: C2 0x4FFD0
// WIN: 0x0047c3b9
// Lines 2043–2054
//
// Per-tick dispatcher for Roman unit AI.  Every 32-tick boundary
// bumps battle_ai_count, then walks active Roman units (type 0):
// routed units (combat_order == 0xc) are skipped; units with the
// byte flag at +0x39 use light AI; elephants (owner/type byte at
// +0x1C == 0x0f) use elephant_ai; all others use heavy AI.
void update_units_ai(void)
{
    if (cnt32 == 0)
        battle_ai_count++;
    for (temp_unit = 1; temp_unit < 0x33; temp_unit++) {
        if (unit_list[temp_unit].exists == 0) continue;
        if (unit_list[temp_unit].type != 0) continue;
        if (unit_list[temp_unit].combat_order == 0xc) continue;
        if (unit_list[temp_unit].unit_sub_kind != 0) {
            do_light_ai();
        } else if (unit_list[temp_unit].owner == 0xf) {
            elephant_ai();
        } else {
            do_heavy_ai();
        }
    }
}

// FUNCTION: C2 0x5004E
// WIN: 0x0047c4cb
// Lines 2056–2066
//
// Per-tick AI driver for elephant units.  Same period
// counter as do_light_ai, but on each fire occasionally
// drifts the unit one cell north (dy = -1) at random:
//
//   r = rand128 & 7;                  // 0..7
//   if (r <= 4)  set_ai_unit_move(0, 0);    // 5/8 stay put
//   else         set_ai_unit_move(0, -1);   // 3/8 drift
//
// Models the gentle wandering elephants exhibit when not
// directly engaged.
void elephant_ai(void)
{
    ++unit_list[temp_unit].ai_tick;
    if (unit_list[temp_unit].ai_tick >= unit_list[temp_unit].ai_period) {
        unit_list[temp_unit].ai_tick = 0;
        if ((rand128 & 7) <= 4) {
            set_ai_unit_move(0, 0);
        } else {
            set_ai_unit_move(0, -1);
        }
    }
}

// FUNCTION: C2 0x5009B
// WIN: 0x0047c57e
// Lines 2068–2079
//
// Per-tick AI driver for “light” (skirmisher / archer)
// units indexed by `temp_unit`.  Bumps the unit's AI tick
// counter; when it crosses the per-unit `ai_period`,
// resets to 0 and decides between charging (berserk) and
// holding to auto-fire based on overall battle pressure.
//
//   period = (unit_rank == 2) ? 60 : 30   // back row
//                                          // ticks slower
//   if (period <= battle_ai_count)       // few units left:
//       set_ai_unit_beserk();             //   charge
//   else                                  // many units:
//       set_ai_unit_auto_fire();          //   keep firing
void do_light_ai(void)
{
    int period;

    ++unit_list[temp_unit].ai_tick;
    if (unit_list[temp_unit].ai_tick >= unit_list[temp_unit].ai_period) {
        unit_list[temp_unit].ai_tick = 0;
        if ((unit_list[temp_unit].unit_rank & 0xff) == 2) {
            period = 60;
        } else {
            period = 30;
        }
        if (period <= battle_ai_count) {
            set_ai_unit_beserk();
        } else {
            set_ai_unit_auto_fire();
        }
    }
}

// FUNCTION: C2 0x500FC
// WIN: 0x0047c653
// Lines 2081–2118
//
// Heavy-AI dispatch for the current battle unit (temp_unit),
// called once per AI tick from update_units_ai.  Reads five
// per-tribe AI thresholds out of tribe_ai_data, gated by a
// per-unit ai_period cooldown.  Two priorities:
//
//   * Broken morale (target_lock > 2): withdraw if the tribe's
//     base_morale threshold permits and we haven't already.
//   * Otherwise (skipping combat_order 8 or 0xA): try delayed-
//     berserk, then berserk (once battle_ai_count crosses the
//     berserk_count threshold), then any pending flank flag,
//     then a wedge-move keyed off the unit's column position,
//     then a forward-move as final fallback.
void do_heavy_ai(void)
{
    int thresh_3;
    int thresh_1;
    int thresh_2;
    int thresh_5;
    int thresh_4;
    int dl;
    int ai_pos;

    thresh_2 = tribe_ai_data[bat_tribe].delayed_berserk;
    thresh_1 = tribe_ai_data[bat_tribe].berserk_count;
    thresh_5 = tribe_ai_data[bat_tribe].base_morale;
    thresh_3 = tribe_ai_data[bat_tribe].wedge_move;
    thresh_4 = tribe_ai_data[bat_tribe].forward_move;

    /* Bump the cooldown counter and bail if not yet ready. */
    unit_list[temp_unit].ai_tick = (unit_list[temp_unit].ai_tick + 1);
    if (unit_list[temp_unit].ai_tick < unit_list[temp_unit].ai_period)
        return;
    unit_list[temp_unit].ai_tick = 0;

    if (unit_list[temp_unit].target_lock > 2) {
        if (thresh_5 != 0 && unit_list[temp_unit].withdraw_flag == 0) set_ai_unit_withdraw(0, 8);
        return;
    }

    dl = unit_list[temp_unit].combat_order;
    if (dl == 0xa || dl == 8) return;

    if (thresh_2 == 1) { set_ai_unit_delayed_beserk(); return; }
    if (thresh_1 <= battle_ai_count) { set_ai_unit_beserk(); return; }

    dl = unit_list[temp_unit].flank_pending;
    if (dl == 1) { set_ai_flank_move(dl); unit_list[temp_unit].flank_pending = 0; return; }
    if (dl == 2) { set_ai_flank_move(dl); unit_list[temp_unit].flank_pending = 0; return; }
    if (dl == 3) { set_ai_flank_move(dl); unit_list[temp_unit].flank_pending = 0; return; }
    if (dl == 4) { set_ai_flank_move(dl); unit_list[temp_unit].flank_pending = 0; return; }

    if (unit_list[temp_unit].manoeuvre_done == 0 && thresh_3 != 0) {
        ai_pos = unit_list[temp_unit].x; if (ai_pos < 0x12) set_ai_unit_move(8, -12);
        else if (ai_pos > 0x1e) set_ai_unit_move(-10, -12);
        else set_ai_unit_move(0, -18);
        return;
    }

    if (unit_list[temp_unit].manoeuvre_done != 0) return; if (thresh_4 == 0) return; set_ai_unit_move(0, -4); unit_list[temp_unit].manoeuvre_done = 0;
}

// FUNCTION: C2 0x502F3
// WIN: 0x0047ca6a
// Lines 2133–2183
//
// Position every figure of temp_unit in a flank-line or
// flank-column formation.  `mode` selects the anchor column:
// 1 = left flank (roman_left_edge - 6), 2 = right flank
// (roman_right_edge + 8), 3 = centre (fixed at 0x2c); the
// column is clamped to [0, 0x33].  The tribe-AI flag picks
// between line and column formation (line_flank_data vs
// col_flank_data); mode 3 always uses line.  Each living
// figure gets state 7 (move-to-target), a column-mode marker
// when relevant, and a (target_x, target_y) drawn from the
// per-formation offset table.
void set_ai_flank_move(int mode)
{
    int col;
    int formation;
    int i;

    if (mode == 1) {
        col = roman_left_edge - 6;
    } else if (mode == 2) {
        col = roman_right_edge + 8;
    } else if (mode >= 3) {
        col = 0x2c;
    }
    if (col < 0) {
        col = 0;
    }
    if (col >= 0x34) {
        col = 0x33;
    }
    i = 0;
    formation = tribe_ai_data[bat_tribe].prefer_column;
    if (mode >= 3) {
        formation = 0;
    }
    if (formation == 1) {
        unit_list[temp_unit].combat_order = 7;
    } else {
        unit_list[temp_unit].combat_order = 3;
        if (mode == 2) {
            col -= unit_list[temp_unit].fig_count / 2;
        }
    }
    unit_list[temp_unit].manoeuvre_done = 1;
    for (temp_figure = unit_list[temp_unit].first_figure;
         temp_figure <= unit_list[temp_unit].last_figure;
         temp_figure++) {
        if (figure_list[temp_figure].exists == 0) continue;
        if (figure_list[temp_figure].state_idx == 2) continue;
        if (figure_list[temp_figure].state_idx == 0xc) continue;
        if (figure_list[temp_figure].state_idx == 0xa) continue;
        if (formation == 1) {
            figure_list[temp_figure].state_idx = 7;
            figure_list[temp_figure].shield_class = 1;
            figure_list[temp_figure].prev_grid_x = col + col_flank_data[i].dx;
            figure_list[temp_figure].prev_grid_y = col_flank_data[i].dy + (unit_list[temp_unit].y - 0x14);
        } else if (mode >= 3) {
            figure_list[temp_figure].state_idx = 7;
            figure_list[temp_figure].prev_grid_x = col + line_flank_data[i].dx;
            figure_list[temp_figure].prev_grid_y = line_flank_data[i].dy + (unit_list[temp_unit].y - mode * 2);
            col -= 2;
        } else {
            figure_list[temp_figure].state_idx = 7;
            figure_list[temp_figure].prev_grid_x = col + line_flank_data[i].dx;
            figure_list[temp_figure].prev_grid_y = line_flank_data[i].dy + (unit_list[temp_unit].y - 0x10);
        }
        i++;
    }
}


// FUNCTION: C2 0x504DF
// WIN: 0x0047ce22
// Lines 2186–2203
//
// Order temp_unit to move by (dx,dy).  The unit combat order is set
// to 3 and its AI flag armed.  Active figures in the unit are cleared
// from defend mode; non-terminal/non-routing figures are either sent
// into state 3 with prev_grid_x/y set to current+delta, or forced to
// berserk/state 10 if their current/target y falls above the top edge.
void set_ai_unit_move(int dx, int dy)
{
    int y_add;
    signed char new_y;

    y_add = dy;

    unit_list[temp_unit].combat_order = 3;
    unit_list[temp_unit].manoeuvre_done = 1;
    for (temp_figure = unit_list[temp_unit].first_figure;
         temp_figure <= unit_list[temp_unit].last_figure;
         temp_figure++) {
        if (figure_list[temp_figure].exists == 0) continue;
        figure_list[temp_figure].is_defending = 0;
        if (figure_list[temp_figure].state_idx == 2
            || figure_list[temp_figure].state_idx == 0xc
            || figure_list[temp_figure].state_idx == 0xa)
            continue;
        if (figure_list[temp_figure].grid_y < 6) {
            figure_list[temp_figure].state_idx = 0xa;
            return;
        }
        figure_list[temp_figure].state_idx = 3;
        figure_list[temp_figure].prev_grid_x = figure_list[temp_figure].grid_x + dx;
        new_y = (signed char)(figure_list[temp_figure].grid_y + y_add);
        figure_list[temp_figure].prev_grid_y = new_y;
        if (new_y <= 2) {
            figure_list[temp_figure].state_idx = 0xa;
            return;
        }
    }
}

// FUNCTION: C2 0x505AA
// WIN: 0x0047d04d
// Lines 2205–2218
//
// Order the current temp_unit to withdraw by delta (dx,dy).  The unit
// combat order is set to 8 and its withdraw flag is armed.  Every active
// non-routing figure in the unit is forced to state 8 and given a new
// destination at current grid position + delta.
void set_ai_unit_withdraw(int dx, int dy)
{
    int state;

    unit_list[temp_unit].combat_order = 8;
    unit_list[temp_unit].withdraw_flag = 1;
    for (temp_figure = unit_list[temp_unit].first_figure;
         unit_list[temp_unit].last_figure >= temp_figure;
         ++temp_figure) {
        if (figure_list[temp_figure].exists != 0) {
            figure_list[temp_figure].is_defending = 0;
            state = figure_list[temp_figure].state_idx;
            if (state != 0xc) {
                figure_list[temp_figure].state_idx = 8;
                figure_list[temp_figure].prev_grid_x = figure_list[temp_figure].grid_x + (char)dx;
                figure_list[temp_figure].prev_grid_y = figure_list[temp_figure].grid_y + (char)dy;
            }
        }
    }
}

// FUNCTION: C2 0x50646
// WIN: 0x0047d1b6
// Lines 2220–2232
//
// Switch the unit indexed by the global `temp_unit` into
// the berserk combat order, and propagate the order to
// every active figure in that unit.
//
//   1. unit_list[temp_unit].combat_order = 0xa  (berserk).
//   2. Walk figures from .first_figure to .last_figure
//      (inclusive); for each figure whose exists flag is nonzero:
//        * is_defending = 0   (a berserker can't shield).
//        * If state_idx is in {2 (sleep), 0xc (rout),
//          4 (some hold/wait state)} leave it; otherwise
//          force state_idx = 10 (charge/berserk state).
void set_ai_unit_beserk(void)
{
    int state;

    unit_list[temp_unit].combat_order = 10;
    for (temp_figure = unit_list[temp_unit].first_figure;
         unit_list[temp_unit].last_figure >= temp_figure;
         ++temp_figure) {
        if (figure_list[temp_figure].exists != 0) {
            figure_list[temp_figure].is_defending = 0;
            state = figure_list[temp_figure].state_idx;
            if (state != 2 && state != 0xc && state != 4) {
                figure_list[temp_figure].state_idx = 10;
            }
        }
    }
}

// FUNCTION: C2 0x506C5
// WIN: 0x0047d2f0
// Lines 2234–2248
//
// Sister of `set_ai_unit_beserk` that QUEUES a berserk
// transition rather than applying it immediately.  Each
// active figure in the unit gets state_idx = 1 (sf01_wait),
// next_state_idx = 10 (berserk), and wait_counter =
// 2 + (figure_no & 3) so the figures peel into the
// berserk state on staggered ticks (2–5 ticks of jitter).
void set_ai_unit_delayed_beserk(void)
{
    int state;

    unit_list[temp_unit].combat_order = 10;
    for (temp_figure = unit_list[temp_unit].first_figure;
         unit_list[temp_unit].last_figure >= temp_figure;
         ++temp_figure) {
        if (figure_list[temp_figure].exists != 0) {
            figure_list[temp_figure].is_defending = 0;
            state = figure_list[temp_figure].state_idx;
            if (state != 2 && state != 0xc && state != 4) {
                figure_list[temp_figure].state_idx = 1;
                figure_list[temp_figure].wait_counter =
                    ((temp_figure & 3) + 2);
                figure_list[temp_figure].next_state_idx = 10;
            }
        }
    }
}

// FUNCTION: C2 0x50760
// WIN: 0x0047d464
// Lines 2251–2266
//
// Put every active figure in temp_unit into auto-fire state unless
// it is already in one of the excluded combat states.  Also clears
// the per-figure defense flag and snapshots current grid position
// into prev_grid_x/prev_grid_y for the auto-fire animation.
void set_ai_unit_auto_fire(void)
{
    temp_figure = unit_list[temp_unit].first_figure;
    for ( ; temp_figure <= unit_list[temp_unit].last_figure; temp_figure++) {
    if (figure_list[temp_figure].exists != 0) {
            figure_list[temp_figure].is_defending = 0;
            if (figure_list[temp_figure].state_idx != 2) {
                if (figure_list[temp_figure].state_idx != 4) {
                    if (figure_list[temp_figure].state_idx != 8) {
                        if (figure_list[temp_figure].state_idx != 3) {
                            if (figure_list[temp_figure].state_idx != 0xc) {
                                if (figure_list[temp_figure].state_idx != 0xe) {
                                    figure_list[temp_figure].state_idx = 0xe;
                                    figure_list[temp_figure].prev_grid_y = figure_list[temp_figure].grid_y - 1;
                                    figure_list[temp_figure].prev_grid_x = figure_list[temp_figure].grid_x;
                                }
                            }
                        }
                    }
                }
            }
    }
    }
}

// FUNCTION: C2 0x50806
// WIN: 0x0047d64e
// Lines 2268–2306
//
// Once-per-tick morale + fatigue refresh over every battle unit,
// called from battle_game_loop.  Skips dead or routed units, then
// runs four steps:
//
//   A. Loss-driven morale drop: when losses_pct/5 exceeds the
//      unit's current tier threshold, look up a drop value from
//      losses_to_morale (banded by combat_order rank * 5) and
//      subtract it from morale + max_men, then advance the tier.
//   B. Fatigue cooldown when fatigue > 0x14: pay down -5 fatigue
//      and -1 morale per tick.
//   C. Morale regen while disengaged: every 25 idle ticks bump
//      morale back toward its max_men cap.
//   D. Rout trigger: at morale ≤ 10 call set_unit_to_rout, then
//      drop allied morale and raise enemy morale on this side.
void update_units_morale(void)
{
    struct unit_rec *unit;
    int losses_pct;
    int tier;
    unsigned char drop;

    for (temp_unit = 1; temp_unit < 0x33; temp_unit++) {
        if (unit_list[temp_unit].exists == 0)        continue;
        if (unit_list[temp_unit].combat_order == 0xc) continue;

        losses_pct = valueDIVtotal(
            unit_list[temp_unit].start_men - unit_list[temp_unit].current_men,
            unit_list[temp_unit].start_men);
        tier = losses_pct / 5;
        if (tier > unit_list[temp_unit].loss_tier) {
            drop = losses_to_morale[unit_list[temp_unit].loss_tier
                                    + (unit_list[temp_unit].owner - 1) * 5 * 4];
            unit_list[temp_unit].morale_a -= drop;
            unit_list[temp_unit].morale_b -= drop / 3;
            unit_list[temp_unit].loss_tier++;
        }

        if (unit_list[temp_unit].fatigue > 0x14) {
            unit_list[temp_unit].fatigue -= 5;
            if (unit_list[temp_unit].fatigue > 0x32) unit_list[temp_unit].fatigue = 0x32;
            unit_list[temp_unit].morale_a--;
            unit_list[temp_unit].fatigue_alert = 1;
        }

        if (unit_list[temp_unit].target_lock == 0) {
            unit_list[temp_unit].regen_tick++;
            if (unit_list[temp_unit].regen_tick > 0x19) {
                unit_list[temp_unit].regen_tick = 0;
                if (unit_list[temp_unit].morale_a < unit_list[temp_unit].morale_b) unit_list[temp_unit].morale_a++;
            }
        }

        if (unit_list[temp_unit].morale_a <= 10) {
            set_unit_to_rout(temp_unit);
            drop_all_units_morale(unit_list[temp_unit].type, 16, 6);
            raise_all_units_morale(unit_list[temp_unit].type, 10, 8);
        }
    }
}

// FUNCTION: C2 0x509C4
// WIN: 0x0047da3d  (unverified)
// Lines 2308–2320
//
// Mirror of raise_all_units_morale: walk unit_list[1..0x32]
// processing units of .type == match_type, dropping morale_a /
// morale_b by delta_a / delta_b.  Rank-2 (elite cohorts) take
// an additional 10 points off morale_a.  Each axis floored at 0.
void drop_all_units_morale(int match_type, int delta_a, int delta_b)
{
    int i;
    for (i = 1; i < 0x33; i++) {
        if (unit_list[i].exists == 0) continue;
        if ((unsigned char)unit_list[i].type != match_type) continue;
        if (unit_list[i].unit_rank == 2)
            unit_list[i].morale_a -= 10;
        unit_list[i].morale_a -= (char)delta_a;
        unit_list[i].morale_b -= (char)delta_b;
        if (unit_list[i].morale_a < 0) unit_list[i].morale_a = 0;
        if (unit_list[i].morale_b < 0) unit_list[i].morale_b = 0;
    }
}

// FUNCTION: C2 0x50A44
// WIN: 0x0047dbad  (unverified)
// Lines 2322–2333
//
// Raise morale_a/morale_b on every unit_list entry whose .type !=
// `skip_type`.  arg1 (eax) is the type to SKIP; arg2 (edx) is the
// morale_a delta; arg3 (ebx) is the morale_b delta.  Each axis is
// capped at 100 after the add.  Walks unit_list[1..0x32] (slot 0
// is reserved).
void raise_all_units_morale(int skip_type, int delta_a, int delta_b)
{
    int i;
    for (i = 1; i < 0x33; i++) {
        if (unit_list[i].exists == 0) continue;
        if ((unsigned char)unit_list[i].type == skip_type) continue;
        unit_list[i].morale_a += (char)delta_a;
        unit_list[i].morale_b += (char)delta_b;
        if (unit_list[i].morale_a > 0x64)
            unit_list[i].morale_a = 0x64;
        if (unit_list[i].morale_b > 0x64)
            unit_list[i].morale_b = 0x64;
    }
}

// FUNCTION: C2 0x50AB5
// WIN: 0x0047dcd4
// Lines 2335–2350
//
// Force unit `unit_no` to rout: zero its primary morale axis, set
// combat_order=0x0c, and walk all member figures.  Active figures not
// already in state 2 clear defending, enter rout state (0x0c), cache
// current x into prev_grid_x, and choose a y target from unit_position
// (-1 routes off-map north to 0xff, otherwise south to 0x34).
void set_unit_to_rout(int unit_no)
{
    int state;

    unit_list[unit_no].morale_a = 0;
    unit_list[unit_no].combat_order = 0xc;
    for (temp_figure = unit_list[unit_no].first_figure;
         unit_list[unit_no].last_figure >= temp_figure;
         ++temp_figure) {
        if (figure_list[temp_figure].exists != 0) {
            figure_list[temp_figure].is_defending = 0;
            state = figure_list[temp_figure].state_idx;
            if (state != 2) {
                figure_list[temp_figure].state_idx = 0xc;
                figure_list[temp_figure].prev_grid_x = figure_list[temp_figure].grid_x;
                if (figure_list[temp_figure].unit_position == -1)
                    figure_list[temp_figure].prev_grid_y = -1;
                else
                    figure_list[temp_figure].prev_grid_y = 0x34;
            }
        }
    }
    battle_tune_mood_from_type(unit_no);
}

// FUNCTION: C2 0x50B57
// WIN: 0x0047de58
// Lines 2352–2457
//
// Recompute the per-side and per-unit battle statistics shown in
// the unit-info panel and used to drive AI decisions.  Called
// from setup_battle (once) and battle_game_loop (every tick).
// Runs four passes:
//   * Pass 0: zero the our/their men/morale/unit-count globals,
//     seed the Roman bbox.
//   * Pass 1: clear each alive unit's anchor / slot caches.
//   * Pass 2: walk every alive figure, accumulating its anchor
//     (first figure of the unit wins), slot counter, HP into the
//     unit total, and expanding the Roman bbox for player-side
//     figures.
//   * Pass 3: mark each unit-empty as dead, then aggregate the
//     selected-unit `battle_stats_*` (mixed selection clamps the
//     type to 4 / 5), and roll our_battle_* / their_battle_*.
// Finally: get_battle_odds(); divide our/their/total
// morale by unit count to get the per-unit average.
void get_units_status(void)
{
    int u_idx;

    our_battle_men         = 0;
    their_battle_men       = 0;
    our_battle_morale      = 0;
    their_battle_morale    = 0;
    our_battle_units       = 0;
    their_battle_units     = 0;
    battle_stats_nof_units = 0;
    battle_stats_men       = 0;
    battle_stats_start_men = 0;
    battle_stats_morale    = 0;
    battle_stats_type      = 0;

    roman_left_edge  = 0x33;
    roman_right_edge = 0;
    roman_back_edge  = 0x33;
    roman_front_edge = 0;

    /* ---- Pass 1: clear per-unit fields for alive units. ---- */
    for (temp_unit = 1; temp_unit < 0x33; temp_unit++) {
        if (unit_list[temp_unit].exists == 0) continue;
        unit_list[temp_unit].target_lock       = 0;
        unit_list[temp_unit].has_selected_figs = 0;
        unit_list[temp_unit].first_figure      = 0;
        unit_list[temp_unit].fig_count         = 0;
        unit_list[temp_unit].last_figure       = 0;
        unit_list[temp_unit].current_men       = 0;
    }

    /* ---- Pass 2: per-figure accumulate. ---- */
    for (temp_figure = 1; temp_figure < 0xc9; temp_figure++) {
        if (figure_list[temp_figure].exists == 0) continue;

        u_idx = figure_list[temp_figure].unit_ref;
        figure_list[temp_figure].unit_type = unit_list[u_idx].fig_count;

        if (figure_list[temp_figure].state_idx == 4)
            unit_list[u_idx].target_lock++;

        if (figure_list[temp_figure].selected != 0)
            unit_list[u_idx].has_selected_figs = 1;

        if (unit_list[u_idx].first_figure == 0) {
            unit_list[u_idx].first_figure = temp_figure;
            unit_list[u_idx].x = figure_list[temp_figure].grid_x;
            unit_list[u_idx].y = figure_list[temp_figure].grid_y;
        }

        unit_list[u_idx].fig_count++;
        unit_list[u_idx].last_figure = temp_figure;
        unit_list[u_idx].current_men += figure_list[temp_figure].stampede_flag;

        if (figure_list[temp_figure].owner != 0) {
            if (figure_list[temp_figure].grid_x < roman_left_edge)  roman_left_edge  = figure_list[temp_figure].grid_x;
            if (figure_list[temp_figure].grid_x > roman_right_edge) roman_right_edge = figure_list[temp_figure].grid_x;
            if (figure_list[temp_figure].grid_y < roman_back_edge)  roman_back_edge  = figure_list[temp_figure].grid_y;
            if (figure_list[temp_figure].grid_y > roman_front_edge) roman_front_edge = figure_list[temp_figure].grid_y;
        }
    }

    /* ---- Pass 3: per-unit finalize + battle_stats. ---- */
    for (temp_unit = 1; temp_unit < 0x33; temp_unit++) {
        if (unit_list[temp_unit].exists == 0) continue;

        if (unit_list[temp_unit].fig_count == 0) {
            unit_list[temp_unit].exists = 0;
            battle_tune_mood_from_type(temp_unit);
        }

        if (unit_list[temp_unit].has_selected_figs != 0 && unit_list[temp_unit].type != 0) {
            battle_stats_control = 1;
            battle_stats_nof_units += 1;
            battle_stats_men       += unit_list[temp_unit].current_men;
            battle_stats_start_men += unit_list[temp_unit].start_men;
            battle_stats_morale    += unit_list[temp_unit].morale_a;
            if (battle_stats_type == 0) {
                battle_stats_type = unit_list[temp_unit].owner;
                if (battle_stats_type > 4)
                    battle_stats_type = 5;
            } else if (unit_list[temp_unit].owner != battle_stats_type) {
                battle_stats_type = 4;
            }
        }
        if (unit_list[temp_unit].has_selected_figs != 0 && unit_list[temp_unit].type == 0) {
            battle_stats_nof_units = 1;
            battle_stats_men       = unit_list[temp_unit].current_men;
            battle_stats_start_men = unit_list[temp_unit].start_men;
            battle_stats_morale    = unit_list[temp_unit].morale_a;
            battle_stats_type      = unit_list[temp_unit].owner;
            battle_stats_control   = 0;
        }

        if (unit_list[temp_unit].type != 0) {
            our_battle_men    += unit_list[temp_unit].current_men;
            our_battle_morale += unit_list[temp_unit].morale_a;
            our_battle_units++;
        } else {
            their_battle_men    += unit_list[temp_unit].current_men;
            their_battle_morale += unit_list[temp_unit].morale_a;
            their_battle_units++;
        }
    }

    get_battle_odds();

    if (our_battle_units != 0)
        our_battle_morale /= our_battle_units;
    if (their_battle_units != 0)
        their_battle_morale /= their_battle_units;
    if (battle_stats_nof_units != 0)
        battle_stats_morale /= battle_stats_nof_units;

}

// FUNCTION: C2 0x50F6D
// WIN: 0x0047e676
// Lines 2460–2483
//
// Convert unit type/owner into the battle music mood bucket and hold
// it.  Units with non-zero .type use moods 6..9 by .owner; zero-type
// barbarian / animal / siege unit classes map to the later mood range.
void battle_tune_mood_from_type(int unit_no)
{
    int t;

    if (unit_list[unit_no].type != 0) {
        t = unit_list[unit_no].owner;
        if (t == 1) tune_mood = 6;
        else if (t == 2) tune_mood = 7;
        else if (t == 3) tune_mood = 8;
        else tune_mood = 9;
    } else {
        t = unit_list[unit_no].owner;
        if (t == 5) tune_mood = 0xd;
        else if (t == 7) tune_mood = 0xd;
        else if (t == 8) tune_mood = 0xd;
        else if (t == 6) tune_mood = 0xc;
        else if (t == 0xb) tune_mood = 0xe;
        else if (t == 0xc) tune_mood = 0xe;
        else if (t == 0xd) tune_mood = 0xe;
        else if (t == 0xe) tune_mood = 0xf;
        else if (t == 0xf) tune_mood = 0x10;
        else tune_mood = 0xb;
    }
    tune_mood_hold = 1;
}

// FUNCTION: C2 0x5105B
// WIN: 0x0047e8ea
// Lines 2485–2511
//
// Re-bind every figure of the unit owning `start_fig` into the fight
// state: "backtrack" any figure that was already engaged, copy the
// trigger figure's facing into it, and pick a fight state_idx of 9
// (defending) or 0xa (attacking).  Used by set_engaged_figures
// after a fight is joined.
void set_unit_to_fight(int start_fig)
{
    int   state;

    temp_unit = figure_list[start_fig].unit_ref;

    for (temp_figure = unit_list[temp_unit].first_figure;
         temp_figure <= unit_list[temp_unit].last_figure;
         temp_figure++) {
        if (figure_list[temp_figure].exists != 0) {
            if (figure_list[temp_figure].owner == 0) {
                figure_list[figure_no].is_defending = 0;
            }
            if (figure_list[temp_figure].is_defending != 0
                && unit_list[temp_unit].target_lock == 0
                && figure_list[temp_figure].backtrack_flag != 0)
            {
                figure_list[temp_figure].is_visible |= 1;
                backtrack_figure(temp_figure);
                figure_list[temp_figure].direction =
                    figure_list[figure_no].backtrack_dirc;
                figure_list[temp_figure].wf_step_x = 0;
                figure_list[temp_figure].backtrack_flag = 0;
            }
            state = figure_list[temp_figure].state_idx;
            if (state != 4 && state != 2 && state != 0xc) {
                if (figure_list[temp_figure].is_defending != 0) {
                    figure_list[temp_figure].state_idx = 9;
                } else {
                    figure_list[temp_figure].state_idx = 0xa;
                }
            }
        }
    }
}

// FUNCTION: C2 0x51189
// WIN: 0x0047eb78
// Lines 2515–2641
//
// Drive figure_no one tick toward its current move / fight target.
// Called from the sf03_move / sf04_fight / sf07_reform dispatchers
// after they have set up the target and heading.  Returns 1 when
// the figure moved (or finished), 0 when the per-tick timer hasn't
// expired or the move was blocked.
//
// Phase 1 ticks the cooldown timer (sub-tick + tick counter +
// timer-elapsed flag), short-circuiting until the per-figure speed
// elapses.  Phase 2 picks a direction: a fresh get_heading toward
// the target when no override exists, the cached override
// otherwise; an invalid direction (≥ 8) drops the figure into stop.
// Phase 3 probes the destination cell via try_a_battlemap_square;
// 0x3E7 is fold-up for "blocked by an enemy" → transition into
// fight state 4, 0 is "blocked by terrain" → idle state 1.5,
// anything else commits the move via move_figure().
//
// SHAPE 2026-07-11: byte-exact.  WIN /Od exposed one invented local: the
// stampede limit and later movement result share `dir_out`; that fixes
// WIN's frame from 12 to 8 bytes / three to two slots.  Trace-v56
// temp-birth attribution then overturned the old single-edit verdicts:
// the cooldown longhand creates two anonymous byte temps, while the
// explicit three-way state 7/state 8/enemy-state 2 branches change the
// later temp order.  Neither rewrite works alone, but composing the
// original-looking `--wf_ttl` guard with those three explicit branches
// restores PS's L2608 move and fixes the is_routing + move-step seats.
// The corrected InsToAddr/temp-birth graph then showed that the chained
// zero assignment invented one extra compiler temp.  Two literal stores,
// the shared movement-return funnel, and the cap!=0 goto recover the PS
// walk exactly.  `line-compare` reports no direction divergence.
// `stampede_kind` is explicitly promoted unsigned: PS and WIN both
// zero-extend it, and the cast drops WIN structural differences 47->31
// while leaving the DOS shape/bytes unchanged.
// Keep declarations in strict-C89 function-front form.
int figure_go_to_target(void)
{
    int dir_out;
    int cap;

    fig_at_edge = 0;

    if (figure_list[figure_no].is_visible & 1) {
        figure_list[figure_no].wf_step_x = 0;
        figure_list[figure_no].wf_step_y = 0;
    } else {
        figure_list[figure_no].backtrack_flag = 0;
        dir_out = (unsigned char)figure_list[figure_no].stampede_kind;
        set_battle_march_fx(figure_list[figure_no].sprite_type);

        figure_list[figure_no].wf_step_y++;
        if (figure_list[figure_no].wf_step_y <= dir_out)
            goto movement_wait;
        figure_list[figure_no].wf_step_y = 0;
        figure_list[figure_no].wf_step_x++;
        if (figure_list[figure_no].wf_step_x <= 7)
            goto movement_wait;
        figure_list[figure_no].is_visible |= 1;
        figure_list[figure_no].wf_step_x = 0;
        goto movement_ready;
movement_wait:
        return 0;
movement_ready:
        ;
    }

    /* ---- Phase 2: heading. ---- */
    if (figure_list[figure_no].is_routing == 0)
        return 1;

    if (figure_list[figure_no].wf_searching != 0
        && --figure_list[figure_no].wf_ttl <= 0)
        figure_list[figure_no].wf_searching = 0;
    if (figure_list[figure_no].wf_searching == 0) {
        w_dirc = get_heading(figure_list[figure_no].grid_x, figure_list[figure_no].grid_y,
                             figure_list[figure_no].prev_grid_x, figure_list[figure_no].prev_grid_y,
                             figure_list[figure_no].direction);
    } else {
        w_dirc = figure_list[figure_no].wf_dirc;
    }

    if (w_dirc >= 8) {
        figure_list[figure_no].is_routing = 0;
        figure_list[figure_no].is_visible |= 2;
        return 1;
    }

    /* ---- Phase 3: try to step. ---- */
    dir_out = try_a_battlemap_square(w_dirc);
    if (dir_out == 0) {
        if (figure_list[enemy_figure].state_idx == 2) {
            dir_out = get_wf_dirc(1);
        } else if (figure_list[figure_no].is_defending != 0) {
            /* Same unit: do not fight self. */
            if ((figure_list[enemy_figure].unit_ref) != (figure_list[figure_no].unit_ref)) {
                if (figure_list[enemy_figure].state_idx != 0xf && figure_list[enemy_figure].next_state_idx != 0xf) {
                    dir_out = get_wf_dirc(2);
                } else {
                    figure_list[figure_no].next_state_idx = figure_list[figure_no].state_idx;
                    figure_list[figure_no].state_idx = 1;
                    figure_list[figure_no].wait_counter = 1;
                    get_fig_still_image();
                    return 0;
                }
            } else {
                figure_list[figure_no].next_state_idx = figure_list[figure_no].state_idx;
                figure_list[figure_no].state_idx = 1;
                figure_list[figure_no].wait_counter = 1;
                get_fig_still_image();
                return 0;
            }
        } else if (figure_list[figure_no].state_idx == 7) {
            cap = swap_2_figures();
            if (cap == 2) {
                figure_list[enemy_figure].state_idx = 1;
                figure_list[enemy_figure].next_state_idx = 7;
                figure_list[enemy_figure].wait_counter = 2;
                figure_list[enemy_figure].is_defending = 0;
                figure_list[enemy_figure].prev_grid_x = figure_list[figure_no].grid_x;
                figure_list[enemy_figure].prev_grid_y = figure_list[figure_no].grid_y;
                return 0;
            }
            if (cap != 0)
                goto cap_wander;
            figure_list[figure_no].state_idx = 1;
            figure_list[figure_no].next_state_idx = 7;
            figure_list[figure_no].wait_counter = 1;
            get_fig_still_image();
            return 0;
cap_wander:
            dir_out = get_wf_dirc(2);
        } else {
            dir_out = get_wf_dirc(1);
            if (dir_out == 0) {
                get_fig_still_image();
            }
        }
    }

    if (dir_out == 0x3e7) {
        /* ---- Combat resolution. ---- */
        if (figure_list[figure_no].state_idx == 2)
            return 0;
        if (figure_list[figure_no].state_idx == 7) {
            dir_out = get_wf_dirc(0);
        } else if (figure_list[figure_no].state_idx == 8) {
            dir_out = get_wf_dirc(0);
        } else if (figure_list[enemy_figure].state_idx == 2) {
            dir_out = get_wf_dirc(0);
        } else {
            set_unit_to_fight(figure_no);
            figure_list[figure_no].state_idx = 4;
            figure_list[figure_no].fight_direction = w_dirc;
            figure_list[figure_no].opponent = enemy_figure;
            figure_list[figure_no].fight_role = 1;
            set_attack_count(figure_no);
            if (figure_list[enemy_figure].state_idx != 4) {
                set_unit_to_fight(enemy_figure);
                figure_list[enemy_figure].state_idx = 4;
                figure_list[enemy_figure].fight_direction = (w_dirc + 4) % 8;
                figure_list[enemy_figure].opponent = figure_no;
                figure_list[enemy_figure].fight_role = 2;
                set_defense_shield(enemy_figure);
            }
            return 0;
        }
    }

    if (dir_out == 0) {
        if (figure_list[figure_no].state_idx == 2)
            return 0;
        figure_list[figure_no].next_state_idx = figure_list[figure_no].state_idx;
        figure_list[figure_no].state_idx = 1;
        figure_list[figure_no].wait_counter = 5;
        return 0;
    }
    if (dir_out == 0x3e7)
        return 0;

    /* ---- Move step. ---- */
    figure_list[figure_no].is_visible &= 0xfe;
    figure_list[figure_no].backtrack_dirc = figure_list[figure_no].direction;
    figure_list[figure_no].direction = w_dirc;
    figure_list[figure_no].wf_step_x = 1;
    move_figure(figure_no);
    figure_list[figure_no].backtrack_flag = 1;
    return 1;
}

// FUNCTION: C2 0x515E0
// WIN: 0x0047f57d
// Lines 2643–2663
//
// If figure_no and enemy_figure belong to the same unit and the
// enemy is in state 6 (the post-charge rotation state), swap their
// (grid_x, grid_y, map_ref) tuples and re-stamp the battle_map
// occupancy bytes so the two figures trade places.  Return code
// tells move_figure what happened:
//   1 — different units, or already in state 1 (no swap)
//   0 — enemy in some other state (no swap)
//   2 — swap performed
int swap_2_figures(void)
{
    int   temp_y;
    int   temp_x;
    int   temp_map_ref;

    if (figure_list[enemy_figure].unit_ref != figure_list[figure_no].unit_ref) return 1;

    if (figure_list[enemy_figure].state_idx == 1) return 1;
    if (figure_list[enemy_figure].state_idx != 6) return 0;

    temp_x       = figure_list[figure_no].grid_x;
    temp_y       = figure_list[figure_no].grid_y;
    temp_map_ref = figure_list[figure_no].map_ref;

    figure_list[figure_no].grid_x  = figure_list[enemy_figure].grid_x;
    figure_list[figure_no].grid_y  = figure_list[enemy_figure].grid_y;
    figure_list[figure_no].map_ref = figure_list[enemy_figure].map_ref;

    figure_list[enemy_figure].grid_x  = temp_x;
    figure_list[enemy_figure].grid_y  = temp_y;
    figure_list[enemy_figure].map_ref = temp_map_ref;

    (*(struct battle_cell *)((unsigned char *)battle_map + (figure_list[figure_no].map_ref))).figure = figure_no;
    (*(struct battle_cell *)((unsigned char *)battle_map + (figure_list[enemy_figure].map_ref))).figure = enemy_figure;
    return 2;
}

// FUNCTION: C2 0x516CB
// WIN: 0x0047f786
// Lines 2665–2709
//
// Compute the destination cell for figure_no stepping one tile in
// direction `dir` (0..7), enforcing grid bounds: an off-grid step
// sets fig_at_edge = 1 and returns 0; otherwise tail-call into
// try_this_battlemap_square(dest_cell_off) which returns 0/1 or a
// large special code (>= 0x3e7).  dir > 7 short-circuits to 0
// without touching fig_at_edge.
int try_a_battlemap_square(int dir)
{
    int r;
    r = 0;
    switch (dir) {
    case 0:  /* N */
        if (figure_list[figure_no].grid_y <= 0) {
            fig_at_edge = 1;
            r = 0;
        } else {
            r = try_this_battlemap_square(figure_list[figure_no].map_ref - 0xd0);
        }
        break;
    case 1:  /* NE */
        if (figure_list[figure_no].grid_x < 0x33) {
            if (figure_list[figure_no].grid_y <= 0) {
                fig_at_edge = 1;
                r = 0;
            } else {
                r = try_this_battlemap_square(figure_list[figure_no].map_ref - 0xcc);
            }
        } else {
            fig_at_edge = 1;
            r = 0;
        }
        break;
    case 2:  /* E */
        if (figure_list[figure_no].grid_x < 0x33) {
            r = try_this_battlemap_square(figure_list[figure_no].map_ref + 4);
        } else {
            fig_at_edge = 1;
            r = 0;
        }
        break;
    case 3:  /* SE */
        if (figure_list[figure_no].grid_x < 0x33) {
            if (figure_list[figure_no].grid_y < 0x33) {
                r = try_this_battlemap_square(figure_list[figure_no].map_ref + 0xd4);
            } else {
                fig_at_edge = 1;
                r = 0;
            }
        } else {
            fig_at_edge = 1;
            r = 0;
        }
        break;
    case 4:  /* S */
        if (figure_list[figure_no].grid_y < 0x33) {
            r = try_this_battlemap_square(figure_list[figure_no].map_ref + 0xd0);
        } else {
            fig_at_edge = 1;
            r = 0;
        }
        break;
    case 5:  /* SW */
        if (figure_list[figure_no].grid_x <= 0) {
            fig_at_edge = 1;
            r = 0;
        } else if (figure_list[figure_no].grid_y < 0x33) {
            r = try_this_battlemap_square(figure_list[figure_no].map_ref + 0xcc);
        } else {
            fig_at_edge = 1;
            r = 0;
        }
        break;
    case 6:  /* W */
        if (figure_list[figure_no].grid_x <= 0) {
            fig_at_edge = 1;
            r = 0;
        } else {
            r = try_this_battlemap_square(figure_list[figure_no].map_ref - 4);
        }
        break;
    case 7:  /* NW */
        if (figure_list[figure_no].grid_x <= 0) {
            fig_at_edge = 1;
            r = 0;
        } else if (figure_list[figure_no].grid_y <= 0) {
            fig_at_edge = 1;
            r = 0;
        } else {
            r = try_this_battlemap_square(figure_list[figure_no].map_ref - 0xd4);
        }
        break;
    }
    return r;
}

// FUNCTION: C2 0x5185C
// WIN: 0x0047fb65
// Lines 2712–2730
//
// Test what figure (if any) occupies a battlemap cell relative to the
// active figure_no, and apply on-contact bookkeeping when meeting an
// enemy.  `cell_off` is the byte offset within battle_map (caller has
// already turned (x,y) into y * 0x34 + x scaled by 4).
//
// Returns:
//   1     — square is empty (target moves into it freely)
//   0     — occupied by ally, or by a fellow cavalry-class (0xf) unit
//           that we now flag for death
//   0x3e7 — occupied by an enemy of a class we cannot enter (caller
//           uses this as a blocker code)
int try_this_battlemap_square(int cell_off)
{
    int my_class;
    int my_state;

    enemy_figure = (*(struct battle_cell *)((unsigned char *)battle_map + ((cell_off)))).figure;
    if (enemy_figure != 0) {
        my_class = figure_list[figure_no].sprite_type;
        if (my_class == 0xf) {
            my_state = figure_list[figure_no].state_idx;
            if (my_state == 2) {
                figure_list[enemy_figure].state_idx   = 2;
                figure_list[enemy_figure].death_timer = 0x1e;
                return 0;
            }
            if (figure_list[enemy_figure].owner == figure_list[figure_no].owner) {
                return 0;
            }
            figure_list[enemy_figure].state_idx   = 2;
            figure_list[enemy_figure].death_timer = 0x1e;
            return 0;
        }
        if (figure_list[enemy_figure].owner == figure_list[figure_no].owner) {
            return 0;
        }
        return 0x3e7;
    }
    return 1;
}

// FUNCTION: C2 0x51927
// WIN: 0x0047fccd  (unverified)
// Lines 2733–2785
//
// Move a figure forward one cell along its current direction; if
// the destination cell is already occupied the figure is destroyed
// (low_beep + remove_figure) instead.  Mirror of backtrack_figure
// with opposite signs on every (dx, dy) pair, but with collision
// detection on the destination cell.
void move_figure(int fig)
{
    int   old_cell = figure_list[fig].map_ref;
    int   new_cell;
    int   prev;

    prev = ((unsigned char *)battle_map)[(old_cell) + 1];
    if (prev == fig) {
        ((unsigned char *)battle_map)[(old_cell) + 1] = 0;
    }

    switch ((unsigned char)figure_list[fig].direction) {
    case 0:
        figure_list[fig].grid_y--;
        figure_list[fig].map_ref -= 0xd0;
        break;
    case 1:
        figure_list[fig].grid_y--;
        figure_list[fig].grid_x++;
        figure_list[fig].map_ref -= 0xcc;
        break;
    case 2:
        figure_list[fig].grid_x++;
        figure_list[fig].map_ref += 0x04;
        break;
    case 3:
        figure_list[fig].grid_y++;
        figure_list[fig].grid_x++;
        figure_list[fig].map_ref += 0xd4;
        break;
    case 4:
        figure_list[fig].grid_y++;
        figure_list[fig].map_ref += 0xd0;
        break;
    case 5:
        figure_list[fig].grid_y++;
        figure_list[fig].grid_x--;
        figure_list[fig].map_ref += 0xcc;
        break;
    case 6:
        figure_list[fig].grid_x--;
        figure_list[fig].map_ref -= 0x04;
        break;
    case 7:
        figure_list[fig].grid_y--;
        figure_list[fig].grid_x--;
        figure_list[fig].map_ref -= 0xd4;
        break;
    default:
        return;
    }
    new_cell = figure_list[fig].map_ref;

    if (((unsigned char *)battle_map)[(new_cell) + 1] == 0) {
        ((unsigned char *)battle_map)[(new_cell) + 1] = fig;
        return;
    }
    low_beep();
    remove_figure(fig);
}

// FUNCTION: C2 0x51A5F
// WIN: 0x0047ffbe  (unverified)
// Lines 2788–2838
//
// Step a figure backward one cell along its current direction (used
// when a forward move was illegal).  Reads figure.+0x12 (battle-map
// cell offset, stride 4 bytes per cell / 52 cells per row), 0x6
// (direction 0..7), and updates the cell-offset and figure.+0x8/+0x9
// (x/y) by the dir-specific (dx, dy) pair:
//
//     0  ( 0, +1)   S
//     1  (-1, +1)   SW
//     2  (-1,  0)   W
//     3  (-1, -1)   NW
//     4  ( 0, -1)   N
//     5  (+1, -1)   NE
//     6  (+1,  0)   E
//     7  (+1, +1)   SE
//
// Clears the old BM_FIGURE(cell) slot when it still pointed at
// this figure, then stamps the new slot with the figure index.  Dir
// values > 7 bail without moving (defensive against corrupt data).
void backtrack_figure(int fig)
{
    int   old_cell = figure_list[fig].map_ref;
    int   new_cell;
    int   prev;

    prev = ((unsigned char *)battle_map)[(old_cell) + 1];
    if (prev == fig) {
        ((unsigned char *)battle_map)[(old_cell) + 1] = 0;
    }

    switch ((unsigned char)figure_list[fig].direction) {
    case 4:
        figure_list[fig].grid_y--;
        figure_list[fig].map_ref -= 0xd0;
        break;
    case 5:
        figure_list[fig].grid_y--;
        figure_list[fig].grid_x++;
        figure_list[fig].map_ref -= 0xcc;
        break;
    case 6:
        figure_list[fig].grid_x++;
        figure_list[fig].map_ref += 0x04;
        break;
    case 7:
        figure_list[fig].grid_y++;
        figure_list[fig].grid_x++;
        figure_list[fig].map_ref += 0xd4;
        break;
    case 0:
        figure_list[fig].grid_y++;
        figure_list[fig].map_ref += 0xd0;
        break;
    case 1:
        figure_list[fig].grid_y++;
        figure_list[fig].grid_x--;
        figure_list[fig].map_ref += 0xcc;
        break;
    case 2:
        figure_list[fig].grid_x--;
        figure_list[fig].map_ref -= 0x04;
        break;
    case 3:
        figure_list[fig].grid_y--;
        figure_list[fig].grid_x--;
        figure_list[fig].map_ref -= 0xd4;
        break;
    default:
        return;
    }
    new_cell = figure_list[fig].map_ref;
    ((unsigned char *)battle_map)[(new_cell) + 1] = fig;
}

// FUNCTION: C2 0x51B58
// WIN: 0x00480277
// Lines 2840–2850
//
// Translate an 8-way heading into the adjacent battle_map cell and stamp it as the
// figure's next target slot (prev_grid_x / prev_grid_y).  Directions outside 0..7
// leave the slot unchanged.
void target_from_figure_dirc(int dir)
{
    /* Translate an 8-way heading into the adjacent
       battle_map cell and stamp it as the figure’s next
       target slot (fl[+0x18], fl[+0x19]).  Directions
       outside 0..7 leave the slot unchanged. */
    if (dir == 0) {
        figure_list[figure_no].prev_grid_x = figure_list[figure_no].grid_x;
        figure_list[figure_no].prev_grid_y = (figure_list[figure_no].grid_y - 1);
    } else if (dir == 2) {
        figure_list[figure_no].prev_grid_x = (figure_list[figure_no].grid_x + 1);
        figure_list[figure_no].prev_grid_y = figure_list[figure_no].grid_y;
    } else if (dir == 4) {
        figure_list[figure_no].prev_grid_x = figure_list[figure_no].grid_x;
        figure_list[figure_no].prev_grid_y = (figure_list[figure_no].grid_y + 1);
    } else if (dir == 6) {
        figure_list[figure_no].prev_grid_x = (figure_list[figure_no].grid_x - 1);
        figure_list[figure_no].prev_grid_y = figure_list[figure_no].grid_y;
    } else if (dir == 1) {
        figure_list[figure_no].prev_grid_x = (figure_list[figure_no].grid_x + 1);
        figure_list[figure_no].prev_grid_y = (figure_list[figure_no].grid_y - 1);
    } else if (dir == 3) {
        figure_list[figure_no].prev_grid_x = (figure_list[figure_no].grid_x + 1);
        figure_list[figure_no].prev_grid_y = (figure_list[figure_no].grid_y + 1);
    } else if (dir == 5) {
        figure_list[figure_no].prev_grid_x = (figure_list[figure_no].grid_x - 1);
        figure_list[figure_no].prev_grid_y = (figure_list[figure_no].grid_y + 1);
    } else if (dir == 7) {
        figure_list[figure_no].prev_grid_x = (figure_list[figure_no].grid_x - 1);
        figure_list[figure_no].prev_grid_y = (figure_list[figure_no].grid_y - 1);
    }
}

// FUNCTION: C2 0x51C64
// WIN: 0x004805cd
// Lines 2854–2892
//
// Walking-fighter direction picker.  First tries the heading
// straight toward the target (current grid → prev grid) via
// try_a_battlemap_square; on a free square commits it to wf_dirc
// and clears the search state.
//
// On failure runs a fallback sweep of up to 8 neighbouring
// directions, picking each candidate per `mode`:
//   1 — wf_battle_dircs[i] + current direction
//   2 — wf_battle_dircs[i] + desired heading
//   0 — inc/dec wf_dirc per wf_orient (alternate sides)
// each wrapped to 0..7 and skipping the direct-reverse of the
// figure's facing.  wf_searching / wf_orient / wf_ttl carry the
// sweep state across ticks.  Mode 0 accepts only a fully free
// square (< 0x3e7); modes 1 and 2 return on any non-zero result.
int get_wf_dirc(int mode)
{
  int i;
  int target_dirc;
  int got;
  int dir;
  int heading;
  int wd;
  i = 0;
  dir = figure_list[figure_no].direction;
  target_dirc = (dir + 4) % 8;
  heading = get_heading(figure_list[figure_no].grid_x, figure_list[figure_no].grid_y, figure_list[figure_no].prev_grid_x, figure_list[figure_no].prev_grid_y, dir);
  got = try_a_battlemap_square(heading);
  if (got == 1)
  {
    w_dirc = heading;
    figure_list[figure_no].wf_dirc = heading;
    figure_list[figure_no].wf_searching = 0;
    return 1;
  }
  if (figure_list[figure_no].wf_searching == 0)
  {
    figure_list[figure_no].wf_ttl = 2;
    figure_list[figure_no].wf_searching = 1;
    figure_list[figure_no].wf_orient ^= 1;
  }
  else
  {
    figure_list[figure_no].wf_ttl--;
    if (figure_list[figure_no].wf_ttl <= 0)
    {
      figure_list[figure_no].wf_searching = 0;
    }
  }
  wd = w_dirc;
  figure_list[figure_no].wf_dirc = wd;
  while (i < 8)
  {
    if (mode == 1)
    {
      figure_list[figure_no].wf_dirc = wf_battle_dircs[i] + wd;
    }
    else
      if (mode == 2)
    {
      figure_list[figure_no].wf_dirc = wf_battle_dircs[i] + heading;
    }
    else
    {
      if (figure_list[figure_no].wf_orient == 1)
      {
        figure_list[figure_no].wf_dirc++;
      }
      else
      {
        figure_list[figure_no].wf_dirc--;
      }
    }
    if (figure_list[figure_no].wf_dirc >= 8)
      figure_list[figure_no].wf_dirc = 0;
    if (figure_list[figure_no].wf_dirc < 0)
      figure_list[figure_no].wf_dirc = 7;
    if (figure_list[figure_no].wf_dirc != target_dirc)
    {
      w_dirc = figure_list[figure_no].wf_dirc;
      got = try_a_battlemap_square(w_dirc);
      if (mode != 0)
      {
        if (got != 0)
          return got;
      }
      else
      {
        if ((got != 0) && (got < 0x3e7))
          return 1;
      }
    }
    i++;
    if ((i >= 2) && (figure_list[figure_no].state_idx == 0xa))
      break;
  }

  return 0;
}


// FUNCTION: C2 0x51E5A
// WIN: 0x004809d7
// Lines 2895–2948
//
// Step an in-flight arrow toward its target and resolve any
// collision; called per tick from arrow_intelligence for the
// current arrow_no.  Ticks the per-arrow fuse first and clears
// the arrow on expiry.  Then runs two move legs (one for cardinal
// dominant arrows, two for diagonals): each leg advances the
// active axis via move_arrow_vert / move_arrow_horiz, decrements
// the remaining step on that axis, and clears the arrow if it
// runs off the map.  After each move recomputes the destination
// battle_map cell and checks for a same-side miss / opposing
// hit.  On a hit, accumulates a damage score (per-figure speed
// bonus + missile delta_anim / 4, with armour / shield penalties),
// applies it to the victim's hit counter once it crosses 10 hits,
// kills the figure on HP ≤ 0 (state 2 = dead), and clears the
// arrow.  When no hit is scored the arrow stamps its slot into
// the destination cell so the next tick can chain into it.

void fly_to_target(void)
{
    int i;
    int delta_anim;
    int score;

    arrow_list[arrow_no].flight_age = arrow_list[arrow_no].flight_age + 1;
    if (arrow_list[arrow_no].flight_age > arrow_list[arrow_no].fire_speed) {
        clear_arrow(&arrow_list[arrow_no]);
        return;
    }

    for (i = 0; i < 2; i++) {
        if (arrow_list[arrow_no].step_x + arrow_list[arrow_no].step_y <= 0) {
            loose_arrow_move();
        } else {
            bd(arrow_list[arrow_no].axis_dominant);
            if (arrow_list[arrow_no].axis_dominant == 2) {
                move_arrow_vert();
                if (arrow_list[arrow_no].step_error >= 0) {
                    arrow_list[arrow_no].step_x--;
                    move_arrow_horiz();
                }
            } else {
                move_arrow_horiz();
                if (arrow_list[arrow_no].step_error >= 0) {
                    arrow_list[arrow_no].step_y--;
                    move_arrow_vert();
                }
            }
        }

        if (arrow_off_map() != 0) {
            clear_arrow(&arrow_list[arrow_no]);
            return;
        }

        arrow_list[arrow_no].grid_x = arrow_list[arrow_no].start_x / 7;
        arrow_list[arrow_no].grid_y = arrow_list[arrow_no].start_y / 7;
        arrow_list[arrow_no].map_ref = (arrow_list[arrow_no].grid_y * 0x34 + arrow_list[arrow_no].grid_x) * 4;

        enemy_figure = ((unsigned char *)battle_map)[arrow_list[arrow_no].map_ref + 1];
        if (enemy_figure == 0) continue;
        if (figure_list[enemy_figure].state_idx == 2) continue;
        if (figure_list[enemy_figure].owner == arrow_list[arrow_no].owner) continue;

        temp_unit = figure_list[enemy_figure].unit_ref;
        unit_list[temp_unit].fatigue++;

        delta_anim = (arrow_list[arrow_no].fire_speed - arrow_list[arrow_no].flight_age) / 4;
        score = (arrow_list[arrow_no].fire_range + delta_anim) / 0x14;

        if (figure_list[enemy_figure].defense > 0) {
            if (figure_list[enemy_figure].sub_state > 2) score--;
            if (figure_list[enemy_figure].is_defending != 0 && figure_list[enemy_figure].shield_class == 2)
                score--;
        }
        if (score > 0) {
            figure_list[enemy_figure].kill_counter += score;
            if (figure_list[enemy_figure].kill_counter >= 0xa) {
                figure_list[enemy_figure].kill_counter = 0;
                figure_list[enemy_figure].stampede_flag--;
                set_missile_fight_fx(arrow_list[arrow_no].weapon_kind);
            }
            if (figure_list[enemy_figure].stampede_flag <= 0) {
                figure_list[enemy_figure].stampede_flag = 0;
                figure_list[enemy_figure].state_idx = 2;
            }
        }

        clear_arrow(&arrow_list[arrow_no]);
    }

    /* NOTE: this bare `{ }` block is almost certainly NOT the original
     * source shape -- the corpus norm is top-of-function decls, and this
     * is the only bare block left in battle.c.  But it is byte-LOAD-BEARING
     * and we have not found the correct flat form:
     *   - hoisting `ptr` to the function top pulls it into the
     *     function-level ConfBefore name queue, which perturbs an
     *     UNRELATED value's (`delta_anim`, in the loop above) CountRegMoves
     *     tie-break EAX->EDX and diverges (regtrace row 13 confirms).
     *   - ALL 24 decl-order permutations of {i,delta_anim,score,ptr},
     *     the embedded-assignment form, init-in-decl, ptr de-invention,
     *     and delta_anim use-order commutes were tried -- every one diffs.
     *   - even keeping the block, `int ptr = ...;` (init-in-decl) breaks
     *     it; the DEFERRED `int ptr; ptr = ...;` is required.
     * PS packs `ptr=map_ref; arrow_a=battle_map[ptr+3];` onto one -d1 line
     * (L2945), reproduced here.  If a future session finds the flat shape
     * that keeps `delta_anim` on EAX, this block should go.  See
     * docs/observed-source-style.md §0. */
    {
        int ptr;
        ptr = arrow_list[arrow_no].map_ref; arrow_a = ((unsigned char *)battle_map)[ptr + 3];
        if (arrow_a != 0) {
            arrow_list[arrow_a].flight_done = arrow_no;
        } else {
            ((unsigned char *)battle_map)[ptr + 3] = arrow_no;
        }
    }
}

// FUNCTION: C2 0x521AB
// WIN: 0x00480f19
// Lines 2950–2964
//
// One Bresenham step for the current arrow_no, used by fly_to_target.
// arrow_rec carries three 4-byte Bresenham counters (named fields):
//   +0x0E = step_x      dx remaining (axis-0 ticks)
//   +0x12 = step_y      dy remaining (axis-1 ticks)
//   +0x16 = step_error  error accumulator (signed)
//
// `axis` selects which direction to advance:
//   axis == 1 : decrement dy; the accumulator is bumped by either
//               2*dx (when err >= 0) or 2*(dx - dy_remaining) (when
//               err < 0).
//   axis != 1 : decrement dx; the accumulator is bumped by either
//               2*dy (when err < 0) or 2*(dy - dx_remaining) (when
//               err >= 0).
// The asymmetric pick keeps the major-axis counter ahead and is the
// classic mid-point line algorithm.
void bd(int axis)
{

    if (axis == 1) {
        if (arrow_list[arrow_no].step_error < 0) {
            arrow_list[arrow_no].step_error = 2 * arrow_list[arrow_no].step_y + arrow_list[arrow_no].step_error;
        } else {
            arrow_list[arrow_no].step_error = 2 * (arrow_list[arrow_no].step_y - arrow_list[arrow_no].step_x) + arrow_list[arrow_no].step_error;
        }
        arrow_list[arrow_no].step_x--;
    } else {
        if (arrow_list[arrow_no].step_error < 0) {
            arrow_list[arrow_no].step_error = 2 * arrow_list[arrow_no].step_x + arrow_list[arrow_no].step_error;
        } else {
            arrow_list[arrow_no].step_error = 2 * (arrow_list[arrow_no].step_x - arrow_list[arrow_no].step_y) + arrow_list[arrow_no].step_error;
        }
        arrow_list[arrow_no].step_y--;
    }
}

// FUNCTION: C2 0x5227D
// WIN: 0x00481041
// Lines 2966–2990
//
// Initialise the Bresenham step-bias and dominant-axis fields of
// the freshly-created arrow `arrow_no` from its endpoints.
// Writes step_x / step_y to |dx| / |dy|; step_error to the
// Bresenham initial error (2*min - max, or 0 when dx == dy);
// axis_dominant to 1 (horizontal) or 2 (vertical).  Also snaps
// the arrow's diagonal heading to the nearest cardinal when one
// axis strongly dominates the other.
void init_bd(int x1, int y1, int x2, int y2)
{
    if (x1 > x2) {
        arrow_list[arrow_no].step_x = x1 - x2;
    } else {
        arrow_list[arrow_no].step_x = x2 - x1;
    }
    if (y1 > y2) {
        arrow_list[arrow_no].step_y = y1 - y2;
    } else {
        arrow_list[arrow_no].step_y = y2 - y1;
    }

    if (arrow_list[arrow_no].step_y > arrow_list[arrow_no].step_x) {
        arrow_list[arrow_no].step_error =
            arrow_list[arrow_no].step_x * 2 - arrow_list[arrow_no].step_y;
    } else if (arrow_list[arrow_no].step_x > arrow_list[arrow_no].step_y) {
        arrow_list[arrow_no].step_error =
            arrow_list[arrow_no].step_y * 2 - arrow_list[arrow_no].step_x;
    } else {
        arrow_list[arrow_no].step_error = 0;
    }

    /* vertical dominant: dx*2 < dy */
    if ((arrow_list[arrow_no].step_x << 1) < arrow_list[arrow_no].step_y) {
        if (arrow_list[arrow_no].heading == 1)
            arrow_list[arrow_no].heading = 0;
        else if (arrow_list[arrow_no].heading == 3)
            arrow_list[arrow_no].heading = 4;
        else if (arrow_list[arrow_no].heading == 5)
            arrow_list[arrow_no].heading = 4;
        else if (arrow_list[arrow_no].heading == 7)
            arrow_list[arrow_no].heading = 0;
    }

    /* horizontal dominant: dy*2 < dx */
    if ((arrow_list[arrow_no].step_y << 1) < arrow_list[arrow_no].step_x) {
        if (arrow_list[arrow_no].heading == 1)
            arrow_list[arrow_no].heading = 2;
        else if (arrow_list[arrow_no].heading == 3)
            arrow_list[arrow_no].heading = 2;
        else if (arrow_list[arrow_no].heading == 5)
            arrow_list[arrow_no].heading = 6;
        else if (arrow_list[arrow_no].heading == 7)
            arrow_list[arrow_no].heading = 6;
    }

    if (arrow_list[arrow_no].step_y > arrow_list[arrow_no].step_x) {
        arrow_list[arrow_no].axis_dominant = 2;
    } else {
        arrow_list[arrow_no].axis_dominant = 1;
    }
}

// FUNCTION: C2 0x52410
// WIN: 0x004813d6
// Lines 2992–2999
//
// True (1) when the current arrow_list[arrow_no] is
// outside the 52×52 battle grid: any negative grid_x/y, or
// either coord ≥ 0x34.  PS reads grid_x/grid_y as signed bytes.
int arrow_off_map(void)
{
    if (arrow_list[arrow_no].grid_x < 0) return 1;
    if (arrow_list[arrow_no].grid_y < 0) return 1;
    if (arrow_list[arrow_no].grid_x >= 0x34) return 1;
    if (arrow_list[arrow_no].grid_y >= 0x34) return 1;
    return 0;
}

// FUNCTION: C2 0x52458
// WIN: 0x0048147a
// Line 3000
//
// Step the current arrow's `start_y` one pixel toward `end_y`.
void move_arrow_vert(void)
{
    if (arrow_list[arrow_no].start_y < arrow_list[arrow_no].end_y)
        arrow_list[arrow_no].start_y++;
    else if (arrow_list[arrow_no].start_y > arrow_list[arrow_no].end_y)
        arrow_list[arrow_no].start_y--;
}

// FUNCTION: C2 0x524A4
// WIN: 0x00481506
// Line 3001
//
// Step the current arrow's `start_x` one pixel toward `end_x`.
void move_arrow_horiz(void)
{
    if (arrow_list[arrow_no].start_x < arrow_list[arrow_no].end_x)
        arrow_list[arrow_no].start_x++;
    else if (arrow_list[arrow_no].start_x > arrow_list[arrow_no].end_x)
        arrow_list[arrow_no].start_x--;
}

// FUNCTION: C2 0x524F0
// WIN: 0x00481592
// Lines 3002–3012
//
// Move arrow_no one battle-map step according to its heading:
// headings 1/2/3 advance X, 5/6/7 retreat X, 3/4/5 advance Y,
// and 0/1/7 retreat Y.  Heading 0 performs only the Y decrement;
// unrecognised headings are ignored.
void loose_arrow_move(void)
{
    if (arrow_list[arrow_no].heading == 0) {
        arrow_list[arrow_no].start_y--;
    } else if (arrow_list[arrow_no].heading == 1) {
        arrow_list[arrow_no].start_x++;
        arrow_list[arrow_no].start_y--;
    } else if (arrow_list[arrow_no].heading == 2) {
        arrow_list[arrow_no].start_x++;
    } else if (arrow_list[arrow_no].heading == 3) {
        arrow_list[arrow_no].start_x++;
        arrow_list[arrow_no].start_y++;
    } else if (arrow_list[arrow_no].heading == 4) {
        arrow_list[arrow_no].start_y++;
    } else if (arrow_list[arrow_no].heading == 5) {
        arrow_list[arrow_no].start_x--;
        arrow_list[arrow_no].start_y++;
    } else if (arrow_list[arrow_no].heading == 6) {
        arrow_list[arrow_no].start_x--;
    } else if (arrow_list[arrow_no].heading == 7) {
        arrow_list[arrow_no].start_x--;
        arrow_list[arrow_no].start_y--;
    }
}

// FUNCTION: C2 0x52582
// WIN: 0x0048185b
// Lines 3016–3054
//
// Resolve one tick of melee combat between figure_no (attacker)
// and enemy_figure.  Acknowledges the mutual swing (drops our
// combat sub-state to 2 when the enemy is mid-swing back at us),
// ticks our swing-cooldown accumulator while we're still in our
// own swing, and on overflow (>= 10) drops our HP by 1 and plays
// the matching swing FX.  If HP drops to zero the figure enters
// state 2 (dying) and the tick ends.  Otherwise, while we're still
// the active swinger, applies the pending damage to the enemy's
// HP, decrements both cooldowns, and on attack_count expiry
// refills via set_attack_count and toggles us back to sub-state 2.
// Always plays the ambient combat hum at the end.
void do_the_fight(void)
{
    temp_figure = (short)figure_list[enemy_figure].opponent;

    if (temp_figure == figure_no
        && figure_list[enemy_figure].fight_role == 1)
    {
        figure_list[figure_no].fight_role = 2;
    }

    if (figure_list[figure_no].defense <= 0) {
        figure_list[figure_no].kill_counter++;
        set_defense_shield(figure_no);
    }

    if (figure_list[figure_no].kill_counter >= 0x0a) {
        figure_list[figure_no].kill_counter -= 0x0a;
        figure_list[figure_no].stampede_flag--;
        set_battle_fight_fx(figure_list[figure_no].sprite_type);
    }

    if (figure_list[figure_no].stampede_flag <= 0) {
        figure_list[figure_no].state_idx = 2;
        return;
    }

    if (figure_list[figure_no].fight_role == 1) {
        if (figure_list[figure_no].morale != 0) {
            figure_list[enemy_figure].stampede_flag -= figure_list[figure_no].morale;
            if (figure_list[enemy_figure].stampede_flag < 0)
                figure_list[enemy_figure].stampede_flag = 0;
            figure_list[figure_no].morale = 0;
        }
        figure_list[enemy_figure].defense--;
        figure_list[figure_no].attack_count--;
        if (figure_list[figure_no].attack_count <= 0) {
            if (temp_figure == figure_no) {
                figure_list[enemy_figure].fight_role = 1;
                set_attack_count(enemy_figure);
                figure_list[figure_no].fight_role = 2;
            } else {
                set_attack_count(figure_no);
            }
        }
    }

    set_this_ambient(0x13);
}

// FUNCTION: C2 0x526F9
// WIN: 0x00481b69
// Lines 3056–3071
//
// Compute and stamp figure_list[n].attack_count from the
// figure's animation kind, formation rank, and defensive
// posture (149 b, L3056–3071).
//
//   * Mirror the figure's unit_ref into the global temp_unit
//     (used by callers that subsequently visit the unit).
//   * Initialise attack_count = anim_kind.
//   * If figure_rank == 1: attack_count -= 2  (back-rank penalty)
//   * If figure_rank == 2: attack_count -= 2  (deeper back-rank penalty)
//   * If is_defending:
//        — if shield_class == 0:
//             attack_count += owner ? 6 : 4   (defender bonus,
//                                               larger for player)
//        — if shield_class == 1:
//             attack_count += 6                (heavy-shield bonus,
//                                               only stacks while defending)
//
// 4 callers: figure_states / battle pre-frame paths.
void set_attack_count(int n)
{
    temp_unit = figure_list[n].unit_ref;
    figure_list[n].attack_count = figure_list[n].anim_kind;

    if (figure_list[n].figure_rank == 1)
        figure_list[n].attack_count -= 2;
    if (figure_list[n].figure_rank == 2)
        figure_list[n].attack_count -= 2;

    if (figure_list[n].is_defending != 0) {
        if (figure_list[n].shield_class == 0) {
            if (figure_list[n].owner != 0)
                figure_list[n].attack_count += 6;
            else
                figure_list[n].attack_count += 4;
        }
        if (figure_list[n].shield_class == 1)
            figure_list[n].attack_count += 6;
    }
}

// FUNCTION: C2 0x5278E
// WIN: 0x00481d29
// Lines 3073–3081
//
// Apply per-figure defense bonuses on a battle round:
//   1. Stash unit_ref into the global temp_unit (zero-extended).
//   2. Add the figure's current sub_state to its running defense.
//   3. If the figure is in defend mode AND has shield_class == 2,
//      add an extra +2 (heavy-shield bonus).
void set_defense_shield(int n)
{
    temp_unit = figure_list[n].unit_ref;
    figure_list[n].defense += figure_list[n].sub_state;
    if (figure_list[n].is_defending != 0
     && figure_list[n].shield_class == 2) {
        figure_list[n].defense += 2;
    }
}

// FUNCTION: C2 0x527CC
// WIN: 0x00481dea
// Lines 3083–3127
//
// Scan the eight neighbour cells around the current figure
// (figure_no) on battle_map and return a direction code
// pointing at the first one that contains an enemy figure
// (different side at bf[+1], and bf[+0x1C] != 2 = dead).
// Tried in the order: N, NW, NE, W, E, SW, SE, S; each
// block is gated by the appropriate edge test on the
// current cell’s (col, row) at fl[+8]/+9.  Writes the
// neighbour’s fig number to enemy_figure on each probe.
//
// Returns:
//   0 = N,  7 = NW, 1 = NE, 6 = W,  2 = E,
//   5 = SW, 3 = SE, 4 = S,  8 = no enemy found.
//
// Each cell on battle_map is 4 bytes; the figure id sits
// at offset +1.  Row stride = 0x34 * 4 = 0xD0.  Offsets
// from fl[+0x12] (this fig’s cell pointer):
//   N  -0xCF, NW -0xD3, NE -0xCB,
//   W  -3,    E  +5,
//   SW +0xCD, SE +0xD5, S  +0xD1.
int nearest_formation_enemy(void)
{
    /* Eight sequential gated probes — each block re-derives the
       neighbour id inline.  The last three probes nest under one
       row < 0x33 gate. */
    if (figure_list[figure_no].grid_y > 0) {
        enemy_figure = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref - 0xcf];   /* N */
        if (enemy_figure != 0
         && figure_list[enemy_figure].owner != figure_list[figure_no].owner
         && figure_list[enemy_figure].state_idx != 2)
            return 0;
        if (figure_list[figure_no].grid_x > 0) {                            /* NW */
            enemy_figure = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref - 0xd3];
            if (enemy_figure != 0
             && figure_list[enemy_figure].owner != figure_list[figure_no].owner
             && figure_list[enemy_figure].state_idx != 2)
                return 7;
        }
        if (figure_list[figure_no].grid_x < 0x33) {                         /* NE */
            enemy_figure = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref - 0xcb];
            if (enemy_figure != 0
             && figure_list[enemy_figure].owner != figure_list[figure_no].owner
             && figure_list[enemy_figure].state_idx != 2)
                return 1;
        }
    }
    if (figure_list[figure_no].grid_x > 0) {                                /* W */
        enemy_figure = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref - 3];
        if (enemy_figure != 0
         && figure_list[enemy_figure].owner != figure_list[figure_no].owner
         && figure_list[enemy_figure].state_idx != 2)
            return 6;
    }
    if (figure_list[figure_no].grid_x < 0x33) {                             /* E */
        enemy_figure = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 5];
        if (enemy_figure != 0
         && figure_list[enemy_figure].owner != figure_list[figure_no].owner
         && figure_list[enemy_figure].state_idx != 2)
            return 2;
    }
    if (figure_list[figure_no].grid_y < 0x33) {
        if (figure_list[figure_no].grid_x > 0) {                            /* SW */
            enemy_figure = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 0xcd];
            if (enemy_figure != 0
             && figure_list[enemy_figure].owner != figure_list[figure_no].owner
             && figure_list[enemy_figure].state_idx != 2)
                return 5;
        }
        if (figure_list[figure_no].grid_x < 0x33) {                         /* SE */
            enemy_figure = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 0xd5];
            if (enemy_figure != 0
             && figure_list[enemy_figure].owner != figure_list[figure_no].owner
             && figure_list[enemy_figure].state_idx != 2)
                return 3;
        }
        enemy_figure = ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 0xd1];   /* S */
        if (enemy_figure != 0
         && figure_list[enemy_figure].owner != figure_list[figure_no].owner
         && figure_list[enemy_figure].state_idx != 2)
            return 4;
    }
    return 8;
}

// FUNCTION: C2 0x52A8C
// WIN: 0x00482390
// Lines 3129–3161
//
// Pick the closest still-fightable hostile figure for figure_no
// and set it up as our melee target.  Distance is the Chebyshev
// metric (get_longest_distance), capped at 0x68 = "no candidate".
// Candidate filters: must exist; opposing owner; not already
// dying / engaged; engaged-count ≤ 1 (max two attackers per
// target).  Formation-loving tribes (tribe_ai_data flag) penalise
// candidates of a different species by +10 distance so homogeneous
// units stick together; the penalty is suppressed for player-side
// figures.  On a hit, latches the target into missile_target /
// prev_grid_x|y, transitions to state 0xA (engage), and bumps the
// target's engaged-count.  Returns 1 on success, 0 otherwise.
int find_nearest_enemy(void)
{
    int dist;
    int best_no;
    int formation;
    int best_dist;

    best_dist = 0x68;
    best_no   = 0;
    formation = tribe_ai_data[bat_tribe].prefer_cohesion;

    if (figure_list[figure_no].owner != 0) formation = 0;

    for (temp_figure = 1; temp_figure < 0xc9; temp_figure++) {
        if (figure_list[temp_figure].exists == 0) continue;
        if (figure_list[temp_figure].owner == figure_list[figure_no].owner) continue;
        if (figure_list[temp_figure].state_idx == 2) continue;
        if (figure_list[temp_figure].state_idx == 0xc) continue;
        if (figure_list[temp_figure].engaged_count > 1) continue;

        dist = get_longest_distance(figure_list[figure_no].grid_x,
                                    figure_list[figure_no].grid_y,
                                    figure_list[temp_figure].grid_x,
                                    figure_list[temp_figure].grid_y);
        if (figure_list[temp_figure].sprite_type != 3 && formation == 1) dist += 10;

        if (dist < best_dist) {
            best_dist = dist;
            best_no   = temp_figure;
        }
    }

    if (best_no == 0) return 0;

    temp_figure = best_no;
    figure_list[figure_no].prev_grid_x = figure_list[temp_figure].grid_x;
    figure_list[figure_no].prev_grid_y = figure_list[temp_figure].grid_y;
    figure_list[figure_no].state_idx = 0x0a;
    figure_list[figure_no].missile_target = temp_figure;
    figure_list[temp_figure].engaged_count++;
    return 1;
}

// FUNCTION: C2 0x52BE9
// WIN: 0x00482654
// Lines 3163–3183
//
// Find the closest active enemy figure to figure_no within `max_dist`.
// Skips same-owner figures, death/rout states (2/12), and figures whose
// unit_ref matches target_unit_debar.  Publishes the chosen target in
// enemy_figure and returns 1 on success, 0 if none qualifies.
int find_nearest_target(int max_dist)
{
    int best_dist = 0x68;
    int best = 0;
    int dist;

    for (temp_figure = 1; temp_figure < 0xc9; temp_figure++) {
        if (figure_list[temp_figure].exists == 0) continue;
        if (figure_list[temp_figure].owner == figure_list[figure_no].owner) continue;
        if (figure_list[temp_figure].state_idx == 2) continue;
        if (figure_list[temp_figure].state_idx == 0xc) continue;
        if (figure_list[temp_figure].unit_ref == target_unit_debar) continue;
        dist = get_distance(figure_list[figure_no].grid_x,
                            figure_list[figure_no].grid_y,
                            figure_list[temp_figure].grid_x,
                            figure_list[temp_figure].grid_y);
        if (dist <= max_dist && dist < best_dist) {
            best_dist = dist;
            best = temp_figure;
        }
    }
    if (best == 0) return 0;
    enemy_figure = best;
    return 1;
}

// FUNCTION: C2 0x52CC0
// Lines 3187–3187
//
// Always returns 0 — PS leaves this slot empty.
int find_adjacent_target(void)
{
    return 0;
}

// FUNCTION: C2 0x52CC3
// WIN: 0x00482837
// Lines 3192–3231
//
// Scan an 11x11 box of battle_map cells around the firing unit
// for a hostile figure to shoot at.  Anchor is the unit's grid;
// the scan span is clamped to [0, 0x33].  Uses the cell offset
// as a monotonic distance proxy: the first cell whose offset
// exceeds the unit's previously-stored range wins outright;
// otherwise the first hostile cell encountered is kept as a
// fallback and committed if nothing better appears.  Returns 1
// on success with enemy_figure latched, 0 otherwise.
int get_fire_target(int fig_no)
{

    int mark_x;
    int mark_y;
    int base_x;
    int end_x;
    int base_y;
    int x;
    int end_y;
    int y;
    int cell_off;
    int fallback_off;
    int row_skip;
    int enemy_no_local;
    int prev_range;
    int en;

    enemy_no_local = 0;

    temp_unit = figure_list[fig_no].unit_ref;
    mark_x    = unit_list[temp_unit].attack_marker_x;
    mark_y    = unit_list[temp_unit].attack_marker_y;
    prev_range = unit_list[temp_unit].prev_attack_off;

    base_x = mark_x; base_y = mark_y;
    end_x = mark_x + 0xb;
    end_y = mark_y + 0xb;
    if (base_x < 0) base_x = 0;
    if (end_x  >= 0x34) end_x = 0x33;
    if (base_y < 0) base_y = 0;
    if (end_y  >= 0x34) end_y = 0x33;

    cell_off = (base_y * 0x34 + base_x) * 4;
    row_skip = (0x34 - (end_x - base_x + 1)) * 4;

    for (y = base_y; y <= end_y; y++, cell_off += row_skip) {
        x = base_x;
        for (; x <= end_x; x++, cell_off += 4) {
            enemy_figure = ((unsigned char *)battle_map)[cell_off + 1];
            if (enemy_figure != 0 && figure_list[(en = enemy_figure)].exists != 0) {
                if (figure_list[en].owner != figure_list[fig_no].owner) {
                if (cell_off > prev_range) { unit_list[temp_unit].prev_attack_off = cell_off; return 1; }
                if (enemy_no_local == 0) { enemy_no_local = en; fallback_off = cell_off; }
                }
            }
        } }

    if (enemy_no_local == 0) return 0;
    unit_list[temp_unit].prev_attack_off = fallback_off;
    enemy_figure = enemy_no_local;
    return 1;
}

struct attack_pos_rec attack_pos_data[20] = {
    { 3, 0, 0 },
    { 3, 1, 0 },
    { 4, 0, 1 },
    { 4, 1, 1 },
    { 3, 0, 0 },
    { 3, 1, 0 },
    { 4, 0, 1 },
    { 4, 1, 1 },
    { 3, 0, 2 },
    { 3, 1, 2 },
    { 4, 0, 2 },
    { 4, 1, 2 },
    { 3, 0, 0 },
    { 3, 1, 0 },
    { 4, 0, 1 },
    { 4, 1, 1 },
    { 3, 0, 2 },
    { 3, 1, 2 },
    { 4, 0, 0 },
    { 4, 1, 0 }
};

int steves_security_false2[7] = { 538976288, 2021138464, 2021161080, 538998904, 2021138464, 538998904, 538976288 };

struct byte_delta_rec elephant_stampede[8] = {
    { 53, 53 },
    { 26, 53 },
    { -1, 53 },
    { 53, 53 },
    { 26, 53 },
    { -1, 53 },
    { 26, 53 },
    { 26, 53 }
};

char sling_images[33] = { 10, 10, 10, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 10, 10, 10, 10, 11, 11, 12, 12, 11, 12, 11, 12 };

char bow_images[33] = { 10, 10, 10, 10, 10, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 11, 11, 11, 11, 12, 12, 12, 12, 12 };

char horsebow_images[33] = { 6, 6, 6, 6, 6, 6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 7, 7, 7, 7, 8, 8, 8, 8, 8 };

char elephant_archer_images[21] = "111111111122223333000";

void (*figure_intelligences[18])(void) = {
    f00_null,
    f01_regular,
    f02_irregular,
    f03_auxillary,
    f00_null,
    f05_barb_sword,
    f06_barb_spear,
    f07_barb_axe,
    f08_barb_pike,
    f03_auxillary,
    f03_auxillary,
    f11_barb_horse_heavy,
    f12_barb_horse_light,
    f12_barb_horse_light,
    f12_barb_horse_light,
    f15_barb_elephant,
    f16_barb_bow,
    f03_auxillary
};

void (*figure_states[17])(void) = {
    sf00_null,
    sf01_wait,
    sf02_death,
    sf03_move,
    sf04_fight,
    sf05_mop_up,
    sf06_defend,
    sf07_reform,
    sf08_withdraw,
    sf09_look_for_fight,
    sf10_hunt_for_fight,
    sf11_fire_missile,
    sf12_rout,
    sf13_autofire_missile,
    sf14_opertunist_fire,
    sf15_move_and_reform,
    sf16_beserk
};

struct int_delta_rec line_flank_data[20] = {
    { 0, 0 },
    { 0, 1 },
    { 1, 0 },
    { 1, 1 },
    { 2, 0 },
    { 2, 1 },
    { 3, 0 },
    { 3, 1 },
    { 4, 0 },
    { 4, 1 },
    { 5, 0 },
    { 5, 1 },
    { 6, 0 },
    { 6, 1 },
    { 7, 0 },
    { 7, 1 },
    { 8, 0 },
    { 8, 1 },
    { 9, 0 },
    { 9, 1 }
};

struct int_delta_rec col_flank_data[20] = {
    { 0, 0 },
    { 1, 0 },
    { 0, 1 },
    { 1, 1 },
    { 0, 2 },
    { 1, 2 },
    { 0, 3 },
    { 1, 3 },
    { 0, 4 },
    { 1, 4 },
    { 0, 5 },
    { 1, 5 },
    { 0, 6 },
    { 1, 6 },
    { 0, 7 },
    { 1, 7 },
    { 0, 8 },
    { 1, 8 },
    { 0, 9 },
    { 1, 9 }
};

signed char wf_battle_dircs[8] = { 1, -1, 2, -2, 3, -3, 4, 4 };
