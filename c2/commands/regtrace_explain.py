"""Correlate the live GiveBestReg trace (`c2 regtrace`) with the actual
PS-vs-recomp byte diff (`decomp-verify`) and emit a ground-truth-backed,
per-divergence lever for HARD cases.

`c2 regtrace` alone prints a flat list of allocator conflicts disconnected from
the byte diff -- not actionable.  This module bridges them:

  * the trace gives, per conflict, the allocator's REAL inputs (savings, the
    candidate priority list -- and crucially its register CLASS: int vs word vs
    byte -- the chosen register, and the allocation/use order);
  * the diff gives the actual PS-vs-RC instruction divergence with registers.

From the two it classifies each register divergence into the validated 7-layer
model (regalloc-model.md) and names the SPECIFIC competing conflict + the source
lever -- turning "Reg swap AX/CX" into "conflict `c` (word-class, savings 55,
alloc-order #0) vs the EAX temps: it's a TYPE-width / truncation-form divergence,
not a register swap -- match the value's width / zero-extension".

Public entry: ``explain(conflicts, diff_rows) -> list[str]`` (report lines).
``conflicts`` are the target-function rows from regtrace.json; ``diff_rows`` are
the ``rows`` array from ``decomp-verify --json`` for the same function.
"""
from __future__ import annotations

import re

# register token -> (class, canonical 32-bit name)
_WORD = {"ax": "eax", "dx": "edx", "bx": "ebx", "cx": "ecx",
         "si": "esi", "di": "edi", "bp": "ebp", "sp": "esp"}
_BYTE = {"al": "eax", "ah": "eax", "dl": "edx", "dh": "edx",
         "bl": "ebx", "bh": "ebx", "cl": "ecx", "ch": "ecx"}
_INT = {"eax", "edx", "ebx", "ecx", "esi", "edi", "ebp", "esp"}
_REG_RE = re.compile(r"\b(e?[a-d]x|[a-d][lh]|e?[sb]p|e?[sd]i)\b")


def _classify_reg(tok: str) -> tuple[str, str] | None:
    """(class, canonical32) for a register token, else None."""
    if tok in _INT:
        return ("int", tok)
    if tok in _WORD:
        return ("word", _WORD[tok])
    if tok in _BYTE:
        return ("byte", _BYTE[tok])
    return None


def _regs(asm: str) -> list[tuple[str, str]]:
    return [c for t in _REG_RE.findall(asm) if (c := _classify_reg(t))]


def _cand_class(cands: list[str]) -> str:
    """Register class of a conflict's candidate list (int/word/byte)."""
    if not cands:
        return "int"
    c0 = cands[0].lower()
    # candidate lists are printed as e.g. ['AX','DX',...] (word) or
    # ['EAX',...] (int) or ['AH','AL',...] (byte) -- or hex (a raw hw_reg_set).
    if c0.startswith("e"):
        return "int"
    if c0 in _WORD:
        return "word"
    if c0 in _BYTE:
        return "byte"
    return "int"


_EXT_FORMS = ("movzx", "movsx", "and ", "cbw", "cwde", "movsxd")


def _is_extension_row(ps_asm: str, rc_asm: str) -> bool:
    """True when one side zero/sign-extends or masks and the other doesn't, or
    word-ptr vs dword access -- the truncation-form divergence (Rule 8/23/49)."""
    def feats(a: str) -> tuple[bool, bool, bool]:
        return (
            any(f in a for f in _EXT_FORMS) or "0xffff" in a or "0xff" in a,
            "word ptr" in a,
            "byte ptr" in a,
        )
    return feats(ps_asm) != feats(rc_asm)


# DoubleRegs priority order (32-bit int class) -- the candidate order the model
# walks; index = allocation priority (lower wins ties).
_DOUBLE_REGS = ["eax", "edx", "ebx", "ecx", "esi", "edi", "ebp", "esp"]


