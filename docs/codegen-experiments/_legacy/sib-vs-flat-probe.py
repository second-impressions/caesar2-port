"""sib-vs-flat-probe — what triggers `[edx+eax+disp]` SIB vs `[eax+disp]` flat?

FINDING (2026-05-24): cgex probe `ps-style-4-cells` reproduces our RC
codegen exactly (flat addressing, no SIB).  PS uses SIB.  The trigger
is NOT in the bounds-check + 4-cell-stamp pattern — must be earlier
in the function (the pointer_mode dispatch + ref_x/ref_y = div/16
assignments + setup_refresh_area call branch).

Background: in set_mouse_refresh, PS does the per-cell store as
`mov [edx+eax+disp], bl` (SIB form) keeping edx=40y and eax=ref_x
in distinct registers.  Recompile chooses to add them first and use
`mov [eax+disp], dl` (flat form).  This experiment isolates what
source patterns trigger which addressing mode.

No PS reference function — pure codegen survey.  Diff column will
show diff vs the first trial as a relative metric (not meaningful
in absolute).
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="sib-vs-flat-probe",
    ps_function=None,
    prelude="""
extern int  rx;
extern int  ry;
extern char tab[1200];
extern int  mx;
extern int  my;
extern char pmode;
extern void area(int x, int y, int w, int h, int v);
""",
    extra_defs="""
int  rx;
int  ry;
char tab[1200];
int  mx;
int  my;
char pmode;
void area(int x, int y, int w, int h, int v) { (void)x;(void)y;(void)w;(void)h;(void)v; }
""",
)

# Trial 1: two stores, both using x (reusing rx)
exp.add(
    "two-stores-reuse-x",
    """
void f(void) {
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
}
""",
    note="ref_x used twice — does Watcom keep it separate from 40*y?",
)

# Trial 2: single store (rx used once)
exp.add(
    "single-store",
    """
void f(void) {
    tab[40 * ry + rx] = 2;
}
""",
    note="single use of rx — should fuse into single addr",
)

# Trial 3: two stores, second uses different x
exp.add(
    "two-stores-different-x",
    """
void f(void) {
    tab[40 * ry + rx] = 2;
    tab[40 * ry + rx + 1] = 2;
}
""",
    note="rx + 1 second — does Watcom common-subexpr 40*ry?",
)

# Trial 4: pointer base
exp.add(
    "pointer-base",
    """
void f(void) {
    char *p = tab + 40 * ry;
    p[rx] = 2;
    if (rx < 39) p[rx + 1] = 2;
}
""",
    note="explicit row-base pointer",
)

# Trial 5: pointer base via expression
exp.add(
    "pointer-base-int",
    """
void f(void) {
    int row = 40 * ry;
    tab[row + rx] = 2;
    if (rx < 39) tab[row + rx + 1] = 2;
}
""",
    note="int row temp",
)

# Trial 6: pre-add into idx
exp.add(
    "idx-cache",
    """
void f(void) {
    int idx = 40 * ry + rx;
    tab[idx] = 2;
    if (rx < 39) tab[idx + 1] = 2;
}
""",
    note="full idx cache",
)

# Trial 7: ry+1 second (forces re-mul)
exp.add(
    "ry-plus-1-second",
    """
void f(void) {
    tab[40 * ry + rx] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
}
""",
    note="second store with (ry+1)*40 — different y axis",
)

# Trial 8: outer guard ry, inner store
exp.add(
    "outer-rx-guard",
    """
