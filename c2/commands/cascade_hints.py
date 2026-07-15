"""Cascade verdict -- the ACTIONABLE register-swap hint (agent-facing).

For a register-identity swap diff, run the corpus-certified offline
allocator cascade (c2.regalloc.replay) as an INVERSE search and emit a
verdict designed for the agent grinding the function:

  * names the exact lever to try FIRST (vars, deflines, savings), and
  * names the lever classes to NOT grind (so no compile is wasted), and
  * says when to STOP (no order reproduces PS -> structural lever).

Verdict classes, in decreasing actionability:

  TIE-REORDER   a same-savings order change reproduces PS exactly.
                ACTION: birth reorder of the named pair.  "Birth" =
                conflict-creation order, which is REVERSE LAST-USE:
                Watcom creates each conflict at its operand's LAST use
                (backward live scan, liveinfo.c) and PREPENDS to
                ConfList; SortConflicts is an UNSTABLE ShellSort with
                strict savings> (regalloc.c ConfBefore).  So for an
                equal-savings tie the value whose LAST USE is EARLIER is
                created LAST and sorts FIRST (gets the earlier register).
                LEVER: move the value PS seats in the earlier register
                so its LAST read comes earlier than the other's (hoist
                its final use up, or push the other's final use down) --
                decl/first-assign order usually does NOT move it.
                Worked: get_reg_buildings_in_radius (ef1467d4).
                Do NOT touch savings.
  SAVINGS       only an order that crosses savings classes reproduces
                PS.  ACTION: change the WEIGHTED USE COUNT of the named
                vars (source shape: chain/split an assignment, inline a
                single-use temp, add/remove a re-read).  Do NOT grind
                decl/use order -- the sort is savings-major, reorders
                cannot cross classes.
  UNREACHABLE   NO single move / pair swap of the allocation order
                reproduces PS (search EXHAUSTED).  STOP grinding
                order+savings levers; the difference is in masks/ranges
                (live-range shape, candidate narrowing) or a
                non-allocator mechanism.
  INCONCLUSIVE  the search hit its replay budget before exhausting the
                order space (big routine) -- absence of a hit means
                NOTHING; do not park on this line.
  (suppressed)  the routine fails the identity-replay trust gate
                (re-presentation mixing); a verdict would be a guess.

Cost bounds (the unbounded search once wedged a full -v run for 20+
minutes on a 220-row routine): the search space is FOCUSED on orders
that move one of the target pair's rows, combos per pair are capped
(named vars preferred), and every search carries a replay budget.

Trust: every verdict line is backed by the routine-local gate (identity
cascade replay must reproduce ALL picks before any what-if is believed).
"""
from __future__ import annotations

from dataclasses import dataclass, field

_MAX_COMBOS = 8          # (x, y) row pairs tried per register pair
_MAX_ROWS = 250          # routines larger than this get no verdict
# replay budget POOL per function, scaled by row count so worst-case work
# stays ~O(300k row-replays) regardless of routine size; split across
# pair x combo calls.  Small routines stay exhaustive (full space << pool).
_POOL_ROW_REPLAYS = 300_000


@dataclass
class CascadeVerdict:
    func: str
    lines: list[str] = field(default_factory=list)


def _tag(a: dict) -> str:
    return a.get("var") or f"t.{(a.get('name') or '?')[-4:]}"


def _loc(a: dict, src_file: str | None) -> str:
    ln = a.get("defline")
    if not ln:
        return ""
    base = (src_file or "").rsplit("/", 1)[-1]
    return f" ({base}:{ln})" if base else f" (line {ln})"


