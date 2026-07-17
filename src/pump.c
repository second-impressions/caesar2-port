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
unsigned char putlen;
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
/* Forward declarations (functions defined later in this file). */
void free_pumping_memory(void);


// Initialize the LZSS match tree with every node detached.
// FUNCTION: C2 0x6f535
// FUNCTION: C2WIN 0x0043b720
void InitTree(void)
{
    short *right_child_ptr;
    short *parent_ptr;
    short node_idx;
    for (node_idx = 0x1001; node_idx <= 0x1100; node_idx++) {
        right_child_ptr = rson;
        right_child_ptr[node_idx] = 0x1000;
    }
    for (node_idx = 0; node_idx < 0x1000; node_idx++) {
        parent_ptr = dad;
        parent_ptr[node_idx] = 0x1000;
    }
}

// Insert a window position into the LZSS search tree and record its best match.
// FUNCTION: C2 0x6f575
// FUNCTION: C2WIN 0x0043b794
void InsertNode(short insert_idx)
{
    unsigned short candidate_distance;
    short compare_result;
    short compare_idx;
    short parent_idx;
    unsigned char *key_ptr;

    compare_result = 1;
    key_ptr = &text_buf[insert_idx];
    parent_idx = (N + 1) + key_ptr[0];
    rson[insert_idx] = lson[insert_idx] = NIL;
    match_length = 0;
    for (;;) {
        if (compare_result >= 0) {
            if (rson[parent_idx] != NIL)
                parent_idx = rson[parent_idx];
            else {
                rson[parent_idx] = insert_idx;
                dad[insert_idx] = parent_idx;
                return;
            }
        } else {
            if (lson[parent_idx] != NIL)
                parent_idx = lson[parent_idx];
            else {
                lson[parent_idx] = insert_idx;
                dad[insert_idx] = parent_idx;
                return;
            }
        }
        for (compare_idx = 1; compare_idx < F; compare_idx++)
            if ((compare_result = key_ptr[compare_idx] - text_buf[parent_idx + compare_idx]) != 0)
                break;
        if (compare_idx > THRESHOLD) {
            if (compare_idx > match_length) {
                match_position = ((insert_idx - parent_idx) & (N - 1)) - 1;
                if ((match_length = compare_idx) >= F)
                    break;
            }
            if (compare_idx == match_length) {
                if ((candidate_distance = ((insert_idx - parent_idx) & (N - 1)) - 1) < match_position)
                    match_position = candidate_distance;
            }
        }
    }
    dad[insert_idx] = dad[parent_idx];
    lson[insert_idx] = lson[parent_idx];
    rson[insert_idx] = rson[parent_idx];
    dad[lson[parent_idx]] = insert_idx;
    dad[rson[parent_idx]] = insert_idx;
    if (rson[dad[parent_idx]] == parent_idx)
        rson[dad[parent_idx]] = insert_idx;
    else
        lson[dad[parent_idx]] = insert_idx;
    dad[parent_idx] = 0x1000;
}

// Remove a window position from the LZSS search tree before reusing its slot.
// FUNCTION: C2 0x6f75a
// FUNCTION: C2WIN 0x0043bab6
void DeleteNode(short node_idx)
{
    short replacement_idx;

    if (dad[node_idx] == NIL)
        return;
    if (rson[node_idx] == NIL) {
        replacement_idx = lson[node_idx];
    } else if (lson[node_idx] == NIL) {
        replacement_idx = rson[node_idx];
    } else {
        replacement_idx = lson[node_idx];
        if (rson[replacement_idx] != NIL) {
            do {
                replacement_idx = rson[replacement_idx];
            } while (rson[replacement_idx] != NIL);
            rson[dad[replacement_idx]] = lson[replacement_idx];
            dad[lson[replacement_idx]] = dad[replacement_idx];
            lson[replacement_idx] = lson[node_idx];
            dad[lson[node_idx]] = replacement_idx;
        }
        rson[replacement_idx] = rson[node_idx];
        dad[rson[node_idx]] = replacement_idx;
    }
    dad[replacement_idx] = dad[node_idx];
    if (rson[dad[node_idx]] == node_idx) {
        rson[dad[node_idx]] = replacement_idx;
    } else {
        lson[dad[node_idx]] = replacement_idx;
    }
    dad[node_idx] = NIL;
}

