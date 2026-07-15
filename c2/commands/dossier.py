"""`c2 dossier <fn>` -- single-function focused view fusing FIVE data
streams + IR tree into one pane that lets you reason about how the
original C source most likely looked:

  1. PS asm bytes     (the ground-truth target -- byte-exact goal)
  2. PS -d1 line info (PS's source line numbers, anchoring asm offsets
                       to logical source lines -- structure ground truth)
  3. RC source + asm  (our current decomp source, freshly built, with
                       its own -d1 line marks for line<->offset)
  4. Mac PPC decompile (AST-cleaned Ghidra C from the Mac port --
                       cross-compiler source-shape oracle)
  5. Windows decompile (MSVC 4.0 /Od Ghidra C from CAESAR2.EXE -- the
                       SAME engine source, x86 + unoptimized => the most
                       legible source-shape oracle: named/typed params,
                       named globals, every statement explicit)
  +  binir IR-tree   (semantic operations recovered from PS+RC asm)
  (+ optional 6th: PS.EXE Ghidra decompile, the Watcom-target C, --ghidra)

Layout (top → bottom):

  HEADER       function name, sizes, raw byte-diff stat
  VERDICT      structural alignment / byte residue / frame / callee
               saves / suggested class (structural vs allocator)
  STREAM       per-line-mark-boundary table (asm-offset aligned)
               showing PS#, RC#, branch tags, PS-IR, RC-IR, RC source
  DETAIL       deeper drill on diverging rows (binir comparison)
  MAC          full AST-cleaned Mac decompile (source-shape oracle)
  WIN          Windows MSVC /Od decompile (x86 source-shape oracle)
  LEVER NOTES  any in-source `/* PROBE: ... */` / `/* NOTE: ... */`
               comments in the function's lexical span (what's tried)

The asm-offset axis is the only one shared by PS and RC (Mac is PPC,
no line info).  PS source-line numbers refer to the LOST original C
source; RC source-line numbers refer to our current `decomp/src/*.c`.
"""
from __future__ import annotations

import bisect
import json
from pathlib import Path
from typing import Annotated, Optional

import typer


_SYMS = Path("data/out/symbols.json")
_CODE = Path("data/out/le_code.bin")
_DECOMP = Path("decomp")


# ── per-side line walkers ─────────────────────────────────────────────


def _ps_func_records(symbols_json: Path, name: str):
    """Returns (start, end, mod_idx, file, recs, code_bytes_in_func).

    `recs` are sorted line records, each {line, offset, file} where
    offset is ABSOLUTE (and >= start, < end)."""
    d = json.loads(symbols_json.read_text())
    codes = sorted(
        (s for s in d["symbols"]
         if s["kind"].endswith("code") and s["segment"] == 1),
        key=lambda s: s["offset"],
    )
    by_name = {s["name"]: i for i, s in enumerate(codes)}
    if name not in by_name:
        return None
    i = by_name[name]
    start = codes[i]["offset"]
    end = (codes[i + 1]["offset"] if i + 1 < len(codes)
           else start + 0x4000)
    mod = codes[i]["module_index"]
    recs = sorted(
        (r for r in d["line_numbers"]
         if r["module_index"] == mod and start <= r["offset"] < end),
        key=lambda r: r["offset"],
    )
    le_code = _CODE.read_bytes()[start:end]
    file = recs[0]["file"] if recs else "?"
    return start, end, mod, file, recs, le_code


def _load_le_code_and_fixups_for_dossier(out_exe: Path):
    from c2.commands.decomp_verify import _load_le_code_and_fixups
    return _load_le_code_and_fixups(out_exe)


def _rc_func_records(out_exe: Path, out_map: Path, name: str):
    """Returns (start, end, file, recs, code_bytes_in_func)."""
    from c2.commands.decomp_verify import _parse_map, _load_le_code_and_fixups
    from c2.parsers.debug import parse_watcom_debug, build_addr_info_base_map

    syms = _parse_map(out_map)
    mangled = name + "_"
    if mangled not in syms:
        return None
    start = syms[mangled]
    items = sorted(syms.items(), key=lambda kv: kv[1])
    nx = None
    for i, (nm, off) in enumerate(items):
        if nm == mangled and i + 1 < len(items):
            nx = items[i + 1][1]
            break
    end = nx if nx is not None else start + 0x4000

    info = parse_watcom_debug(out_exe)
    addr_base = build_addr_info_base_map(info.addr_info)
    mod_file = {m.index: Path(m.name.replace("\\", "/")).name
                for m in info.modules}
    recs = []
    for mod_idx, segments in info.line_numbers.items():
        for seg in segments:
            base = addr_base.get(seg.addr_info_offset, 0)
            for le in seg.entries:
                flat = base + le.code_offset
                if start <= flat < end:
                    recs.append({
                        "line": le.line,
                        "offset": flat,
                        "file": mod_file.get(mod_idx, "?"),
                    })
    recs.sort(key=lambda r: r["offset"])
    file = recs[0]["file"] if recs else "?"
    code_bin, _ = _load_le_code_and_fixups(out_exe)
    le_code = code_bin[start:end]
    return start, end, file, recs, le_code


# ── instruction-by-instruction asm walker ─────────────────────────────


def _disasm_func(code: bytes, base: int):
    """Yield (abs_off, size, mnemonic, op_str)."""
    from capstone import CS_ARCH_X86, CS_MODE_32, Cs
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for ins in md.disasm(code, base):
        yield ins.address, ins.size, ins.mnemonic, ins.op_str


def _branch_tag(mnemonic: str, op_str: str) -> str:
    if mnemonic == "call":
        return "call"
    if mnemonic == "ret":
        return "ret"
    if mnemonic == "jmp":
        return "jmp"
    if mnemonic.startswith("j"):
        return mnemonic
    return ""


# ── prologue / frame summary ──────────────────────────────


_PUSH_REGS = ["eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"]


def _prologue_summary(code: bytes) -> tuple[list[str], int]:
    """Walk the function's prologue (consecutive push-reg + optional
    sub esp,imm) and return (pushed_regs_in_order, sub_esp_amount).

    Stops at the first non-prologue instruction.  Recognises:
      0x50..0x57            push eax..edi
      0x83 0xec NN          sub esp, imm8
      0x81 0xec NN NN NN NN sub esp, imm32
      0x55 + 0x89 0xe5      push ebp + mov ebp, esp (frame setup)
      0x66 + push           operand-size override (rare)
    """
    pushed: list[str] = []
    i = 0
    sub_esp = 0
    while i < len(code):
        b = code[i]
        if 0x50 <= b <= 0x57:
            pushed.append(_PUSH_REGS[b - 0x50])
            i += 1
            continue
        # mov ebp, esp (frame setup after push ebp)
        if (b == 0x89 and i + 1 < len(code)
                and code[i + 1] == 0xe5
                and pushed and pushed[-1] == "ebp"):
            i += 2
            continue
        if b == 0x83 and i + 2 < len(code) and code[i + 1] == 0xec:
            sub_esp = code[i + 2]
            break
        if b == 0x81 and i + 5 < len(code) and code[i + 1] == 0xec:
            sub_esp = int.from_bytes(code[i + 2:i + 6], "little")
            break
        break
    return pushed, sub_esp


# ── binir per-row recovery ──────────────────────────────────


def _binir_for_code(code: bytes):
    """Return list[RecoveredOp] for a function body.

    Op offsets are FUNCTION-RELATIVE (matching our line-mark offsets).
    """
    from c2.commands.decomp_verify import _disasm_for_diff
    from c2 import binir
    insns = _disasm_for_diff(code)
    try:
        return binir.recover(insns)
    except Exception:
        return []


def _binir_in_span(ops, lo_rel: int, hi_rel: int) -> list:
    """Return ops whose offset lies in [lo_rel, hi_rel)."""
    return [o for o in ops if lo_rel <= o.offset < hi_rel]


def _binir_short(ops) -> str:
    """Short tag for an op list: kinds joined, repeated kinds suffixed xN."""
    if not ops:
        return ""
    counts: dict[str, int] = {}
    order: list[str] = []
    for o in ops:
        if o.kind not in counts:
            order.append(o.kind)
        counts[o.kind] = counts.get(o.kind, 0) + 1
    parts = []
    for k in order:
        n = counts[k]
        parts.append(f"{k}x{n}" if n > 1 else k)
    return " ".join(parts)


# ── source extractor ──────────────────────────────────────────────────


def _read_source_lines(file: str, decomp_dir: Path) -> dict[int, str]:
    for sub in ("src", "include"):
        p = decomp_dir / sub / file
        if p.exists():
            return {i + 1: ln.rstrip("\n")
                    for i, ln in enumerate(p.read_text().splitlines())}
    return {}


# ── stream renderer ──────────────────────────────────────────────────


def _line_at(recs, abs_off: int):
    """Return (line, file) of the most recent line mark at or before abs_off,
    or (None, None) if abs_off precedes the first mark."""
    if not recs:
        return None, None
    # recs sorted by offset
    offs = [r["offset"] for r in recs]
    j = bisect.bisect_right(offs, abs_off) - 1
    if j < 0:
        return None, None
    return recs[j]["line"], recs[j]["file"]


# ── sibling-prologue scan ─────────────────────────────────


def _byte_exact_set_with_prologues(prologue_bytes: int = 16):
    """Return ``[(name, address, size, prologue_hex), ...]`` for every
    byte-exact function in the current corpus cache.

    Reads ``.c2-cache/verify.json`` (the corpus snapshot from the last
    ``decomp-verify`` run) and slices PS bytes from
    ``data/out/le_code.bin``.  Returns ``[]`` if either is missing.
    """
    cache = Path(".c2-cache/verify.json")
    code_path = Path("data/out/le_code.bin")
    syms_path = Path("data/out/symbols.json")
    if not (cache.exists() and code_path.exists() and syms_path.exists()):
        return []
    try:
        doc = json.loads(cache.read_text())
        syms = json.loads(syms_path.read_text())
    except json.JSONDecodeError:
        return []
    # verify.json uses LE VAs (0x10000 + le_code offset); le_code.bin is the
    # raw code section (offset 0).  Use symbols.json's name->offset map
    # directly so we don't have to track the base across rebuilds.
    name_to_off = {
        s["name"]: s["offset"]
        for s in syms["symbols"]
        if s["kind"].endswith("code") and s["segment"] == 1
    }
    code = code_path.read_bytes()
    out = []
    for f in doc.get("functions", []):
        if not f.get("exact"):
            continue
        nm = f.get("name")
        size = f.get("size")
        if not (nm and size):
            continue
        off = name_to_off.get(nm)
        if off is None:
            continue
        n = min(prologue_bytes, size, len(code) - off)
        if n <= 0:
            continue
        out.append((nm, off, size, code[off:off + n].hex()))
    return out


def _find_prologue_siblings(target_code: bytes, prologue_len: int = 16,
                            min_match: int = 8):
    """Return byte-exact functions whose first bytes match the target's by
    at least ``min_match`` bytes.

    Returns ``[(name, address, size, match_bytes), ...]`` sorted by
    match length descending (longest match first).
    """
    candidates = _byte_exact_set_with_prologues(prologue_len)
    if not candidates:
        return []
    tgt_hex = target_code[:prologue_len].hex()
    matches = []
    for name, off, size, hexbytes in candidates:
        common = 0
        for k in range(min(len(tgt_hex), len(hexbytes))):
            if tgt_hex[k] != hexbytes[k]:
                break
            common += 1
        common_bytes = common // 2
        if common_bytes >= min_match:
            matches.append((name, off, size, common_bytes))
    matches.sort(key=lambda t: -t[3])
    return matches


