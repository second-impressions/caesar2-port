r"""Cross-build function map for the three Caesar II PS.EXE pressings.

Background
----------
Three byte-distinct DOS PS.EXE builds exist across the CD collection,
all produced by the **same toolchain** (Watcom C/C++32 10.0a + DOS/4GW
Professional — proven by byte-identical CRT leaf functions and the
identical 228 KB extender stub):

  ============  ==========  ============  =========  ==================
  build id      date        size (bytes)  debug -d1  source disc(s)
  ============  ==========  ============  =========  ==================
  dbg-1996-04   1996-04-01     1,304,734  YES        all 1996/97 rereleases (== data/PS.EXE)
  rel-1995-10   1995-10-04     1,040,111  no         USA 1995-10-06, Europe OEM/96-04-25, France, Germany
  rel-1995-09   1995-09-21     1,039,599  no         Caesar II (Europe)
  ============  ==========  ============  =========  ==================

Only ``dbg-1996-04`` carries ``-d1`` line/symbol debug info (the
``D:\C2\CODE\*.c`` paths) — it is the source of every function name we
have.  The two 1995 release builds are *un-symbolled*.

Because Watcom links each translation unit's functions contiguously and
**in source order**, the function layout order is preserved across all
three builds (empirically: <3 % order inversions among byte-exact
anchors, and those are short-needle false positives — see
``version_match`` Phases A3/A4, which exploit exactly this).  That makes
it possible to transfer every debug-build name into the two un-symbolled
1995 builds, bucketed per build as:

  * **exact**   — byte-identical after masking fixups + rel32 disps
                  (the source function is unchanged since that build).
  * **near**    — ≤ 8 masked byte-diff (a tiny source/codegen tweak).
  * **differs** — anchored by module geometry but body changed
                  (the function evolved between 1995 and 1996).
  * **absent**  — could not be anchored (added after that build, or
                  too heavily rewritten / removed).

This module:

  1. Self-extracts each build's PS.EXE straight from the CD ``.zip``
     (pure-Python MODE1/2352 → ISO9660 → ``HD/PS.EXE``; no bchunk/7z),
     md5-verified and cached under ``.c2-cache/crossbuild/``.
  2. Runs ``version_match`` to anchor every named function into each
     1995 build.
  3. Emits a persistent, human-readable map to
     ``data/out/crossbuild-map.json`` (one record per function, with
     per-build status / diff / candidate offset).
  4. Exposes ``load_crossbuild_map`` / ``crossbuild_status`` /
     ``render_crossbuild_hint`` for use during decomp (the
     ``decomp-verify -v`` ``Cross-build:`` header).

Why it helps the decomp
------------------------
* A function **exact across all three builds** has the most stable
  source shape in the corpus — highest-confidence decomp target, and
  a free triple-witness when validating recompiled C.
* A function that **differs in 1995** flags source that evolved; the
  decomp targets the 1996 shape specifically, so knowing it moved is a
  useful caution.
* The reloc-only deltas independently confirm which immediates are
  address operands (a second witness to the LE fixup table).
"""

from __future__ import annotations

import hashlib
import json
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional

import typer

from c2.commands.version_match import build_reference, match_variant


# ── Build registry ────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MAP_PATH = REPO_ROOT / "data" / "out" / "crossbuild-map.json"
CACHE_DIR = REPO_ROOT / ".c2-cache" / "crossbuild"


@dataclass(frozen=True)
class Build:
    """A registered PS.EXE pressing."""

    id: str
    date: str
    size: int
    md5: str
    has_debug: bool
    role: str  # "reference" | "release"
    # Source: either a repo-relative exe path, or a CD zip + inner ISO path.
    exe_path: Optional[str] = None
    cd_zip: Optional[str] = None
    iso_path: str = "HD/PS.EXE"
    note: str = ""


