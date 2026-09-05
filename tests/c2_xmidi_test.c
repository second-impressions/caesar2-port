/*
 * Tests for the XMIDI sequencer and the Miles OPL3 driver reimplementation.
 *
 * The driver tables are checked byte-for-byte against the shipped OPL3.MDI
 * image and the sequencer against the shipped scores when C2_TEST_DATA_DIR
 * points at a Caesar II installation (or extracted disc); without assets the
 * synthetic tests still run.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <unity/unity.h>

#include "xmidi/miles_opl.h"
#include "xmidi/xmidi.h"

/* ------------------------------------------------------------------------ */
/* Helpers                                                                  */

static const char *asset_root(void)
{
    const char *root;

    root = getenv("C2_TEST_DATA_DIR");
    return root != NULL && *root != 0 ? root : NULL;
}

static unsigned char *try_read(const char *root, const char *sub,
                               const char *name, size_t *size)
{
    char path[1024];
    FILE *file;
    unsigned char *data;
    long length;

    if (sub) snprintf(path, sizeof(path), "%s/%s/%s", root, sub, name);
    else snprintf(path, sizeof(path), "%s/%s", root, name);
    file = fopen(path, "rb");
    if (file == NULL) return NULL;
    fseek(file, 0, SEEK_END);
    length = ftell(file);
    fseek(file, 0, SEEK_SET);
    data = malloc((size_t)length + 1);
    TEST_ASSERT_NOT_NULL(data);
    TEST_ASSERT_EQUAL_size_t((size_t)length, fread(data, 1, (size_t)length, file));
    fclose(file);
    *size = (size_t)length;
    return data;
}

/* Assets live flat in an installation and below HD/ and XMI/ on the disc. */
static unsigned char *read_asset(const char *name, size_t *size)
{
    static const char *subs[] = {NULL, "HD", "XMI", "hd", "xmi"};
    const char *root;
    unsigned char *data;
    size_t i;

    root = asset_root();
    if (root == NULL) TEST_IGNORE_MESSAGE("no Caesar II assets");
    for (i = 0; i < sizeof(subs) / sizeof(subs[0]); i++) {
        data = try_read(root, subs[i], name, size);
        if (data != NULL) return data;
    }
    return NULL;
}

static unsigned char *require_asset(const char *name, size_t *size)
{
    unsigned char *data;

    data = read_asset(name, size);
    if (data == NULL) {
        char message[256];
        snprintf(message, sizeof(message), "asset %s not found", name);
        TEST_IGNORE_MESSAGE(message);
    }
    return data;
}

struct midi_log {
    unsigned status[4096];
    unsigned data1[4096];
    unsigned data2[4096];
    int count;
    int note_ons;
    int note_offs;
};

static void log_midi(void *user, unsigned status, unsigned data1,
                     unsigned data2)
{
    struct midi_log *log;

    log = user;
    if (log->count < 4096) {
        log->status[log->count] = status;
        log->data1[log->count] = data1;
        log->data2[log->count] = data2;
        log->count++;
    }
    if ((status & 0xf0) == 0x90 && data2 != 0) log->note_ons++;
    if ((status & 0xf0) == 0x80 || ((status & 0xf0) == 0x90 && data2 == 0)) {
        log->note_offs++;
    }
}

static int log_find(const struct midi_log *log, unsigned status,
                    unsigned data1)
{
    int i;

    for (i = 0; i < log->count; i++) {
        if (log->status[i] == status && log->data1[i] == data1) return i;
    }
    return -1;
}

static int log_last(const struct midi_log *log, unsigned status,
                    unsigned data1)
{
    int i;

    for (i = log->count - 1; i >= 0; i--) {
        if (log->status[i] == status && log->data1[i] == data1) return i;
    }
    return -1;
}

struct reg_log {
    unsigned reg[8192];
    unsigned value[8192];
    int count;
};

static void log_reg(void *user, unsigned reg, unsigned value)
{
    struct reg_log *log;

    log = user;
    if (log->count < 8192) {
        log->reg[log->count] = reg;
        log->value[log->count] = value;
        log->count++;
    }
}

static int reg_last(const struct reg_log *log, unsigned reg)
{
    int i;

    for (i = log->count - 1; i >= 0; i--) {
        if (log->reg[i] == reg) return (int)log->value[i];
    }
    return -1;
}

/* ------------------------------------------------------------------------ */
/* Driver tables against the shipped driver image                           */

static void expect_bytes(const unsigned char *image, size_t size,
                         size_t offset, const void *table, size_t length,
                         const char *name)
{
    char message[128];

    snprintf(message, sizeof(message), "%s @0x%04zx", name, offset);
    TEST_ASSERT_TRUE_MESSAGE(offset + length <= size, message);
    TEST_ASSERT_EQUAL_MEMORY_MESSAGE(image + offset, table, length, message);
}

static void test_driver_tables_match_shipped_opl3_driver(void)
{
    unsigned char *mdi;
    size_t size;
    unsigned char fnum[12 * 16 * 2];
    int row;
    int col;

    mdi = require_asset("OPL3.MDI", &size);
    TEST_ASSERT_EQUAL_MEMORY("AIL3MDI\x1a", mdi, 8);
    for (row = 0; row < 12; row++) {
        for (col = 0; col < 16; col++) {
            fnum[(row * 16 + col) * 2] = miles_opl_fnum_table[row][col] & 0xff;
            fnum[(row * 16 + col) * 2 + 1] = miles_opl_fnum_table[row][col] >> 8;
        }
    }
    expect_bytes(mdi, size, 0x07da, fnum, sizeof(fnum), "fnum");
    expect_bytes(mdi, size, 0x095a, miles_opl_block_table, 96, "block");
    expect_bytes(mdi, size, 0x09ba, miles_opl_row_table, 96, "row");
    expect_bytes(mdi, size, 0x0a1a, miles_opl_init_registers[0], 0xf5, "init0");
    expect_bytes(mdi, size, 0x0b0f, miles_opl_init_registers[1], 0xf5, "init1");
    expect_bytes(mdi, size, 0x0c04, miles_opl_velocity_table, 16, "velocity");
    expect_bytes(mdi, size, 0x0c14, miles_opl_op1_of_channel, 18, "op1");
    expect_bytes(mdi, size, 0x0c26, miles_opl_op2_of_channel, 18, "op2");
    expect_bytes(mdi, size, 0x0c38, miles_opl_op_register, 36, "op reg");
    expect_bytes(mdi, size, 0x0c5c, miles_opl_op_bank, 36, "op bank");
    expect_bytes(mdi, size, 0x0c80, miles_opl_channel_register, 18, "ch reg");
    expect_bytes(mdi, size, 0x0c92, miles_opl_channel_bank, 18, "ch bank");
    expect_bytes(mdi, size, 0x0ca4, miles_opl_channel_4op_capable, 18, "4op");
    expect_bytes(mdi, size, 0x0cb6, miles_opl_channel_partner, 18, "partner");
    expect_bytes(mdi, size, 0x0cc8, miles_opl_partner_op1, 18, "partner op1");
    expect_bytes(mdi, size, 0x0cda, miles_opl_partner_op2, 18, "partner op2");
    expect_bytes(mdi, size, 0x0cec, miles_opl_4op_enable_mask, 18, "4op mask");
    expect_bytes(mdi, size, 0x0cfe, miles_opl_4op_channels, 6, "4op channels");
    expect_bytes(mdi, size, 0x0d04, miles_opl_4op_volume_ops_a, 4, "vol ops a");
    expect_bytes(mdi, size, 0x0d08, miles_opl_4op_volume_ops_b, 4, "vol ops b");
    /* The dispatcher and the register writer sit where the transliteration
     * expects them: the MIDI_XMIT entry parses the message buffer at 0x370. */
    TEST_ASSERT_EQUAL_HEX8(0x3d, mdi[0x132]);
    TEST_ASSERT_EQUAL_HEX16(0x3e3e, mdi[0x11c] | (mdi[0x11d] << 8));
    free(mdi);
}

