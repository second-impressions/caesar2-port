import struct

import pytest

from c2.commands.fixups import canonicalize_le_fixup_record_order


def _record(source_offset: int, target_offset: int) -> bytes:
    # off32 internal fixup, 8-bit object number, 16-bit target offset.
    return (
        b"\x07\x00"
        + struct.pack("<H", source_offset)
        + b"\x01"
        + struct.pack("<H", target_offset)
    )


def _image(pages: list[list[bytes]]) -> bytes:
    fpt_offset = 0x80
    frt_offset = 0xA0
    records = bytearray()
    entries = [0]
    for page in pages:
        records += b"".join(page)
        entries.append(len(records))

    data = bytearray(frt_offset + len(records))
    struct.pack_into("<I", data, 0x68, fpt_offset)
    struct.pack_into("<I", data, 0x6C, frt_offset)
    for index, entry in enumerate(entries):
        struct.pack_into("<I", data, fpt_offset + index * 4, entry)
    data[frt_offset:] = records
    return bytes(data)


def test_canonicalize_le_fixup_record_order_reorders_rebuilt_records() -> None:
    first = _record(4, 0x100)
    second = _record(12, 0x200)
    third = _record(20, 0x300)
    reference = _image([[first, second], [third]])
    rebuilt = _image([[second, first], [third]])

    got = canonicalize_le_fixup_record_order(reference, rebuilt, 0, 2)

    assert got == reference


def test_canonicalize_le_fixup_record_order_rejects_record_defect() -> None:
    reference = _image([[_record(4, 0x100)]])
    rebuilt = _image([[_record(4, 0x101)]])

    with pytest.raises(ValueError, match="different records"):
        canonicalize_le_fixup_record_order(reference, rebuilt, 0, 1)
