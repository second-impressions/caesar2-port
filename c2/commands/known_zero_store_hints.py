"""Rule 156 detector — tail store of a *known-zero* register.

PS sometimes satisfies a `dst = 0;` (or `dst = v;` where the flow proved
`v == 0` on that path) by **reusing a register the dataflow already knows
is zero** rather than emitting `mov byte [mem], 0` or `xor r,r; mov`.  The
byte clue is a `mov [mem], r8` whose source byte register was just
`test`ed (or `and`+tested) and the branch *fell through* to the store —
so `r8 == 0` there.

This is load-bearing, not cosmetic: the store is also an IL *use* of the
variable that occupies `r8`.  Transcribing it as `= <var>` (the obvious
read) gives that variable an extra `use_save` in CalcSavings, inflating
its savings and flipping its register seat; the faithful `= 0` removes
the use and frequently unblocks a Rule 115 / Rule 28a byte-seat tie.

See ``docs/watcom-codegen-patterns.md`` Rule 156 and the worked example
``get_education_ov_image`` (``docs/codegen-experiments/education-ov-seats.py``).

The detector is a linear-scan heuristic over the PS disasm — it suits the
flat guard-chain functions where this pattern lives.  It is advisory: it
reports the PS signature; ``decomp-verify`` gates it on the function
still diffing.
"""
from __future__ import annotations

from dataclasses import dataclass

_BYTE_REGS = {"al", "ah", "bl", "bh", "cl", "ch", "dl", "dh"}
_COND_JE = {"je", "jz"}


@dataclass(frozen=True)
class KnownZeroStore:
    off: int          # rel offset of the store instruction
    reg: str          # the known-zero byte register stored
    test_off: int     # rel offset of the test that proved it zero
    dest: str         # destination operand text (the lvalue)


def _norm(ins) -> tuple[int, str, str]:
    """Normalise an insn to (off, mnemonic, op_str).

    Accepts both the object form (``.rel_off``/``.mnemonic``/``.op_str``,
    as cgex's PSFunction yields) and decomp_verify's ``InsnT`` tuple
    ``(off, size, bytes, "mnem op_str")``."""
    if hasattr(ins, "mnemonic"):
        return (ins.rel_off, ins.mnemonic, ins.op_str or "")
    off, _size, _b, text = ins
    parts = text.split(None, 1)
    return (off, parts[0] if parts else "", parts[1] if len(parts) > 1 else "")


def _ops(op_str: str) -> list[str]:
    return [p.strip() for p in op_str.split(",")] if op_str else []


def _is_mem(op: str) -> bool:
    return "[" in op


def _writes(mnem: str, op_str: str, reg: str) -> bool:
    """True if the insn writes `reg` (reg is the destination operand 0).

    `push`/`pop` are transparent: in these epilogue-heavy guard chains a
    `pop edx` restores the caller's saved register on some *other* exit
    path -- it is not a redefinition of the byte VALUE we are tracking on
    the path that reaches the store."""
    if mnem in ("push", "pop"):
        return False
    ops = _ops(op_str)
    if not ops:
        return False
    dst = ops[0]
    if dst == reg:
        return True
    # a full-width write to the containing dword also redefines the byte
    cont = {"al": "eax", "ah": "eax", "bl": "ebx", "bh": "ebx",
            "cl": "ecx", "ch": "ecx", "dl": "edx", "dh": "edx"}.get(reg)
    if cont and dst == cont:
        return True
    return False


def detect(orig_insns) -> list[KnownZeroStore]:
    """Scan PS instructions for known-zero-register tail stores."""
    ins = [_norm(x) for x in orig_insns]
    hits: list[KnownZeroStore] = []
    for i, (off, mnem, op_str) in enumerate(ins):
        if mnem != "mov":
            continue
        ops = _ops(op_str)
        if len(ops) != 2:
            continue
        dest, src = ops
        if not _is_mem(dest) or src not in _BYTE_REGS:
            continue
        # Walk back: nearest `test src,src` with NO redefinition of src
        # between it and the store, and the following branch must be a
        # forward je/jz (store reached on the zero fall-through/target).
        found = None
        for j in range(i - 1, -1, -1):
            joff, jmn, jop = ins[j]
            if jmn == "test":
                tops = _ops(jop)
                if len(tops) == 2 and tops[0] == src and tops[1] == src:
                    if j + 1 < len(ins) and ins[j + 1][1] in _COND_JE:
                        found = joff
                    break
                continue
            if _writes(jmn, jop, src):
                break
        if found is not None:
            hits.append(KnownZeroStore(off=off, reg=src,
                                       test_off=found, dest=dest))
    return hits


def to_json(hits: list[KnownZeroStore]) -> list[dict] | None:
    if not hits:
        return None
    return [{"rule": "156", "off": h.off, "reg": h.reg,
             "test_off": h.test_off, "dest": h.dest} for h in hits]


def render(hits: list[KnownZeroStore]) -> str | None:
    """One advisory line for the decomp-verify console."""
    if not hits:
        return None
    h = hits[0]
    extra = f" (+{len(hits) - 1} more)" if len(hits) > 1 else ""
    return (f"known-zero store: PS `mov [mem], {h.reg}` at +0x{h.off:x} reuses a "
            f"register proven 0 by `test {h.reg},{h.reg}` at +0x{h.test_off:x} "
            f"-> the source statement is `= 0`, NOT `= <{h.reg}-var>` (Rule 156); "
            f"the dropped use can unblock a Rule 115/28a byte-seat tie{extra}")
