"""write_clipped_image — lib32 sprite blit dispatcher.

PS @ 0x27CB3, 213 bytes.  Current source is at 133 b diff against PS.

After fixing the `id <<= 4; id += 8` mutation (which now matches PS's
'shl edx, 4; add edx, 8'), the remaining diff is the indexing form:

  PS: keeps `buf` in ESI and `id` in EAX, uses SIB:
       mov dl, byte ptr [esi + eax + 1]    ; 4 bytes per load
  RC: pre-computes `buf + id` into EAX:
       add eax, edx                          ; (once)
       mov dl, byte ptr [eax + 1]            ; 3 bytes per load
       (saves bytes BUT layout shifts cascade through 133 b diffs)

Need to force the SIB form to match PS.

Run::

    uv run c2 cgex run write_clipped_image
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
extern int data_ptr;
extern int sprite_width;
extern int sprite_height;
extern int sprite_start;
extern int sprite_x;
extern int sprite_y;
extern int xclipped;
extern int yclipped;
extern void xclip(int, int);
extern void yclip(int, int);
extern void write_i_sprite(unsigned char *);
extern void write_i_left_sprite(unsigned char *);
extern void write_i_right_sprite(unsigned char *);
"""

_DEFS = """
int data_ptr, sprite_width, sprite_height, sprite_start;
int sprite_x, sprite_y, xclipped, yclipped;
void xclip(int a, int b) { (void)a; (void)b; }
void yclip(int a, int b) { (void)a; (void)b; }
void write_i_sprite(unsigned char *p) { (void)p; }
void write_i_left_sprite(unsigned char *p) { (void)p; }
void write_i_right_sprite(unsigned char *p) { (void)p; }
"""

