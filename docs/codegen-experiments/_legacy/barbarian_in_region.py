"""barbarian_in_region — EAX vs EDX scratch in map_ref block.

PS @ 0x53688, 238 bytes.  Currently 3 b diff at +0xBB, +0xC2, +0xC8
(post-merge map_ref read).

PS:  movsx eax, word [created_army_no]
     imul eax, eax, 0xaf
     mov edx, [eax + 0x846c0]      <- scratch in EAX, map_ref in EDX

RC:  movsx edx, word [created_army_no]
     imul edx, edx, 0xaf
     mov edx, [edx + 0x846c0]      <- scratch and map_ref both in EDX

Sibling raider_in_region is byte-exact and uses EAX for the same scratch
slot — but raider has target_x=0; target_y=0 stores in between, which
re-use the scratch EAX.  Barbarian lacks those stores so the scratch
is only used once.

Goal: find the source shape that forces EAX (or any non-EDX) for the
scratch in barbarian.

Run::

    uv run c2 cgex run barbarian_in_region
    uv run c2 cgex run barbarian_in_region --trial baseline
"""

from c2.commands.cgex import Experiment


_PRELUDE = """
struct army_rec {
    char        pad00[8];
    int         map_ref;          /* +0x08 */
    char        pad0C[2];
    signed char target_x;         /* +0x0E */
    signed char target_y;         /* +0x0F */
    char        saved_state_idx;  /* +0x10 */
    signed char wait_count;       /* +0x11 */
    signed char state_idx;        /* +0x12 */
    char        pad13[0x1D];
    char        army_id;          /* +0x30 */
    char        pad31[0x63];
    char        target_kind;      /* +0x94 */
    char        pad95[26];        /* pad to 0xAF total */
};
extern struct army_rec army_list[];
extern short created_army_no;
extern int   barb_x, barb_y;
extern unsigned char rand128;
extern int  get_region_invasion_points(int dirc, int from_sea);
extern int  create_army(int kind, int x, int y, int from_sea_flag);
extern void put_message(int msg, int map_ref, int arg3);
"""

_DEFS = _PRELUDE + """
struct army_rec army_list[300];
short created_army_no;
int   barb_x, barb_y;
unsigned char rand128;

int  get_region_invasion_points(int dirc, int from_sea){return 0;}
int  create_army(int kind, int x, int y, int s){return 0;}
void put_message(int m, int r, int a){}
"""