// Read one bit from the compressed input stream.
// FUNCTION: C2 0x6f8b5
// FUNCTION: C2WIN 0x0043bce1
short GetBit(void)
{
    short value;

    while (getlen <= 8) {
        int input_idx;
        unsigned char *input_ptr;
        input_idx = pmp_iptr;
        input_ptr = pmp_inbuff;
        pmp_iptr = input_idx + 1;
        value = input_ptr[input_idx];
        getbuf |= value << (8 - getlen);
        getlen += 8;
    }
    value = getbuf;
    getbuf <<= 1;
    getlen--;
    return (value < 0);
}

// Read one byte from the compressed input stream.
// FUNCTION: C2 0x6f923
// FUNCTION: C2WIN 0x0043bd95
int GetByte(void)
{
    unsigned short value;

    while (getlen <= 8) {
        int input_idx;
        unsigned char *input_ptr;
        input_idx = pmp_iptr;
        input_ptr = pmp_inbuff;
        pmp_iptr = input_idx + 1;
        value = input_ptr[input_idx];
        getbuf |= value << (8 - getlen);
        getlen += 8;
    }
    value = getbuf;
    getbuf <<= 8;
    getlen -= 8;
    return value >> 8;
}

// Append the high `l` bits of `c` to the compressed output stream.
// FUNCTION: C2 0x6f993
// FUNCTION: C2WIN 0x0043be48
void Putcode(short bit_count, unsigned short code)
{
    putbuf |= code >> putlen;
    if ((putlen += bit_count) >= 8) {
        pmp_outbuff[pmp_optr++] = putbuf >> 8;
        if ((putlen -= 8) >= 8) {
            pmp_outbuff[pmp_optr++] = putbuf;
            codesize += 2;
            putlen -= 8;
            putbuf = code << (bit_count - putlen);
        } else {
            putbuf <<= 8;
            codesize++;
        }
    }
}

// Initialize the adaptive Huffman tree with equal symbol frequencies.
// FUNCTION: C2 0x6fa66
// FUNCTION: C2WIN 0x0043bf35
void StartHuff(void)
{
    short child_idx;
    short node_idx;

    for (child_idx = 0; child_idx < N_CHAR; child_idx++) {
        freq[child_idx] = 1;
        son[child_idx] = child_idx + T;
        prnt[child_idx + T] = child_idx;
    }
    child_idx = 0;
    node_idx = N_CHAR;
    while (node_idx <= R) {
        freq[node_idx] = freq[child_idx] + freq[child_idx + 1];
        son[node_idx] = child_idx;
        prnt[child_idx] = prnt[child_idx + 1] = node_idx;
        child_idx += 2;
        node_idx++;
    }
    freq[T] = 0xffff;
    prnt[R] = 0;
}

// Rebuild the adaptive Huffman tree with halved frequencies.
// FUNCTION: C2 0x6fb1e
// FUNCTION: C2WIN 0x0043c061
void reconst(void)
{
    short source_idx;
    short scan_idx;
    short write_idx;
    unsigned short node_freq;
    unsigned short byte_count;

    write_idx = 0;
    for (source_idx = 0; source_idx < T; source_idx++) {
        if (son[source_idx] >= T) {
            freq[write_idx] = (freq[source_idx] + 1) / 2;
            son[write_idx] = son[source_idx];
            write_idx++;
        }
    }
    for (source_idx = 0, write_idx = N_CHAR; write_idx < T; source_idx += 2, write_idx++) {
        scan_idx = source_idx + 1;
        node_freq = freq[write_idx] = (freq[source_idx] + freq[scan_idx]);
        for (scan_idx = write_idx - 1; node_freq < freq[scan_idx]; scan_idx--)
            ;
        scan_idx++;
        byte_count = (write_idx - scan_idx) * 2;
        memmove(&freq[scan_idx + 1], &freq[scan_idx], byte_count);
        freq[scan_idx] = node_freq;
        memmove(&son[scan_idx + 1], &son[scan_idx], byte_count);
        son[scan_idx] = source_idx;
    }
    for (source_idx = 0; source_idx < T; source_idx++) {
        if ((scan_idx = son[source_idx]) >= T) {
            prnt[scan_idx] = source_idx;
        } else {
            prnt[scan_idx] = prnt[scan_idx + 1] = source_idx;
        }
    }
}

