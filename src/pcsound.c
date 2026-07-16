
#pragma aux _ds "*"
#include "pcsound.h"
#include "c2_data.h"
#include "smacker.h"
#include <fcntl.h>             /* O_BINARY */
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

/* File-local state. */
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

/* Far-pointer startup hooks preserve the register contract expected by Miles. */
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
extern void *malloc(unsigned int size);

// Boot the sound subsystem: clear the playback flags, enable both digital + MIDI in c2inf, install
// AIL, and bring up the sample + sequence drivers.
// FUNCTION: C2 0x11758
// FUNCTION: C2WIN 0x00401000
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

// Tear down the sound subsystem: end both AIL driver halves and shut AIL down.
// FUNCTION: C2 0x117a2
void stop_sounds(void)
{
    stop_samples();
    stop_sequences();
    AIL_shutdown();
}
// Installs the digital sound driver: loads the two click WAVs into the preloaded buffers, installs
// DIG.INI, allocates 6 sample handles, verifies them, and flips `samples_running`. Re-entry is a
// no-op.
// FUNCTION: C2 0x117b8
// FUNCTION: C2WIN 0x00401085
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

// AIL MIDI sequence bootstrap. Installs the MDI driver, allocates two sequence handles, and
// initialises the mood-tracking globals.
// FUNCTION: C2 0x118a2
// FUNCTION: C2WIN 0x00401250
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

// Stop every active digital sample slot. Clears db_playing and ends any S_dig handle currently
// reporting status 4 (PLAYING).
// FUNCTION: C2 0x1197b
// FUNCTION: C2WIN 0x0040138f
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

// Stop every active music sequence. Clears the city tune flag and ends any S_mdi handle currently
// reporting status 4 (PLAYING).
// FUNCTION: C2 0x119e7
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

// Push the user-configured digital-sample volume to AIL, scaled from c2inf.samples_level (0..100)
// to AIL's 0..127 range via totalXpercent. No-op if samples are disabled or the digital driver
// isn't initialised.
// FUNCTION: C2 0x11a53
// FUNCTION: C2WIN 0x0040149b
void set_samples_volume(void)
{
    if (c2inf.samples_on == 0)   return;
    if (samples_running == 0)    return;
    AIL_set_digital_master_volume(dig, totalXpercent(0x7f, c2inf.samples_level));
}

// Push the user-configured music volume to both AIL sequence handles (tune1 and tune2) — scaled
// from c2inf.tunes_level (0..100) to AIL's 0..127 range; fade=0 (instant).
// FUNCTION: C2 0x11a8c
// FUNCTION: C2WIN 0x00401515
void set_sequences_volume(void)
{
    int vol;

    if (c2inf.tunes_on == 0)     return;
    if (sequences_running == 0)  return;
    vol = totalXpercent(0x7f, c2inf.tunes_level);
    AIL_set_sequence_volume(S_mdi[tune1], vol, 0);
    AIL_set_sequence_volume(S_mdi[tune2], vol, 0);
}

// Begin a 1-second fade-in on S_mdi[idx]: snap to 0 then fade up to the user-configured master
// volume. Skipped if music is disabled.
// FUNCTION: C2 0x11ae9
// FUNCTION: C2WIN 0x0040158e
void fade_sequence_in(int idx)
{
    int vol;

    if (c2inf.tunes_on == 0)     return;
    if (sequences_running == 0)  return;
    vol = totalXpercent(0x7f, c2inf.tunes_level);
    AIL_set_sequence_volume(S_mdi[idx],   0, 0);
    AIL_set_sequence_volume(S_mdi[idx], vol, 1000);
}

// Begin a 1-second fade-out on S_mdi[idx] iff music is enabled (c2inf.tunes_on) and the global
// sequences_running flag is set. `AIL_set_sequence_volume(h, target=0, fade_ms=1000)`.
// FUNCTION: C2 0x11b4b
// FUNCTION: C2WIN 0x00401604
void fade_sequences_out(int idx)
{
    if (c2inf.tunes_on == 0)      return;
    if (sequences_running == 0)   return;
    AIL_set_sequence_volume(S_mdi[idx], 0, 1000);
}

// Schedule a digital sample for playback. Each sample slot owns a 20 000-byte (0x4E20) chunk of
// `sample_buffer`; if the same fname has been queued before, ``check_old_sslots`` returns the
// existing slot and we skip the load.
// FUNCTION: C2 0x11b7b
// FUNCTION: C2WIN 0x0040164d
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

// "Priority" variant of set_sound — same flow, but skips the check_for_free_slot gate. Used by
// callers that always want the sample played, displacing the oldest slot if all 10 are busy.
// FUNCTION: C2 0x11c35
// FUNCTION: C2WIN 0x00401734
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

