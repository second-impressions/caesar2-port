// D:\C2\CODE\gloops.c

#include "c2_data.h"
#include "c2_types.h"

int mouse_styles[10] = { 0, 1, 2, 3, 9, 0, 2, 3, 4, 4 };

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
extern int colour_cycle_delay1();  /* really char -- lib32.c */
extern int colour_cycle_delay2();  /* really char -- lib32.c */


extern void put_a_font_string(char *str, int x, int y, unsigned char *font, int color);
extern void font_list(int idx, int word_count, int x, int y, unsigned char *font, int color);
extern int  get_fb_width(unsigned char *font);
extern void show_cursor(unsigned char *font);

extern void exit_screen_void(void);  /* unused; placeholder if needed */


// FUNCTION: C2 0x3D399
// WIN: 0x0040f7f0
// Lines 57–62
void gloop_start(void)
{
    cycle_count++;
    cover_mouse_droppings();
    get_mouse();
    random();
}

// FUNCTION: C2 0x3D9DF
// Lines 302–302
//
// Common end-of-game-loop tail: refresh mouse cursor, refresh SVGA
// screen, advance audio db, latch the running-delay tick into
// button_time_flag.
//
// ⚠ ORDERING IS LOad-BEARING — keep gloop_end (and its ICF twin
// mloop_end) DEFINED BEFORE floop_end, even though PS PLACES gloop_end
// at 0x3D9DF, *after* floop_end (0x3D3AE).  This is the Mac-binary
// source order, and it is what makes the whole file byte-exact:
//
//   * Watcom DECOUPLES placement from ComTail processing.  Placement
//     is fall-through-driven — just_idle_game_loop tail-calls gloop_end,
//     so gloop_end is PINNED right after just_idle (late address)
//     regardless of where it is defined.
//   * The ComTail tail-merge DONOR is chosen by SOURCE/emission order:
//     whichever of {gloop_end, floop_end} is compiled first owns the
//     shared `show_mouse(...); set_mouse_refresh; ...; ret` tail; the
//     other folds into it.
//
// With gloop_end first, gloop_end is the donor and floop_end folds
// FORWARD into it (floop_end early + gloop_end pinned late) -> floop_end
// is the 28-byte forward jumper, byte-for-byte PS.  Put floop_end first
// (the order PS's own -d1 L85<L302 implies) and OUR 10.0a makes floop_end
// the donor instead -> gloop_end folds backward, floop_end diffs 7-8b.
// func-order is satisfied because the ICF class (gloop_end+mloop_end at
// one address) is exempt from the address-monotone check.  DO NOT
// "fix" this back to PS address order.
void gloop_end(void)
{
    get_mouse_droppings();
    show_mouse(pointer_mode);
    set_mouse_refresh();
    refresh_svga_screen();
    continue_db();
    button_time_flag = running_delay1();
}

// FUNCTION: C2 0x3D9DF
//
// Dead (uncalled) byte-identical twin of gloop_end, ICF-folded onto
// gloop_end's address (0x3D9DF in PS).  Mac keeps mloop_end/gloop_end
// at distinct addresses but their four bl targets resolve identically
// -> genuine source duplicate.  NOTE: the Mac gloop_end body itself
// differs from PS.EXE (Mac drops get_mouse_droppings/set_mouse_refresh/
// continue_db and adds process_event) -- a different source revision --
// so the body here mirrors the DOS PS.EXE gloop_end, not the Mac one.
void mloop_end(void)
{
    get_mouse_droppings();
    show_mouse(pointer_mode);
    set_mouse_refresh();
    refresh_svga_screen();
    continue_db();
    button_time_flag = running_delay1();
}

