// D:\C2\CODE\titles.c

#include "c2_data.h"


extern void font_list(int idx, int word_count, int x, int y, unsigned char *font, int color);
extern void font_format_split(int idx, int word_skip, int x, int y_start, int max_width, int line_limit, int x_overflow, int max_width_overflow, unsigned char *font, int color);

/* Per-file extern supplements: stone_random_count is a single byte
   (used as a small integer) — c2_data.h would otherwise default-type
   it as int.  Declare it as char here to get the right store width. */

/* Local forward declarations for the file-internal call sites with
   their proper Watcom register-call signatures.  The auto-generated
   stubs.c keeps the same names with (void) bodies — that's fine at
   link time since the stubs ignore their inputs. */

// FUNCTION: C2 0x59F76
// Lines 19–32
void do_lose_game(void)
{
    pointer_mode = 0;
    stop_tune();
    lose_game_screen();
    out1 = 0;
    play_speech(2);
    while (out1 == 0) {
        just_idle_game_loop();
        if (mouse_right_click != 0) {
            out1 = 1;
        }
    }
    stop_db();
    do_vga_smacked_anim("losegame.smk");
}

// FUNCTION: C2 0x59FD2
// WIN: 0x004ae99a
// Lines 37–49
void lose_game_screen(void)
{
    black_out();
    setup_whole_screen_refresh();
    stone_random_count = 0x32;
    show_a_mosaic_window(0x80, 0xa0, 0x14, 0xc);
    x_is = 0;
    font_list(0x2e, 0, 0xd0, 0xc0, font2, 0x10);
    font_format_split(0x2e, 1, 0xa0, 0xe8,
                      0x100, 0x64, 0, 0,
                      font1, 0x10);
    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(city_palette);
}

// FUNCTION: C2 0x5A067
// WIN: 0x004aea34
// Lines 52–82
//
// Display the promotion / win-game splash with a Smacker
// preroll, mosaic window, font lines, and a 3-button row.
// The ``rank`` argument selects between the win-game variant
// (rank >= 10) and the regular promotion screen.
void show_want_promotion_box(int rank)
{
    stop_tune();
    if (rank >= 10)
        do_vga_smacked_anim("wingame.smk");
    else
        do_vga_smacked_anim("promote.smk");
    background_screen();
    stone_random_count = 0x32;
    show_a_mosaic_window(0x80, 0x70, 0x14, 0x10);
    x_is = 0;
    if (rank < 10) {
        font_list(0x46, 0, 0xd0, 0x90, font2, 0x10);
        font_format_split(0x46, 4, 0xa0, 0xb4,
                          0x100, 0x64, 0, 0,
                          font1, 0x10);
        play_speech(0);
    } else {
        font_list(0x46, 5, 0xd0, 0x90, font2, 0x10);
        font_format_split(0x46, 6, 0xa0, 0xb4,
                          0x100, 0x64, 0, 0,
                          font1, 0x10);
        play_speech(1);
    }
    font_list(0x46, 1, 0xc0, 0x106, font1, 0x10);
    font_list(0x46, 2, 0xc0, 0x126, font1, 0x10);
    font_list(0x46, 3, 0xc0, 0x146, font1, 0x10);
    show_buttons(0x80, 0x70, promotion_buttons, 3);
    setup_whole_screen_refresh();
    hold_mouse_replace = 1;
    refresh_svga_screen();
}

// FUNCTION: C2 0x5A1E7
// WIN: 0x004aeabe
//
// Empty in PS.EXE — just ``ret``.  Likely a hook for a demo /
// teaser slideshow that was stubbed out before ship.  Called from
// main()'s exit path (c2.c).  In PS.EXE this symbol and
// demo_lead_out_slideshow share ONE 1-byte body at 0x5A1E7 (both
// -d1 names land on the same address); CAESAR2.EXE keeps them as two
// distinct empty functions (@0x004aeabe / @0x004aeac9), witnessing
// that the source defined both, lead_in first.
void demo_lead_in_slideshow(void)
{
}

// FUNCTION: C2 0x5A1E7
// WIN: 0x004aeac9
//
// The lead-out twin — see demo_lead_in_slideshow above.
void demo_lead_out_slideshow(void)
{
}

// FUNCTION: C2 0x5A1E8
// WIN: 0x004aead7
// Lines 113–132
void lead_in_logos(void)
{
    black_out();
    mouse_was_pressed = 0;
    if (display_pl8file("logo1.pl8", "logo1.256") != 0
        && mouse_was_pressed == 0) {
        fade_to_black_out();
        if (mouse_was_pressed == 0
            && display_pl8file("logo2.pl8", "logo2.256") != 0
            && mouse_was_pressed == 0) {
            fade_to_black_out();
        }
    }
    black_out();
    clear_all_screens();
    clear_a_screen();
    setup_whole_screen_refresh();
    refresh_svga_screen();
}
