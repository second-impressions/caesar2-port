"""build_city_item -- the two remaining seat regions, statement-split shapes.

line-shape cues (PS-only statement starts at +0153/+016d/+01ab) say the
==1 arm's terrain tests and base_kind load began NEW statements in PS,
and stmt-IR says our ==10 arm's cover_gfx ternary folds ASSIGN+CALL+
COMPARE that PS had as separate statements (L802 call / L803 test /
L804 else).  Sweep: ==1 arm {guard nesting} x {named base_kind local},
==10 arm {split if/else} x {named return local}; depth 2 combines one
of each.  Base: 62bd ir0/isl0 seat2.
"""
from c2.forge import Forge, TextEdit

forge = Forge("build_city_item", file="action.c")
src = forge.text

CELL = '(*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr)))'

ARM1 = '        if (act_start_x == over_x\n         && act_start_y == over_y\n         && ((*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).terrain & 0x20) != 0\n         && ((*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).terrain & 0x40) != 0) {\n            confirm(10, 0xa0, 0xa0);\n            if (decision == 0) {\n                (*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).terrain &= 0xdf;\n                if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).base_kind == 0xd5) {\n                    (*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).base_kind = 0xcf;\n                    (*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).extra_edge = 0x79;\n                } else {\n                    (*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).base_kind = 0xd0;\n                    (*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).extra_edge = 0x76;\n                }\n                aquaduct_ramifications(over_x, over_y);\n                setup_map_screen_refresh();\n                goto after_clear;\n            }\n        }'
a1 = src.index(ARM1)
b1 = a1 + len(ARM1)

BODY_CUR = """                if ((unsigned char)CELL.base_kind == 0xd5) {""".replace("CELL", CELL)

def arm1_variant(nested, body_var):
    if body_var is None:
        body_if = f"                if ((unsigned char){CELL}.base_kind == 0xd5) {{"
    else:
        body_if = (f"                {body_var} = {CELL}.base_kind;\n"
                   f"                if ({body_var} == 0xd5) {{")
    body = (f"                {CELL}.terrain &= 0xdf;\n"
            f"{body_if}\n"
            f"                    {CELL}.base_kind = 0xcf;\n"
            f"                    {CELL}.extra_edge = 0x79;\n"
            f"                }} else {{\n"
            f"                    {CELL}.base_kind = 0xd0;\n"
            f"                    {CELL}.extra_edge = 0x76;\n"
            f"                }}\n"
            f"                aquaduct_ramifications(over_x, over_y);\n"
            f"                setup_map_screen_refresh();\n"
            f"                goto after_clear;")
    inner = (f"            confirm(10, 0xa0, 0xa0);\n"
             f"            if (decision == 0) {{\n"
             f"{body}\n"
             f"            }}")
    if not nested:
        return (f"        if (act_start_x == over_x\n"
                f"         && act_start_y == over_y\n"
                f"         && ({CELL}.terrain & 0x20) != 0\n"
                f"         && ({CELL}.terrain & 0x40) != 0) {{\n"
                f"{inner}\n"
                f"        }}")
    return (f"        if (act_start_x == over_x\n"
            f"         && act_start_y == over_y) {{\n"
            f"            if (({CELL}.terrain & 0x20) != 0) {{\n"
            f"            if (({CELL}.terrain & 0x40) != 0) {{\n"
            f"{inner}\n"
            f"            }}\n"
            f"            }}\n"
            f"        }}")

assert arm1_variant(False, None) == ARM1
for nested in (False, True):
    for v in (None, "warned", "ok", "shape", "i", "tgfx_a", "tgfx_b"):
        if not nested and v is None:
            continue
        forge.candidate(f"arm1_{'nest' if nested else 'and'}_{v or 'anon'}",
                        TextEdit(start=a1, end=b1,
                                 replacement=arm1_variant(nested, v)))

ARM10 = '        cover_gfx = (affected_by_cover1(\n                   (*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).b,\n                   2, 4) != 0)\n              ? 0x20 : 99;'
a2 = src.index(ARM10)
b2 = a2 + len(ARM10)

def arm10_split(ret_var):
    call = (f"affected_by_cover1(\n"
            f"                   {CELL}.b,\n"
            f"                   2, 4)")
    if ret_var is None:
        return (f"        if ({call} != 0) {{\n"
                f"            cover_gfx = 0x20;\n"
                f"        }} else {{\n"
                f"            cover_gfx = 99;\n"
                f"        }}")
    return (f"        {ret_var} = {call};\n"
            f"        if ({ret_var} != 0) {{\n"
            f"            cover_gfx = 0x20;\n"
            f"        }} else {{\n"
            f"            cover_gfx = 99;\n"
            f"        }}")

for v in (None, "warned", "ok", "shape", "i", "tgfx_a", "tgfx_b"):
    forge.candidate(f"arm10_split_{v or 'anon'}",
                    TextEdit(start=a2, end=b2, replacement=arm10_split(v)))
