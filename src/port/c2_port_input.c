#include "c2_asm_routines.h"
#include "c2_data.h"
#include "c2_host.h"

char mouse_background[576];
char mse_button;
char old_mouse_lb;
char old_mouse_rb;
char mouse_right_button;
short mse_x;
short mse_y;
unsigned char decision;
unsigned char exit_flag;
unsigned char mice[8630];
unsigned char mouse_left_button;
unsigned char mouse_left_click;
unsigned char mouse_left_preclick;
unsigned char mouse_right_click;
unsigned char mouse_right_preclick;
unsigned char pointer_mode;
int button_time_flag;
int cycle_count;
int mouse_movement;
int mouse_was_pressed;
int mouse_x;
int mouse_y;
int old_mouse_drops_x;
int old_mouse_drops_y;
int old_mouse_x;
int old_mouse_y;
int out1;
int out2;
int para1;
int para2;
unsigned int randseed = 1;
int rand32000;
int rand128;
int rand8;

extern void xclip(int clip_left, int clip_right);
extern void yclip(int clip_top, int clip_bottom);

static void read_mouse(void)
{
    struct c2_host_input input;

    c2_host_input_snapshot(&input);
    mse_x = input.mouse_x;
    mse_y = input.mouse_y;
    mse_button = 0;
    if ((input.mouse_buttons & C2_HOST_MOUSE_LEFT) != 0) {
        mse_button |= 1;
    }
    if ((input.mouse_buttons & C2_HOST_MOUSE_RIGHT) != 0) {
        mse_button |= 2;
    }
}

void get_mouse(void)
{
    int button_state;

    read_mouse();
    mouse_movement = 0;
    old_mouse_x = mouse_x;
    old_mouse_y = mouse_y;
    old_mouse_lb = mouse_left_button;
    old_mouse_rb = mouse_right_button;
    mouse_x = mse_x;
    mouse_y = mse_y;

    mouse_left_button = 0;
    mouse_left_preclick = 0;
    mouse_left_click = 0;
    mouse_right_button = 0;
    mouse_right_preclick = 0;
    mouse_right_click = 0;

    if ((mse_button & 2) != 0) mouse_right_button = 1;
    if ((mse_button & 1) != 0) mouse_left_button = 1;

    if (old_mouse_x != mouse_x) mouse_movement = 1;
    if (old_mouse_y != mouse_y) mouse_movement = 1;

    if (mouse_left_button != old_mouse_lb) {
        button_state = 1;
        mouse_movement = button_state;
        mouse_was_pressed = button_state;
        if (mouse_left_button == button_state) {
            mouse_left_preclick = 1;
        } else if (mouse_left_button == 0) {
            mouse_left_click = 1;
        }
    }
    if (mouse_right_button != old_mouse_rb) {
        button_state = 1;
        mouse_movement = button_state;
        mouse_was_pressed = button_state;
        if (mouse_right_button == button_state) {
            mouse_right_preclick = 1;
        } else if (mouse_right_button == 0) {
            mouse_right_click = 1;
        }
    }
}

void clear_mouse(void)
{
    do {
        get_mouse();
        if (mouse_left_button != 0 || mouse_right_button != 0) {
            c2_host_sleep_ms(1);
        }
    } while (mouse_left_button != 0 || mouse_right_button != 0);
    mouse_right_click = 0;
    mouse_left_click = 0;
    mouse_right_preclick = 0;
    mouse_left_preclick = 0;
}

void show_mouse(int image_idx)
{
    data_ptr = image_idx * 16 + 8;
    sprite_width = mice[data_ptr] + (mice[data_ptr + 1] << 8);
    sprite_height = mice[data_ptr + 2] + (mice[data_ptr + 3] << 8);
    sprite_start = mice[data_ptr + 4] + (mice[data_ptr + 5] << 8);
    if (sprite_start > 0x4baf0 || sprite_width <= 0 || sprite_width > 300 ||
        sprite_height <= 0 || sprite_height > 300) {
        return;
    }
    sprite_x = mouse_x;
    sprite_y = mouse_y;
    xclip(0, screen_width);
    yclip(0, screen_height);
    if (yclipped == 5) return;
    if (xclipped == 1) {
        write_i_left_sprite(mice);
    } else if (xclipped == 2) {
        write_i_right_sprite(mice);
    } else {
        write_i_sprite(mice);
    }
}

void get_mouse_droppings(void)
{
    sprite_x = mouse_x;
    sprite_y = mouse_y;
    if (sprite_x < 0) sprite_x = 0;
    if (sprite_y < 0) sprite_y = 0;
    if (screen_width - 24 < sprite_x) sprite_x = screen_width - 24;
    if (screen_height - 24 < sprite_y) sprite_y = screen_height - 24;
    old_mouse_drops_x = sprite_x;
    old_mouse_drops_y = sprite_y;
    pick_up_mouse_background(mouse_background);
}

void cover_mouse_droppings(void)
{
    if (hold_mouse_replace != 0) {
        hold_mouse_replace = 0;
        return;
    }
    sprite_x = old_mouse_drops_x;
    sprite_y = old_mouse_drops_y;
    put_down_mouse_background(mouse_background);
}

int mouse_in_area(int x, int y, int width, int height)
{
    return x <= mouse_x && mouse_x < x + width &&
           y <= mouse_y && mouse_y < y + height;
}

int running_delay1(void)
{
    static uint64_t last_ticks;
    uint64_t ticks;
    uint64_t elapsed;

    c2_host_sleep_ms(1);
    ticks = c2_host_ticks_ms();
    elapsed = ticks >= last_ticks ? ticks - last_ticks : 999;
    last_ticks = ticks;
    return elapsed <= 999 ? (int)elapsed : 999;
}

static int big_random(void)
{
    int i;
    unsigned int bit;

    for (i = 0; i < 31; i++) {
        bit = (randseed & 1) ^ ((randseed & 0x10) >> 4);
        randseed >>= 1;
        if (bit != 0) randseed |= 0x40000000;
    }
    return (int)(randseed & 0x7fff);
}

void random(void)
{
    rand32000 = big_random();
    rand128 = rand32000 & 0x7f;
    rand8 = rand32000 & 7;
}

void continue_db(void)
{
}

void stop_db(void)
{
}

void play_speech(int speech_idx)
{
    (void)speech_idx;
}

void test_beeps(void)
{
}
