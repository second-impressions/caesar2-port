"""TextEdit -- the core primitive of forge's source mutation layer.

A ``TextEdit`` is a (range, replacement) pair on a file's text.  Every
lever produces TextEdits, never an AST regeneration -- so source bytes
OUTSIDE the edited range are preserved EXACTLY (indentation, comments,
brace style, alignment).  This is non-negotiable: the project's
``observed-source-style.md`` guide is load-bearing, and a CGenerator
round-trip would silently destroy it on every variant.

Composing edits
---------------

A ``Candidate`` is a NAMED set of TextEdits that must be applied as a
group (e.g. "swap two statements" is two text moves, both required).
An ``EditPlan`` is a SELECTION of candidates whose edits don't
textually overlap (a precondition for applying them simultaneously).

The cartesian-product search builds EditPlans of size 1..N from a pool
of candidates, skipping plans whose edits overlap.  Each plan is one
variant; the worker compiles the source-with-all-edits-applied and
scores it.

Why TextEdit is enough
----------------------

* "Swap statement at line A with statement at line B" = two TextEdits
  (replace line A's text with line B's text, and vice versa).
* "Commute ``a + b`` at line 42" = one TextEdit on a sub-range of that
  line.
* "Change ``int x;`` to ``short x;``" = one TextEdit on the type word.
* "Insert ``int cache = global;`` before line 30" = one TextEdit
  inserting a zero-length range.

All of these preserve neighbouring whitespace, comments, and the
project's brace + alignment style by construction -- because the
unchanged bytes are not regenerated.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class TextEdit:
    """Replace ``[start, end)`` of the source text with ``replacement``.

    Both offsets are byte offsets into the original (unedited) file text.
    A zero-length range (``start == end``) is a pure insertion.  A
    zero-length ``replacement`` is a pure deletion.
    """

    start: int                       # inclusive byte offset
    end: int                         # exclusive byte offset
    replacement: str                 # replacement text (may be empty)
    note: str = ""                   # debug-only label

    def overlaps(self, other: "TextEdit") -> bool:
        """Two edits conflict if their byte ranges touch or overlap.

        ``[a, b)`` and ``[c, d)`` overlap iff ``a < d AND c < b``.

        Two PURE INSERTIONS at the same offset do NOT conflict: their
        relative order is made deterministic by ``EditPlan.apply``'s
        sort tie-break, so composing e.g. two hoisted decls (or a
        hoisted decl + a split init assignment) at the same anchor is
        legal.  Rejecting them (the pre-2026-07-05 behaviour) made
        every multi-insert combination unreachable -- exactly the
        combos the winning hand sessions used.
        """
        if self.start == other.start and self.end == other.end == self.start:
            # Same-offset pure insertions compose (deterministic order).
            return False
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class Candidate:
    """One NAMED hypothesis the experiment wants to try.

    The edits are a frozenset (order-independent) of TextEdits.  A
    Candidate may contain one edit (commute a binop) or several (swap
    two statements = two moves).  Forge's cartesian search picks
    SUBSETS of candidates whose edits don't overlap.
    """

    name: str
    edits: tuple[TextEdit, ...]
    # ↑ tuple (not frozenset) so the deterministic insertion order is
    #   preserved -- matters for the textual hash + reproducibility.
    note: str = ""

    def overlaps(self, other: "Candidate") -> bool:
        for a in self.edits:
            for b in other.edits:
                if a.overlaps(b):
                    return True
        return False


@dataclass(frozen=True)
class EditPlan:
    """An ordered tuple of candidates whose edits don't overlap.

    The ``apply`` method splices every TextEdit into the source text in
    reverse-offset order (so earlier offsets aren't shifted by later
    inserts/deletes).  The result is the FULL replacement file text for
    one variant.
    """

    candidates: tuple[Candidate, ...]

    @property
    def name(self) -> str:
        if not self.candidates:
            return "baseline"
        return " + ".join(c.name for c in self.candidates)

    @property
    def fingerprint(self) -> str:
        """Stable hash of the plan's edit set (used for variant dedup)."""
        h = hashlib.sha1()
        for c in self.candidates:
            for e in c.edits:
                h.update(f"{e.start}:{e.end}:{e.replacement}\0".encode())
        return h.hexdigest()[:12]

    def apply(self, source: str) -> str:
        """Apply every candidate's TextEdits to ``source`` and return the
        new full file text.  Edits are applied in REVERSE-OFFSET order so
        a later splice doesn't shift the offsets of earlier ones.
        """
        all_edits: list[TextEdit] = []
        for c in self.candidates:
            all_edits.extend(c.edits)
        # Reverse-offset apply: largest start first.  For SAME-position
        # pure insertions the replacement text is the deterministic
        # tie-break (a later-applied insert lands BEFORE an earlier one,
        # so sorting by replacement descending yields ascending final
        # order) -- plan fingerprints stay stable across runs.
        all_edits.sort(key=lambda e: (-e.start, -e.end, e.replacement))
        buf = source
        for e in all_edits:
            buf = buf[:e.start] + e.replacement + buf[e.end:]
        return buf


def plan_ok(candidates: Iterable[Candidate]) -> bool:
    """Return True if no pair of candidates in the iterable overlaps.

    O(n^2) but n is the search depth (typically <= 5), so cheap.
    """
    cs = list(candidates)
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            if a.overlaps(b):
                return False
    return True


def baseline_plan() -> EditPlan:
    """The empty plan -- source text unchanged."""
    return EditPlan(candidates=())
