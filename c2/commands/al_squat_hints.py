"""AL-squat family classifier (byte-conflict AL-vs-D-register seating).

Fires when the aligned diff shows a Byte-reg swap whose RC side is an
A-family byte register (AL/AH) and the PS side is not: our build seated a
byte conflict in AL where PS used DL/DH/BL/... -- the AL-SQUAT family
(watcom10.0a ``docs/al-squat-family.md``).

What is PROVEN about this family (10.0a RE, 2026-06-10):

* ``CountRegMoves`` gives NO credit for OP_CONVERT, so a load+test+zext
  byte temp has saves==0 for every candidate; GiveBestReg keeps the FIRST
  best-saves candidate and the GivenRegisters tie-break can only prefer
  AL further.  **AL wins deterministically whenever it is in the
  candidate list** -- tie-level source levers (decl/use/creation order)
  are provably irrelevant.
* Both asm forms are one post-alloc reduction (``rCLRHI_R``): byte temp
  in AL -> ``and eax,0xff`` in place; elsewhere -> ``xor eax,eax;
  mov al,<reg>``.  The form is downstream of the seating, never a lever.
* Therefore PS's seating means AL was missing from the conflict's REAL
  candidate list (``bt`` trace record / ``tree_cands``) or blocked via
  with.regs by an IL-shape difference.

The hint surfaces the RC-side ground truth: the AL-seated byte
conflict(s) and their real candidate lists, so the agent immediately
knows which case applies instead of grinding tie levers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_SWAP_RE = re.compile(r"PS uses `(\w+)`, recomp uses `(\w+)`")
_A_FAMILY = {"al", "ah", "ax", "eax"}


def _int_widen_candidate(func: str, file: str | None):
    """Rule 126 int-widen lever gate (source-AST).

    Returns the list of ``unsigned char`` top-scope locals when the
    function is a *bare-AND byte-mask* shape (``unsigned char x = field &
    MASK;`` / plain byte loads) with NO shift operators anywhere in the
    body.  That is the shape where widening those locals to ``int``
    escapes the AL-squat byte-seat coloring (get_education_ov_image
    92b->44b).  The shift exclusion drops the siblings the lever
    REGRESSES (``(field & MASK) >> n`` -- entertainment/industry/water).
    """
    try:
        import pycparser.c_ast as c_ast
        from c2.commands.style_check import _source_index
    except Exception:
        return None
    idx = _source_index()
    ent = idx.get(func)
    if not ent:
        return None
    _path, node, _start = ent
    # Bail if the source uses any shift op -- the regressing-sibling shape.
    has_shift = False
    uchar_locals: list[str] = []

    class _V(c_ast.NodeVisitor):
        def visit_BinaryOp(self, n):
            nonlocal has_shift
            if n.op in ("<<", ">>"):
                has_shift = True
            self.generic_visit(n)

        def visit_Decl(self, n):
            t = n.type
            if isinstance(t, c_ast.TypeDecl) and isinstance(
                    t.type, c_ast.IdentifierType):
                names = t.type.names
                if names == ["unsigned", "char"] and n.name:
                    uchar_locals.append(n.name)
            self.generic_visit(n)

    try:
        _V().visit(node)
    except Exception:
        return None
    if has_shift or len(uchar_locals) < 2:
        return None
    return uchar_locals


@dataclass
class AlSquatHint:
    func: str
    lines: list[str] = field(default_factory=list)


def _ps_copy_and_srcs(ps_insns) -> list[str]:
    """PS-side Rule 127 signature: `mov al,<byte reg != al>` directly followed
    by `and eax,0xff` -- the re-extend of a ROVER-seated CSE temp.  Returns
    the source byte registers (e.g. ['ch'])."""
    out = []
    if not ps_insns:
        return out
    byte_regs = {"ah", "bl", "bh", "cl", "ch", "dl", "dh"}
    for k in range(len(ps_insns) - 1):
        t = ps_insns[k][3].replace(",", " ").split()
        n = ps_insns[k + 1][3].replace(",", " ").split()
        if (len(t) == 3 and t[0] == "mov" and t[1] == "al" and t[2] in byte_regs
                and len(n) == 3 and n[0] == "and" and n[1] == "eax"
                and n[2] in {"0xff", "255"}):
            out.append(t[2])
    return out


def detect(func: str, hints, *, file: str | None = None,
           ps_insns=None) -> AlSquatHint | None:
    pairs = set()
    for h in hints:
        if h is None or getattr(h, "rule", None) != "Byte-reg swap":
            continue
        m = _SWAP_RE.search(getattr(h, "summary", ""))
        if not m:
            continue
        ps_reg, rc_reg = m.group(1), m.group(2)
        if rc_reg in _A_FAMILY and ps_reg not in _A_FAMILY:
            pairs.add((ps_reg, rc_reg))
    if not pairs:
        return None
    # The int-widen lever (source-AST gate) fires on the AL-squat asm
    # signature alone; it does not need the regalloc trace image.
    out = []
    widen = _int_widen_candidate(func, file)
    if widen:
        names = ", ".join(widen[:6])
        out.append(
            "AL-squat (Rule 126) int-widen LEVER: this is a bare-AND "
            f"byte-mask shape (no shifts).  Try widening the `unsigned char` "
            f"locals to `int` ({names}) -- it drops the byte-seat (DH/DL) "
            "coloring and recovers PS's control-flow/compare structure "
            "(get_education_ov_image 92b->44b).  Semantically identical "
            "(loads stay byte loads, masks are int-promoted).  VERIFY: the "
            "lever helps the bare-AND idiom but can regress siblings with an "
            "extra byte value (terrain) -- re-run decomp-verify after.")
    pair_s = ", ".join(f"PS {p}\u2194RC {q}" for p, q in sorted(pairs))
    try:
        from c2.commands.regalloc_hints import _lookup
        r, _cost, _base = _lookup(func, file)
    except Exception:
        r = None
    squatters = []
    if r:
        squatters = [a for a in r.get("alloc", [])
                     if a.get("regclass_name") == "byte"
                     and a.get("reg_name") in ("AL", "AH")]
    if not squatters and not out:
        return None
    r127 = _ps_copy_and_srcs(ps_insns)
    if r127:
        out.append(
            "AL-squat / Rule 127 OVERRIDE: PS re-extends the byte value from "
            f"{','.join(r127)} via `mov al,<reg>; and eax,0xff` (binir "
            "zext_copy_and) -> PS's value is a ROVER-SEATED CSE temp, not an "
            "allocator conflict.  Lever: delete the named byte local and "
            "write the EXPRESSION TWICE (e.g. `if (bm[i+1] != 0) f(bm[i+1],0);`) "
            "-- the commoned load takes the next byte-rover slot and shifts "
            "every later byte rover pick +1 (battle_action 316b -> exact).  "
            "The Rule 126 mask levers below do NOT apply to this case.  "
            "CAVEAT: the same asm shape also arises when a NAMED byte local "
            "(e.g. seated AH) is re-extended into an allocator-EAX funnel "
            "temp (get_reg_geog family) -- if the GB line shows an EAX "
            "conflict with MOV credit covering this site, it is a funnel "
            "seat question, not Rule 127; probe both forms.")
    for a in squatters:
        tag = a.get("var") or f"t.{a['conf'][-4:]}"
        tc = a.get("tree_cands")
        cand_s = ",".join(tc) if tc else "(no bt record -- rebuild trace image)"
        if tc and "AL" in tc:
            # The CONFIRMED mask channel (get_industry_ov_image, 2026-06-10):
            # a byte value live across a separate `xor eax,eax; mov al,<b>`
            # extension gets EAX into its with.regs (NeighboursUse channel
            # C), and the [base] ADDRESS temp masks whichever byte value is
            # loaded FIRST (it stays live to the later field load).  PS
            # parity = make THIS value allocate AFTER an overlapping EAX
            # temp (zext or addr): demote its savings below them, or extend
            # its live range across one (second zext use / later last-use).
            verdict = ("AL present in RC cand list AND wr A-clean -> this "
                       "value allocates BEFORE every overlapping EAX temp.  "
                       "Lever class (PROVEN): zext-overlap mask -- demote "
                       "this conflict below the EAX zext/addr temps "
                       "(savings), or keep it live across one (re-extended "
                       "use).  Tie levers PROVABLY irrelevant")
            wr = a.get("withregs")
            if wr is not None and (wr & 0x3):
                verdict = ("wr has A-bits -> zext-overlap mask ALREADY firing "
                           "for this conflict (it will land in the D family); "
                           "if the asm still shows AL, the squatter is a "
                           "DIFFERENT byte conflict -- re-read the walk")
        elif tc:
            verdict = ("AL ABSENT from cand list -> BuildRegTree narrowed it; "
                       "find which source shape triggers the narrowing (this "
                       "is the lever)")
        else:
            verdict = "need bt data for the verdict"
        out.append(
            f"AL-squat (Rule 126): byte conflict s{a['savings']}:{tag}->{a['reg_name']} "
            f"({pair_s}); saves==0 class -- decl/use/creation-order levers "
            f"PROVABLY irrelevant (no CONVERT credit in CountRegMoves).  "
            f"cand list: {cand_s}.  {verdict}.  "
            f"See watcom10.0a docs/al-squat-family.md.")
    return AlSquatHint(func, out)


def render_lines(h: AlSquatHint) -> list[str]:
    return h.lines
