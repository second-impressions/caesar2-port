/*
 * The game-data library (docs/game-data-library.md) against synthetic
 * sources shaped like the real ones: where each file goes, which copy wins,
 * that the order of imports does not matter, the Mac discs and their audio,
 * export and re-import, removal and the migration of old caches.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <unity/unity.h>
#include <SDL3/SDL.h>

#include "c2_import.h"
#include "c2_library.h"

#define ROOT "c2-library-test-data"

/* ------------------------------------------------------------------ */
/* Files                                                               */

static SDL_EnumerationResult SDLCALL remove_child(void *userdata, const char *dirname,
                                                  const char *fname)
{
    char path[2048];
    SDL_PathInfo info;
    size_t n = strlen(dirname);
    (void)userdata;
    snprintf(path, sizeof(path), "%s%s%s", dirname, n && dirname[n - 1] == '/' ? "" : "/", fname);
    if (SDL_GetPathInfo(path, &info) && info.type == SDL_PATHTYPE_DIRECTORY) {
        SDL_EnumerateDirectory(path, remove_child, NULL);
    }
    SDL_RemovePath(path);
    return SDL_ENUM_CONTINUE;
}

static void remove_tree(const char *path)
{
    SDL_EnumerateDirectory(path, remove_child, NULL);
    SDL_RemovePath(path);
}

static void make_parents(const char *path)
{
    char copy[2048];
    char *p;
    snprintf(copy, sizeof(copy), "%s", path);
    for (p = copy + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            SDL_CreateDirectory(copy);
            *p = '/';
        }
    }
}

static void write_bytes(const char *path, const void *data, size_t size)
{
    FILE *file;
    make_parents(path);
    file = fopen(path, "wb");
    TEST_ASSERT_NOT_NULL_MESSAGE(file, path);
    TEST_ASSERT_EQUAL_size_t(size, fwrite(data, 1, size, file));
    TEST_ASSERT_EQUAL_INT(0, fclose(file));
}

static void write_text(const char *path, const char *text)
{
    write_bytes(path, text, strlen(text));
}

static size_t read_bytes(const char *path, unsigned char *buffer, size_t capacity)
{
    FILE *file = fopen(path, "rb");
    size_t got;
    if (!file) return 0;
    got = fread(buffer, 1, capacity, file);
    fclose(file);
    return got;
}

static int exists(const char *path)
{
    return SDL_GetPathInfo(path, NULL);
}

static void assert_content(const char *path, const char *expected)
{
    unsigned char buffer[256];
    size_t got = read_bytes(path, buffer, sizeof(buffer) - 1);
    buffer[got] = 0;
    TEST_ASSERT_TRUE_MESSAGE(exists(path), path);
    TEST_ASSERT_EQUAL_STRING_MESSAGE(expected, (const char *)buffer, path);
}

/* C2.ENG in the recovered Textfile layout: 24-bit offsets at +8, list 1
 * word 0 the File menu title (what the language is detected from), list
 * 0x0b word 0 the version line. */
static void write_c2eng(const char *path, const char *file_menu, const char *version)
{
    unsigned char buffer[512];
    size_t pos = 8 + 16 * 4;
    int list;
    memset(buffer, 0, sizeof(buffer));
    memcpy(buffer, "Textfile", 8);
    for (list = 0; list < 16; list++) {
        const char *text = list == 1 ? file_menu : list == 0x0b ? version : "x";
        buffer[8 + list * 4] = (unsigned char)(pos & 0xff);
        buffer[9 + list * 4] = (unsigned char)(pos >> 8);
        memcpy(buffer + pos, text, strlen(text) + 1);
        pos += strlen(text) + 1;
    }
    write_bytes(path, buffer, pos);
}

static void write_smk(const char *path, unsigned width, unsigned height, size_t size)
{
    unsigned char buffer[64];
    memset(buffer, 0, sizeof(buffer));
    memcpy(buffer, "SMK2", 4);
    buffer[4] = (unsigned char)width; buffer[5] = (unsigned char)(width >> 8);
    buffer[8] = (unsigned char)height; buffer[9] = (unsigned char)(height >> 8);
    TEST_ASSERT_TRUE(size <= sizeof(buffer));
    write_bytes(path, buffer, size < 12 ? 12 : size);
}

static unsigned movie_width(const char *path)
{
    unsigned char buffer[12];
    if (read_bytes(path, buffer, sizeof(buffer)) != sizeof(buffer)) return 0;
    return (unsigned)(buffer[4] | (buffer[5] << 8));
}

