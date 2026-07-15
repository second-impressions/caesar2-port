# city_test_for_road: flip the x<->y param seat tie by pushing y's
# LAST USE past x's (backward live scan creates conflicts at last use;
# prepend => earlier-scanned = later list position).  Probe neutral /
# folded later uses of y and last-use-shifting guard forms.  MECHANISM
# probe: even an un-PS-ish form that lands byte-exact names the lever.
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)")

W = """    if (x > 0) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 20)))).terrain & 0x20) {
            slots[6][0] = 1;
            slots[6][1] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 20)))).citizen_a;
            slots[6][2] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 20)))).citizen_b;
        }
    }
"""
a = src.index(W, fn_start)
b = a + len(W)

# 1. bare `y;` statement after the W guard (IL use, no code)
forge.candidate("y_stmt_after_W", TextEdit(start=b, end=b, replacement="    y;\n"))
# 2. (void)y cast
forge.candidate("voidy_after_W", TextEdit(start=b, end=b, replacement="    (void)y;\n"))
# 3. folded-away arithmetic use: y - y added to a constant expression? use in n_present init
NP = "    n_present = 0; n_empty = 0;"
c = src.index(NP, fn_start)
forge.candidate("np_y_minus_y", TextEdit(start=c, end=c + len(NP),
    replacement="    n_present = y - y; n_empty = 0;"))
# 4. W guard reads x via a comma with y: `if (x > 0)` -> `if ((y, x) > 0)`
XG = "    if (x > 0) {"
d = src.index(XG, fn_start)
forge.candidate("W_comma_y_x", TextEdit(start=d, end=d + len(XG), replacement="    if ((y, x) > 0) {"))
# 5. always-true folded guard with y (Rule 158 style): `if (x > 0 && y >= 0)`? changes IL...
forge.candidate("W_and_y_ge0", TextEdit(start=d, end=d + len(XG), replacement="    if (x > 0 && y >= -1000) {"))
# 6. swap x-guard polarity form `0 < x`
forge.candidate("W_0_lt_x", TextEdit(start=d, end=d + len(XG), replacement="    if (0 < x) {"))
# 7. N guard `0 < y` (win form)
NG = "    if (y > 0) {"
e = src.index(NG, fn_start)
forge.candidate("N_0_lt_y", TextEdit(start=e, end=e + len(NG), replacement="    if (0 < y) {"))
# 8. E guard win form `x < 0x4f` already; probe `0x4f > x`
EG = "    if (x < 0x4f) {"
f_ = src.index(EG, fn_start)
forge.candidate("E_4f_gt_x", TextEdit(start=f_, end=f_ + len(EG), replacement="    if (0x4f > x) {"))
# 9. S guard `0x4f > y`
SG = "    if (y < 0x4f) {"
g = src.index(SG, fn_start)
forge.candidate("S_4f_gt_y", TextEdit(start=g, end=g + len(SG), replacement="    if (0x4f > y) {"))
