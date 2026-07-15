# Caesar II `CAESAR2.INF` Format

> ImHex pattern: [`tools/imhex/caesar2_inf.hexpat`](../tools/imhex/caesar2_inf.hexpat).

## Overview

`CAESAR2.INF` is the game's persistent **options / preferences** file. It has no header
and no structure of its own — it is simply the 64-byte in-memory `c2inf` struct dumped to
disk verbatim:

```c
void save_inf(void) { ... write(fd, &c2inf, 0x40); ... }   // loadsave.c
void load_inf(void) { ... read (fd, &c2inf, 0x40); test_inf_settings(); ... }
```

On load, `test_inf_settings` validates the file by checking the **magic**
`starting_year == 0x7d5` (2005). If it doesn't match, `basic_inf_settings` rewrites the
defaults. Two runtime-seeded bytes (`cd_letter`, `drive_init`) are preserved across
`load_inf` rather than taken from disk.

The struct is **byte-packed** (Watcom `-zp1`), so the two `int` volume levels at `+0x0E`
and `+0x12` are unaligned.

## Layout (`struct c2inf_rec`, 64 bytes)

```
Offset  Size  Type  Field           Notes
------  ----  ----  -----           -----
+0x00   1     char  cd_letter       CD drive letter; preserved across load_inf
+0x01   1     char  drive_init      flag: CD path resolved; preserved across load_inf
+0x02   1     char  _unk02          unused
+0x03   1     char  speech_on       bool: Latin speech
+0x04   4     int   game_speed      default 100
+0x08   4     int   scroll_speed    default 100
+0x0C   1     char  samples_on      bool
+0x0D   1     char  tunes_on        bool
+0x0E   4     int   samples_level   0..100  (UNALIGNED)
+0x12   4     int   tunes_level     0..100  (UNALIGNED)
+0x16   2     short starting_year   MAGIC = 0x7d5 (2005); validity check
+0x18   1     char  paused          bool
+0x19   1     char  anims_on        bool
+0x1A   26    char  player_name[26] NUL-terminated ("Octavian")
+0x34   1     s8    skill_level     signed; career skill
+0x35   1     char  peace_mode      bool: 1 = no random events
+0x36   1     char  _unused36       write-only, never read (dead in DOS + Mac builds)
+0x37   1     char  config37        config byte (read by load_inf)
+0x38   1     char  _unused38       write-only, never read (dead in DOS + Mac builds)
+0x39   1     char  yearend_on      bool
+0x3A   1     char  ambients_on     bool
+0x3B   1     char  autosave_on     bool
+0x3C   4     int   max_samples     default 4 (concurrent voices)
                                    --- struct ends at 0x40 ---
```

The Mac PPC build (same source) has an extra dual-window-mode flag at its `c2inf+0x45`
(`set_window_mode`/`select_window`), a Mac-only UI feature `#ifdef`'d out of the
full-screen DOS build — so the DOS struct genuinely ends at `0x40`.

## Defaults (`basic_inf_settings`)

`starting_year = 0x7d5`, `player_name = "Octavian"`, `game_speed = scroll_speed = 100`,
all the `*_on` toggles = 1, `samples_level = tunes_level = 100`, `max_samples = 4`,
`paused = 0`, `skill_level = 0`, `peace_mode = 1`, `config37 = 1`.