def _sim_check(r: dict, base: int | None, var_a: str, var_b: str,
               depth: int, n_uses: int, raise_a: bool) -> str:
    """Run edit_sim's diagnose_savings_edit on the Cascade-suggested edit
    and report whether the named pair would flip.  Adds CONFIRMED /
    UNCONFIRMED tag to the lever line so the agent knows the suggested
    delta is actually sufficient (or whether the heuristic gap calc is
    misleading).  Tries both directions of the named alternative
    (raise A vs lower B, or raise B vs lower A) and reports whichever
    flips the pair.

    See c2/regalloc/edit_sim.py.
    """
    try:
        from c2.regalloc.edit_sim import diagnose_savings_edit
        if raise_a:
            # sa < sb: hint says "raise sav(a) to >= sb"
            # Try: add uses to a (raise a) OR remove uses from b (lower b)
            candidates = [(var_a, n_uses, "add to"),
                          (var_b, -n_uses, "remove from")]
        else:
            # sa > sb: hint says "lower sav(a) <= sb OR raise sav(b) >= sa"
            candidates = [(var_a, -n_uses, "remove from"),
                          (var_b, n_uses, "add to")]
        for var, delta, verb in candidates:
            try:
                result = diagnose_savings_edit(
                    r, base or 10, var=var, delta_uses=[(depth, delta)],
                    pair=(var_a, var_b))
            except ValueError:
                continue
            if result.pair_check == "FLIPPED":
                return (f"  SIM CHECK: edit_sim CONFIRMED -- {verb} {var} "
                        f"({result.sav_before}->{result.sav_after}) flips "
                        f"the pair.")
        # Neither direction flipped at the heuristic delta -- report
        # so the agent knows to try a bigger delta or another lever
        return (f"  SIM CHECK: edit_sim could not flip the pair at delta "
                f"+/-{n_uses} depth-{depth} uses; the heuristic gap calc "
                f"may be too small, or this pair is masked / has a non-"
                f"allocator mechanism.")
    except Exception:
        return ""


