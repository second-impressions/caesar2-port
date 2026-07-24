#include <SDL3/SDL.h>

#include <limits.h>
#include <stdio.h>
#include <string.h>

#include "c2_host.h"
#include "c2_observation.h"
#include "c2_sdl_host.h"
#include "c2_sdl_smoke.h"

enum city_smoke_phase {
    CITY_SMOKE_WAIT_FOR_CITY,
    CITY_SMOKE_SETTLE,
    CITY_SMOKE_OPEN_FILE_MENU,
    CITY_SMOKE_CLOSE_FILE_MENU,
    CITY_SMOKE_OPEN_OPTIONS_MENU,
    CITY_SMOKE_CLOSE_OPTIONS_MENU,
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

enum campania_smoke_phase {
    CAMPANIA_SMOKE_WAIT_FOR_CITY,
    CAMPANIA_SMOKE_SETTLE,
    CAMPANIA_SMOKE_WAIT_FOR_QUERY,
    CAMPANIA_SMOKE_WAIT_FOR_QUERY_CLOSE
};

enum {
    CITY_FORUM_ICON_X = 560,
    CITY_FORUM_ICON_Y = 251,
    NAME_BUTTON_X = 280,
    NAME_BUTTON_Y = 297,
    TUTORIAL_FORWARD_X = 112,
    TUTORIAL_FORWARD_Y = 432,
    CAMPANIA_REGION = 2,
    CAMPANIA_X = 301,
    CAMPANIA_Y = 280,
    MUSIC_VOICE_FIRST = 8,
    MUSIC_VOICE_COUNT = 2,
    MUSIC_SAMPLE_DURATION_MS = 8000,
    MUSIC_SAMPLE_LOG_INTERVAL_MS = 250,
    MUSIC_MIN_SAFE_QUEUE_MS = 40,
    CAMPANIA_CONFIRM_DELAY_MS = 3000,
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
        click_mouse(smoke, now, 0, 479, C2_HOST_MOUSE_RIGHT);
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
    if (!observation_is(observation,
                        C2_OBSERVATION_PROVINCE_SELECTION)) return;
    if (observation->detail == CAMPANIA_REGION) {
        click_mouse(smoke, now, CAMPANIA_X, CAMPANIA_Y,
                    C2_HOST_MOUSE_LEFT);
        return;
    }
    if (smoke->mouse_down || now - smoke->last_input < 12) return;
    c2_sdl_host_set_headless_mouse(CAMPANIA_X, CAMPANIA_Y, 0);
    smoke->mouse_x = CAMPANIA_X;
    smoke->mouse_y = CAMPANIA_Y;
    smoke->last_input = now;
}

static int city_menu_bar_is_valid(
    const struct c2_observation *observation)
{
    int i;

    if ((observation->reached &
         (UINT64_C(1) << C2_OBSERVATION_MENU_BAR)) == 0) {
        fprintf(stderr, "city menu bar was not rendered\n");
        return 0;
    }
    if (observation->menu_count != C2_OBSERVATION_MENU_LIMIT) {
        fprintf(stderr, "city menu bar has %d entries instead of %d\n",
                observation->menu_count, C2_OBSERVATION_MENU_LIMIT);
        return 0;
    }
    for (i = 0; i < observation->menu_count; i++) {
        if (observation->menu_x2[i] <= observation->menu_x1[i] ||
            (i != 0 &&
             observation->menu_x1[i] <= observation->menu_x2[i - 1])) {
            fprintf(stderr,
                    "city menu %d has invalid bounds %d..%d\n",
                    i, observation->menu_x1[i],
                    observation->menu_x2[i]);
            return 0;
        }
    }
    return 1;
}

static int click_city_menu(struct c2_sdl_smoke *smoke, Uint64 now,
                           const struct c2_observation *observation,
                           int menu_index)
{
    int x;

    x = (observation->menu_x1[menu_index] +
         observation->menu_x2[menu_index]) / 2;
    return click_mouse(smoke, now, x, 10, C2_HOST_MOUSE_LEFT);
}

static int menu_items_match(const struct c2_observation *observation,
                            int text_group, int item_count)
{
    if (observation->menu_item_group == text_group &&
        observation->menu_item_count == item_count) {
        return 1;
    }
    fprintf(stderr,
            "menu group %d has %d items, expected group %d with %d\n",
            observation->menu_item_group, observation->menu_item_count,
            text_group, item_count);
    return 0;
}

static enum c2_sdl_smoke_result drive_city(
    struct c2_sdl_smoke *smoke, Uint64 now,
    const struct c2_observation *observation)
{
    if (observation_is(observation, C2_OBSERVATION_MESSAGE)) {
        smoke->city_quiet_since = now;
        click_mouse(smoke, now, 0, 479, C2_HOST_MOUSE_RIGHT);
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
            if (observation->construction_plebs !=
                observation->required_construction_plebs) {
                fprintf(stderr,
                        "new province has %d of %d construction plebs\n",
                        observation->construction_plebs,
                        observation->required_construction_plebs);
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
            if (!city_menu_bar_is_valid(observation)) {
                return C2_SDL_SMOKE_FAILURE;
            }
            if (click_city_menu(smoke, now, observation, 0)) {
                smoke->phase = CITY_SMOKE_OPEN_FILE_MENU;
            }
        }
        break;
    case CITY_SMOKE_OPEN_FILE_MENU:
        if (observation_is(observation, C2_OBSERVATION_MENU_ITEMS)) {
            if (!menu_items_match(observation, 1, 4)) {
                return C2_SDL_SMOKE_FAILURE;
            }
            if (click_mouse(smoke, now, 320, 240,
                            C2_HOST_MOUSE_RIGHT)) {
                smoke->phase = CITY_SMOKE_CLOSE_FILE_MENU;
            }
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            click_city_menu(smoke, now, observation, 0);
        }
        break;
    case CITY_SMOKE_CLOSE_FILE_MENU:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            click_city_menu(smoke, now, observation, 1)) {
            smoke->phase = CITY_SMOKE_OPEN_OPTIONS_MENU;
        }
        break;
    case CITY_SMOKE_OPEN_OPTIONS_MENU:
        if (observation_is(observation, C2_OBSERVATION_MENU_ITEMS)) {
            if (!menu_items_match(observation, 2, 5)) {
                return C2_SDL_SMOKE_FAILURE;
            }
            if (click_mouse(smoke, now, 320, 240,
                            C2_HOST_MOUSE_RIGHT)) {
                smoke->phase = CITY_SMOKE_CLOSE_OPTIONS_MENU;
            }
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            click_city_menu(smoke, now, observation, 1);
        }
        break;
    case CITY_SMOKE_CLOSE_OPTIONS_MENU:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            type_character(smoke, now, 'p')) {
            smoke->phase = CITY_SMOKE_PAUSE;
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
#if C2_FEAT_ARROW_KEY_SCROLL
            c2_sdl_host_set_headless_arrow_keys(C2_HOST_ARROW_LEFT);
#else
            c2_sdl_host_set_headless_mouse(0, 240, 0);
            smoke->mouse_x = 0;
            smoke->mouse_y = 240;
#endif
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
#if C2_FEAT_ARROW_KEY_SCROLL
            c2_sdl_host_set_headless_arrow_keys(0);
#else
            c2_sdl_host_set_headless_mouse(320, 240, 0);
            smoke->mouse_x = 320;
            smoke->mouse_y = 240;
#endif
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
        if (observation->sequences_running &&
            observation->tune_branch_count > 0) {
            printf("recovered city-loop smoke completed with music branch %d\n",
                   observation->tune_branch);
            return C2_SDL_SMOKE_SUCCESS;
        }
        break;
    }
    return C2_SDL_SMOKE_RUNNING;
}