/* A mono 8-bit AIFF, the Mac discs' speech and music: signed samples. */
static void write_aiff(const char *path, const unsigned char *samples, size_t count)
{
    unsigned char buffer[256];
    size_t n = 0;
    size_t form = 4 + 8 + 18 + 8 + 8 + count;
#define PUT32(v) do { buffer[n++] = (unsigned char)((v) >> 24); buffer[n++] = (unsigned char)((v) >> 16); \
                      buffer[n++] = (unsigned char)((v) >> 8); buffer[n++] = (unsigned char)(v); } while (0)
    memcpy(buffer + n, "FORM", 4); n += 4; PUT32(form);
    memcpy(buffer + n, "AIFF", 4); n += 4;
    memcpy(buffer + n, "COMM", 4); n += 4; PUT32(18);
    buffer[n++] = 0; buffer[n++] = 1;               /* channels */
    PUT32(count);                                   /* frames */
    buffer[n++] = 0; buffer[n++] = 8;               /* bits */
    memcpy(buffer + n, "\x40\x0d\xac\x44\x00\x00\x00\x00\x00\x00", 10); n += 10; /* 22050 Hz */
    memcpy(buffer + n, "SSND", 4); n += 4; PUT32(8 + count);
    PUT32(0); PUT32(0);
    memcpy(buffer + n, samples, count); n += count;
#undef PUT32
    write_bytes(path, buffer, n);
}

/* Fifty ordinary base files: what makes a tree complete enough to play. */
static void write_common(const char *base, const char *marker)
{
    char path[1024];
    int i;
    for (i = 0; i < 50; i++) {
        snprintf(path, sizeof(path), "%s/COMMON%02d.DAT", base, i);
        write_text(path, marker);
    }
}

/* A DOS CD: HD/ with the base files and the intro, media beside it. */
static void make_dos_disc(const char *root, const char *file_menu, const char *version,
                          const char *marker)
{
    char path[1024];
    snprintf(path, sizeof(path), "%s/HD/C2.ENG", root); write_c2eng(path, file_menu, version);
    snprintf(path, sizeof(path), "%s/HD/HELP.ENG", root); write_text(path, marker);
    snprintf(path, sizeof(path), "%s/HD", root); write_common(path, "dos");
    snprintf(path, sizeof(path), "%s/HD/A09.WAV", root); write_text(path, marker);
    snprintf(path, sizeof(path), "%s/HD/CAESAR.OPL", root); write_text(path, "bank");
    snprintf(path, sizeof(path), "%s/HD/HISTORY.DAT", root); write_text(path, "player");
    snprintf(path, sizeof(path), "%s/HD/INTRO.SMK", root); write_smk(path, 640, 480, 20);
    snprintf(path, sizeof(path), "%s/RAW/A01.RAW", root); write_text(path, marker);
    snprintf(path, sizeof(path), "%s/XMI/CITYPROV.XMI", root); write_text(path, "score");
    snprintf(path, sizeof(path), "%s/PL8/AFORUM.PL8", root); write_text(path, marker);
    snprintf(path, sizeof(path), "%s/PL8/SHARED.PL8", root); write_text(path, "dos");
    snprintf(path, sizeof(path), "%s/SMK/BATTWON.SMK", root); write_smk(path, 320, 152, 20);
    snprintf(path, sizeof(path), "%s/SMK/MESSAGE.SMK", root); write_smk(path, 320, 152, 20);
}

/* The Windows 95 tree of the hybrid discs, or of the 1998 pressing. */
static void make_windows_tree(const char *base_parent, const char *file_menu, const char *marker)
{
    char path[1024];
    snprintf(path, sizeof(path), "%s/HD/C2.ENG", base_parent);
    write_c2eng(path, file_menu, "Caesar II - version 1.02 - 2nd Feb 96");
    snprintf(path, sizeof(path), "%s/HD/HELP.ENG", base_parent); write_text(path, marker);
    snprintf(path, sizeof(path), "%s/HD/C2_START.DAT", base_parent); write_text(path, "start");
    snprintf(path, sizeof(path), "%s/HD", base_parent); write_common(path, "windows");
    snprintf(path, sizeof(path), "%s/RAW/A01.RAW", base_parent); write_text(path, marker);
    snprintf(path, sizeof(path), "%s/RAW/CITYPRO0.RAW", base_parent); write_text(path, "recording");
    snprintf(path, sizeof(path), "%s/PL8/SHARED.PL8", base_parent); write_text(path, "windows");
    snprintf(path, sizeof(path), "%s/SMK/BATTWON.SMK", base_parent); write_smk(path, 500, 240, 20);
    snprintf(path, sizeof(path), "%s/SMK/MESSAGE.SMK", base_parent); write_smk(path, 500, 240, 20);
    snprintf(path, sizeof(path), "%s/SMK/INTRO.SMK", base_parent); write_smk(path, 640, 480, 30);
}

