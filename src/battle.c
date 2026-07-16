
#include "battle.h"
#include "c2_data.h"

/* File-local state. */
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

extern int get_heading();

void elephant_fire(void);
// Enter or resume a battle, preparing its map, graphics, units, audio, and main battle screen.
// FUNCTION: C2 0x4afd7
// FUNCTION: C2WIN 0x00472bc0
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

// Select or toggle every figure belonging to the same unit as `fig_idx`.
// FUNCTION: C2 0x4b267
// FUNCTION: C2WIN 0x00472f8c
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

// Clear the .selected flag on every figure in figure_list[1..200].
// FUNCTION: C2 0x4b2ee
// FUNCTION: C2WIN 0x004730ae
void deselect_all_figures(void)
{
    for (figure_no = 1; figure_no < 201; figure_no++) {
        figure_list[figure_no].selected = 0;
    }
}

// Clear selection from every enemy figure.
// FUNCTION: C2 0x4b31c
// FUNCTION: C2WIN 0x004730fc
void deselect_enemy_figures(void)
{
    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].owner == 0) {
            figure_list[figure_no].selected = 0;
        }
    }
}

// Select every active player-controlled figure.
// FUNCTION: C2 0x4b352
// FUNCTION: C2WIN 0x00473169
void select_all_figures(void)
{
    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists != 0
         && figure_list[figure_no].owner != 0) {
            figure_list[figure_no].selected = 1;
        }
    }
}

// Select units inside the current battle-map drag rectangle.
// FUNCTION: C2 0x4b38f
// FUNCTION: C2WIN 0x004731f5
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

// Validate and draw the destination preview for selected moving units.
// FUNCTION: C2 0x4b438
// FUNCTION: C2WIN 0x00473345
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


// Highlight the target area for selected missile units.
// FUNCTION: C2 0x4b69f
// FUNCTION: C2WIN 0x0047388d
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

// Commit the highlighted destination for the selected units.
// FUNCTION: C2 0x4b7b2
// FUNCTION: C2WIN 0x00473acd
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
        /* Check whether any selected unit is already engaged. */
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

        /* Clear the selected figures' current map cells during setup. */
        for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
            if (figure_list[figure_no].exists != 0
                && figure_list[figure_no].selected != 0
                && battle_state == 0) {
                ((unsigned char *)battle_map)[figure_list[figure_no].map_ref + 1] = 0;
            }
        }

        /* Apply the new destination and movement state. */
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

// Activate "aim" mode for every selected figure.
// FUNCTION: C2 0x4ba40
// FUNCTION: C2WIN 0x0047410c
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

// Compute the selected figures' bounding box and its offset from the cursor.
// FUNCTION: C2 0x4bb23
// FUNCTION: C2WIN 0x00474311
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

