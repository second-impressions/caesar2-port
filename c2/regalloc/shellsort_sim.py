"""Offline simulator of Watcom 10.0a's ShellSort + TempAllocBefore.

Reproduces the AssignTemps SortList call exactly (validated 100 %
against the live trace for build_units_figures' 123-entry input).
Use it to predict the output of source-level perturbations WITHOUT
recompiling -- a fast iteration loop for the Rule 107 slot-swap
residue class.

Key insight:  10.0a's ShellSort (`bld/cg/c/sortlist.c` in OW v1; the
binary at `0x66689` in 10.0a) is **NOT stable** for same-size temps
when they are INTERLEAVED with different-size temps.  The gap-based
swaps between size=1 and size=4 temps drag adjacent same-size temps
into non-input order.  This is what causes the
build_units_figures same-line-PARAM slot-swap residue:  the size=1
anonymous byte temps from the body's byte-store statements between
sub_kind2 and sub_kind perturb sub_kind2's position past sub_kind.

The same source set has multiple FLIPPING permutations:

* swap input positions of sub_kind / sub_kind2     -> output flipped
* remove the size=1 temps between them             -> output flipped
* insert a size=1 just before sub_kind             -> output flipped
* relocate a size=1 from before sub_kind2 to between -> output flipped

The challenge is to find a SOURCE-FAITHFUL change that achieves one
of these input permutations.  This simulator lets you test candidate
perturbations of the INPUT array directly, then map back to source.

See `docs/slot-swap-survey-2026-06-24.md` for the broader context.
"""
from __future__ import annotations


def temp_alloc_before(t1: dict, t2: dict) -> bool:
    """The 10.0a `TempAllocBefore` comparator at va `0x55503`.

    Layout per `c2/regalloc/trace.py`'s `nt_pre`/`nt_post` schema:
    each temp is ``{"name": str, "size": int, "usage": int,
    "flags": int}``.  ``flags`` is the dword at offset +0x28..+0x2b
    in the `name` struct; byte at +0x2b carries USED_AS_FD at bit 2.

    Returns True iff t1 should sort BEFORE t2.  Distinct same-size
    non-FD temps return FALSE both ways (no swap -- but ShellSort
    can still re-order them via transitive swaps when smaller-size
    temps are present, see module doc).
    """
    fd1 = (t1["flags"] >> 24) & 0x2  # byte +0x2b bit 2 = USED_AS_FD
    fd2 = (t2["flags"] >> 24) & 0x2
    if fd1 and not fd2:
        return True
    if fd2 and not fd1:
        return False
    if t1["size"] < t2["size"]:
        return True
    if t1["size"] != t2["size"]:
        return False
    # equal size, distinct temps -> FALSE
    return False


def shell_sort(arr: list, before=temp_alloc_before) -> list:
    """The 10.0a ShellSort at va `0x66689`.  Gap-decreasing.

    Decompiled from the binary: the gap sequence is
    ``length, length//2+1, length//4, length//8+1, ...`` (alternating
    ``+0`` / ``+1`` adjustment until gap==1).  Each pass loops the
    inner swap loop until no swap occurs.

    Returns a NEW list.  ``arr`` is unmodified.

    Validated 100 % against the live trace for build_units_figures
    (123-entry input -> 123-entry output, identical order).
    """
    length = len(arr)
    arr = list(arr)
    gap = length
    adjust = 1
    while True:
        adjust = 0 if adjust else 1
        gap = gap // 2 + adjust
        while True:
            swap = False
            for i in range(length - gap):
                if before(arr[i + gap], arr[i]):
                    arr[i], arr[i + gap] = arr[i + gap], arr[i]
                    swap = True
            if not swap:
                break
        if gap == 1:
            break
    return arr


def position(stream: list, name_ptr: str) -> int | None:
    """Return the index of `name_ptr` in `stream` (or None)."""
    for i, e in enumerate(stream):
        if e["name"] == name_ptr:
            return i
    return None


def find_var(stream: list, by_name: dict, var: str) -> int | None:
    """Return the index of the entry whose `al` record's `var` is `var`."""
    for i, e in enumerate(stream):
        a = by_name.get(e["name"], {})
        if a.get("var") == var:
            return i
    return None


