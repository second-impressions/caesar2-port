"""PS-vs-RC register *seat* reconstruction (the value-aligned allocation diff).

The allocator is deterministic, so a PS↔RC register-identity swap is a
property of the IL we feed it, not of the allocator.  ``regtrace`` runs the
real allocator on *our* (RC) source and yields a value→register map; what was
missing is the symmetric **PS** seat map, reconstructed from PS.EXE's own asm.

Core idea (cheap, asm-only, no container): the diff already aligns PS and RC
instructions.  In a structurally-matching aligned row (same mnemonic, same
operand *shapes*) a register operand at position *k* holds the **same abstract
value** on both sides — the instruction computes the same thing, just with a
different register choice.  Tallying ``(rc_reg_family → ps_reg_family)`` over
all such operands recovers the register permutation between the two
allocations; the dominant non-identity entries are the seat swaps, and the
earliest divergent row is the cascade root.

``register_correspondence`` / ``seat_diff`` are the asm-only core (used by
``decomp-verify --json`` across the whole corpus).  ``regtrace --vs-ps`` joins
the result with regtrace's value→register table to *name* the swapped values
and report whether the swap is a savings/shape difference or an
equal-savings ConfBefore tie (the steerable tie-break).
"""

from __future__ import annotations
from typing import Optional

import re
from collections import Counter, defaultdict

# ---- register-family normalisation -----------------------------------------
# Collapse a register token to its 32-bit family so AL/AX/EAX all read as "A".
_FAM: dict[str, str] = {}
for _f, _subs in {
    "A": "eax ax al ah", "B": "ebx bx bl bh", "C": "ecx cx cl ch",
    "D": "edx dx dl dh", "SI": "esi si", "DI": "edi di",
    "BP": "ebp bp", "SP": "esp sp",
}.items():
    for _s in _subs.split():
        _FAM[_s] = _f

_FAM_TO_E = {"A": "EAX", "B": "EBX", "C": "ECX", "D": "EDX",
             "SI": "ESI", "DI": "EDI", "BP": "EBP", "SP": "ESP"}

_REG_RE = re.compile(r"\b(e?[abcd]x|[abcd][lh]|e?(?:si|di|bp|sp))\b")


def fam_to_reg(fam: str) -> str:
    """Family letter → canonical 32-bit register name (for display)."""
    return _FAM_TO_E.get(fam, fam)


def reg_to_fam(reg: str) -> str:
    """Register name (any width) → family letter."""
    return _FAM.get(reg.strip().lower(), reg.strip().upper())


def _toks(asm: str) -> tuple[str, list[str]]:
    """(mnemonic, [operand strings]) from a capstone op-string."""
    asm = (asm or "").strip()
    if not asm:
        return "", []
    parts = asm.split(None, 1)
    mn = parts[0]
    ops = [o.strip() for o in parts[1].split(",")] if len(parts) > 1 else []
    return mn, ops


def _op_shape(op: str):
    """Classify an operand:
        ('reg', fam) | ('mem', (fams…)) | ('imm',) | ('other', text)
    Memory operands keep only the register families inside the brackets so the
    masked global address (PS 0x72dc4 vs RC 0x2c731) is ignored."""
    op = op.strip()
    if op[:5] in ("dword", "byte ", "word ") or "[" in op:
        regs = tuple(
            _FAM[m.group(1)] for m in _REG_RE.finditer(op) if m.group(1) in _FAM
        )
        return ("mem", regs)
    if op in _FAM:
        return ("reg", _FAM[op])
    if re.fullmatch(r"-?0x[0-9a-f]+|-?\d+", op):
        return ("imm",)
    return ("other", op)


def _same_structure(pops: list[str], rops: list[str]) -> bool:
    if len(pops) != len(rops):
        return False
    for a, b in zip(pops, rops):
        if _op_shape(a)[0] != _op_shape(b)[0]:
            return False
    return True


