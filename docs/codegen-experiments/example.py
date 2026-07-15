"""Example forge experiment -- targeted DSL + presets + cartesian search.

Read .pi/skills/forge/SKILL.md for the full DSL surface; this file is
just an annotated example you can clone with `c2 forge new`.

The workflow:
  1.  Pick a stuck function with `c2 diagnose <fn>`.
  2.  Author hypotheses below as one DSL line per hypothesis.
  3.  Run: `c2 forge run example --depth 2 --jobs $(nproc)`
  4.  Confirm + apply: `c2 forge run example --apply`
      (text-preserving patch, comments and indent preserved)
"""

from c2.forge import Forge


forge = Forge("get_random_start_points_from_dirc", file="bbarian.c")

# ── massive feeders -- one preset call adds dozens of candidates ─────────
forge.preset("tie_group")                # decl_swap + stmt_swap
forge.preset("commute_all")              # one per commutative binop site

# ── targeted hypotheses -- one DSL line per specific edit ────────────────
forge.swap_decls("x", "y")               # explicit Rule 115 swap
forge.commute_at(line=691)               # exact site I want to flip
forge.try_type("seed", ["short", "unsigned short"])  # 2 type variants

# With ~50 candidates total, `c2 forge run example --depth 2` searches
# ~1000 plans (all 2-combinations, overlap-pruned, deduped).  Bump to
# `--depth 3` for ~10k plans if the pairs pass finds nothing.
