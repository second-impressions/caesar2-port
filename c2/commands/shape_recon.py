"""`c2 shape-recon <fn>` -- witness-reconciliation shape inference.

Fuses three independent structural witnesses of the lost original source
into a single candidate STATEMENT SKELETON, with a per-statement
agreement classification and a corpus-wide agreement metric.

  Witness A -- PS ``-d1`` line table : statement boundaries + source
               order (Hard Rule #4).  Axis: asm-offset.  (this module's
               ``ps_statement_spine``; mirrors ``c2 line-skeleton``.)
  Witness B -- Mac CodeWarrior decompile : control-flow nesting + local
               types + per-statement expression shape, independent of
               Watcom codegen.  Axis: PPC (no shared offsets), aligned
               structurally.  (``c2.mac.clean`` -> pycparser AST.)
  Witness C -- binir IR reconstruction : per-statement IR shape, the
               byte-exact spec.  Axis: asm-offset.  (``c2.binir.recover``)

A and C share the asm-offset axis and align with zero ambiguity.  B
lives on a separate axis and is aligned onto the PS spine by an
anchor-based monotonic sequence alignment (calls / globals / comparison
constants are compiler-independent tokens).

See ``docs/shape-inference-witness-reconciliation.md`` for the full
design rationale, data model and prior-art mapping.

Usage::

    c2 shape-recon place2_a_building_base
    c2 shape-recon place2_a_building_base --json
    c2 shape-recon place2_a_building_base --no-mac      # A+C only (fast)
    c2 shape-recon --corpus --limit 40                  # go/no-go metric
"""
from __future__ import annotations

import bisect
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Annotated, Optional

import typer

_SYMS = Path("data/out/symbols.json")
_CODE = Path("data/out/le_code.bin")

# Structural op prefixes shared with stmt_map (leaves/raw_asm excluded).
_STRUCTURAL = ("BINARY:", "UNARY:", "COMPARE:", "ASSIGN", "PRE_GETS",
               "POST_GETS", "CALL", "COND_BRANCH")


# ════════════════════════════════════════════════════════════════════════
#  Data model  (see spec §1)
# ════════════════════════════════════════════════════════════════════════


@dataclass
class Disagreement:
    axis: str        # order | nesting | type | ir-shape | boundary | missing
    detail: str
    witness_lo: str  # which witness disagrees with the spine


@dataclass
class Statement:
    idx: int
    ps_line: int
    ps_line_rel: str
    byte_span: tuple
    multi_stmt: bool
    backward: bool
    # Witness A
    a_summary: list = field(default_factory=list)
    a_calls: list = field(default_factory=list)
    a_globals: list = field(default_factory=list)
    a_cmp_consts: list = field(default_factory=list)
    a_consts: list = field(default_factory=list)
    a_arcs: list = field(default_factory=list)   # (target_rel, "fwd"/"back"/"self")
    # Witness C
    c_ops: dict = field(default_factory=dict)
    c_summary: str = ""
    # Witness B
    b_construct: Optional[str] = None
    b_nesting: list = field(default_factory=list)
    b_types: dict = field(default_factory=dict)
    b_align_conf: float = 0.0
    b_expr: str = ""
    # RC correspondence (best-effort)
    rc_cues: list = field(default_factory=list)
    rc_rel: str = ""
    rc_diff: bool = False
    # Verdict
    witnesses: int = 1
    confidence: str = "low"
    disagreements: list = field(default_factory=list)


@dataclass
class ShapeSkeleton:
    func: str
    file: str
    statements: list = field(default_factory=list)
    n_high: int = 0
    n_medium: int = 0
    n_low: int = 0
    mac_aligned: int = 0
    mac_total: int = 0
    # coverage = fraction of (byte-weighted) statements that have >=2 witnesses
    #   (A + B and/or C) -- how much we can say anything about.
    # concordance = among those informative statements, the fraction with NO
    #   shape conflict -- the CORRECTNESS signal (the witnesses agree).
    # agreement_score is kept as an alias for concordance (back-compat).
    coverage: float = 0.0
    concordance: float = 0.0
    agreement_score: float = 0.0


# ════════════════════════════════════════════════════════════════════════
#  Symbol / disasm substrate
# ════════════════════════════════════════════════════════════════════════


class _Syms:
    """Lazily-loaded symbol tables + le_code, shared across a session."""

    def __init__(self, symbols_json: Path = _SYMS, code_bin: Path = _CODE):
        d = json.loads(symbols_json.read_text())
        self.d = d
        self.code_syms = sorted(
            (s for s in d["symbols"]
             if s["kind"].endswith("code") and s["segment"] == 1),
            key=lambda s: s["offset"])
        self.by_name = {s["name"]: i for i, s in enumerate(self.code_syms)}
        self.code_offs = [s["offset"] for s in self.code_syms]
        self.data_syms = sorted(
            (s for s in d["symbols"] if s["is_data"] and s["segment"] == 2),
            key=lambda s: s["offset"])
        self.data_offs = [s["offset"] for s in self.data_syms]
        self.le_code = code_bin.read_bytes()

    def dsym(self, off: int) -> str:
        j = bisect.bisect_right(self.data_offs, off) - 1
        if j < 0:
            return hex(off)
        s = self.data_syms[j]
        delta = off - s["offset"]
        return s["name"] + (f"+{delta:#x}" if delta else "")

    def csym(self, off: int) -> Optional[str]:
        j = bisect.bisect_right(self.code_offs, off) - 1
        if j >= 0 and self.code_offs[j] == off:
            return self.code_syms[j]["name"]
        return None


_SYMS_CACHE: Optional[_Syms] = None


def _get_syms(symbols_json: Path = _SYMS) -> _Syms:
    global _SYMS_CACHE
    if _SYMS_CACHE is None:
        _SYMS_CACHE = _Syms(symbols_json)
    return _SYMS_CACHE


def _disasm(code: bytes) -> list:
    """(addr, size, raw, 'mnem op') tuples, base 0 -- the binir InsnT shape."""
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    out = []
    for ins in md.disasm(code, 0):
        out.append((ins.address, ins.size, bytes(ins.bytes),
                    f"{ins.mnemonic} {ins.op_str}".strip()))
    decoded = sum(s for _, s, _, _ in out)
    if decoded < len(code):
        tail = code[decoded:]
        out.append((decoded, len(tail), tail, f"<raw {len(tail)}b>"))
    return out


# ════════════════════════════════════════════════════════════════════════
#  Witness A -- PS statement spine  (mirrors line_skeleton.py)
# ════════════════════════════════════════════════════════════════════════


@dataclass
class SpineEntry:
    ps_line: int
    rel_off: int
    n_bytes: int
    multi_stmt: bool
    backward: bool
    summary: list
    calls: list
    globals: list
    cmp_consts: list
    consts: list
    arcs: list
    insns: list   # InsnT slice for this span (rel offsets)


# Instructions whose FIRST operand is written (for ->/<- direction tagging).
_WRITES_DEST = frozenset({
    "mov", "lea", "add", "sub", "and", "or", "xor", "inc", "dec",
    "shl", "shr", "sar", "imul", "movzx", "movsx", "neg", "not",
    "adc", "sbb", "mul", "idiv", "div",
})