static int import(const char *game_data, const char *source)
{
    char error[512] = "";
    int ok = c2_library_import(game_data, source, NULL, error, sizeof(error));
    TEST_ASSERT_TRUE_MESSAGE(ok, error);
    return ok;
}

void setUp(void)
{
    remove_tree(ROOT);
    SDL_CreateDirectory(ROOT);
}

void tearDown(void)
{
    remove_tree(ROOT);
}

/* ------------------------------------------------------------------ */
/* Sorting                                                             */

static void test_a_dos_disc_is_sorted_into_places(void)
{
    struct c2_library_summary s;
    make_dos_disc(ROOT "/disc", "File", "Caesar II - Version 1.1", "en11");
    import(ROOT "/data", ROOT "/disc");

    /* text, speech and the files that differ between releases */
    assert_content(ROOT "/data/library/language/en/HELP.ENG", "en11");
    assert_content(ROOT "/data/library/language/en/A09.WAV", "en11");
    assert_content(ROOT "/data/library/language/en/RAW/A01.RAW", "en11");
    assert_content(ROOT "/data/library/language/en/PL8/AFORUM.PL8", "en11");
    /* what every release shares */
    assert_content(ROOT "/data/library/common/COMMON00.DAT", "dos");
    assert_content(ROOT "/data/library/common/PL8/SHARED.PL8", "dos");
    /* the 1995 scores with their synthesizer bank; the movies, the intro
     * among them although the DOS disc keeps it with the base files */
    assert_content(ROOT "/data/library/music/dos/CAESAR.OPL", "bank");
    assert_content(ROOT "/data/library/music/dos/XMI/CITYPROV.XMI", "score");
    TEST_ASSERT_EQUAL_UINT(640, movie_width(ROOT "/data/library/video/SMK/INTRO.SMK"));
    TEST_ASSERT_TRUE(exists(ROOT "/data/library/video/SMK/BATTWON.SMK"));
    /* never a player's own file */
    TEST_ASSERT_FALSE(exists(ROOT "/data/library/common/HISTORY.DAT"));
    /* the format marker, first line */
    {
        unsigned char marker[32];
        size_t got = read_bytes(ROOT "/data/library/C2ASSETS", marker, 17);
        TEST_ASSERT_EQUAL_size_t(17, got);
        TEST_ASSERT_EQUAL_MEMORY("caesar2-assets 1\n", marker, 17);
    }

    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_TRUE(s.playable);
    TEST_ASSERT_EQUAL_INT(1, s.language_count);
    TEST_ASSERT_EQUAL_STRING("en", s.languages[0].tag);
    TEST_ASSERT_TRUE(s.languages[0].speech);
    TEST_ASSERT_EQUAL_STRING("Version 1.1", s.languages[0].version);
    TEST_ASSERT_TRUE(s.music_dos);
    TEST_ASSERT_FALSE(s.music_windows);
    /* the summary the browser page reads */
    TEST_ASSERT_TRUE(exists(ROOT "/data/local/summary"));
}

static void test_a_hybrid_disc_adds_the_recordings_and_larger_scaled_movies(void)
{
    struct c2_library_summary s;
    make_dos_disc(ROOT "/disc", "File", "Caesar II - version 1.2 ", "en12");
    make_windows_tree(ROOT "/disc/C2WIN95", "File", "w95");
    import(ROOT "/data", ROOT "/disc");

    assert_content(ROOT "/data/library/music/windows/RAW/CITYPRO0.RAW", "recording");
    /* BATTWON is scaled into the VGA box, so the 500x240 copy wins;
     * MESSAGE and the intro are drawn 1:1 and keep their DOS copies. */
    TEST_ASSERT_EQUAL_UINT(500, movie_width(ROOT "/data/library/video/SMK/BATTWON.SMK"));
    TEST_ASSERT_EQUAL_UINT(320, movie_width(ROOT "/data/library/video/SMK/MESSAGE.SMK"));
    TEST_ASSERT_EQUAL_UINT(640, movie_width(ROOT "/data/library/video/SMK/INTRO.SMK"));
    /* The Windows tree's remapped art and speech never replace DOS files. */
    assert_content(ROOT "/data/library/common/PL8/SHARED.PL8", "dos");
    assert_content(ROOT "/data/library/language/en/RAW/A01.RAW", "en12");
    TEST_ASSERT_FALSE(exists(ROOT "/data/library/common/C2_START.DAT"));

    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_TRUE(s.music_dos && s.music_windows);
    TEST_ASSERT_EQUAL_INT(1, s.movies_enhanced);
}

