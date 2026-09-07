#include <unity/unity.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_port_text.h"

/* The host normally reads the game data's C2.ENG for language detection;
 * the test supplies whatever it wants detected. */
static unsigned char probe_c2eng[64];
static size_t probe_size;

size_t c2_host_asset_read(const char *filename, void *buffer, size_t size, size_t offset)
{
    (void)filename;
    if (offset >= probe_size) return 0;
    if (size > probe_size - offset) size = probe_size - offset;
    memcpy(buffer, probe_c2eng + offset, size);
    return size;
}

static void set_probe(const char *first_string)
{
    /* Textfile header, a two-entry table, group 1 = first_string. */
    size_t n = strlen(first_string);
    memset(probe_c2eng, 0, sizeof(probe_c2eng));
    memcpy(probe_c2eng, "Textfile", 8);
    probe_c2eng[12] = 16;
    memcpy(probe_c2eng + 16, first_string, n);
    probe_size = 16 + n + 1;
}

void setUp(void)
{
    c2_port_text_shutdown();
    c2_port_text_select("en");
    set_probe("File");
}

void tearDown(void) {}

static unsigned int u32(const unsigned char *p)
{
    return p[0] | (unsigned int)p[1] << 8 | (unsigned int)p[2] << 16 | (unsigned int)p[3] << 24;
}

/* String `index` of `group` in a built Textfile. */
static const char *text_string(const unsigned char *c2eng, int group, int index)
{
    const char *p = (const char *)c2eng + u32(c2eng + 8 + group * 4);
    while (index-- > 0) p += strlen(p) + 1;
    return p;
}

static void test_bundle_lists_every_language_with_its_name(void)
{
    int i;
    int have_en = 0;
    int have_de = 0;

    TEST_ASSERT_GREATER_OR_EQUAL(3, c2_port_text_language_count());
    for (i = 0; i < c2_port_text_language_count(); i++) {
        const struct c2_port_language *l = c2_port_text_language(i);
        TEST_ASSERT_NOT_NULL(l);
        if (strcmp(l->tag, "en") == 0) { have_en = 1; TEST_ASSERT_EQUAL_STRING("English", l->name); }
        if (strcmp(l->tag, "de") == 0) { have_de = 1; TEST_ASSERT_EQUAL_STRING("Deutsch", l->name); }
    }
    TEST_ASSERT_TRUE(have_en);
    TEST_ASSERT_TRUE(have_de);
    TEST_ASSERT_EQUAL_STRING("en", c2_port_text_language(0)->tag);
}

static void test_detects_the_language_from_the_disc_text(void)
{
    TEST_ASSERT_EQUAL_STRING("de", c2_port_text_detect((const unsigned char *)"Textfile\0\0\0\0\x10\0\0\0Datei", 22));
    TEST_ASSERT_EQUAL_STRING("fr", c2_port_text_detect((const unsigned char *)"Textfile\0\0\0\0\x10\0\0\0Fichier", 24));
    TEST_ASSERT_NULL(c2_port_text_detect((const unsigned char *)"Textfile\0\0\0\0\x10\0\0\0Archivo", 24));
    TEST_ASSERT_NULL(c2_port_text_detect((const unsigned char *)"Helpfile", 8));
}

static void test_detection_selects_unless_overridden(void)
{
    c2_port_text_select(NULL);
    set_probe("Datei");
    TEST_ASSERT_EQUAL_STRING("de", c2_port_text_selected());
    c2_port_text_select(NULL);
    set_probe("Archivo");
    TEST_ASSERT_EQUAL_STRING("en", c2_port_text_selected());
    c2_port_text_select(NULL);
    probe_size = 0;
    TEST_ASSERT_EQUAL_STRING("en", c2_port_text_selected());
    TEST_ASSERT_TRUE(c2_port_text_select("fr"));
    TEST_ASSERT_EQUAL_STRING("fr", c2_port_text_selected());
    TEST_ASSERT_FALSE(c2_port_text_select("xx"));
    TEST_ASSERT_EQUAL_STRING("fr", c2_port_text_selected());
}

