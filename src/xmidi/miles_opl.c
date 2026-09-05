/*
 * Miles Sound System OPL3 driver (AIL 3.x OPL3.MDI) reimplemented in C.
 *
 * The structure follows the original driver function by function so that the
 * behaviour can be checked against the disassembly:
 *
 *   MIDI_message        -> miles_opl_message
 *   note_on / note_off  -> note_on / note_off
 *   assign_voice        -> assign_physical      (round-robin allocation)
 *   steal_voices        -> steal_physical       (priority based stealing)
 *   release_voice       -> release_physical
 *   update_voice        -> update_voice         (register writer)
 *   setup_2op/setup_4op -> load_timbre_2op/4op
 *
 * Driver state that only existed because the DOS driver had a 4 KiB timbre
 * cache (LRU eviction, timbre protection) is not reproduced: the whole GTL
 * bank is resident.
 */
#include <stdlib.h>
#include <string.h>

#include "opl3.h"
#include "xmidi/miles_opl.h"

#define VV MILES_OPL_VIRTUAL_VOICES
#define PV MILES_OPL_PHYSICAL_VOICES
#define NO_VOICE 0xff

/* Dirty flags handed to update_voice (driver byte 0x1512). */
#define DIRTY_FREQ 0x01
#define DIRTY_FEEDBACK 0x08
#define DIRTY_WAVE 0x10
#define DIRTY_ENVELOPE 0x20
#define DIRTY_VOLUME 0x40
#define DIRTY_MODULATION 0x80
#define DIRTY_ALL 0xf9

#define VOICE_2OP 0
#define VOICE_4OP 3

#define KEY_ON 0x20

struct timbre {
    unsigned char bank;
    unsigned char patch;
    unsigned char data[MILES_OPL_TIMBRE_BYTES];
};

struct operator_image {
    unsigned char flags;   /* 0x20: AM/VIB/EG/KSR bits (byte & 0xf0) */
    unsigned char mult;    /* 0x20: multiplier (byte & 0x0f) */
    unsigned char ksl;     /* 0x40: key scale level bits (byte & 0xc0) */
    unsigned char level;   /* 0x40: 63 - total level */
    unsigned char attack;  /* 0x60 */
    unsigned char sustain; /* 0x80 */
    unsigned char wave;    /* 0xe0 */
};

struct pair_image {
    struct operator_image op[2];
    unsigned char feedback; /* 0xc0 feedback bits (byte & 0x0e) */
    unsigned char volume_ops; /* which operators carry volume */
};

struct virtual_voice {
    unsigned char in_use;
    unsigned char channel;
    unsigned char note;      /* MIDI note as received */
    unsigned char key;       /* note (or percussion key) used for pitch */
    signed char transpose;
    unsigned char velocity;  /* velocity table value */
    unsigned char physical;  /* NO_VOICE when unassigned */
    unsigned char sustained;
    unsigned char type;      /* VOICE_2OP / VOICE_4OP */
    unsigned char dirty;
    unsigned char key_state; /* KEY_ON while the key is held */
    unsigned char b0;        /* last value written to 0xB0 */
    unsigned char connection; /* bit 0: pair 1 conn, bit 1: pair 2 conn */
    unsigned priority;
    unsigned score;
    struct pair_image pair[2];
};

struct channel {
    unsigned char bank;          /* controller 114 */
    unsigned char voice_protect; /* controller 112 */
    unsigned char program;
    unsigned char timbre;        /* index into timbres, NO_VOICE when none */
    unsigned char bend_range;    /* controller 6 */
    unsigned char volume;        /* controller 7 */
    unsigned char pan;           /* controller 10 */
    unsigned char bend_lsb;
    unsigned char bend_msb;
    unsigned char expression;    /* controller 11 */
    unsigned char modulation;    /* controller 1 */
    unsigned char sustain;       /* controller 64 */
    unsigned char notes;         /* physical voices assigned */
};

