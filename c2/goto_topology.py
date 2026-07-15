"""Goto-topology census — the /Od jmp-topology witness for goto recovery.

Empirical basis: ``docs/msvc-od-goto-signal.md`` (MSVC 4.0 /Od + Watcom
10.0a probes, 2026-07-03).

**MSVC /Od (CAESAR2.EXE) preserves gotos losslessly.**  Every source
``goto`` survives as its own near ``jmp`` (E9): no fusion (``if (c)
goto L`` = inverted jcc *over* the jmp), no threading, no elimination.
Structured statements emit jmps only at fixed template positions.
Therefore comparing the INTERNAL-JMP TOPOLOGY of CAESAR2.EXE's copy of
a function against our own MSVC /Od compile of the recovered source is
a *differential census of jump-statement structure*:

* a **funnel** (>= 2 unconditional jmps converging on one
  non-epilogue target) present in WIN but absent in ours = a shared
  label our source is missing (`goto` ladder);
* the reverse = a goto/label we invented.

The differential design absorbs the structured-jmp false positives
(switch-break funnels, if/else join jmps): those appear identically on
BOTH sides when the source shape is right.

**Watcom 10.0a -d1 (PS.EXE) erases most goto signals** — it fuses
``if (c) goto L`` into a single jcc, deletes degenerate gotos, and
emits no LINNUM record for a label, so goto-to-end == ``return``,
goto-past-loop == ``break`` etc. are byte- AND line-identical.  What
survives is NON-STRUCTURED topology only: a **detached block**
(preceded by ``ret``/``jmp``, i.e. unreachable by fall-through, and not
a pure shared epilogue) with >= 2 predecessors — the cleanup-funnel
shape.  :func:`ps_goto_evidence` reports those as corroboration.

Surfaces: ``c2 diagnose`` (the ``win-goto`` line) and
``c2 win-census --goto`` (per-function detail + corpus scan).
"""
from __future__ import annotations

import bisect
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import capstone

from c2.win_bytes import (
    SRC_DIR,
    CompiledTU,
    WinImage,
    compile_tu,
    disasm_norm,
    load_win_image,
    tu_of,
    win_va_for,
)

_REPO = Path(__file__).resolve().parent.parent
_WIN_SYMBOLS = _REPO / "data/windows-builds/caesar2_symbols.json"

_CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

_JCC = frozenset({
    "je", "jne", "jl", "jle", "jg", "jge", "jb", "jbe", "ja", "jae",
    "jz", "jnz", "js", "jns", "jo", "jno", "jp", "jnp",
})


# ── generic jmp-topology extraction (works on any /Od or Watcom blob) ────
@dataclass(frozen=True)
class Funnel:
    target: int          # function-relative offset of the converged-on block
    indeg: int           # number of unconditional jmps landing there
    epilogue: bool       # target is a pure pop/leave/ret tail (return-like)
    detached: bool       # insn before target is ret/jmp (no fall-through)
    kind: str = "label"  # return | loop-inc (continue) | label


@dataclass(frozen=True)
class JmpTopology:
    n_insn: int
    n_jmp: int                       # internal unconditional jmps
    funnels: tuple[Funnel, ...]      # indeg >= 2 targets of unconditional jmps
    n_pairs: int                     # jcc-skipping-exactly-the-next-jmp sites
                                     # (= `if (c) <goto/break/continue/return>;`)

    @property
    def goto_profile(self) -> tuple[int, ...]:
        """Sorted in-degrees of NON-epilogue funnels — the comparable
        fingerprint of shared-label structure (epilogue funnels are
        plain multi-`return` and carry no goto information)."""
        return tuple(sorted((f.indeg for f in self.funnels if not f.epilogue),
                            reverse=True))


def _decode(code: bytes) -> list:
    return list(_CS.disasm(code, 0))


