"""education-ov-seats -- reproduce get_education_ov_image's byte-seat layout.

PS get_education_ov_image (0x3ED2A, 137b) lays the four locals out as:

    kind    -> BL  (ebx, callee-saved, pushed)   ; byte-loaded, widened
                                                    at the COMPARE via
                                                    `xor eax,eax; mov al,bl`
    flags   -> AL  (eax, scratch)                ; read once, consumed
                                                    immediately into dh/dl
    school  -> DH  (edx, callee-saved, pushed)
    academy -> DL  (edx, callee-saved, pushed)

Our decompiled source diverges:
  * all-int  (44b): kind->EBX ok, but school<->flags swap EAX<->EDX, and
                    kind zext happens at the LOAD (`xor ebx,ebx; mov bl`)
                    not the compare.
  * all-uchar(92b): school grabs AL, flags->AH, academy->AH, kind->DL ->
                    kind widens in-place (`and edx,0xff`), so eax is never
                    reserved and the whole seat map scrambles.

QUESTION: which source SHAPE makes Watcom 10.0a put flags in AL (the
first/best byte reg) and push school/academy onto DH/DL -- i.e. reserve
eax for the kind compare scratch?  The hypothesis under test is that the
divergence is driven by WHEN/whether eax is occupied at the moment the
school/academy conflicts are created, which is a function of:
  (a) the declared widths (byte vs int) of the four locals, and
  (b) the statement order (does flags occupy al before school is born?).

Run:  uv run c2 cgex run education-ov-seats
      uv run c2 cgex run education-ov-seats --trial all_uchar   # full disasm

RESOLVED 2026-06-18 -- get_education_ov_image is now BYTE-EXACT.
----------------------------------------------------------------
The seat layout is one of two symmetric EAX<->EDX fixpoints in Watcom
10.0a's coupled convert-lowering + byte-register allocator.  PS sits in
the non-default one (kind-widen -> `xor eax,eax;mov al,bl`, eax reserved,
school/academy packed into EDX as DH/DL, kind in BL).  THREE source
levers together re-select it -- found by sweeping all
type x decl-order x store combinations (9216 variants) compiled in a
single TU and diffed against PS, then cross-checked against the raw
-trace conflict/savecalc dump and OW v1 regalloc.c/regsave.c:

  1. ALL FOUR locals `unsigned char` (the kind range-compare widens via
     the eax-scratch rCLRHI form, reserving eax).
  2. `kind` declared LAST (Rule 115 conflict-creation-order tie-break:
     flips school->DH / academy->DL / kind->BL instead of the default
     eax-squat where school grabs AL).
  3. final store `= 0` NOT `= school` (drops school's 3rd use so it no
     longer outranks the others for eax; the compiler reuses school's
     known-zero DH for the `=0` store, matching PS's `mov [..],dh`).

Key diagnostic milestone: the raw savecalc dump showed school sav=4
(def + 2 tests + store) vs flags/academy sav=3 -- the store-use was what
pinned school to AL; `= 0` removes it.  The decl-order lever then breaks
the remaining byte-seat tie toward EDX.
"""

from c2.commands.cgex import Experiment

# city_map / landfill_pool / cursors, exactly as the real TU sees them.
# base_kind is cell offset 0, education is cell offset 0xD.
PRELUDE = r"""
struct city_cell {
    unsigned char base_kind;     /* +0x00 */
    unsigned char pad1[12];
    unsigned char education;     /* +0x0D */
    unsigned char pad2[6];
};
unsigned char city_map[128000];
unsigned char landfill_pool[6400];
int cm_sptr;
int cm_dptr;
#define CM_CELL(off)  (*(struct city_cell *)((unsigned char *)city_map + (off)))
"""

exp = Experiment(
    name="education-ov-seats",
    ps_function="get_education_ov_image",
    prelude=PRELUDE,
)

