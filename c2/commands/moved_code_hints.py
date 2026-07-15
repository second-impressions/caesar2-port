"""Moved-code / source-position hints (Rule 125).

Watcom 10.0a's peephole optimizer operates on a sliding queue of object-
code entries that SPANS FUNCTION BOUNDARIES.  Three transforms physically
relocate or duplicate code within that queue:

  * ``CallRet``        — ``call X; ret``  ->  ``jmp X`` (tail call).
  * ``StraightenCode`` — "hauling code up to jump": moves the block at a
    jmp's target label (label .. first unconditional jmp/ret, which may
    span several basic blocks and calls) up to the jump site, deleting
    the jump.  When the jmp is a CallRet-produced tail call and the
    target is a whole function defined LATER in the TU, the callee's
    HEAD is physically moved to the caller's address — the function's
    symbol then points at code far away from its source position.
  * ``CloneCode``      — duplicates a small (<= 40 b) block at the jump
    site; the clone loop explicitly skips ``OC_INFO`` entries.

``NextIns()``/``PrevIns()`` skip ``OC_INFO`` (line-number) entries, so
moved code leaves its ``OC_LINENUM`` records ORPHANED at the original
emission position; consecutive orphans are collapsed by
``MultiLineNums`` (last one wins).  Net observable in PS.EXE's -d1 line
table:

  * a moved/cloned function body has **ZERO line records**, and
  * the not-moved remainder (everything from the first unconditional
    jmp onward) stays at the original source position, carrying the
    function's LAST few line records (e.g. ``helping``: head at
    0x32409 with no records, tail at 0x324C9 with L1693-1697).

Decomp consequence: for such a function, **source-definition order must
NOT match symbol-address order**.  The function must be defined at its
ORIGINAL source position (where its tail/orphaned lines are) and the
optimizer reproduces the haul.  Worked example: ``helping`` in
action.c — defining it after ``act_about`` closed helping (5 b) and
act_help_icons (1 b) to byte-exact in one move.

This module detects the zero-line-record signature and classifies it:

  * ``hauled``        — trailing ``jmp`` lands in a region whose line
    numbers are LATER than the address-position neighbourhood: the
    body was hauled up; the true source position is at the tail.
    Actionable: move the definition (the hint names the spot).
  * ``tail-consumed`` — trailing ``jmp`` goes BACKWARD into an
    earlier-line donor (ordinary Rule 42 tail-merge whose deleted tail
    happened to carry every line record).  Position is fine.
  * ``relocated``     — no trailing jmp to follow (whole body ends in
    ``ret``).  The body was moved/cloned but the destination gives no
    pointer back; the room heuristic says whether the address position
    could even hold the source.

Library API: ``detect(name)``, ``render_moved_code_hint(name)``,
``to_json(hint)``, ``scan_all()``.
"""

from __future__ import annotations

import bisect
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional

import typer

# ── cached symbols.json index ───────────────────────────────────────────────

_INDEX = None


@dataclass
class _Index:
    code_base: int
    # code functions sorted by address: (addr, name, size)
    funcs: list[tuple[int, str, int]]
    func_addrs: list[int]
    by_name: dict[str, tuple[int, int]]          # name -> (addr, size)
    # line records sorted by code-section vaddr: (vaddr, line, file)
    recs: list[tuple[int, int, str]]
    rec_addrs: list[int]


def _basename(path: str) -> str:
    return os.path.basename(path.replace("\\", "/")).lower()


def _index(symbols_json: Path = Path("data/out/symbols.json")) -> _Index:
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    sym = json.loads(symbols_json.read_text())
    code_base = sym["memory_map"]["objects"][0]["base_address_int"]

    code_syms = sorted(
        (s for s in sym["symbols"] if s.get("is_code")),
        key=lambda s: s["address"],
    )
    funcs: list[tuple[int, str, int]] = []
    for i, s in enumerate(code_syms):
        nxt = (code_syms[i + 1]["address"] if i + 1 < len(code_syms)
               else s["address"])
        funcs.append((s["address"], s["name"], max(0, nxt - s["address"])))

    recs = sorted(
        (ln["offset"] + code_base, ln.get("line", 0),
         _basename(ln.get("file", "")))
        for ln in sym.get("line_numbers", [])
    )
    _INDEX = _Index(
        code_base=code_base,
        funcs=funcs,
        func_addrs=[f[0] for f in funcs],
        by_name={f[1]: (f[0], f[2]) for f in funcs},
        recs=recs,
        rec_addrs=[r[0] for r in recs],
    )
    return _INDEX