def ps_statement_spine(name: str, symbols_json: Path = _SYMS) -> Optional[dict]:
    """Build witness A: the PS ``-d1`` statement spine for ``name``.

    Returns ``{"file": str, "first": int, "last": int, "entries":
    list[SpineEntry]}`` (spine in source/asm order, rel offsets) or None
    when the function has no line records (asm module)."""
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs

    S = _get_syms(symbols_json)
    if name not in S.by_name:
        return None
    i = S.by_name[name]
    start = S.code_syms[i]["offset"]
    end = (S.code_syms[i + 1]["offset"] if i + 1 < len(S.code_syms)
           else start + 0x4000)
    mod = S.code_syms[i]["module_index"]

    recs = sorted((r for r in S.d["line_numbers"]
                   if r["module_index"] == mod and start <= r["offset"] < end),
                  key=lambda r: r["offset"])
    if not recs:
        return None

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    ins_by_off = {}
    for ins in md.disasm(S.le_code[start:end], start):
        ins_by_off[ins.address] = ins
        if ins.mnemonic == "ret" and ins.address >= recs[-1]["offset"]:
            end = ins.address + ins.size
            break

    bounds = [r["offset"] for r in recs] + [end]
    entries: list[SpineEntry] = []
    prev_line = None
    for k, r in enumerate(recs):
        line, off = r["line"], r["offset"]
        multi = backward = False
        if prev_line is not None:
            if line == prev_line:
                multi = True
            elif line < prev_line:
                backward = True
        prev_line = line

        summary: list[str] = []
        calls: list[str] = []
        globs: list[str] = []
        cmp_consts: list[int] = []
        consts: list[int] = []
        arcs: list = []
        span_insns: list = []
        o = off
        while o < bounds[k + 1]:
            ins = ins_by_off.get(o)
            if ins is None:
                o += 1
                continue
            span_insns.append((ins.address - start, ins.size,
                               bytes(ins.bytes),
                               f"{ins.mnemonic} {ins.op_str}".strip()))
            mn = ins.mnemonic
            if mn == "call":
                t = int(ins.op_str, 16) if ins.op_str.startswith("0x") else None
                csym = S.csym(t) if t is not None else None
                summary.append(f"call {csym or ins.op_str}")
                if csym:
                    calls.append(csym)
                o += ins.size
                continue
            if mn.startswith("j"):
                t = int(ins.op_str, 16) if ins.op_str.startswith("0x") else None
                if t is not None:
                    rel_t = t - start
                    arc = ("self" if t == off else "back" if t < off else "fwd")
                    arcs.append((rel_t, arc))
                    summary.append(f"{mn}->{rel_t:+#x}({arc})")
                else:
                    summary.append(mn)
                o += ins.size
                continue
            # General operand pass: capture data-symbol memory operands
            # (absolute AND based/indexed -- the array-base pattern) and
            # immediates.
            writes = mn in _WRITES_DEST
            for oi, op in enumerate(ins.operands):
                if op.type == 3 and op.value.mem.disp > 0x1000:
                    nm = S.dsym(op.value.mem.disp)
                    if not nm.startswith("0x"):
                        base = nm.split("+", 1)[0]
                        globs.append(base)
                        indexed = (op.value.mem.base != 0
                                   or op.value.mem.index != 0)
                        st = "->" if (oi == 0 and writes) else "<-"
                        summary.append(f"{st}{base}" + ("[]" if indexed else ""))
                elif op.type == 2:
                    # Skip frame-adjust immediates (sub/add esp|ebp, K) and
                    # tiny shift counts -- they are not source-level constants
                    # and only pollute the anchor set.
                    if mn in ("add", "sub") and ins.op_str.startswith(
                            ("esp", "ebp")):
                        continue
                    if mn in ("shl", "shr", "sar"):
                        continue
                    v = op.value.imm
                    if 0 <= v < 0x10000:
                        consts.append(int(v))
                        if mn in ("cmp", "test", "sub"):
                            cmp_consts.append(int(v))
            if mn in ("cmp", "test"):
                ops_s = ins.op_str
                for op in ins.operands:
                    if op.type == 3 and op.value.mem.disp > 0x1000:
                        nm = S.dsym(op.value.mem.disp)
                        if not nm.startswith("0x"):
                            ops_s = ops_s.replace(hex(op.value.mem.disp), nm)
                summary.append(f"{mn} {ops_s}")
            elif mn == "ret":
                summary.append("ret")
            o += ins.size

        entries.append(SpineEntry(
            ps_line=line, rel_off=off - start, n_bytes=bounds[k + 1] - off,
            multi_stmt=multi, backward=backward, summary=summary,
            calls=_dedup(calls), globals=_dedup(globs),
            cmp_consts=_dedup(cmp_consts), consts=_dedup(consts),
            arcs=arcs, insns=span_insns))

    return {"file": recs[0]["file"], "first": recs[0]["line"],
            "last": recs[-1]["line"], "entries": entries,
            "code": S.le_code[start:end], "start": start}


def _dedup(xs: list) -> list:
    seen = []
    for x in xs:
        if x not in seen:
            seen.append(x)
    return seen


# ════════════════════════════════════════════════════════════════════════
#  Witness C -- binir IR per span
# ════════════════════════════════════════════════════════════════════════


def _structural_multiset(shapes) -> dict:
    from collections import Counter
    out: Counter = Counter()

    def walk(s):
        if s.op.startswith(_STRUCTURAL):
            out[s.op] += 1
        for c in s.children:
            walk(c)

    for s in shapes:
        walk(s)
    return dict(out)


def witness_c(entry: SpineEntry) -> tuple:
    """Return (structural-op multiset, compact summary) for a span via binir."""
    try:
        from c2 import binir
        from c2.tree_diff import shape_from_binir_ops
        ops = binir.recover(entry.insns)
        shapes = shape_from_binir_ops(ops)
        ms = _structural_multiset(shapes)
        # compact: the raw recovered op kinds, deduped with counts
        from collections import Counter
        kinds = Counter(o.kind for o in ops)
        summ = ",".join(f"{k}×{v}" if v > 1 else k
                        for k, v in kinds.most_common(4))
        return ms, summ
    except Exception:
        return {}, ""


# ════════════════════════════════════════════════════════════════════════
#  RC correspondence -- current recovered source's statement structure
#  (Phase 5 hook).  Built from the freshly-recompiled out.exe -d1 marks and
#  aligned to the PS spine with the same anchor engine.  RC and PS are the
#  SAME compiler + (mostly) same source, so calls + comparison constants are
#  near-identical anchors -- no RC global resolution needed.
# ════════════════════════════════════════════════════════════════════════


@dataclass
class RcStmt:
    """An RC source statement (one -d1 line span), shaped like MacStmt so it
    can flow through ``_align``/``_sim``."""
    construct: str
    nesting: list
    calls: list
    globals: list
    consts: list
    cmp_consts: list
    types: dict
    line: int           # RC source line (decomp/src/*.c)
    expr: str
    rel_off: int
    diff: bool = False


_RC_BUILD: Optional[tuple] = None    # (out_exe, out_map, code_bin, line_lut)


def _ensure_rc_build(decomp_dir: Path = Path("decomp")):
    """Incremental recompile once per process; cache (out_exe, out_map,
    code_bin, line_lut).  Returns None on build failure."""
    global _RC_BUILD
    if _RC_BUILD is not None:
        return _RC_BUILD
    try:
        from c2.commands.decomp_verify import (
            _build_all, _load_le_code_and_fixups, PS_CFLAGS, _DEFAULT_IMAGE)
        from c2.commands.oracle import _load_oracle_line_lookup
        ok, _out, _work, out_exe, out_map = _build_all(
            decomp_dir / "src", decomp_dir / "include",
            _DEFAULT_IMAGE, PS_CFLAGS, use_cache=True)
        if not ok:
            return None
        code_bin, _fix = _load_le_code_and_fixups(Path(out_exe))
        line_lut = _load_oracle_line_lookup(Path(out_exe))
    except Exception:
        return None
    _RC_BUILD = (Path(out_exe), Path(out_map), code_bin, line_lut)
    return _RC_BUILD


def _rc_spine(name: str, *, decomp_dir: Path = Path("decomp")):
    """Build the RC statement spine for ``name`` from a (cached, incremental)
    recompile.  Returns ``list[RcStmt]`` or None on any failure (build error,
    function absent from the RC map)."""
    try:
        from c2.commands.decomp_verify import _parse_map
    except Exception:
        return None
    built = _ensure_rc_build(decomp_dir)
    if built is None:
        return None
    out_exe, out_map, code_bin, line_lut = built
    try:
        syms = _parse_map(Path(out_map))
    except Exception:
        return None
    mangled = name + "_"
    if mangled not in syms:
        return None
    items = sorted(syms.items(), key=lambda kv: kv[1])
    offs = [o for _, o in items]
    names = [n for n, _ in items]
    start = syms[mangled]
    j = offs.index(start)
    end = offs[j + 1] if j + 1 < len(offs) else start + 0x4000

    def rc_csym(addr):
        k = bisect.bisect_right(offs, addr) - 1
        if k >= 0 and offs[k] == addr:
            nm = names[k]
            return nm[:-1] if nm.endswith("_") else nm
        return None

    code = code_bin[start:end]
    # RC -d1 marks within the function, as rel offsets.
    marks = sorted((off - start, ln) for off, ln in line_lut.items()
                   if start <= off < end)
    if not marks:
        return None

    from capstone import CS_ARCH_X86, CS_MODE_32, Cs
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    ins = [(i.address, i.size, i.mnemonic, i.op_str, i.operands)
           for i in md.disasm(code, 0)]
    bounds = [m[0] for m in marks] + [len(code)]

    stmts: list[RcStmt] = []
    for k, (moff, ln) in enumerate(marks):
        calls, cmp_consts, consts = [], [], []
        construct = "other"
        for (a, sz, mn, ops, operands) in ins:
            if not (moff <= a < bounds[k + 1]):
                continue
            if mn == "call":
                t = int(ops, 16) if ops.startswith("0x") else None
                nm = rc_csym(start + t) if t is not None else None
                if nm:
                    calls.append(nm)
                    construct = "call"
            elif mn.startswith("j") and mn != "jmp":
                if construct == "other":
                    construct = "if"
            else:
                for op in operands:
                    if op.type == 2:
                        if mn in ("add", "sub") and ops.startswith(("esp", "ebp")):
                            continue
                        if mn in ("shl", "shr", "sar"):
                            continue
                        v = op.value.imm
                        if 0 <= v < 0x10000:
                            consts.append(int(v))
                            if mn in ("cmp", "test", "sub"):
                                cmp_consts.append(int(v))
        stmts.append(RcStmt(
            construct=construct, nesting=[], calls=_dedup(calls), globals=[],
            consts=_dedup(consts), cmp_consts=_dedup(cmp_consts), types={},
            line=ln, expr="", rel_off=moff))
    return stmts, code


