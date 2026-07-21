#include <assert.h>
#include <string.h>

#include "c2_port_keymap.h"

static void expect_text(uint32_t codepoint, unsigned char expected)
{
    struct c2_host_event event;
    unsigned char ascii;
    unsigned char scan_code;

    memset(&event, 0, sizeof(event));
    event.type = C2_HOST_EVENT_TEXT_INPUT;
    event.codepoint = codepoint;
    assert(c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
    assert(ascii == expected);
    assert(scan_code == 0);
}

static void expect_control(enum c2_host_key key, unsigned char expected_ascii,
                           unsigned char expected_scan_code)
{
    struct c2_host_event event;
    unsigned char ascii;
    unsigned char scan_code;

    memset(&event, 0, sizeof(event));
    event.type = C2_HOST_EVENT_KEY_DOWN;
    event.key = key;
    assert(c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
    assert(ascii == expected_ascii);
    assert(scan_code == expected_scan_code);
}

int main(void)
{
    struct c2_host_event event;
    unsigned char ascii;
    unsigned char scan_code;

    expect_text('A', 'A');
    expect_text('z', 'z');
    expect_text(' ', ' ');
    expect_text(0x00e4, 0x84);
    expect_text(0x00e9, 0x82);
    expect_text(0x00f1, 0xa4);
    expect_text(0x00df, 0xe1);

    expect_control(C2_HOST_KEY_ESCAPE, 0x1b, 0);
    expect_control(C2_HOST_KEY_RETURN, 0x0d, 0);
    expect_control(C2_HOST_KEY_BACKSPACE, 0x08, 0);
    expect_control(C2_HOST_KEY_DELETE, 0, 0x53);
    expect_control(C2_HOST_KEY_INSERT, 0, 0x52);
    expect_control(C2_HOST_KEY_HOME, 0, 0x47);
    expect_control(C2_HOST_KEY_END, 0, 0x4f);
    expect_control(C2_HOST_KEY_LEFT, 0, 0x4b);
    expect_control(C2_HOST_KEY_RIGHT, 0, 0x4d);
    expect_control(C2_HOST_KEY_UP, 0, 0x48);
    expect_control(C2_HOST_KEY_DOWN, 0, 0x50);

    memset(&event, 0, sizeof(event));
    event.type = C2_HOST_EVENT_TEXT_INPUT;
    event.codepoint = 0x20ac;
    assert(!c2_port_event_to_legacy_key(&event, &ascii, &scan_code));

    event.type = C2_HOST_EVENT_KEY_DOWN;
    event.key = C2_HOST_KEY_UNKNOWN;
    assert(!c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
    return 0;
}