def _stream_rows(ps_start, ps_end, ps_recs, ps_code,
                 rc_start, rc_end, rc_recs, rc_code):
    """Emit one row per line-mark boundary on EITHER side.

    Algorithm: the function-relative offsets where each side issues a
    line mark are merged into a single sorted boundary list (annotated
    with which side(s) own each boundary).  Between consecutive
    boundaries we know:
       - PS's current source line (= most recent PS mark at or before)
       - RC's current source line (= most recent RC mark at or before)
       - the byte span (same number on each side since offsets are
         function-relative)

    When codegen matches byte-for-byte, the PS and RC mark offsets
    coincide and rows show paired transitions.  When they diverge by
    K bytes, the side that emits 'extra' marks (typically because the
    user split a single PS source line onto two lines, or vice versa)
    gets a row pair where its line# advances while the other side's
    stays put -- the asymmetry visually localises the source-shape
    divergence.

    Returns list of dicts {boundary_off, span, ps_line, rc_line,
                           ps_advanced, rc_advanced, ps_tags, rc_tags}.
    """
    ps_func_size = ps_end - ps_start
    rc_func_size = rc_end - rc_start
    ps_marks = [(r["offset"] - ps_start, r["line"]) for r in ps_recs]
    rc_marks = [(r["offset"] - rc_start, r["line"]) for r in rc_recs]
    # union of boundary offsets (each tagged 'P', 'R', or 'B')
    bset: dict[int, str] = {}
    for off, _ in ps_marks:
        bset[off] = "P"
    for off, _ in rc_marks:
        bset[off] = "B" if off in bset else "R"
    # always include function-end on each side as a stop
    stop = max(ps_func_size, rc_func_size)
    bset.setdefault(stop, bset.get(stop, "E"))
    bounds = sorted(bset)

    ps_off_to_line = dict(ps_marks)
    rc_off_to_line = dict(rc_marks)

    def _cur_line(marks_off_to_line, sorted_offs, at):
        j = bisect.bisect_right(sorted_offs, at) - 1
        if j < 0:
            return None
        return marks_off_to_line[sorted_offs[j]]

    ps_sorted = sorted(ps_off_to_line)
    rc_sorted = sorted(rc_off_to_line)

    rows = []
    for k in range(len(bounds) - 1):
        off = bounds[k]
        nxt = bounds[k + 1]
        span = nxt - off
        owner = bset[off]
        ps_line = _cur_line(ps_off_to_line, ps_sorted, off)
        rc_line = _cur_line(rc_off_to_line, rc_sorted, off)
        ps_adv = owner in ("P", "B")
        rc_adv = owner in ("R", "B")
        # branch tags inside this span, clamped to each side's func
        ps_tags = (_tags_in(ps_code, ps_start, off, min(nxt, ps_func_size))
                   if off < ps_func_size else [])
        rc_tags = (_tags_in(rc_code, rc_start, off, min(nxt, rc_func_size))
                   if off < rc_func_size else [])
        rows.append({
            "off": off, "span": span,
            "ps_line": ps_line, "rc_line": rc_line,
            "ps_adv": ps_adv, "rc_adv": rc_adv,
            "ps_tags": ps_tags, "rc_tags": rc_tags,
            "owner": owner,
        })
    return rows


def _tags_in(code, base, lo_rel, hi_rel):
    """Branch/call tags for the function-relative span [lo_rel, hi_rel)."""
    out = []
    for off, sz, mn, op in _disasm_func(code[lo_rel:hi_rel], base + lo_rel):
        t = _branch_tag(mn, op)
        if t:
            out.append(t)
    return out


def _fmt_tags(tags: list[str], cap: int = 4) -> str:
    if not tags:
        return ""
    return " ".join(tags[:cap]) + (" …" if len(tags) > cap else "")


# ── main entry ───────────────────────────────────────────────────────


# ── focused view (the default since 2026-06-25): bisect mode ───────────
#
# Replaces the old "every stream at once" firehose (kept behind --full).
# Each invocation shows the CURRENT first PS↯RC divergence with all
# oracles aligned to it, plus the delta vs git HEAD.  Re-run after every
# edit to converge on byte-exact.  Stateless -- git is the session log.
#
# Design discussion: AGENTS.md + the chat handover 2026-06-25.


def _disasm_around(code: bytes, base: int, target_rel: int,
                   ctx_before: int = 5, ctx_after: int = 5,
                   recs: Optional[list] = None) -> list[tuple]:
    """Disassemble ``code`` and return ~(ctx_before+1+ctx_after) insn rows
    centered on the insn whose relative offset is the smallest one >=
    target_rel.  Each row = (rel_off, mnem, op_str, line_or_None).

    ``recs`` is the PS or RC line-record list ({offset, line, ...}); if
    given, the source line at each insn is computed by walking the records.
    """
    insns = list(_disasm_func(code, base))
    if not insns:
        return []
    # find insn covering target_rel
    rel_offs = [a - base for (a, _sz, _mn, _op) in insns]
    k_target = 0
    for k, ro in enumerate(rel_offs):
        if ro >= target_rel:
            k_target = k
            break
    else:
        k_target = len(insns) - 1
    lo = max(0, k_target - ctx_before)
    hi = min(len(insns), k_target + ctx_after + 1)
    # line-at lookup
    line_at = None
    if recs:
        abs_offs = sorted(r["offset"] for r in recs)
        line_by_off = {r["offset"]: r["line"] for r in recs}
        last_emitted = [None]

        def _la(abs_off: int) -> Optional[int]:
            cur = None
            for o in abs_offs:
                if o <= abs_off:
                    cur = o
                else:
                    break
            if cur is None:
                return None
            ln = line_by_off[cur]
            if ln == last_emitted[0]:
                return None
            last_emitted[0] = ln
            return ln
        line_at = _la
    out = []
    for k in range(lo, hi):
        a, _sz, mn, op = insns[k]
        ln = line_at(a) if line_at else None
        out.append((a - base, mn, op, ln))
    return out, k_target - lo  # also return relative index of target row


def _ps_call_anchor(ps_calls: list, first_diff_rel: int) -> Optional[tuple]:
    """Return the nearest PS call entry ``(name, ps_line, rel_off)`` at or
    BEFORE the given relative offset, or None if no call precedes it."""
    best = None
    for entry in ps_calls:
        _nm, _ln, ro = entry
        if ro <= first_diff_rel:
            best = entry
        else:
            break
    return best


def _match_oracle_anchor(ps_calls: list, oracle_src: str,
                         anchor_idx: int) -> Optional[int]:
    """Given the PS call sequence, the Mac/Win source text, and the index of
    the anchor PS call, return the line number in the oracle source where
    the matching call occurs.  None if no match.
    """
    if anchor_idx is None or anchor_idx < 0:
        return None
    oracle_calls = _mac_call_sequence(oracle_src)  # same scanner for Mac/Win
    matches = _match_call_sequences(ps_calls, oracle_calls)
    mi = matches.get(anchor_idx)
    if mi is None or mi >= len(oracle_calls):
        return None
    return oracle_calls[mi][1]


def _oracle_excerpt(src: str, lineno: Optional[int], ctx: int = 6) -> list[str]:
    """Return ``[lines...]`` from ``src`` covering [lineno-ctx, lineno+ctx],
    prefixed with the line number for easy reading.  If lineno is None
    return [].
    """
    if lineno is None:
        return []
    lines = src.splitlines()
    if not lines:
        return []
    lo = max(1, lineno - ctx)
    hi = min(len(lines), lineno + ctx)
    out = []
    for i in range(lo, hi + 1):
        marker = "→ " if i == lineno else "  "
        out.append(f"     {marker}L{i:<5} {lines[i-1]}")
    return out


def _read_oracle_cached(name: str, kind: str) -> Optional[str]:
    """Fetch (force) the Mac or Windows decompile of ``name`` when forced.

    ``kind`` is 'mac' or 'win'.  Only called from the focused view when the
    user passed ``--mac``/``--win`` (force) AND the per-fn decompile is not
    already on disk.

    * ``win``: returns RAW MSVC /Od C (this build has no post-processor).
    * ``mac``: returns the PEF-indirection-cleaned C (mac's value-add); the
      raw decompile is fetched via ``mac.decompile_cached`` (the shared
      cache-or-fetch primitive, symmetric with ``c2win.decompile_cached``) so
      a miss actually fetches instead of no-op'ing, then AST-cleaned at read.
      Absence surfaces as None.

    Returns the C source text, or None.
    """
    if kind == "mac":
        try:
            import mac as macmod
            # mac.decompile_clean is cache-aware: raw via decompile_cached
            # (instant on hit, opens JVM on miss) + AST cleaning at read.
            # Raises ValueError if the function is absent from the Mac build.
            return macmod.decompile_clean(name)
        except Exception:
            return None
    if kind == "win":
        try:
            import c2win
            # c2win.decompile_cached is the full cache-or-fetch path: cache
            # hit returns instantly (no JVM); cache miss opens the project,
            # decompiles, and persists the result.  Do NOT pre-filter on the
            # cache file existing -- that guard (removed) returned None on a
            # miss and silently defeated `--win`, making the force flag a no-op.
            return c2win.decompile_cached(name)
        except Exception:
            return None
    return None


def _read_oracle_from_disk(name: str, kind: str) -> Optional[str]:
    """Read the cached oracle straight from the per-fn cache file on disk,
    bypassing the Ghidra bridge entirely (used by --bisect to avoid the JVM).
    For Mac an empty file is the recorded known-miss sentinel; for Win likewise.
    Returns the C source text, or None.
    """
    if kind == "mac":
        # Raw Ghidra C cached at `.c2-cache/mac/decompile/` (the shared
        # cache-or-fetch dir, symmetric with win's `.c2-cache/win/decompile/`).
        # The bisect path returns the RAW text (no PEF cleaning) to stay JVM-free
        # even when the cleaner would need refreshing; the force path
        # (`_read_oracle_cached`) returns the cleaned form.
        p = Path(".c2-cache/mac/decompile") / f"{name}.c"
        if p.exists():
            t = p.read_text(errors="replace")
            return t if t.strip() else None
        return None
    if kind == "win":
        p = Path(".c2-cache/win/decompile") / f"{name}.c"
        if p.exists():
            t = p.read_text(errors="replace")
            return t if t.strip() else None
        return None
    return None


