#include "c2_bugfixes.h"

#include <assert.h>

int main(void)
{
    char text[] = "city\x92s don\x91t x \x97 y x \x96 y o\x97 C\x92 ";

    c2_fix_help_text(text, sizeof(text));

#if C2_FIX_HELP_SMART_PUNCTUATION
    assert(text[4] == '\'');
    assert(text[10] == '\'');
    assert(text[15] == '-');
    assert(text[21] == '-');
#else
    assert((unsigned char)text[4] == 0x92);
    assert((unsigned char)text[10] == 0x91);
    assert((unsigned char)text[15] == 0x97);
    assert((unsigned char)text[21] == 0x96);
#endif

    /* These byte values are letters in the DOS code pages used by the
     * localized assets and must remain untouched inside words. */
    assert((unsigned char)text[26] == 0x97);
    assert((unsigned char)text[29] == 0x92);
    return 0;
}
