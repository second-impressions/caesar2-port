"""OMF library and object file parser.

Provides:
  - extract_omf_lib():  Extract .obj modules from an OMF .lib file.
  - parse_obj_functions():  Parse an OMF .obj → [(name, code, fixup_offsets)].

Ported from ad-hoc scripts used during compiler version identification
(see docs/compiler-version-confirmation.md).
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

# ── Location-type → byte width of the patched field ─────────────────────────

_LOC_SIZE = {
    0: 1,   # LOC_OFFSET_8
    1: 2,   # LOC_OFFSET_16
    2: 2,   # LOC_BASE_16
    3: 4,   # LOC_POINTER_32  (16:16 far ptr)
    4: 1,   # LOC_OFFSET_HIBYTE
    5: 2,   # LOC_LOADER_RESOLVED_16
    9: 4,   # LOC_OFFSET_32            ← absolute 32-bit ref
    11: 6,  # LOC_POINTER_48           (16:32 far ptr)
    13: 4,  # LOC_OFFSET_32_SELF_REL   ← relative 32-bit call/jmp
    14: 4,  # LOC_OFFSET_32_LDR
}


# ── Library extraction ───────────────────────────────────────────────────────

def extract_omf_lib(lib_path: str | Path, out_dir: str | Path) -> list[str]:
    """Extract individual .obj modules from an OMF library (.lib) file.

    Returns a list of module base names written to *out_dir*.
    """
    lib_path = Path(lib_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = lib_path.read_bytes()

    if not data or data[0] != 0xF0:
        raise ValueError(f"Not an OMF library (first byte {data[0]:#x})")

    rec_len = struct.unpack_from("<H", data, 1)[0]
    page_size = rec_len + 3

    pos = page_size  # skip library header
    modules: dict[str, bytes] = {}

    while pos < len(data):
        rtype = data[pos]
        if rtype == 0xF1:  # Library End record
            break
        if rtype not in (0x80, 0x82):  # THEADR / LHEADR
            pos = ((pos // page_size) + 1) * page_size
            if pos >= len(data):
                break
            continue

        # Module name from THEADR
        rlen = struct.unpack_from("<H", data, pos + 1)[0]
        name_len = data[pos + 3]
        mod_name = data[pos + 4 : pos + 4 + name_len].decode(
            "ascii", errors="replace"
        )
        base = os.path.splitext(
            os.path.basename(mod_name.replace("\\", "/"))
        )[0].lower()

        # Scan to MODEND (0x8A / 0x8B)
        cur = pos
        while cur < len(data):
            rt = data[cur]
            rl = struct.unpack_from("<H", data, cur + 1)[0]
            cur += 3 + rl
            if rt in (0x8A, 0x8B):
                break

        obj_bytes = data[pos:cur]

        # Deduplicate names
        out_name = base
        idx = 0
        while out_name in modules:
            idx += 1
            out_name = f"{base}_{idx}"
        modules[out_name] = obj_bytes

        (out_dir / (out_name + ".obj")).write_bytes(obj_bytes)

        pos = ((cur - 1) // page_size + 1) * page_size

    return list(modules.keys())


# ── Object file parser ───────────────────────────────────────────────────────

def parse_obj_functions(
    obj_path: str | Path,
) -> list[tuple[str, bytes, set[int]]]:
    """Parse an OMF .obj → list of (mangled_name, code_bytes, fixup_byte_offsets).

    Only functions in the _TEXT segment are returned.  Fixup byte offsets
    are relative to each function's start, making masked comparison easy.
    """
    obj_path = Path(obj_path)
    raw = obj_path.read_bytes()
    pos = 0

    lnames: list[str] = [""]
    seg_idx = 0
    seg_sizes: dict[int, int] = {}
    seg_names: dict[int, str] = {}
    seg_code: dict[int, bytearray] = {}
    seg_fixups: dict[int, set[int]] = {}
    pubdefs: list[tuple[str, int, int]] = []  # (name, seg, offset)
    last_seg = 0
    last_off = 0

    while pos < len(raw):
        rt = raw[pos]
        rl = struct.unpack_from("<H", raw, pos + 1)[0]
        body = raw[pos + 3 : pos + 2 + rl]  # exclude checksum

        if rt == 0x96:  # LNAMES
            i = 0
            while i < len(body):
                n = body[i]
                i += 1
                lnames.append(
                    body[i : i + n].decode("ascii", errors="replace")
                )
                i += n

        elif rt in (0x98, 0x99):  # SEGDEF / SEGDEF32
            seg_idx += 1
            is32 = rt == 0x99
            sz = struct.unpack_from("<I" if is32 else "<H", body, 1)[0]
            ni = body[5 if is32 else 3]
            seg_sizes[seg_idx] = sz
            seg_names[seg_idx] = lnames[ni] if ni < len(lnames) else "?"
            seg_code[seg_idx] = bytearray(sz)
            seg_fixups[seg_idx] = set()

        elif rt in (0xA0, 0xA1):  # LEDATA / LEDATA32
            seg = body[0]
            is32 = rt == 0xA1
            off = struct.unpack_from("<I" if is32 else "<H", body, 1)[0]
            payload = body[(5 if is32 else 3) :]
            sc = seg_code.get(seg)
            if sc is not None:
                sc[off : off + len(payload)] = payload
            last_seg = seg
            last_off = off

        elif rt in (0x9C, 0x9D):  # FIXUPP / FIXUPP32
            is32 = rt == 0x9D
            i = 0

            def _read_index(buf, j):
                """OMF index: 1 byte if <0x80, else 2 bytes (high bit on
                first byte signals the 2-byte form). Returns (value, new_j).
                Getting this wrong desyncs the whole FIXUPP record."""
                b0 = buf[j]
                j += 1
                if b0 & 0x80:
                    b0 = ((b0 & 0x7F) << 8) | buf[j]
                    j += 1
                return b0, j

            while i < len(body):
                if body[i] & 0x80:  # FIXUP subrecord
                    if i + 1 >= len(body):
                        break
                    locat = (body[i] << 8) | body[i + 1]
                    i += 2
                    fix_offset = locat & 0x03FF
                    loc_type = (locat >> 10) & 0x0F
                    if i >= len(body):
                        break
                    fd = body[i]
                    i += 1
                    # Fix Dat byte: F | Frame[3] | T | P | Targt[2]
                    F = (fd >> 7) & 1
                    frame_method = (fd >> 4) & 0x07
                    T = (fd >> 3) & 1
                    P = (fd >> 2) & 1
                    # Frame Datum: methods 0,1,2 carry a (variable-length)
                    # index; method 3 a 2-byte frame number; 4,5,6,7 nothing.
                    if F == 0:
                        if frame_method <= 2 and i < len(body):
                            _, i = _read_index(body, i)
                        elif frame_method == 3:
                            i += 2
                    # Target Datum: when not thread-specified, a
                    # (variable-length) segment/group/external index.
                    if T == 0 and i < len(body):
                        _, i = _read_index(body, i)
                    # Target displacement present iff P == 0.
                    if P == 0:
                        i += 4 if is32 else 2
                    fset = seg_fixups.get(last_seg)
                    if fset is not None:
                        abs_off = last_off + fix_offset
                        fix_width = _LOC_SIZE.get(loc_type, 4)
                        for b in range(fix_width):
                            fset.add(abs_off + b)
                else:  # THREAD subrecord
                    d = body[i]
                    i += 1
                    D = (d >> 6) & 1
                    method = (d >> 2) & 0x07
                    if (D == 0 and method <= 2) or (D == 1 and method <= 2):
                        i += 1

        elif rt in (0x90, 0x91):  # PUBDEF / PUBDEF32
            is32 = rt == 0x91
            seg = body[1]
            i = 2
            if seg == 0:
                i += 2
            while i < len(body):
                n = body[i]
                i += 1
                name = body[i : i + n].decode("ascii", errors="replace")
                i += n
                off = struct.unpack_from("<I" if is32 else "<H", body, i)[0]
                i += 4 if is32 else 2
                i += 1  # type index
                pubdefs.append((name, seg, off))

        pos += 3 + rl

    # Find _TEXT segment
    text_seg = next(
        (si for si, nm in seg_names.items() if nm == "_TEXT"), 1
    )
    code = bytes(seg_code.get(text_seg, b""))
    foffs = seg_fixups.get(text_seg, set())

    # Split by PUBDEF boundaries
    pubs = sorted(
        [(n, o) for n, s, o in pubdefs if s == text_seg], key=lambda x: x[1]
    )
    result = []
    for i, (name, off) in enumerate(pubs):
        end = pubs[i + 1][1] if i + 1 < len(pubs) else len(code)
        result.append(
            (name, code[off:end], {b - off for b in foffs if off <= b < end})
        )
    return result
