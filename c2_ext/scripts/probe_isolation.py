"""Risk-1 spike: confirm standalone-TU byte equivalence on diverse functions.

Picks a curated set of byte-exact functions spanning the codegen
surface and runs compose + verify on each.  Reports per-function
match status and aggregate stats.

Run with::

    uv run python -m c2_ext.scripts.probe_isolation
"""

from __future__ import annotations

import sys
from pathlib import Path

from c2_ext.project import ProjectConfig
from c2_ext.runs import compose, ComposeError
from c2_ext.verify import verify


# Curated picks spanning codegen patterns.  Each must be in the
# byte-exact pool for this probe to be meaningful.
SPIKE_FUNCTIONS = [
    # baseline: simple linear function
    ("barbarian_in_region",  "linear / multi-call"),
    # tail-merge dependent (the donor splice path)
    ("load_overlay_graphics", "tail-merge dependent"),
    # tail-merge donor (other side of merge)
    ("clear_map_gfx_buffers", "tail-merge donor"),
    # large function (> 500 bytes)
    ("main",                  "large function (>1kb)"),
    # function with switch / jump table
    ("region_trouble",        "linear with multi-branch"),
    # math-heavy
    ("distance",              "small math helper"),
    # function with many globals
    ("deal_with_battles",     "complex multi-branch"),
    # specific picks
    ("city_trouble",          "empty function"),
]


def main() -> int:
    project = ProjectConfig.load()
    pool = project.toolchain().byte_exact_functions()
    print(f"byte-exact pool size: {len(pool)}")

    results = []
    for fn, category in SPIKE_FUNCTIONS:
        if fn not in pool:
            print(f"  SKIP {fn} ({category}): not in byte-exact pool")
            results.append((fn, category, "SKIP", "not in pool", None))
            continue
        try:
            rd = compose(project, fn)
        except ComposeError as e:
            print(f"  COMPOSE FAIL {fn} ({category}): {e}")
            results.append((fn, category, "COMPOSE_FAIL", str(e), None))
            continue
        res = verify(project, rd)
        status = "OK" if res.exact else "DIFF"
        detail = (
            f"build_ok={res.build_ok} byte_diff={res.byte_diff} "
            f"rows={res.real_diff_rows}"
        )
        marker = "\u2713" if res.exact else ("\u2717" if res.build_ok else "BUILD")
        print(f"  {marker} {fn:35s} ({category}): {detail}")
        results.append((fn, category, status, detail, rd))

    ok = sum(1 for _, _, s, _, _ in results if s == "OK")
    skip = sum(1 for _, _, s, _, _ in results if s == "SKIP")
    n = len(results) - skip
    print()
    print(f"=== summary: {ok}/{n} exact ({skip} skipped) ===")
    if ok < n:
        print()
        print("non-exact results:")
        for fn, cat, status, detail, rd in results:
            if status not in ("OK", "SKIP"):
                print(f"  {fn} ({cat}): {detail}")
                if rd:
                    print(f"    run dir: {rd}")
    return 0 if ok == n else 1


if __name__ == "__main__":
    sys.exit(main())
