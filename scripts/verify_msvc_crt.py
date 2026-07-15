#!/usr/bin/env python3
"""Prove a CAESAR2.EXE (Win) build links the Visual C++ 4.0 *debug* CRT.

Method (lotr2-style CRT-module fingerprint, adapted to COFF/PE):
  * Parse VC4.0's LIBCD.LIB (debug) and LIBC.LIB (release) — MS COFF archives.
  * For chosen CRT objects, pull the .obj's .text + relocation table; mask the
    4-byte DIR32/REL32 reloc slots to wildcards (link-time-patched).
  * Search the binary's .text for the masked byte-run.
  * Discriminator: objects whose code DIFFERS between LIBCD and LIBC (malloc,
    free) match the *debug* lib and NOT the release lib -> proves /MLd debug CRT.

Compiler source (not hosted; clone on demand):
    https://github.com/itsmattkc/MSVC400  (commit 821e942)
    LINK.EXE = 3.00.5270, CL.EXE = 10.00.5270  == Visual C++ 4.0
    LIBCD.LIB sha256 08eff0ddca5631cedaa61140c0bfb45fa958c1e165326aaf7e451f6c12105d8f
    LIBC.LIB  sha256 e5f0d0e6dd2e01dbb0005e9dd4764507b852ede9a824798f0970bc570966a7e3

Usage:
    git clone --depth 1 https://github.com/itsmattkc/MSVC400 /tmp/MSVC400
    python scripts/verify_msvc_crt.py data/windows-builds/named/caesar2_C_1060864.exe /tmp/MSVC400
"""
import struct, sys, os


def pe_text(path):
    d = open(path, 'rb').read()
    e = struct.unpack_from('<I', d, 0x3c)[0]
    coff = e + 4
    nsec, optsz = struct.unpack_from('<H', d, coff + 2)[0], struct.unpack_from('<H', d, coff + 16)[0]
    secoff = coff + 20 + optsz
    for i in range(nsec):
        b = secoff + i * 40
        nm = d[b:b + 8].rstrip(b'\0')
        vsize, vaddr, rawsz, rawptr = struct.unpack_from('<IIII', d, b + 8)
        if nm == b'.text':
            return d[rawptr:rawptr + rawsz], vaddr
    return None, None


def lib_members(libdata):
    i = 8
    ms = []
    ln = b''
    while i + 60 <= len(libdata):
        hdr = libdata[i:i + 60]
        nm = hdr[0:16].decode('latin1').rstrip()
        size = int(hdr[48:58].decode().strip())
        do = i + 60
        ms.append((nm, do, size))
        i = do + size + (size % 2)
    for nm, do, sz in ms:
        if nm == '//':
            ln = libdata[do:do + sz]

    def res(nm):
        if nm.startswith('/') and nm[1:].isdigit():
            o = int(nm[1:]); en = ln.find(b'\0', o); return ln[o:en].decode('latin1')
        return nm.rstrip('/')
    return [(res(nm).split('\\')[-1], do, sz) for nm, do, sz in ms if nm not in ('/', '//')]


def obj_text_mask(libdata, do, sz, secname=b'.text'):
    data = libdata[do:do + sz]
    nsec, optsz = struct.unpack_from('<H', data, 2)[0], struct.unpack_from('<H', data, 16)[0]
    so = 20 + optsz
    for k in range(nsec):
        b = so + k * 40
        secn = data[b:b + 8].rstrip(b'\0')
        vsize, vaddr, rawsz, rawptr, relptr = struct.unpack_from('<IIIII', data, b + 8)
        nrel = struct.unpack_from('<H', data, b + 32)[0]
        if secn.startswith(secname) and rawsz > 0:
            code = bytearray(data[rawptr:rawptr + rawsz])
            mask = bytearray(len(code))
            for r in range(nrel):
                va, si, ty = struct.unpack_from('<IIH', data, relptr + r * 10)
                if ty in (6, 20):  # DIR32 / REL32 -> 4 patched bytes
                    for j in range(4):
                        if va + j < len(mask):
                            mask[va + j] = 1
            return bytes(code), bytes(mask), nrel
    return None, None, 0


def get_obj(libdata, basename):
    for nm, do, sz in lib_members(libdata):
        if nm == basename:
            return obj_text_mask(libdata, do, sz)
    return None, None, 0


def masked_find(hay, needle, mask):
    n = len(needle)
    best = (0, 0)
    run = 0; start = 0
    for i in range(n):  # longest fixed run as anchor
        if not mask[i]:
            if run == 0:
                start = i
            run += 1
            if run > best[1]:
                best = (start, run)
        else:
            run = 0
    rs, rl = best
    sub = needle[rs:rs + rl]
    hits = []
    pos = hay.find(sub)
    while pos != -1:
        s = pos - rs
        if 0 <= s and s + n <= len(hay) and all(mask[i] or hay[s + i] == needle[i] for i in range(n)):
            hits.append(s)
        pos = hay.find(sub, pos + 1)
    return hits


def main():
    binpath, msvc = sys.argv[1], sys.argv[2]
    libcd = open(os.path.join(msvc, 'LIB', 'LIBCD.LIB'), 'rb').read()
    libc = open(os.path.join(msvc, 'LIB', 'LIBC.LIB'), 'rb').read()
    code, va = pe_text(binpath)
    print(f"binary: {binpath}  (.text {len(code)} B @ {hex(va)})\n")

    print("[1] CRT leaf routines (reloc-free) — byte-exact match vs VC4.0 LIBCD:")
    for obj in ['chkstk.obj', 'strlen.obj', 'memset.obj', 'strcat.obj', 'memcpy.obj']:
        c, m, n = get_obj(libcd, obj)
        h = masked_find(code, c, m) if c else []
        print(f"    {obj:12s} {len(c):4d}B {n:2d} relocs  -> {len(h)} match @ {[hex(va+x) for x in h[:2]]}")

    print("\n[2] DEBUG discriminator (objects whose code differs debug vs release):")
    for obj in ['malloc.obj', 'free.obj']:
        cd, mcd, ncd = get_obj(libcd, obj)
        cc, mcc, ncc = get_obj(libc, obj)
        hcd = masked_find(code, cd, mcd) if cd else []
        hcc = masked_find(code, cc, mcc) if cc else []
        verdict = 'DEBUG (LIBCD)' if hcd and not hcc else ('release (LIBC)' if hcc and not hcd else 'inconclusive')
        print(f"    {obj:12s} LIBCD={len(cd)}B/{len(hcd)}match  LIBC={len(cc)}B/{len(hcc)}match  => {verdict}")


if __name__ == '__main__':
    main()
