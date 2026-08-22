#ifndef PORT_OBSERVATION_H
#define PORT_OBSERVATION_H

#include <stdint.h>

enum c2_observation_point {
    PORT_OBSERVATION_NONE,
    PORT_OBSERVATION_ENGINE_STARTED,
    PORT_OBSERVATION_STARTUP,
    PORT_OBSERVATION_SKILL_SELECTION,
    PORT_OBSERVATION_SKILL_DETAILS,
    PORT_OBSERVATION_PROVINCE_INTRO,
    PORT_OBSERVATION_PROVINCE_SELECTION,
    PORT_OBSERVATION_PROVINCE_CONFIRMATION,
    PORT_OBSERVATION_PROVINCE_INITIALIZED,
    PORT_OBSERVATION_CITY_LOOP,
    PORT_OBSERVATION_MESSAGE,
    PORT_OBSERVATION_FORUM,
    PORT_OBSERVATION_NAME_ENTRY,
    PORT_OBSERVATION_TUTORIAL_PAGE,
    PORT_OBSERVATION_CONFIRMATION,
    PORT_OBSERVATION_FILE_DIALOG,
    PORT_OBSERVATION_SAVE_COMPLETE,
    PORT_OBSERVATION_LOAD_COMPLETE,
    PORT_OBSERVATION_MENU_BAR,
    PORT_OBSERVATION_MENU_ITEMS,
    PORT_OBSERVATION_QUERY_PANEL,
    PORT_OBSERVATION_ENGINE_STOPPED
};

#define PORT_OBSERVATION_MENU_LIMIT 4

struct c2_observation {
    uint64_t sequence;
    uint64_t reached;
    enum c2_observation_point point;
    int detail;
    int province;
    int map_mode;
    int pointer_mode;
    int zoom_level;
    int paused;
    int peace_mode;
    int tutorial_mode;
    int in_forum;
    int map_x;
    int map_y;
    int construction_plebs;
    int required_construction_plebs;
    int sequences_running;
    int speech_playing;
    int query_type;
    int out1;
    int out2;
    int out3;
    int mouse_left_button;
    int mouse_left_preclick;
    int mouse_left_click;
    int mouse_right_button;
    int mouse_right_preclick;
    int mouse_right_click;
    int tune_branch;
    int tune_branch_count;
    int menu_count;
    int active_menu;
    int menu_item_group;
    int menu_item_count;
    int active_menu_item;
    int menu_x1[PORT_OBSERVATION_MENU_LIMIT];
    int menu_x2[PORT_OBSERVATION_MENU_LIMIT];
    char player_name[26];
    char filename[13];
};

void c2_observe(enum c2_observation_point point, int detail);
void c2_observe_menu_bar(int menu_count, int active_menu);
void c2_observe_menu_items(int text_group, int item_count, int active_item);

#endif /* PORT_OBSERVATION_H */
