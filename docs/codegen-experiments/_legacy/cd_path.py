"""cd_path — lib32 CD-path switcher.

PS @ 0x242A2, 276 bytes.  Current source is at 6 b diff against PS.

The diff is pure Rule 28 swap: PS uses ECX as the callee-save for
'p = buf'; recomp uses EBX. The whole function uses one callee-save
for the 'p' pointer.

Run::

    uv run c2 cgex run cd_path
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
struct c2info { char drive_init; char cd_letter; };
extern struct c2info c2inf;
extern char extension[];
extern void get_filename_extension(const char *);
extern void string_to_upper(char *);
extern int strcmp(const char *, const char *);
extern void _dos_setdrive(unsigned, unsigned *);
extern void chdir(const char *);
"""

_DEFS = """
struct c2info { char drive_init; char cd_letter; } c2inf;
char extension[16];
int strcmp(const char *a, const char *b) { (void)a; (void)b; return 0; }
void _dos_setdrive(unsigned a, unsigned *b) { (void)a; (void)b; }
void chdir(const char *p) { (void)p; }
void get_filename_extension(const char *p) { (void)p; }
void string_to_upper(char *p) { (void)p; }
"""

exp = Experiment(
    name="cd_path",
    ps_function="cd_path",
    chk=False,
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


_BUF = 'static char buf[] = "c:\\\\";'


exp.add("baseline", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="baseline current")


# A: assign p later, just before use
exp.add("A_assign_late", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p = buf;
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="A: p = buf late")


# B: use buf directly instead of p alias
exp.add("B_no_p", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    buf[0] = c2inf.cd_letter;
    chdir(buf);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="B: no p alias")


# C: declare p AFTER matched
exp.add("C_p_after_matched", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    unsigned saved_drive;
    char *p;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="C: p decl after matched")


# D: declare p as register
exp.add("D_register_p", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    register char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="D: register char *p")


# E: rename buf to bias allocation
exp.add("E_buf_local", """
void cd_path(const char *fname)
{
    static char buf[] = "c:\\\\";
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="E: static buf inside function")


# F: matched -> early return inverted (might change conflict order)
exp.add("F_inverted_matched", _BUF + """
void cd_path(const char *fname)
{
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    if (strcmp("PL8", extension) != 0 &&
        strcmp("RAW", extension) != 0 &&
        strcmp("XMI", extension) != 0 &&
        strcmp("SMK", extension) != 0)
        return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="F: inverted matched, no matched var")


# G: char buf as array param-like
exp.add("G_array_index", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    buf[0] = c2inf.cd_letter;
    chdir(&buf[0]);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="G: &buf[0] for chdir")


# H: matched as ptr to suppress its callee-save preference
exp.add("H_matched_ptr_via_addr", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    /* extra use of p forces higher savings on it */
    if (p[0] == 0) return;
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="H: extra p use")


# I: matched as boolean expression inline
exp.add("I_inline_matched", _BUF + """
void cd_path(const char *fname)
{
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    if (!(strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0))
        return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="I: no matched, inline test")


# J: declare p with block-local scope inside if body
exp.add("J_block_local_p", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    {
        char *p = buf;
        _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
        p[0] = c2inf.cd_letter;
        chdir(p);
    }
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="J: block-local p")


# K: chdir(&buf[0]) without p alias (force higher use density on buf-addr)
exp.add("K_buf_arr_idx", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = &buf[0];
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    *p = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="K: *p = ... instead of p[0] = ...")


# L: matched address taken (force on stack)
exp.add("L_matched_addr", _BUF + """
extern void use_int(int *);
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    use_int(&matched);  /* take address to force on stack */
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
}
""", note="L: take addr of matched to force on stack")


# M: matched = 0 default, set 1 if match (inverted)
exp.add("M_matched_inverted", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 0;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 1;
    if (!matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="M: matched=0 default")


# N: explicit init both p and matched at same time
exp.add("N_paired_init", _BUF + """
void cd_path(const char *fname)
{
    char *p = buf;
    int matched = 1;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="N: paired init at decl")


# O: matched as int written via subexp (forces stack)
exp.add("O_matched_volatile", _BUF + """
void cd_path(const char *fname)
{
    char *p;
    volatile int matched;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="O: volatile matched -> stack")


# P: use a literal-decl static char buf inside extension match
exp.add("P_static_char_p", _BUF + """
void cd_path(const char *fname)
{
    static char *p = buf;
    int matched;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
}
""", note="P: static char *p = buf")


# Q: write through buf direct + cache index
exp.add("Q_inline_p", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    p = buf;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="Q: p init after matched check")


# R: declare p second after matched, same as baseline
exp.add("R_canonical", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
}
""", note="R: short body, p init early, matched after")


# S: external buf, not static
exp.add("S_extern_buf", """
extern char buf[];
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
}
""", note="S: extern char buf[]")


# T: file-static buf, not function-static
exp.add("T_file_static_buf", """
static char buf[] = "c:\\\\";
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
}
""", note="T: file-static buf")


# U: matched declared and inited at top, before drive_init check
exp.add("U_matched_init_at_decl_early", _BUF + """
void cd_path(const char *fname)
{
    int matched = 1;
    char *p = buf;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="U: both inited at decl")


# V: declare matched first, init at decl
exp.add("V_matched_first_init", _BUF + """
void cd_path(const char *fname)
{
    int matched = 1;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="V: matched inited at decl, p assigned later")


# W: cache extension into local pointer (like font_no's bufp trick)
exp.add("W_extp_cache", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    char *extp;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    extp = extension;
    matched = 1;
    if (strcmp("PL8", extp) == 0 ||
        strcmp("RAW", extp) == 0 ||
        strcmp("XMI", extp) == 0 ||
        strcmp("SMK", extp) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
}
""", note="W: cache extension into extp")


# X: declare buf at file scope, with explicit array size
_BUF_SIZED = 'static char buf[4] = "c:\\\\";'
exp.add("X_buf_sized", _BUF_SIZED + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
}
""", note="X: explicit buf[4]")


# Y: drop early return, use nested if
exp.add("Y_nested", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init == 1) {
        get_filename_extension(fname);
        string_to_upper(extension);
        matched = 1;
        if (strcmp("PL8", extension) == 0 ||
            strcmp("RAW", extension) == 0 ||
            strcmp("XMI", extension) == 0 ||
            strcmp("SMK", extension) == 0)
            matched = 0;
        if (!matched) {
            _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
            p[0] = c2inf.cd_letter;
            chdir(p);
        }
    }
}
""", note="Y: nested if, no early return")


# Z: extra dummy local to shift conflict numbering
exp.add("Z_dummy_first", _BUF + """
void cd_path(const char *fname)
{
    int dummy = 0;
    int matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    (void)dummy;
}
""", note="Z: dummy first decl")


# AA: dummy in between matched and p
exp.add("AA_dummy_middle", _BUF + """
void cd_path(const char *fname)
{
    int matched;
    int dummy = 0;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    (void)dummy;
}
""", note="AA: dummy between matched and p")


# BB: long matched
exp.add("BB_long_matched", _BUF + """
void cd_path(const char *fname)
{
    long matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="BB: long matched")


# CC: unsigned matched
exp.add("CC_unsigned_matched", _BUF + """
void cd_path(const char *fname)
{
    unsigned matched;
    char *p;
    unsigned saved_drive;

    p = buf;
    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    matched = 1;
    if (strcmp("PL8", extension) == 0 ||
        strcmp("RAW", extension) == 0 ||
        strcmp("XMI", extension) == 0 ||
        strcmp("SMK", extension) == 0)
        matched = 0;
    if (matched) return;
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="CC: unsigned matched")


# DD: matched scoped to if-block
exp.add("DD_matched_blockscoped", _BUF + """
void cd_path(const char *fname)
{
    char *p = buf;
    unsigned saved_drive;

    if (c2inf.drive_init != 1) return;
    get_filename_extension(fname);
    string_to_upper(extension);
    {
        int matched = 1;
        if (strcmp("PL8", extension) == 0 ||
            strcmp("RAW", extension) == 0 ||
            strcmp("XMI", extension) == 0 ||
            strcmp("SMK", extension) == 0)
            matched = 0;
        if (matched) return;
    }
    _dos_setdrive(c2inf.cd_letter - 0x40, &saved_drive);
    p[0] = c2inf.cd_letter;
    chdir(p);
    if      (strcmp("PL8", extension) == 0) chdir("pl8");
    else if (strcmp("RAW", extension) == 0) chdir("raw");
    else if (strcmp("XMI", extension) == 0) chdir("xmi");
    else if (strcmp("SMK", extension) == 0) chdir("smk");
}
""", note="DD: matched in inner block scope")