struct miles_opl {
    opl3_chip chip;
    uint32_t sample_rate;
    struct timbre timbres[MILES_OPL_MAX_TIMBRES];
    int timbre_count;
    struct virtual_voice voice[VV];
    struct channel channel[16];
    unsigned char percussion_timbre[128];
    unsigned char physical_owner[PV + 3]; /* MIDI channel or NO_VOICE */
    unsigned char four_op_enable;         /* shadow of register 0x104 */
    int rr_2op;
    int rr_4op;
    unsigned char registers[2][256];
    miles_opl_write_tap tap;
    void *tap_user;
};

/* ------------------------------------------------------------------------ */
/* Chip access                                                              */

static void write_reg(struct miles_opl *drv, unsigned bank, unsigned reg,
                      unsigned value)
{
    drv->registers[bank & 1][reg & 0xff] = (unsigned char)value;
    OPL3_WriteReg(&drv->chip, (uint16_t)(((bank & 1) << 8) | (reg & 0xff)),
                  (uint8_t)value);
    if (drv->tap) drv->tap(drv->tap_user, ((bank & 1) << 8) | (reg & 0xff), value);
}

static void write_op(struct miles_opl *drv, unsigned op, unsigned reg,
                     unsigned value)
{
    write_reg(drv, miles_opl_op_bank[op],
              (miles_opl_op_register[op] + reg) & 0xff, value);
}

static void write_channel(struct miles_opl *drv, unsigned ch, unsigned reg,
                          unsigned value)
{
    write_reg(drv, miles_opl_channel_bank[ch],
              (miles_opl_channel_register[ch] + reg) & 0xff, value);
}

/* DRV_INIT_DEV: OPL3 mode on, 4-op off, then the register image. */
static void reset_chip(struct miles_opl *drv)
{
    unsigned reg;

    write_reg(drv, 1, 0x05, 1);
    write_reg(drv, 1, 0x04, 0);
    drv->four_op_enable = 0;
    for (reg = 1; reg <= 0xf5; reg++) {
        write_reg(drv, 0, reg, miles_opl_init_registers[0][reg - 1]);
    }
    for (reg = 1; reg <= 0xf5; reg++) {
        write_reg(drv, 1, reg, miles_opl_init_registers[1][reg - 1]);
    }
}

/* ------------------------------------------------------------------------ */
/* Timbres                                                                  */

static int find_timbre(const struct miles_opl *drv, int bank, int patch)
{
    int i;

    for (i = 0; i < drv->timbre_count; i++) {
        if (drv->timbres[i].bank == bank && drv->timbres[i].patch == patch) {
            return i;
        }
    }
    return -1;
}

const unsigned char *miles_opl_find_timbre(const struct miles_opl *drv,
                                           int bank, int patch)
{
    int index;

    if (drv == NULL) return NULL;
    index = find_timbre(drv, bank, patch);
    return index < 0 ? NULL : drv->timbres[index].data;
}

int miles_opl_load_bank(struct miles_opl *drv, const void *data, size_t size)
{
    const unsigned char *bytes;
    const unsigned char *entry;
    size_t offset;
    size_t record;
    unsigned length;
    int count;

    if (drv == NULL || data == NULL) return 0;
    bytes = data;
    count = 0;
    for (offset = 0; offset + 6 <= size; offset += 6) {
        entry = bytes + offset;
        if (entry[0] == 0xff || entry[1] == 0xff) break;
        if (entry[0] > 127) return 0;
        record = (size_t)entry[2] | ((size_t)entry[3] << 8) |
                 ((size_t)entry[4] << 16) | ((size_t)entry[5] << 24);
        if (record > size || size - record < 3) return 0;
        length = (unsigned)bytes[record] | ((unsigned)bytes[record + 1] << 8);
        if ((length != 14 && length != 25) || length > size - record) return 0;
        if (count == MILES_OPL_MAX_TIMBRES) break;
        drv->timbres[count].bank = entry[1];
        drv->timbres[count].patch = entry[0];
        memset(drv->timbres[count].data, 0, MILES_OPL_TIMBRE_BYTES);
        memcpy(drv->timbres[count].data, bytes + record, length);
        count++;
    }
    drv->timbre_count = count;
    memset(drv->percussion_timbre, NO_VOICE, sizeof(drv->percussion_timbre));
    return count;
}

int miles_opl_timbre_count(const struct miles_opl *drv)
{
    return drv == NULL ? 0 : drv->timbre_count;
}