// Allocate a free voice slot and start a one-shot sample. Walks S_dig[0..max_samples) looking for
// a slot in idle (status 2) or paused (status 8) state.
// FUNCTION: C2 0x11ce2
// FUNCTION: C2WIN 0x00401809
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

// Returns nonzero if a sample slot is available.
// FUNCTION: C2 0x11df2
// FUNCTION: C2WIN 0x0040198e
int check_for_free_slot(void)
{
    for (ds = 0; ds < c2inf.max_samples; ds++) {
        dig_status = AIL_sample_status(S_dig[ds]);
        if (dig_status != 4) return 1;
    }
    return 0;
}

// Walk all 4 digital sample slots and end any that report status SMP_PLAYING (4).
// FUNCTION: C2 0x11e3b
void stop_all_sounds(void)
{
    for (ds = 0; ds < 4; ds++) {
        dig_status = AIL_sample_status(S_dig[ds]);
        if (dig_status == 4) AIL_end_sample(S_dig[ds]);
    }
}

#pragma aux _pos_ret3 = "xor edx,edx" "mov eax,3" modify exact [eax edx]

// Cinematic "positive" sting playback. Latches sample slot 4, recycles it if currently active,
// then plays the preloaded `positive_buffer`.
// FUNCTION: C2 0x11e92
// FUNCTION: C2WIN 0x00401a69
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

// Play the negative feedback sample when digital audio is available.
// FUNCTION: C2 0x11f40
// FUNCTION: C2WIN 0x00401b30
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

// Refill one of AIL's double-buffered sample slots from the open db_handle file. buf is an array
// of byte-buffer pointers (one per sample buffer slot); the slot index is the one AIL reports
// ready via AIL_sample_buffer_ready (-1 if none ready, silent no-op).
// FUNCTION: C2 0x11fb9
void serve_sample(int sample_handle, unsigned char **buf, int size)
{
    int slot;
    int n;

    slot = AIL_sample_buffer_ready(sample_handle);
    if (slot == -1) return;
    n = read(db_handle, buf[slot], size);
    AIL_load_sample_buffer(sample_handle, slot, buf[slot], n);
}

// Stage a streaming digital sample ("db" = digital buffer) for double-buffered playback. Bails out
// if the master sample/speech toggles are off, AIL isn't running, another db is already playing,
// the filename is empty, or the file doesn't exist.
// FUNCTION: C2 0x12003
// FUNCTION: C2WIN 0x00401c57
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

// Resume / advance the digital-buffer (db) playback loop. Re-stages a chunk via serve_sample(),
// then if AIL says the previous sample finished (status == 2), closes the file handle and clears
// db_playing.
// FUNCTION: C2 0x1211e
// FUNCTION: C2WIN 0x00401da8
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

// Stop the current db playback. Same early-out triple-guard as continue_db, then ends the AIL
// sample, clears db_playing, closes the file handle, and restores CWD via main_path().
// FUNCTION: C2 0x121a9
// FUNCTION: C2WIN 0x00401e49
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

// Pause/resume the digital "background" sample channel (S_dig[5]). No-op if samples are disabled
// or the db_playing flag is clear.
// FUNCTION: C2 0x121fa
// FUNCTION: C2WIN 0x00401ec1
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

// Load and start an XMI tune unless music or the sequence engine is disabled.
// FUNCTION: C2 0x12279
void play_tune(char *fname, int loops)
{
    if (c2inf.tunes_on == 0) return;
    if (sequences_running == 0) return;
    if (*fname == 0) return;
    if (readfile(fname, tune_buffer, 0x6b6c, 0) == 0) return;
    start_tune(tune_buffer, 0, loops);
}

// Drive a music sequence on MDI slot `slot`. Special-cases: slot == 0 — first end the *other* slot
// (S_mdi[1]) so two sequences don't clash.
// FUNCTION: C2 0x122bc
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

// Halt all currently-playing music sequences. Probes both MDI handles in S_mdi[] and uses the
// asymmetric AIL pair: stop_sequence (pauses) for slot 0, end_sequence (frees) for slot 1.
// FUNCTION: C2 0x1239c
void stop_tune(void)
{
    mdi_status = AIL_sequence_status(S_mdi[0]);
    if (mdi_status == 4) AIL_stop_sequence(S_mdi[0]);
    mdi_status = AIL_sequence_status(S_mdi[1]);
    if (mdi_status == 4) AIL_end_sequence(S_mdi[1]);
}

// Halt only S_mdi[0] — the first half of stop_tune.
// FUNCTION: C2 0x123f5
void stop_tune0(void)
{
    mdi_status = AIL_sequence_status(S_mdi[0]);
    if (mdi_status == 4) AIL_stop_sequence(S_mdi[0]);
}

