"""image command group: export and import Caesar II `.PL8` sprite files.

Sub-commands
------------
show        Parse and display metadata from a `.PL8` file.
metadata    Read and display the embedded ``c2_sidecar`` metadata from a PNG.
export      Convert a `.PL8` + `.256` palette to a composed PNG with embedded metadata.
import      Reconstruct a `.PL8` + `.256` from a PNG with embedded metadata.

Editing workflow
----------------
Export a ``.PL8`` to PNG, edit the PNG in any image editor (keeping it as an
indexed-colour PNG with 256 palette entries), then import it back.  The import
command reads the pixel data directly from the PNG canvas, so any edits you
make to the image are faithfully captured in the resulting ``.PL8``.

The PNG embeds sprite layout metadata in a ``tEXt`` chunk keyed
``c2_sidecar`` (per-sprite descriptors, zoom level, group boundary index,
file ID).  The VGA palette is stored in the PNG's standard PLTE chunk.
Image viewers ignore the ``tEXt`` chunk; the import command reads it.

Lossy re-encoding
-----------------
Re-encoding is **not** binary-identical to the original ``.PL8``.  Files with
overlapping sprite bounding boxes (e.g. ``BUILD*.PL8``) will differ at overlap
positions because composition is last-writer-wins.  The visual result is
identical — ``compose(decompose(compose(orig))) == compose(orig)`` holds for
all 82 tested files.

Format notes
------------
The PNG is written as colour type 3 (indexed, PLTE chunk) with a ``tRNS`` chunk
marking palette index 0 as fully transparent.  Sprites are composited at their
screen positions (``default_x``, ``default_y``) so buildings appear assembled.

Reference: data/docs/pl8-format.md
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Annotated

import typer

from c2.parsers.pl8 import (
    PALETTE_ENTRIES,
    BlitterType,
    PL8File,
    SpriteDescriptor,
    VGAPalette,
    is_diamond_encoded,
    parse as parse_pl8,
    parse_palette,
    serialise as serialise_pl8,
    serialise_palette,
)
from c2.parsers.pl8_compose import compose_sprites, decompose_sprites

# ── Typer sub-application ─────────────────────────────────────────────────────

app = typer.Typer(
    name="image",
    help="Export and import Caesar II `.PL8` sprite files.",
    no_args_is_help=True,
)

# ── Palette resolution helpers ────────────────────────────────────────────────

def _infer_palette_name(pl8_filename: str) -> str | None:
    """Infer the correct .256 palette filename for a .PL8 file based on PS.EXE analysis.
    
    Returns the palette filename (e.g., "CITYFIXT.256") or None if no mapping is known.
    
    Mappings are derived from reverse engineering PS.EXE with Ghidra.
    See data/docs/pl8-palette-mappings.md for full details.
    """
    name_upper = pl8_filename.upper()
    stem = name_upper.replace(".PL8", "")
    
    # Explicit same-name palette mappings (from Ghidra analysis)
    SAME_NAME_PALETTES = {
        "LOGO1", "LOGO2", "BACKGRND", "FORUM", "EMPIRE", "RAT_BACK",
    }
    if stem in SAME_NAME_PALETTES:
        return f"{stem}.256"
    
    # RAT_FRON uses RAT_BACK palette (loaded by basic_temple_screen @ 0x0005f108)
    if stem == "RAT_FRON":
        return "RAT_BACK.256"
    
    # Tutorial files: tut_XXa.pl8 → tut_XXa.256
    if stem.startswith("TUT_") and stem.endswith("A"):
        return f"{stem}.256"
    
    # Startup graphics and city-context sprites use CITYFIXT.256
    CITY_PALETTE_FILES = {
        # Startup graphics (loaded by load_start_graphics @ 0x00010e98)
        "LANDFILL", "FONT_C2", "FONT3C2", "MOUSE", "SYSTEM", "PANELS",
        "SMACKER", "MISC", "INT_CITY",
        # City sprite sets (use active city palette during gameplay)
        "CITYFIXT", "CITYFIX2", "CITYFIX3",
        "HOUSES1", "HOUSES2", "HOUSES3",
        "CITYTOP1", "CITYTOP2", "CITYTOP3",
        "LTLMEN1B", "LTLMEN2B", "LTLMEN3B",
        "OVERLAY1", "OVERLAY2", "OVERLAY3",
    }
    if stem in CITY_PALETTE_FILES:
        return "CITYFIXT.256"
    
    # Building sets use city palette
    if stem.startswith("BUILD"):
        return "CITYFIXT.256"
    
    # Province-context sprites use PROVFIXT.256
    PROVINCE_PALETTE_FILES = {
        "INT_PROV", "INT_BATL",  # Loaded at startup with province palette
        "PROVFIXT", "PROVFIX2", "PROVFIX3",
        "MOUNTNS1", "MOUNTNS2", "MOUNTNS3",
        "MY_STDS", "MY_STDS2", "MY_STDS3",
    }
    if stem in PROVINCE_PALETTE_FILES:
        return "PROVFIXT.256"
    
    # Province building sets
    if stem.startswith("PRVBLD"):
        return "PROVFIXT.256"
    
    # Battle-context sprites use BATLFIX2.256
    if stem.startswith("BATLFIX"):
        return "BATLFIX2.256"
    
    # Forum UI elements use forum palette (loaded by forum_temple_screen @ 0x0005f094)
    if stem == "FORUMBIT":
        return "FORUM.256"
    
    # Empire map parts use empire palette (loaded by show_initreg_box @ 0x0005cb64)
    if stem.startswith("E_PARTS"):
        return "EMPIRE.256"
    
    # Unused/test files - use CITYFIXT.256 as fallback
    if stem in ("MAIN", "ICONS"):
        return "CITYFIXT.256"
    
    # No known mapping
    return None


# ── Blitter type helpers ──────────────────────────────────────────────────────


def _sprite_blitter(desc: SpriteDescriptor) -> BlitterType:
    """Return the ``BlitterType`` from ``desc.extra[0]``, defaulting to ``FLAT``."""
    if desc.extra and len(desc.extra) >= 1:
        try:
            return BlitterType(desc.extra[0])
        except ValueError:
            pass
    return BlitterType.FLAT


# ── Sidecar builder (embedded in PNG metadata) ───────────────────────────────


def _build_sidecar(
    pl8: PL8File,
    palette_source_name: str,
) -> dict:
    """Build the sidecar document to embed in PNG metadata.

    Contains sprite layout descriptors and file-level metadata needed to
    reconstruct the ``.PL8`` on import.  The palette lives in the PNG's
    standard PLTE chunk.
    """
    sprites_list = []
    for desc in pl8.sprites:
        sprites_list.append({
            "screen_x": desc.default_x,
            "screen_y": desc.default_y,
            "width": desc.width,
            "height": desc.height,
            "sprite_start": desc.sprite_start,
            "extra": desc.extra.hex(),
        })

    return {
        "zoom_level": pl8.zoom_level,
        "group_boundary_index": pl8.group_boundary_index,
        "file_id": pl8.file_id,
        "palette_source": palette_source_name,
        "sprites": sprites_list,
    }


def _pl8_from_sidecar(
    doc: dict,
    png_palette_flat: list[int],
    canvas: bytes,
    canvas_w: int,
    canvas_h: int,
) -> tuple[PL8File, VGAPalette]:
    """Reconstruct a ``PL8File`` and ``VGAPalette`` from sidecar + PNG canvas.

    Pixel data is read from the PNG canvas, so any edits the user made to
    the image are faithfully captured in the resulting ``.PL8``.

    *png_palette_flat* is the flat 768-int list from ``Image.getpalette()``
    (8-bit RGB values, divided by 4 to recover 6-bit VGA DAC values).
    """
    for key in ("zoom_level", "group_boundary_index", "file_id", "sprites"):
        if key not in doc:
            raise ValueError(f"sidecar missing required key '{key}'")

    zoom_level = doc["zoom_level"]
    group_boundary_index = doc["group_boundary_index"]
    file_id = doc["file_id"]

    # ── Palette (recovered from PNG PLTE chunk) ───────────────────────────────
    if len(png_palette_flat) < PALETTE_ENTRIES * 3:
        raise ValueError(
            f"PNG palette too short: expected {PALETTE_ENTRIES * 3} values, "
            f"got {len(png_palette_flat)}"
        )
    pal_entries: list[tuple[int, int, int]] = []
    for i in range(PALETTE_ENTRIES):
        r8 = png_palette_flat[i * 3]
        g8 = png_palette_flat[i * 3 + 1]
        b8 = png_palette_flat[i * 3 + 2]
        pal_entries.append((r8 // 4, g8 // 4, b8 // 4))
    palette = VGAPalette(raw=pal_entries)

    # ── Sprite descriptors ────────────────────────────────────────────────────
    raw_sprites = doc["sprites"]
    sprites: list[SpriteDescriptor] = []

    for entry in raw_sprites:
        w = entry["width"]
        h = entry["height"]
        sx = entry["screen_x"]
        sy = entry["screen_y"]
        sprite_start: int = entry.get("sprite_start", 0)
        extra_hex: str = entry.get("extra", "00000000")
        try:
            extra_bytes = bytes.fromhex(extra_hex)
            if len(extra_bytes) != 4:
                extra_bytes = b"\x00\x00\x00\x00"
        except (ValueError, AttributeError):
            extra_bytes = b"\x00\x00\x00\x00"

        sprites.append(SpriteDescriptor(
            width=w, height=h, sprite_start=sprite_start,
            default_x=sx, default_y=sy, extra=extra_bytes,
        ))

    # ── Recover pixel data from PNG canvas ────────────────────────────────────
    pixel_data_list = decompose_sprites(canvas, canvas_w, canvas_h, sprites)

    pl8 = PL8File(
        zoom_level=zoom_level, sprites=sprites, pixel_data=pixel_data_list,
        group_boundary_index=group_boundary_index, file_id=file_id,
    )
    return pl8, palette


# ── Sub-commands ──────────────────────────────────────────────────────────────


@app.command("show")
def show(
    file: Annotated[
        Path, typer.Argument(help="Path to a Caesar II `.PL8` file")
    ],
) -> None:
    """Parse and display metadata from a `.PL8` file."""
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

    # Count sprite types for summary
    type_counts: dict[str, int] = {}
    diamond_count = 0  # sprites where actual < declared (diamond-scan storage)

    typer.echo(
        f"{'#':>4}  {'W':>5}  {'H':>5}  {'start':>10}  "
        f"{'actual':>8}  {'decl':>8}  "
        f"{'def_x':>6}  {'def_y':>6}  {'type':>10}  {'extra'}"
    )
    typer.echo(
        f"{'─'*4}  {'─'*5}  {'─'*5}  {'─'*10}  "
        f"{'─'*8}  {'─'*8}  "
        f"{'─'*6}  {'─'*6}  {'─'*10}  {'─'*8}"
    )
    for i, (desc, pixels) in enumerate(zip(pl8.sprites, pl8.pixel_data)):
        actual = len(pixels)
        declared = desc.pixel_count  # w * h
        bt = _sprite_blitter(desc)
        diamond = is_diamond_encoded(desc, actual)
        type_name = bt.name.lower().replace("_", "-")

        # Track diamond-scan storage (actual bytes < declared w*h)
        if diamond:
            diamond_count += 1

        type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Show body y_len for extended types
        y_len_str = ""
        if bt in (BlitterType.EXT_DIAMOND, BlitterType.LEFT_ROOF, BlitterType.RIGHT_ROOF) and desc.extra and len(desc.extra) >= 2:
            y_len = desc.extra[1]
            if y_len > 0:
                y_len_str = f"  y_len={y_len}"

        typer.echo(
            f"{i:>4}  {desc.width:>5}  {desc.height:>5}  "
            f"0x{desc.sprite_start:08x}  "
            f"{actual:>8,}  {declared:>8,}  "
            f"{desc.default_x:>6}  {desc.default_y:>6}  "
            f"{type_name:>10}  {desc.extra.hex()}{y_len_str}"
        )

    # Summary
    typer.echo("")
    typer.echo("Summary:")
    for tname, count in sorted(type_counts.items()):
        typer.echo(f"  {tname:>12}: {count}")
    total_pixels = sum(len(p) for p in pl8.pixel_data)
    typer.echo(f"  {'total bytes':>12}: {total_pixels:,}")
    if diamond_count:
        typer.echo(
            f"  Note: {diamond_count} sprite(s) use diamond-scan storage "
            f"(actual bytes < declared w×h)"
        )


@app.command("metadata")
def metadata(
    png_file: Annotated[
        Path,
        typer.Argument(help="Path to a PNG produced by 'image export'."),
    ],
    raw: Annotated[
        bool,
        typer.Option("--raw", "-r", help="Print the full JSON sidecar instead of a summary."),
    ] = False,
) -> None:
    """Read and display the embedded ``c2_sidecar`` metadata from a PNG.

    By default prints a human-readable summary.  Use ``--raw`` to dump the
    full JSON document (useful for scripting or debugging).

    Example:

        c2 image metadata build1a.png
        c2 image metadata build1a.png --raw
    """
    try:
        from PIL import Image
    except ImportError:
        typer.echo(
            "Error: Pillow is required.  Install it with: uv add Pillow",
            err=True,
        )
        raise typer.Exit(1)

    if not png_file.exists():
        typer.echo(f"Error: file not found: {png_file}", err=True)
        raise typer.Exit(1)

    try:
        img = Image.open(png_file)
    except Exception as exc:
        typer.echo(f"Error: cannot open PNG: {exc}", err=True)
        raise typer.Exit(1)

    sidecar_json = img.info.get("c2_sidecar")
    if not sidecar_json:
        typer.echo(
            f"Error: {png_file} does not contain embedded c2_sidecar metadata.\n"
            "This PNG was not produced by 'c2 image export'.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        doc = json.loads(sidecar_json)
    except json.JSONDecodeError as exc:
        typer.echo(f"Error: malformed c2_sidecar metadata: {exc}", err=True)
        raise typer.Exit(1)

    if raw:
        typer.echo(json.dumps(doc, indent=2))
        return

    # ── Human-readable summary ────────────────────────────────────────────────
    typer.echo(f"PNG file:              {png_file}")
    typer.echo(f"Image size:            {img.size[0]}×{img.size[1]} px")
    typer.echo(f"Source PL8:            {doc.get('source_file', '?')}")
    typer.echo(f"Palette source:        {doc.get('palette_source', '?')}")
    typer.echo(f"Zoom level:            {doc.get('zoom_level', '?')}")
    typer.echo(f"Group boundary index:  {doc.get('group_boundary_index', '?')}")
    typer.echo(f"File ID:               {doc.get('file_id', '?')}")

    sprites = doc.get("sprites", [])
    typer.echo(f"Sprite count:          {len(sprites)}")

    if sprites:
        typer.echo("")
        typer.echo(
            f"{'#':>4}  {'W':>5}  {'H':>5}  "
            f"{'screen_x':>8}  {'screen_y':>8}  "
            f"{'extra'}"
        )
        typer.echo(
            f"{'─'*4}  {'─'*5}  {'─'*5}  "
            f"{'─'*8}  {'─'*8}  "
            f"{'─'*8}"
        )
        for i, s in enumerate(sprites):
            typer.echo(
                f"{i:>4}  "
                f"{s.get('width', '?'):>5}  {s.get('height', '?'):>5}  "
                f"{s.get('screen_x', '?'):>8}  {s.get('screen_y', '?'):>8}  "
                f"{s.get('extra', '')}"
            )

    sidecar_size = len(sidecar_json)
    typer.echo("")
    typer.echo(f"Sidecar size:          {sidecar_size:,} chars ({sidecar_size / 1024:.1f} KB)")


@app.command("export")
def export_png(
    file: Annotated[
        Path, typer.Argument(help="Path to a Caesar II `.PL8` file")
    ],
    palette: Annotated[
        Path | None,
        typer.Option(
            "--palette", "-p",
            help="Path to the companion `.256` palette file.",
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
    """Convert a `.PL8` + `.256` palette to a composed PNG.

    Sprites are composited at their screen positions so buildings appear
    assembled.  All metadata needed for round-trip reconstruction is embedded
    in the PNG as a ``tEXt`` chunk (``c2_sidecar``).

    Produces one file:
      - ``<name>.png``  — 8-bit indexed PNG with embedded reconstruction metadata

    Use ``c2 image import <name>.png`` to reconstruct the original `.PL8` + `.256`.

    Example:

        c2 image export BUILD1A.PL8
        c2 image export INT_CITY.PL8 --palette CITYFIXT.256
    """
    try:
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo
    except ImportError:
        typer.echo(
            "Error: Pillow is required.  Install it with: uv add Pillow",
            err=True,
        )
        raise typer.Exit(1)

    if not file.exists():
        typer.echo(f"Error: file not found: {file}", err=True)
        raise typer.Exit(1)

    # ── Resolve palette path ──────────────────────────────────────────────────
    pal_path: Path
    if palette is not None:
        # Explicit --palette option takes priority
        pal_path = palette
    else:
        # Try same-name .256 file first
        candidate = file.with_suffix(".256")
        if candidate.exists():
            pal_path = candidate
        else:
            # Use Ghidra-derived palette mapping
            inferred_name = _infer_palette_name(file.name)
            if inferred_name is not None:
                inferred_path = file.parent / inferred_name
                if inferred_path.exists():
                    pal_path = inferred_path
                    typer.echo(
                        f"Note: using inferred palette {inferred_name} for {file.name}",
                        err=True,
                    )
                else:
                    typer.echo(
                        f"Error: inferred palette {inferred_name} not found for {file.name}.",
                        err=True,
                    )
                    raise typer.Exit(1)
            else:
                typer.echo(
                    f"Error: no palette mapping known for {file.name}. "
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

    # ── Determine output path ─────────────────────────────────────────────────
    dest_dir = out_dir if out_dir is not None else file.parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    stem = file.stem.lower()
    png_path = dest_dir / f"{stem}.png"

    if png_path.exists() and not force:
        typer.echo(
            f"Error: output file already exists: {png_path}\n"
            "Use --force / -f to overwrite.",
            err=True,
        )
        raise typer.Exit(1)

    # ── Compose sprites at screen positions ───────────────────────────────────
    canvas, cw, ch = compose_sprites(pl8)

    # ── Build indexed PNG ─────────────────────────────────────────────────────
    img = Image.new("P", (cw, ch), color=0)
    img.putpalette(vga_pal.as_flat_bytes())
    img.frombytes(canvas)

    # ── Embed sidecar metadata in PNG ─────────────────────────────────────────
    sidecar = _build_sidecar(pl8, pal_path.name)
    png_info = PngInfo()
    png_info.add_text("c2_sidecar", json.dumps(sidecar, separators=(",", ":")))

    # ── Write PNG ─────────────────────────────────────────────────────────────
    buf = io.BytesIO()
    img.save(buf, format="PNG", transparency=0, pnginfo=png_info)
    png_path.write_bytes(buf.getvalue())

    typer.echo(
        f"Exported {pl8.sprite_count} sprite(s) → {png_path}  ({cw}×{ch} px)"
    )


@app.command("import")
def import_png(
    png_file: Annotated[
        Path,
        typer.Argument(
            help="Path to a PNG previously produced by 'image export'."
        ),
    ],
    out_dir: Annotated[
        Path | None,
        typer.Option(
            "--out-dir", "-d",
            help="Output directory for the reconstructed `.PL8` and `.256` files.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite output files if they exist."),
    ] = False,
) -> None:
    """Reconstruct a `.PL8` + `.256` from a PNG with embedded metadata.

    The PNG must have been produced by ``c2 image export``, which embeds
    reconstruction metadata in a ``tEXt`` chunk.  Pixel data is read from
    the PNG canvas, so any edits you made to the image are captured.

    .. note::

       Re-encoding is not binary-identical to the original ``.PL8`` for
       files with overlapping sprite bounding boxes (e.g. ``BUILD*.PL8``).
       The visual result is identical.

    Example:

        c2 image import build1a.png
    """
    try:
        from PIL import Image
    except ImportError:
        typer.echo(
            "Error: Pillow is required.  Install it with: uv add Pillow",
            err=True,
        )
        raise typer.Exit(1)

    if not png_file.exists():
        typer.echo(f"Error: file not found: {png_file}", err=True)
        raise typer.Exit(1)

    # ── Read PNG and extract sidecar ──────────────────────────────────────────
    try:
        img = Image.open(png_file)
    except Exception as exc:
        typer.echo(f"Error: cannot open PNG: {exc}", err=True)
        raise typer.Exit(1)

    sidecar_json = img.info.get("c2_sidecar")
    if not sidecar_json:
        typer.echo(
            f"Error: {png_file} does not contain embedded c2_sidecar metadata.\n"
            "This PNG was not produced by 'c2 image export'.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        doc = json.loads(sidecar_json)
    except json.JSONDecodeError as exc:
        typer.echo(f"Error: malformed c2_sidecar metadata: {exc}", err=True)
        raise typer.Exit(1)

    png_palette_flat = img.getpalette()
    if png_palette_flat is None:
        typer.echo(
            f"Error: {png_file} has no palette (not an indexed-colour PNG).",
            err=True,
        )
        raise typer.Exit(1)

    # ── Extract canvas pixel data from PNG ─────────────────────────────────
    canvas_w, canvas_h = img.size
    canvas = img.tobytes()

    try:
        pl8, vga_pal = _pl8_from_sidecar(
            doc, png_palette_flat, canvas, canvas_w, canvas_h,
        )
    except (ValueError, RuntimeError) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    dest_dir = out_dir if out_dir is not None else png_file.parent

    # Source filename is derived from PNG filename
    source_name = png_file.stem.upper() + ".PL8"
    
    palette_source_name: str = doc.get("palette_source", "")
    if not palette_source_name:
        palette_source_name = png_file.stem.upper() + ".256"

    dest_dir.mkdir(parents=True, exist_ok=True)
    pl8_out = dest_dir / source_name
    pal_out = dest_dir / palette_source_name

    if pl8_out.exists() and not force:
        typer.echo(
            f"Error: output file already exists: {pl8_out}\n"
            "Use --force / -f to overwrite.",
            err=True,
        )
        raise typer.Exit(1)

    try:
        pl8_bytes = serialise_pl8(pl8)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1)

    pal_bytes = serialise_palette(vga_pal)

    # Only require --force for the palette if the existing file differs.
    # Many PL8 files share the same palette (e.g. CITYFIXT.256), so
    # silently skip writing an identical palette.
    if pal_out.exists():
        if pal_out.read_bytes() == pal_bytes:
            pal_bytes = None  # identical — skip write
        elif not force:
            typer.echo(
                f"Error: palette file already exists with different content: {pal_out}\n"
                "Use --force / -f to overwrite.",
                err=True,
            )
            raise typer.Exit(1)

    pl8_out.write_bytes(pl8_bytes)
    if pal_bytes is not None:
        pal_out.write_bytes(pal_bytes)

    typer.echo(
        f"Reconstructed {pl8.sprite_count} sprite(s) → {pl8_out}  ({len(pl8_bytes):,} bytes)"
    )
    if pal_bytes is not None:
        typer.echo(f"Palette                → {pal_out}")
    else:
        typer.echo(f"Palette                → {pal_out}  (unchanged, skipped)")
