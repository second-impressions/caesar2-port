"""refresh_battle_zoom_mode — Watcom regalloc cascade in trailing
recomputation of pm_screen_x_end / pm_screen_y_end.

PS uses `eax` as the multiplication accumulator for both stores;
recomp uses `edx`.  The cascade adds ~26 b through register
encoding deltas.  Experiment probes which source variation
flips the choice.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
extern char zoom_level;
extern int  scroll_amount;
extern int  pm_screen_width;
extern int  pm_screen_height;
extern int  pm_screen_x_start;
extern int  pm_screen_y_start;
extern int  pm_screen_x_end;
extern int  pm_screen_y_end;
extern int  pm_diamond_width;
extern int  pm_diamond_height;
extern int  pm_diamond_half_width;
extern int  pm_diamond_half_height;
"""

_DEFS = """
char zoom_level;
int  scroll_amount;
int  pm_screen_width;
int  pm_screen_height;
int  pm_screen_x_start;
int  pm_screen_y_start;
int  pm_screen_x_end;
int  pm_screen_y_end;
int  pm_diamond_width;
int  pm_diamond_height;
int  pm_diamond_half_width;
int  pm_diamond_half_height;
"""


exp = Experiment(
    name="refresh-battle-zoom-mode",
    ps_function="refresh_battle_zoom_mode",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# Body templates: only the trailing two-statement tail varies,
# the level==1 and level==2 bodies are identical across trials.
_HEAD = """
void refresh_battle_zoom_mode(int level)
{
    zoom_level = (char)level;
    if ((level & 0xff) == 1) {
        scroll_amount = 2;
        pm_screen_width = 0x17;
        pm_screen_height = 0x30;
        pm_screen_x_start = 0;
        pm_screen_y_start = 0x11;
        pm_diamond_width = 0x1c;
        pm_diamond_height = 0xe;
        pm_diamond_half_width = 0xe;
        pm_diamond_half_height = 7;
    } else if ((level & 0xff) == 2) {
        scroll_amount = 4;
        pm_screen_width = 0x35;
        pm_screen_height = 0x70;
        pm_screen_x_start = 6;
        pm_screen_y_start = 0x15;
        pm_diamond_width = 0xc;
        pm_diamond_height = 6;
        pm_diamond_half_width = 6;
        pm_diamond_half_height = 3;
    }
"""


# ── trial 1: baseline ───────────────────────────────────────────
exp.add(
    "baseline",
    _HEAD + """
    pm_screen_x_end = pm_screen_width * pm_diamond_width + pm_screen_x_start;
    pm_screen_y_end = (pm_screen_height + 1) * pm_diamond_half_height
                      + pm_screen_y_start;
}
""",
    note="natural source; ~26 b regalloc cascade",
)


# ── trial 2: swap order (y_end first) ──────────────────────────
exp.add(
    "swap-order",
    _HEAD + """
    pm_screen_y_end = (pm_screen_height + 1) * pm_diamond_half_height
                      + pm_screen_y_start;
    pm_screen_x_end = pm_screen_width * pm_diamond_width + pm_screen_x_start;
}
""",
    note="swap statement order: y_end first",
)


# ── trial 3: temp ints for both ────────────────────────────────
exp.add(
    "temp-ints",
    _HEAD + """
    {
        int xe = pm_screen_width * pm_diamond_width + pm_screen_x_start;
        int ye = (pm_screen_height + 1) * pm_diamond_half_height
                 + pm_screen_y_start;
        pm_screen_x_end = xe;
        pm_screen_y_end = ye;
    }
}
""",
    note="hoist into local temps before stores",
)


# ── trial 4: operand order (start first) ───────────────────────
exp.add(
    "start-first",
    _HEAD + """
    pm_screen_x_end = pm_screen_x_start + pm_screen_width * pm_diamond_width;
    pm_screen_y_end = pm_screen_y_start
                      + (pm_screen_height + 1) * pm_diamond_half_height;
}
""",
    note="put _start first in the addition",
)


# ── trial 5: explicit hp1 temp for height+1 ────────────────────
exp.add(
    "explicit-hp1",
    _HEAD + """
    {
        int hp1 = pm_screen_height + 1;
        pm_screen_x_end = pm_screen_width * pm_diamond_width + pm_screen_x_start;
        pm_screen_y_end = hp1 * pm_diamond_half_height + pm_screen_y_start;
    }
}
""",
    note="hoist (height+1) into a named local",
)


# ── trial 6: cast level differently in the if checks ───────────
exp.add(
    "char-level-tests",
    """
void refresh_battle_zoom_mode(int level)
{
    zoom_level = (char)level;
    if (zoom_level == 1) {
        scroll_amount = 2;
        pm_screen_width = 0x17;
        pm_screen_height = 0x30;
        pm_screen_x_start = 0;
        pm_screen_y_start = 0x11;
        pm_diamond_width = 0x1c;
        pm_diamond_height = 0xe;
        pm_diamond_half_width = 0xe;
        pm_diamond_half_height = 7;
    } else if (zoom_level == 2) {
        scroll_amount = 4;
        pm_screen_width = 0x35;
        pm_screen_height = 0x70;
        pm_screen_x_start = 6;
        pm_screen_y_start = 0x15;
        pm_diamond_width = 0xc;
        pm_diamond_height = 6;
        pm_diamond_half_width = 6;
        pm_diamond_half_height = 3;
    }
    pm_screen_x_end = pm_screen_width * pm_diamond_width + pm_screen_x_start;
    pm_screen_y_end = (pm_screen_height + 1) * pm_diamond_half_height
                      + pm_screen_y_start;
}
""",
    note="test against zoom_level (char) in branches",
)


# ── trial 7: char-cast tests inline ────────────────────────────
exp.add(
    "char-cast-tests",
    """
void refresh_battle_zoom_mode(int level)
{
    zoom_level = (char)level;
    if ((char)level == 1) {
        scroll_amount = 2;
        pm_screen_width = 0x17;
        pm_screen_height = 0x30;
        pm_screen_x_start = 0;
        pm_screen_y_start = 0x11;
        pm_diamond_width = 0x1c;
        pm_diamond_height = 0xe;
        pm_diamond_half_width = 0xe;
        pm_diamond_half_height = 7;
    } else if ((char)level == 2) {
        scroll_amount = 4;
        pm_screen_width = 0x35;
        pm_screen_height = 0x70;
        pm_screen_x_start = 6;
        pm_screen_y_start = 0x15;
        pm_diamond_width = 0xc;
        pm_diamond_height = 6;
        pm_diamond_half_width = 6;
        pm_diamond_half_height = 3;
    }
    pm_screen_x_end = pm_screen_width * pm_diamond_width + pm_screen_x_start;
    pm_screen_y_end = (pm_screen_height + 1) * pm_diamond_half_height
                      + pm_screen_y_start;
}
""",
    note="(char)level == N in tests",
)


# ── trial 8: split exprs into 4 statements each ────────────────
exp.add(
    "split-stmts",
    _HEAD + """
    {
        int xe = pm_screen_width;
        xe *= pm_diamond_width;
        xe += pm_screen_x_start;
        pm_screen_x_end = xe;
        int ye = pm_screen_height;
        ye++;
        ye *= pm_diamond_half_height;
        ye += pm_screen_y_start;
        pm_screen_y_end = ye;
    }
}
""",
    note="step-by-step computations to control evaluation",
)
