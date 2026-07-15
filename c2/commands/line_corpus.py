"""Cross-corpus line-code index: 1:1 source-line <-> generated-code map.

For every BYTE-EXACT decompiled function we know, with certainty, which C
source line produced each run of machine code (via the Watcom -d1 line table
of *our* compiled binary -- not a comment-counting heuristic).  This module
turns that into a reverse index keyed by the *normalized* bytes of each
source-line's instruction run, so that when decompiling a new function we can
look up "what verified C source produced this exact code elsewhere".

Normalization masks the two things that legitimately differ between two
otherwise-identical code runs:

  * **relocations** (absolute address fields, from the LE fixup table), and
  * **branch displacements** (rel8 / rel32 of jmp/call/jcc, which encode
    layout, not source).

Everything else -- opcodes, registers, immediates, memory displacements -- is
kept, so a match means the runs are genuinely the same binary code (modulo
which global/target they reference).  That makes a match a high-confidence
source suggestion, at the cost of requiring the register context to align.

The index is refreshed as a byproduct of every ``decomp-verify`` pass
(negligible cost -- disassembling the exact corpus is ~0.1s).  A FULL pass
rewrites the whole index; a partial/filtered (``-f`` / per-file) pass MERGES
the functions it visited into the existing index (refreshing those and
preserving all others) so it can't be clobbered with an incomplete index --
see ``CorpusBuilder.save(merge_processed=...)``.  It is never rebuilt
recursively.  ``line-shape`` consumes the cache statically (PS disasm only).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

CORPUS_PATH = Path(".c2-cache/line-corpus.json")


@lru_cache(maxsize=128)
def _read_src_lines(path_str: str) -> tuple[str, ...]:
    """Cached source-file read (the corpus builder calls extract_line_runs
    ~1k times across ~33 files; reading each file once keeps it cheap)."""
    try:
        return tuple(Path(path_str).read_text(errors="ignore").splitlines())
    except OSError:
        return ()

# A line-run must be at least this many post-normalization bytes to be
# indexed/matched.  Below this, runs are too short to be distinctive
# (e.g. a bare ``inc eax`` matches everything).
MIN_RUN_BYTES = 5

# Branch opcodes whose displacement bytes must be masked (they encode
# layout, not source).  Value = (disp_start, disp_len) within the insn.
_REL32_1 = {0xE8, 0xE9}              # call/jmp rel32  -> bytes [1:5]
_REL8_1 = set(range(0x70, 0x80)) | {0xEB, 0xE0, 0xE1, 0xE2, 0xE3}  # jcc/jmp/loop rel8 -> byte [1]


def normalize_insn(raw: bytes, code_off: int, fixups: set[int]) -> bytes:
    """Return ``raw`` with relocation + branch-displacement bytes zeroed.

    ``code_off`` is the instruction's offset within the LE code section;
    ``fixups`` is the set of code-section byte offsets that are relocated
    (from the LE fixup table).  Both the corpus (RC) side and the query
    (PS) side call this with their own code offset + fixup set, so an
    exact byte-for-byte run normalizes identically on both.
    """
    out = bytearray(raw)
    n = len(out)
    # Relocation fields (absolute addresses).
    for k in range(n):
        if (code_off + k) in fixups:
            out[k] = 0
    if n == 0:
        return bytes(out)
    op = out[0]
    # Branch displacements (relative, layout-dependent).
    if op in _REL32_1 and n >= 5:
        for k in range(1, 5):
            out[k] = 0
    elif op in _REL8_1 and n >= 2:
        out[1] = 0
    elif op == 0x0F and n >= 6 and 0x80 <= out[1] <= 0x8F:   # jcc rel32
        for k in range(2, 6):
            out[k] = 0
    return bytes(out)


@dataclass
class LineRun:
    """One source-line's instruction run from a byte-exact function."""
    line: int                 # source line in `file`
    norm_hex: str             # normalized bytes, hex (the index key)
    text: str                 # the C source text of that line (stripped)
    nbytes: int               # length of the (normalized) run in bytes