def simulate_perturbation(nt: list, perturbation) -> list:
    """Apply `perturbation(nt)` and return the ShellSort output.

    `perturbation` is a callable taking the input list and returning
    a new list (typically: swap two entries, remove some, insert).
    """
    perturbed = perturbation(list(nt))
    return shell_sort(perturbed)


from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SlotSwapDiagnosis:
    """Per-function ShellSort-instability verdict on a slot-swap residue.

    Built by ``diagnose()`` from a routine's trace data (`nt_pre`,
    `nt_post`, `slots`, `alloc`) and the asm-observed PS slot order.
    The verdict surfaces in `decomp-verify -v`'s `Slot-swap:` hint, in
    `c2 dossier`, and in `c2 worklist`'s tool string.
    """
    fn: str
    # MECHANISM CLASS
    klass: str            # "shellsort-instability" | "sort-stable-other" | "misbucketed" | "sub-source"
    # PIPELINE STAGE that perturbs the order (if known)
    perturb_stage: Optional[str] = None  # "AssignTemps-size-sort" | "BuildNameConflicts-savings-sort" | "unknown"
    # NAMED slot variables (user vars in slot order)
    slot_vars: list = field(default_factory=list)   # [(var, defline, savings, size)]
    # SIZE distribution in nt
    nt_size_dist: dict = field(default_factory=dict)
    # FLIPPING perturbations the simulator found (input-level swaps that produce PS's order)
    flipping_swaps: list = field(default_factory=list)
    # Single-INSERT windows: positions where ONE fresh sz1/sz4 temp in
    # nt_pre flips the sort output to PS's slot order (the lever class the
    # 2026-07 residue corpus actually needs; the birth attribution names
    # which pass creates temps at the window's neighbors).
    insert_windows: list = field(default_factory=list)
    # Single-REMOVAL hits: nt positions whose deletion flips to PS order.
    removal_hits: list = field(default_factory=list)
    # {name_ptr: {line, pass, pass_va, kind}} from c2.regalloc.tempbirth
    # (empty when the trace predates the nb/nbc/nbo probes, 2026-07-10).
    birth_attrib: dict = field(default_factory=dict)
    # SORT-TIME vs al-record savings split for each named slot temp
    # (set for the sort-stable-other class).  [(var, sort_sav, al_sav)]
    slot_sort_savs: list = field(default_factory=list)
    # NEXT-STEP guidance (humanly-readable)
    next_step: str = ""


