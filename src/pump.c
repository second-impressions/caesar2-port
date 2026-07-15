// D:\C2\CODE\pump.c

#include "pump.h"
#include "c2_data.h"

unsigned char p_len[64] = { 3, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8 };

unsigned char p_code[64] = { 0, 32, 48, 64, 80, 88, 96, 104, 112, 120, 128, 136, 144, 148, 152, 156, 160, 164, 168, 172, 176, 180, 184, 188, 192, 194, 196, 198, 200, 202, 204, 206, 208, 210, 212, 214, 216, 218, 220, 222, 224, 226, 228, 230, 232, 234, 236, 238, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255 };

unsigned char d_code[256] = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 9, 9, 9, 9, 9, 9, 9, 9, 10, 10, 10, 10, 10, 10, 10, 10, 11, 11, 11, 11, 11, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 15, 15, 15, 15, 16, 16, 16, 16, 17, 17, 17, 17, 18, 18, 18, 18, 19, 19, 19, 19, 20, 20, 20, 20, 21, 21, 21, 21, 22, 22, 22, 22, 23, 23, 23, 23, 24, 24, 25, 25, 26, 26, 27, 27, 28, 28, 29, 29, 30, 30, 31, 31, 32, 32, 33, 33, 34, 34, 35, 35, 36, 36, 37, 37, 38, 38, 39, 39, 40, 40, 41, 41, 42, 42, 43, 43, 44, 44, 45, 45, 46, 46, 47, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63 };

unsigned char d_len[256] = { 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 8 };

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
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

/* Okumura/Yoshizaki LZHUF parameters (de-structured into globals, 32-bit
 * port: 16-bit DOS `int` values are `short`, arrays are pointers).  PS used
 * N=4096 (the original buffer size) and F=60. */
#define N           4096        /* size of string buffer */
#define F           60          /* lookahead buffer size */
#define THRESHOLD   2
#define NIL         N           /* tree leaf sentinel */
#define N_CHAR      (256 - THRESHOLD + F)
#define T           (N_CHAR * 2 - 1)
#define R           (T - 1)
#define MAX_FREQ    0x8000

extern void  memmove(void *dst, const void *src, unsigned int n);
// FUNCTION: C2 0x6F535
// WIN: 0x0043b720
// Lines 138–143
//
// LHARC LZSS sliding-window match-tree initialization.  Resets
// the right-son table (`rson`) for indices N+1..N+256 and the
// dad-table (`dad`) for indices 0..N-1, both pointing to NIL
// (= N = 4096).  Called once by `StartHuff`.
//
// Globals:
//   rson/dad are short* LHARC tree work arrays.
//
// PS uses a `short i` loop counter (movsx ax → edx for compare).
extern void *calloc(unsigned int nmemb, unsigned int size);
extern void free(void *);

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

// FUNCTION: C2 0x6F575
// WIN: 0x0043b794
// Lines 145–190
//
// LZSS binary-search-tree insert with longest-match search.
// Inserts the substring at sliding-window position `r` into the
// match-finding tree, indexed by text_buf[r], and along the way
// records the longest matching previous substring as
// (match_position, match_length).
//
// Walks the BST starting from the root keyed by text_buf[r]
// (= N + 1 + key[0]).  At each visited node p, compares F bytes
// of text_buf[r..r+F-1] against text_buf[p..p+F-1] and remembers
// the longest match.  When the walk hits a missing child, links
// r into that empty slot.  If a full F-byte match is found, also
// splices r into p's slot and removes p (which had been deleted
// from the window earlier).
//
// Byte-exact reconstruction of Okumura/Yoshizaki LZHUF.C InsertNode
// (16-bit MSDOS source; struct members are globals here, DOS `int`
// 16-bit values are `short`).  Constants: N=4096, NIL=N=0x1000,
// F=60 (0x3c), THRESHOLD=2.
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

