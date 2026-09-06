#ifndef C2_BUGFIXES_H
#define C2_BUGFIXES_H

#include "c2_target.h"

/*
 * Bug fixes default to the portable continuation only. Define a switch on
 * the compiler command line to override that target default. Shipped DOS and
 * Windows builds must retain their recovered behavior unless explicitly
 * selected otherwise.
 */
#ifndef PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET
#define PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET PORT_PLATFORM
#endif

#ifndef PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR
#define PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR PORT_PLATFORM
#endif

#ifndef PORT_FIX_GFX_BUFFER_DOUBLE_FREE
#define PORT_FIX_GFX_BUFFER_DOUBLE_FREE PORT_PLATFORM
#endif

#ifndef PORT_FIX_PLAYER_NAME_PADDING
#define PORT_FIX_PLAYER_NAME_PADDING PORT_PLATFORM
#endif

#ifndef PORT_FIX_LARGE_XMI_ASSETS
#define PORT_FIX_LARGE_XMI_ASSETS PORT_PLATFORM
#endif

#ifndef C2_FIX_MOSAIC_RANDOM_SENTINEL
#define C2_FIX_MOSAIC_RANDOM_SENTINEL PORT_PLATFORM
#endif

#if PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET != 0 && \
    PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET != 1
#error "PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET must be 0 or 1"
#endif

#if PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR != 0 && \
    PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR != 1
#error "PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR must be 0 or 1"
#endif

#if PORT_FIX_GFX_BUFFER_DOUBLE_FREE != 0 && \
    PORT_FIX_GFX_BUFFER_DOUBLE_FREE != 1
#error "PORT_FIX_GFX_BUFFER_DOUBLE_FREE must be 0 or 1"
#endif


#if PORT_FIX_PLAYER_NAME_PADDING != 0 && \
    PORT_FIX_PLAYER_NAME_PADDING != 1
#error "PORT_FIX_PLAYER_NAME_PADDING must be 0 or 1"
#endif

#if PORT_FIX_LARGE_XMI_ASSETS != 0 && PORT_FIX_LARGE_XMI_ASSETS != 1
#error "PORT_FIX_LARGE_XMI_ASSETS must be 0 or 1"
#endif

#if C2_FIX_MOSAIC_RANDOM_SENTINEL != 0 && \
    C2_FIX_MOSAIC_RANDOM_SENTINEL != 1
#error "C2_FIX_MOSAIC_RANDOM_SENTINEL must be 0 or 1"
#endif

void c2_fix_player_name_padding(char *name, int capacity);

#endif
