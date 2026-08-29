#include "c2_port.h"

#if PORT_FIX_PAUSED_MUSIC_VARIETY
int c2_port_paused_music_branch(int base, int count,
                                int current_branch, int branch_count)
{
    unsigned int sequence;
    int candidate;

    if (count <= 1) return base;
    sequence = (unsigned int)branch_count;
    candidate = base + (int)((sequence * 5u + 2u) % (unsigned int)count);
    if (candidate == current_branch) {
        candidate = base + (candidate - base + 1) % count;
    }
    return candidate;
}
#endif
