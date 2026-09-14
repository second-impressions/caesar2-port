#include <stdint.h>
#include <string.h>

#include "c2_save_compat.h"

/*
 * Layout guards for the recovered records the save format carries as byte
 * images and for the original (version 0) layout the importer reads. There
 * is no code here on purpose: the format's codec is c2_save_v1.c.
 */

#define C2_FIGURE_POINTER_OFFSET 0x0a
#define C2_FIGURE_DISK_TAIL_OFFSET 0x12
#define C2_ARROW_POINTER_OFFSET 0x08
#define C2_ARROW_DISK_TAIL_OFFSET 0x0c

_Static_assert(sizeof(char) == 1, "save format requires 8-bit bytes");
_Static_assert(sizeof(short) == 2, "save format requires 16-bit shorts");
_Static_assert(sizeof(int) == 4, "save format requires 32-bit ints");
_Static_assert(sizeof(struct c2inf_rec) == 0x40,
               "c2inf layout must match the original file");
_Static_assert(sizeof(struct army_rec) == 175,
               "army save records must retain one-byte packing");
_Static_assert(sizeof(struct citizen_rec) == 58,
               "citizen save records must retain one-byte packing");
_Static_assert(sizeof(struct unit_rec) == 78,
               "unit save records must retain one-byte packing");
_Static_assert(sizeof(struct army_route_rec) == 346,
               "army-route save records must retain one-byte packing");
_Static_assert(sizeof(struct province_industry) == 16,
               "province-industry save records must retain their layout");
_Static_assert(sizeof(struct industry_rec) == 48,
               "industry save records must retain their layout");
_Static_assert(sizeof(struct city_cell) == 20,
               "city-map save cells must retain their layout");
_Static_assert(sizeof(struct region_cell) == 8,
               "region-map save cells must retain their layout");
_Static_assert(sizeof(struct battle_cell) == 4,
               "battle-map save cells must retain their layout");
_Static_assert(sizeof(struct slave_req) == 8,
               "slave-requirement save records must retain their layout");
_Static_assert(sizeof(struct msg_slot) == 8,
               "message save records must retain their layout");

_Static_assert(offsetof(struct figure_rec, arrow_data_ptr) ==
                   C2_FIGURE_POINTER_OFFSET,
               "figure pointer prefix changed");
_Static_assert(offsetof(struct figure_rec, sprite_data_ptr) ==
                   C2_FIGURE_POINTER_OFFSET + sizeof(void *),
               "figure pointer fields must remain adjacent");
_Static_assert(offsetof(struct figure_rec, map_ref) ==
                   C2_FIGURE_POINTER_OFFSET + 2 * sizeof(void *),
               "figure save tail changed");
_Static_assert(sizeof(struct figure_rec) ==
                   C2_SAVE_FIGURE_SIZE + 2 * (sizeof(void *) - 4),
               "figure runtime record differs beyond its native pointers");

_Static_assert(offsetof(struct arrow_rec, arrow_data_ptr) ==
                   C2_ARROW_POINTER_OFFSET,
               "arrow pointer prefix changed");
_Static_assert(offsetof(struct arrow_rec, grid_x) ==
                   C2_ARROW_POINTER_OFFSET + sizeof(void *),
               "arrow save tail changed");
_Static_assert(sizeof(struct arrow_rec) ==
                   C2_SAVE_ARROW_SIZE + (sizeof(void *) - 4),
               "arrow runtime record differs beyond its native pointer");
