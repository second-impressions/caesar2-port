#include <stdlib.h>
#include <string.h>

#include <unity/unity.h>
#include <SDL3/SDL.h>

#include "c2_import.h"

#define SECTOR 2048u
#define RAW_SECTOR 2352u

struct memory_source {
    unsigned char *data;
    size_t size;
};

static int memory_read(void *userdata, uint64_t offset, void *buffer,
                       size_t size, size_t *read_out)
{
    struct memory_source *source = userdata;
    if (read_out) *read_out = 0;
    if (offset > source->size) return 0;
    if (size > source->size - (size_t)offset) size = source->size - (size_t)offset;
    memcpy(buffer, source->data + (size_t)offset, size);
    if (read_out) *read_out = size;
    return 1;
}

static void le16(unsigned char *p, unsigned value)
{
    p[0] = (unsigned char)value;
    p[1] = (unsigned char)(value >> 8);
    p[2] = p[1];
    p[3] = p[0];
}

static void le32(unsigned char *p, unsigned value)
{
    p[0] = (unsigned char)value;
    p[1] = (unsigned char)(value >> 8);
    p[2] = (unsigned char)(value >> 16);
    p[3] = (unsigned char)(value >> 24);
    p[4] = p[3];
    p[5] = p[2];
    p[6] = p[1];
    p[7] = p[0];
}

static size_t record(unsigned char *p, unsigned extent, unsigned size,
                     unsigned flags, const unsigned char *name,
                     unsigned name_length)
{
    size_t length = 33u + name_length + (name_length % 2u == 0u ? 1u : 0u);
    memset(p, 0, length);
    p[0] = (unsigned char)length;
    le32(p + 2, extent);
    le32(p + 10, size);
    p[25] = (unsigned char)flags;
    le16(p + 28, 1);
    p[32] = (unsigned char)name_length;
    memcpy(p + 33, name, name_length);
    return length;
}

static unsigned char *make_iso(size_t *size_out)
{
    static const unsigned char dot = 0;
    static const unsigned char dotdot = 1;
    static const unsigned char hd[] = "HD";
    static const unsigned char file[] = "C2.ENG;1";
    unsigned char *iso = calloc(32, SECTOR);
    unsigned char *pvd = iso + 16 * SECTOR;
    unsigned char *term = iso + 17 * SECTOR;
    unsigned char *root = iso + 20 * SECTOR;
    unsigned char *dir = iso + 21 * SECTOR;
    size_t pos;

    pvd[0] = 1;
    memcpy(pvd + 1, "CD001", 5);
    pvd[6] = 1;
    le32(pvd + 80, 32);
    le16(pvd + 128, SECTOR);
    record(pvd + 156, 20, SECTOR, 2, &dot, 1);
    term[0] = 255;
    memcpy(term + 1, "CD001", 5);
    term[6] = 1;

    pos = 0;
    pos += record(root + pos, 20, SECTOR, 2, &dot, 1);
    pos += record(root + pos, 20, SECTOR, 2, &dotdot, 1);
    record(root + pos, 21, SECTOR, 2, hd, 2);

    pos = 0;
    pos += record(dir + pos, 21, SECTOR, 2, &dot, 1);
    pos += record(dir + pos, 20, SECTOR, 2, &dotdot, 1);
    record(dir + pos, 22, 4, 0, file, 8);
    memcpy(iso + 22 * SECTOR, "text", 4);
    *size_out = 32 * SECTOR;
    return iso;
}

static void test_iso_catalog_reads_nested_file(void)
{
    struct memory_source memory;
    struct c2_source_reader source;
    struct c2_iso_catalog catalog;
    const struct c2_iso_entry *entry;
    char error[128];
    char value[5] = {0};
    size_t read;

    memory.data = make_iso(&memory.size);
    source.userdata = &memory;
    source.size = memory.size;
    source.read_at = memory_read;
    TEST_ASSERT_TRUE(c2_iso_catalog_open(&source, &catalog, error, sizeof(error)));
    TEST_ASSERT_EQUAL_size_t(1, catalog.count);
    entry = c2_iso_catalog_find(&catalog, "hd\\c2.eng");
    TEST_ASSERT_NOT_NULL(entry);
    TEST_ASSERT_EQUAL_UINT64(4, entry->size);
    TEST_ASSERT_TRUE(c2_iso_entry_read(&source, entry, 0, value, 4, &read));
    TEST_ASSERT_EQUAL_size_t(4, read);
    TEST_ASSERT_EQUAL_STRING("text", value);
    c2_iso_catalog_close(&catalog);
    free(memory.data);
}

