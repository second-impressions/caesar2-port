"""test_zone_for_closest_fire -- find the temp-set change that lands PS's spill-slot order.

Context (2026-07-04): PS's `dist` is int-width (mov edx,eax at L2158) but
flipping our `char dist` -> `int dist` perturbs the anon temp set and the
unstable ShellSort (AssignTemps/DoSortList) scrambles the 8 spilled locals'
[esp+N] slots away from PS (13 [slot] islands).  Decl-order perms are proven
insufficient offline (predict_slot_ptrs: min_cov sav=105 pins rank 2, PS needs
rank 7).  The required nb2 order is unique:
  min_uncov, cov_y, min_cov, cov_x, uncov_ptr, cov_ptr, uncov_y, uncov_x
so the lever must be a temp-SET change (extra/fewer anon temps) that shifts
the ShellSort dynamics.  Baseline: int dist (PINNED -- the PS-true width).

Run:  uv run c2 forge run tzfcf-slot-shuffle --depth 2 --jobs $(nproc)
"""

from c2.forge import Forge

forge = Forge("test_zone_for_closest_fire", file="int_c2.c")

forge.preset("all")
