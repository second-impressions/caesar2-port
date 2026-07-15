"""set_mouse_refresh — Watcom regalloc cascade for ref_x / ref_y.

PS.EXE function `set_mouse_refresh` (259 b @ 0x28EB2) marks an up-to-2×2
cluster at (ref_x, ref_y) priority 2 in svga_refresh_table.

The natural C source produces ~44 b diff with two artefacts:

  1. Rule 28 callee-save swap: PS uses ebp where RC uses edi.
  2. SIB-vs-flat addressing for cells 1+2 of the 2×2 stamp:
     PS keeps edx=40*ref_y + eax=ref_x as separate registers and
     stores via [edx + eax + svga + N], while RC merges into
     eax = 40*ref_y + ref_x and stores via [eax + svga + N].

This experiment probes source variations to find the trigger.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="set-mouse-refresh",
    ps_function="set_mouse_refresh",
    externs={
        "setup_refresh_area":
            "extern void setup_refresh_area(int x, int y, int w, int h, int v);",
    },
    prelude="""
extern int  ref_x;
extern int  ref_y;
extern int  ref_ptr;
extern int  mouse_x;
extern int  mouse_y;
extern char pointer_mode;
extern char svga_refresh_table[];
""",
    extra_defs="""
int  ref_x;
int  ref_y;
int  ref_ptr;
int  mouse_x;
int  mouse_y;
char pointer_mode;
char svga_refresh_table[1200];
""",
)


# ── trial 1: baseline (current decomp source) ────────────────────
exp.add(
    "baseline",
    """
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    svga_refresh_table[40 * ref_y + ref_x] = 2;
    if (ref_x < 39)
        svga_refresh_table[40 * ref_y + ref_x + 1] = 2;
    if (ref_y < 29)
        svga_refresh_table[40 * (ref_y + 1) + ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[40 * (ref_y + 1) + ref_x + 1] = 2;
}
""",
    note="natural source; ~44 b regalloc cascade",
)


# ── trial 2: short-circuit-and bounds with single guard ─────────
exp.add(
    "single-guard",
    """
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x >= 0 && ref_y >= 0 && ref_x < 40 && ref_y < 30) {
        svga_refresh_table[40 * ref_y + ref_x] = 2;
        if (ref_x < 39)
            svga_refresh_table[40 * ref_y + ref_x + 1] = 2;
        if (ref_y < 29)
            svga_refresh_table[40 * (ref_y + 1) + ref_x] = 2;
        if (ref_x < 39 && ref_y < 29)
            svga_refresh_table[40 * (ref_y + 1) + ref_x + 1] = 2;
    }
}
""",
    note="merged bounds into single nested-if",
)


# ── trial 3: explicit yoff local ────────────────────────────────
exp.add(
    "yoff-local",
    """
void set_mouse_refresh(void)
{
    int yoff;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    yoff = 40 * ref_y;
    svga_refresh_table[yoff + ref_x] = 2;
    if (ref_x < 39)
        svga_refresh_table[yoff + ref_x + 1] = 2;
    if (ref_y < 29)
        svga_refresh_table[40 * (ref_y + 1) + ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[40 * (ref_y + 1) + ref_x + 1] = 2;
}
""",
    note="explicit yoff local for shared base",
)


# ── trial 4: nested if-tree (2x2 short-circuit) ────────────────
exp.add(
    "nested-if",
    """
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    svga_refresh_table[40 * ref_y + ref_x] = 2;
    if (ref_x < 39) {
        svga_refresh_table[40 * ref_y + ref_x + 1] = 2;
    }
    if (ref_y < 29) {
        svga_refresh_table[40 * (ref_y + 1) + ref_x] = 2;
        if (ref_x < 39) {
            svga_refresh_table[40 * (ref_y + 1) + ref_x + 1] = 2;
        }
    }
}
""",
    note="nested ifs: ref_y<29 outer, ref_x<39 inner",
)


# ── trial 5: nested swap (ref_x outer, ref_y inner) ────────────
exp.add(
    "nested-swap",
    """
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    svga_refresh_table[40 * ref_y + ref_x] = 2;
    if (ref_y < 29) {
        svga_refresh_table[40 * (ref_y + 1) + ref_x] = 2;
    }
    if (ref_x < 39) {
        svga_refresh_table[40 * ref_y + ref_x + 1] = 2;
        if (ref_y < 29) {
            svga_refresh_table[40 * (ref_y + 1) + ref_x + 1] = 2;
        }
    }
}
""",
    note="nested ifs: ref_x<39 outer, ref_y<29 inner",
)


# ── trial 6: cell 1 only — minimal repro of SIB choice ────────
exp.add(
    "minimal-sib",
    """