def _funnel_kind(insns_by_off: dict[int, "capstone.CsInsn"], off: int) -> str:
    """Heuristic label for a funnel target block.

    ``loop-inc (continue)`` — the /Od for-increment template
    (inc/dec/add/sub on a frame slot, then cmp): only the backedge and
    ``continue`` statements can converge there (no source label can name
    the increment — proven in docs/msvc-od-goto-signal.md), so an
    in-degree >= 2 here means the source had a ``continue``.
    Anything else non-epilogue is a shared source ``label``.
    """
    if _is_pure_epilogue(insns_by_off, off):
        return "return"
    # allow a multi-statement increment (comma expression: `x++, p += 20`
    # = several inc/add insns, possibly a reload) before the loop test
    cur, seen_arith = off, False
    for _ in range(6):
        a = insns_by_off.get(cur)
        if a is None:
            break
        if a.mnemonic in ("inc", "dec", "add", "sub"):
            seen_arith = True
            cur += a.size
            continue
        if seen_arith and a.mnemonic in ("mov", "shl", "lea"):
            cur += a.size          # test-operand reload after the increment
            continue
        if seen_arith and a.mnemonic == "cmp":
            return "loop-inc"
        break
    return "label"


def _is_pure_epilogue(insns_by_off: dict[int, "capstone.CsInsn"],
                      off: int, limit: int = 8) -> bool:
    """True if from ``off`` the straight-line code is only pop/leave/ret."""
    for _ in range(limit):
        ins = insns_by_off.get(off)
        if ins is None:
            return False
        if ins.mnemonic == "ret":
            return True
        if ins.mnemonic not in ("pop", "leave"):
            return False
        off += ins.size
    return False


def jmp_topology(code: bytes) -> JmpTopology:
    """Extract the internal unconditional-jmp topology of a code blob."""
    insns = _decode(code)
    by_off = {i.address: i for i in insns}
    n = len(code)

    jmp_targets: dict[int, int] = {}
    n_jmp = 0
    n_pairs = 0
    prev = None
    for ins in insns:
        if ins.mnemonic == "jmp" and ins.op_str.startswith("0x"):
            tgt = int(ins.op_str, 16)
            if 0 <= tgt < n:
                n_jmp += 1
                jmp_targets[tgt] = jmp_targets.get(tgt, 0) + 1
            # the conditional-jump-statement pair: a jcc whose target is
            # EXACTLY the end of this jmp (it skips only the jmp)
            if (prev is not None and prev.mnemonic in _JCC
                    and prev.op_str.startswith("0x")
                    and int(prev.op_str, 16) == ins.address + ins.size):
                n_pairs += 1
        prev = ins

    funnels = []
    for tgt, indeg in sorted(jmp_targets.items()):
        if indeg < 2:
            continue
        # detached = the byte before the target is not fall-through code
        det = False
        for ins in insns:
            if ins.address + ins.size == tgt:
                det = ins.mnemonic in ("ret", "jmp")
                break
        funnels.append(Funnel(tgt, indeg, _is_pure_epilogue(by_off, tgt), det,
                              _funnel_kind(by_off, tgt)))
    return JmpTopology(len(insns), n_jmp, tuple(funnels), n_pairs)


# ── source census ────────────────────────────────────────────────────────
_LABEL_RE = re.compile(
    r"^\s*(?!default\b)(?!case\b)([A-Za-z_]\w*)\s*:(?![:=])", re.M)
_GOTO_RE = re.compile(r"\bgoto\s+([A-Za-z_]\w*)")


def _function_body(name: str) -> Optional[str]:
    """Brace-matched body of ``name`` from its decomp/src TU (build-free)."""
    tu = tu_of(name)
    if tu is None:
        return None
    text = (SRC_DIR / f"{tu}.c").read_text(errors="replace")
    pat = re.compile(rf"^[A-Za-z_][^\n;]*\b{re.escape(name)}\s*\(", re.M)
    for m in pat.finditer(text):
        brace = text.find("{", m.end())
        semi = text.find(";", m.end())
        if brace == -1 or (semi != -1 and semi < brace):
            continue                     # prototype
        depth, j = 0, brace
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    return text[brace:j + 1]
            j += 1
    return None


def source_goto_census(name: str) -> Optional[dict]:
    """``{gotos, labels, label_names}`` for a decompiled function's source."""
    body = _function_body(name)
    if body is None:
        return None
    gotos = _GOTO_RE.findall(body)
    labels = [m for m in _LABEL_RE.findall(body)]
    return {"gotos": len(gotos), "labels": len(labels),
            "label_names": sorted(set(labels))}