def _emit_focused(name: str, symbols_json: Path, decomp_dir: Path,
                  no_mac: bool, force_mac: bool,
                  no_win: bool, force_win: bool) -> None:
    """The focused per-function view: HEAD-delta header, FIRST DIVERGENCE
    with PS asm + RC asm + RC source + Mac/Win oracle at the nearest call
    anchor, IR delta interpretation, routing footer.

    Run after every edit to converge on byte-exact.  --full restores the
    old all-streams firehose.
    """
    from c2 import bisect as _bs
    from c2.commands.decomp_verify import (
        _build_all, PS_CFLAGS, _DEFAULT_IMAGE, _compare_bytes,
        _build_diff_rows, _load_le_code_and_fixups,
    )
    from c2.parsers.exe import parse_exe
    from c2.commands.fixups import parse_le_fixups

    # ── 1. PS side ────────────────────────────────────────────────
    ps = _ps_func_records(symbols_json, name)
    if ps is None:
        typer.secho(f"[!] {name!r} not in PS code symbols", fg="red")
        raise typer.Exit(1)
    ps_start, ps_end, _mod, ps_file, ps_recs, ps_code = ps
    if not ps_recs:
        typer.secho(f"[!] {name!r}: no PS line records (asm module?)",
                    fg="red")
        raise typer.Exit(1)
    ps_size = ps_end - ps_start

    # ── 2. RC side (fresh build) ───────────────────────────────────
    src_dir = decomp_dir / "src"
    inc_dir = decomp_dir / "include"
    ok, out, _work, out_exe, out_map = _build_all(
        src_dir, inc_dir, _DEFAULT_IMAGE, PS_CFLAGS, use_cache=True,
    )
    if not ok:
        typer.secho("[!] build failed:\n" + out, fg="red")
        raise typer.Exit(1)
    rc = _rc_func_records(out_exe, out_map, name)
    if rc is None:
        typer.secho(f"[!] {name!r} not in RC map (decl/build mismatch?)",
                    fg="red")
        raise typer.Exit(1)
    rc_start, rc_end, rc_file, rc_recs, rc_code = rc
    rc_size = rc_end - rc_start

    # ── 3. byte diff + shape distance (current = WT) ────────────────────
    _, _bw, le_ps = parse_exe(Path("data/PS.EXE"))
    ps_fm, _ = parse_le_fixups(
        Path("data/PS.EXE"), le_ps.le_offset, le_ps.page_size,
        le_ps.num_pages, le_ps.objects[0].num_pages,
        le_ps.objects[1].num_pages,
    )
    ps_fix: set[int] = set()
    for off in ps_fm:
        for k in range(4):
            ps_fix.add(off + k)
    _, rc_fix = _load_le_code_and_fixups(out_exe)
    n = min(len(ps_code), len(rc_code))
    diffs = _compare_bytes(
        ps_code[:n], rc_code[:n], ps_start, rc_start, ps_fix, rc_fix,
    )
    bdiff = len(diffs)
    if len(ps_code) != len(rc_code):
        bdiff += abs(len(ps_code) - len(rc_code))
    first_diff_rel = diffs[0] if diffs else None

    # ── 4. shape distance + binir ops ──────────────────────────────
    # THE JUDGE METRIC comes from the CANONICAL shared helper
    # (bisect._verify_function_at -> decomp_verify._recon_bundle_for_json):
    # identical inputs and code path to `c2 decomp-verify` (PS-sized
    # recomp slice, RC-extent audit slice, the build's own -d1 line
    # lookup, dual-marks run ledger feeding the ir layer).  The old
    # dossier-local computation used the byte-diff-aligned binir count,
    # which drifts past the first length-changing diff and could report
    # ir IMPROVING while the verifier's ir worsened (the 2026-07-09
    # contradiction report).  binir/rows below are for the DETAIL views
    # only, never for the judge metric.
    from c2.regalloc.seat_recon import fmt_shape_layers as _flyr
    from c2.commands.binir_shape_hints import detect as _bdet
    line_map = {r["offset"]: r["line"] for r in ps_recs}
    rows, _ = _build_diff_rows(
        ps_code, ps_start, rc_code, rc_start, ps_fix, rc_fix, line_map,
    )
    binir = _bdet(rows)
    _canon = _bs._verify_function_at(name, out_exe, out_map, symbols_json)
    sd = (_canon or {}).get("shape")
    if _canon is not None:
        bdiff = _canon["byte_diff"]
        first_diff_rel = _canon["first_diff"]
    if sd is None:
        typer.secho("[!] canonical shape computation failed (bisect."
                    "_verify_function_at) -- metrics would not match "
                    "decomp-verify; aborting rather than showing "
                    "divergent numbers", fg="red")
        raise typer.Exit(1)

    # ── 5. HEAD baseline (bisect cache) ────────────────────────────
    sha = _bs.current_sha()
    dirty = _bs.is_dirty([src_dir, inc_dir])
    baseline = None
    if sha is not None:
        baseline = _bs.get_baseline(name, sha=sha, decomp_dir=decomp_dir,
                                    symbols_json=symbols_json)
    current = {
        "byte_diff": bdiff,
        "first_diff": first_diff_rel,
        "shape": sd,
        "ps_size": ps_size,
        "rc_size": rc_size,
    }
    # When clean WT, current == baseline by definition; cache it if absent.
    if sha is not None and not dirty and baseline is None:
        cache = _bs.load_cache(name)
        cache[sha] = {**current, "ts": int(__import__("time").time())}
        _bs.save_cache(name, cache)
        baseline = cache[sha]

    # ── 6. HEADER ─────────────────────────────────────────────────
    typer.secho(
        f"# {name}    PS {ps_file} ({ps_size}b)   ⇆   "
        f"RC {rc_file} ({rc_size}b)",
        fg="cyan", bold=True,
    )
    for ln in _bs.format_delta_block(name, sha, baseline, current, dirty):
        typer.echo(ln)

    if bdiff == 0:
        # Byte-exact: brief verdict + line-compare summary if available.
        typer.echo()
        typer.secho("   ✓ byte-exact", fg="green", bold=True)
        typer.secho(
            "\n   note: --full restores the old all-streams firehose; "
            "`c2 line-compare " + name + "` for Hard Rule #8 shape check.",
            dim=True)
        return

    # ── 7. shape line + classification + work-order ────────────────────
    typer.echo()
    color = "green" if sd["shape"] == 0 else "yellow"
    typer.secho(f"   shape vs PS:     {_flyr(sd)}   "
                f"→ fix-next: {sd['fix_next']}", fg=color)
    # win mapping (cheap)
    try:
        from c2.win_bytes import win_hint as _win_hint, tu_of as _tu_of
        _wh = _win_hint(name, _tu_of(name))
        if _wh.get("available"):
            typer.secho(
                f"   win:             CAESAR2.EXE {_wh['win_va']} "
                f"({_wh['confidence']})", fg="cyan")
    except Exception:
        pass
    # tail-merge donor block warning
    try:
        from c2.commands.decomp_verify import (
            _scan_tail_merge_donor, _donor_blocking_status,
        )
        tm = _scan_tail_merge_donor(ps_code, ps_start, is_vaddr=False)
        if tm is not None:
            ds = _donor_blocking_status(tm.donor_name)
            if ds == "diff":
                typer.secho(
                    f"   ⚠ DONOR-BLOCKED by {tm.donor_name} -- fix the "
                    "donor first; this residue is downstream.", fg="red")
            elif ds == "missing":
                typer.secho(
                    f"   ⚠ donor {tm.donor_name} missing/stub -- decompile "
                    "it first.", fg="yellow")
    except Exception:
        pass
    # const-audit
    try:
        from c2.commands.decomp_verify import _const_audit_for_json
        ca = _const_audit_for_json(
            ps_code, rc_code, ps_start, rc_start, ps_fix, rc_fix)
        if ca:
            bits = []
            for ch, lbl in (("cmp_threshold", "cmp-boundary"),
                            ("eq", "eq"), ("plain", "plain")):
                if ch in ca:
                    ps_only = ",".join(
                        f"{k:#x}" for k in sorted(ca[ch]["ps_only"]))
                    rc_only = ",".join(
                        f"{k:#x}" for k in sorted(ca[ch]["rc_only"]))
                    bits.append(
                        f"{lbl}[PS:{ps_only or '-'} "
                        f"RC:{rc_only or '-'}]")
            typer.secho(
                f"   const-audit:     ✗ {ca['n_div']} divergent "
                f"constant(s)  " + "  ".join(bits), fg="yellow")
        else:
            typer.secho("   const-audit:     ✓ clean (regalloc-invariant)",
                        fg="green")
    except Exception:
        pass

    # ── 8. FIRST DIVERGENCE block ──────────────────────────────────
    typer.echo()
    if first_diff_rel is None:
        typer.secho(
            "## NO MASKED-BYTE DIVERGENCE  (residue is length/fixup only)",
            bold=True)
        typer.secho(
            "   PS and RC bytes match after fixup masking, but lengths "
            "differ -- likely an extra/missing tail-merge edge or "
            "prologue/epilogue mismatch.", dim=True)
        typer.echo(f"   PS size {ps_size}b   RC size {rc_size}b   "
                   f"Δ {rc_size - ps_size:+d}b")
        return

    # PS source line at first-diff offset (Hard Rule #4 anchor)
    ps_ln_at = None
    cur = None
    for r in ps_recs:
        if r["offset"] - ps_start <= first_diff_rel:
            cur = r
        else:
            break
    if cur is not None:
        ps_ln_at = cur["line"]
    rc_ln_at = None
    cur = None
    for r in rc_recs:
        if r["offset"] - rc_start <= first_diff_rel:
            cur = r
        else:
            break
    if cur is not None:
        rc_ln_at = cur["line"]

    typer.secho(
        f"## FIRST DIVERGENCE at +{first_diff_rel:#x}  "
        f"(PS L{ps_ln_at or '?'} / RC L{rc_ln_at or '?'})",
        bold=True)

    # PS asm context
    ps_dis, ps_target_idx = _disasm_around(
        ps_code, ps_start, first_diff_rel,
        ctx_before=4, ctx_after=4, recs=ps_recs)
    rc_dis, rc_target_idx = _disasm_around(
        rc_code, rc_start, first_diff_rel,
        ctx_before=4, ctx_after=4, recs=rc_recs)

    typer.echo("   PS asm  (context around first divergence):")
    for i, (off, mn, op, ln) in enumerate(ps_dis):
        marker = "→" if i == ps_target_idx else " "
        ln_col = f"L{ln}" if ln else "   "
        line = f"     {marker} +{off:>#5x}  {ln_col:<6} {mn:<6} {op}"
        if i == ps_target_idx:
            typer.secho(line, fg="red")
        else:
            typer.echo(line)

    typer.echo("   RC asm  (context around first divergence):")
    for i, (off, mn, op, ln) in enumerate(rc_dis):
        marker = "→" if i == rc_target_idx else " "
        ln_col = f"L{ln}" if ln else "   "
        line = f"     {marker} +{off:>#5x}  {ln_col:<6} {mn:<6} {op}"
        if i == rc_target_idx:
            typer.secho(line, fg="red")
        else:
            typer.echo(line)

    # RC source context
    rc_src = _read_source_lines(rc_file, decomp_dir)
    if rc_ln_at and rc_src:
        lo = max(1, rc_ln_at - 3)
        hi = min(len(rc_src), rc_ln_at + 3)
        typer.echo(f"   RC source  ({rc_file} L{lo}..L{hi}):")
        for i in range(lo, hi + 1):
            text = rc_src.get(i, "")
            marker = "→" if i == rc_ln_at else " "
            line = f"     {marker} L{i:<5} {text}"
            if i == rc_ln_at:
                typer.secho(line, fg="yellow")
            else:
                typer.echo(line)

    # ── 9. Mac/Win oracles at the nearest call anchor ──────────────────
    ps_calls = _ps_call_sequence(ps_code, ps_start, ps_recs)
    anchor = _ps_call_anchor(ps_calls, first_diff_rel)
    anchor_idx = None
    if anchor is not None:
        anchor_idx = ps_calls.index(anchor)
        ac_name, ac_line, ac_off = anchor
        typer.echo(
            f"   nearest call anchor:  {ac_name}() at PS L{ac_line}  "
            f"(+{ac_off:#x})")
    else:
        typer.secho(
            "   nearest call anchor:  (function entry -- no prior call; "
            "showing oracle entry instead)", dim=True)

    def _emit_oracle(label: str, src: Optional[str], cmd_hint: str) -> None:
        if src is None:
            typer.secho(
                f"   {label}:  not cached -- `{cmd_hint}` to fetch", dim=True)
            return
        oracle_ln = _match_oracle_anchor(ps_calls, src, anchor_idx)
        if oracle_ln is None:
            # No anchor (function-entry first-diff or no matching call):
            # show the oracle's HEAD (function entry) so the reader sees
            # types/locals at least.
            typer.echo(f"   {label}  (function entry; no call anchor):")
            for line in _oracle_excerpt(src, lineno=4, ctx=4):
                typer.secho(line, dim=True)
        else:
            typer.echo(
                f"   {label}  (around L{oracle_ln}, anchored at "
                f"{anchor[0] if anchor else '?'}() call):")
            for line in _oracle_excerpt(src, oracle_ln, ctx=4):
                typer.secho(line, dim=True)

    if not no_mac:
        mac_src = _read_oracle_from_disk(name, "mac")
        if mac_src is None and force_mac:
            mac_src = _read_oracle_cached(name, "mac")
        _emit_oracle("Mac PPC oracle", mac_src,
                     f"c2 dossier {name} --mac")

    if not no_win:
        win_src = _read_oracle_from_disk(name, "win")
        if win_src is None and force_win:
            win_src = _read_oracle_cached(name, "win")
        _emit_oracle("Win MSVC /Od oracle", win_src,
                     f"c2 dossier {name} --win")

    # ── 10. IR delta interpretation at the first divergence ─────────────
    if binir and binir.divergences:
        # find the divergence at ps_ln_at
        for d in binir.divergences:
            if d.line == ps_ln_at:
                typer.echo()
                typer.secho(
                    f"   IR delta at L{d.line}:  {d.summary}", fg="yellow")
                break

    # ── 11. Routing footer ───────────────────────────────────────
    typer.echo()
    # donor-block takes precedence: working a blocked function is wasted.
    donor_redirect = None
    try:
        from c2.commands.decomp_verify import (
            _scan_tail_merge_donor, _donor_blocking_status,
        )
        tm = _scan_tail_merge_donor(ps_code, ps_start, is_vaddr=False)
        if tm is not None and _donor_blocking_status(tm.donor_name) == "diff":
            donor_redirect = tm.donor_name
    except Exception:
        pass
    if donor_redirect is not None:
        typer.secho(
            f"   → next: this body is DONOR-BLOCKED -- run `c2 dossier "
            f"{donor_redirect}` and fix THAT first; the residue here "
            "cascades from it.", fg="red")
    else:
        fn_layer = sd.get("fix_next", "ir")
        route_msg = {
            "ir": "the recovered SHAPE diverges -- fix the structure first "
                  "(read Mac+Win oracle above; `c2 mac-decompile` for the "
                  "full body if needed)",
            "width": "a local's type/signedness diverges -- "
                     f"`c2 win-verify -v {name}` first (MSVC /Od shows the "
                     "declared width: movsx = signed char, xor+mov = "
                     "unsigned), then the type fix",
            "spill": f"frame/live-set divergence -- `c2 win-verify -v {name}` "
                     "FIRST: the MSVC /Od frame exposes PS's true local set "
                     "(write-only locals, de-invented precomputes) that "
                     "Watcom canonicalizes away; then add/de-invent named "
                     "locals to match PS's spill set",
            "seat": f"register-identity tie -- `c2 win-verify -v {name}` "
                    "FIRST (a Watcom-invisible shape defect -- invented "
                    "temp, write-only local, guard nesting -- often owns "
                    "the seat; proven 5x on the map.c elastic family), "
                    f"then `c2 regtrace {name} --explain` names the lever",
        }.get(fn_layer, "")
        if route_msg:
            typer.secho(f"   → next: {route_msg}", fg="cyan")
    typer.secho(
        "\n   note: focused first-divergence view; --full for the "
        f"all-streams firehose; `c2 decomp-verify -v -f {name}` for "
        "the windowed byte-oracle diff; `c2 diagnose` for the routed "
        "triage.", dim=True)


