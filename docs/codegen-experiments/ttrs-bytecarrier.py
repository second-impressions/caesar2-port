# try_this_regionmap_square: last 6b -- accept-path target_y pair index
# temps EAX/EDX swapped; CRM-driven (score EDX=2) by the byte-carrier /
# an upstream EDX holder.  Broad shotgun over the accept path + the
# SIBLING pairs (decline path, blocked tail) whose anon temps share the
# tie group: byte-neutral form changes there can reorder the group.
from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")


def cand(name, old, new, occ=0):
    a = fn_start
    for _ in range(occ + 1):
        a = src.index(old, a + 1)
    forge.candidate(name, TextEdit(start=a, end=a + len(old), replacement=new))


I16 = "                    "
I8 = "        "

# --- accept-path neighborhood forms ---
cand("b2ptr_cast", "battle2_ptr   = target;", "battle2_ptr   = (int)target;")
cand("gv_arg_paren", "get_villagers(base_kind - 0x92);", "get_villagers((base_kind - 0x92));")
cand("gv_arg_int", "get_villagers(base_kind - 0x92);", "get_villagers((int)base_kind - 0x92);")
cand("gv_arg_add", "get_villagers(base_kind - 0x92);", "get_villagers(base_kind + -0x92);")
cand("gs_hex", "game_state    = 4;\n" + I16 + "army_list[army_no].target_x",
     "game_state    = 0x4;\n" + I16 + "army_list[army_no].target_x")

# --- accept pair packing / swap (one-line forms not yet tried here) ---
PAIR_A = (I16 + "army_list[army_no].target_x = army_list[army_no].x;\n"
          + I16 + "army_list[army_no].target_y = army_list[army_no].y;")
cand("pairA_oneline", PAIR_A,
     I16 + "army_list[army_no].target_x = army_list[army_no].x; army_list[army_no].target_y = army_list[army_no].y;")

# --- decline-path sibling pair forms (share the anon tie group) ---
PAIR_B = (I16 + "army_list[army_no].target_x = army_list[army_no].x;\n"
          + I16 + "army_list[army_no].target_y = army_list[army_no].y;")
cand("pairB_oneline", PAIR_B,
     I16 + "army_list[army_no].target_x = army_list[army_no].x; army_list[army_no].target_y = army_list[army_no].y;",
     occ=1)

# --- decline-path zero stores order/forms ---
cand("destxy_swap",
     I16 + "army_list[army_no].dest_y = 0;\n" + I16 + "army_list[army_no].dest_x = 0;",
     I16 + "army_list[army_no].dest_x = 0;\n" + I16 + "army_list[army_no].dest_y = 0;")

# --- route resets: chained-zero forms ---
cand("route_chain",
     I16 + "army_routes[army_list[army_no].cohort_id].row_count = 0;\n"
     + I16 + "army_routes[army_list[army_no].cohort_id].chase_row = 0;\n"
     + I16 + "army_routes[army_list[army_no].cohort_id].target_army = 0;",
     I16 + "army_routes[army_list[army_no].cohort_id].row_count =\n"
     + I16 + "army_routes[army_list[army_no].cohort_id].chase_row =\n"
     + I16 + "army_routes[army_list[army_no].cohort_id].target_army = 0;")

# --- confirm arg forms ---
cand("confirm_hex", "confirm(9, 0xa0, 0xa0);", "confirm(0x9, 0xa0, 0xa0);")

# --- decision test forms ---
cand("decision_ne0", "if (decision == 1) {", "if (decision != 0) {")