// FUNCTION: C2 0x3D3AE
// WIN: 0x0040f844
// Lines 85–89
//
// Forum-loop end. Same as gloop_end but mouse cursor is forced to
// style 0x15 when a forum department is hovered.
//
// PS tail-jumps INTO gloop_end's body — once at +5 (else: skipping
// get_mouse_droppings) and once at +0xC (if: skipping the pointer_mode
// load too).  floop_end folds FORWARD into gloop_end's shared tail.
// This only reproduces because gloop_end is DEFINED EARLIER in this
// file (see the gloop_end banner above): source order picks gloop_end
// as the ComTail donor, while the just_idle fall-through pins gloop_end
// to its late 0x3D9DF placement.  Keep this two-branch form (NOT a
// single computed-style show_mouse) so the tail is actually shared.
void floop_end(void)
{
    get_mouse_droppings();
    if (forum_dept_over)
        show_mouse(0x15);
    else
        show_mouse(pointer_mode);
    set_mouse_refresh();
    refresh_svga_screen();
    continue_db();
    button_time_flag = running_delay1();
}

// FUNCTION: C2 0x3D3CA
// WIN: 0x0040fb4a
// Lines 98–212
void main_game_loop(void)
{
    int sub_loops;
    int i;

    cycle_count++;
    button_time_flag = running_delay1();

    if (game_speed() != 0) {
        if (turbo_mode != 0)
            sub_loops = 4;
        else
            sub_loops = 1;
        for (i = 0; i < sub_loops; i++) {
            do_32_count();
            random();
            citymap_evolution();
            if (game_state == 3) return;
            if (game_state == 2) return;
            if (game_state == 1) return;
            citizen_intelligence();
            army_intelligence();
        }
    }
    cover_mouse_droppings();
    get_mouse();

    if (turbo_mode > 1) {
        show_turbo_panel();
    } else if (map_mode == 0) {
        show_citymap();
    } else if (map_mode == 1 && pointer_mode != 5) {
        show_regionmap();
    }

    if (turbo_mode < 2) {
        write_image(misc, map_direction / 2, 0x1c4, 0x1a);
        old_pm_over = pm_over;
        pm_over = get_pm_over_diamond(0);
        if (pm_over != 0 && pointer_mode == 0 && particles_built == 0) {
            show_diamond_ptr();
        }
        if (pm_over != 0) {
            over_ptr = pm_over_cm_ptr / map_actual_atom;
            over_x = over_ptr % map_actual_width;
            over_y = over_ptr / map_actual_width;
        }
        get_over_army();
    }

    show_top_line();
    show_icon_strip();
    show_tutorial_timer();
    show_ov_bar();
    show_paused();
    show_querymode_panel();

    if (pointer_mode == 5) {
        if (gen_refresh1) {
            if (army_list[tracking_army].type == 1) {
                show_cohort_box();
            } else {
                show_non_cohort_box();
            }
            gen_refresh1 = 0;
        }
        if (army_list[tracking_army].type == 1)
            update_tribune_flag(0);
        if (army_list[tracking_army].type == 1)
            show_buttons(0x190, 0x82, cohort_buttons, 1);
    }

    if (scrolling)
        setup_map_screen_refresh();

    if (update_landfill) {
        show_landfill(com_x, com_y);
        setup_refresh_area(0x1e0, 0x30, 0xa, 0xb, 1);
        update_landfill--;
    }

    redraw_icon_bits();
    get_mouse_droppings();

    if (pm_over != 0)
        refresh_a_square(pm_over_x >> 4, pm_over_y >> 4, 2);

    /* Mouse pointer style selection (signed compare on flag_mode!=0) */
    if (flag_mode) {
        show_mouse(0xa);
    } else if (illegal_build == 1) {
        show_mouse(0x14);
    } else if (illegal_build == 2) {
        show_mouse(0x13);
    } else if (over_an_army) {
        show_mouse(0x11);
    } else if ((pointer_mode == 2 || pointer_mode == 6) && pm_over == 0) {
        show_mouse(mouse_styles[0]);
    } else {
        show_mouse(mouse_styles[pointer_mode]);
    }
    set_mouse_refresh();
    refresh_svga_screen();

    if (!scrolling && colour_cycle_delay1(0x3c) != 0 && c2inf.paused == 0) {
        if (map_mode == 0) {
            cycle_colours(0x40, 0x47);
        } else {
            cycle_colours(0x41, 0x43);
        }
        pulse_red(0x48, 6);
    }
    if (!scrolling && colour_cycle_delay2(0x96) != 0 && c2inf.paused == 0 && map_mode == 0) {
        cycle_colours(0x50, 0x55);
    }

    if (stopped_scrolling) {
        update_landfill = 1;
        clear_edge_info();
        setup_whole_screen_refresh();
        update_map = 1;
    }

    if (turbo_mode != 0)
        turbo_mode = turbo_mode + 1;

    if (flag_mode != 0)
        flag_mode_action();
    else
        action();

    if (hot_exit_flag) {
        act_exit_game();
        hot_exit_flag = 0;
    }
    if (restart_flag != 0)
        return;

    if (flag_mode_decay_count != 0) {
        flag_mode_decay_count = flag_mode_decay_count - 1;
        if (flag_mode_decay_count <= 0) {
            flag_mode = 0;
            setup_map_screen_refresh();
        }
    }
    if (!mouse_left_button)
        show_messages();
    pm_limits();
    play_ambient_fx();
    continue_db();
}

