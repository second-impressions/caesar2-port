#include <string.h>

#include "c2_citizen_index.h"

#if PORT_FEAT_WIDE_CITIZEN_INDEX

unsigned short c2_cell_citizen_a[PORT_CITY_CELLS];
unsigned short c2_cell_citizen_b[PORT_CITY_CELLS];
unsigned short c2_cell_envoy[PORT_CITY_CELLS];
unsigned short c2_citizen_target[PORT_CITIZEN_SLOTS];
unsigned short c2_q_people_wide[10];

void c2_citizen_index_clear(void)
{
    memset(c2_cell_citizen_a, 0, sizeof(c2_cell_citizen_a));
    memset(c2_cell_citizen_b, 0, sizeof(c2_cell_citizen_b));
    memset(c2_cell_envoy, 0, sizeof(c2_cell_envoy));
    memset(c2_citizen_target, 0, sizeof(c2_citizen_target));
}

#endif