// FUNCTION: C2 0x6F75A
// WIN: 0x0043bab6
// Lines 192–217
//
// LZSS binary search tree node deletion (Knuth Vol.3 BST delete).
// Removes the substring rooted at sliding-window position `p` from
// the match-finding tree before its window slot is overwritten.
//
// Three cases:
//   - p has no right child -> replace p with its left child.
//   - p has no left child  -> replace p with its right child.
//   - both children exist  -> find rightmost descendant of left
//     subtree, splice it into p's slot.
// Finally fix the parent link (dad[]) and mark p free.
//
// Tail-merges into StartHuff's epilogue at 0x6FB18 (skipping the
// first 'pop ebp' since DeleteNode has 5 callee-saves vs StartHuff's 6).
//
// NOTE: not yet byte-exact -- complex regalloc + cross-fn tail-merge.
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

// FUNCTION: C2 0x6F8B5
// WIN: 0x0043bce1
// Lines 219–234
//
// Read one bit from the LZSS input bit-buffer.  When fewer than
// 9 bits remain (getlen <= 8), pull a fresh input byte from
// pmp_inbuff[pmp_iptr++] and shift it into getbuf's high half.
// Then return the high bit (bit 15) of getbuf and shift getbuf
// left by 1.
//
// Byte-exact.  This is Okumura/Yoshizaki's 16-bit MSDOS LZHUF.C
// GetBit (`int i; ... return (i < 0)`).  In the original DOS source
// `int` is 16-bit, so the byte-exact 32-bit-Watcom port returns
// `short` and keeps `i`/getbuf 16-bit — that is what makes Watcom
// emit the 16-bit refill (`xor ch,ch`) and 16-bit return (`xor ah,ah`).
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

// FUNCTION: C2 0x6F923
// WIN: 0x0043bd95
// Lines 236–251
//
// Read 8 bits from the LZSS input bit-buffer.  Same refill loop
// as GetBit; the consume step shifts getbuf left by 8 (instead of
// 1) and returns the byte that just rotated out of the top.
//
// Byte-exact.  16-bit MSDOS LZHUF.C GetByte (`unsigned i; ...
// getbuf <<= 8; return i >> 8`).  getbuf is `unsigned short` (16-bit
// `unsigned` in the DOS original), `i` likewise — no casts needed.
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

// FUNCTION: C2 0x6F993
// WIN: 0x0043be48
// Lines 253–274
//
// Output `l` bits of `c` to the bit-packed pmp_outbuff.  `c` holds
// the bit pattern in the HIGH half-word (top `l` bits); putbuf is
// the 16-bit accumulator and putlen the count of bits already in
// it.  Once putbuf has 8+ bits, the high byte spills out to
// pmp_outbuff[pmp_optr++] and codesize advances.  If 16+ bits,
// both bytes spill and putbuf is reseeded with the unwritten part
// of c.
//
// NOTE: not yet byte-exact -- same Watcom 10.0a sub-register
// encoding diffs as GetBit/GetByte (xor ah,ah vs and eax,0xff,
// xor ch,ch vs xor ecx,ecx).  Logic is faithful.
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

// FUNCTION: C2 0x6FA66
// WIN: 0x0043bf35
// Lines 277–292
//
// Initialize the adaptive-Huffman frequency tree.  First loop
// seeds N_CHAR (= 0x13a) leaves: freq[i]=1, son[i]=i+T, prnt[i+T]=i.
// Second loop builds 0x139 internal nodes from index 0x13a up to
// the root R=0x272: freq[j] = freq[i] + freq[i+1], son[j]=i,
// prnt[i] = prnt[i+1] = j, i+=2.  Finally seeds the sentinels:
// freq[T]=0xFFFF (acts as +infty for the rebalancer), prnt[R]=0.
//
// NOTE: not yet byte-exact -- subreg encoding diffs.
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

// FUNCTION: C2 0x6FB1E
// WIN: 0x0043c061
// Lines 294–326
//
// Adaptive-Huffman tree rebuild: halves every leaf weight (rounding
// up), re-sorts, then re-links son/prnt pointers.  Called by update
// when freq[R] hits 0x8000 to prevent overflow.
//
// First pass: scan son[0..T-1], collect entries whose son >= T (i.e.
// the leaves), packing them into the low end with halved weights.
// Second pass: rebuild internal nodes [N_CHAR..T-1] by combining
// pairs and bubble-sort-inserting via memmove.
// Third pass: rewire prnt[] from son[].
//
// NOTE: not yet byte-exact -- complex regalloc with 4 spill slots.

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

