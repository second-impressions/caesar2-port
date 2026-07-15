"""FindRegister (RISCify rover) forward model -- the P6 engine.

The rover is the post-RegAlloc scratch-register picker (LdStAlloc ->
FindRegister@0x62a29) whose cursor-parity desyncs own the byte-rover
residue class (Rule 163; the `action` / `build_city_item` end-game).
Until 2026-07-13 it was REPLAY-only: `rover_hints._simulate` walked the
recorded `fr` stream using each record's recorded ``except`` mask
(validated against the ``frx`` ground truth 7028/7028).  What replay
cannot answer is the COUNTERFACTUAL: "same IL, one conflict re-seated --
what does the cursor pick at op N?", because ``except`` is an opaque OR.

The >= 2026-07-13 trace image records the except-mask COMPONENTS on every
fr row::

    except == zap | live | resreg          (certified 12,119/12,119)

MEASURED provenance of each component (corpus decomposition 2026-07-13;
the naive "zap is IL-static" reading was WRONG):

* ``zap`` ([ins+8] at LdStAlloc vintage) -- the ins's static zap set
  FOLDED with the registers of allocated conflicts LIVE ACROSS the ins.
  Empirically ``zap  ⊆  static(gi zap_reg|live_regs)  ∪  ⋃ spanning
  committed seats`` with missing-bits ≈ 0 corpus-wide (the spanning
  union over-claims only via linear-range holes).  THIS is the
  seat-dependent component: a re-seat R_old -> R_new moves bits here.
* ``live`` (*(ins+0x2c)+0xc) -- ~always 0 at RISCified ops (556/559
  zero on common.c); the rare nonzero rows are PHYSICAL register
  windows (call-arg marshaling / far-pair returns: EAX / EDX:EAX).
* ``resreg`` -- the result's register when it is N_REGISTER (a store
  into an allocated value's register): seat-dependent.

With the components + the per-conflict range join (``own_walk`` ins
sets), a counterfactual seat flip recomputes ``except'`` per row and
replays the (certified) cursor.
This module is the canonical home for:

* :func:`replay`               -- pure-sim picks (no frx override)
* :func:`certify_picks`        -- sim == frx per routine (the P6
                                  certification, crm10a_v2-style)
* :func:`certify_except`       -- except == zap|live|resreg per routine
* :func:`counterfactual_walk`  -- replay with component-level edits
* :func:`attribution`          -- per fr row, each except bit -> its
                                  sources (static / spanning conflicts)
* :func:`certify_attribution`  -- no unattributed bits (the corpus gate
                                  for the flip substrate)
* :func:`seat_flip_walk`       -- THE actuator: re-seat one conflict,
                                  recompute except', replay, report the
                                  changed rover picks (+ ambiguity)
* :func:`chain_vintages`       -- the bo -> br -> bk block-chain
                                  trajectory (which pass moved a block:
                                  the walk-order lever's provenance)

Corpus gates: ``docs/codegen-experiments/corpus-chain-certification.py``
(gate #9).  Surfaced through the existing landscape -- `c2 spell
--walk-order` (chain vintages), the `Rover:` hint (rover_hints imports
the same primitives), `c2 regtrace` (fr rows carry the components).

Cursor mechanics (proven, watcom10.0a docs/rover-model.md + the
2026-07-12c corrected sim): one stateful cursor per width class, reset
per routine, ++-FIRST, skipping ``except`` members; the dword ring is
EAX,EDX,EBX,ECX,ESI,EDI,EBP (ESP permanently excepted).
"""
from __future__ import annotations

from typing import Callable, Optional

# The reg tables + cursor primitives live in rover_hints (the Rover: hint
# was their first consumer); import lazily to avoid import cycles.


def _prims():
    from c2.commands.rover_hints import _REGS, _advance, _cls_of_tc, _NAME
    return _REGS, _advance, _cls_of_tc, _NAME


# ---------------------------------------------------------------- replay

