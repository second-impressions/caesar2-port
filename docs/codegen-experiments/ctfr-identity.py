# city_test_for_road: identity-form probes on x's guard uses.  Goal: make
# the FE materialise an ALIAS temp for x (high temp id) so the
# RoughSortTemps id-desc walk creates x's conflict BEFORE y's (the
# AddConflictNode DeAlias path) -- flipping the EDI/EBP tie -- while the
# emitted compare stays byte-identical.
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")

EG = "if (x < 0x4f) {"
WG = "if (x > 0) {"
e = src.index(EG, fn_start)
w = src.index(WG, fn_start)

E_FORMS = ["if ((int)x < 0x4f) {", "if ((long)x < 0x4f) {",
           "if ((x) < 0x4f) {", "if (x + 0 < 0x4f) {",
           "if ((int)(x) < 0x4f) {", "if ((signed int)x < 0x4f) {"]
W_FORMS = ["if ((int)x > 0) {", "if ((long)x > 0) {",
           "if ((x) > 0) {", "if (x + 0 > 0) {",
           "if ((signed int)x > 0) {", "if (x - 0 > 0) {"]
for f in E_FORMS:
    forge.candidate("E_" + f[4:14].replace(' ', '').replace('(', '').replace(')', ''),
                    TextEdit(start=e, end=e + len(EG), replacement=f))
for f in W_FORMS:
    forge.candidate("W_" + f[4:14].replace(' ', '').replace('(', '').replace(')', ''),
                    TextEdit(start=w, end=w + len(WG), replacement=f))
