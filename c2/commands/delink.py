"""``c2 delink`` — byte-preserving delink of a linked-in module set to OMF ``.obj``(s).

Recovers *relocatable* Watcom OMF object(s) from the fully-linked PS.EXE LE
image, for a set of modules (a translation unit, or a named library group
such as the RAD Smacker SDK).  The code and data bytes are copied verbatim;
the relocation table is reconstructed from:

  * the LE fixup table  — every absolute address reference (code->data,
    code->code jump tables), and
  * a control-flow scan — the PC-relative call/jmp edges that leave a
    contiguous function cluster (the LE table does not carry these, since
    they were resolved by displacement at link time).

Functions are grouped into *clusters* of originally-contiguous bodies; each
cluster is copied as one verbatim byte run, so every intra-cluster relative
branch (including short rel8) is preserved with no fixup.  Only cross-cluster
and external references become relocations — all of which are rel32/abs and
therefore relocatable.

Two output modes:

* **merged** (default): one ``.obj`` for the whole set — the safe, simple
  construction (all shared anonymous data is trivially single-copy).
* **``--split``**: one ``.obj`` PER ORIGINAL MODULE, mirroring the input
  structure of the 1995 link (separate library objects).  Every unnamed
  shared region is emitted ONCE in its owning module's object and referenced
  cross-module through exported anchors (the region's named symbol where one
  exists in the set; a synthetic ``__dlk_*`` label where the only anchor is
  a foreign/CRT name that clib3r also defines).  Split objects let the
  functional rebuild interleave modules in PS.EXE's original link order —
  the prerequisite for a layout-faithful relink.

The result links with WLINK 10.0a exactly like freshly-compiled objects.

Usage:
    c2 delink --group smacker -o lib/smacker.obj --verify
    c2 delink --group av --split -o .c2-cache/rebuild --verify
    c2 delink unsmack.ASM -o /tmp/unsmack.obj
    c2 delink --list                    # predefined groups
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Optional

import typer

# Predefined library groups (path substrings that identify the modules).
_GROUPS: dict[str, list[str]] = {
    # RAD Smacker SDK (NOT D:\C2\CODE\smacker.c, which is our own wrapper).
    "smacker": [r"SMACK\20", "unsmack.ASM"],
    # Miles AIL (Audio Interface Library) SDK.
    "ail": [r"NET\LIBS\AIL", "aila.asm", "ailssa.asm"],
    # RAD file I/O used by Smacker.
    "radio": ["rfile.ASM", "qread"],
    # Full audio/video stack: Smacker + AIL + RAD file I/O.  These modules
    # interoperate and share scratch data (see docs/delinking.md in git history -- the
    # simspeed overlay), so they must be delinked in ONE analysis set;
    # --split still emits one object per module with shared regions
    # single-copied and anchored.
    "av": [r"SMACK\20", "unsmack.ASM", r"NET\LIBS\AIL",
           "aila.asm", "ailssa.asm", "rfile.ASM", "qread"],
}

# File-scope statics inside delinked modules that GAME-side code references
# (memory shared across the module boundary in the original link).  These
# get a PUBDEF so the game objects resolve against the delinked storage.
_DATA_EXPORT_STATICS = {"_sndinit"}

# Reconstructed vendor-library assignment for --libs (module-name substring
# -> archive), mirroring the 1995 link inputs: Miles AIL's library and the
# RAD Smacker SDK library (which shipped the sound glue and file I/O).
_LIB_ASSIGNMENT: dict[str, list[str]] = {
    "ail.lib": [r"NET\LIBS\AIL", "aila.asm", "ailssa.asm"],
    "smack.lib": [r"SMACK\20", "unsmack.ASM", "rfile.ASM", "qread"],
}


def _lib_of(mod_name: str) -> Optional[str]:
    up = (mod_name or "").upper()
    for lib, subs in _LIB_ASSIGNMENT.items():
        if any(s.upper() in up for s in subs):
            return lib
    return None


def _norm_sym(name: str) -> str:
    """Normalise a symbol for CRT matching (strip leading underscores/case)."""
    return (name or "").lstrip("_").upper()


_CRT_SYMS_CACHE: set[str] | None = None


def _load_crt_symbols() -> set[str]:
    """Load the clib3r CRT symbol set (for extern-vs-inline data decisions)."""
    global _CRT_SYMS_CACHE
    if _CRT_SYMS_CACHE is not None:
        return _CRT_SYMS_CACHE
    syms: set[str] = set()
    p = Path("lib/clib3r-symbols.txt")
    if p.exists():
        for ln in p.read_text(errors="ignore").splitlines():
            tok = ln.strip().split()
            if tok:
                syms.add(_norm_sym(tok[0]))
    _CRT_SYMS_CACHE = syms
    return syms


def _load_context(symbols_json: Path, exe_path: Path):
    from c2.parsers.exe import parse_exe
    from c2.commands.fixups import parse_le_fixups

    d = json.loads(symbols_json.read_text())
    _mz, _bw, le = parse_exe(exe_path)
    exe = exe_path.read_bytes()
    code_off = le.object_file_offset(le.objects[0])
    code_vsize = d["memory_map"]["objects"][0]["virtual_size"]
    data_vsize = d["memory_map"]["objects"][1]["virtual_size"]
    data_fsize = d["memory_map"]["objects"][1]["file_size"]
    data_file_off = int(d["memory_map"]["objects"][1]["file_offset_int"])
    code_bytes = exe[code_off:code_off + code_vsize]
    data_bytes = exe[data_file_off:data_file_off + data_fsize]
    code_fm, data_fm = parse_le_fixups(
        exe_path, le.le_offset, le.page_size, le.num_pages,
        le.objects[0].num_pages, le.objects[1].num_pages,
    )
    return d, code_bytes, data_bytes, code_vsize, data_vsize, data_fsize, code_fm, data_fm


def _resolve_modules(d: dict, selectors: list[str], group: Optional[str]) -> set[int]:
    mods = d["modules"]
    want: set[int] = set()
    subs: list[str] = []
    if group:
        if group not in _GROUPS:
            raise typer.BadParameter(
                f"unknown group {group!r}; known: {', '.join(_GROUPS)}")
        subs += _GROUPS[group]
    subs += list(selectors)
    for i, m in enumerate(mods):
        name = (m.get("name") or "")
        up = name.upper()
        for s in subs:
            if s.upper() in up:
                want.add(i)
    return want


def _mod_base(mods: list[dict], idx: int) -> str:
    """Module basename without extension (lowercased): the .obj stem."""
    name = (mods[idx].get("name") or f"mod{idx}").rsplit("\\", 1)[-1]
    return name.rsplit(".", 1)[0].lower()


class _Report(dict):
    pass


# Per-module code SEGMENT names for --split.  The RAD assembly modules
# live in their OWN code segments in PS.EXE (placed AFTER the _TEXT
# stream — qread @0x7879a, unsmack @0x78c60, rfile @0x7c040, right at
# the code object's tail, far from their library pull positions), so
# their delinked objects must not flatten into _TEXT if a library-
# resolution link is to reproduce PS's layout.  The original segment
# names are unknowable from the LE (segments are merged); these stand-ins
# reproduce the placement class.
_SEGMENT_NAME_OVERRIDES: dict[str, str] = {
    "qread": "QREAD",
    "unsmack": "UNSMACK",
    "rfile": "RFILE",
}

# PS's segment order for those modules is (qread, unsmack, rfile) — NOT
# their library pull order (unsmack, rfile, qread).  wlink orders
# same-class segments by first registration, so the original RAD objects
# must each have DECLARED all three segments in one canonical order (a
# shared assembler include), letting the first-pulled module register
# them all.  Each delinked RAD object therefore declares the full canon
# (own segment filled, the others empty SEGDEFs).
_SEGMENT_CANON: list[str] = ["QREAD", "UNSMACK", "RFILE"]


class _Part:
    """One output object (a module in --split mode; the whole set merged)."""

    def __init__(self, name: str):
        from c2.omf import OmfObject
        self.name = name
        self.o = OmfObject(name)
        own = _SEGMENT_NAME_OVERRIDES.get(name)
        if own is None:
            self.text = self.o.segment("_TEXT", "CODE")
        else:
            self.text = None
            for seg_name in _SEGMENT_CANON:
                seg = self.o.segment(seg_name, "CODE")
                if seg_name == own:
                    self.text = seg
        self.const_seg = None
        self.data_seg = None
        self.bss_seg = None
        self.clusters: list[dict] = []       # this part's clusters
        self.dranges: list[tuple[int, int, str, int]] = []  # (st,en,kind,base)
        self.bss_len = 0
        self.report = _Report(
            module=name, clusters=0, functions=0, publics=0, data_publics=0,
            text_bytes=0, data_bytes=0, bss_bytes=0,
            abs_data=0, abs_code=0, abs_ext=0, rel_internal=0, rel_ext=0,
            externs=[], data_regions=0, code_tables=0, synthetics=0,
        )

    def ensure_data_segs(self, need_data: bool, need_bss: bool) -> None:
        if need_data and self.data_seg is None:
            self.data_seg = self.o.segment("_DATA", "DATA")
        if need_bss and self.bss_seg is None:
            self.bss_seg = self.o.segment("_BSS", "BSS", is_bss=True)

    def ensure_const_seg(self) -> None:
        if self.const_seg is None:
            self.const_seg = self.o.segment("CONST", "DATA")
            self.const_seg.align = 4

    def finish_groups(self) -> None:
        # DGROUP order mirrors Watcom's: CONST, _DATA, _BSS.
        dgroup = []
        if self.const_seg is not None:
            dgroup.append(self.const_seg.seg_index)
        if self.data_seg is not None:
            dgroup.append(self.data_seg.seg_index)
        if self.bss_seg is not None:
            dgroup.append(self.bss_seg.seg_index)
        if dgroup:
            self.o.group("DGROUP", dgroup)
        self.o.group("FLAT", [])

    def seg_for(self, kind: str):
        return {"const": self.const_seg, "data": self.data_seg,
                "bss": self.bss_seg}[kind]


def _delink(d, code_bytes, data_bytes, code_vsize, data_vsize, data_fsize,
            code_fm, data_fm, module_indices: set[int], module_name: str,
            split: bool = False):
    """Core delink.

    Returns ``(parts, total_report)`` where *parts* is a list of ``_Part``
    (exactly one in merged mode).  Byte-preserving by construction: code and
    data are copied verbatim per contiguous region; only cross-region and
    external references become relocations.
    """
    import bisect
    from c2.omf import Fixup

    mods = d["modules"]
    allc = sorted([s for s in d["symbols"] if s.get("is_code")],
                  key=lambda s: s["offset"])
    alld = sorted([s for s in d["symbols"] if s.get("is_data")],
                  key=lambda s: s["offset"])
    cstarts = [s["offset"] for s in allc]
    dstarts = [s["offset"] for s in alld]

    def cown(o):
        i = bisect.bisect_right(cstarts, o) - 1
        return allc[i] if 0 <= i < len(allc) else None

    def cend(s):
        i = bisect.bisect_right(cstarts, s["offset"])
        while i < len(allc) and allc[i]["offset"] == s["offset"]:
            i += 1
        return allc[i]["offset"] if i < len(allc) else code_vsize

    def dend(s):
        i = bisect.bisect_right(dstarts, s["offset"])
        return alld[i]["offset"] if i < len(alld) else data_vsize

    def part_of_module(mi: int) -> str:
        return _mod_base(mods, mi) if split else module_name

    # ── code: functions -> contiguous clusters ─────────────────────────
    fns_all = sorted([s for s in allc if s["module_index"] in module_indices],
                     key=lambda s: s["offset"])
    if not fns_all:
        raise typer.BadParameter("no code symbols in the selected module(s)")
    # Dedupe ALIASES: -d1 can carry several names for ONE body (e.g.
    # ailsfile.c's _AIL_WAV_EOS == _AIL_VOC_terminate @0x6f83e).  Without
    # this, each alias became its own function span and the shared bytes
    # were emitted TWICE (a second cluster over the same range — caught by
    # the rebuild comparator as a 94-byte layout drift, 2026-07-10).  One
    # body is kept; every alias still gets a PUBDEF below.
    fns: list[dict] = []
    aliases: dict[int, list[dict]] = {}
    for s in fns_all:
        if fns and fns[-1]["offset"] == s["offset"]:
            aliases[s["offset"]].append(s)
        else:
            fns.append(s)
            aliases[s["offset"]] = [s]

    clusters: list[dict] = []
    for s in fns:
        st, en = s["offset"], cend(s)
        pk = part_of_module(s["module_index"])
        if clusters and clusters[-1]["end"] == st and clusters[-1]["part"] == pk:
            clusters[-1]["end"] = en
            clusters[-1]["fns"].append(s)
        else:
            clusters.append({"start": st, "end": en, "fns": [s], "part": pk})

    # ── data-in-code jump tables (unnamed in-module tables that trail a
    #    CRT code symbol) ────────────────────────────────────────────────
    # ailssa.asm's DIG/mixer dispatch tables (`_DC_*`/`_M_*` pointers) live
    # in the code image but carry no `-d1` symbol, so the symbol map
    # attributes them to the *preceding* symbol (e.g. a 5-byte CRT `remove`
    # jmp thunk).  In-module code reaches them by absolute address
    # (`call cs:[eax*4 + TABLE]`).  Pull [target, owner_end) in as a
    # verbatim text region owned by the REFERENCING module; the normal
    # fixup passes then relocate the reference and the table's own entries.
    def _fn_cluster_of(off):
        for c in clusters:
            if c["fns"] and c["start"] <= off < c["end"]:
                return c
        return None

    tables: dict[int, tuple[int, str]] = {}     # start -> (end, part)

    def _in_table(off):
        return any(rs <= off < re_ for rs, (re_, _p) in tables.items())

    def _add_table(st, en, part):
        for rs in list(tables):
            re_, pp = tables[rs]
            if not (en < rs or st > re_):       # overlap / adjacent -> merge
                st, en = min(st, rs), max(en, re_)
                part = pp                        # first owner wins
                del tables[rs]
        tables[st] = (en, part)

    _tbl_changed = True
    while _tbl_changed:
        _tbl_changed = False
        for site, (tobj, toff) in code_fm.items():
            if tobj != 1:
                continue
            site_c = _fn_cluster_of(site)
            site_part = None
            if site_c is not None:
                site_part = site_c["part"]
            elif _in_table(site):
                for rs, (re_, pp) in tables.items():
                    if rs <= site < re_:
                        site_part = pp
                        break
            if site_part is None:
                continue
            if _fn_cluster_of(toff) or _in_table(toff) or toff >= code_vsize:
                continue
            owner = cown(toff)
            if owner is None or owner["module_index"] in module_indices:
                continue
            if toff == owner["offset"]:
                continue                        # exact foreign symbol -> extern
            _add_table(toff, cend(owner), site_part)
            _tbl_changed = True

    n_tables = len(tables)
    for st, (en, pk) in tables.items():
        clusters.append({"start": st, "end": en, "fns": [], "part": pk})
    clusters.sort(key=lambda c: c["start"])

    # ── data regions -> _DATA (file-backed) / _BSS (uninitialised) ─────
    # PS.EXE data ownership is only partially recoverable: function-local
    # statics carry no `-d1` symbol (they show up as unnamed gaps after a
    # named static — e.g. qread's read buffer trails `simspeed`).  We start
    # from the selected modules' named statics and *pull in* every other
    # in-image data region the code references, EXCEPT genuine CRT/library
    # data (e.g. `_nullarea`), which stays an extern resolved by clib3r.lib.
    crt_syms = _load_crt_symbols()

    def is_crt_data(sym) -> bool:
        modname = (mods[sym["module_index"]].get("name") or "").upper()
        if "D:\\C2\\CODE" in modname or sym["module_index"] in module_indices:
            return False
        return _norm_sym(sym["raw_name"]) in crt_syms or "CSTRT" in modname \
            or "CLIB" in modname or modname.endswith(".LIB")

    def is_crt_code(sym) -> bool:
        if sym is None or sym["module_index"] in module_indices:
            return False
        modname = (mods[sym["module_index"]].get("name") or "").upper()
        return _norm_sym(sym["raw_name"]) in crt_syms or "CSTRT" in modname \
            or "CLIB" in modname or modname.endswith(".LIB")

    def owned_data_end(sym) -> int:
        """Trim a named AV span when the following tail belongs to CRT.

        Debug symbols do not mark unnamed object boundaries.  In PS the
        512-byte smackinp table beginning at `_simspeed` is followed by the
        CRT stk386 object's unnamed stack-overflow record, then by `___iob`.
        The naive named-symbol span therefore swallowed that CRT record into
        smackinp and the rebuild emitted it twice.  A CRT code fixup into the
        tail is the surviving ownership witness; cut at its first target when
        the next named datum is also CRT-owned.
        """
        st, en = sym["offset"], dend(sym)
        ni = bisect.bisect_left(dstarts, en)
        if ni >= len(alld) or not is_crt_data(alld[ni]):
            return en
        cuts = [toff for site, (tobj, toff) in code_fm.items()
                if tobj == 2 and st < toff < en and is_crt_code(cown(site))]
        return min(cuts) if cuts else en

    def data_interval(off):
        """Enclosing named-symbol interval [sym.offset, next.offset) for off."""
        i = bisect.bisect_right(dstarts, off) - 1
        if not (0 <= i < len(alld)):
            return None
        s = alld[i]
        return s, s["offset"], dend(s)

    # region list: start -> (end, part, anchored) — disjoint intervals.
    regions: dict[int, tuple[int, str, bool]] = {}

    def in_regions(off):
        return any(rs <= off < re_ for rs, (re_, _p, _a) in regions.items())

    def add_region(st, en, part, anchored):
        # Intervals are [named-sym, next-named-sym) — disjoint by
        # construction.  Merge only same-part touching intervals (keeps the
        # merged mode identical to the historical behaviour; in split mode
        # adjacent regions from DIFFERENT modules stay separate objects).
        for rs in list(regions):
            re_, pp, aa = regions[rs]
            if en < rs or st > re_:
                continue
            if pp == part:
                st, en = min(st, rs), max(en, re_)
                anchored = anchored or aa
                del regions[rs]
        regions[st] = (en, part, anchored)

    for s in sorted([s for s in alld if s["module_index"] in module_indices],
                    key=lambda s: s["offset"]):
        add_region(s["offset"], owned_data_end(s),
                   part_of_module(s["module_index"]),
                   True)
    n_named = len(regions)

    def _code_part_at(off):
        for c in clusters:
            if c["start"] <= off < c["end"]:
                return c["part"]
        return None

    # Data offsets referenced by AV code/data inside a foreign named span.
    # `_nullarea` covers the shared CONST pool: game and CRT literals are
    # re-emitted by their rebuilt objects, while AV literals must accompany
    # the delinked modules.  Recover only convex AV-reference runs, retaining
    # tiny alignment/computed-offset gaps and dropping large foreign gaps.
    _av_data_spans = sorted(
        (s["offset"], dend(s)) for s in alld
        if s["module_index"] in module_indices and s["offset"] < data_fsize)

    def _site_is_av_data(site: int) -> bool:
        i = bisect.bisect_right([a for a, _ in _av_data_spans], site) - 1
        return i >= 0 and _av_data_spans[i][0] <= site < _av_data_spans[i][1]

    av_ref_offs: dict[str, set[int]] = {}
    for site, (tobj, toff) in code_fm.items():
        part = _code_part_at(site)
        if tobj == 2 and part is not None:
            av_ref_offs.setdefault(part, set()).add(toff)
    for site, (tobj, toff) in data_fm.items():
        if tobj != 2 or not _site_is_av_data(site):
            continue
        iv = data_interval(site)
        if iv is None or iv[0]["module_index"] not in module_indices:
            continue
        part = part_of_module(iv[0]["module_index"])
        av_ref_offs.setdefault(part, set()).add(toff)
    av_ref_offs = {part: set(sorted(offs))
                   for part, offs in av_ref_offs.items()}

    def _ref_clusters(st: int, en: int, part: str) -> list[tuple[int, int]]:
        """One AV module's referenced literal runs inside foreign [st,en).

        Each direct target contributes through its next NUL.  Only overlapping
        or nearby targets from the SAME original object merge; WLINK then
        recreates padding between the separate objects' CONST contributions.
        """
        refs = sorted(off for off in av_ref_offs.get(part, ())
                      if st <= off < en)
        if not refs:
            return []
        runs: list[list[int]] = []
        for ref in refs:
            e = data_bytes.find(b"\x00", ref, en)
            rend = (e + 1) if 0 <= e < en else en
            if runs and ref - runs[-1][1] <= 16:
                runs[-1][1] = max(runs[-1][1], rend)
            else:
                runs.append([ref, rend])
        return [(a, b) for a, b in runs]

    # fixpoint pull-in of referenced foreign (non-CRT) data
    externs_data: set[int] = set()   # data offsets that stay extern (CRT)
    n_inlined = 0
    changed = True
    while changed:
        changed = False
        refs = [(toff, _code_part_at(site))
                for site, (tobj, toff) in code_fm.items()
                if tobj == 2 and _code_part_at(site) is not None]
        for site, (tobj, toff) in data_fm.items():
            if tobj != 2:
                continue
            for rs, (re_, pp, _a) in regions.items():
                if rs <= site < re_:
                    refs.append((toff, pp))
                    break
        for toff, ref_part in refs:
            if in_regions(toff) or toff in externs_data:
                continue
            iv = data_interval(toff)
            if iv is None:
                continue
            sym, st, en = iv
            if is_crt_data(sym) and toff == st:
                # exact CRT symbol (offset 0) -> genuine clib3r extern
                externs_data.add(toff)
                continue
            if sym["module_index"] in module_indices:
                # Genuine in-module data (a delinked module's own -d1 symbol):
                # inline its whole [sym, next) span, verbatim.
                add_region(st, en, part_of_module(sym["module_index"]), True)
                n_inlined += 1
                changed = True
            else:
                # A *mid-symbol* reference into a FOREIGN/CRT symbol whose
                # -d1 span is a large UNNAMED pool SHARED with the game and
                # the CRT.  The canonical case is `_nullarea`, whose span
                # [0, __IsTable) covers the ENTIRE CONST string pool: game
                # strings (provided by the game TUs), CRT strings (clib3r),
                # and the AV SDK's own strings (AIL driver names + the
                # AIL_*() debug format block), all interleaved with no -d1
                # symbols of their own.  Inlining the whole span duplicates
                # the game/CRT bytes in the rebuild (they arrive twice: once
                # from the game/clib3r objects, once from ours) -- the
                # __dlk_D000000 duplication.  Instead inline only the CLUSTERS
                # this module set actually references: contiguous runs of AV
                # references bounded by their convex hull, split wherever a
                # large unreferenced gap (a foreign game/CRT string block)
                # separates them.  Intra-run unreferenced strings are kept
                # (an AV string reached by computed offset stays present);
                # only the big foreign blocks are dropped.  The verbatim
                # check still passes (every emitted byte is from PS.EXE); the
                # rebuild no longer double-emits the shared pool.
                if st == 0:
                    # `_nullarea`: the shared CONST/string pool.  Retain
                    # only this AV object's directly referenced runs.
                    candidates = _ref_clusters(st, en, ref_part)
                    is_data = False
                else:
                    # A foreign named symbol can precede an unnamed binary
                    # block owned by the referencing AV module.  Its direct
                    # fixups name interior offsets; the original object ran
                    # from the first such target through the interval end.
                    # AILA's [0xc210,0xcdc0) and AILSSA's [0xcfa0,0xcfc0)
                    # are the two PS instances (2,992 + 32 bytes).
                    own_refs = sorted(off for off in av_ref_offs.get(ref_part, ())
                                      if st < off < en)
                    candidates = [(own_refs[0], en)] if own_refs else []
                    is_data = True
                for cst, cen in candidates:
                    if not in_regions(cst):
                        add_region(cst, cen, ref_part, is_data)
                        n_inlined += 1
                        changed = True

    # ── build parts + lay out text/data ────────────────────────────────
    part_names: list[str] = []
    if split:
        for mi in sorted(module_indices):
            pn = part_of_module(mi)
            if pn not in part_names:
                part_names.append(pn)
        for _st, (_en, pp, _a) in sorted(regions.items()):
            if pp not in part_names:
                part_names.append(pp)
    else:
        part_names = [module_name]
    parts: dict[str, _Part] = {pn: _Part(pn) for pn in part_names}

    for c in clusters:
        p = parts[c["part"]]
        c["text_off"] = len(p.text.data)
        p.text.data += code_bytes[c["start"]:c["end"]]
        p.clusters.append(c)
        p.report["clusters"] += 1
        p.report["functions"] += len(c["fns"])
        if not c["fns"]:
            p.report["code_tables"] += 1

    # Infer each part's _TEXT segment ALIGNMENT from PS's pad evidence:
    # the smallest OMF-representable alignment (2/4/16) whose required
    # padding at the module's start exactly matches the zero bytes PS
    # carries before it (e.g. smackinp.cpp: 15 zero-pad bytes to a
    # 16-boundary => para-aligned _TEXT, exactly what the original
    # object declared).  No pad evidence => byte alignment.
    if split:
        for p in parts.values():
            fn_clusters = [c for c in p.clusters if c["fns"]]
            if not fn_clusters:
                continue
            st = min(c["start"] for c in fn_clusters)
            npad = 0
            while npad < 15 and st - npad - 1 >= 0 \
                    and code_bytes[st - npad - 1] == 0:
                npad += 1
            if npad == 0:
                continue
            for a in (2, 4, 16):
                if st % a == 0 and (a - (st - npad) % a) % a == npad:
                    p.text.align = a
                    break

    def cluster_of(off):
        for c in clusters:
            if c["start"] <= off < c["end"]:
                return c
        return None

    def map_text(off):
        """PS code offset -> (part, part-local text offset)."""
        c = cluster_of(off)
        if c is None:
            return None
        return c["part"], c["text_off"] + (off - c["start"])

    for st in sorted(regions):
        en, pk, anchored = regions[st]
        p = parts[pk]
        p.report["data_regions"] += 1
        if st < data_fsize:                        # file-backed -> CONST/_DATA
            img = data_bytes[st:min(en, data_fsize)]
            if en > data_fsize:
                img = img + b"\x00" * (en - data_fsize)
            # A FOREIGN-inlined (anchored=False) region is carved from the
            # CRT `_nullarea` span: PS's shared CONST pool containing game,
            # CRT, and AV literals.  It is still CONST even when the AV run
            # includes a small binary literal/table among its strings (the
            # AIL debug pool has `20 00 fa 00` between format strings).  The
            # old printable-only gate misclassified the entire 0x10f9 run as
            # _DATA and inserted 5,428 bytes between vgawintab and disk_err.
            if not anchored:
                p.ensure_const_seg()
                p.dranges.append((st, en, "const", len(p.const_seg.data)))
                p.const_seg.data += img
            else:
                p.ensure_data_segs(True, False)
                p.dranges.append((st, en, "data", len(p.data_seg.data)))
                p.data_seg.data += img
        else:                                      # _BSS
            p.ensure_data_segs(False, True)
            p.dranges.append((st, en, "bss", p.bss_len))
            p.bss_len += en - st
    for p in parts.values():
        if p.bss_seg is not None:
            p.bss_seg.bss_len = p.bss_len
        p.finish_groups()

    def map_data(off):
        """PS data offset -> (part, kind, part-local offset)."""
        for pn, p in parts.items():
            for st, en, kind, base in p.dranges:
                if st <= off < en:
                    return pn, kind, base + (off - st)
        return None

    # ── export registry (cross-part + genuinely public names) ──────────
    # A name is exported at most once across all parts; collisions between
    # same-named STATICS of different modules (e.g. ail.c/_locked vs
    # aildebug.c/_locked) get a deterministic per-module suffix; anonymous
    # targets get a synthetic ``__dlk_[CD]<offset>`` label.
    exported: dict[str, tuple[str, int]] = {}     # name -> (part, ps_off)
    n_synth = 0

    def _export(name: str, pn: str, ps_off: int, seg, local_off: int) -> str:
        nonlocal n_synth
        cand = name
        if cand in exported:
            if exported[cand] == (pn, ps_off):
                return cand
            cand = f"{name}__{pn}"
        if cand in exported and exported[cand] != (pn, ps_off):
            cand = f"__dlk_X{ps_off:06X}"
            n_synth += 1
        if cand not in exported:
            exported[cand] = (pn, ps_off)
            parts[pn].o.public(seg, cand, local_off)
        return cand

    def export_code(ps_off: int) -> tuple[str, int]:
        """Ensure a linker-visible name for PS code offset; -> (name, base)."""
        nonlocal n_synth
        # exact function (any alias)?
        for a in aliases.get(ps_off, []):
            pn, tx = map_text(ps_off)
            return _export(a["raw_name"], pn, ps_off,
                           parts[pn].text, tx), ps_off
        c = cluster_of(ps_off)
        pn = c["part"]
        if c["fns"]:
            # mid-function target: anchor on the containing function
            fn = max((f for f in c["fns"] if f["offset"] <= ps_off),
                     key=lambda f: f["offset"])
            _pn, tx = map_text(fn["offset"])
            return _export(fn["raw_name"], pn, fn["offset"],
                           parts[pn].text, tx), fn["offset"]
        # data-in-code table: synthetic label at the table start
        name = f"__dlk_C{c['start']:06X}"
        _pn, tx = map_text(c["start"])
        n_synth += 1
        return _export(name, pn, c["start"], parts[pn].text, tx), c["start"]

    def export_data(ps_off: int) -> tuple[str, int]:
        """Ensure a linker-visible name for PS data offset; -> (name, base)."""
        nonlocal n_synth
        pn, kind, _doff = map_data(ps_off)
        p = parts[pn]
        iv = data_interval(ps_off)
        if iv is not None:
            sym, st, _en = iv
            loc = map_data(st)
            if (sym["module_index"] in module_indices and loc is not None
                    and loc[0] == pn):
                _pn2, kind2, d2 = loc
                return _export(sym["raw_name"], pn, st,
                               p.seg_for(kind2), d2), st
        # No safe in-set anchor (region trails a foreign/CRT name that
        # clib3r also defines): synthetic label at the region start.
        for st, en, kind2, base in p.dranges:
            if st <= ps_off < en:
                name = f"__dlk_D{st:06X}"
                n_synth += 1
                return _export(name, pn, st, p.seg_for(kind2), base), st
        raise RuntimeError(f"export_data: 0x{ps_off:x} not in any region")

    # ── standard publics ────────────────────────────────────────────────
    for c in clusters:
        for s in c["fns"]:
            for a in aliases.get(s["offset"], [s]):
                if not a.get("is_static"):
                    pn, tx = map_text(a["offset"])
                    _export(a["raw_name"], pn, a["offset"],
                            parts[pn].text, tx)
                    parts[pn].report["publics"] += 1

    # data publics: every non-static data symbol of the selected modules,
    # plus the allowlisted file-scope STATICS that game-side modules reach
    # into (`_sndinit`: the four dia_*.asm renderers EXTRN it).
    for s in sorted([s for s in alld if s["module_index"] in module_indices],
                    key=lambda s: s["offset"]):
        if s.get("is_static") and s["raw_name"] not in _DATA_EXPORT_STATICS:
            continue
        loc = map_data(s["offset"])
        if loc is None:
            continue
        pn, kind, doff = loc
        got = _export(s["raw_name"], pn, s["offset"],
                      parts[pn].seg_for(kind), doff)
        if got == s["raw_name"]:
            parts[pn].report["data_publics"] += 1

    # ── fixup emission ──────────────────────────────────────────────────
    def _emit_abs(p: _Part, seg, local_off: int, tobj: int, toff: int) -> None:
        """Absolute 4-byte reference at (seg, local_off) -> target."""
        if tobj == 2:                              # -> data
            loc = map_data(toff)
            if loc is not None:
                tpn, kind, doff = loc
                if tpn == p.name:
                    seg.data[local_off:local_off + 4] = doff.to_bytes(4, "little")
                    seg.fixups.append(Fixup(local_off, self_rel=False,
                                            target_seg=p.seg_for(kind).seg_index))
                    p.report["abs_data"] += 1
                else:
                    name, base = export_data(toff)
                    ext = p.o.extern(name)
                    seg.data[local_off:local_off + 4] = \
                        (toff - base).to_bytes(4, "little", signed=False)
                    seg.fixups.append(Fixup(local_off, self_rel=False,
                                            target_ext=ext))
                    p.report["abs_ext"] += 1
                    p.report["externs"].append(name)
            else:                                  # external data (CRT)
                sym = cown_data_owner(alld, dstarts, toff)
                if sym is None:
                    raise RuntimeError(f"unresolved data target 0x{toff:x}")
                disp = toff - sym["offset"]
                ext = p.o.extern(sym["raw_name"])
                seg.data[local_off:local_off + 4] = \
                    disp.to_bytes(4, "little", signed=False)
                seg.fixups.append(Fixup(local_off, self_rel=False,
                                        target_ext=ext))
                p.report["abs_ext"] += 1
                p.report["externs"].append(sym["raw_name"])
        else:                                      # -> code
            loc = map_text(toff)
            if loc is not None:
                tpn, tx = loc
                if tpn == p.name:
                    seg.data[local_off:local_off + 4] = tx.to_bytes(4, "little")
                    seg.fixups.append(Fixup(local_off, self_rel=False,
                                            target_seg=p.text.seg_index))
                    p.report["abs_code"] += 1
                else:
                    name, base = export_code(toff)
                    ext = p.o.extern(name)
                    seg.data[local_off:local_off + 4] = \
                        (toff - base).to_bytes(4, "little", signed=False)
                    seg.fixups.append(Fixup(local_off, self_rel=False,
                                            target_ext=ext))
                    p.report["abs_ext"] += 1
                    p.report["externs"].append(name)
            else:                                  # external code pointer
                sym = cown(toff)
                disp = toff - sym["offset"]
                ext = p.o.extern(sym["raw_name"])
                seg.data[local_off:local_off + 4] = \
                    disp.to_bytes(4, "little", signed=False)
                seg.fixups.append(Fixup(local_off, self_rel=False,
                                        target_ext=ext))
                p.report["abs_ext"] += 1
                p.report["externs"].append(sym["raw_name"])

    # absolute fixups (LE table) sited inside our clusters
    for site, (tobj, toff) in code_fm.items():
        loc = map_text(site)
        if loc is None:
            continue
        pn, stext = loc
        _emit_abs(parts[pn], parts[pn].text, stext, tobj, toff)

    # relative control-flow edges leaving a cluster
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True
    for c in clusters:
        if not c["fns"]:                        # data-in-code table: not code
            continue
        p = parts[c["part"]]
        buf = code_bytes[c["start"]:c["end"]]
        for ins in md.disasm(buf, c["start"]):
            m = ins.mnemonic
            if not (m in ("call", "jmp") or m.startswith("j") or m.startswith("loop")):
                continue
            if not (len(ins.operands) == 1 and
                    ins.operands[0].type == capstone.x86.X86_OP_IMM):
                continue
            toff = ins.operands[0].imm
            if c["start"] <= toff < c["end"]:      # intra-cluster: verbatim
                continue
            if ins.size < 5:                       # cross-cluster short branch
                raise RuntimeError(
                    f"unrelocatable cross-cluster rel8 in {m} @0x{ins.address:x}")
            opnd = ins.address + ins.size - 4      # rel32 operand position
            _pn, stext = map_text(opnd)
            loc = map_text(toff)
            if loc is not None and loc[0] == c["part"]:   # same-part internal
                p.text.data[stext:stext + 4] = loc[1].to_bytes(4, "little")
                p.text.fixups.append(Fixup(stext, self_rel=True,
                                           target_seg=p.text.seg_index))
                p.report["rel_internal"] += 1
            elif loc is not None:                          # cross-part call
                name, base = export_code(toff)
                ext = p.o.extern(name)
                p.text.data[stext:stext + 4] = \
                    (toff - base).to_bytes(4, "little", signed=False)
                p.text.fixups.append(Fixup(stext, self_rel=True,
                                           target_ext=ext))
                p.report["rel_ext"] += 1
                p.report["externs"].append(name)
            else:                                          # external call/jmp
                sym = cown(toff)
                if sym is None:
                    raise RuntimeError(f"unresolved rel target 0x{toff:x}")
                disp = toff - sym["offset"]
                ext = p.o.extern(sym["raw_name"])
                p.text.data[stext:stext + 4] = \
                    disp.to_bytes(4, "little", signed=False)
                p.text.fixups.append(Fixup(stext, self_rel=True,
                                           target_ext=ext))
                p.report["rel_ext"] += 1
                p.report["externs"].append(sym["raw_name"])

    # absolute fixups sited inside our DATA statics (pointers)
    for site, (tobj, toff) in data_fm.items():
        loc = map_data(site)
        if loc is None:
            continue
        pn, skind, soff = loc
        if skind == "bss":
            raise RuntimeError(f"pointer in BSS static @0x{site:x} (unexpected)")
        p = parts[pn]
        _emit_abs(p, p.seg_for(skind), soff, tobj, toff)
        p.report["data_ptr"] = p.report.get("data_ptr", 0) + 1

    # ── totals ──────────────────────────────────────────────────────────
    total = _Report(
        module=module_name, modules=sorted(module_indices),
        parts=len(parts), functions=len(fns),
        clusters=len(clusters), code_tables=n_tables,
        data_named=n_named, data_inlined=n_inlined, synthetics=n_synth,
    )
    for p in parts.values():
        p.report["text_bytes"] = len(p.text.data)
        p.report["data_bytes"] = (
            (len(p.const_seg.data) if p.const_seg is not None else 0)
            + (len(p.data_seg.data) if p.data_seg is not None else 0))
        p.report["bss_bytes"] = p.bss_len
        p.report["externs"] = sorted(set(p.report["externs"]))
        p.report["data_ptr"] = p.report.get("data_ptr", 0)
        p.report["_clusters"] = p.clusters
        p.report["_dranges"] = p.dranges
        for k in ("text_bytes", "data_bytes", "bss_bytes", "publics",
                  "data_publics", "abs_data", "abs_code", "abs_ext",
                  "rel_internal", "rel_ext", "data_ptr"):
            total[k] = total.get(k, 0) + p.report[k]
    total["externs"] = sorted({e for p in parts.values()
                               for e in p.report["externs"]})
    total["_code_bytes"] = code_bytes
    total["_data_bytes"] = data_bytes
    total["_data_fsize"] = data_fsize
    return list(parts.values()), total


def _pack_libs(out_dir: Path, parts: list["_Part"], d: dict,
               module_indices: set[int]) -> str:
    """Pack the split objects into reconstructed vendor archives via wlib.

    Placement caveat (measured 2026-07-10): linking THROUGH the archives
    (`LIBRARY` or `FILE lib(module)`) defers module placement in wlink
    10.0a, breaking PS's interleaved layout — so the layout-faithful
    rebuild keeps FILE-ing the loose objects; the archives are the
    faithful *artifact* form and serve consumers where layout doesn't
    matter (e.g. the smk-player).
    """
    from c2.buildenv import _run_in_container, _STOCK_IMAGE

    mods = d["modules"]
    # part name -> lib via any of its module names
    part_lib: dict[str, str] = {}
    for mi in module_indices:
        lib = _lib_of(mods[mi].get("name") or "")
        if lib:
            part_lib[_mod_base(mods, mi)] = lib
    by_lib: dict[str, list[str]] = {}
    for p in parts:
        lib = part_lib.get(p.name)
        if lib:
            by_lib.setdefault(lib, []).append(p.name)
    notes = []
    for lib, members in by_lib.items():
        (out_dir / lib).unlink(missing_ok=True)
        cmd = f"wlib -n {lib} " + " ".join(f"+{m}.obj" for m in members)
        ok, out = _run_in_container(out_dir.resolve(), _STOCK_IMAGE, cmd,
                                    timeout=300)
        if not (out_dir / lib).exists():
            raise RuntimeError(f"wlib failed for {lib}:\n{out}")
        notes.append(f"{lib}({len(members)} modules, "
                     f"{(out_dir / lib).stat().st_size}b)")
    return " + ".join(notes)


def cown_data_owner(alld, dstarts, off):
    import bisect
    i = bisect.bisect_right(dstarts, off) - 1
    return alld[i] if 0 <= i < len(alld) else None


def _verify_verbatim(parts: list[_Part], total: _Report) -> tuple[int, int]:
    """Assert non-fixup bytes are verbatim from PS.EXE.  Returns (checked, bad).

    Checks BOTH emitted segments of every part against the source image,
    masking only that segment's own 4-byte fixup fields.
    """
    import bisect as _b
    code_bytes = total["_code_bytes"]
    data_bytes = total["_data_bytes"]
    data_fsize = total["_data_fsize"]
    checked = bad = 0

    def masked(offsets_sorted, off):
        i = _b.bisect_right(offsets_sorted, off) - 1
        return i >= 0 and offsets_sorted[i] <= off < offsets_sorted[i] + 4

    for p in parts:
        tfix = sorted(f.offset for f in p.text.fixups)
        for c in p.clusters:
            for i in range(c["end"] - c["start"]):
                toff = c["text_off"] + i
                if masked(tfix, toff):
                    continue
                checked += 1
                if p.text.data[toff] != code_bytes[c["start"] + i]:
                    bad += 1
        for kind_want, seg in (("const", p.const_seg), ("data", p.data_seg)):
            if seg is None:
                continue
            dfix = sorted(f.offset for f in seg.fixups)
            for st, en, kind, base in p.dranges:
                if kind != kind_want:
                    continue
                for i in range(min(en, data_fsize) - st):
                    doff = base + i
                    if masked(dfix, doff):
                        continue
                    checked += 1
                    if seg.data[doff] != data_bytes[st + i]:
                        bad += 1
    return checked, bad


def delink(
    selectors: Annotated[Optional[list[str]], typer.Argument(
        help="Module name substring(s) (e.g. unsmack.ASM). Omit with --group.")] = None,
    group: Annotated[Optional[str], typer.Option(
        "--group", "-g", help="Predefined library group (e.g. smacker).")] = None,
    output: Annotated[Optional[Path], typer.Option(
        "--output", "-o",
        help="Output .obj path (merged) or directory (--split).")] = None,
    split: Annotated[bool, typer.Option(
        "--split", help="Emit one .obj PER ORIGINAL MODULE (into the -o "
                        "directory) instead of one merged object.")] = False,
    libs: Annotated[bool, typer.Option(
        "--libs", help="With --split: also pack the objects into the "
                       "reconstructed vendor archives (ail.lib / smack.lib) "
                       "via wlib, mirroring the original link inputs.")] = False,
    module_name: Annotated[Optional[str], typer.Option(
        "--name", help="THEADR module name (merged mode; default from output/group).")] = None,
    symbols_json: Annotated[Path, typer.Option(
        "--symbols", help="symbols.json path.")] = Path("data/out/symbols.json"),
    exe_path: Annotated[Path, typer.Option(
        "--exe", help="PS.EXE path.")] = Path("data/PS.EXE"),
    verify: Annotated[bool, typer.Option(
        "--verify", help="Assert non-relocated bytes are verbatim from PS.EXE.")] = False,
    list_groups: Annotated[bool, typer.Option(
        "--list", help="List predefined groups and exit.")] = False,
    as_json: Annotated[bool, typer.Option("--json", help="JSON report.")] = False,
) -> None:
    """Delink a module set from PS.EXE into linkable OMF .obj file(s)."""
    if list_groups:
        for g, subs in _GROUPS.items():
            typer.echo(f"  {g:12} {subs}")
        return
    selectors = selectors or []
    if not selectors and not group:
        raise typer.BadParameter("give a module selector or --group")

    from c2.original import ensure_original
    ensure_original(exe_path)

    ctx = _load_context(symbols_json, exe_path)
    d = ctx[0]
    module_indices = _resolve_modules(d, selectors, group)
    if not module_indices:
        raise typer.BadParameter("no modules matched")

    if module_name is None:
        module_name = (group or (output.stem if output else selectors[0]))
    parts, total = _delink(*ctx, module_indices=module_indices,
                           module_name=module_name, split=split)

    if verify:
        checked, bad = _verify_verbatim(parts, total)
        total["verify_checked"] = checked
        total["verify_bad"] = bad
        if bad:
            typer.echo(f"VERBATIM CHECK FAILED: {bad}/{checked} bytes differ",
                       err=True)
            raise typer.Exit(1)

    outputs: list[str] = []
    lib_note = ""
    if output:
        if split:
            output.mkdir(parents=True, exist_ok=True)
            for p in parts:
                obj = p.o.build()
                (output / f"{p.name}.obj").write_bytes(obj)
                outputs.append(f"{p.name}.obj({len(obj)}b)")
            total["output"] = str(output)
            if libs:
                lib_note = _pack_libs(output, parts, d, module_indices)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            obj = parts[0].o.build()
            output.write_bytes(obj)
            total["obj_bytes"] = len(obj)
            total["output"] = str(output)

    if as_json:
        clean = {k: v for k, v in total.items() if not k.startswith("_")}
        clean["parts"] = [{k: v for k, v in p.report.items()
                           if not k.startswith("_")} for p in parts]
        typer.echo(json.dumps(clean, indent=2))
        return

    mods = d["modules"]
    typer.echo(f"delink: {module_name}" + (" (split)" if split else ""))
    typer.echo(f"  modules: " + ", ".join(
        mods[i]["name"].rsplit("\\", 1)[-1] for i in sorted(module_indices)))
    typer.echo(f"  {total['functions']} funcs in {total['clusters']} cluster(s), "
               f"{total['publics']} public + {total['data_publics']} data public"
               + (f", {total['synthetics']} synthetic label(s)"
                  if total.get("synthetics") else ""))
    typer.echo(f"  _TEXT {total['text_bytes']}b  _DATA {total['data_bytes']}b  "
               f"_BSS {total['bss_bytes']}b  ({total['data_named']} named + "
               f"{total['data_inlined']} inlined foreign region(s)"
               + (f", {total['code_tables']} code jump-table(s)"
                  if total.get('code_tables') else "") + ")")
    typer.echo(f"  relocations: abs-data {total['abs_data']}  abs-code {total['abs_code']}  "
               f"abs-ext {total['abs_ext']}  rel-internal {total['rel_internal']}  "
               f"rel-ext {total['rel_ext']}  data-ptr {total['data_ptr']}")
    typer.echo(f"  externs ({len(total['externs'])}): "
               + ", ".join(total["externs"][:8])
               + (" ..." if len(total["externs"]) > 8 else ""))
    if split:
        for p in parts:
            r = p.report
            typer.echo(f"    {p.name + '.obj':14} _TEXT {r['text_bytes']:6}b  "
                       f"_DATA {r['data_bytes']:5}b  _BSS {r['bss_bytes']:5}b  "
                       f"{r['functions']:3} fn")
    if verify:
        typer.echo(f"  verbatim check: {total['verify_checked']} bytes  OK")
    if output:
        if split:
            typer.echo(f"  wrote {len(parts)} obj(s) -> {output}")
            if lib_note:
                typer.echo(f"  packed: {lib_note}")
        else:
            typer.echo(f"  wrote {total['obj_bytes']}b -> {output}")
