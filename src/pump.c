#include "pump.h"
#include "c2_data.h"

unsigned char p_len[64] = { 3, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8 };

unsigned char p_code[64] = { 0, 32, 48, 64, 80, 88, 96, 104, 112, 120, 128, 136, 144, 148, 152, 156, 160, 164, 168, 172, 176, 180, 184, 188, 192, 194, 196, 198, 200, 202, 204, 206, 208, 210, 212, 214, 216, 218, 220, 222, 224, 226, 228, 230, 232, 234, 236, 238, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255 };

unsigned char d_code[256] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15, 16, 16, 16, 16, 17, 17, 17, 17, 18, 18, 18, 18, 19, 19, 19, 19, 20, 20, 20, 20, 21, 21, 21, 21, 22, 22, 22, 22, 23, 23, 23, 23, 24, 24, 25, 25, 26, 26, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 32, 33, 33, 34, 34, 35, 35, 36, 36, 37, 37, 38, 38, 39, 39, 40, 40, 41, 41, 42, 42, 43, 43, 44, 44, 45, 45, 46, 46, 47, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63 };

unsigned char d_len[256] = { 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8 };

/* File-local compression state. */
short *dad;
unsigned char *pmp_inbuff;
int pmp_length;
unsigned short *freq;
int pmp_optr;
int pmp_iptr;
int textsize;
short *rson;
short *lson;
unsigned char *pmp_outbuff;
short *prnt;
unsigned char *text_buf;
int codesize;
int pmp_mem_needed;
short *son;
short match_length;
unsigned short getbuf;
unsigned short putbuf;
short match_position;
char putlen;
char getlen;

/* Okumura/Yoshizaki LZHUF parameters. */
#define N           4096        /* size of string buffer */
#define F           60          /* lookahead buffer size */
#define THRESHOLD   2
#define NIL         N           /* tree leaf sentinel */
#define N_CHAR      (256 - THRESHOLD + F)
#define T           (N_CHAR * 2 - 1)
#define R           (T - 1)
#define MAX_FREQ    0x8000

extern void  memmove(void *dst, const void *src, unsigned int n);
extern void *calloc(unsigned int nmemb, unsigned int size);
extern void free(void *);

// LHARC LZSS sliding-window match-tree initialization. Resets the right-son table (`rson`) for
// indices N+1..N+256 and the dad-table (`dad`) for indices 0..N-1, both pointing to NIL (= N =
// 4096).
// FUNCTION: C2 0x6f535
// FUNCTION: C2WIN 0x0043b720
void InitTree(void)
{
    short *r;
    short *d;
    short i;
    for (i = 0x1001; i <= 0x1100; i++) {
        r = rson;
        r[i] = 0x1000;
    }
    for (i = 0; i < 0x1000; i++) {
        d = dad;
        d[i] = 0x1000;
    }
}

// LZSS binary-search-tree insert with longest-match search. Inserts the substring at
// sliding-window position `r` into the match-finding tree, indexed by text_buf[r], and along the
// way records the longest matching previous substring as (match_position, match_length).
// FUNCTION: C2 0x6f575
// FUNCTION: C2WIN 0x0043b794
void InsertNode(short r)
{
    unsigned short c;
    short cmp;
    short i;
    short p;
    unsigned char *key;

    cmp = 1;
    key = &text_buf[r];
    p = (N + 1) + key[0];
    rson[r] = lson[r] = NIL;
    match_length = 0;
    for (;;) {
        if (cmp >= 0) {
            if (rson[p] != NIL)
                p = rson[p];
            else {
                rson[p] = r;
                dad[r] = p;
                return;
            }
        } else {
            if (lson[p] != NIL)
                p = lson[p];
            else {
                lson[p] = r;
                dad[r] = p;
                return;
            }
        }
        for (i = 1; i < F; i++)
            if ((cmp = key[i] - text_buf[p + i]) != 0)
                break;
        if (i > THRESHOLD) {
            if (i > match_length) {
                match_position = ((r - p) & (N - 1)) - 1;
                if ((match_length = i) >= F)
                    break;
            }
            if (i == match_length) {
                if ((c = ((r - p) & (N - 1)) - 1) < match_position)
                    match_position = c;
            }
        }
    }
    dad[r] = dad[p];
    lson[r] = lson[p];
    rson[r] = rson[p];
    dad[lson[p]] = r;
    dad[rson[p]] = r;
    if (rson[dad[p]] == p)
        rson[dad[p]] = r;
    else
        lson[dad[p]] = r;
    dad[p] = 0x1000;
}