// FUNCTION: C2 0x6FC6E
// WIN: 0x0043c2d1
// Lines 328–354
//
// Adaptive-Huffman tree update after a single symbol encode/decode.
// Increments freq[c+T]'s leaf weight, then walks up to the root
// re-sorting nodes whose weight now exceeds the next sibling's.
// When swapping is needed, finds the highest node `l` whose weight
// still falls below the new k, swaps freq[c]↔freq[l] and rewires
// the son/prnt links so children follow their new parents.
//
// When freq[R] == MAX_FREQ (= 0x8000), reconst() halves all weights
// to prevent overflow.  Function tail-merges into StartHuff's 6-pop
// epilogue at 0x6FB17 (after 'add esp, 8').
//
// NOTE: not yet byte-exact -- complex regalloc + spill ordering.
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

// FUNCTION: C2 0x6FDB3
// WIN: 0x0043c486
// Lines 356–371
//
// Adaptive-Huffman encode of one character/length-pair token `c`.
// Walks from leaf prnt[c+T] up to the root R = 0x272, accumulating
// a code by shifting right one bit per step and OR-ing 0x8000
// when the parent's address has bit 0 set (right-child marker).
// Then emits the code via Putcode(depth, code) and rebalances
// the tree via update(c).
//
// NOTE: not yet byte-exact -- subreg encoding diffs.
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

// FUNCTION: C2 0x6FE17
// WIN: 0x0043c51f
// Lines 373–380
//
// Encode an LZSS match position via Putcode.  Top 6 bits index
// into the static p_code/p_len tables (Tanaka-style adaptive
// position prefix); bottom 6 bits go out raw, left-shifted by 10
// so they pack into the high half of Putcode's `code` arg.
//
// p_len/p_code are 64-byte prefix tables.
void EncodePosition(unsigned short c)
{
    int i;
    i = (c >> 6) & 0xFFFF;
    Putcode(p_len[i],
            (unsigned short)(p_code[i] << 8));
    c &= 0x3F;
    Putcode(6, (unsigned short)(c << 10));
}

// FUNCTION: C2 0x6FE63
// WIN: 0x0043c57d
// Lines 382–389
//
// Flush the LZSS bit-buffer's last partial byte to the output
// buffer.  In canonical LHARC this calls putc(putbuf>>8); Caesar II
// uses an in-memory output buffer (pmp_outbuff[pmp_optr++]).
//
// PS uses SAR (signed shift) on putbuf -- it's declared 'short'
// (signed), and the C source must shift the signed value before
// truncating to char.
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

// FUNCTION: C2 0x6FE9D
// WIN: 0x0043c5ba
// Lines 391–404
//
// Adaptive-Huffman decode of one character/length-pair token.
// Walks the `son[]` tree from the root (index 0x272) downward,
// reading one bit per step and following son[c+bit].  Stops
// when c >= T (= 0x273), then converts tree index to value via
// c -= T and updates frequencies.
//
// NOTE: 12 b diff, partially understood (ground hard via
// docs/codegen-experiments/decode_char.py, ~40 trials + OW1 forensics).
// PS: `and edx,0xffff` (clean c in EDX) ; `mov eax,[son]` ; `mov dx,
// [eax+edx*2]` ; return `mov eax,edx`.  Our inline `son[c]` form parks son
// in EDX, evicts c to EAX (`xor eax,eax; mov ax,dx`), indexes [EDX+EAX*2],
// and re-zero-extends the return.
//   * son-register LEVER FOUND: a named local `unsigned short *p; p = son;
//     c = p[c];` flips son EDX->EAX (Rule-24a/27 named-temp) and yields PS's
//     exact `[eax+edx*2]` index + in-place `and edx,0xffff`.  Still 12 b
//     because it leaves a 2-instr Rule-27 ORDER swap (p=son load emitted
//     before the mask; PS masks first) + the return form.
//   * Refuted earlier "whole-TU" guess: GivenRegisters is reset per
//     RegAlloc/Generate call (regalloc.c:1332), and cgex single-TU
//     reproduces the diff — it is a LOCAL effect.
//   * regtrace (GiveBestReg tracer) confirms: son-load & index-CONV temps
//     have EQUAL savings (30/30) => son-register is a use-order tie that the
//     p-local fixes.  ROOT CAUSE of the residue is front-end wrap timing:
//     ushort c => LAZY wrap (a CONV temp ties son for EAX) ; PS's EAGER
//     wrap (`and` at the +=) leaves NO CONV temp so son wins EAX and the
//     wrap precedes the load.  int c forces eager but breaks the compare.
//     No source shape forces eager wrap for ushort c (FE CONV policy).
//   * Types verified right (unsigned short c, son short*); int c breaks the
//     zero-extend compare; int-vs-uint return + son cast are byte-neutral.
// Kept the faithful inline form (the p-local is the same 12 b and adds a
// variable PS's source likely didn't have).
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