def _row_asm(row: dict, side: str) -> str:
    """Pull the op-string from either the json row form ({'ps':{'asm':…}}) or
    the internal _build_diff_rows form ({'o': (off,sz,raw,'asm')})."""
    sd = row.get(side)
    if isinstance(sd, dict):
        return sd.get("asm", "") or ""
    key = "o" if side == "ps" else "r"
    ins = row.get(key)
    if ins is not None:
        try:
            return ins[3] or ""
        except (IndexError, TypeError):
            return ""
    return ""


# ---- the core --------------------------------------------------------------
def register_correspondence(rows: list[dict]):
    """Tally (rc_fam → ps_fam) over structurally-matching aligned operand slots.

    Returns (per_rc, divergences):
      per_rc       : {rc_fam: Counter(ps_fam → n)}
      divergences  : [(off, ln, rc_fam, ps_fam, ps_asm, rc_asm)] for every
                     operand slot whose seat differs, in offset order.
    """
    per_rc: dict[str, Counter] = defaultdict(Counter)
    divergences: list[tuple] = []
    for r in rows:
        ps = _row_asm(r, "ps")
        rc = _row_asm(r, "rc")
        if not ps or not rc:
            continue
        pmn, pops = _toks(ps)
        rmn, rops = _toks(rc)
        if pmn != rmn or not _same_structure(pops, rops):
            continue
        off = r.get("off", 0)
        ln = r.get("ln")
        for a, b in zip(pops, rops):
            sa, sb = _op_shape(a), _op_shape(b)
            if sa[0] == "reg" and sb[0] == "reg":
                per_rc[sb[1]][sa[1]] += 1
                if sa[1] != sb[1]:
                    divergences.append((off, ln, sb[1], sa[1], ps, rc))
            elif sa[0] == "mem" and sb[0] == "mem":
                for fa, fb in zip(sa[1], sb[1]):
                    per_rc[fb][fa] += 1
                    if fa != fb:
                        divergences.append((off, ln, fb, fa, ps, rc))
    divergences.sort(key=lambda d: (d[0], d[1] if d[1] is not None else 1 << 30))
    return per_rc, divergences


def seat_diff(rows: list[dict], *, margin: float = 0.7, min_support: int = 2):
    """Structured PS↔RC seat reconstruction from aligned diff rows.

    Returns a dict:
      verdict      : "clean" | "swap" | "ambiguous" | "empty"
      coverage     : total register-operand observations
      swaps        : [{rc, ps, support, confidence}]  (confident non-identity)
      first_divergence : {off, ln, rc, ps, ps_asm, rc_asm} | None
      map          : {rc_fam: ps_fam}   (dominant; display as regs via fam_to_reg)
    A byte-exact / identically-allocated function ⇒ "clean" (no swaps).
    """
    per_rc, divergences = register_correspondence(rows)
    coverage = sum(sum(c.values()) for c in per_rc.values())
    if not per_rc:
        return {"verdict": "empty", "coverage": 0, "swaps": [],
                "first_divergence": None, "map": {}}

    swaps = []
    ambiguous = False
    fam_map: dict[str, str] = {}
    for rcf, c in per_rc.items():
        total = sum(c.values())
        psf, n = c.most_common(1)[0]
        fam_map[rcf] = psf
        conf = n / total if total else 0.0
        if psf != rcf:
            if n >= min_support and conf >= margin:
                swaps.append({"rc": fam_to_reg(rcf), "ps": fam_to_reg(psf),
                              "support": n, "confidence": round(conf, 3)})
            else:
                # a dominant-but-weak non-identity entry: low confidence
                ambiguous = True
        elif conf < margin and total >= min_support:
            # identity wins but not cleanly (a rival family is close)
            ambiguous = True

    first = None
    if divergences:
        off, ln, rcf, psf, ps, rc = divergences[0]
        first = {"off": off, "ln": ln, "rc": fam_to_reg(rcf),
                 "ps": fam_to_reg(psf), "ps_asm": ps, "rc_asm": rc}

    if swaps:
        verdict = "swap"
    elif ambiguous:
        verdict = "ambiguous"
    else:
        verdict = "clean"
    swaps.sort(key=lambda s: -s["support"])
    return {"verdict": verdict, "coverage": coverage, "swaps": swaps,
            "first_divergence": first, "map": fam_map}


