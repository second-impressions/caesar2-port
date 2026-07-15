"""show_query_business_advice: forge experiment (seat-tier residue, screens.c).

RESULT: NEUTRAL at depth=2.  1118 plans tried, no improving variant.
The residue is a single ECX<->EAX seat tie at the project oracle
(shape ir 0/37 / width 0/14 / spill 0 / seat 1/5).  Per `c2 regtrace`:

  ECX <-> EAX (3 rows at +0x0156)
    our eax holds: (temp)[sav=8, ln4404]
    lever: "make ECX already-given before alloc #0"

None of the structural presets below reach this tie.  Classified as
sub-source per AGENTS.md until a new lever (cache_global / value-flow
restructure) is available.
"""
from c2.forge import Forge
forge = Forge("show_query_business_advice", file="screens.c")
forge.preset("tie_group")
forge.preset("firstassign")
forge.preset("commute_all")
forge.preset("relorder_all")
forge.preset("bytemask")
forge.preset("shift1")
