"""Compare command: compare executable versions across CD releases."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Annotated, Optional

import typer

# Default files to track
DEFAULT_FILES = [
    "HD/PS.EXE",
    "C2WIN95/HD/CAESAR2.EXE",
]


def _format_size(size_bytes: int) -> str:
    return f"{size_bytes:,} bytes".replace(",", ".")


def _load_hashes_file(hashes_file: Path) -> dict[str, tuple[str, str]]:
    """Load a .hashes file → {normalized_path: (hash, original_path)}."""
    hashes: dict[str, tuple[str, str]] = {}
    try:
        with open(hashes_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("  ", 1)
                    if len(parts) == 2:
                        hash_value, file_path = parts
                        normalized = file_path.replace("\\", "/").upper()
                        hashes[normalized] = (hash_value, file_path)
    except OSError as e:
        typer.echo(f"Warning: Error reading {hashes_file}: {e}", err=True)
    return hashes


def _find_file(
    hashes: dict[str, tuple[str, str]], pattern: str
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    normalized = pattern.replace("\\", "/").upper()
    for norm_path, (hash_value, orig_path) in hashes.items():
        if norm_path == normalized or norm_path.endswith("/" + normalized.split("/")[-1]):
            return orig_path, hash_value, norm_path
    return None, None, None


def _get_file_size(cds_dir: Path, cd_name: str, file_path: str) -> Optional[int]:
    for base in (cds_dir / "extracted" / cd_name, cds_dir / cd_name):
        p = base / file_path
        if p.exists():
            return p.stat().st_size
    return None


def compare(
    files: Annotated[
        Optional[list[str]],
        typer.Option("--file", "-f", help="File path pattern to track (repeatable)"),
    ] = None,
    hashes_dir: Annotated[
        Path,
        typer.Option("--hashes-dir", help="Directory containing .sha256 files"),
    ] = Path("data/hashes"),
    cds_dir: Annotated[
        Path,
        typer.Option("--cds-dir", help="Directory containing extracted CD subdirectories (for file sizes)"),
    ] = Path("CDs"),
) -> None:
    """Compare executable versions across CD releases."""
    files_to_track = files or DEFAULT_FILES

    if not hashes_dir.exists():
        typer.echo(f"Error: hashes directory not found: {hashes_dir}", err=True)
        raise typer.Exit(1)

    hashes_files = sorted([
        f for f in hashes_dir.glob("*.sha256")
        if f.stem not in ("ps.exe", "caesar2.exe")
    ])

    if not hashes_files:
        typer.echo(f"No .sha256 files found in {hashes_dir}", err=True)
        raise typer.Exit(1)

    typer.echo(f"Found {len(hashes_files)} CD hash files\n")

    for file_pattern in files_to_track:
        typer.echo(f"{'=' * 70}")
        typer.echo(f"File: {file_pattern}")
        typer.echo(f"{'=' * 70}")

        hash_to_cds: dict[str, list[tuple[str, str]]] = defaultdict(list)
        missing_cds: list[str] = []

        for hashes_file in hashes_files:
            cd_name = hashes_file.stem
            hashes = _load_hashes_file(hashes_file)
            actual_path, hash_value, _ = _find_file(hashes, file_pattern)
            if hash_value:
                hash_to_cds[hash_value].append((cd_name, actual_path))
            else:
                missing_cds.append(cd_name)

        if hash_to_cds:
            typer.echo(f"\nFound {len(hash_to_cds)} unique version(s):\n")
            for i, (hash_value, cds) in enumerate(
                sorted(hash_to_cds.items(), key=lambda x: -len(x[1])), 1
            ):
                file_size = None
                for cd_name, actual_path in cds:
                    if actual_path:
                        file_size = _get_file_size(cds_dir, cd_name, actual_path)
                        if file_size is not None:
                            break
                size_str = f" ({_format_size(file_size)})" if file_size is not None else ""
                typer.echo(f"Version {i}: {hash_value}{size_str}")
                typer.echo(f"  Found in {len(cds)} CD(s):")
                for cd_name, _ in sorted(cds):
                    typer.echo(f"    - {cd_name}")
                typer.echo("")

        if missing_cds:
            typer.echo(f"Not found in {len(missing_cds)} CD(s):")
            for cd_name in sorted(missing_cds):
                typer.echo(f"    - {cd_name}")
            typer.echo("")

    typer.echo(f"{'=' * 70}")
    typer.echo("Done.")