static enum c2_sdl_smoke_result drive_campania_transition(
    struct c2_sdl_smoke *smoke, Uint64 now,
    const struct c2_observation *observation)
{
    if (observation_is(observation, C2_OBSERVATION_MESSAGE)) {
        smoke->city_quiet_since = now;
        click_mouse(smoke, now, 0, 479, C2_HOST_MOUSE_RIGHT);
        return C2_SDL_SMOKE_RUNNING;
    }

    switch (smoke->phase) {
    case CAMPANIA_SMOKE_WAIT_FOR_CITY:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP)) {
            if (observation->province != CAMPANIA_REGION - 1) {
                fprintf(stderr, "entered province %d instead of Campania\n",
                        observation->province);
                return C2_SDL_SMOKE_FAILURE;
            }
            if (observation->speech_playing) {
                fprintf(stderr,
                        "Campania speech remained active after city entry\n");
                return C2_SDL_SMOKE_FAILURE;
            }
            smoke->city_quiet_since = now;
            smoke->phase = CAMPANIA_SMOKE_SETTLE;
        }
        break;
    case CAMPANIA_SMOKE_SETTLE:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP) &&
            now - smoke->city_quiet_since >= 300 &&
            click_mouse(smoke, now, 320, 240, C2_HOST_MOUSE_RIGHT)) {
            smoke->phase = CAMPANIA_SMOKE_WAIT_FOR_QUERY;
        }
        break;
    case CAMPANIA_SMOKE_WAIT_FOR_QUERY:
        if (observation_is(observation, C2_OBSERVATION_QUERY_PANEL)) {
            if (click_mouse(smoke, now, 10, 10,
                            C2_HOST_MOUSE_RIGHT)) {
                smoke->phase = CAMPANIA_SMOKE_WAIT_FOR_QUERY_CLOSE;
            }
        } else if (observation_is(observation,
                                  C2_OBSERVATION_CITY_LOOP) &&
                   now - smoke->last_input >= 250) {
            click_mouse(smoke, now, 320, 240, C2_HOST_MOUSE_RIGHT);
        }
        break;
    case CAMPANIA_SMOKE_WAIT_FOR_QUERY_CLOSE:
        if (observation_is(observation, C2_OBSERVATION_CITY_LOOP)) {
            printf("Campania speech transition smoke completed\n");
            return C2_SDL_SMOKE_SUCCESS;
        }
        if (observation_is(observation, C2_OBSERVATION_QUERY_PANEL) &&
            now - smoke->last_input >= 250) {
            click_mouse(smoke, now, 10, 10, C2_HOST_MOUSE_RIGHT);
        }
        break;
    }
    return C2_SDL_SMOKE_RUNNING;
}