# The reference MUST be first.  Only distinct binaries are listed — the
# many CDs that share a PS.EXE md5 collapse onto one Build each.
BUILDS: list[Build] = [
    Build(
        id="dbg-1996-04",
        date="1996-04-01",
        size=1_304_734,
        md5="23bdf1fdd03d1a64f5e695d18e4861eb",
        has_debug=True,
        role="reference",
        exe_path="data/PS.EXE",
        note=r"Debug build (-d1); the only one with D:\C2\CODE paths. Source of all names.",
    ),
    Build(
        id="rel-1995-10",
        date="1995-10-04",
        size=1_040_111,
        md5="4849288ecbd2c2a2ddd1ed41c706f290",
        has_debug=False,
        role="release",
        cd_zip="CDs/Caesar II (USA) (Rerelease) (1995-10-06).zip",
        note="Un-symbolled release; also on Europe OEM/96-04-25, France, Germany.",
    ),
    Build(
        id="rel-1995-09",
        date="1995-09-21",
        size=1_039_599,
        md5="939bbd906e68567bb01cd41767467649",
        has_debug=False,
        role="release",
        cd_zip="CDs/Caesar II (Europe).zip",
        note="Earliest known PS.EXE; un-symbolled release build.",
    ),
]

REFERENCE_BUILD = BUILDS[0]
RELEASE_BUILDS = [b for b in BUILDS if b.role != "reference"]


def build_by_id(build_id: str) -> Optional[Build]:
    return next((b for b in BUILDS if b.id == build_id), None)


# ── Pure-Python PS.EXE extraction from CD images ───────────────────────────────

_SECTOR = 2352  # MODE1/2352 raw sector
_DATA_OFF = 16  # 12 sync + 4 header
_DATA_LEN = 2048


def iso_from_mode1_bin(bin_bytes: bytes) -> bytes:
    """Convert a MODE1/2352 raw track image to a flat 2048-byte/sector
    ISO9660 image by carving the user-data field out of every sector."""
    n = len(bin_bytes) // _SECTOR
    out = bytearray(n * _DATA_LEN)
    for i in range(n):
        base = i * _SECTOR + _DATA_OFF
        out[i * _DATA_LEN : (i + 1) * _DATA_LEN] = bin_bytes[base : base + _DATA_LEN]
    return bytes(out)


def _parse_dir_record(rec: bytes) -> tuple[Optional[tuple[int, int, int, bytes]], int]:
    length = rec[0]
    if length == 0:
        return None, 0
    ext_lba = struct.unpack_from("<I", rec, 2)[0]
    size = struct.unpack_from("<I", rec, 10)[0]
    flags = rec[25]
    nlen = rec[32]
    name = rec[33 : 33 + nlen]
    return (ext_lba, size, flags, name), length


