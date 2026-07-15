"""Diamond-scan and building-body codecs for Caesar II `.PL8` sprites.

These codecs handle the two non-trivial pixel encodings used by the game:

Diamond-scan encoding
    Used for isometric terrain tiles at all three zoom levels.  Pixels are
    stored in diamond-scan order (widest row in the middle, narrowing to a
    point at top and bottom).  The ``decode_diamond`` / ``encode_diamond``
    functions convert between this packed format and a standard row-major
    pixel buffer.

Building-body encoding
    Used for the rectangular body portion of building sprites (types 2–4).
    At zoom 0 (width=58), the body is stored in a triangular-scan order
    derived from ``write_large_diamond_roof`` in PS.EXE.  At zoom 1/2
    (width < 58), the body bytes are already row-major.

Reference: data/docs/pl8-format.md
"""

from __future__ import annotations

from .pl8 import diamond_pixel_bytes


# ── Diamond-scan codec ────────────────────────────────────────────────────────


def _diamond_row_layout_wh(row: int, width: int, height: int) -> tuple[int, int]:
    """Return ``(col_start, row_width)`` for *row* in a *width* × *height* diamond.

    Works for any valid diamond dimensions (height even, width = 4*(height//2-1)+2).

    Derived from ``place_i_large_diamond`` assembly in PS.EXE:
      top half    (row 0 .. H//2-1): row_width = 4*row + 2,
                                     col_start = (W//2 - 1) - 2*row
      bottom half (row H//2 .. H-1): row_width = 4*(H-1-row) + 2,
                                     col_start = 2*(row - H//2)
    """
    half = height // 2
    if row < half:
        row_width = 4 * row + 2
        col_start = (width // 2 - 1) - 2 * row
    else:
        row_width = 4 * (height - 1 - row) + 2
        col_start = 2 * (row - half)
    return col_start, row_width


def decode_diamond(pixels: bytes, width: int = 58, height: int = 30) -> bytes:
    """Decode diamond-scan bytes into a *width* × *height* row-major pixel buffer.

    The returned buffer is ``width * height`` bytes.
    Pixels outside the diamond shape are filled with index 0 (transparent).

    Works for all zoom levels (58×30, 26×14, 10×6).

    Raises ``ValueError`` if *pixels* length does not match the expected diamond
    byte count for the given dimensions.
    """
    expected = diamond_pixel_bytes(width, height)
    if len(pixels) != expected:
        raise ValueError(
            f"decode_diamond: expected {expected} bytes for {width}×{height}, "
            f"got {len(pixels)}"
        )

    out = bytearray(width * height)  # zero-filled (transparent)
    src = 0
    for row in range(height):
        col_start, row_width = _diamond_row_layout_wh(row, width, height)
        dst = row * width + col_start
        out[dst : dst + row_width] = pixels[src : src + row_width]
        src += row_width
    return bytes(out)


def encode_diamond(pixels: bytes, width: int = 58, height: int = 30) -> bytes:
    """Encode a *width* × *height* row-major pixel buffer to diamond-scan bytes.

    This is the inverse of ``decode_diamond``.  Only the pixels within the
    diamond shape are written; corner pixels (which must be index 0) are
    discarded.

    Works for all zoom levels (58×30, 26×14, 10×6).

    Raises ``ValueError`` if *pixels* is not exactly ``width * height`` bytes.
    """
    expected_in = width * height
    if len(pixels) != expected_in:
        raise ValueError(
            f"encode_diamond: expected {expected_in} bytes for {width}×{height}, "
            f"got {len(pixels)}"
        )

    diamond_bytes = diamond_pixel_bytes(width, height)
    out = bytearray(diamond_bytes)
    dst = 0
    for row in range(height):
        col_start, row_width = _diamond_row_layout_wh(row, width, height)
        src = row * width + col_start
        out[dst : dst + row_width] = pixels[src : src + row_width]
        dst += row_width
    return bytes(out)


# ── Building body codec ───────────────────────────────────────────────────────
#
# Derived from ``write_large_diamond_roof`` in PS.EXE (screen_width=320).
#
# The body data is stored as y_len × 58 bytes (zoom 0).  Each 58-byte chunk n
# (0-indexed) encodes a triangular slice of the roof diamond.  All chunks share
# the same "base row" on screen; chunk n writes to abs_rows in the range
# [−n, +n] (every other row), centred on the base row.
#
# Within chunk n the active bytes occupy positions [28−2n .. 28+2n+1] (the rest
# are padding zeros).  Pair p (0 ≤ p ≤ 2n) within the active region maps to:
#   abs_row = n − 2p          (for p ≤ n)
#   abs_row = 2(p−n) − n      (for p > n)
#   col     = 28 − 2n + 2p + bit   (bit = 0 or 1 within the pair)
#
# The canvas is (2·y_len − 1) rows × 58 cols.  The base row sits at canvas row
# (y_len − 1).  Chunk 0 contributes only the base row; chunk y_len−1 contributes
# rows 0 and 2·y_len−2 (the outermost edges).
#
# For zoom 1/2 (width < 58) the body bytes are already row-major (y_len rows of
# width bytes each) and no remapping is needed.

_BODY_CHUNK_COLS_Z0 = 58  # sprite width at zoom 0


def _body_chunk_byte_to_rc(n: int, b: int) -> tuple[int, int] | None:
    """Map byte *b* of chunk *n* to (abs_row, col), or ``None`` for padding.

    *abs_row* is relative to the shared base row (positive = below, negative = above).
    *col* is the screen column within the 58-pixel-wide sprite.
    """
    start = 28 - 2 * n
    end = 28 + 2 * n + 1
    if b < start or b > end:
        return None  # padding byte
    local = b - start          # 0-indexed within active region
    p = local >> 1             # pair index
    bit = local & 1            # 0 = left byte of pair, 1 = right byte
    abs_row = (n - 2 * p) if p <= n else (2 * (p - n) - n)
    col = start + 2 * p + bit
    return (abs_row, col)


def body_canvas_height(y_len: int, width: int = 58) -> int:
    """Return the canvas height needed to display *y_len* body chunks.

    For zoom 0 (width=58) the roof diamond spans ``2·y_len − 1`` rows.

    For zoom 1/2 (width < 58) the body bytes are stored as simple row-major
    rows of *width* bytes each, so the canvas height is simply *y_len*.
    """
    if y_len <= 0:
        return 0
    if width == _BODY_CHUNK_COLS_Z0:
        return 2 * y_len - 1
    return y_len


def decode_body(body_bytes: bytes, y_len: int, width: int = 58) -> bytes:
    """Decode *y_len* × *width* body bytes into a row-major pixel canvas.

    For zoom 0 (width=58) the body is stored in triangular-scan order
    (``write_large_diamond_roof`` in PS.EXE).  The canvas is
    ``(2·y_len − 1) × 58`` pixels; the base row is at canvas row ``y_len − 1``.

    For zoom 1/2 (width < 58) the body bytes are already row-major
    (*y_len* rows of *width* bytes), so the canvas is simply *y_len* × *width*.

    Raises ``ValueError`` if ``len(body_bytes) != y_len * width``.
    """
    expected = y_len * width
    if len(body_bytes) != expected:
        raise ValueError(
            f"decode_body: expected {expected} bytes for y_len={y_len} width={width}, "
            f"got {len(body_bytes)}"
        )
    canvas_h = body_canvas_height(y_len, width)
    out = bytearray(canvas_h * width)

    if width == _BODY_CHUNK_COLS_Z0:
        # Zoom 0: triangular-scan decode.
        # All chunks share the same base row at canvas row (y_len - 1).
        base_row = y_len - 1
        for chunk_idx in range(y_len):
            chunk_start = chunk_idx * width
            for b in range(width):
                rc = _body_chunk_byte_to_rc(chunk_idx, b)
                if rc is None:
                    continue
                abs_row, col = rc
                canvas_row = base_row + abs_row
                if 0 <= canvas_row < canvas_h:
                    out[canvas_row * width + col] = body_bytes[chunk_start + b]
    else:
        # Zoom 1/2: body bytes are already row-major; copy directly.
        out[:] = body_bytes

    return bytes(out)


def encode_body(canvas: bytes, y_len: int, width: int = 58) -> bytes:
    """Encode a body canvas back to *y_len* × *width* raw body bytes.

    This is the exact inverse of ``decode_body``.

    Raises ``ValueError`` if *canvas* is not the expected size.
    """
    canvas_h = body_canvas_height(y_len, width)
    expected = canvas_h * width
    if len(canvas) != expected:
        raise ValueError(
            f"encode_body: expected {expected} bytes for y_len={y_len} width={width} "
            f"(canvas {canvas_h}×{width}), got {len(canvas)}"
        )
    out = bytearray(y_len * width)

    if width == _BODY_CHUNK_COLS_Z0:
        # Zoom 0: re-encode from canvas back to triangular-scan order.
        base_row = y_len - 1
        for chunk_idx in range(y_len):
            chunk_start = chunk_idx * width
            for b in range(width):
                rc = _body_chunk_byte_to_rc(chunk_idx, b)
                if rc is None:
                    continue
                abs_row, col = rc
                canvas_row = base_row + abs_row
                if 0 <= canvas_row < canvas_h:
                    out[chunk_start + b] = canvas[canvas_row * width + col]
    else:
        # Zoom 1/2: canvas is already row-major; copy directly.
        out[:] = canvas

    return bytes(out)
