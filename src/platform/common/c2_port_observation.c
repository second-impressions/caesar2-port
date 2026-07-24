#include <string.h>

#include "c2_data.h"
#include "c2_host.h"
#include "c2_observation.h"

static void fill_observation(struct c2_observation *observation)
{
    int i;

    memset(observation, 0, sizeof(*observation));
    observation->province = province_is;
    observation->map_mode = map_mode;
    observation->zoom_level = zoom_level;
    observation->paused = c2inf.paused;
    observation->peace_mode = c2inf.peace_mode;
    observation->tutorial_mode = tutorial_mode;
    observation->in_forum = in_the_forum;
    observation->map_x = pm_x;
    observation->map_y = pm_y;
    observation->sequences_running = sequences_running;
    observation->tune_branch = tune_branch;
    observation->tune_branch_count = tune_branch_count;
    observation->menu_count = C2_OBSERVATION_MENU_LIMIT;
    for (i = 0; i < C2_OBSERVATION_MENU_LIMIT; i++) {
        observation->menu_x1[i] = main_menu[i].u.pos.x1;
        observation->menu_x2[i] = main_menu[i].u.pos.x2;
    }
    memcpy(observation->player_name, c2inf.player_name,
           sizeof(observation->player_name));
    observation->player_name[sizeof(observation->player_name) - 1] = '\0';
    memcpy(observation->filename, filename, sizeof(observation->filename));
    observation->filename[sizeof(observation->filename) - 1] = '\0';
}

void c2_observe(enum c2_observation_point point, int detail)
{
    struct c2_observation observation;

    fill_observation(&observation);
    observation.point = point;
    observation.detail = detail;
    c2_host_publish_observation(&observation);
}

void c2_observe_menu_bar(int menu_count, int active_menu)
{
    struct c2_observation observation;

    fill_observation(&observation);
    observation.point = C2_OBSERVATION_MENU_BAR;
    observation.menu_count = menu_count;
    observation.active_menu = active_menu;
    c2_host_publish_observation(&observation);
}

void c2_observe_menu_items(int text_group, int item_count, int active_item)
{
    struct c2_observation observation;

    fill_observation(&observation);
    observation.point = C2_OBSERVATION_MENU_ITEMS;
    observation.menu_item_group = text_group;
    observation.menu_item_count = item_count;
    observation.active_menu_item = active_item;
    c2_host_publish_observation(&observation);
}
