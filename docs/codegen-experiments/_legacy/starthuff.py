"""StartHuff — loop-index vs array-base register identity swap.

PS homes the loop index `i` in EDX and reloads each array base into ECX;
recomp swaps them (i in ECX, base in EDX).  Probe source shapes.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="starthuff",
    ps_function="StartHuff",
    extra_defs="""
short *freq;
short *prnt;
short *son;
""",
    prelude="""
extern short *freq;
extern short *prnt;
extern short *son;
""",
)

exp.add(
    "baseline",
    """
void StartHuff(void)
{
    short i; short j; short *p;
    for (i = 0; i < 0x13a; i++) {
        p = freq; p[i] = 1;
        p = son;  p[i] = i + 0x273;
        p = prnt; p[i + 0x273] = i;
    }
    i = 0; j = 0x13a;
    while (j <= 0x272) {
        short f0, f1;
        p = freq; f0 = p[i]; f1 = p[i + 1]; p[j] = f0 + f1;
        p = son;  p[j] = i;
        p = prnt; p[i + 1] = j; p = prnt; p[i] = j;
        i += 2; j++;
    }
    p = freq; p[0x273] = (short)0xFFFF;
    p = prnt; p[0x272] = 0;
}
""",
    note="current source",
)

exp.add(
    "direct_index",
    """
void StartHuff(void)
{
    short i; short j;
    for (i = 0; i < 0x13a; i++) {
        freq[i] = 1;
        son[i] = i + 0x273;
        prnt[i + 0x273] = i;
    }
    i = 0; j = 0x13a;
    while (j <= 0x272) {
        short f0, f1;
        f0 = freq[i]; f1 = freq[i + 1]; freq[j] = f0 + f1;
        son[j] = i;
        prnt[i + 1] = j; prnt[i] = j;
        i += 2; j++;
    }
    freq[0x273] = (short)0xFFFF;
    prnt[0x272] = 0;
}
""",
    note="no p temp; index arrays directly",
)

exp.add(
    "int_index",
    """
void StartHuff(void)
{
    int i; int j; short *p;
    for (i = 0; i < 0x13a; i++) {
        p = freq; p[i] = 1;
        p = son;  p[i] = i + 0x273;
        p = prnt; p[i + 0x273] = i;
    }
    i = 0; j = 0x13a;
    while (j <= 0x272) {
        short f0, f1;
        p = freq; f0 = p[i]; f1 = p[i + 1]; p[j] = f0 + f1;
        p = son;  p[j] = i;
        p = prnt; p[i + 1] = j; p = prnt; p[i] = j;
        i += 2; j++;
    }
    p = freq; p[0x273] = (short)0xFFFF;
    p = prnt; p[0x272] = 0;
}
""",
    note="i/j as int",
)
