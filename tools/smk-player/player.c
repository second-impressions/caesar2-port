/* Smacker playback test for the delinked RAD Smacker OMF object.
 *
 * Exercises the full delinked decode path:
 *   SmackOpen -> _radopen/__qread/blockread -> SmackDoFrame ->
 *   _SmackDoFrameToBuffer (unsmack.ASM decompressor) -> SmackToBuffer.
 *
 * Default (headless): decode every frame and dump a few as .ppm images
 * (index -> RGB via the movie's 6-bit VGA palette).  With "vga" arg it
 * also sets mode 13h and blits (for dosbox-x / real hardware).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <i86.h>
#include <conio.h>
#include <stdarg.h>
#include "smacker.h"

/* step tracer: writes to stdout AND PLAYLOG.TXT, flushing each line, so the
 * last step reached survives even if DOSBox-X closes on a fault (C89 varargs). */
static FILE *g_log = 0;
static void DBG(const char *fmt, ...)
{
    va_list ap;
    printf("[dbg] ");
    va_start(ap, fmt); vprintf(fmt, ap); va_end(ap);
    printf("\n"); fflush(stdout);
    if (g_log) {
        fprintf(g_log, "[dbg] ");
        va_start(ap, fmt); vfprintf(g_log, fmt, ap); va_end(ap);
        fprintf(g_log, "\n"); fflush(g_log);
    }
}

/* Miles AIL (delinked from PS.EXE).  #pragma aux "_*" gives the real
 * _AIL_* linker names with AIL's caller-cleanup register contract. */
#pragma aux AIL_startup          "_*" parm caller [] modify [eax ebx ecx edx]
#pragma aux AIL_shutdown         "_*" parm caller [] modify [eax ebx ecx edx]
#pragma aux AIL_install_DIG_INI  "_*" parm caller [] modify [eax ebx ecx edx]
extern int  AIL_startup(void);
extern void AIL_shutdown(void);
extern int  AIL_install_DIG_INI(int *dig_out);          /* 0 == success */
extern void __cdecl SetSmackAILDigDriver(int a, int b); /* _SetSmackAILDigDriver */

static void write_ppm(const char *fn, unsigned char *pix, int w, int h,
                      unsigned char *pal6)
{
    FILE *f = fopen(fn, "wb");
    int i;
    if (!f) { printf("  cannot write %s\n", fn); return; }
    fprintf(f, "P6\n%d %d\n255\n", w, h);
    for (i = 0; i < w * h; i++) {
        unsigned char idx = pix[i];
        fputc(pal6[idx * 3 + 0] << 2, f);   /* 6-bit -> 8-bit */
        fputc(pal6[idx * 3 + 1] << 2, f);
        fputc(pal6[idx * 3 + 2] << 2, f);
    }
    fclose(f);
    printf("  dumped %s\n", fn);
}

/* Set a display mode: a standard BIOS mode (<0x100, e.g. 0x13 / 0x03) or a
 * VESA mode (>=0x100, e.g. 0x101 = 640x480x256) via INT 10h AX=4F02h. */
static void set_gfx_mode(int mode)
{
    union REGS r;
    if (mode < 0x100) { r.w.ax = (unsigned short)mode; }
    else { r.w.ax = 0x4F02; r.w.bx = (unsigned short)mode; }
    int386(0x10, &r, &r);
}

/* VESA banked framebuffer: point window A at the given 64KB bank (the
 * granularity DOSBox-X's svga_s3 reports) via INT 10h AX=4F05h.  The window
 * itself lives at 0xA0000, directly addressable in the DOS/4GW flat model. */
static void vesa_set_bank(int bank)
{
    union REGS r;
    r.w.ax = 0x4F05; r.w.bx = 0; r.w.dx = (unsigned short)bank;
    int386(0x10, &r, &r);
}

/* Copy a full mode-sized frame (total bytes) to the display.  Mode 13h is the
 * flat 0xA0000 window; VESA 640x480 is banked, so we walk 64KB windows. */
static void blit_screen(unsigned char *out, long total, int banked)
{
    unsigned char *win = (unsigned char *)0xA0000L;
    long off = 0;
    int bank = -1;
    if (!banked) { memcpy(win, out, (size_t)total); return; }
    while (off < total) {
        int cur = (int)(off >> 16);
        long winoff = off & 0xFFFFL;
        long chunk = 0x10000L - winoff;
        if (chunk > total - off) chunk = total - off;
        if (cur != bank) { vesa_set_bank(cur); bank = cur; }
        memcpy(win + winoff, out + off, (size_t)chunk);
        off += chunk;
    }
}

/* Wait for the start of vertical retrace (VGA input status @ 0x3DA, bit 3).
 * Blitting + DAC programming here is tear-free and snow-free: the CRT isn't
 * fetching pixels/palette, so an async IRQ (the AIL sound timer) interleaving
 * mid-update can't leave a visible half-drawn frame or a mid-scan DAC write. */
