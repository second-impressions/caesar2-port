"""battle_stats_panel: forge experiment (seat-tier residue, screens.c).

RESULT: NEUTRAL at depth=2.  1033 plans tried, no improving variant.
The residue is a single ECX<->EBP seat tie at the project oracle
(shape ir 0/34 / width 0/6 / spill 0 / seat 1/7).  Per `c2 regtrace`:

  EBP <-> EAX (1 row at +0x03e9)
    our eax holds: (temp)[sav=3,ln184], (temp)[sav=3,ln188], (temp)[sav=2,ln181]
    lever: "make EBP already-given before alloc #6" -- higher-savings
    value into EBP earlier, OR move an earlier value off EAX.

None of the structural presets below produces a candidate that achieves
this rearrangement.  Closing the seat would need either `cache_global`
(Rule 116 -- insert a local cache for a frequently-used global to seat
the cache in EBP) or a more invasive value-flow restructure.  Re-open
if a new lever lands; until then, classified as sub-source per
AGENTS.md Hard Rule #6 -> finish-line rules ("classified regalloc
tie-break with no source handle").
"""
from c2.forge import Forge
forge = Forge("battle_stats_panel", file="screens.c")
forge.preset("tie_group")
forge.preset("firstassign")
forge.preset("commute_all")
forge.preset("relorder_all")
forge.preset("bytemask")
forge.preset("shift1")
