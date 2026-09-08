#include <unity/unity.h>

#include <stdlib.h>
#include <string.h>

/* The movie player's two portable decisions, with its statics in reach:
 * which of a movie's two files (DOS or Windows 95 tree) to play, and how a
 * frame of any size lands in the doubled VGA screen. */
#include "../src/platform/common/c2_port_video.c"

/* The engine globals and functions c2_port_video.c reaches for. */
unsigned char current_palette[C2_PALETTE_BYTES];
unsigned char *internal_screen;
unsigned char *scratch_buffer;
int scratch_buffer_size;
char temp_palette[0x300];
struct c2inf_rec c2inf;
void refresh_svga_screen(void) {}
void setup_refresh_area(int a, int b, int c, int d, int e) { (void)a; (void)b; (void)c; (void)d; (void)e; }
void setup_whole_screen_refresh(void) {}
void stop_samples(void) {}
void general_sprite(int a, int b, int c) { (void)a; (void)b; (void)c; }
void set_palette(char *p) { (void)p; }
void c2_port_wait_for_frame(void) {}
void c2_port_wait_vblank(void) {}
uint64_t c2_host_ticks_ms(void) { return 0; }
int c2_host_audio_init(int n) { (void)n; return 0; }
int c2_host_audio_queue_pcm(int v, const void *d, size_t s, int r, int c, int b, int f)
{ (void)v; (void)d; (void)s; (void)r; (void)c; (void)b; (void)f; return 0; }
void c2_host_audio_stop_voice(int v) { (void)v; }

/* The game data: a name, its bytes, in the DOS tree and/or the Windows one. */
struct fake { const char *name; int windows; unsigned char bytes[16]; size_t size; };
static struct fake files[8];
static size_t file_count;

static void add_smk(const char *name, int windows, unsigned long width, unsigned long height)
{
    struct fake *f = &files[file_count++];
    f->name = name;
    f->windows = windows;
    memcpy(f->bytes, "SMK2", 4);
    f->bytes[4] = width & 0xff; f->bytes[5] = (width >> 8) & 0xff; f->bytes[6] = 0; f->bytes[7] = 0;
    f->bytes[8] = height & 0xff; f->bytes[9] = (height >> 8) & 0xff; f->bytes[10] = 0; f->bytes[11] = 0;
    f->size = 12;
}

static const struct fake *find(const char *name, int windows)
{
    size_t i;
    for (i = 0; i < file_count; i++) {
        if (files[i].windows == windows && strcmp(files[i].name, name) == 0) return &files[i];
    }
    return NULL;
}

static size_t read_from(const struct fake *f, void *buffer, size_t size, size_t offset)
{
    if (!f || offset >= f->size) return 0;
    if (size > f->size - offset) size = f->size - offset;
    memcpy(buffer, f->bytes + offset, size);
    return size;
}

uint64_t c2_host_asset_size(const char *name) { const struct fake *f = find(name, 0); return f ? f->size : 0; }
size_t c2_host_asset_read(const char *name, void *b, size_t s, size_t o) { return read_from(find(name, 0), b, s, o); }
uint64_t c2_host_asset_windows_size(const char *name) { const struct fake *f = find(name, 1); return f ? f->size : 0; }
size_t c2_host_asset_windows_read(const char *name, void *b, size_t s, size_t o) { return read_from(find(name, 1), b, s, o); }

void *c2_port_load_asset(const char *name, size_t *size_out)
{
    const struct fake *f = find(name, 0);
    void *data;
    if (!f) return NULL;
    data = malloc(f->size);
    memcpy(data, f->bytes, f->size);
    *size_out = f->size;
    return data;
}

void setUp(void)
{
    file_count = 0;
    memset(&c2_movie, 0, sizeof(c2_movie));
    internal_screen = calloc((size_t)C2_SCREEN_WIDTH * C2_SCREEN_HEIGHT, 1);
}

void tearDown(void)
{
    free(internal_screen);
    internal_screen = NULL;
}

static unsigned long chosen_pixels(const char *name, int mode)
{
    size_t size = 0;
    unsigned char *data = load_movie_asset(name, mode, &size);
    unsigned long pixels = smk_header_pixels(data, size);
    free(data);
    return pixels;
}