def replay(fr_rows: list[dict],
           except_of: Optional[Callable[[int, dict], int]] = None
           ) -> list[tuple]:
    """Replay the three rovers over ``fr_rows`` and return one
    ``(cls, reg_name, opcode)`` per row (cls/reg None for non-rover rows).

    Unlike ``rover_hints._simulate`` this NEVER substitutes the frx truth:
    it is the pure forward model (what the certification compares against
    the truth).  ``except_of(i, row)`` overrides the except mask per row --
    the counterfactual entry point (default: the recorded mask).
    """
    _REGS, _advance, _cls_of_tc, _NAME = _prims()
    rovers = {"byte": None, "word": None, "dword": None}
    out = []
    for i, r in enumerate(fr_rows):
        cls = _cls_of_tc(r["type_class"])
        reg = None
        if cls is not None:
            exc = r["except"] if except_of is None else except_of(i, r)
            rovers[cls] = _advance(rovers[cls], _REGS[cls], exc)
            reg = _NAME[_REGS[cls][rovers[cls]]]
        out.append((cls, reg, r["opcode"]))
    return out


# ---------------------------------------------------------------- certify

def certify_picks(routine: dict) -> dict:
    """Compare the pure sim against the frx ground truth for one routine.

    Returns {"ok": n, "total": n, "mismatches": [(idx, sim, truth), ...]}.
    ``total`` counts only rows with a recorded truth (frx pairs 1:1 with
    the FOUND fr's; NULL-return rovers have none).
    """
    fr = routine.get("fr", [])
    sim = replay(fr)
    ok, total, mism = 0, 0, []
    for i, (r, (cls, reg, _)) in enumerate(zip(fr, sim)):
        t = r.get("truth")
        if not t or cls is None:
            continue
        total += 1
        if reg == t:
            ok += 1
        else:
            mism.append((i, reg, t))
    return {"ok": ok, "total": total, "mismatches": mism}


def certify_except(routine: dict) -> dict:
    """Verify ``except == zap | live | resreg`` on every component-carrying
    fr row (>= 2026-07-13 image).  Returns {"ok", "total", "mismatches"}.
    total == 0 means the trace predates the component fields."""
    ok, total, mism = 0, 0, []
    for i, r in enumerate(routine.get("fr", [])):
        if "zap" not in r:
            continue
        total += 1
        derived = r["zap"] | r["live"] | r["resreg"]
        if derived == r["except"]:
            ok += 1
        else:
            mism.append((i, derived, r["except"]))
    return {"ok": ok, "total": total, "mismatches": mism}


# ------------------------------------------------------- counterfactuals

def counterfactual_walk(fr_rows: list[dict], *,
                        live_clear: int = 0, live_set: int = 0,
                        rows: Optional[range] = None,
                        edit: Optional[Callable[[int, dict], Optional[int]]]
                        = None) -> list[tuple]:
    """Replay with SEATING-dependent components edited.

    The seat-flip primitive: a conflict re-seated R_old -> R_new changes
    ``live`` (and possibly ``resreg``) at every fr ins its range spans.
    Callers express that as ``live_clear``/``live_set`` hw_reg_set masks
    applied over ``rows`` (default: all), or supply ``edit(i, row) ->
    except'|None`` for full control (None = recorded mask).

    Rows without components (pre-2026-07-13 traces) fall back to the
    recorded mask -- the walk is then only exact where the edit is a
    no-op; certify_except() == total tells you the substrate is complete.
    """
    def _exc(i: int, r: dict) -> int:
        if edit is not None:
            e = edit(i, r)
            if e is not None:
                return e
            return r["except"]
        if "zap" not in r or (rows is not None and i not in rows):
            return r["except"]
        live = (r["live"] & ~live_clear) | live_set
        return r["zap"] | live | r["resreg"]

    return replay(fr_rows, except_of=_exc)


# ------------------------------------------------- seat-flip attribution

BASE_EXCEPT = 0x40fff800   # the reserved band + ESP: permanently excepted


def _as_mask(reg) -> int:
    return int(reg, 16) if isinstance(reg, str) else int(reg)


