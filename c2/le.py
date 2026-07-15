"""LE executable access for the c2 toolkit, built on ``reccmp.formats``.

The reccmp fork (a pinned dependency) is the single implementation of
MZ/BW/LE parsing for the org; this module is the thin adapter that maps
its :class:`~reccmp.formats.lx.LXImage` onto the access patterns the
build toolchain needs:

* :func:`load_le` — open a plain or DOS/4GW-Professional-bound LE
  (walks the ``BW`` wrapper chain automatically);
* per-object **file** offset/size (from the section physical ranges);
* the loader-fixup tables as **segment-relative maps**
  ``offset → (target_object, target_offset)``, the shape the delinker
  and the final-link comparison consume.
"""

from __future__ import annotations

import struct
from pathlib import Path

from reccmp.formats.lx import LXImage, find_bw_wrapped_mz
from reccmp.formats.mz import ImageDosHeader


def load_le(path: Path) -> LXImage:
    """Open *path* as an LE image, walking any DOS/4GW BW wrapper chain."""
    data = path.read_bytes()
    mz, _ = ImageDosHeader.from_memory(data, 0)
    if data[mz.e_lfanew : mz.e_lfanew + 2] == b"LE":
        return LXImage.from_memory(data, mz, path, mz_offset=0)
    inner_mz, inner_offset = find_bw_wrapped_mz(data, mz)
    return LXImage.from_memory(data, inner_mz, path, mz_offset=inner_offset)


def mz_offset(image: LXImage) -> int:
    """Absolute file offset of the (inner) MZ stub."""
    return image.le_offset - image.mz_header.e_lfanew


def data_pages_abs(image: LXImage) -> int:
    """Absolute file offset of the first LE data page."""
    return mz_offset(image) + image.header.data_pages_offset


def object_file_offset(image: LXImage, index: int) -> int:
    """Absolute file offset of object *index* (0-based)."""
    return image.sections[index].physical_range.start


def object_file_size(image: LXImage, index: int) -> int:
    """Size of object *index*'s pages as stored in the file."""
    r = image.sections[index].physical_range
    return r.stop - r.start


def object_num_pages(image: LXImage, index: int) -> int:
    """Number of pages backing object *index*."""
    return image._raw_objects[index][2]  # noqa: SLF001 (adapter by design)


def object_raw_flags(image: LXImage, index: int) -> int:
    """Raw LE object-table flags dword for object *index* (0-based).

    reccmp maps flags onto its portable ImageSectionFlags; the export
    format also records the raw value (incl. the 0x2000 32-bit bit).
    """
    off = image.le_offset + image.header.object_table_off + index * 24
    return struct.unpack_from("<I", image.data, off + 8)[0]


def segment_fixup_maps(
    image: LXImage,
) -> tuple[dict[int, tuple[int, int]], dict[int, tuple[int, int]]]:
    """Return (code_fixups, data_fixups) as segment-relative maps.

    Each map is ``byte_offset_within_object → (target_obj_number,
    target_offset)`` covering the internal off32 loader fixups, keyed
    relative to object 1 (code) and object 2 (data) respectively.
    """
    code_base = image.sections[0].virtual_address
    code_end = code_base + image.sections[0].virtual_size
    data_base = image.sections[1].virtual_address
    data_end = data_base + image.sections[1].virtual_size

    code_map: dict[int, tuple[int, int]] = {}
    data_map: dict[int, tuple[int, int]] = {}
    for fixup in image.fixups:
        va = fixup.source_va
        target = (fixup.target_object, fixup.target_offset)
        if code_base <= va < code_end:
            code_map[va - code_base] = target
        elif data_base <= va < data_end:
            data_map[va - data_base] = target
    return code_map, data_map
