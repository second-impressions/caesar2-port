#ifndef PORT_APP_H
#define PORT_APP_H

enum c2_port_app_result {
    PORT_APP_CONTINUE,
    PORT_APP_SUCCESS,
    PORT_APP_FAILURE
};

struct c2_port_app_config {
    const char *screenshot_filename;
};

enum c2_port_app_result c2_port_app_run(
    const struct c2_port_app_config *config);

#endif /* PORT_APP_H */
