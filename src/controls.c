//

#include "c2_data.h"
#include "c2_types.h"
#include "refresh.h"

char button_speed_profile[40] = { 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 1, 1, 0, 1 };


extern int  get_string_width(char *src, unsigned char *font);
extern void font_list(int idx, int word_count, int x, int y, unsigned char *font, int color);
extern void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color);
extern void font_format_split(int idx, int word_skip, int x, int y_start, int max_width, int line_limit, int x_overflow, int max_width_overflow, unsigned char *font, int color);
extern void place_16x16_block(unsigned char *panel_addr);
extern void place_24x24_block(unsigned char *panel_addr);
extern void place_32x32_block(unsigned char *panel_addr);

// Render the top-bar menu strip. Each menu caption is drawn at (x_is, m->y) and gets its bounding
// x1/x2 fields stamped so over_menu / control_menus can hit-test it later.
// FUNCTION: C2 0x2d4a5
// FUNCTION: C2WIN 0x0041ff90
void show_menus(struct menu_rec *menus, int count, int active)
{
    struct menu_rec *m;
    int i;
    int start_x;
    int y;
    int text;
    int width;
    int sx;
    int rx;
    int ry;
    int xspan;
    int yspan;

    cover_mouse_droppings();
    hold_mouse_replace = 1;
    x_is = 0;
    x_is = menus->u.start_x;
    start_x = x_is;
    m = menus;
    for (i = 1; i <= count; i++) {
        text = m->text;
        m->u.pos.x1 = x_is;
        sx = (short)x_is;
        y = m->y;
        if (i == active) {
            get_text_pointer(text, 0);
            width = (get_string_width(text_pointer, font1) + 4) / 16 + 2;
            sprite_width = width;
            sprite_height = 0xf;
            show_fast_rect(sx - 2, y - 1, 0x10);
            font_list(text, 0, sx, y, font1, 0x1a);
        } else {
            get_text_pointer(text, 0);
            width = (get_string_width(text_pointer, font1) + 4) / 16 + 2;
            sprite_width = width;
            sprite_height = 0xf;
            show_fast_rect(sx - 2, y - 1, 0x1a);
            font_list(text, 0, sx, y, font1, 0x10);
        }
        m->u.pos.x2 = x_is;
        x_is += 0x20;
        m++;
    }
    ref_x = (start_x - 2) / 16;
    ref_y = (y - 1) / 16;
    xspan = (x_is - start_x - 2) / 16 + 2;
    yspan = 2;
    for (ry = ref_y; ry < ref_y + yspan; ry++)
        for (rx = ref_x; rx < ref_x + xspan; rx++)
            svga_refresh_table[rx + ry * 40] = 2;
}

// Drop-down pane for an open menu: paints the background mosaic at (x, y + 0x12) then `count` item
// captions 20 px apart; the active row is highlighted via show_fast_rect + reversed colours.
// FUNCTION: C2 0x2d66e
// FUNCTION: C2WIN 0x004201d2
void show_menu_items(struct menu_item_rec *items, int x, int y, int text_group, int count, int active)
{
    struct menu_item_rec *it;
    int i;
    int row_y;
    int text_idx;
    int rx;
    int ry;
    int xspan;
    int yspan;

    sprite_width = 9;
    sprite_height = count * 20 + 4;
    show_fast_rect(x, y + 0x12, 0x1a);
    it = items;
    for (i = 1; i <= count; i++) {
        text_idx = it->text;
        row_y = y + 0x18 + it->y;
        if (i == active) {
            sprite_width = 9;
            sprite_height = 0xf;
            show_fast_rect(x, row_y - 1, 0x10);
            font_list(text_group, text_idx, x + 0x10, row_y, font1, 0x1a);
        }
        else font_list(text_group, text_idx, x + 0x10, row_y, font1, 0x10);
        it++;
    }
    ref_x = x / 16;
    ref_y = (y + 0x12) / 16;
    xspan = 10;
    yspan = (count * 20 + 4) / 16 + 2;
    for (ry = ref_y; ry < ref_y + yspan; ry++)
        for (rx = ref_x; rx < ref_x + xspan; rx++) svga_refresh_table[rx + ry * 40] = 2;
}

// Show the selection panel as a system window: covers the mouse droppings, marks the screen as
// held for replace, then defers to `show_a_system_window` after converting the selection's pixel
// width/height into cell counts (÷16, signed).
// FUNCTION: C2 0x2d7bd
// FUNCTION: C2WIN 0x0042036d
void show_selection_box(int p1, int x, int y, int p4)
{
    (void)p1;
    (void)p4;
    cover_mouse_droppings();
    hold_mouse_replace = 1;
    show_a_system_window(x, y,
                         (select_width + select_cost_flag) / 16,
                         select_height / 16);
}

