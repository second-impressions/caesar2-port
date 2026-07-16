
#include "c2_data.h"


extern void font_list(int idx, int word_count, int x, int y, unsigned char *font, int color);
extern void font_format_split(int idx, int word_skip, int x, int y_start, int max_width, int line_limit, int x_overflow, int max_width_overflow, unsigned char *font, int color);

// Shows the defeat screen, waits for a right click, then plays the defeat animation.
// FUNCTION: C2 0x59f76
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

// Displays the defeat screen and waits for the player to continue.
// FUNCTION: C2 0x59fd2
// FUNCTION: C2WIN 0x004ae99a
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

// Shows the promotion or victory dialog with its video, text, speech, and response buttons.
// Ranks of 10 or higher select the victory variant.
// FUNCTION: C2 0x5a067
// FUNCTION: C2WIN 0x004aea34
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

// Does nothing; reserved for the demo lead-in slideshow.
// FUNCTION: C2 0x5a1e7 FOLDED
// FUNCTION: C2WIN 0x004aeac9
void demo_lead_in_slideshow(void)
{
}

// Does nothing; reserved for the demo lead-out slideshow.
// FUNCTION: C2 0x5a1e7 FOLDED
// FUNCTION: C2WIN 0x004aeabe REORDERED
void demo_lead_out_slideshow(void)
{
}

// Shows the startup logos, allowing a mouse press to skip the remaining sequence.
// FUNCTION: C2 0x5a1e8
// FUNCTION: C2WIN 0x004aead7
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
