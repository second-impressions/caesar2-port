#include "c2_bugfixes.h"

#if C2_FIX_HELP_SMART_PUNCTUATION
static int is_ascii_letter(unsigned char character)
{
    return (character >= 'A' && character <= 'Z') ||
           (character >= 'a' && character <= 'z');
}

static unsigned char fix_help_character(unsigned char previous,
                                        unsigned char character,
                                        unsigned char next)
{
    if ((character == 0x91 || character == 0x92) &&
        is_ascii_letter(previous) && is_ascii_letter(next)) {
        return '\'';
    }
    if ((character == 0x96 || character == 0x97) &&
        previous == ' ' && next == ' ') {
        return '-';
    }
    return character;
}
#endif

void c2_fix_help_text(char *text, int length)
{
#if C2_FIX_HELP_SMART_PUNCTUATION
    int i;

    for (i = 1; i + 1 < length; i++) {
        text[i] = (char)fix_help_character((unsigned char)text[i - 1],
                                           (unsigned char)text[i],
                                           (unsigned char)text[i + 1]);
    }
#else
    (void)text;
    (void)length;
#endif
}

void c2_fix_player_name_padding(char *name, int capacity)
{
#if C2_FIX_PLAYER_NAME_PADDING
    int length;

    length = 0;
    while (length < capacity && name[length] != '\0') length++;
    while (length > 0 && name[length - 1] == ' ') length--;
    if (length < capacity) name[length] = '\0';
#else
    (void)name;
    (void)capacity;
#endif
}
