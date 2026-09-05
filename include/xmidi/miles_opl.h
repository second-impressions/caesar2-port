/*
 * Miles Sound System OPL3 music driver, reimplemented in C.
 *
 * This is a transliteration of the AIL 3.x "OPL3.MDI" driver that ships with
 * Caesar II (HD/OPL3.MDI, "Generic Yamaha OPL3-based FM music synthesizer").
 * It accepts the same MIDI channel-voice messages the driver received through
 * MDI_MIDI_XMIT, keeps the same 20 virtual / 18 physical voice model with the
 * same allocation and stealing policy, uses the driver's own frequency,
 * velocity and register tables, and renders through the Nuked OPL3 emulator.
 *
 * Timbres come from the game's Miles Global Timbre Library (CAESAR.OPL or
 * CAESAR.AD): the same 14-byte (2-op) and 25-byte (4-op) records the driver
 * loaded on demand from the .OPL file.
 */
#ifndef XMIDI_MILES_OPL_H
#define XMIDI_MILES_OPL_H

#include <stddef.h>
#include <stdint.h>

#define MILES_OPL_VIRTUAL_VOICES 20
#define MILES_OPL_PHYSICAL_VOICES 18
#define MILES_OPL_MAX_TIMBRES 192
#define MILES_OPL_TIMBRE_BYTES 25

struct miles_opl;

/* Create a driver rendering stereo 16-bit PCM at sample_rate. */
struct miles_opl *miles_opl_create(uint32_t sample_rate);
void miles_opl_destroy(struct miles_opl *drv);

/* Load every timbre from a Miles GTL bank image (.OPL / .AD). Returns the
 * number of timbres loaded, 0 when the image is not a valid bank. */
int miles_opl_load_bank(struct miles_opl *drv, const void *data, size_t size);
int miles_opl_timbre_count(const struct miles_opl *drv);
/* Look a timbre up by bank/patch; returns the record (2 length bytes, transpose,
 * then 11 bytes per voice) or NULL. Percussion uses bank 0x7f, patch = key. */
const unsigned char *miles_opl_find_timbre(const struct miles_opl *drv,
                                           int bank, int patch);

/* Reset the chip and channel state exactly as DRV_INIT_DEV + the AIL driver
 * constructor did (register image, then the per-channel controller preset). */
void miles_opl_reset(struct miles_opl *drv);

/* Feed one MIDI channel-voice message (status with channel in the low nibble). */
void miles_opl_message(struct miles_opl *drv, unsigned status,
                       unsigned data1, unsigned data2);

/* Render interleaved stereo frames. */
void miles_opl_render(struct miles_opl *drv, int16_t *stereo, size_t frames);

/* Introspection used by tests. */
int miles_opl_active_voices(const struct miles_opl *drv);
int miles_opl_channel_notes(const struct miles_opl *drv, int channel);
unsigned miles_opl_register(const struct miles_opl *drv, unsigned reg);

/* Optional register write tap (bank<<8 | reg, value) for tests. */
typedef void (*miles_opl_write_tap)(void *user, unsigned reg, unsigned value);
void miles_opl_set_write_tap(struct miles_opl *drv, miles_opl_write_tap tap,
                             void *user);

/* Driver data tables, exported so tests can check them byte-for-byte against
 * the shipped OPL3.MDI image. */
extern const uint16_t miles_opl_fnum_table[12][16];
extern const uint8_t miles_opl_block_table[96];
extern const uint8_t miles_opl_row_table[96];
extern const uint8_t miles_opl_velocity_table[16];
extern const uint8_t miles_opl_op1_of_channel[18];
extern const uint8_t miles_opl_op2_of_channel[18];
extern const uint8_t miles_opl_op_register[36];
extern const uint8_t miles_opl_op_bank[36];
extern const uint8_t miles_opl_channel_register[18];
extern const uint8_t miles_opl_channel_bank[18];
extern const uint8_t miles_opl_channel_4op_capable[18];
extern const uint8_t miles_opl_channel_partner[18];
extern const uint8_t miles_opl_partner_op1[18];
extern const uint8_t miles_opl_partner_op2[18];
extern const uint8_t miles_opl_4op_enable_mask[18];
extern const uint8_t miles_opl_4op_channels[6];
extern const uint8_t miles_opl_4op_volume_ops_a[4];
extern const uint8_t miles_opl_4op_volume_ops_b[4];
extern const uint8_t miles_opl_init_registers[2][0xf5];

#endif
