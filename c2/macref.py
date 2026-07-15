"""Mac (PowerPC) reference binaries -- per-function byte/disasm oracle.

Two 1996 CW Pro 1 Mac builds of Caesar II carry the engine's function
names inline as CodeWarrior/AIX-style TRACEBACK TABLES (see
MAC/ANALYSIS.md): after each function's final instruction sits a zero
marker word, an 8-byte traceback header, the function LENGTH
(tb_offset), and the dot-prefixed name.  That gives exact per-function
byte ranges, not just names:

    French retail 1996-11-26  -- 1,575 named functions (full game)
    Demo          1996-10-04  -- 1,309 named functions (cross-check)

Why this matters for the PC decomp (validated on devolve_a_building /
evolve_a_building, 2026-06-12): the Mac port compiles the SAME C source
with CW Pro 1, which neither schedules (operands sit next to their
uses) nor cross-function tail-merges (Mac evolve is a full 276-byte
body while PS merged it into devolve).  The PPC disassembly therefore
reads as a ~1:1 statement-level rendition of the original source --
arm structure, goto/do_call convergence, byte-table indexing,
constants (0x5DF threshold, *4+0x20/0x63) are all directly visible.
It is a SOURCE-SHAPE oracle, not a byte oracle: register seating,
frame layout and the PC-side merge phenomena still come from PS.EXE
and the wcc386 trace image.

CAVEAT (grounded): the Mac source is a LATER snapshot (1996-10/11 vs
PS's 1995 vintage); small drifts exist -- compare structure, not
gospel.  Known example: none yet beyond content cuts in the demo
(demo evolve_region is a 4-byte stub; use the French retail).

Layout of a traceback record (empirically verified on both builds):

    <function code ...>  blr
    00 00 00 00          zero marker (= function code END)
    version lang f2 f3 f4 f5 f6 f7   8-byte header
      f2 & 0x20 = has_tboff, f3 & 0x40 = name_present
      (f6|f7 nonzero -> one extra parminfo word before tb_offset)
    tb_offset:u32        function length: START = marker - tb_offset
    name_len:u16, name   dot-prefixed identifier ('.devolve_a_building')

The index is cached as JSON keyed by the PEF file's sha256.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parent.parent
CACHE_DIR = REPO / ".c2-cache" / "mac"

#: build id -> PEF path (data fork).  The demo data fork is the unar
#: output of the .sit (see MAC/ANALYSIS.md for re-extraction); the
#: French retail PEF is hcopy'd out of the Toast HFS image:
#:   nix-shell -p hfsutils --run 'hmount "Caesar™ II 1.0.toast"; \
#:     hcopy -r ":Caesar* II Optimale:Caesar* II 1.0" out.pef'
BUILDS = {
    "fr": REPO / "MAC" / "extracted" / "French retail" /
          "Caesar_II_1.0_fr.pef",
    "demo": REPO / "MAC" / "extracted" / "Caesar II Demo Mac (1996-10-04)" /
            "Caesar II Demo Folder" / "Caesar\u2122 II Demo",
}

_NAME_RE = re.compile(rb"\.?[A-Za-z_$][A-Za-z0-9_$]*")


def pef_code_section(raw: bytes) -> bytes:
    """Carve the (uncompressed, kind-0) code section out of a PEF."""
    if raw[:8] != b"Joy!peff":
        raise ValueError("not a PEF container")
    sec_n = struct.unpack(">H", raw[32:34])[0]
    for i in range(sec_n):
        off = 40 + i * 28
        (_nameOff, _defAddr, _totalLen, _unpackedLen, cont_len, cont_off,
         kind, _share, _align, _r) = struct.unpack(">iIIIIIBBBB",
                                                   raw[off:off + 28])
        if kind == 0:
            return raw[cont_off:cont_off + cont_len]
    raise ValueError("no code section in PEF")


def parse_traceback_index(code: bytes) -> list[tuple[int, int, str]]:
    """Scan a PEF code section for CW traceback tables.

    Returns [(start, end, name)] in address order; ``code[start:end]``
    is exactly the function's instructions (end = zero-marker address).
    """
    out: list[tuple[int, int, str]] = []
    pos, n = 0, len(code)
    while pos + 20 <= n:
        zi = code.find(b"\x00\x00\x00\x00", pos)
        if zi < 0:
            break
        if zi % 4:
            pos = zi + (4 - zi % 4)
            continue
        tb = code[zi + 4:zi + 12]
        if len(tb) < 8:
            break
        version, _lang, f2, f3, f6, f7 = tb[0], tb[1], tb[2], tb[3], tb[6], tb[7]
        if not (version == 0 and (f2 & 0x20) and (f3 & 0x40)):
            pos = zi + 4
            continue
        o = zi + 12
        if f6 or f7:                      # parminfo word present
            o += 4
        if o + 6 > n:
            break
        tb_off = struct.unpack(">I", code[o:o + 4])[0]
        nlen = struct.unpack(">H", code[o + 4:o + 6])[0]
        o += 6
        name = code[o:o + nlen]
        if not (0 < nlen <= 64 and 0 < tb_off <= zi
                and _NAME_RE.fullmatch(name)):
            pos = zi + 4
            continue
        out.append((zi - tb_off, zi, name.decode().lstrip(".")))
        pos = o + nlen
    return out


class MacBuild:
    """One indexed Mac binary: name -> exact function bytes + disasm."""

    def __init__(self, build: str = "fr", path: Optional[Path] = None):
        self.build = build
        self.path = Path(path) if path else BUILDS[build]
        if not self.path.exists():
            raise FileNotFoundError(
                f"Mac build '{build}' not extracted at {self.path} -- see "
                "MAC/ANALYSIS.md / c2/macref.py header for extraction steps")
        raw = self.path.read_bytes()
        self.sha = hashlib.sha256(raw).hexdigest()
        self.code = pef_code_section(raw)
        self.index = self._load_index()
        self.by_name = {nm: (s, e) for s, e, nm in self.index}
        self.by_start = {s: nm for s, _e, nm in self.index}
        self.toc_names = load_toc_map(build)   # {} until built

    # -- index cache -----------------------------------------------------
    def _load_index(self) -> list[tuple[int, int, str]]:
        cache = CACHE_DIR / f"{self.build}.{self.sha[:16]}.json"
        if cache.exists():
            try:
                return [tuple(x) for x in json.loads(cache.read_text())]
            except Exception:
                pass
        idx = parse_traceback_index(self.code)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(idx))
        return idx

    # -- queries ----------------------------------------------------------
    def lookup(self, name: str) -> Optional[tuple[int, int]]:
        return self.by_name.get(name)

    def grep(self, pattern: str) -> list[str]:
        rx = re.compile(pattern)
        return [nm for _s, _e, nm in self.index if rx.search(nm)]

    def func_bytes(self, name: str) -> bytes:
        s, e = self._need(name)
        return self.code[s:e]

    def _need(self, name: str) -> tuple[int, int]:
        r = self.lookup(name)
        if r is None:
            raise KeyError(f"{name!r} not in {self.build} index "
                           f"({len(self.index)} functions); try grep")
        return r

    def disasm(self, name: str, with_bytes: bool = False) -> str:
        """Annotated PPC disassembly: bl/b targets resolved to function
        names, in-function branch targets rendered as local labels, and
        TOC-relative loads (off(r2)) tagged -- a stable per-global key
        usable to correlate globals ACROSS functions."""
        from capstone import CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN, Cs
        s, e = self._need(name)
        md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
        ins_list = list(md.disasm(self.code[s:e], s))
        # local label targets (branches within [s,e))
        targets = set()
        for ins in ins_list:
            t = _branch_target(ins)
            if t is not None and s <= t < e:
                targets.add(t)
        lines = []
        for ins in ins_list:
            label = f"L{ins.address - s:x}:" if ins.address in targets else ""
            note = ""
            t = _branch_target(ins)
            if t is not None:
                if s <= t < e:
                    note = f"  -> L{t - s:x}"
                elif t in self.by_start:
                    note = f"  <{self.by_start[t]}>"
            m = re.search(r"(-?0x[0-9a-f]+|\-?\d+)\(r2\)", ins.op_str)
            if m:
                key = int(m.group(1), 0)
                gname = self.toc_names.get(key)
                note += (f"  ; &{gname}" if gname
                         else f"  ; toc[{m.group(1)}]")
            bcol = (self.code[ins.address:ins.address + ins.size].hex(" ")
                    + "  ") if with_bytes else ""
            lines.append(f"{label:8s}{ins.address - s:5x}: {bcol}"
                         f"{ins.mnemonic:8s} {ins.op_str}{note}")
        return "\n".join(lines)


def _branch_target(ins) -> Optional[int]:
    if ins.mnemonic in ("b", "bl") or ins.mnemonic.startswith(
            ("beq", "bne", "blt", "ble", "bgt", "bge", "bdnz", "bdz")):
        m = re.search(r"0x[0-9a-f]+$", ins.op_str)
        if m:
            return int(m.group(0), 16)
    return None


_cache: dict[str, MacBuild] = {}


def get(build: str = "fr") -> MacBuild:
    """Memoized accessor (index parse ~0.5s, then free)."""
    if build not in _cache:
        _cache[build] = MacBuild(build)
    return _cache[build]


# ---------------------------------------------------------------------------
# TOC -> PC global-name mapping
#
# Mac code reaches globals through r2-relative TOC slots (`lwz rP, K(r2)`);
# each slot K holds one global's address, so K is a stable per-global key.
# We recover K -> PC-global-name by CO-OCCURRENCE over the ~1,263 functions
# present in both binaries: a slot's global must appear in (nearly) every PC
# function whose Mac twin references the slot.  Candidate sets are narrowed
# by soft intersection (>= 85% of occurrences), seeded with ground-truth
# anchors from byte-exact recoveries, then resolved by iterative singleton
# elimination; a final pass drops any mapping violated in > 30% of its
# supporting functions.  2026-06-12 run: 246 slots, 0 violations.
# ---------------------------------------------------------------------------

#: ground-truth anchors from byte-exact recoveries (flag_range et al.):
#: the Mac registers' roles were read directly off the validated disasm.
TOC_SEEDS = {
    -0x7694: "city_map",
    -0x70d4: "gmn_sptr",
    -0x715c: "gmn_y",
    -0x7164: "gmn_x",
}


def _toc_map_path(build: str) -> Path:
    return CACHE_DIR / f"toc_names.{build}.json"


def load_toc_map(build: str = "fr") -> dict[int, str]:
    p = _toc_map_path(build)
    if p.exists():
        try:
            return {int(k): v for k, v in json.loads(p.read_text()).items()}
        except Exception:
            pass
    return {}


def build_toc_map(build: str = "fr", repo: Path = REPO) -> dict[int, str]:
    """Correlate Mac TOC slots with PC global names (see header).  Writes
    the result to the cache and returns it.  Needs data/out/symbols.json +
    data/out/le_code.bin (the PS debug-build artifacts)."""
    import bisect
    from collections import Counter, defaultdict

    from capstone import (CS_ARCH_PPC, CS_ARCH_X86, CS_MODE_32,
                          CS_MODE_BIG_ENDIAN, Cs)

    b = get(build)
    syms = json.loads((repo / "data/out/symbols.json").read_text())["symbols"]
    code_syms = sorted((s for s in syms
                        if s["kind"] == "code" and s["segment"] == 1),
                       key=lambda s: s["offset"])
    data_syms = sorted((s for s in syms
                        if s["is_data"] and s["segment"] == 2),
                       key=lambda s: s["offset"])
    data_offs = [s["offset"] for s in data_syms]
    le_code = (repo / "data/out/le_code.bin").read_bytes()
    pc_rng = {}
    for i, s in enumerate(code_syms):
        end = (code_syms[i + 1]["offset"] if i + 1 < len(code_syms)
               else len(le_code))
        pc_rng[s["name"]] = (s["offset"], min(end, s["offset"] + 8192))

    md_x86 = Cs(CS_ARCH_X86, CS_MODE_32)
    md_x86.detail = True
    md_ppc = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
    data_max = data_syms[-1]["offset"] + 0x1000

    def pc_globals(name):
        s, e = pc_rng[name]
        out = set()
        for ins in md_x86.disasm(le_code[s:e], s):
            for op in ins.operands:
                v = (op.value.mem.disp if op.type == 3 else
                     op.value.imm if op.type == 2 else 0)
                if 0x1000 <= v < data_max:
                    i = bisect.bisect_right(data_offs, v) - 1
                    if i >= 0:
                        out.add(data_syms[i]["name"])
            if ins.mnemonic == "ret":
                break
        return out

    def mac_tocs(name):
        s, e = b.by_name[name]
        out = set()
        for ins in md_ppc.disasm(b.code[s:e], s):
            m = re.match(r"(-?0x[0-9a-f]+|-?\d+)\(r2\)$", ins.op_str.split(", ")[-1])
            if ins.mnemonic == "lwz" and m:
                out.add(int(m.group(1), 0))
        return out

    pairs = []
    for nm in sorted(set(pc_rng) & set(b.by_name)):
        try:
            p, m = pc_globals(nm), mac_tocs(nm)
        except Exception:
            continue
        if p and m:
            pairs.append((p, m))

    occ = defaultdict(list)
    for p, m in pairs:
        for k in m:
            occ[k].append(p)
    work = {}
    for k, sets in occ.items():
        if len(sets) < 2:
            continue
        cnt = Counter()
        for s in sets:
            cnt.update(s)
        work[k] = {g for g, c in cnt.items()
                   if c >= max(2, 0.85 * len(sets))}

    toc_map = dict(TOC_SEEDS)
    rev = {g: k for k, g in toc_map.items()}
    for k, c in work.items():            # pre-seeded singletons
        if k not in toc_map and len(c) == 1:
            g, = c
            if g not in rev:
                toc_map[k] = g
                rev[g] = k
    changed, rounds = True, 0
    while changed and rounds < 100:
        changed, rounds = False, rounds + 1
        for k, c in work.items():
            if k in toc_map:
                continue
            c2 = {g for g in c if g not in rev}
            if len(c2) == 1:
                g, = c2
                toc_map[k] = g
                rev[g] = k
                changed = True

    # verification: drop mappings violated in > 30% of supporting fns
    viol, supp = Counter(), Counter()
    for p, m in pairs:
        for k in m:
            if k in toc_map:
                supp[k] += 1
                if toc_map[k] not in p:
                    viol[k] += 1
    toc_map = {k: g for k, g in toc_map.items()
               if k in TOC_SEEDS
               or not supp[k] or viol[k] / supp[k] <= 0.3}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _toc_map_path(build).write_text(
        json.dumps({str(k): v for k, v in sorted(toc_map.items())}, indent=0))
    return toc_map