static const unsigned char *find_bytes(const unsigned char *hay, size_t hay_size,
                                       const void *needle, size_t needle_size)
{
    size_t i;

    if (needle_size > hay_size) return NULL;
    for (i = 0; i + needle_size <= hay_size; i++) {
        if (memcmp(hay + i, needle, needle_size) == 0) return hay + i;
    }
    return NULL;
}

/* Every Miles FM driver on the disc (Ad Lib, Ad Lib Gold, Sound Blaster
 * family, Pro Audio Spectrum) carries the same pitch and velocity tables. */
static void test_sibling_fm_drivers_share_the_tables(void)
{
    static const char *drivers[] = {
        "ADLIB.MDI", "ADLIBG.MDI", "SBLASTER.MDI", "SBPRO1.MDI",
        "SBPRO2.MDI", "PAS.MDI", "PASPLUS.MDI", "OPL3.MDI"
    };
    unsigned char *mdi;
    size_t size;
    size_t i;
    int checked;
    unsigned char fnum_row0[32];
    int col;

    for (col = 0; col < 16; col++) {
        fnum_row0[col * 2] = miles_opl_fnum_table[0][col] & 0xff;
        fnum_row0[col * 2 + 1] = miles_opl_fnum_table[0][col] >> 8;
    }
    checked = 0;
    for (i = 0; i < sizeof(drivers) / sizeof(drivers[0]); i++) {
        mdi = read_asset(drivers[i], &size);
        if (mdi == NULL) continue;
        TEST_ASSERT_NOT_NULL_MESSAGE(
            find_bytes(mdi, size, miles_opl_velocity_table, 16), drivers[i]);
        TEST_ASSERT_NOT_NULL_MESSAGE(
            find_bytes(mdi, size, fnum_row0, sizeof(fnum_row0)), drivers[i]);
        TEST_ASSERT_NOT_NULL_MESSAGE(
            find_bytes(mdi, size, miles_opl_block_table, 96), drivers[i]);
        free(mdi);
        checked++;
    }
    TEST_ASSERT_GREATER_THAN_INT(0, checked);
}

/* ------------------------------------------------------------------------ */
/* GTL banks                                                                */

static void test_gtl_bank_loads_every_timbre(void)
{
    struct miles_opl *drv;
    unsigned char *bank;
    size_t size;
    const unsigned char *timbre;
    static const unsigned char patch0[] = {
        0x06, 0xa4, 0xf3, 0xf4, 0x00, 0x06, 0x03, 0x6d, 0xe2, 0xe4, 0x00,
        0x01, 0x53, 0xe1, 0xd4, 0x00, 0x00, 0x11, 0x02, 0xe1, 0xe5, 0x00
    };
    static const unsigned char patch1[] = {
        0x41, 0x9d, 0xf2, 0x53, 0x00, 0x06, 0x13, 0x00, 0xf2, 0xf3, 0x00
    };

    bank = require_asset("CAESAR.OPL", &size);
    drv = miles_opl_create(44100);
    TEST_ASSERT_NOT_NULL(drv);
    TEST_ASSERT_GREATER_THAN_INT(100, miles_opl_load_bank(drv, bank, size));
    timbre = miles_opl_find_timbre(drv, 0, 0);
    TEST_ASSERT_NOT_NULL(timbre);
    TEST_ASSERT_EQUAL_INT(25, timbre[0] | (timbre[1] << 8));
    TEST_ASSERT_EQUAL_INT(0, timbre[2]);
    TEST_ASSERT_EQUAL_MEMORY(patch0, timbre + 3, sizeof(patch0));
    timbre = miles_opl_find_timbre(drv, 0, 1);
    TEST_ASSERT_NOT_NULL(timbre);
    TEST_ASSERT_EQUAL_INT(14, timbre[0]);
    TEST_ASSERT_EQUAL_MEMORY(patch1, timbre + 3, sizeof(patch1));
    TEST_ASSERT_NULL(miles_opl_find_timbre(drv, 5, 0));
    miles_opl_destroy(drv);
    free(bank);
}

static void test_ad_fallback_bank_loads(void)
{
    struct miles_opl *drv;
    unsigned char *bank;
    size_t size;

    bank = require_asset("CAESAR.AD", &size);
    drv = miles_opl_create(44100);
    TEST_ASSERT_GREATER_THAN_INT(100, miles_opl_load_bank(drv, bank, size));
    TEST_ASSERT_NOT_NULL(miles_opl_find_timbre(drv, 0, 0));
    miles_opl_destroy(drv);
    free(bank);
}

static void test_bank_loader_rejects_garbage(void)
{
    struct miles_opl *drv;
    unsigned char junk[64];

    memset(junk, 0x11, sizeof(junk));
    drv = miles_opl_create(44100);
    TEST_ASSERT_EQUAL_INT(0, miles_opl_load_bank(drv, junk, sizeof(junk)));
    TEST_ASSERT_EQUAL_INT(0, miles_opl_load_bank(drv, junk, 3));
    miles_opl_destroy(drv);
}

/* ------------------------------------------------------------------------ */
/* XMIDI file layout                                                        */

static int city_branch_expected(unsigned branch)
{
    return branch <= 6 || (branch >= 10 && branch <= 16) ||
           (branch >= 20 && branch <= 26) || (branch >= 30 && branch <= 36) ||
           (branch >= 40 && branch <= 53);
}