def iso_read_file(iso: bytes, target_path: str) -> bytes:
    """Read a file out of a flat ISO9660 image by path (case-insensitive,
    version-suffix tolerant).  Minimal walker — directories only, no
    Rock Ridge / Joliet needed for the DOS disc layout."""
    pvd = iso[16 * 2048 : 17 * 2048]
    if pvd[1:6] != b"CD001":
        raise ValueError("not an ISO9660 image (no CD001 at sector 16)")
    (rlba, rsize, _, _), _ = _parse_dir_record(pvd[156 : 156 + 34])

    def list_dir(lba: int, size: int) -> list[tuple[int, int, int, bytes]]:
        data = iso[lba * 2048 : lba * 2048 + size]
        entries: list[tuple[int, int, int, bytes]] = []
        pos = 0
        while pos < len(data):
            if data[pos] == 0:
                nxt = ((pos // 2048) + 1) * 2048
                if nxt >= len(data):
                    break
                pos = nxt
                continue
            rec, length = _parse_dir_record(data[pos : pos + 255])
            if rec is None:
                break
            entries.append(rec)
            pos += length
        return entries

    cur = (rlba, rsize)
    parts = target_path.strip("/").split("/")
    for i, part in enumerate(parts):
        match = None
        for lba, size, flags, name in list_dir(*cur):
            nm = name.split(b";")[0].decode("latin1")
            if nm.upper() == part.upper():
                match = (lba, size, flags)
                break
        if match is None:
            raise FileNotFoundError(f"{part} (in {target_path})")
        if i == len(parts) - 1:
            return iso[match[0] * 2048 : match[0] * 2048 + match[1]]
        cur = (match[0], match[1])
    raise FileNotFoundError(target_path)


def _extract_from_cd_zip(zip_path: Path, iso_path: str) -> bytes:
    with zipfile.ZipFile(zip_path) as z:
        bins = [n for n in z.namelist() if n.lower().endswith(".bin")]
        if not bins:
            raise FileNotFoundError(f"no .bin track inside {zip_path}")
        bin_bytes = z.read(bins[0])
    iso = iso_from_mode1_bin(bin_bytes)
    return iso_read_file(iso, iso_path)


def resolve_build_exe(build: Build, *, cache_dir: Path = CACHE_DIR) -> Path:
    """Return a filesystem path to ``build``'s PS.EXE, extracting and
    caching from the CD image if necessary.  Verifies md5."""
    # Direct exe (the reference).
    if build.exe_path:
        p = REPO_ROOT / build.exe_path
        if not p.exists():
            raise FileNotFoundError(p)
        _verify_md5(p.read_bytes(), build)
        return p

    # Cached extraction.
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{build.id}.exe"
    if cached.exists() and hashlib.md5(cached.read_bytes()).hexdigest() == build.md5:
        return cached

    if not build.cd_zip:
        raise ValueError(f"build {build.id} has neither exe_path nor cd_zip")
    zip_path = REPO_ROOT / build.cd_zip
    if not zip_path.exists():
        raise FileNotFoundError(f"CD image missing: {zip_path}")
    exe = _extract_from_cd_zip(zip_path, build.iso_path)
    _verify_md5(exe, build)
    cached.write_bytes(exe)
    return cached


def _verify_md5(data: bytes, build: Build) -> None:
    got = hashlib.md5(data).hexdigest()
    if got != build.md5:
        raise ValueError(
            f"md5 mismatch for build {build.id}: expected {build.md5}, got {got}"
        )


# ── Map construction ───────────────────────────────────────────────────────────

@dataclass
class BuildColumn:
    """Per-build match summary for the report header."""

    build: Build
    anchored: int
    exact: int
    near: int
    differs: int
    absent: int


def _recover_absent(
    ref,
    variant_exe: Path,
    records: dict,
    build_id: str,
    matched_addrs: set[int],
) -> list[tuple[int, str, int, int]]:
    """Tolerant whole-body search for ref functions version_match left
    unanchored.  Returns ``(ref_addr, status, diff_bytes, cand_off)`` for
    each newly-recovered function.

    Search is fixup/rel-mask aware on both sides: the ref body already has
    fixup+rel32 bytes zeroed (``RefFn.masked``); we anchor on the first
    16-byte all-nonzero window and accept a hit only when every remaining
    non-masked byte matches (ignoring the candidate's own fixup positions).
    A unique hit ⇒ recover; ambiguous/none ⇒ leave absent.
    """
    from c2.commands.decomp_verify import _load_le_code_and_fixups

    code, fix = _load_le_code_and_fixups(variant_exe)
    cm = bytearray(code)
    for o in fix:
        if 0 <= o < len(cm):
            cm[o] = 0
    cm = bytes(cm)

    out: list[tuple[int, str, int, int]] = []
    for addr, rec in records.items():
        if addr in matched_addrs or build_id in rec["builds"]:
            continue
        rf = ref.fns[addr]
        body = rf.masked  # fixup+rel masked
        nz = [i for i, byte in enumerate(body) if byte != 0]
        if len(nz) < 16:
            continue  # too small to anchor confidently → leave absent
        a0 = nz[0]
        if not all(body[a0 + k] != 0 for k in range(16)):
            continue
        anchor = bytes(body[a0 : a0 + 16])
        # collect candidate bases with a verified body match (≤8 b diff)
        hits: list[tuple[int, int]] = []  # (diff, base)
        start = 0
        while len(hits) < 3:
            p = cm.find(anchor, start)
            if p < 0:
                break
            base = p - a0
            start = p + 1
            if base < 0 or base + len(body) > len(cm):
                continue
            diff = 0
            for i in nz:
                cb = cm[base + i]
                if cb == 0:
                    continue  # candidate fixup position
                if cb != body[i]:
                    diff += 1
                    if diff > 8:
                        break
            if diff <= 8:
                hits.append((diff, base))
        if len(hits) == 1:
            diff, base = hits[0]
            status = "exact" if diff == 0 else "near"
            out.append((addr, status, diff, base))
    return out


def build_map(
    *,
    symbols: Path = REPO_ROOT / "data" / "out" / "symbols.json",
    reference_exe: Optional[Path] = None,
    builds: Optional[list[Build]] = None,
) -> dict:
    """Build the cross-build map.  Returns the JSON-serialisable dict."""
    builds = builds or BUILDS
    ref_build = builds[0]
    ref_exe = reference_exe or resolve_build_exe(ref_build)
    ref = build_reference(symbols, ref_exe)

    # function name → record skeleton (preserve ref address order)
    records: dict[int, dict] = {}
    for addr in sorted(ref.fns):
        rf = ref.fns[addr]
        records[addr] = {
            "function": rf.name,
            "module_index": rf.module_index,
            "ref_addr": rf.addr,
            "ref_addr_hex": f"0x{rf.addr:08x}",
            "ref_size": rf.size,
            "builds": {
                ref_build.id: {
                    "status": "reference",
                    "addr": rf.addr,
                    "addr_hex": f"0x{rf.addr:08x}",
                }
            },
        }

    columns: list[BuildColumn] = []
    for b in builds[1:]:
        variant_exe = resolve_build_exe(b)
        result = match_variant(ref, variant_exe)
        matched_addrs: set[int] = set()
        exact = near = differs = 0
        for m in result.matches:
            matched_addrs.add(m.ref_addr)
            if m.status == "exact":
                exact += 1
            elif m.status == "near":
                near += 1
            else:
                differs += 1
            records[m.ref_addr]["builds"][b.id] = {
                "status": m.status,
                "diff_bytes": m.diff_bytes,
                "cand_off": m.cand_off,
                "cand_off_hex": f"0x{m.cand_off:08x}",
                "method": m.method,
            }
        # Post-pass: recover functions version_match left unanchored
        # (e.g. isolated fns whose neighbours all changed, so module
        # interpolation couldn't bridge them) via a tolerant whole-body
        # masked search.  Reclassifies confirmed-present fns out of the
        # "absent" bucket so the count reflects genuine absence only.
        for ref_addr, status, diff, off in _recover_absent(
            ref, variant_exe, records, b.id, matched_addrs
        ):
            if status == "exact":
                exact += 1
            elif status == "near":
                near += 1
            else:
                differs += 1
            matched_addrs.add(ref_addr)
            records[ref_addr]["builds"][b.id] = {
                "status": status,
                "diff_bytes": diff,
                "cand_off": off,
                "cand_off_hex": f"0x{off:08x}",
                "method": "body-search",
            }

        absent = 0
        for addr, rec in records.items():
            if b.id not in rec["builds"]:
                rec["builds"][b.id] = {"status": "absent"}
                absent += 1
        columns.append(
            BuildColumn(
                build=b,
                anchored=len(matched_addrs),
                exact=exact,
                near=near,
                differs=differs,
                absent=absent,
            )
        )

    out = {
        "schema": "crossbuild-map/v1",
        "reference": {
            "id": ref_build.id,
            "date": ref_build.date,
            "md5": ref_build.md5,
            "exe": str(ref_exe),
            "functions": len(records),
        },
        "builds": [
            {
                "id": b.id,
                "date": b.date,
                "size": b.size,
                "md5": b.md5,
                "has_debug": b.has_debug,
                "role": b.role,
                "source": b.exe_path or b.cd_zip,
                "note": b.note,
            }
            for b in builds
        ],
        "summary": {
            col.build.id: {
                "anchored": col.anchored,
                "exact": col.exact,
                "near": col.near,
                "differs": col.differs,
                "absent": col.absent,
            }
            for col in columns
        },
        "functions": [records[a] for a in sorted(records)],
    }
    annotate_semantics(out, symbols=symbols, reference_exe=ref_exe, builds=builds)
    return out


# ── Semantic annotation (same work vs genuinely new) ───────────────────────────
#
# The byte buckets (exact/near/differs/absent) say *whether* a function
# changed; this pass says *what kind* of change it is, by comparing the
# multiset of named callees across builds:
#
#   * differs/near → compare ref callees vs the 1995 build's callees
#     (resolved through the map's cand_off → name index):
#       - same-work : identical callee multiset → pure codegen/source
#                     drift; behaviour unchanged.
#       - extended  : 1996 calls helpers the 1995 build didn't → new
#                     functionality bolted on.
#       - trimmed   : 1996 dropped callees the 1995 build had.
#       - reworked  : callee sets diverge both ways.
#   * absent → no 1995 counterpart, so classify by the module's 1995
#     anchor density + module kind:
#       - new-feature  : game module <25% anchored in 1995 → the whole
#                        feature area is new (debug screen, demo/outro
#                        sequences, screenshot capture, …).
#       - restructured : game module well-anchored but THIS body changed
#                        beyond recognition (forum subsystem, battle AI).
#       - library      : Watcom/RAD library TU (lib32 graphics rewrite,
#                        or a CRT helper newly linked because new code
#                        calls it).

_GAME_SRC_MARK = "C2\\CODE"


def _callees_at(code: bytes, slice_off: int, size: int,
                resolve, cs, addr_base: int) -> "list[str]":
    """Disassemble ``code[slice_off:slice_off+size]`` as if it were loaded
    at ``addr_base`` and return the resolved names of every ``E8 rel32``
    call target.  ``slice_off`` (where the bytes live) and ``addr_base``
    (the address space call targets resolve in) are decoupled so the
    reference can slice in RVA space but resolve targets in absolute
    address space, while the 1995 builds use cand_off for both."""
    body = code[slice_off : slice_off + size]
    names: list[str] = []
    for ins in cs.disasm(body, addr_base):
        b = ins.bytes
        if b and b[0] == 0xE8 and ins.size == 5:
            tgt = ins.address + 5 + int.from_bytes(b[1:5], "little", signed=True)
            nm = resolve(tgt)
            if nm:
                names.append(nm)
    return names


def annotate_semantics(
    data: dict,
    *,
    symbols: Path,
    reference_exe: Path,
    builds: Optional[list[Build]] = None,
) -> None:
    """Add a per-function ``semantic`` block (keyed by release-build id) to
    an already-built map ``data`` in place."""
    import capstone
    from collections import Counter, defaultdict
    from c2.commands.decomp_verify import _load_le_code_and_fixups

    builds = builds or BUILDS
    cs = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    cs.detail = False

    sym = json.loads(Path(symbols).read_text())
    code_base = sym["memory_map"]["objects"][0]["base_address_int"]
    addr2name = {s["address"]: s["name"] for s in sym["symbols"] if s.get("is_code")}
    addr2mod = {s["address"]: s.get("module_index", -1)
                for s in sym["symbols"] if s.get("is_code")}
    modnames = {mod["index"]: mod.get("name", "?") for mod in sym.get("modules", [])}

    ref_code, _ = _load_le_code_and_fixups(reference_exe)

    def ref_resolve(tgt: int) -> Optional[str]:
        nm = addr2name.get(tgt)
        return nm  # None ⇒ unnamed/sub — ignored in the comparison

    recs = data["functions"]
    sem_summary: dict[str, Counter] = {}

    for b in builds[1:]:
        code, _ = _load_le_code_and_fixups(resolve_build_exe(b))
        off2name = {}
        mod_total: Counter = Counter()
        mod_anchored: Counter = Counter()
        for rec in recs:
            mi = addr2mod.get(rec["ref_addr"], -1)
            mn = modnames.get(mi, "?")
            mod_total[mn] += 1
            info = rec["builds"].get(b.id, {})
            st = info.get("status")
            if st in ("exact", "near", "differs"):
                mod_anchored[mn] += 1
            if "cand_off" in info:
                off2name[info["cand_off"]] = rec["function"]

        def old_resolve(tgt: int) -> Optional[str]:
            return off2name.get(tgt)

        counts: Counter = Counter()
        for rec in recs:
            info = rec["builds"].get(b.id, {})
            st = info.get("status")
            mi = addr2mod.get(rec["ref_addr"], -1)
            mn = modnames.get(mi, "?")
            is_game = _GAME_SRC_MARK in mn
            sem: Optional[dict] = None

            if st in ("near", "differs"):
                rc = Counter(
                    n for n in _callees_at(
                        ref_code, rec["ref_addr"] - code_base, rec["ref_size"],
                        ref_resolve, cs, addr_base=rec["ref_addr"])
                )
                oc = Counter(
                    n for n in _callees_at(
                        code, info["cand_off"], rec["ref_size"], old_resolve, cs,
                        addr_base=info["cand_off"])
                )
                added = sorted((rc - oc).elements())
                dropped = sorted((oc - rc).elements())
                if not added and not dropped:
                    cls = "same-work"
                elif added and not dropped:
                    cls = "extended"
                elif dropped and not added:
                    cls = "trimmed"
                else:
                    cls = "reworked"
                sem = {"class": cls}
                if added:
                    sem["added_callees"] = added
                if dropped:
                    sem["dropped_callees"] = dropped
            elif st == "absent":
                tot = mod_total[mn] or 1
                rate = mod_anchored[mn] / tot
                if "lib32" in mn:
                    cls = "library"
                elif not is_game:
                    cls = "library"
                elif rate < 0.25:
                    cls = "new-feature"
                else:
                    cls = "restructured"
                sem = {"class": cls, "module": mn,
                       "module_anchor_pct": round(rate * 100, 1)}

            if sem is not None:
                rec.setdefault("semantic", {})[b.id] = sem
                counts[sem["class"]] += 1

        sem_summary[b.id] = counts

    for bid, counts in sem_summary.items():
        data["summary"][bid]["semantic"] = dict(counts)


def write_map(data: dict, path: Path = DEFAULT_MAP_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1) + "\n")
    return path


# ── Loader / query API (used during decomp) ────────────────────────────────────

_CACHE: dict[str, object] = {}


def load_crossbuild_map(path: Path = DEFAULT_MAP_PATH) -> Optional[dict]:
    """Load the persisted map (cached in-process).  Returns ``None`` if it
    has not been generated yet."""
    key = str(path)
    if key in _CACHE:
        return _CACHE[key]  # type: ignore[return-value]
    if not path.exists():
        _CACHE[key] = None
        return None
    data = json.loads(path.read_text())
    by_name = {rec["function"]: rec for rec in data.get("functions", [])}
    data["_by_name"] = by_name
    _CACHE[key] = data
    return data


def crossbuild_status(name: str, path: Path = DEFAULT_MAP_PATH) -> Optional[dict]:
    """Return the per-build status record for one function, or ``None``."""
    data = load_crossbuild_map(path)
    if not data:
        return None
    return data["_by_name"].get(name)


def render_crossbuild_hint(name: str, path: Path = DEFAULT_MAP_PATH) -> Optional[str]:
    """One-line decomp-verify hint, e.g.

        stable since 1995-09 (exact in rel-1995-10, rel-1995-09)
        body changed in rel-1995-09 (differs); exact in rel-1995-10
        added after 1995-10 (absent in rel-1995-10, rel-1995-09)

    Returns ``None`` when the map is missing or the function isn't in it.
    """
    rec = crossbuild_status(name, path)
    if not rec:
        return None
    data = load_crossbuild_map(path)
    assert data is not None
    rel_ids = [b["id"] for b in data["builds"] if b["role"] != "reference"]
    statuses = {bid: rec["builds"].get(bid, {}).get("status", "absent") for bid in rel_ids}

    sem = rec.get("semantic", {})

    if all(s == "exact" for s in statuses.values()) and statuses:
        return f"[green]stable across all builds[/] (exact in {', '.join(rel_ids)})"
    if all(s == "absent" for s in statuses.values()):
        # Differentiate genuinely-new vs restructured vs library.
        cls = next((sem[bid].get("class") for bid in rel_ids if bid in sem), None)
        if cls == "new-feature":
            return "[yellow]genuinely new in 1996[/] (feature area absent from the 1995 builds)"
        if cls == "restructured":
            return "[yellow]existed but rewritten[/] (body unrecognizable in the 1995 builds)"
        if cls == "library":
            return "[dim]library function not linked into the 1995 builds[/]"
        return f"[yellow]absent from the 1995 builds[/] ({', '.join(rel_ids)})"

    parts = []
    for bid in rel_ids:
        s = statuses[bid]
        diff = rec["builds"].get(bid, {}).get("diff_bytes")
        if s in ("near", "differs") and diff is not None:
            parts.append(f"{bid}: {s} ({diff} b)")
        else:
            parts.append(f"{bid}: {s}")
    line = " · ".join(parts)
    # Append the semantic verdict if the body changed in some build.
    cls = next((sem[bid].get("class") for bid in rel_ids if bid in sem), None)
    if cls == "same-work":
        line += "  — [green]same work[/] (identical callees; codegen drift only)"
    elif cls == "extended":
        added = next((sem[bid].get("added_callees", []) for bid in rel_ids if bid in sem), [])
        line += f"  — [yellow]extended in 1996[/] (+{', '.join(added[:3])})"
    elif cls == "reworked":
        line += "  — [yellow]reworked[/] (callee set diverges)"
    elif cls == "trimmed":
        line += "  — [yellow]trimmed in 1996[/]"
    return line


# ── CLI ─────────────────────────────────────────────────────────────────────────

def crossbuild_map(
    rebuild: Annotated[
        bool,
        typer.Option("--rebuild", help="Regenerate the map even if it exists."),
    ] = False,
    function: Annotated[
        Optional[str],
        typer.Option("--function", "-f", help="Query one function's per-build status."),
    ] = None,
    differs_only: Annotated[
        bool,
        typer.Option("--differs", help="List functions that changed in a 1995 build."),
    ] = False,
    new_only: Annotated[
        bool,
        typer.Option("--new", help="List functions genuinely new / rewritten in 1996."),
    ] = False,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit the full map JSON to stdout."),
    ] = False,
    output: Annotated[
        Path,
        typer.Option("--output", "-o", help="Where to write the map."),
    ] = DEFAULT_MAP_PATH,
    symbols: Annotated[
        Path,
        typer.Option("--symbols", "-s", help="symbols.json with the reference function table."),
    ] = REPO_ROOT / "data" / "out" / "symbols.json",
) -> None:
    """Map every debug-build function name into the two un-symbolled 1995
    PS.EXE builds, and persist it to ``data/out/crossbuild-map.json``.

    The 1995 release builds carry no ``-d1`` debug info; this transfers
    names from the 1996-04 debug build via ``version_match`` (TU-order
    module interpolation) and buckets each function per build as
    exact / near / differs / absent.

    Examples::

        c2 crossbuild-map                 # build (or reuse) + print summary
        c2 crossbuild-map --rebuild       # force regeneration
        c2 crossbuild-map -f move_army    # one function's per-build status
        c2 crossbuild-map --differs       # functions that evolved by 1995
        c2 crossbuild-map --json > map.json
    """
    # Query mode reuses the persisted map if present and fresh enough.
    if function and not rebuild and output.exists():
        rec = crossbuild_status(function, output)
        if rec is None:
            typer.echo(f"{function}: not found in map ({output})")
            raise typer.Exit(1)
        _print_function(rec, load_crossbuild_map(output))
        return

    needs_build = rebuild or not output.exists()
    if needs_build:
        data = build_map(symbols=symbols)
        write_map(data, output)
        # refresh loader cache
        _CACHE.pop(str(output), None)
    else:
        data = load_crossbuild_map(output)

    assert data is not None

    if json_out:
        clean = {k: v for k, v in data.items() if not k.startswith("_")}
        typer.echo(json.dumps(clean, indent=1))
        return

    if function:
        rec = data["_by_name"].get(function) if "_by_name" in data else None
        if rec is None:
            rec = next((r for r in data["functions"] if r["function"] == function), None)
        if rec is None:
            typer.echo(f"{function}: not found in map")
            raise typer.Exit(1)
        _print_function(rec, data)
        return

    if differs_only:
        _print_differs(data)
        return

    if new_only:
        _print_new(data)
        return

    _print_summary(data, output)