static int capture_music_voices(
    struct c2_host_audio_observation observations[MUSIC_VOICE_COUNT])
{
    int index;

    for (index = 0; index < MUSIC_VOICE_COUNT; index++) {
        if (!c2_host_audio_observation_snapshot(
                MUSIC_VOICE_FIRST + index, &observations[index])) {
            fprintf(stderr, "could not observe music voice %d\n",
                    MUSIC_VOICE_FIRST + index);
            return 0;
        }
    }
    return 1;
}

static enum c2_sdl_smoke_result drive_music_buffer(
    struct c2_sdl_smoke *smoke, Uint64 now,
    const struct c2_observation *observation)
{
    struct c2_host_audio_observation voices[MUSIC_VOICE_COUNT];
    uint64_t produced_bytes;
    uint64_t underflow_bytes;
    unsigned int device_requests;
    unsigned int underflows;
    unsigned int queued_ms;
    unsigned int estimated_ms;
    int active_voices;
    int index;

    if (observation_is(observation, C2_OBSERVATION_MESSAGE)) {
        click_mouse(smoke, now, 0, 479, C2_HOST_MOUSE_RIGHT);
        return C2_SDL_SMOKE_RUNNING;
    }
    if (!observation_is(observation, C2_OBSERVATION_CITY_LOOP) ||
        !observation->sequences_running) {
        return C2_SDL_SMOKE_RUNNING;
    }
    if (!capture_music_voices(voices)) return C2_SDL_SMOKE_FAILURE;

    produced_bytes = 0;
    underflow_bytes = 0;
    device_requests = 0;
    underflows = 0;
    queued_ms = UINT_MAX;
    estimated_ms = UINT_MAX;
    active_voices = 0;
    for (index = 0; index < MUSIC_VOICE_COUNT; index++) {
        produced_bytes += voices[index].produced_bytes;
        underflow_bytes += voices[index].underflow_bytes;
        device_requests += voices[index].device_requests;
        underflows += voices[index].underflows;
        if (voices[index].active) {
            active_voices++;
            if (voices[index].queued_ms < queued_ms) {
                queued_ms = voices[index].queued_ms;
            }
            if (voices[index].estimated_queued_ms < estimated_ms) {
                estimated_ms = voices[index].estimated_queued_ms;
            }
        }
    }
    if (active_voices == 0 || produced_bytes == 0) {
        return C2_SDL_SMOKE_RUNNING;
    }

    if (smoke->music_started == 0) {
        smoke->music_started = now;
        smoke->music_last_sample = now - MUSIC_SAMPLE_LOG_INTERVAL_MS;
        smoke->music_initial_produced_bytes = produced_bytes;
        smoke->music_min_queued_ms = UINT_MAX;
        printf("music-buffer-ms elapsed actual estimated requests "
               "underflows missing-bytes produced-bytes\n");
    }
    smoke->music_samples++;
    if (queued_ms == 0) smoke->music_zero_fill_samples++;
    if (queued_ms < smoke->music_min_queued_ms) {
        smoke->music_min_queued_ms = queued_ms;
    }
    if (queued_ms > smoke->music_max_queued_ms) {
        smoke->music_max_queued_ms = queued_ms;
    }
    if (now - smoke->music_last_sample >= MUSIC_SAMPLE_LOG_INTERVAL_MS) {
        printf("music-buffer-ms %llu %u %u %u %u %llu %llu\n",
               (unsigned long long)(now - smoke->music_started),
               queued_ms, estimated_ms, device_requests, underflows,
               (unsigned long long)underflow_bytes,
               (unsigned long long)produced_bytes);
        smoke->music_last_sample = now;
    }
    if (now - smoke->music_started < MUSIC_SAMPLE_DURATION_MS) {
        return C2_SDL_SMOKE_RUNNING;
    }
#if !PLATFORM_WASM
    if (device_requests == 0) {
        fprintf(stderr,
                "music buffer was produced but the audio device never "
                "consumed it\n");
        return C2_SDL_SMOKE_FAILURE;
    }
#endif
    if (produced_bytes <= smoke->music_initial_produced_bytes) {
        fprintf(stderr,
                "music synthesis did not replenish the buffer during "
                "observation\n");
        return C2_SDL_SMOKE_FAILURE;
    }
    if (underflows != 0) {
        fprintf(stderr,
                "music buffer underfilled %u times (%llu missing bytes) "
                "over %llu ms\n",
                underflows, (unsigned long long)underflow_bytes,
                (unsigned long long)(now - smoke->music_started));
        return C2_SDL_SMOKE_FAILURE;
    }
    if (smoke->music_min_queued_ms < MUSIC_MIN_SAFE_QUEUE_MS) {
        fprintf(stderr,
                "music buffer fell to %u ms; expected at least %u ms of "
                "scheduling margin\n",
                smoke->music_min_queued_ms, MUSIC_MIN_SAFE_QUEUE_MS);
        return C2_SDL_SMOKE_FAILURE;
    }
#if PLATFORM_WASM
    if (smoke->music_zero_fill_samples != 0) {
        fprintf(stderr,
                "music buffer was empty in %u of %u browser samples\n",
                smoke->music_zero_fill_samples, smoke->music_samples);
        return C2_SDL_SMOKE_FAILURE;
    }
#endif
    printf("music buffer smoke completed over %llu ms with %u samples, "
           "%u..%u ms queued and no underflows\n",
           (unsigned long long)(now - smoke->music_started),
           smoke->music_samples, smoke->music_min_queued_ms,
           smoke->music_max_queued_ms);
    return C2_SDL_SMOKE_SUCCESS;
}