/* Miles GTL voice record: five operator-1 registers, the 0xC0 byte, then the
 * five operator-2 registers. Operator 1 is the modulator. */
static void load_operator(struct operator_image *op, const unsigned char *regs)
{
    op->flags = regs[0] & 0xf0;
    op->mult = regs[0] & 0x0f;
    op->ksl = regs[1] & 0xc0;
    op->level = (unsigned char)(~regs[1] & 0x3f);
    op->attack = regs[2];
    op->sustain = regs[3];
    op->wave = regs[4];
}

static void load_timbre_2op(struct virtual_voice *v, const unsigned char *t)
{
    v->key_state = KEY_ON;
    v->type = VOICE_2OP;
    v->priority = 0x7fff;
    v->connection = t[8] & 1;
    v->pair[0].feedback = t[8] & 0x0e;
    load_operator(&v->pair[0].op[0], t + 3);
    load_operator(&v->pair[0].op[1], t + 9);
    v->pair[0].volume_ops = v->connection | 2;
    v->dirty = DIRTY_ALL;
}

static void load_timbre_4op(struct virtual_voice *v, const unsigned char *t)
{
    load_timbre_2op(v, t);
    v->type = VOICE_4OP;
    /* Bit 7 of the first 0xC0 byte is the second pair's connection. */
    v->connection |= (t[8] & 0x80) >> 6;
    v->pair[0].volume_ops = miles_opl_4op_volume_ops_a[v->connection];
    v->pair[1].volume_ops = miles_opl_4op_volume_ops_b[v->connection];
    v->pair[1].feedback = 0;
    load_operator(&v->pair[1].op[0], t + 14);
    load_operator(&v->pair[1].op[1], t + 20);
}

/* ------------------------------------------------------------------------ */
/* Register writer (driver update_voice, 0x3134)                            */

static unsigned pitch_registers(const struct miles_opl *drv,
                                const struct virtual_voice *v)
{
    const struct channel *ch;
    int bend;
    int note;
    int pitch;
    unsigned fnum;
    int block;

    ch = &drv->channel[v->channel];
    bend = (((int)ch->bend_msb << 7) | ch->bend_lsb) - 0x2000;
    bend = (bend >> 5) * ch->bend_range;
    /* The driver's octave normalisation, kept literally: the net effect is
     * key + transpose - 12 folded into 0..95. */
    note = (int)v->key + v->transpose - 24;
    while (note + 12 < 0) note += 12;
    note += 24;
    do {
        note -= 12;
    } while (note > 95);
    /* Pitch in 1/16 semitone, folded into the eight-octave table range. */
    pitch = ((note * 256 + bend + 8) >> 4) - 0xc0;
    while (pitch + 0xc0 < 0) pitch += 0xc0;
    pitch += 0x180;
    do {
        pitch -= 0xc0;
    } while (pitch > 0x5ff);
    fnum = miles_opl_fnum_table[miles_opl_row_table[pitch >> 4]][pitch & 0x0f];
    block = miles_opl_block_table[pitch >> 4];
    if ((fnum & 0x8000) == 0) block--;
    if (block < 0) {
        block++;
        fnum >>= 1;
    }
    fnum &= 0x3ff;
    return fnum | ((unsigned)block << 10);
}