// Update and reorder the adaptive Huffman tree after processing a symbol.
// FUNCTION: C2 0x6fc6e
// FUNCTION: C2WIN 0x0043c2d1
void update(short tree_idx)
{
    short child_idx;
    short other_child_idx;
    short updated_freq;
    short swap_idx;

    if (freq[R] == MAX_FREQ)
        reconst();
    tree_idx = prnt[tree_idx + T];
    do {
        updated_freq = ++freq[tree_idx];
        if (updated_freq > freq[swap_idx = (tree_idx + 1)]) {
            while (updated_freq > freq[++swap_idx])
                ;
            swap_idx--;
            freq[tree_idx] = freq[swap_idx];
            freq[swap_idx] = updated_freq;
            child_idx = son[tree_idx];
            prnt[child_idx] = swap_idx;
            if (child_idx < T)
                prnt[child_idx + 1] = swap_idx;
            other_child_idx = son[swap_idx];
            son[swap_idx] = child_idx;
            prnt[other_child_idx] = tree_idx;
            if (other_child_idx < T)
                prnt[other_child_idx + 1] = tree_idx;
            son[tree_idx] = other_child_idx;
            tree_idx = swap_idx;
        }
        tree_idx = prnt[tree_idx];
    } while (tree_idx);
}

// Encode one literal or match-length token with the adaptive Huffman tree.
// FUNCTION: C2 0x6fdb3
// FUNCTION: C2WIN 0x0043c486
void EncodeChar(unsigned short symbol)
{
    short bit_count;
    unsigned short code;
    short tree_idx;

    bit_count = 0;
    code = 0;
    tree_idx = prnt[(unsigned short)symbol + 0x273];

    do {
        code >>= 1;
        if (tree_idx & 1) {
            code += 0x8000;
        }
        bit_count++;
        tree_idx = prnt[tree_idx];
    } while (tree_idx != 0x272);

    Putcode((int)bit_count, code);
    update((short)symbol);
}

// Encode an LZSS match distance using a table-coded prefix and six raw bits.
// FUNCTION: C2 0x6fe17
// FUNCTION: C2WIN 0x0043c51f
void EncodePosition(unsigned short position)
{
    int prefix_idx;
    prefix_idx = (position >> 6) & 0xFFFF;
    Putcode(p_len[prefix_idx],
            (unsigned short)(p_code[prefix_idx] << 8));
    position &= 0x3F;
    Putcode(6, (unsigned short)(position << 10));
}

// Flush the final partial byte from the compressed output bit buffer.
// FUNCTION: C2 0x6fe63
// FUNCTION: C2WIN 0x0043c57d
void EncodeEnd(void)
{
    if (putlen) {
        int output_idx;
        unsigned char *output_ptr;
        unsigned char output_byte = (unsigned char)(putbuf >> 8);
        output_idx = pmp_optr;
        output_ptr = pmp_outbuff;
        pmp_optr = output_idx + 1;
        output_ptr[output_idx] = output_byte;
        codesize++;
    }
}

// Decode one literal or match-length token with the adaptive Huffman tree.
// FUNCTION: C2 0x6fe9d
// FUNCTION: C2WIN 0x0043c5ba
short DecodeChar(void)
{
    unsigned short tree_idx;

    tree_idx = son[R];
    while (tree_idx < T) {
        tree_idx += GetBit();
        tree_idx = son[tree_idx];
    }
    tree_idx -= T;
    update(tree_idx);
    return (short)tree_idx;
}

// Decode an LZSS match distance from its prefix and trailing bits.
// FUNCTION: C2 0x6fee1
// FUNCTION: C2WIN 0x0043c643
short DecodePosition(void)
{
    unsigned short code_bits;
    unsigned short bit_count;
    unsigned short position;

    code_bits = GetByte();
    position = d_code[code_bits] << 6;
    bit_count = d_len[code_bits];
    bit_count -= 2;
    while (bit_count--) {
        code_bits = (code_bits << 1) + GetBit();
    }
    return (short)(position | code_bits & 0x3f);
}

// Allocate the LZSS and Huffman work tables, rolling back on failure.
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

// Free the LZSS and Huffman work tables.
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

