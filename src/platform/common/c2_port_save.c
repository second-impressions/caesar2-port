#include <stdlib.h>
#include <string.h>

#include "c2_host.h"
#include "c2_port_save.h"
#include "c2_save_compat.h"

#define C2_SAVE_REGISTRY_CAPACITY 500
#define C2_HISTORY_FILENAME "history.dat"

int c2_port_save_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            const struct figure_rec *figures,
                            const struct arrow_rec *arrows)
{
    unsigned char *file_data;
    size_t history_size;
    size_t offset;
    size_t block_size;
    size_t i;
    int result;

    if (entry_count != C2_SAVE_REGISTRY_CAPACITY ||
        !c2_port_save_registry_valid(entries, entry_count,
                                     figures, arrows)) {
        return 0;
    }
    file_data = malloc(C2_SAVE_FILE_SIZE + 1);
    if (file_data == NULL) return 0;

    offset = 0;
    for (i = 0; i < entry_count; i++) {
        if (entries[i].size == 0) break;
        block_size = (size_t)entries[i].size;
        if (entries[i].buf == figures) {
            c2_save_pack_figures(file_data + offset, figures);
        } else if (entries[i].buf == arrows) {
            c2_save_pack_arrows(file_data + offset, arrows);
        } else {
            memcpy(file_data + offset, entries[i].buf, block_size);
        }
        offset += block_size;
    }

    history_size = c2_host_user_file_read(C2_HISTORY_FILENAME,
                                           file_data + offset,
                                           C2_SAVE_HISTORY_SIZE + 1, 0);
    result = history_size == C2_SAVE_HISTORY_SIZE &&
             c2_host_user_file_write(filename, file_data,
                                     C2_SAVE_FILE_SIZE);
    free(file_data);
    return result;
}

int c2_port_load_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            struct figure_rec *figures,
                            struct arrow_rec *arrows)
{
    unsigned char *file_data;
    size_t file_size;
    size_t offset;
    size_t block_size;
    size_t i;

    if (entry_count != C2_SAVE_REGISTRY_CAPACITY ||
        !c2_port_save_registry_valid(entries, entry_count,
                                     figures, arrows)) {
        return 0;
    }
    file_data = malloc(C2_SAVE_FILE_SIZE + 1);
    if (file_data == NULL) return 0;
    file_size = c2_host_user_file_read(filename, file_data,
                                       C2_SAVE_FILE_SIZE + 1, 0);
    if (file_size != C2_SAVE_FILE_SIZE ||
        !c2_host_user_file_write(C2_HISTORY_FILENAME,
                                 file_data + C2_SAVE_STATE_SIZE,
                                 C2_SAVE_HISTORY_SIZE)) {
        free(file_data);
        return 0;
    }

    offset = 0;
    for (i = 0; i < entry_count; i++) {
        if (entries[i].size == 0) break;
        block_size = (size_t)entries[i].size;
        if (entries[i].buf == figures) {
            c2_save_unpack_figures(figures, file_data + offset);
        } else if (entries[i].buf == arrows) {
            c2_save_unpack_arrows(arrows, file_data + offset);
        } else {
            memcpy(entries[i].buf, file_data + offset, block_size);
        }
        offset += block_size;
    }
    free(file_data);
    return 1;
}
