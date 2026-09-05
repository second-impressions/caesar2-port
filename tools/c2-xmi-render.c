/*
 * Render an XMIDI score through the port's Miles OPL3 driver to a WAV file.
 *
 *   c2-xmi-render BANK.OPL SCORE.XMI OUT.WAV [seconds] [branch]
 *
 * With a branch number, every callback trigger jumps back to that branch, so
 * one section of the city/battle score can be rendered in isolation; without
 * one, triggers jump to the branch id given by the trigger's own value, which
 * approximates the game's mood loop without its randomness.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "xmidi/xmidi.h"

static unsigned char *read_file(const char *path, size_t *size)
{
    FILE *file;
    unsigned char *data;
    long length;

    file = fopen(path, "rb");
    if (file == NULL) return NULL;
    fseek(file, 0, SEEK_END);
    length = ftell(file);
    fseek(file, 0, SEEK_SET);
    data = malloc((size_t)length);
    if (data == NULL || fread(data, 1, (size_t)length, file) != (size_t)length) {
        free(data);
        fclose(file);
        return NULL;
    }
    fclose(file);
    *size = (size_t)length;
    return data;
}

static void write_le32(FILE *f, unsigned v)
{
    fputc(v & 0xff, f); fputc((v >> 8) & 0xff, f);
    fputc((v >> 16) & 0xff, f); fputc((v >> 24) & 0xff, f);
}

static void write_le16(FILE *f, unsigned v)
{
    fputc(v & 0xff, f); fputc((v >> 8) & 0xff, f);
}

static int fixed_branch = -1;
static int triggers;

static void on_trigger(void *user, struct xmi_sequence *seq, int channel,
                       int value)
{
    (void)user;
    (void)channel;
    triggers++;
    xmi_sequence_branch(seq, fixed_branch >= 0 ? (unsigned)fixed_branch
                                               : (unsigned)value);
}

int main(int argc, char **argv)
{
    struct xmi_player *player;
    struct xmi_sequence *seq;
    unsigned char *bank;
    unsigned char *xmi;
    size_t bank_size;
    size_t xmi_size;
    int seconds;
    unsigned rate;
    unsigned frames;
    int16_t buffer[1024 * 2];
    FILE *out;
    unsigned done;
    unsigned chunk;

    if (argc < 4) {
        fprintf(stderr, "usage: %s BANK.OPL SCORE.XMI OUT.WAV [seconds] [branch]\n",
                argv[0]);
        return 2;
    }
    seconds = argc > 4 ? atoi(argv[4]) : 30;
    if (argc > 5) fixed_branch = atoi(argv[5]);
    bank = read_file(argv[1], &bank_size);
    xmi = read_file(argv[2], &xmi_size);
    if (bank == NULL || xmi == NULL) {
        fprintf(stderr, "could not read inputs\n");
        return 1;
    }
    rate = 44100;
    player = xmi_player_create(rate);
    if (player == NULL || xmi_player_load_bank(player, bank, bank_size) == 0) {
        fprintf(stderr, "could not load bank\n");
        return 1;
    }
    seq = xmi_sequence_create(xmi_player_driver(player));
    if (!xmi_sequence_init(seq, xmi, xmi_size, 0)) {
        fprintf(stderr, "not an XMIDI file\n");
        return 1;
    }
    xmi_sequence_set_trigger_callback(seq, on_trigger, NULL);
    xmi_sequence_start(seq);
    out = fopen(argv[3], "wb");
    if (out == NULL) return 1;
    frames = rate * (unsigned)seconds;
    fwrite("RIFF", 1, 4, out);
    write_le32(out, 36 + frames * 4);
    fwrite("WAVEfmt ", 1, 8, out);
    write_le32(out, 16);
    write_le16(out, 1);
    write_le16(out, 2);
    write_le32(out, rate);
    write_le32(out, rate * 4);
    write_le16(out, 4);
    write_le16(out, 16);
    fwrite("data", 1, 4, out);
    write_le32(out, frames * 4);
    for (done = 0; done < frames; done += chunk) {
        chunk = frames - done < 1024 ? frames - done : 1024;
        xmi_player_render(player, buffer, chunk);
        fwrite(buffer, 4, chunk, out);
    }
    fclose(out);
    fprintf(stderr, "%s: status %d, %d triggers, tempo %d\n", argv[2],
            xmi_sequence_status(seq), triggers, xmi_sequence_file_tempo(seq));
    xmi_player_destroy(player);
    free(bank);
    free(xmi);
    return 0;
}
