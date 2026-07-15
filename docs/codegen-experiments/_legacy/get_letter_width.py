"""get_letter_width — lib32 font letter width lookup.

PS @ 0x26305, 98 bytes.  Current source is at 38 b diff against PS.

The remaining diff is pure Rule 28a swap: PS uses ECX as callee-save
for the cached ``idx-1`` value; recomp uses EBX.  The whole-function
swap propagates through:

  +000a  push ecx (PS) vs push ebx (RC)
  +0036  lea ecx, [eax-1] (PS) vs lea ebx, [eax-1] (RC)
  +003f  PS has 'mov eax, ecx' (re-materialize idx-1 in eax for shl)
         RC keeps eax==idx and rewrites to 'shl eax, 4; sub eax, 8'
         (strength-reduced (idx-1)*16+8 = idx*16-8)

We want to force PS shape.  Hypotheses:

  1. The strength reduction in RC (sub 8 vs add 8) happens because
     Watcom sees EAX still holds the original idx after the lea.
     Forcing the idx variable to be re-read or aliased may break
     CSE and yield the PS pattern.
  2. The ECX vs EBX tie-break may flip based on which register gets
     used first elsewhere (GivenRegisters bias).

Run::

    uv run c2 cgex run get_letter_width
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
extern int sprite_image_no;
extern int data_ptr;
extern unsigned char letter_table[];
"""

_DEFS = """
int sprite_image_no;
int data_ptr;
unsigned char letter_table[256];
"""

exp = Experiment(
    name="get_letter_width",
    ps_function="get_letter_width",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# ── baseline: current source ──
exp.add("baseline", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = (idx - 1) * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="baseline: current source (38 b diff)")


# ── A: use temp variable for idx-1 ──
exp.add("A_temp", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;
    int m1;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    m1 = idx - 1;
    sprite_image_no = m1;
    offset = m1 * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="A: explicit m1 temp")


# ── B: parenthesize differently ──
exp.add("B_paren", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = ((idx - 1) << 4) + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="B: shift instead of mul")


# ── C: factor (idx - 1) once ──
exp.add("C_factor", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    idx--;
    sprite_image_no = idx;
    offset = idx * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="C: mutate idx with --")


# ── D: register hint on idx ──
exp.add("D_register", """
int get_letter_width(int letter, unsigned char *font)
{
    register int idx;
    int offset;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = (idx - 1) * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="D: register int idx")


# ── E: rearrange so offset uses arithmetic via global read ──
exp.add("E_via_global", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = sprite_image_no * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="E: read sprite_image_no for offset calc")


# ── F: separate decls for letter mutation ──
exp.add("F_letter_var", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;
    int code;

    code = (unsigned char)letter;
    if ((char)letter == 0) return 0;
    if (code == 0x20) return 4;

    idx = letter_table[code - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = (idx - 1) * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="F: separate code var, no letter mutation")


# ── G: reorder decls (offset first) ──
exp.add("G_offset_first", """
int get_letter_width(int letter, unsigned char *font)
{
    int offset;
    int idx;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = (idx - 1) * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="G: reorder local decls")


# ── H: hold font in ecx via local ──
# Watcom may pick ECX for font if the local is named separately.
exp.add("H_font_local", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;
    unsigned char *fp;

    fp = font;
    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = (idx - 1) * 16 + 8;
    data_ptr = offset;
    return (fp[offset + 1] << 8) + fp[offset] + 1;
}
""", note="H: local font copy")


# ── I: single-exit structured form ──
exp.add("I_single_exit", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;
    int rv;

    rv = 0;
    if ((char)letter != 0) {
        letter = letter & 0xff;
        if (letter == 0x20) {
            rv = 4;
        } else {
            idx = letter_table[letter - 0x20];
            sprite_image_no = idx;
            if (idx != 0) {
                sprite_image_no = idx - 1;
                offset = (idx - 1) * 16 + 8;
                data_ptr = offset;
                rv = (font[offset + 1] << 8) + font[offset] + 1;
            }
        }
    }
    return rv;
}
""", note="I: single-exit nested if")


# ── J: take address of idx (forces stack spill, no reg) ──
# This eliminates EBX/ECX choice entirely if Watcom spills idx.
exp.add("J_addr_idx", """
extern void no_op(int *);
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = (idx - 1) * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="J: dead address-take placeholder")


# ── K: keep two locals, force conflict ──
# Add an idx_save local that holds idx separately so Watcom must
# materialize both idx and idx-1 distinctly.
exp.add("K_idx_save", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int idx_save;
    int offset;

    if ((char)letter == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    idx_save = idx;
    sprite_image_no = idx_save - 1;
    offset = (idx_save - 1) * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="K: idx_save copy")


# ── L: cast int via temp ──
exp.add("L_cast_temp", """
int get_letter_width(int letter, unsigned char *font)
{
    int idx;
    int offset;
    char ch;

    ch = (char)letter;
    if (ch == 0) return 0;
    letter = letter & 0xff;
    if (letter == 0x20) return 4;

    idx = letter_table[letter - 0x20];
    sprite_image_no = idx;
    if (idx == 0) return 0;

    sprite_image_no = idx - 1;
    offset = (idx - 1) * 16 + 8;
    data_ptr = offset;
    return (font[offset + 1] << 8) + font[offset] + 1;
}
""", note="L: char ch temp")
