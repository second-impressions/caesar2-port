"""Register-pressure spill / rematerialization detector for `decomp-verify`.

Some diffing functions are not source-shape problems at all: PS's allocator
**spilled** a value and re-materialized it (re-read a never-written global, or
re-loaded it) at several use sites, while our build had enough free registers to
**hold** the value once.  bribe_emperor is the canonical case — PS re-reads
``imperial_gift_level`` 5× (4 redundant reads, no intervening call/write); our
build keeps it in EAX, which cascades the whole `trib*N` chain into different
registers (283 b diff).

This is **Rule 111** in ``docs/watcom-codegen-patterns.md``: a register-pressure
spill tie-break.  There is no faithful single-source lever — removing the local
makes Watcom CSE the reads into a *different* held register (still no spill), and
``volatile`` is non-faithful (other readers of the same global cache it).  The
value of this detector is *negative triage*: it tells a future session the diff
is a spill/rematerialization class so they DON'T burn time hunting a source
lever.

Mechanism (proven, OW source):
  * Normally Watcom holds a CSE-able value across blocks (full global CSE).
  * Under register pressure the allocator spills the lowest-priority conflict;
    for a constant or a global read it re-materializes (re-read) instead of
    stack-spilling, because the re-read is cheaper.
  * Which conflict gets evicted is an ordinary ``GiveBestReg``/savings
    decision; when PS's pressure forces an eviction the recompile doesn't hit,
    PS re-reads the global while the recompile holds it.  This is a pure
    allocator divergence with no confirmed source lever -- it is NOT a
    memory-mode artifact (the compiler's low-memory path is unreachable in this
    toolchain; do not try to reproduce it with any memory knob).

Detection is **PS-vs-RC differential**: count CSE-able redundant reads on each
side; flag only when PS re-reads materially more than the recompile does (so a
function where both re-read — e.g. the byte-exact ``raider_in_region`` — is NOT
flagged).

``InsnT = (address:int, size:int, raw:bytes, asm:str)`` — same tuple the rest of
decomp-verify passes around; only ``asm`` (``"<mnemonic> <op_str>"``) is used.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Flag thresholds: PS must redundantly re-read at least this many times, and
# exceed the recompile's redundant-read count by at least this margin.
_MIN_PS_REDUNDANT = 2
_MIN_MARGIN = 2

_MEM = re.compile(r"\[(0x[0-9a-f]+)\]")
_MEM_DST = re.compile(r"\[0x[0-9a-f]+\]\s*,")


@dataclass
class SpillHint:
    addr: str        # the most re-read memory operand on the PS side
    ps_reads: int    # redundant PS reads of that operand
    ps_total: int    # total redundant reads (all operands) PS side
    rc_total: int    # total redundant reads RC side
    margin: int      # ps_total - rc_total


def _classify(asm: str):
    """Return ('r'|'w', addr) for a direct-memory operand, else None.

    A read is a `[addr]` used as a source operand; a write (or read-modify-write
    like `sub [addr], eax`) is `[addr]` as the destination — it kills the value.
    """
    parts = asm.split(None, 1)
    if len(parts) < 2:
        return None
    ops = parts[1]
    m = _MEM.search(ops)
    if not m:
        return None
    if _MEM_DST.search(ops):
        return ("w", m.group(1))
    return ("r", m.group(1))


def redundant_reads(insns) -> tuple[int, dict[str, int]]:
    """Count CSE-able re-reads in one instruction stream.

    A redundant read is a `mov reg, [addr]` (or any source-`[addr]`) where the
    same `[addr]` was already read with **no intervening call and no intervening
    write to that addr** — i.e. the value was provably still available, so a real
    cross-block CSE would have elided the second load.
    """
    available: set[str] = set()
    total = 0
    per: dict[str, int] = {}
    for ins in insns:
        asm = ins[3] if not isinstance(ins, str) else ins
        if asm.startswith("call"):
            available.clear()
            continue
        ev = _classify(asm)
        if ev is None:
            continue
        kind, addr = ev
        if kind == "w":
            available.discard(addr)
            continue
        if addr in available:
            total += 1
            per[addr] = per.get(addr, 0) + 1
        else:
            available.add(addr)
    return total, per


def detect_spill_class(orig_insns, recomp_insns, *, has_body_diff: bool = True):
    """Flag a register-pressure spill/rematerialization divergence.

    Returns a :class:`SpillHint` when PS redundantly re-reads a global
    materially more than the recompile does, else ``None``.  Restricted to
    functions that currently diff (``has_body_diff``).
    """
    if not has_body_diff:
        return None
    ps_total, ps_per = redundant_reads(orig_insns)
    rc_total, _ = redundant_reads(recomp_insns)
    if ps_total < _MIN_PS_REDUNDANT:
        return None
    margin = ps_total - rc_total
    if margin < _MIN_MARGIN:
        return None
    addr, n = max(ps_per.items(), key=lambda kv: kv[1])
    return SpillHint(addr=addr, ps_reads=n, ps_total=ps_total,
                     rc_total=rc_total, margin=margin)


_SYMS: dict[int, str] | None = None


def _resolve(addr: str) -> str:
    """Map a PS data address (``0x72ba0``) to its symbol name, lazily."""
    global _SYMS
    if _SYMS is None:
        _SYMS = {}
        try:
            import json
            from pathlib import Path
            root = Path(__file__).resolve().parents[2]
            d = json.loads((root / "data" / "out" / "symbols.json").read_text())
            for s in d.get("symbols", []):
                if s.get("is_data") and "offset" in s:
                    _SYMS[int(s["offset"])] = s["name"]
        except Exception:
            _SYMS = {}
    try:
        return _SYMS.get(int(addr, 16)) or addr
    except (ValueError, TypeError):
        return addr


def render(hint: SpillHint) -> str:
    """One-line hint for `decomp-verify -v`."""
    sym = _resolve(hint.addr)
    return (
        f"Rule 111 register-pressure spill: PS re-reads {sym} "
        f"{hint.ps_reads}x (re-materialised, no call/write between) but the "
        f"recompile holds it in a register (RC redundant reads {hint.rc_total} "
        f"vs PS {hint.ps_total}). This is a regalloc spill tie-break, NOT a "
        f"source-shape bug — do not chase a source lever (removing the local "
        f"CSEs into another held reg; volatile is non-faithful). It is an "
        f"ordinary GiveBestReg eviction divergence with no confirmed lever."
    )
