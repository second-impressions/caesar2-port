#include "c2_text_compat.h"

#include <string.h>

extern char text_buffer[];

static unsigned int read_u32_le(const unsigned char *bytes)
{
    return (unsigned int)bytes[0] |
           (unsigned int)bytes[1] << 8 |
           (unsigned int)bytes[2] << 16 |
           (unsigned int)bytes[3] << 24;
}

int c2_text_group_string_count_in_buffer(const char *buffer,
                                         size_t buffer_capacity,
                                         int group_index)
{
    const unsigned char *bytes;
    unsigned int first_offset;
    unsigned int group_count;
    unsigned int start;
    unsigned int end;
    unsigned int candidate;
    unsigned int i;
    int string_count;

    if (buffer == NULL || buffer_capacity < 16 || group_index < 1)
        return -1;

    bytes = (const unsigned char *)buffer;
    if (memcmp(bytes, "Textfile", 8) != 0)
        return -1;

    first_offset = read_u32_le(bytes + 12);
    if (first_offset < 16 || first_offset > buffer_capacity ||
        (first_offset - 8) % 4 != 0)
        return -1;

    group_count = (first_offset - 8) / 4;
    if ((unsigned int)group_index >= group_count)
        return -1;

    start = read_u32_le(bytes + 8 + (unsigned int)group_index * 4);
    if (start < first_offset || start >= buffer_capacity)
        return -1;

    end = (unsigned int)buffer_capacity;
    for (i = 1; i < group_count; i++) {
        candidate = read_u32_le(bytes + 8 + i * 4);
        if (candidate > start && candidate < end)
            end = candidate;
    }
    if (end == buffer_capacity)
        return -1;

    string_count = 0;
    for (i = start; i < end; i++) {
        if (bytes[i] == 0 && i > start &&
            (bytes[i - 1] >= ' ' || bytes[i - 1] == 0)) {
            string_count++;
        }
    }
    return string_count;
}

int c2_text_group_has_string(int group_index, int string_index)
{
    int string_count;

    if (string_index < 0)
        return 0;

    string_count = c2_text_group_string_count_in_buffer(
        text_buffer, C2_TEXT_BUFFER_CAPACITY, group_index);
    return string_count > string_index;
}

int c2_text_has_new_game_cancel(void)
{
    return c2_text_group_has_string(0x2b, 0x12);
}

int c2_text_has_late_region_quotes(void)
{
    return c2_text_group_has_string(0x45, 0x1e);
}
