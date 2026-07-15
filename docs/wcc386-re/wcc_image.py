#!/usr/bin/env python3
"""Crack the Watcom 10.0a ``wcc386.exe`` (Phar Lap TNT bound) flat image and
expose a single coordinate system for reverse-engineering the code generator.

Why this exists
---------------
``wcc386-10.0a.exe`` is an MS-DOS ``MZ`` stub + a tiny ~4 KB OS/2 ``LX``
bootstrap + a **headerless, uncompressed, flat 32-bit code/data image** that
the Phar Lap TNT extender memory-maps.  Off-the-shelf loaders (rizin's LX
loader, Ghidra's OS/2 loader) only see the 4 KB bootstrap and miss the entire
compiler.  This module parses the real payload and pins the load base so that
disassembly resolves calls and data references correctly.

Key facts (derived in this file, see ``selftest``):
  * The flat image is **uncompressed** (entropy ~6.0 everywhere).
  * ``virtual_address == file_offset + DELTA`` with ``DELTA = 0x6758``.
    -> code lives at file 0x1000..~0x6F000 (va 0x7758..~0x75758)
    -> read-only data + strings + globals at file ~0x6F000..EOF
  * Because relative ``call rel32`` cancels the base, the *file offset* of a
    call target is ``next_file_off + rel32`` regardless of DELTA -- so the
    file itself is a valid coordinate system for the call graph.

Usage:
    python wcc_image.py <wcc386-10.0a.exe>            # self-test + summary
    python wcc_image.py <exe> --regtables            # dump register tables
    python wcc_image.py <exe> --ghidra-base          # print Ghidra import base
"""
from __future__ import annotations
import struct, sys, re, math, argparse
from dataclasses import dataclass

DELTA = 0x6758            # virtual_address = file_offset + DELTA
CODE_LO, CODE_HI = 0x1000, 0x70000
DATA_LO = 0x6F000

# --- Watcom 386 hw_reg_set encoding (hw_reg_set is a single 32-bit word for the
#     1995 build: _0 = part0 | (part1 << 16); MMX/XMM bits were added later and
#     would shift this -- which is exactly why the 2003 OW V2 source layout does
#     NOT match the 10.0a binary).
def _rs(p0, p1=0):       # build a 32-bit register-set value
    return (p0 | (p1 << 16)) & 0xFFFFFFFF

REG = {
    "EAX": _rs(0x0003, 0x0100), "EDX": _rs(0x00C0, 0x0800),
    "ECX": _rs(0x0030, 0x0400), "EBX": _rs(0x000C, 0x0200),
    "ESI": _rs(0x0100, 0x1000), "EDI": _rs(0x0200, 0x2000),
    "EBP": _rs(0x0400, 0),      "ESP": _rs(0x0800, 0),
    "AX": _rs(0x0003), "DX": _rs(0x00C0), "CX": _rs(0x0030), "BX": _rs(0x000C),
    "AL": _rs(0x0002), "AH": _rs(0x0001), "BL": _rs(0x0008), "BH": _rs(0x0004),
    "CL": _rs(0x0020), "CH": _rs(0x0010), "DL": _rs(0x0080), "DH": _rs(0x0040),
    "SI": _rs(0x0100), "DI": _rs(0x0200),
}
VAL2REG = {v: k for k, v in REG.items()}


@dataclass
class Image:
    raw: bytes
    def va2file(self, va: int) -> int: return va - DELTA
    def file2va(self, off: int) -> int: return off + DELTA
    def dword(self, off: int) -> int: return struct.unpack_from("<I", self.raw, off)[0]


def load(path: str) -> Image:
    return Image(open(path, "rb").read())


def entropy(b: bytes) -> float:
    from collections import Counter
    if not b: return 0.0
    c = Counter(b); n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())


def find_regtables(img: Image):
    """Locate EMPTY(0)-terminated register-set tables in the data segment.

    Returns list of (file_off, va, [reg_name,...]).
    """
    f = img.raw
    out = []
    o = DATA_LO
    end = len(f) - 4
    while o < end:
        v = img.dword(o)
        if v == 0:
            o += 4; continue
        start = o; vals = []
        while o < end:
            v = img.dword(o)
            if v == 0: break
            vals.append(v); o += 4
        if 2 <= len(vals) <= 40 and any(x in VAL2REG for x in vals):
            names = [VAL2REG.get(x, "?0x%X" % x) for x in vals]
            # keep tables that are mostly registers
            if sum(1 for n in names if not n.startswith("?")) >= max(2, len(names) // 2):
                out.append((start, img.file2va(start), names))
        o += 4
    return out


def selftest(img: Image):
    f = img.raw
    assert f[:2] == b"MZ"
    lx = struct.unpack_from("<I", f, 0x3C)[0]
    print(f"MZ stub + LX bootstrap at file 0x{lx:X} ({f[lx:lx+2]!r})")
    print(f"file size              0x{len(f):X}")
    print(f"entropy @code 0x10000  {entropy(f[0x10000:0x11000]):.2f}  (uncompressed if ~6)")
    print(f"entropy @data 0x70000  {entropy(f[0x70000:0x71000]):.2f}")
    print(f"coordinate system      va = file + 0x{DELTA:X}")
    # spot-check the base: find any data string whose va appears as a code
    # immediate (proves the baked-in pointers use va = file + DELTA).
    for m in re.finditer(rb"[ -~]{6,}\x00", f[0x70000:]):
        s = 0x70000 + m.start()
        if f[s - 1] != 0:
            continue
        va = img.file2va(s)
        n = sum(1 for _ in re.finditer(re.escape(struct.pack("<I", va)), f[:CODE_HI]))
        if n >= 2:
            print(f"base check: {f[s:m.end()+s-m.start()-1][:20]!r} "
                  f"file 0x{s:X} -> va 0x{va:X}; used {n}x as code imm (base OK)")
            break
    print()
    print("Register-set tables found in .data:")
    for off, va, names in find_regtables(img):
        print(f"  va 0x{va:05X} (file 0x{off:05X})  {names}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--regtables", action="store_true")
    ap.add_argument("--ghidra-base", action="store_true")
    a = ap.parse_args()
    img = load(a.exe)
    if a.ghidra_base:
        print(f"-loader BinaryLoader -loader-baseAddr 0x{DELTA:X} -processor x86:LE:32:default")
        return
    if a.regtables:
        for off, va, names in find_regtables(img):
            print(f"va 0x{va:05X} file 0x{off:05X}: {names}")
        return
    selftest(img)


if __name__ == "__main__":
    main()