# ════════════════════════════════════════════════════════════════════════
#  Whole-surface line-mark divergence map (the cheap, no-Mac sweep)
# ════════════════════════════════════════════════════════════════════════


def _iter_function_marks(symbols_json: Path = _SYMS):
    """Yield ``(name, file, is_exact, ps_marks, rc_marks)`` for every
    decompiled function, where ``*_marks`` are sorted ``[(rel_off, line)]``
    drawn from CACHED data only (one RC build's `-d1` table + `symbols.json`).
    Each range is bounded by the function's KNOWN size (not "next map symbol",
    which truncates when Watcom places a symbol inside a function)."""
    import bisect
    from collections import defaultdict
    try:
        from c2.commands.decomp_verify import _parse_map
    except Exception:
        return
    built = _ensure_rc_build()
    if built is None:
        return
    _oe, out_map, _cb, line_lut = built
    try:
        rc_syms = _parse_map(Path(out_map))
    except Exception:
        return
    rc_off_sorted = sorted(rc_syms.values())
    rc_items = sorted(line_lut.items())          # [(offset, line)]
    rc_offs = [o for o, _ in rc_items]

    S = _get_syms(symbols_json)
    ps_by_mod: dict = defaultdict(list)
    for r in S.d["line_numbers"]:
        ps_by_mod[r["module_index"]].append((r["offset"], r["line"]))
    for k in ps_by_mod:
        ps_by_mod[k].sort()

    status: dict = {}
    try:
        from c2.commands.verify_json import get_verify_json
        for f in get_verify_json(no_build=True).get("functions", []):
            status[f["name"]] = (
                f.get("diff_byte_count", 0) == 0, f.get("file", "?"),
                f.get("size"), f.get("recomp_size") or f.get("size"))
    except Exception:
        pass

    for i, s in enumerate(S.code_syms):
        name = s["name"]
        rc_start = rc_syms.get(name + "_")
        if rc_start is None:
            continue
        is_exact, file, ps_size, rc_size = status.get(
            name, (None, "?", None, None))
        ps_start = s["offset"]
        ps_end = (ps_start + ps_size if ps_size else
                  (S.code_syms[i + 1]["offset"] if i + 1 < len(S.code_syms)
                   else ps_start + 0x4000))
        recs = ps_by_mod.get(s["module_index"], [])
        lo = bisect.bisect_left(recs, (ps_start,))
        hi = bisect.bisect_left(recs, (ps_end,))
        ps_marks = [(o - ps_start, l) for o, l in recs[lo:hi]]
        if not ps_marks:
            continue
        if rc_size:
            rc_end = rc_start + rc_size
        else:
            j = bisect.bisect_right(rc_off_sorted, rc_start)
            rc_end = rc_off_sorted[j] if j < len(rc_off_sorted) else rc_start + 0x4000
        lo2 = bisect.bisect_left(rc_offs, rc_start)
        hi2 = bisect.bisect_left(rc_offs, rc_end)
        rc_marks = [(o - rc_start, l) for o, l in rc_items[lo2:hi2]]
        yield name, file, is_exact, ps_marks, rc_marks


def _sgn(x: int) -> int:
    return 1 if x > 0 else -1 if x < 0 else 0


def _trajectory(ps_marks: list, rc_marks: list) -> Optional[dict]:
    """TRAJECTORY divergence: do PS and RC have the same forward/backward
    code-flow direction, with the direction SWITCHES lining up -- ignoring
    line counts, packing, comments and blank lines?

    Anchors are the marks PS and RC share by (function-relative) byte offset
    -- the corresponding statements (byte-exact => offsets coincide).  Over
    those anchors we compare the SIGN of each line step (+ forward, - backward,
    0 same-line); a backward step is a real reordering/loop, NOT a split
    (splits are forward insertions), so this is packing/comment-invariant.
    ``switch_mismatch`` counts anchors where PS and RC disagree on direction
    (the choose_odd_tune smell).  ``ratio`` is reccmp's pinned-sequence match
    over the FULL sign trajectories, anchored at those offsets -- so extra/
    missing lines are absorbed as insertions, not penalised as divergence.
    Returns None when there are too few shared anchors to judge."""
    ps_l = {o: l for o, l in ps_marks}
    rc_l = {o: l for o, l in rc_marks}
    common = sorted(set(ps_l) & set(rc_l))
    if len(common) < 3:
        return None
    ps_s = [_sgn(ps_l[common[i]] - ps_l[common[i - 1]])
            for i in range(1, len(common))]
    rc_s = [_sgn(rc_l[common[i]] - rc_l[common[i - 1]])
            for i in range(1, len(common))]
    mism_off = [common[i + 1] for i in range(len(ps_s))
                if ps_s[i] != rc_s[i]]
    # reccmp pinned-sequence ratio over the full sign trajectories.
    ratio = 1.0 - len(mism_off) / max(1, len(ps_s))
    try:
        from reccmp.compare.pinned_sequences import SequenceMatcherWithPins
        A = [str(_sgn(ps_marks[i][1] - ps_marks[i - 1][1]))
             for i in range(1, len(ps_marks))]
        B = [str(_sgn(rc_marks[i][1] - rc_marks[i - 1][1]))
             for i in range(1, len(rc_marks))]
        pi = {o: k for k, (o, _) in enumerate(ps_marks)}
        ri = {o: k for k, (o, _) in enumerate(rc_marks)}
        pins, pa, pb = [], -1, -1
        for o in common:
            a, b = pi[o] - 1, ri[o] - 1
            if a > pa and b > pb:          # strictly monotonic, valid
                pins.append((a, b)); pa, pb = a, b
        if A and B:
            ratio = SequenceMatcherWithPins(A, B, pins).ratio()
    except Exception:
        pass
    return {"anchors": len(common), "switch_mismatch": len(mism_off),
            "mismatch_offsets": mism_off[:8], "ratio": round(ratio, 3)}


def mark_divergence_rows(symbols_json: Path = _SYMS) -> Optional[list]:
    """Whole-surface shape-divergence rows from CACHED data (RC build `-d1`
    table + `symbols.json`; no disasm/binir/Mac).  Two signals per function:

    * ``delta`` = ``rc_marks - ps_marks`` -- the line-COUNT divergence
      (over-split / over-merged).  Strict on packing; flags comment/blank-
      line-style restructuring you may not care about.
    * ``traj`` (`_trajectory`) -- the forward/backward TRAJECTORY divergence
      (`switch_mismatch` + reccmp `ratio`): are the direction SWITCHES lined
      up, ignoring counts/packing/comments?  This is the source-shape smell
      that actually matters (statement reordering).

    Returns rows sorted by trajectory divergence (most-divergent first;
    `switch_mismatch` desc, then `1 - ratio`), or None if the build is
    unavailable."""
    any_yield = False
    rows = []
    for name, file, is_exact, ps_marks, rc_marks in _iter_function_marks(
            symbols_json):
        any_yield = True
        traj = _trajectory(ps_marks, rc_marks)
        rows.append({
            "name": name, "file": file, "exact": is_exact,
            "ps_marks": len(ps_marks), "rc_marks": len(rc_marks),
            "delta": len(rc_marks) - len(ps_marks),
            "anchors": traj["anchors"] if traj else 0,
            "switch_mismatch": traj["switch_mismatch"] if traj else 0,
            "traj_ratio": traj["ratio"] if traj else None,
            "mismatch_offsets": traj["mismatch_offsets"] if traj else []})
    if not any_yield:
        return None
    rows.sort(key=lambda r: (r["switch_mismatch"],
                             1.0 - (r["traj_ratio"] or 1.0),
                             abs(r["delta"])), reverse=True)
    return rows


def shape_divergence_report(symbols_json: Path = _SYMS, *, top: int = 40,
                            scope: str = "all", json_out: bool = False) -> None:
    """Render the whole-surface line-mark divergence map (see
    :func:`mark_divergence_rows`).  ``scope``: ``all`` | ``diff`` | ``exact``.
    Hosted by ``c2 decomp-verify --shape-divergence``."""
    rows = mark_divergence_rows(symbols_json)
    if rows is None:
        typer.secho("[!] RC build unavailable; run `c2 decomp-verify` once",
                    fg="red")
        raise typer.Exit(1)
    if scope == "diff":
        rows = [r for r in rows if r["exact"] is False]
    elif scope == "exact":
        rows = [r for r in rows if r["exact"] is True]
    # The actionable signal is TRAJECTORY divergence (direction switches that
    # don't line up) -- robust to line counts / packing / comments.  Functions
    # with switch_mismatch == 0 have the same forward/backward code-flow shape,
    # however differently they pack statements onto lines.
    diverging = [r for r in rows if r["switch_mismatch"] > 0]
    if json_out:
        typer.echo(json.dumps(diverging))
        return
    n_total = len([r for r in rows if r["anchors"] >= 3])
    n_div = len(diverging)
    typer.secho(
        "\n# shape divergence (whole surface): forward/backward TRAJECTORY of "
        "the -d1 line stream", fg="cyan", bold=True)
    typer.echo(
        f"#   {n_div}/{n_total} judged functions have direction SWITCHES that "
        f"do NOT line up with PS")
    typer.echo(
        "#   switch = # anchor statements where PS and RC disagree on "
        "forward/backward (the reorder smell); ratio = reccmp pinned-sequence "
        "trajectory match (1.0 = identical flow).")
    typer.echo(
        "#   delta (RC-PS line count) shown for context only -- NOT ranked on "
        "(packing/comments are ignored).")
    typer.echo(f"#   {'switch':>6} {'ratio':>5} {'anc':>4} {'delta':>6}  "
               f"{'status':<6}  function (file)")
    for r in diverging[:top]:
        st = ("exact" if r["exact"] else "diff " if r["exact"] is False
              else "?")
        rt = f"{r['traj_ratio']:.2f}" if r["traj_ratio"] is not None else "  - "
        typer.echo(
            f"    {r['switch_mismatch']:>6} {rt:>5} {r['anchors']:>4} "
            f"{r['delta']:>+6}  {st:<6}  {r['name']}  ({r['file']})")
    if n_div > top:
        typer.echo(f"#   … {n_div - top} more.  `c2 shape-recon <fn>` for the "
                   f"per-statement breakdown.")