// Branch-on-mood callback: invoked from the AIL sequencer when a tune reaches a marked branch
// point. Re-evaluates the current mood (battle or city, depending on map mode) and tells the
// sequencer where to branch next via `AIL_branch_index(seq, tune_branch)`.
// FUNCTION: C2 0x12424
void __cdecl mood_modfication(int seq)
{
    tune_mood_hold = 0;
    tune_branch_count++;
    if (map_mode == 2) get_battle_mood();
    else               get_city_mood();
    AIL_branch_index(seq, tune_branch);
}

// Restore the last-known mood for the current map mode (battle uses last_battle_mood, otherwise
// last_city_mood) into the live tune_mood global and return it.
// FUNCTION: C2 0x12461
// FUNCTION: C2WIN 0x004021fd
int get_old_mood(void)
{
    int mood;
    if (map_mode == 2) mood = last_battle_mood;
    else               mood = last_city_mood;
    tune_mood = mood;
    return mood;
}

// Choose the music branch from the current mood, including temporary threat and emergency states.
// FUNCTION: C2 0x1247f
// FUNCTION: C2WIN 0x00402231
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

// Battle-tune branch selector. Moods 1..5 delegate to choose_odd_tune (paired branch markers at
// 0xe / 0x16 / 0x1e / 0x26 / 0x2e); moods 6..18 select fixed branch indices 0..13; everything else
// uses a random branch (rand128 + 0xe) & 7.
// FUNCTION: C2 0x12751
// FUNCTION: C2WIN 0x0040266b
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

// Branch-callback helper invoked when a battle tune reaches an "odd-tune" marker.
// FUNCTION: C2 0x128ad
// FUNCTION: C2WIN 0x00402888
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

// Periodic mood-cooldown tick: decrements each of the three transient anger counters that bias
// music selection if non- zero, leaving the long-term `tune_mood` untouched.
// FUNCTION: C2 0x128ea
// FUNCTION: C2WIN 0x004028cf
void sooth_mood(void)
{
    if (emergency_mood) emergency_mood -= 1;
    if (threat_mood)    threat_mood    -= 1;
    if (bad_mood)       bad_mood       -= 1;
}

// Seed the 10 sample-slot LRU counters with their own index (so slot 9 will be the oldest and
// recycled first) and reset the current-slot cursor.
// FUNCTION: C2 0x12932
// FUNCTION: C2WIN 0x00402913
void init_ss_entires(void)
{
    int i;
    for (i = 0; i < 10; i++) ss_entries[i].hits = i;
    sslot = 0;
}

// Returns new sslot.
// FUNCTION: C2 0x12953
// FUNCTION: C2WIN 0x00402959
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

// Mark a sample slot as unused: bias its LRU counter to a huge value (1000, way above any real ply
// count) so it'll be the next one chosen by `get_new_sslot`, and overwrite its name field with the
// placeholder "unused.wav".
// FUNCTION: C2 0x129b1
// FUNCTION: C2WIN 0x00402a06
void free_up_sslot(int slot)
{
    ss_entries[slot].hits = 1000;
    strcpy(ss_entries[slot].name, "unused.wav");
}

// Linear search of the 10 sample slots for one already holding `fname`. On a hit, resets that
// slot's LRU counter to 0 (most recently used), updates `sslot`, and returns 1.
// FUNCTION: C2 0x129db
// FUNCTION: C2WIN 0x00402a41
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

// Hand the AIL digital driver pointer to the Smacker video library so movie audio mixes through
// the same DAC as game SFX. Idempotent -- bails early with 1 if already linked.
// FUNCTION: C2 0x12a25
// FUNCTION: C2WIN 0x00402abd
int link_to_smacker(void)
{
    int o;
    if (smacker_open) return 1;
    o = smacker_open;
    SetSmackAILDigDriver(dig, o);
    smacker_open = 1;
    return 1;
}

// True when the AIL digital subsystem is running.
// FUNCTION: C2 0x12a5c
// FUNCTION: C2WIN 0x00402b01
int allow_samples(void)
{
    return samples_running != 0;
}

// Flag ambient slot `idx` for playback on the next play_ambient_fx tick.
// FUNCTION: C2 0x12a6c
// FUNCTION: C2WIN 0x00402b2a
void set_this_ambient(int idx)
{
    ambient_list[idx].active = 1;
}

// Floor an ambient slot's delay_counter at `min` (bias toward firing sooner; leaves the slot alone
// if its counter already exceeds min).
// FUNCTION: C2 0x12a77
// FUNCTION: C2WIN 0x00402b4a
void set_ambient_minimum(int idx, int min)
{
    if (ambient_list[idx].delay_counter < min)
        ambient_list[idx].delay_counter = min;
}

