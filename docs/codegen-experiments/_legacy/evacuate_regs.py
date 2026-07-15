"""evacuate — the count<->k EBX/ECX homing swap (the whole 114b cascade).

PS homes the OUTER loop counter `count` in EBX (callee-save, survives the
DecodeChar/DecodePosition calls) and the INNER back-ref copy counter `k` in
ECX.  RC swaps them (k->EBX, count->ECX), and every diff row is that swap or
an instruction shuffle falling out of it.  Grind the source lever (decl order,
loop form, counter shape) that gives count the higher priority for EBX.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern unsigned char *pmp_inbuff, *pmp_outbuff;
extern int pmp_iptr, pmp_optr, pmp_length;
extern int textsize, codesize;
extern unsigned short getbuf, putbuf;
extern unsigned char getlen, putlen;
extern short match_position, match_length;
extern unsigned char *text_buf;
#define N 4096
#define F 60
#define THRESHOLD 2
"""

_DEFS = """
unsigned char *pmp_inbuff, *pmp_outbuff;
int pmp_iptr, pmp_optr, pmp_length;
int textsize, codesize;
unsigned short getbuf, putbuf;
unsigned char getlen, putlen;
short match_position, match_length;
unsigned char *text_buf;
"""

exp = Experiment(
    name="evacuate_regs",
    ps_function="evacuate",
    externs={
        "my_strcpy": "void my_strcpy(char *src, char *dst, int n);",
        "get_pumping_memory": "int get_pumping_memory(void);",
        "free_pumping_memory": "void free_pumping_memory(void);",
        "StartHuff": "void StartHuff(void);",
        "DecodeChar": "short DecodeChar(void);",
        "DecodePosition": "short DecodePosition(void);",
    },
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

_SETUP = """
    my_strcpy((char *)(src + 4), (char *)&hdr, 4);
    pmp_inbuff  = src;
    pmp_outbuff = dst;
    pmp_iptr    = 8;
    pmp_optr    = 0;
    pmp_length = hdr;
    textsize   = hdr;
    codesize   = 0;
    getbuf = 0; putbuf = 0; getlen = 0; putlen = 0;
    match_position = 0; match_length = 0;
    if (!get_pumping_memory()) return 0;
    StartHuff();
    for (i = 0; i < (N - F); i++)
        text_buf[i] = ' ';
    r = (N - F);
"""

def trial(name, decls, loop, note):
    exp.add(name, """
int evacuate(unsigned char *src, unsigned char *dst)
{
""" + decls + _SETUP + loop + """
    free_pumping_memory();
    return pmp_optr;
}
""", note=note)

# back-ref copy with explicit k (reference shape)
_COPY_K = """
    for (count = 0; count < (unsigned int)textsize; ) {
        c = DecodeChar();
        if (c < 256) {
            pmp_outbuff[pmp_optr++] = c;
            text_buf[r++] = c;
            r &= (N - 1);
            count++;
        } else {
            i = (r - DecodePosition() - 1) & (N - 1);
            j = c - (255 - THRESHOLD);
            count += j;
            for (k = 0; k < j; k++) {
                c = text_buf[(i + k) & (N - 1)];
                pmp_outbuff[pmp_optr++] = c;
                text_buf[r++] = c;
                r &= (N - 1);
            }
        }
    }
"""

# copy that advances i and counts down j (no separate k)
_COPY_J = """
    for (count = 0; count < (unsigned int)textsize; ) {
        c = DecodeChar();
        if (c < 256) {
            pmp_outbuff[pmp_optr++] = c;
            text_buf[r++] = c;
            r &= (N - 1);
            count++;
        } else {
            i = (r - DecodePosition() - 1) & (N - 1);
            j = c - (255 - THRESHOLD);
            count += j;
            for (k = 0; k < j; k++) {
                c = text_buf[i++ & (N - 1)];
                pmp_outbuff[pmp_optr++] = c;
                text_buf[r++] = c;
                r &= (N - 1);
            }
        }
    }
"""

_D_REF = "    short c; short r; short k; short i; short j; int hdr; unsigned int count;\n"
_D_COUNT_FIRST = "    unsigned int count; short c; short r; short k; short i; short j; int hdr;\n"
_D_COUNT_BEFORE_K = "    short c; short r; unsigned int count; short k; short i; short j; int hdr;\n"
_D_INT_COUNT = "    short c; short r; short k; short i; short j; int hdr; int count;\n"
_D_K_LAST = "    short c; short r; short i; short j; int hdr; unsigned int count; short k;\n"

trial("baseline",        _D_REF,            _COPY_K, "ref decls, for-k copy")
trial("count_first",     _D_COUNT_FIRST,    _COPY_K, "count declared first")
trial("count_before_k",  _D_COUNT_BEFORE_K, _COPY_K, "count before k")
trial("int_count",       _D_INT_COUNT,      _COPY_K, "int count (not unsigned)")
trial("k_last",          _D_K_LAST,         _COPY_K, "k declared last")
trial("copy_i_advance",  _D_REF,            _COPY_J, "copy via i++ in body")
trial("count_first_iadv",_D_COUNT_FIRST,    _COPY_J, "count first + i++ copy")

# count++ INSIDE the inner copy loop (== count += j, but depth-2 savings)
_COPY_CNT_IN = """
    for (count = 0; count < (unsigned int)textsize; ) {
        c = DecodeChar();
        if (c < 256) {
            pmp_outbuff[pmp_optr++] = c;
            text_buf[r++] = c;
            r &= (N - 1);
            count++;
        } else {
            i = (r - DecodePosition() - 1) & (N - 1);
            j = c - (255 - THRESHOLD);
            for (k = 0; k < j; k++) {
                c = text_buf[(i + k) & (N - 1)];
                pmp_outbuff[pmp_optr++] = c;
                text_buf[r++] = c;
                r &= (N - 1);
                count++;
            }
        }
    }
"""
trial("count_in_loop", _D_REF, _COPY_CNT_IN, "count++ inside inner copy loop")
trial("count_in_first", _D_COUNT_FIRST, _COPY_CNT_IN, "count++ inside + count first")
