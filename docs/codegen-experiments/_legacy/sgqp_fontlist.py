"""show_general_query_panel — font_list yrow ECX-vs-EAX+LEA (Rule 98).

Full-function cgex reproduction so the *real* whole-function conflict
graph is present (the minimal probes diverged because they lacked it).
Goal: find a source structure for the word==0x52 block (and/or dispatch)
that makes the trailing font_list arg4 (yrow) land in ECX like PS,
dropping the 30 b residue to 0.

Run:  uv run c2 cgex run sgqp_fontlist
      uv run c2 cgex run sgqp_fontlist --trial baseline
"""
from c2.commands.cgex import Experiment

exp = Experiment(
    name="sgqp_fontlist",
    ps_function="show_general_query_panel",
    externs={
        "font_format_split":
            "extern void font_format_split(int a,int w,int x,int y,int p,"
            "int q,int r,int s,unsigned char*f,int sz);",
        "font_list":
            "extern void font_list(int a,int b,int x,int y,"
            "unsigned char*f,int sz);",
        "font_no":
            "extern void font_no(int a,int b,char*s,int x,int y,"
            "unsigned char*f,int sz);",
        "show_query_house_advice":
            "extern void show_query_house_advice(void);",
        "show_query_business_advice":
            "extern void show_query_business_advice(void);",
        "_g":
            "extern char q_type; extern char q_road_access;\n"
            "extern int q_hospital_access; extern char q_supply;\n"
            "extern int query_panel_reduction; extern int x_is;\n"
            "extern unsigned char font1[];",
    },
    extra_defs="""
char q_type; char q_road_access; char q_hospital_access_pad;
int q_hospital_access; char q_supply; int query_panel_reduction; int x_is;
unsigned char font1[64];
""",
)

# Dispatch is identical across all trials; only the word==0x52 tail varies.
_PRE = """
void show_general_query_panel(void)
{
    int q;
    int word;

    q = (unsigned char)q_type;
    if (q >= 0x82 && q < 0xa2) { show_query_house_advice(); return; }
    q = (unsigned char)q_type;
    if (q == 0xfb || q == 0xf5) {
        if (!q_road_access)        word = 0x5a;
        else if (q_hospital_access) word = 0x52;
        else                        word = 0x53;
    } else if (q == 0xfa) {
        show_query_business_advice(); return;
    } else if (q == 0x7c) { word = 0x24;
    } else if (q == 0x7d) { word = 0x25;
    } else if (q == 0x7e) { word = 0x26;
    } else if (q >= 0x82) {
        if (q <= 0xa5) { word = (unsigned char)q; word -= 0x7b;
        } else if (q <= 0xa9) { word = (unsigned char)q; word -= 0x7f;
        } else if (q <= 0xad) { word = (unsigned char)q; word -= 0x83;
        } else if (q <= 0xb1) { if (!q_road_access) word = 0x5a; else { word = (unsigned char)q; word -= 0x87; }
        } else if (q <= 0xb5) { if (!q_road_access) word = 0x5a; else { word = (unsigned char)q; word -= 0x8b; }
        } else if (q <= 0xb9) { if (!q_road_access) word = 0x5a; else { word = (unsigned char)q; word -= 0x8f; }
        } else if (q >= 0xd7) {
            if (q <= 0xda) { word = (unsigned char)q; word -= 0xb0;
            } else if (q <= 0xe2) {
                if (!q_supply) { word = 0x2b; }
                else if (q <= 0xde) { word = q - 0xb4; }
                else if (q <= 0xe2) { word = q - 0xb8; }
            } else if (q < 0xe5) { if (!q_road_access) word = 0x5a; else word = 0x23;
            } else if (q >= 0xfc && q <= 0xff) { if (!q_road_access) word = 0x5a; else { word = q - 0xd0; }
            } else { word = 0x23; }
        } else { word = 0x23; }
    } else { word = 0x23; }

    font_format_split(0x3d, word, 0x38,
                      (query_panel_reduction + 9) * 0x10 + 0x20, 0x160, 0x64,
                      0, 0, font1, 0x10);
"""

FL = "(query_panel_reduction + 0xa) * 0x10 + 0x20"

def trial(name, block, note=""):
    exp.add(name, _PRE + block + "\n}\n", note=note)

# baseline = current real source (expect ~30 b residue: font_list yrow EAX+LEA)
trial("baseline", f"""
    if (word == 0x52) {{
        x_is = 0;
        if (q_type == 0xfb)  font_no(0x3e8, 0x20, "(", 0x38, {FL}, font1, 0x10);
        else                 font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10);
        font_list(0x3d, 0x5b, x_is + 0x38, {FL}, font1, 0x10);
    }}
""", note="current real source — font_list yrow EAX+LEA")

