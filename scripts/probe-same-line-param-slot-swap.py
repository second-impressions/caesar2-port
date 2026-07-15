"""same-line-param-slot-swap — what source change moves the slot order
of two same-line register parameters?

Companion to `docs/slot-swap-survey-2026-06-24.md`.  The build_units_figures
function in battle.c has a 5-byte slot-swap residue between two register
PARAMs declared on the same signature line (`sub_kind`, `sub_kind2`).
Trace ground truth shows the slot order is the user-named subsequence of
the `an` (AllocNewLocal) stream; for build_units_figures, RC commits
`[sub_kind, sub_kind2]` and PS commits `[sub_kind2, sub_kind]`.

The byte-exact `raise_all_units_morale` (same battle.c TU, 3 same-line
register PARAMs) DOES preserve the post-BuildNameConflicts savings-sort
order through to AssignTemps.  build_units_figures does NOT.

This experiment probes which controlled source changes shift the
`(sub_kind, sub_kind2)` position in the trace's `an` order, so future
agents can iterate without going blind.  Each variant compiles
build_units_figures.c (with the perturbation applied) under the trace
image and reports:

  * `bytes_diff`  -- vs PS.EXE for `build_units_figures` (per
                      decomp-verify)
  * `an_order`    -- the user-named subsequence of `an`
  * `nb1_pos`     -- positions in Names[N_TEMP] pre BuildNameConflicts sort
  * `nb2_pos`     -- positions post BuildNameConflicts sort
  * `nt_pos`      -- positions at AssignTemps' size sort entry
  * `semantic_ok` -- whether the perturbation preserves source semantics
                      (Mac PPC + Win MSVC oracles agree)

The Mac PPC + Win MSVC `/Od` decompiles confirm baseline naming
`(made, kind, sub_kind, sub_kind2, ...)` is semantically correct
(4th param maps to unit_list[].unit_sub_kind store).  Any perturbation
that changes the param-to-field mapping is a semantic regression
even if it happens to drop the byte count.

Findings as of 2026-06-24:

  P1 SWAP signature decl order (sub_kind2, sub_kind)
      bytes 5 -> 3 (rename), an order unchanged.  REJECTED -- Mac/Win
      both show 4th param stores to unit_sub_kind; renaming inverts
      semantic meaning.
  P2-P12 various (void)/shadow/cast/register/early-use perturbations
      bytes unchanged.  AllocName order isn't moved by these
      (optimised away or only affect body, not param creation).
  P13 short sub_kind2 (size 2)
      bytes -> 831, an order SWAPPED.  REJECTED -- body uses int
      contexts that widen.
  P14 short sub_kind
      bytes -> 835, an unchanged direction.  REJECTED.
  P15/P16 char sub_kind2 (size 1)
      bytes 5 -> 1, an order SWAPPED.  REJECTED -- the size-sort
      lever works but Win MSVC `/Od` decompile of 0x47605c shows
      sub_kind2 is `int` in the original source; the byte-spill
      opcode at +000d (88 cl vs 89 ecx) is the residual.
  P20 char sub_kind
      bytes -> 6, an unchanged direction.  REJECTED.
  P21/P22 `register int` (either param)
      bytes unchanged.  `register` is inert in Watcom 10.0a.
  P23 in-body casts on sub_kind2 uses
      bytes unchanged.  Casts don't perturb param decl.

The trace also shows WHERE in the pipeline the swap happens.  For
build_units_figures sub_kind moves ahead of sub_kind2 between the
post-BuildNameConflicts savings sort (where sub_kind2@17, sub_kind@23)
and AssignTemps entry (sub_kind@55, sub_kind2@64).  An extra 15
positions of head-ward push happens to sub_kind2 in that window which
simple AllocName-prepend can't explain.  The candidates: `FreeName`/
re-`AllocName` cycle, per-block list rebuild from `CurrProc->names
[N_TEMP]`, or a MoreConflicts retry-round re-sort.

Open lever search avenues (FUTURE WORK):

  1. Add a `Names[N_TEMP]` walk hook at each MoreConflicts retry round
     and per-block restore to bisect the window further.
  2. Probe whether build_units_figures triggers more aggressive
     CONFLICT_ON_HOLD reseats than raise_all_units_morale does
     (the 13-param vs 3-param register-pressure delta).
  3. Probe whether a STRUCT FIELD TYPE in our headers (unit_list /
     figure_list fields) differs from PS's in a way that changes
     IL pressure.
  4. Try semantic-neutral source perturbations that affect REGISTER
     PRESSURE (e.g. one fewer local; or factoring a sub-expression).

Run with::

    uv run python scripts/probe-same-line-param-slot-swap.py

Note: this script EDITS decomp/src/battle.c in-place around each
perturbation and restores it.  Run on a clean working copy; if it
dies mid-loop, `git checkout decomp/src/battle.c` to restore.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _verify_byte_diff(fn: str = "build_units_figures") -> int | None:
    """Return the byte-diff count for `fn` from a fresh decomp-verify run."""
    obj = REPO / ".c2-cache/build/battle.obj"
    if obj.exists():
        obj.unlink()
    rc = subprocess.run(
        ["uv", "run", "c2", "decomp-verify", "decomp/src/battle.c", "-f", fn],
        capture_output=True, text=True, cwd=str(REPO), timeout=300)
    for line in rc.stdout.split("\n"):
        if fn in line:
            m = re.search(rf"{fn}\s+\(\d+b\)\s+(\d+) byte diff", line)
            if m:
                return int(m.group(1))
            if "(silent)" in line or "exact" in line:
                return 0
    return None


def _trace_an(fn: str = "build_units_figures") -> list[tuple[str, int | None]]:
    """Return the user-named subsequence of `an` for `fn`."""
    # Clear trace cache
    import glob
    for f in glob.glob("/tmp/c2-regalloc-corpus/*/trace.json"):
        os.unlink(f)
    script = """