static void vga_wait_retrace(void)
{
    while (inp(0x3DA) & 0x08) { /* wait out any retrace in progress */ }
    while (!(inp(0x3DA) & 0x08)) { /* wait for retrace to begin */ }
}

/* Pick a palette index that displays as black, for the letterbox bars.  Index
 * 0 is NOT reliably black: the Mac re-encodes put magenta (the transparency
 * key) at index 0, so bars filled with index 0 come out pink.  Scan for the
 * darkest entry (exact black wins immediately) in the video's own palette. */
static int black_index(unsigned char *pal6)
{
    int i, best = 0, bestsum = 0x7fffffff;
    for (i = 0; i < 256; i++) {
        int s = pal6[i*3] + pal6[i*3+1] + pal6[i*3+2];
        if (s < bestsum) { bestsum = s; best = i; if (s == 0) break; }
    }
    return best;
}

static void vga_palette(unsigned char *pal6)
{
    int i;
    /* Program the DAC with interrupts off so the AIL timer ISR can't split
     * the index/RGB write sequence (garbled palette == coloured artifacts). */
    _disable();
    outp(0x3C8, 0);
    for (i = 0; i < 768; i++) outp(0x3C9, pal6[i]);
    _enable();
}

static void tick_delay(void)
{
    volatile unsigned long *bios = (volatile unsigned long *)0x46CL;
    unsigned long t = *bios;
    while (*bios == t) { /* spin ~55ms */ }
}