def _given_before(conf: dict, all_conflicts: list[dict]) -> tuple[int, dict]:
    """GivenRegisters (the already-handed-out register set) at the moment
    ``conf`` is allocated, plus ``{REG: the conflict that first gave it}``.
    GiveBestReg does ``HW_TurnOn(GivenRegisters, pick)`` on every assignment
    (regalloc.c) and the prefer-already-given equal-savings tie-break tests
    ``HW_Subset(GivenRegisters, cand)``.

    The MASK comes from the bt hook's ground-truth ``given_regs`` snapshot
    (read at THIS conflict's GiveBestReg entry) when the trace carries it;
    the union-of-earlier-picks reconstruction is kept only as a fallback for
    older traces and for SEEDER attribution (which conflict first took each
    reg) -- the hardware mask alone cannot name the rival."""
    from c2.commands.regtrace import _REG_ENC
    my = conf.get("order", 0)
    mask, seeder = 0, {}
    for c in sorted(all_conflicts, key=lambda c: c.get("order", 0)):
        if c.get("order", 0) >= my:
            break
        reg = (c.get("chosen") or "").upper()
        enc = _REG_ENC.get(reg)
        if enc:
            seeder.setdefault(reg, c)
            mask |= enc
    gt = conf.get("given_regs")
    if gt:                      # ground truth from the bt hook (>= 2026-06-11)
        mask = gt
    return mask, seeder