// Compress a buffer with LZSS and adaptive Huffman coding.
// The output header stores compressed and uncompressed sizes.
// FUNCTION: C2 0x7007f
// FUNCTION: C2WIN 0x0043c8f6
int pump(unsigned char *source_ptr, unsigned char *dest_ptr, int source_size)
{
        short loop_idx;
    short input_byte;
    int lookahead_len;
    short ring_idx;
    short replace_idx;
    int last_match_length;

    pmp_inbuff  = source_ptr;
    pmp_outbuff = dest_ptr;
    pmp_iptr    = 0;
    pmp_optr    = 8;
    pmp_length  = source_size;
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

    replace_idx = 0;
    ring_idx = N - F;
    for (loop_idx = replace_idx; loop_idx < ring_idx; loop_idx++)
        text_buf[loop_idx] = ' ';
    lookahead_len = 0;
    while (lookahead_len < F) {
        input_byte = pmp_inbuff[pmp_iptr++];
        if (pmp_iptr >= pmp_length)
            break;
        text_buf[ring_idx + lookahead_len] = input_byte;
        lookahead_len++;
    }
    textsize = lookahead_len;
    for (loop_idx = 1; loop_idx <= F; loop_idx++)
        InsertNode(ring_idx - loop_idx);
    InsertNode(ring_idx);

    lib_ret4 = 0;

    do {
        if (match_length > lookahead_len)
            match_length = lookahead_len;
        if (match_length <= THRESHOLD) {
            match_length = 1;
            EncodeChar(text_buf[ring_idx]);
        } else {
            EncodeChar((255 - THRESHOLD) + match_length);
            EncodePosition(match_position);
        }
        last_match_length = match_length;
        for (loop_idx = 0; loop_idx < last_match_length; loop_idx++) {
            if (pmp_iptr >= pmp_length)
                break;
            input_byte = pmp_inbuff[pmp_iptr++];
            DeleteNode(replace_idx);
            text_buf[replace_idx] = input_byte;
            if (replace_idx < F - 1)
                text_buf[replace_idx + N] = input_byte;
            replace_idx = (replace_idx + 1) & (N - 1);
            ring_idx = (ring_idx + 1) & (N - 1);
            InsertNode(ring_idx);
        }
        while (loop_idx++ < last_match_length) {
            DeleteNode(replace_idx);
            replace_idx = (replace_idx + 1) & (N - 1);
            ring_idx = (ring_idx + 1) & (N - 1);
            if (--lookahead_len)
                InsertNode(ring_idx);
        }
    } while (lookahead_len > 0);

    EncodeEnd();

    my_strcpy((char *)&pmp_optr, (char *)dest_ptr, 4);
    my_strcpy((char *)&source_size, (char *)(dest_ptr + 4), 4);

    free_pumping_memory();
    return pmp_optr;
}

// Expand an LZSS/adaptive-Huffman buffer into `dst`.
// The input header stores compressed and uncompressed sizes.
// FUNCTION: C2 0x702df
// FUNCTION: C2WIN 0x0043cc5b
int evacuate(unsigned char *source_ptr, unsigned char *dest_ptr)
{
    short symbol;
    short ring_idx;
    short copy_idx;
    short source_idx;
    short match_len;
    int output_size;
    unsigned int output_count;

    /* Header: byte 4..7 = uncompressed length. */
    my_strcpy((char *)(source_ptr + 4), (char *)&output_size, 4);
    pmp_inbuff  = source_ptr;
    pmp_outbuff = dest_ptr;
    pmp_iptr    = 8;
    pmp_optr    = 0;

    pmp_length = output_size;
    textsize   = output_size;
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

    for (source_idx = 0; source_idx < (N - F); source_idx++) {
        text_buf[source_idx] = ' ';
    }
    ring_idx = (N - F);
    for (output_count = 0; output_count < textsize; ) {
        symbol = DecodeChar();
        if (symbol < 256) {
            pmp_outbuff[pmp_optr++] = symbol;
            text_buf[ring_idx++] = symbol;
            ring_idx &= (N - 1);
            output_count++;
        } else {
            source_idx = (ring_idx - DecodePosition() - 1) & (N - 1);
            match_len = symbol - (255 - THRESHOLD);
            for (copy_idx = 0; copy_idx < match_len; copy_idx++) {
                symbol = text_buf[(source_idx + copy_idx) & (N - 1)];
                pmp_outbuff[pmp_optr++] = symbol;
                text_buf[ring_idx++] = symbol;
                ring_idx &= (N - 1);
                output_count++;
            }
        }
    }

    free_pumping_memory();
    return pmp_optr;
}