static void check_branches(const char *name, int (*expected)(unsigned),
                           int count, int timbres)
{
    struct xmi_form form;
    unsigned char *data;
    size_t size;
    unsigned id;
    size_t offset;
    unsigned mask[256];
    int i;

    data = require_asset(name, &size);
    TEST_ASSERT_EQUAL_size_t(size, xmi_image_size(data, size));
    TEST_ASSERT_EQUAL_size_t(size, xmi_image_size(data, size + 100));
    TEST_ASSERT_EQUAL_size_t(0, xmi_image_size(data, size - 1));
    TEST_ASSERT_TRUE(xmi_find_form(data, size, 0, &form));
    TEST_ASSERT_FALSE(xmi_find_form(data, size, 1, &form));
    TEST_ASSERT_TRUE(xmi_find_form(data, size, 0, &form));
    TEST_ASSERT_EQUAL_INT(count, xmi_form_branch_count(&form));
    TEST_ASSERT_EQUAL_INT(timbres, xmi_form_timbre_count(&form));
    memset(mask, 0, sizeof(mask));
    for (i = 0; i < count; i++) {
        TEST_ASSERT_TRUE(xmi_form_branch(&form, i, &id, &offset));
        TEST_ASSERT_TRUE(id < 256);
        TEST_ASSERT_TRUE(offset < form.evnt_size);
        /* Every branch target directly follows its own branch-index marker
         * (controller 120 with the branch id). */
        TEST_ASSERT_TRUE(offset >= 3);
        TEST_ASSERT_EQUAL_HEX8(0xb0, form.evnt[8 + offset - 3] & 0xf0);
        TEST_ASSERT_EQUAL_INT(120, form.evnt[8 + offset - 2]);
        TEST_ASSERT_EQUAL_UINT(id, form.evnt[8 + offset - 1]);
        mask[id] = 1;
    }
    for (i = 0; i < 256; i++) {
        TEST_ASSERT_EQUAL_INT_MESSAGE(expected((unsigned)i), (int)mask[i], name);
    }
    free(data);
}

static int battle_branch_expected(unsigned branch)
{
    return branch <= 53;
}

static int no_branch_expected(unsigned branch)
{
    (void)branch;
    return 0;
}

static void test_official_scores_expose_their_branches(void)
{
    check_branches("CITYPROV.XMI", city_branch_expected, 42, 5);
    check_branches("BATEST2.XMI", battle_branch_expected, 54, 5);
    check_branches("FORUM1.XMI", no_branch_expected, 0, 3);
    check_branches("FORUM3.XMI", no_branch_expected, 0, 2);
}

static void test_score_timbres_exist_in_the_bank(void)
{
    static const char *scores[] = {
        "CITYPROV.XMI", "BATEST2.XMI", "FORUM1.XMI", "FORUM2.XMI", "FORUM3.XMI"
    };
    struct miles_opl *drv;
    struct xmi_form form;
    unsigned char *bank;
    unsigned char *data;
    size_t size;
    size_t i;
    int t;
    unsigned patch;
    unsigned bank_id;

    bank = require_asset("CAESAR.OPL", &size);
    drv = miles_opl_create(44100);
    TEST_ASSERT_GREATER_THAN_INT(0, miles_opl_load_bank(drv, bank, size));
    for (i = 0; i < sizeof(scores) / sizeof(scores[0]); i++) {
        data = require_asset(scores[i], &size);
        TEST_ASSERT_TRUE(xmi_find_form(data, size, 0, &form));
        for (t = 0; t < xmi_form_timbre_count(&form); t++) {
            TEST_ASSERT_TRUE(xmi_form_timbre(&form, t, &patch, &bank_id));
            TEST_ASSERT_NOT_NULL_MESSAGE(
                miles_opl_find_timbre(drv, (int)bank_id, (int)patch), scores[i]);
        }
        free(data);
    }
    miles_opl_destroy(drv);
    free(bank);
}

/* A hand-built XMIDI image: FORM XDIR + CAT with one FORM XMID. */
static size_t build_xmi(unsigned char *out, const unsigned char *events,
                        size_t events_size, const unsigned char *rbrn,
                        size_t rbrn_size)
{
    unsigned char *p;
    size_t form_len;
    size_t cat_len;
    size_t evnt_len;

    evnt_len = events_size + (events_size & 1);
    form_len = 4 + 8 + evnt_len + (rbrn_size ? 8 + rbrn_size : 0);
    cat_len = 4 + 8 + form_len;
    p = out;
    memcpy(p, "FORM\0\0\0\x0eXDIRINFO\0\0\0\x02\x01\0", 22);
    p += 22;
    memcpy(p, "CAT ", 4);
    p[4] = (unsigned char)(cat_len >> 24); p[5] = (unsigned char)(cat_len >> 16);
    p[6] = (unsigned char)(cat_len >> 8); p[7] = (unsigned char)cat_len;
    memcpy(p + 8, "XMID", 4);
    p += 12;
    memcpy(p, "FORM", 4);
    p[4] = (unsigned char)(form_len >> 24); p[5] = (unsigned char)(form_len >> 16);
    p[6] = (unsigned char)(form_len >> 8); p[7] = (unsigned char)form_len;
    memcpy(p + 8, "XMID", 4);
    p += 12;
    if (rbrn_size) {
        memcpy(p, "RBRN", 4);
        p[4] = 0; p[5] = 0; p[6] = (unsigned char)(rbrn_size >> 8);
        p[7] = (unsigned char)rbrn_size;
        memcpy(p + 8, rbrn, rbrn_size);
        p += 8 + rbrn_size;
    }
    memcpy(p, "EVNT", 4);
    p[4] = 0; p[5] = 0; p[6] = (unsigned char)(evnt_len >> 8);
    p[7] = (unsigned char)evnt_len;
    memcpy(p + 8, events, events_size);
    if (events_size & 1) p[8 + events_size] = 0;
    p += 8 + evnt_len;
    return (size_t)(p - out);
}