// FUNCTION: C2 0x6FEE1
// WIN: 0x0043c643
// Lines 406–416
//
// Decode an LZSS match-position offset.  Reads one byte for the
// 6-bit position prefix, then reads d_len[byte]-1 raw bits to
// recover the original 12-bit position.  Inverse of EncodePosition.
//
// NOTE: not yet byte-exact -- regalloc divergence (PS keeps both
// the byte-index and the loop counter `j` in edx; RC picks ebx for
// the index) plus 16-vs-32-bit cmp encoding.  Logic is faithful.
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

// FUNCTION: C2 0x6FF25
// WIN: 0x0043c6e0
// Lines 419–434
//
// Allocate the seven LHARC working tables (text_buf, lson, rson,
// dad, freq, prnt, son).  If any allocation fails, free everything
// already allocated and return 0; otherwise return 1.
//
// NOTE: not yet byte-exact -- 'test eax, eax' on the last check
// (vs cmp [son], 0) requires the compiler to recognize that eax
// still holds calloc's return.

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

// FUNCTION: C2 0x6FFFC
// WIN: 0x0043c7e8
// Lines 436–444
//
// Free the seven LHARC working tables allocated by
// get_pumping_memory.  Each is `if (ptr) free(ptr);` -- skipped
// for null.  The function tail-merges into StartHuff's 6-pop
// epilogue at 0x6FB17 (cross-function Rule 15).
//
// NOTE: not byte-exact -- the trailing 'jmp StartHuff_epilogue'
// requires StartHuff to share the same prologue.  Recomp emits
// its own pop sequence here.

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

