"""`c2 win-decompile` -- Ghidra decompile from the Windows CAESAR2.EXE build.

Sibling of `c2 mac-decompile`.  The Win95 build is MSVC 4.0 /Od of the SAME
engine source as the DOS Watcom PS.EXE (see docs/windows-builds-fingerprint.md),
so its decompile is a second source-shape oracle -- and, being x86 /Od (no
optimization), often the MOST legible reading of a function: every statement
and local explicit, params named + typed, globals named.

Loads `data/windows-builds/named/caesar2_A_1044480.exe` in pyghidra (auto-
builds the project + applies 1187 function names, 1079 globals, and 1168
signatures from c2_funcs.h on first run; ~60s), then decompiles the function.
Subsequent calls reuse the saved project + per-function disk cache (<1s).

Usage::

    c2 win-decompile city_pop_limit_10_to_1
    c2 win-decompile water_trouble --no-cache

See also:  c2 mac-decompile (Mac PPC oracle), c2 decompile (PS.EXE Ghidra),
           c2 dossier (all streams), docs/windows-builds/ghidra-recreate.md
"""
from __future__ import annotations

import typer


def win_decompile(
    name: str = typer.Argument(..., help="function name (PS symbol)"),
    timeout: int = typer.Option(60, "--timeout", help="Ghidra decompile timeout (s)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="bypass the per-fn disk cache"),
) -> None:
    """Ghidra decompile of a function from the Windows MSVC build."""
    import c2win

    if no_cache:
        if c2win.prog is None:
            c2win.open()
        if c2win.func(name) is None:
            typer.secho(
                f"no Windows function: {name!r} "
                "(not present / not mapped in the Win build)",
                fg=typer.colors.YELLOW, err=True)
            raise typer.Exit(1)
        typer.echo(c2win.decompile(name, timeout))
        return

    src = c2win.decompile_cached(name, timeout)
    if src is None:
        typer.secho(
            f"no Windows function: {name!r} "
            "(not present / not mapped in the Win build)",
            fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(1)
    typer.echo(src)