# ── legacy: the old all-streams firehose, kept behind --full ────────────
def dossier(
    name: Annotated[str, typer.Argument(help="function name")],
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", help="Path to PS symbols.json"),
    ] = _SYMS,
    decomp_dir: Annotated[
        Path,
        typer.Option("--decomp", help="Decomp source root"),
    ] = _DECOMP,
    width: Annotated[
        int,
        typer.Option("--width", help="RC source-text column width"),
    ] = 56,
    no_source: Annotated[
        bool,
        typer.Option("--no-source", help="Skip the RC source-text column"),
    ] = False,
    no_mac: Annotated[
        bool,
        typer.Option("--no-mac",
                     help="Skip the Mac PPC decompile section entirely"),
    ] = False,
    force_mac: Annotated[
        bool,
        typer.Option("--mac",
                     help="Decompile the Mac source even when NOT cached "
                          "(~25s JVM warmup; default shows it only when the "
                          "per-fn decompile is already cached, ~instant)"),
    ] = False,
    no_ghidra: Annotated[
        bool,
        typer.Option("--no-ghidra/--ghidra",
                     help="Include the PS.EXE Ghidra decompile (Watcom-target"
                          " C); spins the ghidra-cli bridge. Default skip."),
    ] = True,
    no_win: Annotated[
        bool,
        typer.Option("--no-win",
                     help="Skip the Windows MSVC /Od decompile section"),
    ] = False,
    force_win: Annotated[
        bool,
        typer.Option("--win",
                     help="Decompile the Windows MSVC build even when NOT "
                          "cached (~60s JVM+project build; default shows it "
                          "only when the per-fn decompile is cached, ~instant)"),
    ] = False,
    full: Annotated[
        bool,
        typer.Option("--full",
                     help="Restore the old all-streams firehose (per-offset "
                          "stream table + full Mac/Win decompiles + sibling "
                          "list + allocator detail).  Default is the "
                          "focused first-divergence view with HEAD delta -- "
                          "re-run after each edit to converge on byte-exact."),
    ] = False,
) -> None:
    """Per-function focused view: FIRST PS↔RC divergence with all oracles
    aligned to it + delta vs git HEAD.

    Run after each edit; the next first-divergence appears.  No start/stop --
    the working tree IS the state; commits advance the HEAD baseline.

    Pass --full to restore the old all-streams firehose (archeology mode).
    """
    if not full:
        _emit_focused(name, symbols_json, decomp_dir, no_mac, force_mac,
                      no_win, force_win)
        return
    # ── --full: legacy all-streams renderer ─────────────────────────────
    # ── 1. PS side ────────────────────────────────────────────────
    ps = _ps_func_records(symbols_json, name)
    if ps is None:
        typer.secho(f"[!] {name!r} not in PS code symbols", fg="red")
        raise typer.Exit(1)
    ps_start, ps_end, ps_mod, ps_file, ps_recs, ps_code = ps
    if not ps_recs:
        typer.secho(f"[!] {name!r}: no PS line records (asm module?)",
                    fg="red")
        raise typer.Exit(1)
    ps_size = ps_end - ps_start

    # ── 2. RC side (fresh build) ─────────────────────────────────
    from c2.commands.decomp_verify import (
        _build_all, PS_CFLAGS, _DEFAULT_IMAGE,
    )
    src_dir = decomp_dir / "src"
    inc_dir = decomp_dir / "include"
    ok, out, _work, out_exe, out_map = _build_all(
        src_dir, inc_dir, _DEFAULT_IMAGE, PS_CFLAGS, use_cache=True,
    )
    if not ok:
        typer.secho("[!] build failed:\n" + out, fg="red")
        raise typer.Exit(1)

    rc = _rc_func_records(out_exe, out_map, name)
    if rc is None:
        typer.secho(f"[!] {name!r} not in RC map (decl/build mismatch?)",
                    fg="red")
        raise typer.Exit(1)
    rc_start, rc_end, rc_file, rc_recs, rc_code = rc
    rc_size = rc_end - rc_start

    # masked byte diff (same logic the corpus verifier uses)
    from c2.commands.decomp_verify import _compare_bytes
    from c2.parsers.exe import parse_exe
    from c2.commands.fixups import parse_le_fixups
    # PS fixups
    _, _bw, le_ps = parse_exe(Path("data/PS.EXE"))
    ps_fm, _ = parse_le_fixups(
        Path("data/PS.EXE"), le_ps.le_offset, le_ps.page_size,
        le_ps.num_pages, le_ps.objects[0].num_pages,
        le_ps.objects[1].num_pages,
    )
    ps_fix = set()
    for off in ps_fm:
        for k in range(4):
            ps_fix.add(off + k)
    # RC fixups already loaded
    _, rc_fix = _load_le_code_and_fixups_for_dossier(out_exe)
    # truncate to common length
    n = min(len(ps_code), len(rc_code))
    diffs = _compare_bytes(
        ps_code[:n], rc_code[:n],
        ps_start, rc_start,
        ps_fix, rc_fix,
    )
    bdiff = len(diffs)
    if len(ps_code) != len(rc_code):
        bdiff += abs(len(ps_code) - len(rc_code))  # tail length mismatch

    # binir recovery for both sides (function-relative op offsets)
    ps_ops = _binir_for_code(ps_code)
    rc_ops = _binir_for_code(rc_code)

    # ── 3. header ────────────────────────────────────────────────
    typer.secho(
        f"# {name}    PS {ps_file}  ({ps_size}b, {len(ps_recs)} marks)"
        f"   ⇆   RC {rc_file}  ({rc_size}b, {len(rc_recs)} marks)"
        f"   raw-diff {bdiff}b ({100*bdiff/max(ps_size,1):.0f}%)",
        fg="cyan", bold=True,
    )

    # ── 3a. shape distance (decomposed distance-to-PS) ───────────
    # seat (register identity) + width (type) + spill (frame) = the
    # byte-INDEPENDENT shape distance; an edit that drops `shape` is
    # PS-faithful even if `bytes` rose (Hard Rule #3 made objective).
    _seat = _wdiff = _spill = _binir = None
    if bdiff > 0:
        from c2.regalloc.seat_recon import (
            seat_diff as _sdf, type_width_diff as _twf,
            spill_diff as _spf,
            fmt_shape_layers as _flyr)
        from c2.commands.decomp_verify import _build_diff_rows as _bdr0
        from c2.commands.binir_shape_hints import detect as _bdet
        from c2 import bisect as _bs0
        try:
            _lm = {r["offset"]: r["line"] for r in ps_recs}
            _dr0, _ = _bdr0(ps_code, ps_start, rc_code, rc_start,
                            ps_fix, rc_fix, _lm)
            _seat, _wdiff, _spill = _sdf(_dr0), _twf(_dr0), _spf(_dr0)
            _binir = _bdet(_dr0)
            # judge metric from the CANONICAL shared helper (identical
            # inputs + code path to decomp-verify) -- see the sibling
            # comment in the focused path.
            _c = _bs0._verify_function_at(name, out_exe, out_map,
                                          symbols_json)
            _sd = (_c or {}).get("shape")
            if _sd is None:
                raise RuntimeError("canonical shape unavailable")
            if _sd['shape'] == 0:
                typer.secho(
                    f"   shape vs PS      : MATCHES (ir/width/spill/seat all "
                    f"0)   — residue is regalloc/encoding",
                    fg="green")
            else:
                typer.secho(
                    f"   shape vs PS      : {_flyr(_sd)}   "
                    f"→ fix-next: {_sd['fix_next']}",
                    fg="yellow")
            _emit_divergent_lines(_binir, _wdiff, _seat, _dr0)
        except Exception:  # noqa: BLE001
            _seat = _wdiff = _spill = _binir = None

    # ── 3b. verdict ──────────────────────────────────────────────
    # CAESAR2.EXE second-oracle hint (cheap map lookup).
    try:
        from c2.win_bytes import win_hint as _win_hint, tu_of as _tu_of
        _wh = _win_hint(name, _tu_of(name))
        if _wh.get("available"):
            typer.secho(
                f"   win: CAESAR2.EXE {_wh['win_va']} ({_wh['confidence']}) "
                f"-- `c2 win-verify {name}` / `c2 win-decompile {name}`",
                fg="cyan")
        else:
            typer.secho("   win: no CAESAR2.EXE mapping (not in func-map / "
                        "absent in the Windows build)", fg="bright_black")
    except Exception:  # noqa: BLE001
        pass
    _emit_verdict(ps_size, rc_size, ps_recs, rc_recs, ps_ops, rc_ops, bdiff,
                  ps_code, rc_code)
    # prescriptive work-order routing (gates the allocator triage below)
    if bdiff > 0:
        _emit_workorder(name)

    # const-audit: regalloc-invariant wrong-constant / off-by-one boundary.
    if bdiff > 0:
        from c2.commands.decomp_verify import _const_audit_for_json
        _ca = _const_audit_for_json(
            ps_code, rc_code, ps_start, rc_start, ps_fix, rc_fix)
        if _ca:
            _bits = []
            for _ch, _lbl in (("cmp_threshold", "cmp-boundary"),
                              ("eq", "eq"), ("plain", "plain")):
                if _ch in _ca:
                    _ps = ",".join(f"{k:#x}" for k in sorted(_ca[_ch]["ps_only"]))
                    _rc = ",".join(f"{k:#x}" for k in sorted(_ca[_ch]["rc_only"]))
                    _bits.append(f"{_lbl}[PS:{_ps or '-'} RC:{_rc or '-'}]")
            _flag = (" ⚠ off-by-one boundary (n vs n±1)"
                     if _ca.get("boundary_offby1") else "")
            typer.secho(
                f"   const-audit      : ✗ {_ca['n_div']} divergent "
                f"constant(s){_flag}  " + "  ".join(_bits), fg="yellow")
        else:
            typer.secho("   const-audit      : ✓ constants match PS "
                        "(regalloc-invariant)", fg="green")
        # out-of-order parameter (swapped constant arg)
        from c2.commands.decomp_verify import _argswap_for_json, _parse_map
        _rcm = _parse_map(out_map)
        _aw = _argswap_for_json(
            ps_code, rc_code, ps_start, rc_start, ps_fix, rc_fix, _rcm)
        if _aw:
            from c2.commands.const_audit import _ARGNAME as _AN
            for _s in _aw:
                typer.secho(
                    f"   arg-swap         : ✗ {_s['callee']}() const "
                    f"{_s['const']:#x} -> PS {_AN[_s['ps_slot']]} but RC "
                    f"{_AN[_s['rc_slot']]} (out-of-order parameter)", fg="red")

    # ── 3c. sibling-prologue scan (only when not byte-exact) ─────────────
    if bdiff > 0:
        siblings = _find_prologue_siblings(
            ps_code, prologue_len=20, min_match=4)
        siblings = [s for s in siblings if s[0] != name]
        if siblings:
            typer.echo()
            typer.secho("## byte-exact siblings (prologue match)", bold=True)
            for sname, _saddr, _sz, common in siblings[:8]:
                typer.echo(f"   {common:>2}-byte prologue match  →  {sname}")
            if len(siblings) > 8:
                typer.echo(f"   ... and {len(siblings) - 8} more")
            typer.secho(
                "   (open these with `c2 disasm <name>` to see what "
                "diverges first after the shared prologue)",
                dim=True)

    # ── 4. interleaved stream ────────────────────────────────────
    typer.echo()
    typer.secho(
        "## stream (one row per line-mark boundary, "
        "asm-offset aligned)",
        bold=True)
    typer.echo(
        "   off     span  who  PS#   RC#   tags                       "
        "PS-IR / RC-IR                                  "
        + ("RC source" if not no_source else ""))
    typer.echo("   ------  ----  ---  ----  ----  ------------------------   "
               "----------------------------------------------  "
               + ("-" * width if not no_source else ""))

    rc_src = _read_source_lines(rc_file, decomp_dir)

    rows = _stream_rows(
        ps_start, ps_end, ps_recs, ps_code,
        rc_start, rc_end, rc_recs, rc_code,
    )
    # annotate each row with binir ops for its span
    ps_func_size = ps_end - ps_start
    rc_func_size = rc_end - rc_start
    for k, r in enumerate(rows):
        nxt_off = (rows[k + 1]["off"] if k + 1 < len(rows)
                   else max(ps_func_size, rc_func_size))
        r["ps_ops"] = _binir_in_span(
            ps_ops, r["off"], min(nxt_off, ps_func_size))
        r["rc_ops"] = _binir_in_span(
            rc_ops, r["off"], min(nxt_off, rc_func_size))
    total = 0
    n_paired = n_ps_only = n_rc_only = 0
    for r in rows:
        owner = r["owner"]
        if owner == "B":
            n_paired += 1
            who = "P+R"
        elif owner == "P":
            n_ps_only += 1
            who = "P  "
        elif owner == "R":
            n_rc_only += 1
            who = "  R"
        else:
            who = " - "
        total += r["span"]
        rc_text = ""
        if not no_source:
            rc_text = rc_src.get(r["rc_line"] or 0, "").strip()
            if len(rc_text) > width:
                rc_text = rc_text[:width - 1] + "…"
        ps_s = f"{r['ps_line']:>4}" if r["ps_line"] else "   -"
        rc_s = f"{r['rc_line']:>4}" if r["rc_line"] else "   -"
        # tag column: if both sides agree on tags, show one set;
        # otherwise show PS|RC
        ps_t = _fmt_tags(r["ps_tags"])
        rc_t = _fmt_tags(r["rc_tags"])
        if ps_t == rc_t:
            tagcol = ps_t
        else:
            tagcol = f"{ps_t} | {rc_t}".strip(" |")
        # IR column: PS IR / RC IR (collapse if equal)
        ps_ir = _binir_short(r["ps_ops"])
        rc_ir = _binir_short(r["rc_ops"])
        if ps_ir == rc_ir:
            ircol = ps_ir
        else:
            ircol = f"{ps_ir} / {rc_ir}".strip(" /")
        if len(ircol) > 46:
            ircol = ircol[:45] + "…"
        line = (
            f"   +{r['off']:>#5x}  {r['span']:>4}  {who}  "
            f"{ps_s}  {rc_s}  {tagcol:<25}  {ircol:<46}  {rc_text}"
        )
        if owner == "B":
            typer.echo(line)
        elif owner == "R":
            typer.secho(line, fg="yellow")
        elif owner == "P":
            typer.secho(line, fg="red")
        else:
            typer.echo(line)
    typer.echo("   ------  ----  ---")
    typer.echo(
        f"   total   {total:>4}        "
        f"({n_paired} paired, {n_ps_only} PS-only, "
        f"{n_rc_only} RC-only)")
    typer.echo()
    typer.secho("   legend: P+R = both sides start a new line here; "
                "P = only PS does (RC kept the prior line);", dim=True)
    typer.secho("           R = only RC does (PS kept the prior line). "
                "P-only/R-only rows mark source-shape divergence.",
                dim=True)

    # ── 4b. highlights (cascade root + top-3 diverging rows) ──────
    if bdiff > 0:
        _emit_highlights(rows, ps_code, rc_code, ps_start, rc_start,
                         ps_fix, rc_fix, rc_src, width, ps_ops, rc_ops)

    # ── 4c. regalloc snapshot (cached file_trace) ────────────────
    # reuses the seat/width/spill diffs computed for the shape-distance line.
    if bdiff > 0:
        _emit_regalloc(name, rc_file, decomp_dir, rc_src, width, _seat,
                       _wdiff, _spill)
        _emit_triage(name)

    # ── 5. Mac PPC source-shape oracle (cleaned Ghidra C) ────────
    # The Mac source is the source-SHAPE oracle (nesting, types, control
    # flow) -- exactly what the `ir` divergence layer needs.  Show it by
    # default when the per-fn decompile is CACHED (~instant); when uncached,
    # show a pointer instead of a surprise ~25s JVM warmup (--mac / mac:true
    # forces it).
    if not no_mac:
        if force_mac or _mac_decompile_cached(name):
            ps_calls = _ps_call_sequence(ps_code, ps_start, ps_recs)
            _emit_mac_section(name, ps_calls)
        else:
            typer.echo()
            typer.secho(
                f"## mac decompile  (source-shape oracle) — not cached; "
                f"`c2 dossier {name} --mac` (or mac:true) to decompile "
                "(~25s JVM, then cached)", dim=True)

    # ── 5b. Windows MSVC /Od source-shape oracle (x86, most legible) ──
    # Second source-shape oracle alongside Mac: MSVC 4.0 /Od of the SAME
    # engine source.  x86 + unoptimized => every statement/local explicit,
    # params named+typed, globals named.  Shown by default when the per-fn
    # decompile is CACHED (~instant); else a pointer (--win / win:true forces).
    if not no_win:
        if force_win or _win_decompile_cached(name):
            if 'ps_calls' not in dir() or ps_calls is None:
                ps_calls = _ps_call_sequence(ps_code, ps_start, ps_recs)
            _emit_win_section(name, ps_calls)
        else:
            typer.echo()
            typer.secho(
                f"## win decompile  (MSVC /Od oracle) — not cached; "
                f"`c2 dossier {name} --win` (or win:true) to decompile "
                "(~60s JVM+build, then cached)", dim=True)

    # ── 5c. PS.EXE Ghidra decompile (Watcom-target C reconstruction) ──
    if not no_ghidra:
        _emit_ghidra_section(name)

    # ── 5c. local-hints (REAL local vs INLINE read; de-invent / add-local) ─
    if bdiff > 0:
        _emit_local_hints(name)


