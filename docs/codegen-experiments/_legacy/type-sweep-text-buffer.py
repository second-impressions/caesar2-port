"""type-sweep-text-buffer — vary types around the load_to_text_buffer pattern.

The current decomp of `load_to_text_buffer` has a 51-byte residue vs PS.
The diff pattern:

  PS:  mov cl, [edx*4 + buf+0x1e]    ; load byte into CL
       xor eax, eax
       mov al, cl                     ; widen CL → EAX
       shl eax, 8
       mov cl, [edx*4 + buf+0x1f]
       xor edx, edx
       mov dl, cl
       add eax, edx
  RC:  xor edx, edx
       mov dl, [eax*4 + buf+0x1e]    ; load directly into DL (no CL hop)
       shl edx, 8
       mov al, [eax*4 + buf+0x1f]
       and eax, 0xff                  ; mask instead of zero-extend
       add eax, edx

PS goes through an intermediate CL register and uses xor-then-mov widening
on BOTH loads.  RC eliminates the intermediate.  Suspect the original PS
source had something different about how the bytes were typed/accessed.

This experiment systematically sweeps:
  - text_buffer element type (char / unsigned char / signed char)
  - intermediate temp presence / type
  - access via index / pointer arithmetic
  - explicit (unsigned char) cast vs implicit
  - structure of the expression (chained shift+add vs split)

Compare against the PS reference function `load_to_text_buffer`.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="type-sweep-text-buffer",
    ps_function="load_to_text_buffer",
    externs={
        "text_buffer": "extern char text_buffer[];",
    },
    extra_defs="char text_buffer[4096];\n",
    prelude="",
)


# ─────────────────── Baseline forms ───────────────────

exp.add(
    "v00-current-decomp",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="current decomp source — 51b residue baseline",
)


# ─────────────────── Variation: text_buffer type ───────────────────

exp.add(
    "v01-uchar-array",
    """
extern unsigned char text_buffer[];
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;

    off  = (text_buffer[idx * 4 + 0x1e] << 8)
         +  text_buffer[idx * 4 + 0x1f];
    dst  = (char *)&text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="text_buffer typed as unsigned char[] — no casts needed",
)

exp.add(
    "v02-schar-array",
    """
extern signed char text_buffer[];
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = (char *)&text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && *(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while (*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="text_buffer as signed char[] — natural for the < ' ' compares",
)


# ─────────────────── Variation: intermediate byte temps ───────────────────

exp.add(
    "v03-uchar-temps",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;
    unsigned char hi, lo;

    hi = text_buffer[idx * 4 + 0x1e];
    lo = text_buffer[idx * 4 + 0x1f];
    off  = (hi << 8) + lo;
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="separate unsigned char temps for the two bytes",
)

exp.add(
    "v04-char-temps-then-cast",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;
    char hi, lo;

    hi = text_buffer[idx * 4 + 0x1e];
    lo = text_buffer[idx * 4 + 0x1f];
    off  = ((unsigned char)hi << 8) + (unsigned char)lo;
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="char temps with cast in expression",
)

exp.add(
    "v05-int-temps",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;
    int hi, lo;

    hi = (unsigned char)text_buffer[idx * 4 + 0x1e];
    lo = (unsigned char)text_buffer[idx * 4 + 0x1f];
    off  = (hi << 8) + lo;
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="int temps for hi/lo",
)


# ─────────────────── Variation: remaining vs n direct ───────────────────

exp.add(
    "v06-n-direct",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    while (n > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            n--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="use n parameter directly, no remaining local",
)


# ─────────────────── Variation: dst as int/index ───────────────────

exp.add(
    "v07-dst-as-int-offset",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    int dst;
    int i;
    int remaining;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = 0x1c + off;
    remaining = n;
    while (remaining > 0) {
        if (text_buffer[dst] == 0 && (signed char)text_buffer[dst - 1] >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)text_buffer[dst] < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        text_buffer[dst + i] = src[i];
}
""",
    note="dst as int index into text_buffer (no pointer)",
)


