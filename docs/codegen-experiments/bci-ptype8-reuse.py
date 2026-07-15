"""build_city_item — the placing_type==8 arm's EBX const-reuse.

PS (L976/L984): `mov ebx,[placing_type]; cmp ebx,8` then at the call
`mov ecx,ebx` — the guard LOADS the global and the known-==8 register
is reused as the 4th put_x1_area arg.  RC: `cmp [placing_type],8` +
`mov ecx,8`.  Win port shows the literal 8 (no local), so the reuse
may be compiler known-value tracking — but Watcom only reuses if the
guard loads to a register, which a bare global==K guard does not do.
Sweep: which local mediates the load (embedded-assign vs separate
statement), whether the arg is the local or the literal, and && vs
nested-if for the inner guard.  Base: 180bd isl3 (post decl-swap
gfx_b<->cover_gfx state, dx-first md==4 arm).
"""
from c2.forge import Forge, TextEdit

forge = Forge("build_city_item", file="action.c")
src = forge.text

ARM = """    if (placing_type == 8) {
        restore_city_from_undo_buffer();
        if (hot_key_out_off_build == 0
         && put_x1_area(over_x, over_y, 0xd7, 8, 0x10) == 0) {
            restore_city_from_undo_buffer();
        }
    }"""
a = src.index(ARM)
b = a + len(ARM)

LOCALS = ["warned", "ok", "shape", "tgfx_a", "tgfx_b", "dx", "dy",
          "gfx_a", "gfx_b", "gfx_a_idx", "gfx_b_idx", "cover_gfx",
          "fountain_gfx", "i"]

def arm(guard, arg, inner="and"):
    if inner == "and":
        body = (f"        if (hot_key_out_off_build == 0\n"
                f"         && put_x1_area(over_x, over_y, 0xd7, {arg}, 0x10) == 0) {{\n"
                f"            restore_city_from_undo_buffer();\n"
                f"        }}")
    else:
        body = (f"        if (hot_key_out_off_build == 0) {{\n"
                f"            if (put_x1_area(over_x, over_y, 0xd7, {arg}, 0x10) == 0) {{\n"
                f"                restore_city_from_undo_buffer();\n"
                f"            }}\n"
                f"        }}")
    return (f"    {guard} {{\n"
            f"        restore_city_from_undo_buffer();\n"
            f"{body}\n"
            f"    }}")

for v in LOCALS:
    for arg in (v, "8"):
        for inner in ("and", "nest"):
            forge.candidate(
                f"emb_{v}_arg{arg}_{inner}",
                TextEdit(start=a, end=b,
                         replacement=arm(f"if (({v} = placing_type) == 8)", arg, inner)))
            forge.candidate(
                f"sep_{v}_arg{arg}_{inner}",
                TextEdit(start=a, end=b,
                         replacement=arm(f"{v} = placing_type;\n    if ({v} == 8)", arg, inner)))

# control: literal guard + nested inner
forge.candidate("lit_nest", TextEdit(start=a, end=b,
                                     replacement=arm("if (placing_type == 8)", "8", "nest")))
