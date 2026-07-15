"""``c2 worklist`` -- the session-start dispatcher / target picker.

ONE verdict per diffing function, fused from every classifier already in
the caches, each pointing at the execution tool to run next.  This is the
*front door*: run it at the start of a session to pick what to work on and
learn the dominant lever; then drop into the per-function loop
(``decomp-verify -v`` + ``shape-recon``) to actually do it.  It does NOT
replace that loop -- it routes you into it.

Buckets (the dispatch ladder, highest-priority lever first):

  WORKABLE -- a clear source lever exists:
    frame      wrong stack frame (Rule 107)         -> c2 frame-hints / -v
    shape-152  missing else-if (Rule 152)           -> -v; add else-if
    shape-151  int/short width (Rule 151)           -> -v; fix local width
    byte-widen AL-squat byte mask (Rule 126)        -> int-widen uchar locals
    byte-dename rover-seated CSE (Rule 127)         -> de-name; write expr 2x
    byte-reorder byte collateral to a dword tie     -> c2 forge solve / triage
    reorder    dword tie REACHABLE (Rule 28a/115)   -> c2 forge solve <fn>
    cache      caching mismatch (de-invent/Rule 116)-> -v de-invent hint
    decl-order decl-order lever                      -> reorder the two decls; -v

  HARD -- a lever exists but it's not a one-liner:
    savings    dword needs a SAVINGS change          -> c2 regtrace <fn>
                                                        (names the swapped value);
                                                        c2 triage (named target)
    byte-seat  byte swap, cache lacks the A/B/C/D split (rebuild) -> -v

  BLOCKED -- a GENUINELY tail-merge-blocked dependent: its WHOLE diff is in
             the shared tail it merges away AND its donor is not byte-exact
             yet (per Phase 2).  A dependent with its own body diffs is NOT
             blocked -- it routes to its real lever instead of hiding here
             (docs/comtail-cascade-analysis.md: only ~2 corpus dependents
             are genuinely tail-blocked).

  HARD ... (cont):
    byte-savings-short byte temp savings-short of AL vs a dword rival
               (Rule 157): a savings GAP, not a tie -- permute WON'T work;
               needs a SAVINGS change on the rival (Rule 156 `=0` / 123 /
               de-invent). Raising the byte is the widen trap (inverse of
               Rule 156); irreducible only if the rival's refs are all
               load-bearing.

  PARK -- no source lever FOUND by current classifiers (lowest
          priority, NOT proven irreducible -- only byte-exact closes):
    park-byte  inert byte tie (Rule 133)
    park-reg   dword swap UNREACHABLE (masks / layer-4 op-direction)

  DIAGNOSE -- no verdict fires: the new-rule frontier (dossier + shape-recon).

Reads ``.c2-cache/verify.json`` (rich per-function record, incl. the
``byte_seat`` field once the cache is rebuilt) + ``.c2-cache/triage.json``
(cascade reachability).  When the verify cache is stale vs ``decomp/src``
it is refreshed INCREMENTALLY -- only the changed ``.c`` files are
re-verified and merged back (a ~3x faster refresh than a full pass; a
full rebuild only when a header changed or most TUs changed).  A fresh
cache is a pure sub-second read.  ``--no-refresh`` skips the refresh
entirely (instant, possibly-stale).  Triage is never auto-rebuilt;
refresh it on demand with ``c2 triage --rebuild``.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

_VERIFY = Path(".c2-cache/verify.json")
_TRIAGE = Path(".c2-cache/triage.json")
_SRC = Path("decomp/src")

# A tail-merge dependent is only GENUINELY blocked (a donor fix would flip
# it byte-exact) when its ENTIRE diff is in the shared tail it merges away
# -- i.e. the last few bytes (PS emits ``jmp donor`` where RC kept the
# epilogue inline).  Anything earlier is the dependent's own body diff,
# which a donor fix does NOT touch (docs/comtail-cascade-analysis.md: only
# ~2 corpus dependents are genuinely tail-blocked; the other ~30 carry
# independent body diffs).  Mirrors ``tail_merge_rank._TAIL_WINDOW``.
_TAIL_WINDOW = 12


def _is_tail_blocked(f: dict) -> bool:
    """True iff every diff byte of ``f`` lands in its shared-tail window.

    Such a dependent's only divergence is the tail-merge itself, so the
    donor (once its tail is byte-exact) is a real gate.  A function with
    body diffs returns False -- it is NOT donor-blocked and should route to
    its own lever.  Lacking offsets/size (e.g. a hand-built test dict), it
    is conservatively treated as not tail-blocked.
    """
    offs = f.get("diff_byte_offsets") or []
    if not offs:
        return False
    size = f.get("size") or 0
    return min(offs) >= max(0, size - _TAIL_WINDOW)

# bucket -> (top-level status, one-line lever, the tool to run next)
_ROUTE = {
    "arg-swap":    ("workable", "out-of-order parameter (swapped const arg)",
                    "c2 const-audit <fn> names the callee + the const that "
                    "lands in a different __watcall arg register than PS; "
                    "fix the call's argument order, re-verify"),
    "const-boundary": ("workable", "off-by-one comparison boundary (n vs "
                    "n±1; >/>= source spelling)",
                    "c2 const-audit <fn> names the off-by-one boundary "
                    "(regalloc-invariant); forge's `boundary` lever "
                    "auto-tries the literal±1 / strict-flip fix (build+verify); "
                    "or hand-fix the </<=/>/>= operator and re-verify"),
    "const":       ("workable", "wrong constant(s) vs PS (literal / struct "
                    "stride / eq-vs-range)",
                    "c2 const-audit <fn> -- the immediate-constant multiset "
                    "diverges from PS independent of regalloc; check the "
                    "flagged literals"),
    "frame":       ("workable", "wrong stack frame (Rule 107)",
                    "c2 frame-hints <fn> ; decomp-verify -v"),
    "shape-152":   ("workable", "missing else-if (Rule 152)",
                    "decomp-verify -v ; add the else-if (cmp/jne)"),
    "shape-151":   ("workable", "int-vs-short width (Rule 151)",
                    "decomp-verify -v ; fix the local's width"),
    "byte-widen":  ("workable", "AL-squat byte mask (Rule 126)",
                    "int-widen the bare-AND `unsigned char` locals"),
    "byte-dename": ("workable", "rover-seated CSE (Rule 127)",
                    "de-name: write the byte expression twice"),
    "byte-reorder":("workable", "byte collateral to a dword tie",
                    "c2 forge solve <fn> ; c2 triage"),
    "reorder":     ("workable", "dword tie-reorder REACHABLE (last-use order)",
                    "birth=REVERSE LAST-USE: move the PS-earlier-register "
                    "value's FINAL read up (or the other's down) so it is "
                    "created last -> sorts first.  Worked: "
                    "get_reg_buildings_in_radius (ef1467d4).  c2 decomp-verify "
                    "-v reads the Cascade lever; c2 regtrace <fn> names WHICH "
                    "value is seated in the PS-earlier register (PS<->RC seat "
                    "diff); c2 forge solve <fn> only if a "
                    "mutator shifts a last use"),
    "cache":       ("workable", "caching mismatch (de-invent / Rule 116)",
                    "decomp-verify -v ; apply the De-invent/Reload hint"),
    "decl-order":  ("workable", "declaration-order lever",
                    "reorder the two named locals' declaration lines (c2 "
                    "regtrace <fn> names them) ; decomp-verify -v.  Screen "
                    "order/credit levers OFFLINE first: c2 savings <fn> "
                    "--flip VAR=REG [--depth 2] replays the full sort+pick "
                    "cascade per grounded edit and prints side effects"),
    "savings":     ("hard", "dword needs a SAVINGS change",
                    "c2 savings <fn> --var X prints the per-REF ledger "
                    "(every unit named to block/ins/kind); c2 savings <fn> "
                    "--flip VAR=REG --depth 2 searches grounded edits "
                    "through the full replay.  c2 regtrace <fn> names the "
                    "swapped VALUE + rival pair ; Rule 123 merge / de-invent"),
    "prologue":    ("hard", "prologue / callee-save divergence (Rule 89/pragma)",
                    "decomp-verify -v <fn> ; Rule 89 diagnose-first "
                    "(EAX-boundary / Rule 28a / Rule 110)"),
    "slot-swap":   ("hard", "same-size spill-slot swap (Rule 107)",
                    "c2 decomp-verify -v <fn> -- the Slot-swap: line carries "
                    "the ShellSort sim VERDICT (shellsort-instability / "
                    "sort-stable-other / sub-source).  c2 dossier <fn> shows "
                    "the same in its Rule-107 section.  For shellsort-"
                    "instability: re-order body byte-stores to move size=1 "
                    "interleaving (the simulator names the destabilising "
                    "temps).  For sort-stable-other (all-same-size): the "
                    "diff is upstream of AssignTemps' size sort -- no clean "
                    "source lever isolated yet (show_menu_items).  For "
                    "sub-source: park.  docs/slot-swap-survey-2026-06-25.md."),
    "loop-rotation": ("workable", "loop rotation (Rule 134)",
                    "rewrite the while-loop as `for ( ; cond; cnt++)` "
                    "(empty init clause + separate inc)"),
    "byte-seat":   ("hard", "byte swap (rebuild verify cache for A/B/C/D)",
                    "decomp-verify -v <fn>  (read the Byte-seat: verdict)"),
    "blocked":     ("blocked", "GENUINELY tail-merge-blocked (whole diff in "
                    "the shared tail), donor not byte-exact",
                    "make the donor's shared TAIL byte-exact, then ComTail "
                    "re-merges (c2 tail-merge --blocked ; c2 donors)"),
    "park-byte":   ("park", "inert byte tie (Rule 133) -- no lever found",
                    "PARK (open; lowest priority) -- permuting has never flipped this class"),
    "byte-rover":  ("workable", "rover-picked byte scratch (Rule 163) -- "
                    "cursor parity, NOT a GB tie",
                    "k-map frx truth vs PS picks (rover_fit anchors), then "
                    "c2 spell --suggest the delta window (rover-model.md)"),
    "byte-savings-short": ("hard", "byte temp savings-short of AL vs a dword "
                    "rival (Rule 157) -- savings gap, NOT a tie",
                    "a SAVINGS change on the RIVAL is needed (Rule 156 `=0` "
                    "/ 123 merge / de-invent); reorders WON'T work.  c2 "
                    "savings <fn> --var RIVAL prints its ref ledger (which "
                    "units are deletable); --flip screens candidates.  "
                    "Raising the byte is the widen trap (irreducible iff "
                    "the rival's refs are all load-bearing)"),
    "park-reg":    ("park", "dword swap: no lever found (masks / layer-4)",
                    "PARK (open; lowest priority) -- reorder/savings grinding "
                    "has never flipped this class.  Cheap re-check: c2 "
                    "savings <fn> --flip VAR=REG --depth 2 (an honest "
                    "negative re-certifies the park; the masked live-range "
                    "family is the un-searched space, see TODO 3b)"),
    "h2-tie":      ("hard", "equal-savings H2 tie (creation-order; cascade "
                    "verdict instrumentation-unreliable, NOT a floor)",
                    "LEVER: birth=REVERSE LAST-USE (conflicts created at the "
                    "operand's last use, backward scan + prepend; unstable "
                    "ShellSort over that order).  Make the value PS seats in "
                    "the EARLIER register have the EARLIER last use (hoist its "
                    "final read up / push the other's down).  c2 regtrace <fn> "
                    "names that value + confirms the equal-savings tie.  "
                    "Worked: get_reg_buildings_in_radius (ef1467d4).  Screen "
                    "offline first: c2 savings <fn> --flip VAR=REG --depth 2 "
                    "(full sort+pick replay; the show_left/right_overlay "
                    "closure came from its named +1-use lever).  Then verify "
                    "bytes"),
    "needs-diagnosis": ("diagnose", "no CACHED lever field -- -v has live levers",
                    "c2 decomp-verify -v <fn>  (Rule 107 slot-swap / parm-reload "
                    "/ Rule 135 / branch-encoding / Neg-corpus fire live); for a "
                    "register diff, c2 regtrace <fn> names the swapped "
                    "VALUE + lever (PS-vs-RC seat diff + ConfBefore detail, "
                    "ground truth); rarely a true new rule -- then "
                    "dossier + shape-recon"),
}
# Fix-order layers: shape & structural levers CASCADE into the regalloc ones
# (a shape/frame change re-does the register allocation below it), so they
# must be fixed -- and re-verified -- FIRST.  (rank, layer label)
_FIX_LAYER = {
    "blocked":         (0, "gate"),
    "arg-swap":        (1, "shape"),
    "const-boundary":  (1, "shape"),
    "const":           (1, "shape"),
    "shape-152":       (1, "shape"),
    "shape-151":       (1, "shape"),
    "loop-rotation":   (1, "shape"),
    "frame":           (2, "structural/layout"),
    "prologue":        (2, "structural/layout"),
    "slot-swap":       (2, "structural/layout"),
    "cache":           (3, "caching"),
    "decl-order":      (3, "caching"),
    "byte-widen":      (4, "regalloc"),
    "byte-dename":     (4, "regalloc"),
    "byte-reorder":    (4, "regalloc"),
    "byte-seat":       (4, "regalloc"),
    "byte-savings-short": (4, "regalloc"),
    "reorder":         (4, "regalloc"),
    "savings":         (4, "regalloc"),
    "h2-tie":          (4, "regalloc"),
    "park-byte":       (5, "park"),
    "byte-rover":      (3, "rover"),
    "park-reg":        (5, "park"),
    "needs-diagnosis": (6, "diagnose"),
}

_STATUS_ORDER = ["workable", "hard", "diagnose", "blocked", "park"]
_STATUS_COLOR = {"workable": "green", "hard": "yellow", "diagnose": "magenta",
                 "blocked": "cyan", "park": "bright_black"}

# Buckets whose verdict is derived from the triage (reg-swap reachability)
# cache via ``_triage_class``.  When triage.json is stale vs decomp/src,
# THESE verdicts -- and only these -- are unreliable (e.g. a function may
# read as ``park-reg`` "do not grind" when it is actually reorderable, or
# the reorder/savings split may be flipped).  Rows dominated by one of
# these get a hard ⚠ marker so the split is never trusted blind.
_TRIAGE_DERIVED = frozenset({"reorder", "savings", "h2-tie", "park-reg"})

# Source-shape (layer-1) buckets: a lever here claims the recovered SOURCE
# SHAPE is wrong (wrong literal / missing else-if / loop rotation / ...).
# When such a lever fires on an IR-IDENTICAL function (binir matches PS),
# the lever is almost certainly codegen noise (a frame-size or strength-
# reduction artifact const-audit picked up), not a real shape bug -- the
# residue is regalloc.  We surface that contradiction.
_SHAPE_LAYER = frozenset(
    b for b, (rank, _lbl) in _FIX_LAYER.items() if rank == 1)


def _shape_signal(f: dict) -> Optional[dict]:
    """The cached binir IR-identity verdict for ``f``, or None.

    ``kind`` is ``"regalloc"`` when the recovered IR is byte-for-byte
    identical to PS (shape already right -> the residue is register
    allocation / encoding, NOT source shape), ``"shape"`` when the IR
    diverges at >=1 source line (the recovered SHAPE is wrong/under-
    recovered -- fix shape first), or ``"unknown"`` when there is no IR to
    compare.  Mirrors ``binir_shape_hint``'s verdict vocabulary.
    """
    b = f.get("binir_shape_hint")
    if not b:
        return None
    dv = b.get("lines_divergent", 0)
    comp = b.get("lines_compared", 0)
    verdict = b.get("verdict")
    if verdict == "encoding_noise" or (comp > 0 and dv == 0):
        kind = "regalloc"
    elif verdict == "no_lines_with_ir" or comp == 0:
        kind = "unknown"
    else:
        kind = "shape"
    return {"kind": kind, "divergent": dv, "compared": comp}


# layered shape-distance rank: ir (1) > width (2) > spill (3) > seat (4).
# Drives the worklist sort so the highest-layer (most source-fixable)
# divergences surface first -- the shape-first priority, NOT byte count.
_FIXNEXT_RANK = {"ir": 1, "width": 2, "spill": 3, "seat": 4}


def _shape_cell(f: dict) -> str:
    """Compact per-row shape-distance cell from the cached shape_distance.

    ``ir{N}/{T}[·i{K}][+k]→fix_next`` -- the IR-divergence headline (layer
    1, the one that decides "is the source shape wrong?"), the run-ledger
    island count ``i{K}`` when available (``i0`` = regalloc_pure), plus
    ``+k`` count of the lower layers (width/spill/seat) also diverging,
    plus the next layer to fix.  Empty when no shape_distance is cached."""
    sd = f.get("shape_distance")
    if not sd:
        return ""
    ir = sd.get("ir", 0); irt = sd.get("ir_total", 0)
    extra = sum(1 for L in ("width", "spill", "seat") if sd.get(L, 0))
    base = f"ir{ir}/{irt}" if irt else f"ir{ir}"
    if sd.get("islands") is not None:
        base += f"·i{sd['islands']}"
    if extra:
        base += f"+{extra}"
    return f"{base}→{sd.get('fix_next', '?')}"


def _shape_sort_key(r: dict) -> tuple:
    """Sort key: highest fix-layer first (ir before width before ...),
    then most-divergent (by shape total) first.  Replaces the old
    biggest-bytes-first ordering."""
    rank = _FIXNEXT_RANK.get(r.get("fix_next", ""), 9)
    return (rank, -int(r.get("shape_total", 0)))



def _triage_class(t: Optional[dict]) -> str:
    cas = (t or {}).get("cascade") or []
    if not cas:
        return "no-cascade"
    if any("REACHABLE by TIE-REORDER" in l for l in cas):
        return "reachable"
    if any("needs a SAVINGS" in l for l in cas):
        return "savings"
    # H2 equal-savings ties: the UNREACHABLE verdict is instrumentation-
    # perturbed (creation-order unstable sort); NOT a park-able floor.
    if any("UNRELIABLE for H2" in l for l in cas):
        return "h2-tie"
    if any("UNREACHABLE" in l for l in cas):
        return "unreachable"
    if any("INCONCLUSIVE" in l for l in cas):
        return "inconclusive"
    return "other-cascade"


def classify_all(f: dict, tri: Optional[dict]) -> list[str]:
    """ALL independent levers that fire for one function, in dominance order.

    A function often carries SEVERAL levers in different layers (e.g.
    put_out_a = a Rule 107 slot-swap AND a Rule 134 loop-rotation).  The old
    single-bucket verdict hid the secondary ones; this returns the full set
    so the connection is never lost.  ``classify`` takes [0] as the dominant
    bucket for ranking.
    """
    rh = f.get("rule_hints") or {}
    tm = f.get("tail_merge")
    reach = _triage_class(tri)
    out: list[str] = []
    # blocked on a non-exact tail-merge donor (Phase 2 gate) -- dominant,
    # but ONLY when the dependent is genuinely tail-blocked (its whole diff
    # is in the shared tail).  A dependent with its own body diffs is not
    # gated by the donor (docs/comtail-cascade-analysis.md) -- it falls
    # through to its real lever below instead of hiding in BLOCKED.
    if (tm and tm.get("donor_status") not in ("exact", None)
            and _is_tail_blocked(f)):
        out.append("blocked")
    # const-audit: a regalloc-INVARIANT constant divergence from PS is a
    # real source bug (wrong literal / off-by-one comparison boundary), so
    # it ranks high -- fix it before chasing the regalloc cascade it feeds.
    # an out-of-order parameter is a definite semantic bug -- highest source
    # priority (a constant lands in the wrong __watcall arg register vs PS).
    if f.get("arg_swap"):
        out.append("arg-swap")
    ca = f.get("const_audit")
    if ca and ca.get("boundary_offby1"):
        out.append("const-boundary")
    if f.get("frame_hint"):
        out.append("frame")
    if ca and not ca.get("boundary_offby1"):
        out.append("const")
    if "Rule 152" in rh:
        out.append("shape-152")
    if "Rule 151" in rh:
        out.append("shape-151")
    # loop rotation (Rule 134) -- a clean workable shape fix, INDEPENDENT of
    # any regalloc residue on the same function.
    if f.get("loop_rotation"):
        out.append("loop-rotation")
    if f.get("pragma_hint"):
        out.append("prologue")
    if f.get("slot_swap"):
        out.append("slot-swap")
    bseat = f.get("byte_seat")
    if isinstance(bseat, dict) and bseat.get("case"):
        out.append({"A": "byte-reorder", "B": "byte-widen", "C": "byte-dename",
                    "D": "park-byte", "E": "byte-savings-short",
                    "R": "byte-rover"}
                   .get(bseat["case"], "byte-seat"))
    elif "Byte-reg swap" in rh:
        out.append("byte-seat")
    if reach == "reachable":
        out.append("reorder")
    if f.get("global_cache_hint") or f.get("reload_hint"):
        out.append("cache")
    if f.get("decl_order_hint"):
        out.append("decl-order")
    if reach in ("savings", "other-cascade", "inconclusive"):
        out.append("savings")
    if reach == "h2-tie":
        out.append("h2-tie")
    if reach == "unreachable" and not out:
        out.append("park-reg")
    return out or ["needs-diagnosis"]


def dominant_bucket(buckets: list[str]) -> str:
    """The bucket to ACT ON FIRST = the lowest ``_FIX_LAYER`` rank.

    A multi-lever function must be fixed shape -> structural -> regalloc
    (each cascades into the ones below; AGENTS.md), so the dominant
    verdict -- which drives the row's status AND the corpus grouping --
    must be the most-upstream lever, NOT merely the first one
    ``classify_all`` happened to emit.  ``classify_all`` emits ``frame``
    (structural, layer 2) before ``const``/``shape-152`` (shape, layer 1),
    so ``buckets[0]`` would mislabel a shape+frame function as ``[frame]``
    while the per-function view correctly says "fix the const/152 first".
    Ties within a layer fall back to ``classify_all``'s emission order
    (its within-layer priority).
    """
    return min(buckets,
               key=lambda b: (_FIX_LAYER.get(b, (9, "?"))[0], buckets.index(b)))


def classify(f: dict, tri: Optional[dict]) -> str:
    """The single dominant bucket = the most-upstream fix-order lever."""
    return dominant_bucket(classify_all(f, tri))


def _load(refresh: bool) -> tuple[list[dict], dict, list[str], bool]:
    """Return ``(diffing_functions, triage_map, notes, triage_stale)``.

    When ``refresh`` (default), AUTO-REFRESH a stale ``verify.json`` via
    the shared in-process ``get_verify_json`` (shares the warm build
    cache; also (re)populates the ``byte_seat`` field).  The refresh is
    INCREMENTAL: when only some ``.c`` files changed, just those are
    re-verified and merged into the cache (~3x faster than the full pass;
    a full rebuild only when a header changed or most TUs changed).  Either
    way it is a single verify pass over the affected files.

    It deliberately does NOT auto-rebuild ``triage.json``: that is a whole
    SECOND verify pass (the reg-swap *reachability* axis only), and the
    doubling makes the picker too slow for a session-start tool.  A stale
    triage just means the reorder/savings/park split of reg-swaps may be a
    little off -- we surface a targeted note and let the user refresh that
    axis on demand (`c2 triage --rebuild`).  ``--no-refresh`` skips the
    verify refresh too (the instant, possibly-stale view).
    """
    from c2.commands.verify_json import get_verify_json, _newest_src_mtime
    newest_src = _newest_src_mtime()
    notes: list[str] = []

    try:
        v = get_verify_json(verbose=refresh, no_build=not refresh)
    except FileNotFoundError:
        typer.secho("no .c2-cache/verify.json and --no-refresh set -- run "
                    "`c2 decomp-verify --json` first", fg="red", err=True)
        raise typer.Exit(1)
    diff = [f for f in v.get("functions", []) if f.get("diff_byte_count", 0) > 0]
    tri = json.loads(_TRIAGE.read_text()) if _TRIAGE.exists() else {}

    if not refresh and _VERIFY.exists() and _VERIFY.stat().st_mtime < newest_src:
        notes.append("verify.json is STALE (--no-refresh) -- drop the flag "
                     "to auto-rebuild it.")
    triage_stale = ((not _TRIAGE.exists())
                    or _TRIAGE.stat().st_mtime < newest_src)
    if triage_stale:
        notes.append("triage (reg-swap reachability) cache is stale -- the "
                     "reorder/savings/park split may be off; refresh that "
                     "axis on demand with `c2 triage --rebuild`.")
    return diff, tri, notes, triage_stale


def _new_rule_frontier(full_diff: list[dict], rows: list[dict],
                       as_json: bool) -> None:
    """The NEW-RULE FRONTIER picker: rank NOVEL residue families by leverage.

    A novel family (``residue-cluster`` coverage == "novel") is one no
    catalogue rule explains -- the highest-value place to mine a new rule,
    because solving the small representative generalises to the whole
    cluster.  The byte-ranked worklist steers AWAY from these (their reps
    are small); this view ranks them by ``cluster size`` (functions a new
    rule unlocks) then ``rep tractability`` (smallest diff first).
    """
    from c2.commands.residue_cluster import build_model, _label_str
    model = build_model({"functions": full_diff})
    novel = [c for c in model.clusters if c.coverage == "novel"]
    novel.sort(key=lambda c: (-c.size, model.diff_bytes.get(c.rep, 0)))
    rec = {f["name"]: f for f in full_diff}
    by_name = {r["name"]: r for r in rows}
    n_diag = sum(1 for r in rows if r["status"] == "diagnose")

    def _ir(name: str) -> bool:
        s = _shape_signal(rec.get(name, {}))
        return bool(s and s["kind"] == "regalloc")

    if as_json:
        typer.echo(json.dumps({
            "novel_families": [{
                "cid": c.cid, "size": c.size, "rep": c.rep,
                "rep_shape_cell": _shape_cell(rec.get(c.rep, {})),
                "rep_ir_identical": _ir(c.rep),
                "signature": _label_str(c.label),
                "members": [{"name": m,
                             "shape_cell": _shape_cell(rec.get(m, {})),
                             "status": (by_name.get(m) or {}).get("status")}
                            for m in sorted(c.members,
                                            key=lambda x: -int((rec.get(x) or {}).get("shape_distance", {}).get("total", 0)))],
            } for c in novel],
            "diagnose_no_lever": [r["name"] for r in rows
                                  if r["status"] == "diagnose"],
        }, indent=2))
        return

    typer.secho(f"\n  NEW-RULE FRONTIER -- {len(novel)} novel residue "
                f"famil{'y' if len(novel) == 1 else 'ies'} "
                "(no catalogue rule explains them)", bold=True)
    typer.echo("  Ranked by leverage (cluster size, then rep tractability), "
               "NOT byte count.  Solve the ● representative -> the rule "
               "generalises to its whole family.\n")
    for c in novel:
        ir = "  ✓IR(regalloc-residue)" if _ir(c.rep) else ""
        typer.secho(f"    ● {c.rep}  ({_shape_cell(rec.get(c.rep, {})) or '-'}) "
                    f"unlocks {c.size} fn{'s' if c.size != 1 else ''}{ir}",
                    fg="green", bold=True)
        typer.echo(f"        signature : {_label_str(c.label)[:60]}")
        mem = [m for m in sorted(c.members,
                                key=lambda x: -int((rec.get(x) or {}).get("shape_distance", {}).get("total", 0)))
               if m != c.rep]
        if mem:
            typer.echo("        family    : " + ", ".join(
                f"{m}({_shape_cell(rec.get(m, {})) or '-'})" for m in mem[:8])
                + (f" … +{len(mem) - 8}" if len(mem) > 8 else ""))
        typer.echo(f"        -> c2 residue-cluster -c {c.cid} ; "
                   f"c2 negative-corpus {c.rep} ; "
                   f"c2 decomp-verify -v -f {c.rep} + c2 shape-recon {c.rep}")
        if "reg swap" in _label_str(c.label).lower():
            typer.echo(f"           (Reg-swap family: c2 regtrace {c.rep} "
                       "names the swapped VALUE + the steerable lever "
                       "(PS<->RC seat diff))")
    typer.echo(f"\n  Also {n_diag} DIAGNOSE function(s) with no cached lever "
               "(the other new-rule edge): c2 worklist --status diagnose.")
    typer.echo("  A novel family solved -> add the rule to "
               "docs/watcom-codegen-patterns.md and bump the counter.")


def _stem(p: Optional[str]) -> str:
    """Basename without the trailing `.c` (so --file map == map.c)."""
    b = (p or "").split("/")[-1]
    return b[:-2] if b.endswith(".c") else b


def _build_rows(diff: list, tri: dict, triage_stale: bool) -> list[dict]:
    """Build the per-function worklist verdict rows from the diff corpus.
    Pure: depends only on the loaded diff/triage data and module-level
    classifiers.  Shared by the CLI and ``worklist_data``."""
    # Lazy-load the layered-verdict helpers + trace verification (no fatal
    # impact if the trace cache is missing -- the trace fields just stay None).
    try:
        from c2.commands.regalloc_verdict import (
            layered_verdict, trace_verification_note)
    except ImportError:
        layered_verdict = None
        trace_verification_note = None

    rows = []
    for f in diff:
        buckets = classify_all(f, tri.get(f["name"]))
        bucket = dominant_bucket(buckets)
        st, lever, tool = _ROUTE[bucket]
        others = [b for b in buckets if b != bucket
                  and b not in ("needs-diagnosis",)]
        # The row's VERDICT (status + dominant lever) is unreliable iff the
        # DOMINANT bucket is reachability-derived and triage is stale.  We
        # flag only the dominant (not secondary levers) -- a function whose
        # first fix is a solid shape lever has a trustworthy verdict even if
        # it also carries a downstream savings lever; over-flagging there
        # would drown the signal (most functions carry a savings secondary).
        row_stale = bool(triage_stale) and bucket in _TRIAGE_DERIVED
        sig = _shape_signal(f)
        shape = sig["kind"] if sig else "unknown"

        # NEW (2026-06-22): per-row trace verification tag.  The Score +
        # MergeIndex probes give EMPIRICAL ground truth about which compile-
        # phase decisions actually happened; we compare to the cascade's
        # slice attribution and surface MATCH / ENRICH / CONTRADICT here.
        # Costs ~0.3 ms / row (a cached load + a Counter); skipped silently
        # if the regalloc_verdict module or the trace cache is unavailable.
        # layered_verdict is computed ONCE and reused for both the trace tag
        # and the steerable class (it was previously called twice per row).
        trace_tag = None
        steerable_class = None
        if layered_verdict is not None:
            try:
                v = layered_verdict(f, name=f["name"], reconcile=True)
                steerable_class = v.get("steerable")
                if trace_verification_note is not None:
                    note = trace_verification_note(
                        f["name"], v.get("steerable", ""))
                    if note is None:
                        trace_tag = None
                    elif "contradict" in note.lower():
                        trace_tag = "contradict"
                    elif "confirms" in note.lower():
                        trace_tag = "confirms"
                    elif "enrich" in note.lower():
                        trace_tag = "enrich"
            except (KeyError, TypeError, AttributeError):
                pass

        # CAESAR2.EXE mapping hint (cheap no-compile lookup): does this
        # function have a Windows location, so `c2 win-verify` / the second
        # byte oracle is usable on it?
        try:
            from c2.win_bytes import win_hint as _win_hint
            _win = _win_hint(f["name"], _stem(f.get("file")))
        except Exception:
            _win = {"available": False, "win_va": None, "confidence": None}

        _sd = f.get("shape_distance") or {}
        rows.append({"name": f["name"], "file": f.get("file"),
                     "win": _win,
                     "bucket": bucket,
                     "status": st, "lever": lever, "tool": tool,
                     "other_levers": others, "triage_stale": row_stale,
                     "shape": shape,
                     "shape_cell": _shape_cell(f),
                     "fix_next": _sd.get("fix_next"),
                     "shape_total": _sd.get("total", 0),
                     "ir_divergent_lines": (sig or {}).get("divergent"),
                     # a shape-layer lever on an IR-identical fn is suspect
                     "shape_lever_noise": (shape == "regalloc"
                                           and bucket in _SHAPE_LAYER),
                     # NEW: GREEN/YELLOW/RED slice verification from trace
                     # contradict = CONTRADICT (trace shows the cascade's
                     #              slice attribution has zero activity);
                     # confirms   = CONFIRMS-NOT (e.g. find_enemy is NOT
                     #              MergeIndex, the cascade was wrong about
                     #              that specific lever);
                     # enrich     = ENRICH (slice is one component but the
                     #              trace shows another active layer);
                     # None       = match / not applicable / no trace.
                     "trace_verification": trace_tag,
                     # NEW: the layered_verdict steerable tag -- lets the
                     # renderer flag 'tie-reorder-pinned' (cascade-REACHABLE
                     # but Watcom IL canonicalisation pins the lever).
                     "steerable_class": steerable_class})
    return rows


def worklist_data(*, refresh: bool = True, file: Optional[str] = None) -> dict:
    """Structured-return core of the worklist (the library entry point used
    by the pi tools).  Returns ``{stale, triage_stale, notes, rows}`` for
    the whole diffing corpus, optionally restricted to one source file.
    The Typer ``worklist`` command renders this; it does not re-derive it."""
    diff, tri, notes, triage_stale = _load(refresh)
    if file:
        diff = [f for f in diff if _stem(f.get("file")) == _stem(file)]
    return {"stale": bool(notes), "triage_stale": bool(triage_stale),
            "notes": notes, "rows": _build_rows(diff, tri, triage_stale)}


def worklist(
    name: Annotated[
        Optional[str],
        typer.Argument(help="One function: print its dispatch verdict. "
                            "Omit for the corpus worklist."),
    ] = None,
    status: Annotated[
        Optional[str],
        typer.Option("--status", "-s",
                     help="Filter: workable | hard | diagnose | blocked | park"),
    ] = None,
    win: Annotated[
        Optional[str],
        typer.Option("--win",
                     help="Filter by CAESAR2.EXE mapping: 'mapped' = only "
                          "functions with a Windows location (c2 win-verify "
                          "usable); 'unmapped' = only those without."),
    ] = None,
    file: Annotated[
        Optional[str],
        typer.Option("--file",
                     help="Only functions in this source file -- EXACT "
                          "basename, .c optional (--file map.c == --file "
                          "map; never matches pm_map1.c)."),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Max rows per status (0 = all)."),
    ] = 12,
    refresh: Annotated[
        bool,
        typer.Option("--refresh/--no-refresh",
                     help="Auto-refresh a stale verify.json before output "
                          "(INCREMENTAL: re-verifies only the changed .c "
                          "files and merges them in -- ~3x faster than a "
                          "full pass).  --no-refresh = instant, may be "
                          "stale.  (Triage is never auto-rebuilt -- too "
                          "slow; refresh on demand.)"),
    ] = True,
    new_rule: Annotated[
        bool,
        typer.Option("--new-rule",
                     help="NEW-RULE FRONTIER picker: rank the NOVEL residue "
                          "families (no catalogue rule explains them) by "
                          "leverage (cluster size x rep tractability), not "
                          "byte count.  Solve a representative to mine a rule "
                          "that generalises to its whole family."),
    ] = False,
    as_json: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Fused GO/PARK/lever verdict per diffing function -- the session
    entrypoint.  Routes into the per-function loop; does not replace it.

    Auto-refreshes a stale verify.json before output -- INCREMENTALLY,
    re-verifying only the changed .c files and merging them into the cache
    (~3x faster than a full pass); pass --no-refresh for the instant,
    possibly-stale view.  The triage reachability axis is refreshed on
    demand only (it is a second verify pass), with a note when stale."""
    diff, tri, notes, triage_stale = _load(refresh)
    full_diff = diff
    if file:
        diff = [f for f in diff if _stem(f.get("file")) == _stem(file)]
    rows = _build_rows(diff, tri, triage_stale)
    if win in ("mapped", "unmapped"):
        want_win = win == "mapped"
        rows = [r for r in rows if bool(r.get("win", {}).get("available")) == want_win]
    if file and not rows:
        typer.secho(f"no diffing functions in '{file}' "
                    "(byte-exact, no such file, or cache stale)", fg="yellow")
        return

    for _n in notes:
        typer.secho(f"  ! {_n}", fg="yellow", err=True)

    if new_rule:
        _new_rule_frontier(full_diff, rows, as_json)
        return

    if name is not None:
        r = next((r for r in rows if r["name"] == name), None)
        if r is None:
            typer.secho(f"{name}: not in the diffing set (byte-exact, "
                        "unknown, or cache stale)", fg="yellow")
            raise typer.Exit(0 if any(f["name"] == name for f in diff) else 1)
        if as_json:
            typer.echo(json.dumps(r, indent=2))
            return
        typer.secho(f"\n  {r['name']}  [{r.get('shape_cell') or '-'}]  "
                    f"{r['lever']}", bold=True)
        if r.get("shape") == "regalloc":
            extra = (" -- and a SHAPE lever fired anyway, so that lever is "
                     "likely codegen noise (frame/strength-reduction), not a "
                     "real shape bug" if r.get("shape_lever_noise") else "")
            typer.secho("    ✓ binir IR matches PS: the SHAPE is already "
                        "right; the residue is regalloc/encoding -- work the "
                        f"regalloc hints or classify it, do NOT restructure{extra}.",
                        fg="green")
        elif r.get("shape") == "shape" and r.get("ir_divergent_lines"):
            typer.secho(f"    ◆ binir IR diverges at {r['ir_divergent_lines']} "
                        "source line(s): the recovered SHAPE is wrong/under-"
                        "recovered -- fix shape first (c2 shape-recon).",
                        fg="cyan")
        if r.get("triage_stale"):
            typer.secho("    ⚠ triage cache STALE -- this verdict leans on "
                        "the reg-swap reachability split (reorder/savings/"
                        "h2-tie/park); it may be wrong. Run `c2 triage "
                        "--rebuild` to trust it.", fg="yellow")
        # all levers (dominant + others), sequenced by fix-order layer.
        all_b = list(dict.fromkeys([r["bucket"]] + list(r.get("other_levers") or [])))
        all_b.sort(key=lambda b: _FIX_LAYER.get(b, (9, "?"))[0])
        if len(all_b) == 1:
            b = all_b[0]
            _s, _lev, _tool = _ROUTE[b]
            typer.secho(f"    status : {_s.upper()}  [{b}]",
                        fg=_STATUS_COLOR[_s])
            typer.echo(f"    lever  : {_lev}")
            typer.echo(f"    -> run : {_tool}")
        else:
            typer.secho(f"    {len(all_b)} levers -- FIX IN THIS ORDER "
                        "(shape/structural cascade into regalloc; re-verify "
                        "after each):", fg="bright_white", bold=True)
            for i, b in enumerate(all_b, 1):
                _s, _lev, _tool = _ROUTE[b]
                _layer = _FIX_LAYER.get(b, (9, "?"))[1]
                typer.secho(f"      {i}. [{_layer}] {_lev}",
                            fg=_STATUS_COLOR[_s])
                typer.echo(f"         -> {_tool}")
        return

    if as_json:
        typer.echo(json.dumps(
            {"stale": bool(notes), "triage_stale": bool(triage_stale),
             "notes": notes, "rows": rows}, indent=2))
        return

    from collections import Counter
    by_status = Counter(r["status"] for r in rows)
    scope = f"  (file = {file!r})" if file else ""
    typer.secho(f"\n  WORKLIST -- {len(rows)} diffing functions{scope}",
                bold=True)
    typer.echo("  ranked by shape-distance (fix-next layer: ir > width > "
              "spill > seat), not byte count.")
    typer.echo("  " + "  ".join(
        f"{s}={by_status.get(s, 0)}" for s in _STATUS_ORDER))

    want = [status] if status else _STATUS_ORDER
    for st in want:
        srows = sorted((r for r in rows if r["status"] == st),
                       key=_shape_sort_key)
        if not srows:
            continue
        typer.secho(f"\n  == {st.upper()} ({len(srows)} fns) ==",
                    fg=_STATUS_COLOR[st], bold=True)
        shown = srows if limit == 0 else srows[:limit]
        # group by bucket within the status for the lever/route header
        last_bucket = None
        for r in shown:
            if r["bucket"] != last_bucket:
                hdr = f"    [{r['bucket']}] {r['lever']}  ->  {r['tool']}"
                if triage_stale and r["bucket"] in _TRIAGE_DERIVED:
                    hdr += ("   ⚠ triage STALE -- verdict unreliable; "
                            "`c2 triage --rebuild`")
                typer.secho(hdr, fg=_STATUS_COLOR[st])
                last_bucket = r["bucket"]
            mark = (f"  (+{len(r['other_levers'])} lever)"
                    if r.get("other_levers") else "")
            if r.get("shape_lever_noise"):
                # shape lever fired but IR matches PS -> lever is noise
                mark += "  ✓IR⚠lever-noise"
            elif r.get("shape") == "regalloc":
                mark += "  ✓IR"
            # NEW: trace-derived empirical verification of the slice attr.
            tv = r.get("trace_verification")
            if tv == "contradict":
                mark += "  ⚠trace:CONTRADICT"      # slice has zero activity
            elif tv == "confirms":
                mark += "  ⚠trace:NOT-mergeindex"   # find_enemy-class
            elif tv == "enrich":
                mark += "  *trace:co-active"        # second slice also active
            # NEW (2026-06-22): cascade-REACHABLE but the named pair has
            # no source handle (compiler-temp on one side, or Watcom IL
            # canonicalisation pinned it).  The agent should NOT grind
            # reorder / permute on these -- the cascade verdict is a
            # model-level claim, not an actionable lever.
            if r.get("steerable_class") == "tie-reorder-pinned":
                mark += "  ⚠PINNED:cascade-no-handle"
            if (r.get("win") or {}).get("available"):
                mark += f"  🪟{r['win']['win_va']}"
            typer.echo(f"       {r['shape_cell'] or '-':>16}  {r['name']:34} "
                       f"{(r['file'] or '').split('/')[-1]}{mark}")
        if limit and len(srows) > limit:
            typer.echo(f"       … {len(srows) - limit} more "
                       f"(--limit 0 for all)")
    n_ir = sum(1 for r in rows if r.get("shape") == "regalloc")
    n_noise = sum(1 for r in rows if r.get("shape_lever_noise"))
    typer.echo("\n  workable first; PARK = do not grind; DIAGNOSE = run "
               "decomp-verify -v (live levers, rarely a new rule).  Then: "
               "c2 decomp-verify -v -f <fn> + c2 shape-recon.")
    typer.echo("  regalloc residue (not source shape)? c2 regtrace <fn> "
               "names the swapped value + lever (allocator ground truth).")
    typer.echo("  rover seat? decomp-verify -v's Rover hint has the fit "
               "windows + [lw census] candidates; c2 spell <fn> screens "
               "spelling probes without byte compiles.  BYTE-class seat? "
               "the lever is byte-RMW naming/inlining (t=g;t+=1;g=t <-> "
               "g+=1; byte compares don't advance -- they widen to dword).")
    typer.echo("  walk-order / chain-structure residue? the construct -> "
               "block-birth dictionary (watcom10.0a docs/block-birth-"
               "dictionary.md) names what adds/moves block births (labels "
               "add one; &&/||/nested-if identical; loop forms distinct); "
               "screen with c2 spell (birth + IL-birth verdicts).")
    if n_ir:
        typer.echo(f"  ✓IR ({n_ir}) = binir IR already matches PS: the WATCOM-"
                   "VISIBLE shape is right -- but binir is blind to Watcom-"
                   "canonicalized source defects.  Run c2 win-verify -v <fn> "
                   "FIRST: the MSVC /Od oracle exposes invented temps, "
                   "write-only locals, x_max-style precomputes and guard "
                   "nesting the byte oracle collapses; fixing those usually "
                   "collapses the seat/spill residue for free (proven 5x on "
                   "the map.c elastic family, 2026-07-04).  Only a win-clean "
                   "or win-classified fn is a true regalloc residue -- then "
                   "work the regalloc hints, do NOT restructure.")
    if n_noise:
        typer.echo(f"  ✓IR⚠lever-noise ({n_noise}) = a SHAPE lever fired on an "
                   "IR-identical fn -- the lever (often const = frame/strength-"
                   "reduction noise) is suspect; treat as regalloc residue.")
