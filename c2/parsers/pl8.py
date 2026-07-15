"""Caesar II `.PL8` sprite/image format parser and serialiser.

A `.PL8` file is an 8-bit palette-indexed sprite container used by Caesar II for
everything from full-screen backgrounds to small UI icons and building sprites.

Format overview
---------------
- 8-byte file header
    byte 0x00: format version (always 0x02)
    byte 0x01: zoom level (0 = full detail, 1 = medium, 2 = small)
    bytes 0x02–0x03: sprite count N (LE uint16)
    bytes 0x04–0x05: tool metadata — group boundary index (NOT read at runtime)
    byte  0x06: always 0x00 (padding)
    byte  0x07: tool metadata — file ID / set index 0–15 (NOT read at runtime)
- N × 16-byte sprite descriptor table (starts at offset 0x08)
    +0x00: width  (LE uint16)
    +0x02: height (LE uint16)
    +0x04: sprite_start (LE uint24, 3 bytes) — absolute file offset of pixel data
    +0x07: 0x00 padding
    +0x08: default_x (LE uint16) — screen X for composition
    +0x0A: default_y (LE uint16) — screen Y for composition
    +0x0C: blitter type (uint8) — 0=flat, 1=diamond, 2=ext-diamond, 3=left-roof, 4=right-roof
    +0x0D: extra_rows / y_len (uint8) — body row count for types 2, 3, 4
    +0x0E: 0x0000 padding (2 bytes)
- Pixel data area: raw 8-bit palette-indexed pixels, packed consecutively

Palette
-------
`.PL8` files contain NO embedded palette.  The palette is always stored in a
companion `.256` file (768 bytes = 256 × RGB triplets, 6-bit VGA DAC values 0–63).
Scale to 8-bit: ``r8 = r6 * 4``.

Reference: data/docs/pl8-format.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

from construct import (
    Array as CArray,
    Bytes as CBytes,
    BytesInteger,
    Const,
    GreedyBytes,
    Int8ub,
    Int16ul,
    Padding,
    Struct as CStruct,
    this,
)

# ── Constants ─────────────────────────────────────────────────────────────────

FORMAT_VERSION = 0x02
HEADER_SIZE = 8
DESCRIPTOR_SIZE = 16
PALETTE_ENTRIES = 256
PALETTE_FILE_SIZE = PALETTE_ENTRIES * 3  # 768 bytes

# ── Construct schemas ─────────────────────────────────────────────────────────
#
# Declarative binary format definitions using the ``construct`` library.
# These handle parsing AND building of the PL8 header, descriptor table,
# and VGA palette — replacing manual struct.pack/unpack code.

#: 3-byte little-endian unsigned integer (used for sprite_start offsets).
Int24ul = BytesInteger(3, signed=False, swapped=True)

#: 8-byte PL8 file header.
PL8HeaderSchema = CStruct(
    "version" / Const(bytes([FORMAT_VERSION])),
    "zoom_level" / Int8ub,
    "sprite_count" / Int16ul,
    "group_boundary_index" / Int16ul,
    Padding(1),
    "file_id" / Int8ub,
)

#: 16-byte sprite descriptor entry.
SpriteDescriptorSchema = CStruct(
    "width" / Int16ul,
    "height" / Int16ul,
    "sprite_start" / Int24ul,
    Padding(1),
    "default_x" / Int16ul,
    "default_y" / Int16ul,
    "extra" / CBytes(4),
)

#: Complete PL8 file: header + descriptor table + remaining pixel data.
PL8FileSchema = CStruct(
    "header" / PL8HeaderSchema,
    "descriptors" / CArray(this.header.sprite_count, SpriteDescriptorSchema),
    "pixel_area" / GreedyBytes,
)

#: VGA palette entry (3 bytes: R, G, B in 6-bit VGA DAC values 0–63).
VGAPaletteEntrySchema = CStruct(
    "r" / Int8ub,
    "g" / Int8ub,
    "b" / Int8ub,
)

#: Complete 256-entry VGA palette (768 bytes).
VGAPaletteSchema = CArray(PALETTE_ENTRIES, VGAPaletteEntrySchema)

# Diamond-scan tile encoding (CITYFIXT / PROVFIXT / BATLFIX sprites, all zoom levels)
#
# The game's `place_i_large_diamond` blitter reads pixels in diamond-scan order.
# The same formula applies at all three zoom levels:
#
#   top half    (row 0 .. H//2-1): width = 4*row + 2,          col_start = (W//2 - 1) - 2*row
#   bottom half (row H//2 .. H-1): width = 4*(H-1-row) + 2,   col_start = 2*(row - H//2)
#
# Actual bytes per sprite = H//2 * (W + 2) / 2 * 2 = H//2 * (W + 2)
# (which equals the sum of the arithmetic series 2, 6, 10, ..., W, W, ..., 2)
#
# Known zoom-level variants:
#   zoom 0 (full):   58×30, 900 bytes   (CITYFIXT.PL8,  PROVFIXT.PL8)
#   zoom 1 (medium): 26×14, 196 bytes   (CITYFIX2.PL8,  PROVFIX2.PL8, BATLFIX2.PL8)
#   zoom 2 (small):  10×6,   36 bytes   (CITYFIX3.PL8,  PROVFIX3.PL8, BATLFIX3.PL8)
#
# Detection: a sprite is diamond-encoded when its actual stored byte count equals
# the diamond formula result for its declared (width, height).

def diamond_pixel_bytes(width: int, height: int) -> int:
    """Return the expected diamond-scan byte count for a sprite of *width* × *height*.

    Returns ``width * height`` (row-major size) if the dimensions do not fit the
    diamond formula, so the result can be compared directly to the actual stride.
    """
    if height < 2 or height % 2 != 0:
        return width * height
    half = height // 2
    # Widest row = 4*(half-1)+2; must equal width for a valid diamond
    if 4 * (half - 1) + 2 != width:
        return width * height
    return half * (width + 2)


# ── Data model ────────────────────────────────────────────────────────────────


class BlitterType(IntEnum):
    """Blitter type from descriptor byte ``+0x0C`` (``extra[0]``).

    Determines how the game engine renders the sprite's pixel data:

    - ``FLAT``: row-major raster, no special encoding
    - ``DIAMOND``: standard isometric diamond tile (terrain)
    - ``EXT_DIAMOND``: diamond base + full-width body/roof extension
    - ``LEFT_ROOF``: diamond base + left-half building roof
    - ``RIGHT_ROOF``: diamond base + right-half building roof
    """

    FLAT = 0          # row-major, no diamond
    DIAMOND = 1       # standard diamond tile (terrain)
    EXT_DIAMOND = 2   # extended diamond: diamond base + body rows
    LEFT_ROOF = 3     # left-half building roof
    RIGHT_ROOF = 4    # right-half building roof



@dataclass
class SpriteDescriptor:
    """One 16-byte sprite descriptor entry from the `.PL8` descriptor table.

    ``sprite_start`` is the absolute byte offset of the sprite's pixel data
    within the `.PL8` file.  ``default_x`` / ``default_y`` give the sprite's
    default placement on the 640×480 screen (0 for runtime-positioned sprites).

    ``extra`` holds the 4 bytes at descriptor offset ``+0x0C``:
      - byte 0 (``+0x0C``): blitter type (0=flat, 1=diamond, 2=ext-diamond,
        3=left-roof, 4=right-roof)
      - byte 1 (``+0x0D``): extra_rows / y_len — body row count for types 2–4
      - bytes 2–3 (``+0x0E–0x0F``): always 0x0000

    These are preserved verbatim for byte-identical round-trips.
    """

    width: int
    height: int
    sprite_start: int  # absolute file offset (uint24)
    default_x: int = 0
    default_y: int = 0
    extra: bytes = b"\x00\x00\x00\x00"  # descriptor bytes +0x0C..+0x0F

    @property
    def pixel_count(self) -> int:
        """Total number of pixels (= bytes of pixel data) for this sprite."""
        return self.width * self.height


@dataclass
class PL8File:
    """Parsed representation of a Caesar II `.PL8` file.

    ``sprites`` is a list of ``SpriteDescriptor`` objects, one per sprite.
    ``pixel_data`` is a list of ``bytes`` objects, one per sprite, containing
    the raw 8-bit palette-indexed pixel data.

    ``group_boundary_index`` and ``file_id`` are tool metadata stored in the
    file header but **never read at runtime** by the game engine.

    Round-trip guarantee: ``serialise(parse(path)) == path.read_bytes()``.
    """

    zoom_level: int  # 0 = full detail, 1 = medium, 2 = small
    sprites: list[SpriteDescriptor] = field(default_factory=list)
    pixel_data: list[bytes] = field(default_factory=list)

    # Tool metadata (bytes 0x04–0x07) — preserved for round-trip but not used at runtime
    group_boundary_index: int = 0  # bytes 0x04–0x05
    file_id: int = 0               # byte 0x07

    @property
    def sprite_count(self) -> int:
        """Number of sprites in this file."""
        return len(self.sprites)


@dataclass
class VGAPalette:
    """A 256-entry VGA DAC palette loaded from a `.256` file.

    ``raw`` holds the original 6-bit values (0–63) as loaded from disk.
    Use ``as_rgb8()`` to get 8-bit RGB tuples suitable for PIL/PNG.
    """

    raw: list[tuple[int, int, int]]  # 256 × (r6, g6, b6)

    def as_rgb8(self) -> list[tuple[int, int, int]]:
        """Return palette as 8-bit RGB tuples (multiply each channel by 4)."""
        return [(r * 4, g * 4, b * 4) for r, g, b in self.raw]

    def as_flat_bytes(self) -> bytes:
        """Return palette as a flat bytes sequence suitable for PIL putpalette()."""
        out = bytearray(PALETTE_ENTRIES * 3)
        for i, (r, g, b) in enumerate(self.raw):
            out[i * 3]     = r * 4
            out[i * 3 + 1] = g * 4
            out[i * 3 + 2] = b * 4
        return bytes(out)


# ── Palette parser ────────────────────────────────────────────────────────────


def parse_palette(path: Path) -> VGAPalette:
    """Parse a 768-byte VGA palette file (`.256`).

    Raises:
        ValueError: if the file is not exactly 768 bytes.
        FileNotFoundError: if *path* does not exist.
    """
    data = path.read_bytes()
    if len(data) != PALETTE_FILE_SIZE:
        raise ValueError(
            f"{path.name}: expected {PALETTE_FILE_SIZE} bytes for a .256 palette, "
            f"got {len(data)}"
        )
    parsed = VGAPaletteSchema.parse(data)
    return VGAPalette(raw=[(e.r, e.g, e.b) for e in parsed])


def serialise_palette(pal: VGAPalette) -> bytes:
    """Serialise a ``VGAPalette`` back to its 768-byte binary representation."""
    return VGAPaletteSchema.build(
        [{"r": r, "g": g, "b": b} for r, g, b in pal.raw]
    )


# ── PL8 parser ────────────────────────────────────────────────────────────────


def parse(path: Path) -> PL8File:
    """Parse a Caesar II `.PL8` file from *path*.

    Raises:
        ValueError: if the file is malformed or truncated.
        FileNotFoundError: if *path* does not exist.
    """
    return parse_bytes(path.read_bytes(), path.name)


def parse_bytes(data: bytes, name: str = "<bytes>") -> PL8File:
    """Parse a Caesar II `.PL8` file from a ``bytes`` object."""
    if len(data) < HEADER_SIZE:
        raise ValueError(f"{name}: file too small ({len(data)} bytes), need {HEADER_SIZE}")

    # ── Construct parse: header + descriptor table + pixel area ───────────────
    parsed = PL8FileSchema.parse(data)
    hdr = parsed.header

    if hdr.zoom_level > 2:
        raise ValueError(f"{name}: zoom level {hdr.zoom_level} out of range (0–2)")

    sprites: list[SpriteDescriptor] = [
        SpriteDescriptor(
            width=d.width,
            height=d.height,
            sprite_start=d.sprite_start,
            default_x=d.default_x,
            default_y=d.default_y,
            extra=bytes(d.extra),
        )
        for d in parsed.descriptors
    ]

    # ── Pixel data ────────────────────────────────────────────────────────────
    # The authoritative byte count for each sprite is the stride to the next
    # sprite's sprite_start (or the remaining file bytes for the last sprite).
    # This handles all known cases:
    #
    #   - Normal sprites: stride == w*h (consecutive, no overlap)
    #   - Overlapping sprites (BUILD*.PL8): stride < w*h (sprites share bytes)
    #   - Diamond-encoded sprites (CITYFIXT/PROVFIXT/BATLFIX): stride == diamond_bytes < w*h
    #   - Last sprite: remaining file bytes (may be < w*h for any of the above)
    #
    # We clamp to the actual file size as a safety measure.
    pixel_data: list[bytes] = []
    for i, desc in enumerate(sprites):
        if i + 1 < len(sprites):
            actual_bytes = sprites[i + 1].sprite_start - desc.sprite_start
        else:
            actual_bytes = len(data) - desc.sprite_start
        # Clamp to file bounds (safety)
        actual_bytes = min(actual_bytes, len(data) - desc.sprite_start)
        pixel_data.append(data[desc.sprite_start : desc.sprite_start + actual_bytes])

    return PL8File(
        zoom_level=hdr.zoom_level,
        sprites=sprites,
        pixel_data=pixel_data,
        group_boundary_index=hdr.group_boundary_index,
        file_id=hdr.file_id,
    )


# ── PL8 serialiser ────────────────────────────────────────────────────────────


def serialise(pl8: PL8File) -> bytes:
    """Serialise a ``PL8File`` back to its binary representation.

    The output is binary-identical to the original file when the ``PL8File``
    was produced by ``parse()`` without modification.

    Raises:
        ValueError: if ``sprites`` and ``pixel_data`` lengths differ.
    """
    if len(pl8.sprites) != len(pl8.pixel_data):
        raise ValueError(
            f"sprites count ({len(pl8.sprites)}) != pixel_data count ({len(pl8.pixel_data)})"
        )

    n = pl8.sprite_count
    pixel_area_start = HEADER_SIZE + n * DESCRIPTOR_SIZE

    # ── Resolve sprite_start offsets ──────────────────────────────────────────
    # Use desc.sprite_start directly — it is always set correctly by the parser
    # and preserved verbatim in the sidecar.  This handles all cases:
    #   - consecutive sprites (normal files)
    #   - overlapping sprites (BUILD*.PL8 space-saving technique)
    #   - diamond-encoded sprites (CITYFIXT/PROVFIXT/BATLFIX, stride=900)
    #   - truncated last sprites (BUILD*.PL8 sentinel entries)
    # For newly-constructed PL8File objects (sprite_start == 0 for all sprites),
    # fall back to computing offsets consecutively.
    use_stored_offsets = any(desc.sprite_start != 0 for desc in pl8.sprites)
    starts: list[int] = []
    current_offset = pixel_area_start
    for desc, pixels in zip(pl8.sprites, pl8.pixel_data):
        starts.append(desc.sprite_start if use_stored_offsets else current_offset)
        current_offset += len(pixels)

    # ── Build header + descriptor table via Construct ─────────────────────────
    descriptor_dicts = [
        {
            "width": desc.width,
            "height": desc.height,
            "sprite_start": start,
            "default_x": desc.default_x,
            "default_y": desc.default_y,
            "extra": desc.extra if len(desc.extra) == 4 else b"\x00\x00\x00\x00",
        }
        for desc, start in zip(pl8.sprites, starts)
    ]

    # PL8FileSchema expects pixel_area but we assemble it manually for
    # overlapping-offset support, so build header + descriptors only.
    header_and_table = PL8HeaderSchema.build({
        "zoom_level": pl8.zoom_level,
        "sprite_count": n,
        "group_boundary_index": pl8.group_boundary_index,
        "file_id": pl8.file_id,
    }) + b"".join(
        SpriteDescriptorSchema.build(d) for d in descriptor_dicts
    )

    # ── Pixel data ────────────────────────────────────────────────────────────
    # When using stored offsets, we must write pixel data at the correct absolute
    # positions.  Build a sparse output buffer sized to hold all pixel data.
    if use_stored_offsets:
        max_end = max(
            desc.sprite_start + len(pixels)
            for desc, pixels in zip(pl8.sprites, pl8.pixel_data)
        )
        pixel_buf = bytearray(max_end - pixel_area_start)
        for desc, pixels in zip(pl8.sprites, pl8.pixel_data):
            rel = desc.sprite_start - pixel_area_start
            pixel_buf[rel : rel + len(pixels)] = pixels
        return header_and_table + bytes(pixel_buf)

    return header_and_table + b"".join(pl8.pixel_data)


def is_diamond_encoded(desc: SpriteDescriptor, pixel_bytes: int) -> bool:
    """Return True if this sprite uses diamond-scan encoding.

    A sprite is diamond-encoded when its actual stored byte count equals the
    diamond formula result for its declared (width, height).  This works for
    all three zoom levels:

      zoom 0 (full):   58×30 → 900 bytes
      zoom 1 (medium): 26×14 → 196 bytes
      zoom 2 (small):  10×6  →  36 bytes
    """
    expected = diamond_pixel_bytes(desc.width, desc.height)
    return expected != desc.pixel_count and pixel_bytes == expected


# ── Convenience I/O ───────────────────────────────────────────────────────────


def write(pl8_file: PL8File, path: Path) -> None:
    """Serialise *pl8_file* and write it to *path*."""
    path.write_bytes(serialise(pl8_file))