// Walk a selection_rec array and mark which rows are visible to the user. An entry is dropped when
// list->max_population exceeds the current city population or when its goods_kind is not in the
// allowed list (per check_selection_goods_list).
// FUNCTION: C2 0x2d80c
// FUNCTION: C2WIN 0x004203b8
void get_allowed_selections(struct selection_rec *list, int count, int what)
{
    int i;
    int max_cost;
    int cost;

    select_count = 0;
    select_width = 0;
    select_height = 0;
    select_cost_flag = 0;
    max_cost = 0;
    for (i = 1; i <= count; i++) {
        if (list->max_population > max_population) {
            list->visible = 0;
        } else if (check_selection_goods_list(list->goods_kind) == 0) {
            list->visible = 0;
        } else {
            list->visible = 1;
            select_count++;
            get_text_pointer(what, list->text_word);
            cost = get_string_width(text_pointer, font1);
            if (cost > select_width) select_width = cost;
            if (list->cost_kind != 0) {
                if (map_mode == 0) cost = city_costs[list->cost_kind];
                else cost = region_costs[list->cost_kind];
                if (cost > max_cost) max_cost = cost;
            }
        }
        list->highlighted = check_highlight_list(list->goods_kind) != 0;
        list++;
    }
    if (max_cost <= 0) select_cost_flag = 0;
    else if (max_cost < 100) select_cost_flag = 0x30;
    else if (max_cost < 1000) select_cost_flag = 0x40;
    else select_cost_flag = 0x50;
    select_height = select_count * 20 + 0x20;
    select_width += 0x30;
}

// Zero-fill loop.
// FUNCTION: C2 0x2d942
// FUNCTION: C2WIN 0x004205ad
void clear_highlight_goods_list(void)
{
    int i;

    for (i = 0; i < 17; i++)
        highlight_goods_list[i] = 0;
}

// Build the goods-selection list. Mode 0 lists active industry kinds and marks already-established
// industries in highlight_goods_list; modes 1..3 copy the three import/export/source slots for the
// current province from region_sources.
// FUNCTION: C2 0x2d958
// FUNCTION: C2WIN 0x004205e6
void get_selection_goods_list(int mode)
{
    int i;

    for (i = 0; i < 17; i++)
        selection_goods_list[i] = 0x10;
    if (mode == 0) {
        for (i = 0; i < 0x10; i++) {
            if (industry[i].status == 1) highlight_goods_list[i] = 1;
            else highlight_goods_list[i] = 0;
            if (industry[i].status != 0) {
                selection_goods_list[i] = i;
            }
        }
    }
    if (mode == 1) {
        for (i = 0; i < 3; i++) {
            selection_goods_list[i] = region_sources[province_is].choices[i];
        }
    } else if (mode == 2) {
        for (i = 0; i < 3; i++) {
            selection_goods_list[i] = region_sources[province_is].choices[3 + i];
        }
    } else if (mode == 3) {
        for (i = 0; i < 3; i++) {
            selection_goods_list[i] = region_sources[province_is].choices[6 + i];
        }
    }
}

// Return 1 if `val` occurs in selection_goods_list, otherwise return 0.
// FUNCTION: C2 0x2da47
// FUNCTION: C2WIN 0x0042077b
int check_selection_goods_list(short val)
{
    int i;
    for (i = 0; i < 0x11; i++) {
        if (val == selection_goods_list[i]) return 1;
    }
    return 0;
}

// True when highlight_goods_list[idx] is non-zero (industry already established / row should be
// marked).
// FUNCTION: C2 0x2da67
// FUNCTION: C2WIN 0x004207cf
int check_highlight_list(short idx)
{
    return highlight_goods_list[idx] != 0;
}

