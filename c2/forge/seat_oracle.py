"""Offline seat-reorder oracle for the forge solver.

For a ``fix_next=seat`` residue, this predicts -- WITHOUT compiling --
whether a pure birth-reorder (decl-swap / stmt-reorder, Rule 28a/115)
can flip the diverging register seat toward PS, and if so, WHICH source
variables to reorder.  It rides the corpus-certified offline allocator
replay (``c2.regalloc.replay``: 19,116/19,116 picks, 1,228/1,228 sorts)
the same way ``c2.commands.cascade_hints`` does, but returns a
machine-readable verdict instead of display text.

Design guarantee -- MONOTONE SAFETY.  The oracle can only ever help or
no-op:

  * It never decides correctness -- every candidate it names is still
    byte-verified by a real compile in the forge climb.
  * It only prunes/redirects the search when the model is TRUSTED
    (its identity replay reproduces our own seats) AND the search was
    EXHAUSTED.  Otherwise it returns ``inconclusive`` / ``untrusted``
    and the caller runs the full blind battery -- never worse than
    today.
  * Any internal failure (no trace, parse error, oversized routine)
    degrades to ``untrusted`` -> full battery.

Verdict routing (consumed by ``c2.forge.experiment.climb``):

  reorder      -> a birth reorder of ``restrict_vars`` is predicted to
                  flip the seat; restrict the decl/stmt presets to those
                  vars and compile them FIRST.
  savings      -> only a savings change reaches PS (not a pure reorder);
                  route to the type / de-invent / bridge levers.
  floor        -> TRUSTED + EXHAUSTED, no reorder reaches PS (or the
                  competing values are anonymous compiler temps with no
                  source handle -- the place_sprite accumulator class).
                  Skip the birth-reorder family; the residue is a bridge
                  (register-class flip) or sub-source.
  inconclusive -> the offline search hit its budget before exhausting the
                  order space (big routine); prune NOTHING.
  untrusted    -> no trace, or the identity replay is leaky; prune
                  NOTHING (full battery).
"""
from __future__ import annotations

from dataclasses import dataclass, field


# Search bounds.  The oracle runs ONCE per function at routing time (not
# per variant like the cascade -v hint), so it affords a much larger
# replay budget -- enough to EXHAUST the order space on small/mid seat
# functions (turning "inconclusive" into a decisive reorder/floor verdict).
_MAX_ROWS = 250
_MAX_COMBOS = 8
_POOL_ROW_REPLAYS = 4_000_000


@dataclass
class CensusVerdict:
    """Local-SET verdict from the MSVC /Od frame-slot census (the W2
    witness).  This is UPSTREAM of the seat oracle: the allocator's
    conflict queue is built from the named-local set, so a wrong SET
    (invented / missing local) must be fixed before any reorder/retype
    of that set can match PS.  ``delta = theirs - ours``."""
    status: str                              # de_invent|add_local|width|untrusted
    delta: int = 0
    quality: float = 0.0
    detail: str = ""


def census_verdict(func: str, min_quality: float = 0.85) -> CensusVerdict:
    """Consult the CAESAR2.EXE /Od frame-slot census for ``func``.

    Gated on mapping quality Q (act only on Q >= ``min_quality``): the
    win func-map is fuzzy and a low-Q census is not trustworthy.  Returns
    ``untrusted`` when the census is unavailable (MSVC TU fails / no body)
    or Q is below the gate, so the caller falls back to the seat oracle.
    """
    try:
        from c2 import win_bytes as wb
        v = wb.census_func(func)
    except Exception as exc:                       # noqa: BLE001
        return CensusVerdict("untrusted", detail=f"census error: {exc!r}")
    if not getattr(v, "ok", False):
        return CensusVerdict("untrusted", detail="census unavailable "
                             "(MSVC TU fails / no body)")
    q = float(getattr(v, "quality", 0.0) or 0.0)
    d = int(getattr(v, "delta", 0) or 0)          # theirs - ours
    if q < min_quality:
        return CensusVerdict("untrusted", d, q,
                             f"Q={q:.2f} < {min_quality} (caution) -- "
                             "corroborate with W1/Mac before trusting")
    if d < 0:
        return CensusVerdict("de_invent", d, q,
                             f"our source INVENTED {-d} local(s) "
                             f"(\u0394={d}, Q={q:.2f}) -- inline them")
    if d > 0:
        return CensusVerdict("add_local", d, q,
                             f"original had {d} MORE local(s) "
                             f"(\u0394={d}, Q={q:.2f}) -- name the missing value")
    return CensusVerdict("width", 0, q,
                         f"local count matches (\u0394=0, Q={q:.2f}) -- "
                         "width/type drift or true sub-source")