static void test_the_windows_only_pressing_is_used_until_dos_files_arrive(void)
{
    struct c2_library_summary s;
    /* 1998: the Windows tree at the root, and once more in C2WIN95/. */
    make_windows_tree(ROOT "/w98", "File", "w98");
    make_windows_tree(ROOT "/w98/C2WIN95", "File", "w98");
    import(ROOT "/data", ROOT "/w98");
    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_TRUE(s.playable);
    TEST_ASSERT_TRUE(s.languages[0].windows);
    assert_content(ROOT "/data/library/common/PL8/SHARED.PL8", "windows");
    TEST_ASSERT_EQUAL_UINT(500, movie_width(ROOT "/data/library/video/SMK/MESSAGE.SMK"));

    make_dos_disc(ROOT "/disc", "File", "Caesar II - Version 1.0A", "en10");
    import(ROOT "/data", ROOT "/disc");
    /* Better copies replace, one file at a time; the language folder is a
     * DOS release now. */
    assert_content(ROOT "/data/library/common/PL8/SHARED.PL8", "dos");
    TEST_ASSERT_EQUAL_UINT(320, movie_width(ROOT "/data/library/video/SMK/MESSAGE.SMK"));
    TEST_ASSERT_EQUAL_UINT(500, movie_width(ROOT "/data/library/video/SMK/BATTWON.SMK"));
    assert_content(ROOT "/data/library/language/en/HELP.ENG", "en10");
    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_FALSE(s.languages[0].windows);
}

static void test_a_language_folder_holds_one_release_and_the_better_one_wins(void)
{
    struct c2_library_summary s;
    char path[256];
    make_dos_disc(ROOT "/v12", "File", "Caesar II - version 1.2 ", "en12");
    snprintf(path, sizeof(path), "%s/PL8/TUT_12B.PL8", ROOT "/v12");
    write_text(path, "en12");
    make_dos_disc(ROOT "/v11", "File", "Caesar II - Version 1.1", "en11");
    make_dos_disc(ROOT "/de", "Datei", "Caesar II - Version 1.0", "de10");

    import(ROOT "/data", ROOT "/v12");
    import(ROOT "/data", ROOT "/v11");
    /* 1.1 is older: nothing of it replaces 1.2 */
    assert_content(ROOT "/data/library/language/en/HELP.ENG", "en12");
    assert_content(ROOT "/data/library/language/en/PL8/TUT_12B.PL8", "en12");

    import(ROOT "/data", ROOT "/de");
    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_EQUAL_INT(2, s.language_count);
    assert_content(ROOT "/data/library/language/de/RAW/A01.RAW", "de10");

    /* A folder with only the two text files (the community German text
     * patch) adds nothing over German with speech. */
    snprintf(path, sizeof(path), "%s/C2.ENG", ROOT "/patch");
    write_c2eng(path, "Datei", "Caesar II - Version 1.0");
    snprintf(path, sizeof(path), "%s/HELP.ENG", ROOT "/patch");
    write_text(path, "patch");
    import(ROOT "/data", ROOT "/patch");
    assert_content(ROOT "/data/library/language/de/HELP.ENG", "de10");

    /* Replacing is whole: the 1.1 folder does not keep 1.2's extra file. */
    remove_tree(ROOT "/data");
    import(ROOT "/data", ROOT "/v11");
    import(ROOT "/data", ROOT "/v12");
    import(ROOT "/data", ROOT "/v11");
    assert_content(ROOT "/data/library/language/en/HELP.ENG", "en12");
    make_dos_disc(ROOT "/v13", "File", "Caesar II - version 1.3", "en13");
    import(ROOT "/data", ROOT "/v13");
    TEST_ASSERT_FALSE(exists(ROOT "/data/library/language/en/PL8/TUT_12B.PL8"));
}

static void test_the_later_pressing_breaks_a_tie_of_equal_versions(void)
{
    /* The German original and its 1996 rerelease both say "Version 1.0";
     * the rerelease carries the Windows 95 tree. */
    make_dos_disc(ROOT "/first", "Datei", "Caesar II - Version 1.0", "original");
    make_dos_disc(ROOT "/later", "Datei", "Caesar II - Version 1.0", "rerelease");
    make_windows_tree(ROOT "/later/C2WIN95", "Datei", "w95");
    import(ROOT "/a", ROOT "/first");
    import(ROOT "/a", ROOT "/later");
    import(ROOT "/b", ROOT "/later");
    import(ROOT "/b", ROOT "/first");
    assert_content(ROOT "/a/library/language/de/HELP.ENG", "rerelease");
    assert_content(ROOT "/b/library/language/de/HELP.ENG", "rerelease");
}