// Paint the selection list (build menu, forum trade-good list, ...). Walks `count` entries; only
// ones flagged visible by get_allowed_selections draw.
// FUNCTION: C2 0x2da7a
// FUNCTION: C2WIN 0x004207ff
void show_selections(struct selection_rec *list, int count, int x, int y, int what, int selected)
{
    struct selection_rec *p;
    int i;
    int shown;
    int row_y;
    int cost;
    int rx;
    int ry;
    int xspan;
    int yspan;
    int word_count;

    sprite_width = select_width / 16 - 1;
    sprite_width += select_cost_flag / 16;
    sprite_height = select_height - 0x18;
    show_fast_rect(x + 8, y + 8, 0x1a);
    p = list;
    shown = 0;
    for (i = 1; i <= count; i++) {
        if (p->visible != 0) {
            word_count = p->text_word;
            row_y = y + 0xc + shown * 20;
            if (p->cost_kind != 0) {
                if (map_mode == 0) cost = city_costs[p->cost_kind];
                else cost = region_costs[p->cost_kind];
            } else {
                cost = 0;
            }
            if (selected - 1 == shown) {
                sprite_width = select_width / 16 - 1;
                sprite_width += select_cost_flag / 16;
                sprite_height = 0xf;
                show_fast_rect(x + 8, row_y - 1, 0x10);
                font_list(what, word_count, x + 8, row_y, font1, 0x1a);
                if (cost != 0)
                    font_no(cost, 0x40, "Dn", x + select_width - 0x10, row_y, font1, 0x1a);
            } else {
                if (p->highlighted != 0)
                    font_list(what, word_count, x + 8, row_y, font1, 0xb);
                else
                    font_list(what, word_count, x + 8, row_y, font1, 0x10);
                if (cost != 0) {
                    if (p->highlighted != 0)
                        font_no(cost, 0x40, "Dn", x + select_width - 0x10, row_y,
                                font1, 0xb);
                    else
                        font_no(cost, 0x40, "Dn", x + select_width - 0x10, row_y,
                                font1, 0x10);
                }
            }
            shown++;
        }
        p++;
    }
    ref_x = (x + 8) / 16;
    ref_y = (y + 8) / 16;
    xspan = (select_width + select_cost_flag) / 16;
    yspan = select_height / 16;
    for (ry = ref_y; ry < ref_y + yspan; ry++)
        for (rx = ref_x; rx < ref_x + xspan; rx++)
            svga_refresh_table[rx + ry * 40] = 2;
}

// Generic confirm-dialog panel: a 12×8-cell mosaic-window at (x-0x10, y-0x10) with the
// message-string `what` drawn at (x+0x10, y+0x10) and the confirming_buttons (Y/N) drawn at (x,
// y).
// FUNCTION: C2 0x2dcfc
// FUNCTION: C2WIN 0x00420b2e
void show_confirming_panel(int what, int x, int y)
{
    cover_mouse_droppings();
    hold_mouse_replace = 1;
    show_a_mosaic_window(x - 0x10, y - 0x10, 0xc, 8);
    font_list(0xa, what, x + 0x10, y + 0x10, font1, 0x10);
    show_buttons(x, y, confirming_buttons, 2);
}

// Extended-confirm panel — wider, taller variant of `show_confirming_panel` for messages that need
// more room. A 12×10-cell mosaic window at (x-0x10, y-0x30) with the message wrapped via
// `font_format_split` (90 px wide, max 100 lines) at (x+0x10, y-0x16).
// FUNCTION: C2 0x2dd58
// FUNCTION: C2WIN 0x00420b99
void show_Xconfirming_panel(int what, int x, int y)
{
    cover_mouse_droppings();
    hold_mouse_replace = 1;
    show_a_mosaic_window(x - 0x10, y - 0x30, 0xc, 0xa);
    font_format_split(0xa, what, x + 0x10, y - 0x16,
                      0x90, 0x64, 0, 0, font1, 0x10);
    show_buttons(x, y, confirming_buttons, 2);
}

// Render the "adjust this number" panel (tax rate, prices, ...).
// FUNCTION: C2 0x2dda9
// FUNCTION: C2WIN 0x00420c0f
void show_adjusting_panel(int what, int x, int y, int kind)
{
    cover_mouse_droppings();
    hold_mouse_replace = 1;
    show_a_mosaic_window(x - 0x10, y - 0x10, 0xf, 7);
    show_an_exit_button(x + 0xb4, y + 0x34);
    font_list(0xc, what, x + 0x10, y + 8, font1, 0x10);
    font_list(0xc, 0, x + 0x10, y + 0x3c, font1, 0x10);
    if (kind == 1) {
        font_no(*adjust_var / 10, 0x20, " ", x + 0x64, y + 0x22, font1, 0x10);
    } else if (kind == 2) {
        font_no(*adjust_var, 0x20, " ", x + 0x64, y + 0x22, font1, 0x10);
    } else {
        font_no(*adjust_var, 0x20, "%", x + 0x64, y + 0x22, font1, 0x10);
    }
    show_buttons(x, y, adjusting_buttons, 2);
}

