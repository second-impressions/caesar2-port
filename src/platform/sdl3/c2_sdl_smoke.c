#include <SDL3/SDL.h>

#include <stdio.h>
#include <string.h>

#include "c2_host.h"
#include "c2_observation.h"
#include "c2_sdl_host.h"
#include "c2_sdl_smoke.h"

enum city_smoke_phase {
    CITY_SMOKE_WAIT_FOR_CITY,
    CITY_SMOKE_SETTLE,
    CITY_SMOKE_PAUSE,
    CITY_SMOKE_UNPAUSE,
    CITY_SMOKE_PAN,
    CITY_SMOKE_ZOOM,
    CITY_SMOKE_OPEN_FORUM,
    CITY_SMOKE_CLOSE_FORUM,
    CITY_SMOKE_DONE
};

static int observation_is(const struct c2_observation *observation,
                          enum c2_observation_point point)
{
    return observation->point == point;
}

static void release_mouse(struct c2_sdl_smoke *smoke, Uint64 now)
{
    if (smoke->mouse_down && now >= smoke->release_mouse_at) {
        c2_sdl_host_set_headless_mouse(smoke->mouse_x, smoke->mouse_y, 0);
        smoke->mouse_down = 0;
    }
}

static int click_mouse(struct c2_sdl_smoke *smoke, Uint64 now,
                       int x, int y, unsigned int button)
{
    if (smoke->mouse_down || now - smoke->last_input < 120) return 0;
    c2_sdl_host_set_headless_mouse(x, y, button);
    smoke->mouse_x = x;
    smoke->mouse_y = y;
    smoke->mouse_down = 1;
    smoke->release_mouse_at = now + 40;
    smoke->last_input = now;
    return 1;
}

static int press_key(struct c2_sdl_smoke *smoke, Uint64 now,
                     enum c2_host_key key)
{
    if (now - smoke->last_input < 120) return 0;
    c2_sdl_host_push_headless_key(key);
    smoke->last_input = now;
    return 1;
}

static void drive_startup(struct c2_sdl_smoke *smoke, Uint64 now,
                          const struct c2_observation *observation)
{
    if (observation_is(observation, C2_OBSERVATION_STARTUP)) {
        click_mouse(smoke, now, 10, 10, C2_HOST_MOUSE_LEFT);
    } else if (observation_is(observation,
                              C2_OBSERVATION_SKILL_SELECTION)) {
        click_mouse(smoke, now, 410, 195, C2_HOST_MOUSE_LEFT);
    } else if (observation_is(observation, C2_OBSERVATION_SKILL_DETAILS)) {
        if (observation->peace_mode) {
            click_mouse(smoke, now, 280, 250, C2_HOST_MOUSE_LEFT);
        } else {
            click_mouse(smoke, now, 280, 345, C2_HOST_MOUSE_LEFT);
        }
    } else if (observation_is(observation,
                              C2_OBSERVATION_PROVINCE_INTRO)) {
        click_mouse(smoke, now, 10, 10, C2_HOST_MOUSE_RIGHT);
    }
}

static void drive_province_selection(
    struct c2_sdl_smoke *smoke, Uint64 now,
    const struct c2_observation *observation)
{
    int x;
    int y;

    if (!observation_is(observation,
                        C2_OBSERVATION_PROVINCE_SELECTION)) return;
    if (observation->detail == 13) {
        click_mouse(smoke, now,
                    286 + smoke->scan_offset % 40,
                    223 + smoke->scan_offset / 40,
                    C2_HOST_MOUSE_LEFT);
        return;
    }
    if (smoke->mouse_down || now - smoke->last_input < 12) return;
    smoke->scan_offset = (smoke->scan_offset + 1) % (40 * 40);
    x = 286 + smoke->scan_offset % 40;
    y = 223 + smoke->scan_offset / 40;
    c2_sdl_host_set_headless_mouse(x, y, 0);
    smoke->mouse_x = x;
    smoke->mouse_y = y;
    smoke->last_input = now;
}

