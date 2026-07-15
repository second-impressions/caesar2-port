// D:\C2\CODE\lib32.c

#include "lib32.h"
#include "c2_data.h"
#include <conio.h>             /* inp(), outpw() */
#ifdef __WATCOMC__
#include <i86.h>              /* int386, union REGS, sound/nosound/delay */
#endif
#include <io.h>                /* open, close, read, write */
#include <fcntl.h>             /* O_BINARY */
#include <stdlib.h>            /* free, malloc */
#include <string.h>            /* memset */
#include <dos.h>               /* _dos_setdrive */
#include <direct.h>            /* chdir */
#include <sys/timeb.h>         /* ftime, struct timeb */

/* ── TU-owned file-scope INITIALIZED data (PS.EXE _DATA / CONST, original
   declaration order: cbd, steves_security_false1, chipset_names,
   multiples).  Kept here (not in datainit.c) so this module's CONST
   literals + _DATA land at lib32's link position, matching PS. */
struct mouse_cbd cbd = { 0, 0, 0, 0, 0, 0, 0, 0 };
int steves_security_false1[7] = {
    538976288, 2021138464, 2021161080, 1717986936,
    1717986918, 538994278, 538976288 };
char *chipset_names[32] = {
    "Unknown", "Trident", "Tseng", "", "", "", "", "",
    "", "", "", "", "", "", "", "",
    "", "", "", "", "", "", "", "",
    "", "", "", "", "", "", "", ""
};
int multiples[8] = { 1, 10, 100, 1000, 10000, 100000, 1000000, 10000000 };

/* ── TU-owned file-scope variables (PS.EXE _BSS layout order).  The original
   first-declaration page order is reconstructed in lib32.h.  These definitions
   keep the functional rebuild self-sustained, with no auto-stubbed storage. */
struct vbe_mode_info vesa_mode_info;
char card_ids[32];
unsigned char greying_data[256];
char mouse_background[576];
struct vbe_info_block vesa_info;
char black_out_data[768];
char current_palette[768];
char temp_palette[768];
unsigned char logos[5344];
unsigned char font2[28248];
unsigned char system_panel[41672];
char format_buffer[2000];
char text_buffer[40000];
char path_name[80];
struct dpmi_mem_info memory;
int cards_recognised;
int card_is;
int card_sub_type;
int vid_bank_tech;
int vid_tech;
int vid_error;
int fb_current_char_length;
int fb_max_char_length;
int vid_memory;
int old_mouse_drops_y;
int old_mouse_drops_x;
int bank_ptr;
int vid_no_of_banks;
short highlight_goods_list[18];
int slider_total;
short selection_goods_list[18];
int select_cost_flag;
int scat32000;
int para1;
int para2;
int select_width;
int select_height;
int rand128;
int select_count;
int slidper_on;
int scat128;
unsigned char font1[9460];
int rand32000;
int rand8;
int cnt32;
int out6;
int out7;
int out4;
int out5;
int out2;
int out3;
unsigned int randseed;
int out1;
int turbo_mode;
int out8;
int cnt16;
int cnt64;
unsigned int scatseed;
int cycle_count;
int cnt128;
int cnt8;
int cnt2;
int cnt4;
int cnt256;
int adjust_step;
int test_value4d;
int test_value4a;
int test_value4b;
int test_value4c;
int test_value2d;
int adjust_min;
int test_value2a;
int test_value2b;
int test_value2c;
int test_value3d;
int test_value3a;
int * adjust_var;
int test_value3b;
int test_value3c;
int test_value1d;
int test_value1a;
int test_value1b;
int test_value1c;
int adjust_max;
int font_style;
int absolute_ofset;
int x_wrap;
int dx;
int dy;
int font_screen_limit;
int ex;
int ey;
int sprite_bank;
int D;
int x_start;
int y_start;
int sprite_next_bank_count;
int gx;
int gy;
int y_length;
int ix;
int iy;
int x_length;
int sprite_bank_ofset;
int x_end;
int y_end;
int x_ofset;
int sprite_height;
int old_sprite_y;
int old_sprite_x;
int sprite2_start;
int sprite3_start;
int sprite_colour;
int sprite_error;
int sprite_width;
int sprite_image_no;
int sprite3_image_no;
int data_ptr;
int sprite2_height;
int sprite2_image_no;
int sprite_start;
int sprite2_width;
int sprite3_width;
int sprite_base_y;
int sprite_base_x;
int sprite_x_off;
int sprite_hat_start;
int sprite3_height;
int sprite_size;
int sprite_y_off;
int sprite_x;
int sprite_y;
int fb_max_width_reached;
int at_limit;
int fb_line_length;
int got_cursx;
int cursor_x;
int cursor_y;
char * text_pointer;
char insert_text[100];
int char_count;
int this_letter;
int insert_count;
int insert_place;
int x_is;
int fb_no_of_lines;
int fb_limit;
int fb_count;
int first_entry;
int cscreen;
int screen_width;
char *lang_file;
char directory[100][13];
int gamesource;
int granularity;
int no_of_entries;
int oscreen;
int screen_size;
unsigned char * internal_screen;
char extension[4];
int file_no;
char *media_file;
int screen_height;
int drive_name;
int file_string;
int button_time_flag;
int local_time;
int time_is;
int mouse_y;
int mouse_x;
int old_mouse_x;
int old_mouse_y;
int mouse_installed;
int mouse_movement;
int mouse_was_pressed;
int used_memory;
int free_memory;
int dos_memory;
int avl_memory;
int max_memory;
int scratch_buffer_size;
unsigned char * scratch_buffer;
int allocable_memory;
struct dpmi_real_block VesaModeInfo;
struct dpmi_real_block VesaInfo;
unsigned char mice[8630];
struct media_entry this_media_entry;
short mse_y;
short mse_x;
unsigned char game_panels[23441];
char filename[13];
char vid_new_val;
char old3d5_14;
char old3d5_17;
char vid_old_val;
char old3cf_6;
char old3cf_5;
char vid_val;
char old3c5_4;
char pre_loaded_status;
char continue_tutorial_status;
char file_loaded_status;
char map_gfx_loaded;
char hot_exit_flag;
char decision;
char confirming;
char exit_flag;
char restart_flag;
char test_mode3;
char test_mode2;
char test_mode1;
char test_mode4;
char develop_mode;
char xclipped;
char yclipped;
char insert_cursor;
char highlight;
char allow_padding;
char hot_key_out_off_build;
char hold_hot_keys;
char padding_off;
char screen_refresh_flag;
char hold_mouse_replace;
unsigned char screen_mode;
unsigned char pointer_mode;
char old_mouse_rb;
char old_mouse_lb;
unsigned char mouse_left_button;
unsigned char mouse_left_click;
char debar_fade_click;
unsigned char mouse_right_preclick;
unsigned char mouse_left_preclick;
char mouse_right_button;
char mouse_right_click;
char key_code;
char debug_interupt;
char key_ascii_was;
char mse_button;
char key_ready;
char key_ascii;

/* Callees still living elsewhere as stubs in this TU or other files. */
// PS-inferred signatures (the only caller in lib32.c is
// `copy_to_physical_screen`, which forwards its own params).
// `c2 inferred-sig` reports both callees read EAX (and EDX for
// the first) on entry — they save EAX into ESI right after pushal.


extern void write_i_sprite(unsigned char *sprite_addr);       /* sprites.asm */
extern void write_i_left_sprite(unsigned char *sprite_addr);  /* sprites.asm */
extern void write_i_right_sprite(unsigned char *sprite_addr); /* sprites.asm */
extern void write_i_font(unsigned char *font);                /* sprites.asm */
extern void write_i_left_font(unsigned char *font);           /* sprites.asm */
extern void write_i_right_font(unsigned char *font);          /* sprites.asm */

extern int _dx;
#pragma aux _dx "*"
extern void __cdecl code_0188AD(void);
extern void __cdecl code_0188B7(void);
extern void __cdecl code_0188ED(void);
extern void __cdecl code_018944(void);
extern void __cdecl code_018964(void);
extern void __cdecl code_018986(void);
extern void __cdecl code_0189AE(void);
extern void __cdecl code_0189D6(void);
extern void __cdecl code_0189ED(void);
extern void __cdecl code_018A04(void);
extern void __cdecl code_018A1D(void);
extern void __cdecl code_018A2F(void);
extern void __cdecl code_018A39(void);
extern void __cdecl code_018A43(void);
extern void __cdecl code_018A4D(void);
extern void __cdecl code_018A79(void);
extern void __cdecl code_018AA0(void);
extern void __cdecl code_018AB9(void);
extern void __cdecl code_018AEE(void);
extern void __cdecl code_018B12(void);
extern void __cdecl code_018B39(void);
extern void __cdecl code_018B60(void);
extern void __cdecl code_018B87(void);
extern void __cdecl code_018BAC(void);
extern void __cdecl code_018BED(void);
extern void __cdecl code_018BFC(void);
extern void __cdecl code_018C03(void);
extern void __cdecl code_018C0A(void);
extern void __cdecl code_018C11(void);
extern void __cdecl code_018C18(void);
extern void __cdecl code_018C1F(void);
extern void __cdecl code_018C26(void);
extern void __cdecl code_018C2D(void);
extern void __cdecl code_018C4A(void);
extern void __cdecl code_018C74(void);
extern void __cdecl code_018C92(void);
extern void __cdecl code_018CCA(void);
extern void __cdecl code_018CEA(void);
extern void __cdecl code_018D13(void);
extern void __cdecl code_018D36(void);
extern void __cdecl code_018D50(void);
char get_insert_letter(void);
char sim_mouse(void);

extern void __far click_handler(unsigned int ax,
                                unsigned int bx,
                                unsigned int cx,
                                unsigned int dx,
                                unsigned int si,
                                unsigned int di);
// FUNCTION: C2 0x24212
// Lines 352–367
//
// Populate the global directory[] table with up to 100 filenames
// matching the given DOS wildcard pattern.  Each slot is 13 bytes
// (8.3 + NUL); the name is copied straight out of the
// _dos_findfirst / _dos_findnext result buffer at offset +0x1E
// (the standard `find_t.name` field).  no_of_entries is reset to
// 0 before the scan and incremented per match; first_entry is
// reset to 0 so the next listing-display starts at the top.
//
// Attribute mask is hardcoded to 0 (regular files only -- no
// directories, hidden, system, or volume-label entries).
#ifdef __WATCOMC__
// WIN: 0x0044a7e0

void get_directory(char *pattern)
{
    struct find_t find_buf;
    unsigned result;
    unsigned j;

    no_of_entries = 0;

    result = _dos_findfirst(pattern, 0, &find_buf);
    while (result == 0) {
        for (j = 0; j < 13; j++) {
            directory[no_of_entries][j] = find_buf.name[j];
        }
        no_of_entries++;
        result = _dos_findnext(&find_buf);
        if (no_of_entries >= 0x64) break;
    }

    first_entry = 0;
}

// FUNCTION: C2 0x2426E
// WIN: 0x0044a8ae
// Lines 369–398
//
// Switches to a CD-resident search path so the next open() finds the
// file there instead of on the hard drive.  Looks at the extension
// in `fname` (PL8/RAW/XMI/etc.) to pick which CD subdir.  All callers
// pair this with a matching main_path() call to restore.
//
// Layout:
//   1. early-exit if c2inf.drive_init != 1 (non-CD install)
//   2. extract the 3-char extension into the global `extension`,
//      uppercase it, and bail out if it isn't one of the four
//      asset families this game ships per-format CD subdirs for
//      (PL8 / RAW / XMI / SMK)
//   3. _dos_setdrive(c2inf.cd_letter - 'A', &saved_drive)
//   4. chdir to "X:\\" where X is c2inf.cd_letter (modifies the
//      static buf[] in place)
//   5. chdir into the matching lower-case subdir
void cd_path(const char *fname)
{
    char *buf = "c:\\";
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;

    get_filename_extension(fname);
    string_to_upper(extension);

    matched = 1;
    if (strcmp("PL8", extension) == 0) matched = 0;
    else if (strcmp("RAW", extension) == 0) matched = 0;
    else if (strcmp("XMI", extension) == 0) matched = 0;
    else if (strcmp("SMK", extension) == 0) matched = 0;
    if (matched) return;

    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);

    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}

