# city_test_for_road: flip the x<->y param seat tie with
# instruction-NEUTRAL source forms (Rule 94: `a && b` == nested if,
# byte-equal) that change the IL walk / conflict bookkeeping.  The Win
# /Od witness shows &&-chains for ALL guards and scan tests -- these
# are ALSO the more witness-faithful forms.
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")


def cand(name, old, new):
    a = src.index(old, fn_start)
    forge.candidate(name, TextEdit(start=a, end=a + len(old), replacement=new))


# --- the four guards as && (win witness form) ---
cand("N_and",
     "if (y > 0) {\n        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 1600)))).terrain & 0x20) {",
     "if (y > 0 && ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 1600)))).terrain & 0x20)) {\n        {")
cand("E_and",
     "if (x < 0x4f) {\n        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 20)))).terrain & 0x20) {",
     "if (x < 0x4f && ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 20)))).terrain & 0x20)) {\n        {")
cand("S_and",
     "if (y < 0x4f) {\n        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 1600)))).terrain & 0x20) {",
     "if (y < 0x4f && ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 1600)))).terrain & 0x20)) {\n        {")
cand("W_and",
     "if (x > 0) {\n        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 20)))).terrain & 0x20) {",
     "if (x > 0 && ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 20)))).terrain & 0x20)) {\n        {")

# --- counting loop: structured win form (n_present++ then &&-pair) ---
cand("count_struct",
     "        if (slots[i][0] == 0) continue;\n"
     "        n_present++; if (slots[i][1] != 0) continue; if (slots[i][2] != 0) continue; n_empty++;",
     "        if (slots[i][0] != 0) {\n"
     "            n_present++;\n"
     "            if (slots[i][1] == 0 && slots[i][2] == 0) n_empty++;\n"
     "        }")

# --- empty-scan: one &&-chain (win form) ---
cand("scan_and",
     "                if (slots[rand_dir][0] != 0) {\n"
     "                    if (slots[rand_dir][1] == 0 && slots[rand_dir][2] == 0) {\n"
     "                        if (rand_dir != forbidden) return rand_dir;\n"
     "                    }\n"
     "                }",
     "                if (slots[rand_dir][0] != 0 && slots[rand_dir][1] == 0\n"
     "                 && slots[rand_dir][2] == 0 && rand_dir != forbidden)\n"
     "                    return rand_dir;")

# --- fallback scan: &&-chain ---
cand("fall_and",
     "            if (slots[rand_dir][0] != 0) {\n"
     "                if (rand_dir != forbidden) return rand_dir;\n"
     "            }",
     "            if (slots[rand_dir][0] != 0 && rand_dir != forbidden) return rand_dir;")

# --- commutes: forbidden != rand_dir (win operand order) ---
a1 = src.index("if (rand_dir != forbidden) return rand_dir;\n                    }", fn_start)
forge.candidate("scan_commute", TextEdit(start=a1, end=a1 + len("if (rand_dir != forbidden)"),
                                         replacement="if (forbidden != rand_dir)"))
a2 = src.index("if (rand_dir != forbidden) return rand_dir;\n            }", fn_start)
forge.candidate("fall_commute", TextEdit(start=a2, end=a2 + len("if (rand_dir != forbidden)"),
                                         replacement="if (forbidden != rand_dir)"))