static void test_english_textfile_has_the_1996_layout(void)
{
    size_t size;
    const unsigned char *c2eng = c2_port_text_c2eng(&size);

    TEST_ASSERT_NOT_NULL(c2eng);
    TEST_ASSERT_EQUAL_MEMORY("Textfile", c2eng, 8);
    TEST_ASSERT_EQUAL_UINT32(0, u32(c2eng + 8));
    TEST_ASSERT_EQUAL_UINT32(8 + 147 * 4, u32(c2eng + 12));
    TEST_ASSERT_EQUAL_UINT32(u32(c2eng + 8 + 116 * 4), u32(c2eng + 8 + 117 * 4));
    TEST_ASSERT_EQUAL_UINT32(u32(c2eng + 8 + 116 * 4), u32(c2eng + 8 + 118 * 4));
    TEST_ASSERT_EQUAL_UINT32(u32(c2eng + 8 + 119 * 4), u32(c2eng + 8 + 120 * 4));
    TEST_ASSERT_EQUAL_STRING("File", text_string(c2eng, 1, 0));
    TEST_ASSERT_EQUAL_STRING("Men", text_string(c2eng, 0x2f, 8));
    TEST_ASSERT_EQUAL_STRING("Cancel", text_string(c2eng, 0x2b, 18));
    TEST_ASSERT_LESS_THAN(40000, size);
}

static void test_german_text_is_transcoded_to_the_font_encoding(void)
{
    size_t size;
    const unsigned char *c2eng;

    c2_port_text_select("de");
    c2eng = c2_port_text_c2eng(&size);
    TEST_ASSERT_NOT_NULL(c2eng);
    TEST_ASSERT_EQUAL_STRING("Datei", text_string(c2eng, 1, 0));
    TEST_ASSERT_EQUAL_STRING("M\x84nner", text_string(c2eng, 0x2f, 8));
    /* The battle icon tips exist in German because the 1996 file has them. */
    TEST_ASSERT_EQUAL_STRING_LEN("Drehen Sie", text_string(c2eng, 0x74, 0), 10);
}

static void test_help_pages_and_aliases(void)
{
    size_t size;
    const unsigned char *help = c2_port_text_helpeng(&size);
    unsigned int page1;
    unsigned int page1234;
    unsigned int page1236;

    TEST_ASSERT_NOT_NULL(help);
    TEST_ASSERT_EQUAL_MEMORY("Helpfile", help, 8);
    TEST_ASSERT_EQUAL_UINT32(0, u32(help + 8));
    page1 = u32(help + 8 + 1 * 0x3a);
    TEST_ASSERT_EQUAL_UINT32(8 + 2000 * 0x3a, page1);
    TEST_ASSERT_EQUAL_STRING("On-Line Help", (const char *)help + page1);
    TEST_ASSERT_EQUAL_STRING("null.pl8", (const char *)help + 8 + 1 * 0x3a + 10);
    page1234 = u32(help + 8 + 1234 * 0x3a);
    page1236 = u32(help + 8 + 1236 * 0x3a);
    TEST_ASSERT_EQUAL_UINT32(page1234, page1236);
    TEST_ASSERT_EQUAL_STRING("acmaxim.pl8", (const char *)help + 8 + 565 * 0x3a + 10);
}

static void test_readfile_hooks_serve_offsets(void)
{
    unsigned char buffer[0x3a];
    size_t n;

    TEST_ASSERT_TRUE(c2_port_text_is_language_file("c2.eng"));
    TEST_ASSERT_TRUE(c2_port_text_is_language_file("C2.GER"));
    TEST_ASSERT_TRUE(c2_port_text_is_help_file("help.eng"));
    TEST_ASSERT_FALSE(c2_port_text_is_language_file("c2win.eng"));
    TEST_ASSERT_FALSE(c2_port_text_is_help_file("helpers.pl8"));
    TEST_ASSERT_FALSE(c2_port_text_read("font_c2.pl8", buffer, sizeof(buffer), 0, &n));
    TEST_ASSERT_TRUE(c2_port_text_read("help.eng", buffer, sizeof(buffer), 8 + 1 * 0x3a, &n));
    TEST_ASSERT_EQUAL_size_t(sizeof(buffer), n);
    TEST_ASSERT_EQUAL_UINT32(8 + 2000 * 0x3a, u32(buffer));
    TEST_ASSERT_TRUE(c2_port_text_read("c2.eng", buffer, sizeof(buffer), 0, &n));
    TEST_ASSERT_EQUAL_MEMORY("Textfile", buffer, 8);
}

