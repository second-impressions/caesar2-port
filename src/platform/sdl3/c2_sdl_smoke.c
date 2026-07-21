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

enum name_smoke_phase {
    NAME_SMOKE_NOT_STARTED,
    NAME_SMOKE_WAIT_FOR_ENTRY,
    NAME_SMOKE_CLEAR,
    NAME_SMOKE_TYPE,
    NAME_SMOKE_SUBMIT,
    NAME_SMOKE_WAIT_FOR_ACCEPT,
    NAME_SMOKE_ACCEPTED
};

enum file_smoke_phase {
    FILE_SMOKE_CLEAR,
    FILE_SMOKE_TYPE,
    FILE_SMOKE_SUBMIT,
    FILE_SMOKE_WAIT
};

enum save_load_smoke_phase {
    SAVE_LOAD_WAIT_FOR_CITY,
    SAVE_LOAD_SETTLE,
    SAVE_LOAD_OPEN_SAVE,
    SAVE_LOAD_WAIT_FOR_SAVE,
    SAVE_LOAD_MUTATE,
    SAVE_LOAD_WAIT_FOR_MUTATION,
    SAVE_LOAD_OPEN_LOAD,
    SAVE_LOAD_WAIT_FOR_LOAD,
    SAVE_LOAD_WAIT_FOR_LOADED_CITY
};

enum {
    CITY_FORUM_ICON_X = 560,
    CITY_FORUM_ICON_Y = 251,
    NAME_BUTTON_X = 280,
    NAME_BUTTON_Y = 297,
    TUTORIAL_FORWARD_X = 112,
    TUTORIAL_FORWARD_Y = 432,
    PROVINCE_SCAN_WIDTH = 40,
    PROVINCE_SCAN_HEIGHT = 40,
    PROVINCE_SCAN_STEP = 2,
    SMOKE_TIMEOUT_MS = 45000,
    SAVE_LOAD_SMOKE_TIMEOUT_MS = 90000
};

static const char smoke_player_name[] = "Portia";
static const char smoke_save_base[] = "c2smoke";
static const char smoke_save_name[] = "c2smoke.sav";

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

static int type_character(struct c2_sdl_smoke *smoke, Uint64 now,
                          uint32_t codepoint)
{
    if (now - smoke->last_input < 120) return 0;
    c2_sdl_host_push_headless_text(codepoint);
    smoke->last_input = now;
    return 1;
}

static void drive_name_entry(struct c2_sdl_smoke *smoke, Uint64 now,
                             const struct c2_observation *observation)
{
    size_t length;

    if (!observation_is(observation, C2_OBSERVATION_NAME_ENTRY)) return;
    if (smoke->name_phase == NAME_SMOKE_WAIT_FOR_ENTRY) {
        length = strlen(observation->player_name);
        if (length != 0 && observation->player_name[length - 1] == ' ') {
            fprintf(stderr, "name editor received trailing fixed-width padding\n");
            smoke->name_failed = 1;
            return;
        }
        smoke->name_phase = NAME_SMOKE_CLEAR;
    }
    if (smoke->name_phase == NAME_SMOKE_CLEAR) {
        if (observation->player_name[0] != '\0') {
            press_key(smoke, now, C2_HOST_KEY_DELETE);
            return;
        }
        smoke->name_phase = NAME_SMOKE_TYPE;
    }
    if (smoke->name_phase == NAME_SMOKE_TYPE) {
        length = strlen(observation->player_name);
        if (length > strlen(smoke_player_name) ||
            memcmp(observation->player_name, smoke_player_name, length) != 0) {
            fprintf(stderr, "name editor produced unexpected text '%s'\n",
                    observation->player_name);
            smoke->name_failed = 1;
            return;
        }
        if (smoke_player_name[length] != '\0') {
            type_character(smoke, now,
                           (unsigned char)smoke_player_name[length]);
            return;
        }
        smoke->name_phase = NAME_SMOKE_SUBMIT;
    }
    if (smoke->name_phase == NAME_SMOKE_SUBMIT &&
        press_key(smoke, now, C2_HOST_KEY_RETURN)) {
        smoke->name_phase = NAME_SMOKE_WAIT_FOR_ACCEPT;
    }
}