def _savings_lever(r: dict, conf: str | None, current, target,
                   base: int | None) -> str:
    """Localize a 'needs a SAVINGS change' verdict to a concrete source edit,
    using the `cv` (CalcSavings per-block) breakdown.  savings =
    sum((save-cost) * W^depth) -- so each use-unit at loop-depth d is worth
    W^d; that tells you HOW MANY uses to add/remove and WHERE the leverage
    is (a single loop use = W, a straight-line use = 1).
    """
    if conf is None or current is None or target is None:
        return ""
    entries = (r.get("savecalc") or {}).get(conf)
    if not entries:
        return ""
    W = base or 10
    by_depth: dict[int, int] = {}
    for e in entries:
        d = min(int(e.get("depth", 0)), 4)
        by_depth[d] = by_depth.get(d, 0) + (e.get("save", 0) - e.get("cost", 0))
    by_depth = {d: u for d, u in by_depth.items() if u}
    if not by_depth:
        return ""
    gap = target - current
    if gap == 0:
        return ""
    maxd = max(by_depth)
    per_use = W ** maxd
    n = max(1, -(-abs(gap) // per_use))   # ceil(|gap| / leverage)
    verb = "ADD" if gap > 0 else "REMOVE"
    where = (f"depth-{maxd} loop use(s) (each ×{per_use})" if maxd
             else "straight-line use(s) (each +1)")
    bd = ", ".join(f"d{d}:{u}u" + (f"×{W**d}" if d else "")
                   for d, u in sorted(by_depth.items()))
    return (f"  SAVINGS (cv): use-units [{bd}] = sav {current}; gap {gap:+d} "
            f"-> {verb} ~{n} {where} of this value (a loop use is worth {W}× "
            f"a straight-line one).  `c2 savings <fn> --var X` names every "
            f"unit's ref (block/ins/kind); `c2 savings <fn> --flip VAR=REG "
            f"--depth 2` screens grounded edits through the full sort+pick "
            f"replay (side effects must match PS).")


def detect(func: str, hints, rows=None, *,
           file: str | None = None,
           rover_pairs: set[frozenset] | None = None) -> CascadeVerdict | None:
    """Build the cascade verdict for ``func`` from the per-row RuleHints."""
    from c2.commands.ps_alloc import swap_pairs_from_hints
    from c2.commands.regalloc_hints import _lookup
    from c2.regalloc import replay

    pairs, _cmp_only = swap_pairs_from_hints(hints, rows)
    if rover_pairs:
        pairs = {p for p in pairs if p not in rover_pairs}
    if not pairs:
        return None
    r, _cost, _base = _lookup(func, file)
    if not r or not r.get("alloc"):
        return None
    arows = replay.replay_rows(r["alloc"])
    if not arows:
        return None
    if len(arows) > _MAX_ROWS:
        return CascadeVerdict(func, [
            f"Cascade: verdict skipped -- {len(arows)} alloc rows exceeds "
            f"the offline-search bound ({_MAX_ROWS}); use "
            "`c2 alloc-replay` --move probes manually."])
    graph = replay.build_graph(arows)
    ident = replay.replay_order(arows, list(range(len(arows))), graph)
    if any(x["pick"] != x["identity"] for x in ident):
        return CascadeVerdict(func, [
            "Cascade: verdict SUPPRESSED -- identity-replay gate leaky for "
            "this routine (re-presentation mixing); offline what-ifs would "
            "be guesses.  Use `c2 regtrace --explain` ties + PS line marks "
            "instead."])
    identity = {x["idx"]: x["identity"] for x in ident}
    src = r.get("src_file")

    # ---- build JOINT targets: a multi-register diff is usually ONE
    # rotation; solving pairs independently chases shadows.  For each
    # pair, candidate (x, y) row combos; compose across pairs (capped).
    pair_list = sorted(pairs, key=sorted)
    combos_per_pair = []
    for p in pair_list:
        ra, rb = sorted(p)
        xs = [i for i, a in enumerate(arows) if a.get("reg_name") == ra]
        ys = [i for i, a in enumerate(arows) if a.get("reg_name") == rb]
        combos = [(x, y, ra, rb) for x in xs for y in ys]
        # cap combos: prefer named vars, then close savings (likely the
        # actually-competing conflicts)
        combos.sort(key=lambda c: (
            (arows[c[0]].get("var") is None) + (arows[c[1]].get("var") is None),
            abs((arows[c[0]].get("savings") or 0) -
                (arows[c[1]].get("savings") or 0))))
        combos_per_pair.append(combos[:_MAX_COMBOS])

    def _side_text(hit):
        side = hit.get("side_effects") or []
        if not side:
            return "  No downstream re-seats (strict)."
        items = ", ".join(f"`{_tag(arows[ix])}` {old}->{new}"
                          for ix, old, new in side[:5])
        more = f" +{len(side)-5} more" if len(side) > 5 else ""
        return (f"  SIDE EFFECTS ({len(side)} re-seat(s)): {items}{more} "
                "-- these must MATCH PS's other diff rows (check the "
                "Reg-swap annotations); if they do, this one edit closes "
                "the whole cascade.")

    def _hit_text(hit, label):
        i, j = hit["i"], hit["j"]
        a, b = arows[i], arows[j]
        if hit["kind"] == "move":
            direction = "after" if j > i else "before"
        else:
            direction = "in place of"
        sa_, sb_ = a.get("savings"), b.get("savings")
        if hit["tie"]:
            return (f"Cascade: {label} REACHABLE by TIE-REORDER: allocate "
                    f"`{_tag(a)}`{_loc(a, src)} {direction} "
                    f"`{_tag(b)}`{_loc(b, src)} (both sav={sa_}).  ACTION: "
                    "reorder their CONFLICT BIRTHS, which is REVERSE "
                    "LAST-USE (Watcom creates each conflict at its "
                    "operand's LAST use via the backward live scan + "
                    "prepend; the equal-savings tie is an unstable "
                    "ShellSort over that order).  The value that should "
                    "sort FIRST (earlier register) must be created LAST = "
                    "have the EARLIER last use: move its final read up, or "
                    "push the other's final read down.  decl/first-assign "
                    "order usually does NOT move it.  Worked: "
                    "get_reg_buildings_in_radius (ef1467d4) -- "
                    "`height=radius*2+1; span--; width=height+span; "
                    "height=width;` put span's last use after radius's so "
                    "radius sorts first -> radius=EAX like PS.  Do NOT "
                    "change savings/shape." + _side_text(hit))
        need = (f"raise sav(`{_tag(a)}`) to >= {sb_}" if sa_ < sb_ else
                f"lower sav(`{_tag(a)}`) to <= {sb_} or raise "
                f"sav(`{_tag(b)}`) to >= {sa_}")
        # Simulator check: does the Cascade-suggested edit actually flip
        # the pair in the offline replay?  Pick the direction (raise the
        # lower-sav side to match the higher) and a reasonable depth.
        sim_check_text = ""
        if a.get("var") and b.get("var") and sa_ is not None and sb_ is not None:
            entries = (r.get("savecalc") or {}).get(a.get("conf")) or []
            maxd = max((min(int(e.get("depth", 0)), 4) for e in entries),
                       default=0)
            W = _base or 10
            per_use = W ** maxd
            gap = abs(sb_ - sa_)
            n_uses = max(1, -(-gap // per_use))
            sim_check_text = _sim_check(r, _base, a.get("var"), b.get("var"),
                                        maxd, n_uses, raise_a=(sa_ < sb_))
        return (f"Cascade: {label} needs a SAVINGS change: PS's order has "
                f"`{_tag(a)}`{_loc(a, src)} (sav={sa_}) allocating "
                f"{direction} `{_tag(b)}`{_loc(b, src)} (sav={sb_}) -- "
                f"{need}.  ACTION: change weighted use counts (chain/split "
                "an assignment, inline a single-use temp, add/remove a "
                f"re-read; check `c2 mac-fn {func}` for the original "
                "shape).  Do NOT grind decl/use order -- the sort is "
                "savings-major."
                + _savings_lever(r, a.get("conf"), sa_, sb_, _base)
                + sim_check_text
                + _side_text(hit))

    def _best(hits):
        # prefer tie-reachable, then fewest side effects, then smallest
        # displacement
        return min(hits, key=lambda h: (not h["tie"],
                                        len(h.get("side_effects") or []),
                                        abs(h["i"] - h["j"])))

    n_rows = len(arows)
    pool = max(600, _POOL_ROW_REPLAYS // max(n_rows, 1))
    n_calls = max(1, sum(len(c) for c in combos_per_pair))
    per_call = max(100, pool // n_calls)

    out: list[str] = []
    # joint solve (all pairs at once)
    if len(pair_list) > 1:
        import itertools
        joint_hits = []
        n_combo = 0
        for combo in itertools.product(*combos_per_pair):
            n_combo += 1
            if n_combo > 16:
                break
            idxs = [c[0] for c in combo] + [c[1] for c in combo]
            if len(set(idxs)) != len(idxs):
                continue
            want = {}
            focus = set()
            for x, y, ra, rb in combo:
                want[x], want[y] = rb, ra
                focus |= {x, y}
            jh, _ex = replay.inverse_search(arows, want, graph,
                                            focus=focus, budget=per_call)
            joint_hits += jh
        if joint_hits:
            label = "+".join("<->".join(sorted(p)) for p in pair_list)
            out.append(_hit_text(_best(joint_hits), label) +
                       "  [ONE order change resolves the whole swap set]")
            return CascadeVerdict(func, out)

    # per-pair fallback; rank so the agent acts on the FIRST line
    # (0 = tie-reorder, 1 = savings, 2 = unreachable, 3 = no binding row)
    ranked: list[tuple[int, str]] = []
    for p, combos in zip(pair_list, combos_per_pair):
        ra, rb = sorted(p)
        label = f"{ra}<->{rb}"
        if not combos:
            ranked.append((3, f"Cascade: {label}: no alloc row holds one "
                           "side (rover/scratch seat, not an allocator "
                           "binding) -- do NOT grind decl/use order for "
                           "this pair."))
            continue
        hits = []
        all_exhausted = True
        # full order space when it fits the budget (a STOP over the full
        # space is the strongest claim); focused otherwise
        full_ok = (n_rows * n_rows * 3) // 2 <= per_call
        for x, y, _ra, _rb in combos:
            # PARTIAL want: constrain only the pair; downstream rows may
            # re-seat (reported as side effects).  Strict matching
            # mislabelled whole-cascade shifts as UNREACHABLE
            # (handle_collision: the sav-9 tie swap reproduces PS's
            # copy-home plus 4 legitimate downstream re-seats).
            want = {x: _rb, y: _ra}
            h, ex = replay.inverse_search(
                arows, want, graph,
                focus=None if full_ok else {x, y}, budget=per_call)
            hits += h
            all_exhausted &= ex
        if hits:
            h = _best(hits)
            ranked.append((0 if h["tie"] else 1, _hit_text(h, label)))
        elif not all_exhausted:
            ranked.append((2, f"Cascade: {label} INCONCLUSIVE -- replay "
                           "budget hit before the order space was "
                           "exhausted (big routine); absence of a hit "
                           "means NOTHING here, do not park on this line."))
        else:
            space = ("any single allocation-order move/swap" if full_ok
                     else "any move/swap involving the pair's rows "
                          "(focused space)")
            # H2 caveat: if the tied rows have EQUAL savings, the order
            # is set by the UNSTABLE ShellSort over conflict-CREATION
            # order (ConfBefore is savings-only -- confirmed from
            # wcc386.exe va 0x58098).  Our replay's creation order comes
            # from the INSTRUMENTED trace image, whose heap layout
            # perturbs that order vs the clean compiler -- so for an
            # equal-savings tie this UNREACHABLE verdict is UNRELIABLE
            # (worked example: get_region_revolt_points' ECX<->EDX index
            # tie -- instrumented build picks EDX=PS, clean build picks
            # ECX, same source).  Creation-order source changes
            # (statement/decl/first-assign reordering) may still flip the
            # clean-compile allocation; permute it and verify the bytes.
            h2 = any(
                arows[x].get("savings") == arows[y].get("savings")
                for x, y, _ra, _rb in combos)
            if h2:
                ranked.append((2, f"Cascade: {label} UNREACHABLE by {space} "
                               f"(search exhausted, {n_rows} rows) -- but this "
                               "is an EQUAL-SAVINGS (H2) tie resolved by the "
                               "unstable ShellSort over conflict-CREATION "
                               "order, and our replay's creation order is from "
                               "the INSTRUMENTED trace (heap layout perturbs it "
                               "vs the clean compile).  VERDICT UNRELIABLE for "
                               "H2 ties: the clean-build LEVER is -- "
                               "conflicts are created at each operand's LAST use "
                               "(backward live scan) and PREPENDED; the tie is an "
                               "unstable ShellSort over that reverse-last-use "
                               "order, so the value PS seats in the EARLIER "
                               "register must be created LAST = have the EARLIER "
                               "last use.  Move that value's final read up (or the "
                               "other's down) and verify; decl/first-assign order "
                               "usually does NOT move it.  Worked: "
                               "get_reg_buildings_in_radius (ef1467d4).  Screen "
                               "offline: `c2 savings <fn> --flip VAR=REG "
                               "--depth 2` (full sort+pick replay) -- do NOT "
                               "park on this line."))
            else:
                ranked.append((2, f"Cascade: {label} UNREACHABLE by {space} "
                               f"(search exhausted, {n_rows} rows).  STOP grinding "
                               "decl/use-order and savings levers for this "
                               "pair; the difference is masks/ranges "
                               "(live-range shape, candidate narrowing) or a "
                               "non-allocator mechanism (rover, treegen)."))
    ranked.sort(key=lambda t: t[0])
    seen: set[str] = set()
    for _rank, ln in ranked:
        # dedupe identical verdict bodies modulo the pair label (several
        # pairs often share one lever -- one line is enough for the agent)
        key = ln.split(": ", 1)[-1]
        if key in seen:
            continue
        seen.add(key)
        out.append(ln)
    if len(out) < len(ranked):
        out.append(f"Cascade: ({len(ranked) - len(out)} further pair "
                   "verdict(s) deduped -- same action)")
    return CascadeVerdict(func, out) if out else None


def render_lines(v: CascadeVerdict) -> list[str]:
    return v.lines
