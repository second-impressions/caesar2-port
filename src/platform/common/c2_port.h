#ifndef PORT_H
#define PORT_H

#include <stddef.h>

#include "c2_target.h"

#define C2_SCREEN_WIDTH 640
#define C2_SCREEN_HEIGHT 480
#define C2_SCREEN_PIXELS (C2_SCREEN_WIDTH * C2_SCREEN_HEIGHT)
#define C2_PALETTE_BYTES (256 * 3)
#define C2_DIRECTORY_MAX_ENTRIES 100

enum c2_port_scroll_key {
    PORT_SCROLL_LEFT = 1u << 0,
    PORT_SCROLL_RIGHT = 1u << 1,
    PORT_SCROLL_UP = 1u << 2,
    PORT_SCROLL_DOWN = 1u << 3
};

int c2_port_compat_init(void);
void c2_port_compat_shutdown(void);
void c2_port_timing_reset(void);
int c2_port_wait_dos_clock_tick(void);
void c2_port_wait_for_frame(void);
void c2_port_wait_vblank(void);
int c2_port_save_screenshot(const char *filename);
int check_user_file_exists(const char *filename);
void *c2_port_load_asset(const char *filename, size_t *size_out);
unsigned int c2_port_scroll_keys(void);
#if PORT_FIX_PAUSED_MUSIC_VARIETY
int c2_port_paused_music_branch(int base, int count,
                                int current_branch, int branch_count);
#endif
#if PORT_FEAT_RECORDED_MUSIC
/* Caesar II has two soundtracks, by different composers: the 1995 DOS
 * music (Jeremy A. Bell and Jason P. Rinaldi), sequenced through the sound
 * card's synthesizer and branching with the city's mood, and the 1996
 * Windows music (Keith Zizza), recorded from hardware synthesizers as
 * seven fixed pieces. "xmidi"/"recorded" say how each is
 * stored; the player sees the version each was written for. */
enum c2_port_music_source {
    C2_PORT_MUSIC_XMIDI = 0,     /* the 1995 DOS music */
    C2_PORT_MUSIC_RECORDED = 1   /* the 1996 Windows recordings */
};
int c2_port_music_recorded_available(void);
int c2_port_music_xmidi_available(void);
void c2_port_music_set_preference(enum c2_port_music_source preference);
enum c2_port_music_source c2_port_music_preference(void);
enum c2_port_music_source c2_port_music_source(void);   /* what plays */
const char *c2_port_music_source_name(enum c2_port_music_source source);
int c2_port_music_source_parse(const char *name, enum c2_port_music_source *out);
/* pcsound.c hooks and the AIL layer's forwarding */
int c2_port_recorded_music_play(const char *filename, int loop_count);
void c2_port_recorded_music_stop(int end_secondary);
void c2_port_recorded_music_pump(void);
void c2_port_recorded_music_set_volume(int slot, int volume, int fade_ms);
void c2_port_recorded_music_shutdown(void);
#endif
#if PORT_FEAT_STICKY_DROPDOWNS
void c2_port_selection_begin(int mouse_x, int mouse_y);
void c2_port_selection_end(void);
int c2_port_selection_consume_release(int mouse_x, int mouse_y);
#endif
void mouserange(int xmin, int ymin, int xmax, int ymax);

#endif /* PORT_H */
