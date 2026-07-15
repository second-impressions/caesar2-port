"""Codegen experiment for message.c::message.

Target residue (249 b): the three loop-tail `out1 = 1; message_goto_ptr = 0;`
blocks each materialise the constant 0 into whatever register is free, and PS
gets EAX for one of them (the 5-byte `a3` accumulator store) while our build
holds EAX with a high-savings short-lived loop temp and falls back to the 6-byte
`89 /r` store.  The +1 byte cascades into a +2 jump-target shift -> all 249.

This experiment brute-forces faithful reorderings (decl order, loop-tail block
order, statement order) to find the one that frees EAX for the 0-store and lands
byte-exact.  `c2 cgex run message` lists every trial's masked diff vs PS.
"""

from c2.commands.cgex import Experiment

STRUCTS = r"""
struct button_rec {
    short x; short y; short sprite; short size;
    void (*callback)(void);
    unsigned char state;
};
struct request_message { int active; int _pad[20]; };
"""

PRELUDE = STRUCTS + r"""
extern char decision, gen_refresh1, hold_hot_keys, map_mode, mouse_right_click;
extern char pointer_mode, zoom_level;
extern char city_palette[], region_palette[], temp_palette[];
extern int final_bribe, game_state, imperial_send_amount, local_time, time_is;
extern int message_goto_ptr, out1, stolen_denarii, turbo_mode, tutorial_mode;
extern int warned_of_not_build;
extern unsigned char msg_is_danger[];
extern struct request_message request_message;
extern struct button_rec goto_mess_buttons[], request_buttons[];
extern void clear_map_gfx_buffers(void), clear_battle_gfx_buffers(void);
extern void clear_keys(void), stop_db(void), gloop_start(void), gloop_end(void);
extern void show_request_amount(void), request_outcome(void), stop_smacking(void);
extern void refresh_svga_screen(void), init_map_gfx_buffers(void);
extern void init_battle_gfx_buffers(void), region_map_screen(int);
extern void battle_screen(int), city_map_screen(int);
extern void show_basic_message(int msg, int param);
extern void show_emperor_message(int msg, int is_emperor);
extern void draw_a_rect(int x, int y, int w, int h, int colour);
extern void set_palette(char *p);
extern void setup_refresh_area(int x, int y, int w, int h, int value);
extern void show_buttons(int x, int y, struct button_rec *buttons, int count);
extern void control_buttons(int x, int y, struct button_rec *buttons, int count);
extern int continue_smacking(int p1, int x, int mode);
extern int exit_screen(void);
extern int load_map_graphics(int mode, int level);
extern int jump_to_regionmap_ptr(int target_ptr);
extern int jump_to_citymap_ptr(int target_ptr);
extern int danger_flag_map_mode;
extern int put_danger_flag(int val);
extern void act_init_turbo_mode(void), flush_sb_buffer(void);
extern void setup_map_screen_long_refresh(int fill);
"""

EXTRA_DEFS = STRUCTS + r"""
char decision, gen_refresh1, hold_hot_keys, map_mode, mouse_right_click;
char pointer_mode, zoom_level;
char city_palette[256], region_palette[256], temp_palette[256];
int final_bribe, game_state, imperial_send_amount, local_time, time_is;
int message_goto_ptr, out1, stolen_denarii, turbo_mode, tutorial_mode;
int warned_of_not_build;
unsigned char msg_is_danger[256];
struct request_message request_message;
struct button_rec goto_mess_buttons[4], request_buttons[4];

void clear_map_gfx_buffers(void){} void clear_battle_gfx_buffers(void){}
void clear_keys(void){} void stop_db(void){} void gloop_start(void){}
void gloop_end(void){} void show_request_amount(void){} void request_outcome(void){}
void stop_smacking(void){} void refresh_svga_screen(void){}
void init_map_gfx_buffers(void){} void init_battle_gfx_buffers(void){}
void region_map_screen(int a){(void)a;} void battle_screen(int a){(void)a;}
void city_map_screen(int a){(void)a;}
void show_basic_message(int a,int b){(void)a;(void)b;}
void show_emperor_message(int a,int b){(void)a;(void)b;}
void draw_a_rect(int a,int b,int c,int d,int e){(void)a;(void)b;(void)c;(void)d;(void)e;}
void set_palette(char *p){(void)p;}
void setup_refresh_area(int a,int b,int c,int d,int e){(void)a;(void)b;(void)c;(void)d;(void)e;}
void show_buttons(int a,int b,struct button_rec *c,int d){(void)a;(void)b;(void)c;(void)d;}
void control_buttons(int a,int b,struct button_rec *c,int d){(void)a;(void)b;(void)c;(void)d;}
int continue_smacking(int a,int b,int c){(void)a;(void)b;(void)c;return 0;}
int exit_screen(void){return 0;}
int load_map_graphics(int a,int b){(void)a;(void)b;return 0;}
int jump_to_regionmap_ptr(int a){(void)a;return 0;}
int jump_to_citymap_ptr(int a){(void)a;return 0;}
int danger_flag_map_mode;
int put_danger_flag(int a){(void)a;return 0;}
void act_init_turbo_mode(void){} void flush_sb_buffer(void){}
void setup_map_screen_long_refresh(int a){(void)a;}
"""

