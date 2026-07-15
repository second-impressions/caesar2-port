"""perform_region_strip_action — regalloc spread (PS edx/ebx/edi vs RC eax/edx).

PS keeps `icon`(last_icon_over)→EDX, the const-0 `zero`→EBX, `after`→EDI
(three callee-saves).  Our recompile packs everything into EAX/EDX:
`icon`→EAX (used directly as the `call [eax*4+disp]` index), `zero`→EDX,
`after`→EAX (reused).

We use the REGION variant as the reference because its dispatch is a clean
function-pointer-array index `city_actions[0x14 + icon]()` (no `btns`
pointer cache), so the only divergence is the register spread itself.

Goal: find a source shape that makes Watcom 10.0a put `icon` in EDX and
spread `zero`/`after` into EBX/EDI, matching PS.

    uv run c2 cgex run strip_action
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="strip_action",
    ps_function="perform_region_strip_action",
    externs={
        "city_actions": "extern void (*city_actions[])(void);",
    },
    prelude="""
extern unsigned char mouse_left_preclick;
extern int last_icon_over;
extern int selected_icon_no;
extern int selected_icon_text;
extern int icon_strip_toggle;
extern int last_icon_used;
extern int update_icon;
""",
    extra_defs="""
void (*city_actions[64])(void);
unsigned char mouse_left_preclick;
int last_icon_over;
int selected_icon_no;
int selected_icon_text;
int icon_strip_toggle;
int last_icon_used;
int update_icon;
""",
)

# ── baseline: current source shape ───────────────────────────────
exp.add(
    "baseline",
    """
int perform_region_strip_action(void)
{
    int icon;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    icon = last_icon_over;
    if (icon < 4) {
        return 0;
    }

    selected_icon_no   = 0;
    selected_icon_text = 0;
    icon_strip_toggle  = 0x1f;

    city_actions[0x14 + icon]();

    {
        int after = last_icon_over;
        if (after >= 0xe && after != 0x12) {
            last_icon_used = after;
            update_icon    = after;
        }
    }
    return 1;
}
""",
    note="current source",
)

# ── named zero local (Rule 110 cache) ────────────────────────────
exp.add(
    "named-zero",
    """
int perform_region_strip_action(void)
{
    int icon;
    int zero;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    icon = last_icon_over;
    if (icon < 4) {
        return 0;
    }

    zero = 0;
    selected_icon_no   = zero;
    selected_icon_text = zero;
    icon_strip_toggle  = 0x1f;

    city_actions[0x14 + icon]();

    {
        int after = last_icon_over;
        if (after >= 0xe && after != 0x12) {
            last_icon_used = after;
            update_icon    = after;
        }
    }
    return 1;
}
""",
    note="explicit zero local",
)

# ── after declared at top (not block) ────────────────────────────
exp.add(
    "after-top",
    """
int perform_region_strip_action(void)
{
    int icon;
    int after;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    icon = last_icon_over;
    if (icon < 4) {
        return 0;
    }

    selected_icon_no   = 0;
    selected_icon_text = 0;
    icon_strip_toggle  = 0x1f;

    city_actions[0x14 + icon]();

    after = last_icon_over;
    if (after >= 0xe && after != 0x12) {
        last_icon_used = after;
        update_icon    = after;
    }
    return 1;
}
""",
    note="after at top scope",
)

# ── after before icon decl ───────────────────────────────────────
exp.add(
    "after-before-icon",
    """
int perform_region_strip_action(void)
{
    int after;
    int icon;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    icon = last_icon_over;
    if (icon < 4) {
        return 0;
    }

    selected_icon_no   = 0;
    selected_icon_text = 0;
    icon_strip_toggle  = 0x1f;

    city_actions[0x14 + icon]();

    after = last_icon_over;
    if (after >= 0xe && after != 0x12) {
        last_icon_used = after;
        update_icon    = after;
    }
    return 1;
}
""",
    note="after declared before icon",
)

# ── reuse the icon variable for the after-check (single var) ─────
exp.add(
    "reuse-icon",
    """
int perform_region_strip_action(void)
{
    int icon;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    icon = last_icon_over;
    if (icon < 4) {
        return 0;
    }

    selected_icon_no   = 0;
    selected_icon_text = 0;
    icon_strip_toggle  = 0x1f;

    city_actions[0x14 + icon]();

    icon = last_icon_over;
    if (icon >= 0xe && icon != 0x12) {
        last_icon_used = icon;
        update_icon    = icon;
    }
    return 1;
}
""",
    note="reuse icon var for after",
)

# ── index via separate pointer (btns cache style) ────────────────
exp.add(
    "ptr-cache",
    """
int perform_region_strip_action(void)
{
    int icon;
    void (**btns)(void);

    if (mouse_left_preclick == 0) {
        return 0;
    }
    icon = last_icon_over;
    if (icon < 4) {
        return 0;
    }

    selected_icon_no   = 0;
    selected_icon_text = 0;
    icon_strip_toggle  = 0x1f;

    btns = city_actions + 0x14;
    btns[icon]();

    {
        int after = last_icon_over;
        if (after >= 0xe && after != 0x12) {
            last_icon_used = after;
            update_icon    = after;
        }
    }
    return 1;
}
""",
    note="btns pointer cache like city",
)

# ── compute index into separate local ────────────────────────────
exp.add(
    "idx-local",
    """
int perform_region_strip_action(void)
{
    int icon;
    int idx;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    icon = last_icon_over;
    if (icon < 4) {
        return 0;
    }

    selected_icon_no   = 0;
    selected_icon_text = 0;
    icon_strip_toggle  = 0x1f;

    idx = 0x14 + icon;
    city_actions[idx]();

    {
        int after = last_icon_over;
        if (after >= 0xe && after != 0x12) {
            last_icon_used = after;
            update_icon    = after;
        }
    }
    return 1;
}
""",
    note="index in separate local",
)

# ── named zero + after at top ────────────────────────────────────
exp.add(
    "zero-and-after-top",
    """
int perform_region_strip_action(void)
{
    int icon;
    int zero;
    int after;

    if (mouse_left_preclick == 0) {
        return 0;
    }
    icon = last_icon_over;
    if (icon < 4) {
        return 0;
    }

    zero = 0;
    selected_icon_no   = zero;
    selected_icon_text = zero;
    icon_strip_toggle  = 0x1f;

    city_actions[0x14 + icon]();

    after = last_icon_over;
    if (after >= 0xe && after != 0x12) {
        last_icon_used = after;
        update_icon    = after;
    }
    return 1;
}
""",
    note="zero local + after at top",
)
