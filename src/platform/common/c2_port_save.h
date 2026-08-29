#ifndef PORT_SAVE_H
#define PORT_SAVE_H

#include <stddef.h>

#include "c2_types.h"

int c2_port_save_registry_valid(const struct save_entry *entries,
                                size_t entry_count,
                                const struct figure_rec *figures,
                                const struct arrow_rec *arrows);
int c2_port_save_state_file_matches(
    const char *filename, const struct save_entry *entries,
    size_t entry_count, const struct figure_rec *figures,
    const struct arrow_rec *arrows, size_t *mismatch_offset);
int c2_port_save_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            const struct figure_rec *figures,
                            const struct arrow_rec *arrows);
int c2_port_load_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            struct figure_rec *figures,
                            struct arrow_rec *arrows);

#endif /* PORT_SAVE_H */
