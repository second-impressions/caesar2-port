#pragma description Caesar II CAESAR2.INF (options / preferences block)
#pragma endian little

// ---------------------------------------------------------------------------
// Caesar II CAESAR2.INF -- the persistent options/preferences block.  It is
// just the 64-byte `c2inf` struct written/read verbatim (no header):
//   save_inf:  write(fd, &c2inf, 0x40);
//   load_inf:  read (fd, &c2inf, 0x40);   then test_inf_settings()
// Validity is checked by the magic starting_year == 0x7d5 (2005); a mismatch
// triggers basic_inf_settings() defaults.  Struct is byte-packed (Watcom -zp1)
// so the two level ints at +0x0E/+0x12 are UNALIGNED.
//
// Field-for-field from struct c2inf_rec (entities.h).
// ---------------------------------------------------------------------------

struct C2Inf {
    char cd_letter;          // +0x00 CD-ROM drive letter (preserved across load_inf)
    char drive_init;         // +0x01 flag: CD path resolved (preserved across load_inf)
    u8   _unk02 [[color("707070"), comment("unused")]];  // +0x02
    char speech_on;          // +0x03 bool: Latin speech enabled
    s32  game_speed;         // +0x04 default 100
    s32  scroll_speed;       // +0x08 default 100
    char samples_on;         // +0x0C bool
    char tunes_on;           // +0x0D bool
    s32  samples_level;      // +0x0E 0..100  (UNALIGNED)
    s32  tunes_level;        // +0x12 0..100  (UNALIGNED)
    s16  starting_year;      // +0x16 MAGIC = 0x7d5 (2005); else -> defaults
    char paused;             // +0x18 bool
    char anims_on;           // +0x19 bool
    char player_name[26];    // +0x1A NUL-terminated ("Octavian")
    s8   skill_level;        // +0x34 signed; career skill
    char peace_mode;         // +0x35 bool: 1 = no random events
    u8   _unused36 [[color("707070"), comment("write-only, never read (dead in both builds)")]]; // +0x36
    char config37;           // +0x37 config byte (load_inf reads)
    u8   _unused38 [[color("707070"), comment("write-only, never read (dead in both builds)")]]; // +0x38
    char yearend_on;         // +0x39 bool
    char ambients_on;        // +0x3A bool
    char autosave_on;        // +0x3B bool
    s32  max_samples;        // +0x3C default 4 (concurrent voices)
};                           // 0x40 = 64 bytes

C2Inf file @ 0x00;