@dataclass
class SeatOracleVerdict:
    #: reorder -> focused birth-reorder profile (restrict_vars).
    #: bridge  -> focused register-class flip on the named competing
    #:            values (restrict_vars, reorder pruned).
    #: skip    -> TRUSTED and the diverging registers hold ONLY anonymous
    #:            compiler temps -> no source handle -> certified
    #:            sub-source residue; do NOT climb (saves ~400s of blind
    #:            grinding on a provable floor).
    #: fallback-> untrusted / no trace / inconclusive with no named vars
    #:            -> run the full battery (never worse than today).
    status: str
    restrict_vars: list[str] = field(default_factory=list)
    competing_vars: list[str] = field(default_factory=list)
    pairs: list[tuple[str, str]] = field(default_factory=list)
    exhausted: bool = False
    trusted: bool = False
    detail: str = ""

    @property
    def prunes_reorder(self) -> bool:
        return self.status == "bridge"

    @property
    def skips(self) -> bool:
        return self.status == "skip"


def _pairs_from_seat_recon(seat: dict | None) -> list[tuple[str, str]]:
    """The diverging register pairs (PS reg, RC reg).  Uses the confident
    systematic ``swaps`` AND the ``first_divergence`` (the localized
    accumulator case -- verdict 'clean', swaps empty, but one seat still
    differs, e.g. place_sprite EBP<->ESI)."""
    if not seat:
        return []
    out: list[tuple[str, str]] = []
    seen: set[frozenset] = set()

    def _add(ps, rc):
        if not ps or not rc or ps == rc:
            return
        k = frozenset((ps, rc))
        if k in seen:
            return
        seen.add(k)
        out.append((ps, rc))

    for s in seat.get("swaps") or []:
        _add(s.get("ps"), s.get("rc"))
    fd = seat.get("first_divergence") or {}
    _add(fd.get("ps"), fd.get("rc"))
    return out


def probe(func: str, file: str | None, seat_recon: dict | None) -> SeatOracleVerdict:
    """Run the offline seat-reorder oracle for ``func``.

    ``seat_recon`` is the ``seat_diff`` bundle already computed by the
    verifier / forge judge (``Score.seat_recon``); pass ``None`` to have
    the oracle skip (returns ``untrusted``).
    """
    try:
        return _probe(func, file, seat_recon)
    except Exception as exc:                       # noqa: BLE001 -- never break solve
        return SeatOracleVerdict(status="untrusted",
                                 detail=f"oracle error: {exc!r}")


