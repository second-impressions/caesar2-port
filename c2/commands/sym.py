"""Look up symbols by address in data/out/symbols.json.

Usage:
    uv run c2 sym 0x726f8 0x34744 0x3cca9
    uv run c2 sym 0x726f8          # single address
    echo "0x726f8 0x34744" | uv run c2 sym -
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer


def _load(symbols_json: Path) -> tuple[list[dict], list[dict]]:
    data = json.loads(symbols_json.read_text())
    return data["symbols"], data.get("modules", [])


def _lookup(symbols: list[dict], addr: int, radius: int = 0) -> list[dict]:
    return sorted(
        [s for s in symbols if abs(s["offset"] - addr) <= radius],
        key=lambda s: abs(s["offset"] - addr),
    )


def sym(
    addresses: Annotated[
        list[str],
        typer.Argument(
            help="Hex or decimal addresses to look up. Pass '-' to read from stdin.",
        ),
    ],
    radius: Annotated[
        int,
        typer.Option("--radius", "-r", help="Also show symbols within ±N bytes"),
    ] = 0,
    code: Annotated[
        bool,
        typer.Option("--code/--no-code", help="Include code symbols"),
    ] = True,
    data: Annotated[
        bool,
        typer.Option("--data/--no-data", help="Include data symbols"),
    ] = True,
    symbols_json: Annotated[
        Path,
        typer.Option("--symbols", "-s"),
    ] = Path("data/out/symbols.json"),
) -> None:
    """Look up one or more addresses in the extracted symbol table."""

    if not symbols_json.exists():
        typer.echo(f"Error: {symbols_json} not found", err=True)
        raise typer.Exit(1)

    # Support reading addresses from stdin when '-' is passed
    raw: list[str] = []
    for a in addresses:
        if a == "-":
            raw.extend(sys.stdin.read().split())
        else:
            raw.append(a)

    syms, _ = _load(symbols_json)

    for raw_addr in raw:
        try:
            addr = int(raw_addr, 0)
        except ValueError:
            typer.echo(f"  {raw_addr}: not a valid address", err=True)
            continue

        hits = _lookup(syms, addr, radius)
        hits = [h for h in hits if (code and h["is_code"]) or (data and not h["is_code"])]

        if not hits:
            typer.echo(f"0x{addr:08X}  (no symbol found)")
            continue

        for h in hits:
            kind   = "code" if h["is_code"] else "data"
            name   = h["raw_name"].rstrip("_")
            delta  = h["offset"] - addr
            delta_str = f"+{delta}" if delta > 0 else (f"{delta}" if delta < 0 else "")
            typer.echo(f"0x{addr:08X}  {name}{delta_str}  [{kind}]")