static void update_pair(struct miles_opl *drv, struct virtual_voice *v,
                        int pair, unsigned ch, unsigned op1, unsigned op2,
                        unsigned volume)
{
    const struct pair_image *img;
    const struct channel *chan;
    unsigned vib;
    unsigned level;
    unsigned value;
    unsigned freq;

    img = &v->pair[pair];
    chan = &drv->channel[v->channel];
    if (v->dirty & DIRTY_MODULATION) {
        vib = chan->modulation >= 0x40 ? 0x40 : 0;
        write_op(drv, op1, 0x20, img->op[0].mult | vib | img->op[0].flags);
        write_op(drv, op2, 0x20, img->op[1].mult | vib | img->op[1].flags);
    }
    if (v->dirty & DIRTY_VOLUME) {
        level = img->op[0].level;
        if (img->volume_ops & 1) level = level * volume / 0x7f;
        write_op(drv, op1, 0x40, (~level & 0x3f) | img->op[0].ksl);
        level = img->op[1].level;
        if (img->volume_ops & 2) level = level * volume / 0x7f;
        write_op(drv, op2, 0x40, (~level & 0x3f) | img->op[1].ksl);
    }
    if (v->dirty & DIRTY_ENVELOPE) {
        write_op(drv, op1, 0x60, img->op[0].attack);
        write_op(drv, op2, 0x60, img->op[1].attack);
        write_op(drv, op1, 0x80, img->op[0].sustain);
        write_op(drv, op2, 0x80, img->op[1].sustain);
    }
    if (v->dirty & DIRTY_WAVE) {
        write_op(drv, op2, 0xe0, img->op[1].wave);
        write_op(drv, op1, 0xe0, img->op[0].wave);
    }
    if (v->dirty & DIRTY_FEEDBACK) {
        value = img->feedback | ((v->connection >> pair) & 1);
        if (chan->pan < 28) value |= 0x10;
        else if (chan->pan > 99) value |= 0x20;
        else value |= 0x30;
        write_channel(drv, ch, 0xc0, value);
    }
    if ((v->dirty & DIRTY_FREQ) && pair == 0) {
        if (v->key_state & KEY_ON) {
            freq = pitch_registers(drv, v);
            write_channel(drv, ch, 0xa0, freq & 0xff);
            v->b0 = (unsigned char)((freq >> 8) | v->key_state);
            write_channel(drv, ch, 0xb0, v->b0);
        } else {
            write_channel(drv, ch, 0xb0, v->b0 & ~KEY_ON);
        }
    }
}

static void update_voice(struct miles_opl *drv, struct virtual_voice *v)
{
    const struct channel *chan;
    unsigned phys;
    unsigned volume;
    unsigned mask;
    unsigned dirty;
    unsigned enable;

    if (v->physical == NO_VOICE) return;
    phys = v->physical;
    chan = &drv->channel[v->channel];
    volume = 0;
    if (v->dirty & DIRTY_VOLUME) {
        /* (a * b * 2) >> 8, rounded up unless zero: the driver's fixed-point
         * product of channel volume, expression and velocity. */
        volume = (chan->volume * chan->expression * 2) >> 8;
        if (volume) volume++;
        volume = (volume * v->velocity * 2) >> 8;
        if (volume) volume++;
    }
    mask = miles_opl_4op_enable_mask[phys];
    if (v->type == VOICE_4OP) {
        enable = drv->four_op_enable | mask;
        if (enable != drv->four_op_enable) {
            drv->four_op_enable = (unsigned char)enable;
            write_reg(drv, 1, 0x04, enable);
        }
    } else {
        enable = drv->four_op_enable & ~mask;
        if (enable != drv->four_op_enable) {
            /* Leaving 4-op mode: silence the partner channel. */
            drv->four_op_enable = (unsigned char)enable;
            write_reg(drv, 1, 0x04, enable);
            write_op(drv, miles_opl_partner_op1[phys], 0x80, 0x0f);
            write_op(drv, miles_opl_partner_op2[phys], 0x80, 0x0f);
            write_channel(drv, miles_opl_channel_partner[phys], 0xb0, 0);
        }
    }
    dirty = v->dirty;
    if (v->type == VOICE_4OP) {
        update_pair(drv, v, 1, phys + 3,
                    miles_opl_op1_of_channel[phys + 3],
                    miles_opl_op2_of_channel[phys + 3], volume);
        v->dirty = (unsigned char)dirty;
    }
    update_pair(drv, v, 0, phys, miles_opl_op1_of_channel[phys],
                miles_opl_op2_of_channel[phys], volume);
    v->dirty = 0;
}

/* ------------------------------------------------------------------------ */
/* Physical voice management                                                */

static void release_physical(struct miles_opl *drv, struct virtual_voice *v)
{
    unsigned phys;

    if (v->physical == NO_VOICE) return;
    v->key_state &= (unsigned char)~KEY_ON;
    v->dirty |= DIRTY_FREQ;
    update_voice(drv, v);
    drv->channel[v->channel].notes--;
    phys = v->physical;
    if (v->type == VOICE_4OP) drv->physical_owner[phys + 3] = NO_VOICE;
    drv->physical_owner[phys] = NO_VOICE;
    v->physical = NO_VOICE;
    v->in_use = 0;
}