def invert_to_target(conf: dict, target: str,
                     all_conflicts: list[dict]) -> dict | None:
    """Model inversion: given a conflict and the register PS actually used
    (`target`), compute WHY our model didn't pick it and the minimal input
    change (mapped to a source lever) that would flip it.

    Returns a dict {case, lever, detail, competitor?} or None if already matches.
    Cases mirror the GiveBestReg decision points:
      not_candidate   - target isn't in the candidate list  -> TYPE/class lever
      taken           - target is in with.regs (held by a rival) -> displace it
      crm_loss        - target free but lower CountRegMoves   -> move-elim lever
      order_loss      - target free, equal CRM, later in DoubleRegs -> the
                        equal-savings tie went the other way (ConfBefore
                        name-pointer); levers are Rule 28a (commute the use)
                        or Rule 115 (swap the two locals' decl order)
    """
    from c2.commands.regtrace import _REG_ENC, _count_reg_moves
    target = target.lower()
    target_up = target.upper()
    chosen = (conf.get("chosen") or "").lower()
    if chosen == target:
        return None
    cand_lower = [c.lower() for c in conf.get("cand", [])]
    wr = conf.get("withregs", 0)
    tenc = _REG_ENC.get(target_up)

    # (1) target not a candidate -> register-class / type mismatch
    if target_up not in conf.get("cand", []):
        cls0 = (conf["cand"][0].lower() if conf.get("cand") else "?")
        return {
            "case": "not_candidate",
            "detail": f"PS reg {target_up} is not in our candidate list "
                      f"(class starts at {cls0.upper()})",
            "lever": "TYPE/class: the value's register class differs from PS's. "
                     "Fix the declared width / signedness so the candidate list "
                     "matches (int vs short vs char; Rule 8/23/49).",
        }

    # (2) target taken in with.regs -> a rival conflict holds it
    if tenc is not None and (tenc & wr):
        comp = next((c for c in all_conflicts
                     if (c.get("chosen") or "").lower() == target
                     and c is not conf), None)
        cd = (f"{comp.get('var') or 'temp'}[sav={comp.get('savings')}, "
              f"line {comp.get('def_line_num')}]" if comp else "(unknown)")
        return {
            "case": "taken",
            "competitor": comp,
            "detail": f"PS reg {target_up} is already held by {cd}",
            "lever": "displace the rival: it out-prioritised this value for "
                     f"{target_up}. Lower the rival's savings (drop a use / "
                     "shorten its live range) or raise this value's savings, OR "
                     "flip the equal-savings ConfBefore name-pointer tie via "
                     "(a) use-order — commute the deciding expression / move a "
                     "statement so this value is referenced first (Rule 28a, "
                     "most predictable), or (b) decl-order — swap the two tied "
                     "locals' declaration lines (Rule 115, for when the use is "
                     "pinned; direction non-monotonic, verify both orders).",
        }

    # (3) target free + candidate but model picked `chosen` instead
    if tenc is not None and chosen:
        cenc = _REG_ENC.get(chosen.upper())
        # Prefer the recorded per-candidate CountRegMoves saves (ce/cq ground
        # truth on crm_scores) over the legacy ins_walk re-derivation, which
        # mis-scores move-elimination picks (see regtrace._gb_pick_scores).
        _cs = conf.get("crm_scores") or {}
        if _cs:
            crm_t = _cs.get(target_up, 0)
            crm_c = _cs.get(chosen.upper(), 0)
        else:
            crm_t = _count_reg_moves(conf, tenc)
            crm_c = _count_reg_moves(conf, cenc) if cenc else 0
        if crm_c > crm_t:
            return {
                "case": "crm_loss",
                "detail": f"{target_up} CountRegMoves={crm_t} < {chosen.upper()}="
                          f"{crm_c} (move-elimination favoured {chosen.upper()})",
                "lever": "move-elimination (layer 4): the value coalesced into "
                         f"{chosen.upper()} to elide an arg/return move. If this "
                         "is a single-use `arr[i].field` load whose index fused "
                         "into the result register, split it with a dead store "
                         "through the same index (`arr[i].field = arr[i].field;`) "
                         "— Watcom DCEs it but the index gets its own scratch reg "
                         f"(Rule 109). Otherwise land the value in {target_up} via "
                         f"a MOV/OP into {target_up}'s role, or remove the move "
                         f"feeding {chosen.upper()}.",
            }
        # equal CRM -> the GivenRegisters tie-break (prefer-already-given)
        # decided it.  Reconstruct GivenRegisters at this value's allocation:
        # if `chosen` was already-given while `target` was NOT, that IS the
        # reason, and the conflict that first took `chosen` is the rival.
        gmask, seeder = _given_before(conf, all_conflicts)
        if (_REG_ENC.get(chosen.upper(), 0) & gmask) and not ((tenc or 0) & gmask):
            seed = seeder.get(chosen.upper())
            sd = (f"{seed.get('var') or 'temp'}[sav={seed.get('savings')}, "
                  f"line {seed.get('def_line_num')}, alloc #{seed.get('order')}]"
                  if seed else "an earlier value")
            return {
                "case": "order_loss",
                "competitor": seed,
                "detail": f"{chosen.upper()} was ALREADY-GIVEN (first to {sd}) when "
                          f"this value (alloc #{conf.get('order')}) was allocated, "
                          f"but {target_up} was not -- with equal CountRegMoves, "
                          "GiveBestReg's prefer-already-given tie-break reused "
                          f"{chosen.upper()}",
                "lever": f"make {target_up} already-given BEFORE alloc "
                         f"#{conf.get('order')} (give it to an earlier, "
                         f"higher-savings value), OR move {sd} OFF {chosen.upper()} "
                         "so it leaves the given-set -- use-order (Rule 28a, "
                         "reference the rival first through a different reg) or "
                         "decl-order (Rule 115). The rival is named above.",
            }
        # else: DoubleRegs candidate order decided it
        try:
            ti, ci = _DOUBLE_REGS.index(target), _DOUBLE_REGS.index(chosen)
        except ValueError:
            ti = ci = 0
        if ti > ci:
            return {
                "case": "order_loss",
                "detail": f"{target_up} is later in DoubleRegs than {chosen.upper()}"
                          f" and CRM ties ({crm_t}); the earlier reg wins",
                "lever": "layer 3 tie-break = REVERSE LAST-USE: conflicts are "
                         "created at each operand's LAST use (backward live "
                         "scan, liveinfo.c) and PREPENDED; SortConflicts is an "
                         "unstable ShellSort over that order (strict savings>). "
                         f"To take the EARLIER reg ({chosen.upper()} side), this "
                         "value must be created LAST = have the EARLIER LAST USE: "
                         "move its final read up, or push the rival's final read "
                         "down.  decl/first-assign order usually does NOT move "
                         "it.  Worked: get_reg_buildings_in_radius (ef1467d4); "
                         "screen: c2 savings <fn> --flip VAR=REG.  (Failing "
                         f"that, raise {target_up}'s CountRegMoves or overall "
                         "pressure.)",
            }
        return {
            "case": "order_loss",
            "detail": f"{target_up} earlier than {chosen.upper()} yet not chosen "
                      "(unexpected: check with.regs/except capture)",
            "lever": "layer 3 tie-break = REVERSE LAST-USE: to allocate this "
                     "value before its rival, give it the EARLIER last use "
                     "(move its final read up / the rival's down); it is then "
                     "created last and sorts first.  decl/first-assign order "
                     "usually does NOT move it.  Screen: c2 savings <fn> --flip "
                     "VAR=REG; worked: get_reg_buildings_in_radius.",
        }
    return None


def _detect_swaps(diff_rows: list[dict]) -> dict:
    """Canonical register-identity swaps (frozenset pair -> {regs, n}) from the
    diff rows.  Used by explain()."""
    swaps: dict = {}
    for r in diff_rows:
        if r.get("kind") != "replace":
            continue
        ps = (r.get("ps") or {}).get("asm", "")
        rc = (r.get("rc") or {}).get("asm", "")
        if not ps or not rc or _is_extension_row(ps, rc):
            continue
        ps_int = {f for cl, f in _regs(ps) if cl == "int"}
        rc_int = {f for cl, f in _regs(rc) if cl == "int"}
        only_ps, only_rc = ps_int - rc_int, rc_int - ps_int
        if len(only_ps) == 1 and len(only_rc) == 1:
            a, b = only_ps.pop(), only_rc.pop()
            swaps.setdefault(frozenset((a, b)), {"regs": (a, b), "n": 0})["n"] += 1
    return swaps