def diagnose(routine: dict, ps_slot_order: Optional[list] = None) -> SlotSwapDiagnosis:
    """Classify a function's slot-swap residue + name the actionable lever.

    `routine` is a per-function trace dict (the dict at
    ``c2.regalloc.file_trace(...).by_func[name]``) carrying
    ``nt_pre``, ``nt_post``, ``slots``, ``alloc``.

    `ps_slot_order`, if supplied, is the asm-observed PS slot order
    (list of user var names).  When supplied, ``flipping_swaps`` is
    populated by searching the input-perturbation space for swaps
    that produce PS's order.

    Verdict classes:
      * ``"shellsort-instability"`` -- same-size temps interleaved with
        different-size temps; ShellSort's gap-based swaps drag them
        out of input order.  Source lever: change source so the
        interleaving differs (relocate a byte-store statement,
        change a char local to int, ...).  See
        ``docs/slot-swap-survey-2026-06-24.md``.
      * ``"sort-stable-other"`` -- ALL temps are same size, ShellSort
        is fully stable, yet slot order doesn't match PS.  Means the
        Names[N_TEMP] order at AssignTemps time differs between PS
        and RC -- driven by AllocName-prepend order or
        BuildNameConflicts savings sort.  No source lever isolated
        yet for this class.  ``show_menu_items`` is the open probe.
      * ``"sub-source"`` -- the diff is dominated by anonymous CG
        temps with no source attribution.
      * ``"misbucketed"`` -- shape `fix-next` is `ir`, not slot;
        re-triage via `c2 diagnose <fn>`.
    """
    nt = routine.get("nt_pre", [])
    na = routine.get("nt_post", [])
    slots = routine.get("slots", [])
    alloc = routine.get("alloc", [])
    by_name = {a["name"]: a for a in alloc}
    src_file = routine.get("src_file", "")

    # User-named slot variables in commit order
    slot_vars = []
    for s in slots:
        a = by_name.get(s["name"], {})
        if a.get("var"):
            slot_vars.append((a["var"], a.get("defline"), a.get("savings"),
                              s.get("size")))

    # Size distribution
    from collections import Counter
    sz_dist = Counter(e["size"] for e in nt)

    d = SlotSwapDiagnosis(fn="", klass="unknown", slot_vars=slot_vars,
                          nt_size_dist=dict(sz_dist))

    # Mostly-anonymous case
    n_anon = sum(1 for s in slots if not by_name.get(s["name"], {}).get("var"))
    if slots and n_anon / len(slots) >= 0.5:
        d.klass = "sub-source"
        d.next_step = (
            "slot-swap dominated by anonymous compiler temps (CSE/spill-"
            "intermediate temps with no source attribution).  No source-"
            "faithful lever available; classify as residue."
        )
        return d

    # ShellSort-instability check: does the sort PERTURB the named-temp
    # relative order between nt and na?
    nt_named = [e["name"] for e in nt
                if by_name.get(e["name"], {}).get("var")]
    na_named = [e["name"] for e in na
                if by_name.get(e["name"], {}).get("var")]
    named_order_preserved = nt_named == na_named

    # Sizes mix?
    sizes_mixed = len(sz_dist) > 1

    if not named_order_preserved and sizes_mixed:
        d.klass = "shellsort-instability"
        d.perturb_stage = "AssignTemps-size-sort"
        # find size-1 temps INTERLEAVED with size-4 in nt (the destabilisers)
        destabilisers = []
        if 1 in sz_dist and 4 in sz_dist:
            # find sz=1 entries that are SURROUNDED by sz=4 entries in nt
            for i in range(1, len(nt) - 1):
                if (nt[i]["size"] == 1 and
                        nt[i-1]["size"] == 4 and nt[i+1]["size"] == 4):
                    a = by_name.get(nt[i]["name"], {})
                    destabilisers.append(
                        (i, a.get("var") or "<anon>", a.get("defline")))
        d.next_step = (
            f"ShellSort instability: {sz_dist.get(1, 0)} size=1 temps "
            f"interleaved with {sz_dist.get(4, 0)} size=4 temps in "
            f"Names[N_TEMP] at AssignTemps entry.  The gap-based size "
            f"sort drags same-size temps into non-input order via "
            f"transitive effects.  Run the simulator (`c2.regalloc."
            f"shellsort_sim`) on candidate source restructurings.  "
            f"See docs/slot-swap-survey-2026-06-24.md."
        )
        if destabilisers:
            sample = destabilisers[:5]
            d.next_step += (
                "  Destabilising size=1 temps surrounded by size=4: " +
                ", ".join(f"nt[{i}] L{ln}" for i, _, ln in sample)
            )
        # Birth attribution (>= 2026-07-10 trace image): who CREATED each
        # nt entry -- turns every window/perturbation below into a named
        # source construct instead of an anonymous position.
        from c2.regalloc.tempbirth import attribute_births, birth_label
        attrib = attribute_births(routine)
        d.birth_attrib = attrib
        if attrib and destabilisers:
            d.next_step += "  Destabiliser births: " + ", ".join(
                f"nt[{i}]={birth_label(nt[i]['name'], attrib)}"
                for i, _, _ in destabilisers[:5])
        # Search the perturbation space if PS slot order is known
        if ps_slot_order is not None:
            # PS order: user var names in slot[0]..slot[N-1]
            ps_vars_in_order = list(ps_slot_order)
            def ps_ok(out_list) -> bool:
                vars_out = []
                for e in out_list:
                    a = by_name.get(e["name"], {})
                    if a.get("var") in ps_vars_in_order:
                        vars_out.append(a["var"])
                return vars_out == ps_vars_in_order
            # 1) single-adjacent input swaps
            for i in range(len(nt) - 1):
                perm = list(nt)
                perm[i], perm[i+1] = perm[i+1], perm[i]
                out = shell_sort(perm)
                if ps_ok(out):
                    a1 = by_name.get(nt[i]["name"], {})
                    a2 = by_name.get(nt[i+1]["name"], {})
                    d.flipping_swaps.append({
                        "pos": i,
                        "var_a": a1.get("var") or "<anon>",
                        "size_a": nt[i]["size"],
                        "defline_a": a1.get("defline"),
                        "var_b": a2.get("var") or "<anon>",
                        "size_b": nt[i+1]["size"],
                        "defline_b": a2.get("defline"),
                        "birth_a": birth_label(nt[i]["name"], attrib),
                        "birth_b": birth_label(nt[i+1]["name"], attrib),
                    })
            # 2) single INSERT windows (a fresh sz1 / sz4 temp at position
            #    j flips the sort to PS's order) and single REMOVALS.  This
            #    is the lever class that actually fires on the 2026-07
            #    residue corpus (set_route/build_road: the (int)-cast crutch
            #    == an insert in its window); ~3N sorts, bounded.
            if len(nt) <= 200:
                for sz, key in ((1, "insert_sz1"), (4, "insert_sz4")):
                    tmpl = {"name": "__fresh__", "size": sz, "usage": 0,
                            "flags": 0}
                    wins = [j for j in range(len(nt) + 1)
                            if ps_ok(shell_sort(nt[:j] + [tmpl] + nt[j:]))]
                    if wins:
                        d.insert_windows.append({
                            "size": sz, "positions": _runs(wins),
                            "neighbors": [
                                (j, birth_label(nt[min(j, len(nt)-1)]["name"],
                                                attrib) if attrib else "?")
                                for j in (wins[0], wins[-1])],
                        })
                rm = [i for i in range(len(nt))
                      if ps_ok(shell_sort(nt[:i] + nt[i+1:]))]
                if rm:
                    d.removal_hits = [
                        {"pos": i,
                         "var": by_name.get(nt[i]["name"], {}).get("var")
                                or "<anon>",
                         "size": nt[i]["size"],
                         "birth": birth_label(nt[i]["name"], attrib)
                                  if attrib else "?"}
                        for i in rm[:8]]
        return d

    if not named_order_preserved and not sizes_mixed:
        # All same size, yet sort still moved names -- shouldn't happen given
        # TempAllocBefore's same-size-FALSE-both-ways branch.  Flag for
        # investigation.
        d.klass = "shellsort-instability-other"
        d.perturb_stage = "AssignTemps-size-sort (anomalous)"
        d.next_step = (
            "All temps same-size but ShellSort still moved them -- "
            "unexpected.  Check TempAllocBefore's USED_AS_FD branch or "
            "the equal-size offset-tiebreak; one of them is firing."
        )
        return d

    if named_order_preserved:
        # The size sort preserved the named order.  The slot diff (if any)
        # is upstream of the size sort -- in BuildNameConflicts' savings
        # sort or in the AllocName-prepend creation order itself.
        # If PS slot order was supplied, name the EXACT pair to flip
        # (the pair where PS has temp_A before temp_B but our slot order
        # has temp_B before temp_A) -- so the agent knows which sort_sav
        # to bump up vs which to drop.
        ps_inversion = None
        if ps_slot_order:
            our_order = [v for v, *_ in slot_vars]
            for i, ps_var in enumerate(ps_slot_order):
                if ps_var not in our_order:
                    continue
                our_idx = our_order.index(ps_var)
                if our_idx != i:
                    # find what's at PS's position in our order
                    if i < len(our_order):
                        our_at = our_order[i]
                        if our_at != ps_var:
                            ps_inversion = (ps_var, our_at)
                            break
        d.klass = "sort-stable-other"
        d.perturb_stage = "BuildNameConflicts-savings-sort"
        # Read the sort-time savings (nb2) for each user-named slot temp.
        # AllocBefore (`name->v.conflict->savings`) reads these AT THE SORT
        # MOMENT -- typically lower than the al-record savings (which include
        # CalcSavings' later refinement in AssignConflicts).  Surface the
        # sort-time vs al-record savings split so the diagnoser names the
        # exact lever direction (which temp needs sort_sav nudged up/down).
        nb2 = routine.get("nb2", [])
        sort_savs = {}
        for e in nb2:
            a = by_name.get(e["name"], {})
            v = a.get("var")
            if v and v not in sort_savs:
                ss = e.get("sort_sav")
                sort_savs[v] = (ss, a.get("savings"))
        slot_sort_savs = []
        for v, ln, sv, sz in slot_vars:
            if v in sort_savs:
                slot_sort_savs.append(
                    (v, sort_savs[v][0], sort_savs[v][1]))
        # store for render_diagnosis
        d.slot_sort_savs = slot_sort_savs
        suffix = ""
        if slot_sort_savs:
            sav_str = ", ".join(
                f"{v}(sort_sav={ss},al_sav={als})"
                for v, ss, als in slot_sort_savs)
            # detect inversions in our current order (rare for sort-stable):
            inversions = []
            for i in range(len(slot_sort_savs) - 1):
                a_v, a_ss, _ = slot_sort_savs[i]
                b_v, b_ss, _ = slot_sort_savs[i+1]
                if a_ss is not None and b_ss is not None and b_ss > a_ss:
                    inversions.append(f"{b_v}(sort_sav={b_ss}) > "
                                      f"{a_v}(sort_sav={a_ss})")
            # PS inversion: if caller supplied PS slot order, name the
            # EXACT pair the source must flip
            if ps_inversion:
                a_v, b_v = ps_inversion  # PS has a before b, ours has b before a
                a_ss = next((ss for v, ss, _ in slot_sort_savs if v == a_v), None)
                b_ss = next((ss for v, ss, _ in slot_sort_savs if v == b_v), None)
                inversions.insert(
                    0, f"PS has {a_v} before {b_v}; ours has {b_v}({b_ss}) "
                       f"before {a_v}({a_ss}) -> bump {a_v}'s sort_sav above "
                       f"{b_v}'s, or drop {b_v}'s below {a_v}'s")
            if inversions:
                suffix = (
                    f"  SORT-TIME SAVINGS: {sav_str}.  Our-order inversion(s): "
                    f"{'; '.join(inversions)}.  Lever direction: bump the "
                    f"LATER temp's sort-time savings ABOVE the EARLIER (add "
                    f"a depth-0 use; uses INSIDE loops add W=10 per loop "
                    f"depth so a single in-loop use can overshoot)."
                )
            else:
                # Slot order matches sort_sav DESC -- our compile is doing
                # exactly what AllocBefore would expect.  PS must produce
                # DIFFERENT sort_savs to get a different slot order.  The
                # lever: change source so the temp at the EARLIER PS slot
                # has HIGHER sort_sav than the temp at the LATER PS slot.
                # Read PS's slot order from `c2 disasm` + the [esp+N]
                # spill stores; identify the pair to flip; then add/remove
                # a use of one of them at depth 0 (W=1) or in-loop (W=10).
                # Verify against Mac PPC + Win MSVC oracles -- any added
                # use must be semantically faithful.
                # Empirically (show_menu_items, this session): caching y
                # into an in-loop local (`int yl = y; for(...) use yl`)
                # drops y's sort_sav from 13 to 4 and lets text_group
                # (sort_sav=12) take y's slot -- worked on the order but
                # introduces an extra local that adds frame bytes.  No
                # zero-byte source-faithful lever isolated yet.  See
                # docs/slot-swap-survey-2026-06-24.md.
                suffix = (
                    f"  SORT-TIME SAVINGS: {sav_str}.  Our slot order "
                    f"matches our sort_sav DESC -- the diff vs PS is in "
                    f"WHICH temps got which sort_sav (PS-source had a "
                    f"different use-count for one of them).  Lever: change "
                    f"source so the EARLIER-PS-slot temp has HIGHER sort_sav "
                    f"than the LATER-PS-slot temp (each depth-0 use = +1, "
                    f"each in-loop use = +W^depth per AddTempSave).  Verify "
                    f"against Mac PPC + Win MSVC.  Empirically, caching the "
                    f"too-high-sav temp into an in-loop local drops its "
                    f"sort_sav and flips the slot order, but adds a frame "
                    f"local (show_menu_items session 2026-06-24)."
                )
        d.next_step = (
            "AssignTemps' size sort preserved the named-temp order; the "
            "slot diff is UPSTREAM -- driven by BuildNameConflicts' savings "
            "sort (`AllocBefore` at va 0x5905b: savings DESC for has-conflict "
            "temps).  The trace's `nb1`/`nb2` records carry the SORT-TIME "
            "savings via deref through `name->v.conflict->savings` (typically "
            "LOWER than the al-record savings, which include CalcSavings' "
            "later refinement)." + suffix
        )
        return d

    return d


