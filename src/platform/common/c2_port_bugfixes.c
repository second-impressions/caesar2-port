#include "c2_bugfixes.h"

unsigned int c2_fix_dispatch_rotation(int year, int month)
{
#if PORT_FIX_WALKER_DISPATCH_FAIRNESS
    /* Calendar month count. Both fields are save state, so a reload keeps the
     * same order; the unsigned conversion makes the early negative years
     * well defined. */
    return (unsigned int)(year * 12 + month);
#else
    (void)year;
    (void)month;
    return 0u;
#endif
}

int c2_fix_dispatch_phase(int phase_slot, unsigned int rotation)
{
#if PORT_FIX_WALKER_DISPATCH_FAIRNESS
    return (int)((((unsigned int)phase_slot >> 2) + rotation) & 3u);
#else
    (void)rotation;
    return phase_slot >> 2;
#endif
}

int c2_fix_dispatch_column(int column_index, unsigned int rotation)
{
#if PORT_FIX_WALKER_DISPATCH_FAIRNESS
    /* 23 is coprime with the map's 80 columns, so successive months start the
     * sweep at well-separated columns instead of drifting by one. Reduce the
     * offset before adding: unsigned wrap-around at 2^32 is not a multiple of
     * 80, so a large rotation would otherwise map two columns to one. */
    unsigned int offset = (rotation % 80u) * 23u % 80u;

    return (int)(((unsigned int)column_index + offset) % 80u);
#else
    (void)rotation;
    return column_index;
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