static void test_synthetic_image_layout(void)
{
    static const unsigned char events[] = {
        0xc0, 0x05,             /* program 5 */
        0x90, 60, 100, 0x0a,    /* note 60 for 10 ticks */
        0x05,                   /* delay 5 */
        0xb0, 120, 0x01,        /* branch marker 1 */
        0x90, 62, 100, 0x04,
        0x7f, 0x02,             /* delay 127 + 2 */
        0xff, 0x2f, 0x00
    };
    static const unsigned char rbrn[] = {
        0x01, 0x00, 0x01, 0x00, 0x07, 0x00, 0x00, 0x00
    };
    unsigned char image[256];
    struct xmi_form form;
    size_t size;
    unsigned id;
    size_t offset;

    size = build_xmi(image, events, sizeof(events), rbrn, sizeof(rbrn));
    TEST_ASSERT_EQUAL_size_t(size, xmi_image_size(image, sizeof(image)));
    TEST_ASSERT_TRUE(xmi_find_form(image, size, 0, &form));
    TEST_ASSERT_EQUAL_size_t(sizeof(events) + 1, form.evnt_size);
    TEST_ASSERT_EQUAL_INT(1, xmi_form_branch_count(&form));
    TEST_ASSERT_TRUE(xmi_form_branch(&form, 0, &id, &offset));
    TEST_ASSERT_EQUAL_UINT(1, id);
    TEST_ASSERT_EQUAL_size_t(7, offset);
    TEST_ASSERT_FALSE(xmi_find_form(image, size, 1, &form));
    TEST_ASSERT_FALSE(xmi_find_form("RIFF....", 8, 0, &form));
}

/* ------------------------------------------------------------------------ */
/* Sequencer                                                                */

static void test_driver_reset_sends_the_ail_channel_preset(void)
{
    struct midi_log log;
    struct xmi_driver *drv;
    static const unsigned expect[15][3] = {
        {0xb0, 114, 0}, {0xc0, 0, 0}, {0xe0, 0, 0x40}, {0xb0, 112, 0},
        {0xb0, 1, 0}, {0xb0, 7, 127}, {0xb0, 10, 64}, {0xb0, 11, 127},
        {0xb0, 64, 0}, {0xb0, 91, 40}, {0xb0, 93, 0}, {0xb0, 100, 0},
        {0xb0, 101, 0}, {0xb0, 38, 0}, {0xb0, 6, 2}
    };
    int i;

    memset(&log, 0, sizeof(log));
    drv = xmi_driver_create(log_midi, &log);
    xmi_driver_reset(drv);
    TEST_ASSERT_EQUAL_INT(15 * 16, log.count);
    for (i = 0; i < 15; i++) {
        TEST_ASSERT_EQUAL_HEX8(expect[i][0], log.status[i]);
        TEST_ASSERT_EQUAL_UINT(expect[i][1], log.data1[i]);
        TEST_ASSERT_EQUAL_UINT(expect[i][2], log.data2[i]);
        TEST_ASSERT_EQUAL_HEX8(expect[i][0] | 0x0f, log.status[15 * 15 + i]);
    }
    xmi_driver_destroy(drv);
}

static void test_synthetic_sequence_timing_notes_and_branch(void)
{
    static const unsigned char events[] = {
        0xc0, 0x05,
        0x90, 60, 100, 0x0a,
        0x05,
        0xb0, 120, 0x01,
        0x90, 62, 100, 0x04,
        0x7f, 0x02,
        0xff, 0x2f, 0x00
    };
    static const unsigned char rbrn[] = {
        0x01, 0x00, 0x01, 0x00, 0x07, 0x00, 0x00, 0x00
    };
    unsigned char image[256];
    struct midi_log log;
    struct xmi_driver *drv;
    struct xmi_sequence *seq;
    size_t size;
    int tick;

    size = build_xmi(image, events, sizeof(events), rbrn, sizeof(rbrn));
    memset(&log, 0, sizeof(log));
    drv = xmi_driver_create(log_midi, &log);
    seq = xmi_sequence_create(drv);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_FREE, xmi_sequence_status(seq));
    TEST_ASSERT_TRUE(xmi_sequence_init(seq, image, size, 0));
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_DONE, xmi_sequence_status(seq));
    xmi_sequence_start(seq);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_PLAYING, xmi_sequence_status(seq));

    /* Tick 1: program, note 60 on; delay 5 starts. */
    xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(2, log.count);
    TEST_ASSERT_EQUAL_HEX8(0xc0, log.status[0]);
    TEST_ASSERT_EQUAL_HEX8(0x90, log.status[1]);
    TEST_ASSERT_EQUAL_INT(1, xmi_sequence_queued_notes(seq));
    TEST_ASSERT_EQUAL_INT(1, xmi_driver_channel_notes(drv, 0));
    /* Ticks 2..5: nothing. Tick 6: marker (sent through), note 62. */
    for (tick = 2; tick <= 5; tick++) {
        xmi_driver_serve(drv);
        TEST_ASSERT_EQUAL_INT(2, log.count);
    }
    xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(4, log.count);
    TEST_ASSERT_EQUAL_UINT(120, log.data1[2]);
    TEST_ASSERT_EQUAL_UINT(62, log.data1[3]);
    /* Note 62 lasts 4 ticks: off on tick 10. Note 60 (10 ticks): tick 11. */
    for (tick = 7; tick <= 9; tick++) xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(0, log.note_offs);
    xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(1, log.note_offs);
    TEST_ASSERT_EQUAL_UINT(62, log.data1[log.count - 1]);
    xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(2, log.note_offs);
    TEST_ASSERT_EQUAL_UINT(60, log.data1[log.count - 1]);
    TEST_ASSERT_EQUAL_INT(0, xmi_driver_channel_notes(drv, 0));
    /* Delay 127 + 2 = 129 ticks after tick 6, then end of track with the
     * default loop count of one: the sequence is done on tick 135. */
    for (tick = 12; tick < 135; tick++) {
        xmi_driver_serve(drv);
        TEST_ASSERT_EQUAL_INT(XMI_SEQ_PLAYING, xmi_sequence_status(seq));
    }
    xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_DONE, xmi_sequence_status(seq));

    /* Branch: land on the marker, which XMI_serve skips. */
    xmi_sequence_start(seq);
    log.count = 0;
    TEST_ASSERT_FALSE(xmi_sequence_branch(seq, 9));
    TEST_ASSERT_TRUE(xmi_sequence_branch(seq, 1));
    TEST_ASSERT_EQUAL_size_t(7, xmi_sequence_position(seq));
    xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(2, log.count);
    TEST_ASSERT_EQUAL_UINT(120, log.data1[0]);
    TEST_ASSERT_EQUAL_UINT(62, log.data1[1]);

    /* Loop forever instead. */
    xmi_sequence_start(seq);
    xmi_sequence_set_loop_count(seq, 0);
    for (tick = 0; tick < 300; tick++) xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_PLAYING, xmi_sequence_status(seq));
    TEST_ASSERT_GREATER_THAN_INT(3, log.note_ons);
    xmi_sequence_destroy(seq);
    xmi_driver_destroy(drv);
}