/* ------------------------------------------------------------------ */
/* The Mac discs                                                       */

/* A Mac install: one flat Data/HD, AIFF speech and music. */
static void make_mac_install(const char *root)
{
    static const unsigned char speech[4] = { 0x00, 0x7f, 0x80, 0xff };
    static const unsigned char music[3] = { 0x10, 0x20, 0x30 };
    char path[1024];
    snprintf(path, sizeof(path), "%s/Caesar II Large Install/Data/HD/C2.ENG", root);
    write_c2eng(path, "File", "Caesar II - Macintosh Version 1.0");
    snprintf(path, sizeof(path), "%s/Caesar II Large Install/Data/HD/HELP.ENG", root);
    write_text(path, "mac");
    snprintf(path, sizeof(path), "%s/Caesar II Large Install/Data/HD", root);
    write_common(path, "mac");
    snprintf(path, sizeof(path), "%s/Caesar II Large Install/Data/HD/A01.RAW", root);
    write_aiff(path, speech, sizeof(speech));
    snprintf(path, sizeof(path), "%s/Caesar II Large Install/Data/HD/PROVINC3.XMI", root);
    write_aiff(path, music, sizeof(music));
    snprintf(path, sizeof(path), "%s/Caesar II Large Install/Data/HD/BATTWON.SMK", root);
    write_smk(path, 500, 240, 40);
    snprintf(path, sizeof(path), "%s/Caesar II Large Install/Data/HD/INTRONEW.SMK", root);
    write_smk(path, 640, 480, 12);
}

static void test_a_mac_install_gives_its_movies_music_and_speech(void)
{
    struct c2_library_summary s;
    unsigned char bytes[8];
    make_mac_install(ROOT "/mac");
    import(ROOT "/data", ROOT "/mac");

    /* PROVINC3 is the Windows version's CITYPRO0: AIFF's signed samples
     * become the PC's unsigned ones. */
    TEST_ASSERT_EQUAL_size_t(3, read_bytes(ROOT "/data/library/music/windows/RAW/CITYPRO0.RAW",
                                           bytes, sizeof(bytes)));
    TEST_ASSERT_EQUAL_HEX8(0x90, bytes[0]);
    TEST_ASSERT_EQUAL_HEX8(0xb0, bytes[2]);
    TEST_ASSERT_EQUAL_size_t(4, read_bytes(ROOT "/data/library/language/en/RAW/A01.RAW",
                                           bytes, sizeof(bytes)));
    TEST_ASSERT_EQUAL_HEX8(0x80, bytes[0]);
    TEST_ASSERT_EQUAL_HEX8(0x7f, bytes[3]);
    TEST_ASSERT_EQUAL_UINT(500, movie_width(ROOT "/data/library/video/SMK/BATTWON.SMK"));
    TEST_ASSERT_EQUAL_UINT(640, movie_width(ROOT "/data/library/video/SMK/INTRO.SMK"));
    /* A Mac disc has no sound-effect files and differs in a third of its
     * art: it cannot be played on its own, and says so. */
    TEST_ASSERT_FALSE(exists(ROOT "/data/library/common/COMMON00.DAT"));
    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_FALSE(s.playable);
    TEST_ASSERT_TRUE(s.languages[0].mac);
    TEST_ASSERT_TRUE(s.music_windows);

    /* A PC disc then supplies the rest; its intro (the DOS one) wins, the
     * Mac copy of a scaled movie stays over the DOS 320x152. */
    make_dos_disc(ROOT "/disc", "File", "Caesar II - Version 1.1", "en11");
    import(ROOT "/data", ROOT "/disc");
    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_TRUE(s.playable);
    TEST_ASSERT_FALSE(s.languages[0].mac);
    assert_content(ROOT "/data/library/language/en/HELP.ENG", "en11");
    TEST_ASSERT_EQUAL_UINT(500, movie_width(ROOT "/data/library/video/SMK/BATTWON.SMK"));
    {
        unsigned char movie[64];
        /* the DOS intro (20 bytes here), not the Mac INTRONEW (12) */
        TEST_ASSERT_EQUAL_size_t(20, read_bytes(ROOT "/data/library/video/SMK/INTRO.SMK", movie, sizeof(movie)));
    }
}

