#include <string.h>

#include "c2_data.h"
#include "c2_host.h"
#include "c2_observation.h"

void c2_observe(enum c2_observation_point point, int detail)
{
    struct c2_observation observation;

    memset(&observation, 0, sizeof(observation));
    observation.point = point;
    observation.detail = detail;
    observation.province = province_is;
    observation.map_mode = map_mode;
    observation.zoom_level = zoom_level;
    observation.paused = c2inf.paused;
    observation.peace_mode = c2inf.peace_mode;
    observation.in_forum = in_the_forum;
    observation.map_x = pm_x;
    observation.map_y = pm_y;
    c2_host_publish_observation(&observation);
}
