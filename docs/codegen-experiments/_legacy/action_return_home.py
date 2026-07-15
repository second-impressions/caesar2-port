"""Codegen experiments for action.c::act_set_return_home.

Target: large residual in the route-reset helper.  The full TU shows that
spelling the row_len clear with a volatile loop index blocks Watcom's memset
recognition and improves the real action.c diff substantially.  This cgex
keeps the experiment around and explores nearby C89-style source shapes.
"""

from c2.commands.cgex import Experiment


PRELUDE = r"""
struct army_route_point { char x; char y; };
struct army_route_rec {
    int row_count;
    int chase_row;
    int target_army;
    char army_x;
    char army_y;
    char over_x;
    char over_y;
    unsigned char row_len[10];
    struct army_route_point points[10][16];
};
struct army_rec {
    char _pad00[0x0c];
    char pixel_x;
    char pixel_y;
    char _pad0e[0x12 - 0x0e];
    signed char state_idx;
    char _pad13[0x25 - 0x13];
    signed char flags;
    char _pad26[0x28 - 0x26];
    signed char cohort_id;
    char dest_y;
    char dest_x;
    char _pad2b[0x2c - 0x2b];
    int fort_ref;
    char _pad30[0x9f - 0x30];
    char order_progress;
    char _padA0[0xaf - 0xa0];
};
extern short tracking_army;
extern char pointer_mode;
extern struct army_rec army_list[];
extern struct army_route_rec army_routes[];
extern void unflag_all_rm_xwarehouse(void);
extern void setup_map_screen_refresh(void);
extern void clear_mouse(void);
"""

EXTRA_DEFS = r"""
struct army_route_point { char x; char y; };
struct army_route_rec {
    int row_count;
    int chase_row;
    int target_army;
    char army_x;
    char army_y;
    char over_x;
    char over_y;
    unsigned char row_len[10];
    struct army_route_point points[10][16];
};
struct army_rec {
    char _pad00[0x0c];
    char pixel_x;
    char pixel_y;
    char _pad0e[0x12 - 0x0e];
    signed char state_idx;
    char _pad13[0x25 - 0x13];
    signed char flags;
    char _pad26[0x28 - 0x26];
    signed char cohort_id;
    char dest_y;
    char dest_x;
    char _pad2b[0x2c - 0x2b];
    int fort_ref;
    char _pad30[0x9f - 0x30];
    char order_progress;
    char _padA0[0xaf - 0xa0];
};
short tracking_army;
char pointer_mode;
struct army_rec army_list[200];
struct army_route_rec army_routes[200];
void unflag_all_rm_xwarehouse(void) {}
void setup_map_screen_refresh(void) {}
void clear_mouse(void) {}
#pragma aux __STOSB "*" parm caller []
void __STOSB(void) {}
"""

exp = Experiment(
    name="action_return_home",
    ps_function="act_set_return_home",
    prelude=PRELUDE,
    extra_defs=EXTRA_DEFS,
    chk=False,
)

BASE_DECLS = """
    int idx;
    struct army_route_rec *route;
    int home_ref;
    int q, r;
"""

TAIL = """
    home_ref = army_list[idx].fort_ref;
    q = home_ref / 8;
    r = q % 60;
    army_list[idx].pixel_x = r;
    army_list[idx].pixel_y = (q / 60);
    army_list[idx].state_idx = 5;
    army_list[idx].flags &= ~2;
    army_list[idx].order_progress = 1;
    setup_map_screen_refresh();
    clear_mouse();
}
"""

PROLOGUE = """
    idx = (signed short)tracking_army;
    pointer_mode = 0;
    army_list[idx].dest_y = 0;
    army_list[idx].dest_x = 0;
    unflag_all_rm_xwarehouse();
"""

exp.add(
    "baseline-for",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 0; i < 10; i++) {
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="current source shape before volatile lever",
)

exp.add(
    "volatile-for",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    volatile int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 0; i < 10; i++) {
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="working full-TU lever: block memset recognition",
)