def _conflict_ranges(routine: dict) -> list[dict]:
    """Committed conflicts with their seat mask + range ins-set (the
    own_walk gi scan -- the compiler's OWN traversal of conf->ins_range at
    allocation time).  One entry per committed presentation."""
    out = []
    for a in routine.get("alloc", []):
        if a.get("reg") is None:
            continue
        ins_set = {x["ins"] for x in (a.get("own_walk") or [])}
        if ins_set:
            out.append({"conf": a["conf"], "var": a.get("var"),
                        "reg": _as_mask(a["reg"]),
                        "reg_name": a.get("reg_name"),
                        "ins_set": ins_set, "alloc": a})
    return out


def _static_masks(routine: dict) -> dict:
    """ins -> allocation-vintage (zap_reg | live_regs) from any gi walk row
    (the NON-seat-dependent part of the LdStAlloc except mask)."""
    st: dict = {}
    for a in routine.get("alloc", []):
        for x in (a.get("own_walk") or []):
            st.setdefault(x["ins"],
                          x.get("zap_reg", 0) | x.get("live_regs", 0))
    return st


def attribution(routine: dict) -> list[dict]:
    """Per component-carrying fr row: attribute every except bit to its
    source(s).  Returns one dict per such row::

        {"idx": i, "static": mask, "spanning": [(conf_entry, seat), ...],
         "unattributed": mask}

    ``unattributed`` = except bits (minus BASE_EXCEPT/live/resreg/static)
    covered by NO spanning committed conflict -- certified ~0 corpus-wide
    (:func:`certify_attribution`); a nonzero value means the flip
    machinery must not touch this row."""
    confs = _conflict_ranges(routine)
    static = _static_masks(routine)
    out = []
    for i, f in enumerate(routine.get("fr", [])):
        if "zap" not in f:
            continue
        span = [(c, c["reg"]) for c in confs if f["ins"] in c["ins_set"]]
        st = static.get(f["ins"], 0)
        covered = st | f["live"] | f["resreg"] | BASE_EXCEPT
        for c, m in span:
            covered |= m
        out.append({"idx": i, "static": st, "spanning": span,
                    "unattributed": f["except"] & ~covered})
    return out


def certify_attribution(routine: dict) -> dict:
    """The flip-substrate gate: every fr except bit must be attributable to
    BASE_EXCEPT / static / live / resreg / a spanning committed seat.
    Returns {"ok", "total", "pinned", "misses": [(idx, unattributed_mask)]}.

    ``pinned`` counts the unattributed rows that are FLIP-IRRELEVANT and
    excluded from misses (measured classes, 2026-07-13 corpus audit):
    a NULL-return row (no frx truth -- nothing was picked) or a
    forced-scratch row whose mask leaves <= 1 selectable register free
    (e.g. jump_to_citymap_ptr's 0x7ffffbff everything-but-EBP pin) --
    the whole mask is a pin marker there, not a live-fold, and no seat
    flip can move the pick."""
    _REGS, _advance, _cls_of_tc, _NAME = _prims()
    fr = routine.get("fr", [])
    ok, total, pinned, miss = 0, 0, 0, []
    for row in attribution(routine):
        total += 1
        if row["unattributed"] == 0:
            ok += 1
            continue
        f = fr[row["idx"]]
        cls = _cls_of_tc(f["type_class"])
        ring = [m for m in _REGS.get(cls, []) if m and m != 0x800]
        free = sum(1 for m in ring if (m & f["except"]) == 0)
        if f.get("truth") is None or free <= 1:
            pinned += 1
        else:
            miss.append((row["idx"], row["unattributed"]))
    return {"ok": ok, "total": total, "pinned": pinned, "misses": miss}


