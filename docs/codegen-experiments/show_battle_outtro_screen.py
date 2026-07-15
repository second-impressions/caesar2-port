"""show_battle_outtro_screen: forge experiment (seat-tier residue, screens.c).

RESULT: NEUTRAL at depth=3.  4525 plans tried, no improving variant.
Baseline is already only 3 bytes off byte-exact (forge's standalone
metric) but the lone divergence at +0x052a is a single seat tie:

  PS:  movsx edx, word ptr [...]
  RC:  movsx ebx, word ptr [...]

Per `c2 regtrace` (note: trace flagged UNRELIABLE here -- this
function lives at screens.c L5409, past the trace's line-num cap, so
the per-value attributions are mis-located to ln0):

  EDX <-> EBX (3 rows)
    our ebx holds: (temp)[sav=3, ln0]
    lever: REVERSE LAST-USE -- give this value the EARLIER last use
    (move its final read up / the rival's down).

The reverse-last-use lever is not a structural preset; it needs a
hand-targeted `move_statement` or `commute_at` that the diagnose-time
analysis can't pinpoint without trustworthy line info.  Until either
the line-num cap is raised or someone bisects by hand, classified as
sub-source -- a HARD-class residue per `c2 worklist`.
"""
from c2.forge import Forge
forge = Forge("show_battle_outtro_screen", file="screens.c")
forge.preset("tie_group")
forge.preset("firstassign")
forge.preset("commute_all")
forge.preset("relorder_all")
forge.preset("bytemask")
forge.preset("shift1")
