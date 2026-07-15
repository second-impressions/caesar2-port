"""Per-statement PS<->RC correspondence from line cues (the statement map).

Statement-boundary cues (``-d1`` debug lines) are layout-independent: a
cue's POSITION in the aligned instruction stream survives the comments /
blank lines that make absolute line numbers incomparable.  Segmenting the
aligned rows at PS cue positions therefore yields the ORIGINAL's statement
structure, and the RC cues falling inside each segment give the
correspondence:

    PS L+10 <-> RC L+12            1:1   (statement matched)
    PS L+10 <-> RC {L+12, L+13}    SPLIT (our source uses 2 statements /
                                          lines where the original has 1 --
                                          the ||/multi-stmt-line signature)
    PS L+10, L+11 <-> RC L+12      MERGE (original splits, ours combines)

On top of the map, each DIVERGING segment gets a forward-vs-reverse IR
comparison at statement granularity: the forward shapes are the trace
IRForest's statement roots whose source line falls in the segment's RC
lines; the reverse shapes come from ``binir.recover`` over the segment's
PS instructions.  Structural ops present on only one side are the
intermediate constructs to add/remove at THAT statement (the per-statement
refinement of ``c2 tree-diff``).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StmtSeg:
    ps_cue: str                          # "L+10"
    rc_cues: list = field(default_factory=list)   # ["L+12", ...]
    ps_insns: list = field(default_factory=list)
    rc_insns: list = field(default_factory=list)
    rc_abs_lines: set = field(default_factory=set)
    has_diff: bool = False
    fwd_only: dict = field(default_factory=dict)  # op -> count
    rev_only: dict = field(default_factory=dict)


@dataclass
class StmtMapHint:
    func: str
    segs: list = field(default_factory=list)
    n_one_to_one: int = 0


_STRUCTURAL = ("BINARY:", "UNARY:", "COMPARE:", "ASSIGN", "PRE_GETS",
               "POST_GETS", "CALL", "COND_BRANCH")


def _structural_ops(shapes) -> Counter:
    """Flatten shapes to a multiset of structural op names (leaves and
    raw_asm excluded -- they only add alignment noise)."""
    out: Counter = Counter()

    def walk(s):
        if s.op.startswith(_STRUCTURAL):
            out[s.op] += 1
        for c in s.children:
            walk(c)

    for s in shapes:
        walk(s)
    return out


def build(name: str, rows: list, ps_cues: dict, rc_cues: dict,
          rc_abs: Optional[dict] = None,
          forest=None) -> Optional[StmtMapHint]:
    """Build the statement map from aligned ``rows`` and the per-rel-offset
    cue maps (``ps_cues``/``rc_cues`` as produced by the side-by-side
    renderer's ``_per_insn_lines``; ``rc_abs`` maps RC rel offset ->
    ABSOLUTE RC source line for the forward-IR join)."""
    segs: list[StmtSeg] = []
    cur: Optional[StmtSeg] = None
    cur_rc_abs: Optional[int] = None
    for row in rows:
        o, r = row.get("o"), row.get("r")
        if o is not None:
            cue = ps_cues.get(o[0])
            if cue:
                cur = StmtSeg(ps_cue=cue)
                segs.append(cur)
        if cur is None:
            continue            # prologue rows before the first statement
        if o is not None:
            cur.ps_insns.append(o)
        if r is not None:
            rcue = rc_cues.get(r[0])
            if rcue:
                cur.rc_cues.append(rcue)
            if rc_abs is not None:
                ln = rc_abs.get(r[0])
                if ln is not None:
                    cur_rc_abs = ln
            if cur_rc_abs is not None:
                cur.rc_abs_lines.add(cur_rc_abs)
            cur.rc_insns.append(r)
        if row.get("kind") != "equal":
            cur.has_diff = True
    if not segs:
        return None
    h = StmtMapHint(func=name, segs=segs)
    h.n_one_to_one = sum(1 for s in segs if len(s.rc_cues) == 1)

    # Forward-vs-reverse IR per diverging segment (needs the trace forest).
    if forest is not None:
        try:
            from c2 import binir
            from c2.tree_diff import shape_from_ir_forest, shape_from_binir_ops
            fwd_all = shape_from_ir_forest(forest)
        except Exception:
            fwd_all = []
        for s in segs:
            if not s.has_diff or not s.ps_insns or not s.rc_abs_lines:
                continue
            try:
                fwd = [sh for sh in fwd_all
                       if sh.detail.get("line") in s.rc_abs_lines]
                rev = shape_from_binir_ops(binir.recover(s.ps_insns))
            except Exception:
                continue
            if not fwd and not rev:
                continue
            f_ops = _structural_ops(fwd)
            r_ops = _structural_ops(rev)
            s.fwd_only = dict(f_ops - r_ops)
            rev_only = r_ops - f_ops
            # Representation-artifact suppression (battle_action lesson,
            # 2026-06-10): binir recovers `test/cmp + jcc` as COMPARE nodes
            # while the FORWARD tree folds call-result truth tests -- a
            # PS-only COMPARE that our own RC asm ALSO contains is not a
            # source difference, just the two IR representations.  Subtract
            # anything the RC-side binir recovery has as well: what is left
            # is a TRUE asm-level asymmetry.
            try:
                rc_ops = _structural_ops(
                    shape_from_binir_ops(binir.recover(s.rc_insns)))
            except Exception:
                rc_ops = type(r_ops)()
            s.rev_only = dict(rev_only - rc_ops)
    return h


def render_lines(h: StmtMapHint, max_entries: int = 6) -> list[str]:
    """Compact rendering: the non-1:1 segments (the structure deltas) and
    the per-statement forward/reverse IR asymmetries."""
    out: list[str] = []
    odd = [s for s in h.segs if len(s.rc_cues) != 1]
    if odd:
        bits = []
        for s in odd[:max_entries]:
            if not s.rc_cues:
                bits.append(f"{s.ps_cue}\u2194\u2205(RC continues prev line)")
            else:
                bits.append(f"{s.ps_cue}\u2194{{{','.join(s.rc_cues)}}}SPLIT")
        out.append(
            f"stmt-map: {len(h.segs)} PS statement(s), {h.n_one_to_one} map "
            f"1:1; structure deltas: " + "  ".join(bits)
            + (" \u2026" if len(odd) > max_entries else ""))
    ir_lines = []
    for s in h.segs:
        if not s.fwd_only and not s.rev_only:
            continue
        rc_l = ",".join(f"L{x}" for x in sorted(s.rc_abs_lines)[:3])
        bits = []
        if s.fwd_only:
            bits.append("forward-only " + ",".join(
                f"{k}\u00d7{v}" for k, v in sorted(s.fwd_only.items())))
        if s.rev_only:
            bits.append("PS-only " + ",".join(
                f"{k}\u00d7{v}" for k, v in sorted(s.rev_only.items())))
        ir_lines.append(f"  {s.ps_cue}(PS)~{rc_l}(RC): " + "; ".join(bits))
    if ir_lines:
        out.append("stmt-IR (per diverging statement, forward=our trace "
                   "tree, PS=binir-recovered; forward-only ops are the "
                   "intermediate constructs OUR source adds at that "
                   "statement -- remove them there; PS-only = constructs "
                   "to add, real asm asymmetries only -- anything our own "
                   "asm also contains is suppressed as representation):")
        out.extend(ir_lines[:max_entries])
        if len(ir_lines) > max_entries:
            out.append(f"  \u2026 {len(ir_lines) - max_entries} more")
    return out