static void test_for_loops_and_volume_scaling(void)
{
    static const unsigned char events[] = {
        0xb0, 7, 100,            /* volume 100 */
        0xb0, 116, 0x02,         /* for loop, twice */
        0x90, 60, 100, 0x01,
        0x02,
        0xb0, 117, 0x7f,         /* loop end */
        0x90, 64, 100, 0x01,
        0x03,
        0xff, 0x2f, 0x00
    };
    unsigned char image[256];
    struct midi_log log;
    struct xmi_driver *drv;
    struct xmi_sequence *seq;
    size_t size;
    int tick;
    int i;
    int sixties;
    int sixty_fours;

    size = build_xmi(image, events, sizeof(events), NULL, 0);
    memset(&log, 0, sizeof(log));
    drv = xmi_driver_create(log_midi, &log);
    seq = xmi_sequence_create(drv);
    TEST_ASSERT_TRUE(xmi_sequence_init(seq, image, size, 0));
    xmi_sequence_set_volume(seq, 64, 0);
    xmi_sequence_start(seq);
    for (tick = 0; tick < 40; tick++) xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_DONE, xmi_sequence_status(seq));
    sixties = sixty_fours = 0;
    for (i = 0; i < log.count; i++) {
        if (log.status[i] == 0x90 && log.data1[i] == 60) sixties++;
        if (log.status[i] == 0x90 && log.data1[i] == 64) sixty_fours++;
    }
    TEST_ASSERT_EQUAL_INT(2, sixties);
    TEST_ASSERT_EQUAL_INT(1, sixty_fours);
    /* Controller 7 reaches the driver scaled by the sequence volume:
     * 100 * 64 * 127 / (127 * 127). */
    i = log_find(&log, 0xb0, 7);
    TEST_ASSERT_TRUE(i >= 0);
    TEST_ASSERT_EQUAL_UINT(100 * 64 * 127 / 16129, log.data2[i]);
    TEST_ASSERT_EQUAL_INT(100, xmi_sequence_controller(seq, 0, 7));
    /* The loop controllers never reach the driver. */
    TEST_ASSERT_EQUAL_INT(-1, log_find(&log, 0xb0, 116));
    TEST_ASSERT_EQUAL_INT(-1, log_find(&log, 0xb0, 117));
    xmi_sequence_destroy(seq);
    xmi_driver_destroy(drv);
}

static void test_volume_ramp_and_master_volume(void)
{
    static const unsigned char events[] = {
        0xb0, 7, 127,
        0x90, 60, 100, 0x7f,
        0x7f, 0x7f, 0x7f, 0x7f,
        0xff, 0x2f, 0x00
    };
    unsigned char image[256];
    struct midi_log log;
    struct xmi_driver *drv;
    struct xmi_sequence *seq;
    size_t size;
    int tick;

    size = build_xmi(image, events, sizeof(events), NULL, 0);
    memset(&log, 0, sizeof(log));
    drv = xmi_driver_create(log_midi, &log);
    seq = xmi_sequence_create(drv);
    TEST_ASSERT_TRUE(xmi_sequence_init(seq, image, size, 0));
    xmi_sequence_set_volume(seq, 0, 0);
    xmi_sequence_start(seq);
    xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_UINT(0, log.data2[log_find(&log, 0xb0, 7)]);
    /* Fade to 127 over one second: 120 ticks later it has arrived. */
    xmi_sequence_set_volume(seq, 127, 1000);
    for (tick = 0; tick < 60; tick++) xmi_driver_serve(drv);
    TEST_ASSERT_TRUE(xmi_sequence_volume(seq) > 50 && xmi_sequence_volume(seq) < 80);
    for (tick = 0; tick < 70; tick++) xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(127, xmi_sequence_volume(seq));
    /* XMI_serve only forwards the ramp every eighth service interval and
     * stops forwarding once the target is reached: the ramp lands on 127 at
     * interval 121, so the driver last heard 125 at interval 120. */
    TEST_ASSERT_EQUAL_UINT(125, log.data2[log_last(&log, 0xb0, 7)]);
    /* Master volume rescales playing sequences at once. */
    xmi_driver_set_master_volume(drv, 64);
    TEST_ASSERT_EQUAL_UINT(64, log.data2[log.count - 1]);
    TEST_ASSERT_EQUAL_UINT(7, log.data1[log.count - 1]);
    xmi_sequence_destroy(seq);
    xmi_driver_destroy(drv);
}

static void test_stop_flushes_notes_and_resume_refreshes_controllers(void)
{
    static const unsigned char events[] = {
        0xc1, 0x03,
        0xb1, 7, 90,
        0xb1, 10, 20,
        0x91, 60, 100, 0x7f,
        0x7f, 0x7f,
        0xff, 0x2f, 0x00
    };
    unsigned char image[256];
    struct midi_log log;
    struct xmi_driver *drv;
    struct xmi_sequence *seq;
    size_t size;
    int i;

    size = build_xmi(image, events, sizeof(events), NULL, 0);
    memset(&log, 0, sizeof(log));
    drv = xmi_driver_create(log_midi, &log);
    seq = xmi_sequence_create(drv);
    TEST_ASSERT_TRUE(xmi_sequence_init(seq, image, size, 0));
    xmi_sequence_start(seq);
    for (i = 0; i < 10; i++) xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(1, xmi_sequence_queued_notes(seq));
    xmi_sequence_stop(seq);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_STOPPED, xmi_sequence_status(seq));
    TEST_ASSERT_EQUAL_INT(0, xmi_sequence_queued_notes(seq));
    TEST_ASSERT_EQUAL_INT(1, log.note_offs);
    TEST_ASSERT_EQUAL_INT(0, xmi_driver_channel_notes(drv, 1));
    for (i = 0; i < 10; i++) xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(1, log.note_offs);
    log.count = 0;
    xmi_sequence_resume(seq);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_PLAYING, xmi_sequence_status(seq));
    /* Program, volume and pan for channel 1 are re-sent from the log. */
    TEST_ASSERT_TRUE(log_find(&log, 0xc1, 3) >= 0);
    TEST_ASSERT_TRUE(log_find(&log, 0xb1, 7) >= 0);
    TEST_ASSERT_EQUAL_UINT(20, log.data2[log_find(&log, 0xb1, 10)]);
    TEST_ASSERT_EQUAL_INT(-1, log_find(&log, 0xc0, 0));
    xmi_sequence_end(seq);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_DONE, xmi_sequence_status(seq));
    xmi_sequence_destroy(seq);
    xmi_driver_destroy(drv);
}

struct trigger_log {
    int count;
    int first_tick;
    int tick;
    int values[64];
    unsigned branch;
};

static void on_trigger(void *user, struct xmi_sequence *seq, int channel,
                       int value)
{
    struct trigger_log *log;

    (void)channel;
    log = user;
    if (log->count == 0) log->first_tick = log->tick;
    if (log->count < 64) log->values[log->count] = value;
    log->count++;
    xmi_sequence_branch(seq, log->branch);
}

