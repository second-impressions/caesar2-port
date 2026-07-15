"""image command group: export and import Caesar II `.PL8` sprite files.

Sub-commands
------------
show      Parse and display metadata from a `.PL8` file.
export    Convert a `.PL8` + `.256` palette to an indexed PNG atlas + JSON sidecar.
import    Reconstruct a `.PL8` + `.256` from an indexed PNG atlas + JSON sidecar.

Round-trip guarantee
--------------------
``import(export(file, palette))`` produces byte-for-byte identical `.PL8` and
`.256` files when neither the PNG nor the JSON has been modified.

Format notes
------------
The PNG is written as colour type 3 (indexed, PLTE chunk) with a ``tRNS`` chunk
marking palette index 0 as fully transparent.  The JSON sidecar stores all
metadata that PNG cannot hold: per-sprite positions, zoom level, group boundary
index, and the original 6-bit VGA DAC palette values for lossless round-trip.

Reference: docs/pl8-format.md, plans/pl8-image-conversion.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer

from c2.parsers.pl8 import (
    PALETTE_ENTRIES,
    PL8File,
    SpriteDescriptor,
    VGAPalette,
    diamond_pixel_bytes as _diamond_pixel_bytes,
    is_diamond_encoded,
    parse as parse_pl8,
    parse_palette,
    serialise as serialise_pl8,
    serialise_palette,
)


def _body_canvas_height(y_len: int, width: int) -> int:
    """Compute the canvas height for the body section of an extended diamond."""
    if width == 0:
        return 0
    return (y_len + width - 1) // width


def decode_body(data: bytes, width: int, height: int) -> bytes:
    """Decode body pixel data (identity - raw pixels)."""
    return data


def decode_diamond(data: bytes, width: int, height: int) -> bytes:
    """Decode diamond-encoded pixel data (stub)."""
    return data


def encode_diamond(pixels: bytes, width: int, height: int) -> bytes:
    """Encode pixels into diamond format (stub)."""
    return pixels

# ── Typer sub-application ─────────────────────────────────────────────────────

app = typer.Typer(
    name="image",
    help="Export and import Caesar II `.PL8` sprite files.",
    no_args_is_help=True,
)

# ── Sprite display-dimension helpers ─────────────────────────────────────────


# Bytes per body row for each sprite type at zoom level 0 (58×30 diamond)
_BODY_ROW_BYTES = {
    2: 58,  # full-width building body (type 2 extended diamond)
    3: 30,  # left-half building body
    4: 30,  # right-half building body
}


def _sprite_type(desc: "SpriteDescriptor") -> int:
    """Return the blitter type from ``desc.extra[0]`` (1–4), or 0 if unknown."""
    if desc.extra and len(desc.extra) >= 1:
        t = desc.extra[0]
        if 1 <= t <= 4:
            return t
    return 0


def _display_dims(desc: "SpriteDescriptor", pixel_bytes: int) -> tuple[int, int]:
    """Return the ``(display_width, display_height)`` for a sprite.

    Caesar II `.PL8` sprites always declare ``width=58, height=30`` (or the
    zoom-level equivalent) in their descriptor.  The actual pixel data layout
    depends on the blitter type stored in ``desc.extra[0]``:

    * **Type 1** – standard 900-byte diamond terrain tile → display as w×h.
    * **Type 2** – extended diamond: 900B base + ``y_len × 58`` body rows →
      display as w×(h + y_len).
    * **Type 3** – left-half: 900B diamond base + ``y_len × 30`` body bytes →
      display as w×h (body data is in diagonal scan order, not row-major).
    * **Type 4** – right-half: same as type 3.
    * **Other / unknown** – fall back to declared w×h.
    """
    w, h = desc.width, desc.height
    t = _sprite_type(desc)
    diamond_bytes = _diamond_pixel_bytes(w, h)

    if t == 2:
        # Extended diamond: diamond base + y_len * w body bytes.
        # y_len is stored in extra[1]; body canvas is placed ABOVE the diamond.
        # Total display height = body_canvas_height + h.
        y_len = desc.extra[1] if desc.extra and len(desc.extra) >= 2 else 0
        if y_len > 0:
            canvas_h = _body_canvas_height(y_len, w)
            return (w, canvas_h + h)
        return (w, h)

    if t in (1, 3, 4):
        # Standard diamond base (type 1) or diamond + body data (type 3/4)
        # In all cases display as the declared w×h (decoded diamond only)
        return (w, h)

    # Fallback: use declared dimensions
    return (w, h)


# ── Atlas packing helpers ─────────────────────────────────────────────────────


def _pack_atlas(
    sprites: list["SpriteDescriptor"],
    pixel_sizes: list[int],
) -> tuple[int, int, list[tuple[int, int]]]:
    """Compute a shelf-packed atlas layout for *sprites*.

    Sprites are placed left-to-right in a single row (shelf).  The atlas width
    is the sum of all display widths; the atlas height is the maximum display
    height.  Display dimensions are computed from the actual pixel data size
    (not the declared descriptor dimensions) so that building body sprites and
    extended diamond tiles are shown at their correct size.

    Returns ``(atlas_width, atlas_height, positions)`` where ``positions[i]``
    is the ``(x, y)`` top-left corner of sprite *i* in the atlas.
    """
    if not sprites:
        return (1, 1, [])

    positions: list[tuple[int, int]] = []
    x = 0
    max_h = 0
    for desc, psize in zip(sprites, pixel_sizes):
        dw, dh = _display_dims(desc, psize)
        positions.append((x, 0))
        x += dw
        if dh > max_h:
            max_h = dh

    return (x, max_h, positions)


# ── JSON sidecar helpers ──────────────────────────────────────────────────────


def _build_sidecar(
    pl8: PL8File,
    palette: VGAPalette,
    positions: list[tuple[int, int]],
    source_pl8_name: str,
    palette_source_name: str,
) -> dict:
    """Build the JSON sidecar document for a `.PL8` export."""
    sprites_list = []
    for i, (desc, pixels, (ax, ay)) in enumerate(zip(pl8.sprites, pl8.pixel_data, positions)):
        diamond = is_diamond_encoded(desc, len(pixels))
        dw, dh = _display_dims(desc, len(pixels))
        t = _sprite_type(desc)
        diamond_bytes = _diamond_pixel_bytes(desc.width, desc.height)
        # body_hex: extra body/roof bytes beyond the 900-byte diamond base, stored as hex.
        # Used for type 2/3/4 sprites where pixel_bytes > diamond_bytes.
        # These bytes are in a special diagonal scan order and are preserved verbatim.
        body_hex: str = ""
        if t in (2, 3, 4) and len(pixels) > diamond_bytes:
            body_hex = pixels[diamond_bytes:].hex()
        sprites_list.append({
            "index": i,
            "screen_x": desc.default_x,
            "screen_y": desc.default_y,
            "width": desc.width,
            "height": desc.height,
            "atlas_x": ax,
            "atlas_y": ay,
            # sprite_start: original absolute file offset — required for round-trip because
            # some BUILD*.PL8 files use overlapping pixel data (sprites share bytes).
            "sprite_start": desc.sprite_start,
            # pixel_bytes: actual stored byte count (may differ from width*height).
            "pixel_bytes": len(pixels),
            # display_width / display_height: dimensions used in the atlas PNG.
            # For type 1/3/4: same as width/height (decoded diamond only).
            # For type 2 (extended diamond): width × (height + extra_rows).
            "display_width": dw,
            "display_height": dh,
            # diamond_encoded: True for CITYFIXT/PROVFIXT/BATLFIX terrain tile sprites
            # whose pixel data is stored in diamond-scan order (900 bytes, not 1740).
            # The atlas PNG stores the decoded w×h row-major image; import re-encodes.
            "diamond_encoded": diamond,
            # extra: descriptor bytes +0x0C..+0x0F as a hex string (not always zero).
            # Encodes blitter type (extra[0]: 1=diamond, 2=ext-diamond, 3=left-half, 4=right-half)
            # and y_length (extra[1]: number of body/roof rows).
            "extra": desc.extra.hex(),
            # body_hex: body/roof bytes beyond the 900-byte diamond (type 2/3/4 only).
            # Stored verbatim as hex; empty string for type 1 and non-building sprites.
            "body_hex": body_hex,
        })

    return {
        "source_file": source_pl8_name,
        "zoom_level": pl8.zoom_level,
        "group_boundary_index": pl8.group_boundary_index,
        "file_id": pl8.file_id,
        "palette_source": palette_source_name,
        "palette_vga_raw": [list(entry) for entry in palette.raw],
        "sprites": sprites_list,
    }


def _pl8_from_sidecar(
    doc: dict,
    png_data: bytes,
    json_path: Path,
) -> tuple[PL8File, VGAPalette]:
    """Reconstruct a ``PL8File`` and ``VGAPalette`` from a JSON sidecar + PNG bytes.

    Raises ``ValueError`` with a descriptive message on any schema violation.
    """
    # ── Validate top-level keys ───────────────────────────────────────────────
    for key in ("zoom_level", "group_boundary_index", "file_id",
                "palette_vga_raw", "sprites"):
        if key not in doc:
            raise ValueError(f"{json_path}: missing required key '{key}'")

    zoom_level = doc["zoom_level"]
    if not isinstance(zoom_level, int) or zoom_level not in (0, 1, 2):
        raise ValueError(f"{json_path}: zoom_level must be 0, 1, or 2, got {zoom_level!r}")

    group_boundary_index = doc["group_boundary_index"]
    if not isinstance(group_boundary_index, int):
        raise ValueError(f"{json_path}: group_boundary_index must be an integer")

    file_id = doc["file_id"]
    if not isinstance(file_id, int) or not (0 <= file_id <= 15):
        raise ValueError(f"{json_path}: file_id must be an integer 0–15, got {file_id!r}")

    # ── Palette ───────────────────────────────────────────────────────────────
    raw_pal = doc["palette_vga_raw"]
    if not isinstance(raw_pal, list) or len(raw_pal) != PALETTE_ENTRIES:
        raise ValueError(
            f"{json_path}: palette_vga_raw must be a list of {PALETTE_ENTRIES} entries"
        )
    pal_entries: list[tuple[int, int, int]] = []
    for i, entry in enumerate(raw_pal):
        if not isinstance(entry, list) or len(entry) != 3:
            raise ValueError(f"{json_path}: palette_vga_raw[{i}] must be [r, g, b]")
        r, g, b = entry
        for ch_name, ch_val in (("r", r), ("g", g), ("b", b)):
            if not isinstance(ch_val, int) or not (0 <= ch_val <= 63):
                raise ValueError(
                    f"{json_path}: palette_vga_raw[{i}].{ch_name} must be 0–63, "
                    f"got {ch_val!r}"
                )
        pal_entries.append((r, g, b))
    palette = VGAPalette(raw=pal_entries)

    # ── Sprites ───────────────────────────────────────────────────────────────
    raw_sprites = doc["sprites"]
    if not isinstance(raw_sprites, list):
        raise ValueError(f"{json_path}: 'sprites' must be a JSON array")

    # Load the PNG to extract pixel data per sprite
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "Pillow is required for image import.  Install it with: "
            "uv add pillow"
        )

    import io
    png_img = Image.open(io.BytesIO(png_data))
    if png_img.mode != "P":
        raise ValueError(
            f"{json_path}: companion PNG must be indexed (mode P), got {png_img.mode!r}"
        )
    png_pixels = png_img.tobytes()
    atlas_w, atlas_h = png_img.size

    sprites: list[SpriteDescriptor] = []
    pixel_data_list: list[bytes] = []

    for i, entry in enumerate(raw_sprites):
        if not isinstance(entry, dict):
            raise ValueError(f"{json_path}: sprites[{i}] must be a JSON object")
        for key in ("index", "screen_x", "screen_y", "width", "height",
                    "atlas_x", "atlas_y"):
            if key not in entry:
                raise ValueError(f"{json_path}: sprites[{i}] missing key '{key}'")

        w = entry["width"]
        h = entry["height"]
        ax = entry["atlas_x"]
        ay = entry["atlas_y"]
        sx = entry["screen_x"]
        sy = entry["screen_y"]
        # sprite_start: original absolute file offset (required for overlapping BUILD files).
        # Defaults to 0 — serialise() will recompute for simple consecutive files.
        sprite_start: int = entry.get("sprite_start", 0)
        # pixel_bytes may be < w*h for truncated last sprites in BUILD*.PL8.
        # Defaults to w*h when absent (normal sprites exported before this field existed).
        pixel_bytes: int = entry.get("pixel_bytes", w * h)
        # diamond_encoded: True for CITYFIXT/PROVFIXT/BATLFIX terrain tile sprites.
        # The atlas PNG stores the decoded 58×30 row-major image; we re-encode on import.
        diamond: bool = bool(entry.get("diamond_encoded", False))
        # extra: descriptor bytes +0x0C..+0x0F as hex string (default "00000000").
        extra_hex: str = entry.get("extra", "00000000")
        try:
            extra_bytes = bytes.fromhex(extra_hex)
            if len(extra_bytes) != 4:
                raise ValueError("wrong length")
        except (ValueError, AttributeError):
            extra_bytes = b"\x00\x00\x00\x00"

        # body_hex: verbatim body/roof bytes beyond the 900-byte diamond base (type 2/3/4).
        # Empty string for type 1 and non-building sprites.
        body_hex_str: str = entry.get("body_hex", "")
        try:
            body_bytes_raw = bytes.fromhex(body_hex_str) if body_hex_str else b""
        except (ValueError, AttributeError):
            body_bytes_raw = b""

        # Derive blitter type from extra_bytes for reconstruction logic.
        t_import: int = 0
        if extra_bytes and len(extra_bytes) >= 1:
            t_val = extra_bytes[0]
            if 1 <= t_val <= 4:
                t_import = t_val

        # display_width / display_height: dimensions used in the atlas PNG.
        # Defaults to w×h for old sidecars that don't have these fields.
        dw: int = entry.get("display_width", w)
        dh: int = entry.get("display_height", h)

        # Validate bounds using display dimensions
        if ax + dw > atlas_w or ay + dh > atlas_h:
            raise ValueError(
                f"{json_path}: sprites[{i}] atlas region "
                f"({ax},{ay})+({dw}×{dh}) exceeds atlas size {atlas_w}×{atlas_h}"
            )

        # Extract pixel rows from the atlas using display dimensions
        rows = bytearray()
        for row in range(dh):
            row_start = (ay + row) * atlas_w + ax
            rows.extend(png_pixels[row_start : row_start + dw])

        diamond_bytes = _diamond_pixel_bytes(w, h)

        if t_import == 2 and body_bytes_raw:
            # Extended diamond (type 2): atlas layout is [body_canvas][diamond].
            # Body canvas occupies the top canvas_h rows; diamond the bottom h rows.
            # We use body_bytes_raw verbatim (preserving padding bytes that the blitter
            # never reads but which must be preserved for byte-identical round-trips).
            y_len = extra_bytes[1] if len(extra_bytes) >= 2 else 0
            if y_len > 0:
                canvas_h = _body_canvas_height(y_len, w)
                base_pixels = bytes(rows[canvas_h * w : canvas_h * w + w * h])
                final_pixels = encode_diamond(base_pixels, w, h) + body_bytes_raw
            else:
                final_pixels = encode_diamond(bytes(rows[:w * h]), w, h)
        elif t_import in (3, 4) and body_bytes_raw:
            # Left/right-half building (type 3/4): atlas stores only the decoded w×h diamond.
            # Re-encode back to diamond, then append body_hex verbatim (30 bytes/row diagonal).
            final_pixels = encode_diamond(bytes(rows[:w * h]), w, h) + body_bytes_raw
        elif t_import in (1, 2, 3, 4) or diamond:
            # Known diamond blitter type (or legacy diamond_encoded flag):
            # Re-encode the decoded w×h row-major image back to diamond-scan order.
            final_pixels = encode_diamond(bytes(rows[:w * h]), w, h)
        else:
            # Row-major sprite: the atlas stores dw×dh pixels; truncate to pixel_bytes.
            final_pixels = bytes(rows[:pixel_bytes])

        sprites.append(SpriteDescriptor(
            width=w,
            height=h,
            sprite_start=sprite_start,
            default_x=sx,
            default_y=sy,
            extra=extra_bytes,
        ))
        pixel_data_list.append(final_pixels)

    pl8 = PL8File(
        zoom_level=zoom_level,
        sprites=sprites,
        pixel_data=pixel_data_list,
        group_boundary_index=group_boundary_index,
        file_id=file_id,
    )
    return pl8, palette


# ── Sub-commands ──────────────────────────────────────────────────────────────


@app.command("show")
def show(
    file: Annotated[
        Path, typer.Argument(help="Path to a Caesar II `.PL8` file")
    ],
) -> None:
    """Parse and display metadata from a `.PL8` file.

    Prints the file header fields and a table of all sprite descriptors.

    Example:

        c2 image show INT_CITY.PL8
    """
    if not file.exists():
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(1)

    try:
        pl8 = parse_pl8(file)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    typer.echo(f"File:                  {file}")
    typer.echo(f"Size:                  {file.stat().st_size:,} bytes")
    typer.echo(f"Format version:        0x02")
    typer.echo(f"Zoom level:            {pl8.zoom_level}  (0=full, 1=medium, 2=small)")
    typer.echo(f"Sprite count:          {pl8.sprite_count}")
    typer.echo(f"Group boundary index:  {pl8.group_boundary_index}  [tool metadata, not read at runtime]")
    typer.echo(f"File ID:               {pl8.file_id}  [tool metadata, not read at runtime]")
    typer.echo("")
    typer.echo(f"{'#':>4}  {'W':>5}  {'H':>5}  {'start':>10}  {'def_x':>6}  {'def_y':>6}  {'pixels':>8}")
    typer.echo(f"{'─'*4}  {'─'*5}  {'─'*5}  {'─'*10}  {'─'*6}  {'─'*6}  {'─'*8}")
    for i, desc in enumerate(pl8.sprites):
        typer.echo(
            f"{i:>4}  {desc.width:>5}  {desc.height:>5}  "
            f"0x{desc.sprite_start:08x}  {desc.default_x:>6}  {desc.default_y:>6}  "
            f"{desc.pixel_count:>8,}"
        )


@app.command("export")
def export_png(
    file: Annotated[
        Path, typer.Argument(help="Path to a Caesar II `.PL8` file")
    ],
    palette: Annotated[
        Path | None,
        typer.Option(
            "--palette", "-p",
            help=(
                "Path to the companion `.256` palette file.  "
                "Defaults to a file with the same stem as the `.PL8` in the same directory "
                "(e.g. BUILD1A.PL8 → BUILD1A.256).  "
                "If that is not found, looks for CITYFIXT.256 in the same directory."
            ),
        ),
    ] = None,
    out_dir: Annotated[
        Path | None,
        typer.Option(
            "--out-dir", "-d",
            help="Output directory.  Defaults to the same directory as the input file.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite output files if they exist."),
    ] = False,
) -> None:
    """Convert a `.PL8` + `.256` palette to an indexed PNG atlas + JSON sidecar.

    Produces two files:
      - ``<name>.png``  — 8-bit indexed PNG (colour type 3, PLTE embedded, tRNS on index 0)
      - ``<name>.json`` — JSON sidecar with sprite metadata and original VGA palette values

    The JSON sidecar stores the original 6-bit VGA DAC palette values so that
    ``c2 image import`` can reconstruct a byte-identical `.PL8` and `.256`.

    Example:

        c2 image export INT_CITY.PL8 --palette CITYFIXT.256
        c2 image export BUILD1A.PL8 --out-dir exported/
    """
    try:
        from PIL import Image
    except ImportError:
        typer.echo(
            "Error: Pillow is required.  Install it with: uv add pillow",
            err=True,
        )
        raise typer.Exit(1)

    if not file.exists():
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(1)

    # ── Resolve palette path ──────────────────────────────────────────────────
    pal_path: Path
    if palette is not None:
        pal_path = palette
    else:
        # Try <stem>.256 next to the PL8 file
        candidate = file.with_suffix(".256")
        if candidate.exists():
            pal_path = candidate
        else:
            # Fall back to CITYFIXT.256 in the same directory
            fallback = file.parent / "CITYFIXT.256"
            if fallback.exists():
                pal_path = fallback
                typer.echo(
                    f"Note: no companion .256 found for {file.name}; "
                    f"using {fallback.name}",
                    err=True,
                )
            else:
                typer.echo(
                    f"Error: no palette file found for {file.name}.  "
                    "Use --palette to specify one.",
                    err=True,
                )
                raise typer.Exit(1)

    if not pal_path.exists():
        typer.echo(f"Error: palette file not found: {pal_path}", err=True)
        raise typer.Exit(1)

    # ── Parse inputs ──────────────────────────────────────────────────────────
    try:
        pl8 = parse_pl8(file)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    try:
        vga_pal = parse_palette(pal_path)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    # ── Determine output paths ────────────────────────────────────────────────
    dest_dir = out_dir if out_dir is not None else file.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = file.stem.lower()
    png_path = dest_dir / f"{stem}.png"
    json_path = dest_dir / f"{stem}.json"

    for out_path in (png_path, json_path):
        if out_path.exists() and not force:
            typer.echo(
                f"Error: output file already exists: {out_path}\n"
                "Use --force / -f to overwrite.",
                err=True,
            )
            raise typer.Exit(1)

    # ── Build atlas ───────────────────────────────────────────────────────────
    pixel_sizes = [len(p) for p in pl8.pixel_data]
    atlas_w, atlas_h, positions = _pack_atlas(pl8.sprites, pixel_sizes)

    # ── Build indexed PNG ─────────────────────────────────────────────────────
    img = Image.new("P", (atlas_w, atlas_h), color=0)
    img.putpalette(vga_pal.as_flat_bytes())

    # Place each sprite into the atlas at its correct display dimensions.
    #
    # Sprite types and how they are placed:
    #   type 1 (diamond 900B):     decode to w×h row-major, place as w×h
    #   type 2 (extended diamond): decode base 900B to w×h, append y_len rows of w pixels,
    #                              place as w×(h+y_len)
    #   type 3/4 (left/right half): decode 900B diamond base to w×h, place as w×h
    #                               (body bytes are in diagonal scan order, not displayed)
    #   normal row-major:          place as w×h
    atlas_pixels = bytearray(atlas_w * atlas_h)  # initialised to 0 (transparent)
    for desc, pixels, (ax, ay) in zip(pl8.sprites, pl8.pixel_data, positions):
        w, h = desc.width, desc.height
        diamond_bytes = _diamond_pixel_bytes(w, h)
        dw, dh = _display_dims(desc, len(pixels))
        t = _sprite_type(desc)

        if t == 2 and len(pixels) > diamond_bytes:
            # Extended diamond: body canvas placed ABOVE diamond in atlas.
            # Atlas layout: [body_canvas (canvas_h rows)] [diamond (h rows)]
            base = decode_diamond(pixels[:diamond_bytes], w, h)
            body_raw = pixels[diamond_bytes:]
            y_len = desc.extra[1] if desc.extra and len(desc.extra) >= 2 else 0
            if y_len > 0:
                body_canvas = decode_body(body_raw, y_len, w)
                display_pixels: bytes = body_canvas + base
            else:
                display_pixels = base
        elif t in (1, 3, 4) or is_diamond_encoded(desc, len(pixels)):
            # Standard diamond base (type 1/3/4): decode to w×h row-major
            # For type 3/4 the body bytes are NOT displayed (diagonal scan order)
            display_pixels = decode_diamond(pixels[:diamond_bytes], w, h)
        else:
            # Normal row-major sprite: use as-is
            display_pixels = pixels

        for row in range(dh):
            src_start = row * dw
            src_end = src_start + dw
            dst_start = (ay + row) * atlas_w + ax
            if src_end <= len(display_pixels):
                atlas_pixels[dst_start : dst_start + dw] = display_pixels[src_start : src_end]
            elif src_start < len(display_pixels):
                partial = display_pixels[src_start:]
                atlas_pixels[dst_start : dst_start + len(partial)] = partial
                break
            else:
                break

    img.frombytes(bytes(atlas_pixels))

    # Set tRNS chunk: palette index 0 is fully transparent
    img.info["transparency"] = 0

    png_path.write_bytes(_encode_indexed_png(img))

    # ── Build JSON sidecar ────────────────────────────────────────────────────
    sidecar = _build_sidecar(pl8, vga_pal, positions, file.name, pal_path.name)
    json_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")

    typer.echo(
        f"Exported {pl8.sprite_count} sprite(s) → {png_path}  ({atlas_w}×{atlas_h} px)"
    )
    typer.echo(f"Sidecar                → {json_path}")


@app.command("import")
def import_png(
    json_file: Annotated[
        Path,
        typer.Argument(
            help="Path to a JSON sidecar previously produced by 'image export'."
        ),
    ],
    out_dir: Annotated[
        Path | None,
        typer.Option(
            "--out-dir", "-d",
            help=(
                "Output directory for the reconstructed `.PL8` and `.256` files.  "
                "Defaults to the same directory as the JSON file."
            ),
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite output files if they exist."),
    ] = False,
) -> None:
    """Reconstruct a `.PL8` + `.256` from an indexed PNG atlas + JSON sidecar.

    Reads ``<name>.json`` and the companion ``<name>.png`` (must be in the same
    directory as the JSON file) and writes the original `.PL8` and `.256` files.

    When neither the PNG nor the JSON has been modified since export, the output
    is byte-for-byte identical to the original files.

    Example:

        c2 image import build1a.json
        c2 image import build1a.json --out-dir reconstructed/
    """
    if not json_file.exists():
        typer.echo(f"Error: file not found: {json_file}", err=True)
        raise typer.Exit(1)

    # ── Load JSON sidecar ─────────────────────────────────────────────────────
    try:
        doc = json.loads(json_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        typer.echo(f"Error: JSON parse error in {json_file}: {exc}", err=True)
        raise typer.Exit(1)

    # ── Load companion PNG ────────────────────────────────────────────────────
    png_path = json_file.with_suffix(".png")
    if not png_path.exists():
        typer.echo(f"Error: companion PNG not found: {png_path}", err=True)
        raise typer.Exit(1)

    png_data = png_path.read_bytes()

    # ── Reconstruct PL8 + palette ─────────────────────────────────────────────
    try:
        pl8, vga_pal = _pl8_from_sidecar(doc, png_data, json_file)
    except (ValueError, RuntimeError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    # ── Determine output paths ────────────────────────────────────────────────
    dest_dir = out_dir if out_dir is not None else json_file.parent

    source_name: str = doc.get("source_file", "")
    if not source_name:
        typer.echo(
            "Error: JSON sidecar is missing 'source_file' — cannot determine output filename.  "
            "Use --out-dir and rename manually.",
            err=True,
        )
        raise typer.Exit(1)

    palette_source_name: str = doc.get("palette_source", "")
    if not palette_source_name:
        palette_source_name = Path(source_name).stem + ".256"

    dest_dir.mkdir(parents=True, exist_ok=True)
    pl8_out = dest_dir / source_name
    pal_out = dest_dir / palette_source_name

    for out_path in (pl8_out, pal_out):
        if out_path.exists() and not force:
            typer.echo(
                f"Error: output file already exists: {out_path}\n"
                "Use --force / -f to overwrite.",
                err=True,
            )
            raise typer.Exit(1)

    # ── Write outputs ─────────────────────────────────────────────────────────
    try:
        pl8_bytes = serialise_pl8(pl8)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    pl8_out.write_bytes(pl8_bytes)
    pal_out.write_bytes(serialise_palette(vga_pal))

    typer.echo(
        f"Reconstructed {pl8.sprite_count} sprite(s) → {pl8_out}  ({len(pl8_bytes):,} bytes)"
    )
    typer.echo(f"Palette                → {pal_out}")


# ── PNG encoding helper ───────────────────────────────────────────────────────


def _encode_indexed_png(img: "Image.Image") -> bytes:  # type: ignore[name-defined]
    """Encode a PIL indexed image to PNG bytes with a tRNS chunk on index 0.

    PIL's ``save()`` only writes a ``tRNS`` chunk when ``img.info["transparency"]``
    is set AND the image is saved via a file-like object.  We use ``io.BytesIO``
    to capture the bytes.
    """
    import io
    buf = io.BytesIO()
    img.save(buf, format="PNG", transparency=0)
    return buf.getvalue()