// Render a 5-row x 20-col system window at (x, y) with two caption paragraphs (`what`, `what+1`)
// and a fixed "OK" prompt (paragraph 9, p2=0) below. Sets hold_mouse_replace so the cursor isn't
// redrawn over the panel.
// FUNCTION: C2 0x2de9c
// FUNCTION: C2WIN 0x00420d5d
void show_warning_panel(int what, int x, int y)
{
    cover_mouse_droppings();
    hold_mouse_replace = 1;
    show_a_system_window(x, y, 0x14, 5);
    font_list(0xb, what,     x + 0x10, y + 0x10, font1, 0x10);
    font_list(0xb, what + 1, x + 0x10, y + 0x20, font1, 0x10);
    font_list(9,   0,        x + 0x60, y + 0x3c, font1, 0x10);
}

// Stamp an icon array into the sprite globals. Each icon contributes (x, y, sprite_image_no); the
// pressed image is sprite + 1 when icon->down is non-zero.
// FUNCTION: C2 0x2df1d
// FUNCTION: C2WIN 0x00420df0
void show_icons(struct icon_rec *icons, int count)
{
    int i;
    cover_mouse_droppings();
    hold_mouse_replace = 1;
    for (i = 0; i < count; i++) {
        sprite_x = icons->x;
        sprite_y = icons->y;
        sprite_image_no = icons->sprite;
        if (icons->down != 0)
            sprite_image_no++;
        icons++;
    }
}

// Render `count` UI buttons from a 24-byte-stride record array.
// FUNCTION: C2 0x2df68
// FUNCTION: C2WIN 0x00420e66
void show_buttons(int x, int y, struct button_rec *buttons, int count)
{
    struct button_rec *btn = buttons;
    int n = count;
    int i;
    int size;
    int xspan;
    int yspan;
    int rx;
    int ry;

    for (i = 0; i < n; i++) {
        sprite_x = x + btn->x;
        sprite_y = y + btn->y;
        if (btn->type == 4) {
            sprite_image_no = btn->sprite;
            if (btn->down != 0)
                sprite_image_no = btn->sprite + 1;
        } else {
            if (btn->state == 0)
                sprite_image_no = btn->sprite;
            else
                sprite_image_no = btn->sprite + 1;
        }

        size = btn->size;
        if (size == 0x10)      place_16x16_block(system_panel);
        else if (size == 0x18) place_24x24_block(system_panel);
        else if (size == 0x20) place_32x32_block(system_panel);

        btn++;
        ref_x = sprite_x / 16;
        ref_y = sprite_y / 16;

        if (size == 0x10) {
            xspan = 2;
            yspan = 2;
        } else {
            xspan = 3;
            yspan = 3;
        }
        for (ry = ref_y; ry < ref_y + yspan; ry++) {
            for (rx = ref_x; rx < ref_x + xspan; rx++) {
                svga_refresh_table[rx + ry * 40] = 2;
            }
        }
    }
}


// Render the standard exit-screen "X" button at (x, y). Sprite 0x33 from the system panel sheet;
// (x, y) is also recorded in the global click-target pair so the input layer can later test the
// cursor against this rect.
// FUNCTION: C2 0x2e0a1
// FUNCTION: C2WIN 0x0042102b
void show_an_exit_button(int x, int y)
{
    exit_x_at = x;
    exit_y_at = y;
    sprite_image_no = 0x33;
    sprite_x = x;
    sprite_y = y;
    place_24x24_block(system_panel);
}

// Dispatches mouse input to each slider's decrement button, track, or increment button.
// FUNCTION: C2 0x2e0cb
// FUNCTION: C2WIN 0x0042106d
int slider_control(struct slider_rec *sliders, int count)
{
    int i;
    int step;
    int range;
    int minp;
    int maxp;
    int knob_width;

    if (mouse_left_button == 0) return 0;
    for (i = 0; i < count; i++) {
        step  = sliders->step_pixels;
        range = sliders->slider_range;
        minp  = sliders->min_pixel;
        maxp  = sliders->max_pixel;
        knob_width = (maxp - minp) * step / range;
        if (sliders->y <= mouse_y && sliders->y + 10 > mouse_y) {
            if (sliders->x <= mouse_x && sliders->x + 12 > mouse_x) {
                down_slider_var(sliders);
                return i + 1;
            }
            if (sliders->x + 12 <= mouse_x && sliders->x + knob_width + 12 > mouse_x) {
                mid_slider_var(sliders, mouse_x - 12 - sliders->x);
                return i + 1;
            }
            if (sliders->x + 12 + knob_width <= mouse_x && sliders->x + knob_width + 0x18 > mouse_x) {
                up_slider_var(sliders);
                return i + 1;
            }
        }
        sliders++;
    }
    return 0;
}