exp = Experiment(
    name="write_clipped_image",
    ps_function="write_clipped_image",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


exp.add("baseline", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    int ptr;
    id <<= 4;
    id += 8;
    data_ptr = id;
    ptr = id;
    sprite_width  = (unsigned char)buf[ptr]     + ((unsigned char)buf[ptr + 1] << 8);
    sprite_height = (unsigned char)buf[ptr + 2] + ((unsigned char)buf[ptr + 3] << 8);
    sprite_start  = (unsigned char)buf[ptr + 4]
                  + ((unsigned char)buf[ptr + 5] << 8)
                  + ((unsigned char)buf[ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="baseline (133 b)")


# A: use id (not ptr) directly
exp.add("A_use_id", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    id <<= 4;
    id += 8;
    data_ptr = id;
    sprite_width  = (unsigned char)buf[id]     + ((unsigned char)buf[id + 1] << 8);
    sprite_height = (unsigned char)buf[id + 2] + ((unsigned char)buf[id + 3] << 8);
    sprite_start  = (unsigned char)buf[id + 4]
                  + ((unsigned char)buf[id + 5] << 8)
                  + ((unsigned char)buf[id + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="A: use id directly")


# B: re-read from data_ptr after assignment
exp.add("B_via_data_ptr", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    int ptr;
    data_ptr = id * 16 + 8;
    ptr = data_ptr;
    sprite_width  = (unsigned char)buf[ptr]     + ((unsigned char)buf[ptr + 1] << 8);
    sprite_height = (unsigned char)buf[ptr + 2] + ((unsigned char)buf[ptr + 3] << 8);
    sprite_start  = (unsigned char)buf[ptr + 4]
                  + ((unsigned char)buf[ptr + 5] << 8)
                  + ((unsigned char)buf[ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="B: re-read via data_ptr")


# C: separate pointer p
exp.add("C_pointer_arg", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    int ptr;
    unsigned char *p;
    id <<= 4;
    id += 8;
    data_ptr = id;
    ptr = id;
    p = buf;
    sprite_width  = (unsigned char)p[ptr]     + ((unsigned char)p[ptr + 1] << 8);
    sprite_height = (unsigned char)p[ptr + 2] + ((unsigned char)p[ptr + 3] << 8);
    sprite_start  = (unsigned char)p[ptr + 4]
                  + ((unsigned char)p[ptr + 5] << 8)
                  + ((unsigned char)p[ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="C: explicit p = buf alias")


# ── E: match PS's L2552 asymmetric idiom ───────────────────────────
# PS asm shows the +4/+5 terms compile to `xor edx, edx; mov dl, [...]`
# (natural unsigned-char promotion), while the +6 term compiles to
# `mov al, [...]; and eax, 0xff; shl eax, 0x10` (explicit zext idiom).
# Hypothesis: source uses `(unsigned char)` cast ONLY on the +6 term,
# and orders the +5 << 8 term BEFORE the +4 term to match PS's
# evaluation sequence (compute (+5)<<8 first into a temp, then add +4,
# then add (+6)<<16).
exp.add("E_ps_eval_order", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    int ptr;
    id <<= 4;
    id += 8;
    data_ptr = id;
    ptr = id;
    sprite_width  = buf[ptr]     + (buf[ptr + 1] << 8);
    sprite_height = buf[ptr + 2] + (buf[ptr + 3] << 8);
    sprite_start  = (buf[ptr + 5] << 8) + buf[ptr + 4]
                  + ((unsigned char)buf[ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="E: +5<<8 first, +4, then (uchar)+6<<16")


# F: same idea but parenthesise the first two as one sub-expr.
exp.add("F_paren_first_two", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    int ptr;
    id <<= 4;
    id += 8;
    data_ptr = id;
    ptr = id;
    sprite_width  = buf[ptr]     + (buf[ptr + 1] << 8);
    sprite_height = buf[ptr + 2] + (buf[ptr + 3] << 8);
    sprite_start  = ((buf[ptr + 5] << 8) + buf[ptr + 4])
                  + ((unsigned char)buf[ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="F: parenthesise (+5<<8 + +4) explicitly")


# G: like baseline but no (unsigned char) on +4/+5 (since buf is already uchar).
exp.add("G_uchar_on_high", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    int ptr;
    id <<= 4;
    id += 8;
    data_ptr = id;
    ptr = id;
    sprite_width  = buf[ptr]     + (buf[ptr + 1] << 8);
    sprite_height = buf[ptr + 2] + (buf[ptr + 3] << 8);
    sprite_start  = buf[ptr + 4] + (buf[ptr + 5] << 8)
                  + ((unsigned char)buf[ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="G: +4 first, (uchar) only on +6")


# H: full natural form (no casts) matching write_image (byte-exact sibling).
exp.add("H_natural_like_sibling", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    int ptr;
    id <<= 4;
    id += 8;
    data_ptr = id;
    ptr = id;
    sprite_width  = buf[ptr]     + (buf[ptr + 1] << 8);
    sprite_height = buf[ptr + 2] + (buf[ptr + 3] << 8);
    sprite_start  = buf[ptr + 4] + (buf[ptr + 5] << 8) + (buf[ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="H: no casts (matches write_image)")


# D: cast id*16+8 expression at call site
exp.add("D_expr_inline", """
void write_clipped_image(unsigned char *buf, int id, int x, int y,
                         int clip_x_lo, int clip_x_hi,
                         int clip_y_lo, int clip_y_hi)
{
    int ptr;
    ptr = id * 16 + 8;
    data_ptr = ptr;
    sprite_width  = (unsigned char)buf[ptr]     + ((unsigned char)buf[ptr + 1] << 8);
    sprite_height = (unsigned char)buf[ptr + 2] + ((unsigned char)buf[ptr + 3] << 8);
    sprite_start  = (unsigned char)buf[ptr + 4]
                  + ((unsigned char)buf[ptr + 5] << 8)
                  + ((unsigned char)buf[ptr + 6] << 16);
    sprite_x = x;
    sprite_y = y;
    xclip(clip_x_lo, clip_x_hi);
    yclip(clip_y_lo, clip_y_hi);
    if (yclipped == 5) return;
    if (xclipped == 1) { write_i_left_sprite(buf); return; }
    if (xclipped == 2) { write_i_right_sprite(buf); return; }
    write_i_sprite(buf);
}
""", note="D: ptr = id * 16 + 8 (no mutation)")
