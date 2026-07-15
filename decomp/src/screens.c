// D:\C2\CODE\screens.c

#include "c2_data.h"
#include "c2_types.h"   /* struct request_message */

int history_graph_years[5] = { 10, 20, 50, 100, 200 };

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
#ifndef _MSC_VER   /* MSVC win-oracle build force-includes c2_funcs.h (typed) */
extern int affected_by_cover1();  /* really char -- map.c */
extern int affected_by_cover2();  /* really char -- map.c */
#endif


extern void put_a_font_string(char *str, int x, int y, unsigned char *font, int color);
extern void font_list(int idx, int word_count, int x, int y, unsigned char *font, int color);
extern void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color);
extern void font_format_split(int idx, int word_skip, int x, int y_start, int max_width, int line_limit, int x_overflow, int max_width_overflow, unsigned char *font, int color);
extern void show_cursor(unsigned char *font);

/* asm-resident helpers (decomp/src/library.asm) */

// FUNCTION: C2 0x5B181
// WIN: 0x00422530
// Lines 120–153
//
// Full city-map screen redraw.  Optionally blackens first, loads the
// city interface PL8 art into scratch_buffer, restores its four pieces,
// clips map edges, draws the city map/menu/compass/landfill overlays,
// refreshes topline/icons, flips the SVGA buffer, then installs the
// city palette.  If the art load fails, emits the debug beep and returns.
void city_map_screen(int do_black_out)
{
    int dir;

    if (do_black_out == 1) black_out();
    hold_mouse_replace = 1;
    setup_whole_screen_refresh();
    if (readfile("int_city.pl8", ((void *)scratch_buffer),
                 0x1d4c0, 0) == 0) {
        test_beeps();
        return;
    }
    draw_a_line(0x1de, 0x30, 0x1de, 0xd0, 0x1f);
    draw_a_line(0x1df, 0x30, 0x1df, 0xd0, 0x12);
    restore_picture_part(scratch_buffer, 0);
    restore_picture_part(scratch_buffer, 1);
    restore_picture_part(scratch_buffer, 2);
    restore_picture_part(scratch_buffer, 3);
    clip_zoom_level1();
    clip_map_bottom();
    flush_sb_buffer();
    show_menus(main_menu, 4, 0);
    update_map = 1;
    show_citymap();
    write_image(misc, map_direction / 2, 0x1c4, 0x1a);
    show_landfill(com_x, com_y);
    redraw_topline = 1;
    update_ov_bar = 1;
    update_map = 1;
    redraw_icons = 2;
    show_top_line();
    redraw_icon_bits();
    refresh_svga_screen();
    set_palette(city_palette);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5B2CA
// WIN: 0x00422610
// Lines 155–183
//
// Build and display the region-map screen.  Optionally fades to black,
// loads the base province PL8 into scratch_buffer, restores the four
// image quadrants, draws menus/compass/landfill cursor, refreshes the
// top-line/icon areas, then installs the region palette.
void region_map_screen(int do_black_out)
{
    if (do_black_out == 1) {
        black_out();
    }
    hold_mouse_replace = 1;
    setup_whole_screen_refresh();
    if (readfile("int_prov.pl8", ((void *)scratch_buffer), 0x1d4c0, 0) == 0) {
        test_beeps();
        return;
    }

    restore_picture_part(scratch_buffer, 0);
    restore_picture_part(scratch_buffer, 1);
    restore_picture_part(scratch_buffer, 2);
    restore_picture_part(scratch_buffer, 3);
    clip_zoom_level1();
    clip_map_bottom();
    flush_sb_buffer();
    show_menus(main_menu, 4, 0);
    show_regionmap();
    write_image(misc, map_direction / 2, 0x1c4, 0x1a);
    show_landfill(com_x, com_y);
    redraw_topline = 1;
    redraw_icons = 2;
    show_top_line();
    redraw_icon_bits();
    refresh_svga_screen();
    set_palette(region_palette);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5B3CB
// WIN: 0x004226d5
// Lines 185–216
//
// Set up the in-battle UI screen.  Loads the batlfix2 palette and
// int_batl picture, paints the four panel quadrants via
// restore_picture_part(0..3), writes the enemy-army-type label and a
// placeholder header (both font_list 7), runs the battle-map render
// pipeline (show_battlemap + write_image of the compass blip at
// map_direction/2 + show_battle_landfill), bumps the top-line /
// overlay-bar / map / icon-strip refresh flags, redraws the icon
// strip, refreshes the SVGA framebuffer, and applies the
// temp_palette.
//
// When called with skipblackout != 1 the initial black_out() is
// suppressed (used by battle continuations that already wiped the
// screen).  When int_batl.pl8 fails to load the function aborts via
// test_beeps() and the regular epilogue.
void battle_screen(int skipblackout)
{
    if (skipblackout == 1) black_out();

    hold_mouse_replace = 1;
    setup_whole_screen_refresh();

    readfile("batlfix2.256", temp_palette, 0x300, 0);
    if (readfile("int_batl.pl8", ((void *)scratch_buffer), 0x1d4c0, 0) == 0) {
        test_beeps();
        return;
    }

    restore_picture_part(scratch_buffer, 0);
    restore_picture_part(scratch_buffer, 1);
    restore_picture_part(scratch_buffer, 2);
    restore_picture_part(scratch_buffer, 3);

    font_list(7,
              army_list[their_battle_army].source_region,
              0x32, 0x172, font1, 0x10);
    font_list(7, 0, 0x32, 0x1a8, font1, 0x10);

    clip_battle_zoom_level2();
    flush_sb_buffer();
    show_menus(main_menu, 4, 0);

    update_map = 1;
    show_battlemap();

    write_image(misc, map_direction / 2, 0x264, 0x1a);
    show_battle_landfill(0, 0x34, 0xb1, 0x170);

    redraw_topline = 1;
    update_ov_bar  = 1;
    update_map     = 4;
    redraw_icons   = 2;
    redraw_icon_bits();

    refresh_svga_screen();
    set_palette(temp_palette);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5B53D
// WIN: 0x004227f5
// Lines 220–326
//
// Right-pane battle stats panel.  Dirty-checks the cached values in
// request_message (bs_nof_units / bs_men / bs_morale / bs_type and
// prev_mode / pointer_mode / last_icon_over) and bails when nothing
// changed.  Otherwise repaints one of four modes:
//   * pointer_mode == 1 -> wrapped help text (0x76 word 0x11).
//   * pointer_mode == 2 -> wrapped help text (0x76 word 0x12).
//   * icon-over hover  -> per-icon help text (0x76 word
//     last_icon_over - 4).
//   * default          -> unit type / count / health bars
//     (game_panels image 0x39) / morale bars (image 0x38),
//     scaled by ceil(stats_men / start_men) and stats_morale / 10.
void battle_stats_panel(void)
{
    int a;  /* ratio / bar count */
    int b;  /* loop counter */
    int c;  /* mode */

    c = 0;

    if (redraw_icons != 0) c = 1;
    if (request_message.bs_nof_units != battle_stats_nof_units) c = 1;
    if (request_message.bs_men != battle_stats_men) c = 1;
    if (request_message.bs_morale != battle_stats_morale) c = 1;
    if (request_message.bs_type != battle_stats_type) c = 1;

    if (request_message.prev_mode == 1) {
        if (pointer_mode == 1) c = 3;
        else if (pointer_mode == 2) c = 4;
        else if (last_icon_over != 0) c = 2;
    } else if (request_message.prev_mode == 2) {
        if (pointer_mode == 1) c = 3;
        else if (pointer_mode == 2) c = 4;
        else if (last_icon_over == 0) c = 1;
        if (last_icon_over != 0 && last_icon_over != request_message.icon_over) c = 2;
    } else if (request_message.prev_mode == 3 && pointer_mode != 1) {
        if (pointer_mode == 2) c = 4;
        else if (last_icon_over != 0) c = 2;
        else c = 1;
    } else if (request_message.prev_mode == 4 && pointer_mode != 2) {
        if (pointer_mode == 1) c = 3;
        else if (last_icon_over != 0) c = 2;
        else c = 1;
    }
    if (c == 0) return;

    request_message.bs_nof_units = battle_stats_nof_units;
    request_message.bs_men       = battle_stats_men;
    request_message.bs_morale    = battle_stats_morale;
    request_message.bs_type      = battle_stats_type;

    sprite_width = 0xa; sprite_height = 0x68;
    show_fast_rect(0x1db, 0x170, 0x1a);

    if (c == 3) {
        request_message.prev_mode = 3;
        font_format_split(0x76, 0x11,
                          0x1e2, 0x180, 0x90, 0x64, 0, 0, font1, 0x10);
    } else if (c == 4) {
        request_message.prev_mode = 4;
        font_format_split(0x76, 0x12,
                          0x1e2, 0x180, 0x90, 0x64, 0, 0, font1, 0x10);
    } else if (c == 2) {
        request_message.icon_over = last_icon_over;
        request_message.prev_mode = 2;
        font_format_split(0x76, last_icon_over - 4,
                          0x1e2, 0x190, 0x90, 0x64, 0, 0, font1, 0x10);
    } else {
        if (battle_stats_nof_units == 0) {
            request_message.prev_mode = 1;
            font_list(0x2f, 0, 0x1e6, 0x190, font1, 0x10);
            x_is = 0;
            font_no(0, 0x20, " ", 0x1ee, 0x1a0, font1, 0x10);
            font_list(0x2f, 1, x_is + 0x1ee, 0x1a0, font1, 0x10);
        } else {
            request_message.prev_mode = 1;
            if (battle_stats_nof_units == 1) {
                font_list(0x2f, 2, 0x1ee, 0x174, font1, 0x10);
            } else {
                x_is = 0;
                font_no(battle_stats_nof_units, 0x20, " ", 0x1ee, 0x174, font1, 0x10);
                font_list(0x2f, 1, x_is + 0x1ee, 0x174, font1, 0x10);
            }
            if (battle_stats_control == 0) {
                font_list(0x47, battle_stats_type + 0xa,
                          0x1ee, 0x188, font1, 0x10);
            } else {
                font_list(0x2f, battle_stats_type + 2,
                          0x1ee, 0x188, font1, 0x10);
            }
            x_is = 0;
            font_list(0x2f, 8, 0x1ee, 0x198, font1, 0x10);
            font_no(battle_stats_men, 0x20, " ",
                    x_is + 0x1ee, 0x198, font1, 0x10);

            a = valueDIVtotal(battle_stats_men, battle_stats_start_men);
            if (a % 10 != 0)
                a = a / 10 + 1;
            else
                a = a / 10;
            for (b = 0; b < a; b++)
                write_image(game_panels, 0x39,
                            b * 9 + 0x1ee, 0x1a5);

            x_is = 0;
            font_list(0x2f, 9, 0x1ee, 0x1b8, font1, 0x10);
            font_no(battle_stats_morale, 0x20, " ",
                    x_is + 0x1ee, 0x1b8, font1, 0x10);

            a = battle_stats_morale / 10;
            if (battle_stats_morale % 10 != 0) a++;
            for (b = 0; b < a; b++)
                write_image(game_panels, 0x38,
                            b * 9 + 0x1ee, 0x1c8);
        }
    }

    setup_refresh_area(0x1e6, 0x170, 0xa, 7, 1);
}

// FUNCTION: C2 0x5BA21
// WIN: 0x00422e53
// Lines 329–378
//
// Repaint the top-of-battle-map totals panel: "their" and
// "our" armies’ man-counts + morale bars side by side.
// Dirty-checks against request_message+0x24..0x30 + the
// redraw_icons flag; bails when nothing changed.
//
// Layout: two 9-pixel-wide rectangles get cleared (at
// x=0x17E / 0x1B4 for enemy / friendly columns), then four
// rows:
//   * their_battle_men (font_no) + bars from game_panels
//     image 0x39 advancing right from 0x2E in 9-pixel steps,
//     ceil(men_ratio / 10) bars.
//   * their_battle_morale (font_no) + bars from image 0x38
//     advancing right from 0x30, ceil(morale / 10) bars.
//   * our_battle_men (font_no) + bars from image 0x3A
//     advancing LEFT from 0x73 (mirrored layout).
//   * our_battle_morale (font_no) + bars from image 0x38
//     advancing LEFT from 0x73, ceil(morale / 10) bars.
// Tail-merges into setup_refresh_area(0x0, 0x180, 0xB, 6, 1).
void battle_totals_panel(void)
{
    int dirty = 0;
    int ratio;
    int bars;
    int rem;
    int i;

    if (request_message.bt_their_men    != their_battle_men)    dirty = 1;
    if (request_message.bt_our_men      != our_battle_men)      dirty = 1;
    if (request_message.bt_their_morale != their_battle_morale) dirty = 1;
    if (request_message.bt_our_morale   != our_battle_morale)   dirty = 1;
    if (redraw_icons != 0)                          dirty = 1;
    if (!dirty) return;

    request_message.bt_their_men    = their_battle_men;
    request_message.bt_our_men      = our_battle_men;
    request_message.bt_their_morale = their_battle_morale;
    request_message.bt_our_morale   = our_battle_morale;

    sprite_width  = 9;
    sprite_height = 0x22;
    show_fast_rect(4, 0x17e, 0x1a);
    sprite_width  = 9;
    sprite_height = 0x22;
    show_fast_rect(0x1d, 0x1b4, 0x1a);

    font_no(their_battle_men, 0x20, " ", 0xc, 0x182, font1, 0x10);
    ratio = valueDIVtotal(their_battle_men, their_battle_start_men);
    rem   = ratio % 10;
    bars  = ratio / 10;
    if (rem != 0) bars = bars + 1;
    for (i = 0; i < bars; i++)
        write_image(game_panels, 0x39,
                    i * 9 + 0x2e, 0x181);

    font_no(their_battle_morale, 0x20, " ", 0xc, 0x194, font1, 0x10);
    bars = their_battle_morale / 10;
    if (their_battle_morale % 10 != 0) bars = bars + 1;
    for (i = 0; i < bars; i++)
        write_image(game_panels, 0x38,
                    i * 8 + 0x30, 0x194);

    font_no(our_battle_men, 0x20, " ", 0x82, 0x1b6, font1, 0x10);
    ratio = valueDIVtotal(our_battle_men, our_battle_start_men);
    rem   = ratio % 10;
    bars  = ratio / 10;
    if (rem != 0) bars = bars + 1;
    for (i = 0; i < bars; i++)
        write_image(game_panels, 0x3a,
                    0x73 - i * 9, 0x1b5);

    font_no(our_battle_morale, 0x20, " ", 0x82, 0x1c8, font1, 0x10);
    bars = our_battle_morale / 10;
    if (our_battle_morale % 10 != 0) bars = bars + 1;
    for (i = 0; i < bars; i++)
        write_image(game_panels, 0x38,
                    0x73 - i * 8, 0x1c8);

    setup_refresh_area(0, 0x180, 0xb, 6, 1);
}

// FUNCTION: C2 0x5BD04
// WIN: 0x004231d9
// Lines 380–388
//
// Battle setup modal: fixed mosaic window, heading/subheading,
// wrapped explanatory text, and an OK/continue prompt.
void show_battle_setup_box(void)
{
    stone_random_count = 0xf;
    show_a_mosaic_window(0x90, 0x80, 0x16, 0xd);
    font_list(0x4d, 0x15, 0xc0, 0x9c, font2, 0x10);
    font_list(0x4d, 0x16, 0x100, 0xbc, font1, 0x10);
    font_format_split(0x4d, 0x18, 0xb0, 0xd0, 0x120, 0x64, 0, 0, font1, 0x10);
    font_list(9, 1, 0x100, 0x130, font1, 0x10);
}

// FUNCTION: C2 0x5BDB6
// WIN: 0x00423280
// Lines 390–400
//
// Render the "Paused" overlay banner.  Compares the current paused
// flag (c2inf.paused) against a per-instance stash at
// request_message + 0x34; if it changed, request a whole-screen
// refresh so the banner gets repainted.  Then, when paused, draw
// a 14×4 mosaic window at (0x80, 0x20) and emit paragraph string
// 9 (2 words wide) at (0xa0, 0x34) in font2.
void show_paused(void)
{
    if (c2inf.paused != request_message.paused)
        setup_whole_screen_refresh();
    request_message.paused = c2inf.paused;
    if (c2inf.paused != 0) {
        stone_random_count = 0xf;
        show_a_mosaic_window(0x80, 0x20, 0xe, 4);
        font_list(9, 2, 0xa0, 0x34, font2, 0x10);
    }
}

// FUNCTION: C2 0x5BE21
// WIN: 0x004232df  (unverified)
// Lines 402–412
//
// At zoom level 1, paint a 1-pixel black L-shape along the
// top, bottom, and bottom-2 edges of the rendered map area
// to mask any garbage between the map and the side panels.
// Top edge: vertical strip at x=0 from y=0x18..0x1df
// (4-point fill).  Bottom row at y=0x1d8: 4-point fill
// every 4 px from x=0..0x1d8 then 2-point fill at the tail.
// Same for y=0x1d9.
//
// zoom_level read as a single byte (movzx ecx, byte ptr)
// so the (zoom_level & 0xff) idiom in C is required to
// match the codegen.
void clip_zoom_level1(void)
{
    int i;

    if (zoom_level == 1) {
        for (i = 0x18; i < 0x1e0; i++) {
            show_internal_4point(0, i, 0);
        }
        for (i = 0; i < 0x1dc; i += 4) {
            show_internal_4point(i, 0x1d8, 0);
        }
        show_internal_2point(i, 0x1d8, 0);
        for (i = 0; i < 0x1dc; i += 4) {
            show_internal_4point(i, 0x1d9, 0);
        }
        show_internal_2point(i, 0x1d9, 0);
    }
}

// FUNCTION: C2 0x5BEA0
// WIN: 0x004232ed  (unverified)
// Lines 414–420
//
// At zoom level 2 in the battle view, paint a 1-pixel black
// vertical strip at x=0..0 (4-point) and x=4..5 (2-point) for
// each row from y=0x18 to y=0x167.  Used to mask the leftmost
// columns when the battle map is offset for the side panel.
void clip_battle_zoom_level2(void)
{
    int i;
    if (zoom_level == 2) {
        for (i = 0x18; i < 0x168; i++) {
            show_internal_4point(0, i, 0);
            show_internal_2point(4, i, 0);
        }
    }
}

// FUNCTION: C2 0x5BEDB
// WIN: 0x004232fb  (unverified)
// Lines 422–430
//
// Paint six black bottom clip rows (y=0x1da..0x1df): 4-point blocks
// across x=0..0x1d8, then a 2-point tail at x=0x1dc.
void clip_map_bottom(void)
{
    int x;

    for (x = 0; x < 0x1dc; x += 4) show_internal_4point(x, 0x1da, 0);
    show_internal_2point(x, 0x1da, 0);
    for (x = 0; x < 0x1dc; x += 4) show_internal_4point(x, 0x1db, 0);
    show_internal_2point(x, 0x1db, 0);
    for (x = 0; x < 0x1dc; x += 4) show_internal_4point(x, 0x1dc, 0);
    show_internal_2point(x, 0x1dc, 0);
    for (x = 0; x < 0x1dc; x += 4) show_internal_4point(x, 0x1dd, 0);
    show_internal_2point(x, 0x1dd, 0);
    for (x = 0; x < 0x1dc; x += 4) show_internal_4point(x, 0x1de, 0);
    show_internal_2point(x, 0x1de, 0);
    for (x = 0; x < 0x1dc; x += 4) show_internal_4point(x, 0x1df, 0);
    show_internal_2point(x, 0x1df, 0);
}

// FUNCTION: C2 0x5BFD2
// WIN: 0x00423309
// Lines 433–477
//
// Pump one frame of pending icon-strip redraws.  Decrements
// redraw_icons (bail when already zero), redraws the persistent
// strip elements for the current map_mode (city/region/battle), and
// then conditionally repaints the tutorial-tooltip box when
// tutorial_mode is on.  Finally consumes a single update_icon
// request via the map-mode-specific draw_*_map_part helper, with the
// city/region branch skipping ids 0..0xd and 0x12 (those are
// implicit in the strip refresh) and the battle branch only
// handling ids > 0xb.
void redraw_icon_bits(void)
{
    if (redraw_icons == 0) return;
    redraw_icons--;

    if (map_mode == 0) {
        draw_city_map_part(2);
        draw_city_map_part(3);
        draw_city_map_part(0xa);
    } else if (map_mode == 1) {
        draw_region_map_part(2);
        draw_region_map_part(3);
        draw_city_map_part(0xc);
    } else if (map_mode == 2) {
        draw_battle_part(3);
        if (zoom_level == 1) draw_battle_part(6);
        else                                draw_battle_part(7);
        if (c2inf.paused == 0) draw_battle_part(8);
        if (pointer_mode == 1)     draw_battle_part(0xa);
        if (pointer_mode == 2)     draw_battle_part(0xb);
    }

    if (tutorial_mode != 0) {
        if (map_mode == 0)      grey_city_map_parts();
        else if (map_mode == 1) grey_region_map_parts();
        show_a_system_window(0x1df, 0x170, 0xa, 7);
        font_list(0x31, 7, 0x1ea, 0x17c, font2, 0x10);
        font_list(0x31, 8, 0x208, 0x19a, font2, 0x10);
        show_an_exit_button(0x258, 0x1b8);
        show_tutorial_timer();
    }

    if (update_icon != 0) {
        if (map_mode == 0) {
            if (update_icon >= 0xe && update_icon != 0x12) draw_city_map_part(update_icon);
        } else if (map_mode == 1) {
            if (update_icon >= 0xe && update_icon != 0x12) draw_region_map_part(update_icon);
        } else if (map_mode == 2) {
            if (update_icon > 0xb) draw_battle_part(update_icon);
        }
    }

    setup_whole_screen_refresh();
    flush_sb_buffer();
}

// FUNCTION: C2 0x5C1A4
// WIN: 0x00423580
// Lines 479–522
//
// Roman cohort info panel.  Bring in forumbit.pl8 from disk
// into scratch_buffer (60000 bytes), frame a 20x28 outer
// mosaic at (0x10, 0x30) with an 18x26 inner blank, exit
// button at (0x1A4, 0x144), then paint:
//
//   * General sprite (army_list[+0x28] + 0x21) at (0x190,
//     0x44).
//   * General portrait (people_data, image 18) at (0x190,
//     0x56).
//   * General name string (font2, string 5, word
//     army_list[+0x28]) at (0x38, 0x4A).
//   * "Founded" + show_date(army_list[+0x3A], 0x52, 0x40+x_is,
//     1).
//   * Three icon dias rows for veterans / casualties /
//     reinforcements.  Each row has show_a_32_block at
//     (0x12B, y+1) keyed on (0x35..0x37 for icons), a
//     left-aligned label (font_list 0x2D word 1/3/5) and a
//     right-aligned label (word 2/4/6) at (0x12A, ..) /
//     (0x13A, ..).
//   * show_tribunes_report row at y = 0x30, width 0x86.
//   * update_tribune_flag(0).
//   * Status string keyed on army_list[+0x12] / army_list[+0xA0]:
//       - +0x12 == 0xA (auto-fight) → word 0x1D
//       - +0xA0 == 0 (idle)         → word 0x1E
//       - +0xA0 == 1 (advancing)    → word 0x25
//       - +0xA0 == 2 (defending)    → word 0x26
//     Drawn from string 0x23.
void show_cohort_box(void)
{
    int auto_fight;

    fill_cohort_centuries();
    readfile("forumbit.pl8", ((void *)scratch_buffer), 0xea60, 0);

    stone_random_count = 0xf;
    show_a_mosaic_frame(0x10, 0x30, 0x1c, 0x14);
    show_a_mosaic_blank(0x20, 0x40, 0x1a, 0x12);
    show_an_exit_button(0x1a4, 0x144);

    write_general_sprite(army_list[tracking_army].cohort_id + 0x21,
                         0x190, 0x44);
    write_image(people_data, 0x12, 0x190, 0x56);

    x_is = 0;
    font_list(5,
              army_list[tracking_army].cohort_id,
              0x38, 0x4a, font2, 0x10);
    font_list(0x2d, 0, x_is + 0x40, 0x52, font1, 0x10);
    show_date(army_list[tracking_army].departure_year,
              x_is + 0x40, 0x52, 1);

    draw_a_dias(0x28, 0x7e, 0x190, 0xa0);
    draw_a_dias(0x28, 0x12a, 0x22, 0x22);
    show_a_32_block(0x29, 0x12b, 0x35);
    font_list(0x2d, 1, 0x50, 0x12a, font1, 0x10);
    font_list(0x2d, 2, 0x50, 0x13a, font1, 0x10);

    draw_a_dias(0xb8, 0x12a, 0x22, 0x22);
    show_a_32_block(0xb9, 0x12b, 0x36);
    font_list(0x2d, 3, 0xe0, 0x12a, font1, 0x10);
    font_list(0x2d, 4, 0xe0, 0x13a, font1, 0x10);

    draw_a_dias(0x148, 0x12a, 0x22, 0x22);
    show_a_32_block(0x149, 0x12b, 0x37);
    font_list(0x2d, 5, 0x170, 0x12a, font1, 0x10);
    font_list(0x2d, 6, 0x170, 0x13a, font1, 0x10);

    show_tribunes_report(tracking_army, 0x30, 0x86, 0);
    update_tribune_flag(0);

    auto_fight = army_list[tracking_army].state_idx;
    if (auto_fight == 0xa) {
        font_list(0x23, 0x1d, 0x120, 0x8a, font1, 0x10);
    } else {
        if      (army_list[tracking_army].cohort_size_class == 0) font_list(0x23, 0x1e, 0x120, 0x8a, font1, 0x10);
        else if (army_list[tracking_army].cohort_size_class == 1) font_list(0x23, 0x25, 0x120, 0x8a, font1, 0x10);
        else if (army_list[tracking_army].cohort_size_class == 2) font_list(0x23, 0x26, 0x120, 0x8a, font1, 0x10);
    }

    setup_map_screen_refresh();
}

// FUNCTION: C2 0x5C4E8
// WIN: 0x00423934
// Lines 524–549
//
// Non-cohort army (barbarian / civilian) info panel.  Frames
// an 8x22 mosaic window at (0x50, 0xF0) with an exit button
// in the corner.  Heading at (0x78, 0x10E) is the army-kind
// label (string 0x2D word 0x19..0x1D keyed on army.type 1..7).
//
// For barbarian (type == 6): show neighbour-province label
// (string 0x2D word 0x1E) + neighbour index (army_list[+0x99]
// + 1) on row 0x138; then show "borders" label (string 0x2D
// word 0x1F) + the bordering province name resolved through
// region_borders[province_is*4 + army_list[+0x98]/2] + 1.
//
// For other non-cohort types: army_list[+0x8A] is the
// reinforcement count (font_no'd at row 0x138) and
// army_list[+0x9B] is the source-region label (font_list word 7,
// string 0x2D, at row 0x138).
void show_non_cohort_box(void)
{
    int type;

    stone_random_count = 0xf;
    show_a_mosaic_window(0x50, 0xf0, 0x16, 8);
    show_an_exit_button(0x184, 0x144);

    type = army_list[tracking_army].type;
    if      (type <= 2) font_list(0x2d, 0x19, 0x78, 0x10e, font2, 0x10);
    else if (type <= 5) font_list(0x2d, 0x1a, 0x78, 0x10e, font2, 0x10);
    else if (type <= 6) font_list(0x2d, 0x1b, 0x78, 0x10e, font2, 0x10);
    else if (type <= 7) font_list(0x2d, 0x1c, 0x78, 0x10e, font2, 0x10);
    else                font_list(0x2d, 0x1d, 0x78, 0x10e, font2, 0x10);

    if (army_list[tracking_army].type == 6) {
        x_is = 0;
        font_list(0x2d, 0x1e, 0x78, 0x138, font1, 0x10);
        font_list(0x10,
                  army_list[tracking_army].trader_brings + 1,
                  x_is + 0x78, 0x138, font1, 0x10);
        font_list(0x2d, 0x1f, x_is + 0x78, 0x138, font1, 0x10);
        font_list(6,
                  region_borders[province_is].u.dir[
                      army_list[tracking_army].compass_side / 2] + 1,
                  0x78, 0x148, font1, 0x10);
    } else {
        x_is = 0;
        font_no(army_list[tracking_army].total_troops,
                0x20, " ", 0x78, 0x138, font1, 0x10);
        font_list(7,
                  army_list[tracking_army].source_region,
                  x_is + 0x78, 0x138, font1, 0x10);
    }
}

// FUNCTION: C2 0x5C71B
// WIN: 0x00423bef
// Lines 551–609
//
// Render the tribunes-report panel into a 0x15x9 strip
// anchored at (x, y).  `mode` (param 4) is 0 for the
// stationary view (large parade sprites, +0x2B/+0x30/+0x35/
// +0x2E base sprite indices) and non-zero for the moving
// view (small sprites, +0xA/+0xF/+0x14/+0xD).
//
// Layout:
//   1. Mosaic blank + label string (0x2D word 7).
//   2. 0x3E×0x3E dias frame for the cohort grid + a
//      show_cohort_landfill ground tile.
//   3. Four loops over the 14 centuries.  Each iteration
//      checks army_list[+0x3E + i*4] == cohort_type (1..4),
//      and on a hit draws write_general_sprite at
//      (x + esi, y + 0x14) with sprite =
//      sprite_table[type] + army_list[+0x3F + i*4].
//      esi advances by cohort_drill_spacing[army_list[+0x92]]
//      per drawn cohort.  esi is NOT reset between the four
//      type loops -- the parade row accumulates left to right
//      (the old per-loop esi = 0x44 reset was a semantic bug).
void show_tribunes_report(int army_idx, int x, int y, int mode)
{
    int esi;
    int drill_step;
    int i;

    stone_random_count = 0xf;
    show_a_mosaic_blank(x, y, 0x15, 9);
    font_list(0x2d, 7, x, y, font1, 0x10);

    draw_a_dias(x, y + 0x10, 0x3e, 0x3e);
    show_cohort_landfill(army_idx, x + 1, y + 0x11);

    esi = 0x44;
    drill_step = cohort_drill_spacing[army_list[army_idx].num_centuries];

    for (i = 0; i < 14; i++) {
        if (army_list[army_idx].centuries[i].type == 1) {
            if (mode == 0) write_general_sprite(army_list[army_idx].centuries[i].damaged + 0x2b, x + esi, y + 0x14);
            else write_general_sprite(army_list[army_idx].centuries[i].damaged + 0xa, x + esi, y + 0x14);
            esi += drill_step;
        }
    }
    for (i = 0; i < 14; i++) {
        if (army_list[army_idx].centuries[i].type == 2) {
            if (mode == 0) write_general_sprite(army_list[army_idx].centuries[i].damaged + 0x30, x + esi, y + 0x14);
            else write_general_sprite(army_list[army_idx].centuries[i].damaged + 0xf, x + esi, y + 0x14);
            esi += drill_step;
        }
    }
    for (i = 0; i < 14; i++) {
        if (army_list[army_idx].centuries[i].type == 3) {
            if (mode == 0) write_general_sprite(army_list[army_idx].centuries[i].damaged + 0x35, x + esi, y + 0x14);
            else write_general_sprite(army_list[army_idx].centuries[i].damaged + 0x14, x + esi, y + 0x14);
            esi += drill_step;
        }
    }
    for (i = 0; i < 14; i++) {
        if (army_list[army_idx].centuries[i].type == 4) {
            if (mode == 0) write_general_sprite(army_list[army_idx].centuries[i].damaged + 0x2e, x + esi, y + 0x14);
            else write_general_sprite(army_list[army_idx].centuries[i].damaged + 0xd, x + esi, y + 0x14);
            esi += drill_step;
        }
    }

    x_is = 0;
    font_list(0x2d, 8, x, y + 0x52, font1, 0x10);
    font_no(army_list[army_idx].total_troops, 0x20, " ",
            x_is + x, y + 0x52, font1, 0x10);
    font_list(0x2d, 9, x_is + x, y + 0x52, font1, 0x10);

    x_is = 0;
    font_no(army_list[army_idx].num_regulars, 0x20, "", x, y + 0x62, font1, 0x10);
    font_list(0x2d, 0x15, x_is + x, y + 0x62, font1, 0x10);
    font_no(army_list[army_idx].num_irregulars, 0x20, "",
            x_is + x, y + 0x62, font1, 0x10);
    font_list(0x2d, 0x16, x_is + x, y + 0x62, font1, 0x10);
    font_no(army_list[army_idx].num_auxillaries, 0x20, "",
            x_is + x, y + 0x62, font1, 0x10);
    font_list(0x2d, 0x17, x_is + x, y + 0x62, font1, 0x10);
    font_no(army_list[army_idx].num_specials, 0x20, "",
            x_is + x, y + 0x62, font1, 0x10);
    font_list(0x2d, 0x18, x_is + x, y + 0x62, font1, 0x10);

    font_list(0x2d, army_list[army_idx].morale + 0xb, x, y + 0x72, font1, 0x10);

    x_is = 0;
    font_list(0x2d, army_list[army_idx].readiness_level + 0x10, x, y + 0x82, font1, 0x10);
    if (army_list[army_idx].readiness_level == 0 && army_list[army_idx].morale_timer != 0) font_list(0x2d, 0xa, x_is + x, y + 0x82, font1, 0x10);
}


// FUNCTION: C2 0x5CB50
// WIN: 0x00424275
// Lines 611–616
//
// Bring up the "choose your starting region" dialog: black
// out the screen, load the empire palette + parts pl8, paint
// the box body via reshow_initreg_box, then push the new
// frame and palette to SVGA.
void show_initreg_box(void)
{
    /* Optimized out of the body; preserves PS's one-byte empty literal
       between the forumbit.pl8 and empire.256 CONST runs. */
    char *unused_padding;

    unused_padding = "";
    black_out();
    readfile("empire.256", temp_palette, 0x300, 0);
    readfile("e_parts2.pl8", ((void *)scratch_buffer), 0x249f0, 0);
    reshow_initreg_box();
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5CB8F
// WIN: 0x004242ef
// Lines 621–629
//
// Re-paint the initial-region selection screen body without
// the title bar.  Loads empire.pl8, calls the four sub-
// renderers (region list, offer panel, top + bottom slabs),
// schedules a refresh, then draws the 0x30 caption with
// font1 colour 0x3f.  Tail-jmps into show_skill1_box's last
// font_list call (+0xC0) — from there the rest of the body
// is shared.
void reshow_initreg_box(void)
{
    show_pl8file("empire.pl8", 0x1e0);
    show_regions_in_empire();
    show_regions_on_offer();
    show_empire_top_slab();
    show_empire_bottom_slab();
    setup_whole_screen_refresh();
    font_list(0x30, 0, 0xd2, 0x19e, font1, 0x3f);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5CBD7
// WIN: 0x00424359
// Lines 633–641
//
// "No provinces yet" notification box.  Sets stone_random_count
// to 15 (gives the mosaic a stable RNG seed), draws a frame +
// blank inner panel, the title strip, a wrapped paragraph via
// font_format_split, and an exit/OK hint.  Tail-merges into
// show_about_box's shared 11-byte epilogue.
void show_no_provinces_box(void)
{
    stone_random_count = 0xf;
    show_a_mosaic_frame(0x90, 0x90, 0x16, 0xc);
    show_a_mosaic_blank(0xa0, 0xa0, 0x14, 0xa);
    font_list(0x4e, 1, 0xc0, 0xb0, font2, 0x10);
    font_format_split(0x4e, 2, 0xb0, 0xd0, 0x120, 0x64, 0, 0,
                      font1, 0x10);
    font_list(9, 1, 0x100, 0x130, font1, 0x10);
    setup_whole_screen_refresh();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5CC82
// WIN: 0x00424400
// Lines 645–651
//
// "First region" greeting box.  Identical structure to
// show_no_provinces_box (same mosaic frame + blank panel +
// title strip + paragraph layout) but with string ID 0x30
// ("first region acquired") instead of 0x4e ("no provinces
// yet").  Tail-merges into show_no_provinces_box at the
// `call font_format_split` instruction (+0x7C inside
// show_no_provinces_box) — from there the bytes are
// identical, so PS just emits a `jmp` and shares the rest.
void show_first_region_box(void)
{
    stone_random_count = 0xf;
    show_a_mosaic_frame(0x90, 0x90, 0x16, 0xc);
    show_a_mosaic_blank(0xa0, 0xa0, 0x14, 0xa);
    font_list(0x30, 1, 0xc0, 0xb0, font2, 0x10);
    font_format_split(0x30, 2, 0xb0, 0xd0, 0x120, 0x64, 0, 0,
                      font1, 0x10);
    font_list(9, 1, 0x100, 0x130, font1, 0x10);
    setup_whole_screen_refresh();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5CD03
// WIN: 0x004244a7
// Lines 657–704
//
// "This region" info dialog.  Mode (p1) selects the outer
// frame height: 0x10 when p1 == 0 (full info with confirm
// buttons), 0xE when p1 != 0 (compact view with single label).
// Frame at (0x70, 0x80) 0x1A x edi; inner blank at
// (0x80, 0x90) 0x18 x (edi-2).  Title at (0x90, 0x9C) is the
// region name (font2 string 6 word region_over).
//
// Body keyed on empire_won[region_over - 1]:
//   * 0       → either "this is your home province" (word 6
//                of string 0x4D) when region_over-1 ==
//                province_is, or string 0x30 word 9.
//   * 99998   → string 0x30 word 5.
//   * 99999   → string 0x30 word 6.
//   * other N → "conquered N years ago" via string 0x30
//                word 7 + font_no(N) + word 8.
//
// After the body: this_help_page = region_over + 0x47C;
// load_media_entry; text_pointer set to its standard scratch
// slot.  Then either two confirm buttons (p1 == 0) or a
// single "close" label (p1 != 0).
void this_region_box(int p1)
{
    int show_media;
    int box_height;
    int r;

    if ((p1) == 0)
        box_height = 0x10;
    else
        box_height = 0xe;
    show_media = 1;

    cover_mouse_droppings();
    hold_mouse_replace = 1;
    stone_random_count = 0x11;
    show_a_mosaic_frame(0x70, 0x80, 0x1a, box_height);
    show_a_mosaic_blank(0x80, 0x90, 0x18, box_height - 2);

    font_list(6, region_over, 0x90, 0x9c, font2, 0x10);

    r = region_over; if (empire_won[r - 1] == 0) {
        if (r - show_media == province_is) {
            font_list(0x4d, 6, 0x90, 0xc0, font1, 0x10);
            show_media = 0;
        } else {
            font_list(0x30, 9, 0x90, 0xc0, font1, 0x10);
        }
    } else if (empire_won[region_over - 1] == 0x1869e) {
        font_list(0x30, 5, 0x90, 0xc0, font1, 0x10);
    } else if (empire_won[region_over - 1] == 0x1869f) {
        font_list(0x30, 6, 0x90, 0xc0, font1, 0x10);
        show_media = 0;
    } else {
        x_is = 0;
        font_list(0x30, 7, 0x90, 0xc0, font1, 0x10);
        font_no(empire_won[region_over - 1], 0x20, " ",
                x_is + 0x90, 0xc0, font1, 0x10);
        font_list(0x30, 8, x_is + 0x90, 0xc0, font1, 0x10);
        show_media = 0;
    }

    this_help_page = region_over + 0x47c;
    load_media_entry();
    text_pointer = format_buffer;
    if (region_over != 1 && show_media != 0) {
        media_text_place(0x90, 0xe0, 0x160, 0x64, 0, 0, font1);
        play_speech(region_over + 0x3a);
    }

    if ((p1) == 0) {
        font_list(0x30, 3, 0xe0, 0x14c, font1, 0x10);
        show_buttons(0x170, 0x110, confirming_buttons, 2);
    } else {
        font_list(9, 1, 0x100, 0x13c, font1, 0x10);
    }
    setup_whole_screen_refresh();
}

// FUNCTION: C2 0x5CF71
// WIN: 0x00424785
// Lines 707–717
//
// First-skill (army-tactic primer) info box.  Cover the mouse,
// re-paper the background, draw a 0x1e×0x14 system window
// at (0x50, 0x50), schedule a full-screen refresh, then five
// font_list paragraphs (string 0x2b: header word at top,
// followed by 4 wrapped paragraphs of 0xd / 0xc / 0xb / 0xf
// words at fixed y positions).  Tail-merges into
// show_about_box's shared 11-byte epilogue at +0xA2
// (hold_mouse_replace = 1; pop; ret).
void show_skill1_box(void)
{
    cover_mouse_droppings();
    background_screen();
    show_a_system_window(0x50, 0x50, 0x1e, 0x14);
    setup_whole_screen_refresh();
    font_list(0x2b, 0, 0x70, 0x68, font2, 0x10);
    font_list(0x2b, 0xd, 0x9a, 0xbe, font1, 0x10);
    font_list(0x2b, 0xc, 0x9a, 0xee, font1, 0x10);
    font_list(0x2b, 0xb, 0x9a, 0x11e, font1, 0x10);
    font_list(0x2b, 0xf, 0x9a, 0x14e, font1, 0x10);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5D03B
// WIN: 0x0042483c
// Lines 722–733
//
// Second-skill (army-tactic detail) info box.  Same shell as
// show_skill1_box (same window geometry, system_window vs
// mosaic_window selection), but with three font_list lines
// of different content + three child renderers
// (show_skill_level / show_peace_level / show_name_choice).
// Tail-merges into show_about_box's shared 11-byte epilogue.
void show_skill2_box(void)
{
    cover_mouse_droppings();
    background_screen();
    show_a_system_window(0x50, 0x50, 0x1e, 0x16);
    setup_whole_screen_refresh();
    font_list(0x2b, 0x10, 0x70, 0x68, font2, 0x10);
    font_list(0x2b, 0x11, 0x6a, 0x156, font1, 0x10);
    font_list(0x2b, 0x12, 0x6a, 0x186, font1, 0x10);
    show_skill_level();
    show_peace_level();
    show_name_choice();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5D0D7
// WIN: 0x004248c2
// Lines 738–794
//
// Display one of four settings sub-pages in a mosaic window:
//   p1 == 0 → music settings (height 7).  Music on/off toggle
//             (c2inf+0xD) and the music volume
//             (c2inf+0x12) value.
//   p1 == 1 → audio + autosave settings (height 0xD).  Four
//             on/off rows (sound c2inf+0xC, speech c2inf+0x3A,
//             autosave c2inf+0x3), the sound volume
//             (c2inf+0xE) value and an autosave interval
//             label (c2inf+0x3C).
//   p1 == 2 → difficulty (height 5).  Single-row label keyed on
//             c2inf+0x19 (difficulty level 2..3).
//   p1 == 3 → tutorial setup (height 7).  Two on/off rows
//             (autopause c2inf+0x39, tutorial c2inf+0x3B).
// Bottom OK button: font_list(9, 1, 0x90, edi * 0x10 + 0x68,
// font1, 0x10).  Tail-merge to the 0x5F73D pop-edi/.../ret
// epilogue.
void show_fx_box(int p1)
{
    int edi;

    if      (p1 == 0) edi = 7;
    else if (p1 == 1) edi = 0xd;
    else if (p1 == 2) edi = 5;
    else if (p1 == 3) edi = 7;

    show_a_mosaic_window(0x40, 0x70, 0x13, edi + 2);
    setup_whole_screen_refresh();

    if (p1 == 0) {
        font_list(0x39, 0, 0x60, 0x98, font1, 0x10);
        if (c2inf.tunes_on != 0)
            font_list(0x39, 3, 0xf0, 0x98, font1, 0x10);
        else
            font_list(0x39, 2, 0xf0, 0x98, font1, 0x10);
        font_list(0x39, 4, 0x60, 0xb8, font1, 0x10);
        font_no(c2inf.tunes_level, 0x20, "%",
                0xf0, 0xb8, font1, 0x10);
    } else if (p1 == 1) {
        font_list(0x39, 1, 0x60, 0x98, font1, 0x10);
        if (c2inf.samples_on != 0)
            font_list(0x39, 3, 0xf0, 0x98, font1, 0x10);
        else
            font_list(0x39, 2, 0xf0, 0x98, font1, 0x10);
        font_list(0x39, 7, 0x60, 0xb8, font1, 0x10);
        if (c2inf.ambients_on != 0)
            font_list(0x39, 3, 0xf0, 0xb8, font1, 0x10);
        else
            font_list(0x39, 2, 0xf0, 0xb8, font1, 0x10);
        font_list(0x39, 8, 0x60, 0xd8, font1, 0x10);
        if (c2inf.speech_on != 0)
            font_list(0x39, 3, 0xf0, 0xd8, font1, 0x10);
        else
            font_list(0x39, 2, 0xf0, 0xd8, font1, 0x10);
        font_list(0x39, 4, 0x60, 0xf8, font1, 0x10);
        font_no(c2inf.samples_level, 0x20, "%",
                0xf0, 0xf8, font1, 0x10);
        font_list(0x4e, 3, 0x60, 0x118, font1, 0x10);
        font_no(c2inf.max_samples, 0x20, " ",
                0xf0, 0x118, font1, 0x10);
    } else if (p1 == 2) {
        font_list(0x39, 5, 0x60, 0x98, font1, 0x10);
        if (c2inf.anims_on != 0)
            font_list(0x39, 3, 0xf0, 0x98, font1, 0x10);
        else
            font_list(0x39, p1, 0xf0, 0x98, font1, 0x10);
    } else if (p1 == 3) {
        font_list(0x39, 6, 0x60, 0x98, font1, 0x10);
        if (c2inf.yearend_on != 0)
            font_list(0x39, p1, 0xf0, 0x98, font1, 0x10);
        else
            font_list(0x39, 2, 0xf0, 0x98, font1, 0x10);
        font_list(0x39, 9, 0x60, 0xb8, font1, 0x10);
        if (c2inf.autosave_on != 0)
            font_list(0x39, 3, 0xf0, 0xb8, font1, 0x10);
        else
            font_list(0x39, 2, 0xf0, 0xb8, font1, 0x10);
    }

    font_list(9, 1, 0x90, edi * 0x10 + 0x68, font1, 0x10);
    setup_whole_screen_refresh();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5D4D4
// WIN: 0x00424d30
// Lines 797–806
//
// Renders the in-game "About" box: a 0x14×0xa mosaic window
// at (0x80, 0x40), three lines of caption text (string IDs
// 0xb, 0x3b, 9) using font1 in colour 0x10, the Impressions
// logo image at (0x150, 0x78), and an exit button at (0x194,
// 0xb4).  Then schedules a full-screen refresh and raises the
// mouse-replace hold flag (the shared epilogue starting at
// +0xA2 that 5 sister box screens tail-jmp into).
void show_about_box(void)
{
    show_a_mosaic_window(0x80, 0x40, 0x14, 0xa);
    font_list(0xb, 0, 0xa0, 0x58, font1, 0x10);
    font_list(0x3b, 0, 0xa0, 0x68, font1, 0x10);
    write_image(logos, 0, 0x150, 0x78);
    font_list(9, 1, 0xc0, 0xc0, font1, 0x10);
    show_an_exit_button(0x194, 0xb4);
    setup_whole_screen_refresh();
    refresh_svga_screen();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5D581
// WIN: 0x00424dd3
// Lines 810–816
//
// New-Game name-prompt panel.  3-row blank at (0x60, 0x110)
// with the "Enter your name:" label (text 0x2b/0xa) on the
// left and the player's current name (`c2inf.player_name`)
// on the right.
void show_name_choice(void)
{
    show_a_system_blank(0x60, 0x110, 0x1c, 3);
    font_list(0x2b, 0xa, 0x6a, 0x126, font1, 0x10);
    put_a_font_string(c2inf.player_name, 0x140, 0x126, font1, 0x10);
}

// FUNCTION: C2 0x5D5DC
// WIN: 0x00424e2d
// Lines 818–824
//
// Peace-mode toggle panel.  3-row blank at (0x60, 0xe0).
// Renders the "Peace mode:" label (text 0x2b/7) on the
// left and the on/off label (text 0x2b/(8 + peace_mode))
// on the right, then refreshes the same rect.
//
// Tail-merges into show_donation_level's epilogue at +0x8a
void show_peace_level(void)
{
    show_a_system_blank(0x60, 0xe0, 0x1c, 3);
    font_list(0x2b, 7, 0x6a, 0xf6, font1, 0x10);
    font_list(0x2b, (signed char)c2inf.peace_mode + 8, 0x140, 0xf6, font1, 0x10);
    setup_refresh_area(0x60, 0xe0, 0x1c, 3, 1);
}

// FUNCTION: C2 0x5D658
// WIN: 0x00424e8b
// Lines 827–835
//
// Render the skill-level selector subpanel in the options/about UI.
// Shows a blank system slab, an outline box, label text, the current
// skill label, an explanatory paragraph, then refreshes the slab.
void show_skill_level(void)
{
    show_a_system_blank(0x60, 0x90, 0x1c, 5);
    draw_a_box(0x68, 0xc0, 0x1b4, 0x1c, 0x10);
    font_list(0x2b, 1, 0x6a, 0xa8, font1, 0x10);
    font_list(0x2c, c2inf.skill_level, 0x160, 0xa2, font2, 0x10);
    font_list(0x2b, c2inf.skill_level + 2, 0x70, 0xc8, font1, 0x10);
    setup_refresh_area(0x60, 0x90, 0x1c, 6, 1);
}

// FUNCTION: C2 0x5D70C
// WIN: 0x00424f21
// Lines 838–844
//
// Render the "enter new player name" dialog box.  Layout:
//   * 17×5-cell system window centred at (0xd0, 0xd0)
//   * Current player name as the editable string at (0xe2, 0xe0)
//   * Paragraph string 0x2b ("Type your name and press ENTER")
//     at (0xe0, 0x100), 14 words wide.
//
// Tail-merges into the same 'font_list ; hold_mouse_replace = 1'
// epilogue used by every other system-dialog box renderer.
void show_new_name_box(void)
{
    cover_mouse_droppings();
    show_a_system_window(0xd0, 0xd0, 0x11, 5);
    setup_whole_screen_refresh();
    put_a_font_string(c2inf.player_name, 0xe2, 0xe0, font1, 0x10);
    font_list(0x2b, 0xe, 0xe0, 0x100, font1, 0x10);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5D765
// WIN: 0x00424f8d
// Lines 848–855
//
// Fixed exit confirmation panel: 14x9 system window centered at
// (0x80, 0xa0), followed by three text lines (paragraph 0x4d, entries
// 9..11).
void show_exit_box(void)
{
    cover_mouse_droppings();
    show_a_system_window(0x80, 0xa0, 0xe, 9);
    setup_whole_screen_refresh();
    font_list(0x4d, 9, 0x90, 0xb8, font1, 0x10);
    font_list(0x4d, 0xa, 0x90, 0xe0, font1, 0x10);
    font_list(0x4d, 0xb, 0x90, 0x108, font1, 0x10);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5D7EB
// WIN: 0x00425011
// Lines 859–871
//
// Draw the shared load/save file-picker frame.  The caller supplies
// the title string id; the directory list is populated separately by
// show_directory(999).
void show_loadsave_box(int title_id)
{
    cover_mouse_droppings();
    show_a_system_window(0x20, 0x50, 0x19, 0x14);
    setup_whole_screen_refresh();
    font_list(title_id, 0, 0x30, 0x60, font2, 0x10);
    draw_a_box(0x30, 0x88, 0x170, 0x100, 0x10);
    draw_a_box(0x38, 0x90, 0xc0, 0x20, 0x10);
    draw_a_box(0x38, 0xb8, 0x140, 0xa4, 0x10);
    draw_a_box(0x38, 0x164, 0x160, 0x1c, 0x10);
    show_directory(999);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5D8B0
// WIN: 0x004250c4
// Lines 873–902
//
// Render the save-file directory picker.  Reset cursor state,
// draw two stacked header strips, stamp the active filename
// with a follow-up text cursor, then paint a 19-row entry box.
// Entries 0..9 sit in the left column (x = 0x40), entries
// 10..19 in the right column (x = 0xE0); rows step by 0x10.
// Each entry is `directory[idx * 13]` (13-byte name slots).
// The currently selected entry (== scroll_top, i.e. the first
// argument) gets a 9x15 highlight rectangle in colour 0x10
// behind it and the text is drawn in 0x20 instead of 0x10.
void show_directory(int scroll_top)
{
    int x;
    int y;
    int entry;
    int row;

    got_cursx     = 0;
    cursor_x      = 0;
    fb_count      = 0;
    cursor_y      = 0x98;
    allow_padding = 1;
    x_is          = 0;

    show_a_system_blank(0x3c, 0x92, 0xa, 1);
    show_a_system_blank(0x3c, 0x9c, 0xa, 1);
    put_a_font_string(filename, 0x40, 0x98, font1, 0x10);
    if (got_cursx == 0) {
        cursor_x  = x_is;
        got_cursx = 1;
    }
    cursor_x += 0x40;
    show_cursor(font1);

    x = 0x40;
    y = 0xbc;
    show_a_system_blank(0x3e, 0xba, 0x13, 0xa);

    entry = first_entry;
    row = 0;
    goto check_entries;
    for (;;) {
        char *name;
        name = directory[entry];
        if (entry == scroll_top) {
            sprite_width  = 9;
            sprite_height = 0xf;
            show_fast_rect(x - 2, y - 2, 0x10);
            put_a_font_string(name, x, y, font1, 0x20);
        } else {
            put_a_font_string(name, x, y, font1, 0x10);
        }
        if (row == 9) {
            x = 0xe0;
            y = 0xbc;
        } else {
            y += 0x10;
        }
        if (row >= 0x13) break;
        entry++;
        row++;
check_entries:
        if (entry >= no_of_entries) break;
    }
}

// FUNCTION: C2 0x5DA18
// WIN: 0x00425294
// Lines 908–916
//
// One-time forum scene loader.  Black-out, then read the
// forum's static assets into scratch_buffer (forumbit.pl8
// for the bitmap pieces, forum_x.gd8 for the geometry data
// at +0x1d4c0), the palette (forum.256 → temp_palette),
// the background image (forum.pl8 → normal show_pl8file),
// then run forum_explanations(i, 0) for i in 0..11 to seed
// the explanation strings.  Tail-merges into show_about_box's
// shared 11-byte epilogue.
void forum_constant_screen(void)
{
    int i;

    black_out();
    readfile("forumbit.pl8", ((void *)scratch_buffer), 0xea60, 0);
    readfile("forum_x.gd8", ((void *)((scratch_buffer) + (0x1d4c0))),
             0xfa0, 0);
    readfile("forum.256", temp_palette, 0x300, 0);
    show_pl8file("forum.pl8", 0x1e0);
    for (i = 0; i < 0xc; i++) {
        forum_explanations(i, 0);
    }
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5DA8F
// WIN: 0x0042533e
// Lines 920–926
//
// Plain background screen used as a quiet curtain between
// scenes (title → forum, splash → menu): black out, load the
// background palette + pl8, refresh, push the palette, and
// raise hold_mouse_replace.
void background_screen(void)
{
    black_out();
    readfile("backgrnd.256", temp_palette, 0x300, 0);
    show_pl8file("backgrnd.pl8", 0x1e0);
    setup_whole_screen_refresh();
    refresh_svga_screen();
    set_palette(temp_palette);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x5DAC6
// WIN: 0x00425395
// Lines 932–943
//
// "Empty" forum screen — no department highlighted: paint the
// generic forum panel and run forum_explanations() over all 12
// slots in non-highlight mode, then push the new frame and
// palette to SVGA and raise hold_mouse_replace.
void forum_empty_screen(void)
{
    int i;

    cover_mouse_droppings();
    setup_whole_screen_refresh();
    show_pl8file("forum.pl8", 0x1e0);
    for (i = 0; i < 12; i++) {
        forum_explanations(i, 0);
    }
    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5DB0B
// WIN: 0x004253ff
// Lines 945–956
//
// Render the "city-only" forum advisor screen: cover any
// stale mouse trail, mark the whole screen for refresh,
// re-paper the chosen department panel if its forum_repapering
// flag is set, then explain_forum() to draw the dept text.
// Frame the panel with a mosaic window, clear x_is, draw the
// two header strings via font_list, raise the mouse-replace
// hold flag, and finally push the new frame and palette to SVGA.
void forum_city_only_screen(void)
{
    cover_mouse_droppings();
    setup_whole_screen_refresh();
    if (forum_repapering[last_forum_dept] != 0) {
        show_pl8file("forum.pl8", forum_repapering[last_forum_dept]);
    }
    explain_forum();
    stone_random_count = 0x14;
    show_a_mosaic_window(0, 0, 0x28, 0xb);
    x_is = 0;
    font_list(0x27, 0, 0x64, 0x38, font2, 0x10);
    font_list(0x27, 1, 0x8c, 0x6a, font1, 0x10);
    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5DBB4
// WIN: 0x004254b0
// Lines 961–992
//
// The forum admin panel: explain backdrop, title strip, treasury
// (denarii, with " Dn" suffix and negative-aware formatting),
// population, employment rate, two dotted separator lines, and the
// admin button strip.  Then chains the three sub-panels
// show_tax_rates / show_accounts / show_estimate.  Tail-merges into
// the shared epilogue at 0x5f73d.
void forum_admin_screen(void)
{
    cover_mouse_droppings();
    setup_whole_screen_refresh();

    if (forum_repapering[last_forum_dept] != 0) {
        show_pl8file("forum.pl8",
                     forum_repapering[last_forum_dept]);
    }

    explain_forum();
    show_a_mosaic_frame(0, 0, 0x28, 0xc);
    stone_random_count = 0xa;
    show_a_mosaic_blank(0x10, 0x10, 0x26, 0xa);

    x_is = 0;
    font_list(0x1e, 0, 0x18, 0x12, font2, 0x10);

    if (denarii < 0) {
        font_no(-denarii, 0x2d, " Dn", x_is + 0x1c, 0x12, font2, 0xb);
    } else {
        font_no(denarii,  0x20, " Dn", x_is + 0x1c, 0x12, font2, 0x10);
    }

    x_is = 0;
    font_no(population,      0x20, " ", 0x18, 0x32, font1, 0x10);
    font_list(0x1e, 1, x_is + 0x18, 0x32, font1, 0x10);
    font_no(employment_rate, 0x20, "%", x_is + 0x18, 0x32, font1, 0x10);
    font_list(0x1e, 2, x_is + 0x18, 0x32, font1, 0x10);

    font_list(0x1e, 3, 0x108, 0x1a, font1, 0x10);
    font_list(0x1e, 4, 0x108, 0x32, font1, 0x10);

    draw_a_dotted_line(0x14, 0x46, 0x26a, 0x46, 0x10);
    draw_a_dotted_line(0x13f, 0x48, 0x13f, 0xac, 0x10);

    show_buttons(0x178, 0x12, admin_buttons, 4);

    show_tax_rates();
    show_accounts();
    show_estimate();

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5DDCD
// WIN: 0x004256cf
// Lines 995–1017
//
// Tax-rate panel.  Refresh the cached averages, then paint
// two stacked boxes:
//
//   1. Two right-justified percentages (population +
//      industry tax rates) at column 0x1B0 in a small box.
//   2. A wider box at column 0x1CE with a two-line label
//      ("Pop tax revenue" / "Ind tax revenue") and the
//      computed denarii + asses values formatted as
//      "NN Dn (M asses)".  The asses field uses a leading
//      space for single-digit values and zero-padding for
//      double-digit, so the parens line up.
void show_tax_rates(void)
{
    get_average_pop_tax();
    get_average_ind_tax();

    stone_random_count = 0x18;
    show_a_mosaic_blank(0x1a8, 0x12, 3, 3);
    font_no(pop_tax_rate, 0x20, "%",  0x1b0, 0x1a, font1, 0x10);
    font_no(ind_tax_rate, 0x20, "%",  0x1b0, 0x32, font1, 0x10);

    show_a_mosaic_blank(0x1ce, 0x12, 0xa, 3);
    x_is = 0;
    font_list(0x1e, 5, 0x1d8, 0x1a, font1, 0x10);
    font_no(average_pop_tax_denariis, 0x20, ".",
            x_is + 0x1d8, 0x1a, font1, 0x10);
    if (average_pop_tax_asses < 0xa) {
        font_no(average_pop_tax_asses, 0x30,
                "Dn )", x_is + 0x1d8, 0x1a, font1, 0x10);
    } else {
        font_no(average_pop_tax_asses, 0x20,
                "Dn )", x_is + 0x1d8, 0x1a, font1, 0x10);
    }
    x_is = 0;
    font_list(0x1e, 5, 0x1d8, 0x32, font1, 0x10);
    font_no(average_ind_tax_denariis, 0x20, ".",
            x_is + 0x1d8, 0x32, font1, 0x10);
    if (average_ind_tax_asses < 0xa) {
        font_no(average_ind_tax_asses, 0x30,
                "Dn )", x_is + 0x1d8, 0x32, font1, 0x10);
    } else {
        font_no(average_ind_tax_asses, 0x20,
                "Dn )", x_is + 0x1d8, 0x32, font1, 0x10);
    }

    setup_refresh_area(0x158, -14, 0x12, 6, 1);
}

// FUNCTION: C2 0x5DFA2
// WIN: 0x004258b9
// Lines 1020–1049
//
// Treasury detail panel.  Mosaic-blank a 6x18 column header
// at (0x10, 0x4A), stamp last year's date and the account
// total in white (positive) or red (negative) with the word
// label "surplus" / "deficit".  Then five ledger rows for
// pop tax / ind tax / construction / operating / tribute,
// each row being (paragraph 0x1E word N) + denarii column.
void show_accounts(void)
{
    stone_random_count = 4;
    show_a_mosaic_blank(0x10, 0x4a, 0x12, 6);
    show_date(year - 1, 0x18, 0x4c, 1);
    font_list(0x1e, 6, x_is + 0x18, 0x4c, font1, 0x10);

    if (account_total < 0) {
        font_no(-account_total, 0x20, " Dn", x_is + 0x18, 0x4c, font1, 0x10);
        font_list(0x1e, 8, x_is + 0x18, 0x4c, font1, 0x10);
    } else {
        font_no(account_total, 0x20, " Dn", x_is + 0x18, 0x4c, font1, 0x10);
        font_list(0x1e, 9, x_is + 0x18, 0x4c, font1, 0x10);
    }

    x_is = 0;
    font_list(0x1e, 0xa, 0x26, 0x5d, font1, 0x10);
    font_no(account_pop_tax, 0x20, " Dn", x_is + 0x26, 0x5e, font1, 0x10);
    font_list(0x1e, 0xc, 0x8c, 0x5e, font1, 0x10);

    x_is = 0;
    font_list(0x1e, 0xa, 0x26, 0x6e, font1, 0x10);
    font_no(account_ind_tax, 0x20, " Dn", x_is + 0x26, 0x6f, font1, 0x10);
    font_list(0x1e, 0xd, 0x8c, 0x6f, font1, 0x10);

    x_is = 0;
    font_list(0x1e, 0xb, 0x26, 0x7f, font1, 0x10);
    font_no(account_construction_cost, 0x20, " Dn",
            x_is + 0x26, 0x80, font1, 0x10);
    font_list(0x1e, 0xe, 0x8c, 0x80, font1, 0x10);

    x_is = 0;
    font_list(0x1e, 0xb, 0x26, 0x90, font1, 0x10);
    font_no(account_operating_cost, 0x20, " Dn",
            x_is + 0x26, 0x91, font1, 0x10);
    font_list(0x1e, 0xf, 0x8c, 0x91, font1, 0x10);

    x_is = 0;
    font_list(0x1e, 0xb, 0x26, 0xa1, font1, 0x10);
    font_no(account_tribute, 0x20, " Dn",
            x_is + 0x26, 0xa2, font1, 0x10);
    font_list(0x1e, 0x10, 0x8c, 0xa2, font1, 0x10);
}

// FUNCTION: C2 0x5E2BD
// WIN: 0x00425bae
// Lines 1051–1083
//
// Year-end estimate panel: same shape as show_accounts but
// rendered into the right-hand 6x18 column at (0x144, 0x4A)
// and reading from the cached `estimate_*` predictions
// (get_estimates is called first to refresh them).  Five rows
// (pop tax, ind tax, construction, operating, tribute) with
// the same surplus/deficit + Dn/asses formatting.
void show_estimate(void)
{
    get_estimates();
    stone_random_count = 0x11;
    show_a_mosaic_blank(0x144, 0x4a, 0x12, 6);
    show_date(year, 0x148, 0x4c, 1);
    font_list(0x1e, 7, x_is + 0x148, 0x4c, font1, 0x10);

    if (estimate_total < 0) {
        font_no(-estimate_total, 0x20, " Dn", x_is + 0x148, 0x4c, font1, 0x10);
        font_list(0x1e, 8, x_is + 0x148, 0x4c, font1, 0x10);
    } else {
        font_no(estimate_total, 0x20, " Dn", x_is + 0x148, 0x4c, font1, 0x10);
        font_list(0x1e, 9, x_is + 0x148, 0x4c, font1, 0x10);
    }

    x_is = 0;
    font_list(0x1e, 0xa, 0x154, 0x5d, font1, 0x10);
    font_no(estimate_pop_tax, 0x20, " Dn", x_is + 0x154, 0x5e, font1, 0x10);
    font_list(0x1e, 0xc, 0x1ba, 0x5e, font1, 0x10);

    x_is = 0;
    font_list(0x1e, 0xa, 0x154, 0x6e, font1, 0x10);
    font_no(estimate_ind_tax, 0x20, " Dn", x_is + 0x154, 0x6f, font1, 0x10);
    font_list(0x1e, 0xd, 0x1ba, 0x6f, font1, 0x10);

    x_is = 0;
    font_list(0x1e, 0xb, 0x154, 0x7f, font1, 0x10);
    font_no(estimate_construction_cost, 0x20, " Dn",
            x_is + 0x154, 0x80, font1, 0x10);
    font_list(0x1e, 0xe, 0x1ba, 0x80, font1, 0x10);

    x_is = 0;
    font_list(0x1e, 0xb, 0x154, 0x90, font1, 0x10);
    font_no(estimate_operating_cost, 0x20, " Dn",
            x_is + 0x154, 0x91, font1, 0x10);
    font_list(0x1e, 0xf, 0x1ba, 0x91, font1, 0x10);

    x_is = 0;
    font_list(0x1e, 0xb, 0x154, 0xa1, font1, 0x10);
    font_no(estimate_tribute, 0x20, " Dn",
            x_is + 0x154, 0xa2, font1, 0x10);
    font_list(0x1e, 0x10, 0x1ba, 0xa2, font1, 0x10);

    setup_refresh_area(0x140, 0x4c, 0x14, 9, 1);
}

// FUNCTION: C2 0x5E60D
// WIN: 0x00425ed0
// Lines 1086–1117
//
// Forum career panel: explain panel + outer mosaic + title row,
// the player's name (c2inf.player_name), the current rank label,
// and — only when not in peace mode AND player_rank < 0xa — the
// "N provinces remaining" line plus a hint row that switches at
// skill_level >= 2.  Finishes with show_personal_cash_stats and
// the bottom button strip.
void forum_career_screen(void)
{
    cover_mouse_droppings();
    setup_whole_screen_refresh();

    if (forum_repapering[last_forum_dept] != 0) {
        show_pl8file("forum.pl8",
                     forum_repapering[last_forum_dept]);
    }

    explain_forum();
    stone_random_count = 0x14;
    show_a_mosaic_frame(0, 0, 0x28, 0xb);
    show_a_mosaic_blank(0x10, 0x10, 0x26, 9);

    x_is = 0;
    font_list(0x1f, 0, 0x18, 0x1c, font2, 0x10);
    put_a_font_string(c2inf.player_name, x_is + 0x1c, 0x1c, font2, 0x10);
    font_list(8, player_rank, x_is + 0x20, 0x1c, font2, 0x10);

    if (c2inf.peace_mode == 0 && player_rank < 0xa) {
        x_is = 0;
        font_list(0x4d, 0x11, 0x18, 0x42, font1, 0x10);
        font_no((unsigned char)promotions_to_win_game[c2inf.skill_level]
                - completed_provinces,
                0x20, " ", x_is + 0x18, 0x42, font1, 0x10);

        font_list(0x4d, 0x12, x_is + 0x18, 0x42, font1, 0x10);

        if (c2inf.skill_level < 2) {
            font_list(0x4d, 0x14, x_is + 0x18, 0x42, font1, 0x10);
        } else {
            font_list(0x4d, 0x13, x_is + 0x18, 0x42, font1, 0x10);
        }
    }

    show_personal_cash_stats();
    show_buttons(0xe0, 0x58, career_buttons, 3);

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5E7F3
// WIN: 0x004260ba
// Lines 1119–1132
//
// Personal cash stats panel.  Shows the player's current denarii
// balance (red "-NNN" if negative, black " NNN" if positive)
// and yearly salary in a 12×4-cell blank-mosaic at (0x10,0x5c).
// Three label slots from string table 0x1f (lines 1, 2, 3) are
// drawn at the corresponding rows; numeric values follow each
// label at column x_is + offset (font_list updates x_is to the
// post-label cursor).  Refreshed via setup_refresh_area at
// (0x10,0x40)+0x11x6.
void show_personal_cash_stats(void)
{
    stone_random_count = 0x14;
    show_a_mosaic_blank(0x10, 0x5c, 0xc, 4);
    x_is = 0;
    font_list(0x1f, 1, 0x12c, 0x5e, font1, 0x10);
    if (players_denarii < 0) {
        font_no(-players_denarii, '-', " Dn", x_is + 0x12c, 0x5e, font1, 0xb);
    } else {
        font_no(players_denarii, ' ', " Dn", x_is + 0x12c, 0x5e, font1, 0x10);
    }
    x_is = 0;
    font_list(0x1f, 2, 0x14, 0x5e, font1, 0x10);
    font_no(players_salary, ' ', " Dn", x_is + 0x14, 0x5e, font1, 0x10);
    x_is = 0;
    font_list(0x1f, 3, 0x14, 0x7a, font1, 0x10);
    setup_refresh_area(0x10, 0x40, 0x11, 6, 1);
}

// FUNCTION: C2 0x5E91E
// WIN: 0x004261cf
// Lines 1135–1145
//
// Donation adjustment panel.  Blank/refresh screen, draw a
// 17x9 mosaic at (0xa0,0x20), render the current donation
// level, two labels, and an exit button.  Tail-merges into the
// standard `hold_mouse_replace=1; refresh_svga_screen` epilogue.
void show_donation_box(void)
{
    cover_mouse_droppings();
    setup_whole_screen_refresh();
    stone_random_count = 0x10;
    show_a_mosaic_window(0xa0, 0x20, 0x11, 9);
    show_donation_level();
    font_list(0x1f, 5, 0xc0, 0x5c, font1, 0x10);
    font_list(9, 1, 0xc0, 0x88, font1, 0x10);
    show_an_exit_button(0x180, 0x80);
    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5E9A4
// WIN: 0x00426260
// Lines 1152–1159
//
// Donation-level panel.  Two-row blank mosaic at (0xb0, 0x38)
// with the "Donation:" label (string table 0x1f, line 4)
// followed by the current donation_level formatted with
// " Dn" suffix.
void show_donation_level(void)
{
    stone_random_count = 0x10;
    show_a_mosaic_blank(0xb0, 0x38, 0xb, 2);
    x_is = 0;
    font_list(0x1f, 4, 0xc0, 0x40, font1, 0x10);
    font_no(donation_level, ' ', " Dn", x_is + 0xc0, 0x40, font1, 0x10);
    setup_refresh_area(0xb0, 0x30, 0xa, 3, 1);
}

// FUNCTION: C2 0x5EA37
// WIN: 0x004262d2
// Lines 1162–1212
//
// Rome (imperial relations) sub-screen of the forum.  Loads
// the per-department forum_repapering plate from forum.pl8
// when the player switched in from another department, then
// calls explain_forum to repaint the help text.
//
// Layout: outer 0xB-tall mosaic frame at (0, 0) 0x28 wide,
// inner 9-tall blank at (0x10, 0x10) 0x26 wide.  Title at
// (0x18, 0x1C) font2 string 0x26 word 0.
//
// Rows (all in string 0x26):
//   * Word 1 + favour label at y=0x40: favour bucket is
//     word 3 (imperial_favour <= 0), word 0xE (>= 0xC8),
//     else word (favour / 20 + 4).
//   * Word 2 + font_no(tribute) at y=0x50, suffixed " Dn.".
//   * Word 0x14 + (or 0x15 when imperial_req_amount > 0)
//     emperor's request row at y=0x60.  When non-zero:
//     amount + word 0xF + word 0x10 (request goods).
//   * dias at (0x1C, 0x76) 0x248 x 0x28 holding either
//     "emperor waiting" (word 0x1A, when warned flag set)
//     or default "new request" (word 0x16) plus the
//     rome1_buttons row.
//   * Word 0x1B + font_no(av_imperial_gift_level) at
//     y=0x180.
//   * Word 1 of string 0x1F + font_no(players_denarii) at
//     y=0x8E.
// Tail: hold_mouse_replace = 1; refresh_svga_screen;
// set_palette(temp_palette).
void forum_rome_screen(void)
{
    int favour_word;

    cover_mouse_droppings();
    setup_whole_screen_refresh();

    if (forum_repapering[last_forum_dept] != 0)
        show_pl8file("forum.pl8",
                     forum_repapering[last_forum_dept]);
    explain_forum();
    stone_random_count = 0x14;
    show_a_mosaic_frame(0, 0, 0x28, 0xb);
    show_a_mosaic_blank(0x10, 0x10, 0x26, 9);
    font_list(0x26, 0, 0x18, 0x1c, font2, 0x10);

    x_is = 0;
    font_list(0x26, 1, 0x20, 0x40, font1, 0x10);
    if      (imperial_favour <= 0)    favour_word = 3;
    else if (imperial_favour >= 0xc8) favour_word = 0xe;
    else                              favour_word = imperial_favour / 20 + 4;
    font_list(0x26, favour_word, x_is + 0x30, 0x40, font1, 0x10);

    x_is = 0;
    font_list(0x26, 2, 0x20, 0x50, font1, 0x10);
    font_no(tribute, 0x20, " Dn.", x_is + 0x20, 0x50, font1, 0x10);

    x_is = 0;
    if (imperial_req_amount == 0) {
        font_list(0x26, 0x14, 0x20, 0x60, font1, 0x10);
    } else {
        font_list(0x26, 0x15, 0x20, 0x60, font1, 0x10);
        font_no(imperial_req_amount, 0x20, " ",
                x_is + 0x20, 0x60, font1, 0x10);
        font_list(0x26, 0xf, x_is + 0x20, 0x60, font1, 0x10);
        font_list(0x10, imperial_req_goods + 1,
                  x_is + 0x20, 0x60, font1, 0x10);
    }

    draw_a_dias(0x1c, 0x76, 0x248, 0x28);
    if (warned_of_emperor_reply_month != 0) {
        font_list(0x26, 0x1a, 0x20, 0x7c, font1, 0x10);
    } else {
        font_list(0x26, 0x16, 0x20, 0x7c, font1, 0x10);
        show_buttons(0x150, 0x78, rome1_buttons, 1);
        x_is = 0;
        font_list(0x26, 0x1b, 0x180, 0x7c, font1, 0x10);
        font_no(av_imperial_gift_level, 0x20, " Dn)",
                x_is + 0x180, 0x7c, font1, 0x10);
    }

    x_is = 0;
    font_list(0x1f, 1, 0x20, 0x8e, font1, 0x10);
    font_no(players_denarii, 0x20, " Dn",
            x_is + 0x20, 0x8e, font1, 0x10);

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5ED7C
// WIN: 0x00426609
// Lines 1214–1234
//
// "Final bribe" / imperial-gift confirmation box.  Draws a
// 14×22-cell mosaic-window panel at (0xa0, 0x80) with three
// label rows: the gift's required amount (text 0x26/0x27 +
// av_imperial_gift_level " Dn)"), the player's current
// denarii (text 0x1f/1 + players_denarii " Dn"), and three
// flavour rows (text 0x26 lines 0x17/0x18/0x19).  The
// rome2_buttons set is drawn at (0x160, 0xf8) and the gift
// thumbnail at index 0x10 via show_gift_amount.
void show_final_bribe_box(void)
{
    cover_mouse_droppings();
    setup_whole_screen_refresh();
    stone_random_count = 0x14;
    show_a_mosaic_window(0xa0, 0x80, 0x16, 0xe);
    font_list(0x26, 0x27, 0xc0, 0x98, font1, 0x10);
    x_is = 0;
    font_list(0x26, 0x1b, 0xc0, 0xb0, font1, 0x10);
    font_no(av_imperial_gift_level, ' ', " Dn)", x_is + 0xc0, 0xb0, font1, 0x10);
    x_is = 0;
    font_list(0x1f, 1, 0xc0, 0xc8, font1, 0x10);
    font_no(players_denarii, ' ', " Dn", x_is + 0xc0, 0xc8, font1, 0x10);
    font_list(0x26, 0x17, 0xc0, 0x100, font1, 0x10);
    font_list(0x26, 0x18, 0xc0, 0x118, font1, 0x10);
    font_list(0x26, 0x19, 0xc0, 0x138, font1, 0x10);
    show_buttons(0x160, 0xf8, rome2_buttons, 3);
    show_gift_amount(0x10);
    hold_mouse_replace = 1;
    refresh_svga_screen();
}

// FUNCTION: C2 0x5EF04
// WIN: 0x0042677f
// Lines 1237–1248
//
// Draw the imperial-gift selection panel and initialise the amount
// display to slot 4, then refresh the screen.
void show_gift_box(void)
{
    cover_mouse_droppings();
    setup_whole_screen_refresh();
    show_a_mosaic_frame(0xa0, 0x20, 0x16, 8);
    stone_random_count = 0x14;
    show_a_mosaic_blank(0xb0, 0x30, 0x14, 6);
    font_list(0x26, 0x17, 0xc0, 0x40, font1, 0x10);
    font_list(0x26, 0x18, 0xc0, 0x58, font1, 0x10);
    font_list(0x26, 0x19, 0xc0, 0x78, font1, 0x10);
    show_buttons(0x160, 0x38, rome2_buttons, 3);
    show_gift_amount(4);
    hold_mouse_replace = 1;
    refresh_svga_screen();
}

// FUNCTION: C2 0x5EFCD
// WIN: 0x00426836
// Lines 1253–1259
//
// Render the imperial-gift amount box for gift slot
// `gift_index` (0–3 typically).  Draws a 1-cell-tall blank
// mosaic at column 0x1a0, row gift_index*16 - 4 (above the
// gift thumbnail), then prints `imperial_gift_level` (the
// player's gift-rating numeric) inside it at row 0x1a8.
//
// If `imperial_gift_level` is negative (uninitialised
// sentinel), zero it before display.
void show_gift_amount(int gift_index)
{
    stone_random_count = 0x14;
    show_a_mosaic_blank(0x1a0, gift_index * 16 - 4, 5, 1);
    if (imperial_gift_level < 0) {
        imperial_gift_level = 0;
    }
    font_no(imperial_gift_level, ' ', " Dn", 0x1a8, gift_index * 16, font1, 0x10);
    setup_refresh_area(0x140, gift_index * 16 - 0x10, 0xf, 2, 2);
}

// FUNCTION: C2 0x5F03F
// WIN: 0x004268a3
// Lines 1262–1269
//
// Forum advisor entry: black out, cover mouse, mark a full refresh,
// paint the forum panel and palette, run explain_forum to draw the
// dept body, then push the frame and palette to SVGA and raise
// hold_mouse_replace.
void forum_advisor_screen(void)
{
    black_out();
    cover_mouse_droppings();
    setup_whole_screen_refresh();
    show_pl8file("forum.pl8", 0x1e0);
    readfile("forum.256", temp_palette, 0x300, 0);
    explain_forum();
    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5F080
// WIN: 0x00426901
// Lines 1275–1284
//
// Forum entry: temple-overview variant.  Blank palette, load
// rat_back.256 + rat_back.pl8 (rat-eating-grain background),
// render basic_temple_screen, fade up the temple palette,
// preload forum.256 + forumbit.pl8 for the next transition.
void forum_temple_screen(void)
{
    black_out();
    readfile("rat_back.256", temp_palette, 0x300, 0);
    readfile("rat_back.pl8", ((void *)scratch_buffer), 0xc350, 0);
    basic_temple_screen();
    set_palette(temp_palette);
    readfile("forum.256", temp_palette, 0x300, 0);
    readfile("forumbit.pl8", ((void *)scratch_buffer), 0xea60, 0);
}

// FUNCTION: C2 0x5F0F5
// WIN: 0x00426989
// Lines 1286–1383
//
// Forum/temple ratings sub-screen.  Loads rat_fron.pl8 as
// the background plate, frames a 0x28x8 panel at (0, 0x160),
// stamps the panel heading (font1 string 0x22 word 3, colour
// 0x20).
//
// Looks up the player’s threshold pair for the current
// promotion rank from promotion_levels and promotion_av_levels
// at row index (c2inf+0x34) * 5 + completed_provinces.
//
// Then four rating rows (empire / peace / prosperity /
// culture):
//   * Draws the rank icon (write_general_sprite_with_front_ofset
//     base 0xC) and the corresponding promotion-mark sprite
//     (write_general_sprite, ebp = 1, 2 keyed on whether the
//     rating clears the next-rank threshold).
//   * Frame the cell with a 0x21x0x8C dias at (rating_y,
//     0x164).
//   * Print the rating name + numeric value (rating /
//     average_rating progress).
//
// When (c2inf+0x35) is non-zero (player is mid-promotion):
// play_speech(0x2D), show a slimmed-down ratings row with no
// peace value (peace = 0), then show_temple_tip.  Otherwise
// play_speech(0x1E) and render the full four-rating table.
//
// Tail: hold_mouse_replace = 1; refresh_svga_screen;
// set_palette(temp_palette).
//
void basic_temple_screen(void)
{
    int next_threshold;
    int next_av_threshold;
    int i;

    cover_mouse_droppings();
    show_pl8file("rat_fron.pl8", 0x1e0);
    show_a_mosaic_blank(0, 0x160, 0x28, 8);
    font_list(0x22, 3, 0xcc, 0x1d0, font1, 0x20);
    setup_whole_screen_refresh();
    x_is = 0;

    next_threshold    = promotion_levels[c2inf.skill_level][completed_provinces];
    next_av_threshold = promotion_av_levels[c2inf.skill_level][completed_provinces];

    for (i = 0; i < 4; i++) {
        int bar_w;
        int rank_image;
        int bar_w_raw;
        if (i == 0)      bar_w = 0x12c - empire_rating * 3;
        else if (i == 1) bar_w = 0x12c - peace_rating * 3;
        else if (i == 2) bar_w = 0x12c - prosperity_rating * 3;
        else if (i == 3) bar_w = 0x12c - culture_rating * 3;
        if (i == 0)      { if (empire_rating     >= next_threshold) rank_image = 2; else rank_image = 1; }
        else if (i == 1) { if (peace_rating      >= next_threshold) rank_image = 2; else rank_image = 1; }
        else if (i == 2) { if (prosperity_rating >= next_threshold) rank_image = 2; else rank_image = 1; }
        else if (i == 3) { if (culture_rating    >= next_threshold) rank_image = 2; else rank_image = 1; }
        bar_w_raw = bar_w;
        if (bar_w > 0x126) bar_w = 0x126;
        if (bar_w < 0)     bar_w = 0;
        write_general_sprite_with_front_ofset(0, i * 0xa0 + 0x20, 0xc, bar_w + 0xc);
        write_general_sprite(rank_image, i * 0xa0 + 0x20, bar_w_raw);
    }

    for (i = 0; i < 4; i++) {
        int icon_x = i * 0xa0;
        draw_a_dias(icon_x + 0xa, 0x164, 0x8c, 0x21);
    }

    if (c2inf.peace_mode == 0) {
        play_speech(0x1e);
        x_is = 0;
        font_list(0x20, 1, 0x1c, 0x167, font1, 0x10);
        font_no(empire_rating, 0x20, " %", x_is + 0x1c, 0x167, font1, 0x10);
        x_is = 0;
        font_list(0x20, 6, 0x20, 0x177, font1, 0x10);
        font_no(next_threshold, 0x20, " %)", x_is + 0x20, 0x177, font1, 0x10);
        x_is = 0;
        font_list(0x20, 2, 0xbc, 0x167, font1, 0x10);
        font_no(peace_rating, 0x20, " %", x_is + 0xbc, 0x167, font1, 0x10);
        x_is = 0;
        font_list(0x20, 6, 0xbc, 0x177, font1, 0x10);
        font_no(next_threshold, 0x20, " %)", x_is + 0xbc, 0x177, font1, 0x10);
        x_is = 0;
        font_list(0x20, 3, 0x160, 0x167, font1, 0x10);
        font_no(prosperity_rating, 0x20, " %", x_is + 0x160, 0x167, font1, 0x10);
        x_is = 0;
        font_list(0x20, 6, 0x15c, 0x177, font1, 0x10);
        font_no(next_threshold, 0x20, " %)", x_is + 0x15c, 0x177, font1, 0x10);
        x_is = 0;
        font_list(0x20, 4, 0x1fc, 0x167, font1, 0x10);
        font_no(culture_rating, 0x20, " %", x_is + 0x205, 0x167, font1, 0x10);
        x_is = 0;
        font_list(0x20, 6, 0x1fc, 0x177, font1, 0x10);
        font_no(next_threshold, 0x20, " %)", x_is + 0x1fc, 0x177, font1, 0x10);
        x_is = 0;
        font_list(0x20, 5, 0xa0, 0x18a, font1, 0xe);
        font_no(average_rating, 0x20, " %",
                x_is + 0xa0, 0x18a, font1, 0xe);
        font_list(0x20, 6, x_is + 0xa2, 0x18a, font1, 0xe);
        font_no(next_av_threshold, 0x20, " %)",
                x_is + 0xa2, 0x18a, font1, 0xe);
        show_temple_tip();
    } else {
        play_speech(0x2d);
        x_is = 0;
        font_list(0x20, 1, 0x1c, 0x167, font1, 0x10);
        font_no(0, 0x20, " %", x_is + 0x1c, 0x167, font1, 0x10);
        x_is = 0;
        font_list(0x20, 2, 0xbc, 0x167, font1, 0x10);
        font_no(0, 0x20, " %", x_is + 0xbc, 0x167, font1, 0x10);
        x_is = 0;
        font_list(0x20, 3, 0x160, 0x167, font1, 0x10);
        font_no(prosperity_rating, 0x20, " %",
                x_is + 0x160, 0x167, font1, 0x10);
        x_is = 0;
        font_list(0x20, 4, 0x1fc, 0x167, font1, 0x10);
        font_no(culture_rating, 0x20, " %",
                x_is + 0x205, 0x167, font1, 0x10);
        show_temple_tip();
    }

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5F743
// WIN: 0x00427122
// Lines 1385–1392
//
// Draw the temple-tip panel at the bottom of the forum temple
// screen.  Peace-mode/tutorial skips the early tips by forcing
// current_temple_tip to 0x11 when it is still below 9.
void show_temple_tip(void)
{
    stone_random_count = 0x1e;
    show_a_mosaic_blank(0x10, 0x19c, 0x26, 3);
    draw_a_dias(0xf, 0x19b, 0x262, 0x32);
    if (c2inf.peace_mode != 0) {
        if (current_temple_tip < 9)
            current_temple_tip = 0x11;
    }
    font_format_split(0x20, current_temple_tip + 7, 0x18, 0x19e,
                      0x258, 0x64, 0, 0, font1, 0x10);
    setup_refresh_area(0, 0x190, 0x28, 5, 1);
}

// FUNCTION: C2 0x5F7E2
// WIN: 0x004271af
// Lines 1396–1411
//
// The forum-clerks panel: re-papers the dept background if the current
// last_forum_dept is on the repapering list, draws the explain panel +
// outer mosaic, lays out the title strip, then chains history_graphs
// and history_selection.  Bottom-line buttons come from clerk_buttons.
// Tail-merges into the shared refresh_svga_screen + set_palette
// epilogue at 0x5db9a.
void forum_clerks_screen(void)
{
    int dept;

    cover_mouse_droppings();
    setup_whole_screen_refresh();

    get_history_in_buffer(((int *)((scratch_buffer) + 0x1fbd0)));

    dept = last_forum_dept;
    if (forum_repapering[dept] != 0) {
        show_pl8file("forum.pl8", forum_repapering[dept]);
    }

    explain_forum();
    show_a_mosaic_frame(0, 0, 0x28, 0xf);

    stone_random_count = 0x28;

    show_a_mosaic_blank(0x10, 0x10, 0x26, 0xd);
    x_is = 0;
    font_list(0x21, 0, 0x18, 0x1c, font2, 0x10);

    history_graphs();
    history_selection();

    show_buttons(0x40, 0x6c, clerk_buttons, 2);

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x5F89E
// WIN: 0x00427286
// Lines 1418–1438
//
// Header strip for the history graph screen.  Lays out:
//   * Two top "From / To" labels (font_list 5 + 6) inside a mosaic blank.
//   * A second mosaic blank for the year selector;
//   * The selected span (history_graph_years[history_graph_length])
//     plus 'years ago' label and its absolute year via show_date;
//   * The current year on the right (font_list 8) and its show_date.
// Tail-merges into show_personal_cash_stats+0x11c — which calls
// setup_refresh_area(0x10, 0x84, 0xb, 7, 1) and returns.
void history_selection(void)
{
    int years;

    stone_random_count = 0x29;

    show_a_mosaic_blank(0x10, 0x40, 4, 8);
    font_list(0x21, 5, 0x20, 0x44, font1, 0x10);
    font_list(0x21, 6, 0x28, 0x58, font1, 0x10);

    x_is  = 0;
    years = history_graph_years[history_graph_length];

    show_a_mosaic_blank(0x10, 0x8e, 0xa, 5);
    font_no(years, 0x20, " ", 0x38, 0x90, font1, 0x10);
    font_list(0x21, 7, x_is + 0x38, 0x90, font1, 0x10);
    x_is = 0;

    show_date(year - years, 0x12, 0xb0, 1);
    font_list(0x21, 8, x_is + 0x14, 0xb0, font1, 0x10);
    show_date(year, x_is + 0x16, 0xb0, 1);

    setup_refresh_area(0x10, 0x84, 0xb, 7, 1);
}

// FUNCTION: C2 0x5F9F0
// WIN: 0x004273b1
// Lines 1442–1473
//
// Render the four history graphs on the forum clerks screen.  Four
// columns: "current" plus three retrospective panels, each
// label-then-graph-then-numeric-tick.  show_history_graph(graph_idx,
// x, y) takes the slot index in EBX.
// Tail-merges into setup_refresh_area(0xb0, 0x10, 0x1d, 0xe, 1) at
// 0x5ea29.
void history_graphs(void)
{
    int top;

    stone_random_count = 0x28;
    show_a_mosaic_blank(0xb0, 0x10, 0x1c, 0xd);

    x_is = 0x10;
    font_list(0x21, 1, 0xc0, 0x83, font1, 0x10);
    top = show_history_graph(0xb0, 0x18, 0);
    font_no(top, 0x20, " ", x_is + 0xb0, 0x83, font1, 0x10);

    x_is = 0x18;
    font_list(0x21, 2, 0x1ac, 0x83, font1, 0x10);
    top = show_history_graph(0x194, 0x18, 1);
    font_no(top, 0x20, " ", x_is + 0x194, 0x83, font1, 0x10);

    x_is = 8;
    font_list(0x21, 3, 0xb8, 0xce, font1, 0x10);
    top = show_history_graph(0xb0, 0x96, 2);
    font_no(top, 0x20, " ", x_is + 0xb0, 0xce, font1, 0x10);

    x_is = 0xc;
    font_list(0x21, 4, 0x1a0, 0xce, font1, 0x10);
    top = show_history_graph(0x194, 0x96, 3);
    font_no(top, 0x20, " ", x_is + 0x194, 0xce, font1, 0x10);

    setup_refresh_area(0xb0, 0x10, 0x1d, 0xe, 1);
}

// FUNCTION: C2 0x5FBBA
// WIN: 0x004275a1
// Lines 1476–1558
//
// Plot a single history series onto a 200x200 graph at (x, y).
// The series index is `idx`; the current zoom level is
// history_graph_length, indexing history_graph_years[] to get
// the displayed span in years.  X step is 0xC8 / years pixels.
//
// Pass 1 walks back `years` records from history_end_ptr in
// the 0xC8-entry circular history buffer (anchored at
// scratch_buffer + 0x1FBD0) to find the max value, then
// quantises it to one of twelve preset Y-axis ranges:
//
//   * idx >= 2 (denarii / population / employment): 50, 100,
//     200, 500, 1k, 2.5k, 5k, 10k, 25k, 50k, 100k, 1M.
//   * idx <  2 (rates / counts): 10, 25, 50, 100, 200, 500,
//     1k, 2k, 4k, 8k, 10k, 20k, 50k.
//
// Each bucket sets `top_value` plus a multiplier OR divisor
// (both start at 1): bar height = v / divis * mult, clipped to
// [0, 200].  NOTE the arm condition is `1 >= idx` (idx 0/1 gets
// the 50..1M ladder with top_div 0x64; idx >= 2 gets the
// 10..50k ladder with top_div 0x32) -- the previous decomp had
// the arms SWAPPED and collapsed mult/divis into one var (bar
// heights wrong by up to 25x).  Axis: draw_a_dias + frame
// draw_a_rect, then one rect per year, colour 0xA/0xD odd/even.
// Returns top_value so the caller can label the Y axis.
int show_history_graph(int x, int y, int idx)
{
    int years   = history_graph_years[history_graph_length];
    int xstep   = 0xc8 / years;
    int idx_circ;
    int max_val = 0;
    int top_value;
    int mult;
    int top_div;
    int divis;
    int i;
    int v;

    idx_circ = history_end_ptr - years;
    if (idx_circ < 0) idx_circ += 0xc8;
    for (i = 0; i < years; i++) {
        v = get_history_from_buffer(((int *)((scratch_buffer) + 0x1fbd0)),
                                    idx_circ, idx);
        if (v > max_val) max_val = v;
        if (++idx_circ >= 0xc8) idx_circ = 0;
    }

    mult = divis = 1;
    if (1 >= idx) {
        if      (max_val <= 0x32)    { top_value = 0x32;    mult = 2; }
        else if (max_val <= 0x64)    { top_value = 0x64;    }
        else if (max_val <= 0xc8)    { top_value = 0xc8;    divis = 2; }
        else if (max_val <= 0x1f4)   { top_value = 0x1f4;   divis = 5; }
        else if (max_val <= 0x3e8)   { top_value = 0x3e8;   divis = 0xa; }
        else if (max_val <= 0x9c4)   { top_value = 0x9c4;   divis = 0x19; }
        else if (max_val <= 0x1388)  { top_value = 0x1388;  divis = 0x32; }
        else if (max_val <= 0x2710)  { top_value = 0x2710;  divis = 0x64; }
        else if (max_val <= 0x61a8)  { top_value = 0x61a8;  divis = 0xfa; }
        else if (max_val <= 0xc350)  { top_value = 0xc350;  divis = 0x1f4; }
        else if (max_val <= 0x186a0) { top_value = 0x186a0; divis = 0x3e8; }
        else                         { top_value = 0xf4240; divis = 0x2710; }
        top_div = 0x64;
    } else {
        if      (max_val <= 0xa)     { top_value = 0xa;     mult = 5; }
        else if (max_val <= 0x19)    { top_value = 0x19;    mult = 2; }
        else if (max_val <= 0x32)    { top_value = 0x32;    }
        else if (max_val <= 0x64)    { top_value = 0x64;    divis = 2; }
        else if (max_val <= 0xc8)    { top_value = 0xc8;    divis = 4; }
        else if (max_val <= 0x1f4)   { top_value = 0x1f4;   divis = 0xa; }
        else if (max_val <= 0x3e8)   { top_value = 0x3e8;   divis = 0x14; }
        else if (max_val <= 0x7d0)   { top_value = 0x7d0;   divis = 0x28; }
        else if (max_val <= 0xfa0)   { top_value = 0xfa0;   divis = 0x50; }
        else if (max_val <= 0x1f40)  { top_value = 0x1f40;  divis = 0xa0; }
        else if (max_val <= 0x2710)  { top_value = 0x2710;  divis = 0xc8; }
        else if (max_val <= 0x4e20)  { top_value = 0x4e20;  divis = 0x190; }
        else                         { top_value = 0xc350;  divis = 0x3e8; }
        top_div = 0x32;
    }

    idx_circ = history_end_ptr - years;
    if (idx_circ < 0) idx_circ += 0xc8;
    draw_a_dias(x, y, 0xca, top_div + 2);
    draw_a_rect(x + 1, y + 1, 0xc8, top_div, 0x20);

    for (i = 0; i < years; i++) {
        int colour;
        int bar_y;
        v = get_history_from_buffer(((int *)((scratch_buffer) + 0x1fbd0)),
                                    idx_circ, idx);
        if (++idx_circ >= 0xc8) idx_circ = 0;
        if (v <= 0) continue;
        if (v > top_value) continue;
        v = v / divis;
        v = v * mult;
        if (v < 0) continue;
        if (v > 0xc8) continue;
        colour = (i & 1) ? 0xa : 0xd;
        bar_y = y + 1 + top_div - v;
        if (bar_y < y) continue;
        if (bar_y + v > y + 0xc9) continue;
        draw_a_rect(x + 1 + i * xstep, bar_y, xstep, v, colour);
    }

    return top_value;
}

// FUNCTION: C2 0x5FFC8
// WIN: 0x00427ae3
// Lines 1560–1569
//
// Forum: load the empire-overview screen.  In peace_mode (tutorial)
// the forum is disabled, so we tail-call forum_city_only_screen
// instead.  Otherwise: blank the palette, load empire.256 into
// temp_palette + e_parts2.pl8 into scratch_buffer, render the
// base empire screen, fade up to the empire palette, and
// preload forum.256 (so the next forum-screen transition can
// fade between palettes without disk-thrashing).
void forum_empire_screen(void)
{
    if (c2inf.peace_mode != 0) {
        forum_city_only_screen();
        return;
    }
    black_out();
    readfile("empire.256", temp_palette, 0x300, 0);
    readfile("e_parts2.pl8", ((void *)scratch_buffer), 0x249f0, 0);
    basic_empire_screen();
    set_palette(temp_palette);
    readfile("forum.256", temp_palette, 0x300, 0);
}

// FUNCTION: C2 0x60038
// WIN: 0x00427b6a
// Lines 1571–1579
//
// Empire-screen base: load `empire.pl8` background, render
// the regional shapes + top/bottom slabs, draw the title at
// (0xbe, 0x19e) and subtitle at (0xd0, 0x1ce) using string
// table 0x22 lines 1 & 3, then refresh the whole screen.
void basic_empire_screen(void)
{
    show_pl8file("empire.pl8", 0x1e0);
    show_regions_in_empire();
    show_empire_top_slab();
    show_empire_bottom_slab();
    font_list(0x22, 1, 0xbe, 0x19e, font1, 0x3f);
    font_list(0x22, 3, 0xd0, 0x1ce, font1, 0x20);
    setup_whole_screen_refresh();
    hold_mouse_replace = 1;
    refresh_svga_screen();
}

// FUNCTION: C2 0x600A3
// WIN: 0x00427bdc
// Lines 1585–1590
//
// Stamp the standard region marker sprite onto the empire map
// for every region with empire[i] == 6 (player-controlled),
// then dispatch to show_regions_on_offer for the rest.
void show_regions_in_empire(void)
{
    int i;

    for (i = 0; i < 0x2c; i++) {
        if (empire[i] == 6) {
            write_general_sprite(i, empire_positions[i].x,
                                    empire_positions[i].y);
        }
    }
    show_regions_on_offer();
}

// FUNCTION: C2 0x600DB
// WIN: 0x00427c45
// Lines 1592–1605
//
// Draw offer/availability markers for regions on the empire map.
// empire == 2 gets marker 7; empire == 6 is further keyed by
// empire_won: not yet won -> 6, completed sentinel -> 8, otherwise
// if below the active threshold -> 5.
void show_regions_on_offer(void)
{
    int i;

    for (i = 0; i < 0x2c; i++) {
        if (empire[i] == 2) {
            write_image(misc, 7, empire_flag_positions[i].x - 5,
                        empire_flag_positions[i].y - 0x20);
        }
        if (empire[i] == 6) {
            if (empire_won[i] == 0) {
                write_image(misc, 6, empire_flag_positions[i].x - 5,
                            empire_flag_positions[i].y - 0x20);
            }
            if (empire_won[i] == 0x1869f) {
                write_image(misc, 8, empire_flag_positions[i].x - 5,
                            empire_flag_positions[i].y - 0x20);
            }
            if (empire_won[i] < 0x1869e) {
                write_image(misc, 5, empire_flag_positions[i].x - 5,
                            empire_flag_positions[i].y - 0x20);
            }
        }
    }
}

// FUNCTION: C2 0x601CC
// WIN: 0x00427d86
// Lines 1607–1613
//
// Top slab of the empire-screen frame: writes four
// horizontal trim sprites at column x=0x1a (=26 px in)
// down the screen at rows 0xd2, 0x112, 0x132, 0x16c
// (210, 274, 306, 364).  Sprite indices 0x2c, 0x2e,
// 0x2c, 0x2d — the symmetric 0x2c on rows 1+3 and the
// asymmetric 0x2e/0x2d on the inner edges form the
// double-bar look of the slab.
void show_empire_top_slab(void)
{
    write_general_sprite(0x2c, 0xd2, 0x1a);
    write_general_sprite(0x2e, 0x112, 0x1a);
    write_general_sprite(0x2c, 0x132, 0x1a);
    write_general_sprite(0x2d, 0x16c, 0x1a);
}

// FUNCTION: C2 0x60221
// WIN: 0x00427dd5
// Lines 1614–1620
//
// Bottom slab of the empire-screen frame: writes five
// vertical trim sprites at row y=0x199 (=409 px down)
// across the screen at columns 0xb8, 0xf8, 0x124, 0x144,
// 0x184 (184, 248, 292, 324, 388).  Sprite sequence is
// 0x2d / 0x2c / 0x2e / 0x2c / 0x2d — mirror of top_slab's
// horizontal layout.
//
// Tail-merges into show_empire_top_slab's last write
void show_empire_bottom_slab(void)
{
    write_general_sprite(0x2d, 0xb8, 0x199);
    write_general_sprite(0x2c, 0xf8, 0x199);
    write_general_sprite(0x2e, 0x124, 0x199);
    write_general_sprite(0x2c, 0x144, 0x199);
    write_general_sprite(0x2d, 0x184, 0x199);
}

// FUNCTION: C2 0x6027F
// WIN: 0x00427e44
// Lines 1623–1652
//
// The forum-army panel: city-only mode delegates to the simpler
// forum_city_only_screen; otherwise we refresh cohort tallies,
// repaper the dept background if applicable, draw the explain panel
// + outer mosaic + title row, and chain the recruitment / tribune
// rollup / mercs sub-panels.  The bottom button strip uses 5/7/8
// army buttons depending on whether any cohorts are deployed and
// whether forum_viewed_army is the special 0xa slot; if mercs are
// permitted, two extra mercenary buttons follow.
void forum_army_screen(void)
{
    if (c2inf.peace_mode != 0) {
        forum_city_only_screen();
        return;
    }

    check_viewed_cohort();
    fill_cohort_centuries();
    total_no_of_cohorts = no_of_cohorts_in_action;

    cover_mouse_droppings();
    setup_whole_screen_refresh();

    if (forum_repapering[last_forum_dept] != 0) {
        show_pl8file("forum.pl8",
                     forum_repapering[last_forum_dept]);
    }

    explain_forum();
    show_a_mosaic_frame(0, 0, 0x28, 0xe);
    stone_random_count = 0x3c;
    show_a_mosaic_blank(0x10, 0x10, 0x26, 0xc);

    x_is = 0;
    font_list(0x23, 0, 0x18, 0x14, font2, 0x10);

    show_recruitment();
    show_this_tribune();
    show_mercs();

    no_of_army_buttons = 5;
    if (total_no_of_cohorts > 0) {
        if (forum_viewed_army == 0xa) {
            no_of_army_buttons = 7;
        } else {
            no_of_army_buttons = 8;
        }
    }
    show_buttons(0x18, 0x30, army_buttons, no_of_army_buttons);

    if (max_mercs_allowed != 0) {
        show_buttons(0x18, 0x30, mercenary_buttons, 2);
    }

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x603C1
// WIN: 0x00427f9b
// Lines 1654–1677
//
// Mercenary panel inside forum_army_screen.  When mercs are allowed:
// a fresh mosaic blank, the count + 'mercenaries' label, the
// 'from <province>' line, the 'of <type>' line, and the upkeep
// cost (mercs_in_army / 50 * mercs_cost_per_50 "Dn").  Otherwise
// three explanation labels (entries 0x22, 0x23, 0x24 of strings 0x23).
void show_mercs(void)
{
    if (max_mercs_allowed != 0) {
        show_a_mosaic_blank(0x16, 0x9c, 0xa, 3);
        setup_refresh_area(0x16, 0x9c, 0xb, 4, 2);

        x_is = 0;
        font_no(mercs_in_army, 0x20, " ", 0x18, 0x9e, font1, 0x10);
        font_list(0x23, 0x1f, x_is + 0x18, 0x9e, font1, 0x10);

        x_is = 0;
        font_list(7,    mercs_from,        0x18, 0xae, font1, 0x10);
        font_list(0x47, mercs_type + 0xa,  x_is + 0x18, 0xae, font1, 0x10);

        x_is = 0;
        font_list(0x23, 0x20, 0x18, 0xbe, font1, 0x10);
        font_no(mercs_in_army / 50 * mercs_cost_per_50, 0x20, "Dn",
                x_is + 0x18, 0xbe, font1, 0x10);
        font_list(0x23, 0x21, x_is + 0x18, 0xbe, font1, 0x10);
    } else {
        font_list(0x23, 0x22, 0x18, 0x9e, font1, 0x10);
        font_list(0x23, 0x23, 0x18, 0xae, font1, 0x10);
        font_list(0x23, 0x24, 0x18, 0xbe, font1, 0x10);
    }
}

// FUNCTION: C2 0x6058A
// WIN: 0x0042813c
// Lines 1679–1743
//
// Tribune-detail panel.  Two layouts:
//
//   * forum_viewed_army == 0xA (aggregate army view): show
//     five rows of (total, recruited, needed) for regulars,
//     irregulars, auxiliaries; one row for mercs in army;
//     finally either two rows (morale + readiness words
//     keyed on average_cohort_morale / _readiness) when
//     total_no_of_cohorts > 0, or a font_format_split
//     paragraph (string 0x4E word 0) when no cohorts exist.
//
//   * forum_viewed_army != 0xA (single-army view): refresh
//     temp_army from get_actual_viewed_army, then run
//     show_tribunes_report(temp_army, 0x108, 0x22, 1).  Stamp
//     the general sprite (army_list[+0x28] + 0x20) and a
//     standard sprite 0x19 at (0x240, ...), with the
//     general name (string 0x23 word 5) at (0x1C0, 0x22).
//
// Both branches close with update_tribune_flag(1) and
// setup_refresh_area(0x108, 0x1E, 0x17, 0xB, 1), then tail-
// merge into 0x5F73D pop epilogue.
void show_this_tribune(void)
{
    stone_random_count = 0xf;

    if (forum_viewed_army == 0xa) {
        show_a_mosaic_blank(0x108, 0x1e, 0x16, 9);
        show_a_mosaic_blank(0x108, 0xa6, 0x16, 1);
        draw_a_dias(0x100, 0x1c, 0x168, 0x98);

        font_list(0x23, 0xc, 0x110, 0x22, font1, 0x10);
        font_list(0x23, 0xd, 0x1c0, 0x22, font1, 0x10);

        x_is = 0;
        font_no(total_no_of_regulars, 0x20, " ",
                0x110, 0x3c, font1, 0x10);
        font_list(0x23, 0xe, x_is + 0x110, 0x3c, font1, 0x10);
        x_is = 0;
        if (total_no_of_regulars >= current_no_of_regulars)
            font_no(current_no_of_regulars, 0x20, " ", 0x190, 0x3c, font1, 0x10);
        else
            font_no(total_no_of_regulars, 0x20, " ", 0x190, 0x3c, font1, 0x10);
        font_list(0x23, 0x11, x_is + 0x190, 0x3c, font1, 0x10);
        font_no(needed_no_of_regulars, 0x20, " ",
                x_is + 0x1a0, 0x3c, font1, 0x10);
        font_list(0x23, 0x12, x_is + 0x1a0, 0x3c, font1, 0x10);

        x_is = 0;
        font_no(total_no_of_irregulars, 0x20, " ",
                0x110, 0x4c, font1, 0x10);
        font_list(0x23, 0xf, x_is + 0x110, 0x4c, font1, 0x10);
        x_is = 0;
        if (total_no_of_irregulars >= current_no_of_irregulars)
            font_no(current_no_of_irregulars, 0x20, " ", 0x190, 0x4c, font1, 0x10);
        else
            font_no(total_no_of_irregulars, 0x20, " ", 0x190, 0x4c, font1, 0x10);
        font_list(0x23, 0x11, x_is + 0x190, 0x4c, font1, 0x10);
        font_no(needed_no_of_irregulars, 0x20, " ",
                x_is + 0x1a0, 0x4c, font1, 0x10);
        font_list(0x23, 0x12, x_is + 0x1a0, 0x4c, font1, 0x10);

        x_is = 0;
        font_no(total_no_of_auxillaries, 0x20, " ",
                0x110, 0x5c, font1, 0x10);
        font_list(0x23, 0x10, x_is + 0x110, 0x5c, font1, 0x10);
        x_is = 0;
        if (total_no_of_auxillaries >= current_no_of_auxillaries)
            font_no(current_no_of_auxillaries, 0x20, " ", 0x190, 0x5c, font1, 0x10);
        else
            font_no(total_no_of_auxillaries, 0x20, " ", 0x190, 0x5c, font1, 0x10);
        font_list(0x23, 0x11, x_is + 0x190, 0x5c, font1, 0x10);
        font_no(needed_no_of_auxillaries, 0x20, " ",
                x_is + 0x1a0, 0x5c, font1, 0x10);
        font_list(0x23, 0x12, x_is + 0x1a0, 0x5c, font1, 0x10);

        x_is = 0;
        font_no(mercs_in_army, 0x20, " ",
                0x110, 0x6c, font1, 0x10);
        font_list(0x23, 0x1f, x_is + 0x110, 0x6c, font1, 0x10);

        if (total_no_of_cohorts != 0) {
            font_list(0x23, average_cohort_morale + 0x13,
                      0x110, 0x8c, font1, 0x10);
            font_list(0x23, average_cohort_readiness + 0x18,
                      0x110, 0x9c, font1, 0x10);
        } else {
            font_format_split(0x4e, 0, 0x110, 0x84,
                              0x140, 0x64, 0, 0, font1, 0x10);
        }
    } else {
        temp_army = (short)get_actual_viewed_army();
        show_a_mosaic_blank(0x108, 0x1e, 0x16, 9);
        show_a_mosaic_blank(0x108, 0xa6, 0x16, 1);
        draw_a_dias(0x100, 0x1c, 0x168, 0x98);

        show_tribunes_report(temp_army, 0x108, 0x22, 1);

        write_general_sprite(army_list[temp_army].cohort_id,
                             0x240, 0x20);
        write_general_sprite(0x19, 0x240, 0x32);
        font_list(5, army_list[temp_army].cohort_id,
                  0x1c0, 0x22, font1, 0x10);
    }

    update_tribune_flag(1);
    setup_refresh_area(0x108, 0x1e, 0x17, 0xb, 1);
}

// FUNCTION: C2 0x60B15
// WIN: 0x004286d5
// Lines 1746–1765
//
// Advance and draw the animated tribune flag in either the city panel
// (`mode` == 0) or the forum panel (`mode` != 0).  The frame counter
// lives at request_message+0x38 and wraps every 64 ticks; routed armies
// (state_idx 10) force it back to zero.  The drawn sprite index is
// counter/8 plus the panel-specific base frame.
void update_tribune_flag(int mode)
{
    short army;

    request_message.tribune_flag_counter += 1;
    if (request_message.tribune_flag_counter >= 0x40) {
        request_message.tribune_flag_counter = 0;
    }
    army = get_actual_viewed_army();
    temp_army = army;
    if (army_list[army].state_idx == 0xa) {
        request_message.tribune_flag_counter = 0;
    }
    stone_random_count = 0xb;
    if (mode == 0) {
        show_a_mosaic_blank(0x190, 0x56, 2, 2);
        write_general_sprite((request_message.tribune_flag_counter >> 3) + 0x3a, 0x190, 0x56);
        setup_refresh_area(0x190, 0x56, 2, 2, 2);
    } else {
        if (forum_viewed_army == 0xa) return;
        show_a_mosaic_blank(0x240, 0x32, 2, 2);
        write_general_sprite((request_message.tribune_flag_counter >> 3) + 0x19, 0x240, 0x32);
        setup_refresh_area(0x240, 0x32, 2, 2, 2);
    }
}

// FUNCTION: C2 0x60C04
// WIN: 0x004287b8
// Lines 1769–1821
//
// Recruitment status panel.  Refreshes predict_army_totals
// and stashes the currently-viewed army into temp_army, then
// paints two narrow header strips at y=0xB6 / 0xC0, the
// recruitment-detail body at (0xC0, 0x3A) and the engagement
// status line at (0x1E0, 0xB6).
//
// Body content (font_list label + font_no value):
//   1. Row 0x3C: "Wages" + army_wage_level (suffix "%").
//   2. Row 0x54: "Conscription" + conscription_rate (suffix "%").
//   3. Header at (0x68, 0x18) width 0xE x 2 / blank at
//      (0x80, 0x18) width 0xE x 1.
//   4. Row 0x6C: "Soldiers requested" + total_no_of_soldiers.
//   5. Row 0x7C: current_no_of_soldiers (clamped to total) +
//      "recruited" / needed_no_of_soldiers + "needed".
//   6. Row 0xBA: cohorts available label keyed on
//      total_no_of_cohorts (0 / 1 / >1) + count + word.
//   7. Status line (forum_viewed_army != 0xA): order word
//      keyed on temp_army's army_list[+0x12] auto-fight
//      (0xA) and army_list[+0xA0] order (idle / advancing /
//      defending).
// Tail-merges into three setup_refresh_area calls for the
// three painted regions, then to the 0x5F73C pop epilogue.
void show_recruitment(void)
{
    int idx;
    int auto_fight;

    stone_random_count = 0x15;
    show_a_mosaic_blank(0x1e0, 0xb6, 9, 1);
    show_a_mosaic_blank(0x1e0, 0xc0, 9, 1);

    predict_army_totals();
    temp_army = (short)get_actual_viewed_army();

    show_a_mosaic_blank(0xc0, 0x3a, 4, 3);

    x_is = 0;
    font_list(0x23, 1, 0x18, 0x3c, font1, 0x10);
    font_no(army_wage_level, 0x20, "Dn",
            0xcc, 0x3c, font1, 0x10);
    x_is = 0;
    font_list(0x23, 2, 0x18, 0x54, font1, 0x10);
    font_no(conscription_rate, 0x20, "%",
            0xcc, 0x54, font1, 0x10);

    show_a_mosaic_blank(0x18, 0x68, 0xe, 2);
    show_a_mosaic_blank(0x18, 0x80, 0xe, 1);

    x_is = 0;
    font_list(0x23, 4, 0x18, 0x6c, font1, 0x10);
    font_no(total_no_of_soldiers, 0x20, " ",
            x_is + 0x18, 0x6c, font1, 0x10);
    font_list(0x23, 5, x_is + 0x18, 0x6c, font1, 0x10);

    x_is = 0;
    if (total_no_of_soldiers >= current_no_of_soldiers)
        font_no(current_no_of_soldiers, 0x20, " ",
                0x18, 0x7c, font1, 0x10);
    else
        font_no(total_no_of_soldiers, 0x20, " ",
                0x18, 0x7c, font1, 0x10);
    font_list(0x23, 6, x_is + 0x18, 0x7c, font1, 0x10);
    font_no(needed_no_of_soldiers, 0x20, " ",
            x_is + 0x28, 0x7c, font1, 0x10);
    font_list(0x23, 7, x_is + 0x28, 0x7c, font1, 0x10);

    x_is = 0;
    if (total_no_of_cohorts == 0) {
        font_list(0x23, 8, 0x160, 0xba, font1, 0x10);
    } else if (total_no_of_cohorts == 1) {
        font_list(0x23, 9, 0x100, 0xba, font1, 0x10);
    } else {
        font_list(0x23, 0xa, 0x100, 0xba, font1, 0x10);
        font_no(total_no_of_cohorts, 0x20, " ",
                x_is + 0x100, 0xba, font1, 0x10);
        font_list(0x23, 0xb, x_is + 0x100, 0xba, font1, 0x10);
    }

    if (forum_viewed_army != 0xa) {
        idx        = temp_army;
        auto_fight = army_list[idx].state_idx;
        if (auto_fight == 0xa) {
            font_list(0x23, 0x1d, 0x1e8, 0xbc, font1, 0x10);
        } else {
            if      (army_list[idx].cohort_size_class == 0) font_list(0x23, 0x1e, 0x1e8, 0xbc, font1, 0x10);
            else if (army_list[idx].cohort_size_class == 1) font_list(0x23, 0x25, 0x1e8, 0xbc, font1, 0x10);
            else if (army_list[idx].cohort_size_class == 2) font_list(0x23, 0x26, 0x1e8, 0xbc, font1, 0x10);
        }
    }

    setup_refresh_area(-8, 0x10, 0x10, 6, 1);
    setup_refresh_area(0x18, 0x6a, 0xe, 3, 1);
    setup_refresh_area(0x1e0, 0xb6, 9, 3, 1);
}

// FUNCTION: C2 0x6100B
// WIN: 0x00428be0
// Lines 1824–1907
//
// Industry sub-screen of the forum.  Branches on c2inf+0x35:
//
//   * normal mode (c2inf+0x35 == 0): iterate i = 0..7 over
//     province_industries[i], reading the (kind, is_trader)
//     pair plus the matching industry[kind] supply /
//     delivered / status counters.  Each row paints an icon
//     (game_panels image kind+0x3B), the kind name (string
//     0x10 word kind+1), a count column (current supply),
//     a label keyed on is_trader (0 = self / 1 = missing /
//     2 = neighbour), a delivered column and a max-needed
//     column.  Neighbour rows (i >= 4) additionally read
//     provincial_difficulty[province_is*4 + i - 4 + 0xAC]
//     as the difficulty boost.
//
//   * promotion mode (c2inf+0x35 != 0): odd-row-only sweep
//     (i = 1, 3, 5, 7) over industry[] keyed by
//     i*2+1, showing the supply + status pair.  Used during
//     temple promotion when half the industries are locked.
//
// Both branches stamp the icon row at y = i*0x10 + 0x37,
// label at y + 2.  Tail: hold_mouse_replace = 1;
// refresh_svga_screen; set_palette(temp_palette);
void forum_industry_screen(void)
{
    int i;
    int hasup;
    int kind;
    int trader;
    int pipe2;
    int supply;
    int diff;
    int citysup;
    int image;

    cover_mouse_droppings();
    setup_whole_screen_refresh();
    if (forum_repapering[last_forum_dept] != 0) show_pl8file("forum.pl8", forum_repapering[last_forum_dept]);
    explain_forum();
    show_a_mosaic_frame(0, 0, 0x28, 0xe);
    stone_random_count = 0x10;
    show_a_mosaic_blank(0x10, 0x10, 0x26, 0xc);

    x_is = 0;
    font_list(0x24, 0, 0x18, 0x14, font2, 0x10);

    if (c2inf.peace_mode == 0) {
        for (i = 0; i < 8; i++) {
            kind   = province_industries[i].kind;
            trader = province_industries[i].is_trader;
            if (i >= 4) diff = ((unsigned char *)provincial_difficulty + 0xac)[i + province_is * 4];
            supply  = industry[kind].supply;
            pipe2   = industry[kind].supply_pipeline[2];
            hasup   = industry[kind].has_supply;
            citysup = industry[kind].city_supply;

            write_image(game_panels, kind + 0x3b, 0x20, i * 0x13 + 0x37);
            font_list(0x10, kind + 1, 0x38, i * 0x13 + 0x39, font1, 0x10);

            if (trader == 0) {
                x_is = 0;
                font_no(pipe2, 0x20, " ", 0x7c, i * 0x13 + 0x39, font1, 0x10);
                font_list(0x24, 1, x_is + 0x7c, i * 0x13 + 0x39, font1, 0x10);
            } else {
                if (trader == 1) image = 0x4b;
                else             image = 0x4c;
                write_image(game_panels, image, 0x7c, i * 0x13 + 0x37);
                font_list(6, diff + 1, 0x90, i * 0x13 + 0x39, font1, 0x10);
            }

            font_no(supply, 0x20, " ", 0x140, i * 0x13 + 0x39, font1, 0x10);
            font_list(0x24, 2, 0x154, i * 0x13 + 0x39, font1, 0x10);
            if (hasup == 0) font_list(0x24, 3, 0x1ae, i * 0x13 + 0x39, font1, 0x10);
            else {
                x_is = 0;
                font_no(hasup, 0x20, " ", 0x1ae, i * 0x13 + 0x39, font1, 0x10);
                if (hasup == 1) font_list(0x24, 4, x_is + 0x1ae, i * 0x13 + 0x39, font1, 0x10);
                else            font_list(0x24, 5, x_is + 0x1ae, i * 0x13 + 0x39, font1, 0x10);
                font_no(citysup, 0x20, "%", x_is + 0x1ae, i * 0x13 + 0x39, font1, 0x10);
                font_list(0x24, 6, x_is + 0x1ae, i * 0x13 + 0x39, font1, 0x10);
            }
        }
    } else {
        for (i = 0; i < 8; i++) {
            kind    = i * 2 + 1;
            hasup   = industry[kind].has_supply;
            citysup = industry[kind].city_supply;

            write_image(game_panels, kind + 0x3b, 0x20, i * 0x13 + 0x37);
            font_list(0x10, kind + 1, 0x38, i * 0x13 + 0x39, font1, 0x10);
            if (hasup == 0) font_list(0x24, 3, 0x8c, i * 0x13 + 0x39, font1, 0x10);
            else {
                x_is = 0;
                font_no(hasup, 0x20, " ", 0x8c, i * 0x13 + 0x39, font1, 0x10);
                if (hasup == 1) font_list(0x24, 4, x_is + 0x8c, i * 0x13 + 0x39, font1, 0x10);
                else            font_list(0x24, 5, x_is + 0x8c, i * 0x13 + 0x39, font1, 0x10);
                font_no(citysup, 0x20, "%", x_is + 0x8c, i * 0x13 + 0x39, font1, 0x10);
                font_list(0x24, 6, x_is + 0x8c, i * 0x13 + 0x39, font1, 0x10);
            }
        }
    }

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x6147E
// WIN: 0x004291b5
// Lines 1909–1946
//
// Forum slaves dept: repaper if needed, draw explain panel + outer
// mosaic + title, show current slave count, then a delta line that
// reads as one of three messages keyed on the sign of
// slave_population_change:
//   < 0 : line 2 + abs(delta)
//   > 0 : line 3 + delta
//   = 0 : line 4 (no number)
// Then label row 5, welfare-bill + allocation sub-panels, and two
// bottom button strips.  Tail-merges into the show_buttons + epilogue
// at 0x5e7d3 (which finishes with refresh + set_palette + pop ret).
void forum_slaves_screen(void)
{
    int delta;

    cover_mouse_droppings();
    setup_whole_screen_refresh();

    if (forum_repapering[last_forum_dept] != 0) {
        show_pl8file("forum.pl8",
                     forum_repapering[last_forum_dept]);
    }

    explain_forum();
    show_a_mosaic_frame(0, 0, 0x28, 0xe);
    stone_random_count = 0x20;
    show_a_mosaic_blank(0x10, 0x10, 0x26, 0xc);

    font_list(0x25, 0, 0x18, 0x1a, font2, 0x10);

    x_is = 0;
    font_no(slaves, 0x20, " ", 0x18, 0x42, font1, 0x10);
    font_list(0x25, 1, x_is + 0x18, 0x42, font1, 0x10);

    x_is = 0;
    if (slave_population_change < 0) {
        font_list(0x25, 2, 0x18, 0x53, font1, 0x10);
        font_no(-slave_population_change, 0x20, " ", x_is + 0x18, 0x53, font1, 0x10);
    } else if (slave_population_change > 0) {
        font_list(0x25, 3, 0x18, 0x53, font1, 0x10);
        font_no(slave_population_change,  0x20, " ", x_is + 0x18, 0x53, font1, 0x10);
    } else {
        font_list(0x25, 4, 0x18, 0x53, font1, 0x10);
    }

    font_list(0x25, 5, x_is + 0x18, 0x53, font1, 0x10);

    show_slave_welfare_bill();
    show_slave_allocation();

    show_buttons(0x40, 0x72, slave1_buttons, 2);
    show_buttons(0x1ae, 0x26, slave2_buttons, 0xc);

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);
}

// FUNCTION: C2 0x61661
// WIN: 0x004293ea
// Lines 1953–1979
//
// Slave-welfare summary panel.  Calls slave_estimate() to
// refresh the projected slave population, then paints:
//   * A 0x18-wide 1-row header strip at (0x10, 0x71).
//   * A 5-row body strip at (0x10, 0x79) holding:
//       row 0: label "Bill" + slave_welfare_bill in Dn.
//       row 1: label "This year's slaves".
//       row 2: label "Next year's estimate".
//       row 3: comparison verdict (string 0x25 word 9/0xA/0xB
//             keyed on population change direction) +
//             slave_population_estimate value when below,
//             above, or stable.
//       row 4: "Forecast (" slave_population_final_estimate.
// Tail-merges into setup_refresh_area(0x18, 0x62, 0x14, 9, 1).
void show_slave_welfare_bill(void)
{
    slave_estimate();
    stone_random_count = 0x16;
    show_a_mosaic_blank(0x18, 0x71, 0x10, 1);
    show_a_mosaic_blank(0x18, 0x79, 0x10, 5);

    font_list(0x25, 6, 0x18, 0x7a, font1, 0x10);
    font_no(slave_welfare_bill, 0x20, " Dn",
            0x78, 0x7a, font1, 0x10);
    font_list(0x25, 7, 0x18, 0x8b, font1, 0x10);
    font_list(0x25, 8, 0x18, 0x9c, font1, 0x10);

    x_is = 0;
    if (slave_population_estimate < slaves) {
        font_list(0x25, 9, 0x18, 0xad, font1, 0x10);
        font_no(slave_population_estimate, 0x20, " ",
                x_is + 0x18, 0xad, font1, 0x10);
    } else if (slave_population_estimate > slaves) {
        font_list(0x25, 0xa, 0x18, 0xad, font1, 0x10);
        font_no(slave_population_estimate, 0x20, " ",
                x_is + 0x18, 0xad, font1, 0x10);
    } else {
        font_list(0x25, 0xb, 0x18, 0xad, font1, 0x10);
    }

    x_is = 0;
    font_list(0x4d, 1, 0x18, 0xbe, font1, 0x10);
    font_no(slave_population_final_estimate, 0x20, " ",
            x_is + 0x18, 0xbe, font1, 0x10);

    setup_refresh_area(0x18, 0x62, 0x14, 9, 1);
}

// FUNCTION: C2 0x6182D
// WIN: 0x004295b2
// Lines 1982–2013
//
// Slave-allocation table.  0x15-wide 0xC-high mosaic at
// (0x120, 0x10) holds eight per-industry rows (string 0x25
// words 0xC..0x13) on the left, then a per-row pair of
// current / max values at columns 0x1EA / 0x21A.  Each row
// has a 0x14x0x50 dias frame; rows are at y = i*0x18 + 0x12.
// Row 5 is special: if c2inf+0x35 (slaves-unavailable flag)
// is non-zero, replace the numeric values with the
// "unavailable" word 0x15.  Tail-merges to
// setup_refresh_area(0x18E, 6, 0x17, 0xE, 1) into the
// 0x5F73D pop epilogue.
//
// Byte-exact after matching the unavailable-row y position to
// the normal value rows (i * 0x18 + 0x16).
void show_slave_allocation(void)
{
    int i;

    stone_random_count = 0xc;
    show_a_mosaic_blank(0x120, 0x10, 0x15, 0xc);

    font_list(0x25, 0xc, 0x118, 0x16, font1, 0x10);
    font_list(0x25, 0xd, 0x118, 0x2e, font1, 0x10);
    font_list(0x25, 0xe, 0x118, 0x46, font1, 0x10);
    font_list(0x25, 0xf, 0x118, 0x5e, font1, 0x10);
    font_list(0x25, 0x10, 0x118, 0x76, font1, 0x10);
    font_list(0x25, 0x11, 0x118, 0x8e, font1, 0x10);
    font_list(0x25, 0x12, 0x118, 0xa6, font1, 0x10);
    font_list(0x25, 0x13, 0x118, 0xbe, font1, 0x10);

    for (i = 0; i < 7; i++) {
        draw_a_dias(0x216, i * 0x18 + 0x12, 0x50, 0x14);
        if (i >= 5 && c2inf.peace_mode != 0) {
            font_list(0x25, 0x15, 0x1ea, i * 0x18 + 0x16, font1, 0x10);
            font_list(0x25, 0x15, 0x21a, i * 0x18 + 0x16, font1, 0x10);
        } else {
            font_no(slave_requirements[i].current, 0x20, " ",
                    0x1ea, i * 0x18 + 0x16, font1, 0x10);
            x_is = 0;
            font_list(0x25, 0x14, 0x21a, i * 0x18 + 0x16, font1, 0x10);
            font_no(slave_requirements[i].max, 0x20, " ",
                    x_is + 0x21a, i * 0x18 + 0x16, font1, 0x10);
        }
    }

    font_no(slave_requirements[i].current, 0x20, " ",
            0x1ea, i * 0x18 + 0x16, font1, 0x10);

    setup_refresh_area(0x18e, 6, 0x17, 0xe, 1);
}

// FUNCTION: C2 0x61A99
// WIN: 0x00429825
// Lines 2019–2097
//
// Year-end report screen.  Cover the cursor, request a full
// redraw, frame the outer mosaic at (0x10, 0x30) 0x1C wide,
// 0xF tall; inner blank at (0x20, 0x40) 0x1A x 0xD; exit
// button at (0x1A4, 0xF4); speech dias at (0x30, 0x70)
// 0x180x0x70.
//
// Title block at (0x30, 0x4C): font2 string 0x49 word 0
// ("Year-end report") + font1 word 1 subtitle.
//
// Four stat rows at y = 0x80 / 0x92 / 0xA4 / 0xB6, each:
//   * label (string 0x49 word 3/4/5/6) at x = 0x40
//   * current value (font_no) right after label
//   * delta column at x = 0x120: "up by" word 7 + (this -
//     last) in white, or "down by" word 8 + (last - this)
//     in red (font2 colour 0xB).
// Tracked metrics: this_years_population, this_years_denarii,
// this_years_pop_tax, this_years_ind_tax (vs last_years_*).
//
// Body paragraph: font_format_split(0x49, 2, 0x30, 0xF0,
// 0x12C, 0x64, 0, 0, font1, 0x10).
// Then hold_mouse_replace = 1; refresh_svga_screen();
void show_year_end_screen(void)
{
    cover_mouse_droppings();
    setup_whole_screen_refresh();
    stone_random_count = 0xf;
    show_a_mosaic_frame(0x10, 0x30, 0x1c, 0xf);
    show_a_mosaic_blank(0x20, 0x40, 0x1a, 0xd);
    show_an_exit_button(0x1a4, 0xf4);
    draw_a_dias(0x30, 0x70, 0x180, 0x70);

    x_is = 0;
    font_list(0x49, 0, 0x30, 0x4c, font2, 0x10);
    font_list(0x49, 1, x_is + 0x30, 0x54, font1, 0x10);

    x_is = 0;
    font_list(0x49, 3, 0x40, 0x80, font1, 0x10);
    font_no(this_years_population, 0x20, " ",
            x_is + 0x40, 0x80, font1, 0x10);
    x_is = 0;
    if (this_years_population >= last_years_population) {
        font_list(0x49, 7, 0x120, 0x80, font1, 0x10);
        font_no(this_years_population - last_years_population,
                0x20, ")", x_is + 0x120, 0x80, font1, 0x10);
    } else {
        font_list(0x49, 8, 0x120, 0x80, font1, 0xb);
        font_no(last_years_population - this_years_population,
                0x20, ")", x_is + 0x120, 0x80, font1, 0xb);
    }

    x_is = 0;
    font_list(0x49, 4, 0x40, 0x92, font1, 0x10);
    if (this_years_denarii >= 0)
        font_no(this_years_denarii, 0x20, "Dn",
                x_is + 0x40, 0x92, font1, 0x10);
    else
        font_no(-this_years_denarii, 0x2d, "Dn",
                x_is + 0x40, 0x92, font1, 0xb);
    x_is = 0;
    if (this_years_denarii >= last_years_denarii) {
        font_list(0x49, 7, 0x120, 0x92, font1, 0x10);
        font_no(this_years_denarii - last_years_denarii,
                0x20, "Dn)", x_is + 0x120, 0x92, font1, 0x10);
    } else {
        font_list(0x49, 8, 0x120, 0x92, font1, 0xb);
        font_no(last_years_denarii - this_years_denarii,
                0x20, "Dn)", x_is + 0x120, 0x92, font1, 0xb);
    }

    x_is = 0;
    font_list(0x49, 5, 0x40, 0xa4, font1, 0x10);
    font_no(this_years_pop_tax, 0x20, "Dn",
            x_is + 0x40, 0xa4, font1, 0x10);
    x_is = 0;
    if (this_years_pop_tax >= last_years_pop_tax) {
        font_list(0x49, 7, 0x120, 0xa4, font1, 0x10);
        font_no(this_years_pop_tax - last_years_pop_tax,
                0x20, "Dn)", x_is + 0x120, 0xa4, font1, 0x10);
    } else {
        font_list(0x49, 8, 0x120, 0xa4, font1, 0xb);
        font_no(last_years_pop_tax - this_years_pop_tax,
                0x20, "Dn)", x_is + 0x120, 0xa4, font1, 0xb);
    }

    x_is = 0;
    font_list(0x49, 6, 0x40, 0xb6, font1, 0x10);
    font_no(this_years_ind_tax, 0x20, "Dn",
            x_is + 0x40, 0xb6, font1, 0x10);
    x_is = 0;
    if (this_years_ind_tax >= last_years_ind_tax) {
        font_list(0x49, 7, 0x120, 0xb6, font1, 0x10);
        font_no(this_years_ind_tax - last_years_ind_tax,
                0x20, "Dn)", x_is + 0x120, 0xb6, font1, 0x10);
    } else {
        font_list(0x49, 8, 0x120, 0xb6, font1, 0xb);
        font_no(last_years_ind_tax - this_years_ind_tax,
                0x20, "Dn)", x_is + 0x120, 0xb6, font1, 0xb);
    }

    font_format_split(0x49, 2, 0x30, 0xf0, 0x12c, 0x64,
                      0, 0, font1, 0x10);
    hold_mouse_replace = 1;
    refresh_svga_screen();
}

// FUNCTION: C2 0x61FAD
// WIN: 0x00429d9f
// Lines 2102–2161
//
// Repaint the top-of-screen status bar (date + treasury).
// Driven by four "dirty" inputs: a 40-tick countdown in
// request_message+0x40 toggles the slave-warning blink flag
// at +0x44, redraw_topline forced refresh, month change vs
// the per-frame snapshot at +0x58, denarii change vs +0x50.
// If any of these changed, clear the topline rect, optionally
// chime when the slave-warning blink rolls over (8-tick beat
// playing a09.wav), and redraw the date string + denarii
// number (in white normally, in red when negative).  The
// battle map (map_mode == 2) suppresses the year/month/denarii
// drop — only the slave-warning blink stays alive.
void show_top_line(void)
{
    char dirty = 0;

    if (--request_message.alarm_blink_timer <= 0) {
        request_message.alarm_blink_state ^= 1;
        request_message.alarm_blink_timer = 0x28;
        dirty = 1;
    }
    if (redraw_topline != 0)                                  dirty = 1;
    if (request_message.cached_month != month)   dirty = 1;
    if (request_message.cached_denarii != denarii) dirty = 1;
    if (!dirty)
        return;

    redraw_topline = 0;
    request_message.cached_month = month;
    request_message.cached_denarii = denarii;

    sprite_width  = 0x15;
    sprite_height = 0xf;
    show_fast_rect(0x12e, 5, 0x1a);

    if (pointer_mode == 5)
        request_message.alarm_blink_state = 1;

    if (slave_warning == 0
        || request_message.alarm_blink_state != 0
        || map_mode == 2) {
        show_date(year, 0x130, 6, 0);
        font_list(0x19, month, x_is + 0x138, 6, font1, 0x10);
    } else {
        font_list(9, 3, 0x138, 6, font1, 0xb);
        if (++request_message.alarm_chime_counter >= 8) {
            request_message.alarm_chime_counter = 0;
            set_pri_sound("a09.wav", 1);
        }
    }
    if (map_mode != 2) {
        if (denarii < 0)
            font_no(-denarii, 0x2d, " Dn",
                    0x230, 6, font1, 0xb);
        else
            font_no(denarii, 0x20, " Dn",
                    0x230, 6, font1, 0x10);
    }

    setup_refresh_area(0xeb, 0, 0x1a, 2, 1);
}

// FUNCTION: C2 0x62177
// WIN: 0x00429f9c
// Lines 2163–2219
//
// Repaint the bottom-of-screen icon / cost status strip.
// One of three things is shown (in priority order):
//
//   1. total_build_cost (active road / wall / etc. placement)
//      — always shown as cost, no oscillation.
//   2. While hovering an active placeable (pm_over) with a
//      non-zero placing_cost: oscillate per-32-frames between
//      the cost ("N Dn") and the placeable's name string.
//      icon_strip_toggle wraps at 0x40.
//   3. Otherwise: the last hovered icon's name string
//      (last_icon_over), unless the topline is mid-redraw —
//      in which case the last-used icon is shown instead.
//
// Skipped entirely when the cached (cost, text_id) pair in
// request_message+0x5C / +0x60 already matches what we'd stamp.
//
// On a cost-flavour redraw, the value cache is updated and
// text-cache is invalidated to -1.  On a text-flavour redraw,
// cost is invalidated to -1 and the text-cache is updated.
// Final tail jmp to setup_refresh_area(0x1E0, 0x10B, 0xA, 2, 1).
void show_icon_strip(void)
{
    int any_text;
    int has_sel;
    int has_cost;
    int cost;
    int text_id;

    if (pointer_mode > 0)
        icon_strip_toggle = 0x21;

    any_text = 0;
    has_sel  = 0;
    has_cost = 0;
    cost     = 0;
    if (total_build_cost != 0) {
        has_cost = 1;
        cost     = total_build_cost;
    } else if (pm_over != 0) {
        if (placing_cost != 0) {
            icon_strip_toggle = icon_strip_toggle + 1;
            if (icon_strip_toggle > 0x40) icon_strip_toggle = 0;
            if (icon_strip_toggle == 0x20) any_text = 1;
            if (icon_strip_toggle < 0x20) {
                has_cost = 1;
                cost     = placing_cost;
            } else if (selected_icon_no != 0) {
                int sel = selected_icon_no;
                text_id  = sel - 1;
                has_sel  = 1;
            } else {
                text_id = last_icon_used;
            }
        } else {
            text_id = last_icon_used;
        }
    } else if (redraw_topline != 0) {
        text_id = last_icon_used;
    } else if (last_icon_over == 0) {
        text_id = last_icon_used;
    } else {
        if (last_icon_over == 0) {
        } else {
            text_id = last_icon_over;
        }
    }

    if (!(any_text == 1)) {
        if (has_cost != 0
            && cost == request_message.cached_cost)
            return;
        if (text_id == request_message.cached_text_id)
            return;
    }

    sprite_width  = 9;
    sprite_height = 0xf;
    show_fast_rect(0x1e8, 0x10b, 0x1a);

    if (has_cost != 0) {
        request_message.cached_text_id = -1;
        x_is = 0;
        font_list(0x34, 0, 0x1ea, 0x10c, font1, 0x10);
        font_no(cost, 0x20, " Dn",
                x_is + 0x1ea, 0x10d, font1, 0x10);
        request_message.cached_cost = cost;
    } else {
        request_message.cached_cost = -1;
        if (map_mode == 0) {
            if (has_sel != 0)
                font_list(selected_icon_text, text_id, 0x1ea,
                          0x10c, font1, 0x10);
            else
                font_list(0x32, text_id, 0x1ea, 0x10c, font1, 0x10);
        } else if (has_sel != 0) {
            font_list(selected_icon_text, text_id, 0x1ea,
                      0x10c, font1, 0x10);
        } else {
            font_list(0x33, text_id, 0x1ea, 0x10c, font1, 0x10);
        }
        request_message.cached_text_id = text_id;
    }

    setup_refresh_area(0x1e0, 0x10b, 0xa, 2, 1);
}

// FUNCTION: C2 0x62366
// WIN: 0x0042a299
// Lines 2222–2237
//
// Redraw the small overview-mode selector bar when the city map top
// line is dirty or the ov-bar countdown requests an update.
void show_ov_bar(void)
{
    int h;
    int w;

    if (map_mode != 0) return;
    if (redraw_topline == 0 && update_ov_bar == 0) return;

    if (update_ov_bar != 0) {
        update_ov_bar--;
    }
    sprite_width = 6;
    h = 0xf;
    sprite_height = h;
    show_fast_rect(0x1e2, 0x1c, 0x1a);
    w = 1;
    sprite_width = w;
    sprite_height = h;
    show_fast_rect(0x23c, 0x1c, 0x1a);
    font_list(0x35, ov_map_mode, 0x1e4, 0x1d, font1, 0x10);
    draw_a_line(0x1de, 0x30, 0x1de, 0xd0, 0x1f);
    draw_a_line(0x1df, 0x30, 0x1df, 0xd0, 0x12);
    setup_refresh_area(0x1e0, 0x1c, 0xa, 2, w);
}

// FUNCTION: C2 0x62462
// WIN: 0x0042a52e
// Lines 2239–2265
//
// Repaint the city-map overlay legend bar at y=0x30 when the
// player has opened an analysis overlay (ov_map_mode 1..9).
// Frame the right-hand strip, draw the overlay's name (string
// 0x35 word ov_map_mode) and description (string 0x35 word
// ov_map_mode+0xC), then dispatch to the correct
// place_*_legend_blocks helper:
//   mode 1, 6     → place_9_legend_blocks (3x3 colour grid)
//   mode 3, 5, 9  → place_3x_legend_blocks (3 wide swatches)
//   mode 2, 4, 7  → place_3_legend_blocks (3 colour pips)
// After the dispatch, clear overlays_on so the next click
// refresh-paints the city-map; setup_whole_screen_refresh
// requests the redraw.
void show_ov_legend_panel(void)
{
    cover_mouse_droppings();
    stone_random_count = 0xa;
    overlays_on = 1;
    show_citymap();

    show_a_system_blank(0x1e0, 0x30, 0xa, 0xa);
    draw_a_box(0x1e1, 0x31, 0x9e, 0x9e, 0x10);
    draw_a_box(0x1e5, 0x35, 0x96, 0x14, 0x10);

    x_is = 0;
    font_list(0x35, ov_map_mode, 0x1ec, 0x38, font1, 0x10);
    font_list(0x35, 0xb, x_is + 0x1ec, 0x38, font1, 0x10);
    font_format_split(0x35, ov_map_mode + 0xc, 0x1e5, 0x50, 0x96, 0x64,
                      0, 0, font1, 0x10);

    if (ov_map_mode == 1) {
        place_9_legend_blocks();
    } else if (ov_map_mode == 2) {
        place_3_legend_blocks(0x19, 0x84, 0x8d, 0x87);
    } else if (ov_map_mode == 3) {
        place_3x_legend_blocks(0x20, 0x93, 0x90, 0x8d);
    } else if (ov_map_mode == 4) {
        place_3_legend_blocks(0x16, 0x79, 0x78, 0x77);
    } else if (ov_map_mode == 5) {
        place_3_legend_blocks(0x16, 0x93, 0x90, 0x8d);
    } else if (ov_map_mode == 6) {
        place_9_legend_blocks();
    } else if (ov_map_mode == 7) {
        place_3_legend_blocks(0x1c, 0x84, 0x8d, 0x87);
    } else if (ov_map_mode == 8) {
        place_3_legend_blocks(0x16, 0x79, 0x78, 0x77);
    } else if (ov_map_mode == 9) {
        place_3_legend_blocks(0x16, 0x93, 0x90, 0x8d);
    }

    overlays_on = 0;
    hold_mouse_replace = 1;
    setup_whole_screen_refresh();
    refresh_svga_screen();
}

// FUNCTION: C2 0x62634
// WIN: 0x0042a5f3
// Lines 2269–2277
//
// Sister of place_3x_legend_blocks: same 3-column legend layout, but
// captions use ascending paragraph numbers p1, p1+1, p1+2 (instead of
// descending).
void place_3_legend_blocks(int p1, int p2, int p3, int p4)
{
    place_legend_block(p2, 0x1e8, 0x92);
    place_legend_block(p3, 0x1e8, 0xa6);
    place_legend_block(p4, 0x1e8, 0xba);
    font_list(0x35, p1,     0x200, 0x94, font1, 0x10);
    font_list(0x35, p1 + 1, 0x200, 0xa8, font1, 0x10);
    font_list(0x35, p1 + 2, 0x200, 0xbc, font1, 0x10);
}

// FUNCTION: C2 0x626C9
// WIN: 0x0042a6a1
// Lines 2279–2286
//
// Render the 3-column legend block for the empire-overview
// screen: three sprite tiles stacked vertically at x = 0x1e8 (sprite
// id taken from p2 / p3 / p4), captioned with three paragraph numbers
// p1, p1-1, p1-2 in font1.
void place_3x_legend_blocks(int p1, int p2, int p3, int p4)
{
    place_legend_block(p2, 0x1e8, 0x92);
    place_legend_block(p3, 0x1e8, 0xa6);
    place_legend_block(p4, 0x1e8, 0xba);
    font_list(0x35, p1,     0x200, 0x94, font1, 0x10);
    font_list(0x35, p1 - 1, 0x200, 0xa8, font1, 0x10);
    font_list(0x35, p1 - 2, 0x200, 0xbc, font1, 0x10);
}

// FUNCTION: C2 0x6274C
// WIN: 0x0042a74f
// Lines 2289–2294
//
// Render a 9-block legend strip: sprite indices 0x7e,0x81,...,0x96
// at x positions 0x1e8,0x1f8,...,0x268 and y=0x92, then place the
// two caption strings (paragraphs 0x16 and 0x18) to the right.
void place_9_legend_blocks(void)
{
    int i;

    for (i = 0; i < 9; i++) {
        place_legend_block(i * 3 + 0x7e, i * 16 + 0x1e8, 0x92);
    }
    font_list(0x35, 0x16, 0x1f0, 0xaa, font1, 0x10);
    font_list(0x35, 0x18, 0x250, 0xaa, font1, 0x10);
}

// FUNCTION: C2 0x627B6
// WIN: 0x0042a7d8
// Lines 2297–2306
//
// Stamp one 16x16 legend tile at (x, y): paints 64 2x2 blocks from
// the landfill sprite at sprite_idx, then frames it with a 0x10
// border.
void place_legend_block(int sprite_idx, int x, int y)
{
    int xo;
    int yo;
    sprite_start = landfill[sprite_idx * 16 + 0xC]
                 + (landfill[sprite_idx * 16 + 0xD] << 8);
    for (yo = 0; yo < 16; yo += 2) {
        for (xo = 0; xo < 16; xo += 2) {
            place_2x2_block((int)landfill + sprite_start,
                            (x + xo) + (y + yo) * screen_width);
        }
    }
    draw_a_box(x - 1, y - 1, 0x12, 0x12, 0x10);
}

// FUNCTION: C2 0x62828
// WIN: 0x0042a88d
// Lines 2308–2327
//
// Print a year number followed by the date-era label from string list
// 0x1a.  Negative years use label 0, non-negative years label 1;
// mode 2 uses highlight colour 0x3f, modes 0/1 use colour 0x10.
void show_date(int year, int x, int y, int mode)
{
    x_is = 0;
    if (mode == 0) {
        if (year < 0) {
            font_no(-year, 0x20, " ", x, y, font1, 0x10);
            font_list(0x1a, 0, x + x_is, y, font1, 0x10);
        } else {
            font_no(year, 0x20, " ", x, y, font1, 0x10);
            font_list(0x1a, 1, x + x_is, y, font1, 0x10);
        }
    } else if (mode == 1) {
        if (year < 0) {
            font_no(-year, 0x20, " ", x, y, font1, 0x10);
            font_list(0x1a, 0, x + x_is, y, font1, 0x10);
        } else {
            font_no(year, 0x20, " ", x, y, font1, 0x10);
            font_list(0x1a, 1, x + x_is, y, font1, 0x10);
        }
    } else if (mode == 2) {
        if (year < 0) {
            font_no(-year, 0x20, " ", x, y, font1, 0x3f);
            font_list(0x1a, 0, x + x_is, y, font1, 0x3f);
        } else {
            font_no(year, 0x20, " ", x, y, font1, 0x3f);
            font_list(0x1a, 1, x + x_is, y, font1, 0x3f);
        }
    }
}

// FUNCTION: C2 0x62911
// WIN: 0x0042aa89
// Lines 2331–2347
//
// The census mini-panel — a small mosaic window with the city's
// current population, employment rate, and a couple of label rows.
// Lays out from y = 0x70 downward inside a 0x50,0x60,0xb,0x14 window
// and chains the shared refresh_svga_screen + hold_mouse_replace
// epilogue.
void show_census_panel(void)
{
    cover_mouse_droppings();
    stone_random_count = 0x1c;

    show_a_mosaic_window(0x50, 0x60, 0x14, 0xb);
    setup_whole_screen_refresh();
    show_an_exit_button(0x160, 0xe0);

    font_list(0x4b, 0,    0x70, 0x78, font2, 0x10);
    font_list(0x4b, 1,    0x70, 0x94, font1, 0x10);

    x_is = 0;
    font_list(0x4b, 2,    0x70, 0xb8, font1, 0x10);
    font_no(population,      0x20, " ",
            x_is + 0x70, 0xb8, font1, 0x10);

    x_is = 0;
    font_list(0x4b, 3,    0x70, 0xd0, font1, 0x10);
    font_no(employment_rate, 0x20, "%",
            x_is + 0x70, 0xd0, font1, 0x10);

    font_list(9,    1,    0x90, 0xf0, font1, 0x10);

    refresh_svga_screen();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x62A51
// WIN: 0x0042abb8
// Lines 2353–2369
//
// Draw/update the turbo-mode population panel.  If the cached
// population is unchanged and turbo_mode is already past the setup
// states, the panel is left alone.
void show_turbo_panel(void)
{
    if (request_message.cached_population == population) {
        if (turbo_mode > 2) return;
    }

    stone_random_count = 0x1c;
    show_a_mosaic_window(0x50, 0x60, 0x14, 0xb);
    setup_whole_screen_refresh();
    show_an_exit_button(0x160, 0xe0);
    font_list(0x4c, 0, 0x70, 0x78, font2, 0x10);
    font_format_split(0x4c, 1, 0x70, 0xa0, 0xf0, 0x64, 0, 0, font1, 0x10);
    x_is = 0;
    font_no(population, 0x20, " ", 0x70, 0xe4, font1, 0x10);
    font_list(0x1e, 1, x_is + 0x70, 0xe4, font1, 0x10);
    request_message.cached_population = population;
}

// FUNCTION: C2 0x62B49
// WIN: 0x0042aca8
// Lines 2371–2376
//
// Reset the query panel UI: enable button index 0x54,
// clear query mode and queried person.
void init_queery_panel(void)
{
    queery_buttons[3].state = 1;
    query_mode = 0;
    queried_person = 0;
}

// FUNCTION: C2 0x62B61
// WIN: 0x0042acce
// Lines 2378–2386
//
// Draw the small lower-right help panel shown while the pointer is in
// query mode.
void show_querymode_panel(void)
{
    if (pointer_mode == 4) {
        show_a_system_window(0x1df, 0x170, 0xa, 7);
        font_list(0x4a, 0, 0x1e8, 0x17c, font2, 0x10);
        font_list(0x4a, 1, 0x21a, 0x19a, font2, 0x10);
        font_format_split(0x4a, 2, 0x1e8, 0x1b8, 0x98, 0x64, 0, 0, font1, 0x10);
        setup_refresh_area(0x1de, 0x16e, 0xb, 8, 1);
    }
}

// FUNCTION: C2 0x62C14
// WIN: 0x0042ad66
// Lines 2388–2417
//
// Top-level dispatcher for the query panel.  Picks the
// query_panel_reduction (vertical shrink in 16-pixel mosaic units)
// based on the active map_mode / query_mode / q_type combo, draws
// the panel frame + blank + exit button + side buttons + dias, then
// fans out to the appropriate inner show_*_query_panel renderer.
void show_query_panel(void)
{
    int heading_y;

    cover_mouse_droppings();
    stone_random_count = 0x1c;

    if (map_mode == 1) {
        query_panel_reduction = 9;
    }
    else if (query_mode == 2) {
        query_panel_reduction = 0;
    }
    else if (query_mode == 1) {
        query_panel_reduction = 7;
    }
    else if (q_type == 0xfa) {
        query_panel_reduction = 5;
    }
    else {
        query_panel_reduction = 9;
    }

    show_a_mosaic_frame(8, 0x20 + query_panel_reduction * 16,
                        0x1c, 0x1b - query_panel_reduction);
    setup_whole_screen_refresh();
    show_a_mosaic_blank(0x18, 0x30 + query_panel_reduction * 16,
                        0x1a, 0x19 - query_panel_reduction);
    show_an_exit_button(0x198, 0x1a0);
    show_buttons(8, 0x20, queery_buttons, nof_query_buttons);
    draw_a_dias(0x20, 0xa0 + query_panel_reduction * 16, 0x190,
                (0xf - query_panel_reduction) * 16);

    heading_y = query_panel_reduction * 16 + 0x48;
    if (map_mode == 0) {
        show_query_panel_heading(heading_y);
        if (query_mode == 2) {
            show_detailed_query_panel();
        }
        else if (query_mode == 1) {
            show_people_query_panel();
        }
        else {
            show_general_query_panel();
        }
    }
    else {
        show_region_query_panel(heading_y);
    }

    refresh_svga_screen();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x62D6E
// WIN: 0x0042af17
// Lines 2420–2443
//
// Draw the heading rows for the query panel.  Buckets q_type into a
// help/string index, picks one of two font_list calls (special-cased
// for q_type 0xfa = goods), latches city_mm_enties[bucket] into
// this_help_page, then draws either a single label row (when
// q_lv <= 0) or label + number (when q_lv > 0).
void show_query_panel_heading(int y)
{
    int qt;
    int bucket;
    int y2;

    y2 = y;
    qt = q_type;
    if      (qt < 8)    bucket = 7;
    else if (qt < 0x1e) bucket = 8;
    else if (qt < 0x4e) bucket = 6;
    else if (qt < 0x78) bucket = 1;
    else if (qt < 0x7c) bucket = 0;
    else if (qt < 0x7d) bucket = 4;
    else if (qt < 0x82) bucket = 5;
    else if (qt == 0xfa) bucket = 2;
    else                bucket = qt - 0x78;

    if (q_type == 0xfa) {
        font_list(0x3e, q_goods, 0x98, y2, font2, 0x10);
    } else {
        font_list(0x3c, bucket, 0x98, y2, font2, 0x10);
    }

    this_help_page = city_mm_enties[bucket];
    y2 += 0x20;

    if (q_lv <= 0) {
        font_list(0x3d, 0, 0x98, y2, font2, 0x10);
        return;
    }
    x_is = 0;
    font_list(0x3d, 1, 0x98, y2, font2, 0x10);
    font_no(q_lv, 0x20, " ", x_is + 0x98, y2, font2, 0x10);
}

// FUNCTION: C2 0x62EB6
// WIN: 0x0042b109
// Lines 2447–2508
//
// Right-click query dispatcher — inspect a city-map tile.
// Forwards to specialised panels for house tiles
// (q_type 0x82..0xA1 → show_query_house_advice) and
// business tiles (q_type 0xFA → show_query_business_advice).
//
// For everything else, picks a help-paragraph word `esi`
// from a per-tile-range lookup table, then renders it via
// font_format_split into the panel column.  Tiles that
// require road access (q_road_access) fall back to a
// different word (0x52 "needs road" / 0x53 "needs hospital")
// when access is missing.  For hospital queries
// (q_type == 0xF5 / 0xFB) at the road-access threshold a
// secondary numeric reading is also stamped (1000 / 1200
// citizens served, font_no + string 0x3D word 0x5B label).
void show_general_query_panel(void)
{
    int q;
    int word;

    q = q_type;
    if (q >= 0x82 && q < 0xa2) {
        show_query_house_advice();
        return;
    }

    q = q_type;
    if (q == 0xfb || q == 0xf5) {
        if (!q_road_access)        word = 0x5a;
        else if (q_hospital_access) word = 0x52;
        else                        word = 0x53;
    } else if (q == 0xfa) {
        show_query_business_advice();
        return;
    } else if (q == 0x7c) {
        word = 0x24;
    } else if (q == 0x7d) {
        word = 0x25;
    } else if (q == 0x7e) {
        word = 0x26;
    } else if (q >= 0x82) {
        if (q <= 0xa5) {
            word = (unsigned char)q;
            word -= 0x7b;
        } else if (q <= 0xa9) {
            word = (unsigned char)q;
            word -= 0x7f;
        } else if (q <= 0xad) {
            word = (unsigned char)q;
            word -= 0x83;
        } else if (q <= 0xb1) {
            if (!q_road_access)        word = 0x5a;
            else {                     word = (unsigned char)q; word -= 0x87; }
        } else if (q <= 0xb5) {
            if (!q_road_access)        word = 0x5a;
            else {                     word = (unsigned char)q; word -= 0x8b; }
        } else if (q <= 0xb9) {
            if (!q_road_access)        word = 0x5a;
            else {                     word = (unsigned char)q; word -= 0x8f; }
        } else if (q >= 0xd7) {
            if (q <= 0xda) {
                word = (unsigned char)q;
                word -= 0xb0;
            } else if (q <= 0xe2) {
                if (!q_supply) {
                    word = 0x2b;
                } else if (q <= 0xde) {
                    word = q - 0xb4;
                } else if (q <= 0xe2) {
                    word = q - 0xb8;
                }
            } else if (q < 0xe5) {
                if (!q_road_access) word = 0x5a;
                else word = 0x23;
            } else if (q >= 0xfc && q <= 0xff) {
                if (!q_road_access) word = 0x5a;
                else {              word = q - 0xd0; }
            } else {
                word = 0x23;
            }
        } else {
            word = 0x23;
        }
    } else {
        word = 0x23;
    }

    font_format_split(0x3d, word, 0x38,
                      (query_panel_reduction + 9) * 0x10 + 0x20, 0x160, 0x64,
                      0, 0, font1, 0x10);

    if (word == 0x52) {
        x_is = 0;
        if (q_type == 0xfb) {
            font_no(0x3e8, 0x20, " ", 0x38,
                    (query_panel_reduction + 0xa) * 0x10 + 0x20, font1, 0x10);
        } else {
            font_no(0x4b0, 0x20, " ", 0x38,
                    (query_panel_reduction + 0xa) * 0x10 + 0x20, font1, 0x10);
        }
        font_list(0x3d, 0x5b, x_is + 0x38,
                  (query_panel_reduction + 0xa) * 0x10 + 0x20
                      + (font1[0] - font1[0]), font1, 0x10);
    }
}

// FUNCTION: C2 0x63169
// WIN: 0x0042b5ad
// Lines 2510–2558
//
// House-tile query advice.  Picks one of ~30 help-paragraph
// words from string 0x3D based on a per-level requirement
// state machine.  Two byte values at
// promotion_av_levels[q_type*2 + 0x186] and +0x187 give
// the next-level (esi) and demote (ecx) thresholds.
//
// Decision tree (q_lv compared in order):
//   * q_lv > demote_thresh   → word 0x57 (downgrade warning).
//   * No aqua / sub_aqua at q_lv == 2 → word 0x3D.
//   * No admin   at lv 6  → word 0x3E.
//   * No business at lv 0xA → word 0x40.
//   * No market  at lv 0xC → word 0x3F.
//   * No aqua    at lv 0xE → word 0x41.
//   * No business_low at lv 0x10 → word 0x4F.
//   * No baths   at lv 0x12 → word 0x42.
//   * No entertainment at lv 0x14 → word 0x43.
//   * No barracks at lv 0x18 → word 0x44.
//   * No security at lv 0x18 → word 0x45.
//   * No business_vlow at lv 0x1A → word 0x50.
//   * Entertainment <= 1 at lv 0x1A         → word 0x43.
//   * No wall    at lv 0x1A → word 0x46.
//   * Entertainment <= 2 at lv 0x1C         → word 0x43.
//   * No gate    at lv 0x1E → word 0x47.
//   * hospital_cover < 20 at lv 0x1E        → word 0x4A.
//   * Entertainment <= 3 at lv 0x20         → word 0x43.
//   * No grammaticus at lv 0x22 → word 0x48.
//   * No prefecture  at lv 0x22 → word 0x49.
//   * hospital_cover < 40 at lv 0x24        → word 0x4A.
//   * Entertainment <= 4 at lv 0x26         → word 0x43.
//   * No near_market at higher levels → word 0x53.
//   * ... and so on through lvl 0x40 + various boundary
//     checks.
// Default (no missing requirement found): word 0x51
// ("residents satisfied / next upgrade").
//
// After rendering the body paragraph, if q_lv >= esi (next-level
// threshold) the function returns.  Otherwise stamp a sub-line
// (word 0x56, font colour 0xD) at
// (0x48, query_panel_reduction * 0x10 + 0x88) showing the
// missing-requirement promotion hint.
void show_query_house_advice(void)
{
    int q = q_type;
    int next_lv;
    int demote_lv;
    int word;

    next_lv = (((signed char *)promotion_av_levels)[(q) * 2 + 0x186]);
    demote_lv = (((signed char *)promotion_av_levels)[(q) * 2 + 0x187]);

    if (q_lv > demote_lv)              { word = 0x57; goto render; }
    if (!q_aqua && !q_sub_aqua) {
        if (q_lv == 2)                  word = 0x3d;
        else                                word = 0x3c;
        goto render;
    }
    if (!q_admin) {
        if (q_lv == 6)                  word = 0x3e;
        else                                word = 0x3c;
        goto render;
    }
    if (q_business) {
        if (q_lv == 0xa)                word = 0x40;
        else                                word = 0x3c;
        goto render;
    }
    if (!q_market) {
        if (q_lv == 0xc)                word = 0x3f;
        else                                word = 0x3c;
        goto render;
    }
    if (!q_aqua) {
        if (q_lv == 0xe)                word = 0x41;
        else                                word = 0x3c;
        goto render;
    }
    if (q_business_low) {
        if (q_lv == 0x10)               word = 0x4f;
        else                                word = 0x3c;
        goto render;
    }
    if (!q_baths) {
        if (q_lv == 0x12)               word = 0x42;
        else                                word = 0x3c;
        goto render;
    }
    if (!q_entertainment) {
        if (q_lv == 0x14)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (q_barracks) {
        if (q_lv == 0x18)               word = 0x44;
        else                                word = 0x3c;
        goto render;
    }
    if (!q_security) {
        if (q_lv == 0x18)               word = 0x45;
        else                                word = 0x3c;
        goto render;
    }
    if (q_business_vlow) {
        if (q_lv == 0x1a)               word = 0x50;
        else                                word = 0x3c;
        goto render;
    }
    if (q_entertainment <= 1) {
        if (q_lv == 0x1a)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (q_wall) {
        if (q_lv == 0x1a)               word = 0x46;
        else                                word = 0x3c;
        goto render;
    }
    if (q_entertainment <= 2) {
        if (q_lv == 0x1c)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (q_gate) {
        if (q_lv == 0x1e)               word = 0x47;
        else                                word = 0x3c;
        goto render;
    }
    if (hospital_cover < 0x14) {
        if (q_lv == 0x1e)               word = 0x4a;
        else                                word = 0x3c;
        goto render;
    }
    if (q_entertainment <= 3) {
        if (q_lv == 0x20)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (!q_grammaticus) {
        if (q_lv == 0x22)               word = 0x48;
        else                                word = 0x3c;
        goto render;
    }
    if (q_prefecture) {
        if (q_lv == 0x22)               word = 0x49;
        else                                word = 0x3c;
        goto render;
    }
    if (hospital_cover < 0x28) {
        if (q_lv == 0x24)               word = 0x4a;
        else                                word = 0x3c;
        goto render;
    }
    if (q_entertainment <= 4) {
        if (q_lv == 0x26)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (q_near_market) {
        if (q_lv == 0x28)               word = 0x4c;
        else                                word = 0x3c;
        goto render;
    }
    if (q_security <= 1) {
        if (q_lv == 0x2a)               word = 0x4d;
        else                                word = 0x3c;
        goto render;
    }
    if (hospital_cover < 0x3c) {
        if (q_lv == 0x2c)               word = 0x4a;
        else                                word = 0x3c;
        goto render;
    }
    if (q_entertainment <= 5) {
        if (q_lv == 0x2c)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (!q_rhetor) {
        if (q_lv == 0x2e)               word = 0x4b;
        else                                word = 0x3c;
        goto render;
    }
    if (library_cover < 0x14) {
        if (q_lv == 0x2e)               word = 0x4e;
        else                                word = 0x3c;
        goto render;
    }
    if (q_entertainment <= 6) {
        if (q_lv == 0x30)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (library_cover < 0x28) {
        if (q_lv == 0x32)               word = 0x4e;
        else                                word = 0x3c;
        goto render;
    }
    if (hospital_cover < 0x50) {
        if (q_lv == 0x34)               word = 0x4a;
        else                                word = 0x3c;
        goto render;
    }
    if (library_cover < 0x3c) {
        if (q_lv == 0x36)               word = 0x4e;
        else                                word = 0x3c;
        goto render;
    }
    if (q_entertainment <= 7) {
        if (q_lv == 0x38)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (hospital_cover < 0x64) {
        if (q_lv == 0x3a)               word = 0x4a;
        else                                word = 0x3c;
        goto render;
    }
    if (library_cover < 0x50) {
        if (q_lv == 0x3a)               word = 0x4e;
        else                                word = 0x3c;
        goto render;
    }
    if (q_entertainment <= 8) {
        if (q_lv == 0x3c)               word = 0x43;
        else                                word = 0x3c;
        goto render;
    }
    if (library_cover < 0x64) {
        if (q_lv == 0x3e)               word = 0x4e;
        else                                word = 0x3c;
        goto render;
    }
    if (q_lv < 0x40) {
        word = 0x3c;
        goto render;
    }
    word = 0x51;

render:
    font_format_split(0x3d, word, 0x38,
                      (query_panel_reduction + 9) * 0x10 + 0x20,
                      0x160, 0x64, 0, 0, font1, 0x10);

    if (q_lv < next_lv) {
        font_list(0x3d, 0x56, 0x48,
                  query_panel_reduction * 0x10 + 0x88, font1, 0xd);
    }
}

// FUNCTION: C2 0x63638
// WIN: 0x0042be42
// Lines 2562–2623
//
// Business-tile query advice.  Picks one of ~10 cause words
// from string 0x3F via a per-output-level state machine on
// q_ind_output (0..7), with secondary tests on q_supplies,
// q_ind_pop, q_ind_market, q_local, no_of_empire_connections
// and q_road_access:
//
//   * q_ind_output >= 7      → word 0x30 ("max output").
//   * 6 with low supplies    → word 0x31.
//   * 5 with low supplies    → word 0x31.
//   * 5 with low pop         → word 0x38.
//   * 4 with no market /
//     no empire connections  → word 0x37.
//   * 3 with low supplies    → word 0x31.
//   * 3 with low pop         → word 0x38.
//   * 2 with low supplies    → word 0x31.
//   * 1 with low supplies    → word 0x31.
//   * 1 with low local sales → word 0x35.
//   * 0 (idle) with no road  → word 0x5A.
//   * Everything else falls through to
//     general_business_cause() which returns the cause word.
//
// After rendering the title (font_list 0x3F word q_ind_output)
// and the explanation paragraph, the panel also shows three
// progress lines: output% (font_no q_ind_output), produced
// total (industry[q_goods].supply + label 0xA / 0xB) and the
// goods name (string 0x10 word q_goods+1).  Tail-merge to
// 0x6315F (font_list).
void show_query_business_advice(void)
{
    int word;

    font_list(0x3f, q_ind_output, 0x38,
              (query_panel_reduction + 9) * 0x10 + 0x20,
              font1, 0x10);

    if (q_ind_output >= 7) {
        word = 0x30;
    } else if (q_ind_output == 6) {
        if (q_supplies <= 0x63)        word = 0x31;
        else                            word = general_business_cause();
    } else if (q_ind_output == 5) {
        if (q_supplies <= 0x4b)        word = 0x31;
        else if (q_ind_pop <= 2) word = 0x38;
        else                            word = general_business_cause();
    } else if (q_ind_output == 4) {
        if (q_supplies <= 0x43) {
            word = 0x31;
        } else if (!q_ind_market) {
            word = 0x36;
        }
        if (no_of_empire_connections <= 0) word = 0x37;
        else                               word = general_business_cause();
    } else if (q_ind_output == 3) {
        if (q_supplies <= 0x32)        word = 0x31;
        else if (q_ind_pop <= 1) word = 0x38;
        else                            word = general_business_cause();
    } else if (q_ind_output == 2) {
        if (q_supplies <= 0x22)        word = 0x31;
        else                            word = general_business_cause();
    } else if (q_ind_output == 1) {
        if (q_supplies <= 0x14)        word = 0x31;
        else if (q_local <= 0x32)      word = 0x35;
        else                            word = general_business_cause();
    } else {
        if (!q_road_access)            word = 0x5a;
        else if (q_supplies <= 0)      word = 0x31;
        else if (q_ind_pop <= 0) word = 0x38;
        else if (q_local <= 0)         word = 0x35;
        else                            word = general_business_cause();
    }

    font_format_split(0x3d, word, 0x38,
                      (query_panel_reduction + 0xa) * 0x10 + 0x20,
                      0x160, 0x64, 0, 0, font1, 0x10);

    x_is = 0;
    font_list(0x3f, 8, 0x38,
              (query_panel_reduction + 0xe) * 0x10 + 0x20,
              font1, 0x10);
    font_no(q_ind_output, 0x20, " ",
            x_is + 0x38,
            (query_panel_reduction + 0xe) * 0x10 + 0x20,
            font1, 0x10);
    font_list(0x3f, 9, x_is + 0x38,
              (query_panel_reduction + 0xe) * 0x10 + 0x20,
              font1, 0x10);

    x_is = 0;
    font_list(0x3f, 0xa, 0x38,
              (query_panel_reduction + 0xf) * 0x10 + 0x20,
              font1, 0x10);
    font_no(industry[q_goods].supply, 0x20, " ",
            x_is + 0x38,
            (query_panel_reduction + 0xf) * 0x10 + 0x20,
            font1, 0x10);
    font_list(0x3f, 0xb, x_is + 0x38,
              (query_panel_reduction + 0xf) * 0x10 + 0x20,
              font1, 0x10);
    font_list(0x10, q_goods + 1,
              x_is + 0x38,
              (query_panel_reduction + 0xf) * 0x10 + 0x20,
              font1, 0x10);
    font_list(0x3f, 0xc, x_is + 0x38,
              (query_panel_reduction + 0xf) * 0x10 + 0x20,
              font1, 0x10);
}

// FUNCTION: C2 0x63945
// WIN: 0x0042c280
// Lines 2627–2635
//
// Pick a paragraph-ID describing the dominant economic
// hindrance for the city-overview "why is business slow?"
// dialog.  Cascades through five conditions in fixed
// priority order, returning the first match.  Default
// (no condition fires) returns 0x39.
int general_business_cause(void)
{
    if (ind_growth_factor < 0)
        return 0x32;
    if (q_local < 0xc8 && population >= 0xc8)
        return 0x3a;
    if (q_ind_market == 0)
        return 0x36;
    if (no_of_empire_connections <= 0)
        return 0x34;
    if (q_local < 0x258 && population >= 0x258)
        return 0x33;
    return 0x39;
}

// FUNCTION: C2 0x639B4
// WIN: 0x0042c330
// Lines 2637–2729
//
// People-query panel: "who lives here?" right-click on a
// house tile shows the people inside.  When q_no_of_people
// is zero, render the "empty" paragraph (string 0x40 word 0)
// and bail.
//
// Otherwise paint a header with the headcount, then an icon
// strip drawing one sprite per occupant from q_people_list:
// dias frame, citizen portrait via people_data, then a
// highlight box around the queried_person.  The detailed-
// info section below describes the queried_person's role:
//
//   * citizen_list[+2] (kind):
//     - 3 → cohort/legionnaire (string 0x42 word
//           citizen_list[+0x32]).
//     - else  → string 0x41 word citizen_list[+0x32].
//   * Trade-tool / weapon / banner row keyed on
//     citizen_list[+2] - 1 (string 0x43).
//   * Health row: test_range_for(citizen_list[+4],
//     [+5], 5, 0) populates test_result1..3, then
//     valueDIVtotal(test_result2, test_result1) and
//     valueDIVtotal(test_result1*3, test_result3) pick
//     one of words 4..9 in string 0x44 (poor/sick/healthy).
void show_people_query_panel(void)
{
    int i;
    int ratio1;
    int ratio2;
    int word_health;

    if (q_no_of_people == 0) {
        font_list(0x40, 0, 0x58,
                  (query_panel_reduction + 0xb) * 0x10 + 0x20,
                  font1, 0x10);
        return;
    }

    x_is = 0;
    font_no(q_no_of_people, 0x20, " ",
            q_no_of_people * 0x28 + 0x30,
            (query_panel_reduction + 9) * 0x10 + 0x1a,
            font1, 0x10);
    if (q_no_of_people == 1)
        font_list(0x40, 1,
                  x_is + (q_no_of_people * 0x28 + 0x30),
                  (query_panel_reduction + 9) * 0x10 + 0x1a,
                  font1, 0x10);
    else
        font_list(0x40, 2,
                  x_is + (q_no_of_people * 0x28 + 0x30),
                  (query_panel_reduction + 9) * 0x10 + 0x1a,
                  font1, 0x10);
    font_list(0x40, 3,
              q_no_of_people * 0x28 + 0x30,
              (query_panel_reduction + 0xa) * 0x10 + 0x1a,
              font1, 0x10);

    for (i = 0; i < q_no_of_people; i++) {
        draw_a_dias(i * 0x28 + 0x30,
                    (query_panel_reduction + 9) * 0x10 + 0x18,
                    0x18, 0x20);
        draw_a_rect(i * 0x28 + 0x31,
                    (query_panel_reduction + 9) * 0x10 + 0x19,
                    0x16, 0x1e, 0x14);
        citizen_a = (short)(unsigned char)q_people_list[i];
        write_image(people_data,
                    citizen_list[citizen_a].image_id,
                    i * 0x28 + 0x37,
                    (query_panel_reduction + 9) * 0x10 + 0x20);
    }

    citizen_a = (short)(unsigned char)q_people_list[queried_person];

    draw_a_box(queried_person * 0x28 + 0x2e,
               (query_panel_reduction + 9) * 0x10 + 0x16,
               0x1c, 0x24, 0xa);

    x_is = 0;
    if (citizen_list[citizen_a].type == 3)
        font_list(0x42, citizen_list[citizen_a].name_id, 0x58,
                  (query_panel_reduction + 0xc) * 0x10 + 0x1c,
                  font1, 0x10);
    else
        font_list(0x41, citizen_list[citizen_a].name_id, 0x58,
                  (query_panel_reduction + 0xc) * 0x10 + 0x1c,
                  font1, 0x10);
    font_list(0x43, citizen_list[citizen_a].type - 1, x_is + 0x58,
              (query_panel_reduction + 0xc) * 0x10 + 0x1c,
              font1, 0x10);

    word_health = 0xf;
    if (citizen_list[citizen_a].type == 1) {
        test_range_for(citizen_list[citizen_a].x,
                       citizen_list[citizen_a].y, 5, 0);
        ratio1 = valueDIVtotal(test_result2, test_result1);
        if      (ratio1 > 0x32) word_health = 4;
        else if (ratio1 > 0xa)  word_health = 5;
        else if (ratio1 != 0)   word_health = 6;
        else {
            ratio2 = valueDIVtotal(test_result3, test_result1 * 3);
            if      (ratio2 < 0x3c) word_health = 7;
            else if (ratio2 < 0x5a) word_health = 8;
            else                     word_health = 9;
        }
    }
    if (citizen_list[citizen_a].type == 2) {
        if      (citizen_list[citizen_a].market_demand_a < 1) word_health = 0xa;
        else if (citizen_list[citizen_a].market_demand_a < 8) word_health = 0xb;
        else if (citizen_list[citizen_a].market_demand_b < 1) word_health = 0xc;
        else                                                   word_health = 0xd;
    }
    if (citizen_list[citizen_a].type == 3)
        word_health = 0xe;
    if (citizen_list[citizen_a].type == 4) {
        if (citizen_list[citizen_a].state_idx == 6) {
            word_health = 0xf;
        } else {
            test_range_for(citizen_list[citizen_a].x,
                           citizen_list[citizen_a].y, 5, 1);
            ratio1 = valueDIVtotal(test_result2, test_result1);
            if      (ratio1 > 0x32) word_health = 0x10;
            else if (ratio1 > 0xa)  word_health = 0x11;
            else                     word_health = 0x12;
        }
    }
    if (citizen_list[citizen_a].type == 5) {
        if (citizen_list[citizen_a].state_idx == 6) {
            word_health = 0xf;
        } else if (citizen_list[citizen_a].state_idx == 9) {
            word_health = 0x13;
        } else {
            test_range_for(citizen_list[citizen_a].x,
                           citizen_list[citizen_a].y, 5, 2);
            ratio1 = valueDIVtotal(test_result2, test_result1 << 4);
            if      (ratio1 > 0x50) word_health = 0x14;
            else if (ratio1 > 0x3c) word_health = 0x15;
            else if (ratio1 > 0x28) word_health = 0x16;
            else if (ratio1 > 0x14) word_health = 0x17;
            else                     word_health = 0x18;
        }
    }
    if (citizen_list[citizen_a].type == 6) {
        if      (citizen_list[citizen_a].market_demand_a < 1) word_health = 0x19;
        else if (citizen_list[citizen_a].market_demand_a < 8) word_health = 0x1a;
        else if (citizen_list[citizen_a].market_demand_b < 1) word_health = 0x1b;
        else                                                   word_health = 0x1c;
    }
    if (citizen_list[citizen_a].type == 7) {
        if (pop_tax_rate > 0xa) word_health = 0x1d;
        else                    word_health = 0x1e;
    }
    font_format_split(0x40, word_health, 0x58,
                      (query_panel_reduction + 0xd) * 0x10 + 0x1c,
                      0x150, 0x64, 0, 0, font1, 0x10);
}

// FUNCTION: C2 0x63EF3
// WIN: 0x0042cba3
// Lines 2731–2742
//
// Hit-test the rows of the query-panel person list.  When
// the player has just left-clicked while in query mode,
// scan all `q_no_of_people` rows; if the mouse falls
// inside row `i`'s rectangle, store `i` into
// `queried_person` and refresh the panel.
//
// Row `i` is a 24×32 cell at
//   (i*40 + 48, (query_panel_reduction + 9)*16 + 24)
// laid out left-to-right at fixed y, 40 px stride.
void get_queried_person(void)
{
    int i;

    if (query_mode != 1) return;
    if (mouse_left_preclick == 0) return;
    for (i = 0; i < q_no_of_people; i++) {
        if (mouse_in_area(i * 40 + 0x30,
                          (query_panel_reduction + 9) * 16 + 0x18,
                          0x18, 0x20)) {
            queried_person = i;
            show_query_panel();
        }
    }
}

// FUNCTION: C2 0x63F55
// WIN: 0x0042cc37
// Lines 2744–2812
//
// Detailed query panel: 11 rows of "requirement met / missing"
// statuses at x = 0x38 (left column) and 6 more at x = 0xF8
// (right column).  Each row picks an esi paragraph word
// (string 0x3D) and a colour ebp (0x10 normal, 0xB missing,
// 0x29 not-pertinent).  not_pertinant_statistic1 dims rows
// that don't apply to the current tile.
//
// Bottom dias frame at (0x28, 0x160) 0x180x0x28 holds two
// growth-factor labels (string 0x26 words 0x25/0x26 +
// font_list of pop_growth_factor / ind_growth_factor + 0x20).
void show_detailed_query_panel(void)
{
    int row;
    int esi;
    int colour;

    for (row = 0; row < 0xb; row++) {
        colour = 0x10;
        if (row == 0) { if (q_aqua) esi = 2; else if (q_sub_aqua) esi = 3; else { esi = 4; colour = 0xb; } }
        if (row == 1) { if (q_admin) esi = 5; else { esi = 6; colour = 0xb; } }
        if (row == 2) {
            if (q_security > 1) esi = 0x5c;
            else if (q_patrol) esi = 7;
            else if (q_security > 0) esi = 8;
            else { esi = 9; colour = 0xb; }
        }
        if (row == 3) { if (q_market) esi = 0xa; else { esi = 0xb; colour = 0xb; } }
        if (row == 4) { if (q_grammaticus) esi = 0xc; else { esi = 0xd; colour = 0xb; } }
        if (row == 5) { if (q_rhetor) esi = 0xe; else { esi = 0xf; colour = 0xb; } }
        if (row == 6) esi = 0x10;
        if (row == 7) { if (q_baths) esi = 0x11; else { esi = 0x12; colour = 0xb; } }
        if (row == 8) {
            if (hospital_cover >= 0x64) esi = 0x13;
            else { if (hospital_cover <= 0) esi = 0x54;
                else esi = 0x14; colour = 0xb; }
        }
        if (row == 9) {
            if (library_cover >= 0x64) esi = 0x15;
            else { if (library_cover <= 0) esi = 0x55;
                else esi = 0x16; colour = 0xb; }
        }
        if (row == 0xa) {
            if (q_road_access) esi = 0x58; else { esi = 0x59; colour = 0xb; }
        }

        if (not_pertinant_statistic1(row) != 0) colour = 0x29;

        x_is = 0;
        font_list(0x3d, esi, 0x38, row * 0x10 + 0xac, font1, colour);
        if (row == 6) font_no(q_entertainment, 0x20, " ", x_is + 0x38, row * 0x10 + 0xac, font1, colour);
        if (row == 8 && esi == 0x14) font_no(hospital_cover, 0x20, "%", x_is + 0x38, row * 0x10 + 0xac, font1, colour);
        if (row == 9 && esi == 0x16) font_no(library_cover, 0x20, "%", x_is + 0x38, row * 0x10 + 0xac, font1, colour);
    }

    for (row = 0; row < 6; row++) {
        colour = 0x10;
        if (row == 0) {
            if (q_business) { esi = 0x17; colour = 0xb; }
            else if (q_business_low) { esi = 0x17; colour = 0xb; }
            else if (q_business_vlow) { esi = 0x17; colour = 0xb; }
            else esi = 0x18;
        }
        if (row == 1) { if (!q_barracks) esi = 0x1a; else { esi = 0x19; colour = 0xb; } }
        if (row == 2) { if (!q_wall) esi = 0x1c; else { esi = 0x1b; colour = 0xb; } }
        if (row == 3) { if (!q_prefecture) esi = 0x1e; else { esi = 0x1d; colour = 0xb; } }
        if (row == 4) { if (!q_near_market) esi = 0x20; else { esi = 0x1f; colour = 0xb; } }
        if (row == 5) { if (!q_gate) esi = 0x22; else { esi = 0x21; colour = 0xb; } }
        font_list(0x3d, esi, 0xf8, row * 0x10 + 0xac, font1, colour);
    }

    draw_a_dias(0x28, 0x160, 0x180, 0x28);
    font_list(0x26, 0x25, 0x38, 0x164, font1, 0x10);
    font_list(0x26, pop_growth_factor + 0x20, 0xd0, 0x164, font1, 0x10);
    font_list(0x26, 0x26, 0x38, 0x176, font1, 0x10);
    font_list(0x26, ind_growth_factor + 0x20, 0xd0, 0x176, font1, 0x10);
}

// FUNCTION: C2 0x64371
// WIN: 0x0042d278
// Lines 2815–2902
//
// Region-map query panel.  Picks one of ~30 paragraph words
// (string 0x3D) based on the region-map tile type at
// q_type, with sub-selection by edi (q_type range):
//
//   * < 0x10  → word 0 ("unknown")
//   * < 0x18  → word 1 (water / sea)
//   * < 0x1C  → word 2 (river)
//   * < 0x20  → word 3 (rocks)
//   * < 0x7D  → word 4 (grass)
//   * < 0x85  → word 5 (trees)
//   * < 0x8D  → word 6 (jungle / forest)
//   * < 0x91  → word 7 (mountains)
//   * < 0x92  → word 8 (snow)
//   * 0x92    → word 9 + numeric sub 1 (resource: gold)
//   * 0x93    → word 0xA + sub 2 (silver)
//   * 0x94    → word 0xB + sub 3 (gems)
//   * 0x95    → word 0xC + sub 4 (iron)
//   * 0x96    → word 0xD + sub 5 (clay)
//   * 0x97    → word 0xE + sub 6 (timber)
//   * 0x98+   → region-edge marker (uses q_occa for the
//              direction label).
//   * >= 0xD5 → large-building cluster (workhouses /
//              forts) keyed on q_wh_level.
//
// After picking the paragraph, font_format_split renders
// it into the panel column.  If sub-word esp[0] is non-
// zero, an extra label "yields N units" + font_no of
// q_workhouse is stamped underneath.  q_road / q_outside
// flags add "road access" / "outside city" sub-lines.
void show_region_query_panel(int y)
{
    int paragraph;
    int quote_kind;
    int extra_kind = 0;
    int quote;

    if (q_type < 0x10) { paragraph = 0; quote_kind = 0; }
    else if (q_type < 0x18) { paragraph = 1; quote_kind = 0; }
    else if (q_type < 0x1c) { paragraph = 2; quote_kind = 0; }
    else if (q_type < 0x20) { paragraph = 3; quote_kind = 0; }
    else if (q_type < 0x7d) { paragraph = 4; quote_kind = 0; }
    else if (q_type < 0x85) { paragraph = 5; quote_kind = 0; }
    else if (q_type < 0x8d) { paragraph = 6; quote_kind = 0; }
    else if (q_type < 0x91) { paragraph = 7; quote_kind = 0; }
    else if (q_type < 0x92) { paragraph = 8; quote_kind = 0; }
    else if (q_type < 0x93) { paragraph = 9; quote_kind = 1; extra_kind = 1; }
    else if (q_type < 0x94) { paragraph = 0xa; quote_kind = 2; }
    else if (q_type < 0x95) { paragraph = 0xb; quote_kind = 3; }
    else if (q_type < 0x96) { paragraph = 0xc; quote_kind = 4; }
    else if (q_type < 0x97) { paragraph = 0xd; quote_kind = 5; }
    else if (q_type < 0x98) { paragraph = 0xe; quote_kind = 6; }
    else if (q_type < 0x9c) { paragraph = 0xf; quote_kind = 7; }
    else if (q_type < 0xa0) { paragraph = 0x10; quote_kind = 0; }
    else if (q_type < 0xb5) { paragraph = 0x11; quote_kind = 0; }
    else if (q_type < 0xb6) { paragraph = 0x12; quote_kind = 0; }
    else if (q_type < 0xd2) { paragraph = 0x13; quote_kind = 0; }
    else if (q_type < 0xd3) { paragraph = 0x14; quote_kind = 0; extra_kind = 2; }
    else if (q_type < 0xd4) { paragraph = 0x15; quote_kind = 8; }
    else if (q_type < 0xd5) { paragraph = 0x16; quote_kind = 9; extra_kind = 4; }
    else if (q_type < 0xdc) { paragraph = 0x17; quote_kind = 0; }
    else if (q_type < 0xe0) { paragraph = 0x18; quote_kind = 0xa; extra_kind = 3; }
    else if (q_type < 0xe4) { paragraph = 0x19; quote_kind = 0xb; extra_kind = 3; }
    else if (q_type < 0xe8) { paragraph = 0x1a; quote_kind = 0xc; extra_kind = 3; }
    else if (q_type < 0xec) { paragraph = 0x1b; quote_kind = 0xd; }
    else { paragraph = 0x1c; quote_kind = 0xe; }

    x_is = 0;
    if (extra_kind != 4) {
        font_list(0x44, paragraph, 0x98, y, font2, 0x10);
    }
    if (extra_kind == 1) {
        font_list(0x32, 0xa, 0x98, y + 0x34, font1, 0x10);
    }
    if (extra_kind == 2) {
        int army_name = get_army_name_from_fort_ref(q_ptr);
        font_list(5, army_name, x_is + 0x98, y, font2, 0x10);
    }
    if (extra_kind == 3) {
        font_list(0x10, q_goods + 1, x_is + 0x98, y, font2, 0x10);
    }
    if (extra_kind == 4) {
        if (q_had_goods != 0) {
            font_list(0x10, q_goods + 1, 0x68, y, font2, 0x10);
            font_list(0x44, paragraph, x_is + 0x68, y, font2, 0x10);
        } else {
            font_list(0x44, paragraph, x_is + 0x98, y, font2, 0x10);
        }
    }

    this_help_page = ((short *)region_mm_enties)[paragraph];

    if (quote_kind == 0) {
        quote = 0;
    } else if (quote_kind == 1) {
        quote = q_gfx / 4 + 1;
    } else if (quote_kind == 2) {
        quote = 2;
    } else if (quote_kind == 3) {
        quote = 4;
    } else if (quote_kind == 4) {
        quote = 6;
    } else if (quote_kind == 5) {
        quote = 8;
    } else if (quote_kind == 6) {
        if (!q_road) quote = 0x1c;
        else quote = q_gfx - 0x31;
    } else if (quote_kind == 7) {
        if (!q_road) quote = 0x1c;
        else quote = q_gfx - 0x4f;
    } else if (quote_kind == 8) {
        quote = q_gfx - 0x33;
    } else if (quote_kind == 9) {
        if (q_wh_level <= 0) quote = 0x1e;
        else if (q_wh_level < 4) quote = 0xd;
        else if (q_wh_level < 8) quote = 0xe;
        else if (q_wh_level < 0xf) quote = 0xf;
        else quote = 0x10;
    } else if (quote_kind == 0xa) {
        quote = reg_industry_quote(q_type - 0xdc);
    } else if (quote_kind == 0xb) {
        quote = reg_industry_quote(q_type - 0xe0);
    } else if (quote_kind == 0xc) {
        quote = reg_industry_quote(q_type - 0xe4);
    } else if (quote_kind == 0xd) {
        quote = reg_tpost_quote(q_type - 0xe8);
    } else if (quote_kind == 0xe) {
        quote = reg_port_quote(q_type - 0xec);
    } else {
        quote = 0;
    }

    font_format_split(0x45, quote, 0x38,
                      (query_panel_reduction + 9) * 0x10 + 0x20,
                      0x150, 0x64, 0, 0, font1, 0x10);
}

// FUNCTION: C2 0x64880
// WIN: 0x0042dabd
// Lines 2905–2915
//
// Pick the industry-advisor quote string id based on the
// q_* state flags.  Falls through to `x + 0x11` for the deep
// case (q_road set, q_workhouse > 1, q_outside == 0).
int reg_industry_quote(int x)
{
    if (q_road == 0)        return 0x19;
    if (q_workhouse == 0)   return 0x1a;
    if (q_outside)          return 0x1d;
    if (q_workhouse <= 1)   return 0x1b;
    return x + 0x11;
}

// FUNCTION: C2 0x648C0
// WIN: 0x0042db4b
// Lines 2917–2923
//
// Trading-post info quote selector.  Returns string id 0x19 when no
// road exists to the cell, otherwise the standard base + 0x15.
int reg_tpost_quote(int base)
{
    if (!q_road) return 0x19;
    return base + 0x15;
}

// FUNCTION: C2 0x648D3
// WIN: 0x0042db85
// Lines 2925–2931
//
// Port info quote selector.  Returns string id 0x19 when no road
// exists to the cell, otherwise the standard base + 0x15.
int reg_port_quote(int base)
{
    if (!q_road) return 0x19;
    return base + 0x15;
}

// FUNCTION: C2 0x648E6
// WIN: 0x0042dbbf
// Lines 2933–3043
//
// City-map right-click info gatherer.  Reads the cell at
// pm_over_cm_ptr, normalises it to the top-left corner of
// multi-cell buildings via reg_aquaduct_gfxdat[+8] (the
// per-tile footprint table), then walks the building
// footprint to fill in every q_* state var:
//
//   * Basic: q_type, q_flag, q_lv (via get_best_lv),
//     q_cover1/2 (city_map[+0xD/0xE]), q_range1/3, q_shell,
//     q_goods, q_ind_output, q_ind_pop, q_ind_market.
//   * Cover-based booleans (affected_by_cover1): q_supply,
//     q_sub_aqua, q_aqua, q_baths, q_grammaticus, q_rhetor,
//     q_business, q_near_market.
//   * Cover-2 (affected_by_cover2): q_business_low,
//     q_business_vlow, q_barracks, q_wall, q_gate,
//     q_prefecture.
//   * Range-based (get_range1 / get_range3): q_admin,
//     q_patrol, q_theatre, q_colosseum (>> 2), q_circus
//     (>> 4), q_entertainment (sum), q_market.
//   * q_security: 1 if q_shell >= 0x10, +1 if q_patrol set.
//   * q_supplies / q_local: from industry[q_goods].
//   * Road / hospital access via test_perimeter_/range_
//     for_road.
//   * People list: gather up to 6 citizens in a 5x5 area
//     around the building footprint into q_people_list,
//     setting q_no_of_people.
void get_query_info(void)
{
    unsigned char b;
    int xc, yc;
    int stride;
    int ptr;
    int pop;
    int dx;
    int dy;
    unsigned char a;
    int ax, ay;
    unsigned char footprint;

    q_type = ((unsigned char *)city_map)[pm_over_cm_ptr];
    if (q_type < 0x82)
        footprint = 1;
    else
        footprint = reg_aquaduct_gfxdat[q_type + 8];

    dx = dy = 0;
    if (footprint > 1) {
        dx = dy = ((unsigned char *)city_map)[pm_over_cm_ptr + 5] & 0xf;
        dx = dx % footprint;
        dy = dy / footprint;
        ptr = pm_over_cm_ptr - dx * 20;
        ptr -= dy * 20 * 80;
    } else {
        ptr = pm_over_cm_ptr;
    }

    q_type = ((unsigned char *)city_map)[ptr];
    q_flag = ((unsigned char *)city_map)[ptr + 1];
    q_lv = (char)get_best_lv((unsigned char *)city_map + ptr, footprint);
    q_cover1 = ((unsigned char *)city_map)[ptr + 0xd];
    q_cover2 = ((unsigned char *)city_map)[ptr + 0xe];
    q_range1 = ((unsigned char *)city_map)[ptr + 0xa];
    q_range3 = ((unsigned char *)city_map)[ptr + 0xc];
    q_supply       = (unsigned char)affected_by_cover1((unsigned char *)city_map + ptr, footprint, 4);
    q_sub_aqua     = (unsigned char)affected_by_cover1((unsigned char *)city_map + ptr, footprint, 2);
    q_aqua         = (char)affected_by_cover1((unsigned char *)city_map + ptr, footprint, 1);
    q_baths        = (unsigned char)affected_by_cover1((unsigned char *)city_map + ptr, footprint, 8);
    q_grammaticus  = (unsigned char)affected_by_cover1((unsigned char *)city_map + ptr, footprint, 0x10);
    q_rhetor       = (unsigned char)affected_by_cover1((unsigned char *)city_map + ptr, footprint, 0x20);
    q_admin        = (char)get_range1((unsigned char *)city_map + ptr, footprint, 0xc);
    q_shell        = ((unsigned char *)city_map)[ptr + 0x11];
    q_patrol       = (unsigned char)get_range1((unsigned char *)city_map + ptr, footprint, 0x30);
    if ((signed char)q_shell >= 0x10)
        q_security = 1;
    else
        q_security = 0;
    if (q_patrol)
        q_security = q_security + 1;
    q_theatre      = get_range3((unsigned char *)city_map + ptr, footprint, 3);
    q_colosseum    = get_range3((unsigned char *)city_map + ptr, footprint, 0xc);
    q_colosseum    = q_colosseum >> 2;
    q_circus       = get_range3((unsigned char *)city_map + ptr, footprint, 0x30);
    q_circus       = q_circus >> 4;
    q_entertainment = q_theatre + q_colosseum + q_circus;
    q_market       = (unsigned char)get_range1((unsigned char *)city_map + ptr, footprint, 0xc0);
    q_business     = (char)affected_by_cover1((unsigned char *)city_map + ptr, footprint, 0x80);
    q_business_low = (char)affected_by_cover2((unsigned char *)city_map + ptr, footprint, 0x10);
    q_business_vlow = (char)affected_by_cover2((unsigned char *)city_map + ptr, footprint, 0x20);
    q_barracks     = (char)affected_by_cover2((unsigned char *)city_map + ptr, footprint, 1);
    q_wall         = (char)affected_by_cover2((unsigned char *)city_map + ptr, footprint, 8);
    q_gate         = (unsigned char)affected_by_cover2((unsigned char *)city_map + ptr, footprint, 4);
    q_prefecture   = (unsigned char)affected_by_cover2((unsigned char *)city_map + ptr, footprint, 2);
    q_near_market  = (unsigned char)affected_by_cover1((unsigned char *)city_map + ptr, footprint, 0x40);

    q_goods = ((unsigned char *)city_map)[ptr + 0x13] & 0xf;
    q_ind_output = ((unsigned char *)city_map)[ptr + 0x9] & 0xf0;
    q_ind_output >>= 4;
    q_ind_pop    = ((unsigned char *)city_map)[ptr + 0x9] & 3;
    pop = test_area_for_population(2,
                                   act_start_x - dx,
                                   act_start_y - dy, 2);
    if      (pop > 0x82) q_ind_pop = q_ind_pop + 4;
    else if (pop > 0x5a) q_ind_pop = q_ind_pop + 3;
    else if (pop > 0x32) q_ind_pop = q_ind_pop + 2;
    else if (pop > 0xa)  q_ind_pop = q_ind_pop + 1;
    q_ind_market = ((unsigned char *)city_map)[ptr + 0x9] & 0xc;

    q_supplies = industry[q_goods].city_supply;
    q_local    = industry[q_goods].supply_pipeline[0];
    q_hospital_access = 0;
    cm_sptr = ptr;
    if (q_type == 0xfb || q_type == 0xf5) {
        if (test_perimeter_for_road_and_forum(
                act_start_x - dx, act_start_y - dy, 3, 0) != 0)
            q_hospital_access = 1;
    }
    q_road_access = (unsigned char)test_perimeter_for_road_and_forum(
            act_start_x - dx, act_start_y - dy, footprint, 1);
    if (q_type >= 0x82 && q_type <= 0xa1 && q_road_access == 0)
        q_road_access = (unsigned char)test_range_for_road(
            act_start_x - dx, act_start_y - dy, 3);

    queried_person = 0;
    q_no_of_people = 0;
    a = ((unsigned char *)city_map)[ptr + 7];
    b = ((unsigned char *)city_map)[ptr + 8];
    if (a) {
        q_people_list[q_no_of_people] = a;
        q_no_of_people++;
    }
    if (b) {
        q_people_list[q_no_of_people] = b;
        q_no_of_people++;
    }

    ax = act_start_x - 1;
    ay = act_start_y - 1;
    xc = yc = 3;
    if (ax < 0) {
        xc = 2;
        ax = 0;
    } else if (xc + ax > 0x50) {
        xc = 2;
    }
    if (ay < 0) {
        yc = 2;
        ay = 0;
    } else if (yc + ay > 0x3c) {
        yc = 2;
    }
    ptr = (ay * 80 + ax) * 20;
    stride = (0x50 - xc) * 20;
    for (gmn_y = ay; gmn_y < ay + yc; gmn_y++, ptr += stride) {
        for (gmn_x = ax; gmn_x < ax + xc; gmn_x++, ptr += 20) {
            if (q_no_of_people >= 6) break;
            if (gmn_x == act_start_x && gmn_y == act_start_y) continue;
            a = ((unsigned char *)city_map)[ptr + 7];
            b = ((unsigned char *)city_map)[ptr + 8];
            if (a) {
                q_people_list[q_no_of_people] = a;
                q_no_of_people++;
            }
            if (b) {
                q_people_list[q_no_of_people] = b;
                q_no_of_people++;
            }
        }
    }
}

// FUNCTION: C2 0x64E92
// WIN: 0x0042e3ed
// Lines 3046–3088
//
// Region-map right-click info gatherer.  Reads the cell at
// pm_over_cm_ptr and populates the q_* globals consumed by
// show_region_query_panel:
//
//   * q_type     = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).base_kind
//   * q_occa     = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).occupant
//   * q_gfx      = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).gfx
//   * q_wh_level = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).occupant & 0xF
//   * q_pop_level = get_pop_level()
//   * q_road     = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).edge_bits & 0x20
//   * q_outside  = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).outside & 0x40
//   * q_goods    = ((*(struct region_cell *)((unsigned char *)region_map + (ptr))).occupant & 0xF0) >> 4
//   * q_had_goods = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).edge_bits & 0x40
//
// For tiles 0xD5+ (large multi-cell buildings), the
// q_ptr is shifted back to the building origin by reading
// the 2-bit corner offset from (*(struct region_cell *)((unsigned char *)region_map + (ptr))).occupant & 3:
// dx_units = corner % 2, dy_units = corner / 2, then
// q_ptr -= dx_units * 8 + dy_units * 0x1E0 (60*8).
//
// q_workhouse is set via get_reg_buildings_in_radius(map_x,
// map_y, 1, 0xD3, 2) and scaled by the per-camp slave
// allocation slave_requirements[5].current / no_of_workcamps,
// then clamped to [0, 3] / 10.
void get_region_query_info(void)
{
    int slave_per_camp;
    int ptr;
    int map_pos;
    int map_x;
    int map_y;
    int workhouse;

    slave_per_camp = slave_requirements[5].current;
    if (no_of_workcamps != 0)
        slave_per_camp = slave_per_camp / no_of_workcamps;
    else
        slave_per_camp = 0;
    slave_per_camp = slave_per_camp / 10;
    if (slave_per_camp > 3) slave_per_camp = 3;
    if (slave_per_camp < 0) slave_per_camp = 0;

    ptr = pm_over_cm_ptr;
    q_type = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).base_kind;

    if (q_type >= 0xd5) {
        int corner = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).occupant & 3;
        int dx     = corner % 2;
        int dy     = corner / 2;
        ptr -= dx * 8;
        ptr -= dy * 0x1e0;
    }
    q_ptr = ptr;

    map_pos = ptr / map_actual_atom;
    map_y = map_pos % 0x3c;
    map_x = map_pos / 0x3c;

    q_occa     = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).occupant;
    q_gfx      = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).gfx;
    q_wh_level = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).occupant & 0xf;
    q_pop_level = get_pop_level();
    q_road     = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).edge_bits & 0x20;
    q_outside  = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).outside & 0x40;

    workhouse = get_reg_buildings_in_radius(map_y, map_x,
                                            2, 1, 0xd3);
    q_workhouse = workhouse;
    if (workhouse != 0)
        q_workhouse = workhouse * slave_per_camp + 1;

    q_goods = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).occupant & 0xf0;
    q_goods >>= 4;
    q_had_goods = (*(struct region_cell *)((unsigned char *)region_map + (ptr))).edge_bits & 0x40;
}

// FUNCTION: C2 0x65001
// WIN: 0x0042e5dc
// Lines 3092–3114
//
// Per-statistic pertinence filter used by show_detailed_query_panel:
// given a row index `p1` (0..n, 0xa = "all"), return 0 if the stat is
// applicable to the current q_type panel.  Each q_type band has its
// own row to suppress.  q_type is reloaded between each range test —
// Watcom 10.0a doesn't CSE through the structure here.
int not_pertinant_statistic1(int p1)
{
    if (q_type >= 0x82 && q_type < 0xa2) {
        if (p1 != 0xa) goto not_pert;
        return 1;
    }
    if (q_type >= 0xae && q_type <= 0xb9) {
        if (p1 == 0xa) goto not_pert;
        return 1;
    }
    if (q_type >= 0xdb && q_type <= 0xe2) {
        if (p1 == 0)   goto not_pert;
        return 1;
    }
    if (q_type >= 0xe3 && q_type <= 0xe4) {
        if (p1 == 0xa) goto not_pert;
        return 1;
    }
    if (q_type == 0xfb || q_type == 0xf5) {
        if (p1 == 0xa) return 0;
        if (p1 == 1) return 0;
        return 1;
    }
    if (q_type == 0xfa) {
        if (p1 == 0xa) goto not_pert;
        return 1;
    }
    if (q_type >= 0xfc) {
        if (q_type <= 0xff) {
            if (p1 == 0xa) goto not_pert;
            return 1;
        }
        return 1;
    }
    return 1;
not_pert:
    return 0;
}

// FUNCTION: C2 0x650C3
// WIN: 0x0042e7a9
// Lines 3116–3121
//
// Statistic-pertinence filter for the empire census screen:
// returns 0 ("not pertinent") for q_type in [0x7C..0xB9] or
// [0xD7..0xE2], else 1.  Companion to not_pertinant_statistic1.
int not_pertinant_statistic2(void)
{
    if (q_type >= 0x7c && q_type <= 0xb9) return 0;
    if (q_type >= 0xd7 && q_type <= 0xe2) return 0;
    return 1;
}

// FUNCTION: C2 0x650F4
// WIN: 0x0042e817
// Lines 3125–3191
//
// Pre-battle briefing screen.  Mosaic window at (8, 0xB0)
// 0x27x0x13.  Title (font2 string 0x47 word 0) at
// (0xF0, 0xDC).  Body shows the matchup with our_battle_army
// vs their_battle_army stats: three rows of
// (cohorts / cavalry / archers) for each side, at rows
// 0x182 / 0x194 / 0x1A6.
// Two centered confirm buttons (confirming_buttons) at
// (0x100, 0x104).  Tail: refresh_svga_screen.
void show_battle_intro_screen(void)
{
    int tribe_idx;

    cover_mouse_droppings();
    setup_whole_screen_refresh();
    stone_random_count = 0x32;
    show_a_mosaic_window(8, 0xb0, 0x27, 0x13);

    x_is = 0;
    font_list(0x47, 0, 0xf0, 0xdc, font2, 0x10);
    font_list(0x47, 1, 0x30, 0x104, font1, 0x10);
    font_list(0x47, 3, 0x30, 0x116, font1, 0x10);
    font_list(0x47, 4, 0x30, 0x13e, font1, 0x10);
    show_buttons(0x100, 0x104, confirming_buttons, 2);
    font_list(0x47, 5, 0x30, 0x170, font1, 0x10);

    x_is = 0;
    font_no(army_list[our_battle_army].num_regulars, 0x20, " ", 0x50, 0x182, font1, 0x10);
    font_list(0x47, 6, x_is + 0x50, 0x182, font1, 0x10);
    x_is = 0;
    font_no(army_list[our_battle_army].num_irregulars, 0x20, " ", 0x50, 0x194, font1, 0x10);
    font_list(0x47, 7, x_is + 0x50, 0x194, font1, 0x10);
    x_is = 0;
    font_no(army_list[our_battle_army].num_auxillaries, 0x20, " ", 0x50, 0x1a6, font1, 0x10);
    font_list(0x47, 8, x_is + 0x50, 0x1a6, font1, 0x10);
    x_is = 0;
    font_no(army_list[our_battle_army].num_specials, 0x20, " ", 0x50, 0x1b8, font1, 0x10);
    font_list(0x47, 9, x_is + 0x50, 0x1b8, font1, 0x10);

    x_is = 0;
    font_list(7, army_list[their_battle_army].source_region, 0x100, 0x170, font1, 0x10);
    font_list(0x47, 0xa, x_is + 0x100, 0x170, font1, 0x10);

    if (army_list[their_battle_army].num_specials != 0) {
        x_is = 0;
        font_no(army_list[their_battle_army].num_specials, 0x20, " ", 0x120, 0x182, font1, 0x10);
        font_list(0x47, 0xb, x_is + 0x120, 0x182, font1, 0x10);
        font_list(0x47, 0x19, x_is + 0x120, 0x182, font1, 0x10);
    } else {
        x_is = 0;
        tribe_idx = tribe_battle_setup[army_list[their_battle_army].tribe_id].u.raw[0];
        font_no(army_list[their_battle_army].num_horse, 0x20, " ", 0x120, 0x182, font1, 0x10);
        font_list(0x47, 0xb, x_is + 0x120, 0x182, font1, 0x10);
        if (army_list[their_battle_army].num_horse != 0) font_list(0x47, tribe_idx + 0xa, x_is + 0x120, 0x182, font1, 0x10);
    }

    x_is = 0;
    tribe_idx = tribe_battle_setup[army_list[their_battle_army].tribe_id].u.raw[1];
    font_no(army_list[their_battle_army].num_regulars, 0x20, " ", 0x120, 0x194, font1, 0x10);
    font_list(0x47, 0xc, x_is + 0x120, 0x194, font1, 0x10);
    font_list(0x47, tribe_idx + 0xa, x_is + 0x120, 0x194, font1, 0x10);

    x_is = 0;
    tribe_idx = tribe_battle_setup[army_list[their_battle_army].tribe_id].u.raw[2];
    font_no(army_list[their_battle_army].num_irregulars, 0x20, " ", 0x120, 0x1a6, font1, 0x10);
    font_list(0x47, 0xd, x_is + 0x120, 0x1a6, font1, 0x10);
    font_list(0x47, tribe_idx + 0xa, x_is + 0x120, 0x1a6, font1, 0x10);

    x_is = 0;
    tribe_idx = tribe_battle_setup[army_list[their_battle_army].tribe_id].u.raw[3];
    font_no(army_list[their_battle_army].num_auxillaries, 0x20, " ", 0x120, 0x1b8, font1, 0x10);
    font_list(0x47, 0xe, x_is + 0x120, 0x1b8, font1, 0x10);
    font_list(0x47, tribe_idx + 0xa, x_is + 0x120, 0x1b8, font1, 0x10);

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(city_palette);
}

// FUNCTION: C2 0x656CD
// WIN: 0x0042eeac
// Lines 3196–3293
//
// Post-battle outcome screen.  Same window frame as the
// intro screen ((8, 0xB0) 0x27x0x13) but the title varies
// with battle_victor / battle_state:
//
//   * Victor 0 (loss): word 0, subtitle word 2, speech 5.
//   * Victor != 0, state == 6 (decisive): word 1, subtitle
//     word 3, speech 6.
//   * Otherwise (marginal victory): word 1, subtitle word 4,
//     speech 7.
//
// Below the title, a centre-aligned description (string 0x48
// word 5).  Two stat blocks at (0x30, 0x182..0x1A6) and
// (0x1C0, 0x182..0x1A6) for our_battle_army / their_battle_
// army show the post-battle cohort, cavalry and archer
// counts (army_list[+0x82/+0x7E/+0x7A]) -- mirrored on the
// right with casualty figures.
//
// Confirm continuation button (string 0x47 word 5) at
// (0x30, 0x170).  Tail: refresh_svga_screen.
void show_battle_outtro_screen(void)
{
    cover_mouse_droppings();
    setup_whole_screen_refresh();
    stone_random_count = 0x32;
    show_a_mosaic_window(8, 0xb0, 0x27, 0x13);

    x_is = 0;
    if (battle_victor == 0) {
        font_list(0x48, 0, 0xc0, 0xdc, font2, 0x10);
        font_list(0x48, 2, 0x80, 0x104, font1, 0x10);
        play_speech(5);
    } else {
        font_list(0x48, 1, 0xc0, 0xdc, font2, 0x10);
        if (battle_state == 6) {
            font_list(0x48, 3, 0x80, 0x104, font1, 0x10);
            play_speech(6);
        } else {
            font_list(0x48, 4, 0x80, 0x104, font1, 0x10);
            play_speech(7);
        }
    }

    font_list(0x48, 5, 0xe0, 0x128, font1, 0x10);
    font_list(0x47, 5, 0x30, 0x170, font1, 0x10);

    x_is = 0;
    font_no(army_list[our_battle_army].num_regulars, 0x20, " ", 0x30, 0x182, font1, 0x10);
    font_list(0x47, 6, x_is + 0x30, 0x182, font1, 0x10);
    font_no(our_battle_regs - army_list[our_battle_army].num_regulars,
            0x28, " ", x_is + 0x30, 0x182, font1, 0x10);
    font_list(0x48, 6, x_is + 0x30, 0x182, font1, 0x10);

    x_is = 0;
    font_no(army_list[our_battle_army].num_irregulars, 0x20, " ", 0x30, 0x194, font1, 0x10);
    font_list(0x47, 7, x_is + 0x30, 0x194, font1, 0x10);
    font_no(our_battle_irregs - army_list[our_battle_army].num_irregulars,
            0x28, " ", x_is + 0x30, 0x194, font1, 0x10);
    font_list(0x48, 6, x_is + 0x30, 0x194, font1, 0x10);

    x_is = 0;
    font_no(army_list[our_battle_army].num_auxillaries, 0x20, " ", 0x30, 0x1a6, font1, 0x10);
    font_list(0x47, 8, x_is + 0x30, 0x1a6, font1, 0x10);
    font_no(our_battle_auxs - army_list[our_battle_army].num_auxillaries,
            0x28, " ", x_is + 0x30, 0x1a6, font1, 0x10);
    font_list(0x48, 6, x_is + 0x30, 0x1a6, font1, 0x10);

    x_is = 0;
    font_no(army_list[our_battle_army].num_specials, 0x20, " ", 0x30, 0x1b8, font1, 0x10);
    font_list(0x47, 9, x_is + 0x30, 0x1b8, font1, 0x10);
    font_no(our_battle_specials - army_list[our_battle_army].num_specials,
            0x28, " ", x_is + 0x30, 0x1b8, font1, 0x10);
    font_list(0x48, 6, x_is + 0x40, 0x1b8, font1, 0x10);

    x_is = 0;
    font_list(7, army_list[their_battle_army].source_region, 0x150, 0x170, font1, 0x10);
    font_list(0x47, 0xa, x_is + 0x150, 0x170, font1, 0x10);

    if (their_battle_specials != 0) {
        x_is = 0;
        font_no(army_list[their_battle_army].num_specials, 0x20, " ", 0x150, 0x182, font1, 0x10);
        font_list(0x47, 0xb, x_is + 0x150, 0x182, font1, 0x10);
        font_no(their_battle_specials - army_list[their_battle_army].num_specials,
                0x28, " ", x_is + 0x150, 0x182, font1, 0x10);
        font_list(0x48, 6, x_is + 0x150, 0x182, font1, 0x10);
    } else {
        x_is = 0;
        font_no(army_list[their_battle_army].num_horse, 0x20, " ", 0x150, 0x182, font1, 0x10);
        font_list(0x47, 0xb, x_is + 0x150, 0x182, font1, 0x10);
        font_no(their_battle_horse - army_list[their_battle_army].num_horse,
                0x28, " ", x_is + 0x150, 0x182, font1, 0x10);
        font_list(0x48, 6, x_is + 0x150, 0x182, font1, 0x10);
    }

    x_is = 0;
    font_no(army_list[their_battle_army].num_regulars, 0x20, " ", 0x150, 0x194, font1, 0x10);
    font_list(0x47, 0xc, x_is + 0x150, 0x194, font1, 0x10);
    font_no(their_battle_regs - army_list[their_battle_army].num_regulars,
            0x28, " ", x_is + 0x150, 0x194, font1, 0x10);
    font_list(0x48, 6, x_is + 0x150, 0x194, font1, 0x10);

    x_is = 0;
    font_no(army_list[their_battle_army].num_irregulars, 0x20, " ", 0x150, 0x1a6, font1, 0x10);
    font_list(0x47, 0xd, x_is + 0x150, 0x1a6, font1, 0x10);
    font_no(their_battle_irregs - army_list[their_battle_army].num_irregulars,
            0x28, " ", x_is + 0x150, 0x1a6, font1, 0x10);
    font_list(0x48, 6, x_is + 0x150, 0x1a6, font1, 0x10);

    x_is = 0;
    font_no(army_list[their_battle_army].num_auxillaries, 0x20, " ", 0x150, 0x1b8, font1, 0x10);
    font_list(0x47, 0xe, x_is + 0x150, 0x1b8, font1, 0x10);
    font_no(their_battle_auxs - army_list[their_battle_army].num_auxillaries,
            0x28, " ", x_is + 0x150, 0x1b8, font1, 0x10);
    font_list(0x48, 6, x_is + 0x150, 0x1b8, font1, 0x10);

    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(city_palette);
}
