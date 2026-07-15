// D:\C2\CODE\pcsound.c

#pragma aux _ds "*"
#include "pcsound.h"
#include "c2_data.h"
#include "smacker.h"
#include <fcntl.h>             /* O_BINARY */
/* The TU's own far-pointer error-code builder, MK_FP(off, seg) --
 * NOT <i86.h>'s MK_FP(seg, off) macro.  Recovered 2026-07-12 from
 * three witnesses (full detail above start_samples):
 *   DOS retail: an EMPTY-BODY #pragma aux -- the "call" vanishes and
 *     the args land in the return pair directly (off->EAX, seg->EDX,
 *     value [dx eax]).  This is the ONLY spelling whose seg=0 at the
 *     handle-check fail compiles with NO xor edx,edx (the encoder's
 *     branch-implied-zero tracker elides the materialization after
 *     `test edx,edx; jne`) while keeping the split load live-out --
 *     byte-exact where every macro/cast form diverged.
 *   DOS demo (C2DEMO 1995-08): the same helper WITH a real body
 *     (`test edx,edx` dispatcher) called via a shared fail tail.
 *   Win port: MSVC can't express #pragma aux -> they made it a real
 *     DEAD function (the empty stub at 0x409344; eax left undefined,
 *     callers discard the sentinel).  Same (off, seg) arg order as
 *     the push sequence shows.  */
#ifdef __WATCOMC__
char __far *MK_FP(int off, int seg);
#pragma aux MK_FP = parm [eax] [edx] value [dx eax];
#else
static char __far *MK_FP(unsigned off, unsigned seg) { }
#endif
extern int  open(const char *path, int flags, ...);
void __cdecl mood_modfication(int seq);

/* File-local supplements (not in c2_data.h) */
extern int _ds;

#include "ail.h"

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
char negative_buffer[624];
unsigned char * db_buf[2];
struct sample_slot_rec ss_entries[10];
int S_mdi[2];
int S_dig[6];
int next_sequence;
int smacker_open;
int sequences_running;
int tune2;
int dig_status;
char positive_buffer[532];
int samples_running;
unsigned char tune_buffer[27500];
int db_handle;
int db_playing;
char *db_file;
char *sample_buffer;
int mdi_status;
int next_sample;
int sslot;
int ds;
int tune1;
int dig;
int ms;
int mdi;
int db_recommended_buffer_size;
int db_buffer_size;
struct ambient_rec ambient_list[25];   /* stride 0x46=70 (init_city_ambients imul), bound cmp edx,0x19 -> 25; span 1752 has 2b trailing pad */

/* Forward declarations of pcsound.c functions used internally.
 *
 * The `modify exact [eax gs]` contracts (measured load-bearing, both
 * functions): `exact` makes EDX callee-saved -> the prologue gains
 * `push edx` and every error return funnels through ONE shared
 * pop-chain epilogue (without it each fail gets its own inline
 * epilogue and EDX stays scratch).  Note the consequence: the
 * epilogue's `pop edx` restores the CALLER's EDX over the far-ptr
 * seg half -- every error return's segment is garbage by contract;
 * callers only ever read the offset half.  `gs` neutralizes the -mf
 * GS-float default (calls zap GS; an exact-save function would
 * otherwise bracket itself in push/pop gs).  EAX in the list is
 * redundant (return regs exempt); `[gs]` alone is byte-identical,
 * as is -zgp + `[eax]` TU-wide.  start_sound/start_tune carry no
 * pragma: default convention (no push edx, inline epilogues). */
char __far *start_samples(void);
#pragma aux start_samples modify exact [eax gs];
char __far *start_sequences(void);
#pragma aux start_sequences modify exact [eax gs];
char __far *start_sound(char *buf, int loop_count);
char __far *start_tune(unsigned char *seq_arg, int sequence_num, int slot);
void init_ss_entires(void);

/* CRT */
void free(void *p);

extern void _pos_ret3(void);
// FUNCTION: C2 0x11758
// WIN: 0x00401000
// Lines 109–125
//
// Boot the sound subsystem: clear the playback flags, enable
// both digital + MIDI in c2inf, install AIL, and bring up the
// sample + sequence drivers.
extern void *malloc(unsigned int size);

void start_sounds(void)
{
    db_playing      = 0;
    smacker_open    = 0;
    c2inf.samples_on = 1;
    c2inf.tunes_on   = 1;
    next_sequence    = 0;
    next_sample      = 0;
    samples_running  = 0;
    sequences_running = 0;
    AIL_startup();
    start_samples();
    start_sequences();
}

// FUNCTION: C2 0x117A2
// Lines 127–132
//
// Tear down the sound subsystem: end both AIL driver halves and
// shut AIL down.
void stop_sounds(void)
{
    stop_samples();
    stop_sequences();
    AIL_shutdown();
}
// FUNCTION: C2 0x117B8
// WIN: 0x00401085
// Lines 131-146
//
// Installs the digital sound driver: loads the two click WAVs into
// the preloaded buffers, installs DIG.INI, allocates 6 sample
// handles, verifies them, and flips `samples_running`.  Re-entry is a
// no-op.  Error far-pointers built by the TU's own MK_FP(off, seg)
// helper (see its declaration at the file top): 4 = a WAV failed,
// 1 = AIL_install_DIG_INI failed, 2 = a sample handle came back
// NULL.  The success/no-op path falls off through the uninitialised
// `rc`, which the lone caller discards.
//
// BYTE-EXACT 2026-07-12 after ~950 probed variants across 5
// sessions.  The load-bearing pieces, each proven by measurement:
//   * the empty-body #pragma aux MK_FP: its parm [edx] keeps the
//     tested value live-out of the check-loop cond block, so the
//     split load survives LdStCompress (`mov edx,[eax*4+S_dig];
//     test edx,edx` -- every cast/macro spelling re-fused it);
//   * seg literal 0 at the check fail: the encoder's branch-implied
//     -zero tracker elides the `xor edx,edx` after `test edx,edx;
//     jne` (fail1/fail2 keep theirs -- EDX unknown there);
//   * the ANONYMOUS check (`if (S_dig[ds] == 0)`): its fr'd split
//     advances the RISCify rover cursor so the ds++ increment's
//     pick lands EBX (`lea ebx,[eax+1]`); naming the value kills
//     the advance (inc eax), a second S_dig[ds] mention makes the
//     FE bind the address (shl eax,2) -- both fatal, all compiler
//     versions 9.5-11.0;
//   * the one-line do-while: a `for` re-marks its cond/incr in the
//     -d1 stream (line-compare RC-only marks); PS marked the loop
//     once.
// Witnesses: C2DEMO 1995-08 (same helper WITH a body -- a
// `test edx,edx` dispatcher -- via a shared fail tail) and the Win
// port (MSVC can't #pragma aux, so MK_FP became the real dead stub
// at 0x409344).  Full mechanism history: git log + the watcom10.0a
// repo's notes/start-samples-p5p6.md.
//
char __far *start_samples(void)
{
    char __far *rc;

    if (!samples_running)
    if (c2inf.samples_on) {
        if (readfile("poscl.wav",  positive_buffer, 0x214, 0) == 0) return MK_FP(4, 0);
        if (readfile("negcl2.wav", negative_buffer, 0x270, 0) == 0) return MK_FP(4, 0);
        if (AIL_install_DIG_INI(&dig)) return MK_FP(1, 0);
        for (ds = 0; ds < 6; ds++) S_dig[ds] = AIL_allocate_sample_handle(dig);
        ds = 0; do { if (S_dig[ds] == 0) return MK_FP(2, 0); ds++; } while (ds < 6);
        samples_running = 1;
        init_ss_entires();
    }
    return rc;
}

