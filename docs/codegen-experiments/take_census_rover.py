"""take_census_rover -- hunt the wall inc-vs-lea coalescing + rover temp seats.

After the 2026-07-03 shape recovery (ir 28->2), the residue is one
coalescing island (wall structure_pass_count++ compiles lea edx vs PS
inc eax) plus 5 same-length rover temp seats.  Singles+pairs of the
full battery are exhausted (climb).  This experiment runs the full
battery at depth 3, island-ordered, capped.
"""
from c2.forge import Forge

forge = Forge("take_census", file="census.c")
forge.preset("all")
