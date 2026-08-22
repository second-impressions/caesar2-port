#ifndef PORT_MOUSE_H
#define PORT_MOUSE_H

struct c2_port_mouse {
    int frame_width;
    int frame_height;
    int min_x;
    int min_y;
    int max_x;
    int max_y;
    int x;
    int y;
    double precise_x;
    double precise_y;
    int inside;
    int edge_margin;
};

int c2_port_mouse_init(struct c2_port_mouse *mouse,
                       int frame_width, int frame_height,
                       int edge_margin);
int c2_port_mouse_set_bounds(struct c2_port_mouse *mouse,
                             int min_x, int min_y, int max_x, int max_y);
void c2_port_mouse_set_position(struct c2_port_mouse *mouse, int x, int y);
void c2_port_mouse_set_absolute(struct c2_port_mouse *mouse,
                                float frame_x, float frame_y);
void c2_port_mouse_add_relative(struct c2_port_mouse *mouse,
                                float frame_dx, float frame_dy);
void c2_port_mouse_leave(struct c2_port_mouse *mouse);
void c2_port_mouse_get_frame_position(const struct c2_port_mouse *mouse,
                                      float *frame_x, float *frame_y);

#endif /* PORT_MOUSE_H */