def group_by_line(
    insns: list[tuple[int, bytes]],
    base_off: int,
    line_map: dict[int, int],
) -> list[tuple[int, list[tuple[int, bytes]]]]:
    """Group ``(rel_off, raw)`` instructions by inherited source line.

    ``line_map`` is ``{flat_code_offset: line}``; ``flat = base_off + rel``.
    Instructions whose offset is not a statement-start inherit the previous
    line (Watcom -d1 semantics).  Returns ``[(line, [(rel, raw), ...])]`` in
    first-appearance order.
    """
    groups: dict[int, list[tuple[int, bytes]]] = {}
    order: list[int] = []
    cur_line: int | None = None
    for rel, raw in insns:
        ln = line_map.get(base_off + rel)
        if ln is not None:
            cur_line = ln
        if cur_line is None:
            continue
        if cur_line not in groups:
            groups[cur_line] = []
            order.append(cur_line)
        groups[cur_line].append((rel, raw))
    return [(ln, groups[ln]) for ln in order]


def extract_line_runs(
    insns: list[tuple[int, bytes]],
    rc_base_off: int,
    recomp_fix: set[int],
    recomp_line_map: dict[int, int],
    src_path: Path,
) -> list[LineRun]:
    """Carve a byte-exact function's RC instructions into per-source-line runs.

    ``recomp_line_map`` is ``{flat_rc_code_offset: source_line}`` from the
    Watcom -d1 debug info of our compiled binary -- the exact 1:1 mapping.
    ``insns`` is ``[(rel_off, raw_bytes), ...]``.  Source text comes from
    ``src_path`` at the mapped line.
    """
    src_lines = _read_src_lines(str(src_path))

    runs: list[LineRun] = []
    for ln, chunks in group_by_line(insns, rc_base_off, recomp_line_map):
        norm = bytearray()
        for rel, raw in chunks:
            norm += normalize_insn(raw, rc_base_off + rel, recomp_fix)
        if len(norm) < MIN_RUN_BYTES:
            continue
        text = src_lines[ln - 1].strip() if 1 <= ln <= len(src_lines) else ""
        if not text:
            continue
        runs.append(LineRun(line=ln, norm_hex=norm.hex(), text=text, nbytes=len(norm)))
    return runs


@dataclass
class CorpusEntry:
    func: str
    file: str
    line: int
    text: str
    nbytes: int