# ── local-hints (REAL local vs INLINE read; the de-invent / add-local lever) ─
def _emit_local_hints(name: str) -> None:
    """Surface the local-hints source-shape lever: which globals PS reads
    INLINE that our source caches in a local (DE-INVENT -> delete it) or PS
    names a local from that our source reads inline (ADD-LOCAL -> introduce
    it).  Fable-5's highest-leverage finding ("most temps were Watcom's, not
    the source's"): de-inventing closed get_morale_and_readiness 162->0 and
    slider_control 156->3.  Plus the per-load REAL/INLINE classification
    counts."""
    try:
        from c2.commands.local_hints import tool_summary
        lh = tool_summary(name)
    except Exception:  # noqa: BLE001
        return
    if not lh.get("available"):
        return
    if not (lh["deinvent"] or lh["addlocal"]
            or lh["n_real"] or lh["n_inline"]):
        return
    typer.echo()
    typer.secho(
        "## local-hints  (memory loads: REAL named local vs INLINE read)",
        bold=True)
    typer.echo(
        f"   classification: {lh['n_real']} REAL  {lh['n_inline']} INLINE  "
        f"{lh['n_abstain']} abstain"
        + (f"   (+{lh['n_reg_locals']} register-rooted local statement(s), "
           "advisory ~92%; `c2 local-hints <fn> --statements`)"
           if lh.get('n_reg_locals') else ""))
    if not lh.get("in_source"):
        typer.secho("   (function not in the recovered-source index -- "
                    "no de-invent / add-local cross-check)", dim=True)
        return
    if not (lh["deinvent"] or lh["addlocal"]):
        typer.secho("   PS-scanner agrees with the recovered source's local "
                    "structure (no de-invent / add-local lever).", fg="green")
        return
    if lh["deinvent"]:
        typer.secho("   DE-INVENT (PS reads INLINE, source caches a local -> "
                    "delete the local, read the global directly; Rule 129):",
                    fg="yellow")
        for sym in lh["deinvent"]:
            n_in = lh["ps_inline_count"].get(sym, 0)
            typer.echo(f"       {sym}  (PS reads inline {n_in}x)")
    if lh["addlocal"]:
        typer.secho("   ADD-LOCAL (PS names a local, source reads inline -> "
                    "introduce `T v = global;`):", fg="cyan")
        for sym in lh["addlocal"]:
            typer.echo(f"       {sym}")
    typer.secho(f"   drill in: c2 local-hints {name} --vs-source", dim=True)


# ── triage (corpus cache from `c2 triage --rebuild`) ───────────────


def _emit_workorder(name: str) -> None:
    """Prescriptive routing line: the EARLIEST divergent residue layer == the
    next action, the named lever, and whether it is steerable today.  From the
    cached verify record (offline).  This GATES the allocator triage below:
    at L1/L2 (substrate/shape) the register-allocation triage is premature.
    """
    cache = Path(".c2-cache/verify.json")
    if not cache.exists():
        return
    try:
        data = json.loads(cache.read_text())
    except json.JSONDecodeError:
        return
    rec = next((f for f in data.get("functions", [])
                if f.get("name") == name), None)
    if not rec or rec.get("diff_byte_count", 0) <= 0:
        return
    from c2.commands.regalloc_verdict import layered_verdict
    # reconcile the IDENTITY-layer steerability against the EXACT inverse
    # (cascade) so the work-order never oversells a tie the inverse search
    # has already proven UNREACHABLE.
    v = layered_verdict(rec, name=name, reconcile=True)
    color = {1: "yellow", 2: "magenta", 3: "red",
             4: "cyan", 5: "bright_black"}[v["layer"]]
    typer.echo()
    typer.secho("## work-order  (earliest divergent layer == next action)",
                bold=True)
    typer.secho(f"   L{v['layer']} {v['name']}   lever: {v['lever']}",
                fg=color)
    typer.echo(f"   steerable: {v['steerable']}   ·   {v['detail']}")
    if len(v.get("stack", [])) > 1:
        typer.secho(
            f"   stack: {' → '.join(v['stack'])}  ({len(v['stack'])} layers; "
            "earliest is NEXT, expect more below)",
            fg="bright_black")
    if v["layer"] <= 2:
        typer.secho(
            "   NOTE: this is a SUBSTRATE/SHAPE layer -- fix it FIRST; the "
            "allocator triage below is premature until the IR matches PS "
            "(the frame/registers are OUTPUTS of allocation).",
            fg="bright_black")
    elif v["steerable"] == "tie-reorder":
        typer.secho("   GAP (cascade-VERIFIED): the named birth-order reorder "
                    "above closes this pair -- see the allocator triage below.",
                    fg="green")
    elif v["steerable"].startswith(("optimize:", "treegen:", "regalloc:",
                                    "rover:", "compiler-slice:")):
        typer.secho(
            f"   SLICE: the order-permutation inverse does not own this "
            f"divergence -- it lives in the `{v['steerable']}` slice.  A source "
            "preimage EXISTS (PS.EXE = Watcom-10.0a(source)); invert that "
            "slice via the lever above, do NOT treat as a floor.", fg="yellow")
        # Surface the slice's trace evidence inline (read-only summary;
        # the per-event detail is in `c2 regalloc-verdict <fn>`).
        from c2.commands.regalloc_verdict import (
            score_event_summary, mergeindex_event_summary)
        if v["steerable"] == "optimize:loop-hoist":
            for ln in score_event_summary(name)[:3]:
                typer.echo(ln)
        elif v["steerable"] == "treegen:index-fusion":
            for ln in mergeindex_event_summary(name)[:3]:
                typer.echo(ln)


