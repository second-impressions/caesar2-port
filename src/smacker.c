#include "pcsound.h"
#include <stdlib.h>      /* malloc, free */

#include "c2_data.h"
#include "c2_types.h"
#include "smacker.h"     /* RAD Smacker entry-point pragmas */

int vgawintab[2] = { 65536, 196610 };

/* File-local Smacker playback state. */
int smk_ref_hi;
int smack_frame;
int smk_height;
int smack_from_cd;
char * smack_filename;
int smksumy[15];
int smacker_on;
struct smk_handle *smk;
int smk_ref_wi;

#pragma aux high_beep modify exact [eax ebx ecx];

/* temp_palette / vgawintab declared in c2_data.h as int[] */

// No-op placeholder for the vgawinrout hook.
// FUNCTION: C2 0x135be
void vgawinrout(void)
{
}

// Allocates memory for the Smacker library.
// FUNCTION: C2 0x135bf
void *__pascal radmalloc(unsigned int size)
{
    if (size == 0) return (void *)size;
    return malloc(size);
}

// Releases memory allocated for the Smacker library.
// FUNCTION: C2 0x135d2
// FUNCTION: C2WIN 0x0044b56e
void __pascal radfree(void *ptr)
{
    free(ptr);
}

// Open a Smacker movie path and play its first frame. ``mode`` selects the playback path: 1 =
// full-screen with PL8 fallback, 2 = blit to back-buffer (no fallback).
// FUNCTION: C2 0x135de
void start_smacking(char *p, int left, int top, int mode)
{
    int sample_flags;

    smacker_on = 0;
    if (link_to_smacker() == 0) return;

    my_strcpy("SMK", extension, 4);
    put_filename_extension(p);
    smack_filename = p;
    smack_from_cd  = 1;
    if (is_file_on_harddrive(p) != 0)
        smack_from_cd = 0;
    if (smack_from_cd != 0)
        cd_path(smack_filename);
    free_scratch_buffer();

    if (allow_samples() == 0) {
        sample_flags = 0;
        high_beep();
    } else if (c2inf.samples_on == 0) {
        sample_flags = 0;
    } else {
        sample_flags = 0x200;
        if (mode == 1) sample_flags = 0x240;
    }
    if (c2inf.anims_on != 0)
        smk = SmackOpen(smack_filename, sample_flags, -1);
    else
        smk = 0;

    if (smk == 0) {
        if (smack_from_cd != 0) main_path();
        setup_scratch_buffer();
        if (mode != 1) return;

        my_strcpy("pl8", extension, 4);
        put_filename_extension(p);
        if (readfile(p, ((void *)scratch_buffer), 0x186a0, 0) == 0) return;

        my_strcpy("256", extension, 4);
        put_filename_extension(p);
        if (readfile(p, temp_palette, 0x300, 0) == 0) return;

        set_palette(temp_palette);
        general_sprite(0, left, top);
        setup_refresh_area(left, top, 0x14, 0xa, 1);
        refresh_svga_screen();
        return;
    }

    /* Choose refresh dimensions from the movie height. */
    smk_height = smk->Height;
    if (smk_height == 0xc8) {
        smk_ref_hi = 0x0d;
        smk_ref_wi = 0x14;
    } else {
        if (smk_height == 0xc8) {
            smk_ref_hi = 0x19;
            smk_ref_wi = 0x28;
        } else {
            smk_ref_hi = 0x1e;
            smk_ref_wi = 0x28;
        }
    }
    smacker_on = 1;
    stop_samples();

    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      internal_screen, 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }

    if (smk->NewPalette != 0) {
        p = (char *)smk;
        if (smk->PalType == 1)
            p += 0x70;
        else
            p += 0x374;
        PaletteSet((unsigned char *)p);
    }
    SmackDoFrame(smk);
    SmackNextFrame(smk);

    if (mode == 0) {
        setup_refresh_area(0, 0, smk_ref_wi, smk_ref_hi, 1);
        refresh_svga_screen();
    } else if (mode == 1) {
        setup_refresh_area(left, top, 0x14, 0xa, 1);
        refresh_svga_screen();
    }

    while ((short)SmackWait(smk) != 0) { }

    smack_frame = 2;
    if (smack_from_cd != 0) main_path();
}

// Per-tick smacker driver: if a movie is open and the next frame is ready (``SMACKWAIT`` returns
// 0), updates the palette, draws the frame, and either schedules a screen refresh (mode 0/1) or
// skips it (mode 2 — caller refreshes the back-buffer).
// FUNCTION: C2 0x138bc
int continue_smacking(int p1, int x, int mode)
{
    int ret = 0;

    if (link_to_smacker() == 0) return 0;
    if (smacker_on == 0) return 0;
    if ((short)SmackWait(smk) != 0) return 0;

    if (smk->NewPalette != 0) {
        unsigned char *pal;
        if (smk->PalType == 1) pal = smk->Palette;
        else                   pal = smk->Palette2;
        PaletteSet(pal);
    }

    SmackDoFrame(smk);
    if (smack_frame < smk->Frames) {
        SmackNextFrame(smk);
        if (mode == 0)
            setup_refresh_area(0, 0, smk_ref_wi, smk_ref_hi, 1);
        else if (mode == 1)
            setup_refresh_area(p1, x, 0x14, 0xa, mode);
        ret = 1;
    }
    smack_frame = smack_frame + 1;
    if (smack_frame >= smk->Frames) {
        SmackClose(smk);
        smacker_on = 0;
        ret = 1;
        setup_scratch_buffer();
    }
    return ret;
}

// Stops smacking.
// FUNCTION: C2 0x139ab
void stop_smacking(void)
{
    if (smacker_on) {
        if (smack_from_cd) cd_path(smack_filename);
        SmackClose(smk);
        setup_scratch_buffer();
        smacker_on = 0;
        if (smack_from_cd) main_path();
    }
}

// Returns smacker_on != 0 for the are smacking query.
// FUNCTION: C2 0x139f7
int are_smacking(void)
{
    return smacker_on != 0;
}

// No-op placeholder for the show smksum screen hook.
// FUNCTION: C2 0x13a06
void show_smksum_screen(void)
{
}
