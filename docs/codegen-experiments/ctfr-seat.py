"""city_test_for_road -- regalloc_pure seat tie (1/8), run-ledger 149/149
register-blind.  Full battery singles/pairs for the seat lever.

Run:  uv run c2 forge run ctfr-seat --depth 1 --jobs $(nproc)
"""

from c2.forge import Forge

forge = Forge("city_test_for_road", file="int_c2.c")

forge.preset("all")
