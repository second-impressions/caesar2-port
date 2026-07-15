"""Rule 123 detector -- split temps whose MERGED savings would reorder the
allocation walk.

Signature (proven on copy_ferret_run_to_army/_citizen): a register-identity
swap where PS's pick implies a conflict allocated EARLIER than its savings
rank in OUR build.  Root cause: our source splits one source-level value
into two temps (`char hi = x << 4;` / rvalue `x << 4`), so each half's
savings rank below a competing local; the original's in-place compound form
(`x <<= 4`) keeps ONE temp whose summed savings outrank the competitor and
flip the SortConflicts order.

Detection inputs are all in the existing trace (no extra instrumentation):
  - alloc rows: savings, regclass, reg picked, defline per conflict
  - the diff's swapped register set (from the layer-3/rule_hist analysis)

We report pairs of same-class temps t1,t2 with
    savings(t1) + savings(t2) > savings(D) >= max(savings(t1), savings(t2))
where D is a conflict whose picked register is part of the observed swap.
The deflines tell the agent exactly WHERE the split expression sits.

Cross-check: the stmt-IR hint independently shows the split as a
forward-only ASSIGN (+ the op) at the same line -- when both fire on the
same line, the in-place rewrite is near-certain.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class MergeHint:
    owner_name: str          # reg name of the competitor (e.g. EBX)
    owner_sav: int
    owner_line: int
    t1_sav: int
    t1_line: int
    t2_sav: int
    t2_line: int
    cls: str                 # regclass name of the mergeable temps


def detect(routine: Optional[dict], swap_regs: set[str]) -> Optional[MergeHint]:
    """``swap_regs`` is the set of full registers participating in the
    observed identity swap (e.g. {"EBX", "ECX"}).  Returns the best merge
    candidate or None."""
    if not routine:
        return None
    alloc = routine.get("alloc") or []
    if len(alloc) < 3:
        return None
    # Competitor: an allocated conflict whose picked reg is in the swap set.
    # Prefer the highest-savings one (the one whose order the merge flips).
    owners = [a for a in alloc
              if a.get("reg_name") in swap_regs
              and a.get("regclass_name") == "dword"]
    if not owners:
        return None
    owner = max(owners, key=lambda a: a.get("savings", 0))
    osav = owner.get("savings", 0)
    if osav <= 0:
        return None
    # Mergeable pairs: same-class temps below the owner whose sum beats it.
    # Same class (byte temps merge with byte temps); N_TEMP only -- named
    # locals don't merge.  Sort candidates descending; try top pairs.
    by_cls: dict[str, list[dict]] = {}
    for a in alloc:
        if a is owner:
            continue
        if a.get("nameclass_name") != "N_TEMP":
            continue
        sav = a.get("savings", 0)
        if 0 < sav < osav:
            by_cls.setdefault(a.get("regclass_name", "?"), []).append(a)
    best: Optional[MergeHint] = None
    for cls, cands in by_cls.items():
        cands.sort(key=lambda a: -a.get("savings", 0))
        for i in range(len(cands)):
            for j in range(i + 1, len(cands)):
                s1, s2 = cands[i].get("savings", 0), cands[j].get("savings", 0)
                if s1 + s2 <= osav:
                    break               # sorted: no later pair can beat it
                l1 = cands[i].get("defline") or 0
                l2 = cands[j].get("defline") or 0
                # Split halves of one expression sit on the same or
                # adjacent lines; require proximity to cut false pairs.
                if l1 and l2 and abs(l1 - l2) > 6:
                    continue
                h = MergeHint(owner_name=owner.get("reg_name", "?"),
                              owner_sav=osav,
                              owner_line=owner.get("defline") or 0,
                              t1_sav=s1, t1_line=l1,
                              t2_sav=s2, t2_line=l2, cls=cls)
                if best is None or _score(h) > _score(best):
                    best = h
    return best


def _score(h: MergeHint) -> tuple:
    """Locatable pairs (nonzero deflines) beat anonymous ones; byte-class
    pairs beat dword (the proven case is a byte sub-reg of the swapped
    full register); then larger sum."""
    return (int(bool(h.t1_line and h.t2_line)),
            int(h.cls == "byte"),
            h.t1_sav + h.t2_sav)


def render(h: MergeHint) -> str:
    return (f"Rule 123 merge candidate -- {h.cls} temps sav {h.t1_sav}"
            f"(L{h.t1_line}) + {h.t2_sav}(L{h.t2_line}) sum "
            f"{h.t1_sav + h.t2_sav} > {h.owner_name}-owner sav {h.owner_sav}"
            f"(L{h.owner_line}): if PS's pick implies the temp allocates "
            f"FIRST, our source SPLITS one value into two temps there.  "
            f"Write the in-place compound form (`x <<= k; use x;` -- no "
            f"named intermediate, no rvalue op) so one merged conflict "
            f"outranks the {h.owner_name} owner and flips the walk.  "
            f"Cross-check: stmt-IR forward-only ASSIGN on the same line.")