static void take_physical(struct miles_opl *drv, struct virtual_voice *v,
                          unsigned phys)
{
    v->physical = (unsigned char)phys;
    drv->channel[v->channel].notes++;
    drv->physical_owner[phys] = v->channel;
    if (v->type == VOICE_4OP) drv->physical_owner[phys + 3] = v->channel;
}

/* Driver 0x36a6: free a physical voice for the waiting virtual voice with
 * the highest score by silencing the assigned voice with the lowest one. */
static void steal_physical(struct miles_opl *drv)
{
    struct virtual_voice *v;
    unsigned waiting_count;
    unsigned best_waiting;
    unsigned worst_assigned;
    unsigned worst_4op;
    int waiting;
    int victim;
    int victim_4op;
    int i;

    waiting_count = 0;
    for (i = 0; i < VV; i++) {
        v = &drv->voice[i];
        if (!v->in_use) continue;
        waiting_count++;
        v->score = drv->channel[v->channel].voice_protect < 0x40 ? v->priority
                                                                  : 0xffff;
        if (v->score < drv->channel[v->channel].notes) v->score = 0;
        else v->score -= drv->channel[v->channel].notes;
    }
    for (;;) {
        best_waiting = 0;
        worst_assigned = 0xffff;
        worst_4op = 0xffff;
        waiting = victim = victim_4op = -1;
        for (i = 0; i < VV; i++) {
            v = &drv->voice[i];
            if (!v->in_use) continue;
            if (v->physical == NO_VOICE) {
                if (v->score >= best_waiting) {
                    best_waiting = v->score;
                    waiting = i;
                }
            } else {
                if (miles_opl_channel_4op_capable[v->physical] &&
                    v->score <= worst_4op) {
                    worst_4op = v->score;
                    victim_4op = i;
                }
                if (v->score <= worst_assigned) {
                    worst_assigned = v->score;
                    victim = i;
                }
            }
        }
        if (waiting < 0 || victim < 0) return;
        if (best_waiting < worst_assigned || best_waiting == 0) return;
        if (drv->voice[waiting].type == VOICE_4OP) {
            victim = victim_4op;
            if (victim < 0) return;
            if (drv->voice[victim].type != VOICE_4OP) {
                /* The original indexes the partner table with the virtual
                 * voice number instead of its physical channel; keep that
                 * behaviour, it is what the shipped driver does. */
                unsigned partner = miles_opl_channel_partner[victim];
                for (i = 0; i < VV; i++) {
                    if (drv->voice[i].in_use &&
                        drv->voice[i].physical == partner) {
                        release_physical(drv, &drv->voice[i]);
                        break;
                    }
                }
            }
        }
        i = drv->voice[victim].physical;
        release_physical(drv, &drv->voice[victim]);
        v = &drv->voice[waiting];
        take_physical(drv, v, (unsigned)i);
        v->dirty = DIRTY_ALL;
        update_voice(drv, v);
        if (--waiting_count == 0) return;
    }
}

/* Driver 0x3035. */
static void assign_physical(struct miles_opl *drv, struct virtual_voice *v)
{
    int tries;
    unsigned phys;

    if (v->type == VOICE_4OP) {
        for (tries = 0; tries < 6; tries++) {
            drv->rr_4op = (drv->rr_4op + 1) % 6;
            phys = miles_opl_4op_channels[drv->rr_4op];
            if (drv->physical_owner[phys] == NO_VOICE &&
                drv->physical_owner[phys + 3] == NO_VOICE) {
                take_physical(drv, v, phys);
                v->dirty = DIRTY_ALL;
                update_voice(drv, v);
                return;
            }
        }
    } else {
        for (tries = 0; tries < PV; tries++) {
            drv->rr_2op = (drv->rr_2op + 1) % PV;
            phys = (unsigned)drv->rr_2op;
            if (drv->physical_owner[phys] == NO_VOICE) {
                take_physical(drv, v, phys);
                v->dirty = DIRTY_ALL;
                update_voice(drv, v);
                return;
            }
        }
    }
    steal_physical(drv);
}

/* ------------------------------------------------------------------------ */
/* MIDI                                                                     */