static void test_official_city_score_triggers_and_branches(void)
{
    struct midi_log midi;
    struct trigger_log triggers;
    struct xmi_driver *drv;
    struct xmi_sequence *seq;
    unsigned char *data;
    size_t size;
    unsigned id;
    size_t offset;
    int i;

    data = require_asset("CITYPROV.XMI", &size);
    memset(&midi, 0, sizeof(midi));
    memset(&triggers, 0, sizeof(triggers));
    triggers.branch = 40;
    drv = xmi_driver_create(log_midi, &midi);
    seq = xmi_sequence_create(drv);
    TEST_ASSERT_TRUE(xmi_sequence_init(seq, data, size, 0));
    xmi_sequence_set_trigger_callback(seq, on_trigger, &triggers);
    xmi_sequence_start(seq);
    for (i = 1; i <= 1029; i++) {
        triggers.tick = i;
        xmi_driver_serve(drv);
    }
    /* The first trigger sits at tick 1028 and fires on service tick 1029. */
    TEST_ASSERT_EQUAL_INT(1, triggers.count);
    TEST_ASSERT_EQUAL_INT(1029, triggers.first_tick);
    /* The branch landed just after marker 40 and playback went on there. */
    for (i = 0; i < xmi_form_branch_count(xmi_sequence_form(seq)); i++) {
        xmi_form_branch(xmi_sequence_form(seq), i, &id, &offset);
        if (id == 40) break;
    }
    TEST_ASSERT_TRUE(xmi_sequence_position(seq) > offset);
    TEST_ASSERT_TRUE(xmi_sequence_position(seq) < offset + 400);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_PLAYING, xmi_sequence_status(seq));
    TEST_ASSERT_GREATER_THAN_INT(50, midi.note_ons);
    TEST_ASSERT_EQUAL_INT(0x082ca2, xmi_sequence_file_tempo(seq));
    xmi_sequence_destroy(seq);
    xmi_driver_destroy(drv);
    free(data);
}

static void test_official_forum_score_loops_forever_and_forum3_ends(void)
{
    struct midi_log midi;
    struct xmi_driver *drv;
    struct xmi_sequence *seq;
    unsigned char *data;
    size_t size;
    int i;
    int ons_after_one_pass;

    data = require_asset("FORUM1.XMI", &size);
    memset(&midi, 0, sizeof(midi));
    drv = xmi_driver_create(log_midi, &midi);
    seq = xmi_sequence_create(drv);
    TEST_ASSERT_TRUE(xmi_sequence_init(seq, data, size, 0));
    xmi_sequence_start(seq);
    /* One pass is 7367 ticks; the loop end at tick 7367 is served on tick
     * 7368 together with the first events of the second pass. The loop
     * stack is not per channel: the first loop end (channel 1) returns to
     * the innermost loop start, channel 4's at offset 105, so the three
     * note-ons before offset 108 belong to the first pass only. */
    for (i = 0; i < 7367; i++) xmi_driver_serve(drv);
    ons_after_one_pass = midi.note_ons;
    TEST_ASSERT_EQUAL_INT(993, ons_after_one_pass);
    for (i = 0; i < 7367; i++) xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_PLAYING, xmi_sequence_status(seq));
    TEST_ASSERT_EQUAL_INT(993 + 990, midi.note_ons);
    TEST_ASSERT_EQUAL_INT(midi.note_ons, midi.note_offs + xmi_sequence_queued_notes(seq));
    free(data);

    data = require_asset("FORUM3.XMI", &size);
    TEST_ASSERT_TRUE(xmi_sequence_init(seq, data, size, 0));
    xmi_sequence_start(seq);
    for (i = 0; i < 15065; i++) xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_PLAYING, xmi_sequence_status(seq));
    xmi_driver_serve(drv);
    TEST_ASSERT_EQUAL_INT(XMI_SEQ_DONE, xmi_sequence_status(seq));
    TEST_ASSERT_EQUAL_INT(0, xmi_sequence_queued_notes(seq));
    xmi_sequence_destroy(seq);
    xmi_driver_destroy(drv);
    free(data);
}

/* ------------------------------------------------------------------------ */
/* Driver behaviour                                                         */

static struct miles_opl *bank_driver(struct reg_log *regs, unsigned char **bank)
{
    struct miles_opl *drv;
    struct xmi_driver *preset;
    size_t size;

    *bank = require_asset("CAESAR.OPL", &size);
    drv = miles_opl_create(44100);
    TEST_ASSERT_GREATER_THAN_INT(0, miles_opl_load_bank(drv, *bank, size));
    preset = xmi_driver_create((xmi_midi_fn)miles_opl_message, drv);
    xmi_driver_reset(preset);
    xmi_driver_destroy(preset);
    memset(regs, 0, sizeof(*regs));
    miles_opl_set_write_tap(drv, log_reg, regs);
    return drv;
}

