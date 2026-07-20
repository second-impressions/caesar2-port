#include <inttypes.h>
#include <stdio.h>

#include "c2_data.h"
#include "c2_port.h"
#include "c2_port_app.h"
#include "c2_types.h"

#define C2_SPLASH_DURATION_MS 2000

enum c2_startup_stage {
    C2_STARTUP_SIERRA,
    C2_STARTUP_IMPRESSIONS,
    C2_STARTUP_MENU,
    C2_STARTUP_SETTINGS,
    C2_STARTUP_PROVINCE
};

struct c2_app_state {
    enum c2_startup_stage stage;
    uint64_t stage_started;
    const char *screenshot_filename;
    int initialized;
};

extern struct button_rec skill1_buttons[];
extern struct button_rec skill2_buttons[];
extern int display_pl8file(char *pl8_filename, char *palette_filename);
extern void refresh_svga_screen(void);
extern void show_buttons(int x, int y, struct button_rec *button_list,
                         int button_count);
extern void show_skill1_box(void);
extern void show_skill2_box(void);
extern void clear_empire(void);
extern void get_new_province_options(void);
extern void show_initreg_box(void);
extern void initreg_game_loop(void);
extern int out2;

static struct c2_app_state c2_app;

static int show_startup_stage(enum c2_startup_stage stage)
{
    int loaded;

    loaded = 0;
    if (stage == C2_STARTUP_SIERRA) {
        loaded = display_pl8file("logo1.pl8", "logo1.256");
    } else if (stage == C2_STARTUP_IMPRESSIONS) {
        loaded = display_pl8file("logo2.pl8", "logo2.256");
    } else if (stage == C2_STARTUP_MENU) {
        show_skill1_box();
        show_buttons(0x50, 0x50, skill1_buttons, 4);
        refresh_svga_screen();
        loaded = 1;
    } else if (stage == C2_STARTUP_SETTINGS) {
        show_skill2_box();
        show_buttons(0x50, 0x50, skill2_buttons, 6);
        refresh_svga_screen();
        loaded = 1;
    } else if (stage == C2_STARTUP_PROVINCE) {
        clear_empire();
        get_new_province_options();
        out2 = 0;
        show_initreg_box();
        loaded = 1;
    }

    if (loaded) {
        c2_app.stage = stage;
        c2_app.stage_started = c2_host_ticks_ms();
        if (c2_app.screenshot_filename != NULL &&
            !c2_port_save_screenshot(c2_app.screenshot_filename)) {
            fprintf(stderr, "could not write screenshot to %s\n",
                    c2_app.screenshot_filename);
            return 0;
        }
    }
    return loaded;
}

static enum c2_port_app_result advance_startup(void)
{
    enum c2_startup_stage next_stage;

    if (c2_app.stage >= C2_STARTUP_MENU) {
        return C2_PORT_APP_CONTINUE;
    }
    next_stage = (enum c2_startup_stage)(c2_app.stage + 1);
    if (!show_startup_stage(next_stage)) {
        return C2_PORT_APP_FAILURE;
    }
    return C2_PORT_APP_CONTINUE;
}

static enum c2_port_app_result redraw_settings(void)
{
    return show_startup_stage(C2_STARTUP_SETTINGS)
        ? C2_PORT_APP_CONTINUE : C2_PORT_APP_FAILURE;
}

enum c2_port_app_result c2_port_app_start(
    const struct c2_port_app_config *config)
{
    if (!c2_port_compat_init()) {
        return C2_PORT_APP_FAILURE;
    }
    c2_app.initialized = 1;
    if (!c2_port_load_startup_ui()) {
        fprintf(stderr, "could not load the Caesar II interface assets\n");
        return C2_PORT_APP_FAILURE;
    }

    c2_app.screenshot_filename = config->screenshot_filename;
    if (!show_startup_stage(C2_STARTUP_SIERRA)) {
        fprintf(stderr, "could not load the Caesar II startup assets\n");
        return C2_PORT_APP_FAILURE;
    }
    printf("optional host capabilities: music=%s video=%s\n",
           c2_host_has_capability(C2_HOST_CAPABILITY_MUSIC) ? "enabled" : "disabled",
           c2_host_has_capability(C2_HOST_CAPABILITY_VIDEO) ? "enabled" : "disabled");
    printf("sierra framebuffer fnv1a64=%016" PRIx64 "\n",
           c2_port_frame_hash());

    if (config->headless) {
        if (advance_startup() == C2_PORT_APP_FAILURE) {
            return C2_PORT_APP_FAILURE;
        }
        printf("impressions framebuffer fnv1a64=%016" PRIx64 "\n",
               c2_port_frame_hash());
        if (advance_startup() == C2_PORT_APP_FAILURE) {
            return C2_PORT_APP_FAILURE;
        }
        printf("startup menu framebuffer fnv1a64=%016" PRIx64 "\n",
               c2_port_frame_hash());
        if (!show_startup_stage(C2_STARTUP_SETTINGS)) {
            return C2_PORT_APP_FAILURE;
        }
        printf("game settings framebuffer fnv1a64=%016" PRIx64 "\n",
               c2_port_frame_hash());
        if (!show_startup_stage(C2_STARTUP_PROVINCE)) {
            return C2_PORT_APP_FAILURE;
        }
        initreg_game_loop();
        printf("province selection framebuffer fnv1a64=%016" PRIx64 "\n",
               c2_port_frame_hash());
        return C2_PORT_APP_SUCCESS;
    }

    return C2_PORT_APP_CONTINUE;
}