def seat_flip_walk(routine: dict, var: str, new_reg: str) -> Optional[dict]:
    """THE P6c actuator: re-seat conflict ``var`` (name or conf ptr) to
    ``new_reg`` and report the rover picks that change.

    Mechanism (grounded in the measured decomposition, module docstring):
    at every fr row inside the conflict's range whose except mask carries
    the old seat, swap ``R_old -> R_new`` in the mask -- unless the bit is
    ALSO owed to another source (static / another spanning conflict with
    the same seat), in which case R_old stays and only R_new is added
    (the row is flagged ambiguous).  resreg rows whose result IS the
    flipped conflict swap too.  Then replay the certified cursor.

    Returns {"conf", "old_reg", "new_reg", "rows_touched", "ambiguous",
    "changes": [(idx, line, old_pick, new_pick)]} or None (conflict not
    found / not committed / no component rows).  The byte compile stays
    the oracle: a flip's rover consequences are PREDICTIONS to screen
    spellings with, not proof."""
    from c2.regalloc.reglists import REG_NAME
    name_to_mask = {n.lower(): m for m, n in REG_NAME.items()}
    new_mask = name_to_mask.get(new_reg.lower())
    if new_mask is None:
        return None
    confs = _conflict_ranges(routine)
    target = next((c for c in confs
                   if c["var"] == var or c["conf"] == var), None)
    if target is None:
        return None
    old_mask = target["reg"]
    if old_mask == new_mask:      # identity flip: provably a no-op
        return {"conf": target["conf"], "var": target["var"],
                "old_reg": (target.get("reg_name") or "").lower(),
                "new_reg": new_reg.lower(), "rows_touched": [],
                "ambiguous": [], "changes": []}
    static = _static_masks(routine)
    fr = routine.get("fr", [])
    touched, ambiguous = [], []

    def edit(i: int, f: dict) -> Optional[int]:
        if "zap" not in f or f["ins"] not in target["ins_set"]:
            return None
        exc = f["except"]
        if exc & old_mask == 0:
            return None
        # is the old seat owed to ANOTHER source at this row?
        other = static.get(f["ins"], 0) | f["live"] | BASE_EXCEPT
        for c in confs:
            if c is not target and f["ins"] in c["ins_set"]:
                other |= c["reg"]
        if old_mask & ~other:
            exc = (exc & ~old_mask) | new_mask
            touched.append(i)
        else:
            exc = exc | new_mask          # conservative: keep + add
            ambiguous.append(i)
        if f.get("resreg", 0) == old_mask:
            # the row's result IS (almost certainly) the flipped value's
            # register store -- its resreg contribution moves with it
            exc = (exc & ~old_mask) | new_mask
        return exc

    base = replay(fr)

    def _exc(i: int, f: dict) -> int:
        e = edit(i, f)
        return f["except"] if e is None else e

    flipped = replay(fr, except_of=_exc)
    changes = [(i, fr[i].get("line"), b[1], n[1])
               for i, (b, n) in enumerate(zip(base, flipped)) if b != n]
    return {"conf": target["conf"], "var": target["var"],
            "old_reg": (target.get("reg_name") or "").lower(),
            "new_reg": new_reg.lower(),
            "rows_touched": touched, "ambiguous": ambiguous,
            "changes": changes}


# ------------------------------------------------------- the chain model