// Updates the active slider from the mouse position along its track.
// FUNCTION: C2 0x2e1a1
// FUNCTION: C2WIN 0x004211f2
void mid_slider_var(struct slider_rec *s, int pos)
{
    int slider_range, max, min;
    int step_pixels, val;
    int old;

    old = (signed char)*s->value;
    max = s->max;
    min = s->min;
    step_pixels = s->step_pixels;
    slider_range = s->slider_range;
    s->refresh_flag = 2;
    val = slider_range * pos;
    val /= step_pixels;
    *s->value = val;
    if ((signed char)*s->value >= max) *s->value = max;
    if ((signed char)*s->value < min) *s->value = min;
    if (val < old) *s->complement += (char)(old - val);
    else if (val > old) {
        if ((signed char)*s->complement < val - old) {
            *s->value = (char)(old + (signed char)*s->complement);
            *s->complement = 0;
        }
        else *s->complement -= (char)(val - old);
    }
}

// Step the slider value DOWN by step (clamped to min).
// FUNCTION: C2 0x2e24a
// FUNCTION: C2WIN 0x0042131c
void down_slider_var(struct slider_rec *s)
{
    int old;
    int min;
    int step;
    int t;
    int last;
    int guard;
    int pct;

    if (mouse_left_preclick == 0) return;
    old = (signed char)*s->value;
    min = s->min;
    step = s->step;
    s->refresh_flag = 2;
    s->down_anim = 4;
    if (slidper_on == 0) {
        *s->value -= (char)step;
    } else {
        guard = 100;
        pct = totalXpercent(slider_total, old);
        last = pct;
        while (last == pct && guard != 0 && pct >= min) {
            guard--;
            *s->value -= (char)step;
            pct = totalXpercent(slider_total, (signed char)*s->value);
        }
        if (pct == 0) *s->value = min;
    }
    if ((signed char)*s->value < min)
        *s->value = min;
    t = (signed char)*s->value;
    if (t < old)
        *s->complement += (char)(old - t);
    else if (t > old)
        *s->complement -= (char)(t - old);
}

// Mirror of down_slider_var: step the slider value UP by step (clamped to max). Refuses to act
// when the bundle complement would underflow below min + step.
// FUNCTION: C2 0x2e327
// FUNCTION: C2WIN 0x00421495
void up_slider_var(struct slider_rec *s)
{
    int step;
    int old;
    int max;
    int min;
    int t;
    int last;
    int pct;
    int guard;

    if (mouse_left_preclick == 0) return;
    old = (signed char)*s->value;
    max = s->max;
    min = s->min;
    step = s->step;
    if ((signed char)*s->complement < min + step) return;
    s->refresh_flag = 2;
    s->up_anim = 4;
    if (slidper_on == 0) {
        *s->value += (char)step;
    } else {
        guard = 100;
        pct = totalXpercent(slider_total, old);
        last = pct;
        while (last == pct && guard != 0) {
            guard--;
            *s->value += (char)step;
            pct = totalXpercent(slider_total, (signed char)*s->value);
        }
    }
    if ((signed char)*s->value > max)
        *s->value = max;
    t = (signed char)*s->value;
    if (t < old)
        *s->complement += (char)(old - t);
    else if (t > old)
        *s->complement -= (char)(t - old);
}

// Hit-test an icon array against the current mouse_x/y. On a click inside any 32x32 icon, lifts
// every other icon (de_toggle_all_icons), marks the hit icon as down, loads para1/para2 from the
// record, and fires its callback().
// FUNCTION: C2 0x2e406
// FUNCTION: C2WIN 0x00421613
int control_icons(struct icon_rec *icons, int count)
{
    struct icon_rec *base;
    int i;

    if (mouse_left_preclick == 0) return 0;
    base = icons;
    for (i = 0; i < count; i++) {
        if (icons->x <= mouse_x && icons->x + 0x20 > mouse_x &&
            icons->y <= mouse_y && icons->y + 0x20 > mouse_y) {
            de_toggle_all_icons(base, count);
            para1 = icons->para1;
            para2 = icons->para2;
            icons->down = 1;
            icons->callback();
            return i + 1;
        }
        icons++;
    }
    return 0;
}

// Clear `down` on every icon in the array and mark a 3x3 tile span dirty around each one in
// svga_refresh_table so the panels get repainted with the released sprite next frame.
// FUNCTION: C2 0x2e47b
// FUNCTION: C2WIN 0x004216f6
void de_toggle_all_icons(struct icon_rec *icons, int count)
{
    int i;
    int rx;
    int ry;
    for (i = 0; i < count; i++) {
        icons->down = 0;
        ref_x = icons->x >> 4;
        ref_y = icons->y >> 4;
        for (ry = ref_y; ry < ref_y + 3; ry++)
            for (rx = ref_x; rx < ref_x + 3; rx++)
                if (rx + ry * 40 <= 0x4b0)
                    svga_refresh_table[rx + ry * 40] = 1;
        icons++;
    }
}