def _emit_triage(name: str) -> None:
    """Surface this function's cascade verdict + rule hints from the
    corpus triage cache.  Built by ``c2 triage --rebuild`` (one-shot
    ``decomp-verify -v`` capture).  Silently skipped when the cache is
    missing.
    """
    cache = Path(".c2-cache/triage.json")
    if not cache.exists():
        return
    try:
        data = json.loads(cache.read_text())
    except json.JSONDecodeError:
        return
    t = data.get(name)
    if not t:
        return
    cascade = t.get("cascade") or []
    prologue = t.get("prologue") or []
    regalloc = t.get("regalloc") or []
    if not (cascade or prologue or regalloc):
        return
    typer.echo()
    typer.secho(
        "## allocator triage  (from `c2 triage` corpus cache)", bold=True)
    for ln in cascade[:4]:
        if "REACHABLE by TIE-REORDER" in ln:
            color = "green"
        elif "needs a SAVINGS" in ln:
            color = "yellow"
        elif "UNREACHABLE" in ln:
            color = "red"
        elif "INCONCLUSIVE" in ln:
            color = "yellow"
        else:
            color = None
        # truncate to one line for readability
        line = ln if len(ln) < 240 else ln[:237] + "…"
        if color:
            typer.secho(f"   {line}", fg=color)
        else:
            typer.echo(f"   {line}")
    for ln in prologue[:2]:
        typer.echo(f"   {ln[:240]}"
                   + ("…" if len(ln) > 240 else ""))
    for ln in regalloc[:2]:
        typer.echo(f"   {ln[:240]}"
                   + ("…" if len(ln) > 240 else ""))
    # caveat about decl-swap fragility
    has_reachable = any("REACHABLE by TIE-REORDER" in l for l in cascade)
    if has_reachable:
        typer.secho(
            "   CAVEAT: 'Rule 115 (decl order)' from the verdict is often a"
            " DEAD lever in WCC 10.0a -- names typically intern by FIRST USE,\n"
            "   not by decl.  Try Rule 28a (use order: reorder which var is"
            " referenced first) BEFORE decl-swap; expect ~1b improvement.",
            dim=True)
    # rover-class: route into the c2 front door (the Rover hint's fit +
    # lw census live in decomp-verify -v; the spelling screener is c2 spell)
    has_rover = any("no alloc row holds one side" in l for l in cascade)
    if has_rover:
        typer.echo()
        typer.secho(
            "   ROVER divergence detected (verdict mentions 'no alloc row"
            " holds one side' -- this is FindRegister scratch picker,\n"
            "   not the named-value allocator).  Work it through:",
            fg="yellow", bold=True)
        typer.secho(
            f"     c2 decomp-verify -v -f {name}   # Rover hint: confirmed "
            "inject / fit windows + [lw census: ...] candidates",
            fg="cyan")
        typer.secho(
            f"     c2 spell {name} --fusion        # which RISCified pairs "
            "fused vs a named lcx reject",
            fg="cyan")
        typer.secho(
            f"     c2 spell {name} <candidate.c>   # 3-stage spelling "
            "screener (INERT@TREE / INERT@BURN / LIVE), no byte compile",
            fg="cyan")
        typer.secho(
            "   The byte-neutral +1 lever is LOAD-FOLDING (`x = g; ... x OP"
            " k` -> `g OP k` inline); -1 is naming the temp.\n"
            "   Mechanism docs: watcom10.0a docs/rover-model.md.",
            dim=True)


# ── regalloc (file_trace cache; instant if file unchanged) ───────────


def _emit_divergent_lines(binir, wdiff: dict | None, seat: dict | None,
                          rows: list | None = None) -> None:
    """Anchor each shape-distance divergence to the PS `-d1` SOURCE LINE that
    produced it AND show the PS-vs-RC asm at that line -- a SELF-CONTAINED
    single-pane view (no need to bounce to `c2 disasm`).  Collapses the fix
    from "somewhere in the function" to "these lines, this divergence".

    Aggregates the three located layers: ir (binir op-kind divergence per
    line), width (signedness + byte<->dword), seat (first divergent seat)."""
    by_line: dict[int, list[tuple[str, str]]] = {}

    def _add(ln, layer, detail):
        if ln is None:
            return
        by_line.setdefault(int(ln), []).append((layer, detail))

    # ir: wrong ops / control-flow (binir's per-line divergence)
    for d in (getattr(binir, "divergences", None) or []):
        _add(d.line, "ir", d.summary)
    # width: signedness + byte<->dword
    for s in ((wdiff or {}).get("signedness") or []):
        for ex in s.get("examples", [])[:2]:
            _add(ex.get("ln"), "width",
                 f"PS {ex['ps_form']} vs RC {ex['rc_form']} — "
                 + ("the local is SIGNED in PS" if ex.get("ps_signed")
                    else "the local is UNSIGNED in PS"))
    for w in ((wdiff or {}).get("width") or [])[:4]:
        _add(w.get("ln"), "width",
             f"byte<->dword: PS {w['ps_width']}b vs our {w['rc_width']}b "
             "— our local is wider")
    # seat: the first divergent register seat
    fd = (seat or {}).get("first_divergence")
    if fd:
        _add(fd.get("ln"), "seat", f"RC {fd['rc']} ⇄ PS {fd['ps']}")

    if not by_line:
        return
    # group the asm by source line so we can show PS vs RC inline
    asm_by_line: dict[int, dict[str, list]] = {}
    if rows:
        try:
            from c2.commands.binir_shape_hints import _group_rows_by_line
            grouped = _group_rows_by_line(rows)
            for ln, sides in grouped.items():
                asm_by_line[int(ln)] = {
                    "ps": [i[3] for i in sides.get("ps", [])],
                    "rc": [i[3] for i in sides.get("rc", [])],
                }
        except Exception:  # noqa: BLE001
            pass

    typer.echo()
    typer.secho("   divergent source lines  (the fix is HERE — PS asm vs ours, "
                "in one pane):", bold=True)
    for ln in sorted(by_line):
        tags = " · ".join(f"[{layer}] {detail}" for layer, detail in by_line[ln])
        typer.secho(f"     L{ln:<5} {tags}", fg="yellow")
        a = asm_by_line.get(ln)
        if a:
            ps_a = "; ".join(a["ps"][:6]) or "—"
            rc_a = "; ".join(a["rc"][:6]) or "—"
            typer.secho(f"            PS  {ps_a}", fg="bright_black")
            typer.secho(f"            RC  {rc_a}", fg="bright_black")


def _emit_regalloc(name: str, rc_file: str, decomp_dir: Path,
                   rc_src: dict, width: int, seat: dict | None = None,
                   wdiff: dict | None = None, spill: dict | None = None) -> None:
    """Show top GiveBestReg conflicts + spilled values for this function.

    Pulls the cached container ``-trace`` per-TU file_trace (which the
    ``c2 regtrace`` command also uses).  Content-hashed on the TU source,
    so this is instant when the .c file hasn't changed since the last
    trace; runs a podman build otherwise (~10-30s).
    """
    try:
        from c2 import regalloc
    except ImportError:
        return
    src_file = decomp_dir / "src" / rc_file
    if not src_file.exists():
        return
    try:
        td = regalloc.file_trace(src_file, decomp_dir / "include")
    except Exception as e:
        typer.secho(f"   (regalloc trace failed: {e})", dim=True)
        return
    routine = td.get("by_func", {}).get(name)
    if not routine or not routine.get("alloc"):
        return
    allocs = routine["alloc"]

    # ── PS↔RC seat divergence (tooling gap #1): name each swapped value
    # by joining the asm-reconstructed PS seat map with this cached trace's
    # value→register table; classify the steerable lever (equal-savings
    # ConfBefore tie vs savings/shape).
    _seat_swaps = seat.get("swaps") if seat else None
    _seat_fd = seat.get("first_divergence") if seat else None
    if seat and (_seat_swaps or _seat_fd):
        from c2.regalloc.seat_recon import reg_to_fam
        rc_by_fam: dict[str, dict] = {}
        for a in allocs:
            reg = a.get("reg_name")
            var = a.get("var")
            if reg and var and var != "(temp)":
                rc_by_fam.setdefault(reg_to_fam(reg),
                                     {"var": var, "sav": a.get("savings", 0)})
        sav_groups: dict[int, int] = {}
        for info in rc_by_fam.values():
            sav_groups[info["sav"]] = sav_groups.get(info["sav"], 0) + 1
        typer.echo()
        typer.secho("## PS↔RC register seats  (value-aligned seat diff)",
                    bold=True)
        typer.secho("   PS seats reconstructed from PS.EXE asm vs our "
                    "allocation (regtrace value→reg); `c2 regtrace "
                    f"{name}` for the full view", dim=True)
        for sw in _seat_swaps or []:
            info = rc_by_fam.get(reg_to_fam(sw["rc"]), {})
            var = info.get("var", "(temp)")
            sav = info.get("sav", 0)
            tied = sav > 0 and sav_groups.get(sav, 0) > 1
            lever = ("equal-savings tie → ConfBefore (Rule 28a/115)" if tied
                     else "savings/shape (live-range / type-width)")
            typer.secho(
                f"     {var:<16} RC {sw['rc']:<4} ⇄ PS {sw['ps']:<4} "
                f"sav={sav:<5} {lever}", fg="yellow")
        if _seat_fd:
            fd = _seat_fd
            loc = f"+{fd['off']:#06x}" + (f" L{fd['ln']}" if fd.get("ln") else "")
            kind = ("first divergent seat" if _seat_swaps
                    else "localized seat difference (not systematic)")
            col = "yellow" if not _seat_swaps else None
            # value naming is reliable only for systematic swaps (dominant
            # family resident); for a one-off divergence the family may host
            # several values, so show registers + asm and let the asm speak.
            typer.secho(f"     {kind} {loc}: "
                        f"RC {fd['rc']} ⇄ PS {fd['ps']}  "
                        f"[PS: {fd['ps_asm']}]", fg=col, dim=bool(_seat_swaps))
        if seat.get("verdict") == "ambiguous" and not _seat_swaps:
            typer.secho("     (low-confidence correspondence — verify it is "
                        "not a disasm artifact)", dim=True)

    # ── PS↔RC type/width diff (gap #3): signedness + byte<->dword ─────────
    if wdiff and wdiff.get("count"):
        typer.echo()
        typer.secho("## PS↔RC type/width  (a signed/byte local PS made differently)",
                    bold=True)
        for s in wdiff.get("signedness", []):
            d = s["delta"]
            who = ("PS is SIGNED, ours UNSIGNED -> make the local signed"
                   if d > 0 else
                   "PS is UNSIGNED, ours SIGNED -> make the local unsigned")
            typer.secho(f"     {s['label']}: {abs(d)}x  ({who})", fg="yellow")
            for ex in s.get("examples", [])[:1]:
                loc = (f" L{ex['ln']}" if ex.get("ln") else "")
                typer.secho(f"       e.g.{loc}  PS[{ex['ps_form']}] "
                            f"RC[{ex['rc_form']}]", dim=True)
        for w in wdiff.get("width", [])[:3]:
            loc = (f" L{w['ln']}" if w.get("ln") else "")
            typer.secho(f"     byte<->dword{loc}: PS {w['ps_width']}b vs our "
                        f"{w['rc_width']}b  [PS: {w['ps_asm']}]  -- our local "
                        "is wider than PS's", fg="yellow")

    # ── PS↔RC frame / spill diff (gap #4): only when frames diverge ──────
    if spill and spill.get("ps_frame") != spill.get("rc_frame"):
        d = spill.get("slot_delta", 0)
        rc_spilled = [a.get("var") for a in allocs
                      if (a.get("memory_exiled") or not a.get("reg_name"))
                      and a.get("var") and a.get("var") != "(temp)"]
        typer.echo()
        typer.secho("## PS↔RC frame / spill  (live-set divergence)", bold=True)
        typer.secho(f"   PS frame {spill['ps_frame']}b ({spill['ps_byte_slots']} "
                    f"byte slots) vs our {spill['rc_frame']}b "
                    f"({spill['rc_byte_slots']} byte slots)", dim=True)
        if d > 0:
            typer.secho(
                f"     PS spills ~{d} MORE value(s): it keeps "
                f"{spill['ps_byte_slots']} byte intermediate(s) as named stack "
                "locals our build holds in registers.  PS's IL has a LARGER "
                "live-set -- we inlined/narrowed temps PS kept.  Lever: give "
                "those locals PS's width (see type/width above) and keep them "
                "named/live; do NOT de-invent them.", fg="yellow")
        elif d < 0:
            typer.secho(
                f"     WE spill ~{-d} more value(s) than PS -- PS keeps them in "
                "registers.  Lever: shorten our live-ranges (de-invent a temp / "
                "reorder so a value dies before the call).", fg="yellow")
        if rc_spilled:
            typer.secho(f"     our spilled locals: {', '.join(rc_spilled[:8])}",
                        dim=True)

    # spilled (memory_exiled OR no chosen reg)
    spilled = [a for a in allocs
               if a.get("memory_exiled") or not a.get("reg_name")]
    typer.echo()
    typer.secho(
        f"## regalloc  ({len(allocs)} GiveBestReg conflicts, "
        f"{len(spilled)} spilled)",
        bold=True)
    typer.secho(
        "   from container `-trace` image (cached by source-file hash); "
        "see `c2 regtrace --explain` for full ConfBefore-tie analysis",
        dim=True)
    # top-5 by savings (the conflicts that most impact codegen)
    top = sorted(allocs, key=lambda a: -a.get("savings", 0))[:5]
    typer.echo("   top conflicts (by savings) -- highest priority "
               "allocations:")
    for a in top:
        var = a.get("var") or "(temp)"
        reg = a.get("reg_name") or "SPILL"
        sav = a.get("savings", 0)
        dln = a.get("defline") or 0
        rc_text = rc_src.get(dln, "").strip()
        if len(rc_text) > width:
            rc_text = rc_text[:width - 1] + "…"
        typer.echo(
            f"     sav={sav:>3}  {var:<20}  → {reg:<5}  "
            + (f"L{dln:<5}" if dln else "      ")
            + f"  {rc_text}")
    # spilled (if any)
    if spilled:
        typer.echo()
        typer.secho("   spilled values (live across too many calls / "
                    "out-ranked):", fg="red")
        for a in spilled[:5]:
            var = a.get("var") or "(temp)"
            sav = a.get("savings", 0)
            dln = a.get("defline") or 0
            rc_text = rc_src.get(dln, "").strip()
            if len(rc_text) > width:
                rc_text = rc_text[:width - 1] + "…"
            typer.echo(f"     sav={sav:>3}  {var:<20}  "
                       + (f"L{dln:<5}" if dln else "      ")
                       + f"  {rc_text}")
        if len(spilled) > 5:
            typer.secho(f"     (+ {len(spilled) - 5} more spilled)",
                        dim=True)
    # crowd-detector: many temps going to the SAME reg = repeated
    # short-lived temps the user could try to merge / pre-name
    reg_counts: dict[str, int] = {}
    for a in allocs:
        if a.get("var") in (None, "(temp)") and a.get("reg_name"):
            reg_counts[a["reg_name"]] = reg_counts.get(a["reg_name"], 0) + 1
    crowded = [(reg, n) for reg, n in reg_counts.items() if n >= 4]
    if crowded:
        typer.echo()
        for reg, n in sorted(crowded, key=lambda t: -t[1]):
            typer.secho(
                f"   crowded reg     : {n} temps allocated to {reg} "
                "(repeated short-lived temps; consider a named local to "
                "force a different reg, or compare against PS for the "
                "expected reg here)",
                fg="yellow")

    # ── slot-swap residue verdict (Rule 107 / ShellSort instability) ──
    # If the routine has spill slots, run the ShellSort-instability diagnoser.
    # It classifies the slot-swap residue (if any) and surfaces the simulator's
    # mechanism verdict + flipping perturbations.  See
    # c2/regalloc/shellsort_sim.py + docs/slot-swap-survey-2026-06-25.md.
    if routine.get("slots"):
        try:
            from c2.regalloc.shellsort_sim import diagnose, render_diagnosis
            d = diagnose(routine)
            d.fn = name
            # Only worth showing for the non-trivial residue classes
            if d.klass in ("shellsort-instability",
                           "shellsort-instability-other",
                           "sort-stable-other", "sub-source"):
                typer.echo()
                typer.secho(
                    "## Rule 107 slot-swap residue  (ShellSort sim diagnoser)",
                    bold=True)
                typer.secho(
                    "   the slot-commit order at AssignTemps' size sort, "
                    "classified by the trace-validated mechanism (size-mix "
                    "-> ShellSort gap-instability; all-same-size -> upstream); "
                    "docs/slot-swap-survey-2026-06-25.md", dim=True)
                for line in render_diagnosis(d).split("\n"):
                    typer.echo(line)
        except Exception:
            pass