static void test_mode_2_takes_the_larger_windows_movie(void)
{
    add_smk("battwon.smk", 0, 320, 152);
    add_smk("battwon.smk", 1, 500, 240);
    TEST_ASSERT_EQUAL_UINT32(500ul * 240ul, chosen_pixels("battwon.smk", 2));
}

static void test_modes_drawn_one_to_one_keep_the_dos_movie(void)
{
    add_smk("message.smk", 0, 320, 152);
    add_smk("message.smk", 1, 500, 240);
    TEST_ASSERT_EQUAL_UINT32(320ul * 152ul, chosen_pixels("message.smk", 1));
    TEST_ASSERT_EQUAL_UINT32(320ul * 152ul, chosen_pixels("message.smk", 0));
}

static void test_same_size_windows_reencode_is_not_preferred(void)
{
    add_smk("congrat.smk", 0, 320, 152);
    add_smk("congrat.smk", 1, 320, 152);
    /* Equal pixels: the DOS file, which has more colours. */
    TEST_ASSERT_EQUAL_PTR(find("congrat.smk", 0)->bytes[4], find("congrat.smk", 1)->bytes[4]);
    {
        size_t size = 0;
        unsigned char *data = load_movie_asset("congrat.smk", 2, &size);
        TEST_ASSERT_NOT_NULL(data);
        free(data);
    }
    /* Only one tree: what there is. */
    file_count = 0;
    add_smk("wingame.smk", 0, 500, 240);
    TEST_ASSERT_EQUAL_UINT32(500ul * 240ul, chosen_pixels("wingame.smk", 2));
}

static void test_vga_frame_fills_the_doubled_box_from_any_size(void)
{
    unsigned char *pixels;
    unsigned long x;
    unsigned long y;

    /* A 500x240 frame: left half colour 1, right half colour 2, drawn at
     * (0, 24) in VGA space = rows 57..421 of the 640x480 frame (2.4x), as
     * the DOS 320x152 frame doubled by the original arithmetic. */
    c2_movie.width = 500;
    c2_movie.height = 240;
    pixels = malloc(500 * 240);
    for (y = 0; y < 240; y++) for (x = 0; x < 500; x++) pixels[y * 500 + x] = x < 250 ? 1 : 2;
    copy_vga_frame(pixels, 0, 0x18);
    free(pixels);

    TEST_ASSERT_EQUAL_UINT8(0, internal_screen[56 * C2_SCREEN_WIDTH + 10]);    /* above the box */
    TEST_ASSERT_EQUAL_UINT8(1, internal_screen[57 * C2_SCREEN_WIDTH + 10]);    /* first row */
    TEST_ASSERT_EQUAL_UINT8(1, internal_screen[200 * C2_SCREEN_WIDTH + 319]);  /* left half */
    TEST_ASSERT_EQUAL_UINT8(2, internal_screen[200 * C2_SCREEN_WIDTH + 320]);  /* right half */
    TEST_ASSERT_EQUAL_UINT8(2, internal_screen[421 * C2_SCREEN_WIDTH + 639]);  /* last row, last column */
    TEST_ASSERT_EQUAL_UINT8(0, internal_screen[422 * C2_SCREEN_WIDTH + 639]);  /* below the box */

    /* The DOS 320x152 frame lands identically: plain doubling. */
    memset(internal_screen, 0, (size_t)C2_SCREEN_WIDTH * C2_SCREEN_HEIGHT);
    c2_movie.width = 320;
    c2_movie.height = 152;
    pixels = malloc(320 * 152);
    for (y = 0; y < 152; y++) for (x = 0; x < 320; x++) pixels[y * 320 + x] = x < 160 ? 1 : 2;
    copy_vga_frame(pixels, 0, 0x18);
    free(pixels);
    TEST_ASSERT_EQUAL_UINT8(1, internal_screen[57 * C2_SCREEN_WIDTH + 319]);
    TEST_ASSERT_EQUAL_UINT8(2, internal_screen[421 * C2_SCREEN_WIDTH + 320]);
    TEST_ASSERT_EQUAL_UINT8(0, internal_screen[422 * C2_SCREEN_WIDTH + 320]);
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_mode_2_takes_the_larger_windows_movie);
    RUN_TEST(test_modes_drawn_one_to_one_keep_the_dos_movie);
    RUN_TEST(test_same_size_windows_reencode_is_not_preferred);
    RUN_TEST(test_vga_frame_fills_the_doubled_box_from_any_size);
    return UNITY_END();
}
