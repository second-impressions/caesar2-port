"""Regalloc hint — surface the REAL 10.0a allocator's per-value register choices
for a function, from the instrumented `-trace` compiler output.

decomp-verify now builds with the trace image, and ``c2.regalloc`` parses that
patched-compiler output ONCE per file (disk-cached, byte-faithful to the per-TU
build). This detector consumes the parsed result -- no re-parsing, no extra
work duplicated across hints -- and renders, for a diffing function, what
register each value actually got + the savings that ordered them. That is the
ground truth behind register-identity-swap diffs (which ``c2 regtrace --solve``
turns into a source lever).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from c2 import regalloc

REPO = Path(__file__).resolve().parents[2]
_SRC = REPO / "decomp" / "src"
_INC = REPO / "decomp" / "include"


@dataclass
class RegallocHint:
    func: str
    cost_model: dict
    loop_base: int | None
    allocs: list          # [{savings, regclass_name, reg_name, nameclass_name}]
    spilled: int
    namelist: list = field(default_factory=list)  # CREATION order (cn stream): [{conf, name, var, savings, defline, nameclass, reg_name}]
    birthlist: list = field(default_factory=list) # BIRTH    order (nb stream): [{name, conf, var, savings, defline, reg_name}]
    fr: list = field(default_factory=list)         # RISCify rover records (rover_hints)
    lw: list = field(default_factory=list)         # LdStAlloc complete walk (c2.regalloc.lwalk)
    lc: list = field(default_factory=list)         # CompressIns re-fusion commits
    lcx: list = field(default_factory=list)        # LdStCompress rejection reasons
    by_line: dict = field(default_factory=dict)   # source line -> [{conf, name, savings, reg_name, ...}] for prominent display
    drift: list = field(default_factory=list)     # given_regs ground-truth vs union-of-picks warnings (retry rounds)
    chain_vintages: list = field(default_factory=list)  # bo -> br -> bk block-chain trajectory (c2.regalloc.rover.chain_vintages; >= 2026-07-13 image) -- the walk-order/haul provenance the Rover-blocked hint cites


@lru_cache(maxsize=4096)
def _file_trace(func: str, file: str | None) -> dict | None:
    """Fallback for STANDALONE use (no build trace active): locate the
    function's .c file and trace just it (disk- + memo-cached)."""
    try:
        from c2.commands.regtrace import _find_function
        sf, *_ = _find_function(func, file)
        return regalloc.file_trace(sf, _INC)
    except Exception:
        return None


def _routine_by_line_range(routines, func, file):
    """Fallback attribution: find the routine whose `fr`/`al` source lines fall
    inside the function's body range.  Robust when name-order zip attribution
    misses a definition (e.g. a many-arg func with a multi-line signature, which
    drops it from `by_func` and shifts everything after it)."""
    try:
        from c2.commands.regtrace import _find_function
        sf, lo, hi, _ = _find_function(func, file)
    except Exception:
        return None
    best, best_hits = None, 0
    for r in routines:
        lines = [f.get("line") for f in r.get("fr", []) if f.get("line")]
        lines += [a.get("defline") for a in r.get("alloc", []) if a.get("defline")]
        hits = sum(1 for ln in lines if lo <= ln <= hi)
        if hits > best_hits:
            best_hits, best = hits, r
    return best


def _lookup(func: str, file: str | None):
    """(routine, cost_model, loop_base).  Prefers the active build trace --
    captured ONCE from decomp-verify's own wmake build (no extra compiles) and
    persisted per function so it is complete even on incremental builds.  Only
    when no build trace is active (standalone) does it compile the lone file."""
    rt = regalloc.active()
    if rt is not None:
        r = rt.routine_for(func)
        if r is None:
            r = _routine_by_line_range(rt.routines, func, file)
        return r, rt.cost_model, rt.loop_base
    td = _file_trace(func, file)
    if not td:
        return None, {}, None
    by = td.get("by_func", {})
    r = by.get(func) or by.get(func.rstrip("_"))
    if r is None:
        r = _routine_by_line_range(td.get("routines", []), func, file)
    return r, td.get("cost_model", {}), td.get("loop_base")


