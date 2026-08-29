#include <stdlib.h>
#include <string.h>

#include "c2_host.h"
#include "c2_port_save.h"
#include "c2_save_compat.h"

#define C2_SAVE_REGISTRY_CAPACITY 500
#define C2_HISTORY_FILENAME "history.dat"

static size_t pack_registered_state(
    unsigned char *destination,
    const struct save_entry *entries, size_t entry_count,
    const struct figure_rec *figures, const struct arrow_rec *arrows)
{
    size_t offset = 0;
    size_t block_size;
    size_t i;

    for (i = 0; i < entry_count; i++) {
        if (entries[i].size == 0) break;
        block_size = (size_t)entries[i].size;
        if (entries[i].buf == figures) {
            c2_save_pack_figures(destination + offset, figures);
        } else if (entries[i].buf == arrows) {
            c2_save_pack_arrows(destination + offset, arrows);
        } else {
            memcpy(destination + offset, entries[i].buf, block_size);
        }
        offset += block_size;
    }
    return offset;
}

int c2_port_save_state_file_matches(
    const char *filename, const struct save_entry *entries,
    size_t entry_count, const struct figure_rec *figures,
    const struct arrow_rec *arrows, size_t *mismatch_offset)
{
    unsigned char *expected;
    unsigned char *actual;
    size_t actual_size;
    size_t history_size;
    size_t offset;
    int matches = 0;

    if (mismatch_offset != NULL) *mismatch_offset = (size_t)-1;
    if (filename == NULL || entry_count != C2_SAVE_REGISTRY_CAPACITY ||
        !c2_port_save_registry_valid(entries, entry_count,
                                     figures, arrows)) return 0;
    expected = malloc(C2_SAVE_FILE_SIZE);
    actual = malloc(C2_SAVE_FILE_SIZE + 1);
    if (expected == NULL || actual == NULL) goto done;
    offset = pack_registered_state(expected, entries, entry_count,
                                   figures, arrows);
    if (offset != C2_SAVE_STATE_SIZE) goto done;
    history_size = c2_host_user_file_read(C2_HISTORY_FILENAME,
                                           expected + offset,
                                           C2_SAVE_HISTORY_SIZE + 1, 0);
    actual_size = c2_host_user_file_read(filename, actual,
                                         C2_SAVE_FILE_SIZE + 1, 0);
    if (history_size != C2_SAVE_HISTORY_SIZE ||
        actual_size != C2_SAVE_FILE_SIZE) goto done;
    for (offset = 0; offset < C2_SAVE_FILE_SIZE; offset++) {
        if (expected[offset] != actual[offset]) {
            if (mismatch_offset != NULL) *mismatch_offset = offset;
            goto done;
        }
    }
    matches = 1;

done:
    free(expected);
    free(actual);
    return matches;
}

int c2_port_save_game_state(const char *filename,
                            const struct save_entry *entries,
                            size_t entry_count,
                            const struct figure_rec *figures,
                            const struct arrow_rec *arrows)
{
    unsigned char *file_data;
    size_t history_size;
    size_t offset;
    int result;

    if (entry_count != C2_SAVE_REGISTRY_CAPACITY ||
        !c2_port_save_registry_valid(entries, entry_count,
                                     figures, arrows)) {
        return 0;
    }
    file_data = malloc(C2_SAVE_FILE_SIZE + 1);
    if (file_data == NULL) return 0;

    offset = pack_registered_state(file_data, entries, entry_count,
                                   figures, arrows);

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