// Drive button state for a panel: a first pass updates each button’s `repeat` counter and fires
// the type-4 (auto-repeat / state-2) variant; a second pass hit-tests the cursor against each
// button rect and, depending on type (2 = toggle on click, 3 = momentary, 4.
// FUNCTION: C2 0x2e4f3
// FUNCTION: C2WIN 0x004217c7
int control_buttons(int x, int y, struct button_rec *buttons, int count)
{
    int i;
    int sz;
    int type;
    struct button_rec *p;

    p = buttons;
    for (i = 0; i < count; i++) {
        if (p->down != 0) {
            if (p->repeat == 0) p->repeat = 1;
            else if (button_time_flag != 0) p->repeat++;
        } else {
            p->repeat = 0;
        }
        p->down = 0;
        type = p->type;
        if (type == 4) {
            if (p->repeat == 0) p->state = 0;
            if (p->state != 0) { para1 = p->para1; para2 = p->para2; p->callback(); }
        }
        if (p->type == 3) p->state = 0;
        p++;
    }

    if (mouse_left_button == 0) return 0;
    for (i = 0; i < count; i++) {
        sz = buttons->size;
        if (buttons->x + x <= mouse_x && buttons->x + sz + x > mouse_x)
        if (buttons->y + y <= mouse_y && buttons->y + sz + y > mouse_y) {
            int type = buttons->type;
            if (type == 4) {
                buttons->down = 1;
                if (buttons->repeat == 0) buttons->state = 1;
                else if (button_time_flag != 0) {
                    int t = buttons->repeat;
                    if (t >= 0x30) { buttons->state = 1; buttons->repeat = 0x30; }
                    else if (t < 8) buttons->state = 0;
                    else if (button_speed_profile[t - 8] != 0) buttons->state = 1;
                    else buttons->state = 0;
                } else buttons->state = 0;
                return i + 1;
            }
            if (type == 2) {
                buttons->down = 1;
                if (buttons->repeat == 0) {
                    buttons->state ^= 1;
                    para1 = buttons->para1;
                    para2 = buttons->para2;
                    buttons->callback();
                }
                return i + 1;
            }
            if (type == 3) {
                buttons->down = 1;
                buttons->state = 1;
                if (buttons->repeat == 0) {
                    para1 = buttons->para1;
                    para2 = buttons->para2;
                    buttons->callback();
                }
                return i + 1;
            }
        }
        buttons++;
    }
    return 0;
}

// Run the top-bar menu interaction. Opens the menu the mouse is over (active_menu = over_menu()),
// then loops the standard gloop_start / show_map_fn / show_menu_items / gloop_end pump while
// tracking hover-switches between menus and the current item-under-cursor.
// FUNCTION: C2 0x2e67d
// FUNCTION: C2WIN 0x00421ae2
int control_menus(struct menu_rec *menus, int count, void (*show_map_fn)(void))
{
    int item;
    int active_menu;
    int over;
    int done;
    int over_flag;
    int old_pointer_mode;
    struct menu_rec *m;

    if (mouse_left_preclick == 0) return 0;
    if (tutorial_mode != 0) return 0;
    active_menu = over_menu(menus, count);
    item = 0;
    if (active_menu == 0) return 0;
    old_pointer_mode = pointer_mode;
    pointer_mode = 0;
    m = menus + active_menu - 1;
    show_menus(menus, count, active_menu);
    setup_map_screen_refresh();
    mouse_left_preclick = 0;
    over_flag = 1;
    done = 0;
    while (done == 0) {
        if (mouse_left_button == 0) over_flag = 0;
        gloop_start();
        update_map = 1;
        show_map_fn();
        show_menu_items(m->items, m->u.pos.x1, m->y, m->text, m->item_count, item);
        gloop_end();
        if (over_flag != 0) {
            over = over_menu(menus, count);
            if (over != 0 && active_menu != over) {
                active_menu = over;
                m = menus + active_menu - 1;
                show_menus(menus, count, active_menu);
            }
        }
        item = over_item(m->items, m->item_count, m->u.pos.x1, m->y);
        if (mouse_left_click != 0 && item != 0) done = 1;
        if (mouse_left_preclick != 0) done = 1;
        if (mouse_right_preclick != 0) { done = 1; item = 0; }
    }
    show_menus(menus, count, 0);
    if (item != 0) {
        struct menu_item_rec *it = m->items;
        it += item - 1;
        it->action();
    }
    setup_map_screen_refresh();
    update_map = 1;
    pointer_mode = old_pointer_mode;
    clear_mouse();
    return 1;
}