def detect(func: str, *, file: str | None = None) -> RegallocHint | None:
    """Return a hint if the function has a register-allocation phase."""
    r, cost, base = _lookup(func, file)
    if not r or not r.get("has_regalloc") or not r.get("alloc"):
        return None
    allocs = [{"savings": a["savings"], "regclass_name": a["regclass_name"],
               "reg_name": a["reg_name"], "nameclass_name": a["nameclass_name"]}
              for a in r["alloc"]]
    spilled = sum(1 for a in r["alloc"] if a["reg"] is None)
    # Build a per-source-line breakdown of regalloc choices.  At each line,
    # show every conflict the back end created (with name, savings, register).
    # This is the most prominent view of "what did the compiler do at THIS
    # statement" -- side-by-side with the asm diff, it pinpoints which named
    # local / anonymous temp the diverging registers map to.
    import collections as _coll
    by_line: dict[int, list] = _coll.defaultdict(list)
    for a in r.get("alloc", []):
        ln = a.get("defline") or 0
        by_line[ln].append({
            "conf": a["conf"], "name": a.get("name"),
            "savings": a["savings"], "regclass_name": a["regclass_name"],
            "reg_name": a["reg_name"], "nameclass_name": a.get("nameclass_name"),
            "var": a.get("var"),
            "tree_cands": a.get("tree_cands"),
        })

    # given_regs cross-check (retry-round detector): ground truth vs the
    # union-of-earlier-picks model over the WHOLE-ROUTINE alloc stream.
    # Non-empty => RegAlloc retry rounds (ON_HOLD reseats) active => any
    # tie-group / creation-order lever reasoning for this function is
    # unreliable.  Surfaced as a warning line by render_lines.
    try:
        from c2.commands.regtrace import given_regs_drift
        table = [{"order": i, "var": a.get("var"),
                  "chosen": a.get("reg_name"),
                  "given_regs": a.get("given_regs", 0)}
                 for i, a in enumerate(r["alloc"])]
        drift = given_regs_drift(table)
    except Exception:
        drift = []

    try:
        from c2.regalloc import rover as _rover
        vintages = _rover.chain_vintages(r)
    except Exception:
        vintages = []

    return RegallocHint(func=func, cost_model=cost,
                        loop_base=base, allocs=allocs, spilled=spilled,
                        namelist=regalloc.name_list(r),
                        birthlist=regalloc.name_birth_order(r),
                        fr=r.get("fr", []),
                        lw=r.get("lw", []),
                        lc=r.get("lc", []),
                        lcx=r.get("lcx", []),
                        by_line=dict(by_line),
                        drift=drift,
                        chain_vintages=vintages)


def render_per_line(h: RegallocHint) -> list[str]:
    """A per-source-line view of what the compiler did at each statement.

    For every line that produced AT LEAST ONE conflict, render every conflict
    at that line with its name (if resolved), savings, allocated register and
    name class.  This is the most prominent view of "what is the compiler
    actually doing at this statement?" -- mirrors the source structure so the
    user can map each diverging byte to its IR origin.
    """
    if not h.by_line:
        return []
    # Class-default candidate-list heads (RegSets order).  A conflict whose
    # REAL list (`bt` record, tree->regs) starts elsewhere or is shorter was
    # NARROWED by BuildRegTree/MarkPossible -- render it, it is the al-squat
    # exclusion signal (the pick is first-free of THIS list, saves==0 ties).
    _DEFAULT_HEAD = {"byte": "AL", "word": "AX", "dword": "EAX"}

    def _cand_tag(c) -> str:
        tc = c.get("tree_cands")
        if not tc:
            return ""
        head = _DEFAULT_HEAD.get(c.get("regclass_name") or "")
        if head is not None and tc[0] == head and len(tc) >= 7:
            return ""          # full default list -- not informative
        return "[cand:" + ",".join(tc) + "]"

    out = ["regalloc by source line:"]
    # L0 (synthetic / pre-statement) confs are noise for source-side levers;
    # show them last in a compact summary.
    real_lines = sorted(L for L in h.by_line if L > 0)
    synthetic = h.by_line.get(0, [])
    for L in real_lines:
        confs = h.by_line[L]
        # Sort within a line by descending savings (deciders first).
        confs = sorted(confs, key=lambda c: -c["savings"])
        bits = []
        for c in confs:
            reg = c["reg_name"] or "spill"
            tag = c.get("var") or f"t.{c['conf'][-4:]}"
            bits.append(f"s{c['savings']}:{tag}->{reg}{_cand_tag(c)}")
        out.append(f"  L{L}: " + "  ".join(bits))
    if synthetic:
        bits = []
        for c in sorted(synthetic, key=lambda c: -c["savings"]):
            reg = c["reg_name"] or "spill"
            tag = c.get("var") or f"t.{c['conf'][-4:]}"
            bits.append(f"s{c['savings']}:{tag}->{reg}{_cand_tag(c)}")
        out.append("  L0 (synthetic/prolog): " + "  ".join(bits))
    return out