# ── hint dataclass ──────────────────────────────────────────────────────────

@dataclass
class MovedCodeHint:
    name: str
    addr: int                    # PS vaddr
    size: int
    kind: str                    # "hauled" | "tail-consumed" | "relocated"
    file: str                    # owning .c (from surrounding records)
    prev_line: int               # nearest record line below fn start
    next_line: int               # first record line at/after fn end
    room: int                    # next_line - prev_line - 1 (free lines here)
    est_lines: int               # rough body-size estimate in source lines
    # hauled only:
    tail_addr: Optional[int] = None      # trailing-jmp target (vaddr)
    tail_line: Optional[int] = None      # line at the tail region
    after_fn: Optional[str] = None       # define AFTER this function
    before_fn: Optional[str] = None      # ... and BEFORE this one


# ── detection ───────────────────────────────────────────────────────────────

def _recs_between(idx: _Index, lo: int, hi: int) -> int:
    a = bisect.bisect_left(idx.rec_addrs, lo)
    b = bisect.bisect_left(idx.rec_addrs, hi)
    return b - a


def _rec_below(idx: _Index, vaddr: int) -> Optional[tuple[int, int, str]]:
    i = bisect.bisect_left(idx.rec_addrs, vaddr) - 1
    return idx.recs[i] if i >= 0 else None


def _rec_at_or_after(idx: _Index, vaddr: int) -> Optional[tuple[int, int, str]]:
    i = bisect.bisect_left(idx.rec_addrs, vaddr)
    return idx.recs[i] if i < len(idx.recs) else None


def _trailing_jmp_target(name: str) -> Optional[int]:
    """vaddr of the function's final unconditional near-jmp target, or
    None.  Uses the cached disasm context."""
    try:
        from c2.commands.disasm import disasm_function
        _addr, _size, lines = disasm_function(name)
    except Exception:
        return None
    if not lines:
        return None
    last = lines[-1]
    if last.mnemonic != "jmp":
        return None
    try:
        return int(last.op_str, 16)
    except (TypeError, ValueError):
        return None


def _orphan_region_start(idx: _Index, code: Optional[bytes],
                         tgt: int) -> Optional[tuple[int, int]]:
    """If the record at/below ``tgt`` belongs to an ORPHAN region — a
    run of line records whose lines sit in a gap of the surrounding
    functions' line ranges, physically preceded by a function-ending
    ``ret``/``jmp`` byte — return (region_start_vaddr, region_first_line).

    This is the unified haul discriminator (Rule 125): a hauled head's
    trailing jmp lands in the orphaned remainder at the ORIGINAL source
    position (helping: L1693 block after act_about's ret; clear_unit:
    L234 block after clear_army's ret).  A genuine Rule 42 tail-merge
    jmp lands inside the donor's line-covered BODY (fade_to_palette →
    go_16m_palette L1045, mid-code), which fails the ret-precedes test.
    """
    i = bisect.bisect_right(idx.rec_addrs, tgt) - 1
    if i < 0:
        return None
    # walk back while the line run is tight (contiguous statements)
    while i > 0:
        a_prev, l_prev, f_prev = idx.recs[i - 1]
        a_cur, l_cur, f_cur = idx.recs[i]
        if f_prev != f_cur or not (0 <= l_cur - l_prev <= 2):
            break
        i -= 1
    start_addr, start_line, _f = idx.recs[i]
    # the byte immediately before the region must end a function:
    # ret (C3) or the last byte of a jmp/ret-like stream.  C3 covers
    # every observed case; without code bytes we cannot confirm.
    if code is None:
        return None
    off = start_addr - 0x10000 - 1
    if off < 0 or off >= len(code):
        return None
    if code[off] != 0xC3:
        return None
    return start_addr, start_line


