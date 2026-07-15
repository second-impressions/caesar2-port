"""`c2 mac-decompile` -- Ghidra Mac PPC decompile with AST cleanup.

Loads `MAC/extracted/French retail/Caesar_II_1.0_fr.pef` in pyghidra (auto-
builds the project + applies our 246 globals + 1291 function names + ~960
function signatures from `c2_funcs.h` on first run), then decompiles the
requested function and runs an AST-based post-processor that removes the
PEF TOC pointer indirection (`*piVar1` -> `water_cover` etc.).

The result is near-source-shape C: parameters typed, globals named,
no extra dereferences.

Usage::

    c2 mac-decompile water_trouble
    c2 mac-decompile water_trouble --raw            # skip AST cleaner
    c2 mac-decompile get_reg_buildings_in_radius --no-cache   # bypass cache

First invocation takes ~25s (Ghidra autoanalysis + knowledge application).
Subsequent calls reuse the saved project; per-function results are disk-cached
at ``.c2-cache/mac/decompile/`` so repeat calls are instant (no JVM).

See also:
    c2 win-decompile <name>  -- the Windows MSVC /Od oracle (same cache
                               architecture: `.c2-cache/win/decompile/`)
    c2 mac-fn <name>     -- raw PPC disasm with TOC-name annotations
    docs/mac-ghidra-decompile.md
"""
from __future__ import annotations

import typer


def mac_decompile(
    name: str = typer.Argument(..., help="function name (PC symbol)"),
    raw: bool = typer.Option(False, "--raw", help="skip the AST cleaner"),
    timeout: int = typer.Option(60, "--timeout", help="Ghidra decompile timeout (s)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="bypass the per-fn disk cache"),
) -> None:
    """Ghidra decompile of a function from the Mac PPC binary."""
    import mac    # imports + starts JVM lazily

    if no_cache:
        # Bypass the cache: open the project, confirm the function exists,
        # decompile fresh (+ clean inline if --raw not given).
        if mac.prog is None:
            mac.open()
        if mac.func(name) is None:
            typer.secho(
                f"no Mac function: {name!r} "
                "(not present in the Mac PPC build -- inlined or build-specific)",
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(1)
        if raw:
            typer.echo(mac.decompile(name, timeout))
        else:
            typer.echo(mac.decompile_clean(name, timeout))
        return

    # Not every PC symbol exists in the Mac PPC build (inlined, build-
    # specific, or simply absent).  decompile_cached records absence as an
    # empty cache file and returns None, so report that cleanly.
    if raw:
        src = mac.decompile_cached(name, timeout)
    else:
        try:
            src = mac.decompile_clean(name, timeout)
        except ValueError:
            src = None
    if src is None:
        typer.secho(
            f"no Mac function: {name!r} "
            "(not present in the Mac PPC build -- inlined or build-specific)",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(1)
    typer.echo(src)
