"""Named-intermediate reload-vs-hold marker (Rule 116).

PS.EXE almost never names an intermediate that holds a **memory-rooted** value (a
global read, an array-element / struct-field read).  It inlines the expression
and lets the compiler decide: across a call the home is reloaded (the call kills
the aliasable global, `cse.c::ReDefinedBy`); with no kill between uses the inline
reads CSE into one register.  A named local `int t = G;` instead **severs the
value from its home** and forces a HOLD (callee-save reg + push, or a private
stack slot) — a different stream.

This detector flags the **actionable** direction: our source declares
`int t = <global/element>;` (a hold) where PS RELOADS the home (≥2 static loads
of the same global).  The lever is to delete the local and inline the
expression.  Causally proven: adding `int pass = pop_income_pass_count;` to the
byte-exact inline `running_pop_tax` breaks it (0 → 22 b); reverting is exact.

The inverse ("PS held a temp we inlined → add one") is **deliberately not
flagged**: empirically a single PS load of a global is dominated by confounds
that a scalar temp does not fix — a compare-chain `if (g==0) … else if (g==1)`
CSEs to one load in *both* builds (`helping`'s `map_mode`), a global in subscript
position is a held *scaled index* (Rule 63/64, not a scalar), and reads in
mutually-exclusive branches load once per path with no reload.  In causal tests
the "add a temp" rewrite was a no-op or actively regressed (`f15_barb_elephant`
7→7 b, `flag_mode_action` 150→198 b).  So "PS loads once" is not a reliable
add-a-temp signal; the inverse needs a control-flow + cross-build analysis we do
not have, and is left to manual inspection.

Distinct from Rule 111 (`spill_hints`): that is the *negative*-triage case (PS
re-reads a global more than we do with **no removable source local** — a
register-pressure spill we cannot reproduce).  Rule 116 fires only on a concrete
source lever: a named local to delete.

Cross-stream note: a memory operand's displacement bytes are link-relative and
differ between PS and RC, so we never match operands across streams.  The hint is
driven by the *source* (which globals are held in a named local) and confirmed on
the *PS* stream alone (does PS reload that global?).  Globals are resolved by
name → data address via ``symbols.json``; element/field temps are flagged on
source shape with ``medium`` confidence (no PS address to confirm).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pycparser import c_ast

from c2.commands.c_source import parse_c

_ROOT = Path(__file__).resolve().parents[2]

# PS must reload the global at least this many times (PS clearly inlined).
_MIN_PS_RELOADS = 2


@dataclass
class ReloadHint:
    local: str              # the named local to delete
    source: str             # global name
    kind: str               # "global" (only confirmed kind)
    uses: int               # source read/use count of the local
    ps_loads: int           # PS static loads of the global home
    confidence: str         # "high"


# ── symbol table (global name → data address) ────────────────────────────────
_SYMS: Optional[dict[str, int]] = None


def _global_addrs() -> dict[str, int]:
    global _SYMS
    if _SYMS is None:
        _SYMS = {}
        try:
            d = json.loads((_ROOT / "data" / "out" / "symbols.json").read_text())
            for s in d.get("symbols", []):
                if s.get("is_data") and "offset" in s:
                    _SYMS[s["name"]] = int(s["offset"])
        except Exception:
            _SYMS = {}
    return _SYMS


# ── source analysis ──────────────────────────────────────────────────────────
@dataclass
class _Temp:
    local: str
    kind: str               # "global"
    gname: Optional[str]


class _Temps(c_ast.NodeVisitor):
    """Find named scalar locals initialised from a bare global read (a HOLD,
    `int t = last_icon_over;`), with their downstream use count.

    Only bare-global caches are handled: their home is a single data address we
    can confirm against the PS stream.  Element/field caches (`int t =
    rows[i].hp;`) have no single address to confirm a reload against, so they
    are NOT flagged here — that family is the Rule 63/73/74 pointer/row cache,
    covered by `c2 row-caches` / `global_cache_hints`.  Arithmetic-of-locals
    temps (no memory home → byte-neutral) are likewise excluded.
    """

    def __init__(self, globals_: set[str]) -> None:
        self._globals = globals_
        self.temps: dict[str, _Temp] = {}
        self.uses: dict[str, int] = {}
        # DISTINCT locals caching each global, via decl-init OR assignment
        # (`int icon; icon = g;`).  A global held in N locals = N intended
        # holds; PS loading it N times is N holds, not a reload of one value.
        self.global_cache_locals: dict[str, set[str]] = {}
        # INLINE reads of a global (read directly, not through a cache local).
        # Our build loads the home once per inline read, so the source's own
        # max load count for G is n_caches + inline_reads.
        self.global_inline_reads: dict[str, int] = {}
        self._cache_rhs_ids: set[int] = set()   # the `g` in `int t = g;`
        self._skip_ids: set[int] = set()        # write lvalues (not reads)

    def _record_cache(self, local: str, gname: str, rhs) -> None:
        if local in self._globals:
            return   # global-to-global store, not a held local
        self.global_cache_locals.setdefault(gname, set()).add(local)
        self._cache_rhs_ids.add(id(rhs))   # don't count it as an inline read

    def visit_Decl(self, node: c_ast.Decl) -> None:
        if isinstance(node.type, c_ast.TypeDecl) and node.init is not None:
            init = node.init
            if isinstance(init, c_ast.ID):
                self.temps[node.name] = _Temp(node.name, "global", init.name)
                self._record_cache(node.name, init.name, init)
        self.generic_visit(node)

    def visit_Assignment(self, node: c_ast.Assignment) -> None:
        # `local = global;` is a hold of that global, even though it is not the
        # temp we flag (the temp must be a decl-init we can delete).
        if (node.op == "=" and isinstance(node.lvalue, c_ast.ID)
                and isinstance(node.rvalue, c_ast.ID)
                and node.rvalue.name in self._globals):
            self._record_cache(node.lvalue.name, node.rvalue.name, node.rvalue)
            self._skip_ids.add(id(node.lvalue))   # lvalue is a write, not a read
        self.generic_visit(node)

    def visit_ID(self, node: c_ast.ID) -> None:
        self.uses[node.name] = self.uses.get(node.name, 0) + 1
        if (node.name in self._globals and id(node) not in self._cache_rhs_ids
                and id(node) not in self._skip_ids):
            self.global_inline_reads[node.name] = \
                self.global_inline_reads.get(node.name, 0) + 1


_FUNC_MAP: Optional[dict[str, c_ast.FuncDef]] = None


def _func_map() -> dict[str, c_ast.FuncDef]:
    """name → FuncDef for every decomp/src/*.c function (parsed once, cached)."""
    global _FUNC_MAP
    if _FUNC_MAP is None:
        _FUNC_MAP = {}
        for path in sorted((_ROOT / "decomp" / "src").glob("*.c")):
            try:
                ast = parse_c(path.read_text(), str(path))
            except Exception:
                continue
            for node in ast.ext:
                if isinstance(node, c_ast.FuncDef):
                    _FUNC_MAP.setdefault(node.decl.name, node)
    return _FUNC_MAP


def clear_cache() -> None:
    global _FUNC_MAP
    _FUNC_MAP = None


# ── PS-asm confirmation ──────────────────────────────────────────────────────
def _ps_global_loads(addr: int, insns) -> int:
    """Count source-operand reads of the direct global ``[addr]`` in a stream."""
    home = f"[0x{addr:x}]"
    n = 0
    for ins in insns:
        asm = ins[3] if not isinstance(ins, str) else ins
        parts = asm.split(None, 1)
        if len(parts) < 2:
            continue
        ops = parts[1]
        if home in ops and not ops.lstrip().startswith(home):
            n += 1
    return n


# ── public API ───────────────────────────────────────────────────────────────
def detect_reload_hints(name: str, orig_insns, *, has_body_diff: bool = True
                        ) -> list[ReloadHint]:
    """Flag named memory-rooted intermediates that PS inlines (reloads).

    ``orig_insns`` is the PS stream (``(addr, size, raw, asm)`` tuples).  Only
    fires for diffing functions.  Every hint is PS-confirmed: PS must load the
    global home more than the source's own max load count AND reach the local's
    use count (PS reloaded at every use = it fully inlined the value).
    """
    if not has_body_diff:
        return []
    fd = _func_map().get(name)
    if fd is None:
        return []
    addrs = _global_addrs()
    v = _Temps(set(addrs.keys()))
    v.visit(fd.body)
    hints: list[ReloadHint] = []
    for t in v.temps.values():
        uses = v.uses.get(t.local, 0)
        if uses < 2:                       # single use is byte-neutral, no marker
            continue
        if t.kind == "global":
            addr = addrs.get(t.gname or "")
            if addr is None:
                continue
            loads = _ps_global_loads(addr, orig_insns)
            if loads < _MIN_PS_RELOADS:
                continue   # PS also holds it → the temp is faithful, don't flag
            # PS must load the home MORE than the source's OWN maximal load
            # count = (distinct caches) + (inline reads of the same global).
            #   * equal cache counts => PS holds one intermediate per cache
            #     (`icon`+`after` => edx/edi), not a reload.
            #   * a source that mixes a cache with inline reads of the SAME
            #     global (act_correct_map: `mm` + 5 inline `map_mode`) already
            #     loads it n_caches+inline times, matching PS -- no divergence.
            g = t.gname or ""
            n_caches = len(v.global_cache_locals.get(g, set()))
            source_loads = max(n_caches, 1) + v.global_inline_reads.get(g, 0)
            if loads <= source_loads:
                continue
            # PS must reload at (essentially) EVERY use, i.e. it fully inlined
            # the value.  A held value PS reloads only a few times across calls
            # (`get_query_info`: ptr used 18x, PS loads 3x) is NOT a DROP target
            # -- inlining its 18 uses would emit 18 loads.  Require ps_loads to
            # reach the local's use count.
            if loads < uses:
                continue
            hints.append(ReloadHint(t.local, t.gname or "?", "global",
                                    uses, loads, "high"))
    hints.sort(key=lambda h: -h.uses)
    return hints


def render(hints: list[ReloadHint]) -> str:
    """One-line `decomp-verify -v` hint (the rule label is printed separately)."""
    if not hints:
        return ""
    h = hints[0]
    extra = f" (+{len(hints) - 1} more)" if len(hints) > 1 else ""
    return (
        f"`int {h.local} = {h.source};` (used {h.uses}x) holds a global PS "
        f"RELOADS {h.ps_loads}x at every use (it inlined the value, no temp). "
        f"Delete the local and inline `{h.source}` at each use to drop the "
        f"hold/push{extra}."
    )


def to_json(hints: list[ReloadHint]) -> Optional[list[dict]]:
    if not hints:
        return None
    return [
        {
            "local": h.local,
            "source": h.source,
            "kind": h.kind,
            "uses": h.uses,
            "ps_loads": h.ps_loads,
            "confidence": h.confidence,
        }
        for h in hints
    ]
