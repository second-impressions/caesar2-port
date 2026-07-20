#include <stddef.h>

#include "c2_asm_routines.h"

static void write_u16(unsigned char *destination, unsigned int value)
{
    destination[0] = (unsigned char)value;
    destination[1] = (unsigned char)(value >> 8);
}

static void write_u32(unsigned char *destination, unsigned int value)
{
    destination[0] = (unsigned char)value;
    destination[1] = (unsigned char)(value >> 8);
    destination[2] = (unsigned char)(value >> 16);
    destination[3] = (unsigned char)(value >> 24);
}

static unsigned int read_u16(const unsigned char *source)
{
    return (unsigned int)source[0] | ((unsigned int)source[1] << 8);
}

static unsigned int read_u32(const unsigned char *source)
{
    return (unsigned int)source[0] |
           ((unsigned int)source[1] << 8) |
           ((unsigned int)source[2] << 16) |
           ((unsigned int)source[3] << 24);
}

void copy(unsigned char *source, unsigned char *destination, int byte_count)
{
    int i;

    for (i = 0; i < byte_count; i++) {
        destination[i] = source[i];
    }
}

int compress(unsigned char *source, unsigned char *destination, int byte_count)
{
    int source_offset;
    int destination_offset;

    write_u32(destination + 4, (unsigned int)byte_count);
    source_offset = 0;
    destination_offset = 8;
    while (source_offset < byte_count) {
        int run_length;

        run_length = 1;
        if (source_offset + 2 < byte_count &&
            source[source_offset] == source[source_offset + 1] &&
            source[source_offset] == source[source_offset + 2]) {
            while (run_length < 0x7d00 &&
                   source_offset + run_length < byte_count &&
                   source[source_offset + run_length] == source[source_offset]) {
                run_length++;
            }
            write_u16(destination + destination_offset,
                      (unsigned int)(run_length - 1));
            destination[destination_offset + 2] = source[source_offset];
            destination_offset += 3;
        } else {
            while (run_length < 0x7d00 &&
                   source_offset + run_length < byte_count) {
                int next_offset;

                next_offset = source_offset + run_length;
                if (next_offset + 2 < byte_count &&
                    source[next_offset] == source[next_offset + 1] &&
                    source[next_offset] == source[next_offset + 2]) {
                    break;
                }
                run_length++;
            }
            write_u16(destination + destination_offset,
                      (unsigned int)(run_length - 1) | 0x8000U);
            copy(source + source_offset, destination + destination_offset + 2,
                 run_length);
            destination_offset += run_length + 2;
        }
        source_offset += run_length;
    }
    write_u32(destination, (unsigned int)destination_offset);
    return destination_offset;
}

int depress(unsigned char *destination, unsigned char *source)
{
    unsigned int remaining;
    int source_offset;
    int destination_offset;

    remaining = read_u32(source + 4);
    source_offset = 8;
    destination_offset = 0;
    while (remaining != 0) {
        unsigned int control;
        unsigned int run_length;

        control = read_u16(source + source_offset);
        run_length = (control & 0x7fffU) + 1;
        source_offset += 2;
        if ((control & 0x8000U) != 0) {
            copy(source + source_offset, destination + destination_offset,
                 (int)run_length);
            source_offset += (int)run_length;
        } else {
            unsigned char value;
            unsigned int i;

            value = source[source_offset++];
            for (i = 0; i < run_length; i++) {
                destination[destination_offset + (int)i] = value;
            }
        }
        destination_offset += (int)run_length;
        remaining -= run_length;
    }
    return destination_offset;
}
