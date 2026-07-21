#include "c2_data.h"
#include "c2_host.h"

extern void exit_game(void);

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

    c2_host_input_snapshot(&input);
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
}

void mouserange(int xmin, int ymin, int xmax, int ymax)
{
    (void)xmin;
    (void)ymin;
    (void)xmax;
    (void)ymax;
}

void get_key(void)
{
    struct c2_host_event event;

    key_ready = 0;
    key_ascii = 0;
    key_code = 0;
    while (c2_host_wait_event(&event, 0)) {
        if (event.type == C2_HOST_EVENT_QUIT) {
            exit_game();
            return;
        }
        if (event.type != C2_HOST_EVENT_KEY_DOWN) continue;
        key_ready = 1;
        key_ascii_was = key_ascii;
        if (event.key == C2_HOST_KEY_ESCAPE) key_ascii = 0x1b;
        else if (event.key == C2_HOST_KEY_RETURN) key_ascii = 0x0d;
        else if (event.key == C2_HOST_KEY_SPACE) key_ascii = 0x20;
        else if (event.key == C2_HOST_KEY_LEFT) key_code = 0x4b;
        else if (event.key == C2_HOST_KEY_RIGHT) key_code = 0x4d;
        else if (event.key == C2_HOST_KEY_P) key_ascii = 'p';
        else key_ready = 0;
        return;
    }
}