static void note_off(struct miles_opl *drv, unsigned channel, unsigned note)
{
    struct virtual_voice *v;
    int i;

    for (i = 0; i < VV; i++) {
        v = &drv->voice[i];
        if (v->in_use != 1 || v->note != note || v->channel != channel) continue;
        if (drv->channel[channel].sustain >= 0x40) {
            v->sustained = 1;
        } else {
            release_physical(drv, v);
            v->in_use = 0;
        }
    }
}

static void release_sustained(struct miles_opl *drv, unsigned channel)
{
    int i;

    for (i = 0; i < VV; i++) {
        if (drv->voice[i].in_use && drv->voice[i].channel == channel &&
            drv->voice[i].sustained) {
            note_off(drv, channel, drv->voice[i].note);
        }
    }
}

static void note_on(struct miles_opl *drv, unsigned channel, unsigned note,
                    unsigned velocity)
{
    struct virtual_voice *v;
    const unsigned char *timbre;
    int index;
    int i;

    index = drv->channel[channel].timbre == NO_VOICE
                ? -1 : drv->channel[channel].timbre;
    if (channel == 9) {
        if (drv->percussion_timbre[note] == NO_VOICE) {
            index = find_timbre(drv, 0x7f, (int)note);
            drv->percussion_timbre[note] =
                (unsigned char)(index < 0 ? NO_VOICE : index);
        }
        index = drv->percussion_timbre[note] == NO_VOICE
                    ? -1 : drv->percussion_timbre[note];
    }
    if (index < 0) return;
    timbre = drv->timbres[index].data;
    for (i = 0; i < VV; i++) {
        if (!drv->voice[i].in_use) break;
    }
    if (i == VV) return; /* every virtual voice busy: the note is dropped */
    v = &drv->voice[i];
    v->channel = (unsigned char)channel;
    v->note = (unsigned char)note;
    if (channel == 9) {
        v->key = timbre[2];
        v->transpose = 0;
    } else {
        v->key = (unsigned char)note;
        v->transpose = (signed char)timbre[2];
    }
    v->velocity = miles_opl_velocity_table[(velocity & 0x7f) >> 3];
    v->in_use = 1;
    v->sustained = 0;
    v->physical = NO_VOICE;
    if (timbre[0] == 25) load_timbre_4op(v, timbre);
    else load_timbre_2op(v, timbre);
    assign_physical(drv, v);
}

static void touch_channel_voices(struct miles_opl *drv, unsigned channel,
                                 unsigned dirty)
{
    int i;

    for (i = 0; i < VV; i++) {
        if (drv->voice[i].in_use && drv->voice[i].channel == channel) {
            drv->voice[i].dirty |= (unsigned char)dirty;
            update_voice(drv, &drv->voice[i]);
        }
    }
}

static void all_notes_off(struct miles_opl *drv, unsigned channel)
{
    int i;

    for (i = 0; i < VV; i++) {
        if (drv->voice[i].in_use == 1 && drv->voice[i].channel == channel) {
            note_off(drv, channel, drv->voice[i].note);
        }
    }
}

static void program_change(struct miles_opl *drv, unsigned channel,
                           unsigned program)
{
    struct channel *ch;
    int index;

    ch = &drv->channel[channel];
    ch->program = (unsigned char)program;
    index = find_timbre(drv, ch->bank, (int)program);
    ch->timbre = (unsigned char)(index < 0 ? NO_VOICE : index);
}

