"""Same-size spill-slot SWAP detector (Rule 107's noisy per-row case).

``frame_hints`` catches a *total frame-size* difference (`sub esp, N`
delta).  It explicitly does NOT catch the case where PS and recomp
allocate the **same** frame but put two (or more) co-spilled, **same-size**
temps at **swapped** ``[esp+N]`` slots.  That signature is pure cascade:
``[esp]`` is a 3-byte encoding and ``[esp+4]`` a 4-byte one, so a swap
changes instruction lengths and renumbers every downstream jump
displacement — a large diff with no register change at all.  ``refresh_svga_screen``
fell exactly into this gap (112 b, only the misleading "register layout
matches PS / don't chase registers" line fired).

The lever (Rule 107 / watcom-codegen-patterns.md, watcom10.0a
``docs/temp-slot-layout.md``): same-size co-spilled temps get stack slots
in **creation order** (`TempAllocBefore` stable sort -> `Names[]` order;
`SetTempLocation` first-allocated -> highest `[esp+N]`).  The **scope** of
a source local is the lever — declaring it at function vs innermost-block
scope changes when its temp is created, hence its slot.  ``refresh_svga_screen``
went byte-exact by moving ``off`` and ``saved_idx`` to function scope.

Detection is purely from the aligned disassembly diff: rows whose two
sides are identical except for an ``[esp+disp]`` displacement, where the
multiset of PS displacements equals the recomp one (a permutation of the
same slots), with no frame-size change.  No new instrumentation needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from c2.commands.frame_hints import detect_frame_alloc

# `[esp]`, `[esp + 4]`, `[esp+0x8]`, optionally with a `dword ptr` etc. size
# prefix that capstone may emit.  Captures the displacement (None => 0).
_ESP_MEM = re.compile(r"\[esp(?:\s*\+\s*(0x[0-9a-fA-F]+|\d+))?\]")
_ESP_TOKEN = "[esp+?]"


_CALLEE_SAVE_REGS = {"ebx", "esi", "edi", "ebp"}
_CALLER_SAVE_REGS = {"eax", "ecx", "edx"}


def _caller_push_pad(insns: list) -> int:
    """Bytes of frame slots allocated by leading caller-saved (`push eax/
    ecx/edx`) prologue pushes -- Watcom's cheap small-frame idiom, which
    ``detect_frame_alloc`` (only `sub esp, N`) does not count.  These sit
    adjacent to the sub-esp region, so a spill slot can read up to this many
    bytes above ``ps_frame``.
    """
    pad = 0
    for ins in insns:
        parts = ins[3].split()
        if not parts:
            break
        op = parts[0]
        if op == "push" and len(parts) == 2 and parts[1] in _CALLER_SAVE_REGS:
            pad += 4            # a `push eax`-style frame slot
        elif op == "push" and len(parts) == 2 and parts[1] in _CALLEE_SAVE_REGS:
            continue            # callee-save register preservation
        elif op in ("sub", "add") and len(ins[3].split(",")) == 2 \
                and ins[3].split(None, 1)[1].lstrip().startswith("esp"):
            continue            # the `sub esp, N` frame alloc -- keep scanning
        else:
            break               # first body instruction (e.g. the spill mov)
    return pad


def _esp_disps(asm: str) -> list[int]:
    out: list[int] = []
    for m in _ESP_MEM.finditer(asm):
        out.append(int(m.group(1), 0) if m.group(1) else 0)
    return out


def _normalize_esp(asm: str) -> str:
    return _ESP_MEM.sub(_ESP_TOKEN, asm)


@dataclass
class SlotSwapHint:
    frame: int                       # shared `sub esp, N` size (bytes)
    pairs: list[tuple[int, int]]     # (ps_disp, rc_disp) for slot-only diff rows
    slots: list[int] = field(default_factory=list)   # the swapped slot offsets
    # Filled by ``annotate()`` from the SetTempLocation (`st`) trace + the
    # alloc var/defline join: the RC temp-list in creation/walk order, and
    # the named temps that occupy the swapped slots.
    temps: list[dict] = field(default_factory=list)  # [{walk,var,line,size,esp}]
    swapped: list[dict] = field(default_factory=list)  # the temps at the swap
    # Set by ``annotate()`` -- the ShellSort-instability diagnoser's verdict
    # (`c2.regalloc.shellsort_sim.diagnose`).  Surfaces the EXACT mechanism
    # class (shellsort-instability vs sort-stable-other vs sub-source vs
    # misbucketed) and the simulator-found flipping perturbations.
    diagnosis: object = None

    @property
    def n_rows(self) -> int:
        return len(self.pairs)


def detect(orig_insns: list, recomp_insns: list,
           rows: Optional[list[dict]] = None) -> Optional[SlotSwapHint]:
    """Return a ``SlotSwapHint`` when PS and recomp share a frame size but
    permute two-or-more same-size co-spilled temps across ``[esp+N]`` slots.

    ``rows`` is the aligned diff stream (dicts with ``o``/``r`` capstone
    tuples ``(off, size, raw, asm)`` and ``kind``).  Returns None unless the
    swap is *consistent*: the set of PS slot displacements equals the recomp
    set (a permutation), at least one row actually swaps, and ≥2 distinct
    slots are involved.
    """
    if rows is None:
        return None
    ps_frame = detect_frame_alloc(orig_insns)
    rc_frame = detect_frame_alloc(recomp_insns)
    # A pure swap does not change the frame size; a size delta is frame_hints'
    # job, not ours.
    if not ps_frame or ps_frame != rc_frame:
        return None
    _frame_top = ps_frame + _caller_push_pad(orig_insns)

    pairs: list[tuple[int, int]] = []
    for row in rows:
        if row.get("kind") == "equal":
            continue
        o = row.get("o")
        r = row.get("r")
        if not o or not r:
            continue
        o_asm, r_asm = o[3], r[3]
        # Identical instruction except for esp displacement(s)?
        if _normalize_esp(o_asm) != _normalize_esp(r_asm):
            continue
        o_d, r_d = _esp_disps(o_asm), _esp_disps(r_asm)
        if len(o_d) != 1 or len(r_d) != 1 or o_d[0] == r_d[0]:
            continue
        # Within the local-frame region (exclude outgoing stack args at/above
        # the frame top).  The boundary is ps_frame PLUS the caller-saved
        # prologue pushes (Watcom's `push eax`/`push ecx` small-frame idiom):
        # those alloc spill slots adjacent to the sub-esp region that
        # detect_frame_alloc does NOT count, so a real spill can read one push
        # above ps_frame (build_units_figures: frame 0x8 + `push eax` -> a
        # spill at [esp+8]).
        if o_d[0] >= _frame_top or r_d[0] >= _frame_top:
            continue
        pairs.append((o_d[0], r_d[0]))

    if len(pairs) < 2:
        return None
    ps_set = {p for p, _ in pairs}
    rc_set = {r for _, r in pairs}
    # Same physical slots on both sides, genuinely permuted (a relabel, not a
    # move into a new slot — that would be a size/layout change, not a swap).
    if ps_set != rc_set or len(ps_set) < 2:
        return None
    if not any(p != r for p, r in pairs):
        return None
    return SlotSwapHint(frame=ps_frame, pairs=pairs, slots=sorted(ps_set))


def annotate(h: SlotSwapHint, name: str, file: str | None = None) -> SlotSwapHint:
    """Fill ``h.temps`` / ``h.swapped`` from the SetTempLocation (`st`) trace.

    The `st` records give RC's per-temp slot allocation IN WALK ORDER (==
    the slot index); joining each temp's name to the `alloc` rows recovers
    its source variable + def line.  ``esp = frame + off`` maps the
    frame-relative slot offset to the `[esp+N]` the asm uses.  This turns
    the generic 'needs a SetTempLocation trace hook' note into the actual
    ground truth: WHICH named temps occupy the swapped slots, so the lever
    targets them by name.
    """
    try:
        from c2.commands.regalloc_hints import _lookup
        rt, _c, _b = _lookup(name.rstrip("_"), file)
    except Exception:
        return h
    slots = (rt or {}).get("slots") or []
    if not slots:
        return h
    # Also pull savings -- the RoughSortTemps key that ORDERS Names[N_TEMP]
    # before AssignOtherLocals' stable size-sort.  When all savings are
    # distinct + slot order == savings-DESC, the source-side mechanism is
    # already aligned with PS and the swap diff is downstream (re-triage as
    # ir/width/seat).  When savings tie, the AllocBefore savings-sort
    # (BuildNameConflicts) decides order; SortCmp_flag2_2b's sort-equal is set
    # by distinct [+0x24] (reverse-decl-rank).  See
    # docs/slot-swap-survey-2026-06-25.md.
    name2var = {a["name"]: (a.get("var"), a.get("defline"), a.get("savings"))
                for a in ((rt or {}).get("alloc") or [])}
    temps = []
    for i, s in enumerate(slots):
        off = (-(s["pre_size"] + s["size"] + s["base"])
               if s.get("pre_size") is not None and s.get("base") is not None
               else None)
        var, line, sav = name2var.get(s["name"], (None, None, None))
        temps.append({"walk": i, "var": var, "line": line, "size": s["size"],
                      "savings": sav,
                      "esp": (h.frame + off) if off is not None else None})
    h.temps = temps
    # The temps sitting at the swapped slots (exact esp match preferred).
    sw = [t for t in temps if t["esp"] in set(h.slots)]
    # Fallback when an extra prologue push shifts esp vs the frame base: if
    # the function has exactly as many same-size temps as swapped slots,
    # they ARE the swap.
    if len(sw) < len(h.slots):
        same = [t for t in temps if t["size"] * 8 >= 0]  # all (sizes equal here)
        if len(temps) == len(h.slots):
            sw = temps
    h.swapped = sw
    # Run the ShellSort instability diagnoser.  It classifies the residue
    # into one of:
    #   * non-stable-shell-sort  -- ShellSort reordered equal-rank same-size temps
    #   * savings-keyed          -- diff upstream in BuildNameConflicts savings sort
    #   * sub-source             -- dominated by anonymous CG temps
    # See c2/regalloc/shellsort_sim.py + docs/slot-swap-survey-2026-06-25.md.
    try:
        from c2.regalloc.shellsort_sim import diagnose
        # Derive PS's slot ORDER from the diff itself: each slot-only diff
        # row pairs an RC displacement with the PS displacement of the SAME
        # instruction, i.e. the rc->ps slot permutation.  Named temps sorted
        # by their PS slot DESC = PS's commit order -- the input the
        # simulator's flip search needs (it never ran in the hint path
        # before 2026-07-10 because nobody supplied ps_slot_order).
        ps_order = None
        try:
            rc2ps: dict = {}
            for ps_d, rc_d in h.pairs:
                rc2ps.setdefault(rc_d, {}).setdefault(ps_d, 0)
                rc2ps[rc_d][ps_d] += 1
            perm = {rc: max(cands, key=cands.get)
                    for rc, cands in rc2ps.items()}
            named = [t for t in temps if t.get("var")
                     and t.get("esp") is not None]
            if named and perm:
                ps_order = [t["var"] for t in sorted(
                    named, key=lambda t: -perm.get(t["esp"], t["esp"]))]
        except Exception:
            ps_order = None
        d = diagnose(rt, ps_slot_order=ps_order)
        d.fn = name
        h.diagnosis = d
    except Exception:
        pass
    return h


def _temp_label(t: dict) -> str:
    v = t["var"] or "<temp>"
    loc = f" (L{t['line']})" if t.get("line") else ""
    esp = f"[esp+{t['esp']:#x}]" if t.get("esp") is not None else "[esp+?]"
    return f"{v}{loc}->{esp}"


def render(h: SlotSwapHint) -> str:
    slots = ", ".join(f"[esp+{s:#x}]" if s else "[esp]" for s in h.slots)
    base = (
        f"same-size spill-SLOT swap across {slots} ({h.n_rows} rows, frame "
        f"unchanged at {h.frame:#x}).  No register changed -- co-spilled same-size "
        "temps got swapped stack slots, cascading every jump displacement.  Slots "
        "come from SortCmp_flag2_2b (i86temps.c) backed by the UNSTABLE "
        "ShellSort (DoSortList alloc-success arm; alloc-fail-> MergeList).  For "
        "distinct-+0x24 same-size temps the comparator is sort-equal, so the "
        "gap-passes reorder them (slot order is NOT the temp-list input order)."
    )
    if h.swapped:
        order = ", ".join(_temp_label(t) for t in h.temps)
        names = " <-> ".join(t["var"] or "<temp>" for t in h.swapped)
        lines = {t.get("line") for t in h.swapped if t.get("line")}
        params = any(t.get("line") and t["var"] and t["line"] == min(lines or {0})
                     for t in h.swapped) and len(lines) == 1
        lever = (
            f"  GROUND TRUTH (SetTempLocation `st` trace, simulator validated "
            f"232/232 nt_post + 130/130 PS slot-order corpus-wide -- "
            f"docs/slot-swap-survey-2026-06-25.md): RC temp-list order = "
            f"[{order}].  The swap is {names}.  FIRST: machine-exhaust the "
            "decl-order space -- COMPOSED decl swaps (often involving "
            "NON-spilled locals whose rank shifts re-seed the ShellSort) DO "
            "reach PS slot orders that single swaps of the spilled pair "
            "cannot (proven: evolve_region ad1de9e7, two composed swaps -> "
            "byte-exact; a ~500-variant forge-preset byte-oracle sweep at "
            "~0.1s/variant covers it).  If the full perm space misses, make "
            "a TEMP-SET change (local reuse merge / FUNCTION-scope hoist / "
            "statement reorder that renames the survivors' +0x24 ranks).  A "
            "clean inner-block -> FUNCTION scope hoist worked: "
            "refresh_svga_screen."
        )
        if params:
            lever += (
                "  NOTE: these share a defline (likely same-line PARAMs) -- "
                "do NOT swap the signature decl order as a lever; the Mac PPC "
                "and Windows MSVC `/Od` decompiles will show that as a "
                "SEMANTIC REGRESSION (each register-param has a definite role "
                "tied to the asm assignments).  A clean source lever for "
                "same-line PARAMs is not yet isolated -- the trace lets you "
                "SEE the `nt`/`an` effect of any candidate edit, so the "
                "search is no longer blind, but verify each edit against "
                "`c2 mac-fn` + `c2 win-decompile` to rule out semantic break."
            )
        out = base + lever + "  Rule 107 / docs/slot-swap-survey-2026-06-25.md."
        # Append the ShellSort-instability diagnoser's verdict.  Splits the
        # generic same-line-PARAM text above into a CONCRETE per-function
        # mechanism class + (when known) the simulator-found flipping
        # perturbations -- so an agent reading -v immediately knows whether
        # to reach for the ShellSort lever, the upstream-sort lever, or to
        # park as sub-source / re-triage as misbucketed.
        if h.diagnosis is not None:
            try:
                from c2.regalloc.shellsort_sim import render_diagnosis
                out += "\n" + render_diagnosis(h.diagnosis)
            except Exception:
                pass
        return out
    return base + (
        "  No `st` trace attribution available (older cache or trace missing). "
        "Re-trace with the current image (`rm -rf /tmp/c2-regalloc-corpus`) "
        "and the `an`/`nt`/`na` records will name every slot; the lever is a "
        "TEMP-SET change (local reuse merge / inner-block -> FUNCTION scope "
        "hoist), not decl-order.  Rule 107 / "
        "docs/slot-swap-survey-2026-06-25.md."
    )


def render_line(h: SlotSwapHint) -> str:
    return f"  [yellow]Slot-swap[/]: {render(h)}"


def to_json(h: Optional[SlotSwapHint]) -> Optional[dict]:
    if h is None:
        return None
    return {"frame": h.frame, "pairs": h.pairs, "slots": h.slots,
            "n_rows": h.n_rows,
            "swapped_vars": [t.get("var") for t in h.swapped] or None,
            "temps": h.temps or None}
