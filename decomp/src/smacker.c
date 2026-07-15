// D:\C2\CODE\smacker.c

#include "pcsound.h"
#include <stdlib.h>      /* malloc, free */

#include "c2_data.h"
#include "c2_types.h"
#include "smacker.h"     /* RAD Smacker entry-point pragmas */

int vgawintab[2] = { 65536, 196610 };

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
int smk_ref_hi;
int smack_frame;
int smk_height;
int smack_from_cd;
char * smack_filename;
int smksumy[15];
int smacker_on;
struct smk_handle *smk;
int smk_ref_wi;

/* high_beep tail-calls into the clib3r ``nosound`` helper which
 * preserves edx; PS keeps the value of ``sample_flags`` in edx
 * across the call.  Without this aux clause Watcom would spill /
 * reload, breaking byte-equivalence. */
#pragma aux high_beep modify exact [eax ebx ecx];

/* temp_palette / vgawintab declared in c2_data.h as int[] */

// FUNCTION: C2 0x135BE
// WIN: 0x00401384  (unverified)
// Lines 13–13
void vgawinrout(void)
{
}

// FUNCTION: C2 0x135BF
// Lines 34–40
void *__pascal radmalloc(unsigned int size)
{
    if (size == 0) return (void *)size;
    return malloc(size);
}

// FUNCTION: C2 0x135D2
// WIN: 0x0044b56e
// Lines 42–45
void __pascal radfree(void *ptr)
{
    free(ptr);
}

// FUNCTION: C2 0x135DE
// Lines 47–120
//
// Open a Smacker movie path and play its first frame.
// ``mode`` selects the playback path: 1 = full-screen with PL8
// fallback, 2 = blit to back-buffer (no fallback).  When SMK
// open fails, mode 1 falls back to displaying the matching
// .pl8 / .256 stills via ``general_sprite``.
//
// Args: filename ``p`` (eax), ``left``/``top`` screen pos (edx/ebx),
// ``mode`` (ecx).  ``left``/``top`` map to SmackToBuffer/Screen's
// left,top exactly as the callers set them (param2=left).
//
// BYTE-EXACT to PS.EXE.
//
// `p` is reused as the palette scratch pointer, assigned inside the
// `if (smk->NewPalette)` block -- that pins it in ESI so the palette walk is
// `add esi,0x70/0x374`, and keeps its live range short enough that the left/top
// tie resolves PS's way (top->EDI, left->EBP).
//
// The three call-argument push registers (SmackToScreen smk, SmackToBuffer smk,
// internal_screen) are picked by the RISCify rover FindRegister (10.0a va
// 0x62a29; owp4v1 i86ldstr.c).  In code generation, before register allocation,
// LdStAlloc lowers each `push <global>` to `mov reg,[global]; push reg` with
// reg = the next DoubleRegs entry (EAX,EDX,EBX,ECX,ESI,EDI) not live, over a
// cursor that PERSISTS across the routine -- so the register depends on how many
// dword loads were RISCified before the call.
//
// PS's cursor is +1 ahead at those pushes.  The fix: write `smk_ref_wi = 0x28`
// in BOTH arms of the dead inner `if (smk_height==0xc8)` instead of once after
// it -- store-for-store identical, but splitting the basic blocks makes the
// compiler emit one extra COALESCED (byte-invisible) dword load before the
// calls, advancing the cursor +1.  That turns EDX/EBX/ECX into PS's EBX/ECX/ESI
// and self-heals at the next push.  decomp-verify's `Rover:` hint diagnoses this
// class; model + simulator: watcom10.0a docs/rover-model.md, tools/rover_sim.py.
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

    /* Smacker open succeeded — set up scaling refresh dims by
     * movie height.  PS shows a curious "dead-code" 240-px
     * branch: the inner re-comparison reuses the flags from the
     * outer ``cmp eax, 200`` so the 0x19 / smk_ref_hi=25 leg is
     * unreachable.  We keep the structure (two cmps against the
     * same constant) so the residual matches byte-for-byte. */
    smk_height = smk->Height;
    if (smk_height == 0xc8) {
        smk_ref_hi = 0x0d;
        smk_ref_wi = 0x14;
    } else {
        if (smk_height == 0xc8) {      /* dead branch in PS */
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

// FUNCTION: C2 0x138BC
// Lines 122–151
//
// Per-tick smacker driver: if a movie is open and the next
// frame is ready (``SMACKWAIT`` returns 0), updates the
// palette, draws the frame, and either schedules a screen
// refresh (mode 0/1) or skips it (mode 2 — caller refreshes
// the back-buffer).  When the movie hits its last frame this
// closes the smacker out.  Returns 1 if a frame was drawn or
// the movie ended this tick; 0 otherwise.
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

// FUNCTION: C2 0x139AB
// Lines 153–162
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

// FUNCTION: C2 0x139F7
// Lines 166–166
int are_smacking(void)
{
    return smacker_on != 0;
}

// FUNCTION: C2 0x13A06
// WIN: 0x00401384  (unverified)
//
// Empty stub — Smacker summary-screen hook compiled away in
// release.  PS body is a single `c3 ret` (1 b); the 8 trailing
// bytes `20 20 00 00 20 20 00 00` are aggregate-init `SYM_TEMP`
// statics from the **next** .obj (smackw32.lib's first TU).
// Reproduced in `decomp/src/smackinp.c` via two matching
// `char[4] = "  "` aggregate-init locals — see Rule 45 in
// `docs/watcom-codegen-patterns.md`.
void show_smksum_screen(void)
{
}
