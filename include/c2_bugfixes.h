#ifndef C2_BUGFIXES_H
#define C2_BUGFIXES_H

/*
 * Bug fixes are enabled by default. Define a switch to 0 before including
 * this header (or on the compiler command line) to restore shipped behavior.
 */
#ifndef C2_FIX_MEDIUM_RIGHT_HAT_OFFSET
#define C2_FIX_MEDIUM_RIGHT_HAT_OFFSET 1
#endif

#if C2_FIX_MEDIUM_RIGHT_HAT_OFFSET != 0 && \
    C2_FIX_MEDIUM_RIGHT_HAT_OFFSET != 1
#error "C2_FIX_MEDIUM_RIGHT_HAT_OFFSET must be 0 or 1"
#endif

#endif