void c2_sdl_smoke_init(struct c2_sdl_smoke *smoke,
                       enum c2_sdl_smoke_kind kind, Uint64 now)
{
    memset(smoke, 0, sizeof(*smoke));
    smoke->kind = kind;
    smoke->started = now;
    smoke->phase = CITY_SMOKE_WAIT_FOR_CITY;
    smoke->last_tutorial_page = -1;
    smoke->music_min_queued_ms = UINT_MAX;
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
                "paused %d zoom %d map (%d,%d) mode %d pointer %d query %d "
                "out %d/%d/%d mouse %d/%d/%d %d/%d/%d speech %d "
                "music %d branch %d count %d "
                "file '%s'\n",
                observation.point, observation.detail, smoke->phase,
                observation.paused, observation.zoom_level,
                observation.map_x, observation.map_y,
                observation.map_mode, observation.pointer_mode,
                observation.query_type,
                observation.out1, observation.out2, observation.out3,
                observation.mouse_left_button,
                observation.mouse_left_preclick,
                observation.mouse_left_click,
                observation.mouse_right_button,
                observation.mouse_right_preclick,
                observation.mouse_right_click,
                observation.speech_playing,
                observation.sequences_running, observation.tune_branch,
                observation.tune_branch_count,
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
        if (smoke->kind == C2_SDL_SMOKE_CAMPANIA_TRANSITION &&
            smoke->confirmation_seen_at == 0) {
            smoke->confirmation_seen_at = now;
        }
        if (!observation.speech_playing) {
            fprintf(stderr,
                    "Campania confirmation did not start its speech line\n");
            return C2_SDL_SMOKE_FAILURE;
        }
        if (!smoke->confirmation_clicked &&
            (smoke->kind != C2_SDL_SMOKE_CAMPANIA_TRANSITION ||
             now - smoke->confirmation_seen_at >=
                 CAMPANIA_CONFIRM_DELAY_MS) &&
            click_mouse(smoke, now, 410, 330, C2_HOST_MOUSE_LEFT)) {
            smoke->confirmation_clicked = 1;
            if (smoke->kind == C2_SDL_SMOKE_CAMPANIA_TRANSITION) {
                printf("Campania confirmation clicked after %llu ms\n",
                       (unsigned long long)(
                           now - smoke->confirmation_seen_at));
            }
        }
    }

    if (smoke->kind == C2_SDL_SMOKE_CITY_LOOP) {
        return drive_city(smoke, now, &observation);
    }
    if (smoke->kind == C2_SDL_SMOKE_CAMPANIA_TRANSITION) {
        return drive_campania_transition(smoke, now, &observation);
    }
    if (smoke->kind == C2_SDL_SMOKE_MUSIC_BUFFER) {
        return drive_music_buffer(smoke, now, &observation);
    }
    if (smoke->kind == C2_SDL_SMOKE_SAVE_LOAD) {
        return drive_save_load(smoke, now, &observation);
    }
    return C2_SDL_SMOKE_RUNNING;
}