static void drive_file_entry(struct c2_sdl_smoke *smoke, Uint64 now,
                             const struct c2_observation *observation)
{
    size_t length;
    size_t prefix_length;

    if (!observation_is(observation, C2_OBSERVATION_FILE_DIALOG)) return;
    if (smoke->file_phase == FILE_SMOKE_CLEAR) {
        if (strcmp(observation->filename, smoke_save_name) == 0) {
            smoke->file_phase = FILE_SMOKE_SUBMIT;
        } else {
            length = strlen(observation->filename);
            if (length < 4 ||
                SDL_strcasecmp(observation->filename + length - 4,
                               ".sav") != 0) {
                fprintf(stderr, "file editor cannot preserve suffix in '%s'\n",
                        observation->filename);
                smoke->name_failed = 1;
                return;
            }
        }
        if (smoke->file_phase == FILE_SMOKE_CLEAR && length > 4) {
            press_key(smoke, now, C2_HOST_KEY_DELETE);
            return;
        }
        if (smoke->file_phase == FILE_SMOKE_CLEAR &&
            press_key(smoke, now, C2_HOST_KEY_INSERT)) {
            smoke->file_phase = FILE_SMOKE_TYPE;
            return;
        }
    }
    if (smoke->file_phase == FILE_SMOKE_TYPE) {
        length = strlen(observation->filename);
        if (length < 4 ||
            SDL_strcasecmp(observation->filename + length - 4, ".sav") != 0) {
            fprintf(stderr, "file editor produced unexpected text '%s'\n",
                    observation->filename);
            smoke->name_failed = 1;
            return;
        }
        prefix_length = length - 4;
        if (prefix_length > strlen(smoke_save_base) ||
            memcmp(observation->filename, smoke_save_base,
                   prefix_length) != 0) {
            fprintf(stderr, "file editor produced unexpected text '%s'\n",
                    observation->filename);
            smoke->name_failed = 1;
            return;
        }
        if (smoke_save_base[prefix_length] != '\0') {
            type_character(smoke, now,
                           (unsigned char)smoke_save_base[prefix_length]);
            return;
        }
        smoke->file_phase = FILE_SMOKE_SUBMIT;
    }
    if (smoke->file_phase == FILE_SMOKE_SUBMIT &&
        press_key(smoke, now, C2_HOST_KEY_RETURN)) {
        smoke->file_phase = FILE_SMOKE_WAIT;
    }
    if (smoke->file_phase == FILE_SMOKE_WAIT &&
        now - smoke->last_input >= 250) {
        press_key(smoke, now, C2_HOST_KEY_RETURN);
    }
}

static enum c2_sdl_smoke_result drive_tutorial(
    struct c2_sdl_smoke *smoke, Uint64 now,
    const struct c2_observation *observation)
{
    if (observation_is(observation, C2_OBSERVATION_STARTUP)) {
        click_mouse(smoke, now, 10, 10, C2_HOST_MOUSE_LEFT);
        return C2_SDL_SMOKE_RUNNING;
    }
    if (observation_is(observation, C2_OBSERVATION_SKILL_SELECTION)) {
        if (smoke->tutorial_confirmation_seen) {
            if (smoke->tutorial_pages_seen == 0) {
                fprintf(stderr, "tutorial returned without displaying a page\n");
                return C2_SDL_SMOKE_FAILURE;
            }
            printf("recovered tutorial flow smoke completed across %d pages\n",
                   smoke->tutorial_pages_seen);
            return C2_SDL_SMOKE_SUCCESS;
        }
        if (click_mouse(smoke, now, 410, 290, C2_HOST_MOUSE_LEFT)) {
            smoke->tutorial_started = 1;
        }
        return C2_SDL_SMOKE_RUNNING;
    }
    if (observation_is(observation, C2_OBSERVATION_TUTORIAL_PAGE)) {
        if (observation->detail != smoke->last_tutorial_page) {
            if (observation->detail < smoke->last_tutorial_page) {
                fprintf(stderr, "tutorial page order moved backward from %d to %d\n",
                        smoke->last_tutorial_page, observation->detail);
                return C2_SDL_SMOKE_FAILURE;
            }
            smoke->last_tutorial_page = observation->detail;
            smoke->tutorial_pages_seen++;
        }
        click_mouse(smoke, now, TUTORIAL_FORWARD_X, TUTORIAL_FORWARD_Y,
                    C2_HOST_MOUSE_LEFT);
        return C2_SDL_SMOKE_RUNNING;
    }
    if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
        observation->tutorial_mode) {
        press_key(smoke, now, C2_HOST_KEY_ESCAPE);
        return C2_SDL_SMOKE_RUNNING;
    }
    if (observation_is(observation, C2_OBSERVATION_CONFIRMATION) &&
        observation->detail == 0x0e) {
        smoke->tutorial_confirmation_seen = 1;
        type_character(smoke, now, 'n');
    }
    return C2_SDL_SMOKE_RUNNING;
}

