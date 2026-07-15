"""DecisionMatrix -- the multi-signal judge for forge searches.

The per-function judge (AGENTS.md) is the FIX-ORDER layer vector
``(ir, islands, width, spill, seat)`` compared lexicographically, with
bytes as the within-layer tie-break.  That is the *honest* metric --
an ir drop is a win even when bytes rise -- and stays the primary
acceptance test (``policy="lex"``).

But pure lexicographic acceptance leaves the search BLIND in two
situations the hand sessions handled by judgement:

  1. **Plateau trades.**  A step that leaves ir/islands untouched but
     trades e.g. seat +1 for bytes -60 is often the bridge to the
     next lex win (the byte diff is the bug-oracle; a big byte drop
     with stable shape usually means a real realisation got closer).
     Lex rejects it; the weighted composite can accept it.
  2. **Ranking among winners.**  Two lex-improving steps with equal
     layer vectors need a tie-break smarter than raw bytes.

``policy="lex+weighted"`` therefore accepts lex improvements FIRST
and falls back to a weighted composite -- under two hard guards that
keep it PS-faithful:

  * the ir and islands layers may NEVER regress (they are the source-
    shape truth; trading them away is drifting from PS), and
  * a plan containing a ``type(...)`` edit may not regress the width
    layer (the 2026-07-03 metric-gaming defence: a type edit's whole
    purpose is fixing width).

Weights are calibrated so one ir line ~ a whole seat family ~ hundreds
of bytes: the composite can only ever trade WITHIN the lower layers,
never against the shape truth.

The **bridge tier** (``bridge_accepts`` / ``bridge_rank_key``) is a
THIRD, deliberately looser acceptance used ONLY to widen the SEARCH,
never to change what is kept.  A residue can be strictly wall-locked:
no lex/weighted step reduces the deep layer (typically ``seat``)
without first regressing a shallow one (``ir``/``islands``/``bytes``).
The motivating case is ``city_test_for_road``'s 6-byte seat tie -- the
only seat=0 launch basins (a register-class type flip on an unrelated
local) cost ir+islands+hundreds of bytes.  Lex and weighted both
forbid that regression, so the beam can never REACH the basin from
which byte-exact is a short descent.  A bridge accepts a BOUNDED
shallow regression when it BUYS a strict improvement in a deeper
residue layer ("pay shallow, buy deep") so the beam can climb OUT of
the local minimum.  Bridges are safe because the climb's KEEP
decision is unchanged: only a net lexicographic improvement over the
run start (or byte-exact) is ever written back -- a bridge that leads
nowhere is explored and discarded.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


LAYER_NAMES: tuple[str, ...] = ("ir", "islands", "width", "spill", "seat")

#: Default layer weights for the composite.  Deliberately steep between
#: adjacent layers (x2.5-4) so the composite approximates lex order
#: unless a LARGE lower-layer/byte win is on offer.
DEFAULT_WEIGHTS: dict[str, float] = {
    "ir": 1000.0,
    "islands": 250.0,
    "width": 120.0,
    "spill": 60.0,
    "seat": 20.0,
    "bytes": 1.0,
}


@dataclass(frozen=True)
class Verdict:
    """One acceptance decision."""

    accept: bool
    reason: str                 # "byte-exact" | "lex" | "weighted" | rejection
    weighted: float             # composite delta (negative = toward PS)

    def __bool__(self) -> bool:          # truthiness == acceptance
        return self.accept


@dataclass
class DecisionMatrix:
    """Weighs layers, islands, and bytes into accept/rank decisions.

    ``policy``:
      * ``"lex"``          -- the strict fix-order judge (per-layer
        lexicographic; bytes tie-break).  The default for reporting.
      * ``"weighted"``     -- composite only (guards still apply).
      * ``"lex+weighted"`` -- lex first, composite fallback.  The
        climb default: it can cross byte-plateaus lex cannot.
    """

    policy: str = "lex"
    weights: dict[str, float] = field(
        default_factory=lambda: dict(DEFAULT_WEIGHTS))


    def weighted_delta(self, score, baseline) -> float:
        """Composite distance delta vs baseline (negative = better)."""
        sl, bl = score.layers, baseline.layers
        total = 0.0
        for name, sv, bv in zip(LAYER_NAMES, sl, bl):
            total += self.weights[name] * (sv - bv)
        if score.bytes >= 0 and baseline.bytes >= 0:
            total += self.weights["bytes"] * (score.bytes - baseline.bytes)
        return total


    def accepts(self, score, baseline, *,
                has_type_edit: bool = False) -> Verdict:
        """Should this variant be considered an improvement?"""
        if not score.ok:
            return Verdict(False, "build-fail", math.inf)
        if score.bytes == 0:
            return Verdict(True, "byte-exact", -math.inf)
        w = self.weighted_delta(score, baseline)
        # type-edit width guard (metric gaming defence)
        if has_type_edit and int(score.shape.get("width", 0)) > \
                int(baseline.shape.get("width", 0)):
            return Verdict(False, "type-edit width regression", w)
        lex = (score.layers, score.bytes) < (baseline.layers, baseline.bytes)
        if self.policy != "weighted" and lex:
            return Verdict(True, "lex", w)
        if self.policy in ("weighted", "lex+weighted"):
            # HARD GUARDS: the shape-truth layers may never regress.
            if score.layers[0] > baseline.layers[0] \
                    or score.layers[1] > baseline.layers[1]:
                return Verdict(False, "ir/isl regression", w)
            if w < 0.0:
                return Verdict(True, "weighted", w)
        return Verdict(False, "no improvement", w)


    def rank_key(self, score, baseline):
        """Sort key: byte-exact first, then layer vector, then the
        weighted composite, then bytes."""
        return (
            0 if score.bytes == 0 else 1,
            score.layers,
            self.weighted_delta(score, baseline),
            score.bytes,
        )

    def bridge_accepts(self, score, baseline, *,
                       ir_budget: int, isl_budget: int) -> Verdict:
        """Basin-hop acceptance: a LATERAL trade that pays a bounded
        shallow-layer (ir/islands, and any amount of bytes) regression
        to BUY a strict improvement in a DEEPER residue layer
        (width/spill/seat).

        Lex and weighted both reject these (neither may regress
        ir/islands); the bridge tier exists so the beam can climb OUT
        of a local minimum toward a seat=0 basin from which byte-exact
        is reachable.  Unlike ``accepts`` there is NO type-edit width
        guard here -- a bridge is *allowed* to regress width, that is
        the whole point (a register-class type flip is the canonical
        seat-perturbation lever).

        Accepted only when:
          * the build is ok and not already byte-exact,
          * ir regresses by <= ``ir_budget`` and islands by <=
            ``isl_budget`` (bytes are unbounded -- "let the byte and
            isle count go up"),
          * SOMETHING regressed (else lex/weighted already handle it),
            and
          * a layer DEEPER than the shallowest regressed layer strictly
            improves (pay shallow, buy deep).

        This never changes the climb's keep bar -- kept states are
        still judged lexicographically vs the run start.
        """
        if not score.ok:
            return Verdict(False, "build-fail", math.inf)
        if score.bytes == 0:
            return Verdict(True, "byte-exact", -math.inf)
        sl, bl = score.layers, baseline.layers
        # STRUCTURE first, budget LAST: this way "bridge over-budget" is
        # only ever returned for a GENUINE deep-gain bridge (so the climb
        # can WARN about the paths a too-tight budget hid, instead of
        # silently conflating them with non-bridges).
        reg_idx = next((i for i in range(len(LAYER_NAMES))
                        if sl[i] > bl[i]), None)
        if reg_idx is None:
            # nothing regressed -> a plain improvement; not a bridge
            return Verdict(False, "not a bridge", math.inf)
        buys_deep = any(sl[j] < bl[j]
                        for j in range(reg_idx + 1, len(LAYER_NAMES)))
        if not buys_deep:
            return Verdict(False, "no deep gain", math.inf)
        if sl[0] - bl[0] > ir_budget or sl[1] - bl[1] > isl_budget:
            return Verdict(False, "bridge over-budget", math.inf)
        return Verdict(True, "bridge", self.weighted_delta(score, baseline))

    def bridge_rank_key(self, score):
        """Rank bridges by clearing the DEEPEST residue first: seat,
        then spill, then width, then (minimise the shallow damage)
        islands, ir, bytes.  The REVERSE of the fix-order lex key -- a
        bridge's job is to reach the lowest-deep-residue (ideally
        seat=0) launch state, accepting shallow cost."""
        sl = score.layers
        return (sl[4], sl[3], sl[2], sl[1], sl[0], score.bytes)


def dominates(a: Sequence[int], b: Sequence[int]) -> bool:
    """a dominates b: <= in every coordinate, < in at least one."""
    le = all(x <= y for x, y in zip(a, b))
    return le and any(x < y for x, y in zip(a, b))


def pareto_front(items: Iterable[Any],
                 vector=lambda it: it.score.layers + (it.score.bytes,),
                 ) -> list:
    """The non-dominated subset over ``(ir, isl, width, spill, seat,
    bytes)``.  These are "the different wins": mutually incomparable
    trade-offs, each potentially the right branch to explore.  O(n^2);
    call on the improving subset, not the full result stream."""
    pool = [(it, tuple(vector(it))) for it in items]
    front = []
    for it, v in pool:
        if any(dominates(w, v) for _, w in pool if w != v):
            continue
        front.append(it)
    # dedupe identical vectors (keep first)
    seen: set[tuple] = set()
    out = []
    for it in front:
        v = tuple(vector(it))
        if v in seen:
            continue
        seen.add(v)
        out.append(it)
    return out
