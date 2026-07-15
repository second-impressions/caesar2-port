"""OMF LINNUM extractor.

Walks an .obj's record stream and pulls every ``LINNUM`` / ``LINNUM32``
(0x94 / 0x95) entry, returning per-segment ``[(line, offset), ...]`` lists.

Combined with the PUBDEF table (the c2 ``parse_obj_functions`` already
returns), this lets us tell the agent which scratch.c source line emitted
each instruction in their recompile \u2014 the same way PS's debug info maps
the target's bytes to its original source lines.
"""

from __future__ import annotations

import struct
from collections import defaultdict
from pathlib import Path


def parse_linnum(obj_path: str | Path) -> dict[int, list[tuple[int, int]]]:
    """Return ``{segment_index: [(line_number, offset_in_segment), ...]}``.

    Segment index matches the order SEGDEF / SEGDEF32 records appear in
    the obj (1-based, mirroring c2.parsers.omf conventions).
    """
    raw = Path(obj_path).read_bytes()
    pos = 0
    out: dict[int, list[tuple[int, int]]] = defaultdict(list)
    seg_idx = 0

    while pos < len(raw):
        rt = raw[pos]
        rl = struct.unpack_from("<H", raw, pos + 1)[0]
        body = raw[pos + 3 : pos + 2 + rl]  # exclude trailing checksum

        if rt in (0x98, 0x99):  # SEGDEF / SEGDEF32
            seg_idx += 1

        elif rt in (0x94, 0x95):  # LINNUM / LINNUM32
            is32 = rt == 0x95
            # Body layout:
            #   BaseGroup index (1 or 2 byte OMF index)
            #   BaseSeg   index (1 or 2 byte OMF index)
            #   pairs of (line_no : u16, offset : u16 or u32)
            i = 0

            def _read_index(buf: bytes, j: int) -> tuple[int, int]:
                b0 = buf[j]
                j += 1
                if b0 & 0x80:
                    b0 = ((b0 & 0x7F) << 8) | buf[j]
                    j += 1
                return b0, j

            try:
                _grp, i = _read_index(body, i)
                seg, i = _read_index(body, i)
            except IndexError:
                pos += 3 + rl
                continue

            entry_size = 2 + (4 if is32 else 2)
            while i + entry_size <= len(body):
                line_no = struct.unpack_from("<H", body, i)[0]
                offset = struct.unpack_from(
                    "<I" if is32 else "<H", body, i + 2,
                )[0]
                out[seg].append((line_no, offset))
                i += entry_size

        pos += 3 + rl

    return dict(out)


def function_line_map(
    obj_path: str | Path,
    function_start_in_text: int,
    function_size: int,
    text_seg: int = 1,
) -> tuple[tuple[int, int], ...]:
    """Return ``((offset_in_function, source_line), ...)`` for the function
    occupying ``[function_start_in_text, function_start_in_text + function_size)``
    bytes of the ``_TEXT`` segment.  Empty tuple if no LINNUM records cover it.
    """
    all_marks = parse_linnum(obj_path).get(text_seg, [])
    out: list[tuple[int, int]] = []
    for line_no, off in all_marks:
        if function_start_in_text <= off < function_start_in_text + function_size:
            out.append((off - function_start_in_text, line_no))
    out.sort()
    return tuple(out)
