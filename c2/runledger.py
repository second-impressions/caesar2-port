"""Dual ``-d1`` run ledger -- statement-level, register-blind PS-vs-RC
instruction comparison built on each side's OWN line marks.

WHY THIS EXISTS.  Every earlier per-line diagnostic (``binir-shape``,
``diagnose``'s divergent-lines, the harness ``lines()`` v1) attributed the
RC instructions to PS source lines THROUGH the byte-diff alignment
(``_build_diff_rows``'s SequenceMatcher).  On a non-exact function that
alignment drifts at every length-changing diff, so RC ops get attached to
the wrong PS line and the per-line comparison reports PHANTOM divergences
(e.g. ``test_elastic_range``'s "L359 RC has 2x branch_jmp, 3x cmp_jcc, ..."
mega-multiset -- pure misattribution; the real levers were loop rotation +
char-typed locals).  The bigger the function, the worse the drift -- this
is why per-line work "beyond ~400 bytes" kept failing.

THE FIX (this module).  Both sides carry their own authoritative ``-d1``
line marks: PS.EXE's debug directory (symbols.json ``line_numbers``) and
our compile's line table (``_load_oracle_line_lookup`` / the scratch
compile's marks).  So:

1. Segment EACH side by its OWN marks -- no cross-side attribution at all.
2. Canonicalize every instruction to a REGISTER-BLIND, width-preserving
   form (``mov R32, dword ptr [R32 + 8]``), masking exactly the
   linker-resolved constants (fixup'd dwords -> ``G``) and branch targets
   (-> ``T``).
3. Align the two canonical instruction STREAMS (difflib); the unmatched
   stretches are "islands", each carrying its own side's line attribution.

INVARIANTS (validated on the corpus):
* byte-exact  =>  zero islands (the canonical streams are identical);
* zero islands on a DIFFING function  =>  the whole diff is register
  seats / spill slots / encoding, i.e. pure regalloc residue -- do NOT
  restructure the source (regtrace territory);
* each island is a LOCAL statement-shape divergence whose PS lines (the
  original ``-d1`` witness) and RC lines (our source, the edit target)
  are both exact.

The canonical form deliberately KEEPS: mnemonics (``jl`` vs ``jb`` =
signedness), operand widths (``R8`` vs ``R32``, ``byte ptr`` vs ``dword
ptr`` = char-vs-int locals), non-fixup immediates (consts), and esp
displacements (slot layout).  It BLINDS only the register identity and
link-resolved values -- the two things regalloc/linking may legitimately
change under an identical source shape.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field

# ---- canonicalization -------------------------------------------------------

_REG8 = frozenset("al ah bl bh cl ch dl dh".split())
_REG16 = frozenset("ax bx cx dx si di bp sp".split())
_REG_RE = re.compile(r"\b(e?[abcd]x|[abcd][lh]|e?(?:si|di|bp|sp))\b")
_HEX_RE = re.compile(r"0x[0-9a-f]+")
_BRANCH_MN = frozenset(("call", "jmp", "loop", "loope", "loopne"))


def _reg_placeholder(m: re.Match) -> str:
    r = m.group(1)
    if r in _REG8:
        return "R8"
    if r in _REG16:
        return "R16"
    return "R32"


def canon_insn(
    off: int,
    size: int,
    text: str,
    fix_rel: frozenset[int] | set[int],
    func_bytes: bytes,
) -> str:
    """Canonical register-blind form of one instruction.

    ``text`` is the ``"mnemonic op_str"`` disassembly; ``off``/``size``
    are function-relative; ``fix_rel`` holds function-relative offsets of
    linker-fixup bytes; ``func_bytes`` is the function's raw bytes (used
    to read the fixup'd dword so exactly THAT constant is masked).
    """
    text = (text or "").strip()
    if not text:
        return ""
    mn = text.split(None, 1)[0]
    if mn in _BRANCH_MN or mn.startswith("j"):
        # branch/call: the target is link/layout-positional -> mask fully.
        return f"{mn} T"
    ops = text[len(mn):].strip()
    # Mask exactly the fixup'd dword(s): read the value at the fixup site
    # and replace that constant's hex rendering.  (A fixup site is the
    # first byte of a 4-byte little-endian field inside this insn.)
    for f in range(off, off + size):
        if f in fix_rel and f + 4 <= len(func_bytes):
            val = struct.unpack("<I", func_bytes[f:f + 4])[0]
            for pat in (f"0x{val:x}", f"-0x{(1 << 32) - val:x}"):
                if pat in ops:
                    ops = ops.replace(pat, "G")
                    break
    ops = _REG_RE.sub(_reg_placeholder, ops)
    return f"{mn} {ops}".strip()


# ---- data model -------------------------------------------------------------

@dataclass
class LedgerInsn:
    """One instruction with its OWN side's line attribution."""
    off: int
    size: int
    text: str            # real disassembly (registers intact)
    canon: str           # register-blind canonical form
    line: int | None     # this side's -d1 line (forward-filled)

    def to_json(self) -> dict:
        return {"off": self.off, "size": self.size, "text": self.text,
                "canon": self.canon, "line": self.line}


