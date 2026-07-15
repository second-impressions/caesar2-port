"""start_smacking — SOLVED byte-exact.  (Kept as a cautionary record: this whole
sweep looked in the WRONG place.)

PS spreads the three SmackToBuffer/Screen push-temps over ecx / esi / ebx; our
default build coalesced them to ebx / ecx / edx (no esi) — a 6-byte residue:

    smk-buffer:      PS ecx  / RC ebx
    internal_screen: PS esi  / RC ecx
    smk-screen:      PS ebx  / RC edx

This experiment swept source shapes of the CALL REGION (push order, reuse of
`p`, neutral terms, decl order — the trials below) and found nothing: it wrongly
concluded a 6-byte irreducible floor.  That was a MISDIAGNOSIS — the lever was
not in the call region at all.

REAL LEVER (smacker.c, byte-exact): the three push-temps are picks of the
push-scratch `FindRegister` ROVER (a persistent dword cursor), so their
registers are set by the cursor POSITION, not by the call's source shape.
Writing `smk_ref_wi = 0x28` into BOTH arms of the dead inner
`if (smk_height == 0xc8)` (instead of hoisting it after the inner if) splits a
basic block, advancing the rover by one, and the three temps land on PS's
ecx/esi/ebx.  Self-healing.  See the decomp-verify `Rover:` hint, Rule 112
("Discovery" 2), and watcom10.0a `docs/rover-model.md`.

Lesson: when a register *distribution* (not a single swap) is off across
call-arg/const push-temps, suspect the rover cursor and look for a byte-neutral
block split EARLIER in the function — do not grind the call region.

    uv run c2 cgex run start_smacking            # call-region sweep (no lever here)
    uv run c2 cgex run start_smacking --trial baseline
"""

from c2.commands.cgex import Experiment

STRUCTS = """
struct smk_handle {
    unsigned char _pad00[0x08];
    int           Height;
    unsigned int  Frames;
    unsigned char _pad10[0x68 - 0x10];
    int           NewPalette;
    int           PalType;
    unsigned char Palette[772];
    unsigned char Palette2[772];
};
struct c2inf_rec {
    unsigned char _p[0x0C];
    char samples_on;
    unsigned char _q[0x19 - 0x0D];
    char anims_on;
    unsigned char _r[0x40 - 0x1A];
};
"""

DECLS = """
extern int  link_to_smacker(void);
extern void my_strcpy(char *d, char *s, int n);
extern void put_filename_extension(char *p);
extern int  is_file_on_harddrive(char *p);
extern void cd_path(char *p);
extern void free_scratch_buffer(void);
extern int  allow_samples(void);
extern void high_beep(void);
extern void main_path(void);
extern void setup_scratch_buffer(void);
extern int  readfile(char *p, void *buf, int n, int z);
extern void set_palette(int *pal);
extern void general_sprite(int a, int b, int c);
extern void setup_refresh_area(int a, int b, int c, int d, int e);
extern void refresh_svga_screen(void);
extern void stop_samples(void);
extern void vgawinrout(void);
extern struct smk_handle *__pascal SmackOpen(char *fname, unsigned flags, unsigned extrabuf);
extern void __pascal SmackToBuffer(struct smk_handle *smk, unsigned left, unsigned top,
                                   unsigned pitch, unsigned destheight,
                                   const void *buf, unsigned flags);
extern void __pascal SmackToScreen(struct smk_handle *smk, unsigned left, unsigned top,
                                   unsigned byteps, const unsigned short *wintbl, void *setbank);
extern void __cdecl PaletteSet(unsigned char *pal);
extern unsigned __pascal SmackDoFrame(struct smk_handle *smk);
extern void __pascal SmackNextFrame(struct smk_handle *smk);
extern unsigned __pascal SmackWait(struct smk_handle *smk);

extern struct smk_handle *smk;
extern struct c2inf_rec c2inf;
extern int  smacker_on;
extern char extension[];
extern char *smack_filename;
extern int  smack_from_cd;
extern int  smk_height;
extern int  smk_ref_hi;
extern int  smk_ref_wi;
extern unsigned char *internal_screen;
extern int  vgawintab[];
extern int  temp_palette[];
extern unsigned char *scratch_buffer;
extern int  smack_frame;
"""