import sys, json
sys.path.insert(0, '.')
from pathlib import Path
from c2 import regalloc
td = regalloc.file_trace(Path('decomp/src/battle.c'), Path('decomp/include'))
r = td['by_func']['build_units_figures']
by_name = {a['name']: a for a in r.get('alloc', [])}
seq = []
for a in r.get('an', []):
    alc = by_name.get(a['name'], {})
    if alc.get('var'):
        seq.append([alc['var'], alc.get('defline'), alc.get('savings')])
print(json.dumps(seq))
"""
    p = Path("/tmp/_cgex_probe.py")
    p.write_text(script)
    rc = subprocess.run(["uv", "run", "python", str(p)],
                        capture_output=True, text=True, cwd=str(REPO), timeout=180)
    try:
        return json.loads(rc.stdout)
    except json.JSONDecodeError:
        return []


def _apply_perturbation(modify_src) -> str:
    """Apply a source perturbation; return original text."""
    src = REPO / "decomp/src/battle.c"
    orig = src.read_text()
    new = modify_src(orig)
    if new == orig:
        return orig
    src.write_text(new)
    return orig


def _restore(orig: str) -> None:
    (REPO / "decomp/src/battle.c").write_text(orig)


PERTURBATIONS = [
    ("BASELINE", lambda s: s, True),
    ("P1 swap signature decl",
     lambda s: s.replace(
         "void build_units_figures(int made, int kind, int sub_kind, int sub_kind2,",
         "void build_units_figures(int made, int kind, int sub_kind2, int sub_kind,"),
     False),  # semantic regression per Mac+Win
    ("P15 char sub_kind2",
     lambda s: s.replace(
         "void build_units_figures(int made, int kind, int sub_kind, int sub_kind2,",
         "void build_units_figures(int made, int kind, int sub_kind, char sub_kind2,"),
     False),  # Win MSVC shows sub_kind2 is int
    ("P21 register int sub_kind2",
     lambda s: s.replace(
         "void build_units_figures(int made, int kind, int sub_kind, int sub_kind2,",
         "void build_units_figures(int made, int kind, int sub_kind, register int sub_kind2,"),
     True),
]


def run(verbose: bool = False) -> None:
    """Run the perturbation matrix and print the byte/an effects."""
    print(f"{'perturbation':35s}  {'bytes':>6}  {'an order':45s}  semantic_ok")
    print("-" * 100)
    for label, modify, semantic_ok in PERTURBATIONS:
        orig = _apply_perturbation(modify)
        try:
            bytes_diff = _verify_byte_diff()
            an = _trace_an()
            an_str = " ".join(f"{v}" for v, _, _ in an[:4])
        finally:
            _restore(orig)
        ok = "yes" if semantic_ok else "**NO**"
        print(f"{label:35s}  {str(bytes_diff):>6}  {an_str:45s}  {ok}")


if __name__ == "__main__":
    run(verbose="-v" in sys.argv)
