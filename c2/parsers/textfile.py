"""Caesar II Textfile format parser.

Parses and serialises the binary text files used by Caesar II for localised UI strings:
  - C2.ENG  (English)
  - C2.GER  (German)
  - C2.FRE  (French)
  - C2.SPA  (Spanish)

Format overview:
  - 8-byte magic: "Textfile" (no null terminator)
  - Offset table: N × 4-byte LE absolute file offsets
      entry[0] = 0x00000000  (null sentinel)
      entry[1] = offset of string group 1  (= byte immediately after table)
      entry[i] = offset of string group i
      Multiple entries MAY share the same offset (aliasing).
  - String area: null-terminated strings packed consecutively
      Each entry[i] points to a string group (one or more \\0-terminated strings)

Character encoding: CP437 (IBM PC / DOS codepage 437).

Buffer limit: the game loads the file into a 40,000-byte buffer via a single readfile()
call. Files larger than 40,000 bytes will be silently truncated by the game.

Reference: docs/textfile-format.md
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO

# ── Constants ─────────────────────────────────────────────────────────────────

MAGIC = b"Textfile"
ENCODING = "cp437"
GAME_BUFFER_LIMIT = 40_000  # bytes — hard limit in readfile() call


# ── Data model ────────────────────────────────────────────────────────────────


@dataclass
class TextFile:
    """Parsed representation of a Caesar II Textfile.

    ``groups`` is a list of string groups, one per offset-table entry.
    ``groups[0]`` is always an empty list (the null sentinel entry).
    ``groups[i]`` is a list of raw CP437-encoded byte strings (no null terminators).

    Multiple entries may share the *same* list object (aliasing): when
    ``groups[i] is groups[j]`` the serialiser will emit the string data only
    once and point both offset-table entries at the same file offset.

    Round-trip guarantee: ``serialise(parse(path)) == path.read_bytes()``.
    """

    groups: list[list[bytes]] = field(default_factory=list)

    # ── Convenience helpers ───────────────────────────────────────────────────

    def get_string(self, group_idx: int, string_idx: int = 0) -> str:
        """Return string ``string_idx`` from group ``group_idx`` as a Unicode string.

        Raises ``IndexError`` if either index is out of range.
        """
        raw = self.groups[group_idx][string_idx]
        return raw.decode(ENCODING)

    def set_string(self, group_idx: int, string_idx: int, value: str) -> None:
        """Set string ``string_idx`` in group ``group_idx`` from a Unicode string."""
        self.groups[group_idx][string_idx] = value.encode(ENCODING)

    @property
    def num_groups(self) -> int:
        """Total number of groups including the null sentinel at index 0."""
        return len(self.groups)


# ── Parser ────────────────────────────────────────────────────────────────────


def parse(path: Path) -> TextFile:
    """Parse a Caesar II Textfile from *path*.

    Raises:
        ValueError: if the magic is wrong or the file is malformed.
        FileNotFoundError: if *path* does not exist.
    """
    with open(path, "rb") as f:
        return _parse_stream(f, path.name)


def parse_bytes(data: bytes, name: str = "<bytes>") -> TextFile:
    """Parse a Caesar II Textfile from a ``bytes`` object."""
    import io

    return _parse_stream(io.BytesIO(data), name)


def _parse_stream(f: BinaryIO, name: str) -> TextFile:
    data = f.read()

    # ── Magic ─────────────────────────────────────────────────────────────────
    if len(data) < 8:
        raise ValueError(f"{name}: file too small ({len(data)} bytes)")
    magic = data[0:8]
    if magic != MAGIC:
        raise ValueError(f"{name}: bad magic {magic!r}, expected {MAGIC!r}")

    # ── Offset table ──────────────────────────────────────────────────────────
    # entry[0] is always 0 (sentinel); entry[1] is the offset of the first string
    # group, which is also the byte immediately after the offset table.
    if len(data) < 16:
        raise ValueError(f"{name}: file too small to contain offset table")

    entry0 = struct.unpack_from("<I", data, 8)[0]
    if entry0 != 0:
        raise ValueError(f"{name}: entry[0] must be 0, got 0x{entry0:08x}")

    entry1 = struct.unpack_from("<I", data, 12)[0]
    if entry1 == 0:
        # Degenerate file with no strings
        return TextFile(groups=[[]])

    if entry1 < 12 or (entry1 - 8) % 4 != 0:
        raise ValueError(
            f"{name}: entry[1]=0x{entry1:x} is not a valid table-end offset"
        )

    num_entries = (entry1 - 8) // 4
    table_end = 8 + num_entries * 4

    if len(data) < table_end:
        raise ValueError(
            f"{name}: file truncated in offset table "
            f"(need {table_end} bytes, have {len(data)})"
        )

    offsets: list[int] = []
    for i in range(num_entries):
        off = struct.unpack_from("<I", data, 8 + i * 4)[0]
        offsets.append(off)

    # ── String area ───────────────────────────────────────────────────────────
    # Build a cache: file_offset → list[bytes] so that aliased entries (multiple
    # table entries pointing to the same offset) share the same list object.
    offset_to_group: dict[int, list[bytes]] = {}

    # Determine the end of each unique offset's data by sorting unique non-zero
    # offsets and using the next one as the boundary.
    unique_offsets = sorted(set(o for o in offsets if o > 0))
    offset_end: dict[int, int] = {}
    for k, o in enumerate(unique_offsets):
        end = unique_offsets[k + 1] if k + 1 < len(unique_offsets) else len(data)
        offset_end[o] = end

    for o in unique_offsets:
        if o >= len(data):
            raise ValueError(
                f"{name}: offset 0x{o:x} is beyond end of file"
            )
        group_data = data[o : offset_end[o]]
        # Split on \0; discard trailing empty segment from the final \0
        parts = group_data.split(b"\x00")
        if parts and parts[-1] == b"":
            parts = parts[:-1]
        offset_to_group[o] = parts

    groups: list[list[bytes]] = []
    for off in offsets:
        if off == 0:
            groups.append([])
        else:
            groups.append(offset_to_group[off])

    return TextFile(groups=groups)


# ── Serialiser ────────────────────────────────────────────────────────────────


def serialise(tf: TextFile) -> bytes:
    """Serialise a ``TextFile`` back to its binary representation.

    The output is binary-identical to the original file when the ``TextFile``
    was produced by ``parse()`` without modification.

    Aliased groups (``groups[i] is groups[j]``) are serialised as a single
    string-data block with both offset-table entries pointing to it.

    Raises:
        ValueError: if the serialised size would exceed ``GAME_BUFFER_LIMIT``.
    """
    num_entries = tf.num_groups
    table_size = 8 + num_entries * 4  # magic (8) + offset table

    # Assign a file offset to each unique group object (by identity).
    # We process groups in index order so the first occurrence of each unique
    # group object determines its position in the string area.
    id_to_offset: dict[int, int] = {}  # id(group_list) → absolute file offset
    string_area = bytearray()

    offsets: list[int] = []

    for group in tf.groups:
        if not group:
            # Sentinel / empty group → offset 0
            offsets.append(0)
            continue

        gid = id(group)
        if gid in id_to_offset:
            # Aliased: reuse the previously assigned offset
            offsets.append(id_to_offset[gid])
        else:
            abs_offset = table_size + len(string_area)
            id_to_offset[gid] = abs_offset
            offsets.append(abs_offset)
            group_bytes = b"\x00".join(group) + b"\x00"
            string_area.extend(group_bytes)

    # Assemble the file
    out = bytearray()
    out.extend(MAGIC)
    for off in offsets:
        out.extend(struct.pack("<I", off))
    out.extend(string_area)

    result = bytes(out)

    if len(result) > GAME_BUFFER_LIMIT:
        raise ValueError(
            f"Serialised size {len(result)} bytes exceeds game buffer limit "
            f"of {GAME_BUFFER_LIMIT} bytes"
        )

    return result


# ── Convenience I/O ───────────────────────────────────────────────────────────


def write(tf: TextFile, path: Path) -> None:
    """Serialise *tf* and write it to *path*."""
    path.write_bytes(serialise(tf))
