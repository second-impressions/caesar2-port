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
    C2_OBSERVATION_ENGINE_STOPPED
};

struct c2_observation {
    uint64_t sequence;
    uint64_t reached;
    enum c2_observation_point point;
    int detail;
    int province;
    int map_mode;
    int zoom_level;
    int paused;
    int peace_mode;
    int tutorial_mode;
    int in_forum;
    int map_x;
    int map_y;
    char player_name[26];
    char filename[13];
};

void c2_observe(enum c2_observation_point point, int detail);

#endif /* C2_OBSERVATION_H */
