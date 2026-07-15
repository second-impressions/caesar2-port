"""do_act_zoom_out — EAX/EDX swap + const-store (push ebx / BL=0) trigger.

PS keeps the *param* `decayed` in EAX and the cached global `zl` (zoom_level)
in EDX; the end-of-function const stores then land in DL (=1) and BL (=0,
push ebx).  Our default build puts the higher-savings `zl` in EAX and moves
`decayed` to EDX, and the const stores land in AH/DH (no push ebx).  Because
that makes do_act_zoom_out's epilogue byte-identical to do_act_zoom_in's,
ComTail spuriously merges them and do_act_zoom_in can't go byte-exact.

Goal: find the C source shape that makes Watcom keep `decayed` in EAX (zl -> EDX),
which cascades the const stores to DL/BL and breaks the bad merge.

Run::

    uv run c2 cgex run zoom_out_conststore
    uv run c2 cgex run zoom_out_conststore --trial baseline
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="zoom_out_conststore",
    ps_function="do_act_zoom_out",
    externs={
        "refresh_zoom_mode": "extern void refresh_zoom_mode(int z);",
        "pm_limits": "extern void pm_limits(void);",
        "setup_map_screen_refresh": "extern void setup_map_screen_refresh(void);",
        "clip_zoom_level1": "extern void clip_zoom_level1(void);",
        "clear_edge_info": "extern void clear_edge_info(void);",
        "load_map_graphics": "extern int load_map_graphics(int mm, int z);",
    },
    prelude="""
extern unsigned char zoom_level;
extern int pm_x;
extern int pm_y;
extern unsigned char update_landfill;
extern unsigned char update_map;
extern unsigned char map_mode;
extern unsigned char pointer_mode;
""",
    extra_defs="""
unsigned char zoom_level;
int pm_x;
int pm_y;
unsigned char update_landfill;
unsigned char update_map;
unsigned char map_mode;
unsigned char pointer_mode;
""",
)


# ── baseline: current source shape (expect ~18 masked diffs) ──────
exp.add(
    "baseline",
    """
void do_act_zoom_out(int decayed)
{
    int zl = zoom_level;
    int new_zoom;
    if (zl == 2) {
        return;
    }
    if (zl == 1 || decayed != 0) {
        pm_x -= 0xc;
        pm_y -= 0x28;
        new_zoom = 2;
        refresh_zoom_mode(new_zoom);
    } else if (zl == 0) {
        pm_x -= 4;
        pm_y -= 0x10;
        new_zoom = 1;
        refresh_zoom_mode(new_zoom);
    }
    pm_limits();
    setup_map_screen_refresh();
    clip_zoom_level1();
    clear_edge_info();
    update_landfill = 1;
    update_map = 1;
    load_map_graphics(map_mode, zoom_level);
    pointer_mode = 0;
}
""",
    note="current source",
)


# ── trial: don't cache zoom_level; read it inline (reloads) ───────
exp.add(
    "inline_zl",
    """
void do_act_zoom_out(int decayed)
{
    if (zoom_level == 2) {
        return;
    }
    if (zoom_level == 1 || decayed != 0) {
        pm_x -= 0xc;
        pm_y -= 0x28;
        refresh_zoom_mode(2);
    } else if (zoom_level == 0) {
        pm_x -= 4;
        pm_y -= 0x10;
        refresh_zoom_mode(1);
    }
    pm_limits();
    setup_map_screen_refresh();
    clip_zoom_level1();
    clear_edge_info();
    update_landfill = 1;
    update_map = 1;
    load_map_graphics(map_mode, zoom_level);
    pointer_mode = 0;
}
""",
    note="no zl cache (Watcom CSEs reloads)",
)


# ── trial: decayed cached into a local read BEFORE zl ─────────────
exp.add(
    "cache_decayed_first",
    """
void do_act_zoom_out(int decayed)
{
    int d = decayed;
    int zl = zoom_level;
    int new_zoom;
    if (zl == 2) {
        return;
    }
    if (zl == 1 || d != 0) {
        pm_x -= 0xc;
        pm_y -= 0x28;
        new_zoom = 2;
        refresh_zoom_mode(new_zoom);
    } else if (zl == 0) {
        pm_x -= 4;
        pm_y -= 0x10;
        new_zoom = 1;
        refresh_zoom_mode(new_zoom);
    }
    pm_limits();
    setup_map_screen_refresh();
    clip_zoom_level1();
    clear_edge_info();
    update_landfill = 1;
    update_map = 1;
    load_map_graphics(map_mode, zoom_level);
    pointer_mode = 0;
}
""",
    note="int d = decayed; before zl",
)


# ── trial: use decayed for the early == 2 guard somehow (raise its uses) ──
exp.add(
    "decayed_guard",
    """
void do_act_zoom_out(int decayed)
{
    int zl = zoom_level;
    int new_zoom;
    if (decayed != 0) {
        if (zl == 2) return;
        pm_x -= 0xc;
        pm_y -= 0x28;
        new_zoom = 2;
        refresh_zoom_mode(new_zoom);
    } else if (zl == 1) {
        pm_x -= 0xc;
        pm_y -= 0x28;
        new_zoom = 2;
        refresh_zoom_mode(new_zoom);
    } else if (zl == 0) {
        pm_x -= 4;
        pm_y -= 0x10;
        new_zoom = 1;
        refresh_zoom_mode(new_zoom);
    } else if (zl == 2) {
        return;
    }
    pm_limits();
    setup_map_screen_refresh();
    clip_zoom_level1();
    clear_edge_info();
    update_landfill = 1;
    update_map = 1;
    load_map_graphics(map_mode, zoom_level);
    pointer_mode = 0;
}
""",
    note="restructure so decayed is checked early (NOTE: changes flow!)",
)