def _do_this(case: str, rc_conf: dict, ps_confs: list[dict],
             has_typewidth: bool = False) -> str | None:
    """Concrete 'do this' for an order_loss (equal-savings tie) between two
    NAMED locals: the exact decl-swap with line numbers (Rule 115), commute
    (Rule 28a) as fallback. Returns None for compiler temps / non-tie cases.

    CAUTION: a register swap can be a DOWNSTREAM artifact of a type-width diff
    rather than its cause -- decl-swapping then regresses (verified on
    get_nearest_reg_building: 4->8b). So when the diff also carries a
    type-width/truncation row, this is demoted to a CANDIDATE and the
    width fix is named as the primary lever."""
    if case != "order_loss" or not ps_confs:
        return None
    a = rc_conf.get("var")
    la = rc_conf.get("def_line_num") or rc_conf.get("def_line")
    pc = max(ps_confs, key=lambda c: c.get("savings", 0))
    b = pc.get("var")
    lb = pc.get("def_line_num") or pc.get("def_line")
    if not (a and b and la and lb) or a.startswith("(") or b.startswith("("):
        return None
    if a == b or la == lb:
        return None
    first, second = sorted([(la, a), (lb, b)])
    swap = (f"swap the declaration lines of {first[1]} (ln{first[0]}) "
            f"and {second[1]} (ln{second[0]}) [Rule 115]; else commute the "
            f"deciding use of {a} so it is referenced before {b} [Rule 28a]")
    if has_typewidth:
        return (f"CANDIDATE (verify -- the diff is NOT a clean swap-only "
                f"divergence (it has type-width / semantic / encoding rows); "
                f"this {a}<->{b} swap is likely downstream and a decl-swap may "
                f"regress -- fix the non-swap rows first): {swap}")
    return f"DO THIS: {swap}."


