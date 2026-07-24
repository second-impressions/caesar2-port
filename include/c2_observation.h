#ifndef C2_OBSERVATION_H
#define C2_OBSERVATION_H

#include <stdint.h>

enum c2_observation_point {
    C2_OBSERVATION_NONE,
    C2_OBSERVATION_ENGINE_STARTED,
    C2_OBSERVATION_STARTUP,
    C2_OBSERVATION_SKILL_SELECTION,
    C2_OBSERVATION_SKILL_DETAILS,
    C2_OBSERVATION_PROVINCE_INTRO,
    C2_OBSERVATION_PROVINCE_SELECTION,
    C2_OBSERVATION_PROVINCE_CONFIRMATION,
    C2_OBSERVATION_PROVINCE_INITIALIZED,
    C2_OBSERVATION_CITY_LOOP,
    C2_OBSERVATION_MESSAGE,
    C2_OBSERVATION_FORUM,
    C2_OBSERVATION_NAME_ENTRY,
    C2_OBSERVATION_TUTORIAL_PAGE,
    C2_OBSERVATION_CONFIRMATION,
    C2_OBSERVATION_FILE_DIALOG,
    C2_OBSERVATION_SAVE_COMPLETE,
    C2_OBSERVATION_LOAD_COMPLETE,
    C2_OBSERVATION_MENU_BAR,
    C2_OBSERVATION_MENU_ITEMS,
    C2_OBSERVATION_QUERY_PANEL,
    C2_OBSERVATION_ENGINE_STOPPED
};

#define C2_OBSERVATION_MENU_LIMIT 4

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
    int menu_x1[C2_OBSERVATION_MENU_LIMIT];
    int menu_x2[C2_OBSERVATION_MENU_LIMIT];
    char player_name[26];
    char filename[13];
};

void c2_observe(enum c2_observation_point point, int detail);
void c2_observe_menu_bar(int menu_count, int active_menu);
void c2_observe_menu_items(int text_group, int item_count, int active_item);

#endif /* C2_OBSERVATION_H */