@dataclass
class Island:
    """One unmatched stretch of the aligned canonical streams."""
    kind: str                     # "replace" | "ps_only" | "rc_only"
    ps: list[LedgerInsn] = field(default_factory=list)
    rc: list[LedgerInsn] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    ps_span: tuple[int, int] = (0, 0)   # [lo, hi) stream-index range
    rc_span: tuple[int, int] = (0, 0)

    @property
    def ps_lines(self) -> list[int]:
        return sorted({i.line for i in self.ps if i.line is not None})

    @property
    def rc_lines(self) -> list[int]:
        return sorted({i.line for i in self.rc if i.line is not None})

    def to_json(self) -> dict:
        return {
            "kind": self.kind,
            "ps_lines": self.ps_lines, "rc_lines": self.rc_lines,
            "tags": self.tags,
            "ps": [i.to_json() for i in self.ps],
            "rc": [i.to_json() for i in self.rc],
        }


@dataclass
class RunLedger:
    """The dual-marks ledger for one function."""
    ps_total: int = 0             # PS instruction count
    rc_total: int = 0
    matched: int = 0              # PS insns matched register-blind
    islands: list[Island] = field(default_factory=list)
    ps_marks: int = 0             # -d1 mark counts (packing witness)
    rc_marks: int = 0
    ps_runs_total: int = 0        # distinct PS line runs compared
    ps_runs_divergent: int = 0    # PS runs touched by any island
    rc_only_runs: int = 0         # RC runs living entirely in insert islands
    matched_pairs: list[tuple[int, int]] = field(default_factory=list)
    """(ps_idx, rc_idx) stream-index pairs for every register-blind-matched
    instruction -- the exact cross-side attribution (consumers can map any
    matched PS insn to the RC insn -- and its OWN source line -- that
    produced it)."""

    @property
    def verdict(self) -> str:
        if not self.ps_total:
            return "empty"
        return "regalloc_pure" if not self.islands else "shape_islands"

    def to_json(self, *, with_insns: bool = True) -> dict:
        d = {
            "verdict": self.verdict,
            "ps_total": self.ps_total, "rc_total": self.rc_total,
            "matched": self.matched,
            "ps_marks": self.ps_marks, "rc_marks": self.rc_marks,
            "ps_runs_total": self.ps_runs_total,
            "ps_runs_divergent": self.ps_runs_divergent,
            "rc_only_runs": self.rc_only_runs,
            "islands": [i.to_json() for i in self.islands],
        }
        if not with_insns:
            for i in d["islands"]:
                i.pop("ps", None)
                i.pop("rc", None)
        return d


# ---- island family tagging --------------------------------------------------

_SIGNED_JCC = frozenset(("jg", "jge", "jl", "jle"))
_UNSIGNED_JCC = frozenset(("ja", "jae", "jb", "jbe"))
_ZEXT_MN = frozenset(("movzx", "movsx"))


def _mn(insn: LedgerInsn) -> str:
    return insn.text.split(None, 1)[0] if insn.text else ""