// Clear all highlight flags from the battle map.
// FUNCTION: C2 0x4bcbf
// FUNCTION: C2WIN 0x00474593
void clear_all_highlights_from_battlemap(void)
{
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

// Build an open-battle map with random terrain, standard dimensions, and a fresh pseudo-map.
// FUNCTION: C2 0x4bd13
// FUNCTION: C2WIN 0x00474618
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

// Initialise battle state for the combatants named in our_battle_army / their_battle_army.
// FUNCTION: C2 0x4bde3
// FUNCTION: C2WIN 0x00474716
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

    /* Re-read the troop totals after the odds calculation. */
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

// Snapshot troop counts from the two participating armies into the battle globals used by the
// setup UI and battle resolution code.
// FUNCTION: C2 0x4bf69
// FUNCTION: C2WIN 0x0047491f
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

// Create and deploy the Roman units for the battle.
// FUNCTION: C2 0x4c016
// FUNCTION: C2WIN 0x00474a86
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

// Build the enemy army from its tribe's formation, unit-kind, and sprite-set configuration.
// FUNCTION: C2 0x4c399
// FUNCTION: C2WIN 0x00474f9f
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

// Re-tally per-rank HP totals into each side's army_list record.
// FUNCTION: C2 0x4c9c0
// FUNCTION: C2WIN 0x00475835
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

// Compute the battle-odds rating into bat_odds (+5 = we vastly outnumber them, 0 = roughly equal,
// -5 = they vastly outnumber us) from their_battle_men and our_battle_men, then — unless
// tune_mood_hold is set — fold that into tune_mood (1..5).
// FUNCTION: C2 0x4cbd9
// FUNCTION: C2WIN 0x00475e2d
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

// Create a battle unit and place its figures in the current deployment slot.
// FUNCTION: C2 0x4cd76
// FUNCTION: C2WIN 0x0047605c
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

    /* Assign eligible enemy units to flank or fan manoeuvres. */
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

    /* Create and configure the unit's figures. */
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

// Rebind every live figure and projectile to the sprite tables loaded for the current map and zoom.
// FUNCTION: C2 0x4d272
// FUNCTION: C2WIN 0x004769af
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

// Initialize the deployment lanes for an attacking army.
// FUNCTION: C2 0x4d404
// FUNCTION: C2WIN 0x00476d34
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

// Initialize the deployment lanes for a defending army.
// FUNCTION: C2 0x4d491
// FUNCTION: C2WIN 0x00476de7
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

// Pick the next (x, y) deployment slot for a unit being placed on the battle map.
// FUNCTION: C2 0x4d51e
// FUNCTION: C2WIN 0x00476e9a
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

// Return a figure's horizontal offset within a formation.
// FUNCTION: C2 0x4d7d3
// FUNCTION: C2WIN 0x004771f6
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

// Return a figure's vertical offset within a formation.
// FUNCTION: C2 0x4d821
// FUNCTION: C2WIN 0x0047726b
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

// Count active figures and mark their map footprints for redraw.
// FUNCTION: C2 0x4d861
// FUNCTION: C2WIN 0x004772f2
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

// Clear projectile occupancy and mark active projectiles' map areas for redraw.
// FUNCTION: C2 0x4da05
// FUNCTION: C2WIN 0x0047763d
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

// Updates every active battle figure for the current simulation tick.
// FUNCTION: C2 0x4dae8
// FUNCTION: C2WIN 0x004777c2
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

// Refresh the still-frame sprite for every active figure.
// FUNCTION: C2 0x4db5e
// FUNCTION: C2WIN 0x004778bf
void figure_images(void)
{
    for (figure_no = 1; figure_no < 0xc9; ++figure_no) {
        if (figure_list[figure_no].exists != 0) {
            get_fig_still_image();
        }
    }
}

// Provide the unused figure-type handler.
// FUNCTION: C2 0x4db8f
// FUNCTION: C2WIN 0x0047791a
void f00_null(void)
{
}

// Initialize a regular soldier's animation and run its current state handler.
// FUNCTION: C2 0x4db90
// FUNCTION: C2WIN 0x00477925
void f01_regular(void)
{
    figure_list[figure_no].anim_kind = 0xf;
    figure_list[figure_no].sub_state = 3;
    figure_states[figure_list[figure_no].state_idx]();
}

// Irregular-troop figure-state init (anim_kind = 0xa, sub_state = 2).
// FUNCTION: C2 0x4dbaa
// FUNCTION: C2WIN 0x0047797c
void f02_irregular(void)
{
    figure_list[figure_no].anim_kind = 0xa;
    figure_list[figure_no].sub_state = 2;
    figure_states[figure_list[figure_no].state_idx]();
}

// Initialize an auxiliary soldier's animation and run its current state handler.
// FUNCTION: C2 0x4dbc4 FOLDED
void f03_auxillary(void)
{
    figure_list[figure_no].anim_kind = 4;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// Empty state-handler slot in `figure_states[]` (state_idx 0).
// FUNCTION: C2 0x4dbea
void sf00_null(void)
{
}

// Initializes a barbarian swordsman's animation state and dispatches its current state handler.
// FUNCTION: C2 0x4dbeb
// FUNCTION: C2WIN 0x00477a2a
void f05_barb_sword(void)
{
    figure_list[figure_no].anim_kind = 0xe;
    figure_list[figure_no].sub_state = 3;
    figure_states[figure_list[figure_no].state_idx]();
}

// Barbarian-spear figure-state init (anim_kind = 0xc, sub_state = 2).
// FUNCTION: C2 0x4dbfe
// FUNCTION: C2WIN 0x00477a81
void f06_barb_spear(void)
{
    figure_list[figure_no].anim_kind = 0xc;
    figure_list[figure_no].sub_state = 2;
    figure_states[figure_list[figure_no].state_idx]();
}

// Barbarian-axe figure-state init (anim_kind = 0x10, sub_state = 1).
// FUNCTION: C2 0x4dc11
// FUNCTION: C2WIN 0x00477ad8
void f07_barb_axe(void)
{
    figure_list[figure_no].anim_kind = 0x10;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// Barbarian-pike figure-state init (anim_kind = 0xa, sub_state = 5).
// FUNCTION: C2 0x4dc24
// FUNCTION: C2WIN 0x00477b2f
void f08_barb_pike(void)
{
    figure_list[figure_no].anim_kind = 0xa;
    figure_list[figure_no].sub_state = 5;
    figure_states[figure_list[figure_no].state_idx]();
}

// Initialize a barbarian javelin soldier and run its current state handler.
// FUNCTION: C2 0x4dbc4 FOLDED
void f09_barb_javalin(void)
{
    figure_list[figure_no].anim_kind = 4;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// Initialize a barbarian slinger and run its current state handler.
// FUNCTION: C2 0x4dbc4 FOLDED
void f10_barb_sling(void)
{
    figure_list[figure_no].anim_kind = 4;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// Heavy barbarian-cavalry figure-state init (anim_kind = 0x10, sub_state = 5).
// FUNCTION: C2 0x4dc3e
// FUNCTION: C2WIN 0x00477c34
void f11_barb_horse_heavy(void)
{
    figure_list[figure_no].anim_kind = 0x10;
    figure_list[figure_no].sub_state = 5;
    figure_states[figure_list[figure_no].state_idx]();
}

// Initialize light barbarian cavalry and run its current state handler.
// FUNCTION: C2 0x4dc51 FOLDED
// FUNCTION: C2WIN 0x00477c8b
void f12_barb_horse_light(void)
{
    figure_list[figure_no].anim_kind = 0xe;
    figure_list[figure_no].sub_state = 4;
    figure_states[figure_list[figure_no].state_idx]();
}

// Initialize a mounted archer and run its current state handler.
// FUNCTION: C2 0x4dc51 FOLDED
// FUNCTION: C2WIN 0x00477ce2
void f13_barb_horse_archer(void)
{
    figure_list[figure_no].anim_kind = 0xe;
    figure_list[figure_no].sub_state = 4;
    figure_states[figure_list[figure_no].state_idx]();
}

// Initialize a camel rider and run its current state handler.
// FUNCTION: C2 0x4dc51 FOLDED
// FUNCTION: C2WIN 0x00477d39
void f14_barb_camel(void)
{
    figure_list[figure_no].anim_kind = 0xe;
    figure_list[figure_no].sub_state = 4;
    figure_states[figure_list[figure_no].state_idx]();
}


// Initializes a barbarian elephant's animation state and dispatches its current state handler.
// FUNCTION: C2 0x4dc6e
// FUNCTION: C2WIN 0x00477d90
void f15_barb_elephant(void)
{
    figure_list[figure_no].anim_kind = 0x14;
    figure_list[figure_no].sub_state = 6;
    figure_states[figure_list[figure_no].state_idx]();
    elephant_fire();
}

// Initializes a barbarian archer's animation state and dispatches its current state handler.
// FUNCTION: C2 0x4dcca
// FUNCTION: C2WIN 0x00477dec
void f16_barb_bow(void)
{
    figure_list[figure_no].anim_kind = 5;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// Initialize a barbarian knife fighter and run its current state handler.
// FUNCTION: C2 0x4dbc4 FOLDED
void f17_barb_knife(void)
{
    figure_list[figure_no].anim_kind = 4;
    figure_list[figure_no].sub_state = 1;
    figure_states[figure_list[figure_no].state_idx]();
}

// Hold a waiting figure still, then advance it to its queued state.
// FUNCTION: C2 0x4dce0
// FUNCTION: C2WIN 0x00477ea5
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

// Animate and remove a dead figure, or send a dying elephant into a stampede.
// FUNCTION: C2 0x4dd4a
// FUNCTION: C2WIN 0x00477fe7
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

// Move state (state_idx 3): step the figure toward its current target; on arrival drop the routing
// flag and return to defend state 6.
// FUNCTION: C2 0x4de81
// FUNCTION: C2WIN 0x00478269
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

// Move-and-reform state (state_idx 15): step the figure toward its current target; once it
// arrives, call reform() on its parent unit with the saved formation.
// FUNCTION: C2 0x4decb
// FUNCTION: C2WIN 0x00478307
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

// Fight state (state_idx 4): if the opponent is still alive and also fighting us, resolve one tick
// of melee; otherwise fall back to look-for-fight (state 9).
// FUNCTION: C2 0x4df2d
// FUNCTION: C2WIN 0x004783ca
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

// Empty state-handler slot for the "mop-up" battle state.
// FUNCTION: C2 0x4dfb7
void sf05_mop_up(void)
{
}

// Defend state (state == 6). Hold position; harass any enemy in firing range.
// FUNCTION: C2 0x4dfb8
// FUNCTION: C2WIN 0x004784c6
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

// Reform state (state_idx 7): walk the figure toward its formation slot; on arrival switch to
// defend state 6 with .is_defending set, snapping its facing to anim_state.
// FUNCTION: C2 0x4e1bf
// FUNCTION: C2WIN 0x00478820
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

// Withdraw state (state_idx 8): step the figure backward to its target tile; on arrival drop into
// defend state 6 and reset morale (halved for rank-1, zeroed for rank-2) based on the tribe's base
// morale.
// FUNCTION: C2 0x4e21c
// FUNCTION: C2WIN 0x00478901
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

// Look-for-fight state (state_idx 9): if defending, scan the eight neighbour cells via
// `nearest_formation_enemy` and engage the first hostile found; otherwise drop into the
// hunt-for-fight state (0xa).
// FUNCTION: C2 0x4e31d
// FUNCTION: C2WIN 0x00478afc
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

// Empty state-handler slot for the "berserk" battle state.
// FUNCTION: C2 0x4e3df
void sf16_beserk(void)
{
}

// Hunt-for-fight state (state_idx 10): pick a fresh missile_target (the previous one if still
// alive, otherwise the nearest enemy), then walk toward it via figure_go_to_target.
// FUNCTION: C2 0x4e3e0
// FUNCTION: C2WIN 0x00478c7b
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

// Fire-missile state (state == 11). While the figure hasn't reached its firing stand yet
// (is_visible bit 1 clear), keep walking via figure_go_to_target.
// FUNCTION: C2 0x4e4cc
// FUNCTION: C2WIN 0x00479337
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

// Routing state handler: mark the figure as routing, update its walk image, advance toward the
// (panic) target, and despawn it once it reaches the map edge.
// FUNCTION: C2 0x4e6b4
// FUNCTION: C2WIN 0x004792ec REORDERED
void sf12_rout(void)
{
    figure_list[figure_no].is_routing = 1;
    get_fig_walk_image();
    figure_go_to_target();
    if (fig_at_edge != 0) {
        remove_figure(figure_no);
    }
}

// Hold position and automatically fire at nearby enemies.
// FUNCTION: C2 0x4e6e4
// FUNCTION: C2WIN 0x004795f0
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

// Move into firing position and periodically attack nearby enemies.
// FUNCTION: C2 0x4e895
// FUNCTION: C2WIN 0x0047995d
void sf14_opertunist_fire(void)
{
    if ((figure_list[figure_no].is_visible & 1) == 0) {
        get_fig_walk_image();
        figure_go_to_target();
        return;
    }

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

// Updates an elephant archer's two firing slots and selects nearby targets.
// FUNCTION: C2 0x4dc94 REORDERED
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

        figure_list[figure_no].archer_image_a = elephant_archer_images[figure_list[figure_no].archer_tick_a];
        if      (map_direction == 0) figure_list[figure_no].archer_image_a += ((figure_list[figure_no].archer_heading_a % 8) * 4);
        else if (map_direction == 2) figure_list[figure_no].archer_image_a += (((figure_list[figure_no].archer_heading_a + 6) % 8) * 4);
        else if (map_direction == 4) figure_list[figure_no].archer_image_a += (((figure_list[figure_no].archer_heading_a + 4) % 8) * 4);
        else if (map_direction == 6) figure_list[figure_no].archer_image_a += (((figure_list[figure_no].archer_heading_a + 2) % 8) * 4);

        /* Animate the elephant's second archer once its firing cycle begins. */
        if (figure_list[figure_no].archer_tick_b < 0xa) figure_list[figure_no].archer_image_b = elephant_archer_images[0];
        else figure_list[figure_no].archer_image_b = elephant_archer_images[figure_list[figure_no].archer_tick_b - 10];

        if      (map_direction == 0) figure_list[figure_no].archer_image_b += ((figure_list[figure_no].archer_heading_b % 8) * 4);
        else if (map_direction == 2) figure_list[figure_no].archer_image_b += (((figure_list[figure_no].archer_heading_b + 6) % 8) * 4);
        else if (map_direction == 4) figure_list[figure_no].archer_image_b += (((figure_list[figure_no].archer_heading_b + 4) % 8) * 4);
        else if (map_direction == 6) figure_list[figure_no].archer_image_b += (((figure_list[figure_no].archer_heading_b + 2) % 8) * 4);
    }
}

// Set a newly created projectile's sprite from the firing figure's type.
// FUNCTION: C2 0x4f096
// FUNCTION: C2WIN 0x0047a4ba
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

// Advance and animate every active projectile.
// FUNCTION: C2 0x4f174
// FUNCTION: C2WIN 0x0047a67f
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

// Deselect the player's selected unit or reform a selected enemy unit for the current map mode.
// FUNCTION: C2 0x4f27d
// FUNCTION: C2WIN 0x0047a7db
void general_reform(int p1)
{
    /* Process each selected unit once. */
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

// Assign a formation and destination slots to every figure in a unit.
// FUNCTION: C2 0x4f33d
// FUNCTION: C2WIN 0x0047a94b
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


// Immediately place a unit's figures into the requested formation.
// FUNCTION: C2 0x4f44d
// FUNCTION: C2WIN 0x0047ab55
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


// Test whether a unit can reform at (x_bit, y_bit) heading direction `dir`.
// FUNCTION: C2 0x4f5e0
// FUNCTION: C2WIN 0x0047aeb4
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


// Compute (x_bit, y_bit) globals for figure `fig_idx` under formation `mode`.
// FUNCTION: C2 0x4f6c1
// FUNCTION: C2WIN 0x0047b036
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

// Pick the sprite-frame for figure_no while it is in a fight state. fight_state == 2 (stopped)
// delegates to get_fig_still_image and returns.
// FUNCTION: C2 0x4f74e
// FUNCTION: C2WIN 0x0047b16d
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


// Select and advance the current figure's walking animation frame.
// FUNCTION: C2 0x4f902
// FUNCTION: C2WIN 0x0047b600
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

// Select the current figure's still frame, including tortoise-formation poses.
// FUNCTION: C2 0x4fa48
// FUNCTION: C2WIN 0x0047b8e5
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
    if (map_direction == 0)      anim = (figure_list[figure_no].direction % 8) * base;
    else if (map_direction == 2) anim = ((figure_list[figure_no].direction + 6) % 8) * base;
    else if (map_direction == 4) anim = ((figure_list[figure_no].direction + 4) % 8) * base;
    else if (map_direction == 6) anim = ((figure_list[figure_no].direction + 2) % 8) * base;
    figure_list[figure_no].sprite_anim = anim;
}

// Pick the facing for a tortoise figure (the locked-shield Roman formation): prefer to face the
// same-army figure that's one step E (4), N (2), S (6), or W (0); fall back to E (4) when no
// neighbour matches.
// FUNCTION: C2 0x4fb34
// FUNCTION: C2WIN 0x0047bac7
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

    if (map_direction == 0)      img = (figure_list[figure_no].direction % 8) * 20;
    else if (map_direction == 2) img = ((figure_list[figure_no].direction + 6) % 8) * 20;
    else if (map_direction == 4) img = ((figure_list[figure_no].direction + 4) % 8) * 20;
    else if (map_direction == 6) img = ((figure_list[figure_no].direction + 2) % 8) * 20;
    img = img + 0x10;
    figure_list[figure_no].sprite_anim = img;
}

// Direction-checked neighbour test on the battle map. Returns 1 if the neighbour cell in `dirc`
// (0/2/4/6) holds a figure that shares figure_no's unit_ref, 0 otherwise.
// FUNCTION: C2 0x4fc4e
// FUNCTION: C2WIN 0x0047bcbd
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

// Pick the sprite frame for a dying figure (figure_no).
// FUNCTION: C2 0x4fd25
// FUNCTION: C2WIN 0x0047be76
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

// Missile-attack frame picker for figure_no. Non-zero fight_state uses the short 9-frame stride
// and sprite_dir=1; idle uses the normal 20-frame stride.
// FUNCTION: C2 0x4fd87
// FUNCTION: C2WIN 0x0047bf53
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

// Mark a clipped rectangle of battle-map cells dirty for redraw.
// FUNCTION: C2 0x4fea9
// FUNCTION: C2WIN 0x0047c1a2
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

// Set the new projectile's firing range and speed from missile-weapon kind `n`.
// FUNCTION: C2 0x4ff22
// FUNCTION: C2WIN 0x0047c2b4
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

// Update the AI-controlled enemy units for the current battle tick.
// FUNCTION: C2 0x4ffd0
// FUNCTION: C2WIN 0x0047c3b9
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

// Per-tick AI driver for elephant units.
// FUNCTION: C2 0x5004e
// FUNCTION: C2WIN 0x0047c4cb
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

// Choose movement or firing orders for the current light enemy unit.
// FUNCTION: C2 0x5009b
// FUNCTION: C2WIN 0x0047c57e
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

// Choose manoeuvre, attack, or withdrawal orders for the current heavy enemy unit.
// FUNCTION: C2 0x500fc
// FUNCTION: C2WIN 0x0047c653
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

    /* Wait until the unit's next AI decision tick. */
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

// Position every figure of temp_unit in a flank-line or flank-column formation. `mode` selects the
// anchor column: 1 = left flank (roman_left_edge - 6), 2 = right flank (roman_right_edge + 8), 3 =
// centre (fixed at 0x2c); the column is clamped to [0, 0x33].
// FUNCTION: C2 0x502f3
// FUNCTION: C2WIN 0x0047ca6a
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


// Order temp_unit to move by (dx,dy). The unit combat order is set to 3 and its AI flag armed.
// FUNCTION: C2 0x504df
// FUNCTION: C2WIN 0x0047ce22
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

// Order the current temp_unit to withdraw by delta (dx,dy). The unit combat order is set to 8 and
// its withdraw flag is armed.
// FUNCTION: C2 0x505aa
// FUNCTION: C2WIN 0x0047d04d
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

// Order every eligible figure in the current unit to attack berserk.
// FUNCTION: C2 0x50646
// FUNCTION: C2WIN 0x0047d1b6
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

// Queue a staggered berserk attack for every eligible figure in the current unit.
// FUNCTION: C2 0x506c5
// FUNCTION: C2WIN 0x0047d2f0
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

// Put every active figure in temp_unit into auto-fire state unless it is already in one of the
// excluded combat states. Also clears the per-figure defense flag and snapshots current grid
// position into prev_grid_x/prev_grid_y for the auto-fire animation.
// FUNCTION: C2 0x50760
// FUNCTION: C2WIN 0x0047d464
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

// Update unit morale, fatigue, recovery, and routing decisions.
// FUNCTION: C2 0x50806
// FUNCTION: C2WIN 0x0047d64e
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

// Lower morale for active units of the specified type.
// FUNCTION: C2 0x509c4
// FUNCTION: C2WIN 0x0047da3d
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

// Raise both morale values for every active unit whose type differs from `skip_type`.
// FUNCTION: C2 0x50a44
// FUNCTION: C2WIN 0x0047dbad
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

// Force unit `unit_no` to rout: zero its primary morale axis, set combat_order=0x0c, and walk all
// member figures.
// FUNCTION: C2 0x50ab5
// FUNCTION: C2WIN 0x0047dcd4
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

// Recompute unit membership, army totals, morale, selection statistics, and Roman map bounds.
// FUNCTION: C2 0x50b57
// FUNCTION: C2WIN 0x0047de58
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

// Convert unit type/owner into the battle music mood bucket and hold it. Units with non-zero .type
// use moods 6..9 by .owner; zero-type barbarian / animal / siege unit classes map to the later
// mood range.
// FUNCTION: C2 0x50f6d
// FUNCTION: C2WIN 0x0047e676
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

// Prepare every eligible figure in a unit to seek or enter combat.
// FUNCTION: C2 0x5105b
// FUNCTION: C2WIN 0x0047e8ea
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

// Advance the current figure toward its destination and handle obstacles or combat.
// FUNCTION: C2 0x51189
// FUNCTION: C2WIN 0x0047eb78
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

    /* Choose a heading toward the destination. */
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

    /* Test the next step and resolve any obstruction. */
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
        /* Engage the blocking enemy. */
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

    /* Commit the movement step. */
    figure_list[figure_no].is_visible &= 0xfe;
    figure_list[figure_no].backtrack_dirc = figure_list[figure_no].direction;
    figure_list[figure_no].direction = w_dirc;
    figure_list[figure_no].wf_step_x = 1;
    move_figure(figure_no);
    figure_list[figure_no].backtrack_flag = 1;
    return 1;
}

// Swap positions when two compatible figures from the same unit block each other.
// FUNCTION: C2 0x515e0
// FUNCTION: C2WIN 0x0047f57d
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

// Test the battle-map destination one tile from `figure_no`, recording when the move reaches an edge.
// FUNCTION: C2 0x516cb
// FUNCTION: C2WIN 0x0047f786
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

// Test whether a battle-map cell is free, friendly, or occupied by an enemy.
// FUNCTION: C2 0x5185c
// FUNCTION: C2WIN 0x0047fb65
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

// Move a figure forward one cell, removing it if the destination is already occupied.
// FUNCTION: C2 0x51927
// FUNCTION: C2WIN 0x0047fccd
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

// Step a figure backward one cell along its current direction (used when a forward move was
// illegal).
// FUNCTION: C2 0x51a5f
// FUNCTION: C2WIN 0x0047ffbe
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

// Set the current figure's destination to the adjacent cell in an eight-way direction.
// FUNCTION: C2 0x51b58
// FUNCTION: C2WIN 0x00480277
void target_from_figure_dirc(int dir)
{
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

// Choose a passable direction toward the current figure's destination.
// FUNCTION: C2 0x51c64
// FUNCTION: C2WIN 0x004805cd
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


// Advance the current projectile and resolve expiry or impact.
// FUNCTION: C2 0x51e5a
// FUNCTION: C2WIN 0x004809d7
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

// Update the current projectile's Bresenham error term.
// FUNCTION: C2 0x521ab
// FUNCTION: C2WIN 0x00480f19
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

// Initialize a new projectile's Bresenham deltas, error term, and dominant axis.
// FUNCTION: C2 0x5227d
// FUNCTION: C2WIN 0x00481041
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

// Return 1 when the current projectile lies outside the 52×52 battle grid.
// FUNCTION: C2 0x52410
// FUNCTION: C2WIN 0x004813d6
int arrow_off_map(void)
{
    if (arrow_list[arrow_no].grid_x < 0) return 1;
    if (arrow_list[arrow_no].grid_y < 0) return 1;
    if (arrow_list[arrow_no].grid_x >= 0x34) return 1;
    if (arrow_list[arrow_no].grid_y >= 0x34) return 1;
    return 0;
}

// Step the current projectile's `start_y` one pixel toward `end_y`.
// FUNCTION: C2 0x52458
// FUNCTION: C2WIN 0x0048147a
void move_arrow_vert(void)
{
    if (arrow_list[arrow_no].start_y < arrow_list[arrow_no].end_y)
        arrow_list[arrow_no].start_y++;
    else if (arrow_list[arrow_no].start_y > arrow_list[arrow_no].end_y)
        arrow_list[arrow_no].start_y--;
}

// Step the current projectile's `start_x` one pixel toward `end_x`.
// FUNCTION: C2 0x524a4
// FUNCTION: C2WIN 0x00481506
void move_arrow_horiz(void)
{
    if (arrow_list[arrow_no].start_x < arrow_list[arrow_no].end_x)
        arrow_list[arrow_no].start_x++;
    else if (arrow_list[arrow_no].start_x > arrow_list[arrow_no].end_x)
        arrow_list[arrow_no].start_x--;
}

// Move the current projectile one grid step along its heading.
// FUNCTION: C2 0x524f0
// FUNCTION: C2WIN 0x00481592
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

// Resolve one tick of melee combat between figure_no (attacker) and enemy_figure.
// FUNCTION: C2 0x52582
// FUNCTION: C2WIN 0x0048185b
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

// Derive a figure's attack count from its animation, rank, and defensive posture.
// FUNCTION: C2 0x526f9
// FUNCTION: C2WIN 0x00481b69
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

// Refresh a figure's defense value from its type and formation.
// FUNCTION: C2 0x5278e
// FUNCTION: C2WIN 0x00481d29
void set_defense_shield(int n)
{
    temp_unit = figure_list[n].unit_ref;
    figure_list[n].defense += figure_list[n].sub_state;
    if (figure_list[n].is_defending != 0
     && figure_list[n].shield_class == 2) {
        figure_list[n].defense += 2;
    }
}

// Return the direction of the first living enemy adjacent to the current figure.
// FUNCTION: C2 0x527cc
// FUNCTION: C2WIN 0x00481dea
int nearest_formation_enemy(void)
{
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

// Pick the closest still-fightable hostile figure for figure_no and set it up as our melee target.
// Distance is the Chebyshev metric (get_longest_distance), capped at 0x68 = "no candidate".
// FUNCTION: C2 0x52a8c
// FUNCTION: C2WIN 0x00482390
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

// Find the closest active enemy figure to figure_no within `max_dist`. Skips same-owner figures,
// death/rout states (2/12), and figures whose unit_ref matches target_unit_debar.
// FUNCTION: C2 0x52be9
// FUNCTION: C2WIN 0x00482654
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

// Empty adjacent-target hook; always returns 0.
// FUNCTION: C2 0x52cc0
int find_adjacent_target(void)
{
    return 0;
}

// Scan an 11x11 box of battle_map cells around the firing unit for a hostile figure to shoot at.
// Anchor is the unit's grid; the scan span is clamped to [0, 0x33].
// FUNCTION: C2 0x52cc3
// FUNCTION: C2WIN 0x00482837
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
