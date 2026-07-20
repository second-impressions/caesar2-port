#include <assert.h>
#include <string.h>

#include "c2_asm_routines.h"

static int callback_count;

static void count_callback(void)
{
    callback_count++;
}

static void test_call_address(void)
{
    callback_count = 0;
    call_address(count_callback);
    assert(callback_count == 1);
}

static void test_copy(void)
{
    unsigned char source[64];
    unsigned char destination[64] = { 0 };
    int i;

    for (i = 0; i < 64; i++) {
        source[i] = (unsigned char)(i * 3 + 1);
    }
    copy(source, destination, 64);
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
    test_call_address();
    test_copy();
    test_repeated_run();
    test_literal_run();
    test_mixed_round_trip();
    return 0;
}
