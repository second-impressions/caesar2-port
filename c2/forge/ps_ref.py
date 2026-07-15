"""PS.EXE reference loader -- bytes, fixups, and -d1 line map for one function.

Forge needs three things for every variant comparison:

  * the PS function's raw bytes,
  * the PS function's fixup byte-set (so link-time displacements mask
    cleanly on both sides),
  * the PS function's ``offset → source-line`` map from ``-d1`` debug
    info (so the binir-IR shape detector can attribute divergences to
    statement boundaries).

All three are derived once at session start (lazy, process-cached) and
reused for every variant compile.  Reuses the existing project
machinery (:func:`c2.commands.decomp_verify._load_le_code_and_fixups`
for bytes + fixups; :func:`c2.commands.disasm.disasm_function` for
addr/size/line-cues) so the masking rules match what the verifier
already applies elsewhere.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class PSRef:
    """All PS-side data needed to score a variant against PS."""

    name: str
    address: int                       # PS image address (e.g. 0x12340)
    bytes_: bytes                      # raw function bytes
    fixups: frozenset[int]             # byte offsets RELATIVE TO FUNCTION START
    line_map: dict[int, int] = field(default_factory=dict)
    # ``line_map[function-relative-byte-offset] = source-line-number``
    # populated from ``-d1`` cues; empty when the function carries no debug
    # info (rare on PS.EXE -- it was built with -d1).  DEDUPED to the first
    # cue per line (the historical _build_diff_rows consumer contract).
    line_marks_full: tuple[tuple[int, int], ...] = ()
    # The FULL -d1 mark stream ``((rel_off, line), ...)`` -- NOT deduped.
    # The dual-marks run ledger needs every mark (a line re-marks when its
    # code is emitted non-contiguously: loops, else-arms, packed lines).


@lru_cache(maxsize=4096)
def load(function: str, *, exe: str = "data/PS.EXE") -> PSRef:
    """Load (and cache) the PS reference for ``function``.

    Caching is keyed by (function, exe) and the cache is per-process; the
    underlying ``_load_le_code_and_fixups`` is itself disk-cached against
    mtime so a re-import is cheap even across short subprocess lifetimes.
    """
    from c2.commands.decomp_verify import _load_le_code_and_fixups
    from c2.commands.disasm import disasm_function

    addr, size, lines = disasm_function(function)
    code, fixups_abs = _load_le_code_and_fixups(Path(exe))
    base = addr - 0x10000
    fn_bytes = bytes(code[base : base + size])
    rel_fixups = frozenset(
        f - base for f in fixups_abs if base <= f < base + size
    )

    # Line map: cue at the first byte of each statement.  Only the FIRST
    # cue for a given line is kept (matches what ``_build_diff_rows``
    # consumes -- one cue per source-line change).  ``marks_full`` keeps
    # EVERY mark for the dual-marks run ledger.
    line_map: dict[int, int] = {}
    seen: set[int] = set()
    marks_full: list[tuple[int, int]] = []
    for ln in lines:
        # disasm_function reports line=0 for every UNMARKED instruction
        # (the line_lookup default) -- 0 is not a mark; keeping it would
        # corrupt the ledger's forward-fill (and used to leak one bogus
        # (off, 0) entry into line_map).
        if not ln.line:
            continue
        rel = ln.address - addr
        if not (0 <= rel < size):
            continue
        marks_full.append((rel, ln.line))
        if ln.line in seen:
            continue
        line_map[rel] = ln.line
        seen.add(ln.line)

    return PSRef(
        name=function,
        address=addr,
        bytes_=fn_bytes,
        fixups=rel_fixups,
        line_map=line_map,
        line_marks_full=tuple(sorted(marks_full)),
    )


def clear_cache() -> None:
    """Drop the in-process PSRef cache.  Workers call this on startup so
    a stale per-import cache from a previous interpreter doesn't leak in
    via checkpoint-restore (a no-op in normal use)."""
    load.cache_clear()