/*
 * A hand-written translation with everything a translator might type:
 * every escape the po format allows, umlauts and ß, a character CP437
 * has but the font cannot draw, one outside CP437, no-break space,
 * fuzzy and empty msgstr (both fall back to English), a reference page,
 * help line breaks, links, a literal $, Windows line endings, an entry
 * without a blank line before its comment, and CRLF.
 */
static const char tricky_po[] =
    "# comment\n"
    "msgid \"\"\n"
    "msgstr \"\"\n"
    "\"Content-Type: text/plain; charset=UTF-8\\n\"\n"
    "\"X-C2-Name: Pr\xc3\xbc" "fung\\n\"\n"
    "\"X-C2-Detect: Datei\\n\"\n"
    "\n"
    "msgctxt \"0x1/0\"\n"
    "msgid \"File\"\n"
    "msgstr \"D\xc3\xa4tei \\\"quoted\\\" back\\\\slash tab\\tend\"\n"
    "\n"
    "#, fuzzy\n"
    "msgctxt \"0x1/1\"\n"
    "msgid \"New Game\"\n"
    "msgstr \"Fuzzy must not be used\"\n"
    "\n"
    "msgctxt \"0x1/2\"\n"
    "msgid \"Load\"\n"
    "msgstr \"\"\n"
    "#. no blank line before this comment\n"
    "msgctxt \"0x1/3\"\n"
    "msgid \"Save\"\n"
    "msgstr \"\"\n"
    "\"Gro\xc3\x9f\"\n"
    "\"e \xc2\xab" "Anf\xc3\xbc" "hrung\xc2\xbb\"\n"
    "\r\n"
    "msgctxt \"0x1/4\"\r\n"
    "msgid \"Quit\"\r\n"
    "msgstr \"\xe2\x82\xac 1\xc2\xa0" "000 \xc5\x91\"\r\n"
    "\n"
    "msgctxt \"help/1/0\"\n"
    "msgid \"Title\"\n"
    "msgstr \"Titel\"\n"
    "\n"
    "msgctxt \"help/1/1\"\n"
    "msgid \"Body\"\n"
    "msgstr \"\"\n"
    "\"Zeile 1\\n\"\n"
    "\"\\n\"\n"
    "\"#12Verweis# und $ Dollar\"\n"
    "\n"
    "msgctxt \"help/2/0\"\n"
    "msgid \"@1\"\n"
    "msgstr \"\"\n"
    "\n"
    "msgctxt \"help/2/1\"\n"
    "msgid \"@1\"\n"
    "msgstr \"\"\n"
    "\n"
    "msgctxt \"help/3/0\"\n"
    "msgid \"@1\"\n"
    "msgstr \"Eigener Titel\"\n"
    "\n"
    "msgctxt \"help/3/1\"\n"
    "msgid \"@1\"\n"
    "msgstr \"Eigener Text\"\n";

