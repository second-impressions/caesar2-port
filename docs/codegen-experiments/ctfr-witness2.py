# city_test_for_road: Mac+Win dual-witness forms that change the
# CONFLICT ARRAY (ShellSort input) without (hopefully) changing code:
#  - init loop: three separate `= 0` stores (Mac), descending order --
#    kills the chain-assign temps
#  - forbidden: (char)world_dir cast (BOTH ports show the cast)
#  - return type uchar (Mac signature)
from c2.forge import Forge, TextEdit

forge = Forge("city_test_for_road", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{")


def cand(name, old, new):
    a = src.index(old, fn_start)
    forge.candidate(name, TextEdit(start=a, end=a + len(old), replacement=new))


INIT = "for (i = 0; i < 8; i += 2) slots[i][0] = slots[i][1] = slots[i][2] = 0;"
cand("init_sep_desc", INIT,
     "for (i = 0; i < 8; i += 2) {\n"
     "        slots[i][2] = 0;\n"
     "        slots[i][1] = 0;\n"
     "        slots[i][0] = 0;\n"
     "    }")
cand("init_sep_asc", INIT,
     "for (i = 0; i < 8; i += 2) {\n"
     "        slots[i][0] = 0;\n"
     "        slots[i][1] = 0;\n"
     "        slots[i][2] = 0;\n"
     "    }")

FORB = "forbidden = (world_dir + 4) & 7;"
cand("forb_schar_plus", FORB, "forbidden = ((signed char)world_dir + 4) & 7;")
cand("forb_uchar_plus", FORB, "forbidden = ((unsigned char)world_dir + 4) & 7;")
cand("forb_char_plus4u", FORB, "forbidden = ((signed char)world_dir + 4u) & 7;")

# return type uchar (edit signature + forward decl consistency handled by
# replacing only the definition line; the fn returns int-compatible values)
SIG = "int city_test_for_road(int x, int y, int map_ref, int world_dir)\n{\n    unsigned char slots"
a = src.index(SIG, fn_start)
forge.candidate("ret_uchar", TextEdit(start=a, end=a + len("int city_test_for_road"),
                                      replacement="unsigned char city_test_for_road"))