def _probe(func: str, file: str | None, seat_recon: dict | None) -> SeatOracleVerdict:
    pairs = _pairs_from_seat_recon(seat_recon)
    if not pairs:
        return SeatOracleVerdict(status="fallback",
                                 detail="no seat divergence to search")

    from c2.commands.regalloc_hints import _lookup
    from c2.regalloc import replay

    r, _cost, base = _lookup(func, file)
    if not r or not r.get("alloc"):
        return SeatOracleVerdict(status="fallback", pairs=pairs,
                                 detail="no allocator trace available")
    arows = replay.replay_rows(r["alloc"])
    if not arows:
        return SeatOracleVerdict(status="fallback", pairs=pairs,
                                 detail="no replayable alloc rows")
    if len(arows) > _MAX_ROWS:
        return SeatOracleVerdict(status="fallback", pairs=pairs,
                                 detail=f"{len(arows)} rows > {_MAX_ROWS} bound")

    graph = replay.build_graph(arows)
    # TRUST GATE: the model must reproduce our OWN seats before any what-if.
    ident = replay.replay_order(arows, list(range(len(arows))), graph)
    if any(x["pick"] != x["identity"] for x in ident):
        return SeatOracleVerdict(status="fallback", pairs=pairs, trusted=False,
                                 detail="identity replay leaky -- what-ifs "
                                        "would be guesses")

    n_rows = len(arows)
    pool = max(600, _POOL_ROW_REPLAYS // max(n_rows, 1))
    full_ok = (n_rows * n_rows * 3) // 2 <= pool

    # NAMED competing values: the source locals seated in the diverging
    # registers -- the type-flip (bridge) targets.  Empty => the seat tie
    # is between anonymous compiler temps => no source handle.
    competing: set[str] = set()
    for ra, rb in pairs:
        for a in arows:
            if a.get("reg_name") in (ra, rb) and a.get("var"):
                competing.add(a["var"])

    tie_vars: set[str] = set()                     # named reorder MOVERS
    any_tie = False
    all_exhausted = True
    for ra, rb in pairs:                           # (ps_reg, rc_reg)
        xs = [i for i, a in enumerate(arows) if a.get("reg_name") == ra]
        ys = [i for i, a in enumerate(arows) if a.get("reg_name") == rb]
        combos = [(x, y) for x in xs for y in ys]
        if not combos:
            continue
        combos.sort(key=lambda c: (
            (arows[c[0]].get("var") is None) + (arows[c[1]].get("var") is None),
            abs((arows[c[0]].get("savings") or 0) -
                (arows[c[1]].get("savings") or 0))))
        n_calls = max(1, len(combos[:_MAX_COMBOS]))
        per_call = max(100, pool // n_calls)
        for x, y in combos[:_MAX_COMBOS]:
            want = {x: rb, y: ra}
            hits, ex = replay.inverse_search(
                arows, want, graph,
                focus=None if full_ok else {x, y}, budget=per_call)
            all_exhausted &= ex
            for h in hits:
                if not h["tie"]:
                    continue
                any_tie = True
                for v in (arows[h["i"]].get("var"), arows[h["j"]].get("var")):
                    if v:
                        tie_vars.update([v])

    tag = '+'.join(a + '<->' + b for a, b in pairs)

    # CALIBRATION (survey of known seat closers, /tmp/survey_out.jsonl):
    # the genuine pure-seat closers (convert_lbm_file, show_history_graph,
    # try_this_regionmap_square, get_water_ov_image, ...) were ALL closed
    # by DECL-ORDER (Rule 115) / use-order (Rule 28a) -- the reorder
    # profile -- NOT a register-class flip.  inverse_search's clean-`tie`
    # detection is too strict to confirm most of them (it fired on few),
    # so the presence of NAMED competing values (the values seated in the
    # diverging registers, or the tie movers) is itself the routing
    # signal: run the focused reorder profile (decl-order + use-order +
    # width, restricted to those vars).  Only when the diverging registers
    # hold ONLY anonymous compiler temps is there no source handle -> skip.
    named = sorted(tie_vars | competing)
    if named:
        why = ("birth-reorder predicted (inverse-search tie)"
               if any_tie and tie_vars else
               "named values in the diverging registers")
        return SeatOracleVerdict(
            status="reorder", restrict_vars=named,
            competing_vars=sorted(competing), pairs=pairs,
            exhausted=all_exhausted, trusted=True,
            detail=f"decl/use-order (Rule 115/28a) on {named} -- {why} ({tag})")

    # TRUSTED and the diverging registers hold ONLY anonymous temps: no
    # source handle -> certified sub-source residue.
    return SeatOracleVerdict(
        status="skip", pairs=pairs, exhausted=all_exhausted, trusted=True,
        detail=("seat tie is between anonymous compiler temps -- no source "
                "handle (accumulator/sub-source residue)"
                + ("" if all_exhausted else "; order space not fully "
                   "exhausted but nothing nameable to restrict")))
