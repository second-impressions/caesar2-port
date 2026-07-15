"""test_reform_pattern: forge experiment on test_reform_pattern (battle.c).

Real-TU residue: 2 byte_diff = pure register-identity swap (EAX <-> EDX)
at the inner figure_list[temp_figure].unit_ref != figure_list[occ].unit_ref
comparison.  binir-shape says all 10/10 source lines IDENTICAL IR --
pure regalloc, H2 equal-savings ConfBefore tie.

Full-blown sweep: every named preset, then a deeper search.
"""

from c2.forge import Forge

forge = Forge("test_reform_pattern", file="battle.c")

# Every named preset -- exhausts the safe lever catalogue.
forge.preset("tie_group")
forge.preset("decl_swap_all")
forge.preset("stmt_swap_adjacent")
forge.preset("firstassign")
forge.preset("commute_all")
forge.preset("relorder_all")
forge.preset("type_sweep")
forge.preset("shift1")
forge.preset("bytemask")

# Targeted: commute the inner != (the actual diverging cmp).
import pathlib
src = pathlib.Path("decomp/src/battle.c").read_text().splitlines()
fn_start = next(i for i, l in enumerate(src, 1) if l.startswith("int test_reform_pattern("))
for i in range(fn_start, fn_start + 60):
    line = src[i - 1]
    if "figure_list[temp_figure].unit_ref != figure_list[occ].unit_ref" in line:
        new = line.replace(
            "figure_list[temp_figure].unit_ref != figure_list[occ].unit_ref",
            "figure_list[occ].unit_ref != figure_list[temp_figure].unit_ref",
        )
        forge.replace_line(i, new)
        break

# `c2 forge run test_reform_pattern --depth 3 --jobs $(nproc)`