// FUNCTION: C2 0x118A2
// Lines 147–158
// AIL MIDI sequence bootstrap.  Installs the MDI driver, allocates
// two sequence handles, and initialises the mood-tracking globals.
// Error codes (char __far *)1 / MK_FP(2,1) flag install / handle
// failures; the success/no-op path returns through an uninitialised
// `rc` (the AIL far-ptr value-less idiom).  `modify exact [eax gs]`
// (file top) shapes the prologue/epilogue -- see the note there.
// WIN: 0x00401250
char __far *start_sequences(void)
{
    char __far *rc;

    if (!sequences_running && c2inf.tunes_on) {
        AIL_set_GTL_filename_prefix("CAESAR");
        if (AIL_install_MDI_INI(&mdi) != 0) return (char __far *)1;
        for (ms = 0; ms < 2; ms++) {
            S_mdi[ms] = AIL_allocate_sequence_handle(mdi);
        }
        for (ms = 0; ms < 2; ms++) {
            if (S_mdi[ms] == 0) return (char __far *)MK_FP(2, 1);
        }
        tune1 = 0;
        tune2 = 1;
        tune_mood = 0;
        tune_branch_count = 0;
        last_battle_mood = 0;
        last_city_mood = 0;
        sequences_running = 1;
    }
    return rc;
}

// FUNCTION: C2 0x1197B
// WIN: 0x0040138f
// Lines 169–178
//
// Stop every active digital sample slot.  Clears db_playing and ends
// any S_dig handle currently reporting status 4 (PLAYING).
void stop_samples(void)
{
    if (samples_running == 0) return;
    db_playing = 0;
    for (ds = 0; ds < 6; ds++) {
        dig_status = AIL_sample_status(S_dig[ds]);
        if (dig_status == 4) {
            AIL_end_sample(S_dig[ds]);
        }
    }
}

// FUNCTION: C2 0x119E7
// Lines 180–189
//
// Stop every active music sequence.  Clears the city tune flag and
// ends any S_mdi handle currently reporting status 4 (PLAYING).
void stop_sequences(void)
{
    city_tune_playing = 0;
    if (sequences_running == 0) return;
    for (ms = 0; ms < 2; ms++) {
        mdi_status = AIL_sequence_status(S_mdi[ms]);
        if (mdi_status == 4) {
            AIL_end_sequence(S_mdi[ms]);
        }
    }
}

// FUNCTION: C2 0x11A53
// WIN: 0x0040149b
// Lines 193–202
//
// Push the user-configured digital-sample volume to AIL, scaled
// from c2inf.samples_level (0..100) to AIL's 0..127 range via
// totalXpercent.  No-op if samples are disabled or the digital
// driver isn't initialised.
void set_samples_volume(void)
{
    if (c2inf.samples_on == 0)   return;
    if (samples_running == 0)    return;
    AIL_set_digital_master_volume(dig, totalXpercent(0x7f, c2inf.samples_level));
}

// FUNCTION: C2 0x11A8C
// WIN: 0x00401515
// Lines 203–212
//
// Push the user-configured music volume to both AIL sequence
// handles (tune1 and tune2) — scaled from c2inf.tunes_level
// (0..100) to AIL's 0..127 range; fade=0 (instant).
void set_sequences_volume(void)
{
    int vol;

    if (c2inf.tunes_on == 0)     return;
    if (sequences_running == 0)  return;
    vol = totalXpercent(0x7f, c2inf.tunes_level);
    AIL_set_sequence_volume(S_mdi[tune1], vol, 0);
    AIL_set_sequence_volume(S_mdi[tune2], vol, 0);
}

// FUNCTION: C2 0x11AE9
// WIN: 0x0040158e
// Lines 213–222
//
// Begin a 1-second fade-in on S_mdi[idx]: snap to 0 then fade up to
// the user-configured master volume.  Skipped if music is disabled.
void fade_sequence_in(int idx)
{
    int vol;

    if (c2inf.tunes_on == 0)     return;
    if (sequences_running == 0)  return;
    vol = totalXpercent(0x7f, c2inf.tunes_level);
    AIL_set_sequence_volume(S_mdi[idx],   0, 0);
    AIL_set_sequence_volume(S_mdi[idx], vol, 1000);
}

// FUNCTION: C2 0x11B4B
// WIN: 0x00401604
// Lines 223–228
//
// Begin a 1-second fade-out on S_mdi[idx] iff music is enabled
// (c2inf.tunes_on) and the global sequences_running flag is set.
// `AIL_set_sequence_volume(h, target=0, fade_ms=1000)`.
void fade_sequences_out(int idx)
{
    if (c2inf.tunes_on == 0)      return;
    if (sequences_running == 0)   return;
    AIL_set_sequence_volume(S_mdi[idx], 0, 1000);
}

// FUNCTION: C2 0x11B7B
// WIN: 0x0040164d
// Lines 232–248
//
// Schedule a digital sample for playback.  Each sample slot
// owns a 20 000-byte (0x4E20) chunk of `sample_buffer`; if the
// same fname has been queued before, ``check_old_sslots``
// returns the existing slot and we skip the load.  Otherwise
// allocate a new slot via ``get_new_sslot``, ``readfile`` 20 000
// bytes into it, and on success start the sound.
//
// Four guards bypass everything: master samples toggle off,
// AIL not running, empty fname, or no free slot available.
//
void set_sound(char *fname, int arg2)
{
    if (c2inf.samples_on == 0) return;
    if (samples_running == 0) return;
    if (*fname == 0) return;
    if (check_for_free_slot() == 0) return;
    if (check_old_sslots(fname) == 0) {
        get_new_sslot(fname);
        if (readfile(fname, sample_buffer + sslot * 0x4e20,
                     0x4e20, 0) == 0) {
            free_up_sslot(sslot);
            return;
        }
    }
    start_sound(sample_buffer + sslot * 0x4e20, arg2);
}

// FUNCTION: C2 0x11C35
// WIN: 0x00401734
// Lines 250–265
//
// "Priority" variant of set_sound — same flow, but skips the
// check_for_free_slot gate.  Used by callers that always want
// the sample played, displacing the oldest slot if all 10 are
// busy.
//
void set_pri_sound(char *fname, int arg2)
{
    if (c2inf.samples_on == 0) return;
    if (samples_running == 0) return;
    if (*fname == 0) return;
    if (check_old_sslots(fname) == 0) {
        get_new_sslot(fname);
        if (readfile(fname, sample_buffer + sslot * 0x4e20,
                     0x4e20, 0) == 0) {
            free_up_sslot(sslot);
            return;
        }
    }
    start_sound(sample_buffer + sslot * 0x4e20, arg2);
}