static void test_translator_input_reaches_the_engine_as_intended(void)
{
    struct c2_text_bundle_entry entries[1];
    size_t size;
    const unsigned char *c2eng;
    const unsigned char *help;
    unsigned int page1;
    unsigned int page2;
    unsigned int page3;

    entries[0].tag = "xx";
    entries[0].data = (const unsigned char *)tricky_po;
    entries[0].size = sizeof(tricky_po) - 1;
    c2_port_text_use_bundle(entries, 1);
    TEST_ASSERT_EQUAL_INT(1, c2_port_text_language_count());
    TEST_ASSERT_EQUAL_STRING("Pr\xc3\xbc" "fung", c2_port_text_language(0)->name);
    TEST_ASSERT_TRUE(c2_port_text_select("xx"));

    c2eng = c2_port_text_c2eng(&size);
    TEST_ASSERT_NOT_NULL(c2eng);
    /* escapes and UTF-8 -> CP437: ä is 0x84 */
    TEST_ASSERT_EQUAL_STRING("D\x84tei \"quoted\" back\\slash tab\tend", text_string(c2eng, 1, 0));
    /* fuzzy and empty fall back to the English msgid */
    TEST_ASSERT_EQUAL_STRING("New Game", text_string(c2eng, 1, 1));
    TEST_ASSERT_EQUAL_STRING("Load", text_string(c2eng, 1, 2));
    /* continuation lines join; ß is 0xe1, « » are 0xae 0xaf (in CP437, no glyph) */
    TEST_ASSERT_EQUAL_STRING("Gro\xe1" "e \xae" "Anf\x81hrung\xaf", text_string(c2eng, 1, 3));
    /* outside CP437 becomes '?'; no-break space is 0xff */
    TEST_ASSERT_EQUAL_STRING("? 1\xff" "000 ?", text_string(c2eng, 1, 4));

    help = c2_port_text_helpeng(&size);
    TEST_ASSERT_NOT_NULL(help);
    page1 = u32(help + 8 + 1 * 0x3a);
    page2 = u32(help + 8 + 2 * 0x3a);
    page3 = u32(help + 8 + 3 * 0x3a);
    TEST_ASSERT_EQUAL_STRING("Titel", (const char *)help + page1);
    /* \n becomes the engine's $ break; a literal $ stays a break; links intact */
    TEST_ASSERT_EQUAL_STRING("Zeile 1$$#12Verweis# und $ Dollar",
                             (const char *)help + page1 + strlen("Titel") + 1);
    /* an untouched @1 reference shares page 1's text */
    TEST_ASSERT_EQUAL_UINT32(page1, page2);
    /* a reference replaced by text gets its own page */
    TEST_ASSERT_NOT_EQUAL(page1, page3);
    TEST_ASSERT_EQUAL_STRING("Eigener Titel", (const char *)help + page3);
    TEST_ASSERT_EQUAL_STRING("Eigener Text", (const char *)help + page3 + strlen("Eigener Titel") + 1);
    /* pages the translation does not mention have no text */
    TEST_ASSERT_EQUAL_UINT32(0, u32(help + 8 + 4 * 0x3a));

    c2_port_text_use_bundle(NULL, 0);
}

static void test_malformed_translation_fails_closed(void)
{
    static const char broken[] =
        "msgid \"\"\nmsgstr \"\"\n\"X-C2-Name: Broken\\n\"\n\n"
        "msgctxt \"0x1/0\"\nmsgid \"File\"\nmsgstr \"unterminated\n";
    struct c2_text_bundle_entry entries[1];
    size_t size;

    entries[0].tag = "xx";
    entries[0].data = (const unsigned char *)broken;
    entries[0].size = sizeof(broken) - 1;
    c2_port_text_use_bundle(entries, 1);
    TEST_ASSERT_TRUE(c2_port_text_select("xx"));
    TEST_ASSERT_NULL(c2_port_text_c2eng(&size));
    c2_port_text_use_bundle(NULL, 0);
}

static void dump(const char *dir, const char *tag)
{
    char path[1024];
    FILE *f;
    size_t size;
    const unsigned char *data;

    c2_port_text_select(tag);
    data = c2_port_text_c2eng(&size);
    snprintf(path, sizeof(path), "%s/%s.c2.eng", dir, tag);
    f = fopen(path, "wb");
    if (f) { fwrite(data, 1, size, f); fclose(f); }
    data = c2_port_text_helpeng(&size);
    snprintf(path, sizeof(path), "%s/%s.help.eng", dir, tag);
    f = fopen(path, "wb");
    if (f) { fwrite(data, 1, size, f); fclose(f); }
}

/* With C2_TEXT_DUMP_DIR set, write every language's rebuilt files so
 * tests/test_c2_text.py can compare them with the Python reference. */
static void test_dump_for_reference_comparison(void)
{
    const char *dir = getenv("C2_TEXT_DUMP_DIR");
    int i;

    if (!dir) TEST_IGNORE_MESSAGE("C2_TEXT_DUMP_DIR not set");
    for (i = 0; i < c2_port_text_language_count(); i++) dump(dir, c2_port_text_language(i)->tag);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_bundle_lists_every_language_with_its_name);
    RUN_TEST(test_detects_the_language_from_the_disc_text);
    RUN_TEST(test_detection_selects_unless_overridden);
    RUN_TEST(test_english_textfile_has_the_1996_layout);
    RUN_TEST(test_german_text_is_transcoded_to_the_font_encoding);
    RUN_TEST(test_help_pages_and_aliases);
    RUN_TEST(test_readfile_hooks_serve_offsets);
    RUN_TEST(test_translator_input_reaches_the_engine_as_intended);
    RUN_TEST(test_malformed_translation_fails_closed);
    RUN_TEST(test_dump_for_reference_comparison);
    return UNITY_END();
}
