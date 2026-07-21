#ifndef PCSOUND_H
#define PCSOUND_H

#include "c2_bugfixes.h"

struct sample_slot_rec {
    int hits;
    char name[16];
};

struct ambient_rec {
    unsigned char active;
    unsigned char name_idx;
    unsigned char name_count;
    unsigned char volume;
    short delay_counter;
    char names[4][16];
};

struct speech_file_rec {
    char name[8];
};

struct smk_handle;

/* First declarations of pcsound.c storage.  Watcom emits BSS by 25-entry
 * symbol-table pages, so these header positions are part of the binary shape.
 * The order is recovered from PS.EXE's per-size, ascending-name-hash runs. */
extern int db_recommended_buffer_size;
extern int db_buffer_size;
extern int S_mdi[2];
extern int S_dig[6];
extern int action_sound;

extern int ds;
extern int tune1;
extern int dig;
extern int ms;
extern int mdi;

/* The declarations between pcsound's two storage runs occupy the rest of the
 * original 25-entry symbol page.  They are all members of the same sound /
 * movie interface rather than anonymous padding. */
extern int city_tune_playing;
extern struct speech_file_rec speech_files[104];
extern char *speech_filaname;
extern int vgawintab[2];
extern int smk_ref_hi;
extern int smack_frame;
extern int smk_height;
extern int smack_from_cd;
extern char *smack_filename;
extern int smksumy[15];
extern int smacker_on;
extern struct smk_handle *smk;
extern int smk_ref_wi;
extern int fss;
extern int didaninit;
extern int *SmackAILDigDriver;
extern int setbyprog;
extern int count;
extern int sndinit[5];
extern int tune_branch;

extern char negative_buffer[624];
extern unsigned char *db_buf[2];
extern struct sample_slot_rec ss_entries[10];
extern int next_sequence;
extern int smacker_open;
extern int sequences_running;
extern int tune2;
extern int dig_status;
extern char positive_buffer[532];
extern int samples_running;
#if defined(PLATFORM_PORTABLE) && C2_FIX_LARGE_XMI_ASSETS
#define C2_TUNE_BUFFER_SIZE 65536
#else
#define C2_TUNE_BUFFER_SIZE 27500
#endif
extern unsigned char tune_buffer[C2_TUNE_BUFFER_SIZE];
extern int db_handle;
extern int db_playing;
extern char *db_file;
extern char *sample_buffer;
extern int mdi_status;
extern int next_sample;
extern int sslot;
extern struct ambient_rec ambient_list[25];

#endif /* PCSOUND_H */