# ── WIN side: CAESAR2.EXE size lookup ────────────────────────────────────
@lru_cache(maxsize=1)
def _win_symbol_sizes() -> dict[str, int]:
    if not _WIN_SYMBOLS.is_file():
        return {}
    out: dict[str, int] = {}
    for s in json.loads(_WIN_SYMBOLS.read_text()):
        ps = s.get("ps_name")
        if ps and s.get("size"):
            out[ps] = int(s["size"])
    return out


# ── the differential audit ───────────────────────────────────────────────
@dataclass
class GotoVerdict:
    name: str
    tu: str
    ok: bool
    note: str = ""
    quality: float = 0.0            # aligned-instruction match ratio (0..1)
    gate: str = ""                  # usable | caution | mapping-suspect
    src: Optional[dict] = None      # source_goto_census()
    ours: Optional[JmpTopology] = None
    theirs: Optional[JmpTopology] = None
    ps_evidence: list = field(default_factory=list)
    verdict: str = ""               # consistent | missing-goto | extra-goto | mixed
    detail: list = field(default_factory=list)


def _q(ours_code: bytes, mask: set[int], theirs_code: bytes) -> float:
    import difflib
    ours = disasm_norm(ours_code, mask)
    theirs = disasm_norm(theirs_code)
    sm = difflib.SequenceMatcher(a=[r[2] for r in ours],
                                 b=[r[2] for r in theirs], autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / max(len(ours), 1)


def win_goto_audit(name: str, tu: Optional[str] = None, *,
                   win: Optional[WinImage] = None,
                   ctu: Optional[CompiledTU] = None) -> GotoVerdict:
    """Differential goto-topology audit: our MSVC /Od build vs CAESAR2.EXE.

    Verdicts (only trust ``gate == usable``/``caution``):

    * ``missing-goto`` — CAESAR2.EXE has non-epilogue jmp-funnels (shared
      labels) or clearly more internal jmps than our compile: the
      original source had goto/label structure we haven't recovered.
    * ``extra-goto``  — our compile shows funnel/jmp structure the
      original lacks: we invented gotos (or mis-shaped control flow).
    * ``consistent``  — jump-statement topology matches.
    """
    tu = tu or tu_of(name)
    if tu is None:
        return GotoVerdict(name, "?", False, note="unknown TU")
    win = win or load_win_image()
    ctu = ctu or compile_tu(tu)
    if ctu.errors:
        return GotoVerdict(name, tu, False,
                           note=f"TU fails MSVC compile: {ctu.errors[0]}")
    fc = ctu.func_code(name)
    if fc is None:
        return GotoVerdict(name, tu, False, note="no MSVC body")
    code, mask = fc
    # Byte-exact certificate first (map-independent, like verify_func):
    # a masked hit anywhere in .text means ours == theirs, so the audit
    # is trivially consistent AND we must NOT trust a possibly-stale
    # func-map VA over the located one.
    from c2.win_bytes import masked_find
    hits = masked_find(win.text, code, mask)
    if hits:
        wbytes = win.text[hits[0]:hits[0] + len(code)]
        q, gate = 1.0, "usable"
    else:
        resolved = win_va_for(name, tu)
        if not resolved:
            return GotoVerdict(name, tu, False, note="no win mapping")
        win_va = resolved[0]
        # symbol sizes are sometimes a few bytes short (they exclude
        # alignment padding and can be stale); truncating drops real jmp
        # edges near the tail, so take the larger of the two estimates —
        # jmp targets must land inside the window to count, which keeps
        # over-reading into a neighbour harmless in practice.
        their_n = max(_win_symbol_sizes().get(name) or 0, len(code))
        wbytes = win.func_bytes(win_va, their_n)
        if not wbytes:
            return GotoVerdict(name, tu, False, note="win VA out of .text")
        q = _q(code, mask, wbytes[:len(code)] if their_n >= len(code) else wbytes)
        gate = "usable" if q >= 0.85 else ("caution" if q >= 0.7
                                           else "mapping-suspect")
    ours = jmp_topology(code)
    theirs = jmp_topology(wbytes)
    src = source_goto_census(name)

    detail: list[str] = []
    op, tp = ours.goto_profile, theirs.goto_profile
    d_jmp = theirs.n_jmp - ours.n_jmp
    d_pairs = theirs.n_pairs - ours.n_pairs
    missing = extra = False
    if tp != op:
        # compare funnel fingerprints (sorted non-epilogue in-degrees)
        if sum(tp) > sum(op) or (tp and max(tp, default=0) > max(op, default=0)):
            missing = True
            detail.append(
                f"WIN funnels {list(tp)} vs ours {list(op)} — CAESAR2.EXE has "
                "shared-label convergence our source lacks")
        if sum(op) > sum(tp):
            extra = True
            detail.append(
                f"our funnels {list(op)} vs WIN {list(tp)} — our source "
                "converges jmps the original doesn't")
    if abs(d_jmp) >= 2:
        (detail.append(f"internal jmp count: WIN {theirs.n_jmp} vs ours "
                       f"{ours.n_jmp} ({d_jmp:+d})"))
        missing |= d_jmp > 0
        extra |= d_jmp < 0
    if d_pairs:
        detail.append(f"cond-jump-statement pairs: WIN {theirs.n_pairs} vs "
                      f"ours {ours.n_pairs} ({d_pairs:+d})")

    if missing and extra:
        verdict = "mixed"
    elif missing:
        verdict = "missing-goto"
    elif extra:
        verdict = "extra-goto"
    else:
        verdict = "consistent"

    return GotoVerdict(name, tu, True, "", q, gate, src, ours, theirs,
                       ps_goto_evidence(name), verdict, detail)


# ── PS side: Watcom non-structured-topology corroboration ────────────────
def ps_goto_evidence(name: str) -> list[dict]:
    """Detached multi-predecessor blocks in PS.EXE's copy of ``name``.

    The only goto shape Watcom 10.0a provably cannot synthesize from
    structured statements: a block with NO fall-through entry (preceded
    by ``ret``/``jmp``), not a pure shared epilogue, converged on by
    >= 2 branches (jcc or jmp).  Empirically everything weaker (single
    goto == break/return/while etc.) is byte-identical to structured
    forms — see docs/msvc-od-goto-signal.md.
    """
    try:
        from c2.commands.disasm import disasm_function
        _start, _size, lines = disasm_function(name)
    except Exception:
        return []
    code = b"".join(bytes(ln.bytes_) for ln in lines)
    base = lines[0].address if lines else 0
    insns = _decode(code)
    by_off = {i.address: i for i in insns}
    n = len(code)

    indeg: dict[int, int] = {}
    for ins in insns:
        if (ins.mnemonic == "jmp" or ins.mnemonic in _JCC) \
                and ins.op_str.startswith("0x"):
            tgt = int(ins.op_str, 16)
            if 0 <= tgt < n:
                indeg[tgt] = indeg.get(tgt, 0) + 1

    ends = {i.address + i.size: i for i in insns}
    out: list[dict] = []
    for tgt, k in sorted(indeg.items()):
        if k < 2 or tgt == 0:
            continue
        before = ends.get(tgt)
        if before is None or before.mnemonic not in ("ret", "jmp"):
            continue                          # fall-through reachable
        if _is_pure_epilogue(by_off, tgt):
            continue                          # shared epilogue / tail-merge
        out.append({"offset": tgt, "va": base + tgt, "indeg": k})
    return out


# ── compact projections for diagnose / win-census ────────────────────────
def tool_summary(name: str) -> dict:
    """Compact dict for ``c2 diagnose`` / JSON consumers."""
    v = win_goto_audit(name)
    if not v.ok:
        ps = ps_goto_evidence(name)
        return {"available": False, "note": v.note,
                "src": source_goto_census(name), "ps_evidence": ps}
    return {
        "available": True, "quality": round(v.quality, 2), "gate": v.gate,
        "verdict": v.verdict, "detail": v.detail, "src": v.src,
        "win_funnels": list(v.theirs.goto_profile),
        "our_funnels": list(v.ours.goto_profile),
        "win_jmps": v.theirs.n_jmp, "our_jmps": v.ours.n_jmp,
        "ps_evidence": v.ps_evidence,
    }
