#include <stdint.h>
#include <string.h>

#include <adlmidi.h>

#include "c2_port_miles_bank.h"

static uint32_t read_u32_le(const unsigned char *bytes)
{
    return (uint32_t)bytes[0] |
           ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) |
           ((uint32_t)bytes[3] << 24);
}

static void set_operator(ADL_Operator *operator,
                         const unsigned char *registers)
{
    operator->avekf_20 = registers[0];
    operator->ksl_l_40 = registers[1];
    operator->atdec_60 = registers[2];
    operator->susrel_80 = registers[3];
    operator->waveform_E0 = registers[4];
}

int c2_port_apply_miles_bank(struct ADL_MIDIPlayer *player,
                             const unsigned char *data, size_t data_size)
{
    ADL_Bank bank;
    ADL_BankId bank_id;
    ADL_Instrument instrument;
    const unsigned char *entry;
    const unsigned char *voice;
    size_t entry_offset;
    size_t instrument_offset;
    unsigned int voice_count;
    unsigned int voice_index;
    int loaded;
    uint16_t instrument_length;
    signed char note_offset;

    if (player == NULL || data == NULL) return 0;
    loaded = 0;
    for (entry_offset = 0; entry_offset + 6 <= data_size;
         entry_offset += 6) {
        entry = data + entry_offset;
        if (entry[0] == 0xff || entry[1] == 0xff) break;
        if (entry[0] > 127) return 0;
        instrument_offset = (size_t)read_u32_le(entry + 2);
        if (instrument_offset > data_size ||
            data_size - instrument_offset < 3) {
            return 0;
        }
        instrument_length = (uint16_t)data[instrument_offset] |
                            ((uint16_t)data[instrument_offset + 1] << 8);
        if (instrument_length < 14 ||
            (instrument_length - 3) % 11 != 0 ||
            instrument_length > data_size - instrument_offset) {
            return 0;
        }
        voice_count = (instrument_length - 3) / 11;
        if (voice_count == 0 || voice_count > 2) return 0;

        bank_id.percussive = entry[1] == 0x7f;
        bank_id.msb = 0;
        bank_id.lsb = bank_id.percussive ? 0 : entry[1];
        if (adl_getBank(player, &bank_id, ADLMIDI_Bank_Create, &bank) < 0 ||
            adl_getInstrument(player, &bank, entry[0], &instrument) < 0) {
            return 0;
        }

        note_offset = (signed char)data[instrument_offset + 2];
        instrument.version = ADLMIDI_InstrumentVersion;
        instrument.note_offset1 = bank_id.percussive ? 0 : note_offset;
        instrument.note_offset2 = 0;
        instrument.midi_velocity_offset = 0;
        instrument.second_voice_detune = 0;
        instrument.percussion_key_number = bank_id.percussive ?
                                               (unsigned char)note_offset : 0;
        instrument.inst_flags = voice_count == 2 ? ADLMIDI_Ins_4op :
                                                   ADLMIDI_Ins_2op;
        instrument.fb_conn1_C0 = data[instrument_offset + 8];
        instrument.fb_conn2_C0 = 0;
        if (voice_count == 2) {
            instrument.fb_conn1_C0 &= 0x0f;
            instrument.fb_conn2_C0 =
                (unsigned char)((data[instrument_offset + 8] & 0x0e) |
                                (data[instrument_offset + 8] >> 7));
        }
        memset(instrument.operators, 0, sizeof(instrument.operators));
        for (voice_index = 0; voice_index < voice_count; voice_index++) {
            voice = data + instrument_offset + 3 + voice_index * 11;
            set_operator(&instrument.operators[voice_index * 2], voice + 6);
            set_operator(&instrument.operators[voice_index * 2 + 1], voice);
        }
        if (adl_setInstrument(player, &bank, entry[0], &instrument) < 0) {
            return 0;
        }
        loaded++;
    }
    return loaded > 0;
}
