"""Byte-level engine for verifying the decomp source against CAESAR2.EXE.

The Windows analogue of the Watcom/PS.EXE path in
``c2.commands.decomp_verify``.  The DOS target is built by Watcom into one LE
executable and compared against ``PS.EXE``; the Windows target is built by
**MSVC 4.0 /Od** (the proven CAESAR2.EXE toolchain — see
``docs/windows-builds-fingerprint.md``) *per translation unit* into COFF
objects, and each function's bytes are compared against ``CAESAR2.EXE``.

Pipeline (mirrors the DOS one, fixup-masking and all)::

    compile TU (msvc-4.00-wibo)  ->  COFF .obj
      -> parse the symbol table for each function's .text range
      -> mask its DIR32/REL32 relocation slots (link-patched bytes)
      -> locate it in CAESAR2.EXE (func-map.json win_va, or a // WIN: annotation,
         or a map-independent masked search across .text)
      -> compare (raw byte diff = the oracle; structural diff = the workable
         figure, since /Od stack-slot shuffling makes raw byte-diff noisy).

A masked search HIT anywhere in ``.text`` *is* a byte-exact certificate
(map-independent), so a stale/approximate ``func-map`` entry never produces a
false "diff".

See ``docs/windows-dual-target-feasibility.md`` for the why.
"""
from __future__ import annotations

import json
import struct
import subprocess
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import capstone

# ── Paths & toolchain ─────────────────────────────────────────────────────────
_REPO = Path(__file__).resolve().parent.parent
WIN_EXE = _REPO / "data/windows-builds/named/caesar2_A_1044480.exe"
FUNC_MAP = _REPO / "data/windows-builds/func-map.json"
DECOMP = _REPO / "decomp"
SRC_DIR = DECOMP / "src"
OBJ_DIR = DECOMP / "_objs"          # gitignored scratch for transient .obj

# The proven CAESAR2.EXE build config (data/windows-builds/ghidra-recreate.md).
MSVC_IMAGE = "localhost/msvc-4.00-wibo"
MSVC_FLAGS = ["/nologo", "/c", "/Od", "/Zp1", "/I", "include",
              "/FIc2_funcs.h", "/D__pascal=", "/D__far="]

_CS = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
_CS.detail = True   # disp_offset/disp_size for reloc-in-displacement detection

# COFF relocation types that patch 4 bytes at link time.
_IMAGE_REL_I386_DIR32 = 6
_IMAGE_REL_I386_REL32 = 20


# ── CAESAR2.EXE (.text) ───────────────────────────────────────────────────────
@dataclass(frozen=True)
class WinImage:
    data: bytes
    text: bytes
    text_va0: int          # absolute VA of .text[0]
    image_base: int

    def func_bytes(self, win_va: int, n: int) -> bytes:
        """``n`` bytes of CAESAR2.EXE starting at absolute VA ``win_va``."""
        off = win_va - self.text_va0
        if off < 0 or off + n > len(self.text):
            return b""
        return self.text[off : off + n]


@lru_cache(maxsize=1)
def load_win_image(path: Path = WIN_EXE) -> WinImage:
    d = path.read_bytes()
    e = struct.unpack_from("<I", d, 0x3C)[0]
    coff = e + 4
    nsec = struct.unpack_from("<H", d, coff + 2)[0]
    optsz = struct.unpack_from("<H", d, coff + 16)[0]
    image_base = struct.unpack_from("<I", d, coff + 20 + 28)[0]
    secoff = coff + 20 + optsz
    for i in range(nsec):
        b = secoff + i * 40
        nm = d[b : b + 8].rstrip(b"\0")
        vsize, vaddr, rawsz, rawptr = struct.unpack_from("<IIII", d, b + 8)
        if nm == b".text":
            text = d[rawptr : rawptr + rawsz]
            return WinImage(d, text, image_base + vaddr, image_base)
    raise RuntimeError(f"no .text section in {path}")


# ── func-map.json (ps_name -> win_va) ─────────────────────────────────────────
@dataclass(frozen=True)
class WinMapEntry:
    win_va: int
    confidence: str
    src: str


