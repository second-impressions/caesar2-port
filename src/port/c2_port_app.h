#ifndef C2_PORT_APP_H
#define C2_PORT_APP_H

#include "c2_host.h"

enum c2_port_app_result {
    C2_PORT_APP_CONTINUE,
    C2_PORT_APP_SUCCESS,
    C2_PORT_APP_FAILURE
};

struct c2_port_app_config {
    const char *screenshot_filename;
    int headless;
};

enum c2_port_app_result c2_port_app_start(
    const struct c2_port_app_config *config);
enum c2_port_app_result c2_port_app_handle_event(
    const struct c2_host_event *event);
enum c2_port_app_result c2_port_app_update(void);
void c2_port_app_stop(void);

#endif /* C2_PORT_APP_H */
