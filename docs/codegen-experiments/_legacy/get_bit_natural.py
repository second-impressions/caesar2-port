"""GetBit — cast-free classic LZHUF with getbuf=unsigned short."""

from c2.commands.cgex import Experiment

_DEFS = """
unsigned short getbuf;
unsigned char getlen;
int pmp_iptr;
unsigned char *pmp_inbuff;
"""
_PRELUDE = """
extern unsigned short getbuf;
extern unsigned char getlen;
extern int pmp_iptr;
extern unsigned char *pmp_inbuff;
"""

exp = Experiment(
    name="get_bit_natural", ps_function="GetBit",
    extra_defs=_DEFS, prelude=_PRELUDE,
)

# Classic LZHUF GetBit: short i shared as buffer, getbuf<<=1, return (i<0).
exp.add("classic", """
int GetBit(void)
{
    short i;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= i << (8 - getlen);
        getlen += 8;
    }
    i = getbuf;
    getbuf <<= 1;
    getlen--;
    return (i < 0);
}
""", note="classic: short i, no casts, getbuf<<=1, return (i<0)")

# variant: separate t (current var naming), still cast-free
exp.add("classic_t", """
int GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= i << (8 - getlen);
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    return (t < 0);
}
""", note="short i + short t, cast-free")

def ret(expr):
    return """
int GetBit(void)
{
    short i;
    short t;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= i << (8 - getlen);
        getlen += 8;
    }
    t = getbuf;
    getbuf <<= 1;
    getlen--;
    """ + expr + """
}
"""

exp.add("ret_ushort", ret("return (unsigned short)(t < 0);"), note="(unsigned short)(t<0)")
exp.add("ret_short", ret("return (short)(t < 0);"), note="(short)(t<0)")
exp.add("ret_signbit", ret("return (unsigned short)t >> 15;"), note="(unsigned short)t>>15")
exp.add("ret_and_word", ret("return (t < 0) & 0xffff;"), note="(t<0)&0xffff")
exp.add("ret_via_short", ret("{ short r; r = (t < 0); return r; }"), note="short r=(t<0)")
exp.add("ret_t_ushort_cmp", ret("return ((unsigned short)t & 0x8000) != 0;"), note="(ushort t & 0x8000)!=0")
exp.add("ret_neg", ret("return t < 0 ? 1 : 0;"), note="ternary")

exp.add("ret_if", ret("if (t < 0) return 1; return 0;"), note="if(t<0)return 1;return 0")
exp.add("ret_ifelse", ret("if (t < 0) return 1; else return 0;"), note="if/else")
exp.add("ret_notnot", ret("return !!(t & 0x8000);"), note="!!(t&0x8000)")
exp.add("ret_ushort_t_shr", ret("return ((unsigned short)t) >> 15;"), note="(ushort)t>>15")
exp.add("ret_logical", ret("return t < 0;"), note="t<0 no parens")
exp.add("ret_minus", ret("return (t < 0) ? 1 : 0;"), note="ternary 2")
exp.add("ret_int_i_buf", """
int GetBit(void)
{
    short i;
    int r;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= i << (8 - getlen);
        getlen += 8;
    }
    i = getbuf;
    getbuf <<= 1;
    getlen--;
    r = (i < 0);
    return r;
}
""", note="int r=(i<0);return r")
exp.add("ret_and1", ret("return (t < 0) & 1;"), note="(t<0)&1")

exp.add("short_ret", """
short GetBit(void)
{
    short i;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= i << (8 - getlen);
        getlen += 8;
    }
    i = getbuf;
    getbuf <<= 1;
    getlen--;
    return (i < 0);
}
""", note="short GetBit(void) return type")
exp.add("ushort_ret", """
unsigned short GetBit(void)
{
    short i;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= i << (8 - getlen);
        getlen += 8;
    }
    i = getbuf;
    getbuf <<= 1;
    getlen--;
    return (i < 0);
}
""", note="unsigned short GetBit(void) return type")