@lru_cache(maxsize=1)
def load_func_map(path: Path = FUNC_MAP) -> dict[str, WinMapEntry]:
    rows = json.loads(path.read_text())
    out: dict[str, WinMapEntry] = {}
    for r in rows:
        out[r["ps_name"]] = WinMapEntry(
            int(r["win_va"], 16), r.get("confidence", "?"), r.get("src", ""))
    return out


# ── // WIN: 0xADDR source annotations (override the map) ───────────────────────
@lru_cache(maxsize=256)
def win_annotations(tu: str) -> dict[str, int]:
    """``{function_name: win_va}`` for any ``// WIN: 0xADDR`` annotation that
    immediately precedes a definition in ``decomp/src/<tu>.c``.

    Mirrors the ``// FUNCTION: C2 0xADDR`` convention on the DOS side; lets the
    Windows address live in-tree and override / extend ``func-map.json``.
    """
    import re

    p = SRC_DIR / f"{tu}.c"
    if not p.exists():
        return {}
    lines = p.read_text(errors="replace").splitlines()
    win_re = re.compile(r"^\s*//\s*WIN:\s*(0x[0-9a-fA-F]+)")
    def_re = re.compile(r"^[A-Za-z_].*\b([A-Za-z_]\w*)\s*\(")
    out: dict[str, int] = {}
    pending: Optional[int] = None
    for ln in lines:
        m = win_re.match(ln)
        if m:
            pending = int(m.group(1), 16)
            continue
        if pending is not None:
            d = def_re.match(ln)
            if d:
                out[d.group(1)] = pending
            if ln.strip() and not ln.lstrip().startswith("//"):
                pending = None
    return out


def win_va_for(name: str, tu: Optional[str] = None) -> Optional[tuple[int, str]]:
    """Resolve a function's CAESAR2.EXE VA: ``// WIN:`` annotation first, then
    ``func-map.json``.  Returns ``(win_va, confidence)`` or ``None``."""
    if tu:
        ann = win_annotations(tu).get(name)
        if ann is not None:
            return ann, "annotation"
    ent = load_func_map().get(name)
    if ent is not None:
        return ent.win_va, ent.confidence
    return None


# Confidence tiers that are placeholders / not a real CAESAR2.EXE location.
_WIN_SENTINELS = {0x401384}


def win_hint(name: str, tu: Optional[str] = None) -> dict:
    """Cheap (no-compile) CAESAR2.EXE mapping hint for a function -- a pure
    func-map / ``// WIN:`` lookup, for surfacing in worklist / dossier /
    decomp-verify.  Returns ``{available, win_va, confidence}``; ``available``
    is False when there is no mapping (or only the 0x401384 placeholder).
    A True hint means ``c2 win-verify <fn>`` / ``c2 win-decompile <fn>`` (the
    second byte oracle + MSVC /Od source view) are usable for this function.
    """
    res = win_va_for(name, tu)
    if res is None or res[0] in _WIN_SENTINELS:
        return {"available": False, "win_va": None, "confidence": None}
    return {"available": True, "win_va": f"0x{res[0]:08x}", "confidence": res[1]}


# ── COFF object parsing ───────────────────────────────────────────────────────
@dataclass
class CompiledTU:
    tu: str
    text: bytes                                  # .text section bytes
    funcs: list[tuple[str, int, int]]            # (name, start, end) sorted
    reloc: set[int]                              # patched .text byte offsets
    errors: list[str] = field(default_factory=list)

    def func_code(self, name: str) -> Optional[tuple[bytes, set[int]]]:
        for n, s, e in self.funcs:
            if n == name:
                mask = {i - s for i in self.reloc if s <= i < e}
                return self.text[s:e], mask
        return None