static void test_cue_accepts_observed_modes(void)
{
    char name[64];
    char error[128];
    enum c2_cd_sector_mode mode;

    TEST_ASSERT_TRUE(c2_cue_parse_single_data_track(
        "FILE \"disc.bin\" BINARY\n TRACK 01 MODE1/2352\n  INDEX 01 00:00:00\n",
        name, sizeof(name), &mode, error, sizeof(error)));
    TEST_ASSERT_EQUAL_STRING("disc.bin", name);
    TEST_ASSERT_EQUAL(C2_CD_MODE1_2352, mode);
    TEST_ASSERT_TRUE(c2_cue_parse_single_data_track(
        "FILE \"disc.bin\" BINARY\r\n TRACK 01 MODE2/2352\r\n  INDEX 01 00:00:00\r\n",
        name, sizeof(name), &mode, error, sizeof(error)));
    TEST_ASSERT_EQUAL(C2_CD_MODE2_2352, mode);
    TEST_ASSERT_FALSE(c2_cue_parse_single_data_track(
        "FILE \"disc.bin\" BINARY\n TRACK 01 AUDIO\n  INDEX 01 00:00:00\n",
        name, sizeof(name), &mode, error, sizeof(error)));
}

static void test_zip_extracts_one_outer_directory(void)
{
    static const unsigned char zip_data[] = {
        0x50,0x4b,0x03,0x04,0x14,0x00,0x00,0x00,0x08,0x00,0x1a,0x4e,0x17,0x5d,0xc7,0xa7,
        0x8b,0x3b,0x06,0x00,0x00,0x00,0x04,0x00,0x00,0x00,0x0e,0x00,0x00,0x00,0x43,0x41,
        0x45,0x53,0x41,0x52,0x32,0x2f,0x43,0x32,0x2e,0x45,0x4e,0x47,0x2b,0x49,0xad,0x28,
        0x01,0x00,0x50,0x4b,0x01,0x02,0x14,0x03,0x14,0x00,0x00,0x00,0x08,0x00,0x1a,0x4e,
        0x17,0x5d,0xc7,0xa7,0x8b,0x3b,0x06,0x00,0x00,0x00,0x04,0x00,0x00,0x00,0x0e,0x00,
        0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x80,0x01,0x00,0x00,0x00,0x00,
        0x43,0x41,0x45,0x53,0x41,0x52,0x32,0x2f,0x43,0x32,0x2e,0x45,0x4e,0x47,0x50,0x4b,
        0x05,0x06,0x00,0x00,0x00,0x00,0x01,0x00,0x01,0x00,0x3c,0x00,0x00,0x00,0x32,0x00,
        0x00,0x00,0x00,0x00
    };
    FILE *file;
    char error[128];
    char text[5] = {0};

    remove("c2-import-test.zip");
    remove("c2-import-output/C2.ENG");
    remove("c2-import-output");
    file = fopen("c2-import-test.zip", "wb");
    TEST_ASSERT_NOT_NULL(file);
    TEST_ASSERT_EQUAL_size_t(sizeof(zip_data), fwrite(zip_data, 1, sizeof(zip_data), file));
    TEST_ASSERT_EQUAL_INT(0, fclose(file));
    TEST_ASSERT_TRUE_MESSAGE(c2_zip_extract("c2-import-test.zip", "c2-import-output", error, sizeof(error)), error);
    file = fopen("c2-import-output/C2.ENG", "rb");
    TEST_ASSERT_NOT_NULL(file);
    TEST_ASSERT_EQUAL_size_t(4, fread(text, 1, 4, file));
    fclose(file);
    TEST_ASSERT_EQUAL_STRING("text", text);
    remove("c2-import-output/C2.ENG");
    remove("c2-import-output");
    remove("c2-import-test.zip");
}

