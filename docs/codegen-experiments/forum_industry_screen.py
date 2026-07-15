"""forum_industry_screen: forge experiment (seat-tier residue, screens.c).

RESULT: PARTIAL at depth=2.  Best plan
    swap_decls(i, hasup) + swap_decls(diff, pipe2)
drops standalone-TU bytes 139 -> 119 (Δ-20) but leaves the project
oracle's layered shape_distance unchanged at seat 1/8 -- the canonical
metric is what the AGENTS.md Hard Rule #3 oracle uses, so the partial
isn't a "clear win" worth committing.  Reverted.

Per `c2 regtrace`: the residue is a single seat tie at the project
level (shape ir 0/29 / width 0/3 / spill 0/8 / seat 1/8).  Closing it
would need a non-structural lever (cache_global, or a value-flow
restructure that moves the dominant value off the contested register
before allocation reaches it).  Classified sub-source until a new
lever lands.
"""
from c2.forge import Forge
forge = Forge("forum_industry_screen", file="screens.c")
forge.preset("tie_group")
forge.preset("firstassign")
forge.preset("commute_all")
forge.preset("relorder_all")
forge.preset("bytemask")
forge.preset("shift1")
