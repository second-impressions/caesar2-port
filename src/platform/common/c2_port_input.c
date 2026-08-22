#include "c2_data.h"
#include "c2_host.h"
#include "c2_port.h"
#include "c2_port_keymap.h"

extern void exit_game(void);

unsigned int c2_port_scroll_keys(void)
{
    struct c2_host_input input;
    unsigned int keys;

    c2_host_input_snapshot(&input);
    keys = 0;
    if ((input.arrow_keys & C2_HOST_ARROW_LEFT) != 0) {
        keys |= PORT_SCROLL_LEFT;
    }
    if ((input.arrow_keys & C2_HOST_ARROW_RIGHT) != 0) {
        keys |= PORT_SCROLL_RIGHT;
    }
    if ((input.arrow_keys & C2_HOST_ARROW_UP) != 0) {
        keys |= PORT_SCROLL_UP;
    }
    if ((input.arrow_keys & C2_HOST_ARROW_DOWN) != 0) {
        keys |= PORT_SCROLL_DOWN;
    }
    return keys;
}

int init_mouse(void)
{
    mouse_installed = 1;
    return 1;
}

void de_install_mouse(void)
{
    mouse_installed = 0;
}

void read_mouse(void)
{
    struct c2_host_input input;

    c2_host_input_poll(&input);
    mse_x = (short)input.mouse_x;
    mse_y = (short)input.mouse_y;
    mse_button = 0;
    if ((input.mouse_buttons & C2_HOST_MOUSE_LEFT) != 0) {
        mse_button |= 1;
    }
    if ((input.mouse_buttons & C2_HOST_MOUSE_RIGHT) != 0) {
        mse_button |= 2;
    }
    if (input.quit_requested || c2_host_shutdown_requested()) {
        exit_game();
    }
}

void set_mouse(void)
{
    c2_host_set_mouse_position(mse_x, mse_y);
}

void mouserange(int xmin, int ymin, int xmax, int ymax)
{
    c2_host_set_mouse_bounds(xmin, ymin, xmax, ymax);
}

void get_key(void)
{
    struct c2_host_event event;
    unsigned char ascii;
    unsigned char scan_code;

    key_ready = 0;
    key_ascii = 0;
    key_code = 0;
    while (c2_host_wait_event(&event, 0)) {
        if (event.type == C2_HOST_EVENT_QUIT) {
            exit_game();
            return;
        }
        if (!c2_port_event_to_legacy_key(&event, &ascii, &scan_code)) continue;
        key_ready = 1;
        key_ascii_was = key_ascii;
        key_ascii = (char)ascii;
        key_code = (char)scan_code;
        return;
    }
}
