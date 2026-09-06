#include "c2_bugfixes.h"

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