static enum c2_sdl_smoke_result drive_city(
    struct c2_sdl_smoke *smoke, Uint64 now,
    const struct c2_observation *observation)
{
    if (observation_is(observation, C2_OBSERVATION_MESSAGE)) {
        smoke->city_quiet_since = now;
        click_mouse(smoke, now, 10, 10, C2_HOST_MOUSE_RIGHT);
        return C2_SDL_SMOKE_RUNNING;
    }

    switch (smoke->phase) {
    case CITY_SMOKE_WAIT_FOR_CITY:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP)) {
            if ((observation->reached &
                 (UINT64_C(1) << C2_OBSERVATION_PROVINCE_INITIALIZED)) == 0) {
                fprintf(stderr,
                        "city loop reached without province initialization "
                        "observation\n");
                return C2_SDL_SMOKE_FAILURE;
            }
            smoke->initial_map_x = observation->map_x;
            smoke->initial_zoom = observation->zoom_level;
            smoke->city_quiet_since = now;
            smoke->phase = CITY_SMOKE_SETTLE;
        }
        break;
    case CITY_SMOKE_SETTLE:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            now - smoke->city_quiet_since >= 300) {
            if (press_key(smoke, now, C2_HOST_KEY_P)) {
                smoke->phase = CITY_SMOKE_PAUSE;
            }
        }
        break;
    case CITY_SMOKE_PAUSE:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            observation->paused) {
            if (press_key(smoke, now, C2_HOST_KEY_P)) {
                smoke->phase = CITY_SMOKE_UNPAUSE;
            }
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            press_key(smoke, now, C2_HOST_KEY_P);
        }
        break;
    case CITY_SMOKE_UNPAUSE:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            !observation->paused) {
            smoke->initial_map_x = observation->map_x;
            c2_sdl_host_set_headless_mouse(0, 240, 0);
            smoke->mouse_x = 0;
            smoke->mouse_y = 240;
            smoke->last_input = now;
            smoke->phase = CITY_SMOKE_PAN;
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            press_key(smoke, now, C2_HOST_KEY_P);
        }
        break;
    case CITY_SMOKE_PAN:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            observation->map_x != smoke->initial_map_x) {
            c2_sdl_host_set_headless_mouse(320, 240, 0);
            smoke->mouse_x = 320;
            smoke->mouse_y = 240;
            smoke->initial_zoom = observation->zoom_level;
            if (press_key(smoke, now, C2_HOST_KEY_MINUS)) {
                smoke->phase = CITY_SMOKE_ZOOM;
            }
        }
        break;
    case CITY_SMOKE_ZOOM:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            observation->zoom_level != smoke->initial_zoom) {
            if (press_key(smoke, now, C2_HOST_KEY_F)) {
                smoke->phase = CITY_SMOKE_OPEN_FORUM;
            }
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            press_key(smoke, now, C2_HOST_KEY_MINUS);
        }
        break;
    case CITY_SMOKE_OPEN_FORUM:
        if (observation_is(observation, C2_OBSERVATION_FORUM)) {
            if (click_mouse(smoke, now, 10, 10,
                            C2_HOST_MOUSE_RIGHT)) {
                smoke->phase = CITY_SMOKE_CLOSE_FORUM;
            }
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            press_key(smoke, now, C2_HOST_KEY_F);
        }
        break;
    case CITY_SMOKE_CLOSE_FORUM:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP)) {
            smoke->phase = CITY_SMOKE_DONE;
        } else if (observation_is(observation, C2_OBSERVATION_FORUM)) {
            click_mouse(smoke, now, 10, 10, C2_HOST_MOUSE_RIGHT);
        }
        break;
    case CITY_SMOKE_DONE:
        printf("recovered city-loop smoke completed\n");
        return C2_SDL_SMOKE_SUCCESS;
    }
    return C2_SDL_SMOKE_RUNNING;
}

void c2_sdl_smoke_init(struct c2_sdl_smoke *smoke,
                       enum c2_sdl_smoke_kind kind, Uint64 now)
{
    memset(smoke, 0, sizeof(*smoke));
    smoke->kind = kind;
    smoke->started = now;
    smoke->phase = CITY_SMOKE_WAIT_FOR_CITY;
}

enum c2_sdl_smoke_result c2_sdl_smoke_iterate(
    struct c2_sdl_smoke *smoke, Uint64 now)
{
    struct c2_observation observation;

    release_mouse(smoke, now);
    c2_host_observation_snapshot(&observation);
    if (now - smoke->started >= 45000) {
        fprintf(stderr,
                "smoke test timed out at observation %d detail %d phase %d "
                "paused %d zoom %d map (%d,%d)\n",
                observation.point, observation.detail, smoke->phase,
                observation.paused, observation.zoom_level,
                observation.map_x, observation.map_y);
        return C2_SDL_SMOKE_FAILURE;
    }

    drive_startup(smoke, now, &observation);
    if (observation_is(&observation,
                       C2_OBSERVATION_PROVINCE_SELECTION)) {
        if (smoke->kind == C2_SDL_SMOKE_PROVINCE_SELECTION) {
            printf("recovered province-selection smoke completed\n");
            return C2_SDL_SMOKE_SUCCESS;
        }
        drive_province_selection(smoke, now, &observation);
    } else if (observation_is(&observation,
                              C2_OBSERVATION_PROVINCE_CONFIRMATION)) {
        click_mouse(smoke, now, 410, 330, C2_HOST_MOUSE_LEFT);
    }

    if (smoke->kind == C2_SDL_SMOKE_CITY_LOOP) {
        return drive_city(smoke, now, &observation);
    }
    return C2_SDL_SMOKE_RUNNING;
}