exp = Experiment(
    name="barbarian_in_region",
    ps_function="barbarian_in_region",
    chk=False,  # PS prologue has no __CHK probe for this function
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# ── A: baseline — current source shape (block-scope int map_ref) ─────────
exp.add("baseline", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        int map_ref = army_list[created_army_no].map_ref;
        if (map_ref == 0) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="baseline (current source)")


# ── B: function-scope declaration of map_ref ─────────────────────────────
exp.add("B_func_scope_decl", """
int barbarian_in_region(int dirc, int from_sea)
{
    int map_ref;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    map_ref = army_list[created_army_no].map_ref;
    if (map_ref == 0) map_ref = 8;
    put_message(0x5d, map_ref, 0x11);
    return 1;
}
""", note="map_ref declared at function scope")


# ── C: ternary in the put_message call ────────────────────────────────────
exp.add("C_ternary_inline", """
int barbarian_in_region(int dirc, int from_sea)
{
    int map_ref;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    map_ref = army_list[created_army_no].map_ref;
    put_message(0x5d, map_ref == 0 ? 8 : map_ref, 0x11);
    return 1;
}
""", note="ternary as put_message arg2")


# ── D: dummy use of created_army_no via extra read ──────────────────────
exp.add("D_extra_read", """
int barbarian_in_region(int dirc, int from_sea)
{
    int map_ref;
    int n;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    n = created_army_no;
    map_ref = army_list[n].map_ref;
    if (map_ref == 0) map_ref = 8;
    put_message(0x5d, map_ref, 0x11);
    return 1;
}
""", note="cache created_army_no in local n")


# ── E: redundant target_x/y=0 like raider ─────────────────────────────────
exp.add("E_target_xy_clear", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    army_list[created_army_no].target_y = 0;
    army_list[created_army_no].target_x = 0;

    {
        int map_ref = army_list[created_army_no].map_ref;
        if (map_ref == 0) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="redundant target_x/y=0 like raider")


# ── F: separate intermediate addr temp ───────────────────────────────────
exp.add("F_addr_temp", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        struct army_rec *a = &army_list[created_army_no];
        int map_ref = a->map_ref;
        if (map_ref == 0) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="cache &army_list[created_army_no] in local")


# ── G: created_army_no in EAX before map_ref read ────────────────────────
exp.add("G_assign_via_idx", """
int barbarian_in_region(int dirc, int from_sea)
{
    int idx;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        idx = created_army_no;
        army_list[idx].state_idx        = 0xe;
        army_list[idx].wait_count       = 0;
        army_list[idx].target_kind      = 4;
        army_list[idx].saved_state_idx  = 7;
        army_list[idx].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        idx = created_army_no;
        army_list[idx].state_idx        = 1;
        army_list[idx].wait_count       = 0x14;
        army_list[idx].target_kind      = 4;
        army_list[idx].saved_state_idx  = 7;
    }

    {
        int map_ref = army_list[created_army_no].map_ref;
        if (map_ref == 0) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="cache idx per-branch")


# ── H: put_message via temp args (force EBX/EAX setup before map_ref) ────
exp.add("H_args_first", """
int barbarian_in_region(int dirc, int from_sea)
{
    int msg;
    int p3;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        int map_ref = army_list[created_army_no].map_ref;
        if (map_ref == 0) map_ref = 8;
        msg = 0x5d;
        p3  = 0x11;
        put_message(msg, map_ref, p3);
    }
    return 1;
}
""", note="msg/p3 in locals before put_message call")


# ── I: do-not-eliminate the map_ref temp via volatile-like write ─────────
exp.add("I_volatile_int", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        volatile int map_ref = army_list[created_army_no].map_ref;
        if (map_ref == 0) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="volatile map_ref")


# ── J: a separate scratch int = army_list[n].map_ref pattern (force temp) ─
exp.add("J_two_step_load", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        int map_ref;
        int *p = &army_list[created_army_no].map_ref;
        map_ref = *p;
        if (map_ref == 0) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="separate int *p then load")


# ── L: PS line-pattern — declare+if on ONE line (matches L289 cue) ───────
# PS asm shows the L287→L289 cue gap is 1 source line (288 blank);
# our baseline puts 3 lines (decl, if, put_message) between L40 and L44.
exp.add("L_psline_match", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {   int map_ref = army_list[created_army_no].map_ref;  if (map_ref == 0)  map_ref = 8;

        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="decl + if on one source line (mirror PS L289)")


# ── M: no { } block at all, function-scope decl, decl+if on one line ─────
exp.add("M_no_block_one_line", """
int barbarian_in_region(int dirc, int from_sea)
{
    int map_ref;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    map_ref = army_list[created_army_no].map_ref;  if (map_ref == 0)  map_ref = 8;

    put_message(0x5d, map_ref, 0x11);
    return 1;
}
""", note="no block, function-scope decl, assign+if one line")


# ── N: explicit idx cached as int, load via cast pointer arithmetic ─────
# Forces scratch (idx*0xaf) into a distinct named temp from map_ref.
exp.add("N_explicit_idx", """
int barbarian_in_region(int dirc, int from_sea)
{
    int idx;
    int map_ref;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    idx = created_army_no * 0xaf;
    map_ref = *(int *)((char *)army_list + idx + 8);
    if (map_ref == 0) map_ref = 8;
    put_message(0x5d, map_ref, 0x11);
    return 1;
}
""", note="explicit int idx + raw ptr arithmetic")


# ── O: paint a byte field after the load — gives scratch a 2nd use ──────
# Same shape as raider's target_y/target_x writes but using a field PS
# actually writes elsewhere (state_idx already written) — see if Watcom
# DCEs it.
exp.add("O_extra_field_after_load", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        int map_ref = army_list[created_army_no].map_ref;
        army_list[created_army_no].saved_state_idx = 7;   /* redundant store */
        if (map_ref == 0) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="redundant saved_state_idx=7 after load (creates 2nd scratch use)")


# ── P: declare map_ref earlier — function scope, with multi-block use ────
exp.add("P_map_ref_top", """
int barbarian_in_region(int dirc, int from_sea)
{
    int map_ref = 0;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    map_ref = army_list[created_army_no].map_ref;
    if (map_ref == 0) map_ref = 8;
    put_message(0x5d, map_ref, 0x11);
    return 1;
}
""", note="map_ref declared+init at function top, reassigned later")


# ── Q: do the map_ref check via < 1 instead of == 0 ───────────────────────
exp.add("Q_lt_one", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        int map_ref = army_list[created_army_no].map_ref;
        if (map_ref < 1) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="< 1 instead of == 0")


# ── R: split into two statements with assignment after if ─────────────────
exp.add("R_negate_test", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        int map_ref = army_list[created_army_no].map_ref;
        if (!map_ref) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="!map_ref instead of ==0")


# ── S: use the value as put_message arg, then test ────────────────────────
exp.add("S_test_after_call", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        int map_ref;
        map_ref = army_list[created_army_no].map_ref;
        map_ref = map_ref == 0 ? 8 : map_ref;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="assign+test as ternary")


# ── T: map_ref read into existing reg via field of separate array ─────────
# Tests if Watcom puts the scratch in EAX when there's no register
# constraint coupling between scratch and result temp.
exp.add("T_indirect_load", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    {
        int *p = &army_list[created_army_no].map_ref;
        int map_ref = *p;
        if (map_ref == 0) map_ref = 8;
        put_message(0x5d, map_ref, 0x11);
    }
    return 1;
}
""", note="int *p first, then *p")


# ── U: explicit int variable holding created_army_no, used twice ─────────
exp.add("U_n_used_twice", """
int barbarian_in_region(int dirc, int from_sea)
{
    int n;
    int map_ref;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        n = created_army_no;
        army_list[n].state_idx        = 0xe;
        army_list[n].wait_count       = 0;
        army_list[n].target_kind      = 4;
        army_list[n].saved_state_idx  = 7;
        army_list[n].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        n = created_army_no;
        army_list[n].state_idx        = 1;
        army_list[n].wait_count       = 0x14;
        army_list[n].target_kind      = 4;
        army_list[n].saved_state_idx  = 7;
    }

    map_ref = army_list[n].map_ref;
    if (map_ref == 0) map_ref = 8;
    put_message(0x5d, map_ref, 0x11);
    return 1;
}
""", note="cache n=created_army_no per branch, reuse in load")


# ── K: nested expression: put_message arg2 = (map_ref==0)?8:map_ref ──────
exp.add("K_inline_no_local", """
int barbarian_in_region(int dirc, int from_sea)
{
    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].target_kind      = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    put_message(0x5d,
                army_list[created_army_no].map_ref == 0
                    ? 8 : army_list[created_army_no].map_ref,
                0x11);
    return 1;
}
""", note="ternary inline, no local map_ref")