def _print_summary(data: dict, output: Path) -> None:
    ref = data["reference"]
    typer.echo(f"cross-build map: {output}")
    typer.echo(f"  reference: {ref['id']} ({ref['date']})  {ref['functions']} functions")
    typer.echo("")
    hdr = f"  {'build':14s} {'date':11s} {'anchored':>8s} {'exact':>7s} {'near':>6s} {'differs':>8s} {'absent':>7s}"
    typer.echo(hdr)
    typer.echo("  " + "-" * (len(hdr) - 2))
    total = ref["functions"]
    for b in data["builds"]:
        if b["role"] == "reference":
            continue
        s = data["summary"][b["id"]]
        pct = 100 * s["anchored"] / total if total else 0
        typer.echo(
            f"  {b['id']:14s} {b['date']:11s} {s['anchored']:>8d} "
            f"{s['exact']:>7d} {s['near']:>6d} {s['differs']:>8d} {s['absent']:>7d}"
            f"   ({pct:.1f}% anchored)"
        )
    # Semantic breakdown (what kind of change), if annotated.
    if any("semantic" in data["summary"][b["id"]]
           for b in data["builds"] if b["role"] != "reference"):
        typer.echo("")
        typer.echo("  semantic (what kind of change vs 1996 debug build):")
        typer.echo("    changed-but-same-work | extended | reworked | trimmed   (body anchored, callees compared)")
        typer.echo("    new-feature | restructured | library                     (absent: classified by module)")
        for b in data["builds"]:
            if b["role"] == "reference":
                continue
            sem = data["summary"][b["id"]].get("semantic", {})
            order = ["same-work", "extended", "reworked", "trimmed",
                     "new-feature", "restructured", "library"]
            parts = [f"{k}={sem[k]}" for k in order if k in sem]
            typer.echo(f"    {b['id']:14s} {'  '.join(parts)}")