# ── highlights (cascade root + top diverging rows) ────────────────


def _emit_highlights(rows, ps_code, rc_code, ps_start, rc_start,
                     ps_fix, rc_fix, rc_src, width, ps_ops, rc_ops):
    """Surface the cascade root (first diverging byte) and the top-3
    rows by byte-impact, to narrow source-shape investigation.
    """
    from c2.commands.decomp_verify import _compare_bytes
    n = min(len(ps_code), len(rc_code))
    diffs = _compare_bytes(
        ps_code[:n], rc_code[:n],
        ps_start, rc_start, ps_fix, rc_fix,
    )

    typer.echo()
    typer.secho("## highlights", bold=True)

    # cascade root: first diverging masked byte
    if diffs:
        root_off = diffs[0]
        # find the stream row covering this offset (most recent row
        # whose .off <= root_off)
        cover = None
        for r in rows:
            if r["off"] <= root_off:
                cover = r
            else:
                break
        if cover:
            ps_ln = cover["ps_line"]
            rc_ln = cover["rc_line"]
            rc_text = rc_src.get(rc_ln or 0, "").strip()
            if len(rc_text) > width:
                rc_text = rc_text[:width - 1] + "…"
            typer.secho(
                f"   cascade root  : first diff at +{root_off:#x} "
                f"(within row +{cover['off']:#x}, span {cover['span']}b)",
                fg="red")
            typer.echo(
                f"                   PS line {ps_ln} ⇆ RC line {rc_ln}"
                f"  ->  {rc_text}")
    else:
        typer.secho(
            "   cascade root  : no masked byte diff (residue only in "
            "length/fixup positions)", fg="yellow")

    # per-row diff impact: count diffs lying in each row's asm span
    if diffs:
        diff_set = set(diffs)
        impact = []
        for k, r in enumerate(rows):
            lo = r["off"]
            hi = rows[k + 1]["off"] if k + 1 < len(rows) else len(ps_code)
            n_diff = sum(1 for d in diffs if lo <= d < hi)
            if n_diff > 0:
                impact.append((n_diff, r))
        impact.sort(key=lambda t: -t[0])
        if impact:
            typer.echo()
            typer.secho(
                f"   top diverging rows (by masked-byte count in span):",
                fg="red")
            shown = 0
            for ndiff, r in impact:
                if shown >= 3:
                    break
                shown += 1
                rc_ln = r["rc_line"]
                rc_text = rc_src.get(rc_ln or 0, "").strip()
                if len(rc_text) > width:
                    rc_text = rc_text[:width - 1] + "…"
                typer.echo(
                    f"     +{r['off']:>#5x}  span {r['span']:>3}b  "
                    f"PS#{r['ps_line'] or '-':<5}  RC#{r['rc_line'] or '-':<5}  "
                    f"→ {ndiff} diff byte(s)   |  {rc_text}")
                # IR op detail when ops on this row differ
                ps_row_ops = r.get("ps_ops", [])
                rc_row_ops = r.get("rc_ops", [])
                ir_lines = _ir_op_diff_lines(ps_row_ops, rc_row_ops)
                for ir_line in ir_lines[:4]:
                    typer.secho(f"       {ir_line}", dim=True)
                if len(ir_lines) > 4:
                    typer.secho(
                        f"       (+{len(ir_lines) - 4} more op diff(s))",
                        dim=True)
            if len(impact) > 3:
                typer.secho(
                    f"   (+ {len(impact) - 3} more rows with diffs)",
                    dim=True)

    # pattern detector: alternating P-only/R-only at consecutive offsets
    # => prologue 1-byte cascade signature
    alt_run = 0
    max_alt = 0
    prev_owner = None
    for r in rows:
        ow = r["owner"]
        if ow in ("P", "R") and prev_owner in ("P", "R") and ow != prev_owner:
            alt_run += 1
            max_alt = max(max_alt, alt_run)
        else:
            alt_run = 0
        prev_owner = ow
    if max_alt >= 4:
        typer.echo()
        typer.secho(
            f"   pattern         : {max_alt + 1}-row alternating "
            "P-only/R-only run = classic 1-byte cascade (PS and RC line "
            "marks drift by 1 byte each step). Look at the prologue / "
            "frame divergence.",
            fg="yellow")


def _ir_op_diff_lines(ps_ops, rc_ops) -> list[str]:
    """Return narrative lines describing per-op differences between PS and RC
    op lists for a stream row.

    Pairs ops by ORDINAL position (Nth PS op vs Nth RC op).  Emits:
      - 'IR   PS only: <op>'      (PS has more ops than RC)
      - 'IR   RC only: <op>'      (RC has more ops than PS)
      - 'IR   PS <op-A>  RC <op-B>'  (mismatch at position k)

    The 'op' field carries the friendly form (e.g.,
    OP_O_CMP_GREATER_EQUAL(eax, 0)) so signedness / register / immediate
    differences are visible without re-disassembling.
    """
    n = max(len(ps_ops), len(rc_ops))
    out = []
    for k in range(n):
        p = ps_ops[k] if k < len(ps_ops) else None
        r = rc_ops[k] if k < len(rc_ops) else None
        if p and r:
            if p.kind == r.kind and getattr(p, "op", "") == getattr(r, "op", ""):
                continue
            out.append(f"IR  PS {p.kind:<20} {getattr(p, 'op', '') or ''}")
            out.append(f"    RC {r.kind:<20} {getattr(r, 'op', '') or ''}")
        elif p:
            out.append(f"IR  PS-only {p.kind:<14} {getattr(p, 'op', '') or ''}")
        elif r:
            out.append(f"IR  RC-only {r.kind:<14} {getattr(r, 'op', '') or ''}")
    return out


# ── verdict (top-line classification) ────────────────────────────────


def _emit_verdict(ps_size, rc_size, ps_recs, rc_recs,
                  ps_ops, rc_ops, bdiff, ps_code, rc_code):
    typer.echo()
    typer.secho("## verdict", bold=True)
    base_ps = min((r["offset"] for r in ps_recs), default=0)
    base_rc = min((r["offset"] for r in rc_recs), default=0)
    ps_rel = {r["offset"] - base_ps for r in ps_recs}
    rc_rel = {r["offset"] - base_rc for r in rc_recs}
    paired = len(ps_rel & rc_rel)
    ps_only = len(ps_rel - rc_rel)
    rc_only = len(rc_rel - ps_rel)

    def _kinds(ops):
        d: dict[str, int] = {}
        for o in ops:
            d[o.kind] = d.get(o.kind, 0) + 1
        return d
    ps_kinds = _kinds(ps_ops)
    rc_kinds = _kinds(rc_ops)
    ir_diffs = []
    for k in sorted(set(ps_kinds) | set(rc_kinds)):
        pn = ps_kinds.get(k, 0)
        rn = rc_kinds.get(k, 0)
        if pn != rn:
            ir_diffs.append((k, pn, rn))

    structural = (
        paired == len(ps_rel) == len(rc_rel)
        and not ir_diffs
    )
    if bdiff == 0:
        cls = "✓ byte-exact"
    elif structural and ps_size == rc_size:
        cls = ("allocator-residue (structure ✓, IR multiset ✓; "
               "residue is register-allocator choice -- needs WCC "
               "GiveBestReg work, not source-shape)")
    elif structural:
        cls = ("frame-shift (structure ✓, IR multiset ✓; byte-length "
               "mismatch -> prologue/epilogue divergence)")
    elif ir_diffs:
        cls = ("semantic divergence (IR multiset differs -- "
               "different ops generated)")
    elif ps_only or rc_only:
        cls = ("source-shape divergence (line-mark counts mismatch; "
               "check P-only/R-only rows in stream for split/merged "
               "statements)")
    else:
        cls = "mixed structural+allocator residue"

    typer.echo(f"   mark alignment   : {paired} paired, "
               f"{ps_only} PS-only, {rc_only} RC-only")
    typer.echo(f"   byte residue     : raw {bdiff}b "
               f"({100*bdiff/max(ps_size,1):.0f}% of {ps_size}b)")
    # prologue / frame
    ps_pushes, ps_sub = _prologue_summary(ps_code)
    rc_pushes, rc_sub = _prologue_summary(rc_code)
    ps_str = ("push " + " ".join(ps_pushes) if ps_pushes else "(no pushes)")
    rc_str = ("push " + " ".join(rc_pushes) if rc_pushes else "(no pushes)")
    if ps_sub:
        ps_str += f"; sub esp,{ps_sub:#x}"
    if rc_sub:
        rc_str += f"; sub esp,{rc_sub:#x}"
    frame_match = (ps_pushes == rc_pushes and ps_sub == rc_sub)
    if frame_match:
        typer.echo(f"   prologue         : ✓ PS = RC = {ps_str}")
    else:
        # describe the diff
        ps_set, rc_set = set(ps_pushes), set(rc_pushes)
        extra_rc = rc_set - ps_set
        extra_ps = ps_set - rc_set
        diff_bits = []
        if extra_rc:
            diff_bits.append(
                f"RC has extra callee-save: {' '.join(sorted(extra_rc))}")
        if extra_ps:
            diff_bits.append(
                f"PS has extra callee-save: {' '.join(sorted(extra_ps))}")
        if ps_sub != rc_sub:
            diff_bits.append(
                f"sub esp delta {rc_sub - ps_sub:+#x} (RC "
                f"{'larger' if rc_sub > ps_sub else 'smaller'} frame)")
        typer.echo(f"   prologue         : ✗ PS: {ps_str}")
        typer.echo(f"                      ✗ RC: {rc_str}")
        for db in diff_bits:
            typer.secho(f"                        → {db}", fg="yellow")
    if not ir_diffs:
        ir_msg = ("✓ identical ("
                  + ", ".join(f"{k}×{v}"
                              for k, v in sorted(ps_kinds.items())[:6])
                  + (" …" if len(ps_kinds) > 6 else "") + ")")
    else:
        ir_msg = (f"✗ differs ({len(ir_diffs)} kind(s): "
                  + ", ".join(f"{k}: PS{p}/RC{r}"
                              for k, p, r in ir_diffs[:5])
                  + (" …" if len(ir_diffs) > 5 else "") + ")")
    typer.echo(f"   IR-multiset      : {ir_msg}")
    color = ("green" if bdiff == 0 else
             "yellow" if structural else "red")
    typer.secho(f"   classification   : {cls}", fg=color, bold=True)