exp = Experiment(
    name="message",
    ps_function="message",
    chk=False,   # PS's message has no __CHK probe (4-byte frame)
    prelude=PRELUDE,
    extra_defs=EXTRA_DEFS,
)


# ── body templates ───────────────────────────────────────────────────────────
# The loop-tail blocks are parameterised so trials can permute them.

def _block(cond, swap=False):
    body = ("message_goto_ptr = 0;\n            out1 = 1;"
            if swap else
            "out1 = 1;\n            message_goto_ptr = 0;")
    return f"if ({cond}) {{\n            {body}\n            }}"


def body(decls="int ret;\n    int old_pointer_mode;",
         tail_order=("mouse", "exit", "time"), swap_store=False,
         time_cond="local_time + 12 < time_is",
         dowhile=False, prologue=None):
    conds = {"mouse": "mouse_right_click != 0",
             "exit": "exit_screen() != 0",
             "time": time_cond}
    # swap_store: bool (all blocks) or a set of block keys to swap
    def _sw(k):
        return swap_store is True or (
            not isinstance(swap_store, bool) and k in swap_store)
    tail = "\n            ".join(
        _block(conds[k], _sw(k)) for k in tail_order)
    _PROL = prologue or """hold_hot_keys        = 1;
        old_pointer_mode     = pointer_mode;
        pointer_mode         = 0;
        turbo_mode           = 0;
        local_time           = time_is;
        message_goto_ptr     = param;
        request_message.active = 0;
        imperial_send_amount = 0;"""
    _loop_open = "do {" if dowhile else "while (out1 != 1) {"
    _loop_close = "} while (out1 != 1);" if dowhile else "}"
    return f"""
void message(int msg, int is_emperor, int param) {{
    {decls}
    decision = 0;
    if (tutorial_mode == 0 &&
        ((msg != 0x56 && msg != 0x59) || stolen_denarii > 0)) {{
        clear_map_gfx_buffers();
        clear_battle_gfx_buffers();
        clear_keys();
        warned_of_not_build  = 0;
        stop_db();
        {_PROL}
        if (is_emperor == 0)
            show_basic_message(msg, param);
        else
            show_emperor_message(msg, is_emperor);
        out1 = 0;
        {_loop_open}
            hold_hot_keys = 1;
            gloop_start();
            continue_smacking(0x60, 0x50, 1);
            if (request_message.active != 0) {{
                if (gen_refresh1 != 0) {{
                    gen_refresh1 = 0;
                    show_request_amount();
                }}
                show_buttons(0x110, 0x18e, request_buttons, 2);
            }}
            if (param != 0)
                show_buttons(0x130, 0x170, goto_mess_buttons, 1);
            gloop_end();
            if (request_message.active != 0)
                control_buttons(0x110, 0x18e, request_buttons, 2);
            if (param != 0)
                control_buttons(0x130, 0x170, goto_mess_buttons, 1);
            {tail}
        {_loop_close}
        if (request_message.active != 0) {{
            request_outcome();
        }} else {{
            if (msg >= 0x7d && msg <= 0x84 && final_bribe == 2)
                game_state = out1;
        }}
        stop_smacking();
        draw_a_rect(0x60, 0x50, 0x140, 0x98, 16);
        setup_refresh_area(0x60, 0x50, 20, 10, 1);
        refresh_svga_screen();
        pointer_mode = old_pointer_mode;
        init_map_gfx_buffers();
        init_battle_gfx_buffers();
        load_map_graphics(map_mode, zoom_level);
        ret = 0;
        if (message_goto_ptr != 0) {{
            turbo_mode = 0;
            if (msg_is_danger[msg] == 1)
                ret = jump_to_regionmap_ptr(message_goto_ptr);
            else
                ret = jump_to_citymap_ptr(message_goto_ptr);
        }}
        if (map_mode == 0)
            set_palette(city_palette);
        else if (map_mode == 1)
            set_palette(region_palette);
        else
            set_palette(temp_palette);
        if (ret != 1) {{
            if (map_mode == 0)
                city_map_screen(0);
            else if (map_mode == 1)
                region_map_screen(0);
            else
                battle_screen(0);
        }}
        if (param != 0) {{
            danger_flag_map_mode = (msg_is_danger[msg] == 1);
            put_danger_flag(param);
        }}
        if (turbo_mode != 0)
            act_init_turbo_mode();
        setup_map_screen_long_refresh(4);
        gen_refresh1 = 1;
        flush_sb_buffer();
    }}
}}
"""