# ════════════════════════════════════════════════════════════════════════
#  Witness B -- Mac AST  (Phase 2)
# ════════════════════════════════════════════════════════════════════════


@dataclass
class MacStmt:
    construct: str          # if | else-if | for | while | do | switch |
                            #   assign | call | return | other
    nesting: list           # enclosing construct path
    calls: list
    globals: list
    consts: list
    cmp_consts: list
    types: dict
    line: int
    expr: str               # short rendering for display
    ops: list = field(default_factory=list)   # canonical computation-shape ops


# Canonical computation-shape op vocabulary, shared by the PS (binir) and Mac
# (AST) sides so an ANCHORLESS arithmetic statement can still align by the
# shape of its computation (a shift+add+store, a divide, a cast, ...).
_MAC_BINOP = {
    "+": "add", "-": "sub", "*": "mul", "<<": "mul", "/": "div",
    ">>": "div", "%": "div", "&": "and", "|": "or", "^": "xor",
    "==": "cmp", "!=": "cmp", "<": "cmp", ">": "cmp",
    "<=": "cmp", ">=": "cmp",
}


def _mac_ops(node) -> list:
    """Canonical computation-shape ops in a Mac AST subtree."""
    import pycparser.c_ast as ca
    out: list[str] = []

    def walk(n):
        if n is None:
            return
        if isinstance(n, ca.BinaryOp):
            t = _MAC_BINOP.get(n.op)
            if t:
                out.append(t)
        elif isinstance(n, ca.Cast):
            out.append("cast")
        elif isinstance(n, ca.Assignment):
            out.append("assign")
        for _, c in (n.children() if hasattr(n, "children") else []):
            walk(c)

    walk(node)
    return _dedup(out)


def _canon_ps_ops(c_ops: dict) -> list:
    """Map binir structural-op names (BINARY:O_TIMES, UNARY:O_CONVERT, ...)
    into the same canonical vocabulary as :func:`_mac_ops`."""
    out: set[str] = set()
    for name in c_ops:
        if name.startswith("COMPARE") or "O_CMP" in name:
            out.add("cmp")
        elif "O_CONVERT" in name:
            out.add("cast")
        elif "O_TIMES" in name or "O_MUL" in name or "O_LSHIFT" in name:
            out.add("mul")
        elif "O_PLUS" in name:
            out.add("add")
        elif "O_MINUS" in name:
            out.add("sub")
        elif "O_DIV" in name or "O_MOD" in name or "O_RSHIFT" in name:
            out.add("div")
        elif "O_AND" in name:
            out.add("and")
        elif "O_OR" in name:
            out.add("or")
        elif "O_XOR" in name:
            out.add("xor")
        elif name.startswith("ASSIGN"):
            out.add("assign")
    return list(out)


def _mac_raw(name: str) -> Optional[str]:
    """Raw Ghidra Mac decompile text for ``name``, disk-cached so repeated
    shape-recon / corpus runs don't re-spin Ghidra.

    Thin wrapper over ``mac.decompile_cached`` (the shared cache-or-fetch
    primitive, symmetric with ``c2win.decompile_cached``); the cache lives at
    ``.c2-cache/mac/decompile/<name>.c`` and an empty file records a known-miss
    (function absent from the Mac binary) to avoid re-querying.
    """
    try:
        import mac as macmod
        return macmod.decompile_cached(name)
    except Exception:
        return None


def _mac_funcdef(name: str):
    """Return the cleaned pycparser FuncDef for ``name`` from the Mac
    build, or None (best-effort; uses the disk cache)."""
    raw = _mac_raw(name)
    if not raw:
        return None
    try:
        from c2.mac.clean import clean_decompile_ast
        fdef, err = clean_decompile_ast(raw)
        return fdef
    except Exception:
        return None


def _lower_mac(fdef, globals_set) -> list:
    """Flatten a cleaned FuncDef AST into a linear MacStmt stream in source
    order: each control construct emits a MacStmt for its CONDITION, then
    recursion descends into the body (mirroring the PS spine's
    linearisation of conditions then bodies)."""
    import pycparser.c_ast as ca

    out: list[MacStmt] = []
    types: dict[str, str] = {}

    def _type_str(node) -> str:
        try:
            from pycparser import c_generator
            return c_generator.CGenerator().visit(node.type)
        except Exception:
            return "?"

    def _anchors(node) -> tuple:
        calls, globs, consts, cmpc = [], [], [], []

        def walk(n, in_cmp=False):
            if n is None:
                return
            if isinstance(n, ca.FuncCall) and isinstance(n.name, ca.ID):
                calls.append(n.name.name)
            elif isinstance(n, ca.ID) and n.name in globals_set:
                globs.append(n.name)
            elif isinstance(n, ca.Constant) and n.type in ("int", "long"):
                try:
                    v = int(n.value, 0)
                    consts.append(v)
                    if in_cmp:
                        cmpc.append(v)
                except ValueError:
                    pass
            cmp_now = in_cmp or (
                isinstance(n, ca.BinaryOp)
                and n.op in ("==", "!=", "<", ">", "<=", ">=", "&"))
            for _, c in (n.children() if hasattr(n, "children") else []):
                walk(c, cmp_now)

        walk(node)
        return _dedup(calls), _dedup(globs), _dedup(consts), _dedup(cmpc)

    def _short(node) -> str:
        try:
            from pycparser import c_generator
            s = c_generator.CGenerator().visit(node)
            s = " ".join(s.split())
            return s[:60] + ("…" if len(s) > 60 else "")
        except Exception:
            return ""

    def emit(node, nesting):
        if node is None:
            return
        if isinstance(node, ca.Compound):
            for it in (node.block_items or []):
                emit(it, nesting)
        elif isinstance(node, ca.Decl):
            if node.name:
                types[node.name] = _type_str(node)
        elif isinstance(node, ca.If):
            # Fold `if (cond) <single simple stmt>;` into ONE MacStmt that
            # carries BOTH the condition and the body anchors.  Watcom emits
            # one -d1 line mark for such a guarded statement, so the PS spine
            # has a single statement there; emitting the body call as a
            # separate Mac stmt causes a one-off alignment shift (guard
            # matched to the body call).  Common idiom:
            # `if (pointer_mode == 1) show_move_highlight();`
            ca_, g, cs, cc = _anchors(node.cond)
            simple = _single_simple(node.iftrue)
            if simple is not None:
                ca2, g2, cs2, cc2 = _anchors(simple)
                out.append(MacStmt(
                    "if", list(nesting), _dedup(ca_ + ca2), _dedup(g + g2),
                    _dedup(cs + cs2), _dedup(cc + cc2), dict(types),
                    _coord(node), _short(node.cond),
                    ops=_dedup(_mac_ops(node.cond) + _mac_ops(simple))))
            else:
                out.append(MacStmt("if", list(nesting), ca_, g, cs, cc,
                                   dict(types), _coord(node),
                                   _short(node.cond), ops=_mac_ops(node.cond)))
                emit(node.iftrue, nesting + ["if"])
            if node.iffalse is not None:
                if isinstance(node.iffalse, ca.If):
                    emit(node.iffalse, nesting)   # else-if chain, same level
                else:
                    emit(node.iffalse, nesting + ["else"])
        elif isinstance(node, (ca.For, ca.While, ca.DoWhile)):
            kind = {"For": "for", "While": "while",
                    "DoWhile": "do"}[type(node).__name__]
            cond = getattr(node, "cond", None)
            ca_, g, cs, cc = _anchors(cond)
            out.append(MacStmt(kind, list(nesting), ca_, g, cs, cc,
                               dict(types), _coord(node), _short(cond),
                               ops=_mac_ops(cond)))
            emit(node.stmt, nesting + [kind])
        elif isinstance(node, ca.Switch):
            ca_, g, cs, cc = _anchors(node.cond)
            out.append(MacStmt("switch", list(nesting), ca_, g, cs, cc,
                               dict(types), _coord(node), _short(node.cond),
                               ops=_mac_ops(node.cond)))
            emit(node.stmt, nesting + ["switch"])
        elif isinstance(node, ca.Return):
            ca_, g, cs, cc = _anchors(node)
            out.append(MacStmt("return", list(nesting), ca_, g, cs, cc,
                               dict(types), _coord(node), _short(node),
                               ops=_mac_ops(node)))
        else:
            ca_, g, cs, cc = _anchors(node)
            construct = "call" if isinstance(node, ca.FuncCall) or (
                isinstance(node, ca.Assignment)
                and isinstance(node.rvalue, ca.FuncCall)) else (
                "assign" if isinstance(node, ca.Assignment) else "other")
            out.append(MacStmt(construct, list(nesting), ca_, g, cs, cc,
                               dict(types), _coord(node), _short(node),
                               ops=_mac_ops(node)))

    body = getattr(fdef, "body", None)
    if body is not None:
        emit(body, [])
    return out


