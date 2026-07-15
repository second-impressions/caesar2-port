"""Cross-version function matcher for Caesar II PS.EXE variants.

Uses the debug symbols from the canonical PS.EXE (data/out/symbols.json)
to fuzzy-match functions in other PS.EXE variants from the CDs.

Strategy
--------
All variants are Watcom 10.0a builds of the same source — codegen is
extremely stable across releases.  The only inter-build noise is:

  * **Absolute address fixups** — every variant relinks at slightly
    different addresses, so absolute pointer literals differ.  Mask
    using the LE fixup table.
  * **Cross-function rel32 displacements** — `E8 rel32` (call) and
    `E9 rel32` (tail jmp) and `0F 8x rel32` (long Jcc) all carry
    link-time-resolved displacements.  Mask the 4 displacement bytes.

After both maskings, **byte-identical** is the common case for any
unchanged source function.

Pipeline:

  1. Build masked-prefix index of every named function in the
     reference (24-byte prefix, fixup-only mask).
  2. Build the same prefix index over the candidate's code section.
  3. **Phase A1** — Unique-prefix anchors.  Ref functions whose
     24-byte masked prefix appears exactly once in both ref and
     candidate are anchored 1:1.
  4. **Phase A2** — Greedy shared-prefix matching.  For ref
     functions sharing a prefix (mostly tiny stubs), score every
     (ref, cand) pair by full-body byte-diff and assign greedily,
     bounded to 30×30 groups.
  5. **Phase B** — Verify each anchor via full-body fingerprint
     (fixups + rel-disps masked) and bucket as exact / near (≤8 b
     diff) / differs.

Limitations
-----------
* No bound discovery for *unnamed* candidate functions — we anchor
  only what the reference's symbols.json knows about.  The remaining
  ~33% of named ref fns that don't anchor either changed
  significantly, were removed, or share too many prefixes for the
  greedy pass.
* Not a substitute for `decomp-verify` — this is recon, not
  ground-truth byte comparison.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional

import capstone
import typer

from c2.commands.decomp_verify import _load_le_code_and_fixups


_CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_CS.detail = False

PREFIX_LEN = 24


# ── Masking helpers ───────────────────────────────────────────────────────────

def _rel_disp_mask(code: bytes) -> set[int]:
    """Byte offsets within `code` holding rel32 displacements of
    cross-instruction jumps/calls (E8, E9, 0F 8x). These bytes carry
    link-time-resolved offsets that vary across builds."""
    m: set[int] = set()
    for ins in _CS.disasm(code, 0):
        b0 = ins.bytes[0]
        if ins.size == 5 and b0 in (0xE8, 0xE9):
            m.update(range(ins.address + 1, ins.address + 5))
        elif ins.size == 6 and b0 == 0x0F and 0x80 <= ins.bytes[1] <= 0x8F:
            m.update(range(ins.address + 2, ins.address + 6))
    return m


def _masked_body(body: bytes, fixups: set[int]) -> bytes:
    """Zero-out fixup bytes and rel-disp bytes in `body`."""
    out = bytearray(body)
    for off in fixups | _rel_disp_mask(bytes(body)):
        if 0 <= off < len(out):
            out[off] = 0
    return bytes(out)


def _fingerprint(body: bytes, fixups: set[int]) -> str:
    return hashlib.sha1(_masked_body(body, fixups)).hexdigest()


# ── Reference build ──────────────────────────────────────────────────────────

@dataclass
class RefFn:
    name: str
    addr: int
    size: int
    fp: str            # full-body fingerprint
    masked: bytes      # full-body masked bytes (for byte-diff)
    prefix_fixonly: bytes  # fixup-only-masked first PREFIX_LEN bytes
    module_index: int  # translation-unit index (-1 if unknown)


@dataclass
class RefIndex:
    code: bytes
    fixups: set[int]
    code_base: int
    fns: dict[int, RefFn]                # keyed by absolute LE address
    by_prefix: dict[bytes, list[int]]    # fixup-only-masked prefix → addresses
    modules: dict[int, list[int]]        # module_index → sorted addresses

    @property
    def names(self) -> list[str]:
        return [f.name for f in self.fns.values()]


def build_reference(symbols_json: Path, exe_path: Path) -> RefIndex:
    sym = json.loads(symbols_json.read_text())
    code_base = sym["memory_map"]["objects"][0]["base_address_int"]
    code, fixups = _load_le_code_and_fixups(exe_path)

    code_syms = sorted(
        [s for s in sym["symbols"] if s.get("is_code")],
        key=lambda s: s["address"],
    )

    fns: dict[int, RefFn] = {}
    by_prefix: dict[bytes, list[int]] = defaultdict(list)
    for i, s in enumerate(code_syms):
        addr = s["address"]
        if addr in fns:
            # Duplicate addresses shouldn't happen, but be defensive.
            continue
        nxt = (
            code_syms[i + 1]["address"] if i + 1 < len(code_syms)
            else code_base + len(code)
        )
        size = nxt - addr
        if size <= 0 or size > 1 << 20:
            continue
        rva = addr - code_base
        body = code[rva : rva + size]
        local_fix = {b - rva for b in fixups if rva <= b < rva + size}
        fp = _fingerprint(body, local_fix)
        masked = _masked_body(body, local_fix)
        # Fixup-only-masked prefix (no rel-disp masking — would require
        # per-window disasm and slows the cand-side index hugely; the
        # first PREFIX_LEN bytes of a function are usually pure prologue
        # and rarely contain a rel32 call).
        if size >= PREFIX_LEN:
            pmask = bytearray(body[:PREFIX_LEN])
            for off in local_fix:
                if off < PREFIX_LEN:
                    pmask[off] = 0
            prefix_fo = bytes(pmask)
            by_prefix[prefix_fo].append(addr)
        else:
            prefix_fo = b""
        fns[addr] = RefFn(
            name=s["name"], addr=addr, size=size,
            fp=fp, masked=masked, prefix_fixonly=prefix_fo,
            module_index=s.get("module_index", -1),
        )

    # Build module → sorted-address index.  Watcom links each TU's
    # functions contiguously in source order, so address order ==
    # source order within each module.
    modules: dict[int, list[int]] = defaultdict(list)
    for addr, rf in fns.items():
        if rf.module_index >= 0:
            modules[rf.module_index].append(addr)
    for mi in modules:
        modules[mi].sort()

    return RefIndex(
        code=code, fixups=fixups, code_base=code_base,
        fns=fns, by_prefix=by_prefix, modules=dict(modules),
    )


# ── Candidate matching ───────────────────────────────────────────────────────

@dataclass
class Match:
    name: str
    ref_addr: int
    ref_size: int
    cand_off: int
    diff_bytes: int       # masked byte-diff (0 == byte-identical)
    status: str           # "exact" | "near" | "differs"
    method: str           # "unique-prefix" | "shared-prefix"


@dataclass
class MatchResult:
    variant: str
    cand_size: int
    cand_code_size: int
    matches: list[Match]
    unmatched_refs: list["RefFn"]   # ref fns we couldn't anchor
    ambiguous_groups: int           # shared-prefix groups skipped (too big)


def _build_cand_prefix_index(
    code: bytes, fixups: set[int], prefix_len: int = PREFIX_LEN,
) -> tuple[bytes, dict[bytes, list[int]]]:
    """Return (fixup-masked code copy, prefix → list[offsets])."""
    masked = bytearray(code)
    for off in fixups:
        if 0 <= off < len(masked):
            masked[off] = 0
    masked_b = bytes(masked)
    idx: dict[bytes, list[int]] = defaultdict(list)
    for i in range(0, len(masked_b) - prefix_len + 1):
        idx[masked_b[i : i + prefix_len]].append(i)
    return masked_b, idx


def _verify(
    ref: RefIndex, addr: int,
    cand_code: bytes, cand_fix: set[int], cand_off: int,
) -> tuple[int, str]:
    """Compute byte-diff at cand_off, return (diff_bytes, status)."""
    rf = ref.fns[addr]
    if cand_off + rf.size > len(cand_code):
        return rf.size, "differs"
    body = cand_code[cand_off : cand_off + rf.size]
    local_fix = {b - cand_off for b in cand_fix
                 if cand_off <= b < cand_off + rf.size}
    cm = _masked_body(body, local_fix)
    rm = rf.masked
    L = min(len(cm), len(rm))
    db = sum(1 for i in range(L) if cm[i] != rm[i]) + abs(len(cm) - len(rm))
    if db == 0:
        return 0, "exact"
    elif db <= 8:
        return db, "near"
    return db, "differs"


def _score_pair(ref: RefIndex, addr: int,
                cand_code: bytes, cand_fix: set[int], cand_off: int) -> int:
    """Score a (ref, cand) pair by masked byte-diff. Returns size on
    out-of-bounds (treated as worst-case mismatch)."""
    rf = ref.fns[addr]
    if cand_off + rf.size > len(cand_code):
        return rf.size
    body = cand_code[cand_off : cand_off + rf.size]
    lf = {b - cand_off for b in cand_fix if cand_off <= b < cand_off + rf.size}
    cm = _masked_body(body, lf)
    rm = rf.masked
    L = min(len(cm), len(rm))
    return sum(1 for i in range(L) if cm[i] != rm[i]) + abs(len(cm) - len(rm))


def match_variant(ref: RefIndex, variant_path: Path) -> MatchResult:
    cand_code, cand_fix = _load_le_code_and_fixups(variant_path)
    _, cand_idx = _build_cand_prefix_index(cand_code, cand_fix, PREFIX_LEN)

    # Pre-mask candidate (fixup-only) once for full-body searches.
    cand_masked = bytearray(cand_code)
    for off in cand_fix:
        if 0 <= off < len(cand_masked):
            cand_masked[off] = 0
    cand_masked_b = bytes(cand_masked)

    matches: list[Match] = []
    matched_addrs: set[int] = set()

    # Phase A0 — sub-PREFIX_LEN tiny functions.  For each ref fn smaller
    # than PREFIX_LEN, search candidate's fixup-masked code for the exact
    # masked body bytes.  Anchor unique hits.  Catches CRT helpers like
    # `flushall`, `_radclose`, `__begtext` that are too small to have a
    # 24-byte prefix.
    tiny_by_body: dict[bytes, list[int]] = defaultdict(list)
    for addr, rf in ref.fns.items():
        if rf.size < PREFIX_LEN:
            tiny_by_body[rf.masked].append(addr)
    for body, addrs in tiny_by_body.items():
        if not body:  # zero-size sentinel
            continue
        # Find all occurrences of `body` in cand_masked_b
        offs: list[int] = []
        start = 0
        while True:
            p = cand_masked_b.find(body, start)
            if p < 0:
                break
            offs.append(p)
            start = p + 1
        if not offs:
            continue
        if len(addrs) == 1 and len(offs) == 1:
            addr = addrs[0]
            rf = ref.fns[addr]
            matches.append(Match(
                name=rf.name, ref_addr=rf.addr, ref_size=rf.size,
                cand_off=offs[0], diff_bytes=0, status="exact",
                method="tiny-body",
            ))
            matched_addrs.add(addr)
        elif len(addrs) > 1 and len(addrs) == len(offs):
            # Same number of refs and cand hits — if all share a single
            # masked body we can't tell them apart by body alone, so
            # assign in address order to offset-sorted hits.  Cheap
            # heuristic; collapses on perfect duplicates as expected.
            for a, o in zip(sorted(addrs), sorted(offs)):
                rf = ref.fns[a]
                matches.append(Match(
                    name=rf.name, ref_addr=rf.addr, ref_size=rf.size,
                    cand_off=o, diff_bytes=0, status="exact",
                    method="tiny-body",
                ))
                matched_addrs.add(a)

    # Phase A1 — unique-prefix 1:1
    # When multiple cand offsets exist for a prefix that is unique in ref,
    # take the one with the lowest masked byte-diff (typically zero =
    # byte-identical).  The simple "len(offs) == 1" rule misses self-
    # match cases where a function's prologue happens to also occur
    # somewhere else in the candidate code.
    for prefix, addrs in ref.by_prefix.items():
        if len(addrs) != 1:
            continue
        offs = cand_idx.get(prefix, [])
        if not offs:
            continue
        addr = addrs[0]
        # Pick best-matching candidate offset by full-body diff.
        best = min(offs, key=lambda o: _score_pair(ref, addr, cand_code, cand_fix, o))
        rf = ref.fns[addr]
        db, status = _verify(ref, addr, cand_code, cand_fix, best)
        # Reject obvious mismatches (>50% of body diffs) — better to
        # leave the function unmatched than emit a false anchor.
        if db > rf.size * 0.50:
            continue
        matches.append(Match(
            name=rf.name, ref_addr=rf.addr, ref_size=rf.size,
            cand_off=best, diff_bytes=db, status=status,
            method="unique-prefix",
        ))
        matched_addrs.add(addr)

    # Phase A2 — shared-prefix greedy
    ambiguous = 0
    for prefix, addrs in ref.by_prefix.items():
        if len(addrs) <= 1:
            continue
        offs = cand_idx.get(prefix, [])
        if not offs:
            continue
        rem_addrs = [a for a in addrs if a not in matched_addrs]
        if not rem_addrs:
            continue
        if len(rem_addrs) > 30 or len(offs) > 30:
            ambiguous += 1
            continue
        pairs: list[tuple[int, int, int]] = []
        for a in rem_addrs:
            for o in offs:
                db = _score_pair(ref, a, cand_code, cand_fix, o)
                pairs.append((db, a, o))
        pairs.sort()
        used_a: set[int] = set()
        used_o: set[int] = set()
        for db, a, o in pairs:
            if a in used_a or o in used_o:
                continue
            rf = ref.fns[a]
            if db > rf.size * 0.25 + 4:
                break
            status = "exact" if db == 0 else ("near" if db <= 8 else "differs")
            matches.append(Match(
                name=rf.name, ref_addr=rf.addr, ref_size=rf.size,
                cand_off=o, diff_bytes=db, status=status,
                method="shared-prefix",
            ))
            matched_addrs.add(a)
            used_a.add(a); used_o.add(o)

    # Phase A3 — module interpolation.
    #
    # Watcom links each translation unit's functions contiguously and in
    # source order, so within a module (== source file) the binary layout
    # is a fixed sequence of fn-bodies in address order.  Whenever we have
    # two anchored functions in the same module with one or more
    # *unanchored* functions between them in source order, and the
    # candidate gap (cand_off_b - cand_off_a - size_a) equals the ref
    # gap (sum of unanchored sizes), we can pin every gap function by
    # cumulative-offset arithmetic.  This catches:
    #   * Tiny stubs that escaped Phases A0–A2 because their masked
    #     body matches multiple positions in the candidate (ambiguous
    #     by content alone, but unambiguous by module position).
    #   * Mid-size functions whose first 24 bytes drifted enough to
    #     miss prefix anchoring but whose body is still byte-exact.
    interp_added = 0
    for mi, addrs in ref.modules.items():
        # Anchors in this module, ordered by source position.
        anchored: list[tuple[int, int]] = [
            (a, next(m for m in matches if m.ref_addr == a).cand_off)
            for a in addrs if a in matched_addrs
        ]
        if len(anchored) < 2:
            continue
        # For each consecutive pair of anchors, look at the source-order
        # range between them.
        for i in range(len(anchored) - 1):
            a_lo, off_lo = anchored[i]
            a_hi, off_hi = anchored[i + 1]
            # Index range in addrs.
            i_lo = addrs.index(a_lo)
            i_hi = addrs.index(a_hi)
            gap_addrs = addrs[i_lo + 1 : i_hi]
            if not gap_addrs:
                continue
            ref_gap = ref.fns[a_hi].addr - (ref.fns[a_lo].addr + ref.fns[a_lo].size)
            cand_gap = off_hi - (off_lo + ref.fns[a_lo].size)
            # Sizes must match exactly between ref and cand (no
            # functions added/removed/resized in this gap).
            if ref_gap != cand_gap:
                continue
            # Walk gap_addrs in source order, advancing cand_off by
            # each fn's ref-size.  Verify every body matches.
            cur_cand = off_lo + ref.fns[a_lo].size
            cur_ref = ref.fns[a_lo].addr + ref.fns[a_lo].size
            new_anchors: list[Match] = []
            ok = True
            for ga in gap_addrs:
                rf = ref.fns[ga]
                if rf.addr != cur_ref:
                    # Module addr layout has a hole the ref didn't
                    # account for — abandon this gap.
                    ok = False
                    break
                db, status = _verify(ref, ga, cand_code, cand_fix, cur_cand)
                # We accept any diff here — the position is locked by
                # module geometry, not by content.  Larger diffs simply
                # bucket as "differs".
                new_anchors.append(Match(
                    name=rf.name, ref_addr=rf.addr, ref_size=rf.size,
                    cand_off=cur_cand, diff_bytes=db, status=status,
                    method="module-interp",
                ))
                cur_cand += rf.size
                cur_ref += rf.size
            if ok:
                for m in new_anchors:
                    if any(a == m.ref_addr for a in matched_addrs):
                        continue
                    matches.append(m)
                    matched_addrs.add(m.ref_addr)
                    interp_added += 1

    # Phase A4 — module head/tail extension.  When a module has at
    # least one anchor, walk source-order *before* the first anchor and
    # *after* the last anchor: the candidate offsets are still locked
    # by cumulative size from the anchor, provided that fn sizes haven't
    # changed.  We bound the walk to functions with the same module_index
    # only — we can't safely cross module boundaries because the
    # candidate may have inserted/removed entire TUs.
    for mi, addrs in ref.modules.items():
        anchored = [(a, next(m for m in matches if m.ref_addr == a).cand_off)
                    for a in addrs if a in matched_addrs]
        if not anchored:
            continue
        # Extend backward from first anchor.
        a0, off0 = anchored[0]
        i0 = addrs.index(a0)
        cur_ref = ref.fns[a0].addr
        cur_cand = off0
        for ga in reversed(addrs[:i0]):
            rf = ref.fns[ga]
            if rf.addr + rf.size != cur_ref:
                break  # gap in ref module addrs — give up
            cur_ref -= rf.size
            cur_cand -= rf.size
            if cur_cand < 0:
                break
            if ga in matched_addrs:
                continue
            db, status = _verify(ref, ga, cand_code, cand_fix, cur_cand)
            if db > rf.size * 0.50:
                break  # likely off the rails — stop walking
            matches.append(Match(
                name=rf.name, ref_addr=rf.addr, ref_size=rf.size,
                cand_off=cur_cand, diff_bytes=db, status=status,
                method="module-head",
            ))
            matched_addrs.add(ga)
            interp_added += 1
        # Extend forward from last anchor.
        aN, offN = anchored[-1]
        iN = addrs.index(aN)
        cur_ref = ref.fns[aN].addr + ref.fns[aN].size
        cur_cand = offN + ref.fns[aN].size
        for ga in addrs[iN + 1 :]:
            rf = ref.fns[ga]
            if rf.addr != cur_ref:
                break
            if cur_cand + rf.size > len(cand_code):
                break
            if ga in matched_addrs:
                cur_cand += rf.size
                cur_ref += rf.size
                continue
            db, status = _verify(ref, ga, cand_code, cand_fix, cur_cand)
            if db > rf.size * 0.50:
                break
            matches.append(Match(
                name=rf.name, ref_addr=rf.addr, ref_size=rf.size,
                cand_off=cur_cand, diff_bytes=db, status=status,
                method="module-tail",
            ))
            matched_addrs.add(ga)
            interp_added += 1
            cur_cand += rf.size
            cur_ref += rf.size

    matches.sort(key=lambda m: m.ref_addr)
    unmatched = sorted(
        [ref.fns[a] for a in (set(ref.fns) - matched_addrs)],
        key=lambda rf: rf.addr,
    )

    return MatchResult(
        variant=str(variant_path),
        cand_size=variant_path.stat().st_size,
        cand_code_size=len(cand_code),
        matches=matches,
        unmatched_refs=unmatched,
        ambiguous_groups=ambiguous,
    )


# ── CLI ──────────────────────────────────────────────────────────────────────

def _print_result(r: MatchResult, ref: RefIndex, *,
                  full: bool, show_unmatched: bool) -> None:
    total_ref = len(ref.fns)
    n_match = len(r.matches)
    by_status = Counter(m.status for m in r.matches)
    by_method = Counter(m.method for m in r.matches)
    print(f"variant: {r.variant}")
    print(f"  file size:      {r.cand_size:>10,d}")
    print(f"  code section:   {r.cand_code_size:>10,d}")
    print()
    print(f"  reference fns:  {total_ref:>5}")
    print(f"  anchored:       {n_match:>5}  ({n_match/total_ref*100:.1f}%)")
    method_str = "  ".join(f"{k}={v}" for k, v in by_method.most_common())
    print(f"    by method:    {method_str}")
    print(f"    exact:        {by_status['exact']:>5}  ({by_status['exact']/total_ref*100:.1f}% of all ref fns)")
    print(f"    near (≤8 b):  {by_status['near']:>5}")
    print(f"    differs:      {by_status['differs']:>5}")
    print(f"  unmatched refs: {len(r.unmatched_refs):>5}")
    if r.ambiguous_groups:
        print(f"  ambiguous groups skipped: {r.ambiguous_groups}")

    if full:
        print()
        print(f"{'status':8s} {'method':14s} {'name':38s} {'ref_addr':>10s} {'size':>6s} {'cand_off':>10s} {'diff':>6s}")
        for m in r.matches:
            print(f"{m.status:8s} {m.method:14s} {m.name:38s} 0x{m.ref_addr:08x} {m.ref_size:>6d} 0x{m.cand_off:08x} {m.diff_bytes:>6d}")
    else:
        non_exact = [m for m in r.matches if m.status != "exact"]
        if non_exact:
            print()
            print(f"Non-exact matches ({len(non_exact)}):")
            print(f"  {'status':8s} {'name':38s} {'size':>6s} {'diff':>6s}  cand_off")
            for m in non_exact:
                print(f"  {m.status:8s} {m.name:38s} {m.ref_size:>6d} {m.diff_bytes:>6d}  0x{m.cand_off:08x}")

    if show_unmatched and r.unmatched_refs:
        print()
        print(f"Unmatched reference functions ({len(r.unmatched_refs)}):")
        for rf in r.unmatched_refs:
            print(f"  {rf.name:38s}  0x{rf.addr:08x}  size={rf.size}")


def version_match(
    variant: Annotated[
        Path,
        typer.Argument(help="Path to a Watcom-built PS.EXE variant to compare against the reference."),
    ],
    reference: Annotated[
        Path,
        typer.Option("--reference", "-r", help="Reference PS.EXE (the one symbols.json was built from)."),
    ] = Path("data/PS.EXE"),
    symbols: Annotated[
        Path,
        typer.Option("--symbols", "-s", help="symbols.json with reference function table."),
    ] = Path("data/out/symbols.json"),
    full: Annotated[
        bool,
        typer.Option("--full", help="Print every anchored function (default: only non-exact)."),
    ] = False,
    show_unmatched: Annotated[
        bool,
        typer.Option("--unmatched", help="List reference functions that could not be anchored."),
    ] = False,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit a machine-readable JSON report instead of text."),
    ] = False,
) -> None:
    """Match named functions from a reference PS.EXE into an unlabelled variant.

    Useful for:
      * Identifying which functions changed between PS.EXE releases.
      * Importing reference symbol names into a Ghidra project for a
        previously-unanalysed variant.
      * Spotting decompilation regressions where a function we thought
        was canonical actually shifted between releases.

    Reads the canonical symbols (default: ``data/out/symbols.json``) and
    the reference PS.EXE bytes (default: ``data/PS.EXE``), then matches
    each named function into ``variant`` via masked-prefix anchoring +
    full-body byte comparison.  See module docstring for the full
    algorithm.
    """
    ref = build_reference(symbols, reference)
    result = match_variant(ref, variant)

    if json_out:
        out = {
            "variant": result.variant,
            "variant_size": result.cand_size,
            "code_size": result.cand_code_size,
            "reference_fns": len(ref.fns),
            "anchored": len(result.matches),
            "ambiguous_groups": result.ambiguous_groups,
            "matches": [
                {
                    "name": m.name, "status": m.status, "method": m.method,
                    "ref_addr": m.ref_addr, "ref_size": m.ref_size,
                    "cand_off": m.cand_off, "diff_bytes": m.diff_bytes,
                }
                for m in result.matches
            ],
            "unmatched": [
                {"name": rf.name, "addr": rf.addr, "size": rf.size}
                for rf in result.unmatched_refs
            ],
        }
        print(json.dumps(out, indent=2))
        return

    _print_result(result, ref, full=full, show_unmatched=show_unmatched)