int main(int argc, char **argv)
{
    struct smk_handle *s;
    unsigned char *buf, *pal, *out = 0;
    int w, h, frames, f, use_vga, snd = 0;
    /* display-mode state (chosen from the video size, letterboxed) */
    int mw = 0, mh = 0, gmode = 0, banked = 0;   /* mode geometry / VESA flag */
    int ox = 0, oy = 0, vsx = 0, vsy = 0, vw = 0, vh = 0;  /* placement + crop */
    int bar_idx = 0;                             /* palette index for black bars */
    char *fn = (argc > 1) ? argv[1] : "MOVIE.SMK";
    char nm[64];

    /* modes: "vga" = mode 13h display; "trace" = text-mode real-time playback
     * with sound + progress prints (no graphics, so console stays visible);
     * default = dump PPM frames (silent). */
    int use_trace = (argc > 2 && strcmp(argv[2], "trace") == 0);
    /* snddump: sound ON but dump frames (no realtime/vga) -- lets us diff
     * decoded frame bytes sound-on vs sound-off to localise A/V corruption. */
    int use_snddump = (argc > 2 && strcmp(argv[2], "snddump") == 0);
    use_vga = (argc > 2 && strcmp(argv[2], "vga") == 0);

    g_log = fopen("PLAYLOG.TXT", "w");
    DBG("main: fn=%s vga=%d trace=%d", fn, use_vga, use_trace);

    /* Miles AIL must be brought up BEFORE SmackOpen even in silent/dump mode:
     * Smacker's sound-glue calls into AIL during open, and real AIL routines
     * fault on uninitialised global state (unlike no-op stubs). */
    DBG("calling AIL_startup...");
    AIL_startup();
    DBG("AIL_startup returned");
    if (use_vga || use_trace || use_snddump) {
        int dig = 0;
        DBG("calling AIL_install_DIG_INI (needs DIG.INI+SB16.DIG+BLASTER)...");
        if (AIL_install_DIG_INI(&dig) == 0) {
            DBG("AIL_install_DIG_INI ok, dig=%d", dig);
            SetSmackAILDigDriver(dig, 0);   /* game order: (driver, 0) */
            DBG("SetSmackAILDigDriver done -> sound ON");
            snd = 1;
        } else {
            DBG("AIL_install_DIG_INI FAILED -> silent");
        }
    }

    DBG("calling SmackOpen(%s, flags=0x%x)...", fn, snd ? 0x200 : 0);
    s = SmackOpen(fn, snd ? 0x200 : 0, snd ? 0xFFFFFFFFu : 0);
    DBG("SmackOpen returned %p", (void *)s);
    if (!s) { printf("SmackOpen(%s) FAILED\n", fn); return 1; }

    w = *(int *)((char *)s + 4);          /* Width  @ +0x04 */
    h = s->Height;                         /* Height @ +0x08 */
    frames = (int)s->Frames;               /* Frames @ +0x0C */
    printf("opened %s: %dx%d, %d frames\n", fn, w, h, frames);
    if (w <= 0 || h <= 0 || w > 1024 || h > 1024) {
        printf("bad dimensions, aborting\n"); return 2;
    }

    buf = (unsigned char *)malloc((size_t)w * h);
    memset(buf, 0, (size_t)w * h);
    DBG("buffer %d bytes allocated at %p", w * h, (void *)buf);

    if (use_vga) {
        /* Pick the smallest standard mode that fits the video 1:1; if it
         * doesn't fit, use the next standard VESA mode and letterbox.
         *   <=320x200  -> mode 13h (320x200)
         *   otherwise  -> VESA 0x101 (640x480) -- covers 500x240 + 640x480 */
        if (w <= 320 && h <= 200) { gmode = 0x13;  mw = 320; mh = 200; banked = 0; }
        else                      { gmode = 0x101; mw = 640; mh = 480; banked = 1; }
        vw = w < mw ? w : mw;  vh = h < mh ? h : mh;     /* centre-crop if larger */
        vsx = (w - vw) / 2; vsy = (h - vh) / 2;          /* source crop origin  */
        ox  = (mw - vw) / 2; oy = (mh - vh) / 2;         /* dest centre (bars)  */
        out = (unsigned char *)malloc((size_t)mw * mh);
        memset(out, 0, (size_t)mw * mh);                 /* black bars, drawn once */
        DBG("video %dx%d -> mode %#x %dx%d, centred at (%d,%d)", w, h, gmode, mw, mh, ox, oy);
        set_gfx_mode(gmode);
    }

    /* Register the decode target ONCE, exactly like the game's start_smacking
     * (continue_smacking then calls SmackDoFrame repeatedly without re-registering). */
    SmackToBuffer(s, 0, 0, w, h, buf, 0);

    for (f = 0; f < frames; f++) {
        /* Frame pacing = the game's continue_smacking (smacker.c): gate every
         * frame on SmackWait, which blocks until it's time for THIS frame
         * relative to the samples the AIL driver is playing (and services the
         * audio buffer while it waits).  A fixed BIOS-tick delay instead makes
         * the video run at 18.2Hz while the audio plays at its own rate -> the
         * drift + jumping you hear.  Only when there is no audio clock (sound
         * off) do we fall back to the frame tick. */
        if (snd)
            while ((short)SmackWait(s) != 0) { /* spin; SmackWait feeds audio */ }

        SmackDoFrame(s);
        pal = (s->PalType == 1) ? s->Palette : s->Palette2;

        if (use_trace) {
            if (f == 0 || (f % 20) == 0 || f == frames - 1)
                DBG("frame %3d/%d decoded (NewPal=%d)", f, frames, s->NewPalette);
            if (!snd) tick_delay();     /* no audio clock -> pace by BIOS tick */
        } else if (use_vga) {
            int yy;
            if (!snd) tick_delay();     /* no audio clock -> pace by BIOS tick */
            if (s->NewPalette) {        /* palette changed: re-black the bars in it */
                bar_idx = black_index(pal);
                memset(out, bar_idx, (size_t)mw * mh);
            }
            for (yy = 0; yy < vh; yy++)  /* composite video into the letterboxed frame */
                memcpy(out + (long)(oy + yy) * mw + ox,
                       buf + (size_t)(vsy + yy) * w + vsx, vw);
            vga_wait_retrace();         /* then sync the update to the frame */
            if (s->NewPalette) vga_palette(pal);
            blit_screen(out, (long)mw * mh, banked);
        } else if (f == 0 || f == frames / 2 || f == frames - 1) {
            FILE *rf;
            sprintf(nm, "frame%03d.ppm", f);
            write_ppm(nm, buf, w, h, pal);
            sprintf(nm, "frame%03d.raw", f);   /* 768 pal + w*h idx + hdr */
            rf = fopen(nm, "wb");
            if (rf) {
                printf("  NewPalette=%d PalType=%d\n", s->NewPalette, s->PalType);
                fwrite(&w, 4, 1, rf); fwrite(&h, 4, 1, rf);
                fwrite(pal, 1, 768, rf);
                fwrite(buf, 1, (size_t)w * h, rf);
                fclose(rf);
            }
        }
        if (f < frames - 1) SmackNextFrame(s);
    }

    /* Playback done.  For the VGA path, hold the last (clean) frame for a
     * keypress and restore TEXT mode BEFORE any further console output:
     * printf/DBG in a graphics mode make the BIOS teletype render text into
     * the framebuffer, which is the stray closing "message" drawn over the
     * held DOS frame (and, in the VESA-banked Mac path, an index-0 = magenta
     * stripe at the top).  No console I/O until we're back in mode 03h. */
    if (use_vga) { if (argc <= 3) getch(); set_gfx_mode(0x03); }

    DBG("loop done, SmackClose...");
    SmackClose(s);
    DBG("AIL_shutdown...");
    AIL_shutdown();
    DBG("exit clean");
    if (g_log) fclose(g_log);
    printf("done: %d frames decoded\n", frames);
    return 0;
}