def predict_chain(routine: dict) -> Optional[list[str]]:
    """The OFFLINE MakeFlowGraph chain model: predict the post-MFG block
    chain from the recorded flow graph (br + bre, >= 2026-07-13b image).

    Faithful reproduction of the 10.0a passes (OW v1 flograph.c, offsets
    verified in the binary at 0x5cd4f/0x5ccfd):

    * ``DepthFirstSearch``/``MarkVisited`` -- recursive DFS from HeadBlock
      over each block's edges IN EDGE-ARRAY ORDER, pushing each block
      onto BlockList at POST-order; unreached blocks (irreducible-side)
      are appended in chain order.
    * ``FixLinks`` -- the chain becomes the reverse of the push order
      (= reverse post-order, RPO).
    * ``FindIntervals``/``ReorderBlocks`` -- the Cocke/Allen interval
      construction over the RPO chain (absorb a block into its sole
      predecessor-parent interval; else open a new interval), iterated
      per level to fixpoint; the chain is then re-emitted in interval-
      TREE order (children in absorb order, leftmost-descent to the
      level-0 leaf).  Irreducible graphs (FindIntervals != 1 interval)
      keep the RPO chain (MFG calls Irreducable and skips the reorder).
    * ``ReturnsToBottom`` -- RETURN-class blocks (class bit0) unspliced
      and appended bottom-up (reverse-chain scan order); the original
      last block never moves.

    A function whose entry cannot reach every block (DepthFirstSearch
    returns irreducible) keeps its ORIGINAL chain -- MFG restores links
    and bails; the prediction is the identity.

    Returns the predicted chain (list of blk ptrs) or None (no br data).
    """
    br = routine.get("chain_post_mfg") or []
    if not br or not any(b.get("edges") for b in br):
        return None
    edges = {b["blk"]: b.get("edges", []) for b in br}
    cls = {b["blk"]: b["class"] for b in br}
    entry = br[0]["blk"]
    visited: set = set()
    postorder: list[str] = []

    def visit(blk: str) -> None:          # MarkVisited, iteratively
        stack = [(blk, 0)]
        visited.add(blk)
        while stack:
            b, i = stack.pop()
            es = edges.get(b, [])
            while i < len(es) and (es[i] in visited
                                   or es[i] not in edges):
                i += 1
            if i < len(es):
                stack.append((b, i + 1))
                visited.add(es[i])
                stack.append((es[i], 0))
            else:
                postorder.append(b)        # post-order push

    visit(entry)
    if len(visited) != len(br):
        # DepthFirstSearch failure: MFG restores the original links and
        # bails -- the chain is unchanged (identity prediction).
        return [b["blk"] for b in br]
    chain = list(reversed(postorder))      # FixLinks: RPO
    chain = _reorder_blocks(chain, edges)  # FindIntervals + ReorderBlocks
    # ReturnsToBottom: scan prev-order (last-1 .. first), moving RETURN
    # blocks after the current last (encounter = reverse chain order).
    non_ret, moved = [], []
    for b in chain:
        (moved if (cls.get(b, 0) & 1) and b != chain[-1] else non_ret).append(b)
    return non_ret + list(reversed(moved))


def _reorder_blocks(chain: list[str], succ: dict) -> list[str]:
    """OW flograph.c FindIntervals + ReorderBlocks over the RPO ``chain``.

    Interval nodes: dicts {parent, sub_int (first child), next_sub_int
    (sibling), level, first_block}.  Level 0 = one leaf per block in
    chain order; each level wraps HeadBlock's interval, then absorbs
    every chain block whose non-internal predecessors all share ONE
    already-parented interval (append to that parent's child list);
    others open new intervals.  Fixpoint: num == prev_num or num == 1.
    Reducible (num == 1) => re-emit the chain in interval-tree order;
    irreducible => the RPO chain stands (MFG's Irreducable path)."""
    preds: dict = {b: [] for b in chain}
    for b in chain:
        for d in succ.get(b, []):
            if d in preds:
                preds[d].append(b)

    def leaf(b):
        return {"parent": None, "sub_int": None, "next_sub_int": None,
                "level": 0, "first_block": b}

    ivl = {b: leaf(b) for b in chain}      # blk -> level-0 interval

    def interval_no(blk, level):
        cur = ivl[blk]
        for _ in range(level):
            cur = cur["parent"]
        return cur

    def new_interval(blk, level):
        prev = interval_no(blk, level - 1)
        new = {"parent": None, "sub_int": prev, "next_sub_int": None,
               "level": level, "first_block": blk}
        prev["parent"] = new
        return new

    num = len(chain)
    level = 1
    head = chain[0]
    while True:
        prev_num = num
        num = 1
        top = new_interval(head, level)
        for blk in chain[1:]:
            curr = interval_no(blk, level - 1)
            if curr["parent"] is not None:
                continue
            prev_int, add = None, False
            src_list = preds[blk]
            if not src_list:
                add = True
            for s in src_list:
                test = interval_no(s, level - 1)
                if test is curr:
                    continue                    # internal edge
                test = test["parent"]
                if test is None:                # lower-level head
                    add = True
                    break
                if prev_int is None:
                    prev_int = test
                elif test is not prev_int:      # different predecessor
                    add = True
                    break
            if not add and prev_int is not None:
                curr["parent"] = prev_int
                t = prev_int["sub_int"]
                while t["next_sub_int"] is not None:
                    t = t["next_sub_int"]
                t["next_sub_int"] = curr
            else:
                new_interval(blk, level)
                num += 1
        level += 1
        if num == prev_num or num == 1:
            break
    if num != 1:
        return chain                            # irreducible: RPO stands
    # ReorderBlocks: interval-tree emission
    out = [head]
    curr = ivl[head]
    while True:
        while curr["next_sub_int"] is None:
            curr = curr["parent"]
            if curr is None:
                break
        if curr is None:
            break
        curr = curr["next_sub_int"]
        while curr["level"] > 0:
            curr = curr["sub_int"]
        out.append(curr["first_block"])
    return out


