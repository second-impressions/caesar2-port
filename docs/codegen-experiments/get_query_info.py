"""get_query_info: forge experiment driven by `c2 regtrace --explain`.

WINNER (closed get_query_info to byte-exact at ff69ef7d):
    swap_decls(ax, b) + commute(+@L5051)
    -> bytes=0, shape Δ-1 (the q_entertainment commute + b-decl move)

Residue before the experiment (per `c2 diagnose`):
  HIGH concordance, shape ir 2/35 / width 0/23 / spill 0/4 / seat 1/8.
  `c2 regtrace` named the levers:
    * ECX <-> EDI swap (16 rows of asm) -- decl-order or use-order tie flip
    * ESI <-> EDX (1 row) -- ConfBefore tie
    * EDX <-> EAX (1 row) -- last-use-creation-order lever
    * type-width on `a`, `b`, `footprint` -- savings 303/303/6, byte candidates

Strategy: feed the safe tie-group preset, the byte-class type sweep,
the firstassign reorder preset, and a handful of targeted commutes /
swaps suggested by the regtrace, then run a depth-2 cartesian.  Depth-2
found the winning combination (1 of 796 plans tried, ~98s on 16 cores).
"""

from c2.forge import Forge

forge = Forge("get_query_info", file="screens.c")

# Safe regalloc tie levers (every adjacent decl swap + every adjacent
# independent stmt swap inside the function).
forge.preset("tie_group")

# Try alternate widths for the three byte-class values the regtrace
# flagged as type-width conflicts.  `unsigned char` is what they are
# today; PS may have declared them as `char` (signed) or `int`.
forge.preset("type_sweep", restrict=["a", "b", "footprint"])

# Bare-assign reorder (the verified dominant lever per the project's
# observed-source-style guide -- §13 over-decompiled-mirror corpus).
forge.preset("firstassign")

# Targeted commutes around the dominant edi/ecx swap region (the cell
# byte-load + cached-pointer materialization for the get_best_lv call).
# The IR delta sits at L5026 in the current source.
forge.commute_all_in((5020, 5060))