# ---- value-aligned TYPE / WIDTH diff (gap #3) -------------------------------
# The allocator is deterministic, so a width/signedness divergence in the
# aligned asm is a SOURCE type difference (a local that is int where PS made it
# unsigned char / signed char / unsigned int), not codegen noise.  These are
# the levers the register-seat diff is blind to -- and the ones that actually
# moved cap_land_value (uint size, signed cl -> jge, byte rank_sum).

# signed Jcc <-> its unsigned twin (SAME relational direction): the compared
# value is signed on one side, unsigned on the other.
_SIGNED_TWIN = {
    "jg": "ja", "jge": "jae", "jl": "jb", "jle": "jbe",
    "ja": "jg", "jae": "jge", "jb": "jl", "jbe": "jle",
}
_SIGNED_JCC = {"jg", "jge", "jl", "jle"}

_REG_W = {}
for _w, _names in {1: "al ah bl bh cl ch dl dh", 2: "ax bx cx dx si di bp sp",
                   4: "eax ebx ecx edx esi edi ebp esp"}.items():
    for _nm in _names.split():
        _REG_W[_nm] = _w
_MEM_W = {"byte": 1, "word": 2, "dword": 4}
# instructions whose operands legitimately differ in width (don't flag those)
_WIDTH_EXEMPT = {"movzx", "movsx", "cbw", "cwde", "cdq", "cwd", "lea",
                 "push", "pop", "call", "ret"}


def _op_data_width(op: str):
    """Data width (1/2/4) of an operand, or None (imm / no size)."""
    op = op.strip()
    if "[" in op or op[:5] in ("dword", "byte ", "word "):
        head = op.split(None, 1)[0]
        return _MEM_W.get(head)            # only when a size prefix is present
    return _REG_W.get(op.lower())


_SIGNED_FORMS = {"jcc": _SIGNED_JCC, "ext": {"movsx"}, "shift": {"sar"}}
_UNSIGNED_FORMS = {"jcc": {"ja", "jae", "jb", "jbe"}, "ext": {"movzx"},
                   "shift": {"shr"}}
_FAMILY_LABEL = {"jcc": "signed branch (Jcc) vs unsigned",
                 "ext": "sign-extend (movsx) vs zero-extend (movzx)",
                 "shift": "arithmetic (sar) vs logical (shr) shift"}