void set_mouse_refresh(void)
{
    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;
    svga_refresh_table[40 * ref_y + ref_x] = 2;
    if (ref_x < 39)
        svga_refresh_table[40 * ref_y + ref_x + 1] = 2;
}
""",
    note="minimal: just the 2 SIB-shareable stores",
)


# ── trial 7: register hint via const-cast ──────────────────────
exp.add(
    "const-ref",
    """
void set_mouse_refresh(void)
{
    const int rx = ref_x;
    const int ry = ref_y;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    svga_refresh_table[40 * ref_y + ref_x] = 2;
    if (ref_x < 39)
        svga_refresh_table[40 * ref_y + ref_x + 1] = 2;
    if (ref_y < 29)
        svga_refresh_table[40 * (ref_y + 1) + ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[40 * (ref_y + 1) + ref_x + 1] = 2;
    (void)rx; (void)ry;
}
""",
    note="dummy const reads at top to dirty regalloc state",
)


# ── trial 8: precompute idx, single-stamp variants ─────────────
exp.add(
    "idx-precomp",
    """
void set_mouse_refresh(void)
{
    int idx;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    idx = 40 * ref_y + ref_x;
    svga_refresh_table[idx] = 2;
    if (ref_x < 39)
        svga_refresh_table[idx + 1] = 2;
    if (ref_y < 29)
        svga_refresh_table[idx + 40] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[idx + 41] = 2;
}
""",
    note="precompute idx once, reuse for all 4 stamps",
)


# ── trial 9: ref_ptr direct (mirror refresh_sprite_square style) ─
exp.add(
    "ref-ptr-direct",
    """
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    ref_ptr = 40 * ref_y + ref_x;
    svga_refresh_table[ref_ptr] = 2;
    if (ref_x < 39)
        svga_refresh_table[ref_ptr + 1] = 2;
    if (ref_y < 29)
        svga_refresh_table[ref_ptr + 40] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[ref_ptr + 41] = 2;
}
""",
    note="use global ref_ptr (refresh_sprite_square style)",
)


# ── trial 10: row-off local, additive ref_x ─────────────────────
exp.add(
    "row-off",
    """
void set_mouse_refresh(void)
{
    int row_off;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    row_off = 40 * ref_y;
    svga_refresh_table[row_off + ref_x] = 2;
    if (ref_x < 39)
        svga_refresh_table[row_off + ref_x + 1] = 2;
    if (ref_y < 29) {
        row_off += 40;
        svga_refresh_table[row_off + ref_x] = 2;
        if (ref_x < 39)
            svga_refresh_table[row_off + ref_x + 1] = 2;
    }
}
""",
    note="row_off local, advance by 40 between rows",
)


# ── trial 11: nested-if structure (no merged && check) ──────────
exp.add(
    "nested-row",
    """
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    svga_refresh_table[40 * ref_y + ref_x] = 2;
    if (ref_x < 39)
        svga_refresh_table[40 * ref_y + ref_x + 1] = 2;
    if (ref_y < 29) {
        svga_refresh_table[40 * (ref_y + 1) + ref_x] = 2;
        if (ref_x < 39)
            svga_refresh_table[40 * (ref_y + 1) + ref_x + 1] = 2;
    }
}
""",
    note="merge cells 3+4 under same ref_y<29 check",
)


# ── trial 12: 2D-array view via cast ────────────────────────────
exp.add(
    "2d-cast",
    """