static void test_driver_note_on_writes_the_expected_registers(void)
{
    struct reg_log regs;
    struct miles_opl *drv;
    unsigned char *bank;

    drv = bank_driver(&regs, &bank);
    TEST_ASSERT_EQUAL_HEX8(0x01, miles_opl_register(drv, 0x105));
    miles_opl_message(drv, 0xc0, 1, 0);
    miles_opl_message(drv, 0x90, 60, 127);
    TEST_ASSERT_EQUAL_INT(1, miles_opl_active_voices(drv));
    TEST_ASSERT_EQUAL_INT(1, miles_opl_channel_notes(drv, 0));
    /* Middle C: F-number 0x2b2 in block 3, key on, on physical channel 0. */
    TEST_ASSERT_EQUAL_HEX8(0xb2, reg_last(&regs, 0x0a0));
    TEST_ASSERT_EQUAL_HEX8(0x2e, reg_last(&regs, 0x0b0));
    /* Patch 1 is FM (connection 0), feedback 6, pan centre: 0xC0 = 0x36. */
    TEST_ASSERT_EQUAL_HEX8(0x36, reg_last(&regs, 0x0c0));
    /* Modulator keeps its level (0x9d), the carrier at full volume is 0. */
    TEST_ASSERT_EQUAL_HEX8(0x9d, reg_last(&regs, 0x040));
    TEST_ASSERT_EQUAL_HEX8(0x00, reg_last(&regs, 0x043));
    /* AM/VIB/EG/KSR + multiplier from the timbre. */
    TEST_ASSERT_EQUAL_HEX8(0x41, reg_last(&regs, 0x020));
    TEST_ASSERT_EQUAL_HEX8(0x13, reg_last(&regs, 0x023));
    TEST_ASSERT_EQUAL_HEX8(0xf2, reg_last(&regs, 0x060));
    TEST_ASSERT_EQUAL_HEX8(0x53, reg_last(&regs, 0x080));
    TEST_ASSERT_EQUAL_HEX8(0xf3, reg_last(&regs, 0x083));

    /* Softer velocity: table[1] = 85 -> volume 85 -> level 63*85/127 = 42. */
    miles_opl_message(drv, 0x90, 62, 8);
    TEST_ASSERT_EQUAL_HEX8(0x15, reg_last(&regs, 0x044));
    /* Channel volume 0 silences the carrier of every voice on the channel. */
    miles_opl_message(drv, 0xb0, 7, 0);
    TEST_ASSERT_EQUAL_HEX8(0x3f, reg_last(&regs, 0x043));
    TEST_ASSERT_EQUAL_HEX8(0x3f, reg_last(&regs, 0x044));
    miles_opl_message(drv, 0xb0, 7, 127);
    /* Pan thresholds: below 28 left, above 99 right. */
    miles_opl_message(drv, 0xb0, 10, 0);
    TEST_ASSERT_EQUAL_HEX8(0x16, reg_last(&regs, 0x0c0));
    miles_opl_message(drv, 0xb0, 10, 127);
    TEST_ASSERT_EQUAL_HEX8(0x26, reg_last(&regs, 0x0c0));
    miles_opl_message(drv, 0xb0, 10, 64);
    TEST_ASSERT_EQUAL_HEX8(0x36, reg_last(&regs, 0x0c0));
    /* Pitch bend up by one semitone (range 2, +4096 of 8192): C# is row 1
     * of the F-number table, still block 3. */
    miles_opl_message(drv, 0xe0, 0, 0x60);
    TEST_ASSERT_EQUAL_HEX8(0x2e, reg_last(&regs, 0x0b0));
    TEST_ASSERT_EQUAL_HEX8(0xdb, reg_last(&regs, 0x0a0));
    /* A quarter of the range up is half a semitone: column 8 of row 0. */
    miles_opl_message(drv, 0xe0, 0, 0x50);
    TEST_ASSERT_EQUAL_HEX8(0x2e, reg_last(&regs, 0x0b0));
    TEST_ASSERT_EQUAL_HEX8(0xc6, reg_last(&regs, 0x0a0));
    miles_opl_message(drv, 0xe0, 0, 0x40);
    /* Note off clears key-on and frees the voice. */
    miles_opl_message(drv, 0x80, 60, 0);
    TEST_ASSERT_EQUAL_HEX8(0x0e, reg_last(&regs, 0x0b0));
    TEST_ASSERT_EQUAL_INT(1, miles_opl_active_voices(drv));
    miles_opl_message(drv, 0x90, 62, 0);
    TEST_ASSERT_EQUAL_INT(0, miles_opl_active_voices(drv));
    TEST_ASSERT_EQUAL_INT(0, miles_opl_channel_notes(drv, 0));
    miles_opl_destroy(drv);
    free(bank);
}

static void test_driver_sustain_and_reset_controllers(void)
{
    struct reg_log regs;
    struct miles_opl *drv;
    unsigned char *bank;

    drv = bank_driver(&regs, &bank);
    miles_opl_message(drv, 0xc0, 1, 0);
    miles_opl_message(drv, 0xb0, 64, 127);
    miles_opl_message(drv, 0x90, 60, 100);
    miles_opl_message(drv, 0x80, 60, 0);
    TEST_ASSERT_EQUAL_INT(1, miles_opl_active_voices(drv));
    TEST_ASSERT_EQUAL_HEX8(0x2e, reg_last(&regs, 0x0b0));
    miles_opl_message(drv, 0xb0, 64, 0);
    TEST_ASSERT_EQUAL_INT(0, miles_opl_active_voices(drv));
    TEST_ASSERT_EQUAL_HEX8(0x0e, reg_last(&regs, 0x0b0));
    miles_opl_message(drv, 0xb0, 64, 127);
    miles_opl_message(drv, 0x90, 60, 100);
    miles_opl_message(drv, 0x80, 60, 0);
    miles_opl_message(drv, 0xb0, 121, 0);
    TEST_ASSERT_EQUAL_INT(0, miles_opl_active_voices(drv));
    miles_opl_message(drv, 0x90, 60, 100);
    miles_opl_message(drv, 0x90, 64, 100);
    miles_opl_message(drv, 0xb0, 123, 0);
    TEST_ASSERT_EQUAL_INT(0, miles_opl_active_voices(drv));
    miles_opl_destroy(drv);
    free(bank);
}

static void test_driver_allocates_round_robin_and_steals(void)
{
    struct reg_log regs;
    struct miles_opl *drv;
    unsigned char *bank;
    int i;
    int written[18];

    drv = bank_driver(&regs, &bank);
    miles_opl_message(drv, 0xc0, 1, 0);
    memset(written, 0, sizeof(written));
    for (i = 0; i < 18; i++) {
        regs.count = 0;
        miles_opl_message(drv, 0x90, (unsigned)(40 + i), 100);
        /* Physical channel i: its 0xB0 register was written with key on. */
        TEST_ASSERT_EQUAL_HEX8(0x20, reg_last(&regs, (unsigned)(
            (miles_opl_channel_bank[i] << 8) |
            (0xb0 + miles_opl_channel_register[i]))) & 0x20);
    }
    TEST_ASSERT_EQUAL_INT(18, miles_opl_active_voices(drv));
    TEST_ASSERT_EQUAL_INT(18, miles_opl_channel_notes(drv, 0));
    /* A 19th note steals the physical channel of an equally ranked voice,
     * which is silenced and freed. */
    regs.count = 0;
    miles_opl_message(drv, 0x90, 70, 100);
    TEST_ASSERT_EQUAL_INT(18, miles_opl_active_voices(drv));
    TEST_ASSERT_EQUAL_INT(18, miles_opl_channel_notes(drv, 0));
    TEST_ASSERT_TRUE(regs.count > 0);
    miles_opl_message(drv, 0xb0, 123, 0);
    TEST_ASSERT_EQUAL_INT(0, miles_opl_active_voices(drv));

    /* Voice protect (controller 112) makes a channel's voices outrank
     * every unprotected candidate: nothing is stolen, the new voices wait
     * without a physical channel, and the 21st virtual voice is dropped. */
    miles_opl_message(drv, 0xb0, 112, 127);
    for (i = 0; i < 18; i++) miles_opl_message(drv, 0x90, (unsigned)(40 + i), 100);
    miles_opl_message(drv, 0xc1, 1, 0);
    miles_opl_message(drv, 0x91, 60, 100);
    miles_opl_message(drv, 0x91, 61, 100);
    TEST_ASSERT_EQUAL_INT(20, miles_opl_active_voices(drv));
    TEST_ASSERT_EQUAL_INT(18, miles_opl_channel_notes(drv, 0));
    TEST_ASSERT_EQUAL_INT(0, miles_opl_channel_notes(drv, 1));
    miles_opl_message(drv, 0x91, 62, 100);
    TEST_ASSERT_EQUAL_INT(20, miles_opl_active_voices(drv));
    /* Freeing a protected note lets a waiting voice in only when the next
     * note-on asks for a channel: the waiting voices stay silent. */
    miles_opl_message(drv, 0x80, 40, 0);
    TEST_ASSERT_EQUAL_INT(19, miles_opl_active_voices(drv));
    miles_opl_message(drv, 0xb0, 123, 0);
    miles_opl_message(drv, 0xb1, 123, 0);
    TEST_ASSERT_EQUAL_INT(0, miles_opl_active_voices(drv));
    miles_opl_destroy(drv);
    free(bank);
}

