# try_this_regionmap_square: last 6 bytes -- the ACCEPT-path
# target_x/target_y copy pair (L1846/1847).  PS's SECOND statement
# computes the DEST index (eax) BEFORE the SRC index (edx); RC emits
# src-first for both.  Probe statement order / packing / temp forms.
from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")

PAIR = """                    army_list[army_no].target_x = army_list[army_no].x;
                    army_list[army_no].target_y = army_list[army_no].y;"""
a = src.index(PAIR, fn_start)
b = a + len(PAIR)

I = "                    "
forge.candidate("swap_xy", TextEdit(start=a, end=b, replacement=(
    I + "army_list[army_no].target_y = army_list[army_no].y;\n"
    + I + "army_list[army_no].target_x = army_list[army_no].x;")))

forge.candidate("one_line", TextEdit(start=a, end=b, replacement=(
    I + "army_list[army_no].target_x = army_list[army_no].x; army_list[army_no].target_y = army_list[army_no].y;")))

# second stmt only packed onto first line's tail? (mark shift)
forge.candidate("y_packed", TextEdit(start=a, end=b, replacement=(
    I + "army_list[army_no].target_x = army_list[army_no].x;\n"
    + I + "army_list[army_no].target_y =\n" + I + "    army_list[army_no].y;")))
