"""Unified caching-mismatch hint: de-invent a temp *or* add an intermediate.

Both directions are the SAME question asked from opposite sides: **does the
source's caching of a global match PS's?**  PS.EXE was compiled
``BlockByBlock=TRUE`` (low-memory mode), so its value pool keeps a loaded
global in a register across plain stores but a CALL kills the copy -- the
next use RELOADS from memory.  A named local caching the global instead
survives calls in a callee-save (one load + push/pop).  So:

* **DE-INVENT** -- the source has a local ``v`` mirroring a global ``G``
  (``v = G`` or ``G = v``) and reads ``v`` afterwards, but PS **re-reads
  ``G``** at each call/block boundary.  Delete the local, read ``G``
  directly (``edit_format_buffer``'s ``key_ascii_val`` 207->0;
  ``one_letter``'s ``data_ptr`` re-read 219->195).

* **ADD an intermediate** -- the source reads a global ``G`` directly many
  times, but PS **caches** it in one callee-save register across the calls.
  Introduce ``T v = G;`` and use ``v`` (Rule 129 inverse).

This module fuses two signals that neither the pure-AST nor the pure-disasm
view can resolve alone:

1. **AST** (``_build_src_func_cache`` -> pycparser ``FuncDef``): enumerates
   the *candidates* and -- crucially -- NAMES the exact local + source line,
   which the disasm-only ``reread_hints`` could not.  A local mirroring a
   global is a trivial structural pattern; a global read >=N times directly
   is too.

2. **PS-side per-address reload census** (``_ps_loads_by_addr``, the
   reliable half -- RC operands are pre-fixup so only the PS side pairs per
   address): the *direction*.  The same AST shape (``v = G``) is correct
   when PS caches and wrong when PS re-reads -- only PS's bytes
   disambiguate.  ``G``'s data-symbol ``offset`` (== the disasm operand
   address, ``key_ascii`` -> ``0x3cccc``) joins the two.

Subsumes the old totals-only Rule-129 ``reread`` hint: when no AST candidate
resolves but the load *totals* still diverge >=4, it falls back to the
totals verdict so coverage never regresses.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pycparser import c_ast

# `mov/movsx/movzx <reg>, [<fixed-addr>]` -- a register load from a fixed
# (global) address.  PS operands are post-fixup absolute; RC operands are
# pre-fixup (print as [0]/small) so only the PS side pairs per-address.
_LOAD_RE = re.compile(
    r"(?:movsx|movzx|mov) \w+, (?:byte|word|dword)? ?ptr? ?"
    r"\[(0x[0-9a-fA-F]+|\d+)\]$")

# Tunables.  A global must be reloaded this many times on the PS side for a
# de-invent to be worth it (>=3 = at least two call/block boundaries past the
# first load), and the load totals must diverge this much for the totals
# fallback / add-intermediate direction.
_DEINVENT_MIN_PS_RELOADS = 3
_MIN_READS_TO_CACHE = 3
_TOTALS_DELTA = 4

_DATA_OFFSETS: dict[str, int] | None = None


def _data_offsets(symbols_json: str = "data/out/symbols.json") -> dict[str, int]:
    """``{symbol_name: fixed_address}`` for every data symbol (both the demangled
    ``name`` and the raw ``_name``).  The ``offset`` field is exactly the address
    the disassembler prints in a ``[0x...]`` operand."""
    global _DATA_OFFSETS
    if _DATA_OFFSETS is None:
        _DATA_OFFSETS = {}
        try:
            blob = json.loads(Path(symbols_json).read_text())
            syms = blob["symbols"] if isinstance(blob, dict) else blob
            for s in syms:
                if not s.get("is_data"):
                    continue
                off = s.get("offset")
                if off is None:
                    continue
                for key in (s.get("name"), s.get("raw_name")):
                    if key:
                        _DATA_OFFSETS.setdefault(key, off)
        except Exception:
            _DATA_OFFSETS = {}
    return _DATA_OFFSETS


def _ps_loads_by_addr(insns) -> Counter:
    """``{address_int: load_count}`` over fixed-address register loads."""
    out: Counter = Counter()
    for i in insns:
        m = _LOAD_RE.match(i[3])
        if m:
            out[int(m.group(1), 16)] += 1
    return out


def _total_fixed_loads(insns) -> int:
    return sum(1 for i in insns if _LOAD_RE.search(i[3]))


def _rhs_is_derefed(node) -> bool:
    """True iff reaching the root ID requires walking through a StructRef or
    ArrayRef (``G->field``, ``arr[i]``).  store-mirror's "faithful mirror"
    semantics requires the rhs be a *bare ID* -- a struct-field read isn't a
    snapshot of the base symbol."""
    seen = 0
    while seen < 16:
        seen += 1
        if isinstance(node, c_ast.Cast):
            node = node.expr
        elif isinstance(node, c_ast.UnaryOp) and node.op in ("*", "&"):
            node = node.expr
        elif isinstance(node, (c_ast.StructRef, c_ast.ArrayRef)):
            return True
        else:
            break
    return False


def _root_symbol(node) -> str | None:
    """Root identifier of a *pure* lvalue/global-read expression: peel casts,
    ``*``/``&``, and struct/array refs, but NOT binary ops (``a & 0xff`` is an
    arithmetic value, not a cache of one symbol)."""
    seen = 0
    while seen < 16:
        seen += 1
        if isinstance(node, c_ast.Cast):
            node = node.expr
        elif isinstance(node, c_ast.UnaryOp) and node.op in ("*", "&"):
            node = node.expr
        elif isinstance(node, c_ast.StructRef):
            node = node.name
        elif isinstance(node, c_ast.ArrayRef):
            node = node.name
        else:
            break
    return node.name if isinstance(node, c_ast.ID) else None


class _Collector(c_ast.NodeVisitor):
    """One pass: record (lhs_root, rhs_root, line) binding events and count
    rvalue reads per identifier."""

    def __init__(self) -> None:
        # binds: (lhs_root, rhs_root, line, rhs_is_derefed).  The last flag
        # is True when the rhs walks through StructRef/ArrayRef before reaching
        # its root ID -- i.e. `G->field` or `arr[i]`, not a bare ID `G`.
        # store-mirror needs this to reject struct-field reads like
        # `figure_a = cell->figure` (FP on place3_sprite).
        self.binds: list[tuple[str | None, str | None, int, bool]] = []
        self.locals: set[str] = set()
        self.reads: Counter = Counter()
        self.assigns: Counter = Counter()   # all writes (=, +=, ...) per root
        self.mods: Counter = Counter()      # ++/-- per root

    def visit_Decl(self, node) -> None:
        if node.name:
            self.locals.add(node.name)
        if getattr(node, "init", None) is not None:
            line = getattr(getattr(node, "coord", None), "line", 0) or 0
            self.binds.append((node.name, _root_symbol(node.init), line,
                               _rhs_is_derefed(node.init)))
            self.assigns[node.name] += 1
            self.visit(node.init)
        # do not recurse the type/name as reads

    def visit_Assignment(self, node) -> None:
        line = getattr(getattr(node, "coord", None), "line", 0) or 0
        lroot = _root_symbol(node.lvalue)
        if lroot:
            self.assigns[lroot] += 1
        if node.op == "=":
            self.binds.append((lroot, _root_symbol(node.rvalue), line,
                               _rhs_is_derefed(node.rvalue)))
            # the bare ID lvalue of '=' is a pure def -- don't count as read,
            # but a struct/array lvalue still reads its index/base, so recurse
            # those (not a plain ID).
            if not isinstance(node.lvalue, c_ast.ID):
                self.visit(node.lvalue)
        else:
            # compound assignment (+=, |=, ...) reads the lvalue too
            self.visit(node.lvalue)
        self.visit(node.rvalue)

    def visit_UnaryOp(self, node) -> None:
        if node.op in ("p++", "p--", "++", "--"):
            root = _root_symbol(node.expr)
            if root:
                self.mods[root] += 1
        self.generic_visit(node)

    def visit_ID(self, node) -> None:
        if node.name:
            self.reads[node.name] += 1


@dataclass
class DeinventHint:
    kind: str                    # "deinvent" | "add" | "totals"
    local: str | None = None
    glob: str | None = None
    line: int = 0
    ps_reloads: int = 0
    reads: int = 0
    ps_total: int = 0
    rc_total: int = 0
    extra: list = field(default_factory=list)


# ---- AST-only over-decompile-mirror helpers (corpus signal, 2026-06-25) ---
#
# A *single-assignment* local that mirrors a global / global-field / global-
# subscript expression with NEITHER (a) the same memory written between the
# assignment and the last read NOR (b) a function call in that window is
# *often* an over-decompile artifact: PS source either inlined the global
# access or never named it.
#
# Corpus signal across 1449 fns: EXACT 1.8% / DIFFING 9.6% of functions
# carry such a mirror -- a 5x bias.  The mechanism (proven by the cgex
# experiment `docs/codegen-experiments/named-local-tiebreak.py`) is a
# structural rank change in the regalloc queue, not a tie-break:
#
#     #define _FrontEndTmp( op ) ( !( (op)->t.temp_flags & CONST_TEMP ) && \
#                                    (op)->v.symbol != NULL )
#                  -- vendor/open-watcom/bld/cg/h/name.h:209
#
# A named C local has a non-null FE symbol pointer; an inline / CSE / index
# temp has `symbol == NULL`.  Watcom does NOT auto-CSE N inline reads of
# the same global into a single high-savings temp within a basic block
# under PS's BlockByBlock=TRUE.  Each inline read emits a SEPARATE sav=2
# anonymous-temp conflict.  Naming the cache (`int x = G; x×N`)
# CONSOLIDATES them into ONE FE conflict at sav=N+1 at the TOP of the
# ConfBefore queue.  See regalloc-model.md §2a and
# observed-source-style.md §13.
#
# These helpers expose the AST candidate list; no automatic hint is fired
# from them because the FP rate against PS-faithful named locals is high
# (sf08_withdraw `unit_idx`/`slot`, new_army_route_point `wp_x`/`wp_y`,
# get_region_revolt_points `x`/`y` are all real).  The byte-oracle load-
# census divergence (the strong `deinvent` arm above) is the necessary
# classifier for automatic verdicts.  Manual-review callers (e.g. a future
# `c2 mirror-audit` command) can use these helpers directly.


_MAX_SPEC = 4   # cap on candidates returned by the manual-review helpers


def _contains_call(node) -> bool:
    if isinstance(node, c_ast.FuncCall):
        return True
    for _, c in (node.children() if hasattr(node, "children") else []):
        if _contains_call(c):
            return True
    return False


def _struct_eq(a, b) -> bool:
    """Structural equality of two AST expressions, ignoring coord/casts.
    Conservative: returns True when both sides are STRUCTURALLY identical
    (same root id, same struct/array path, same constant subscripts).
    Used for the (a) gate -- detecting writes to the SAME memory the mirror
    captured."""
    if isinstance(a, c_ast.Cast):
        return _struct_eq(a.expr, b)
    if isinstance(b, c_ast.Cast):
        return _struct_eq(a, b.expr)
    if type(a) is not type(b):
        return False
    if isinstance(a, c_ast.ID):
        return a.name == b.name
    if isinstance(a, c_ast.Constant):
        return a.type == b.type and a.value == b.value
    if isinstance(a, c_ast.StructRef):
        return (a.type == b.type
                and getattr(a.field, "name", None) == getattr(b.field, "name", None)
                and _struct_eq(a.name, b.name))
    if isinstance(a, c_ast.ArrayRef):
        return _struct_eq(a.name, b.name) and _struct_eq(a.subscript, b.subscript)
    if isinstance(a, c_ast.UnaryOp):
        return a.op == b.op and _struct_eq(a.expr, b.expr)
    if isinstance(a, c_ast.BinaryOp):
        return (a.op == b.op and _struct_eq(a.left, b.left)
                and _struct_eq(a.right, b.right))
    return False


def _contains_write_to(node, rhs_template) -> bool:
    """True if `node` contains an assignment / ++ / -- whose lvalue is
    structurally == `rhs_template` (the mirror's RHS)."""
    if isinstance(node, c_ast.Assignment):
        if _struct_eq(node.lvalue, rhs_template):
            return True
    if isinstance(node, c_ast.UnaryOp) and node.op in ("++", "--", "p++", "p--"):
        if _struct_eq(node.expr, rhs_template):
            return True
    for _, c in (node.children() if hasattr(node, "children") else []):
        if _contains_write_to(c, rhs_template):
            return True
    return False


def _contains_id_read(node, name: str, in_lhs: bool = False) -> bool:
    if isinstance(node, c_ast.Assignment):
        if node.op == "=" and isinstance(node.lvalue, c_ast.ID) and node.lvalue.name == name:
            return _contains_id_read(node.rvalue, name)
        for _, c in node.children():
            if _contains_id_read(c, name):
                return True
        return False
    if isinstance(node, c_ast.UnaryOp) and node.op in ("++", "--", "p++", "p--"):
        if isinstance(node.expr, c_ast.ID) and node.expr.name == name:
            return True
    if isinstance(node, c_ast.ID) and node.name == name and not in_lhs:
        return True
    for _, c in (node.children() if hasattr(node, "children") else []):
        if _contains_id_read(c, name):
            return True
    return False


def _unjustified_ast_mirrors(func_ast, offsets, param_names) -> list:
    """Return [(local, glob_expr_text, glob_root, line), ...] for AST mirrors
    that pass the (a)+(b) test: single-assignment local of a global root,
    with neither a function call nor a write to the same memory between the
    assignment and any read of the local."""
    if func_ast is None:
        return []
    try:
        body = func_ast.body
        if body is None or body.block_items is None:
            return []
    except AttributeError:
        return []
    # Local declarations declared in the function-scope block (C89: top of
    # function).  We only consider locals that look like a simple scalar.
    local_names: set[str] = set(param_names)
    for item in body.block_items:
        if isinstance(item, c_ast.Decl) and getattr(item, "name", None):
            local_names.add(item.name)
    # Pre-pass: assignment counts (so we can require single-assign).
    write_counts: Counter = Counter()
    mod_counts: Counter = Counter()
    for item in body.block_items:
        for sub in _walk(item):
            if isinstance(sub, c_ast.Assignment):
                root = _root_symbol(sub.lvalue)
                if root:
                    write_counts[root] += 1
            elif (isinstance(sub, c_ast.UnaryOp)
                  and sub.op in ("++", "--", "p++", "p--")):
                root = _root_symbol(sub.expr)
                if root:
                    mod_counts[root] += 1
    block = body.block_items
    out: list = []
    seen_local: set[str] = set()
    try:
        gen = _get_generator()
    except NameError:
        gen = None
    for i, item in enumerate(block):
        if not isinstance(item, c_ast.Assignment) or item.op != "=":
            continue
        if not isinstance(item.lvalue, c_ast.ID):
            continue
        local = item.lvalue.name
        if local in seen_local or local not in local_names or local in param_names:
            continue
        if write_counts.get(local, 0) != 1 or mod_counts.get(local, 0) != 0:
            continue
        rhs = item.rvalue
        # Mirror must root at a known global symbol that isn't shadowed.
        rhs_root = _root_symbol(rhs)
        if rhs_root is None or rhs_root not in offsets or rhs_root in local_names:
            continue
        # Walk forward statements: find calls / writes to the RHS expr / reads
        # of the local.
        had_call = False
        had_write = False
        had_read = False
        for j in range(i + 1, len(block)):
            nxt = block[j]
            if _contains_call(nxt):
                had_call = True
                break
            if _contains_write_to(nxt, rhs):
                had_write = True
                break
            if _contains_id_read(nxt, local):
                had_read = True
                # do not break -- keep scanning for an LATER call/write that
                # might justify the mirror.  But finding a clean read first
                # is enough to start counting.
        if had_read and not had_call and not had_write:
            line = getattr(getattr(item, "coord", None), "line", 0) or 0
            seen_local.add(local)
            rhs_text = ""
            if gen is not None:
                try:
                    rhs_text = gen.visit(rhs).strip()
                except Exception:
                    rhs_text = rhs_root
            else:
                rhs_text = rhs_root
            out.append((local, rhs_text, rhs_root, line))
            if len(out) >= _MAX_SPEC:
                break
    return out


def _walk(node):
    """Yield node and all descendants (pre-order)."""
    yield node
    for _, c in (node.children() if hasattr(node, "children") else []):
        yield from _walk(c)


# Lazy cached c_generator (pycparser) -- only loaded when needed.
_GEN = None


def _get_generator():
    global _GEN
    if _GEN is None:
        from pycparser import c_generator
        _GEN = c_generator.CGenerator()
    return _GEN


def _param_names(func_ast) -> set[str]:
    """Names declared in the function's parameter list.  These shadow any
    same-named global INSIDE the function -- the detector must add them to
    col.locals or a parameter like `int count` (with a sibling global `count`)
    will be miscounted as a global read.  Bug example: `evolve_a_building(int
    count, ...)` flagged `count` as 'add a local for the global count'."""
    out: set[str] = set()
    try:
        params = func_ast.decl.type.args.params
    except Exception:
        return out
    for d in params or []:
        nm = getattr(d, "name", None)
        if nm:
            out.add(nm)
    return out


def detect(func_ast, ps_insns, rc_insns,
           symbols_json: str = "data/out/symbols.json") -> DeinventHint | None:
    ps_total = _total_fixed_loads(ps_insns)
    rc_total = _total_fixed_loads(rc_insns)
    offsets = _data_offsets(symbols_json)
    ps_loads = _ps_loads_by_addr(ps_insns)

    col = None
    if func_ast is not None:
        try:
            col = _Collector()
            # Parameters shadow same-named globals -- seed col.locals so a
            # parameter 'count' isn't matched against the global 'count'.
            col.locals.update(_param_names(func_ast))
            col.visit(func_ast.body)
        except Exception:
            col = None

    # ---- direction 1: DE-INVENT -------------------------------------------
    # A local v mirrors a global G (v = G or G = v) and v is read again, but
    # PS reloads G's address >= threshold.  Strongest (most-reloaded) wins.
    # Gate on ps_total > rc_total too: RC must actually reload globals FEWER
    # times than PS (i.e. RC is caching where PS re-reads).  For a byte-exact
    # function the totals are equal, so the cache is byte-neutral and the
    # hint correctly stays silent.
    best: DeinventHint | None = None
    if col is not None and ps_total - rc_total >= 2:
        # Record which binds had a deref'd rhs root (`G->field`, `arr[i]`):
        # those are NOT faithful mirrors of `G`, so the store-mirror direction
        # must reject them.  False-positive example: `figure_a = cell->figure`
        # peeled to `cell` -- but figure_a is reading cell's `figure` field,
        # not snapshotting `cell` itself.
        for lhs, rhs, line, rhs_derefed in col.binds:
            local = glob = None
            if (lhs in col.locals and rhs in offsets and rhs not in col.locals
                    and col.assigns.get(lhs, 0) == 1 and col.mods.get(lhs, 0) == 0):
                # v = G, with v single-assigned and never ++/-- -- a pure
                # read-only cache of the global (key_ascii_val class).
                local, glob = lhs, rhs        # load-cache
            elif (rhs in col.locals and lhs in offsets and lhs not in col.locals
                    and col.assigns.get(lhs, 0) == 1 and not rhs_derefed):
                # G = v, with the GLOBAL written exactly once AND `v` a bare
                # ID (no struct/array deref) -- a faithful single-write mirror
                # (one_letter's data_ptr), not a struct-field read (place3_
                # sprite's `figure_a = cell->figure`) nor a reused scratch
                # global (x_is, written many times -> rejected).
                local, glob = rhs, lhs        # store-mirror
            if local is None:
                continue
            reloads = ps_loads.get(offsets[glob], 0)
            reads = col.reads.get(local, 0)
            if reloads >= _DEINVENT_MIN_PS_RELOADS and reads >= 2:
                cand = DeinventHint("deinvent", local, glob, line,
                                    reloads, reads, ps_total, rc_total)
                if best is None or cand.ps_reloads > best.ps_reloads:
                    best = cand
    if best is not None:
        return best

    # ---- direction 2: ADD an intermediate ---------------------------------
    # RC reloads globals materially more than PS (PS caches more).  Name the
    # most directly-read global that ISN'T already mirrored to a local.
    if rc_total - ps_total >= _TOTALS_DELTA and col is not None:
        mirrored = {g for _, g, _, _ in col.binds if g in offsets} | \
                   {l for l, _, _, _ in col.binds if l in offsets}
        cands = [
            (col.reads[g], g)
            for g in offsets
            if g not in col.locals
            and col.reads.get(g, 0) >= _MIN_READS_TO_CACHE
            and g not in mirrored
        ]
        if cands:
            cands.sort(reverse=True)
            n, g = cands[0]
            return DeinventHint("add", None, g, 0, ps_loads.get(offsets[g], 0),
                                n, ps_total, rc_total, extra=cands[1:3])

    # ---- fallback: totals-only (subsumes the old Rule-129 reread hint) -----
    if ps_total - rc_total >= _TOTALS_DELTA and ps_loads and \
            ps_loads.most_common(1)[0][1] >= 3:
        return DeinventHint("totals", None, None, 0, 0, 0, ps_total, rc_total)
    if rc_total - ps_total >= _TOTALS_DELTA:
        return DeinventHint("totals", None, None, 0, 0, 0, ps_total, rc_total,
                            extra=["inverse"])
    # NB: a corpus-wide AST-only speculative arm ("single-assign mirror with
    # no call OR same-memory write between assign and last read") was tested
    # 2026-06-25.  It exposes the `_FrontEndTmp` structural rank change
    # documented in observed-source-style.md §13 (5x bias toward diffing;
    # mechanism proven by `docs/codegen-experiments/named-local-tiebreak.py`
    # -- N inline reads = N sav=2 anon leaves, vs ONE sav=N+1 FE temp from
    # `int x = G`).  But the false-positive rate against byte-exact PS-
    # faithful mirrors is near 100% (sf08_withdraw `unit_idx`/`slot`,
    # new_army_route_point `wp_x`/`wp_y`, ... all byte-exact mirrors that
    # LOOK over-decompiled to the AST scan).  The byte oracle classifier
    # here is the load-census divergence -- without it, the AST signal is
    # too weak to ship as an automatic hint.  The helpers
    # (`_unjustified_ast_mirrors` etc.) are exposed for callers who want a
    # *manual-review* candidate list (e.g. an audit command), not a verdict.


def render(h: DeinventHint) -> str:
    if h.kind == "deinvent":
        return (
            f"De-invent (Rule 129 / \u00a710): the local `{h.local}` "
            f"(line {h.line}) mirrors the global `{h.glob}`, but PS RE-READS "
            f"`{h.glob}` {h.ps_reloads}\u00d7 (one reload per call/block "
            f"boundary; you cache it and read `{h.local}` {h.reads}\u00d7).  "
            f"PS was compiled BlockByBlock=TRUE -- it does not keep the "
            f"global live across calls.  LEVER: DELETE `{h.local}` and read "
            f"`{h.glob}` directly at each use (an extra callee-save usually "
            f"disappears with it).  Caveat (Hard Rule #3): may regress alone "
            f"if a sibling shape is still wrong -- read the asm.")
    if h.kind == "add":
        more = ""
        if h.extra:
            more = "  also: " + ", ".join(f"`{g}`\u00d7{n}" for n, g in h.extra)
        return (
            f"Add an intermediate (Rule 129 inverse): the source reads the "
            f"global `{h.glob}` {h.reads}\u00d7 directly (PS loads it "
            f"{h.ps_reloads}\u00d7), and RC reloads globals {h.rc_total}\u00d7 "
            f"vs PS {h.ps_total}\u00d7 overall -- PS caches in a callee-save "
            f"across the calls.  LEVER: introduce `T {h.glob[:1]} = "
            f"{h.glob};` and use the local at each read.{more}")
    # totals fallback
    if "inverse" in h.extra:
        return (
            f"Global re-read (Rule 129, inverse): RC reloads fixed globals "
            f"{h.rc_total}\u00d7 vs PS {h.ps_total}\u00d7 -- PS caches a value "
            f"in a callee-save local.  ADD a caching local and use it instead "
            f"of the repeated global reads.  (No single AST candidate "
            f"resolved -- inspect the per-line view for the hot global.)")
    return (
        f"Global re-read (Rule 129): PS reloads fixed globals {h.ps_total}\u00d7 "
        f"vs RC {h.rc_total}\u00d7 -- the decomp invented a caching local PS "
        f"never made.  DELETE the caching local and read the global directly "
        f"at each use.  (No single AST candidate resolved -- inspect the "
        f"per-line view for the hot global.)")