// Hit-test the mouse against an array of `count` menu rectangles starting at `menu`. Each entry is
// 14 bytes: short x1, x2, y_top, then 8 bytes of caption / payload.
// FUNCTION: C2 0x2e81c
// FUNCTION: C2WIN 0x00421d3c
int over_menu(struct menu_rec *menu, int count)
{
    struct menu_rec *p = menu;
    int i;
    for (i = 1; i <= count; i++) {
        if (p->u.pos.x1 <= mouse_x && p->u.pos.x2 > mouse_x
         && p->y <= mouse_y && p->y + 0xc > mouse_y) {
            return i;
        }
        p++;
    }
    return 0;
}

// Hit-test the mouse against `count` menu items in a column. Each item is a fixed 96×15-pixel
// rectangle whose left edge is `x_start` and whose top is `y_base + 0x17 + items[i].y`.
// FUNCTION: C2 0x2e868
// FUNCTION: C2WIN 0x00421dcb
int over_item(struct menu_item_rec *items, int count, int x_start, int y_base)
{
    struct menu_item_rec *p = items;
    int i;
    for (i = 1; i <= count; i++) {
        int y_top = y_base + 0x17 + p->y;
        if (x_start <= mouse_x && x_start + 0x60 > mouse_x
         && y_top <= mouse_y && y_top + 0xf > mouse_y) {
            return i;
        }
        p++;
    }
    return 0;
}

// Run the selection-panel interaction (build menu, forum trade-good chooser, ...). Calls
// get_allowed_selections to size the panel, clamps (x, y) into the visible area, then pumps the
// gloop loop while over_selection tracks the hovered row.
// FUNCTION: C2 0x2e8bb
// FUNCTION: C2WIN 0x00421e5e
int control_selection(struct selection_rec *list, int count, int x, int y, int what)
{
    int i;
    int visible;

    selection_is = 0;
    get_allowed_selections(list, count, what);
    x -= select_cost_flag;
    if (x < 0) x = 0;
    if (y < 0x18) y = 0x18;
    if (select_width + x >= 0x26c) x = 0x26c - select_width;
    if (select_height + y >= 0x1cc) y = 0x1cc - select_height;
    show_selection_box(count, x, y, what);
    setup_whole_screen_refresh();
    mouse_left_preclick = 0;
    for (;;) {
        gloop_start();
        show_selections(list, count, x, y, what, selection_is);
        gloop_end();
        selection_is = over_selection(select_count, x, y);
        if (mouse_left_click != 0 && selection_is != 0) break;
        if (mouse_left_click != 0 && is_icon_over(last_icon_over) == 0) {
            selection_is = 0;
            break;
        }
        if (mouse_left_preclick != 0 && selection_is != 0) break;
        if (mouse_right_preclick != 0) { selection_is = 0; break; }
    }
    if (selection_is != 0 && selection_is <= select_count) {
        i = 1;
        visible = 1;
        for (; i <= count; i++) {
            if (list->visible != 0) {
                if (visible++ == selection_is) break;
            }
            list++;
        }
        para1 = list->para1;
        list->callback();
        if (selection_is == select_count) selection_is = 0;
        else selection_is = i;
    } else {
        selection_is = 0;
    }
    setup_whole_screen_refresh();
    clear_mouse();
    clear_highlight_goods_list();
    return 1;
}

// Hit-test the mouse cursor against a vertical list of `n` selection items rendered at column `x`,
// starting row `base_y + 7`, with each row 20 pixels tall and `select_width + select_cost_flag`
// pixels wide.
// FUNCTION: C2 0x2ea4f
// FUNCTION: C2WIN 0x004220d2
int over_selection(int n, int x, int base_y)
{
    int i;
    int row_y;

    for (i = 0; i < n; ++i) {
        row_y = base_y + 7 + i * 20;
        if (x <= mouse_x &&
            x + select_width + select_cost_flag > mouse_x &&
            row_y <= mouse_y &&
            row_y + 20 > mouse_y) {
            return i + 1;
        }
    }
    return 0;
}

