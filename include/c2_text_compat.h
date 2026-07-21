#ifndef C2_TEXT_COMPAT_H
#define C2_TEXT_COMPAT_H

#include <stddef.h>

#define C2_TEXT_BUFFER_CAPACITY 40000

int c2_text_group_string_count_in_buffer(const char *buffer,
                                         size_t buffer_capacity,
                                         int group_index);
int c2_text_group_has_string(int group_index, int string_index);
int c2_text_has_new_game_cancel(void);
int c2_text_has_late_region_quotes(void);

#endif
