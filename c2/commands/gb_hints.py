"""Rule 124 reader -- explain a register pick from the gb/tg trace.

For each conflict involved in an observed register-identity swap, classify
WHY GiveBestReg picked what it picked (the algorithm, verified in 10.0a
GiveBestReg@0x57b78: argmax CountRegMoves saves; tie -> first candidate
already subset-of GivenRegisters when the current best is not; else
candidate-list order) and show the full comparison set, so the agent can
see which of the three Rule 124 knobs (savings order / MOV credit / Given
tie-break) must move to reproduce PS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PickExplain:
    var: str
    reg: str
    savings: int
    reason: str                       # "credit" | "given-tie-break" | "list-order" | "forced"
    detail: str
    scores: list = field(default_factory=list)
    skipped: list = field(default_factory=list)   # (cand, "masked"|"TooGreedy")


def _explain_row(a: dict) -> Optional[PickExplain]:
    scores = a.get("cand_scores") or []
    pick = a.get("reg_name")
    if not scores or not pick:
        return None
    cands = [e["cand"] for e in scores]
    saves = {e["cand"]: e["saves"] for e in scores}
    tree = a.get("tree_cands") or []
    veto = set(a.get("tg_veto") or [])
    skipped = []
    for c in tree:
        if c in ("ESP",) or c in cands:
            continue
        skipped.append((c, "TooGreedy" if c in veto else "masked"))
    if len(cands) == 1:
        reason, detail = "forced", f"only survivor of {len(tree)} tree candidates"
    elif pick in saves and saves[pick] > 0 and saves[pick] == max(saves.values()):
        reason = "credit"
        detail = (f"CountRegMoves credit {saves[pick]} beats "
                  f"{max((v for c, v in saves.items() if c != pick), default=0)} "
                  f"(a MOV/2-op ins in range touches {pick})")
    elif pick != cands[0] and saves.get(pick, 0) == saves.get(cands[0], 0):
        gb = a.get("given_before")
        gtxt = f" (Given=0x{gb:x} at this pick)" if isinstance(gb, int) else ""
        reason = "given-tie-break"
        detail = (f"ties {cands[0]} at {saves.get(pick, 0)}; {pick} already in "
                  f"GivenRegisters, {cands[0]} not{gtxt} -- reorder which "
                  f"conflict allocates first to flip")
    else:
        reason = "list-order"
        detail = f"all scores 0; {pick} is first surviving candidate"
    return PickExplain(var=a.get("var") or a.get("name") or "?", reg=pick,
                       savings=a.get("savings") or 0, reason=reason,
                       detail=detail,
                       scores=[(e["cand"], e["saves"]) for e in scores],
                       skipped=skipped)


def detect(routine: Optional[dict], swap_regs: set[str]) -> list[PickExplain]:
    """Explanations for the conflicts whose PICKED register participates in
    the observed swap, in allocation (walk) order.

    Round-2 detection: the walk is ROUNDS of savings-desc order
    (id-bit starvation -> CONFLICT_ON_HOLD -> next round; 10.0a
    MoreConflicts@0x59377, docs/regalloc-mechanics.md).  A row whose
    savings EXCEED an earlier row's marks a later round: its walk
    position is creation-order sensitive, not savings -- flag it."""
    if not routine:
        return []
    out = []
    running_min = None
    for a in routine.get("alloc") or []:
        sav = a.get("savings") or 0
        later_round = running_min is not None and sav > running_min
        if running_min is None or sav < running_min:
            running_min = sav
        if a.get("reg_name") in swap_regs:
            e = _explain_row(a)
            if e is not None:
                if later_round:
                    e.detail += ("  [ROUND-2: allocated after lower-savings "
                                 "conflicts = id-bit starved; position is "
                                 "creation-order sensitive]")
                out.append(e)
    return out


def render(explains: list[PickExplain], max_rows: int = 4) -> list[str]:
    lines = []
    for e in explains[:max_rows]:
        sc = " ".join(f"{c}:{v}" for c, v in e.scores)
        sk = ("; skipped " + ",".join(f"{c}({why})" for c, why in e.skipped)
              ) if e.skipped else ""
        lines.append(f"{e.var}->{e.reg} sav={e.savings} [{e.reason}] "
                     f"{e.detail}  scores: {sc}{sk}")
    if len(explains) > max_rows:
        lines.append(f"\u2026 {len(explains) - max_rows} more (see al rows)")
    return lines