// Pop a non-modal warning panel and block until the user clicks anywhere. Pumps the gloop loop
// until either mouse button is clicked, then refreshes the screen so the panel is wiped.
// FUNCTION: C2 0x2eaac
// FUNCTION: C2WIN 0x0042216b
void click_warning(int what, int x, int y)
{
    clear_mouse();
    show_warning_panel(what, x, y);
    setup_whole_screen_refresh();
    out1 = 0;
    while (out1 != 1) {
        gloop_start();
        gloop_end();
        if (mouse_left_click != 0 || mouse_right_click != 0) {
            out1 = 1;
        }
    }
    setup_whole_screen_refresh();
}

// Standard Y/N confirm dialog. Renders the panel, pumps the gloop loop while the Y/N buttons drive
// the global `decision`, and exits when a callback sets out1 to 1.
// FUNCTION: C2 0x2eb01
// FUNCTION: C2WIN 0x004221cc
void confirm(int what, int x, int y)
{
    decision = 0;
    pointer_mode = 0;
    show_confirming_panel(what, x, y);
    setup_whole_screen_refresh();
    refresh_svga_screen();
    clear_mouse();
    out1 = 0;
    while (out1 != 1) {
        gloop_start();
        show_buttons(x, y, confirming_buttons, 2);
        gloop_end();
        control_buttons(x, y, confirming_buttons, 2);
        if (out1 > 1) {
            out1 = out1 - 1;
        }
    }
    setup_whole_screen_refresh();
    update_map = 1;
}

// Same as `confirm` but renders the wider X-panel (`show_Xconfirming_panel`) for messages that
// need more room.
// FUNCTION: C2 0x2eb95
// FUNCTION: C2WIN 0x0042222f
void extended_confirm(int what, int x, int y)
{
    decision = 0;
    pointer_mode = 0;
    show_Xconfirming_panel(what, x, y);
    setup_whole_screen_refresh();
    refresh_svga_screen();
    clear_mouse();
    out1 = 0;
    while (out1 != 1) {
        gloop_start();
        show_buttons(x, y, confirming_buttons, 2);
        gloop_end();
        control_buttons(x, y, confirming_buttons, 2);
        if (out1 > 1) {
            out1 = out1 - 1;
        }
    }
    setup_whole_screen_refresh();
    update_map = 1;
}

// Modal "adjust this number" dialog.
// FUNCTION: C2 0x2ec18
// FUNCTION: C2WIN 0x004222ac
void adjust(int kind, int *var, int step, int max, int min, int x, int y, int mode)
{
    adjust_var = var;
    adjust_step = step;
    adjust_max = max;
    adjust_min = min;
    show_adjusting_panel(kind, x, y, mode);
    setup_whole_screen_refresh();
    out1 = 0;
    while (out1 != 1) {
        gloop_start();
        show_buttons(x, y, adjusting_buttons, 2);
        stone_random_count = 0xa;
        show_a_mosaic_blank(x + 0x5c, y + 0x1e, 3, 1);
        if (mode == 1) {
            font_no(*adjust_var / 10, 0x20, " ", x + 0x64, y + 0x22, font1, 0x10);
        } else if (mode == 2) {
            font_no(*adjust_var, 0x20, " ", x + 0x64, y + 0x22, font1, 0x10);
        } else {
            font_no(*adjust_var, 0x20, "%", x + 0x64, y + 0x22, font1, 0x10);
        }
        refresh_a_square((x + 0x64) >> 4, (y + 0x22) >> 4, 1);
        gloop_end();
        control_buttons(x, y, adjusting_buttons, 2);
        if (mouse_right_click != 0) out1 = 4;
        if (exit_screen() != 0) out1 = 1;
        if (out1 > 1) out1--;
    }
    setup_whole_screen_refresh();
}

// Hit-test for the standard exit-X button: returns 1 (and clears the click) if the user just
// left-clicked inside a 24x24 region at (exit_x_at, exit_y_at), 0 otherwise. Pairs with
// show_an_exit_button() which renders the button and stamps the exit_*_at globals.
// FUNCTION: C2 0x2ed7a
// FUNCTION: C2WIN 0x00422479
int exit_screen(void)
{
    if (!mouse_left_preclick) {
        return 0;
    }
    if (mouse_in_area(exit_x_at, exit_y_at, 24, 24)) {
        clear_mouse();
        return 1;
    }
    return 0;
}

// Hit-test for an "exit screen" mouse click. Only fires when the user pressed the left button
// (mouse_left_preclick gates every panel "clickable" region).
// FUNCTION: C2 0x2edb5
// FUNCTION: C2WIN 0x004224d0
int exit_screen_at(int x, int y)
{
    if (!mouse_left_preclick)
        return 0;
    if (mouse_in_area(x, y, 0x18, 0x18)) {
        clear_mouse();
        return 1;
    }
    return 0;
}
