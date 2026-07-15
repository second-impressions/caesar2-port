"""battle_auto_resolve -- whole-function seat rotation root probe.

RC named seats are PS's rotated one register down the DoubleRegs
order: ratio_band EDX vs EBX, their_str EBX vs ECX, our_str ECX vs
ESI, their_score ESI vs EDI, our_score EDI vs EBP.  ratio_band is
queue #0 (sav=76): PS's allocator rejected EDX for it, RC's didn't.
Probe: expression/statement levers around ratio_band's live range
(the two else-if chains + the valueDIVtotal call) that could add an
EDX conflict (div staging, call-arg order, rand128&7 form).
"""

from c2.forge import Forge

forge = Forge("battle_auto_resolve", file="bbarian.c")

forge.preset("tie_group")
forge.preset("commute_all")
forge.preset("relorder_all")
forge.preset("compound_assign_expand")
forge.preset("incdec_toggle")
forge.preset("bytemask")