static int saved_view_matches(const struct c2_sdl_smoke *smoke,
                              const struct c2_observation *observation)
{
    return observation->province == smoke->saved_province &&
           observation->map_x == smoke->saved_map_x &&
           observation->map_y == smoke->saved_map_y &&
           observation->zoom_level == smoke->saved_zoom;
}

static enum c2_sdl_smoke_result drive_save_load(
    struct c2_sdl_smoke *smoke, Uint64 now,
    const struct c2_observation *observation)
{
    if (observation_is(observation, C2_OBSERVATION_MESSAGE)) {
        smoke->city_quiet_since = now;
        click_mouse(smoke, now, 10, 10, C2_HOST_MOUSE_RIGHT);
        return C2_SDL_SMOKE_RUNNING;
    }
    if (observation_is(observation, C2_OBSERVATION_CONFIRMATION) &&
        observation->detail == 2) {
        type_character(smoke, now, 'y');
        return C2_SDL_SMOKE_RUNNING;
    }

    switch (smoke->phase) {
    case SAVE_LOAD_WAIT_FOR_CITY:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP)) {
            smoke->city_quiet_since = now;
            smoke->phase = SAVE_LOAD_SETTLE;
        }
        break;
    case SAVE_LOAD_SETTLE:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            now - smoke->city_quiet_since >= 300 &&
            press_key(smoke, now, C2_HOST_KEY_F5)) {
            smoke->phase = SAVE_LOAD_OPEN_SAVE;
        }
        break;
    case SAVE_LOAD_OPEN_SAVE:
        if (observation_is(observation, C2_OBSERVATION_FILE_DIALOG) &&
            observation->detail == 0x29) {
            drive_file_entry(smoke, now, observation);
            smoke->phase = SAVE_LOAD_WAIT_FOR_SAVE;
        }
        break;
    case SAVE_LOAD_WAIT_FOR_SAVE:
        if (observation_is(observation, C2_OBSERVATION_FILE_DIALOG) &&
            observation->detail == 0x29) {
            drive_file_entry(smoke, now, observation);
        } else if (observation_is(observation,
                                  C2_OBSERVATION_SAVE_COMPLETE)) {
            if (SDL_strcasecmp(observation->filename, smoke_save_name) != 0 ||
                !c2_host_user_file_exists(smoke_save_name)) {
                fprintf(stderr,
                        "save smoke observed '%s' instead of '%s' (exists %d)\n",
                        observation->filename, smoke_save_name,
                        c2_host_user_file_exists(smoke_save_name));
                return C2_SDL_SMOKE_FAILURE;
            }
            smoke->saved_province = observation->province;
            smoke->saved_map_x = observation->map_x;
            smoke->saved_map_y = observation->map_y;
            smoke->saved_zoom = observation->zoom_level;
            smoke->file_phase = FILE_SMOKE_CLEAR;
            smoke->phase = SAVE_LOAD_MUTATE;
        }
        break;
    case SAVE_LOAD_MUTATE:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            type_character(smoke, now, '-')) {
            smoke->phase = SAVE_LOAD_WAIT_FOR_MUTATION;
        }
        break;
    case SAVE_LOAD_WAIT_FOR_MUTATION:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            observation->zoom_level != smoke->saved_zoom) {
            if (press_key(smoke, now, C2_HOST_KEY_F4)) {
                smoke->phase = SAVE_LOAD_OPEN_LOAD;
            }
        } else if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            type_character(smoke, now, '-');
        }
        break;
    case SAVE_LOAD_OPEN_LOAD:
        if (observation_is(observation, C2_OBSERVATION_FILE_DIALOG) &&
            observation->detail == 0x28) {
            drive_file_entry(smoke, now, observation);
            smoke->phase = SAVE_LOAD_WAIT_FOR_LOAD;
        }
        break;
    case SAVE_LOAD_WAIT_FOR_LOAD:
        if (observation_is(observation, C2_OBSERVATION_FILE_DIALOG) &&
            observation->detail == 0x28) {
            drive_file_entry(smoke, now, observation);
        } else if (observation_is(observation,
                                  C2_OBSERVATION_LOAD_COMPLETE)) {
            if (!saved_view_matches(smoke, observation)) {
                fprintf(stderr,
                        "loaded view differs: province %d/%d zoom %d/%d "
                        "map (%d,%d)/(%d,%d)\n",
                        observation->province, smoke->saved_province,
                        observation->zoom_level, smoke->saved_zoom,
                        observation->map_x, observation->map_y,
                        smoke->saved_map_x, smoke->saved_map_y);
                return C2_SDL_SMOKE_FAILURE;
            }
            smoke->phase = SAVE_LOAD_WAIT_FOR_LOADED_CITY;
        }
        break;
    case SAVE_LOAD_WAIT_FOR_LOADED_CITY:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP)) {
            if (observation->province != smoke->saved_province ||
                observation->zoom_level != smoke->saved_zoom) {
                fprintf(stderr, "loaded game entered with the wrong view state\n");
                return C2_SDL_SMOKE_FAILURE;
            }
            printf("recovered save/load smoke restored '%s'\n",
                   smoke_save_name);
            return C2_SDL_SMOKE_SUCCESS;
        }
        break;
    }
    return C2_SDL_SMOKE_RUNNING;
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
        if (smoke->name_phase == NAME_SMOKE_NOT_STARTED) {
            if (click_mouse(smoke, now, NAME_BUTTON_X, NAME_BUTTON_Y,
                            C2_HOST_MOUSE_LEFT)) {
                smoke->name_phase = NAME_SMOKE_WAIT_FOR_ENTRY;
            }
        } else if (smoke->name_phase == NAME_SMOKE_WAIT_FOR_ACCEPT) {
            if (strcmp(observation->player_name, smoke_player_name) != 0) {
                fprintf(stderr, "accepted player name is '%s', expected '%s'\n",
                        observation->player_name, smoke_player_name);
                smoke->name_failed = 1;
            } else {
                smoke->name_phase = NAME_SMOKE_ACCEPTED;
            }
        } else if (smoke->name_phase == NAME_SMOKE_ACCEPTED &&
                   observation->peace_mode) {
            click_mouse(smoke, now, 280, 250, C2_HOST_MOUSE_LEFT);
        } else if (smoke->name_phase == NAME_SMOKE_ACCEPTED) {
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
    x = 286 + (smoke->scan_offset %
               (PROVINCE_SCAN_WIDTH / PROVINCE_SCAN_STEP)) *
        PROVINCE_SCAN_STEP;
    y = 223 + (smoke->scan_offset /
               (PROVINCE_SCAN_WIDTH / PROVINCE_SCAN_STEP)) *
        PROVINCE_SCAN_STEP;
    if (observation->detail == 13) {
        click_mouse(smoke, now, x, y, C2_HOST_MOUSE_LEFT);
        return;
    }
    if (smoke->mouse_down || now - smoke->last_input < 12) return;
    smoke->scan_offset = (smoke->scan_offset + 1) %
        ((PROVINCE_SCAN_WIDTH / PROVINCE_SCAN_STEP) *
         (PROVINCE_SCAN_HEIGHT / PROVINCE_SCAN_STEP));
    x = 286 + (smoke->scan_offset %
               (PROVINCE_SCAN_WIDTH / PROVINCE_SCAN_STEP)) *
        PROVINCE_SCAN_STEP;
    y = 223 + (smoke->scan_offset /
               (PROVINCE_SCAN_WIDTH / PROVINCE_SCAN_STEP)) *
        PROVINCE_SCAN_STEP;
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
            if (type_character(smoke, now, 'p')) {
                smoke->phase = CITY_SMOKE_PAUSE;
            }
        }
        break;
    case CITY_SMOKE_PAUSE:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            observation->paused) {
            if (type_character(smoke, now, 'p')) {
                smoke->phase = CITY_SMOKE_UNPAUSE;
            }
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            type_character(smoke, now, 'p');
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
            type_character(smoke, now, 'p');
        }
        break;
    case CITY_SMOKE_PAN:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            observation->map_x != smoke->initial_map_x) {
            c2_sdl_host_set_headless_mouse(320, 240, 0);
            smoke->mouse_x = 320;
            smoke->mouse_y = 240;
            smoke->initial_zoom = observation->zoom_level;
            if (type_character(smoke, now, '-')) {
                smoke->phase = CITY_SMOKE_ZOOM;
            }
        }
        break;
    case CITY_SMOKE_ZOOM:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            observation->zoom_level != smoke->initial_zoom) {
            if (click_mouse(smoke, now, CITY_FORUM_ICON_X,
                            CITY_FORUM_ICON_Y, C2_HOST_MOUSE_LEFT)) {
                smoke->phase = CITY_SMOKE_OPEN_FORUM;
            }
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            type_character(smoke, now, '-');
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
            click_mouse(smoke, now, CITY_FORUM_ICON_X,
                        CITY_FORUM_ICON_Y, C2_HOST_MOUSE_LEFT);
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
    smoke->last_tutorial_page = -1;
}

