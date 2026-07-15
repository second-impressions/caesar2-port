"""get_number_from_text — byte-load + LEA-subtract idiom in multiply leg.

PS pattern (3-row block at the multiply leg):

    xor ebx, ebx              ; 2 bytes
    mov bl, byte ptr [eax]    ; 2 bytes
    dec edx
    lea esi, [ebx - 0x30]     ; 3 bytes  ← LEA-form subtraction
    imul esi, [edx*4 + multiples]

RC pattern:

    dec edx
    movzx esi, byte ptr [eax] ; 3 bytes
    sub esi, 0x30             ; 3 bytes
    imul esi, [edx*4 + multiples]

Both produce the same semantic value but PS keeps EBX live across the
LEA (loads byte into EBX, then subtracts 0x30 into ESI), which is a
2-register live-range expansion.  RC fuses the load+subtract into ESI.

The goal: discover what C source shape forces Watcom to emit the
`xor ebx,ebx; mov bl,[eax]; lea esi,[ebx-0x30]` triple instead of the
`movzx esi,[eax]; sub esi,0x30` pair.
"""
from c2.commands.cgex import Experiment

_PRELUDE = r"""
extern int multiples[];
"""
_DEFS = r"""
int multiples[10];
"""

exp = Experiment(
    name="get_number_from_text",
    ps_function="get_number_from_text",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

exp.add("baseline_int_cast", r"""
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        int d;
        digits = digits - 1;
        d = (unsigned char)*p;
        total = total + (d - '0') * multiples[digits];
        p = p + 1;
    }
    return total;
}
""", note="current 26 b")

exp.add("inline_unsigned_cast", r"""
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        digits = digits - 1;
        total = total + ((unsigned char)*p - '0') * multiples[digits];
        p = p + 1;
    }
    return total;
}
""", note="inline (unsigned char) — no temp")

exp.add("uchar_temp", r"""
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        unsigned char d;
        digits = digits - 1;
        d = *p;
        total = total + (d - '0') * multiples[digits];
        p = p + 1;
    }
    return total;
}
""", note="unsigned char local")

exp.add("orig_char_arith", r"""
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        digits = digits - 1;
        total = total + (*p - '0') * multiples[digits];
        p = p + 1;
    }
    return total;
}
""", note="original char arith (no cast)")

exp.add("d_then_subexpr", r"""
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;
    int d;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        digits = digits - 1;
        d = (unsigned char)*p;
        d = d - '0';
        total = total + d * multiples[digits];
        p = p + 1;
    }
    return total;
}
""", note="split d - '0' into separate stmt")

exp.add("d_hoisted_uchar", r"""
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;
    unsigned char d;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        digits = digits - 1;
        d = *p;
        total = total + (d - '0') * multiples[digits];
        p = p + 1;
    }
    return total;
}
""", note="hoist `unsigned char d` out of loop")

exp.add("d_hoisted_int", r"""
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;
    int d;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        digits = digits - 1;
        d = (unsigned char)*p;
        total = total + (d - '0') * multiples[digits];
        p = p + 1;
    }
    return total;
}
""", note="hoist `int d` out of loop")

exp.add("paren_explicit", r"""
int get_number_from_text(char *text)
{
    char *p;
    int total;
    int digits;

    p = text;
    total = 0;
    digits = 0;
    while (*p >= '0' && *p <= '9') {
        digits = digits + 1;
        p = p + 1;
    }
    p = text;
    while (digits != 0) {
        int d;
        digits = digits - 1;
        d = (unsigned char)(*p) - '0';
        total = total + d * multiples[digits];
        p = p + 1;
    }
    return total;
}
""", note="d holds the subtracted value")
