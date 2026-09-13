#include "c2_bugfixes.h"

int c2_fix_envoy_retires_itself(int recorded_citizen, int replacement_citizen)
{
#if PORT_FIX_MARKET_ENVOY_SELF_KILL
    return recorded_citizen == replacement_citizen;
#else
    (void)recorded_citizen;
    (void)replacement_citizen;
    return 0;
#endif
}

void c2_fix_player_name_padding(char *name, int capacity)
{
#if PORT_FIX_PLAYER_NAME_PADDING
    int length;

    length = 0;
    while (length < capacity && name[length] != '\0') length++;
    while (length > 0 && name[length - 1] == ' ') length--;
    if (length < capacity) name[length] = '\0';
#else
    (void)name;
    (void)capacity;
#endif
}
