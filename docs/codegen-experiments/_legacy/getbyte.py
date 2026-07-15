"""GetByte — `xor ch, ch` (16-bit zero-extend) vs recomp `xor ecx, ecx`.

PS loads the shift count `8 - getlen` keeping it 16-bit (`xor ch,ch;
mov cl,[getlen]`), recomp clears the full 32-bit reg (`xor ecx,ecx`).
Find the source shape for the 16-bit zero-extension.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="getbyte",
    ps_function="GetByte",
    extra_defs="""
short getbuf;
char getlen;
int pmp_iptr;
unsigned char *pmp_inbuff;
""",
    prelude="""
extern short getbuf;
extern char getlen;
extern int pmp_iptr;
extern unsigned char *pmp_inbuff;
""",
)

exp.add(
    "baseline",
    """
int GetByte(void)
{
    short i;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    {
        short tmp = getbuf; int old;
        getbuf = (short)(tmp << 8);
        old = (int)(unsigned short)tmp;
        getlen -= 8;
        return old >> 8;
    }
}
""",
    note="current source",
)

exp.add(
    "short_shift",
    """
int GetByte(void)
{
    short i;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        short sh;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        sh = (short)(8 - getlen);
        getbuf |= (short)(i << sh);
        getlen += 8;
    }
    {
        short tmp = getbuf; int old;
        getbuf = (short)(tmp << 8);
        old = (int)(unsigned short)tmp;
        getlen -= 8;
        return old >> 8;
    }
}
""",
    note="shift count via short local",
)

exp.add(
    "short_return",
    """
short GetByte(void)
{
    short i;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= (short)(i << (8 - getlen));
        getlen += 8;
    }
    {
        short tmp = getbuf; int old;
        getbuf = (short)(tmp << 8);
        old = (int)(unsigned short)tmp;
        getlen -= 8;
        return old >> 8;
    }
}
""",
    note="short return type line-shape probe",
)

exp.add(
    "short_i_shift",
    """
int GetByte(void)
{
    short i;
    while (getlen <= 8) {
        int idx; unsigned char *p;
        idx = pmp_iptr; p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        i = (short)(i << (short)(8 - getlen));
        getbuf |= i;
        getlen += 8;
    }
    {
        short tmp = getbuf; int old;
        getbuf = (short)(tmp << 8);
        old = (int)(unsigned short)tmp;
        getlen -= 8;
        return old >> 8;
    }
}
""",
    note="shift into i (short) then OR",
)