def _ps_call_sequence(ps_code: bytes, ps_start: int,
                      ps_recs: list) -> list:
    """Return ``[(call_name, ps_line, func_rel_off), ...]`` in order of
    occurrence in the PS function.

    Resolves call destinations against PS code symbols (so `call 0x6d12c`
    becomes `('unflag_all_cm', ...)`).
    """
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    try:
        d = json.loads(_SYMS.read_text())
    except Exception:
        return []
    code_syms = sorted(
        (s for s in d["symbols"]
         if s["kind"].endswith("code") and s["segment"] == 1),
        key=lambda s: s["offset"],
    )
    by_off = {s["offset"]: s["name"] for s in code_syms}
    # build (offset -> line) lookup using ps_recs
    rec_offs = [r["offset"] - ps_start for r in ps_recs]
    rec_lines = [r["line"] for r in ps_recs]
    out = []
    for ins in md.disasm(ps_code, ps_start):
        if ins.mnemonic == "call" and ins.op_str.startswith("0x"):
            tgt = int(ins.op_str, 16)
            nm = by_off.get(tgt)
            if not nm:
                continue
            rel = ins.address - ps_start
            # find the line mark whose span covers this offset
            j = bisect.bisect_right(rec_offs, rel) - 1
            ln = rec_lines[j] if j >= 0 else None
            out.append((nm, ln, rel))
    return out


def _mac_call_sequence(mac_src: str) -> list:
    """Return ``[(call_name, mac_lineno), ...]`` in order from the AST-cleaned
    Mac decompile output.

    Identifies calls by ``\\b<ident>\\s*\\(`` outside of obvious type-cast
    contexts.  Skips C keywords (if, while, switch, etc.) and a small list
    of Ghidra-generated cast helpers (``int``, ``short``, ``char``,
    ``byte``, ``undefined``, ``ushort``, ``uint``).
    """
    import re
    skip = {
        "if", "while", "for", "switch", "sizeof", "return",
        "int", "short", "char", "byte", "undefined", "ushort",
        "uint", "undefined1", "undefined2", "undefined4", "long",
        "unsigned", "signed", "void",
    }
    pat = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
    out = []
    for i, line in enumerate(mac_src.splitlines(), 1):
        for m in pat.finditer(line):
            nm = m.group(1)
            if nm in skip:
                continue
            out.append((nm, i))
    return out


def _match_call_sequences(ps_calls: list, mac_calls: list) -> dict:
    """Greedy in-order match by name.  Returns ``{ps_idx: mac_idx}``.

    For each PS call, advance through Mac calls until name matches; bind
    that pair, continue.  Handles N:M mismatch (extra Mac calls between
    matches, or PS tail-merged so Mac has more calls than PS).
    """
    out = {}
    mi = 0
    for pi, (pname, _pln, _po) in enumerate(ps_calls):
        while mi < len(mac_calls) and mac_calls[mi][0] != pname:
            mi += 1
        if mi >= len(mac_calls):
            break
        out[pi] = mi
        mi += 1
    return out


def _emit_ghidra_section(name: str) -> None:
    """Print Ghidra's C decompile of the ACTUAL PS.EXE target function (the
    Watcom build we are matching) -- the PS-side analogue of the Mac section.
    Together they bracket the source shape: Mac = CodeWarrior's reading of the
    SAME source; Ghidra/PS = the Watcom target we must reproduce byte-for-byte.
    Spins the read-only ghidra-cli bridge (slow only on first warmup), so it is
    flag-gated like the Mac/JVM section.
    """
    import subprocess
    typer.echo()
    typer.secho("## PS.EXE decompile  (ghidra-cli, Watcom-target C)",
                bold=True)
    typer.secho(f"   raw: `c2 decompile {name}`   "
                "the C reconstruction of the binary we are matching",
                dim=True)
    try:
        r = subprocess.run(
            ["ghidra-cli", "decompile", name],
            capture_output=True, text=True, timeout=180)
    except FileNotFoundError:
        typer.secho("   (ghidra-cli not on PATH -- skipped)", fg="yellow")
        return
    except subprocess.TimeoutExpired:
        typer.secho("   (ghidra-cli timed out)", fg="yellow")
        return
    if r.returncode != 0:
        typer.secho(f"   (ghidra-cli decompile failed: "
                    f"{(r.stderr or '').strip()[:120]})", fg="yellow")
        return
    out = r.stdout or ""
    # the bridge may prepend non-JSON bootstrap lines; locate the JSON array
    # and extract the `code` field (same shape c2 decompile parses).
    i = out.find("[")
    rec = None
    if i >= 0:
        try:
            recs = json.loads(out[i:])
            rec = next((x for x in recs if x.get("name") == name),
                       recs[0] if recs else None)
        except (json.JSONDecodeError, TypeError):
            rec = None
    if not rec or not rec.get("code"):
        typer.secho("   (no decompile output)", fg="yellow")
        return
    sig = rec.get("signature")
    if sig:
        typer.secho(f"   // {sig}  @ {rec.get('address', '?')}", dim=True)
    for line in rec["code"].strip().splitlines():
        typer.echo(f"   {line}")


def _mac_decompile_cached(name: str) -> bool:
    """True when the per-fn raw Mac decompile is already on disk (so the
    cleaned decompile is ~instant, no JVM).  An empty cache file is a
    recorded known-miss (function absent from the Mac binary) -> treat as
    cached (showing the 'not in Mac binary' note is cheap)."""
    try:
        return (Path(".c2-cache/mac/decompile") / f"{name}.c").exists()
    except OSError:
        return False


def _emit_mac_section(name: str, ps_calls: list | None = None) -> None:
    """Print the Mac PPC Ghidra decompile (AST-cleaned).

    Mac has NO source-line debug (PEF only carries function names via
    traceback tables), so we can't align it to PS/RC by asm offset.
    What we CAN do: match Mac call sites to PS call sites in order by
    name, and tag each matched Mac line with the PS line number
    containing that call -- giving partial per-row alignment for the
    structural anchors (call sites).

    Tail-merged PS code (one shared `call X; ret` epilogue serving
    several Mac call sites) shows as the first Mac call being tagged
    and the rest left bare -- the agent can see the merge happened.
    """
    typer.echo()
    try:
        from c2 import macref
        which = None
        for build in ("fr", "demo"):
            try:
                b = macref.get(build)
            except FileNotFoundError:
                continue
            if b.lookup(name):
                which = build
                break
        if which is None:
            typer.secho(
                f"## mac decompile: {name!r} not in Mac binary (port-specific?)",
                bold=True, fg="yellow")
            return
        typer.secho(
            f"## mac decompile  (PEF/CodeWarrior {which}, AST-cleaned)",
            bold=True)
        typer.secho(
            f"   raw PPC: `c2 mac-fn {name}`   "
            "call-name anchors tagged inline with PS line #",
            dim=True)
        import mac as macmod
        # decompile_clean is cache-aware: a cache hit returns instantly
        # (no JVM); a miss opens the project itself (~25s first call).
        src = macmod.decompile_clean(name)
        # compute per-mac-line PS tags
        mac_calls = _mac_call_sequence(src)
        ps_to_mac = {}
        if ps_calls:
            ps_to_mac = _match_call_sequences(ps_calls, mac_calls)
        # build {mac_lineno: ps_lineno_tag}
        mac_ln_to_ps: dict[int, int] = {}
        for pi, mi in ps_to_mac.items():
            _pname, ps_ln, _po = ps_calls[pi]
            _, mac_ln = mac_calls[mi]
            if ps_ln is not None:
                mac_ln_to_ps[mac_ln] = ps_ln
        for i, line in enumerate(src.splitlines(), 1):
            tag = mac_ln_to_ps.get(i)
            if tag is not None:
                # right-align the tag
                padded = line.ljust(80)
                typer.echo(f"   {padded}  [≈ PS#{tag}]")
            else:
                typer.echo(f"   {line}")
        # summary line
        if ps_calls:
            paired = len(ps_to_mac)
            typer.secho(
                f"   ({paired} of {len(ps_calls)} PS call(s) matched against "
                f"{len(mac_calls)} Mac call(s)"
                + (" -- PS tail-merge likely"
                   if paired < len(mac_calls) else "")
                + ")",
                dim=True)
    except Exception as e:
        typer.secho(f"## mac decompile: failed -- {e}", fg="red")


def _win_decompile_cached(name: str) -> bool:
    """True when the per-fn Windows decompile is already on disk (so the
    dossier section is ~instant, no JVM).  An empty cache file is a recorded
    known-miss (function absent/unmapped in the Win build) -> treat as cached."""
    try:
        return (Path(".c2-cache/win/decompile") / f"{name}.c").exists()
    except OSError:
        return False


def _emit_win_section(name: str, ps_calls: list | None = None) -> None:
    """Print the Windows CAESAR2.EXE decompile (MSVC 4.0 /Od).

    The Win95 build is MSVC 4.0 /Od of the SAME engine source as the DOS
    Watcom PS.EXE -- a second source-shape oracle, and being x86 +
    unoptimized it is often the MOST legible reading: params named+typed,
    globals named, every statement explicit.  Like the Mac stream it carries
    no -d1 line info, so call sites are tagged with the matching PS line # by
    in-order name matching (the structural anchors).
    """
    typer.echo()
    try:
        import c2win
        src = c2win.decompile_cached(name)
        if src is None:
            typer.secho(
                f"## win decompile: {name!r} not present/mapped in the "
                "Windows build", bold=True, fg="yellow")
            return
        typer.secho("## win decompile  (MSVC 4.0 /Od, x86 source-shape oracle)",
                    bold=True)
        typer.secho(
            f"   raw: `c2 win-decompile {name}`   "
            "named+typed; call anchors tagged inline with PS line #",
            dim=True)
        win_calls = _mac_call_sequence(src)   # same C-source call extractor
        ps_to_win = _match_call_sequences(ps_calls, win_calls) if ps_calls else {}
        win_ln_to_ps: dict[int, int] = {}
        for pi, wi in ps_to_win.items():
            _pname, ps_ln, _po = ps_calls[pi]
            _, win_ln = win_calls[wi]
            if ps_ln is not None:
                win_ln_to_ps[win_ln] = ps_ln
        for i, line in enumerate(src.splitlines(), 1):
            tag = win_ln_to_ps.get(i)
            if tag is not None:
                typer.echo(f"   {line.ljust(80)}  [≈ PS#{tag}]")
            else:
                typer.echo(f"   {line}")
        if ps_calls:
            paired = len(ps_to_win)
            typer.secho(
                f"   ({paired} of {len(ps_calls)} PS call(s) matched against "
                f"{len(win_calls)} Win call(s))", dim=True)
    except Exception as e:
        typer.secho(f"## win decompile: failed -- {e}", fg="red")