exp.add("baseline", body(), note="exact message.c body")
exp.add("decl-swap", body(decls="int old_pointer_mode;\n    int ret;"),
        note="ret/old_pointer_mode decl order swapped (Rule 115)")
exp.add("store-swap", body(swap_store=True),
        note="mgp=0 before out1=1 in all 3 blocks")

# loop-tail block-order permutations (all 3 conds checked every iter)
import itertools as _it
for perm in _it.permutations(("mouse", "exit", "time")):
    if perm == ("mouse", "exit", "time"):
        continue
    exp.add("tail-" + "".join(p[0] for p in perm), body(tail_order=perm),
            note="loop-tail block order " + ">".join(perm))


# store-swap x tail-order combos (the 2 growth points may need different blocks
# in EAX); plus per-block store swaps to isolate which block PS holds in EAX.
for perm in _it.permutations(("mouse", "exit", "time")):
    tag = "".join(p[0] for p in perm)
    exp.add(f"sw-tail-{tag}", body(tail_order=perm, swap_store=True),
            note="store-swap + tail " + ">".join(perm))
for sub in (("mouse",), ("exit",), ("time",),
            ("mouse", "exit"), ("mouse", "time"), ("exit", "time")):
    exp.add("sw-" + "".join(s[0] for s in sub),
            body(swap_store=set(sub)),
            note="store-swap only in " + ",".join(sub))
exp.add("sw-decl", body(decls="int old_pointer_mode;\n    int ret;",
                        swap_store=True),
        note="store-swap + decl-swap")

# Rule 28a: commute / re-shape the line-171 condition so the loop-weighted
# `local_time + 12` temp (sav=20, the EAX hog) lands in a different register
# and frees EAX for the loop-tail 0-stores.  Try each form alone and x sw-e.
_TIME_FORMS = {
    "gt":      "time_is > local_time + 12",
    "submin":  "local_time < time_is - 12",
    "diffgt":  "time_is - local_time > 12",
    "diffge":  "time_is - local_time >= 13",
    "le":      "local_time + 12 <= time_is - 1",
    "revsub":  "local_time - time_is < -12",
}
for tag, cond in _TIME_FORMS.items():
    exp.add(f"cond-{tag}", body(time_cond=cond),
            note=f"time cond: {cond}")
    exp.add(f"cond-{tag}-swe", body(time_cond=cond, swap_store={"exit"}),
            note=f"time cond: {cond} + sw-exit")


exp.add("dowhile", body(dowhile=True), note="do/while loop form")
# prologue 0-store reorder (independent global scalar stores -> faithful);
# perturbs which register the optimiser parks 0 in.
exp.add("prol-reorder", body(prologue="""old_pointer_mode     = pointer_mode;
        message_goto_ptr     = param;
        local_time           = time_is;
        hold_hot_keys        = 1;
        pointer_mode         = 0;
        turbo_mode           = 0;
        imperial_send_amount = 0;
        request_message.active = 0;"""),
        note="prologue 0-store order shuffled")
exp.add("prol-zeros-last", body(prologue="""hold_hot_keys        = 1;
        old_pointer_mode     = pointer_mode;
        local_time           = time_is;
        message_goto_ptr     = param;
        pointer_mode         = 0;
        turbo_mode           = 0;
        request_message.active = 0;
        imperial_send_amount = 0;"""),
        note="all 0-stores grouped at end of prologue")


if __name__ == "__main__":
    exp.run()
    exp.print_table()