enum c2_sdl_smoke_result c2_sdl_smoke_iterate(
    struct c2_sdl_smoke *smoke, Uint64 now)
{
    struct c2_observation observation;

    release_mouse(smoke, now);
    c2_host_observation_snapshot(&observation);
    if (now - smoke->started >=
        (smoke->kind == C2_SDL_SMOKE_SAVE_LOAD
             ? SAVE_LOAD_SMOKE_TIMEOUT_MS : SMOKE_TIMEOUT_MS)) {
        fprintf(stderr,
                "smoke test timed out at observation %d detail %d phase %d "
                "paused %d zoom %d map (%d,%d) file '%s'\n",
                observation.point, observation.detail, smoke->phase,
                observation.paused, observation.zoom_level,
                observation.map_x, observation.map_y,
                observation.filename);
        return C2_SDL_SMOKE_FAILURE;
    }

    if (smoke->kind == C2_SDL_SMOKE_TUTORIAL) {
        return drive_tutorial(smoke, now, &observation);
    }
    drive_startup(smoke, now, &observation);
    drive_name_entry(smoke, now, &observation);
    if (smoke->name_failed) return C2_SDL_SMOKE_FAILURE;
    if (observation_is(&observation,
                       C2_OBSERVATION_PROVINCE_SELECTION)) {
        if (smoke->kind == C2_SDL_SMOKE_PROVINCE_SELECTION) {
            printf("recovered province-selection smoke completed\n");
            return C2_SDL_SMOKE_SUCCESS;
        }
        drive_province_selection(smoke, now, &observation);
    } else if (observation_is(&observation,
                              C2_OBSERVATION_PROVINCE_CONFIRMATION)) {
        if (!smoke->confirmation_clicked &&
            click_mouse(smoke, now, 410, 330, C2_HOST_MOUSE_LEFT)) {
            smoke->confirmation_clicked = 1;
        }
    }

    if (smoke->kind == C2_SDL_SMOKE_CITY_LOOP) {
        return drive_city(smoke, now, &observation);
    }
    if (smoke->kind == C2_SDL_SMOKE_SAVE_LOAD) {
        return drive_save_load(smoke, now, &observation);
    }
    return C2_SDL_SMOKE_RUNNING;
}
