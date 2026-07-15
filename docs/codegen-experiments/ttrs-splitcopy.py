# try_this_regionmap_square: final 6b = stmt2 (target_y copy) index-temp
# pair seats EAX/EDX swapped vs PS.  Offline ShellSort sim: swapping the
# pair's CONFLICT CREATION order flips it cleanly.  Creation order = FE
# processing order (LHS addr first in a plain assignment).  A split
# `t = .y; target_y = t;` form processes the RHS load FIRST -- and a
# memory LOAD (unlike a temp copy) cannot be move-propagated away.
from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")

I = "                    "
PAIR = (I + "army_list[army_no].target_x = army_list[army_no].x;\n"
        + I + "army_list[army_no].target_y = army_list[army_no].y;")
a = src.index(PAIR, fn_start)


def cand(name, repl):
    forge.candidate(name, TextEdit(start=a, end=a + len(PAIR), replacement=repl))


# split only stmt2 (temp declared inline? no - C89: reuse decl block).
# use a new uchar local `ty` -- decl edit is separate; try with existing
# locals first: `terrain` is dead by now (uchar!) -- reuse it!
cand("split_y_via_terrain",
     I + "army_list[army_no].target_x = army_list[army_no].x;\n"
     + I + "terrain = army_list[army_no].y;\n"
     + I + "army_list[army_no].target_y = terrain;")
# split BOTH statements via terrain
cand("split_xy_via_terrain",
     I + "terrain = army_list[army_no].x;\n"
     + I + "army_list[army_no].target_x = terrain;\n"
     + I + "terrain = army_list[army_no].y;\n"
     + I + "army_list[army_no].target_y = terrain;")
# split only stmt1
cand("split_x_via_terrain",
     I + "terrain = army_list[army_no].x;\n"
     + I + "army_list[army_no].target_x = terrain;\n"
     + I + "army_list[army_no].target_y = army_list[army_no].y;")
# one-line packing of the split (same source line -> single -d1 mark)
cand("split_y_oneline",
     I + "army_list[army_no].target_x = army_list[army_no].x;\n"
     + I + "terrain = army_list[army_no].y; army_list[army_no].target_y = terrain;")