// FUNCTION: C2 0x3D816
// WIN: 0x004101e4
// Lines 214–279
void battle_game_loop(void)
{
    cycle_count++;
    button_time_flag = running_delay1();
    figure_update();
    get_units_status();
    random();

    if (game_speed() != 0 || battle_turbo != 0) {
        if (zoom_level == 1) {
            arrow_update();
            update_units_morale();
            update_units_ai();
            figure_intelligence();
            arrow_intelligence();
            do_32_count();
        }
    }
    cover_mouse_droppings();
    get_mouse();

    if (battle_setup_count != 0) {
        battle_setup_count--;
        if (battle_setup_count <= 1) {
            setup_battle_screen_refresh();
            update_map = 1;
        }
    }

    if (battle_turbo == 0 || scrolling != 0) {
        show_battlemap();
    } else {
        battle_turbo_count++;
        if (battle_turbo_count > 0x14) {
            battle_turbo_count = 0;
            show_battlemap();
            setup_battle_screen_refresh();
        }
    }

    write_image(misc, map_direction / 2, 0x264, 0x1a);
    old_pm_over = pm_over;
    pm_over = get_pm_over_diamond(0);
    show_top_line();
    battle_totals_panel();
    battle_stats_panel();

    if (scrolling)
        setup_battle_screen_refresh();

    if (update_landfill) {
        show_battle_landfill(0, 0x34, 0xb1, 0x170);
        update_landfill--;
    } else {
        update_battle_landfill();
    }

    redraw_icon_bits();
    get_mouse_droppings();
    show_mouse(mouse_styles[0]);
    set_mouse_refresh();
    refresh_svga_screen();

    if (stopped_scrolling) {
        update_landfill = 1;
        clear_edge_info();
        setup_whole_screen_refresh();
    }
    battle_action();

    if (hot_exit_flag) {
        act_exit_game();
        hot_exit_flag = 0;
    }
    if (restart_flag == 0) {
        pm_limits();
        if (battle_turbo == 0)
            play_ambient_fx();
        continue_db();
    }
}

// FUNCTION: C2 0x3D9D9
// (no confirmed CAESAR2.EXE slot; old 0x00401384 was a placeholder.)
// 1-byte body — a bare `ret`. Probably a stub-out kept for symbol
// linkage or for cases where mouse-on-top rendering is disabled.
void show_mouse_top(void)
{
}

// FUNCTION: C2 0x3D9DA
// WIN: 0x00410478  (unverified)
// Lines 299–299
//
// 5-byte function: just `call gloop_start;` then FALLS THROUGH into
// gloop_end (Rule 15-fall: Watcom elides the trailing `call gloop_end;
// ret` when gloop_end is placed immediately after).  This tail-call
// fall-through is what PINS gloop_end to address 0x3D9DF (right after
// this function) -- which is why gloop_end can be DEFINED earlier in
// the file (so it is the ComTail donor) yet still be PLACED late.  See
// the gloop_end banner for the full ordering rationale.
void just_idle_game_loop(void)
{
    gloop_start();
    gloop_end();
}