def _parse_coff(obj: bytes) -> tuple[bytes, list[tuple[str, int, int]], set[int]]:
    nsec = struct.unpack_from("<H", obj, 2)[0]
    symptr, nsym = struct.unpack_from("<II", obj, 8)
    optsz = struct.unpack_from("<H", obj, 16)[0]
    so = 20 + optsz
    text = b""
    text_idx = None
    relptr = nrel = 0
    for i in range(nsec):
        b = so + i * 40
        nm = obj[b : b + 8].rstrip(b"\0")
        _vs, _va, rawsz, rawptr, rp = struct.unpack_from("<IIIII", obj, b + 8)
        nr = struct.unpack_from("<H", obj, b + 32)[0]
        if nm == b".text":
            text = obj[rawptr : rawptr + rawsz]
            text_idx, relptr, nrel = i + 1, rp, nr
            break
    if text_idx is None:
        return b"", [], set()

    reloc: set[int] = set()
    for r in range(nrel):
        va, _si, ty = struct.unpack_from("<IIH", obj, relptr + r * 10)
        if ty in (_IMAGE_REL_I386_DIR32, _IMAGE_REL_I386_REL32):
            reloc.update(range(va, va + 4))

    strtab = symptr + nsym * 18

    def symname(raw: bytes) -> str:
        if raw[:4] == b"\0\0\0\0":
            off = struct.unpack_from("<I", raw, 4)[0]
            end = obj.find(b"\0", strtab + off)
            return obj[strtab + off : end].decode("latin1")
        return raw.rstrip(b"\0").decode("latin1")

    fsyms: list[tuple[int, str]] = []
    i = 0
    while i < nsym:
        b = symptr + i * 18
        value, secnum, typ, sclass, naux = struct.unpack_from("<IhHBB", obj, b + 8)
        # Function symbols: derived-type DT_FCN (high nibble 2), defined in .text.
        if secnum == text_idx and sclass == 2 and (typ & 0x20):
            fsyms.append((value, symname(obj[b : b + 8]).lstrip("_")))
        i += 1 + naux

    fsyms.sort()
    funcs: list[tuple[str, int, int]] = []
    for k, (val, name) in enumerate(fsyms):
        end = fsyms[k + 1][0] if k + 1 < len(fsyms) else len(text)
        funcs.append((name, val, end))
    return text, funcs, reloc


