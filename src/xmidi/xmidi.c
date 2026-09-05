/*
 * XMIDI sequencer with AIL 3.x semantics.
 *
 * Function names in comments refer to the AIL routines in PS.EXE that each
 * block reproduces (XMI_serve, XMI_send_channel_voice_message, XMI_read_log,
 * XMI_write_log, XMI_refresh_channel, AIL_API_branch_index, ...).
 */
#include <stdlib.h>
#include <string.h>

#include "xmidi/miles_opl.h"
#include "xmidi/xmidi.h"

#define XMI_NOTE_QUEUE 32
#define XMI_LOOP_DEPTH 4
#define XMI_CHANNELS 16

/* Controller log slots (XMI_read_log / XMI_write_log). */
enum log_slot {
    LOG_PROGRAM = 0,
    LOG_BEND_LSB,
    LOG_BEND_MSB,
    LOG_CHANNEL_LOCK,      /* 110 */
    LOG_LOCK_PROTECT,      /* 111 */
    LOG_MUTE,              /* 107 */
    LOG_VOICE_PROTECT,     /* 112 */
    LOG_BANK,              /* 114 */
    LOG_INDIRECT,          /* 115 */
    LOG_TRIGGER,           /* 119 */
    LOG_MODULATION,        /* 1 */
    LOG_VOLUME,            /* 7 */
    LOG_PAN,               /* 10 */
    LOG_EXPRESSION,        /* 11 */
    LOG_SUSTAIN,           /* 64 */
    LOG_REVERB,            /* 91 */
    LOG_CHORUS,            /* 93 */
    LOG_BEND_RANGE,        /* 6 */
    LOG_SLOTS
};

struct xmi_sequence {
    struct xmi_driver *driver;
    struct xmi_sequence *next;
    int status;
    struct xmi_form form;
    const unsigned char *evnt_begin;
    const unsigned char *evnt_end;
    const unsigned char *ptr;

    xmi_trigger_fn trigger_fn;
    void *trigger_user;
    xmi_sequence_fn end_fn;
    void *end_user;

    int loop_count;
    int interval_count;
    int interval_num;
    int volume;
    int volume_target;
    int volume_accum;
    int volume_period;
    int tempo_percent;
    int tempo_target;
    int tempo_accum;
    int tempo_period;
    int tempo_error;
    int file_tempo;

    const unsigned char *loop_start[XMI_LOOP_DEPTH];
    int loop_counter[XMI_LOOP_DEPTH];

    int log[LOG_SLOTS][XMI_CHANNELS];

    int note_count;
    int note_channel[XMI_NOTE_QUEUE];
    int note_number[XMI_NOTE_QUEUE];
    int note_time[XMI_NOTE_QUEUE];
};

struct xmi_driver {
    xmi_midi_fn midi;
    void *midi_user;
    struct xmi_sequence *sequences;
    int master_volume;
    int interval_us;
    int channel_notes[XMI_CHANNELS];
    int serving;
    unsigned quirks;
};

/* ------------------------------------------------------------------------ */
/* File layout                                                              */