def _tag_island(isl: Island) -> list[str]:
    """Cheap, honest FAMILY tags for an island (hints, not verdicts)."""
    tags: list[str] = []
    ps_mns = [_mn(i) for i in isl.ps]
    rc_mns = [_mn(i) for i in isl.rc]
    ps_txt = " | ".join(i.text for i in isl.ps)
    rc_txt = " | ".join(i.text for i in isl.rc)

    # frame size: sub esp, N with different N
    if any(t.startswith("sub esp,") or t.startswith("sub esp ")
           for t in (ps_txt, rc_txt)) and isl.ps and isl.rc:
        if [t for t in ps_txt.split(" | ") if t.startswith("sub esp")] != \
           [t for t in rc_txt.split(" | ") if t.startswith("sub esp")]:
            tags.append("frame")

    # spill-slot swap: both sides identical except esp/ebp displacements
    # (computed from the REAL text -- canon has already blinded esp)
    if isl.kind == "replace" and len(isl.ps) == len(isl.rc) \
            and ("[esp" in ps_txt or "[ebp" in ps_txt):
        def _slot_blind(t: str) -> str:
            t = re.sub(r"\[(esp|ebp)(?: [+-] (?:0x[0-9a-f]+|\d+))?\]",
                       r"[\1]", t)
            return _REG_RE.sub(_reg_placeholder, t)
        if [_slot_blind(i.text) for i in isl.ps] == \
           [_slot_blind(i.text) for i in isl.rc]:
            tags.append("slot")

    # signedness: signed jcc on one side, unsigned twin on the other
    if (set(ps_mns) & _SIGNED_JCC and set(rc_mns) & _UNSIGNED_JCC) or \
       (set(ps_mns) & _UNSIGNED_JCC and set(rc_mns) & _SIGNED_JCC):
        tags.append("signedness")

    # zero/sign-extension idiom family (movzx / and 0xff / xor+mov byte):
    # the char-vs-int + Rule 49 family.  Fire only when at least one side
    # shows an explicit extension idiom.
    def _has_zext(mns: list[str], txt: str) -> bool:
        return bool(set(mns) & _ZEXT_MN) \
            or ("and" in mns and "0xff" in txt) \
            or ("xor" in mns and ("byte ptr" in txt or " al" in txt
                                  or " dl" in txt or " bl" in txt
                                  or " cl" in txt))
    if _has_zext(ps_mns, ps_txt) or _has_zext(rc_mns, rc_txt):
        tags.append("zext-idiom")

    # width: same-shape ops but byte ptr vs dword ptr / R8 vs R32
    if isl.kind == "replace":
        pw = ("byte ptr" in ps_txt, "R8" in " ".join(i.canon for i in isl.ps))
        rw = ("byte ptr" in rc_txt, "R8" in " ".join(i.canon for i in isl.rc))
        if pw != rw:
            tags.append("width")

    # loop form: one side has a bare jmp where the other computes an
    # inline test (cmp/test + jcc) -- rotation / head-vs-bottom test
    def _is_test_block(mns: list[str]) -> bool:
        return any(m in ("cmp", "test") for m in mns) and \
            any(m.startswith("j") and m != "jmp" for m in mns)
    if ("jmp" in ps_mns and _is_test_block(rc_mns)) or \
       ("jmp" in rc_mns and _is_test_block(ps_mns)):
        tags.append("loop-form")

    # increment/copy REALISATION: in-place `inc`/`dec` on one side vs
    # `lea R,[R +/- 1]` on the other (the +/-1 computed into a DIFFERENT
    # register because the old value stays live under this side's register
    # pressure).  This is a regalloc/liveness realisation, NOT a source
    # shape: the identical `x++` compiles to inc OR lea depending only on
    # surrounding pressure (proven -- take_census's `structure_pass_count++`
    # diverges as inc-vs-lea while the byte-identical sibling
    # `road_pass_count++` two lines up is byte-exact).  Tag it so the
    # shape-census does not mislabel it as a shape lever.
    def _has_incdec(mns: list[str]) -> bool:
        return bool(set(mns) & {"inc", "dec"})

    def _has_lea_pm1(insns: list) -> bool:
        return any(_mn(i) == "lea"
                   and re.search(r"\[R\d+ [+-] 1\]", i.canon) for i in insns)
    if (_has_incdec(ps_mns) and _has_lea_pm1(isl.rc)) or \
       (_has_incdec(rc_mns) and _has_lea_pm1(isl.ps)):
        tags.append("incr-realize")

    # const REALISATION: a memory STORE that is an IMMEDIATE on one side and a
    # cached REGISTER on the other (`mov [m],0xf` vs `mov [m],ebp`).  This is
    # the LICM const-hoist: one side keeps the constant in a register across a
    # loop and stores the register in-loop, the other emits the immediate each
    # time.  A regalloc/LICM realisation on IDENTICAL source (the hoist fires on
    # register availability / cost, not the C) -- NOT a source shape.  Tag it so
    # shape-census does not mislabel the const-cache as a shape lever.
    def _store_kind(t: str):
        m = re.match(r"mov \w* ?ptr \[[^\]]+\], (\S+)$", t)
        if not m:
            return None
        s = m.group(1)
        if s[:1].isdigit() or s.startswith(("0x", "-")):
            return "imm"
        if re.fullmatch(r"(e?[a-d]x|[a-d][lh]|e?si|e?di|e?bp)", s):
            return "reg"
        return None
    ps_sk = {_store_kind(i.text) for i in isl.ps}
    rc_sk = {_store_kind(i.text) for i in isl.rc}
    if ("imm" in ps_sk and "reg" in rc_sk) or ("reg" in ps_sk and "imm" in rc_sk):
        tags.append("const-realize")

    # const: same canonical shapes except an immediate value
    if isl.kind == "replace" and len(isl.ps) == len(isl.rc):
        def _wipe_imm(t: str) -> str:
            return _HEX_RE.sub("K", re.sub(r"\b\d+\b", "K", t))
        if [_wipe_imm(i.canon) for i in isl.ps] == \
           [_wipe_imm(i.canon) for i in isl.rc] and "slot" not in tags:
            tags.append("const")

    if not tags:
        tags.append("ops")
    return tags


# ---- the core ---------------------------------------------------------------

