#include "c2_port_save.h"

#include "c2_save_compat.h"

int c2_port_save_registry_valid(const struct save_entry *entries,
                                size_t entry_count,
                                const struct figure_rec *figures,
                                const struct arrow_rec *arrows)
{
    size_t state_size;
    size_t block_size;
    size_t i;

    if (entries == NULL || figures == NULL || arrows == NULL) return 0;
    state_size = 0;
    for (i = 0; i < entry_count; i++) {
        if (entries[i].size == 0) break;
        if (entries[i].size < 0) return 0;
        block_size = (size_t)entries[i].size;
        if ((entries[i].buf == figures &&
             block_size != C2_SAVE_FIGURES_SIZE) ||
            (entries[i].buf == arrows &&
             block_size != C2_SAVE_ARROWS_SIZE) ||
            block_size > C2_SAVE_STATE_SIZE - state_size) {
            return 0;
        }
        state_size += block_size;
    }
    return state_size == C2_SAVE_STATE_SIZE;
}