static uint32_t be32(const unsigned char *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static uint16_t le16(const unsigned char *p)
{
    return (uint16_t)(p[0] | (p[1] << 8));
}

static uint32_t le32(const unsigned char *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

size_t xmi_image_size(const void *data, size_t cap)
{
    const unsigned char *p;
    size_t offset;
    size_t chunk;

    p = data;
    offset = 0;
    if (p == NULL) return 0;
    for (;;) {
        if (cap - offset < 12) return 0;
        if (memcmp(p + offset, "FORM", 4) != 0 &&
            memcmp(p + offset, "CAT ", 4) != 0) {
            return 0;
        }
        chunk = (size_t)be32(p + offset + 4) + 8;
        if (chunk > cap - offset) return 0;
        if (memcmp(p + offset + 8, "XMID", 4) == 0) return offset + chunk;
        offset += chunk;
    }
}

/* XMI_find_sequence */
static const unsigned char *find_sequence(const unsigned char *data,
                                          size_t size, int index)
{
    const unsigned char *p;
    const unsigned char *end;
    const unsigned char *q;
    size_t chunk;

    p = data;
    end = data + size;
    for (;;) {
        if (end - p < 12) return NULL;
        if (memcmp(p, "FORM", 4) != 0 && memcmp(p, "CAT ", 4) != 0) return NULL;
        chunk = (size_t)be32(p + 4) + 8;
        if (chunk > (size_t)(end - p)) return NULL;
        if (memcmp(p + 8, "XMID", 4) == 0) break;
        p += chunk;
    }
    if (memcmp(p, "FORM", 4) == 0) return index == 0 ? p : NULL;
    for (q = p + 12; q + 12 <= p + chunk; q += (size_t)be32(q + 4) + 8) {
        if (memcmp(q + 8, "XMID", 4) == 0 && index-- == 0) return q;
        if ((size_t)be32(q + 4) + 8 > (size_t)(p + chunk - q)) break;
    }
    return NULL;
}

int xmi_find_form(const void *data, size_t size, int index,
                  struct xmi_form *out)
{
    const unsigned char *form;
    const unsigned char *end;
    const unsigned char *q;
    size_t chunk;

    if (out == NULL) return 0;
    memset(out, 0, sizeof(*out));
    if (data == NULL) return 0;
    form = find_sequence(data, size, index);
    if (form == NULL) return 0;
    end = form + 8 + be32(form + 4);
    if (end > (const unsigned char *)data + size) return 0;
    out->form = form;
    for (q = form + 12; q + 8 <= end; q += chunk) {
        chunk = (size_t)be32(q + 4) + 8;
        if (chunk > (size_t)(end - q)) break;
        if (memcmp(q, "TIMB", 4) == 0) out->timb = q;
        else if (memcmp(q, "RBRN", 4) == 0) out->rbrn = q;
        else if (memcmp(q, "EVNT", 4) == 0) {
            out->evnt = q;
            out->evnt_size = chunk - 8;
        }
    }
    return out->evnt != NULL;
}

int xmi_form_branch_count(const struct xmi_form *form)
{
    if (form == NULL || form->rbrn == NULL) return 0;
    return le16(form->rbrn + 8);
}

int xmi_form_branch(const struct xmi_form *form, int index, unsigned *id,
                    size_t *offset)
{
    const unsigned char *entry;

    if (index < 0 || index >= xmi_form_branch_count(form)) return 0;
    entry = form->rbrn + 10 + index * 6;
    if (id) *id = le16(entry);
    if (offset) *offset = le32(entry + 2);
    return 1;
}

int xmi_form_timbre_count(const struct xmi_form *form)
{
    if (form == NULL || form->timb == NULL) return 0;
    return le16(form->timb + 8);
}

int xmi_form_timbre(const struct xmi_form *form, int index, unsigned *patch,
                    unsigned *bank)
{
    const unsigned char *entry;

    if (index < 0 || index >= xmi_form_timbre_count(form)) return 0;
    entry = form->timb + 10 + index * 2;
    if (patch) *patch = entry[0];
    if (bank) *bank = entry[1];
    return 1;
}

/* ------------------------------------------------------------------------ */
/* Controller log                                                           */

static int log_slot(unsigned status, unsigned data1)
{
    switch (status & 0xf0) {
    case 0xc0:
        return LOG_PROGRAM;
    case 0xb0:
        switch (data1) {
        case 1: return LOG_MODULATION;
        case 6: return LOG_BEND_RANGE;
        case 7: return LOG_VOLUME;
        case 10: return LOG_PAN;
        case 11: return LOG_EXPRESSION;
        case 64: return LOG_SUSTAIN;
        case 91: return LOG_REVERB;
        case 93: return LOG_CHORUS;
        case 107: return LOG_MUTE;
        case 110: return LOG_CHANNEL_LOCK;
        case 111: return LOG_LOCK_PROTECT;
        case 112: return LOG_VOICE_PROTECT;
        case 114: return LOG_BANK;
        case 115: return LOG_INDIRECT;
        case 119: return LOG_TRIGGER;
        default: return -1;
        }
    default:
        return -1;
    }
}

/* XMI_write_log */
static void write_log(struct xmi_sequence *seq, unsigned status,
                      unsigned data1, unsigned data2)
{
    unsigned channel;
    int slot;

    channel = status & 0x0f;
    if ((status & 0xf0) == 0xe0) {
        seq->log[LOG_BEND_LSB][channel] = (int)(data1 & 0xff);
        seq->log[LOG_BEND_MSB][channel] = (int)(data2 & 0xff);
        return;
    }
    slot = log_slot(status, data1);
    if (slot < 0) return;
    if ((status & 0xf0) == 0xc0) seq->log[slot][channel] = (int)(data1 & 0xff);
    else seq->log[slot][channel] = (int)(data2 & 0xff);
}

int xmi_sequence_controller(const struct xmi_sequence *seq, int channel,
                            int controller)
{
    int slot;

    if (seq == NULL || channel < 0 || channel > 15) return -1;
    slot = log_slot(0xb0, (unsigned)controller);
    return slot < 0 ? -1 : seq->log[slot][channel];
}

/* ------------------------------------------------------------------------ */
/* Message routing                                                          */

static void driver_send(struct xmi_driver *drv, unsigned status,
                        unsigned data1, unsigned data2)
{
    if (drv->midi) drv->midi(drv->midi_user, status, data1, data2);
}

static void send_channel_voice_message(struct xmi_sequence *seq,
                                       unsigned status, unsigned data1,
                                       unsigned data2, int from_stream);

static int branch_to(struct xmi_sequence *seq, unsigned index);

/* XMI_send_channel_voice_message */
static void send_channel_voice_message(struct xmi_sequence *seq,
                                       unsigned status, unsigned data1,
                                       unsigned data2, int from_stream)
{
    struct xmi_driver *drv;
    unsigned channel;
    unsigned type;
    int i;

    drv = seq->driver;
    channel = status & 0x0f;
    type = status & 0xf0;
    if (type == 0xb0 || type == 0xc0 || type == 0xe0) {
        write_log(seq, status, data1, data2);
    }
    if (type == 0xb0) {
        if (from_stream && seq->log[LOG_INDIRECT][channel] != -1) {
            /* A pending indirect controller value replaces the data byte. */
            data2 = (unsigned)seq->log[LOG_INDIRECT][channel];
            seq->log[LOG_INDIRECT][channel] = -1;
        }
        switch (data1) {
        case 6:
            /* Bend range goes out as RPN 0 with a zero LSB first. */
            send_channel_voice_message(seq, status, 100, 0, 0);
            send_channel_voice_message(seq, status, 101, 0, 0);
            send_channel_voice_message(seq, status, 38, 0, 0);
            break;
        case 7:
            data2 = (unsigned)((seq->volume * (int)data2 * drv->master_volume) /
                               (127 * 127));
            if (data2 > 127) data2 = 127;
            break;
        case 108:
            /* Prefix callback: not registered by the port. */
            break;
        case 109:
            branch_to(seq, data2);
            return;
        case 110:
        case 111:
            /* Channel locking against other sequences is not reproduced:
             * the port never plays two sequences at once. */
            return;
        case 115:
            /* Indirect controller array: none registered. */
            break;
        case 116:
            for (i = 0; i < XMI_LOOP_DEPTH; i++) {
                if (seq->loop_counter[i] == -1) break;
            }
            if (i == XMI_LOOP_DEPTH) return;
            seq->loop_counter[i] = (int)data2;
            seq->loop_start[i] = seq->ptr;
            return;
        case 117:
            if (data2 < 0x40) return;
            for (i = XMI_LOOP_DEPTH - 1; i >= 0; i--) {
                if (seq->loop_counter[i] != -1) break;
            }
            if (i < 0) return;
            if (seq->loop_counter[i] != 0) {
                seq->loop_counter[i]--;
                if (seq->loop_counter[i] == 0) {
                    seq->loop_counter[i] = -1;
                    return;
                }
            }
            seq->ptr = seq->loop_start[i];
            return;
        case 118:
            /* Clear beat/bar count: only feeds beat callbacks. */
            return;
        case 119:
            if (seq->trigger_fn) {
                seq->trigger_fn(seq->trigger_user, seq, (int)channel,
                                (int)data2);
            }
            return;
        default:
            break;
        }
    }
    if (type == 0x90) drv->channel_notes[channel]++;
    else if (type == 0x80) drv->channel_notes[channel]--;
    if (type == 0x90 && seq->log[LOG_MUTE][channel] >= 0x40) return;
    driver_send(drv, status, data1, data2);
}

/* XMI_update_volume */
static void update_volume(struct xmi_sequence *seq)
{
    int channel;

    for (channel = 0; channel < XMI_CHANNELS; channel++) {
        if (seq->log[LOG_VOLUME][channel] != -1) {
            send_channel_voice_message(seq, 0xb0 | (unsigned)channel, 7,
                                       (unsigned)seq->log[LOG_VOLUME][channel],
                                       0);
        }
    }
}

/* XMI_refresh_channel */
static void refresh_channel(struct xmi_sequence *seq, unsigned channel)
{
    static const struct {
        enum log_slot slot;
        unsigned controller;
    } order[] = {
        {LOG_BANK, 114}, {LOG_MUTE, 107}, {LOG_LOCK_PROTECT, 111},
        {LOG_VOICE_PROTECT, 112}, {LOG_MODULATION, 1}, {LOG_VOLUME, 7},
        {LOG_PAN, 10}, {LOG_EXPRESSION, 11}, {LOG_SUSTAIN, 64},
        {LOG_REVERB, 91}, {LOG_CHORUS, 93}, {LOG_BEND_RANGE, 6},
    };
    size_t i;

    if (seq->log[LOG_BANK][channel] != -1) {
        send_channel_voice_message(seq, 0xb0 | channel, 114,
                                   (unsigned)seq->log[LOG_BANK][channel], 0);
    }
    if (seq->log[LOG_PROGRAM][channel] != -1) {
        send_channel_voice_message(seq, 0xc0 | channel,
                                   (unsigned)seq->log[LOG_PROGRAM][channel], 0,
                                   0);
    }
    if (seq->log[LOG_BEND_LSB][channel] != -1) {
        send_channel_voice_message(seq, 0xe0 | channel,
                                   (unsigned)seq->log[LOG_BEND_LSB][channel],
                                   (unsigned)seq->log[LOG_BEND_MSB][channel],
                                   0);
    }
    for (i = 1; i < sizeof(order) / sizeof(order[0]); i++) {
        if (seq->log[order[i].slot][channel] != -1) {
            send_channel_voice_message(seq, 0xb0 | channel,
                                       order[i].controller,
                                       (unsigned)seq->log[order[i].slot][channel],
                                       0);
        }
    }
}

/* XMI_flush_note_queue */
static void flush_note_queue(struct xmi_sequence *seq)
{
    int i;

    for (i = 0; i < XMI_NOTE_QUEUE; i++) {
        if (seq->note_channel[i] != -1) {
            send_channel_voice_message(seq, 0x80 | (unsigned)seq->note_channel[i],
                                       (unsigned)seq->note_number[i], 0, 0);
            seq->note_channel[i] = -1;
        }
    }
    seq->note_count = 0;
}

/* ------------------------------------------------------------------------ */
/* Sequence state                                                           */

/* XMI_init_sequence_state */
static void init_sequence_state(struct xmi_sequence *seq)
{
    int i;

    memset(seq->log, 0xff, sizeof(seq->log));
    for (i = 0; i < XMI_LOOP_DEPTH; i++) {
        seq->loop_counter[i] = -1;
        seq->loop_start[i] = NULL;
    }
    for (i = 0; i < XMI_NOTE_QUEUE; i++) seq->note_channel[i] = -1;
    seq->note_count = 0;
    seq->interval_count = 0;
    seq->interval_num = 0;
    seq->loop_count = 1;
}

static int read_vln(struct xmi_sequence *seq)
{
    int value;
    unsigned char byte;

    value = 0;
    do {
        if (seq->ptr >= seq->evnt_end) return value;
        byte = *seq->ptr++;
        value = (value << 7) | (byte & 0x7f);
    } while (byte & 0x80);
    return value;
}

static int message_size(unsigned status)
{
    switch (status & 0xf0) {
    case 0x80: case 0x90: case 0xa0: case 0xb0: case 0xe0:
        return 3;
    case 0xc0: case 0xd0:
        return 2;
    default:
        return 0;
    }
}

/* AIL_API_stop_sequence */
static void stop_sequence(struct xmi_sequence *seq)
{
    unsigned channel;

    if (seq->status != XMI_SEQ_PLAYING) return;
    seq->status = XMI_SEQ_STOPPED;
    flush_note_queue(seq);
    for (channel = 0; channel < XMI_CHANNELS; channel++) {
        if (seq->log[LOG_SUSTAIN][channel] >= 0x40) {
            driver_send(seq->driver, 0xb0 | channel, 64, 0);
        }
        if (seq->log[LOG_VOICE_PROTECT][channel] >= 0x40) {
            driver_send(seq->driver, 0xb0 | channel, 112, 0);
        }
    }
}

/* Meta event 0x2f reached: loop or finish. Returns 1 when playback stops. */
static int end_of_track(struct xmi_sequence *seq, int length)
{
    if (seq->loop_count == 0 || --seq->loop_count != 0) {
        seq->ptr = seq->evnt_begin;
        return 0;
    }
    stop_sequence(seq);
    seq->status = XMI_SEQ_DONE;
    if (seq->end_fn) seq->end_fn(seq->end_user, seq);
    seq->ptr += length;
    return 1;
}

/* Process events at the current position until the next delay byte. */
static void process_events(struct xmi_sequence *seq, int *done)
{
    unsigned status;
    unsigned type;
    int length;
    int i;
    const unsigned char *p;

    for (;;) {
        if (seq->ptr >= seq->evnt_end) {
            /* Unterminated stream: treat as end of track. */
            *done = end_of_track(seq, 0);
            if (!*done) *done = 1;
            return;
        }
        status = *seq->ptr;
        if (status < 0x80 || *done) return;
        if (status == 0xf0 || status == 0xf7) {
            seq->ptr++;
            length = read_vln(seq);
            seq->ptr += length; /* sysex: no OPL driver consumes it */
            continue;
        }
        if (status == 0xff) {
            p = seq->ptr;
            if (p + 2 > seq->evnt_end) {
                *done = end_of_track(seq, 0);
                if (!*done) *done = 1;
                return;
            }
            type = p[1];
            seq->ptr = p + 2;
            length = read_vln(seq);
            if (seq->ptr + length > seq->evnt_end) length = (int)(seq->evnt_end - seq->ptr);
            if (type == 0x2f) {
                *done = 1;
                if (!end_of_track(seq, length)) {
                    /* Rewound: the next tick restarts from the top. */
                }
                return;
            }
            if (type == 0x51 && length >= 3) {
                seq->file_tempo = ((int)seq->ptr[0] << 16) |
                                  ((int)seq->ptr[1] << 8) | seq->ptr[2];
            }
            seq->ptr += length;
            continue;
        }
        /* Channel voice message. */
        length = message_size(status);
        if (length == 0 || seq->ptr + length > seq->evnt_end) {
            *done = end_of_track(seq, 0);
            if (!*done) *done = 1;
            return;
        }
        p = seq->ptr;
        send_channel_voice_message(seq, status, seq->ptr[1],
                                   length == 3 ? seq->ptr[2] : 0, 1);
        if ((status & 0xf0) == 0x90) {
            /* Note-on: the position cannot have moved. */
            for (i = 0; i < XMI_NOTE_QUEUE; i++) {
                if (seq->note_channel[i] == -1) break;
            }
            if (i == XMI_NOTE_QUEUE) {
                /* "Internal note queue overflow" */
                stop_sequence(seq);
                seq->status = XMI_SEQ_DONE;
                *done = 1;
                return;
            }
            seq->note_count++;
            seq->note_channel[i] = (int)(status & 0x0f);
            seq->note_number[i] = seq->ptr[1];
            seq->ptr += 3;
            seq->note_time[i] = read_vln(seq);
        } else {
            /* XMI_serve re-reads the status byte after the message: when a
             * loop end, branch controller or trigger callback moved the
             * position, it is the event at the new position that gets
             * skipped (XMI_QUIRK_BRANCH_SKIPS_EVENT). Loop starts are the
             * loop controller itself, so those always skip cleanly. */
            if (seq->ptr == p ||
                (seq->driver->quirks & XMI_QUIRK_BRANCH_SKIPS_EVENT) ||
                (seq->ptr < seq->evnt_end && (*seq->ptr & 0xf0) == 0xb0 &&
                 seq->ptr[1] == 116)) {
                if (seq->ptr < seq->evnt_end) {
                    seq->ptr += message_size(*seq->ptr);
                }
            }
        }
    }
}

/* One XMIDI tick of XMI_serve for one sequence. */
static void serve_tick(struct xmi_sequence *seq, int *done)
{
    int i;

    if (seq->note_count > 0) {
        for (i = 0; i < XMI_NOTE_QUEUE; i++) {
            if (seq->note_channel[i] == -1) continue;
            if (--seq->note_time[i] < 1) {
                send_channel_voice_message(seq,
                                           0x80 | (unsigned)seq->note_channel[i],
                                           (unsigned)seq->note_number[i], 0, 0);
                seq->note_channel[i] = -1;
                if (--seq->note_count == 0) break;
            }
        }
    }
    if (--seq->interval_count < 1) {
        process_events(seq, done);
        if (!*done) {
            seq->interval_count = *seq->ptr++;
        }
    }
}

/* XMI_serve, per sequence. */
static void serve_sequence(struct xmi_sequence *seq)
{
    int done;

    if (seq->status != XMI_SEQ_PLAYING) return;
    seq->interval_num++;
    done = 0;
    seq->tempo_error += seq->tempo_percent;
    while (seq->tempo_error >= 100) {
        seq->tempo_error -= 100;
        if (!done) serve_tick(seq, &done);
    }
    if (done) return;
    if (seq->volume != seq->volume_target) {
        seq->volume_accum += seq->driver->interval_us;
        while (seq->volume_accum >= seq->volume_period) {
            seq->volume_accum -= seq->volume_period;
            if (seq->volume < seq->volume_target) seq->volume++;
            else seq->volume--;
            if (seq->volume == seq->volume_target) break;
        }
        if ((seq->interval_num & 7) == 0) update_volume(seq);
    }
    if (seq->tempo_percent != seq->tempo_target) {
        seq->tempo_accum += seq->driver->interval_us;
        while (seq->tempo_accum >= seq->tempo_period) {
            seq->tempo_accum -= seq->tempo_period;
            if (seq->tempo_percent < seq->tempo_target) seq->tempo_percent++;
            else seq->tempo_percent--;
            if (seq->tempo_percent == seq->tempo_target) break;
        }
    }
}

/* AIL_API_branch_index */
static int branch_to(struct xmi_sequence *seq, unsigned index)
{
    unsigned id;
    size_t offset;
    int count;
    int i;

    count = xmi_form_branch_count(&seq->form);
    for (i = 0; i < count; i++) {
        xmi_form_branch(&seq->form, i, &id, &offset);
        if (id != index) continue;
        if (offset >= seq->form.evnt_size) return 0;
        seq->interval_count = 0;
        seq->ptr = seq->evnt_begin + offset;
        /* MDI_ALLOW_LOOP_BRANCHING is off: a branch abandons open loops. */
        for (i = 0; i < XMI_LOOP_DEPTH; i++) seq->loop_counter[i] = -1;
        return 1;
    }
    return 0;
}

/* ------------------------------------------------------------------------ */
/* Public sequence API                                                      */

struct xmi_sequence *xmi_sequence_create(struct xmi_driver *drv)
{
    struct xmi_sequence *seq;

    if (drv == NULL) return NULL;
    seq = calloc(1, sizeof(*seq));
    if (seq == NULL) return NULL;
    seq->driver = drv;
    seq->status = XMI_SEQ_FREE;
    seq->next = drv->sequences;
    drv->sequences = seq;
    init_sequence_state(seq);
    return seq;
}

void xmi_sequence_destroy(struct xmi_sequence *seq)
{
    struct xmi_sequence **link;

    if (seq == NULL) return;
    xmi_sequence_end(seq);
    for (link = &seq->driver->sequences; *link; link = &(*link)->next) {
        if (*link == seq) {
            *link = seq->next;
            break;
        }
    }
    free(seq);
}

int xmi_sequence_init(struct xmi_sequence *seq, const void *data, size_t size,
                      int index)
{
    if (seq == NULL) return 0;
    xmi_sequence_end(seq);
    seq->status = XMI_SEQ_DONE;
    if (!xmi_find_form(data, size, index, &seq->form)) {
        memset(&seq->form, 0, sizeof(seq->form));
        return 0;
    }
    seq->evnt_begin = seq->form.evnt + 8;
    seq->evnt_end = seq->evnt_begin + seq->form.evnt_size;
    seq->ptr = seq->evnt_begin;
    seq->trigger_fn = NULL;
    seq->end_fn = NULL;
    init_sequence_state(seq);
    seq->volume = XMI_DEFAULT_VOLUME;
    seq->volume_target = XMI_DEFAULT_VOLUME;
    seq->volume_accum = 0;
    seq->volume_period = 0;
    seq->tempo_percent = 100;
    seq->tempo_target = 100;
    seq->tempo_accum = 0;
    seq->tempo_period = 0;
    seq->tempo_error = 0;
    seq->file_tempo = 500000;
    return 1;
}

const struct xmi_form *xmi_sequence_form(const struct xmi_sequence *seq)
{
    return seq == NULL || seq->form.evnt == NULL ? NULL : &seq->form;
}

void xmi_sequence_start(struct xmi_sequence *seq)
{
    if (seq == NULL || seq->status == XMI_SEQ_FREE || seq->form.evnt == NULL) return;
    stop_sequence(seq);
    init_sequence_state(seq);
    seq->status = XMI_SEQ_PLAYING;
    seq->ptr = seq->evnt_begin;
}

void xmi_sequence_stop(struct xmi_sequence *seq)
{
    if (seq == NULL) return;
    stop_sequence(seq);
}

void xmi_sequence_resume(struct xmi_sequence *seq)
{
    unsigned channel;

    if (seq == NULL || seq->status != XMI_SEQ_STOPPED) return;
    for (channel = 0; channel < XMI_CHANNELS; channel++) {
        refresh_channel(seq, channel);
    }
    seq->status = XMI_SEQ_PLAYING;
}

void xmi_sequence_end(struct xmi_sequence *seq)
{
    if (seq == NULL || seq->status == XMI_SEQ_FREE) return;
    stop_sequence(seq);
    seq->status = XMI_SEQ_DONE;
}

int xmi_sequence_status(const struct xmi_sequence *seq)
{
    return seq == NULL ? 0 : seq->status;
}

void xmi_sequence_set_volume(struct xmi_sequence *seq, int volume, int ms)
{
    int distance;

    if (seq == NULL) return;
    if (volume < 0) volume = 0;
    if (volume > 127) volume = 127;
    seq->volume_target = volume;
    if (seq->volume == seq->volume_target) return;
    if (ms == 0) {
        seq->volume = seq->volume_target;
    } else {
        distance = seq->volume - seq->volume_target;
        if (distance < 0) distance = -distance;
        seq->volume_accum = 0;
        seq->volume_period = ms * 1000 / distance;
        if (seq->volume_period <= 0) seq->volume = seq->volume_target;
    }
    update_volume(seq);
}

int xmi_sequence_volume(const struct xmi_sequence *seq)
{
    return seq == NULL ? 0 : seq->volume;
}

void xmi_sequence_set_loop_count(struct xmi_sequence *seq, int count)
{
    if (seq) seq->loop_count = count;
}

int xmi_sequence_loop_count(const struct xmi_sequence *seq)
{
    return seq == NULL ? 0 : seq->loop_count;
}

void xmi_sequence_set_tempo(struct xmi_sequence *seq, int percent, int ms)
{
    int distance;

    if (seq == NULL) return;
    seq->tempo_target = percent;
    if (seq->tempo_percent == seq->tempo_target) return;
    if (ms == 0) {
        seq->tempo_percent = seq->tempo_target;
        return;
    }
    distance = seq->tempo_percent - seq->tempo_target;
    if (distance < 0) distance = -distance;
    seq->tempo_accum = 0;
    seq->tempo_period = ms * 1000 / distance;
    if (seq->tempo_period <= 0) seq->tempo_percent = seq->tempo_target;
}

int xmi_sequence_tempo(const struct xmi_sequence *seq)
{
    return seq == NULL ? 0 : seq->tempo_percent;
}

int xmi_sequence_branch(struct xmi_sequence *seq, unsigned index)
{
    if (seq == NULL || seq->form.evnt == NULL) return 0;
    return branch_to(seq, index);
}

void xmi_sequence_set_trigger_callback(struct xmi_sequence *seq,
                                       xmi_trigger_fn fn, void *user)
{
    if (seq == NULL) return;
    seq->trigger_fn = fn;
    seq->trigger_user = user;
}

void xmi_sequence_set_end_callback(struct xmi_sequence *seq,
                                   xmi_sequence_fn fn, void *user)
{
    if (seq == NULL) return;
    seq->end_fn = fn;
    seq->end_user = user;
}

size_t xmi_sequence_position(const struct xmi_sequence *seq)
{
    if (seq == NULL || seq->form.evnt == NULL) return 0;
    return (size_t)(seq->ptr - seq->evnt_begin);
}

int xmi_sequence_queued_notes(const struct xmi_sequence *seq)
{
    return seq == NULL ? 0 : seq->note_count;
}

int xmi_sequence_file_tempo(const struct xmi_sequence *seq)
{
    return seq == NULL ? 0 : seq->file_tempo;
}

/* ------------------------------------------------------------------------ */
/* Driver                                                                   */

struct xmi_driver *xmi_driver_create(xmi_midi_fn midi, void *user)
{
    struct xmi_driver *drv;

    drv = calloc(1, sizeof(*drv));
    if (drv == NULL) return NULL;
    drv->midi = midi;
    drv->midi_user = user;
    drv->master_volume = 127;
    drv->interval_us = 1000000 / XMI_SERVICE_RATE;
    drv->quirks = XMI_QUIRKS_ALL;
    return drv;
}

void xmi_driver_set_quirks(struct xmi_driver *drv, unsigned quirks)
{
    if (drv) drv->quirks = quirks;
}

unsigned xmi_driver_quirks(const struct xmi_driver *drv)
{
    return drv == NULL ? 0 : drv->quirks;
}

void xmi_driver_destroy(struct xmi_driver *drv)
{
    if (drv == NULL) return;
    while (drv->sequences) xmi_sequence_destroy(drv->sequences);
    free(drv);
}

/* XMI_construct_MDI_driver: the controller preset for every channel. */
void xmi_driver_reset(struct xmi_driver *drv)
{
    unsigned ch;

    if (drv == NULL) return;
    memset(drv->channel_notes, 0, sizeof(drv->channel_notes));
    for (ch = 0; ch < XMI_CHANNELS; ch++) {
        driver_send(drv, 0xb0 | ch, 114, 0);
        driver_send(drv, 0xc0 | ch, 0, 0);
        driver_send(drv, 0xe0 | ch, 0, 0x40);
        driver_send(drv, 0xb0 | ch, 112, 0);
        driver_send(drv, 0xb0 | ch, 1, 0);
        driver_send(drv, 0xb0 | ch, 7, XMI_DEFAULT_VOLUME);
        driver_send(drv, 0xb0 | ch, 10, 0x40);
        driver_send(drv, 0xb0 | ch, 11, 0x7f);
        driver_send(drv, 0xb0 | ch, 64, 0);
        driver_send(drv, 0xb0 | ch, 91, 0x28);
        driver_send(drv, 0xb0 | ch, 93, 0);
        driver_send(drv, 0xb0 | ch, 100, 0);
        driver_send(drv, 0xb0 | ch, 101, 0);
        driver_send(drv, 0xb0 | ch, 38, 0);
        driver_send(drv, 0xb0 | ch, 6, XMI_DEFAULT_BEND_RANGE);
    }
}

void xmi_driver_set_master_volume(struct xmi_driver *drv, int volume)
{
    struct xmi_sequence *seq;

    if (drv == NULL || volume == drv->master_volume) return;
    drv->master_volume = volume;
    for (seq = drv->sequences; seq; seq = seq->next) {
        if (seq->status == XMI_SEQ_PLAYING) update_volume(seq);
    }
}

int xmi_driver_master_volume(const struct xmi_driver *drv)
{
    return drv == NULL ? 0 : drv->master_volume;
}

void xmi_driver_serve(struct xmi_driver *drv)
{
    struct xmi_sequence *seq;

    if (drv == NULL || drv->serving) return;
    drv->serving = 1;
    for (seq = drv->sequences; seq; seq = seq->next) serve_sequence(seq);
    drv->serving = 0;
}

int xmi_driver_channel_notes(const struct xmi_driver *drv, int channel)
{
    if (drv == NULL || channel < 0 || channel > 15) return 0;
    return drv->channel_notes[channel];
}

/* ------------------------------------------------------------------------ */
/* Player                                                                   */

struct xmi_player {
    struct miles_opl *synth;
    struct xmi_driver *driver;
    uint32_t sample_rate;
    uint32_t frames_per_tick;
    uint32_t remainder_per_tick;
    uint32_t frames_to_tick;
    uint32_t remainder;
};

static void player_midi(void *user, unsigned status, unsigned data1,
                        unsigned data2)
{
    miles_opl_message(user, status, data1, data2);
}

struct xmi_player *xmi_player_create(uint32_t sample_rate)
{
    struct xmi_player *player;

    if (sample_rate < XMI_SERVICE_RATE) return NULL;
    player = calloc(1, sizeof(*player));
    if (player == NULL) return NULL;
    player->synth = miles_opl_create(sample_rate);
    player->driver = player->synth
        ? xmi_driver_create(player_midi, player->synth) : NULL;
    if (player->driver == NULL) {
        xmi_player_destroy(player);
        return NULL;
    }
    player->sample_rate = sample_rate;
    player->frames_per_tick = sample_rate / XMI_SERVICE_RATE;
    player->remainder_per_tick = sample_rate % XMI_SERVICE_RATE;
    player->frames_to_tick = 0;
    xmi_driver_reset(player->driver);
    return player;
}

void xmi_player_destroy(struct xmi_player *player)
{
    if (player == NULL) return;
    xmi_driver_destroy(player->driver);
    miles_opl_destroy(player->synth);
    free(player);
}

struct xmi_driver *xmi_player_driver(struct xmi_player *player)
{
    return player == NULL ? NULL : player->driver;
}

struct miles_opl *xmi_player_synth(struct xmi_player *player)
{
    return player == NULL ? NULL : player->synth;
}

int xmi_player_load_bank(struct xmi_player *player, const void *data,
                         size_t size)
{
    if (player == NULL) return 0;
    return miles_opl_load_bank(player->synth, data, size);
}

void xmi_player_render(struct xmi_player *player, int16_t *stereo,
                       size_t frames)
{
    size_t chunk;

    if (player == NULL || stereo == NULL) return;
    while (frames > 0) {
        if (player->frames_to_tick == 0) {
            xmi_driver_serve(player->driver);
            player->frames_to_tick = player->frames_per_tick;
            player->remainder += player->remainder_per_tick;
            if (player->remainder >= XMI_SERVICE_RATE) {
                player->remainder -= XMI_SERVICE_RATE;
                player->frames_to_tick++;
            }
        }
        chunk = frames < player->frames_to_tick ? frames
                                                : player->frames_to_tick;
        miles_opl_render(player->synth, stereo, chunk);
        stereo += chunk * 2;
        frames -= chunk;
        player->frames_to_tick -= (uint32_t)chunk;
    }
}
