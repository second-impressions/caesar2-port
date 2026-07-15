"""GetBit (pump.c) — partial-register (8/16-bit) vs 32-bit char arithmetic.

PS.EXE `GetBit` (110 b) does the LHARC bit-buffer refill using 8/16-bit
partial-register ops:

    mov al, [pmp_inbuff + idx] ; xor ah, ah    ; i = (byte) zero-extended to AX
    ... shift by (8 - getlen) in CL ...
    xor ch, ch                                  ; getlen kept in CL (char)

Our build promotes everything to 32-bit (`and eax,0xff`, `xor ecx,ecx`),
giving a 63 b diff.  `getlen` is `char` and `getbuf` is `short`, so PS
keeps the arithmetic narrow; we want the same.  This experiment bisects
the local `i`'s type / cast shape.

Run::  uv run c2 cgex run get_bit
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern short getbuf;
extern char getlen;
extern int pmp_iptr;
extern unsigned char *pmp_inbuff;
"""

_DEFS = """
short getbuf;
char getlen;
int pmp_iptr;
unsigned char *pmp_inbuff;
"""

exp = Experiment(
    name="get_bit",
    ps_function="GetBit",
    externs={},
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

exp.add("baseline", """
int GetBit(void)
{
    int i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="current source (int i)")

exp.add("short-i", """
int GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="short i")

exp.add("uchar-i", """
int GetBit(void)
{
    unsigned char i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="unsigned char i")

exp.add("ushort-i", """
int GetBit(void)
{
    unsigned short i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="unsigned short i")

exp.add("short-i-shift", """
int GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        i = (short)(i << (8 - getlen));
        getbuf |= i;
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="short i, shift into i then |=")


def _body(ret):
    return """
int GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    """ + ret + """
}
"""

exp.add("ret-ternary", _body("return t < 0 ? 1 : 0;"), note="ternary return")
exp.add("ret-ushort", _body("return (unsigned short)(t < 0);"), note="(unsigned short) cast")
exp.add("ret-shift", _body("return (getbuf >> 1) & 1;"), note="bit extract (wrong? test)")
exp.add("ret-and", _body("return (t & 0x8000) != 0;"), note="(t & 0x8000) != 0")
exp.add("ret-short-tmp", _body("{ short r = (t < 0); return r; }"), note="short r temp")
exp.add("ret-uchar", _body("return (unsigned char)(t < 0);"), note="(unsigned char) cast")

exp.add("short-return", """
short GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="short return type probe from line-shape return zext")

exp.add("ushort-return", """
unsigned short GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="unsigned short return type probe")

exp.add("short-return-short-shift", """
short GetBit(void)
{
    short i;
    short t;
    short sh;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        sh = 8 - getlen;
        getbuf |= (short)(i << sh);
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="short return + named short shift")

exp.add("short-return-uchar-cast-len", """
short GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - (unsigned char)getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="short return + unsigned-char getlen cast")

exp.add("short-return-short-cast-len", """
short GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - (short)getlen));
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="short return + short getlen cast")