def _print_function(rec: dict, data: Optional[dict]) -> None:
    typer.echo(f"{rec['function']}   ref {rec['ref_addr_hex']}  size {rec['ref_size']}")
    builds = data["builds"] if data else []
    bmeta = {b["id"]: b for b in builds}
    for bid, info in rec["builds"].items():
        date = bmeta.get(bid, {}).get("date", "")
        st = info.get("status")
        extra = ""
        if st in ("near", "differs"):
            extra = f"  diff={info.get('diff_bytes')}b  off={info.get('cand_off_hex')}  via {info.get('method')}"
        elif st == "exact":
            extra = f"  off={info.get('cand_off_hex')}  via {info.get('method')}"
        typer.echo(f"  {bid:14s} {date:11s} {st}{extra}")
        sem = rec.get("semantic", {}).get(bid)
        if sem:
            line = f"      ↳ {sem['class']}"
            if sem.get("added_callees"):
                line += f"  +callees: {', '.join(sem['added_callees'])}"
            if sem.get("dropped_callees"):
                line += f"  -callees: {', '.join(sem['dropped_callees'])}"
            if "module_anchor_pct" in sem:
                line += f"  (module {sem['module_anchor_pct']}% anchored in 1995)"
            typer.echo(line)


def _print_differs(data: dict) -> None:
    rel_ids = [b["id"] for b in data["builds"] if b["role"] != "reference"]
    rows = []
    for rec in data["functions"]:
        sts = {bid: rec["builds"].get(bid, {}).get("status") for bid in rel_ids}
        if any(s in ("near", "differs") for s in sts.values()):
            rows.append((rec, sts))
    typer.echo(f"{len(rows)} functions changed in at least one 1995 build:\n")
    for rec, sts in rows:
        flag = "  ".join(
            f"{bid}={sts[bid]}({rec['builds'].get(bid, {}).get('diff_bytes', '?')}b)"
            if sts[bid] in ("near", "differs") else f"{bid}={sts[bid]}"
            for bid in rel_ids
        )
        sem = rec.get("semantic", {})
        cls = next((sem[bid].get("class") for bid in rel_ids if bid in sem), "")
        typer.echo(f"  {rec['function']:40s} [{cls:10s}] {flag}")