def _run_msvc(tu: str, *, image: str = MSVC_IMAGE) -> tuple[Optional[bytes], list[str]]:
    """Compile ``decomp/src/<tu>.c`` with MSVC 4.0 /Od -> COFF .obj bytes."""
    OBJ_DIR.mkdir(exist_ok=True)
    objname = f"_wv_{tu}_{uuid.uuid4().hex[:8]}.obj"
    objpath = OBJ_DIR / objname
    cmd = [
        "podman", "run", "--rm", "-v", f"{DECOMP}:/src", image, "cl.exe",
        *MSVC_FLAGS, f"/Fo_objs/{objname}", f"src/{tu}.c",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return None, [str(exc)]
    if not objpath.exists():
        errs = [l for l in (r.stdout + r.stderr).splitlines()
                if "error" in l.lower() or "fatal" in l.lower()]
        return None, errs or ["compile produced no object"]
    data = objpath.read_bytes()
    objpath.unlink(missing_ok=True)
    return data, []


_TU_CACHE: dict[str, CompiledTU] = {}


def compile_tu(tu: str, *, cache: bool = True) -> CompiledTU:
    """Compile a TU (memoised within a process) into a ``CompiledTU``."""
    if cache and tu in _TU_CACHE:
        return _TU_CACHE[tu]
    obj, errs = _run_msvc(tu)
    if obj is None:
        ctu = CompiledTU(tu, b"", [], set(), errs)
    else:
        text, funcs, reloc = _parse_coff(obj)
        ctu = CompiledTU(tu, text, funcs, reloc)
    if cache:
        _TU_CACHE[tu] = ctu
    return ctu


# ── Masked search / comparison ────────────────────────────────────────────────
def masked_find(haystack: bytes, needle: bytes, mask: set[int]) -> list[int]:
    """Offsets in ``haystack`` where ``needle`` matches with ``mask`` bytes
    treated as wildcards.  Anchored on the longest unmasked run."""
    n = len(needle)
    best_start = best_len = run = run_start = 0
    for i in range(n):
        if i not in mask:
            if run == 0:
                run_start = i
            run += 1
            if run > best_len:
                best_start, best_len = run_start, run
        else:
            run = 0
    if best_len == 0:
        return []
    anchor = needle[best_start : best_start + best_len]
    hits: list[int] = []
    pos = haystack.find(anchor)
    while pos != -1:
        s = pos - best_start
        if 0 <= s and s + n <= len(haystack) and all(
            (i in mask) or haystack[s + i] == needle[i] for i in range(n)
        ):
            hits.append(s)
        pos = haystack.find(anchor, pos + 1)
    return hits


def _norm_op(op: str) -> str:
    """Operand string with absolute addresses + immediates wildcarded.

    Keeps mnemonic/register/memory *shape* (incl. ebp/esp displacement
    presence) so the structural compare is insensitive to which global a
    DIR32 points at or which exact constant an immediate holds -- the
    link-/layout-variant bytes -- while still distinguishing real opcode and
    addressing-mode divergence."""
    import re
    op = re.sub(r"0x[0-9a-f]+", "K", op)
    op = re.sub(r"\b\d+\b", "K", op)
    return op


def disasm_norm(code: bytes, mask: Optional[set[int]] = None):
    """``[(hexbytes, asm_text, norm_key)]`` for a code blob.

    Reloc-in-displacement canonicalisation: in the unlinked .obj a DIR32
    displacement is a ZERO placeholder, so capstone prints ``[eax]`` where
    the linked exe shows ``[eax + 0x50b930]`` — a false "struct" diff.
    When the mask overlaps the displacement field and the placeholder is
    zero, normalise the memory operand to the ``[… + K]`` shape."""
    import re
    out = []
    for ins in _CS.disasm(code, 0):
        off = ins.address
        raw = bytes(ins.bytes)
        hx = "".join(".." if (mask and (off + k) in mask) else f"{b:02x}"
                     for k, b in enumerate(raw))
        asm = f"{ins.mnemonic} {ins.op_str}".rstrip()
        key = f"{ins.mnemonic} {_norm_op(ins.op_str)}"
        if mask:
            try:
                do, ds = ins.disp_offset, ins.disp_size
            except Exception:  # noqa: BLE001
                do, ds = 0, 0
            if do and ds and ins.disp == 0 \
                    and any((off + do + k) in mask for k in range(ds)):
                # zero reloc placeholder in the displacement: give the
                # memory operand its linked-exe `+ K` shape
                key = re.sub(r"\[([a-z0-9* ]+)\]", r"[\1 + K]", key)
        out.append((hx, asm, key))
    return out


def _struct_distance(a_keys: list[str], b_keys: list[str]) -> int:
    """Instruction-level edit distance under optimal alignment (difflib).

    Counts how many instructions truly diverge, NOT positional shifts -- so
    an inserted/removed instruction (e.g. an extra local's store) costs 1,
    not 'everything after it'."""
    import difflib
    sm = difflib.SequenceMatcher(a=a_keys, b=b_keys, autojunk=False)
    matched = sum(blk.size for blk in sm.get_matching_blocks())
    return max(len(a_keys), len(b_keys)) - matched


@dataclass
class FuncVerdict:
    name: str
    tu: str
    status: str                       # "exact" | "diff" | "nomap" | "absent"
    size: int = 0
    byte_diff: int = 0                # raw masked byte diff at located va
    struct_diff: int = 0             # mnemonic+normed-operand mismatches
    insn_total: int = 0
    win_va: Optional[int] = None
    confidence: str = ""
    located_va: Optional[int] = None  # where the bytes actually matched/aligned


def verify_func(name: str, tu: str, *, win: Optional[WinImage] = None,
                ctu: Optional[CompiledTU] = None) -> FuncVerdict:
    """Verdict for one decompiled function vs CAESAR2.EXE."""
    win = win or load_win_image()
    ctu = ctu or compile_tu(tu)
    fc = ctu.func_code(name)
    if fc is None:
        return FuncVerdict(name, tu, "absent")
    code, mask = fc
    n = len(code)
    resolved = win_va_for(name, tu)
    win_va = resolved[0] if resolved else None
    conf = resolved[1] if resolved else ""

    # Authoritative exactness: a masked hit ANYWHERE in .text (map-independent).
    hits = masked_find(win.text, code, mask)
    if hits:
        located = win.text_va0 + hits[0]
        return FuncVerdict(name, tu, "exact", n, 0, 0, 0, win_va, conf, located)

    if win_va is None:
        return FuncVerdict(name, tu, "nomap", n, win_va=None, confidence=conf)

    # Diff: align at the mapped va and count raw + structural divergence.
    wbytes = win.func_bytes(win_va, n)
    byte_diff = sum(1 for i in range(min(n, len(wbytes)))
                    if i not in mask and code[i] != wbytes[i]) + abs(n - len(wbytes))
    ours = disasm_norm(code, mask)
    theirs = disasm_norm(wbytes)
    struct_diff = _struct_distance([r[2] for r in ours], [r[2] for r in theirs])
    return FuncVerdict(name, tu, "diff", n, byte_diff, struct_diff, len(ours),
                       win_va, conf, win_va)


def aligned_diff(v: "FuncVerdict") -> list[dict]:
    """Aligned MSVC-of-our-source vs CAESAR2.EXE rows for a diff verdict.

    ``[{kind, ours, theirs}]`` where kind is ``equal`` | ``struct`` (a real
    shape divergence — inserted/removed/different-mnemonic) | ``slot`` (same
    instruction shape, only a displacement/immediate differs — the /Od
    stack-slot / global / immediate noise).  Shared by the CLI view and the
    pi tool.
    """
    import difflib

    ctu = compile_tu(v.tu)
    fc = ctu.func_code(v.name)
    if fc is None or v.win_va is None:
        return []
    code, mask = fc
    win = load_win_image()
    wbytes = win.func_bytes(v.win_va, len(code))
    ours = disasm_norm(code, mask)
    theirs = disasm_norm(wbytes)
    sm = difflib.SequenceMatcher(a=[r[2] for r in ours], b=[r[2] for r in theirs],
                                 autojunk=False)
    rows: list[dict] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                o, t = ours[i1 + k], theirs[j1 + k]
                rows.append({"kind": "slot" if o[1] != t[1] else "equal",
                             "ours": o[1], "theirs": t[1]})
        else:
            for k in range(max(i2 - i1, j2 - j1)):
                o = ours[i1 + k] if i1 + k < i2 else None
                t = theirs[j1 + k] if j1 + k < j2 else None
                rows.append({"kind": "struct",
                             "ours": o[1] if o else "", "theirs": t[1] if t else ""})
    return rows


def tu_of(name: str) -> Optional[str]:
    """The source TU basename a function's DEFINITION lives in."""
    return _func_tu_index().get(name)


@lru_cache(maxsize=1)
def _func_tu_index() -> dict[str, str]:
    """Map every function name to its TU by scanning for column-0 definitions.

    In this codebase a function *definition* starts at column 0 as
    ``<type> name(...)`` and is not a prototype (no trailing ``;``); calls and
    nested code are indented.  That is a reliable, build-free discriminator.
    """
    import re
    def_re = re.compile(r"^[A-Za-z_][A-Za-z0-9_ \t\*]*?\b([A-Za-z_]\w*)\s*\(")
    idx: dict[str, str] = {}
    for p in sorted(SRC_DIR.glob("*.c")):
        for ln in p.read_text(errors="replace").splitlines():
            if not ln[:1].isalpha() and ln[:1] != "_":
                continue                      # not a column-0 definition
            if ln.rstrip().endswith(";"):
                continue                      # prototype / extern decl
            if any(k in ln.split("(")[0] for k in ("return", "typedef", "=")):
                continue
            m = def_re.match(ln)
            if m:
                idx.setdefault(m.group(1), p.stem)
    return idx


def decompiled_funcs(tu: str) -> list[str]:
    """Functions with a real body (compiled symbols) in a TU."""
    return [n for n, _s, _e in compile_tu(tu).funcs]


# ── Frame-slot census (the W2 witness; docs/root-cause-survey-2026-07-02.md) ──
#
# MSVC 4.0 /Od gives every named source local a distinct ``[ebp-N]`` frame
# slot.  Comparing CAESAR2.EXE's slot set against our own MSVC compile of the
# same function is therefore a census of the ORIGINAL's named-local set —
# the input that decides Watcom conflict membership / savings / spill sets.
# Reliability is gated by the mapping quality Q (the win func-map is fuzzy):
# on the PS-byte-exact corpus the slot-count census agrees 78.5 %; mismatches
# concentrate in low-Q mappings and genuine port drift.

_SLOT_RE = __import__("re").compile(r"\[ebp - (0x[0-9a-f]+|\d+)\]")
_SUB_RE = __import__("re").compile(r"^sub esp, (0x[0-9a-f]+|\d+)$")


def _slot_census(insns: list[str]) -> tuple[Optional[int], dict[int, dict]]:
    """``(frame_size, {disp: {widths, n_uses, first_use_asm}})`` for one side."""
    frame: Optional[int] = None
    slots: dict[int, dict] = {}
    for i, asm in enumerate(insns):
        if frame is None and i < 6:
            m = _SUB_RE.match(asm)
            if m:
                frame = int(m.group(1), 0)
        for m in _SLOT_RE.finditer(asm):
            disp = int(m.group(1), 0)
            width = "d"
            if "byte ptr" in asm:
                width = "b"
            elif "word ptr" in asm and "dword" not in asm:
                width = "w"
            rec = slots.setdefault(disp, {"widths": set(), "n_uses": 0, "first": asm})
            rec["widths"].add(width)
            rec["n_uses"] += 1
    return frame, slots


@dataclass
class CensusVerdict:
    name: str
    tu: str
    ok: bool                       # census computed at all
    quality: float = 0.0           # aligned-instruction match ratio (0..1)
    gate: str = ""                 # "usable" | "caution" | "mapping-suspect"
    frame_ours: Optional[int] = None
    frame_theirs: Optional[int] = None
    slots_ours: dict = field(default_factory=dict)
    slots_theirs: dict = field(default_factory=dict)
    delta: int = 0                 # len(theirs) - len(ours)
    note: str = ""


def census_func(name: str, tu: Optional[str] = None, *,
                win: Optional[WinImage] = None,
                ctu: Optional[CompiledTU] = None) -> CensusVerdict:
    """Frame-slot census of one function: our MSVC /Od build vs CAESAR2.EXE.

    ``delta > 0`` ⇒ the original has MORE named locals than our source
    (missing locals — the §13 named-local class); ``delta < 0`` ⇒ our source
    INVENTED locals the original lacks.  Only trust ``gate == "usable"``.
    """
    import difflib

    tu = tu or tu_of(name)
    if tu is None:
        return CensusVerdict(name, "?", False, note="unknown TU")
    win = win or load_win_image()
    ctu = ctu or compile_tu(tu)
    if ctu.errors:
        return CensusVerdict(name, tu, False,
                             note=f"TU fails MSVC compile: {ctu.errors[0]}")
    fc = ctu.func_code(name)
    if fc is None:
        return CensusVerdict(name, tu, False, note="no MSVC body")
    code, mask = fc
    resolved = win_va_for(name, tu)
    if not resolved:
        return CensusVerdict(name, tu, False, note="no win mapping")
    wbytes = win.func_bytes(resolved[0], len(code))
    ours = disasm_norm(code, mask)
    theirs = disasm_norm(wbytes)
    sm = difflib.SequenceMatcher(a=[r[2] for r in ours], b=[r[2] for r in theirs],
                                 autojunk=False)
    matched = sum(b.size for b in sm.get_matching_blocks())
    q = matched / max(len(ours), 1)
    gate = "usable" if q >= 0.85 else ("caution" if q >= 0.7 else "mapping-suspect")
    fo, so = _slot_census([r[1] for r in ours])
    ft, st = _slot_census([r[1] for r in theirs])
    return CensusVerdict(name, tu, True, q, gate, fo, ft, so, st,
                         len(st) - len(so))


# ── Rule 158: folded always-true-guard probe ─────────────────────────────────
# A source guard like ``kind >= 0 &&`` (kind unsigned) emits ZERO bytes under
# Watcom (constant-folded after flow-graph construction, where it still roots
# a CSE partition — docs/watcom-codegen-patterns.md Rule 158) but is LITERAL
# under MSVC /Od.  So the CAESAR2.EXE oracle shows it as a one-sided
# instruction run shaped like a zero-compare guard:
#
#     xor eax, eax              (uchar zext, optional)
#     mov al, byte ptr [ebp-X]
#     test eax, eax             (or cmp reg, 0)
#     jl <skip>                 (signed zero-relative jcc)
#
# ``theirs``-only run  ⇒ OUR source is MISSING the guard (add it).
# ``ours``-only run    ⇒ our source INVENTED a guard the original lacks.
#
# Ground truth: evolve_land_value (evolver.c) — a single ``kind >= 0 &&``
# token was the whole 247-byte PS diff; found ONLY via this witness.

_GUARD_JCC = ("jl", "jge", "jle", "jg", "js", "jns")


@dataclass
class GuardHit:
    """One suspected folded-guard site from the aligned win diff."""

    side: str          # "theirs" = CAESAR2-only (we're missing the guard)
    kind: str          # "zext0" (uchar zext + zero-test) | "cmp0"
    insns: list[str]   # the one-sided run
    after: list[str]   # next shared/CAESAR2 insns (the guarded condition)
    row: int           # index into aligned_diff rows (locality anchor)


def _guard_run_kind(insns: list[str]) -> Optional[str]:
    """Classify a one-sided run as a PURE zero-compare guard, else None.

    Shape: [optional zext/load insns] + zero-test + signed jcc, with the
    zero-test IMMEDIATELY feeding the final jcc and nothing but loads /
    register-zeroing in between (any arithmetic/store/call disqualifies —
    that's a genuinely missing/extra statement, not a folded guard).
    """
    import re as _re
    if not 2 <= len(insns) <= 6:
        return None
    last = insns[-1].split()[0] if insns[-1] else ""
    if last not in _GUARD_JCC:
        return None
    zt = insns[-2]
    m = _re.match(r"test (\w+), (\w+)$", zt)
    is_zero_test = bool(m and m.group(1) == m.group(2)) \
        or bool(_re.match(r"cmp \w+, 0$", zt)) \
        or bool(_re.match(r"cmp (dword|word|byte) ptr \[[^]]*\], 0$", zt))
    if not is_zero_test:
        return None
    # body (before the zero-test) may only be loads / register zeroing
    for t in insns[:-2]:
        if _re.match(r"xor (\w+), \1$", t):
            continue
        if _re.match(r"mov \w+, (byte |word |dword )?ptr \[", t) \
                or _re.match(r"mov \w+, \w+$", t) \
                or _re.match(r"movsx \w+, ", t) \
                or _re.match(r"movzx \w+, ", t):
            continue
        return None
    has_zext = any(_re.match(r"xor (\w+), \1$", t) for t in insns) and \
        any(_re.match(r"mov [a-d]l, byte ptr", t) for t in insns)
    return "zext0" if has_zext else "cmp0"


def guard_hits(v: "FuncVerdict") -> list[GuardHit]:
    """Scan the aligned win diff for folded-guard fingerprints (Rule 158)."""
    if v.status != "diff":
        return []
    rows = aligned_diff(v)
    hits: list[GuardHit] = []
    i = 0
    while i < len(rows):
        r = rows[i]
        side = None
        if r["kind"] == "struct" and r["theirs"] and not r["ours"]:
            side = "theirs"
        elif r["kind"] == "struct" and r["ours"] and not r["theirs"]:
            side = "ours"
        if side is None:
            i += 1
            continue
        j = i
        key = "theirs" if side == "theirs" else "ours"
        other = "ours" if side == "theirs" else "theirs"
        run: list[str] = []
        while j < len(rows) and rows[j]["kind"] == "struct" \
                and rows[j][key] and not rows[j][other]:
            run.append(rows[j][key])
            j += 1
        kind = _guard_run_kind(run)
        if kind:
            after = [rows[k]["theirs"] or rows[k]["ours"]
                     for k in range(j, min(j + 2, len(rows)))]
            hits.append(GuardHit(side, kind, run, after, i))
        i = j
    return hits


def guard_probe(name: str, tu: Optional[str] = None) -> dict:
    """Rule 158 probe for one function.  ``{available, hits:[…], note}``.

    ``hits`` entries: {side, kind, insns, after}.  ``side == "theirs"`` ⇒
    add the folded always-true guard (``x >= 0 &&`` on the matching
    condition — read ``after`` for the guarded compare); ``side == "ours"``
    ⇒ delete the guard our source invented.
    """
    tu = tu or tu_of(name)
    if tu is None:
        return {"available": False, "note": "unknown TU"}
    try:
        v = verify_func(name, tu)
    except Exception as exc:  # noqa: BLE001
        return {"available": False, "note": f"win verify failed: {exc}"}
    if v.status in ("absent", "nomap"):
        return {"available": False, "note": f"win status: {v.status}"}
    if v.status == "exact":
        return {"available": True, "hits": [], "note": "win-exact"}
    hits = guard_hits(v)
    return {"available": True,
            "hits": [{"side": h.side, "kind": h.kind, "insns": h.insns,
                      "after": h.after} for h in hits],
            "note": f"{len(hits)} suspected folded-guard site(s)"}