// FUNCTION: C2 0x11CE2
// WIN: 0x00401809
// Lines 267–283
//
// Allocate a free voice slot and start a one-shot sample.
// Walks S_dig[0..max_samples) looking for a slot in idle
// (status 2) or paused (status 8) state.  If none found,
// uses the round-robin `next_sample` index regardless.
// Then recycles the slot (end_sample if status 4), inits,
// loads the buffer, sets loop count, and starts.
//
// Far-ptr return is required: error code 3 is MK_FP(0, 3) (lowered to
// `xor edx,edx; mov eax,3`), and the success path returns the AIL
// call's edx:eax directly via tail position so the compiler
// move-eliminates the return.
char __far *start_sound(char *buf, int loop_count)
{
    for (ds = 0; ds < c2inf.max_samples; ds++) {
        dig_status = AIL_sample_status(S_dig[ds]);
        if (dig_status == 2) { next_sample = ds; break; }
        if (dig_status == 8) { next_sample = ds; break; }
    }

    ds = next_sample;
    next_sample++;
    if (next_sample >= c2inf.max_samples) next_sample = 0;

    dig_status = AIL_sample_status(S_dig[ds]);
    if (dig_status == 4) AIL_end_sample(S_dig[ds]);
    AIL_init_sample(S_dig[ds]);
    if (AIL_set_sample_file(S_dig[ds], buf, -1) == 0) return (char __far *)3;
    AIL_set_sample_loop_count(S_dig[ds], loop_count);
    return AIL_start_sample(S_dig[ds]);
}

// FUNCTION: C2 0x11DF2
// WIN: 0x0040198e
// Lines 285–294
//
// Returns nonzero if a sample slot is available.
int check_for_free_slot(void)
{
    for (ds = 0; ds < c2inf.max_samples; ds++) {
        dig_status = AIL_sample_status(S_dig[ds]);
        if (dig_status != 4) return 1;
    }
    return 0;
}

// FUNCTION: C2 0x11E3B
// Lines 296–303
//
// Walk all 4 digital sample slots and end any that report status
// SMP_PLAYING (4).
void stop_all_sounds(void)
{
    for (ds = 0; ds < 4; ds++) {
        dig_status = AIL_sample_status(S_dig[ds]);
        if (dig_status == 4) AIL_end_sample(S_dig[ds]);
    }
}

// FUNCTION: C2 0x11E92
// Lines 305–315
//
// Cinematic "positive" sting playback.  Latches sample slot
// 4, recycles it if currently active, then plays the
// preloaded `positive_buffer`.
//
// The set_sample_file == 0 path emits an unused `xor edx,edx; mov
// eax,3` store that PS keeps but a stricter DSE would remove.  The
// `_pos_ret3` inline-asm thunk forces those exact bytes to land
// in-place because inline asm is treated as a side-effect.
#pragma aux _pos_ret3 = "xor edx,edx" "mov eax,3" modify exact [eax edx]
// WIN: 0x00401a69
void pos_sound(void)
{
    if (c2inf.samples_on != 0 && samples_running != 0) {
        ds = 4;
        dig_status = AIL_sample_status(S_dig[4]);
        if (dig_status == 4) AIL_end_sample(S_dig[ds]);
        AIL_init_sample(S_dig[ds]);
        if (AIL_set_sample_file(S_dig[ds], positive_buffer, -1) == 0) _pos_ret3();
        AIL_start_sample(S_dig[ds]);
    }
}

// FUNCTION: C2 0x11F40
// WIN: 0x00401b30
// Lines 317–326
//
// Twin of pos_sound for `negative_buffer`.  Source order matters --
// the back half (set_sample_file + start) tail-merges with
// pos_sound at the shared push-buf/push-(-1) site.
void neg_sound(void)
{
    if (c2inf.samples_on != 0 && samples_running != 0) {
        ds = 4;
        dig_status = AIL_sample_status(S_dig[4]);
        if (dig_status == 4) AIL_end_sample(S_dig[ds]);
        AIL_init_sample(S_dig[ds]);
        if (AIL_set_sample_file(S_dig[ds], negative_buffer, -1) == 0) _pos_ret3();
        AIL_start_sample(S_dig[ds]);
    }
}

// FUNCTION: C2 0x11FB9
// Lines 332–341
//
// Refill one of AIL's double-buffered sample slots from the
// open db_handle file.  buf is an array of byte-buffer pointers
// (one per sample buffer slot); the slot index is the one AIL
// reports ready via AIL_sample_buffer_ready (-1 if none ready,
// silent no-op).
void serve_sample(int sample_handle, unsigned char **buf, int size)
{
    int slot;
    int n;

    slot = AIL_sample_buffer_ready(sample_handle);
    if (slot == -1) return;
    n = read(db_handle, buf[slot], size);
    AIL_load_sample_buffer(sample_handle, slot, buf[slot], n);
}

// FUNCTION: C2 0x12003
// WIN: 0x00401c57
// Lines 343–368
//
// Stage a streaming digital sample ("db" = digital buffer)
// for double-buffered playback.  Bails out if the master
// sample/speech toggles are off, AIL isn't running, another
// db is already playing, the filename is empty, or the file
// doesn't exist.
//
// Once committed, the file is opened, db_playing is latched,
// the two ping-pong buffers are pinned at scratch_buffer
// +140000 / +150000, AIL is told the recommended buffer size
// for 22050 Hz, our buffer chunk size (10000), and that we'll
// drive sample slot 5 (`ds`).  Then init_sample sets up the
// AIL handle, set_sample_type configures format, and
// set_sample_playback_rate sets the rate.  main_path() flips
// the working drive back to the install dir (since cd_path
// switched it earlier).
void set_db_sound(char *fname)
{
    if (c2inf.samples_on == 0)   return;
    if (c2inf.speech_on == 0)    return;
    if (samples_running == 0)    return;
    if (db_playing != 0)         return;
    if (*fname == 0)             return;
    if (check_file_exists(fname) == 0) return;

    db_file = fname;
    cd_path(fname);
    db_handle = open(db_file, O_RDONLY | O_BINARY);
    db_playing = 1;

    db_buf[0] = scratch_buffer + 140000;   /* 0x222e0 */
    db_buf[1] = scratch_buffer + 150000;   /* 0x249f0 */

    db_recommended_buffer_size = AIL_minimum_sample_buffer_size(dig, 22050, 0);
    db_buffer_size = 10000;
    ds = 5;

    AIL_init_sample(S_dig[ds]);
    AIL_set_sample_type(S_dig[ds], 0, 0);
    AIL_set_sample_playback_rate(S_dig[ds], 22050);
    main_path();
}

// FUNCTION: C2 0x1211E
// WIN: 0x00401da8
// Lines 370–381
//
// Resume / advance the digital-buffer (db) playback loop.  Re-stages
// a chunk via serve_sample(), then if AIL says the previous sample
// finished (status == 2), closes the file handle and clears
// db_playing.  main_path() restores the working directory in either
// case.
void continue_db(void)
{
    if (c2inf.samples_on == 0) return;
    if (samples_running == 0) return;
    if (db_playing == 0) return;
    cd_path(db_file);
    ds = 5;
    serve_sample(S_dig[5], db_buf, db_buffer_size);
    if (AIL_sample_status(S_dig[ds]) == 2) {
        db_playing = 0;
        close(db_handle);
    }
    main_path();
}

