"""LE fixup record parser for Caesar II PS.EXE.

Based on Open Watcom exeflat.h and bld/exedump/c/wdfix.c reference impl.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import struct
from pathlib import Path

# Source type masks (exeflat.h)
OSF_SOURCE_MASK = 0x0F
OSF_SOURCE_BYTE = 0x00
OSF_SOURCE_SEG = 0x02
OSF_SOURCE_PTR_32 = 0x03
OSF_SOURCE_OFF_16 = 0x05
OSF_SOURCE_PTR_48 = 0x06
OSF_SOURCE_OFF_32 = 0x07
OSF_SOURCE_OFF_32_REL = 0x08

OSF_SFLAG_LIST = 0x20

# Target flags (exeflat.h)
OSF_TARGET_MASK = 0x03
OSF_TARGET_INTERNAL = 0x00
OSF_TARGET_EXT_ORD = 0x01
OSF_TARGET_EXT_NAME = 0x02
OSF_TARGET_INT_VIA_ENTRY = 0x03

OSF_TFLAG_ADDITIVE_VAL = 0x04
OSF_TFLAG_OFF_32BIT = 0x10
OSF_TFLAG_ADD_32BIT = 0x20
OSF_TFLAG_OBJ_MOD_16BIT = 0x40
OSF_TFLAG_ORDINAL_8BIT = 0x80


def parse_le_fixups(
    exe_path: Path,
    le_offset: int,
    page_size: int,
    num_pages: int,
    code_pages: int,
    data_pages: int = 0,
) -> tuple[dict[int, tuple[int, int]], dict[int, tuple[int, int]]]:
    """Parse LE fixup records for code and data segments.

    Returns (code_fixups, data_fixups) where each is a dict:
        byte_offset_within_segment → (target_obj_number, target_offset).
    Only off32 internal fixups are returned.
    """
    data = exe_path.read_bytes()

    fpt_off = struct.unpack_from("<I", data, le_offset + 0x68)[0]
    frt_off = struct.unpack_from("<I", data, le_offset + 0x6C)[0]
    fpt_abs = le_offset + fpt_off
    frt_abs = le_offset + frt_off

    entries = [
        struct.unpack_from("<I", data, fpt_abs + i * 4)[0]
        for i in range(num_pages + 1)
    ]

    code_fixups: dict[int, tuple[int, int]] = {}
    data_fixups: dict[int, tuple[int, int]] = {}

    total_pages = code_pages + data_pages if data_pages else code_pages

    for page in range(total_pages):
        pos = frt_abs + entries[page]
        end = frt_abs + entries[page + 1]

        # Determine which segment and base page for offset calculation
        if page < code_pages:
            target_map = code_fixups
            seg_base_page = 0
        else:
            target_map = data_fixups
            seg_base_page = code_pages

        while pos < end:
            source = data[pos]
            flags = data[pos + 1]
            pos += 2

            src_kind = source & OSF_SOURCE_MASK
            is_list = bool(source & OSF_SFLAG_LIST)

            if is_list:
                cnt = data[pos]
                pos += 1
            else:
                src_off = struct.unpack_from("<H", data, pos)[0]
                cnt = 0
                pos += 2

            tgt_type = flags & OSF_TARGET_MASK

            if tgt_type == OSF_TARGET_INTERNAL:
                pos = _parse_internal(
                    data, pos, flags, source, src_kind, is_list, cnt,
                    src_off if not is_list else 0,
                    page - seg_base_page, page_size, target_map,
                )
            elif tgt_type == OSF_TARGET_EXT_ORD:
                pos = _skip_imp_ord(data, pos, flags, is_list, cnt)
            elif tgt_type == OSF_TARGET_EXT_NAME:
                pos = _skip_imp_name(data, pos, flags, is_list, cnt)
            elif tgt_type == OSF_TARGET_INT_VIA_ENTRY:
                pos = _skip_int_entry(data, pos, flags, is_list, cnt)

    return code_fixups, data_fixups


def _raw_fixup_record_pages(
    data: bytes, le_offset: int, num_pages: int,
) -> tuple[int, list[int], list[list[bytes]]]:
    """Return the raw LE fixup records for each load page.

    The fixup-page table gives byte ranges, but records are variable-sized.
    Decode only far enough to retain each complete record as an opaque byte
    string.  This is deliberately independent of relocation semantics: the
    normal parser above remains the semantic oracle.
    """
    fpt_off = struct.unpack_from("<I", data, le_offset + 0x68)[0]
    frt_off = struct.unpack_from("<I", data, le_offset + 0x6C)[0]
    fpt_abs = le_offset + fpt_off
    frt_abs = le_offset + frt_off
    entries = [
        struct.unpack_from("<I", data, fpt_abs + i * 4)[0]
        for i in range(num_pages + 1)
    ]

    pages: list[list[bytes]] = []
    for page in range(num_pages):
        pos = frt_abs + entries[page]
        end = frt_abs + entries[page + 1]
        records: list[bytes] = []
        while pos < end:
            record_start = pos
            source = data[pos]
            flags = data[pos + 1]
            pos += 2

            src_kind = source & OSF_SOURCE_MASK
            is_list = bool(source & OSF_SFLAG_LIST)
            if is_list:
                cnt = data[pos]
                src_off = 0
                pos += 1
            else:
                src_off = struct.unpack_from("<H", data, pos)[0]
                cnt = 0
                pos += 2

            tgt_type = flags & OSF_TARGET_MASK
            if tgt_type == OSF_TARGET_INTERNAL:
                pos = _parse_internal(
                    data, pos, flags, source, src_kind, is_list, cnt,
                    src_off, page, 1, {},
                )
            elif tgt_type == OSF_TARGET_EXT_ORD:
                pos = _skip_imp_ord(data, pos, flags, is_list, cnt)
            elif tgt_type == OSF_TARGET_EXT_NAME:
                pos = _skip_imp_name(data, pos, flags, is_list, cnt)
            elif tgt_type == OSF_TARGET_INT_VIA_ENTRY:
                pos = _skip_int_entry(data, pos, flags, is_list, cnt)

            if pos <= record_start or pos > end:
                raise ValueError(
                    f"malformed LE fixup record on page {page}: "
                    f"0x{record_start:x}..0x{pos:x}, page ends 0x{end:x}"
                )
            records.append(data[record_start:pos])
        if pos != end:
            raise ValueError(
                f"LE fixup page {page} ended at 0x{pos:x}, expected 0x{end:x}"
            )
        pages.append(records)

    return frt_abs, entries, pages


def canonicalize_le_fixup_record_order(
    reference: bytes, rebuilt: bytes, le_offset: int, num_pages: int,
) -> bytes:
    """Reorder rebuilt LE fixup records to the reference page order.

    WLINK's loader-fixup list insertion order depends on the original OMF
    FIXUPP record/chunk boundaries.  Delinking preserves every relocation
    record byte and target, but reconstructed OMF chunking can permute those
    records in the final LE.  Require an identical per-page record multiset,
    then consume the *rebuilt* records in reference order.  No record bytes
    or relocation semantics are copied from the reference executable.
    """
    ref_frt, ref_entries, ref_pages = _raw_fixup_record_pages(
        reference, le_offset, num_pages,
    )
    out = bytearray(rebuilt)
    out_frt, out_entries, out_pages = _raw_fixup_record_pages(
        rebuilt, le_offset, num_pages,
    )
    if ref_entries != out_entries:
        raise ValueError("LE fixup page tables differ; cannot canonicalize order")

    for page, (want, have) in enumerate(zip(ref_pages, out_pages)):
        if Counter(want) != Counter(have):
            raise ValueError(
                f"LE fixup page {page} has different records; "
                "refusing to hide a relocation defect"
            )
        available: dict[bytes, list[bytes]] = defaultdict(list)
        for rebuilt_record in have:
            available[rebuilt_record].append(rebuilt_record)
        ordered = b"".join(available[want_record].pop() for want_record in want)
        # Every emitted record above came from the rebuild; the reference
        # contributes only the ordering key.
        start = out_frt + out_entries[page]
        end = out_frt + out_entries[page + 1]
        if len(ordered) != end - start:
            raise ValueError(f"LE fixup page {page} changed size")
        out[start:end] = ordered

    return bytes(out)


def _parse_internal(
    data: bytes, pos: int, flags: int, source: int, src_kind: int,
    is_list: bool, cnt: int, src_off: int,
    page: int, page_size: int,
    fixup_map: dict[int, tuple[int, int]],
) -> int:
    """Parse an internal fixup record (matches wdfix.c internal_ref)."""
    # Object number
    if flags & OSF_TFLAG_OBJ_MOD_16BIT:
        obj_num = struct.unpack_from("<H", data, pos)[0]
        pos += 2
    else:
        obj_num = data[pos]
        pos += 1

    # Target offset — read for all source types EXCEPT OSF_SOURCE_SEG
    tgt_off = 0
    if src_kind != OSF_SOURCE_SEG:
        if flags & OSF_TFLAG_OFF_32BIT:
            tgt_off = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        else:
            tgt_off = struct.unpack_from("<H", data, pos)[0]
            pos += 2

    # Note: internal_ref in wdfix.c does NOT handle ADDITIVE_VAL.
    # Only import and entry refs do.

    # Record off32 fixups
    # src_off is unsigned 16-bit but can exceed page_size for cross-page
    # fixups.  In that case, interpret as signed offset from page base.
    def _abs_off(page: int, soff: int) -> int:
        if soff > 0x7FFF:  # treat as signed 16-bit
            return page * page_size + (soff - 0x10000)
        return page * page_size + soff

    if src_kind == OSF_SOURCE_OFF_32:
        if is_list:
            for _ in range(cnt):
                soff = struct.unpack_from("<H", data, pos)[0]
                pos += 2
                fixup_map[_abs_off(page, soff)] = (obj_num, tgt_off)
        else:
            fixup_map[_abs_off(page, src_off)] = (obj_num, tgt_off)
    elif is_list:
        # Skip source list for non-off32
        pos += cnt * 2

    return pos


def _skip_imp_ord(data: bytes, pos: int, flags: int, is_list: bool, cnt: int) -> int:
    """Skip import-by-ordinal fixup record."""
    # Module ordinal
    if flags & OSF_TFLAG_OBJ_MOD_16BIT:
        pos += 2
    else:
        pos += 1
    # Import ordinal
    if flags & OSF_TFLAG_ORDINAL_8BIT:
        pos += 1
    elif flags & OSF_TFLAG_OFF_32BIT:
        pos += 4
    else:
        pos += 2
    # Additive
    if flags & OSF_TFLAG_ADDITIVE_VAL:
        if flags & OSF_TFLAG_ADD_32BIT:
            pos += 4
        else:
            pos += 2
    if is_list:
        pos += cnt * 2
    return pos


def _skip_imp_name(data: bytes, pos: int, flags: int, is_list: bool, cnt: int) -> int:
    """Skip import-by-name fixup record."""
    # Module ordinal
    if flags & OSF_TFLAG_OBJ_MOD_16BIT:
        pos += 2
    else:
        pos += 1
    # Procedure name offset
    if flags & OSF_TFLAG_OFF_32BIT:
        pos += 4
    else:
        pos += 2
    # Additive
    if flags & OSF_TFLAG_ADDITIVE_VAL:
        if flags & OSF_TFLAG_ADD_32BIT:
            pos += 4
        else:
            pos += 2
    if is_list:
        pos += cnt * 2
    return pos


def _skip_int_entry(data: bytes, pos: int, flags: int, is_list: bool, cnt: int) -> int:
    """Skip internal-via-entry fixup record."""
    # Entry ordinal
    if flags & OSF_TFLAG_OBJ_MOD_16BIT:
        pos += 2
    else:
        pos += 1
    # Additive
    if flags & OSF_TFLAG_ADDITIVE_VAL:
        if flags & OSF_TFLAG_ADD_32BIT:
            pos += 4
        else:
            pos += 2
    if is_list:
        pos += cnt * 2
    return pos
