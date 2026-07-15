"""gen-header command: generate decomp/include/c2_data.h + c2_funcs.h."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer

from c2.commands.c_source import generate_header


def gen_header(
    symbols_json: Annotated[
        Path,
        typer.Argument(help="Path to symbols.json (default: data/out/symbols.json)"),
    ] = Path("data/out/symbols.json"),
    src_dir: Annotated[
        Optional[Path],
        typer.Option("--src", help="Directory containing .c source files"),
    ] = None,
    output_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--output-dir", "-o",
            help="Directory to write c2_data.h / c2_funcs.h "
                 "(default: decomp/include/)",
        ),
    ] = None,
) -> None:
    """Generate decomp/include/c2_data.h and decomp/include/c2_funcs.h
    from symbols.json + the .c sources.

    Uses symbol sizes (derived from adjacent offsets) to assign C types:
      1 byte   → char
      2 bytes  → short
      4 bytes  → int
      >4, %4=0 → int[]
      >4, %4≠0 → char[]

    Symbols defined with struct types in hand-written .c files are
    excluded (their owning .c file keeps the definition).
    """
    if not symbols_json.exists():
        typer.echo(f"Error: {symbols_json} not found", err=True)
        typer.echo("Run 'c2 export data/PS.EXE' first.", err=True)
        raise typer.Exit(1)

    resolved_src = src_dir or Path("decomp/src")
    resolved_out_dir = output_dir or Path("decomp/include")
    resolved_out_dir.mkdir(parents=True, exist_ok=True)

    # generate_header still accepts a single "out_path" for backwards
    # compatibility; pass an unused placeholder pointing at the target
    # directory so c2_data.h / c2_funcs.h land next to each other.
    placeholder = resolved_out_dir / "_unused.h"
    generate_header(resolved_src, placeholder, symbols_json)


if __name__ == "__main__":
    gen_header()
