#ifndef C2_TYPES_H
#define C2_TYPES_H

/* Shared Caesar II structs, typedef-like records, and map helpers.
 *
 * `entities.h` is the historical reconstruction that currently contains both
 * struct definitions and the map/cell macros that would have lived in a shared
 * PS-era globals/defs header.  Include it through this stable layer in new
 * source; keep `entities.h` available for older file-local comments and direct
 * includes during cleanup.
 */
#include "entities.h"

/* Pointer-valued globals (scratch_buffer, people_data) are stored as
 * ints in the original data segment; cast them inline at each use. */

/* DPMI real-mode buffer descriptor: 32-bit linear offset + 16-bit
 * protected-mode selector.  Matches the 6-byte VesaInfo /
 * VesaModeInfo blocks PS allocates via int 0x31 fn 0x0100 and
 * stuffs through `MK_FP(seg, 0)` so the real-mode VESA driver can
 * write into them. */
struct dpmi_real_block {
    int   offset;     /* +0x00 */
    short selector;   /* +0x04 */
};

/* DPMI int 0x31 fn 0x0500 Free Memory Info Block: 48 bytes returned
 * by the DPMI host (DOS/4GW).  PS reads only the free-linear-pages
 * slot at +0x1C and shifts it left by 2 to convert pages-to-KB-ish
 * (DPMI page == 4 KB). */
struct dpmi_mem_info {
    int largest_avail_block;   /* +0x00  largest free block, bytes  */
    int max_unlocked_pages;    /* +0x04                              */
    int max_locked_pages;      /* +0x08                              */
    int linear_space_pages;    /* +0x0C                              */
    int total_unlocked_pages;  /* +0x10                              */
    int total_free_pages;      /* +0x14                              */
    int total_physical_pages;  /* +0x18                              */
    int free_linear_pages;     /* +0x1C  PS reads this slot          */
    int paging_file_pages;     /* +0x20                              */
    int reserved[3];           /* +0x24..+0x2F                       */
};

/* Heading / facing direction returned by get_heading(): the 8-point
 * compass rose, clockwise from north (screen coords, +y downward).
 * Values 8..15 (HEADING_STILL + facing) mean "source == target":
 * stationary, retaining the facing direction passed as `mode`. */
typedef enum {
    HEADING_N  = 0,
    HEADING_NE = 1,
    HEADING_E  = 2,
    HEADING_SE = 3,
    HEADING_S  = 4,
    HEADING_SW = 5,
    HEADING_W  = 6,
    HEADING_NW = 7,
    HEADING_STILL = 8
} heading_t;

#endif /* C2_TYPES_H */