/* ------------------------------------------------------------------ */
/* HFS                                                                 */

static void be16(unsigned char *p, unsigned v) { p[0] = (unsigned char)(v >> 8); p[1] = (unsigned char)v; }
static void be32(unsigned char *p, unsigned long v)
{
    p[0] = (unsigned char)(v >> 24); p[1] = (unsigned char)(v >> 16);
    p[2] = (unsigned char)(v >> 8); p[3] = (unsigned char)v;
}

/* A catalog leaf record: key (parent, name), then a folder or file. */
static size_t hfs_record(unsigned char *node, size_t at, unsigned long parent, const char *name,
                         int folder, unsigned long id, unsigned long start_block,
                         unsigned long length)
{
    size_t data;
    node[at] = (unsigned char)(6 + strlen(name));   /* key length: reserved, parent, name */
    be32(node + at + 2, parent);
    node[at + 6] = (unsigned char)strlen(name);
    memcpy(node + at + 7, name, strlen(name));
    data = at + 1 + node[at];
    data += data & 1;
    memset(node + data, 0, 102);
    if (folder) {
        node[data] = 1;
        be32(node + data + 6, id);
        return data + 70 - at;
    }
    node[data] = 2;
    be32(node + data + 20, id);
    be32(node + data + 26, length);
    be16(node + data + 74, (unsigned)start_block);
    be16(node + data + 76, (unsigned)((length + 511) / 512));
    return data + 102 - at;
}

/* An Apple partition map and one HFS volume holding HD/C2.ENG, HD/HELP.ENG
 * and HD/HELLO.DAT: what the Macintosh CDs look like to the reader. */
static unsigned char *make_hfs(size_t *size_out)
{
    const size_t partition = 64 * 512;       /* partition starts at block 64 */
    const size_t size = partition + 64 * 512;
    unsigned char *image = calloc(1, size);
    unsigned char *mdb = image + partition + 1024;
    unsigned char *tree = image + partition + 8 * 512;   /* catalog at allocation block 0 */
    unsigned char *leaf = tree + 1024;
    unsigned char *files = image + partition + 16 * 512; /* allocation block 8 */
    size_t at = 14;
    unsigned offsets[5];
    int n = 0;
    int i;

    image[0] = 'E'; image[1] = 'R';
    image[512] = 'P'; image[513] = 'M'; be32(image + 516, 2);
    be32(image + 520, 1); be32(image + 524, 2);
    memcpy(image + 560, "Apple_partition_map", 19);
    image[1024] = 'P'; image[1025] = 'M'; be32(image + 1028, 2);
    be32(image + 1032, 64); be32(image + 1036, 64);
    memcpy(image + 1072, "Apple_HFS", 9);

    mdb[0] = 'B'; mdb[1] = 'D';
    be16(mdb + 18, 48);                 /* allocation blocks */
    be32(mdb + 20, 512);                /* allocation block size */
    be16(mdb + 28, 8);                  /* first allocation block, in sectors */
    be32(mdb + 146, 2 * 1024);          /* catalog size: two 1 KiB nodes */
    be16(mdb + 150, 0); be16(mdb + 152, 4);

    be16(tree + 14 + 18, 1024);         /* node size */
    be32(tree + 14 + 10, 1);            /* first leaf */
    leaf[8] = 0xff;                     /* a leaf */
    offsets[n++] = 14;
    at += hfs_record(leaf, at, 1, "Volume", 1, 2, 0, 0);
    offsets[n++] = (unsigned)at;
    at += hfs_record(leaf, at, 2, "HD", 1, 16, 0, 0);
    offsets[n++] = (unsigned)at;
    at += hfs_record(leaf, at, 16, "C2.ENG", 0, 20, 8, 4);
    offsets[n++] = (unsigned)at;
    at += hfs_record(leaf, at, 16, "HELP.ENG", 0, 21, 9, 4);
    offsets[n++] = (unsigned)at;
    at += hfs_record(leaf, at, 16, "Hello.dat", 0, 22, 10, 5);
    be16(leaf + 10, (unsigned)n);
    for (i = 0; i < n; i++) be16(leaf + 1024 - 2 * (i + 1), offsets[i]);
    memcpy(files, "text", 4);
    memcpy(files + 512, "help", 4);
    memcpy(files + 1024, "hello", 5);
    *size_out = size;
    return image;
}

