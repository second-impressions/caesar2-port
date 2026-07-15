"""Scan command: inspect executables in extracted CD directories for interesting properties."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from pydantic import BaseModel

from c2.parsers.debug import parse_watcom_debug
from c2.parsers.exe import BW_SIGNATURE, LE_SIGNATURE, MZ_SIGNATURE, parse_exe

_EXE_SUFFIXES = {".exe", ".com", ".ovl"}


# ── Models ────────────────────────────────────────────────────────────────────


class ExeScanResult(BaseModel):
    """Scan result for a single executable."""

    path: str
    size: int
    format: str          # e.g. "MZ", "MZ+BW+LE", "LE (bare)"
    has_le: bool = False
    le_objects: Optional[int] = None
    has_watcom_debug: bool = False
    watcom_debug_kb: Optional[int] = None
    error: Optional[str] = None

    @property
    def is_interesting(self) -> bool:
        return self.has_le or self.has_watcom_debug or self.error is not None


# ── Helpers ───────────────────────────────────────────────────────────────────


def _inspect_exe(path: Path) -> ExeScanResult:
    """Inspect a single executable using the existing parsers."""
    size = path.stat().st_size
    fmt = "unknown"
    has_le = False
    le_objects = None
    has_debug = False
    debug_kb = None
    error = None

    try:
        # Peek at the first 2 bytes to determine format
        with open(path, "rb") as f:
            sig = f.read(2)

        if sig[:2] == bytes([MZ_SIGNATURE & 0xFF, MZ_SIGNATURE >> 8]):
            fmt = "MZ"
            # Try full parse (handles MZ → BW chain → LE)
            try:
                _mz, bw_headers, le = parse_exe(path)
                if bw_headers:
                    fmt = "MZ+BW+LE" if le else "MZ+BW"
                else:
                    fmt = "MZ+LE" if le else "MZ"
                if le:
                    has_le = True
                    le_objects = len(le.objects)
            except Exception:
                pass  # Not a DOS/4GW exe — plain MZ is fine

        elif sig[:2] == bytes([LE_SIGNATURE & 0xFF, LE_SIGNATURE >> 8]):
            fmt = "LE (bare)"
            has_le = True

        elif sig[:2] == bytes([BW_SIGNATURE & 0xFF, BW_SIGNATURE >> 8]):
            fmt = "BW"

        # Check for Watcom debug info using the existing parser
        if size >= 14:
            try:
                info = parse_watcom_debug(path)
                has_debug = True
                debug_kb = info.debug_size // 1024
            except (ValueError, Exception):
                pass  # No Watcom debug info

    except OSError as e:
        error = str(e)

    return ExeScanResult(
        path=str(path),
        size=size,
        format=fmt,
        has_le=has_le,
        le_objects=le_objects,
        has_watcom_debug=has_debug,
        watcom_debug_kb=debug_kb,
        error=error,
    )


def _find_executables(directory: Path) -> list[Path]:
    """Recursively find all executable files in a directory."""
    return sorted(
        p for p in directory.rglob("*")
        if p.is_file() and p.suffix.lower() in _EXE_SUFFIXES
    )


# ── Command ───────────────────────────────────────────────────────────────────


def scan(
    directories: Annotated[
        Optional[list[Path]],
        typer.Argument(help="Directories to scan (auto-discovers CDs/extracted/ if omitted)"),
    ] = None,
    interesting_only: Annotated[
        bool,
        typer.Option("--interesting", "-i", help="Only show executables with LE format or Watcom debug info"),
    ] = False,
) -> None:
    """Scan extracted CD directories for executables and report format and debug info."""
    dirs_to_scan: list[Path] = list(directories or [])

    if not dirs_to_scan:
        extracted = Path("CDs/extracted")
        if extracted.exists():
            typer.echo("Auto-discovering in CDs/extracted/...")
            for item in sorted(extracted.iterdir()):
                if item.is_dir():
                    dirs_to_scan.append(item)
                    typer.echo(f"  Found: {item}")

    if not dirs_to_scan:
        typer.echo("No directories to scan. Specify directories or run from repo root.")
        raise typer.Exit(1)

    total_exes = 0
    total_le = 0
    total_debug = 0

    for directory in dirs_to_scan:
        typer.echo(f"\n{'=' * 70}")
        typer.echo(f"Scanning: {directory}")
        typer.echo(f"{'=' * 70}")

        exes = _find_executables(directory)
        if not exes:
            typer.echo("  No executables found.")
            continue

        results = [_inspect_exe(p) for p in exes]
        shown = [r for r in results if not interesting_only or r.is_interesting]

        if not shown:
            typer.echo(f"  {len(results)} executables found, none interesting.")
            continue

        typer.echo(f"  {len(results)} executable(s) found:\n")

        for r in shown:
            rel = Path(r.path).relative_to(directory)
            size_kb = r.size // 1024

            flags: list[str] = []
            if r.has_le:
                objs = f" {r.le_objects} obj" if r.le_objects is not None else ""
                flags.append(f"LE{objs}")
            if r.has_watcom_debug:
                flags.append(f"Watcom debug {r.watcom_debug_kb} KB")
            if r.error:
                flags.append(f"ERROR: {r.error}")

            flag_str = f"  [{', '.join(flags)}]" if flags else ""
            typer.echo(f"  {rel}  ({size_kb} KB, {r.format}){flag_str}")

            total_exes += 1
            if r.has_le:
                total_le += 1
            if r.has_watcom_debug:
                total_debug += 1

    typer.echo(f"\n{'=' * 70}")
    typer.echo(f"Summary: {total_exes} executables shown")
    typer.echo(f"  LE format:      {total_le}")
    typer.echo(f"  Watcom debug:   {total_debug}")
