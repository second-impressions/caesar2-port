"""InsertNode — PS spills param `r` to a stack slot (push eax, Rule 24a);
RC homes it in edi.  This single decision cascades through all 401 bytes.
Probe source shapes that change register pressure on `r` / `key`.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="insertnode",
    ps_function="InsertNode",
    extra_defs="""
unsigned char *text_buf;
short *lson;
short *rson;
short *dad;
short match_length;
short match_position;
""",
    prelude="""
extern unsigned char *text_buf;
extern short *lson;
extern short *rson;
extern short *dad;
extern short match_length;
extern short match_position;
""",
)

LOOP = """
    for (;;) {
        if (cmp >= 0) {
            if (rson[p] != 0x1000) { p = rson[p]; }
            else { rson[p] = r; dad[r] = p; return; }
        } else {
            if (lson[p] != 0x1000) { p = lson[p]; }
            else { lson[p] = r; dad[r] = p; return; }
        }
        for (i = 1; i < 0x12; i++) {
            cmp = (int)key[i] - (int)text_buf[p + i];
            if (cmp != 0) break;
        }
        if (i > match_length) {
            match_position = p; match_length = i;
            if (match_length >= 0x12) break;
        }
    }
    dad[r] = dad[p]; lson[r] = lson[p]; rson[r] = rson[p];
    dad[lson[p]] = r; dad[rson[p]] = r;
    if (rson[dad[p]] == p) { rson[dad[p]] = r; } else { lson[dad[p]] = r; }
    dad[p] = 0x1000;
}
"""

exp.add("baseline", """
void InsertNode(int r)
{
    int i; int p; int cmp; unsigned char *key;
    cmp = 1; key = &text_buf[r]; p = 0x1001 + (int)key[0];
    rson[r] = 0x1000; lson[r] = 0x1000; match_length = 0;
""" + LOOP, note="current source (cached key)")

exp.add("inline_key", """
void InsertNode(int r)
{
    int i; int p; int cmp;
    cmp = 1; p = 0x1001 + (int)text_buf[r];
    rson[r] = 0x1000; lson[r] = 0x1000; match_length = 0;
""" + LOOP.replace("(int)key[i]", "(int)text_buf[r + i]"),
    note="no key local; inline text_buf[r+i]")