def _coord(node) -> int:
    c = getattr(node, "coord", None)
    return getattr(c, "line", 0) if c is not None else 0


def _single_simple(body):
    """If ``body`` is a single simple statement (call / assignment / return),
    return it, else None.  Used to fold `if (c) f();` into one statement."""
    import pycparser.c_ast as ca
    node = body
    if isinstance(node, ca.Compound):
        items = node.block_items or []
        if len(items) != 1:
            return None
        node = items[0]
    if isinstance(node, (ca.FuncCall, ca.Assignment, ca.Return)):
        return node
    return None


# ════════════════════════════════════════════════════════════════════════
#  Alignment engine  (Phase 3, spec §3)
# ════════════════════════════════════════════════════════════════════════


def _jaccard(a: list, b: list) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _construct_compat(c_ops: dict, mac_construct: str) -> float:
    has_branch = any(k.startswith(("COMPARE:", "COND_BRANCH")) for k in c_ops)
    has_call = any(k.startswith("CALL") for k in c_ops)
    has_assign = any(k.startswith(("ASSIGN", "PRE_GETS", "BINARY:", "UNARY:"))
                     for k in c_ops)
    if mac_construct in ("if", "else-if", "for", "while", "do", "switch"):
        return 1.0 if has_branch else 0.2
    if mac_construct in ("call",):
        return 1.0 if has_call else 0.3
    if mac_construct in ("assign", "return", "other"):
        return 1.0 if has_assign else 0.4
    return 0.5


def _sim(stmt: Statement, mac) -> float:
    return (3.0 * _jaccard(stmt.a_calls, mac.calls)
            + 2.0 * _jaccard(stmt.a_globals, mac.globals)
            + 2.0 * _jaccard(stmt.a_cmp_consts, mac.cmp_consts)
            + 1.0 * _jaccard(_spine_consts(stmt), mac.consts)
            # computation-shape match: lets anchorless arithmetic statements
            # align by the shape of their op tree (binir vs Mac AST).
            + 1.0 * _jaccard(_canon_ps_ops(stmt.c_ops),
                             getattr(mac, "ops", []))
            + 0.5 * _construct_compat(stmt.c_ops, mac.construct))


def _spine_consts(stmt: Statement) -> list:
    return _dedup(list(stmt.a_consts) + list(stmt.a_cmp_consts))