def explain(conflicts: list[dict], diff_rows: list[dict]) -> list[str]:
    out: list[str] = []
    named = [c for c in conflicts if c.get("var")]

    # ---- 1. type-width-sensitive conflicts (word/byte register classes) ----
    typed = [c for c in named if _cand_class(c.get("cand", [])) != "int"]
    if typed:
        out.append("type-width conflicts (candidate class != int -- these are "
                   "short/char values; divergences on them are TRUNCATION-form,")
        out.append("  Rule 8/23/49, NOT register swaps -- the lever is the "
                   "value's declared width / zero-extension, not regalloc):")
        for c in typed:
            cls = _cand_class(c.get("cand", []))
            out.append(f"    {c['var']:<14} {cls}-class  savings={c.get('savings')}"
                       f"  candidates={','.join(c.get('cand', []))}")

    # ---- 2. classify each diff divergence ----
    # build register -> chosen conflict map (int class) from the trace
    chosen_by_reg: dict[str, list[dict]] = {}
    for c in conflicts:
        ch = (c.get("chosen") or "").lower()
        if ch in _INT:
            chosen_by_reg.setdefault(ch, []).append(c)

    # source-line -> conflicts defined there (def_line_num), for pinning a diff
    # row to the SPECIFIC value involved (works for unnamed temps too).
    by_line: dict[int, list[dict]] = {}
    for c in conflicts:
        ln = c.get("def_line_num") or 0
        if ln:
            by_line.setdefault(ln, []).append(c)

    def _at_line(ln: int | None) -> str:
        if not ln or ln not in by_line:
            return ""
        names = [(c.get("var") or f"temp@{ln}") + f"[{c.get('chosen')},sav={c.get('savings')}]"
                 for c in by_line[ln]]
        return f" (line {ln}: {', '.join(names)})"

    # canonicalize swaps by the unordered pair (frozenset) so a PS-esi/RC-edi row
    # and a PS-edi/RC-esi row merge into one "ESI<->EDI swap".
    swaps: dict[frozenset, dict] = {}
    trunc = 0
    other = 0   # replace rows that are neither a clean swap nor a trunc/width
                # divergence -> semantic / strength-reduction / encoding noise
    for r in diff_rows:
        if r.get("kind") not in ("replace",):
            continue
        ps = (r.get("ps") or {}).get("asm", "")
        rc = (r.get("rc") or {}).get("asm", "")
        if not ps or not rc:
            continue
        if _is_extension_row(ps, rc):
            trunc += 1
            continue
        ps_int = {f for cl, f in _regs(ps) if cl == "int"}
        rc_int = {f for cl, f in _regs(rc) if cl == "int"}
        only_ps = ps_int - rc_int
        only_rc = rc_int - ps_int
        # a clean 1-1 identity swap (same count) is the classic regalloc swap
        if len(only_ps) == 1 and len(only_rc) == 1:
            a, b = only_ps.pop(), only_rc.pop()
            key = frozenset((a, b))
            sw = swaps.setdefault(key, {"n": 0, "regs": (a, b), "lines": set()})
            sw["n"] += 1
            if r.get("ln"):
                sw["lines"].add(r["ln"])
        else:
            other += 1

    if trunc:
        out.append(f"truncation/extension divergences: {trunc} row(s) where one "
                   "side masks/extends and the other doesn't (Rule 8/23/49 --")
        out.append("  fix the value's width / zero-extension form; not a "
                   "register-allocation problem).")

    # a register swap is only a trustworthy 'do this' when the diff is a CLEAN
    # swap-only divergence: no type-width/truncation rows AND no other
    # (semantic / strength-reduction / encoding) replace rows -- both of those
    # masquerade as swaps, and a decl-swap then regresses (verified:
    # get_nearest_reg_building type-width 4->8b; show_selections is 80% semantic).
    has_typewidth = bool(typed) or trunc > 0 or other > 0

    already_pinned: dict = {}
    if swaps:
        out.append("register-identity swaps (PS reg <-> RC reg) -- correlate to "
                   "the trace to find the competing value + the lever:")
        for sw in sorted(swaps.values(), key=lambda s: -s["n"]):
            ps_r, rc_r = sw["regs"]
            n = sw["n"]
            out.append(f"    {ps_r.upper()} <-> {rc_r.upper()}  ({n} row(s))")
            # pin to the conflict(s) at the diff rows' source lines, and INVERT
            # the model: the value RC put in rc_r should be in ps_r (PS's reg).
            pinned = False
            for ln in sorted(x for x in sw.get("lines", set()) if x):
                pin = _at_line(ln)
                if not pin:
                    continue
                out.append(f"      at{pin}")
                for c in by_line.get(ln, []):
                    if (c.get("chosen") or "").lower() != rc_r:
                        continue
                    inv = invert_to_target(c, ps_r, conflicts)
                    if inv:
                        pinned = True
                        out.append(f"        -> {inv['case']}: {inv['detail']}")
                        out.append(f"           lever: {inv['lever']}")
                        do = _do_this(inv["case"], c, chosen_by_reg.get(ps_r, []),
                                      has_typewidth)
                        if do:
                            out.append(f"           {do}")
            already_pinned[frozenset((ps_r, rc_r))] = pinned
            ps_owner = chosen_by_reg.get(ps_r, [])
            rc_owner = chosen_by_reg.get(rc_r, [])

            def _desc(cs: list[dict]) -> str:
                parts = []
                for c in sorted(cs, key=lambda c: -c.get("savings", 0))[:3]:
                    v = c.get("var") or "(temp)"
                    parts.append(f"{v}[sav={c.get('savings')},ln{c.get('def_line_num')}]")
                return ", ".join(parts) or "(none in trace)"

            out.append(f"      our {rc_r} holds: {_desc(rc_owner)}")
            out.append(f"      our {ps_r} holds: {_desc(ps_owner)}")
            # Register reuse makes rc_r ambiguous; the swapped value is most
            # likely the DOMINANT (highest-savings) conflict in rc_r.  Run the
            # precise model inversion on it toward ps_r -- this fires even when
            # no diff row carried a source line (best-guess, labelled).
            if not already_pinned.get(frozenset((ps_r, rc_r))) and rc_owner:
                dom = max(rc_owner, key=lambda c: c.get("savings", 0))
                inv = invert_to_target(dom, ps_r, conflicts)
                if inv:
                    v = dom.get("var") or f"temp[sav={dom.get('savings')}]"
                    out.append(f"      best-guess (dominant {rc_r} value {v}): "
                               f"{inv['case']}")
                    out.append(f"        lever: {inv['lever']}")
                    do = _do_this(inv["case"], dom, ps_owner, has_typewidth)
                    if do:
                        out.append(f"        {do}")

    if not out:
        out.append("no register-class divergence found in the trace x diff "
                   "correlation -- the diff is likely instruction-selection / "
                   "strength-reduction / branch-encoding (outside regalloc).")
    return out
