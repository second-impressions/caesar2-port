#ifndef C2_PORT_KEYMAP_H
#define C2_PORT_KEYMAP_H

#include "c2_host.h"

int c2_port_event_to_legacy_key(const struct c2_host_event *event,
                                unsigned char *ascii,
                                unsigned char *scan_code);

#endif /* C2_PORT_KEYMAP_H */