def type_width_diff(rows: list[dict]) -> dict:
    """Value-aligned PS<->RC type/width divergences from the aligned diff rows.

    The signedness signals (Jcc / movsx-movzx / sar-shr) are counted
    ALIGNMENT-INDEPENDENTLY (a multiset delta per side) -- robust to the
    diff drift that hides a late signed/unsigned branch -- and ALSO located
    per-row when PS and RC still align there.  A signedness imbalance means a
    local is signed on one side and unsigned on the other (PS's form names
    which: jge => signed char/int; jae => unsigned).  The byte<->dword width
    signal is restricted to SAME-register-family operands AND structurally
    matched rows (a clean width diff on a same-seated value, e.g. PS `al` vs
    RC `eax`) so register-identity swaps and capstone desyncs don't
    masquerade as width bugs.

    Soundness: byte-exact => identical asm => 0 (validated 1380/1384 on the
    corpus; the ~4 residual are a capstone DESYNC on functions with an
    embedded jump table whose relocated entries decode differently PS vs RC,
    inflating one side's Jcc count by 1 -- a rare artifact, not a width bug).

    Returns:
      signedness : [{family, ps_signed, rc_signed, delta, label, examples}]
      width      : [{off, ln, ps_width, rc_width, ps_asm, rc_asm}]
      count      : total signedness imbalance + width hits
    A byte-exact function yields none.
    """
    # ---- alignment-independent signedness multiset (per side) --------------
    ps_cnt = {k: {"s": 0, "u": 0} for k in _SIGNED_FORMS}
    rc_cnt = {k: {"s": 0, "u": 0} for k in _SIGNED_FORMS}
    located: dict[str, list] = {k: [] for k in _SIGNED_FORMS}
    width: list[dict] = []

    def _tally(asm, cnt):
        mn = _toks(asm)[0]
        for fam in _SIGNED_FORMS:
            if mn in _SIGNED_FORMS[fam]:
                cnt[fam]["s"] += 1
            elif mn in _UNSIGNED_FORMS[fam]:
                cnt[fam]["u"] += 1

    for r in rows:
        ps = _row_asm(r, "ps")
        rc = _row_asm(r, "rc")
        if ps:
            _tally(ps, ps_cnt)
        if rc:
            _tally(rc, rc_cnt)
        if not ps or not rc:
            continue
        pmn, pops = _toks(ps)
        rmn, rops = _toks(rc)
        off, ln = r.get("off", 0), r.get("ln")
        rec = {"off": off, "ln": ln, "ps_asm": ps, "rc_asm": rc}
        # located signedness hit (a clean aligned signed<->unsigned twin)
        for fam in _SIGNED_FORMS:
            ps_s = pmn in _SIGNED_FORMS[fam] or pmn in _UNSIGNED_FORMS[fam]
            rc_s = rmn in _SIGNED_FORMS[fam] or rmn in _UNSIGNED_FORMS[fam]
            if ps_s and rc_s and (pmn in _SIGNED_FORMS[fam]) != (
                    rmn in _SIGNED_FORMS[fam]):
                located[fam].append({**rec, "ps_form": pmn, "rc_form": rmn,
                                     "ps_signed": pmn in _SIGNED_FORMS[fam]})
        # same-family byte<->dword width (not a register swap).  Require the
        # WHOLE instruction to be structurally matched (same op shapes) so a
        # capstone desync that pairs unrelated rows can't masquerade as width.
        if (pmn == rmn and pmn not in _WIDTH_EXEMPT
                and _same_structure(pops, rops)):
            for a, b in zip(pops, rops):
                sa, sb = _op_shape(a), _op_shape(b)
                if sa[0] == "reg" and sb[0] == "reg" and sa[1] == sb[1]:
                    wa, wb = _op_data_width(a), _op_data_width(b)
                    if wa and wb and wa != wb:
                        width.append({**rec, "ps_width": wa, "rc_width": wb})
                        break

    signedness = []
    for fam in _SIGNED_FORMS:
        d = ps_cnt[fam]["s"] - rc_cnt[fam]["s"]
        if d != 0:
            signedness.append({
                "family": fam, "label": _FAMILY_LABEL[fam],
                "ps_signed": ps_cnt[fam]["s"], "rc_signed": rc_cnt[fam]["s"],
                "ps_unsigned": ps_cnt[fam]["u"], "rc_unsigned": rc_cnt[fam]["u"],
                "delta": d, "examples": located[fam][:3],
            })
    count = sum(abs(s["delta"]) for s in signedness) + len(width)
    # goal-post denominator: the number of type-comparable ops in the
    # function (signed+unsigned branches/exts/shifts on the larger side).
    total = sum(max(ps_cnt[f]["s"] + ps_cnt[f]["u"],
                    rc_cnt[f]["s"] + rc_cnt[f]["u"]) for f in _SIGNED_FORMS)
    return {"signedness": signedness, "width": width, "count": count,
            "total": total}


# ---- per-value SPILL / frame diff (gap #4) ---------------------------------
# A frame-size divergence ("PS spills more") is deterministic too: it means our
# IL keeps fewer values live across calls than PS's (we inlined/narrowed temps
# PS held as named stack locals).  Reconstruct each side's spill SLOT profile
# from the asm -- the `sub esp,N` frame + the distinct `[esp+K]` slots and
# their widths -- and diff them.  Names come from regtrace as an enrichment.

_SUB_ESP_RE = re.compile(r"\bsub\s+esp,\s*(0x[0-9a-f]+|\d+)")
_ESP_SLOT_RE = re.compile(r"\[esp(?:\s*\+\s*(0x[0-9a-f]+|\d+))?\]")


