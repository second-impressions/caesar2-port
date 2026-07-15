"""copy_to_physical_screen — zero-extend idiom + callee-save choice.

PS:  push ebx; xor ebx, ebx; mov bl, [m]; cmp ebx, 1; ...
RC:  mov al, [m]; and eax, 0xff; cmp eax, 1; ...

PS uses callee-save EBX for the byte load (xor + mov bl).
RC uses caller-save EAX (mov + and).

Probe which source pattern flips Watcom into the EBX/xor pattern.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern char screen_mode;
extern int sink;
"""

_DEFS = """
char screen_mode;
int sink;
"""

exp = Experiment(
    name="copy_to_physical_screen",
    ps_function="copy_to_physical_screen",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
    externs={
        "convert_and_copy_to_256xscreen":
            "void convert_and_copy_to_256xscreen(void);",
        "copy_to_640_480_screen":
            "void copy_to_640_480_screen(void);",
    },
)


# ── trial 1: baseline — char local ─────────────────────────────
exp.add(
    "char-local",
    """
void copy_to_physical_screen(void)
{
    char mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="char mode = screen_mode (current source)",
)


# ── trial 2: int local (force int promotion) ───────────────────
exp.add(
    "int-local",
    """
void copy_to_physical_screen(void)
{
    int mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="int mode — force int promotion early",
)


# ── trial 3: direct read in if ─────────────────────────────────
exp.add(
    "direct-read",
    """
void copy_to_physical_screen(void)
{
    if (screen_mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="direct global read in if",
)


# ── trial 4: unsigned char local ───────────────────────────────
exp.add(
    "uchar-local",
    """
void copy_to_physical_screen(void)
{
    unsigned char mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="unsigned char mode — explicit unsigned type",
)


# ── trial 5: switch instead of if ──────────────────────────────
exp.add(
    "switch-stmt",
    """
void copy_to_physical_screen(void)
{
    switch (screen_mode) {
        case 1:
            convert_and_copy_to_256xscreen();
            break;
        default:
            copy_to_640_480_screen();
    }
}
""",
    note="switch statement instead of if",
)


# ── trial 6: int cast ───────────────────────────────────────────
exp.add(
    "int-cast",
    """
void copy_to_physical_screen(void)
{
    if ((int)screen_mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="(int)screen_mode to force int promotion",
)


# ── trial 7: register char local ───────────────────────────────
exp.add(
    "register-char",
    """
void copy_to_physical_screen(void)
{
    register char mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="register char mode hint",
)


# ── trial 8: register int local ────────────────────────────────
exp.add(
    "register-int",
    """
void copy_to_physical_screen(void)
{
    register int mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="register int mode hint",
)


# ── trial 9: volatile char local ───────────────────────────────
exp.add(
    "volatile-char",
    """
void copy_to_physical_screen(void)
{
    volatile char mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="volatile char local (forces stack/local lifetime)",
)


# ── trial 10: keep mode live across both calls ─────────────────
exp.add(
    "post-call-use",
    """
void copy_to_physical_screen(void)
{
    char mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
    sink = mode;
}
""",
    note="artificially use mode after call to force callee-save lifetime",
)


# ── trial 11: explicit __watcall modify for callees ────────────
exp.add(
    "callees-clobber-all",
    """
#pragma aux convert_and_copy_to_256xscreen modify [eax ebx ecx edx esi edi];
#pragma aux copy_to_640_480_screen modify [eax ebx ecx edx esi edi];

void copy_to_physical_screen(void)
{
    char mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="explicit broad modify sets for callees; tests call-clobber assumptions",
)


# ── trial 12: exact-empty modify for callees ───────────────────
exp.add(
    "callees-clobber-none",
    """
#pragma aux convert_and_copy_to_256xscreen modify exact [];
#pragma aux copy_to_640_480_screen modify exact [];

void copy_to_physical_screen(void)
{
    char mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="exact no-clobber callees; tests whether PS saw preserved regs",
)


# ── trial 13: assignment before if with separate statement ─────
exp.add(
    "split-decl-assign",
    """
void copy_to_physical_screen(void)
{
    char mode;
    mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="split declaration/assignment (conflict ordering probe)",
)


# ── trial 14: compare via unsigned int temp from char temp ─────
exp.add(
    "char-then-int",
    """
void copy_to_physical_screen(void)
{
    char c = screen_mode;
    int mode = c;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
}
""",
    note="two conflicts: byte temp then int temp",
)


# ── trial 15: dummy early EBX pressure via extra char local ────
exp.add(
    "two-char-locals",
    """
void copy_to_physical_screen(void)
{
    char dummy = screen_mode;
    char mode = screen_mode;
    if (mode == 1)
        convert_and_copy_to_256xscreen();
    else
        copy_to_640_480_screen();
    (void)dummy;
}
""",
    note="two byte locals to perturb conflict ordering / GivenRegisters",
)


# ── trial 16: early-return exact branch shape ──────────────────
exp.add(
    "early-return-char",
    """
void copy_to_physical_screen(void)
{
    char mode = screen_mode;
    if (mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="PS branch shape: if mode==1 call+return; fallthrough else call",
)


# ── trial 17: early-return direct read ─────────────────────────
exp.add(
    "early-return-direct",
    """
void copy_to_physical_screen(void)
{
    if (screen_mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="early-return shape with direct global compare",
)


# ── trial 18: int local, early-return ──────────────────────────
exp.add(
    "early-return-int",
    """
void copy_to_physical_screen(void)
{
    int mode = screen_mode;
    if (mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="early-return with int promoted local",
)


# ── trial 19: unsigned char local, early-return ────────────────
exp.add(
    "early-return-uchar",
    """
void copy_to_physical_screen(void)
{
    unsigned char mode = screen_mode;
    if (mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="early-return with unsigned char local",
)


# ── trial 20: compare against char literal ─────────────────────
exp.add(
    "char-literal",
    """
void copy_to_physical_screen(void)
{
    char mode = screen_mode;
    if (mode == (char)1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="compare char local to (char)1",
)


# ── trial 21: compare != 1 branch first ────────────────────────
exp.add(
    "not-equal-first",
    """
void copy_to_physical_screen(void)
{
    char mode = screen_mode;
    if (mode != 1) {
        copy_to_640_480_screen();
        return;
    }
    convert_and_copy_to_256xscreen();
}
""",
    note="source spells PS jcc direction: if mode != 1 goto else",
)


# ── trial 22: int temp assigned from zero then byte ────────────
exp.add(
    "zero-then-byte-or",
    """
void copy_to_physical_screen(void)
{
    int mode;
    mode = 0;
    mode |= screen_mode;
    if (mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="try to force xor reg,reg then byte merge into same temp",
)


# ── trial 23: int temp assigned from zero then add byte ────────
exp.add(
    "zero-then-byte-add",
    """
void copy_to_physical_screen(void)
{
    int mode;
    mode = 0;
    mode += screen_mode;
    if (mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="zero temp then += char global",
)


# ── trial 24: manual unsigned mask local ───────────────────────
exp.add(
    "mask-local",
    """
void copy_to_physical_screen(void)
{
    int mode = screen_mode & 0xff;
    if (mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="explicit &0xff zero-extension",
)


# ── trial 25: two-step promoted local ──────────────────────────
exp.add(
    "uchar-then-int",
    """
void copy_to_physical_screen(void)
{
    unsigned char c;
    int mode;
    c = screen_mode;
    mode = c;
    if (mode == 1) {
        convert_and_copy_to_256xscreen();
        return;
    }
    copy_to_640_480_screen();
}
""",
    note="explicit byte local then promoted int local",
)


# ── trial 26: do-while false keeps local statement boundary ────
exp.add(
    "do-once",
    """
void copy_to_physical_screen(void)
{
    char mode = screen_mode;
    do {
        if (mode == 1) {
            convert_and_copy_to_256xscreen();
            return;
        }
        copy_to_640_480_screen();
    } while (0);
}
""",
    note="same semantics via do { } while(0)",
)


# ─── RULE 59 DISCOVERY ───────────────────────────────────────
#
# All trials above stayed at ≥ 13 b residue — no body-level rewrite
# of the void(void) form reproduces PS's `push ebx; xor ebx, ebx;
# mov bl, [m]; cmp ebx, 1` shape.
#
# Breakthrough came from cross-referencing other PS functions that
# DO use this idiom (`xor ebx, ebx; mov bl, [m]`) and finding
# `show_landfill` (37 b) with 7 callers all setting EAX+EDX before
# the call.  PS source had pass-through args; reserving EAX/EDX for
# them shifts the byte-temp regalloc into EBX.  The fix is now in
# `decomp/src/lib32.c` (`int p1, int p2` pass-through forwarded to
# typed callees) — byte-exact →0 b.  See Rule 59 in
# `docs/watcom-codegen-patterns.md` for the full mechanism and the
# parallel fix on `show_landfill` (also →0 b).
