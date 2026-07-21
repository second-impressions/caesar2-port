#include "c2_port_mouse.h"

static double clamp_double(double value, double minimum, double maximum)
{
    if (value < minimum) return minimum;
    if (value > maximum) return maximum;
    return value;
}

static int rounded_position(double value)
{
    return (int)(value + 0.5);
}

static void publish_position(struct c2_port_mouse *mouse)
{
    mouse->precise_x = clamp_double(mouse->precise_x,
                                    mouse->min_x, mouse->max_x);
    mouse->precise_y = clamp_double(mouse->precise_y,
                                    mouse->min_y, mouse->max_y);
    mouse->x = rounded_position(mouse->precise_x);
    mouse->y = rounded_position(mouse->precise_y);
}

int c2_port_mouse_init(struct c2_port_mouse *mouse,
                       int frame_width, int frame_height,
                       int edge_margin)
{
    if (mouse == 0 || frame_width <= 0 || frame_height <= 0 ||
        edge_margin < 0) {
        return 0;
    }
    mouse->frame_width = frame_width;
    mouse->frame_height = frame_height;
    mouse->min_x = 0;
    mouse->min_y = 0;
    mouse->max_x = frame_width;
    mouse->max_y = frame_height;
    mouse->precise_x = frame_width / 2.0;
    mouse->precise_y = frame_height / 2.0;
    mouse->inside = 1;
    mouse->edge_margin = edge_margin;
    publish_position(mouse);
    return 1;
}

int c2_port_mouse_set_bounds(struct c2_port_mouse *mouse,
                             int min_x, int min_y, int max_x, int max_y)
{
    if (mouse == 0 || max_x <= min_x || max_y <= min_y) return 0;
    mouse->min_x = min_x;
    mouse->min_y = min_y;
    mouse->max_x = max_x;
    mouse->max_y = max_y;
    publish_position(mouse);
    return 1;
}

void c2_port_mouse_set_position(struct c2_port_mouse *mouse, int x, int y)
{
    mouse->precise_x = x;
    mouse->precise_y = y;
    mouse->inside = 1;
    publish_position(mouse);
}

void c2_port_mouse_set_absolute(struct c2_port_mouse *mouse,
                                float frame_x, float frame_y)
{
    int margin_x;
    int margin_y;
    double range_x;
    double range_y;

    if (frame_x < 0.0f || frame_y < 0.0f ||
        frame_x >= mouse->frame_width || frame_y >= mouse->frame_height) {
        c2_port_mouse_leave(mouse);
        return;
    }

    margin_x = mouse->edge_margin;
    margin_y = mouse->edge_margin;
    if (margin_x * 2 >= mouse->frame_width) margin_x = 0;
    if (margin_y * 2 >= mouse->frame_height) margin_y = 0;
    range_x = mouse->max_x - mouse->min_x;
    range_y = mouse->max_y - mouse->min_y;

    if (frame_x < margin_x) {
        mouse->precise_x = mouse->min_x;
    } else if (frame_x >= mouse->frame_width - margin_x) {
        mouse->precise_x = mouse->max_x;
    } else {
        mouse->precise_x = mouse->min_x +
            frame_x * range_x / mouse->frame_width;
    }
    if (frame_y < margin_y) {
        mouse->precise_y = mouse->min_y;
    } else if (frame_y >= mouse->frame_height - margin_y) {
        mouse->precise_y = mouse->max_y;
    } else {
        mouse->precise_y = mouse->min_y +
            frame_y * range_y / mouse->frame_height;
    }
    mouse->inside = 1;
    publish_position(mouse);
}

void c2_port_mouse_add_relative(struct c2_port_mouse *mouse,
                                float frame_dx, float frame_dy)
{
    double range_x;
    double range_y;

    range_x = mouse->max_x - mouse->min_x;
    range_y = mouse->max_y - mouse->min_y;
    mouse->precise_x += frame_dx * range_x / mouse->frame_width;
    mouse->precise_y += frame_dy * range_y / mouse->frame_height;
    mouse->inside = 1;
    publish_position(mouse);
}

void c2_port_mouse_leave(struct c2_port_mouse *mouse)
{
    mouse->inside = 0;
    if (mouse->x <= mouse->min_x) mouse->precise_x = mouse->min_x + 1;
    if (mouse->x >= mouse->max_x) mouse->precise_x = mouse->max_x - 1;
    if (mouse->y <= mouse->min_y) mouse->precise_y = mouse->min_y + 1;
    if (mouse->y >= mouse->max_y) mouse->precise_y = mouse->max_y - 1;
    publish_position(mouse);
}

void c2_port_mouse_get_frame_position(const struct c2_port_mouse *mouse,
                                      float *frame_x, float *frame_y)
{
    double range_x;
    double range_y;
    double x;
    double y;

    range_x = mouse->max_x - mouse->min_x;
    range_y = mouse->max_y - mouse->min_y;
    x = (mouse->precise_x - mouse->min_x) * mouse->frame_width / range_x;
    y = (mouse->precise_y - mouse->min_y) * mouse->frame_height / range_y;
    x = clamp_double(x, 0, mouse->frame_width - 1);
    y = clamp_double(y, 0, mouse->frame_height - 1);
    *frame_x = (float)x;
    *frame_y = (float)y;
}