// FUNCTION: C2 0x24382
// WIN: 0x0044aa77
// Lines 400–406
//
// If c2inf.drive_init==1 we're booted from a non-system drive: switch back
// to the original drive and chdir into the install path.
void main_path(void)
{
    unsigned total;
    if (c2inf.drive_init == 1) {
        _dos_setdrive(drive_name - 0x40, &total);
        chdir(path_name);
    }
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x243B0
// Lines 408–420
//
// Walk past the filename to the '.' separator and copy the 3-char
// extension into the global `extension[]` buffer (NUL-terminated).
void get_filename_extension(const char *fname)
{
    char c;
    do {
        c = *fname;
        fname++;
    } while (c != '.' && c != 0);
    if (c != '.')
        return;
    extension[0] = *fname++;
    extension[1] = *fname++;
    extension[2] = *fname;
    extension[3] = 0;
}

// FUNCTION: C2 0x243EF
// Lines 422–434
//
// Walk past the filename to the '.' separator and overwrite the 3-char
// extension with the global `extension[]` (NUL-terminated).
void put_filename_extension(char *fname)
{
    char c;
    do {
        c = *fname;
        fname++;
    } while (c != '.' && c != 0);
    if (c != '.')
        return;
    *fname++ = extension[0];
    *fname++ = extension[1];
    *fname++ = extension[2];
    *fname   = 0;
}

// FUNCTION: C2 0x2442B
// Lines 436–443
//
// Length of a filename up to (and including) the first '.' or '\0'.
char get_filename_length(char *s)
{
    char len = 0;
    char c;
    do {
        c = *s++;
        len++;
    } while (c != '.' && c != 0);
    return len;
}

// FUNCTION: C2 0x24446
// Lines 445–458
//
// Try to open `fname` (after cd_path) and report whether it exists.
// Always restores the working directory via main_path before returning.
int check_file_exists(char *fname)
{
    int fd;
    int found = 0;
    cd_path(fname);
    fd = open(fname, 0x200);
    if (fd >= 0) {
        found = 1;
        close(fd);
    }
    main_path();
    return found;
}

// FUNCTION: C2 0x24477
// Lines 460–467
//
// Variant of check_file_exists that doesn't cd_path/main_path —
// just opens the file at its given path.
int is_file_on_harddrive(char *fname)
{
    int fd;
    int found = 0;
    fd = open(fname, 0x202);
    if (fd >= 0) {
        found = 1;
        close(fd);
    }
    return found;
}

// FUNCTION: C2 0x2449A
// Lines 469–495
//
// Read `size` bytes from `fname` at byte `offset` into `buf`.
// Returns the number of bytes actually read, or 0 if both the
// hard-drive and CD attempts failed to read anything.
//
// Tries the hard-drive path first; on any failure (open returns
// -1, lseek fails, or read returns 0) falls through to a second
// attempt under cd_path() and is unconditionally followed by
// main_path() to restore the working directory.
int readfile(const char *fname, void *buf, int size, int offset)
{
    int fd;
    int n;

    n = 0;
    fd = open(fname, 0x200);
    if (fd != -1) {
        if (_lseek(fd, offset, 0) != -1) {
            n = read(fd, buf, size);
        }
        close(fd);
    }

    if (n <= 0) {
        cd_path(fname);
        fd = open(fname, 0x200);
        if (fd != -1) {
            if (_lseek(fd, offset, 0) != -1) {
                n = read(fd, buf, size);
            }
            close(fd);
        }
        main_path();
    }

    return n;
}

// FUNCTION: C2 0x24541
// Lines 497–505
//
// open() the named file (creating it 0644), write `size` bytes, close.
// Returns the number written, or 0 on open failure.
int writefile(const char *fname, char *buf, int size)
{
    int fd;
    int n;
    fd = open(fname, 0x261, 0x180);
    if (fd == -1)
        return 0;
    n = write(fd, buf, size);
    close(fd);
    return n;
}

// FUNCTION: C2 0x24572
// Lines 507–518
//
// Open `fname` for write+create at the given offset, write `size` bytes
// from `buf`, close. Returns the number of bytes written, or 0 on
// open or seek failure (and leaks the fd on seek failure — PS does too).
int write_to_file(char *fname, char *buf, int size, int offset)
{
    int fd;
    int n;
    fd = open(fname, 0x221, 0x180);
    if (fd == -1)
        return 0;
    if (_lseek(fd, offset, 0) == -1)
        return 0;
    n = write(fd, buf, size);
    close(fd);
    return n;
}

// FUNCTION: C2 0x245BE
// Lines 521–534
//
// Parse a key=value config file looking for the "resaud" key.
// Reads up to 1000 bytes of the file into 'buf', then byte-by-byte
// scans for the literal text "resaud" (6 chars).  If found, returns
// the byte at offset +7 from the match start (the '=' / separator
// byte is at +6, value byte at +7).  Returns:
//
//   1  - readfile() failed (file missing / unreadable)
//   0  - readfile() succeeded but "resaud" key not present
//   v  - the byte stored 7 chars past the matched "resaud"
//
// Currently the only key understood is "resaud", so this function
// is essentially a single-purpose probe of resource.cfg for the
// audio-driver letter.  Caller cast to (unsigned char) makes the
// distinction between the 1-byte 'failure' sentinel (al == 1) and
// a real audio code clean.
char read_config(char *fname, char *buf)
{
    char *p;
    int n;

    p = buf;
    n = 1000;
    if (readfile(fname, p, n, 0) == 0) return 1;

    while (n > 0) {
        if (my_strcmp(p, "resaud", 6) == 0) break;
        n--;
        p++;
    }
    if (n <= 0) return 0;

    p += 7;
    return *p;
}

// FUNCTION: C2 0x2460F
// Lines 537–608
//
// Parse an IFF ILBM (.lbm) image already loaded into `src`.
// Locates the BMHD, CMAP, and BODY chunks (each found by scanning
// up to `length` bytes for the chunk's 4-byte tag).  The BMHD
// width sets screen_mode (320→mode 1, 640→mode 2); CMAP entries
// are 6-bit palette values stored into `pal` (768 bytes); BODY is
// RLE-decoded into `dst` (PackBits-style: a byte n in [0..127]
// means copy the next n+1 bytes verbatim; n in [129..255] means
// repeat the next byte (257-n) times; n == 128 is a no-op).
// Returns 0 on success, or 2/3/4/6/7/8 for the various parse
// failures.
//
// Shape status (2026-07-03): run-ledger 161/161 insns register-blind
// identical, isl 0, width/spill 0 -- every statement matches PS's IR;
// 11 diff bytes = two isolated register mirrors (seat 1/8):
//   * the two width zext temps (PS EDX/EAX, RC EAX/EDX) -- an
//     equal-savings allocator tie at their shared death (the +=
//     add); commuting is canonicalised away, decl order inert.
//   * a/b (PS a=EAX,b=EBX; RC mirrored) -- PS-alloc REACHABLE via
//     commuting `(a << 16) + (b << 8)` but that drags the shl
//     emission order away from PS (G_RR2), so source order is kept.
// Probed: forge full battery x pairs (4823 plans), decl sweeps,
// zext-form/cast variants, shuttle-variable sweep, rover carriers.
//
// `i` must be MEMORY-HOMED at [esp] (PS slots: [esp]=i,
// [esp+4]=length) without stealing the decode loop's 8th register:
// the dead `p = (unsigned char *)&i;` makes i addressable, which
// reproduces ALL of PS's i forms (CMAP load-inc-store shuttle via
// the rover's EBX, decode-loop inc [esp] / add [esp],ebx /
// cmp edi,[esp], zero-temp writes).  volatile instead gives inc-mem
// + dead re-reads; plain int enregisters i and cascades (205bd).
// The address-take is instrumental -- PS's true construct for the
// memory homing is still unknown (its -d1 stream is silent here).
int convert_lbm_file(unsigned char *src, unsigned char *dst, char *pal, int length)
{
    int a;
    short width;
    int i;
    unsigned char tag;
    unsigned char run;
    unsigned char *p;
    int chunk_search;
    int b;
    int c;
    int k;

    p = (unsigned char *)&i;
    p = src;
    chunk_search = 0x64;
    while (chunk_search > 0) {
        if (my_strcmp((char *)p, "BMHD", 4) == 0) break;
        chunk_search--; p++;
    }
    if (chunk_search <= 0) return 2;

    p += 8;
    width = (*p++ << 8) + *p++;
    p += 2;
    if (width == 0x140) screen_mode = 1;
    else if (width == 0x280) screen_mode = 2;
    else return 4;
    p += 5;
    if ((*p++ & 0xff) == 1) return 3;

    chunk_search = length;
    while (chunk_search > 0) {
        if (my_strcmp((char *)p, "CMAP", 4) == 0) break;
        chunk_search--; p++;
    }
    if (chunk_search <= 0) return 6;
    i = 0;
    p += 8;
    do {
        *pal++ = (*p++ & 0xff) >> 2;
        i++;
    } while (i < 0x300);

    chunk_search = length;
    while (chunk_search > 0) {
        if (my_strcmp((char *)p, "BODY", 4) == 0) break;
        chunk_search--; p++;
    }
    if (chunk_search <= 0) return 7;
    p += 5;
    a = *p++;
    b = *p++;
    c = *p++;
    c += (a << 16) + (b << 8);
    if (c > length) return 8;

    for (i = 0; i < c; ++i)
    {
        tag = *p++;
        if (tag > 0x80) {
            run = *p++;
            for (k = 0; k < 0x100 - tag + 1; k++) *dst++ = run;
            ++i;
        }
        else {
            for (k = 0; k < tag + 1; k++) *dst++ = *p++;
            i += tag + 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x247B1
// Lines 614–714
//
// Switch into a VESA SVGA mode (640×480 for `mode == 0`, 640×400
// for `mode == 1`).  Issues four real-mode VESA calls via
// DPMI int 0x31:
//
//   * Function 0x4F00 — fetch VbeInfoBlock into VesaInfo.
//   * Function 0x4F01 — fetch ModeInfoBlock for the chosen mode
//     into VesaModeInfo (and copy the bank-switching far pointer
//     into `bank_ptr`).
//   * Function 0x4F02 — set the requested SVGA mode.
//
// Side effects: writes screen_width / screen_height / screen_size,
// granularity (0..6 — the log2 of the kilobyte-step the chip uses
// between video banks), bank_ptr, and calls recognise_card +
// get_video_technique to identify the chipset.  Returns 0 on
// success, 1 if 4F00 didn't report VESA, or 2 if 4F02 refused the
// mode.
#ifdef __WATCOMC__
int set_svga_640_480(int mode)
{
    union REGS r;
    struct SREGS sr;
    int sel;
    int mode_id;
    int height;
    int vmask;
    int seg;

    if (mode == 0) {
        mode_id = 0x101;
        height = 0x1e0;
    } else if (mode == 1) {
        mode_id = 0x100;
        height = 0x190;
    }
    set_vga_mode(0x12);

    /* VESA 4F00 — VbeInfoBlock */
    memset(&sr, 0, 0xc);
    r.w.ax = 0x100;
    r.w.bx = 0x10;
    int386(0x31, &r, &r);
    sel = r.w.ax;
    seg = r.w.dx;
    VesaInfo.selector = seg;
    VesaInfo.offset   = 0;
    _fmemset(MK_FP(seg, 0), 0xaa, 0x100);
    memset(&RMI, 0, 0x32);
    RMI.eax = 0x4f00;
    RMI.es = sel;
    RMI.edx = 0;
    r.w.ax = 0x300;
    r.h.bl = 0x10;
    r.h.bh = 0;
    r.w.cx = 0;
    sr.es = FP_SEG(&RMI);
    r.x.edi = (int)&RMI;
    int386x(0x31, &r, &r, &sr);
    _fmemcpy((void __far *)&vesa_info, *(void __far **)&VesaInfo, 0x100);
    vid_memory = (short)vesa_info.total_memory << 6;
    r.w.ax = 0x101;
    r.w.bx = seg;
    int386(0x31, &r, &r);
    if (RMI.eax != 0x4f) return 1;

    /* VESA 4F01 — ModeInfoBlock */
    memset(&sr, 0, 0xc);
    r.w.ax = 0x100;
    r.w.bx = 0x10;
    int386(0x31, &r, &r);
    sel = r.w.ax;
    seg = r.w.dx;
    VesaModeInfo.selector = seg;
    VesaModeInfo.offset   = 0;
    _fmemset(MK_FP(seg, 0), 0xaa, 0x100);
    memset(&RMI, 0, 0x32);
    RMI.eax = 0x4f01;
    RMI.ecx = mode_id;
    RMI.es = sel;
    RMI.edx = 0;
    r.w.ax = 0x300;
    r.h.bl = 0x10;
    r.h.bh = 0;
    r.w.cx = 0;
    sr.es = FP_SEG(&RMI);
    r.x.edi = (int)&RMI;
    int386x(0x31, &r, &r, &sr);
    _fmemcpy((void __far *)&vesa_mode_info, *(void __far **)&VesaModeInfo, 0x100);
    bank_ptr = (vesa_mode_info.win_func_seg << 4) + vesa_mode_info.win_func_off;
    r.w.ax = 0x101;
    r.w.bx = seg;
    int386(0x31, &r, &r);
    recognise_card();
    get_video_technique();

    r.w.ax = 0x4f02;
    r.w.bx = mode_id;
    int386(0x10, &r, &r);
    if (r.w.ax != 0x4f) return 2;

    screen_width = 0x280;
    screen_height = height;
    screen_size = height * 0x280;
    vmask = vesa_mode_info.win_granularity;
    if (vmask == 0x40)      granularity = 0;
    else if (vmask == 0x20) granularity = 1;
    else if (vmask == 0x10) granularity = 2;
    else if (vmask == 8)    granularity = 3;
    else if (vmask == 4)    granularity = 4;
    else if (vmask == 2)    granularity = 5;
    else if (vmask == 1)    granularity = 6;
    set_bank(0);
    return 0;
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x24B0E
// Lines 719–728
//
// Probe for the installed VGA chipset.  Zeroes the card-detection
// state, runs the per-vendor probes (currently Trident and Tseng),
// then double-checks: if more than one probe claimed a hit, throw
// out everything (Caesar II won't try to use ambiguous detections).
//
// State globals:
//   card_ids[]          - 0x20 bytes; per-vendor sub-id slots.
//                         card_ids[1] = check_for_Trident()'s byte
//                         card_ids[2] = check_for_Tseng()'s byte.
//   cards_recognised    - count of probes that returned non-zero;
//                         each probe self-increments this when it
//                         claims a hit.
//   card_is             - the chosen card-id (0 if none/ambiguous).
//   card_sub_type       - the chosen sub-type (0 if none/ambiguous).


void recognise_card(void)
{
    int i;

    cards_recognised = 0;
    card_sub_type    = 0;
    card_is          = 0;
    for (i = 0; i < 0x20; i++)
        card_ids[i] = 0;

    card_ids[1] = check_for_Trident();
    card_ids[2] = check_for_Tseng();

    if (cards_recognised > 1) {
        card_sub_type    = 0;
        card_is          = 0;
        cards_recognised = 0;
    }
}

// FUNCTION: C2 0x24B69
// Lines 730–747
//
// Probe the VGA Sequencer for a Trident chipset signature.
//
// Trident SVGAs respond to a write to Sequencer index 0x0E
// (Mode Control Register 2): the low nibble reads back as 2
// after writing 0 (Trident's hardware reads it inverted from
// what was written, plus a fixed 0x02 ID nibble).  Generic
// VGAs read back what was written and so won't match.
//
// On a positive ID:
//   * Sequencer index 0x0B (Hardware Version) is read; the
//     value is the chip generation.
//   * card_is               = 1                (Trident).
//   * card_sub_type         = 0x22c4 (TVGA89xx) for ver >= 3,
//                             else 0x2260 (TVGA88xx).
//   * cards_recognised      += 1.
//   * returns 1.
//
// On a negative ID we restore the saved register and return 0.
//
// Side scratch globals: vid_old_val (the saved 0x3C5 byte for
// restoration), vid_val (low nibble probe / version).
#ifdef __WATCOMC__
int check_for_Trident(void)
{
    int rv;

    /* Save current SR0E, write 0, read back the low nibble. */
    outp(0x3c4, 0x0e);
    vid_old_val = inp(0x3c5);
    outp(0x3c5, 0);
    vid_val = inp(0x3c5) & 0xf;
    outp(0x3c5, vid_old_val);

    if (vid_val != 2) return 0;

    /* Hardware Version index. */
    outp(0x3c4, 0x0b);
    outp(0x3c5, 0);
    vid_val = inp(0x3c5) & 0xf;

    card_is = 1;
    if (vid_val >= 3) {
        card_sub_type = 0x22c4;
    } else {
        card_sub_type = 0x2260;
    }
    cards_recognised += 1;
    return 1;
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x24C2C
// Lines 749–749
//
// Tseng VGA detection -- a stub returning 0 (no Tseng card found).
int check_for_Tseng(void)
{
    return 0;
}

// FUNCTION: C2 0x24C2F
// Lines 755–768
//
// Set vid_tech / vid_bank_tech / vid_no_of_banks based on the
// detected VESA memory and recognised cards.
void get_video_technique(void)
{
    vid_tech         = 0;
    vid_bank_tech    = 0;
    vid_no_of_banks  = 0;
    if (vid_memory >= 0x400)
        vid_tech = 1;
    if (cards_recognised != 0)
        vid_bank_tech = 1;
    if (vid_bank_tech == 0)
        vid_tech = vid_bank_tech;
}

// FUNCTION: C2 0x24C7F
// Lines 771–799
//
// Diagnostic dump (stdout) of the VESA information collected by
// set_svga_640_480 / recognise_card / get_video_technique.  Skipped
// when vid_error != 0 (everything past the OEM string is
// uninitialised in that case).
//
void print_vesa_info(void)
{
    int oem;

    printf("\n--------------------------------------------------------\n");
    if (vid_error == 1) printf("Vesa SVGA not supported by this graphics card.\n");
    else if (vid_error == 2) printf("SVGA mode not supported by this graphics card.\n");
    else if (vid_error == 3) printf("VESA ext bios error :- failed to set bank.\n");
    else printf("VESA Compliant  - Video Card Information.\n");
    printf("--------------------------------------------------------\n");
    if (vid_error != 0) return;

    oem = (vesa_info.oem_string_seg << 4) + vesa_info.oem_string_off;
    printf("OEM string      : %s \n", (char *)oem);
    printf("VESA Version    : %d.%d,",
           ((short)vesa_info.version & 0xff00) >> 8,
           (short)vesa_info.version & 0xff);
    printf(" %s", chipset_names[card_is]);
    if (card_sub_type != 0) printf(" %d chipset.\n", card_sub_type);
    else printf(" chipset.\n");
    printf("Video memory    : %dk \n", vid_memory);
    printf("Attributes      : %x,%x,",
           vesa_mode_info.win_a_attributes,
           vesa_mode_info.win_b_attributes);
    if (vid_tech == 0) printf("S,"); else printf("C,");
    if (vid_bank_tech == 0) printf("S\n"); else printf("C\n");
    printf("Granularity     : %dk with %dk size ",
           vesa_mode_info.win_granularity,
           vesa_mode_info.win_size);
    printf("at  %x and %x \n",
           vesa_mode_info.win_a_segment,
           vesa_mode_info.win_b_segment);
    printf("Bank function   : %x \n", bank_ptr);
    printf("--------------------------------------------------------\n");
}

// FUNCTION: C2 0x24E3C
// Lines 802–826
//
// Switch the VGA into mode-X (320×200, 4 planes × 80 bytes), saving
// the touched register values into the old3*_* slots so unset_vga_256x
// can restore them. Read-modify-write each control register through
// `val` then push back via outp.
#ifdef __WATCOMC__
void set_vga_256x(void)
{
    char val;

    outp(0x3c4, 4);
    old3c5_4 = inp(0x3c5);
    outp(0x3ce, 5);
    old3cf_5 = inp(0x3cf);
    outp(0x3ce, 6);
    old3cf_6 = inp(0x3cf);
    outp(0x3d4, 0x14);
    old3d5_14 = inp(0x3d5);
    outp(0x3d4, 0x17);
    old3d5_17 = inp(0x3d5);

    set_vga_mode(0x13);

    outp(0x3c4, 4);
    val = (inp(0x3c5) & 0xf3) | 4;
    outp(0x3c5, val);

    outp(0x3ce, 5);
    val = inp(0x3cf) & 0xef;
    outp(0x3cf, val);

    outp(0x3ce, 6);
    val = inp(0x3cf) & 0xfd;
    outp(0x3cf, val);

    outp(0x3d4, 0x14);
    val = inp(0x3d5) & 0xbf;
    outp(0x3d5, val);

    outp(0x3d4, 0x17);
    val = inp(0x3d5) | 0x40;
    outp(0x3d5, val);

    clear_all_screens();
    oscreen = 0x4000;
    cscreen = 0;
    swap_screens();
    swap_screens();
    screen_width  = 320;
    screen_height = 200;
    screen_size   = 0xfa00;
}

// FUNCTION: C2 0x24FEF
// Lines 829–842
//
// Restore the VGA registers saved by set_vga_256x to leave the
// adapter in a sane mode-X state, after wiping all four pages.
void unset_vga_256x(void)
{
    clear_all_screens();
    outp(0x3c4, 4);
    outp(0x3c5, old3c5_4);
    outp(0x3ce, 5);
    outp(0x3cf, old3cf_5);
    outp(0x3ce, 6);
    outp(0x3cf, old3cf_6);
    outp(0x3d4, 0x14);
    outp(0x3d5, old3d5_14);
    outp(0x3d4, 0x17);
    outp(0x3d5, old3d5_17);
}

// FUNCTION: C2 0x2509C
// Lines 844–850
//
// Switch to text mode (BIOS int 10h, AX = 3).  Uses the 16-bit `w.ax`
// slot in the REGS union so the BIOS sees a word-sized argument.
void set_mode3(void)
{
    union REGS regs;
    regs.w.ax = 3;
    int386(0x10, &regs, &regs);
}

// FUNCTION: C2 0x250BB
// Lines 852–856
//
// Same shape as set_mode3 but takes the mode word as an argument.
void set_vga_mode(int mode)
{
    union REGS r;
    r.w.ax = mode;
    int386(0x10, &r, &r);
}

// FUNCTION: C2 0x250C6
// Lines 860–860
//
// Switches the EGA/VGA Graphics Controller to read from page 1.
void page1_read(void)
{
    outpw(0x3CE, 4);
}

// FUNCTION: C2 0x250D8
// Lines 864–875
//
// Push a 256×3 palette buffer to the VGA DAC. Sends 0xFF to the
// pixel-mask register (0x3C6) once, then for each colour writes the
// index to 0x3C8 and the R/G/B triple to 0x3C9.
void set_vga_palette(char *p)
{
    int i;
    outp(0x3c6, 0xff);
    for (i = 0; i < 256; i++) {
        outp(0x3c8, i);
        outp(0x3c9, *p++);
        outp(0x3c9, *p++);
        outp(0x3c9, *p++);
    }
}

// FUNCTION: C2 0x25134
// Lines 877–887
//
// Program the VGA DAC entries [start, end] (inclusive) from the
// 3-bytes-per-entry palette buffer at `p`.
void set_vga_palette_range(char *p, int start, int end)
{
    int i;
    for (i = start; i <= end; i++) {
        outp(0x3c8, i);
        outp(0x3c9, *p++);
        outp(0x3c9, *p++);
        outp(0x3c9, *p++);
    }
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x2517F
// Lines 889–907
//
// Rotate the colour entries in current_palette[start_idx..end_idx]
// (inclusive) by one slot toward higher indices: the colour that
// was at end_idx moves to start_idx, and every entry in between
// shifts up by one.  Pushes the result to the VGA DAC via
// set_vga_palette_range.
//
// Each palette entry is three bytes (R, G, B) packed flat -- so
// current_palette[3 * i .. 3 * i + 2] is one entry.
void cycle_colours(int start_idx, int end_idx)
{
    int i;
    char saved[3];

    saved[0] = current_palette[3 * end_idx + 0];
    saved[1] = current_palette[3 * end_idx + 1];
    saved[2] = current_palette[3 * end_idx + 2];

    for (i = end_idx; i > start_idx; i--) {
        current_palette[3 * i + 0] = current_palette[3 * (i - 1) + 0];
        current_palette[3 * i + 1] = current_palette[3 * (i - 1) + 1];
        current_palette[3 * i + 2] = current_palette[3 * (i - 1) + 2];
    }

    current_palette[3 * start_idx + 0] = saved[0];
    current_palette[3 * start_idx + 1] = saved[1];
    current_palette[3 * start_idx + 2] = saved[2];

    set_vga_palette_range(&current_palette[3 * start_idx], start_idx, end_idx);
}

// FUNCTION: C2 0x25226
// WIN: 0x0044b659
// Lines 909–929
//
// Three-slot red flash effect.  Increments slot[idx]'s red channel
// by `delta`, capping wraparound to 0x10 (so it never blows past
// 0x3F into invalid territory).  Slots [idx+1] and [idx+2] get the
// same red component but progressively brighter green channels --
// red/2 and (3*red)/4 -- producing a yellow-tinted falloff.
// Blue is always zero across all three slots.
void pulse_red(int idx, int delta)
{
    unsigned char red;

    red = current_palette[3 * idx + 0];
    red += delta;
    if (red > 0x3f) red = 0x10;

    current_palette[3 * idx + 0] = red;
    current_palette[3 * idx + 1] = 0;
    current_palette[3 * idx + 2] = 0;

    current_palette[3 * (idx + 1) + 0] = red;
    current_palette[3 * (idx + 1) + 1] = red / 2;
    current_palette[3 * (idx + 1) + 2] = 0;

    current_palette[3 * (idx + 2) + 0] = red;
    current_palette[3 * (idx + 2) + 1] = (3 * red) / 4;
    current_palette[3 * (idx + 2) + 2] = 0;

    set_vga_palette_range(&current_palette[3 * idx], idx, idx + 2);
}

// FUNCTION: C2 0x252DE
// WIN: 0x0044b730
// Lines 931–938
//
// Toggle palette entry 0 between black and full-red, set the rest
// of the entry to 0, and reload the VGA palette.
void swap_background_to_red(void)
{
    if (current_palette[0] == 0x3f)
        current_palette[0] = 0;
    else
        current_palette[0] = 0x3f;
    current_palette[1] = 0;
    current_palette[2] = 0;
    set_vga_palette_range(current_palette, 0, 0);
}

// FUNCTION: C2 0x2531C
// WIN: 0x0044b77d
// Lines 940–949
//
// Copy palette entry `idx` (RGB triple) into entry 0 and reload the
// VGA palette.
void swap_background_to(int idx)
{
    int r = current_palette[idx*3];
    int g = current_palette[idx*3 + 1];
    int b = current_palette[idx*3 + 2];
    current_palette[0] = r;
    current_palette[1] = g;
    current_palette[2] = b;
    set_vga_palette_range(current_palette, 0, 0);
}

// FUNCTION: C2 0x2534F
// (CAESAR2.EXE slot undetermined: the palette/background block is reordered
//  between PS and the temporally-distant CAESAR2.EXE port, so the old
//  0x0044b7e1 annotation — which is actually set_palette — was wrong.)
// Lines 966–975
//
// Copy 256 RGB triples (3 bytes each) from src to dst.
void copy_palette(char *src, char *dst)
{
    int i;
    for (i = 0; i < 256; i++) {
        dst[i*3]   = src[i*3];
        dst[i*3+1] = src[i*3+1];
        dst[i*3+2] = src[i*3+2];
    }
}

// FUNCTION: C2 0x25384
// WIN: 0x0044b87c
// Lines 977–986
//
// Right-shift every channel of a 256-entry palette by 2 (6-bit
// VGA → 4-bit hi-color downsample).
void go_64k_palette(char *p)
{
    int i;
    for (i = 0; i < 256; i++) {
        p[i*3]   >>= 2;
        p[i*3+1] >>= 2;
        p[i*3+2] >>= 2;
    }
}

// FUNCTION: C2 0x253AB
// WIN: 0x0044b8f7
// Lines 988–997
//
// Expand a 256-entry VGA palette in-place from 6-bit channels to the
// 8-bit-ish form used by the screenshot writer.
// after this function's ret (the donor for fade_to_palette et al.) and
// is not part of this function's body — do not chase it.
void go_16m_palette(char *p)
{
    int i;

    for (i = 0; i < 256; i++) {
        p[i * 3] <<= 2;
        p[i * 3 + 1] <<= 2;
        p[i * 3 + 2] <<= 2;
    }
}

// FUNCTION: C2 0x255B1
// WIN: 0x0044b9a7
//
// Fade current_palette one step at a time toward `p`, allowing mouse
// clicks to skip the inter-step delay.  PS tail-jumps this function
// into the hidden shared fade tail parked after go_16m_palette; this
// straightforward version is semantically faithful but non-exact.
void fade_to_palette(char *p)
{
    short i;
    short j;
    int waited;
    int wait_limit;
    char changed;
    char target;
    char cur;
    short fade_step;

    wait_limit = 5;
    for (fade_step = 0; fade_step < 300; fade_step++) {
        changed = 0;
        j = 0;
        get_mouse();
        if ((mouse_left_preclick || mouse_right_preclick) && !debar_fade_click) wait_limit = 0;
        waited = 0;
        while (j < 20000) {
            waited += running_delay1();
            if (waited >= wait_limit) break;
            j++;
        }

        for (i = 0; i < 256; i++) {
            target = p[i * 3];
            cur = current_palette[i * 3];
            if (cur > target) {
                changed = 1;
                cur--;
            } else if (cur < target) {
                if (fade_step >= (unsigned char)cur) {
                    changed = 1;
                    cur++;
                }
            }
            current_palette[i * 3] = cur;

            target = p[i * 3 + 1];
            cur = current_palette[i * 3 + 1];
            if (cur > target) {
                changed = 1;
                cur--;
            } else if (cur < target) {
                if (fade_step >= (unsigned char)cur) {
                    changed = 1;
                    cur++;
                }
            }
            current_palette[i * 3 + 1] = cur;

            target = p[i * 3 + 2];
            cur = current_palette[i * 3 + 2];
            if (cur > target) {
                changed = 1;
                cur--;
            } else if (cur < target) {
                if (fade_step >= (unsigned char)cur) {
                    changed = 1;
                    cur++;
                }
            }
            current_palette[i * 3 + 2] = cur;
        }

        if (!changed) break;
        set_vga_palette(current_palette);
    }

    set_palette(p);
    debar_fade_click = 0;
}
// FUNCTION: C2 0x2550B
// WIN: 0x0044bbce
// Lines 1050–1054
//
// Read 0x300 bytes (256 RGB triples) into temp_palette and apply.
void load_to_temp_palette(char *fname)
{
    readfile(fname, temp_palette, 0x300, 0);
    set_palette(temp_palette);
}

// FUNCTION: C2 0x2552D
// WIN: 0x0044bbfe
// Lines 1056–1060
//
// Same as load_to_temp_palette but fades into the new palette.
void fade_to_temp_palette(char *fname)
{
    readfile(fname, temp_palette, 0x300, 0);
    fade_to_palette(temp_palette);
}

// FUNCTION: C2 0x2554F
// WIN: 0x0044bc2e  (unverified)
// Lines 1062–1062
//
// Forwarder that pushes the all-zero palette via
// set_palette(black_out_data).
void black_out(void)
{
    set_palette(black_out_data);
}

// FUNCTION: C2 0x25554
// WIN: 0x0044b7e1
//
// Copy a 256×3 palette buffer to current_palette and push it to the
// VGA DAC. The trailing assignments to current_palette[0..2] force
// VGA colour 0 to black regardless of the source palette.
void set_palette(char *p)
{
    int i;
    for (i = 0; i < 256; i++) {
        current_palette[i*3]     = p[i*3];
        current_palette[i*3 + 1] = p[i*3 + 1];
        current_palette[i*3 + 2] = p[i*3 + 2];
    }
    current_palette[2] = 0;
    current_palette[1] = 0;
    current_palette[0] = 0;
    set_vga_palette(current_palette);
}

// FUNCTION: C2 0x255AC
// WIN: 0x0044bc46  (unverified)
// Lines 1067–1067
//
// Forwarder: fade the screen to the all-black palette.
void fade_to_black_out(void)
{
    fade_to_palette(black_out_data);
}



// FUNCTION: C2 0x255CB
// Lines 1076–1078
//
// Wait for a complete vertical-blank cycle on port 0x3DA bit 3.
#ifdef __WATCOMC__
void wvbl2(void)
{
    while (inp(0x3DA) & 8) ;
    while (!(inp(0x3DA) & 8)) ;
}

// FUNCTION: C2 0x255E8
// Lines 1080–1092
//
// Toggle the active framebuffer page (cscreen / oscreen) by
// reprogramming the CRTC start-address registers and flipping a
// private page flag.
void swap_screens(void)
{
    static int page_flag;

    outpw(0x3d4, 0x0d);
    outpw(0x3d4, cscreen + 0xc);
    page_flag ^= 1;
    if (page_flag != 0) {
        oscreen = 0x4000;
        cscreen = 0;
    } else {
        oscreen = 0;
        cscreen = 0x4000;
    }
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x25645
// WIN: 0x0044bc74
// Lines 1094–1104
//
// De-interleave a 4-plane mode-X buffer (4 × 0x3E80 bytes) back into
// a contiguous 256×N raster.
void convert256x_to_256screen(char *src, char *dst)
{
    int i;
    for (i = 0; i < 0x3e80; i++) {
        dst[i*4]     = src[i];
        dst[i*4 + 1] = src[i + 0x3e80];
        dst[i*4 + 2] = src[i + 0x7d00];
        dst[i*4 + 3] = src[i + 0xbb80];
    }
}

// FUNCTION: C2 0x25686
// WIN: 0x0044bcfa
// Lines 1106–1119
//
// Repack a 320×200 linear-256 framebuffer (`src` is 64,000 bytes
// of one byte per pixel in row-major order) into the four-plane
// VGA mode-X layout used by `dst`.  Mode-X interleaves pixels in
// groups of four across four 16,000-byte planes (a, b, c, d).
// We unroll the inner loop two-pixels-per-plane-per-step, so each
// pass through the loop body copies 8 source bytes into 8
// destination bytes spread over the four planes.
void convert256_to_256xscreen(unsigned char *src, unsigned char *dst)
{
    int i;
    int s;

    i = 0;
    s = 0;
    for (; i < 0x3e80; i += 2, s += 8) {
        dst[i]            = src[s];
        dst[i + 0x3e80]   = src[s + 1];
        dst[i + 0x7d00]   = src[s + 2];
        dst[i + 0xbb80]   = src[s + 3];
        dst[i + 1]        = src[s + 4];
        dst[i + 0x3e81]   = src[s + 5];
        dst[i + 0x7d01]   = src[s + 6];
        dst[i + 0xbb81]   = src[s + 7];
    }
}

// FUNCTION: C2 0x256F8
// Lines 1122–1126
//
// Dispatch on screen_mode to the right physical-screen blitter.
// (Dead in PS.EXE: 0 xrefs, but the engine kept it for completeness.
// The two pass-through params are forwarded straight to the chosen
// blitter via the __watcall ABI's EAX/EDX register pair.)
void copy_to_physical_screen(int p1, int p2)
{
    if (screen_mode == 1) {
        convert_and_copy_to_256xscreen(p1, p2);
        return;
    }
    copy_to_640_480_screen(p1);
}

// FUNCTION: C2 0x25714
// Lines 1128–1138
//
// Clear all four 64K screen pages (mode-X). Falls through to
// clear_a_screen for the non-256x case.
void clear_screens(void)
{
    if (screen_mode == 1) {
        cls_256x(0,       0xfa00);
        cls_256x(0x4000,  0xfa00);
        cls_256x(0x8000,  0xfa00);
        cls_256x(0xc000,  0xfa00);
    } else {
        clear_a_screen();
    }
}

// FUNCTION: C2 0x25763
// WIN: 0x0044be1d  (unverified)
// Lines 1140–1154
//
// Wipe the current visible page. In mode 1 (320×200 mode-X) defer to
// cls_256x; in modes 2/3 (640×480 / 640×400 linear) zero the
// internal_screen buffer byte-by-byte.
void clear_a_screen(void)
{
    int i;
    if (screen_mode == 1) {
        cls_256x(cscreen, 0xfa00);
        return;
    }
    if (screen_mode == 2) {
        if (internal_screen == 0)
            return;
        for (i = 0; i < 0x4b000; i++)
            internal_screen[i] = 0;
        return;
    }
    if (screen_mode == 3) {
        if (internal_screen == 0)
            return;
        for (i = 0; i < 0x3e800; i++)
            internal_screen[i] = 0;
    }
}

// FUNCTION: C2 0x257C9
// WIN: 0x0044be4a
// Lines 1156–1176
//
// Convert the live 320x240 internal_screen to greyscale.  Only runs
// in screen_mode 2 (the 320x240 mode) and only when internal_screen
// is mapped.  Builds a 256-entry lookup mapping each VGA palette
// index i to a grey shade based on the red component of that
// palette entry, then runs every pixel of the 0x4B000 (= 307_200,
// = 320*240*4) byte framebuffer through the table.
//
// The grey value is `0x3F - r/2` where `r` is the red channel --
// inverted intensity (low red -> bright grey, high red -> dim grey)
// to keep the colour relationship roughly visible after the filter.
// PS accumulates `total` via three separate reads of the same
// palette byte (the CAESAR2.EXE /Od build shows three memory adds
// into the same slot); Watcom CSEs the three `current_palette[n]`
// loads into one register, producing the mov/add/add average.
void grey_a_screen(void)
{
    int i;
    int n;
    int total;
    int idx;

    if (screen_mode != 2)         return;
    if (internal_screen == 0)     return;

    for (i = 0; i < 0x100; i++)
    {
        n = i * 3; total = (unsigned char)current_palette[n];
        total += (unsigned char)current_palette[n];
        total += (unsigned char)current_palette[n]; total /= 3;
        greying_data[i] = (unsigned char)(0x3f - (total >> 1));
    }

    for (i = 0; i < 0x4b000; i++)
    {
        idx = internal_screen[i];
        internal_screen[i] = greying_data[idx];
    }
}

// FUNCTION: C2 0x25845
// Lines 1178–1188
//
// Wipe all four 64K mode-X pages — same as clear_screens but uses
// the high-cleared-byte 0xa000 region as the fourth page.
void clear_all_screens(void)
{
    cls_256x(0,      0x10000);
    cls_256x(0x4000, 0x10000);
    cls_256x(0x8000, 0x10000);
    cls_256x(0xa000, 0x10000);
}

// FUNCTION: C2 0x25880
// (no confirmed CAESAR2.EXE slot; old 0x00401384 was a placeholder.)
//
// Empty trailer for the CBC encryption tail — a single `ret`.
void cbc_end(void)
{
}

// FUNCTION: C2 0x25881
// Lines 1190–1197
//
// BIOS int 10h fn 6: scroll up, full text screen with attribute 7
// (effective text-mode CLS).
#ifdef __WATCOMC__
void dos_cls(void)
{
    union REGS r;
    r.w.cx  = 0;
    r.w.dx  = 0x1850;
    r.h.bh  = 7;
    r.w.ax  = 0x600;
    int386(0x10, &r, &r);
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x258A4
// Lines 1281–1293
//
// Real-mode mouse-callback (DOS int 0x33 function 0x0C).  Installed
// by `install_mouse`; the mouse driver calls this with AX = event
// mask, BX = button state, CX = X, DX = Y, SI = mickey-X,
// DI = mickey-Y.  We snapshot all six registers into the cbd
// (callback-data-block), set cbd[+4] = 1 to mark new data, and on a
// click (bit 3 of AX) set cbd[0] = 1.  Far return back to the
// driver.
#pragma aux click_handler __loadds parm [eax] [ebx] [ecx] [edx] [esi] [edi];
void __far click_handler(unsigned int ax, unsigned int bx,
                         unsigned int cx, unsigned int dx,
                         unsigned int si, unsigned int di)
{
    cbd.pending = 1;
    cbd.ax = ax;
    cbd.bx = bx;
    cbd.cx = cx;
    cbd.dx = dx;
    cbd.si = si;
    cbd.di = di;
    if ((cbd.ax & 8) != 0)
        cbd.click_flag = 1;
}

/* ---- Stack-overflow checking turns ON here (PS source line ~1300) ----
 *
 * The whole game is built with `-s` (stack-overflow checks off), but the
 * back half of lib32.c runs WITH checks: every function from
 * `install_mouse` to the end of the file emits a `__CHK` prologue
 * (107 functions in PS.EXE; the front half, lines 352-1281, has none).
 * The split is a clean source-line threshold with no exceptions, and
 * the `-d1` line numbers run monotonically straight across it, so this
 * is ONE translation unit toggled by a `#pragma on(check_stack)` in the
 * source -- NOT a separate object compiled without `-s`.
 *
 * Why the original author guarded only this region: everything from
 * `install_mouse` on is the variable-depth / recursion-prone graphics
 * and input code -- the mouse callback path, the Bresenham/line/box/
 * diamond drawing primitives, the font layout + format-buffer machinery,
 * delays and key polling -- where a stack blowout during development was
 * a live risk.  The unchecked front half is flat, shallow hardware/file
 * setup (VGA mode sets, palette pokes, fades, file I/O, screen blits)
 * that the global `-s` covers safely.
 *
 * `__CHK` here is the genuine overflow check (`__STK` compares the
 * projected frame base against `_STACKLOW`), not a >4 KB page probe:
 * 8-20 byte accessor frames call it, while `__GRO` (the page-probe
 * helper) has zero callers.  See docs/build-environment.md.
 *
 * We compile the file globally with `-s`, so flip the pragma back on
 * locally to match PS.EXE. */
#pragma on(check_stack);

/* click_handler is an `__interrupt __far` callback installed via
 * DPMI int 0x33 fn 0x0C.  Excluded from c2_funcs.h (see
 * _IMPLICIT_INT_FUNCTIONS in c2/commands/c_source.py) because
 * pycparser drops the storage-class modifiers; forward-declare it
 * here so install_mouse can take its address. */

// FUNCTION: C2 0x258F3
// Lines 1300–1338
//
// Probe for a real-mode mouse driver via int 0x33, lock the cbd
// callback-data-block and click_handler code page into physical
// memory (DPMI is allowed to swap them out otherwise; we'd hit a
// page fault from within the real-mode mouse driver's callback),
// set the custom graphics cursor (int 0x33 function 9) from the
// mouse_ptr mask, then arm function 0x0C with a click_handler
// far-pointer and the PS event mask.
#ifdef __WATCOMC__
void install_mouse(void)
{
    union REGS out;
    union REGS in;
    struct SREGS sr;

    mouse_installed = 0;
    segread(&sr);
    in.w.ax = 0;
    int386(0x33, &in, &out);
    mouse_installed = (out.w.ax == -1);
    if (mouse_installed == 0) return;

    if (lock_region((int)&cbd, 0x14) == 0 ||
        lock_region((int)click_handler,
                    (char *)cbc_end - (char *)click_handler) == 0) {
        exit_flag = 1; return;
    }
    in.w.ax = 1;
    int386(0x33, &in, &out);
    in.w.ax = 9;
    in.w.bx = 0;
    in.w.cx = 0;
    in.x.edx = FP_OFF(mouse_ptr);
    sr.es = FP_SEG(mouse_ptr);
    int386x(0x33, &in, &out, &sr);
    in.w.ax = 0xc;
    in.w.cx = 1;
    in.x.edx = FP_OFF(click_handler);
    sr.es = FP_SEG(click_handler);
    int386x(0x33, &in, &out, &sr);
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x25A0C
// WIN: 0x0044bf7b
// Lines 1340–1350
//
// Drain the deferred mouse-call buffer (cbd) into mse_x/mse_y/mse_button.
void read_installed_mouse(void)
{
    if (mouse_installed == 0) return;
    if (cbd.pending == 0)     return;
    mse_x      = cbd.cx;
    mse_y      = cbd.dx;
    mse_button = (char)cbd.bx;
    cbd.pending = 0;
}

// FUNCTION: C2 0x25A55
// Lines 1353–1363
//
// Hide the mouse cursor (int 33h fn 2) then reset the mouse driver
// (int 33h fn 0) when one is installed.
#ifdef __WATCOMC__
void de_install_mouse(void)
{
    union REGS in;
    union REGS out;
    if (mouse_installed == 0)
        return;
    in.w.ax = 2;
    int386(0x33, &in, &out);
    in.w.ax = 0;
    int386(0x33, &in, &out);
}

// FUNCTION: C2 0x25AA1
// Lines 1375–1385
//
// Reset the mouse driver (int 33h fn 0); cache the result in
// `mouse_installed` and return it.
int init_mouse(void)
{
    union REGS in;
    union REGS out;
    memset(&in, 0, sizeof(in));
    in.w.ax = 0;
    int386(0x33, &in, &out);
    mouse_installed = out.w.ax;
    if (mouse_installed < 0)
        mouse_installed = 0;
    return mouse_installed;
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x25AF3
// Lines 1389–1395
//
// Constrain the mouse cursor to the active screen mode's resolution.
// No-op if no mouse is installed or screen_mode isn't 1/2/3.
void set_mouse_limits(void)
{
    if (mouse_installed == 0)
        return;
    if (screen_mode == 1)
        mouserange(0, 0, 320, 200);
    else if (screen_mode == 3)
        mouserange(0, 0, 640, 400);
    else if (screen_mode == 2)
        mouserange(0, 0, 640, 480);
}

// FUNCTION: C2 0x25B4E
// Lines 1398–1411
//
// Configure the int 33h driver's horizontal (fn 7) and vertical
// (fn 8) cursor limits.  Zeroes the full REGS union before each
// int386 call so any reserved register slots are left clear.
#ifdef __WATCOMC__
void mouserange(int xmin, int ymin, int xmax, int ymax)
{
    union REGS r;
    int hi_x = xmax;
    memset(&r, 0, 0x1c);
    r.w.ax = 7;
    r.w.cx = xmin;
    r.w.dx = hi_x;
    int386(0x33, &r, &r);
    r.w.ax = 8;
    r.w.cx = ymin;
    r.w.dx = ymax;
    int386(0x33, &r, &r);
}

// FUNCTION: C2 0x25BB9
// WIN: 0x0044c055
// Lines 1424–1433
//
// Read the mouse position via int 33h fn 3 and update mse_x, mse_y
// and mse_button.
void read_mouse(void)
{
    union REGS r;
    memset(&r, 0, 0x1c);
    r.w.ax = 3;
    int386(0x33, &r, &r);
    mse_x = r.w.cx;
    mse_y = r.w.dx;
    mse_button = r.w.bx;
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x25C0C
// Lines 1436–1439
//
// Poll the mouse until the user clicks any button.
void wait_click(void)
{
    do {
        read_mouse();
    } while (mse_button == 0);
}

// FUNCTION: C2 0x25C25
// WIN: 0x0044c18a
// Lines 1441–1447
//
// Drain any held mouse buttons and reset the click/preclick latches.
void clear_mouse(void)
{
    do {
        get_mouse();
    } while (mouse_left_button != 0 || mouse_right_button != 0);
    mouse_right_click    = 0;
    mouse_left_click     = 0;
    mouse_right_preclick = 0;
    mouse_left_preclick  = 0;
}

// FUNCTION: C2 0x25C60
// WIN: 0x0044c1da
// Lines 1449–1452
//
// Update the cached (mouse_x, mouse_y) and push them to the driver
// via set_mouse (int 33h fn 4).
void position_mouse(short x, short y)
{
    mse_x   = x;
    mouse_x = x;
    mse_y   = y;
    mouse_y = y;
    set_mouse();
}

// FUNCTION: C2 0x25C85
// Lines 1453–1453
//
// Push the cached (mse_x, mse_y) to the mouse driver via int 33h fn 4.
#ifdef __WATCOMC__
void set_mouse(void)
{
    union REGS r;
    memset(&r, 0, sizeof(r));
    r.w.ax = 4;
    r.w.cx = mse_x;
    r.w.dx = mse_y;
    int386(0x33, &r, &r);
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x25CCC
// WIN: 0x0044c216
// Lines 1456–1489
//
// Pump the mouse driver and update the engine's mouse state.  Tries
// sim_mouse() first (replay-from-recording / inter-net sync feeder);
// on no replay frame falls through to read_mouse() which polls INT
// 33h.  Snapshots last frame's (x, y, lb, rb) into the old_mouse_*
// shadows, sign-extends mse_x/y into mouse_x/y, then decodes the
// mse_button bitmask (bit 0 = left, bit 1 = right).  Sets
// mouse_movement when any axis or button changed.  On a left-button
// transition arms mouse_left_preclick (newly pressed) or
// mouse_left_click (newly released); the right button is mirrored.
// mse_button is then cleared so the next frame starts fresh.

void get_mouse(void)
{
    int one;

    if (sim_mouse() == 0) {
        read_mouse();
    }
    mouse_movement = 0;
    old_mouse_x = mouse_x;
    old_mouse_y = mouse_y;
    old_mouse_lb = mouse_left_button;
    old_mouse_rb = mouse_right_button;
    mouse_x = mse_x;
    mouse_y = mse_y;

    mouse_left_button   = 0;
    mouse_left_preclick = 0;
    mouse_left_click    = 0;
    mouse_right_button   = 0;
    mouse_right_preclick = 0;
    mouse_right_click    = 0;

    if ((mse_button & 2) != 0) mouse_right_button = 1;
    if ((mse_button & 1) != 0) mouse_left_button  = 1;

    if (old_mouse_x != mouse_x) mouse_movement = 1;
    if (old_mouse_y != mouse_y) mouse_movement = 1;

    if (mouse_left_button != old_mouse_lb) {
        one = 1;
        mouse_movement   = one;
        mouse_was_pressed = one;
        if (mouse_left_button == one) {
            mouse_left_preclick = 1;
        } else if (mouse_left_button == 0) {
            mouse_left_click = 1;
        }
    }

    if (mouse_right_button != old_mouse_rb) {
        one = 1;
        mouse_movement   = one;
        mouse_was_pressed = one;
        if (mouse_right_button == one) {
            mouse_right_preclick = 1;
        } else if (mouse_right_button == 0) {
            mouse_right_click = 1;
        }
    }

    mse_button = 0;
}

// FUNCTION: C2 0x25E33
// WIN: 0x0044c3d3
// Lines 1491–1513
//
// Mouse-cursor variant of write_image().  Same packed-descriptor
// layout (16-byte entries, +8 header skip; +0..+1 width LE u16,
// +2..+3 height LE u16, +4..+6 start LE u24) but reads the
// descriptor from the global 'mice' bank, places the sprite at
// (mouse_x, mouse_y), and adds sanity bounds:
//
//   sprite_start  <= 0x4baf0   (within mouse_bank)
//   sprite_width  in (0, 300]
//   sprite_height in (0, 300]
//
// Any out-of-range descriptor is silently dropped (no draw, no
// global state corruption past sprite_start) -- this guards
// against junk indices on screens the cursor tile-set hasn't
// loaded yet.  Then dispatches to write_i_*_sprite via xclip/
// yclip's xclipped flag, exactly as write_image() does.
void show_mouse(int id)
{
    data_ptr = id * 16 + 8;

    sprite_width  = mice[data_ptr]     + (mice[data_ptr + 1] << 8);
    sprite_height = mice[data_ptr + 2] + (mice[data_ptr + 3] << 8);
    sprite_start  = mice[data_ptr + 4] + (mice[data_ptr + 5] << 8);

    if (sprite_start > 0x4baf0) return;
    if (sprite_width  <= 0)     return;
    if (sprite_width  > 300)    return;
    if (sprite_height <= 0)     return;
    if (sprite_height > 300)    return;

    sprite_x = mouse_x;
    sprite_y = mouse_y;

    xclip(0, screen_width);
    yclip(0, screen_height);

    if (yclipped == 5) return;

    if (xclipped == 1) {
        write_i_left_sprite(mice);
    } else if (xclipped == 2) {
        write_i_right_sprite(mice);
    } else {
        write_i_sprite(mice);
    }
}

// FUNCTION: C2 0x25F52
// WIN: 0x0044c5dc
// Lines 1520–1532
//
// Snapshot the current mouse position into sprite_x / sprite_y,
// clamp to (0, 0) — (screen_w-24, screen_h-24), stash the clamped
// coords as the next-frame `old_mouse_drops_*`, and pick up the
// background tile under the cursor.
void get_mouse_droppings(void)
{
    sprite_x = mouse_x;
    sprite_y = mouse_y;
    if (sprite_x < 0)
        sprite_x = 0;
    if (sprite_y < 0)
        sprite_y = 0;
    if (screen_width  - 0x18 < sprite_x)
        sprite_x = screen_width  - 0x18;
    if (screen_height - 0x18 < sprite_y)
        sprite_y = screen_height - 0x18;
    old_mouse_drops_x = sprite_x;
    old_mouse_drops_y = sprite_y;
    pick_up_mouse_background(mouse_background);
}

// FUNCTION: C2 0x25FDF
// WIN: 0x0044c68c
// Lines 1534–1540
//
// Restore the mouse-background sprite at the last drop coordinates;
// no-op while hold_mouse_replace is set.
void cover_mouse_droppings(void)
{
    if (hold_mouse_replace != 0) {
        hold_mouse_replace = 0;
        return;
    }
    sprite_x = old_mouse_drops_x;
    sprite_y = old_mouse_drops_y;
    put_down_mouse_background(mouse_background);
}

// FUNCTION: C2 0x2601D
// WIN: 0x0044c6d3
// Lines 1542–1548
//
// 1 if (mouse_x, mouse_y) is inside the half-open rectangle
// [x, x+w) x [y, y+h), 0 otherwise.
int mouse_in_area(int x, int y, int w, int h)
{
    if (x <= mouse_x) {
        if (x + w > mouse_x) {
            if (y <= mouse_y) {
                if (y + h > mouse_y) {
                    return 1;
                }
            }
        }
    }
    return 0;
}

// FUNCTION: C2 0x26056
// WIN: 0x0044c7aa
// Lines 1552–1564
//
// Non-blocking keyboard poll.  Always clears key_ready and key_ascii
// up front; if kbhit() reports a pending byte, fills the four key_*
// globals from getch():
//
//   key_ready     = 1            (caller's "did we read a key?" flag)
//   key_ascii_was = key_ascii    (snapshot of the *previous* ASCII --
//                                 here always 0 because we just zeroed
//                                 it; left in to preserve PS layout)
//   key_code      = 0
//   key_ascii     = getch()
//   if key_ascii == 0:           (extended-key prefix byte)
//       key_code  = getch()      (the actual scan code)
void get_key(void)
{
    key_ready = 0;
    key_ascii = 0;
    if (kbhit()) {
        key_ascii_was = key_ascii;
        key_ready = 1;
        key_code = 0;
        key_ascii = getch();
        if (key_ascii == 0) {
            key_code = getch();
        }
    }
}

// FUNCTION: C2 0x260AB
// WIN: 0x0044c7fa
// Lines 1566–1571
//
// Drain the keyboard buffer then block until the next key event.
void wait_key(void)
{
    clear_keys();
    do {
        get_key();
    } while (key_ready == 0);
}

// FUNCTION: C2 0x260C9
// WIN: 0x0044c81e
// Lines 1573–1576
//
// Set key_ready and drain via get_key() until it clears.
void clear_keys(void)
{
    key_ready = 1;
    while (key_ready != 0)
        get_key();
}

// FUNCTION: C2 0x260EA
// Lines 1581–1587
//
// Bounded byte-compare of two strings: returns 1-based index of first
// mismatch, or 0 if all `n` bytes are equal.
int my_strcmp(char *s1, char *s2, int n)
{
    int i;
    for (i = 0; i < n; i++) {
        if (s2[i] != s1[i])
            return i + 1;
    }
    return 0;
}

// FUNCTION: C2 0x26118
// WIN: 0x0044c8a5
// Lines 1589–1593
//
// Bounded byte-copy of `n` bytes from src to dst.
void my_strcpy(char *src, char *dst, int n)
{
    int i;
    for (i = 0; i < n; i++)
        dst[i] = src[i];
}

// FUNCTION: C2 0x2613E
// WIN: 0x0044c8e5
// Lines 1595–1599
//
// Uppercase a single ASCII letter; non-letters pass through.
// Param/return are `char` — PS spills via dl/edx for the (promoted)
// compare and modifies `al` directly for the byte subtract.
char to_upper(char c)
{
    if (c >= 'a' && c <= 'z')
        c -= 0x20;
    return c;
}

// FUNCTION: C2 0x2615B
// WIN: 0x0044c91f
// Lines 1601–1610
//
// Uppercase every ASCII letter in `s` in place.
void string_to_upper(char *s)
{
    char c;
    while ((c = *s) != 0) {
        if (c >= 'a' && c <= 'z')
            c -= 0x20;
        *s = c;
        s++;
    }
}

// FUNCTION: C2 0x26187
// WIN: 0x0044c97b
// Lines 1613–1617
//
// Shift bytes of [p, end) one position left and null-terminate at *end.
void pull_string_left(char *p, char *end)
{
    while (p < end) {
        *p = *(p + 1);
        p++;
    }
    *p = 0;
}

// FUNCTION: C2 0x261A5
// WIN: 0x0044c9ab
// Lines 1619–1622
//
// Mirror of pull_string_left: shift bytes from `start..end-1` one
// position right, pad with NUL at end+1.
void push_string_right(char *start, char *end)
{
    end[1] = 0;
    while (end > start) {
        *end = end[-1];
        end--;
    }
}

// FUNCTION: C2 0x261C2
// WIN: 0x0044c9dc
// Lines 1625–1631
//
// Drop leading spaces by repeatedly shifting the string left until
// the first character is non-space.
void strip_leading_space(signed char *s)
{
    int i;
    while (*s == ' ') {
        i = 0;
        while (s[i] != 0) {
            s[i] = s[i + 1];
            i++;
        }
    }
}

// FUNCTION: C2 0x261EF
// WIN: 0x0044ca32
// Lines 1635–1640
//
// Strip trailing spaces by walking back from the NUL and writing 0
// over any space. Tail-merges into set_mouse_limits's epilogue.
void strip_trailing_space(signed char *s)
{
    int i;
    i = 0;
    while (s[i] != 0)
        i++;
    do {
        i--;
        if (s[i] != ' ')
            return;
        s[i] = 0;
    } while (1);
}

// FUNCTION: C2 0x2621E
// WIN: 0x0044ca89
// Lines 1643–1658
//
// Collapse runs of inner spaces in the NUL-terminated string `s`.
// The first loop finds `len = strlen(s)` capped at 0xfa00.  The
// second loop walks 0..len-1: a space immediately after a non-space
// triggers `pull_string_left(p - 1, &s[len])` (which shifts the tail
// of the string left by one; `len` is NOT decremented as the loop
// bound).  Used to canonicalise
// player-entered names.
void strip_spaces(char *s)
{
    int len;
    int i;
    int prev_was_nonspace = 0;

    for (i = 0; i < 0xfa00; i++) {
        if (s[i] == 0) {
            len = i;
            break;
        }
    }
    for (i = 0; i < len; i++) {
        if (s[i] == 0) return;
        if ((signed char)s[i] == ' ') {
            if (prev_was_nonspace) {
                i--;
                pull_string_left(s + i, s + len);
            } else {
                prev_was_nonspace = 1;
            }
        } else {
            prev_was_nonspace = 0;
        }
    }
}

// FUNCTION: C2 0x26284
// WIN: 0x0044cb61
// Lines 1660–1685
//
// Pixel-width measurement for a NUL-terminated string in one of
// the variable-width game fonts.  Walks the string char by char
// (capped at 10000 iterations as a runaway guard), and for each
// codepoint:
//
//   * ' '  -> 4 px (the standard inter-word gap, no glyph fetch).
//   * other-> look up the glyph id in letter_table[c - ' '].  A
//     zero entry means "no glyph" (skipped silently); otherwise the
//     glyph index is decremented (table is 1-based) and the glyph
//     header (16 bytes per glyph, starting at +8 in the font block)
//     is consulted at byte offset font_id (16-bit width field).
//     The width is added to the total, plus 1 px of inter-glyph
//     padding.
//
// sprite_image_no and data_ptr are scratch globals used by the
// underlying glyph-fetch helper -- they're set here so the next
// blit-string call can reuse them without repeating the lookup.
int get_string_width(char *src, unsigned char *font)
{
    int total;
    int count;
    char c;

    count = 0x2710;
    total = 0;
    while (count > 0) {
        c = *src;
        src++;
        if (c == 0) return total;
        if (c == ' ') {
            total += 4;
        } else {
            sprite_image_no = letter_table[c - ' '];
            if (sprite_image_no != 0) {
                sprite_image_no--;
                data_ptr = sprite_image_no * 16 + 8;
                total += font[data_ptr] + font[data_ptr + 1] * 256;
                total++;
            }
        }
        count--;
    }
    return total;
}

// FUNCTION: C2 0x26305
// WIN: 0x0044cc2a
// Lines 1687–1700
//
// Pixel width of a single ASCII character in the given font.
// 0 → empty letter; ' ' → fixed 4-px space; otherwise look up
// the sprite index in `letter_table` (indexed by `letter -
// 0x20`) and read the 16-bit little-endian width word from the font
// atlas at offset (sprite_idx-1)*16 + 8.  PS adds 1 for inter-letter
// padding.
int get_letter_width(int letter, unsigned char *font)
{
    char c;
    int result;
    c = (char)letter;
    if (c == 0) result = 0;
    else if (c == ' ') result = 4;
    else {
        sprite_image_no = letter_table[c - 0x20];
        if (sprite_image_no == 0) result = 0;
        else {
            sprite_image_no = sprite_image_no - 1;
            data_ptr = sprite_image_no * 16 + 8;
            result = (font[data_ptr] + font[data_ptr + 1] * 0x100) + 1;
        }
    }
    return result;
}

// FUNCTION: C2 0x26367
// WIN: 0x0044ccd7
// Lines 1703–1720
//
// Parse a leading run of ASCII digits from `text` and return
// its decimal value.  Walks the text twice: first to count
// digits, then back from the start applying `multiples[]`
// (1, 10, 100, …) right-to-left so each digit gets the right
// place value.  Stops at the first non-digit (no sign, no overflow
// check).
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        int d;
        digits = digits - 1;
        d = (unsigned char)(*p) - '0';
        total = total + d * multiples[digits];
        p = p + 1;
    }
    return total;
}

// FUNCTION: C2 0x263AF
// WIN: 0x0044cd64
// Lines 1724–1746
//
// Copy `n` bytes from `src` into the `idx`-th text-buffer slot.
// The slot's payload offset lives in two big-endian bytes at
// text_buffer[idx*4 + 0x1e..0x1f]; the actual data starts at
// text_buffer[0x1c + offset].  Before copying we scan past any
// non-control characters the slot already holds (so we land on the
// first writable byte), then `memcpy(dst, src, n)`.
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    char i;
    unsigned char c;

    c = text_buffer[idx * 4 + 0x1e];
    off  = c;
    off  = off << 8;
    c = text_buffer[idx * 4 + 0x1f];
    off  = off + c;
    dst  = &text_buffer[0x1c + off];
    while (n > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            n--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}

// FUNCTION: C2 0x2641A
// WIN: 0x0044ce30
// Lines 1748–1767
//
// Mirror of load_to_text_buffer: copies `copy_len` bytes *out* of
// the idx-th slot into `dst`.  Same slot-offset lookup and same
// skip-past-existing-words preamble.
void load_from_text_buffer(char *dst, int idx, int n, int copy_len)
{
    int off;
    char *src;
    char i;
    unsigned char c;

    c = text_buffer[idx * 4 + 0x1e];
    off  = c;
    off  = off << 8;
    c = text_buffer[idx * 4 + 0x1f];
    off  = off + c;
    src  = &text_buffer[0x1c + off];
    while (n > 0) {
        if (*src == 0 && (signed char)*(src - 1) >= ' ')
            n--;
        src++;
    }
    while ((signed char)*src < ' ')
        src++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}

// FUNCTION: C2 0x26485
// WIN: 0x0044cefc
// Lines 1769–1781
//
// Returns the 24-bit little-endian value at text_buffer[idx*4 + 8..10]:
// (high<<16) + (mid<<8) + low.
int get_buffer_ofset(int idx)
{
    int off = idx * 4;
    int r;
    int t;

    t  = (unsigned char)text_buffer[off + 0xa];
    t <<= 16;
    r  = t;
    t  = (unsigned char)text_buffer[off + 9];
    t <<= 8;
    r += t;
    t  = (unsigned char)text_buffer[off + 8];
    r += t;
    return r;
}

// FUNCTION: C2 0x264BD
// WIN: 0x0044cf59
// Lines 1783–1792
//
// Walk the text buffer from the entry's offset, skipping `word_count`
// tokens (anything preceded by a NUL terminator), then strip leading
// control characters.  Returns the resulting `text_pointer`.
void get_text_pointer(int idx, int word_count)
{
    char *p;

    text_pointer = text_buffer;
    text_pointer += get_buffer_ofset(idx);

    while (word_count > 0) {
        p = text_pointer;
        if (*p == 0 && (*(p - 1) >= ' ' || *(p - 1) == 0)) word_count--;
        text_pointer++;
    }

    while (*text_pointer < ' ')
        text_pointer++;

    /* return removed */}

// FUNCTION: C2 0x26518
// WIN: 0x0044cfeb
// Lines 1801–1848
//
// One-iteration handler for the in-place format_buffer text editor
// (used by the "enter a name" prompts).  Reads one keystroke from
// the keyboard polling globals (key_ready / key_ascii / key_code)
// and updates `this_letter` (cursor position) and the buffer
// contents.  Returns 1 on Enter, 0 on Escape, or 0 to keep editing.
int edit_format_buffer(void)
{
    int len;
    int i;

    if (this_letter > fb_current_char_length)
        this_letter = fb_current_char_length;
    if (this_letter < 0)
        this_letter = 0;

    if (key_ready != 1) return 0;

    if (key_ascii == 0x1b) return 0;
    if (key_ascii == 0x0d) return 1;

    test_for_delimiter();
    if (key_ascii == 0) {
        /* Function keys / arrows / Home / End / Insert. */
        if (key_code == 0x53) del_fb();           /* Delete */
        if (key_code == 0x52) insert_cursor ^= 1; /* Insert */
        if (key_code == 0x47) this_letter = 0;    /* Home   */

        if (key_code == 0x4b && this_letter > 0)  /* Left   */
            this_letter--;

        if (key_code == 0x48) {                    /* Up     */
            for (i = 0; i < 0xa; i++)
                if (this_letter > 0) this_letter--;
        }
        if (at_limit != 0) return 0;

        if (key_code == 0x4d                       /* Right  */
            && this_letter < fb_current_char_length)
            this_letter++;

        if (fb_limit == 1) return 0;

        if (key_code == 0x50) {                    /* Down   */
            for (i = 0; i < 0xa; i++)
                if (this_letter < fb_current_char_length) this_letter++;
        }
        if (key_code == 0x4f)                      /* End    */
            this_letter = fb_current_char_length;
        return 0;
    }

    /* Printable / control: backspace and the per-codepage whitelist. */
    if (key_ascii == 8) {                          /* BS     */
        if (this_letter > 0) {
            at_limit = 0;
            this_letter--;
            del_fb();
            return 0;
        }
    }
    if (at_limit == 2) return 0;

    if (key_ascii == ' ' || key_ascii == '\\'
        || key_ascii == ',' || key_ascii == '?'
        || key_ascii == '\'' || key_ascii == '!'
        || key_ascii == '"'
        || (key_ascii >= '0' && key_ascii <= '9')
        || (key_ascii >= 'a' && key_ascii <= 'z')
        || (key_ascii >= 'A' && key_ascii <= 'Z')
        || (key_ascii >= 0x80 && key_ascii <= 0x9a)
        || (key_ascii >= 0xa0 && key_ascii <= 0xa7)
        || key_ascii == 0xe1) {
        to_fb();
    }

    if (this_letter >= fb_max_char_length)
        this_letter = fb_max_char_length;
    if (this_letter < 0)
        this_letter = 0;
    return 0;
}

// FUNCTION: C2 0x267B3
// WIN: 0x0044d41a
// Lines 1850–1884
//
// Insert / overwrite the current `key_ascii` byte at `this_letter`
// inside `format_buffer`, advance the cursor, and shuffle
// subsequent characters right when in insert mode.  Used by the
// on-screen text editor.  Three early-exit gates: cursor past the
// end (the limit compare is jg in fb_limit==2 loose mode, jge
// otherwise), fb_max_width_reached, fb_current_char_length already
// at fb_max_char_length.
void to_fb(void)
{
    int p;
    int len;

    if (fb_limit == 2) { if (this_letter > fb_current_char_length) return;
    } else {
        if (this_letter >= fb_current_char_length) return;
    }

    if (insert_cursor || at_limit == 1) {
        /* Insert path: shove tail right by one, drop new char,
         * advance cursor.  No-op if we're width-capped or at
         * the per-buffer character cap. */
        if (fb_max_width_reached) return;
        if (fb_current_char_length >= fb_max_char_length) return;
        push_string_right(&format_buffer[this_letter],
                          &format_buffer[fb_current_char_length + 1]);
        p = this_letter; format_buffer[p] = key_ascii; this_letter = p + 1;
    } else {
        /* Overwrite path: stamp the byte at the cursor first,
         * then decide whether to advance.  At the end-of-text
         * boundary we either hold or step depending on whether
         * the buffer has room AND fb_limit allows the extra
         * step. */
        int next;
        p = this_letter; format_buffer[p] = key_ascii;
        if (fb_max_width_reached) return; next = p + 1;
        if (fb_current_char_length >= fb_max_char_length) {
            if (p >= fb_current_char_length) return; this_letter = next; return;
        }
        if (fb_limit != 2) {
            len = fb_current_char_length - 1; if (p >= len) return;
        }
        this_letter = next;
    }
}

// FUNCTION: C2 0x2689D
// WIN: 0x0044d568
// Lines 1886–1890
//
// Delete a single character from the format buffer, shifting the
// tail left by one. Skipped when at_limit is set.
void del_fb(void)
{
    if (at_limit == 0) {
        pull_string_left(&format_buffer[this_letter],
                         &format_buffer[fb_current_char_length]);
    }
}

// FUNCTION: C2 0x268CE
// WIN: 0x0044d5a3
// Lines 1892–1896
//
// Copy 2000 bytes (the full format buffer) from src to dst.
void copy_fb(char *src, char *dst)
{
    int i;
    for (i = 0; i < 2000; i++)
        dst[i] = src[i];
}

// FUNCTION: C2 0x268F1
// WIN: 0x0044d5e4
// Lines 1898–1906
//
// Update at_limit based on the character at format_buffer[this_letter]
// and the current fb_limit setting.
void test_for_delimiter(void)
{
    at_limit = 0;
    if (format_buffer[this_letter] == 0)
        at_limit = 1;
    if (fb_limit == 1) {
        if (format_buffer[this_letter] == '.') {
            if (this_letter < 8)
                at_limit = 1;
            else
                at_limit = 2;
        }
    }
}

// FUNCTION: C2 0x26955
// WIN: 0x0044d66b
// Lines 1908–1917
//
// Walk the format buffer and pull-string-left every space character
// up to fb_current_char_length, returning early on the first NUL.
void strip_fb_spaces(void)
{
    int i;
    for (i = 0; i <= fb_current_char_length; i++) {
        if (format_buffer[i] == 0)
            return;
        if (format_buffer[i] == ' ')
            pull_string_left(&format_buffer[i],
                             &format_buffer[fb_current_char_length]);
    }
}

// FUNCTION: C2 0x2699E
// WIN: 0x0044d6e4
// Lines 1919–1923
//
// Recompute fb_current_char_length from the format_buffer's NUL.
void get_fb_length(void)
{
    int i = 0;
    fb_current_char_length = 0;
    while (format_buffer[i++] != 0)
        fb_current_char_length++;
}

// FUNCTION: C2 0x269C8
// WIN: 0x0044d72a
// Lines 1926–1932
//
// Sums get_letter_width() across every char in the null-terminated
// `format_buffer`.
int get_fb_width(unsigned char *font)
{
    int i;
    int total;

    i = 0;
    total = 0;
    while (1) {
        unsigned char c;
        c = format_buffer[i];
        i = i + 1;
        if (c == 0) break;
        total = total + get_letter_width(c, font);
    }
    return total;
}

// FUNCTION: C2 0x269FB
// WIN: 0x0044d782
// Lines 1936–1963
//
// Word-wrap measurement: walk the format_buffer and return the
// number of display lines the text would occupy given a maximum of
// fb_line_length pixels per line, 0x32 (=50) characters per line,
// and 0x64 (=100) total lines.  Spaces count as 4 px, '#' bumps the
// width by 0x64 (a wider escape used for in-game format codes).  We
// stop at the first NUL byte.
int get_fb_lines(void)
{
    int line;
    int px_on_line;
    int chars_on_line;
    int idx;
    int last_space;
    int active;
    unsigned char c;
    char *fb;

    fb = format_buffer;
    active = 1;
    line = 0;
    last_space = 0;
    while (line < 0x64 && active != 0) {
        idx = last_space;
        last_space = 0;
        px_on_line = 0;
        chars_on_line = 0;
        while (chars_on_line < 0x32 && active != 0
               && px_on_line < fb_line_length) {
            c = (unsigned char)fb[idx];
            if (c == 0) {
                active = 0;
                last_space = idx;
            } else if (c == ' ') {
                last_space = idx;
                px_on_line += 4;
            } else if (c == '#') {
                px_on_line += 0x64;
            }
            chars_on_line++;
            idx++;
        }
        if (last_space == 0)
            last_space = idx - 1;
        line++;
        last_space++;
    }
    return line;
}

// FUNCTION: C2 0x26A8D
// WIN: 0x0044d88b
// Lines 1965–1977
//
// Initialise format_buffer for editing.  Wipes all 0x7D0 bytes
// (= 2000) of the buffer to 0, then copies the source string into
// it (NUL-terminator excluded).  Stores the string length in
// fb_current_char_length and pins the editor's per-field limits:
//
//   max_char    -> fb_max_char_length     (per-token max width)
//   line_len    -> fb_line_length         (max line width in pixels)
//   limit       -> fb_limit               (overall char cap)
//
// Resets fb_max_width_reached and cursor_y to 0 so the next render
// starts at the top of the field.
void in_format_buffer(char *src, int max_char, int line_len, int limit)
{
    int i;
    char c;

    for (i = 0x7cf; i >= 0; i--) format_buffer[i] = 0;
    while (*src) format_buffer[++i] = *src++;
    fb_current_char_length = i + 1;
    fb_max_char_length = max_char;
    fb_line_length = line_len;
    fb_limit = limit;
    fb_max_width_reached = 0;
    cursor_y = 0;
}

// FUNCTION: C2 0x26AF5
// WIN: 0x0044d91d
// Lines 1979–1984
//
// Copy format_buffer (a NUL-terminated string) into `out`, null
// terminator included.
void out_format_buffer(char *out)
{
    int i = 0;
    while (format_buffer[i] != 0) {
        *out = format_buffer[i];
        i++;
        out++;
    }
    *out = 0;
}

// FUNCTION: C2 0x26B1A
// WIN: 0x0044d964
// Lines 1986–1998
//
// Read the entry's offset word from the table at file offset
// idx*4 + 0x1E (big-endian on disk), then load 0x7D0 bytes from
// (offset + 0x1C) into format_buffer. Initializes fb_max_char_length
// from the loaded string's length, sets fb_line_length / line count /
// fb_limit, and tail-jumps into a sibling's epilogue.
void load_format_buffer_from_disk(char *fname, int idx)
{
    int word_value;
    char *p;

    readfile(fname, (char *)&word_value, 2, idx * 4 + 0x1e);

    /* Byte-swap the 16-bit word (BE on disk → LE in memory). */
    word_value = ((word_value & 0xff) << 8)
               + ((word_value & 0xff00) >> 8);

    readfile(fname, format_buffer, 0x7d0, word_value + 0x1c);

    fb_max_char_length = 0;
    p = format_buffer;
    while (*p != 0) {
        p++;
        fb_max_char_length++;
    }

    fb_line_length  = 0xe0;
    fb_no_of_lines  = 4;
    fb_limit        = 0;
}

// FUNCTION: C2 0x26BAB
// WIN: 0x0044da0c
// Lines 2001–2015
//
// Read the entry's offset word from the table at file offset
// idx*4 + 0x1E (big-endian on disk), pad the format_buffer past its
// first NUL with spaces, and write fb_max_char_length bytes back at
// (offset + 0x1C).
void save_format_buffer_to_disk(char *fname, int idx)
{
    int word_value;
    int i;
    int found_zero;

    readfile(fname, (char *)&word_value, 2, idx * 4 + 0x1e);

    /* Byte-swap the 16-bit word (BE on disk → LE in memory). */
    word_value = ((word_value & 0xff) << 8)
               + ((word_value & 0xff00) >> 8);

    /* Replace anything past the first NUL with spaces. */
    found_zero = 0;
    i = 0;
    while (i < fb_max_char_length) {
        if (format_buffer[i] == 0)
            found_zero = 1;
        if (found_zero)
            format_buffer[i] = ' ';
        i++;
    }

    write_to_file(fname, format_buffer,
                  fb_max_char_length, word_value + 0x1c);
}

// FUNCTION: C2 0x26C2E
// WIN: 0x0044dabc
// Lines 2021–2072
//
// Render a printable string `str` at pixel (x, y) using the bitmap
// font (font1 / font2).  `color` is the palette index for solid
// pixels; 0 selects the shadow font_style with the default colour.
//
// Special bytes: '#' pulls the next inserted-text byte (when
// insert_place is set, else a space); '_' renders as a literal
// space; < 0x20 is skipped.  Each printable byte indexes
// letter_table[c - 0x20] for the glyph id; missing glyphs use a
// fixed 4-pixel width.  one_letter draws the glyph and returns the
// advance; sprite_x / x_is step by that.  When fb_count reaches
// this_letter the caret position is snapshotted into cursor_x.
// Padding suppression: when allow_padding == 0 and padding_off != 0,
// repeats of a ' ' or '_' undo the advance, collapsing padding runs.

void put_a_font_string(char *str, int x, int y, unsigned char *font, int color)
{
    char prev_char;
    char ch;
    int  width;

    font_style = 1;
    if (color != 0) {
        font_style = 0;
    }
    sprite_colour = color;
    sprite_x      = x;

    ch = *str;
    while (ch != 0) {
        prev_char = ch;

        if (ch == '#') {
            if (insert_place == 1) {
                ch = get_insert_letter();
            } else {
                ch = 0x20;
            }
        }

        if (ch == '_') {
            ch = 0x20;
        }

        if ((unsigned char)ch >= 0x20) {
            ch -= 0x20;

            if (fb_count == this_letter && got_cursx == 0) {
                cursor_x  = x_is;
                got_cursx = 1;
            }

            sprite_y = y;

            if (letter_table[(unsigned char)ch] > 0) {
                width = one_letter(font, ch);
            } else {
                width = 4;
            }

            sprite_x += width;
            x_is     += width;
        }

        if (insert_count != 0) {
            ch = get_insert_letter();
        } else {
            str++;
            ch = *str;
        }
        fb_count++;

        if (allow_padding == 0 && padding_off != 0) {
            if (prev_char == ch) {
                if (ch == 0x20 || ch == '_') {
                    x_is     -= width;
                    sprite_x -= width;
                }
            }
        }
    }

    x_is += 4;
    insert_place      = 0;
    insert_count      = 0;
    allow_padding     = 0;
    font_screen_limit = 0;
}

// FUNCTION: C2 0x26D83
// WIN: 0x0044dcb8
// Lines 2076–2109
//
// Render a single bitmap-font glyph for `letter` from the font
// table (font1 or font2) at the current sprite position with the
// supplied clipping box.  letter_table[letter] gives the glyph id
// (0 = no glyph, short-circuits); each glyph is 16 bytes at offset
// 8 + idx*16: width (+0..1 LE16), height (+2..3 LE16), start (+4..6
// LE24 into the pixel pool), vertical offset (+13).
//
// font1 also applies Latin-shape descender nudges: 'a'..'m', 's'..'w',
// and 0x80..0x84 each shift sprite_y up by one.  font2 has none.
//
// font_screen_limit chooses the clip box (set = pm_screen_x_start +
// 0x18..pm_screen_y_end; clear = full screen).  xclip / yclip then
// dispatch to write_i_left_font / write_i_right_font / write_i_font
// (skipping when yclipped == 5).  Returns sprite_width + 1, the
// advance the caller uses to step to the next glyph.
int one_letter(unsigned char *font, unsigned char letter)
{
    unsigned char *p;

    sprite_image_no = letter_table[letter];
    if (sprite_image_no == 0) {
        return 0;
    }

    sprite_image_no = sprite_image_no - 1;
    data_ptr = (sprite_image_no << 4) + 8;

    sprite_y += (unsigned char)font[data_ptr + 13];

    if (font == font1) {
        if (letter >= 'a' && letter <= 'm') {
            sprite_y -= 1;
        }
        if (letter >= 's' && letter <= 'w') {
            sprite_y -= 1;
        }
        if (letter >= 0x80 && letter <= 0x84) {
            sprite_y -= 1;
        }
    }

    p = font + data_ptr;
    sprite_width  = p[0] + (p[1] << 8);
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);

    if (font_screen_limit != 0) {
        xclip(pm_screen_x_start, 0x1de);
        yclip(0x18, pm_screen_y_end);
    } else {
        xclip(0, screen_width);
        yclip(0, screen_height);
    }

    if (yclipped != 5) {
        if (xclipped == 1) {
            write_i_left_font(font);
        } else if (xclipped == 2) {
            write_i_right_font(font);
        } else {
            write_i_font(font);
        }
    }

    return sprite_width + 1;
}

// FUNCTION: C2 0x26EFE
// WIN: 0x0044dedb
// Lines 2111–2118
//
// Pull the next letter from the typed-insert buffer; rewinds and
// emits a space when the buffer is exhausted. Returns `char` (al only)
// to match PS's `mov al, 0x20` exit path.
char get_insert_letter(void)
{
    char c = insert_text[insert_count];
    if (c == 0) {
        insert_count = 0;
        return ' ';
    }
    insert_count++;
    return c;
}

// FUNCTION: C2 0x26F2E
// WIN: 0x0044df23
// Lines 2120–2136
//
// Same scan-and-skip as get_text_pointer / font_list, then horizontally
// centre the resulting substring inside `total_width` and render via
// put_a_font_string. `ret 0xc` pops the three trailing stack args.
void font_centre(int idx, int word_count, int x_left, int arg4,
                 int total_width, unsigned char *font, int p7)
{
    char *p;
    int width;
    int offset;

    text_pointer = text_buffer;
    text_pointer += get_buffer_ofset(idx);

    while (word_count > 0) {
        p = text_pointer;
        if (*p == 0 && (*(p - 1) >= ' ' || *(p - 1) == 0)) word_count--;
        text_pointer++;
    }

    while (*text_pointer < ' ')
        text_pointer++;

    width  = get_string_width(text_pointer, font);
    offset = (total_width - width) / 2;
    if (offset < 0)
        offset = 0;

    put_a_font_string(text_pointer, x_left + offset, arg4, font, p7);
    font_screen_limit = 0;
}

// FUNCTION: C2 0x26FCF
// WIN: 0x0044e018
// Lines 2138–2150
//
// Same scan-and-skip as get_text_pointer, then render the resulting
// substring via put_a_font_string with two stack-passed parameters.
// `ret 8` pops the two trailing args.
void font_list(int idx, int word_count, int x, int y, unsigned char *font, int color)
{
    char *p;

    text_pointer = text_buffer;
    text_pointer += get_buffer_ofset(idx);

    while (word_count > 0) {
        p = text_pointer;
        if (*p == 0 && (*(p - 1) >= ' ' || *(p - 1) == 0)) word_count--;
        text_pointer++;
    }

    while (*text_pointer < ' ')
        text_pointer++;

    put_a_font_string(text_pointer, x, y, font, color);
    font_screen_limit = 0;
}

// FUNCTION: C2 0x2704E
// WIN: 0x0044e0d2
// Lines 2152–2177
//
// Render an integer right-aligned into a static 16-byte scratch
// buffer (filled with `pad_char` for the digit field, then `suffix`
// at positions 10..15), strip the leading padding, and hand the
// result to put_a_font_string at (x, y) in the supplied font.
//
// Digits walk buf[9..0] right-to-left: while `value > 0`, write the
// next decimal digit; when value reaches 0, the first iteration
// emits a single '0' (so zero renders as "0" not all-pad), and
// subsequent iterations overwrite the cell with a literal space so
// the leading pad strips off.  The static scratch buffer is
// declared as a writable initialised array so the linker resolves
// the fixup against our local copy.

void font_no(int value, char pad_char, char *suffix, int x,
             int y, unsigned char *font, int color)
{
    char *buf = "                ";  /* 16 spaces + NUL, PS pools in CONST */
    char *bufp;
    int i;
    char had_zero;

    had_zero = 0;
    bufp = buf;
    if (pad_char != 0) {
        for (i = 9; i >= 0; i--)
            bufp[i] = pad_char;
    }

    i = 10;
    while (*suffix != 0) {
        bufp[i] = *suffix++;
        i++;
        if (i >= 16) break;
    }
    bufp[i] = 0;

    for (i = 9; i >= 0; i--) {
        if (value <= 0 && i != 9 && !had_zero) {
            had_zero = 1; goto next;
        }
        if (value <= 0 && i != 9 && had_zero) {
            bufp[i] = ' ';
        } else {
            bufp[i] = (char)((value % 10) + '0');
        }
    next:
        value = value / 10;
    }

    strip_leading_space((signed char *)bufp);
    put_a_font_string(bufp, x, y, font, color);
    font_screen_limit = 0;
}

// FUNCTION: C2 0x2712A
// WIN: 0x0044e235
// Lines 2179–2225
//
// Word-wrap a text-buffer entry into multiple rendered lines.
// Pulls the entry's offset via get_buffer_ofset, optionally skips
// `word_skip` whole words, strips leading control characters, and
// builds format_buffer one wrapped line at a time before dispatching
// each to put_a_font_string at (x, y + line_index*0x10).
//
// Per line: drain whole words via get_next_word_length while the
// running pixel width stays under max_width; the first word that
// would overflow stays un-copied for the next line.  Within a word,
// bytes copy through char_count, suppressing the leading separator.
//
// When line_index reaches `line_limit` the layout switches to the
// overflow column (x = x_overflow, max_width = max_width_overflow),
// matching the message browser's two-column wrap.
//
void font_format_split(int idx, int word_skip, int x, int y_start,
                       int max_width, int line_limit,
                       int x_overflow, int max_width_overflow,
                       unsigned char *font, int color)
{
    int   line_index;
    int   line_y;
    int   more_lines;
    int   x_count;
    int   buf_idx;
    int   skip_lead;
    int   char_iter;
    int   i;
    char *p;
    char  ch;

    font_screen_limit = 0;
    text_pointer      = text_buffer;
    text_pointer     += get_buffer_ofset(idx);

    /* Skip word_skip whole words from the entry's offset. */
    while (word_skip > 0) {
        p = text_pointer;
        if (*p == 0) {
            if ((unsigned char)*(p - 1) >= ' ' || *(p - 1) == 0) {
                word_skip--;
            }
        }
        text_pointer++;
    }

    /* Strip leading control bytes (any byte < ' '). */
    while ((unsigned char)*text_pointer < ' ') {
        text_pointer++;
    }

    more_lines = 1;
    line_index = 0;
    line_y     = y_start;

    while (more_lines) {
        for (i = 0; i < 0x7d0; i++)
            format_buffer[i] = 0;

        x_count   = 0;
        buf_idx   = 0;
        skip_lead = 1;

        while (more_lines && x_count < max_width) {
            x_count += get_next_word_length(text_pointer,
                                            font);
            if (x_count >= max_width) continue;

            for (char_iter = 0; char_iter < char_count; char_iter++) {
                p  = text_pointer;
                text_pointer = p + 1;
                ch = *p;
                if (skip_lead == 0 || ch != ' ') {
                    format_buffer[buf_idx++] = ch;
                    skip_lead = 0;
                }
            }

            if (*text_pointer == 0) {
                more_lines = 0;
            }
        }

        insert_place  = 1;
        x_is          = 0;       allow_padding = 1;
        put_a_font_string(format_buffer, x, line_y, font, color);

        line_index++;
        line_y += 0x10;

        if (line_index >= line_limit) {
            x         = x_overflow;
            max_width = max_width_overflow;
        }
    }
}

// FUNCTION: C2 0x2729B
// WIN: 0x0044e448
// Lines 2227–2248
//
// Pixel width of the next word in `src`, used by the format-buffer
// editor to decide if appending a token would overflow the current
// line.  Walks at most 2000 chars (runaway guard) and:
//
//   * NUL ............ end of buffer (stop, char_count counts what we ate)
//   * ' ' ............ word separator: leading spaces add 4 px each;
//                      a space *after* a word terminates the scan.
//   * '$' ............ format escape: same role as space (terminates
//                      after the first word; before, just consumed).
//   * < ' ' .......... control byte (e.g. \n, \t): skipped silently.
//   * other .......... printable: pixel width via get_letter_width;
//                      flips `started` so the next ' '/'$' breaks.
//
// char_count is the per-call running tally of bytes consumed,
// mirrored to a global because callers re-use it to advance the
// in-buffer text pointer after each scan.
int get_next_word_length(char *src, unsigned char *font)
{
    int width;
    int started;
    int i;
    char c;

    char_count = 0;
    width   = 0;
    started = 0;
    i = 0;
    while (1) {
        i++;
        if (i >= 0x7d0) break;
        c = *src;
        src++;
        if (c == 0) break;
        if ((unsigned char)c == ' ') {
            if (started) break;
            width += 4;
        } else if ((unsigned char)c == '$') {
            if (started == 0)
                goto next;
            break;
        } else if ((unsigned char)c >= ' ') {
            width += get_letter_width(c, font);
            started = 1;
        }
    next:
        char_count++;
    }
    return width;
}

// FUNCTION: C2 0x27309
// WIN: 0x0044e53d
// Lines 2252–2259
//
// If the user just pre-clicked inside the text rect [x,x+w)×[y,y+h),
// remember the click's y-coordinate.
void click_on_text(int x, int y, int w, int h)
{
    if (cursor_y != 0)                  return;
    if (mouse_left_preclick == 0)       return;
    if (x > mouse_x)                    return;
    if (x + w <= mouse_x)               return;
    if (y > mouse_y)                    return;
    if (y + h <= mouse_y)               return;
    cursor_y = y;
}

// FUNCTION: C2 0x2734D
// Lines 2261–2271
//
// Like clicked_delay() but runs the inner poll for a fixed 8000
// iterations and returns void: a settle (warmup) loop of 1000
// get_mouse() calls followed by `delay` outer ticks of 8000
// inner polls. Returns as soon as either click latch fires.
#ifdef __WATCOMC__
void click_delay(int delay)
{
    int i;
    int j;
    for (j = 0; j < 1000; j++)
        get_mouse();
    for (i = 0; i < delay; i++) {
        for (j = 0; j < 8000; j++) {
            get_mouse();
            if (mouse_left_click != 0 || mouse_right_click != 0) {
                clear_mouse();
                return;
            }
        }
    }
}

// FUNCTION: C2 0x273A4
// Lines 2273–2284
//
// Same shape as click_delay but returns 1 on click / 0 on timeout.
int clicked_delay(int delay)
{
    int i;
    int j;
    for (j = 0; j < 1000; j++)
        get_mouse();
    for (i = 0; i < delay; i++) {
        for (j = 0; j < 8000; j++) {
            get_mouse();
            if (mouse_left_click != 0 || mouse_right_click != 0) {
                clear_mouse();
                return 1;
            }
        }
    }
    return 0;
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x27402
// WIN: 0x0044e712
// Lines 2286–2291
//
// Crude busy-wait: `n` * 25 vertical-blank cycles.
void do_delay(int n)
{
    int i;
    int j;
    for (i = 0; i < n; i++)
        for (j = 0; j < 25; j++)
            wvbl2();
}

// FUNCTION: C2 0x2742B
// WIN: 0x0044e763
// Lines 2293–2309
//
// Returns the number of milliseconds since the previous call,
// or 999 if the wallclock went backwards (clock skew / wrap).
// Latches `tb.time` into the global `time_is` so the rest of
// the engine can read it without re-calling ftime().
int running_delay1(void)
{
    /* PS: unnamed function-local static (data 0x3ccd1, no -d1 symbol) --
       last tick (ms since epoch) seen by this delay. */
    static int running_delay_last;
    struct timeb tb;
    int t;
    int dt;

    ftime(&tb);
    time_is = tb.time;
    t = tb.time * 1000;
    t = t + tb.millitm;
    if (t >= running_delay_last)
        dt = t - running_delay_last;
    else
        dt = 999;
    running_delay_last = t;
    return dt;
}

// FUNCTION: C2 0x27483
// Lines 2311–2323
//
// Sub-second elapsed-time gate, used by the palette colour cycler
// to throttle hue rotations.  Each call:
//
//   1. ftime() into a local timeb,
//   2. compute (tb.millitm - last_cycle_ms1) modulo 1000 (where
//      last_cycle_ms1 is last_cycle_ms1, persisted across calls),
//   3. if that signed-16-bit delta is >= the requested delay_ms,
//      latch tb.millitm into last_cycle_ms1 and return 1;
//   4. otherwise return 0 (no time has passed yet, don't tick).
//
// The wraparound case is the < branch -- when tb.millitm is
// numerically smaller than last_cycle_ms1 the second has rolled
// over, so the elapsed time is (tb.millitm + 1000) - last_cycle_ms1.
// The == branch shortcuts to delta = 0 (cwde of zero is zero).
//
char colour_cycle_delay1(int delay_ms)
{
    /* PS: unnamed function-local static (data 0x3ccd5) -- last sub-second
       tick seen by this delay. */
    static short last_cycle_ms1;
    struct timeb tb;
    short ms;
    short delta;

    ftime(&tb);
    ms = tb.millitm;

    if (ms > last_cycle_ms1) {
        delta = ms - last_cycle_ms1;
    } else if (ms < last_cycle_ms1) {
        delta = (ms + 1000) - last_cycle_ms1;
    } else {
        delta = 0;
    }

    if ((int)delta >= delay_ms) {
        last_cycle_ms1 = ms;
        return 1;
    }
    return 0;
}

// FUNCTION: C2 0x274D8
// Lines 2326–2337
//
// Second sub-second elapsed-time gate -- bit-identical algorithm
// to colour_cycle_delay1, but persists its high-water mark into
// last_cycle_ms2 (a separate 16-bit slot at 0x3ccd7) so the two
// gates can run independently for two different palette layers.
//
// Behaviour: returns 1 once at least 'delay_ms' have elapsed
// since the last successful tick (latching tb.millitm into
// last_cycle_ms2 in the process), 0 otherwise.  See colour_cycle_
// delay1 for the wrap-around semantics.
char colour_cycle_delay2(int delay_ms)
{
    /* PS: unnamed function-local static (data 0x3ccd7) -- twin of
       colour_cycle_delay1's, so the two cyclers don't share state. */
    static short last_cycle_ms2;
    struct timeb tb;
    short ms;
    short delta;

    ftime(&tb);
    ms = tb.millitm;

    if (ms > last_cycle_ms2) {
        delta = ms - last_cycle_ms2;
    } else if (ms < last_cycle_ms2) {
        delta = (ms + 1000) - last_cycle_ms2;
    } else {
        delta = 0;
    }

    if ((int)delta >= delay_ms) {
        last_cycle_ms2 = ms;
        return 1;
    }
    return 0;
}

// FUNCTION: C2 0x27522
// WIN: 0x0044e926
// Lines 2341–2365
//
// Stopwatch in milliseconds.  Each call is one of three states:
//   mode 0 — start the clock: snapshot `ftime` into private static
//            seconds/milliseconds slots.  Returns 0.
//   mode 1 — read the elapsed time: compute (now - snapshot) in ms,
//            wrapping millitm via +1000 when it has rolled over.
//            Returns the delta in milliseconds.
//   else   — returns 0.
int timer(int mode)
{
    /* PS reserves the next dword at 0x3cce1, but has no fixup referencing it. */
    static int unused_timer_state;
    static int start_ms;
    static int start_sec;
    struct timeb tb;
    int now_ms, delta;

    ftime(&tb);
    if (mode == 0)
    {
        start_ms = (int)(unsigned short)tb.millitm;
        start_sec = tb.time;
        return 0;
    }
    if (mode == 1)
    {
        now_ms = (int)(unsigned short)tb.millitm;
        delta = (tb.time - start_sec) * 1000;
        if (now_ms < start_ms) {
            now_ms += 0x3e8; return delta + (now_ms - start_ms);
        }
        return delta + (now_ms - start_ms);
    }
    return 0;
}

// FUNCTION: C2 0x2759C
// Lines 2370–2370
//
// Short beep at 880 Hz (0x370). Tail-merges with low_beep below.
#ifdef __WATCOMC__
void high_beep(void)
{
    sound(0x370);
    delay(50);
    nosound();
}

// FUNCTION: C2 0x275BF
// Lines 2371–2371
//
// Short beep at 220 Hz (0xDC).
void low_beep(void)
{
    sound(0xdc);
    delay(50);
    nosound();
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x275D0
// WIN: 0x0044ea28
// Lines 2372–2372
//
// Emit `n` high beeps with a 1-tick delay between each.
void no_high_beeps(int n)
{
    while (n != 0) {
        high_beep();
        n--;
        do_delay(1);
    }
}

// FUNCTION: C2 0x275F7
// WIN: 0x0044ea54
// Lines 2373–2373
//
// Emit `n` low beeps with a 1-tick delay between each.
void no_low_beeps(int n)
{
    while (n != 0) {
        low_beep();
        n--;
        do_delay(1);
    }
}

// FUNCTION: C2 0x2761E
// WIN: 0x0044ea80
// Lines 2374–2374
//
// Cycles through every beep tone for an audio test pass. The trailing
// vhigh_beep call falls through into vhigh_beep below (no `ret`).
void test_beeps(void)
{
    vhigh_beep();
    high_beep();
    low_beep();
    high_beep();
    vhigh_beep();
}

// FUNCTION: C2 0x2763C
//
// Short beep at 1720 Hz (0x6b8) for 150 ms.
#ifdef __WATCOMC__
void vhigh_beep(void)
{
    sound(0x6b8);
    delay(150);
    nosound();
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x2765A
// WIN: 0x0044eaa4
// Lines 2378–2390
//
// Sets up Bresenham state for the line from (x1, y1) to (x2, y2).
// dx / dy hold the absolute extents along each axis; the longer
// of the two becomes the major axis (so the line loop in
// draw_a_line steps along it).  (ix, iy) is always the start
// closer to the major-axis origin and (ex, ey) the far end --
// either (x1, y1) or (x2, y2) depending on which has the smaller
// major-axis coordinate.  gx / gy default to +1 and flip to -1
// when the line moves backward along that axis.
void get_longest_side(int x1, int y1, int x2, int y2)
{
    gy = 1;
    gx = 1;

    if (x1 > x2) dx = x1 - x2;
    else         dx = x2 - x1;

    if (y1 > y2) dy = y1 - y2;
    else         dy = y2 - y1;

    if (dy > dx) {
        if (y1 > y2) {
            iy = y2; ey = y1;
            ix = x2; ex = x1;
        } else {
            iy = y1; ey = y2;
            ix = x1; ex = x2;
        }
    } else {
        if (x1 > x2) {
            iy = y2; ey = y1;
            ix = x2; ex = x1;
        } else {
            iy = y1; ey = y2;
            ix = x1; ex = x2;
        }
    }

    if (ex < ix) gx = -1;
    if (ey < iy) gy = -1;
}

// FUNCTION: C2 0x27714
// WIN: 0x0044ebff
// Lines 2392–2395
//
// Per-step Bresenham accumulator update.  draw_a_line passes
// mode = 0 in the x-major branch and mode = 1 in the y-major
// branch.  In each direction the increment is +2 * minor when D
// has not crossed yet (D < 0) and +2 * (minor - major) once the
// caller is about to step the minor axis (D >= 0):
//
//   mode 0 (x-major):  D += (D < 0) ? 2*dy : 2*(dy - dx)
//   mode 1 (y-major):  D += (D < 0) ? 2*dx : 2*(dx - dy)
//
// Tail-merges into the shared 5-pop epilogue at 0x25505.
void Bresenham_decision(int mode)
{
    if (mode == 0) {
        if (D < 0) D = D + 2 * dy;
        else       D = D + 2 * (dy - dx);
    } else {
        if (D < 0) D = D + 2 * dx;
        else       D = D + 2 * (dx - dy);
    }
}

// FUNCTION: C2 0x2779B
// WIN: 0x0044ec7d
// Lines 2398–2404
//
// Bounds-checked single-pixel point plot.  If (x, y) is inside the
// screen rectangle, dispatches to show_internal_point which writes
// the colour byte (in ebx) at internal_screen[y * screen_width + x].

void draw_a_point(int x, int y, int colour)
{
    if (x < 0 || x >= screen_width)  return;
    if (y < 0 || y >= screen_height) return;
    show_internal_point(x, y, colour);
}

// FUNCTION: C2 0x277D2
// WIN: 0x0044ece2
// Lines 2410–2416
//
// Bounds-checked two-pixel point plot.  If (x, y) is inside the
// screen rectangle, dispatches to show_internal_2point which
// writes the colour byte at (x, y) AND (x + 1, y).

void draw_a_2point(int x, int y, int colour)
{
    if (x < 0 || x >= screen_width)  return;
    if (y < 0 || y >= screen_height) return;
    show_internal_2point(x, y, colour);
}

// FUNCTION: C2 0x27809
// WIN: 0x0044ed47
// Lines 2419–2451
//
// Bresenham line draw from (x1, y1) to (x2, y2).  Three cases:
//
//   1. Vertical (x1 == x2)   -- step iy from start..ey, plot.
//   2. Horizontal (y1 == y2) -- step ix from start..ex, plot.
//   3. Diagonal              -- standard Bresenham, switching the
//      major axis on dy > dx and decrementing the running counts
//      via Bresenham_decision().
//
// get_longest_side initializes ix, iy, ex, ey, dx, dy, gx, gy
// (signed step direction) globals.  Tail-merges into the
// 5-pop+ret-4 epilogue at 0x27C15.
void draw_a_line(int x1, int y1, int x2, int y2, int colour)
{
    int lx;
    int ly;

    get_longest_side(x1, y1, x2, y2);
    ly = iy;
    lx = ix;

    if (x1 == x2) {
        while (ly <= ey) {
            draw_a_point(x1, ly, colour);
            ly++;
        }
        return;
    }

    if (y1 == y2) {
        while (lx <= ex) {
            draw_a_point(lx, y1, colour);
            lx++;
        }
        return;
    }

    if (dy > dx) {
        D = 2 * dx - dy;
        for ( ; ly <= ey; ly++) {
            draw_a_point(lx, ly, colour);
            Bresenham_decision(1);
            dy--;
            if (D >= 1) {
                dx--;
                lx += gx;
            }
        }
    } else {
        D = 2 * dy - dx;
        for ( ; lx <= ex; lx++) {
            draw_a_point(lx, ly, colour);
            Bresenham_decision(0);
            dx--;
            if (D >= 1) {
                dy--;
                ly += gy;
            }
        }
    }
}

// FUNCTION: C2 0x27923
// WIN: 0x0044ef01
// Lines 2453–2459
//
// Vertical / horizontal dotted line: plots one dot every two
// pixels along the major axis.  Diagonal lines are silently
// dropped.  Tail-jumps to draw_a_line's shared epilogue at 0x2791B.
void draw_a_dotted_line(int x1, int y1, int x2, int y2, int colour)
{
    int loc_x;
    int loc_y;

    get_longest_side(x1, y1, x2, y2);
    loc_y = iy;
    loc_x = ix;

    if (x1 == x2) {
        while (loc_y <= ey) {
            draw_a_point(x1, loc_y, colour);
            loc_y += 2;
        }
    } else if (y1 == y2) {
        while (loc_x <= ex) {
            draw_a_point(loc_x, y1, colour);
            loc_x += 2;
        }
    }
}

// FUNCTION: C2 0x27996
// WIN: 0x0044efab
// Lines 2462–2468
//
// Outline a rectangle with four draw_a_line calls -- top edge,
// bottom edge, left edge, right edge -- in that order.  The
// inclusive lower-right corner is (x + w - 1, y + h - 1).
void draw_a_box(int x, int y, int w, int h, int colour)
{
    draw_a_line(x,             y,             x + (w - 1), y,             colour);
    draw_a_line(x,             y + (h - 1),   x + (w - 1), y + (h - 1),   colour);
    draw_a_line(x,             y,             x,           y + (h - 1),   colour);
    draw_a_line(x + (w - 1),   y,             x + (w - 1), y + (h - 1),   colour);
}

// FUNCTION: C2 0x27A0A
// WIN: 0x0044f046
// Lines 2470–2475
//
// Outline a beveled rectangle ("dias" = dais / pedestal): light
// edges on top + right (colour 0x1f), dark edges on bottom + left
// (colour 0x12).  Inclusive lower-right corner is
// (x + w - 1, y + h - 1).
void draw_a_dias(int x, int y, int w, int h)
{
    draw_a_line(x,           y,           x + (w - 1), y,           0x1f);
    draw_a_line(x + (w - 1), y,           x + (w - 1), y + (h - 1), 0x1f);
    draw_a_line(x,           y + (h - 1), x + (w - 1), y + (h - 1), 0x12);
    draw_a_line(x,           y,           x,           y + (h - 1), 0x12);
}

// FUNCTION: C2 0x27A74
// WIN: 0x0044f0d9
// Lines 2478–2492
//
// Outline a tile-shaped diamond using draw_a_2point (which plots
// two mirror-image pixels per call).  Walks top-half rows widening,
// then bottom-half rows narrowing, with the centre column at
// `xcentre`.  Tail-merges into draw_a_2point's stack-pop.
void draw_a_diamond(int x, int y, int width, int height, int colour)
{
    int col;
    int row_down;
    int row_up;

    width += 2;
    col = 0;
    row_down = height / 2 - 1;
    row_up   = height / 2;
    for ( ; col < width / 2; col += 2, row_down--, row_up++) {
        draw_a_2point(x + col, y + row_down, colour);
        draw_a_2point(x + col, y + row_up, colour);
    }

    col      = width / 2;
    row_down = height - 2;
    row_up   = 1;
    for ( ; col < width - 2; col += 2, row_down--, row_up++) {
        draw_a_2point(x + col, y + row_down, colour);
        draw_a_2point(x + col, y + row_up, colour);
    }
}

// FUNCTION: C2 0x27B35
// WIN: 0x0044f1d8
// Lines 2494–2501
//
// XOR-plot the top half of a tile diamond (both quadrants).  Like
// draw_a_diamond but routes through xor_internal_2point and stops
// at the equator (height/2).
void xor_a_diamond_top(int x, int y, int width, int height, int colour)
{
    int col;
    int row_down;
    int row_up;

    width += 2;
    col = 0;
    row_down = height / 2 - 1;
    row_up   = height / 2;
    for ( ; col < width / 2; col += 2, row_down--, row_up++)
        xor_internal_2point(x + col, y + row_down, colour);

    col      = width / 2;
    row_down = height - 2;
    row_up   = 1;
    for ( ; col < width - 2; col += 2, row_down--, row_up++)
        xor_internal_2point(x + col, y + row_up, colour);
}

// FUNCTION: C2 0x27BC3
// WIN: 0x0044f2a3
// Lines 2504–2510
//
// Draws the left-hand-side top quadrant of a diamond outline by
// stepping through (height/2) rows, advancing x by 2 per iteration
// and dropping y by 1.  Each step calls xor_internal_2point which
// XOR-plots a mirrored point pair about a vertical axis.
void xor_a_diamond_lhs_top(int x, int y, int width, int height, int color)
{
    int x_offset;
    int y_offset;

    width += 2;
    x_offset = 0; y_offset = height / 2 - 1;

    for ( ; x_offset < width / 2; x_offset += 2, y_offset--) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
}

// FUNCTION: C2 0x27C1B
// WIN: 0x0044f315
// Lines 2512–2517
//
// Mirror sibling of xor_a_diamond_lhs_top: draws the top-right half
// of an XOR diamond outline.  Iterates the column from width/2 to
// width - 2 (exclusive) in 2-px steps and raises the row by 1 each
// iteration.  Same `width += 2` padding as the LHS sibling.
void xor_a_diamond_rhs_top(int x, int y, int width, int height, int color)
{
    int x_offset;
    int y_offset;

    width += 2;
    x_offset = width / 2; y_offset = 1;
    for ( ; x_offset < width - 2; x_offset += 2, y_offset++) {
        xor_internal_2point(x + x_offset, y + y_offset, color);
    }
    (void)height;
}

// FUNCTION: C2 0x27C66
// WIN: 0x0044f380
// Lines 2520–2526
//
// Filled (solid) rectangle by stacking horizontal draw_a_line calls
// from y to y + h - 1.  Returns early if w or h is non-positive.
void draw_a_rect(int x, int y, int w, int h, int colour)
{
    int cur_y;

    if (w <= 0) return;
    if (h <= 0) return;

    for (cur_y = y; cur_y < y + h; cur_y++) {
        draw_a_line(x, cur_y, x + (w - 1), cur_y, colour);
    }
}

// FUNCTION: C2 0x27CB3
// WIN: 0x0044f3e9
// Lines 2530–2545
//
// Sprite-blit dispatcher.  `buf` is a packed sprite-bank: an 8-byte
// header followed by 16-byte descriptors (width at +0, height at +2,
// pixel-data byte-offset at +4..+6 all LE).  Populates sprite_width,
// sprite_height, sprite_start, sprite_x, sprite_y, then runs xclip /
// yclip against the full screen and dispatches to write_i_sprite
// (no clip), write_i_left_sprite, or write_i_right_sprite; yclipped
// == 5 skips drawing entirely.

void write_image(unsigned char *buf, int id, int x, int y)
{
    data_ptr = id * 16 + 8;

    sprite_width  = buf[data_ptr]     + (buf[data_ptr + 1] << 8);
    sprite_height = buf[data_ptr + 2] + (buf[data_ptr + 3] << 8);
    sprite_start  = buf[data_ptr + 4] + (buf[data_ptr + 5] << 8)
                  + (buf[data_ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;

    xclip(0, screen_width);
    yclip(0, screen_height);

    if (yclipped == 5) return;

    if (xclipped == 1) {
        write_i_left_sprite(buf);
    } else if (xclipped == 2) {
        write_i_right_sprite(buf);
    } else {
        write_i_sprite(buf);
    }
}

// FUNCTION: C2 0x27D7F
// WIN: 0x0044f521
// Lines 2547–2562
//
// Plot one sprite from the sprite-bank `buf` at (x, y) with X/Y
// clipping against a rectangular window.  Reads the bank header
// (16-byte stride per sprite, starting at +8) to extract
// sprite_width / sprite_height / sprite_start, runs xclip+yclip to
// classify the clip case, then dispatches:
//
//   yclipped == 5   — reject (off-screen).
//   xclipped == 1   — write_i_left_sprite (clip left edge).
//   xclipped == 2   — write_i_right_sprite (clip right edge).
//   otherwise       — write_i_sprite.
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    unsigned char *p;
    data_ptr = id * 16 + 8;
    p = buf + data_ptr;
    sprite_width  = p[0] + (p[1] << 8);
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_y_lo);
    yclip(clip_x_hi, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}

// FUNCTION: C2 0x27E54
// WIN: 0x0044f659
// Lines 2564–2593
//
// Clip a sprite's horizontal extent against the [clip_left,
// clip_right] window.  Reads sprite_x / sprite_width, writes the
// global clip-state quintet (xclipped, x_start, x_end, x_length,
// x_ofset, x_wrap, plus an in-place adjustment of sprite_start
// and sprite_x on a left-clip).  Result codes in 'xclipped':
//
//   0  no clip (sprite fully inside window).
//   1  left-clipped: shift x_start, sprite_start, sprite_x to the
//      window's left edge and discard the leading clip_left-sprite_x
//      pixels of the source.
//   2  right-clipped: trim x_end to the window's right edge.
//   5  off-screen (degenerate width or sprite outside [left,right]).
//
// 'x_length' is the visible row width (= x_end - x_start, or 0 when
// xclipped == 5); 'x_ofset' is the per-row source-pointer post-step
// (sprite_width - x_length); 'x_wrap' is the per-row dest-pointer
// post-step (screen_width - x_length).
void xclip(int clip_left, int clip_right)
{
    xclipped = 0;
    x_start = 0;
    x_end = sprite_width;

    if (sprite_width <= 0) {
        xclipped = 5;
    } else if (clip_left > sprite_x) {
        if (sprite_x + sprite_width <= clip_left) {
            xclipped = 5;
        } else {
            xclipped = 1;
            x_start = clip_left - sprite_x;
            sprite_start += x_start;
            sprite_x = clip_left;
        }
    } else if (clip_right - sprite_width < sprite_x) {
        if (clip_right <= sprite_x) {
            xclipped = 5;
        } else {
            xclipped = 2;
            x_end = clip_right - sprite_x;
        }
    }

    if (xclipped == 5) {
        x_length = 0;
    } else {
        x_length = x_end - x_start;
    }
    x_ofset = sprite_width - x_length;
    x_wrap = screen_width - x_length;
}

// FUNCTION: C2 0x27F20
// WIN: 0x0044f7ad
// Lines 2595–2623
//
// Vertical sibling of xclip().  Clips a sprite's Y-extent against
// the [clip_top, clip_bottom] window, leaving the result in the
// global y-clip state (yclipped, y_start, y_end, y_length, plus an
// in-place adjustment of sprite_start and sprite_y on a top-clip).
// Result codes in 'yclipped':
//
//   0  no clip (sprite fully inside window).
//   3  top-clipped: drop the leading (clip_top - sprite_y) rows
//      from the source by advancing sprite_start by that many
//      sprite_width-byte rows; sprite_y moves to clip_top.
//   4  bottom-clipped: trim y_end to the window's bottom edge.
//   5  off-screen.
//
// Final guard: if xclipped is already 5 (sprite is off-screen
// horizontally), force yclipped = 5 too, so callers can early-exit
// on a single yclipped == 5 check after running both clips.
void yclip(int clip_top, int clip_bottom)
{
    yclipped = 0;
    y_start = 0;
    y_end = sprite_height;

    if (sprite_height <= 0) {
        yclipped = 5;
    } else if (clip_top > sprite_y) {
        if (sprite_y + sprite_height <= clip_top) {
            yclipped = 5;
        } else {
            yclipped = 3;
            y_start = clip_top - sprite_y;
            sprite_start += y_start * sprite_width;
            sprite_y = clip_top;
        }
    } else if (clip_bottom - sprite_height < sprite_y) {
        if (clip_bottom <= sprite_y) {
            yclipped = 5;
        } else {
            yclipped = 4;
            y_end = clip_bottom - sprite_y;
        }
    }

    if (yclipped == 5) {
        y_length = 0;
    } else {
        y_length = y_end - y_start;
    }

    if (xclipped == 5) {
        yclipped = 5;
    }
}

// FUNCTION: C2 0x27FEA
// WIN: 0x0044f8e9
// Lines 2627–2635
//
// Tick the seven free-running frame counters used to drive
// periodic UI animations.  Each counter increments on every
// call and wraps back to 0 when it hits its modulus:
//
//   cnt4   wraps at 4   (4-frame  cycle)
//   cnt8   wraps at 8   (8-frame  cycle)
//   cnt16  wraps at 16  (16-frame cycle)
//   cnt32  wraps at 32
//   cnt64  wraps at 64
//   cnt128 wraps at 128
//   cnt256 wraps at 256
//
// Various rendering / blink / pulse routines test these counters
// to gate their effects.
void do_32_count(void)
{
    ++cnt4;   if (cnt4   >= 4)   cnt4   = 0;
    ++cnt8;   if (cnt8   >= 8)   cnt8   = 0;
    ++cnt16;  if (cnt16  >= 16)  cnt16  = 0;
    ++cnt32;  if (cnt32  >= 32)  cnt32  = 0;
    ++cnt64;  if (cnt64  >= 64)  cnt64  = 0;
    ++cnt128; if (cnt128 >= 128) cnt128 = 0;
    ++cnt256; if (cnt256 >= 256) cnt256 = 0;
}

// FUNCTION: C2 0x280BC
// WIN: 0x0044f9c5
// Lines 2638–2649
//
// 31-bit linear-feedback shift register (taps 0 and 4) folding
// into bit 30 of randseed; returns the low 15 bits.
int big_random(void)
{
    int i;
    unsigned int bit;
    for (i = 0; i < 0x1f; i++) {
        bit = (randseed & 1) ^ ((randseed & 0x10) >> 4);
        randseed >>= 1;
        if (bit != 0)
            randseed |= 0x40000000;
    }
    return randseed & 0x7fff;
}

// FUNCTION: C2 0x28105
// WIN: 0x0044fa34
// Lines 2651–2658
//
// Refresh the per-frame random caches (rand32000, rand128, rand8)
// from a single big_random() draw.
void random(void)
{
    rand32000 = big_random();
    rand128   = rand32000 & 0x7f;
    rand8     = rand32000 & 7;
}

// FUNCTION: C2 0x2812F
// WIN: 0x0044fa63
// Lines 2660–2671
//
// Same LFSR as big_random but mixes scatseed and stores the low 7
// bits to scat128 — used for sprite scatter offsets.
void scatter(void)
{
    int i;
    unsigned int bit;
    for (i = 0; i < 0x1f; i++) {
        /* See big_random: XOR operand order picks which input goes
         * into the first allocated reg (ebx vs edx). */
        bit = (scatseed & 1) ^ ((scatseed & 0x10) >> 4);
        scatseed >>= 1;
        if (bit != 0)
            scatseed |= 0x40000000;
    }
    scat128 = scatseed & 0x7f;
}

// FUNCTION: C2 0x2817B
// WIN: 0x0044fad0
// Lines 2673–2701
//
// Uniformly-distributed bounded random in [0, max].  Pulls a sample
// from the cached rand32000 word, masks it down to the smallest
// 2^k - 1 mask >= max, and rejects/retries (calling random() to
// reseed rand32000) if the masked sample exceeds max.  This avoids
// the modulo-bias of the obvious 'rand % (max+1)'.  After at most
// 10 rejections it gives up and returns 0.
//
// Caller convention: max <= 0 returns 0 (degenerate / sentinel).
//
// The mask cascade covers max up through 0xffff (16-bit unsigned);
// callers that want more than 65535 distinct outputs must build
// their own.
int get_rand_max(int max)
{
    int i;
    int mask;
    int v;

    if (max <= 0) return 0;

    if      (max <=     1) mask =     1;
    else if (max <=     3) mask =     3;
    else if (max <=     7) mask =     7;
    else if (max <=   0xf) mask =   0xf;
    else if (max <=  0x1f) mask =  0x1f;
    else if (max <=  0x3f) mask =  0x3f;
    else if (max <=  0x7f) mask =  0x7f;
    else if (max <=  0xff) mask =  0xff;
    else if (max <= 0x1ff) mask = 0x1ff;
    else if (max <= 0x3ff) mask = 0x3ff;
    else if (max <= 0x7ff) mask = 0x7ff;
    else if (max <= 0xfff) mask = 0xfff;
    else if (max <= 0x1fff) mask = 0x1fff;
    else if (max <= 0x3fff) mask = 0x3fff;
    else if (max <= 0x7fff) mask = 0x7fff;
    else                   mask = 0xffff;

    i = 0;
    while (i++ < 10) {
        v = rand32000 & mask;
        if (v <= max) return v;
        random();
    }
    return 0;
}

// FUNCTION: C2 0x28298
// WIN: 0x0044fca2
// Lines 2705–2710
//
// Returns (a * b) / 100.  The divide is its own statement (rather
// than a `return a / 100;`) -- the MSVC /Od Windows build encodes
// the assignment+reload explicitly, byte-exactly matching this
// two-statement form.
int totalXpercent(int a, int b)
{
    a *= b;
    a = a / 100;
    return a;
}

// FUNCTION: C2 0x282BA
// WIN: 0x0044fccd
// Lines 2712–2715
//
// Returns (a * b) / 10000.
int totalXpercentX100(int a, int b)
{
    a *= b;
    a = a / 10000;
    return a;
}

// FUNCTION: C2 0x282D2
// WIN: 0x0044fcf8
// Lines 2719–2725
//
// Percentage helper: (value * 100) / total, with a guard for total==0.
int valueDIVtotal(int value, int total)
{
    value *= 100;
    if (total != 0)
        value = value / total;
    else
        value = 0;
    return value;
}

// FUNCTION: C2 0x28300
// WIN: 0x0044fd3a
// Lines 2729–2739
//
// Manhattan distance between (x1,y1) and (x2,y2).
int get_distance(int x1, int y1, int x2, int y2)
{
    int dx;
    int dy;
    if (x1 > x2)      dx = x1 - x2;
    else if (x1 < x2) dx = x2 - x1;
    else              dx = 0;
    if (y1 > y2)      dy = y1 - y2;
    else if (y1 < y2) dy = y2 - y1;
    else              dy = 0;
    return dx + dy;
}

// FUNCTION: C2 0x28333
// WIN: 0x0044fdc9
// Lines 2741–2752
//
// Chebyshev (king-move) distance: max(|dx|, |dy|).
int get_longest_distance(int x1, int y1, int x2, int y2)
{
    int dx;
    int dy;
    int r;
    if (x1 > x2)      dx = x1 - x2;
    else if (x1 < x2) dx = x2 - x1;
    else              dx = 0;
    if (y1 > y2)      dy = y1 - y2;
    else if (y1 < y2) dy = y2 - y1;
    else              dy = 0;
    if (dx < dy) r = dy;
    else         r = dx;
    return r;
}

// FUNCTION: C2 0x28368
// WIN: 0x0044fe69
// Lines 2754–2765
//
// min(|dx|, |dy|) — the shortest leg of the bounding rectangle.
int get_shortest_distance(int x1, int y1, int x2, int y2)
{
    int dx;
    int dy;
    int r;
    if (x1 > x2)      dx = x1 - x2;
    else if (x1 < x2) dx = x2 - x1;
    else              dx = 0;
    if (y1 > y2)      dy = y1 - y2;
    else if (y1 < y2) dy = y2 - y1;
    else              dy = 0;
    if (dx < dy) r = dx;
    else         r = dy;
    return r;
}

// FUNCTION: C2 0x2839E
// Lines 2769–2783
//
// Issue DPMI service 0x600 (lock linear region) for the byte range
// [addr, addr+size). Returns nonzero on success (carry clear).
#ifdef __WATCOMC__
int lock_region(unsigned int addr, unsigned int size)
{
    union REGS r;
    unsigned int hi;
    r.w.ax = 0x600;
    hi = addr >> 16;
    r.w.bx = hi;
    r.w.cx = addr;
    hi = size >> 16;
    r.w.si = hi;
    r.w.di = size;
    int386(0x31, &r, &r);
    return r.w.cflag == 0;
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x283F0
// WIN: 0x0044ff14  (unverified)
// Lines 2787–2787
//
// One-line forwarder onto start_system, kept distinct so it can be
// called from the assembly entry stub.
void start_game(void)
{
    start_system();
}

// FUNCTION: C2 0x28470
// WIN: 0x0044ff24
// Lines 2793–2810
//
// Tear-down counterpart of start_system: stop the runtime, print
// the goodbye banner, and exit(0).
//
// The 265-byte symbol extent also contains start_system's un-hauled
// remainder (L2825-2852) at +0x23: Rule 125 -- start_game's tail call
// became `jmp start_system` and StraightenCode hauled start_system's
// head (through its first unconditional jmp, line records orphaned)
// up to 0x283FA, leaving the rest here.  Hence start_system must be
// DEFINED AFTER exit_game (below) so the optimizer reproduces the
// haul; the symbol addresses are optimizer artifacts (c2 func-order
// exempts moved-code functions).
void exit_game(void)
{
    stop_system();
    printf("\nExiting Caesar II.\n");
    exit(0);
}

// FUNCTION: C2 0x283FA
// WIN: 0x0044ff39
// Lines 2812–2852
//
// Rule 125 moved-code: defined AFTER exit_game in source (see the
// note there); the head through the first `jmp` is hauled up to
// 0x283FA behind start_game's elided tail call, the remainder stays
// at exit_game+0x23.
//
// Boot the runtime.  Seeds the two random generators, clears the
// debug test_mode flags + used_memory + key_ascii, zeroes the
// 0x300-byte palette black-out buffer, then puts the screen into
// the configured mode (1 = VGA mode-X 320×200, 2 = SVGA 640×480,
// 3 = SVGA 640×400).  Allocates the off-screen render target
// `internal_screen`, brings up the scratch buffer, sound, screen
// clear and mouse, and returns true iff exit_flag is still clear.
int start_system(void)
{
    int i;

    randseed = 0x54657687;
    scatseed = 0x34518632;
    test_mode4 = 0;
    test_mode3 = 0;
    test_mode2 = 0;
    test_mode1 = 0;
    used_memory = 0;
    for (i = 0; i < 0x300; i++)
        black_out_data[i] = 0;
    key_ascii = 0;
    if (screen_mode == 1) {
        clear_all_screens();
        set_vga_256x();
    }
    else if (screen_mode == 2) vid_error = set_svga_640_480(0);
    else if (screen_mode == 3) vid_error = set_svga_640_480(1);

    screen_refresh_flag = 0;
    if (screen_mode == 1)      { screen_width = 0x140; screen_height = 0xc8; }
    else if (screen_mode == 2) { screen_width = 0x280; screen_height = 0x1e0; }
    else                       { screen_width = 0x280; screen_height = 0x190; }
    screen_size = screen_width * screen_height;

    internal_screen = 0;
    internal_screen = malloc(screen_size);
    if (internal_screen != 0) used_memory += (unsigned int)screen_size / 0x400;
    setup_scratch_buffer();
    start_sounds();
    clear_screens();
    set_mouse_limits();
    pointer_mode = 0;
    dos_memory = 0;
    return exit_flag == 0;
}

// FUNCTION: C2 0x28579
// Lines 2854–2868
//
// Query the DPMI host for the current free-memory snapshot:
//   * int 0x31 fn 0x500 — fills a 0x20-byte block at `memory` with
//                         the DPMI memory information; offset 0x1c
//                         is the largest free block in pages.
//                         dos_memory = pages * 4096 (KB-ish).
//   * _memavl()           — near-heap available bytes.
//   * _memmax()           — largest contiguous near-heap block.
#ifdef __WATCOMC__
void get_dos_memory(void)
{
    union REGS r;
    struct SREGS sr;

    r.x.eax = 0x500;
    memset(&sr, 0, sizeof sr);
    sr.es = FP_SEG((void __far *)&memory);
    r.x.edi = (int)&memory;
    int386x(0x31, &r, &r, &sr);
    dos_memory = memory.free_linear_pages * 4;
    avl_memory = _memavl();
    max_memory = _memmax();
}
#endif /* __WATCOMC__ */

// FUNCTION: C2 0x285EE
// WIN: 0x004500d3
// Lines 2870–2875
//
// Allocate scratch_buffer with the size in scratch_buffer_size and
// charge the (KB-rounded) cost to used_memory.
void setup_scratch_buffer(void)
{
    scratch_buffer = 0;
    if (scratch_buffer_size != 0)
        scratch_buffer = malloc(scratch_buffer_size);
    if (scratch_buffer != 0)
        used_memory += scratch_buffer_size / 1024;
}

// FUNCTION: C2 0x2863C
// WIN: 0x0045012c
// Lines 2877–2884
//
// Release the scratch buffer if any, and decrement used_memory by
// the buffer's KB size.
void free_scratch_buffer(void)
{
    if (scratch_buffer != 0) {
        free((void *)scratch_buffer);
        used_memory -= scratch_buffer_size / 1024;
    }
}

// FUNCTION: C2 0x28672
// Lines 2886–2900
//
// Probe the heap by repeatedly malloc()/free()ing larger blocks
// (in 1 MB / 0x400 KB steps) until allocation fails, then back off
// by one step.  The final allocable_memory is in KB.
void get_free_memory(void)
{
    void *p;
    int n;

    allocable_memory = 0x400;
    n = allocable_memory;
    while ((p = malloc(n)) != NULL) {
        free(p);
        allocable_memory += 0x400;
        n = allocable_memory;
    }
    allocable_memory -= 0x400;
    allocable_memory = allocable_memory / 0x400;
}

// FUNCTION: C2 0x286DA
// WIN: 0x00450206
// Lines 2903–2911
//
// Tear down the runtime systems brought up by start_system,
// in reverse order:
//
//   1. Free the off-screen render target (internal_screen) if
//      one was allocated.
//   2. Release the scratch buffer used by the rendering layer.
//   3. If we ran in mode 1 (320x200x256), restore the chip's
//      default sequencer/palette state.
//   4. Clear the DOS text page and switch the BIOS back to
//      mode 3 (80x25 colour text).
//   5. Stop the sound subsystem (closes Miles drivers,
//      releases timer hooks, etc.).
//
// internal_screen is declared 'int' globally but stores a
// malloc'd pointer; the cast is conventional throughout the
// codebase.
void stop_system(void)
{
    if (internal_screen != 0) free(internal_screen);
    free_scratch_buffer();
    if (screen_mode == 1) unset_vga_256x();
    dos_cls();
    set_mode3();
    stop_sounds();
}
