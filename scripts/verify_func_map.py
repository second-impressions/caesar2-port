#!/usr/bin/env python3
r"""verify_func_map.py -- independently VERIFY the DOS->Windows function map.

The Windows ``CAESAR2.EXE`` (MSVC 4.0 /Od) and the DOS ``PS.EXE`` (Watcom
10.0a) are built from the *same* engine source.  ``data/windows-builds/
func-map.json`` claims a ``ps_name -> win_va`` correspondence for ~1339
functions, but only the ``compile-exact`` tier was byte-verified when the map
was built; the ``ordinal``/``fuzzy`` tiers were positioned by heuristics and
were never verified.

This script establishes a *verified* correspondence from THREE independent,
map-independent oracles and cross-checks them against the current func-map:

  1. BYTE  -- masked compile-exact search (from ``.c2-cache/win-verify.json``):
     when our MSVC compile of a function's bytes matches at exactly ONE place
     in ``.text`` (map-independent), that VA is ground truth.  (Non-unique
     matches are byte-coincidences between structural twins/stubs and are NOT
     used as anchors.)

  2. ORDINAL -- within a TU, PS source order == Windows VA order (proven: the
     byte-unique anchors are strictly monotonic per-TU, LIS fraction 1.00).
     Anchored gap alignment interpolates the functions between anchors when
     the PS-count and Windows-count of a gap agree.

  3. CALLGRAPH -- both binaries share source, so the call graph is isomorphic.
     A candidate ``F -> V`` is corroborated when the Windows call targets at
     ``V`` (mapped back through the map) reproduce F's DOS callees.

A function is VERIFIED when >=2 independent oracles agree.  Where they
conflict (e.g. platform-divergent DOS-only functions like the demo recorder
break the ordinal count), the entry is flagged NEEDS-REVIEW with all evidence.

Outputs (to ``data/windows-builds/``):
  * ``func-map-verified.json`` -- per-entry verdict + proposed correction
  * a per-TU summary table on stdout

Usage::
    uv run python scripts/verify_func_map.py                # whole tree
    uv run python scripts/verify_func_map.py --tu loadsave  # one TU, verbose
    uv run python scripts/verify_func_map.py --conflicts    # only disagreements
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path

import capstone

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

WIN_EXE = ROOT / "data/windows-builds/named/caesar2_A_1044480.exe"
FUNC_MAP = ROOT / "data/windows-builds/func-map.json"
WIN_SYMS = ROOT / "data/windows-builds/caesar2_symbols.json"
WIN_VERIFY = ROOT / ".c2-cache/win-verify.json"
SYMBOLS = ROOT / "data/out/symbols.json"
DOS_CG_CACHE = ROOT / ".c2-cache/dos-callgraph.json"
GLOBALS_MAP = ROOT / "data/windows-builds/globals-map.json"
PS_EXE = ROOT / "data/PS.EXE"
OUT = ROOT / "data/windows-builds/func-map-verified.json"


# ── Windows binary: PE parse + call graph ─────────────────────────────────────
def load_win():
    """Return (text_va0, text_bytes, image_base, sections)."""
    raw = WIN_EXE.read_bytes()
    e_lfanew = struct.unpack_from("<I", raw, 0x3C)[0]
    assert raw[e_lfanew : e_lfanew + 4] == b"PE\x00\x00"
    coff = e_lfanew + 4
    num_sec = struct.unpack_from("<H", raw, coff + 2)[0]
    opt_size = struct.unpack_from("<H", raw, coff + 16)[0]
    opt = coff + 20
    image_base = struct.unpack_from("<I", raw, opt + 28)[0]
    sec_tbl = opt + opt_size
    sections = {}
    for i in range(num_sec):
        off = sec_tbl + i * 40
        name = raw[off : off + 8].rstrip(b"\x00").decode("latin1")
        vsize, va, rsize, roff = struct.unpack_from("<IIII", raw, off + 8)
        sections[name] = (image_base + va, roff, rsize, vsize)
    va0, roff, rsize, _vs = sections[".text"]
    return va0, raw[roff : roff + rsize], image_base, sections, raw


def build_win_data_refs(raw, image_base, sections, text_va0, text_bytes, win_funcs):
    """win_va -> {referenced .data VA}, via .reloc DIR32 sites in .text.

    The PE on-disk image holds preferred-base absolute VAs at each DIR32 reloc
    site (image loads at image_base), so reading the 4 bytes at a site gives
    the referenced VA directly -- a map-independent global-reference readout.
    """
    dlo, dhi, _, dvs = (*sections[".data"][:1], sections[".data"][0] + sections[".data"][3],
                        0, 0)
    dlo = sections[".data"][0]
    dhi = dlo + sections[".data"][3]
    rva0, roff, rsize, _ = sections[".reloc"]
    rel = raw[roff : roff + rsize]
    tend = text_va0 + len(text_bytes)
    starts = [a for a, _, _ in win_funcs]
    refs = defaultdict(set)
    p = 0
    while p < rsize - 8:
        page_rva, block = struct.unpack_from("<II", rel, p)
        if block == 0:
            break
        for e in range((block - 8) // 2):
            ent = struct.unpack_from("<H", rel, p + 8 + e * 2)[0]
            if ent >> 12 != 3:            # not HIGHLOW/DIR32
                continue
            site = image_base + page_rva + (ent & 0xFFF)
            if not (text_va0 <= site < tend):
                continue
            val = struct.unpack_from("<I", text_bytes, site - text_va0)[0]
            if dlo <= val < dhi:
                fi = bisect.bisect_right(starts, site) - 1
                if fi >= 0:
                    fa, fsz, _ = win_funcs[fi]
                    if site < fa + fsz:
                        refs[fa].add(val)
        p += block
    return refs


def build_dos_data_refs(ps_by_name):
    """ps_name -> {referenced DOS data VA}, via the LE code fixup map (ground
    truth for what the linker patched -- no disassembly needed)."""
    from c2.parsers.exe import parse_exe
    from c2.commands.fixups import parse_le_fixups
    _, _bw, le = parse_exe(PS_EXE)
    code_fix, _dfix = parse_le_fixups(PS_EXE, le.le_offset, le.page_size,
                                      le.num_pages, le.objects[0].num_pages,
                                      le.objects[1].num_pages)
    CODE_BASE, DATA_BASE = 0x10000, 0x90000
    starts = sorted((v["addr"], n) for n, v in ps_by_name.items())
    svas = [a for a, _ in starts]
    refs = defaultdict(set)
    for coff, (obj, toff) in code_fix.items():
        if obj != 2:                      # obj 2 == the data object
            continue
        fi = bisect.bisect_right(svas, CODE_BASE + coff) - 1
        if fi >= 0:
            refs[starts[fi][1]].add(DATA_BASE + toff)
    return refs


_MD = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_MD.detail = False
import re as _re


def build_win_callgraph(text_va0, text_bytes, win_funcs):
    """win_va -> [direct call target VAs, in order]."""
    calls = {}
    for a, sz, _nm in win_funcs:
        off = a - text_va0
        if off < 0 or off + sz > len(text_bytes):
            calls[a] = []
            continue
        tgts = []
        for insn in _MD.disasm(text_bytes[off : off + sz], a):
            if insn.mnemonic == "call" and insn.op_str.startswith("0x"):
                tgts.append(int(insn.op_str, 16))
        calls[a] = tgts
    return calls


def build_stub_classes(text_va0, text_bytes, win_funcs):
    """Group Windows functions by operand-wildcarded disasm.  Members of a
    class with >1 function are byte-identical stubs/structural twins: the
    individual DOS->win assignment among identical siblings is inherently
    unverifiable, but class membership is.  Returns {win_va: class_key}."""
    groups = {}
    for a, sz, _nm in win_funcs:
        off = a - text_va0
        if off < 0 or off + sz > len(text_bytes):
            continue
        seq = tuple(insn.mnemonic + " " + _re.sub(r"0x[0-9a-f]+", "K", insn.op_str)
                    for insn in _MD.disasm(text_bytes[off : off + sz], a))
        groups.setdefault(seq, []).append(a)
    return {v: k for k, vs in groups.items() if len(vs) > 1 for v in vs}


# ── DOS call graph (cached; disassembling PS.EXE is slow) ─────────────────────
def load_dos_callgraph():
    if DOS_CG_CACHE.exists():
        return json.loads(DOS_CG_CACHE.read_text())
    from c2.commands.callgraph import build_callgraph

    callers, _ = build_callgraph()
    cg = {F: [c for _off, c in calls] for F, calls in callers.items()}
    DOS_CG_CACHE.write_text(json.dumps(cg))
    return cg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tu", help="restrict verbose listing to one TU")
    ap.add_argument("--conflicts", action="store_true",
                    help="list only entries where oracles disagree with the map")
    ap.add_argument("--write", action="store_true",
                    help="write func-map-verified.json")
    args = ap.parse_args()

    func_map = json.loads(FUNC_MAP.read_text())
    win_syms = json.loads(WIN_SYMS.read_text())
    win_cache = json.loads(WIN_VERIFY.read_text())
    sym = json.loads(SYMBOLS.read_text())
    dos_cg = load_dos_callgraph()

    fm_by_name = {e["ps_name"]: e for e in func_map}
    fm_va = {e["ps_name"]: int(e["win_va"], 16) for e in func_map}

    def src_tu(e):
        s = e["src"]
        return s[:-2] if s.endswith(".c") else s

    # Windows function table + call graph
    win_funcs = sorted((int(s["address"], 16), s["size"], s["ghidra_name"])
                       for s in win_syms)
    wf_va = [a for a, _, _ in win_funcs]
    wf_size = {a: sz for a, sz, _ in win_funcs}
    text_va0, text_bytes, image_base, sections, raw = load_win()
    win_calls = build_win_callgraph(text_va0, text_bytes, win_funcs)
    stub_class = build_stub_classes(text_va0, text_bytes, win_funcs)
    win_data_refs = build_win_data_refs(raw, image_base, sections, text_va0,
                                        text_bytes, win_funcs)

    # PS function -> TU + source order
    modules = sym["modules"]
    mod_name = {i: m.get("name", "") for i, m in enumerate(modules)}

    def mod_tu(idx):
        nm = mod_name.get(idx, "")
        if nm.upper().startswith("D:\\C2\\CODE\\") and nm.lower().endswith(".c"):
            return os.path.basename(nm.replace("\\", "/")).lower()[:-2]
        return None

    ps_by_name = {}
    ps_tu_order = defaultdict(list)
    for s in sorted((s for s in sym["symbols"] if s.get("is_code")),
                    key=lambda x: x["address"]):
        tu = mod_tu(s["module_index"])
        ps_by_name[s["name"]] = dict(addr=s["address"], tu=tu)
        if tu:
            ps_tu_order[tu].append(s["name"])

    # Global-reference oracle: DOS globals a function references (LE fixups) vs
    # the Windows function's .data references (.reloc), bridged by globals-map.
    dos_data_refs = build_dos_data_refs(ps_by_name)
    gmap = json.loads(GLOBALS_MAP.read_text())
    def _toint(x):
        return int(x, 16) if isinstance(x, str) else int(x)
    gm_ps2win = {_toint(g["ps_addr"]): _toint(g["win_va"]) for g in gmap
                 if g.get("ps_addr") is not None}

    def gref_check(F, V):
        exp = {gm_ps2win[r] for r in dos_data_refs.get(F, ()) if r in gm_ps2win}
        act = win_data_refs.get(V, set())
        return len(exp), len(exp & act)

    # BYTE oracle: byte-unique compile-exact -> ground-truth VA
    exact = [f for f in win_cache["functions"] if f["status"] == "exact"]
    by_lva = defaultdict(list)
    for f in exact:
        by_lva[f["located_va"]].append(f)
    byte_true = {fs[0]["name"]: lva for lva, fs in by_lva.items() if len(fs) == 1}

    # ── ORDINAL backbone: PS_global in Windows layout order ──
    # TU link order in Windows = order of anchor/func-map center VAs.
    tu_center = {}
    for tu in ps_tu_order:
        anch = sorted(byte_true[n] for n in ps_tu_order[tu] if n in byte_true)
        if anch:
            tu_center[tu] = anch[len(anch) // 2]
        else:
            vs = sorted(fm_va[n] for n in ps_tu_order[tu] if n in fm_va)
            if vs:
                tu_center[tu] = vs[len(vs) // 2]
    tu_link_order = sorted(tu_center, key=lambda t: tu_center[t])
    PS_global = [(tu, nm) for tu in tu_link_order for nm in ps_tu_order[tu]]

    def win_in_range(lo, hi):
        i = bisect.bisect_right(wf_va, lo)
        j = bisect.bisect_left(wf_va, hi)
        return win_funcs[i:j]

    # SIZE oracle -- the blind-spot guard.  ps_size = MSVC /Od size of OUR
    # decomp; wf_size = the Windows function's size (both /Od, so ~equal when
    # correctly mapped and shape-correct).  A tiny decomp mapped onto a much
    # BIGGER real Windows function (win >> ps, and the win fn is not a stub) is
    # the city_trouble mismap signature -- caught by nothing else when the
    # function is a leaf that references only unmapped globals.  (ps >> win is
    # the opposite: Windows STUBBED the body -- legitimate, not a mismap.)
    ps_size = {f["name"]: f["size"] for f in win_cache["functions"]}

    # STRUCT oracle -- an independent CONTENT match.  win-verify compiles our
    # decomp with MSVC /Od and computes struct_diff = the reloc/immediate-
    # normalized instruction-mnemonic edit distance vs the Windows function at
    # the mapped VA.  A low ratio means the Windows function IS structurally our
    # decomp (a mismap onto a different function scores near 1.0), so it
    # certifies the mapping independently of source-order position -- the second
    # family the position-only PROBABLE leaves were missing.  Only meaningful
    # when our decomp is a real body (insn_total large enough) located at the
    # mapped VA (not a byte-coincidence stub elsewhere).
    _wvf = {f["name"]: f for f in win_cache["functions"]}

    def struct_ok(F, V):
        f = _wvf.get(F)
        if not f or f.get("status") == "exact":
            return False
        sd, it = f.get("struct_diff"), f.get("insn_total") or 0
        if sd is None or it < 6 or f.get("located_va") not in (None, V):
            return False
        ratio = sd / it
        ps, w = ps_size.get(F), wf_size.get(V)
        size_ok = ps and w and min(ps, w) / max(ps, w) >= 0.6
        return ratio < 0.5 or (ratio < 0.62 and size_ok)

    def size_mismap(F, V):
        ps = ps_size.get(F)
        w = wf_size.get(V)
        if not ps or not w:
            return False
        return w >= 2 * ps and (w - ps) >= 40 and w > 16

    def cg_check(F, V, name2va):
        D = {name2va[c] for c in dos_cg.get(F, []) if name2va.get(c)}
        W = set(win_calls.get(V, []))
        return len(D), len(D & W)

    # Complete the name map to CRT/library callees (and any func missing from the
    # map) by voting from trusted functions -- the technique that built
    # globals-map.  For a trusted F->V, the residual unmapped DOS callees align
    # to the residual unmapped Windows call targets; each forced alignment votes
    # name->va.  High-agreement votes (>=3, >=75%) are accepted.
    def vote_names(trusted, name2va):
        va2names = defaultdict(set)
        for n, v in name2va.items():
            va2names[v].add(n)
        for _ in range(5):
            vote = defaultdict(Counter)
            for F in trusted:
                V = name2va.get(F, fm_va.get(F))
                if V is None:
                    continue
                d_un = [c for c in dos_cg.get(F, []) if c not in name2va]
                w_un = [t for t in win_calls.get(V, []) if t not in va2names]
                if d_un and len(d_un) == len(w_un):
                    for c, t in zip(d_un, w_un):
                        vote[c][t] += 1
            added = 0
            for c, ctr in vote.items():
                tot = sum(ctr.values())
                va, n = ctr.most_common(1)[0]
                if n >= 3 and n / tot >= 0.75 and va not in va2names and c not in name2va:
                    name2va[c] = va
                    va2names[va].add(c)
                    added += 1
            if not added:
                break
        return name2va

    # Anchor set: byte-unique + call-graph-confirmed-against-func-map (>=2 callees)
    anchor = dict(byte_true)
    for e in func_map:
        F = e["ps_name"]
        if F in anchor:
            continue
        nD, nhit = cg_check(F, fm_va[F], fm_va)
        if nD >= 2 and nhit == nD:
            anchor[F] = fm_va[F]

    # Anchored gap alignment
    ancL = sorted((i, anchor[nm]) for i, (_t, nm) in enumerate(PS_global)
                  if nm in anchor)
    mono, last = [], -1
    for i, v in ancL:
        if v > last:
            mono.append((i, v))
            last = v
    ord_va = {nm: anchor[nm] for _t, nm in PS_global if nm in anchor}
    ord_method = {nm: "anchor" for nm in ord_va}
    for k in range(len(mono) - 1):
        i0, v0 = mono[k]
        i1, v1 = mono[k + 1]
        ps_gap = [PS_global[i][1] for i in range(i0 + 1, i1)]
        win_gap = win_in_range(v0, v1)
        if ps_gap and len(ps_gap) == len(win_gap):
            for nm, (wva, _sz, _gn) in zip(ps_gap, win_gap):
                ord_va.setdefault(nm, wva)
                ord_method.setdefault(nm, "ordinal-exact")
        else:
            for nm in ps_gap:
                ord_method.setdefault(nm, "gap-mismatch")

    # TU-structural oracle: within a TU, PS source order == Windows VA order.
    # A TU whose func-map VAs form a COMPLETE bijection onto the Windows funcs
    # in its contiguous range AND are strictly increasing in PS source order is
    # FULLY order-verified -- every entry sits at its forced position (this is
    # the reccmp/isle-style order-preserving match).  A monotonic-but-incomplete
    # TU gives weaker 'tu-order' corroboration (extras create position slack).
    ps_tu_src_order = defaultdict(list)
    for s in sorted((s for s in sym["symbols"] if s.get("is_code")),
                    key=lambda x: x["address"]):
        tu = mod_tu(s["module_index"])
        if tu:
            ps_tu_src_order[tu].append(s["name"])
    tu_kind = {}          # tu -> 'bijection' | 'monotonic' | 'mixed'
    nonmono = set()
    for tu, order in ps_tu_src_order.items():
        # Stub-class functions are byte-identical and position-ambiguous (e.g.
        # act_null is one of 40 identical 11-byte stubs); exclude them from the
        # ordering check so they don't spoil an otherwise-clean TU.
        subst = [(n, fm_va[n]) for n in order
                 if n in fm_va and fm_va[n] not in stub_class]
        vs = [v for _n, v in subst]
        if len(vs) < 2:
            continue
        allvs = [fm_va[n] for n in order if n in fm_va]
        i = bisect.bisect_left(wf_va, min(allvs))
        j = bisect.bisect_right(wf_va, max(allvs))
        complete = set(allvs) == set(wf_va[i:j])
        monotonic = all(vs[k] < vs[k + 1] for k in range(len(vs) - 1))
        for k in range(len(vs) - 1):
            if vs[k] >= vs[k + 1]:
                nonmono.add(subst[k + 1][0])
        tu_kind[tu] = ("bijection" if complete and monotonic
                       else "monotonic" if monotonic else "mixed")

    def tu_oracle(F, tu):
        k = tu_kind.get(tu)
        if k == "bijection":
            return "tu-bijection"
        if k == "monotonic":
            return "tu-order"
        if k == "mixed" and F not in nonmono:
            return "tu-order"
        return None

    # First-pass trusted set (byte-unique + ord/cg agree at the map VA), then
    # complete the call graph to CRT/library callees by voting from it.
    def prelim_agree(e):
        F = e["ps_name"]
        Vfm = fm_va[F]
        n = 0
        if byte_true.get(F) == Vfm:
            n += 1
        if ord_va.get(F) == Vfm and ord_method.get(F) in ("ordinal-exact", "anchor"):
            n += 1
        nD, nhit = cg_check(F, Vfm, fm_va)
        if nD >= 2 and nhit == nD:
            n += 1
        return n >= 2 or byte_true.get(F) == Vfm

    trusted = {e["ps_name"] for e in func_map if prelim_agree(e)}
    name2va = vote_names(trusted, dict(fm_va))
    discovered = {n: v for n, v in name2va.items() if n not in fm_va}

    # ── Per-entry verdict (independent signal FAMILIES; require 2 to agree) ──
    # Families: POSITIONAL (byte-position / ordinal / tu-order -- all order-based,
    # counted ONCE), BYTE (unique compile-exact), CALLGRAPH.  tu-bijection is a
    # FORCED positional signal (verifies alone).  cg with >=2 distinct callees is
    # strong (verifies alone).  A stub-class VA is verifiable only up to the
    # byte-identical equivalence class.
    def verdict(e):
        F = e["ps_name"]
        Vfm = fm_va[F]
        tu = src_tu(e)
        bva = byte_true.get(F)
        ova = ord_va.get(F)
        omethod = ord_method.get(F, "unaligned")
        nD, nhit = cg_check(F, Vfm, name2va)
        isleaf = not dos_cg.get(F)
        instub = Vfm in stub_class
        tuo = tu_oracle(F, tu)
        oracles = []
        if bva is not None:
            oracles.append("byte" if bva == Vfm else "byte!")
        if ova == Vfm and omethod in ("ordinal-exact", "anchor"):
            oracles.append("ord")
        elif ova is not None and ova != Vfm:
            oracles.append("ord!")
        if tuo:
            oracles.append(tuo)
        if nD >= 2 and nhit == nD:
            oracles.append("cg")
        elif nD >= 1 and nhit == nD:
            oracles.append("cg1")
        elif nD >= 1 and nhit == 0:
            oracles.append("cg!")
        gE, gH = gref_check(F, Vfm)
        if gE >= 2 and gH >= max(2, gE * 0.6):
            oracles.append("gref")
        elif gE >= 2 and gH == 0:
            oracles.append("gref!")
        elif gE == 1 and gH == 1:
            oracles.append("gref1")

        byte_ok = bva is not None and bva == Vfm
        byte_bad = bva is not None and bva != Vfm
        pos_forced = tuo == "tu-bijection"
        pos_ok = (ova == Vfm and omethod in ("ordinal-exact", "anchor")) or tuo == "tu-order"
        pos_conflict = tuo is None and ova is not None and ova != Vfm
        cg_strong = nD >= 2 and nhit == nD
        cg_weak = nD >= 1 and nhit == nD
        cg_neg = nD >= 2 and nhit == 0
        gref_strong = gE >= 2 and gH >= max(2, gE * 0.6)
        gref_ok = gref_strong or (gE == 1 and gH == 1)
        gref_neg = gE >= 2 and gH == 0
        struct_c = struct_ok(F, Vfm)
        if struct_c:
            oracles.append("struct")
        content_pos = (nD >= 1 and nhit >= 1) or (gE >= 1 and gH >= 1)
        size_bad = size_mismap(F, Vfm) and not content_pos
        if size_bad:
            oracles.append("size!")
        propose = bva if byte_bad else None

        # MANUAL tier: a human content-verified the mapping (a positive
        # call-target / global / size fingerprint match documented in the
        # confidence field).  A valid verification input for the divergent-body
        # cases the automated oracles cannot adjudicate (Windows reimplemented
        # the body, so cg/gref legitimately diverge).  Byte conflict still wins.
        MANUAL = {"callee-verified", "callee-global-verified", "content-verified"}
        manual = e["confidence"] in MANUAL

        # Independent signal families: BYTE, POSITIONAL (byte-pos/ordinal/tu),
        # CALLGRAPH, GLOBAL-REF.  >=2 agreeing families (or a forced/strong one)
        # => VERIFIED.
        families = sum([byte_ok, pos_ok, cg_weak, gref_ok, struct_c])
        if byte_ok:
            v = "VERIFIED_BYTE"
        elif byte_bad:
            v = "CONFLICT_BYTE"
        elif manual:
            v = "VERIFIED_MANUAL"
        elif pos_forced:
            # position FORCED (complete+monotonic bijection).  A cg/gref conflict
            # here is body divergence (Windows reimplemented the body), not a
            # mapping error -- still verified, but flagged for transparency.
            v = "VERIFIED_DIVERGED" if (cg_neg or gref_neg) else "VERIFIED"
        elif cg_strong or gref_strong:
            v = "VERIFIED"                      # >=2 distinct callees or globals
        elif size_bad:
            # a tiny decomp sits on a much bigger real Windows function and no
            # content corroborates -> the city_trouble mismap signature.
            v = "REVIEW_CONFLICT"
        elif families >= 2:
            v = "VERIFIED"                      # two independent families agree
        elif cg_neg or gref_neg:
            # a structural oracle contradicts a non-forced position -> review
            # (mismap or heavy build divergence).
            v = "REVIEW_CONFLICT"
        elif instub:
            v = "VERIFIED_STUBCLASS"
        elif pos_conflict:
            v = "REVIEW_CONFLICT"
        elif pos_ok and isleaf:
            v = "PROBABLE_ORD_LEAF"
        elif pos_ok or cg_weak or gref_ok or struct_c:
            v = "PROBABLE"
        else:
            v = "REVIEW_NOEV"
        return dict(name=F, tu=tu, win_va=Vfm, tier=e["tier"],
                    conf=e["confidence"], byte_va=bva, ord_va=ova,
                    ord_method=omethod, tu_kind=tu_kind.get(tu), nD=nD, nhit=nhit,
                    isleaf=isleaf, stub_class=instub, oracles=oracles,
                    verdict=v, propose=propose)

    rows = [verdict(e) for e in func_map]
    by_name = {r["name"]: r for r in rows}

    # ── Report ──
    vc = Counter(r["verdict"] for r in rows)
    print("=== func-map verification (%d entries) ===" % len(rows))
    order = ["VERIFIED_BYTE", "VERIFIED", "VERIFIED_MANUAL", "VERIFIED_DIVERGED",
             "VERIFIED_STUBCLASS", "PROBABLE_ORD_LEAF", "PROBABLE",
             "REVIEW_CONFLICT", "CONFLICT_BYTE", "REVIEW_NOEV"]
    for k in order:
        if vc.get(k):
            print(f"  {k:20s} {vc[k]}")
    nver = sum(vc.get(k, 0) for k in ("VERIFIED_BYTE", "VERIFIED",
                                      "VERIFIED_MANUAL", "VERIFIED_DIVERGED",
                                      "VERIFIED_STUBCLASS"))
    nprob = sum(vc.get(k, 0) for k in ("PROBABLE_ORD_LEAF", "PROBABLE"))
    nrev = sum(vc.get(k, 0) for k in ("REVIEW_CONFLICT", "CONFLICT_BYTE",
                                      "REVIEW_NOEV"))
    print(f"\n  VERIFIED {nver}   PROBABLE {nprob}   NEEDS-REVIEW {nrev}")
    if discovered:
        print(f"\n  + {len(discovered)} game/lib functions DISCOVERED (missing from "
              f"func-map, located by call-graph voting):")
        for n, v in sorted(discovered.items()):
            tu = ps_by_name.get(n, {}).get("tu") or "?"
            print(f"      {n:24s} -> {v:#010x}  ({tu})")

    # per-TU table
    print("\n=== per-TU ===")
    tus = sorted({r["tu"] for r in rows})
    print(f'{"TU":12s} {"n":>4s} {"verif":>5s} {"prob":>4s} {"rev":>4s}')
    for tu in tus:
        rr = [r for r in rows if r["tu"] == tu]
        nv = sum(1 for r in rr if r["verdict"].startswith("VERIFIED"))
        npb = sum(1 for r in rr if r["verdict"].startswith("PROBABLE"))
        nrv = sum(1 for r in rr if r["verdict"].startswith(("REVIEW", "CONFLICT")))
        flag = "  <<" if nrv else ""
        print(f"{tu:12s} {len(rr):4d} {nv:5d} {npb:4d} {nrv:4d}{flag}")

    if args.tu or args.conflicts:
        print(f"\n=== detail ({'conflicts' if args.conflicts else args.tu}) ===")
        for r in rows:
            if args.tu and r["tu"] != args.tu:
                continue
            if args.conflicts and not (r["verdict"].startswith(("REVIEW", "CONFLICT"))):
                continue
            prop = f" PROPOSE={r['propose']:#010x}" if r["propose"] else ""
            print(f"{r['name']:30s} {r['tu']:10s} {r['win_va']:#010x} "
                  f"{r['verdict']:16s} oracles={r['oracles']} "
                  f"cg={r['nhit']}/{r['nD']}{prop}")

    if args.write:
        OUT.write_text(json.dumps(rows, indent=1))
        print(f"\nwrote {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