void set_mouse_refresh(void)
{
    char (*table)[40] = (char (*)[40])svga_refresh_table;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    table[ref_y][ref_x] = 2;
    if (ref_x < 39)
        table[ref_y][ref_x + 1] = 2;
    if (ref_y < 29)
        table[ref_y + 1][ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        table[ref_y + 1][ref_x + 1] = 2;
}
""",
    note="char[40] 2D view of svga_refresh_table",
)


# ── trial 13: 2D-array as direct extern ─────────────────────────
exp.add(
    "2d-extern",
    """
extern char svga_refresh_table_2d[30][40];

void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    svga_refresh_table_2d[ref_y][ref_x] = 2;
    if (ref_x < 39)
        svga_refresh_table_2d[ref_y][ref_x + 1] = 2;
    if (ref_y < 29)
        svga_refresh_table_2d[ref_y + 1][ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table_2d[ref_y + 1][ref_x + 1] = 2;
}
""",
    note="extern svga_refresh_table_2d[30][40] as fresh 2D",
)


# ── trial 14: separate xv/yv locals (early reads) ───────────────
exp.add(
    "xv-yv-locals",
    """
void set_mouse_refresh(void)
{
    int xv, yv;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    xv = mouse_x / 16;
    yv = mouse_y / 16;
    ref_x = xv;
    ref_y = yv;

    if (xv < 0) return;
    if (yv < 0) return;
    if (xv >= 40) return;
    if (yv >= 30) return;

    svga_refresh_table[40 * yv + xv] = 2;
    if (xv < 39)
        svga_refresh_table[40 * yv + xv + 1] = 2;
    if (yv < 29)
        svga_refresh_table[40 * (yv + 1) + xv] = 2;
    if (xv < 39 && yv < 29)
        svga_refresh_table[40 * (yv + 1) + xv + 1] = 2;
}
""",
    note="locals xv/yv keep ref_x/ref_y access in registers",
)


# ── trial 15: const ref_y read into local first ────────────────
exp.add(
    "ry-first",
    """
void set_mouse_refresh(void)
{
    int ry, rx;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    rx = ref_x;
    ry = ref_y;

    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;

    svga_refresh_table[ry * 40 + rx] = 2;
    if (rx < 39)
        svga_refresh_table[ry * 40 + rx + 1] = 2;
    if (ry < 29)
        svga_refresh_table[(ry + 1) * 40 + ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[(ref_y + 1) * 40 + ref_x + 1] = 2;
}
""",
    note="ry/rx locals before bounds checks; mix locals & globals in stamps",
)


# ── trial 16: tight cell-1 only, gradual extension ─────────────
exp.add(
    "minimal-l61",
    """
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    /* Cell 1+2: shared 40*ref_y base */
    {
        char v = 2;
        svga_refresh_table[40 * ref_y + ref_x] = v;
        if (ref_x < 39)
            svga_refresh_table[40 * ref_y + ref_x + 1] = v;
    }
    if (ref_y < 29)
        svga_refresh_table[40 * (ref_y + 1) + ref_x] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[40 * (ref_y + 1) + ref_x + 1] = 2;
}
""",
    note="explicit char v=2 local for cells 1+2 (PS uses bl)",
)


# ── trial 17: register-keyword hint on ref_y mirror ────────────
exp.add(
    "register-hint",
    """
void set_mouse_refresh(void)
{
    register int ry, rx;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    rx = mouse_x / 16;
    ry = mouse_y / 16;
    ref_x = rx;
    ref_y = ry;

    if (rx < 0) return;
    if (ry < 0) return;
    if (rx >= 40) return;
    if (ry >= 30) return;

    svga_refresh_table[40 * ry + rx] = 2;
    if (rx < 39)
        svga_refresh_table[40 * ry + rx + 1] = 2;
    if (ry < 29)
        svga_refresh_table[40 * (ry + 1) + rx] = 2;
    if (rx < 39 && ry < 29)
        svga_refresh_table[40 * (ry + 1) + rx + 1] = 2;
}
""",
    note="register int rx/ry locals — Watcom register hint",
)


# ── trial 18: index expression x first (Rule 57-ish probe) ─────
exp.add(
    "x-plus-y40",
    """
void set_mouse_refresh(void)
{
    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    svga_refresh_table[ref_x + 40 * ref_y] = 2;
    if (ref_x < 39)
        svga_refresh_table[ref_x + 40 * ref_y + 1] = 2;
    if (ref_y < 29)
        svga_refresh_table[ref_x + 40 * (ref_y + 1)] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[ref_x + 40 * (ref_y + 1) + 1] = 2;
}
""",
    note="index source order: ref_x + 40*ref_y (does it keep row base separate?)",
)


# ── trial 19: split row base local + x-first addressing ─────────
exp.add(
    "base-local-x-first",
    """
void set_mouse_refresh(void)
{
    int base;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    base = 40 * ref_y;
    svga_refresh_table[ref_x + base] = 2;
    if (ref_x < 39)
        svga_refresh_table[ref_x + base + 1] = 2;
    if (ref_y < 29)
        svga_refresh_table[ref_x + base + 40] = 2;
    if (ref_x < 39 && ref_y < 29)
        svga_refresh_table[ref_x + base + 41] = 2;
}
""",
    note="explicit row base local, but source address order ref_x + base",
)


# ── trial 20: late ref_y local, matching PS's post-first-row load ─
exp.add(
    "late-y-local",
    """
void set_mouse_refresh(void)
{
    int y;

    if (pointer_mode == 6 || pointer_mode == 7) {
        setup_refresh_area(mouse_x, mouse_y, 3, 3, 2);
        return;
    }

    ref_x = mouse_x / 16;
    ref_y = mouse_y / 16;

    if (ref_x < 0) return;
    if (ref_y < 0) return;
    if (ref_x >= 40) return;
    if (ref_y >= 30) return;

    svga_refresh_table[40 * ref_y + ref_x] = 2;
    if (ref_x < 39)
        svga_refresh_table[40 * ref_y + ref_x + 1] = 2;

    y = ref_y;
    if (y < 29)
        svga_refresh_table[40 * (y + 1) + ref_x] = 2;
    if (ref_x < 39 && y < 29)
        svga_refresh_table[40 * (y + 1) + ref_x + 1] = 2;
}
""",
    note="late y=ref_y local after first-row stores; PS loads ref_y into ebp there",
)
