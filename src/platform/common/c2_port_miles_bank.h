#ifndef C2_PORT_MILES_BANK_H
#define C2_PORT_MILES_BANK_H

#include <stddef.h>

struct ADL_MIDIPlayer;

int c2_port_apply_miles_bank(struct ADL_MIDIPlayer *player,
                             const unsigned char *data, size_t data_size);

#endif
