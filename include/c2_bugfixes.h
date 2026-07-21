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

#endif
