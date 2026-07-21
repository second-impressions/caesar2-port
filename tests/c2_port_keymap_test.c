#include <unity/unity.h>
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
    TEST_ASSERT_TRUE(c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
    TEST_ASSERT_TRUE(ascii == expected);
    TEST_ASSERT_TRUE(scan_code == 0);
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
    TEST_ASSERT_TRUE(c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
    TEST_ASSERT_TRUE(ascii == expected_ascii);
    TEST_ASSERT_TRUE(scan_code == expected_scan_code);
}

static void expect_modified_control(enum c2_host_key key,
                                    unsigned int modifiers,
                                    unsigned char expected_scan_code)
{
    struct c2_host_event event;
    unsigned char ascii;
    unsigned char scan_code;

    memset(&event, 0, sizeof(event));
    event.type = C2_HOST_EVENT_KEY_DOWN;
    event.key = key;
    event.key_modifiers = modifiers;
    TEST_ASSERT_TRUE(c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
    TEST_ASSERT_EQUAL_UINT8(0, ascii);
    TEST_ASSERT_EQUAL_UINT8(expected_scan_code, scan_code);
}

static void test_printable_text(void)
{
    expect_text('A', 'A');
    expect_text('z', 'z');
    expect_text(' ', ' ');
    expect_text(0x00e4, 0x84);
    expect_text(0x00e9, 0x82);
    expect_text(0x00f1, 0xa4);
    expect_text(0x00df, 0xe1);
}

static void test_editor_controls(void)
{
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
    expect_control(C2_HOST_KEY_F1, 0, 0x3b);
    expect_control(C2_HOST_KEY_F2, 0, 0x3c);
    expect_control(C2_HOST_KEY_F3, 0, 0x3d);
    expect_control(C2_HOST_KEY_F4, 0, 0x3e);
    expect_control(C2_HOST_KEY_F5, 0, 0x3f);
}

static void test_alt_hotkeys(void)
{
    enum c2_host_key digits[8] = {
        C2_HOST_KEY_1, C2_HOST_KEY_2, C2_HOST_KEY_3, C2_HOST_KEY_4,
        C2_HOST_KEY_5, C2_HOST_KEY_6, C2_HOST_KEY_7, C2_HOST_KEY_8
    };
    size_t i;

    expect_modified_control(C2_HOST_KEY_F, C2_HOST_KEY_MODIFIER_ALT, 0x21);
    expect_modified_control(C2_HOST_KEY_F1, C2_HOST_KEY_MODIFIER_ALT, 0x68);
    expect_modified_control(C2_HOST_KEY_F3, C2_HOST_KEY_MODIFIER_ALT, 0x6a);
    expect_modified_control(C2_HOST_KEY_D, C2_HOST_KEY_MODIFIER_ALT, 0x20);
    expect_modified_control(C2_HOST_KEY_X, C2_HOST_KEY_MODIFIER_ALT, 0x2d);
    for (i = 0; i < 8; i++) {
        expect_modified_control(digits[i], C2_HOST_KEY_MODIFIER_ALT,
                                (unsigned char)(0x78 + i));
    }
}

static void test_mouse_wheel_zoom(void)
{
    struct c2_host_event event;
    unsigned char ascii;
    unsigned char scan_code;

    memset(&event, 0, sizeof(event));
    event.type = C2_HOST_EVENT_MOUSE_WHEEL;
    event.wheel_y = 1;
    TEST_ASSERT_TRUE(c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
    TEST_ASSERT_EQUAL_UINT8('+', ascii);
    TEST_ASSERT_EQUAL_UINT8(0, scan_code);
    event.wheel_y = -1;
    TEST_ASSERT_TRUE(c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
    TEST_ASSERT_EQUAL_UINT8('-', ascii);
    TEST_ASSERT_EQUAL_UINT8(0, scan_code);
    event.wheel_y = 0;
    TEST_ASSERT_FALSE(c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
}

static void test_unsupported_input(void)
{
    struct c2_host_event event;
    unsigned char ascii;
    unsigned char scan_code;

    memset(&event, 0, sizeof(event));
    event.type = C2_HOST_EVENT_TEXT_INPUT;
    event.codepoint = 0x20ac;
    TEST_ASSERT_TRUE(!c2_port_event_to_legacy_key(&event, &ascii, &scan_code));

    event.type = C2_HOST_EVENT_KEY_DOWN;
    event.key = C2_HOST_KEY_UNKNOWN;
    TEST_ASSERT_TRUE(!c2_port_event_to_legacy_key(&event, &ascii, &scan_code));
}

int main(void)
{
    UNITY_BEGIN();
    RUN_TEST(test_printable_text);
    RUN_TEST(test_editor_controls);
    RUN_TEST(test_alt_hotkeys);
    RUN_TEST(test_mouse_wheel_zoom);
    RUN_TEST(test_unsupported_input);
    return UNITY_END();
}
