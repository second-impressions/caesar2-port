"""Byte-seat verdict -- one classification for every ``Byte-reg swap`` row.

The generic ``Byte-reg swap`` classifier (rule_hints.detect_byte_reg_swap)
fires last and historically said *"usually no source lever"* -- which is
both incomplete (three real levers exist) and sometimes wrong (the row is
often the low byte of a dword tie that IS reorderable).  This module
synthesises the existing signals into ONE verdict naming the OW-v1 path
and its lever, so an agent never (a) grinds decl-order reorders on
an inert byte tie, nor (b) gives up on a widenable / de-nameable value.

Four cases.  Each is proven against the disassembled wcc386 10.0a binary
(VAs below; pinned in the watcom10.0a repo's ``knowledge/wcc386_regalloc.py``
and mirrored in ``docs/wcc386-re/regalloc-model.md`` §"Byte-register
seating").  OW v1 ``bld/cg/`` is only the algorithm guide.

  A  COLLATERAL -- the byte register is the low/high byte of a 32-bit (or
     16-bit) ``Reg swap``; the real divergence is a dword/word equal-savings
     tie, NOT byte-seat coloring.  Lever: the dword tie levers (Rule 28a /
     115 / 123); if ``Cascade:`` says REACHABLE, screen with
     ``c2 savings <fn> --flip VAR=REG --depth 2`` / ``c2 sweep <fn>``.

  B  AL-SQUAT MASKING (Rule 126) -- a genuine byte conflict that our build
     seats in AL while PS keeps it off A via ``NeighboursUse@0x580c0``
     masking (conf->with.regs at +0x20) of an EAX zext/address temp;
     ``GiveBestReg`` excludes the masked candidate at VA 0x57c50.  Lever:
     widen the bare-AND ``unsigned char`` locals to ``int`` so the value
     leaves the ``ByteRegs`` path for ``DoubleRegs`` (get_education 92->44).

  C  ROVER-SEATED CSE (Rule 127) -- PS commoned a repeated byte expression
     into a ``FindRegister@0x62a29`` rover pick, re-extended via
     ``mov al,<reg>; and eax,0xff``; our named local makes a GiveBestReg
     conflict seated in AL instead.  Lever: de-name -- write the expression
     twice (battle_action 316b -> exact).

  D  INERT BYTE TIE (Rule 133) -- a genuine byte conflict whose seat is
     decided by GiveBestReg's tie-break, which is DEAD for bytes: every
     byte register is a sub-register of an already-given dword, so
     ``HW_Subset(GivenRegisters, cand)`` is true for ALL candidates
     (tie-break at VA 0x57ca1-0x57cc8) and ``ByteRegs@0x79620`` list-order
     decides.  SOURCE-IRREDUCIBLE -- do NOT run permute/decl-swap; park it.

The verdict has a STATIC fast-path (PS asm + RC AST, always available) and
a TRACE upgrade (regclass + GiveBestReg reason) when the 10.0a trace image
is present.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

# byte register -> parent dword (low/high byte both map to the same dword)
_PARENT = {
    "al": "eax", "ah": "eax", "dl": "edx", "dh": "edx",
    "bl": "ebx", "bh": "ebx", "cl": "ecx", "ch": "ecx",
}
# byte register -> parent word (16-bit), for collateral-to-a-word-tie
_PARENT_W = {
    "al": "ax", "ah": "ax", "dl": "dx", "dh": "dx",
    "bl": "bx", "bh": "bx", "cl": "cx", "ch": "cx",
}
_BYTE_SWAP_RE = re.compile(r"PS uses `(\w+)`, recomp uses `(\w+)`")
_REG_TOKEN_RE = re.compile(r"\b(e[a-d]x|e[sd]i|ebp)\b")


def _cascade_savings_pair(func, hints, rows, file, parents):
    """Rule 157 key: return the ``'X<->Y'`` pair string when the VALIDATED
    cascade replay search classifies a dword swap involving the byte's
    PARENT register(s) as ``needs a SAVINGS change`` (a genuine savings gap,
    not an equal-savings tie), else ``None``.

    NOT a savings-delta proxy.  A raw savings delta between two alloc rows
    does NOT prove they are the competing OVERLAPPING pair: ``NeighboursUse``
    (vendor/open-watcom bld/cg/c/regalloc.c:1157) excludes a register from a
    conflict's candidate set ONLY when a value whose LIVE RANGE OVERLAPS the
    conflict holds it -- independent of savings magnitude.  So the byte loses
    AL iff an *overlapping* higher-savings value took EAX; cascade_hints does
    that overlap-aware replay, a magnitude threshold cannot."""
    try:
        from c2.commands import cascade_hints
        cv = cascade_hints.detect(func, hints, rows=rows, file=file)
    except Exception:
        return None
    if cv is None:
        return None
    pu = {p.upper() for p in parents}
    for ln in cv.lines:
        if "needs a SAVINGS change" not in ln:
            continue
        m = re.search(r"Cascade:\s*(\w+)<->(\w+)\s+needs a SAVINGS change", ln)
        if m and (m.group(1) in pu or m.group(2) in pu):
            return f"{m.group(1)}<->{m.group(2)}"
    return None


@dataclass
class ByteSeatVerdict:
    func: str
    case: str                       # 'A' | 'A2' | 'B' | 'C' | 'D' | 'E' | 'R'
    confidence: str                 # 'trace' | 'static'
    lines: list[str] = field(default_factory=list)
    savings_pair: str | None = None  # CASE E: the 'X<->Y' SAVINGS-gap swap


def _byte_swap_pairs(hints) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for h in hints or ():
        if getattr(h, "rule", None) != "Byte-reg swap":
            continue
        m = _BYTE_SWAP_RE.search(getattr(h, "summary", "") or "")
        if m:
            out.append((m.group(1).lower(), m.group(2).lower()))
    return out


def _dword_swap_pairs(hints) -> set[frozenset]:
    """All register pairs named by ``Reg swap`` hints (32-bit identity
    swaps), as unordered {a, b} sets."""
    out: set[frozenset] = set()
    for h in hints or ():
        if getattr(h, "rule", None) != "Reg swap":
            continue
        regs = _REG_TOKEN_RE.findall((getattr(h, "summary", "") or "").lower())
        for i in range(0, len(regs) - 1, 2):
            out.add(frozenset((regs[i], regs[i + 1])))
    return out


_BYTE_REG_ONLY_RE = re.compile(r"\b(a[lh]|b[lh]|c[lh]|d[lh])\b")


def _kmap_line(rows) -> Optional[str]:
    """The measured byte-rover k-map, straight from the aligned diff rows.

    For every aligned row whose two sides are the same mnemonic with byte-
    register operands, k = cyclic distance (ByteRegs order, corrected H/L
    orientation via rover_hints/_REG_IDX) from the RC pick to the PS pick:
    k=0 at matching sites (anchors), k=+n where RC's cursor is n advances
    BEHIND PS.  Piecewise-constant runs in code order; each transition is
    one advance-count delta window (the rover lever's target).  This is the
    'measured k trajectory' of the 2026-07-11 action sessions, surfaced by
    default instead of hand-computed."""
    try:
        from c2.commands.rover_hints import _REG_IDX, _REG_CLASS, _CYCLE
    except Exception:
        return None
    pts: list[tuple[int, int]] = []
    for row in rows or ():
        o, r = row.get("o"), row.get("r")
        if o is None or r is None:
            continue
        oa, ra = o[3].lower(), r[3].lower()
        if oa.split(None, 1)[0] != ra.split(None, 1)[0]:
            continue
        po = _BYTE_REG_ONLY_RE.findall(oa)
        rc = _BYTE_REG_ONLY_RE.findall(ra)
        if not po or len(po) != len(rc):
            continue
        ks: set[int] = set()
        bad = False
        for a, b in zip(po, rc):
            if _REG_CLASS.get(a) != "byte" or _REG_CLASS.get(b) != "byte":
                bad = True
                break
            c = _CYCLE[a]
            k = (_REG_IDX[a] - _REG_IDX[b]) % c
            ks.add(k if k <= c // 2 else k - c)
        if bad or len(ks) != 1:
            continue
        pts.append((row["off"], ks.pop()))
    if not pts or not any(k for _o, k in pts):
        return None
    segs: list[list] = []          # [start, end, k, count]
    for off, k in pts:
        if segs and segs[-1][2] == k:
            segs[-1][1] = off
            segs[-1][3] += 1
        else:
            segs.append([off, off, k, 1])
    body = " | ".join(
        (f"+{a:04x}..+{b:04x} k={k:+d}\u00d7{n}" if n > 1 else
         f"+{a:04x} k={k:+d}")
        for a, b, k, n in segs)
    return ("k-map (byte sites, code order; k = advances RC's cursor is "
            "BEHIND PS; each k-transition = one delta window): " + body)


def detect(func: str, hints, *, file: str | None = None,
           ps_insns=None, rows=None) -> Optional[ByteSeatVerdict]:
    pairs = _byte_swap_pairs(hints)
    if not pairs:
        return None

    swapped = {r for p in pairs for r in p}
    parents = ({_PARENT[r] for r in swapped if r in _PARENT}
               | {_PARENT_W[r] for r in swapped if r in _PARENT_W})
    pair_s = ", ".join(f"PS {a}\u2194RC {b}" for a, b in sorted(set(pairs)))

    # ── static signals (always available) ──────────────────────────────
    rule127_regs: list[str] = []
    widen: list[str] | None = None
    try:
        from c2.commands import al_squat_hints
        rule127_regs = al_squat_hints._ps_copy_and_srcs(ps_insns)
        widen = al_squat_hints._int_widen_candidate(func, file)
    except Exception:
        pass
    dwswaps = _dword_swap_pairs(hints)
    collateral_static = any(
        a in _PARENT and b in _PARENT
        and frozenset((_PARENT[a], _PARENT[b])) in dwswaps
        for a, b in pairs)

    # ── trace upgrade (regclass + GiveBestReg reason) ───────────────────
    byte_confs: list = []
    dword_parent_confs: list = []
    gb_reasons: set[str] = set()
    have_trace = False
    try:
        from c2.commands.regalloc_hints import _lookup
        from c2.commands import gb_hints
        rt, _cost, _base = _lookup(func, file)
        allocs = (rt or {}).get("alloc") or []
        if allocs:
            have_trace = True
            byte_confs = [a for a in allocs
                          if a.get("regclass_name") == "byte"
                          and (a.get("reg_name") or "").lower() in swapped]
            dword_parent_confs = [a for a in allocs
                                  if a.get("regclass_name") in ("dword", "word")
                                  and (a.get("reg_name") or "").lower() in parents]
            gb_reasons = {e.reason for e in
                          gb_hints.detect(rt, {r.upper() for r in swapped})}
    except Exception:
        pass

    confidence = "trace" if have_trace else "static"
    lines: list[str] = []

    def _verdict(case: str, head: str) -> ByteSeatVerdict:
        lines.insert(0, f"Byte-seat = CASE {case} [{confidence}] ({pair_s}): {head}")
        return ByteSeatVerdict(func, case, confidence, lines)

    # ── ladder, most-specific first ─────────────────────────────────────
    # C: Rule 127 -- PS re-extend signature is asm-proven, highest specificity.
    if rule127_regs:
        lines.append(
            "Rule 127 (rover-seated CSE): PS re-extends the byte from "
            f"{','.join(rule127_regs)} via `mov al,<reg>; and eax,0xff` -- "
            "its value is a FindRegister rover pick (i86ldstr.c:130), not a "
            "GiveBestReg conflict.  LEVER: delete the named byte local and "
            "write the EXPRESSION TWICE (e.g. `if (bm[i+1]) f(bm[i+1],0);`) -- "
            "the commoned load takes the next byte-rover slot (battle_action "
            "316b -> exact).  The Rule 126 widen lever does NOT apply here.")
        return _verdict("C", "rover-seated CSE temp -- de-name the expression")

    # B: Rule 126 -- bare-AND uchar locals (genuine byte conflict masked off A).
    genuine_byte = bool(byte_confs) or (not have_trace and not collateral_static)
    if widen and genuine_byte:
        lines.append(
            "Rule 126 (AL-squat masking): bare-AND byte-mask shape, no shifts.  "
            f"LEVER: widen the `unsigned char` locals to `int` ({', '.join(widen[:6])}) "
            "-- the value leaves the ByteRegs path for DoubleRegs and escapes "
            "the NeighboursUse EAX-temp masking (regalloc.c:1157) that squats "
            "it in AL (get_education_ov_image 92b -> 44b).  Loads stay byte "
            "loads; VERIFY after -- it can regress siblings with an extra byte "
            "value.")
        return _verdict("B", "AL-squat masking -- widen the char locals to int")

    # A (collateral): no genuine byte conflict -- the byte register is the
    # low/high byte of a dword/word tie.  NOT byte-seat coloring.
    collateral_trace = have_trace and not byte_confs and bool(dword_parent_confs)

    # R: ROVER-picked byte scratch (Rule 163) -- checked BEFORE the
    # collateral verdicts (2026-07-12 fix: A used to shadow R whenever ANY
    # dword Reg-swap coexisted, e.g. action's 6c1b2f4c EBX<->ECX seat --
    # exactly the case Rule 163 was built for).  frx ground truth is DIRECT
    # per-site evidence: if the RC-side swapped byte regs not covered by a
    # GB byte conflict ARE byte-class FindRegister picks, those swaps are
    # rover CURSOR PARITY regardless of any coexisting dword tie.
    if have_trace:
        try:
            _bfr = [f for f in (rt or {}).get("fr", [])
                    if f.get("type_class", 99) in (0, 1) and f.get("truth")]
            _rover_picks = {f["truth"] for f in _bfr}
            _conf_regs = {(a.get("reg_name") or "").lower() for a in byte_confs}
            _rc_swapped = {b for _a, b in pairs}
            _uncovered = _rc_swapped - _conf_regs
        except Exception:
            _uncovered, _rover_picks = set(), set()
        if _uncovered and _uncovered <= _rover_picks:
            lines.append(
                "Rule 163 (rover-picked byte scratch): the RC side of "
                f"{len(_uncovered)}/{len(_rc_swapped)} swapped byte regs "
                "({}) is a FindRegister ROVER pick (frx ground truth), not "
                .format(",".join(sorted(_uncovered)))
                + "a GiveBestReg conflict -- the swap is byte-rover CURSOR "
                  "PARITY (advance count / except mask), steerable by the "
                  "rover levers: k-map PS picks vs fr['truth'] in walk "
                  "order (piecewise-constant k; each transition = one "
                  "advance-count delta window), then rover_fit the anchors "
                  "and census the window (`c2 spell --suggest`, load-fold / "
                  "Rule 121 / temp-SET).  Rule 133/161 'irreducible' "
                  "verdicts do NOT apply to rover sites."
                + ("  (A coexisting dword Reg swap exists -- "
                   "the DWORD seat is a separate lever; see Seat-chain.)"
                   if (collateral_static or dword_parent_confs) else ""))
            _km = _kmap_line(rows)
            if _km:
                lines.append(_km)
            return _verdict("R", "rover-picked byte scratch -- cursor "
                                 "parity, use the rover levers (NOT a GB tie)")

    # E: Rule 157 -- byte swap collateral to a dword swap that the VALIDATED
    # cascade replay search classifies as a genuine SAVINGS gap (not an
    # equal-savings tie, not UNREACHABLE-masks, not an H2 unreliable tie).
    # Checked BEFORE the equal-savings collateral path so a savings-gap
    # collateral is E (permute can't move it), not A ("run permute").
    # cascade returns None when it can't decide (too many rows / suppressed)
    # -> we fall through and do NOT over-claim E.
    if collateral_static or collateral_trace or (have_trace and byte_confs):
        sav_pair = _cascade_savings_pair(func, hints, rows, file, parents)
        if sav_pair is not None:
            lines.append(
                f"Rule 157 (savings-short byte temp, {sav_pair}): the byte is "
                f"the low/high byte of the {sav_pair} dword swap, which the "
                "replay search classifies as a SAVINGS GAP (not an equal-"
                "savings tie) -- permute / decl-swap / Rule 28a/115 PROVABLY "
                "cannot move it (savings-major sort).  Needs a SAVINGS change "
                "on the RIVAL: Rule 156 (`= 0` instead of `= <provably-0 var>` "
                "drops a rival use), Rule 123 (merge a split temp), or "
                "de-invent a rival local -- `c2 triage <fn>`.  RAISING the "
                "byte instead is the WIDEN TRAP (its +1 use IS the divergence: "
                "explicit `& 0xff` = 2nd widen vs PS's shared in-place `and`).  "
                "INVERSE of Rule 156.  IRREDUCIBLE only when the rival's refs "
                "are all load-bearing (get_best_elastic_value: dir).")
            v = _verdict("E", f"savings-short byte temp (Rule 157) -- collateral "
                              f"to the {sav_pair} SAVINGS-gap swap; SAVINGS "
                              f"change needed (not permute)")
            v.savings_pair = sav_pair
            return v

    if collateral_static or collateral_trace:
        owners = ", ".join(sorted(parents))
        lines.append(
            f"Collateral to a wider Reg swap on {owners}: the byte register "
            "is the low/high byte of a dword/word equal-savings tie, NOT "
            "byte-seat coloring.  LEVER: the dword tie levers (Rule 28a / 115 "
            "/ 123, see the Regalloc/Merge lines).  If the `Cascade:` line says "
            "REACHABLE, screen with `c2 savings <fn> --flip VAR=REG --depth 2` "
            "(full sort+pick replay), then `c2 sweep <fn>` for the byte battery.")
        return _verdict("A", "collateral to a wider Reg swap -- use the 32-bit tie levers")

    # Genuine byte conflict -> D (inert) vs A (reorderable), split by the
    # GiveBestReg reason.  Rule 133 (inert) ONLY when the tie-break is dead
    # (list-order / forced); any `credit`/`given-tie-break` means the seat
    # WAS discriminated, so a reorder / Rule 123 merge can move it.
    if have_trace and byte_confs:
        if gb_reasons <= {"list-order", "forced"}:
            lines.append(
                "Rule 133 (inert byte tie): the byte value is a genuine "
                "GiveBestReg conflict, but the layer-3 tie-break is DEAD for "
                "bytes -- every byte register sub-registers an already-given "
                "dword, so HW_Subset(GivenRegisters, cand) holds for ALL "
                "candidates (10.0a tie-break VA 0x57ca1-0x57cc8) and ByteRegs "
                "list-order alone decides the seat.  SOURCE-IRREDUCIBLE: "
                "declaration/use-order "
                "levers (permute, decl-swap, Rule 28a/115) PROVABLY cannot "
                "move it.  Park it.")
            return _verdict("D", "inert byte tie (Rule 133) -- IRREDUCIBLE, do not reorder")
        # Rule 161 refinement (2026-07-09 gb-record study): when EVERY
        # swap-participating byte conflict is ANONYMOUS, the discriminator
        # (byte-granular occupancy = the gb sweep's start register, and/or
        # a CountRegMoves credit on an anon temp's range) has NO source
        # handle: decl swaps of NAMED byte locals provably move SLOT order,
        # not byte seats (2 corpus perturbation experiments), and statement
        # reorders were pair-sweep-exhausted (figure_go_to_target, 406
        # variants, all tie).  Only a byte-temp-SET change (name/inline a
        # byte value, byte-RMW form -- Rule 129/§10) can re-seed the
        # occupancy; if `c2 spell --suggest` hazard-rejects every set
        # change, certify.
        if byte_confs and all(not a.get("var") for a in byte_confs):
            lines.append(
                "Rule 161 (occupancy-pinned byte tie): every swap byte "
                f"conflict is ANONYMOUS ({len(byte_confs)} confs, reasons "
                f"{', '.join(sorted(gb_reasons))}); the seat = first "
                "non-excluded byte reg in AL,AH,DL,DH,BL,BH,CL,CH order "
                "(exclusions = OVERLAPPING anon byte ranges; credits = MOVs "
                "in anon ranges; GivenRegisters saturated late-function).  "
                "Decl/use reorders have NO handle (named-byte decl swaps "
                "move SLOTS, not seats -- corpus-proven).  LEVER: byte-temp-"
                "SET change only (name/inline a byte value, byte-RMW form); "
                "`c2 spell --suggest` empty => certified residue.")
            return _verdict("A2", "occupancy-pinned anon byte tie (Rule 161) "
                                  "-- temp-SET levers only, do NOT reorder")
        lines.append(
            "Reorderable byte tie: the byte conflict's seat was discriminated "
            f"by GiveBestReg ({', '.join(sorted(gb_reasons))}), NOT the dead "
            "byte tie-break -- so it is NOT the irreducible Rule 133 case.  "
            "LEVER: a Rule 123 split-temp merge (see the Merge line) or a "
            "Rule 28a/115 reorder; screen with `c2 savings <fn> --flip "
            "VAR=REG --depth 2` / `c2 sweep <fn>` if the Cascade line "
            "says REACHABLE.")
        return _verdict("A", "reorderable byte tie -- Rule 123 merge / 28a / 115")

    # Static fallback: cannot tell A from D without the trace.
    lines.append(
        "byte-register identity swap with no asm/AST lever signature.  "
        "Either CASE A (low byte of a dword tie -- reorderable) or CASE D "
        "(inert byte tie -- irreducible).  Run `c2 regtrace " + func +
        " --explain` for the byte-vs-dword ground truth (regclass + the GB "
        "line's [list-order]/[credit] verdict).")
    return _verdict("?", "byte swap -- run regtrace to split CASE A vs CASE D")


def render_lines(v: ByteSeatVerdict) -> list[str]:
    return v.lines
