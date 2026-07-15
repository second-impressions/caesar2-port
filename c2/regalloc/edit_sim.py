"""Composed simulator for HARD-bucket source-lever testing.

Chains the existing per-stage simulators so an agent can test "what if I
ADD/REMOVE a use of value X at depth D?" against the live trace in
microseconds, without recompiling:

  1. ``c2.regalloc.trace.savecalc_savings``     -- CalcSavings per conflict
  2. ``c2.regalloc.sort.sort_conflicts``        -- SortConflicts ShellSort

Pre-existing components; this module just composes them into a single
``diagnose_savings_edit()`` call that returns the predicted register
flip (or NOT) for a given candidate source edit.

Usage:

    from c2 import regalloc
    from c2.regalloc.edit_sim import diagnose_savings_edit

    td = regalloc.file_trace(Path("decomp/src/action.c"), Path("decomp/include"))
    r = td["by_func"]["get_region_over"]

    # Cascade verdict said: raise sav(ry) to >= 52 (add ~2 depth-1 uses)
    result = diagnose_savings_edit(r, td.get("loop_base", 10),
                                   var="ry", delta_uses=[(1, 2)])  # 2 uses at depth-1
    print(result.sav_before, "->", result.sav_after)
    print("rank flipped?", result.rank_changed)
    print("pair check:", result.pair_check)

For idiom-by-idiom savings contributions, see
``docs/optimiser-folding-idioms-2026-06-24.md``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from c2.regalloc.sort import sort_conflicts
from c2.regalloc.trace import savecalc_savings


@dataclass
class EditDiagnosis:
    """Predicted effect of a candidate source edit on regalloc."""
    var: str
    sav_before: int                       # current al.savings
    sav_after: int                        # predicted after the edit
    delta: int                            # sav_after - sav_before
    rank_before: int                      # position in postsort
    rank_after: int                       # predicted post-edit position
    rank_changed: bool
    # If a target pair was supplied (e.g. from a Cascade hint), did the
    # edit flip its order?
    pair_check: Optional[str] = None      # "FLIPPED" | "UNCHANGED" | None


def diagnose_savings_edit(
    routine: dict,
    loop_base: int,
    var: str,
    delta_uses: list[tuple[int, int]] | None = None,
    delta_defs: list[tuple[int, int]] | None = None,
    pair: tuple[str, str] | None = None,
) -> EditDiagnosis:
    """Predict the effect of an ADD/REMOVE source edit on ``var``'s
    savings + ConfList rank, without recompiling.

    ``delta_uses`` / ``delta_defs`` are lists of ``(depth, count)``
    pairs.  Negative counts mean REMOVE uses.  Cost units come from the
    routine's existing per-block savecalc entries (so re-uses don't
    bump cost; the model assumes added uses don't introduce spills).

    ``pair = (var_a, var_b)``: if supplied, report whether the
    perturbation flips the postsort rank of these two values (e.g. the
    Cascade-named pair whose register seats are swapped vs PS).

    Returns ``EditDiagnosis``.

    Caveats:
      * RegAlloc retry rounds add CONFLICT_ON_HOLD reseats that re-sort
        the list; this predictor models only the FIRST sort invocation.
      * The savings model assumes the edit affects only the named
        conflict's ``save`` count; it doesn't account for additional
        IL temps or new live ranges the edit might create.
      * For "size=1 byte-temp" / interleaving effects (slot-swap class),
        use the dedicated ``c2.regalloc.shellsort_sim.diagnose`` instead.
    """
    delta_uses = delta_uses or []
    delta_defs = delta_defs or []

    by_var = {a.get("var"): a for a in routine.get("alloc", []) if a.get("var")}
    a_var = by_var.get(var)
    if a_var is None:
        raise ValueError(f"no conflict named {var!r} in routine")
    conf_id = a_var["conf"]
    sav_before = a_var.get("savings", 0)

    # Build synthetic savecalc entries for the perturbation
    cv = list(routine.get("savecalc", {}).get(conf_id, []))
    for depth, count in delta_uses:
        cv.append({"blk": 0, "save": int(count), "cost": 0, "depth": depth})
    for depth, count in delta_defs:
        # def adds save (per the cost model: use=def=1 by default)
        cv.append({"blk": 0, "save": int(count), "cost": 0, "depth": depth})
    sav_after = savecalc_savings(cv, loop_base)
    delta = sav_after - sav_before

    # Build the post-perturbation ConfList: same items as current
    # presort, but with var's savings updated.
    presort = list(routine.get("presort", []))
    perturbed = []
    for entry in presort:
        if entry["node"] == conf_id:
            perturbed.append({**entry, "savings": sav_after})
        else:
            perturbed.append(entry)

    # Rank var in postsort (current) and in the simulated sort (after)
    postsort = routine.get("postsort", [])
    rank_before = next(
        (i for i, e in enumerate(postsort) if e["node"] == conf_id),
        -1,
    )
    sim_after = sort_conflicts(perturbed, savings_of=lambda c: c["savings"])
    rank_after = next(
        (i for i, e in enumerate(sim_after) if e["node"] == conf_id),
        -1,
    )

    pair_check = None
    if pair is not None:
        ca = by_var.get(pair[0])
        cb = by_var.get(pair[1])
        if ca and cb:
            rank_a_before = next(
                (i for i, e in enumerate(postsort) if e["node"] == ca["conf"]),
                -1,
            )
            rank_b_before = next(
                (i for i, e in enumerate(postsort) if e["node"] == cb["conf"]),
                -1,
            )
            rank_a_after = next(
                (i for i, e in enumerate(sim_after) if e["node"] == ca["conf"]),
                -1,
            )
            rank_b_after = next(
                (i for i, e in enumerate(sim_after) if e["node"] == cb["conf"]),
                -1,
            )
            order_before = rank_a_before < rank_b_before
            order_after = rank_a_after < rank_b_after
            pair_check = "FLIPPED" if order_before != order_after else "UNCHANGED"

    return EditDiagnosis(
        var=var,
        sav_before=sav_before,
        sav_after=sav_after,
        delta=delta,
        rank_before=rank_before,
        rank_after=rank_after,
        rank_changed=(rank_before != rank_after),
        pair_check=pair_check,
    )