// FUNCTION: C2 0x121A9
// WIN: 0x00401e49
// Lines 384–391
//
// Stop the current db playback.  Same early-out triple-guard as
// continue_db, then ends the AIL sample, clears db_playing, closes
// the file handle, and restores CWD via main_path().
void stop_db(void)
{
    if (c2inf.samples_on == 0) return;
    if (samples_running == 0) return;
    if (db_playing == 0) return;
    cd_path(db_file);
    ds = 5;
    AIL_end_sample(S_dig[5]);
    db_playing = 0;
    close(db_handle);
    main_path();
}

// FUNCTION: C2 0x121FA
// WIN: 0x00401ec1
// Lines 396–405
//
// Pause/resume the digital "background" sample channel (S_dig[5]).
// No-op if samples are disabled or the db_playing flag is clear.
// Status 4 (PLAYING) -> AIL_stop_sample; status 8 (PAUSED) ->
// AIL_resume_sample.  Returns 1 on success / no-action, 0 if any
// guard failed.
int pause_db(void)
{
    if (c2inf.samples_on == 0) return 0;
    if (samples_running == 0)  return 0;
    if (db_playing == 0)       return 0;
    ds = 5;
    dig_status = AIL_sample_status(S_dig[ds]);
    if (dig_status == 4)       AIL_stop_sample  (S_dig[ds]);
    else if (dig_status == 8)  AIL_resume_sample(S_dig[ds]);
    return 1;
}

// FUNCTION: C2 0x12279
// Lines 411–418
//
// Load `fname` into `tune_buffer` (27 500-byte staging area)
// via readfile(), then hand the buffer off to start_tune()
// for AIL-driven sequence playback.  Three guards skip the
// load if music is globally disabled (c2inf.tunes_on),
// the AIL sequence engine isn't running, or `fname` is the
// empty string.  `loops` is the AIL "loop count" forwarded
// to start_tune.
void play_tune(char *fname, int loops)
{
    if (c2inf.tunes_on == 0) return;
    if (sequences_running == 0) return;
    if (*fname == 0) return;
    if (readfile(fname, tune_buffer, 0x6b6c, 0) == 0) return;
    start_tune(tune_buffer, 0, loops);
}

// FUNCTION: C2 0x122BC
// Lines 420–441
//
// Drive a music sequence on MDI slot `slot`.  Special-cases:
//   slot == 0 — first end the *other* slot (S_mdi[1]) so two
//               sequences don't clash.
//   slot == 1 — first stop slot 0 (pauses, doesn't free).
// Then probes the target slot's status:
//   status == 4 (DONE)    — release it via end_sequence
//   status == 8 (PAUSED)  — resume in place and tail-jump out
// Otherwise initialises the sequence with the user buffer,
// installs `mood_modfication` as the trigger callback,
// returns error codes 3/4 for init failure, otherwise fades
// in and starts.
//
// Far-ptr return: the two error exits use MK_FP(1, 3) and MK_FP(1,
// 4); the resume / start paths tail-return the AIL call's edx:eax
// directly so the compiler move-eliminates the return.
char __far *start_tune(unsigned char *seq_arg, int sequence_num, int slot)
{
    int rc;

    if (slot == 0) AIL_end_sequence(S_mdi[1]);
    else if (slot == 1) AIL_stop_sequence(S_mdi[0]);

    mdi_status = AIL_sequence_status(S_mdi[slot]);
    if (mdi_status == 4) AIL_end_sequence(S_mdi[slot]);
    else if (mdi_status == 8) {
        return AIL_resume_sequence(S_mdi[slot]);
    }

    rc = AIL_init_sequence(S_mdi[slot], seq_arg, sequence_num);
    AIL_register_trigger_callback(S_mdi[slot], (void (*)())mood_modfication);
    if (rc < 0) return (char __far *)MK_FP(3, 1);
    if (rc == 0) return (char __far *)MK_FP(4, 1);
    fade_sequence_in(slot);
    return AIL_start_sequence(S_mdi[slot]);
}

// FUNCTION: C2 0x1239C
// Lines 443–449
//
// Halt all currently-playing music sequences.  Probes both MDI
// handles in S_mdi[] and uses the asymmetric AIL pair: stop_sequence
// (pauses) for slot 0, end_sequence (frees) for slot 1.
void stop_tune(void)
{
    mdi_status = AIL_sequence_status(S_mdi[0]);
    if (mdi_status == 4) AIL_stop_sequence(S_mdi[0]);
    mdi_status = AIL_sequence_status(S_mdi[1]);
    if (mdi_status == 4) AIL_end_sequence(S_mdi[1]);
}

// FUNCTION: C2 0x123F5
// Lines 451–455
//
// Halt only S_mdi[0] — the first half of stop_tune.
void stop_tune0(void)
{
    mdi_status = AIL_sequence_status(S_mdi[0]);
    if (mdi_status == 4) AIL_stop_sequence(S_mdi[0]);
}

// FUNCTION: C2 0x12424
// Lines 457–465
//
// Branch-on-mood callback: invoked from the AIL sequencer
// when a tune reaches a marked branch point.  Re-evaluates
// the current mood (battle or city, depending on map mode)
// and tells the sequencer where to branch next via
// `AIL_branch_index(seq, tune_branch)`.
//
// Note the typo "modfication" preserved from the PS.EXE
// debug symbol.
void __cdecl mood_modfication(int seq)
{
    tune_mood_hold = 0;
    tune_branch_count++;
    if (map_mode == 2) get_battle_mood();
    else               get_city_mood();
    AIL_branch_index(seq, tune_branch);
}

// FUNCTION: C2 0x12461
// WIN: 0x004021fd
// Lines 467–471
//
// Restore the last-known mood for the current map mode (battle
// uses last_battle_mood, otherwise last_city_mood) into the live
// tune_mood global and return it.
int get_old_mood(void)
{
    int mood;
    if (map_mode == 2) mood = last_battle_mood;
    else               mood = last_city_mood;
    tune_mood = mood;
    return mood;
}