def _print_new(data: dict) -> None:
    """List functions that are genuinely new or rewritten in the 1996
    build (grouped by semantic class), answering 'same work or new?'."""
    rel_ids = [b["id"] for b in data["builds"] if b["role"] != "reference"]
    groups: dict[str, list[tuple[str, str]]] = {
        "new-feature": [], "restructured": [], "extended": [],
        "reworked": [], "library": [],
    }
    for rec in data["functions"]:
        sem = rec.get("semantic", {})
        cls = next((sem[bid].get("class") for bid in rel_ids if bid in sem), None)
        if cls in groups:
            mod = next((sem[bid].get("module", "") for bid in rel_ids if bid in sem), "")
            extra = mod
            added = next((sem[bid].get("added_callees", []) for bid in rel_ids if bid in sem), [])
            if added:
                extra = "+" + ", ".join(sorted(set(added))[:4])
            groups[cls].append((rec["function"], extra))
    titles = {
        "new-feature":  "GENUINELY NEW in 1996 (feature area absent from 1995)",
        "restructured": "EXISTED but REWRITTEN in 1996 (body unrecognizable in 1995)",
        "extended":     "EXTENDED in 1996 (anchored, but new callees added)",
        "reworked":     "REWORKED in 1996 (callee set diverges)",
        "library":      "LIBRARY (lib32 rewrite / CRT helper newly linked)",
    }
    for cls in ("new-feature", "restructured", "extended", "reworked", "library"):
        rows = groups[cls]
        if not rows:
            continue
        typer.echo(f"\n{titles[cls]}  ({len(rows)}):")
        for fn, extra in sorted(rows):
            typer.echo(f"  {fn:40s} {extra}")
