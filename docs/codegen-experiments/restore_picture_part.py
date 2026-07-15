"""restore_picture_part: forge experiment on restore_picture_part (display.c).

4 byte_diff, seat 1/5, all 11/11 lines IR-identical.  Tiny function,
mostly byte-pack expressions like `(p[1] << 8) + p[0]` -- the diff is
almost certainly a commute/ordering tie in those.

Throw every preset + every commute site.
"""

from c2.forge import Forge

forge = Forge("restore_picture_part", file="display.c")

forge.preset("tie_group")
forge.preset("decl_swap_all")
forge.preset("stmt_swap_adjacent")
forge.preset("firstassign")
forge.preset("commute_all")
forge.preset("relorder_all")
forge.preset("type_sweep")
forge.preset("shift1")
forge.preset("bytemask")

# `c2 forge run restore_picture_part --depth 3 --jobs $(nproc)`
