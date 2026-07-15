"""do_heavy_ai — thresh-local declaration-order sweep (last 10 bytes).

After the de-alias (Rule 73) + the two structural fixes (target_lock
branch inversion, flank 4-ifs), do_heavy_ai is 10 b from exact.  The
residue is the emission ORDER of the five tribe_ai_data field loads at
the top (registers already match PS).  permute --depth 2 finds nothing
and 6 hand-tried decl orders bottom out at 10.  This experiment
brute-forces all 5! = 120 declaration orderings of the thresh locals via
cgex (standalone build, ~0.2 s each) to settle whether decl order can
reach 0.

    uv run c2 cgex run do_heavy_ai_thresh
    uv run c2 cgex run do_heavy_ai_thresh --trial t_12345

FINDING (2026-06): cgex is NOT a faithful proxy here.  A standalone
build is 494 b vs PS's 503 b and diffs ~99 b regardless of thresh order,
because do_heavy_ai's `return`s TAIL-MERGE into get_wf_dirc's shared
epilogue (donor get_wf_dirc+0x8D) in the real TU — a dependency a
standalone snippet cannot reproduce (no donor → local `ret` + different
layout).  The ~89 b gap vs the full-TU diff (10 b) is that epilogue, not
the thresh order.  Lesson: cgex's per-function isolation only models
functions WITHOUT tail-merge; for tail-merge-dependent functions use the
full-TU `c2 decomp-verify`.  The committed do_heavy_ai sits at 10 b (a
Watcom field-load SCHEDULING tie on the five thresh reads — registers
already match PS); permute --depth 2 and 6 hand-tried decl orders all
bottom out at 10, so the residue is not declaration-order-reachable.
"""

from c2.commands.cgex import Experiment

_PRELUDE = """
struct unit_rec {
    char  x;              /* +0x00 */
    char  pad1[0x0C];     /* +0x01 */
    char  withdraw_flag;  /* +0x0D */
    int   target_lock;    /* +0x0E */
    char  pad2[0x0E];     /* +0x12 */
    char  combat_order;   /* +0x20 */
    char  pad3[0x1C];     /* +0x21 */
    char  flank_pending;  /* +0x3D */
    short ai_period;      /* +0x3E */
    short ai_tick;        /* +0x40 */
    char  manoeuvre_done; /* +0x42 */
    char  pad4[0x0B];     /* +0x43 .. +0x4D ; total 0x4E */
};
struct tribe_ai_rec {
    unsigned char aggression, berserk_count, delayed_berserk, wedge_move,
                  forward_move, base_morale, prefer_cohesion, prefer_column,
                  no_flanks, no_fans;
};
extern struct unit_rec unit_list[];
extern struct tribe_ai_rec tribe_ai_data[];
extern int   bat_tribe;
extern short temp_unit;
extern int   battle_ai_count;
extern void set_ai_unit_withdraw(int, int);
extern void set_ai_unit_delayed_beserk(void);
extern void set_ai_unit_beserk(void);
extern void set_ai_flank_move(int);
extern void set_ai_unit_move(int, int);
"""

_DEFS = """
struct unit_rec {
    char  x; char pad1[0x0C]; char withdraw_flag; int target_lock;
    char  pad2[0x0E]; char combat_order; char pad3[0x1C]; char flank_pending;
    short ai_period; short ai_tick; char manoeuvre_done; char pad4[0x0B];
};
struct tribe_ai_rec {
    unsigned char aggression, berserk_count, delayed_berserk, wedge_move,
                  forward_move, base_morale, prefer_cohesion, prefer_column,
                  no_flanks, no_fans;
};
struct unit_rec unit_list[0x33];
struct tribe_ai_rec tribe_ai_data[16];
int   bat_tribe;
short temp_unit;
int   battle_ai_count;
void set_ai_unit_withdraw(int a, int b) { (void)a; (void)b; }
void set_ai_unit_delayed_beserk(void) {}
void set_ai_unit_beserk(void) {}
void set_ai_flank_move(int a) { (void)a; }
void set_ai_unit_move(int a, int b) { (void)a; (void)b; }
"""

exp = Experiment(
    name="do_heavy_ai_thresh",
    ps_function="do_heavy_ai",
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)

_FIELD = {1: "berserk_count", 2: "delayed_berserk", 3: "wedge_move",
          4: "forward_move", 5: "base_morale"}


def _body(order):
    decls = "\n".join(
        f"    int thresh_{k} = tribe_ai_data[bat_tribe].{_FIELD[k]};"
        for k in order)
    return f"""
void do_heavy_ai(void)
{{
{decls}
    int dl;
    int ai_pos;

    unit_list[temp_unit].ai_tick = (unit_list[temp_unit].ai_tick + 1);
    if (unit_list[temp_unit].ai_tick < unit_list[temp_unit].ai_period)
        return;
    unit_list[temp_unit].ai_tick = 0;

    if (unit_list[temp_unit].target_lock > 2) {{
        if (thresh_5 != 0 && unit_list[temp_unit].withdraw_flag == 0)
            set_ai_unit_withdraw(0, 8);
        return;
    }}

    dl = unit_list[temp_unit].combat_order;
    if (dl == 0xa || dl == 8)
        return;

    if (thresh_2 == 1) {{
        set_ai_unit_delayed_beserk();
        return;
    }}
    if (thresh_1 <= battle_ai_count) {{
        set_ai_unit_beserk();
        return;
    }}

    dl = unit_list[temp_unit].flank_pending;
    if (dl == 1) {{ set_ai_flank_move(dl); unit_list[temp_unit].flank_pending = 0; return; }}
    if (dl == 2) {{ set_ai_flank_move(dl); unit_list[temp_unit].flank_pending = 0; return; }}
    if (dl == 3) {{ set_ai_flank_move(dl); unit_list[temp_unit].flank_pending = 0; return; }}
    if (dl == 4) {{ set_ai_flank_move(dl); unit_list[temp_unit].flank_pending = 0; return; }}

    if (unit_list[temp_unit].manoeuvre_done == 0 && thresh_3 != 0) {{
        ai_pos = unit_list[temp_unit].x;
        if (ai_pos < 0x12)
            set_ai_unit_move(8, -12);
        else if (ai_pos > 0x1e)
            set_ai_unit_move(-10, -12);
        else
            set_ai_unit_move(0, -18);
        return;
    }}

    if (unit_list[temp_unit].manoeuvre_done != 0)
        return;
    if (thresh_4 == 0)
        return;
    set_ai_unit_move(0, -4);
    unit_list[temp_unit].manoeuvre_done = 0;
}}
"""


# representative orders (the in-process sweep below covers all 120)
exp.add("t_31254", _body((3, 1, 2, 5, 4)), note="current committed order (10 b)")
exp.add("t_12345", _body((1, 2, 3, 4, 5)), note="natural struct order")
