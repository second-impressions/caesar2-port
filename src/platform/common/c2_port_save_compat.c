#include <stdint.h>
#include <string.h>

#include "c2_save_compat.h"

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

static void write_pointer_marker(unsigned char *destination,
                                 const void *pointer)
{
    destination[0] = pointer == NULL ? 0 : 1;
    destination[1] = 0;
    destination[2] = 0;
    destination[3] = 0;
}

static void *read_pointer_marker(const unsigned char *source)
{
    return (source[0] | source[1] | source[2] | source[3]) == 0
        ? NULL : (void *)(uintptr_t)1;
}

void c2_save_pack_figures(unsigned char *destination,
                          const struct figure_rec *source)
{
    size_t i;

    for (i = 0; i < C2_SAVE_FIGURE_COUNT; i++) {
        const unsigned char *record;
        unsigned char *disk_record;

        record = (const unsigned char *)&source[i];
        disk_record = destination + i * C2_SAVE_FIGURE_SIZE;
        memcpy(disk_record, record, C2_FIGURE_POINTER_OFFSET);
        write_pointer_marker(disk_record + C2_FIGURE_POINTER_OFFSET,
                             source[i].arrow_data_ptr);
        write_pointer_marker(disk_record + C2_FIGURE_POINTER_OFFSET + 4,
                             source[i].sprite_data_ptr);
        memcpy(disk_record + C2_FIGURE_DISK_TAIL_OFFSET,
               record + offsetof(struct figure_rec, map_ref),
               C2_SAVE_FIGURE_SIZE - C2_FIGURE_DISK_TAIL_OFFSET);
    }
}

void c2_save_unpack_figures(struct figure_rec *destination,
                            const unsigned char *source)
{
    size_t i;

    for (i = 0; i < C2_SAVE_FIGURE_COUNT; i++) {
        unsigned char *record;
        const unsigned char *disk_record;

        record = (unsigned char *)&destination[i];
        disk_record = source + i * C2_SAVE_FIGURE_SIZE;
        memcpy(record, disk_record, C2_FIGURE_POINTER_OFFSET);
        destination[i].arrow_data_ptr = read_pointer_marker(
            disk_record + C2_FIGURE_POINTER_OFFSET);
        destination[i].sprite_data_ptr = read_pointer_marker(
            disk_record + C2_FIGURE_POINTER_OFFSET + 4);
        memcpy(record + offsetof(struct figure_rec, map_ref),
               disk_record + C2_FIGURE_DISK_TAIL_OFFSET,
               C2_SAVE_FIGURE_SIZE - C2_FIGURE_DISK_TAIL_OFFSET);
    }
}

void c2_save_pack_arrows(unsigned char *destination,
                         const struct arrow_rec *source)
{
    size_t i;

    for (i = 0; i < C2_SAVE_ARROW_COUNT; i++) {
        const unsigned char *record;
        unsigned char *disk_record;

        record = (const unsigned char *)&source[i];
        disk_record = destination + i * C2_SAVE_ARROW_SIZE;
        memcpy(disk_record, record, C2_ARROW_POINTER_OFFSET);
        write_pointer_marker(disk_record + C2_ARROW_POINTER_OFFSET,
                             source[i].arrow_data_ptr);
        memcpy(disk_record + C2_ARROW_DISK_TAIL_OFFSET,
               record + offsetof(struct arrow_rec, grid_x),
               C2_SAVE_ARROW_SIZE - C2_ARROW_DISK_TAIL_OFFSET);
    }
}

void c2_save_unpack_arrows(struct arrow_rec *destination,
                           const unsigned char *source)
{
    size_t i;

    for (i = 0; i < C2_SAVE_ARROW_COUNT; i++) {
        unsigned char *record;
        const unsigned char *disk_record;

        record = (unsigned char *)&destination[i];
        disk_record = source + i * C2_SAVE_ARROW_SIZE;
        memcpy(record, disk_record, C2_ARROW_POINTER_OFFSET);
        destination[i].arrow_data_ptr = read_pointer_marker(
            disk_record + C2_ARROW_POINTER_OFFSET);
        memcpy(record + offsetof(struct arrow_rec, grid_x),
               disk_record + C2_ARROW_DISK_TAIL_OFFSET,
               C2_SAVE_ARROW_SIZE - C2_ARROW_DISK_TAIL_OFFSET);
    }
}
