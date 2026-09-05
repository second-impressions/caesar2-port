/*
 * XMIDI sequencer with Miles Sound System (AIL 3.x) semantics.
 *
 * This reproduces the XMIDI player linked into Caesar II's PS.EXE
 * (XMI_serve, XMI_send_channel_voice_message, AIL_branch_index and friends):
 * a 120 Hz service tick, the 32-entry note-duration queue, the four-deep
 * for-loop stack, numbered RBRN branches, callback triggers, the controller
 * log used to refresh a resumed sequence, and the volume model in which a
 * sequence volume scales controller 7 on its way to the driver.
 *
 * The sequencer is independent of the synthesizer: it emits plain MIDI
 * channel-voice messages through a callback. xmi_player couples it with the
 * Miles OPL3 driver and a sample clock for the common case.
 */
#ifndef XMIDI_XMIDI_H
#define XMIDI_XMIDI_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define XMI_SERVICE_RATE 120       /* MDI_SERVICE_RATE preference */
#define XMI_DEFAULT_VOLUME 127     /* MDI_DEFAULT_VOLUME preference */
#define XMI_DEFAULT_BEND_RANGE 2   /* MDI_DEFAULT_BEND_RANGE preference */

/* Sequence status values, as returned by AIL_sequence_status. */
#define XMI_SEQ_FREE 1
#define XMI_SEQ_DONE 2
#define XMI_SEQ_PLAYING 4
#define XMI_SEQ_STOPPED 8

struct xmi_driver;
struct xmi_sequence;

typedef void (*xmi_midi_fn)(void *user, unsigned status, unsigned data1,
                            unsigned data2);
typedef void (*xmi_trigger_fn)(void *user, struct xmi_sequence *seq,
                               int channel, int value);
typedef void (*xmi_sequence_fn)(void *user, struct xmi_sequence *seq);

/* ---- File layout ------------------------------------------------------- */

struct xmi_form {
    const unsigned char *form;  /* FORM XMID chunk header */
    const unsigned char *timb;  /* TIMB chunk header or NULL */
    const unsigned char *rbrn;  /* RBRN chunk header or NULL */
    const unsigned char *evnt;  /* EVNT chunk header or NULL */
    size_t evnt_size;           /* EVNT payload length */
};

/* Total size of an XMIDI image (FORM XDIR + CAT, or a bare FORM XMID) that
 * starts at data, or 0 when the header is not an XMIDI file or exceeds cap. */
size_t xmi_image_size(const void *data, size_t cap);

/* Locate the index-th FORM XMID sequence and its chunks. Returns 0 when the
 * image is not XMIDI or the sequence does not exist. */
int xmi_find_form(const void *data, size_t size, int index,
                  struct xmi_form *out);

/* RBRN introspection: number of branch entries and the id/offset of one. */
int xmi_form_branch_count(const struct xmi_form *form);
int xmi_form_branch(const struct xmi_form *form, int index, unsigned *id,
                    size_t *offset);
/* TIMB introspection: number of entries and the patch/bank of one. */
int xmi_form_timbre_count(const struct xmi_form *form);
int xmi_form_timbre(const struct xmi_form *form, int index, unsigned *patch,
                    unsigned *bank);

/* ---- Driver: the shared MDI driver state ------------------------------- */

struct xmi_driver *xmi_driver_create(xmi_midi_fn midi, void *user);
void xmi_driver_destroy(struct xmi_driver *drv);

/* Send the per-channel controller preset the AIL driver constructor sends
 * (bank 0, program 0, bend centre, volume, pan, expression, bend range ...). */
void xmi_driver_reset(struct xmi_driver *drv);

/* Behaviour switches. All quirks are on by default: the sequencer then does
 * exactly what the AIL library in PS.EXE did, bugs included.
 *
 * XMI_QUIRK_BRANCH_SKIPS_EVENT: after a controller that moves the playback
 * position (a loop end, or a trigger callback that branches), XMI_serve
 * advances past whatever event sits at the new position. Branch targets in
 * the shipped scores follow their own marker, so this drops the first note
 * of a section whenever the target starts with a note-on (9 of the 42 city
 * branches), turning its duration bytes into a delay. */