// LZSS binary search tree node deletion (Knuth Vol.3 BST delete). Removes the substring rooted at
// sliding-window position `p` from the match-finding tree before its window slot is overwritten.
// FUNCTION: C2 0x6f75a
// FUNCTION: C2WIN 0x0043bab6
void DeleteNode(short p)
{
    short q;

    if (dad[p] == NIL)
        return;
    if (rson[p] == NIL) {
        q = lson[p];
    } else if (lson[p] == NIL) {
        q = rson[p];
    } else {
        q = lson[p];
        if (rson[q] != NIL) {
            do {
                q = rson[q];
            } while (rson[q] != NIL);
            rson[dad[q]] = lson[q];
            dad[lson[q]] = dad[q];
            lson[q] = lson[p];
            dad[lson[p]] = q;
        }
        rson[q] = rson[p];
        dad[rson[p]] = q;
    }
    dad[q] = dad[p];
    if (rson[dad[p]] == p) {
        rson[dad[p]] = q;
    } else {
        lson[dad[p]] = q;
    }
    dad[p] = NIL;
}

// Read one bit from the LZSS input bit-buffer. When fewer than 9 bits remain (getlen <= 8), pull a
// fresh input byte from pmp_inbuff[pmp_iptr++] and shift it into getbuf's high half.
// FUNCTION: C2 0x6f8b5
// FUNCTION: C2WIN 0x0043bce1
short GetBit(void)
{
    short i;

    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
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

// Read 8 bits from the LZSS input bit-buffer. Same refill loop as GetBit; the consume step shifts
// getbuf left by 8 (instead of 1) and returns the byte that just rotated out of the top.
// FUNCTION: C2 0x6f923
// FUNCTION: C2WIN 0x0043bd95
int GetByte(void)
{
    unsigned short i;

    while (getlen <= 8) {
        int idx;
        unsigned char *p;
        idx = pmp_iptr;
        p = pmp_inbuff;
        pmp_iptr = idx + 1;
        i = p[idx];
        getbuf |= i << (8 - getlen);
        getlen += 8;
    }
    i = getbuf;
    getbuf <<= 8;
    getlen -= 8;
    return i >> 8;
}

// Output `l` bits of `c` to the bit-packed pmp_outbuff. `c` holds the bit pattern in the HIGH
// half-word (top `l` bits); putbuf is the 16-bit accumulator and putlen the count of bits already
// in it.
// FUNCTION: C2 0x6f993
// FUNCTION: C2WIN 0x0043be48
void Putcode(short l, unsigned short c)
{
    putbuf |= c >> putlen;
    if ((putlen += l) >= 8) {
        pmp_outbuff[pmp_optr++] = putbuf >> 8;
        if ((putlen -= 8) >= 8) {
            pmp_outbuff[pmp_optr++] = putbuf;
            codesize += 2;
            putlen -= 8;
            putbuf = c << (l - putlen);
        } else {
            putbuf <<= 8;
            codesize++;
        }
    }
}

// Initialize the adaptive-Huffman frequency tree. First loop seeds N_CHAR (= 0x13a) leaves:
// freq[i]=1, son[i]=i+T, prnt[i+T]=i.
// FUNCTION: C2 0x6fa66
// FUNCTION: C2WIN 0x0043bf35
void StartHuff(void)
{
    short i;
    short j;

    for (i = 0; i < N_CHAR; i++) {
        freq[i] = 1;
        son[i] = i + T;
        prnt[i + T] = i;
    }
    i = 0;
    j = N_CHAR;
    while (j <= R) {
        freq[j] = freq[i] + freq[i + 1];
        son[j] = i;
        prnt[i] = prnt[i + 1] = j;
        i += 2;
        j++;
    }
    freq[T] = 0xffff;
    prnt[R] = 0;
}

// Adaptive-Huffman tree rebuild: halves every leaf weight (rounding up), re-sorts, then re-links
// son/prnt pointers. Called by update when freq[R] hits 0x8000 to prevent overflow.
// FUNCTION: C2 0x6fb1e
// FUNCTION: C2WIN 0x0043c061
void reconst(void)
{
    short i;
    short k;
    short j;
    unsigned short f;
    unsigned short l;

    j = 0;
    for (i = 0; i < T; i++) {
        if (son[i] >= T) {
            freq[j] = (freq[i] + 1) / 2;
            son[j] = son[i];
            j++;
        }
    }
    for (i = 0, j = N_CHAR; j < T; i += 2, j++) {
        k = i + 1;
        f = freq[j] = (freq[i] + freq[k]);
        for (k = j - 1; f < freq[k]; k--)
            ;
        k++;
        l = (j - k) * 2;
        memmove(&freq[k + 1], &freq[k], l);
        freq[k] = f;
        memmove(&son[k + 1], &son[k], l);
        son[k] = i;
    }
    for (i = 0; i < T; i++) {
        if ((k = son[i]) >= T) {
            prnt[k] = i;
        } else {
            prnt[k] = prnt[k + 1] = i;
        }
    }
}

// Adaptive-Huffman tree update after a single symbol encode/decode. Increments freq[c+T]'s leaf
// weight, then walks up to the root re-sorting nodes whose weight now exceeds the next sibling's.
// FUNCTION: C2 0x6fc6e
// FUNCTION: C2WIN 0x0043c2d1
void update(short c)
{
    short i;
    short j;
    short k;
    short l;

    if (freq[R] == MAX_FREQ)
        reconst();
    c = prnt[c + T];
    do {
        k = ++freq[c];
        if (k > freq[l = (c + 1)]) {
            while (k > freq[++l])
                ;
            l--;
            freq[c] = freq[l];
            freq[l] = k;
            i = son[c];
            prnt[i] = l;
            if (i < T)
                prnt[i + 1] = l;
            j = son[l];
            son[l] = i;
            prnt[j] = c;
            if (j < T)
                prnt[j + 1] = c;
            son[c] = j;
            c = l;
        }
        c = prnt[c];
    } while (c);
}

// Adaptive-Huffman encode of one character/length-pair token `c`. Walks from leaf prnt[c+T] up to
// the root R = 0x272, accumulating a code by shifting right one bit per step and OR-ing 0x8000
// when the parent's address has bit 0 set (right-child marker).
// FUNCTION: C2 0x6fdb3
// FUNCTION: C2WIN 0x0043c486
void EncodeChar(unsigned short c)
{
    short j;
    unsigned short i;
    short k;

    j = 0;
    i = 0;
    k = prnt[(unsigned short)c + 0x273];

    do {
        i >>= 1;
        if (k & 1) {
            i += 0x8000;
        }
        j++;
        k = prnt[k];
    } while (k != 0x272);

    Putcode((int)j, i);
    update((short)c);
}

// Encode an LZSS match position via Putcode. Top 6 bits index into the static p_code/p_len tables
// (Tanaka-style adaptive position prefix); bottom 6 bits go out raw, left-shifted by 10 so they
// pack into the high half of Putcode's `code` arg.
// FUNCTION: C2 0x6fe17
// FUNCTION: C2WIN 0x0043c51f
void EncodePosition(unsigned short c)
{
    int i;
    i = (c >> 6) & 0xFFFF;
    Putcode(p_len[i],
            (unsigned short)(p_code[i] << 8));
    c &= 0x3F;
    Putcode(6, (unsigned short)(c << 10));
}

// Flush the LZSS bit-buffer's last partial byte to the output buffer. In canonical LHARC this
// calls putc(putbuf>>8); Caesar II uses an in-memory output buffer (pmp_outbuff[pmp_optr++]).
// FUNCTION: C2 0x6fe63
// FUNCTION: C2WIN 0x0043c57d
void EncodeEnd(void)
{
    if (putlen) {
        int idx;
        unsigned char *o;
        unsigned char b = (unsigned char)(putbuf >> 8);
        idx = pmp_optr;
        o = pmp_outbuff;
        pmp_optr = idx + 1;
        o[idx] = b;
        codesize++;
    }
}

// Adaptive-Huffman decode of one character/length-pair token. Walks the `son[]` tree from the root
// (index 0x272) downward, reading one bit per step and following son[c+bit].
// FUNCTION: C2 0x6fe9d
// FUNCTION: C2WIN 0x0043c5ba
short DecodeChar(void)
{
    unsigned short c;

    c = son[R];
    while (c < T) {
        c += GetBit();
        c = son[c];
    }
    c -= T;
    update(c);
    return (short)c;
}

// Decode an LZSS match-position offset. Reads one byte for the 6-bit position prefix, then reads
// d_len[byte]-1 raw bits to recover the original 12-bit position.
// FUNCTION: C2 0x6fee1
// FUNCTION: C2WIN 0x0043c643
short DecodePosition(void)
{
    unsigned short i;
    unsigned short j;
    unsigned short c;

    i = GetByte();
    c = d_code[i] << 6;
    j = d_len[i];
    j -= 2;
    while (j--) {
        i = (i << 1) + GetBit();
    }
    return (short)(c | i & 0x3f);
}

// Allocate the seven LHARC working tables (text_buf, lson, rson, dad, freq, prnt, son). If any
// allocation fails, free everything already allocated and return 0; otherwise return 1.
// FUNCTION: C2 0x6ff25
// FUNCTION: C2WIN 0x0043c6e0
int get_pumping_memory(void)
{
    text_buf = calloc(0x103b, 1);
    lson    = calloc(0x1001, 2);
    rson    = calloc(0x1101, 2);
    dad     = calloc(0x1001, 2);
    freq    = calloc(0x274,  2);
    prnt    = calloc(0x3ad,  2);
    son     = calloc(0x273,  2);

    if (text_buf == 0 || lson == 0 || rson == 0 || dad == 0 ||
        freq == 0 || prnt == 0 || son == 0) {
        free_pumping_memory();
        return 0;
    }
    return 1;
}

// Free the seven LHARC working tables allocated by get_pumping_memory. Each is `if (ptr)
// free(ptr);` -- skipped for null.
// FUNCTION: C2 0x6fffc
// FUNCTION: C2WIN 0x0043c7e8
void free_pumping_memory(void)
{
    if (text_buf) free(text_buf);
    if (lson)     free(lson);
    if (rson)     free(rson);
    if (dad)      free(dad);
    if (freq)     free(freq);
    if (prnt)     free(prnt);
    if (son)      free(son);
}

// LHARC LZSS encoder. Reads `len` bytes from `src`, compresses to `dst` with the canonical
// LZSS-with-adaptive-Huffman scheme, and writes a 8-byte header (compressed size, uncompressed
// size) at the start of dst.
// FUNCTION: C2 0x7007f
// FUNCTION: C2WIN 0x0043c8f6
int pump(unsigned char *src, unsigned char *dst, int length)
{
        short i;
    short c;
    int len;
    short r;
    short s;
    int last_match_length;

    pmp_inbuff  = src;
    pmp_outbuff = dst;
    pmp_iptr    = 0;
    pmp_optr    = 8;
    pmp_length  = length;
    textsize    = 0;
    codesize    = 0;

    getbuf = 0;
    putbuf = 0;
    getlen = 0;
    putlen = 0;
    match_position = 0;
    match_length   = 0;

    if (!get_pumping_memory()) {
        return 0;
    }

    StartHuff();
    InitTree();

    s = 0;
    r = N - F;
    for (i = s; i < r; i++)
        text_buf[i] = ' ';
    len = 0;
    while (len < F) {
        c = pmp_inbuff[pmp_iptr++];
        if (pmp_iptr >= pmp_length)
            break;
        text_buf[r + len] = c;
        len++;
    }
    textsize = len;
    for (i = 1; i <= F; i++)
        InsertNode(r - i);
    InsertNode(r);

    lib_ret4 = 0;

    do {
        if (match_length > len)
            match_length = len;
        if (match_length <= THRESHOLD) {
            match_length = 1;
            EncodeChar(text_buf[r]);
        } else {
            EncodeChar((255 - THRESHOLD) + match_length);
            EncodePosition(match_position);
        }
        last_match_length = match_length;
        for (i = 0; i < last_match_length; i++) {
            if (pmp_iptr >= pmp_length)
                break;
            c = pmp_inbuff[pmp_iptr++];
            DeleteNode(s);
            text_buf[s] = c;
            if (s < F - 1)
                text_buf[s + N] = c;
            s = (s + 1) & (N - 1);
            r = (r + 1) & (N - 1);
            InsertNode(r);
        }
        while (i++ < last_match_length) {
            DeleteNode(s);
            s = (s + 1) & (N - 1);
            r = (r + 1) & (N - 1);
            if (--len)
                InsertNode(r);
        }
    } while (len > 0);

    EncodeEnd();

    my_strcpy((char *)&pmp_optr, (char *)dst, 4);
    my_strcpy((char *)&length, (char *)(dst + 4), 4);

    free_pumping_memory();
    return pmp_optr;
}

// LHARC LZSS decoder. Reads packed bytes from `src` (after a 4-byte file signature + 4-byte
// uncompressed-length header) and writes the decoded stream to `dst`.
// FUNCTION: C2 0x702df
// FUNCTION: C2WIN 0x0043cc5b
int evacuate(unsigned char *src, unsigned char *dst)
{
    short c;
    short r;
    short k;
    short i;
    short j;
    int hdr;
    unsigned int count;

    /* Header: byte 4..7 = uncompressed length. */
    my_strcpy((char *)(src + 4), (char *)&hdr, 4);
    pmp_inbuff  = src;
    pmp_outbuff = dst;
    pmp_iptr    = 8;
    pmp_optr    = 0;

    pmp_length = hdr;
    textsize   = hdr;
    codesize   = 0;

    getbuf = 0;
    putbuf = 0;
    getlen = 0;
    putlen = 0;
    match_position = 0;
    match_length   = 0;

    if (!get_pumping_memory()) {
        return 0;
    }

    StartHuff();

    for (i = 0; i < (N - F); i++) {
        text_buf[i] = ' ';
    }
    r = (N - F);
    for (count = 0; count < textsize; ) {
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

    free_pumping_memory();
    return pmp_optr;
}
