#include <stddef.h>

#include "c2_port_keymap.h"

struct c2_codepage_pair {
    uint32_t codepoint;
    unsigned char byte;
};

/* Characters accepted by the recovered name editor outside ASCII. */
static const struct c2_codepage_pair c2_cp850_characters[] = {
    { 0x00c7, 0x80 }, { 0x00fc, 0x81 }, { 0x00e9, 0x82 },
    { 0x00e2, 0x83 }, { 0x00e4, 0x84 }, { 0x00e0, 0x85 },
    { 0x00e5, 0x86 }, { 0x00e7, 0x87 }, { 0x00ea, 0x88 },
    { 0x00eb, 0x89 }, { 0x00e8, 0x8a }, { 0x00ef, 0x8b },
    { 0x00ee, 0x8c }, { 0x00ec, 0x8d }, { 0x00c4, 0x8e },
    { 0x00c5, 0x8f }, { 0x00c9, 0x90 }, { 0x00e6, 0x91 },
    { 0x00c6, 0x92 }, { 0x00f4, 0x93 }, { 0x00f6, 0x94 },
    { 0x00f2, 0x95 }, { 0x00fb, 0x96 }, { 0x00f9, 0x97 },
    { 0x00ff, 0x98 }, { 0x00d6, 0x99 }, { 0x00dc, 0x9a },
    { 0x00e1, 0xa0 }, { 0x00ed, 0xa1 }, { 0x00f3, 0xa2 },
    { 0x00fa, 0xa3 }, { 0x00f1, 0xa4 }, { 0x00d1, 0xa5 },
    { 0x00aa, 0xa6 }, { 0x00ba, 0xa7 }, { 0x00df, 0xe1 }
};

static int encode_text(uint32_t codepoint, unsigned char *ascii)
{
    size_t i;

    if (codepoint >= 0x20 && codepoint <= 0x7e) {
        *ascii = (unsigned char)codepoint;
        return 1;
    }
    for (i = 0; i < sizeof(c2_cp850_characters) /
                        sizeof(c2_cp850_characters[0]); i++) {
        if (c2_cp850_characters[i].codepoint == codepoint) {
            *ascii = c2_cp850_characters[i].byte;
            return 1;
        }
    }
    return 0;
}

int c2_port_event_to_legacy_key(const struct c2_host_event *event,
                                unsigned char *ascii,
                                unsigned char *scan_code)
{
    *ascii = 0;
    *scan_code = 0;

    if (event->type == C2_HOST_EVENT_TEXT_INPUT) {
        return encode_text(event->codepoint, ascii);
    }
    if (event->type != C2_HOST_EVENT_KEY_DOWN) return 0;

    switch (event->key) {
    case C2_HOST_KEY_ESCAPE:    *ascii = 0x1b; return 1;
    case C2_HOST_KEY_RETURN:    *ascii = 0x0d; return 1;
    case C2_HOST_KEY_BACKSPACE: *ascii = 0x08; return 1;
    case C2_HOST_KEY_DELETE:    *scan_code = 0x53; return 1;
    case C2_HOST_KEY_INSERT:    *scan_code = 0x52; return 1;
    case C2_HOST_KEY_HOME:      *scan_code = 0x47; return 1;
    case C2_HOST_KEY_END:       *scan_code = 0x4f; return 1;
    case C2_HOST_KEY_LEFT:      *scan_code = 0x4b; return 1;
    case C2_HOST_KEY_RIGHT:     *scan_code = 0x4d; return 1;
    case C2_HOST_KEY_UP:        *scan_code = 0x48; return 1;
    case C2_HOST_KEY_DOWN:      *scan_code = 0x50; return 1;
    default: return 0;
    }
}