// FUNCTION: C2 0x3DA0A
// WIN: 0x0041048d
// Lines 305–313
void forum_admin_game_loop(void)
{
    gloop_start();
    show_buttons(0x178, 0x12, admin_buttons, 4);
    if (gen_refresh1) {
        gen_refresh1 = 0;
        show_tax_rates();
        show_estimate();
    }
    control_buttons(0x178, 0x12, admin_buttons, 4);
    floop_end();
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_ADMIN;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3DA8A
// WIN: 0x00410515
// Lines 315–323
void forum_career_game_loop(void)
{
    gloop_start();
    show_buttons(0xe0, 0x58, career_buttons, 3);
    if (gen_refresh1) {
        gen_refresh1 = 0;
        show_personal_cash_stats();
    }
    floop_end();
    control_buttons(0xe0, 0x58, career_buttons, 3);
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_CLERKS;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3DB05
// WIN: 0x00410598
// Lines 325–334
void donation_game_loop(void)
{
    gloop_start();
    show_buttons(0x160, 0x38, donation_buttons, 3);
    if (gen_refresh1) {
        gen_refresh1 = 0;
        show_donation_level();
    }
    gloop_end();
    control_buttons(0x160, 0x38, donation_buttons, 3);
    if (mouse_right_click)
        out1 = 1;
    if (exit_screen())
        out1 = 1;
}

// FUNCTION: C2 0x3DB84
// WIN: 0x00410624
// Lines 336–343
//
// Show emperor-related buttons unless we've already warned the
// emperor this month (in which case the panel is unclickable).
void forum_rome_game_loop(void)
{
    gloop_start();
    if (!warned_of_emperor_reply_month)
        show_buttons(0x150, 0x78, rome1_buttons, 1);
    floop_end();
    if (!warned_of_emperor_reply_month)
        control_buttons(0x150, 0x78, rome1_buttons, 1);
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_ROME;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3DBFB
// WIN: 0x004106aa
// Lines 345–353
//
// Like other forum loops but takes a `gift_index` arg in eax which
// is shifted (i*16 - 8) to get the per-gift Y offset.
void gift_game_loop(int gift_index)
{
    gloop_start();
    show_buttons(0x160, gift_index * 16 - 8, rome2_buttons, 3);
    if (gen_refresh1) {
        gen_refresh1 = 0;
        show_gift_amount(gift_index);
    }
    gloop_end();
    control_buttons(0x160, gift_index * 16 - 8, rome2_buttons, 3);
    if (mouse_right_click)
        out1 = 1;
}

// FUNCTION: C2 0x3DC73
// WIN: 0x00410736
// Lines 355–368
void forum_temple_game_loop(void)
{
    int i;

    gloop_start();
    if (gen_refresh1) {
        gen_refresh1--;
        show_temple_tip();
    }
    gloop_end();
    if (mouse_left_preclick) {
        for (i = 0; i < 4; i++) {
            if (mouse_in_area(i * 160 + 10, 0x164, 0x8c, 0x21)) {
                act_set_temple_tips(i);
                break;
            }
        }
    }
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_TEMPLE;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3DD00
// WIN: 0x004107f6
// Lines 370–378
void forum_clerks_game_loop(void)
{
    gloop_start();
    show_buttons(0x40, 0x6c, clerk_buttons, 2);
    if (gen_refresh1) {
        gen_refresh1 = 0;
        history_graphs();
        history_selection();
    }
    control_buttons(0x40, 0x6c, clerk_buttons, 2);
    floop_end();
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_CAREER;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3DD80
// WIN: 0x00410878
// Lines 380–385
void forum_advisor_game_loop(void)
{
    gloop_start();
    gloop_end();
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_ADVISOR;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3DDAF
// WIN: 0x004108b4
// Lines 387–429
void forum_empire_game_loop(void)
{
    if (c2inf.peace_mode) {
        forum_advisor_game_loop();
        return;
    }
    gloop_start();
    get_region_over();
    show_empire_top_slab();

    if (region_over != 0) {
        if (known_world(region_over - 1)) {
            font_centre(6, region_over, 0xd8, 0x1e, 0xdc, font1, 0x3f);
        } else {
            font_centre(0x30, 4, 0xd8, 0x1e, 0xdc, font1, 0x3f);
        }
    } else {
        x_is = 0;
        font_list(0x22, 2, 0xd8, 0x1e, font1, 0x3f);
        show_date(year, x_is + 0xd8, 0x1e, 2);
    }
    setup_refresh_area(0xd2, 0x1a, 0x12, 2, 1);
    gloop_end();

    if (mouse_left_preclick && region_over != 0 && known_world(region_over - 1)) {
        this_region_box(1);
        out1 = 0;
        while (out1 == 0) {
            just_idle_game_loop();
            if (mouse_right_click)
                out1 = 1;
        }
        stop_db();
        clear_mouse();
        out1 = 0;
        basic_empire_screen();
    }

    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_EMPIRE;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
        readfile("forumbit.pl8", ((void *)scratch_buffer), 0xea60, 0);
        readfile("forum_x.gd8", ((void *)((scratch_buffer) + (0x1d4c0))), 0xfa0, 0);
    }
}

// FUNCTION: C2 0x3DF63
// WIN: 0x00410a8d
// Lines 431–448
void forum_army_game_loop(void)
{
    if (c2inf.peace_mode) {
        forum_advisor_game_loop();
        return;
    }
    no_of_army_buttons = 5;
    if (total_no_of_cohorts > 0) {
        if (forum_viewed_army == 10)
            no_of_army_buttons = 7;
        else
            no_of_army_buttons = 8;
    }
    gloop_start();
    update_tribune_flag(1);
    show_buttons(0x18, 0x30, army_buttons, no_of_army_buttons);
    if (max_mercs_allowed) {
        show_buttons(0x18, 0x30, mercenary_buttons, 2);
    }
    if (gen_refresh1) {
        gen_refresh1 = 0;
        show_recruitment();
    }
    if (gen_refresh2) {
        gen_refresh2 = 0;
        show_this_tribune();
    }
    if (gen_refresh3) {
        gen_refresh3 = 0;
        show_mercs();
    }
    control_buttons(0x18, 0x30, army_buttons, no_of_army_buttons);
    if (max_mercs_allowed) {
        control_buttons(0x18, 0x30, mercenary_buttons, 2);
    }
    floop_end();
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_ARMY;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3E09E
// WIN: 0x00410be8
// Lines 450–455
void forum_industry_game_loop(void)
{
    gloop_start();
    floop_end();
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_INDUSTRY;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3E0CD
// WIN: 0x00410c24
// Lines 457–476
void forum_slaves_game_loop(void)
{
    int i;

    gloop_start();
    if (gen_refresh1) {
        gen_refresh1 = 0;
        show_slave_welfare_bill();
    }
    if (gen_refresh2) {
        gen_refresh2 = 0;
        show_slave_allocation();
    }
    show_buttons(0x40,  0x72, slave1_buttons, 2);
    show_buttons(0x1ae, 0x26, slave2_buttons, 0xc);
    control_buttons(0x40,  0x72, slave1_buttons, 2);
    control_buttons(0x1ae, 0x26, slave2_buttons, 0xc);
    floop_end();
    if (mouse_left_preclick) {
        for (i = 1; i < 7; i++) {
            if (mouse_in_area(0x216, i * 24 + 18, 0x50, 0x14)) {
                act_set_slaves_to_need_level(i);
                break;
            }
        }
    }
    if (mouse_right_click) {
        last_forum_dept = FORUM_DEPT_SLAVES;
        forum_dept = FORUM_DEPT_OVERVIEW;
        out1 = 2;
    }
}

// FUNCTION: C2 0x3E1D3
// WIN: 0x00410d4f
// Lines 478–484
void forum_idle_game_loop(void)
{
    gloop_start();
    explain_forum();
    floop_end();
    if (mouse_right_click)
        out1 = 1;
}

// FUNCTION: C2 0x3E1F6
// WIN: 0x00410d82
// Lines 486–495
void explain_forum(void)
{
    int i;

    if (out1 == 1) return;
    for (i = 0; i < FORUM_DEPT_END; i++) {
        if (i == forum_dept_over)
            forum_explanations(i, 1);
        else
            forum_explanations(i, 0);
    }
}

// FUNCTION: C2 0x3E227
// WIN: 0x00410df1
// Lines 497–508
//
// Render one of the 12 forum-department info panels: a 9x1 mosaic
// background plus the dept name in font1. `forum_menu[idx*2]` /
// `forum_menu[idx*2+1]` are the panel x/y; the +8/+5 offsets
// position the inner content area.
void forum_explanations(int idx, int hilite)
{
    int x;
    int y;

    x = forum_menu[idx].x + 8;
    y = forum_menu[idx].y + 5;
    stone_random_count = 0xb;
    show_a_mosaic_blank(x, y, 9, 1);
    if (hilite == 0)
        font_list(0x1d, idx, x + 4, y + 2, font1, 0x10);
    else
        font_list(0x1d, idx, x + 4, y + 2, font1, 0xb);
    setup_refresh_area(x, y, 0xa, 2, 1);
}

// FUNCTION: C2 0x3D9DA
// WIN: 0x00410478  (unverified)
//
// Dead (uncalled) byte-identical twin of just_idle_game_loop -- a
// source duplicate that Watcom ICF-folds onto just_idle's address
// (both PUBDEFs resolve to 0x3D9DA in PS).  The Mac builds keep the
// two separate at distinct addresses but with identical structure and
// call targets, confirming it is a true duplicate (not demo/ifdef
// variation).  Body must mirror just_idle exactly so ICF fires.
void year_end_game_loop(void)
{
    gloop_start();
    gloop_end();
}

// FUNCTION: C2 0x3E2A3
// WIN: 0x00410ea4
// Lines 520–525
//
// Tail-merger — jmp FORWARD to skill1+0x34 (Rule 15).
void battle_intro_game_loop(void)
{
    gloop_start();
    show_buttons(0x100, 0x104, confirming_buttons, 2);
    gloop_end();
    control_buttons(0x100, 0x104, confirming_buttons, 2);
}

// FUNCTION: C2 0x3E2E2
// WIN: 0x00410eeb
// Lines 530–537
void tune_game_loop(void)
{
    gloop_start();
    show_buttons(0x50, 0x80, tunes_buttons, 2);
    gloop_end();
    control_buttons(0x50, 0x80, tunes_buttons, 2);
    if (mouse_right_click)
        out1 = 1;
}

// FUNCTION: C2 0x3E338
// WIN: 0x00410f45
// Lines 539–546
void samples_game_loop(void)
{
    gloop_start();
    show_buttons(0x50, 0x80, samples_buttons, 5);
    gloop_end();
    control_buttons(0x50, 0x80, samples_buttons, 5);
    if (mouse_right_click)
        out1 = 1;
}

// FUNCTION: C2 0x3E38E
// WIN: 0x00410f9f
// Lines 548–555
void tog_anims_game_loop(void)
{
    gloop_start();
    show_buttons(0x50, 0x80, tog_anims_buttons, 1);
    gloop_end();
    control_buttons(0x50, 0x80, tog_anims_buttons, 1);
    if (mouse_right_click)
        out1 = 1;
}

// FUNCTION: C2 0x3E3E4
// WIN: 0x00410ff9
// Lines 557–564
void tog_yearend_game_loop(void)
{
    gloop_start();
    show_buttons(0x50, 0x80, tog_yearend_buttons, 2);
    gloop_end();
    control_buttons(0x50, 0x80, tog_yearend_buttons, 2);
    if (mouse_right_click)
        out1 = 1;
}

// FUNCTION: C2 0x3E43A
// WIN: 0x00411053
// Lines 566–571
//
// Tail-merges into skill1_game_loop's `call control_buttons` block
// at +0x34 (Rule 15 cross-function). Watcom emits `jmp skill1+0x34`
// instead of duplicating the call+epilogue.
void exit_game_loop(void)
{
    gloop_start();
    show_buttons(0, 0, exit_buttons, 3);
    gloop_end();
    control_buttons(0, 0, exit_buttons, 3);
}

// FUNCTION: C2 0x3E46A
// WIN: 0x0041108e
// Lines 574–579
//
// Merge target for the control_buttons-tail cluster (battle_intro,
// exit, promotion all jmp into +0x34 here).
void skill1_game_loop(void)
{
    gloop_start();
    show_buttons(0x50, 0x50, skill1_buttons, 4);
    gloop_end();
    control_buttons(0x50, 0x50, skill1_buttons, 4);
}

// FUNCTION: C2 0x3E4A7
// WIN: 0x004110c9
// Lines 582–589
//
// Tail-merger — jmp into skill1+0x2D (sharing the bigger tail
// `mov edx,0x50; mov eax,edx; call control_buttons; pop;pop;pop;ret`).
void skill2_game_loop(void)
{
    gloop_start();
    if (gen_refresh1) {
        gen_refresh1 = 0;
        show_skill_level();
    }
    if (gen_refresh2) {
        gen_refresh2 = 0;
        show_peace_level();
    }
    show_buttons(0x50, 0x50, skill2_buttons, 6);
    gloop_end();
    control_buttons(0x50, 0x50, skill2_buttons, 6);
}

// FUNCTION: C2 0x3E502
// WIN: 0x0041113a
// Lines 592–630
//
// 2026-06-13 byte-EXACT (was 17b residue): the table index form
// `empire_region_order[region_over + 10]` keeps region_over live in
// EAX past the load (PS picks EDX for the table-value temp).  The
// pointer-decay form `(&empire_region_order[10])[region_over]` makes
// the codegen route the address through EAX, clobbering region_over
// and forcing a reload before `empire[region_over - 1] = 6`.
// Both spellings are semantically identical (C9899 6.5.6); only the
// tree-genned shape differs.  Source-shape lever, not a regalloc tie.
void initreg_game_loop(void)
{


    gloop_start();
    if (out2 == 0) {
        get_region_over();
        show_empire_top_slab();
        if (region_over != 0) {
            x_is = 0;
            if (known_world(region_over - 1)) {
                font_centre(6, region_over, 0xd2, 0x1e, 0xdc, font1, 0x3f);
            } else {
                font_centre(0x30, 4, 0xd2, 0x1e, 0xdc, font1, 0x3f);
            }
        } else {
            x_is = 0;
            font_list(0x22, 2, 0xd8, 0x1e, font1, 0x3f);
            show_date(year, x_is + 0xd8, 0x1e, 2);
        }
        setup_refresh_area(0xd2, 0x1a, 0x12, 2, 1);
    }
    gloop_end();

    if (out2 > 1) {
        out2 = out2 - 1;
        goto end;
    }
    if (!mouse_left_click)
        goto end;
    if (region_over == 0)
        goto end;
    /* empire[] is 1-based here via region_over (Watcom folds the -1 into
       the base address: PS reads byte [empire - 1 + region_over]). */
    if ((empire[region_over - 1] & 0xff) != 2)
        goto end;

    this_region();
    if (decision == 1) {
        out2 = 0x64;
        province_is = region_over - 1;
        province_difficulty = empire_region_order[region_over + 10];
        empire[region_over - 1] = 6;
    }
    reshow_initreg_box();
end:;
}

// FUNCTION: C2 0x3E673
// WIN: 0x004112b7
// Lines 632–656
//
// Province-naming text-entry game loop. Edits format_buffer (the
// running line of typed text) on every frame, repaints the entry
// region, and exits (`out2 = 1`) on Escape, Enter, or right-click.
//
// `c2inf + 0x1A` is the running text buffer that out_format_buffer
// flushes the format-buffer into.
void new_name_game_loop(void)
{
    int y;

    hold_hot_keys = 1;
    gloop_start();
    if (edit_format_buffer())
        out2 = 1;
    get_fb_length();
    out_format_buffer(c2inf.player_name);
    got_cursx = 0;
    cursor_x = 0;
    fb_count = 0;
    y = 0xe0;
    cursor_y = y;
    allow_padding = 1;
    x_is = 0;
    show_a_system_blank(y, 0xd8, 0xc, 2);
    put_a_font_string(c2inf.player_name, 0xe2, y, font1, 0x10);
    fb_max_width_reached = (get_fb_width(font1) > fb_line_length);
    if (got_cursx == 0) {
        cursor_x = x_is;
        got_cursx = 1;
    }
    cursor_x += 0xe2;
    show_cursor(font1);
    setup_refresh_area(0xe0, 0xd0, 0xc, 3, 1);
    if (key_ascii == 0x1b) out2 = 1;
    if (key_ascii == 0xd)  out2 = 1;
    if (mouse_right_click) out2 = 1;
    gloop_end();
}

// FUNCTION: C2 0x3E7B1
// WIN: 0x00411428
// Lines 658–664
//
// Note the order: show_buttons → control_buttons → gloop_end
// (different from sibling loops which do show → gloop_end → control).
void help_game_loop(void)
{
    gloop_start();
    show_buttons(0x168, 0x1a0, help_buttons, 2);
    control_buttons(0x168, 0x1a0, help_buttons, 2);
    gloop_end();
}

// FUNCTION: C2 0x3E7F4
// WIN: 0x0041146f
// Lines 666–675
//
// Tooltip/query loop. Shows queery_buttons always, plus an extra
// query_buttons2 panel when (map_mode == regionmap) AND (q_type == 0x92).
void queery_game_loop(void)
{
    gloop_start();
    show_buttons(8, 0x20, queery_buttons, nof_query_buttons);
    if (map_mode == 1 && q_type == 0x92)
        show_buttons(8, 0x20, query_buttons2, 1);
    gloop_end();
    control_buttons(8, 0x20, queery_buttons, nof_query_buttons);
    if (map_mode == 1 && q_type == 0x92)
        control_buttons(8, 0x20, query_buttons2, 1);
    get_queried_person();
}

// FUNCTION: C2 0x3E8AA
// WIN: 0x00411521
// Lines 677–682
//
// Forward tail-merger — jmp BACKWARD to skill1+0x34 (Rule 15).
void promotion_game_loop(void)
{
    gloop_start();
    show_buttons(0x80, 0x70, promotion_buttons, 3);
    gloop_end();
    control_buttons(0x80, 0x70, promotion_buttons, 3);
}

// FUNCTION: C2 0x3E8E9
// WIN: 0x00411562
// Lines 687–709
//
// Decide whether the game-tick should advance this frame. Returns 1
// if the cumulative button-time tick passed the speed threshold,
// 0 otherwise. Always returns 1 in turbo. Inhibited by the
// game-paused flag (c2inf[6]), active scrolling, an active
// flag_mode, the pointer being in flag-mode (>=5), or the left
// mouse button being held.  Nested positive guards keep PS's shared
// return-0 tail without a source label (Rule 92).
int game_speed(void)
{
    int q;

    cmu_count[1] += button_time_flag;
    if (turbo_mode > 1)
        return 1;

    q = (100 - c2inf.game_speed) / 10;
    if (q < 10) {
        if (!c2inf.paused) {
            if (!scrolling) {
                if (flag_mode == 0) {
                    if (pointer_mode < 5) {
                        if (!mouse_left_button) {
                            if (q * 50 + 50 <= cmu_count[1]) {
                                cmu_count[1] = flag_mode;  /* known 0 — lets Watcom reuse esi reg */
                                return 1;
                            }
                        }
                    }
                }
            }
        }
    }
    return 0;
}

// FUNCTION: C2 0x3E972
// WIN: 0x00411657
// Lines 712–726
//
// Decide whether the map should auto-scroll this frame. Uses the
// Rule-92 positive-success form so Watcom keeps a single shared
// return-0 tail; repeated early `return 0` guards diverge.
int scroll_speed(void)
{
    int q;

    cmu_count[2] += button_time_flag;
    q = (100 - c2inf.scroll_speed) / 10;
    if (q < 10) {
        if (q * 50 + 20 <= cmu_count[2]) {
            cmu_count[2] = 0;
            return 1;
        }
    }
    return 0;
}

