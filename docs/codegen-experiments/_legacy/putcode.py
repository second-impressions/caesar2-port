"""Putcode — PS homes param `l` in ebx for end-use; RC homes the `t`
temp there and pushes an extra edi.  Probe removing the t local.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="putcode",
    ps_function="Putcode",
    extra_defs="""
short putbuf;
char putlen;
int pmp_optr;
int codesize;
unsigned char *pmp_outbuff;
""",
    prelude="""
extern short putbuf;
extern char putlen;
extern int pmp_optr;
extern int codesize;
extern unsigned char *pmp_outbuff;
""",
)

BODY_TAIL = """
    if (putlen < 8) { return; }
    {
        int idx; unsigned char *p;
        idx = pmp_optr; p = pmp_outbuff;
        pmp_optr = idx + 1;
        p[idx] = (unsigned char)((unsigned short)putbuf >> 8);
    }
    putlen -= 8;
    if (putlen < 8) { putbuf <<= 8; codesize++; return; }
    {
        int idx; unsigned char *p;
        idx = pmp_optr; p = pmp_outbuff;
        pmp_optr = idx + 1;
        p[idx] = putbuf;
    }
    codesize += 2;
    putlen -= 8;
    l -= putlen;
    putbuf = (short)(c << l);
}
"""

exp.add(
    "baseline",
    """
void Putcode(int l, unsigned short c)
{
    int t;
    t = (int)((unsigned short)c >> putlen);
    putbuf |= (short)t;
    putlen += (char)l;
""" + BODY_TAIL,
    note="current source (named t)",
)

exp.add(
    "swap_lo",
    """
void Putcode(int l, unsigned short c)
{
    int t;
    t = (int)((unsigned short)c >> putlen);
    putbuf |= (short)t;
    putlen += (char)l;
    if (putlen < 8) { return; }
    {
        int idx; unsigned char *p;
        idx = pmp_optr; p = pmp_outbuff;
        pmp_optr = idx + 1;
        p[idx] = (unsigned char)((unsigned short)putbuf >> 8);
    }
    putlen -= 8;
    if (putlen < 8) { putbuf <<= 8; codesize++; return; }
    {
        int idx; unsigned char *p;
        p = pmp_outbuff; idx = pmp_optr;
        pmp_optr = idx + 1;
        p[idx] = putbuf;
    }
    codesize += 2;
    putlen -= 8;
    l -= putlen;
    putbuf = (short)(c << l);
}
""",
    note="swap p/idx order in low-byte block (permuter claim)",
)

exp.add(
    "no_t",
    """
void Putcode(int l, unsigned short c)
{
    putbuf |= (short)((unsigned short)c >> putlen);
    putlen += (char)l;
""" + BODY_TAIL,
    note="inline t into putbuf |=",
)
