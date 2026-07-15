"""Minimal OMF (Object Module Format) writer for 32-bit flat Watcom objects.

This is a *byte-preserving delink* backend: it emits a relocatable OMF
``.obj`` that WLINK 10.0a accepts, carrying verbatim code/data bytes plus
a reconstructed relocation table.  It is deliberately small — it supports
exactly the record set a flat 32-bit Watcom object needs:

    THEADR  0x80   module name
    COMENT  0x88   (only the trivial ones Watcom emits)
    LNAMES  0x96   name table (segment / class / group names)
    SEGDEF32 0x99  32-bit segment definitions (USE32)
    GRPDEF  0x9A   the FLAT group
    PUBDEF  0x90 / PUBDEF32 0x91   public symbols
    EXTDEF  0x8C   external references
    LEDATA32 0xA1  enumerated data (the actual bytes)
    FIXUPP32 0x9D  relocations
    MODEND  0x8A   module end

Design notes (validated against a wasm-produced reference object):

  * Every fixup is an OFFSET32 (loc = 9).  Absolute references use
    segment-relative mode (M=1); PC-relative call/jmp use self-relative
    mode (M=0).
  * Frame is always "determined by target" (frame method 5) — correct for
    flat model.
  * The additive displacement is folded into the *location content* (the
    bytes already in the LEDATA), and the FIXUPP uses a no-displacement
    target method (4 = segment index, 6 = external index).  This mirrors
    exactly what Watcom's own assembler emits.
  * LEDATA is chunked to <= 1024 bytes; the 10-bit FIXUPP data-record
    offset is relative to each chunk, and chunk boundaries never split a
    4-byte fixup field.

The OMF record checksum byte is emitted as 0 (the spec-sanctioned
"ignore" value; WLINK accepts it).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field


# ── record type constants ────────────────────────────────────────────────
THEADR = 0x80
COMENT = 0x88
EXTDEF = 0x8C
PUBDEF = 0x90
PUBDEF32 = 0x91
LNAMES = 0x96
SEGDEF32 = 0x99
GRPDEF = 0x9A
FIXUPP32 = 0x9D
LEDATA32 = 0xA1
MODEND = 0x8A

# Fixup target/frame method encodings used here
_FRAME_TARGET = 5          # frame determined by target (flat model)
_TARG_SEG_NODISP = 4       # target = segment index, no displacement
_TARG_EXT_NODISP = 6       # target = external index, no displacement

_MAX_LEDATA = 1024         # data bytes per LEDATA (10-bit FIXUPP dataoff)


def _index(i: int) -> bytes:
    """OMF index: 1 byte if < 128, else 2 bytes big-endian with hi bit set."""
    if i < 0x80:
        return bytes([i])
    return bytes([0x80 | (i >> 8), i & 0xFF])


def _record(rtype: int, body: bytes) -> bytes:
    """Wrap a record body with type, length and (zero) checksum."""
    length = len(body) + 1  # + checksum byte
    return bytes([rtype]) + struct.pack("<H", length) + body + b"\x00"


# ── fixup model ──────────────────────────────────────────────────────────
@dataclass
class Fixup:
    """One relocation site within a segment.

    offset       byte offset of the 4-byte field within its segment
    self_rel     True for PC-relative (call/jmp rel32); False for absolute
    target_seg   segment index if this targets a segment (mutually excl.)
    target_ext   external index if this targets an external symbol
    """
    offset: int
    self_rel: bool
    target_seg: int | None = None
    target_ext: int | None = None


@dataclass
class Segment:
    name_idx: int
    class_idx: int
    seg_index: int
    data: bytearray = field(default_factory=bytearray)
    is_bss: bool = False
    bss_len: int = 0
    align: int = 1            # 1 = byte alignment
    fixups: list[Fixup] = field(default_factory=list)

    @property
    def length(self) -> int:
        return self.bss_len if self.is_bss else len(self.data)


# ── the builder ──────────────────────────────────────────────────────────
class OmfObject:
    def __init__(self, module_name: str):
        self.module_name = module_name
        self._names: list[str] = []
        self._name_idx: dict[str, int] = {}
        self.segments: list[Segment] = []
        self._publics: list[tuple[int, str, int]] = []  # (seg_idx, name, off)
        self._externs: list[str] = []
        self._ext_idx: dict[str, int] = {}
        self._groups: list[tuple[int, list[int]]] = []   # (name_idx, [seg_idx])
        self.lname(" ".rstrip())  # index 1 = null name ("")

    # -- name / segment / group / symbol registration --------------------
    def lname(self, name: str) -> int:
        if name in self._name_idx:
            return self._name_idx[name]
        self._names.append(name)
        idx = len(self._names)
        self._name_idx[name] = idx
        return idx

    def segment(self, name: str, class_name: str, *, is_bss: bool = False) -> Segment:
        seg = Segment(
            name_idx=self.lname(name),
            class_idx=self.lname(class_name),
            seg_index=len(self.segments) + 1,
            is_bss=is_bss,
        )
        self.segments.append(seg)
        return seg

    def group(self, name: str, seg_indices: list[int]) -> int:
        gidx = len(self._groups) + 1
        self._groups.append((self.lname(name), seg_indices))
        return gidx

    def public(self, seg: Segment, name: str, offset: int) -> None:
        self._publics.append((seg.seg_index, name, offset))

    def extern(self, name: str) -> int:
        if name in self._ext_idx:
            return self._ext_idx[name]
        self._externs.append(name)
        idx = len(self._externs)
        self._ext_idx[name] = idx
        return idx

    # -- serialisation ----------------------------------------------------
    def _emit_lnames(self) -> bytes:
        out = b""
        chunk = b""
        for n in self._names:
            enc = bytes([len(n)]) + n.encode("ascii")
            if len(chunk) + len(enc) > 1020:
                out += _record(LNAMES, chunk)
                chunk = b""
            chunk += enc
        out += _record(LNAMES, chunk)
        return out

    def _emit_segdefs(self) -> bytes:
        # OMF alignment codes: 1=byte 2=word 3=para(16) 4=page(256) 5=dword
        _ALIGN_CODE = {1: 1, 2: 2, 16: 3, 256: 4, 4: 5}
        out = b""
        for s in self.segments:
            # ACBP: A=align C=010 (public) B=0 P=1 (use32)
            acbp = (_ALIGN_CODE.get(s.align, 1) << 5) | 0x09
            body = bytes([acbp]) + struct.pack("<I", s.length)
            body += _index(s.name_idx) + _index(s.class_idx) + _index(1)  # overlay ""
            out += _record(SEGDEF32, body)
        return out

    def _emit_grpdefs(self) -> bytes:
        out = b""
        for name_idx, segs in self._groups:
            body = _index(name_idx)
            for si in segs:
                body += bytes([0xFF]) + _index(si)   # 0xFF = segment-index group member
            out += _record(GRPDEF, body)
        return out

    def _emit_extdefs(self) -> bytes:
        if not self._externs:
            return b""
        out = b""
        chunk = b""
        for n in self._externs:
            enc = bytes([len(n)]) + n.encode("ascii") + b"\x00"  # + type index 0
            if len(chunk) + len(enc) > 1020:
                out += _record(EXTDEF, chunk)
                chunk = b""
            chunk += enc
        out += _record(EXTDEF, chunk)
        return out

    def _emit_pubdefs(self) -> bytes:
        out = b""
        # group by base segment
        by_seg: dict[int, list[tuple[str, int]]] = {}
        for seg_idx, name, off in self._publics:
            by_seg.setdefault(seg_idx, []).append((name, off))
        for seg_idx, items in by_seg.items():
            body = _index(0) + _index(seg_idx)  # base group 0, base segment
            use32 = any(off >= 0x10000 for _, off in items)
            for name, off in items:
                enc = bytes([len(name)]) + name.encode("ascii")
                enc += struct.pack("<I", off) if use32 else struct.pack("<H", off)
                enc += b"\x00"  # type index
                body += enc
            out += _record(PUBDEF32 if use32 else PUBDEF, body)
        return out

    def _emit_ledata_fixupp(self, seg: Segment) -> bytes:
        if seg.is_bss or not seg.data:
            return b""
        out = b""
        data = bytes(seg.data)
        # Address order is needed only to choose safe LEDATA boundaries.
        # Keep the recovered insertion order for FIXUPP emission, inverted:
        # WLINK prepends loader fixups while consuming a FIXUPP chain, so
        # inverse input order recovers more of the original LE record order.
        fx = sorted(seg.fixups, key=lambda f: f.offset)
        pos = 0
        n = len(data)
        while pos < n:
            end = min(pos + _MAX_LEDATA, n)
            # never let a fixup's 4-byte field straddle the chunk end
            for f in fx:
                if f.offset < end and f.offset + 4 > end:
                    end = f.offset
            if end <= pos:  # a single fixup near start forced backoff to 0
                end = min(pos + _MAX_LEDATA, n)
            chunk = data[pos:end]
            ledata = _index(seg.seg_index) + struct.pack("<I", pos) + chunk
            out += _record(LEDATA32, ledata)
            # fixups within [pos,end)
            fixbody = b""
            for f in reversed(seg.fixups):
                if not (pos <= f.offset < end):
                    continue
                dataoff = f.offset - pos
                locat = 0x8000 | (0 if f.self_rel else 0x4000) | (9 << 10) | (dataoff & 0x3FF)
                fixbody += bytes([(locat >> 8) & 0xFF, locat & 0xFF])
                if f.target_seg is not None:
                    fixdata = (_FRAME_TARGET << 4) | _TARG_SEG_NODISP
                    fixbody += bytes([fixdata]) + _index(f.target_seg)
                else:
                    fixdata = (_FRAME_TARGET << 4) | _TARG_EXT_NODISP
                    fixbody += bytes([fixdata]) + _index(f.target_ext)
            if fixbody:
                out += _record(FIXUPP32, fixbody)
            pos = end
        return out

    def build(self) -> bytes:
        out = _record(THEADR, bytes([len(self.module_name)]) +
                      self.module_name.encode("ascii"))
        out += self._emit_lnames()
        out += self._emit_segdefs()
        out += self._emit_grpdefs()
        out += self._emit_extdefs()
        out += self._emit_pubdefs()
        for seg in self.segments:
            out += self._emit_ledata_fixupp(seg)
        # MODEND: module type byte 0 (non-main, no start address)
        out += _record(MODEND, b"\x00")
        return out