def _load_code() -> Optional[bytes]:
    try:
        from c2.commands.decomp_verify import _load_le_code_and_fixups

        code, _fix = _load_le_code_and_fixups(Path("data/PS.EXE"))
        return code
    except Exception:
        return None


_CODE_CACHE: list = []  # [bytes] once loaded


def detect(
    name: str,
    symbols_json: Path = Path("data/out/symbols.json"),
) -> Optional[MovedCodeHint]:
    """Return a MovedCodeHint when PS's -d1 line table has ZERO records
    inside `name`'s body (the moved-code signature), else None."""
    idx = _index(symbols_json)
    rec = idx.by_name.get(name)
    if rec is None:
        return None
    addr, size = rec
    if size < 5:
        return None
    if _recs_between(idx, addr, addr + size) > 0:
        return None

    prev = _rec_below(idx, addr)
    nxt = _rec_at_or_after(idx, addr + size)
    if prev is None or nxt is None:
        return None
    # Both neighbours must be .c records from the same TU — otherwise the
    # module has no line info at all (.asm / 3rd-party) and zero records
    # is meaningless.
    if not (prev[2].endswith(".c") and prev[2] == nxt[2]):
        return None

    room = nxt[1] - prev[1] - 1
    est = max(3, size // 16)
    kind = "relocated"
    tail_addr = tail_line = None
    after_fn = before_fn = None

    tgt = _trailing_jmp_target(name)
    if tgt is not None:
        trec = _rec_below(idx, tgt + 1)
        if trec is not None and trec[2] == prev[2]:
            tail_line = trec[1]
            tail_addr = tgt
            if not _CODE_CACHE:
                _CODE_CACHE.append(_load_code())
            orphan = _orphan_region_start(idx, _CODE_CACHE[0], tgt)
            if orphan is not None:
                # hauled (either direction): the orphan region IS the
                # original source position.  Suggest: after the function
                # whose records precede the orphan, before the function
                # whose first line follows the orphan's lines.
                kind = "hauled"
                o_addr, o_line = orphan
                p = _rec_below(idx, o_addr)
                if p is not None:
                    j = bisect.bisect_right(idx.func_addrs, p[0]) - 1
                    if j >= 0:
                        after_fn = idx.funcs[j][1]
                # next function by line: first function (by address,
                # within the same record neighbourhood) whose first
                # record line exceeds the orphan's lines.
                # stop the forward walk at the next function symbol —
                # the orphan run never extends into a named function's
                # own body.
                jn = bisect.bisect_right(idx.func_addrs, o_addr)
                next_sym = (idx.func_addrs[jn]
                            if jn < len(idx.func_addrs) else None)
                k = bisect.bisect_left(idx.rec_addrs, o_addr)
                last_line = o_line
                while (k < len(idx.recs)
                       and idx.recs[k][2] == prev[2]
                       and (next_sym is None or idx.recs[k][0] < next_sym)
                       and 0 <= idx.recs[k][1] - last_line <= 2):
                    last_line = idx.recs[k][1]
                    k += 1
                if k < len(idx.recs):
                    j2 = bisect.bisect_right(idx.func_addrs,
                                             idx.recs[k][0]) - 1
                    if j2 >= 0:
                        before_fn = idx.funcs[j2][1]
            elif tail_line < prev[1]:
                kind = "tail-consumed"
            elif tail_line > nxt[1]:
                kind = "hauled"
                j = bisect.bisect_right(idx.func_addrs, tgt) - 1
                if j >= 0:
                    after_fn = idx.funcs[j][1]
                    if j + 1 < len(idx.funcs):
                        before_fn = idx.funcs[j + 1][1]

    return MovedCodeHint(
        name=name, addr=addr, size=size, kind=kind, file=prev[2],
        prev_line=prev[1], next_line=nxt[1], room=room, est_lines=est,
        tail_addr=tail_addr, tail_line=tail_line,
        after_fn=after_fn, before_fn=before_fn,
    )


# ── rendering / JSON ────────────────────────────────────────────────────────

def render(hint: MovedCodeHint) -> str:
    base = (f"ZERO -d1 line records in PS body (optimizer moved this code, "
            f"Rule 125)")
    if hint.kind == "hauled":
        where = f"after {hint.after_fn}" if hint.after_fn else "later in the TU"
        if hint.before_fn:
            where += f" / before {hint.before_fn}"
        return (f"{base}; trailing jmp -> 0x{hint.tail_addr:X} "
                f"(L{hint.tail_line}, vs L{hint.prev_line}..L{hint.next_line} "
                f"here): HAULED head — define this function {where}; "
                f"CallRet+StraightenCode reproduces the layout")
    if hint.kind == "tail-consumed":
        return (f"{base}; trailing jmp goes BACKWARD to L{hint.tail_line} "
                f"(donor tail-merge consumed the body's records): source "
                f"position is fine, fix the donor first")
    room_note = (f"only {hint.room} free source line(s) here vs ~{hint.est_lines} "
                 f"needed — body was NOT written at this position"
                 if hint.room < hint.est_lines else
                 f"{hint.room} free line(s) here could hold it")
    return (f"{base}; no trailing jmp to follow ({room_note}); look for a "
            f"caller whose tail call hauled it (CallRet+StraightenCode) or a "
            f"CloneCode duplicate")


def render_moved_code_hint(name: str) -> Optional[str]:
    hint = detect(name)
    return render(hint) if hint is not None else None


def to_json(hint: Optional[MovedCodeHint]) -> Optional[dict]:
    if hint is None:
        return None
    out = {
        "kind": hint.kind,
        "file": hint.file,
        "address": f"0x{hint.addr:X}",
        "size": hint.size,
        "neighbour_lines": [hint.prev_line, hint.next_line],
        "room_lines": hint.room,
        "est_lines": hint.est_lines,
    }
    if hint.tail_addr is not None:
        out["tail_addr"] = f"0x{hint.tail_addr:X}"
        out["tail_line"] = hint.tail_line
    if hint.after_fn:
        out["define_after"] = hint.after_fn
    if hint.before_fn:
        out["define_before"] = hint.before_fn
    return out


def scan_all(
    symbols_json: Path = Path("data/out/symbols.json"),
) -> list[MovedCodeHint]:
    """Every code function with the zero-line-record signature."""
    idx = _index(symbols_json)
    out = []
    for addr, name, size in idx.funcs:
        h = detect(name, symbols_json)
        if h is not None:
            out.append(h)
    return out


# ── CLI ─────────────────────────────────────────────────────────────────────

def moved_code(
    name: Annotated[
        Optional[str],
        typer.Argument(help="One function (default: scan all)"),
    ] = None,
    as_json: Annotated[
        bool, typer.Option("--json", help="Emit JSON"),
    ] = False,
) -> None:
    """List functions whose PS body carries no -d1 line records (the
    moved-code signature, Rule 125): the peephole optimizer relocated
    the body, so source-definition position may differ from symbol
    address order."""
    if name:
        h = detect(name)
        if h is None:
            typer.echo(f"{name}: line records present (not moved)")
            raise typer.Exit(0)
        if as_json:
            typer.echo(json.dumps({"name": name, **to_json(h)}, indent=2))
        else:
            typer.echo(f"{name}: {render(h)}")
        raise typer.Exit(0)

    hints = scan_all()
    if as_json:
        typer.echo(json.dumps(
            [{"name": h.name, **to_json(h)} for h in hints], indent=2))
        raise typer.Exit(0)
    for h in hints:
        extra = ""
        if h.kind == "hauled" and h.after_fn:
            extra = f" -> define after {h.after_fn}"
        typer.echo(f"  {h.kind:13s} {h.size:5d}b  {h.name:32s} {h.file}{extra}")
    typer.echo(f"\n{len(hints)} function(s) with the moved-code signature")
