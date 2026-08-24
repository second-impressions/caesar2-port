/*
 * Applies host pause requests with the recovered pause action.
 *
 * The port never decides what pausing means: it reads the engine's own paused
 * flag and calls act_pause() when the state has to change, so map-mode and
 * battle behaviour stay exactly as the recovered code defines them. Only the
 * player's pre-existing choice is remembered here, so closing host chrome
 * cannot resume a game the player had paused themselves.
 */

#include "c2_data.h"
#include "c2_host.h"
#include "c2_port_pause.h"

extern void act_pause(void);

static int c2_pause_restore = -1;

int c2_port_host_pause_active(void)
{
    return c2_pause_restore >= 0;
}

void c2_port_apply_pause_request(void)
{
    int request;

    request = c2_host_take_pause_request();
    if (request < 0) return;
    if (request != 0) {
        if (c2_pause_restore < 0) c2_pause_restore = c2inf.paused != 0;
        if (c2inf.paused == 0) act_pause();
        return;
    }
    if (c2_pause_restore == 0 && c2inf.paused != 0) act_pause();
    c2_pause_restore = -1;
}
