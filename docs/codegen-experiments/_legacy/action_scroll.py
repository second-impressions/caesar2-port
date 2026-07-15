"""Codegen experiments for action.c::scroll.

scroll is an important tail-merge donor for many action.c functions.  The
current full-TU residue is small (Rule 16 / shared epilogue direction), but
changes here can cascade through dependents, so keep the source-shape probes
persisted.
"""

from c2.commands.cgex import Experiment

PRELUDE = r"""
extern int pm_x;
extern int pm_y;
extern int map_mode;
extern char zoom_level;
extern char pointer_mode;
extern int mouse_y;
extern int mouse_x;
extern int screen_height;
extern int screen_width;
extern int pm_screen_height;
extern int pm_screen_width;
extern int scroll_amount;
extern char scrolling;
extern char update_map;
extern void setup_map_screen_refresh(void);
extern int scroll_speed(void);
"""

EXTRA_DEFS = r"""
int pm_x;
int pm_y;
int map_mode;
char zoom_level;
char pointer_mode;
int mouse_y;
int mouse_x;
int screen_height;
int screen_width;
int pm_screen_height;
int pm_screen_width;
int scroll_amount;
char scrolling;
char update_map;
void setup_map_screen_refresh(void) {}
int scroll_speed(void) { return 0; }
"""

exp = Experiment(
    name="action_scroll",
    ps_function="scroll",
    prelude=PRELUDE,
    extra_defs=EXTRA_DEFS,
    chk=False,
)

BODY = r"""
    if (mouse_y <= 0 && pm_y > 0) {
        pm_y = pm_y - scroll_amount * 2;
        scrolling = 1;
        update_map = 1;
        setup_map_screen_refresh();
    }
    if (mouse_y >= screen_height && (0xa0 - pm_screen_height) > pm_y) {
        pm_y = pm_y + scroll_amount * 2;
        scrolling = 1;
        update_map = 1;
        setup_map_screen_refresh();
    }
    if (mouse_x <= 0 && pm_x > 0) {
        pm_x = pm_x - scroll_amount;
        scrolling = 1;
        update_map = 1;
        setup_map_screen_refresh();
    }
    if (mouse_x >= screen_width && (0x50 - pm_screen_width) > pm_x) {
        pm_x = pm_x + scroll_amount;
        scrolling = 1;
        update_map = 1;
        setup_map_screen_refresh();
    }

    if (scrolling != 0 && scroll_speed() == 0) {
        pm_x = saved_pm_x;
        pm_y = saved_pm_y;
        scrolling = 0;
    }
"""

exp.add(
    "baseline-early-return",
    r"""
void scroll(void)
{
    int saved_pm_x = pm_x;
    int saved_pm_y = pm_y;
    if (map_mode == 2 && zoom_level == 2) {
        return;
    }
    if (pointer_mode == 5) {
        return;
    }
""" + BODY + "}\n",
    note="current source shape",
)

exp.add(
    "explicit-done-label",
    r"""
void scroll(void)
{
    int saved_pm_x = pm_x;
    int saved_pm_y = pm_y;
    if (map_mode == 2 && zoom_level == 2) {
        goto scroll_done;
    }
    if (pointer_mode == 5) {
        goto scroll_done;
    }
""" + BODY + r"""
scroll_done:
    return;
}
""",
    note="force common local epilogue label",
)

exp.add(
    "single-negative-guard",
    r"""
void scroll(void)
{
    int saved_pm_x = pm_x;
    int saved_pm_y = pm_y;
    if (!(map_mode == 2 && zoom_level == 2) && pointer_mode != 5) {
""" + "\n".join("        " + line if line.strip() else line for line in BODY.splitlines()) + r"""
    }
}
""",
    note="wrap body in one negative guard",
)

exp.add(
    "separate-saved-loads",
    r"""
void scroll(void)
{
    int saved_pm_x;
    int saved_pm_y;
    saved_pm_x = pm_x;
    saved_pm_y = pm_y;
    if (map_mode == 2 && zoom_level == 2) {
        return;
    }
    if (pointer_mode == 5) {
        return;
    }
""" + BODY + "}\n",
    note="C89 assignment after decls",
)