class CorpusBuilder:
    """Accumulates ``norm_hex -> [CorpusEntry]`` during a decomp pass."""

    def __init__(self) -> None:
        self.index: dict[str, list[dict]] = {}
        self.n_funcs = 0
        self.n_runs = 0

    def add_function(self, func: str, file: str, runs: list[LineRun]) -> None:
        if not runs:
            return
        self.n_funcs += 1
        for r in runs:
            bucket = self.index.setdefault(r.norm_hex, [])
            # Dedupe identical (func, line) re-entries.
            if any(e["func"] == func and e["line"] == r.line for e in bucket):
                continue
            bucket.append({
                "func": func, "file": file, "line": r.line,
                "text": r.text, "nbytes": r.nbytes,
            })
            self.n_runs += 1

    def save(self, path: Path = CORPUS_PATH,
             *, merge_processed: set[str] | None = None) -> None:
        """Write the corpus index.

        Full pass (``merge_processed is None``): write the freshly-built index
        verbatim -- it is complete.

        Partial pass (``merge_processed`` = the set of function names visited
        this pass): MERGE into the existing on-disk index so an ``-f`` /
        per-file run refreshes only the functions it actually recompiled and
        preserves every other function's entries.  Stale entries for the
        visited functions are dropped first (a function that stopped being
        byte-exact is thereby removed); the fresh runs are then overlaid.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        if merge_processed is not None and path.exists():
            try:
                existing = (json.loads(path.read_text()) or {}).get("index", {})
            except (OSError, ValueError):
                existing = {}
            merged: dict[str, list[dict]] = {}
            for norm_hex, entries in existing.items():
                kept = [e for e in entries if e["func"] not in merge_processed]
                if kept:
                    merged[norm_hex] = kept
            for norm_hex, entries in self.index.items():
                bucket = merged.setdefault(norm_hex, [])
                have = {(e["func"], e["line"]) for e in bucket}
                for e in entries:
                    if (e["func"], e["line"]) not in have:
                        bucket.append(e)
            index = merged
        else:
            index = self.index
        # Recount from the final index so the reported totals are accurate for
        # both the full-write and merge paths.
        self.n_runs = sum(len(v) for v in index.values())
        self.n_funcs = len({e["func"] for v in index.values() for e in v})
        payload = {
            "version": 1,
            "n_functions": self.n_funcs,
            "n_runs": self.n_runs,
            "min_run_bytes": MIN_RUN_BYTES,
            "index": index,
        }
        path.write_text(json.dumps(payload))


def load_corpus(path: Path = CORPUS_PATH) -> dict[str, list[dict]] | None:
    """Load the index (``norm_hex -> [entry]``) or None if absent."""
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return doc.get("index") or {}


@dataclass
class LineMatch:
    """A corpus match for one query line."""
    norm_hex: str
    nbytes: int
    # Distinct source texts that produced this exact code, with a sample
    # function for each (most-distinctive first is the caller's job).
    suggestions: list[dict] = field(default_factory=list)  # {text, func, file, line, count}
    n_functions: int = 0           # how many distinct functions share this run


import re as _re

_STRUCTURAL = {"", "{", "}", "};", ")", "});", "} else {", "} else"}
# A function-definition signature: <type> name(...) with no ';', '=' or body.
_SIG_RE = _re.compile(r"^[A-Za-z_][\w\s\*]*\b[A-Za-z_]\w*\s*\([^;{}]*\)\s*$")
_CTRL = ("if", "for", "while", "switch", "return", "do", "else")


def is_useful_text(text: str) -> bool:
    """False for code-shape boilerplate that is a useless source suggestion:
    bare braces, and function-definition signatures (these are what prologue/
    epilogue runs map to, since those instructions inherit the def line).
    """
    t = text.strip()
    if t in _STRUCTURAL:
        return False
    head = t.split("(")[0].split()
    first = head[0] if head else ""  # empty when t starts with '(' (e.g. a cast)
    if first not in _CTRL and "=" not in t and _SIG_RE.match(t):
        return False
    return True


def useful_suggestions(match: "LineMatch", limit: int | None = None) -> list[dict]:
    """Suggestions with structural/signature noise removed, most-shared first.
    Used for the compact text output (JSON keeps the full unfiltered list)."""
    out = [s for s in match.suggestions if is_useful_text(s["text"])]
    return out[:limit] if limit else out


def match_run(
    norm_hex: str, nbytes: int, corpus: dict[str, list[dict]],
    *, self_func: str | None = None,
) -> LineMatch | None:
    """Look up a normalized run in the corpus; group by distinct source text."""
    entries = corpus.get(norm_hex)
    if not entries:
        return None
    by_text: dict[str, dict] = {}
    funcs: set[str] = set()
    for e in entries:
        if self_func and e["func"] == self_func:
            continue
        funcs.add(e["func"])
        # Dedupe on whitespace-stripped text so pure-formatting variants of
        # the same source line (`arr[i];` vs `arr[i] ;`) count as one.
        key = "".join(e["text"].split())
        slot = by_text.setdefault(key, {
            "text": e["text"], "func": e["func"], "file": e["file"],
            "line": e["line"], "count": 0,
        })
        slot["count"] += 1
    if not by_text:
        return None
    # Most-shared text first (a widely-shared idiom is the safer suggestion).
    suggestions = sorted(by_text.values(), key=lambda s: -s["count"])
    return LineMatch(
        norm_hex=norm_hex, nbytes=nbytes,
        suggestions=suggestions, n_functions=len(funcs),
    )
