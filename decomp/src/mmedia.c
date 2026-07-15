// D:\C2\CODE\mmedia.c

#include "mmedia.h"
#include "c2_data.h"


extern void put_a_font_string(char *str, int x, int y, unsigned char *font, int color);
extern int  one_letter(unsigned char *font, unsigned char letter);
extern void font_list(int idx, int word_count, int x, int y, unsigned char *font, int color);
extern void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color);
extern int  get_next_word_length(char *src, unsigned char *font);
void media_text_place(int x, int y, int width, int line_count, int alt_x, int alt_width, unsigned char *font);

/* The constant-bound fill loops in this file compile to
 * `call __STOSB` (count in ecx) via Watcom's fill-loop recognition;
 * the original source was plain loops, as the Mac PPC build shows.
 *
 * Confirmed via docs/codegen-experiments/memset_init_help.py:
 * 32-bit Watcom 10.0a never marks memset() as intrinsic
 * (string.h: `#ifndef __386__ #pragma intrinsic(memset)`), so
 * even `-oi` + explicit `#pragma intrinsic(memset)` produces a
 * call with the count in ebx (__watcall 3rd arg slot), not ecx —
 * the source was NOT memset(). */

#include "c2_types.h"

char help_palname[14] = "xxxxxxxx.256";

char active_tutorial_pages[34] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2, 0, 3, 0, 4, 0, 0, 0, 6, 0, 7, 0, 0, 0, 0, 0, 0, 0, 0, 0 };

char city_tutorial_icons[30] = { 1, 1, 1, 1, 1, 1, 9, 6, 9, 1, 1, 1, 3, 3, 1, 2, 4, 7, 7, 1, 7, 7, 7, 7, 99, 99, 99, 99, 99, 99 };

char region_tutorial_icons[30] = { 5, 5, 5, 5, 5, 5, 5, 6, 5, 5, 5, 5, 5, 8, 5, 5, 8, 5, 8, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99, 99 };

struct tutorial_file_rec tut_files[32] = {
    { "tut_01a.pl8" },
    { "tut_01b.pl8" },
    { "tut_02a.pl8" },
    { "tut_02b.pl8" },
    { "tut_03a.pl8" },
    { "tut_03b.pl8" },
    { "tut_04a.pl8" },
    { "tut_04b.pl8" },
    { "tut_05a.pl8" },
    { "tut_05b.pl8" },
    { "tut_06a.pl8" },
    { "tut_06b.pl8" },
    { "tut_07a.pl8" },
    { "tut_07b.pl8" },
    { "tut_08a.pl8" },
    { "tut_08b.pl8" },
    { "tut_09a.pl8" },
    { "tut_09b.pl8" },
    { "tut_10a.pl8" },
    { "tut_10b.pl8" },
    { "tut_11a.pl8" },
    { "tut_11b.pl8" },
    { "tut_12a.pl8" },
    { "tut_12b.pl8" },
    { "tut_13a.pl8" },
    { "tut_13b.pl8" },
    { "tut_14a.pl8" },
    { "tut_14b.pl8" },
    { "tut_15a.pl8" },
    { "tut_15b.pl8" },
    { "tut_16a.pl8" },
    { "tut_16b.pl8" }
};

struct tutorial_file_rec tut_palfiles[32] = {
    { "tut_01a.256" },
    { "tut_01b.256" },
    { "tut_02a.256" },
    { "tut_02b.256" },
    { "tut_03a.256" },
    { "tut_03b.256" },
    { "tut_04a.256" },
    { "tut_04b.256" },
    { "tut_05a.256" },
    { "tut_05b.256" },
    { "tut_06a.256" },
    { "tut_06b.256" },
    { "tut_07a.256" },
    { "tut_07b.256" },
    { "tut_08a.256" },
    { "tut_08b.256" },
    { "tut_09a.256" },
    { "tut_09b.256" },
    { "tut_10a.256" },
    { "tut_10b.256" },
    { "tut_11a.256" },
    { "tut_11b.256" },
    { "tut_12a.256" },
    { "tut_12b.256" },
    { "tut_13a.256" },
    { "tut_13b.256" },
    { "tut_14a.256" },
    { "tut_14b.256" },
    { "tut_15a.256" },
    { "tut_15b.256" },
    { "tut_16a.256" },
    { "tut_16b.256" }
};

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
char media_line_buffer[200];
int greyed_out;
int tutorial_correct_timer;
int media_voc;
int media_right_image;
int this_spot;
int tutorial_level;
int last_tutorial_page;
int tutorial_timer;
int media_left_image;
int tutorial_correct;
int linked_text_flag;

/* act_goto_city_map's signature is ambiguous in c2_funcs.h
 * (conflicting fwd/def in action.c), so spell it explicitly here. */