def _runs(positions: list) -> list:
    """Compress a sorted position list into (lo, hi) inclusive runs."""
    runs = []
    for p in positions:
        if runs and p == runs[-1][1] + 1:
            runs[-1] = (runs[-1][0], p)
        else:
            runs.append((p, p))
    return runs


def render_diagnosis(d: SlotSwapDiagnosis, max_swaps: int = 5) -> str:
    """One-block textual rendering for surfacing in -v / dossier hints."""
    lines = [
        f"  ShellSort sim verdict: {d.klass}"
        + (f" (perturb at {d.perturb_stage})" if d.perturb_stage else "")
    ]
    if d.slot_vars:
        vs = ", ".join(
            f"{v}(L{ln},sv={sv},sz={sz})" for v, ln, sv, sz in d.slot_vars[:8]
        )
        lines.append(f"  named slots (commit order): {vs}")
    if d.nt_size_dist:
        sd = ", ".join(f"sz{k}:{v}" for k, v in sorted(d.nt_size_dist.items()))
        lines.append(f"  nt size distribution: {sd}")
    if d.flipping_swaps:
        lines.append(
            f"  simulator: {len(d.flipping_swaps)} single-adjacent input "
            f"swaps produce PS slot order; first {min(max_swaps, len(d.flipping_swaps))}:"
        )
        for sw in d.flipping_swaps[:max_swaps]:
            la = f"L{sw['defline_a']}" if sw['defline_a'] else "L?"
            lb = f"L{sw['defline_b']}" if sw['defline_b'] else "L?"
            ba = f" ←{sw['birth_a']}" if sw.get('birth_a') not in (None, '?') else ""
            bb = f" ←{sw['birth_b']}" if sw.get('birth_b') not in (None, '?') else ""
            lines.append(
                f"    nt[{sw['pos']}] ({sw['var_a']} sz={sw['size_a']} {la}{ba}) <-> "
                f"nt[{sw['pos']+1}] ({sw['var_b']} sz={sw['size_b']} {lb}{bb})"
            )
    if d.insert_windows:
        for w in d.insert_windows:
            spans = ", ".join(f"nt[{lo}..{hi}]" if hi != lo else f"nt[{lo}]"
                              for lo, hi in w["positions"])
            nb = "; ".join(f"@{j}←{lbl}" for j, lbl in w.get("neighbors", [])
                           if lbl != "?")
            lines.append(
                f"  simulator: ONE fresh sz{w['size']} temp inserted at "
                f"{spans} flips to PS's slot order"
                + (f"  (window births: {nb})" if nb else "")
            )
        lines.append(
            "    lever: the insert = a source construct that births a temp "
            "in that creation window -- FlowOut = a bool-VALUED expression "
            "(`x = (a op b)`), CondConstStores2Bool = if/else const stores "
            "differing by 1, BGNewTemp = tree-burn temps.  `c2 tempbirths "
            "<fn>` prints the fully attributed nt table."
        )
    if d.removal_hits:
        rm = ", ".join(
            f"nt[{r['pos']}] {r['var']} sz{r['size']}"
            + (f" ←{r['birth']}" if r.get('birth') not in (None, '?') else "")
            for r in d.removal_hits)
        lines.append(f"  simulator: single REMOVALS that flip to PS order: {rm}")
    if d.next_step:
        # wrap manually for readability
        lines.append("  next: " + d.next_step)
    return "\n".join(lines)