DEFS = STRUCTS + """
struct smk_handle *smk;
struct c2inf_rec c2inf;
int  smacker_on;
char extension[4];
char *smack_filename;
int  smack_from_cd;
int  smk_height;
int  smk_ref_hi;
int  smk_ref_wi;
unsigned char *internal_screen;
int  vgawintab[64];
int  temp_palette[192];
unsigned char *scratch_buffer;
int  smack_frame;

int  link_to_smacker(void) { return 1; }
void my_strcpy(char *d, char *s, int n) { (void)d;(void)s;(void)n; }
void put_filename_extension(char *p) { (void)p; }
int  is_file_on_harddrive(char *p) { (void)p; return 0; }
void cd_path(char *p) { (void)p; }
void free_scratch_buffer(void) { }
int  allow_samples(void) { return 1; }
void high_beep(void) { }
void main_path(void) { }
void setup_scratch_buffer(void) { }
int  readfile(char *p, void *buf, int n, int z) { (void)p;(void)buf;(void)n;(void)z; return 1; }
void set_palette(int *pal) { (void)pal; }
void general_sprite(int a, int b, int c) { (void)a;(void)b;(void)c; }
void setup_refresh_area(int a, int b, int c, int d, int e) { (void)a;(void)b;(void)c;(void)d;(void)e; }
void refresh_svga_screen(void) { }
void stop_samples(void) { }
void vgawinrout(void) { }
struct smk_handle *__pascal SmackOpen(char *fname, unsigned flags, unsigned extrabuf)
    { (void)fname;(void)flags;(void)extrabuf; return 0; }
void __pascal SmackToBuffer(struct smk_handle *smk, unsigned left, unsigned top,
                            unsigned pitch, unsigned destheight, const void *buf, unsigned flags)
    { (void)smk;(void)left;(void)top;(void)pitch;(void)destheight;(void)buf;(void)flags; }
void __pascal SmackToScreen(struct smk_handle *smk, unsigned left, unsigned top,
                            unsigned byteps, const unsigned short *wintbl, void *setbank)
    { (void)smk;(void)left;(void)top;(void)byteps;(void)wintbl;(void)setbank; }
void __cdecl PaletteSet(unsigned char *pal) { (void)pal; }
unsigned __pascal SmackDoFrame(struct smk_handle *smk) { (void)smk; return 0; }
void __pascal SmackNextFrame(struct smk_handle *smk) { (void)smk; }
unsigned __pascal SmackWait(struct smk_handle *smk) { (void)smk; return 0; }
"""

exp = Experiment(
    name="start_smacking",
    ps_function="start_smacking",
    prelude=STRUCTS + DECLS,
    extra_defs=DEFS,
)


def fn(calls, decls="    int sample_flags;\n", pal=None):
    if pal is None:
        pal = """    if (smk->NewPalette != 0) {
        p = (char *)smk;
        if (smk->PalType == 1)
            p += 0x70;
        else
            p += 0x374;
        PaletteSet((unsigned char *)p);
    }"""
    return f"""
void start_smacking(char *p, int left, int top, int mode)
{{
{decls}
    smacker_on = 0;
    if (link_to_smacker() == 0) return;

    my_strcpy(extension, "SMK", 4);
    put_filename_extension(p);
    smack_filename = p;
    smack_from_cd  = 1;
    if (is_file_on_harddrive(p) != 0)
        smack_from_cd = 0;
    if (smack_from_cd != 0)
        cd_path(smack_filename);
    free_scratch_buffer();

    if (allow_samples() == 0) {{
        sample_flags = 0;
        high_beep();
    }} else if (c2inf.samples_on == 0) {{
        sample_flags = 0;
    }} else {{
        sample_flags = 0x200;
        if (mode == 1) sample_flags = 0x240;
    }}
    if (c2inf.anims_on != 0)
        smk = SmackOpen(smack_filename, sample_flags, -1);
    else
        smk = 0;

    if (smk == 0) {{
        if (smack_from_cd != 0) main_path();
        setup_scratch_buffer();
        if (mode != 1) return;
        my_strcpy(extension, "pl8", 4);
        put_filename_extension(p);
        if (readfile(p, ((void *)scratch_buffer), 0x186a0, 0) == 0) return;
        my_strcpy(extension, "256", 4);
        put_filename_extension(p);
        if (readfile(p, temp_palette, 0x300, 0) == 0) return;
        set_palette(temp_palette);
        general_sprite(0, left, top);
        setup_refresh_area(left, top, 0x14, 0xa, 1);
        refresh_svga_screen();
        return;
    }}

    smk_height = smk->Height;
    if (smk_height == 0xc8) {{
        smk_ref_hi = 0x0d;
        smk_ref_wi = 0x14;
    }} else {{
        if (smk_height == 0xc8)
            smk_ref_hi = 0x19;
        else
            smk_ref_hi = 0x1e;
        smk_ref_wi = 0x28;
    }}
    smacker_on = 1;
    stop_samples();

{calls}

{pal}
    SmackDoFrame(smk);
    SmackNextFrame(smk);

    if (mode == 0) {{
        setup_refresh_area(0, 0, smk_ref_wi, smk_ref_hi, 1);
        refresh_svga_screen();
    }} else if (mode == 1) {{
        setup_refresh_area(left, top, 0x14, 0xa, 1);
        refresh_svga_screen();
    }}

    while ((short)SmackWait(smk) != 0) {{ }}

    smack_frame = 2;
    if (smack_from_cd != 0) main_path();
}}
"""


