#ifndef C2_PORT_APP_H
#define C2_PORT_APP_H

enum c2_port_app_result {
    C2_PORT_APP_CONTINUE,
    C2_PORT_APP_SUCCESS,
    C2_PORT_APP_FAILURE
};

struct c2_port_app_config {
    const char *screenshot_filename;
};

enum c2_port_app_result c2_port_app_run(
    const struct c2_port_app_config *config);

#endif /* C2_PORT_APP_H */