def _slot_width(asm: str, slot_text: str) -> int:
    """byte/word/dword ptr size of the `[esp+K]` operand in this insn."""
    i = asm.find(slot_text)
    pre = asm[:i].rsplit(",", 1)[-1] + asm[:i].split()[-1] if i > 0 else ""
    seg = asm[max(0, i - 12):i]
    if "byte" in seg:
        return 1
    if "word" in seg and "dword" not in seg:
        return 2
    return 4


def _spill_profile(rows: list[dict], side: str) -> dict:
    """{frame, slots:{off:width}} from one side's asm across the diff rows."""
    frame = 0
    slots: dict[int, int] = {}
    for r in rows:
        asm = _row_asm(r, side)
        if not asm:
            continue
        m = _SUB_ESP_RE.search(asm)
        if m and not frame:
            frame = int(m.group(1), 16) if m.group(1).startswith("0x") \
                else int(m.group(1))
        for sm in _ESP_SLOT_RE.finditer(asm):
            off = sm.group(1)
            off = (int(off, 16) if off and off.startswith("0x")
                   else int(off) if off else 0)
            w = _slot_width(asm, sm.group(0))
            slots[off] = max(slots.get(off, 0), w)
    return {"frame": frame, "slots": slots}


def spill_diff(rows: list[dict]) -> dict:
    """PS<->RC stack-frame / spill-slot divergence (gap #4).

    Reconstructs each side's frame size + the distinct `[esp+K]` spill slots
    (and their byte/dword widths) from the asm, and reports the delta.  A
    positive `slot_delta` means PS spills more values than we do -- our IL
    keeps them in registers (we inlined/narrowed temps PS held as named stack
    locals); the source lever is to give those values PS's width/live-range
    (cross-link the type/width diff).  Byte-exact => identical => no delta.

    Returns {ps_frame, rc_frame, ps_slots, rc_slots, ps_byte_slots,
             rc_byte_slots, slot_delta, direction}.
    """
    ps = _spill_profile(rows, "ps")
    rc = _spill_profile(rows, "rc")
    ps_n, rc_n = len(ps["slots"]), len(rc["slots"])
    ps_b = sum(1 for w in ps["slots"].values() if w == 1)
    rc_b = sum(1 for w in rc["slots"].values() if w == 1)
    delta = ps_n - rc_n
    direction = ("ps_spills_more" if delta > 0 else
                 "rc_spills_more" if delta < 0 else "equal")
    return {"ps_frame": ps["frame"], "rc_frame": rc["frame"],
            "ps_slots": ps_n, "rc_slots": rc_n,
            "ps_byte_slots": ps_b, "rc_byte_slots": rc_b,
            "slot_delta": delta, "direction": direction}


# ---- composite SHAPE DISTANCE (gap #5 core) --------------------------------
# A decomposed distance-to-PS: register seats + type widths + spilling, plus
# the raw byte diff.  The `shape` subtotal (seat+width+spill) is the
# byte-independent shape distance -- the operationalisation of "byte-exactness
# is the ORACLE, not the scoreboard": an edit that DROPS `shape` is
# PS-faithful even if `bytes` rises (keep it), and one that RAISES `shape`
# moved away from PS regardless of the byte count.  shape==0 means the
# recovered shape matches PS (seats/types/frame agree) -- any residue is a
# pure regalloc tie-break / encoding.

def seat_distance(seat: dict) -> int:
    """Register-identity divergence count from a seat_diff result."""
    if not seat:
        return 0
    n = len(seat.get("swaps") or [])
    if not n and seat.get("first_divergence"):
        n = 1                         # a localized one-off seat difference
    return n