// FUNCTION: C2 0x57FA8
// WIN: 0x004521a0
// Lines 115–148
//
// Run the in-game help/media browser starting at `page`.  Valid pages
// are 1..1999.  Pointer mode is suppressed for the duration and
// restored on exit; linked pages and media voice playback are handled
// inside the modal help loop.
//
// Faithful but not byte-exact (~130 b residue): the modal-loop structure
// matches, but Watcom picks ecx/edi temporaries where PS uses edx/esi/ebp,
// causing a register-allocation cascade through the loop.
void launch_help(int page)
{
    int old_pointer_mode;

    if (page <= 0) return;
    if (page >= 0x7d0) return;

    old_pointer_mode = pointer_mode;
    pointer_mode = 0;
    first_help_page = this_help_page = page;
    init_help_history();
    out3 = 0;
    greyed_out = 0;
    while (out3 != 1) {
        stop_db();
        load_media_entry();
        show_help_page();
        if (media_voc != 0) {
            set_db_sound(this_media_entry.voc_file);
        }
        out2 = 0;
        while (out2 != 1) {
            help_game_loop();
            if (exit_screen() != 0) {
                out3 = out2 = 1;
            }
            if (mouse_right_click != 0) {
                out3 = out2 = 1;
            }
            if (out2 > 1) {
                out2 = out2 - 1;
                continue;
            }
            if (mouse_left_preclick != 0) {
                if (get_linked_page() != 0) {
                    out2 = 1;
                }
            }
        }
    }
    stop_db();
    pointer_mode = old_pointer_mode;
}

// FUNCTION: C2 0x580A9
// WIN: 0x00452332
// Lines 150–158
//
// Load the current help/media table entry, then load its text block
// into format_buffer and mark which optional assets are present.
void load_media_entry(void)
{
    media_voc = 0;
    media_right_image = 0;
    media_left_image = 0;

    readfile(media_file, &this_media_entry, 0x3a,
             this_help_page * 0x3a + 8);
    readfile(media_file, format_buffer, 0x7d0,
             this_media_entry.text_offset);

    if (my_strcmp(this_media_entry.left_file, "null.pl8", 8) != 0) {
        media_left_image = 1;
    }
    if (my_strcmp(this_media_entry.right_file, "null.pl8", 8) != 0) {
        media_right_image = 1;
    }
    if (my_strcmp(this_media_entry.voc_file, "null.voc", 8) != 0) {
        media_voc = 1;
    }
}