def render_lines(h: RegallocHint, *, max_vals: int = 8,
                 detailed: bool = False) -> list[str]:
    """Compact regalloc summary, or detailed per-line view when
    ``detailed=True`` (intended for -v / explicit user request)."""
    cm = h.cost_model
    head = (f"regalloc (actual 10.0a): {len(h.allocs)} values"
            + (f", {h.spilled} spilled" if h.spilled else "")
            + (f"  [W={h.loop_base}" if h.loop_base else "")
            + (f" load={cm['load_cost']} store={cm['store_cost']} "
               f"use={cm['use_save']}]" if cm else "]"))
    picks = []
    for a in h.allocs[:max_vals]:
        reg = a["reg_name"] or "spill"
        picks.append(f"s{a['savings']}->{reg}")
    if len(h.allocs) > max_vals:
        picks.append("…")
    lines = [head, "  " + "  ".join(picks)]
    if h.drift:
        n = len(h.drift) - 1     # last entry is the explanation footer
        lines.append(f"  given_regs DRIFT ({n} alloc(s)): RegAlloc retry "
                     "rounds active -- tie-group / creation-order levers "
                     "(Rule 28a/115, PS-alloc) are UNRELIABLE here; do not "
                     "grind order swaps.")
    if detailed:
        # The most prominent view: per-source-line breakdown of what the
        # compiler did.  Maps each conflict to its source statement so the
        # user can correlate asm-diff offsets back to the IR.
        for ln in render_per_line(h):
            lines.append("  " + ln)
    # CONFLICT CREATION order (the `cn` AddConflictNode stream) -- the order
    # the back end created conflict nodes (name-list walk + per-instruction
    # sightings).  This is what SortConflicts' ShellSort actually permutes;
    # tie-break "input positions" come from this order.
    nl = [n for n in h.namelist if n.get("defline")]
    if nl and any(n["defline"] for n in nl):
        items = []
        for n in nl[:max_vals]:
            tag = n.get("var") or (f"t.{n['conf'][-4:]}" if n.get("conf") else "?")
            items.append(f"L{n['defline']}:s{n['savings']}:{tag}->{n['reg_name'] or 'spill'}")
        if len(nl) > max_vals:
            items.append("…")
        lines.append("  conflicts(creation order): " + "  ".join(items))
    # FRONT-END BIRTH order (AllocName ``nb`` stream) -- the source-side LEVER
    # (Rule 28 / Rule 115).  Source author controls birth via declaration
    # order.  Render only when it DIFFERS from creation order (otherwise the
    # two lines would duplicate); when present, this is the actionable view
    # for "reshape the source to change tie-break outcomes".
    bl = [n for n in h.birthlist if n.get("defline")]
    if bl and any(n["defline"] for n in bl):
        creation_confs = [n["conf"] for n in nl]
        birth_confs    = [n["conf"] for n in bl if n["conf"]]
        if creation_confs != birth_confs:
            items = []
            for n in bl[:max_vals]:
                reg = n["reg_name"] or ("spill" if n["conf"] else "filtered")
                tag = n.get("var") or (f"t.{n['conf'][-4:]}" if n.get("conf") else "dead")
                items.append(f"L{n['defline']}:s{n['savings']}:{tag}->{reg}")
            if len(bl) > max_vals:
                items.append("…")
            lines.append("  names(birth order, source lever): " + "  ".join(items))
    return lines
