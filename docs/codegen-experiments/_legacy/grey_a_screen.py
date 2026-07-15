"""grey_a_screen — palette → greyscale lookup builder.

PS asm pattern (inner loop body):

    mov edx, ebx
    shl edx, 2
    sub edx, ebx              ; edx = 3*i
    mov dl, [edx + current_palette]
    and edx, 0xff             ; v zero-extended
    mov eax, edx              ; save v in eax
    add edx, edx              ; edx = 2*v
    add edx, eax              ; edx = 3*v
    mov eax, edx              ; eax = 3*v (for idiv)
    sar edx, 0x1f             ; sign extend to high half
    idiv ecx                  ; eax = 3*v / 3 = v
    mov edx, eax
    sar edx, 1                ; edx = v / 2
    mov eax, 0x3f
    sub eax, edx              ; eax = 0x3f - (v / 2)
    mov [ebx + greying_data], al

ECX is preloaded to 3 outside the loop ("xor ebx, ebx; mov ecx, 3"
before the loop).  The (v * 3) / 3 round-trip is the giveaway: PS
keeps the "trinity" computation intact and divides by the
preloaded ECX.

Hypothesis: the original source had something like

    sum = v + v + v;
    greying_data[i] = (unsigned char)(0x3f - ((sum / 3) >> 1));

or maybe

    int divisor = 3;
    sum = v * divisor;
    greying_data[i] = (unsigned char)(0x3f - ((sum / divisor) >> 1));

which both produce the (3*v / 3) round-trip.
"""

from c2.commands.cgex import Experiment


_PRELUDE = r"""
extern unsigned char current_palette[];
extern unsigned char greying_data[];
extern int screen_mode;
extern unsigned char *internal_screen;
"""

_DEFS = r"""
unsigned char current_palette[768];
unsigned char greying_data[256];
int screen_mode;
unsigned char *internal_screen;
"""


exp = Experiment(
    name="grey_a_screen",
    ps_function="grey_a_screen",
    chk=True,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


exp.add("baseline", r"""
void grey_a_screen(void)
{
    int i;
    unsigned char *fb;

    if (screen_mode != 2)         return;
    if (internal_screen == 0)     return;

    for (i = 0; i < 0x100; i++) {
        int avg = (current_palette[3 * i] * 3) / 3;
        greying_data[i] = (unsigned char)(0x3f - (avg >> 1));
    }

    fb = internal_screen;
    for (i = 0; i < 0x4b000; i++) {
        int idx = fb[i];
        fb[i] = greying_data[idx];
    }
}
""", note="baseline: (v*3)/3 form")


exp.add("A_sum_three", r"""
void grey_a_screen(void)
{
    int i;
    unsigned char *fb;
    int avg, v;

    if (screen_mode != 2)         return;
    if (internal_screen == 0)     return;

    for (i = 0; i < 0x100; i++) {
        v = current_palette[3 * i];
        avg = (v + v + v) / 3;
        greying_data[i] = (unsigned char)(0x3f - (avg >> 1));
    }

    fb = internal_screen;
    for (i = 0; i < 0x4b000; i++) {
        int idx = fb[i];
        fb[i] = greying_data[idx];
    }
}
""", note="A: v+v+v / 3 form")


exp.add("B_divisor_var", r"""
void grey_a_screen(void)
{
    int i;
    unsigned char *fb;
    int avg, v, divisor;

    if (screen_mode != 2)         return;
    if (internal_screen == 0)     return;

    divisor = 3;
    for (i = 0; i < 0x100; i++) {
        v = current_palette[3 * i];
        avg = (v * divisor) / divisor;
        greying_data[i] = (unsigned char)(0x3f - (avg >> 1));
    }

    fb = internal_screen;
    for (i = 0; i < 0x4b000; i++) {
        int idx = fb[i];
        fb[i] = greying_data[idx];
    }
}
""", note="B: divisor variable preloaded")


exp.add("C_rgb_separate", r"""
void grey_a_screen(void)
{
    int i;
    unsigned char *fb;
    int avg, r, g, b;

    if (screen_mode != 2)         return;
    if (internal_screen == 0)     return;

    for (i = 0; i < 0x100; i++) {
        r = current_palette[3 * i];
        g = current_palette[3 * i];
        b = current_palette[3 * i];
        avg = (r + g + b) / 3;
        greying_data[i] = (unsigned char)(0x3f - (avg >> 1));
    }

    fb = internal_screen;
    for (i = 0; i < 0x4b000; i++) {
        int idx = fb[i];
        fb[i] = greying_data[idx];
    }
}
""", note="C: r+g+b separate loads (all same idx)")


exp.add("D_v_temp", r"""
void grey_a_screen(void)
{
    int i;
    unsigned char *fb;
    int v;

    if (screen_mode != 2)         return;
    if (internal_screen == 0)     return;

    for (i = 0; i < 0x100; i++) {
        v = current_palette[3 * i];
        v = (v * 3) / 3;
        greying_data[i] = (unsigned char)(0x3f - (v >> 1));
    }

    fb = internal_screen;
    for (i = 0; i < 0x4b000; i++) {
        int idx = fb[i];
        fb[i] = greying_data[idx];
    }
}
""", note="D: v = ...; v = v*3/3; separate stmts")


exp.add("E_three_mul_inline", r"""
void grey_a_screen(void)
{
    int i;
    unsigned char *fb;
    int v;

    if (screen_mode != 2)         return;
    if (internal_screen == 0)     return;

    for (i = 0; i < 0x100; i++) {
        v = (current_palette[3 * i] * 3) / 3;
        greying_data[i] = (unsigned char)(0x3f - (v >> 1));
    }

    fb = internal_screen;
    for (i = 0; i < 0x4b000; i++) {
        int idx = fb[i];
        fb[i] = greying_data[idx];
    }
}
""", note="E: explicit v assignment instead of `int avg = ...;`")