static void test_the_hfs_reader_catalogues_a_mac_disc_image(void)
{
    size_t size;
    unsigned char *image = make_hfs(&size);
    char root[512];
    char error[256] = "";
    int in_place = 1;
    write_bytes(ROOT "/mac.toast", image, size);
    free(image);
    TEST_ASSERT_TRUE_MESSAGE(c2_import_stage(ROOT "/mac.toast", ROOT "/stage", NULL, root,
                                             sizeof(root), &in_place, error, sizeof(error)), error);
    TEST_ASSERT_FALSE(in_place);
    assert_content(ROOT "/stage/HD/C2.ENG", "text");
    assert_content(ROOT "/stage/HD/HELP.ENG", "help");
    assert_content(ROOT "/stage/HD/HELLO.DAT", "hello");
}

/* ------------------------------------------------------------------ */
/* The library as a whole                                             */

static uint64_t tree_fingerprint(const char *root)
{
    char **names;
    int count = 0;
    int i;
    uint64_t hash = 1469598103934665603ULL;
    names = SDL_GlobDirectory(root, NULL, 0, &count);
    TEST_ASSERT_NOT_NULL(names);
    for (i = 0; i < count; i++) {
        char path[2048];
        unsigned char buffer[4096];
        size_t got;
        size_t k;
        const char *p;
        snprintf(path, sizeof(path), "%s/%s", root, names[i]);
        if (!SDL_GetPathInfo(path, NULL)) continue;
        /* order-independent: sum of per-file hashes */
        {
            uint64_t h = 1469598103934665603ULL;
            for (p = names[i]; *p; p++) { h ^= (unsigned char)*p; h *= 1099511628211ULL; }
            got = read_bytes(path, buffer, sizeof(buffer));
            for (k = 0; k < got; k++) { h ^= buffer[k]; h *= 1099511628211ULL; }
            hash += h;
        }
    }
    SDL_free(names);
    return hash;
}

static void test_the_order_of_imports_does_not_matter(void)
{
    make_dos_disc(ROOT "/en", "File", "Caesar II - version 1.2 ", "en12");
    make_windows_tree(ROOT "/en/C2WIN95", "File", "w95");
    make_dos_disc(ROOT "/de", "Datei", "Caesar II - Version 1.0", "de10");
    make_mac_install(ROOT "/mac");
    import(ROOT "/a", ROOT "/en");
    import(ROOT "/a", ROOT "/de");
    import(ROOT "/a", ROOT "/mac");
    import(ROOT "/b", ROOT "/mac");
    import(ROOT "/b", ROOT "/de");
    import(ROOT "/b", ROOT "/en");
    TEST_ASSERT_EQUAL_UINT64(tree_fingerprint(ROOT "/a/library"), tree_fingerprint(ROOT "/b/library"));
    /* and importing again changes nothing */
    import(ROOT "/b", ROOT "/de");
    TEST_ASSERT_EQUAL_UINT64(tree_fingerprint(ROOT "/a/library"), tree_fingerprint(ROOT "/b/library"));
}

static void test_an_export_is_the_library_zipped_and_imports_back(void)
{
    char error[512] = "";
    unsigned char head[64];
    make_dos_disc(ROOT "/en", "File", "Caesar II - version 1.2 ", "en12");
    make_dos_disc(ROOT "/de", "Datei", "Caesar II - Version 1.0", "de10");
    import(ROOT "/a", ROOT "/en");
    import(ROOT "/a", ROOT "/de");
    TEST_ASSERT_TRUE_MESSAGE(c2_library_export(ROOT "/a", ROOT "/all.c2assets", NULL,
                                               error, sizeof(error)), error);
    /* a plain ZIP whose first entry is the format marker */
    TEST_ASSERT_EQUAL_size_t(64, read_bytes(ROOT "/all.c2assets", head, sizeof(head)));
    TEST_ASSERT_EQUAL_MEMORY("PK\x03\x04", head, 4);
    TEST_ASSERT_EQUAL_MEMORY("C2ASSETS", head + 30, 8);
    import(ROOT "/b", ROOT "/all.c2assets");
    TEST_ASSERT_EQUAL_UINT64(tree_fingerprint(ROOT "/a/library"), tree_fingerprint(ROOT "/b/library"));
    /* an unzipped one reads the same */
    import(ROOT "/c", ROOT "/a/library");
    TEST_ASSERT_EQUAL_UINT64(tree_fingerprint(ROOT "/a/library"), tree_fingerprint(ROOT "/c/library"));
}

static void test_a_newer_format_is_refused_by_name(void)
{
    char error[512] = "";
    write_text(ROOT "/future/C2ASSETS", "caesar2-assets 2\n");
    write_text(ROOT "/future/common/A.DAT", "x");
    TEST_ASSERT_FALSE(c2_library_import(ROOT "/data", ROOT "/future", NULL, error, sizeof(error)));
    TEST_ASSERT_NOT_NULL_MESSAGE(strstr(error, "newer"), error);
}