#define XMI_QUIRK_BRANCH_SKIPS_EVENT 0x01
#define XMI_QUIRKS_ALL 0x01
void xmi_driver_set_quirks(struct xmi_driver *drv, unsigned quirks);
unsigned xmi_driver_quirks(const struct xmi_driver *drv);

/* AIL_set_XMIDI_master_volume: rescales every playing sequence. */
void xmi_driver_set_master_volume(struct xmi_driver *drv, int volume);
int xmi_driver_master_volume(const struct xmi_driver *drv);

/* One service tick (XMI_serve): call XMI_SERVICE_RATE times per second. */
void xmi_driver_serve(struct xmi_driver *drv);

/* Notes currently sounding on a driver channel (AIL_channel_notes). */
int xmi_driver_channel_notes(const struct xmi_driver *drv, int channel);

/* ---- Sequences --------------------------------------------------------- */

struct xmi_sequence *xmi_sequence_create(struct xmi_driver *drv);
void xmi_sequence_destroy(struct xmi_sequence *seq);

/* AIL_init_sequence: bind an XMIDI image (kept referenced, not copied) and
 * reset the playback state. Returns 1 on success, 0 for an invalid image. */
int xmi_sequence_init(struct xmi_sequence *seq, const void *data, size_t size,
                      int index);
const struct xmi_form *xmi_sequence_form(const struct xmi_sequence *seq);

void xmi_sequence_start(struct xmi_sequence *seq);
void xmi_sequence_stop(struct xmi_sequence *seq);
void xmi_sequence_resume(struct xmi_sequence *seq);
void xmi_sequence_end(struct xmi_sequence *seq);
int xmi_sequence_status(const struct xmi_sequence *seq);

/* AIL_set_sequence_volume: 0..127, optionally ramped over milliseconds. */
void xmi_sequence_set_volume(struct xmi_sequence *seq, int volume, int ms);
int xmi_sequence_volume(const struct xmi_sequence *seq);
/* AIL_set_sequence_loop_count: 1 plays once (the default), 0 loops forever. */
void xmi_sequence_set_loop_count(struct xmi_sequence *seq, int count);
int xmi_sequence_loop_count(const struct xmi_sequence *seq);
/* AIL_set_sequence_tempo: percent of the file tempo, optionally ramped. */
void xmi_sequence_set_tempo(struct xmi_sequence *seq, int percent, int ms);
int xmi_sequence_tempo(const struct xmi_sequence *seq);

/* AIL_branch_index: jump to a numbered RBRN branch. Returns 1 when found. */
int xmi_sequence_branch(struct xmi_sequence *seq, unsigned index);

void xmi_sequence_set_trigger_callback(struct xmi_sequence *seq,
                                       xmi_trigger_fn fn, void *user);
void xmi_sequence_set_end_callback(struct xmi_sequence *seq,
                                   xmi_sequence_fn fn, void *user);

/* AIL_controller_value: logged controller value for a channel, or -1. */
int xmi_sequence_controller(const struct xmi_sequence *seq, int channel,
                            int controller);
/* Byte offset of the next event within the EVNT payload (tests). */
size_t xmi_sequence_position(const struct xmi_sequence *seq);
/* Number of notes waiting in the duration queue (tests). */
int xmi_sequence_queued_notes(const struct xmi_sequence *seq);
/* Tempo and time signature last seen in the stream (tests). */
int xmi_sequence_file_tempo(const struct xmi_sequence *seq);

/* ---- Player: sequencer + Miles OPL3 driver + clock --------------------- */

struct miles_opl;
struct xmi_player;

struct xmi_player *xmi_player_create(uint32_t sample_rate);
void xmi_player_destroy(struct xmi_player *player);
struct xmi_driver *xmi_player_driver(struct xmi_player *player);
struct miles_opl *xmi_player_synth(struct xmi_player *player);
/* Load a Miles GTL bank into the synthesizer; returns timbres loaded. */
int xmi_player_load_bank(struct xmi_player *player, const void *data,
                         size_t size);
/* Render interleaved stereo frames, serving the sequencer at 120 Hz. */
void xmi_player_render(struct xmi_player *player, int16_t *stereo,
                       size_t frames);

#ifdef __cplusplus
}
#endif

#endif
