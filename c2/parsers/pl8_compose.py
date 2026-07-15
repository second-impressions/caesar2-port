"""Isometric tile codec and sprite composition for Caesar II `.PL8` files.

This module handles the high-level operations that combine the diamond and
body codecs to decode/encode complete isometric tiles, and the composition
of multiple sprites onto a shared canvas (and its inverse, decomposition).

Functions
---------
decode_iso_tile
    Decode a complete isometric tile (diamond base + roof/body extension)
    into a row-major pixel canvas.
encode_iso_tile
    Encode a row-major canvas back to raw PL8 pixel bytes (inverse of
    ``decode_iso_tile``).
compose_sprites
    Compose a group of sprites into a single canvas using their screen
    positions.
decompose_sprites
    Recover per-sprite raw PL8 pixel data from a composed canvas (inverse
    of ``compose_sprites``).

Lossy re-encoding
-----------------
Re-encoding from a composed canvas is **not** binary-identical to the
original ``.PL8``.  Files with overlapping sprite bounding boxes (e.g.
``BUILD*.PL8``) will differ at overlap positions because composition is
last-writer-wins.  The visual result is identical in all tested cases.

Reference: data/docs/pl8-format.md
"""

from __future__ import annotations

from .pl8 import BlitterType, PL8File, SpriteDescriptor, diamond_pixel_bytes


# ── Isometric tile decoder (C++ isoTile port) ────────────────────────────────
#
# Ported from the C++ ``isoTile()`` function in the LOTR2 parser.  This decodes
# a complete isometric tile — diamond base + roof/body extension — into a single
# row-major pixel buffer.  The roof extends ABOVE the diamond base, so the
# returned canvas is taller than the declared height.
#
# The C++ logic for the roof zigzag scan (types 2, 3, 4):
#   for y_ in range(extraRows, 0, -1):
#     leftOffset  = halfWidth-1 if type==4 else 0
#     rightOffset = halfWidth+1 if type==3 else width
#     for x in range(leftOffset, rightOffset):
#       y = (y_ + halfHeight-1 - x//2) if x <= halfWidth else (y_ + x//2 - halfHeight+1)
#       pixel[y * width + x] = data[src++]