static void test_removal_leaves_everything_else(void)
{
    struct c2_library_summary s;
    make_dos_disc(ROOT "/en", "File", "Caesar II - Version 1.1", "en11");
    import(ROOT "/data", ROOT "/en");
    write_text(ROOT "/data/../keep.sav", "save");
    TEST_ASSERT_TRUE(c2_library_remove(ROOT "/data"));
    TEST_ASSERT_FALSE(exists(ROOT "/data/library"));
    TEST_ASSERT_FALSE(exists(ROOT "/data/local"));
    assert_content(ROOT "/keep.sav", "save");
    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_EQUAL_INT(0, s.language_count);
    TEST_ASSERT_FALSE(s.playable);
}

static void test_old_caches_are_migrated_and_removed(void)
{
    struct c2_library_summary s;
    char error[256];
    make_dos_disc(ROOT "/data/0123456789abcdef", "File", "Caesar II - Version 1.1", "old");
    write_text(ROOT "/data/0123456789abcdef/.complete", "");
    make_dos_disc(ROOT "/data/fedcba9876543210", "Datei", "Caesar II - Version 1.0", "old");
    /* no marker: an unfinished extraction */
    TEST_ASSERT_EQUAL_INT(1, c2_library_migrate(ROOT "/data", NULL, error, sizeof(error)));
    TEST_ASSERT_FALSE(exists(ROOT "/data/0123456789abcdef"));
    TEST_ASSERT_FALSE(exists(ROOT "/data/fedcba9876543210"));
    TEST_ASSERT_TRUE(c2_library_describe(ROOT "/data", &s));
    TEST_ASSERT_EQUAL_INT(1, s.language_count);
    TEST_ASSERT_TRUE(s.playable);
}

static void test_the_runtime_reads_the_chosen_speech_first(void)
{
    struct c2_asset_layout layout;
    char error[256];
    make_dos_disc(ROOT "/en", "File", "Caesar II - Version 1.1", "en11");
    make_dos_disc(ROOT "/de", "Datei", "Caesar II - Version 1.0", "de10");
    import(ROOT "/data", ROOT "/en");
    import(ROOT "/data", ROOT "/de");
    TEST_ASSERT_TRUE_MESSAGE(c2_library_layout(ROOT "/data", "de", &layout, error, sizeof(error)), error);
    TEST_ASSERT_EQUAL_STRING("de", layout.speech);
    TEST_ASSERT_NOT_NULL(strstr(layout.roots[0].base, "language/de"));
    TEST_ASSERT_NOT_NULL(strstr(layout.roots[1].base, "language/en"));
    TEST_ASSERT_NOT_NULL(strstr(layout.roots[2].base, "common"));
    /* no wish: English */
    TEST_ASSERT_TRUE(c2_library_layout(ROOT "/data", "", &layout, error, sizeof(error)));
    TEST_ASSERT_EQUAL_STRING("en", layout.speech);
    /* a wish the data cannot grant: English too */
    TEST_ASSERT_TRUE(c2_library_layout(ROOT "/data", "fr", &layout, error, sizeof(error)));
    TEST_ASSERT_EQUAL_STRING("en", layout.speech);
    /* nothing yet: said so */
    TEST_ASSERT_FALSE(c2_library_layout(ROOT "/nothing-here", "", &layout, error, sizeof(error)));
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_a_dos_disc_is_sorted_into_places);
    RUN_TEST(test_a_hybrid_disc_adds_the_recordings_and_larger_scaled_movies);
    RUN_TEST(test_the_windows_only_pressing_is_used_until_dos_files_arrive);
    RUN_TEST(test_a_language_folder_holds_one_release_and_the_better_one_wins);
    RUN_TEST(test_the_later_pressing_breaks_a_tie_of_equal_versions);
    RUN_TEST(test_a_mac_install_gives_its_movies_music_and_speech);
    RUN_TEST(test_the_hfs_reader_catalogues_a_mac_disc_image);
    RUN_TEST(test_the_order_of_imports_does_not_matter);
    RUN_TEST(test_an_export_is_the_library_zipped_and_imports_back);
    RUN_TEST(test_a_newer_format_is_refused_by_name);
    RUN_TEST(test_removal_leaves_everything_else);
    RUN_TEST(test_old_caches_are_migrated_and_removed);
    RUN_TEST(test_the_runtime_reads_the_chosen_speech_first);
    return UNITY_END();
}