static void test_pack_activates_default_profile(void)
{
    FILE *file;
    char active[256];
    char error[128];
    char text[5] = {0};
    remove("c2-pack-test/ACTIVE-en/.c2-object-map");
    remove("c2-pack-test/ACTIVE-en");
    remove("c2-pack-test/OBJECTS/00000001.BIN");
    remove("c2-pack-test/OBJECTS");
    remove("c2-pack-test/C2PACK.IDX");
    remove("c2-pack-test");
    TEST_ASSERT_TRUE(SDL_CreateDirectory("c2-pack-test/OBJECTS"));
    file = fopen("c2-pack-test/OBJECTS/00000001.BIN", "wb");
    TEST_ASSERT_NOT_NULL(file); fwrite("text", 1, 4, file); fclose(file);
    file = fopen("c2-pack-test/C2PACK.IDX", "wb");
    TEST_ASSERT_NOT_NULL(file);
    fputs("C2PACK1\nDEFAULT_LANGUAGE\ten\nCOMPONENT\tcore/default\n"
          "FILE\tC2.ENG\t00000001.BIN\nPROFILE\ten\tcore/default\nEND\n", file);
    fclose(file);
    TEST_ASSERT_TRUE_MESSAGE(c2_pack_activate("c2-pack-test", NULL,
                                               active, sizeof(active),
                                               error, sizeof(error)), error);
    file = fopen("c2-pack-test/ACTIVE-en/.c2-object-map", "rb");
    TEST_ASSERT_NOT_NULL(file); fread(text, 1, 4, file); fclose(file);
    TEST_ASSERT_EQUAL_MEMORY("C2.E", text, 4);
    remove("c2-pack-test/ACTIVE-en/.c2-object-map");
    remove("c2-pack-test/ACTIVE-en");
    remove("c2-pack-test/OBJECTS/00000001.BIN");
    remove("c2-pack-test/OBJECTS");
    remove("c2-pack-test/C2PACK.IDX");
    remove("c2-pack-test");
}

static void test_raw_sector_adapter_feeds_iso_reader(void)
{
    static const unsigned char sync[12] = {
        0x00, 0xff, 0xff, 0xff, 0xff, 0xff,
        0xff, 0xff, 0xff, 0xff, 0xff, 0x00
    };
    struct memory_source iso_memory;
    struct memory_source raw_memory;
    struct c2_source_reader raw_source;
    struct c2_source_reader logical_source;
    struct c2_raw_cd_reader adapter;
    struct c2_iso_catalog catalog;
    char error[128];
    size_t sector;

    iso_memory.data = make_iso(&iso_memory.size);
    raw_memory.size = (iso_memory.size / SECTOR) * RAW_SECTOR;
    raw_memory.data = calloc(1, raw_memory.size);
    for (sector = 0; sector < iso_memory.size / SECTOR; sector++) {
        unsigned char *raw = raw_memory.data + sector * RAW_SECTOR;
        memcpy(raw, sync, sizeof(sync));
        raw[15] = 2;
        memcpy(raw + 24, iso_memory.data + sector * SECTOR, SECTOR);
    }
    raw_source.userdata = &raw_memory;
    raw_source.size = raw_memory.size;
    raw_source.read_at = memory_read;
    TEST_ASSERT_TRUE(c2_raw_cd_reader_init(&adapter, &raw_source,
                                            C2_CD_MODE2_2352,
                                            error, sizeof(error)));
    c2_raw_cd_source(&adapter, &logical_source);
    TEST_ASSERT_TRUE(c2_iso_catalog_open(&logical_source, &catalog,
                                         error, sizeof(error)));
    TEST_ASSERT_NOT_NULL(c2_iso_catalog_find(&catalog, "HD/C2.ENG"));
    c2_iso_catalog_close(&catalog);
    free(raw_memory.data);
    free(iso_memory.data);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_iso_catalog_reads_nested_file);
    RUN_TEST(test_cue_accepts_observed_modes);
    RUN_TEST(test_zip_extracts_one_outer_directory);
    RUN_TEST(test_pack_activates_default_profile);
    RUN_TEST(test_raw_sector_adapter_feeds_iso_reader);
    return UNITY_END();
}