def decode_iso_tile(
    pixels: bytes,
    width: int,
    height: int,
    blitter: BlitterType,
    extra_rows: int,
) -> tuple[bytes, int, int]:
    """Decode an isometric tile (diamond base + roof) into a row-major canvas.

    Returns ``(canvas_bytes, canvas_width, canvas_height)`` where the canvas
    includes the roof extension above the diamond base.

    The diamond base occupies the bottom ``height`` rows of the canvas.
    The roof extension occupies the top ``extra_rows`` rows.

    Raises ``ValueError`` if the pixel data is too short.
    """
    if blitter == BlitterType.FLAT:
        # Flat / orthogonal — no diamond encoding
        return (pixels, width, height)

    half_width = width // 2
    half_height = height // 2
    diamond_bytes = diamond_pixel_bytes(width, height)

    # Total canvas height = extra_rows + height (roof above diamond)
    canvas_h = extra_rows + height
    canvas_w = width
    out = bytearray(canvas_h * canvas_w)  # zero-filled (transparent)

    # ── Decode diamond base into the lower portion ────────────────────────
    # Diamond base starts at canvas row `extra_rows`
    src = 0
    if len(pixels) < diamond_bytes:
        raise ValueError(
            f"decode_iso_tile: need {diamond_bytes} bytes for diamond base, "
            f"got {len(pixels)}"
        )

    # Top half of diamond
    for row in range(half_height):
        row_width = 4 * row + 2
        col_start = (half_width - 1) - 2 * row
        canvas_row = extra_rows + row
        dst = canvas_row * canvas_w + col_start
        out[dst : dst + row_width] = pixels[src : src + row_width]
        src += row_width

    # Bottom half of diamond
    for row in range(half_height, height):
        row_width = 4 * (height - 1 - row) + 2
        col_start = 2 * (row - half_height)
        canvas_row = extra_rows + row
        dst = canvas_row * canvas_w + col_start
        out[dst : dst + row_width] = pixels[src : src + row_width]
        src += row_width

    # ── Decode roof/body extension above the diamond ──────────────────────
    if blitter in (BlitterType.EXT_DIAMOND, BlitterType.LEFT_ROOF, BlitterType.RIGHT_ROOF) and extra_rows > 0 and len(pixels) > diamond_bytes:
        roof_data = pixels[diamond_bytes:]
        roof_src = 0

        # Determine column bounds based on blitter type
        left_offset = half_width - 1 if blitter == BlitterType.RIGHT_ROOF else 0
        right_offset = half_width + 1 if blitter == BlitterType.LEFT_ROOF else width

        for y_ in range(extra_rows, 0, -1):
            for x in range(left_offset, right_offset):
                if roof_src >= len(roof_data):
                    break
                # Zigzag y calculation from C++ isoTile
                if x <= half_width:
                    y = y_ + (half_height - 1) - (x // 2)
                else:
                    y = y_ + (x // 2) - (half_height - 1)

                value = roof_data[roof_src]
                roof_src += 1

                if 0 <= y < canvas_h and value != 0:
                    out[y * canvas_w + x] = value

    return (bytes(out), canvas_w, canvas_h)


# ── Isometric tile encoder (inverse of decode_iso_tile) ───────────────────────


def encode_iso_tile(
    canvas: bytes,
    width: int,
    height: int,
    blitter: BlitterType,
    extra_rows: int,
) -> bytes:
    """Encode a row-major canvas back to raw PL8 pixel bytes.

    This is the exact inverse of ``decode_iso_tile``.  Given a decoded canvas
    (as produced by ``decode_iso_tile``), it recovers the packed pixel data
    suitable for storage in a ``.PL8`` file.

    Raises ``ValueError`` if the canvas is not the expected size.
    """
    if blitter == BlitterType.FLAT:
        # Flat / orthogonal — no diamond encoding
        expected = width * height
        if len(canvas) != expected:
            raise ValueError(
                f"encode_iso_tile: expected {expected} bytes for flat {width}×{height}, "
                f"got {len(canvas)}"
            )
        return canvas if isinstance(canvas, bytes) else bytes(canvas)

    half_width = width // 2
    half_height = height // 2

    # Total canvas height = extra_rows + height (roof above diamond)
    canvas_h = extra_rows + height
    canvas_w = width
    expected = canvas_h * canvas_w
    if len(canvas) != expected:
        raise ValueError(
            f"encode_iso_tile: expected {expected} bytes for {canvas_w}×{canvas_h} canvas "
            f"(blitter={blitter.name}, extra_rows={extra_rows}), got {len(canvas)}"
        )

    # ── Encode diamond base from the lower portion ────────────────────────
    # Diamond base occupies canvas rows [extra_rows .. extra_rows+height)
    diamond_bytes_count = diamond_pixel_bytes(width, height)
    diamond_out = bytearray(diamond_bytes_count)
    dst = 0

    # Top half of diamond
    for row in range(half_height):
        row_width = 4 * row + 2
        col_start = (half_width - 1) - 2 * row
        canvas_row = extra_rows + row
        src = canvas_row * canvas_w + col_start
        diamond_out[dst : dst + row_width] = canvas[src : src + row_width]
        dst += row_width

    # Bottom half of diamond
    for row in range(half_height, height):
        row_width = 4 * (height - 1 - row) + 2
        col_start = 2 * (row - half_height)
        canvas_row = extra_rows + row
        src = canvas_row * canvas_w + col_start
        diamond_out[dst : dst + row_width] = canvas[src : src + row_width]
        dst += row_width

    if blitter == BlitterType.DIAMOND:
        # Diamond only — no roof data
        return bytes(diamond_out)

    # ── Encode roof/body extension from above the diamond ─────────────────
    left_offset = half_width - 1 if blitter == BlitterType.RIGHT_ROOF else 0
    right_offset = half_width + 1 if blitter == BlitterType.LEFT_ROOF else width

    # Count expected roof bytes: same iteration order as decode
    roof_byte_count = 0
    for y_ in range(extra_rows, 0, -1):
        roof_byte_count += right_offset - left_offset

    roof_out = bytearray(roof_byte_count)
    roof_dst = 0

    for y_ in range(extra_rows, 0, -1):
        for x in range(left_offset, right_offset):
            # Zigzag y calculation from C++ isoTile (same as decode)
            if x <= half_width:
                y = y_ + (half_height - 1) - (x // 2)
            else:
                y = y_ + (x // 2) - (half_height - 1)

            if 0 <= y < canvas_h:
                roof_out[roof_dst] = canvas[y * canvas_w + x]
            # else: stays 0 (transparent)
            roof_dst += 1

    return bytes(diamond_out) + bytes(roof_out)


# ── Sprite composition ────────────────────────────────────────────────────────


def compose_sprites(
    pl8: PL8File,
    group_start: int = 0,
    group_end: int | None = None,
) -> tuple[bytes, int, int]:
    """Compose a group of sprites into a single canvas using their screen positions.

    Each sprite is decoded (diamond + roof if applicable) and placed at its
    ``(default_x, default_y - extra_rows)`` position on a shared canvas.
    The canvas size is computed from the bounding box of all placed sprites.

    Returns ``(canvas_bytes, canvas_width, canvas_height)``.

    This implements the same logic as the C++ ``convertPL8()`` / ``emplaceTile()``
    and TypeScript ``GraphicFactory.tiles()`` functions from the LOTR2 parsers.
    """
    if group_end is None:
        group_end = len(pl8.sprites)

    sprites = pl8.sprites[group_start:group_end]
    pixel_data = pl8.pixel_data[group_start:group_end]

    if not sprites:
        return (b"\x00", 1, 1)

    # First pass: decode all tiles and compute bounding box
    decoded: list[tuple[bytes, int, int, int, int]] = []  # (pixels, w, h, x, y)
    max_right = 0
    max_bottom = 0

    for desc, pixels in zip(sprites, pixel_data):
        blitter = BlitterType(desc.extra[0]) if desc.extra and len(desc.extra) >= 1 and desc.extra[0] <= BlitterType.RIGHT_ROOF else BlitterType.FLAT
        extra_rows = desc.extra[1] if desc.extra and len(desc.extra) >= 2 else 0

        # Only use extra_rows for extended blitter types
        if blitter not in (BlitterType.EXT_DIAMOND, BlitterType.LEFT_ROOF, BlitterType.RIGHT_ROOF):
            extra_rows = 0

        tile_pixels, tile_w, tile_h = decode_iso_tile(
            pixels, desc.width, desc.height, blitter, extra_rows,
        )

        # Place at (default_x, default_y - extra_rows)
        place_x = desc.default_x
        place_y = desc.default_y - extra_rows

        decoded.append((tile_pixels, tile_w, tile_h, place_x, place_y))

        right = place_x + tile_w
        bottom = place_y + tile_h
        if right > max_right:
            max_right = right
        if bottom > max_bottom:
            max_bottom = bottom

    # Shift all sprites so the bounding box starts at (0, 0).
    # This removes wasted transparent space for single-sprite files where
    # default_x/default_y represent a screen position rather than a
    # composition offset, while preserving relative placement for
    # multi-sprite building files.
    min_x = min(d[3] for d in decoded)
    min_y = min(d[4] for d in decoded)
    if min_x != 0 or min_y != 0:
        decoded = [(p, w, h, x - min_x, y - min_y) for p, w, h, x, y in decoded]
        max_right -= min_x
        max_bottom -= min_y

    canvas_w = max_right
    canvas_h = max_bottom
    if canvas_w <= 0 or canvas_h <= 0:
        return (b"\x00", 1, 1)

    out = bytearray(canvas_w * canvas_h)

    # Second pass: blit each decoded tile onto the canvas
    for tile_pixels, tile_w, tile_h, place_x, place_y in decoded:
        for row in range(tile_h):
            canvas_row = place_y + row
            if canvas_row < 0 or canvas_row >= canvas_h:
                continue
            for col in range(tile_w):
                canvas_col = place_x + col
                if canvas_col < 0 or canvas_col >= canvas_w:
                    continue
                src_idx = row * tile_w + col
                if src_idx < len(tile_pixels):
                    value = tile_pixels[src_idx]
                    if value != 0:  # skip transparent pixels
                        out[canvas_row * canvas_w + canvas_col] = value

    return (bytes(out), canvas_w, canvas_h)


# ── Sprite decomposition (inverse of compose_sprites) ─────────────────────────


def decompose_sprites(
    canvas: bytes,
    canvas_w: int,
    canvas_h: int,
    sprites: list[SpriteDescriptor],
) -> list[bytes]:
    """Recover per-sprite raw PL8 pixel data from a composed canvas.

    This is the inverse of ``compose_sprites``.  Given the composed canvas
    (as stored in the PNG) and the sprite descriptors, it extracts each
    sprite's region from the canvas and re-encodes it to the original PL8
    pixel format.

    The function replicates the same placement logic as ``compose_sprites``
    (including the min_x/min_y origin shift) to determine where each sprite
    sits on the canvas, then crops and re-encodes each one independently.

    **Overlap handling**: When sprites have overlapping bounding boxes on the
    canvas, transparent pixels (index 0) in one sprite's region may have been
    overwritten by another sprite during composition.  For diamond-encoded
    sprites this is harmless because ``encode_diamond`` only reads pixels
    within the diamond shape (corners are always transparent).  For flat
    sprites (type 0), any overlap at transparent positions will produce
    different bytes than the original — but this only affects index-0 pixels
    which are transparent and visually identical.

    Returns a list of ``bytes`` objects, one per sprite, in the same order
    as *sprites*.

    Raises ``ValueError`` if the canvas dimensions don't match expectations.
    """
    if not sprites:
        return []

    # ── Replicate placement logic from compose_sprites ────────────────────
    placements: list[tuple[int, int, int, int, BlitterType, int]] = []
    # (place_x, place_y, tile_w, tile_h, blitter, extra_rows)

    for desc in sprites:
        blitter = BlitterType(desc.extra[0]) if desc.extra and len(desc.extra) >= 1 and desc.extra[0] <= BlitterType.RIGHT_ROOF else BlitterType.FLAT
        extra_rows = desc.extra[1] if desc.extra and len(desc.extra) >= 2 else 0

        # Only use extra_rows for extended blitter types
        if blitter not in (BlitterType.EXT_DIAMOND, BlitterType.LEFT_ROOF, BlitterType.RIGHT_ROOF):
            extra_rows = 0

        if blitter == BlitterType.FLAT:
            tile_w = desc.width
            tile_h = desc.height
        else:
            tile_w = desc.width
            tile_h = extra_rows + desc.height

        place_x = desc.default_x
        place_y = desc.default_y - extra_rows

        placements.append((place_x, place_y, tile_w, tile_h, blitter, extra_rows))

    # Apply the same min_x/min_y origin shift as compose_sprites
    min_x = min(p[0] for p in placements)
    min_y = min(p[1] for p in placements)
    if min_x != 0 or min_y != 0:
        placements = [
            (px - min_x, py - min_y, tw, th, bt, er)
            for px, py, tw, th, bt, er in placements
        ]

    # ── Extract and re-encode each sprite ─────────────────────────────────
    result: list[bytes] = []

    for desc, (place_x, place_y, tile_w, tile_h, bt, extra_rows) in zip(
        sprites, placements
    ):
        # Crop the sprite's region from the canvas into a local tile buffer
        tile_buf = bytearray(tile_w * tile_h)

        for row in range(tile_h):
            canvas_row = place_y + row
            if canvas_row < 0 or canvas_row >= canvas_h:
                continue
            for col in range(tile_w):
                canvas_col = place_x + col
                if canvas_col < 0 or canvas_col >= canvas_w:
                    continue
                src_idx = canvas_row * canvas_w + canvas_col
                if src_idx < len(canvas):
                    tile_buf[row * tile_w + col] = canvas[src_idx]

        # Re-encode using the appropriate codec
        raw_pixels = encode_iso_tile(
            bytes(tile_buf), desc.width, desc.height, bt, extra_rows,
        )
        result.append(raw_pixels)

    return result
