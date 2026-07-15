"""regalloc-verdict -- the layered residue work-order classifier.

A diffing function's byte residue is a STACK of layers, and they have a
causal order (each layer is an input to the next):

    L1 substrate   wrong constants / types / widths      (edits the IR)
    L2 shape/IR    the CG conflict SET diverges from PS   (edits the IR)
    L3 pressure    callee-save COUNT differs (the frame)  (alloc output)
    L4 identity    same IR + count, different physical reg(alloc output)
    L5 residue     IR-identical, no nameable lever        (classified floor)

The frame (prologue push set) and the register identity are OUTPUTS of the
allocator, downstream of the IR -- so the work order is IR-first.  A frame
mismatch is the loudest *signal* that allocation diverged, not the first
fixable thing: you cannot steer the prologue until the IR that feeds it
matches PS.  (Corpus fact 2026-06-22: every callee-save-COUNT divergence
also carries an earlier shape/const divergence -- the pressure layer is
gated behind shape.)

This command reports, per diffing function, the EARLIEST divergent layer
== the next action, plus the named lever and whether it is steerable
*today* (a decl-swap on two named locals) or needs a deeper build
(temp pin / pressure savings).  It runs fully OFFLINE from the cached
verify record (diff rows + every hint) and the cached allocator trace --
no container.

Pairs with: const-audit (L1), shape-recon/binir (L2), pragma-hints/
frame-hints (L3), regtrace --explain / decl-swap (L4).
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

import typer

VERIFY_CACHE = Path(".c2-cache/verify.json")
TRACE_CACHE = Path(".c2-cache/build/regtrace.json")
TRIAGE_CACHE = Path(".c2-cache/triage.json")


@functools.lru_cache(maxsize=8)
def _parse_json(path_str: str, _mtime: float) -> dict:
    """Parse a cache file ONCE per (path, mtime) and memoise the result.
    The triage/trace/verify caches are read per-function all over this
    module; the trace cache alone is ~150 MB, so re-parsing it on every
    call made worklist (~131 fns x several calls each) parse hundreds of
    GB.  Keyed on mtime so an updated cache re-parses."""
    return json.loads(Path(path_str).read_text())


def _load_cache(path: Path) -> dict:
    """Memoised parse of a cache file (mtime-invalidated).  Raises the same
    OSError/ValueError the inline ``json.loads(read_text())`` did, so callers'
    try/except still works."""
    return _parse_json(str(path), path.stat().st_mtime)


def cascade_from_cache(name: str) -> tuple[str, str] | None:
    """The EXACT offline inverse verdict for ``name`` from the triage cache
    (cascade_hints over the real allocator trace).  Returns (verdict, detail)
    where verdict is one of REACHABLE / UNREACHABLE / SAVINGS / INCONCLUSIVE /
    other, or None when the cache has nothing.  This is the GROUND-TRUTH
    gap-pointer that the shallow hints must defer to (it actually ran
    inverse_search; the decl_order_hint is a heuristic that can oversell).
    """
    if not TRIAGE_CACHE.exists():
        return None
    try:
        data = _load_cache(TRIAGE_CACHE)
    except (OSError, json.JSONDecodeError):
        return None
    t = data.get(name)
    if not t:
        return None
    casc = t.get("cascade") or []
    txt = " ".join(casc)
    # the most actionable line (REACHABLE names the birth-order delta)
    detail = next((ln for ln in casc if "REACHABLE by TIE-REORDER" in ln),
                  casc[0] if casc else "")
    # Priority: ACTIONABLE verdicts first (REACHABLE/SAVINGS -- each points at a
    # concrete edit), then OUT-OF-SLICE routing (UNREACHABLE), then STOP-SIGNALS
    # (ROVER says 'this pair is not an allocator binding -- do not chase it via
    # decl/use-order', but only useful when no actionable verdict exists for
    # ANOTHER pair in the same function), then INCONCLUSIVE.  A function with
    # both a SAVINGS pair and a ROVER pair (e.g. get_city_mood) must surface
    # the SAVINGS one -- ROVER overriding it would silence a real edit.
    if "REACHABLE by TIE-REORDER" in txt:
        return ("REACHABLE", detail)
    # SAVINGS: must match the VERDICT phrase 'needs a SAVINGS change', not the
    # bare word -- UNREACHABLE lines mention 'EQUAL-SAVINGS (H2) tie' as flavor
    # and that would mis-fire (caught on get_random_start_points_from_dirc,
    # restore_picture_part, strip_spaces -- pure UNREACHABLE cases that the
    # bare match wrongly promoted to SAVINGS).
    if "needs a SAVINGS change" in txt:
        return ("SAVINGS", next((ln for ln in casc
                                 if "needs a SAVINGS change" in ln), detail))
    if "UNREACHABLE" in txt:
        return ("UNREACHABLE", next((ln for ln in casc
                                     if "UNREACHABLE" in ln), detail))
    if ("rover/scratch seat" in txt
            or "no alloc row holds one side" in txt):
        rline = next((ln for ln in casc
                      if "rover/scratch seat" in ln
                      or "no alloc row holds one side" in ln), detail)
        return ("ROVER", rline)
    if "INCONCLUSIVE" in txt:
        return ("INCONCLUSIVE", detail)
    if casc:
        return ("other", detail)
    return None


def _regalloc_line(name: str) -> str | None:
    """The triage `Regalloc:` slice-attribution line for ``name`` (names which
    compiler slice owns a non-order-reachable divergence)."""
    if not TRIAGE_CACHE.exists():
        return None
    try:
        data = _load_cache(TRIAGE_CACHE)
    except (OSError, json.JSONDecodeError):
        return None
    t = data.get(name) or {}
    rg = t.get("regalloc") or []
    return rg[0] if rg else None

# Layer ids, names, and the one-line "what to do" for each verdict bucket.
_LAYER_NAME = {
    1: "substrate",
    2: "shape-IR",
    3: "pressure",
    4: "identity",
    5: "residue",
}


def _is_named(tok) -> bool:
    """A real source variable name (not an anonymous temp tag)."""
    if not tok:
        return False
    s = str(tok)
    return not (s.startswith("(") or s.startswith("@") or
                (len(s) > 1 and s[0] == "t" and s[1:].isalnum()
                 and not s.isalpha()))


# Map a triage `Regalloc:` slice line to (slice-tag, inverse-lever).  PS.EXE =
# f(S*) with f = Watcom 10.0a (forward-exact), so a source preimage ALWAYS
# exists -- a register divergence the order-permutation inverse cannot reach is
# simply OWNED BY A DIFFERENT SLICE of the compiler (optimize / treegen /
# capacity / rover), each with its own inverse lever.  There is no 'unreachable'.
_SLICE_MAP = [
    # callee-save (EBX/ESI/EDI/EBP) equal-savings tie: the lever is reverse-
    # LAST-USE, not decl/first-assign (DoubleRegs priority order).
    ("callee-save swap", "regalloc:callee-save-tie",
     "reverse-LAST-USE order of the two callee-saved values: make the value "
     "that should win the higher-priority reg (per DoubleRegs order "
     "EAX,EDX,EBX,ECX,...) have the EARLIER last use (move its final read up, "
     "or push the other's final read down).  decl/first-assign order is NOT "
     "the lever here."),
    ("loop hoist", "optimize:loop-hoist",
     "match the loop's aliasing call/pointer-store so Watcom reloads (not "
     "hoists) the global, as PS does"),
    ("reload", "optimize:loop-hoist",
     "match the loop's aliasing call/pointer-store (PS reloads the global)"),
    ("capacity", "regalloc:capacity",
     "cut the simultaneously-live count (drop the lowest-savings value / "
     "shorten a live range) so PS's value set fits in registers"),
    ("spill", "regalloc:capacity",
     "reduce register pressure so the spilled value stays enregistered"),
    ("Rule 109", "treegen:index-fusion",
     "reshape the index expression so the scaled-index load stays in a "
     "scratch reg (PS) instead of fusing into the result"),
    ("fused into", "treegen:index-fusion",
     "reshape the index expression so the load stays scratch (PS shape)"),
    ("Rule 28a", "treegen:use-order",
     "commute the deciding use (Rule 28a) -- changes which operand is op0 and "
     "thus CountRegMoves; the order-permutation inverse misses this because "
     "it is a TREEGEN effect, not a queue reorder"),
    ("tie-break", "treegen:use-order",
     "commute/reorder the deciding USE (Rule 28a) -- a treegen effect outside "
     "the queue-permutation slice"),
    ("rover", "rover:scratch-seat",
     "the divergence is FindRegister scratch seating (const store / call arg), "
     "not allocation -- match PS's store/arg order"),
]


def _slice_of(detail: str, regalloc_line: str | None) -> tuple[str, str]:
    """Name the compiler SLICE that owns a non-order-reachable divergence, and
    its inverse lever, from the triage Regalloc: line (falls back to the
    cascade detail).  Never returns 'unreachable'."""
    hay = ((regalloc_line or "") + " " + (detail or ""))
    for needle, tag, lever in _SLICE_MAP:
        if needle.lower() in hay.lower():
            return tag, lever
    return ("compiler-slice:unclassified",
            "the order-permutation inverse cannot reach this -- the divergence "
            "is in another compiler slice (optimize/treegen/rover); identify it "
            "with c2 regtrace --explain and invert THAT slice (a preimage "
            "exists: PS.EXE = Watcom-10.0a(source))")


import re as _re
_CASC_PAIR_RE = _re.compile(
    r"allocate\s+`([^`]+)`\s+\([^)]*\)\s+after\s+`([^`]+)`")
_TEMP_RE = _re.compile(r"^t\.[0-9a-fA-F]+$")


def _cascade_pair_handle(detail: str) -> tuple[str, str] | None:
    """Inspect a cascade REACHABLE detail line and classify the named
    competing pair into one of four handle categories:

      'named-strong'      both members are >=2-char identifiers; LIKELY
                          has a source handle but verify with decl-swap
                          before grinding (e.g. city_test_for_road has
                          `x`+`y` and the cascade names them as if movable
                          but decl-swap proves no improvement -- IL
                          canonicalisation defeats it).
      'single-letter'     one or both are single-letter names.  Often a
                          C local but also commonly a Watcom IL pseudo-
                          variable for an expression sub-part.  LOW
                          confidence.
      'mixed-named-temp'  one named, one compiler temp (`t.<hex>`).  NO
                          source handle for the temp member; the cascade's
                          REACHABLE is a model-only claim.
      'temp-pair'         both are compiler temps.  NO source handle.

    Returns (handle_class, label) or None if the pattern didn't match.

    Empirical evidence (2026-06-22):
      * control_buttons (sz + t.b354 = mixed-named-temp): decl-swap reports
        'no source handle', permute 0/63, structural rewrites all regress.
      * city_test_for_road (x + y = single-letter): decl-swap 0/6 variants
        improve.  Even "strong-looking" named pairs need verification.
    """
    if not detail:
        return None
    m = _CASC_PAIR_RE.search(detail)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    a_temp = bool(_TEMP_RE.match(a))
    b_temp = bool(_TEMP_RE.match(b))
    if a_temp and b_temp:
        return ("temp-pair", "both compiler temps")
    if a_temp or b_temp:
        return ("mixed-named-temp",
                f"named `{a if b_temp else b}` + temp `{b if b_temp else a}`")
    if len(a) <= 1 or len(b) <= 1:
        return ("single-letter", f"`{a}` + `{b}`")
    return ("named-strong", f"`{a}` + `{b}`")


def _reconcile_identity(v: dict, cascade: tuple[str, str] | None,
                        regalloc_line: str | None = None) -> dict:
    """For the IDENTITY layer, DEFER the steerability claim to the exact inverse
    (cascade) instead of the shallow decl_order_hint -- which oversells.

    Crucially: a cascade 'UNREACHABLE' is NOT a floor.  The order-permutation
    inverse covers only ONE slice of the compiler; an out-of-slice divergence
    is NAMED by its owning slice (optimize/treegen/capacity/rover) and that
    slice's inverse lever -- because PS.EXE = f(source) with f known, so a
    source preimage always exists."""
    if v["layer"] != 4 or cascade is None:
        if v["layer"] == 4 and v["steerable"] in ("named-tie", "temp-tie"):
            v = dict(v, detail=v["detail"] + "  [UNVERIFIED: run c2 triage]")
        return v
    verdict, detail = cascade
    detail = detail.replace("Cascade: ", "").strip()
    if verdict == "ROVER":
        # cascade proves the diverging registers are not allocator bindings --
        # they are FindRegister scratch seats (const stores, call-arg loads).
        # The shallow decl_order/named-tie hint is WRONG for this pair; the
        # lever lives in the rover slice (match PS's store/arg order).
        return dict(v, steerable="rover:scratch-seat",
                    lever="NOT an allocator binding -- FindRegister scratch seat "
                          "(const store / call-arg).  Match PS's store/arg "
                          "order; decl/use-order levers do not apply.",
                    detail=detail)
    if verdict == "REACHABLE":
        # NEW: classify the cascade's competing pair by source-handle
        # category so the agent reads honest reachability, not just the
        # cascade's model-level claim.
        handle = _cascade_pair_handle(detail)
        cls = handle[0] if handle else None
        if cls in ("temp-pair", "mixed-named-temp"):
            return dict(v, steerable="tie-reorder-pinned",
                        lever=(f"cascade-REACHABLE but pair has NO source "
                               f"handle ({handle[1]}): Watcom's IL "
                               "canonicalises commutative-op operand order "
                               "before regalloc, so source-text reorders "
                               "cannot move it.  decl-swap / permute / "
                               "operand-commute will not close this."),
                        detail=detail)
        if cls == "single-letter":
            return dict(v, steerable="tie-reorder",
                        lever=(f"birth-order reorder (cascade-VERIFIED on "
                               f"single-letter pair {handle[1]}: "
                               "LOW confidence the lever is mechanizable -- "
                               "SCREEN with `c2 savings <fn> --flip VAR=REG` "
                               "before hand-editing.  Pair names that look "
                               "like C locals can also be Watcom IL pseudo-"
                               "names for expression sub-parts; an honest "
                               "flip-search negative means the lever is "
                               "pinned)."),
                        detail=detail)
        # named-strong (>=2-char idents on both sides) -- HIGH confidence
        # but still verify with decl-swap on first attempt (the Watcom IL
        # canonicalisation gotcha applies to ALL cascade REACHABLE pairs).
        return dict(v, steerable="tie-reorder",
                    lever="birth-order reorder (cascade-VERIFIED)",
                    detail=detail)
    if verdict == "UNREACHABLE":
        tag, lever = _slice_of(detail, regalloc_line)
        return dict(v, steerable=tag,
                    lever=f"out of the regalloc-tie slice -> {lever}",
                    detail=detail)
    if verdict == "SAVINGS":
        return dict(v, steerable="treegen:savings",
                    lever="change weighted use-count (a treegen/source-shape "
                          "slice, not the queue order)",
                    detail=detail)
    if verdict == "INCONCLUSIVE":
        return dict(v, detail=v["detail"]
                    + "  [cascade INCONCLUSIVE: search budget hit -- raise it; "
                    "never read as unreachable]")
    return v


def present_layers(vrec: dict, name: str | None = None) -> list[str]:
    """Every divergence signal currently present in the record -- the full LAYER
    STACK, not just the earliest.  Empirical fact (corpus 2026-06-22): only ~4%
    of L1/L2 diffing functions are single-layer; the median is 3 layers stacked.
    The work-order's earliest-layer verdict names the NEXT action, but byte-
    exact closure requires peeling each layer in turn."""
    out: list[str] = []
    if (vrec.get("const_audit") or {}).get("n_div", 0) > 0:
        out.append("L1:const")
    bi = vrec.get("binir_shape_hint") or {}
    if bi.get("verdict") == "shape_divergence":
        d = bi.get("lines_divergent")
        c = bi.get("lines_compared")
        out.append(f"L2:shape({d}/{c})")
    p = (vrec.get("pragma_hint") or {}).get("category")
    if p in ("ps_extra_callee_save", "rc_extra_callee_save"):
        out.append("L3:pressure")
    if p == "callee_save_swap":
        out.append("L4:prologue-swap")
    if vrec.get("slot_swap"):
        out.append("L4:slot")
    if vrec.get("byte_seat"):
        out.append("L4:byte-seat")
    if (vrec.get("decl_order_hint") or {}).get("layer3_reg_swap"):
        out.append("L4:reg-swap")
    # rule_hints catch register swaps that did not produce a decl_order_hint
    # (e.g. identity-unclassified rovers / Rule 109 fusion / tail-merge
    # collateral) -- without these, restore_picture_part/find_enemy/install_
    # mouse/show_battle_outtro_screen showed an EMPTY stack (a false 'single-
    # layer' tag).  These additions catch the 4 missing signals.
    rh = vrec.get("rule_hints") or {}
    if rh.get("Reg swap", 0) > 0 and "L4:reg-swap" not in out:
        out.append("L4:reg-swap")
    if rh.get("Byte-reg swap", 0) > 0 and "L4:byte-seat" not in out:
        out.append("L4:byte-reg-swap")
    if rh.get("Rule 109", 0) > 0:
        out.append("L4:index-fusion")
    if vrec.get("tail_merge"):
        out.append("L4:tail-merge")
    if name and TRIAGE_CACHE.exists():
        try:
            t = _load_cache(TRIAGE_CACHE).get(name) or {}
            rg = " ".join(t.get("regalloc") or []).lower()
        except (OSError, json.JSONDecodeError):
            rg = ""
        if "loop hoist" in rg or "reload" in rg:
            out.append("L4:loop-hoist")
        if "capacity" in rg or "spill" in rg:
            out.append("L4:capacity")
        if "callee-save swap" in rg:
            out.append("L4:callee-save-tie")
        if "rover" in rg or "scratch" in rg or "riscify" in rg:
            out.append("L4:rover-scratch")
    return out


def layered_verdict(vrec: dict, name: str | None = None,
                    reconcile: bool = False) -> dict:
    """Pure, offline: classify a verify record into its earliest divergent
    layer + the named lever.  Returns a dict with keys: layer, name, lever,
    detail, steerable, bytes, stack.

    The `stack` field lists EVERY divergence signal present -- the median
    diffing function has 3 layers stacked, only ~4% are single-layer.  The
    earliest layer is the NEXT action; byte-exact closure peels the rest.

    When ``reconcile`` and ``name`` are given, the IDENTITY-layer steerability
    is reconciled against the EXACT inverse verdict (cascade) so the shallow
    decl_order_hint can never oversell a 'steerable' claim the real inverse
    search has already proven UNREACHABLE."""
    bytes_ = vrec.get("diff_byte_count", 0)
    binir = vrec.get("binir_shape_hint") or {}
    verdict = binir.get("verdict")
    pragma = vrec.get("pragma_hint") or {}
    pcat = pragma.get("category")
    ca = vrec.get("const_audit") or {}
    n_div = ca.get("n_div", 0)
    slot = vrec.get("slot_swap")
    decl = vrec.get("decl_order_hint") or {}
    byte_seat = vrec.get("byte_seat")
    rh = vrec.get("rule_hints") or {}

    _cascade = (cascade_from_cache(name) if (reconcile and name) else None)
    _regline = (_regalloc_line(name) if (reconcile and name) else None)

    _stack = present_layers(vrec, name)

    def mk(layer, name_, lever, detail, steerable):
        v = dict(layer=layer, name=name_, lever=lever, detail=detail,
                 steerable=steerable, bytes=bytes_, stack=_stack)
        return _reconcile_identity(v, _cascade, _regline)

    # ---- L1 substrate: wrong constants/types (regalloc-invariant; fix FIRST)
    if n_div > 0:
        b = ca.get("boundary_offby1")
        return mk(1, "substrate-const", "const-audit",
                  f"{n_div} divergent constant(s)"
                  + (" (off-by-one boundary)" if b else ""), "shape")

    # ---- L2 shape/IR: the conflict SET diverges -> match before regalloc ----
    if verdict == "shape_divergence":
        lever = "binir / shape-152 / decl-order"
        detail = (f"{binir.get('lines_divergent')}/"
                  f"{binir.get('lines_compared')} IR lines diverge")
        # An extra callee-save push means some (or all) of the "IR-line"
        # divergence is REALISATION -- a const-hoist / extra enregistration
        # that binir sees as changed BYTES, not a source-shape defect.  Do
        # NOT chase shape-152/decl-order blind; read the register census.
        if pcat in ("ps_extra_callee_save", "rc_extra_callee_save"):
            lever = "c2 reg-delta (realisation?) then binir / shape-152"
            detail += (" -- CAVEAT: extra callee-save push present, so a "
                       "const-hoist / seat-swap may be the real cause (not "
                       "shape): run `c2 reg-delta <fn>` FIRST")
        return mk(2, "shape-IR", lever, detail, "shape")
    if verdict != "encoding_noise":
        return mk(2, "shape-IR", "binir / shape-recon",
                  f"binir verdict={verdict!r}", "shape")

    # ===== binir IDENTICAL from here: pure allocation / encoding residue =====

    # ---- L3 pressure: callee-save COUNT differs (the frame) ----
    if pcat in ("ps_extra_callee_save", "rc_extra_callee_save"):
        return mk(3, "pressure-callee-save", "savings / live-range",
                  pragma.get("summary") or pcat, "pressure")
    if pcat == "structural_divergence":
        return mk(3, "frame-structural", "pragma / frame-hints",
                  pragma.get("summary") or pcat, "frame")

    # ---- L4 identity: same IR & count, different physical register ----
    if slot:
        return mk(4, "identity-slot", "Rule 107 spill-slot swap",
                  f"slots {slot.get('slots')} vars {slot.get('swapped_vars')}",
                  "slot")
    # byte-register class dominates -> the byte-seat lever, NOT the dword
    # decl-swap (a dword candidate_pair here is a secondary/downstream hint).
    if byte_seat and rh.get("Byte-reg swap", 0) >= rh.get("Reg swap", 0):
        return mk(4, "identity-byte-seat", "byte-register seat",
                  f"byte-seat case {byte_seat.get('case')} "
                  f"(Byte-reg swap x{rh.get('Byte-reg swap', 0)})", "byte")
    # named-tie: two PINNED named locals -> decl-swap STEERABLE today
    pair = decl.get("candidate_pair")
    if decl.get("layer3_reg_swap") and pair and len(pair) == 2 \
            and all(_is_named(p) for p in pair):
        return mk(4, "identity-named-tie", "Rule 115 decl-swap / Rule 28a",
                  f"swap {decl.get('swap_regs')} pair={pair} "
                  f"rows={decl.get('swap_row_count')}", "named-tie")
    # layer-3 reg swap but no named pair -> the rival is a temp
    if decl.get("layer3_reg_swap"):
        return mk(4, "identity-temp-tie", "pin-temp (build #2)",
                  f"swap {decl.get('swap_regs')} "
                  f"rows={decl.get('swap_row_count')}; rival is a temp",
                  "temp-tie")
    if byte_seat:
        return mk(4, "identity-byte-seat", "byte-register seat",
                  f"byte-seat case {byte_seat.get('case')}", "byte")
    if pcat == "callee_save_swap":
        return mk(4, "identity-prologue", "birth-order tie (prologue reg)",
                  pragma.get("summary") or pcat, "temp-tie")
    if rh.get("Reg swap") or rh.get("Byte-reg swap"):
        return mk(4, "identity-unclassified", "regtrace --explain",
                  f"Reg swap x{rh.get('Reg swap', 0)} "
                  f"Byte-reg swap x{rh.get('Byte-reg swap', 0)}", "temp-tie")

    # ---- L5 residue: no SHALLOW signal -- but the triage may still name the
    # slice (callee-save swap, capacity/spill, hoist, treegen, ...).  PS.EXE =
    # f(source) so there is no true floor: defer to the triage regalloc line
    # before claiming residue.
    final = mk(5, "residue-floor", "certify (regtrace --explain)",
               "IR-identical, no shallow lever", "floor")
    if reconcile and name and final["steerable"] == "floor" and _regline:
        tag, lever = _slice_of("", _regline)
        if tag != "compiler-slice:unclassified":
            return dict(final, layer=4, name="identity-via-triage",
                        steerable=tag,
                        lever=f"triage-named slice -> {lever}",
                        detail=_regline.replace("Regalloc: ", "")
                        .strip()[:240])
    return final


# --------------------------------------------------------------------------
# Trace-backed deep detail for the allocation layers (builds #2 and #3).
# --------------------------------------------------------------------------

def _load_trace_func(name: str) -> dict | None:
    if not TRACE_CACHE.exists():
        return None
    try:
        td = _load_cache(TRACE_CACHE)
    except (OSError, json.JSONDecodeError):
        return None
    bf = td.get("by_func", {})
    return bf.get(name) or bf.get(name.rstrip("_"))


def _dword_allocs(tf: dict) -> list[dict]:
    return [a for a in (tf.get("alloc") or [])
            if a.get("regclass_name") == "dword"]


def temp_tie_detail(name: str, vrec: dict) -> list[str]:
    """Build #2 seed: for an identity-temp-tie, characterise the divergence and
    name the SEED conflict (the highest-savings value on each side of the
    register pair).  Distinguishes a LOCALISED tie (few holders -> a pin/reorder
    candidate) from a WHOLE-FUNCTION 2-cycle (the same register pair swapped
    across many live ranges -> the lever is to flip the seed's birth order and
    let the cascade follow; that is inverse-search territory, build #4).
    Always COMPILE-VERIFY (graph-changing)."""
    decl = vrec.get("decl_order_hint") or {}
    regs = [r.upper() for r in (decl.get("swap_regs") or [])]
    if len(regs) != 2:
        return ["  (swap_regs not a clean pair -- see "
                f"`c2 regtrace {name} --explain`)"]
    tf = _load_trace_func(name)
    if not tf:
        return ["  (no cached trace -- run `c2 regtrace %s`)" % name]
    al = _dword_allocs(tf)
    ps_reg, rc_reg = regs  # swap_regs = [ps, rc] convention
    rc_holders = [a for a in al if a.get("reg_name") == rc_reg]
    ps_holders = [a for a in al if a.get("reg_name") == ps_reg]
    out = [f"  divergence: PS uses {ps_reg} where RC uses {rc_reg}"]

    def _seed(holders):
        return max(holders, key=lambda a: a.get("savings", 0)) if holders \
            else None
    n_total = len(rc_holders) + len(ps_holders)
    global_cycle = n_total > 4 and rc_holders and ps_holders
    kind = "WHOLE-FUNCTION 2-cycle" if global_cycle else "localised tie"
    out.append(f"  shape: {kind} "
               f"({len(rc_holders)} {rc_reg} + {len(ps_holders)} {ps_reg} "
               f"live ranges)")
    for label, reg, a in (("RC", rc_reg, _seed(rc_holders)),
                          ("PS", ps_reg, _seed(ps_holders))):
        if a:
            tag = a.get("var") or "(temp)"
            dl = a.get("defline") or 0
            out.append(f"    seed {label} {reg}: {tag} "
                       f"savings={a.get('savings')}"
                       + (f" L{dl}" if dl else ""))
    seed_rc, seed_ps = _seed(rc_holders), _seed(ps_holders)
    tie = (seed_rc and seed_ps
           and seed_rc.get("savings") == seed_ps.get("savings"))
    if global_cycle:
        out.append(
            "  LEVER: this is a register-IDENTITY permutation, not a single "
            "tie -- flip the SEED conflict's birth order (move its producing "
            "statement / commute its operands) and the cascade follows. "
            + ("seeds are equal-savings => reachable by a pure birth reorder "
               "(Rule 28a/115). " if tie else
               "seeds differ in savings => needs a savings/live-range change "
               "(not pure reorder). ")
            + "Drive with inverse-search (build #4) + COMPILE-VERIFY.")
    else:
        a = next((x for x in (seed_rc, seed_ps)
                  if x and not x.get("var") and x.get("defline")), None)
        if a:
            out.append(
                f"  LEVER (build #2): pin the temp at L{a['defline']} into a "
                "named local, then swap its decl line against its rival "
                "[Rule 115].  Pinning changes the conflict graph -> "
                "COMPILE-VERIFY.")
        else:
            out.append("  both seeds are named -> swap their decl lines (Rule 115); "
                       "screen with `c2 savings <fn> --flip` first.")
    return out


def score_event_summary(name: str) -> list[str]:
    """Pull the cached Score (sb/sbi/sbs) event stream for ``name`` and
    summarise the *coalesce decisions* the redundant-load eliminator made.
    For the L4:optimize:loop-hoist class this is the ground-truth read of
    'where in the body did Watcom decide to coalesce vs reload'.

    The stream is the RC-side trace; the PS-side ground truth is in the
    PS asm.  Pair the two with `c2 disasm <name>` (PS) + this summary (RC)
    to name the specific call/store whose presence diverges.
    """
    tf = _load_trace_func(name)
    if not tf:
        return ["  (no cached trace -- run `c2 regtrace %s`)" % name]
    ev = tf.get("score_events") or []
    if not ev:
        return ["  Score: no events (the function has no PostOptimize Score "
                "activity -- not a loop-hoist candidate, or trace was "
                "generated before the probe sweep landed)"]
    from collections import Counter
    by_tag = Counter(e["tag"] for e in ev)
    out = [f"  Score events: {by_tag.get('sb',0)} coalesce(sb), "
           f"{by_tag.get('sbi',0)} call-invalidate(sbi), "
           f"{by_tag.get('sbs',0)} store-invalidate(sbs)"]
    # show the inflection point: per-ins, the LAST event that touched it
    # tells whether RC's scoreboard kept it coalesced or invalidated it.
    if by_tag.get("sbi", 0) > 0:
        out.append("  CALL invalidates (= RC's source has a CALL here that "
                   "PS's may not):")
        for e in [x for x in ev if x["tag"] == "sbi"][:6]:
            out.append(f"    sbi ins=0x{e['ins']}  (seq={e['seq']})")
        if by_tag["sbi"] > 6:
            out.append(f"    … (+{by_tag['sbi'] - 6} more)")
    if by_tag.get("sbs", 0) > 0:
        out.append("  STORE invalidates (= RC has an aliasing store here):")
        for e in [x for x in ev if x["tag"] == "sbs"][:4]:
            opc = e.get("opcode", 0)
            out.append(f"    sbs ins=0x{e['ins']} opcode=0x{opc:x}  "
                       f"(seq={e['seq']})")
    return out


def mergeindex_event_summary(name: str) -> list[str]:
    """Pull the cached MergeIndex (mic/mip/mi) event stream for ``name``
    and summarise the *fusion decisions* the index-fusion pass made.  For
    the L4:treegen:index-fusion class this names which ins's were tested
    and which actually fused.

    Per-clause rejection records (`mir1..6`) are always emitted; the
    dead-code SACRIFICE in patch_trace.py absorbs their cave cost.
    Note: most predicate rejections happen at the opcode-ineligible
    bail at the TOP of FUN_0006c5b2 (`MergeIndex_bail_opcode_ineligible`,
    not instrumented as it is a trivial filter); the inner-loop clauses
    that DO get tagged (mir1..6) are the interesting fusion-blocking
    decisions.  Schema: mip - mi - sum(mir1..6) = opcode-ineligible bail.
    """
    tf = _load_trace_func(name)
    if not tf:
        return ["  (no cached trace -- run `c2 regtrace %s`)" % name]
    ev = tf.get("mergeindex_events") or []
    if not ev:
        return ["  MergeIndex: no events (no index-fusion candidates in "
                "this function, or trace pre-probe-sweep)"]
    from collections import Counter
    by_tag = Counter(e["tag"] for e in ev)
    cand = by_tag.get("mic", 0)
    pred = by_tag.get("mip", 0)
    fused = by_tag.get("mi", 0)
    out = [f"  MergeIndex events: {cand} candidate-test, {pred} predicate-"
           f"test, {fused} fusion-commit",
           f"  candidate → predicate rejection: {cand - pred}/{cand}",
           f"  predicate → fusion rejection:   {pred - fused}/{pred}"]
    # show the actually-fused ins's -- these are the ones RC FUSED that
    # might be the divergence target if PS didn't
    if fused:
        out.append("  FUSED ins's (RC fused these; if PS didn't, the "
                   "divergence is here):")
        for e in [x for x in ev if x["tag"] == "mi"][:6]:
            opc = e.get("opcode", 0)
            out.append(f"    mi ins=0x{e['ins']} opcode=0x{opc:x}  "
                       f"(seq={e['seq']})")
        if fused > 6:
            out.append(f"    … (+{fused - 6} more)")
    # per-clause if mir records present
    mir_tags = [t for t in by_tag if t.startswith("mir")]
    if mir_tags:
        out.append("  Per-clause rejection counts (inner-loop clauses):")
        clause_names = {"mir1": "CLASS-1 inner", "mir2": "NON-INDEX inner",
                        "mir3": "SCALE-OVERFLOW", "mir4": "MODE-MISMATCH",
                        "mir5": "CLASS-2", "mir6": "NON-INDEX-1"}
        for t in sorted(mir_tags):
            out.append(f"    {t} ({clause_names.get(t, '?')}): "
                       f"{by_tag[t]}")
    return out


def trace_activity_summary(name: str) -> dict | None:
    """One-line summary of Score+MergeIndex activity from the cached trace.
    Used by the classifier to verify a slice attribution against the actual
    compile-phase decisions.  Returns None when no trace is cached.

    Counts:
      score_active   = sbi + sbs (CALL or store invalidates -- 'this function
                       has lots of scoreboard-flushing events')
      mi_active      = mi  (actual MergeIndex fusions)
      mi_attempts    = mip (predicate attempts)
      mir_inner      = sum(mir1..6) (per-clause inner-loop rejections)
    """
    tf = _load_trace_func(name)
    if not tf:
        return None
    from collections import Counter
    sc = Counter(e["tag"] for e in (tf.get("score_events") or []))
    mi = Counter(e["tag"] for e in (tf.get("mergeindex_events") or []))
    return {
        "score_active": sc.get("sbi", 0) + sc.get("sbs", 0),
        "sb": sc.get("sb", 0),
        "sbi": sc.get("sbi", 0),
        "sbs": sc.get("sbs", 0),
        "mi_active": mi.get("mi", 0),
        "mi_attempts": mi.get("mip", 0),
        "mir_inner": sum(v for k, v in mi.items() if k.startswith("mir")),
    }


def trace_verification_note(name: str, slice_tag: str) -> str | None:
    """Compare the slice attribution against the actual trace activity and
    return a short verification/divergence note (or None when no issue).

    The new instrumentation gives us EMPIRICAL ground truth about which
    compile-phase activity actually happened.  Three possible findings:

      ✓ MATCH       -- trace activity is consistent with the slice claim
      ! ENRICH      -- slice is correct but the trace reveals a co-active
                       second slice (e.g. heavy Score activity in a
                       function the cascade tagged temp-tie)
      ✗ CONTRADICT  -- the named slice should have activity but the trace
                       shows none (suggests the cascade verdict misnamed
                       the slice; e.g. find_enemy treegen:index-fusion
                       with 0 mi events => CONFIRMS NOT-MergeIndex)
    """
    a = trace_activity_summary(name)
    if a is None:
        return None
    if slice_tag == "optimize:loop-hoist":
        if a["score_active"] == 0:
            return "trace contradicts: 0 sbi+sbs (Score not active)"
        return None
    if slice_tag == "treegen:index-fusion":
        if a["mi_active"] == 0 and a["mi_attempts"] > 0:
            return (f"trace confirms NOT-MergeIndex: "
                    f"{a['mi_attempts']} predicate attempts, 0 fusions "
                    f"-- the divergence is CountRegMoves coalesce, NOT "
                    f"MergeIndex")
        return None
    # ENRICH note: a non-L4 slice (shape, substrate, etc) carries no
    # useful verification signal here -- big shape functions always have
    # lots of Score activity as a side effect.  Restrict the co-active
    # warning to L4-specific slices where the cascade promised a single
    # named lever and the trace reveals a second one is also live.
    _L4_SLICES = {
        "tie-reorder", "tie-reorder-pinned",
        "temp-tie", "named-tie",
        "byte", "slot", "rover:scratch-seat",
        "regalloc:capacity", "regalloc:callee-save-tie",
        "treegen:use-order", "treegen:savings",
    }
    if slice_tag in _L4_SLICES and a["score_active"] >= 50:
        return (f"trace enriches: heavy Score co-activity ({a['sbi']} sbi + "
                f"{a['sbs']} sbs) -- the {slice_tag} slice is one component; "
                "the Score/coalesce layer is ALSO active here")
    return None


def pressure_detail(name: str, vrec: dict) -> list[str]:
    """Build #3 seed: for a callee-save COUNT divergence, name the marginal
    value near the register threshold and the savings gap to the rival.  The
    lever is to move that value across the threshold (raise its savings / lower
    the rival's): hoist a load, cache a reload across the call, or change a
    reference's loop depth."""
    pragma = vrec.get("pragma_hint") or {}
    out = [f"  {pragma.get('summary', '')}"]
    tf = _load_trace_func(name)
    if not tf:
        return out + ["  (no cached trace)"]
    al = _dword_allocs(tf)
    # the marginal decisions: dword values that DID get a callee-saved reg
    # (EBX/ESI/EDI/EBP) vs those exiled to memory, ranked by savings -- the
    # threshold sits between the lowest-savings enregistered value and the
    # highest-savings memory-exiled one.
    callee = {"EBX", "ESI", "EDI", "EBP"}
    enreg = sorted((a for a in al if a.get("reg_name") in callee),
                   key=lambda a: a.get("savings", 0))
    exiled = sorted((a for a in al if a.get("memory_exiled")
                     or a.get("reg_name") == "MEM"),
                    key=lambda a: -a.get("savings", 0))
    if enreg:
        a = enreg[0]
        out.append(f"  lowest enregistered callee-save: "
                   f"{a.get('var') or '(temp)'} -> {a['reg_name']} "
                   f"savings={a.get('savings')}"
                   + (f" L{a['defline']}" if a.get("defline") else ""))
    if exiled:
        a = exiled[0]
        out.append(f"  highest memory-exiled value: "
                   f"{a.get('var') or '(temp)'} savings={a.get('savings')}"
                   + (f" L{a['defline']}" if a.get("defline") else ""))
        out.append("  LEVER (build #3): push that value over the threshold "
                   "(hoist its load / cache a reload across the call / change "
                   "a reference's loop depth) -- COMPILE-VERIFY (savings/"
                   "live-range change).")
    binir = (vrec.get("binir_shape_hint") or {}).get("verdict")
    if binir == "encoding_noise":
        out.append("  NOTE: binir is identical here -- the pressure residue "
                   "is the live target.")
    else:
        out.append("  NOTE: pressure is DOWNSTREAM of shape and binir is NOT "
                   f"yet identical ({binir}). Fix the shape layer FIRST; this "
                   "pressure verdict is a preview.")
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _load_verify() -> dict:
    if not VERIFY_CACHE.exists():
        raise typer.Exit(typer.secho(
            "verify.json cache missing -- run `c2 decomp-verify --json` first.",
            fg="red"))
    return _load_cache(VERIFY_CACHE)


def regalloc_verdict(
    function: str = typer.Argument(
        None, help="one function (deep view); omit for the corpus table"),
    steerable: str = typer.Option(
        None, "--steerable",
        help="filter corpus to one steerable class "
             "(named-tie/temp-tie/byte/slot/pressure/shape/floor)"),
    layer: int = typer.Option(
        None, "--layer", help="filter corpus to one layer (1-5)"),
    as_json: bool = typer.Option(False, "--json", help="emit JSON"),
):
    """Layered residue work-order verdict for the diffing corpus (or one fn).

    Reports the EARLIEST divergent layer == the next action, the named lever,
    and whether it is steerable today.  Offline from the verify + trace caches.
    """
    V = _load_verify()
    fd = {f["name"]: f for f in V.get("functions", []) if "name" in f}

    if function:
        vrec = fd.get(function)
        if vrec is None:
            typer.secho(f"{function}: not in verify cache", fg="red")
            raise typer.Exit(1)
        if vrec.get("diff_byte_count", 0) == 0:
            typer.secho(f"{function}: byte-exact (no residue)", fg="green")
            return
        v = layered_verdict(vrec, name=function, reconcile=True)
        if as_json:
            typer.echo(json.dumps({**v, "function": function}, indent=1))
            return
        col = {1: "yellow", 2: "magenta", 3: "red",
               4: "cyan", 5: "bright_black"}[v["layer"]]
        typer.secho(f"\n{function}  — residue layer L{v['layer']} "
                    f"({v['name']})", bold=True)
        typer.secho(f"  earliest divergent layer: L{v['layer']} "
                    f"{v['name']}  [{_LAYER_NAME[v['layer']]}]", fg=col)
        typer.echo(f"  lever     : {v['lever']}")
        typer.echo(f"  steerable : {v['steerable']}")
        typer.echo(f"  detail    : {v['detail']}")
        # Empirical verification of the slice attribution against the
        # actual compile-phase trace.  Surfaces (a) confirmations, (b) co-
        # active slices the cascade missed, (c) contradictions where the
        # named slice has zero trace activity (slice mis-attribution).
        _tv = trace_verification_note(function, v["steerable"])
        if _tv:
            color = "red" if "contradict" in _tv.lower() else (
                "yellow" if "enrich" in _tv.lower() else "green")
            typer.secho(f"  trace     : {_tv}", fg=color)
        if len(v.get("stack", [])) > 1:
            typer.secho(
                f"  stack     : {' → '.join(v['stack'])}  "
                f"({len(v['stack'])} layers; fix earliest first, expect more)",
                fg="bright_black")
        if v["steerable"] == "temp-tie":
            typer.secho("  --- build #2 (temp pin) ---", fg="cyan")
            for ln in temp_tie_detail(function, vrec):
                typer.echo(ln)
        elif v["steerable"] == "named-tie":
            typer.secho("  --- decl-swap (steerable today) ---", fg="green")
            d = vrec.get("decl_order_hint") or {}
            locs = {l["name"]: l.get("line") for l in (d.get("locals") or [])}
            a, b = d["candidate_pair"]
            typer.echo(f"  swap decl lines of {a} (ln{locs.get(a)}) and "
                       f"{b} (ln{locs.get(b)})  (screen: c2 savings "
                       f"{function} --flip)")
        elif v["steerable"] == "pressure":
            typer.secho("  --- build #3 (pressure) ---", fg="red")
            for ln in pressure_detail(function, vrec):
                typer.echo(ln)
        elif v["steerable"] == "shape" and (vrec.get("pragma_hint") or {}) \
                .get("category") in ("ps_extra_callee_save",
                                     "rc_extra_callee_save"):
            typer.secho("  --- downstream pressure preview (gated by shape) "
                        "---", fg="bright_black")
            for ln in pressure_detail(function, vrec):
                typer.echo(ln)
        # ---- Score / MergeIndex event streams (the new probe data) ----
        # Auto-surface for the slices the events directly inform:
        #   optimize:loop-hoist       -> Score sb/sbi/sbs (names the
        #                                  call/store that invalidated RC's
        #                                  scoreboard -- pair vs PS asm)
        #   treegen:index-fusion      -> MergeIndex mic/mip/mi (names which
        #                                  ins's actually fused vs were
        #                                  rejected at predicate)
        if v["steerable"] in ("optimize:loop-hoist",) or \
                "loop-hoist" in v.get("lever", ""):
            typer.secho("  --- Score (redundant-load coalesce) trace ---",
                        fg="cyan")
            for ln in score_event_summary(function):
                typer.echo(ln)
        if v["steerable"] in ("treegen:index-fusion",) or \
                "index-fusion" in v.get("lever", ""):
            typer.secho("  --- MergeIndex (index-fusion) trace ---",
                        fg="cyan")
            for ln in mergeindex_event_summary(function):
                typer.echo(ln)
        return

    # ---- corpus table ----
    rows = []
    for f in V.get("functions", []):
        if f.get("diff_byte_count", 0) <= 0:
            continue
        v = layered_verdict(f, name=f["name"], reconcile=True)
        if steerable and v["steerable"] != steerable:
            continue
        if layer and v["layer"] != layer:
            continue
        rows.append((f["name"], v))
    rows.sort(key=lambda r: (r[1]["layer"], -r[1]["bytes"]))

    if as_json:
        typer.echo(json.dumps(
            [{"function": n, **v} for n, v in rows], indent=1))
        return

    from collections import Counter
    by_steer = Counter(v["steerable"] for _, v in rows)
    by_layer = Counter(v["layer"] for _, v in rows)
    # NOTE: byte diff is a corpus-progress figure kept in the
    # `decomp-verify` / `progress` project views only; it is not surfaced
    # here (the per-function judge metric is the residue LAYER / steerability).

    typer.secho(f"\n{len(rows)} diffing functions  (by residue layer)",
                bold=True)
    typer.echo("\nwork-order (earliest divergent layer == next action):")
    for L in sorted(by_layer):
        typer.echo(f"  L{L} {_LAYER_NAME[L]:<11} {by_layer[L]:>4} fns")
    typer.echo("\nallocation-layer steerability:")
    for s in ("named-tie", "temp-tie", "slot", "byte", "pressure", "floor"):
        if by_steer.get(s):
            typer.echo(f"  {s:<11} {by_steer[s]:>4} fns")
    # keep the within-layer rows ordered deterministically by name (the
    # byte count is no longer shown and not used for ranking).
    rows.sort(key=lambda r: (r[1]["layer"], r[0]))

    typer.echo("")
    typer.secho(f"{'function':<34}  L  {'steerable':<10} lever",
                bold=True)
    for n, v in rows:
        col = {1: "yellow", 2: "magenta", 3: "red",
               4: "cyan", 5: "bright_black"}[v["layer"]]
        typer.secho(f"{n:<34}  {v['layer']}  "
                    f"{v['steerable']:<10} {v['lever']}", fg=col)
