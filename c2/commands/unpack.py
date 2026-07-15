"""Unpack command: unpack a CD zip → bin/cue → iso → files."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

import typer


def _require_tool(name: str) -> None:
    if shutil.which(name) is None:
        typer.echo(f"Error: required tool '{name}' not found on PATH", err=True)
        raise typer.Exit(1)


def unpack(
    zip_file: Annotated[Path, typer.Argument(help="Path to CD .zip file")],
    cleanup: Annotated[
        bool,
        typer.Option("--cleanup", "-c", help="Remove intermediate files after extraction"),
    ] = False,
    output_dir: Annotated[
        Path,
        typer.Option("--output", "-o", help="Extraction destination (default: CDs/extracted/<name>)"),
    ] = None,
) -> None:
    """Unpack a Caesar II CD zip file: zip → bin/cue → iso → game files."""
    for tool in ("unzip", "bchunk", "7z"):
        _require_tool(tool)

    if not zip_file.exists():
        typer.echo(f"Error: zip file not found: {zip_file}", err=True)
        raise typer.Exit(1)

    zip_file = zip_file.resolve()
    basename = zip_file.stem

    dest = output_dir or (zip_file.parent / "extracted" / basename)
    dest.mkdir(parents=True, exist_ok=True)

    typer.echo(f"Processing: {zip_file}")
    typer.echo(f"Destination: {dest}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Step 1: Extract zip
        typer.echo("Step 1: Extracting ZIP...")
        subprocess.run(["unzip", "-o", str(zip_file)], cwd=tmp, check=True)

        # Step 2: Convert bin/cue → iso
        bin_file = tmp_path / f"{basename}.bin"
        cue_file = tmp_path / f"{basename}.cue"
        if not bin_file.exists() or not cue_file.exists():
            typer.echo(f"Error: expected {bin_file.name} and {cue_file.name} in zip", err=True)
            raise typer.Exit(1)

        typer.echo("Step 2: Converting BIN/CUE → ISO with bchunk...")
        subprocess.run(
            ["bchunk", str(bin_file), str(cue_file), basename],
            cwd=tmp,
            check=True,
        )

        # bchunk creates basename01.iso or basename1.iso
        iso_file = None
        for candidate in (f"{basename}01.iso", f"{basename}1.iso"):
            p = tmp_path / candidate
            if p.exists():
                iso_file = p
                break

        if iso_file is None:
            typer.echo("Error: bchunk did not produce an ISO file", err=True)
            raise typer.Exit(1)

        # Step 3: Extract iso → dest
        typer.echo("Step 3: Extracting ISO with 7z...")
        subprocess.run(
            ["7z", "x", str(iso_file), f"-o{dest}", "-y"],
            check=True,
        )

    typer.echo(f"\nExtracted to: {dest}")