def shape_distance_from(seat: dict | None, width: dict | None,
                        spill: dict | None, byte_diff: int = 0,
                        ir_divergent: int = 0, ir_max: int = 0,
                        islands: int | None = None) -> dict:
    """Compose the LAYERED distance-to-PS from the already-computed sub-diffs
    (cheap; no row re-walk).  Layers, in fix-order:
        ir     -- binir IR-tree divergent source-lines (wrong OPS / control
                  flow -- the highest layer; fix the source shape first)
        width  -- type/signedness divergences (wrong local type)
        spill  -- frame / live-range divergence (|slot delta|)
        seat   -- register-identity divergence (often a sub-source tie)
    `shape` = ir+width+spill+seat is the byte-INDEPENDENT source distance;
    `bytes` is the oracle (done == 0).  An edit that drops `shape` is
    PS-faithful even if `bytes` rose.

    ``islands`` is the dual-marks run-ledger island count (the ir layer's
    fine-grained unit: one island = one local statement-shape divergence;
    0 = regalloc_pure; None = ledger unavailable, ir fell back to the
    byte-diff-aligned binir count)."""
    s = seat_distance(seat or {})
    w = (width or {}).get("count", 0)
    sp = spill or {}
    p = (abs(sp.get("slot_delta", 0))
         if sp.get("ps_frame") != sp.get("rc_frame") else 0)
    ir = max(0, int(ir_divergent or 0))
    shape = ir + w + p + s
    # fix_next = the highest-priority NON-ZERO layer (the issue to work first);
    # lets an agent prioritise / pick functions by a SPECIFIC residue type.
    layers = (("ir", ir), ("width", w), ("spill", p), ("seat", s))
    fix_next = next((nm for nm, v in layers if v),
                    "regalloc" if byte_diff else "done")
    # goal-post denominators (the per-layer UPPER BOUND, which depends on the
    # function's shape): N/T reads "N of T divergent", so 14/62 is moderate
    # but 14/16 is severe.  0 means "no scale recorded".
    spd = spill or {}
    ir_total = max(0, int(ir_max or 0))
    width_total = (width or {}).get("total", 0)
    spill_total = max(spd.get("ps_slots", 0), spd.get("rc_slots", 0))
    seat_total = len((seat or {}).get("map", {}))
    # NOTE: `shape` is the raw SUM of the four layers -- a mixed-unit
    # aggregate (IR lines + type-ops + slots + families), so it has no honest
    # single goal-post and is NOT shown as a headline.  It is kept only as a
    # coarse monotonic key for sorting/ranking.  The interpretable figures are
    # the per-layer N/T and `fix_next`.
    return {"ir": ir, "width": w, "spill": p, "seat": s, "shape": shape,
            "bytes": byte_diff, "total": shape + byte_diff,
            "fix_next": fix_next, "islands": islands,
            "ir_total": ir_total, "width_total": width_total,
            "spill_total": spill_total, "seat_total": seat_total}


def fmt_shape_layers(sd: dict) -> str:
    """`ir N/T (isl K) · width N/T · spill N/T · seat N/T` -- each layer
    with its goal-post denominator (the shape-dependent upper bound) when
    known.  ``isl K`` = the run-ledger island count (the ir layer's
    fine-grained unit; 0 = regalloc_pure; omitted when the ledger was
    unavailable)."""
    def _lyr(name: str) -> str:
        n = sd.get(name, 0)
        t = sd.get(name + "_total", 0)
        cell = f"{name} {n}/{t}" if t else f"{name} {n}"
        if name == "ir" and sd.get("islands") is not None:
            cell += f" (isl {sd['islands']})"
        return cell
    return " · ".join(_lyr(x) for x in ("ir", "width", "spill", "seat"))


def fmt_shape_cell(sd: Optional[dict]) -> str:
    """Compact per-function shape-distance tag for inline one-liners:
    ``ir{N}/{T}[·i{K}][+k]→fix_next`` -- the IR-divergence headline, the
    run-ledger island count ``i{K}`` when available (the ir layer's
    fine-grained unit; ``i0`` = regalloc_pure), a ``+k`` count of the
    lower layers (width/spill/seat) also diverging, and the next layer to
    fix.  This is the per-function JUDGE metric (in place of a byte-diff
    count).  Empty string when ``sd`` is falsy."""
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


def shape_distance(rows: list[dict], byte_diff: int = 0) -> dict:
    """Compute the layered shape distance directly from the aligned diff rows
    (includes the binir IR-tree divergence)."""
    from c2.commands.binir_shape_hints import detect as _binir_detect
    bh = _binir_detect(rows)
    return shape_distance_from(seat_diff(rows), type_width_diff(rows),
                               spill_diff(rows), byte_diff,
                               bh.lines_divergent, bh.lines_compared)
