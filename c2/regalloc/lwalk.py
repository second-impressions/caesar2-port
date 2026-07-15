"""LdStAlloc walk analysis -- the shared library over the ``~WV1 lw`` /
``fr`` / ``lc`` / ``lcx*`` trace records (trace image >= 2026-07-09).

THE canonical home for the analyses that were prototyped as standalone
scripts in the watcom10.0a repo (``tools/lw_map.py``, ``tools/lw_diff.py``,
``tools/walk_order.py`` -- now superseded; kept there only as probe-side
debug harnesses).  Everything here is surfaced through the c2 front door:

  * :func:`window_census`   -> the ``Rover:`` hint (rover_hints.py) appends
    a per-inject-window candidate map whenever the influence-window fit
    names a window.
  * :func:`spelling_compare` -> ``c2 spell <fn> <candidate.c>`` (the
    staged INERT@TREE / INERT@BURN / LIVE localizer; the candidate view
    also prints :func:`birth_compare` (block births, ``bo``) and
    :func:`il_birth_compare` (IL-instruction births, ``ni``) -- the two
    layers BETWEEN tree and walk, so every inert verdict names the stage
    that absorbed the spelling).
  * :func:`walk_vs_layout`  -> ``c2 spell <fn> --walk-order`` (birth
    ordinals per walked block; reverse-arm restructure detection).
  * :func:`compress_context` -> ``c2 spell <fn> --fusion`` (cw records x
    chain block: the pair-scan inputs of every LdStCompress attempt --
    the chain-separation lens).

  The SOURCE-CONSTRUCT -> BLOCK-BIRTH dictionary (which C constructs
  add/move block births; the label lever; loop-form signatures; the
  byte-class RMW lever) lives at watcom10.0a
  docs/block-birth-dictionary.md -- consult it before designing a
  structural variant.

Background (docs in the watcom10.0a repo: docs/rover-model.md "The
complete walk"): the RISCify rover advances only on ops that
LoadStoreIns actually RISCifies -- Enregister's gates decide, and the
operand/result KINDS in each ``lw`` record encode the verdict:

  * MOV (0x26): RISCified iff op0 is N_CONSTANT(0) and the result kind
    is in {N_INDEXED(1), N_MEMORY(2), N_TEMP(4)} -- the const-store class.
  * converts 0x24/0x25, misc <0x2a, BOUND 0x36: never RISCified.
  * scan class >=0x2a (cmp/test/arith): the first operand with kind in
    {1,2,4} is registerized (a split-out load = a rover advance).
  * plain ``mov reg,[mem]`` loads NEVER advance; ops whose operands are
    all N_REGISTER (allocator-bound values) never advance.

Therefore the byte-neutral +1 lever is LOAD-FOLDING (``x = g; ... x OP k``
-> ``g OP k`` inline: the split lands the rover on the same register =
identical bytes, one more advance), and the -1 lever is the reverse
(name the temp).  ``window_census`` enumerates exactly which ops in a
window are candidates for either direction.

The ``lc``/``lcx*`` pairing additionally resolves every RISCified pair to
fused (``lc``) or a NAMED rejection (``lcx0`` = pair separated -- the
byte-level "hoist" fingerprint, Score's ReplaceLoad is the separator;
``lcx1..5`` = zap/interference/encoding rejects).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# operand/result kind bytes (name+4)
KIND_NAMES = {0: 'CONST', 1: 'IDX', 2: 'MEM', 3: 'REG', 4: 'TEMP', 0xf: '-'}
REGISTERIZABLE = {1, 2, 4}

# type_class -> rover class (mirrors rover_hints._cls_of_tc)
TC_CLASS = {0: 'byte', 1: 'byte', 2: 'word', 3: 'word',
            4: 'dword', 5: 'dword', 6: 'dword'}

LCX_MEANING = {
    'lcx0': 'pair separated (Score coalesce; the byte-level "hoist")',
    'lcx1': 'result-mov reg in next ins zap set',
    'lcx2': 'load reg interferes with sibling N_REGISTER operand',
    'lcx3': 'load reg zapped by next ins',
    'lcx4': 'ChangeIns encoding refusal',
    'lcx5': 'operand-load pair register mismatch',
}


def skip_verdict(r: dict) -> str:
    """Why a visited-but-not-RISCified lw op was skipped (Enregister's
    gates, from the 0x62939 decompile)."""
    op = r['opcode']
    if op in (0x24, 0x25):
        return 'convert'
    if op == 0x36:
        return 'bound-op'
    if op == 0x26:
        if r['op0kind'] != 0:
            return 'mov-src-not-const'
        return 'mov-dst-reg'
    if op < 0x2a:
        return 'opcode-class'
    kinds = [k for k in (r['op0kind'], r['op1kind']) if k != 0xf]
    if any(k in REGISTERIZABLE for k in kinds):
        return 'UNEXPECTED(reg-izable operand)'
    return 'all-reg'


@dataclass
class WindowCensus:
    """Per-inject-window candidate map for the rover ±N-advance hunt."""
    cls: str                      # rover class the window is about
    lo_line: Optional[int]        # source-line bounds (best effort)
    hi_line: Optional[int]
    n_riscified: int = 0          # -1 candidates (name the value)
    n_foldable: int = 0           # +1 candidates: mov-src-not-const loads
    fold_lines: list = field(default_factory=list)   # their source lines
    n_flippable: int = 0          # other skipped ops w/ registerizable kind
    flip_lines: list = field(default_factory=list)
    n_pinned: int = 0             # convert/bound/const->reg/all-reg: no lever

    def verdict(self) -> str:
        if self.n_foldable or self.n_flippable:
            leads = []
            if self.n_foldable:
                ls = ','.join(f'L{x}' for x in self.fold_lines[:4])
                leads.append(f'{self.n_foldable} foldable load(s) [{ls}]'
                             ' -- inline the read into its consumer (+1)')
            if self.n_flippable:
                ls = ','.join(f'L{x}' for x in self.flip_lines[:4])
                leads.append(f'{self.n_flippable} flippable op(s) [{ls}]')
            return '; '.join(leads)
        return ('kind-flip-free -- every skipped op is convert/bound/'
                'const->REG/all-reg: the divergence is IL-birth or '
                'walk-order class, NOT reachable by operand-kind spellings')


def fr_site(f: dict) -> Optional[tuple]:
    """SITE IDENTITY of a RISCified op, from the 2026-07-11 fr extension
    (result/op0 name identity: class byte, v.symbol handle, v.offset).

    Returns ``(role, sym_handle, offset)`` -- role 'res' for a const store
    (result is the N_MEMORY destination), 'op0' for a split cmp/test load
    (op0 is the N_MEMORY source) -- or None on pre-extension caches.  The
    (sym, off) pair joins every advance (even Score-coalesced / re-fused
    ones) to its destination global, which line-only attribution cannot do
    once the walk-vs-layout reorder kicks in."""
    if f.get("rescls") == 1:            # N_MEMORY result: const store
        return ("res", f["ressym"], f["resoff"])
    if f.get("op0cls") == 1:            # N_MEMORY op0: split load
        return ("op0", f["op0sym"], f["op0off"])
    if f.get("rescls") == 4:            # N_INDEXED result (array store)
        return ("res-ix", f["ressym"], f["resoff"])
    return None


def fr_sites_by_symbol(fr: list) -> dict:
    """Group a routine's fr records by site symbol: {(sym,off): [fr_idx,...]}
    in walk order.  With ``fr[i]['truth']`` (the frx ground-truth pick, also
    attached at parse time) this gives per-global rover-pick sequences that
    can be diffed against PS's disasm picks per SYMBOL -- the robust anchor
    identification the rover-fit workflow needed."""
    out: dict = {}
    for i, f in enumerate(fr):
        s = fr_site(f)
        if s is not None:
            out.setdefault((s[1], s[2]), []).append(i)
    return out


def window_census(lw: list, fr: list, cls: str,
                  fr_lo: int, fr_hi: int) -> Optional[WindowCensus]:
    """Candidate map for the lw ops between two fr records.

    ``fr_lo``/``fr_hi`` index the routine's ``fr`` list (the influence-window
    fit's coordinates); the census covers the lw rows strictly between the
    two anchoring RISCified ops (inclusive of edges for context counts).
    """
    if not lw or not fr:
        return None
    fr_lo = max(0, min(fr_lo, len(fr) - 1))
    fr_hi = max(0, min(fr_hi, len(fr) - 1))
    lw_pos = {r['ins']: i for i, r in enumerate(lw)}
    a = lw_pos.get(fr[fr_lo]['ins'])
    b = lw_pos.get(fr[fr_hi]['ins'])
    if a is None or b is None:
        return None
    if a > b:
        a, b = b, a
    fr_ins = {x['ins'] for x in fr}
    wc = WindowCensus(cls=cls,
                      lo_line=fr[fr_lo].get('line') or None,
                      hi_line=fr[fr_hi].get('line') or None)
    for i in range(a, b + 1):
        r = lw[i]
        if TC_CLASS.get(r['type_class']) != cls:
            continue
        if r['ins'] in fr_ins:
            wc.n_riscified += 1
            continue
        v = skip_verdict(r)
        if v == 'mov-src-not-const' and r['op0kind'] in REGISTERIZABLE:
            wc.n_foldable += 1
            if r['line']:
                wc.fold_lines.append(r['line'])
        elif v.startswith('UNEXPECTED'):
            wc.n_flippable += 1
            if r['line']:
                wc.flip_lines.append(r['line'])
        else:
            wc.n_pinned += 1
    return wc


def census_after_line(lw: list, fr: list, cls: str,
                      line: int) -> Optional[WindowCensus]:
    """Census of the inject GAP named by a Rover-closeable verdict: the lw
    ops between the fr op at ``line`` and the next same-class fr op (the
    span where the +k advance must come from).  Used by decomp-verify to
    annotate each closeable site with its concrete candidates."""
    idx = [i for i, r in enumerate(fr) if r.get('line') == line]
    if not idx:
        return None
    lo = idx[0]
    hi = next((j for j in range(lo + 1, len(fr))
               if TC_CLASS.get(fr[j].get('type_class', -1)) == cls), lo)
    return window_census(lw, fr, cls, lo, hi)


def fusion_map(routine: dict) -> list[dict]:
    """Resolve every RISCified (fr) ins to fused (lc) or a named lcx
    rejection.  Returns [{'fr_idx', 'line', 'state'}] where state is in
    {'fused', 'lcx0'..'lcx5', 'no-record'}.

    Timing note (proven 2026-07-09): ALL lc/lcx events come from ONE
    LdStCompress driver at PostOptimize's END (`cd` marker; sole caller
    of the worker) -- the split (fr) happens at PostOptimize's HEAD and
    the fuse decision LAST, after Score / the loop-depth pass / 63404 /
    54990 have perturbed adjacency.  A 'fused' pair whose PS counterpart
    kept the split form (the cap_land_value kept-triple) therefore
    diverged in one of those INTERMEDIATE passes, not in the compress
    gate itself."""
    lc = {x['ins'] for x in routine.get('lc', [])}
    lcx = {x['ins']: x['why'] for x in routine.get('lcx', [])}
    out = []
    for i, r in enumerate(routine.get('fr', [])):
        st = ('fused' if r['ins'] in lc
              else lcx.get(r['ins'], 'no-record'))
        out.append({'fr_idx': i, 'line': r.get('line'), 'state': st})
    return out


def score_coalesce_chains(routine: dict) -> list[dict]:
    """Follow Score's successful ``sb`` coalesces from every ``lcx0``
    RISCified instruction to the earlier instruction it was folded into.

    ``lcx0`` only says that Score separated the load/store pair before
    LdStCompress ran.  The trace's newer ``sb.into`` field names the other
    end, and that instruction can itself have been coalesced.  Returning the
    transitive chain turns the generic "Score hoist" verdict into a concrete
    source-line / block target for spelling search.

    Each node carries the best source attribution available from the final
    LdStAlloc walk.  Optimizer-born or deleted intermediate instructions can
    have no ``lw`` row; their raw pointer is intentionally retained so the
    next linked node still makes the chain visible.
    """
    sb: dict[str, list[dict]] = {}
    for event in routine.get('score_events', []):
        if event.get('tag') == 'sb' and event.get('into'):
            sb.setdefault(event['ins'], []).append(event)

    lw = {row['ins']: row for row in routine.get('lw', [])}
    lcx0 = {row['ins'] for row in routine.get('lcx', [])
            if row.get('why') == 'lcx0'}
    out = []
    for fr_idx, fr in enumerate(routine.get('fr', [])):
        if fr['ins'] not in lcx0:
            continue
        nodes = []
        current = fr['ins']
        seen = set()
        while current not in seen and current in sb:
            seen.add(current)
            # Score may revisit an instruction.  The last successful edge is
            # the state seen by the final compress pass.
            event = sb[current][-1]
            target = event['into']
            row = lw.get(target)
            nodes.append({
                'ins': current,
                'opcode': event.get('opcode'),
                'into': target,
                'into_line': row.get('line') if row else None,
                'into_blk': row.get('blk') if row else None,
                'into_opcode': row.get('opcode') if row else None,
            })
            current = target
        out.append({'fr_idx': fr_idx, 'line': fr.get('line'),
                    'ins': fr['ins'], 'nodes': nodes})
    return out


# ---------------------------------------------------------------- spelling
def _walk_rows(routine: dict) -> list[tuple]:
    fr_ins = {x['ins'] for x in routine.get('fr', [])}
    return [(r['line'], r['opcode'], r['type_class'], r['reskind'],
             r['op0kind'], r['op1kind'], r['ins'] in fr_ins)
            for r in routine.get('lw', [])]


def _advances(rows: list[tuple]) -> dict:
    out: dict = {}
    for ln, op, tc, rk, o0, o1, risc in rows:
        if risc:
            c = TC_CLASS.get(tc, f'tc{tc:x}')
            out[c] = out.get(c, 0) + 1
    return out


def _tree_shapes(routine: dict) -> Optional[list[str]]:
    forest = routine.get('ir')
    if forest is None:
        return None
    try:
        from c2.tree_diff import shape_from_ir_forest
        return [s.pretty() for s in shape_from_ir_forest(forest)]
    except Exception:
        return None


@dataclass
class SpellingVerdict:
    """Three-stage localization of where a spelling difference dies."""
    stage: str                    # 'INERT@TREE' | 'INERT@BURN' | 'LIVE' | 'LIVE(reorder)'
    tree_same: Optional[bool]
    walk_same: bool
    adv_base: dict
    adv_cand: dict
    delta: dict
    walk_rows_base: list = field(default_factory=list)
    walk_rows_cand: list = field(default_factory=list)
    trees_base: Optional[list] = None
    trees_cand: Optional[list] = None

    def headline(self) -> str:
        if self.stage == 'INERT@TREE':
            return ('INERT@TREE -- the parser/tree-build canonicalized the '
                    'spelling away; provably unreachable, stop this family')
        if self.stage == 'INERT@BURN':
            return ('INERT@BURN -- trees differ but the LdStAlloc walk is '
                    'identical; the tree->IL burn is the filter -- other '
                    'tree spellings of this class may still work')
        if self.stage == 'LIVE':
            return f'LIVE -- advance DELTA {self.delta}; byte-compile it'
        return ('LIVE(reorder) -- walk differs with zero advance delta; '
                'may still move seats -- byte-compile it')


def spelling_compare(base_routine: dict, cand_routine: dict) -> SpellingVerdict:
    """The three-stage spelling-difference localizer (TREE -> WALK ->
    ADVANCES).  Callers trace the two TU variants themselves (see
    c2/commands/spell.py) so this stays a pure function."""
    ta, tb = _tree_shapes(base_routine), _tree_shapes(cand_routine)
    tree_same = (ta == tb) if (ta is not None and tb is not None) else None
    ra, rb = _walk_rows(base_routine), _walk_rows(cand_routine)
    sig = lambda r: (r[1], r[2], r[3], r[4], r[5], r[6])
    walk_same = [sig(r) for r in ra] == [sig(r) for r in rb]
    adv_a, adv_b = _advances(ra), _advances(rb)
    delta = {k: adv_b.get(k, 0) - adv_a.get(k, 0)
             for k in set(adv_a) | set(adv_b)}
    delta = {k: v for k, v in delta.items() if v}
    if tree_same:
        stage = 'INERT@TREE'
    elif tree_same is False and walk_same:
        stage = 'INERT@BURN'
    elif delta:
        stage = 'LIVE'
    elif not walk_same:
        stage = 'LIVE(reorder)'
    else:
        stage = 'INERT@BURN'   # tree stage unavailable, walk identical
    return SpellingVerdict(stage=stage, tree_same=tree_same,
                           walk_same=walk_same, adv_base=adv_a,
                           adv_cand=adv_b, delta=delta,
                           walk_rows_base=ra, walk_rows_cand=rb,
                           trees_base=ta, trees_cand=tb)


# -------------------------------------------------------------- walk order
def walk_vs_layout(routine: dict) -> list[dict]:
    """Group the lw walk by block and rank against min-source-line layout
    order.  Blocks whose walk rank deviates from layout rank are the
    boundary-crossing candidates of the walk-order divergence class
    (else-if chain arms are walked in REVERSE source order while the
    emitted layout stays source-order).

    With a `bo`-carrying trace (image >= 2026-07-09) each row also gets
    BIRTH provenance: `birth` = the block's ordinal in the front-end
    GenBlock stream (tree-burn generation order -- the chain order BEFORE
    the optimizer restructured it), or 'opt' for optimizer-born blocks
    (blktrim merge products, absent from the bo stream).  A walked arm
    sequence whose birth ordinals run BACKWARD (e.g. 6,5,3) is the named
    proof of the reverse-arm restructure -- the lever question becomes
    \"which source change flips the post-restructure chain order\", and
    diffing two spellings' birth streams (bo) localizes WHERE the front
    end changed generation order."""
    blocks: dict = {}
    fr_ins = {x['ins'] for x in routine.get('fr', [])}
    for r in routine.get('lw', []):
        b = blocks.setdefault(r['blk'], {'lines': set(), 'adv': {}})
        if r['line']:
            b['lines'].add(r['line'])
        if r['ins'] in fr_ins:
            c = TC_CLASS.get(r['type_class'], '?')
            b['adv'][c] = b['adv'].get(c, 0) + 1
    # bk index -> block POINTER (ldst_blocks), pointer -> birth ordinal (bo)
    walk_ptrs = routine.get('ldst_blocks', [])
    birth_ord = {b['blk']: i
                 for i, b in enumerate(routine.get('blocks_born', []))}
    # >= 2026-07-13 image: the post-MakeFlowGraph chain vintage (br).
    # post_mfg = the block's ordinal AFTER the DFS/RPO relink +
    # ReorderBlocks + ReturnsToBottom; `ret` = RETURN-class (bit0, the
    # ReturnsToBottom haul predicate).  birth -> post_mfg divergence =
    # the pre-conflicts optimizer / MakeFlowGraph moved the block;
    # post_mfg -> walk divergence = a LATER pass did.
    mfg_ord = {b['blk']: i
               for i, b in enumerate(routine.get('chain_post_mfg', []))}
    mfg_cls = {b['blk']: b['class']
               for b in routine.get('chain_post_mfg', [])}
    with_lines = [b for b in sorted(blocks) if blocks[b]['lines']]
    layout_rank = {b: i for i, b in enumerate(
        sorted(with_lines, key=lambda b: min(blocks[b]['lines'])))}
    out = []
    for wpos, b in enumerate(with_lines):
        lines = sorted(blocks[b]['lines'])
        ptr = walk_ptrs[b] if isinstance(b, int) and b < len(walk_ptrs) else None
        birth = birth_ord.get(ptr, 'opt' if ptr is not None else None) \
            if birth_ord else None
        out.append({'walk': wpos, 'blk': b,
                    'lines': (lines[0], lines[-1]),
                    'adv': blocks[b]['adv'],
                    'layout': layout_rank[b],
                    'birth': birth,
                    'post_mfg': mfg_ord.get(ptr) if mfg_ord else None,
                    'ret': bool(mfg_cls.get(ptr, 0) & 1) if mfg_cls else None,
                    'moved': abs(layout_rank[b] - wpos) > 1})
    return out


def birth_compare(base_routine: dict, cand_routine: dict) -> dict:
    """Diff two compiles' block-BIRTH streams (bo): did the candidate
    spelling change the front-end GENERATION order / block set?

    The walk-order class's screener: when a candidate is walk-inert at
    the lw level (spelling_compare INERT@BURN) but the residue is a
    reversed arm walk, the birth stream shows whether the spelling even
    REACHED the tree burn's block emission (identical birth = the
    construct canonicalized before block layout; different birth with
    identical walk = the optimizer re-normalized -- a stronger INERT).

    Returns {verdict, base_sig, cand_sig, delta} where sig is the
    (class, targets) sequence with line marks where present."""
    def sig(ro):
        return [(b['class'], b['targets'], b['line'])
                for b in ro.get('blocks_born', [])]
    bs, cs = sig(base_routine), sig(cand_routine)
    if bs == cs:
        return {'verdict': 'IDENTICAL', 'base_sig': bs, 'cand_sig': cs,
                'delta': []}
    delta = [i for i, (x, y) in enumerate(zip(bs, cs)) if x != y]
    if len(bs) != len(cs):
        delta.append(min(len(bs), len(cs)))
    return {'verdict': 'DIVERGED', 'base_sig': bs, 'cand_sig': cs,
            'delta': sorted(set(delta))}


def il_birth_compare(base_routine: dict, cand_routine: dict) -> dict:
    """Diff two compiles' IL-instruction BIRTH streams (ni: NewIns exit,
    per-ins nops + SrcLine, in tree-burn EMISSION order) -- the layer
    BELOW block births (bo) and ABOVE the LdStAlloc walk (lw).

    The kind-flip-free class's screener (take_census, top_it): when a
    spelling is walk-inert (INERT@BURN) the birth diff localizes WHERE
    the burn absorbed it -- identical births = the canonicalization
    happened at tree->IL emission itself (the deepest inert); diverged
    births with an identical walk = a post-emission pass (opt/normalize)
    re-converged it.  A LIVE walk delta always shows a birth delta first;
    `delta_lines` names the source lines whose emission count changed --
    the finest-grained edit target the trace can name without burning
    the treegen dispatch itself."""
    from collections import Counter
    def sig(ro):
        return [(b['nops'], b['line']) for b in ro.get('il_born', [])]
    bs, cs = sig(base_routine), sig(cand_routine)
    if bs == cs:
        return {'verdict': 'IDENTICAL', 'n_base': len(bs), 'n_cand': len(cs),
                'delta_lines': []}
    bl = Counter(l for _, l in bs)
    cl = Counter(l for _, l in cs)
    delta_lines = sorted(set(l for l in (bl.keys() | cl.keys())
                             if bl.get(l, 0) != cl.get(l, 0)))
    return {'verdict': 'DIVERGED', 'n_base': len(bs), 'n_cand': len(cs),
            'delta_lines': delta_lines}


def compress_context(routine: dict) -> list[dict]:
    """Join the cw (CompressIns pair-scan context) records with the lw
    walk's BLOCK membership: for every real compress attempt, which chain
    block the ins lives in and what the pair-recognition kinds were.

    THE chain-separation lens (cap_land_value class): a fused attempt
    whose PS counterpart kept the split form should show, in the PS-
    faithful candidate, prevkind flipping to 0x1NN (0x14b = a BLOCK
    HEADER between the halves -- chain-separated even when the final
    LAYOUT is byte-adjacent)."""
    lw_blk = {r['ins']: r.get('blk') for r in routine.get('lw', [])}
    lc = {x['ins'] for x in routine.get('lc', [])}
    lcx = {x['ins']: x['why'] for x in routine.get('lcx', [])}
    out = []
    for r in routine.get('cw', []):
        out.append({**r,
                    'blk': lw_blk.get(r['ins']),
                    'outcome': ('fused' if r['ins'] in lc
                                else lcx.get(r['ins'], 'no-verdict'))})
    return out


# ── chain-placement lens (2026-07-10, the start_samples root cause) ─────────
#
# A conflict's CountRegMoves walk scans its ins range [first..last] in
# CHAIN order.  A CALL instruction (IL opcode 0x36) inside that span
# contributes an ABI-FIXED EAX credit -- undodgeable by any savings /
# order / decl lever.  Whether a call sits inside the span is decided
# by the front end's BLOCK CHAIN PLACEMENT (return blocks can chain
# AFTER later-source-line blocks while the byte LAYOUT keeps them
# early -- the Rule 125 chain/layout split).  Proven on
# pcsound.c::start_samples: the h-form's fail-return block chains
# after the init_ss_entires call block -> s's range spans the call ->
# +2 EAX credit -> s@EAX (85bd); the u-form's extra tail block lands
# the fail block BEFORE the call -> no credit -> s@EDX (28bd).

CALL_OP = 0x36


def _is_call(ins_row: dict) -> bool:
    """op 0x36 with a WIDE zap mask = a real CALL (returns share the
    opcode but zap little)."""
    if ins_row.get('opcode') != CALL_OP:
        return False
    return bin(ins_row.get('zap_reg') or 0).count('1') > 8


def chain_placement(routine: dict) -> dict:
    """The chain-placement report: blocks in CHAIN order with call/line
    tags, plus every allocated conflict's ins range mapped to its chain
    span and the CALL instructions it covers (each an ABI-fixed EAX
    CountRegMoves credit for any conflict whose range spans it).

    Substrate: the round-0 `iv` full-IL snapshot (il_walks[0]) --
    complete ins set in chain order with zap masks; falls back to the
    lw walk when the snapshot is absent (older images).

    Returns {'blocks': [...], 'conflicts': [...]}."""
    lw_lines = {}
    for r in routine.get('lw') or []:
        if r.get('line'):
            lw_lines.setdefault(r['ins'], r['line'])

    walks = routine.get('il_walks') or []
    blocks: list[dict] = []
    flat: list[dict] = []
    if walks:
        for b in walks[0].get('blocks', []):
            row = {'blk': b['blk'], 'lines': set(), 'calls': 0,
                   'first': len(flat)}
            for ins in b.get('ins', []):
                ins = dict(ins)
                ins['blk'] = b['blk']
                if ins['ins'] in lw_lines:
                    row['lines'].add(lw_lines[ins['ins']])
                    ins['line'] = lw_lines[ins['ins']]
                if _is_call(ins):
                    row['calls'] += 1
                flat.append(ins)
            blocks.append(row)
    else:                                    # legacy fallback: lw only
        cur = None
        for r in routine.get('lw') or []:
            if cur is None or r['blk'] != cur['blk']:
                cur = {'blk': r['blk'], 'lines': set(), 'calls': 0,
                       'first': len(flat)}
                blocks.append(cur)
            if r.get('line'):
                cur['lines'].add(r['line'])
            if r.get('opcode') == CALL_OP:
                cur['calls'] += 1
            flat.append(dict(r))

    pos = {r['ins']: i for i, r in enumerate(flat)}
    calls = [(i, r) for i, r in enumerate(flat) if _is_call(r)]

    # Rule 125 flag: a block whose min line is LOWER than a preceding
    # block's min line was chained after later-source code.
    best = -1
    for b in blocks:
        b['minline'] = min(b['lines']) if b['lines'] else None
        if b['minline'] is not None:
            if b['minline'] < best:
                b['moved_late'] = True
            best = max(best, b['minline'])

    confs = []
    for a in routine.get('alloc') or []:
        own = a.get('own_walk') or a.get('ins_walk') or []
        spanned = []
        known = bool(own)
        if own:
            # GROUND TRUTH: the conflict's actual CountRegMoves scan
            # (chain order AT ALLOCATION TIME).  Any op with a physical
            # register in it is a credit source; op54 with a physical
            # result = a CALL (ABI EAX) or the far-return pair.
            for w in own:
                phys = [w.get('result_reg') or w.get('res_reg') or 0,
                        w.get('op0_reg') or 0, w.get('op1_reg') or 0]
                if w.get('opcode') == CALL_OP and any(phys):
                    spanned.append({'ins': w['ins'],
                                    'line': lw_lines.get(w['ins'], 0),
                                    'blk': '?', 'phys': [hex(x) for x in
                                                         phys if x]})
        else:                              # legacy: round-0 span estimate
            first, last = a.get('first'), a.get('last')
            p0, p1 = pos.get(first), pos.get(last)
            known = p0 is not None and p1 is not None and p1 >= p0
            if known:
                spanned = [
                    {'ins': r['ins'], 'line': r.get('line') or 0,
                     'blk': r['blk']}
                    for i, r in calls if p0 < i < p1]
        p0 = pos.get(a.get('first'))
        p1 = pos.get(a.get('last'))
        confs.append({
            'conf': a.get('conf'),
            'name': a.get('var') or a.get('name'),
            'savings': a.get('savings'), 'reg': a.get('reg_name'),
            'span': (p0, p1), 'span_known': known,
            'scan_len': len(own),
            'calls_in_range': spanned})
    return {'blocks': blocks, 'conflicts': confs}
