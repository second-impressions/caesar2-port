#include <inttypes.h>
#include <stdio.h>
#include <setjmp.h>

#include "c2_host.h"
#if C2_FEAT_DEBUG_OBSERVATION
#include "c2_observation.h"
#endif
#include "c2_port.h"
#include "c2_port_app.h"

extern void c2_engine_main(int argc, char *argv[]);
extern void stop_system(void);

static jmp_buf c2_exit_target;
static int c2_engine_running;
static int c2_exit_status;

void c2_port_exit(int status)
{
    c2_exit_status = status != 0 ? status : 1;
    c2_host_request_shutdown();
    if (c2_engine_running) {
        longjmp(c2_exit_target, 1);
    }
}

void exit_game(void)
{
    c2_host_request_shutdown();
    if (c2_engine_running) {
        c2_exit_status = 0;
        longjmp(c2_exit_target, 1);
    }
}

enum c2_port_app_result c2_port_app_run(
    const struct c2_port_app_config *config)
{
    int result;

    if (!c2_port_compat_init()) {
        return C2_PORT_APP_FAILURE;
    }

    c2_exit_status = 0;
    c2_engine_running = 1;
#if C2_FEAT_DEBUG_OBSERVATION
    c2_observe(C2_OBSERVATION_ENGINE_STARTED, 0);
#endif
    if (setjmp(c2_exit_target) == 0) {
        c2_engine_main(0, NULL);
        result = 0;
    } else {
        result = c2_exit_status;
    }
    c2_engine_running = 0;
#if C2_FEAT_DEBUG_OBSERVATION
    c2_observe(C2_OBSERVATION_ENGINE_STOPPED, result);
#endif
    if (config->headless) {
        printf("final framebuffer fnv1a64=%016" PRIx64 "\n",
               c2_port_frame_hash());
    }
    if (config->screenshot_filename != NULL &&
        !c2_port_save_screenshot(config->screenshot_filename)) {
        fprintf(stderr, "could not write screenshot to %s\n",
                config->screenshot_filename);
        result = 1;
    }
    stop_system();
    c2_port_compat_shutdown();
    return result == 0 ? C2_PORT_APP_SUCCESS : C2_PORT_APP_FAILURE;
}
