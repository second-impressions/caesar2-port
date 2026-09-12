#ifndef PORT_SAVE_H
#define PORT_SAVE_H

#include <stddef.h>

#include "c2_save_compat.h"
#include "c2_types.h"

/*
 * Engine adapter for the save format (core: c2_save_v1.h). These are the
 * entry points the recovered loadsave.c calls on the portable target. The
 * registry arguments are kept so the adapter can be pointed at synthetic
 * state, but the functions read and write the engine's globals.
 */

int c2_port_save_registry_valid(const struct save_entry *entries,
                                size_t entry_count,
                                const struct figure_rec *figures,
                                const struct arrow_rec *arrows);

/* Write live state as a container. Atomic: temp file then rename. */
int c2_port_save_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            const struct figure_rec *figures,
                            const struct arrow_rec *arrows);

/* Read a container or an original-layout file into live state. Nothing is
 * committed unless the whole file decodes and validates. */
int c2_port_load_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            struct figure_rec *figures,
                            struct arrow_rec *arrows);

/* Debug verifier: does the file describe the same state as the engine now
 * holds? On mismatch *mismatch_part names the first differing part. */
int c2_port_save_state_file_matches(
    const char *filename, const struct save_entry *entries,
    size_t entry_count, const struct figure_rec *figures,
    const struct arrow_rec *arrows, const char **mismatch_part);

/* Last load/save diagnostics for the UI and logs. */
const char *c2_port_save_last_error(void);

/* Battle figures: the secondary-sprite bit the engine keeps as a pointer. */
extern unsigned char c2_figure_secondary_sprite[C2_SAVE_FIGURE_COUNT];

/* Monthly history ring, in memory on the portable target (loadsave.c). */
void c2_port_history_reset(void);
void c2_port_history_store(const int *entry, int slot);
void c2_port_history_copy(int *out);

#endif /* PORT_SAVE_H */