// FUNCTION: C2 0x58162
// WIN: 0x0045241f
// Lines 160–220
//
// Render the in-game F1 help dialog.  Loads the help page's
// palette over the current city_palette into temp_palette, paints
// the modal mosaic frame, optionally loads / draws the left and
// right illustration sprites flanking the text column, then
// dispatches to media_text_place to wrap the help body into the
// gap between them.  Buttons (prev / next / index) live along
// the bottom edge and the exit button anchors the top-right.
//
// Layout constants (all in svga pixel coords):
//   * frame:      cell (8,0x20) span (0x1d,0x1b) on the mosaic grid
//   * blank pane: cell (0x18,0x30) span (0x1b,0x19)
//   * exit btn:   (0x1a8, 0x1a0)
//   * buttons:    base (0x168, 0x1a0), 2 buttons from help_buttons
//   * title:      put_a_font_string(text_pointer, esi=0x28, 0x38, font2, 0x10)
//   * body:       media_text_place(x=0x28, y=0x5a, width=ebp,
//                                  line_count=edi, alt_x=0x28,
//                                  alt_width=0x190, font=font1)
//
// The two images (when present) eat horizontal space; ebp
// (width passed to media_text_place) shrinks by sprite_width+8
// per side, and edi (line_count) is capped at
// (sprite_height-0x18)/0x10.
void show_help_page(void)
{
    int  text_lines;
    int  text_x;
    int  text_w;
    int  left_ok;
    int  right_ok;

    /* extension := "256" so subsequent put_filename_extension()
     * calls stamp the palette suffix on the page's image names. */
    my_strcpy("256", extension, 4);
    my_strcpy(city_palette, temp_palette, 0x300);

    cover_mouse_droppings();
    if (!greyed_out) {
        grey_a_screen();
        greyed_out = 1;
    }

    stone_random_count = 0x11;
    show_a_mosaic_frame(8, 0x20, 0x1d, 0x1b);
    setup_whole_screen_refresh();
    show_a_mosaic_blank(0x18, 0x30, 0x1b, 0x19);
    show_an_exit_button(0x1a8, 0x1a0);
    show_buttons(0x168, 0x1a0, help_buttons, 2);

    text_pointer = format_buffer;

    text_x     = 0x28;
    text_w     = 0x190;
    text_lines = 1;

    /* Optional left illustration ---------------------------------- */
    left_ok = 0;
    if (media_left_image) {
        left_ok = readfile(this_media_entry.left_file,
                           ((void *)scratch_buffer), 0x186a0, 0);
        my_strcpy(this_media_entry.left_file, help_palname, 0xd);
        my_strcpy("256", extension, 4);
        put_filename_extension(help_palname);
        readfile(help_palname, temp_palette, 0x300, 0);
        if (left_ok) {
            int cap;
            general_sprite(this_media_entry.left_sprite, 0x1e, 0x38);
            draw_a_dias(0x1d, 0x37, sprite_width + 2, sprite_height + 2);
            draw_a_dias(0x1c, 0x36, sprite_width + 4, sprite_height + 4);
            text_w -= sprite_width + 8;
            text_x  = sprite_width + 0x28;
            cap     = (sprite_height - 0x18) / 0x10;
            if (cap > text_lines) text_lines = cap;
        }
    }

    /* Optional right illustration --------------------------------- */
    right_ok = 0;
    if (media_right_image) {
        right_ok = readfile(this_media_entry.right_file,
                            ((void *)scratch_buffer), 0x186a0, 0);
        my_strcpy(this_media_entry.right_file, help_palname, 0xd);
        my_strcpy("256", extension, 4);
        put_filename_extension(help_palname);
        readfile(help_palname, temp_palette, 0x300, 0);
        if (right_ok) {
            int cap;
            get_general_sprite_sizes(this_media_entry.right_sprite);
            general_sprite(this_media_entry.right_sprite,
                           0x1b8 - sprite_width + 6, 0x38);
            draw_a_dias(0x1b8 - sprite_width + 5, 0x37,
                        sprite_width + 2, sprite_height + 2);
            draw_a_dias(0x1b8 - sprite_width + 4, 0x36,
                        sprite_width + 4, sprite_height + 4);
            text_w -= sprite_width + 8;
            cap     = (sprite_height - 0x18) / 0x10;
            if (cap > text_lines) text_lines = cap;
        }
    }

    put_a_font_string(text_pointer, text_x, 0x38, font2, 0x10);
    media_text_place(text_x, 0x5a, text_w, text_lines,
                     0x28, 0x190, font1);

    refresh_svga_screen();
    set_palette(temp_palette);
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x584A9
// WIN: 0x0045296c
// Lines 222–274
//
// Word-wrap a stream of help / tutorial text from format_buffer
// (the global media-load scratch) into successive lines on the
// sprite layer.  Walks one line at a time:
//
//   1. Clear media_line_buffer (200 bytes — the max width of a
//      packed line).
//   2. Pull whole words out of text_pointer via
//      get_next_word_length() and accumulate their advance widths
//      until the next word would push the line past `width`
//      (less alt_x_offset, which is held at zero in PS — the
//      escape-flag mechanism wires it but no caller exercises it).
//   3. Copy each fitting word's bytes into media_line_buffer,
//      skipping leading spaces and bailing on '$' (which sets
//      escape_flag=1 to force the line to fill and break early).
//   4. Call put_a_media_string(buffer, x, y) to render the line
//      and bump y by 0x12.
//
// When line_index reaches line_count, the function swaps in
// (alt_x, alt_width) — the caller-provided continuation
// rectangle — and keeps wrapping the rest of the text into
// that secondary area.  show_help_page uses this for the
// double-column footer rendered below the main paragraph.
//
// The 20-entry help_page_hot_spots[] table is reset to zero at
// entry so each call starts with a clean hotspot list, which is
// then populated by put_a_media_string's '#'-tag handler.
//
// Calling convention (__watcall):
//   eax = x         edx = y          ebx = width     ecx = line_count
//   stack: alt_x,   alt_width,       font  (cleaned by callee, ret 0xC)
void media_text_place(int x, int y, int width, int line_count,
                      int alt_x, int alt_width, unsigned char *font)
{
    int    i;
    int    escape_flag;
    int    line_idx;
    int    cur_y;
    int    alt_off;
    int    loop_active;
    int    line_width;
    int    buf_pos;
    int    skip_leading;
    signed char c;
    int    edx_count;

    this_spot        = 0;
    linked_text_flag = 0;
    nof_hot_spots    = 0;
    for (i = 0; i < 20; i++) {
        help_page_hot_spots[i].page = 0;
        help_page_hot_spots[i].x1 = help_page_hot_spots[i].x2 = 0;
        help_page_hot_spots[i].x3 = help_page_hot_spots[i].x4 = 0;
        help_page_hot_spots[i].y  = help_page_hot_spots[i].unused = 0;
    }

    /* Walk text_pointer forward through the format_buffer header
     * (loading code wrote some prelude bytes ahead of the actual
     * paragraph text).  Loop terminates one past the first NUL,
     * leaving text_pointer pointing at the start of the real
     * wrappable content. */
    text_pointer = format_buffer;
    while (*text_pointer > 0) text_pointer++;
    text_pointer++;

    font_screen_limit = 0;
    loop_active = 1;
    line_idx    = 0;
    cur_y       = y;
    escape_flag = 0;

    while (loop_active) {
        for (i = 0; i < 200; i++) media_line_buffer[i] = 0;
        line_width  = 0;
        buf_pos     = 0;
        skip_leading = 1;

        if (escape_flag) {
            alt_off     = 0;
            escape_flag = 0;
        } else {
            alt_off = 0;
        }

        while (loop_active && line_width < width - alt_off) {
            line_width += get_next_word_length(text_pointer, font);
            if (line_width >= width - alt_off) continue;

            for (edx_count = 0; edx_count < char_count; ) {
                c = *text_pointer++;
                if (skip_leading && c == ' ') {
                    /* drop */
                } else if (c == '$') {
                    escape_flag = 1;
                    line_width  = width;
                    break;
                } else {
                    media_line_buffer[buf_pos++] = c;
                    skip_leading = 0;
                }
                edx_count++;
            }
            if (*text_pointer == 0) {
                loop_active = 0;
                continue;
            }
        }

        insert_place  = 1;
        x_is          = 0;
        allow_padding = 1;
        put_a_media_string(media_line_buffer, x + alt_off, cur_y);
        line_idx++;
        cur_y += 0x12;

        if (line_idx >= line_count) {
            /* Switch over to the continuation rectangle. */
            x     = alt_x;
            width = alt_width;
        }
    }
}

// FUNCTION: C2 0x58684
// WIN: 0x00452c66
// Lines 276–326
//
// Render one line of help / tutorial text into the sprite layer.
//
//   text = pointer to ASCIIZ string
//   x    = pen x in pixels (also caches into sprite_x)
//   y    = pen y in pixels (also caches into sprite_y)
//
// Walks the string a byte at a time:
//
//   * '#' — hotspot delimiter, alternating open/close.  When
//     opening, allocate a new entry in help_page_hot_spots[],
//     parse the immediately-following ASCII integer (1–4 digits)
//     as the hotspot id via get_number_from_text(), and record
//     the current pen position as the rectangle origin.  When
//     closing, store the current pen x as the rectangle right
//     edge.  Setting linked_text_flag colours subsequent glyphs
//     in highlight colour 0x0D.
//
//     Each hotspot record is 7 shorts (14 bytes):
//
//        +0  id
//        +2  x1 (rectangle left)
//        +4  x2 (rectangle right, closes the spot)
//        +6  y
//        +8  x3 (continued line: second-row left)
//        +A  x4 (continued line: second-row right)
//        +C  (unused)
//
//   * 0x20–0xFF — printable, draws via one_letter(font1, c-' ').
//     Glyphs absent from letter_table[] (width 0) fall back to a
//     plain 4-pixel advance.
//
//   * < 0x20 — skipped, just consumes the byte.
//
// On NUL: if a hotspot is still open, close it with the current
// pen x in the +4 slot; then advance x_is by 4 (line padding).
//
// BYTE-EXACT 2026-06-12 (was 298 b), first compile after re-reading
// the Mac PPC oracle: (1) NO `hot` pointer cache and NO `num` local
// — every hotspot access is a direct `help_page_hot_spots[this_spot]
// .field` (Mac recomputes this_spot*0xe per access; Watcom CSEs the
// offset at the loop head), and the digit-skip chain RE-READS the
// just-stored .page field per compare (PS: movsx from the array,
// L305-308, nested if/else-if — not the old `num > 9 && num <= 99`
// flat chain); (2) the open-hotspot x3 stamp is PRE-LOOP only, and
// on NUL the close goes to x2 — the old body re-stamped x3 every
// iteration and never closed x2 (semantic fix); (3) `c` is a CHAR
// living in AL (byte sub/test; compares zero-extend per use — an
// int c forces wrong widening), with the `c = 1;` sentinel ending
// the '#' arm so the SEPARATE `if (c >= 0x20)` render block skips
// (PS: mov al,1 at L310 — the arms are NOT an else-if chain);
// (4) source statement order text++/this_spot=/.../nof++/flag=1
// follows the -d1 line records (L298→L304); Watcom's const-1 EBP
// cache (Rule 110) and the colour if/else fall out for free.
void put_a_media_string(char *text, int x, int y)
{
    char c;
    int  width;

    sprite_x   = x;
    font_style = 0;
    c = *text;
    if (linked_text_flag)
        help_page_hot_spots[this_spot].x3 = sprite_x;
    while (c != 0) {
        sprite_y = y;
        if (c == '#') {
            if (linked_text_flag) {
                /* Closing tag: write the right edge into either
                 * the primary or the continuation slot, depending
                 * on whether this spot has already wrapped. */
                linked_text_flag = 0;
                if (help_page_hot_spots[this_spot].x2 == 0)
                    help_page_hot_spots[this_spot].x2 = sprite_x;
                else
                    help_page_hot_spots[this_spot].x4 = sprite_x;
            } else {
                /* Opening tag.  Allocate a fresh hotspot, parse
                 * the id digits, and stamp the rectangle origin. */
                text++;
                this_spot = nof_hot_spots;
                help_page_hot_spots[this_spot].page = get_number_from_text(text);
                help_page_hot_spots[this_spot].x1 = sprite_x;
                help_page_hot_spots[this_spot].y = sprite_y - 2;
                nof_hot_spots++;
                linked_text_flag = 1;
                /* get_number_from_text consumed one digit; if the
                 * id was multi-digit, skip the remainder so the
                 * loop doesn't try to render the digits as text. */
                if (help_page_hot_spots[this_spot].page > 9) {
                    if (help_page_hot_spots[this_spot].page <= 99)
                        text += 1;
                    else if (help_page_hot_spots[this_spot].page <= 999)
                        text += 2;
                    else
                        text += 3;
                }
            }
            c = 1;
        }
        if (c >= 0x20) {
            if (linked_text_flag)
                sprite_colour = 0x0d;
            else
                sprite_colour = 0x10;
            c -= 0x20;
            if (letter_table[c] > 0)
                width = one_letter(font1, c);
            else
                width = 4;
            sprite_x += width;
            x_is     += width;
        }
        text++;
        c = *text;
    }
    if (linked_text_flag)
        help_page_hot_spots[this_spot].x2 = sprite_x;
    x_is += 4;
}

// FUNCTION: C2 0x58828
// WIN: 0x00452f00
// Lines 329–358
//
// Hit-test the current mouse position against the help-screen hot
// spots.  Each entry of help_page_hot_spots is 14 bytes (7 shorts):
//   [0] = target page id
//   [1]..[2] = primary x range (x_min, x_max)
//   [3] = y top
//   [4]..[5] = optional secondary-row x range (a second 18px-high
//              hit-box stacked below the first; zero x_min means "no
//              second row").
// Returns 1 (with this_help_page latched and the history pushed) on
// hit, 0 otherwise.  Tail-merges into the shared 6-register pop/ret
// at 0x584a2.
int get_linked_page(void)
{
    int i;
    int x_w;
    int y_top;

    /* BYTE-EXACT 2026-06-12 via Mac oracle + line skeleton + Cascade
     * verdict.  The Mac PPC disasm is literal about the second row:
     * subf r29 REUSES the x_w slot (x_w = x4 - x3, no separate sec_w),
     * the x3 test is direct (one mark at orig line 346, no named
     * sec_min), and addi r27,r27,0x12 updates y_top IN PLACE -- with no
     * line mark at 348 the += must be EMBEDDED in the call argument
     * (mouse_in_area(..., y_top += 0x12, ...)).  That extra def+use
     * lifts sav(y_top) over sav(i) (40 -> >41 vs 41), exactly the
     * SAVINGS relation the Cascade verdict demanded (i had sav 41 =
     * 4 d1-refs + the d0 init; decl-order levers were provably dead).
     * PS's `lea edx,[edi+0x12]` does not contradict the +=: y_top is
     * dead after the call, so wcc386 elides the store-back. */
    for (i = 0; i < nof_hot_spots; i++) {
        x_w   = help_page_hot_spots[i].x2 - help_page_hot_spots[i].x1;
        y_top = help_page_hot_spots[i].y;
        if (mouse_in_area(help_page_hot_spots[i].x1, y_top, x_w, 0x12)) {
            push_forward_help_history();
            this_help_page = help_page_hot_spots[i].page;
            return 1;
        }

        if (help_page_hot_spots[i].x3 == 0) continue;
        x_w = help_page_hot_spots[i].x4 - help_page_hot_spots[i].x3;
        if (mouse_in_area(help_page_hot_spots[i].x3, y_top += 0x12, x_w, 0x12)) {
            push_forward_help_history();
            this_help_page = help_page_hot_spots[i].page;
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x588B9
// WIN: 0x0045307e
// Lines 361–366
//
// Append the current help page to the history buffer at the
// action cursor, then advance the cursor (capped at 0xC7).
void push_forward_help_history(void)
{
    help_history[this_help_action] = this_help_page;
    if (this_help_action < 0xc7)
        this_help_action++;
}

// FUNCTION: C2 0x588E2
// WIN: 0x004530b7
// Lines 368–373
//
// Step the help history back one slot, loading the prior
// page index.  No-op if already at the start.
void rewind_help_history(void)
{
    if (this_help_action > 0) {
        this_help_action--;
        this_help_page = help_history[this_help_action];
    }
}

// FUNCTION: C2 0x58907
// WIN: 0x004530ec
// Lines 375–381
//
// Reset the help history: jump to first page, zero the
// action cursor, and wipe the 200-entry history buffer.
// The fill loop lowers to `call __STOSB`; see file header for
// why the source can't have been memset() in 32-bit Watcom 10.0a.
void init_help_history(void)
{
    int i;

    this_help_page = first_help_page;
    this_help_action = 0;
    for (i = 0; i < 0xc8; i++)
        help_history[i] = 0;
}

// FUNCTION: C2 0x5892D
// WIN: 0x0045313c
// Lines 387–423
//
// Run the tutorial: stash the player's real skill_level / peace_mode,
// force easiest-skill peace-mode, zero the calendar back to -200 BC,
// clear the empire and seed the starting province, then loop
// do_a_tutorial_page() until tutorial_page >= 0x20.  Restore the
// original c2inf flags, ask the user whether to start a real game
// (confirm 0xe), latch continue_tutorial_status on Yes, then
// black_out + cover_mouse_droppings + clear_a_screen and tail-merge
// into the shared 6-register pop epilogue at 0x584a2.
void do_tutorial(void)
{
    int saved_skill = c2inf.skill_level;
    int saved_peace = (signed char)c2inf.peace_mode;

    c2inf.skill_level   = 0;
    c2inf.peace_mode    = 1;
    tutorial_page       = 0;
    tutorial_mode       = 1;
    province_difficulty = 1;
    year                = -200;
    start_year          = -200;
    month               = 0;
    week                = 0;
    players_denarii     = 0;
    players_salary      = init_salary[0].welfare_bill;
    init_tribute();
    years_elapsed       = 0;
    completed_provinces = 0;
    player_rank         = 0;

    clear_empire();
    setup_history_data();
    new_province();
    black_out();

    while (tutorial_page < 0x20) {
        do_a_tutorial_page();
    }

    tutorial_mode = 0;
    c2inf.skill_level = (signed char)saved_skill;
    c2inf.peace_mode  = saved_peace;

    confirm(0xe, 0xa0, 0xa0);
    if (decision == 1) {
        continue_tutorial_status = 1;
    }

    black_out();
    cover_mouse_droppings();
    clear_a_screen();
    hold_mouse_replace = 1;
}

// FUNCTION: C2 0x58A24
// WIN: 0x004532dc
// Lines 427–505
//
// Render and run one page of the in-game tutorial.
//
// Per page:
//   1. tut_files[page] holds the .pl8 image filename;
//      tut_palfiles[page] is the matching .256 palette.
//      Each table entry is 14 bytes (zero-padded ASCIIZ).  If the
//      pl8 file is missing, skip the page (out4=0; ++page) — but
//      FALL THROUGH to the challenge wrap-up (PS's skip jmp lands
//      on L477, the active_tutorial_pages dispatch, NOT the
//      epilogue), so a challenge attached to the next page still
//      arms and stop_db() still runs.
//   2. show_pl8file(image, 0x1E0) paints the page.
//      readfile() pulls the palette into temp_palette.
//   3. load_media_entry() loads the page's MED record (text +
//      title + narration filename) into this_media_entry /
//      format_buffer.
//   4. put_a_font_string draws the title;
//      media_text_place wraps the body into the page's text rect
//      stored in this_media_entry[+4..+9] (x, y_top, width).
//   5. Three navigation arrows (font_list idx 1/2/3) at fixed
//      bottom-row positions + an exit button.
//   6. Plays narration via set_db_sound when media_voc is set.
//
// Then loops just_idle_game_loop() until either:
//   * exit_screen() returns true (user clicks X) — jumps page to
//     0x20 and calls do_pos().
//   * The user clicks one of the three nav rectangles
//     (act_back/middle/forward_tutorial_page).
//
// Finally, if active_tutorial_pages[page] is non-zero, this page
// has an interactive challenge attached: it sets tutorial_level
// to that byte, arms the 0x13B9-tick timer, dispatches to either
// the province or city map (depending on the challenge code 5/8
// vs anything else), and enters main_game_loop() until
// tutorial_timer expires or tutorial_correct fires for 100 ticks
// (in which case show_please_wait/wait_click and out4=1).
//
// Byte-exact (was 219b parked).  Two load-bearing source facts:
//   * the challenge-wrap-up reads the GLOBAL `tutorial_level` directly
//     (no local `level`) at the guard and the ==5/==8 dispatch — Watcom
//     CSEs the just-stored value, and the absence of the extra local
//     seats the post-loop rover scratch (out4 -> ESI) the way PS does.
//   * the out1 idle loop is written as an explicit top-tested goto loop
//     (Rule 92 / §5b): a structured `while (out1 == 0)` lets Watcom
//     rotate the loop and OptPull-hoist the exit-arm constants
//     (out1=1 / tutorial_page=0x20) into preheader registers, which PS
//     keeps as in-place `mov [m], imm` stores.
void do_a_tutorial_page(void)
{
    char *image_path;
    char *pal_path;
    int x;
    int y;
    int w;

    image_path = tut_files[tutorial_page].name;
    pal_path   = tut_palfiles[tutorial_page].name;

    /* `out4 = 0;` shares the if's source line: PS's -d1 stream keeps
       the (eax-CSEd) store inside the L436 run, with L437 on the
       increment alone. */
    if (!check_file_exists(image_path)) { out4 = 0;
        tutorial_page++;
    } else {

    last_tutorial_page = tutorial_page;
    setup_whole_screen_refresh();
    show_pl8file(image_path, 0x1e0);
    readfile(pal_path, temp_palette, 0x300, 0);

    this_help_page = tutorial_page + 0x3c;
    load_media_entry();
    text_pointer = format_buffer;

    x = this_media_entry.left_sprite;
    y = this_media_entry.right_sprite;
    w = this_media_entry.width;
    put_a_font_string(text_pointer, x, y, font2, 0x10);
    media_text_place(x, y + 0x1e, w, 1, x, w, font1);

    /* Bottom-row navigation arrows */
    font_list(0x31, 1, 0xa0, 0x1a0, font1, 0x10);
    font_list(0x31, 2, 0xa0, 0x1b0, font1, 0x10);
    font_list(0x31, 3, 0xa0, 0x1c0, font1, 0x10);
    font_list(0x31, 4, 0x1b0, 0x1b4, font1, 0x10);

    show_an_exit_button(0x250, 0x1b0);
    hold_mouse_replace = 1;
    refresh_svga_screen();
    set_palette(temp_palette);

    if (media_voc) set_db_sound(this_media_entry.voc_file);

    out1 = 0;
    out4 = 0;
  out1_loop:
    if (out1 != 0) goto out1_done;
    just_idle_game_loop();
    if (exit_screen()) {
        out1          = 1;
        tutorial_page = 0x20;
        do_pos();
    }
    if (mouse_left_preclick) {
        if (mouse_in_area(0x18, 0x1a8, 0x20, 0x20)) act_back_tutorial_page();
        if (mouse_in_area(0x40, 0x1a8, 0x20, 0x20)) act_middle_tutorial_page();
        if (mouse_in_area(0x68, 0x1a8, 0x20, 0x20)) act_forward_tutorial_page();
    }
    goto out1_loop;
  out1_done: ;

    }

    /* Interactive-challenge wrap-up */
    tutorial_level = active_tutorial_pages[tutorial_page] & 0xff;
    if (tutorial_level != 0 && out4 == 0) {
        tutorial_timer         = 0x13b9;
        tutorial_correct       = 0;
        tutorial_correct_timer = 0;
        if (tutorial_level == 5)      act_goto_prov_map();
        else if (tutorial_level == 8) act_goto_prov_map();
        else                          act_goto_city_map();

        if (map_mode == 0)      city_map_screen(0);
        else if (map_mode == 1) region_map_screen(0);

        while (out4 == 0) {
            main_game_loop();
            if (c2inf.paused == 0) tutorial_timer--;
            if (tutorial_timer < 0) out4 = 1;
            if (tutorial_correct) {
                tutorial_correct_timer++;
                if (tutorial_correct_timer > 0x64) {
                    show_please_wait();
                    wait_click();
                    out4 = 1;
                }
            }
        }
    }

    stop_db();
    /* Tail-merges with show_help_page's 6-pop epilogue at 0x584A2
     * (Rule 15) — the C source ends here. */
}

// FUNCTION: C2 0x58D3B
// WIN: 0x004537a1
// Lines 508–526
//
// Periodic check (every 50 game ticks) during tutorial level 3:
// scan the city map for at least one housing cell (kind 0x82..0xA1)
// whose range_flag (+0xA) has bit 2 or bit 3 set — i.e. the cell
// is currently within forum service range.  When found, arm the
// "correct" countdown (tutorial_correct_timer = 50) and flip
// tutorial_correct = 1 so the tutorial advances.
void tutorial_test_for_forum_access(void)
{
    int y;
    int x;
    unsigned char kind;

    if (tutorial_level != 3) return;
    if (tutorial_timer % 50 != 0) return;
    if (tutorial_correct) return;

    cm_sptr = 0;
    y = 0;
    for ( ; y < 80; y++) {
    for (x = 0; x < 80; x++, cm_sptr += 20) {
        kind = CM_CELL(cm_sptr).base_kind;
        if (kind >= 0x82 && kind <= 0xa1
            && (CM_CELL(cm_sptr).range_flag & 0x0c) != 0) {
            tutorial_correct_timer = 50;
            tutorial_correct       = 1;
            return;
        }
    }
    }
}

// FUNCTION: C2 0x58DDC
// WIN: 0x00453897
// Lines 528–546
//
// Periodic check (every 50 ticks) during tutorial level 2: scan
// the city map for at least one housing cell whose education
// byte (+0xD) bit 0 is set — i.e. the cell is being supplied with
// water.  When found, flip tutorial_correct = 1 so the tutorial
// advances.  Note this variant does NOT arm the
// tutorial_correct_timer (the forum test does); the difference is
// preserved.
void tutorial_test_for_water_distribution(void)
{
    int y;
    int x;
    unsigned char kind;

    if (tutorial_level != 2) return;
    if (tutorial_timer % 50 != 0) return;
    if (tutorial_correct) return;

    cm_sptr = 0;
    y = 0;
    for ( ; y < 80; y++) {
    for (x = 0; x < 80; x++, cm_sptr += 20) {
        kind = CM_CELL(cm_sptr).base_kind;
        if (kind >= 0x82 && kind <= 0xa1
            && (CM_CELL(cm_sptr).education & 0x01) != 0) {
            tutorial_correct = 1;
            return;
        }
    }
    }
}

// FUNCTION: C2 0x58E6F
// WIN: 0x00453983
// Lines 548–557
//
// Blocking "please wait" system panel.  Draws a fixed 20x8 window,
// schedules a full refresh, prints the heading in font2 followed by
// three explanatory lines in font1, then flushes to the SVGA screen.
void show_please_wait(void)
{
    show_a_system_window(0x50, 0xc0, 0x14, 8);
    setup_whole_screen_refresh();
    font_list(0x31, 0,   0x90, 0xd8, font2, 0x10);
    font_list(0x31, 9,   0x80, 0x100, font1, 0x10);
    font_list(0x31, 0xa, 0xb0, 0x110, font1, 0x10);
    font_list(0x31, 0xb, 0xa0, 0x128, font1, 0x10);
    refresh_svga_screen();
}

// FUNCTION: C2 0x58F16
// WIN: 0x00453a1a
// Lines 559–565
//
// Render the tutorial countdown HUD when `tutorial_mode`
// is on.  Clears a 2-row mosaic at (0x1f4, 0x1b3), prints
// `tutorial_timer / 50` (the timer is in 50-tick units —
// 50 ticks/sec, so this is the seconds value) inside it,
// and refreshes the area.
//
// 2 callers — mmedia.c donor.
void show_tutorial_timer(void)
{
    if (tutorial_mode != 0) {
        show_a_system_blank(0x1f4, 0x1b3, 6, 2);
        font_no(tutorial_timer / 50, ' ', " ", 0x206, 0x1bc, font2, 0x10);
        setup_refresh_area(0x1f4, 0x1b3, 6, 3, 1);
    }
}

// FUNCTION: C2 0x58F8B
// WIN: 0x00453ad1
// Lines 567–577
//
// Walk the tutorial-page index backwards to the previous
// page whose .pl8 file actually exists on disk.  Filename
// stride is 14 bytes per entry.  do_pos / do_neg flip the
// fade-direction flags for the page transition.
void act_back_tutorial_page(void)
{
    while (tutorial_page > 0) {
        tutorial_page--;
        if (check_file_exists(tut_files[tutorial_page].name)) {
            out1 = 1;
            out4 = 1;
            do_pos();
            return;
        }
    }
    do_neg();
}

// FUNCTION: C2 0x58FDB
// WIN: 0x00453b44
// Lines 579–579
void act_middle_tutorial_page(void)
{
    tutorial_page = 7;
    out1          = 1;
    do_pos();
}

// FUNCTION: C2 0x58FF4
// WIN: 0x00453b68
// Lines 580–580
void act_forward_tutorial_page(void)
{
    out1 = 1;
    tutorial_page += 1;
    do_pos();
}

// FUNCTION: C2 0x5900D
// WIN: 0x00453b88
// Lines 584–584
//
// city_icon_allowed holds the merge target at +0x6 for
// region_icon_allowed (which only differs in the lookup table).
int city_icon_allowed(int idx)
{
    return (unsigned char)city_tutorial_icons[idx] <= tutorial_level;
}

// FUNCTION: C2 0x59027
// WIN: 0x00453bbb
// Lines 590–590
int region_icon_allowed(int idx)
{
    return (unsigned char)region_tutorial_icons[idx] <= tutorial_level;
}

// FUNCTION: C2 0x5902F
// WIN: 0x00453bee
// Lines 594–609
//
// In tutorial mode, grey out city-view header icons whose tutorial
// gate returns false.  Icon slots 4..27 are checked against
// city_icon_allowed(slot-4); the rectangle geometry comes from
// int_city_header's 16-byte records, with the X coordinate shifted
// rightward by 0xee pixels.
void grey_city_map_parts(void)
{
    int i;
    int off;
    unsigned short w;
    unsigned short h;
    unsigned short x;
    unsigned short y;

    if (tutorial_mode == 0) return;
    for (i = 4; i < 0x1c; i++) {
        if (city_icon_allowed(i - 4) == 0) {
            off = i * 8;
            w = int_city_header[off + 4];
            h = int_city_header[off + 5];
            x = int_city_header[off + 8] + 0xee;
            y = int_city_header[off + 9];
            draw_a_rect(x, y, w, h, 0x1a);
        }
    }
}

// FUNCTION: C2 0x5909F
// WIN: 0x00453c56
// Lines 611–626
//
// Region-view counterpart to grey_city_map_parts, using the region
// header table and region_icon_allowed over icon slots 4..22.
void grey_region_map_parts(void)
{
    int i;
    int off;

    unsigned short w;
    unsigned short h;
    unsigned short x;
    unsigned short y;

    if (tutorial_mode == 0) return;
    for (i = 4; i < 0x17; i++) {
        if (region_icon_allowed(i - 4) == 0) {
            off = i * 8;
            w = int_region_header[off + 4];
            h = int_region_header[off + 5];
            x = int_region_header[off + 8] + 0xee;
            y = int_region_header[off + 9];
            draw_a_rect(x, y, w, h, 0x1a);
        }
    }
}