static void test_driver_pairs_four_op_voices(void)
{
    struct reg_log regs;
    struct miles_opl *drv;
    unsigned char *bank;

    drv = bank_driver(&regs, &bank);
    TEST_ASSERT_EQUAL_HEX8(0x00, miles_opl_register(drv, 0x104));
    miles_opl_message(drv, 0xc0, 0, 0); /* patch 0 is 4-op */
    miles_opl_message(drv, 0x90, 60, 100);
    TEST_ASSERT_EQUAL_HEX8(0x01, miles_opl_register(drv, 0x104));
    /* Both channels of the pair are programmed, only the leader has pitch. */
    TEST_ASSERT_EQUAL_HEX8(0x2e, reg_last(&regs, 0x0b0));
    TEST_ASSERT_EQUAL_INT(-1, reg_last(&regs, 0x0a3));
    TEST_ASSERT_TRUE(reg_last(&regs, 0x0c3) >= 0);
    TEST_ASSERT_TRUE(reg_last(&regs, 0x048) >= 0); /* op3: channel 3 op1 */
    miles_opl_message(drv, 0x90, 64, 100);
    TEST_ASSERT_EQUAL_HEX8(0x03, miles_opl_register(drv, 0x104));
    /* A 2-op note now lands on channel 2, the first free one. */
    miles_opl_message(drv, 0xc1, 1, 0);
    miles_opl_message(drv, 0x91, 60, 100);
    TEST_ASSERT_EQUAL_HEX8(0x2e, reg_last(&regs, 0x0b2));
    /* Releasing the first pair leaves the enable bit set, as the driver
     * only clears it when a 2-op voice takes the channel: the next 2-op
     * note lands on channel 3, the pair's partner, and drops it. */
    miles_opl_message(drv, 0x80, 60, 0);
    TEST_ASSERT_EQUAL_HEX8(0x03, miles_opl_register(drv, 0x104));
    miles_opl_message(drv, 0x91, 62, 100);
    TEST_ASSERT_EQUAL_HEX8(0x02, miles_opl_register(drv, 0x104));
    TEST_ASSERT_EQUAL_HEX8(0x2f, reg_last(&regs, 0x0b3));
    miles_opl_destroy(drv);
    free(bank);
}

static void test_player_renders_audio_at_the_service_rate(void)
{
    struct xmi_player *player;
    struct xmi_sequence *seq;
    struct xmi_driver *reference;
    struct midi_log log;
    struct xmi_sequence *ref_seq;
    unsigned char *bank;
    unsigned char *data;
    size_t bank_size;
    size_t size;
    int16_t pcm[2 * 4410];
    int i;
    long energy;
    int peak;

    bank = require_asset("CAESAR.OPL", &bank_size);
    data = require_asset("FORUM1.XMI", &size);
    player = xmi_player_create(44100);
    TEST_ASSERT_NOT_NULL(player);
    TEST_ASSERT_GREATER_THAN_INT(0, xmi_player_load_bank(player, bank, bank_size));
    seq = xmi_sequence_create(xmi_player_driver(player));
    TEST_ASSERT_TRUE(xmi_sequence_init(seq, data, size, 0));
    xmi_sequence_start(seq);
    energy = 0;
    peak = 0;
    for (i = 0; i < 20; i++) {
        size_t n;
        xmi_player_render(player, pcm, 4410);
        for (n = 0; n < 2 * 4410; n++) {
            if (abs(pcm[n]) > peak) peak = abs(pcm[n]);
            energy += abs(pcm[n]) > 64;
        }
    }
    TEST_ASSERT_GREATER_THAN_INT(2000, peak);
    TEST_ASSERT_LESS_THAN_INT(32000, peak);
    TEST_ASSERT_GREATER_THAN_INT(20000, (int)energy);
    /* Two seconds of audio is 240 service ticks: the same position a pure
     * sequencer reaches after 240 serves. */
    memset(&log, 0, sizeof(log));
    reference = xmi_driver_create(log_midi, &log);
    ref_seq = xmi_sequence_create(reference);
    xmi_sequence_init(ref_seq, data, size, 0);
    xmi_sequence_start(ref_seq);
    for (i = 0; i < 240; i++) xmi_driver_serve(reference);
    TEST_ASSERT_EQUAL_size_t(xmi_sequence_position(ref_seq),
                             xmi_sequence_position(seq));
    xmi_driver_destroy(reference);
    xmi_player_destroy(player);
    free(bank);
    free(data);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_driver_tables_match_shipped_opl3_driver);
    RUN_TEST(test_sibling_fm_drivers_share_the_tables);
    RUN_TEST(test_gtl_bank_loads_every_timbre);
    RUN_TEST(test_ad_fallback_bank_loads);
    RUN_TEST(test_bank_loader_rejects_garbage);
    RUN_TEST(test_official_scores_expose_their_branches);
    RUN_TEST(test_score_timbres_exist_in_the_bank);
    RUN_TEST(test_synthetic_image_layout);
    RUN_TEST(test_driver_reset_sends_the_ail_channel_preset);
    RUN_TEST(test_synthetic_sequence_timing_notes_and_branch);
    RUN_TEST(test_for_loops_and_volume_scaling);
    RUN_TEST(test_volume_ramp_and_master_volume);
    RUN_TEST(test_stop_flushes_notes_and_resume_refreshes_controllers);
    RUN_TEST(test_official_city_score_triggers_and_branches);
    RUN_TEST(test_official_forum_score_loops_forever_and_forum3_ends);
    RUN_TEST(test_driver_note_on_writes_the_expected_registers);
    RUN_TEST(test_driver_sustain_and_reset_controllers);
    RUN_TEST(test_driver_allocates_round_robin_and_steals);
    RUN_TEST(test_driver_pairs_four_op_voices);
    RUN_TEST(test_player_renders_audio_at_the_service_rate);
    return UNITY_END();
}