static void control_change(struct miles_opl *drv, unsigned channel,
                           unsigned controller, unsigned value)
{
    struct channel *ch;

    ch = &drv->channel[channel];
    switch (controller) {
    case 1:
        ch->modulation = (unsigned char)value;
        touch_channel_voices(drv, channel, DIRTY_MODULATION);
        break;
    case 6:
        ch->bend_range = (unsigned char)value;
        break;
    case 7:
        ch->volume = (unsigned char)value;
        touch_channel_voices(drv, channel, DIRTY_VOLUME);
        break;
    case 10:
        ch->pan = (unsigned char)value;
        touch_channel_voices(drv, channel, DIRTY_FEEDBACK);
        break;
    case 11:
        ch->expression = (unsigned char)value;
        touch_channel_voices(drv, channel, DIRTY_VOLUME);
        break;
    case 64:
        ch->sustain = (unsigned char)value;
        if (value < 0x40) release_sustained(drv, channel);
        break;
    case 112:
        ch->voice_protect = (unsigned char)value;
        break;
    case 113:
        /* Timbre protect: only meaningful for the DOS timbre cache. */
        break;
    case 114:
        ch->bank = (unsigned char)value;
        break;
    case 121:
        ch->sustain = 0;
        release_sustained(drv, channel);
        ch->modulation = 0;
        ch->expression = 0x7f;
        ch->bend_lsb = 0;
        ch->bend_msb = 0x40;
        touch_channel_voices(drv, channel,
                             DIRTY_MODULATION | DIRTY_VOLUME | DIRTY_FREQ);
        break;
    case 123:
        all_notes_off(drv, channel);
        break;
    default:
        break;
    }
}

void miles_opl_message(struct miles_opl *drv, unsigned status,
                       unsigned data1, unsigned data2)
{
    unsigned channel;
    struct channel *ch;

    if (drv == NULL) return;
    channel = status & 0x0f;
    data1 &= 0xff;
    data2 &= 0xff;
    switch (status & 0xf0) {
    case 0x80:
        note_off(drv, channel, data1);
        break;
    case 0x90:
        if (data2 == 0) note_off(drv, channel, data1);
        else note_on(drv, channel, data1, data2);
        break;
    case 0xb0:
        control_change(drv, channel, data1, data2);
        break;
    case 0xc0:
        program_change(drv, channel, data1);
        break;
    case 0xe0:
        ch = &drv->channel[channel];
        ch->bend_lsb = (unsigned char)data1;
        ch->bend_msb = (unsigned char)data2;
        touch_channel_voices(drv, channel, DIRTY_FREQ);
        break;
    default:
        break;
    }
}

/* ------------------------------------------------------------------------ */
/* Lifecycle                                                                */

void miles_opl_reset(struct miles_opl *drv)
{
    int i;

    if (drv == NULL) return;
    memset(drv->voice, 0, sizeof(drv->voice));
    memset(drv->channel, 0, sizeof(drv->channel));
    memset(drv->physical_owner, NO_VOICE, sizeof(drv->physical_owner));
    memset(drv->percussion_timbre, NO_VOICE, sizeof(drv->percussion_timbre));
    for (i = 0; i < 16; i++) drv->channel[i].timbre = NO_VOICE;
    drv->rr_2op = -1;
    drv->rr_4op = -1;
    memset(drv->registers, 0, sizeof(drv->registers));
    OPL3_Reset(&drv->chip, drv->sample_rate);
    reset_chip(drv);
}

struct miles_opl *miles_opl_create(uint32_t sample_rate)
{
    struct miles_opl *drv;

    drv = calloc(1, sizeof(*drv));
    if (drv == NULL) return NULL;
    drv->sample_rate = sample_rate;
    miles_opl_reset(drv);
    return drv;
}

void miles_opl_destroy(struct miles_opl *drv)
{
    free(drv);
}

void miles_opl_render(struct miles_opl *drv, int16_t *stereo, size_t frames)
{
    if (drv == NULL || stereo == NULL || frames == 0) return;
    OPL3_GenerateStream(&drv->chip, stereo, (uint32_t)frames);
}

void miles_opl_set_write_tap(struct miles_opl *drv, miles_opl_write_tap tap,
                             void *user)
{
    if (drv == NULL) return;
    drv->tap = tap;
    drv->tap_user = user;
}

int miles_opl_active_voices(const struct miles_opl *drv)
{
    int count;
    int i;

    if (drv == NULL) return 0;
    count = 0;
    for (i = 0; i < VV; i++) count += drv->voice[i].in_use != 0;
    return count;
}

int miles_opl_channel_notes(const struct miles_opl *drv, int channel)
{
    if (drv == NULL || channel < 0 || channel > 15) return 0;
    return drv->channel[channel].notes;
}

unsigned miles_opl_register(const struct miles_opl *drv, unsigned reg)
{
    if (drv == NULL) return 0;
    return drv->registers[(reg >> 8) & 1][reg & 0xff];
}
