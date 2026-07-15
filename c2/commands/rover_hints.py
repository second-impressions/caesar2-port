"""RISCify push/load-store ROVER lever for decomp-verify.

A register-identity swap whose divergent registers are RISCified memory picks
is NOT a savings / last-use / decl-order tie.  Two patterns are picks:
  * a LOAD `mov <reg>,[global]` (incl. the `mov reg,[global]; push reg` of a call
    argument);
  * a constant STORE `xor reg,reg; mov [global],reg` (Watcom RISCifies the
    *result* of `MOV N_MEMORY <- const`, so the zero/const lands in a rover reg
    -- message.c's loop-tail `message_goto_ptr = 0`).
Those registers are
picks of the WATCOM 10.0a RISCify rover ``FindRegister`` (owp4v1
``bld/cg/intel/c/i86ldstr.c``; binary va 0x62a29).  There are THREE independent,
persistent cursors, one per operand width:

    byte  (char)  RoverByte   over ByteRegs   = AL,AH,DL,DH,BL,BH,CL,CH
    word  (short) RoverWord   over WordRegs   = AX,DX,BX,CX,SI,DI
    dword (int/*) RoverDouble over DoubleRegs = EAX,EDX,EBX,ECX,ESI,EDI,EBP

EBP IS a normal pick at PS's flags (``-mf -4r -s`` -> no frame pointer); only
ESP and the reserved 0x40fff800 band are permanently excepted.  (Empirically
confirmed: pm_map1.c trace shows 39 EBP picks vs 21 EAX.)  Each cursor is
advanced once per RISCified op of that width, gated by ``except``
(= live | zap | result.reg), and PERSISTS across the routine.  PS's choice is the
cursor a few steps further along (or behind) at the diverging op.

To steer it you change, BYTE-NEUTRALLY, the count/order/liveness of RISCified ops
of that width *before* the diverging op:

  * +k advance -> split a basic block before it so the compiler materialises k
    extra COALESCED (byte-invisible) loads.  The most reliable faithful trick is
    a dead / duplicated branch: push a store shared by an if/else INTO BOTH ARMS,
    or keep a never-taken ``if (x == K)`` the optimiser cannot fold.  (Solved
    start_smacking: ``smk_ref_wi = 0x28`` in both arms of the dead inner
    ``if (smk_height==0xc8)`` -> +1 -> EDX/EBX/ECX became EBX/ECX/ESI.)
  * -k advance -> merge blocks / CSE a redundant load / pass an
    array-or-immediate arg (no load) instead of a memory VARIABLE (a load).
  * the shift SELF-HEALS at the next op whose ``except`` wraps both cursors to the
    same register, so only the targeted ops move -- inject as close as possible.

Model + simulator: watcom10.0a ``docs/rover-model.md`` + ``tools/rover_sim.py``,
search harness ``tools/rover_search.py``.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field

# The three RISCify rover arrays (Mapping A), 0-terminated.  EBP (0x400) IS
# pickable in dword (no frame pointer at -mf -4r -s); only ESP (0x800) and the
# reserved 0x40fff800 band are permanently excepted.  See the _DWORD_REGS note.
_REGS = {
    "byte":  [0x2, 0x1, 0x80, 0x40, 0x8, 0x4, 0x20, 0x10, 0],        # AL,AH,DL,DH,BL,BH,CL,CH (OW v1 cgi86reg.h: H = LOW bit)
    "word":  [0x3, 0xc0, 0xc, 0x30, 0x100, 0x200, 0],                # AX,DX,BX,CX,SI,DI
    "dword": [0x1000003, 0x80000c0, 0x200000c, 0x4000030,
              0x10000100, 0x20000200, 0x400, 0x800, 0],              # EAX,EDX,EBX,ECX,ESI,EDI,EBP,ESP
}
# Byte-pair orientation is the classic landmine (H = the LOW bit of each
# pair: AH=0x1, AL=0x2, BH=0x4, BL=0x8, ...).  This table was pairwise-
# SWAPPED for B/C/D until 2026-07-11 -- every byte-class Rover hint named
# bl/bh, cl/ch, dl/dh backwards, and the PS-side name->mask parse inverted
# byte k-levers.  Proven against emitted bytes via the frx ground-truth
# probe on action.c (mask 0x40 emits `dh`, 0x8 emits `bl`, ...).  Derive
# from the ONE corrected source of truth instead of restating it.
from c2.regalloc.reglists import REG_NAME as _REG_NAME_UC
_NAME = {m: n.lower() for m, n in _REG_NAME_UC.items()}
_NAME[0] = "-"
# reg name -> (class, array index, cycle length over SELECTABLE entries).
# ESP (0x800) is a member of DoubleRegs but is PERMANENTLY excepted (BASE_EXCEPT
# covers 0x800), so the rover never selects it -- it is transparent to the cursor
# and must NOT count as a cycle step.  Excluding it makes the dword cycle 7
# (EAX,EDX,EBX,ECX,ESI,EDI,EBP), not 8; otherwise any cursor wrap whose path
# crosses ESP reports its shift one step too large (e.g. RC=ebp->PS=eax is a true
# +1 but came out +2).  EBP (0x400) is NOT excepted (no frame pointer at -mf -4r
# -s) so it stays in the cycle.  (byte/word arrays have no always-excepted member.)
_ALWAYS_EXCEPT = {0x800}  # esp
_REG_CLASS, _REG_IDX, _CYCLE = {}, {}, {}
for _cls, _arr in _REGS.items():
    _pick = [m for m in _arr if m and m not in _ALWAYS_EXCEPT]
    for _i, _m in enumerate(_pick):
        _nm = _NAME[_m]
        _REG_CLASS[_nm] = _cls
        _REG_IDX[_nm] = _i
        _CYCLE[_nm] = len(_pick)
_CALLEE = ("ebx", "ecx", "edx", "esi", "edi", "ebp")
_BYTE_REGS = {"al", "ah", "bl", "bh", "cl", "ch", "dl", "dh"}
_WORD_REGS = {"ax", "bx", "cx", "dx", "si", "di"}
_DWORD_REGS = {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp"}
# NB: EBP IS pickable by RoverDouble when the routine has no frame pointer
# (update_time RC: `mov ebp,[g]` guard-RMW scratch); ESP never.
_OP_PARM = 0x2a


@dataclass
class RoverHint:
    cls: str           # byte | word | dword
    ps_regs: list      # PS rover picks, code order
    rc_regs: list      # RC rover picks, code order
    shift: int | None  # uniform cursor delta (RC->PS), array steps, or None
    advances: list = field(default_factory=list)  # fr-confirmed k's that reproduce PS
    inject_at: int | None = None
    diverge: tuple | None = None  # (source_line, rc_reg, ps_reg) of 1st diverging op
    summary: str = ""
    lever: str = ""


# ---------------------------------------------------------------- disasm side
def _callee_pushes(insns) -> list:
    """Leading callee-save pushes (the prologue set), skipping a __CHK probe."""
    start = 0
    if (len(insns) >= 2 and insns[0][3].startswith("push ")
            and insns[1][3].startswith("call ")):
        op = insns[0][3].split(None, 1)[1] if len(insns[0][3].split()) > 1 else ""
        if op[:1].isdigit() or op.startswith("0x"):
            start = 2
    out = []
    for ins in insns[start:]:
        p = ins[3].split(None, 1)
        if not p or p[0] != "push":
            break
        if len(p) > 1 and p[1] in _CALLEE:
            out.append(p[1])
        else:
            break
    return out


def _cls_of_tc(tc):
    if tc < 2:
        return "byte"
    if tc < 4:
        return "word"
    if tc <= 5:
        return "dword"
    return None


def _rover_loads(insns, cls):
    """Rover register picks of class ``cls`` from `mov <reg>,[<bare global>]`
    loads, code order.  For dword, restrict to scratches that are PUSHed before
    the next call (the robust call-arg signal); for byte/word the load itself is
    the pick."""
    want = {"byte": _BYTE_REGS, "word": _WORD_REGS, "dword": _DWORD_REGS}[cls]
    out, n = [], len(insns)
    for i, ins in enumerate(insns):
        m = re.match(r"mov (e?[a-d][xlh]|e?[sd]i|si|di), "
                     r"(?:(?:byte|word|dword) ptr )?\[([^\]]+)\]$", ins[3])
        if not m:
            continue
        reg, inside = m.group(1), m.group(2)
        if reg not in want or any(c in inside for c in "+*-"):
            continue
        if cls == "dword":
            pushed = False
            for j in range(i + 1, min(i + 16, n)):
                b = insns[j][3]
                if b == "push " + reg:
                    pushed = True
                    break
                if b.startswith("call "):
                    break
            if not pushed:
                continue
        out.append(reg)
    return out


def _rover_cmp_loads(insns, cls):
    """Rover picks from COMPARE-scratch loads: ``mov <reg>,[bare global]``
    whose register is consumed by a ``cmp reg, imm`` / ``test reg, reg``
    within the next few instructions (no push).  This is the Rule 121
    family's pick site (print3_test_info: ``mov ebx,[pm_shown_ptr]; cmp
    ebx,0xfff0000`` -- a RISCified guard load, NOT a GiveBestReg
    conflict).  Higher false-positive risk than the push gate (a Rule-1
    value-pool cache can look identical), so detect() only trusts it when
    the `fr`-trace search CONFIRMS an exact, self-healing injection."""
    want = {"byte": _BYTE_REGS, "word": _WORD_REGS, "dword": _DWORD_REGS}[cls]
    out, n = [], len(insns)
    for i, ins in enumerate(insns):
        m = re.match(r"mov (e?[a-d][xlh]|e?[sd]i|si|di|ebp), "
                     r"(?:(?:byte|word|dword) ptr )?\[([^\]]+)\]$", ins[3])
        if not m:
            continue
        reg, inside = m.group(1), m.group(2)
        if reg not in want or any(c in inside for c in "+*-"):
            continue
        for j in range(i + 1, min(i + 6, n)):
            b = insns[j][3]
            if (re.match(rf"cmp {reg}, (0x[0-9a-f]+|\d+)$", b)
                    or b == f"test {reg}, {reg}"):
                out.append(reg)
                break
            # RMW chain on the SAME scratch keeps the pick alive:
            # `g++; if (g > K)` compiles to mov reg,[g]; inc reg;
            # mov [g],reg; cmp reg,imm -- all one rover pick.
            if (re.match(rf"(inc|dec) {reg}$", b)
                    or re.match(rf"(add|sub) {reg}, (0x[0-9a-f]+|\d+)$", b)
                    or re.match(rf"mov (?:(?:byte|word|dword) ptr )?\[[^\]]+\], {reg}$", b)):
                continue
            if re.match(rf"\w+ {reg}\b", b):     # reg redefined first
                break
            if b.startswith(("call", "jmp", "j")):
                break
    return out


# any x86 GPR token; class is resolved via _REG_CLASS so widths are filtered.
_ANYREG = (r"(eax|ebx|ecx|edx|esi|edi|ebp|esp|ax|bx|cx|dx|si|di"
           r"|al|ah|bl|bh|cl|ch|dl|dh)")


def _rover_const_stores(insns, cls):
    """Rover picks of class ``cls`` from RISCified constant STORES, code order.

    ``message_goto_ptr = 0`` is ``MOV N_MEMORY <- const``; Enregister RISCifies
    the *result*, so the store becomes ``xor reg,reg`` (or ``mov reg,imm``) +
    ``mov [global],reg`` -- and ``reg`` is a FindRegister rover pick, exactly like
    a call-arg load.  (`mov [global],imm` -- the c7 direct form -- is NOT a pick
    and is correctly skipped: it has no register.)  We take the store's source
    register when its nearest preceding definition is a constant materialisation.
    """
    out = []
    for i, ins in enumerate(insns):
        m = re.match(r"mov (?:(?:byte|word|dword) ptr )?\[([^\]]+)\], "
                     + _ANYREG + r"$", ins[3])
        if not m:
            continue
        inside, reg = m.group(1), m.group(2)
        if _REG_CLASS.get(reg) != cls or any(c in inside for c in "+*-"):
            continue
        # nearest preceding write to reg must be a constant materialisation.
        for j in range(i - 1, max(-1, i - 6), -1):
            b = insns[j][3]
            if b == f"xor {reg}, {reg}" or re.match(rf"mov {reg}, (0x[0-9a-f]+|\d+)$", b):
                out.append(reg)
                break
            if re.match(rf"\w+ {reg}\b", b):   # reg clobbered by something else
                break
    return out


def _uniform_shift(rc, ps):
    """If every DIFFERING pair is the same cursor step k (mod cycle) in its
    rover order, return signed k; else None.  Non-contested pairs are ignored."""
    if len(rc) != len(ps) or not rc:
        return None
    ks = set()
    for r, p in zip(rc, ps):
        if r == p:
            continue
        if r not in _REG_IDX or p not in _REG_IDX or _REG_CLASS[r] != _REG_CLASS[p]:
            return None
        c = _CYCLE[r]
        ks.add((_REG_IDX[p] - _REG_IDX[r]) % c)
    if len(ks) == 1:
        k = ks.pop()
        c = _CYCLE[next(r for r, p in zip(rc, ps) if r != p)]
        return k if k <= c // 2 else k - c
    return None


# ---------------------------------------------------------------- rover sim
def _advance(rover, start, except_mask):
    regs = rover if rover is not None else 0
    first = regs
    while True:
        regs += 1
        if start[regs] == 0:
            regs = 0
        if (start[regs] & except_mask) == 0:
            return regs
        if regs == first:
            return regs


def _simulate(fr, inject=None):
    """Replay all three rovers.  ``inject=(idx,k,except,cls)`` adds k extra
    advances of the ``cls`` rover just before fr[idx].  Returns a per-record list
    of (class, reg_name, opcode)."""
    rovers = {"byte": None, "word": None, "dword": None}
    out = []
    for i, r in enumerate(fr):
        if inject and i == inject[0]:
            cls = inject[3]
            for _ in range(inject[1]):
                rovers[cls] = _advance(rovers[cls], _REGS[cls], inject[2])
        cls = _cls_of_tc(r["type_class"])
        reg = None
        if cls is not None:
            rovers[cls] = _advance(rovers[cls], _REGS[cls], r["except"])
            reg = _NAME[_REGS[cls][rovers[cls]]]
            # frx GROUND TRUTH (attached at parse time, trace.py v55): the
            # actual FindRegister pick.  Authoritative for the UNMODIFIED
            # replay; counterfactual injections still use the sim state
            # (sim==frx is 7028/7028-validated, so the two never disagree
            # on the base stream -- this guards against future model drift).
            if not inject and r.get("truth"):
                reg = r["truth"]
        out.append((cls, reg, r["opcode"]))
    return out


def _align_from_end(idx_picks, want):
    """Greedily match ``want`` (disasm picks, code order) against ``idx_picks``
    ``[(fr_index, base_pick), ...]`` from the END, returning the fr indices (or
    None).  The diverging stores cluster at the tail, and earlier same-reg picks
    are usually coalesced away -- the prologue ``=0`` stores reuse one register,
    the ``=nonzero`` stores collapse to the c7 direct form (no register) -- so
    matching backwards lands on the *kept* stores, not the coalesced ones."""
    pos, wi = [], len(want) - 1
    for i, pk in reversed(idx_picks):
        if wi < 0:
            break
        if pk == want[wi]:
            pos.append(i)
            wi -= 1
    return list(reversed(pos)) if wi < 0 else None


def _search(fr, cls, rc_regs, ps_regs, parm_only, const_store=False):
    """Find (inject_index, sorted k's) such that injecting k coalesced advances
    of the ``cls`` rover reproduces PS's picks AT THE VISIBLE STORE POSITIONS.

    The visible positions are recovered by aligning ``rc_regs`` (disasm, code
    order) to the base-sim picks of the relevant fr ops *from the end*
    (``_align_from_end``).  This is what makes the const-store path work despite
    the fr trace also carrying the coalesced ops that never reach the disasm:
    the ``=nonzero`` stores (c7 form, no register) and the prologue zero-stores
    (reused into one register).  Checking only those positions -- not the whole
    pick multiset -- is what the old change-multiset match got wrong."""
    if not rc_regs or rc_regs == ps_regs:
        return None
    base = _simulate(fr)
    if const_store:
        relevant = [i for i, r in enumerate(fr)
                    if _cls_of_tc(r["type_class"]) == cls and r["opcode"] == 0x26]
    elif parm_only:
        relevant = [i for i, r in enumerate(fr)
                    if _cls_of_tc(r["type_class"]) == cls and r["opcode"] == _OP_PARM]
    else:
        relevant = [i for i, r in enumerate(fr) if _cls_of_tc(r["type_class"]) == cls]
    pos = _align_from_end([(i, base[i][1]) for i in relevant], rc_regs)
    if pos is None or [base[p][1] for p in pos] != rc_regs:
        return None
    cyc = _CYCLE.get(rc_regs[0], 8)
    cand = [i for i, r in enumerate(fr) if _cls_of_tc(r["type_class"]) == cls]
    for idx in reversed(cand):                       # closest to the diverging op
        if idx > pos[-1]:
            continue
        ks = [k for k in range(1, cyc + 1)
              if [_simulate(fr, inject=(idx, k, fr[idx]["except"], cls))[p][1]
                  for p in pos] == ps_regs]
        if ks:
            return idx, sorted(ks)
    return None


def _cls_maps(fr, cls):
    """Per-record cursor-transition maps for the ``cls`` rover (identity for
    records of other classes).  Basis of the influence-window computation."""
    ring = _REGS[cls]
    n = len([m for m in ring if m])
    maps = []
    for r in fr:
        if _cls_of_tc(r["type_class"]) == cls:
            maps.append(tuple(_advance(s, ring, r["except"]) for s in range(n)))
        else:
            maps.append(tuple(range(n)))
    return maps, n


def _influences(maps, n, p, a):
    """True iff a cursor perturbation introduced just before record ``p`` can
    still change record ``a``'s pick: the composed masked-advance map over
    records p..a-1 is non-constant.  Mask SEQUENCES merge adjacent cursor
    states (the register between them being excepted), so uncertainty often
    dies within a few records -- and can be PARTIALLY absorbed (a +1 shift
    dies where a +2 survives), which is why single-probe evidence never
    proves irrelevance (take_census 2026-07-09)."""
    cur = tuple(range(n))
    for j in range(p, a):
        cur = tuple(maps[j][s] for s in cur)
        if len(set(cur)) == 1:
            return False
    return len(set(cur)) > 1


def _sim_mods(fr, cls, drops, injects):
    """Replay with multiple modifications: ``drops`` = record indexes whose
    advance is removed (an IL op PS lacked); ``injects`` = [(gap, k)] extra
    advances just before that record (PS-only ops; the gap record's except
    mask stands in for the unknown op's).  Returns per-record reg names."""
    rovers = {"byte": None, "word": None, "dword": None}
    inj = {}
    for p, k in injects:
        inj[p] = inj.get(p, 0) + k
    out = []
    for i, r in enumerate(fr):
        rcls = _cls_of_tc(r["type_class"])
        if i in inj and rcls == cls:
            for _ in range(inj[i]):
                rovers[cls] = _advance(rovers[cls], _REGS[cls], r["except"])
        reg = None
        if rcls is not None and i not in drops:
            rovers[rcls] = _advance(rovers[rcls], _REGS[rcls], r["except"])
            reg = _NAME[_REGS[rcls][rovers[rcls]]]
        out.append(reg)
    return out


def _fit_groups(fr, cls, pos, ps_want, max_k=None):
    """Influence-window fit solver (the take_census 2026-07-09 method,
    generalized).  ``pos`` = fr indexes of the disasm-visible picks (from
    ``_kept_positions``), ``ps_want`` = PS's registers at those picks.

    1. Split the DIVERGENT anchors into influence-decoupled GROUPS: anchors a
       and b are coupled iff a perturbation at a still reaches b (non-constant
       composed map).  A modification inside one group's window provably
       cannot disturb another group (the uncertainty dies in between).
    2. Per group, search SINGLE modifications -- one DROP of a same-class
       record, or one INJECT of +k advances at a gap -- inside the group's
       influence window, requiring every anchor of the group (divergent AND
       matching) to land on PS's pick.

    Returns a list of dicts (one per divergent group):
      {'anchors': [(fr_idx, rc, ps)..], 'window': (lo, hi), 'mods': [...]}
    where mods is possibly empty (no single-mod fit in the window)."""
    maps, n = _cls_maps(fr, cls)
    base = _simulate(fr)
    div = [(p, base[p][1], w) for p, w in zip(pos, ps_want) if base[p][1] != w]
    if not div or len(div) > 12 or len(fr) > 800:
        return None
    if max_k is None:
        max_k = max(2, _CYCLE.get(ps_want[0], 7) - 1)
    # group by coupling (transitive over consecutive divergent anchors)
    groups = [[div[0]]]
    for prev, cur in zip(div, div[1:]):
        if _influences(maps, n, prev[0] + 1, cur[0]):
            groups[-1].append(cur)
        else:
            groups.append([cur])
    all_targets = {p: w for p, w in zip(pos, ps_want)}
    out = []
    for g in groups:
        first, last = g[0][0], g[-1][0]
        gaps = [p for p in range(0, last + 1)
                if _influences(maps, n, p, first) or first <= p <= last]
        gaps = [p for p in gaps if _influences(maps, n, p, last) or p <= first]
        lo = min(gaps) if gaps else first
        # anchors to preserve/achieve inside this group's span (incl. matching ones)
        span_targets = {p: w for p, w in all_targets.items() if lo <= p <= last}

        def ok(sim):
            return all(sim[p] == w for p, w in span_targets.items())

        mods = []
        for p in gaps:
            if (p < len(fr) and _cls_of_tc(fr[p]["type_class"]) == cls
                    and p not in span_targets
                    and ok(_sim_mods(fr, cls, {p}, []))):
                mods.append(("drop", p, 0))
            for k in range(1, max_k + 1):
                if ok(_sim_mods(fr, cls, set(), [(p, k)])):
                    mods.append(("inject", p, k))
        out.append({"anchors": g, "window": (lo, last), "mods": mods})
    return out


def _fit_render(fr, cls, fit, src_lines=None) -> str:
    """One-line-per-group rendering of the fit-solver result."""
    def near_line(i):
        for j in range(i, max(-1, i - 6), -1):
            ln = fr[j].get("line")
            if ln:
                return ln
        return None
    parts = []
    for g in fit:
        anc = " ".join(f"fr#{p}:{rc}->{ps}" for p, rc, ps in g["anchors"])
        lo, hi = g["window"]
        lnlo, lnhi = near_line(lo), near_line(hi)
        win = (f"window fr#{lo}..#{hi}"
               + (f" (~lines {lnlo}..{lnhi})" if lnlo and lnhi else ""))
        if g["mods"]:
            # prefer smallest k / drops; show up to 3
            ms = sorted(g["mods"], key=lambda m: (m[2], m[0] != "drop"))[:3]
            mtx = "; ".join(
                (f"DROP the {cls} op at fr#{p}(blk{fr[p].get('blk','?')}"
                 + (f",L{fr[p].get('line')}" if fr[p].get("line") else "") + ")")
                if kind == "drop" else
                (f"INJECT +{k} before fr#{p}(blk{fr[p].get('blk','?')}"
                 + (f",L{near_line(p)}" if near_line(p) else "") + ")")
                for kind, p, k in ms)
            parts.append(f"{anc}: {win} -> {mtx}")
        else:
            parts.append(f"{anc}: {win} -> NO single-mod fit in window "
                         "(needs >=2 ops here, or the anchor map is off)")
        # lw window census (when the trace carries the lw stream): the
        # per-op candidate map -- foldable loads (+1 via inline-fold),
        # riscified ops (-1 via naming), or the kind-flip-free verdict
        # routing to the IL-birth/walk-order class.
        cen = g.get("census")
        if cen is not None:
            parts.append(f"[lw census: {cen.verdict()}]")
    return ("Rover-fit (influence-window solver): " + "  ||  ".join(parts)
            + ".  A mod in one group's window provably cannot disturb the "
            "other groups (uncertainty dies in between); statement-form "
            "rewrites are IL-inert -- the lever must ADD/REMOVE an op "
            "(fill-form, guard-order inversion, dup-tail, de-CSE) inside "
            "the named window.  Anchors cover only this kind's same-form "
            "picks; lea<->inc realization diffs are unanchored -- confirm "
            "a candidate against the full diff.")


def _kept_positions(fr, cls, rc_regs, ps_regs, parm_only, const_store):
    """fr indices of the disasm-visible (kept) picks, or None (alignment as
    in _search)."""
    base = _simulate(fr)
    if const_store:
        relevant = [i for i, r in enumerate(fr)
                    if _cls_of_tc(r["type_class"]) == cls and r["opcode"] == 0x26]
    elif parm_only:
        relevant = [i for i, r in enumerate(fr)
                    if _cls_of_tc(r["type_class"]) == cls and r["opcode"] == _OP_PARM]
    else:
        # regs came from _rover_cmp_loads (the guard-load class, op 0x35).
        # Restrict the alignment to cmp-load records FIRST: the greedy
        # backward alignment otherwise mis-anchors a visible cmp-load to a
        # LATER same-pick record of another form (show_battlemap_base
        # 2026-07-09: fr#12/#15 (op1 +=/fused) instead of the true fr#5/#10
        # guard loads -- same base picks, wrong influence window, and the
        # fit solver reported "NO single-mod fit" noise).  Fall back to the
        # all-records alignment only when the restricted one fails.
        relevant = [i for i, r in enumerate(fr)
                    if _cls_of_tc(r["type_class"]) == cls and r["opcode"] == 0x35]
        pos = _align_from_end([(i, base[i][1]) for i in relevant], rc_regs)
        if pos is not None and [base[p][1] for p in pos] == rc_regs:
            return pos
        relevant = [i for i, r in enumerate(fr) if _cls_of_tc(r["type_class"]) == cls]
    pos = _align_from_end([(i, base[i][1]) for i in relevant], rc_regs)
    if pos is None or [base[p][1] for p in pos] != rc_regs:
        return None
    return pos


def _sim_events(events):
    """Simulate a reordered fr EVENT LIST; returns {id(event): pick_name}."""
    rovers = {"byte": None, "word": None, "dword": None}
    arrays = {"byte": _REGS["byte"], "word": _REGS["word"], "dword": _REGS["dword"]}
    picks = {}
    for r in events:
        cls = _cls_of_tc(r["type_class"])
        if cls is None:
            continue
        start = arrays[cls]
        regs = rovers[cls] if rovers[cls] is not None else 0
        first = regs
        while True:
            regs += 1
            if start[regs] == 0:
                regs = 0
            if (start[regs] & r["except"]) == 0:
                break
            if regs == first:
                break
        rovers[cls] = regs
        picks[id(r)] = _NAME[start[regs]]
    return picks


def _arm_swap_search(fr, cls, rc_regs, ps_regs, parm_only, const_store):
    """Rule 122 reorder test: swap two BLOCK GROUPS of fr events (grouped by
    the bk-derived ``blk`` tag) and check whether the kept picks become PS's.
    Returns (blkA, blkB, lineA, lineB) -- the two blocks to arm-swap -- or
    None.  Requires blk tags (trace images with the `bk` record)."""
    if not fr or any(r.get("blk") is None for r in fr):
        return None
    pos = _kept_positions(fr, cls, rc_regs, ps_regs, parm_only, const_store)
    if pos is None:
        return None
    kept = [fr[p] for p in pos]
    # the first diverging kept pick's block -- the lever's neighbourhood
    base = _simulate(fr)
    div_blk = None
    for p, want in zip(pos, ps_regs):
        if base[p][1] != want:
            div_blk = fr[p]["blk"]
            break
    blks = []
    for r in fr:
        b = r["blk"]
        if b not in blks:
            blks.append(b)
    wins = []
    for ai in range(len(blks)):
        for bi in range(ai + 1, len(blks)):
            a, b = blks[ai], blks[bi]
            ga = [r for r in fr if r["blk"] == a]
            gb = [r for r in fr if r["blk"] == b]
            reordered = []
            for r in fr:
                if r["blk"] == a:
                    if r is ga[0]:
                        reordered.extend(gb)
                elif r["blk"] == b:
                    if r is gb[0]:
                        reordered.extend(ga)
                else:
                    reordered.append(r)
            picks = _sim_events(reordered)
            if [picks.get(id(k)) for k in kept] == ps_regs:
                la = next((r.get("line") for r in ga if r.get("line")), None)
                lb = next((r.get("line") for r in gb if r.get("line")), None)
                # rank: prefer pairs bracketing/adjacent to the diverging
                # block, then smallest span (the if/else arms are adjacent)
                rank = (0 if (div_blk is not None and a <= div_blk <= b)
                        else 1, b - a)
                wins.append((rank, a, b, la, lb))
    if not wins:
        return None
    wins.sort()
    _rank, a, b, la, lb = wins[0]
    return a, b, la, lb


# ---------------------------------------------------------------- public API
def parm_reload(fr) -> str | None:
    """Detect the *checked-global-reused-as-call-arg reload* (the link_to_smacker
    root, proven in watcom10.0a docs/parm-reload-rover.md).

    A global that is tested (`if (g)`) and then passed as a call argument is
    RELOADED for the argument: ``Enregister`` (wcc386 va 0x62939) returns the
    PARM_DEF's N_MEMORY operand UNCONDITIONALLY -- no "already in a register"
    check -- so the same name is RISCified twice.  The second RISCify is an extra
    push-scratch rover advance that bumps every later call-arg / const-store up a
    register (and can force an extra callee-save spill).  Score (0x54df1) later
    coalesces the reload back to a register reuse, but only AFTER the rover
    already cascaded.

    Signal: a PARM_DEF (opcode 0x2a) fr record whose ``op0`` equals an *earlier*
    non-PARM record's ``op0`` (the same global, loaded for the test then again
    for the arg).  Returns a one-line diagnostic, or None.
    """
    if not fr:
        return None
    seen = {}  # op0 -> opcode of first sighting
    for r in fr:
        op0, opc = r.get("op0"), r.get("opcode")
        if opc == 0x2a and op0 in seen and seen[op0] != 0x2a:
            return ("a global is checked then passed as a call arg, so Watcom "
                    "RELOADS it for the push (Enregister RISCifies the memory "
                    "operand) -- an extra push-scratch rover advance that bumps "
                    "the later call-args/const-stores up a register (the cascade "
                    "behind this swap / extra callee-save spill).  LEVER (proven "
                    "byte-exact on link_to_smacker): copy the global into a temp "
                    "AFTER the guard and pass the temp -- `int o; if (g) ...; "
                    "o = g; f(.., o);`.  The test stays a DIRECT rover read (so it "
                    "keeps PS's register) while the arg becomes a temp (no reload "
                    "advance); Score coalesces the temp away.  Do NOT cache "
                    "BEFORE the guard -- that puts the test on a named temp "
                    "(GiveBestReg->EAX) and shifts everything.  watcom10.0a "
                    "docs/parm-reload-rover.md.")
        seen.setdefault(op0, opc)
    return None


# ------------------------------------------------- offline closeability verdict
_LOAD_RE = re.compile(r"mov (e[a-d]x|e[sd]i|ebp), (?:dword ptr )?\[[^\]]+\]$")


def _load_divergences(rows) -> tuple[list, list]:
    """Form-matched dword LOAD register swaps from the aligned diff, code order.
    A true rover pick is ``mov <reg>, [<mem>]`` on BOTH sides (same form) where the
    register differs -- this is the unambiguous FindRegister scratch.  Inherited
    swaps (lea / stores of a computed value) are excluded."""
    rc_regs, ps_regs = [], []
    for row in rows:
        if row.get("kind") != "replace":
            continue
        o, r = row.get("o"), row.get("r")
        if not o or not r:
            continue
        mp, mr = _LOAD_RE.match(o[3]), _LOAD_RE.match(r[3])
        if not mp or not mr:
            continue
        pr, rr = mp.group(1), mr.group(1)
        if pr == rr or _REG_CLASS.get(pr) != "dword" or _REG_CLASS.get(rr) != "dword":
            continue
        rc_regs.append(rr)
        ps_regs.append(pr)
    return rc_regs, ps_regs


def closeability(rows, fr, src_lines=None, visible=None):
    """OFFLINE closeable/blocked verdict for a rover diff -- NO recompile.

    Take RC's fr table; inject one ``+k`` dword advance at EACH position (one
    location at a time); simulate; a position is a WIN iff it makes every
    divergent load become PS's pick AND leaves every disasm-VISIBLE dword op
    unchanged (true self-heal = byte-neutral).  >=1 win => CLOSEABLE (the +k
    self-heals at that source line).  0 wins => BLOCKED.

    ``visible`` is the CompressIns model (CRITICAL): a ``(decomp_line, reg)`` set
    of the disasm-VISIBLE rover picks (real ``mov reg,[g]`` loads + ``mov [g],reg``
    register stores).  LdStCompress runs right after the rover and compresses
    single-use loads + immediate const-stores BACK to direct memory operands
    (``cmp [g],0`` / ``mov [g],imm``), so their rover advance leaves NO register
    in the bytes -- those ops must NOT be required to hold.  Without ``visible``
    every fr op is (wrongly) required to hold, over-reporting BLOCKED (e.g.
    build_region_item's `warned_of_not_build = 1` immediate stores).

    Returns ``(verdict, k, lines)`` -- verdict in {closeable, blocked, align-fail}
    -- or None when there is no clean uniform-k dword load divergence.
    """
    if not fr:
        return None
    rc_regs, ps_regs = _load_divergences(rows)
    if not rc_regs:
        return None
    k = _uniform_shift(rc_regs, ps_regs)
    if not k:                                  # None or 0 -> not a clean rover
        return None
    base = _simulate(fr)
    didx = [i for i, r in enumerate(fr) if _cls_of_tc(r.get("type_class")) == "dword"]
    pos = _align_from_end([(i, base[i][1]) for i in didx], rc_regs)
    if pos is None:
        return ("align-fail", k, [])
    targets = {p: v for p, v in zip(pos, ps_regs)}
    dontcare = set(range(min(pos), max(pos) + 1))   # the divergent run + coalesced
    hold = [i for i in didx if i not in dontcare]
    if visible is not None:
        # CompressIns model: only DISASM-VISIBLE picks must hold; invisible
        # compressed ops advance the rover but leave no register in the bytes.
        hold = [i for i in hold if (fr[i].get("line"), base[i][1]) in visible]
    wins = []
    for P in range(len(fr) + 1):
        exc = fr[min(P, len(fr) - 1)]["except"]
        sim = _simulate(fr, inject=(P, abs(k), exc, "dword"))
        if all(sim[i][1] == v for i, v in targets.items()) and \
           all(sim[i][1] == base[i][1] for i in hold):
            lb = next((fr[j]["line"] for j in range(P - 1, -1, -1) if fr[j].get("line")), None)
            if lb:
                wins.append(lb)
    if wins:
        return ("closeable", k, sorted(set(wins)))
    return ("blocked", k, [])


def render_closeability(result, src_lines=None, chain_vintages=None) -> str:
    """One-line text for the closeability verdict (or '' for None/align-fail).

    ``chain_vintages`` (c2.regalloc.rover.chain_vintages, >= 2026-07-13
    image) enriches the BLOCKED verdict with the haul PROVENANCE: how many
    blocks MakeFlowGraph (DFS/RPO relink / ReturnsToBottom) moved vs a
    later pass -- the attribution that used to need a one-off WCPATCH_BC
    image.  Drill-in: `c2 spell <fn> --walk-order`."""
    if not result:
        return ""
    verdict, k, lines = result
    if verdict == "closeable":
        loc = ", ".join(
            (f"L{ln} `{_src_text(src_lines, ln, 30)}`" if _src_text(src_lines, ln, 30)
             else f"L{ln}") for ln in lines[:3])
        return (f"Rover-closeable: a {k:+d} dword advance SELF-HEALS offline "
                f"(no recompile) injected after {loc} -- add a {k:+d} dword rover "
                "op there (dead-branch/duplicated-tail const-store, or a coalesced "
                "reload) and the cursor heals before any byte-exact op.  "
                "Rule 121 refinement: a statement-only tail dup re-merges "
                "pre-walk (spell INERT@BURN); include the arm's CALL in the dup "
                "to survive to the walk -- byte-safe only where PS's layout is "
                "the merged-dup form (jmp carries its own -d1 mark), NOT a "
                "cross-arm goto/shared tail (jmp unmarked); screen with c2 spell "
                "then byte-compile (mid3_line_no_sides_base 15cd1284 vs "
                "show_battlemap_base b5d891d9).")
    if verdict == "blocked":
        prov = ""
        if chain_vintages:
            hauled = sum(1 for v in chain_vintages if v.get("hauled_mfg"))
            late = sum(1 for v in chain_vintages if v.get("moved_after_mfg"))
            if hauled or late:
                prov = (f"  [br: {hauled} block(s) hauled by MakeFlowGraph "
                        f"(DFS/RPO / ReturnsToBottom), {late} moved by a "
                        "later pass -- `c2 spell <fn> --walk-order`]")
        return (f"Rover-blocked: a {k:+d} dword advance CANNOT self-heal in RC's IL "
                "chain order -- every injection that fixes the divergence also "
                "shifts a byte-exact op (BLOCK-ORDER divergence: PS walks those "
                "blocks in a different order).  Needs block-order restructuring, "
                f"not a single faithful advance.{prov}")
    return ""


def detect(ps_insns, rc_insns, rule_hist: dict | None = None, fr=None,
           lw=None,
           src_lines: dict | None = None,
           src_struct: dict | None = None) -> RoverHint | None:
    """Classify a RISCify-rover register swap (byte/word/dword) and, when ``fr``
    is given, report the exact byte-neutral cursor advance that reproduces PS.

    ``src_lines`` (decomp ``line -> text``) annotates each cursor-advance site
    and the divergence line with its source construct.  ``src_struct`` (AST
    control-flow facts: ``dup_hosts`` / ``guard_stores`` / ``const_stores``)
    lets the lever give an ACCURATE host verdict -- a real duplicated-tail host,
    or a definite "the const-stores are early-return guards, not dup-able"."""
    rule_hist = rule_hist or {}
    if not (rule_hist.keys() & {"Reg swap", "Byte-reg swap", "Rule 28", "Rule 28b"}):
        return None
    # The rover lever is for PURE register-identity swaps.  If RC pushes a
    # different callee-save set (extra/missing push) the dominant issue is
    # usually CAPACITY -- defer to the Prologue/Rule-89 hint AND the
    # Parm-reload hint.  (link_to_smacker: RC reloads a global parm -> rover
    # cascade -> an extra esi spill; the clean fix is the Parm-reload lever.)
    # EXCEPTION (battle_action, 2026-06-10): when the push delta is exactly
    # the PARENTS of byte/word rover picks (PS rover lands on CL/CH -> PS
    # pushes ECX), the rover pick is the CAUSE of the push difference, not a
    # symptom -- proceed and tag the hint.
    _ps_p, _rc_p = _callee_pushes(ps_insns), _callee_pushes(rc_insns)
    rover_caused_push = False
    if _ps_p != _rc_p:
        _delta = set(_ps_p) ^ set(_rc_p)
        _parent = {"al": "eax", "ah": "eax", "bl": "ebx", "bh": "ebx",
                   "cl": "ecx", "ch": "ecx", "dl": "edx", "dh": "edx",
                   "ax": "eax", "bx": "ebx", "cx": "ecx", "dx": "edx"}
        _subreg_parents = set()
        for _insns in (ps_insns, rc_insns):
            for _i in _insns:
                for _tok in _i[3].replace(",", " ").split():
                    _pp = _parent.get(_tok)
                    if _pp:
                        _subreg_parents.add(_pp)
        if _delta and _delta <= _subreg_parents:
            rover_caused_push = True
        elif (len(_ps_p) == len(_rc_p) and len(_delta) == 2
              and _delta <= {"ebx", "ecx", "edx", "esi", "edi", "ebp"}):
            # SAME-COUNT callee-save SUBSTITUTION (e.g. edi<->ebp,
            # mouse_follow_cohort): the push set differs but the COUNT is
            # identical -- the rover landed on a different register and that
            # register got pushed.  The push delta is a SYMPTOM of the rover
            # pick, not a capacity decision.  Proceed; the uniform-shift check
            # below confirms it is the rover (consistent k across the swaps) or
            # the enumeration finds nothing and we return None.  Without this
            # the diff is mis-routed to "Regalloc: layer-3 callee-save swap"
            # and the rover lever is never surfaced.
            rover_caused_push = True
        else:
            return None
    # try widest class first (dword pushes are the common, robust case)
    for cls, parm_only in (("dword", True), ("word", False), ("byte", False)):
        const_store = False
        ps_regs = _rover_loads(ps_insns, cls)
        rc_regs = _rover_loads(rc_insns, cls)
        _ok = (ps_regs and rc_regs and ps_regs != rc_regs
               and len(ps_regs) == len(rc_regs)
               and any(p != r for p, r in zip(ps_regs, rc_regs)))
        if not _ok:
            # fall back to RISCified constant STORES (the `xor reg,reg;
            # mov [global],reg` zero-stores -- message's loop-tail residue).
            ps_s = _rover_const_stores(ps_insns, cls)
            rc_s = _rover_const_stores(rc_insns, cls)
            if (ps_s and rc_s and len(ps_s) == len(rc_s)
                    and any(p != r for p, r in zip(ps_s, rc_s))):
                ps_regs, rc_regs, parm_only, const_store = ps_s, rc_s, False, True
            else:
                # fall back to COMPARE-scratch loads (the Rule 121 family's
                # pick site: `mov reg,[g]; cmp reg,imm` guard loads).  The
                # asm shape alone can false-positive on value-pool caches,
                # so this path is only ADVISORY unless the fr search below
                # confirms an exact injection.
                ps_c = _rover_cmp_loads(ps_insns, cls)
                rc_c = _rover_cmp_loads(rc_insns, cls)
                if (ps_c and rc_c and len(ps_c) == len(rc_c)
                        and any(p != r for p, r in zip(ps_c, rc_c))):
                    ps_regs, rc_regs, parm_only = ps_c, rc_c, False
                else:
                    continue
        shift = _uniform_shift(rc_regs, ps_regs)
        advances, inject_at = [], None
        diverge = None
        arm_swap = None
        fit = None
        if fr:
            res = _search(fr, cls, rc_regs, ps_regs, parm_only,
                          const_store=const_store)
            if res:
                inject_at, advances = res
            else:
                # +k failed -> Rule 122 reorder test (needs bk blk tags).
                arm_swap = _arm_swap_search(fr, cls, rc_regs, ps_regs,
                                            parm_only, const_store)
                if arm_swap is None:
                    # piecewise deltas (a single inject/uniform shift cannot
                    # fit) -> influence-window fit solver: decouple this
                    # kind's divergent picks into influence-independent
                    # groups and solve each group's minimal +/-op requirement
                    # inside its window.  (Anchors cover THIS kind's visible
                    # picks only -- cross-form realizations like lea<->inc
                    # have no same-form pair and stay unanchored; the render
                    # says so.)
                    kp = _kept_positions(fr, cls, rc_regs, ps_regs,
                                         parm_only, const_store)
                    if kp is not None:
                        try:
                            fit = _fit_groups(fr, cls, kp, ps_regs)
                            # enrich each fit group with the lw-based
                            # window CENSUS (c2.regalloc.lwalk): which ops
                            # in the window are foldable (+1) / riscified
                            # (-1) / pinned -- or the kind-flip-free
                            # verdict routing to the IL-birth/walk-order
                            # class.  Needs the lw stream (trace image >=
                            # 2026-07-09); silently absent otherwise.
                            if fit and lw:
                                from c2.regalloc import lwalk
                                for g in fit:
                                    lo, hi = g["window"]
                                    g["census"] = lwalk.window_census(
                                        lw, fr, cls, lo, hi)
                        except Exception:
                            import os as _os
                            if _os.environ.get("C2_DEBUG_REGALLOC"):
                                import traceback
                                traceback.print_exc()
                            fit = None
                    else:
                        import os as _os
                        if _os.environ.get("C2_DEBUG_REGALLOC"):
                            print(f"[rover-fit] kept_positions=None cls={cls} "
                                  f"rc={rc_regs} ps={ps_regs}")
            diverge = _diverge_line(fr, cls, rc_regs, ps_regs, const_store, parm_only)
        return _build(cls, ps_regs, rc_regs, shift, advances, inject_at, fr,
                      parm_only, diverge, arm_swap,
                      rover_caused_push=rover_caused_push, src_lines=src_lines,
                      src_struct=src_struct, fit=fit)
    return None


def _build(cls, ps_regs, rc_regs, shift, advances, inject_at, fr, parm_only,
           diverge=None, arm_swap=None, rover_caused_push=False, src_lines=None,
           src_struct=None, fit=None):
    pairs = "  ".join(f"#{i}:{r}->{p}" for i, (r, p) in enumerate(zip(rc_regs, ps_regs))
                      if r != p)
    summary = f"RISCify {cls} rover swap [RC->PS]  {pairs}"
    if diverge is not None:
        dln, drc, dps = diverge
        summary += (f"  -- 1st DIVERGENCE at source line {dln}: "
                    f"RC picks {drc.upper()}, PS picks {dps.upper()}")
    if advances:
        small = [k for k in advances if k <= _CYCLE.get(rc_regs[0], 8) // 2] or advances[:1]
        rng = " or ".join(f"+{k}" for k in small)
        rank = _op_rank(fr, inject_at, cls, parm_only)
        at_line = fr[inject_at].get("line") if fr and inject_at is not None else None
        loc = f"{cls} op #{rank}" + (f" (source line {at_line})" if at_line else "")
        adv_txt = (f"the `fr` rover trace CONFIRMS it: inject {rng} coalesced {cls} "
                   f"load(s) before {loc} -- that advance reproduces PS's "
                   "picks exactly and self-heals. ")
    elif arm_swap is not None:
        _a, _b, la, lb = arm_swap
        adv_txt = (f"Rule 122 CONFIRMED by the fr reorder test: swapping the "
                   f"WALK ORDER of the blocks at source lines "
                   f"{la or '?'} and {lb or '?'} reproduces PS's picks exactly "
                   "(later picks unchanged).  These are two ARMS of an "
                   "if/else: INVERT the condition and swap the arms "
                   "(`if (A) X else Y` -> `if (!A) Y else X`) -- bytes are "
                   "identical for both orders, only the LdStAlloc walk moves "
                   "(update_time: 26b->22b register-exact). ")
    elif fit:
        adv_txt = _fit_render(fr, cls, fit, src_lines) + " "
    elif shift is not None and shift > 0:
        adv_txt = (f"PS's cursor is +{shift} vs RC: add ~{shift} coalesced {cls} "
                   "load(s) before the diverging op. ")
    elif shift is not None and shift < 0:
        adv_txt = (f"PS's cursor is {shift} vs RC: remove ~{abs(shift)} {cls} "
                   "load(s) before the diverging op. ")
    else:
        adv_txt = ("per-op `except` differs (non-uniform); try a small block split "
                   "just before the diverging op and re-check direction. ")
    order = {"byte": "AL,AH,DL,DH,BL,BH,CL,CH", "word": "AX,DX,BX,CX,SI,DI",
             "dword": "EAX,EDX,EBX,ECX,ESI,EDI"}[cls]
    sites = _rover_sites(fr, cls, src_lines)
    sites_txt = ("  Cursor-advance SITES (source line:kind «code», walk order -- the +1 "
                f"lives at or before the diverging op): {sites}." if sites else "")
    # Concrete, function-specific prescription (names the divergence construct +
    # the best host site).  Leads the lever when we have source text.
    action = _actionable(cls, diverge, advances, shift, fr, src_lines, parm_only,
                         src_struct)
    action_txt = (action + "  ") if action else ""
    lever = (
        action_txt +
        f"NOT a savings/last-use tie -- FindRegister {cls} rover picks over a "
        f"persistent cursor ({order}). " + adv_txt + sites_txt +
        "  What advances the cursor (lw-probe-refined, 2026-07-09): a SPLIT-OUT "
        "memory operand (a cmp/test/arith op reading memory directly -- Enregister "
        "splits it into rover-load + reg-op) or a const store to memory.  Plain "
        "`mov reg,[mem]` loads NEVER advance (already load-form; Enregister only "
        "RISCifies const-source movs), nor do reg-only ops, converts, or calls.  "
        "So the byte-neutral +1 lever is: rewrite `x = g; ... x OP k` so the "
        "consumer reads g INLINE (`g OP k` -- the split lands the rover on the "
        "same reg = identical bytes, +1 advance); the -1 lever is the reverse "
        "(name the temp so the consumer reads a register).  "
        "Enumerate candidates: the [lw census: ...] line above (per fit window), "
        "`c2 spell <fn> --fusion` (which RISCified pairs fused vs a named lcx "
        "reject), and `c2 spell <fn> <candidate.c>` (the 3-stage INERT@TREE / "
        "INERT@BURN / LIVE spelling screener -- probe WITHOUT byte compiles).  "
        "A value already in "
        "a register (reused) does NOT.  PROVEN byte-neutral levers (try in order): "
        "(1) LOOP-INVARIANT-CONST -- a post-loop use of a value the loop pins to a "
        "constant: write the literal so it becomes a const store (advance) instead "
        "of a reused-register load (no advance).  message: `game_state = out1` -> "
        "`game_state = 1` (out1==1 after `while(out1 != 1)`) = +1 = byte-exact.  "
        "(2) PARM-RELOAD -- cache a checked global through a temp AFTER its guard "
        "(link_to_smacker).  (3) DEAD-BRANCH DWORD DUP -- duplicate a dword store "
        "into both arms of a never-taken `if(x==K)` (start_smacking).  "
        "(4) DUPLICATED TAIL (Rule 121) -- when the swap is on a COMPARE-scratch "
        "load in the second-walked arm of an if/else-if with a shared tail, write "
        "the tail INSIDE EACH ARM: LdStAlloc walks the duplicated rover ops "
        "between the arms' picks (+1) and ComTail merges the bytes back "
        "(print_test_info 98b->exact, print3_test_info 3b->exact).  "
        "REFINEMENT (2026-07-10, mid3_line_no_sides_base 15cd1284): a bare "
        "statement-only dup (add+continue) is re-merged by a pre-walk pass and "
        "screens INERT@BURN -- include the arm's CALL in the duplicated tail and "
        "the dup SURVIVES to the walk (spell = LIVE with the advance delta).  "
        "Byte-safety then depends on PS's witnessed layout: if PS's -d1/asm shows "
        "the merged-dup form the lever closes (mid3_no_sides' ebp-0xf knot); if "
        "PS shows a cross-arm goto/shared-tail jmp, ComTail builds a NEW merge "
        "point and regresses (show_battlemap_base 296->313bd) -- screen with "
        "c2 spell, then byte-compile before keeping.  Confirm with "
        "watcom10.0a tools/rover_sim.py; search edits with tools/rover_search.py."
    )
    if rover_caused_push:
        summary = ("[ROVER-CAUSED PUSH] the callee-save delta is the PARENT "
                   "of rover picks (e.g. PS rover lands on CL/CH -> PS pushes "
                   "ECX): fixing the rover cursor fixes the prologue too -- "
                   "do NOT chase the push as a capacity problem.  " + summary)
    return RoverHint(cls=cls, ps_regs=ps_regs, rc_regs=rc_regs, shift=shift,
                     advances=advances, inject_at=inject_at, diverge=diverge,
                     summary=summary, lever=lever)


def _src_text(src_lines, ln, width=40) -> str:
    """Trimmed source text at decomp line ``ln`` (or '' if unavailable)."""
    if not src_lines or ln is None or ln not in src_lines:
        return ""
    t = " ".join(src_lines[ln].split())          # collapse whitespace
    t = t.rstrip("{").strip()
    if len(t) > width:
        t = t[:width - 1] + "\u2026"
    return t


def _rover_sites(fr, cls, src_lines=None) -> str:
    """Source-line map of the ``cls`` rover ops in walk order -- the candidate
    cursor-advance sites.  Each is ``line:kind`` (L=load/mem-op, C=const-store);
    a value already live in a register is reused (no entry).  When ``src_lines``
    is given each site is annotated with its source construct, so the walk order
    reads e.g. ``795:L if(cohort_tick_gate>=2)`` -- the concrete things whose
    count/order you change.  Needs the fr line_num field (2026-06+ images)."""
    if not fr:
        return ""
    out, seen = [], None
    for r in fr:
        if _cls_of_tc(r.get("type_class")) != cls:
            continue
        ln = r.get("line")
        if ln is None:
            return ""            # old trace image, no line info
        kind = "C" if r.get("opcode") == 0x26 else "L"   # 0x26 = OP_MOV (const store)
        tok = f"{ln}:{kind}"
        if tok != seen:          # collapse runs on the same line
            txt = _src_text(src_lines, ln, width=34)
            out.append(f"{tok} \u00ab{txt}\u00bb" if txt else tok)
            seen = tok
    return " ".join(out)


def _actionable(cls, diverge, advances, shift, fr, src_lines, parm_only,
                src_struct=None) -> str:
    """Concrete, function-specific prescription built from the precise rover
    mechanism (an advance = ONE extra RISCified *leftover* ``cls`` memory op --
    a global/field load or const-store that RegAlloc did NOT keep in a named
    register and that is NOT move-elim'd into a call-arg register).

    Names the divergence construct, the exact +k/-k needed, and -- when the AST
    ``src_struct`` is available -- an ACCURATE host verdict: a real
    duplicated-tail host (a const-store following an if/else), or a definite
    "these const-stores are early-return guards, not dup-able".  Empty string
    when there is nothing source-level to point at."""
    if diverge is None:
        return ""
    dln, drc, dps = diverge
    dsrc = _src_text(src_lines, dln, width=52)
    # direction + magnitude
    if advances:
        small = [k for k in advances if k <= _CYCLE.get(drc, 8) // 2] or advances[:1]
        k = small[0]
        need = f"ADD {k} {cls} advance(s) BEFORE line {dln}"
    elif shift is not None and shift > 0:
        k, need = shift, f"ADD ~{shift} {cls} advance(s) BEFORE line {dln}"
    elif shift is not None and shift < 0:
        k, need = shift, f"REMOVE ~{abs(shift)} {cls} advance(s) BEFORE line {dln}"
    else:
        k, need = None, f"shift the {cls} cursor just before line {dln}"
    # same-class advance sites strictly BEFORE the divergence, in walk order,
    # with their source text -- these are where you add/remove an advance.
    befores, const_hosts = [], []
    if fr:
        seen = None
        for r in fr:
            if r.get("line") == dln:
                break          # reached the divergence line; stop
            if _cls_of_tc(r.get("type_class")) != cls:
                continue
            ln = r.get("line")
            tok = (ln, "C" if r.get("opcode") == 0x26 else "L")
            if tok != seen and ln is not None:
                befores.append(tok)
                if tok[1] == "C":
                    const_hosts.append(ln)
                seen = tok
    parts = []
    if dsrc:
        parts.append(f"divergence line {dln}: `{dsrc}`  (RC={drc.upper()} "
                     f"PS={dps.upper()}).")
    parts.append(f"ACTION: {need}.")
    if k is not None and k > 0:
        # +k: add ONE extra leftover dword mem op walked before the divergence.
        # Use the AST (src_struct) to give a DEFINITE host verdict instead of a
        # guess: a const-store that follows an if/else IS a duplicated-tail host
        # (Rule 121 / start_smacking); a const-store in an early-return guard is
        # NOT (no "both arms").
        dup_hosts = (src_struct or {}).get("dup_hosts", {})
        guard_stores = (src_struct or {}).get("guard_stores", set())
        real_hosts = [hl for hl in const_hosts if hl in dup_hosts]
        if real_hosts:
            hl = real_hosts[-1]
            parts.append(f"+{k} HOST = the const-store at line {hl} "
                         f"(`{_src_text(src_lines, hl, 36)}`), the shared tail of "
                         f"the if/else at line {dup_hosts[hl]}: push it INTO BOTH "
                         "ARMS so LdStAlloc RISCifies a coalesced load between "
                         "them (+1) and ComTail merges the bytes back "
                         "(start_smacking / Rule 121).")
        elif const_hosts and all(hl in guard_stores for hl in const_hosts):
            cand = ", ".join(str(hl) for hl in const_hosts)
            parts.append(f"the const-stores before the divergence ({cand}) are "
                         "ALL early-return guards (`if(c){{...;return;}}`), NOT "
                         "dup-able (no second arm).  The +1 must come from "
                         "PARM-RELOAD (a checked global passed as a call arg -> "
                         "copy to a temp after the guard) or a genuine block "
                         "split; verify with watcom10.0a tools/rover_sim.py.")
        elif src_struct is not None:
            cand = ", ".join(f"{hl}:{'guard' if hl in guard_stores else 'plain'}"
                             for hl in const_hosts) or "none"
            parts.append(f"no duplicated-tail host before line {dln} "
                         f"(const-stores: {cand}).  Add the +1 via PARM-RELOAD "
                         "(checked global passed as a call arg) or a block split; "
                         "verify with watcom10.0a tools/rover_sim.py.")
        else:
            # no AST available -- fall back to listing the fr candidates.
            cand = ", ".join(f"{hl}" for hl in const_hosts) or "none"
            parts.append(f"+{k} const-store candidates before the divergence: "
                         f"{cand}; a store SHARED by both arms of an if/else is "
                         "the duplicated-tail host (push into both arms).")
    elif k is not None and k < 0:
        parts.append("REMOVE an advance: CSE a redundant reload before the "
                     "divergence, or pass an immediate / array address (no load) "
                     "instead of a memory VARIABLE at one of the sites below.")
    if befores:
        parts.append("advance sites before the divergence: "
                     + "  ".join(f"{ln}:{kd}" for ln, kd in befores) + ".")
    return "  ".join(parts)


def _diverge_line(fr, cls, rc_regs, ps_regs, const_store, parm_only):
    """Pinpoint the FIRST diverging kept-store/parm op: align the disasm pick
    lists (rc_regs/ps_regs, code order) to the fr trace's same-class records of
    the right opcode (from the END -- coalesced ops drop off the front), then
    return (source_line, rc_reg, ps_reg) for the first position where RC != PS.
    None if the alignment fails or the trace lacks line numbers."""
    if not fr or not rc_regs or len(rc_regs) != len(ps_regs):
        return None
    # first diverging position in the kept-pick lists
    di = next((i for i, (r, p) in enumerate(zip(rc_regs, ps_regs)) if r != p), None)
    if di is None:
        return None
    base = _simulate(fr)
    if const_store:
        relevant = [i for i, r in enumerate(fr)
                    if _cls_of_tc(r["type_class"]) == cls and r["opcode"] == 0x26]
    elif parm_only:
        relevant = [i for i, r in enumerate(fr)
                    if _cls_of_tc(r["type_class"]) == cls and r["opcode"] == _OP_PARM]
    else:
        relevant = [i for i, r in enumerate(fr) if _cls_of_tc(r["type_class"]) == cls]
    pos = _align_from_end([(i, base[i][1]) for i in relevant], rc_regs)
    if pos is None or di >= len(pos):
        return None
    ln = fr[pos[di]].get("line")
    if ln is None:
        return None
    return (ln, rc_regs[di], ps_regs[di])


def _op_rank(fr, idx, cls, parm_only) -> int:
    if fr is None or idx is None:
        return 0
    rank = 0
    for i, r in enumerate(fr):
        if i == idx:
            return rank
        if _cls_of_tc(r["type_class"]) == cls and (not parm_only or r["opcode"] == _OP_PARM):
            rank += 1
    return rank


def render(hint: RoverHint) -> str:
    return f"{hint.summary}. {hint.lever}"
