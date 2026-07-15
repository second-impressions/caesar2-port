# try_this_regionmap_square: PS tags ALL four mask computations L1821
# (the type-load line) -- multi-statement line packing.  Line boundaries
# gate cachecon/temp flushes -> rover state at the L1847 pair.  Probe
# packing combos of the head statements.
from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")

TYPE_LINE = "    type        = army_list[army_no].type;"
ASGS = ("    terr_bit_2  = terrain & 2;\n"
        "    terr_bit_20 = terrain & 0x20;\n"
        "    terr_bit_4  = terrain & 4;\n"
        "    terr_bit_1  = terrain & 1;")
blk = TYPE_LINE + "\n\n" + ASGS
a = src.index(blk, fn_start)
b = a + len(blk)

forge.candidate("pack_all_one_line", TextEdit(start=a, end=b, replacement=(
    "    type = army_list[army_no].type; terr_bit_2 = terrain & 2; terr_bit_20 = terrain & 0x20; terr_bit_4 = terrain & 4; terr_bit_1 = terrain & 1;")))

forge.candidate("pack_masks_one_line", TextEdit(start=a, end=b, replacement=(
    TYPE_LINE + "\n\n"
    "    terr_bit_2 = terrain & 2; terr_bit_20 = terrain & 0x20; terr_bit_4 = terrain & 4; terr_bit_1 = terrain & 1;")))

forge.candidate("pack_masks_on_type_line", TextEdit(start=a, end=b, replacement=(
    "    type = army_list[army_no].type; terr_bit_2 = terrain & 2; terr_bit_20 = terrain & 0x20;\n"
    "    terr_bit_4 = terrain & 4; terr_bit_1 = terrain & 1;")))

forge.candidate("pack_pairs", TextEdit(start=a, end=b, replacement=(
    TYPE_LINE + "\n\n"
    "    terr_bit_2 = terrain & 2; terr_bit_20 = terrain & 0x20;\n"
    "    terr_bit_4 = terrain & 4; terr_bit_1 = terrain & 1;")))

# also probe packing at the ACCEPT-path pair itself + its neighbors
I = "                    "
tail = (I + "game_state    = 4;\n"
        + I + "army_list[army_no].target_x = army_list[army_no].x;\n"
        + I + "army_list[army_no].target_y = army_list[army_no].y;")
ta = src.index(tail, fn_start)
tb = ta + len(tail)
forge.candidate("accept_pack_gs_x", TextEdit(start=ta, end=tb, replacement=(
    I + "game_state = 4; army_list[army_no].target_x = army_list[army_no].x;\n"
    + I + "army_list[army_no].target_y = army_list[army_no].y;")))
forge.candidate("accept_pack_xy", TextEdit(start=ta, end=tb, replacement=(
    I + "game_state    = 4;\n"
    + I + "army_list[army_no].target_x = army_list[army_no].x; army_list[army_no].target_y = army_list[army_no].y;")))
forge.candidate("accept_pack_all", TextEdit(start=ta, end=tb, replacement=(
    I + "game_state = 4; army_list[army_no].target_x = army_list[army_no].x; army_list[army_no].target_y = army_list[army_no].y;")))