def canon_stream(
    insns: list[tuple],
    marks: dict[int, int] | list[tuple[int, int]],
    fix_rel: frozenset[int] | set[int],
    func_bytes: bytes,
) -> list[LedgerInsn]:
    """Build one side's canonical stream with its OWN line attribution.

    ``insns``: [(off, size, text), ...] or [(off, size, raw, text), ...]
    (the decomp-verify ``InsnT`` shape), function-relative offsets.
    ``marks``: {rel_off: line} or [(rel_off, line), ...] -- this side's
    own -d1 marks, function-relative.
    """
    if isinstance(marks, dict):
        mark_list = sorted(marks.items())
    else:
        mark_list = sorted(marks)
    fix_rel = frozenset(fix_rel)
    out: list[LedgerInsn] = []
    mi = 0
    cur_line: int | None = None
    for t in insns:
        if len(t) >= 4:
            off, size, _raw, text = t[0], t[1], t[2], t[3]
        else:
            off, size, text = t[0], t[1], t[2]
        while mi < len(mark_list) and mark_list[mi][0] <= off:
            cur_line = mark_list[mi][1]
            mi += 1
        out.append(LedgerInsn(
            off=off, size=size, text=(text or "").strip(),
            canon=canon_insn(off, size, text, fix_rel, func_bytes),
            line=cur_line,
        ))
    return out


def build_ledger(
    ps_stream: list[LedgerInsn],
    rc_stream: list[LedgerInsn],
    *,
    ps_marks: int = 0,
    rc_marks: int = 0,
) -> RunLedger:
    """Align the two canonical streams; islands = unmatched stretches."""
    import difflib

    sm = difflib.SequenceMatcher(
        None,
        [i.canon for i in ps_stream],
        [i.canon for i in rc_stream],
        autojunk=False,
    )
    islands: list[Island] = []
    matched = 0
    matched_pairs: list[tuple[int, int]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            matched += i2 - i1
            matched_pairs.extend((i1 + k, j1 + k) for k in range(i2 - i1))
            continue
        ps_part = ps_stream[i1:i2]
        rc_part = rc_stream[j1:j2]
        kind = ("replace" if ps_part and rc_part
                else "ps_only" if ps_part else "rc_only")
        isl = Island(kind=kind, ps=ps_part, rc=rc_part,
                     ps_span=(i1, i2), rc_span=(j1, j2))
        isl.tags = _tag_island(isl)
        islands.append(isl)

    ledger = RunLedger(
        ps_total=len(ps_stream), rc_total=len(rc_stream),
        matched=matched, islands=islands,
        ps_marks=ps_marks, rc_marks=rc_marks,
        matched_pairs=matched_pairs,
    )
    # run-level counts: a PS "run" = a distinct forward-filled line value
    # over a maximal contiguous stretch.  Count runs + divergent runs.
    def _runs(stream: list[LedgerInsn]) -> list[tuple[int | None, int, int]]:
        runs: list[tuple[int | None, int, int]] = []   # (line, lo_idx, hi_idx)
        for idx, ins in enumerate(stream):
            if runs and runs[-1][0] == ins.line:
                runs[-1] = (runs[-1][0], runs[-1][1], idx)
            else:
                runs.append((ins.line, idx, idx))
        return runs

    ps_runs = _runs(ps_stream)
    ledger.ps_runs_total = len(ps_runs)
    div_offs = {i.off for isl in islands for i in isl.ps}
    ledger.ps_runs_divergent = sum(
        1 for (_ln, lo, hi) in ps_runs
        if any(ps_stream[k].off in div_offs for k in range(lo, hi + 1)))
    rc_runs = _runs(rc_stream)
    ins_offs = {i.off for isl in islands if isl.kind == "rc_only"
                for i in isl.rc}
    ledger.rc_only_runs = sum(
        1 for (_ln, lo, hi) in rc_runs
        if all(rc_stream[k].off in ins_offs for k in range(lo, hi + 1)))
    return ledger


def ledger_from_raw(
    ps_insns: list[tuple], ps_marks, ps_fix_rel, ps_bytes: bytes,
    rc_insns: list[tuple], rc_marks, rc_fix_rel, rc_bytes: bytes,
) -> RunLedger:
    """One-call convenience: canonicalize both sides + align."""
    ps_stream = canon_stream(ps_insns, ps_marks, ps_fix_rel, ps_bytes)
    rc_stream = canon_stream(rc_insns, rc_marks, rc_fix_rel, rc_bytes)
    n_pm = len(ps_marks) if not isinstance(ps_marks, dict) else len(ps_marks)
    n_rm = len(rc_marks) if not isinstance(rc_marks, dict) else len(rc_marks)
    return build_ledger(ps_stream, rc_stream, ps_marks=n_pm, rc_marks=n_rm)
