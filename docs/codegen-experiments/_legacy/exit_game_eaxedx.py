"""act_exit_game — decision/map_mode byte-global reads: EAX (PS) vs EDX (recomp).

PS reads `decision` and `map_mode` into EAX (the short `a0` AL-direct form);
recomp reads them into EDX (the 6-byte `8a 15` form, reusing the register the
named local `t = tutorial_mode` lived in).  The 1-byte-longer DL encoding then
cascades every following offset.  This is a self-contained eax<->edx layer-3
swap (no tail-merge, no param).  Bisect the source shape that keeps the
short-lived byte reads in EAX.

Run::

    uv run c2 cgex run exit_game_eaxedx
    uv run c2 cgex run exit_game_eaxedx --trial baseline
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="exit_game_eaxedx",
    ps_function="act_exit_game",
    externs={
        "click_warning": "extern void click_warning(int a, int b, int c);",
        "show_exit_box": "extern void show_exit_box(void);",
        "exit_game_loop": "extern void exit_game_loop(void);",
        "setup_map_screen_refresh": "extern void setup_map_screen_refresh(void);",
    },
    prelude="""
extern int tutorial_mode;
extern char pointer_mode;
extern int out1;
extern char decision;
extern char exit_flag;
extern char map_mode;
extern int battle_state;
extern char update_map;
""",
    extra_defs="""
int tutorial_mode;
char pointer_mode;
int out1;
char decision;
char exit_flag;
char map_mode;
int battle_state;
char update_map;
""",
)


exp.add(
    "baseline",
    """
void act_exit_game(void)
{
    int t = tutorial_mode;
    if (t != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    pointer_mode = 0;
    show_exit_box();
    out1 = t;
    while (out1 == 0) {
        exit_game_loop();
    }
    if (decision == 1) {
        exit_flag = 1;
        if (map_mode == 2) {
            battle_state = 0xa;
        }
    }
    setup_map_screen_refresh();
    update_map = 1;
}
""",
    note="current source",
)


# Use literal out1 = 0 instead of out1 = t (frees the t/EDX binding earlier).
exp.add(
    "out1_zero",
    """
void act_exit_game(void)
{
    if (tutorial_mode != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    pointer_mode = 0;
    show_exit_box();
    out1 = 0;
    while (out1 == 0) {
        exit_game_loop();
    }
    if (decision == 1) {
        exit_flag = 1;
        if (map_mode == 2) {
            battle_state = 0xa;
        }
    }
    setup_map_screen_refresh();
    update_map = 1;
}
""",
    note="out1 = 0 literal (no t reuse) — may change the t store form",
)


# Cache decision into a named local (Rule 108-ish flip).
exp.add(
    "cache_decision",
    """
void act_exit_game(void)
{
    int t = tutorial_mode;
    int dec;
    if (t != 0) {
        click_warning(2, 0x50, 0xa0);
        return;
    }
    pointer_mode = 0;
    show_exit_box();
    out1 = t;
    while (out1 == 0) {
        exit_game_loop();
    }
    dec = decision;
    if (dec == 1) {
        exit_flag = 1;
        if (map_mode == 2) {
            battle_state = 0xa;
        }
    }
    setup_map_screen_refresh();
    update_map = 1;
}
""",
    note="int dec = decision; named local",
)
