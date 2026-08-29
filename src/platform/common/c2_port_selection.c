#include "c2_port.h"

#if PORT_FEAT_STICKY_REGION_DROPDOWNS
#define PORT_REGION_CLICK_SLOP 4

static int initial_release_pending;
static int opening_x;
static int opening_y;

void c2_port_region_selection_begin(int mouse_x, int mouse_y)
{
    opening_x = mouse_x;
    opening_y = mouse_y;
    initial_release_pending = 1;
}

void c2_port_region_selection_end(void)
{
    initial_release_pending = 0;
}

int c2_port_region_selection_consume_release(int mouse_x, int mouse_y)
{
    int dx;
    int dy;

    if (!initial_release_pending) return 0;
    initial_release_pending = 0;
    dx = mouse_x - opening_x;
    dy = mouse_y - opening_y;
    return dx >= -PORT_REGION_CLICK_SLOP && dx <= PORT_REGION_CLICK_SLOP &&
           dy >= -PORT_REGION_CLICK_SLOP && dy <= PORT_REGION_CLICK_SLOP;
}
#endif