# ─────────────────── Variation: idx*4 hoisted ───────────────────

exp.add(
    "v08-idx-times-4-hoisted",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;
    int idx4;

    idx4 = idx * 4;
    off  = ((unsigned char)text_buffer[idx4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="hoist idx*4 into local",
)


# ─────────────────── Variation: ptr to slot vs index ───────────────────

exp.add(
    "v09-slot-ptr",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    char *slot;
    int i;
    int remaining;

    slot = &text_buffer[idx * 4];
    off  = ((unsigned char)slot[0x1e] << 8)
         +  (unsigned char)slot[0x1f];
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="hoist slot pointer",
)


# ─────────────────── Variation: param types ───────────────────

exp.add(
    "v10-n-as-uint",
    """
void load_to_text_buffer(char *src, int idx, unsigned int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    unsigned int remaining;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="n as unsigned int",
)

exp.add(
    "v11-src-uchar-ptr",
    """
void load_to_text_buffer(unsigned char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="src as unsigned char *",
)


# ─────────────────── Variation: separate statements ───────────────────

exp.add(
    "v12-separate-off-statements",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;

    off  = (unsigned char)text_buffer[idx * 4 + 0x1e];
    off  = off << 8;
    off  = off + (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="split off-computation across 3 statements",
)


# ─────────────────── Variation: struct entry ───────────────────

exp.add(
    "v13-struct-entry",
    """
struct text_entry {
    unsigned char data[0x1e];
    unsigned char off_hi;
    unsigned char off_lo;
};
extern struct text_entry text_buf_ents[];
extern char text_buffer[];
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;
    int remaining;

    off  = (text_buf_ents[idx].off_hi << 8) + text_buf_ents[idx].off_lo;
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="text_buffer viewed as array of structs (off_hi/off_lo fields)",
)


# ─────────────────── Variation: combined winners ───────────────────

exp.add(
    "v15-i-as-char",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    char i;
    int remaining;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="i (loop counter) as char — PS uses inc bl + xor/mov widening",
)

exp.add(
    "v16-i-uchar",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    unsigned char i;
    int remaining;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    remaining = n;
    while (remaining > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            remaining--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="i as unsigned char",
)

exp.add(
    "v17-i-char-n-direct",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    char i;

    off  = ((unsigned char)text_buffer[idx * 4 + 0x1e] << 8)
         +  (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    while (n > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            n--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="i as char + n direct (combo of v06 + v15)",
)

exp.add(
    "v18-split-stmts-char-i-n-direct",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    char i;

    off  = (unsigned char)text_buffer[idx * 4 + 0x1e];
    off  = off << 8;
    off  = off + (unsigned char)text_buffer[idx * 4 + 0x1f];
    dst  = &text_buffer[0x1c + off];
    while (n > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            n--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="split-stmts + char i + n direct — combo",
)

exp.add(
    "v19-shared-uchar-temp",
    """
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    char i;
    unsigned char c;

    c    = text_buffer[idx * 4 + 0x1e];
    off  = c << 8;
    c    = text_buffer[idx * 4 + 0x1f];
    off  = off + c;
    dst  = &text_buffer[0x1c + off];
    while (n > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            n--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="shared unsigned char byte temp — matches PS CL hop pattern",
)

exp.add(
    "v14-uchar-array-n-direct",
    """
extern unsigned char text_buffer[];
void load_to_text_buffer(char *src, int idx, int n, int copy_len)
{
    int off;
    char *dst;
    int i;

    off  = (text_buffer[idx * 4 + 0x1e] << 8)
         +  text_buffer[idx * 4 + 0x1f];
    dst  = (char *)&text_buffer[0x1c + off];
    while (n > 0) {
        if (*dst == 0 && (signed char)*(dst - 1) >= ' ')
            n--;
        dst++;
    }
    while ((signed char)*dst < ' ')
        dst++;
    for (i = 0; i < copy_len; i++)
        dst[i] = src[i];
}
""",
    note="uchar array + n direct (no remaining)",
)