// FUNCTION: C2 0x1247F
// WIN: 0x00402231
// Lines 473–507
//
// Faithful mood→branch dispatcher.  The body follows the PS state
// machine, including transient bad/threat/emergency overrides and the
// fallback away from repeated high moods.
void get_city_mood(void)
{
    if (tune_mood == 10) { tune_mood = 0; tune_branch = 0x28; }
    else if (tune_mood == 11) { tune_mood = 0; tune_branch = 0x29; }
    else if (tune_mood == 12) { tune_mood = 0; tune_branch = 0x2a; }
    else if (tune_mood == 13) { tune_mood = 1; tune_branch = 0x2d; bad_mood = 0xc8; }
    else if (tune_mood == 14) { tune_mood = 1; tune_branch = 0x2b; bad_mood = 0xc8; }
    else if (tune_mood == 15) { tune_mood = 1; tune_branch = 0x2c; bad_mood = 0xc8; }
    else if (tune_mood == 16) { tune_mood = 1; tune_branch = 0x2e; bad_mood = 0xc8; }
    else if (tune_mood == 17) { tune_mood = 2; tune_branch = 0x2f; threat_mood = 0xc8; }
    else if (tune_mood == 18) { tune_mood = 2; tune_branch = 0x30; threat_mood = 0xc8; }
    else if (tune_mood == 19) { tune_mood = 2; tune_branch = 0x31; threat_mood = 0xc8; }
    else if (tune_mood == 20) { tune_mood = 3; tune_branch = 0x32; emergency_mood = 0xc8; }
    else if (tune_mood == 21) { tune_mood = 3; tune_branch = 0x33; emergency_mood = 0xc8; }
    else if (tune_mood == 22) { tune_mood = 3; tune_branch = 0x34; emergency_mood = 0xc8; }
    else if (tune_mood == 23) { tune_mood = 3; tune_branch = 0x35; emergency_mood = 0xc8; }
    else if (tune_mood == 0) { tune_branch = rand128 & 7; if (tune_branch > 6) tune_branch = 6; }
    else if (tune_mood == 1) { tune_branch = (rand128 & 7) + 0xa; if (tune_branch > 0x10) tune_branch = 0x10; }
    else if (tune_mood == 2) { tune_branch = (rand128 & 7) + 0x14; if (tune_branch > 0x1a) tune_branch = 0x1a; }
    else if (tune_mood == 3) { tune_branch = (rand128 & 7) + 0x1e; if (tune_branch > 0x24) tune_branch = 0x24; }
    else { tune_mood = 0; tune_branch = 0; }
    if (bad_mood != 0)       tune_mood = 1;
    if (threat_mood != 0)    tune_mood = 2;
    if (emergency_mood != 0) tune_mood = 3;

    if (((bad_mood == 0) && (threat_mood == 0)) && (emergency_mood == 0)) {
        if (last_city_mood == 3)      tune_mood = 2;
        else if (last_city_mood == 2) tune_mood = 1;
        else                          tune_mood = bad_mood;
    }
    last_city_mood = tune_mood;
}

// FUNCTION: C2 0x12751
// WIN: 0x0040266b
// Lines 510–532
//
// Battle-tune branch selector.  Moods 1..5 delegate to
// choose_odd_tune (paired branch markers at 0xe / 0x16 / 0x1e / 0x26
// / 0x2e); moods 6..18 select fixed branch indices 0..13; everything
// else uses a random branch (rand128 + 0xe) & 7.  Caches the chosen
// mood in last_battle_mood for get_old_mood.
void get_battle_mood(void)
{
    if      (tune_mood == 1)  choose_odd_tune(0xe);
    else if (tune_mood == 2)  choose_odd_tune(0x16);
    else if (tune_mood == 3)  choose_odd_tune(0x1e);
    else if (tune_mood == 4)  choose_odd_tune(0x26);
    else if (tune_mood == 5)  choose_odd_tune(0x2e);
    else if (tune_mood == 6)  tune_branch = 0;
    else if (tune_mood == 7)  tune_branch = 1;
    else if (tune_mood == 8)  tune_branch = 2;
    else if (tune_mood == 9)  tune_branch = 3;
    else if (tune_mood == 10) tune_branch = 4;
    else if (tune_mood == 11) tune_branch = 5;
    else if (tune_mood == 12) tune_branch = 6;
    else if (tune_mood == 13) tune_branch = 7;
    else if (tune_mood == 14) tune_branch = 9;
    else if (tune_mood == 15) tune_branch = 10;
    else if (tune_mood == 16) tune_branch = 11;
    else if (tune_mood == 17) tune_branch = 12;
    else if (tune_mood == 18) tune_branch = 13;
    else                      tune_branch = (rand128 + 0xe) & 7;
    last_battle_mood = tune_mood;
}

// FUNCTION: C2 0x128AD
// WIN: 0x00402888
// Lines 534–546
//
// Branch-callback helper invoked when a battle tune reaches
// an "odd-tune" marker.  Toggles the `odd_battle_tune` flag
// and either picks a randomised branch index (`x + (rand128
// & 6)`) on the *first* visit, or just bumps the existing
// branch by 1 on the *second* visit, alternating between the
// two halves of a paired tune.
void choose_odd_tune(int x)
{
    if (odd_battle_tune) {
        tune_branch = x + (rand128 & 6);
        odd_battle_tune = 0;
    } else {
        tune_branch += 1;
        odd_battle_tune = 1;
    }
}

// FUNCTION: C2 0x128EA
// WIN: 0x004028cf
// Lines 548–552
//
// Periodic mood-cooldown tick: decrements each of the three
// transient anger counters that bias music selection if non-
// zero, leaving the long-term `tune_mood` untouched.
void sooth_mood(void)
{
    if (emergency_mood) emergency_mood -= 1;
    if (threat_mood)    threat_mood    -= 1;
    if (bad_mood)       bad_mood       -= 1;
}

// FUNCTION: C2 0x12932
// WIN: 0x00402913
// Lines 557–562
//
// Seed the 10 sample-slot LRU counters with their own index (so
// slot 9 will be the oldest and recycled first) and reset the
// current-slot cursor.
void init_ss_entires(void)
{
    int i;
    for (i = 0; i < 10; i++) ss_entries[i].hits = i;
    sslot = 0;
}

// FUNCTION: C2 0x12953
// WIN: 0x00402959
// Lines 564–576
//
// LRU sample-slot allocator.  Each entry of `ss_entries`
// (10 × 20 bytes = `int count` + `char name[16]`) gets its
// hit-count bumped on every miss; the slot with the highest
// count is the *least* recently used and gets recycled with
// the new file name.  Ties go to the lowest index thanks to
// the strict `>` comparison.
//
// Layout: ss_entries[i*5]   = count (int)
//         ss_entries[i*5+1] = first int of name  (16-byte char field)
//
void get_new_sslot(char *fname)
{
    int max_c = 0;
    int best  = 0;
    int i;
    for (i = 0; i < 10; i++) {
        ++ss_entries[i].hits;
        if (max_c <= ss_entries[i].hits) {
            best  = i;
            max_c = ss_entries[i].hits;
        }
    }
    sslot = best;
    ss_entries[best].hits = 0;
    strcpy(ss_entries[best].name, fname);
}

// FUNCTION: C2 0x129B1
// WIN: 0x00402a06
// Lines 579–583
//
// Mark a sample slot as unused: bias its LRU counter to a
// huge value (1000, way above any real ply count) so it'll
// be the next one chosen by `get_new_sslot`, and overwrite
// its name field with the placeholder "unused.wav".
void free_up_sslot(int slot)
{
    ss_entries[slot].hits = 1000;
    strcpy(ss_entries[slot].name, "unused.wav");
}