# 13: separate top-declared pointer `pp` reused for BOTH buffer and palette.
#     p (filename) ends at the smk==0 split; pp starts at the buffer — the two
#     ranges don't overlap, so they can share ESI (one push), matching PS.
for order in ["    unsigned char *pp;\n    int sample_flags;\n",
              "    int sample_flags;\n    unsigned char *pp;\n"]:
    tag = "pp_first" if order.startswith("    unsigned") else "pp_last"
    exp.add(tag, fn(
"""    if (mode != 2) {
        pp = internal_screen;
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      pp, 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }""",
        decls=order,
        pal="""    if (smk->NewPalette != 0) {
        pp = (unsigned char *)smk;
        if (smk->PalType == 1)
            pp += 0x70;
        else
            pp += 0x374;
        PaletteSet(pp);
    }"""))

# 14: same but inline the buffer assignment (late load order)
exp.add("pp_inline", fn(
"""    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      (pp = internal_screen), 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }""",
    decls="    unsigned char *pp;\n    int sample_flags;\n",
    pal="""    if (smk->NewPalette != 0) {
        pp = (unsigned char *)smk;
        if (smk->PalType == 1)
            pp += 0x70;
        else
            pp += 0x374;
        PaletteSet(pp);
    }"""))

# break internal_screen's move-elim into ECX: load via a perturbing op
exp.add("buf_xor0", fn(
"""    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      (unsigned char *)((unsigned)internal_screen | 0), 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }"""))

# SmackWait result as a named local, declared before sample_flags
WAIT_LOCAL = """    while ((short)(wret = SmackWait(smk)) != 0) { }"""
_BASE = """    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      internal_screen, 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }"""

BASE_CALLS = """    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      internal_screen, 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }"""

exp.add("baseline", fn(BASE_CALLS))

PAL_P = None  # default (reuse p)
PAL_SEP = """    if (smk->NewPalette != 0) {
        pal = (unsigned char *)smk;
        if (smk->PalType == 1)
            pal += 0x70;
        else
            pal += 0x374;
        PaletteSet(pal);
    }"""

# 1: buffer = (p = internal_screen) inline, palette reuses p
exp.add("buf_p_inline", fn(
"""    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      (p = (char *)internal_screen), 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }"""))

# 2: buffer reuse p (stmt), palette separate pal
exp.add("buf_p_pal_sep", fn(
"""    if (mode != 2) {
        p = (char *)internal_screen;
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      p, 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }""",
    decls="    int sample_flags;\n    unsigned char *pal;\n", pal=PAL_SEP))

# 3: palette separate pal, buffer direct
exp.add("pal_sep", fn(BASE_CALLS,
    decls="    int sample_flags;\n    unsigned char *pal;\n", pal=PAL_SEP))

# 4: separate buffer local scr declared first, palette reuse p
exp.add("scr_first", fn(
"""    if (mode != 2) {
        scr = internal_screen;
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      scr, 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }""",
    decls="    unsigned char *scr;\n    int sample_flags;\n"))

# 5: separate buffer local scr declared after sample_flags
exp.add("scr_last", fn(
"""    if (mode != 2) {
        scr = internal_screen;
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      scr, 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }""",
    decls="    int sample_flags;\n    unsigned char *scr;\n"))

# 6: Rule 24c neutral term tying internal_screen to p's register (esi)
exp.add("buf_neutral_p", fn(
"""    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      internal_screen + (p - p), 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }"""))

# 7: smk neutral term to push it toward ecx in buffer call
exp.add("smk_neutral", fn(
"""    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      internal_screen, 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }""",
    decls="    int sample_flags;\n"))

# 8: buf_p_inline but palette keeps using a fresh value via p (true PS shape),
#    plus reuse p for SmackToScreen branch too (mode==2 doesn't load buffer)
exp.add("buf_p_inline2", fn(
"""    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      (p = (char *)internal_screen), 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }""",
    pal="""    if (smk->NewPalette != 0) {
        p = (char *)smk;
        if (smk->PalType == 1)
            p += 0x70;
        else
            p += 0x374;
        PaletteSet((unsigned char *)p);
    }"""))

# 10: reuse p for the WHOLE success path incl SmackWait (one long esi range)
exp.add("buf_p_all", fn(
"""    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      (p = (char *)internal_screen), 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }""",
    pal="""    if (smk->NewPalette != 0) {
        if (smk->PalType == 1)
            p = (char *)smk + 0x70;
        else
            p = (char *)smk + 0x374;
        PaletteSet((unsigned char *)p);
    }"""))

# 11: declare buffer pointer as the FIRST local, used only at the call site
exp.add("buf_decl_first", fn(BASE_CALLS,
    decls="    unsigned char *buf;\n    int sample_flags;\n"))

# 12: pass internal_screen, palette reuse p, but split the buffer/screen
#     branch so smk is referenced via a common pre-load expression
exp.add("buf_amp", fn(
"""    if (mode != 2) {
        SmackToBuffer(smk, left, top, 0x280, 0x1e0,
                      &internal_screen[0], 0);
    } else {
        SmackToScreen(smk, left, top, 0x140,
                      (const unsigned short *)vgawintab, vgawinrout);
    }"""))