// City building-kind -> ambient-slot dispatcher: a dense if/else chain mapping every building tile
// range (0x78..0xff) to one of the 24 ambient slots and marking it active.
// FUNCTION: C2 0x12a8f
// FUNCTION: C2WIN 0x00402b8b
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

// Province-event → ambient-slot dispatcher. Like set_battle_fight_fx but with a denser if/else
// chain mapping province event ids 0xd2..0xeb to slots 0xc/5/4/0xb/2/6/7/3.
// FUNCTION: C2 0x12c22
// FUNCTION: C2WIN 0x00402e37
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

// Schedule a battle-death sound effect for the given unit-type id (0-17): picks one of 4
// sample-slot indices via an if/else chain, activates that slot, and pins its delay_counter to
// 0xC8.
// FUNCTION: C2 0x12cad
// FUNCTION: C2WIN 0x00402f45
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

// Schedule a unit-march sound for the given unit-type id.
// FUNCTION: C2 0x12cec
// FUNCTION: C2WIN 0x00402fd9
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

// Battle event-id -> ambient-slot dispatcher. Activates the slot and bumps delay_counter by 0x19
// (priority boost).
// FUNCTION: C2 0x12d41
// FUNCTION: C2WIN 0x00403094
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

// Event-id → ambient-slot dispatcher: maps an event/missile type to one of the canonical ambient
// slots (3, 6, 0xb, or the default 0), then marks that slot active in ambient_list[] and bumps its
// priority counter by 0x19.
// FUNCTION: C2 0x12d9f
// FUNCTION: C2WIN 0x004031ac
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

// Missile launch SFX dispatcher: maps missile_type to one of three ambient slots (0 / 1 / 4),
// activates it, and bumps the slot's delay_counter by 0x28 (priority boost).
// FUNCTION: C2 0x12de2
// FUNCTION: C2WIN 0x0040326c
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

// Service pending ambient SFX slots. Slots 1..24 have a 70-byte record: active flag, rotating
// filename index, filename count, priority/base volume byte, a short delay/priority counter, then
// up to four 16-byte sample names at +6/+0x16/+0x26/+0x36.
// FUNCTION: C2 0x12e1e
// FUNCTION: C2WIN 0x0040332c
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

// Populate the 24 ambient slots with the city-screen sample bank -- gardens, circus, bath house,
// colliseum, forum, fountain, schools, market, plaza, well, reservoir, aqueduct, temple, theatre,
// business districts, fire siren, ...
// FUNCTION: C2 0x12f2a
// FUNCTION: C2WIN 0x004035c9
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

// Empty sound-error hook.
// FUNCTION: C2 0x13186
void sound_error(void)
{
}

// Populate the ambient slots with the province-screen sample bank -- birds, mining, surf / shore,
// shipyard, warehouse, quarry, trading, march cadences, uprising, farms.
// FUNCTION: C2 0x13187
// FUNCTION: C2WIN 0x00403999
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

// Populate the ambient slots with the battle-screen sample bank -- bow/sling launches and hits,
// melee weapon hits (axe, sword, club, spear, knife), death cries, elephant trumpets,
// advance/cavalry/mob march cadences, melee fight loops.
// FUNCTION: C2 0x13351
// FUNCTION: C2WIN 0x00403cab
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


// Reserve `n * 20000` bytes for the per-slot sample buffer (each slot holds a 20 000-byte raw PCM
// clip). No-op when the audio system isn't running or the user disabled samples; returns 0 only
// when malloc fails so the caller can flag init_err = 4.
// FUNCTION: C2 0x13546
// FUNCTION: C2WIN 0x00403fd7
int init_sample_buffer(int n)
{
    sample_buffer = 0;
    if (samples_running != 0 && c2inf.samples_on != 0) {
        sample_buffer = malloc(n * 20000);
        if (sample_buffer == 0) return 0;
    }
    return 1;
}

// Release the sample buffer if it was allocated; `n` is unused (legacy signature kept symmetric
// with init_sample_buffer).
// FUNCTION: C2 0x1358a
void free_sample_buffer(int n)
{
    if (sample_buffer != 0) free(sample_buffer);
}

// No-op stub kept for symmetry with init_sample_buffer. Always 1.
// FUNCTION: C2 0x1359e
// FUNCTION: C2WIN 0x0040408f
int init_tune_buffer(void)
{
    return 1;
}

// Empty placeholder (tune_buffer is a static global, never freed).
// FUNCTION: C2 0x135a3
void free_tune_buffer(void)
{
}