// FUNCTION: C2 0x129DB
// WIN: 0x00402a41
// Lines 586–597
//
// Linear search of the 10 sample slots for one already
// holding `fname`.  On a hit, resets that slot's LRU
// counter to 0 (most recently used), updates `sslot`, and
// returns 1.  On a miss, returns 0 leaving sslot/entries
// untouched.
int check_old_sslots(char *fname)
{
    int i;
    for (i = 0; i < 10; i++) {
        if (strcmp(ss_entries[i].name, fname) == 0) {
            ss_entries[i].hits = 0;
            sslot = i;
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x12A25
// WIN: 0x00402abd
// Lines 601–608
//
// Hand the AIL digital driver pointer to the Smacker video library
// so movie audio mixes through the same DAC as game SFX.  Idempotent
// -- bails early with 1 if already linked.
int link_to_smacker(void)
{
    int o;
    if (smacker_open) return 1;
    o = smacker_open;
    SetSmackAILDigDriver(dig, o);
    smacker_open = 1;
    return 1;
}

// FUNCTION: C2 0x12A5C
// WIN: 0x00402b01
// Lines 611–611
//
// True when the AIL digital subsystem is running.
int allow_samples(void)
{
    return samples_running != 0;
}

// FUNCTION: C2 0x12A6C
// WIN: 0x00402b2a
// Lines 617–620
//
// Flag ambient slot `idx` for playback on the next play_ambient_fx
// tick.
void set_this_ambient(int idx)
{
    ambient_list[idx].active = 1;
}

// FUNCTION: C2 0x12A77
// WIN: 0x00402b4a
// Lines 622–625
//
// Floor an ambient slot's delay_counter at `min` (bias toward firing
// sooner; leaves the slot alone if its counter already exceeds min).
void set_ambient_minimum(int idx, int min)
{
    if (ambient_list[idx].delay_counter < min)
        ambient_list[idx].delay_counter = min;
}

// FUNCTION: C2 0x12A8F
// WIN: 0x00402b8b
// Lines 627–665
//
// City building-kind -> ambient-slot dispatcher: a dense if/else
// chain mapping every building tile range (0x78..0xff) to one of the
// 24 ambient slots and marking it active.  The 0xfa..0xfb range
// (well / aqueduct overflow) picks between slots 0x14 / 0x15 based
// on the cell's upper-nibble building field; ranges that don't map
// to a slot (< 0x78 / 0x7c..0x82 / 0xa2..0xae / 0xbf..0xcb /
// 0xf5..0xfa) are no-ops.
void set_city_ambient(int kind)
{
    int slot;
    unsigned char temp;

    if (kind < 0x78) return;
    if      (kind < 0x7c) slot = 1;
    else if (kind < 0x82) slot = 0xe;
    else if (kind < 0xa2) return;
    else if (kind < 0xae) slot = 0x12;
    else if (kind < 0xbc) slot = 7;
    else if (kind < 0xbe) slot = 0x11;
    else if (kind < 0xbf) slot = 0x10;
    else if (kind < 0xcb) return;
    else if (kind < 0xd7) slot = 0x11;
    else if (kind < 0xdb) slot = 0xf;
    else if (kind < 0xdf) slot = 8;
    else if (kind < 0xe3) slot = 4;
    else if (kind < 0xe4) slot = 0x17;
    else if (kind < 0xe5) slot = 3;
    else if (kind < 0xe7) slot = 0x13;
    else if (kind < 0xe9) slot = 5;
    else if (kind < 0xf3) slot = 2;
    else if (kind < 0xf4) slot = 0xa;
    else if (kind < 0xf5) slot = 0xb;
    else if (kind < 0xfa) return;
    else if (kind < 0xfb) {
        temp = (*(struct city_cell *)((unsigned char *)city_map + (pm_shown_ptr))).building & 0xf0;
        temp >>= 4;
        slot = temp;
        if (slot > 3) slot = 0x14;
        else          slot = 0x15;
    } else if (kind < 0xfc) slot = 0x16;
    else if (kind < 0xfe) slot = 0xd;
    else slot = 0xc;

    ambient_list[slot].active = 1;
}

// FUNCTION: C2 0x12C22
// WIN: 0x00402e37
// Lines 668–684
//
// Province-event → ambient-slot dispatcher.  Like
// set_battle_fight_fx but with a denser if/else chain mapping
// province event ids 0xd2..0xeb to slots 0xc/5/4/0xb/2/6/7/3.
// Out-of-range events early-return.  Only sets the active
// byte — no priority bump.
void set_prov_ambient(int event)
{
    if (event <  0xd2) return;
    if (event <  0xd3) return;
    if      (event <  0xd4) event = 0xc;
    else if (event <  0xd5) event = 5;
    else if (event <  0xdc) event = 4;
    else if (event <  0xe0) event = 0xb;
    else if (event <  0xe4) event = 2;
    else if (event <  0xe8) event = 6;
    else if (event <  0xec) event = 7;
    else                    event = 3;

    ambient_list[event].active = 1;
}

// FUNCTION: C2 0x12CAD
// WIN: 0x00402f45
// Lines 686–697
//
// Schedule a battle-death sound effect for the given unit-type id
// (0-17): picks one of 4 sample-slot indices via an if/else chain,
// activates that slot, and pins its delay_counter to 0xC8.
void set_battle_death_fx(int unit_type)
{
    int idx = 0;

    if      (unit_type <=  3) idx = 0xc;
    else if (unit_type <= 14) idx = 0xd;
    else if (unit_type <= 15) idx = 0xe;
    else if (unit_type <= 17) idx = 0xd;

    ambient_list[idx].active = 1;
    ambient_list[idx].delay_counter = 0xc8;
}

// FUNCTION: C2 0x12CEC
// WIN: 0x00402fd9
// Lines 699–714
//
// Schedule a unit-march sound for the given unit-type id.
// Picks one of two sample slots (15 or 16) by if/else-if
// chain, marks it active in ambient_list[], and updates
// the global ambient minimum to the appropriate sample id
// (0xC7 if marching_fx hadn't been bumped yet, 0xB9 once it
// has).  Finally sets marching_fx = 10 (frame countdown).
void set_battle_march_fx(int unit_type)
{
    int idx = 0;
    int min;

    if      (unit_type <=  3) idx = 15;
    else if (unit_type <= 10) idx = 15;
    else if (unit_type <= 15) idx = 16;
    else if (unit_type <= 17) idx = 15;

    ambient_list[idx].active = 1;
    if (marching_fx == 0) min = 0xc7;
    else                  min = 0xb9;
    set_ambient_minimum(idx, min);
    marching_fx = 10;
}

// FUNCTION: C2 0x12D41
// WIN: 0x00403094
// Lines 716–732
//
// Battle event-id -> ambient-slot dispatcher.  Activates the slot
// and bumps delay_counter by 0x19 (priority boost).
void set_battle_fight_fx(int event)
{
    int slot = 0;

    if      (event <= 2)    slot = 8;
    else if (event <= 3)    slot = 9;
    else if (event <= 5)    slot = 8;
    else if (event <= 6)    slot = 0xa;
    else if (event <= 7)    slot = 7;
    else if (event <= 8)    slot = 0xa;
    else if (event <= 0xa)  slot = 9;
    else if (event <= 0xd)  slot = 8;
    else if (event <= 0x11) slot = 9;

    ambient_list[slot].active = 1;
    ambient_list[slot].delay_counter += 0x19;
}

// FUNCTION: C2 0x12D9F
// WIN: 0x004031ac
// Lines 734–746
//
// Event-id → ambient-slot dispatcher: maps an event/missile
// type to one of the canonical ambient slots (3, 6, 0xb, or
// the default 0), then marks that slot active in
// ambient_list[] and bumps its priority counter by 0x19.
void set_missile_fight_fx(int event)
{
    int slot = 0;

    if      (event <= 3)    slot = 6;
    else if (event <= 9)    slot = 0xb;
    else if (event <= 0xa)  slot = 6;
    else if (event <= 0x10) slot = 3;
    else if (event <= 0x11) slot = 0xb;

    ambient_list[slot].active = 1;
    ambient_list[slot].delay_counter += 0x19;
}

// FUNCTION: C2 0x12DE2
// WIN: 0x0040326c
// Lines 748–760
//
// Missile launch SFX dispatcher: maps missile_type to one of three
// ambient slots (0 / 1 / 4), activates it, and bumps the slot's
// delay_counter by 0x28 (priority boost).
void set_missile_fire_fx(int missile_type)
{
    int idx = 0;

    if      (missile_type <=  3) idx = 4;
    else if (missile_type <=  9) idx = 0;
    else if (missile_type <= 10) idx = 4;
    else if (missile_type <= 16) idx = 1;
    else if (missile_type <= 17) idx = 0;

    ambient_list[idx].active = 1;
    ambient_list[idx].delay_counter += 0x28;
}

// FUNCTION: C2 0x12E1E
// WIN: 0x0040332c
// Lines 762–784
//
// Service pending ambient SFX slots.  Slots 1..24 have a 70-byte
// record: active flag, rotating filename index, filename count,
// priority/base volume byte, a short delay/priority counter, then up
// to four 16-byte sample names at +6/+0x16/+0x26/+0x36.  When a slot
// is active its counter is bumped; once it reaches 200, rand128 seeds
// the next delay and the current filename is queued via set_sound().
void play_ambient_fx(void)
{
    int i;

    if (marching_fx != 0) marching_fx--;
    for (i = 1; i < 0x19; i++) {
        if (ambient_list[i].active == 0) continue;
        ambient_list[i].active = 0;
        (ambient_list[i].delay_counter)++;
        if (ambient_list[i].delay_counter < 0xc8) continue;
        ambient_list[i].delay_counter = rand128;
        if (c2inf.ambients_on == 0) break;
        if (ambient_list[i].name_idx == 0) {
            set_sound(ambient_list[i].names[0], ambient_list[i].volume);
        } else if (ambient_list[i].name_idx == 1) {
            set_sound(ambient_list[i].names[1], ambient_list[i].volume);
        } else if (ambient_list[i].name_idx == 2) {
            set_sound(ambient_list[i].names[2], ambient_list[i].volume);
        } else if (ambient_list[i].name_idx == 3) {
            set_sound(ambient_list[i].names[3], ambient_list[i].volume);
        }
        ambient_list[i].name_idx++;
        if (ambient_list[i].name_idx >= ambient_list[i].name_count) {
            ambient_list[i].name_idx = 0;
        }
    }
}

// FUNCTION: C2 0x12F2A
// WIN: 0x004035c9
// Lines 786–854
//
// Populate the 24 ambient slots with the city-screen sample bank --
// gardens, circus, bath house, colliseum, forum, fountain, schools,
// market, plaza, well, reservoir, aqueduct, temple, theatre, business
// districts, fire siren, ...  Each slot gets a stagger delay (i * 8),
// a default volume (1), and one or more 16-byte sample file names.
//
// WARNING: every "*.wav" literal below is a REAL truncated DOS 8.3
// filename baked into PS.EXE (reserv.wav, colisum5.wav, bathhs.wav,
// fountn.wav, grammat2.wav, marketh.wav, ...).  They are NOT typos --
// do NOT "correct" them.  Expanding one (e.g. reserv->reserve) changes
// the emitted string data AND the code that references it, breaking
// byte-exactness here and, via the start_sequences tail-merge, in
// neighbouring functions too.
void init_city_ambients(void)
{
    int i;

    for (i = 0; i < 0x19; i++) {
        ambient_list[i].active = 0;
        ambient_list[i].delay_counter = (i * 8);
        ambient_list[i].name_idx = 0;
        ambient_list[i].volume = 1;
    }
    ambient_list[1].name_count = 3;
    strcpy(ambient_list[1].names[0], "gardenb.wav");
    strcpy(ambient_list[1].names[1], "gardenc.wav");
    strcpy(ambient_list[1].names[2], "gardend.wav");
    ambient_list[2].name_count = 1;
    strcpy(ambient_list[2].names[0], "circus1.wav");
    ambient_list[3].name_count = 1;
    strcpy(ambient_list[3].names[0], "barrack2.wav");
    ambient_list[4].name_count = 1;
    ambient_list[4].volume = 1;
    strcpy(ambient_list[4].names[0], "bathhs.wav");
    ambient_list[5].name_count = 2;
    strcpy(ambient_list[5].names[0], "colisum5.wav");
    strcpy(ambient_list[5].names[1], "colisum6.wav");
    ambient_list[6].name_count = 1;
    strcpy(ambient_list[6].names[0], "fire.wav");
    ambient_list[7].name_count = 1;
    strcpy(ambient_list[7].names[0], "forum.wav");
    ambient_list[8].name_count = 1;
    ambient_list[8].volume = 1;
    strcpy(ambient_list[8].names[0], "fountn.wav");
    ambient_list[9].name_count = 1;
    strcpy(ambient_list[9].names[0], "fountnx.wav");
    ambient_list[10].name_count = 1;
    strcpy(ambient_list[10].names[0], "grammat2.wav");
    ambient_list[11].name_count = 1;
    strcpy(ambient_list[11].names[0], "rhetor.wav");
    ambient_list[12].name_count = 1;
    ambient_list[12].volume = 1;
    strcpy(ambient_list[12].names[0], "marketh.wav");
    ambient_list[13].name_count = 1;
    ambient_list[13].volume = 1;
    strcpy(ambient_list[13].names[0], "marketl.wav");
    ambient_list[14].name_count = 1;
    strcpy(ambient_list[14].names[0], "plazab.wav");
    ambient_list[15].name_count = 1;
    ambient_list[15].volume = 1;
    strcpy(ambient_list[15].names[0], "well.wav");
    ambient_list[16].name_count = 1;
    ambient_list[16].volume = 1;
    strcpy(ambient_list[16].names[0], "reserv.wav");
    ambient_list[17].name_count = 1;
    ambient_list[17].volume = 1;
    strcpy(ambient_list[17].names[0], "aquadct.wav");
    ambient_list[18].name_count = 1;
    strcpy(ambient_list[18].names[0], "temple1.wav");
    ambient_list[19].name_count = 1;
    strcpy(ambient_list[19].names[0], "theatre.wav");
    ambient_list[20].name_count = 1;
    ambient_list[20].volume = 1;
    strcpy(ambient_list[20].names[0], "hbiz.wav");
    ambient_list[21].name_count = 1;
    ambient_list[21].volume = 1;
    strcpy(ambient_list[21].names[0], "lbiz.wav");
    ambient_list[22].name_count = 1;
    strcpy(ambient_list[22].names[0], "null.wav");
    ambient_list[23].name_count = 1;
    strcpy(ambient_list[23].names[0], "null.wav");
}

// FUNCTION: C2 0x13186
// WIN: 0x00401384  (unverified)
//
// Empty placeholder.  Reserved label that PS's shared 5-pop epilogue
// jumps to (`pop ebp; ret`).
void sound_error(void)
{
}

// FUNCTION: C2 0x13187
// WIN: 0x00403999
// Lines 857–903
//
// Populate the ambient slots with the province-screen sample bank --
// birds, mining, surf / shore, shipyard, warehouse, quarry, trading,
// march cadences, uprising, farms.
void init_prov_ambients(void)
{
    int i;

    for (i = 0; i < 0x19; i++) {
        ambient_list[i].active = 0;
        ambient_list[i].delay_counter = (i * 8);
        ambient_list[i].name_idx = 0;
        ambient_list[i].volume = 1;
    }
    ambient_list[1].name_count = 4;
    strcpy(ambient_list[1].names[0], "birdsp2.wav");
    strcpy(ambient_list[1].names[1], "birdsp3.wav");
    strcpy(ambient_list[1].names[2], "birdsp4.wav");
    strcpy(ambient_list[1].names[3], "birdsp5.wav");
    ambient_list[2].name_count = 1;
    strcpy(ambient_list[2].names[0], "mining3.wav");
    ambient_list[3].name_count = 4;
    strcpy(ambient_list[3].names[0], "surf1.wav");
    strcpy(ambient_list[3].names[1], "surf2.wav");
    strcpy(ambient_list[3].names[2], "shore1.wav");
    strcpy(ambient_list[3].names[3], "shore2.wav");
    ambient_list[4].name_count = 2;
    strcpy(ambient_list[4].names[0], "shipyrd1.wav");
    strcpy(ambient_list[4].names[1], "shipyrd2.wav");
    ambient_list[5].name_count = 3;
    strcpy(ambient_list[5].names[0], "warehse1.wav");
    strcpy(ambient_list[5].names[1], "warehse2.wav");
    strcpy(ambient_list[5].names[2], "warehse3.wav");
    ambient_list[6].name_count = 1;
    strcpy(ambient_list[6].names[0], "quarry.wav");
    ambient_list[7].name_count = 1;
    strcpy(ambient_list[7].names[0], "trading.wav");
    ambient_list[8].name_count = 1;
    strcpy(ambient_list[8].names[0], "marchb2.wav");
    ambient_list[9].name_count = 1;
    strcpy(ambient_list[9].names[0], "marchr.wav");
    ambient_list[10].name_count = 1;
    strcpy(ambient_list[10].names[0], "uprise.wav");
    ambient_list[11].name_count = 4;
    strcpy(ambient_list[11].names[0], "farm3.wav");
    strcpy(ambient_list[11].names[1], "farm4.wav");
    strcpy(ambient_list[11].names[2], "farm5.wav");
    strcpy(ambient_list[11].names[3], "farm6.wav");
    ambient_list[12].name_count = 1;
    strcpy(ambient_list[12].names[0], "null.wav");
}

// FUNCTION: C2 0x13351
// WIN: 0x00403cab
// Lines 906–961
//
// Populate the ambient slots with the battle-screen sample bank --
// bow/sling launches and hits, melee weapon hits (axe, sword, club,
// spear, knife), death cries, elephant trumpets, advance/cavalry/mob
// march cadences, melee fight loops.
void init_battle_ambients(void)
{
    int i;

    for (i = 0; i < 0x19; i++) {
        ambient_list[i].active = 0;
        ambient_list[i].delay_counter = (i * 8);
        ambient_list[i].name_idx = 0;
        ambient_list[i].volume = 1;
    }
    ambient_list[1].name_count = 2;
    strcpy(ambient_list[1].names[0], "bowlau.wav");
    strcpy(ambient_list[1].names[1], "bowslau.wav");
    ambient_list[3].name_count = 1;
    strcpy(ambient_list[3].names[0], "bowhit.wav");
    ambient_list[4].name_count = 2;
    strcpy(ambient_list[4].names[0], "sling4.wav");
    strcpy(ambient_list[4].names[1], "sling5.wav");
    ambient_list[6].name_count = 1;
    strcpy(ambient_list[6].names[0], "slinght.wav");
    ambient_list[7].name_count = 1;
    strcpy(ambient_list[7].names[0], "axe.wav");
    ambient_list[8].name_count = 1;
    strcpy(ambient_list[8].names[0], "swordht.wav");
    ambient_list[9].name_count = 1;
    strcpy(ambient_list[9].names[0], "clubht.wav");
    ambient_list[10].name_count = 1;
    strcpy(ambient_list[10].names[0], "spearht.wav");
    ambient_list[11].name_count = 1;
    strcpy(ambient_list[11].names[0], "knieht.wav");
    ambient_list[12].name_count = 1;
    strcpy(ambient_list[12].names[0], "deathr.wav");
    ambient_list[13].name_count = 1;
    strcpy(ambient_list[13].names[0], "deathb.wav");
    ambient_list[14].name_count = 1;
    strcpy(ambient_list[14].names[0], "elephant.wav");
    ambient_list[15].name_count = 2;
    ambient_list[15].volume = 3;
    strcpy(ambient_list[15].names[0], "soldadv.wav");
    strcpy(ambient_list[15].names[1], "armadv.wav");
    ambient_list[16].name_count = 2;
    ambient_list[16].volume = 2;
    strcpy(ambient_list[16].names[0], "singcav.wav");
    strcpy(ambient_list[16].names[1], "armcav.wav");
    ambient_list[17].name_count = 1;
    ambient_list[17].volume = 1;
    strcpy(ambient_list[17].names[0], "mobadv.wav");
    ambient_list[18].name_count = 1;
    ambient_list[18].volume = 1;
    strcpy(ambient_list[18].names[0], "mobcav2.wav");
    ambient_list[19].name_count = 2;
    ambient_list[19].volume = 3;
    strcpy(ambient_list[19].names[0], "meleeam.wav");
    strcpy(ambient_list[19].names[1], "melee2a.wav");
}


// FUNCTION: C2 0x13546
// WIN: 0x00403fd7
// Lines 964–975
//
// Reserve `n * 20000` bytes for the per-slot sample buffer (each slot
// holds a 20 000-byte raw PCM clip).  No-op when the audio system
// isn't running or the user disabled samples; returns 0 only when
// malloc fails so the caller can flag init_err = 4.
int init_sample_buffer(int n)
{
    sample_buffer = 0;
    if (samples_running != 0 && c2inf.samples_on != 0) {
        sample_buffer = malloc(n * 20000);
        if (sample_buffer == 0) return 0;
    }
    return 1;
}

// FUNCTION: C2 0x1358A
// Lines 977–984
//
// Release the sample buffer if it was allocated; `n` is unused
// (legacy signature kept symmetric with init_sample_buffer).
void free_sample_buffer(int n)
{
    if (sample_buffer != 0) free(sample_buffer);
}

// FUNCTION: C2 0x1359E
// WIN: 0x0040408f  (unverified)
// Lines 988–988
//
// No-op stub kept for symmetry with init_sample_buffer.  Always 1.
int init_tune_buffer(void)
{
    return 1;
}

// FUNCTION: C2 0x135A3
// WIN: 0x00401384  (unverified)
//
// Empty placeholder (tune_buffer is a static global, never freed).
void free_tune_buffer(void)
{
}
