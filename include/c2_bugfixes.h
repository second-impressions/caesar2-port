#ifndef C2_BUGFIXES_H
#define C2_BUGFIXES_H

/*
 * Bug fixes are enabled by default. Define a switch to 0 before including
 * this header (or on the compiler command line) to restore shipped behavior.
 */
#ifndef C2_FIX_MEDIUM_RIGHT_HAT_OFFSET
#define C2_FIX_MEDIUM_RIGHT_HAT_OFFSET 1
#endif

#ifndef C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR
#define C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR 1
#endif

#ifndef C2_FIX_GFX_BUFFER_DOUBLE_FREE
#define C2_FIX_GFX_BUFFER_DOUBLE_FREE 1
#endif

#ifndef C2_FIX_HELP_SMART_PUNCTUATION
#define C2_FIX_HELP_SMART_PUNCTUATION 1
#endif

#ifndef C2_FIX_PLAYER_NAME_PADDING
#define C2_FIX_PLAYER_NAME_PADDING 1
#endif

#if C2_FIX_MEDIUM_RIGHT_HAT_OFFSET != 0 && \
    C2_FIX_MEDIUM_RIGHT_HAT_OFFSET != 1
#error "C2_FIX_MEDIUM_RIGHT_HAT_OFFSET must be 0 or 1"
#endif

#if C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR != 0 && \
    C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR != 1
#error "C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR must be 0 or 1"
#endif

#if C2_FIX_GFX_BUFFER_DOUBLE_FREE != 0 && \
    C2_FIX_GFX_BUFFER_DOUBLE_FREE != 1
#error "C2_FIX_GFX_BUFFER_DOUBLE_FREE must be 0 or 1"
#endif

#if C2_FIX_HELP_SMART_PUNCTUATION != 0 && \
    C2_FIX_HELP_SMART_PUNCTUATION != 1
#error "C2_FIX_HELP_SMART_PUNCTUATION must be 0 or 1"
#endif

#if C2_FIX_PLAYER_NAME_PADDING != 0 && \
    C2_FIX_PLAYER_NAME_PADDING != 1
#error "C2_FIX_PLAYER_NAME_PADDING must be 0 or 1"
#endif

void c2_fix_help_text(char *text, int length);
void c2_fix_player_name_padding(char *name, int capacity);

#endif