# ── all int (current decomp; expect 44b) ─────────────────────────
exp.add(
    "all_int",
    r"""
void get_education_ov_image(void)
{
    int kind;
    int flags;
    int school;
    int academy;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all int (decomp floor, 44b)",
)

# ── all unsigned char (expect 92b) ───────────────────────────────
exp.add(
    "all_uchar",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    unsigned char flags;
    unsigned char school;
    unsigned char academy;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all unsigned char (92b)",
)

# ── uchar, but kind int (kind in ebx, byte derives in edx) ───────
exp.add(
    "kind_int_rest_uchar",
    r"""
void get_education_ov_image(void)
{
    int kind;
    unsigned char flags;
    unsigned char school;
    unsigned char academy;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="kind int, flags/school/academy uchar",
)

# ── uchar, kind char (signed) -- does signedness move the seat? ──
exp.add(
    "kind_schar",
    r"""
void get_education_ov_image(void)
{
    signed char kind;
    unsigned char flags;
    unsigned char school;
    unsigned char academy;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="kind signed char (probe widen form)",
)

# ── all uchar, but read flags BEFORE kind (flags claims al first) ─
exp.add(
    "uchar_flags_first",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    unsigned char flags;
    unsigned char school;
    unsigned char academy;

    flags = CM_CELL(cm_sptr).education;
    kind = CM_CELL(cm_sptr).base_kind;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all uchar, flags read before kind",
)

# ── do the kind range-compare FIRST (reserve eax before school) ──
exp.add(
    "uchar_kind_first",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    unsigned char flags;
    unsigned char school;
    unsigned char academy;

    kind = CM_CELL(cm_sptr).base_kind;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all uchar, kind range-compare hoisted first",
)

# ── school/academy int, kind/flags uchar ────────────────────────
exp.add(
    "sa_int_kf_uchar",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    unsigned char flags;
    int school;
    int academy;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="school/academy int, kind/flags uchar",
)

# ── flags int (so it owns a dword), kind/school/academy uchar ────
exp.add(
    "flags_int",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    int flags;
    unsigned char school;
    unsigned char academy;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="flags int, kind/school/academy uchar",
)

# ── no flags var: derive school/academy from a re-read field ─────
exp.add(
    "no_flags_var",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    unsigned char school;
    unsigned char academy;

    kind = CM_CELL(cm_sptr).base_kind;
    school = CM_CELL(cm_sptr).education & 0x10;
    academy = CM_CELL(cm_sptr).education & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="no flags var; school/academy from re-read education",
)

# ── all int, academy/school decl+compute swapped ─────────────────
exp.add(
    "int_swap_sa",
    r"""
void get_education_ov_image(void)
{
    int kind;
    int flags;
    int academy;
    int school;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    academy = flags & 0x20;
    school = flags & 0x10;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all int, academy before school (decl+compute)",
)

# ── all int, flags decl LAST (after school/academy) ──────────────
exp.add(
    "int_flags_last_decl",
    r"""
void get_education_ov_image(void)
{
    int kind;
    int school;
    int academy;
    int flags;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all int, flags declared last",
)

# ── kind LAST decl, all int (kind born later -> ebx?) ────────────
exp.add(
    "int_kind_last_decl",
    r"""
void get_education_ov_image(void)
{
    int flags;
    int school;
    int academy;
    int kind;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all int, kind declared last",
)

# ── all uchar, academy before school (compute+test order) ────────
exp.add(
    "uchar_swap_sa",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    unsigned char flags;
    unsigned char academy;
    unsigned char school;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    academy = flags & 0x20;
    school = flags & 0x10;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all uchar, academy before school",
)

# ── all uchar, kind declared+read last (born after the masks) ────
exp.add(
    "uchar_kind_last",
    r"""
void get_education_ov_image(void)
{
    unsigned char flags;
    unsigned char school;
    unsigned char academy;
    unsigned char kind;

    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    kind = CM_CELL(cm_sptr).base_kind;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all uchar, kind read last (after masks)",
)

# ── cached cell pointer, all int (pointer eats a reg) ────────────
exp.add(
    "int_cached_ptr",
    r"""
void get_education_ov_image(void)
{
    struct city_cell *c;
    int kind;
    int flags;
    int school;
    int academy;

    c = &CM_CELL(cm_sptr);
    kind = c->base_kind;
    flags = c->education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all int, cached struct cell *",
)

# ── cached cell pointer, all uchar ────────────────────────
exp.add(
    "uchar_cached_ptr",
    r"""
void get_education_ov_image(void)
{
    struct city_cell *c;
    unsigned char kind;
    unsigned char flags;
    unsigned char school;
    unsigned char academy;

    c = &CM_CELL(cm_sptr);
    kind = c->base_kind;
    flags = c->education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="all uchar, cached struct cell *",
)

# ── inline field reads (no kind/flags vars at all) ──────────────
exp.add(
    "inline_all",
    r"""
void get_education_ov_image(void)
{
    unsigned char school;
    unsigned char academy;

    if (CM_CELL(cm_sptr).base_kind >= 0xf3
        && CM_CELL(cm_sptr).base_kind <= 0xf5)
        { landfill_pool[cm_dptr] = 0x96; return; }
    school = CM_CELL(cm_sptr).education & 0x10;
    academy = CM_CELL(cm_sptr).education & 0x20;
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="inline kind compare, no kind/flags vars",
)

# ── kind inline (uchar field cmp), flags/school/academy cached uchar ─
exp.add(
    "inline_kind_uchar",
    r"""
void get_education_ov_image(void)
{
    unsigned char flags;
    unsigned char school;
    unsigned char academy;

    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (CM_CELL(cm_sptr).base_kind >= 0xf3
        && CM_CELL(cm_sptr).base_kind <= 0xf5)
        { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="kind inline uchar cmp; flags/school/academy cached uchar",
)

# ── kind inline, flags/school/academy cached INT ───────────────
exp.add(
    "inline_kind_int",
    r"""
void get_education_ov_image(void)
{
    int flags;
    int school;
    int academy;

    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (CM_CELL(cm_sptr).base_kind >= 0xf3
        && CM_CELL(cm_sptr).base_kind <= 0xf5)
        { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="kind inline cmp; flags/school/academy cached int",
)

# ── no flags var either: school/academy from re-read, kind inline, int ─
exp.add(
    "inline_kind_no_flags_int",
    r"""
void get_education_ov_image(void)
{
    int school;
    int academy;

    school = CM_CELL(cm_sptr).education & 0x10;
    academy = CM_CELL(cm_sptr).education & 0x20;
    if (CM_CELL(cm_sptr).base_kind >= 0xf3
        && CM_CELL(cm_sptr).base_kind <= 0xf5)
        { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="kind inline, no flags var (school/academy int from education)",
)

# ── kind cached int, flags NOT a var (school/academy from re-read int) ─
exp.add(
    "kind_int_no_flags",
    r"""
void get_education_ov_image(void)
{
    int kind;
    int school;
    int academy;

    kind = CM_CELL(cm_sptr).base_kind;
    school = CM_CELL(cm_sptr).education & 0x10;
    academy = CM_CELL(cm_sptr).education & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = school;
}
""",
    note="kind cached int, no flags var (school/academy int)",
)

# ── CSE form: only kind+flags cached; masks inline (school/academy
#    become CSE temps, not named locals). kind int. ────────────────
exp.add(
    "cse_masks_kind_int",
    r"""
void get_education_ov_image(void)
{
    int kind;
    unsigned char flags;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if ((flags & 0x10) && (flags & 0x20)) { landfill_pool[cm_dptr] = 0x87; return; }
    if (flags & 0x10) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (flags & 0x20) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = flags & 0x10;
}
""",
    note="CSE: kind int + flags cached; masks inline",
)

# ── CSE form, flags int too ────────────────────────────
exp.add(
    "cse_masks_all_int",
    r"""
void get_education_ov_image(void)
{
    int kind;
    int flags;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if ((flags & 0x10) && (flags & 0x20)) { landfill_pool[cm_dptr] = 0x87; return; }
    if (flags & 0x10) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (flags & 0x20) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = flags & 0x10;
}
""",
    note="CSE: kind+flags int; masks inline",
)

# ── CSE form, flags uchar, kind cached uchar ──────────────────
exp.add(
    "cse_masks_all_uchar",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    unsigned char flags;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if ((flags & 0x10) && (flags & 0x20)) { landfill_pool[cm_dptr] = 0x87; return; }
    if (flags & 0x10) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (flags & 0x20) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = flags & 0x10;
}
""",
    note="CSE: kind+flags uchar; masks inline",
)

# ── all uchar, final store = 0 (NOT school): school drops to 2 uses,
#    ties flags -> flags born-first grabs AL, school->DH (PS layout?) ─
exp.add(
    "uchar_store0",
    r"""
void get_education_ov_image(void)
{
    unsigned char kind;
    unsigned char flags;
    unsigned char school;
    unsigned char academy;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = 0;
}
""",
    note="all uchar, final store = 0 (school only 2 uses)",
)

# ── all int, final store = 0 ──────────────────────────
exp.add(
    "int_store0",
    r"""
void get_education_ov_image(void)
{
    int kind;
    int flags;
    int school;
    int academy;

    kind = CM_CELL(cm_sptr).base_kind;
    flags = CM_CELL(cm_sptr).education;
    school = flags & 0x10;
    academy = flags & 0x20;
    if (kind >= 0xf3 && kind <= 0xf5) { landfill_pool[cm_dptr] = 0x96; return; }
    if (school != 0 && academy != 0) { landfill_pool[cm_dptr] = 0x87; return; }
    if (school != 0) { landfill_pool[cm_dptr] = 0x8d; return; }
    if (academy != 0) { landfill_pool[cm_dptr] = 0x84; return; }
    landfill_pool[cm_dptr] = 0;
}
""",
    note="all int, final store = 0",
)