// FUNCTION: C2 0x7007F
// WIN: 0x0043c8f6
// Lines 448–522
//
// LHARC LZSS encoder.  Reads `len` bytes from `src`, compresses
// to `dst` with the canonical LZSS-with-adaptive-Huffman scheme,
// and writes a 8-byte header (compressed size, uncompressed size)
// at the start of dst.  Returns the total bytes written including
// the header.
//
// Algorithm:
//   1. setup pmp_inbuff/pmp_outbuff and zero accumulators.
//   2. allocate working tables (get_pumping_memory).
//   3. seed Huffman tree (StartHuff) and BST (InitTree).
//   4. prefill text_buf[0..N-F-1] with space (0x20).
//   5. read first F bytes; insert F-1 dummy nodes + one real one.
//   6. repeat: encode literal or length-position pair, advance
//      sliding window, refill from input until exhausted.
//   7. emit EncodeEnd; write header; free tables.
//
// Caesar II's runtime never calls this -- only evacuate (decoder)
// is exercised.  Function is here for code completeness.
//
// Faithful reconstruction of Okumura LZHUF.C `Encode` (de-structured;
// see Okumura/Yoshizaki LZHUF.C, 1988/89 public sources): short i/c/len/r/s/
// last_match_length, `for (len = 0; len < F && (c = getc()) != EOF; len++)`
// read loops (PS does check-AFTER-read, so the getc is the comma
// `(c = pmp_inbuff[pmp_iptr++], pmp_iptr < pmp_length)`), `do { } while
// (len > 0)`.
//
// BYTE-EXACT 2026-06 (408 -> 0 b).  The eight verified source levers, read
// off the PS disasm line-by-line (line-shape) and the Watcom 10.0a codegen
// source (bld/cg) + the live allocator (c2 regtrace):
//   1. short i/c/r/s + reference Encode shape (do-while(len>0)).
//   2. `&length` (the PARAM, ==pmp_length) for the 2nd header field, NOT
//      `&pmp_length` (the global): PS takes the param's address (mov
//      eax,esp), which spills it to the stack (entry `push ebx`).
//   3. First read loop = `while (len < F) { c = inbuff[iptr++]; if (iptr >=
//      length) break; ... }` (test-at-TOP) -- a `for` gives test-at-bottom.
//   4. Refill read loop = check-BEFORE-read (the two loops genuinely differ
//      in PS: first is check-after, refill is check-before).
//   5. `int len` (PS keeps len 32-bit in EDI, `cmp edi,0x3c` with no movsx).
//   6. `int last_match_length` -- PS stores it 32-bit (`mov [esp+8],eax`) and
//      reloads it for the refill bound (32-bit `cmp`).  Crucially this also
//      fixes the STACK-SLOT ORDER: Watcom's TempAllocBefore (bld/cg/intel/c/
//      i86temps.c) sorts spilled temps by size, SMALLER first -> higher
//      [esp+N].  So the 2-byte `c` lands at [esp+0xc] and the 4-byte
//      last_match_length at [esp+8], matching PS.  With both `short` the two
//      slots swap.  This makes the whole refill loop byte-exact.
//   7. Direct `return pmp_optr;` / `return 0;` -- NO shared `result` local.
//      (A result local helps the short-lml shape but HURTS the int-lml one:
//      it costs +128 b by perturbing the early text_buf base/index tie.)
//   8. `EncodeChar(unsigned short c)` (matching the sibling EncodePosition).
//      PS masks each EncodeChar arg to its 16-bit param width: the char
//      `text_buf[r]` -> `and eax,0xff`, the int `253+match_length` ->
//      `and eax,0xffff`.  Declaring the param `int` drops the 0xffff mask
//      (10 b short) AND flips the text_buf[r] base/index allocation.
//      Both calls go byte-exact once the param is 16-bit.
// Caesar's runtime never calls pump (only evacuate, the decoder, runs) --
// but it is now byte-identical to PS.EXE all the same.

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

    /* Write 8-byte header: [0..3]=compressed size, [4..7]=length.
     * The (char *) casts bridge unsigned-byte buffers and int-aligned
     * globals into my_strcpy's `char *` signature; they're authentic
     * to PS source (verified: retyping my_strcpy to `void *` shifts
     * its regalloc and regresses byte-exactness). */
    my_strcpy((char *)&pmp_optr, (char *)dst, 4);
    /* Second header field is written from the `length` PARAM (==pmp_length),
     * not the global: PS takes `&length`, which spills the param to the
     * stack (the entry `push ebx`) and reads it back here as `&length`
     * (mov eax,esp).  Using &pmp_length keeps length in a register and
     * shifts the whole function's register homing. */
    my_strcpy((char *)&length, (char *)(dst + 4), 4);

    free_pumping_memory();
    return pmp_optr;
}

// FUNCTION: C2 0x702DF
// WIN: 0x0043cc5b
// Lines 524–572
//
// LHARC LZSS decoder.  Reads packed bytes from `src` (after a
// 4-byte file signature + 4-byte uncompressed-length header) and
// writes the decoded stream to `dst`.  Returns the number of
// bytes written (= pmp_optr).
//
// Maintains a 4096-byte sliding window in text_buf prefilled with
// space (0x20).  Each token from DecodeChar is either a literal
// byte (< 0x100) or a length-position pair (>= 0x100), in which
// case DecodePosition gives the back-distance and (token - 0xFD)
// is the run length.  Both bytes are mirrored into the sliding
// window for future matches.
//
// Faithful reconstruction of Okumura LZHUF.C `Decode` (see
// Okumura/Yoshizaki LZHUF.C, 1988/89 public sources): short c/r/i/j/k, the
// `text_buf[r++] = c; r &= (N-1)` idiom, `count < textsize`.
// NOTE: ~114 b regalloc residue (down from 216) -- PS homes src/dst
// in callee-saved esi/edi across the header my_strcpy; the rest is
// the de-structured Caesar buffer I/O, not pure LZHUF.

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
            /* count++ lives INSIDE the copy loop (== count += j): the
             * depth-2 loop savings make Watcom home `count` in the
             * callee-saved EBX over the inner counter `k` (which falls to
             * ECX), matching PS.  `count += j` before the loop homes count
             * in ECX and swaps the whole function (114 b cascade). */
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