void f(void) {
    if (rx >= 40 || ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
}
""",
    note="with outer guards",
)

# Trial 9: compute as separate adds
exp.add(
    "explicit-adds",
    """
void f(void) {
    tab[40 * ry + rx] = 2;
    if (rx < 39) {
        int p = 40 * ry;
        p = p + rx;
        p = p + 1;
        tab[p] = 2;
    }
}
""",
    note="explicit second-store decomposition",
)

# Trial 10: PS-style bounds checks before multiplication
# This is the actual PS function shape — does PS's prior `cmp edx, 0x28`
# keep rx in a register across the multiplication?
exp.add(
    "ps-style-bounds",
    """
void f(void) {
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
}
""",
    note="PS-style: 4 bounds checks before computation",
)

# Trial 11: bounds + 4-cell stamp
exp.add(
    "ps-style-4-cells",
    """
void f(void) {
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    note="full PS-style 4-cell stamp",
)

# Trial 12: alternate bounds order (y first)
exp.add(
    "y-first-bounds",
    """
void f(void) {
    if (ry < 0 || ry >= 30) return;
    if (rx < 0 || rx >= 40) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
}
""",
    note="y bounds first",
)

# Trial 13: FULL PS source shape
exp.add(
    "full-ps-shape",
    """
void f(void) {
    if (pmode == 6 || pmode == 7) {
        area(mx, my, 3, 3, 2);
        return;
    }
    rx = mx / 16;
    ry = my / 16;
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    note="full PS source: pmode dispatch + global writes + 4-cell stamp",
)

# Trial 14: same but no pmode dispatch
exp.add(
    "no-pmode-dispatch",
    """
void f(void) {
    rx = mx / 16;
    ry = my / 16;
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    note="drop pmode — only global writes + 4-cell",
)

# Trial 15: same but no global writes (no ref_x/ref_y store)
exp.add(
    "no-global-writes",
    """
void f(void) {
    int rx = mx / 16;
    int ry = my / 16;
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    note="local rx/ry only",
)

# Trial 16: full-ps-shape but with -ol (loop opt)
exp.add(
    "full-ps-shape-ol",
    """
void f(void) {
    if (pmode == 6 || pmode == 7) {
        area(mx, my, 3, 3, 2);
        return;
    }
    rx = mx / 16;
    ry = my / 16;
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    cflags="-bt=dos -mf -4r -s -ol",
    note="full PS source + -ol (loop opt)",
)

# Trial 17: + -or (instruction scheduling)
exp.add(
    "full-ps-shape-or",
    """
void f(void) {
    if (pmode == 6 || pmode == 7) {
        area(mx, my, 3, 3, 2);
        return;
    }
    rx = mx / 16;
    ry = my / 16;
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    cflags="-bt=dos -mf -4r -s -or",
    note="full PS source + -or (instruction scheduling)",
)

# Trial 18: + -oe (inline expansion)
exp.add(
    "full-ps-shape-oe",
    """
void f(void) {
    if (pmode == 6 || pmode == 7) {
        area(mx, my, 3, 3, 2);
        return;
    }
    rx = mx / 16;
    ry = my / 16;
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    cflags="-bt=dos -mf -4r -s -oe",
    note="full PS source + -oe (inline expansion)",
)

# Trial 19: -3r (386 reg calling instead of 486)
exp.add(
    "full-ps-shape-3r",
    """
void f(void) {
    if (pmode == 6 || pmode == 7) {
        area(mx, my, 3, 3, 2);
        return;
    }
    rx = mx / 16;
    ry = my / 16;
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    cflags="-bt=dos -mf -3r -s",
    note="full PS source + -3r (386 instead of 486)",
)

# Trial 20: -5r
exp.add(
    "full-ps-shape-5r",
    """
void f(void) {
    if (pmode == 6 || pmode == 7) {
        area(mx, my, 3, 3, 2);
        return;
    }
    rx = mx / 16;
    ry = my / 16;
    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;
    tab[40 * ry + rx] = 2;
    if (rx < 39) tab[40 * ry + rx + 1] = 2;
    if (ry < 29) tab[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29) tab[40 * (ry + 1) + rx + 1] = 2;
}
""",
    cflags="-bt=dos -mf -5r -s",
    note="full PS source + -5r (Pentium)",
)