# ---- variant battery ----
def blk(mid):
    return "    if (word == 0x52) {\n        x_is = 0;\n" + mid + "    }\n"

# t1: font_list yrow split — compute the *0x10 part, then +0x20 separately
trial("t1_split_add", blk(f"""        if (q_type == 0xfb)  font_no(0x3e8, 0x20, "(", 0x38, {FL}, font1, 0x10);
        else                 font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10);
        {{ int b = (query_panel_reduction + 0xa) * 0x10; font_list(0x3d, 0x5b, x_is + 0x38, b + 0x20, font1, 0x10); }}
"""), note="font_list yrow as b=...*0x10; b+0x20")

# t2: precompute arg3 into temp before yrow
trial("t2_arg3_first", blk(f"""        if (q_type == 0xfb)  font_no(0x3e8, 0x20, "(", 0x38, {FL}, font1, 0x10);
        else                 font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10);
        {{ int x3 = x_is + 0x38; font_list(0x3d, 0x5b, x3, {FL}, font1, 0x10); }}
"""), note="arg3 temp computed first")

# t3: font_no yrow via named local (not shared inline) per branch
trial("t3_fno_local", blk(f"""        if (q_type == 0xfb)  {{ int y=(query_panel_reduction+0xa)*0x10+0x20; font_no(0x3e8,0x20,"(",0x38,y,font1,0x10); }}
        else                 {{ int y=(query_panel_reduction+0xa)*0x10+0x20; font_no(0x4b0,0x20,"(",0x38,y,font1,0x10); }}
        font_list(0x3d, 0x5b, x_is + 0x38, {FL}, font1, 0x10);
"""), note="font_no yrow per-branch local")

# t4: q_type tested via local int
trial("t4_qt_local", blk(f"""        {{ int qt = q_type;
        if (qt == 0xfb)  font_no(0x3e8, 0x20, "(", 0x38, {FL}, font1, 0x10);
        else             font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10); }}
        font_list(0x3d, 0x5b, x_is + 0x38, {FL}, font1, 0x10);
"""), note="q_type cached in local int")

# t5: font_list args reversed eval — multiply form as (qpr+0xa)<<4
trial("t5_shift", blk(f"""        if (q_type == 0xfb)  font_no(0x3e8, 0x20, "(", 0x38, {FL}, font1, 0x10);
        else                 font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10);
        font_list(0x3d, 0x5b, x_is + 0x38, ((query_panel_reduction + 0xa) << 4) + 0x20, font1, 0x10);
"""), note="font_list yrow shift form")

# t6: x_is read into temp first (arg3), then yrow last
trial("t6_x_is_temp", blk(f"""        if (q_type == 0xfb)  font_no(0x3e8, 0x20, "(", 0x38, {FL}, font1, 0x10);
        else                 font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10);
        {{ int xi = x_is; font_list(0x3d, 0x5b, xi + 0x38, {FL}, font1, 0x10); }}
"""), note="x_is cached; arg3=xi+0x38")

# t8: DIAGNOSTIC arg3 constant (breaks semantics) - does x_is read pin the alloc?
trial("t8_arg3_const", blk(f"""        if (q_type == 0xfb)  font_no(0x3e8, 0x20, "(", 0x38, {FL}, font1, 0x10);
        else                 font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10);
        font_list(0x3d, 0x5b, 0x38, {FL}, font1, 0x10);
"""), note="DIAG arg3 const 0x38 (no x_is read)")

# t9: DIAGNOSTIC no font_no at all - confirm font_list alone picks ecx
trial("t9_no_fno", blk(f"""        font_list(0x3d, 0x5b, x_is + 0x38, {FL}, font1, 0x10);
"""), note="DIAG no font_no")

# t10: DIAGNOSTIC single font_no (no if/else)
trial("t10_one_fno", blk(f"""        font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10);
        font_list(0x3d, 0x5b, x_is + 0x38, {FL}, font1, 0x10);
"""), note="DIAG single font_no")

# t11: font_list yrow used twice (force non-arg-bound temp)
trial("t11_yrow_twice", blk(f"""        if (q_type == 0xfb)  font_no(0x3e8, 0x20, "(", 0x38, {FL}, font1, 0x10);
        else                 font_no(0x4b0, 0x20, "(", 0x38, {FL}, font1, 0x10);
        {{ int y = {FL}; x_is = y; font_list(0x3d, 0x5b, x_is + 0x38, y, font1, 0x10); }}
"""), note="DIAG yrow used twice (x_is=y)")