def certify_chain_model(routine: dict) -> Optional[dict]:
    """Compare :func:`predict_chain` against the RECORDED br chain.
    Returns {"ok": bool, "n": len, "first_diff": idx|None} or None."""
    pred = predict_chain(routine)
    if pred is None:
        return None
    got = [b["blk"] for b in routine.get("chain_post_mfg", [])]
    if pred == got:
        return {"ok": True, "n": len(got), "first_diff": None}
    fd = next((i for i, (p, g) in enumerate(zip(pred, got)) if p != g),
              min(len(pred), len(got)))
    return {"ok": False, "n": len(got), "first_diff": fd}


# ------------------------------------------------------- chain vintages

def chain_vintages(routine: dict) -> list[dict]:
    """The block-chain trajectory bo (FE birth) -> br (post-MakeFlowGraph)
    -> bk (LdStAlloc walk), keyed by block pointer.

    Returns one dict per POST-MFG chain position (the br stream order)::

        {"blk": ptr, "post_mfg": i, "birth": j|None, "walk": k|None,
         "cls": class_flags, "ret": bool, "hauled_mfg": bool,
         "moved_after_mfg": bool}

    * ``hauled_mfg``      -- birth order != post-MFG order at this block
                             (the pre-conflicts optimizer / MakeFlowGraph
                             DFS/RPO / ReturnsToBottom moved it; ret=True
                             names the ReturnsToBottom haul).
    * ``moved_after_mfg`` -- post-MFG order != LdStAlloc walk order (a
                             LATER pass moved it; blocks absent from bk
                             were merged away, walk=None).

    Empty when the trace predates the br probe (2026-07-13 image).
    """
    br = routine.get("chain_post_mfg", [])
    if not br:
        return []
    birth_ord = {b["blk"]: i
                 for i, b in enumerate(routine.get("blocks_born", []))}
    walk_ord = {p: i for i, p in enumerate(routine.get("ldst_blocks", []))}
    # rank the SHARED blocks in each vintage to compare relative order
    shared_birth = [r["blk"] for r in br if r["blk"] in birth_ord]
    birth_rank = {b: i for i, b in enumerate(
        sorted(shared_birth, key=lambda b: birth_ord[b]))}
    shared_walk = [r["blk"] for r in br if r["blk"] in walk_ord]
    walk_rank = {b: i for i, b in enumerate(
        sorted(shared_walk, key=lambda b: walk_ord[b]))}
    out = []
    for i, r in enumerate(br):
        blk = r["blk"]
        birth = birth_ord.get(blk)
        walk = walk_ord.get(blk)
        pos_in_shared_birth = ([x["blk"] for x in br
                                if x["blk"] in birth_ord].index(blk)
                               if blk in birth_ord else None)
        pos_in_shared_walk = ([x["blk"] for x in br
                               if x["blk"] in walk_ord].index(blk)
                              if blk in walk_ord else None)
        out.append({
            "blk": blk, "post_mfg": i, "birth": birth, "walk": walk,
            "cls": r["class"], "ret": bool(r["class"] & 1),
            "hauled_mfg": (pos_in_shared_birth is not None
                           and birth_rank.get(blk) != pos_in_shared_birth),
            "moved_after_mfg": (pos_in_shared_walk is not None
                                and walk_rank.get(blk) != pos_in_shared_walk),
        })
    return out
