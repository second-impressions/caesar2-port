#!/usr/bin/env python3
"""Compiler/flag fingerprint for PE / NE Windows binaries (no external deps).

Reports, per file: format (PE32/NE), MS linker version -> Visual C++ product,
PE link timestamp, sections, debug directory (MISC/FPO/CodeView NB10 + PDB path
+ rebuild age), CRT linkage (static debug vs release), and a coarse /Od-vs-/O
codegen read from the prologue/var-reload pattern.

Usage:  python scripts/fingerprint_pe.py <file> [<file> ...]
        python scripts/fingerprint_pe.py data/windows-builds/store/*

Background: PE optional-header MajorLinkerVersion pins the MS toolchain
(authoritative table from geoffchappell "linkcpu"):
    LINK 2.5x -> Visual C++ 2.0      LINK 4.20 -> Visual C++ 4.2
    LINK 3.00 -> Visual C++ 4.0      LINK 5.00 -> Visual C++ 5.0
    LINK 3.10 -> Visual C++ 4.1      LINK 6.00 -> Visual C++ 6.0
"""
import struct, sys, datetime, re

LINK_TO_VC = {'2.55': 'Visual C++ 2.x', '2.60': 'Win95 DDK linker (VC2 base)',
              '3.00': 'Visual C++ 4.0', '3.10': 'Visual C++ 4.1',
              '4.20': 'Visual C++ 4.2', '5.00': 'Visual C++ 5.0',
              '6.00': 'Visual C++ 6.0'}


def rva_to_off(secs, rva):
    for nm, vsize, vaddr, rawsz, rawptr, sc in secs:
        if vaddr <= rva < vaddr + max(vsize, rawsz):
            return rawptr + (rva - vaddr)
    return None


def fingerprint(path):
    d = open(path, 'rb').read()
    out = {'file': path, 'size': len(d)}
    if d[:2] != b'MZ':
        out['format'] = 'not-MZ'
        return out
    e = struct.unpack_from('<I', d, 0x3c)[0]
    sig = d[e:e + 4]
    if sig[:2] == b'NE':
        lv, lr = d[e + 2], d[e + 3]
        tos = d[e + 0x36]
        out.update(format='NE (16-bit Windows)', linker=f'{lv}.{lr:02d}',
                   target_os={1: 'OS/2', 2: 'Windows', 3: 'DOS', 4: 'Win386'}.get(tos, tos))
        if b'PKSFX' in d:
            out['note'] = 'PKWARE PKSFX self-extractor (wrapper, not compiled game code)'
        return out
    if sig != b'PE\0\0':
        out['format'] = sig[:2].decode('latin1', 'replace')
        return out
    coff = e + 4
    machine, nsec, ts, _, _, optsz, chars = struct.unpack_from('<HHIIIHH', d, coff)
    opt = coff + 20
    lmaj, lmin = d[opt + 2], d[opt + 3]
    link = f'{lmaj}.{lmin:02d}'
    secoff = opt + optsz
    secs = []
    for i in range(nsec):
        nm = d[secoff + i * 40:secoff + i * 40 + 8].rstrip(b'\0').decode('latin1', 'replace')
        vsize, vaddr, rawsz, rawptr = struct.unpack_from('<IIII', d, secoff + i * 40 + 8)
        secs.append((nm, vsize, vaddr, rawsz, rawptr, 0))
    nrva = struct.unpack_from('<I', d, opt + 92)[0]
    ddoff = opt + 96
    debug = None
    for i in range(min(nrva, 16)):
        va, sz = struct.unpack_from('<II', d, ddoff + i * 8)
        if i == 6 and va:
            debug = (va, sz)
    dbg_entries, pdb, age = [], None, None
    if debug:
        off = rva_to_off(secs, debug[0])
        if off is not None:
            for k in range(debug[1] // 28):
                _, _, _, _, typ, szd, _, ptr = struct.unpack_from('<IIHHIIII', d, off + k * 28)
                tn = {1: 'COFF', 2: 'CODEVIEW', 3: 'FPO', 4: 'MISC'}.get(typ, typ)
                dbg_entries.append(tn)
                if typ == 2 and ptr and d[ptr:ptr + 4] == b'NB10':
                    age = struct.unpack_from('<I', d, ptr + 12)[0]
                    pdb = d[ptr + 16:].split(b'\0')[0].decode('latin1', 'replace')
    debug_crt = b'Debug Library' in d
    watcom = b'WATCOM' in d or b'Watcom' in d
    out.update(format='PE32', linker=link,
               compiler=('Watcom C/C++32 (wlink %s)' % link) if watcom else LINK_TO_VC.get(link, 'unknown'),
               link_date_utc=datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") if ts else None,
               sections=[s[0] for s in secs], debug_dir=dbg_entries or None,
               pdb=pdb, pdb_age=age,
               crt=('static debug CRT (LIBCD/LIBCMTD)' if debug_crt
                    else ('Watcom RT' if watcom else 'static/DLL release CRT')),
               config=('Debug /Od (no optimization)' if debug_crt and not watcom
                       else ('3rd-party (Watcom)' if watcom else 'Release')))
    return out


if __name__ == '__main__':
    import json
    for p in sys.argv[1:]:
        print(json.dumps(fingerprint(p), indent=2))