enum c2_port_app_result c2_port_app_handle_event(
    const struct c2_host_event *event)
{
    if (event->type == C2_HOST_EVENT_QUIT) {
        return C2_PORT_APP_SUCCESS;
    }
    if (event->type == C2_HOST_EVENT_KEY_DOWN &&
        event->key == C2_HOST_KEY_ESCAPE) {
        if (c2_app.stage == C2_STARTUP_SETTINGS) {
            return show_startup_stage(C2_STARTUP_MENU)
                ? C2_PORT_APP_CONTINUE : C2_PORT_APP_FAILURE;
        }
        return C2_PORT_APP_SUCCESS;
    }
    if (c2_app.stage < C2_STARTUP_MENU &&
        (event->type == C2_HOST_EVENT_KEY_DOWN ||
         event->type == C2_HOST_EVENT_MOUSE_BUTTON_DOWN)) {
        return advance_startup();
    }
    if (c2_app.stage == C2_STARTUP_MENU &&
        event->type == C2_HOST_EVENT_KEY_DOWN &&
        (event->key == C2_HOST_KEY_RETURN ||
         event->key == C2_HOST_KEY_SPACE)) {
        return show_startup_stage(C2_STARTUP_SETTINGS)
            ? C2_PORT_APP_CONTINUE : C2_PORT_APP_FAILURE;
    }
    if (c2_app.stage == C2_STARTUP_MENU &&
        event->type == C2_HOST_EVENT_MOUSE_BUTTON_DOWN) {
        if (event->mouse_x >= 130 && event->mouse_x < 440) {
            if (event->mouse_y >= 170 && event->mouse_y < 218) {
                return show_startup_stage(C2_STARTUP_SETTINGS)
                    ? C2_PORT_APP_CONTINUE : C2_PORT_APP_FAILURE;
            }
            if (event->mouse_y >= 314 && event->mouse_y < 362) {
                return C2_PORT_APP_SUCCESS;
            }
        }
    }
    if (c2_app.stage == C2_STARTUP_SETTINGS &&
        event->type == C2_HOST_EVENT_KEY_DOWN) {
        if (event->key == C2_HOST_KEY_RETURN ||
            event->key == C2_HOST_KEY_SPACE) {
            return show_startup_stage(C2_STARTUP_PROVINCE)
                ? C2_PORT_APP_CONTINUE : C2_PORT_APP_FAILURE;
        }
        if (event->key == C2_HOST_KEY_LEFT && c2inf.skill_level > 0) {
            c2inf.skill_level--;
            return redraw_settings();
        }
        if (event->key == C2_HOST_KEY_RIGHT && c2inf.skill_level < 4) {
            c2inf.skill_level++;
            return redraw_settings();
        }
        if (event->key == C2_HOST_KEY_P) {
            c2inf.peace_mode ^= 1;
            return redraw_settings();
        }
    }
    if (c2_app.stage == C2_STARTUP_SETTINGS &&
        event->type == C2_HOST_EVENT_MOUSE_BUTTON_DOWN) {
        if (event->mouse_y >= 145 && event->mouse_y < 195) {
            if (event->mouse_x >= 260 && event->mouse_x < 300 &&
                c2inf.skill_level > 0) {
                c2inf.skill_level--;
                return redraw_settings();
            }
            if (event->mouse_x >= 300 && event->mouse_x < 340 &&
                c2inf.skill_level < 4) {
                c2inf.skill_level++;
                return redraw_settings();
            }
        }
        if (event->mouse_x >= 130 && event->mouse_x < 440 &&
            event->mouse_y >= 220 && event->mouse_y < 275) {
            c2inf.peace_mode ^= 1;
            return redraw_settings();
        }
        if (event->mouse_x >= 130 && event->mouse_x < 440 &&
            event->mouse_y >= 320 && event->mouse_y < 370) {
            return show_startup_stage(C2_STARTUP_PROVINCE)
                ? C2_PORT_APP_CONTINUE : C2_PORT_APP_FAILURE;
        }
        if (event->mouse_x >= 130 && event->mouse_x < 440 &&
            event->mouse_y >= 370 && event->mouse_y < 425) {
            return show_startup_stage(C2_STARTUP_MENU)
                ? C2_PORT_APP_CONTINUE : C2_PORT_APP_FAILURE;
        }
    }

    return C2_PORT_APP_CONTINUE;
}

enum c2_port_app_result c2_port_app_update(void)
{
    if (c2_app.stage < C2_STARTUP_MENU &&
        c2_host_ticks_ms() - c2_app.stage_started >= C2_SPLASH_DURATION_MS) {
        return advance_startup();
    }
    if (c2_app.stage == C2_STARTUP_PROVINCE) {
        initreg_game_loop();
    }
    return C2_PORT_APP_CONTINUE;
}

void c2_port_app_stop(void)
{
    if (c2_app.initialized) {
        c2_port_compat_shutdown();
    }
    c2_app.initialized = 0;
}