exp.add(
    "volatile-while",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    volatile int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    i = 0;
    while (i < 10) {
        route->row_len[i] = 0;
        i++;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="C89 explicit while loop",
)

exp.add(
    "no-route-cache-volatile",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    volatile int i;
""" + PROLOGUE + """
    for (i = 0; i < 10; i++) {
        army_routes[army_list[idx].cohort_id].row_len[i] = 0;
    }
    route = &army_routes[army_list[idx].cohort_id];
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="avoid cached route in row_len loop",
)

exp.add(
    "local-zero-for",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
    char zero;
""" + PROLOGUE + """
    zero = 0;
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 0; i < 10; i++) {
        route->row_len[i] = zero;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="non-volatile loop using named zero byte",
)

exp.add(
    "global-zero-for",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 0; i < 10; i++) {
        route->row_len[i] = pointer_mode;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="use just-cleared pointer_mode as zero source",
)

exp.add(
    "init-decl-volatile", 
    """
void act_set_return_home(void)
{
    int idx = (signed short)tracking_army;
    struct army_route_rec *route;
    int home_ref;
    int q, r;
    volatile int i;

    pointer_mode = 0;
    army_list[idx].dest_y = 0;
    army_list[idx].dest_x = 0;
    unflag_all_rm_xwarehouse();
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 0; i < 10; i++) {
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="match current full source local initializer style",
)

exp.add(
    "byte-offset-route",
    """
void act_set_return_home(void)
{
    int idx;
    int route_off;
    int home_ref;
    int q, r;
    int i;
    idx = (signed short)tracking_army;
    pointer_mode = 0;
    army_list[idx].dest_y = 0;
    army_list[idx].dest_x = 0;
    unflag_all_rm_xwarehouse();
    route_off = army_list[idx].cohort_id * 0x15a;
    for (i = 0; i < 10; i++) {
        ((unsigned char *)army_routes)[route_off + 0x10 + i] = 0;
    }
    *(int *)((unsigned char *)army_routes + route_off + 0) = 0;
    *(int *)((unsigned char *)army_routes + route_off + 4) = 0;
    *(int *)((unsigned char *)army_routes + route_off + 8) = 0;
""" + TAIL,
    note="manual route byte offset, PS-like row_len loop",
)

exp.add(
    "byte-offset-route-volatile",
    """
void act_set_return_home(void)
{
    int idx;
    int route_off;
    int home_ref;
    int q, r;
    volatile int i;
    idx = (signed short)tracking_army;
    pointer_mode = 0;
    army_list[idx].dest_y = 0;
    army_list[idx].dest_x = 0;
    unflag_all_rm_xwarehouse();
    route_off = army_list[idx].cohort_id * 0x15a;
    for (i = 0; i < 10; i++) {
        ((unsigned char *)army_routes)[route_off + 0x10 + i] = 0;
    }
    *(int *)((unsigned char *)army_routes + route_off + 0) = 0;
    *(int *)((unsigned char *)army_routes + route_off + 4) = 0;
    *(int *)((unsigned char *)army_routes + route_off + 8) = 0;
""" + TAIL,
    note="byte offsets plus volatile loop index",
)

exp.add(
    "local-bound-for",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
    int n;
""" + PROLOGUE + """
    n = 10;
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 0; i < n; i++) {
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="register local bound to avoid const memset pattern",
)

exp.add(
    "downward-for",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 9; i >= 0; i--) {
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="backwards clear loop",
)

exp.add(
    "pointer-walk",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    unsigned char *p;
    unsigned char *end;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    p = route->row_len;
    end = p + 10;
    while (p < end) {
        *p = 0;
        p++;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="pointer walk over row_len",
)

exp.add(
    "not-equal-bound",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 0; i != 10; i++) {
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="i != 10 loop bound",
)

exp.add(
    "lte-bound",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    for (i = 0; i <= 9; i++) {
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="i <= 9 loop bound",
)

exp.add(
    "countdown-predec",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    i = 10;
    while (--i >= 0) {
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="countdown with predecrement",
)

exp.add(
    "countdown-postdec",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    i = 10;
    while (i > 0) {
        i--;
        route->row_len[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="countdown with body decrement",
)

exp.add(
    "manual-byte-pointer",
    """
void act_set_return_home(void)
{
""" + BASE_DECLS + """
    int i;
    unsigned char *p;
""" + PROLOGUE + """
    route = &army_routes[army_list[idx].cohort_id];
    p = route->row_len;
    for (i = 0; i < 10; i++) {
        p[i] = 0;
    }
    route->row_count = 0;
    route->chase_row = 0;
    route->target_army = 0;
""" + TAIL,
    note="explicit byte pointer to row_len",
)
