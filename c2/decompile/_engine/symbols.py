"""Symbol-table lookup for the ``lookup`` agent tool.

Smart single-entry API: a query string is interpreted as either

  * a hex/decimal **address** (``0x117d6c``, ``117d6c``, ``1146732``)
    \u2192 reverse lookup: nearest containing symbol + signed delta
  * a **glob pattern** (contains ``*`` or ``?``)
    \u2192 list matching symbols (capped at 25)
  * an exact **name**
    \u2192 forward lookup with full metadata

Returns a small dataclass so callers (CLI / TS tool / JSON) can format
as they like.  Reads ``symbols.json`` once per process.
"""

from __future__ import annotations

import fnmatch
import json
import re
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class SymbolHit:
    name: str
    address_hex: str
    address: int
    kind: str               # "function" | "data" | "static"
    size: int | None        # exact for functions; None for data globals
    source_file: str | None
    source_lines: tuple[int, int] | None
    delta: int = 0          # signed offset from the matched symbol (reverse-lookup only)

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.source_lines is None:
            d["source_lines"] = None
        else:
            d["source_lines"] = list(self.source_lines)
        return d


# \u2500\u2500 Lazy load \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


@lru_cache(maxsize=4)
def _load(symbols_json_str: str) -> dict:
    raw = json.loads(Path(symbols_json_str).read_text())
    # Build helper indices for fast lookup.
    by_name = {s["name"]: s for s in raw["symbols"]}
    by_addr_sorted = sorted(raw["symbols"], key=lambda s: s["address"])

    # Per-function size: next symbol's address - this one's address (for
    # is_code symbols; conservative cap at 65536 for the last function).
    code_sorted = sorted(
        (s for s in raw["symbols"] if s.get("is_code")),
        key=lambda s: s["address"],
    )
    sizes: dict[str, int] = {}
    for i, s in enumerate(code_sorted[:-1]):
        sizes[s["name"]] = code_sorted[i + 1]["address"] - s["address"]
    if code_sorted:
        sizes[code_sorted[-1]["name"]] = 256  # conservative

    # Per-function source line range from the line_numbers table.
    line_marks_by_addr: dict[int, list[tuple[int, str]]] = {}
    for ln in raw.get("line_numbers", []):
        line_marks_by_addr.setdefault(ln["address"], []).append(
            (ln["line"], ln["file"])
        )

    # Per-symbol source: find first line mark at-or-after the symbol's
    # address but before the next symbol.
    source_per_name: dict[str, tuple[str, int, int]] = {}
    for i, s in enumerate(code_sorted):
        start = s["address"]
        end = code_sorted[i + 1]["address"] if i + 1 < len(code_sorted) \
              else start + sizes.get(s["name"], 256)
        marks = []
        for addr in sorted(line_marks_by_addr.keys()):
            if start <= addr < end:
                marks.extend(line_marks_by_addr[addr])
        if marks:
            files = {f for _, f in marks}
            file = next(iter(files))
            lo = min(line for line, _ in marks)
            hi = max(line for line, _ in marks)
            source_per_name[s["name"]] = (file, lo, hi)

    return {
        "by_name": by_name,
        "by_addr_sorted": by_addr_sorted,
        "sizes": sizes,
        "source_per_name": source_per_name,
    }


def _kind(sym: dict) -> str:
    if sym.get("is_code"):
        return "function"
    if sym.get("is_static"):
        return "static"
    return "data"


def _to_hit(idx: dict, sym: dict, *, delta: int = 0) -> SymbolHit:
    name = sym["name"]
    source = idx["source_per_name"].get(name)
    return SymbolHit(
        name=name,
        address_hex=sym["address_hex"],
        address=sym["address"],
        kind=_kind(sym),
        size=idx["sizes"].get(name),
        source_file=source[0] if source else None,
        source_lines=(source[1], source[2]) if source else None,
        delta=delta,
    )


# \u2500\u2500 Query parsing + dispatch \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500


_HEX_RE = re.compile(r"^(?:0[xX])?[0-9a-fA-F]+$")


def parse_address(query: str) -> int | None:
    """Return an integer address if ``query`` is hex/decimal, else None."""
    q = query.strip()
    if q.startswith(("0x", "0X")):
        try:
            return int(q, 16)
        except ValueError:
            return None
    # Hex with no prefix \u2014 if it's all hex digits AND >= 5 chars (so we
    # don't mistake short decimal numbers for hex)
    if _HEX_RE.match(q) and len(q) >= 5:
        try:
            return int(q, 16)
        except ValueError:
            return None
    # Plain decimal
    if q.isdigit():
        return int(q)
    return None


def lookup(symbols_json: Path, query: str,
           *, limit: int = 25) -> list[SymbolHit]:
    """Single-entry symbol search.  See module docstring."""
    idx = _load(str(symbols_json))

    addr = parse_address(query)
    if addr is not None:
        return _reverse_lookup(idx, addr)

    if "*" in query or "?" in query:
        return _glob_lookup(idx, query, limit=limit)

    sym = idx["by_name"].get(query)
    if sym is None:
        # Fuzzy fallback: case-insensitive contains match (capped)
        q_lower = query.lower()
        hits = [
            _to_hit(idx, s) for s in idx["by_addr_sorted"]
            if q_lower in s["name"].lower()
        ]
        return hits[:limit]
    return [_to_hit(idx, sym)]


def _reverse_lookup(idx: dict, addr: int) -> list[SymbolHit]:
    """Find the symbol containing or nearest to ``addr``."""
    by_addr = idx["by_addr_sorted"]
    sizes = idx["sizes"]

    # Walk to find candidates: nearest at-or-below and nearest above.
    lo = 0
    hi = len(by_addr)
    while lo < hi:
        mid = (lo + hi) // 2
        if by_addr[mid]["address"] <= addr:
            lo = mid + 1
        else:
            hi = mid

    candidates: list[tuple[int, SymbolHit]] = []
    if lo > 0:
        prev = by_addr[lo - 1]
        delta = addr - prev["address"]
        if delta == 0:
            return [_to_hit(idx, prev, delta=0)]
        # Functions have a known size; data globals: assume up to 16 KiB
        # field-displacement window.
        size = sizes.get(prev["name"], 0x4000)
        if delta <= max(size, 0x4000):
            candidates.append((delta, _to_hit(idx, prev, delta=delta)))
    if lo < len(by_addr):
        nxt = by_addr[lo]
        delta = nxt["address"] - addr
        if delta <= 0x100:
            candidates.append((delta, _to_hit(idx, nxt, delta=-delta)))
    if not candidates:
        return []
    candidates.sort(key=lambda c: c[0])
    return [candidates[0][1]]


def _glob_lookup(idx: dict, pattern: str, *, limit: int) -> list[SymbolHit]:
    matched = [
        _to_hit(idx, s) for s in idx["by_addr_sorted"]
        if fnmatch.fnmatchcase(s["name"], pattern)
    ]
    matched.sort(key=lambda h: (h.kind, h.name))
    return matched[:limit]
