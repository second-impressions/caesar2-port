# one_aquaduct_ramification: PS materializes the else-arm `return 0`
# INLINE at the c1/c2 compare (mid_func_epilogue, Rule 92 5b) and the
# shared gmn_err block back-jumps into it; our RC absorbs the ret0
# forward after the gmn_err stores.  Enumerate label/goto/arm-form
# combinations to find the source shape that steers the 10.0a
# ret-tail-merge direction.
from c2.forge import Forge, TextEdit

forge = Forge("one_aquaduct_ramification", file="map.c")

src = forge.index.text  # current on-disk source text
GM = '(*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr)))'


def off(needle, start=0):
    i = src.index(needle, start)
    return i, i + len(needle)


fn_start = src.index("int one_aquaduct_ramification(void)")

# --- site 1: the middle-arm `return 0;` on the else-if line
s1_needle = f"else if ({GM}.base_kind != 0xc2) return 0;"
s1_a, s1_b = off(s1_needle, fn_start)

# --- site 4: aquawall-else gmn_err block (return 0 at its end)
s4_needle = ("gmn_err_sptr = gmn_sptr;\n"
             "                gmn_err_x = gmn_x;\n"
             "                gmn_err_y = gmn_y;\n"
             "                return 0;")
s4_a, s4_b = off(s4_needle, fn_start)
s4_ret_a = s4_a + s4_needle.index("return 0;")
s4_ret_b = s4_ret_a + len("return 0;")

# --- site 5: sel == 0 gmn_err block
s5_needle = ("gmn_err_sptr = gmn_sptr;\n"
             "            gmn_err_x = gmn_x;\n"
             "            gmn_err_y = gmn_y;\n"
             "            return 0;")
s5_a, s5_b = off(s5_needle, fn_start)
s5_ret_a = s5_a + s5_needle.index("return 0;")
s5_ret_b = s5_ret_a + len("return 0;")

# --- site 7: resevoir gmn_err block
s7_needle = ("gmn_err_sptr = gmn_sptr;\n"
             "        gmn_err_x = gmn_x;\n"
             "        gmn_err_y = gmn_y;\n"
             "        return 0;")
s7_a, s7_b = off(s7_needle, fn_start)
s7_ret_a = s7_a + s7_needle.index("return 0;")
s7_ret_b = s7_ret_a + len("return 0;")

# ---- candidates ----
# label the middle-arm return
forge.candidate("lbl_fail_mid", TextEdit(
    start=s1_a, end=s1_b,
    replacement=f"else if ({GM}.base_kind != 0xc2) {{ fail: return 0; }}"))

# arm form: back to last-arm else return 0 (labeled)
forge.candidate("lbl_fail_last", TextEdit(
    start=s1_a,
    end=off(f"else first_choice = 0xbc;", s1_b)[1],
    replacement=(f"else if ({GM}.base_kind == 0xc2) first_choice = 0xbc;\n"
                 "                else { fail: return 0; }")))

# gotos to fail (each site)
forge.candidate("s4_goto_fail", TextEdit(start=s4_ret_a, end=s4_ret_b,
                                         replacement="goto fail;"))
forge.candidate("s5_goto_fail", TextEdit(start=s5_ret_a, end=s5_ret_b,
                                         replacement="goto fail;"))
forge.candidate("s7_goto_fail", TextEdit(start=s7_ret_a, end=s7_ret_b,
                                         replacement="goto fail;"))

# err: label at site 4 stores; sites 5/7 collapse to goto err
forge.candidate("lbl_err_s4", TextEdit(
    start=s4_a, end=s4_a,
    replacement="err:\n                "))
forge.candidate("s5_goto_err", TextEdit(
    start=s5_a, end=s5_b, replacement="goto err;"))
forge.candidate("s7_goto_err", TextEdit(
    start=s7_a, end=s7_b, replacement="goto err;"))
