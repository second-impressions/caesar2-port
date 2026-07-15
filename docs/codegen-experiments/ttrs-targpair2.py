# try_this_regionmap_square: 6 bytes left -- the accept-path
# target_y=y statement's TWO index temps get eax(src)/edx(dest) in PS
# but edx(src)/eax(dest) in RC (pure anon-temp seat rotation).  Probe
# tree-shape variants of the pair that could flip the temp order
# WITHOUT changing the byte-matched neighborhood.
from c2.forge import Forge, TextEdit

forge = Forge("try_this_regionmap_square", file="int_c2.c")
src = forge.index.text
fn_start = src.index("int try_this_regionmap_square(int target, int kind, int third)")

I = "                    "
PAIR = (I + "army_list[army_no].target_x = army_list[army_no].x;\n"
        + I + "army_list[army_no].target_y = army_list[army_no].y;")
a = src.index(PAIR, fn_start)
b = a + len(PAIR)

X = I + "army_list[army_no].target_x = army_list[army_no].x;\n"

variants = {
    # dest via explicit pointer deref (LHS tree gets heavier -> maybe dest-first)
    "y_ptr_lhs": X + I + "*(&army_list[army_no].target_y) = army_list[army_no].y;",
    # src via explicit pointer deref
    "y_ptr_rhs": X + I + "army_list[army_no].target_y = *(&army_list[army_no].y);",
    # both
    "y_ptr_both": X + I + "*(&army_list[army_no].target_y) = *(&army_list[army_no].y);",
    # x via pointer lhs (flip stmt1's temp order instead)
    "x_ptr_lhs": (I + "*(&army_list[army_no].target_x) = army_list[army_no].x;\n"
                  + I + "army_list[army_no].target_y = army_list[army_no].y;"),
    # y src parenthesized (NOISE expected, cheap)
    "y_paren": X + I + "army_list[army_no].target_y = (army_list[army_no].y);",
    # y as += 0-style identity? no -- semantics. use cast on RHS
    "y_cast": X + I + "army_list[army_no].target_y = (unsigned char)army_list[army_no].y;",
    # x statement with cast (flip stmt1 handling)
    "x_cast": (I + "army_list[army_no].target_x = (unsigned char)army_list[army_no].x;\n"
               + I + "army_list[army_no].target_y = army_list[army_no].y;"),
}
for name, txt in variants.items():
    forge.candidate(name, TextEdit(start=a, end=b, replacement=txt))
