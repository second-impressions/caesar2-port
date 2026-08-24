#ifndef PORT_PAUSE_H
#define PORT_PAUSE_H

/*
 * Applies a pending host pause request through the recovered pause action.
 * Called from the engine's own city loop so the change lands at a point the
 * recovered code already treats as safe.
 */
void c2_port_apply_pause_request(void);
int c2_port_host_pause_active(void);

#endif
