#include <assert.h>
#include <string.h>

#include "c2_asm_routines.h"

static void test_copy(void)
{
    unsigned char source[] = { 1, 2, 3, 4, 5 };
    unsigned char destination[5] = { 0 };

    copy(source, destination, 5);
    assert(memcmp(source, destination, sizeof(source)) == 0);
}

static void test_repeated_run(void)
{
    unsigned char source[] = { 'A', 'A', 'A', 'A', 'A' };
    unsigned char packed[32] = { 0 };
    unsigned char unpacked[sizeof(source)] = { 0 };
    unsigned char expected[] = {
        11, 0, 0, 0, 5, 0, 0, 0, 4, 0, 'A'
    };

    assert(compress(source, packed, sizeof(source)) == sizeof(expected));
    assert(memcmp(packed, expected, sizeof(expected)) == 0);
    assert(depress(unpacked, packed) == sizeof(source));
    assert(memcmp(unpacked, source, sizeof(source)) == 0);
}

static void test_literal_run(void)
{
    unsigned char source[] = { 1, 2, 3, 4 };
    unsigned char packed[32] = { 0 };
    unsigned char unpacked[sizeof(source)] = { 0 };
    unsigned char expected[] = {
        14, 0, 0, 0, 4, 0, 0, 0, 3, 0x80, 1, 2, 3, 4
    };

    assert(compress(source, packed, sizeof(source)) == sizeof(expected));
    assert(memcmp(packed, expected, sizeof(expected)) == 0);
    assert(depress(unpacked, packed) == sizeof(source));
    assert(memcmp(unpacked, source, sizeof(source)) == 0);
}

static void test_mixed_round_trip(void)
{
    unsigned char source[] = {
        1, 2, 3, 4, 7, 7, 7, 7, 9, 10, 11, 12, 12, 12
    };
    unsigned char packed[64] = { 0 };
    unsigned char unpacked[sizeof(source)] = { 0 };

    assert(compress(source, packed, sizeof(source)) > 8);
    assert(depress(unpacked, packed) == sizeof(source));
    assert(memcmp(unpacked, source, sizeof(source)) == 0);
}

int main(void)
{
    test_copy();
    test_repeated_run();
    test_literal_run();
    test_mixed_round_trip();
    return 0;
}
