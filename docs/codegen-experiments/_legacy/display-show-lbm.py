"""show_lbm — two-byte readfile-result register tie experiment."""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="display-show-lbm",
    ps_function="show_lbm",
    externs={
        "readfile": 'extern int readfile(char *fname, void *buf, int size, int offset);',
        "no_high_beeps": 'extern void no_high_beeps(int n);',
        "stop_system": 'extern void stop_system(void);',
        "printf": 'extern int printf(char *fmt);',
        "exit": 'extern void exit(int code);',
        "convert_lbm_file": 'extern void convert_lbm_file(int dst, int src, int pal);',
        "flush_sb_buffer": 'extern void flush_sb_buffer(void);',
    },
    prelude="""
extern int scratch_buffer;
extern int scratch_buffer_size;
extern int internal_screen;
extern int temp_palette[];
""",
    extra_defs="""
int scratch_buffer;
int scratch_buffer_size;
int internal_screen;
int temp_palette[256];
""",
)

base = r'''
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
'''
exp.add("baseline", base, note="current source: 2b ECX/EDX choice")

exp.add("compound-if", r'''
void show_lbm(char *fname)
{
    int rc;

    if ((rc = readfile(fname, (void *)scratch_buffer,
                       scratch_buffer_size, 0)) >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="assignment inside if")

exp.add("else-if", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    } else if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="else-if layout")

exp.add("rc-init", base.replace("int rc;", "int rc = 0;"), note="initializer")
exp.add("register-rc", base.replace("int rc;", "register int rc;"), note="register hint")
exp.add("fname-alias", base.replace("int rc;", "int rc;\n    char *name = fname;").replace("readfile(fname,", "readfile(name,"), note="alias fname")

exp.add("call-wrapper", r'''
static int rf(char *fname)
{
    return readfile(fname, (void *)scratch_buffer, scratch_buffer_size, 0);
}

void show_lbm(char *fname)
{
    int rc;

    rc = rf(fname);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="local wrapper perturbation")

exp.add("two-tests-nested", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc < scratch_buffer_size) {
        if (rc != 0) {
            convert_lbm_file(internal_screen, scratch_buffer,
                             (int)&temp_palette);
        }
        flush_sb_buffer();
        return;
    }
    no_high_beeps(1);
    stop_system();
    printf("Exit from c2 tutorial mode .lbm file too large.\n");
    exit(100);
    flush_sb_buffer();
}
''', note="invert oversized branch")

exp.add("offset-local", r'''
void show_lbm(char *fname)
{
    int rc;
    int offset;

    offset = 0;
    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, offset);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="named offset=0")

exp.add("offset-reuse-rc", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = 0;
    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, rc);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="rc also supplies offset")

exp.add("offset-local-after", r'''
void show_lbm(char *fname)
{
    int rc;
    int offset = 0;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, offset);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="initialized offset local")

exp.add("short-second-test", base.replace("if (rc != 0)", "if ((short)rc != 0)"), note="second test narrows rc")
exp.add("unsigned-second-test", base.replace("if (rc != 0)", "if ((unsigned)rc != 0)"), note="unsigned second test")
exp.add("not-eq-zero-explicit", base.replace("if (rc != 0)", "if (0 != rc)"), note="commute zero compare")
exp.add("rc-plus-zero", base.replace("if (rc != 0)", "if ((rc + 0) != 0)"), note="rc+0 in second test")

exp.add("rc-as-static", r'''
static int rc_global;
void show_lbm(char *fname)
{
    rc_global = readfile(fname, (void *)scratch_buffer,
                         scratch_buffer_size, 0);
    if (rc_global >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc_global != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="rc as static global")

exp.add("dummy-int-before-rc", r'''
void show_lbm(char *fname)
{
    int dummy;
    int rc;

    dummy = 0;
    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, dummy);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="dummy local before rc")

exp.add("dummy-after-rc", r'''
void show_lbm(char *fname)
{
    int rc;
    int dummy;

    dummy = 0;
    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, dummy);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="dummy local after rc")

exp.add("rc-block-scope", r'''
void show_lbm(char *fname)
{
    {
        int rc;
        rc = readfile(fname, (void *)scratch_buffer,
                      scratch_buffer_size, 0);
        if (rc >= scratch_buffer_size) {
            no_high_beeps(1);
            stop_system();
            printf("Exit from c2 tutorial mode .lbm file too large.\n");
            exit(100);
        }
        if (rc != 0) {
            convert_lbm_file(internal_screen, scratch_buffer,
                             (int)&temp_palette);
        }
    }
    flush_sb_buffer();
}
''', note="rc inside inner block")

exp.add("goto-form", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc < scratch_buffer_size) goto convert;
    no_high_beeps(1);
    stop_system();
    printf("Exit from c2 tutorial mode .lbm file too large.\n");
    exit(100);
convert:
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="goto convert")

exp.add("addr-rc-taken", r'''
extern void noinline_use(int *p);
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    noinline_use(&rc);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="address of rc taken (forces memory)")

exp.add("flush-then-test", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc < scratch_buffer_size) {
        if (rc != 0)
            convert_lbm_file(internal_screen, scratch_buffer,
                             (int)&temp_palette);
        flush_sb_buffer();
        return;
    }
    no_high_beeps(1);
    stop_system();
    printf("Exit from c2 tutorial mode .lbm file too large.\n");
    exit(100);
}
''', note="single oversized branch tail")

exp.add("nonzero-test-first", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc != 0 && rc < scratch_buffer_size) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    flush_sb_buffer();
}
''', note="rc!=0 test first")

exp.add("rc-cast-call", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = (int)readfile(fname, (void *)scratch_buffer,
                       scratch_buffer_size, 0);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="cast call result to int")

exp.add("nested-rc-checks", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc) {
        if (rc >= scratch_buffer_size) {
            no_high_beeps(1);
            stop_system();
            printf("Exit from c2 tutorial mode .lbm file too large.\n");
            exit(100);
        }
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="nest oversize check inside non-zero check")

exp.add("rc-fname-swap-order", r'''
void show_lbm(char *fname)
{
    char *name;
    int rc;

    name = fname;
    rc = readfile(name, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="name local before rc")

exp.add("two-rc-with-second-int", r'''
void show_lbm(char *fname)
{
    int rc, second;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    second = rc;
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (second != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="alias rc to second local")

exp.add("rc-store-load-via-second", r'''
void show_lbm(char *fname)
{
    int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc < scratch_buffer_size) {
        if (rc != 0) {
            convert_lbm_file(internal_screen, scratch_buffer,
                             (int)&temp_palette);
        }
    } else {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    flush_sb_buffer();
}
''', note="if-else with two-test inside")

exp.add("call-volatile-cast", r'''
void show_lbm(char *fname)
{
    volatile int rc;

    rc = readfile(fname, (void *)scratch_buffer,
                  scratch_buffer_size, 0);
    if (rc >= scratch_buffer_size) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="volatile rc")

exp.add("scratch-into-local", r'''
void show_lbm(char *fname)
{
    int rc;
    int sb;

    sb = scratch_buffer_size;
    rc = readfile(fname, (void *)scratch_buffer, sb, 0);
    if (rc >= sb) {
        no_high_beeps(1);
        stop_system();
        printf("Exit from c2 tutorial mode .lbm file too large.\n");
        exit(100);
    }
    if (rc != 0) {
        convert_lbm_file(internal_screen, scratch_buffer,
                         (int)&temp_palette);
    }
    flush_sb_buffer();
}
''', note="cache scratch_buffer_size")