def _align(spine: list, macs: list) -> dict:
    """Monotonic (Needleman-Wunsch) global alignment of spine statements to
    Mac statements.  Returns {spine_idx: (mac_idx, margin)} for matched
    pairs only.  ``margin`` = best sim minus second-best in that row,
    normalised -- the per-statement alignment confidence proxy."""
    n, m = len(spine), len(macs)
    if n == 0 or m == 0:
        return {}
    GAP = -0.5
    NEG = float("-inf")
    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]   # 0=diag 1=up(spine gap) 2=left(mac gap)
    for i in range(1, n + 1):
        dp[i][0] = dp[i - 1][0] + GAP
        bt[i][0] = 1
    for j in range(1, m + 1):
        dp[0][j] = dp[0][j - 1] + GAP
        bt[0][j] = 2
    sims = [[0.0] * m for _ in range(n)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = _sim(spine[i - 1], macs[j - 1])
            sims[i - 1][j - 1] = s
            diag = dp[i - 1][j - 1] + s
            up = dp[i - 1][j] + GAP
            left = dp[i][j - 1] + GAP
            best = max(diag, up, left)
            dp[i][j] = best
            bt[i][j] = 0 if best == diag else (1 if best == up else 2)
    # Traceback
    matches: dict = {}
    i, j = n, m
    while i > 0 and j > 0:
        if bt[i][j] == 0:
            si, mj = i - 1, j - 1
            s = sims[si][mj]
            if s > 0.2:           # only keep substantive matches
                row = sims[si]
                second = max([row[k] for k in range(m) if k != mj], default=0.0)
                margin = s - second
                # Confidence is ABSOLUTE-similarity-driven, not margin-driven:
                # NW already enforces monotonic (diagonal) order, so a matched
                # pair is structurally trustworthy even when the margin is low
                # (repetitive code -- e.g. a run of identical array swaps --
                # has many equally-good candidates, i.e. low margin, but the
                # SHAPE transferred is the same regardless of which one).  A
                # solid single anchor (shared call/global/cmp-const) reaches
                # s ~= 2.5; margin is a secondary bonus.
                conf = 0.7 * min(1.0, s / 2.0) + 0.3 * min(1.0, margin / 1.5)
                matches[si] = (mj, max(0.0, min(1.0, conf)))
            i, j = i - 1, j - 1
        elif bt[i][j] == 1:
            i -= 1
        else:
            j -= 1
    return matches


# ════════════════════════════════════════════════════════════════════════
#  Fusion + classification
# ════════════════════════════════════════════════════════════════════════


def _flat_guard_run(entries: list) -> bool:
    """Heuristic: the spine is a flat-guard chain if most jcc arcs jump
    FORWARD to a small set of late targets (early-return guards) rather
    than interleaving."""
    fwd = back = 0
    for e in entries:
        for _, arc in e.arcs:
            if arc == "fwd":
                fwd += 1
            elif arc == "back":
                back += 1
    return fwd >= 2 and back <= 1


def _layout_aligned(ps_bytes: bytes, rc_bytes: bytes) -> bool:
    """True iff PS and RC disassemble to the SAME instruction-boundary
    offsets over PS's length (byte-exact modulo fixups => offsets coincide)."""
    if not ps_bytes or not rc_bytes:
        return False
    po = [t[0] for t in _disasm(ps_bytes)]
    ro = [t[0] for t in _disasm(rc_bytes) if t[0] < len(ps_bytes)]
    return po == ro


def _rc_anchored(rc) -> bool:
    return bool(rc.calls or rc.cmp_consts)


def _rc_correspondence(stmts: list, rc_stmts: list,
                       ps_bytes: bytes = b"", rc_bytes: bytes = b"") -> None:
    """Align the RC statement spine to the PS spine (``stmts``) and populate
    rc_cues/rc_rel per PS statement, surfacing statement-BOUNDARY divergence
    (SPLIT = RC over-split a PS statement; MERGE = RC combined two).

    Two paths:

    * **byte-exact** (``ps_bytes == rc_bytes``): PS and RC offsets coincide,
      so each RC ``-d1`` mark maps PRECISELY onto the PS statement whose byte
      span contains it.  Counting RC marks per PS statement gives the exact
      per-statement line-mark comparison (the same divergence ``line-compare``
      reports globally, but localised): 0 marks => MERGE, 1 => 1:1, >=2 =>
      SPLIT.  This catches the boundary class -- e.g. `scroll`'s residual
      PS-only mark -- that the Mac witness (nesting/ir-shape) cannot see.
    * **diffing** (bytes differ): offsets have diverged, so fall back to the
      anchor-based monotonic alignment and emit SPLIT conservatively (an
      anchored PS statement owning >= 2 anchored RC statements).
    """
    if not rc_stmts:
        return

    # Use the precise offset mapping iff PS and RC have the SAME instruction
    # LAYOUT (identical boundary offsets).  Raw byte-equality is the wrong
    # test -- a byte-exact function still differs at fixup (address-operand)
    # positions because PS and RC reference different absolute addresses; but
    # its instruction boundaries are identical, so offsets coincide and each
    # RC -d1 mark lands in the right PS statement.
    if _layout_aligned(ps_bytes, rc_bytes):
        _rc_correspondence_exact(stmts, rc_stmts)
        return

    matches = _align(stmts, rc_stmts)   # {ps_idx: (rc_idx, conf)}
    ps_for_rc = {rc_idx: ps_idx for ps_idx, (rc_idx, _c) in matches.items()}
    # Attribute each RC statement to the most recent PS owner (matched PS
    # whose RC index is <= this one).
    owner_by_rc: dict = {}
    cur_owner = None
    for rc_idx in range(len(rc_stmts)):
        if rc_idx in ps_for_rc:
            cur_owner = ps_for_rc[rc_idx]
        owner_by_rc[rc_idx] = cur_owner
    rc_by_ps: dict = {}
    for rc_idx, ps_idx in owner_by_rc.items():
        if ps_idx is None:
            continue
        rc_by_ps.setdefault(ps_idx, []).append(rc_idx)
    for ps_idx, st in enumerate(stmts):
        owned = rc_by_ps.get(ps_idx, [])
        st.rc_cues = [f"L{rc_stmts[i].line}" for i in owned]
        has_anchors = bool(st.a_calls or st.a_globals or st.a_cmp_consts)
        anchored_owned = [i for i in owned if _rc_anchored(rc_stmts[i])]
        matched = ps_idx in matches
        if has_anchors and len(anchored_owned) >= 2:
            st.rc_rel = "SPLIT"
        elif matched and len(owned) == 1:
            st.rc_rel = "1:1"
        else:
            st.rc_rel = ""        # unknown / not trustworthy -- stay silent


def _rc_correspondence_exact(stmts: list, rc_stmts: list) -> None:
    """Precise per-statement line-mark comparison for a byte-exact function
    (PS and RC offsets coincide).  See :func:`_rc_correspondence`."""
    bounds = [(st.byte_span[0], st.byte_span[1], i)
              for i, st in enumerate(stmts)]
    rc_by_ps: dict = {}
    for rc in rc_stmts:
        for a, b, i in bounds:
            if a <= rc.rel_off < b:
                rc_by_ps.setdefault(i, []).append(rc)
                break
    for i, st in enumerate(stmts):
        owned = rc_by_ps.get(i, [])
        st.rc_cues = [f"L{rc.line}" for rc in owned]
        n = len(owned)
        if n >= 2:
            st.rc_rel = "SPLIT"        # RC started extra statement(s) here
        elif n == 0:
            st.rc_rel = "MERGE"        # PS starts a statement; RC continues
        else:
            st.rc_rel = "1:1"


def build_skeleton(name: str, *, use_mac: bool = True,
                   symbols_json: Path = _SYMS,
                   use_rc: bool = False,
                   rc_map: Optional[dict] = None) -> Optional[ShapeSkeleton]:
    spine = ps_statement_spine(name, symbols_json)
    if spine is None:
        return None
    entries = spine["entries"]

    first_line = spine["first"]
    stmts: list[Statement] = []
    for idx, e in enumerate(entries):
        c_ops, c_summary = witness_c(e)
        st = Statement(
            idx=idx, ps_line=e.ps_line, ps_line_rel=f"L+{e.ps_line - first_line}",
            byte_span=(e.rel_off, e.rel_off + e.n_bytes),
            multi_stmt=e.multi_stmt, backward=e.backward,
            a_summary=e.summary, a_calls=e.calls, a_globals=e.globals,
            a_cmp_consts=e.cmp_consts, a_consts=e.consts, a_arcs=e.arcs,
            c_ops=c_ops, c_summary=c_summary)
        stmts.append(st)

    sk = ShapeSkeleton(func=name, file=spine["file"], statements=stmts)

    # Witness B + alignment
    macs: list = []
    if use_mac:
        fdef = _mac_funcdef(name)
        if fdef is not None:
            try:
                from c2.mac.clean import known_globals
                macs = _lower_mac(fdef, known_globals())
            except Exception:
                macs = []
    sk.mac_total = len(macs)
    if macs:
        matches = _align(stmts, macs)
        for si, (mj, conf) in matches.items():
            mac = macs[mj]
            st = stmts[si]
            st.b_construct = mac.construct
            st.b_nesting = mac.nesting
            st.b_types = mac.types
            st.b_expr = mac.expr
            st.b_align_conf = conf
        sk.mac_aligned = len(matches)

    # RC correspondence: align the current recovered source's statement
    # spine to the PS spine and surface SPLIT/MERGE boundary divergence.
    if use_rc:
        try:
            rc_res = _rc_spine(name)
        except Exception:
            rc_res = None
        if rc_res:
            rc_stmts, rc_bytes = rc_res
            _rc_correspondence(stmts, rc_stmts,
                               spine.get("code", b""), rc_bytes)

    flat = _flat_guard_run(entries)
    _classify(sk, flat, mac_available=bool(macs))
    return sk


def _classify(sk: ShapeSkeleton, flat_guard: bool, *,
              mac_available: bool = True) -> None:
    TAU = 0.3
    total_w = 0.0
    informative_w = 0.0
    corroborated_w = 0.0
    for st in sk.statements:
        dis: list[Disagreement] = []
        b_ok = st.b_construct is not None and st.b_align_conf >= TAU
        c_ok = bool(st.c_ops)

        # nesting disagreement: flat-guard spine but Mac says nested-if body
        if b_ok and st.b_nesting and flat_guard and "if" in st.b_nesting \
                and any(a == "fwd" for _, a in st.a_arcs):
            dis.append(Disagreement(
                "nesting",
                f"Mac nests under {'/'.join(st.b_nesting)} but PS arc is a "
                f"forward guard (flat-guard chain)", "B"))
        # ir-shape: spine has a branch but Mac is a plain assign (or vice versa)
        if b_ok and c_ok:
            has_branch = any(k.startswith(("COMPARE:", "COND_BRANCH"))
                             for k in st.c_ops)
            if has_branch and st.b_construct in ("assign", "call", "return"):
                dis.append(Disagreement(
                    "ir-shape",
                    f"binir shows a compare/branch but Mac construct is "
                    f"'{st.b_construct}'", "B"))
        # boundary: RC splits/merges this statement
        if st.rc_rel in ("SPLIT", "MERGE"):
            dis.append(Disagreement(
                "boundary", f"RC {st.rc_rel} (statement decomposition differs)",
                "RC"))
        # missing: an ANCHORED statement (calls/globals/consts) that B
        # failed to align AND binir couldn't shape -- a real unaligned
        # statement.  Pure control-flow glue (prologue pushes, tail jmps
        # with no anchors) is NOT a frontier: there is nothing to recover,
        # so it stays low-confidence but unflagged.  When Mac was entirely
        # unavailable, suppress (B was never consulted; the function header
        # reports the absence instead).
        # "Real" anchors for the frontier gate: calls / globals / comparison
        # constants.  General immediates (a_consts) are too noisy (loop
        # bounds, scratch loads) to mark a statement as recoverable.
        has_anchors = bool(st.a_calls or st.a_globals or st.a_cmp_consts)
        if mac_available and not b_ok and not c_ok and has_anchors:
            dis.append(Disagreement(
                "missing", "PS anchors present but no Mac alignment and "
                "trivial IR", "BC"))
        if st.backward:
            dis.append(Disagreement(
                "order", "PS line went backward (Watcom statement reorder / "
                "loop / shared tail)", "A"))

        st.disagreements = dis
        st.witnesses = 1 + (1 if b_ok else 0) + (1 if c_ok else 0)

        # confidence
        if st.witnesses == 3 and not dis:
            st.confidence = "high"
        elif st.witnesses >= 2 and all(d.axis in ("boundary", "order")
                                       for d in dis):
            st.confidence = "medium"
        elif st.witnesses >= 2 and len(dis) <= 1:
            st.confidence = "medium"
        else:
            st.confidence = "low"

        # Coverage vs concordance (byte-weighted).  An INFORMATIVE statement
        # has >=2 witnesses (the PS spine plus Mac and/or binir corroborating
        # it).  Among informative statements, CONFLICTED ones carry a real
        # shape disagreement (nesting/ir-shape/boundary); the rest are
        # CORROBORATED.  Single-witness statements are uninformative (benign
        # witness sparsity) and excluded from concordance so it measures
        # CORRECTNESS, not coverage.
        w = max(1, st.byte_span[1] - st.byte_span[0])
        total_w += w
        informative = st.witnesses >= 2
        conflicted = any(d.axis in ("nesting", "ir-shape", "boundary")
                         for d in dis)
        if informative:
            informative_w += w
            if not conflicted:
                corroborated_w += w

    sk.n_high = sum(1 for s in sk.statements if s.confidence == "high")
    sk.n_medium = sum(1 for s in sk.statements if s.confidence == "medium")
    sk.n_low = sum(1 for s in sk.statements if s.confidence == "low")
    sk.coverage = (informative_w / total_w) if total_w else 0.0
    sk.concordance = (corroborated_w / informative_w) if informative_w else 1.0
    sk.agreement_score = sk.concordance


# ════════════════════════════════════════════════════════════════════════
#  Rendering
# ════════════════════════════════════════════════════════════════════════

_CONF_COLOR = {"high": "green", "medium": "yellow", "low": "red"}


def _deinvent_note(name: str, symbols_json: Path = _SYMS) -> Optional[str]:
    """Named shape-fix for a caching mismatch (de-invent / add-intermediate),
    via the SAME detector decomp-verify uses (c2.commands.deinvent_hints).
    shape-recon's LOW-concordance verdict says "the shape is wrong"; this
    says *how* -- which invented local to delete (or which global to cache).
    Best-effort: needs the PS disasm (always) + the incremental RC build (for
    the byte-exact gate) + the function's AST."""
    try:
        from capstone import CS_ARCH_X86, CS_MODE_32, Cs
        from c2.commands import deinvent_hints
        from c2.commands.decomp_verify import _build_src_func_cache, _parse_map

        fa = _build_src_func_cache().get(name)
        if not fa:
            return None
        md = Cs(CS_ARCH_X86, CS_MODE_32)

        # PS insns over the function's symbol range.
        S = _get_syms(symbols_json)
        if name not in S.by_name:
            return None
        i = S.by_name[name]
        start = S.code_syms[i]["offset"]
        end = (S.code_syms[i + 1]["offset"] if i + 1 < len(S.code_syms)
               else start + 0x4000)
        ps = [(ins.address, ins.size, ins.bytes,
               f"{ins.mnemonic} {ins.op_str}".strip())
              for ins in md.disasm(S.le_code[start:end], start)]

        # RC insns from the incremental build (the byte-exact gate needs them).
        rc: list = []
        built = _ensure_rc_build()
        if built is not None:
            _, out_map, code_bin, _ = built
            try:
                syms = _parse_map(Path(out_map))
                mangled = name + "_"
                if mangled in syms:
                    offs = sorted(syms.values())
                    rs = syms[mangled]
                    j = offs.index(rs)
                    re_ = offs[j + 1] if j + 1 < len(offs) else rs + 0x4000
                    rc = [(k.address, k.size, b"",
                           f"{k.mnemonic} {k.op_str}".strip())
                          for k in md.disasm(code_bin[rs:re_], 0)]
            except Exception:
                rc = []
        h = deinvent_hints.detect(fa[1], ps, rc)
        return deinvent_hints.render(h) if h is not None else None
    except Exception:
        return None


def _render_human(sk: ShapeSkeleton) -> None:
    from rich.console import Console
    from rich.markup import escape
    con = Console(highlight=False, soft_wrap=True)
    con.print(
        f"# [bold cyan]{sk.func}[/]  {sk.file}  "
        f"{len(sk.statements)} statements  "
        f"concordance [bold]{sk.concordance:.2f}[/] "
        f"(witnesses agree)  coverage {sk.coverage:.0%}  "
        f"(B aligned {sk.mac_aligned}/{sk.mac_total})", highlight=False)
    _dnote = _deinvent_note(sk.func)
    if _dnote:
        con.print(f"#  [magenta]\u2192 shape-fix: {escape(_dnote)}[/]",
                  highlight=False)
    con.print("#  conf  L#       bytes  A: PS line-summary   │  "
              "B: Mac construct/expr   │  C: binir   │  RC line(s)  │  flags")
    for st in sk.statements:
        col = _CONF_COLOR[st.confidence]
        a = "  ".join(st.a_summary[:4]) or "-"
        if len(st.a_summary) > 4:
            a += " …"
        b = (f"{st.b_construct}: {st.b_expr}" if st.b_construct
             else "(no Mac match)")
        rc = (f"→{','.join(st.rc_cues)}" if st.rc_cues else "")
        if st.rc_rel == "SPLIT":
            rc += " SPLIT"
        flags = []
        if st.multi_stmt:
            flags.append("multi")
        if st.backward:
            flags.append("⟲back")
        for d in st.disagreements:
            if d.axis not in ("order",):
                flags.append(f"⚠{d.axis}")
        flagstr = " ".join(_dedup(flags))
        con.print(
            f"  [{col}]{st.confidence.upper():<5}[/] "
            f"{st.ps_line_rel:<7} "
            f"+{st.byte_span[0]:<#5x}{st.byte_span[1]-st.byte_span[0]:>3}b  "
            f"{escape(a[:34]):<34} │ {escape(b[:30]):<30} │ "
            f"{escape(st.c_summary[:18]):<18} │ {escape(rc[:16]):<16} │ "
            f"{flagstr}",
            highlight=False)
    # disagreement digest
    from collections import Counter
    dc: Counter = Counter()
    for st in sk.statements:
        for d in st.disagreements:
            dc[d.axis] += 1
    if dc:
        con.print("# disagreements: " + ", ".join(
            f"{n} {ax}" for ax, n in dc.most_common()))
    b_note = (f"B {sk.mac_aligned}/{len(sk.statements)} aligned"
              if sk.mac_total else "B UNAVAILABLE (function absent from Mac "
              "build or Ghidra not extracted)")
    con.print(f"# witness coverage: A {len(sk.statements)}/{len(sk.statements)}, "
              f"{b_note}, "
              f"C {sum(1 for s in sk.statements if s.c_ops)}/"
              f"{len(sk.statements)} non-trivial")
    con.print(f"# confidence: {sk.n_high} high, {sk.n_medium} medium, "
              f"{sk.n_low} low  --  ⚠-flagged statements are the search "
              f"frontier")


def _skeleton_to_dict(sk: ShapeSkeleton) -> dict:
    d = asdict(sk)
    return d


# ════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════


def shape_recon(
    name: Annotated[Optional[str], typer.Argument(
        help="function name (omit with --corpus)")] = None,
    use_mac: Annotated[bool, typer.Option(
        "--mac/--no-mac",
        help="Include witness B (Mac decompile).  --no-mac is much faster "
             "(A+C only).  Default: on.")] = True,
    use_rc: Annotated[bool, typer.Option(
        "--rc/--no-rc",
        help="Include RC correspondence: align the CURRENT recovered source's "
             "statement spine to PS and surface SPLIT boundary divergence "
             "(needs an incremental recompile, ~2s).  Default: on for a single "
             "function, off for --corpus.")] = True,
    json_out: Annotated[bool, typer.Option(
        "--json", help="Emit the ShapeSkeleton as JSON.")] = False,
    corpus: Annotated[bool, typer.Option(
        "--corpus", help="Run over all diffing functions; print the "
        "agreement distribution + ranked targets (the go/no-go metric).")]
        = False,
    exact: Annotated[bool, typer.Option(
        "--exact", help="Corpus: run over BYTE-EXACT functions instead of "
        "diffing ones -- a calibration/self-check.  Their recovered source "
        "is correct, so agreement should be HIGH and the frontier (false "
        "disagreements) near-empty.")] = False,
    limit: Annotated[int, typer.Option(
        "--limit", "-n", help="Corpus: max functions to process "
        "(0 = all).")] = 40,
    from_json: Annotated[Optional[Path], typer.Option(
        "--from-json", help="Corpus: cached decomp-verify --json blob.")]
        = None,
    symbols_json: Annotated[Path, typer.Option("--symbols")] = _SYMS,
) -> None:
    """Witness-reconciliation shape inference for a function."""
    if corpus:
        _run_corpus(use_mac=use_mac, limit=limit, from_json=from_json,
                    json_out=json_out, symbols_json=symbols_json, exact=exact,
                    use_rc=use_rc)
        return
    if not name:
        typer.secho("[!] provide a function name or --corpus", fg="red")
        raise typer.Exit(1)
    sk = build_skeleton(name, use_mac=use_mac, use_rc=use_rc,
                        symbols_json=symbols_json)
    if sk is None:
        typer.secho(f"[!] {name!r}: no PS -d1 line records (asm module?)",
                    fg="red")
        raise typer.Exit(1)
    if json_out:
        typer.echo(json.dumps(_skeleton_to_dict(sk), default=str))
    else:
        _render_human(sk)


def _run_corpus(*, use_mac: bool, limit: int, from_json: Optional[Path],
                json_out: bool, symbols_json: Path, exact: bool = False,
                use_rc: bool = False) -> None:
    from c2.commands.verify_json import get_verify_json
    try:
        doc = get_verify_json(no_build=True, from_path=from_json)
    except FileNotFoundError:
        typer.secho("[!] no cached decomp-verify --json; run "
                    "`c2 decomp-verify --json` once or pass --from-json",
                    fg="red")
        raise typer.Exit(1)
    if exact:
        # Calibration: byte-exact functions have correct recovered source,
        # so a well-behaved tool should score them HIGH with a near-empty
        # frontier.  A high frontier here = false-positive disagreements.
        targets = [f["name"] for f in doc.get("functions", [])
                   if f.get("diff_byte_count", 0) == 0
                   and not f.get("size_differs", False)]
    else:
        targets = [f["name"] for f in doc.get("functions", [])
                   if f.get("diff_byte_count", 0) > 0]
    if limit:
        targets = targets[:limit]

    # On --exact, cross-validate shape CONFLICTS against the independent
    # line-compare offender signal (PS-vs-RC -d1 line stream).  A byte-exact
    # function can still be MIS-TRANSCRIBED (Watcom emits identical bytes
    # from a different source shape -- Hard Rule #8); shape-recon conflicts
    # that coincide with line-compare offenders are high-confidence real
    # shape bugs, not false positives.
    _lc = None
    if exact:
        try:
            from c2.commands.line_compare import compare_function as _lc
        except Exception:
            _lc = None

    rows = []
    for nm in targets:
        try:
            sk = build_skeleton(nm, use_mac=use_mac, use_rc=use_rc,
                                symbols_json=symbols_json)
        except Exception:
            sk = None
        if sk is None:
            continue
        # coverage gap (could not corroborate) vs shape CONFLICT (the
        # witnesses actively disagree).  Only conflicts indicate a wrong
        # recovered shape; missing is benign witness sparsity.  boundary
        # (RC SPLIT) is a direct over-split signal -> counts as a conflict.
        coverage = sum(1 for s in sk.statements for d in s.disagreements
                       if d.axis == "missing")
        # mac_conflict (nesting/ir-shape) comes from the INDEPENDENT Mac
        # witness; bnd_conflict (boundary) is derived from the RC -d1 line
        # stream -- the SAME source `line-compare` uses, so it overlaps the
        # oracle by construction and is reported separately.
        mac_conflict = sum(1 for s in sk.statements for d in s.disagreements
                           if d.axis in ("nesting", "ir-shape"))
        bnd_conflict = sum(1 for s in sk.statements for d in s.disagreements
                           if d.axis == "boundary")
        conflict = mac_conflict + bnd_conflict
        frontier = sum(1 for s in sk.statements
                       if any(d.axis not in ("order",) for d in s.disagreements))
        lc_offender = None
        if _lc is not None:
            try:
                lc_offender = not _lc(nm, sk.file).is_clean
            except Exception:
                lc_offender = None
        rows.append({
            "name": nm, "file": sk.file, "n_stmt": len(sk.statements),
            "concordance": round(sk.concordance, 3),
            "coverage": round(sk.coverage, 3),
            "mac_aligned": sk.mac_aligned, "mac_total": sk.mac_total,
            "frontier": frontier, "cov_gaps": coverage, "conflict": conflict,
            "mac_conflict": mac_conflict, "bnd_conflict": bnd_conflict,
            "lc_offender": lc_offender,
            "n_high": sk.n_high, "n_low": sk.n_low})

    if json_out:
        typer.echo(json.dumps(rows))
        return

    if not rows:
        typer.secho("[!] no functions produced a skeleton", fg="red")
        return
    import statistics
    scores = [r["concordance"] for r in rows]
    covs = [r["coverage"] for r in rows]
    mac_rows = [r for r in rows if r["mac_total"]]
    cov = [r["mac_aligned"] / r["mac_total"] for r in mac_rows]
    kind = "BYTE-EXACT (calibration)" if exact else "diffing"
    typer.secho(f"\n# shape-recon corpus: {len(rows)} {kind} functions  "
                f"(mac={'on' if use_mac else 'off'})", fg="cyan", bold=True)
    # False-frontier rate: mean fraction of statements flagged with a
    # non-order disagreement.  On --exact this is the false-positive rate.
    fr_rate = statistics.mean(
        [r["frontier"] / max(1, r["n_stmt"]) for r in rows])
    label = ("frontier rate (coverage gaps + conflicts)" if exact
             else "frontier rate (statements needing work)")
    typer.echo(f"#   {label}: {fr_rate:.0%}")
    if exact:
        lc_known = [r for r in rows if r["lc_offender"] is not None]
        lc_off = [r for r in lc_known if r["lc_offender"]]
        tot_stmt = sum(r["n_stmt"] for r in rows)
        n_cov_stmt = sum(r["cov_gaps"] for r in rows)
        typer.echo(f"#   coverage-gap rate {n_cov_stmt / max(1, tot_stmt):.0%}")
        # Two conflict sources, reported separately because they differ in
        # independence from the line-compare oracle:
        #   (a) Mac conflicts (nesting/ir-shape) -- from the INDEPENDENT Mac
        #       witness; cross-checking these against line-compare is a real
        #       validation.
        #   (b) boundary conflicts -- derived from the RC -d1 line stream,
        #       the SAME source line-compare uses, so they overlap the oracle
        #       BY CONSTRUCTION (not independent corroboration).
        mac_fns = [r for r in rows if r["mac_conflict"] > 0]
        bnd_fns = [r for r in rows if r["bnd_conflict"] > 0]
        if lc_known:
            typer.echo(
                f"#   cross-check vs line-compare ({len(lc_known)} with RC "
                f"line sidecar): {len(lc_off)} offenders")
            # (a) INDEPENDENT Mac signal -- the meaningful precision claim
            mac_both = sum(1 for r in mac_fns if r["lc_offender"])
            mac_clean = sum(1 for r in mac_fns if r["lc_offender"] is False)
            mac_recall = sum(1 for r in lc_off if r["mac_conflict"] > 0)
            typer.echo(
                f"#   (a) INDEPENDENT Mac conflicts (nesting/ir-shape): "
                f"{len(mac_fns)} fns -> {mac_both} are offenders "
                f"(precision {mac_both}/{max(1, len(mac_fns))}), "
                f"{mac_clean} clean; recall {mac_recall}/{len(lc_off)}")
            # (b) RC boundary signal -- native detection, overlaps by design
            bnd_recall = sum(1 for r in lc_off if r["bnd_conflict"] > 0)
            typer.echo(
                f"#   (b) RC boundary conflicts (line-mark divergence, "
                f"shares line-compare's source): {len(bnd_fns)} fns; "
                f"recall {bnd_recall}/{len(lc_off)} (native+localised, and "
                f"works on DIFFING fns where line-compare cannot run)")
            combined = sum(1 for r in lc_off
                           if r["mac_conflict"] > 0 or r["bnd_conflict"] > 0)
            typer.echo(
                f"#   combined recall {combined}/{len(lc_off)}")
    typer.echo(f"#   CONCORDANCE (witnesses agree where >=2 present; the "
               f"correctness signal)  mean {statistics.mean(scores):.2f}  "
               f"median {statistics.median(scores):.2f}")
    typer.echo(f"#   coverage (>=2-witness statements; how much we can judge) "
               f" mean {statistics.mean(covs):.0%}")
    if use_mac:
        n_avail = len(mac_rows)
        typer.echo(f"#   Mac available: {n_avail}/{len(rows)} functions")
        if mac_rows:
            ms = [r["concordance"] for r in mac_rows]
            typer.echo(f"#   concordance (Mac-available only)  mean "
                       f"{statistics.mean(ms):.2f}  median "
                       f"{statistics.median(ms):.2f}")
    if cov:
        typer.echo(f"#   Mac alignment coverage  mean "
                   f"{statistics.mean(cov):.0%}")
    # histogram
    buckets = [0] * 5
    for s in scores:
        buckets[min(4, int(s * 5))] += 1
    labels = ["0.0-0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0"]
    typer.echo("#   concordance histogram:")
    for lab, n in zip(labels, buckets):
        bar = "█" * int(40 * n / max(1, max(buckets)))
        typer.echo(f"#     {lab}  {n:>4}  {bar}")

    if exact:
        # The interesting calibration cases are byte-exact functions with
        # shape CONFLICTS.  Annotated with the line-compare verdict: 'LC!'
        # = also a line-compare offender (likely REAL mis-transcription,
        # i.e. a true positive on byte-equal-but-wrong source); 'lc-ok' =
        # line-compare clean (likely a shape-recon false positive).
        bad = sorted([r for r in rows if r["conflict"] > 0],
                     key=lambda r: (r["conflict"], -r["n_stmt"]),
                     reverse=True)[:25]
        typer.echo("\n# BYTE-EXACT FUNCTIONS WITH SHAPE CONFLICTS "
                   "(nesting/ir-shape).  LC! = also a line-compare offender "
                   "=> likely a REAL mis-transcription (byte-equal from a "
                   "different source shape, Hard Rule #8); lc-ok => likely a "
                   "shape-recon false positive to debug:")
        typer.echo(f"#   {'cfl':>3} {'cov':>3} {'stmts':>5}  {'line-cmp':>8}  "
                   f"function")
        for r in bad:
            lc = ("LC!" if r["lc_offender"] else
                  "lc-ok" if r["lc_offender"] is False else "?")
            typer.echo(f"    {r['conflict']:>3} {r['cov_gaps']:>3} "
                       f"{r['n_stmt']:>5}  {lc:>8}  {r['name']}  ({r['file']})")
        return

    # BEST TARGETS: trustworthy skeleton (high concordance + decent coverage)
    # that still diffs, with a localized frontier.
    best = sorted([r for r in rows if r["frontier"] > 0],
                  key=lambda r: (-(r["concordance"] * r["coverage"]),
                                 r["frontier"]))[:20]
    typer.echo("\n# BEST TARGETS (trustworthy skeleton = high concordance x "
               "coverage, still diffing; residue localized to the frontier):")
    typer.echo(f"#   {'conc':>5} {'cov':>4} {'front':>5} {'stmts':>5}  "
               f"function")
    for r in best:
        typer.echo(f"    {r['concordance']:>5.2f} {r['coverage']:>4.0%} "
                   f"{r['frontier']:>5} {r['n_stmt']:>5}  {r['name']}  "
                   f"({r['file']})")

    worst = sorted([r for r in rows if r["coverage"] >= 0.2],
                   key=lambda r: r["concordance"])[:10]
    typer.echo("\n# LOW CONCORDANCE (witnesses present but DISAGREE -- likely "
               "wrong recovered shape):")
    for r in worst:
        typer.echo(f"    {r['concordance']:>5.2f} (cov {r['coverage']:>3.0%})  "
                   f"{r['name']}  ({r['file']})")
